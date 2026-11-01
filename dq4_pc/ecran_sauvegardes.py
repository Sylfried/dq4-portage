"""Ecran « Sauvegardes » du menu de depart (a la place de la case « Sauv. cloud » du jeu mobile) : exporter et importer les fichiers de sauvegarde.

N'existe pas dans le jeu d'origine : fenetre dessinee dans le style des autres menus (cadre noir, plaques et bouton retour du jeu). La logique des fichiers est dans `sauvegardes.py`.
Le choix du fichier passe par la boite de dialogue de Windows (tkinter, dans un fil a part : la fenetre du jeu reste vivante) ; sans tkinter, repli sur des dossiers du portage (`sauvegardes/export`, `sauvegardes/import`)."""
import os
import pyglet
from pyglet import gl
import sauvegardes as S

CADRE = (-215.0, -215.0, 215.0, 215.0)                 # unites d'interface, origine au centre de la colonne de 450 x 800, Y vers le haut
BLANC = (255, 255, 255, 255); AIDE = (170, 170, 170, 255); GRIS = (128, 128, 128, 255); ROUGE = (255, 110, 110, 255); VERT = (150, 235, 160, 255)
JAUNE = (255, 235, 4)
SE_BOUTON = 300                                          # bruitage d'appui sur un bouton de menu (comme fenetre.SE_BOUTON)
BOUTONS = ('Exporter', 'Importer')
BTN_Y, BTN_L, BTN_H, BTN_X = -42.0, 180.0, 50.0, 100.0
RETOUR_L, RETOUR_H = 62.0, 52.0
I_RETOUR = 2
EXPLICATION = ("Exporter : enregistre tes journaux (data1 à data5, data9) et tes états instantanés dans un fichier .zip.",
               "Importer : lit un .zip de ce genre, ou des fichiers data1.dat, data2.dat… (par exemple copiés depuis un téléphone Android).",
               "Les fichiers remplacés sont d'abord copiés dans le dossier « avant_import_… » de tes sauvegardes.")


def _nb(n, singulier, pluriel):
    return '%d %s' % (n, singulier if n < 2 else pluriel)


