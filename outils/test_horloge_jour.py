"""Arrivee de la nuit a marche acceleree (#163) : (1 + a) / 2 fois plus vite par seconde reelle, pas a fois (comme les rencontres aleatoires, #45).

    python3 outils/test_horloge_jour.py
    DQ_APK=... DQ_SAVES=... python3 outils/test_horloge_jour.py      (ajoute les tests du vrai moteur : le crochet sur FieldPlayerDoku::checkDokuDamage)

Sur la carte du monde, le temps du monde (`status::g_Stage + 0xcc`, cycle de 0xd40) avance de 2 par image du moteur ou le heros a change de position (`FieldStage::ChangeTime(0)`). A la vitesse `a`, le moteur fait
`a` fois plus d'images par seconde reelle : chaque pas doit donc compter (1 + a) / (2 a) fois ce qu'il comptait.
"""
import os, sys, struct, shutil, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import rencontres as RE


class TestFormules(unittest.TestCase):
    def test_passeur_a_un_laisse_tout_passer(self):
        p = RE.Passeur(1.0)
        self.assertTrue(all(p.passe() for _ in range(100)))
        p = RE.Passeur(); self.assertTrue(all(p.passe() for _ in range(100)))                   # (defaut : transparent)

    def test_passeur_fraction_exacte(self):
        for a in (1.25, 1.5, 2.0, 3.0, 4.0, 8.0):
            p = RE.Passeur(RE.facteur_par_pas(a)); n = sum(1 for _ in range(1200) if p.passe())
            self.assertLessEqual(abs(n - 1200 * RE.facteur_par_pas(a)), 1.0, a)                  # a un appel pres

    def test_passeur_regulier(self):
        """Les appels sautes sont repartis (3 sur 4 a x2 : jamais deux saut de suite) : le temps n'avance pas par a-coups."""
        p = RE.Passeur(RE.facteur_par_pas(2.0)); vus = [p.passe() for _ in range(40)]
        self.assertEqual(sum(vus), 30); self.assertFalse(any(not a and not b for a, b in zip(vus, vus[1:])))

    def test_nuit_par_seconde_comme_les_rencontres(self):
        """Pas par seconde (a) x temps par pas (2 x facteur) = 2 x (1 + a) / 2 : x2 -> 1,5 fois, x1,5 -> 1,25 fois, x4 -> 2,5 fois."""
        for a, attendu in ((1.5, 1.25), (2.0, 1.5), (3.0, 2.0), (4.0, 2.5)):
            self.assertAlmostEqual(a * RE.facteur_par_pas(a), attendu)
            self.assertAlmostEqual(a * RE.facteur_par_pas(a), RE.rencontres_par_seconde(a))


@unittest.skipUnless(os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES'), 'DQ_APK et DQ_SAVES requis (vrai moteur)')
class TestVraiMoteur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import moteur as MO
        cls.MO = MO
        cls.ecr = '/tmp/sv_test_horloge_jour'; shutil.rmtree(cls.ecr, ignore_errors=True); os.makedirs(cls.ecr)

    def monde(self):
        """Moteur sur la carte du monde (sauvegarde 4), le heros dans le couloir sans entree ni sortie de outils/simuler_rencontres.py, sans combat (Encount::brew renvoie faux) ; -> (moteur, lecteur du temps du monde)."""
        MO = self.MO
        m = MO.Moteur(os.environ['DQ_APK'], os.environ['DQ_SAVES'], self.ecr); c = m.core; m.charger_sauvegarde(4)
        for i in range(700):
            m.step(0, 0)
            if i >= 130 and 0 in m.etat.sprites: break
        c.mem_w(c.export('_ZN7Encount4brewEv'), struct.pack('<II', 0x52800000, 0xd65f03c0))
        m.enc = c.call(c.export('_ZN7Encount12getSingletonEv')); m.enc_setup = c.export('_ZN7Encount5setupE11EncountPart8LandType')
        for _ in range(10): m.step(MO.HAUT, MO.HAUT)                                                  # de la case de depart au couloir (y = 354)
        g = c.export('_ZN6status7g_StageE')
        return m, (lambda: struct.unpack('<i', c.mem(g + 0xcc, 4))[0])

    def marche(self, m, temps, v, images=500):
        """Marche allers-retours dans le couloir (le sens s'inverse quand le heros est bloque) a la vitesse `v` : -> (pas, avance du temps du monde, positions du heros apres chaque image)."""
        MO = self.MO; c = m.core
        m.vitesse_marche = v; pas = 0; dt = 0; dernier = temps(); prev = tuple(m.etat.sprites[0]['pos']); trace = []; d = MO.GAUCHE; bloque = 0
        for k in range(images):
            m.step(d, d)
            if struct.unpack('<i', c.mem(m.enc + 0x1c, 4))[0] >= 1: c.call(m.enc_setup, m.enc, 0, 0)         # rencontre declenchee (sans combat) : le compteur repart, le heros peut marcher
            pos = tuple(m.etat.sprites[0]['pos']); t = temps(); trace.append(pos)
            if pos != prev:
                pas += 1; bloque = 0; dd = t - dernier; dt += dd + (0xd40 if dd < 0 else 0)
            else:
                bloque += 1
                if bloque >= 2: d = MO.DROITE if d == MO.GAUCHE else MO.GAUCHE; bloque = 0
            dernier = t; prev = pos
        m.vitesse_marche = 1.0
        return pas, dt, trace

    def test_x1_le_jeu_tel_quel_et_x2_x4_reduits(self):
        for v in (1.0, 1.5, 2.0, 3.0, 4.0):
            m, temps = self.monde()
            pas, dt, _ = self.marche(m, temps, v)
            self.assertGreater(pas, 200, v)
            attendu = 2.0 * (1.0 if v <= 1.0 else RE.facteur_par_pas(v))
            self.assertLessEqual(abs(dt - pas * attendu), 4.0, 'x%g : +%d en %d pas' % (v, dt, pas))      # x1 : exactement 2 par pas ; sinon (1 + a) / (2 a) de cela, a quelques unites pres
            self.assertEqual(dt % 2, 0, v)                                                              # le temps avance toujours par 2 : les zones et la palette restent celles du jeu
            print('x%g : %d pas, temps +%d (%.3f par pas, attendu %.3f ; par seconde %.3f fois x1)' % (v, pas, dt, dt / pas, attendu, v * dt / pas / 2.0), flush=True)

    def test_le_deplacement_du_heros_ne_change_pas(self):
        m1, t1 = self.monde(); m2, t2 = self.monde()
        _, _, a = self.marche(m1, t1, 1.0); _, _, b = self.marche(m2, t2, 4.0)
        self.assertEqual(a, b)                                                                          # memes positions image par image : seul le temps du monde est ralenti


if __name__ == '__main__': unittest.main(verbosity=1)
