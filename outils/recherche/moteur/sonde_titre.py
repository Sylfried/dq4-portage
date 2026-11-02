#!/usr/bin/env python3
"""Sonde du flux « avant partie » de Dragon Quest IV (moteur libdq4core.so sous Unicorn, sans Unity).

Amene le moteur au menu titre puis explore chaque branche (continuer / reprendre / auto / nouveau journal / supprimer)
en imitant ce que ferait l'interface Unity : touches (octets pad passes a GameUpdate) et messages de menu
([1, case, pad] deposes dans la file du port, voir Moteur.envoyer_menu). Affiche l'etat des fenetres a chaque etape.
Lecture seule sur le depot (dq4_pc est importe tel quel) ; les sauvegardes sont ecrites dans un dossier temporaire.

Usage :
  python3 sonde_titre.py [--apk DOSSIER_APK] [--lecture DOSSIER_SAVES|-] [--branche B ...] [--captures DIR]
  branches : titre  menu  continuer  reprendre  auto  nouveau  supprimer  toutes (defaut : toutes)
  --lecture - : aucun fichier de sauvegarde (premier lancement) ; defaut : les sauvegardes d'exemple de Sylfried.
Sortie : journal textuel sur la sortie standard (reproductible, deterministe) ; --captures ecrit aussi
les images de la visionneuse (xvfb) si fenetre.py est disponible (voir runv.sh).
"""
import sys, os, struct, shutil, argparse, tempfile, copy
sys.path.insert(0, '/home/claude/dq4-portage/dq4_pc')
import moteur as MO

APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/Downloads/DQ Patch/jeux/DQ4/saves/20261007_190735'
A, B, BAS, HAUT, DROITE, GAUCHE = 0x10, 0x20, 1, 2, 4, 8       # octets de la manette du jeu (GameUpdate arg 2 ; messages de menu)

# adresses (vaddr de la lib ; + LIB_BASE a l'execution)
OBJ = {'LOAD': 0x24c8d8, 'NAMEEDIT': 0x24c928, 'SAVE': 0x24c948, 'NETWORK': 0x24c8b8, 'MESSAGE': 0x24b590, 'GLOBAL': 0x258158}
NAME_BUF, NAME_GENRE, NAME_ETAT, NAME_MODE = 0x259b5e, 0x259b5c, 0x259b84, 0x259b80      # MaterielMenu_NameEdit (statiques)


def txt(a):
    return ''.join(chr(v & 0xffff) for v in a if v)


