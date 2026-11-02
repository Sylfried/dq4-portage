"""Test de la camera de l'ecran-titre (carte ev01), sans fenetre ni moteur : `Jeu._camera_ville` est appelee sur un faux objet, comme dans test_camera_ville.py.

  1. le titre est SANS heros (le moteur charge pourtant le sprite 0, cache) : la scene est celle de l'original, champ horizontal fixe (fov x 4/3) a l'ecran portrait 0,5625 ; la formule « le heros prend une fraction de la
     hauteur » ne s'y applique pas (avant : zoom de 1,185, logo plus large que la zone portrait) ;
  2. la meme camera, une fois la fenetre elargie, garde la zone portrait du milieu 1 pour 1 : un point de la scene projete a la meme distance (en pixels) du centre, a la meme hauteur, en 1280 x 720 (zone 405 x 720)
     et dans une fenetre portrait 405 x 720 ;
  3. une carte de ville ordinaire garde le zoom commun du heros (la correction ne vaut que pour ev01) ;
  4. (retour de 22 h 29 : « le logo et le decor ne sont plus centres ») le titre est CENTRE a toute taille de fenetre : la cible de la camera (le milieu de la scene, x = 0) reste au milieu de l'image
     quelle que soit l'option « Centrer la camera sur le joueur » (Oui / Non), meme avec les bornes de la carte (en 16/9 la camera glissait de +4,5 u vers leur milieu : 15 % de la largeur) et meme si le
     sprite du heros garde une position perimee ; une carte ordinaire garde ses bornes 16/9 (l'exception ne vaut que pour ev01).

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

    # ---- retour de 22 h 29 : le titre doit etre centre, a toute taille de fenetre, quel que soit le reglage « Centrer la camera »
    BORNES = (-7.0, 16.0)          # bornes en x de la carte ev01 mesurees dans la visionneuse (ciel, logo, ile : leur milieu est a x = 4,5, pas a la camera du jeu, x = 0)
    ASPECTS = (('portrait 9:16', 405 / 720), ('4:3', 1024 / 768), ('16:10', 1280 / 800), ('16:9', 1280 / 720), ('1430 x 815', 1430 / 815), ('21:9', 2560 / 1080), ('32:9', 32 / 9))

    def vue_bornee(self, carte, sprites, aspect, option, bornes=BORNES):
        j = T.faux_jeu(option=option, bornes_x=bornes); j.carte_nom = carte
        e = T.faux_etat(CIB, CIB, 10.0); e.cam_pos = POS; e.cam_bas = 3.019360065460205; e.cam_far = 150.0; e.sprites = sprites
        return F.Jeu._camera_ville(j, e, aspect)[0]

    def test_titre_centre_a_toute_taille_et_tout_reglage(self):
        """La cible du jeu (l'origine, au milieu du logo) est au milieu de l'image (NDC x = 0) et la matrice ne depend ni des bornes de la carte ni de l'option : a toute taille de fenetre."""
        for sprites in ({}, {0: {'pos': (0.0, 0.0, 0.0)}}, {0: {'pos': (9.0, 0.0, -4.0)}}):          # (le dernier : position perimee du heros d'une partie precedente, a 10 u de la cible)
            for nom, asp in self.ASPECTS:
                ref = self.vue_bornee('ev01', sprites, asp, False, bornes=None)
                for option in (True, False):
                    M = self.vue_bornee('ev01', sprites, asp, option)
                    self.assertAlmostEqual(T.ndc(M, CIB)[0], 0.0, places=9, msg='%s option=%s heros=%s' % (nom, option, sprites))
                    self.assertLess(float(np.abs(M - ref).max()), 1e-12, '%s option=%s heros=%s' % (nom, option, sprites))

    def test_titre_symetrique_a_gauche_et_a_droite(self):
        """Deux points de la scene symetriques par rapport au plan vertical de la camera (x = +/- a, meme profondeur) donnent des NDC x opposes : rien ne penche d'un cote, a aucune taille."""
        for nom, asp in self.ASPECTS:
            M = self.vue_bornee('ev01', {}, asp, False)
            for a in (1.0, 3.0, 6.0):
                xg, xd = T.ndc(M, np.array([-a, 0.0, 0.0]))[0], T.ndc(M, np.array([a, 0.0, 0.0]))[0]
                self.assertAlmostEqual(xg + xd, 0.0, places=9, msg='%s a=%s' % (nom, a))

    def test_une_carte_ordinaire_garde_ses_bornes(self):
        """Controle du test : sur une autre carte, les memes bornes et l'option sur Non deplacent bien la camera en large (la correction ne vaut que pour le titre)."""
        for nom, asp in self.ASPECTS[3:6]:
            lib = self.vue_bornee('ville', {}, asp, False, bornes=None); bor = self.vue_bornee('ville', {}, asp, False)
            self.assertGreater(abs(T.ndc(bor, CIB)[0]), 0.05, nom)                                    # la cible n'est plus au milieu : les bornes ont glisse la camera
            self.assertLess(float(np.abs(lib - self.vue_bornee('ville', {}, asp, True)).max()), 1e-12, nom)      # option Oui : aucune borne, comme sans bornes


if __name__ == '__main__':
    unittest.main()
