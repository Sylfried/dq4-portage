"""Test (#131) : bulles d'icone cliquables et rond central de la croix = touche d'action (comme sur mobile).

    python3 outils/test_bulles_et_croix.py

1. `bulles.py` (fonctions pures) : projection d'un coin du monde en pixels (origine en bas a gauche, comme les evenements de souris), refus derriere la camera, point dans un quadrilatere (bords compris, tous sens).
2. Moteur : le paquet 19 avec un emplacement >= 16 n'est plus ignore, c'est le clignotement de la croix (`pad_clignote`) ; les vraies bulles (emplacements 0 a 15) restent inchangees.
3. Croix (`hud_mobile.Boutons`) : un TOUCHER du rond central (appui puis relachement sans en sortir) est reconnu ; un glissement (meme bref, meme s'il revient au centre) et un appui hors du rond non ; les directions ne changent pas.
4. Fenetre (vraies methodes de `fenetre.Jeu` sur un faux jeu) : clic gauche sur une bulle = touche A (`clic_a`), ailleurs rien ; toucher du rond central = A ; seulement sur le terrain libre (ni menu, ni message).
"""
import math, os, sys, types, unittest

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False
import bulles as BU
import hud_mobile as HM
import moteur as MO

try:
    import fenetre as FE
except Exception as ex:          # fenetre.py a besoin de pyglet, numpy, unicorn... (l'import seul suffit, aucune fenetre n'est creee)
    FE = None; ERREUR_FE = ex


def matrice(cam, cible, fov, aspect, n=1.0, f=200.0, haut=(0, 1, 0)):
    """Meme forme que `fenetre.matrice` (reecrite ici)."""
    pos = np.array(cam, float); fw = np.array(cible, float) - pos; fw /= np.linalg.norm(fw)
    droite = np.cross(haut, fw); droite /= np.linalg.norm(droite); haut = np.cross(fw, droite)
    th = math.tan(math.radians(fov) / 2)
    M = np.zeros((4, 4))
    M[0, :3] = droite / (th * aspect); M[0, 3] = -pos @ droite / (th * aspect)
    M[1, :3] = haut / th; M[1, 3] = -pos @ haut / th
    k = (f + n) / (f - n)
    M[2, :3] = fw * k; M[2, 3] = -pos @ fw * k - 2 * f * n / (f - n)
    M[3, :3] = fw; M[3, 3] = -pos @ fw
    return M


W, H = 1280, 720
CAM, CIBLE = (0.0, 6.0, -8.0), (0.0, 1.0, 0.0)


class Projection(unittest.TestCase):
    M = matrice(CAM, CIBLE, 40.0, W / H)

    def test_la_cible_est_au_centre(self):
        (x, y), = BU.projeter(self.M, [CIBLE], W, H); self.assertAlmostEqual(x, W / 2, 3); self.assertAlmostEqual(y, H / 2, 3)

    def test_droite_et_haut(self):
        c = np.array(CIBLE, float)
        (x, y), = BU.projeter(self.M, [c + (1.0, 0.0, 0.0)], W, H); self.assertGreater(x, W / 2)                      # cette camera regarde vers +z : +x est a droite de l'ecran
        (x2, y2), = BU.projeter(self.M, [c + (-1.0, 0.0, 0.0)], W, H); self.assertLess(x2, W / 2)
        (_, yh), = BU.projeter(self.M, [c + (0.0, 1.0, 0.0)], W, H); self.assertGreater(yh, H / 2)                    # origine en bas : plus haut dans le monde = plus grand y
        (_, yb), = BU.projeter(self.M, [c + (0.0, -1.0, 0.0)], W, H); self.assertLess(yb, H / 2)

    def test_derriere_la_camera(self):
        self.assertIsNone(BU.projeter(self.M, [(0.0, 6.0, -20.0)], W, H))                                               # derriere la camera
        self.assertIsNone(BU.projeter(self.M, [CIBLE, (0.0, 6.0, -20.0)], W, H))                                        # un seul coin derriere suffit

    def test_pixels_comme_le_debogage_de_la_fenetre(self):
        """Meme formule que `Jeu._dbg_proj` (DQ_PROJ) : (v0 / w x 0,5 + 0,5) x largeur ; y mesure depuis le haut = 1 - (v1 / w x 0,5 + 0,5)."""
        P = np.array([0.4, 2.0, 3.0]); v = self.M @ np.array([*P, 1.0])
        ref = ((v[0] / v[3] * 0.5 + 0.5) * W, (1 - (1 - (v[1] / v[3] * 0.5 + 0.5))) * H)
        (x, y), = BU.projeter(self.M, [P], W, H); self.assertAlmostEqual(x, ref[0], 6); self.assertAlmostEqual(y, ref[1], 6)


