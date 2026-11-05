"""Contours des decors de combat (retour de Sylfried, 14 h 08 : « ameliorer visuellement le contour des arbres et montagnes ») : adoucissement de l'alpha binaire des silhouettes (scenery_outlines.py).

Mesures sur des formes synthetiques (pas de moteur ni de GPU) : ecart du contour a la droite ideale, pointes fines conservees, surface, couleur sous les texels transparents ; avec
DQ_CACHE=<cache des cartes> : les 140 decors de combat du jeu (texture traitee seulement si decoupee, surface conservee a 1,5 % pres).

    python3 tools/test_scenery_outlines.py                (DQ_CACHE=... pour les textures reelles)"""
import os, sys, glob, pickle, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.world import scenery_outlines as CD

CACHE = os.environ.get('DQ_CACHE')


def rgba(mask, color=(60, 160, 60)):
    a = np.zeros(mask.shape + (4,), np.uint8)
    a[mask, :3] = color; a[mask, 3] = 255
    return a


def right_spacing(field, slope, base, f=CD.FACTOR):
    """Ecart quadratique moyen (en texels) entre le contour (niveau 0,5) du champ d'alpha et la droite i = pente * j + base, hors des bords."""
    err = []
    for xf in range(8 * f, field.shape[1] - 8 * f):
        col = field[:, xf] - 0.5
        k = np.where((col[:-1] < 0) & (col[1:] >= 0))[0]
        if len(k) == 0: continue
        k = k[0]; y = k + (0 - col[k]) / (col[k + 1] - col[k])
        err.append((y + 0.5) / f - 0.5 - (slope * ((xf + 0.5) / f - 0.5) + base))
    return float(np.sqrt((np.array(err) ** 2).mean()))


class Shapes(unittest.TestCase):
    @staticmethod
    def half_plane(slope, base=20, n=64):
        i, j = np.mgrid[0:n, 0:n]
        return i > slope * j + base

    def test_staircase_stairs_straightened(self):
        m = self.half_plane(0.37)                                      # pente de 1 texel pour 2,7 (flanc de montagne)
        before = right_spacing(CD._bilinear(m.astype(np.float32), CD.FACTOR), 0.37, 20)
        after = right_spacing(CD.softened_alpha(m), 0.37, 20)
        self.assertLess(after, 0.75 * before, (before, after))

    def test_no_slope_is_worsened(self):
        for slope in (0.1, 0.5, 1.0, 2.0):
            m = self.half_plane(slope)
            before = right_spacing(CD._bilinear(m.astype(np.float32), CD.FACTOR), slope, 20)
            after = right_spacing(CD.softened_alpha(m), slope, 20)
            self.assertLessEqual(after, before + 0.01, (slope, before, after))

    def test_a_one_texel_spike_stays_visible(self):
        m = np.zeros((64, 64), bool); m[:, 30] = True               # trait d'un texel de large (brin d'herbe, pointe de sapin)
        al = CD.softened_alpha(m)
        f = CD.FACTOR
        self.assertGreater(al[:, 30 * f + 1:30 * f + 3].max(), 0.8)                     # le coeur du trait reste opaque
        width_px = (al[32 * f, :] >= 0.5).sum() / f                                     # largeur a mi-hauteur, en texels
        self.assertGreater(width_px, 0.6); self.assertLess(width_px, 1.5)

    def test_area_is_preserved(self):
        i, j = np.mgrid[0:64, 0:64]
        disk = (i - 32) ** 2 + (j - 30) ** 2 < 20 ** 2
        al = CD.softened_alpha(disk)
        self.assertLess(abs((al >= 0.5).mean() / disk.mean() - 1), 0.01)

    def test_color_under_transparent_texels(self):
        m = np.zeros((128, 128), bool); m[40:90, 30:100] = True
        output = CD.soften(rgba(m))
        self.assertEqual(output.shape, (512, 512, 4))
        edge = (output[..., 3] > 0) & (output[..., 3] < 255)           # pixels de la rampe d'alpha : couleur du bord, plus de noir
        self.assertTrue(edge.any())
        self.assertGreater(output[edge, 1].min(), 150)                  # vert (60, 160, 60) partout, pas d'assombrissement vers (0, 0, 0)

    def test_inside_keeps_original_filtered_color(self):
        rng = np.random.default_rng(5)
        y, x = np.mgrid[0:128, 0:128]; a = np.empty((128, 128, 4), np.uint8)                       # peinture lisse : degrade + ondulations (comme les textures du jeu)
        for k in range(3): a[..., k] = 128 + 100 * np.sin(x / (6.0 + 3 * k) + y / (9.0 - 2 * k) + k)
        a[..., 3] = 255
        a[:, :20, 3] = 0
        s = CD.soften(a)
        self.assertTrue((s[200:300, 200:300, 3] == 255).all())          # loin du bord : opaque

        def gpu(img, u, v):                                              # filtrage bilineaire du GPU (centres de texels, texture en boucle)
            h, w = img.shape[:2]; x = u * w - 0.5; y = v * h - 0.5
            x0, y0 = int(np.floor(x)), int(np.floor(y)); fx, fy = x - x0, y - y0
            g = lambda yy, xx: img[yy % h, xx % w, :3].astype(np.float32)
            return (g(y0, x0) * (1 - fx) + g(y0, x0 + 1) * fx) * (1 - fy) + (g(y0 + 1, x0) * (1 - fx) + g(y0 + 1, x0 + 1) * fx) * fy
        spacings = [np.abs(gpu(a, u, v) - gpu(s, u, v)).max() for u, v in rng.random((500, 2)) * [0.6, 0.9] + [0.3, 0.05]]
        self.assertLess(float(np.mean(spacings)), 0.7); self.assertLess(max(spacings), 3)


