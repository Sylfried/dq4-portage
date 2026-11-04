"""#210 (audit SPR-01) : decoupage des feuilles de sprites. Un personnage = cases de 24 x 32 sur 3 colonnes (4 ou 8 rangees) ; le bateau de la carte du monde (h193 ; 194 = alias) = cases de 40 x 40 sur 12 colonnes
(navire : rangees 0 a 4, sillage : rangees 5 a 9) et panneau de 0,8 x 0,8 (au lieu de 0,48 x 0,64). Sans fenetre ni moteur (numpy seul) ; avec la vraie feuille h193 si elle est dans le cache (DQ_CACHE_CARTES).
    python3 tests/test_feuilles_speciales.py"""
import os, sys, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.monde import hd as HD
GOUT = 2


def feuille_coloree(larg, haut, cols, rangees, tw, th):
    """Feuille tw x th ou chaque case a sa couleur : (rouge = colonne + 1, vert = rangee + 1)."""
    a = np.zeros((th, tw, 4), np.uint8)
    for r in range(rangees):
        for c in range(cols): a[r * haut:(r + 1) * haut, c * larg:(c + 1) * larg] = (c + 1, r + 1, 7, 255)
    return a


def atlas_de(arr, geo):
    a, cl, ch = HD.agrandir_feuille(arr, geo['larg'], geo['haut'], geo['cols'], geo['nl'], lambda c: c, GOUT, 1)
    return a, dict(tw=a.shape[1], th=a.shape[0], cl=cl, ch=ch, g=GOUT)


class Geometrie(unittest.TestCase):
    def test_personnage_quatre_rangees(self):
        g = HD.geometrie_feuille(3, np.zeros((128, 128, 4), np.uint8))
        self.assertEqual((g['larg'], g['haut'], g['cols'], g['nl'], g['pw'], g['ph'], g['standard']), (24, 32, 3, 4, 1.0, 1.0, True))

    def test_personnage_huit_rangees(self):
        a = np.zeros((256, 128, 4), np.uint8); a[4 * 32 + 5, 10, 3] = 255
        self.assertEqual(HD.geometrie_feuille(106, a)['nl'], 8)

    def test_bateau(self):
        g = HD.geometrie_feuille(193, np.zeros((512, 512, 4), np.uint8))
        self.assertEqual((g['larg'], g['haut'], g['cols'], g['nl'], g['standard']), (40, 40, 12, 10, False))
        self.assertAlmostEqual(g['pw'] * 24, 40.0); self.assertAlmostEqual(g['ph'] * 32, 40.0)          # panneau de 0,8 x 0,8 : 40 pixels de carte, le hero (0,48 x 0,64) en fait 24 x 32

    def test_alias_194(self):
        self.assertEqual(HD.ALIAS_FEUILLES[194], 193)
        g = HD.geometrie_feuille(194, np.zeros((512, 512, 4), np.uint8)); self.assertEqual((g['ident'], g['cols']), (193, 12))


class Cases(unittest.TestCase):
    """La case (colonne, rangee) de l'atlas, lue avec `uv_case` (celle du dessin), a bien la couleur de la case (colonne, rangee) de la feuille."""
    def verifie(self, arr, geo, cases):
        atlas, f = atlas_de(arr, geo)
        for col, row in cases:
            u0, u1, v0, v1 = HD.uv_case(f, col, row)
            x, y = int((u0 + u1) / 2 * f['tw']), int((1 - (v0 + v1) / 2) * f['th'])
            self.assertEqual(tuple(atlas[y, x][:3]), (col + 1, row + 1, 7), (col, row))
            self.assertAlmostEqual((u1 - u0) * f['tw'], geo['larg']); self.assertAlmostEqual((v1 - v0) * f['th'], geo['haut'])

    def test_bateau(self):
        g = HD.geometrie_feuille(193, None); self.verifie(feuille_coloree(40, 40, 12, 10, 512, 512), g, [(0, 0), (11, 0), (5, 4), (0, 5), (7, 6), (11, 9)])

    def test_personnage(self):
        g = HD.geometrie_feuille(3, np.zeros((128, 128, 4), np.uint8)); self.verifie(feuille_coloree(24, 32, 3, 4, 128, 128), g, [(0, 0), (2, 0), (1, 2), (2, 3)])


@unittest.skipUnless(os.path.exists(os.path.join(os.environ.get('DQ_CACHE_CARTES', '/tmp/audit_final/sprites/cache'), 'sprite_h193.npy')), 'feuille h193 absente du cache')
class VraieFeuille(unittest.TestCase):
    def test_cases_occupees(self):
        a = np.load(os.path.join(os.environ.get('DQ_CACHE_CARTES', '/tmp/audit_final/sprites/cache'), 'sprite_h193.npy')); g = HD.geometrie_feuille(193, a)
        occ = lambda c, r: bool(a[r * 40:(r + 1) * 40, c * 40:(c + 1) * 40, 3].any())
        for r in range(4): self.assertTrue(all(occ(c, r) for c in range(12)), r)                  # navire : rangees 0 a 3 pleines, la 4e a 8 cases
        self.assertTrue(all(occ(c, 4) for c in range(8))); self.assertFalse(any(occ(c, 4) for c in range(8, 12)))
        for r in range(5, 9): self.assertTrue(all(occ(c, r) for c in range(12)), r)                # sillage : rangees 5 a 8 pleines
        self.assertFalse(any(occ(c, r) for c in range(12) for r in (10, 11)))                      # rien apres la rangee 9 (nl = 10)
        self.assertEqual(g['nl'], 10)


if __name__ == '__main__': unittest.main(verbosity=1)
