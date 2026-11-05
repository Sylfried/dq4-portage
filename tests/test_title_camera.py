"""Test de la camera de l'ecran-titre (carte ev01), sans fenetre ni moteur : `Game._town_camera` est appelee sur un faux objet, comme dans test_town_camera.py.

  1. le titre est NO_DEFAULT heros (le moteur charge pourtant le sprite 0, cache) : la scene est celle de l'original, champ horizontal fixe (fov x 4/3) a l'ecran portrait 0,5625 ; la formule « le heros prend une fraction de la
     hauteur » ne s'y applique pas (avant : zoom de 1,185, logo plus large que la zone portrait) ;
  2. la meme camera, une fois la fenetre elargie, garde la zone portrait du milieu 1 pour 1 : un point de la scene projete a la meme distance (en pixels) du centre, a la meme hauteur, en 1280 x 720 (zone 405 x 720)
     et dans une fenetre portrait 405 x 720 ;
  3. (retour de 22 h 29 : « le logo et le decor ne sont plus centres ») le titre est CENTRE a toute taille de fenetre : la cible de la camera (le milieu de la scene, x = 0) reste au milieu de l'image, meme si le sprite
     du heros garde une position perimee. Depuis #264 la camera de TOUTES les cartes est celle du jeu (plus de zoom commun du heros, ni de centrage, ni de reste d'une partie precedente).

    python3 tests/test_title_camera.py
"""
import os, sys, unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import test_town_camera as T
F = T.F

POS = (0.0, 27.7041015625, -34.181640625)          # camera du titre relevee dans le moteur (image 400)
TARGET = (0.0, 0.0, 0.0)
POINTS = [np.array(p, float) for p in ((0, 0, 0), (2, 0, 3), (-3, 1, -2), (4, 2, 8), (-4, 0.5, 6))]     # points de la scene du titre (logo, ile, dragon)


def make_view(game_map, sprites, aspect):
    j = T.fake_game(); j.map_name = game_map
    e = T.fake_state(TARGET, TARGET, 10.0); e.cam_pos = POS; e.cam_down = 3.019360065460205; e.cam_far = 150.0; e.sprites = sprites
    return F.Game._town_camera(j, e, aspect)[0]


class TestTitleCamera(unittest.TestCase):
    def test_title_field_of_view_fixed_despite_hidden_hero(self):
        ref = T.unity_ndc(POS, TARGET, 10.0, F.TOWN_NEAR, 150.0, 0.0, F.ASPECT_PORTRAIT, POINTS, bottom=3.019360065460205)
        for sprites in ({}, {0: {'pos': (0.0, 0.0, 0.0)}}):                                  # sans sprite, et avec le sprite 0 charge mais cache
            M = make_view('ev01', sprites, F.ASPECT_PORTRAIT)
            worst = float(np.abs(np.array([T.ndc(M, p) for p in POINTS]) - ref).max())
            self.assertLess(worst, 1e-9, sprites)

    def test_portrait_zone_identical_in_wide(self):
        """x de la fenetre large : (ndc x) x (largeur / 2) = distance au centre en pixels ; y : ndc y x (hauteur / 2). La zone portrait de 1280 x 720 est la fenetre portrait 405 x 720."""
        Mp, Ml = make_view('ev01', {0: {'pos': (0.0, 0.0, 0.0)}}, 405 / 720), make_view('ev01', {0: {'pos': (0.0, 0.0, 0.0)}}, 1280 / 720)
        for p in POINTS:
            xp, yp = T.ndc(Mp, p); xl, yl = T.ndc(Ml, p)
            self.assertAlmostEqual(xp * 405 / 2, xl * 1280 / 2, places=6); self.assertAlmostEqual(yp * 720 / 2, yl * 720 / 2, places=6)

    # ---- retour de 22 h 29 : le titre doit etre centre, a toute taille de fenetre (la camera est toujours centree sur le heros : le titre, sans heros, est exempte)
    ASPECTS = (('portrait 9:16', 405 / 720), ('4:3', 1024 / 768), ('16:10', 1280 / 800), ('16:9', 1280 / 720), ('1430 x 815', 1430 / 815), ('21:9', 2560 / 1080), ('32:9', 32 / 9))

    def hero_view(self, game_map, sprites, aspect):
        j = T.fake_game(); j.map_name = game_map
        e = T.fake_state(TARGET, TARGET, 10.0); e.cam_pos = POS; e.cam_down = 3.019360065460205; e.cam_far = 150.0; e.sprites = sprites
        return F.Game._town_camera(j, e, aspect)[0]

    def test_title_centered_at_any_size(self):
        """La cible du jeu (l'origine, au milieu du logo) est au milieu de l'image (NDC x = 0), meme avec un sprite 0 perime d'une partie precedente a 10 u de la cible (le centrage sur le heros ne vaut pas pour le titre)."""
        for sprites in ({}, {0: {'pos': (0.0, 0.0, 0.0)}}, {0: {'pos': (9.0, 0.0, -4.0)}}):
            ref = self.hero_view('ev01', {}, 16 / 9)
            for name_str, asp in self.ASPECTS:
                M = self.hero_view('ev01', sprites, asp)
                self.assertAlmostEqual(T.ndc(M, TARGET)[0], 0.0, places=9, msg='%s heros=%s' % (name_str, sprites))
                self.assertLess(float(np.abs(M - self.hero_view('ev01', {}, asp)).max()), 1e-12, '%s heros=%s' % (name_str, sprites))
            self.assertEqual(ref.shape, (4, 4))

    def test_title_symmetric_left_and_right(self):
        """Deux points de la scene symetriques par rapport au plan vertical de la camera (x = +/- a, meme profondeur) donnent des NDC x opposes : rien ne penche d'un cote, a aucune taille."""
        for name_str, asp in self.ASPECTS:
            M = self.hero_view('ev01', {}, asp)
            for a in (1.0, 3.0, 6.0):
                xg, xd = T.ndc(M, np.array([-a, 0.0, 0.0]))[0], T.ndc(M, np.array([a, 0.0, 0.0]))[0]
                self.assertAlmostEqual(xg + xd, 0.0, places=9, msg='%s a=%s' % (name_str, a))


if __name__ == '__main__':
    unittest.main()
