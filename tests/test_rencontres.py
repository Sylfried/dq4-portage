"""Tests des rencontres aleatoires a marche acceleree (#45) : (1 + a) / 2 rencontres par seconde reelle, pas a.

    python3 outils/test_rencontres.py
    DQ_APK=... DQ_SAVES=... python3 outils/test_rencontres.py      (ajoute les tests du vrai moteur : le crochet sur CountDown::exec)

La simulation statistique (marche reelle sur la carte du monde et dans un donjon, nombre de rencontres par pas a x1 / x2 / x4) est dans outils/simuler_rencontres.py.
"""
import os, sys, struct, shutil, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import rencontres as RE


class TestFormules(unittest.TestCase):
    def test_x1_et_en_dessous_rien_ne_change(self):
        for a in (0.25, 0.5, 1.0): self.assertEqual(RE.facteur_par_pas(a), 1.0)
        for a in (0.25, 0.5, 1.0): self.assertEqual(RE.rencontres_par_seconde(a), a if a < 1 else 1.0 * a)

    def test_un_plus_a_sur_deux(self):
        for a in (2.0, 3.0, 4.0, 6.0, 8.0):
            self.assertAlmostEqual(RE.facteur_par_pas(a), (1.0 + a) / (2.0 * a))
            self.assertAlmostEqual(RE.rencontres_par_seconde(a), (1.0 + a) / 2.0)          # x2 : 1,5 ; x3 : 2 ; x4 : 2,5
        self.assertAlmostEqual(RE.rencontres_par_seconde(2.0), 1.5); self.assertAlmostEqual(RE.rencontres_par_seconde(3.0), 2.0); self.assertAlmostEqual(RE.rencontres_par_seconde(4.0), 2.5)

    def test_moins_de_rencontres_par_pas_mais_toujours_plus_par_seconde(self):
        a_prec = 1.0
        for a in (1.5, 2.0, 3.0, 4.0, 8.0):
            self.assertLess(RE.facteur_par_pas(a), RE.facteur_par_pas(a_prec))                  # chaque pas compte moins ...
            self.assertGreater(RE.facteur_par_pas(a), 0.5)                                      # ... sans jamais descendre sous 1 / 2
            self.assertGreater(RE.rencontres_par_seconde(a), RE.rencontres_par_seconde(a_prec)) # ... et la vitesse augmente toujours la frequence par seconde
            a_prec = a

    def test_reducteur_a_facteur_un_est_transparent(self):
        r = RE.Reducteur(1.0)
        for p in (0, 1, 846, 100000, -5): self.assertEqual(r.retenir(p), p)

    def test_reducteur_somme_exacte_avec_fractions(self):
        for a in (2.0, 3.0, 4.0):
            r = RE.Reducteur(RE.facteur_par_pas(a)); tot = 0; jeu = 0
            for i in range(1000):
                p = 846 + (i % 7) * 13; jeu += p; tot += r.retenir(p)
            self.assertLessEqual(abs(tot - jeu * RE.facteur_par_pas(a)), 1.0)                  # a une unite pres
            self.assertTrue(all(RE.Reducteur(RE.facteur_par_pas(a)).retenir(p) <= p for p in (1, 7, 846)))      # jamais plus que le jeu


@unittest.skipUnless(os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES'), 'DQ_APK et DQ_SAVES requis (vrai moteur)')
class TestVraiMoteur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dq4_pc.noyau import moteur as MO
        ecr = '/tmp/sv_test_rencontres'; shutil.rmtree(ecr, ignore_errors=True); os.makedirs(ecr)
        cls.m = MO.Moteur(os.environ['DQ_APK'], os.environ['DQ_SAVES'], ecr)
        cls.m.charger_sauvegarde(4)
        for _ in range(60): cls.m.step(0, 0)
        c = cls.m.core
        cls.c = c; cls.enc = c.call(c.export('_ZN7Encount12getSingletonEv')); cls.cd = c.export('_ZN9CountDown4execEv')

    def ecrire(self, compteur, taux):
        self.c.mem_w(self.enc + 0x134, struct.pack('<i', compteur)); self.c.mem_w(self.enc + 0x144, struct.pack('<i', taux))

    def lire(self): return struct.unpack('<i', self.c.mem(self.enc + 0x134, 4))[0]

    def appeler(self, n, vitesse, compteur=1 << 24, taux=423):
        """n appels de CountDown::exec du vrai moteur a la vitesse de marche `vitesse` : perte totale du compteur."""
        self.m.vitesse_marche = vitesse; self.m.rencontres.reste = 0.0
        self.ecrire(compteur, taux)
        for _ in range(n): self.c.call(self.cd, self.enc + 0x134)
        self.m.vitesse_marche = 1.0
        return compteur - self.lire()

    def test_crochet_installe_et_x1_identique(self):
        self.assertEqual(self.appeler(1, 1.0), 2 * 423)                                         # le jeu : 2 x [+0x10] par appel
        self.assertEqual(self.appeler(100, 1.0), 100 * 2 * 423)
        self.assertEqual(self.appeler(100, 0.5), 100 * 2 * 423)                                 # plus lent que x1 : jamais touche

    def test_perte_du_compteur_a_x2_x3_x4(self):
        for a in (2.0, 3.0, 4.0):
            perte = self.appeler(1000, a); attendu = 1000 * 2 * 423 * (1.0 + a) / (2.0 * a)
            self.assertLessEqual(abs(perte - attendu), 1.0, (a, perte, attendu))               # (1 + a) / (2 a) de la perte du jeu, a une unite pres
            self.assertAlmostEqual(a * perte / (1000 * 2 * 423), (1.0 + a) / 2.0, places=3)     # pas par seconde x perte par pas : (1 + a) / 2

    def test_declenchement_quand_le_compteur_devient_negatif(self):
        """Le compteur passe sous zero apres (compteur / perte) appels a x1, apres (compteur / perte) x 2a / (1 + a) appels a x4 : meme tirage, simplement moins de pas comptes."""
        def appels(vitesse):
            self.m.vitesse_marche = vitesse; self.m.rencontres.reste = 0.0; self.ecrire(8326, 423); n = 0
            while self.lire() >= 0 and n < 1000: self.c.call(self.cd, self.enc + 0x134); n += 1
            self.m.vitesse_marche = 1.0
            return n
        n1, n4 = appels(1.0), appels(4.0)
        self.assertEqual(n1, 10)                                                                # 8326 / 846 : le jeu d'origine
        self.assertEqual(n4, 16)                                                                # 8326 / (846 x 0,625) = 15,7 appels -> 16
        self.assertAlmostEqual(n4 / n1, 2.0 * 4 / (1 + 4), delta=0.1)

    def test_compteur_negatif_reste_negatif(self):
        """Apres le declenchement le moteur continue d'appeler exec : le crochet ne doit jamais remonter le compteur."""
        self.m.vitesse_marche = 4.0; self.ecrire(-5, 423)
        for _ in range(20):
            self.c.call(self.cd, self.enc + 0x134); self.assertLess(self.lire(), 0)
        self.m.vitesse_marche = 1.0


if __name__ == '__main__': unittest.main(verbosity=1)
