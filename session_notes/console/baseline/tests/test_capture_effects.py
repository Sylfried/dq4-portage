"""Effets d'ecran de la classe `Capture` (paquet 34, valeurs 3 : voyage / ailes de Chimere, 5 : lampe / Ranaruta, 6 : Riremito ; audit UNI-06) :

  1. modules purs (rendu/tabi_effect.py, lamp_effect.py, riremito_effect.py) : nombre d'appels de MoveNext (64, 45 a l'arrivee, 64, 63), moment ou le rendu s'allume et s'eteint, valeurs de controle lues dans la
     specification (sommets de Tabi, octets de la lampe, deplacements de Riremito), passes de flou (une par image, deux textures en alternance, la premiere lit « rien ») et tampons de dessin ;
  2. moteur (Engine._start_screen_effect / _screen_effect, sans moteur : le drapeau est simule) : bit 7 de la valeur (arrivee, matin), duree qui suit « Vitesse de transition », noir immediat de la lampe et de Riremito
     (State.sharp_black_fade), fondu d'entree et fin de l'ecran noir a l'arrivee d'un voyage, garde-fous, un seul effet a la fois, un etat enregistre avant le correctif.

    python3 tests/test_capture_effects.py
"""
import os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
from dq4_pc.core import engine as ENGINE
from dq4_pc.core import game_priority as PJ
from dq4_pc.render import capture_effects as EF
from dq4_pc.render.lamp_effect import LampEffect
from dq4_pc.render.riremito_effect import RiremitoEffect
from dq4_pc.render.tabi_effect import TabiEffect


def play(effect, toward=None):
    """Fait tourner l'effet jusqu'a sa fin (ou jusqu'a l'appel `toward`) ; rend la liste des (appel, render_active)."""
    savestates = []
    while not effect.finished and (toward is None or effect.frames < toward):
        effect.stage(); savestates.append((effect.frames, effect.render_active))
    return savestates


class Durations(unittest.TestCase):
    def test_move_next_call_count(self):
        for name_str, factory, expected in (('tabi', lambda: TabiEffect(False), 64), ('tabi_retour', lambda: TabiEffect(True), 45), ('lampe', LampEffect, 64), ('riremito', RiremitoEffect, 63)):
            e = factory(); savestates = play(e)
            self.assertEqual(e.frames, expected, name_str); self.assertEqual(EF.FRAMES[name_str], expected); self.assertTrue(e.finished); self.assertEqual(e.duration, expected)
        self.assertEqual(EF.frames_of('tabi', True), 45); self.assertEqual(EF.frames_of('tabi', False), 64); self.assertEqual(EF.frames_of('lampe', True), 64)       # (bit 7 : sans effet hors voyage)
        self.assertEqual(EF.KINDS, {3: 'tabi', 5: 'lampe', 6: 'riremito'})

    def test_game_stays_normal_first_two_calls(self):
        for factory in (lambda: TabiEffect(False), LampEffect, RiremitoEffect):
            e = factory(); savestates = play(e, 3)
            self.assertEqual(savestates, [(1, False), (2, False), (3, True)])                              # le rendu s'allume au 3e appel (la capture a ete faite au debut du 2e)

    def test_render_end(self):
        e = TabiEffect(False); savestates = play(e); self.assertTrue(savestates[-1][1])                          # le depart n'eteint rien : l'ecran reste noir (les deux materiaux a l'alpha 0)
        d = {n: c for n, p, u, c in e.drawings()}; self.assertTrue(np.all(d['flou'] == 0) and np.all(d['capture'] == 0))
        e = TabiEffect(True); savestates = play(e); self.assertTrue(savestates[-2][1]); self.assertFalse(savestates[-1][1]); self.assertEqual(e.drawings(), [])         # l'arrivee remet le jeu : dernier appel = rendu coupe
        e = LampEffect(); savestates = play(e); self.assertEqual([a for a, r in savestates if r], list(range(3, 64))); self.assertFalse(savestates[-1][1])
        e = RiremitoEffect(); savestates = play(e); self.assertEqual([a for a, r in savestates if r], list(range(3, 63))); self.assertFalse(savestates[-1][1])

    def test_calls_made_follow_transition_speed(self):
        self.assertEqual([EF.calls_made(n, 64, 64) for n in (0, 1, 62, 63, 64)], [1, 2, 63, 64, 64])                       # x1 : un appel par image du moteur (le premier a l'image du paquet)
        d = PJ.fade_duration(64, 2.0); self.assertEqual(d, 32)
        v = [EF.calls_made(n, d, 64) for n in range(d)]
        self.assertEqual(v[0], 2); self.assertEqual(v[-1], 64); self.assertTrue(all(b >= a for a, b in zip(v, v[1:])))


