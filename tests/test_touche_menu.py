"""Test de la touche « Menu » (menu du terrain : Objets / Magie / Carac. / Divers) : defaut Entree et Tab, migration d'un ancien reglages.json (sans ecraser un choix du joueur), Tab libre ailleurs, ligne de la page
Commandes et bouton ↺ (vrai code de reglages.py, de pause.py et, sans fenetre, de Jeu.on_key_press / _fronts).

    python3 outils/test_touche_menu.py
"""
import glob, json, os, re, sys, tempfile, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..')); sys.path.insert(0, ICI)
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.persistance import reglages as RG
import test_pause_pages as TP

K = pyglet.window.key


def charger(contenu):
    f = os.path.join(tempfile.mkdtemp(prefix='rg_menu_'), 'reglages.json')
    with open(f, 'w', encoding='utf-8') as fh: json.dump(contenu, fh)
    return RG.Reglages(f), f


class Defaut(unittest.TestCase):
    def test_entree_et_tab(self):
        self.assertEqual(RG.TOUCHES_DEF['menu'], ['RETURN', 'TAB']); self.assertEqual(RG.Reglages(None)['touches']['menu'], ['RETURN', 'TAB'])
        r = RG.Reglages(None)
        self.assertEqual(r.action_de(K.TAB), 'menu'); self.assertEqual(r.codes('menu'), (K.RETURN, K.TAB))          # (action_de(K.RETURN) est None : pyglet nomme 0xff0d « ENTER » ; le jeu lit les touches par `codes`, voir Jeu._tenue)
        self.assertEqual(dict(RG.ACTIONS)['menu'], 'Menu')

    def test_tab_n_est_a_aucune_autre_action(self):
        for a, ts in RG.TOUCHES_DEF.items():
            if a != 'menu': self.assertNotIn('TAB', ts, a)
        self.assertNotIn('TAB', RG.RESERVEES); self.assertNotIn('RETURN', RG.RESERVEES)
        tous = [n for ts in RG.TOUCHES_DEF.values() for n in ts if n]
        self.assertEqual(len(tous), len(set(tous)), 'une touche ne sert qu\'a une action')

    def test_tab_ailleurs_dans_le_code(self):
        """Les seuls usages de Tab (K.TAB) : replier le panneau de l'editeur d'interface (menu Pause), changer de mode dans la saisie du nom, passer au bouton suivant de l'ecran Sauvegardes. Ces trois ecrans
        prennent la touche dans Jeu.on_key_press AVANT les actions du jeu (menu Pause ouvert, saisie du nom, ecran Sauvegardes) : Tab n'y est jamais la touche « Menu ». Un nouvel usage doit etre examine ici."""
        ici = os.path.join(ICI, '..', 'dq4_pc'); trouves = set()
        for f in glob.glob(os.path.join(ici, '**', '*.py'), recursive=True):
            with open(f, encoding='utf-8') as fh:
                if re.search(r'\bK\.TAB\b', fh.read()): trouves.add(os.path.basename(f))
        self.assertEqual(trouves, {'pause.py', 'saisie_nom.py', 'ecran_sauvegardes.py'})


