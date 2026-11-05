"""Description d'un objet qui ne tient pas dans son cadre (retour de 13 h 30, #190) : en combat, « Peut aussi etre utilisee comme objet au / combat. » sortait de la cellule de gauche de la fiche de l'objet (type 38)
et recouvrait la cellule « Attaque E 74 » ; dans le menu Objets (type 10) une description d'une seule ligne de 50 caracteres allait sous le bouton du sac. Le texte francais du patch a des lignes de 38 caracteres, la
mise en page du jeu a ete faite pour 2 lignes de ~28 : Render._texte recoupe maintenant la description a la largeur de son cadre (UM.DESCRIPTIONS) et, si 2 lignes ne suffisent pas, la comprime (jusqu'a COMPRESSION_MIN).

    python3 tools/test_item_description.py
    DQ_APK=<APK patches> [DQ_UI_CACHE=<cache de l'interface>] python3 tools/test_item_description.py        (ajoute les 360 descriptions reelles du patch avec la vraie police)"""
import os, re, sys, types, unittest, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import pyglet
pyglet.options['shadow_window'] = False
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True
from dq4_pc.menus import ui_menu as UM

APK = os.environ.get('DQ_APK')
CACHE = os.environ.get('DQ_UI_CACHE', '/tmp/uicache47_camera')
U = 9.945 * 0.1                                                      # unites d'interface par pixel de police (characterSize 9,945 des descriptions)
BATTLE_LAYOUT = UM.BATTLE_DESC_X_MAX + 214.0                          # type 38 : texte ancre a x = -214
ITEMS_LAYOUT = UM.CARD_DESC_X_MAX + 211.0                           # type 10 : texte ancre a x = -211


def render(width_px):
    r = object.__new__(UM.Render)
    r.texts = types.SimpleNamespace(bitmap=types.SimpleNamespace(width_px=width_px))
    return r


def adjust(r, text, layout, node=None):
    return r._adjust_description({} if node is None else node, text.split('\n'), layout, 2, r.texts.bitmap, 1.0, 1.0, 1.0, 9.0)


