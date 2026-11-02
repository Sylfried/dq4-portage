"""Test du placement vertical des textes de menu (TextMesh d'Unity avec la police SE-GARRIR), logique pure, sans fenetre ni moteur :

  1. `base_premiere_ligne` reproduit le jeu d'origine : lignes de base mesurees sur la capture du mobile (ecran4 : bouton de cible « Rat volant » = 1 ligne, « Scarapince / x2 » = chaine « Scarapince\\n\\n\\t x2 » = 3 lignes ;
     bouton de 82 px de haut centre a y = 159,2 ; echelle 1,688 px / unite ; characterSize 9,945, lineSpacing 0,441, ancre MiddleLeft) a 0,6 unite pres ;

    python3 outils/test_texte_recentrage.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import ui_menu as UM

LIGNE, ASCENT, HAUT_MAJ = 23.525390625, 18.88671875, 14.0         # SE-GARRIR : interligne, ascent, hauteur des majuscules (px de police)
ECH, CENTRE_Y = 1.688, 159.2                                      # capture du mobile : px par unite, centre vertical du bouton de cible (px depuis le haut)


def unites(y_px): return -(y_px - CENTRE_Y) / ECH                  # ordonnee mesuree (px, vers le bas) -> unites relatives au centre du bouton (vers le haut)


class PlacementOrigine(unittest.TestCase):
    def test_bouton_de_cible_une_ligne(self):
        u = 9.945 * 0.1; pas = LIGNE * u * 0.441
        base = UM.base_premiere_ligne(0.0, 1, 1, pas, ASCENT * u)
        self.assertAlmostEqual(base, unites(182.0), delta=0.6)       # « Rat volant » : ligne de base a y = 182 px

    def test_bouton_de_cible_trois_lignes(self):
        u = 9.945 * 0.1; pas = LIGNE * u * 0.441
        b1 = UM.base_premiere_ligne(0.0, 1, 3, pas, ASCENT * u)
        self.assertAlmostEqual(b1, unites(165.0), delta=0.6)         # « Scarapince » : y = 165 px
        self.assertAlmostEqual(b1 - 2 * pas, unites(200.0), delta=0.6)       # « x2 » (3e ligne) : y = 200 px

    def test_ancrages(self):
        self.assertAlmostEqual(UM.base_premiere_ligne(100.0, 0, 2, 10.0, 18.0), 82.0)     # haut : le bloc pend sous l'ancre
        self.assertAlmostEqual(UM.base_premiere_ligne(100.0, 1, 2, 10.0, 18.0), 92.0)     # milieu
        self.assertAlmostEqual(UM.base_premiere_ligne(100.0, 2, 2, 10.0, 18.0), 102.0)    # bas : le bloc monte au-dessus de l'ancre


if __name__ == '__main__':
    unittest.main(verbosity=2)