class Quadrilatere(unittest.TestCase):
    CARRE = [(10.0, 10.0), (50.0, 10.0), (50.0, 50.0), (10.0, 50.0)]

    def test_dedans_et_dehors(self):
        for sens in (self.CARRE, self.CARRE[::-1]):                                                                    # (les deux sens de parcours)
            self.assertTrue(BU.dans_quadrilatere((30, 30), sens)); self.assertTrue(BU.dans_quadrilatere((10.5, 49.5), sens))
            self.assertFalse(BU.dans_quadrilatere((5, 30), sens)); self.assertFalse(BU.dans_quadrilatere((30, 55), sens)); self.assertFalse(BU.dans_quadrilatere((60, 60), sens))

    def test_bords_compris(self):
        self.assertTrue(BU.dans_quadrilatere((10, 10), self.CARRE)); self.assertTrue(BU.dans_quadrilatere((50, 30), self.CARRE))

    def test_quadrilatere_incline(self):
        losange = [(30.0, 0.0), (60.0, 30.0), (30.0, 60.0), (0.0, 30.0)]
        self.assertTrue(BU.dans_quadrilatere((30, 30), losange)); self.assertFalse(BU.dans_quadrilatere((5, 5), losange)); self.assertFalse(BU.dans_quadrilatere((55, 55), losange))


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
        import moteur as M
        for (dx, dy), bits in (((0.5, 0.0), M.DROITE), ((-0.5, 0.0), M.GAUCHE), ((0.0, 0.5), M.HAUT), ((0.0, -0.5), M.BAS), ((0.5, 0.5), M.HAUT | M.DROITE)):
            self.b.croix_lacher(); self.appui(dx, dy); self.assertEqual(self.b.croix_bits(), bits, (dx, dy))
        self.b.croix_lacher(); self.appui(); self.assertEqual(self.b.croix_bits(), 0)                                      # (le rond central seul n'envoie aucune direction)

    def test_relacher_sans_appui(self):
        self.assertFalse(self.b.croix_relacher())

    def test_croix_masquee(self):
        self.appui(); self.J.reg['croix'] = False; self.assertEqual(self.b.croix_bits(), 0); self.assertFalse(self.b.croix_on); self.assertFalse(self.b.croix_glisse)


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class DansLaFenetre(unittest.TestCase):
    """Les vraies methodes de `Jeu` (clic sur une bulle, relachement de la croix) sur un faux jeu."""
    M = matrice(CAM, CIBLE, 40.0, W / H)
    QUAD = np.array([(-0.5, 1.0, 0.0), (0.5, 1.0, 0.0), (0.5, 2.0, 0.0), (-0.5, 2.0, 0.0)], float)          # bulle de 1 x 1 au-dessus de la cible

    def jeu(self, **kw):
        j = types.SimpleNamespace(**kw) if kw else types.SimpleNamespace()
        J = faux_jeu(); j.width, j.height, j.reg, j.moteur = W, H, J.reg, J.moteur
        j.moteur.menu_actif = lambda: None; j.moteur.msg_visible = False; j.moteur.etat.partie = MO.PARTIE_VILLE
        j.pause = J.pause; j.titre = None; j.licence = None; j.sauv = None; j.carte_ouverte = False; j._saisie_nom_en_cours = lambda: False; j._pret = True; j.ui_rendu = None
        j.hud = HM.Boutons(j); j.son = types.SimpleNamespace(jouer_se=lambda *a: None); j.garde_souris = types.SimpleNamespace(clic=lambda: None, clavier=lambda s: None)
        j.dernier_peripherique = None; j.souris = None; j.clic_a = j.clic_b = False; j._M_ville = self.M; j.icone_quads = {2: self.QUAD}; j.appui = None; j.molette = types.SimpleNamespace(annuler=lambda: None, en_cours=False)
        for nom in ('_terrain_libre', '_bulle_sous', 'on_mouse_press', 'on_mouse_release'): setattr(j, nom, types.MethodType(getattr(FE.Jeu, nom), j))
        j._carte_ports = lambda: {}; j.effet_ref = None
        return j

    def centre(self): (x, y), = BU.projeter(self.M, [self.QUAD.mean(axis=0)], W, H); return x, y

    def test_bulle_sous_le_pointeur(self):
        j = self.jeu(); x, y = self.centre()
        self.assertEqual(j._bulle_sous(x, y), 2); self.assertEqual(j._bulle_sous(x + 3, y - 3), 2)
        self.assertIsNone(j._bulle_sous(5, 5)); self.assertIsNone(j._bulle_sous(x + 400, y))

    def test_slot_zero_compte(self):
        j = self.jeu(); j.icone_quads = {0: self.QUAD}; x, y = self.centre(); self.assertEqual(j._bulle_sous(x, y), 0)           # (l'emplacement 0 est une vraie bulle, pas « rien »)
        j.on_mouse_press(int(x), int(y), pyglet.window.mouse.LEFT, 0); self.assertTrue(j.clic_a)

    def test_clic_sur_la_bulle_donne_la_touche_d_action(self):
        j = self.jeu(); x, y = self.centre(); j.on_mouse_press(int(x), int(y), pyglet.window.mouse.LEFT, 0); self.assertTrue(j.clic_a); self.assertFalse(j.clic_b)

    def test_clic_ailleurs_ne_fait_rien(self):
        j = self.jeu(); j.on_mouse_press(5, 5, pyglet.window.mouse.LEFT, 0); self.assertFalse(j.clic_a)

    def test_clic_droit_sur_la_bulle_reste_annuler(self):
        j = self.jeu(); x, y = self.centre(); j.on_mouse_press(int(x), int(y), pyglet.window.mouse.RIGHT, 0); self.assertTrue(j.clic_b); self.assertFalse(j.clic_a)

    def test_pas_de_clic_de_bulle_dans_un_menu_ou_un_message(self):
        x, y = self.centre()
        j = self.jeu(); j.moteur.msg_visible = True; self.assertIsNone(j._bulle_sous(x, y))                                       # message (le toucher du message est une autre commande)
        j = self.jeu(); j.moteur.menu_actif = lambda: object(); self.assertIsNone(j._bulle_sous(x, y))
        j = self.jeu(); j.pause.ouvert = True; self.assertIsNone(j._bulle_sous(x, y))
        j = self.jeu(); j.moteur.etat.partie = MO.PARTIE_COMBAT; self.assertIsNone(j._bulle_sous(x, y))

    def test_aucune_bulle(self):
        j = self.jeu(); j.icone_quads = {}; x, y = self.centre(); self.assertIsNone(j._bulle_sous(x, y)); j._M_ville = None; j.icone_quads = {2: self.QUAD}; self.assertIsNone(j._bulle_sous(x, y))

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
