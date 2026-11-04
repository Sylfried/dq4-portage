"""Oui / Non empilés en haut à droite de la boîte de dialogue, comme sur DS (D-231 ; demande de Sylfried du 04/11/2026 à 23 h 02 : « tu les mets l'un sur l'autre posé sur le coin en haut à droite de la boîte de dialogue
avec les bords droits alignés »), sans fenêtre ni moteur :

  1. `Fenetre` de type 1 (Make_YesNo) : la plaque « Non » passe sous « Oui » (même colonne, une unité entre les deux), avec son texte ; son panneau du cadre la suit ; l'étendue verticale grandit d'un panneau, l'étendue horizontale
     est celle d'une seule colonne ; les zones tactiles sont empilées (Oui en haut) ; une autre mise en page (pas deux plaques) n'est pas touchée ;
  2. `bords_visibles` : le bord VISIBLE d'une maille de cadre (les colonnes et les rangées de la feuille dont l'opacité dépasse le seuil), pas le bord de la maille ;
  3. `_ouinon_sur_message` / `_ui_ouinon` : la pile pose son bord bas VISIBLE `OUINON_ECART` au-dessus du bord haut visible de la boîte, et son bord droit visible sur celui de la boîte, à toutes les échelles du joueur ;
  4. (si le cache d'interface existe : DQ_UI_CACHE ou DQ_CACHE_UI, sinon /tmp/uicache4) la VRAIE mise en page : (-10 ; 87) sur une colonne de -134,5 à -0,5 ; clavier et clic inchangés (haut = Oui, bas = Non).

    python3 tests/test_oui_non_empile.py        (pyglet seul est nécessaire ; sans pyglet les tests sont passés)
"""
import ast, os, sys, types, unittest

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, RACINE)
os.environ.setdefault('PYGLET_HEADLESS', '1')
CACHE = os.environ.get('DQ_UI_CACHE') or os.environ.get('DQ_CACHE_UI') or '/tmp/uicache4'

try:
    import numpy as np
    from dq4_pc.menus import ui_menu as UM
    from dq4_pc.fenetre import constantes as K
    from dq4_pc.fenetre.affichage_menus import MenusMixin
    ERREUR_IMPORT = None
except Exception as ex:                                       # (CI : ni pyglet ni fenetre)
    UM = K = MenusMixin = np = None; ERREUR_IMPORT = ex


def gabarit_oui_non(ecart_plaques=1.0):
    """Mise en page minimale de Make_YesNo (même structure que l'export du jeu) : cadre (z 87) de deux panneaux de 134 x 48 (x -134,5..-0,5 et 0,5..134,5, une case chacun), deux plaques (x -67,5 et 67,5, z 62,5) et leurs textes."""
    def quad(x0, x1, z0, z1): return [[x0, z1], [x1, z1], [x1, z0], [x0, z0]]
    mat = lambda feuille, part: [dict(sheet=feuille, part=part, color=None, shader='parts', offset=None)]
    cadre = dict(id=1, par=None, pos=[0.0, 10.0, 87.0], act=True, mats=mat(0, 4), mesh=dict(vtx=quad(-134.5, -0.5, -48.0, 0.0) + quad(0.5, 134.5, -48.0, 0.0), uv=[[0, 0]] * 8, sub={'0': [0, 1, 3, 3, 1, 2, 4, 5, 7, 7, 5, 6]}))
    def plaque(i, x, bouton):
        return dict(id=i, par=1, pos=[x, 14.0, 62.5], act=True, mats=mat(1, 7), mesh=dict(vtx=quad(-61.0, 61.0, 2.0, 18.0), uv=[[0, 0]] * 4, sub={'0': [0, 1, 3, 3, 1, 2]}), parts=dict(buttonId=bouton, gamepad=1))
    def texte(i, par, x): return dict(id=i, par=par, pos=[x, 20.0, 83.5], act=True, mats=[dict(sheet='font', part=None, color=[1, 1, 1, 1], shader='font', offset=None)], text=dict(font='font', alignment=1, anchor=4, lineSpacing=0.8, characterSize=10.5, text=None))
    noeuds = [cadre, plaque(2, -67.5, 0), texte(3, 2, -67.5), plaque(4, 67.5, 1), texte(5, 4, 67.5)]
    for n in noeuds[1:]:
        if 'parts' not in n: n['parts'] = {}
    t = dict(name='Make_YesNo()', nodes=noeuds, parts=[], params=[], codes=[], builds=[])
    return types.SimpleNamespace(types={'1': t}, cadres=[], hdr={})


