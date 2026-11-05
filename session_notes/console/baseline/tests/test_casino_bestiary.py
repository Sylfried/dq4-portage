"""Test du casino et du bestiaire (parties 0xf et 0x10 du moteur), sans fenetre ni moteur (faux objets) :

  1. constantes du moteur : PART_CASINO, PART_BESTIARY, MINIGAME_PARTS ;
  2. camera libre du casino (`camera_free`) : position + rotation du paquet 10, sans paquet 11 ; pas ailleurs ;
  3. vitesse de marche : jamais acceleree dans le casino et le bestiaire (les fleches tenues y servent aux menus) ;
  4. Echap : bouton retour de la fenetre ouverte (manette 0x20) dans le casino et le bestiaire, sinon menu Echap ;
  5. menus de saisie numerique au clavier (mise de la machine a sous, du poker, jetons, arene) : colonnes, ▲ / ▼, validation, retour ;
  6. code de fenetre a masque de bits (poker : zones tactiles des cartes et « Donner », valeur 63 hors du tableau exporte) ;
  7. combat de l'arene : fenetre « Quitter » sans validation, A tourne la page du message.

    python3 tools/test_casino_bestiary.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import functools, os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.core import engine as ENGINE
from dq4_pc.window import game as F
from dq4_pc.menus import ui_menu as UI


class Constants(unittest.TestCase):
    def test_parts(self):
        self.assertEqual((ENGINE.PART_CASINO, ENGINE.PART_BESTIARY), (0xf, 0x10))
        self.assertEqual(set(ENGINE.MINIGAME_PARTS), {ENGINE.PART_CASINO, ENGINE.PART_BESTIARY})
        self.assertFalse({ENGINE.PART_INITIAL, ENGINE.PART_TOWN, ENGINE.PART_BATTLE, ENGINE.PART_FIELD} & set(ENGINE.MINIGAME_PARTS))


class FreeCamera(unittest.TestCase):
    def e(self, part, free=False, rot=None): return types.SimpleNamespace(part=part, cam_free=free, cam_rot=rot)

    def test_casino(self):
        self.assertTrue(F.camera_free(self.e(ENGINE.PART_CASINO, rot=(10.0, 0.0, 0.0))), 'casino : position + rotation, sans paquet 11')
        self.assertFalse(F.camera_free(self.e(ENGINE.PART_CASINO, rot=None)), 'pas de rotation : camera a cible')

    def test_other_parts(self):
        self.assertTrue(F.camera_free(self.e(ENGINE.PART_TOWN, free=True, rot=(0.0, 0.0, 0.0))), 'scene (paquet 11, bit 7)')
        self.assertFalse(F.camera_free(self.e(ENGINE.PART_TOWN, rot=(10.0, 0.0, 0.0))), 'ville : la rotation seule ne rend pas la camera libre')
        self.assertFalse(F.camera_free(self.e(ENGINE.PART_BESTIARY, rot=(10.0, 0.0, 0.0))), 'bestiaire : camera de la ville gardee en memoire')

    def test_fake_state_without_game(self):
        """Les tests de camera passent un faux etat sans `part` : camera de ville, pas d'erreur."""
        self.assertFalse(F.camera_free(types.SimpleNamespace(cam_free=False, cam_rot=None)))


def fake_walk(part, msg=False):
    eng = types.SimpleNamespace(state=types.SimpleNamespace(part=part, effect=None, load_wait=None, transition_guard=0, battle_transition=lambda: False), msg_visible=msg, active_menu=lambda: None, flags=lambda: 0x28)
    return types.SimpleNamespace(reg={'vitesse_marche': 2.0, 'vitesse_accel': 1.5}, engine=eng, pad=lambda: ENGINE.RIGHT, _held=lambda a: a == 'accel', hud=types.SimpleNamespace(dpad_run=lambda: False), pause=types.SimpleNamespace(opened=False), _battle_clock=lambda: False)


class WalkSpeed(unittest.TestCase):
    def test_terrain(self):
        self.assertEqual(F.Game._speed_factor(fake_walk(ENGINE.PART_TOWN)), 3.0, 'ville : reglage x accelerateur')

    def test_casino_bestiary(self):
        for part in ENGINE.MINIGAME_PARTS: self.assertEqual(F.Game._speed_factor(fake_walk(part)), 1.0, hex(part))


