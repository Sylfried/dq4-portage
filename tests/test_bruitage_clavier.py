"""Test (#227, audit SND-08 / SND-09 / UI-01, regle de #60 / D-156) : le bruitage 300 des boutons de menu suit la regle du jeu d'origine, au doigt comme au clavier.

    python3 tests/test_bruitage_clavier.py

Original (MenuPortItem.Update, desassemblage) : a l'appui, `Sound.PlaySE(300)` seulement si la touche de manette du bouton est A (0x10) ou action (0x800). B (0x20), retour (0x400), fleches (1, 2, 4, 8) et zone 0x80 sont muets ;
les boutons du terrain (Carte, Commandes, Discussion : TouchPad.internalUpdate) jouent le bruitage. Le clavier joue le bruitage « dans les memes situations qu'au doigt » (D-156).

1. La regle (`bruit_bouton`) : une table de touches de manette.
2. `Boutons.permis` : les boutons du terrain permis par le moteur = ceux que `visibles` montre (sans le reglage d'affichage).
3. Vraies methodes de `Jeu` sur un faux jeu : clic sur un bouton (A / action : bruit ; B, fleches, retour, mode de la carte : muet), menu au clavier (A : bruit ; B, fleches de page, ▲ ▼, colonne : muet),
   touches Commandes / Discussion / Carte sur le terrain (bruit si le moteur autorise le bouton), carte ouverte (tout muet), lettres tapees dans la saisie du nom (une par lettre).
(Les parties 2 et 3 demandent pyglet : ignorees sans lui, comme dans la CI.)
"""
import inspect, os, sys, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..'))
from dq4_pc.fenetre.constantes import BTN_CARTE, BTN_DISCUSSION, BTN_MENU, SE_BOUTON, bruit_bouton
from dq4_pc.noyau import moteur as MO

try:
    import pyglet
    pyglet.options['shadow_window'] = False
    from dq4_pc.menus import hud_mobile as HM
    from dq4_pc.fenetre import jeu as FE
    from dq4_pc.menus import saisie_nom as SN
    ERREUR = None
except Exception as ex:                       # pas de pyglet (CI) ou fenetre non importable : seule la regle est testee
    pyglet = HM = FE = SN = None; ERREUR = ex


class Regle(unittest.TestCase):
    def test_a_et_action_jouent_le_bruit(self):
        for pad in (0x10, 0x800, 0x810, 0x10 | 0x4):
            self.assertTrue(bruit_bouton(pad), hex(pad))

    def test_les_autres_touches_sont_muettes(self):
        for pad in (0, 1, 2, 4, 8, 0x20, 0x80, 0x400, 0x20 | 0x4, 0x1000):
            self.assertFalse(bruit_bouton(pad), hex(pad))

    def test_la_valeur_du_bruit(self):
        self.assertEqual(SE_BOUTON, 300)


class JeuSonore:
    """Faux jeu : un journal des bruitages demandes et des messages envoyes aux menus."""
    pass


def faux_son():
    s = types.SimpleNamespace(se=[]); s.jouer_se = lambda n: s.se.append(n); return s


@unittest.skipIf(pyglet is None or FE is None, 'pyglet / fenetre non importables ici : %r' % (ERREUR,))
class Permis(unittest.TestCase):
    """`Boutons.permis` suit `Boutons.visibles` (le reglage « boutons » mis a part)."""

    def jeu(self, flags=0x28, partie=None, effet=None, pause=False, carte=False, boutons=True):
        J = types.SimpleNamespace(width=1280, height=720, reg={'boutons': boutons, 'croix': False, 'bouton_vitesse': False}, carte_ouverte=carte, pause=types.SimpleNamespace(ouvert=pause))
        J.moteur = types.SimpleNamespace(etat=types.SimpleNamespace(partie=partie if partie is not None else MO.PARTIE_VILLE, effet=effet), drapeaux=lambda: flags)
        J.hud = HM.Boutons(J); return J

    def test_terrain_libre(self):
        h = self.jeu(0x28).hud
        for n in HM.NOMS: self.assertTrue(h.permis(n), n)

    def test_la_carte_demande_le_bit_0x20(self):
        h = self.jeu(0x08).hud
        self.assertTrue(h.permis('menu')); self.assertTrue(h.permis('discussion')); self.assertFalse(h.permis('carte'))

    def test_interface_verrouillee_ou_evenement(self):
        for flags in (0x00, 0x01, 0x02, 0x04, 0x40, 0x10000, 0x20000, 0x28 | 0x40, 0x28 | 0x04):
            h = self.jeu(flags).hud
            for n in HM.NOMS: self.assertFalse(h.permis(n), (hex(flags), n))

    def test_pause_effet_combat_et_carte_ouverte(self):
        for kw in (dict(pause=True), dict(effet=object()), dict(partie=MO.PARTIE_COMBAT), dict(carte=True)):
            h = self.jeu(0x28, **kw).hud
            for n in HM.NOMS: self.assertFalse(h.permis(n), (list(kw), n))

    def test_independant_du_reglage_d_affichage(self):
        h = self.jeu(0x28, boutons=False).hud
        self.assertEqual(h.visibles(), ()); self.assertTrue(h.permis('menu'))

    def test_meme_ensemble_que_visibles(self):
        for flags in (0x00, 0x08, 0x28, 0x48, 0x09, 0x30008, 0x8 | 0x20):
            for kw in ({}, dict(pause=True), dict(effet=object()), dict(partie=MO.PARTIE_COMBAT), dict(carte=True)):
                h = self.jeu(flags, **kw).hud
                if kw.get('partie') == MO.PARTIE_COMBAT: continue                    # (en combat : seul le bouton de vitesse, propre au portage)
                self.assertEqual({n for n in h.visibles() if n in HM.NOMS}, {n for n in HM.NOMS if h.permis(n)}, (hex(flags), list(kw)))


