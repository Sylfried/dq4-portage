"""Position EXACTE des textes de menu (D-243, 05/11/2026, issue #311 : « tout revenir a la position exacte du jeu d'origine »). Le TextMesh d'Unity avec la police SE-GARRIR est place exactement comme dans l'APK : ancre, interligne, tabulations,
alignement ; plus de recentrage vertical (ex-`text_recentering`, D-143 / D-174 : variable `DQ_TEXTE_ORIGINAL` supprimee avec lui), plus de recoupe ni de compression (descriptions, ligne de cout des sorts, poker), plus de decalage du titre du menu de depart.
Logique pure, sans fenetre ni moteur (`tests/_text_render.py` : le vrai `Render._text` avec un faux GL) :

  1. `first_line_baseline` reproduit le jeu d'origine : lignes de base mesurees sur la capture du mobile (ecran4 : bouton de cible « Rat volant » = 1 ligne, « Scarapince / x2 » = chaine « Scarapince\\n\\n\\t x2 » = 3 lignes ;
     bouton de 82 px de haut centre a y = 159,2 ; echelle 1,688 px / unite ; characterSize 9,945, lineSpacing 0,441, ancre MiddleLeft) a 0,6 unite pres ;
  2. rien du recentrage ne reste (ni fonction, ni constante, ni variable d'environnement) et `Render._text` dessine la 1re ligne de base a `first_line_baseline` pres de zero, pour toutes les ancres et tous les interlignes ;
  3. aucune compression : un texte plus large que tout cadre garde sa largeur naturelle (echelle 1), quel que soit le type de fenetre (poker 48, fiche d'un sort 7, infos d'objet en combat 38...) ; seule la police de repli (GMaruGoPro-M, sans ui_garrir.*) comprime encore ;
  4. avec la VRAIE mise en page et la vraie police (cache de l'interface : DQ_UI_CACHE, par defaut /tmp/audit_final/interface/uicache) : les 465 cellules de texte des 80 types, avec une chaine longue a espace insecable et a plusieurs lignes, sont dessinees
     exactement a la position de la mise en page (ligne de base, bord gauche, echelle 1) ; le titre du menu de depart (type 54) ne bouge pas quand le jeu change de cadre.

    python3 tests/test_text_exact_position.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _text_render as TR
UM = TR.UM

LINE, ASCENT, CAP_HEIGHT = TR.LEADING, TR.ASCENT, 14.0              # SE-GARRIR : interligne, ascent, hauteur des majuscules (px de police)
SCALE, CENTER_Y = 1.688, 159.2                                      # capture du mobile : px par unite, centre vertical du bouton de cible (px depuis le haut)
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def units(y_px): return -(y_px - CENTER_Y) / SCALE                  # ordonnee mesuree (px, vers le bas) -> unites relatives au centre du bouton (vers le haut)


class OriginPlacement(unittest.TestCase):
    def test_target_button_one_line(self):
        u = 9.945 * 0.1; step = LINE * u * 0.441
        base = UM.first_line_baseline(0.0, 1, 1, step, ASCENT * u)
        self.assertAlmostEqual(base, units(182.0), delta=0.6)       # « Rat volant » : ligne de base a y = 182 px

    def test_target_button_three_lines(self):
        u = 9.945 * 0.1; step = LINE * u * 0.441
        b1 = UM.first_line_baseline(0.0, 1, 3, step, ASCENT * u)
        self.assertAlmostEqual(b1, units(165.0), delta=0.6)         # « Scarapince » : y = 165 px
        self.assertAlmostEqual(b1 - 2 * step, units(200.0), delta=0.6)       # « x2 » (3e ligne) : y = 200 px

    def test_anchors(self):
        self.assertAlmostEqual(UM.first_line_baseline(100.0, 0, 2, 10.0, 18.0), 82.0)     # haut : le bloc pend sous l'ancre
        self.assertAlmostEqual(UM.first_line_baseline(100.0, 1, 2, 10.0, 18.0), 92.0)     # milieu
        self.assertAlmostEqual(UM.first_line_baseline(100.0, 2, 2, 10.0, 18.0), 102.0)    # bas : le bloc monte au-dessus de l'ancre


class NothingLeftOfTheRecentering(unittest.TestCase):
    def test_no_function_nor_constant(self):
        for name in ('text_recentering', 'TEXT_CENTERING', 'compress_label', 'DESCRIPTIONS', 'THIN_SPACES', 'BUTTON_COMPRESSION_TYPES', 'CARD_COST_X_MAX'):
            self.assertFalse(hasattr(UM, name), name)
        for name in ('_adjust_description', '_tab_title'):
            self.assertFalse(hasattr(UM.Render, name) or hasattr(UM.Window, name), name)

    def test_no_environment_variable_anywhere(self):
        for folder, _, files in os.walk(os.path.join(ROOT, 'dq4_pc')):
            for f in files:
                if f.endswith('.py'):
                    with open(os.path.join(folder, f), encoding='utf-8') as fh: self.assertNotIn('DQ_TEXTE_ORIGINAL', fh.read(), os.path.join(folder, f))


class ExactPlacement(unittest.TestCase):
    """Fenetres synthetiques, police factice (8 px par caractere) : la geometrie dessinee est celle de TextMesh (ancre, interligne, alignement), rien de plus."""
    TEXTS = ('Abandonner', 'Abandonner\nOk', 'Abc\n\nDefghij')

    def test_first_baseline_for_every_anchor_and_line_spacing(self):
        for anchor in range(9):
            for ls in (0.441, 0.481, 0.801, 0.873, 0.962, 1.0, 1.258):
                for text in self.TEXTS:
                    wnd = TR.make_window(3, [dict(pos=[10.0, 4.0, 20.0], anchor=anchor, alignment=0, ls=ls)]); wnd.param_str(0, 0, text)
                    node = wnd.N[10]; quads = TR.draw(wnd, node)
                    u = node['text']['characterSize'] * 0.1; step = LINE * u * ls; lines = text.split('\n')
                    base0 = UM.first_line_baseline(20.0, anchor // 3, len(lines), step, ASCENT * u)
                    expected = [base0 - i * step for i, l in enumerate(lines) if l]
                    self.assertEqual(len(quads), len(expected), (anchor, ls, text))
                    for q, b in zip(quads, expected): self.assertAlmostEqual(q.base, b, delta=0.01, msg=(anchor, ls, text))      # aucun recentrage : ni remontee de (1 - ls) x interligne x u / 2, ni autre

    def test_the_text_is_not_lifted_for_a_low_line_spacing(self):
        """Avec lineSpacing 0,441 (cibles de combat) le recentrage remontait le texte de 6,5 unites ; il est maintenant exactement a la ligne de base du jeu."""
        wnd = TR.make_window(33, [dict(pos=[0.0, 4.0, 0.0], anchor=4, alignment=1, ls=0.441)]); wnd.param_str(0, 0, 'Rat volant')
        q = TR.draw(wnd, wnd.N[10])[0]; u = 0.9945
        self.assertAlmostEqual(q.base, UM.first_line_baseline(0.0, 1, 1, LINE * u * 0.441, ASCENT * u), delta=0.01)

    def test_horizontal_anchor_and_alignment(self):
        for col, side in ((0, 'left'), (1, 'centre'), (2, 'right')):
            wnd = TR.make_window(3, [dict(pos=[-50.0, 4.0, 0.0], anchor=col, alignment=col)]); wnd.param_str(0, 0, 'Abcdefghij\nAbc')
            long_, short = TR.draw(wnd, wnd.N[10]); u = 0.9945; w1, w2 = 80 * u, 24 * u
            edge = {0: lambda q, w: q.x, 1: lambda q, w: q.x + w / 2, 2: lambda q, w: q.x + w}[col]
            self.assertAlmostEqual(edge(long_, w1), -50.0, delta=0.01, msg=side)                                         # la ligne la plus longue : son bord (gauche, milieu, droit) est a l'ancre
            self.assertAlmostEqual(edge(short, w2), -50.0, delta=0.01, msg=side)                                         # alignement identique a l'ancre : la ligne courte est calee sur le meme bord

    def test_no_compression_whatever_the_window(self):
        """Une chaine de 400 pixels sur un cadre de quelques dizaines d'unites : echelle 1 et largeur naturelle, pour tous les types qui compressaient (poker 48, fiche d'un sort 7, infos d'objet 38) et les autres."""
        for typ in (3, 7, 38, 46, 48, 53, 54, 60):
            for anchor, x in ((0, 75.0), (1, 0.0), (3, -214.0)):
                wnd = TR.make_window(typ, [dict(pos=[x, 4.0, 0.0], anchor=anchor)]); wnd.param_str(0, 0, 'Coût en PM  10/ 30 Abandonner Doubler Changer Garder x' * 2)
                for q in TR.draw(wnd, wnd.N[10]): self.assertAlmostEqual(q.ts, 1.0, places=6, msg=(typ, anchor)); self.assertAlmostEqual(q.width, (8 * len(q.text) + 4) * 0.9945, delta=0.01)

    def test_description_is_drawn_as_the_game_gives_it(self):
        """Une description a 3 ou 4 lignes (cadre de 2) : toutes les lignes, aux memes retours a la ligne, au meme x, a l'interligne du jeu (plus de recoupe)."""
        text = "Permet de sortir\r\nimmédiatement des\r\ndonjons, grottes et\r\ntours."
        for typ, port, no in ((7, 0, 1), (10, 0, 4), (38, 2, 3), (46, 4, 3), (60, 4, 4), (61, 4, 4), (63, 0, 4), (70, 0, 3)):
            wnd = TR.make_window(typ, [dict(pos=[-214.0, 4.0, -324.0], anchor=3, ls=0.881)] * (no + 1), port=port)
            for k in range(no + 1): wnd.param_str(port, k, 'x')
            wnd.param_str(port, no, text); node = wnd.N[10 + no]
            self.assertFalse({'wrap_x', 'wrap_n', 'fit_x'} & set(node), typ)
            self.assertEqual(node['text']['text'], text)
            quads = TR.draw(wnd, node); step = LINE * 0.9945 * 0.881
            self.assertEqual([q.text for q in quads], text.split('\n'), typ)
            for i, q in enumerate(quads): self.assertAlmostEqual(q.x, -214.0, delta=0.01); self.assertAlmostEqual(q.ts, 1.0, places=6); self.assertAlmostEqual(q.base, quads[0].base - i * step, delta=0.01)

    def test_spell_cost_line_is_not_compressed(self):
        wnd = TR.make_window(7, [dict(pos=[75.0, 12.0, 103.0], anchor=0, ls=0.88)] * 3); wnd.param_str(0, 2, 'Coût en PM  10/ 30 et encore beaucoup de texte')      # (cellule 0/2 : la ligne de cout de Make_MagicInfo)
        self.assertNotIn('fit_x', wnd.N[12]); q = TR.draw(wnd, wnd.N[12])[0]
        self.assertAlmostEqual(q.ts, 1.0, places=6); self.assertAlmostEqual(q.x, 75.0, delta=0.01)


