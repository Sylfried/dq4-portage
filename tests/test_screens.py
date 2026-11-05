"""Test du moniteur du plein ecran : le plein ecran (F11, Alt + Entree, interrupteur « Plein écran ») se fait toujours sur le moniteur ou se trouve la fenetre. Le choix du moniteur (reglage `ecran_plein`, ligne
« Écran du plein écran ») a ete retire le 03/11/2026 sur demande de Sylfried. Sans fenetre reelle, avec de faux moniteurs (`FakeScreen`) et la vraie logique de screens.py et de fenetre.Game (liee a une fausse
fenetre qui journalise ses appels).

  1. screens.py : liste des moniteurs (principal marque), moniteur de la fenetre (celui de son centre), cible (celui de la fenetre, a defaut le principal) ;
  2. reglages : `ecran_plein` et `sortie_audio` n'existent plus (cles obsoletes, jamais relues) ; les cles de la camera a la souris restent booleennes ;
  3. plein ecran : le moniteur ou se trouve la fenetre sert a chaque entree (meme apres un deplacement), un seul moniteur comme avant ; moniteurs illisibles = repli sans plantage ; echec = fenetre gardee ;
     retour en fenetre ou elle etait (ou centree sur le moniteur du plein ecran) ;
  4. page Affichage : plus de ligne « Écran du plein écran ».

    python3 tools/test_screens.py
"""
import json, os, sys, tempfile, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import pyglet
pyglet.options['shadow_window'] = False          # pas de fenetre cachee : le test tourne sans serveur d'affichage
from dq4_pc.window import screens as EK
from dq4_pc.persistence import settings as RG

try:
    from dq4_pc.window import game as WND
    from test_window_mode import FakeWindow, FakeScreen
except Exception as ex:
    WND = None; ERROR_WND = ex

A = lambda: FakeScreen(0, 0, 1920, 1080, 'Moniteur A', True)
B = lambda: FakeScreen(1920, 0, 2560, 1440, 'Moniteur B')
C = lambda: FakeScreen(-1280, 0, 1280, 1024, '')


class Logic(unittest.TestCase):
    def test_entries_main_marked(self):
        d = EK.listing([B(), A()])                                                    # (pyglet peut donner le principal en second)
        self.assertEqual([x['principal'] for x in d], [False, True]); self.assertEqual([x['indice'] for x in d], [0, 1])
        self.assertEqual((d[1]['largeur'], d[1]['hauteur'], d[1]['nom']), (1920, 1080, 'Moniteur A')); self.assertEqual(EK.listing([C()])[0]['nom'], '')

    def test_a_single_primary_even_if_the_system_announces_none(self):
        e1, e2 = FakeScreen(0, 0, 100, 100), FakeScreen(100, 0, 100, 100)
        e1.is_primary = e2.is_primary = False
        d = EK.listing([e2, e1]); self.assertEqual(sum(x['principal'] for x in d), 1); self.assertTrue(d[1]['principal'])          # (a defaut : celui en (0, 0))
        e1.x = 5; self.assertTrue(EK.listing([e2, e1])[0]['principal'])                                           # (a defaut du defaut : le premier)

    def test_unreadable_screens(self):
        self.assertEqual(EK.listing(None), []); self.assertEqual(EK.listing([]), [])
        d = EK.listing([object(), A()]); self.assertEqual(len(d), 1); self.assertEqual(d[0]['source'], 1)         # (un ecran illisible est ignore ; `source` retrouve l'objet pyglet)

    def test_target_is_window_monitor(self):
        d = EK.listing([A(), B()])
        self.assertEqual(EK.target(d, 0), 0); self.assertEqual(EK.target(d, 1), 1)                                   # celui de la fenetre
        self.assertEqual(EK.target(d, None), 0); self.assertEqual(EK.target(d, 7), 0); self.assertEqual(EK.target(d, -1), 0)          # fenetre inconnue : le principal
        self.assertEqual(EK.target(EK.listing([B(), A()]), None), 1)                                                    # (le principal, meme en second)
        self.assertIsNone(EK.target([], None)); self.assertIsNone(EK.target([], 0))

    def test_window_screen(self):
        d = EK.listing([A(), B(), C()])
        self.assertEqual(EK.screen_of((100, 80, 1280, 720), d), 0)
        self.assertEqual(EK.screen_of((2000, 100, 1280, 720), d), 1)
        self.assertEqual(EK.screen_of((-1000, 0, 1280, 720), d), 2)
        self.assertEqual(EK.screen_of((1500, 100, 1280, 720), d), 1)                                              # a cheval : celui du centre (2140, 460)
        self.assertEqual(EK.screen_of((1500, 100, 600, 300), d), 0)                                               # a cheval, centre (1800, 250) : A
        self.assertEqual(EK.screen_of((1800, 100, 400, 300), d), 1)                                               # centre (2000, 250) : B
        self.assertIsNone(EK.screen_of((9000, 9000, 100, 100), d)); self.assertIsNone(EK.screen_of(None, d)); self.assertIsNone(EK.screen_of((1, 2), d))

