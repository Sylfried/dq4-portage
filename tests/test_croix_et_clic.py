"""Test (#131) : un clic gauche sur le terrain libre = touche d'action ; rond central de la croix = touche d'action qui s'anime quand une action est possible (comme sur mobile).

    python3 outils/test_croix_et_clic.py

1. Moteur : le paquet 19 avec un emplacement >= 16 n'est pas ignore, c'est le clignotement de la croix (`pad_clignote`) ; les vraies bulles (emplacements 0 a 15) restent inchangees.
2. Croix (`hud_mobile.Boutons`) : un TOUCHER du rond central (appui puis relachement sans en sortir) est reconnu ; un glissement (meme bref, meme s'il revient au centre) et un appui hors du rond non ; les directions ne changent pas.
3. Animation : `Boutons.action_possible` = le jeu fait clignoter la croix OU, sur le terrain libre, une bulle d'icone est affichee.
4. Fenetre (vraies methodes de `fenetre.Jeu` sur un faux jeu) : clic gauche n'importe ou sur le terrain libre = touche A (`clic_a`) ; clic droit = B ; ni dans un menu, ni dans un message, ni en combat ; toucher du rond central = A.
"""
import math, os, sys, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..'))
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.noyau import moteur as MO

try:
    from dq4_pc.fenetre import jeu as FE
except Exception as ex:          # fenetre.py a besoin de pyglet, numpy, unicorn... (l'import seul suffit, aucune fenetre n'est creee)
    FE = None; ERREUR_FE = ex


W, H = 1280, 720


class PaquetsDuMoteur(unittest.TestCase):
    def appliquer(self, e, *paquets): e.appliquer(list(paquets), lambda: 'carte')

    def test_clignotement_de_la_croix(self):
        e = MO.Etat(); self.assertFalse(e.pad_clignote)
        self.appliquer(e, (19, [16, 0], [])); self.assertTrue(e.pad_clignote); self.assertEqual(e.icones, {})                   # ce n'est pas une bulle
        self.appliquer(e, (19, [16, -1], [])); self.assertFalse(e.pad_clignote)
        self.appliquer(e, (19, [20, 3], [])); self.assertTrue(e.pad_clignote)                                                  # (tout emplacement >= 16)

    def test_les_bulles_sont_inchangees(self):
        e = MO.Etat(); self.appliquer(e, (19, [3, 5], []), (20, [3], [1.0, 2.0, 3.0, 0.5]))
        self.assertEqual(e.icones[3]['id'], 5); self.assertEqual(e.icones[3]['pos'], (1.0, 2.0, 3.0)); self.assertEqual(e.icones[3]['alpha'], 0.5); self.assertFalse(e.pad_clignote)
        self.appliquer(e, (19, [3, -1], [])); self.assertEqual(e.icones, {})
        self.appliquer(e, (19, [15, 7], [])); self.assertIn(15, e.icones)                                                       # (15 est encore une bulle, 16 le clignotement)


def faux_jeu(W=1280, H=720, croix=True):
    etat = types.SimpleNamespace(partie=MO.PARTIE_VILLE, effet=None, pad_clignote=False)
    J = types.SimpleNamespace(width=W, height=H, reg={'boutons': True, 'croix': croix, 'boutons_taille': 1.0, 'croix_taille': 1.0, 'boutons_pos': {}, 'boutons_aimant': False, 'bouton_vitesse': True,
                                                         'bouton_vitesse_taille': 1.0, 'bouton_vitesse_pos': []},
                              pause=types.SimpleNamespace(ouvert=False), carte_ouverte=False, args=types.SimpleNamespace(cache='/inexistant'))
    J.moteur = types.SimpleNamespace(etat=etat, drapeaux=lambda: 0x28, taille_croix=lambda: 1)
    return J


