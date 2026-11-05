"""Test de la touche « Menu » (menu du terrain : Objets / Magie / Carac. / Divers) : defaut Entree et Tab, migration d'un ancien reglages.json (sans ecraser un choix du joueur), Tab libre ailleurs, ligne de la page
Commandes et bouton ↺ (vrai code de settings.py, de pause.py et, sans fenetre, de Game.on_key_press / _fronts).

    python3 tools/test_menu_key.py
"""
import glob, json, os, re, sys, tempfile, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.persistence import settings as RG
import test_pause_pages as TP

K = pyglet.window.key


def load(content):
    f = os.path.join(tempfile.mkdtemp(prefix='rg_menu_'), 'settings.json')
    with open(f, 'w', encoding='utf-8') as fh: json.dump(content, fh)
    return RG.Settings(f), f


class Default(unittest.TestCase):
    def test_enter_and_tab(self):
        self.assertEqual(RG.DEFAULT_KEYS['menu'], ['RETURN', 'TAB']); self.assertEqual(RG.Settings(None)['touches']['menu'], ['RETURN', 'TAB'])
        r = RG.Settings(None)
        self.assertEqual(r.action_of(K.TAB), 'menu'); self.assertEqual(r.codes('menu'), (K.RETURN, K.TAB))          # (action_of(K.RETURN) est None : pyglet nomme 0xff0d « ENTER » ; le jeu lit les touches par `codes`, voir Game._tenue)
        self.assertEqual(dict(RG.ACTIONS)['menu'], 'Menu')

    def test_tab_belongs_to_no_other_action(self):
        for a, ts in RG.DEFAULT_KEYS.items():
            if a != 'menu': self.assertNotIn('TAB', ts, a)
        self.assertNotIn('TAB', RG.RESERVED); self.assertNotIn('RETURN', RG.RESERVED)
        every = [n for ts in RG.DEFAULT_KEYS.values() for n in ts if n]
        self.assertEqual(len(every), len(set(every)), 'une touche ne sert qu\'a une action')

    def test_tab_elsewhere_in_the_code(self):
        """Les seuls usages de Tab (K.TAB) : replier le panneau de l'editeur d'interface (menu Pause), changer de mode dans la saisie du nom, passer au bouton suivant de l'ecran Sauvegardes. Ces trois ecrans
        prennent la touche dans Game.on_key_press AVANT les actions du jeu (menu Pause ouvert, saisie du nom, ecran Sauvegardes) : Tab n'y est jamais la touche « Menu ». Un nouvel usage doit etre examine ici."""
        here = os.path.join(HERE, '..', 'dq4_pc'); found_set = set()
        for f in glob.glob(os.path.join(here, '**', '*.py'), recursive=True):
            with open(f, encoding='utf-8') as fh:
                if re.search(r'\bK\.TAB\b', fh.read()): found_set.add(os.path.basename(f))
        self.assertEqual(found_set, {'pause.py', 'name_entry.py', 'saves_screen.py'})


