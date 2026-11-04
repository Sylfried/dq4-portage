"""Sprites de ville toujours droits a l'ecran (#134 : « quand mon perso monte ou descend, les sprites des PNJ se penchent », sans fenetre ni moteur : `Jeu._camera_ville` et `Jeu._panneau_ville` sont appelees sur un faux objet) :

  1. les 4 coins du panneau d'un PNJ, projetes par la matrice REELLE de la visionneuse, donnent un rectangle a bords gauche / droit verticaux (ecart bas -> haut < 0,01 px) et une proportion largeur / hauteur
     constante, a toute position de l'ecran (haut, bas, gauche, droite, coins, centre) et dans tous les etats de camera : suivi du heros, decalage `cam_dec`, inclinaison, lacet, zoom, fov, s_yOffset, hauteur
     (butte #110 : la camera monte avec le sol), echelle SetScale ;
  2. la correction des bords ne touche NI la profondeur (z-buffer, recouvrements) NI la position et la hauteur a l'ecran : memes profondeurs de coin, meme bas du panneau, meme haut, qu'avec le panneau d'origine ;
     au centre de l'image rien ne change (centre du haut = centre du haut d'origine, largeur moyenne identique) ; ailleurs la LARGEUR change par construction (proportion constante 0,738 au lieu de 0,65 en haut a 0,81
     en bas de l'ecran pour le panneau d'origine) ;
  3. garde-fou : le panneau d'ORIGINE (correction coupee) se penche bien de plus de 8 degres pres des bords, donc le test 1 verifie quelque chose ;
  4. essai d'inclinaison (#134) : avec `inc` > 0 le panneau est cisaille vers la verticale du monde, pieds fixes, a taille, profondeur et position de bas inchangees ; son bord penche de atan(inc x tan(angle d'une
     verticale du monde au pied)) ; inc = 1 : parallele aux murs ; 0,5 par defaut (`Jeu._inclinaison_sprites`, variable DQ_SPRITE_INCLINAISON) ;
  5. constat (cause de l'impression de #134, voir `Jeu._panneau_ville`) : les VERTICALES DU MONDE (murs, portes) penchent a l'ecran selon leur position (point de fuite sous l'image, camera a 47 degres), de beaucoup plus en 16/9 que
     sur le portrait d'origine, et cet angle change de plusieurs degres quand le heros monte ou descend (le PNJ change de hauteur a l'ecran) alors que le sprite, lui, reste a 0 : le sprite parait pencher PAR RAPPORT aux murs voisins.

    python3 outils/test_sprites_droits.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import itertools, math, os, sys, unittest

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc')); sys.path.insert(0, ICI)
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import fenetre as F
import test_camera_ville as TC

ASPECT = 16.0 / 9.0
LARG, HAUT = 1280.0, 720.0
CIB = np.array([20.0, 0.0, 30.0])
POSITIONS = list(itertools.product((-9.0, -4.5, 0.0, 4.5, 9.0), (-5.0, -2.0, 0.0, 3.0, 6.0, 9.0)))          # decalage (x, z) du PNJ par rapport au heros, en unites de ville : du coin bas a un coin haut de l'ecran
ETATS = {'defaut': {}, 'lacet 20': dict(lacet=20.0), 'lacet 45': dict(lacet=45.0), 'lacet -30': dict(lacet=-30.0), 'angle +15': dict(angle=15.0), 'angle -15': dict(angle=-15.0), 'angle +30': dict(angle=30.0),
         'zoom 0,5': dict(zoom=0.5), 'zoom 4': dict(zoom=4.0), 'yoff 0,05': dict(yoff=0.05), 'fov 10': dict(fov=10.0), 'heros decale (5, -4)': dict(dec=(5.0, -4.0)), 'heros en hauteur': dict(hy=0.5),
         'lacet 20 + angle 15 + zoom 2': dict(lacet=20.0, angle=15.0, zoom=2.0), 'echelle 0,738': dict(k=0.738)}


def px(M, P):
    v = M @ np.array([P[0], P[1], P[2], 1.0]); return np.array([(v[0] / v[3] * 0.5 + 0.5) * LARG, (1.0 - (v[1] / v[3] * 0.5 + 0.5)) * HAUT])


def angle(bas, haut):
    """Inclinaison (degres) d'un bord a l'ecran par rapport a la verticale ; + = le haut part vers la droite."""
    return math.degrees(math.atan2(haut[0] - bas[0], bas[1] - haut[1]))


def faux_jeu(lacet=0.0, angle_cam=0.0, zoom=1.0):
    j = TC.faux_jeu(); j.lacet = lacet; j.angle_cam = angle_cam; j.zoom = zoom; j.fixe_test = True          # fixe_test : un pas de 1/60 s par appel, sans horloge
    return j


def panneau(j, e, pied, t, k=1.0, inc=0.0):
    """(M, coins du panneau en MONDE, repere de la camera, position de la camera) d'un PNJ dont les pieds sont en `pied`, comme le fait `Jeu._dessiner` (voir la boucle des sprites)."""
    M, cam3d = F.Jeu._camera_ville(j, e, ASPECT)
    r_, u_, f_ = cam3d; w, h = F.SPRITE_L * F.SPRITE_ECHELLE * k, F.SPRITE_H * F.SPRITE_ECHELLE * k
    zb, zh = 0.185 / 0.48 * w, (0.65 - 0.185) / 0.48 * w
    C = j._cadre_vue[0]
    return M, F.Jeu._panneau_ville(j, np.array(pied, float), r_, u_, f_, w, h, zb, zb + zh, t, C, inc), cam3d, C