class Tabi(unittest.TestCase):
    def test_control_vertices(self):
        """Tableau de la specification (ecran 16/9 : 9 rangees, 170 sommets) : coin haut gauche (sommet 0) et bas droit (dernier) aux appels cites."""
        for inv, call, s0, sn in ((False, 3, (-1.0, 1.0), (1.0, -1.0)), (False, 4, (-0.97416, 1.00887), (0.97416, -1.00887)), (False, 33, (-0.27309, 1.02490), (0.27309, -1.02490)),
                                   (False, 63, (0.18492, 0.68250), (-0.18492, -0.68250)), (True, 3, (-0.08043, 0.93937), (0.08043, -0.93937)), (True, 43, (-1.0, 1.0), (1.0, -1.0))):
            e = TabiEffect(inv, 9); self.assertEqual(e.num, 170); play(e, call)
            np.testing.assert_allclose(e._vt[0], s0, atol=2e-5, err_msg='%s appel %d' % ('arrivee' if inv else 'depart', call)); np.testing.assert_allclose(e._vt[-1], sn, atol=2e-5)

    def test_alphas(self):
        """Montee sur 4 images (bAlpha : 0,23125 par pas au depart, cAlpha : 0,70625 puis -0,0625 par pas), puis decroissance a partir du compteur 30 (depart seulement) ; arrivee : 0,24375 / +0,0625."""
        e = TabiEffect(False); play(e, 3); self.assertAlmostEqual(float(e.alpha_blur), 0.23125, 5); self.assertAlmostEqual(float(e.alpha_capture), 0.70625, 5)
        play(e, 6); self.assertAlmostEqual(float(e.alpha_blur), 0.925, 5); self.assertAlmostEqual(float(e.alpha_capture), 0.51875, 5)
        play(e); self.assertEqual(float(e.alpha_capture), 0.0); self.assertAlmostEqual(float(e.alpha_blur), 0.6925, 4)                  # cAlpha tombe a 0 avant la fin, bAlpha pas
        a = TabiEffect(True); play(a, 6); self.assertAlmostEqual(float(a.alpha_blur), 0.975, 5); self.assertAlmostEqual(float(a.alpha_capture), 0.25, 5); play(a, 44); self.assertAlmostEqual(float(a.alpha_blur), 0.975, 5)

    def test_default_mobile_mesh(self):
        """28 rangees (m_divY = 56 de l'ecran portrait d'origine) : 17 x 29 sommets, 2 x 16 x 28 triangles ; les uv couvrent la capture."""
        e = TabiEffect(False); self.assertEqual((e.lines, e.num), (28, 17 * 29)); play(e, 3)
        name_str, pos, uv, rgba = e.drawings()[1]; self.assertEqual(name_str, 'capture'); self.assertEqual(pos.shape, (2 * 3 * 16 * 28, 2)); self.assertEqual(uv.shape, pos.shape)
        self.assertEqual((float(uv.min()), float(uv.max())), (0.0, 1.0)); self.assertLessEqual(float(np.abs(pos).max()), 1.0 + 1e-5)         # a l'appel 3 : la grille est reguliere, tout l'ecran


