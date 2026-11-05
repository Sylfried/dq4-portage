"""Test : la croix de l'ecran fait DEUX FOIS la taille du mobile, et le heros court quand elle est tenue au bord de son anneau (04/11/2026).

    python3 tools/test_dpad_run.py

1. Taille : `hud_mobile.DPAD_DIAMETER` = 1,5 x 161,28 (le double de #169 moins 25 %, #172) ; diametre a l'ecran = H / 800 x DPAD_DIAMETER x option du jeu x reglage « Taille de la croix » (67 % = la taille du mobile).
2. Course : `Buttons.dpad_run()` vaut vrai au bord de l'anneau (TRAVEL_THRESHOLD du rayon ou plus, dans une direction), faux plus pres du centre, dans la zone morte, croix lachee ou non tenue ; la direction envoyee au jeu ne change pas.
3. Vitesse (vraie `Game._speed_factor`, faux jeu et vraie croix) : marche normale (x vitesse de marche) tant que le pointeur est dans l'anneau, x multiplicateur de l'accelerateur au bord ; la touche d'accelerateur
   fait toujours courir, et les deux ensemble ne se cumulent pas.
"""
import os, sys, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.core import engine as ENGINE
import test_dpad_and_click as TC

try:
    from dq4_pc.window import game as F
except Exception as ex:
    F = None


class Size(unittest.TestCase):
    def test_constant_is_one_and_a_half_times_mobile(self):
        self.assertAlmostEqual(HM.DPAD_DIAMETER, 1.5 * 161.28, places=6)
        self.assertAlmostEqual(HM.DPAD_DIAMETER, 0.75 * 2 * 161.28, places=6)                                 # (le double de #169, moins 25 % : #172)

    def test_diameter_on_screen(self):
        J = TC.fake_game(1280, 800); b = HM.Buttons(J)
        self.assertAlmostEqual(b.dpad_diameter(), 241.92, places=4, msg='800 de haut, option du jeu moyenne, reglage 100 % : une fois et demie le mobile')
        J.reg['croix_taille'] = 0.5; self.assertAlmostEqual(b.dpad_diameter(), 120.96, places=4, msg='reglage a 50 %')
        J.reg['croix_taille'] = 2.0; self.assertAlmostEqual(b.dpad_diameter(), 483.84, places=4)

    def test_proportional_to_height(self):
        d720 = HM.Buttons(TC.fake_game(1280, 720)).dpad_diameter(); d1080 = HM.Buttons(TC.fake_game(1920, 1080)).dpad_diameter()
        self.assertAlmostEqual(d1080 / d720, 1.5, places=6)

    def test_narrow_window_dpad_reduced_to_fit(self):
        b = HM.Buttons(TC.fake_game(394, 1102)); self.assertAlmostEqual(b.dpad_diameter(), HM.DPAD_WIDTH_MAX * 394, places=6)
        b = HM.Buttons(TC.fake_game(450, 800)); self.assertLessEqual(b.dpad_diameter(), 0.75 * 450 + 1e-6)
        b = HM.Buttons(TC.fake_game(1280, 720)); self.assertAlmostEqual(b.dpad_diameter(), 720 / 800.0 * 241.92, places=4, msg='16:9 : jamais reduite')

    def test_dpad_stays_within_screen(self):
        for W, H in ((1280, 720), (1920, 1080), (1866, 1050), (394, 1102), (3440, 1440)):
            b = HM.Buttons(TC.fake_game(W, H)); rx, ry, c, _ = b.rect(HM.DPAD)
            self.assertGreaterEqual(rx, -1e-6, (W, H)); self.assertGreaterEqual(ry, -1e-6, (W, H)); self.assertLessEqual(rx + c, W + 1e-6, (W, H)); self.assertLessEqual(ry + c, H + 1e-6, (W, H))