class TestWindows(unittest.TestCase):
    def window(self, typ, nodes, port=0):
        def text(nid): return {'id': nid, 'par': 1, 'pos': [-214.0, 4.0, -197.0], 'act': True, 'text': {'font': 'font', 'characterSize': 9.945, 'text': None, 'anchor': 3, 'alignment': 0, 'lineSpacing': 1.0}, 'mats': []}
        t = {'name': 'Make_Test()', 'err': None, 'nodes': [{'id': 1, 'par': None, 'pos': [0.0, 0.0, 0.0], 'act': True, 'mats': []}] + [text(10 + k) for k in range(nodes)],
             'parts': [{'node': 1, 'ib': [{'k': 'text', 'go': 10 + k, 'variant': 0} for k in range(nodes)]}], 'params': [{'id': port, 'no': k, 'parts': 0, 'base': k} for k in range(nodes)], 'codes': [], 'builds': []}
        return UM.Window(types.SimpleNamespace(types={str(typ): t}, info=[], borders=[], hdr={'lang': {'hiro': 1.0}}, pushed=(0.0, 0.0)), typ)

    def test_description_table(self):
        F = UM.CARD_DESC_X_MAX      # (type, port, numero de chaine) : le port est dans la cle (#219 : la fenetre du casino a d'autres textes au meme numero)
        self.assertEqual(UM.DESCRIPTIONS, {(7, 0, 1): F, (10, 0, 4): F, (38, 2, 3): UM.BATTLE_DESC_X_MAX, (46, 4, 3): F, (60, 4, 4): F, (61, 4, 4): F, (63, 0, 4): F, (70, 0, 3): F})
        self.assertLess(UM.BATTLE_DESC_X_MAX, 63.0)                  # la cellule « Attaque » commence a x = 63 : la description s'arrete avant son cadre

    def test_item_card_in_battle(self):
        wnd = self.window(38, 5, port=2)
        for no, s in enumerate(('Ragnar', 'Objets', 'Épée de cuivre', "Peut aussi être utilisée comme objet au\r\ncombat.", 'Attaque\n   E 24')): wnd.param_str(2, no, s)
        self.assertEqual([(wnd.N[10 + k].get('wrap_x'), wnd.N[10 + k].get('wrap_n')) for k in range(5)], [(None, None)] * 3 + [(UM.BATTLE_DESC_X_MAX, 2), (None, None)])
        self.assertEqual(wnd.N[13]['text']['text'], "Peut aussi être utilisée comme objet au\r\ncombat.")       # le texte du moteur n'est pas modifie (c'est le rendu qui recoupe)

    def test_items_menu(self):
        wnd = self.window(10, 6)
        for no, s in enumerate(('Arme', 'Lance de fer', 'Attaque\n     E 50', "Ne semble pas avoir d'effets\r\nparticuliers.\n", '')): wnd.param_str(0, no, s)
        self.assertEqual([wnd.N[10 + k].get('wrap_x') for k in range(6)], [None, None, None, None, UM.CARD_DESC_X_MAX, None])

    def test_shops_and_casino(self):
        """#219 (audit UI-04) : la barre du bas des fenetres du casino (46), d'achat (60, 61), de vente (63) et de la fiche d'objet de vente (70) est recoupee comme celle des fiches d'objet."""
        for typ, port, no in ((46, 4, 3), (60, 4, 4), (61, 4, 4), (63, 0, 4), (70, 0, 3)):
            wnd = self.window(typ, no + 1, port=port)
            for k in range(no + 1): wnd.param_str(port, k, 'x' * 60)
            self.assertEqual([(wnd.N[10 + k].get('wrap_x'), wnd.N[10 + k].get('wrap_n')) for k in range(no + 1)], [(None, None)] * no + [(UM.CARD_DESC_X_MAX, 2)], typ)

    def test_same_number_in_other_port_not_touched(self):
        """Type 46 : les listes (ports 0 a 3) ont aussi un texte au numero 3 ; seule la barre du bas (port 4) est recoupee."""
        for port in (0, 1, 2, 3):
            wnd = self.window(46, 4, port=port)
            for k in range(4): wnd.param_str(port, k, 'x' * 60)
            self.assertTrue(all(wnd.N[10 + k].get('wrap_x') is None for k in range(4)), port)

    def test_another_window_is_not_touched(self):
        wnd = self.window(36, 5)
        for no in range(5): wnd.param_str(0, no, 'x' * 60)
        self.assertTrue(all(wnd.N[10 + k].get('wrap_x') is None for k in range(5)))