class Setting(unittest.TestCase):
    def load(self, content):
        f = os.path.join(tempfile.mkdtemp(prefix='rg_ecran_'), 'reglages.json')
        with open(f, 'w', encoding='utf-8') as fh: json.dump(content, fh)
        return RG.Settings(f), f

    def test_monitor_and_audio_output_choices_removed(self):
        for k in ('ecran_plein', 'sortie_audio'):
            self.assertNotIn(k, RG.DEFAULT); self.assertIn(k, RG.OBSOLETE_KEYS); self.assertNotIn(k, RG.Settings(None).v)
        r, f = self.load({'son': False, 'ecran_plein': {'indice': 1, 'x': 1920, 'y': 0, 'largeur': 2560, 'hauteur': 1440, 'nom': 'B'}, 'sortie_audio': {'id': 'a', 'nom': 'Casque'}})
        for k in ('ecran_plein', 'sortie_audio'): self.assertNotIn(k, r.v, k)          # un ancien fichier de reglages : les deux cles ne sont pas relues
        self.assertFalse(r['son']); r.store()
        with open(f, encoding='utf-8') as fh: raw_value = json.load(fh)
        for k in ('ecran_plein', 'sortie_audio'): self.assertNotIn(k, raw_value, k)          # ... et disparaissent du fichier a la prochaine sauvegarde

    def test_camera_key_boolean(self):
        r = RG.Settings(None); self.assertIs(r['camera_inverser_gd'], False)          # defaut = glisser vers la droite tourne comme la fleche droite
        r, _ = self.load({'camera_inverser_gd': True}); self.assertIs(r['camera_inverser_gd'], True)
        r, _ = self.load({'camera_inverser_gd': 'oui'}); self.assertIs(r['camera_inverser_gd'], False)      # (valeur absurde : defaut)
        r, f = self.load({}); r['camera_inverser_gd'] = True; r.store(); self.assertIs(RG.Settings(f)['camera_inverser_gd'], True)
        r, _ = self.load({'camera_inverser_hb': True}); self.assertNotIn('camera_inverser_hb', r.v)      # (l'inclinaison est retiree : plus d'inversion haut / bas)



def win(screens=None, screen_page=0, **kw):
    return FakeWindow(WND, screens=screens, screen_page=screen_page, **kw)


