"""#223 (audit CMB-02) : un effet de combat fait d'un quad plein ecran (l'effet 35, modele 5035 : teinte violette) est etire a la largeur de l'ecran quand le combat est elargi en 16/9 ; sinon il ne couvrait que le
centre 4:3 (bandes laterales non teintees). Sans fenetre ni moteur.
    python3 tests/test_full_screen_effects.py"""
import os, sys, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.battle import full_screen_effects as EPE

QUAD = np.array([[-6.45, -6.45, 5.0], [6.45, -6.45, 5.0], [6.45, 6.45, 5.0], [-6.45, 6.45, 5.0]], np.float32)       # quad de 12,9 x 12,9, a 5 unites devant la camera


class Widen(unittest.TestCase):
    def test_16_9(self):
        out = EPE.widen(QUAD, 5035, 16 / 9)
        self.assertAlmostEqual(float(out[:, 0].max() - out[:, 0].min()), 12.9 * (16 / 9) / (4 / 3), places=3)      # largeur x 4/3
        self.assertTrue(np.allclose(out[:, 1:], QUAD[:, 1:]))                                                      # hauteur et profondeur inchangees
        self.assertAlmostEqual(float(out[:, 0].mean()), 0.0, places=5)                                             # meme centre

    def test_shifted_center_kept(self):
        q = QUAD.copy(); q[:, 0] += 1.5
        out = EPE.widen(q, 5035, 16 / 9)
        self.assertAlmostEqual(float(out[:, 0].mean()), 1.5, places=4)

    def test_4_3_or_narrower_screen_unchanged(self):
        for a in (4 / 3, 1.0, 9 / 16, 0.5): self.assertIs(EPE.widen(QUAD, 5035, a), QUAD)

    def test_other_models_unchanged(self):
        for m in (5009, 5036, 5001, 100, 8905): self.assertIs(EPE.widen(QUAD, m, 16 / 9), QUAD)

    def test_does_not_modify_input(self):
        before = QUAD.copy(); EPE.widen(QUAD, 5035, 21 / 9); self.assertTrue(np.array_equal(QUAD, before))

    def test_ultra_wide(self):
        out = EPE.widen(QUAD, 5035, 21 / 9); self.assertAlmostEqual(float(out[:, 0].max() - out[:, 0].min()), 12.9 * (21 / 9) / (4 / 3), places=3)

    def test_empty_mesh(self):
        self.assertEqual(EPE.widen(np.zeros((0, 3), np.float32), 5035, 16 / 9).shape, (0, 3))


if __name__ == '__main__': unittest.main(verbosity=1)
