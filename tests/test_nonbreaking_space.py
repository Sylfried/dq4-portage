"""Espaces insecable (U+00A0), fine (U+202F) et mince (U+2009) : le patch FR met une espace insecable avant « ! », « ? » et « : » ; la police du jeu (SE-GARRIR) donne 11 px d'advance a son glyphe 160 contre 5 px a l'espace normale, d'ou une espace
presque double (issue #161, avance #162, D-226 : elles etaient dessinees comme l'espace normale, PARTOUT, par `BitmapFont`). D-243 (05/11/2026, issue #311) : seul l'HISTORIQUE des messages les dessine comme l'espace normale (`ui_history.normal_spaces`) ;
les autres menus (`ui_menu.BitmapFont`) utilisent la largeur que la police donne a ces caracteres, comme le jeu d'origine. La police des messages (`MessageFont`, celle du moteur : son U+00A0 fait deja 5 px) n'est pas touchee.

    python3 tests/test_nonbreaking_space.py

Sans donnees du jeu : police factice (espace 5, insecable 11, « ! » 6). Avec la vraie police extraite (DQ_UI_CACHE : dossier de ui_garrir.json / .png) : les memes controles sur ses vraies metriques.
"""
import json, os, sys, tempfile, types, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _text_render as TR
import pyglet
pyglet.options['shadow_window'] = False
UM = TR.UM
try:
    from dq4_pc.menus import ui_history as UH
    from dq4_pc.core import history as HI
    from PIL import Image
except Exception as ex:
    UH = None; ERROR = ex

THIN = (' ', ' ', ' ')


def dummy_font():
    d = tempfile.mkdtemp()
    j, p = os.path.join(d, 'f.json'), os.path.join(d, 'f.png')
    Image.new('RGBA', (256, 256), (255, 255, 255, 255)).save(p)
    def g(code, adv, w=3, h=5): return [code, 0.0, -10.0, float(w), -float(h), float(adv), 0, 0.1, 0.1, 0.01, -0.02]
    with open(j, 'w') as f:
        json.dump({'nom': 'test', 'fontSize': 20.0, 'lineSpacing': 23.5, 'ascent': 18.9, 'descent': -4.0, 'pixelScale': 1.0,
                   'glyphes': [g(32, 5, 0, 0), g(0xa0, 11, 0, 0), g(33, 6), g(63, 9), g(58, 6), g(ord('a'), 8), g(ord('l'), 4)]}, f)
    return UM.BitmapFont(j, p)


def real_font():
    f = TR.real_font()
    return f.bm if f is not None else None


@unittest.skipIf(UH is None, 'ui_history non importable ici')
class MenusKeepTheFontWidths(unittest.TestCase):
    """Hors historique : le glyphe 160 garde son advance (11 px), comme dans le jeu d'origine ; U+202F et U+2009, absents de la police, comptent comme une espace (regle de BitmapFont pour tout caractere absent)."""
    def controls(self, F):
        self.assertEqual(F.width_px(' '), F.G[0xa0][0]); self.assertGreater(F.width_px(' '), F.width_px(' '))
        self.assertEqual(F.width_px('a !'), F.width_px('a') + F.G[0xa0][0] + F.width_px('!'))              # « l'air !» : l'espace insecable a la largeur de son glyphe
        self.assertEqual(F.width_px('a   '), F.width_px('a') + 3 * F.G[0xa0][0])
        if 0x202f not in F.G: self.assertEqual(F.width_px(' '), F.width_px(' '))
        if 0x2009 not in F.G: self.assertEqual(F.width_px(' '), F.width_px(' '))

    def test_dummy_font(self):
        F = dummy_font(); self.assertEqual(F.G[0xa0][0], 11); self.assertEqual(F.width_px(' '), 11); self.controls(F)

    def test_real_font(self):
        F = real_font()
        if F is None: self.skipTest('DQ_UI_CACHE (ui_garrir.json / .png) absent')
        self.assertEqual(F.G[32][0], 5); self.assertEqual(F.G[0xa0][0], 11); self.controls(F)

    def test_line_image(self):
        """La texture d'une ligne avec l'insecable est plus large que celle avec l'espace normale (besoin d'un contexte GL : fenetre cachee)."""
        try: win = pyglet.window.Window(width=64, height=64, visible=False)
        except Exception as ex: self.skipTest('pas de contexte GL : %r' % (ex,))
        try:
            F = dummy_font(); t, w, h, b = F.line('a !'); t2, w2, h2, b2 = F.line('a !')
            self.assertEqual(w - w2, 6); self.assertEqual((h, b), (h2, b2))
        finally: win.close()

    def test_other_chars_do_not_change(self):
        F = dummy_font()
        self.assertEqual(F.width_px('al!?:'), 4 + 8 + 6 + 9 + 6)
        self.assertEqual(F.width_px('a l'), 8 + 5 + 4)                                       # l'espace normale reste a 5

    def test_no_constant_left_in_the_menus_module(self):
        self.assertFalse(hasattr(UM, 'THIN_SPACES'))


