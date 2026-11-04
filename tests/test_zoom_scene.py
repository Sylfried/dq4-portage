"""Test du zoom des scenes (UNI-08, choix du joueur du 04/11 : « le jeu l'emporte dans ses scenes, et au debut de la scene une transition remet le zoom par defaut, comme la remise a zero au clavier ou a la souris »).

  1. Debut de scene (`Jeu._suivre_scene`) : quand le jeu prend la camera (TownCamera verrouillee et menee ailleurs, ou camera libre d'une scene), le zoom du joueur revient a 100 % par l'animation de la remise a zero
     (progressive, jamais d'a-coup, meme vitesse), meme sous un message ; rien si le zoom est deja a 100 % ; jamais sur l'ecran-titre ni hors des villes ; une nouvelle scene la relance.
  2. Pendant la scene le jeu l'emporte : la molette, les touches de distance et Ctrl + molette ne reglent plus le zoom ; la transition en cours n'est pas interrompue par une touche ; elle se poursuit apres la scene.
     Le menu Echap (le joueur regle sa distance) ou la sortie du terrain l'arretent.
  3. Cadrage (`Jeu._camera_ville`) : hors scene, le heros garde la meme taille a l'ecran quelle que soit la distance de la camera du jeu (zoom commun, inchange) ; pendant la scene le champ du jeu s'applique tel quel
     (un travelling avant grossit le heros, comme sur le mobile) ; le passage de l'un a l'autre est progressif, sans a-coup, immediat apres une coupure, et revient de meme a la fin de la scene.

    python3 tests/test_zoom_scene.py
"""
import math, os, sys, types, unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _chemins          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
pyglet.options['shadow_window'] = False
from dq4_pc.persistance import reglages as RG
from dq4_pc.fenetre import jeu as FE

MO = FE.MO
J = FE.Jeu
ASPECT = 16.0 / 9.0


class Faux:
    """Un `Jeu` minimal : les vraies methodes de fenetre.Jeu liees a cet objet (terrain libre d'une ville, camera a 100 %)."""
    def __init__(self, distance=100, partie=None, cam_jeu=False, libre=False):
        self.moteur = types.SimpleNamespace(etat=types.SimpleNamespace(partie=MO.PARTIE_VILLE if partie is None else partie, effet=None, cam_libre=libre), msg_visible=False, menu_actif=lambda: None)
        self.pause = types.SimpleNamespace(ouvert=False); self.licence = None; self.sauv = None; self.titre = None; self._saisie_nom_en_cours = lambda: False; self.carte_ouverte = False; self.carte_nom = 'mlb1a'
        self.reg = RG.Reglages(None); self.reg['distance_camera'] = distance; self.zoom = 100.0 / distance; self.fixe_test = True; self._pret = True; self.tenues = set(); self._t_dist = None
        self.dist_retour = False; self.dist_bloque = False; self.dist_scene = False; self.scene_prec = False; self.cam_jeu = cam_jeu; self.cam_axe = {'lacet': [False, False], 'angle': [False, False]}
        for nom in ('_zoom_possible', 'regler_zoom', 'regler_distance', '_maj_distance_clavier', 'distance_par_defaut', '_transition_scene_possible', '_scene_en_cours', '_suivre_scene', 'on_mouse_scroll'):
            setattr(self, nom, types.MethodType(getattr(J, nom), self))
        self._zoom_valide = J._zoom_valide; self._tenue = lambda a: a in self.tenues; self._ctrl_actif = lambda m: False

    @property
    def etat(self): return self.moteur.etat

    @property
    def distance(self): return 100.0 / self.zoom

    def images(self, n, *touches):
        self.tenues = set(touches); out = []
        for _ in range(n): self._suivre_scene(self.etat); self._maj_distance_clavier(); out.append(self.distance)
        return out