class Sonde:
    def __init__(self, apk=APK, lecture=SAVES, ecriture=None, langue=1, silence=False):
        self.tmp = ecriture or tempfile.mkdtemp(prefix='sonde_')
        shutil.rmtree(self.tmp, ignore_errors=True); os.makedirs(self.tmp)
        self.silence = silence
        self.m = MO.Moteur(apk, lecture, self.tmp, langue)
        self.c = self.m.core; self.L = self.c.LIB_BASE
        self.journal = []                      # (image, paquets) pour inspection
        self.derniers = []

    # ---- acces memoire -------------------------------------------------------------------------------
    def u(self, ad, n=4, sg=False):
        return int.from_bytes(self.c.mem(self.L + ad if ad < 0x10000000 else ad, n), 'little', signed=sg)

    def objet(self, nom, off, n=4, sg=False):
        return self.u(OBJ[nom] + off, n, sg)

    def partie(self):
        g = self.m._global()
        return struct.unpack('<HHH', self.c.mem(g + 0xee, 6))      # partie, suivante, precedente

    def etat_load(self):
        """MaterielMenu_LOAD : +0x1c etat, +0x20 genre (0 continuer, 1 creer, 2 supprimer, 3 reprendre, 4 auto), +0x24 compteur, +0x2c banque, +0x30 statut du catalogue."""
        return dict(etat=self.objet('LOAD', 0x1c), genre=self.objet('LOAD', 0x20), banque=self.objet('LOAD', 0x2c, 2, True), statut=self.objet('LOAD', 0x30, 2))

    def etat_nom(self):
        return dict(etat=self.u(NAME_ETAT, 2), mode=self.u(NAME_MODE, 2), sexe=self.u(NAME_GENRE, 2),
                    nom=self.c.read_cstr(self.L + NAME_BUF).decode('utf-8', 'replace'), etape=self.objet('NAMEEDIT', 0x1c))

    def etat_message(self):
        return dict(ouvert=self.objet('MESSAGE', 8, 1), reponse=self.objet('MESSAGE', 0x10))

    # ---- avancement ----------------------------------------------------------------------------------
    def image(self, tenu=0, decl=None, afficher=False):
        pq = self.m.step(tenu, tenu if decl is None else decl)
        self.journal.append((self.m.images - 1, pq, list(self.m.msgs_ui)))
        if afficher: self.afficher_paquets(pq)
        return pq

    def avancer(self, n, **kw):
        for _ in range(n): self.image(**kw)

    def appui(self, octet=A, duree=1):
        """appui sur la manette (le titre lit decl) puis relachement."""
        self.image(octet, octet)
        for _ in range(duree - 1): self.image(octet, 0)
        self.image(0, 0)

    def menu(self, port, case, pad=A):
        """message de menu [1, case, pad] (clic/touche sur une case) puis relachement [1, -1, 0] l'image suivante."""
        self.m.envoyer_menu(port, 1, case, pad); self.image()
        self.m.envoyer_menu(port, 1, -1, 0); self.image()

    # ---- affichage -----------------------------------------------------------------------------------
    def fenetres(self):
        out = []
        for p, f in sorted(self.m.ui.f.items()):
            if p < 2 or not (f['act'] or f['vis']): continue
            out.append(dict(port=p, type=f['type'], vis=f['vis'], act=f['act'], cur=f['cur'], grille=f.get('grille'),
                            cases={k: v for k, v in sorted(f['cases'].items())}, ints=dict(sorted(f.get('ints', {}).items())), indic=dict(f['indic'])))
        return out

    def afficher_fenetres(self, titre=''):
        print('  == fenetres %s (image %d, partie %s)' % (titre, self.m.images - 1, [hex(x) for x in self.partie()]))
        for w in self.fenetres():
            print('   port %2d type %-4s vis=%d act=%d cur=%s grille=%s' % (w['port'], w['type'], w['vis'], w['act'], w['cur'], w['grille']))
            for k, v in w['cases'].items(): print('        case %-8s %r' % (k, v))
            if w['ints']: print('        ints', w['ints'])
            if w['indic']: print('        codes', w['indic'])

    @staticmethod
    def resume_paquets(pq, ignorer=(13, 22, 28, 29, 32, 33)):
        return ' '.join('%d%s%s' % (t, list(a[:6]), ('f' + str([round(x, 2) for x in f[:4]])) if f else '') for t, a, f in pq if t not in ignorer)

    def afficher_paquets(self, pq):
        print('   img %d : %s' % (self.m.images - 1, self.resume_paquets(pq)))

    def messages(self, filtre=lambda p, a: True, brut=False):
        """messages moteur -> interface de l'image (hors dessin/entree), les textes de case (apres [11, l, c]) decodes."""
        out = []; prev = None
        for p, a in self.m.msgs_ui:
            a = list(a)
            if a and a[0] in (5, 6) and p >= 2: continue
            if prev and prev[0] == p and prev[1][0] == 11:
                out.append('port %d case(%d,%d) = %r' % (p, prev[1][1], prev[1][2], txt(a))); prev = None; continue
            if filtre(p, a): out.append('port %d %s' % (p, a[:12]))
            prev = (p, a)
        return out


# ---------------------------------------------------------------------------------------------------------------
def vers_menu_titre(s, verbeux=True):
    """Demarrage -> titre (ev01, partie 0xc) -> 1er appui (fondu + invite) -> 2e appui (cmd_start_game) -> GameStartPart + MaterielMenu_LOAD.
    Repere (sans sauvegarde et avec) : appuis aux images 63 et 130 ; le menu s'ouvre ~29 images apres le 2e appui."""
    s.avancer(63)
    if verbeux: s.afficher_fenetres('titre, avant appui'); print('  partie', [hex(x) for x in s.partie()])
    s.image(A, A)
    s.avancer(66)
    s.image(A, A)
    for i in range(80):
        s.image()
        if s.partie()[0] == 3 and any(w['type'] == 53 for w in s.fenetres()): break
    s.avancer(40)
    if verbeux: s.afficher_fenetres('menu titre'); print('  LOAD', s.etat_load())


