"""Descriptions d'objets et de sorts a la position et a la taille EXACTES du jeu (D-243, 05/11/2026, issue #311). Avant (#190 a #191, puis #219 pour les boutiques et le casino), la description etait recoupee a la largeur de son cadre (2 lignes) puis comprimee
jusqu'a x0,7 : « Peut aussi etre utilisee comme objet au / combat. » ne recouvrait plus « Attaque E 74 ». Sylfried a repris : le texte du jeu s'affiche tel quel et deborde comme sur le mobile ; le projet de traduction raccourcira les chaines.

Les huit cellules concernees (type, port, numero de chaine) : fiche d'un sort (7, 0, 1), menu Objets (10, 0, 4), infos d'objet en combat (38, 2, 3), casino (46, 4, 3), boutiques (60, 4, 4), (61, 4, 4), (63, 0, 4), fiche d'objet de vente (70, 0, 3).

  1. la cellule ne porte plus ni limite de recoupe (`wrap_x`, `wrap_n`) ni limite de largeur (`fit_x`), et son texte est celui du moteur ;
  2. `Render._text` (police factice, sans GL) dessine toutes les lignes du texte, aux memes retours a la ligne, a l'ancre de la cellule, a l'echelle 1 : ni recoupe, ni fusion, ni compression ;
  3. avec la vraie mise en page (cache de l'interface : DQ_UI_CACHE) : les huit cellules existent et sont dessinees telles quelles ;
  4. avec DQ_APK=<dossier des APK patches> et la vraie police : les 360 descriptions du patch (assets/msg/en/b0831000.mpt et b0835000.mpt) sont dessinees telles quelles, ligne pour ligne.

    python3 tests/test_item_description.py
    DQ_APK=<APK patches> [DQ_UI_CACHE=<cache de l'interface>] python3 tests/test_item_description.py
"""
import os, re, sys, unittest, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _text_render as TR
UM = TR.UM

APK = os.environ.get('DQ_APK')
CELLS = ((7, 0, 1), (10, 0, 4), (38, 2, 3), (46, 4, 3), (60, 4, 4), (61, 4, 4), (63, 0, 4), (70, 0, 3))
ONE_LINE = "Au combat, ils peuvent inverser le cours du temps."                      # une seule ligne de 50 caracteres
TWO_LINES = "Peut aussi être utilisée comme objet au\r\ncombat."                      # 1re ligne de 39 caracteres
FOUR_LINES = "Permet de sortir\r\nimmédiatement des\r\ndonjons, grottes et\r\ntours."


def description_window(typ, port, no):
    """Fenetre synthetique : `no` + 1 cellules de texte du port `port`, la derniere est la description (a l'ancre x = -214, en bas : z = -324)."""
    return TR.make_window(typ, [dict(pos=[-214.0, 4.0, -324.0], anchor=3, ls=0.881)] * (no + 1), port=port)


class Cells(unittest.TestCase):
    def test_no_limit_on_any_cell(self):
        for typ, port, no in CELLS:
            wnd = description_window(typ, port, no)
            for k in range(no + 1): wnd.param_str(port, k, 'x' * 60 if k != no else FOUR_LINES)
            for k in range(no + 1):
                node = wnd.N[10 + k]; self.assertFalse({'wrap_x', 'wrap_n', 'fit_x', '_adj'} & set(node), (typ, port, no, k))
            self.assertEqual(wnd.N[10 + no]['text']['text'], FOUR_LINES, (typ, port, no))                 # le texte du moteur n'est pas modifie

    def test_spell_card_cost_line_has_no_limit_either(self):
        wnd = TR.make_window(7, [dict(pos=[75.0, 12.0, 103.0], anchor=0, ls=0.88)] * 4)
        for no, s in enumerate(('Premiers secours', "Restaure au moins 30\r\nPV d'un seul allié.", 'Coût en PM  2/ 30', 'Lancer')): wnd.param_str(0, no, s)
        for k in range(4): self.assertFalse({'wrap_x', 'wrap_n', 'fit_x'} & set(wnd.N[10 + k]), k)


