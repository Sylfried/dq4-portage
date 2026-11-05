"""Test de la logique pure des objets animes des cartes (sans fenetre, sans moteur, sans APK) : orientation propre des objets et sens des animations (coffres, tiroirs, portes) :

  1. `data.euler_mat` = FldObject.rotateXZY (0xCD47F0) : q = (AngleAxis(ry, haut) * AngleAxis(-rz, avant)) * AngleAxis(-rx, droite) : X appliquee d'abord, puis Z, puis Y (le cap en dernier).
     Re-calcule a part avec le produit de quaternions de Unity (celui du desassemblage : R = q2 * q3 puis R * q1) ;
  2. coffre qui s'ouvre (couvercle : mouvement commun, rotation -60 en X) : le couvercle pivote autour de la charniere DU COFFRE, quel que soit son cap (0, 90, -90, 180, -27 degres : tous les coffres de la
     meme famille s'ouvrent « vers l'arriere du coffre », jamais de cote), et a la meme vitesse ;
  3. tiroir (mouvement commun avec une cle de position) : le deplacement est dans le repere de l'objet (FldObject.c_pmv_func : MultiplyPoint(TRS(position, rotateXZY(rotation), echelle)) ; un
     mouvement ordinaire (pmv_func) ajoute le deplacement tel quel ;
  4. porte (rotation autour de Y seulement) : inchangee (cap de la porte + cap du mouvement) ;
  5. animations en continu (mouvements FPMV et sequences de maillages FSQD) : CHACUNE a son horloge (FldObject.fld_motion_update, une FLD_MOTION par animation) ; interpolation lineaire des angles d'Euler
     COMPOSANTE PAR COMPOSANTE (pmv_func : rotateXZY de la rotation interpolee, jamais de quaternion ni de plus court chemin) : 0 -> 360 degres tourne vraiment, boucle sans saut ; le rayon de soin
     `kifk01a` (rotation 0 -> 180 -> 360 en 800 / 60 s, sequence de 84 / 60 s) tourne d'un tour complet et non de 38 degres avant de revenir ;
  6. (si le cache de cartes existe : DQ_CACHE_CARTES, sinon /tmp/uicache_coffres) les VRAIS objets : les 194 coffres, les tiroirs et des portes de toutes les cartes.

    python3 tools/test_map_items.py
"""
import math, os, sys, unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.world.data import euler_mat
from dq4_pc.world import map_objects as OC


# ---- reference independante : quaternions de Unity
def qaxe(angle_deg, axis):
    a = math.radians(angle_deg) / 2; s = math.sin(a); return np.array([axis[0] * s, axis[1] * s, axis[2] * s, math.cos(a)])      # (x, y, z, w)


def qmul(a, b):
    """Produit de Hamilton a * b (b appliquee d'abord), (x, y, z, w) : formules du desassemblage."""
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz])


def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def game_rotate_xzy(rx, ry, rz):
    """FldObject.rotateXZY lue au desassemblage : q1 = AngleAxis(-rx, droite), q2 = AngleAxis(ry, haut), q3 = AngleAxis(-rz, avant) ; R = q2 * q3 ; resultat = R * q1."""
    q1 = qaxe(-rx, (1, 0, 0)); q2 = qaxe(ry, (0, 1, 0)); q3 = qaxe(-rz, (0, 0, 1))
    return qmat(qmul(qmul(q2, q3), q1))


def ry_mat(deg):
    b = math.radians(deg); return np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])


# ---- cartes minuscules
def map_object(pos, rot, local_pts, lookup_keys, movement_flag=4, scl=(1.0, 1.0, 1.0), end=10):
    """Une carte d'un objet : sommets `local_pts` (repere du modele) cuits a la position / rotation / echelle d'origine, une table d'animations communes a 4 entrees dont la 2e (numero 2) est
    un mouvement a deux cles (image 0 : rien ; image `end` : `lookup_keys`)."""
    pts = np.array(local_pts, np.float64)
    world = (np.array(pos, np.float64) + (euler_mat(*rot) @ np.diag(scl) @ pts.T).T).astype(np.float32)
    n = len(pts)
    ident = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
    def word(last_one): return dict(flag=movement_flag, nkey=2, repeat=1, delai=0, rdelai=0, fin=end, keys=[(0,) + ident, (end,) + last_one])
    words = [word(ident), word(lookup_keys), word(lookup_keys), word(ident)]
    words[0]['fin'] = 2; words[0]['keys'] = [(0,) + ident, (2,) + ident]
    obj = dict(i=0, pos=tuple(pos), rot=tuple(rot), scl=tuple(scl), mdl=1, canim=0, flag=0, seqobj=-1, pmv=-1, id=0, com=0, uid=0, prio=0, rest='')
    return {'objets': [obj], 'groupes': {'k': (world, np.zeros((n, 2), np.float32), np.ones((n, 4), np.float32))}, 'plages': {0: [('k', 0, n)]}, 'var': {},
            'tabs': [[(1, -1, 0), (1, -1, 1), (1, -1, 2), (1, -1, 3)]], 'mots': words, 'seqs': [], 'seqent': [], 'imgobj': {}}


