"""Test de la retenue du dessin pendant un changement de carte (micro-images de mise en place du decor) et de l'absorption des blocages de chargement.

Le moteur envoie le decor de la nouvelle carte (paquet 0) une image AVANT sa camera (paquet 10) et les positions de ses personnages (paquet 13) ; le fondu d'entree demarre, lui, a l'image du chargement.
Sans retenue, une image de la scene d'avant (camera) / sans personnages se voyait sous les quelques % d'opacite restants. `State.loading` retient le dessin (noir + fondus seulement) et suspend le fondu d'entree
jusqu'a ce que la scene soit en place, sans changer la duree du fondu.

  1. regles pures (`State.apply`, `update_loading`, `tick_fade` sur des paquets fabriques) ;
  2. absorption des blocages (`Game._absorb_blocking`, faux objet) ;
  3. Windows : transitions du gestionnaire de fenetres (`transitions_dwm`, systeme simule) ;
  4. moteur d'origine (si --apk et --saves sont donnes) : teleportations vers des cartes de villes : la retenue dure au plus LOADING_MAX images, la 1re image montree est complete (camera envoyee, personnages
     places) et le fondu d'entree garde toute sa duree.

    python3 tools/test_loading.py [--apk "<dossier des APK patches>" --saves "<dossier des sauvegardes>" [--slot 4]]
Les sauvegardes ne sont ouvertes qu'en lecture : le moteur ecrit dans un dossier temporaire.
"""
import argparse, os, sys, tempfile, time, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.core import engine as ENGINE
from dq4_pc.window import game as F

ARGS = None
OUTPUT, ENTRY = 0x1000, 0                       # bit 12 du paquet 9 : fondu vers la couleur (sortie) ; sinon entree


def step(e, packets=()):
    """Un pas du moteur vu de l'etat (Engine.step) : image, paquets, fin de la retenue, fondus."""
    e.image += 1; e.apply(list(packets), lambda: 'carte_b'); e.update_loading(); e.tick_fade()


def do_load(duration=10, camera=True):
    """Paquets d'un chargement de carte : decor, fondu d'entree, un personnage cree (sa position arrive a l'image suivante)."""
    p = [(0, [], []), (9, [ENTRY | duration], []), (12, [0, 5], [])]
    if camera: p.append((10, [3], [0.0, 10.0, -20.0, 0.0, 0.0, 0.0]))
    return p


def covered_state(duration=10):
    """Etat apres un fondu au noir termine (ecran couvert), sur une carte quelconque."""
    e = ENGINE.State(); e.game_map = 'carte_a'
    step(e, [(9, [OUTPUT | duration], [])])
    for _ in range(duration + 2): step(e)
    assert e.fade['a'] == 1.0 and e.fade['n'] == 0
    return e