def forme(M, q):
    """Inclinaison des bords gauche et droit (degres), proportion largeur / hauteur et coins en pixels (bas gauche, bas droit, haut droit, haut gauche)."""
    A, B, Cc, D = (px(M, p) for p in q)
    haut = 0.5 * ((A[1] - D[1]) + (B[1] - Cc[1])); larg = 0.5 * ((B[0] - A[0]) + (Cc[0] - D[0]))
    return angle(A, D), angle(B, Cc), larg / haut, (A, B, Cc, D)


def cas(nom, dx, dz, t, inc=0.0):
    kw = ETATS[nom]; hero = CIB + np.array([kw.get('dec', (0.0, 0.0))[0], kw.get('hy', 0.0), kw.get('dec', (0.0, 0.0))[1]])
    e = TC.faux_etat(CIB, hero, fov=kw.get('fov'), yoff=kw.get('yoff')); j = faux_jeu(kw.get('lacet', 0.0), kw.get('angle', 0.0), kw.get('zoom', 1.0))
    for _ in range(3): F.Jeu._camera_ville(j, e, ASPECT)                       # (le reste du centrage se resorbe : meme etat qu'apres quelques images)
    return panneau(j, e, hero + np.array([dx, 0.0, dz]), t, kw.get('k', 1.0), inc), hero


