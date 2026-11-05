"""Tests des rencontres aleatoires a marche acceleree (#45) : (1 + a) / 2 rencontres par seconde reelle, pas a.

    python3 tools/test_encounters.py
    DQ_APK=... DQ_SAVES=... python3 tools/test_encounters.py      (ajoute les tests du vrai moteur : le crochet sur CountDown::exec)

La simulation statistique (marche reelle sur la carte du monde et dans un donjon, nombre de rencontres par pas a x1 / x2 / x4) est dans tools/simulate_encounters.py.
"""
import os, sys, struct, shutil, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.core import encounters as RE


class TestFormulas(unittest.TestCase):
    def test_x1_and_below_nothing_changes(self):
        for a in (0.25, 0.5, 1.0): self.assertEqual(RE.factor_per_step(a), 1.0)
        for a in (0.25, 0.5, 1.0): self.assertEqual(RE.encounters_per_second(a), a if a < 1 else 1.0 * a)

    def test_one_plus_a_over_two(self):
        for a in (2.0, 3.0, 4.0, 6.0, 8.0):
            self.assertAlmostEqual(RE.factor_per_step(a), (1.0 + a) / (2.0 * a))
            self.assertAlmostEqual(RE.encounters_per_second(a), (1.0 + a) / 2.0)          # x2 : 1,5 ; x3 : 2 ; x4 : 2,5
        self.assertAlmostEqual(RE.encounters_per_second(2.0), 1.5); self.assertAlmostEqual(RE.encounters_per_second(3.0), 2.0); self.assertAlmostEqual(RE.encounters_per_second(4.0), 2.5)

    def test_fewer_encounters_per_step_but_always_more_per_second(self):
        prev_a = 1.0
        for a in (1.5, 2.0, 3.0, 4.0, 8.0):
            self.assertLess(RE.factor_per_step(a), RE.factor_per_step(prev_a))                  # chaque pas compte moins ...
            self.assertGreater(RE.factor_per_step(a), 0.5)                                      # ... sans jamais descendre sous 1 / 2
            self.assertGreater(RE.encounters_per_second(a), RE.encounters_per_second(prev_a)) # ... et la vitesse augmente toujours la frequence par seconde
            prev_a = a

    def test_reducer_with_factor_one_is_transparent(self):
        r = RE.Reducer(1.0)
        for p in (0, 1, 846, 100000, -5): self.assertEqual(r.retain(p), p)

    def test_reducer_exact_total_with_fractions(self):
        for a in (2.0, 3.0, 4.0):
            r = RE.Reducer(RE.factor_per_step(a)); tot = 0; game = 0
            for i in range(1000):
                p = 846 + (i % 7) * 13; game += p; tot += r.retain(p)
            self.assertLessEqual(abs(tot - game * RE.factor_per_step(a)), 1.0)                  # a une unite pres
            self.assertTrue(all(RE.Reducer(RE.factor_per_step(a)).retain(p) <= p for p in (1, 7, 846)))      # jamais plus que le jeu


@unittest.skipUnless(os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES'), 'DQ_APK et DQ_SAVES requis (vrai moteur)')
class TestRealEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dq4_pc.core import engine as ENGINE
        wdir = '/tmp/sv_test_rencontres'; shutil.rmtree(wdir, ignore_errors=True); os.makedirs(wdir)
        cls.m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], wdir)
        cls.m.load_save(4)
        for _ in range(60): cls.m.step(0, 0)
        c = cls.m.core
        cls.c = c; cls.enc = c.call(c.export('_ZN7Encount12getSingletonEv')); cls.cd = c.export('_ZN9CountDown4execEv')

    def write(self, counter, rate):
        self.c.mem_w(self.enc + 0x134, struct.pack('<i', counter)); self.c.mem_w(self.enc + 0x144, struct.pack('<i', rate))

    def read(self): return struct.unpack('<i', self.c.mem(self.enc + 0x134, 4))[0]

    def invoke(self, n, speed, counter=1 << 24, rate=423):
        """n appels de CountDown::exec du vrai moteur a la vitesse de marche `speed` : perte totale du compteur."""
        self.m.walking_speed = speed; self.m.encounters.remainder = 0.0
        self.write(counter, rate)
        for _ in range(n): self.c.call(self.cd, self.enc + 0x134)
        self.m.walking_speed = 1.0
        return counter - self.read()

    def test_hook_installed_and_x1_identical(self):
        self.assertEqual(self.invoke(1, 1.0), 2 * 423)                                         # le jeu : 2 x [+0x10] par appel
        self.assertEqual(self.invoke(100, 1.0), 100 * 2 * 423)
        self.assertEqual(self.invoke(100, 0.5), 100 * 2 * 423)                                 # plus lent que x1 : jamais touche

    def test_counter_loss_at_x2_x3_x4(self):
        for a in (2.0, 3.0, 4.0):
            loss = self.invoke(1000, a); expected = 1000 * 2 * 423 * (1.0 + a) / (2.0 * a)
            self.assertLessEqual(abs(loss - expected), 1.0, (a, loss, expected))               # (1 + a) / (2 a) de la perte du jeu, a une unite pres
            self.assertAlmostEqual(a * loss / (1000 * 2 * 423), (1.0 + a) / 2.0, places=3)     # pas par seconde x perte par pas : (1 + a) / 2

    def test_trigger_when_counter_goes_negative(self):
        """Le compteur passe sous zero apres (compteur / perte) appels a x1, apres (compteur / perte) x 2a / (1 + a) appels a x4 : meme tirage, simplement moins de pas comptes."""
        def calls(speed):
            self.m.walking_speed = speed; self.m.encounters.remainder = 0.0; self.write(8326, 423); n = 0
            while self.read() >= 0 and n < 1000: self.c.call(self.cd, self.enc + 0x134); n += 1
            self.m.walking_speed = 1.0
            return n
        n1, n4 = calls(1.0), calls(4.0)
        self.assertEqual(n1, 10)                                                                # 8326 / 846 : le jeu d'origine
        self.assertEqual(n4, 16)                                                                # 8326 / (846 x 0,625) = 15,7 appels -> 16
        self.assertAlmostEqual(n4 / n1, 2.0 * 4 / (1 + 4), delta=0.1)

    def test_negative_counter_stays_negative(self):
        """Apres le declenchement le moteur continue d'appeler exec : le crochet ne doit jamais remonter le compteur."""
        self.m.walking_speed = 4.0; self.write(-5, 423)
        for _ in range(20):
            self.c.call(self.cd, self.enc + 0x134); self.assertLess(self.read(), 0)
        self.m.walking_speed = 1.0


if __name__ == '__main__': unittest.main(verbosity=1)
