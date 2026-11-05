"""Test (#131) : un clic gauche sur le terrain libre = touche d'action ; rond central de la croix = touche d'action qui s'anime quand une action est possible (comme sur mobile).

    python3 tools/test_dpad_and_click.py

1. Moteur : le paquet 19 avec un emplacement >= 16 n'est pas ignore, c'est le clignotement de la croix (`pad_blink`) ; les vraies bulles (emplacements 0 a 15) restent inchangees.
2. Croix (`hud_mobile.Buttons`) : un TOUCHER du rond central (appui puis relachement sans en sortir) est reconnu ; un glissement (meme bref, meme s'il revient au centre) et un appui hors du rond non ; les directions ne changent pas.
3. Animation : `Buttons.action_possible` = le jeu fait clignoter la croix OU, sur le terrain libre, une bulle d'icone est affichee.
4. Fenetre (vraies methodes de `window.Game` sur un faux jeu) : clic gauche n'importe ou sur le terrain libre = touche A (`click_a`) ; clic droit = B ; ni dans un menu, ni dans un message, ni en combat ; toucher du rond central = A.
"""
import math, os, sys, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.core import engine as ENGINE

try:
    from dq4_pc.window import game as WND
except Exception as ex:          # window.py a besoin de pyglet, numpy, unicorn... (l'import seul suffit, aucune fenetre n'est creee)
    WND = None; ERROR_WND = ex


W, H = 1280, 720


class EnginePackets(unittest.TestCase):
    def apply(self, e, *packets): e.apply(list(packets), lambda: 'carte')

    def test_dpad_blink(self):
        e = ENGINE.State(); self.assertFalse(e.pad_blink)
        self.apply(e, (19, [16, 0], [])); self.assertTrue(e.pad_blink); self.assertEqual(e.icons, {})                   # ce n'est pas une bulle
        self.apply(e, (19, [16, -1], [])); self.assertFalse(e.pad_blink)
        self.apply(e, (19, [20, 3], [])); self.assertTrue(e.pad_blink)                                                  # (tout emplacement >= 16)

    def test_bubbles_unchanged(self):
        e = ENGINE.State(); self.apply(e, (19, [3, 5], []), (20, [3], [1.0, 2.0, 3.0, 0.5]))
        self.assertEqual(e.icons[3]['id'], 5); self.assertEqual(e.icons[3]['pos'], (1.0, 2.0, 3.0)); self.assertEqual(e.icons[3]['alpha'], 0.5); self.assertFalse(e.pad_blink)
        self.apply(e, (19, [3, -1], [])); self.assertEqual(e.icons, {})
        self.apply(e, (19, [15, 7], [])); self.assertIn(15, e.icons)                                                       # (15 est encore une bulle, 16 le clignotement)


def fake_game(W=1280, H=720, dpad=True):
    state = types.SimpleNamespace(part=ENGINE.PART_TOWN, effect=None, pad_blink=False)
    J = types.SimpleNamespace(width=W, height=H, reg={'boutons': True, 'croix': dpad, 'boutons_taille': 1.0, 'croix_taille': 1.0, 'boutons_pos': {}, 'boutons_aimant': False, 'bouton_vitesse': True,
                                                         'bouton_vitesse_taille': 1.0, 'bouton_vitesse_pos': []},
                              pause=types.SimpleNamespace(opened=False), map_open=False, args=types.SimpleNamespace(cache='/inexistant'))
    J.engine = types.SimpleNamespace(state=state, flags=lambda: 0x28, dpad_size=lambda: 1)
    return J


