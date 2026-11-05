"""Oui / Non empilés en haut à droite de la boîte de dialogue, comme sur DS (D-231 ; demande de Sylfried du 04/11/2026 à 23 h 02 : « tu les mets l'un sur l'autre posé sur le coin en haut à droite de la boîte de dialogue
avec les bords droits alignés »), sans fenêtre ni moteur :

  1. `Window` de type 1 (Make_YesNo) : la plaque « Non » passe sous « Oui » (même colonne, une unité entre les deux), avec son texte ; son panneau du cadre la suit ; l'étendue verticale grandit d'un panneau, l'étendue horizontale
     est celle d'une seule colonne ; les zones tactiles sont empilées (Oui en haut) ; une autre mise en page (pas deux plaques) n'est pas touchée ;
  2. `visible_edges` : le bord VISIBLE d'une maille de cadre (les colonnes et les rangées de la feuille dont l'opacité dépasse le seuil), pas le bord de la maille ;
  3. `_yesno_on_message` / `_ui_yesno` : la pile pose son bord bas VISIBLE `YESNO_BOX_SPACING` au-dessus du bord haut visible de la boîte, et son bord droit visible sur celui de la boîte, à toutes les échelles du joueur ;
  4. (si le cache d'interface existe : DQ_UI_CACHE ou DQ_CACHE_UI, sinon /tmp/uicache4) la VRAIE mise en page : (-10 ; 87) sur une colonne de -134,5 à -0,5 ; clavier et clic inchangés (haut = Oui, bas = Non).

    python3 tests/test_stacked_yes_no.py        (pyglet seul est nécessaire ; sans pyglet les tests sont passés)
"""
import ast, os, sys, types, unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
os.environ.setdefault('PYGLET_HEADLESS', '1')
CACHE = os.environ.get('DQ_UI_CACHE') or os.environ.get('DQ_CACHE_UI') or '/tmp/uicache4'

try:
    import numpy as np
    from dq4_pc.menus import ui_menu as UM
    from dq4_pc.window import constants as K
    from dq4_pc.window.menu_display import MenusMixin
    IMPORT_ERROR = None
except Exception as ex:                                       # (CI : ni pyglet ni fenetre)
    UM = K = MenusMixin = np = None; IMPORT_ERROR = ex


def yes_no_template(plate_spacing=1.0):
    """Mise en page minimale de Make_YesNo (même structure que l'export du jeu) : cadre (z 87) de deux panneaux de 134 x 48 (x -134,5..-0,5 et 0,5..134,5, une case chacun), deux plaques (x -67,5 et 67,5, z 62,5) et leurs textes."""
    def quad(x0, x1, z0, z1): return [[x0, z1], [x1, z1], [x1, z0], [x0, z0]]
    mat = lambda sheet, part: [dict(sheet=sheet, part=part, color=None, shader='parts', offset=None)]
    border = dict(id=1, par=None, pos=[0.0, 10.0, 87.0], act=True, mats=mat(0, 4), mesh=dict(vtx=quad(-134.5, -0.5, -48.0, 0.0) + quad(0.5, 134.5, -48.0, 0.0), uv=[[0, 0]] * 8, sub={'0': [0, 1, 3, 3, 1, 2, 4, 5, 7, 7, 5, 6]}))
    def plate(i, x, button):
        return dict(id=i, par=1, pos=[x, 14.0, 62.5], act=True, mats=mat(1, 7), mesh=dict(vtx=quad(-61.0, 61.0, 2.0, 18.0), uv=[[0, 0]] * 4, sub={'0': [0, 1, 3, 3, 1, 2]}), parts=dict(buttonId=button, gamepad=1))
    def text(i, parent_idx, x): return dict(id=i, par=parent_idx, pos=[x, 20.0, 83.5], act=True, mats=[dict(sheet='font', part=None, color=[1, 1, 1, 1], shader='font', offset=None)], text=dict(font='font', alignment=1, anchor=4, lineSpacing=0.8, characterSize=10.5, text=None))
    nodes = [border, plate(2, -67.5, 0), text(3, 2, -67.5), plate(4, 67.5, 1), text(5, 4, 67.5)]
    for n in nodes[1:]:
        if 'parts' not in n: n['parts'] = {}
    t = dict(name='Make_YesNo()', nodes=nodes, parts=[], params=[], codes=[], builds=[])
    return types.SimpleNamespace(types={'1': t}, borders=[], hdr={})


