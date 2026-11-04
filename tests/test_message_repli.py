"""#231 (audit CMB-04) : `Moteur.lire_message` (repli « menus simples », sans ui_layout.json) lit le canevas du message comme une texture circulaire de 512 lignes (REPEAT d'Unity) : le defilement du moteur
croit sans borne, apres une dizaine de lignes il depassait 512 et le texte devenait vide. Moteur factice (memoire et canevas simules), sans carte ni donnees.
    python3 tests/test_message_repli.py"""
import os, struct, sys, types, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import moteur as MO

L, OBJ = 0x100000, 0x200000


def moteur_factice(defil, lignes=4, lh=28, canevas='ok'):
    """Moteur dont seuls `lire_canevas` et la lecture des reglages (nombre de lignes, hauteur d'une ligne, defilement) existent."""
    val = {L + 0x2523a0: lignes - 1, OBJ + 0x42: lh, OBJ + 0x4a: defil}
    m = types.SimpleNamespace(L=L, obj_msg=OBJ, core=types.SimpleNamespace(mem=lambda ad, n: struct.pack('<h', val[ad])))
    img = np.repeat((np.arange(MO.CANEVAS_H) % 251 + 1).astype(np.uint8)[:, None], MO.CANEVAS_L, axis=1)       # chaque ligne r porte la valeur r % 251 + 1 (jamais 0)
    m.lire_canevas = lambda: img if canevas == 'ok' else None
    return m, img


def lignes(sub): return [int(v) for v in sub[:, 0]]


class Repli(unittest.TestCase):
    def lire(self, defil, **kw):
        m, img = moteur_factice(defil, **kw); return MO.Moteur.lire_message(m), img

    def attendu(self, premiere, n): return [(r % MO.CANEVAS_H) % 251 + 1 for r in range(premiere, premiere + n)]

    def test_debut(self):
        sub, _ = self.lire(-3); self.assertEqual(sub.shape, (112, MO.CANEVAS_L)); self.assertEqual(lignes(sub), self.attendu(0, 112))

    def test_dans_le_canevas(self):
        sub, _ = self.lire(100); self.assertEqual(lignes(sub), self.attendu(103, 112))

    def test_fin_du_canevas_reprend_au_debut(self):
        sub, _ = self.lire(450)                                                               # lignes 453 a 511 puis 0 a 52 (avant : du vide apres la ligne 511)
        self.assertEqual(lignes(sub), self.attendu(453, 59) + self.attendu(0, 53)); self.assertTrue((sub != 0).all())

    def test_defilement_au_dela_de_512(self):
        for defil in (509, 1000, 5000, 30000):
            sub, _ = self.lire(defil); self.assertEqual(lignes(sub), self.attendu((defil + 3) % 512, 112), defil); self.assertTrue((sub != 0).all(), defil)

    def test_petit_defilement_negatif_inchange(self):
        sub, _ = self.lire(-10); self.assertEqual(lignes(sub), self.attendu(0, 112))

    def test_reglages_incoherents_valeurs_par_defaut(self):
        sub, _ = self.lire(200, lignes=20); self.assertEqual(lignes(sub), self.attendu(0, 112))                      # (4 lignes de 28, defilement -3)

    def test_autre_nombre_de_lignes(self):
        sub, _ = self.lire(300, lignes=3, lh=40); self.assertEqual(sub.shape[0], 120); self.assertEqual(lignes(sub), self.attendu(303, 120))

    def test_sans_canevas(self):
        m, _ = moteur_factice(0, canevas=None); self.assertIsNone(MO.Moteur.lire_message(m))

    def test_le_canevas_n_est_pas_modifie(self):
        m, img = moteur_factice(450); avant = img.copy(); MO.Moteur.lire_message(m); self.assertTrue((img == avant).all())


if __name__ == '__main__':
    unittest.main(verbosity=1)
