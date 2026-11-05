"""Test du panneau flottant « Interface » (menu Echap > Affichage > Interface) : glisser par la barre de titre, replier / deplier, double clic.

    python3 tools/test_interface_panel.py

Rejoue la suite d'evenements d'une vraie souris, comme pyglet les envoie a la fenetre (on_mouse_press -> Pause.clic, on_mouse_drag -> Pause.glisser avec dx / dy, on_mouse_release -> Pause.relache ;
l'horloge est simulee, la boucle d'images appelle Pause.maj) :
  - appui puis glisser tout de suite (sans attendre l'appui long) : le panneau suit le pointeur et ne se replie pas ;
  - appui sans bouger (ou avec une secousse de quelques pixels) : replier / deplier ;
  - appui maintenu sans bouger (soulevement) puis glisser : il suit aussi ;
  - double clic : retour a la position d'origine ; double appui suivi d'un glisser : il se deplace ;
  - detection du double clic alignee sur Windows (#145) : delai compte depuis le DEBUT du premier appui, rectangle SM_CXDOUBLECLK x SM_CYDOUBLECLK centre sur lui, et un simple clic replie des que le double clic est
    devenu impossible (delai ecoule, pointeur sorti du rectangle, autre appui) au lieu d'attendre betement.
"""
import os, sys, types, unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
pyglet.options['shadow_window'] = False          # pas de fenetre cachee : le test tourne sans serveur d'affichage
from dq4_pc.persistence import settings as RG

try:
    from dq4_pc.menus import pause as PA
except Exception as ex:          # pause.py a besoin de pyglet (sans affichage : l'import seul suffit)
    PA = None; ERROR = ex

LEFT, RIGHT_BUTTON = 1, 4             # pyglet.window.mouse.LEFT / RIGHT
BORDER = (600.0, 300.0, 1240.0, 700.0)         # panneau deplie : x0, y0, x1, y1 (fenetre 1280 x 720)
BARRE = (600.0, 636.0, 1240.0, 700.0)         # barre de titre (fold_zone)


class Mouse:
    """Souris simulee : horloge et evenements pyglet vers un menu Pause d'un jeu factice."""
    def __init__(self):
        self.t = 1000.0
        game = types.SimpleNamespace(reg=RG.Settings(None), hud=types.SimpleNamespace(taken=None, place=lambda: None), width=1280, height=720,
                                    sound=types.SimpleNamespace(listening=False, listen=lambda b: None, tick=lambda: None), key_list={})
        self.P = PA.Pause(game); P = self.P
        P.opened = True; P.stack = ['racine', 'affichage', 'interface']; P.panel_border = BORDER; P.fold_zone = BARRE
        self.x = self.y = None
        self.patch = mock.patch.object(PA.time, 'time', lambda: self.t); self.patch.start()

    def end(self): self.patch.stop()

    def wait(self, s):
        """Le temps passe (images de la boucle : Pause.maj a chaque image)."""
        for _ in range(max(1, int(s / 0.016))): self.t += 0.016; self.P.do_update()

    def press_state(self, x, y, button=LEFT): self.x, self.y = x, y; self.P.click(x, y, button)

    def dragging(self, x, y):
        self.x, self.y = x, y
        self.P.drag_to(x, y)                                           # (fenetre.on_mouse_drag : x, y, dx, dy, boutons, modifiers ; seuls x et y servent)
        self.t += 0.008; self.P.do_update()

    def release(self, button=LEFT): self.P.release(self.x, self.y, button)

    def gesture(self, initial, points, button=LEFT):
        self.press_state(*initial, button=button)
        for p in points: self.dragging(*p)
        self.release(button)