class FakeWindow:
    """Fenetre de menu du jeu (ui_menu.Window) reduite a ce que lisent les fonctions testees : typ, boutons() = (numero, manette, x0, z0, x1, z1, profondeur)."""
    def __init__(self, typ, buttons): self.typ = typ; self._b = buttons
    def buttons(self): return list(self._b)


def b(num, pad, x, z=0.0): return (num, pad, x - 10.0, z - 10.0, x + 10.0, z + 10.0, 0)


def fake_game_menu(buttons, typ=47, part=ENGINE.PART_CASINO, port=12):
    sends = []
    wnd = FakeWindow(typ, buttons)
    eng = types.SimpleNamespace(state=types.SimpleNamespace(part=part), msg_visible=False, active_menu=lambda: port, send_menu=lambda *a: sends.append(a), ui=types.SimpleNamespace(f={port: {'ordre': 1, 'grille': None, 'vis': True}}))
    j = types.SimpleNamespace(engine=eng, ui_g=types.SimpleNamespace(f={port: wnd}), cursor_step={}, hover_node=1, menu_to_release=None, sound=types.SimpleNamespace(play_sfx=lambda *a: None), sends=sends,
                              name_entry=types.SimpleNamespace(active=False), license_panel=None)
    for name_str in ('_step_columns', '_active_step', '_step_entry', '_can_go_back', '_esc_back'): setattr(j, name_str, functools.partial(getattr(F.Game, name_str), j))
    j._port_for_gamepad = lambda p, pad: p
    return j, wnd


# machine a sous (type 47) : une colonne ▲ (manette 0x2) / ▼ (0x1) de numero 1, « Lancer » (0x10) de numero 0 ; retour 0x20 de numero -1
SLOT = [b(1, 0x2, 100, -50), b(1, 0x1, 100, 50), b(0, 0x10, 0, 100), b(-1, 0x20, 200, 150)]
# jetons (type 44) : cinq colonnes (1, 10, 100, 1000, 10000) de gauche a droite : 10000, 1000, 100, 10, 1 (positions croissantes), validation numero 0, retour -1
CHIPS = [b(n, 0x2, x, -50) for n, x in ((10000, -200), (1000, -100), (100, 0), (10, 100), (1, 200))] + [b(n, 0x1, x, 50) for n, x in ((10000, -200), (1000, -100), (100, 0), (10, 100), (1, 200))] + [b(0, 0x10, 0, 150), b(-1, 0x20, 250, 200)]


