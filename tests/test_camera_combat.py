"""Effets de camera en combat (lot #47, retour de Sylfried : « certains ennemis peuvent faire changer l'angle de la camera pendant leur attaque »).

Ce que le jeu d'origine fait (lu au desassemblage de libdq4core.so et verifie sur le moteur reel) :
  - `BattleMonster::startAnimation(action, variante)` cherche l'enregistrement `param::MonsterAnim` (monstre, action, variante) et appelle `BattleCamera::setCameraAnimation(camA, camB, attente)` avec les
    octets +0x13 / +0x14 / +0xe de cet enregistrement ; les sorts passent par `BattleEffectUnit::waitStart` (`BattleCamera::setFilename`) ;
  - `EffectParam::getCameraFile(n)` donne le fichier `camera/<nom>.cam` (images cles de position et d'angle, lus par `CameraControl::calc`) ; deux fichiers s'additionnent (A = mouvement, B = secousse) ;
  - a chaque image `BattleCamera::executeForMap` calcule position et angle, `dss::Camera::send_unity` les envoie dans UN paquet 10 (bit 0 position, bit 2 angle) : rien d'autre ne pilote la camera.
La visionneuse n'a donc rien a rejouer : elle applique chaque paquet 10 (`Etat.appliquer`) et `_camera_combat` en fait la matrice. Ce test le prouve :
  - sans moteur : application des paquets 10 par morceaux, roulis et tangage / lacet dans la matrice ;
  - moteur reel (facultatif, DQ_APK + DQ_SAVES) : un vrai combat contre un monstre dont l'attaque a une camera (indice 7 : `setCameraAnimation(25, 0, 0)`, la camera monte puis revient), et quatre
    camera injectees (secousse, grand mouvement de boss, plongee de sort final) : elles reviennent toutes exactement a leur point de depart et le roulis envoye vaut toujours 0.

    python3 outils/test_camera_combat.py
    DQ_APK=... DQ_SAVES=... python3 outils/flux_session/moteur_slot.sh python3 outils/test_camera_combat.py        (une minute environ)
"""
import math, os, struct, sys, tempfile, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import numpy as np
from dq4_pc.fenetre import jeu as F
from dq4_pc.noyau import moteur as MO

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
BASE_POS, BASE_ROT = (0.0, 4.75, -39.8125), (-0.703125, 180.0, 0.0)          # camera de combat au repos (apres l'approche du debut)


def paquet10(drapeaux, flottants): return (10, [drapeaux], list(flottants))


# ------------------------------------------------------------------------------------------------------------------------------ sans moteur
class ApplicationDesPaquets(unittest.TestCase):
    def setUp(self):
        self.e = MO.Etat(); self.e.appliquer([paquet10(5, BASE_POS + BASE_ROT)], lambda: 'btl_pl_d')

    def test_position_et_angle_du_premier_paquet(self):
        self.assertEqual(tuple(self.e.cam_pos), BASE_POS); self.assertEqual(tuple(self.e.cam_rot), BASE_ROT)

    def test_paquet_de_position_seule_garde_l_angle(self):
        self.e.appliquer([paquet10(1, (0.0, 7.1, -39.8125))], lambda: 'btl_pl_d')
        self.assertEqual(tuple(self.e.cam_pos), (0.0, 7.1, -39.8125)); self.assertEqual(tuple(self.e.cam_rot), BASE_ROT)

    def test_paquet_d_angle_seul_garde_la_position(self):
        self.e.appliquer([paquet10(4, (5.5, 170.0, 0.0))], lambda: 'btl_pl_d')
        self.assertEqual(tuple(self.e.cam_pos), BASE_POS); self.assertEqual(tuple(self.e.cam_rot), (5.5, 170.0, 0.0))

    def test_plusieurs_paquets_dans_une_image_le_dernier_gagne(self):
        self.e.appliquer([paquet10(1, (0.0, 5.0, -39.0)), paquet10(1, (0.0, 6.0, -38.0)), paquet10(4, (1.0, 181.0, 0.0))], lambda: 'btl_pl_d')
        self.assertEqual(tuple(self.e.cam_pos), (0.0, 6.0, -38.0)); self.assertEqual(tuple(self.e.cam_rot), (1.0, 181.0, 0.0))


