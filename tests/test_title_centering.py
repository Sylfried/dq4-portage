"""Test du centrage de l'ecran-titre sur le RENDU reel (retour de 22 h 29 : « pourquoi le logo et le decor ne sont plus centres ? »).

La visionneuse est lancee (moteur d'origine, rendu Mesa sans ecran ; avant la correction, les bornes 16/9 de la carte glissaient la camera du titre de 4,5 unites quand l'option « Centrer la camera »
sur le joueur etait sur Non, option supprimee depuis) a trois formats (16:9 de 1430 x 815, 4:3, 21:9), et on mesure sur la capture de l'image 700 (dragon au-dessus du logo, avant « Touchez l'ecran ») :
  1. le barycentre du logo (pixels rouge-violet du lettrage) est au milieu de la fenetre, a quelques pixels pres : decalage horizontal / hauteur de la fenetre < 0,03 (avant la correction : 0,29) ;
  2. ce decalage est le meme (a 0,004 pres) a tous les formats : le placement du logo est celui du jeu pour le cadre portrait central, quel que soit le format de la fenetre ;
  3. pas de bande noire dissymetrique : les 8 colonnes de chaque bord ne contiennent aucun pixel noir (le ciel remplit toute la fenetre) ;
  4. le chateau (ile orange) est a droite du logo, a la meme distance (en hauteur de fenetre, a 0,01 pres) a tous les formats.

    python3 tools/test_title_centering.py --apk "<dossier des APK patches>" --saves "<dossier des sauvegardes>" --cache "<dossier du cache d'interface, avec ui_layout.json>"
(ou les variables DQ_APK, DQ_SAVES, DQ_UICACHE ; sans elles les tests sont ignores). Un test dure environ 40 s par format ; a lancer par `tools/session_flow/engine_slot.sh`.
"""
import argparse, json, os, subprocess, sys, tempfile, unittest

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FORMATS = ((1430, 815), (1024, 768), (2560, 1080))
FRAME = 700
ARGS = None; REST = sys.argv[1:]
if __name__ == '__main__':
    _ap = argparse.ArgumentParser(); _ap.add_argument('--apk'); _ap.add_argument('--saves'); _ap.add_argument('--cache')
    _a, REST = _ap.parse_known_args()
    if _a.apk and _a.saves and _a.cache: ARGS = _a


def mesures(path):
    """(decalage horizontal du logo, ecart logo -> ile, colonnes noires de bord), en hauteurs de fenetre / pixels."""
    a = np.asarray(Image.open(path).convert('RGB')).astype(int); h, w = a.shape[:2]; R, G, B = a[..., 0], a[..., 1], a[..., 2]
    logo = (R > 170) & (G < 60) & (B > 40) & (B < 140) & (R - B > 70)             # lettrage rouge-violet du logo
    island = (R > 200) & (G > 80) & (G < 150) & (B < 70) & (R - B > 150)             # dessous orange de l'ile du chateau
    island[:int(0.66 * h)] = False                                                    # (l'ile est dans le tiers bas ; plus haut, des ailes de dragon et des bords dores du logo sont aussi orange)
    yl, xl = np.nonzero(logo); yi, xi = np.nonzero(island)
    if len(xl) < 500 or len(xi) < 200: return None
    black = int(((a[:, :8].sum(axis=2) < 12).sum()) + ((a[:, -8:].sum(axis=2) < 12).sum()))
    return (xl.mean() - w / 2) / h, (xi.mean() - xl.mean()) / h, black


@unittest.skipIf(ARGS is None and not (os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES') and os.environ.get('DQ_UICACHE')), 'moteur d\'origine : --apk, --saves et --cache requis')
class TitleCentering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        apk = ARGS.apk if ARGS else os.environ['DQ_APK']; saves = ARGS.saves if ARGS else os.environ['DQ_SAVES']; cache = ARGS.cache if ARGS else os.environ['DQ_UICACHE']
        cls.tmp = tempfile.mkdtemp(prefix='titre_centrage_'); rg = os.path.join(cls.tmp, 'reglages.json')
        json.dump({}, open(rg, 'w'))             # reglages par defaut (l'option « Centrer la camera » n'existe plus : la camera est toujours centree, le titre en est exempte)
        env = dict(os.environ, PYGLET_HEADLESS='1', PYGLET_AUDIO='silent'); cls.res = {}
        for (w, h) in FORMATS:
            shot = os.path.join(cls.tmp, 'titre_%dx%d.png' % (w, h))
            cmd = [sys.executable, '-W', 'ignore', '-m', 'dq4_pc', '--apk', apk, '--saves-lecture', saves, '--saves-ecriture', os.path.join(cls.tmp, 'sv'), '--reglages', rg, '--slot', '0', '--sans-logos',
                   '--cache', cache, '--msaa', '0', '--largeur', str(w), '--hauteur', str(h), '--sans-preparation', '--sans-son', '--shot', shot, '--images', '100000', '--touches-test', '', '--shots-boucle', str(FRAME)]
            subprocess.run(cmd, cwd=os.path.join(HERE, '..'), env=env, timeout=900, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cls.res[(w, h)] = mesures(os.path.join(cls.tmp, 'titre_%dx%d_b%d.png' % (w, h, FRAME)))

    def test_screenshot_taken_at_each_format(self):
        for f in FORMATS: self.assertIsNotNone(self.res[f], 'logo ou ile introuvable sur la capture %dx%d' % f)

    def test_logo_in_the_middle(self):
        for f in FORMATS: self.assertLess(abs(self.res[f][0]), 0.03, 'barycentre du logo decentre a %dx%d : %.3f hauteurs' % (f + (self.res[f][0],)))

    def test_same_placement_at_all_formats(self):
        d = [self.res[f][0] for f in FORMATS]; self.assertLess(max(d) - min(d), 0.004, d)

    def test_no_black_band_at_edges(self):
        for f in FORMATS: self.assertEqual(self.res[f][2], 0, 'pixels noirs aux bords a %dx%d' % f)

    def test_island_right_of_logo_same_distance(self):
        e = [self.res[f][1] for f in FORMATS]
        for x in e: self.assertGreater(x, 0.05)
        self.assertLess(max(e) - min(e), 0.01, e)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + REST)
