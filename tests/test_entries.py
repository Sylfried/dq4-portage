"""Test des entrees souris / clavier : logique pure (inputs.py) et branchement dans la fenetre (fenetre.Game), sans ouvrir de fenetre.

    python3 tests/test_entries.py

1. La souris apres le clavier (« passer du clavier a la souris rend la souris inutilisable pendant 1 s ») : le survol reprend la main au premier vrai mouvement (ecart CUMULE depuis la derniere touche, petite
   tolerance de bruit), un clic agit toujours, aussitot. L'ancien test (ecart d'un evenement au suivant) est rejoue pour montrer qu'une souris qui envoie des mouvements de 1 a 2 pixels ne reprenait jamais la main.
2. Le clic molette (D-233, D-234) : clic = la camera revient au nord (par le jeu), glisser a gauche / a droite = rotation demandee (pas de saut au debut, le deplacement vertical ne tourne rien), un clic suivi d'un deplacement
   n'est pas un clic ; sens du glissement inversable (reglage `camera_inverser_gd`), fleches du clavier non. Le zoom, l'inclinaison et leurs gestes (molette, Ctrl) ont ete retires en #264 et ne reviennent pas.
3. Le bloc d'infos de F1 : en haut a droite par defaut.
4. Branchement dans Jeu (D-234) : la camera est celle du JEU. Fleches gauche / droite = boutons de camera du jeu (bits 4 et 5 des touches tenues), les deux ensemble = retour au nord (une seule fois), vitesse de camera = crans de plus
   par pas, l'accelerateur n'y change rien ; la visionneuse ne tourne NI la camera NI les directions du heros a cote du jeu (le jeu s'en charge, comme sur mobile, y compris dans ses scenes) ; le clic molette n'agit que sur le terrain
   libre d'une ville, ne fait rien d'autre, et la molette ne fait plus rien sur le terrain. Le test avec le vrai moteur (rotation, marche relative a la camera, retour au nord) est tests/test_engine_camera.py.
"""
import math, os, sys, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import pyglet
pyglet.options['shadow_window'] = False          # pas de fenetre cachee : le test tourne sans serveur d'affichage
from dq4_pc.window import inputs as EN

try:
    from dq4_pc.window import game as WND
except Exception as ex:          # window.py a besoin de pyglet, numpy, unicorn... (l'import seul suffit, aucune fenetre n'est creee)
    WND = None; ERROR_WND = ex


class MouseAfterKeyboard(unittest.TestCase):
    def test_without_reference_the_mouse_is_in_control(self):
        self.assertTrue(EN.mouse_active(None, (10, 10)))
        self.assertTrue(EN.mouse_active((10, 10), None))

    def test_tolerance(self):
        t = EN.MOUSE_TOLERANCE
        self.assertFalse(EN.mouse_active((100, 100), (100, 100)))                         # evenement sans deplacement (envoye par Windows quand le dessin change sous un pointeur au repos)
        self.assertFalse(EN.mouse_active((100, 100), (101, 102)))                         # tremblement du capteur
        self.assertTrue(EN.mouse_active((100, 100), (100 + t, 100)))                      # vrai mouvement
        self.assertTrue(EN.mouse_active((100, 100), (100 - t, 100)))
        self.assertTrue(EN.mouse_active((100, 100), (100, 100 + t)))
        self.assertFalse(EN.mouse_active((100, 100), (100 + t - 0.5, 100)))

    def test_cumulative_displacement_slow_mouse_regains_control(self):
        """Mouvement lent : 1 pixel par evenement. L'ancien test (ecart d'un evenement au suivant < 3 px) ne la reprenait jamais ; l'ecart cumule la reprend au bout de quelques evenements (sans delai)."""
        def old(prev_pos, pos): return not (prev_pos is None or abs(pos[0] - prev_pos[0]) + abs(pos[1] - prev_pos[1]) < 3)
        path = [(100 + i, 100) for i in range(1, 60)]                                    # 59 evenements de 1 pixel
        prev = (100, 100); resumed = False
        for p in path:
            if old(prev, p): resumed = True
            prev = p
        self.assertFalse(resumed)                                                           # (le defaut d'origine : la souris restait inutilisable tant que le geste n'etait pas rapide)
        g = EN.MouseGuard(); g.keyboard((100, 100)); n = 0
        for p in path:
            n += 1
            if g.has_moved(p): break
        self.assertTrue(g.mouse)
        self.assertLessEqual(n, math.ceil(EN.MOUSE_TOLERANCE))                            # 4 evenements de 1 pixel : quelques millisecondes, pas une seconde

    def test_jitter_does_not_resume(self):
        g = EN.MouseGuard(); g.keyboard((300, 200))
        for p in [(300, 200), (301, 200), (300, 201), (299, 199), (301, 201), (300, 200)] * 10: self.assertFalse(g.has_moved(p))
        self.assertFalse(g.mouse)

    def test_tremor_does_not_add_up(self):
        """L'ecart est mesure depuis le point de la derniere touche, pas somme d'un evenement a l'autre : aller-retour de 2 px mille fois ne fait pas un mouvement."""
        g = EN.MouseGuard(); g.keyboard((50, 50))
        for i in range(1000): self.assertFalse(g.has_moved((52, 50) if i % 2 == 0 else (50, 50)))

    def test_click_always_acts_and_returns_control(self):
        g = EN.MouseGuard(); g.keyboard((10, 10)); self.assertFalse(g.mouse)
        g.click(); self.assertTrue(g.mouse)
        self.assertTrue(g.has_moved((10, 10)))                                                 # la souris a la main : tout evenement compte, meme sans deplacement

    def test_once_resumed_the_mouse_keeps_control(self):
        g = EN.MouseGuard(); g.keyboard((0, 0))
        self.assertTrue(g.has_moved((40, 0)))
        self.assertTrue(g.has_moved((41, 0))); self.assertTrue(g.has_moved((41, 0)))               # plus de tolerance : le survol suit chaque evenement
        g.keyboard((41, 0)); self.assertFalse(g.has_moved((41, 1)))                             # une nouvelle touche : le clavier reprend la main

    def test_unknown_position(self):
        g = EN.MouseGuard(); g.keyboard(None); self.assertTrue(g.mouse); self.assertTrue(g.has_moved((5, 5)))


