"""La camera des villes avec le VRAI moteur (D-234) : la rotation du joueur est celle du jeu, pas une rotation de la visionneuse a cote de lui.

Sur le terrain d'une ville, les bits 4 et 5 des touches tenues envoyees a GameUpdate ne sont pas A et B mais les boutons de camera du jeu (window::NormalControl::checkCamera : 1 = tourne a gauche, 2 = a droite, 3 = retour au nord) ;
TownPlayerManager::setCameraRot tourne la camera d'un cran (0x200 sur 65536 par tour : 2,8125 degres) par pas du moteur, borne selon les limites du lieu, tient le joueur pendant le retour au nord, et le jeu tourne lui-meme
les directions de marche et les rangees des sprites selon sa camera. On le verifie sur le jeu d'origine (carte `mak1f1`, sauvegarde 1, joueur libre ; avec un message ouvert les memes bits sont A et B, d'ou l'envoi des boutons de camera sur le terrain libre seulement, voir test_entries.py) :

  1. un bouton de camera tenu fait tourner la camera de 2,8125 degres par pas (a droite : le cap avance vers +X), l'autre en sens inverse ; le jeu garde le bouton en attente apres le pas (`Engine.camera_wait`) ;
  2. `Engine.camera_turn(direction, n)` : exactement n crans de plus (reglage « Vitesse de camera », glissement du clic molette), meme apres un pas qui a pris le bouton ;
  3. les deux boutons ensemble, un seul pas : le jeu ramene la camera au nord (cap 0) et tient le joueur pendant ce temps (Global.Flag 4), puis le rend ;
  4. camera tournee, la marche vers le haut va dans le sens de la camera (le jeu tourne les directions : la visionneuse n'a rien a faire) et le sprite du heros garde la meme rangee ;

Sans DQ_APK et DQ_SAVES (dossier des APK patches et dossier des sauvegardes), les tests du vrai moteur sont ignores.

    DQ_APK=... DQ_SAVES=... python3 tests/test_engine_camera.py
"""
import math, os, shutil, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.core import engine as ENGINE


def spacing(a, b): return (a - b + 180.0) % 360.0 - 180.0


class GameConstants(unittest.TestCase):
    def test_buttons_and_notch(self):
        self.assertEqual((ENGINE.CAM_G, ENGINE.CAM_D), (0x10, 0x20)); self.assertEqual((ENGINE.ROT_CAM_RIGHT, ENGINE.ROT_CAM_LEFT, ENGINE.ROT_CAM_NORD), (1, 2, 3))
        self.assertAlmostEqual(ENGINE.CAM_STEP, 2.8125)


