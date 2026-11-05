"""Test (sans moteur ni affichage) de l'ecran « Paramètres » (#136) : l'ecran qui s'appelait « Pause » (menu Echap) s'appelle « Paramètres » et ne met plus le jeu en pause : le jeu tourne derriere lui
(sans touche ni clic : les touches du menu ne font pas marcher le heros). Depuis #178 (D-229, « il ne faut aucune pause dans aucun menu ») AUCUNE page ne l'arrete, pas meme « Historique » ni « Quitter » ;
le mecanisme (Pause.FROZEN_PAGES, vide) reste et est essaye ici avec une page figee de test.

    python3 tools/test_params_without_pause.py

  1. le titre de la racine est « Paramètres » (plus « Pause ») ;
  2. Pause.freezes_game : faux menu ferme, faux sur TOUTES les pages (racine, reglages, historique, question de sortie ; toute page `_e_*` du menu), Pause.FROZEN_PAGES vide ;
  3. Game._sync_freeze : le son et l'horloge ne s'arretent qu'en entrant sur une page figee (ici une page de test ajoutee a FROZEN_PAGES ; aucune par defaut), et repartent en la quittant (sans rattrapage du temps passe) ; Game.pause_game : ouvrir ne coupe rien, fermer rend le son s'il etait arrete ;
  4. Game.tick : aucune entree n'est envoyee au moteur menu ouvert ; Game._speed_factor : pas de marche acceleree menu ouvert (aucune direction n'est envoyee au jeu) ;
  5. Game._boucle : le moteur tourne menu ouvert (sauf page figee : aucune).
"""
import inspect, os, sys, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.window import game as F
from dq4_pc.menus import pause as PA
from dq4_pc.core import engine as ENGINE


def menu(screen_page, opened=True):
    p = PA.Pause.__new__(PA.Pause); p.opened = opened; p.stack = ['racine'] + ([screen_page] if screen_page != 'racine' else []); return p


class TestTitle(unittest.TestCase):
    def test_root_is_called_settings(self):
        src = inspect.getsource(PA.Pause.draw_all)
        self.assertTrue("'racine': 'Paramètres'" in src or "'racine': N_('Paramètres')" in src, 'le titre de la racine')                    # (D-238 : N_() marque le texte, traduit au dessin)
        self.assertNotIn("'racine': 'Pause'", src); self.assertNotIn("'racine': N_('Pause')", src)


class TestFrozenPages(unittest.TestCase):
    def test_settings_pages_let_game_run(self):
        for page in ('racine', 'affichage', 'son', 'commandes', 'interface', 'etats', 'modifications'):
            self.assertFalse(menu(page).freezes_game(), page)

    def test_history_and_quit_no_longer_stop_the_game(self):                                                      # #178 : « le menu historique met le jeu en pause, il ne faut aucune pause dans aucun menu »
        for page in ('historique', 'quitter'): self.assertFalse(menu(page).freezes_game(), page)

    def test_no_menu_page_freezes_the_game(self):
        pages = set(PA.Pause.PAGE_ENTRIES)
        self.assertGreaterEqual(len(pages), 8)                                                                           # (toutes les pages du menu, pas seulement celles que ce test connait)
        for page in sorted(pages): self.assertFalse(menu(page).freezes_game(), page)
        self.assertEqual(tuple(PA.Pause.FROZEN_PAGES), ())

    def test_closed_menu(self):
        self.assertFalse(menu('historique', opened=False).freezes_game())

    def test_page_added_to_frozen_pages_would_freeze_the_game_until_return(self):                                  # (le mecanisme reste, vide)
        old = PA.Pause.FROZEN_PAGES
        try:
            PA.Pause.FROZEN_PAGES = ('historique',)
            p = menu('historique'); self.assertTrue(p.freezes_game()); p.stack.pop(); self.assertFalse(p.freezes_game())
        finally: PA.Pause.FROZEN_PAGES = old


class Fake:
    """Ce que la boucle de la fenetre demande au menu, au son et au reste (champs de Jeu utilises par les methodes essayees)."""
    def __init__(self, screen_page='racine'):
        self.stack_p = menu(screen_page); self.pause = self.stack_p; self.calls = []; self._game_frozen = False; self.acc = 5.0; self.t_loop = 1.0
        self.sound = types.SimpleNamespace(set_paused=lambda yes: self.calls.append(('son', yes)))
        self.pad_prev = None; self.prev_action = None; self.rep = {}; self.hovered = self.press_state = self.hover_node = None
        self.pad = lambda: 0; self._held = lambda a: False; self.mouse_guard = types.SimpleNamespace(keyboard=lambda s: None); self.mouse = None