class StandaloneWheelGesture(unittest.TestCase):
    def test_simple_click_recenters(self):
        m = EN.WheelGesture(); m.press_state(500, 300)
        self.assertTrue(m.let_go())

    def test_jitter_stays_a_click(self):
        m = EN.WheelGesture(); m.press_state(500, 300)
        for p in [(502, 301), (499, 302), (501, 299), (503, 300)]: self.assertEqual(m.move_to(*p), 0.0)
        self.assertTrue(m.let_go())

    def test_slide_no_jump_at_start_and_recenters_nothing(self):
        m = EN.WheelGesture(); m.press_state(500, 300)
        self.assertEqual(m.move_to(503, 300), 0.0)                                        # sous le seuil
        self.assertEqual(m.move_to(520, 300), 0.0)                                        # seuil franchi : le geste devient un glissement, la camera ne bouge pas encore (pas de saut des 20 premiers pixels)
        self.assertEqual(m.move_to(530, 310), 10.0)                                       # ensuite : l'ecart horizontal a l'evenement precedent (le vertical ne compte pas)
        self.assertEqual(m.move_to(530, 310), 0.0)
        self.assertFalse(m.let_go()); self.assertFalse(m.let_go())                     # apres un glissement le relachement ne recentre rien

    def test_vertical_slide_does_not_turn_but_is_no_longer_a_click(self):
        m = EN.WheelGesture(); m.press_state(500, 300)
        for y in (330, 380, 450): self.assertEqual(m.move_to(500, y), 0.0)
        self.assertFalse(m.let_go())

    def test_return_to_start_stays_a_slide(self):
        m = EN.WheelGesture(); m.press_state(500, 300); m.move_to(600, 300); m.move_to(500, 300)
        self.assertFalse(m.let_go())                                                     # (on a tourne la camera : ce n'est plus un clic)

    def test_nothing_without_press(self):
        m = EN.WheelGesture(); self.assertEqual(m.move_to(10, 10), 0.0); self.assertFalse(m.let_go())
        m.press_state(1, 1); m.cancel(); self.assertFalse(m.let_go()); self.assertEqual(m.move_to(300, 300), 0.0)


class Rotation(unittest.TestCase):
    def piv(self, requested, dx, h=720.0, inv=False, maximum=180.0): return EN.rotate(requested, dx, h, inv, maximum)

    def test_direction_like_the_arrows(self):
        self.assertGreater(self.piv(0.0, 100), 0.0)                                        # droite = fleche droite
        self.assertLess(self.piv(0.0, -100), 0.0)

    def test_sensitivity_independent_of_resolution(self):
        self.assertAlmostEqual(self.piv(0.0, 360, h=720), self.piv(0.0, 540, h=1080))      # la moitie de la hauteur = la meme rotation
        self.assertAlmostEqual(self.piv(0.0, 360, h=720), EN.CAM_MOUSE_YAW / 2)

    def test_remaining_rotation_is_added(self):
        self.assertAlmostEqual(self.piv(10.0, 100), 10.0 + self.piv(0.0, 100))
        self.assertAlmostEqual(self.piv(10.0, -100), 10.0 + self.piv(0.0, -100))

    def test_plafond(self):
        """Un grand glissement ne fait pas tourner la camera longtemps apres le relachement : la rotation demandee est plafonnee (et ne boucle pas : le jeu tourne par crans, il n'y a plus de cap a ramener entre -180 et 180)."""
        self.assertEqual(self.piv(100.0, 5000), 180.0); self.assertEqual(self.piv(-100.0, -5000), -180.0)
        self.assertEqual(self.piv(0.0, 5000, maximum=45.0), 45.0)

    def test_zero_height(self):
        self.assertTrue(math.isfinite(self.piv(0.0, 10, h=0)))

    def test_left_right_inversion(self):
        for dx in (100, -60, 5):
            normal = self.piv(0.0, dx); inv = self.piv(0.0, dx, inv=True)
            self.assertAlmostEqual(inv, -normal); self.assertAlmostEqual(inv, self.piv(0.0, -dx))      # = glisser de l'autre cote

    def test_default_without_inversion(self):
        self.assertEqual(EN.rotate(0.0, 100, 720.0), self.piv(0.0, 100))


