#!/usr/bin/env python3
"""Sonde du flux « avant partie » de Dragon Quest IV (moteur libdq4core.so sous Unicorn, sans Unity).

Amene le moteur au menu titre puis explore chaque branche (continuer / reprendre / auto / nouveau journal / supprimer)
en imitant ce que ferait l'interface Unity : touches (octets pad passes a GameUpdate) et messages de menu
([1, case, pad] deposes dans la file du port, voir Engine.send_menu). Affiche l'etat des fenetres a chaque etape.
Lecture seule sur le depot (dq4_pc est importe tel quel) ; les sauvegardes sont ecrites dans un dossier temporaire.

Usage :
  python3 probe_title.py [--apk DOSSIER_APK] [--lecture DOSSIER_SAVES|-] [--branche B ...] [--captures DIR]
  branches : titre  menu  continuer  reprendre  auto  nouveau  supprimer  toutes (defaut : toutes)
  --lecture - : aucun fichier de sauvegarde (premier lancement) ; defaut : les sauvegardes d'exemple de Sylfried.
Sortie : journal textuel sur la sortie standard (reproductible, deterministe) ; --captures ecrit aussi
les images de la visionneuse (xvfb) si window.py est disponible (voir runv.sh).
"""
import sys, os, struct, shutil, argparse, tempfile, copy
sys.path.insert(0, '/home/claude/dq4-portage/dq4_pc')
from dq4_pc.core import engine as ENGINE

APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/Downloads/DQ Patch/jeux/DQ4/saves/20261007_190735'
A, B, DOWN, UP, RIGHT, LEFT = 0x10, 0x20, 1, 2, 4, 8       # octets de la manette du jeu (GameUpdate arg 2 ; messages de menu)

# adresses (vaddr de la lib ; + LIB_BASE a l'execution)
OBJ = {'LOAD': 0x24c8d8, 'NAMEEDIT': 0x24c928, 'SAVE': 0x24c948, 'NETWORK': 0x24c8b8, 'MESSAGE': 0x24b590, 'GLOBAL': 0x258158}
NAME_BUF, NAME_KIND, NAME_STATE, NAME_MODE = 0x259b5e, 0x259b5c, 0x259b84, 0x259b80      # MaterielMenu_NameEdit (statiques)


def txt(a):
    return ''.join(chr(v & 0xffff) for v in a if v)


