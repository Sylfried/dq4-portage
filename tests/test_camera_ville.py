"""Test de la camera des villes (sans fenetre ni moteur : `Jeu._camera_ville` est appelee sur un faux objet) :

  1. la matrice du portage = le pipeline d'Unity re-ecrit a part (SceneCamera.Update : LookAt, tangage - lookDownAdjust, avance de distanceAdjust, Perspective(fov x 4/3, 1/aspect) dont on echange
     [0] et [5], s_yOffset) a l'ecran portrait d'origine (0,5625) ;
  2. camera TOUJOURS centree sur le joueur (plus d'option, #47) : le heros reste au centre de l'image meme quand la cible du jeu est ailleurs (bord de la carte), a toute vitesse du jeu (x1 a x4) et toute cadence
     d'affichage, et apres l'arret ; aucune borne de la visionneuse ;
  2 bis. hauteur (#47, #110) : un relief de moins de CAM_Y_RELIEF (la butte du village du prologue, +0,5 u) est suivi EXACTEMENT comme le mobile (le heros ne bouge pas a l'ecran) ; au-dela (escaliers, etages) la
     camera retarde comme avant (lissage CAM_Y_TAU, borne CAM_Y_MAX), sans a-coup, et recentre le heros a l'arret ; coupure du jeu = hauteur du jeu aussitot ;
  3. camera prise par le jeu (travelling, cible = un personnage, camera libre d'une scene, mini-jeu) : la visionneuse n'ajoute RIEN (ni centrage, ni borne) : le rendu ne depend plus du heros ;
  4. `Jeu._camera_menee` : verrou de la TownCamera du moteur qui mene la camera ailleurs que sur le joueur, ou qui la tient sur le joueur.

    python3 outils/test_camera_ville.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import math, os, sys, types, unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _chemins          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.fenetre import jeu as F

ASPECT_16_9 = 16.0 / 9.0
HORLOGE = [0.0]


def faux_jeu(bornes_x=None, jeu=False):
    j = types.SimpleNamespace(zoom=1.0, reg={}, cam_jeu=jeu, cam_saut=True, cam_dec=[0.0, 0.0], cam_res=[0.0, 0.0], cam_centre=False, cam_ref_y=None, t_centre=None, fixe_test=False,
                              bornes_x=bornes_x, lacet=0.0, angle_cam=0.0, cam_bloquee=False, carte_nom='x', n_boucle=0, _cadre_vue=None)
    j._rot_camera = lambda e: None
    return j


def faux_etat(cib, hero, fov=None, yoff=None, partie=None, libre=False):
    cib = np.array(cib, float)
    return types.SimpleNamespace(cam_pos=cib + np.array([0.0, 28.94, -27.0]), cam_cible=cib, cam_fov=fov, cam_near=None, cam_far=None, cam_yoff=yoff, cam_bas=None, cam_libre=libre, cam_rot=None,
                                 sprites={0: {'pos': tuple(hero)}}, partie=partie)


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
        self.remettre_temps = _chemins.poser_global('time', types.SimpleNamespace(perf_counter=lambda: HORLOGE[0], time=lambda: HORLOGE[0], sleep=lambda *a: None))

    def tearDown(self): self.remettre_temps()

    def test_projection_comme_unity(self):
        rng = np.random.default_rng(1); pire = 0.0
        for _ in range(100):
            cib = rng.uniform(-30, 30, 3); cib[1] = 0
            pos = cib + np.array([rng.uniform(-8, 8), 29.0 + rng.uniform(-3, 3), -27.0 + rng.uniform(-3, 3)])
            fov = float(rng.choice([9.5, 10.0])); yoff = float(rng.choice([0.0, 0.05]))
            pts = [cib + np.array([dx, dy, dz]) for dx in (-5, 0, 5) for dy in (0, 1.5) for dz in (-6, 0, 6)]
            ref = unity_ndc(pos, cib, fov, F.VILLE_NEAR, F.VILLE_FAR, yoff, F.ASPECT_PORTRAIT, pts)
            e = faux_etat(cib, cib, fov, yoff); e.cam_pos = pos; e.sprites = {}          # sans heros : champ horizontal fixe de l'original (avec lui, zoom commun de la visionneuse)
            M, _ = F.Jeu._camera_ville(faux_jeu(), e, F.ASPECT_PORTRAIT)
            pire = max(pire, float(np.abs(np.array([ndc(M, p) for p in pts]) - ref).max()))
        self.assertLess(pire, 1e-9)

    def course(self, dt, f, bord=5.0, arret=8.0):
        """Un heros court (30 pas du moteur par seconde x f) vers une zone ou le jeu borne sa cible a `bord`, puis s'arrete : ecart maximal du heros au centre de l'image (NDC x)."""
        HORLOGE[0] = 0.0; j = faux_jeu(); x = 0.0; t = 0.0; pire = 0.0
        while t < 4.0:
            HORLOGE[0] += dt; t += dt; x = min(arret, x + 0.2128 * 30.0 * f * dt)
            e = faux_etat((min(x, bord), 0.0, 0.0), (x, 0.0, 0.0))
            M, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9); pire = max(pire, abs(ndc(M, (x, 0.0, 0.0))[0]))
        return pire

    def test_centrage_rigide_a_toute_vitesse(self):
        for dt in (1 / 30, 1 / 60, 1 / 144):
            for f in (1.0, 1.5, 2.0, 3.0, 4.0): self.assertLess(self.course(dt, f), 1e-6, 'dt=1/%d x%s' % (round(1 / dt), f))

    def montee(self, dt, vy=0.113, pas=30, repos=8.0, jeu=False, tau=None):
        """Le heros monte `pas` pas du moteur de `vy` (rampe a 45 degres a la marche), s'arrete, puis `repos` secondes : NDC y du heros a chaque image (la cible du jeu suit le heros a 0,047 pres, comme le moteur)."""
        if tau is not None: _chemins.poser_global('CAM_Y_TAU', tau)
        HORLOGE[0] = 0.0; j = faux_jeu(jeu=jeu); ys = []; y_prec = None; ys_hero = []
        for k in range(pas + int(repos * 30)):
            hy = 0.047 + min(k, pas) * vy; a = 0.0
            while a < 1.0 - 1e-9:
                a = min(1.0, a + dt * 30.0); h = hy if y_prec is None else y_prec + (hy - y_prec) * a
                HORLOGE[0] += dt; e = faux_etat((0.0, h - 0.047, 0.78), (0.0, h, 0.78))
                M, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9); ys.append(ndc(M, (0.0, h, 0.78))[1]); ys_hero.append(h)
            y_prec = hy
        return ys, j

    def test_escalier_hauteur_lissee(self):
        """Escaliers, rampes, ponts (retour #45 + reponse de Sylfried, #47) : le moteur d'origine suit la hauteur du heros a chaque pas (TownCamera::execute : setTarget(joueur), aucun amortissement en Y ; mesure sur
        la rampe de `ckf4` : cible Y = heros Y - 0,047) et c'est ce qui donnait « l'effet de montee ». La visionneuse garde maintenant une hauteur de reference qui rejoint lentement celle du jeu (CAM_Y_TAU) : pendant la
        montee le heros s'eleve a l'ecran au lieu de rester fixe, bien moins que la montee, jamais hors champ ; a l'arret la camera le recentre exactement, a toute cadence d'affichage."""
        tau = F.CAM_Y_TAU
        try:
            for dt in (1 / 30, 1 / 60, 1 / 144):
                ys, j = self.montee(dt)
                exc = max(abs(y - ys[0]) for y in ys)
                self.assertGreater(exc, 0.02, 'la camera ignore une partie de la montee (dt=1/%d)' % round(1 / dt))
                self.assertLess(exc, 0.3, 'le heros reste bien dans l\'ecran (dt=1/%d)' % round(1 / dt))
                self.assertLess(abs(ys[-1] - ys[0]), 2e-3, 'recentre a l\'arret (dt=1/%d)' % round(1 / dt))
            ref_, _ = self.montee(1 / 60, tau=0.0)                              # CAM_Y_TAU = 0 : exactement la camera du jeu (le heros reste au meme point de l'image)
            self.assertLess(max(ref_) - min(ref_), 1e-9)
        finally: _chemins.poser_global('CAM_Y_TAU', tau)

    def parcours(self, dt, pas_y, repos=4.0, **kw):
        """Comme `montee`, mais la hauteur du heros a chaque pas du moteur est donnee (`pas_y`, liste de hauteurs de sol) : NDC y du heros a chaque image."""
        HORLOGE[0] = 0.0; j = faux_jeu(**kw); ys = []; y_prec = None
        for k in range(len(pas_y) + int(repos * 30)):
            hy = 0.047 + pas_y[min(k, len(pas_y) - 1)]; a = 0.0
            while a < 1.0 - 1e-9:
                a = min(1.0, a + dt * 30.0); h = hy if y_prec is None else y_prec + (hy - y_prec) * a
                HORLOGE[0] += dt; e = faux_etat((0.0, h - 0.047, 0.78), (0.0, h, 0.78))
                M, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9); ys.append(ndc(M, (0.0, h, 0.78))[1])
            y_prec = hy
        return ys, j

    @staticmethod
    def profil_butte(haut=0.5, pas_montee=8, plateau=30):
        """Hauteur du sol sous le heros, pas du moteur par pas : rampe de `haut` unites en `pas_montee` pas, plateau, descente symetrique (la butte du village du prologue, carte mlout1 : +0,5 u en ~8 pas)."""
        mont = [haut * (i + 1) / pas_montee for i in range(pas_montee)]
        return [0.0] * 10 + mont + [haut] * plateau + mont[::-1][1:] + [0.0] * 3

    def test_butte_suivie_exactement(self):
        """#110 (retour de Sylfried : « en marchant sur la butte la camera reste sur le meme plan ») : le moteur d'origine suit la hauteur du heros a chaque pas (setTarget(joueur), aucun lissage en Y ; SceneCamera.Update
        non plus), donc sur un relief de moins de CAM_Y_RELIEF (la butte : +0,5 u) le heros reste exactement au meme point de l'image, a la montee comme a la descente, a toute cadence d'affichage. Avant : le lissage
        de #47 retardait la camera et le heros montait puis descendait a l'ecran (18 a 29 px a 720 p)."""
        for dt in (1 / 30, 1 / 60, 1 / 144):
            for haut in (0.2, 0.5, 0.58):
                ys, j = self.parcours(dt, self.profil_butte(haut))
                self.assertLess(max(ys) - min(ys), 1e-9, 'butte de %s u, dt=1/%d : le heros doit rester au meme point de l\'image' % (haut, round(1 / dt)))
            ys, _ = self.parcours(dt, self.profil_butte(0.5), jeu=True)              # la camera du jeu (scene) : toujours exacte
            self.assertLess(max(ys) - min(ys), 1e-9)

    def test_butte_ancien_lissage_visible(self):
        """Garde-fou du test precedent : avec CAM_Y_RELIEF = 0 (lissage de #47 seul) la meme butte ferait bien bouger le heros a l'ecran (c'est le defaut de #110)."""
        relief = F.CAM_Y_RELIEF
        try:
            _chemins.poser_global('CAM_Y_RELIEF', 0.0)
            ys, _ = self.parcours(1 / 60, self.profil_butte(0.5))
            self.assertGreater((max(ys) - min(ys)) * 360, 10.0, 'sans bande morte : le heros bouge de plus de 10 px (720 p)')
        finally: _chemins.poser_global('CAM_Y_RELIEF', relief)

    def test_escalier_reste_lisse_au_dela_de_la_bande_morte(self):
        """Un denivele plus grand que CAM_Y_RELIEF (escalier, etage : +1,9 u en 16 pas) garde l'effet de #47 : le heros s'eleve a l'ecran, jamais hors champ, et la camera le recentre a l'arret ; la bande morte
        ne retarde pas plus que le lissage seul (plus petit retard), et le mouvement du heros a l'ecran n'est jamais plus brusque (d'une image a l'autre) qu'avec le lissage seul."""
        relief = F.CAM_Y_RELIEF
        try:
            for haut, pas in ((1.0, 8), (1.9, 16), (3.0, 20), (-1.9, 16), (6.0, 40)):
                prof = [0.0] * 10 + [haut * (i + 1) / pas for i in range(pas)] + [haut] * 30
                if haut < 0: prof = [-haut] * 10 + [-haut + haut * (i + 1) / pas for i in range(pas)] + [0.0] * 30
                _chemins.poser_global('CAM_Y_RELIEF', relief); nou, _ = self.parcours(1 / 60, prof, repos=10.0)
                _chemins.poser_global('CAM_Y_RELIEF', 0.0); anc, _ = self.parcours(1 / 60, prof, repos=10.0)
                self.assertGreater(max(abs(y - nou[0]) for y in nou), 0.005 if abs(haut) < 2 else 0.02, 'haut=%s : le heros doit s\'elever a l\'ecran' % haut)
                self.assertLess(max(abs(y - nou[0]) for y in nou), 0.45, 'haut=%s : jamais hors champ' % haut)
                self.assertLess(max(abs(y - nou[0]) for y in nou), max(abs(y - anc[0]) for y in anc) + 1e-9, 'haut=%s : pas plus de retard qu\'avec le lissage seul' % haut)
                self.assertLess(abs(nou[-1] - nou[0]), 2e-3, 'haut=%s : recentre a l\'arret' % haut)
                brusque = lambda ys: max(abs(b - a) for a, b in zip(ys, ys[1:]))
                self.assertLessEqual(brusque(nou), brusque(anc) + 1e-9, 'haut=%s : pas de saut d\'une image a l\'autre plus grand qu\'avec le lissage seul' % haut)
        finally: _chemins.poser_global('CAM_Y_RELIEF', relief)

    def test_hauteur_camera_invariants(self):
        """`hauteur_camera` (fonction pure) sur des profils aleatoires : la zone de repos reste a CAM_Y_RELIEF de la cible et ne bouge jamais plus vite qu'elle (contraction : aucun a-coup), la reference reste a CAM_Y_MAX
        de la zone, le decalage est nul tant que la cible reste dans la bande morte, et `None` (coupure, premiere image) rend la camera du jeu."""
        self.assertEqual(F.hauteur_camera(None, None, 3.0, 1 / 60), (3.0, 3.0, 0.0))
        self.assertEqual(F.hauteur_camera(1.0, None, 3.0, 1 / 60), (3.0, 3.0, 0.0))
        rng = np.random.default_rng(7)
        for _ in range(200):
            c = float(rng.uniform(-5, 5)); zone, ref, dy = F.hauteur_camera(None, None, c, 1 / 60)
            for _ in range(300):
                c2 = c + float(rng.normal(0, rng.choice([0.01, 0.1, 1.0]))); dt = float(rng.choice([1 / 30, 1 / 60, 1 / 144]))
                z2, r2, dy = F.hauteur_camera(zone, ref, c2, dt)
                self.assertLessEqual(abs(z2 - c2), F.CAM_Y_RELIEF + 1e-9)
                self.assertLessEqual(abs(z2 - zone), abs(c2 - c) + 1e-9)             # contraction : la zone ne s'emballe jamais
                self.assertLessEqual(abs(r2 - z2), F.CAM_Y_MAX + 1e-9); self.assertAlmostEqual(dy, r2 - z2, 12)
                zone, ref, c = z2, r2, c2
        zone, ref, dy = F.hauteur_camera(None, None, 0.0, 1 / 60)
        for c in (0.1, -0.3, 0.55, -0.6, 0.0):
            zone, ref, dy = F.hauteur_camera(zone, ref, c, 1 / 60); self.assertEqual(dy, 0.0, 'cible a %s : dans la bande morte' % c)

    def test_butte_coupure_remet_la_zone(self):
        """Coupure du jeu (teleportation, changement de carte) : la zone de repos et la reference sont remises sur la hauteur du jeu (aucun glissement) ; camera prise par le jeu : plus aucun etat."""
        HORLOGE[0] = 0.0; j = faux_jeu(); e = faux_etat((0.0, 0.0, 0.78), (0.0, 0.047, 0.78))
        for _ in range(30): HORLOGE[0] += 1 / 60; F.Jeu._camera_ville(j, e, ASPECT_16_9)
        e = faux_etat((0.0, 0.5, 0.78), (0.0, 0.547, 0.78))
        for _ in range(30): HORLOGE[0] += 1 / 60; F.Jeu._camera_ville(j, e, ASPECT_16_9)
        self.assertAlmostEqual(j.cam_zone_y, 0.0, 9); self.assertAlmostEqual(j.cam_ref_y, 0.0, 9)           # la butte (+0,5 u) est dans la bande morte
        e = faux_etat((0.0, 6.0, 0.78), (0.0, 6.047, 0.78)); j.cam_saut = True; HORLOGE[0] += 1 / 60
        F.Jeu._camera_ville(j, e, ASPECT_16_9)
        self.assertAlmostEqual(j.cam_zone_y, 6.0, 9); self.assertAlmostEqual(j.cam_ref_y, 6.0, 9)
        j.cam_jeu = True; HORLOGE[0] += 1 / 60; F.Jeu._camera_ville(j, e, ASPECT_16_9)
        self.assertIsNone(j.cam_zone_y); self.assertIsNone(j.cam_ref_y)

    def test_escalier_a_toute_vitesse_de_jeu(self):
        """Marche acceleree (x4 : 4 fois plus de pas du moteur par seconde) ou tres grande hauteur (tour) : l'ecart de la camera au jeu est borne par CAM_Y_MAX, le heros ne sort jamais de l'ecran."""
        borne = None
        for vy in (0.113, 0.45, 1.0):
            ys, j = self.montee(1 / 60, vy=vy, pas=30)
            exc = max(abs(y - ys[0]) for y in ys); borne = exc if borne is None else borne
            self.assertLess(exc, 0.45, 'vy=%s' % vy)                                   # (CAM_Y_MAX = 3 unites ~ 0,29 de NDC)
            self.assertLess(abs(ys[-1] - ys[0]), 2e-3)

    def test_escalier_coupure_du_jeu_sans_glissement(self):
        """Le jeu coupe (teleportation, changement de carte : `cam_saut`) ou prend la camera (scene) : la hauteur est celle du jeu aussitot, sans glissement."""
        HORLOGE[0] = 0.0; j = faux_jeu(); e = faux_etat((0.0, 0.0, 0.78), (0.0, 0.047, 0.78))
        for _ in range(30): HORLOGE[0] += 1 / 60; F.Jeu._camera_ville(j, e, ASPECT_16_9)
        e = faux_etat((0.0, 6.0, 0.78), (0.0, 6.047, 0.78)); j.cam_saut = True; HORLOGE[0] += 1 / 60
        M, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9)
        ref, _ = F.Jeu._camera_ville(faux_jeu(), e, ASPECT_16_9)
        self.assertLess(float(np.abs(M - ref).max()), 1e-9, 'coupure : camera identique a celle d\'un jeu qui arrive sur cette hauteur')
        ys, j = self.montee(1 / 60, jeu=True)
        self.assertLess(max(ys) - min(ys), 1e-9, 'camera du jeu : le heros reste au meme point de l\'image (le moteur suit sa hauteur)')
        self.assertIsNone(j.cam_ref_y)

    def test_toujours_centree_sur_le_heros(self):
        """Plus d'option : la camera est centree sur le heros meme quand la cible du jeu est ailleurs (bord de la carte), et les anciennes bornes 16/9 (`bornes_x`) ne s'appliquent plus."""
        for bornes in (None, (-3.0, 3.0)):
            HORLOGE[0] = 0.0; j = faux_jeu(bornes_x=bornes)
            e = faux_etat((3.0, 0.0, 11.3), (6.07, 0.0, 11.3))               # le jeu a borne sa cible a x = 3 ; le heros est en x = 6,07
            for _ in range(60): HORLOGE[0] += 1 / 60; M, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9)
            self.assertLess(abs(ndc(M, (6.07, 0.0, 11.3))[0]), 1e-6, 'bornes=%s' % (bornes,))

    def regime(self, **kw):
        """Matrice de la camera pour deux positions du heros (la cible du jeu est la meme) : si les deux matrices different, la visionneuse a recentre la camera sur le heros."""
        out = []
        for hx in (0.0, 2.0):
            HORLOGE[0] = 0.0; j = faux_jeu(jeu=kw.get('jeu', False)); e = faux_etat((5.0, 0.0, 4.0), (hx, 0.0, 4.0), partie=kw.get('partie'), libre=kw.get('libre', False))
            if kw.get('libre'): e.cam_rot = (40.0, 0.0, 0.0)
            j._rot_camera = lambda e: np.eye(3)
            for _ in range(60): HORLOGE[0] += 1 / 60; M, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9)
            out.append(M)
        return float(np.abs(out[0] - out[1]).max())

    def test_camera_prise_par_le_jeu(self):
        """Le jeu la mene (TownCamera verrouillee et menee ailleurs : travelling, cible = un personnage, retour) : le rendu est exactement ce que le moteur commande, indifferent au heros ; sans cela, centree sur le heros."""
        self.assertGreater(self.regime(jeu=False), 1e-3, 'le joueur a la camera : elle suit le heros')
        self.assertLess(self.regime(jeu=True), 1e-9, 'scene : camera du jeu telle quelle')
        self.assertLess(self.regime(libre=True), 1e-9, 'camera libre d\'une scene (paquet 11, bit 7) : cadrage du jeu')
        self.assertLess(self.regime(partie=F.MO.PARTIE_CASINO), 1e-9, 'mini-jeu : cadrage du jeu')

    def test_retour_de_scene_sans_saut(self):
        """Fin d'une scene (le jeu rend la camera) : la camera ne saute pas, elle rejoint le heros en douceur (aucun saut d'une image a l'autre) ; au declenchement d'une scene, meme chose en sens inverse."""
        HORLOGE[0] = 0.0; j = faux_jeu(jeu=True); e = faux_etat((5.0, 0.0, 4.0), (0.0, 0.0, 4.0))
        for _ in range(30): HORLOGE[0] += 1 / 60; M, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9)
        x0 = ndc(M, (0.0, 0.0, 4.0))[0]; self.assertGreater(abs(x0), 0.1)
        j.cam_jeu = False; xs = [x0]
        for _ in range(90): HORLOGE[0] += 1 / 60; M, _ = F.Jeu._camera_ville(j, e, ASPECT_16_9); xs.append(ndc(M, (0.0, 0.0, 4.0))[0])
        self.assertLess(max(abs(b - a) for a, b in zip(xs, xs[1:])), abs(x0) * 0.5, 'pas de saut')
        self.assertLess(abs(xs[-1]), 1e-3, 'le heros est revenu au centre')

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