class NumericEntry(unittest.TestCase):
    def test_columns(self):
        j, wnd = fake_game_menu(SLOT); self.assertEqual(j._step_columns(wnd), [1])
        j, wnd = fake_game_menu(CHIPS, 44); self.assertEqual(j._step_columns(wnd), [10000, 1000, 100, 10, 1], 'de gauche a droite')

    def test_ordinary_window(self):
        """Une liste (cadeaux, bestiaire) n'a pas de colonne ▲ / ▼ : curseur ordinaire. Les fleches de page (numero -1) ne comptent pas."""
        j, wnd = fake_game_menu([b(0, 0x10, 0, 0), b(1, 0x10, 0, 50), b(-1, 0x2, 50, 0), b(-1, 0x1, 50, 100)], 45)
        self.assertEqual(j._step_columns(wnd), [])
        self.assertFalse(j._step_entry(12, j.engine.ui.f[12], wnd, {0: 1}, ENGINE.UP))
        self.assertEqual(j.sends, [])

    def test_up_down(self):
        j, wnd = fake_game_menu(SLOT); f = j.engine.ui.f[12]
        self.assertTrue(j._step_entry(12, f, wnd, {0: 1}, ENGINE.UP)); self.assertEqual(j.sends[-1], (12, 1, 1, 0x2), '▲ de la colonne 1 (manette 0x2)')
        self.assertEqual(j.menu_to_release, 12, 'le relachement suit a l\'image suivante')
        self.assertTrue(j._step_entry(12, f, wnd, {0: 1}, ENGINE.DOWN)); self.assertEqual(j.sends[-1], (12, 1, 1, 0x1), '▼ (manette 0x1)')
        self.assertIsNone(j.hover_node, 'une touche : le curseur reprend la main')

    def test_left_right_columns(self):
        j, wnd = fake_game_menu(CHIPS, 44); f = j.engine.ui.f[12]; z = {0: 1}
        self.assertEqual(j._active_step(12), 1, 'au depart : les unites (colonne de droite)')
        j._step_entry(12, f, wnd, z, ENGINE.LEFT); self.assertEqual(j._active_step(12), 10)
        j._step_entry(12, f, wnd, z, ENGINE.LEFT); j._step_entry(12, f, wnd, z, ENGINE.LEFT); j._step_entry(12, f, wnd, z, ENGINE.LEFT); j._step_entry(12, f, wnd, z, ENGINE.LEFT); j._step_entry(12, f, wnd, z, ENGINE.LEFT)
        self.assertEqual(j._active_step(12), 10000, 'bornee a gauche')
        j._step_entry(12, f, wnd, z, ENGINE.UP); self.assertEqual(j.sends[-1], (12, 1, 10000, 0x2))
        for _ in range(8): j._step_entry(12, f, wnd, z, ENGINE.RIGHT)
        self.assertEqual(j._active_step(12), 1, 'bornee a droite')
        self.assertEqual(j.sends, [(12, 1, 10000, 0x2)], 'gauche / droite ne transmettent rien au moteur')

    def test_validate_and_back(self):
        j, wnd = fake_game_menu(SLOT); f = j.engine.ui.f[12]
        self.assertTrue(j._step_entry(12, f, wnd, {0: 1}, ENGINE.A)); self.assertEqual(j.sends[-1], (12, 1, 0, 0x10), 'A = bouton de validation (Lancer)')
        self.assertTrue(j._step_entry(12, f, wnd, {0: 1}, ENGINE.B)); self.assertEqual(j.sends[-1], (12, 1, -1, 0x20), 'B = retour (manette 0x20)')

    def test_no_useful_key(self):
        j, wnd = fake_game_menu(SLOT); self.assertFalse(j._step_entry(12, j.engine.ui.f[12], wnd, {0: 1}, 0)); self.assertEqual(j.sends, [])

    def test_several_validations_ordinary_cursor(self):
        """Une fenetre qui a plusieurs boutons de validation (choix a faire) garde le curseur ordinaire."""
        j, wnd = fake_game_menu(SLOT + [b(2, 0x10, 0, 200)]); self.assertIsNone(j._active_step(12))


class EscBack(unittest.TestCase):
    def test_casino_with_back_button(self):
        j, wnd = fake_game_menu(SLOT); self.assertTrue(j._esc_back(), 'machine a sous : Echap = retour')

    def test_bestiary_with_back_button(self):
        j, wnd = fake_game_menu([b(0, 0x10, 0, 0), b(-1, 0x20, 200, 0)], 28, ENGINE.PART_BESTIARY); self.assertTrue(j._esc_back())

    def test_without_back_button_esc_opens_the_menu(self):
        """Rouleaux en marche, cartes en cours de distribution : la fenetre n'a plus de bouton retour actif."""
        j, wnd = fake_game_menu([b(0, 0x10, 0, 0)]); self.assertFalse(j._esc_back())

    def test_message_visible(self):
        j, wnd = fake_game_menu(SLOT); j.engine.msg_visible = True; self.assertFalse(j._esc_back(), 'un message : le menu Echap')

    def test_no_menu(self):
        j, wnd = fake_game_menu(SLOT); j.engine.active_menu = lambda: None; self.assertFalse(j._esc_back())


