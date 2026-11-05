"""Test de la camera des villes (sans fenetre ni moteur : `Game._town_camera` est appelee sur un faux objet). Depuis #264 elle est celle du jeu, et depuis D-234 la rotation gauche / droite du joueur l'est aussi :

  1. la matrice du portage = le pipeline d'Unity re-ecrit a part (SceneCamera.Update : LookAt, tangage - lookDownAdjust, avance de distanceAdjust, Perspective(fov x 4/3, 1/aspect) dont on echange
     [0] et [5], s_yOffset) a l'ecran portrait d'origine (0,5625) ;
  2. elle ne depend QUE de ce que le moteur envoie (position, cible, champ, decalage, rotation libre) : ni du heros, ni de l'historique des images (aucun lissage, aucun centrage,
     aucun reste qui glisse), ni zoom, ni inclinaison, ni rotation ajoutee par la visionneuse (D-233 la faisait a cote du jeu : elle « se teleportait » quand une scene du jeu prenait la camera) ;
  3. la rotation que le joueur donne par les boutons de camera DU JEU est dans la position de la camera que le jeu envoie : la vue la montre telle quelle (distance, tangage, place de la cible a l'ecran inchanges) ;
     entre deux pas du moteur elle est interpolee en arc autour de la cible (`Game._interpolate_camera`), un angle regle d'un coup ou un changement de plan est une coupure ;
  4. les autres reglages et gestes du joueur sur la camera n'existent plus (zoom, distance, inclinaison, centrage, acceleration, molette).

    python3 tests/test_town_camera.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import math, os, sys, types, unittest, inspect

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.window import game as F
from dq4_pc.core import engine as ENGINE
from dq4_pc.persistence import settings as RG

ASPECT_16_9 = 16.0 / 9.0


def fake_game(**kw):
    """Le strict necessaire : si la camera relisait un reglage du joueur retire (zoom, angle, distance...) ou un etat de rotation de la visionneuse (D-233), ce faux jeu leverait AttributeError."""
    j = types.SimpleNamespace(n_loop=0, _view_border=None, map_name=None, engine=types.SimpleNamespace(state=types.SimpleNamespace(part=None, cam_free=False, cam_rot=None)))
    j._rot_camera = lambda e: F.Game._rot_camera(j, e)
    for k, v in kw.items(): setattr(j, k, v)
    return j


def make_view(e, aspect=None, j=None, **kw):
    """-> (matrice, repere, faux jeu) : la camera de la ville pour l'etat `e` (le faux moteur est celui de `e`)."""
    j = j or fake_game(**kw); j.engine.state = e
    M, rep = F.Game._town_camera(j, e, ASPECT_16_9 if aspect is None else aspect)
    return M, rep, j


def fake_state(target_pos, hero, fov=None, yoff=None, part=None, free=False, rot=None, pos=None):
    target_pos = np.array(target_pos, float)
    return types.SimpleNamespace(cam_pos=target_pos + np.array([0.0, 28.94, -27.0]) if pos is None else np.array(pos, float), cam_target=target_pos, cam_fov=fov, cam_near=None, cam_far=None, cam_yoff=yoff, cam_down=None, cam_free=free, cam_rot=rot,
                                 sprites={0: {'pos': tuple(hero)}} if hero is not None else {}, part=part)


def ndc(M, p):
    c = M @ np.array([p[0], p[1], p[2], 1.0]); return c[0] / c[3], c[1] / c[3]


def unity_ndc(pos, target_pos, fov, near, far, yoff, aspect_cam, pts, bottom=0.2, dist_adj=4.0):
    """SceneCamera.Update (mode avec cible) + NativeManager.cmd_camera, d'apres le code d'origine."""
    pos = np.array(pos, float); target_pos = np.array(target_pos, float)
    f0 = target_pos - pos; f0 /= np.linalg.norm(f0)
    ry, rx = math.atan2(f0[0], f0[2]), math.asin(-f0[1]) - math.radians(bottom)                            # euler Unity : cap, tangage vers le bas ; eulerAngles.x -= s_lookDownAdjust
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


