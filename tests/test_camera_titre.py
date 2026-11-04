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
import _chemins          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import test_camera_ville as T
F = T.F

POS = (0.0, 27.7041015625, -34.181640625)          # camera du titre relevee dans le moteur (image 400)
CIB = (0.0, 0.0, 0.0)
POINTS = [np.array(p, float) for p in ((0, 0, 0), (2, 0, 3), (-3, 1, -2), (4, 2, 8), (-4, 0.5, 6))]     # points de la scene du titre (logo, ile, dragon)


def vue(carte, sprites, aspect):
    j = T.faux_jeu(); j.carte_nom = carte
    e = T.faux_etat(CIB, CIB, 10.0); e.cam_pos = POS; e.cam_bas = 3.019360065460205; e.cam_far = 150.0; e.sprites = sprites
    return F.Jeu._camera_ville(j, e, aspect)[0]


class TestCameraTitre(unittest.TestCase):
    def setUp(self):
        T.HORLOGE[0] = 0.0; self.remettre_temps = _chemins.poser_global('time', T.types.SimpleNamespace(perf_counter=lambda: T.HORLOGE[0], time=lambda: T.HORLOGE[0], sleep=lambda *a: None))

    def tearDown(self): self.remettre_temps()

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

    # ---- retour de 22 h 29 : le titre doit etre centre, a toute taille de fenetre (la camera est toujours centree sur le heros : le titre, sans heros, est exempte)
    ASPECTS = (('portrait 9:16', 405 / 720), ('4:3', 1024 / 768), ('16:10', 1280 / 800), ('16:9', 1280 / 720), ('1430 x 815', 1430 / 815), ('21:9', 2560 / 1080), ('32:9', 32 / 9))

    def vue_heros(self, carte, sprites, aspect):
        j = T.faux_jeu(); j.carte_nom = carte
        e = T.faux_etat(CIB, CIB, 10.0); e.cam_pos = POS; e.cam_bas = 3.019360065460205; e.cam_far = 150.0; e.sprites = sprites
        return F.Jeu._camera_ville(j, e, aspect)[0]

    def test_titre_centre_a_toute_taille(self):
        """La cible du jeu (l'origine, au milieu du logo) est au milieu de l'image (NDC x = 0), meme avec un sprite 0 perime d'une partie precedente a 10 u de la cible (le centrage sur le heros ne vaut pas pour le titre)."""
        for sprites in ({}, {0: {'pos': (0.0, 0.0, 0.0)}}, {0: {'pos': (9.0, 0.0, -4.0)}}):
            ref = self.vue_heros('ev01', {}, 16 / 9)
            for nom, asp in self.ASPECTS:
                M = self.vue_heros('ev01', sprites, asp)
                self.assertAlmostEqual(T.ndc(M, CIB)[0], 0.0, places=9, msg='%s heros=%s' % (nom, sprites))
                self.assertLess(float(np.abs(M - self.vue_heros('ev01', {}, asp)).max()), 1e-12, '%s heros=%s' % (nom, sprites))
            self.assertEqual(ref.shape, (4, 4))

    def test_titre_symetrique_a_gauche_et_a_droite(self):
        """Deux points de la scene symetriques par rapport au plan vertical de la camera (x = +/- a, meme profondeur) donnent des NDC x opposes : rien ne penche d'un cote, a aucune taille."""
        for nom, asp in self.ASPECTS:
            M = self.vue_heros('ev01', {}, asp)
            for a in (1.0, 3.0, 6.0):
                xg, xd = T.ndc(M, np.array([-a, 0.0, 0.0]))[0], T.ndc(M, np.array([a, 0.0, 0.0]))[0]
                self.assertAlmostEqual(xg + xd, 0.0, places=9, msg='%s a=%s' % (nom, a))

    def test_titre_sans_reste_d_une_partie_precedente(self):
        """Retour au titre apres une partie jouee : camera tournee (lacet, angle), zoom de distance, reste de centrage, heros ailleurs : rien de tout cela ne decale ni ne tourne la camera du titre (le cadrage est celui du jeu)."""
        for nom, asp in self.ASPECTS[1:6]:
            ref = self.vue_heros('ev01', {}, asp)
            j = T.faux_jeu(jeu=False); j.carte_nom = 'ev01'; j.lacet = 40.0; j.angle_cam = -12.0; j.zoom = 2.5
            j.cam_dec = [3.0, -2.0]; j.cam_res = [1.0, 1.0]; j.cam_centre = True; j.cam_saut = False
            e = T.faux_etat(CIB, CIB, 10.0); e.cam_pos = POS; e.cam_bas = 3.019360065460205; e.cam_far = 150.0; e.sprites = {0: {'pos': (20.0, 0.0, 15.0)}}
            M = F.Jeu._camera_ville(j, e, asp)[0]
            self.assertLess(float(np.abs(M - ref).max()), 1e-12, nom)

    def test_une_carte_ordinaire_reste_centree_sur_le_heros(self):
        """Controle du test : sur une autre carte, un heros a cote de la cible du jeu est ramene au milieu de l'image (centrage permanent), ce que le titre n'a pas."""
        for nom, asp in self.ASPECTS[3:6]:
            M = self.vue_heros('ville', {0: {'pos': (3.0, 0.0, 0.0)}}, asp)
            self.assertAlmostEqual(T.ndc(M, (3.0, 0.0, 0.0))[0], 0.0, places=2, msg=nom)


if __name__ == '__main__':
    unittest.main()
