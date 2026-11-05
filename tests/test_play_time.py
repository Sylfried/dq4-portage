"""Temps de jeu de la sauvegarde sur l'heure reelle (#239, audit ENG-04, sondage du 04/11/2026) : le moteur ajoute 2 unites (1/60 s) par pas ; quand le jeu est accelere (marche x1,5 a x8, accelerateur, combat rapide) il fait `a` fois
plus de pas par seconde reelle : le crochet de `Engine._game_time_hooks` ne laisse passer que 1 / a des appels `GameStatus::addPlayTime`.

    python3 tests/test_play_time.py
    DQ_APK=... DQ_SAVES=... python3 tests/test_play_time.py      (ajoute les tests du vrai moteur)
"""
import os, sys, struct, shutil, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.core import encounters as RE


class TestFormula(unittest.TestCase):
    def test_share_of_steps(self):
        """Sur 1200 pas a la vitesse a, 1200 / a appels passent (a un pres) : 2 x 1200 / a unites de temps, soit 2400 / a / 60 s de temps de jeu pour 1200 / (30 a) s d'horloge reelle."""
        for a in (1.25, 1.5, 2.0, 3.0, 4.0, 8.0):
            p = RE.Passer(1.0 / a); n = sum(1 for _ in range(1200) if p.allows())
            self.assertLessEqual(abs(n - 1200 / a), 1.0, a)
            game_time = 2 * n / 60.0; real_time = 1200 / (30.0 * a)
            self.assertAlmostEqual(game_time, real_time, delta=0.1, msg=a)               # le temps de jeu suit l'horloge reelle

    def test_at_x1_everything_passes(self):
        p = RE.Passer(1.0); self.assertTrue(all(p.allows() for _ in range(100)))


@unittest.skipUnless(os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES'), 'DQ_APK et DQ_SAVES requis (vrai moteur)')
class TestRealEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dq4_pc.core import engine as ENGINE
        cls.ENGINE = ENGINE
        cls.wdir = '/tmp/sv_test_temps_de_jeu'; shutil.rmtree(cls.wdir, ignore_errors=True); os.makedirs(cls.wdir)
        cls.m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], cls.wdir); cls.m.load_save(4)
        for _ in range(200): cls.m.step(0, 0)
        cls.g = cls.m.core.export('_ZN6status6g_GameE')

    def clock(self): return struct.unpack('<I', self.m.core.mem(self.g + 4, 4))[0]

    def measure(self, v, step=600):
        m = self.m; m.clock_speed = v; t0 = self.clock()
        for _ in range(step): m.step(0, 0)
        m.clock_speed = 1.0
        return self.clock() - t0

    def test_hook_installed(self):
        self.assertFalse([x for x in self.m.missing_hooks if 'temps de jeu' in x], self.m.missing_hooks)

    def test_x1_the_game_as_is(self):
        self.assertEqual(self.measure(1.0), 1200)                                          # exactement 2 par pas
        self.assertEqual(self.measure(0.5), 1200)                                          # (ralenti : inchange, le crochet ne rattrape pas)

    def test_acceleration_reduces_time_per_step(self):
        for v in (1.5, 2.0, 3.0, 4.0, 8.0):
            d = self.measure(v)
            self.assertLessEqual(abs(d - 1200 / v), 2.0, 'x%g : +%d' % (v, d))
            self.assertEqual(d % 2, 0, v)                                                 # le temps avance toujours par 2 (les appels sont sautes, jamais coupes)

    def test_return_to_x1_after_acceleration(self):
        self.measure(4.0); self.assertEqual(self.measure(1.0), 1200)


if __name__ == '__main__': unittest.main(verbosity=1)