# ---------------------------------------------------------------------------------------------------------------
# Constantes ETABLIES (voir moteur_avant_partie.md)
RACINE = {'continuer': 0, 'reprendre': 1, 'nouveau': 2, 'supprimer': 3, 'auto': 4, 'cloud': 8, 'licence': 11}   # valeur [1, valeur, pad] envoyee au port StartMenuSecond (type 53)
HEROS = {'masculin': 0, 'feminin': 1}                                                                       # case envoyee au port StartNameEntry (type 55)
OUI, NON = 0, 1                                                                                             # cases de la fenetre Oui / Non (type 1, 2 cases : 'Oui' = 0)


def port_type(s, typ, visible=None):
    for w in s.fenetres():
        if w['type'] == typ and (visible is None or w['vis'] == visible): return w['port']
    raise RuntimeError('pas de fenetre de type %d (fenetres : %s)' % (typ, [(w['port'], w['type']) for w in s.fenetres()]))


def envoyer_nom(s, port, nom, code=2):
    """Valide le clavier : message [code=2, longueur en octets] puis message de donnees (octets UTF-8 empaquetes deux par deux dans des short,
    petit-boutiste) ; le moteur (MaterielMenu_NameEdit::menuSetup, rappel « autre reception ») copie au plus 30 octets (0x1e) vers 0x259b5e."""
    b = nom.encode('utf-8')[:30]
    sh = [b[i] | ((b[i + 1] if i + 1 < len(b) else 0) << 8) for i in range(0, len(b), 2)]
    sh = [v - 0x10000 if v >= 0x8000 else v for v in sh]
    s.m.envoyer_menu(port, code, len(b)); s.m.envoyer_menu(port, *sh)


def suivre(s, n, titre='', ignorer=lambda p, a: False, verbeux=True, arret=None):
    """avance n images en imprimant chaque changement d'etat (etat du menu LOAD, du nom, partie, carte) et les messages de menu utiles."""
    dernier = None
    for k in range(n):
        pq = s.image()
        st = (s.etat_load()['etat'], s.etat_nom()['etat'], tuple(s.partie()), s.m._nom_carte())
        ms = [m for m in s.messages(lambda p, a: p >= 2 and a and a[0] not in (5, 6, 7) and not ignorer(p, a))]
        if verbeux and (st != dernier or (ms and k < 40)):
            print('   %s k=%-3d img %-4d LOAD=%-2d NOM=%-5d partie=%s carte=%s %s' % (titre, k, s.m.images - 1, st[0], st[1], [hex(x) for x in st[2]], st[3],
                  s.resume_paquets(pq, ignorer=(13, 22, 28, 29, 32, 33, 12, 30, 31))[:80]), ms[:4])
        dernier = st
        if arret and arret(s): break
    return dernier


def decrire_fichiers(s):
    try:
        from dq4_sauvegarde import filtre, analyser
    except ImportError:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from dq4_sauvegarde import filtre, analyser
    for f in sorted(os.listdir(s.tmp)):
        print('   ecrit : %-10s %s' % (f, analyser(filtre(open(os.path.join(s.tmp, f), 'rb').read()))))


def nouveau_moteur(lecture):
    s = Sonde(lecture=lecture); vers_menu_titre(s, verbeux=False); return s


def b_titre(a):
    print('== titre : demarrage sans appui (sauvegardes : %s)' % ('aucune' if a.lecture == '-' else 'exemples'))
    s = Sonde(lecture=None if a.lecture == '-' else a.lecture)
    s.avancer(60); s.afficher_fenetres('phase 1 (logos) avant appui')
    s.image(A, A); s.avancer(2); print('   appui A -> fondu (cmd_fade_out 30 images, a ~3 images de l\'appui), SetItemCode(0,0) a la fin, fondu entrant 30 images')
    s.avancer(70); s.afficher_fenetres('phase 2 apres le 1er appui')
    s.image(A, A); suivre(s, 90, 'start_game', arret=lambda s: any(w['type'] == 53 for w in s.fenetres() if w['vis']))
    s.avancer(10); s.afficher_fenetres('menu titre'); print('   LOAD', s.etat_load(), ' partie', [hex(x) for x in s.partie()])
    print('   fichiers presents :', sorted(os.listdir(s.tmp)))


def b_continuer(a, case='continuer', slot=0):
    print('== %s (case racine %d), banque %d' % (case, RACINE[case], slot))
    s = nouveau_moteur(None if a.lecture == '-' else a.lecture)
    p13 = port_type(s, 53)
    s.menu(p13, RACINE[case]); s.avancer(3)
    s.afficher_fenetres('liste (%s)' % case); print('   LOAD', s.etat_load())
    p14 = port_type(s, 54)
    s.menu(p14, 0 if case in ('reprendre', 'auto') else slot)
    print('   selection de la banque -> ', end=''); suivre(s, 420, case, arret=lambda s: s.partie()[0] == 0xc and s.m.images > 260 and s.etat_load()['etat'] in (0, 11, 14))
    print('   carte chargee :', s.m._nom_carte(), ' LOAD', s.etat_load())


