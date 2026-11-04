"""Test de la camera des villes (sans fenetre ni moteur : `Jeu._camera_ville` est appelee sur un faux objet). Depuis #264 elle est EXACTEMENT celle du jeu :

  1. la matrice du portage = le pipeline d'Unity re-ecrit a part (SceneCamera.Update : LookAt, tangage - lookDownAdjust, avance de distanceAdjust, Perspective(fov x 4/3, 1/aspect) dont on echange
     [0] et [5], s_yOffset) a l'ecran portrait d'origine (0,5625) ;
  2. elle ne depend QUE de ce que le moteur envoie (position, cible, champ, decalage, rotation libre) : ni du heros, ni de l'historique des images (aucun lissage, aucun centrage, aucun reste qui glisse),
     ni d'un reglage du joueur (le faux jeu n'a ni zoom, ni rotation, ni inclinaison : le code n'en lit plus) ;
  3. les reglages et les gestes du joueur sur la camera n'existent plus (zoom, distance, rotation, inclinaison, recentrage, molette).

    python3 tests/test_camera_ville.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import math, os, sys, types, unittest, inspect

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _chemins          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.fenetre import jeu as F
from dq4_pc.persistance import reglages as RG

ASPECT_16_9 = 16.0 / 9.0


def faux_jeu():
    """Le strict necessaire : si la camera relisait un reglage du joueur (zoom, lacet...), ce faux jeu leverait AttributeError."""
    j = types.SimpleNamespace(n_boucle=0, _cadre_vue=None, _cadre_sprites=None)
    j._rot_camera = lambda e: F.Jeu._rot_camera(j, e)
    return j


def faux_etat(cib, hero, fov=None, yoff=None, partie=None, libre=False, rot=None, pos=None):
    cib = np.array(cib, float)
    return types.SimpleNamespace(cam_pos=cib + np.array([0.0, 28.94, -27.0]) if pos is None else np.array(pos, float), cam_cible=cib, cam_fov=fov, cam_near=None, cam_far=None, cam_yoff=yoff, cam_bas=None, cam_libre=libre, cam_rot=rot,
                                 sprites={0: {'pos': tuple(hero)}} if hero is not None else {}, partie=partie)


def ndc(M, p):
    c = M @ np.array([p[0], p[1], p[2], 1.0]); return c[0] / c[3], c[1] / c[3]


def unity_ndc(pos, cib, fov, near, far, yoff, aspect_cam, pts, bas=0.2, dist_adj=4.0):
    """SceneCamera.Update (mode avec cible) + NativeManager.cmd_camera, d'apres le code d'origine."""
    pos = np.array(pos, float); cib = np.array(cib, float)
    f0 = cib - pos; f0 /= np.linalg.norm(f0)
    ry, rx = math.atan2(f0[0], f0[2]), math.asin(-f0[1]) - math.radians(bas)                            # euler Unity : cap, tangage vers le bas ; eulerAngles.x -= s_lookDownAdjust
    Ry = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
    R = Ry @ Rx; pos = pos + R @ np.array([0, 0, 1.0]) * dist_adj                                      # avance de s_distanceAdjust
    V = np.eye(4); V[:3, :3] = R.T; V[:3, 3] = -R.T @ pos; V = np.diag([1, 1, -1, 1.0]) @ V            # worldToCamera d'Unity (regarde vers -z)
    fv = math.radians(fov * 4.0 / 3.0)
    m11 = 1 / math.tan(fv / 2); m00 = m11 / (1.0 / aspect_cam)                                          # Matrix4x4.Perspective(fov x 4/3, 1 / aspect, near, far)
    P = np.zeros((4, 4)); P[0, 0] = m00; P[1, 1] = m11; P[2, 2] = -(far + near) / (far - near); P[2, 3] = -2 * far * near / (far - near); P[3, 2] = -1
    P[0, 0], P[1, 1] = P[1, 1], P[0, 0]                                                                 # [0] et [5] echanges : champ horizontal fixe
    Ty = np.eye(4); Ty[1, 3] = yoff                                                                     # s_yOffset
    out = []
    for p in pts:
        c = Ty @ P @ V @ np.array([*p, 1.0]); out.append((c[0] / c[3], c[1] / c[3]))
    return np.array(out)


class TestCameraVille(unittest.TestCase):
    def test_projection_comme_unity(self):
        rng = np.random.default_rng(1); pire = 0.0
        for _ in range(100):
            cib = rng.uniform(-30, 30, 3); cib[1] = 0
            pos = cib + np.array([rng.uniform(-8, 8), 29.0 + rng.uniform(-3, 3), -27.0 + rng.uniform(-3, 3)])
            fov = float(rng.choice([9.5, 10.0])); yoff = float(rng.choice([0.0, 0.05]))
            pts = [cib + np.array([dx, dy, dz]) for dx in (-5, 0, 5) for dy in (0, 1.5) for dz in (-6, 0, 6)]
            ref = unity_ndc(pos, cib, fov, F.VILLE_NEAR, F.VILLE_FAR, yoff, F.ASPECT_PORTRAIT, pts)
            e = faux_etat(cib, cib, fov, yoff, pos=pos)
            M, _ = F.Jeu._camera_ville(faux_jeu(), e, F.ASPECT_PORTRAIT)
            pire = max(pire, float(np.abs(np.array([ndc(M, p) for p in pts]) - ref).max()))
        self.assertLess(pire, 1e-9)

    def test_independante_du_heros(self):
        """Le heros au centre, a l'autre bout de la carte, absent : meme image (la cible du jeu, bornee aux bords de la carte, fait foi ; la visionneuse ne recentre plus)."""
        refs = []
        for hero in ((0.0, 0.0, 0.0), (7.0, 0.0, -3.0), (40.0, 5.0, 40.0), None):
            M, _ = F.Jeu._camera_ville(faux_jeu(), faux_etat((5.0, 0.0, 4.0), hero), ASPECT_16_9); refs.append(M)
        for M in refs[1:]: self.assertLess(float(np.abs(M - refs[0]).max()), 1e-12)
        self.assertGreater(abs(ndc(refs[0], (0.0, 0.0, 0.0))[0]), 0.05, 'le heros n\'est pas recentre quand la cible du jeu est ailleurs (bord de la carte)')

    def test_sans_memoire(self):
        """Aucun lissage, aucun reste : l'image ne depend que de l'etat envoye par le moteur a cet instant (marche, escalier, coupure de scene, retour de scene...)."""
        j = faux_jeu(); trajet = [((0.0, 0.0, 0.0), 0.0), ((1.0, 0.0, 0.5), 0.3), ((1.0, 4.0, 0.5), 4.0), ((30.0, 4.0, -9.0), 4.0), ((30.0, 0.0, -9.0), 0.0), ((2.0, 0.0, 2.0), 0.0)]
        for cib, y in trajet:
            e = faux_etat((cib[0], y, cib[2]), (cib[0], y, cib[2]))
            M1, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9); M2, _ = F.Jeu._camera_ville(faux_jeu(), e, ASPECT_16_9)
            self.assertLess(float(np.abs(M1 - M2).max()), 1e-12, cib)
            self.assertLess(abs(ndc(M1, (cib[0], y, cib[2]))[0]) + abs(ndc(M1, (cib[0], y, cib[2]))[1] - ndc(M2, (cib[0], y, cib[2]))[1]), 1e-6, 'la cible du jeu reste ou le jeu la met')

    def test_hauteur_telle_que_le_jeu(self):
        """Un escalier : la cible du jeu monte de 4 unites, l'image suit tout de suite (aucun retard comme l'ancien lissage de hauteur)."""
        j = faux_jeu(); M0, _ = F.Jeu._camera_ville(j, faux_etat((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)), ASPECT_16_9)
        e = faux_etat((0.0, 4.0, 0.0), (0.0, 4.0, 0.0)); M1, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9)
        self.assertLess(abs(ndc(M1, (0.0, 4.0, 0.0))[1] - ndc(M0, (0.0, 0.0, 0.0))[1]), 1e-9, 'le heros reste ou il etait a l\'ecran, sans glissement')

    def test_camera_libre_et_decalage(self):
        """Camera libre d'une scene (paquet 11, bit 7 : position + angles) et decalage vertical : ce que le jeu commande, rien de plus."""
        e = faux_etat((0.0, 0.0, 0.0), (9.0, 0.0, 9.0), libre=True, rot=(30.0, 20.0, 0.0), pos=(1.0, 12.0, -10.0))
        M, rep = F.Jeu._camera_ville(faux_jeu(), e, ASPECT_16_9); e2 = faux_etat((0.0, 0.0, 0.0), None, libre=True, rot=(30.0, 20.0, 0.0), pos=(1.0, 12.0, -10.0))
        M2, _ = F.Jeu._camera_ville(faux_jeu(), e2, ASPECT_16_9); self.assertLess(float(np.abs(M - M2).max()), 1e-12)
        d = faux_etat((3.0, 0.0, 3.0), (3.0, 0.0, 3.0), yoff=0.05); d0 = faux_etat((3.0, 0.0, 3.0), (3.0, 0.0, 3.0), yoff=0.0)
        Ma, _ = F.Jeu._camera_ville(faux_jeu(), d, ASPECT_16_9); Mb, _ = F.Jeu._camera_ville(faux_jeu(), d0, ASPECT_16_9)
        self.assertAlmostEqual(ndc(Ma, (3.0, 0.0, 3.0))[1] - ndc(Mb, (3.0, 0.0, 3.0))[1], 0.05, places=6)

    def test_plus_de_reglage_de_camera_pour_le_joueur(self):
        """Retires en #264 : zoom / distance, rotation, inclinaison, recentrage, touches de camera, reglages enregistres, gestes de la molette."""
        src = inspect.getsource(F.Jeu._camera_ville)
        for mot in ('self.zoom', 'self.lacet', 'angle_cam', 'cam_dec', 'cam_res', 'cam_jeu', 'cam_ref_y', 'hauteur_camera'): self.assertNotIn(mot, src, mot)
        for nom in ('_maj_camera', '_maj_distance_clavier', 'regler_zoom', 'regler_distance', 'reinitialiser_camera', 'recentrer_camera', 'distance_par_defaut', '_camera_pilotable', '_zoom_possible', '_molette_appui', '_molette_glisse',
                    '_molette_relache', '_suivre_scene', '_camera_menee', '_coupure_camera', '_lacet_eff', '_tourner_dir', '_etat_axe'):
            self.assertFalse(hasattr(F.Jeu, nom), nom)
        for cle in ('distance_camera', 'angle_camera', 'camera_inverser_gd', 'camera_inverser_hb', 'vitesse_camera'): self.assertNotIn(cle, RG.DEFAUT, cle)
        for act in ('cam_pres', 'cam_loin'): self.assertNotIn(act, RG.TOUCHES_DEF, act)
        for cle in ('distance_camera', 'vitesse_camera', 'angle_camera'): self.assertIn(cle, RG.CLES_OBSOLETES, cle)

    def test_ancien_fichier_de_reglages_lisible(self):
        """Un reglages.json d'avant #264 (distance, angle, vitesse de camera, touches Page haut / Page bas) se lit sans erreur ; les cles retirees ne sont pas reecrites."""
        import json, tempfile
        with tempfile.TemporaryDirectory() as d:
            ch = os.path.join(d, 'reglages.json')
            with open(ch, 'w', encoding='utf-8') as f: json.dump({'distance_camera': 150, 'angle_camera': 12.0, 'vitesse_camera': 3.0, 'camera_inverser_gd': True, 'vitesse_marche': 2.0, 'touches': {'cam_pres': ['PAGEUP', None], 'haut': ['W', None]}, 'touches_v': RG.DEFAUT['touches_v']}, f)
            r = RG.Reglages(ch); r.enregistrer()
            with open(ch, encoding='utf-8') as f: ecrit = json.load(f)
        self.assertEqual(r['vitesse_marche'], 2.0); self.assertEqual(r['touches']['haut'][0], 'W')
        for cle in ('distance_camera', 'angle_camera', 'vitesse_camera', 'camera_inverser_gd'): self.assertNotIn(cle, ecrit, cle)
        self.assertNotIn('cam_pres', ecrit['touches'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