class MatriceDeLaCamera(unittest.TestCase):
    """`_camera_combat` : la camera du combat est celle d'Unity (euler (-x, -(y + 180), z)) ; position, tangage, lacet ET roulis changent l'image."""
    def jeu(self): return types.SimpleNamespace(cb_mx=False, _rot_camera=lambda e: F.Jeu._rot_camera(None, e))

    def projeter(self, pos, rot, point):
        e = types.SimpleNamespace(cam_pos=pos, cam_rot=rot, cam_fov=None)
        M, _ = F.Jeu._camera_combat(self.jeu(), e, 16 / 9)
        v = M @ np.array([point[0], point[1], point[2], 1.0]); return v[0] / v[3], v[1] / v[3], v[3]

    def test_repos_regarde_vers_z_positif(self):
        x, y, w = self.projeter(BASE_POS, BASE_ROT, (0.0, 4.75, 0.0))
        self.assertGreater(w, 0); self.assertAlmostEqual(x, 0.0, places=3)

    def test_lacet_deplace_l_image_horizontalement(self):
        x0, _, _ = self.projeter(BASE_POS, BASE_ROT, (0.0, 4.75, 0.0))
        x1, _, _ = self.projeter(BASE_POS, (BASE_ROT[0], BASE_ROT[1] + 10.0, 0.0), (0.0, 4.75, 0.0))
        self.assertGreater(abs(x1 - x0), 0.15)

    def test_tangage_deplace_l_image_verticalement(self):
        _, y0, _ = self.projeter(BASE_POS, BASE_ROT, (0.0, 4.75, 0.0))
        _, y1, _ = self.projeter(BASE_POS, (BASE_ROT[0] + 5.0, BASE_ROT[1], 0.0), (0.0, 4.75, 0.0))
        self.assertGreater(abs(y1 - y0), 0.1)

    def test_position_deplace_l_image(self):
        x0, y0, _ = self.projeter(BASE_POS, BASE_ROT, (0.0, 4.75, 0.0))
        x1, y1, _ = self.projeter((0.0, 7.1, -39.8125), BASE_ROT, (0.0, 4.75, 0.0))
        self.assertGreater(abs(y1 - y0), 0.05)

    def test_roulis_fait_tourner_l_image(self):
        """Le jeu n'envoie jamais de roulis en combat (voir le test du moteur reel), mais s'il en envoyait un, la visionneuse l'appliquerait (G-073 : rien a ajouter)."""
        R0 = F.Jeu._rot_camera(None, types.SimpleNamespace(cam_rot=BASE_ROT)); R1 = F.Jeu._rot_camera(None, types.SimpleNamespace(cam_rot=(BASE_ROT[0], BASE_ROT[1], 20.0)))
        self.assertAlmostEqual(float((R0 @ [0.0, 1.0, 0.0])[0]), 0.0, places=3)
        self.assertAlmostEqual(abs(float((R1 @ [0.0, 1.0, 0.0])[0])), math.sin(math.radians(20.0)), places=3)
        x0, y0, _ = self.projeter(BASE_POS, BASE_ROT, (3.0, 4.75, 0.0)); x1, y1, _ = self.projeter(BASE_POS, (BASE_ROT[0], BASE_ROT[1], 20.0), (3.0, 4.75, 0.0))
        self.assertGreater(abs(y1 - y0), 0.03)                                                 # un point a droite du centre monte ou descend quand la camera roule

    def test_champ_de_vision_du_paquet_11(self):
        e = types.SimpleNamespace(cam_pos=BASE_POS, cam_rot=BASE_ROT, cam_fov=30.0)
        M, _ = F.Jeu._camera_combat(self.jeu(), e, 16 / 9); e2 = types.SimpleNamespace(cam_pos=BASE_POS, cam_rot=BASE_ROT, cam_fov=None); M2, _ = F.Jeu._camera_combat(self.jeu(), e2, 16 / 9)
        self.assertGreater(abs(M[1, 1] - M2[1, 1]), 0.05)