class Migration(unittest.TestCase):
    def test_old_default_receives_tab(self):
        for v in (3, 4):
            r, _ = load({'touches_v': v, 'touches': {'menu': ['RETURN', None], 'carte': ['M', None], 'A': ['SPACE', None]}})
            self.assertEqual(r['touches']['menu'], ['RETURN', 'TAB'], 'touches_v %d' % v)
        r, _ = load({'touches_v': 4, 'touches': {k: list(v) for k, v in RG.DEFAULT_KEYS.items() if k != 'menu'} | {'menu': ['RETURN']}}); self.assertEqual(r['touches']['menu'], ['RETURN', 'TAB'])       # (liste d'une seule touche)
        r, _ = load({'touches_v': 4, 'touches': {k: list(v) for k, v in RG.DEFAULT_KEYS.items()} | {'menu': ['RETURN', None]}}); self.assertEqual(r['touches']['menu'], ['RETURN', 'TAB'])      # (fichier complet d'avant)

    def test_player_choice_kept(self):
        for menu in (['E', None], ['RETURN', 'F2'], ['F2', None], [None, None], ['SPACE', 'RETURN'], [None, 'RETURN'], ['E', 'RETURN']):
            r, _ = load({'touches_v': 4, 'touches': {'menu': list(menu), 'A': ['SPACE', None]}}); self.assertEqual(r['touches']['menu'], menu, menu)

    def test_tab_already_taken_by_another_action(self):
        r, _ = load({'touches_v': 4, 'touches': {'menu': ['RETURN', None], 'infos': ['TAB', None]}})
        self.assertEqual(r['touches']['menu'], ['RETURN', None]); self.assertEqual(r['touches']['infos'], ['TAB', None]); self.assertEqual(r.action_of(K.TAB), 'infos')      # le choix du joueur prime

    def test_only_once(self):
        """Apres la migration le fichier est enregistre en v5 : Tab retire ensuite par le joueur (case videe) n'est pas remis."""
        r, f = load({'touches_v': 4, 'touches': {'menu': ['RETURN', None]}}); r.store()
        with open(f, encoding='utf-8') as fh: d = json.load(fh)
        self.assertEqual((d['touches_v'], d['touches']['menu']), (5, ['RETURN', 'TAB']))
        r2 = RG.Settings(f); r2.unbind('menu', 1); r2.store()
        self.assertEqual(RG.Settings(f)['touches']['menu'], ['RETURN', None])
        r3, _ = load({'touches_v': 5, 'touches': {'menu': ['RETURN', None]}}); self.assertEqual(r3['touches']['menu'], ['RETURN', None])

    def test_files_without_keys_or_too_old(self):
        for content in ({}, {'son': False}, {'touches_v': 2, 'touches': {'menu': ['RETURN', None]}}, {'touches': {'menu': ['RETURN', None]}}):
            r, _ = load(content); self.assertEqual(r['touches']['menu'], ['RETURN', 'TAB'], content)                      # (touches abandonnees ou absentes : les defauts)

    def test_other_keys_do_not_move(self):
        r, _ = load({'touches_v': 4, 'touches': {'menu': ['RETURN', None], 'haut': ['W', None], 'carte': ['N', None]}})
        self.assertEqual((r['touches']['haut'], r['touches']['carte'], r['touches']['historique']), (['W', None], ['N', None], ['H', None]))


class CommandsPage(unittest.TestCase):
    def test_default_line_and_button(self):
        J, p = TP.menu('commandes'); e = TP.by_caption(p, 'Menu')
        self.assertEqual((e['t'], e['act'], e['v']), ('touche', 'menu', ['Entrée', 'Tab'])); self.assertTrue(e['est_defaut']())
        J.reg.bind('menu', 1, K.F2); J.reg.bind('menu', 0, K.E)
        e = TP.by_caption(p, 'Menu'); self.assertEqual(e['v'], ['E', 'F2']); self.assertFalse(e['est_defaut']())
        e['defaut'](); e = TP.by_caption(p, 'Menu')                                                          # ↺ : les deux touches reviennent
        self.assertEqual((e['v'], J.reg['touches']['menu']), (['Entrée', 'Tab'], ['RETURN', 'TAB'])); self.assertTrue(e['est_defaut']())

    def test_default_takes_tab_from_other_action(self):
        J, p = TP.menu('commandes'); J.reg.bind('infos', 0, K.TAB)                                            # Tab donne a « Infos » : « Menu » n'a plus que Entree
        self.assertEqual(J.reg['touches']['menu'], ['RETURN', None]); e = TP.by_caption(p, 'Menu'); self.assertFalse(e['est_defaut']())
        e['defaut'](); self.assertEqual(J.reg['touches']['menu'], ['RETURN', 'TAB']); self.assertEqual(J.reg['touches']['infos'], [None, None])      # ↺ reprend Tab (et le dit : message)
        self.assertIn('Infos', p.message[0])
        J.reg.bind('menu', 0, K.F3); J.reg.default_keys(); self.assertEqual(J.reg['touches']['menu'], ['RETURN', 'TAB'])         # « Rétablir les touches par défaut » aussi

    def test_tab_key_capture(self):
        """Lier Tab a « Menu » dans la page Commandes (case secondaire) : la capture de touche prend Tab comme n'importe quelle touche."""
        J, p = TP.menu('commandes'); J.reg.unbind('menu', 1)
        p.capture = ('menu', 1); p.key_press(K.TAB, 0); self.assertEqual(J.reg['touches']['menu'], ['RETURN', 'TAB']); self.assertIsNone(p.capture)

    def test_tab_folds_the_editor_panel(self):
        """Dans l'editeur d'interface, Tab replie le panneau (il ne declenche rien d'autre) ; hors editeur, Tab ne fait rien dans le menu Pause."""
        J, p = TP.menu('interface'); self.assertFalse(p.folded)
        p.key_press(K.TAB, 0); self.assertTrue(p.folded); p.key_press(K.TAB, 0); self.assertFalse(p.folded)
        J, p = TP.menu('affichage'); before = dict(p.selected); p.key_press(K.TAB, 0); self.assertEqual((p.screen_page, p.selected), ('affichage', before))