@unittest.skipIf(UM is None, 'ui_menu non importable ici (%r)' % (IMPORT_ERROR,))
class Stacking(unittest.TestCase):
    def wnd(self): return UM.Window(yes_no_template(), 1)

    def test_no_under_yes(self):
        wnd = self.wnd(); yes, no = wnd.N[2], wnd.N[4]
        self.assertEqual(no['pos'][0], yes['pos'][0])                                        # même colonne
        self.assertEqual(yes['pos'][2], 62.5)                                                 # « Oui » n'a pas bougé
        self.assertAlmostEqual(yes['pos'][2] - no['pos'][2], 48.0 + UM.Window.YES_NO_SPACING)       # un panneau (48) + une unité
        self.assertEqual((wnd.N[5]['pos'][0], wnd.N[5]['pos'][2]), (wnd.N[3]['pos'][0], wnd.N[3]['pos'][2] - 49.0))      # le texte de « Non » a suivi sa plaque

    def test_border_follows_plates(self):
        wnd = self.wnd(); v = wnd.N[1]['vtx']
        left, right = v[:4], v[4:]
        self.assertEqual((min(p[0] for p in right), max(p[0] for p in right)), (min(p[0] for p in left), max(p[0] for p in left)))      # même colonne
        self.assertAlmostEqual(max(p[1] for p in left) - min(p[1] for p in right), 48.0 + 48.0 + 1.0)                                      # « Non » juste sous « Oui », une unité entre les panneaux

    def test_extents(self):
        wnd = self.wnd()
        self.assertEqual(wnd.extent(), (87.0 - 48.0 - 49.0, 87.0))                              # (-10 ; 87) : deux panneaux l'un sur l'autre
        self.assertEqual(wnd.extent_x(), (-134.5, -0.5))                                        # une seule colonne, celle de gauche

    def test_stacked_touch_zones(self):
        wnd = self.wnd(); z = {b[0]: b for b in wnd.buttons()}
        self.assertEqual(set(z), {0, 1})
        self.assertEqual((z[0][2], z[0][4]), (z[1][2], z[1][4]))                                # mêmes bords gauche et droit
        self.assertGreater(z[0][3], z[1][5])                                                    # « Oui » (0) entièrement au-dessus de « Non » (1)

    def test_other_layout_intact(self):
        ml = yes_no_template(); ml.types['1']['nodes'] = [n for n in ml.types['1']['nodes'] if n['id'] not in (4, 5)]      # une seule plaque : rien à empiler
        wnd = UM.Window(ml, 1); self.assertEqual(wnd.N[2]['pos'], [-67.5, 14.0, 62.5]); self.assertEqual(wnd.extent(), (39.0, 87.0))
        ml = yes_no_template(); ml.types['1']['name'] = 'Make_Autre()'; wnd = UM.Window(ml, 1)                                    # un autre type de fenêtre
        self.assertEqual((wnd.N[4]['pos'], wnd.extent()), ([67.5, 14.0, 62.5], (39.0, 87.0)))

    def test_gap_equals_one_visible_unit(self):
        self.assertEqual(K.YESNO_BOX_SPACING, 1.0); self.assertEqual(UM.Window.YES_NO_SPACING, 1.0)


