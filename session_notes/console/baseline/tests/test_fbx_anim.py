"""Tests de l'animation des modeles 3D (dq4_pc/fbx.py) : courbes d'Hermite, boucle du lecteur, melange de rotations.

    python3 tools/test_fbx_anim.py

  1. une rotation de 0 a 360 degres (clip a cles de quaternions tous les 90 degres, comme les modeles du jeu : `m_EulerCurves` est vide, les rotations sont des quaternions) tourne EN CONTINU, ni de quelques
     degres seulement, ni a l'envers ;
  2. le temps d'un clip en boucle est replie modulo sa duree (WrapMode.Loop) : deux tours = un tour ; un clip qui n'est pas une boucle reste sur sa derniere image ;
  3. le fondu entre deux clips melange les rotations du meme cote de la sphere : q et -q sont la meme rotation, leur moyenne ne doit ni s'annuler ni faire faire un demi-tour a l'os ;
     un melange de rotations proches (cas du dragon du titre) reste la simple moyenne ponderee, inchangee.
"""
import math, os, sys, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.world import fbx as F


def quat_y(deg):
    """Quaternion (x, y, z, w) d'une rotation de `deg` degres autour de Y."""
    a = math.radians(deg) / 2; return (0.0, math.sin(a), 0.0, math.cos(a))


def quat_curve(degrees_per_key, dt):
    """Courbe de rotation a 4 composantes : un quaternion tous les `dt` secondes, tangentes lineaires (pente d'une cle a la suivante), comme les cles reechantillonnees de l'import Unity."""
    t = [dt * k for k in range(len(degrees_per_key))]; v = np.array([quat_y(a) for a in degrees_per_key])
    slope = (v[1:] - v[:-1]) / dt
    sor = np.vstack([slope, slope[-1:]]); ent = np.vstack([slope[:1], slope])
    return F.Curve(t, v, ent, sor)


def one_bone_model(clips):
    """FbxModel minimal (un os, sans maillage) : seul `local` est utilise."""
    m = F.FbxModel.__new__(F.FbxModel)
    m.p0 = np.zeros((1, 3)); m.q0 = np.array([[0.0, 0.0, 0.0, 1.0]]); m.s0 = np.ones((1, 3)); m.clips = clips
    return m


def angle_y(q):
    """Rotation autour de Y (degres, entre -180 et 180) d'un quaternion normalise."""
    q = np.asarray(q, float); q = q / np.linalg.norm(q)
    if q[3] < 0: q = -q
    return math.degrees(2 * math.atan2(q[1], q[3]))


class TestCurves(unittest.TestCase):
    def test_values_at_keyframes(self):
        c = F.Curve([0.0, 1.0, 2.0], [0.0, 10.0, 0.0], [0.0] * 3, [0.0] * 3)
        self.assertEqual((c.value(0.0), c.value(1.0), c.value(2.0)), (0.0, 10.0, 0.0))
        self.assertAlmostEqual(c.value(0.5), 5.0); self.assertAlmostEqual(c.value(1.5), 5.0)       # Hermite a pentes nulles : milieu = moyenne
        self.assertEqual(c.value(-1.0), 0.0); self.assertEqual(c.value(9.0), 0.0)                  # hors des cles : on garde la premiere / derniere valeur

    def test_rotation_from_0_to_360_degrees_continuous(self):
        """TzKeys tous les 90 degres : l'angle de l'os croit regulierement de 0 a 360 (= 0), sans retour en arriere."""
        c = quat_curve([0, 90, 180, 270, 360], 1.0)
        prev = -1.0
        for k in range(0, 41):
            t = k / 10.0; a = angle_y(c.value(t))
            expected = (90.0 * t) % 360
            vu = a % 360
            self.assertAlmostEqual(math.sin(math.radians(vu)), math.sin(math.radians(expected)), delta=0.03, msg='t=%.1f' % t)      # nlerp entre deux cles de 90 degres : ecart < 1 degre
            self.assertAlmostEqual(math.cos(math.radians(vu)), math.cos(math.radians(expected)), delta=0.03, msg='t=%.1f' % t)
            if t < 4.0:
                self.assertGreater(vu, prev - 1e-9, 't=%.1f : retour en arriere' % t); prev = vu      # strictement croissant sur le tour


