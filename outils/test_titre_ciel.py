"""Test de la logique pure du ciel de l'ecran-titre en format large (`dq4_pc/ciel_titre.py` : sans fenetre, sans moteur, sans APK) :

  1. zone portrait (colonne 9:16 du milieu) : 1280 x 720 -> 405 px de large, centree ; 720 x 1280 -> toute la fenetre ; demi-largeur normalisee ;
  2. deformation de la texture : G(0) = 0, pente 1 au bord, pente toujours entre 0,46 et 1,54 (jamais de retournement), echelle d'ensemble conservee, deterministe, differente a gauche et a droite,
     et le motif ne revient pas identique un carreau plus loin (c'est tout l'objet : « on voit trop le pattern repetitif ») ;
  3. analyse de l'objet « kumo » (reconstitue ici a l'identique : 4 rangees de 3 carreaux de 11,5, decalees d'un demi-carreau) : rangees, periode, u exact, refus des structures inattendues ;
  4. bandes : aucun sommet dans la zone portrait (le ciel d'origine y reste intact), raccord continu au bord (u et v du ciel d'origine, a toute position du defilement), memes sommets / couleurs que les rangees,
     meme sens de parcours des triangles que les quadrilateres d'origine, rien a ajouter en portrait, plus de bandes quand la fenetre s'elargit.

    python3 outils/test_titre_ciel.py
"""
import math, os, sys, unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import ciel_titre as CT


def matrice(cam, cible, fov, aspect, n=1.0, f=200.0, haut=(0, 1, 0)):
    """Meme forme que `fenetre.matrice` (reecrite ici : pas de pyglet)."""
    pos = np.array(cam, float); fw = np.array(cible, float) - pos; fw /= np.linalg.norm(fw)
    droite = np.cross(haut, fw); droite /= np.linalg.norm(droite); haut = np.cross(fw, droite)
    th = math.tan(math.radians(fov) / 2)
    M = np.zeros((4, 4))
    M[0, :3] = droite / (th * aspect); M[0, 3] = -pos @ droite / (th * aspect)
    M[1, :3] = haut / th; M[1, 3] = -pos @ haut / th
    k = (f + n) / (f - n)
    M[2, :3] = fw * k; M[2, 3] = -pos @ fw * k - 2 * f * n / (f - n)
    M[3, :3] = fw; M[3, 3] = -pos @ fw
    return M


def camera_titre(aspect):
    """Camera du titre telle que la calcule le portage (valeurs relevees dans le moteur a l'image 400 : position (0, 27,70, -34,18), cible (0, 0, 0), fov 10, tangage 3,019 ; SceneCamera.Update)."""
    pos, cib = np.array([0.0, 27.7041015625, -34.181640625]), np.zeros(3)
    th_v = math.tan(math.radians(10.0 * 4.0 / 3.0) / 2) / CT.ASPECT_PORTRAIT
    fw = cib - pos; fw /= np.linalg.norm(fw)
    lacet = math.atan2(fw[0], fw[2]); tang = math.asin(-fw[1]) - math.radians(3.019360065460205)
    fw = np.array([math.sin(lacet) * math.cos(tang), -math.sin(tang), math.cos(lacet) * math.cos(tang)])
    pos = pos + fw * 4.0
    return matrice(pos, pos + fw * 10, math.degrees(2 * math.atan(th_v)), aspect, n=1.0, f=150.0)


def ciel_synthetique():
    """Sommets (positions, uv, couleurs) du ciel du titre (objet 000_kumo2) : 4 rangees (y, z, couleur de sommet comme dans l'original), 3 carreaux de 11,5 par rangee coupes en deux quadrilateres de 5,75,
    u de 0,002 a 0,998 sur le carreau ; deux rangees sur quatre sont decalees d'un demi-carreau (u de 0,502 d'abord)."""
    blanc, teinte = (1.0, 1.0, 1.0, 1.0), (1.0, 0.796, 0.6, 1.0)
    lignes = [(-33.56, 10.10, teinte, -22.75, 14.03, blanc, 1), (-22.75, 14.03, blanc, -11.95, 17.97, blanc, 0), (-11.95, 17.97, blanc, -1.14, 21.90, teinte, 1), (-1.14, 21.90, teinte, 9.67, 25.83, teinte, 0)]
    P, U, C = [], [], []
    for yb, zb, cb, yh, zh, ch, dec in lignes:
        for k in range(6):
            xg = -12.75 + 5.75 * k; xd = xg + 5.75
            demi = (k + dec) % 2
            ug, ud = (0.002, 0.502) if demi == 0 else (0.502, 0.998)
            for (x, y, z, u, v, c) in ((xg, yb, zb, ug, 0.998, cb), (xg, yh, zh, ug, 0.002, ch), (xd, yh, zh, ud, 0.002, ch), (xg, yb, zb, ug, 0.998, cb), (xd, yh, zh, ud, 0.002, ch), (xd, yb, zb, ud, 0.998, cb)):
                P.append((x, y, z)); U.append((u, v)); C.append(c)
    return np.array(P, np.float32), np.array(U, np.float32), np.array(C, np.float32)


