"""Sprites de ville toujours droits a l'ecran (#134 : « quand mon perso monte ou descend, les sprites des PNJ se penchent », sans fenetre ni moteur : `Game._town_camera` et `Game._town_panel` sont appelees sur un faux objet) :

  1. les 4 coins du panneau d'un PNJ, projetes par la matrice REELLE de la visionneuse, donnent un rectangle a bords gauche / droit verticaux (ecart bas -> haut < 0,01 px) et une proportion largeur / hauteur
     constante, a toute position de l'ecran (haut, bas, gauche, droite, coins, centre) et dans tous les etats de camera : fov, s_yOffset, hauteur
     (butte #110 : la camera monte avec le sol), echelle SetScale ;
  2. la correction des bords ne touche NI la profondeur (z-buffer, recouvrements) NI la position et la hauteur a l'ecran : memes profondeurs de coin, meme bas du panneau, meme haut, qu'avec le panneau d'origine ;
     au centre de l'image rien ne change (centre du haut = centre du haut d'origine, largeur moyenne identique) ; ailleurs la LARGEUR change par construction (proportion constante 0,738 au lieu de 0,65 en haut a 0,81
     en bas de l'ecran pour le panneau d'origine) ;
  3. garde-fou : le panneau d'ORIGINE (correction coupee) se penche bien de plus de 8 degres pres des bords, donc le test 1 verifie quelque chose ;
  4. essai d'inclinaison (#134) : avec `inc` > 0 le panneau est cisaille vers la verticale du monde, pieds fixes, a taille, profondeur et position de bas inchangees ; son bord penche de atan(inc x tan(angle d'une
     verticale du monde au pied)) ; inc = 1 : parallele aux murs ; 0 PAR DEFAUT depuis #180 (« remets l'affichage des PNJ comme sur la version mobile ... ils s'etirent pres du bord » : le cisaillement a 0,5 deformait les
     sprites ; `Game._sprite_tilt`, variable DQ_SPRITE_INCLINAISON pour l'essayer) : la correction des bords seule (sans cisaillement) donne des bords exactement verticaux et la proportion constante (elle n'est plus le defaut depuis #184 : DQ_CORRECTION_BORDS=100) ;
  5. constat (cause de l'impression de #134, voir `Game._town_panel`) : les VERTICALES DU MONDE (murs, portes) penchent a l'ecran selon leur position (point de fuite sous l'image, camera a 47 degres), de beaucoup plus en 16/9 que
     sur le portrait d'origine, et cet angle change de plusieurs degres quand le heros monte ou descend (le PNJ change de hauteur a l'ecran) alors que le sprite, lui, reste a 0 : le sprite parait pencher PAR RAPPORT aux murs voisins.

  6. #184 (« reviens a la position brute des PNJ, exactement comme dans le jeu ... avec le nouveau systeme de camera ils ne doivent pas s'aligner si on monte ou descend la camera ») : par defaut le panneau est celui du jeu (correction
     des bords nulle) et son repere (`Game._sprite_reference`) est celui de la camera DU JEU : Haut / Bas ne le change pas (coins identiques en monde), Gauche / Droite le font tourner de face avec l'inclinaison du jeu ;

    python3 tools/test_upright_sprites.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import itertools, math, os, sys, types, unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.window import game as F
import test_town_camera as TC

ASPECT = 16.0 / 9.0
WIDTH, UP = 1280.0, 720.0
TARGET = np.array([20.0, 0.0, 30.0])
POSITIONS = list(itertools.product((-9.0, -4.5, 0.0, 4.5, 9.0), (-5.0, -2.0, 0.0, 3.0, 6.0, 9.0)))          # decalage (x, z) du PNJ par rapport au heros, en unites de ville : du coin bas a un coin haut de l'ecran
SAVESTATES = {'defaut': {}, 'yoff 0,05': dict(yoff=0.05), 'fov 10': dict(fov=10.0), 'fov 40': dict(fov=40.0), 'heros decale (5, -4)': dict(dec=(5.0, -4.0)), 'heros en hauteur': dict(hy=0.5), 'echelle 0,738': dict(k=0.738)}          # (#264 : plus de lacet, d'angle ni de zoom : la camera est celle du jeu)


def px(M, P):
    v = M @ np.array([P[0], P[1], P[2], 1.0]); return np.array([(v[0] / v[3] * 0.5 + 0.5) * WIDTH, (1.0 - (v[1] / v[3] * 0.5 + 0.5)) * UP])


def angle(bottom, topmost):
    """Inclinaison (degres) d'un bord a l'ecran par rapport a la verticale ; + = le haut part vers la droite."""
    return math.degrees(math.atan2(topmost[0] - bottom[0], bottom[1] - topmost[1]))


def fake_game():
    j = TC.fake_game(); j.fixed_test = True          # fixed_test : un pas de 1/60 s par appel, sans horloge
    return j


def mound_profile(topmost=0.5, climb_step=8, plateau=30):
    """Hauteur du sol sous le heros, pas du moteur par pas : rampe de `topmost` unites en `climb_step` pas, plateau, descente symetrique (la butte du village du prologue, carte mlout1 : +0,5 u en ~8 pas)."""
    mont = [topmost * (i + 1) / climb_step for i in range(climb_step)]
    return [0.0] * 10 + mont + [topmost] * plateau + mont[::-1][1:] + [0.0] * 3


def panel(j, e, foot, t, k=1.0, inc=0.0):
    """(M, coins du panneau en MONDE, repere de la camera, position de la camera) d'un PNJ dont les pieds sont en `foot`, comme le fait `Game._draw` (voir la boucle des sprites)."""
    M, cam3d = F.Game._town_camera(j, e, ASPECT)
    r_, u_, f_ = cam3d; w, h = F.SPRITE_L * F.SPRITE_SCALE * k, F.SPRITE_H * F.SPRITE_SCALE * k
    zb, zh = 0.185 / 0.48 * w, (0.65 - 0.185) / 0.48 * w
    C = j._view_border[0]
    return M, F.Game._town_panel(j, np.array(foot, float), r_, u_, f_, w, h, zb, zb + zh, t, C, inc), cam3d, C


