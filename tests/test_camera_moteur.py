"""La camera des villes avec le VRAI moteur (D-234) : la rotation du joueur est celle du jeu, pas une rotation de la visionneuse a cote de lui.

Sur le terrain d'une ville, les bits 4 et 5 des touches tenues envoyees a GameUpdate ne sont pas A et B mais les boutons de camera du jeu (window::NormalControl::checkCamera : 1 = tourne a gauche, 2 = a droite, 3 = retour au nord) ;
TownPlayerManager::setCameraRot tourne la camera d'un cran (0x200 sur 65536 par tour : 2,8125 degres) par pas du moteur, borne selon les limites du lieu, tient le joueur pendant le retour au nord, et le jeu tourne lui-meme
les directions de marche et les rangees des sprites selon sa camera. On le verifie sur le jeu d'origine (carte `mak1f1`, sauvegarde 1, joueur libre ; avec un message ouvert les memes bits sont A et B, d'ou l'envoi des boutons de camera sur le terrain libre seulement, voir test_entrees.py) :

  1. un bouton de camera tenu fait tourner la camera de 2,8125 degres par pas (a droite : le cap avance vers +X), l'autre en sens inverse ; le jeu garde le bouton en attente apres le pas (`Moteur.camera_attente`) ;
  2. `Moteur.camera_tourner(sens, n)` : exactement n crans de plus (reglage « Vitesse de camera », glissement du clic molette), meme apres un pas qui a pris le bouton ;
  3. les deux boutons ensemble, un seul pas : le jeu ramene la camera au nord (cap 0) et tient le joueur pendant ce temps (Global.Flag 4), puis le rend ;
  4. camera tournee, la marche vers le haut va dans le sens de la camera (le jeu tourne les directions : la visionneuse n'a rien a faire) et le sprite du heros garde la meme rangee ;

Sans DQ_APK et DQ_SAVES (dossier des APK patches et dossier des sauvegardes), les tests du vrai moteur sont ignores.

    DQ_APK=... DQ_SAVES=... python3 tests/test_camera_moteur.py
"""
import math, os, shutil, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import moteur as MO


def ecart(a, b): return (a - b + 180.0) % 360.0 - 180.0


class ConstantesDuJeu(unittest.TestCase):
    def test_boutons_et_cran(self):
        self.assertEqual((MO.CAM_G, MO.CAM_D), (0x10, 0x20)); self.assertEqual((MO.ROT_CAM_DROITE, MO.ROT_CAM_GAUCHE, MO.ROT_CAM_NORD), (1, 2, 3))
        self.assertAlmostEqual(MO.CAM_PAS, 2.8125)