@unittest.skipIf(UM is None, 'ui_menu non importable ici (%r)' % (ERREUR_IMPORT,))
class Empilement(unittest.TestCase):
    def fe(self): return UM.Fenetre(gabarit_oui_non(), 1)

    def test_non_sous_oui(self):
        fe = self.fe(); oui, non = fe.N[2], fe.N[4]
        self.assertEqual(non['pos'][0], oui['pos'][0])                                        # même colonne
        self.assertEqual(oui['pos'][2], 62.5)                                                 # « Oui » n'a pas bougé
        self.assertAlmostEqual(oui['pos'][2] - non['pos'][2], 48.0 + UM.Fenetre.ECART_OUI_NON)       # un panneau (48) + une unité
        self.assertEqual((fe.N[5]['pos'][0], fe.N[5]['pos'][2]), (fe.N[3]['pos'][0], fe.N[3]['pos'][2] - 49.0))      # le texte de « Non » a suivi sa plaque

    def test_le_cadre_suit_les_plaques(self):
        fe = self.fe(); v = fe.N[1]['vtx']
        gauche, droite = v[:4], v[4:]
        self.assertEqual((min(p[0] for p in droite), max(p[0] for p in droite)), (min(p[0] for p in gauche), max(p[0] for p in gauche)))      # même colonne
        self.assertAlmostEqual(max(p[1] for p in gauche) - min(p[1] for p in droite), 48.0 + 48.0 + 1.0)                                      # « Non » juste sous « Oui », une unité entre les panneaux

    def test_etendues(self):
        fe = self.fe()
        self.assertEqual(fe.etendue(), (87.0 - 48.0 - 49.0, 87.0))                              # (-10 ; 87) : deux panneaux l'un sur l'autre
        self.assertEqual(fe.etendue_x(), (-134.5, -0.5))                                        # une seule colonne, celle de gauche

    def test_zones_tactiles_empilees(self):
        fe = self.fe(); z = {b[0]: b for b in fe.boutons()}
        self.assertEqual(set(z), {0, 1})
        self.assertEqual((z[0][2], z[0][4]), (z[1][2], z[1][4]))                                # mêmes bords gauche et droit
        self.assertGreater(z[0][3], z[1][5])                                                    # « Oui » (0) entièrement au-dessus de « Non » (1)

    def test_autre_mise_en_page_intacte(self):
        ml = gabarit_oui_non(); ml.types['1']['nodes'] = [n for n in ml.types['1']['nodes'] if n['id'] not in (4, 5)]      # une seule plaque : rien à empiler
        fe = UM.Fenetre(ml, 1); self.assertEqual(fe.N[2]['pos'], [-67.5, 14.0, 62.5]); self.assertEqual(fe.etendue(), (39.0, 87.0))
        ml = gabarit_oui_non(); ml.types['1']['name'] = 'Make_Autre()'; fe = UM.Fenetre(ml, 1)                                    # un autre type de fenêtre
        self.assertEqual((fe.N[4]['pos'], fe.etendue()), ([67.5, 14.0, 62.5], (39.0, 87.0)))

    def test_ecart_vaut_une_unite_visible(self):
        self.assertEqual(K.OUINON_ECART, 1.0); self.assertEqual(UM.Fenetre.ECART_OUI_NON, 1.0)