class Migration(unittest.TestCase):
    def test_ancien_defaut_recoit_tab(self):
        for v in (3, 4):
            r, _ = charger({'touches_v': v, 'touches': {'menu': ['RETURN', None], 'carte': ['M', None], 'A': ['SPACE', None]}})
            self.assertEqual(r['touches']['menu'], ['RETURN', 'TAB'], 'touches_v %d' % v)
        r, _ = charger({'touches_v': 4, 'touches': {k: list(v) for k, v in RG.TOUCHES_DEF.items() if k != 'menu'} | {'menu': ['RETURN']}}); self.assertEqual(r['touches']['menu'], ['RETURN', 'TAB'])       # (liste d'une seule touche)
        r, _ = charger({'touches_v': 4, 'touches': {k: list(v) for k, v in RG.TOUCHES_DEF.items()} | {'menu': ['RETURN', None]}}); self.assertEqual(r['touches']['menu'], ['RETURN', 'TAB'])      # (fichier complet d'avant)

    def test_choix_du_joueur_conserve(self):
        for menu in (['E', None], ['RETURN', 'F2'], ['F2', None], [None, None], ['SPACE', 'RETURN'], [None, 'RETURN'], ['E', 'RETURN']):
            r, _ = charger({'touches_v': 4, 'touches': {'menu': list(menu), 'A': ['SPACE', None]}}); self.assertEqual(r['touches']['menu'], menu, menu)

    def test_tab_deja_pris_par_une_autre_action(self):
        r, _ = charger({'touches_v': 4, 'touches': {'menu': ['RETURN', None], 'infos': ['TAB', None]}})
        self.assertEqual(r['touches']['menu'], ['RETURN', None]); self.assertEqual(r['touches']['infos'], ['TAB', None]); self.assertEqual(r.action_de(K.TAB), 'infos')      # le choix du joueur prime

    def test_une_seule_fois(self):
        """Apres la migration le fichier est enregistre en v5 : Tab retire ensuite par le joueur (case videe) n'est pas remis."""
        r, f = charger({'touches_v': 4, 'touches': {'menu': ['RETURN', None]}}); r.enregistrer()
        with open(f, encoding='utf-8') as fh: d = json.load(fh)
        self.assertEqual((d['touches_v'], d['touches']['menu']), (5, ['RETURN', 'TAB']))
        r2 = RG.Reglages(f); r2.delier('menu', 1); r2.enregistrer()
        self.assertEqual(RG.Reglages(f)['touches']['menu'], ['RETURN', None])
        r3, _ = charger({'touches_v': 5, 'touches': {'menu': ['RETURN', None]}}); self.assertEqual(r3['touches']['menu'], ['RETURN', None])

    def test_fichiers_sans_touches_ou_trop_anciens(self):
        for contenu in ({}, {'son': False}, {'touches_v': 2, 'touches': {'menu': ['RETURN', None]}}, {'touches': {'menu': ['RETURN', None]}}):
            r, _ = charger(contenu); self.assertEqual(r['touches']['menu'], ['RETURN', 'TAB'], contenu)                      # (touches abandonnees ou absentes : les defauts)

    def test_les_autres_touches_ne_bougent_pas(self):
        r, _ = charger({'touches_v': 4, 'touches': {'menu': ['RETURN', None], 'haut': ['W', None], 'carte': ['N', None]}})
        self.assertEqual((r['touches']['haut'], r['touches']['carte'], r['touches']['historique']), (['W', None], ['N', None], ['H', None]))


class PageCommandes(unittest.TestCase):
    def test_ligne_et_bouton_defaut(self):
        J, p = TP.menu('commandes'); e = TP.par_libelle(p, 'Menu')
        self.assertEqual((e['t'], e['act'], e['v']), ('touche', 'menu', ['Entrée', 'Tab'])); self.assertTrue(e['est_defaut']())
        J.reg.lier('menu', 1, K.F2); J.reg.lier('menu', 0, K.E)
        e = TP.par_libelle(p, 'Menu'); self.assertEqual(e['v'], ['E', 'F2']); self.assertFalse(e['est_defaut']())
        e['defaut'](); e = TP.par_libelle(p, 'Menu')                                                          # ↺ : les deux touches reviennent
        self.assertEqual((e['v'], J.reg['touches']['menu']), (['Entrée', 'Tab'], ['RETURN', 'TAB'])); self.assertTrue(e['est_defaut']())

    def test_defaut_reprend_tab_a_une_autre_action(self):
        J, p = TP.menu('commandes'); J.reg.lier('infos', 0, K.TAB)                                            # Tab donne a « Infos » : « Menu » n'a plus que Entree
        self.assertEqual(J.reg['touches']['menu'], ['RETURN', None]); e = TP.par_libelle(p, 'Menu'); self.assertFalse(e['est_defaut']())
        e['defaut'](); self.assertEqual(J.reg['touches']['menu'], ['RETURN', 'TAB']); self.assertEqual(J.reg['touches']['infos'], [None, None])      # ↺ reprend Tab (et le dit : message)
        self.assertIn('Infos', p.message[0])
        J.reg.lier('menu', 0, K.F3); J.reg.touches_par_defaut(); self.assertEqual(J.reg['touches']['menu'], ['RETURN', 'TAB'])         # « Rétablir les touches par défaut » aussi

    def test_capture_de_tab(self):
        """Lier Tab a « Menu » dans la page Commandes (case secondaire) : la capture de touche prend Tab comme n'importe quelle touche."""
        J, p = TP.menu('commandes'); J.reg.delier('menu', 1)
        p.capture = ('menu', 1); p.touche(K.TAB, 0); self.assertEqual(J.reg['touches']['menu'], ['RETURN', 'TAB']); self.assertIsNone(p.capture)

    def test_tab_replie_le_panneau_de_l_editeur(self):
        """Dans l'editeur d'interface, Tab replie le panneau (il ne declenche rien d'autre) ; hors editeur, Tab ne fait rien dans le menu Pause."""
        J, p = TP.menu('interface'); self.assertFalse(p.plie)
        p.touche(K.TAB, 0); self.assertTrue(p.plie); p.touche(K.TAB, 0); self.assertFalse(p.plie)
        J, p = TP.menu('affichage'); avant = dict(p.sel); p.touche(K.TAB, 0); self.assertEqual((p.ecran, p.sel), ('affichage', avant))