@unittest.skipIf(UH is None, 'ui_history non importable ici')
class HistoryDrawsThemAsNormalSpaces(unittest.TestCase):
    def test_normal_spaces(self):
        F = dummy_font()
        for c in THIN: self.assertEqual(UH.normal_spaces(F, 'a%s!' % c), 'a !', repr(c))
        self.assertEqual(UH.normal_spaces(F, 'a   '), 'a   ')
        self.assertEqual(UH.normal_spaces(F, 'Que faites-vous ? Allez'), 'Que faites-vous ? Allez')       # le reste du texte ne change pas
        for font in (None, object(), types.SimpleNamespace(width_px=lambda t: 0)):                        # autre police (MessageFont : celle du moteur) : texte tel quel
            self.assertEqual(UH.normal_spaces(font, 'a !'), 'a !')

    def test_widths_in_the_history(self):
        F = dummy_font(); view = object.__new__(UH.HistoryView)
        for c in THIN: self.assertEqual(view._text_width(F, 'a%s!' % c, 1.0, 17), view._text_width(F, 'a !', 1.0, 17), repr(c))
        self.assertEqual(view._text_width(F, 'a !', 2.0, 17), (8 + 5 + 6) * 2.0)                 # 8 + 5 + 6 px de police (et non 8 + 11 + 6), a l'echelle 2

    def test_lines_drawn_in_the_history(self):
        """`_line` dessine la texture de la ligne avec des espaces normales (la police des menus, elle, a mesure l'insecable a 11 px)."""
        F = dummy_font(); seen = []
        F.line = lambda text: (seen.append(text), (types.SimpleNamespace(target=0, id=0), 20, 31, 22))[1]
        class Sprite:
            def __init__(self, tex): self.image = tex
            def update(self, **kw): pass
            def draw(self): pass
        old = pyglet.sprite.Sprite; pyglet.sprite.Sprite = Sprite
        try:
            view = object.__new__(UH.HistoryView); view._spr = {}
            view._line(F, 'Quoi !', 0.0, 0.0, 1.0, (255, 255, 255), 17); view._line(F, 'Mais ?', 0.0, 0.0, 1.0, (255, 255, 255), 17)
        finally: pyglet.sprite.Sprite = old
        self.assertEqual(seen, ['Quoi !', 'Mais ?'])

    def test_wrapping_uses_the_normal_space_width(self):
        """Les coupures de l'historique (police SE-GARRIR, sans la police des messages) mesurent l'espace insecable comme une espace normale : « aa<nbsp>! al » (44 px) tient dans 46 px ; avec 11 px pour l'insecable (50 px) il se coupait."""
        F = dummy_font(); view = object.__new__(UH.HistoryView); view._lines = {}; view._bmm = lambda: None
        e = types.SimpleNamespace(n=1, type=HI.TYPE_DIALOGUE, text='aa ! al')
        B = types.SimpleNamespace(text_scale=1.0, text_width=lambda: 46.0, LINES=3)
        pages = view._pages_of(F, e, B, 1.0, 17); self.assertEqual(pages, [['aa ! al']])
        self.assertEqual(F.width_px('aa ! al'), 50)                                              # (la police, elle, la mesure a 50 : c'est bien la normalisation qui evite la coupure)

    def test_real_font(self):
        F = real_font()
        if F is None: self.skipTest('DQ_UI_CACHE (ui_garrir.json / .png) absent')
        view = object.__new__(UH.HistoryView); sp = F.G[32][0]
        self.assertEqual(view._text_width(F, 'a !', 1.0, 17), F.width_px('a') + sp + F.width_px('!'))
        self.assertGreater(F.width_px('a !'), view._text_width(F, 'a !', 1.0, 17))


if __name__ == '__main__':
    unittest.main(verbosity=2)