@unittest.skipIf(UM is None, 'ui_menu non importable ici (%r)' % (IMPORT_ERROR,))
class VisibleEdges(unittest.TestCase):
    """Case de 10 x 6 unités sur une feuille de 16 x 8 pixels (la case couvre les colonnes 0 à 15, les rangées 0 à 3 : u de 0 à 1, v de 0 à -0,5)."""
    QUAD = ([[0.0, 0.0], [10.0, 0.0], [10.0, -6.0], [0.0, -6.0]], [[0.0, 0.0], [1.0, 0.0], [1.0, -0.5], [0.0, -0.5]], [0, 1, 3, 3, 1, 2])

    def alpha(self):
        a = np.zeros((8, 16), np.uint8); a[1:4, 2:14] = 255                                     # dessin : colonnes 2 à 13, rangées 1 à 3
        a[0, :] = 100; a[:, 1] = 100                                                            # sous le seuil : ne compte pas
        return a

    def test_drawing_edge_not_mesh_edge(self):
        x0, x1, z0, z1 = UM.visible_edges(*self.QUAD, self.alpha())
        self.assertAlmostEqual(x0, 10 * 2 / 16.0); self.assertAlmostEqual(x1, 10 * 14 / 16.0)          # 1,25 et 8,75
        self.assertAlmostEqual(z1, -6 * 1 / 4.0); self.assertAlmostEqual(z0, -6 * 4 / 4.0)             # rangée 1 sur 4 depuis le haut ; bas de la rangée 3 = bas de la case

    def test_threshold(self):
        r = UM.visible_edges(*self.QUAD, self.alpha(), threshold=50)                               # avec un seuil bas la rangée 0 (opacité 100, sur toute la largeur) compte : bords de la case entière
        self.assertAlmostEqual(r[0], 0.0); self.assertAlmostEqual(r[1], 10.0); self.assertAlmostEqual(r[3], 0.0)

    def test_nothing_visible(self):
        self.assertIsNone(UM.visible_edges(*self.QUAD, np.zeros((8, 16), np.uint8)))

    def test_several_cells(self):
        """Deux cases côte à côte : les bords sont ceux de l'ensemble."""
        vtx = [[0.0, 0.0], [5.0, 0.0], [5.0, -6.0], [0.0, -6.0], [5.0, 0.0], [10.0, 0.0], [10.0, -6.0], [5.0, -6.0]]
        uv = [[0.0, 0.0], [0.5, 0.0], [0.5, -0.5], [0.0, -0.5], [0.5, 0.0], [1.0, 0.0], [1.0, -0.5], [0.5, -0.5]]
        r = UM.visible_edges(vtx, uv, [0, 1, 3, 3, 1, 2, 4, 5, 7, 7, 5, 6], self.alpha())
        self.assertAlmostEqual(r[0], 1.25); self.assertAlmostEqual(r[1], 8.75)


class FakeBorder:
    """Fenêtre qui ne sait que donner son étendue visible (x0, x1, z0, z1)."""
    def __init__(self, v): self.v = v
    def visible_extent(self): return self.v