def b_nouveau(a, slot=2, nom='Sofia', sexe='masculin'):
    print('== nouveau journal : banque %d, nom %r, sexe %s' % (slot, nom, sexe))
    s = nouveau_moteur(None if a.lecture == '-' else a.lecture)
    s.menu(port_type(s, 53), RACINE['nouveau']); s.avancer(3)
    s.menu(port_type(s, 54), slot); s.avancer(5)
    if s.etat_nom()['etat'] != 1:                                                  # banque occupee : question Oui / Non avant la saisie
        s.afficher_fenetres('confirmation ecrasement'); s.menu(port_type(s, 1, True), OUI); s.avancer(5)
    s.afficher_fenetres('saisie du nom (type 55)'); print('   NOM', s.etat_nom())
    p15 = port_type(s, 55)
    envoyer_nom(s, p15, nom); s.avancer(3); print('   apres le nom : NOM', s.etat_nom())
    s.afficher_fenetres('choix du sexe'); s.menu(p15, HEROS[sexe]); print('   sexe valide ; suite :')
    suivre(s, 330, 'creation', arret=lambda s: s.m.images > 300 and s.partie()[0] == 0xc and s.m._nom_carte() != 'ev01' and s.etat_load()['etat'] in (11, 0))
    print('   carte', s.m._nom_carte(), ' partie', [hex(x) for x in s.partie()]); decrire_fichiers(s)
    s.avancer(520); s.afficher_fenetres('prologue (titre de chapitre)')
    print('   (le script de mlb1a attend ensuite une touche : cmd_key_wait_type_b, puis message + Oui/Non)')


def b_supprimer(a, slot=1, rep=OUI):
    print('== supprimer : banque %d, reponse %s' % (slot, 'Oui' if rep == OUI else 'Non'))
    s = nouveau_moteur(None if a.lecture == '-' else a.lecture)
    s.menu(port_type(s, 53), RACINE['supprimer']); s.avancer(3)
    s.menu(port_type(s, 54), slot); s.avancer(30)
    s.afficher_fenetres('confirmation (message sur le canevas du port 1 + Oui/Non)'); print('   LOAD', s.etat_load())
    s.menu(port_type(s, 1, True), rep); suivre(s, 60, 'suppr')
    s.appui(A); s.avancer(4); suivre(s, 20, 'fin')
    print('   LOAD', s.etat_load()); decrire_fichiers(s)


def b_licence(a):
    print('== licence')
    s = nouveau_moteur(None if a.lecture == '-' else a.lecture)
    s.menu(port_type(s, 53), RACINE['licence']); suivre(s, 60, 'licence'); s.afficher_fenetres('licence')


def b_quitter(a):
    print('== quitter / portail (messages vers Unity sur le port 0)')
    for nom, typ, case, pad in (('B sur le menu racine', 53, -1, B), ('bouton portail', 74, 0, A)):
        s = nouveau_moteur(None if a.lecture == '-' else a.lecture)
        s.m.envoyer_menu(port_type(s, typ), 1, case, pad); s.image()
        print('   %-22s -> %s' % (nom, [m for m in s.messages() if m.startswith('port 0')]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apk', default=APK); ap.add_argument('--lecture', default=SAVES)
    ap.add_argument('--branche', nargs='*', default=['toutes'], choices=['toutes', 'titre', 'continuer', 'reprendre', 'auto', 'nouveau', 'supprimer', 'licence', 'quitter'])
    a = ap.parse_args()
    br = a.branche
    tout = 'toutes' in br
    if tout or 'titre' in br: b_titre(a)
    if tout or 'continuer' in br: b_continuer(a, 'continuer', 0)
    if tout or 'reprendre' in br: b_continuer(a, 'reprendre')
    if tout or 'auto' in br: b_continuer(a, 'auto')
    if tout or 'nouveau' in br: b_nouveau(a)
    if tout or 'supprimer' in br: b_supprimer(a)
    if tout or 'licence' in br: b_licence(a)
    if tout or 'quitter' in br: b_quitter(a)


if __name__ == '__main__':
    main()