@unittest.skipIf(WND is None, 'window.py non importable ici')
class FullScreen(unittest.TestCase):
    def setUp(self):
        os.environ.pop('DQ_SIM_ECHEC', None); os.environ.pop('DQ_BASCULE_SIMPLE', None)
        self.zone = WND.useful_zone; WND.useful_zone = lambda: (1904, 1040)

    def tearDown(self):
        WND.useful_zone = self.zone; os.environ.pop('DQ_SIM_ECHEC', None); os.environ.pop('DQ_BASCULE_SIMPLE', None)

    def two(self, **kw): return win([A(), B()], **kw)

    def sets(self, f): return [e for e in f.logfile if e.startswith('set_fullscreen')]

    def test_window_on_pyglet_monitor_as_before(self):
        f = self.two(); f.set_full_screen(True)
        self.assertEqual(self.sets(f), ['set_fullscreen(True)']); self.assertEqual((f.width, f.height), (1920, 1080))          # c'est deja le moniteur de pyglet : rien d'impose
        f = win(); f.set_full_screen(True); self.assertEqual(self.sets(f), ['set_fullscreen(True)'])             # un seul moniteur

    def test_follows_window_moved_to_another_monitor(self):
        f = self.two(); f._windowed_location = (2000, 100)                                                       # (pyglet croit toujours la fenetre sur A, elle est sur B)
        f.set_full_screen(True); self.assertEqual(self.sets(f), ['set_fullscreen(True,écran 2)']); self.assertEqual((f.width, f.height), (2560, 1440))

    def test_each_entry_uses_monitor_where_window_is(self):
        """Fenetre deplacee d'un moniteur a l'autre entre deux passages : chaque entree en plein ecran se fait sur le moniteur ou elle est."""
        f = self.two()
        for slot, expected in (((2000, 100), 'set_fullscreen(True,écran 2)'), ((100, 80), 'set_fullscreen(True,écran 1)'), ((2300, 200), 'set_fullscreen(True,écran 2)')):
            f.logfile.clear(); f._windowed_location = slot; f.toggle_full_screen()
            self.assertTrue(f.fullscreen); self.assertEqual(self.sets(f), [expected], slot)
            f.toggle_full_screen(); self.assertFalse(f.fullscreen)

    def test_straddling_window_uses_center_monitor(self):
        f = self.two(); f._windowed_location = (1500, 100)                                                       # fenetre 1280 x 720 : centre en x = 2140 -> moniteur B
        f.set_full_screen(True); self.assertEqual(self.sets(f), ['set_fullscreen(True,écran 2)'])

    def test_full_screen_already_taken_reasks_nothing(self):
        f = self.two(); f.set_full_screen(True); f.logfile.clear(); f.set_full_screen(True); self.assertEqual(f.logfile, [])          # (deja en plein ecran : rien ne bouge)

    def test_unreadable_monitors_no_crash(self):
        f = self.two()
        def breaks(): raise OSError('plus de moniteurs')
        f.display = types.SimpleNamespace(get_screens=breaks)
        self.assertEqual(f._read_screens(True), ([], [])); self.assertEqual(f._screen_for_fullscreen(), (None, None))
        f.set_full_screen(True); self.assertTrue(f.fullscreen); self.assertEqual(self.sets(f), ['set_fullscreen(True)'])                  # pyglet garde son moniteur

    def test_full_screen_entry_failure_stays_windowed(self):
        f = self.two(); f._windowed_location = (2000, 100); os.environ['DQ_SIM_ECHEC'] = '1'; f.set_full_screen(True)
        self.assertFalse(f.fullscreen); self.assertTrue(f._visible); self.assertEqual((f.win_mode, f.reg['mode_fenetre']), (0, 0))

    def test_return_to_window_no_saved_place_centers_on_fullscreen_monitor(self):
        f = self.two(full=True, screen_page=1); f._note_full_zone(); f.set_full_screen(False)                     # (lancee en plein ecran sur B)
        self.assertIn('set_location(%d,%d)' % (1920 + (2560 - 1280) // 2, (1440 - 720) // 2), f.logfile)
        f = self.two(full=True, screen_page=0); f._note_full_zone(); f.set_full_screen(False); self.assertIn('set_location(320,180)', f.logfile)

    def test_return_to_window_if_its_monitor_vanished(self):
        f = self.two(); f.set_full_screen(True)
        f.display = types.SimpleNamespace(get_screens=lambda: [f._screens[1]])                                       # (A debranche pendant le plein ecran) : seul B reste
        f._windowed_location = (100, 80)
        f.logfile.clear(); f.set_full_screen(False)
        self.assertTrue([e for e in f.logfile if e.startswith('set_location')], f.logfile)                         # la fenetre serait hors de tous les moniteurs : elle est recentree

    def test_alt_enter_and_f11_go_through_same_code(self):
        self.assertIs(WND.Game.toggle_full_screen.__code__.co_names.count('set_full_screen') >= 1, True)
        import inspect; src = inspect.getsource(WND.Game._window_shortcut); self.assertIn('toggle_full_screen', src)

    def test_signature_of_pyglet_set_fullscreen(self):
        """Le retour en fenetre passe la taille par `width` / `height` : le 2e et le 3e argument positionnels de pyglet sont le moniteur et le mode (l'ancien appel `set_fullscreen(False, width_px, height_px)` les confondait)."""
        import inspect
        p = list(inspect.signature(pyglet.window.BaseWindow.set_fullscreen).parameters)
        self.assertEqual(p[:6], ['self', 'fullscreen', 'screen', 'mode', 'width', 'height'])
        self.assertNotIn('set_fullscreen(False, *size_value)', inspect.getsource(WND.Game._apply_full_screen))




@unittest.skipIf(WND is None, 'window.py non importable ici')
class DisplayPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dq4_pc.menus import pause; cls.PA = pause

    def test_no_more_line_to_choose_monitor(self):
        f = win([A(), B()]); f.mode = 4; f.zoom = 1.0; f.post = types.SimpleNamespace(max_msaa=None); f.resolutions = lambda: [(1280, 720), (1920, 1080)]; f.current_resolution = lambda: (1280, 720)
        f.set_resolution = lambda v: None; f.set_mode = lambda v: None; f.set_distance = lambda v: None
        order = [x['l'] for x in self.PA.Pause(f)._entries_display()]
        self.assertEqual(order[:3], ['Langue', 'Plein écran', 'Résolution']); self.assertFalse([l for l in order if 'cran du plein' in l or 'moniteur' in l.lower()], order)
        for name_str in ('valeurs_ecran', 'valeur_ecran', 'nom_ecran', 'ecran_modifiable', 'regler_ecran_plein'): self.assertFalse(hasattr(WND.Game, name_str), name_str)          # (et plus rien dans la fenetre pour le choisir)


if __name__ == '__main__':
    unittest.main(verbosity=1)
