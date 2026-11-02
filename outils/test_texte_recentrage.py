"""Test du placement vertical des textes de menu (TextMesh d'Unity avec la police SE-GARRIR), logique pure, sans fenetre ni moteur :

  1. `base_premiere_ligne` reproduit le jeu d'origine : lignes de base mesurees sur la capture du mobile (ecran4 : bouton de cible « Rat volant » = 1 ligne, « Scarapince / x2 » = chaine « Scarapince\\n\\n\\t x2 » = 3 lignes ;
     bouton de 82 px de haut centre a y = 159,2 ; echelle 1,688 px / unite ; characterSize 9,945, lineSpacing 0,441, ancre MiddleLeft) a 0,6 unite pres ;
  2. `recentrage_texte` : ecart de l'encre au centre de la boite de ligne (nul pour lineSpacing >= 1, borne par DQ_TEXTE_ORIGINAL) ; apres recentrage le milieu des majuscules d'une ligne unique est a moins de 0,6 unite du point d'ancrage,
     pour tous les lineSpacing du jeu (0,441 a 1) ; le bloc de 3 lignes (« Scarapince / x2 ») est centre sur l'ancre a moins de 1 unite.

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
    def setUp(self): self._rec = UM.RECENTRAGE_TEXTE; UM.RECENTRAGE_TEXTE = False
    def tearDown(self): UM.RECENTRAGE_TEXTE = self._rec

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


class Recentrage(unittest.TestCase):
    def setUp(self): self._rec = UM.RECENTRAGE_TEXTE; UM.RECENTRAGE_TEXTE = True
    def tearDown(self): UM.RECENTRAGE_TEXTE = self._rec

    def test_valeurs(self):
        u = 9.945 * 0.1
        self.assertAlmostEqual(UM.recentrage_texte(LIGNE, u, 0.441), 6.53, delta=0.05)       # cibles : 6,5 unites (11 px a 1,688)
        self.assertAlmostEqual(UM.recentrage_texte(LIGNE, 9.393 * 0.1, 0.481), 5.73, delta=0.05)     # plaques de monstres
        self.assertAlmostEqual(UM.recentrage_texte(LIGNE, 9.945 * 0.1, 0.801), 2.34, delta=0.05)      # onglets, boutons, noms
        for ls in (1.0, 1.002, 1.258, 2.46): self.assertEqual(UM.recentrage_texte(LIGNE, u, ls), 0.0)     # PV / PM / Nv. et listes : inchange

    def test_option_originale(self):
        UM.RECENTRAGE_TEXTE = False
        self.assertEqual(UM.recentrage_texte(LIGNE, 0.99, 0.441), 0.0)

    def test_une_ligne_centree(self):
        for ls in (0.441, 0.481, 0.801, 0.841, 0.873, 0.881, 0.962):
            for cs in (6.63, 9.393, 9.945, 10.498):
                u = cs * 0.1; pas = LIGNE * u * ls
                base = UM.base_premiere_ligne(0.0, 1, 1, pas, ASCENT * u) + UM.recentrage_texte(LIGNE, u, ls)
                milieu = base + HAUT_MAJ * u / 2                      # milieu des majuscules
                self.assertAlmostEqual(milieu, 0.0, delta=0.6, msg=(ls, cs))

    def test_trois_lignes_centrees(self):
        u = 9.945 * 0.1; ls = 0.441; pas = LIGNE * u * ls
        b1 = UM.base_premiere_ligne(0.0, 1, 3, pas, ASCENT * u) + UM.recentrage_texte(LIGNE, u, ls)
        haut_encre, bas_encre = b1 + HAUT_MAJ * u, b1 - 2 * pas       # majuscules de la 1re ligne ... ligne de base de la 3e
        self.assertAlmostEqual((haut_encre + bas_encre) / 2, 0.0, delta=1.0)
        self.assertLess(haut_encre, 24.3); self.assertGreater(bas_encre, -24.3)       # le bloc tient dans le bouton (demi-hauteur visible 24,3 unites) : « x2 » ne touche plus le bas

    def test_ancrage_haut_et_bas_decales_pareil(self):
        u = 9.393 * 0.1
        for ls in (0.801, 0.873):
            d = UM.recentrage_texte(LIGNE, u, ls)
            self.assertGreater(d, 0.0)
            haut = UM.base_premiere_ligne(50.0, 0, 3, LIGNE * u * ls, ASCENT * u); bas = UM.base_premiere_ligne(50.0, 2, 3, LIGNE * u * ls, ASCENT * u)
            self.assertAlmostEqual(bas - haut, 3 * LIGNE * u * ls)


if __name__ == '__main__':
    unittest.main(verbosity=2)
