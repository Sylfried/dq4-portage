"""Contours des decors de combat (retour de Sylfried, 14 h 08 : « ameliorer visuellement le contour des arbres et montagnes ») : adoucissement de l'alpha binaire des silhouettes (contours_decor.py).

Mesures sur des formes synthetiques (pas de moteur ni de GPU) : ecart du contour a la droite ideale, pointes fines conservees, surface, couleur sous les texels transparents ; avec
DQ_CACHE=<cache des cartes> : les 140 decors de combat du jeu (texture traitee seulement si decoupee, surface conservee a 1,5 % pres).

    python3 outils/test_contours_decor.py                (DQ_CACHE=... pour les textures reelles)"""
import os, sys, glob, pickle, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.monde import contours_decor as CD

CACHE = os.environ.get('DQ_CACHE')


def rgba(masque, couleur=(60, 160, 60)):
    a = np.zeros(masque.shape + (4,), np.uint8)
    a[masque, :3] = couleur; a[masque, 3] = 255
    return a


def ecart_droite(champ, pente, base, f=CD.FACTEUR):
    """Ecart quadratique moyen (en texels) entre le contour (niveau 0,5) du champ d'alpha et la droite i = pente * j + base, hors des bords."""
    err = []
    for xf in range(8 * f, champ.shape[1] - 8 * f):
        col = champ[:, xf] - 0.5
        k = np.where((col[:-1] < 0) & (col[1:] >= 0))[0]
        if len(k) == 0: continue
        k = k[0]; y = k + (0 - col[k]) / (col[k + 1] - col[k])
        err.append((y + 0.5) / f - 0.5 - (pente * ((xf + 0.5) / f - 0.5) + base))
    return float(np.sqrt((np.array(err) ** 2).mean()))


class Formes(unittest.TestCase):
    @staticmethod
    def demi_plan(pente, base=20, n=64):
        i, j = np.mgrid[0:n, 0:n]
        return i > pente * j + base

    def test_les_marches_d_escalier_sont_redressees(self):
        m = self.demi_plan(0.37)                                      # pente de 1 texel pour 2,7 (flanc de montagne)
        avant = ecart_droite(CD._bilineaire(m.astype(np.float32), CD.FACTEUR), 0.37, 20)
        apres = ecart_droite(CD.alpha_adouci(m), 0.37, 20)
        self.assertLess(apres, 0.75 * avant, (avant, apres))

    def test_aucune_pente_n_est_aggravee(self):
        for pente in (0.1, 0.5, 1.0, 2.0):
            m = self.demi_plan(pente)
            avant = ecart_droite(CD._bilineaire(m.astype(np.float32), CD.FACTEUR), pente, 20)
            apres = ecart_droite(CD.alpha_adouci(m), pente, 20)
            self.assertLessEqual(apres, avant + 0.01, (pente, avant, apres))

    def test_une_pointe_d_un_texel_reste_visible(self):
        m = np.zeros((64, 64), bool); m[:, 30] = True               # trait d'un texel de large (brin d'herbe, pointe de sapin)
        al = CD.alpha_adouci(m)
        f = CD.FACTEUR
        self.assertGreater(al[:, 30 * f + 1:30 * f + 3].max(), 0.8)                     # le coeur du trait reste opaque
        largeur = (al[32 * f, :] >= 0.5).sum() / f                                     # largeur a mi-hauteur, en texels
        self.assertGreater(largeur, 0.6); self.assertLess(largeur, 1.5)

    def test_la_surface_est_conservee(self):
        i, j = np.mgrid[0:64, 0:64]
        disque = (i - 32) ** 2 + (j - 30) ** 2 < 20 ** 2
        al = CD.alpha_adouci(disque)
        self.assertLess(abs((al >= 0.5).mean() / disque.mean() - 1), 0.01)

    def test_couleur_sous_les_texels_transparents(self):
        m = np.zeros((128, 128), bool); m[40:90, 30:100] = True
        sortie = CD.adoucir(rgba(m))
        self.assertEqual(sortie.shape, (512, 512, 4))
        bord = (sortie[..., 3] > 0) & (sortie[..., 3] < 255)           # pixels de la rampe d'alpha : couleur du bord, plus de noir
        self.assertTrue(bord.any())
        self.assertGreater(sortie[bord, 1].min(), 150)                  # vert (60, 160, 60) partout, pas d'assombrissement vers (0, 0, 0)

    def test_l_interieur_garde_la_couleur_d_origine_filtree(self):
        rng = np.random.default_rng(5)
        y, x = np.mgrid[0:128, 0:128]; a = np.empty((128, 128, 4), np.uint8)                       # peinture lisse : degrade + ondulations (comme les textures du jeu)
        for k in range(3): a[..., k] = 128 + 100 * np.sin(x / (6.0 + 3 * k) + y / (9.0 - 2 * k) + k)
        a[..., 3] = 255
        a[:, :20, 3] = 0
        s = CD.adoucir(a)
        self.assertTrue((s[200:300, 200:300, 3] == 255).all())          # loin du bord : opaque

        def gpu(img, u, v):                                              # filtrage bilineaire du GPU (centres de texels, texture en boucle)
            h, w = img.shape[:2]; x = u * w - 0.5; y = v * h - 0.5
            x0, y0 = int(np.floor(x)), int(np.floor(y)); fx, fy = x - x0, y - y0
            g = lambda yy, xx: img[yy % h, xx % w, :3].astype(np.float32)
            return (g(y0, x0) * (1 - fx) + g(y0, x0 + 1) * fx) * (1 - fy) + (g(y0 + 1, x0) * (1 - fx) + g(y0 + 1, x0 + 1) * fx) * fy
        ecarts = [np.abs(gpu(a, u, v) - gpu(s, u, v)).max() for u, v in rng.random((500, 2)) * [0.6, 0.9] + [0.3, 0.05]]
        self.assertLess(float(np.mean(ecarts)), 0.7); self.assertLess(max(ecarts), 3)