def deux_menus(pads, port=3):
    """Un faux menu : liste de (numero, manette, x0, z0, x1, z1) en unites d'interface, rendue sous forme de `fe` (boutons) et de zones en pixels."""
    bs = [(b, pad, x0, z0, x1, z1, 0.0, 100 + i) for i, (b, pad, x0, z0, x1, z1) in enumerate(pads)]
    fe = types.SimpleNamespace(typ=99, boutons=lambda ident=False: [t if ident else t[:7] for t in bs], N={})
    return fe, bs


@unittest.skipIf(pyglet is None or FE is None, 'pyglet / fenetre non importables ici : %r' % (ERREUR,))
class SurLeJeu(unittest.TestCase):
    """Vraies methodes de `Jeu` (_saisie_menu, _saisie_pas, on_mouse_press, _entrees, _bruit_hud) sur un faux jeu."""

    def jeu(self, boutons, flags=0x28, port=3, grille=False):
        fe, zones = deux_menus(boutons)
        j = types.SimpleNamespace()
        j.son = faux_son(); j.envoyes = []
        j.moteur = types.SimpleNamespace(
            ui=types.SimpleNamespace(f={port: {'grille': grille, 'ordre': 1, 'cur': -1, 'type': 99, 'entree': True, 'cases': [], 'vis': True}}),
            envoyer_menu=lambda p, *a: j.envoyes.append((p,) + a), menu_actif=lambda: port, menus_saisie=lambda: [port], msg_visible=False, drapeaux=lambda: flags, boutiques=lambda: (0, 0),
            etat=types.SimpleNamespace(partie=MO.PARTIE_VILLE, effet=None))
        j.ui_g = types.SimpleNamespace(f={port: fe}); j.cur_local = {}; j.cur_pas = {}; j.survol_nd = None; j.menu_relacher = None
        j.width, j.height = 1280, 720; j.reg = {'boutons': False, 'croix': False, 'bouton_vitesse': False}; j.pause = types.SimpleNamespace(ouvert=False); j.carte_ouverte = False
        j.hud = HM.Boutons(j); j.titre = None; j.licence = None; j.sauv = None; j.saisie_nom = types.SimpleNamespace(actif=False); j.hud_decl = 0
        j.clic_a = j.clic_b = False; j.appui = None; j.appui_nd = None; j._pret = True; j.ui_rendu = True; j.dernier_peripherique = None; j.souris = None; j.n = 0
        j.garde_souris = types.SimpleNamespace(clic=lambda: None); j.molette = types.SimpleNamespace(en_cours=False, annuler=lambda: None)
        j._zones = lambda p: zones if p == port else []; j._carte_ports = lambda: {}; j._terrain_libre = lambda: False
        j._port_pour_manette = lambda p, pad: p; j._port_depart = lambda p: False; j._port_clavier = lambda p: p
        j._saisie_nom_en_cours = lambda: False; j._cachee = lambda t: False
        j._bits_camera = lambda: 0; j._camera_oublier = lambda: None            # (la camera du jeu n'a rien a voir avec les bruitages : test_entrees.py et test_camera_moteur.py)
        for nom in ('_saisie_menu', '_saisie_pas', '_pas_colonnes', '_pas_actif', '_voisin', '_fleche_page', '_bouton_sous', 'on_mouse_press', '_bruit_hud', '_entrees', '_survol_pas', '_quitter_seul'):
            f = inspect.getattr_static(FE.Jeu, nom, None)
            if isinstance(f, staticmethod): setattr(j, nom, f.__func__)
            elif f is not None: setattr(j, nom, types.MethodType(f, j))
        return j

    # ---- doigt / souris : bouton sous le pointeur
    def clic(self, pad):
        j = self.jeu([(0, pad, 0.0, 0.0, 10.0, 10.0)]); j._zones = lambda p: [(0, pad, 100, 100, 200, 200, 0.0, 7)]
        j.on_mouse_press(150, 150, pyglet.window.mouse.LEFT, 0); return j

    def test_clic_sur_un_bouton_a_ou_action_joue_le_bruit(self):
        for pad in (0x10, 0x800):
            self.assertEqual(self.clic(pad).son.se, [300], hex(pad))

    def test_clic_sur_les_autres_boutons_est_muet(self):
        for pad in (0x20, 0x400, 1, 2, 4, 8, 0x80):
            j = self.clic(pad); self.assertEqual(j.son.se, [], hex(pad)); self.assertIsNotNone(j.appui, hex(pad))             # (le bouton est bien presse, seul le bruit manque)

    def test_clic_droit_et_clic_dans_le_vide(self):
        j = self.clic(0x10); j.son.se.clear(); j.on_mouse_press(900, 900, pyglet.window.mouse.LEFT, 0); self.assertEqual(j.son.se, [])

    def test_bouton_retour_de_la_carte_muet(self):
        j = self.jeu([(-1, 0x400, 0, 0, 1, 1), (-1, 2, 5, 5, 6, 6)]); j._carte_ports = lambda: {22: 3}
        j._zones = lambda p: [(-1, 0x400, 100, 100, 200, 200, 0.0, 7), (-1, 2, 300, 300, 400, 400, 0.0, 8)] if p == 3 else []
        j.on_mouse_press(150, 150, pyglet.window.mouse.LEFT, 0); j.on_mouse_press(350, 350, pyglet.window.mouse.LEFT, 0)
        self.assertEqual(j.son.se, []); self.assertEqual(j.appui, (3, -1, 2))

    # ---- clavier : menu a curseur local (liste d'une colonne de boutons A)
    LISTE = [(0, 0x10, 0, 100, 50, 120), (1, 0x10, 0, 70, 50, 90), (2, 0x10, 0, 40, 50, 60)]

    def test_clavier_a_joue_le_bruit(self):
        j = self.jeu(self.LISTE); j._saisie_menu(3, MO.A)
        self.assertEqual(j.son.se, [300]); self.assertEqual(j.envoyes[-1][1:], (1, 0, 0x10))

    def test_clavier_b_est_muet(self):
        j = self.jeu(self.LISTE); j._saisie_menu(3, MO.B)
        self.assertEqual(j.son.se, []); self.assertEqual(j.envoyes[-1][1:], (1, -1, 0x20))                 # (le message d'annulation part quand meme)

    def test_clavier_deplacer_le_curseur_est_muet(self):
        j = self.jeu(self.LISTE)
        for bit in (MO.HAUT, MO.BAS): j._saisie_menu(3, bit)
        self.assertEqual(j.son.se, [])

    def test_clavier_fleches_de_page_muettes(self):
        j = self.jeu(self.LISTE + [(-1, 8, 0, 0, 10, 10), (-1, 4, 20, 0, 30, 10)])
        j._port_pour_manette = lambda p, pad: 9 if pad in (4, 8) else p                       # les fleches sont dans une autre fenetre
        j._saisie_menu(3, MO.DROITE); j._saisie_menu(3, MO.GAUCHE)
        self.assertEqual(j.son.se, []); self.assertEqual([e[:1] + e[-1:] for e in j.envoyes], [(9, 4), (9, 8)])

    # ---- clavier : saisie numerique (colonnes ▲ ▼, validation A)
    PAS = [(0, 2, 0, 50, 10, 60), (0, 1, 0, 0, 10, 10), (1, 2, 20, 50, 30, 60), (1, 1, 20, 0, 30, 10), (5, 0x10, 40, 20, 80, 40)]

    def test_saisie_numerique(self):
        j = self.jeu(self.PAS)
        j._saisie_menu(3, MO.GAUCHE); self.assertEqual(j.cur_pas[(3, 1)], 0)                                    # changement de colonne : muet
        j._saisie_menu(3, MO.DROITE); self.assertEqual(j.cur_pas[(3, 1)], 1)
        j._saisie_menu(3, MO.HAUT); j._saisie_menu(3, MO.BAS); self.assertEqual([e[-2:] for e in j.envoyes], [(1, 2), (1, 1)])            # ▲ ▼ : message au moteur
        self.assertEqual(j.son.se, [], 'colonne, ▲ et ▼ muets')
        j._saisie_menu(3, MO.A); self.assertEqual(j.son.se, [300], 'A (validation) joue le bruit'); self.assertEqual(j.envoyes[-1][-1], 0x10)
        j._saisie_menu(3, MO.B); self.assertEqual(j.son.se, [300], 'B muet'); self.assertEqual(j.envoyes[-1][-1], 0x20)

    # ---- clavier : touches du terrain
    def touches(self, **fr):
        j = self.jeu(self.LISTE, flags=fr.pop('flags', 0x28))
        j.moteur.menu_actif = lambda: None
        base = {a: False for a in ('menu', 'discussion', 'carte', 'L', 'R')}; base.update(fr)
        j._fronts = lambda: dict(base); j.rep = {}; j.pad_prec = 0; j.reg = dict(j.reg); j.hud_decl = fr.pop('hud_decl', 0)
        return j

    def entrees(self, j): return j._entrees(0)

    def test_terrain_entree_espace_et_m_jouent_le_bruit(self):
        for nom, bouton in (('menu', BTN_MENU), ('discussion', BTN_DISCUSSION), ('carte', BTN_CARTE)):
            j = self.touches(**{nom: True}); p, decl = self.entrees(j); self.assertEqual(decl, bouton, nom); self.assertEqual(j.son.se, [300], nom)

    def test_terrain_sans_touche_muet(self):
        j = self.touches(); self.entrees(j); self.assertEqual(j.son.se, [])

    def test_terrain_bouton_non_permis_muet(self):
        for flags in (0x00, 0x08 | 0x40):                                           # interdit : rien ne se passe, aucun bruit
            for nom in ('menu', 'discussion', 'carte'):
                j = self.touches(flags=flags, **{nom: True}); self.entrees(j); self.assertEqual(j.son.se, [], (hex(flags), nom))
        j = self.touches(flags=0x08, carte=True); self.entrees(j); self.assertEqual(j.son.se, [], 'la carte exige le bit 0x20')

    def test_terrain_touche_d_action_muette(self):
        j = self.touches(); j.clic_a = True; p, decl = self.entrees(j); self.assertEqual(j.son.se, [])           # (A / clic sur le terrain : parler, aucun bouton)

    def test_terrain_bouton_a_l_ecran_deja_sonore_pas_de_doublon(self):
        j = self.touches(menu=True); j.hud_decl = BTN_DISCUSSION; p, decl = self.entrees(j)                              # appui souris sur le bouton Discussion : le bruit a deja ete joue a l'appui
        self.assertEqual(decl, BTN_DISCUSSION); self.assertEqual(j.son.se, [])

    def test_carte_ouverte_au_clavier_muette(self):
        for ports in ({22: 3}, {25: 3, 26: 4}):
            j = self.touches(carte=True); j._carte_ports = lambda ports=ports: ports; j.carte_vue = 1; j.carte_bascule = False; j.carte_ouverte = False
            j.moteur.ui.f.update({q: {'grille': False, 'cases': [], 'vis': False, 'type': 25} for q in ports.values() if q not in j.moteur.ui.f})
            j.menu_relacher = None; self.entrees(j); self.assertEqual(j.son.se, [], ports)


class SaisieDuNom(unittest.TestCase):
    """Une lettre tapee au clavier joue le bruitage du bouton, comme le clic sur la lettre."""

    @unittest.skipIf(SN is None, 'saisie_nom non importable ici')
    def test_lettre_tapee(self):
        s = SN.SaisieNom.__new__(SN.SaisieNom); s.J = types.SimpleNamespace(son=faux_son()); s.texte = ''; s.max = 8; s.cur = 0; s.souris = 1
        s.texte_saisi('ab'); self.assertEqual(s.texte, 'ab'); self.assertEqual(s.J.son.se, [300, 300])
        s.texte_saisi('@@'); self.assertEqual(s.J.son.se, [300, 300], 'caractere hors grille : rien')
        s.texte = 'x' * 8; s.texte_saisi('z'); self.assertEqual(s.J.son.se, [300, 300], 'nom plein : rien')


if __name__ == '__main__':
    unittest.main(verbosity=1)