class Probe:
    def __init__(self, apk=APK, read_dir=SAVES, write_dir=None, language=1, silence=False):
        self.tmp = write_dir or tempfile.mkdtemp(prefix='sonde_')
        shutil.rmtree(self.tmp, ignore_errors=True); os.makedirs(self.tmp)
        self.silence = silence
        self.m = ENGINE.Engine(apk, read_dir, self.tmp, language)
        self.c = self.m.core; self.L = self.c.LIB_BASE
        self.logfile = []                      # (image, paquets) pour inspection
        self.last_items = []

    # ---- acces memoire -------------------------------------------------------------------------------
    def u(self, ad, n=4, sg=False):
        return int.from_bytes(self.c.mem(self.L + ad if ad < 0x10000000 else ad, n), 'little', signed=sg)

    def item(self, name_str, off, n=4, sg=False):
        return self.u(OBJ[name_str] + off, n, sg)

    def part(self):
        g = self.m._global()
        return struct.unpack('<HHH', self.c.mem(g + 0xee, 6))      # partie, suivante, precedente

    def load_button_state(self):
        """MaterielMenu_LOAD : +0x1c etat, +0x20 genre (0 continuer, 1 creer, 2 supprimer, 3 reprendre, 4 auto), +0x24 compteur, +0x2c banque, +0x30 statut du catalogue."""
        return dict(etat=self.item('LOAD', 0x1c), genre=self.item('LOAD', 0x20), banque=self.item('LOAD', 0x2c, 2, True), status=self.item('LOAD', 0x30, 2))

    def state_name(self):
        return dict(etat=self.u(NAME_STATE, 2), mode=self.u(NAME_MODE, 2), gender=self.u(NAME_KIND, 2),
                    nom=self.c.read_cstr(self.L + NAME_BUF).decode('utf-8', 'replace'), stage=self.item('NAMEEDIT', 0x1c))

    def message_state(self):
        return dict(opened=self.item('MESSAGE', 8, 1), answer=self.item('MESSAGE', 0x10))

    # ---- avancement ----------------------------------------------------------------------------------
    def image(self, held=0, decl=None, show=False):
        pkt = self.m.step(held, held if decl is None else decl)
        self.logfile.append((self.m.frames - 1, pkt, list(self.m.msgs_ui)))
        if show: self.show_packets(pkt)
        return pkt

    def advance_time(self, n, **kw):
        for _ in range(n): self.image(**kw)

    def press_state(self, byte=A, duration=1):
        """appui sur la manette (le titre lit decl) puis relachement."""
        self.image(byte, byte)
        for _ in range(duration - 1): self.image(byte, 0)
        self.image(0, 0)

    def menu(self, port, cell, pad=A):
        """message de menu [1, case, pad] (clic/touche sur une case) puis relachement [1, -1, 0] l'image suivante."""
        self.m.send_menu(port, 1, cell, pad); self.image()
        self.m.send_menu(port, 1, -1, 0); self.image()

    # ---- affichage -----------------------------------------------------------------------------------
    def windows(self):
        out = []
        for p, f in sorted(self.m.ui.f.items()):
            if p < 2 or not (f['act'] or f['vis']): continue
            out.append(dict(port=p, type=f['type'], vis=f['vis'], act=f['act'], cur=f['cur'], grille=f.get('grille'),
                            cases={k: v for k, v in sorted(f['cases'].items())}, ints=dict(sorted(f.get('ints', {}).items())), indic=dict(f['indic'])))
        return out

    def show_windows(self, title_screen=''):
        print('  == windows %s (frame %d, part %s)' % (title_screen, self.m.frames - 1, [hex(x) for x in self.part()]))
        for w in self.windows():
            print('   port %2d type %-4s vis=%d act=%d cur=%s grid=%s' % (w['port'], w['type'], w['vis'], w['act'], w['cur'], w['grille']))
            for k, v in w['cases'].items(): print('        case %-8s %r' % (k, v))
            if w['ints']: print('        ints', w['ints'])
            if w['indic']: print('        codes', w['indic'])

    @staticmethod
    def summarize_packets(pkt, ignore=(13, 22, 28, 29, 32, 33)):
        return ' '.join('%d%s%s' % (t, list(a[:6]), ('f' + str([round(x, 2) for x in f[:4]])) if f else '') for t, a, f in pkt if t not in ignore)

    def show_packets(self, pkt):
        print('   img %d : %s' % (self.m.frames - 1, self.summarize_packets(pkt)))

    def messages(self, sieve=lambda p, a: True, raw_value=False):
        """messages moteur -> interface de l'image (hors dessin/entree), les textes de case (apres [11, l, c]) decodes."""
        out = []; prev = None
        for p, a in self.m.msgs_ui:
            a = list(a)
            if a and a[0] in (5, 6) and p >= 2: continue
            if prev and prev[0] == p and prev[1][0] == 11:
                out.append('port %d case(%d,%d) = %r' % (p, prev[1][1], prev[1][2], txt(a))); prev = None; continue
            if sieve(p, a): out.append('port %d %s' % (p, a[:12]))
            prev = (p, a)
        return out


# ---------------------------------------------------------------------------------------------------------------
def to_title_menu(s, verbose=True):
    """Demarrage -> titre (ev01, partie 0xc) -> 1er appui (fondu + invite) -> 2e appui (cmd_start_game) -> GameStartPart + MaterielMenu_LOAD.
    Repere (sans sauvegarde et avec) : appuis aux images 63 et 130 ; le menu s'ouvre ~29 images apres le 2e appui."""
    s.advance_time(63)
    if verbose: s.show_windows('title, before the press'); print('  part', [hex(x) for x in s.part()])
    s.image(A, A)
    s.advance_time(66)
    s.image(A, A)
    for i in range(80):
        s.image()
        if s.part()[0] == 3 and any(w['type'] == 53 for w in s.windows()): break
    s.advance_time(40)
    if verbose: s.show_windows('title menu'); print('  LOAD', s.load_button_state())


