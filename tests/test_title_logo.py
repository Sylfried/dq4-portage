"""Test du logo et du sous-titre de l'ecran-titre agrandis 1,5 fois (issue #108 ; d'abord 2 fois, ramene a 1,5 le 03/11/2026 a 21 h 05 ; ECART VOULU avec l'APK : demande de Sylfried du 03/11/2026).

Partie 1 (sans moteur) : les fonctions pures de `pre_game` (`upscale_logo`, `logo_factor`) : x et y sont multiplies autour d'un point fixe, la profondeur ne change pas, le facteur est reduit
dans une fenetre trop etroite (le logo ne deborde jamais) et ne descend jamais sous 1.

Partie 2 (rendu reel, Mesa sans ecran) : la visionneuse est lancee avec le moteur d'origine a 16:9, 16:10, 4:3 et 21:9, a l'image 770 (logo, sous-titre, « Touchez l'ecran » au maximum de son clignotement),
et une fois avec DQ_LOGO_ECHELLE=1 (le logo de l'APK, a 16:9) pour comparer. On mesure sur les captures :
  1. la largeur du lettrage « DRAGON QUEST » (pixels rouge-violet) vaut 1,5 fois celle de l'APK (a 3 % pres), a tous les formats (en hauteurs de fenetre) ;
  2. le logo reste dans la fenetre (aucun pixel du lettrage sur les 1 % de bord) ;
  3. le bas du « IV » reste au-dessus du haut de « Touchez l'ecran » (zone calculee comme `Game._ui_reference` : 228 unites sous le centre, hauteur 41,48, echelle H / 800 x UI_ZOOM) d'au moins 2 % de la hauteur ;
  4. le haut du logo reste dans la fenetre (a plus de 5 % du bord haut) ;
  5. le logo est centre horizontalement (a 1 % de la largeur pres).

    python3 tools/test_title_logo.py --apk "<dossier des APK patches>" --saves "<dossier des sauvegardes>" --cache "<dossier du cache d'interface, avec ui_layout.json et ap_taptostart.png>"
(ou les variables DQ_APK, DQ_SAVES, DQ_UICACHE ; sans elles seule la partie 1 tourne). La partie 2 dure environ 2 minutes ; a lancer par `tools/session_flow/engine_slot.sh`.
"""
import argparse, json, os, re, subprocess, sys, tempfile, unittest

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
from dq4_pc.menus import pre_game as AP

FORMATS = ((1280, 720), (1280, 800), (1024, 768), (2560, 1080))              # 16:9, 16:10, 4:3, 21:9
FRAME = 770
ARGS = None; REST = sys.argv[1:]
if __name__ == '__main__':
    _ap = argparse.ArgumentParser(); _ap.add_argument('--apk'); _ap.add_argument('--saves'); _ap.add_argument('--cache')
    _a, REST = _ap.parse_known_args()
    if _a.apk and _a.saves and _a.cache: ARGS = _a


class Functions(unittest.TestCase):
    def test_upscale_x_and_y_around_fixed_point(self):
        loc = np.array([[-4.5, 0.8, 0.0], [4.5, 3.7, 0.0], [-1.4, -0.87, 0.062]], np.float32)
        r = AP.upscale_logo(loc, 2.0, 0.7)
        np.testing.assert_allclose(r[:, 0], loc[:, 0] * 2.0, atol=1e-5)
        np.testing.assert_allclose(r[:, 1], 0.7 + 2.0 * (loc[:, 1] - 0.7), atol=1e-5)
        np.testing.assert_array_equal(r[:, 2], loc[:, 2])                            # profondeur (ordre des couches) inchangee
        self.assertEqual(float(loc[0, 0]), -4.5)                                    # l'entree n'est pas modifiee

    def test_fixed_point_does_not_move(self):
        r = AP.upscale_logo(np.array([[0.0, 0.7, 0.0]], np.float32), 2.0, 0.7)
        self.assertAlmostEqual(float(r[0, 1]), 0.7, places=5); self.assertAlmostEqual(float(r[0, 0]), 0.0, places=5)

    def test_wanted_factor_when_window_wide_enough(self):
        for wid in (0.1, 0.25, 0.40, 0.60): self.assertEqual(AP.logo_factor(wid), 1.5)

    def test_factor_reduced_in_narrow_window(self):
        for wid in (0.7, 0.8, 0.9):
            f = AP.logo_factor(wid); self.assertLess(f, 1.5); self.assertGreaterEqual(f, 1.0); self.assertLessEqual(f * wid, AP.LOGO_WIDTH_MARGIN + 1e-9)             # le logo agrandi tient dans 96 % de la largeur
        self.assertEqual(AP.logo_factor(1.2), 1.0)                                  # jamais plus petit que l'APK, meme si le logo d'origine deborde deja

    def test_factor_without_measure(self):
        self.assertEqual(AP.logo_factor(0.0), 1.5)

    def test_constants(self):
        self.assertEqual(AP.LOGO_SCALE, 1.5); self.assertEqual(set(AP.LOGO_MODELS), {8900, 8901})              # 8901 : logo + sous-titre ; 8900 : eclat anime