class Choix(unittest.TestCase):
    def test_seules_les_textures_decoupees_a_alpha_binaire_sont_traitees(self):
        m = np.zeros((256, 256), bool); m[100:200, 50:200] = True
        self.assertTrue(CD.est_decoupe(rgba(m), 12345))
        self.assertFalse(CD.est_decoupe(rgba(m), ('tr', 0, 12345)))                       # materiau transparent (melange) : intact
        self.assertFalse(CD.est_decoupe(rgba(np.ones((256, 256), bool)), 1))               # sol, ciel : opaques
        self.assertFalse(CD.est_decoupe(rgba(np.zeros((256, 256), bool)), 1))              # entierement transparente
        self.assertFalse(CD.est_decoupe(rgba(m[:64, :64]), 1))                             # petite texture de motif (grille, torche)
        a = rgba(m); a[110:120, 60:70, 3] = 128                                           # alpha intermediaire : ce n'est pas un decoupage dur
        self.assertTrue(CD.est_decoupe(a, 1))                                              # 100 texels sur 65 536 : toujours binaire
        a[:, :, 3] = np.where(m, 128, 0)
        self.assertFalse(CD.est_decoupe(a, 1))
        sol = rgba(np.ones((256, 256), bool)); self.assertIs(CD.pour_decor(sol, 1), sol)
        self.assertEqual(CD.pour_decor(rgba(m), 1).shape, (1024, 1024, 4))


@unittest.skipUnless(CACHE and os.path.isdir(CACHE), 'textures reelles : DQ_CACHE=<cache des cartes>')
class Reelles(unittest.TestCase):
    def test_tous_les_decors_de_combat(self):
        traitees = 0
        for f in sorted(glob.glob(os.path.join(CACHE, 'carte10_btl*.pkl'))):
            with open(f, 'rb') as fh: c = pickle.load(fh)
            for cle, t in c['textures'].items():
                if cle not in c['groupes'] or not CD.est_decoupe(t, cle): continue
                s = CD.adoucir(t); traitees += 1
                self.assertEqual(s.shape[:2], (t.shape[0] * 4, t.shape[1] * 4))
                aire = ((s[..., 3] >= 128).mean() / (t[..., 3] >= 128).mean() - 1)
                self.assertLess(abs(aire), 0.015, '%s : surface %+.2f %%' % (os.path.basename(f), 100 * aire))
        self.assertGreater(traitees, 30)


if __name__ == '__main__': unittest.main()
