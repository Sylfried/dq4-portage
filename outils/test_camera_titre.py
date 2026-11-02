"""Test de la camera de l'ecran-titre (carte ev01), sans fenetre ni moteur : `Jeu._camera_ville` est appelee sur un faux objet, comme dans test_camera_ville.py.

  1. le titre est SANS heros (le moteur charge pourtant le sprite 0, cache) : la scene est celle de l'original, champ horizontal fixe (fov x 4/3) a l'ecran portrait 0,5625 ; la formule « le heros prend une fraction de la
     hauteur » ne s'y applique pas (avant : zoom de 1,185, logo plus large que la zone portrait) ;
  2. la meme camera, une fois la fenetre elargie, garde la zone portrait du milieu 1 pour 1 : un point de la scene projete a la meme distance (en pixels) du centre, a la meme hauteur, en 1280 x 720 (zone 405 x 720)
     et dans une fenetre portrait 405 x 720 ;
  3. une carte de ville ordinaire garde le zoom commun du heros (la correction ne vaut que pour ev01).

    python3 outils/test_camera_titre.py
"""
import os, sys, unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_camera_ville as T
F = T.F

POS = (0.0, 27.7041015625, -34.181640625)          # camera du titre relevee dans le moteur (image 400)
CIB = (0.0, 0.0, 0.0)
POINTS = [np.array(p, float) for p in ((0, 0, 0), (2, 0, 3), (-3, 1, -2), (4, 2, 8), (-4, 0.5, 6))]     # points de la scene du titre (logo, ile, dragon)


def vue(carte, sprites, aspect):
    j = T.faux_jeu(option=False); j.carte_nom = carte
    e = T.faux_etat(CIB, CIB, 10.0); e.cam_pos = POS; e.cam_bas = 3.019360065460205; e.cam_far = 150.0; e.sprites = sprites
    return F.Jeu._camera_ville(j, e, aspect)[0]


class TestCameraTitre(unittest.TestCase):
    def setUp(self):
        T.HORLOGE[0] = 0.0; self.temps_avant = F.time
        F.time = T.types.SimpleNamespace(perf_counter=lambda: T.HORLOGE[0], time=lambda: T.HORLOGE[0], sleep=lambda *a: None)

    def tearDown(self): F.time = self.temps_avant

    def test_titre_champ_fixe_malgre_le_heros_cache(self):
        ref = T.unity_ndc(POS, CIB, 10.0, F.VILLE_NEAR, 150.0, 0.0, F.ASPECT_PORTRAIT, POINTS, bas=3.019360065460205)
        for sprites in ({}, {0: {'pos': (0.0, 0.0, 0.0)}}):                                  # sans sprite, et avec le sprite 0 charge mais cache
            M = vue('ev01', sprites, F.ASPECT_PORTRAIT)
            pire = float(np.abs(np.array([T.ndc(M, p) for p in POINTS]) - ref).max())
            self.assertLess(pire, 1e-9, sprites)

    def test_zone_portrait_identique_en_large(self):
        """x de la fenetre large : (ndc x) x (largeur / 2) = distance au centre en pixels ; y : ndc y x (hauteur / 2). La zone portrait de 1280 x 720 est la fenetre portrait 405 x 720."""
        Mp, Ml = vue('ev01', {0: {'pos': (0.0, 0.0, 0.0)}}, 405 / 720), vue('ev01', {0: {'pos': (0.0, 0.0, 0.0)}}, 1280 / 720)
        for p in POINTS:
            xp, yp = T.ndc(Mp, p); xl, yl = T.ndc(Ml, p)
            self.assertAlmostEqual(xp * 405 / 2, xl * 1280 / 2, places=6); self.assertAlmostEqual(yp * 720 / 2, yl * 720 / 2, places=6)

    def test_ville_ordinaire_garde_le_zoom_du_heros(self):
        sprites = {0: {'pos': (0.0, 0.0, 0.0)}}
        Mv, Mt = vue('ville', sprites, F.ASPECT_PORTRAIT), vue('ev01', sprites, F.ASPECT_PORTRAIT)
        self.assertGreater(float(np.abs(Mv - Mt).max()), 1e-3)                                  # zoom commun du heros (autre champ vertical) hors du titre


if __name__ == '__main__':
    unittest.main()
