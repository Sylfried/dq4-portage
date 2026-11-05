"""Etiquettes du poker du casino (type 48) a la largeur EXACTE du jeu (D-243, 05/11/2026, issue #311). Avant : « Abandonner » sortait des cinq boutons sous les cartes et se chevauchait (le francais est plus long que l'anglais du bouton) ;
SVC-03 avait fait comprimer ces etiquettes (jusqu'a x0,70 : choix « police reduite »). Sylfried a repris : tout revient a la position et a la taille exactes du jeu, les debordements sont a corriger dans le projet de traduction. Il n'y a plus de compression,
ni pour le poker ni ailleurs (avec SE-GARRIR).

  1. plaque de bouton (partie 7) de 80 unites et etiquette centree plus large qu'elle : echelle 1, centree sur la plaque, la meme que pour n'importe quel autre type de fenetre ;
  2. avec la VRAIE mise en page et la vraie police (cache de l'interface : DQ_UI_CACHE) : les etiquettes des cinq boutons « Abandonner », « Doubler », « Changer », « Garder » gardent leur largeur naturelle.

    python3 tests/test_poker_font.py
"""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _text_render as TR
UM = TR.UM


class Poker(unittest.TestCase):
    def test_label_wider_than_its_plate_is_not_compressed(self):
        for typ in (48, 3, 44, 46, 47, 49, 53, 54):                       # le poker, et les fenetres qui ne comprimaient pas non plus
            wnd = TR.make_window(typ, [dict(pos=[0.0, 4.0, 0.0], anchor=4, alignment=1)], plates=[dict(pos=[0.0, 0.0], w=80.0, h=40.0)]); wnd.param_str(0, 0, 'Abandonner')
            q = TR.draw(wnd, wnd.N[10])[0]
            self.assertAlmostEqual(q.ts, 1.0, places=6, msg=typ); self.assertAlmostEqual(q.width, (8 * 10 + 4) * 0.9945, delta=0.01)
            self.assertGreater(q.width, 80.0 - 14.0)                      # (plus large que la plaque moins ses marges : c'est bien le cas qui etait comprime)
            self.assertAlmostEqual(q.x + (q.width - 4 * 0.9945) / 2, 0.0, delta=0.01)       # centree sur l'ancre, comme dans le jeu

    def test_no_compression_machinery_left(self):
        for name in ('compress_label', 'BUTTON_COMPRESSION_TYPES', 'COMPRESSION_MIN'): self.assertFalse(hasattr(UM, name), name)


class RealPoker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = TR.real_font(); j = os.path.join(TR.CACHE, 'ui_layout.json'); b = os.path.join(TR.CACHE, 'ui_frameData.bin')
        if cls.font is None or not os.path.exists(j): raise unittest.SkipTest('cache de l\'interface absent (DQ_UI_CACHE : ui_layout.json, ui_garrir.json / .png)')
        cls.ml = UM.PageLayout(j, b if os.path.exists(b) else None)

    def test_labels_keep_their_natural_width(self):
        n = 0
        for (i, no) in ((4, 0), (4, 2), (2, 0), (0, 5)):
            wnd = UM.Window(self.ml, 48)
            if (i, no) not in wnd.params: continue
            for s in ('Abandonner', 'Doubler', 'Garder', 'Changer'):
                wnd = UM.Window(self.ml, 48); wnd.param_str(i, no, s); pt, ib = wnd._ib(wnd.params[(i, no)])
                q = TR.draw(wnd, wnd.N[ib['go']], r=TR.render(self.font, ml=self.ml))[0]
                self.assertAlmostEqual(q.ts, 1.0, places=5, msg=(i, no, s)); n += 1
        self.assertGreaterEqual(n, 8)
        self.assertGreater(self.font.width_px('Abandonner') * 0.9945, 100.0)               # « Abandonner » fait 103 unites : plus que la plaque de 72 (il depasse, comme sur le mobile)


if __name__ == '__main__':
    unittest.main()