class InfoF1(unittest.TestCase):
    def test_top_right_by_default(self):
        for l, h in ((1280, 720), (1920, 1080), (2560, 1080), (960, 720)):
            side, wid = EN.info_zone(l, h, True, 1.12, 'centre')
            self.assertEqual(side, 'droite', (l, h)); self.assertGreaterEqual(wid, 260)
            self.assertEqual(EN.info_zone(l, h, False, 1.12, 'centre')[0], 'droite')      # sans fenetres du jeu : tout l'ecran, toujours a droite

    def test_width_leaves_interface_column(self):
        l, h = 1920, 1080; col = 450 * h / 800.0 * 1.12
        side, wid = EN.info_zone(l, h, True, 1.12, 'centre')
        self.assertLessEqual(wid, (l - col) / 2)                                          # ne recouvre pas la colonne centree
        self.assertEqual(EN.info_zone(l, h, False, 1.12, 'centre')[1], l - 20)

    def test_right_column_block_moves_left(self):
        self.assertEqual(EN.info_zone(1920, 1080, True, 1.12, 'droite')[0], 'gauche')
        self.assertEqual(EN.info_zone(1920, 1080, True, 1.12, 'gauche')[0], 'droite')


try:
    from dq4_pc.persistence import settings as RG
    from dq4_pc.menus import pause as PA
except Exception as ex:          # pause.py a besoin de pyglet (sans affichage : l'import seul suffit)
    PA = None


@unittest.skipIf(PA is None, 'pause.py non importable ici')
class PauseMouseAfterKeyboard(unittest.TestCase):
    """Menu Echap : une touche remet la selection au clavier ; la souris reprend la main au premier vrai mouvement (pas apres un tremblement), un clic aussitot."""
    LINES = [(500.0, 400.0 - 40 * i, 780.0, 436.0 - 40 * i, i) for i in range(6)]          # six lignes de 36 px, la premiere en haut

    def pause(self, pos=(640.0, 300.0)):
        guard = EN.MouseGuard()
        game = types.SimpleNamespace(reg=RG.Settings(None), hud=types.SimpleNamespace(taken=None, place=lambda: None), width=1280, height=720, mouse=pos, mouse_guard=guard,
                                    sound=types.SimpleNamespace(listening=False, listen=lambda b: None, tick=lambda: None), key_list={}, pause_game=lambda yes: None)
        P = PA.Pause(game); P.opened = True; P.stack = ['racine']; P.zones = list(self.LINES); P.mouse_pos = pos; P.selected['racine'] = 0; P.mouse_mode = False
        return P

    def test_slow_one_pixel_per_event(self):
        P = self.pause(); P.key_press(pyglet.window.key.F5); self.assertFalse(P.mouse_mode)             # une touche (sans effet) : retour au clavier
        for i in range(1, 12):                                                                        # le pointeur descend d'un pixel par evenement, de y = 300 (ligne 2, entre 276 et 320 : la ligne 3 est entre 236 et 276)
            P.hovered(640.0, 300.0 - i)
            if P.mouse_mode: break
        self.assertTrue(P.mouse_mode); self.assertLessEqual(i, 5)                                    # au 4e pixel : aucune attente
        P.hovered(640.0, 250.0)
        self.assertEqual(P._zone(640.0, 250.0)[0], P.selected['racine'])                                   # la selection suit le pointeur

    def test_jitter_changes_nothing(self):
        P = self.pause(); P.key_press(pyglet.window.key.F5); before = P.selected['racine']
        for p in [(641, 300), (640, 301), (639, 299), (640, 300)] * 20: P.hovered(*p)
        self.assertFalse(P.mouse_mode); self.assertEqual(P.selected['racine'], before)

    def test_click_acts_immediately(self):
        P = self.pause(); P.key_press(pyglet.window.key.F5)
        P.click(640.0, 250.0, 1)                                                                       # clic gauche juste apres la touche
        self.assertTrue(P.mouse_mode); self.assertEqual(P.selected['racine'], P._zone(640.0, 250.0)[0])

    def test_pointer_outside_window_first_movement_counts(self):
        P = self.pause(); P.output(); P.key_press(pyglet.window.key.F5); P.hovered(641.0, 250.0)
        self.assertTrue(P.mouse_mode)

    def test_keyboard_opening_mouse_at_rest_takes_nothing(self):
        P = self.pause(); P.opened = False; P.open_menu()
        P.hovered(640.0, 300.0); P.hovered(641.0, 300.0)
        self.assertFalse(P.mouse_mode)
        P.hovered(660.0, 300.0); self.assertTrue(P.mouse_mode)


