"""Tests de l'animation des modeles 3D (dq4_pc/fbx.py) : courbes d'Hermite, boucle du lecteur, melange de rotations.

    python3 outils/test_fbx_anim.py

  1. une rotation de 0 a 360 degres (clip a cles de quaternions tous les 90 degres, comme les modeles du jeu : `m_EulerCurves` est vide, les rotations sont des quaternions) tourne EN CONTINU, ni de quelques
     degres seulement, ni a l'envers ;
  2. le temps d'un clip en boucle est replie modulo sa duree (WrapMode.Loop) : deux tours = un tour ; un clip qui n'est pas une boucle reste sur sa derniere image ;
  3. le fondu entre deux clips melange les rotations du meme cote de la sphere : q et -q sont la meme rotation, leur moyenne ne doit ni s'annuler ni faire faire un demi-tour a l'os ;
     un melange de rotations proches (cas du dragon du titre) reste la simple moyenne ponderee, inchangee.
"""
import math, os, sys, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import fbx as F


def quat_y(deg):
    """Quaternion (x, y, z, w) d'une rotation de `deg` degres autour de Y."""
    a = math.radians(deg) / 2; return (0.0, math.sin(a), 0.0, math.cos(a))


def courbe_quat(degres_par_cle, dt):
    """Courbe de rotation a 4 composantes : un quaternion tous les `dt` secondes, tangentes lineaires (pente d'une cle a la suivante), comme les cles reechantillonnees de l'import Unity."""
    t = [dt * k for k in range(len(degres_par_cle))]; v = np.array([quat_y(a) for a in degres_par_cle])
    pente = (v[1:] - v[:-1]) / dt
    sor = np.vstack([pente, pente[-1:]]); ent = np.vstack([pente[:1], pente])
    return F.Courbe(t, v, ent, sor)


def modele_un_os(clips):
    """ModeleFbx minimal (un os, sans maillage) : seul `locales` est utilise."""
    m = F.ModeleFbx.__new__(F.ModeleFbx)
    m.p0 = np.zeros((1, 3)); m.q0 = np.array([[0.0, 0.0, 0.0, 1.0]]); m.s0 = np.ones((1, 3)); m.clips = clips
    return m


def angle_y(q):
    """Rotation autour de Y (degres, entre -180 et 180) d'un quaternion normalise."""
    q = np.asarray(q, float); q = q / np.linalg.norm(q)
    if q[3] < 0: q = -q
    return math.degrees(2 * math.atan2(q[1], q[3]))


class TestCourbes(unittest.TestCase):
    def test_valeurs_aux_cles(self):
        c = F.Courbe([0.0, 1.0, 2.0], [0.0, 10.0, 0.0], [0.0] * 3, [0.0] * 3)
        self.assertEqual((c.valeur(0.0), c.valeur(1.0), c.valeur(2.0)), (0.0, 10.0, 0.0))
        self.assertAlmostEqual(c.valeur(0.5), 5.0); self.assertAlmostEqual(c.valeur(1.5), 5.0)       # Hermite a pentes nulles : milieu = moyenne
        self.assertEqual(c.valeur(-1.0), 0.0); self.assertEqual(c.valeur(9.0), 0.0)                  # hors des cles : on garde la premiere / derniere valeur

    def test_rotation_de_0_a_360_degres_en_continu(self):
        """Cles tous les 90 degres : l'angle de l'os croit regulierement de 0 a 360 (= 0), sans retour en arriere."""
        c = courbe_quat([0, 90, 180, 270, 360], 1.0)
        prec = -1.0
        for k in range(0, 41):
            t = k / 10.0; a = angle_y(c.valeur(t))
            attendu = (90.0 * t) % 360
            vu = a % 360
            self.assertAlmostEqual(math.sin(math.radians(vu)), math.sin(math.radians(attendu)), delta=0.03, msg='t=%.1f' % t)      # nlerp entre deux cles de 90 degres : ecart < 1 degre
            self.assertAlmostEqual(math.cos(math.radians(vu)), math.cos(math.radians(attendu)), delta=0.03, msg='t=%.1f' % t)
            if t < 4.0:
                self.assertGreater(vu, prec - 1e-9, 't=%.1f : retour en arriere' % t); prec = vu      # strictement croissant sur le tour


