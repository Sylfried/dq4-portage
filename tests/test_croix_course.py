"""Test : la croix de l'ecran fait DEUX FOIS la taille du mobile, et le heros court quand elle est tenue au bord de son anneau (04/11/2026).

    python3 outils/test_croix_course.py

1. Taille : `hud_mobile.DIAM_CROIX` = 1,5 x 161,28 (le double de #169 moins 25 %, #172) ; diametre a l'ecran = H / 800 x DIAM_CROIX x option du jeu x reglage « Taille de la croix » (67 % = la taille du mobile).
2. Course : `Boutons.croix_course()` vaut vrai au bord de l'anneau (COURSE_SEUIL du rayon ou plus, dans une direction), faux plus pres du centre, dans la zone morte, croix lachee ou non tenue ; la direction envoyee au jeu ne change pas.
3. Vitesse (vraie `Jeu._facteur_vitesse`, faux jeu et vraie croix) : marche normale (x vitesse de marche) tant que le pointeur est dans l'anneau, x multiplicateur de l'accelerateur au bord ; la touche d'accelerateur
   fait toujours courir, et les deux ensemble ne se cumulent pas.
"""
import os, sys, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI); sys.path.insert(0, os.path.join(ICI, '..'))
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.noyau import moteur as MO
import test_croix_et_clic as TC

try:
    from dq4_pc.fenetre import jeu as F
except Exception as ex:
    F = None


class Taille(unittest.TestCase):
    def test_constante_une_fois_et_demie_le_mobile(self):
        self.assertAlmostEqual(HM.DIAM_CROIX, 1.5 * 161.28, places=6)
        self.assertAlmostEqual(HM.DIAM_CROIX, 0.75 * 2 * 161.28, places=6)                                 # (le double de #169, moins 25 % : #172)

    def test_diametre_a_l_ecran(self):
        J = TC.faux_jeu(1280, 800); b = HM.Boutons(J)
        self.assertAlmostEqual(b.diametre_croix(), 241.92, places=4, msg='800 de haut, option du jeu moyenne, reglage 100 % : une fois et demie le mobile')
        J.reg['croix_taille'] = 0.5; self.assertAlmostEqual(b.diametre_croix(), 120.96, places=4, msg='reglage a 50 %')
        J.reg['croix_taille'] = 2.0; self.assertAlmostEqual(b.diametre_croix(), 483.84, places=4)

    def test_proportionnel_a_la_hauteur(self):
        d720 = HM.Boutons(TC.faux_jeu(1280, 720)).diametre_croix(); d1080 = HM.Boutons(TC.faux_jeu(1920, 1080)).diametre_croix()
        self.assertAlmostEqual(d1080 / d720, 1.5, places=6)

    def test_fenetre_etroite_la_croix_est_reduite_pour_tenir(self):
        b = HM.Boutons(TC.faux_jeu(394, 1102)); self.assertAlmostEqual(b.diametre_croix(), HM.LARGEUR_CROIX_MAX * 394, places=6)
        b = HM.Boutons(TC.faux_jeu(450, 800)); self.assertLessEqual(b.diametre_croix(), 0.75 * 450 + 1e-6)
        b = HM.Boutons(TC.faux_jeu(1280, 720)); self.assertAlmostEqual(b.diametre_croix(), 720 / 800.0 * 241.92, places=4, msg='16:9 : jamais reduite')

    def test_la_croix_reste_dans_l_ecran(self):
        for W, H in ((1280, 720), (1920, 1080), (1866, 1050), (394, 1102), (3440, 1440)):
            b = HM.Boutons(TC.faux_jeu(W, H)); rx, ry, c, _ = b.rect(HM.CROIX)
            self.assertGreaterEqual(rx, -1e-6, (W, H)); self.assertGreaterEqual(ry, -1e-6, (W, H)); self.assertLessEqual(rx + c, W + 1e-6, (W, H)); self.assertLessEqual(ry + c, H + 1e-6, (W, H))