class TestAdjusted(unittest.TestCase):
    """Police fictive : 8 pixels par caractere (U = 0,9945 : 8 unites par caractere a peu pres), cellule de combat = 270 unites (33 caracteres), cadre du menu Objets = 359 unites (44 caracteres)."""
    def setUp(self): self.r = render(lambda x: 8.0 * len(x) / U)

    def wid(self, l): return 8.0 * len(l.strip())

    def test_a_text_that_fits_is_left_as_is(self):
        t = "Ne semble pas avoir d'effets\r\nparticuliers.\n"
        out, f = adjust(self.r, t, BATTLE_LAYOUT)
        self.assertEqual((out, f), (t.split('\n'), 1.0))                    # memes lignes, memes retours a la ligne, ligne vide finale comprise

    def test_too_wide_line_rewrapped(self):
        out, f = adjust(self.r, "Peut aussi être utilisée comme objet au\r\ncombat.", BATTLE_LAYOUT)           # 1re ligne de 39 caracteres = 312 unites > 270
        self.assertEqual((out, f), (['Peut aussi être utilisée comme', 'objet au combat.'], 1.0))

    def test_single_line_of_fifty_chars(self):
        t = "Au combat, ils peuvent inverser le cours du temps."
        out, f = adjust(self.r, t, BATTLE_LAYOUT)
        self.assertEqual((len(out), f), (2, 1.0)); self.assertEqual(' '.join(out), t)
        self.assertTrue(all(self.wid(l) <= BATTLE_LAYOUT for l in out), out)
        out, f = adjust(self.r, t, ITEMS_LAYOUT)                            # menu Objets : 400 unites > 359
        self.assertEqual((len(out), f), (2, 1.0)); self.assertTrue(all(self.wid(l) <= ITEMS_LAYOUT for l in out), out)

    def test_two_long_lines_compressed(self):
        t = "Sonnez-le avant le combat final pour\r\nfaire apparaître votre chariot."           # 36 + 31 caracteres : trois lignes a 270 unites, deux en comprimant
        out, f = adjust(self.r, t, BATTLE_LAYOUT)
        self.assertEqual(len(out), 2, out); self.assertTrue(UM.COMPRESSION_MIN <= f < 1.0, f)
        self.assertTrue(all(self.wid(l) * f <= BATTLE_LAYOUT + 0.5 for l in out), (out, f))
        self.assertEqual(' '.join(out), "Sonnez-le avant le combat final pour faire apparaître votre chariot.")

    def test_hopeless_text_compressed_to_the_minimum(self):
        out, f = adjust(self.r, "mot " * 80, BATTLE_LAYOUT)
        self.assertEqual(f, UM.COMPRESSION_MIN); self.assertGreater(len(out), 2)           # (ne plante pas : le texte deborde, comme avant)

    def test_word_wider_than_border(self):
        out, f = adjust(self.r, "x" * 40, BATTLE_LAYOUT)                    # 320 unites : un seul mot, 1 ligne, comprime pour tenir
        self.assertEqual(len(out), 1); self.assertAlmostEqual(self.wid(out[0]) * f, BATTLE_LAYOUT, delta=17.0); self.assertLessEqual(self.wid(out[0]) * f, BATTLE_LAYOUT + 0.5)

    def test_empty_texts(self):
        for t in ('', '\n\n', ' \r\n'):
            out, f = adjust(self.r, t, BATTLE_LAYOUT); self.assertEqual((out, f), (t.split('\n'), 1.0))

    def test_color_codes_have_no_width(self):
        out, f = adjust(self.r, "@c1" + "a" * 30 + "@c0", BATTLE_LAYOUT)           # 30 caracteres = 240 unites : tient (les codes @cN ne comptent pas)
        self.assertEqual(f, 1.0); self.assertEqual(len(out), 1)

    def test_result_kept_in_memory(self):
        node = {}; t = "Peut aussi être utilisée comme objet au\r\ncombat."
        a = adjust(self.r, t, BATTLE_LAYOUT, node); self.assertIn('_adj', node)
        self.r.texts.bitmap.width_px = lambda x: 1 / 0                      # le deuxieme appel (meme texte, meme cadre) ne mesure plus rien
        self.assertIs(adjust(self.r, t, BATTLE_LAYOUT, node), a)