class ArenaMessagePage(unittest.TestCase):
    """Combat de l'arene : la seule fenetre ouverte est « Quitter » (type 71, un bouton de manette 0x400). A tourne la page du message (la fenetre n'a pas de bouton de validation) et
    la fenetre n'est pas une attente du joueur (la vitesse des combats s'applique au combat de l'arene)."""
    def game(self, buttons, grid=None, part=ENGINE.PART_BATTLE):
        j, wnd = fake_game_menu(buttons, 71, part); j.engine.ui.f[12]['grille'] = grid
        j._quit_only = functools.partial(F.Game._quit_only, j); j._wait_for_player = functools.partial(F.Game._wait_for_player, j); j.engine.ui.msg = {}
        return j

    def test_quit_alone(self):
        j = self.game([b(0, 0x400, 0, 62)]); self.assertTrue(F.without_validation(j.engine, j.ui_g, 12)); self.assertTrue(j._quit_only(12))

    def test_window_with_confirmation(self):
        j = self.game([b(0, 0x10, 0, 0), b(-1, 0x20, 200, 0)]); self.assertFalse(j._quit_only(12), 'un bouton A : la touche lui appartient')

    def test_engine_yes_no(self):
        self.assertFalse(self.game([], grid=(1, 2, 2))._quit_only(12), 'curseur du moteur (Oui / Non) : A est la sienne')

    def test_outside_battle(self):
        self.assertFalse(self.game([b(0, 0x400, 0, 62)], part=ENGINE.PART_CASINO)._quit_only(12), 'la regle ne vaut qu\'en combat')

    def test_without_menu_window(self):
        j = self.game([b(0, 0x400, 0, 62)]); j.ui_g = None; self.assertFalse(j._quit_only(12))
        j = self.game([b(0, 0x400, 0, 62)]); self.assertFalse(j._quit_only(99))

    def test_waiting_for_player(self):
        self.assertFalse(self.game([b(0, 0x400, 0, 62)])._wait_for_player(), 'arene : « Quitter » seul ouvert : le combat n\'attend personne')
        self.assertTrue(self.game([b(0, 0x10, 0, 0)])._wait_for_player(), 'menu a boutons de validation (commandes, cibles...) : attente du joueur')
        self.assertTrue(self.game([], grid=(1, 2, 2))._wait_for_player(), 'Oui / Non du moteur : attente du joueur')
        j = self.game([b(0, 0x400, 0, 62)]); j.engine.active_menu = lambda: None; self.assertFalse(j._wait_for_player())
        j.engine.msg_visible = True; j.engine.ui.msg = {'feed': True}; self.assertTrue(j._wait_for_player(), 'message avec son curseur : attente du joueur')


class MaskCode(unittest.TestCase):
    """Poker (type 48) : le code 2 de la fenetre recoit un MASQUE (63 = tout actif) ; le tableau `fx` exporte ne connait que 0 a 5."""
    def window(self, fx):
        e = {'kind': 'func', 'fx': fx}
        f = types.SimpleNamespace(N={10: {'buttonId': 0, 'act': False}, 11: {'buttonId': 1, 'act': False}, 12: {'buttonId': 5, 'act': False}, 13: {'buttonId': None, 'act': True}}, codes={2: [e]}, vals_code={}, church=False, status=False, names=False, begin=False)
        f.code = functools.partial(UI.Window.code, f); f._mask_code = functools.partial(UI.Window._mask_code, f)
        return f, e

    FX_REGULAR = {'0': {'d': {'10': {'act': False}, '11': {'act': False}, '12': {'act': False}}}, '1': {'d': {'11': {'act': False}, '12': {'act': False}}}, '2': {'d': {'10': {'act': False}, '12': {'act': False}}},
                   '3': {'d': {'12': {'act': False}}}}

    def test_mask_outside_array(self):
        f, e = self.window(self.FX_REGULAR)
        f.code(2, 63); self.assertEqual([f.N[n]['act'] for n in (10, 11, 12)], [True, True, True], '63 : toutes les zones tactiles (cartes 0, 1 et « Donner »)')
        f.code(2, 33); self.assertEqual([f.N[n]['act'] for n in (10, 11, 12)], [True, False, True], 'bits 0 et 5')
        self.assertTrue(f.N[13]['act'], 'un element hors du masque n\'est pas touche')

    def test_array_value_unchanged(self):
        f, e = self.window(self.FX_REGULAR)
        f.code(2, 1); self.assertEqual([f.N[n]['act'] for n in (10, 11, 12)], [True, False, False], 'valeur 1 du tableau : comme avant')

    def test_irregular_array_does_nothing(self):
        """Un tableau qui n'a pas la forme « bit n = bouton n » : on n'invente rien (comportement d'origine)."""
        fx = {'0': {'d': {'10': {'act': False}, '11': {'act': False}}}, '1': {'d': {'10': {'act': False}, '11': {'act': False}}}}
        f, e = self.window(fx); f.code(2, 63); self.assertEqual([f.N[n]['act'] for n in (10, 11)], [False, False])

    def test_negative_or_non_integer_value(self):
        f, e = self.window(self.FX_REGULAR)
        f.code(2, -1); f.code(2, 'x'); self.assertEqual([f.N[n]['act'] for n in (10, 11, 12)], [False, False, False])


if __name__ == '__main__':
    unittest.main(verbosity=1)