def shape(M, q):
    """Inclinaison des bords gauche et droit (degres), proportion largeur / hauteur et coins en pixels (bas gauche, bas droit, haut droit, haut gauche)."""
    A, B, Cc, D = (px(M, p) for p in q)
    topmost = 0.5 * ((A[1] - D[1]) + (B[1] - Cc[1])); wid = 0.5 * ((B[0] - A[0]) + (Cc[0] - D[0]))
    return angle(A, D), angle(B, Cc), wid / topmost, (A, B, Cc, D)


def scenario(name_str, dx, dz, t, inc=0.0):
    kw = SAVESTATES[name_str]; hero = TARGET + np.array([kw.get('dec', (0.0, 0.0))[0], kw.get('hy', 0.0), kw.get('dec', (0.0, 0.0))[1]])
    e = TC.fake_state(TARGET, hero, fov=kw.get('fov'), yoff=kw.get('yoff')); j = fake_game()
    for _ in range(3): F.Game._town_camera(j, e, ASPECT)                       # (le reste du centrage se resorbe : meme etat qu'apres quelques images)
    return panel(j, e, hero + np.array([dx, 0.0, dz]), t, kw.get('k', 1.0), inc), hero


class TestStraightSprites(unittest.TestCase):
    def test_vertical_edges_everywhere(self):
        worst = 0.0; r_min, r_max = 9.0, 0.0
        for name_str, (dx, dz) in itertools.product(SAVESTATES, POSITIONS):
            (M, q, _, _), _ = scenario(name_str, dx, dz, 1.0)
            g, d, ratio, (A, B, Cc, D) = shape(M, q)
            worst = max(worst, abs(D[0] - A[0]), abs(Cc[0] - B[0]), abs(A[1] - B[1]), abs(D[1] - Cc[1]))             # bords gauche / droit verticaux ET bas / haut horizontaux (ecart en pixels)
            r_min, r_max = min(r_min, ratio), max(r_max, ratio)
        self.assertLess(worst, 0.01, 'le panneau doit etre un rectangle droit a l\'ecran, a toute position et pour toute camera')
        self.assertGreater(r_min, 0.730); self.assertLess(r_max, 0.745)                                              # proportion constante a +- 1 % (0,72 x la hauteur au centre de l'image : 0,738 mesure)

    def test_default_state_is_raw_panel(self):
        """#184 (« reviens a la position brute des PNJ, exactement comme dans le jeu ») : par defaut la correction des bords est nulle, le cisaillement aussi : le panneau est celui du jeu, sans reconstruction a l'ecran.
        L'ancienne correction complete (#134 : bords verticaux, proportion constante) reste disponible par DQ_CORRECTION_BORDS / --correction-bords."""
        old = os.environ.pop('DQ_SPRITE_INCLINAISON', None); old_b = os.environ.pop('DQ_CORRECTION_BORDS', None)
        try:
            j0 = fake_game(); j0.args = types.SimpleNamespace(edge_correction=None); j0.SPRITE_TILT_DEFAULT = F.Game.SPRITE_TILT_DEFAULT
            self.assertEqual(F.EDGE_CORRECTION_DEFAULT, 0.0)
            self.assertEqual((F.Game._edge_correction(j0), F.Game._sprite_tilt(j0)), (0.0, 0.0))
            for val, att in (('100', 1.0), ('0', 0.0), ('40', 0.4), ('250', 1.0), ('-5', 0.0), ('abc', 0.0), ('', 0.0)):
                os.environ['DQ_CORRECTION_BORDS'] = val; self.assertAlmostEqual(F.Game._edge_correction(j0), att, 9, repr(val))
            os.environ.pop('DQ_CORRECTION_BORDS', None)
            j0.args = types.SimpleNamespace(edge_correction=100.0); self.assertEqual(F.Game._edge_correction(j0), 1.0)          # l'option de la ligne de commande l'emporte
            # panneau par defaut (t = 0) = panneau d'origine : meme coins que le calcul direct des decalages le long de l'axe de la camera du jeu
            (M, q, cam3d, C), hero = scenario('defaut', 6.0, 3.0, 0.0)
            r_, u_, f_ = cam3d; w, h = F.SPRITE_L * F.SPRITE_SCALE, F.SPRITE_H * F.SPRITE_SCALE; zb, zt = 0.185 / 0.48 * w, 0.65 / 0.48 * w
            p = hero + np.array([6.0, 0.0, 3.0]); a, b = p - r_ * (w / 2), p + r_ * (w / 2)
            for x, y in zip(q, (a - f_ * zb, b - f_ * zb, b + u_ * h - f_ * zt, a + u_ * h - f_ * zt)): self.assertTrue(np.allclose(x, y))
        finally:
            for k, v in (('DQ_SPRITE_INCLINAISON', old), ('DQ_CORRECTION_BORDS', old_b)):
                if v is not None: os.environ[k] = v

    def test_full_correction_state_vertical_edges_no_shear(self):
        """La correction des bords complete (DQ_CORRECTION_BORDS=100, #134 / #180) donne toujours un rectangle droit a l'ecran, a toute camera."""
        worst = 0.0
        for name_str, (dx, dz) in itertools.product(SAVESTATES, POSITIONS):
            (M, q, _, _), _ = scenario(name_str, dx, dz, 1.0, 0.0); g, d, ratio, (A, B, Cc, D) = shape(M, q)
            worst = max(worst, abs(D[0] - A[0]), abs(Cc[0] - B[0]), abs(A[1] - B[1]), abs(D[1] - Cc[1])); self.assertAlmostEqual(ratio, 0.738, delta=0.008)
        self.assertLess(worst, 0.01)

    def test_mound_climb_and_descent(self):
        """Camera de la butte (#110) : la hauteur de la camera suit le sol (CAM_Y_RELIEF) ou retarde (escalier) ; a chaque image, un PNJ au bord gauche, au bord droit et en haut reste droit."""
        worst = 0.0; j = fake_game(); y_prev = None
        height_profile = mound_profile(0.5) + [0.5 + 0.1 * i for i in range(30)] + [3.5] * 20 + [3.5 - 0.1 * i for i in range(30)]          # butte, puis une montee d'escalier de 3 u et sa descente
        for hy in height_profile:
            h = 0.047 + hy; hero = np.array([20.0, h, 30.0]); e = TC.fake_state((20.0, h - 0.047, 30.0), hero)
            for dx, dz in ((-9.0, 0.0), (9.0, -4.0), (0.0, 8.0), (-9.0, 9.0)):
                M, q, _, _ = panel(j, e, hero + np.array([dx, 0.0, dz]), 1.0)
                A, B, Cc, D = shape(M, q)[3]; worst = max(worst, abs(D[0] - A[0]), abs(Cc[0] - B[0]))
        self.assertLess(worst, 0.01)

    def test_depth_and_center_unchanged(self):
        """z-buffer (profondeur de chaque coin le long de l'axe de la camera) et hauteur a l'ecran inchanges ; bas du panneau identique ; au centre de l'image, haut identique et largeur moyenne identique."""
        center_pos = 0
        for name_str, (dx, dz) in itertools.product(('defaut', 'fov 40', 'heros en hauteur', 'echelle 0,738'), POSITIONS):
            (M, new_corners, cam3d, C), _ = scenario(name_str, dx, dz, 1.0); (_, ori, _, _), _ = scenario(name_str, dx, dz, 0.0)
            f_ = cam3d[2]
            for a, b in zip(new_corners, ori): self.assertAlmostEqual(float((a - C) @ f_), float((b - C) @ f_), 8, '%s (%s, %s) : profondeur d\'un coin' % (name_str, dx, dz))
            An, Bn, Cn, Dn = (px(M, p) for p in new_corners); Ao, Bo, Co, Do = (px(M, p) for p in ori)
            for a, b in ((An[1], Ao[1]), (Bn[1], Bo[1]), (Cn[1], Co[1]), (Dn[1], Do[1])): self.assertAlmostEqual(a, b, 6, '%s (%s, %s) : ordonnee a l\'ecran' % (name_str, dx, dz))
            self.assertAlmostEqual(0.5 * (An[0] + Bn[0]), 0.5 * (Ao[0] + Bo[0]), 6, 'centre du bas inchange')
            if dx == 0.0 and dz == 0.0:                                          # au centre de l'image (la camera est centree sur le heros : un PNJ a ses pieds est au centre, quelle que soit la camera)
                center_pos += 1
                self.assertAlmostEqual(0.5 * (Cn[0] + Dn[0]), 0.5 * (Co[0] + Do[0]), 6, 'centre de l\'image : le haut ne bouge pas')
                self.assertAlmostEqual(0.5 * ((Bn[0] - An[0]) + (Cn[0] - Dn[0])), 0.5 * ((Bo[0] - Ao[0]) + (Co[0] - Do[0])), delta=0.01 * (Bo[0] - Ao[0]), msg='centre de l\'image : largeur moyenne identique')
        self.assertEqual(center_pos, 4, 'un cas central par camera verifiee')

    def test_original_tilted_guard_rail(self):
        """Sans la correction (panneau d'origine) le sprite se penche de plus de 8 degres pres des bords gauche / droit du 16/9 : le test 1 mesure donc bien quelque chose ; au centre il reste droit a 1 degre pres."""
        (M, q, _, _), _ = scenario('defaut', 9.0, 0.0, 0.0); g, d, _, _ = shape(M, q); self.assertGreater(min(abs(g), abs(d)), 8.0)
        (M, q, _, _), _ = scenario('defaut', -9.0, 0.0, 0.0); g, d, _, _ = shape(M, q); self.assertGreater(min(abs(g), abs(d)), 8.0)
        (M, q, _, _), _ = scenario('defaut', 0.0, 0.0, 0.0); g, d, _, _ = shape(M, q); self.assertLess(max(abs(g), abs(d)), 1.0)

    @staticmethod
    def world_vertical(M, foot, h=1.44):
        return angle(px(M, foot), px(M, foot + np.array([0.0, h, 0.0])))

    def test_finding_world_verticals(self):
        """Cause de l'impression de #134 : une verticale du monde (arete de mur, porte) a 9 u du heros penche a l'ecran de 11 a 19 degres selon la hauteur de l'ecran ou elle se trouve (16/9, camera a 47 degres), contre
        4 a 6,5 degres sur le portrait d'origine ; quand le heros monte ou descend l'angle change de plus de 5 degres, alors que le sprite reste a 0. (C'est la perspective du decor, pas le panneau : voir test 1.)"""
        def sweep(aspect):
            global WIDTH, UP
            WIDTH, UP = (1280.0, 720.0) if aspect > 1 else (450.0, 800.0)
            try:
                dx = -9.0 if aspect > 1 else -3.0; e = TC.fake_state(TARGET, TARGET); j = fake_game(); M, _ = F.Game._town_camera(j, e, aspect)
                return [self.world_vertical(M, TARGET + np.array([dx, 0.0, dz])) for dz in (-5.0, 9.0)]            # bas de l'ecran, haut de l'ecran
            finally: WIDTH, UP = 1280.0, 720.0
        bottom, topmost = sweep(16.0 / 9.0)
        self.assertLess(bottom, -17.0); self.assertGreater(topmost, -12.0); self.assertGreater(abs(bottom) - abs(topmost), 5.0)
        bottom, topmost = sweep(0.5625)
        self.assertLess(abs(bottom), 7.0); self.assertLess(abs(bottom) - abs(topmost), 3.0)

    def test_tilt_toward_world_vertical(self):
        """Essai #134 : avec `inc`, le bord du sprite penche de atan(inc x tan(angle de la verticale du monde au pied)) (a 0,05 degre pres) ; inc = 1 : parallele aux murs ; le sprite et le mur ne s'ecartent plus que de (1 - inc)
        fois l'ecart initial ; sens : le sprite penche du meme cote que le mur ; au centre de l'image (verticale du monde droite) rien ne change ; les bords gauche et droit restent paralleles."""
        worst = 0.0; read_value = 0
        for name_str, (dx, dz), inc in itertools.product(('defaut', 'fov 40', 'heros en hauteur', 'echelle 0,738'), POSITIONS, (0.3, 0.5, 0.7, 1.0)):
            (M, q, cam3d, C), hero = scenario(name_str, dx, dz, 1.0, inc); (_, q0, _, _), _ = scenario(name_str, dx, dz, 1.0, 0.0)
            g, d, _, (A, B, Cc, D) = shape(M, q); g0, d0, _, _ = shape(M, q0)
            foot_bottom = 0.5 * (np.array(q[0]) + np.array(q[1]))                              # milieu du bas du panneau
            wall = self.world_vertical(M, foot_bottom)
            expected = math.degrees(math.atan(inc * math.tan(math.radians(wall))))
            worst = max(worst, abs(g - expected), abs(d - expected)); read_value += 1
            self.assertAlmostEqual(g, d, 5, '%s (%s, %s) inc %s : les deux bords sont paralleles' % (name_str, dx, dz, inc))
            self.assertAlmostEqual(g0, 0.0, 5)
            if abs(wall) > 2.0: self.assertGreater(g * wall, 0.0, '%s (%s, %s) : meme sens que le mur' % (name_str, dx, dz))
            if inc == 1.0: self.assertAlmostEqual(g, wall, delta=0.05, msg='inc = 1 : parallele au mur')
            if dx == 0.0 and dz == 0.0 and name_str == 'defaut': self.assertLess(abs(g), 0.5, 'au centre de l\'image rien ne change')
        self.assertLess(worst, 0.05); self.assertEqual(read_value, 4 * len(POSITIONS) * 4)

    def test_tilt_changes_neither_size_nor_depth(self):
        """Cisaillement pur, pieds fixes : bas du panneau, hauteur et largeur a l'ecran, profondeur de chaque coin (z-buffer) = ceux de `inc` = 0."""
        for name_str, (dx, dz), inc in itertools.product(('defaut', 'fov 40', 'heros en hauteur', 'echelle 0,738'), POSITIONS, (0.5, 1.0)):
            (M, a, cam3d, C), _ = scenario(name_str, dx, dz, 1.0, inc); (_, b, _, _), _ = scenario(name_str, dx, dz, 1.0, 0.0); f_ = cam3d[2]
            for u, v in zip(a, b): self.assertAlmostEqual(float((u - C) @ f_), float((v - C) @ f_), 8, '%s (%s, %s) inc %s : profondeur d\'un coin' % (name_str, dx, dz, inc))
            Pa = [px(M, p) for p in a]; Pb = [px(M, p) for p in b]
            for i in range(4): self.assertAlmostEqual(Pa[i][1], Pb[i][1], 6, 'ordonnee a l\'ecran du coin %d' % i)
            for i in (0, 1): self.assertAlmostEqual(Pa[i][0], Pb[i][0], 6, 'les pieds ne bougent pas')
            self.assertAlmostEqual(Pa[1][0] - Pa[0][0], Pb[1][0] - Pb[0][0], 6, 'largeur du bas')
            self.assertAlmostEqual(Pa[2][0] - Pa[3][0], Pb[2][0] - Pb[3][0], 6, 'largeur du haut')

    def test_climb_and_descent_minus_offset_with_wall(self):
        """Constat de #134 : un PNJ au bord gauche, quand le heros monte ou descend, change de hauteur a l'ecran et l'ecart sprite / mur varie de plusieurs degres ; avec inc = 0,5 la variation est divisee par deux (a 5 % pres)."""
        def spacings(inc):
            out = []
            for dz in (-5.0, 0.0, 4.0, 9.0):                                                  # le PNJ du bord gauche, a differentes hauteurs d'ecran (= le heros qui monte ou descend)
                (M, q, _, _), _ = scenario('defaut', -9.0, dz, 1.0, inc); g = shape(M, q)[0]
                wall = self.world_vertical(M, 0.5 * (np.array(q[0]) + np.array(q[1]))); out.append(wall - g)
            return out
        e0, e5 = spacings(0.0), spacings(0.5)
        self.assertGreater(max(e0) - min(e0), 5.0, 'constat : sans inclinaison, l\'ecart sprite / mur varie de plus de 5 degres')
        self.assertGreater(max(abs(x) for x in e0), 15.0)
        for a, b in zip(e0, e5): self.assertAlmostEqual(b, a * 0.5, delta=0.05 * abs(a) + 0.7)
        self.assertLess(max(e5) - min(e5), 0.55 * (max(e0) - min(e0)))

    def test_setting_by_environment_variable(self):
        """DQ_SPRITE_INCLINAISON : 0 a 100 (%) ; absente, vide ou illisible : 0 % (defaut depuis #180) ; bornee."""
        j = TC.fake_game(); j.SPRITE_TILT_DEFAULT = F.Game.SPRITE_TILT_DEFAULT; old = os.environ.pop('DQ_SPRITE_INCLINAISON', None)
        try:
            self.assertEqual(F.Game._sprite_tilt(j), 0.0); self.assertEqual(F.Game.SPRITE_TILT_DEFAULT, 0.0)
            for val, att in (('0', 0.0), ('100', 1.0), ('30', 0.3), ('70.5', 0.705), ('250', 1.0), ('-5', 0.0), ('', 0.0), ('  ', 0.0), ('abc', 0.0)):
                os.environ['DQ_SPRITE_INCLINAISON'] = val; self.assertAlmostEqual(F.Game._sprite_tilt(j), att, 9, repr(val))
        finally:
            os.environ.pop('DQ_SPRITE_INCLINAISON', None)
            if old is not None: os.environ['DQ_SPRITE_INCLINAISON'] = old

    def test_unknown_camera_or_correction_cut(self):
        """Sans camera (C inconnue) ou avec la correction des bords coupee (t = 0) : le panneau d'origine, meme avec `inc`."""
        (M, q, cam3d, C), hero = scenario('defaut', 6.0, 3.0, 0.0, 0.8); (_, q0, _, _), _ = scenario('defaut', 6.0, 3.0, 0.0, 0.0)
        for a, b in zip(q, q0): self.assertTrue(np.allclose(a, b))
        r_, u_, f_ = cam3d; w, h = F.SPRITE_L * F.SPRITE_SCALE, F.SPRITE_H * F.SPRITE_SCALE; zb, zh = 0.185 / 0.48 * w, (0.65 - 0.185) / 0.48 * w
        j = TC.fake_game(); a = F.Game._town_panel(j, hero, r_, u_, f_, w, h, zb, zb + zh, 1.0, None, 0.8); b = F.Game._town_panel(j, hero, r_, u_, f_, w, h, zb, zb + zh, 0.0, None, 0.0)
        for x, y in zip(a, b): self.assertTrue(np.allclose(x, y))