class FallbackFont(unittest.TestCase):
    """Sans ui_garrir.* (police de repli GMaruGoPro-M, dont les metriques ne sont pas celles du jeu) la compression dans la plaque ou la fenetre reste : c'est le seul cas ou elle sert encore."""
    def test_wide_text_is_compressed_in_its_frame(self):
        import types
        neighbor = types.SimpleNamespace(rects=lambda: [(-50.0, -50.0, 50.0, 50.0)])        # une fenetre voisine de 100 unites de large contient l'ancre du texte
        r = TR.render(None, neighbors=[neighbor])
        wnd = TR.make_window(3, [dict(pos=[0.0, 4.0, 0.0], anchor=4, alignment=1)]); wnd.param_str(0, 0, 'Un texte tres long qui depasse la fenetre voisine')
        q = TR.draw(wnd, wnd.N[10], r=r)[0]
        self.assertLess(q.ts, 1.0); self.assertGreaterEqual(q.ts, 0.7 - 1e-9)


class RealLayoutAndFont(unittest.TestCase):
    """Les 465 cellules de texte de la vraie mise en page (80 types), la vraie police."""
    @classmethod
    def setUpClass(cls):
        cls.font = TR.real_font(); j = os.path.join(TR.CACHE, 'ui_layout.json'); b = os.path.join(TR.CACHE, 'ui_frameData.bin')
        if cls.font is None or not os.path.exists(j): raise unittest.SkipTest('cache de l\'interface absent (DQ_UI_CACHE : ui_layout.json, ui_garrir.json / .png)')
        cls.ml = UM.PageLayout(j, b if os.path.exists(b) else None); cls.dy = cls.ml.hdr['lang']['dy']

    def cells(self):
        for typ in sorted(self.ml.types, key=int):
            t = self.ml.types[typ]
            if t.get('err') or not t.get('nodes') or not t.get('params'): continue
            wnd = UM.Window(self.ml, int(typ))
            for (i, no), p in wnd.params.items():
                if 'custom' in p or p.get('textcolor') is not None: continue
                pt, ib = wnd._ib(p)
                if ib and ib['k'] == 'text': yield int(typ), i, no

    def test_every_cell_is_where_the_layout_puts_it(self):
        probes = ('Abcdefgh', 'Coût : 10/ 30 Abandonner Doubler Changer un texte bien plus large que toutes les plaques', "Peut aussi être utilisée comme objet au\r\ncombat.\nEt une troisième ligne")
        n = 0
        for typ, i, no in self.cells():
            for probe in probes:
                wnd = UM.Window(self.ml, typ); wnd.param_str(i, no, probe)
                pt, ib = wnd._ib(wnd.params[(i, no)]); node = wnd.N[ib['go']]; t = node['text']
                if not t.get('text'): continue
                u = t['characterSize'] * 0.1; step = self.font.leading * u * t['lineSpacing']; lines = t['text'].split('\n'); col = t['anchor'] % 3
                base0 = UM.first_line_baseline(node['pos'][2] - self.dy, t['anchor'] // 3, len(lines), step, self.font.ascent * u)
                quads = TR.draw(wnd, node, r=TR.render(self.font, ml=self.ml))
                shown = [l for l in lines if l]; self.assertEqual([q.text for q in quads], shown, (typ, i, no))
                wid = [self.font.width_px(l) * u * node['tscale'] for l in lines]; bl = max(wid); it = iter(quads)
                for idx, l in enumerate(lines):
                    if not l: continue
                    q = next(it)
                    self.assertAlmostEqual(q.ts, node['tscale'], places=5, msg=(typ, i, no, probe))                                   # pas de compression, pas d'espace fine remplacee
                    self.assertAlmostEqual(q.base, base0 - idx * step, delta=0.01, msg=(typ, i, no, probe))                           # pas de recentrage
                    al = {0: 0.0, 1: (bl - wid[idx]) / 2, 2: bl - wid[idx]}[t['alignment']]
                    self.assertAlmostEqual(q.x, node['pos'][0] - {0: 0.0, 1: bl / 2, 2: bl}[col] + al, delta=0.01, msg=(typ, i, no, probe))      # pas de recoupe : la ligne part de l'ancre du jeu
                n += 1
        self.assertGreater(n, 1300)                                                     # 465 cellules x 3 chaines (moins les cellules sans texte)

    def test_poker_labels(self):
        """« Abandonner », « Doubler », « Changer », « Garder » (types 48) : largeur naturelle, comme sur le mobile, meme quand ils depassent leur plaque (le projet de traduction raccourcira les chaines)."""
        for (i, no) in ((4, 0), (4, 2), (2, 0), (0, 5)):
            for s in ('Abandonner', 'Doubler', 'Garder', 'Changer'):
                wnd = UM.Window(self.ml, 48)
                if (i, no) not in wnd.params: continue
                wnd.param_str(i, no, s); pt, ib = wnd._ib(wnd.params[(i, no)])
                q = TR.draw(wnd, wnd.N[ib['go']], r=TR.render(self.font, ml=self.ml))[0]; self.assertAlmostEqual(q.ts, 1.0, places=5, msg=(i, no, s))

    def test_start_menu_title_does_not_move(self):
        """Type 54 : le titre du menu de depart reste ou la mise en page le met, quel que soit le cadre choisi par le code 3 (il se decalait de +30 en x et -56 en z pour le cadre 221)."""
        for c in (0, 1, 2):
            wnd = UM.Window(self.ml, 54)
            frame = next((ib for pt in wnd.parts for ib in pt['ib'] if ib['k'] == 'frame'), None); self.assertIsNotNone(frame)
            title = next(n for n in wnd.N.values() if n['par'] == frame.get('go') and n['text'] is not None); before = list(title['pos'])
            wnd.code(3, c); self.assertEqual(title['pos'], before, c)


if __name__ == '__main__':
    unittest.main(verbosity=2)