class Rules(unittest.TestCase):
    def setUp(self):
        self.speed = ENGINE.State.fade_speed; ENGINE.State.fade_speed = 1.0

    def tearDown(self): ENGINE.State.fade_speed = self.speed

    def test_held_until_the_scene_is_complete(self):
        e = covered_state(); d = 10
        step(e, do_load(d, camera=False))
        self.assertIsNotNone(e.loading, 'ecran couvert + chargement : dessin retenu')
        self.assertEqual((e.fade['a'], e.fade['n']), (1.0, d), 'le fondu d\'entree attend (il n\'a pas bouge)')
        step(e, [(10, [3], [0.0, 10.0, -20.0, 0.0, 0.0, 0.0])])
        self.assertIsNotNone(e.loading, 'la camera est la, mais le personnage cree n\'est pas place')
        step(e, [(13, [0x2000], [1.0, 0.0, 2.0])])
        self.assertIsNone(e.loading, 'camera recue, personnage place : scene en place')
        self.assertAlmostEqual(e.fade['a'], 1.0 - 1.0 / d, 6, 'le fondu d\'entree demarre a cette image')

    def test_fade_duration_does_not_change(self):
        d = 12; e = covered_state(d)
        step(e, do_load(d)); waiting = 0
        while e.loading is not None: waiting += 1; step(e, [(13, [0x2000], [1.0, 0.0, 2.0])] if waiting == 1 else [])
        n = 1                                                          # (l'image qui leve la retenue fait deja le 1er pas du fondu)
        while e.fade['n'] >= 1: step(e); n += 1
        self.assertEqual(n, d, 'le fondu d\'entree du jeu garde ses %d images apres la retenue' % d)
        self.assertEqual(e.fade['a'], 0.0)

    def test_camera_and_characters_in_same_packets(self):
        e = covered_state()
        step(e, do_load() + [(13, [0x2000], [1.0, 0.0, 2.0])])
        self.assertIsNotNone(e.loading, 'au moins une image de retenue (CHARGEMENT_MIN)')
        step(e)
        self.assertIsNone(e.loading)

    def test_guardrail(self):
        e = covered_state(); step(e, do_load(camera=False)); n = 0
        while e.loading is not None and n < 50: step(e); n += 1
        self.assertIsNone(e.loading, 'la retenue ne bloque jamais')
        self.assertLessEqual(n, ENGINE.LOADING_MAX, 'images retenues (celle du chargement comprise) au plus CHARGEMENT_MAX')

    def test_character_never_placed(self):
        e = covered_state(); step(e, do_load()); n = 0
        while e.loading is not None and n < 50: step(e); n += 1
        self.assertLessEqual(n, ENGINE.LOADING_PLACEMENT, 'attente des positions bornee a %d images' % ENGINE.LOADING_PLACEMENT)

    def test_hidden_character_not_awaited(self):
        e = covered_state(); step(e, do_load() + [(14, [0, 0], [])]); step(e)
        self.assertIsNone(e.loading, 'un personnage cache n\'a pas besoin de position')

    def test_screen_not_covered(self):
        e = ENGINE.State(); e.game_map = 'carte_a'
        step(e, [(0, [], [])])
        self.assertIsNone(e.loading, 'sans fondu, comportement d\'origine')
        e = ENGINE.State(); step(e, [(9, [OUTPUT | 10], [])]); step(e); step(e)
        self.assertLess(e.fade['a'], 0.9)
        step(e, [(0, [], [])])
        self.assertIsNone(e.loading, 'fondu au noir en cours mais pas encore couvrant')

    def test_immediate_entry_fade_without_prior_fade(self):
        e = ENGINE.State(); step(e, [(0, [], []), (9, [ENTRY | 1], [])])
        self.assertIsNone(e.loading, 'fondu d\'une image : rien a retenir (l\'ecran n\'est pas couvert)')

    def test_entry_fade_with_loading(self):
        e = ENGINE.State(); step(e, [(0, [], []), (9, [ENTRY | 10], [])])
        self.assertIsNotNone(e.loading, 'le fondu d\'entree repart de l\'opacite 1 : l\'ecran est couvert')

    def test_world_map_waits_for_its_tiles(self):
        e = covered_state(); e.part = ENGINE.PART_FIELD; e.field = None
        step(e, do_load()); step(e, [(13, [0x2000], [1.0, 0.0, 2.0])])
        self.assertIsNotNone(e.loading, 'carte du monde : on attend les tuiles (paquet 28)')
        e.field = {'x0': 0, 'y0': 0, 'cols': 1, 'tuiles': [0], 'cam': None}; step(e)
        self.assertIsNone(e.loading)

    def test_two_loads_in_a_row(self):
        e = covered_state(); step(e, do_load()); step(e, [(0, [], []), (9, [ENTRY | 10], [])])
        self.assertIsNotNone(e.loading, 'mort puis eglise : la retenue repart avec le nouveau chargement')
        self.assertEqual(e.loading['n'], 0)
        for _ in range(ENGINE.LOADING_MAX + 1): step(e)
        self.assertIsNone(e.loading)

    def test_state_loaded_from_old_save(self):
        e = ENGINE.State(); d = dict(e.__dict__); d.pop('loading')
        e2 = ENGINE.State.__new__(ENGINE.State); e2.__setstate__(d)
        self.assertIsNone(e2.loading)


class Absorption(unittest.TestCase):
    def fake(self, maps=1):
        return types.SimpleNamespace(engine=types.SimpleNamespace(state=types.SimpleNamespace(loaded_maps=maps)), t_loop=5.0)

    def test_long_frame_after_loading(self):
        j = self.fake()
        F.Game._absorb_blocking(j, time.perf_counter() - 0.3)
        self.assertIsNone(j.t_loop, 'un blocage de 300 ms n\'est pas rattrape par le moteur')

    def test_normal_frame(self):
        j = self.fake()
        for _ in range(5): F.Game._absorb_blocking(j, time.perf_counter() - 0.004)
        self.assertEqual(j.t_loop, 5.0)

    def test_slow_machine(self):
        j = self.fake()
        for _ in range(3): F.Game._absorb_blocking(j, time.perf_counter() - 0.10)
        self.assertEqual(j.t_loop, 5.0, 'des images de 100 ms (machine lente) ne sont pas des blocages : le jeu ne se fige pas')

    def test_only_the_first_frames_of_a_map(self):
        j = self.fake()
        for _ in range(3): F.Game._absorb_blocking(j, time.perf_counter())
        F.Game._absorb_blocking(j, time.perf_counter() - 0.3)
        self.assertEqual(j.t_loop, 5.0, 'plus de 3 images apres le chargement : un ralentissement ordinaire reste soumis au rattrapage normal')
        j.engine.state.loaded_maps = 2
        F.Game._absorb_blocking(j, time.perf_counter() - 0.3)
        self.assertIsNone(j.t_loop, 'nouvelle carte : le compte repart')


