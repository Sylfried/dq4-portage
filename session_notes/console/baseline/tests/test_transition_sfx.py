"""Test du bruitage de transition de carte (porte, sortie / entree de village, escalier, carte du monde <-> ville) avec la « Vitesse de transition » de la visionneuse.

Cause (retours de 22 h 29 : « il n'y a toujours pas les bruitages de transition de map ») : le bruitage 305 de la transition n'est pas lance par Unity ni par la porte (celle-ci joue le 309 a l'ouverture) mais par
Global::NativeExec, 15 images apres que startTown / startField ont lance le fondu au noir de 30 images (decompte de l'octet LIB + 0x258254) ; il n'est joue que si l'ancienne scene vit encore. Le chargement de la carte suivante
arrive a la fin du fondu : dans le jeu d'origine, le bruitage est demande a mi-fondu. Avec un fondu raccourci (x3 : 10 images, x4 : 8 images ; marginal a x2 : 15 images), l'ancienne scene etait detruite avant les 15 images
et le moteur ne demandait plus rien. Engine._exit_countdown remet le decompte a la meme proportion que le fondu ; la duree des fondus ne change pas.

  1. calcul pur : proportion du fondu memorisee par State._fondu, ajustement du decompte (faux coeur) ;
  2. moteur d'origine (DQ_APK + DQ_SAVES, sauvegarde 1 : Ragnar a Strattbourg) : la porte de l'eglise et la sortie du village vers la carte du monde, dans les deux sens, a chaque « Vitesse de transition » (x1 a x4) : un seul bruitage 305, demande entre le debut du fondu et
     le chargement de la carte, apres le 309 de la porte ; fondu de la duree reglee ;
  3. visionneuse (Son, faux lecteurs) : les deux bruitages restent joues jusqu'a leur fin quand le chargement de la carte bloque la boucle (voir test_sound_mixing).

    DQ_APK=... DQ_SAVES=... python3 tools/test_transition_sfx.py
"""
import os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
SPEEDS = (1.0, 1.5, 2.0, 3.0, 4.0)       # « Vitesse de transition » : 1.0 = comme le jeu ; 4.0 = le maximum du menu
GAME_FADE = 30                              # images du fondu au noir de startTown / startField (UnitySetFade(0x101e))


class FakeCountdownCore:
    """Memoire du moteur reduite a l'octet du decompte."""
    def __init__(self): self.byte = 0; self.written_items = []
    def mem(self, addr, n): return bytes([self.byte])
    def mem_w(self, addr, data): self.byte = data[0]; self.written_items.append(data[0])


def dummy_engine():
    from dq4_pc.core import engine as ENGINE
    m = ENGINE.Engine.__new__(ENGINE.Engine)
    m.core = FakeCountdownCore(); m.L = 0; m.state = ENGINE.State(); m.frames = 0; m._countdown = 0; m._countdown_armed = -99; m._countdown_done = True
    return m