class Dpad(unittest.TestCase):
    def setUp(self):
        self.J = fake_game(); self.b = HM.Buttons(self.J); rx, ry, c, _ = self.b.rect(HM.DPAD); self.cx, self.cy, self.r = rx + c / 2, ry + c / 2, c / 2
        self.vis = (HM.DPAD,)

    def press_state(self, dx=0.0, dy=0.0): return self.b.press(self.cx + dx * self.r, self.cy + dy * self.r, self.vis)

    def test_touch_on_the_central_circle(self):
        self.assertEqual(self.press_state(), HM.DPAD); self.assertTrue(self.b.dpad_on); self.assertFalse(self.b.dpad_dragging); self.assertIsNone(self.b.dpad_sector())
        self.assertTrue(self.b.dpad_release()); self.assertFalse(self.b.dpad_on)                                       # appui puis relachement sans glisser = toucher

    def test_small_movements_in_dead_zone_remain_touch(self):
        self.press_state(); self.b.dpad_drag(self.cx + 0.05 * self.r, self.cy - 0.06 * self.r); self.assertFalse(self.b.dpad_dragging); self.assertTrue(self.b.dpad_release())

    def test_a_slide_is_not_a_touch(self):
        self.press_state(); self.b.dpad_drag(self.cx + 0.5 * self.r, self.cy); self.assertTrue(self.b.dpad_dragging); self.assertEqual(self.b.dpad_sector(), 2)         # direction : droite
        self.assertFalse(self.b.dpad_release())

    def test_a_return_to_center_after_a_slide_is_not_a_touch(self):
        self.press_state(); self.b.dpad_drag(self.cx + 0.5 * self.r, self.cy); self.b.dpad_drag(self.cx, self.cy)
        self.assertIsNone(self.b.dpad_sector()); self.assertFalse(self.b.dpad_release())

    def test_press_outside_central_circle_is_direction(self):
        self.press_state(0.0, 0.6); self.assertTrue(self.b.dpad_dragging); self.assertEqual(self.b.dpad_sector(), 0); self.assertFalse(self.b.dpad_release())                # haut

    def test_directions_unchanged(self):
        from dq4_pc.core import engine as M
        for (dx, dy), bits in (((0.5, 0.0), M.RIGHT), ((-0.5, 0.0), M.LEFT), ((0.0, 0.5), M.UP), ((0.0, -0.5), M.DOWN), ((0.5, 0.5), M.UP | M.RIGHT)):
            self.b.dpad_drop(); self.press_state(dx, dy); self.assertEqual(self.b.dpad_bits(), bits, (dx, dy))
        self.b.dpad_drop(); self.press_state(); self.assertEqual(self.b.dpad_bits(), 0)                                      # (le rond central seul n'envoie aucune direction)

    def test_release_without_press(self):
        self.assertFalse(self.b.dpad_release())

    def test_dpad_hidden(self):
        self.press_state(); self.J.reg['croix'] = False; self.assertEqual(self.b.dpad_bits(), 0); self.assertFalse(self.b.dpad_on); self.assertFalse(self.b.dpad_dragging)


@unittest.skipIf(WND is None, 'window.py non importable ici')


class Animation(unittest.TestCase):
    """`Buttons.action_possible` : la croix s'anime quand une action est realisable."""

    def hud(self, icons=None, free=True, blink=False):
        J = fake_game(); J.engine.state.icons = icons or {}; J.engine.state.pad_blink = blink; J._terrain_free = lambda: free
        return HM.Buttons(J)

    def test_no_action_possible(self): self.assertFalse(self.hud().action_possible())

    def test_a_displayed_bubble(self):
        self.assertTrue(self.hud({0: {'id': 1, 'pos': (1.0, 2.0, 3.0), 'alpha': 1.0}}).action_possible())             # (emplacement 0 compris)
        self.assertTrue(self.hud({7: {'id': 1, 'pos': (1.0, 2.0, 3.0), 'alpha': 0.5}}).action_possible())

    def test_bubble_not_yet_placed_or_transparent(self):
        self.assertFalse(self.hud({2: {'id': 1, 'pos': None, 'alpha': 1.0}}).action_possible()); self.assertFalse(self.hud({2: {'id': 1, 'pos': (0, 0, 0), 'alpha': 0.0}}).action_possible())

    def test_no_animation_outside_free_terrain(self):
        self.assertFalse(self.hud({0: {'id': 1, 'pos': (1.0, 2.0, 3.0), 'alpha': 1.0}}, free=False).action_possible())                # menu, message, combat...

    def test_game_blink_counts(self):
        self.assertTrue(self.hud(blink=True).action_possible()); self.assertTrue(self.hud(blink=True, free=False).action_possible())

    def test_dpad_drawn_without_error_without_window(self):
        self.assertFalse(self.hud().action_possible())          # (le dessin lui-meme demande un contexte GL : verifie en vrai, voir les notes de l'avance)


