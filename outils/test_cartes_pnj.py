"""Tests de la mission « cartes, PNJ, interrupteurs » de l'audit (sans fenetre, sans moteur, sans APK) :

  1. un personnage de ville qui recoit une pose (paquet 13, bit 0x4000) sans jamais avoir recu de position est a l'ORIGINE (0, 0, 0) : le moteur ne renvoie une position que si elle change
     (son enregistrement du personnage vaut (0, 0, 0) : relu dans la memoire du moteur sur mqtf3, mom2f1 et msm1f1, emplacement 8 : Fix32 a 0x1026a688 + 0x1c0 x (emplacement - 8)) ;

    python3 outils/test_cartes_pnj.py
"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import moteur as MO


def nom_carte(): return 'carte_test'


class TestSpritesALOrigine(unittest.TestCase):
    def setUp(self): self.e = MO.Etat()

    def appliquer(self, *paquets): self.e.appliquer(list(paquets), nom_carte)

    def test_pose_sans_position(self):
        self.e.image = 153; self.appliquer((12, [8, 157], []))
        self.assertIsNone(self.e.sprites[8]['pos'])                  # charge, pas encore pose : rien a dessiner
        self.e.image = 154; self.appliquer((13, [0x4008, 0 | (0 << 8)], []))      # 1re pose, 1 image apres : la position des autres personnages arrive a cette image ou la suivante, rien n'est dessine encore
        self.assertIsNone(self.e.sprites[8]['pos'])
        self.e.image = 159; self.appliquer((13, [0x4008, 1 | (2 << 8)], []))      # pose 1, cap 2, toujours aucune position : le personnage est a l'origine
        s = self.e.sprites[8]
        self.assertEqual((s['pose'], s['dir']), (1, 2))
        self.assertEqual(tuple(s['pos']), (0.0, 0.0, 0.0))

    def test_position_recue_gardee(self):
        self.appliquer((12, [9, 21], []))
        self.appliquer((13, [0x6009, 0 | (3 << 8)], [3.5, 0.25, -2.0]))     # position + pose dans le meme paquet
        self.assertEqual(tuple(self.e.sprites[9]['pos']), (3.5, 0.25, -2.0))
        self.appliquer((13, [0x4009, 1 | (3 << 8)], []))             # pose seule ensuite : la position ne bouge pas
        self.assertEqual(tuple(self.e.sprites[9]['pos']), (3.5, 0.25, -2.0))

    def test_position_avant_pose_dans_la_meme_image(self):
        self.appliquer((12, [10, 5], []), (13, [0x400a, 2 << 8], []), (13, [0x200a], [1.0, 0.0, 4.0]))
        self.assertEqual(tuple(self.e.sprites[10]['pos']), (1.0, 0.0, 4.0))

    def test_couleur_seule_ne_pose_pas(self):
        self.appliquer((12, [11, 5], []), (13, [0x100b], [1.0, 1.0, 1.0, 0.0]))
        self.assertIsNone(self.e.sprites[11]['pos'])                 # (la couleur n'est pas une preuve de position : seule la pose en est une)


if __name__ == '__main__':
    unittest.main(verbosity=1)