# ---------------------------------------------------------------------------------------------------------------
# Constantes ETABLIES (voir engine_pre_game.md)
ROOT = {'continuer': 0, 'reprendre': 1, 'nouveau': 2, 'supprimer': 3, 'auto': 4, 'cloud': 8, 'licence': 11}   # valeur [1, valeur, pad] envoyee au port StartMenuSecond (type 53)
HERO_GENDER = {'masculin': 0, 'feminin': 1}                                                                       # case envoyee au port StartNameEntry (type 55)
YES, NO = 0, 1                                                                                             # cases de la fenetre Oui / Non (type 1, 2 cases : 'Oui' = 0)


def port_type(s, typ, visible=None):
    for w in s.windows():
        if w['type'] == typ and (visible is None or w['vis'] == visible): return w['port']
    raise RuntimeError('no window of type %d (windows: %s)' % (typ, [(w['port'], w['type']) for w in s.windows()]))


def send_name(s, port, name_str, code=2):
    """Valide le clavier : message [code=2, longueur en octets] puis message de donnees (octets UTF-8 empaquetes deux par deux dans des short,
    petit-boutiste) ; le moteur (MaterielMenu_NameEdit::menuSetup, rappel « autre reception ») copie au plus 30 octets (0x1e) vers 0x259b5e."""
    b = name_str.encode('utf-8')[:30]
    sh = [b[i] | ((b[i + 1] if i + 1 < len(b) else 0) << 8) for i in range(0, len(b), 2)]
    sh = [v - 0x10000 if v >= 0x8000 else v for v in sh]
    s.m.send_menu(port, code, len(b)); s.m.send_menu(port, *sh)


def follow(s, n, title_screen='', ignore=lambda p, a: False, verbose=True, stop=None):
    """avance n images en imprimant chaque changement d'etat (etat du menu LOAD, du nom, partie, carte) et les messages de menu utiles."""
    last = None
    for k in range(n):
        pkt = s.image()
        st = (s.load_button_state()['etat'], s.state_name()['etat'], tuple(s.part()), s.m._map_name())
        ms = [m for m in s.messages(lambda p, a: p >= 2 and a and a[0] not in (5, 6, 7) and not ignore(p, a))]
        if verbose and (st != last or (ms and k < 40)):
            print('   %s k=%-3d frame %-4d LOAD=%-2d NAME=%-5d part=%s map=%s %s' % (title_screen, k, s.m.frames - 1, st[0], st[1], [hex(x) for x in st[2]], st[3],
                  s.summarize_packets(pkt, ignore=(13, 22, 28, 29, 32, 33, 12, 30, 31))[:80]), ms[:4])
        last = st
        if stop and stop(s): break
    return last


def describe_files(s):
    try:
        from dq4_save import sieve, analyze
    except ImportError:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from dq4_save import sieve, analyze
    for f in sorted(os.listdir(s.tmp)):
        print('   written: %-10s %s' % (f, analyze(sieve(open(os.path.join(s.tmp, f), 'rb').read()))))


def new_engine(read_dir):
    s = Probe(read_dir=read_dir); to_title_menu(s, verbose=False); return s


def b_title(a):
    print('== title: start without a press (saves: %s)' % ('none' if a.read_dir == '-' else 'exemples'))
    s = Probe(read_dir=None if a.read_dir == '-' else a.read_dir)
    s.advance_time(60); s.show_windows('phase 1 (logos) before the press')
    s.image(A, A); s.advance_time(2); print('   press A -> fade (cmd_fade_out 30 frames, ~3 frames after the press), SetItemCode(0,0) at the end, fade in 30 frames')
    s.advance_time(70); s.show_windows('phase 2 after the 1st press')
    s.image(A, A); follow(s, 90, 'start_game', stop=lambda s: any(w['type'] == 53 for w in s.windows() if w['vis']))
    s.advance_time(10); s.show_windows('title menu'); print('   LOAD', s.load_button_state(), ' part', [hex(x) for x in s.part()])
    print('   files present:', sorted(os.listdir(s.tmp)))


