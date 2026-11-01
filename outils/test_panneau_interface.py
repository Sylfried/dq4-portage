"""Test du panneau flottant « Interface » (menu Echap > Affichage > Interface) : glisser par la barre de titre, replier / deplier, double clic.

    python3 outils/test_panneau_interface.py

Rejoue la suite d'evenements d'une vraie souris, comme pyglet les envoie a la fenetre (on_mouse_press -> Pause.clic, on_mouse_drag -> Pause.glisser avec dx / dy, on_mouse_release -> Pause.relache ;
l'horloge est simulee, la boucle d'images appelle Pause.maj) :
  - appui puis glisser tout de suite (sans attendre l'appui long) : le panneau suit le pointeur et ne se replie pas ;
  - appui sans bouger (ou avec une secousse de quelques pixels) : replier / deplier ;
  - appui maintenu sans bouger (soulevement) puis glisser : il suit aussi ;
  - double clic : retour a la position d'origine ; double appui suivi d'un glisser : il se deplace.
"""
import os, sys, types, unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False          # pas de fenetre cachee : le test tourne sans serveur d'affichage
import reglages as RG

try:
    import pause as PA
except Exception as ex:          # pause.py a besoin de pyglet (sans affichage : l'import seul suffit)
    PA = None; ERREUR = ex

GAUCHE, DROIT = 1, 4             # pyglet.window.mouse.LEFT / RIGHT
CADRE = (600.0, 300.0, 1240.0, 700.0)         # panneau deplie : x0, y0, x1, y1 (fenetre 1280 x 720)
BARRE = (600.0, 636.0, 1240.0, 700.0)         # barre de titre (zone_plier)


class Souris:
    """Souris simulee : horloge et evenements pyglet vers un menu Pause d'un jeu factice."""
    def __init__(self):
        self.t = 1000.0
        jeu = types.SimpleNamespace(reg=RG.Reglages(None), hud=types.SimpleNamespace(pris=None, poser=lambda: None), width=1280, height=720,
                                    son=types.SimpleNamespace(ecoute=False, ecouter=lambda b: None, tick=lambda: None), touches={})
        self.P = PA.Pause(jeu); P = self.P
        P.ouvert = True; P.pile = ['racine', 'affichage', 'interface']; P.cadre_panneau = CADRE; P.zone_plier = BARRE
        self.x = self.y = None
        self.patch = mock.patch.object(PA.time, 'time', lambda: self.t); self.patch.start()

    def fin(self): self.patch.stop()

    def attendre(self, s):
        """Le temps passe (images de la boucle : Pause.maj a chaque image)."""
        for _ in range(max(1, int(s / 0.016))): self.t += 0.016; self.P.maj()

    def appui(self, x, y, bouton=GAUCHE): self.x, self.y = x, y; self.P.clic(x, y, bouton)

    def glisse(self, x, y):
        self.x, self.y = x, y
        self.P.glisser(x, y)                                           # (fenetre.on_mouse_drag : x, y, dx, dy, boutons, modifiers ; seuls x et y servent)
        self.t += 0.008; self.P.maj()

    def relache(self, bouton=GAUCHE): self.P.relache(self.x, self.y, bouton)

    def geste(self, depart, points, bouton=GAUCHE):
        self.appui(*depart, bouton=bouton)
        for p in points: self.glisse(*p)
        self.relache(bouton)