@unittest.skipUnless(os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES'), 'DQ_APK et DQ_SAVES requis (vrai moteur)')
class TestVraiMoteur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = tempfile.mkdtemp(prefix='sv_test_camera_')
        cls.m = MO.Moteur(os.environ['DQ_APK'], os.environ['DQ_SAVES'], cls.dossier)
        for _ in range(3): cls.m.step(0, 0)
        cls.m.charger_sauvegarde(1)
        cls.etat_libre()

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.dossier, ignore_errors=True)

    @classmethod
    def etat_libre(cls):
        """Ferme le message d'arrivee (touche A) et laisse le joueur libre : aucun message, joueur non verrouille."""
        m = cls.m
        for i in range(900):
            if m.msg_visible and i % 12 < 3: m.step(MO.A, MO.A)
            else: m.step(0, 0)
            if i > 150 and not m.msg_visible and not m.drapeaux() & MO.DRAPEAU_JOUEUR_VERROUILLE: break
        for _ in range(20): m.step(0, 0)

    def setUp(self):
        m = self.m
        self.assertEqual(m.etat.carte, 'mak1f1'); self.assertFalse(m.msg_visible); self.assertFalse(m.drapeaux() & MO.DRAPEAU_JOUEUR_VERROUILLE)
        self.revenir_au_nord()

    def cap(self):
        e = self.m.etat; return math.degrees(math.atan2(e.cam_cible[0] - e.cam_pos[0], e.cam_cible[2] - e.cam_pos[2]))

    def pas(self, n, tenu=0, decl=0):
        for _ in range(n): self.m.step(tenu, decl)

    def revenir_au_nord(self):
        if abs(ecart(self.cap(), 0.0)) > 0.01:
            self.m.step(MO.CAM_G | MO.CAM_D, 0); self.pas(40)
        self.assertLess(abs(ecart(self.cap(), 0.0)), 0.01)

    def test_un_bouton_tourne_la_camera_d_un_cran_par_pas(self):
        m = self.m; caps = [self.cap()]
        for _ in range(30): m.step(MO.CAM_D, 0); caps.append(self.cap())
        d = [ecart(b, a) for a, b in zip(caps, caps[1:])]
        self.assertEqual(d[0], 0.0)                                                                  # (le jeu tourne au pas suivant celui du bouton)
        for v in d[1:]: self.assertAlmostEqual(v, MO.CAM_PAS, delta=0.05)                            # a droite : le cap avance vers +X
        self.pas(3); apres = self.cap(); self.pas(5); self.assertAlmostEqual(self.cap(), apres, places=6)          # bouton relache : la camera s'arrete
        caps = [self.cap()]
        for _ in range(10): m.step(MO.CAM_G, 0); caps.append(self.cap())
        for a, b in list(zip(caps, caps[1:]))[1:]: self.assertAlmostEqual(ecart(b, a), -MO.CAM_PAS, delta=0.05)

    def test_le_jeu_garde_le_bouton_en_attente(self):
        m = self.m
        m.step(MO.CAM_D, 0); self.assertEqual(m.camera_attente(), MO.ROT_CAM_DROITE)
        m.step(0, 0); self.assertEqual(m.camera_attente(), 0)
        m.step(MO.CAM_G, 0); self.assertEqual(m.camera_attente(), MO.ROT_CAM_GAUCHE)
        self.pas(3)

    def test_n_crans_de_plus(self):
        m = self.m
        for n in (2, 3, 4):
            avant = self.cap(); m.step(MO.CAM_D, 0); self.assertEqual(m.camera_attente(), MO.ROT_CAM_DROITE); m.camera_tourner(MO.ROT_CAM_DROITE, n); self.pas(2)
            self.assertAlmostEqual(ecart(self.cap(), avant), n * MO.CAM_PAS, delta=0.05, msg=n)       # n crans exactement (le cran du bouton est l'un d'eux)
        avant = self.cap(); m.step(MO.CAM_G, 0); m.camera_tourner(MO.ROT_CAM_GAUCHE, 3); self.pas(2); self.assertAlmostEqual(ecart(self.cap(), avant), -3 * MO.CAM_PAS, delta=0.05)
        avant = self.cap(); m.camera_tourner(MO.ROT_CAM_DROITE, 2); self.pas(2); self.assertAlmostEqual(ecart(self.cap(), avant), 2 * MO.CAM_PAS, delta=0.05)          # (sans pas avant : aussi)

    def test_vitesse_x2_et_x4_en_marche_continue(self):
        m = self.m
        for n in (2, 4):
            caps = [self.cap()]
            for _ in range(10):
                m.step(MO.CAM_D, 0); m.camera_tourner(MO.ROT_CAM_DROITE, n); caps.append(self.cap())
            for a, b in list(zip(caps, caps[1:]))[2:]: self.assertAlmostEqual(ecart(b, a), n * MO.CAM_PAS, delta=0.06, msg=n)
            self.revenir_au_nord()

    def test_les_deux_boutons_ramenent_au_nord_et_tiennent_le_joueur(self):
        m = self.m
        for _ in range(20): m.step(MO.CAM_D, 0)
        self.pas(3); self.assertGreater(abs(ecart(self.cap(), 0.0)), 40.0)
        m.step(MO.CAM_G | MO.CAM_D, 0)                                                              # UN seul pas suffit : le jeu fait le reste
        verrous = []; caps = []
        for _ in range(40): m.step(0, 0); verrous.append(bool(m.drapeaux() & MO.DRAPEAU_JOUEUR_VERROUILLE)); caps.append(abs(ecart(self.cap(), 0.0)))
        self.assertTrue(all(verrous[:8])); self.assertFalse(verrous[-1])                            # le joueur est tenu pendant le retour, puis rendu
        self.assertAlmostEqual(caps[-1], 0.0, places=6); self.assertTrue(all(b <= a + 1e-9 for a, b in zip(caps, caps[1:])))          # retour sans a-coup, par le chemin le plus court, qui s'arrete au nord
        self.assertEqual(m.camera_attente(), 0)

    def test_marche_relative_a_la_camera_et_meme_rangee_du_sprite(self):
        """Camera tournee d'un quart de tour : « haut » fait marcher le heros vers le fond de l'ecran (dans le sens de la camera), et le sprite montre toujours la meme rangee : c'est le jeu qui s'en charge."""
        m = self.m
        for _ in range(32): m.step(MO.CAM_D, 0)
        self.pas(6); cap = self.cap(); self.assertGreater(abs(ecart(cap, 0.0)), 80.0)
        pos = lambda: tuple(float(x) for x in m.etat.sprites[0]['pos'])
        p0 = pos(); self.pas(18, MO.HAUT, MO.HAUT); p1 = pos()
        dx, dz = p1[0] - p0[0], p1[2] - p0[2]
        self.assertGreater(math.hypot(dx, dz), 1.0, 'le heros a marche')
        self.assertLess(abs(ecart(math.degrees(math.atan2(dx, dz)), cap)), 12.0)                    # vers le fond de l'ecran
        rangee = m.etat.sprites[0]['dir']; self.pas(10)
        self.pas(12, MO.HAUT, MO.HAUT); self.assertEqual(m.etat.sprites[0]['dir'], rangee)
        self.pas(10)


if __name__ == '__main__':
    unittest.main(verbosity=1)