class TestStop(unittest.TestCase):
    """Le mecanisme d'arret (page de FROZEN_PAGES), essaye avec la page « historique » ajoutee le temps du test : par defaut plus aucune page n'arrete le jeu (voir TestFrozenPages)."""
    def setUp(self): self._anc = PA.Pause.FROZEN_PAGES; PA.Pause.FROZEN_PAGES = ('historique',)
    def tearDown(self): PA.Pause.FROZEN_PAGES = self._anc

    def test_default_opening_history_cuts_nothing(self):
        PA.Pause.FROZEN_PAGES = self._anc
        J = Fake('racine'); J.pause.stack.append('historique'); J.acc = 7.0; F.Game._sync_freeze(J)
        self.assertEqual(J.calls, []); self.assertFalse(J._game_frozen); self.assertEqual((J.acc, J.t_loop), (7.0, 1.0))      # ni son coupe, ni horloge remise a zero

    def test_entering_frozen_page_cuts_sound_and_clock(self):
        J = Fake('racine'); F.Game._sync_freeze(J); self.assertEqual(J.calls, []); self.assertFalse(J._game_frozen)       # racine : rien ne s'arrete
        J.pause.stack.append('historique'); J.acc = 7.0; F.Game._sync_freeze(J)
        self.assertEqual(J.calls, [('son', True)]); self.assertTrue(J._game_frozen); self.assertEqual((J.acc, J.t_loop), (0.0, None))
        F.Game._sync_freeze(J); self.assertEqual(J.calls, [('son', True)], 'pas de repetition')

    def test_leaving_frozen_page_restarts(self):
        J = Fake('historique'); F.Game._sync_freeze(J); J.pause.stack.pop(); J.acc = 3.0; J.t_loop = 2.0
        F.Game._sync_freeze(J)
        self.assertEqual(J.calls, [('son', True), ('son', False)]); self.assertFalse(J._game_frozen); self.assertEqual((J.acc, J.t_loop), (0.0, None), 'pas de rattrapage du temps passe')

    def test_open_root_cuts_nothing(self):
        J = Fake('racine'); F.Game.pause_game(J, True); self.assertEqual(J.calls, []); self.assertFalse(J._game_frozen)

    def test_closing_from_frozen_page_restores_sound(self):
        J = Fake('historique'); F.Game._sync_freeze(J); J.pause.opened = False; F.Game.pause_game(J, False)
        self.assertEqual(J.calls, [('son', True), ('son', False)]); self.assertFalse(J._game_frozen)

    def test_closing_root_does_not_touch_sound(self):
        J = Fake('racine'); F.Game.pause_game(J, True); J.pause.opened = False; F.Game.pause_game(J, False); self.assertEqual(J.calls, [])


class TestInputs(unittest.TestCase):
    def test_tick_sends_no_input_while_menu_open(self):
        src = inspect.getsource(F.Game.tick)
        self.assertIn('(mute or self.pause.opened)', src)                                               # (0, 0) : ni touche ni clic ni direction pour le jeu

    def fake_factor(self, opened, dirs):
        eng = types.SimpleNamespace(state=types.SimpleNamespace(effect=None, transition_guard=0, part=ENGINE.PART_FIELD, load_wait=None), msg_visible=False, active_menu=lambda: None, flags=lambda: 0)
        J = types.SimpleNamespace(reg={'vitesse_marche': 3.0, 'vitesse_accel': 2.0, 'vitesse_combat': 0}, engine=eng, pause=types.SimpleNamespace(opened=opened),
                                  pad=lambda: dirs, _held=lambda a: False, hud=types.SimpleNamespace(dpad_run=lambda: False))
        J._battle_clock = lambda: F.Game._battle_clock(J)
        return F.Game._speed_factor(J)

    def test_no_accelerated_walk_with_menu_opened(self):
        self.assertEqual(self.fake_factor(False, ENGINE.LEFT), 3.0, 'terrain : la marche acceleree s\'applique')
        self.assertEqual(self.fake_factor(True, ENGINE.LEFT), 1.0, 'menu ouvert : une direction du menu ne fait pas courir le jeu')


class TestLoop(unittest.TestCase):
    def test_engine_runs_with_menu_open_except_frozen_page(self):
        src = inspect.getsource(F.Game._loop)
        self.assertIn('if self.pause.freezes_game():', src)                                           # seul le retour anticipe d'une page figee (aucune par defaut) arrete le moteur
        self.assertNotIn('if self.pause.opened: self.pause.do_update(); self.acc = 0.0', src)                 # l'ancien arret general a disparu
        self.assertIn('self._sync_freeze()', src)


if __name__ == '__main__':
    unittest.main(verbosity=1)
