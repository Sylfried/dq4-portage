"""#212 (audit SPR-02) : paquet 15 (cmd_chara_shadow) : bit 12 = position de l'ombre (3 flottants), bit 13 = opacite (1 flottant), bit 14 = position de l'ombre sur la carte du monde (SetFieldShadowPosition, 3 flottants).
Les flottants se suivent dans cet ordre : lire le bit 14 sans avoir retire celui du bit 13 donnait un decalage. Le ballon (paquet 0x440c, [2495,97 ; 383,97 ; -1] pour un sprite en (2496 ; 352)) a son ombre 32 pixels plus au sud.
Sans fenetre ni moteur (unicorn seul pour l'import) :    python3 tests/test_ombre_ballon.py"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import moteur as MO


def etat_avec(slot=12):
    e = MO.Etat(); e.sprites[slot] = {'id': 4279, 'pos': (2496.0, 352.0, 20.0), 'col': (1, 1, 1, 1), 'pose': 0, 'dir': 0}
    return e


def paquet(e, v, fl, slot=12):
    e.appliquer([(15, [v | slot], list(fl))], lambda *a: None); return e.sprites[slot]


class PaquetOmbre(unittest.TestCase):
    def test_ballon(self):                                            # 0x440c : bits 10 (separee) et 14 (position sur la carte)
        s = paquet(etat_avec(), 0x4400, [2495.97, 383.97, -1.0])
        self.assertEqual(s['ombre_champ'], (2495.97, 383.97, -1.0)); self.assertTrue(s['ombre_sep']); self.assertNotIn('ombre_pos', s); self.assertNotIn('ombre_a', s)
        self.assertAlmostEqual(s['ombre_champ'][1] - s['pos'][1], 32.0, delta=0.1)       # 2 tuiles de 16 pixels au sud

    def test_opacite_puis_position_sur_la_carte(self):               # bit 13 : un flottant qui doit etre retire avant ceux du bit 14
        s = paquet(etat_avec(), 0x6000, [0.5, 100.0, 200.0, -1.0])
        self.assertEqual((s['ombre_a'], s['ombre_champ']), (0.5, (100.0, 200.0, -1.0)))

    def test_ordre_complet(self):                                     # bits 12, 13, 14
        s = paquet(etat_avec(), 0x7000, [1.0, 2.0, 3.0, 0.25, 10.0, 20.0, 30.0])
        self.assertEqual((s['ombre_pos'], s['ombre_a'], s['ombre_champ']), ((1.0, 2.0, 3.0), 0.25, (10.0, 20.0, 30.0)))

    def test_sans_bit_14_rien_ne_change(self):
        s = paquet(etat_avec(), 0x2000, [0.5]); self.assertEqual(s['ombre_a'], 0.5); self.assertNotIn('ombre_champ', s)
        s = paquet(etat_avec(), 0x1000, [1.0, 2.0, 3.0]); self.assertEqual(s['ombre_pos'], (1.0, 2.0, 3.0)); self.assertNotIn('ombre_champ', s)
        s = paquet(etat_avec(), 0x100, []); self.assertTrue(s['ombre']); self.assertNotIn('ombre_champ', s)

    def test_flottants_manquants(self):                               # paquet tronque : pas d'erreur, pas de position inventee
        s = paquet(etat_avec(), 0x4000, [1.0, 2.0]); self.assertNotIn('ombre_champ', s)


if __name__ == '__main__': unittest.main(verbosity=1)