@unittest.skipUnless(os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES'), 'DQ_APK et DQ_SAVES requis (vrai moteur)')
class TestRealEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.mkdtemp(prefix='sv_test_camera_')
        cls.m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], cls.folder)
        for _ in range(3): cls.m.step(0, 0)
        cls.m.load_save(1)
        cls.free_state()

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.folder, ignore_errors=True)

    @classmethod
    def free_state(cls):
        """Ferme le message d'arrivee (touche A) et laisse le joueur libre : aucun message, joueur non verrouille."""
        m = cls.m
        for i in range(900):
            if m.msg_visible and i % 12 < 3: m.step(ENGINE.A, ENGINE.A)
            else: m.step(0, 0)
            if i > 150 and not m.msg_visible and not m.flags() & ENGINE.PLAYER_LOCKED_FLAG: break
        for _ in range(20): m.step(0, 0)

    def setUp(self):
        m = self.m
        self.assertEqual(m.state.game_map, 'mak1f1'); self.assertFalse(m.msg_visible); self.assertFalse(m.flags() & ENGINE.PLAYER_LOCKED_FLAG)
        self.return_to_north()

    def cap(self):
        e = self.m.state; return math.degrees(math.atan2(e.cam_target[0] - e.cam_pos[0], e.cam_target[2] - e.cam_pos[2]))

    def step(self, n, held=0, decl=0):
        for _ in range(n): self.m.step(held, decl)

    def return_to_north(self):
        if abs(spacing(self.cap(), 0.0)) > 0.01:
            self.m.step(ENGINE.CAM_G | ENGINE.CAM_D, 0); self.step(40)
        self.assertLess(abs(spacing(self.cap(), 0.0)), 0.01)

    def test_a_button_turns_the_camera_one_notch_per_step(self):
        m = self.m; caps = [self.cap()]
        for _ in range(30): m.step(ENGINE.CAM_D, 0); caps.append(self.cap())
        d = [spacing(b, a) for a, b in zip(caps, caps[1:])]
        self.assertEqual(d[0], 0.0)                                                                  # (le jeu tourne au pas suivant celui du bouton)
        for v in d[1:]: self.assertAlmostEqual(v, ENGINE.CAM_STEP, delta=0.05)                            # a droite : le cap avance vers +X
        self.step(3); after = self.cap(); self.step(5); self.assertAlmostEqual(self.cap(), after, places=6)          # bouton relache : la camera s'arrete
        caps = [self.cap()]
        for _ in range(10): m.step(ENGINE.CAM_G, 0); caps.append(self.cap())
        for a, b in list(zip(caps, caps[1:]))[1:]: self.assertAlmostEqual(spacing(b, a), -ENGINE.CAM_STEP, delta=0.05)

    def test_game_keeps_button_pending(self):
        m = self.m
        m.step(ENGINE.CAM_D, 0); self.assertEqual(m.camera_wait(), ENGINE.ROT_CAM_RIGHT)
        m.step(0, 0); self.assertEqual(m.camera_wait(), 0)
        m.step(ENGINE.CAM_G, 0); self.assertEqual(m.camera_wait(), ENGINE.ROT_CAM_LEFT)
        self.step(3)

    def test_n_more_notches(self):
        m = self.m
        for n in (2, 3, 4):
            before = self.cap(); m.step(ENGINE.CAM_D, 0); self.assertEqual(m.camera_wait(), ENGINE.ROT_CAM_RIGHT); m.camera_turn(ENGINE.ROT_CAM_RIGHT, n); self.step(2)
            self.assertAlmostEqual(spacing(self.cap(), before), n * ENGINE.CAM_STEP, delta=0.05, msg=n)       # n crans exactement (le cran du bouton est l'un d'eux)
        before = self.cap(); m.step(ENGINE.CAM_G, 0); m.camera_turn(ENGINE.ROT_CAM_LEFT, 3); self.step(2); self.assertAlmostEqual(spacing(self.cap(), before), -3 * ENGINE.CAM_STEP, delta=0.05)
        before = self.cap(); m.camera_turn(ENGINE.ROT_CAM_RIGHT, 2); self.step(2); self.assertAlmostEqual(spacing(self.cap(), before), 2 * ENGINE.CAM_STEP, delta=0.05)          # (sans pas avant : aussi)

    def test_speed_x2_and_x4_in_continuous_walking(self):
        m = self.m
        for n in (2, 4):
            caps = [self.cap()]
            for _ in range(10):
                m.step(ENGINE.CAM_D, 0); m.camera_turn(ENGINE.ROT_CAM_RIGHT, n); caps.append(self.cap())
            for a, b in list(zip(caps, caps[1:]))[2:]: self.assertAlmostEqual(spacing(b, a), n * ENGINE.CAM_STEP, delta=0.06, msg=n)
            self.return_to_north()

    def test_two_buttons_return_to_north_and_hold_player(self):
        m = self.m
        for _ in range(20): m.step(ENGINE.CAM_D, 0)
        self.step(3); self.assertGreater(abs(spacing(self.cap(), 0.0)), 40.0)
        m.step(ENGINE.CAM_G | ENGINE.CAM_D, 0)                                                              # UN seul pas suffit : le jeu fait le reste
        verrous = []; caps = []
        for _ in range(40): m.step(0, 0); verrous.append(bool(m.flags() & ENGINE.PLAYER_LOCKED_FLAG)); caps.append(abs(spacing(self.cap(), 0.0)))
        self.assertTrue(all(verrous[:8])); self.assertFalse(verrous[-1])                            # le joueur est tenu pendant le retour, puis rendu
        self.assertAlmostEqual(caps[-1], 0.0, places=6); self.assertTrue(all(b <= a + 1e-9 for a, b in zip(caps, caps[1:])))          # retour sans a-coup, par le chemin le plus court, qui s'arrete au nord
        self.assertEqual(m.camera_wait(), 0)

    def test_walk_relative_to_camera_and_same_sprite_row(self):
        """Camera tournee d'un quart de tour : « haut » fait marcher le heros vers le fond de l'ecran (dans le sens de la camera), et le sprite montre toujours la meme rangee : c'est le jeu qui s'en charge."""
        m = self.m
        for _ in range(32): m.step(ENGINE.CAM_D, 0)
        self.step(6); cap = self.cap(); self.assertGreater(abs(spacing(cap, 0.0)), 80.0)
        pos = lambda: tuple(float(x) for x in m.state.sprites[0]['pos'])
        p0 = pos(); self.step(18, ENGINE.UP, ENGINE.UP); p1 = pos()
        dx, dz = p1[0] - p0[0], p1[2] - p0[2]
        self.assertGreater(math.hypot(dx, dz), 1.0, 'le heros a marche')
        self.assertLess(abs(spacing(math.degrees(math.atan2(dx, dz)), cap)), 12.0)                    # vers le fond de l'ecran
        row = m.state.sprites[0]['dir']; self.step(10)
        self.step(12, ENGINE.UP, ENGINE.UP); self.assertEqual(m.state.sprites[0]['dir'], row)
        self.step(10)


if __name__ == '__main__':
    unittest.main(verbosity=1)