class DansLaFenetre(unittest.TestCase):
    """Vrai code de Jeu.on_key_press / _fronts sur un faux Jeu (comme test_mode_fenetre.py)."""
    @classmethod
    def setUpClass(cls):
        try: from dq4_pc.fenetre import jeu as fenetre; cls.FE = fenetre
        except Exception as ex: raise unittest.SkipTest('fenetre.py non importable ici (%r)' % (ex,))

    def faux_jeu(self, pause=False, nom=False):
        FE = self.FE
        j = types.SimpleNamespace(avalees=set(), alt_cand=False, alt_tap=False, reg=RG.Reglages(None), touches=K.KeyStateHandler(), act_prec={}, n=0, _pret=True, combo=[False, False], _logo_touche=False, appuis_pause=0, appuis_nom=0,
                                  pause=None, sauv=None, licence=None, titre=None, dernier_peripherique='', bascules=0, annulations=0, est_plein=False, souris=(0, 0), garde_souris=__import__('dq4_pc.fenetre.entrees', fromlist=['GardeSouris']).GardeSouris(), aide=False)
        j.pause = types.SimpleNamespace(ouvert=pause, capture=None, touche=lambda sym, mods: setattr(j, 'appuis_pause', j.appuis_pause + 1))
        j.saisie_nom = types.SimpleNamespace(touche=lambda sym, mods: setattr(j, 'appuis_nom', j.appuis_nom + 1))
        j.basculer_plein_ecran = lambda: setattr(j, 'bascules', j.bascules + 1)
        j._tenue = lambda a: FE.Jeu._tenue(j, a); j._saisie_nom_en_cours = lambda: nom; j._num_etat = FE.Jeu._num_etat; j._raccourci_fenetre = lambda sym, mods: FE.Jeu._raccourci_fenetre(j, sym, mods)
        j.annuler_chargement = lambda: None
        return j

    def appui(self, j, sym):
        j.touches.on_key_press(sym, 0); return self.FE.Jeu.on_key_press(j, sym, 0)

    def test_tab_comme_entree_sur_le_terrain(self):
        for sym in (K.RETURN, K.TAB):
            j = self.faux_jeu(); self.appui(j, sym); self.assertTrue(self.FE.Jeu._fronts(j)['menu'], sym)                # un appui = un front « Menu » (ouvre le menu du terrain, valide, tourne les pages des messages)
            j.touches.on_key_release(sym, 0); self.assertFalse(self.FE.Jeu._fronts(j)['menu'])
        j = self.faux_jeu(); self.appui(j, K.TAB); self.appui(j, K.RETURN); self.assertTrue(self.FE.Jeu._fronts(j)['menu']); self.assertFalse(self.FE.Jeu._fronts(j)['menu'])          # les deux ensemble : un seul front

    def test_tab_pris_avant_les_actions_dans_le_menu_et_la_saisie_du_nom(self):
        j = self.faux_jeu(pause=True); self.appui(j, K.TAB); self.assertEqual(j.appuis_pause, 1)                    # menu Pause : la touche lui appartient
        j = self.faux_jeu(nom=True); self.appui(j, K.TAB); self.assertEqual(j.appuis_nom, 1)                         # saisie du nom : Tab change de mode (saisie_nom.py)
        j = self.faux_jeu(); j.sauv = types.SimpleNamespace(touche=lambda sym, mods: setattr(j, 'appuis_nom', 7)); self.appui(j, K.TAB); self.assertEqual(j.appuis_nom, 7)      # ecran Sauvegardes : bouton suivant


if __name__ == '__main__':
    unittest.main(verbosity=1)
