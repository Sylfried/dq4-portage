"""Temps de jeu de la sauvegarde sur l'heure reelle (#239, audit ENG-04, sondage du 04/11/2026) : le moteur ajoute 2 unites (1/60 s) par pas ; quand le jeu est accelere (marche x1,5 a x8, accelerateur, combat rapide) il fait `a` fois
plus de pas par seconde reelle : le crochet de `Moteur._crochets_temps_de_jeu` ne laisse passer que 1 / a des appels `GameStatus::addPlayTime`.

    python3 tests/test_temps_de_jeu.py
    DQ_APK=... DQ_SAVES=... python3 tests/test_temps_de_jeu.py      (ajoute les tests du vrai moteur)
"""
import os, sys, struct, shutil, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import rencontres as RE


class TestFormule(unittest.TestCase):
    def test_part_des_pas(self):
        """Sur 1200 pas a la vitesse a, 1200 / a appels passent (a un pres) : 2 x 1200 / a unites de temps, soit 2400 / a / 60 s de temps de jeu pour 1200 / (30 a) s d'horloge reelle."""
        for a in (1.25, 1.5, 2.0, 3.0, 4.0, 8.0):
            p = RE.Passeur(1.0 / a); n = sum(1 for _ in range(1200) if p.passe())
            self.assertLessEqual(abs(n - 1200 / a), 1.0, a)
            temps_jeu = 2 * n / 60.0; temps_reel = 1200 / (30.0 * a)
            self.assertAlmostEqual(temps_jeu, temps_reel, delta=0.1, msg=a)               # le temps de jeu suit l'horloge reelle

    def test_a_x1_tout_passe(self):
        p = RE.Passeur(1.0); self.assertTrue(all(p.passe() for _ in range(100)))


@unittest.skipUnless(os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES'), 'DQ_APK et DQ_SAVES requis (vrai moteur)')
class TestVraiMoteur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dq4_pc.noyau import moteur as MO
        cls.MO = MO
        cls.ecr = '/tmp/sv_test_temps_de_jeu'; shutil.rmtree(cls.ecr, ignore_errors=True); os.makedirs(cls.ecr)
        cls.m = MO.Moteur(os.environ['DQ_APK'], os.environ['DQ_SAVES'], cls.ecr); cls.m.charger_sauvegarde(4)
        for _ in range(200): cls.m.step(0, 0)
        cls.g = cls.m.core.export('_ZN6status6g_GameE')

    def temps(self): return struct.unpack('<I', self.m.core.mem(self.g + 4, 4))[0]

    def mesure(self, v, pas=600):
        m = self.m; m.vitesse_horloge = v; t0 = self.temps()
        for _ in range(pas): m.step(0, 0)
        m.vitesse_horloge = 1.0
        return self.temps() - t0

    def test_crochet_installe(self):
        self.assertFalse([x for x in self.m.crochets_manques if 'temps de jeu' in x], self.m.crochets_manques)

    def test_x1_le_jeu_tel_quel(self):
        self.assertEqual(self.mesure(1.0), 1200)                                          # exactement 2 par pas
        self.assertEqual(self.mesure(0.5), 1200)                                          # (ralenti : inchange, le crochet ne rattrape pas)

    def test_acceleration_reduit_le_temps_par_pas(self):
        for v in (1.5, 2.0, 3.0, 4.0, 8.0):
            d = self.mesure(v)
            self.assertLessEqual(abs(d - 1200 / v), 2.0, 'x%g : +%d' % (v, d))
            self.assertEqual(d % 2, 0, v)                                                 # le temps avance toujours par 2 (les appels sont sautes, jamais coupes)

    def test_retour_a_x1_apres_acceleration(self):
        self.mesure(4.0); self.assertEqual(self.mesure(1.0), 1200)


if __name__ == '__main__': unittest.main(verbosity=1)
