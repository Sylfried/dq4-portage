"""Test des copies de ciel de `dpout` et `ev09` (MAP-05 : ciel prolonge de part et d'autre ; logique pure : sans fenetre, sans moteur, sans APK) :

  1. `title_sky.cloned_positions` : un `dx` nombre decale x (copies du ciel du titre, comme avant) ; `('miroir', xe)` est une symetrie par rapport au plan x = xe (les points du bord ne bougent pas, y et z intacts, symetrie
     deux fois appliquee = identite), le tableau d'origine n'est pas modifie, float32 conserve ;
  2. copie symetrique d'un plan de ciel : elle touche l'original par son bord (aucun trou, aucun chevauchement) et le plan etendu (copie gauche + original + copie droite) couvre trois fois sa largeur, a la meme profondeur ;
  3. `EXTENDED_SKIES` : `dpout` (plan `dpoutenk`) et `ev09` (plan `e9km1`) ; l'ecran-titre garde son traitement propre.

    python3 tests/test_extended_sky.py
"""
import os, sys, unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.render import title_sky as CT


def plan(xmin=-9.1, xmax=17.9, y0=0.0, y1=10.0, z=2.4):
    """Plan de ciel type (deux triangles ; pas de la geometrie reelle, seulement sa forme : un rectangle vertical)."""
    return np.array([[xmin, y0, z], [xmin, y1, z], [xmax, y1, z], [xmin, y0, z], [xmax, y1, z], [xmax, y0, z]], np.float32)


class ClonePositions(unittest.TestCase):
    def test_offset_by_a_number(self):
        p = plan(); q = CT.cloned_positions(p, 5.0)
        np.testing.assert_allclose(q[:, 0], p[:, 0] + 5.0, atol=1e-6)
        np.testing.assert_array_equal(q[:, 1:], p[:, 1:])

    def test_mirror_keeps_edge(self):
        p = plan(); xe = float(p[:, 0].min()); q = CT.cloned_positions(p, ('miroir', xe))
        np.testing.assert_allclose(q[p[:, 0] == xe, 0], xe, atol=1e-6)         # les points du bord ne bougent pas
        np.testing.assert_allclose(q[:, 0], 2 * xe - p[:, 0], atol=1e-5)
        np.testing.assert_array_equal(q[:, 1:], p[:, 1:])

    def test_mirror_twice_gives_origin(self):
        p = plan(); xe = 3.7
        np.testing.assert_allclose(CT.cloned_positions(CT.cloned_positions(p, ('miroir', xe)), ('miroir', xe)), p, atol=1e-5)

    def test_intact_origin_and_float32(self):
        p = plan(); copied = p.copy()
        for dx in (4.0, ('miroir', 1.0)):
            q = CT.cloned_positions(p, dx); self.assertEqual(q.dtype, np.float32)
            np.testing.assert_array_equal(p, copied)


class ExtendedPlane(unittest.TestCase):
    def test_three_widths_without_gap_or_overlap(self):
        p = plan(); xmin, xmax = float(p[:, 0].min()), float(p[:, 0].max()); wid = xmax - xmin
        g = CT.cloned_positions(p, ('miroir', xmin)); d = CT.cloned_positions(p, ('miroir', xmax))
        self.assertAlmostEqual(float(g[:, 0].max()), xmin, places=4)                  # la copie gauche finit la ou l'original commence
        self.assertAlmostEqual(float(d[:, 0].min()), xmax, places=4)                  # la copie droite commence la ou il finit
        self.assertAlmostEqual(float(g[:, 0].min()), xmin - wid, places=4)
        self.assertAlmostEqual(float(d[:, 0].max()), xmax + wid, places=4)
        np.testing.assert_array_equal(g[:, 2], p[:, 2]); np.testing.assert_array_equal(d[:, 2], p[:, 2])       # meme profondeur : aucun plan incline


class Constants(unittest.TestCase):
    def test_maps_and_planes(self):
        from dq4_pc.window import constants as C
        self.assertEqual(C.EXTENDED_SKIES['dpout'], ('dpoutenk',))
        self.assertEqual(C.EXTENDED_SKIES['ev09'], ('e9km1',))
        self.assertNotIn(C.TITLE_MAP, C.EXTENDED_SKIES)             # le titre a son propre ciel (`_title_sky`)


if __name__ == '__main__':
    unittest.main(verbosity=2)