class DebutDeScene(unittest.TestCase):
    def test_le_debut_d_une_scene_lance_le_retour_a_100(self):
        j = Faux(distance=160); self.assertFalse(j.dist_retour)
        j.cam_jeu = True; j._suivre_scene(j.etat); self.assertTrue(j.dist_retour); self.assertTrue(j.dist_scene); self.assertEqual(j.distance, 160.0)          # (rien n'est immediat : c'est une animation)
        d = j.images(120); self.assertEqual(j.distance, 100.0); self.assertEqual(j.reg['distance_camera'], 100); self.assertFalse(j.dist_retour); self.assertFalse(j.dist_scene)

    def test_transition_progressive_et_monotone(self):
        for depart in (200, 150, 70, 50):
            j = Faux(distance=depart, cam_jeu=True); d = j.images(120); sens = 1 if depart > 100 else -1
            self.assertEqual(j.distance, 100.0, depart)
            suite = [float(depart)] + d; self.assertTrue(all((b - a) * sens <= 1e-9 for a, b in zip(suite, suite[1:])), depart)                    # jamais de depassement ni de retour en arriere
            self.assertGreater(sum(1 for x in d if x not in (100.0,)), 4, depart)                                                                       # plusieurs images : pas un saut
            self.assertLessEqual(max(abs(b - a) for a, b in zip(suite, suite[1:])), max(FE.CAM_RECENTRE_DIST, 5.0 * abs(depart - 100.0)) / 60.0 + 1e-9, depart)   # meme vitesse que la remise a zero

    def test_meme_animation_que_la_remise_a_zero_au_clavier(self):
        a = Faux(distance=150, cam_jeu=True).images(60); b = Faux(distance=150); b.distance_par_defaut(); c = b.images(60)
        self.assertEqual(a, c)

    def test_deja_a_100_rien_ne_se_lance(self):
        j = Faux(distance=100, cam_jeu=True); j._suivre_scene(j.etat); self.assertFalse(j.dist_retour); self.assertFalse(j.dist_scene)

    def test_la_scene_continue_sans_relancer(self):
        j = Faux(distance=150, cam_jeu=True); j.images(120); self.assertEqual(j.distance, 100.0)
        j.regler_distance(130.0); j.images(10); self.assertEqual(round(j.distance), 130, 'la scene dure : pas de nouvelle remise a 100 % (un seul debut)')            # (zoom reglable par le menu Echap meme pendant : pas de rebond ici)
        j.cam_jeu = False; j._suivre_scene(j.etat); j.cam_jeu = True; j._suivre_scene(j.etat); self.assertTrue(j.dist_retour)                              # (une nouvelle scene : nouveau retour)

    def test_camera_libre_d_une_scene_compte(self):
        j = Faux(distance=150, libre=True); j._suivre_scene(j.etat); self.assertTrue(j.dist_retour)

    def test_ni_le_titre_ni_hors_des_villes(self):
        j = Faux(distance=150, cam_jeu=True); j.carte_nom = FE.CARTE_TITRE; j._suivre_scene(j.etat); self.assertFalse(j.dist_retour)
        j = Faux(distance=150, partie=MO.PARTIE_CHAMP, cam_jeu=True); j._suivre_scene(j.etat); self.assertFalse(j.dist_retour)
        j = Faux(distance=150, partie=MO.PARTIE_COMBAT, cam_jeu=True); j._suivre_scene(j.etat); self.assertFalse(j.dist_retour)

    def test_sous_un_message_la_transition_va_a_son_terme(self):
        j = Faux(distance=150, cam_jeu=True); j.moteur.msg_visible = True; d = j.images(120); self.assertEqual(d[-1], 100.0)                       # (les scenes affichent des messages : la transition ne s'arrete pas)