class InWindow(unittest.TestCase):
    """Les vraies methodes de `Game` (clic sur le terrain, relachement de la croix) sur un faux jeu."""

    def game(self, **kw):
        j = types.SimpleNamespace(**kw) if kw else types.SimpleNamespace()
        J = fake_game(); j.width, j.height, j.reg, j.engine = W, H, J.reg, J.engine
        j.engine.active_menu = lambda: None; j.engine.msg_visible = False; j.engine.state.part = ENGINE.PART_TOWN
        j.pause = J.pause; j.title_screen = None; j.license_panel = None; j.saves_screen = None; j.map_open = False; j._name_entry_in_progress = lambda: False; j._ready = True; j.ui_render = None
        j.hud = HM.Buttons(j); j.sound = types.SimpleNamespace(play_sfx=lambda *a: None); j.mouse_guard = types.SimpleNamespace(click=lambda: None, keyboard=lambda s: None)
        j.last_device = None; j.mouse = None; j.click_a = j.click_b = False; j.press_state = None; j.wheel = types.SimpleNamespace(cancel=lambda: None, in_progress=False)
        for name_str in ('_terrain_free', 'on_mouse_press', 'on_mouse_release'): setattr(j, name_str, types.MethodType(getattr(WND.Game, name_str), j))
        j._map_ports = lambda: {}; j.ref_effect = None
        return j

    def test_left_click_anywhere_gives_action_key(self):
        for x, y in ((5, 5), (640, 360), (1270, 715), (300, 600)):
            j = self.game(); j.on_mouse_press(x, y, pyglet.window.mouse.LEFT, 0); self.assertTrue(j.click_a, (x, y)); self.assertFalse(j.click_b)

    def test_right_click_stays_cancel(self):
        j = self.game(); j.on_mouse_press(640, 360, pyglet.window.mouse.RIGHT, 0); self.assertTrue(j.click_b); self.assertFalse(j.click_a)

    def test_no_action_click_outside_free_terrain(self):
        j = self.game(); j.pause.opened = True; j.pause.click = lambda *a: None; j.on_mouse_press(640, 360, pyglet.window.mouse.LEFT, 0); self.assertFalse(j.click_a)           # menu d'Echap : son propre clic
        j = self.game(); j.engine.state.part = ENGINE.PART_BATTLE; j.hud.visible_ones = lambda: (); j.on_mouse_press(640, 360, pyglet.window.mouse.LEFT, 0); self.assertFalse(j.click_a)
        j = self.game(); j.engine.active_menu = lambda: object(); j.on_mouse_press(640, 360, pyglet.window.mouse.LEFT, 0); self.assertFalse(j.click_a)                         # menu du jeu : ses boutons
        j = self.game(); j.map_open = True; j.on_mouse_press(640, 360, pyglet.window.mouse.LEFT, 0); self.assertFalse(j.click_a)

    def test_message_visible_on_next_page(self):
        j = self.game(); j.engine.msg_visible = True; j.engine.input_menus = lambda: []; j.ui_render = object(); j.on_mouse_press(640, 360, pyglet.window.mouse.LEFT, 0); self.assertTrue(j.click_a)                                        # (inchange : toucher le message)

    def test_touch_on_central_circle_gives_the_action_key(self):
        j = self.game(); rx, ry, c, _ = j.hud.rect(HM.DPAD); cx, cy = rx + c / 2, ry + c / 2
        j.on_mouse_press(int(cx), int(cy), pyglet.window.mouse.LEFT, 0); self.assertTrue(j.hud.dpad_on); self.assertFalse(j.click_a)               # l'action vient au relachement
        j.on_mouse_release(int(cx), int(cy), pyglet.window.mouse.LEFT, 0); self.assertTrue(j.click_a); self.assertFalse(j.hud.dpad_on)

    def test_sliding_on_dpad_no_action(self):
        j = self.game(); rx, ry, c, _ = j.hud.rect(HM.DPAD); cx, cy = rx + c / 2, ry + c / 2
        j.on_mouse_press(int(cx), int(cy), pyglet.window.mouse.LEFT, 0); j.hud.dpad_drag(cx + c * 0.3, cy)
        j.on_mouse_release(int(cx + c * 0.3), int(cy), pyglet.window.mouse.LEFT, 0); self.assertFalse(j.click_a)

    def test_touch_on_central_circle_in_a_menu_does_nothing(self):
        j = self.game(); rx, ry, c, _ = j.hud.rect(HM.DPAD); cx, cy = rx + c / 2, ry + c / 2
        j.on_mouse_press(int(cx), int(cy), pyglet.window.mouse.LEFT, 0); j.engine.msg_visible = True
        j.on_mouse_release(int(cx), int(cy), pyglet.window.mouse.LEFT, 0); self.assertFalse(j.click_a)                         # (un message apparu entre-temps : pas d'action fantome)


if __name__ == '__main__':
    unittest.main(verbosity=1)