@unittest.skipIf(PA is None, 'pause.py non importable ici')
class Panneau(unittest.TestCase):
    def setUp(self): self.S = Souris(); self.P = self.S.P
    def tearDown(self): self.S.fin()

    def test_glisser_tout_de_suite(self):
        """Appui et mouvement immediat (moins de DELAI_APPUI_LONG) : le panneau suit le pointeur, sans se replier."""
        S, P = self.S, self.P
        S.geste((900, 670), [(902, 669), (906, 667), (915, 660), (870, 620), (820, 560), (800, 500)])
        self.assertEqual(P.pan_pos, (800 - (900 - CADRE[2]), 500 - (670 - CADRE[3])))          # coin haut droit = pointeur - decalage de l'appui
        self.assertFalse(P.plie); self.assertIsNone(P.pan_appui)
        self.assertEqual(P.pan_clic_t, 0.0)                                                    # un glisser n'est pas un clic (pas de double clic ensuite)

    def test_glisser_pendant_l_appui_long(self):
        S, P = self.S, self.P
        S.appui(900, 670); S.attendre(0.5); self.assertTrue(P.pan_appui['long'])               # soulevement apres 0,35 s sans bouger
        S.glisse(700, 600); S.glisse(500, 300); S.relache()
        self.assertEqual(P.pan_pos, (500 - (900 - CADRE[2]), 300 - (670 - CADRE[3]))); self.assertFalse(P.plie)

    def test_appui_long_sans_bouger_ne_replie_pas(self):
        S, P = self.S, self.P
        S.appui(900, 670); S.attendre(0.6); S.relache()
        self.assertFalse(P.plie); self.assertIsNone(P.pan_pos)

    def test_appui_court_replie(self):
        S, P = self.S, self.P
        S.appui(900, 670); S.attendre(0.1); S.relache(); self.assertTrue(P.plie)
        S.attendre(1.0); S.appui(900, 670); S.attendre(0.1); S.relache(); self.assertFalse(P.plie)       # (assez tard : pas un double clic)
        self.assertIsNone(P.pan_pos)

    def test_secousse_de_la_souris(self):
        """Quelques pixels de tremblement pendant un clic (moins de TOLERANCE_APPUI) : c'est un clic, pas un glisser."""
        S, P = self.S, self.P
        S.geste((900, 670), [(903, 669), (905, 672), (902, 668)])
        self.assertTrue(P.plie); self.assertIsNone(P.pan_pos)

    def test_double_clic_position_d_origine(self):
        S, P = self.S, self.P
        P.pan_pos = (700.0, 500.0)
        S.appui(900, 670); S.attendre(0.08); S.relache(); self.assertTrue(P.plie)              # premier clic : replie
        S.attendre(0.1); S.appui(900, 670); S.attendre(0.08); S.relache()                         # deuxieme clic dans DELAI_DOUBLE_CLIC
        self.assertFalse(P.plie); self.assertIsNone(P.pan_pos)                                 # le pliage est annule, le panneau revient a sa place d'origine

    def test_double_appui_puis_glisser(self):
        """Un glisser juste apres un clic deplace le panneau (il ne revient pas a l'origine)."""
        S, P = self.S, self.P
        S.appui(900, 670); S.attendre(0.08); S.relache(); S.attendre(0.1)
        S.geste((900, 670), [(880, 650), (700, 500)])
        self.assertEqual(P.pan_pos, (700 - (900 - CADRE[2]), 500 - (670 - CADRE[3])))

    def test_glisser_puis_glisser(self):
        S, P = self.S, self.P
        S.geste((900, 670), [(850, 640), (800, 600)]); p1 = P.pan_pos
        S.attendre(0.1); S.geste((900, 670), [(940, 660)])                                      # nouvel appui juste apres : un glisser, pas un double clic
        self.assertNotEqual(P.pan_pos, p1); self.assertIsNotNone(P.pan_pos); self.assertFalse(P.plie)

    def test_hors_de_la_barre_de_titre(self):
        S, P = self.S, self.P
        S.appui(900, 500); self.assertIsNone(P.pan_appui)                                       # une ligne du panneau, pas la barre : pas de glisser du panneau
        S.relache(); S.appui(900, 670, bouton=DROIT); self.assertIsNone(P.pan_appui)            # clic droit : Annuler, pas de glisser

    def test_position_gardee_dans_l_ecran(self):
        P = self.P
        for pos in ((5000.0, 5000.0), (-300.0, -300.0)):
            P.pan_pos = pos; x0, y1 = P._pos_panneau(640.0, 400.0, 1280, 720, 0.8)
            self.assertTrue(0 <= x0 and x0 + 640 <= 1280 and 400 <= y1 <= 720, (pos, x0, y1))
        for W, H, pos in ((1920, 1080, (5000.0, 5000.0)), (2560, 1440, (-50.0, -50.0))):         # fenetre plus grande que 1280 x 720
            P.pan_pos = pos; x0, y1 = P._pos_panneau(640.0, 400.0, W, H, 1.2)
            self.assertTrue(0 <= x0 and x0 + 640 <= W and 400 <= y1 <= H, (W, pos, x0, y1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
