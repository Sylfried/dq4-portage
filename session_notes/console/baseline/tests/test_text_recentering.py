"""Test du placement vertical des textes de menu (TextMesh d'Unity avec la police SE-GARRIR), logique pure, sans fenetre ni moteur :

  1. `first_line_baseline` reproduit le jeu d'origine : lignes de base mesurees sur la capture du mobile (ecran4 : bouton de cible « Rat volant » = 1 ligne, « Scarapince / x2 » = chaine « Scarapince\\n\\n\\t x2 » = 3 lignes ;
     bouton de 82 px de haut centre a y = 159,2 ; echelle 1,688 px / unite ; characterSize 9,945, lineSpacing 0,441, ancre MiddleLeft) a 0,6 unite pres ;
  2. `text_recentering` : ecart de l'encre au centre de la boite de ligne (nul pour lineSpacing >= 1, borne par DQ_TEXTE_ORIGINAL) ; apres recentrage le milieu des majuscules d'une ligne unique est a moins de 0,6 unite du point d'ancrage,
     pour tous les lineSpacing du jeu (0,441 a 1) ; le bloc de 3 lignes (« Scarapince / x2 ») est centre sur l'ancre a moins de 1 unite.

    python3 tools/test_text_recentering.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.menus import ui_menu as UM

LINE, ASCENT, CAP_HEIGHT = 23.525390625, 18.88671875, 14.0         # SE-GARRIR : interligne, ascent, hauteur des majuscules (px de police)
SCALE, CENTER_Y = 1.688, 159.2                                      # capture du mobile : px par unite, centre vertical du bouton de cible (px depuis le haut)


def units(y_px): return -(y_px - CENTER_Y) / SCALE                  # ordonnee mesuree (px, vers le bas) -> unites relatives au centre du bouton (vers le haut)


class OriginPlacement(unittest.TestCase):
    def setUp(self): self._rec = UM.TEXT_CENTERING; UM.TEXT_CENTERING = False
    def tearDown(self): UM.TEXT_CENTERING = self._rec

    def test_target_button_one_line(self):
        u = 9.945 * 0.1; step = LINE * u * 0.441
        base = UM.first_line_baseline(0.0, 1, 1, step, ASCENT * u)
        self.assertAlmostEqual(base, units(182.0), delta=0.6)       # « Rat volant » : ligne de base a y = 182 px

    def test_target_button_three_lines(self):
        u = 9.945 * 0.1; step = LINE * u * 0.441
        b1 = UM.first_line_baseline(0.0, 1, 3, step, ASCENT * u)
        self.assertAlmostEqual(b1, units(165.0), delta=0.6)         # « Scarapince » : y = 165 px
        self.assertAlmostEqual(b1 - 2 * step, units(200.0), delta=0.6)       # « x2 » (3e ligne) : y = 200 px

    def test_anchors(self):
        self.assertAlmostEqual(UM.first_line_baseline(100.0, 0, 2, 10.0, 18.0), 82.0)     # haut : le bloc pend sous l'ancre
        self.assertAlmostEqual(UM.first_line_baseline(100.0, 1, 2, 10.0, 18.0), 92.0)     # milieu
        self.assertAlmostEqual(UM.first_line_baseline(100.0, 2, 2, 10.0, 18.0), 102.0)    # bas : le bloc monte au-dessus de l'ancre


class Centering(unittest.TestCase):
    def setUp(self): self._rec = UM.TEXT_CENTERING; UM.TEXT_CENTERING = True
    def tearDown(self): UM.TEXT_CENTERING = self._rec

    def test_values(self):
        u = 9.945 * 0.1
        self.assertAlmostEqual(UM.text_recentering(LINE, u, 0.441), 6.53, delta=0.05)       # cibles : 6,5 unites (11 px a 1,688)
        self.assertAlmostEqual(UM.text_recentering(LINE, 9.393 * 0.1, 0.481), 5.73, delta=0.05)     # plaques de monstres
        self.assertAlmostEqual(UM.text_recentering(LINE, 9.945 * 0.1, 0.801), 2.34, delta=0.05)      # onglets, boutons, noms
        for ls in (1.0, 1.002, 1.258, 2.46): self.assertEqual(UM.text_recentering(LINE, u, ls), 0.0)     # PV / PM / Nv. et listes : inchange

    def test_original_option(self):
        UM.TEXT_CENTERING = False
        self.assertEqual(UM.text_recentering(LINE, 0.99, 0.441), 0.0)

    def test_a_centered_line(self):
        for ls in (0.441, 0.481, 0.801, 0.841, 0.873, 0.881, 0.962):
            for cs in (6.63, 9.393, 9.945, 10.498):
                u = cs * 0.1; step = LINE * u * ls
                base = UM.first_line_baseline(0.0, 1, 1, step, ASCENT * u) + UM.text_recentering(LINE, u, ls)
                middle = base + CAP_HEIGHT * u / 2                      # milieu des majuscules
                self.assertAlmostEqual(middle, 0.0, delta=0.6, msg=(ls, cs))

    def test_three_centered_lines(self):
        u = 9.945 * 0.1; ls = 0.441; step = LINE * u * ls
        b1 = UM.first_line_baseline(0.0, 1, 3, step, ASCENT * u) + UM.text_recentering(LINE, u, ls)
        ink_top, ink_bottom = b1 + CAP_HEIGHT * u, b1 - 2 * step       # majuscules de la 1re ligne ... ligne de base de la 3e
        self.assertAlmostEqual((ink_top + ink_bottom) / 2, 0.0, delta=1.0)
        self.assertLess(ink_top, 24.3); self.assertGreater(ink_bottom, -24.3)       # le bloc tient dans le bouton (demi-hauteur visible 24,3 unites) : « x2 » ne touche plus le bas

    def test_top_and_bottom_anchors_shifted_the_same(self):
        u = 9.393 * 0.1
        for ls in (0.801, 0.873):
            d = UM.text_recentering(LINE, u, ls)
            self.assertGreater(d, 0.0)
            topmost = UM.first_line_baseline(50.0, 0, 3, LINE * u * ls, ASCENT * u); bottom = UM.first_line_baseline(50.0, 2, 3, LINE * u * ls, ASCENT * u)
            self.assertAlmostEqual(bottom - topmost, 3 * LINE * u * ls)


if __name__ == '__main__':
    unittest.main(verbosity=2)
