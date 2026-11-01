"""Test de la camera des villes (sans fenetre ni moteur : `Jeu._camera_ville` est appelee sur un faux objet) :

  1. la matrice du portage = le pipeline d'Unity re-ecrit a part (SceneCamera.Update : LookAt, tangage - lookDownAdjust, avance de distanceAdjust, Perspective(fov x 4/3, 1/aspect) dont on echange
     [0] et [5], s_yOffset) a l'ecran portrait d'origine (0,5625) ;
  2. camera centree sur le joueur : le heros reste au centre de l'image quand le jeu borne SA cible (bord de la carte), a toute vitesse du jeu (x1 a x4) et toute cadence d'affichage, et apres l'arret ;
  3. camera menee par le jeu (travelling, cible = un personnage) : la visionneuse n'ajoute AUCUNE borne (cadrage 16/9, centrage) : le rendu est exactement ce que le moteur commande ;
  4. `Jeu._camera_menee` : verrou de la TownCamera du moteur qui mene la camera ailleurs que sur le joueur, ou qui la tient sur le joueur.

    python3 outils/test_camera_ville.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import math, os, sys, types, unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import fenetre as F

ASPECT_16_9 = 16.0 / 9.0
HORLOGE = [0.0]


def faux_jeu(option=True, bornes_x=None, jeu=False):
    j = types.SimpleNamespace(zoom=1.0, reg={'camera_centree': option}, cam_jeu=jeu, cam_saut=True, cam_dec=[0.0, 0.0], cam_res=[0.0, 0.0], cam_centre=False, cam_poids=1.0, t_centre=None, fixe_test=False,
                              bornes_x=bornes_x, lacet=0.0, angle_cam=0.0, cam_bloquee=False, carte_nom='x', n_boucle=0, _cadre_vue=None)
    j._rot_camera = lambda e: None
    return j


def faux_etat(cib, hero, fov=None, yoff=None):
    cib = np.array(cib, float)
    return types.SimpleNamespace(cam_pos=cib + np.array([0.0, 28.94, -27.0]), cam_cible=cib, cam_fov=fov, cam_near=None, cam_far=None, cam_yoff=yoff, cam_bas=None, cam_libre=False, cam_rot=None,
                                 sprites={0: {'pos': tuple(hero)}})


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
    def setUp(self):
        HORLOGE[0] = 0.0
        self.temps_avant = F.time
        F.time = types.SimpleNamespace(perf_counter=lambda: HORLOGE[0], time=lambda: HORLOGE[0], sleep=lambda *a: None)

    def tearDown(self): F.time = self.temps_avant

    def test_projection_comme_unity(self):
        rng = np.random.default_rng(1); pire = 0.0
        for _ in range(100):
            cib = rng.uniform(-30, 30, 3); cib[1] = 0
            pos = cib + np.array([rng.uniform(-8, 8), 29.0 + rng.uniform(-3, 3), -27.0 + rng.uniform(-3, 3)])
            fov = float(rng.choice([9.5, 10.0])); yoff = float(rng.choice([0.0, 0.05]))
            pts = [cib + np.array([dx, dy, dz]) for dx in (-5, 0, 5) for dy in (0, 1.5) for dz in (-6, 0, 6)]
            ref = unity_ndc(pos, cib, fov, F.VILLE_NEAR, F.VILLE_FAR, yoff, F.ASPECT_PORTRAIT, pts)
            e = faux_etat(cib, cib, fov, yoff); e.cam_pos = pos; e.sprites = {}          # sans heros : champ horizontal fixe de l'original (avec lui, zoom commun de la visionneuse)
            M, _ = F.Jeu._camera_ville(faux_jeu(option=False), e, F.ASPECT_PORTRAIT)
            pire = max(pire, float(np.abs(np.array([ndc(M, p) for p in pts]) - ref).max()))
        self.assertLess(pire, 1e-9)

    def course(self, dt, f, bord=5.0, arret=8.0):
        """Un heros court (30 pas du moteur par seconde x f) vers une zone ou le jeu borne sa cible a `bord`, puis s'arrete : ecart maximal du heros au centre de l'image (NDC x)."""
        HORLOGE[0] = 0.0; j = faux_jeu(option=True); x = 0.0; t = 0.0; pire = 0.0
        while t < 4.0:
            HORLOGE[0] += dt; t += dt; x = min(arret, x + 0.2128 * 30.0 * f * dt)
            e = faux_etat((min(x, bord), 0.0, 0.0), (x, 0.0, 0.0))
            M, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9); pire = max(pire, abs(ndc(M, (x, 0.0, 0.0))[0]))
        return pire

    def test_centrage_rigide_a_toute_vitesse(self):
        for dt in (1 / 30, 1 / 60, 1 / 144):
            for f in (1.0, 1.5, 2.0, 3.0, 4.0): self.assertLess(self.course(dt, f), 1e-6, 'dt=1/%d x%s' % (round(1 / dt), f))

    def test_camera_menee_sans_bornes(self):
        """Le moteur mene la camera loin de la carte (la grenouille sort par l'est) : le rendu est celui du moteur, avec ou sans l'option de centrage, bornes de la visionneuse ou non."""
        for option in (True, False):
            HORLOGE[0] = 0.0; j = faux_jeu(option=option, bornes_x=(-3.0, 3.0), jeu=True)
            e = faux_etat((6.07, 0.0, 11.3), (0.93, 0.0, 10.56))
            for _ in range(60): HORLOGE[0] += 1 / 60; M, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9)
            ref, _ = F.Jeu._camera_ville(faux_jeu(option=False, bornes_x=None, jeu=True), e, ASPECT_16_9)
            self.assertLess(float(np.abs(M - ref).max()), 1e-9, 'option=%s' % option)

    def test_bornes_16_9_hors_scene(self):
        """Hors scene, option de centrage desactivee : la camera est ramenee dans la carte (cadrage 16/9) ; en scene, non (ci-dessus)."""
        HORLOGE[0] = 0.0; j = faux_jeu(option=False, bornes_x=(-3.0, 3.0), jeu=False)
        e = faux_etat((6.07, 0.0, 11.3), (6.07, 0.0, 11.3))
        for _ in range(60): HORLOGE[0] += 1 / 60; M, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9)
        self.assertGreater(abs(ndc(M, (6.07, 0.0, 11.3))[0]), 0.3)

    def test_camera_menee_predicat(self):
        def mo(cj, hero, cib):
            e = types.SimpleNamespace(sprites={0: {'pos': hero}} if hero else {}, cam_cible=cib)
            return types.SimpleNamespace(camera_jeu=lambda: cj, etat=e)
        cas = [((1, 6, 0, 0), (0, 0, 0), (0, 0, 0), False),          # verrou, cible = le joueur : rien ne change
               ((1, 0, 0, 0), (0, 0, 0), (0.3, 0, 0.2), False),      # verrou sans cible, camera sur le heros : rien ne change
               ((1, 0, 0, 0), (0, 0, 0), (3, 0, 0), True),           # plan fixe, heros ailleurs
               ((1, 5, 0, 0), (0, 0, 0), (0, 0, 0), True),           # cible = un personnage (grenouille)
               ((1, 4, 0, 1), (0, 0, 0), (0, 0, 0), True),           # retour vers le joueur : deplacement en cours
               ((1, 1, 0, 1), (0, 0, 0), (0, 0, 0), True),           # travelling
               ((1, 0, 0, 0), None, (0, 0, 0), True),                # heros hors champ
               ((1, 6, 0, 0), None, (9, 0, 9), False)]
        for cj, h, c, attendu in cas: self.assertEqual(F.Jeu._camera_menee(None, mo(cj, h, c)), attendu, (cj, h, c))


if __name__ == '__main__':
    unittest.main(verbosity=2)
