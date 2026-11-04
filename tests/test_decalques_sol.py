"""Decalques plats poses au sol (chemins de pierres, fleurs, herbes, taches de terre...) : hauteur au-dessus du sol dans les DONNEES du jeu (cartes extraites par `donnees.py`, cache `carte10_*.pkl`).

Constat (enquete #45, « les pierres flottent ») : les shaders de decor du jeu (`Custom/fld_normal`, `fld_atest`, `fld_trans`) n'ont AUCUN `Offset` de profondeur ; les concepteurs separent les couches
par la geometrie : chaque couche de decalques est posee 0,125 unite (1/8) au-dessus de celle d'en dessous (village `maout` : herbe y = -0,25, terre et pierres y = -0,125). Ce test garde cette mesure :
si l'extraction (signe de y, matrices, cache) changeait, la regle ne se verrait plus et il echouerait. Il ne teste PAS le rendu.

    DQ_CACHE_CARTES=<dossier des carte10_*.pkl> python3 outils/test_decalques_sol.py
"""
import os, pickle, sys, unittest

import numpy as np

CACHE = os.environ.get('DQ_CACHE_CARTES', '')
PAS = 0.125            # unite de superposition des couches de decor


def hauteurs_au_dessus_du_sol(c):
    """Pour chaque triangle plat DECOUPE (alpha < 250 quelque part dans sa texture) hors groupes transparents ('tr') : hauteur au-dessus du triangle de sol OPAQUE (texture sans aucun alpha < 250) le plus
    haut qui est dessous (meme x, z). -> (liste des hauteurs, nombre de decalques sans sol dessous, nombre de decalques tournes vers le bas)."""
    g, T = c['groupes'], c['textures']
    tris, cut, tr = [], [], []
    for k, (pos, uv, col) in g.items():
        t = T.get(k)
        if t is None: continue
        P = np.asarray(pos).reshape(-1, 3, 3); tris.append(P)
        cut += [bool((t[..., 3] < 250).any())] * len(P); tr += [isinstance(k, tuple) and k[0] == 'tr'] * len(P)
    P = np.concatenate(tris); cut = np.array(cut); tr = np.array(tr)
    plat = (P[..., 1].max(1) - P[..., 1].min(1)) < 1e-3
    A = (P[:, 1, 0] - P[:, 0, 0]) * (P[:, 2, 2] - P[:, 0, 2]) - (P[:, 2, 0] - P[:, 0, 0]) * (P[:, 1, 2] - P[:, 0, 2])          # < 0 : horaire vu de dessus = face avant d'Unity (Cull Back)
    dec = np.nonzero(plat & cut & ~tr)[0]
    ax, az, bx, bz, cx, cz = P[:, 0, 0], P[:, 0, 2], P[:, 1, 0], P[:, 1, 2], P[:, 2, 0], P[:, 2, 2]
    det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz); ok = np.abs(det) > 1e-9; ds = np.where(ok, det, 1.0)
    h, sans = [], 0
    for d in dec:
        q = P[d].mean(0)
        l0 = ((bz - cz) * (q[0] - cx) + (cx - bx) * (q[2] - cz)) / ds; l1 = ((cz - az) * (q[0] - cx) + (ax - cx) * (q[2] - cz)) / ds; l2 = 1 - l0 - l1
        m = ok & (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6); m[d] = False
        y = l0 * P[:, 0, 1] + l1 * P[:, 1, 1] + l2 * P[:, 2, 1]
        dessous = m & (y <= q[1] + 1e-4) & ~cut
        if dessous.any(): h.append(float(q[1] - y[dessous].max()))
        else: sans += 1
    return np.array(h), sans, int((A[dec] > 1e-9).sum())


@unittest.skipUnless(os.path.exists(os.path.join(CACHE, 'carte10_maout.pkl')), 'DQ_CACHE_CARTES (carte10_maout.pkl) absent')
class DecalquesAuSol(unittest.TestCase):
    def carte(self, nom):
        with open(os.path.join(CACHE, 'carte10_%s.pkl' % nom), 'rb') as f: return pickle.load(f)

    def test_maout_pierres_a_un_huitieme_au_dessus_de_l_herbe(self):
        c = self.carte('maout'); h, sans, bas = hauteurs_au_dessus_du_sol(c)
        self.assertGreater(len(h), 300)
        self.assertGreater(np.mean(np.abs(h - PAS) < 0.002), 0.25)                        # la couche la plus frequente : exactement 0,125 (pierres, terre, fleurs sur l'herbe)
        mult = np.abs(h / PAS - np.round(h / PAS)) * PAS < 0.002
        self.assertGreater(np.mean(mult & (h > 0.01)), 0.5)                                # la plupart des decalques sont a un multiple de 0,125 au-dessus du sol
        self.assertLess(np.mean(h < 0.02), 0.03)                                           # presque aucun decalque coplanaire avec le sol (le jeu n'a pas de decalage de profondeur)
        self.assertEqual(bas, 0)                                                           # tous tournes vers le haut : le Cull Back d'Unity ne cache aucun decalque

    def test_pierres_du_chemin(self):
        """Objet `020_mast1` (dallage du village : pierres `maisiyk1..4`, terre `sn02` / `najimi02`, bassin `r_mizu02`, textures 32 x 32 ou 64 x 64) : toutes ses surfaces plates sont a y = -0,125 ;
        l'herbe `masiba` (objet `018_maoutsb1`) en dessous : y = -0,25."""
        c = self.carte('maout'); g = c['groupes']
        def tranches(nom): return [(key, np.asarray(g[key][0])[deb:deb + n]) for i, pl in c['plages'].items() if c['noms'].get(i) == nom for key, deb, n in pl]      # (groupe, sommets de CET objet)
        dalles = tranches('020_mast1'); herbe = tranches('018_maoutsb1')
        self.assertGreaterEqual(len(dalles), 7, [k for k, _ in dalles]); self.assertEqual(len(herbe), 3)
        for k, V in dalles: self.assertLess(np.abs(V[:, 1] + 0.125).max(), 1e-3, k)         # tous les sommets de l'objet a -0,125 (surfaces plates)
        for k, V in herbe: self.assertLess(np.abs(V[:, 1] + 0.25).max(), 1e-3, k)

if __name__ == '__main__':
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    unittest.main()