class DrawnAsIs(unittest.TestCase):
    def check(self, wnd, node, text, x=-214.0):
        quads = TR.draw(wnd, node); step = TR.LEADING * node['text']['characterSize'] * 0.1 * node['text']['lineSpacing']
        self.assertEqual([q.text for q in quads], [l for l in text.split('\n') if l])                  # toutes les lignes, memes retours a la ligne, rien de fusionne ni de recoupe
        for i, q in enumerate(quads):
            self.assertAlmostEqual(q.x, x, delta=0.01); self.assertAlmostEqual(q.ts, 1.0, places=6); self.assertAlmostEqual(q.base, quads[0].base - i * step, delta=0.01)
        return quads

    def test_every_cell_every_text(self):
        for typ, port, no in CELLS:
            for text in (ONE_LINE, TWO_LINES, FOUR_LINES, "Ne semble pas avoir d'effets\r\nparticuliers.\n"):
                wnd = description_window(typ, port, no)
                for k in range(no + 1): wnd.param_str(port, k, 'x')
                wnd.param_str(port, no, text); self.check(wnd, wnd.N[10 + no], text)

    def test_single_long_line_stays_a_single_line_and_overflows(self):
        wnd = description_window(38, 2, 3)
        for k in range(4): wnd.param_str(2, k, 'x')
        wnd.param_str(2, 3, ONE_LINE); quads = self.check(wnd, wnd.N[13], ONE_LINE)
        self.assertEqual(len(quads), 1); self.assertGreater(quads[0].width, 270.0)                     # 400 unites dans une cellule de 270 : il deborde comme sur le mobile

    def test_a_text_that_fits_is_unchanged_too(self):
        wnd = description_window(10, 0, 4)
        for k in range(5): wnd.param_str(0, k, 'x')
        wnd.param_str(0, 4, "Ne semble pas avoir d'effets\r\nparticuliers.\n"); self.check(wnd, wnd.N[14], "Ne semble pas avoir d'effets\r\nparticuliers.\n")


@unittest.skipUnless(os.path.exists(os.path.join(TR.CACHE, 'ui_layout.json')) and TR.real_font() is not None, "mise en page et police reelles : cache de l'interface (DQ_UI_CACHE : ui_layout.json, ui_garrir.json / .png)")
class RealPageLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ml = UM.PageLayout(os.path.join(TR.CACHE, 'ui_layout.json')); cls.font = TR.real_font()

    def test_each_cell_is_the_bottom_description_cell_and_is_drawn_as_is(self):
        for typ, port, no in CELLS:
            wnd = UM.Window(self.ml, typ); pt, ib = wnd._ib(wnd.params[(port, no)])
            self.assertEqual(ib['k'], 'text', (typ, port, no)); node = wnd.N[ib['go']]
            self.assertTrue(node['pos'][2] < -190 and node['pos'][0] < -200, (typ, port, no, node['pos']))      # barre du bas (z -324 ou -323,5) ou cellule de gauche en combat (z -197), texte a gauche
            wnd.param_str(port, no, FOUR_LINES)
            for n in wnd.N.values(): self.assertFalse({'wrap_x', 'wrap_n', 'fit_x'} & set(n), (typ, port, no))
            quads = TR.draw(wnd, node, r=TR.render(self.font, ml=self.ml))
            self.assertEqual([q.text for q in quads], FOUR_LINES.split('\n'), (typ, port, no))
            for q in quads: self.assertAlmostEqual(q.ts, 1.0, places=5); self.assertAlmostEqual(q.x, node['pos'][0], delta=0.01)


@unittest.skipUnless(APK and os.path.exists(os.path.join(APK, 'split_UnityDataAssetPack.apk')) and os.path.exists(os.path.join(TR.CACHE, 'ui_layout.json')) and TR.real_font() is not None,
                     "descriptions reelles : DQ_APK=<dossier des APK patches> et le cache de l'interface (ui_layout.json, ui_garrir.*)")
class RealDescriptions(unittest.TestCase):
    """Les 360 descriptions du patch (assets/msg/en/b0831000.mpt et b0835000.mpt : deux tables jumelles de 180 objets), la vraie police et la vraie fenetre : chacune est dessinee telle quelle, ligne pour ligne."""
    SEP = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f�]+|@c\d@(?:@a@b)?|@a@b")

    @classmethod
    def setUpClass(cls):
        cls.ml = UM.PageLayout(os.path.join(TR.CACHE, 'ui_layout.json')); cls.font = TR.real_font()
        z = zipfile.ZipFile(os.path.join(APK, 'split_UnityDataAssetPack.apk')); cls.texts = []
        for name_str in ('assets/msg/en/b0831000.mpt', 'assets/msg/en/b0835000.mpt'):
            b = z.read(name_str).decode('utf-8', 'replace'); cls.texts += [e for e in cls.SEP.split(b[b.find('@a@b'):]) if len(e.strip()) >= 6]

    def test_patch_descriptions_exist(self):
        self.assertGreaterEqual(len(self.texts), 300)
        self.assertTrue(any('Peut aussi être utilisée comme objet au' in t for t in self.texts))

    def test_every_description_drawn_line_for_line(self):
        for typ, port, no in ((38, 2, 3), (10, 0, 4)):
            wnd = UM.Window(self.ml, typ); pt, ib = wnd._ib(wnd.params[(port, no)]); node = wnd.N[ib['go']]; r = TR.render(self.font, ml=self.ml)
            for text in self.texts:
                wnd.param_str(port, no, text)
                lines = [l for l in node['text']['text'].split('\n') if l]; quads = TR.draw(wnd, node, r=r)
                self.assertEqual([q.text for q in quads], lines, (typ, text))                                    # aucune recoupe, aucune fusion
                for q in quads: self.assertAlmostEqual(q.ts, 1.0, places=5, msg=(typ, text)); self.assertAlmostEqual(q.x, node['pos'][0], delta=0.01, msg=(typ, text))     # aucune compression, a l'ancre du jeu


if __name__ == '__main__':
    unittest.main()