class Croix(unittest.TestCase):
    def setUp(self):
        self.J = faux_jeu(); self.b = HM.Boutons(self.J); rx, ry, c, _ = self.b.rect(HM.CROIX); self.cx, self.cy, self.r = rx + c / 2, ry + c / 2, c / 2
        self.vis = (HM.CROIX,)

    def appui(self, dx=0.0, dy=0.0): return self.b.appuyer(self.cx + dx * self.r, self.cy + dy * self.r, self.vis)

    def test_toucher_du_rond_central(self):
        self.assertEqual(self.appui(), HM.CROIX); self.assertTrue(self.b.croix_on); self.assertFalse(self.b.croix_glisse); self.assertIsNone(self.b.croix_secteur())
        self.assertTrue(self.b.croix_relacher()); self.assertFalse(self.b.croix_on)                                       # appui puis relachement sans glisser = toucher

    def test_petits_mouvements_dans_la_zone_morte_restent_un_toucher(self):
        self.appui(); self.b.croix_glisser(self.cx + 0.05 * self.r, self.cy - 0.06 * self.r); self.assertFalse(self.b.croix_glisse); self.assertTrue(self.b.croix_relacher())

    def test_un_glissement_n_est_pas_un_toucher(self):
        self.appui(); self.b.croix_glisser(self.cx + 0.5 * self.r, self.cy); self.assertTrue(self.b.croix_glisse); self.assertEqual(self.b.croix_secteur(), 2)         # direction : droite
        self.assertFalse(self.b.croix_relacher())

    def test_un_retour_au_centre_apres_un_glissement_n_est_pas_un_toucher(self):
        self.appui(); self.b.croix_glisser(self.cx + 0.5 * self.r, self.cy); self.b.croix_glisser(self.cx, self.cy)
        self.assertIsNone(self.b.croix_secteur()); self.assertFalse(self.b.croix_relacher())

    def test_appui_hors_du_rond_central_est_une_direction(self):
        self.appui(0.0, 0.6); self.assertTrue(self.b.croix_glisse); self.assertEqual(self.b.croix_secteur(), 0); self.assertFalse(self.b.croix_relacher())                # haut

    def test_directions_inchangees(self):
        from dq4_pc.noyau import moteur as M
        for (dx, dy), bits in (((0.5, 0.0), M.DROITE), ((-0.5, 0.0), M.GAUCHE), ((0.0, 0.5), M.HAUT), ((0.0, -0.5), M.BAS), ((0.5, 0.5), M.HAUT | M.DROITE)):
            self.b.croix_lacher(); self.appui(dx, dy); self.assertEqual(self.b.croix_bits(), bits, (dx, dy))
        self.b.croix_lacher(); self.appui(); self.assertEqual(self.b.croix_bits(), 0)                                      # (le rond central seul n'envoie aucune direction)

    def test_relacher_sans_appui(self):
        self.assertFalse(self.b.croix_relacher())

    def test_croix_masquee(self):
        self.appui(); self.J.reg['croix'] = False; self.assertEqual(self.b.croix_bits(), 0); self.assertFalse(self.b.croix_on); self.assertFalse(self.b.croix_glisse)


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')


class Animation(unittest.TestCase):
    """`Boutons.action_possible` : la croix s'anime quand une action est realisable."""

    def hud(self, icones=None, libre=True, clignote=False):
        J = faux_jeu(); J.moteur.etat.icones = icones or {}; J.moteur.etat.pad_clignote = clignote; J._terrain_libre = lambda: libre
        return HM.Boutons(J)

    def test_rien_n_est_possible(self): self.assertFalse(self.hud().action_possible())

    def test_une_bulle_affichee(self):
        self.assertTrue(self.hud({0: {'id': 1, 'pos': (1.0, 2.0, 3.0), 'alpha': 1.0}}).action_possible())             # (emplacement 0 compris)
        self.assertTrue(self.hud({7: {'id': 1, 'pos': (1.0, 2.0, 3.0), 'alpha': 0.5}}).action_possible())

    def test_bulle_pas_encore_posee_ou_transparente(self):
        self.assertFalse(self.hud({2: {'id': 1, 'pos': None, 'alpha': 1.0}}).action_possible()); self.assertFalse(self.hud({2: {'id': 1, 'pos': (0, 0, 0), 'alpha': 0.0}}).action_possible())

    def test_pas_d_animation_hors_du_terrain_libre(self):
        self.assertFalse(self.hud({0: {'id': 1, 'pos': (1.0, 2.0, 3.0), 'alpha': 1.0}}, libre=False).action_possible())                # menu, message, combat...

    def test_le_clignotement_du_jeu_compte(self):
        self.assertTrue(self.hud(clignote=True).action_possible()); self.assertTrue(self.hud(clignote=True, libre=False).action_possible())

    def test_croix_dessinee_sans_erreur_sans_fenetre(self):
        self.assertFalse(self.hud().action_possible())          # (le dessin lui-meme demande un contexte GL : verifie en vrai, voir les notes de l'avance)