class Lamp(unittest.TestCase):
    def follow(self, morning):
        l = LampEffect(morning); suite = []
        while not l.finished:
            l.stage()
            if l.render_active: suite.append((int(l.cl[3, 8, 0 if not morning else 2]), int(l.cl[3, 0, 0 if not morning else 2]), float(l.bias), l.cl[3, 8].tolist(), l.cl[3, 0].tolist()))
        return l, suite

    def test_night_values(self):
        l, s = self.follow(False); c8 = [x[0] for x in s]; c0 = [x[1] for x in s]
        self.assertEqual(c8[:9], [251, 246, 240, 233, 225, 216, 206, 195, 183]); self.assertEqual(c8.index(0), 19)                         # colonne centrale : tombe a 0 au compteur 19
        self.assertEqual(c0[0], 254); self.assertEqual(c0.index(0), 57)                                                                       # colonnes du bord : tres lentement, 0 au compteur 57
        self.assertEqual(s[0][3], [251, 251, 255, 255]); self.assertEqual(s[-1][3], [0, 0, 255, 255])                                       # nuit : rouge et vert baissent, bleu (et alpha) restent a 255
        self.assertAlmostEqual(min(x[2] for x in s), 0.5880126953125, 12); self.assertAlmostEqual(max(x[2] for x in s), 1.091552734375, 12)         # « paupiere » : bias de 1 a 0,588 (compteur 27), puis jusqu'a 1,09
        self.assertAlmostEqual(float(l.b_alpha), 0.875, 5); self.assertAlmostEqual(float(l.c_alpha), 0.8125, 5); self.assertEqual(float(l.fade), 0.0)

    def test_morning_values(self):
        l, s = self.follow(True)
        self.assertEqual([x[3] for x in s[:4]], [[255, 255, 255, 255], [255, 255, 254, 255], [255, 255, 252, 255], [255, 255, 249, 255]])           # matin : seul le bleu baisse (teinte jaune) ; cbias part de 0 : rien n'est retire a la 1re mise a jour
        self.assertEqual(s[-1][3], [255, 255, 0, 255]); self.assertTrue(0 < s[-1][4][2] <= 8)                                                      # fin : centre a 0, colonnes du bord jamais a 0 (7)
        self.assertEqual(s[0][0], 255)

    def test_pinch(self):
        """Colonnes 0 et 16 : y inchange ; rangee du haut (y = 1) : la colonne centrale prend la valeur de `bias`, sa voisine 0,1 + 0,9 bias ; `bias` oscille entre 0,588 et 1,09."""
        l = LampEffect(False); seen = []; orig = l._update
        def do_update(): seen.append(float(l.bias)); orig()
        l._update = do_update; play(l, 3 + 28)
        self.assertEqual(l.counter, 28)
        np.testing.assert_array_equal(l.g[:, 0, 1], l.pt); np.testing.assert_array_equal(l.g[:, 16, 1], l.pt)
        self.assertAlmostEqual(float(l.g[0, 8, 1]), seen[-1], 5); self.assertAlmostEqual(float(l.g[0, 7, 1]), 0.1 + 0.9 * seen[-1], 5); self.assertAlmostEqual(float(l.g[0, 9, 1]), float(l.g[0, 7, 1]), 7)
        self.assertEqual(l.h_div_y, 14); self.assertEqual(l.g.shape, (15, 17, 3)); self.assertAlmostEqual(min(seen), 0.5880126953125, 12)


class Riremito(unittest.TestCase):
    def test_movements_at_last_update(self):
        r = RiremitoEffect(); play(r, 2 + 59); self.assertEqual(r.counter, 59)
        avg = [r.vt[4 * i:4 * i + 4, :2].mean(0) for i in range(4)]                                                                           # centre de chaque copie : (+-3 u, +-u), u = 0,0005 (i + 1) c
        np.testing.assert_allclose(avg, [(0.0885, -0.0295), (0.177, 0.059), (-0.2655, 0.0885), (-0.354, -0.118)], atol=1e-5)
        self.assertAlmostEqual(float(r.rot), 6.49, 4)                                                                                         # 0,11 degre par image
        np.testing.assert_allclose(r.background_mat, (0.9, 0.9, 0.9, 1.0), atol=1e-6); np.testing.assert_allclose(r.mat_capture, (0.0, 0.0, 0.0, 0.18), atol=1e-6)      # fond (b, b, b, 1) ; copies : noircies, opacite 0,18

    def test_first_step_and_blackening(self):
        r = RiremitoEffect(); play(r, 3)
        np.testing.assert_allclose(r.vt[0:4, :2].mean(0), (0.0015, -0.0005), atol=1e-6); np.testing.assert_allclose(r.mat_capture, (1, 1, 1, 0.82), atol=1e-6)      # c = 1 : u = 0,0005, copie 0 vers la droite et le bas
        play(r, 2 + 29); self.assertEqual(r.counter, 29); self.assertEqual(float(r.fade), 1.0)
        play(r, 2 + 30); self.assertAlmostEqual(float(r.fade), 1 - 1 / 30, 6)                                                                # le noircissement commence au compteur 30