class Travel(unittest.TestCase):
    def setUp(self):
        self.J = TC.fake_game(); self.b = HM.Buttons(self.J); rx, ry, c, _ = self.b.rect(HM.DPAD); self.cx, self.cy, self.r = rx + c / 2, ry + c / 2, c / 2; self.vis = (HM.DPAD,)

    def hold(self, dx, dy):
        self.b.press(self.cx, self.cy, self.vis); self.b.dpad_drag(self.cx + dx * self.r, self.cy + dy * self.r)

    def test_not_held(self): self.assertFalse(self.b.dpad_run())

    def test_threshold(self):
        for radius, expected in ((0.05, False), (0.2, False), (0.5, False), (HM.TRAVEL_THRESHOLD - 0.01, False), (HM.TRAVEL_THRESHOLD, True), (1.0, True), (1.178, True), (1.6, True)):
            self.hold(0.0, radius); self.assertEqual(self.b.dpad_run(), expected, 'rayon %.3f' % radius); self.b.dpad_drop()

    def test_all_directions(self):
        import math
        for deg in range(0, 360, 15):
            self.hold(math.sin(math.radians(deg)) * 1.0, math.cos(math.radians(deg)) * 1.0); self.assertTrue(self.b.dpad_run(), deg)
            self.hold(math.sin(math.radians(deg)) * 0.5, math.cos(math.radians(deg)) * 0.5); self.assertFalse(self.b.dpad_run(), deg)

    def test_released(self):
        self.hold(0.0, 1.0); self.assertTrue(self.b.dpad_run()); self.b.dpad_drop(); self.assertFalse(self.b.dpad_run())

    def test_direction_does_not_change(self):
        self.hold(0.0, 0.5); near = self.b.dpad_bits(); self.hold(0.0, 1.0); self.assertEqual(self.b.dpad_bits(), near); self.assertEqual(near, ENGINE.UP)

    def test_central_touch_is_not_a_run(self):
        self.b.press(self.cx, self.cy, self.vis); self.assertFalse(self.b.dpad_run()); self.assertTrue(self.b.dpad_release())


def fake_walk(hud, accel_held=False, walk=1.0, accel=1.5):
    eng = types.SimpleNamespace(state=types.SimpleNamespace(part=ENGINE.PART_FIELD, effect=None, load_wait=None, transition_guard=0), msg_visible=False, active_menu=lambda: None, flags=lambda: 0x28)
    J = types.SimpleNamespace(reg={'vitesse_marche': walk, 'vitesse_accel': accel, 'vitesse_combat': 0}, engine=eng, pause=types.SimpleNamespace(opened=False), hud=hud, pad=lambda: ENGINE.UP, _held=lambda a: accel_held and a == 'accel')
    J._battle_clock = lambda: F.Game._battle_clock(J)
    return J


@unittest.skipIf(F is None, 'window.py non importable ici')
class Speed(unittest.TestCase):
    def setUp(self):
        self.J0 = TC.fake_game(); self.b = HM.Buttons(self.J0); rx, ry, c, _ = self.b.rect(HM.DPAD); self.cx, self.cy, self.r = rx + c / 2, ry + c / 2, c / 2
        self.b.press(self.cx, self.cy, (HM.DPAD,))

    def factor(self, **kw): return F.Game._speed_factor(fake_walk(self.b, **kw))

    def test_inside_ring_normal_walk(self):
        self.b.dpad_drag(self.cx, self.cy + 0.5 * self.r); self.assertEqual(self.factor(), 1.0)
        self.assertEqual(self.factor(walk=2.0), 2.0, 'la vitesse de marche du reglage reste appliquee')

    def test_run_at_edge(self):
        self.b.dpad_drag(self.cx, self.cy + 1.0 * self.r); self.assertEqual(self.factor(), 1.5); self.assertEqual(self.factor(walk=2.0), 3.0)

    def test_accelerator_key_always_valid(self):
        self.b.dpad_drag(self.cx, self.cy + 0.5 * self.r); self.assertEqual(self.factor(accel_held=True), 1.5)

    def test_no_accumulation(self):
        self.b.dpad_drag(self.cx, self.cy + 1.0 * self.r); self.assertEqual(self.factor(accel_held=True), 1.5)

    def test_dpad_released(self):
        self.b.dpad_drag(self.cx, self.cy + 1.0 * self.r); self.b.dpad_drop(); self.assertEqual(F.Game._speed_factor(fake_walk(self.b)), 1.0)


if __name__ == '__main__':
    unittest.main(verbosity=1)