def mesures(path):
    """Dict : largeur du lettrage (en hauteurs de fenetre), x0 / x1 / y0 (fractions de la fenetre), bas du « IV » (fraction de la hauteur, bande centrale), largeur / hauteur."""
    a = np.asarray(Image.open(path).convert('RGB')).astype(int); h, w = a.shape[:2]; R, G, B = a[..., 0], a[..., 1], a[..., 2]
    letters = (R > 170) & (G < 60) & (B > 40) & (B < 140) & (R - B > 70)             # lettrage rouge-violet de « DRAGON QUEST »
    yl, xl = np.nonzero(letters)
    if len(xl) < 500: return None
    golden = (R > 190) & (G > 90) & (G < 200) & (B < 90) & (R - B > 130)                # or du « IV »
    band = np.zeros_like(golden); band[:, int(w / 2 - 0.07 * h):int(w / 2 + 0.07 * h)] = True       # bande centrale : le « IV » seul (l'ile du chateau commence plus a droite)
    band[:int(0.3 * h)] = False
    yi, _ = np.nonzero(golden & band)
    return dict(w=w, h=h, larg_h=(xl.max() - xl.min()) / h, x0=xl.min() / w, x1=xl.max() / w, y0=yl.min() / h, iv_bas=(yi.max() / h if len(yi) else None), centre=((xl.min() + xl.max()) / 2 - w / 2) / w)


def prompt_top(ui_zoom):
    """Haut de « Touchez l'ecran » en fraction de la hauteur de la fenetre : centre 228 unites sous le centre de l'ecran, hauteur 41,48, echelle H / 800 x UI_ZOOM (Game._ui_reference, titre sans fenetre ouverte)."""
    return 0.5 + (AP.TT_BOTTOM - AP.TT_H / 2) * ui_zoom / 800.0


@unittest.skipIf(ARGS is None and not (os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES') and os.environ.get('DQ_UICACHE')), 'moteur d\'origine : --apk, --saves et --cache requis')
class TitleRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        apk = ARGS.apk if ARGS else os.environ['DQ_APK']; saves = ARGS.saves if ARGS else os.environ['DQ_SAVES']; cache = ARGS.cache if ARGS else os.environ['DQ_UICACHE']
        src = _paths.source('window.py'); cls.zoom = float(re.search(r'^UI_ZOOM = ([0-9.]+)', src, re.M).group(1))
        cls.tmp = tempfile.mkdtemp(prefix='titre_logo_'); rg = os.path.join(cls.tmp, 'reglages.json'); json.dump({}, open(rg, 'w'))
        def launch(w, h, name_str, extra_env):
            shot = os.path.join(cls.tmp, name_str + '.png')
            cmd = [sys.executable, '-W', 'ignore', '-m', 'dq4_pc', '--apk', apk, '--saves-lecture', saves, '--saves-ecriture', os.path.join(cls.tmp, 'sv'), '--reglages', rg, '--slot', '0', '--sans-logos',
                   '--cache', cache, '--msaa', '0', '--largeur', str(w), '--hauteur', str(h), '--sans-preparation', '--sans-son', '--shot', shot, '--images', '100000', '--touches-test', '', '--shots-boucle', str(FRAME)]
            env = dict(os.environ, PYGLET_HEADLESS='1', PYGLET_AUDIO='silent', **extra_env)
            subprocess.run(cmd, cwd=os.path.join(HERE, '..'), env=env, timeout=900, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return mesures(os.path.join(cls.tmp, '%s_b%d.png' % (name_str, FRAME)))
        cls.origin = launch(1280, 720, 'origine', {'DQ_LOGO_ECHELLE': '1'})
        cls.res = {f: launch(f[0], f[1], 'titre_%dx%d' % f, {}) for f in FORMATS}

    def test_screenshots_taken(self):
        self.assertIsNotNone(self.origin, 'lettrage introuvable sur la capture de l\'APK')
        for f in FORMATS: self.assertIsNotNone(self.res[f], 'lettrage introuvable a %dx%d' % f)

    def test_one_and_a_half_times_wider_at_all_formats(self):
        for f in FORMATS:
            r = self.res[f]['larg_h'] / self.origin['larg_h']
            self.assertAlmostEqual(r, 1.5, delta=0.05, msg='rapport de largeur %.3f a %dx%d' % ((r,) + f))

    def test_logo_stays_in_window(self):
        for f in FORMATS:
            r = self.res[f]; self.assertGreater(r['x0'], 0.01, f); self.assertLess(r['x1'], 0.99, f); self.assertGreater(r['y0'], 0.05, f)

    def test_logo_is_centered(self):
        for f in FORMATS: self.assertLess(abs(self.res[f]['centre']), 0.01, f)

    def test_iv_does_not_cover_touch_the_screen(self):
        limit = prompt_top(self.zoom) - 0.02
        for f in FORMATS:
            self.assertIsNotNone(self.res[f]['iv_bas'], f)
            self.assertLess(self.res[f]['iv_bas'], limit, 'bas du IV a %.3f H, haut de « Touchez l\'ecran » a %.3f H (%dx%d)' % ((self.res[f]['iv_bas'], prompt_top(self.zoom)) + f))

    def test_same_placement_at_all_formats(self):
        for lookup_key in ('larg_h', 'y0', 'iv_bas'):
            v = [self.res[f][lookup_key] for f in FORMATS]; self.assertLess(max(v) - min(v), 0.02, (lookup_key, v))


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + REST)