def play(c, no=2, frames=20):
    oc = OC.MapObjects(c)
    oc.common_anim(0, no)
    for _ in range(frames): oc.tick()
    return oc.cur['k'].astype(np.float64)


# couvercle de coffre : charniere le long de l'axe X local (au pied du modele : origine = charniere), s'etend vers l'avant du coffre (-Z local), un peu d'epaisseur (Y)
LID = [(-0.4, 0, 0), (0.4, 0, 0), (-0.4, 0, -0.6), (0.4, 0, -0.6), (-0.4, 0.1, -0.3)]
OPENED = ((0.0, 0.0, 0.0), (-60.0, 0.0, 0.0), (1.0, 1.0, 1.0))                  # cle d'ouverture des 194 coffres du jeu : rotation X = -60


class TestGameRotation(unittest.TestCase):
    def test_rotation_order_like_game(self):
        rng = np.random.RandomState(7)
        for _ in range(50):
            rx, ry, rz = rng.uniform(-180, 180, 3)
            np.testing.assert_allclose(euler_mat(rx, ry, rz), game_rotate_xzy(rx, ry, rz), atol=1e-9)

    def test_x_first_in_the_object_frame(self):
        """La bascule en X (couvercle) se fait dans le repere de l'objet, puis le cap le tourne : Ry . Rx."""
        for cap in (0, 90, -90, 180, -27, 133):
            np.testing.assert_allclose(euler_mat(-60, cap, 0), euler_mat(0, cap, 0) @ euler_mat(-60, 0, 0), atol=1e-9)

    def test_simple_rotations_unchanged(self):
        for cap in (0, 45, 90, -90, 180):
            np.testing.assert_allclose(euler_mat(0, cap, 0), ry_mat(cap), atol=1e-12)
        r = euler_mat(-60, 0, 0) @ np.array([0, 0, -1.0])                           # cle -60 : le bord avant du couvercle monte et recule
        self.assertAlmostEqual(r[1], math.sin(math.radians(60))); self.assertAlmostEqual(r[2], -0.5); self.assertAlmostEqual(r[0], 0.0)


class TestChest(unittest.TestCase):
    def test_opening_follows_chest_heading(self):
        """Quel que soit le cap, le couvercle fini = celui du coffre de cap 0, tourne du cap (autour de la charniere)."""
        pos = (3.0, 0.5, -2.0)
        ref = play(map_object(pos, (0, 0, 0), LID, OPENED)) - np.array(pos)
        self.assertGreater(ref[2][1], 0.4)                                          # coffre de cap 0 : le bord avant se leve (0,6 x sin 60 = 0,52)
        for cap in (90, -90, 180, -27, 133):
            finished = play(map_object(pos, (0, cap, 0), LID, OPENED)) - np.array(pos)
            expected = (ry_mat(cap) @ ref.T).T
            np.testing.assert_allclose(finished, expected, atol=1e-5, err_msg='cap %d' % cap)

    def test_hinge_stays_put_and_lid_never_rolls(self):
        pos = (0.0, 0.5, 0.0)
        for cap in (0, 90, -90, 180, -27):
            c = map_object(pos, (0, cap, 0), LID, OPENED); before = c['groupes']['k'][0].astype(np.float64).copy()
            finished = play(c)
            np.testing.assert_allclose(finished[:2], before[:2], atol=1e-6)               # les deux sommets de la charniere ne bougent pas
            front_f = ry_mat(cap) @ np.array([0, 0, -1.0])                           # l'avant du coffre (axe de la charniere vers l'avant)
            d = (finished[2] - finished[0]); d = d / np.linalg.norm(d)                       # axe de la charniere -> bord avant du couvercle ouvert : dans le plan vertical de l'avant du coffre
            lateral = ry_mat(cap) @ np.array([1.0, 0, 0])                            # axe de la charniere : le deplacement lateral doit rester nul (ouverture « en livre », pas de roulis)
            self.assertAlmostEqual(float(d @ lateral), 0.0, places=5, msg='cap %d' % cap)
            self.assertGreater(float(d @ front_f), 0.0)

    def test_mid_travel_same_speed_at_all_headings(self):
        pos = (0.0, 0.5, 0.0)
        ref0 = None
        for cap in (0, 90, 180):
            oc = OC.MapObjects(map_object(pos, (0, cap, 0), LID, OPENED)); oc.common_anim(0, 2)
            for _ in range(3): oc.tick()                                             # 3 images du jeu = 6 / 60 s sur 10
            p = (ry_mat(cap).T @ (oc.cur['k'].astype(np.float64)[2] - np.array(pos)))
            if ref0 is None: ref0 = p
            np.testing.assert_allclose(p, ref0, atol=1e-5)
            self.assertTrue(0.05 < p[1] < 0.5)                                       # entre fermé et ouvert