def b_continue(a, cell='continuer', slot=0):
    print('== %s (root cell %d), slot %d' % (cell, ROOT[cell], slot))
    s = new_engine(None if a.read_dir == '-' else a.read_dir)
    p13 = port_type(s, 53)
    s.menu(p13, ROOT[cell]); s.advance_time(3)
    s.show_windows('list (%s)' % cell); print('   LOAD', s.load_button_state())
    p14 = port_type(s, 54)
    s.menu(p14, 0 if cell in ('reprendre', 'auto') else slot)
    print('   slot selection -> ', end=''); follow(s, 420, cell, stop=lambda s: s.part()[0] == 0xc and s.m.frames > 260 and s.load_button_state()['etat'] in (0, 11, 14))
    print('   map loaded:', s.m._map_name(), ' LOAD', s.load_button_state())


def b_new(a, slot=2, name_str='Sofia', gender='masculin'):
    print('== new diary: slot %d, name %r, gender %s' % (slot, name_str, gender))
    s = new_engine(None if a.read_dir == '-' else a.read_dir)
    s.menu(port_type(s, 53), ROOT['nouveau']); s.advance_time(3)
    s.menu(port_type(s, 54), slot); s.advance_time(5)
    if s.state_name()['etat'] != 1:                                                  # banque occupee : question Oui / Non avant la saisie
        s.show_windows('overwrite confirmation'); s.menu(port_type(s, 1, True), YES); s.advance_time(5)
    s.show_windows('name entry (type 55)'); print('   NAME', s.state_name())
    p15 = port_type(s, 55)
    send_name(s, p15, name_str); s.advance_time(3); print('   after the name: NAME', s.state_name())
    s.show_windows('gender choice'); s.menu(p15, HERO_GENDER[gender]); print('   gender confirmed; next:')
    follow(s, 330, 'creation', stop=lambda s: s.m.frames > 300 and s.part()[0] == 0xc and s.m._map_name() != 'ev01' and s.load_button_state()['etat'] in (11, 0))
    print('   map', s.m._map_name(), ' part', [hex(x) for x in s.part()]); describe_files(s)
    s.advance_time(520); s.show_windows('prologue (chapter title)')
    print('   (the mlb1a script then waits for a key: cmd_key_wait_type_b, then message + Yes/No)')


def b_delete(a, slot=1, rep=YES):
    print('== delete: slot %d, answer %s' % (slot, 'Yes' if rep == YES else 'No'))
    s = new_engine(None if a.read_dir == '-' else a.read_dir)
    s.menu(port_type(s, 53), ROOT['supprimer']); s.advance_time(3)
    s.menu(port_type(s, 54), slot); s.advance_time(30)
    s.show_windows('confirmation (message on the canvas of port 1 + Yes/No)'); print('   LOAD', s.load_button_state())
    s.menu(port_type(s, 1, True), rep); follow(s, 60, 'suppr')
    s.press_state(A); s.advance_time(4); follow(s, 20, 'fin')
    print('   LOAD', s.load_button_state()); describe_files(s)


def b_license(a):
    print('== license')
    s = new_engine(None if a.read_dir == '-' else a.read_dir)
    s.menu(port_type(s, 53), ROOT['licence']); follow(s, 60, 'licence'); s.show_windows('licence')


def b_quit(a):
    print('== quit / portal (messages to Unity on port 0)')
    for name_str, typ, cell, pad in (('B on the root menu', 53, -1, B), ('portal button', 74, 0, A)):
        s = new_engine(None if a.read_dir == '-' else a.read_dir)
        s.m.send_menu(port_type(s, typ), 1, cell, pad); s.image()
        print('   %-22s -> %s' % (name_str, [m for m in s.messages() if m.startswith('port 0')]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apk', default=APK); ap.add_argument('--lecture', dest='read_dir', default=SAVES)
    ap.add_argument('--branche', nargs='*', default=['toutes'], choices=['toutes', 'titre', 'continuer', 'reprendre', 'auto', 'nouveau', 'supprimer', 'licence', 'quitter'])
    a = ap.parse_args()
    br = a.branche
    everything = 'toutes' in br
    if everything or 'titre' in br: b_title(a)
    if everything or 'continuer' in br: b_continue(a, 'continuer', 0)
    if everything or 'reprendre' in br: b_continue(a, 'reprendre')
    if everything or 'auto' in br: b_continue(a, 'auto')
    if everything or 'nouveau' in br: b_new(a)
    if everything or 'supprimer' in br: b_delete(a)
    if everything or 'licence' in br: b_license(a)
    if everything or 'quitter' in br: b_quit(a)


if __name__ == '__main__':
    main()