def ndc_x(M, p):
    c = M @ np.array([p[0], p[1], p[2], 1.0]); return c[0] / c[3]


def aire(p):
    """Aire signee (dans le plan x, y) d'un triangle de 3 points."""
    return (p[1][0] - p[0][0]) * (p[2][1] - p[0][1]) - (p[2][0] - p[0][0]) * (p[1][1] - p[0][1])


class TestZonePortrait(unittest.TestCase):
    def test_zone(self):
        x0, w = CT.zone_portrait(1280, 720); self.assertAlmostEqual(w, 405.0); self.assertAlmostEqual(x0, 437.5)
        x0, w = CT.zone_portrait(720, 1280); self.assertEqual((x0, w), (0.0, 720.0))             # fenetre portrait : tout est la zone
        x0, w = CT.zone_portrait(1920, 820); self.assertAlmostEqual(w, 461.25); self.assertAlmostEqual(x0 + w / 2, 960.0)
        x0, w = CT.zone_portrait(1920, 400); self.assertAlmostEqual(w, 225.0)

    def test_demi_ndc(self):
        self.assertAlmostEqual(CT.demi_zone_ndc(16 / 9), 0.5625 / (16 / 9)); self.assertEqual(CT.demi_zone_ndc(0.5625), 1.0); self.assertEqual(CT.demi_zone_ndc(0.3), 1.0)
        x0, w = CT.zone_portrait(1280, 720); self.assertAlmostEqual(w / 1280, CT.demi_zone_ndc(1280 / 720))        # meme zone en pixels et en coordonnees d'ecran (la zone fait 2 x demi de la largeur de la fenetre / 2)


class TestDeformation(unittest.TestCase):
    d = np.linspace(0.0, 80.0, 8001)

    def test_raccord(self):
        for cote in (0, 1):
            G, dv = CT.deformation(self.d, cote); self.assertEqual(G[0], 0.0); self.assertEqual(dv[0], 0.0)
            self.assertAlmostEqual(float(G[1] / self.d[1]), 1.0, places=3); self.assertLess(abs(dv[1]), 1e-6)       # pente 1 et glissement nul avec pente nulle au bord de la zone : raccord sans cassure

    def test_pente_bornee(self):
        for cote in (0, 1):
            G, _ = CT.deformation(self.d, cote); p = np.diff(G) / np.diff(self.d)
            self.assertGreater(p.min(), 1 - 0.54 - 0.01); self.assertLess(p.max(), 1 + 0.54 + 0.01)       # jamais de retournement du motif, etirure de 0,46 a 1,54 au plus

    def test_echelle_d_ensemble(self):
        for cote in (0, 1):
            G, _ = CT.deformation(self.d, cote); self.assertLess(abs(G[-1] / self.d[-1] - 1.0), 0.03)       # meme echelle que l'original en moyenne

    def test_deterministe_et_independant_du_tableau(self):
        a = CT.deformation(np.array([3.0, 17.5, 40.0]), 0); b = CT.deformation(self.d, 0)
        for k in (0, 1): self.assertAlmostEqual(float(a[k][1]), float(np.interp(17.5, self.d, b[k])), places=3)
        self.assertTrue(all(np.array_equal(x, y) for x, y in zip(CT.deformation(self.d, 1), CT.deformation(self.d, 1))))

    def test_cotes_differents(self):
        (g0, v0), (g1, v1) = CT.deformation(self.d, 0), CT.deformation(self.d, 1)
        self.assertGreater(np.abs(g0 - g1).max(), 0.5); self.assertGreater(np.abs(v0 - v1).max(), 0.05)                                                  # pas de symetrie gauche / droite

    def test_le_motif_ne_revient_pas_identique(self):
        """Un carreau (11,5) plus loin, le motif est lu a une abscisse de texture differente : sans etirure G(d + 11,5) - G(d) = 11,5 partout (repetition exacte)."""
        P = 11.5; i = self.d <= 60.0
        for cote in (0, 1):
            G, _ = CT.deformation(self.d, cote); ecart = np.interp(self.d[i] + P, self.d, G) - G[i] - P
            self.assertGreater(np.abs(ecart).max(), 1.0)                                                 # ecart de plus d'un dixieme de carreau en plusieurs endroits
            self.assertGreater((np.abs(ecart) > 0.4).mean(), 0.5)                                       # et presque partout : le motif est decale d'au moins 3 % de carreau sur plus de la moitie de la bande