class TestMovements(unittest.TestCase):
    DRAWER_KEYFRAME = ((0.0, 0.0, -0.5), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))             # le tiroir sort de 0,5 vers l'avant du meuble

    def test_common_movement_in_item_reference_frame(self):
        pos = (1.0, 0.0, 1.0); pts = [(0, 0, 0), (0.2, 0.1, 0)]
        for cap in (0, 90, -90, 180, -27):
            c = map_object(pos, (0, cap, 0), pts, self.DRAWER_KEYFRAME); before = c['groupes']['k'][0].astype(np.float64).copy()
            finished = play(c)
            np.testing.assert_allclose(finished - before, np.tile(ry_mat(cap) @ np.array([0, 0, -0.5]), (2, 1)), atol=1e-5, err_msg='cap %d' % cap)

    def test_common_movement_with_scale(self):
        pos = (0.0, 0.0, 0.0); pts = [(0, 0, 0)]
        c = map_object(pos, (0, 90, 0), pts, self.DRAWER_KEYFRAME, scl=(2.0, 1.0, 3.0)); before = c['groupes']['k'][0].astype(np.float64).copy()
        finished = play(c)
        np.testing.assert_allclose(finished - before, [(-0.5 * 3.0, 0, 0)], atol=1e-5)    # MultiplyPoint(TRS) : l'echelle de l'objet s'applique aussi au deplacement (z x 3, tourne de 90 degres)

    def test_ordinary_movement_displacement_as_is(self):
        pos = (0.0, 0.0, 0.0); pts = [(0, 0, 0)]
        c = map_object(pos, (0, 90, 0), pts, self.DRAWER_KEYFRAME, movement_flag=0); before = c['groupes']['k'][0].astype(np.float64).copy()
        finished = play(c)
        np.testing.assert_allclose(finished - before, [(0, 0, -0.5)], atol=1e-5)          # pmv_func : position de l'objet + cle, sans rotation

    def test_engine_order_position_and_heading(self):
        """SetMapObjPos / SetMapObjRot (paquets 3 et 4) puis mouvement commun : la base du mouvement est la position et le cap COURANTS de l'objet (c_pmv_func lit les champs de l'objet)."""
        pts = [(0, 0, 0)]
        c = map_object((0.0, 0.0, 0.0), (0, 0, 0), pts, self.DRAWER_KEYFRAME); oc = OC.MapObjects(c)
        oc.position(0, (5.0, 0.0, 5.0)); oc.rotation(0, (0.0, 90.0)); oc.common_anim(0, 2)
        for _ in range(20): oc.tick()
        np.testing.assert_allclose(oc.cur['k'].astype(np.float64)[0], (5.0 - 0.5, 0.0, 5.0), atol=1e-5)

    def test_door_around_y_unchanged(self):
        pts = [(0, 0, 0), (0.0, 0.0, 1.0), (0.0, 1.0, 1.0)]
        for cap in (0, 90, -90, 180):
            c = map_object((0, 0, 0), (0, cap, 0), pts, ((0, 0, 0), (0, -90, 0), (1, 1, 1))); finished = play(c)
            np.testing.assert_allclose(finished, np.array([ry_mat(cap - 90) @ np.array(p, float) for p in pts]), atol=1e-5)