class Calc(unittest.TestCase):
    def setUp(self):
        from dq4_pc.core import engine as ENGINE
        self.ENGINE = ENGINE; self.speed = ENGINE.State.fade_speed

    def tearDown(self): self.ENGINE.State.fade_speed = self.speed

    def fade(self, v, part=None, image=7):
        e = self.ENGINE.State(); e.image = image
        if part is not None: e.part = part
        e.apply([(9, [v], [])], lambda: 'x')
        return e

    def test_proportion_remembered_per_state(self):
        from dq4_pc.core import game_priority as PJ
        for vf in SPEEDS:
            self.ENGINE.State.fade_speed = vf
            e = self.fade(0x1000 | GAME_FADE)
            self.assertEqual(e.fade_ratio[0], 7)
            self.assertAlmostEqual(e.fade_ratio[1], PJ.fade_duration(GAME_FADE, vf) / GAME_FADE, 6, 'x%s' % vf)
        self.ENGINE.State.fade_speed = 1.0
        self.assertEqual(self.fade(0x1000 | GAME_FADE).fade_ratio[1], 1.0, 'x1 : duree du jeu')

    def test_shortened_battle_like_others_entry_without_countdown(self):
        from dq4_pc.core import game_priority as PJ
        self.ENGINE.State.fade_speed = 4.0
        self.assertAlmostEqual(self.fade(0x1000 | GAME_FADE, part=self.ENGINE.PART_BATTLE).fade_ratio[1], PJ.fade_duration(GAME_FADE, 4.0) / GAME_FADE, 6, 'fondu d\'un combat : suit « Vitesse de transition » (#47)')
        self.assertEqual(self.fade(GAME_FADE).fade_ratio[1], 1.0, 'fondu d\'entree (vers la scene) : pas de decompte a ajuster')

    def arm(self, m, byte, ratio, fade_frame=None):
        """Un pas ou le moteur arme le decompte (15, deja decremente une fois : 14) et ou le fondu de cette sortie arrive."""
        m.state.fade_ratio = (m.frames if fade_frame is None else fade_frame, ratio)
        m.core.byte = byte; m._exit_countdown()

    def test_countdown_reset_to_fade_proportion(self):
        for r, expected in ((1.0, 14), (0.5, 7), (10 / 30, 5), (8 / 30, 4)):
            m = dummy_engine(); self.arm(m, 14, r)
            self.assertEqual(m.core.byte, expected, 'rapport %.2f' % r)
            m.frames += 1; m._exit_countdown(); self.assertEqual(m.core.byte, expected, 'une seule fois')
        m = dummy_engine(); self.arm(m, 1, 0.1); self.assertEqual(m.core.byte, 1, 'jamais 0 : le bruitage est demande a l\'image suivante, pas annule')

    def test_ratio_one_changes_nothing(self):
        m = dummy_engine(); self.arm(m, 14, 1.0); self.assertEqual(m.core.written_items, [], 'aucune ecriture dans le moteur')

    def test_fade_arrives_one_frame_after_arming(self):
        m = dummy_engine(); m.core.byte = 14; m._exit_countdown(); self.assertEqual(m.core.byte, 14, 'pas de fondu connu : rien')
        m.frames += 1; m.core.byte = 13; m.state.fade_ratio = (m.frames, 0.5); m._exit_countdown()
        self.assertEqual(m.core.byte, 6, 'le fondu de la sortie est arrive juste apres : decompte restant (13) remis a la proportion (13 x 0,5 arrondi)')

    def test_fade_unrelated_to_countdown(self):
        m = dummy_engine(); m.state.fade_ratio = (-50, 0.25); m.core.byte = 14; m._exit_countdown()
        self.assertEqual(m.core.byte, 14, 'un fondu ancien n\'est pas celui de cette sortie')
        m.frames += 3; m.state.fade_ratio = (m.frames, 0.25); m._exit_countdown()
        self.assertEqual(m.core.byte, 14, 'passe 2 images, plus d\'ajustement')


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class RealEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dq4_pc.core import engine as ENGINE; from dq4_pc.persistence import savestates as SS
        cls.ENGINE, cls.SS = ENGINE, SS
        cls.eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_bruit_trans_'))
        cls.eng.load_save(1)
        for _ in range(250): cls.eng.step(0, 0)
        n = 0
        while (cls.eng.msg_visible or cls.eng.active_menu() is not None) and n < 1500:           # message d'accueil de la sauvegarde : A jusqu'a sa fermeture
            n += 1; cls.eng.step(ENGINE.A, ENGINE.A) if n % 6 == 0 else cls.eng.step(0, 0)
        for _ in range(40): cls.eng.step(0, 0)
        cls.initial = SS.snapshot(cls.eng)
        cls.speed = ENGINE.State.fade_speed

    @classmethod
    def tearDownClass(cls): cls.ENGINE.State.fade_speed = cls.speed

    def trajet(self, direction):
        """Marche dans `direction` jusqu'a la porte (ou la sortie du village) puis laisse la carte suivante se charger. -> [(image, genre, valeur)] : SE (paquet 35), FONDU (duree, paquet 9 vers le noir), CHARGE (premier paquet 0 ou 27 :
        decor de ville ou carte du monde), N (images du fondu apres son 1er pas : duree reglee - 1)."""
        eng, e = self.eng, self.eng.state; after = None; log = []; do_load = False
        for i in range(1500):
            pkt = eng.step(direction if after is None else 0, direction if i == 0 else 0)
            for t, a, f in pkt:
                if t == 35: log.append((eng.frames, 'SE', a[0]))
                elif t == 9 and a[0] & 0x1000: log.append((eng.frames, 'FONDU', a[0] & 0x7ff)); log.append((eng.frames, 'N', e.fade['n']))
                elif t in (0, 27) and not do_load: log.append((eng.frames, 'CHARGE', t)); do_load = True
            if do_load and after is None: after = 0
            if after is not None:
                after += 1
                if after > 30: return log
        self.fail('la transition n\'a pas eu lieu : %r' % (log,))

    def reset(self, vf):
        self.SS.apply(self.eng, self.initial); self.ENGINE.State.fade_speed = vf
        self.eng._countdown = 0; self.eng._countdown_armed = -99; self.eng._countdown_done = True

    def check(self, log, vf, name_str):
        from dq4_pc.core import game_priority as PJ
        im = {g: [x[0] for x in log if x[1] == g] for g in ('FONDU', 'CHARGE')}
        sfxs = [(x[0], x[2]) for x in log if x[1] == 'SE']
        self.assertEqual(len(im['FONDU']), 1, name_str); self.assertEqual(len(im['CHARGE']), 1, name_str)
        fade, do_load = im['FONDU'][0], im['CHARGE'][0]
        n = next(x[2] for x in log if x[1] == 'N')
        self.assertEqual(n + 1, PJ.fade_duration(GAME_FADE, vf), '%s : le fondu garde la duree reglee (x%s)' % (name_str, vf))
        outputs = [i for i, v in sfxs if v == 305]
        self.assertEqual(len(outputs), 1, '%s (x%s) : un bruitage de transition 305 demande : %r' % (name_str, vf, log))
        self.assertTrue(fade <= outputs[0] < do_load, '%s (x%s) : demande entre le debut du fondu (%d) et le chargement (%d), pas apres : %d' % (name_str, vf, fade, do_load, outputs[0]))
        return sfxs

    def test_church_door_in_both_directions(self):
        for vf in SPEEDS:
            self.reset(vf)
            go_to = self.trajet(self.ENGINE.DOWN)
            sfxs = self.check(go_to, vf, 'eglise > village')
            self.assertEqual([v for _, v in sfxs], [309, 305], 'x%s : la porte (309) puis la transition (305)' % vf)
            for _ in range(80): self.eng.step(0, 0)
            back = self.trajet(self.ENGINE.UP)
            self.check(back, vf, 'village > eglise')
            self.assertEqual(self.eng.state.game_map, 'mak1f1')

    def test_exit_village_to_world_map_and_back(self):
        """Le village (`maout`) s'ouvre sur la carte du monde a droite : sortie (startField, TownSystem::playTownExitSE) puis retour (startTown, FieldSystem::playFieldExitSE), memes bruitages 305."""
        for vf in SPEEDS:
            self.reset(vf)
            self.trajet(self.ENGINE.DOWN)
            for _ in range(80): self.eng.step(0, 0)
            self.check(self.trajet(self.ENGINE.RIGHT), vf, 'village > carte du monde')
            self.assertEqual(self.eng.state.part, self.ENGINE.PART_FIELD)
            for _ in range(120): self.eng.step(self.ENGINE.RIGHT, 0)               # (quelques pas sur la carte du monde, l'entree du village est a gauche)
            for _ in range(40): self.eng.step(0, 0)
            self.check(self.trajet(self.ENGINE.LEFT), vf, 'carte du monde > village')
            self.assertEqual(self.eng.state.part, self.ENGINE.PART_TOWN)

    def test_x1_like_the_game(self):
        """Sans fondu raccourci, rien ne change : le bruitage 305 est demande 14 images apres le fondu, comme avant."""
        self.reset(1.0)
        log = self.trajet(self.ENGINE.DOWN)
        fade = next(x[0] for x in log if x[1] == 'FONDU'); sfx = next(x[0] for x in log if x[1:] == ('SE', 305))
        self.assertEqual(sfx - fade, 14)


if __name__ == '__main__':
    unittest.main(verbosity=2)