class TestPlayer(unittest.TestCase):
    CLIPS = {'Take 001': {'dur': 2.0, 'wrap': F.LOOP}, 'Take 002': {'dur': 1.0, 'wrap': 1}}

    def test_loop_modulo_duration(self):
        l = F.AnimPlayer(self.CLIPS); l.play(0, True, 0)
        for t in (0.0, 0.4, 1.3, 1.99):
            a = l.poses(t * F.ENGINE_FPS)[0][1]; b = l.poses((t + 2.0) * F.ENGINE_FPS)[0][1]; c = l.poses((t + 6.0) * F.ENGINE_FPS)[0][1]
            self.assertAlmostEqual(a, t, places=6); self.assertAlmostEqual(b, t, places=6); self.assertAlmostEqual(c, t, places=6)      # 1, 2 ou 4 tours plus tard : meme instant du clip

    def test_a_non_looping_clip_stays_on_its_last_frame(self):
        l = F.AnimPlayer(self.CLIPS); l.play(1, True, 0)
        self.assertAlmostEqual(l.poses(0.5 * F.ENGINE_FPS)[0][1], 0.5, places=6)
        for t in (1.0, 1.5, 10.0): self.assertAlmostEqual(l.poses(t * F.ENGINE_FPS)[0][1], 1.0, places=6)

    def test_fade_from_loop_increasing_weights(self):
        l = F.AnimPlayer(self.CLIPS); l.play(0, True, 0); l.play(1, False, 30)             # 1 s plus tard : fondu de 0,3 s vers « Take 002 »
        p = l.poses(30 + 0.15 * F.ENGINE_FPS)
        self.assertEqual([x[0] for x in p], ['Take 001', 'Take 002']); self.assertAlmostEqual(p[0][2], 0.5); self.assertAlmostEqual(p[1][2], 0.5)


class TestBlendRotations(unittest.TestCase):
    def model(self, qa, qb):
        z = [(0.0, 0.0, 0.0, 0.0)] * 2
        ca = F.Curve([0.0, 1.0], [qa, qa], z, z); cb = F.Curve([0.0, 1.0], [qb, qb], z, z)
        return one_bone_model({'A': {'dur': 1.0, 'wrap': 1, 'courbes': [(0, 'rot', ca)]}, 'B': {'dur': 1.0, 'wrap': 1, 'courbes': [(0, 'rot', cb)]}})

    def test_q_and_minus_q_same_rotation(self):
        """A = +10 degres, B = -(-10 degres) (meme rotation que -10, mais de l'autre cote de la sphere) : a mi-fondu, 0 degre ; avant : 180 degres."""
        m = self.model(quat_y(10), tuple(-x for x in quat_y(-10)))
        q = m.local([('A', 0.0, 0.5), ('B', 0.0, 0.5)])[1][0]
        self.assertAlmostEqual(angle_y(q), 0.0, places=6)
        q = m.local([('A', 0.0, 0.25), ('B', 0.0, 0.75)])[1][0]
        self.assertAlmostEqual(angle_y(q), -5.0, delta=0.05)

    def test_same_opposite_rotation_does_not_cancel(self):
        m = self.model(quat_y(40), tuple(-x for x in quat_y(40)))
        q = m.local([('A', 0.0, 0.5), ('B', 0.0, 0.5)])[1][0]
        self.assertAlmostEqual(float(np.linalg.norm(q)), 1.0, places=6); self.assertAlmostEqual(angle_y(q), 40.0, places=6)     # avant : quaternion nul

    def test_close_rotations_unchanged(self):
        """Du meme cote de la sphere : moyenne ponderee des composantes, comme avant."""
        qa, qb = quat_y(20), quat_y(80); m = self.model(qa, qb)
        q = m.local([('A', 0.0, 0.3), ('B', 0.0, 0.7)])[1][0]
        np.testing.assert_allclose(q, 0.3 * np.array(qa) + 0.7 * np.array(qb), atol=1e-12)

    def test_a_single_unchanged_pose(self):
        m = self.model(quat_y(20), tuple(-x for x in quat_y(80)))
        np.testing.assert_array_equal(m.local([('B', 0.0, 1.0)])[1][0], np.array([-x for x in quat_y(80)]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