class Blur(unittest.TestCase):
    def test_blur_passes(self):
        """La passe a lieu avant chaque appel tant que SetBlur est vrai (a partir du 2e) ; deux textures en alternance ; la premiere passe lit « rien » ; le rendu repasse sur l'etat de l'image PRECEDENTE."""
        for factory, last_one in ((lambda: TabiEffect(False), 64), (LampEffect, 63), (RiremitoEffect, 62)):
            e = factory(); vu = []
            e.on_blur = lambda ef, i: vu.append((ef.frames + 1, i, ef.blur_read, bool(ef.drawings())))
            play(e)
            self.assertEqual([a for a, i, l, d in vu], list(range(2, last_one + 1)))
            self.assertEqual([i for a, i, l, d in vu], [k % 2 for k in range(len(vu))]); self.assertIsNone(vu[0][2]); self.assertEqual([l for a, i, l, d in vu[1:]], [1 - i for a, i, l, d in vu[1:]])
            self.assertFalse(vu[0][3]); self.assertFalse(vu[1][3]); self.assertTrue(vu[2][3])               # appels 2 et 3 : le rendu n'est pas encore allume dans l'etat de l'image precedente

    def test_drawing_buffers(self):
        """Fond d'abord (texture floue x couleur, remplace l'ecran), puis la capture ; positions en coordonnees d'ecran normalisees ; une couleur par sommet."""
        for e in (TabiEffect(False), LampEffect(False), LampEffect(True), RiremitoEffect()):
            self.assertEqual(e.drawings(), []); play(e, 20); d = e.drawings()
            self.assertEqual([n for n, p, u, c in d], ['flou', 'capture'])
            for n, p, u, c in d: self.assertEqual((p.shape[1], u.shape[1], c.shape[1]), (2, 2, 4)); self.assertEqual(len(p), len(u)); self.assertEqual(len(p), len(c)); self.assertTrue(np.isfinite(p).all())
            np.testing.assert_array_equal(d[0][1], [(-1, 1), (1, 1), (-1, -1), (1, 1), (1, -1), (-1, -1)])              # fond : l'ecran entier
            self.assertEqual(len(d[0][1]), 6)
        e = RiremitoEffect(); play(e, 20); self.assertEqual(len(e.drawings()[1][1]), 24)                                 # quatre copies
        e = LampEffect(False); play(e, 5); r = e.drawings()[1][3]; self.assertTrue(np.all(r[:, 2] == 1.0)); play(e, 40); self.assertTrue(np.all(e.drawings()[1][3][:, 3] == e.grid_mat[3]))


def mock_engine(speed=1.0):
    ENGINE.State.fade_speed = speed; e = ENGINE.State(); flag = []
    return types.SimpleNamespace(state=e, _effect_flag=lambda a: flag.append(a), flag=flag, frames=0)


def launch(eng, value):
    ENGINE.Engine._start_screen_effect(eng, value)


def step(eng):
    ENGINE.Engine._screen_effect(eng); eng.frames += 1; eng.state.tick_fade()