class DummyEngine:
    """Le jeu vu par la visionneuse : accepte (ou refuse) le bouton de camera de ce pas, le garde en attente (TownPlayerManager + 0x698) et tourne d'UN cran au pas suivant, sauf si `camera_turn` en a fait n tout de suite."""
    def __init__(self):
        ENGINE = WND.ENGINE
        self.state = types.SimpleNamespace(part=ENGINE.PART_TOWN, effect=None, cam_free=False, cam_rot=None, cam_pos=None, cam_target=None)
        self.msg_visible = False; self.active_menu = lambda: None
        self.accepte = True; self.waiting = 0; self.crans = 0; self.calls = []; self.bits = []

    def camera_wait(self): return self.waiting

    def camera_turn(self, direction, times): self.calls.append((direction, times)); self.crans += times * (1 if direction == WND.ENGINE.ROT_CAM_RIGHT else -1); self.waiting = 0

    def step(self, bits):
        """Un pas du moteur avec ces boutons de camera."""
        ENGINE = WND.ENGINE; self.bits.append(bits)
        if self.waiting:                                                            # rotation en attente depuis le pas d'avant (non consommee par camera_turn) : le jeu tourne d'un cran
            self.crans += 1 if self.waiting == ENGINE.ROT_CAM_RIGHT else -1; self.waiting = 0
        if self.accepte and bits in (ENGINE.CAM_D, ENGINE.CAM_G): self.waiting = ENGINE.ROT_CAM_RIGHT if bits == ENGINE.CAM_D else ENGINE.ROT_CAM_LEFT


class Fake:
    """Un `Game` minimal : les vraies methodes de fenetre.Game (liees a cet objet) travaillent sur un moteur factice qui accepte ou refuse les boutons de camera."""
    def __init__(self, part=None, **kw):
        ENGINE = WND.ENGINE
        self.engine = DummyEngine()
        if part is not None: self.engine.state.part = part
        self.pause = types.SimpleNamespace(opened=False); self.license_panel = None; self.saves_screen = None; self.title_screen = None; self._name_entry_in_progress = lambda: False; self.map_open = False; self.map_name = None
        self.hud = types.SimpleNamespace(dpad_on=False, dpad_bits=lambda: 0); self.press_state = None; self.wheel = EN.WheelGesture(); self.height = 720
        self.cam_direction = (0, False); self.cam_recenter = False; self.cam_two = False; self.cam_request = 0.0; self.cam_acc = 0.0
        self.key_list = {}; self.reg = {'camera_inverser_gd': False, 'vitesse_camera': 1.0, 'vitesse_accel': 1.5}
        self._ready = True; self.fixed_test = True
        for k, v in kw.items(): setattr(self, k, v)
        for name_str in ('_terrain_free', '_drivable_camera', 'recenter_camera', '_wheel_press', '_wheel_drag', '_wheel_release', '_axis_state', '_bits_camera', '_camera_after_step', '_camera_oublier', 'pad', 'on_mouse_scroll'):
            setattr(self, name_str, types.MethodType(getattr(WND.Game, name_str), self))
        self._held = lambda a: False

    def hold(self, *actions): self._held = lambda a: a in actions

    def frames(self, n):
        """n pas du moteur : les boutons de camera que la visionneuse envoie (`Game._entries`, terrain), puis le suivi du pas (`Game.tick`)."""
        for _ in range(n):
            bits = self._bits_camera(); self.engine.step(bits); self._camera_after_step(self.engine)
        return self.engine.bits[-n:]

    def click(self, x=500, y=300):
        self._wheel_press(x, y); self._wheel_release()


BOTH = lambda: WND.ENGINE.CAM_G | WND.ENGINE.CAM_D