@unittest.skipIf(UM is None, 'ui_menu non importable ici (%r)' % (ERREUR_IMPORT,))
class BordsVisibles(unittest.TestCase):
    """Case de 10 x 6 unités sur une feuille de 16 x 8 pixels (la case couvre les colonnes 0 à 15, les rangées 0 à 3 : u de 0 à 1, v de 0 à -0,5)."""
    QUAD = ([[0.0, 0.0], [10.0, 0.0], [10.0, -6.0], [0.0, -6.0]], [[0.0, 0.0], [1.0, 0.0], [1.0, -0.5], [0.0, -0.5]], [0, 1, 3, 3, 1, 2])

    def alpha(self):
        a = np.zeros((8, 16), np.uint8); a[1:4, 2:14] = 255                                     # dessin : colonnes 2 à 13, rangées 1 à 3
        a[0, :] = 100; a[:, 1] = 100                                                            # sous le seuil : ne compte pas
        return a

    def test_bord_du_dessin_et_non_de_la_maille(self):
        x0, x1, z0, z1 = UM.bords_visibles(*self.QUAD, self.alpha())
        self.assertAlmostEqual(x0, 10 * 2 / 16.0); self.assertAlmostEqual(x1, 10 * 14 / 16.0)          # 1,25 et 8,75
        self.assertAlmostEqual(z1, -6 * 1 / 4.0); self.assertAlmostEqual(z0, -6 * 4 / 4.0)             # rangée 1 sur 4 depuis le haut ; bas de la rangée 3 = bas de la case

    def test_seuil(self):
        r = UM.bords_visibles(*self.QUAD, self.alpha(), seuil=50)                               # avec un seuil bas la rangée 0 (opacité 100, sur toute la largeur) compte : bords de la case entière
        self.assertAlmostEqual(r[0], 0.0); self.assertAlmostEqual(r[1], 10.0); self.assertAlmostEqual(r[3], 0.0)

    def test_rien_de_visible(self):
        self.assertIsNone(UM.bords_visibles(*self.QUAD, np.zeros((8, 16), np.uint8)))

    def test_plusieurs_cases(self):
        """Deux cases côte à côte : les bords sont ceux de l'ensemble."""
        vtx = [[0.0, 0.0], [5.0, 0.0], [5.0, -6.0], [0.0, -6.0], [5.0, 0.0], [10.0, 0.0], [10.0, -6.0], [5.0, -6.0]]
        uv = [[0.0, 0.0], [0.5, 0.0], [0.5, -0.5], [0.0, -0.5], [0.5, 0.0], [1.0, 0.0], [1.0, -0.5], [0.5, -0.5]]
        r = UM.bords_visibles(vtx, uv, [0, 1, 3, 3, 1, 2, 4, 5, 7, 7, 5, 6], self.alpha())
        self.assertAlmostEqual(r[0], 1.25); self.assertAlmostEqual(r[1], 8.75)


class FauxCadre:
    """Fenêtre qui ne sait que donner son étendue visible (x0, x1, z0, z1)."""
    def __init__(self, v): self.v = v
    def etendue_visible(self): return self.v


@unittest.skipIf(MenusMixin is None, 'fenetre non importable ici (%r)' % (ERREUR_IMPORT,))
class Pose(unittest.TestCase):
    MSG = (-223.0 + 6.0, 229.0 - 6.0, -165.0, -43.5)              # boîte de dialogue : bords visibles
    PILE = (-134.5, -0.5, -10.0, 87.0)                            # pile Oui / Non : bords visibles de sa mise en page d'origine

    def pose(self, msg=None, pile=None): return MenusMixin._ouinon_sur_message(None, FauxCadre(msg or self.MSG), FauxCadre(pile or self.PILE))

    def test_bord_bas_de_la_pile_sur_le_bord_haut_de_la_boite(self):
        dz, (bm, bp) = self.pose()
        self.assertAlmostEqual(self.PILE[2] + dz, self.MSG[3] + K.OUINON_ECART)              # bas de la pile (décalé) = haut de la boîte + 1
        self.assertEqual((bm, bp), (self.MSG[1], self.PILE[1]))

    def test_mesure_manquante(self):
        self.assertIsNone(MenusMixin._ouinon_sur_message(None, None, FauxCadre(self.PILE)))
        self.assertIsNone(MenusMixin._ouinon_sur_message(None, FauxCadre(self.MSG), FauxCadre(None)))

    def test_bord_droit_aligne_a_toute_echelle(self):
        """Quelle que soit la taille réglée par le joueur (v[0]), le bord droit de la pile est celui de la boîte (tant que le joueur ne la décale pas) ; le bord bas aussi autour de son pied."""
        jeu = types.SimpleNamespace(width=1280, height=720); dz, bords = self.pose()
        base = (640.0, 300.0, 0.9)                                                          # (centre x, bas y, échelle) de la boîte
        for echelle in (0.5, 1.0, 1.3, 2.0):
            cx, cy, s2 = MenusMixin._ui_ouinon(jeu, base, dz, self.PILE[2], (echelle, 0.0, 0.0), bords)
            self.assertAlmostEqual(cx + self.PILE[1] * s2, base[0] + self.MSG[1] * base[2], places=6)         # bords droits
            self.assertAlmostEqual(cy + self.PILE[2] * s2, base[1] + (dz + self.PILE[2]) * base[2], places=6)  # bord bas : ne bouge pas avec la taille

    def test_reglage_de_position_relatif(self):
        jeu = types.SimpleNamespace(width=1000, height=500); dz, bords = self.pose(); base = (500.0, 200.0, 1.0)
        a = MenusMixin._ui_ouinon(jeu, base, dz, self.PILE[2], (1.0, 0.0, 0.0), bords); b = MenusMixin._ui_ouinon(jeu, base, dz, self.PILE[2], (1.0, 0.1, -0.2), bords)
        self.assertAlmostEqual(b[0] - a[0], 100.0); self.assertAlmostEqual(b[1] - a[1], -100.0)

    def test_sans_bords_rien_ne_change(self):
        """Sans mesure (bords = None) la pile garde son ancienne pose : x = centre de la boîte + décalage."""
        jeu = types.SimpleNamespace(width=1000, height=500)
        self.assertEqual(MenusMixin._ui_ouinon(jeu, (500.0, 200.0, 1.0), 0.0, 0.0, (1.0, 0.0, 0.0))[0], 500.0)


