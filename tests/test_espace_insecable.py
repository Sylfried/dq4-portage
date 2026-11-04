"""Espace avant « ! », « ? », « : » dans les boites de dialogue (issue #73) : le patch FR met une espace insecable (U+00A0) avant ces signes ; la police du jeu (SE-GARRIR) donne 11 px d'advance
a son glyphe 160 contre 5 px a l'espace normale, d'ou une espace presque double. Le portage dessine U+00A0, U+202F et U+2009 comme l'espace normale.

    python3 outils/test_espace_insecable.py

Sans donnees du jeu : police factice (espace 5, insecable 11, « ! » 6). Avec la vraie police extraite (DQ_CACHE_UI=<dossier du cache des menus>, ui_garrir.json / .png) : les memes controles sur ses vraies metriques.
"""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
pyglet.options['shadow_window'] = False
try:
    from dq4_pc.menus import ui_menu as UM
    from PIL import Image
except Exception as ex:
    UM = None; ERREUR = ex


def police_factice():
    d = tempfile.mkdtemp()
    j, p = os.path.join(d, 'f.json'), os.path.join(d, 'f.png')
    Image.new('RGBA', (256, 256), (255, 255, 255, 255)).save(p)
    def g(code, adv, w=3, h=5): return [code, 0.0, -10.0, float(w), -float(h), float(adv), 0, 0.1, 0.1, 0.01, -0.02]
    json.dump({'nom': 'test', 'fontSize': 20.0, 'lineSpacing': 23.5, 'ascent': 18.9, 'descent': -4.0, 'pixelScale': 1.0,
               'glyphes': [g(32, 5, 0, 0), g(0xa0, 11, 0, 0), g(33, 6), g(63, 9), g(58, 6), g(ord('a'), 8), g(ord('l'), 4)]}, open(j, 'w'))
    return UM.PoliceBitmap(j, p)


def police_reelle():
    d = os.environ.get('DQ_CACHE_UI')
    j, p = (os.path.join(d, 'ui_garrir.json'), os.path.join(d, 'ui_garrir.png')) if d else ('', '')
    return UM.PoliceBitmap(j, p) if os.path.exists(j) and os.path.exists(p) else None


@unittest.skipIf(UM is None, 'ui_menu non importable ici')
class EspaceInsecable(unittest.TestCase):
    def controles(self, F):
        esp = F.largeur(' ')
        for c in ('\u00a0', '\u202f', '\u2009'):
            self.assertEqual(F.largeur(c), esp, repr(c))                                  # meme largeur que l'espace normale
        self.assertEqual(F.largeur('a\u00a0!'), F.largeur('a !'))                         # « l'air !» comme « l'air ! » : meme largeur avec l'insecable
        self.assertEqual(F.largeur('a\u00a0?'), F.largeur('a ?')); self.assertEqual(F.largeur('a\u00a0:'), F.largeur('a :'))
        self.assertEqual(F.largeur('a\u00a0\u00a0\u00a0'), F.largeur('a   '))             # plusieurs de suite : autant d'espaces

    def test_police_factice(self):
        F = police_factice(); self.assertEqual(F.G[0xa0][0], 11)                          # (le glyphe 160 garde son advance : seul le dessin des espaces change)
        self.assertEqual(F.largeur('\u00a0'), 5); self.controles(F)

    def test_vraie_police(self):
        F = police_reelle()
        if F is None: self.skipTest('DQ_CACHE_UI (ui_garrir.json / .png) absent')
        self.assertEqual(F.G[32][0], 5); self.controles(F)
        self.assertGreater(F.G[0xa0][0], F.G[32][0])                                       # la police a bien le defaut que le portage corrige

    def test_image_de_la_ligne(self):
        """La texture d'une ligne avec l'insecable a la meme taille que celle avec l'espace normale (besoin d'un contexte GL : fenetre cachee)."""
        try: fen = pyglet.window.Window(width=64, height=64, visible=False)
        except Exception as ex: self.skipTest('pas de contexte GL : %r' % (ex,))
        try:
            F = police_factice()
            t, w, h, b = F.ligne('a\u00a0!'); t2, w2, h2, b2 = F.ligne('a !')
            self.assertEqual((w, h, b), (w2, h2, b2))
        finally: fen.close()

    def test_les_autres_caracteres_ne_changent_pas(self):
        F = police_factice()
        self.assertEqual(F.largeur('al!?:'), 4 + 8 + 6 + 9 + 6)
        self.assertEqual(F.largeur('a l'), 8 + 5 + 4)                                       # l'espace normale reste a 5


if __name__ == '__main__':
    unittest.main(verbosity=2)