class InWindow(unittest.TestCase):
    """Vrai code de Game.on_key_press / _fronts sur un faux Jeu (comme test_window_mode.py)."""
    @classmethod
    def setUpClass(cls):
        try: from dq4_pc.window import game as window; cls.WND = window
        except Exception as ex: raise unittest.SkipTest('window.py non importable ici (%r)' % (ex,))

    def fake_game(self, pause=False, name_str=False):
        WND = self.WND
        j = types.SimpleNamespace(swallowed=set(), alt_cand=False, alt_tap=False, reg=RG.Settings(None), key_list=K.KeyStateHandler(), prev_action={}, n=0, _ready=True, combo=[False, False], _logo_touched=False, appuis_pause=0, appuis_nom=0,
                                  pause=None, saves_screen=None, license_panel=None, title_screen=None, last_device='', bascules=0, annulations=0, is_fullscreen=False, mouse=(0, 0), mouse_guard=__import__('dq4_pc.window.inputs', fromlist=['MouseGuard']).MouseGuard(), helptext=False)
        j.pause = types.SimpleNamespace(opened=pause, capture=None, key_press=lambda sym, mods: setattr(j, 'appuis_pause', j.appuis_pause + 1))
        j.name_entry = types.SimpleNamespace(key_press=lambda sym, mods: setattr(j, 'appuis_nom', j.appuis_nom + 1))
        j.toggle_full_screen = lambda: setattr(j, 'bascules', j.bascules + 1)
        j._held = lambda a: WND.Game._held(j, a); j._name_entry_in_progress = lambda: name_str; j._state_number = WND.Game._state_number; j._window_shortcut = lambda sym, mods: WND.Game._window_shortcut(j, sym, mods)
        j.cancel_loading = lambda: None
        return j

    def press_state(self, j, sym):
        j.key_list.on_key_press(sym, 0); return self.WND.Game.on_key_press(j, sym, 0)

    def test_tab_as_enter_on_the_field(self):
        for sym in (K.RETURN, K.TAB):
            j = self.fake_game(); self.press_state(j, sym); self.assertTrue(self.WND.Game._edges(j)['menu'], sym)                # un appui = un front « Menu » (ouvre le menu du terrain, valide, tourne les pages des messages)
            j.key_list.on_key_release(sym, 0); self.assertFalse(self.WND.Game._edges(j)['menu'])
        j = self.fake_game(); self.press_state(j, K.TAB); self.press_state(j, K.RETURN); self.assertTrue(self.WND.Game._edges(j)['menu']); self.assertFalse(self.WND.Game._edges(j)['menu'])          # les deux ensemble : un seul front

    def test_tab_taken_before_actions_in_menu_and_name_entry(self):
        j = self.fake_game(pause=True); self.press_state(j, K.TAB); self.assertEqual(j.appuis_pause, 1)                    # menu Pause : la touche lui appartient
        j = self.fake_game(name_str=True); self.press_state(j, K.TAB); self.assertEqual(j.appuis_nom, 1)                         # saisie du nom : Tab change de mode (name_entry.py)
        j = self.fake_game(); j.saves_screen = types.SimpleNamespace(key_press=lambda sym, mods: setattr(j, 'appuis_nom', 7)); self.press_state(j, K.TAB); self.assertEqual(j.appuis_nom, 7)      # ecran Sauvegardes : bouton suivant


if __name__ == '__main__':
    unittest.main(verbosity=1)