@unittest.skipIf(MenusMixin is None, 'fenetre non importable ici (%r)' % (IMPORT_ERROR,))
class Pose(unittest.TestCase):
    MSG = (-223.0 + 6.0, 229.0 - 6.0, -165.0, -43.5)              # boîte de dialogue : bords visibles
    STACK = (-134.5, -0.5, -10.0, 87.0)                            # pile Oui / Non : bords visibles de sa mise en page d'origine

    def pose(self, msg=None, stack=None): return MenusMixin._yesno_on_message(None, FakeBorder(msg or self.MSG), FakeBorder(stack or self.STACK))

    def test_bottom_edge_of_stack_on_top_edge_of_box(self):
        dz, (bm, bp) = self.pose()
        self.assertAlmostEqual(self.STACK[2] + dz, self.MSG[3] + K.YESNO_BOX_SPACING)              # bas de la pile (décalé) = haut de la boîte + 1
        self.assertEqual((bm, bp), (self.MSG[1], self.STACK[1]))

    def test_missing_measure(self):
        self.assertIsNone(MenusMixin._yesno_on_message(None, None, FakeBorder(self.STACK)))
        self.assertIsNone(MenusMixin._yesno_on_message(None, FakeBorder(self.MSG), FakeBorder(None)))

    def test_right_edge_aligned_at_any_scale(self):
        """Quelle que soit la taille réglée par le joueur (v[0]), le bord droit de la pile est celui de la boîte (tant que le joueur ne la décale pas) ; le bord bas aussi autour de son pied."""
        game = types.SimpleNamespace(width=1280, height=720); dz, edges = self.pose()
        base = (640.0, 300.0, 0.9)                                                          # (centre x, bas y, échelle) de la boîte
        for scale_factor in (0.5, 1.0, 1.3, 2.0):
            cx, cy, s2 = MenusMixin._ui_yesno(game, base, dz, self.STACK[2], (scale_factor, 0.0, 0.0), edges)
            self.assertAlmostEqual(cx + self.STACK[1] * s2, base[0] + self.MSG[1] * base[2], places=6)         # bords droits
            self.assertAlmostEqual(cy + self.STACK[2] * s2, base[1] + (dz + self.STACK[2]) * base[2], places=6)  # bord bas : ne bouge pas avec la taille

    def test_relative_position_setting(self):
        game = types.SimpleNamespace(width=1000, height=500); dz, edges = self.pose(); base = (500.0, 200.0, 1.0)
        a = MenusMixin._ui_yesno(game, base, dz, self.STACK[2], (1.0, 0.0, 0.0), edges); b = MenusMixin._ui_yesno(game, base, dz, self.STACK[2], (1.0, 0.1, -0.2), edges)
        self.assertAlmostEqual(b[0] - a[0], 100.0); self.assertAlmostEqual(b[1] - a[1], -100.0)

    def test_without_edges_nothing_changes(self):
        """Sans mesure (bords = None) la pile garde son ancienne pose : x = centre de la boîte + décalage."""
        game = types.SimpleNamespace(width=1000, height=500)
        self.assertEqual(MenusMixin._ui_yesno(game, (500.0, 200.0, 1.0), 0.0, 0.0, (1.0, 0.0, 0.0))[0], 500.0)


class Code(unittest.TestCase):
    """Sans pyglet : la pose est branchée aux endroits qui comptent (dessin, zones de clic, aperçu de l'éditeur)."""
    def source(self, *path):
        with open(os.path.join(ROOT, *path), encoding='utf-8') as f: return f.read()

    def test_yes_no_border_stacks_on_creation(self):
        tree = ast.parse(self.source('dq4_pc', 'menus', 'ui_menu.py'))
        init = [n for c in ast.walk(tree) if isinstance(c, ast.ClassDef) and c.name == 'Window' for n in c.body if isinstance(n, ast.FunctionDef) and n.name == '__init__'][0]
        calls = [n.func.attr for n in ast.walk(init) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertIn('_push_yes_no', calls)

    def test_drawing_click_and_preview_use_same_pose(self):
        src = self.source('dq4_pc', 'window', 'menu_display.py')
        self.assertGreaterEqual(src.count('_yesno_on_message('), 3)                       # définition + dessin + aperçu de l'éditeur
        self.assertIn("ui_edges", src); self.assertIn("self.ui_tf[p] = (t2[0], t2[1] - D * t2[2], t2[2])", src)      # zones de clic = repère de dessin


@unittest.skipIf(UM is None, 'ui_menu non importable ici (%r)' % (IMPORT_ERROR,))
class RealPageLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        l = os.path.join(CACHE, 'ui_layout.json')
        if not os.path.exists(l): raise unittest.SkipTest("cache d'interface absent : " + CACHE)
        cls.ml = UM.PageLayout(l, os.path.join(CACHE, 'ui_frameData.bin'))

    def test_real_window_stack(self):
        wnd = UM.Window(self.ml, 1); self.assertEqual(wnd.t['name'][:11], 'Make_YesNo(')
        e = wnd.extent(); self.assertAlmostEqual(e[0], -10.0); self.assertAlmostEqual(e[1], 87.0)
        x = wnd.extent_x(); self.assertAlmostEqual(x[0], -134.5); self.assertAlmostEqual(x[1], -0.5)

    def test_yes_above_no(self):
        z = {b[0]: b for b in UM.Window(self.ml, 1).buttons()}
        self.assertEqual(set(z), {0, 1}); self.assertGreater(z[0][3], z[1][5]); self.assertEqual((z[0][2], z[0][4]), (z[1][2], z[1][4]))


if __name__ == '__main__':
    unittest.main(verbosity=1)