class TestAnalyse(unittest.TestCase):
    def test_rangees(self):
        r = CT.analyser(*ciel_synthetique())
        self.assertEqual(len(r), 4)
        for ra in r:
            self.assertAlmostEqual(ra.periode, 11.5, places=3); self.assertEqual(len(ra.quads), 6); self.assertAlmostEqual(ra.taux, 0.996 / 11.5, places=3)
        self.assertEqual([round(ra.bas[0], 2) for ra in r], [-33.56, -22.75, -11.95, -1.14])           # tries de bas en haut
        self.assertAlmostEqual(r[1].haut[0], r[2].bas[0], places=2)                                    # rangees contigues

    def test_u_exact(self):
        P, U, C = ciel_synthetique(); r = CT.analyser(P, U, C)
        # u(x) = celui des quadrilateres de la rangee, partout dans l'objet, et il se repete au-dela
        for ra in r:
            for xg, xd, ug, ud in ra.quads:
                for f in (0.0, 0.25, 0.5, 0.9):
                    x = xg + f * (xd - xg); self.assertAlmostEqual(float(ra.u(x)), ug + f * (ud - ug), places=6)
                    self.assertAlmostEqual(float(ra.u(x + 11.5 * 4)), ug + f * (ud - ug), places=5); self.assertAlmostEqual(float(ra.u(x - 11.5 * 3)), ug + f * (ud - ug), places=5)
        self.assertNotAlmostEqual(float(r[0].u(0.0)), float(r[1].u(0.0)), places=2)                      # rangees decalees d'un demi-carreau

    def test_couleurs_et_bords(self):
        r = CT.analyser(*ciel_synthetique())
        self.assertEqual(tuple(np.round(r[0].bas[3], 3)), (1.0, 0.796, 0.6, 1.0)); self.assertEqual(tuple(r[0].haut[3]), (1.0, 1.0, 1.0, 1.0))
        self.assertAlmostEqual(r[0].bas[2], 0.998, places=3); self.assertAlmostEqual(r[0].haut[2], 0.002, places=3)
        self.assertAlmostEqual(r[0].bas[1], 10.10, places=2); self.assertAlmostEqual(r[0].haut[1], 14.03, places=2)

    def test_structure_inattendue(self):
        P, U, C = ciel_synthetique()
        for args in ((P[:-1], U[:-1], C[:-1]), (P[:0], U[:0], C[:0])):
            with self.assertRaises(ValueError): CT.analyser(*args)
        P2 = P.copy(); P2[1, 0] += 0.5                                                                  # sommet hors de l'alignement des quadrilateres
        with self.assertRaises(ValueError): CT.analyser(P2, U, C)
        U2 = U.copy(); U2[12:, 0] = 0.3                                                                 # motif non periodique
        with self.assertRaises(ValueError): CT.analyser(P, U2, C)


