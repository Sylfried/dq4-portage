"""Arrivee de la nuit a marche acceleree (#163) : (1 + a) / 2 fois plus vite par seconde reelle, pas a fois (comme les rencontres aleatoires, #45).

    python3 tools/test_day_clock.py
    DQ_APK=... DQ_SAVES=... python3 tools/test_day_clock.py      (ajoute les tests du vrai moteur : le crochet sur FieldPlayerDoku::checkDokuDamage)

Sur la carte du monde, le temps du monde (`status::g_Stage + 0xcc`, cycle de 0xd40) avance de 2 par image du moteur ou le heros a change de position (`FieldStage::ChangeTime(0)`). A la vitesse `a`, le moteur fait
`a` fois plus d'images par seconde reelle : chaque pas doit donc compter (1 + a) / (2 a) fois ce qu'il comptait.
"""
import os, sys, struct, shutil, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.core import encounters as RE


class TestFormulas(unittest.TestCase):
    def test_passer_at_one_lets_everything_pass(self):
        p = RE.Passer(1.0)
        self.assertTrue(all(p.allows() for _ in range(100)))
        p = RE.Passer(); self.assertTrue(all(p.allows() for _ in range(100)))                   # (defaut : transparent)

    def test_passer_exact_fraction(self):
        for a in (1.25, 1.5, 2.0, 3.0, 4.0, 8.0):
            p = RE.Passer(RE.factor_per_step(a)); n = sum(1 for _ in range(1200) if p.allows())
            self.assertLessEqual(abs(n - 1200 * RE.factor_per_step(a)), 1.0, a)                  # a un appel pres

    def test_passer_regular(self):
        """Les appels sautes sont repartis (3 sur 4 a x2 : jamais deux saut de suite) : le temps n'avance pas par a-coups."""
        p = RE.Passer(RE.factor_per_step(2.0)); seen = [p.allows() for _ in range(40)]
        self.assertEqual(sum(seen), 30); self.assertFalse(any(not a and not b for a, b in zip(seen, seen[1:])))

    def test_night_per_second_like_encounters(self):
        """Pas par seconde (a) x temps par pas (2 x facteur) = 2 x (1 + a) / 2 : x2 -> 1,5 fois, x1,5 -> 1,25 fois, x4 -> 2,5 fois."""
        for a, expected in ((1.5, 1.25), (2.0, 1.5), (3.0, 2.0), (4.0, 2.5)):
            self.assertAlmostEqual(a * RE.factor_per_step(a), expected)
            self.assertAlmostEqual(a * RE.factor_per_step(a), RE.encounters_per_second(a))


@unittest.skipUnless(os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES'), 'DQ_APK et DQ_SAVES requis (vrai moteur)')
class TestRealEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dq4_pc.core import engine as ENGINE
        cls.ENGINE = ENGINE
        cls.wdir = '/tmp/sv_test_horloge_jour'; shutil.rmtree(cls.wdir, ignore_errors=True); os.makedirs(cls.wdir)

    def world(self):
        """Moteur sur la carte du monde (sauvegarde 4), le heros dans le couloir sans entree ni sortie de tools/simulate_encounters.py, sans combat (Encount::brew renvoie faux) ; -> (moteur, lecteur du temps du monde)."""
        ENGINE = self.ENGINE
        m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], self.wdir); c = m.core; m.load_save(4)
        for i in range(700):
            m.step(0, 0)
            if i >= 130 and 0 in m.state.sprites: break
        c.mem_w(c.export('_ZN7Encount4brewEv'), struct.pack('<II', 0x52800000, 0xd65f03c0))
        m.enc = c.call(c.export('_ZN7Encount12getSingletonEv')); m.enc_setup = c.export('_ZN7Encount5setupE11EncountPart8LandType')
        for _ in range(10): m.step(ENGINE.UP, ENGINE.UP)                                                  # de la case de depart au couloir (y = 354)
        g = c.export('_ZN6status7g_StageE')
        return m, (lambda: struct.unpack('<i', c.mem(g + 0xcc, 4))[0])

    def walk(self, m, clock, v, frames=500):
        """Marche allers-retours dans le couloir (le sens s'inverse quand le heros est bloque) a la vitesse `v` : -> (pas, avance du temps du monde, positions du heros apres chaque image)."""
        ENGINE = self.ENGINE; c = m.core
        m.walking_speed = v; step = 0; dt = 0; last = clock(); prev = tuple(m.state.sprites[0]['pos']); trace = []; d = ENGINE.LEFT; blocked = 0
        for k in range(frames):
            m.step(d, d)
            if struct.unpack('<i', c.mem(m.enc + 0x1c, 4))[0] >= 1: c.call(m.enc_setup, m.enc, 0, 0)         # rencontre declenchee (sans combat) : le compteur repart, le heros peut marcher
            pos = tuple(m.state.sprites[0]['pos']); t = clock(); trace.append(pos)
            if pos != prev:
                step += 1; blocked = 0; dd = t - last; dt += dd + (0xd40 if dd < 0 else 0)
            else:
                blocked += 1
                if blocked >= 2: d = ENGINE.RIGHT if d == ENGINE.LEFT else ENGINE.LEFT; blocked = 0
            last = t; prev = pos
        m.walking_speed = 1.0
        return step, dt, trace

    def test_x1_the_game_as_is_and_x2_x4_reduced(self):
        for v in (1.0, 1.5, 2.0, 3.0, 4.0):
            m, clock = self.world()
            step, dt, _ = self.walk(m, clock, v)
            self.assertGreater(step, 200, v)
            expected = 2.0 * (1.0 if v <= 1.0 else RE.factor_per_step(v))
            self.assertLessEqual(abs(dt - step * expected), 4.0, 'x%g : +%d en %d pas' % (v, dt, step))      # x1 : exactement 2 par pas ; sinon (1 + a) / (2 a) de cela, a quelques unites pres
            self.assertEqual(dt % 2, 0, v)                                                              # le temps avance toujours par 2 : les zones et la palette restent celles du jeu
            print('x%g : %d pas, temps +%d (%.3f par pas, attendu %.3f ; par seconde %.3f fois x1)' % (v, step, dt, dt / step, expected, v * dt / step / 2.0), flush=True)

    def test_hero_movement_does_not_change(self):
        m1, t1 = self.world(); m2, t2 = self.world()
        _, _, a = self.walk(m1, t1, 1.0); _, _, b = self.walk(m2, t2, 4.0)
        self.assertEqual(a, b)                                                                          # memes positions image par image : seul le temps du monde est ralenti


if __name__ == '__main__': unittest.main(verbosity=1)