@unittest.skipIf(WND is None, 'window.py non importable ici')
class WheelInGame(unittest.TestCase):
    def recenter(self, j): return j.cam_recenter

    def test_click_in_town_requests_return_to_north(self):
        j = Fake(); j.click()
        self.assertTrue(self.recenter(j)); self.assertEqual(j.frames(3), [BOTH(), 0, 0])        # les deux boutons de camera ensemble, une seule fois : le jeu anime le retour au nord (et tient le joueur)

    def dragging(self, gd, ndy=-40):
        j = Fake(); j.reg['camera_inverser_gd'] = gd
        j._wheel_press(500, 300); j._wheel_drag(520, 300); j._wheel_drag(620, 300 + ndy)          # 100 px vers la droite, ndy vers le haut (y pyglet vers le haut)
        return j

    def test_slide_inversion_in_game(self):
        self.assertGreater(self.dragging(False).cam_request, 0.0)                            # sans inversion : droite = a droite, comme la fleche droite
        for dy in (-40, 0, 40):
            self.assertAlmostEqual(self.dragging(True, dy).cam_request, -self.dragging(False, dy).cam_request)
        self.assertAlmostEqual(self.dragging(False, 40).cam_request, self.dragging(False, -40).cam_request)      # le deplacement vertical ne change rien

    def test_inversion_leaves_keyboard_arrows_alone(self):
        """Fleches gauche / droite tenues 30 pas : memes boutons de camera et meme nombre de crans quel que soit le reglage d'inversion."""
        ENGINE = WND.ENGINE
        for held_name, bit, signe in (('cam_droite', ENGINE.CAM_D, 1), ('cam_gauche', ENGINE.CAM_G, -1)):
            res = []
            for gd in (False, True):
                j = Fake(); j.reg['camera_inverser_gd'] = gd; j.hold(held_name); b = j.frames(30); res.append((set(b), j.engine.crans))
            self.assertEqual(res[0], res[1], held_name); self.assertEqual(res[0][0], {bit}); self.assertEqual(res[0][1], 29 * signe)      # (le dernier cran est consomme au pas d'apres)

    def test_inversion_has_no_effect_on_return_to_north(self):
        for gd in (False, True):
            j = Fake(); j.reg['camera_inverser_gd'] = gd; j.click(); self.assertEqual(j.frames(1), [BOTH()])

    def test_click_followed_by_movement_is_not_a_click(self):
        j = Fake(); j._wheel_press(500, 300); j._wheel_drag(530, 300); j._wheel_drag(500, 300); j._wheel_release()      # revenu au point de depart : toujours un glissement
        self.assertFalse(self.recenter(j))
        j = Fake(); j._wheel_press(500, 300); j._wheel_drag(502, 301); j._wheel_release()                                    # un simple tremblement reste un clic
        self.assertTrue(self.recenter(j))

    def test_slide_requests_rotation_like_arrows(self):
        ENGINE = WND.ENGINE
        j = Fake(); j._wheel_press(500, 300); j._wheel_drag(520, 300); j._wheel_drag(620, 360)
        self.assertGreater(j.cam_request, 0.0); requested = j.cam_request
        j._wheel_release(); self.assertFalse(self.recenter(j))                           # le relachement d'un glissement ne demande aucun retour au nord
        b = j.frames(1); self.assertEqual(b, [ENGINE.CAM_D])                                   # la camera tourne a droite, par le bouton de camera du jeu
        j = Fake(); j._wheel_press(500, 300); j._wheel_drag(500, 340); j._wheel_drag(500, 480); self.assertEqual(j.cam_request, 0.0); self.assertEqual(j.frames(3), [0, 0, 0])      # purement vertical : rien ne tourne
        j = Fake(); j.reg['camera_inverser_gd'] = True; j._wheel_press(500, 300); j._wheel_drag(520, 300); j._wheel_drag(620, 300); self.assertEqual(j.frames(1), [ENGINE.CAM_G])

    def test_sliding_follows_pointer_in_notches(self):
        """La rotation demandee est faite par des crans du jeu (ENGINE.CAM_STEP chacun, au plus CAM_DRAG_STEP par pas), puis s'arrete : le reste de moins d'un demi-cran n'est pas tourne, il s'ajoute au glissement suivant."""
        ENGINE = WND.ENGINE
        j = Fake(); j.cam_request = 40.0; j.frames(60)
        self.assertAlmostEqual(j.engine.crans * ENGINE.CAM_STEP, 40.0, delta=ENGINE.CAM_STEP / 2 + 1e-9); self.assertLess(abs(j.cam_request), ENGINE.CAM_STEP / 2 + 1e-9)
        self.assertLessEqual(max(f for _, f in j.engine.calls), WND.CAM_DRAG_STEP)
        j = Fake(); j.cam_request = 40.0; j.frames(1); self.assertEqual(j.engine.calls, [(ENGINE.ROT_CAM_RIGHT, WND.CAM_DRAG_STEP)])         # un grand glissement : plusieurs crans dans le meme pas
        j = Fake(); j.cam_request = -1.0; self.assertEqual(j.frames(3), [0, 0, 0])                                                   # moins d'un demi-cran : rien
        j = Fake(); j.cam_request = -ENGINE.CAM_STEP; j.frames(3); self.assertEqual(j.engine.crans, -1)

    def test_arrows_prevail_over_sliding(self):
        j = Fake(); j.cam_request = -40.0; j.hold('cam_droite'); self.assertEqual(j.frames(2), [WND.ENGINE.CAM_D] * 2)

    def test_game_refuses_rotation(self):
        """Verrou du joueur, scene, lieu qui interdit de tourner, limite atteinte : le jeu ne prend pas le bouton (rien en attente). La visionneuse n'ajoute aucun verrou a elle (elle envoie le bouton, le jeu decide) mais abandonne la rotation demandee a la souris."""
        j = Fake(); j.engine.accepte = False; j.cam_request = 40.0; j.frames(3)
        self.assertEqual(j.cam_request, 0.0); self.assertEqual(j.engine.crans, 0); self.assertEqual(j.engine.calls, [])
        j = Fake(); j.engine.accepte = False; j.hold('cam_droite'); self.assertEqual(j.frames(3), [WND.ENGINE.CAM_D] * 3); self.assertEqual(j.engine.crans, 0)          # (les fleches ne sont pas abandonnees : le jeu peut la reprendre la fin de la scene)
        j = Fake(); j.engine.accepte = False; j.click(); self.assertEqual(j.frames(2), [BOTH(), 0])

    def test_terrain_changes_between_press_and_release(self):
        """Un message qui s'ouvre pendant que le bouton du milieu est enfonce : le relachement ne demande rien, et le glissement ne tourne rien."""
        j = Fake(); j._wheel_press(500, 300); j.engine.msg_visible = True
        j._wheel_drag(520, 300); j._wheel_drag(560, 300); self.assertEqual(j.cam_request, 0.0)
        j._wheel_release(); self.assertFalse(self.recenter(j))
        j = Fake(); j._wheel_press(500, 300); j.engine.msg_visible = True; j._wheel_release(); self.assertFalse(self.recenter(j))                  # un clic simple, mais le terrain n'est plus libre

    def test_a_pending_request_is_not_sent_after_a_menu(self):
        """Rotation demandee ou retour au nord demande, puis un message s'ouvre avant le pas : ils sont oublies (`Game._entries` : hors terrain), ils ne partent pas a la fermeture du message."""
        j = Fake(); j.cam_request = 40.0; j.recenter_camera(); j.engine.msg_visible = True; j._camera_oublier(); j.engine.msg_visible = False
        self.assertEqual(j.frames(3), [0, 0, 0])

    def test_return_to_north_clears_rotation_requested_by_mouse(self):
        """Clic molette (retour au nord) alors qu'une rotation de la souris restait a faire : le jeu ramene la camera au nord, la rotation restante n'est pas faite apres coup."""
        j = Fake(); j.cam_request = 40.0; j.recenter_camera()
        self.assertEqual(j.frames(4), [BOTH(), 0, 0, 0]); self.assertEqual(j.cam_request, 0.0); self.assertEqual(j.engine.calls, [])

    def test_slide_cancels_return_to_north_not_yet_sent(self):
        j = Fake(); j.recenter_camera(); j._wheel_press(500, 300); j._wheel_drag(520, 300); j._wheel_drag(620, 300)
        self.assertFalse(self.recenter(j)); self.assertEqual(j.frames(1), [WND.ENGINE.CAM_D])

    def test_press_in_menu_then_free_field_on_release(self):
        """Le bouton du milieu enfonce pendant un message, le message se ferme, puis il est relache : ce n'est pas un clic sur le terrain (le geste n'a jamais commence)."""
        j = Fake(); j.engine.msg_visible = True; j._wheel_press(500, 300); j.engine.msg_visible = False
        j._wheel_release(); self.assertFalse(self.recenter(j))
        j._wheel_drag(560, 300); self.assertEqual(j.cam_request, 0.0)

    def test_outside_terrain_nothing_happens(self):
        ENGINE = WND.ENGINE
        def fake(name_str):
            j = Fake()
            if name_str == 'pause': j.pause.opened = True
            elif name_str == 'message': j.engine.msg_visible = True
            elif name_str == 'menu': j.engine.active_menu = lambda: 12
            elif name_str == 'combat': j.engine.state.part = ENGINE.PART_BATTLE
            elif name_str == 'titre': j.title_screen = object()
            elif name_str == 'licence': j.license_panel = object()
            elif name_str == 'sauvegardes': j.saves_screen = object()
            elif name_str == 'nom': j._name_entry_in_progress = lambda: True
            elif name_str == 'carte': j.map_open = True
            elif name_str == 'effet': j.engine.state.effect = object()
            elif name_str == 'croix': j.hud.dpad_on = True
            elif name_str == 'bouton': j.press_state = (12, 0, 16)
            elif name_str == 'ecran-titre': j.map_name = WND.TITLE_MAP
            return j
        for name_str in ('pause', 'message', 'menu', 'combat', 'titre', 'licence', 'sauvegardes', 'nom', 'carte', 'effet', 'croix', 'bouton', 'ecran-titre'):
            j = fake(name_str); j.click(); j._wheel_press(0, 0); j._wheel_drag(50, 50); j._wheel_drag(120, 90); j._wheel_release()
            self.assertEqual(j.cam_request, 0.0, name_str); self.assertFalse(self.recenter(j), name_str)
            if name_str in ('croix', 'bouton'): continue                                                           # (la croix et les boutons de l'ecran sont tenus a la souris : ils ne bloquent que le clic molette, pas les fleches du clavier)
            j = fake(name_str); j.hold('cam_droite', 'cam_gauche'); self.assertEqual(j.frames(30), [0] * 30, name_str); self.assertFalse(self.recenter(j), name_str)
            j = fake(name_str); j.hold('cam_droite'); self.assertEqual(j.frames(5), [0] * 5, name_str)

    def test_world_map_no_rotation(self):
        j = Fake(part=WND.ENGINE.PART_FIELD); j.click(); self.assertFalse(self.recenter(j))          # pas de rotation sur la carte du monde (comme les fleches)
        j.hold('cam_droite'); self.assertEqual(j.frames(30), [0] * 30)

    def test_wheel_no_longer_does_anything_on_terrain(self):
        for part in (None, WND.ENGINE.PART_FIELD):
            j = Fake(part=part); j.hold('modif'); j.on_mouse_scroll(0, 0, 0, 1); j.on_mouse_scroll(0, 0, 0, -3)
            self.assertEqual(j.cam_request, 0.0); self.assertFalse(self.recenter(j)); self.assertEqual(j.frames(2), [0, 0])
            self.assertFalse(hasattr(j, 'zoom'))