class DansLaFenetre(unittest.TestCase):
    """Les vraies methodes de `Jeu` (clic sur le terrain, relachement de la croix) sur un faux jeu."""

    def jeu(self, **kw):
        j = types.SimpleNamespace(**kw) if kw else types.SimpleNamespace()
        J = faux_jeu(); j.width, j.height, j.reg, j.moteur = W, H, J.reg, J.moteur
        j.moteur.menu_actif = lambda: None; j.moteur.msg_visible = False; j.moteur.etat.partie = MO.PARTIE_VILLE
        j.pause = J.pause; j.titre = None; j.licence = None; j.sauv = None; j.carte_ouverte = False; j._saisie_nom_en_cours = lambda: False; j._pret = True; j.ui_rendu = None
        j.hud = HM.Boutons(j); j.son = types.SimpleNamespace(jouer_se=lambda *a: None); j.garde_souris = types.SimpleNamespace(clic=lambda: None, clavier=lambda s: None)
        j.dernier_peripherique = None; j.souris = None; j.clic_a = j.clic_b = False; j.appui = None; j.molette = types.SimpleNamespace(annuler=lambda: None, en_cours=False)
        for nom in ('_terrain_libre', 'on_mouse_press', 'on_mouse_release'): setattr(j, nom, types.MethodType(getattr(FE.Jeu, nom), j))
        j._carte_ports = lambda: {}; j.effet_ref = None
        return j

    def test_clic_gauche_n_importe_ou_donne_la_touche_d_action(self):
        for x, y in ((5, 5), (640, 360), (1270, 715), (300, 600)):
            j = self.jeu(); j.on_mouse_press(x, y, pyglet.window.mouse.LEFT, 0); self.assertTrue(j.clic_a, (x, y)); self.assertFalse(j.clic_b)

    def test_clic_droit_reste_annuler(self):
        j = self.jeu(); j.on_mouse_press(640, 360, pyglet.window.mouse.RIGHT, 0); self.assertTrue(j.clic_b); self.assertFalse(j.clic_a)

    def test_pas_de_clic_d_action_hors_du_terrain_libre(self):
        j = self.jeu(); j.pause.ouvert = True; j.pause.clic = lambda *a: None; j.on_mouse_press(640, 360, pyglet.window.mouse.LEFT, 0); self.assertFalse(j.clic_a)           # menu d'Echap : son propre clic
        j = self.jeu(); j.moteur.etat.partie = MO.PARTIE_COMBAT; j.hud.visibles = lambda: (); j.on_mouse_press(640, 360, pyglet.window.mouse.LEFT, 0); self.assertFalse(j.clic_a)
        j = self.jeu(); j.moteur.menu_actif = lambda: object(); j.on_mouse_press(640, 360, pyglet.window.mouse.LEFT, 0); self.assertFalse(j.clic_a)                         # menu du jeu : ses boutons
        j = self.jeu(); j.carte_ouverte = True; j.on_mouse_press(640, 360, pyglet.window.mouse.LEFT, 0); self.assertFalse(j.clic_a)

    def test_message_visible_une_page_suivante(self):
        j = self.jeu(); j.moteur.msg_visible = True; j.moteur.menus_saisie = lambda: []; j.ui_rendu = object(); j.on_mouse_press(640, 360, pyglet.window.mouse.LEFT, 0); self.assertTrue(j.clic_a)                                        # (inchange : toucher le message)

    def test_toucher_du_rond_central_donne_la_touche_d_action(self):
        j = self.jeu(); rx, ry, c, _ = j.hud.rect(HM.CROIX); cx, cy = rx + c / 2, ry + c / 2
        j.on_mouse_press(int(cx), int(cy), pyglet.window.mouse.LEFT, 0); self.assertTrue(j.hud.croix_on); self.assertFalse(j.clic_a)               # l'action vient au relachement
        j.on_mouse_release(int(cx), int(cy), pyglet.window.mouse.LEFT, 0); self.assertTrue(j.clic_a); self.assertFalse(j.hud.croix_on)

    def test_glissement_sur_la_croix_pas_d_action(self):
        j = self.jeu(); rx, ry, c, _ = j.hud.rect(HM.CROIX); cx, cy = rx + c / 2, ry + c / 2
        j.on_mouse_press(int(cx), int(cy), pyglet.window.mouse.LEFT, 0); j.hud.croix_glisser(cx + c * 0.3, cy)
        j.on_mouse_release(int(cx + c * 0.3), int(cy), pyglet.window.mouse.LEFT, 0); self.assertFalse(j.clic_a)

    def test_toucher_du_rond_central_dans_un_menu_ne_fait_rien(self):
        j = self.jeu(); rx, ry, c, _ = j.hud.rect(HM.CROIX); cx, cy = rx + c / 2, ry + c / 2
        j.on_mouse_press(int(cx), int(cy), pyglet.window.mouse.LEFT, 0); j.moteur.msg_visible = True
        j.on_mouse_release(int(cx), int(cy), pyglet.window.mouse.LEFT, 0); self.assertFalse(j.clic_a)                         # (un message apparu entre-temps : pas d'action fantome)


if __name__ == '__main__':
    unittest.main(verbosity=1)