class TestSpritesDroits(unittest.TestCase):
    def test_bords_verticaux_partout(self):
        pire = 0.0; r_min, r_max = 9.0, 0.0
        for nom, (dx, dz) in itertools.product(ETATS, POSITIONS):
            (M, q, _, _), _ = cas(nom, dx, dz, 1.0)
            g, d, ratio, (A, B, Cc, D) = forme(M, q)
            pire = max(pire, abs(D[0] - A[0]), abs(Cc[0] - B[0]), abs(A[1] - B[1]), abs(D[1] - Cc[1]))             # bords gauche / droit verticaux ET bas / haut horizontaux (ecart en pixels)
            r_min, r_max = min(r_min, ratio), max(r_max, ratio)
        self.assertLess(pire, 0.01, 'le panneau doit etre un rectangle droit a l\'ecran, a toute position et pour toute camera')
        self.assertGreater(r_min, 0.730); self.assertLess(r_max, 0.745)                                              # proportion constante a +- 1 % (0,72 x la hauteur au centre de l'image : 0,738 mesure)

    def test_butte_montee_et_descente(self):
        """Camera de la butte (#110) : la hauteur de la camera suit le sol (CAM_Y_RELIEF) ou retarde (escalier) ; a chaque image, un PNJ au bord gauche, au bord droit et en haut reste droit."""
        pire = 0.0; j = faux_jeu(); y_prec = None
        profil = TC.TestCameraVille.profil_butte(0.5) + [0.5 + 0.1 * i for i in range(30)] + [3.5] * 20 + [3.5 - 0.1 * i for i in range(30)]          # butte, puis une montee d'escalier de 3 u et sa descente
        for hy in profil:
            h = 0.047 + hy; hero = np.array([20.0, h, 30.0]); e = TC.faux_etat((20.0, h - 0.047, 30.0), hero)
            for dx, dz in ((-9.0, 0.0), (9.0, -4.0), (0.0, 8.0), (-9.0, 9.0)):
                M, q, _, _ = panneau(j, e, hero + np.array([dx, 0.0, dz]), 1.0)
                A, B, Cc, D = forme(M, q)[3]; pire = max(pire, abs(D[0] - A[0]), abs(Cc[0] - B[0]))
        self.assertLess(pire, 0.01)

    def test_profondeur_et_centre_inchanges(self):
        """z-buffer (profondeur de chaque coin le long de l'axe de la camera) et hauteur a l'ecran inchanges ; bas du panneau identique ; au centre de l'image, haut identique et largeur moyenne identique."""
        centre = 0
        for nom, (dx, dz) in itertools.product(('defaut', 'lacet 45', 'angle +15', 'zoom 4', 'echelle 0,738'), POSITIONS):
            (M, nou, cam3d, C), _ = cas(nom, dx, dz, 1.0); (_, ori, _, _), _ = cas(nom, dx, dz, 0.0)
            f_ = cam3d[2]
            for a, b in zip(nou, ori): self.assertAlmostEqual(float((a - C) @ f_), float((b - C) @ f_), 8, '%s (%s, %s) : profondeur d\'un coin' % (nom, dx, dz))
            An, Bn, Cn, Dn = (px(M, p) for p in nou); Ao, Bo, Co, Do = (px(M, p) for p in ori)
            for a, b in ((An[1], Ao[1]), (Bn[1], Bo[1]), (Cn[1], Co[1]), (Dn[1], Do[1])): self.assertAlmostEqual(a, b, 6, '%s (%s, %s) : ordonnee a l\'ecran' % (nom, dx, dz))
            self.assertAlmostEqual(0.5 * (An[0] + Bn[0]), 0.5 * (Ao[0] + Bo[0]), 6, 'centre du bas inchange')
            if dx == 0.0 and dz == 0.0:                                          # au centre de l'image (la camera est centree sur le heros : un PNJ a ses pieds est au centre, quelle que soit la camera)
                centre += 1
                self.assertAlmostEqual(0.5 * (Cn[0] + Dn[0]), 0.5 * (Co[0] + Do[0]), 6, 'centre de l\'image : le haut ne bouge pas')
                self.assertAlmostEqual(0.5 * ((Bn[0] - An[0]) + (Cn[0] - Dn[0])), 0.5 * ((Bo[0] - Ao[0]) + (Co[0] - Do[0])), delta=0.01 * (Bo[0] - Ao[0]), msg='centre de l\'image : largeur moyenne identique')
        self.assertEqual(centre, 5, 'un cas central par camera verifiee')

    def test_original_penche_garde_fou(self):
        """Sans la correction (panneau d'origine) le sprite se penche de plus de 8 degres pres des bords gauche / droit du 16/9 : le test 1 mesure donc bien quelque chose ; au centre il reste droit a 1 degre pres."""
        (M, q, _, _), _ = cas('defaut', 9.0, 0.0, 0.0); g, d, _, _ = forme(M, q); self.assertGreater(min(abs(g), abs(d)), 8.0)
        (M, q, _, _), _ = cas('defaut', -9.0, 0.0, 0.0); g, d, _, _ = forme(M, q); self.assertGreater(min(abs(g), abs(d)), 8.0)
        (M, q, _, _), _ = cas('defaut', 0.0, 0.0, 0.0); g, d, _, _ = forme(M, q); self.assertLess(max(abs(g), abs(d)), 1.0)

    @staticmethod
    def verticale_monde(M, pied, h=1.44):
        return angle(px(M, pied), px(M, pied + np.array([0.0, h, 0.0])))

    def test_constat_verticales_du_monde(self):
        """Cause de l'impression de #134 : une verticale du monde (arete de mur, porte) a 9 u du heros penche a l'ecran de 11 a 19 degres selon la hauteur de l'ecran ou elle se trouve (16/9, camera a 47 degres), contre
        4 a 6,5 degres sur le portrait d'origine ; quand le heros monte ou descend l'angle change de plus de 5 degres, alors que le sprite reste a 0. (C'est la perspective du decor, pas le panneau : voir test 1.)"""
        def balayage(aspect):
            global LARG, HAUT
            LARG, HAUT = (1280.0, 720.0) if aspect > 1 else (450.0, 800.0)
            try:
                dx = -9.0 if aspect > 1 else -3.0; e = TC.faux_etat(CIB, CIB); j = faux_jeu(); M, _ = F.Jeu._camera_ville(j, e, aspect)
                return [self.verticale_monde(M, CIB + np.array([dx, 0.0, dz])) for dz in (-5.0, 9.0)]            # bas de l'ecran, haut de l'ecran
            finally: LARG, HAUT = 1280.0, 720.0
        bas, haut = balayage(16.0 / 9.0)
        self.assertLess(bas, -17.0); self.assertGreater(haut, -12.0); self.assertGreater(abs(bas) - abs(haut), 5.0)
        bas, haut = balayage(0.5625)
        self.assertLess(abs(bas), 7.0); self.assertLess(abs(bas) - abs(haut), 3.0)

    def test_inclinaison_vers_la_verticale_du_monde(self):
        """Essai #134 : avec `inc`, le bord du sprite penche de atan(inc x tan(angle de la verticale du monde au pied)) (a 0,05 degre pres) ; inc = 1 : parallele aux murs ; le sprite et le mur ne s'ecartent plus que de (1 - inc)
        fois l'ecart initial ; sens : le sprite penche du meme cote que le mur ; au centre de l'image (verticale du monde droite) rien ne change ; les bords gauche et droit restent paralleles."""
        pire = 0.0; lu = 0
        for nom, (dx, dz), inc in itertools.product(('defaut', 'lacet 20', 'angle +15', 'zoom 4', 'echelle 0,738'), POSITIONS, (0.3, 0.5, 0.7, 1.0)):
            (M, q, cam3d, C), hero = cas(nom, dx, dz, 1.0, inc); (_, q0, _, _), _ = cas(nom, dx, dz, 1.0, 0.0)
            g, d, _, (A, B, Cc, D) = forme(M, q); g0, d0, _, _ = forme(M, q0)
            pied_bas = 0.5 * (np.array(q[0]) + np.array(q[1]))                              # milieu du bas du panneau
            mur = self.verticale_monde(M, pied_bas)
            attendu = math.degrees(math.atan(inc * math.tan(math.radians(mur))))
            pire = max(pire, abs(g - attendu), abs(d - attendu)); lu += 1
            self.assertAlmostEqual(g, d, 5, '%s (%s, %s) inc %s : les deux bords sont paralleles' % (nom, dx, dz, inc))
            self.assertAlmostEqual(g0, 0.0, 5)
            if abs(mur) > 2.0: self.assertGreater(g * mur, 0.0, '%s (%s, %s) : meme sens que le mur' % (nom, dx, dz))
            if inc == 1.0: self.assertAlmostEqual(g, mur, delta=0.05, msg='inc = 1 : parallele au mur')
            if dx == 0.0 and dz == 0.0 and nom == 'defaut': self.assertLess(abs(g), 0.5, 'au centre de l\'image rien ne change')
        self.assertLess(pire, 0.05); self.assertEqual(lu, 5 * len(POSITIONS) * 4)

    def test_inclinaison_ne_touche_ni_taille_ni_profondeur(self):
        """Cisaillement pur, pieds fixes : bas du panneau, hauteur et largeur a l'ecran, profondeur de chaque coin (z-buffer) = ceux de `inc` = 0."""
        for nom, (dx, dz), inc in itertools.product(('defaut', 'lacet 45', 'angle -15', 'zoom 4', 'echelle 0,738'), POSITIONS, (0.5, 1.0)):
            (M, a, cam3d, C), _ = cas(nom, dx, dz, 1.0, inc); (_, b, _, _), _ = cas(nom, dx, dz, 1.0, 0.0); f_ = cam3d[2]
            for u, v in zip(a, b): self.assertAlmostEqual(float((u - C) @ f_), float((v - C) @ f_), 8, '%s (%s, %s) inc %s : profondeur d\'un coin' % (nom, dx, dz, inc))
            Pa = [px(M, p) for p in a]; Pb = [px(M, p) for p in b]
            for i in range(4): self.assertAlmostEqual(Pa[i][1], Pb[i][1], 6, 'ordonnee a l\'ecran du coin %d' % i)
            for i in (0, 1): self.assertAlmostEqual(Pa[i][0], Pb[i][0], 6, 'les pieds ne bougent pas')
            self.assertAlmostEqual(Pa[1][0] - Pa[0][0], Pb[1][0] - Pb[0][0], 6, 'largeur du bas')
            self.assertAlmostEqual(Pa[2][0] - Pa[3][0], Pb[2][0] - Pb[3][0], 6, 'largeur du haut')

    def test_montee_et_descente_moins_de_decalage_avec_le_mur(self):
        """Constat de #134 : un PNJ au bord gauche, quand le heros monte ou descend, change de hauteur a l'ecran et l'ecart sprite / mur varie de plusieurs degres ; avec inc = 0,5 la variation est divisee par deux (a 5 % pres)."""
        def ecarts(inc):
            out = []
            for dz in (-5.0, 0.0, 4.0, 9.0):                                                  # le PNJ du bord gauche, a differentes hauteurs d'ecran (= le heros qui monte ou descend)
                (M, q, _, _), _ = cas('defaut', -9.0, dz, 1.0, inc); g = forme(M, q)[0]
                mur = self.verticale_monde(M, 0.5 * (np.array(q[0]) + np.array(q[1]))); out.append(mur - g)
            return out
        e0, e5 = ecarts(0.0), ecarts(0.5)
        self.assertGreater(max(e0) - min(e0), 5.0, 'constat : sans inclinaison, l\'ecart sprite / mur varie de plus de 5 degres')
        self.assertGreater(max(abs(x) for x in e0), 15.0)
        for a, b in zip(e0, e5): self.assertAlmostEqual(b, a * 0.5, delta=0.05 * abs(a) + 0.7)
        self.assertLess(max(e5) - min(e5), 0.55 * (max(e0) - min(e0)))

    def test_reglage_par_variable_d_environnement(self):
        """DQ_SPRITE_INCLINAISON : 0 a 100 (%) ; absente, vide ou illisible : 50 % (essai) ; bornee."""
        j = TC.faux_jeu(); j.INCLINAISON_SPRITES_DEF = F.Jeu.INCLINAISON_SPRITES_DEF; ancien = os.environ.pop('DQ_SPRITE_INCLINAISON', None)
        try:
            self.assertEqual(F.Jeu._inclinaison_sprites(j), 0.5); self.assertEqual(F.Jeu.INCLINAISON_SPRITES_DEF, 0.5)
            for val, att in (('0', 0.0), ('100', 1.0), ('30', 0.3), ('70.5', 0.705), ('250', 1.0), ('-5', 0.0), ('', 0.5), ('  ', 0.5), ('abc', 0.5)):
                os.environ['DQ_SPRITE_INCLINAISON'] = val; self.assertAlmostEqual(F.Jeu._inclinaison_sprites(j), att, 9, repr(val))
        finally:
            os.environ.pop('DQ_SPRITE_INCLINAISON', None)
            if ancien is not None: os.environ['DQ_SPRITE_INCLINAISON'] = ancien

    def test_camera_inconnue_ou_correction_coupee(self):
        """Sans camera (C inconnue) ou avec la correction des bords coupee (t = 0) : le panneau d'origine, meme avec `inc`."""
        (M, q, cam3d, C), hero = cas('defaut', 6.0, 3.0, 0.0, 0.8); (_, q0, _, _), _ = cas('defaut', 6.0, 3.0, 0.0, 0.0)
        for a, b in zip(q, q0): self.assertTrue(np.allclose(a, b))
        r_, u_, f_ = cam3d; w, h = F.SPRITE_L * F.SPRITE_ECHELLE, F.SPRITE_H * F.SPRITE_ECHELLE; zb, zh = 0.185 / 0.48 * w, (0.65 - 0.185) / 0.48 * w
        j = TC.faux_jeu(); a = F.Jeu._panneau_ville(j, hero, r_, u_, f_, w, h, zb, zb + zh, 1.0, None, 0.8); b = F.Jeu._panneau_ville(j, hero, r_, u_, f_, w, h, zb, zb + zh, 0.0, None, 0.0)
        for x, y in zip(a, b): self.assertTrue(np.allclose(x, y))


if __name__ == '__main__':
    unittest.main(verbosity=2)