@unittest.skipUnless(APK and os.path.exists(os.path.join(CACHE, 'ui_garrir.json')) and os.path.exists(os.path.join(CACHE, 'ui_garrir.png')), 'police et descriptions reelles : DQ_APK=<dossier des APK patches> et le cache de l\'interface (ui_garrir.*)')
class TestRealDescriptions(unittest.TestCase):
    """Les 360 descriptions du patch (assets/msg/en/b0831000.mpt et b0835000.mpt : deux tables jumelles de 180 objets) avec la vraie police SE-GARRIR : aucune ne sort du cadre, ni en combat (type 38) ni dans le menu Objets (type 10)."""
    SEP = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f�]+|@c\d@(?:@a@b)?|@a@b")

    @classmethod
    def setUpClass(cls):
        cls.bm = UM.BitmapFont(os.path.join(CACHE, 'ui_garrir.json'), os.path.join(CACHE, 'ui_garrir.png'))
        z = zipfile.ZipFile(os.path.join(APK, 'split_UnityDataAssetPack.apk')); cls.texts = []
        for name_str in ('assets/msg/en/b0831000.mpt', 'assets/msg/en/b0835000.mpt'):
            b = z.read(name_str).decode('utf-8', 'replace'); cls.texts += [e for e in cls.SEP.split(b[b.find('@a@b'):]) if len(e.strip()) >= 6]
        cls.r = render(cls.bm.width_px); cls.r.texts.bitmap = cls.bm

    def verify(self, layout, u=U):
        n_before = n_compressed = 0; fmin = 1.0
        for e in self.texts:
            lines = e.split('\n'); useful = [l for l in lines]
            while useful and not useful[-1].strip(): useful.pop()
            if len(useful) > 2 or max(self.bm.width_px(l.strip()) * u for l in useful) > layout + 0.5: n_before += 1
            out, f = self.r._adjust_description({}, lines, layout, 2, self.bm, u, 1.0, 1.0, u)
            out = [l for l in out]
            while out and not out[-1].strip(): out.pop()
            self.assertLessEqual(len(out), 2, e); self.assertLessEqual(max(self.bm.width_px(l.strip()) * u for l in out) * f, layout + 0.5, e)
            self.assertEqual(' '.join(x.strip() for x in useful if x.strip()).split(), ' '.join(x.strip() for x in out).split(), e)        # aucun mot perdu, ajoute ou deplace
            n_compressed += f < 1.0; fmin = min(fmin, f)
        return n_before, n_compressed, fmin

    def test_patch_descriptions_exist(self):
        self.assertGreaterEqual(len(self.texts), 300)
        self.assertTrue(any('Peut aussi être utilisée comme objet au' in t for t in self.texts))

    def test_battle(self):
        n_before, n_compressed, fmin = self.verify(BATTLE_LAYOUT)
        self.assertGreater(n_before, 100)                             # (le constat : la majorite des descriptions debordait de la cellule de gauche)
        self.assertGreaterEqual(fmin, 0.75 - 1e-9)                   # compression la plus forte : x 0,75

    def test_items_menu(self):
        n_before, n_compressed, fmin = self.verify(ITEMS_LAYOUT)
        self.assertGreater(n_before, 0); self.assertEqual(n_compressed, 0)       # aucune n'a besoin d'etre comprimee : le recoupage suffit

    def test_shops_and_casino(self):
        """#219 : barre du bas des fenetres 46, 60, 61, 70 (texte a l'ancre x = -213,5, taille 9,945) : 24 descriptions sur 360 sortaient du cadre (pire : +72 unites), aucune ne sort apres."""
        n_before, n_compressed, fmin = self.verify(UM.CARD_DESC_X_MAX + 213.5)
        self.assertGreaterEqual(n_before, 20); self.assertGreaterEqual(fmin, 0.7 - 1e-9)

    def test_sale_smaller_text(self):
        """Type 63 : texte de taille 8,2875 (0,83 fois les autres) : aucune ligne trop large, mais 3 descriptions de plus de 2 lignes (comprimees pour tenir sur 2)."""
        n_before, n_compressed, fmin = self.verify(UM.CARD_DESC_X_MAX + 213.5, u=0.82875)
        self.assertEqual(n_before, 3)


@unittest.skipUnless(os.path.exists(os.path.join(CACHE, 'ui_layout.json')), "mise en page reelle : cache de l'interface (ui_layout.json, DQ_UI_CACHE)")
class TestRealPageLayout(unittest.TestCase):
    """Les cles de UM.DESCRIPTIONS designent bien, dans la vraie mise en page, la barre de description du bas de chaque fenetre (et rien d'autre)."""
    @classmethod
    def setUpClass(cls): cls.ml = UM.PageLayout(os.path.join(CACHE, 'ui_layout.json'))

    def test_each_key_designates_bottom_text_cell(self):
        for (typ, port, no), limit in UM.DESCRIPTIONS.items():
            wnd = UM.Window(self.ml, typ); pt, ib = wnd._ib(wnd.params[(port, no)])
            self.assertEqual(ib['k'], 'text', (typ, port, no)); node = wnd.N[ib['go']]
            self.assertTrue(node['pos'][2] < -190 and node['pos'][0] < -200, (typ, port, no, node['pos']))             # barre du bas (z -324 ou -323,5) ou cellule de gauche en combat (z -197), texte a gauche
            self.assertGreater(limit - node['pos'][0], 250.0)

    def test_a_single_cell_rewrapped_per_window(self):
        for typ in sorted({t for t, _, _ in UM.DESCRIPTIONS}):
            wnd = UM.Window(self.ml, typ)
            for (port, no) in list(wnd.params): wnd.param_str(port, no, 'x' * 60)
            rewrapped = [n for n in wnd.N.values() if n.get('wrap_x') is not None]
            self.assertEqual(len(rewrapped), sum(1 for t, _, _ in UM.DESCRIPTIONS if t == typ), typ)


if __name__ == '__main__':
    unittest.main()