# ---- animations en continu : une horloge par animation
def auto_map_object(local_pts, lookup_keys, end, repeat=-1, delay=0, rdelai=0, seq_end=None, common=False, pos=(0.0, 0.0, 0.0)):
    """Une carte d'un objet qui tourne : mouvement FPMV a cles (image, rotation) joue en continu (ou lance par SetCommonAnimation 1 si `common`), avec en plus, si `seq_end`, une sequence de maillages
    de duree propre (deux images de sommets : l'objet et le meme decale de 0,5 en hauteur)."""
    pts = np.array(local_pts, np.float64); n = len(pts); world = (np.array(pos, np.float64) + pts).astype(np.float32)
    word = dict(flag=0, nkey=len(lookup_keys), repeat=repeat, delai=delay, rdelai=rdelai, fin=end, keys=[(f, (0.0, 0.0, 0.0), tuple(float(v) for v in r), (1.0, 1.0, 1.0)) for f, r in lookup_keys])
    obj = dict(i=0, pos=tuple(pos), rot=(0.0, 0.0, 0.0), scl=(1.0, 1.0, 1.0), mdl=1, canim=0 if common else -1, flag=0, seqobj=-1, pmv=-1 if common else 0, id=0, com=0, uid=0, prio=0, rest='')
    c = {'objets': [obj], 'groupes': {'k': (world, np.zeros((n, 2), np.float32), np.ones((n, 4), np.float32))}, 'plages': {0: [('k', 0, n)]}, 'var': {}, 'tabs': [], 'mots': [word],
         'seqs': [], 'seqent': [], 'imgobj': {}}
    if seq_end:
        c['seqs'] = [dict(flag=0, nkey=3, repeat=-1, delai=0, rdelai=0, fin=seq_end, keys=[(0, 0), (seq_end // 2, 1), (seq_end, 0)])]
        c['seqent'] = [(0, 0, 0, 0, 0, -1, 0, -1)]                              # (objet, sequence, groupe, delai de depart, delai entre deux tours, nombre de tours, _, nombre de tours d'origine)
        c['imgobj'] = {0: [{'pos': np.stack([world, world + np.array([0.0, 0.5, 0.0], np.float32)]), 'uv': None, 'col': None}]}
        if common: c['tabs'] = [[(1, 0, 0)]]
        else: obj['seqobj'] = 0
    elif common: c['tabs'] = [[(1, -1, 0)]]
    return c


def turn(c, ticks, common=False):
    oc = OC.MapObjects(c)
    if common: oc.common_anim(0, 1)
    for _ in range(ticks): oc.tick()
    return oc


def map_vertices(oc): return oc.cur['k'].astype(np.float64)


PTS = [(1.0, 0.0, 0.0), (0.0, 0.0, 2.0), (-0.5, 1.0, 0.0)]


class TestClocks(unittest.TestCase):
    """ExampleCounter d'une animation (FldObject.fld_motion_update) : delai de depart, tours, delai entre deux tours, tenue sur la derniere cle."""

    def advance_time(self, delay, rdelai, rep, end, n):
        h = OC._clock(delay, rdelai, rep, end); suite = []
        for _ in range(n): OC._advance(h); suite.append(h['temps'])
        return h, suite

    def test_endless_loop(self):
        h, t = self.advance_time(0, 0, -1, 10, 12)
        self.assertEqual(t, [2, 4, 6, 8, 10, 2, 4, 6, 8, 10, 2, 4])               # a la fin exacte on reste sur la derniere cle ; au-dela, retour au debut par le reste du depassement
        self.assertFalse(h['fini'])

    def test_overshoot_kept(self):
        h, t = self.advance_time(0, 0, -1, 9, 7)
        self.assertEqual(t, [2, 4, 6, 8, 1, 3, 5])                                 # 10 > 9 : 10 - 9 = 1

    def test_initial_delay(self):
        h, t = self.advance_time(5, 0, -1, 10, 6)
        self.assertEqual(t, [0, 0, 0, 2, 4, 6])                                    # delai 5 : 3 images a l'image 0 (5, 3, 1 >= 1), puis le temps avance

    def test_finite_turn_count_then_stop_on_last_key(self):
        h, t = self.advance_time(0, 0, 2, 6, 12)
        self.assertEqual(t[:9], [2, 4, 6, 2, 4, 6, 6, 6, 6]); self.assertTrue(h['fini'])      # 2 tours puis tenue a la fin

    def test_delay_between_two_turns(self):
        h, t = self.advance_time(0, 4, -1, 4, 8)
        self.assertEqual(t, [2, 4, 2, 0, 0, 2, 4, 2])                              # 2, 4, (6 > 4 : reste 2), delai de 4 : 2 images a 0

    def test_two_independent_clocks(self):
        a = OC._clock(0, 0, -1, 84); b = OC._clock(0, 0, -1, 800)
        for _ in range(100): OC._advance(a); OC._advance(b)
        self.assertEqual(b['temps'], 200); self.assertEqual(a['temps'], 32)


class TestRotationsEuler(unittest.TestCase):
    """Interpolation des rotations d'un mouvement : angles d'Euler, lineaires, composante par composante (pmv_func : rotateXZY(rotation interpolee)) ; une image du jeu = 2 / 60 s."""

    def check(self, c, ticks, expected_euler, msg=''):
        oc = turn(c, ticks)
        np.testing.assert_allclose(map_vertices(oc), (euler_mat(*expected_euler) @ np.array(PTS).T).T, atol=1e-5, err_msg=msg)

    def test_0_to_360_turns_continuously(self):
        c = auto_map_object(PTS, [(0, (0, 0, 0)), (400, (0, 360, 0))], 400)
        for k in range(0, 201, 5): self.check(c, k, (0, 1.8 * k, 0), 'tick %d' % k)       # 400 / 60 s = 200 images : 1,8 degre par image, sans aucun retour en arriere
        oc = turn(c, 100); np.testing.assert_allclose(map_vertices(oc), np.array(PTS) * [-1, 1, -1], atol=1e-5)     # a mi-course : demi-tour exact (pas une rotation nulle)

    def test_loop_after_one_turn(self):
        c = auto_map_object(PTS, [(0, (0, 0, 0)), (400, (0, 360, 0))], 400)
        for k in (0, 1, 7, 50, 133):
            np.testing.assert_allclose(map_vertices(turn(c, 200 + k)), map_vertices(turn(c, k)), atol=1e-5)      # le deuxieme tour reprend exactement le premier
        np.testing.assert_allclose(map_vertices(turn(c, 400 + 33)), map_vertices(turn(c, 33)), atol=1e-5)

    def test_four_quarter_turns(self):
        lookup_keys = [(0, (0, 0, 0)), (100, (0, 90, 0)), (200, (0, 180, 0)), (300, (0, 270, 0)), (400, (0, 360, 0))]
        c = auto_map_object(PTS, lookup_keys, 400)
        for tick, ang in ((25, 45), (50, 90), (75, 135), (100, 180), (125, 225), (150, 270), (175, 315), (200, 360)): self.check(c, tick, (0, ang, 0), 'tick %d' % tick)

    def test_negative_angles(self):
        c = auto_map_object(PTS, [(0, (0, 0, 0)), (100, (0, -90, 0)), (400, (0, -360, 0))], 400)
        for tick, ang in ((25, -45), (50, -90), (125, -225), (200, -360)): self.check(c, tick, (0, ang, 0), 'tick %d' % tick)

    def test_no_shortest_path(self):
        """0 -> 270 degres : le jeu passe par 135 a mi-course ; un slerp de quaternions irait en arriere vers -45."""
        c = auto_map_object(PTS, [(0, (0, 0, 0)), (400, (0, 270, 0))], 400)
        self.check(c, 100, (0, 135, 0))
        oc = turn(c, 100); self.assertFalse(np.allclose(map_vertices(oc), (euler_mat(0, -45, 0) @ np.array(PTS).T).T, atol=1e-3))

    def test_component_by_component(self):
        c = auto_map_object(PTS, [(0, (0, 0, 0)), (400, (60, 120, 90))], 400)
        self.check(c, 50, (15, 30, 22.5)); self.check(c, 100, (30, 60, 45))      # Quaternion.Euler(lerp(x), lerp(y), lerp(z)), pas la rotation du quaternion intermediaire

    def test_holds_last_keyframe_when_turns_are_finished(self):
        c = auto_map_object(PTS, [(0, (0, 0, 0)), (100, (0, 90, 0))], 100, repeat=2)
        self.check(c, 25, (0, 45, 0)); self.check(c, 50, (0, 90, 0)); self.check(c, 60, (0, 18, 0)); self.check(c, 300, (0, 90, 0))   # 120 > 100 : 2e tour a 20 / 100 (18 degres), puis 90 pour toujours

    def test_a_non_looping_animation_does_not_restart(self):
        c = auto_map_object(PTS, [(0, (0, 0, 0)), (100, (0, 90, 0))], 100, repeat=1)
        self.check(c, 50, (0, 90, 0)); self.check(c, 500, (0, 90, 0))


class TestOneClockPerAnimation(unittest.TestCase):
    """Cause du faisceau de soin qui « tournait de 5 degres puis revenait » : le mouvement (800 / 60 s) et la sequence de maillages (84 / 60 s) de l'objet partageaient UNE horloge qui bouclait a 84."""

    KEYFRAMES = [(0, (0, 0, 0)), (400, (0, 180, 0)), (800, (0, 360, 0))]

    def test_sequence_does_not_shorten_movement(self):
        c = auto_map_object(PTS, self.KEYFRAMES, 800, seq_end=84)
        oc = turn(c, 100); st = oc.state[0]
        self.assertEqual(st['tmot'], 200); self.assertEqual(st['tseq'], 32)           # chacune son temps (avant : 32 pour les deux)
        self.assertEqual(oc.auto[0]['hm']['fin'], 800); self.assertEqual(oc.auto[0]['hs']['fin'], 84)
        without = auto_map_object(PTS, self.KEYFRAMES, 800); ref = turn(without, 100)
        topmost = map_vertices(oc)[:, 1] - map_vertices(ref)[:, 1]
        np.testing.assert_allclose(map_vertices(oc)[:, [0, 2]], map_vertices(ref)[:, [0, 2]], atol=1e-5)       # la meme rotation (90 degres), avec ou sans sequence
        self.assertTrue(np.all(np.abs(topmost) <= 0.5 + 1e-6))                           # la sequence ne fait que deplacer les sommets d'une image a l'autre

    def test_a_full_turn_despite_the_short_sequence(self):
        c = auto_map_object(PTS, self.KEYFRAMES, 800, seq_end=84); without = auto_map_object(PTS, self.KEYFRAMES, 800)
        for k in (0, 10, 50, 100, 150, 200, 250, 399):
            a = map_vertices(turn(c, k)); b = map_vertices(turn(without, k))
            np.testing.assert_allclose(a[:, [0, 2]], b[:, [0, 2]], atol=1e-5, err_msg='tick %d' % k)
            np.testing.assert_allclose(b, (euler_mat(0, 0.9 * k, 0) @ np.array(PTS).T).T, atol=1e-5)          # 800 / 60 s = 400 images : 0,9 degre par image

    def test_shared_animation_one_clock_per_animation(self):
        c = auto_map_object(PTS, [(0, (0, 0, 0)), (800, (0, 360, 0))], 800, seq_end=84, common=True)
        c['mots'][0]['repeat'] = -1; oc = turn(c, 100, common=True)
        self.assertEqual(oc.state[0]['tmot'], 200); self.assertEqual(oc.state[0]['tseq'], 32)
        without = turn(auto_map_object(PTS, [(0, (0, 0, 0)), (800, (0, 360, 0))], 800, common=True), 100, common=True)
        np.testing.assert_allclose(map_vertices(oc)[:, [0, 2]], map_vertices(without)[:, [0, 2]], atol=1e-5)

    def test_state_stored_by_old_version(self):
        """Un etat instantane d'avant la correction (une seule horloge : `clock`, entrees `auto` a plat) se recharge et continue sans erreur."""
        c = auto_map_object(PTS, self.KEYFRAMES, 800, seq_end=84); oc = OC.MapObjects(c); sq, eng = oc.auto[0]['seq'], oc.auto[0]['mot']
        auto_old = {0: dict(seq=sq, mot=eng, delai=0, rdelai=0, rep=-1, fin=84, temps=40, fini=False)}
        old_state = {0: {'mdl': 1, 'off': False, 'alpha': 31, 'pos': None, 'rot': None, 'mot': eng, 'seq': sq, 'temps': 40}}
        oc.restore(old_state, auto_old)
        self.assertEqual(oc.auto[0]['hs']['temps'], 40); self.assertEqual(oc.auto[0]['hm']['temps'], 40)
        oc.tick(); self.assertEqual(oc.state[0]['tmot'], 42); self.assertEqual(oc.state[0]['tseq'], 42)
        for _ in range(50): oc.tick()
        self.assertEqual(oc.state[0]['tmot'], 142); self.assertEqual(oc.state[0]['tseq'], 142 - 84)         # a partir de la, chacune boucle a sa duree


def expected_clock(end, ticks):
    t = 0
    for _ in range(ticks):
        t += OC.STEP
        if t > end: t -= end
    return t


def real_maps():
    """Cartes du cache de l'utilisateur (carte10_*.pkl) : `DQ_CACHE_CARTES`, sinon /tmp/uicache_coffres ; vide si le cache n'existe pas (les tests ci-dessous sont alors ignores)."""
    import glob
    return sorted(glob.glob(os.path.join(os.environ.get('DQ_CACHE_CARTES', '/tmp/uicache_coffres'), 'carte10_*.pkl')))


@unittest.skipUnless(real_maps(), 'pas de cache de cartes (carte10_*.pkl)')
class TestRealMaps(unittest.TestCase):
    """Les vrais objets du jeu : tous les coffres (modele `tbox02` = le couvercle, `tbox01` = le corps), tiroirs (`hikidashi1b`) et portes de toutes les cartes, joues de bout en bout."""

    @staticmethod
    def load(f):
        import pickle
        with open(f, 'rb') as fh: return pickle.load(fh)

    @staticmethod
    def vertices(c, oc, i):
        return np.concatenate([oc.cur[key][d:d + n] for key, d, n in c['plages'][i]]).astype(np.float64)

    def objects(self, pattern):
        """[(carte, c, i)] des objets dont le nom de modele finit par `pattern` et qui ont des animations communes."""
        res = []
        for f in real_maps():
            c = self.load(f)
            for i, o in enumerate(c['objets']):
                if c['noms'].get(i, '').endswith(pattern) and 0 <= o['canim'] < len(c['tabs']) and i in c['plages']: res.append((os.path.basename(f), c, i))
        return res

    def test_all_chests_open_around_their_hinge(self):
        chests = self.objects('tbox02'); self.assertGreater(len(chests), 150)
        caps = set()
        for name_str, c, i in chests:
            o = c['objets'][i]; pos = np.array(o['pos'], np.float64); R = euler_mat(*o['rot']); caps.add(round(o['rot'][1]))
            oc = OC.MapObjects(c); closed = self.vertices(c, oc, i)
            oc.common_anim(i, 2)                                                    # SetCommonAnimation 2 = ouverture (TownFurnitureObject::openObject), 4 = fermeture
            for _ in range(20): oc.tick()
            opened = self.vertices(c, oc, i); msg = '%s objet %d cap %s' % (name_str, i, o['rot'])
            np.testing.assert_allclose(np.linalg.norm(opened - pos, axis=1), np.linalg.norm(closed - pos, axis=1), atol=1e-4, err_msg=msg)       # rotation rigide autour de l'origine du modele (la charniere)
            axis = R @ np.array([1.0, 0.0, 0.0])                                      # la charniere est l'axe X du coffre
            np.testing.assert_allclose((opened - closed) @ axis, 0.0, atol=1e-4, err_msg=msg)       # aucun mouvement le long de la charniere : le couvercle ne roule jamais de cote
            topmost = np.argmax(opened[:, 1]); self.assertGreater(opened[topmost, 1] - closed[:, 1].max(), 0.1, msg)    # le bord libre monte...
            dec = (opened[topmost] - closed[topmost]) @ (R @ np.array([0.0, 0.0, 1.0]))     # ... et recule vers l'arriere du coffre (+Z du modele, le devant est -Z)
            self.assertGreater(dec, 0.1, msg)
        self.assertTrue({90, -90, 180, -180, -27} <= caps or len(caps) > 1, caps)    # les caps non nuls existent dans les donnees (ss5b1b, hcy1b1, tcf1, mdi1f1...)

    def test_chests_reclose_to_initial_state(self):
        for name_str, c, i in self.objects('tbox02')[:40]:
            oc = OC.MapObjects(c); closed = self.vertices(c, oc, i)
            oc.common_anim(i, 2)
            for _ in range(20): oc.tick()
            oc.common_anim(i, 4)                                                    # fermeture
            for _ in range(20): oc.tick()
            np.testing.assert_allclose(self.vertices(c, oc, i), closed, atol=1e-4, err_msg='%s objet %d' % (name_str, i))

    def test_drawers_come_out_toward_the_front_of_the_furniture(self):
        drawers = self.objects('hikidashi1b'); self.assertGreater(len(drawers), 10)
        vu = set()
        for name_str, c, i in drawers:
            o = c['objets'][i]; oc = OC.MapObjects(c); closed = self.vertices(c, oc, i)
            oc.common_anim(i, 2)
            for _ in range(20): oc.tick()
            dep = self.vertices(c, oc, i) - closed
            lookup_key = np.array(c['mots'][c['tabs'][o['canim']][1][2]]['keys'][-1][1], np.float64)       # cle d'arrivee de l'animation 2 : un tiroir sort vers l'avant (-Z) de son meuble, de 0,25 (ou 1) selon le modele
            self.assertEqual((lookup_key[0], lookup_key[1]), (0.0, 0.0)); self.assertLess(lookup_key[2], 0.0)
            expected = euler_mat(*o['rot']) @ (np.array(o['scl'], np.float64) * lookup_key)  # tournee du cap du meuble (repere de l'objet)
            np.testing.assert_allclose(dep, np.tile(expected, (len(dep), 1)), atol=1e-4, err_msg='%s objet %d cap %s' % (name_str, i, o['rot']))
            vu.add(round(o['rot'][1]))
        self.assertGreater(len(vu), 1)                                               # des tiroirs de caps differents (0, 90, -90, -6, -2)

    def test_doors_opened_around_vertical_hinge(self):
        for pattern in ('door01', 'wdoor04'):
            for name_str, c, i in self.objects(pattern)[:60]:
                o = c['objets'][i]; pos = np.array(o['pos'], np.float64); oc = OC.MapObjects(c); closed = self.vertices(c, oc, i)
                oc.common_anim(i, 2)
                for _ in range(20): oc.tick()
                opened = self.vertices(c, oc, i); msg = '%s objet %d' % (name_str, i)
                np.testing.assert_allclose(opened[:, 1], closed[:, 1], atol=1e-4, err_msg=msg)            # la porte tourne autour de la verticale : aucune hauteur ne change
                np.testing.assert_allclose(np.hypot(opened[:, 0] - pos[0], opened[:, 2] - pos[2]), np.hypot(closed[:, 0] - pos[0], closed[:, 2] - pos[2]), atol=1e-4, err_msg=msg)


@unittest.skipUnless(real_maps(), 'pas de cache de cartes (carte10_*.pkl)')
class TestRealContinuousAnimations(unittest.TestCase):
    """Les vraies cartes : rayon de soin (`kifk01a`, cartes cmf1c, dmb2, tab1a) et toutes les animations en continu."""

    @staticmethod
    def load(name_str):
        import pickle
        for f in real_maps():
            if os.path.basename(f) == 'carte10_%s.pkl' % name_str:
                with open(f, 'rb') as fh: return pickle.load(fh)
        return None

    def test_healing_ray_turns_a_full_circle(self):
        vu = 0
        for name_str in ('cmf1c', 'dmb2', 'tab1a'):
            c = self.load(name_str)
            if c is None: continue
            io = [i for i, n in c['noms'].items() if n.endswith('kifk01a')]; self.assertEqual(len(io), 1, name_str); io = io[0]
            o = c['objets'][io]; eng = c['mots'][o['pmv']]
            self.assertEqual((eng['repeat'], eng['fin'], [k[2][1] for k in eng['keys']]), (-1, 800, [0.0, 180.0, 360.0]), name_str)       # donnees : 0 -> 180 -> 360 en 800 / 60 s, sans fin
            without = dict(c, imgobj={k: v for k, v in c['imgobj'].items() if k != io})                   # mouvement seul (sans la sequence de maillages) pour mesurer la rotation
            ref = OC.MapObjects(without); pos0 = np.array(o['pos'], np.float64)
            def pts(oc): return np.concatenate([oc.cur[key][d:d + n] for key, d, n in c['plages'][io]]).astype(np.float64)
            initial = pts(ref)
            for k in (50, 100, 150, 200, 300, 399):
                for _ in range(k - getattr(ref, '_k', 0)): ref.tick()
                ref._k = k
                att = pos0 + (euler_mat(0, 0.9 * k, 0) @ (initial - pos0).T).T                           # 0,9 degre par image : 45 degres a 50 images, 90 a 100, 180 a 200
                np.testing.assert_allclose(pts(ref), att, atol=2e-4, err_msg='%s tick %d' % (name_str, k))
            actual = OC.MapObjects(c)
            for _ in range(100): actual.tick()
            st = actual.state[io]; self.assertEqual((st['tmot'], st['tseq']), (200, expected_clock(84, 100)), name_str)         # sequence de 84 : sa propre horloge
            vu += 1
        self.assertGreater(vu, 0)

    def test_clocks_of_all_continuous_animations(self):
        """Pour toutes les cartes : chaque mouvement et chaque sequence en continu (sans delai) a son temps = (2 x images) replie a SA duree."""
        n_doubles = 0
        for f in real_maps():
            c = self.load(os.path.basename(f)[8:-4])
            if os.path.basename(f).startswith('carte10_btl_'): continue
            oc = OC.MapObjects(c)
            for _ in range(137): oc.tick()
            for i, a in oc.auto.items():
                for h, lookup_key in ((a['hs'], 'tseq'), (a['hm'], 'tmot')):
                    if h is None or h['rep'] != -1 or h['rdelai']: continue
                    if h['fin'] == 0: continue
                    d0 = (c['seqent'][c['objets'][i]['seqobj']][3] if lookup_key == 'tseq' else a['mot']['delai'])
                    if d0: continue
                    self.assertEqual(oc.state[i][lookup_key], expected_clock(h['fin'], 137), '%s objet %d %s' % (os.path.basename(f), i, lookup_key))
                if a['hs'] and a['hm']: n_doubles += 1
        self.assertGreater(n_doubles, 20)                                                   # des dizaines d'objets ont les deux animations (torches, oiseaux, cascades, rayons de soin...)


if __name__ == '__main__':
    unittest.main(verbosity=2)