class Choice(unittest.TestCase):
    def test_only_cutout_textures_with_binary_alpha_are_processed(self):
        m = np.zeros((256, 256), bool); m[100:200, 50:200] = True
        self.assertTrue(CD.is_sliced(rgba(m), 12345))
        self.assertFalse(CD.is_sliced(rgba(m), ('tr', 0, 12345)))                       # materiau transparent (melange) : intact
        self.assertFalse(CD.is_sliced(rgba(np.ones((256, 256), bool)), 1))               # sol, ciel : opaques
        self.assertFalse(CD.is_sliced(rgba(np.zeros((256, 256), bool)), 1))              # entierement transparente
        self.assertFalse(CD.is_sliced(rgba(m[:64, :64]), 1))                             # petite texture de motif (grille, torche)
        a = rgba(m); a[110:120, 60:70, 3] = 128                                           # alpha intermediaire : ce n'est pas un decoupage dur
        self.assertTrue(CD.is_sliced(a, 1))                                              # 100 texels sur 65 536 : toujours binaire
        a[:, :, 3] = np.where(m, 128, 0)
        self.assertFalse(CD.is_sliced(a, 1))
        ground = rgba(np.ones((256, 256), bool)); self.assertIs(CD.for_scenery(ground, 1), ground)
        self.assertEqual(CD.for_scenery(rgba(m), 1).shape, (1024, 1024, 4))


@unittest.skipUnless(CACHE and os.path.isdir(CACHE), 'textures reelles : DQ_CACHE=<cache des cartes>')
class Real(unittest.TestCase):
    def test_all_battle_scenery(self):
        processed = 0
        for f in sorted(glob.glob(os.path.join(CACHE, 'carte10_btl*.pkl'))):
            with open(f, 'rb') as fh: c = pickle.load(fh)
            for lookup_key, t in c['textures'].items():
                if lookup_key not in c['groupes'] or not CD.is_sliced(t, lookup_key): continue
                s = CD.soften(t); processed += 1
                self.assertEqual(s.shape[:2], (t.shape[0] * 4, t.shape[1] * 4))
                area = ((s[..., 3] >= 128).mean() / (t[..., 3] >= 128).mean() - 1)
                self.assertLess(abs(area), 0.015, '%s : surface %+.2f %%' % (os.path.basename(f), 100 * area))
        self.assertGreater(processed, 30)


if __name__ == '__main__': unittest.main()