@unittest.skipIf(WND is None, 'window.py non importable ici')
class ArrowsInGame(unittest.TestCase):
    def test_arrows_rotate_game_camera(self):
        ENGINE = WND.ENGINE
        j = Fake(); j.hold('cam_droite'); self.assertEqual(j.frames(30), [ENGINE.CAM_D] * 30); self.assertEqual(j.engine.crans, 29); self.assertEqual(j.engine.calls, [])          # un cran par pas, par le jeu : 84,4 degres par seconde
        j = Fake(); j.hold('cam_gauche'); self.assertEqual(j.frames(30), [ENGINE.CAM_G] * 30); self.assertEqual(j.engine.crans, -29)

    def test_camera_buttons_are_bits_4_and_5_of_held_keys(self):
        """Sur le terrain d'une ville, (Global + 0xe0) >> 4 & 3 : 1 = gauche, 2 = droite, 3 = retour au nord (NormalControl::checkCamera). Ce sont les valeurs de A et B des menus : la visionneuse retire A et B du terrain (le moteur y veut BTN_TALK)."""
        ENGINE = WND.ENGINE
        self.assertEqual((ENGINE.CAM_G, ENGINE.CAM_D), (0x10, 0x20)); self.assertEqual((ENGINE.CAM_G, ENGINE.CAM_D), (ENGINE.A, ENGINE.B))
        self.assertAlmostEqual(ENGINE.CAM_STEP, 2.8125)

    def test_camera_speed(self):
        """x2 = deux crans par pas, x4 = quatre ; le premier cran est celui du bouton (pas d'appel), les autres sont ajoutes tout de suite."""
        ENGINE = WND.ENGINE
        for v in (1.0, 2.0, 3.0, 4.0):
            j = Fake(); j.reg['vitesse_camera'] = v; j.hold('cam_droite'); j.frames(10); self.assertEqual(j.engine.crans, 10 * int(v) if v > 1 else 9, v)
            if v > 1: self.assertEqual(set(j.engine.calls), {(ENGINE.ROT_CAM_RIGHT, int(v))})
            else: self.assertEqual(j.engine.calls, [])

    def test_camera_speed_to_the_left(self):
        ENGINE = WND.ENGINE
        j = Fake(); j.reg['vitesse_camera'] = 3.0; j.hold('cam_gauche'); j.frames(10)
        self.assertEqual(j.engine.crans, -30); self.assertEqual(set(j.engine.calls), {(ENGINE.ROT_CAM_LEFT, 3)})

    def test_no_extra_notch_during_return_to_north(self):
        """Le jeu tient la camera (retour au nord en cours : le type en attente est celui du nord, pas celui du bouton envoye) : la visionneuse n'y ajoute aucun cran, ni pour les fleches ni pour le glissement."""
        ENGINE = WND.ENGINE
        j = Fake(); j.reg['vitesse_camera'] = 4.0; j.cam_direction = (-1, False); j.engine.waiting = ENGINE.ROT_CAM_NORD
        j._camera_after_step(j.engine); self.assertEqual(j.engine.calls, [])
        j.cam_request = -40.0; j.cam_direction = (-1, True); j._camera_after_step(j.engine); self.assertEqual(j.engine.calls, []); self.assertEqual(j.cam_request, 0.0)

    def test_no_sliding_while_arrow_is_held(self):
        j = Fake(); j.hold('cam_gauche', 'cam_droite'); self.assertEqual(j.frames(1), [BOTH()])
        j.cam_request = 40.0; self.assertEqual(j.frames(3), [0, 0, 0])
        j.hold('cam_droite'); self.assertEqual(j.frames(2), [0, 0])                  # (la fleche restante apres la pression double)
        j.hold(); self.assertEqual(j.frames(1), [WND.ENGINE.CAM_D])                       # tout relache : la rotation demandee a la souris repart

    def test_non_integer_speed_spread_from_one_step_to_the_next(self):
        j = Fake(); j.reg['vitesse_camera'] = 1.5; j.hold('cam_droite'); j.frames(40); self.assertAlmostEqual(j.engine.crans, 60, delta=2)

    def test_accelerator_does_not_accelerate_camera(self):
        j = Fake(); j.hold('cam_droite'); j.frames(30); ref = j.engine.crans
        j = Fake(); j.hold('cam_droite', 'accel'); j.frames(30); self.assertEqual(j.engine.crans, ref)
        j = Fake(); j.reg['vitesse_accel'] = 2.0; j.hold('cam_gauche', 'accel'); j.frames(30); self.assertEqual(j.engine.crans, -ref)

    def test_up_down_do_nothing_on_terrain(self):
        j = Fake(); j.hold('cam_haut', 'cam_bas'); self.assertEqual(j.frames(30), [0] * 30); self.assertEqual(j.pad(), 0)          # (ils ne servent que dans les menus : plus d'inclinaison)

    def test_two_arrows_return_camera_to_north_once(self):
        ENGINE = WND.ENGINE
        j = Fake(); j.hold('cam_gauche', 'cam_droite'); self.assertEqual(j.frames(10), [BOTH()] + [0] * 9)          # les deux boutons de camera du jeu au premier pas seulement : le jeu fait le reste (animation, joueur tenu)
        self.assertEqual(j.engine.crans, 0)

    def test_arrow_still_pressed_after_double_press_does_nothing(self):
        ENGINE = WND.ENGINE
        j = Fake(); j.hold('cam_gauche', 'cam_droite'); j.frames(1); j.hold('cam_droite'); self.assertEqual(j.frames(10), [0] * 10)        # la fleche restante (relachement jamais simultane) ne tourne pas
        j.hold('cam_gauche', 'cam_droite'); self.assertEqual(j.frames(2), [0, 0])                                                         # (l'autre re-enfoncee alors que la premiere est restee tenue : pas de nouveau retour au nord)
        j.hold(); j.frames(1); j.hold('cam_droite'); self.assertEqual(j.frames(3), [ENGINE.CAM_D] * 3)                                      # tout relache, puis une fleche seule : la camera tourne a nouveau
        j.hold('cam_gauche', 'cam_droite'); self.assertEqual(j.frames(2), [BOTH(), 0])                                                    # une fleche tenue, l'autre s'y ajoute : pression double, retour au nord

    def test_two_arrows_already_held_when_returning_to_field(self):
        """Les deux fleches tenues pendant un message, puis le message se ferme : pas de retour au nord (ce n'est pas une pression double sur le terrain)."""
        j = Fake(); j.engine.msg_visible = True; j.hold('cam_gauche', 'cam_droite'); j._camera_oublier(); j.engine.msg_visible = False
        self.assertEqual(j.frames(5), [0] * 5)

    def test_viewer_no_longer_rotates_walk_directions(self):
        """Les directions de marche sont celles de l'ecran, tournees par le jeu selon sa camera (comme sur mobile) : plus de rotation faite par la visionneuse."""
        ENGINE = WND.ENGINE
        for held_name, wanted in ((('haut',), ENGINE.UP), (('bas',), ENGINE.DOWN), (('gauche',), ENGINE.LEFT), (('droite',), ENGINE.RIGHT), (('haut', 'droite'), ENGINE.UP | ENGINE.RIGHT)):
            j = Fake(); j.hold(*held_name); self.assertEqual(j.pad(), wanted, held_name)
        j = Fake(); j.hold('A'); self.assertEqual(j.pad(), ENGINE.A)
        for name_str in ('_lacet_eff', '_tourner_dir', '_maj_camera', '_camera_menee', '_coupure_camera'): self.assertFalse(hasattr(WND.Game, name_str), name_str)
        for name_str in ('yaw', 'cam_w', 'cam_jeu', 'cam_bloquee', 'cam_limite', 'cam_saut', 'cam_axe'): self.assertFalse(hasattr(Fake(), name_str), name_str)

    def test_in_menus_arrows_are_directions(self):
        ENGINE = WND.ENGINE
        j = Fake(); j.engine.msg_visible = True
        for action, bit in (('cam_haut', ENGINE.UP), ('cam_bas', ENGINE.DOWN), ('cam_gauche', ENGINE.LEFT), ('cam_droite', ENGINE.RIGHT)):
            j.hold(action); self.assertEqual(j.pad(), bit, action)

    def test_inputs_sends_camera_buttons_on_terrain_only(self):
        """Branchement (le code est relu, la fenetre n'est pas ouverte) : `_entries` ajoute les boutons de camera apres avoir retire A et B, dans la branche du terrain ; ailleurs elle oublie les demandes ; `tick` suit le pas avec _camera_after_step."""
        import inspect
        src = inspect.getsource(WND.Game._entries)
        self.assertIn('p &= ~(ENGINE.A | ENGINE.B)\n            terrain = True; p |= self._bits_camera()', src)
        self.assertIn('if not terrain: self._camera_oublier()', src)
        tick = inspect.getsource(WND.Game.tick)
        self.assertLess(tick.index('eng.step(p, decl)'), tick.index('self._camera_after_step(eng)'))


if __name__ == '__main__':
    unittest.main(verbosity=1)