# ------------------------------------------------------------------------------------------------------------------------------ moteur reel
@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class MoteurReel(unittest.TestCase):
    MONSTRE = 7                                                      # monstre dont l'attaque de base a une camera (fichier « m007_at ») : la camera monte de ~2,35 unites puis revient

    @classmethod
    def setUpClass(cls):
        import unicorn; from dq4_pc.persistance import etats as ET
        from unicorn.arm64_const import UC_ARM64_REG_W1, UC_ARM64_REG_W2, UC_ARM64_REG_W3
        cls.ET = ET; mo = cls.mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_camcb_')); c = cls.c = mo.core
        mo.charger_sauvegarde(1)
        for _ in range(200): mo.step(0, 0)
        enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
        def forcer(u, adr, sz, ud):                                  # composition de la rencontre : un seul monstre (Encount + 0x34 / 0x44, comme test_historique_combat)
            for j in range(4):
                c.mem_w(enc + 0x34 + 4 * j, struct.pack('<I', cls.MONSTRE if j == 0 else 0)); c.mem_w(enc + 0x44 + 4 * j, struct.pack('<I', 1 if j == 0 else 0))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, forcer, None, a, a)
        cls.appels = []                                              # BattleCamera::setCameraAnimation(camA, camB, attente) : (image, camA, camB, attente)
        a = c.export('_ZN12BattleCamera18setCameraAnimationEhht')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, lambda u, ad, sz, ud: cls.appels.append((mo.images, u.reg_read(UC_ARM64_REG_W1) & 0xff, u.reg_read(UC_ARM64_REG_W2) & 0xff, u.reg_read(UC_ARM64_REG_W3) & 0xffff)), None, a, a)
        c.uc.ctl_flush_tb()
        c.call(c.export('_ZN6Global11startBattleEv'), mo._global(), label='startBattle')
        n = 0
        while mo.etat.partie != MO.PARTIE_COMBAT and n < 1500: mo.step(); n += 1
        assert mo.etat.partie == MO.PARTIE_COMBAT
        cls.cam = c.call(c.export('_ZN12BattleCamera12getSingletonEv'), label='cam')
        cls.sca = c.export('_ZN12BattleCamera18setCameraAnimationEhht'); cls.isa = c.export('_ZN12BattleCamera17isCameraAnimationEv')
        for _ in range(600):                                         # jusqu'au menu de commandes : camera au repos, rien n'a encore attaque
            mo.step(0, 0); mo.ui.degats = []
            if mo.menu_actif() is not None: break
        assert mo.menu_actif() is not None
        cls.depart = ET.instantane(mo)

    def pas(self, p=0, d=0):
        pq = self.mo.step(p, d); self.mo.ui.degats = []; return pq

    def test_1_combat_reel_l_attaque_du_monstre_bouge_la_camera(self):
        """Un vrai combat, joue comme test_vitesse_combat : l'attaque du monstre lance `setCameraAnimation(25, 0, 0)` ; la camera de la visionneuse (Etat.cam_pos) suit les paquets, monte, puis revient exactement."""
        mo = self.mo; st = {'rel': None, 'att': 0}; serie = []; debut = None
        self.ET.appliquer(mo, self.depart); e = mo.etat                                     # (appliquer remplace l'objet Etat : le relire apres)
        for i in range(3000):
            p = d = 0
            if st['rel'] is not None: mo.envoyer_menu(st['rel'], 1, -1, 0); st['rel'] = None
            port = mo.menu_actif()
            if port is not None and not mo.msg_visible:
                st['att'] += 1
                if st['att'] % 4 == 0: mo.envoyer_menu(port, 1, -1, 0x10); st['rel'] = port
            elif mo.msg_visible and (mo.ui.msg.get('feed') or mo.etat_message()[1] in (3, 5)):
                st['att'] += 1
                if st['att'] % 4 == 0: p = d = MO.A
            else: st['att'] = 0
            prec = e.partie; self.pas(p, d)
            if any(a[1] == 25 for a in self.appels) and debut is None: debut = i
            if debut is not None: serie.append((tuple(e.cam_pos), tuple(e.cam_rot)))
            if debut is not None and i - debut > 60: break
            if e.partie != MO.PARTIE_COMBAT and prec == MO.PARTIE_COMBAT: break
        self.assertIsNotNone(debut, 'le monstre n\'a pas lance d\'attaque avec camera (appels : %r)' % (self.appels[:6],))
        self.assertIn((25, 0, 0), [a[1:] for a in self.appels])
        ys = [s[0][1] for s in serie]; base_y = BASE_POS[1]
        self.assertGreater(max(ys) - base_y, 2.0, 'la camera doit monter d\'au moins 2 unites')
        self.assertAlmostEqual(ys[-1], base_y, delta=0.01)                                  # revient a son point de depart
        for s in serie:
            self.assertAlmostEqual(s[0][0], BASE_POS[0], delta=1e-3); self.assertAlmostEqual(s[0][2], BASE_POS[2], delta=1e-3)       # seule la hauteur change
            self.assertEqual(s[1], BASE_ROT)                                                                                              # l'angle ne change pas pour cette attaque
        self.assertGreater(len(set(ys)), 15, 'un mouvement continu, image par image (un paquet 10 par image)')

    def injecter(self, cam_a, cam_b, attente, maxi=700):
        """Remet le combat au repos (menu de commandes), lance la camera (comme BattleMonster::startAnimation) et suit Etat.cam_pos / cam_rot jusqu'a la fin de l'animation."""
        ET, mo, c = self.ET, self.mo, self.c
        ET.appliquer(mo, self.depart); e = mo.etat                                           # (appliquer remplace l'objet Etat : le relire apres)
        for _ in range(3): self.pas()
        c.call(self.sca, self.cam, 0, 0, 0, label='sca0')
        for _ in range(4): self.pas()
        base = (tuple(e.cam_pos), tuple(e.cam_rot)); serie = []
        c.call(self.sca, self.cam, cam_a, cam_b, attente, label='sca')
        for j in range(maxi):
            self.pas(); serie.append((tuple(e.cam_pos), tuple(e.cam_rot)))
            if not (c.call(self.isa, self.cam, label='isanim') & 1) and j > 3: break
        return base, serie

    def ecarts(self, base, serie):
        dp = [max(abs(s[0][k] - base[0][k]) for s in serie) for k in range(3)]; da = [max(abs(s[1][k] - base[1][k]) for s in serie) for k in range(3)]
        return dp, da

    def verifier_retour(self, base, serie):
        for k in range(3):
            self.assertAlmostEqual(serie[-1][0][k], base[0][k], delta=0.01); self.assertAlmostEqual(serie[-1][1][k], base[1][k], delta=0.01)       # revient a son point de depart
        self.assertTrue(all(s[1][2] == 0.0 for s in serie), 'roulis envoye par le jeu : toujours 0 (G-073)')

    def test_2_secousse_verticale(self):
        """Camera 158 « tateyure1 » (secousse de tangage, la plus courante) : ~1 degre de tangage, ni position ni lacet, ~13 images."""
        base, serie = self.injecter(0, 158, 30); dp, da = self.ecarts(base, serie)
        self.assertGreater(da[0], 0.8); self.assertLess(da[0], 1.5); self.assertLess(max(dp), 0.01); self.assertLess(da[1], 0.01); self.assertTrue(20 <= len(serie) <= 40, len(serie)); self.verifier_retour(base, serie)

    def test_3_attaque_a_tangage_marque(self):
        """Camera 21 « m000_at » (attaque de gluant, variante 1) : tangage de ~6,5 degres, rien d'autre."""
        base, serie = self.injecter(21, 0, 0); dp, da = self.ecarts(base, serie)
        self.assertGreater(da[0], 6.0); self.assertLess(da[0], 7.0); self.assertLess(max(dp), 0.01); self.verifier_retour(base, serie)

    def test_4_grand_mouvement_de_boss(self):
        """Camera 127 « m255_tai » (formes speciales d'indice >= 250) : la camera glisse de ~14,6 unites en x et z et tourne de ~19 degres en lacet, pendant ~230 images (7 s), puis revient."""
        base, serie = self.injecter(127, 0, 0, maxi=800); dp, da = self.ecarts(base, serie)
        self.assertGreater(dp[0], 14.0); self.assertGreater(dp[2], 14.0); self.assertGreater(da[1], 18.0); self.assertGreater(len(serie), 200); self.verifier_retour(base, serie)

    def test_5_sort_final_plongee(self):
        """Camera 140 « madante_evi » : la camera monte de ~31,6 unites en hauteur et plonge de ~54 degres, ~180 images, puis revient."""
        base, serie = self.injecter(140, 0, 0, maxi=800); dp, da = self.ecarts(base, serie)
        self.assertGreater(dp[1], 30.0); self.assertGreater(da[0], 50.0); self.assertGreater(len(serie), 150); self.verifier_retour(base, serie)

    def test_6_la_visionneuse_projette_la_camera_envoyee(self):
        """Au sommet du mouvement du boss (127), la matrice de la visionneuse n'est plus celle du repos : un point du decor se projette ailleurs."""
        base, serie = self.injecter(127, 0, 0, maxi=800)
        pic = max(serie, key=lambda s: abs(s[1][1] - base[1][1]))
        jeu = types.SimpleNamespace(cb_mx=False, _rot_camera=lambda e: F.Jeu._rot_camera(None, e)); pt = np.array([0.0, 4.75, 0.0, 1.0])
        proj = lambda pos, rot: (lambda v: v[:2] / v[3])(F.Jeu._camera_combat(jeu, types.SimpleNamespace(cam_pos=pos, cam_rot=rot, cam_fov=None), 16 / 9)[0] @ pt)
        self.assertGreater(float(np.abs(proj(*pic) - proj(*base)).max()), 0.1)


if __name__ == '__main__':
    unittest.main()