def sprites_ref_frame(j, e, corr=0.0):
    """(M, repere de la vue, repere des sprites choisi par `Game._sprite_reference`, position de la camera de la visionneuse) pour l'etat de camera `j`."""
    M, cam3d = F.Game._town_camera(j, e, ASPECT)
    return M, cam3d, F.Game._sprite_reference(j, cam3d, corr), j._view_border[0]


def pitch(fw):
    """Inclinaison (degres, vers le bas) d'un axe avant."""
    return math.degrees(math.asin(-fw[1]))


class TestSpritesLikeTheGame(unittest.TestCase):
    """#184 : le panneau d'un PNJ garde l'inclinaison de la camera DU JEU : monter ou descendre la camera (Haut / Bas) ne le change pas, la rotation autour du heros (Gauche / Droite) le suit."""

    def borders(self, **kw):
        hero = TARGET + np.array([0.0, kw.get('hy', 0.0), 0.0]); e = TC.fake_state(TARGET, hero, fov=kw.get('fov'), yoff=kw.get('yoff')); j = fake_game()
        for _ in range(3): F.Game._town_camera(j, e, ASPECT)
        return j, e, hero

    def test_without_tilt_or_rotation_game_reference_frame(self):
        """Camera du jeu telle quelle : le repere des sprites est celui de la vue ET celui de `_game_border` (la camera du jeu : depuis #264 la vue n'ajoute plus ni zoom, ni rotation, ni inclinaison)."""
        j, e, _ = self.borders(); M, cam3d, rep, _ = sprites_ref_frame(j, e)
        _, dr, ha, fw = F.Game._game_border(j, e)
        for a, b in zip(rep, cam3d): self.assertTrue(np.allclose(a, b))
        for a, b in zip(rep, (dr, ha, fw)): self.assertTrue(np.allclose(a, b, atol=1e-9))

    def test_panel_tilt_in_world_matches_game(self):
        """Le panneau d'origine est quasi vertical dans le monde (le haut penche de 36 degres vers la camera) ; cette pente (angle du bord bas -> haut avec la verticale) est la meme a toute hauteur du heros."""
        w, h = F.SPRITE_L * F.SPRITE_SCALE, F.SPRITE_H * F.SPRITE_SCALE; zb, zt = 0.185 / 0.48 * w, 0.65 / 0.48 * w; slopes = []
        for hy in (0.0, 0.5, 3.0):
            j, e, hero = self.borders(hy=hy); _, _, r, _ = sprites_ref_frame(j, e)
            a, b, c, d = F.Game._town_panel(j, hero, *r, w, h, zb, zt, 0.0, None); mid_bottom, mid_top = 0.5 * (a + b), 0.5 * (c + d); v = mid_top - mid_bottom
            slopes.append(math.degrees(math.atan2(math.hypot(v[0], v[2]), v[1])))
        for x in slopes: self.assertAlmostEqual(x, slopes[0], 6)
        self.assertLess(slopes[0], 40.0)

    def test_edge_correction_and_settings_keep_view_reference(self):
        """Correction des bords > 0 (essai #134) : le repere de la vue (la reconstruction a l'ecran en a besoin) ; DQ_SPRITES_SUR_VUE : l'ancien alignement ; sans camera : rien."""
        j, e, _ = self.borders(); _, v, r0, _ = sprites_ref_frame(j, e, 0.0); _, _, r1, _ = sprites_ref_frame(j, e, 0.5)
        [self.assertTrue(np.allclose(a, b, atol=1e-9)) for a, b in zip(r0, v)]; [self.assertTrue(np.allclose(a, b)) for a, b in zip(r1, v)]          # (la vue est la camera du jeu : meme repere avec ou sans correction)
        old = os.environ.get('DQ_SPRITES_SUR_VUE'); os.environ['DQ_SPRITES_SUR_VUE'] = '1'
        try: [self.assertTrue(np.allclose(a, b)) for a, b in zip(F.Game._sprite_reference(j, v, 0.0), v)]
        finally:
            if old is None: os.environ.pop('DQ_SPRITES_SUR_VUE', None)
            else: os.environ['DQ_SPRITES_SUR_VUE'] = old
        self.assertIsNone(F.Game._sprite_reference(j, None, 0.0))

    def test_free_scene_camera_and_minigame_unchanged(self):
        """Camera libre (position et angles fixes par le script) : le repere des sprites est celui de la vue ; sans appel de la camera, repli sur la vue."""
        j = fake_game(); j._rot_camera = lambda e: F.Game._rot_camera(j, e)
        e = TC.fake_state(TARGET, TARGET, free=True); e.cam_rot = (45.0, 0.0, 0.0)
        M, cam3d = F.Game._town_camera(j, e, ASPECT); rep = F.Game._sprite_reference(j, cam3d, 0.0)
        for a, b in zip(rep, cam3d): self.assertTrue(np.allclose(a, b))
        jv = types.SimpleNamespace(); r = F.Game._sprite_reference(jv, cam3d, 0.0)
        for a, b in zip(r, cam3d): self.assertTrue(np.allclose(a, b))


if __name__ == '__main__':
    unittest.main(verbosity=2)