class Engine(unittest.TestCase):
    def tearDown(self): ENGINE.State.fade_speed = 1.0

    def test_packet_values(self):
        for value, kind, inverse, morning, frames in ((3, 'tabi', False, False, 64), (0x83, 'tabi', True, False, 45), (5, 'lampe', False, False, 64), (0x85, 'lampe', False, True, 64), (6, 'riremito', False, False, 63), (0x86, 'riremito', False, False, 63)):
            eng = mock_engine(); launch(eng, value); ef = eng.state.screen_effect
            self.assertEqual((ef['genre'], ef['inverse'], ef['matin'], ef['images'], ef['duree'], ef['n']), (kind, inverse, morning, frames, frames, 0), hex(value)); self.assertEqual(eng.flag, [True])
        for value in (0, 1, 2, 4, 7, 0x84):
            eng = mock_engine(); launch(eng, value); self.assertIsNone(eng.state.screen_effect, hex(value)); self.assertEqual(eng.flag, [])        # 4 : debut de combat (autre effet, Engine._start_battle_effect)
        eng = mock_engine(); launch(eng, 5); launch(eng, 6); self.assertEqual(eng.state.screen_effect['genre'], 'lampe'); self.assertEqual(eng.flag, [True])              # un seul effet a la fois

    def test_flag_falls_back_after_duration(self):
        for value, frames in ((3, 64), (0x83, 45), (5, 64), (6, 63)):
            for speed in (1.0, 2.0, 4.0):
                eng = mock_engine(speed); launch(eng, value); d = PJ.fade_duration(frames, speed); self.assertEqual(eng.state.screen_effect['duree'], d); n = 0
                while eng.state.screen_effect is not None: self.assertEqual(eng.flag, [True]); step(eng); n += 1
                self.assertEqual(n, d, 'valeur %s x%g' % (hex(value), speed)); self.assertEqual(eng.flag, [True, False])
        self.assertFalse(mock_engine().state.battle_transition())                                                                    # (ce n'est pas la transition d'un combat)
        eng = mock_engine(); launch(eng, 3); self.assertFalse(eng.state.battle_transition()); self.assertIsNone(eng.state.effect)

    def test_immediate_black_for_lamp_and_riremito(self):
        for value, call in ((5, 63), (6, 62)):
            eng = mock_engine(); launch(eng, value); self.assertEqual(eng.state.fade['a'], 0.0); n = 0
            while eng.state.screen_effect is not None:
                step(eng); n += 1
                self.assertEqual(eng.state.fade['a'], 1.0 if n + 1 >= call else 0.0, (value, n))                                   # appel d'origine = n + 1 (le premier a l'image du paquet)
            self.assertEqual((eng.state.fade['a'], eng.state.fade['n'], eng.state.fade['col']), (1.0, 0, (0.0, 0.0, 0.0))); self.assertFalse(eng.state.fade_in_progress())          # opaque, noir, immediat ; il reste ainsi
            self.assertIsNone(eng.state.black_screen)

    def test_trip_departure_and_arrival(self):
        eng = mock_engine(); launch(eng, 3)
        for _ in range(63): step(eng); self.assertIsNone(eng.state.black_screen)
        step(eng); self.assertIsNone(eng.state.screen_effect); self.assertEqual(eng.state.black_screen, {'n': 0})                              # fin du depart : l'ecran reste noir
        for _ in range(100): step(eng)
        self.assertEqual(eng.state.black_screen['n'], 100); self.assertEqual(eng.state.fade['a'], 0.0)                                    # (le noir n'est pas un plan de fondu : l'interface reste dessinee)
        eng.state.fade['a'] = 0.5; launch(eng, 0x83)
        for n in range(1, 46):
            step(eng)
            if n == 1: self.assertEqual(eng.state.fade['n'], 0)
            if n == 2: self.assertEqual((eng.state.fade['n'], round(eng.state.fade['pas'], 6), eng.state.fade['fin']), (EF.FADE_IN - 1, round(-0.5 / 30, 6), 0.0))     # Fade.SetFadeIn(30) a l'appel 3 : de l'opacite courante a 0 (30 images, une deja ecoulee a la fin de cette image)
            if n < 44: self.assertIsNotNone(eng.state.black_screen, n)
            if n == 44: self.assertIsNone(eng.state.black_screen); self.assertIsNotNone(eng.state.screen_effect)                             # dernier appel (etat 4) : la scene reparait ; le drapeau retombe a l'image suivante
        self.assertIsNone(eng.state.screen_effect); self.assertEqual(eng.flag, [True, False, True, False])

    def test_entry_fade_from_transparent_plane(self):
        e = ENGINE.State(); e.current_fade_in(30); self.assertEqual((e.fade['a'], e.fade['n'], e.fade['pas']), (0.0, 30, -0.0))
        for _ in range(30): e.tick_fade()
        self.assertEqual((e.fade['a'], e.fade['n']), (0.0, 0)); self.assertFalse(e.fade_in_progress())

    def test_black_screen_guardrails(self):
        eng = mock_engine(); eng.state.black_screen = {'n': 0}
        for _ in range(ENGINE.BLACK_SCREEN_MAX): step(eng)
        self.assertIsNotNone(eng.state.black_screen); step(eng); self.assertIsNone(eng.state.black_screen)                                        # jamais d'arrivee : le jeu est rouvert au bout de 60 s
        for cond in ({'game_map': ENGINE.TITLE_MAP}, {'part': ENGINE.PART_INITIAL}):
            eng = mock_engine(); eng.state.black_screen = {'n': 0}
            for k, v in cond.items(): setattr(eng.state, k, v)
            step(eng); self.assertIsNone(eng.state.black_screen, cond)                                                                    # retour au titre : plus de noir

    def test_state_stored_before_fix(self):
        e = ENGINE.State(); e.__dict__.pop('screen_effect', None); e.__dict__.pop('black_screen', None); self.assertIsNone(e.screen_effect); self.assertIsNone(e.black_screen)      # attributs de classe


if __name__ == '__main__':
    unittest.main(verbosity=2)