@unittest.skipIf(PA is None, 'pause.py non importable ici')
class Panel(unittest.TestCase):
    def setUp(self): self.S = Mouse(); self.P = self.S.P
    def tearDown(self): self.S.end()

    def test_slide_right_away(self):
        """Appui et mouvement immediat (moins de LONG_PRESS_DELAY) : le panneau suit le pointeur, sans se replier."""
        S, P = self.S, self.P
        S.gesture((900, 670), [(902, 669), (906, 667), (915, 660), (870, 620), (820, 560), (800, 500)])
        self.assertEqual(P.pan_pos, (800 - (900 - BORDER[2]), 500 - (670 - BORDER[3])))          # coin haut droit = pointeur - decalage de l'appui
        self.assertFalse(P.folded); self.assertIsNone(P.pan_pressed)
        self.assertEqual(P.pan_click_t, 0.0)                                                    # un glisser n'est pas un clic (pas de double clic ensuite)

    def test_slide_during_long_press(self):
        S, P = self.S, self.P
        S.press_state(900, 670); S.wait(0.5); self.assertTrue(P.pan_pressed['long'])               # soulevement apres 0,35 s sans bouger
        S.dragging(700, 600); S.dragging(500, 300); S.release()
        self.assertEqual(P.pan_pos, (500 - (900 - BORDER[2]), 300 - (670 - BORDER[3]))); self.assertFalse(P.folded)

    def test_long_press_without_moving_does_not_fold(self):
        S, P = self.S, self.P
        S.press_state(900, 670); S.wait(0.6); S.release()
        self.assertFalse(P.folded); self.assertIsNone(P.pan_pos)

    def test_short_press_folds(self):
        S, P = self.S, self.P
        S.press_state(900, 670); S.wait(0.1); S.release(); S.wait(0.6); self.assertTrue(P.folded)       # (le pliage attend la fin du delai du double clic : #145)
        S.wait(1.0); S.press_state(900, 670); S.wait(0.1); S.release(); S.wait(0.6); self.assertFalse(P.folded)       # (assez tard : pas un double clic)
        self.assertIsNone(P.pan_pos)

    def test_mouse_shake(self):
        """Quelques pixels de tremblement pendant un clic (moins de PRESS_TOLERANCE) : c'est un clic, pas un glisser."""
        S, P = self.S, self.P
        S.gesture((900, 670), [(903, 669), (905, 672), (902, 668)]); S.wait(0.6)
        self.assertTrue(P.folded); self.assertIsNone(P.pan_pos)

    def test_double_click_origin_position(self):
        S, P = self.S, self.P
        P.pan_pos = (700.0, 500.0)
        S.press_state(900, 670); S.wait(0.08); S.release(); self.assertFalse(P.folded)             # premier clic : rien ne bouge encore (on attend un eventuel second clic)
        S.wait(0.1); S.press_state(900, 670); S.wait(0.08); S.release()                         # deuxieme clic dans DOUBLE_CLICK_DELAY
        self.assertFalse(P.folded); self.assertIsNone(P.pan_pos)                                 # le panneau revient a sa place d'origine, sans avoir change d'etat
        S.wait(1.0); self.assertFalse(P.folded)                                              # et le pliage du premier clic n'a pas lieu apres coup

    def test_simple_click_single_change_after_delay(self):
        """#145 : un clic simple ne plie qu'une fois le delai du double clic ecoule, et une seule fois ; le delai court depuis le DEBUT de l'appui (comme Windows), pas depuis son relachement."""
        S, P = self.S, self.P
        t0 = S.t; savestates = []; instants = []
        S.press_state(900, 670); S.wait(0.05); S.release()
        for _ in range(60): S.wait(0.016); savestates.append(P.folded); instants.append(S.t - t0)
        self.assertFalse(savestates[0]); self.assertTrue(savestates[-1])                                 # replie, mais pas tout de suite
        self.assertEqual(sum(1 for a, b in zip(savestates, savestates[1:]) if a != b), 1)                # un seul changement d'etat
        when = instants[savestates.index(True)]
        self.assertGreaterEqual(when, PA.DOUBLE_CLICK_DELAY - 1e-6)                            # pas avant la fin du delai (compte depuis l'appui)
        self.assertLess(when, PA.DOUBLE_CLICK_DELAY + 0.02)                                    # et sans attendre davantage : pas de delai ajoute apres le relachement

    def test_delay_counted_from_start_of_first_press(self):
        """#145 (Windows) : second appui a 0,45 s du DEBUT du premier (donc 0,40 s apres son relachement) = double clic ; a 0,55 s du debut = deux clics simples, meme si 0,5 s ne separent pas le relachement du second."""
        S, P = self.S, self.P
        P.pan_pos = (700.0, 500.0)
        S.press_state(900, 670); S.wait(0.05); S.release(); S.wait(0.40)                      # 0,45 s apres le debut du premier appui
        self.assertFalse(P.folded)
        S.press_state(900, 670); S.wait(0.05); S.release()
        self.assertIsNone(P.pan_pos); S.wait(1.0); self.assertFalse(P.folded)                # double clic : retour a l'origine, aucun pliage
        S.wait(1.0)
        S.press_state(900, 670); S.wait(0.05); S.release(); S.wait(0.52)                       # 0,57 s apres le debut du premier : le premier clic est deja acquis
        self.assertTrue(P.folded)                                                                # (replie au bout de 0,5 s, sans attendre un delai de plus)
        S.press_state(900, 670); S.wait(0.05); S.release(); S.wait(0.6); self.assertFalse(P.folded)      # le second est un clic simple : il deplie

    def test_double_click_rectangle(self):
        """#145 (Windows) : le second appui doit tomber dans le rectangle SM_CXDOUBLECLK x SM_CYDOUBLECLK centre sur le premier ; sinon c'est un clic simple de plus."""
        S, P = self.S, self.P
        delay, w, h = PA.system_double_click()
        S.press_state(900, 670); S.wait(0.04); S.release(); S.wait(0.04)
        S.press_state(900 + w / 2.0 + 3, 670); S.wait(0.04); S.release()                         # trop loin : pas un double clic, le premier clic replie aussitot
        self.assertTrue(P.folded)
        S.wait(1.0); self.assertFalse(P.folded)                                              # et le second (simple) a deplie apres son propre delai
        P.pan_pos = (700.0, 500.0)
        S.press_state(900, 670); S.wait(0.04); S.release(); S.wait(0.04)
        S.press_state(900 + w / 2.0 - 1, 670 - h / 2.0 + 1); S.wait(0.04); S.release()           # dans le rectangle : double clic
        self.assertIsNone(P.pan_pos); S.wait(1.0); self.assertFalse(P.folded)

    def test_folding_does_not_wait_if_double_click_impossible(self):
        """#145 : pointeur sorti du rectangle apres le relachement (survol) = le simple clic est acquis, le panneau replie tout de suite, sans attendre la fin du delai."""
        S, P = self.S, self.P
        S.press_state(900, 670); S.wait(0.04); S.release(); self.assertFalse(P.folded)
        S.t += 0.03; P.hovered(900, 670); self.assertFalse(P.folded)                              # pointeur toujours sur place : on attend encore
        S.t += 0.03; P.hovered(900 + 40, 670); self.assertTrue(P.folded)                          # il s'est eloigne : plus de double clic possible, le clic simple agit a l'instant
        S.wait(1.0); self.assertTrue(P.folded)                                               # une seule fois

    def test_a_press_elsewhere_acquires_the_pending_click(self):
        """#145 : un autre appui (hors du rectangle) valide aussitot le clic simple qui attendait, au lieu de le laisser traine."""
        S, P = self.S, self.P
        S.press_state(900, 670); S.wait(0.04); S.release(); S.wait(0.04)
        S.press_state(900, 500); self.assertTrue(P.folded)                                              # (clic sur une ligne du panneau, loin de la barre)
        S.release(); S.wait(1.0); self.assertTrue(P.folded)

    def test_press_longer_than_delay_folds_on_release(self):
        """#145 : si l'appui a deja dure plus que le delai du double clic (delai systeme court), le clic simple est acquis des le relachement."""
        S, P = self.S, self.P
        with mock.patch.object(PA, 'system_double_click', lambda: (0.2, 4, 4)), mock.patch.object(PA, 'LONG_PRESS_DELAY', 5.0):
            S.press_state(900, 670); S.wait(0.3); S.release()
            self.assertTrue(P.folded); S.wait(1.0); self.assertTrue(P.folded)

    def test_double_click_never_changes_the_state(self):
        """#145 : un double clic sur un panneau replie ou deplie ne le replie ni ne le deplie, a aucun moment."""
        S, P = self.S, self.P
        for initial in (False, True):
            P.folded = initial; P.pan_pos = (700.0, 500.0); P.pan_click_t = 0.0; P.pan_fold_at = None; P.pan_click_pos = None
            S.wait(1.0)
            seen = set()
            S.press_state(900, 670); S.wait(0.05); S.release(); seen.add(P.folded)
            S.wait(0.1); seen.add(P.folded); S.press_state(900, 670); S.wait(0.05); S.release(); seen.add(P.folded)
            for _ in range(60): S.wait(0.016); seen.add(P.folded)
            self.assertEqual(seen, {initial}, 'depart replie=%s' % initial); self.assertIsNone(P.pan_pos)

    def test_third_click_after_a_double_click_is_a_single_click(self):
        S, P = self.S, self.P
        S.press_state(900, 670); S.wait(0.05); S.release(); S.wait(0.1); S.press_state(900, 670); S.wait(0.05); S.release(); S.wait(1.0)
        self.assertFalse(P.folded)
        S.press_state(900, 670); S.wait(0.05); S.release(); S.wait(0.6); self.assertTrue(P.folded)

    def test_click_then_drag_folds_then_moves(self):
        """Un clic suivi tout de suite d'un glisser : le clic plie d'abord (comme avant), puis le panneau suit le pointeur."""
        S, P = self.S, self.P
        S.press_state(900, 670); S.wait(0.05); S.release(); S.wait(0.1)
        S.gesture((900, 670), [(880, 650), (700, 500)])
        self.assertTrue(P.folded); self.assertIsNotNone(P.pan_pos); S.wait(1.0); self.assertTrue(P.folded)      # (un seul pliage)

    def test_double_press_then_slide(self):
        """Un glisser juste apres un clic deplace le panneau (il ne revient pas a l'origine)."""
        S, P = self.S, self.P
        S.press_state(900, 670); S.wait(0.08); S.release(); S.wait(0.1)
        S.gesture((900, 670), [(880, 650), (700, 500)])
        self.assertEqual(P.pan_pos, (700 - (900 - BORDER[2]), 500 - (670 - BORDER[3])))

    def test_slide_then_slide(self):
        S, P = self.S, self.P
        S.gesture((900, 670), [(850, 640), (800, 600)]); p1 = P.pan_pos
        S.wait(0.1); S.gesture((900, 670), [(940, 660)])                                      # nouvel appui juste apres : un glisser, pas un double clic
        self.assertNotEqual(P.pan_pos, p1); self.assertIsNotNone(P.pan_pos); self.assertFalse(P.folded)

    def test_outside_title_bar(self):
        S, P = self.S, self.P
        S.press_state(900, 500); self.assertIsNone(P.pan_pressed)                                       # une ligne du panneau, pas la barre : pas de glisser du panneau
        S.release(); S.press_state(900, 670, button=RIGHT_BUTTON); self.assertIsNone(P.pan_pressed)            # clic droit : Annuler, pas de glisser

    def test_position_kept_within_screen(self):
        P = self.P
        for pos in ((5000.0, 5000.0), (-300.0, -300.0)):
            P.pan_pos = pos; x0, y1 = P._panel_pos(640.0, 400.0, 1280, 720, 0.8)
            self.assertTrue(0 <= x0 and x0 + 640 <= 1280 and 400 <= y1 <= 720, (pos, x0, y1))
        for W, H, pos in ((1920, 1080, (5000.0, 5000.0)), (2560, 1440, (-50.0, -50.0))):         # fenetre plus grande que 1280 x 720
            P.pan_pos = pos; x0, y1 = P._panel_pos(640.0, 400.0, W, H, 1.2)
            self.assertTrue(0 <= x0 and x0 + 640 <= W and 400 <= y1 <= H, (W, pos, x0, y1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