class EcranSauvegardes:
    def __init__(self, J):
        self.J = J; self.cur = 0; self.zones = []; self.survol = None; self.dialogue = None; self.action = None; self.msg = []; self.msg_coul = BLANC
        self.a_recharger = False                          # vrai apres un import reussi : la fenetre du jeu relit les journaux

    # ---- logique
    def _dossiers(self):
        a = self.J.args
        return a.saves_ecriture, a.saves_lecture

    def exporter(self):
        if self.dialogue is not None: return
        ecr, _ = self._dossiers()
        self.action = 'export'; self.dialogue = S.Dialogue('enregistrer', 'Exporter les sauvegardes', ecr if os.path.isdir(ecr) else None, S.nom_export_par_defaut())
        self._dire(["Choisis où enregistrer le fichier dans la fenêtre qui vient de s'ouvrir…"], AIDE)

    def importer(self):
        if self.dialogue is not None: return
        ecr, _ = self._dossiers()
        self.action = 'import'; self.dialogue = S.Dialogue('ouvrir', 'Importer des sauvegardes', None)
        self._dire(["Choisis le .zip ou les fichiers de sauvegarde dans la fenêtre qui vient de s'ouvrir…"], AIDE)

    def _dire(self, lignes, coul=BLANC):
        self.msg = list(lignes); self.msg_coul = coul

    def maj(self):
        """Appelee a chaque image : traite la reponse de la boite de dialogue."""
        d = self.dialogue
        if d is None or d.resultat is None: return
        self.dialogue = None; ecr, lec = self._dossiers(); action, self.action = self.action, None
        try:
            if action == 'export':
                if d.indisponible:                                     # pas de boite de dialogue : un dossier du portage
                    chemin = os.path.join(ecr, 'export', S.nom_export_par_defaut())
                elif not d.resultat: self._dire(['Export annulé.'], AIDE); return
                else: chemin = d.resultat[0]
                nj, ne = S.exporter(ecr, lec, chemin)
                self._dire(['Exporté : %s et %s.' % (_nb(nj, 'fichier de sauvegarde', 'fichiers de sauvegarde'), _nb(ne, 'état instantané', 'états instantanés')), chemin], VERT)
            elif action == 'import':
                if d.indisponible:
                    dossier = os.path.join(ecr, 'import'); os.makedirs(dossier, exist_ok=True)
                    if not any(os.scandir(dossier)):
                        try: os.startfile(dossier)                      # (Windows) ouvre le dossier dans l'Explorateur
                        except Exception: pass
                        self._dire(['Pas de boîte de dialogue disponible : dépose tes fichiers (.zip, data1.dat…) dans', dossier, 'puis clique de nouveau sur Importer.'], ROUGE); return
                    sources = [dossier]
                elif not d.resultat: self._dire(['Import annulé.'], AIDE); return
                else: sources = d.resultat
                nj, ne, copie, pb = S.importer(sources, ecr, lec)
                self.a_recharger = True; mo = self.J.moteur
                nouveau = mo.relire_journaux()                         # les listes (Continuer, Reprendre, Supprimer, Auto) affichent aussitot les nouveaux journaux
                lignes = ['Importé : %s et %s.' % (_nb(nj, 'fichier de sauvegarde', 'fichiers de sauvegarde'), _nb(ne, 'état instantané', 'états instantanés'))]
                if copie: lignes.append('Anciens fichiers copiés dans : ' + copie)
                if pb: lignes.append('Ignorés : ' + '; '.join(pb))
                if mo.etat_boutons_depart(nouveau) != mo.etat_boutons_depart(self.J.statut_depart):
                    lignes.append('Pour mettre à jour les boutons grisés du menu de départ, relance le jeu.')
                self._dire(lignes, VERT)
        except Exception as ex:
            self._dire(['Impossible : %s' % (ex,)], ROUGE)

    # ---- entrees
    def appuyer(self, i):
        if i == 0: self.exporter(); return True
        if i == 1: self.importer(); return True
        if i == I_RETOUR: self.J._sauv_fermer(); return True
        return False

    def touche(self, symbol, modifiers=0):
        K = pyglet.window.key
        if symbol in (K.ESCAPE, K.BACKSPACE) or self.J.reg.action_de(symbol) == 'B': self.J._sauv_fermer(); return True
        if symbol in (K.LEFT, K.UP): self.cur = (self.cur - 1) % 3; return True
        if symbol in (K.RIGHT, K.DOWN, K.TAB): self.cur = (self.cur + 1) % 3; return True
        if symbol in (K.RETURN, K.ENTER, K.SPACE) or self.J.reg.action_de(symbol) == 'A':
            if self.appuyer(self.cur): self.J.son.jouer_se(SE_BOUTON)
            return True
        return True

    def clic(self, x, y, bouton):
        if bouton == pyglet.window.mouse.RIGHT: self.J._sauv_fermer(); return
        for x0, y0, x1, y1, i in self.zones:
            if x0 <= x <= x1 and y0 <= y <= y1:
                self.cur = i
                if self.appuyer(i): self.J.son.jouer_se(SE_BOUTON)
                return

    def hover(self, x, y):
        self.survol = None
        for x0, y0, x1, y1, i in self.zones:
            if x0 <= x <= x1 and y0 <= y <= y1: self.survol = i; self.cur = i; return

    # ---- dessin
    def _lignes(self, P, texte, largeur, taille):
        """Texte coupe aux mots (et aux caracteres pour un chemin sans espace) pour tenir dans `largeur` pixels."""
        out = []
        for para in texte.split('\n'):
            cur = ''
            for mot in para.split(' '):
                essai = (cur + ' ' + mot) if cur else mot
                if P._et(essai, taille).content_width <= largeur: cur = essai; continue
                if cur: out.append(cur)
                while P._et(mot, taille).content_width > largeur and len(mot) > 1:       # mot trop long (chemin) : coupe au dernier caractere qui tient
                    n = len(mot)
                    while n > 1 and P._et(mot[:n], taille).content_width > largeur: n -= 1
                    out.append(mot[:n]); mot = mot[n:]
                cur = mot
            out.append(cur)
        return out

    def dessiner(self, J, cx, cy, ech):
        P = J.pause; k = ech * 800.0 / 900.0
        ech = min(ech, 0.97 * J.height / (CADRE[3] - CADRE[1])); k = ech * 800.0 / 900.0
        U = lambda x, y: (cx + x * ech, cy + y * ech)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        fond = pyglet.shapes.Rectangle(0, 0, J.width, J.height, color=(0, 0, 0)); fond.opacity = 170; fond.draw()           # le menu de depart reste visible, assombri
        x0, y0 = U(CADRE[0], CADRE[1]); x1, y1 = U(CADRE[2], CADRE[3]); P._cadre(x0, y0, x1 - x0, y1 - y0, k)
        P._melange()

        def texte(t, x, y, taille, coul=BLANC, ancre=1):
            et = P._et(t, taille * ech * 0.75, coul); w = et.content_width; px, py = U(x, y)
            et.x = px - (w / 2 if ancre == 1 else (w if ancre == 2 else 0)); et.y = py - taille * ech * 0.30; et.draw()
        texte('Sauvegardes', 0, CADRE[3] - 40, 26)
        y = CADRE[3] - 82; larg = (CADRE[2] - CADRE[0] - 40) * ech
        for ligne in EXPLICATION:
            for l in self._lignes(P, ligne, larg, 13 * ech * 0.75):
                texte(l, CADRE[0] + 20, y, 13, AIDE, 0); y -= 17
            y -= 4
        souris = J.dernier_peripherique == 'souris'; zones = []
        for i, lib in enumerate(BOUTONS):
            xc = (i * 2 - 1) * BTN_X; a, b = U(xc - BTN_L / 2, BTN_Y - BTN_H / 2); w, h = BTN_L * ech, BTN_H * ech
            sel = self.cur == i; sur = souris and self.survol == i; occupe = self.dialogue is not None
            P._plaque(a, b, w, h, k, sur or (sel and not souris))                    # (souris : la plaque sous le pointeur s'assombrit, sans encadre jaune)
            if sel and not souris: P._curseur(a - 24 * ech, b + h / 2, 28 * ech)
            P._melange(); texte(lib, xc, BTN_Y, 20, GRIS if occupe else BLANC)
            zones.append((a, b, a + w, b + h, i))
        # message de resultat
        y = BTN_Y - BTN_H / 2 - 30; larg_msg = larg - (RETOUR_L + 14) * ech                  # (le message s'arrete avant le bouton retour, en bas a droite)
        for ligne in self.msg:
            for l in self._lignes(P, ligne, larg_msg, 14 * ech * 0.75):
                texte(l, CADRE[0] + 20, y, 14, self.msg_coul, 0); y -= 18
        a, b = U(CADRE[2] - RETOUR_L - 14, CADRE[1] + 12); w, h = RETOUR_L * ech, RETOUR_H * ech
        sur = souris and self.survol == I_RETOUR
        P._bouton_retour(a, b, w, h, sur or (self.cur == I_RETOUR and not souris))
        if self.cur == I_RETOUR and not souris: P._curseur(a - 24 * ech, b + h / 2, 28 * ech)
        zones.append((a, b, a + w, b + h, I_RETOUR)); self.zones = zones
