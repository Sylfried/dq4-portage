"""Test des copies de ciel de `dpout` et `ev09` (MAP-05 : ciel prolonge de part et d'autre ; logique pure : sans fenetre, sans moteur, sans APK) :

  1. `ciel_titre.positions_copie` : un `dx` nombre decale x (copies du ciel du titre, comme avant) ; `('miroir', xe)` est une symetrie par rapport au plan x = xe (les points du bord ne bougent pas, y et z intacts, symetrie
     deux fois appliquee = identite), le tableau d'origine n'est pas modifie, float32 conserve ;
  2. copie symetrique d'un plan de ciel : elle touche l'original par son bord (aucun trou, aucun chevauchement) et le plan etendu (copie gauche + original + copie droite) couvre trois fois sa largeur, a la meme profondeur ;
  3. `CIELS_ETENDUS` : `dpout` (plan `dpoutenk`) et `ev09` (plan `e9km1`) ; l'ecran-titre garde son traitement propre.

    python3 tests/test_ciel_etendu.py
"""
import os, sys, unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.rendu import ciel_titre as CT


def plan(xmin=-9.1, xmax=17.9, y0=0.0, y1=10.0, z=2.4):
    """Plan de ciel type (deux triangles ; pas de la geometrie reelle, seulement sa forme : un rectangle vertical)."""
    return np.array([[xmin, y0, z], [xmin, y1, z], [xmax, y1, z], [xmin, y0, z], [xmax, y1, z], [xmax, y0, z]], np.float32)


class PositionsCopie(unittest.TestCase):
    def test_decalage_par_un_nombre(self):
        p = plan(); q = CT.positions_copie(p, 5.0)
        np.testing.assert_allclose(q[:, 0], p[:, 0] + 5.0, atol=1e-6)
        np.testing.assert_array_equal(q[:, 1:], p[:, 1:])

    def test_miroir_garde_le_bord(self):
        p = plan(); xe = float(p[:, 0].min()); q = CT.positions_copie(p, ('miroir', xe))
        np.testing.assert_allclose(q[p[:, 0] == xe, 0], xe, atol=1e-6)         # les points du bord ne bougent pas
        np.testing.assert_allclose(q[:, 0], 2 * xe - p[:, 0], atol=1e-5)
        np.testing.assert_array_equal(q[:, 1:], p[:, 1:])

    def test_miroir_deux_fois_donne_l_origine(self):
        p = plan(); xe = 3.7
        np.testing.assert_allclose(CT.positions_copie(CT.positions_copie(p, ('miroir', xe)), ('miroir', xe)), p, atol=1e-5)

    def test_origine_intacte_et_float32(self):
        p = plan(); copie = p.copy()
        for dx in (4.0, ('miroir', 1.0)):
            q = CT.positions_copie(p, dx); self.assertEqual(q.dtype, np.float32)
            np.testing.assert_array_equal(p, copie)


class PlanEtendu(unittest.TestCase):
    def test_trois_largeurs_sans_trou_ni_chevauchement(self):
        p = plan(); xmin, xmax = float(p[:, 0].min()), float(p[:, 0].max()); larg = xmax - xmin
        g = CT.positions_copie(p, ('miroir', xmin)); d = CT.positions_copie(p, ('miroir', xmax))
        self.assertAlmostEqual(float(g[:, 0].max()), xmin, places=4)                  # la copie gauche finit la ou l'original commence
        self.assertAlmostEqual(float(d[:, 0].min()), xmax, places=4)                  # la copie droite commence la ou il finit
        self.assertAlmostEqual(float(g[:, 0].min()), xmin - larg, places=4)
        self.assertAlmostEqual(float(d[:, 0].max()), xmax + larg, places=4)
        np.testing.assert_array_equal(g[:, 2], p[:, 2]); np.testing.assert_array_equal(d[:, 2], p[:, 2])       # meme profondeur : aucun plan incline


class Constantes(unittest.TestCase):
    def test_cartes_et_plans(self):
        from dq4_pc.fenetre import constantes as C
        self.assertEqual(C.CIELS_ETENDUS['dpout'], ('dpoutenk',))
        self.assertEqual(C.CIELS_ETENDUS['ev09'], ('e9km1',))
        self.assertNotIn(C.CARTE_TITRE, C.CIELS_ETENDUS)             # le titre a son propre ciel (`_ciel_titre`)


if __name__ == '__main__':
    unittest.main(verbosity=2)