class LeJeuL_Emporte(unittest.TestCase):
    def test_zoom_bloque_pendant_la_scene(self):
        self.assertTrue(Faux()._zoom_possible()); self.assertFalse(Faux(cam_jeu=True)._zoom_possible())
        j = Faux(distance=100, cam_jeu=True); j.on_mouse_scroll(0, 0, 0, 3); self.assertEqual(j.distance, 100.0)                                    # molette : sans effet
        j.images(10, 'cam_loin'); self.assertEqual(j.distance, 100.0)                                                                                 # touche « Eloigner » : sans effet
        j.images(10, 'cam_pres', 'cam_loin'); self.assertEqual(j.distance, 100.0)

    def test_touche_ou_molette_n_interrompt_pas_la_transition(self):
        j = Faux(distance=170, cam_jeu=True); j.images(3); d0 = j.distance; self.assertTrue(j.dist_scene)
        j.images(4, 'cam_pres'); self.assertTrue(j.dist_retour); self.assertLess(j.distance, d0)                                                       # (la touche n'arrete rien)
        j.on_mouse_scroll(0, 0, 0, -3); self.assertTrue(j.dist_retour)
        j.images(120, 'cam_loin'); self.assertEqual(j.distance, 100.0)

    def test_la_transition_se_poursuit_apres_la_scene(self):
        j = Faux(distance=200, cam_jeu=True); j.images(3); j.cam_jeu = False; d = j.images(120); self.assertEqual(d[-1], 100.0)
        j.images(10, 'cam_loin'); self.assertGreater(j.distance, 100.0)                                                                                 # (hors scene, les touches reglent de nouveau la distance)

    def test_menu_echap_arrete_la_transition(self):
        j = Faux(distance=200, cam_jeu=True); j.images(3); d = j.distance; j.pause.ouvert = True; j.images(5)
        self.assertEqual(j.distance, d); self.assertFalse(j.dist_retour); self.assertFalse(j.dist_scene)                                              # (le joueur regle lui-meme sa distance dans le menu)

    def test_sortie_du_terrain_arrete_la_transition(self):
        j = Faux(distance=200, cam_jeu=True); j.images(3); d = j.distance; j.etat.partie = MO.PARTIE_COMBAT; j.images(5)
        self.assertEqual(j.distance, d); self.assertFalse(j.dist_retour); self.assertFalse(j.dist_scene)


# ---- cadrage : taille du heros a l'ecran selon la distance de la camera du jeu
def faux_jeu(cam_jeu, zoom=1.0):
    j = types.SimpleNamespace(zoom=zoom, reg={}, cam_jeu=cam_jeu, cam_saut=True, cam_dec=[0.0, 0.0], cam_res=[0.0, 0.0], cam_centre=False, cam_ref_y=None, t_centre=None, fixe_test=True,
                              bornes_x=None, lacet=0.0, angle_cam=0.0, cam_bloquee=False, carte_nom='mlb1a', n_boucle=0, _cadre_vue=None)
    j._rot_camera = lambda e: FE.rot_unity(0.0, 0.0, 0.0) if e.cam_rot is None else FE.rot_unity(*[-e.cam_rot[0], -(e.cam_rot[1] + 180.0), e.cam_rot[2]])
    return j


def faux_etat(dist_rel):
    """Ville dont la camera du jeu est a `dist_rel` x la distance habituelle, heros a l'origine."""
    cib = np.zeros(3)
    return types.SimpleNamespace(cam_pos=cib + np.array([0.0, 28.94, -27.0]) * dist_rel, cam_cible=cib, cam_fov=None, cam_near=None, cam_far=None, cam_yoff=None, cam_bas=None, cam_libre=False, cam_rot=None,
                                 sprites={0: {'pos': (0.0, 0.0, 0.0)}}, partie=MO.PARTIE_VILLE)


def hauteur_heros(M):
    """Hauteur du panneau du heros a l'ecran (coordonnees normalisees, 2 = toute la fenetre)."""
    h = FE.SPRITE_H * FE.SPRITE_ECHELLE
    def y(p): c = M @ np.array([p[0], p[1], p[2], 1.0]); return c[1] / c[3]
    return y((0.0, h, 0.0)) - y((0.0, 0.0, 0.0))