class TestLecteur(unittest.TestCase):
    CLIPS = {'Take 001': {'dur': 2.0, 'wrap': F.LOOP}, 'Take 002': {'dur': 1.0, 'wrap': 1}}

    def test_boucle_modulo_la_duree(self):
        l = F.LecteurAnim(self.CLIPS); l.jouer(0, True, 0)
        for t in (0.0, 0.4, 1.3, 1.99):
            a = l.poses(t * F.FPS_MOTEUR)[0][1]; b = l.poses((t + 2.0) * F.FPS_MOTEUR)[0][1]; c = l.poses((t + 6.0) * F.FPS_MOTEUR)[0][1]
            self.assertAlmostEqual(a, t, places=6); self.assertAlmostEqual(b, t, places=6); self.assertAlmostEqual(c, t, places=6)      # 1, 2 ou 4 tours plus tard : meme instant du clip

    def test_un_clip_qui_n_est_pas_une_boucle_reste_sur_sa_derniere_image(self):
        l = F.LecteurAnim(self.CLIPS); l.jouer(1, True, 0)
        self.assertAlmostEqual(l.poses(0.5 * F.FPS_MOTEUR)[0][1], 0.5, places=6)
        for t in (1.0, 1.5, 10.0): self.assertAlmostEqual(l.poses(t * F.FPS_MOTEUR)[0][1], 1.0, places=6)

    def test_fondu_depuis_une_boucle_poids_croissants(self):
        l = F.LecteurAnim(self.CLIPS); l.jouer(0, True, 0); l.jouer(1, False, 30)             # 1 s plus tard : fondu de 0,3 s vers « Take 002 »
        p = l.poses(30 + 0.15 * F.FPS_MOTEUR)
        self.assertEqual([x[0] for x in p], ['Take 001', 'Take 002']); self.assertAlmostEqual(p[0][2], 0.5); self.assertAlmostEqual(p[1][2], 0.5)


class TestMelangeRotations(unittest.TestCase):
    def modele(self, qa, qb):
        z = [(0.0, 0.0, 0.0, 0.0)] * 2
        ca = F.Courbe([0.0, 1.0], [qa, qa], z, z); cb = F.Courbe([0.0, 1.0], [qb, qb], z, z)
        return modele_un_os({'A': {'dur': 1.0, 'wrap': 1, 'courbes': [(0, 'rot', ca)]}, 'B': {'dur': 1.0, 'wrap': 1, 'courbes': [(0, 'rot', cb)]}})

    def test_q_et_moins_q_meme_rotation(self):
        """A = +10 degres, B = -(-10 degres) (meme rotation que -10, mais de l'autre cote de la sphere) : a mi-fondu, 0 degre ; avant : 180 degres."""
        m = self.modele(quat_y(10), tuple(-x for x in quat_y(-10)))
        q = m.locales([('A', 0.0, 0.5), ('B', 0.0, 0.5)])[1][0]
        self.assertAlmostEqual(angle_y(q), 0.0, places=6)
        q = m.locales([('A', 0.0, 0.25), ('B', 0.0, 0.75)])[1][0]
        self.assertAlmostEqual(angle_y(q), -5.0, delta=0.05)

    def test_meme_rotation_opposee_ne_s_annule_pas(self):
        m = self.modele(quat_y(40), tuple(-x for x in quat_y(40)))
        q = m.locales([('A', 0.0, 0.5), ('B', 0.0, 0.5)])[1][0]
        self.assertAlmostEqual(float(np.linalg.norm(q)), 1.0, places=6); self.assertAlmostEqual(angle_y(q), 40.0, places=6)     # avant : quaternion nul

    def test_rotations_proches_inchangees(self):
        """Du meme cote de la sphere : moyenne ponderee des composantes, comme avant."""
        qa, qb = quat_y(20), quat_y(80); m = self.modele(qa, qb)
        q = m.locales([('A', 0.0, 0.3), ('B', 0.0, 0.7)])[1][0]
        np.testing.assert_allclose(q, 0.3 * np.array(qa) + 0.7 * np.array(qb), atol=1e-12)

    def test_une_seule_pose_inchangee(self):
        m = self.modele(quat_y(20), tuple(-x for x in quat_y(80)))
        np.testing.assert_array_equal(m.locales([('B', 0.0, 1.0)])[1][0], np.array([-x for x in quat_y(80)]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