class TestTownCamera(unittest.TestCase):
    def test_projection_like_unity(self):
        rng = np.random.default_rng(1); worst = 0.0
        for _ in range(100):
            target_pos = rng.uniform(-30, 30, 3); target_pos[1] = 0
            pos = target_pos + np.array([rng.uniform(-8, 8), 29.0 + rng.uniform(-3, 3), -27.0 + rng.uniform(-3, 3)])
            fov = float(rng.choice([9.5, 10.0])); yoff = float(rng.choice([0.0, 0.05]))
            pts = [target_pos + np.array([dx, dy, dz]) for dx in (-5, 0, 5) for dy in (0, 1.5) for dz in (-6, 0, 6)]
            ref = unity_ndc(pos, target_pos, fov, F.TOWN_NEAR, F.TOWN_FAR, yoff, F.ASPECT_PORTRAIT, pts)
            e = fake_state(target_pos, target_pos, fov, yoff, pos=pos)
            M, _ = F.Game._town_camera(fake_game(), e, F.ASPECT_PORTRAIT)
            worst = max(worst, float(np.abs(np.array([ndc(M, p) for p in pts]) - ref).max()))
        self.assertLess(worst, 1e-9)

    def test_independent_of_hero(self):
        """Le heros au centre, a l'autre bout de la carte, absent : meme image (la cible du jeu, bornee aux bords de la carte, fait foi ; la visionneuse ne recentre plus)."""
        refs = []
        for hero in ((0.0, 0.0, 0.0), (7.0, 0.0, -3.0), (40.0, 5.0, 40.0), None):
            M, _ = F.Game._town_camera(fake_game(), fake_state((5.0, 0.0, 4.0), hero), ASPECT_16_9); refs.append(M)
        for M in refs[1:]: self.assertLess(float(np.abs(M - refs[0]).max()), 1e-12)
        self.assertGreater(abs(ndc(refs[0], (0.0, 0.0, 0.0))[0]), 0.05, 'le heros n\'est pas recentre quand la cible du jeu est ailleurs (bord de la carte)')

    def test_without_memory(self):
        """Aucun lissage, aucun reste : l'image ne depend que de l'etat envoye par le moteur a cet instant (marche, escalier, coupure de scene, retour de scene...)."""
        j = fake_game(); trajet = [((0.0, 0.0, 0.0), 0.0), ((1.0, 0.0, 0.5), 0.3), ((1.0, 4.0, 0.5), 4.0), ((30.0, 4.0, -9.0), 4.0), ((30.0, 0.0, -9.0), 0.0), ((2.0, 0.0, 2.0), 0.0)]
        for target_pos, y in trajet:
            e = fake_state((target_pos[0], y, target_pos[2]), (target_pos[0], y, target_pos[2]))
            M1, _ = F.Game._town_camera(j, e, ASPECT_16_9); M2, _ = F.Game._town_camera(fake_game(), e, ASPECT_16_9)
            self.assertLess(float(np.abs(M1 - M2).max()), 1e-12, target_pos)
            self.assertLess(abs(ndc(M1, (target_pos[0], y, target_pos[2]))[0]) + abs(ndc(M1, (target_pos[0], y, target_pos[2]))[1] - ndc(M2, (target_pos[0], y, target_pos[2]))[1]), 1e-6, 'la cible du jeu reste ou le jeu la met')

    def test_height_same_as_game(self):
        """Un escalier : la cible du jeu monte de 4 unites, l'image suit tout de suite (aucun retard comme l'ancien lissage de hauteur)."""
        j = fake_game(); M0, _ = F.Game._town_camera(j, fake_state((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)), ASPECT_16_9)
        e = fake_state((0.0, 4.0, 0.0), (0.0, 4.0, 0.0)); M1, _ = F.Game._town_camera(j, e, ASPECT_16_9)
        self.assertLess(abs(ndc(M1, (0.0, 4.0, 0.0))[1] - ndc(M0, (0.0, 0.0, 0.0))[1]), 1e-9, 'le heros reste ou il etait a l\'ecran, sans glissement')

    def test_free_camera_and_offset(self):
        """Camera libre d'une scene (paquet 11, bit 7 : position + angles) et decalage vertical : ce que le jeu commande, rien de plus."""
        e = fake_state((0.0, 0.0, 0.0), (9.0, 0.0, 9.0), free=True, rot=(30.0, 20.0, 0.0), pos=(1.0, 12.0, -10.0))
        M, rep = F.Game._town_camera(fake_game(), e, ASPECT_16_9); e2 = fake_state((0.0, 0.0, 0.0), None, free=True, rot=(30.0, 20.0, 0.0), pos=(1.0, 12.0, -10.0))
        M2, _ = F.Game._town_camera(fake_game(), e2, ASPECT_16_9); self.assertLess(float(np.abs(M - M2).max()), 1e-12)
        d = fake_state((3.0, 0.0, 3.0), (3.0, 0.0, 3.0), yoff=0.05); d0 = fake_state((3.0, 0.0, 3.0), (3.0, 0.0, 3.0), yoff=0.0)
        Ma, _ = F.Game._town_camera(fake_game(), d, ASPECT_16_9); Mb, _ = F.Game._town_camera(fake_game(), d0, ASPECT_16_9)
        self.assertAlmostEqual(ndc(Ma, (3.0, 0.0, 3.0))[1] - ndc(Mb, (3.0, 0.0, 3.0))[1], 0.05, places=6)

    def cap(self, rep):
        fw = rep[2]; return math.degrees(math.atan2(fw[0], fw[2]))

    def test_game_rotation_shown_as_is(self):
        """La camera du jeu tourne autour de sa cible (boutons de camera du jeu, ou scene) : le jeu envoie la position tournee, la vue la montre sans rien y ajouter : distance, tangage et place de la cible a l'ecran inchanges,
        cap = cap d'origine + rotation (positive vers +X, comme la fleche droite)."""
        target_pos = np.array((5.0, 0.0, 4.0)); e0 = fake_state(target_pos, target_pos, part=ENGINE.PART_TOWN); M0, rep0, j0 = make_view(e0)
        pos0, fw0 = j0._view_border[0], j0._view_border[3]; d0 = e0.cam_pos - target_pos
        for yaw in (-120.0, -45.0, 30.0, 90.0, 179.0):
            c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
            e = fake_state(target_pos, target_pos, part=ENGINE.PART_TOWN, pos=target_pos + np.array([d0[0] * c + d0[2] * s, d0[1], -d0[0] * s + d0[2] * c]))          # (la position que le moteur envoie apres la rotation)
            M, rep, j = make_view(e); pos, fw = j._view_border[0], j._view_border[3]
            self.assertLess(abs(ndc(M, target_pos)[0] - ndc(M0, target_pos)[0]) + abs(ndc(M, target_pos)[1] - ndc(M0, target_pos)[1]), 1e-9, yaw)          # la cible reste ou le jeu la met
            self.assertAlmostEqual(float(np.linalg.norm(pos - target_pos)), float(np.linalg.norm(pos0 - target_pos)), places=9)                 # meme distance
            self.assertAlmostEqual(float(pos[1]), float(pos0[1]), places=9); self.assertAlmostEqual(float(fw[1]), float(fw0[1]), places=9)   # meme hauteur, meme tangage
            spacing = (self.cap(rep) - self.cap(rep0) - yaw + 180.0) % 360.0 - 180.0; self.assertLess(abs(spacing), 1e-6, yaw)             # cap + rotation
        self.assertGreater(self.cap(make_view(fake_state(target_pos, target_pos, part=ENGINE.PART_TOWN, pos=target_pos + np.array([d0[2], d0[1], 0.0 - d0[0]])))[1]) - self.cap(rep0), 0.0)         # (a droite : le cap avance vers +X)

    def test_no_viewer_state_in_view(self):
        """Rien d'autre que ce que le moteur envoie ne change la vue : le faux jeu n'a ni rotation, ni poids de scene, ni verrou (D-233 en avait), et la vue est la meme quel que soit l'etat de la partie."""
        target_pos = (5.0, 0.0, 4.0); ref = make_view(fake_state(target_pos, target_pos, part=ENGINE.PART_TOWN))[0]
        for part in (ENGINE.PART_TOWN, ENGINE.PART_FIELD): self.assertLess(float(np.abs(make_view(fake_state(target_pos, target_pos, part=part), map_name=None)[0] - ref).max()), 1e-12, part)
        self.assertLess(float(np.abs(make_view(fake_state(target_pos, target_pos, part=ENGINE.PART_TOWN), map_name=F.TITLE_MAP)[0] - ref).max()), 1e-12)
        for name_str in ('yaw', 'cam_w', 'cam_jeu', 'cam_bloquee', 'cam_saut', 't_centre', '_sprites_border'): self.assertFalse(hasattr(fake_game(), name_str), name_str)
        src = inspect.getsource(F.Game._town_camera)
        for word in ('self.yaw', 'cam_w', '_lacet_eff', 'perf_counter', 'cam_jeu'): self.assertNotIn(word, src, word)

    # ---- interpolation entre deux pas du moteur (Game._interpolate_camera)
    def turn(self, target_pos, d0, deg):
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg)); return tuple(np.array(target_pos) + np.array([d0[0] * c + d0[2] * s, d0[1], -d0[0] * s + d0[2] * c]))

    def interp(self, pr_pos, prev_target, pos, target_pos, a):
        j = types.SimpleNamespace(engine=types.SimpleNamespace(state=types.SimpleNamespace(cam_pos=pos, cam_target=target_pos)))
        return F.Game._interpolate_camera(j, dict(cam_pos=pr_pos, cam_cible=prev_target), a)

    def test_rotation_interpolated_along_an_arc(self):
        """Un cran de rotation (2,8125 degres) deplace la camera de plus de CAM_JUMP_TOWN sur une coordonnee quand elle est a 34 unites de sa cible (ev01, cbout : (0 ; 27,7 ; -34,18)) : l'ancienne interpolation coordonnee par coordonnee y voyait un saut,
        et la rotation restait a 30 pas par seconde. En arc autour de la cible : meme distance, cap intermediaire."""
        target_pos = (5.0, 0.0, 4.0); d0 = np.array([0.0, 27.7, -34.18]); r0 = math.hypot(d0[0], d0[2])
        for yaw in (0.0, 60.0, 135.0, -100.0):
            p0 = self.turn(target_pos, self.turn((0, 0, 0), d0, yaw), 0.0); p1 = self.turn(target_pos, self.turn((0, 0, 0), d0, yaw), ENGINE.CAM_STEP)
            if yaw == 0.0: self.assertGreater(float(np.abs(np.array(p1) - np.array(p0)).max()), F.CAM_JUMP_TOWN)          # (le cas a traiter : plus que le seuil d'un saut sur une seule coordonnee)
            for a in (0.0, 0.25, 0.5, 1.0):
                r = self.interp(p0, target_pos, p1, target_pos, a); self.assertIsNotNone(r, (yaw, a))
                pos, c = np.array(r[0]), np.array(r[1]); rel = pos - c
                self.assertAlmostEqual(math.hypot(rel[0], rel[2]), r0, places=9); self.assertAlmostEqual(float(rel[1]), float(d0[1]), places=9)       # meme distance, meme hauteur
                cap = math.degrees(math.atan2(-rel[0], -rel[2])); cap0 = math.degrees(math.atan2(-(p0[0] - target_pos[0]), -(p0[2] - target_pos[2])))
                self.assertAlmostEqual((cap - cap0 + 180.0) % 360.0 - 180.0, a * ENGINE.CAM_STEP, places=6)
            self.assertLess(float(np.abs(np.array(self.interp(p0, target_pos, p1, target_pos, 1.0)[0]) - np.array(p1)).max()), 1e-9)

    def test_height_and_distance_interpolated(self):
        """Une scene qui monte la camera ou l'approche de sa cible pendant qu'elle tourne : la hauteur et la distance suivent a mi-chemin (pas de marche d'escalier a 30 pas par seconde)."""
        target_pos = (5.0, 0.0, 4.0); p0 = (5.0, 20.0, 4.0 - 30.0); p1 = (5.0 + 30.0 * math.sin(math.radians(ENGINE.CAM_STEP)), 24.0, 4.0 - 30.0 * math.cos(math.radians(ENGINE.CAM_STEP)))
        r = self.interp(p0, target_pos, p1, target_pos, 0.5); self.assertIsNotNone(r); rel = np.array(r[0]) - np.array(r[1])
        self.assertAlmostEqual(float(rel[1]), 22.0, places=9); self.assertAlmostEqual(math.hypot(rel[0], rel[2]), 30.0, places=9)
        p2 = (5.0, 20.0, 4.0 - 34.0); r = self.interp(p0, target_pos, p2, target_pos, 0.25); rel = np.array(r[0]) - np.array(r[1])
        self.assertAlmostEqual(math.hypot(rel[0], rel[2]), 31.0, places=9)

    def test_rotation_crossing_180_degrees(self):
        target_pos = (0.0, 0.0, 0.0); p0 = (0.0, 28.94, 26.96 - 0.5); p1 = self.turn(target_pos, p0, -ENGINE.CAM_STEP)       # camera vers -Z de la cible, tourne de part et d'autre de 180 degres
        r = self.interp(p0, target_pos, p1, target_pos, 0.5); self.assertIsNotNone(r); rel = np.array(r[0]) - np.array(r[1])
        self.assertAlmostEqual(math.hypot(rel[0], rel[2]), math.hypot(p0[0], p0[2]), places=9)

    def test_walking_target_and_turning_camera(self):
        cib0 = (5.0, 0.0, 4.0); cib1 = (5.3, 0.0, 4.1); d0 = np.array([0.0, 28.94, -26.96])
        p0 = tuple(np.array(cib0) + d0); p1 = self.turn(cib1, d0, ENGINE.CAM_STEP)
        r = self.interp(p0, cib0, p1, cib1, 0.5); self.assertIsNotNone(r)
        self.assertLess(float(np.abs(np.array(r[1]) - (np.array(cib0) + np.array(cib1)) / 2).max()), 1e-12)          # la cible est a mi-chemin

    def test_nothing_moved_or_cut(self):
        target_pos = (5.0, 0.0, 4.0); d0 = np.array([0.0, 28.94, -26.96]); p0 = tuple(np.array(target_pos) + d0)
        self.assertIsNone(self.interp(p0, target_pos, p0, target_pos, 0.5))                                                      # rien n'a bouge
        self.assertIsNone(self.interp(p0, target_pos, tuple(np.array(p0) + (20.0, 0.0, 0.0)), (25.0, 0.0, 4.0), 0.5))    # la cible a saute : changement de carte, plan de scene
        self.assertIsNone(self.interp(p0, target_pos, self.turn(target_pos, d0, 90.0), target_pos, 0.5))                              # angle regle d'un coup (script du jeu, 90 degres en un pas) : coupure
        self.assertIsNone(self.interp(p0, target_pos, p0, None, 0.5)); self.assertIsNone(self.interp(None, target_pos, p0, target_pos, 0.5))
        self.assertIsNotNone(self.interp(p0, target_pos, self.turn(target_pos, d0, 15.0), target_pos, 0.5))                             # jusqu'a ~20 degres par pas (vitesse x4 : 11,25) : une rotation, interpolee
        self.assertIsNotNone(self.interp(p0, target_pos, self.turn(target_pos, d0, 4 * ENGINE.CAM_STEP), target_pos, 0.5))

    def test_only_rotation_is_left_to_the_player(self):
        """Retires en #264 et qui ne reviennent pas : zoom / distance, inclinaison, centrage sur le heros, lissage de hauteur, acceleration de la camera. Reviennent en D-233 : la rotation gauche / droite et son recentrage."""
        src = inspect.getsource(F.Game._town_camera)
        for word in ('self.zoom', 'angle_cam', 'cam_dec', 'cam_res', 'cam_ref_y', 'hauteur_camera'): self.assertNotIn(word, src, word)
        for name_str in ('_maj_distance_clavier', 'regler_zoom', 'set_distance', 'reinitialiser_camera', 'distance_par_defaut', '_zoom_possible', '_suivre_scene', '_ctrl_actif'): self.assertFalse(hasattr(F.Game, name_str), name_str)
        for name_str in ('recenter_camera', '_drivable_camera', '_wheel_press', '_wheel_drag', '_wheel_release', '_axis_state', '_bits_camera', '_camera_after_step', '_camera_oublier', '_engine_yaw', '_interpolate_camera'):
            self.assertTrue(hasattr(F.Game, name_str), name_str)
        for name_str in ('_maj_camera', '_camera_menee', '_coupure_camera', '_lacet_eff', '_tourner_dir'): self.assertFalse(hasattr(F.Game, name_str), name_str)          # (D-233 : la rotation de la visionneuse a cote du jeu, retiree en D-234)
        src = inspect.getsource(F.Game._bits_camera) + inspect.getsource(F.Game._camera_after_step)
        for word in ("'accel'", 'vitesse_accel', 'angle_cam', 'cam_haut', 'cam_bas'): self.assertNotIn(word, src, word)         # la camera ne s'accelere plus, et n'a plus d'inclinaison
        for lookup_key in ('distance_camera', 'angle_camera', 'camera_inverser_hb'): self.assertNotIn(lookup_key, RG.DEFAULT, lookup_key)
        for action in ('cam_pres', 'cam_loin'): self.assertNotIn(action, RG.DEFAULT_KEYS, action)
        for lookup_key in ('distance_camera', 'angle_camera', 'camera_inverser_hb'): self.assertIn(lookup_key, RG.OBSOLETE_KEYS, lookup_key)

    def test_wiring_in_loop_and_drawing(self):
        """Les fils qui relient la camera au reste (on ne peut pas faire tourner la vraie boucle ici) : la visionneuse n'a plus de mise a jour de la camera par image ni d'etat de la TownCamera a lire (verrou, limite, scene : c'est le jeu qui decide),
        plus de rotation de la marche ni des rangees de sprites (le jeu envoie les directions deja relatives a sa camera) ; les boutons de camera partent avec les touches du pas, et le clic molette y est relie."""
        looping = inspect.getsource(F.Game._loop)
        self.assertNotIn('_maj_camera', looping)
        self.assertEqual([n for n, f in inspect.getmembers(F.Game, inspect.isfunction) if 'lg, ld, vr = eng.camera_town()' in inspect.getsource(f)], [], 'la TownCamera du jeu n\'est plus lue pour y ajouter une rotation')
        self.assertEqual([n for n, f in inspect.getmembers(F.Game, inspect.isfunction) if 'phi = ' in inspect.getsource(f) and 'lacet' in inspect.getsource(f)], [], 'plus de correction des rangees des sprites')
        self.assertNotIn('_tourner_dir', inspect.getsource(F.Game.pad))
        self.assertIn('self._bits_camera()', inspect.getsource(F.Game._entries)); self.assertIn('self._camera_after_step(eng)', inspect.getsource(F.Game.tick))
        self.assertIn('self._wheel_press(x, y)', inspect.getsource(F.Game.on_mouse_press)); self.assertIn('self._wheel_release()', inspect.getsource(F.Game.on_mouse_release))
        self.assertIn('self.wheel.cancel()', inspect.getsource(F.Game.on_deactivate)); self.assertIn('self.wheel.cancel()', inspect.getsource(F.Game.on_mouse_motion))
        self.assertIn('self._interpolate_camera(pr, a)', inspect.getsource(F.Game._interpolate))

    def test_camera_settings(self):
        """Par defaut : Gauche > fleche gauche, Droite > fleche droite, vitesse de camera x1, sens du glissement non inverse. Visibles dans Commandes (voir test_pause_pages)."""
        self.assertEqual(RG.DEFAULT_KEYS['cam_gauche'], ['LEFT', None]); self.assertEqual(RG.DEFAULT_KEYS['cam_droite'], ['RIGHT', None])
        self.assertEqual(RG.DEFAULT['vitesse_camera'], 1.0); self.assertIs(RG.DEFAULT['camera_inverser_gd'], False)
        self.assertIn('vitesse_camera', RG.SPEEDS_X_KEYS); self.assertEqual(RG.BOUNDS['vitesse_camera'], (1.0, 4.0))
        for lookup_key in ('vitesse_camera', 'camera_inverser_gd'): self.assertNotIn(lookup_key, RG.OBSOLETE_KEYS, lookup_key)
        self.assertEqual(dict(RG.ACTIONS)['cam_gauche'], 'Caméra (Gauche)'); self.assertEqual(dict(RG.ACTIONS)['cam_droite'], 'Caméra (Droite)')
        self.assertAlmostEqual(ENGINE.CAM_STEP, 360.0 * 0x200 / 65536.0)          # la vitesse de reference (x1) est celle du jeu : un cran de 2,8125 degres par pas, 84,4 degres par seconde

    def test_old_settings_file_readable(self):
        """Un reglages.json d'avant #264 (distance, angle, vitesse de camera, touches Page haut / Page bas) se lit sans erreur : la vitesse de camera et le sens du glissement sont de nouveau valides et gardes ;
        les cles retirees (distance, angle, inversion haut / bas) ne sont pas reecrites."""
        import json, tempfile
        with tempfile.TemporaryDirectory() as d:
            ch = os.path.join(d, 'settings.json')
            with open(ch, 'w', encoding='utf-8') as f: json.dump({'distance_camera': 150, 'angle_camera': 12.0, 'vitesse_camera': 3.0, 'camera_inverser_gd': True, 'camera_inverser_hb': True, 'vitesse_marche': 2.0, 'touches': {'cam_pres': ['PAGEUP', None], 'haut': ['W', None]}, 'touches_v': RG.DEFAULT['touches_v']}, f)
            r = RG.Settings(ch); r.store()
            with open(ch, encoding='utf-8') as f: written_data = json.load(f)
        self.assertEqual(r['vitesse_marche'], 2.0); self.assertEqual(r['touches']['haut'][0], 'W')
        self.assertEqual(r['vitesse_camera'], 3.0); self.assertIs(r['camera_inverser_gd'], True)
        for lookup_key in ('distance_camera', 'angle_camera', 'camera_inverser_hb'): self.assertNotIn(lookup_key, written_data, lookup_key)
        self.assertEqual(written_data['vitesse_camera'], 3.0); self.assertIs(written_data['camera_inverser_gd'], True); self.assertNotIn('cam_pres', written_data['touches'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