class Cadrage(unittest.TestCase):
    def hauteur(self, cam_jeu, dist_rel, zoom=1.0):
        j = faux_jeu(cam_jeu, zoom); M, _ = J._camera_ville(j, faux_etat(dist_rel), ASPECT); return hauteur_heros(M), j

    def test_hors_scene_le_heros_garde_sa_taille(self):
        a, _ = self.hauteur(False, 1.0); b, _ = self.hauteur(False, 0.7); c, _ = self.hauteur(False, 1.4)
        self.assertAlmostEqual(b / a, 1.0, delta=0.03); self.assertAlmostEqual(c / a, 1.0, delta=0.03)                                                 # zoom commun inchange

    def test_pendant_la_scene_le_champ_du_jeu_s_applique(self):
        a, _ = self.hauteur(True, 1.0); b, _ = self.hauteur(True, 0.7); c, _ = self.hauteur(True, 1.4)
        self.assertAlmostEqual(b / a, 1 / 0.7, delta=0.1); self.assertAlmostEqual(c / a, 1 / 1.4, delta=0.06)                                         # une camera plus proche grossit le heros, plus loin le rapetisse (travelling)
        self.assertGreater(b, a); self.assertGreater(a, c)

    def test_a_la_distance_habituelle_scene_et_hors_scene_se_confondent(self):
        a, _ = self.hauteur(False, 1.0); b, _ = self.hauteur(True, 1.0)
        self.assertAlmostEqual(a / b, 1.0, delta=0.02)                                                                                                  # (HEROS_FRAC est calcule sur la distance habituelle : aucun saut au declenchement d'une scene ordinaire)

    def test_apres_une_coupure_le_champ_du_jeu_est_immediat(self):
        j = faux_jeu(True); j.cam_saut = True; M, _ = J._camera_ville(j, faux_etat(0.7), ASPECT); self.assertEqual(j.cam_scene_w, 1.0)
        j = faux_jeu(False); j.cam_saut = True; J._camera_ville(j, faux_etat(0.7), ASPECT); self.assertEqual(j.cam_scene_w, 0.0)

    def test_passage_progressif_dans_les_deux_sens(self):
        j = faux_jeu(False); e = faux_etat(0.7); J._camera_ville(j, e, ASPECT)                                                                           # (hors scene, coupure initiale)
        j.cam_jeu = True; hs = []; ws = []
        for _ in range(90): M, _ = J._camera_ville(j, e, ASPECT); hs.append(hauteur_heros(M)); ws.append(j.cam_scene_w)
        self.assertTrue(all(b >= a - 1e-12 for a, b in zip(ws, ws[1:]))); self.assertGreater(ws[0], 0.0); self.assertLess(ws[0], 0.5); self.assertGreater(ws[-1], 0.99)    # (0,4 s pour 90 % : ~ 15 images a peine, jamais d'un coup)
        self.assertTrue(all(b >= a - 1e-9 for a, b in zip(hs, hs[1:])))                                                                                  # le heros grossit sans a-coup, sans retour en arriere
        self.assertLess(max((b - a) / a for a, b in zip(hs, hs[1:])), 0.05)                                                                              # moins de 5 % d'une image a l'autre
        j.cam_jeu = False; hs = []; ws = []
        for _ in range(90): M, _ = J._camera_ville(j, e, ASPECT); hs.append(hauteur_heros(M)); ws.append(j.cam_scene_w)
        self.assertTrue(all(b <= a + 1e-12 for a, b in zip(ws, ws[1:]))); self.assertLess(ws[-1], 0.01)                                                  # fin de scene : retour progressif au cadrage commun
        self.assertTrue(all(b <= a + 1e-9 for a, b in zip(hs, hs[1:])))

    def test_le_zoom_du_joueur_s_applique_encore_pendant_la_transition(self):
        a, _ = self.hauteur(True, 1.0, zoom=1.0); b, _ = self.hauteur(True, 1.0, zoom=1.5)
        self.assertAlmostEqual(b / a, 1.5, delta=0.05)                                                                                                    # (c'est la transition qui le ramene a 100 % ; elle se voit)

    def test_camera_libre_et_titre_inchanges(self):
        e = faux_etat(0.7); e.cam_libre = True; e.cam_rot = (30.0, 0.0, 0.0); e.cam_pos = np.array([0.0, 6.0, -10.0])
        j = faux_jeu(True, zoom=1.5); M1, _ = J._camera_ville(j, e, ASPECT); j = faux_jeu(True, zoom=1.0); M2, _ = J._camera_ville(j, e, ASPECT)
        self.assertTrue(np.allclose(M1, M2))                                                                                                              # camera libre : cadrage du jeu, sans zoom du joueur (comme avant)


if __name__ == '__main__':
    unittest.main()