class Course(unittest.TestCase):
    def setUp(self):
        self.J = TC.faux_jeu(); self.b = HM.Boutons(self.J); rx, ry, c, _ = self.b.rect(HM.CROIX); self.cx, self.cy, self.r = rx + c / 2, ry + c / 2, c / 2; self.vis = (HM.CROIX,)

    def tenir(self, dx, dy):
        self.b.appuyer(self.cx, self.cy, self.vis); self.b.croix_glisser(self.cx + dx * self.r, self.cy + dy * self.r)

    def test_non_tenue(self): self.assertFalse(self.b.croix_course())

    def test_seuil(self):
        for rayon, attendu in ((0.05, False), (0.2, False), (0.5, False), (HM.COURSE_SEUIL - 0.01, False), (HM.COURSE_SEUIL, True), (1.0, True), (1.178, True), (1.6, True)):
            self.tenir(0.0, rayon); self.assertEqual(self.b.croix_course(), attendu, 'rayon %.3f' % rayon); self.b.croix_lacher()

    def test_toutes_directions(self):
        import math
        for deg in range(0, 360, 15):
            self.tenir(math.sin(math.radians(deg)) * 1.0, math.cos(math.radians(deg)) * 1.0); self.assertTrue(self.b.croix_course(), deg)
            self.tenir(math.sin(math.radians(deg)) * 0.5, math.cos(math.radians(deg)) * 0.5); self.assertFalse(self.b.croix_course(), deg)

    def test_lachee(self):
        self.tenir(0.0, 1.0); self.assertTrue(self.b.croix_course()); self.b.croix_lacher(); self.assertFalse(self.b.croix_course())

    def test_la_direction_ne_change_pas(self):
        self.tenir(0.0, 0.5); proche = self.b.croix_bits(); self.tenir(0.0, 1.0); self.assertEqual(self.b.croix_bits(), proche); self.assertEqual(proche, MO.HAUT)

    def test_le_toucher_central_n_est_pas_une_course(self):
        self.b.appuyer(self.cx, self.cy, self.vis); self.assertFalse(self.b.croix_course()); self.assertTrue(self.b.croix_relacher())


def faux_marche(hud, accel_tenue=False, marche=1.0, accel=1.5):
    mo = types.SimpleNamespace(etat=types.SimpleNamespace(partie=MO.PARTIE_CHAMP, effet=None, attente_charge=None, garde_trans=0), msg_visible=False, menu_actif=lambda: None, drapeaux=lambda: 0x28)
    J = types.SimpleNamespace(reg={'vitesse_marche': marche, 'vitesse_accel': accel, 'vitesse_combat': 0}, moteur=mo, pause=types.SimpleNamespace(ouvert=False), hud=hud, pad=lambda: MO.HAUT, _tenue=lambda a: accel_tenue and a == 'accel')
    J._horloge_combat = lambda: F.Jeu._horloge_combat(J)
    return J


@unittest.skipIf(F is None, 'fenetre.py non importable ici')
class Vitesse(unittest.TestCase):
    def setUp(self):
        self.J0 = TC.faux_jeu(); self.b = HM.Boutons(self.J0); rx, ry, c, _ = self.b.rect(HM.CROIX); self.cx, self.cy, self.r = rx + c / 2, ry + c / 2, c / 2
        self.b.appuyer(self.cx, self.cy, (HM.CROIX,))

    def facteur(self, **kw): return F.Jeu._facteur_vitesse(faux_marche(self.b, **kw))

    def test_dans_l_anneau_marche_normale(self):
        self.b.croix_glisser(self.cx, self.cy + 0.5 * self.r); self.assertEqual(self.facteur(), 1.0)
        self.assertEqual(self.facteur(marche=2.0), 2.0, 'la vitesse de marche du reglage reste appliquee')

    def test_au_bord_course(self):
        self.b.croix_glisser(self.cx, self.cy + 1.0 * self.r); self.assertEqual(self.facteur(), 1.5); self.assertEqual(self.facteur(marche=2.0), 3.0)

    def test_touche_d_accelerateur_toujours_valable(self):
        self.b.croix_glisser(self.cx, self.cy + 0.5 * self.r); self.assertEqual(self.facteur(accel_tenue=True), 1.5)

    def test_pas_de_cumul(self):
        self.b.croix_glisser(self.cx, self.cy + 1.0 * self.r); self.assertEqual(self.facteur(accel_tenue=True), 1.5)

    def test_croix_lachee(self):
        self.b.croix_glisser(self.cx, self.cy + 1.0 * self.r); self.b.croix_lacher(); self.assertEqual(F.Jeu._facteur_vitesse(faux_marche(self.b)), 1.0)


if __name__ == '__main__':
    unittest.main(verbosity=1)