class TestBandes(unittest.TestCase):
    def setUp(self):
        self.P, self.U, self.C = ciel_synthetique(); self.ciel = CT.CielLarge(self.P, self.U, self.C)

    def test_portrait_rien_a_ajouter(self):
        self.assertIsNone(self.ciel.bandes(camera_titre(0.5625), 0.5625, 0.0)); self.assertIsNone(self.ciel.bandes(camera_titre(0.4), 0.4, 0.0))

    def test_zone_intacte(self):
        """Aucun point de la zone portrait (|x d'ecran| <= demi, dans le champ) n'est recouvert par une bande : on projette les triangles et on teste un quadrillage de la zone."""
        for asp in (16 / 9, 21 / 9, 32 / 9):
            M = camera_titre(asp); demi = CT.demi_zone_ndc(asp)
            P, U, C = self.ciel.bandes(M, asp, 0.0)
            self.assertEqual(len(P) % 6, 0)
            ex = M @ np.c_[P, np.ones(len(P))].T; xs = ex[0] / ex[3]; ys = ex[1] / ex[3]
            visibles = np.abs(ys) <= 1.0
            self.assertGreater(np.abs(xs[visibles]).min(), demi - 0.15, 'asp %.2f : bande trop pres du bord de la zone' % asp)           # sommets des bandes : hors de la zone, a la marge des rangees inclinees pres
            for ra in self.ciel.rangees:                                                               # points de la zone sur la rangee, de bas en haut : leur abscisse monde est entre les bandes
                b = CT.bords_zone(M, self.ciel.rangees, demi, self.ciel.x_mil)
                self.assertIsNotNone(b)
                zb, zh, eb, eh = b
                self.assertLess(eb, zb); self.assertLess(zh, eh)
                for t in np.linspace(0, 1, 9):
                    y = ra.bas[0] + t * (ra.haut[0] - ra.bas[0]); z = ra.bas[1] + t * (ra.haut[1] - ra.bas[1])
                    for xn in np.linspace(-demi, demi, 7):
                        # abscisse monde qui projette en xn (dichotomie) : doit etre dans [zb, zh]
                        lo, hi = -80.0, 80.0
                        for _ in range(60):
                            mid = (lo + hi) / 2
                            if ndc_x(M, (mid, y, z)) < xn: lo = mid
                            else: hi = mid
                        c = M @ np.array([lo, y, z, 1.0])
                        if abs(c[1] / c[3]) <= 1.0: self.assertTrue(zb - 1e-3 <= lo <= zh + 1e-3, (asp, t, xn, lo, zb, zh))

    def test_raccord_au_bord(self):
        """Sommets de chaque bande au bord de la zone : u = celui du ciel d'origine a cette abscisse (decale du defilement de l'objet), v = celui du bord de la rangee, a toute position du defilement."""
        asp = 16 / 9; M = camera_titre(asp)
        zb, zh, eb, eh = CT.bords_zone(M, self.ciel.rangees, CT.demi_zone_ndc(asp), self.ciel.x_mil)
        for phi in (0.0, -0.0192 * 100, -5.77, -11.49):
            P, U, C = self.ciel.bandes(M, asp, phi)
            for deb, fin, ri, xs in self.ciel._ref:                                                    # chaque bande (rangee, cote) a ses propres sommets (les rangees voisines partagent un bord y, z)
                ra = self.ciel.rangees[ri]; Pb, Ub = P[deb:fin], U[deb:fin]
                for y, z, v in ((ra.bas[0], ra.bas[1], ra.bas[2]), (ra.haut[0], ra.haut[1], ra.haut[2])):
                    m = np.isclose(Pb[:, 0], xs, atol=1e-3) & np.isclose(Pb[:, 1], y, atol=1e-4) & np.isclose(Pb[:, 2], z, atol=1e-4)
                    self.assertTrue(m.any()); self.assertIn(xs, (zb, zh))
                    self.assertTrue(np.allclose(Ub[m, 0], ra.u(xs - phi), atol=2e-4), (phi, xs, Ub[m, 0][:3], ra.u(xs - phi)))
                    self.assertTrue(np.allclose(Ub[m, 1], v, atol=1e-6))

    def test_defilement_suit_l_objet(self):
        """Positions et couleurs des bandes ne dependent pas du defilement ; leur u en depend d'un decalage constant par bande (au bord de la zone la texture glisse comme l'objet : taux x dx)."""
        asp = 16 / 9; M = camera_titre(asp)
        a = self.ciel.bandes(M, asp, 0.0); b = self.ciel.bandes(M, asp, -3.0)
        self.assertTrue(np.array_equal(a[0], b[0])); self.assertTrue(np.array_equal(a[2], b[2])); self.assertTrue(np.array_equal(a[1][:, 1], b[1][:, 1]))
        du = b[1][:, 0] - a[1][:, 0]
        for deb, fin, ri, xs in self.ciel._ref:
            self.assertLess(np.ptp(du[deb:fin]), 1e-5)                                                  # decalage identique sur toute la bande (une rangee, un cote) : la texture glisse d'un bloc
            att = 3.0 * self.ciel.rangees[ri].taux                                                      # le motif de l'objet avance de 3 unites : u change de taux x 3 (modulo un carreau, 0,996 : le u d'origine est replie dans [0,002 ; 0,998])
            self.assertLess(abs((du[deb] - att + 0.498) % 0.996 - 0.498), 0.01)

    def test_couleurs_comme_les_rangees(self):
        asp = 16 / 9; P, U, C = self.ciel.bandes(camera_titre(asp), asp, 0.0)
        for ra in self.ciel.rangees:
            bas = np.isclose(P[:, 1], ra.bas[0], atol=1e-4) & np.isclose(P[:, 2], ra.bas[1], atol=1e-4)
            haut = np.isclose(P[:, 1], ra.haut[0], atol=1e-4) & np.isclose(P[:, 2], ra.haut[1], atol=1e-4)
            self.assertTrue(np.allclose(C[bas], ra.bas[3], atol=1e-6)); self.assertTrue(np.allclose(C[haut], ra.haut[3], atol=1e-6))

    def test_sens_des_triangles(self):
        """Tous les triangles des bandes tournent dans le meme sens que ceux du ciel d'origine (face visible identique)."""
        asp = 21 / 9; P, U, C = self.ciel.bandes(camera_titre(asp), asp, -2.0)
        s0 = {np.sign(aire(self.P[i:i + 3, :2])) for i in range(0, len(self.P), 3)}
        s1 = {np.sign(aire(P[i:i + 3, :2])) for i in range(0, len(P), 3)}
        self.assertEqual(len(s0), 1); self.assertEqual(s0, s1)

    def test_plus_large_plus_de_bandes(self):
        n = [len(self.ciel.bandes(camera_titre(a), a, 0.0)[0]) for a in (16 / 9, 21 / 9, 32 / 9)]
        self.assertLess(n[0], n[1]); self.assertLess(n[1], n[2])
        a = self.ciel.bandes(camera_titre(16 / 9), 16 / 9, 0.0)
        for t in a: self.assertTrue(np.isfinite(t).all())

    def test_couvre_toute_la_fenetre(self):
        """A chaque abscisse d'ecran (hors zone) et chaque hauteur visible, le point du ciel est couvert par une bande : l'etendue des bandes depasse le bord de la fenetre."""
        for asp in (16 / 9, 21 / 9, 32 / 9):
            M = camera_titre(asp); P, U, C = self.ciel.bandes(M, asp, 0.0)
            b = CT.bords_zone(M, self.ciel.rangees, CT.demi_zone_ndc(asp), self.ciel.x_mil); zb, zh, eb, eh = b
            self.assertLessEqual(P[:, 0].min(), eb - 0.5 * self.ciel.pas); self.assertGreaterEqual(P[:, 0].max(), eh + 0.5 * self.ciel.pas)

    def test_coutures_entre_rangees_intactes(self):
        """Le glissement vertical est nul sur les bords haut / bas de chaque rangee (ils lisent la texture de v = 0 a 1 comme l'original : sinon couture visible entre les rangees decalees d'un demi-carreau) et agit a l'interieur."""
        asp = 21 / 9; P, U, C = self.ciel.bandes(camera_titre(asp), asp, 0.0); interieur = 0.0
        for deb, fin, ri, xs in self.ciel._ref:
            ra = self.ciel.rangees[ri]; Pb, Ub = P[deb:fin], U[deb:fin]
            bas = np.isclose(Pb[:, 1], ra.bas[0], atol=1e-4) & np.isclose(Pb[:, 2], ra.bas[1], atol=1e-4)
            haut = np.isclose(Pb[:, 1], ra.haut[0], atol=1e-4) & np.isclose(Pb[:, 2], ra.haut[1], atol=1e-4)
            self.assertTrue(np.allclose(Ub[bas, 1], ra.bas[2], atol=1e-5)); self.assertTrue(np.allclose(Ub[haut, 1], ra.haut[2], atol=1e-5))
            mil = ~(bas | haut); interieur = max(interieur, float(np.abs(Ub[mil, 1] - np.interp(Pb[mil, 1], [ra.bas[0], ra.haut[0]], [ra.bas[2], ra.haut[2]])).max()))
        self.assertGreater(interieur, 0.04); self.assertLess(interieur, 0.12)

    def test_cle_de_cache(self):
        asp = 16 / 9; M = camera_titre(asp)
        a = self.ciel.bandes(M, asp, 0.0); b = self.ciel.bandes(M, asp, 0.0); self.assertTrue(np.array_equal(a[1], b[1]))
        c = self.ciel.bandes(camera_titre(21 / 9), 21 / 9, 0.0); self.assertNotEqual(len(a[0]), len(c[0]))


if __name__ == '__main__':
    unittest.main()