class Interpolation(unittest.TestCase):
    """L'image qui leve la retenue d'un chargement n'est pas interpolee depuis l'etat de la retenue (camera d'avant) : Game._interpoler sur un faux objet."""
    def fake(self, retained_before, retained_after):
        e = types.SimpleNamespace(part=0xc, game_map='x', loading={'n': 1} if retained_after else None, sprites={}, cam_pos=(0.0, 10.0, -20.0), cam_target=(0.0, 0.0, 0.0), field=None)
        pr = dict(cle=(0xc, 'x'), ret=retained_before, sp={}, cam_pos=(0.5, 10.0, -20.0), cam_cible=(0.0, 0.0, 0.0), champ=None)
        j = types.SimpleNamespace(prev=pr, alpha=0.5, engine=types.SimpleNamespace(state=e)); j._interpolate_camera = types.MethodType(F.Game._interpolate_camera, j); return j

    def test_no_interpolation_on_lift(self):
        j = self.fake(True, False)
        self.assertEqual(F.Game._interpolate(j), [])
        self.assertEqual(j.engine.state.cam_pos, (0.0, 10.0, -20.0))

    def test_ordinary_interpolation(self):
        j = self.fake(False, False)
        saved = F.Game._interpolate(j)
        self.assertTrue(saved); self.assertAlmostEqual(j.engine.state.cam_pos[0], 0.25, places=3, msg='camera a mi-chemin entre les deux pas')


class DWM(unittest.TestCase):
    """Windows : animation d'ouverture de la fenetre coupee pendant le lancement (fenetre.transitions_dwm). Ici sans Windows : le systeme est simule."""
    def with_dwm(self, dwm, window):
        import ctypes
        old = sys.platform; sys.platform = 'win32'; ctypes.windll = types.SimpleNamespace(dwmapi=dwm)
        try: return F.transitions_dwm(window, False), F.transitions_dwm(window, True)
        finally: sys.platform = old; del ctypes.windll

    def test_non_windows_nothing_changes(self):
        self.assertFalse(F.transitions_dwm(types.SimpleNamespace(_hwnd=123), False))

    def test_windows_call(self):
        calls = []
        class Dwm:
            def DwmSetWindowAttribute(self, h, attr, ref, size_value): calls.append((h.value, attr, ref._obj.value, size_value)); return 0
        self.assertEqual(self.with_dwm(Dwm(), types.SimpleNamespace(_hwnd=0x1234)), (True, True))
        self.assertEqual(calls, [(0x1234, 3, 1, 4), (0x1234, 3, 0, 4)], 'DWMWA_TRANSITIONS_FORCEDISABLED : 1 pour couper, 0 pour remettre')

    def test_errors_without_consequence(self):
        class Broken:
            def DwmSetWindowAttribute(self, *a): raise OSError('dwmapi absent')
        class Refused:
            def DwmSetWindowAttribute(self, *a): return 0x80070057
        self.assertEqual(self.with_dwm(Broken(), types.SimpleNamespace(_hwnd=1)), (False, False))
        self.assertEqual(self.with_dwm(Refused(), types.SimpleNamespace(_hwnd=1)), (False, False))
        self.assertEqual(self.with_dwm(Refused(), types.SimpleNamespace()), (False, False), 'pas de poignee de fenetre')


@unittest.skipIf(ARGS is None and '--apk' not in sys.argv, 'moteur d\'origine : --apk et --saves requis')
class Engine(unittest.TestCase):
    def test_teleports(self):
        eng = ENGINE.Engine(ARGS.apk, ARGS.saves, tempfile.mkdtemp(prefix='sv_test_chg_'))
        eng.load_save(ARGS.slot)
        for _ in range(100): eng.step(0, 0)
        ENGINE.State.fade_speed = 1.0; seen = 0
        for name_str in ('caf1', 'cbf1', 'cdf1', 'mak1f1', 'maout'):
            before = eng.state.loaded_maps; cam0 = eng.state.cam_pos
            eng.start_town(name_str); k = None; trace = []
            for i in range(40):
                eng.step(0, 0); e = eng.state
                if k is None and e.loaded_maps > before: k = i
                if k is not None: trace.append((i - k, e.loading is not None, e.cam_pos, [s['pos'] for s in e.sprites.values() if s.get('vis', True)], e.fade['a'], e.fade['n']))
            self.assertIsNotNone(k, name_str + ' : carte chargee')
            seen += 1
            retained_list = [t for t in trace if t[1]]
            self.assertTrue(retained_list, name_str + ' : le chargement a ete retenu')
            self.assertLessEqual(len(retained_list), ENGINE.LOADING_MAX, name_str)
            is_first = next(t for t in trace if not t[1])
            self.assertIsNotNone(is_first[2], name_str + ' : camera envoyee a la 1re image montree')
            if seen == 1: self.assertNotEqual(is_first[2], cam0, name_str + ' : ce n\'est plus la camera de la carte d\'avant (carte du monde ; deux villes peuvent avoir la meme camera de depart)')
            self.assertTrue(all(p is not None for p in is_first[3]), name_str + ' : personnages places a la 1re image montree')
            for t in retained_list: self.assertEqual(t[4], 1.0, name_str + ' : ecran couvert pendant la retenue')
        self.assertEqual(seen, 5)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apk'); ap.add_argument('--saves'); ap.add_argument('--slot', type=int, default=4)
    ARGS, remainder = ap.parse_known_args()
    if not (ARGS.apk and ARGS.saves): ARGS = None
    unittest.main(argv=[sys.argv[0]] + remainder, verbosity=2)