class Code(unittest.TestCase):
    """Sans pyglet : la pose est branchée aux endroits qui comptent (dessin, zones de clic, aperçu de l'éditeur)."""
    def source(self, *chemin):
        with open(os.path.join(RACINE, *chemin), encoding='utf-8') as f: return f.read()

    def test_le_cadre_oui_non_s_empile_a_la_creation(self):
        arbre = ast.parse(self.source('dq4_pc', 'menus', 'ui_menu.py'))
        init = [n for c in ast.walk(arbre) if isinstance(c, ast.ClassDef) and c.name == 'Fenetre' for n in c.body if isinstance(n, ast.FunctionDef) and n.name == '__init__'][0]
        appels = [n.func.attr for n in ast.walk(init) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertIn('_empiler_oui_non', appels)

    def test_dessin_clic_et_apercu_utilisent_la_meme_pose(self):
        src = self.source('dq4_pc', 'fenetre', 'affichage_menus.py')
        self.assertGreaterEqual(src.count('_ouinon_sur_message('), 3)                       # définition + dessin + aperçu de l'éditeur
        self.assertIn("ui_bords", src); self.assertIn("self.ui_tf[p] = (t2[0], t2[1] - D * t2[2], t2[2])", src)      # zones de clic = repère de dessin


@unittest.skipIf(UM is None, 'ui_menu non importable ici (%r)' % (ERREUR_IMPORT,))
class VraieMiseEnPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        l = os.path.join(CACHE, 'ui_layout.json')
        if not os.path.exists(l): raise unittest.SkipTest("cache d'interface absent : " + CACHE)
        cls.ml = UM.MiseEnPage(l, os.path.join(CACHE, 'ui_frameData.bin'))

    def test_pile_de_la_vraie_fenetre(self):
        fe = UM.Fenetre(self.ml, 1); self.assertEqual(fe.t['name'][:11], 'Make_YesNo(')
        e = fe.etendue(); self.assertAlmostEqual(e[0], -10.0); self.assertAlmostEqual(e[1], 87.0)
        x = fe.etendue_x(); self.assertAlmostEqual(x[0], -134.5); self.assertAlmostEqual(x[1], -0.5)

    def test_oui_au_dessus_de_non(self):
        z = {b[0]: b for b in UM.Fenetre(self.ml, 1).boutons()}
        self.assertEqual(set(z), {0, 1}); self.assertGreater(z[0][3], z[1][5]); self.assertEqual((z[0][2], z[0][4]), (z[1][2], z[1][4]))


if __name__ == '__main__':
    unittest.main(verbosity=1)
