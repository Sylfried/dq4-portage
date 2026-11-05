"""Test de la vitesse de combat (Manuel / Normal / Rapide / Tres rapide) : reglage, cycle, horloge du moteur, independance de l'accelerateur, musique et bruitages non accelerees, bouton de l'ecran de combat.
Sans fenetre ni moteur (faux objets) ; la partie « moteur reel » est facultative : DQ_APK=<dossier des APK> DQ_SAVES=<dossier des sauvegardes> la lance (rejeu d'un combat a 1, 2 et 3 pas par image).

    python3 tools/test_battle_speed.py       (Linux sans ecran : pyglet en mode « headless »)
"""
import json, math, os, random, re, sys, tempfile, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
from dq4_pc.persistence import settings as RG
from dq4_pc.battle import battle_speed as VC

try:
    import pyglet
    if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
    from dq4_pc.window import game as F
    from dq4_pc.menus import hud_mobile as HM
    from dq4_pc.core import engine as ENGINE
    from dq4_pc.battle import battle_effect as EC
except Exception as ex:                                                     # (pas de pyglet / moteur ici : les tests qui en ont besoin sont ignores)
    F = HM = ENGINE = None; IMPORT_ERROR = ex

STEP = VC.ENGINE_STEP


def load(content):
    f = os.path.join(tempfile.mkdtemp(prefix='rg_test_'), 'settings.json')
    with open(f, 'w', encoding='utf-8') as fh: json.dump(content, fh)
    return RG.Settings(f), f


class Setting(unittest.TestCase):
    def test_default_normal(self):
        r = RG.Settings(None); self.assertEqual(r['vitesse_combat'], 1.0); self.assertEqual(RG.DEFAULT['vitesse_combat'], 1.0)
        self.assertEqual(RG.BATTLE_SPEEDS, (0.0, 1.0, 2.0, 3.0))

    def test_labels_never_x(self):
        self.assertEqual([RG.BATTLE_SPEED_NAMES[v] for v in RG.BATTLE_SPEEDS], ['Manuel', 'Normal', 'Rapide', 'Très rapide'])
        self.assertFalse(any(re.search(r'\bx\d', n) for n in RG.BATTLE_SPEED_NAMES.values()))

    def test_validation(self):
        for raw_value, expected in ((0, 0.0), (1, 1.0), (2, 2.0), (3, 3.0), (1.0, 1.0), (2.4, 2.0), (1.5, 2.0), (2.5, 3.0), (0.4, 0.0), (0.5, 1.0), (-4, 0.0), (4, 3.0), (99, 3.0), (float('inf'), 3.0), (float('-inf'), 0.0),
                              (float('nan'), 1.0), ('2', 1.0), ('x', 1.0), (None, 1.0), (True, 1.0), (False, 1.0), ([2], 1.0), ({'a': 2}, 1.0)):
            self.assertEqual(RG.battle_notch(raw_value), expected, repr(raw_value))
            r, _ = load({'vitesse_combat': raw_value}); self.assertEqual(r['vitesse_combat'], expected, 'fichier : %r' % (raw_value,))
        r, _ = load({'son': False}); self.assertEqual(r['vitesse_combat'], 1.0)                      # absent : Normal

    def test_cycle(self):
        v = 1.0; seen = []
        for _ in range(9): v = RG.next_battle_speed(v); seen.append(v)
        self.assertEqual(seen, [2.0, 3.0, 0.0, 1.0, 2.0, 3.0, 0.0, 1.0, 2.0])                         # Normal -> Rapide -> Très rapide -> Manuel -> Normal
        self.assertEqual(RG.next_battle_speed('x'), 2.0); self.assertEqual(RG.next_battle_speed(None), 2.0)    # valeur invalide : lue comme Normal

    def test_storage(self):
        r, f = load({}); r['vitesse_combat'] = 3.0; r.store()
        self.assertEqual(RG.Settings(f)['vitesse_combat'], 3.0)
        with open(f, encoding='utf-8') as fh: self.assertEqual(json.load(fh)['vitesse_combat'], 3.0)

    def test_default_key_free(self):
        d = RG.DEFAULT_KEYS['vit_combat']; self.assertEqual(d, ['V', None])
        for a, ts in RG.DEFAULT_KEYS.items():
            if a != 'vit_combat': self.assertNotIn('V', ts, a)                                      # aucun conflit avec les touches existantes
        self.assertNotIn('V', RG.RESERVED)
        self.assertIn('vit_combat', dict(RG.ACTIONS)); self.assertEqual(dict(RG.ACTIONS)['vit_combat'], 'Changer la vitesse en combat')
        r = RG.Settings(None); self.assertEqual(r['touches']['vit_combat'], ['V', None]); self.assertEqual(r.action_of(RG.key_symbol('V')), 'vit_combat')

    def test_old_file_takes_default_key(self):
        r, _ = load({'touches_v': 4, 'touches': {'carte': ['M', None]}}); self.assertEqual(r['touches']['vit_combat'], ['V', None])
        r, _ = load({'touches_v': 4, 'touches': {'carte': ['V', None]}})                            # une autre action a deja pris V : la nouvelle action n'a pas de touche (et la sienne est gardee)
        self.assertEqual(r['touches']['vit_combat'], [None, None]); self.assertEqual(r['touches']['carte'], ['V', None])

    def test_interface_classification(self):
        self.assertNotIn('vitesse_combat', RG.INTERFACE_KEYS)                                         # un reglage de jeu, pas d'interface ; le bouton a sa propre interface (RG.SPEED_TARGET : bouton_vitesse, _taille, _pos)


class Factor(unittest.TestCase):
    def test_outside_battle_nothing(self):
        for v in (0.0, 1.0, 2.0, 3.0): self.assertIsNone(VC.factor(v, False))

    def test_battle(self):
        self.assertEqual([VC.factor(v, True) for v in (0.0, 1.0, 2.0, 3.0)], [1.0, 1.0, 2.0, 3.0])            # Manuel et Normal : l'horloge du jeu

    def test_absurd_values(self):
        self.assertEqual(VC.factor(9, True), 3.0); self.assertEqual(VC.factor(0.2, True), 1.0)
        for v in (None, 'x', float('nan')): self.assertEqual(VC.factor(v, True), 1.0)


class MessageScrolling(unittest.TestCase):
    """La « Vitesse de combat » fixe aussi OptionStatus.battleSpeed : 4 (a la main) en Manuel, 0 (12 images, la plus courte) sinon (#45)."""
    def test_imposed_code(self):
        self.assertEqual([RG.scroll_code(v) for v in (0.0, 1.0, 2.0, 3.0)], [4, 0, 0, 0])
        self.assertEqual(RG.scroll_code('x'), 0); self.assertEqual(RG.scroll_code(None), 0)             # valeur invalide : Normal

    def test_game_changes_message_speed(self):
        self.assertEqual(RG.speed_after_game_code(4, 2.0), 0.0)                                              # Manuel choisi dans le jeu
        self.assertEqual(RG.speed_after_game_code(0, 0.0), 1.0); self.assertEqual(RG.speed_after_game_code(3, 0.0), 1.0)      # autre valeur : on sort du Manuel (Normal)
        self.assertEqual(RG.speed_after_game_code(0, 3.0), 3.0); self.assertEqual(RG.speed_after_game_code(2, 2.0), 2.0)      # hors Manuel : le cran est garde
        self.assertEqual(RG.speed_after_game_code('x', 2.0), 2.0)

    def test_old_setting_messages_in_battle(self):
        r, _ = load({'defilement_force': True, 'defilement_combat': 4, 'vitesse_combat': 3.0}); self.assertEqual(r['vitesse_combat'], 0.0)           # ancien « Manuel » : devient la vitesse Manuel
        for old in (0, 2, 3):                                                                              # autres crans : plus d'equivalent, la vitesse de combat enregistree reste
            r, _ = load({'defilement_force': True, 'defilement_combat': old, 'vitesse_combat': 2.0}); self.assertEqual(r['vitesse_combat'], 2.0)
        r, _ = load({'defilement_force': False, 'defilement_combat': 4, 'vitesse_combat': 2.0}); self.assertEqual(r['vitesse_combat'], 2.0)       # non impose : la sauvegarde du jeu decidait, pas le joueur
        r, _ = load({'defilement_auto': False, 'defilement_force': True}); self.assertEqual(r['vitesse_combat'], 0.0)      # tout ancien « Defilement automatique : non » impose
        r, _ = load({'defilement_auto': False}); self.assertEqual(r['vitesse_combat'], 1.0)                 # (rien n'etait impose : la sauvegarde du jeu decidait)
        r, _ = load({'defilement_force': True, 'defilement_combat': 4}); r.store()
        with open(r.path, encoding='utf-8') as fh: d = json.load(fh)
        self.assertEqual(d['vitesse_combat'], 0.0); self.assertNotIn('defilement_force', d); self.assertNotIn('defilement_combat', d)           # les anciennes cles disparaissent du fichier


class Clock(unittest.TestCase):
    @staticmethod
    def simulate(f, seconds=10.0, cost=0.0, fps=60.0, waiting=None, budget=VC.STEP_BUDGET):
        """Rejoue `seconds` d'images affichees a `fps` avec un moteur factice de `cost` secondes par pas -> (nombre de pas, temps de pas maximal dans une image, nombre d'images coupees)."""
        h = [0.0]; acc = 0.0; step = [0]; max_img = 0.0; cuts = 0
        def perform():
            step[0] += 1; h[0] += cost
            return not (waiting and waiting(step[0]))
        for _ in range(int(seconds * fps)):
            t0 = h[0]; h[0] += 0.0                                                  # (le temps d'affichage n'entre pas dans le budget des pas)
            acc, n, cut = VC.advance_time(acc, 1.0 / fps, f, perform, lambda: h[0], STEP, budget)
            max_img = max(max_img, h[0] - t0); cuts += cut; h[0] += 1.0 / fps
        return step[0], max_img, cuts

    def test_step_count_per_second(self):
        for f in (1.0, 2.0, 3.0):
            n, _, _ = self.simulate(f); self.assertAlmostEqual(n / 10.0, 30.0 * f, delta=0.6, msg='x%g' % f)       # 30, 60, 90 pas par seconde reelle (60 Hz)

    def test_other_display_rates(self):
        for fps in (30.0, 75.0, 144.0, 240.0):
            for f in (1.0, 2.0, 3.0):
                n, _, _ = self.simulate(f, fps=fps); self.assertAlmostEqual(n / 10.0, 30.0 * f, delta=0.04 * 30.0 * f + 0.6, msg='x%g a %g Hz' % (f, fps))

    def test_compute_budget_bounded(self):
        """Pas du moteur plus couteux que ce que le PC supporte : le temps de calcul d'une image reste borne (budget + un pas), le jeu ralentit au lieu de geler l'affichage."""
        n, max_img, cuts = self.simulate(3.0, cost=0.012); self.assertAlmostEqual(n / 10.0, 90.0, delta=0.6); self.assertEqual(cuts, 0)         # pas bon marche (12 ms) : cadence complete, rien n'est coupe
        n, max_img, cuts = self.simulate(3.0, cost=0.035)                                                                                        # pas lourd (35 ms) : un seul pas par image, donc 60 pas par seconde (x2 au lieu de x3)
        self.assertLessEqual(max_img, VC.STEP_BUDGET + 0.035 + 1e-9); self.assertAlmostEqual(n / 10.0, 60.0, delta=0.6); self.assertGreater(cuts, 0)
        n, max_img, cuts = self.simulate(2.0, cost=0.035); self.assertAlmostEqual(n / 10.0, 60.0, delta=0.6)                                     # x2 demande un pas par image a 60 Hz : tient meme avec un pas lourd
        for f in (2.0, 3.0):
            for cost in (0.012, 0.02, 0.035, 0.08):
                n, max_img, _ = self.simulate(f, cost=cost); self.assertLessEqual(max_img, VC.STEP_BUDGET + cost + 1e-9, 'x%g %g s' % (f, cost)); self.assertGreaterEqual(n / 10.0, 59.4, 'x%g %g s' % (f, cost))     # jamais sous x2 par image affichee

    def test_budget_no_effect_at_normal_speed(self):
        n, _, cuts = self.simulate(1.0, cost=0.05); self.assertEqual(cuts, 0); self.assertAlmostEqual(n / 10.0, 30.0, delta=0.6)      # (a x1 le budget ne s'applique pas : comme avant)

    def test_engine_waits_for_player(self):
        """Quand un pas ouvre un menu (do_step renvoie False) on n'enchaine pas d'autres pas dans la meme image, et le reste d'horloge est oublie."""
        acc, n, cut = VC.advance_time(0.0, 0.05, 3.0, lambda: False, lambda: 0.0)       # 0,15 s de moteur a faire (4 pas) : un seul est fait
        self.assertEqual((n, acc, cut), (1, 0.0, False))
        tally = [0]
        def perform(): tally[0] += 1; return tally[0] != 2                            # le 2e pas ouvre un menu
        acc, n, _ = VC.advance_time(0.0, 0.05, 3.0, perform, lambda: 0.0); self.assertEqual((n, acc), (2, 0.0))

    def test_identical_to_old_loop(self):
        """La boucle deplacee dans VC.avancer fait exactement ce que faisait Game._boucle (marche acceleree comprise)."""
        def old_version(acc, dt, f, perform, clock, budget):
            acc += min(dt * f, 3 * STEP * max(1.0, f)); n = 0; nmax = 3 * max(1, math.ceil(f)); cut = False; t0 = clock()
            while acc >= STEP * 0.85 and n < nmax:
                perform(); acc -= STEP; n += 1
                if f > 1.0 and clock() - t0 > budget: cut = True; break
            if n == nmax or cut: acc = 0.0
            return acc, n, cut
        rnd = random.Random(7)
        for f in (0.25, 1.0, 1.5, 2.0, 3.0, 4.0, 8.0):
            for cost in (0.0, 0.004, 0.02):
                a1 = a2 = 0.0; h1 = [0.0]; h2 = [0.0]
                for _ in range(400):
                    dt = rnd.choice((1 / 60.0, 1 / 60.0, 1 / 30.0, 1 / 144.0, 0.1, 0.4))
                    def f1(): h1[0] += cost
                    def f2(): h2[0] += cost
                    r1 = old_version(a1, dt, f, f1, lambda: h1[0], VC.STEP_BUDGET); r2 = VC.advance_time(a2, dt, f, f2, lambda: h2[0], STEP, VC.STEP_BUDGET)
                    self.assertEqual(r1[1:], r2[1:]); self.assertAlmostEqual(r1[0], r2[0], places=12); a1, a2 = r1[0], r2[0]; h1[0] += dt; h2[0] += dt


class Sounds(unittest.TestCase):
    def test_no_duplicate_in_frame(self):
        already = set()
        step1 = VC.sounds_to_play([(35, 412), (37, 30)], already); step2 = VC.sounds_to_play([(35, 412), (35, 402)], already); step3 = VC.sounds_to_play([(35, 402), (35, 412)], already)
        self.assertEqual(step1, [(35, 412), (37, 30)]); self.assertEqual(step2, [(35, 402)]); self.assertEqual(step3, [])
        self.assertEqual(VC.sounds_to_play([(35, 412)], set()), [(35, 412)])                       # image suivante : de nouveau joue

    def test_a_frame_filters_only_sfx(self):
        already = set(); self.assertEqual(VC.sounds_to_play([(37, 30), (37, 30), (36, 412), (36, 412)], already), [(37, 30), (37, 30), (36, 412), (36, 412)])     # musique et arrets : intacts

    def test_start_stop_start(self):
        already = set(); self.assertEqual(VC.sounds_to_play([(35, 311), (36, 311), (35, 311)], already), [(35, 311), (36, 311), (35, 311)])                    # un arret libere le bruitage

    def test_without_filter_everything_passes(self):
        evts = [(35, 412), (35, 412), (37, 5)]; self.assertEqual(VC.sounds_to_play(evts, None), evts)

    def test_playback_speed_and_duration_unchanged(self):
        """Une image affichee a x3 envoie plusieurs pas : le bruitage est lance une seule fois, avec la duree de son fichier (aucune notion de vitesse dans le module son) ; la musique garde son horloge reelle."""
        try:
            sys.modules.setdefault('pyglet', None)
            from dq4_pc import sound as SOUND
        except Exception as ex: self.skipTest('sound.py non importable ici (%r)' % (ex,))
        launched = []
        class Player:
            def __init__(self): self.volume = 1.0; self.playing = False
            def queue(self, src): pass
            def play(self): self.playing = True; launched.append(self)
            def pause(self): self.playing = False
            def delete(self): self.playing = False
        s = SOUND.Sound('inexistant.apk', '/tmp', log=lambda *a: None)
        s.ok = True; s.ogg = True; s.media = types.SimpleNamespace(Player=Player, Source=object); s.AudioFormat = lambda **kw: kw; s.AudioData = None; SOUND.LoopSource = lambda *a: None
        s.dec['SE0412'] = dict(pcm=__import__('numpy').zeros((11025, 1), 'int16'), frequence=22050, debut=0, fin=0, volume=0.5, boucle=False)       # 0,5 s
        import time
        for f in (1.0, 3.0):
            launched.clear(); s.sfx.clear(); already = set() if f > 1.0 else None
            t0 = time.time()
            for _ in range(3): s.events(VC.sounds_to_play([(35, 412)], already))                # trois pas du moteur dans la meme image affichee
            self.assertEqual(len(launched), 1 if f > 1.0 else 3, 'x%g' % f)
            for x in s.sfx: self.assertAlmostEqual(x.end - t0, 0.5 + 0.5, delta=0.1)          # duree du fichier (0,5 s) + marge de liberation : la meme a toutes les vitesses
        with open(SOUND.__file__, encoding='utf-8') as fh: src = fh.read()
        for word in ('vitesse_combat', 'vitesse_marche', 'vitesse_accel', 'import vitesse_combat'): self.assertNotIn(word, src, word)         # le module son ne connait pas l'horloge acceleree


@unittest.skipIf(F is None, 'window.py non importable ici')
class AcceleratorIndependence(unittest.TestCase):
    @staticmethod
    def fake(part, battle_speed=1.0, walk=1.0, accel=1.0, accel_held=False, direction=True, effect=None, waiting=None, menu=None, msg=False, feed=False):
        j = types.SimpleNamespace(reg={'vitesse_combat': battle_speed, 'vitesse_marche': walk, 'vitesse_accel': accel})
        state = ENGINE.State(); state.part = part; state.effect = effect; state.load_wait = waiting           # (l'Etat reel : battle_transition() decide de l'horloge de la cascade et des fondus)
        j.engine = types.SimpleNamespace(state=state, msg_visible=msg, active_menu=lambda: menu, flags=lambda: 0x28, ui=types.SimpleNamespace(msg={'feed': feed}))
        j.pad = lambda: ENGINE.UP if direction else 0
        j._held = lambda a: accel_held and a == 'accel'; j.hud = types.SimpleNamespace(dpad_run=lambda: False); j.pause = types.SimpleNamespace(opened=False)
        for name_str in ('_battle_clock', '_wait_for_player'): setattr(j, name_str, types.MethodType(getattr(F.Game, name_str), j))
        j.factor = lambda: F.Game._speed_factor(j)
        return j

    def test_accelerator_does_not_accelerate_battle(self):
        for v in (0.0, 1.0, 2.0, 3.0):
            for walk, accel, held_name in ((1.0, 1.0, False), (4.0, 2.0, True), (4.0, 2.0, False), (1.0, 2.0, True), (3.0, 1.5, True)):
                j = self.fake(ENGINE.PART_BATTLE, v, walk, accel, held_name); self.assertEqual(j.factor(), max(1.0, v), 'combat x%g, marche x%g, accelerateur x%g tenu=%s' % (v, walk, accel, held_name))      # ni cumule ni applique

    def test_outside_battle_walk_keeps_its_settings(self):
        for part in (ENGINE.PART_TOWN, ENGINE.PART_FIELD):
            self.assertEqual(self.fake(part, 3.0, 1.0, 1.0).factor(), 1.0)                                   # la vitesse des combats n'agit pas sur le terrain
            self.assertEqual(self.fake(part, 3.0, 2.0, 1.5).factor(), 2.0)                                   # marche x2
            self.assertEqual(self.fake(part, 1.0, 2.0, 1.5, accel_held=True).factor(), 3.0)                 # marche x2 x accelerateur x1,5 : comme avant
            self.assertEqual(self.fake(part, 1.0, 4.0, 2.0, accel_held=True).factor(), 8.0)
            self.assertEqual(self.fake(part, 3.0, 2.0, 1.5, accel_held=True, direction=False).factor(), 1.0)  # (arret : vitesse normale)

    def test_cascade_on_game_clock_then_battle_speed_from_black_screen(self):
        """#47 : la cascade d'entree en combat est a l'horloge du jeu (x1 quelle que soit la vitesse de combat, de marche ou l'accelerateur ; sa duree suit « Vitesse de transition » : voir tools/test_battle_transition.py) ;
        des qu'elle est finie, l'ecran noir qui attend la scene (puis le fondu d'arrivee et le message « X apparait ») va a la vitesse de combat."""
        for v in (0.0, 1.0, 2.0, 3.0):
            self.assertEqual(self.fake(ENGINE.PART_FIELD, v, 4.0, 2.0, True, effect={'n': 3}).factor(), 1.0)             # effet qui brise l'ecran
            self.assertEqual(self.fake(ENGINE.PART_FIELD, v, 4.0, 2.0, True, waiting={'base': 0, 'n': 3}).factor(), max(1.0, v))      # ecran noir avant la scene du combat

    def test_input_waits_keep_chosen_speed(self):
        """Les monstres suivent la vitesse de combat meme pendant les menus : l'horloge reste celle du reglage ; seule la lecture des touches est a cadence normale (pas muets : test suivant)."""
        self.assertEqual(self.fake(ENGINE.PART_BATTLE, 3.0, menu=13).factor(), 3.0)                              # menu de commandes, de cible...
        self.assertEqual(self.fake(ENGINE.PART_BATTLE, 3.0, msg=True, feed=True).factor(), 3.0)                  # message qui attend une touche (curseur ▼)
        self.assertEqual(self.fake(ENGINE.PART_BATTLE, 3.0, msg=True, feed=False).factor(), 3.0)                 # message qui defile seul
        self.assertEqual(self.fake(ENGINE.PART_BATTLE, 2.0).factor(), 2.0); self.assertEqual(self.fake(ENGINE.PART_BATTLE, 0.0, menu=13).factor(), 1.0)      # Manuel : l'horloge du jeu

    def test_not_muted_during_waits(self):
        """Moteur en attente du joueur : un seul pas sur f lit les touches (un par 1 / 30 s reelles), les autres sont muets ; sinon tous les pas sont ordinaires."""
        from unittest import mock
        is_waiting = [True]; calls = []; h = [100.0]
        j = types.SimpleNamespace(_t_real_step=0.0, _wait_for_player=lambda: is_waiting[0], _step=lambda mute=False: calls.append(mute), engine=types.SimpleNamespace(state=ENGINE.State()))
        with mock.patch.object(F.time, 'perf_counter', lambda: h[0]):
            for _ in range(3): self.assertTrue(F.Game._do_battle_step(j))                                      # 1er pas : lit les touches ; les 2 suivants (meme image affichee) : muets
            self.assertEqual(calls, [False, True, True]); h[0] += STEP; F.Game._do_battle_step(j); self.assertEqual(calls[-1], False)       # 1 / 30 s plus tard : un pas qui lit les touches
            is_waiting[0] = False; calls.clear()
            for _ in range(3): F.Game._do_battle_step(j)
            self.assertEqual(calls, [False, False, False])                                                     # le moteur ne tient pas le joueur : tous les pas sont ordinaires

    def test_can_be_changed_without_leaving_battle(self):
        """Touche ou bouton : le reglage change, est enregistre, le defilement des messages suit (Manuel : a la main) ; aucun message a l'ecran (retire depuis #267 : le faux jeu n'a pas de `toast`)."""
        r = RG.Settings(None); saved = []; r.store = lambda: saved.append(r['vitesse_combat']); imposed = []
        vis = [()]
        j = types.SimpleNamespace(reg=r, hud=types.SimpleNamespace(visible_ones=lambda: vis[0]), apply_scroll=lambda: imposed.append(RG.scroll_code(r['vitesse_combat'])))
        for expected in (2.0, 3.0, 0.0, 1.0, 2.0): F.Game.change_battle_speed(j); self.assertEqual(r['vitesse_combat'], expected)
        self.assertEqual(saved, [2.0, 3.0, 0.0, 1.0, 2.0]); self.assertEqual(imposed, [0, 0, 4, 0, 0])
        vis[0] = (HM.BATTLE,); F.Game.change_battle_speed(j); F.Game.change_battle_speed(j, 'bouton')                      # (bouton a l'ecran ou non : jamais de message)
        vis[0] = (); F.Game.change_battle_speed(j, 'bouton'); self.assertEqual(saved[-3:], [3.0, 0.0, 1.0])


@unittest.skipIf(F is None, 'window.py non importable ici')
class EngineClock(unittest.TestCase):
    """Tout ce que la visionneuse anime pendant un combat doit suivre les pas du moteur (moteur.images + alpha), pas l'horloge reelle : sinon, a x2 / x3, ils se desynchronisent des actions."""
    def test_battle_animations_without_real_clock(self):
        import inspect
        for item in (F.Game._draw_damage, F.Game._paint_fbx, F.Game._draw_effect, F.Game._draw_fade, F.Game._battle_meshes, EC.TilesEffect, ENGINE.State.tick_fade):
            src = inspect.getsource(item)
            self.assertIsNone(re.search(r'time\.(time|perf_counter|monotonic)\(', src), item.__name__)
        self.assertIn('engine.frames', inspect.getsource(F.Game._draw_damage)); self.assertIn('engine.frames', inspect.getsource(F.Game._paint_fbx))

    def test_only_real_clock_of_battle_ui_is_the_target_arrow(self):
        """ui_menu : la fleche de cible clignote en temps reel (BattleUpCursor, 0,7 s) : c'est une attente de saisie du joueur, qui n'est pas acceleree (la vitesse n'agit pas quand un menu a la saisie)."""
        src = _paths.source('ui_menu.py')
        self.assertEqual(sorted(set(re.findall(r'time\.(?:time|perf_counter|monotonic)\(\)', src))), ['time.monotonic()'])
        lines = [l.strip() for l in src.splitlines() if 'time.monotonic' in l]
        self.assertEqual(len(lines), 3)                                                                        # curseur de cible (2) et clignotement des lieux de la carte du monde (1)


@unittest.skipIf(HM is None, 'hud_mobile.py non importable ici')
class ScreenButton(unittest.TestCase):
    @staticmethod
    def fake(W=1280, H=720, buttons=True, part=None, effect=None, waiting=None, fade=None, pause=False, pos=None, flag=0x28, game_map=False):
        MOd = ENGINE or types.SimpleNamespace(PART_BATTLE=13)
        plan = lambda **k: dict(dict(a=0.0, fin=0.0, pas=0.0, n=0, col=(0, 0, 0), noir=0), **k)
        f = fade or {}
        state = types.SimpleNamespace(part=MOd.PART_BATTLE if part is None else part, effect=effect, load_wait=waiting, fade=plan(**f.get('devant', {})), background_fade=plan(**f.get('fond', {})))
        J = types.SimpleNamespace(width=W, height=H, reg={'boutons': True, 'bouton_vitesse': buttons, 'bouton_vitesse_taille': 1.0, 'bouton_vitesse_pos': pos or [], 'croix': True, 'boutons_taille': 1.0, 'croix_taille': 1.0, 'boutons_pos': {}, 'boutons_aimant': True},
                                  pause=types.SimpleNamespace(opened=pause), map_open=game_map, args=types.SimpleNamespace(cache='/inexistant'))
        J.engine = types.SimpleNamespace(state=state, flags=lambda: flag, dpad_size=lambda: 1)
        return J, HM.Buttons(J)

    def test_in_battle_only_the_speed_button(self):
        J, b = self.fake(); self.assertEqual(b.visible_ones(), (HM.BATTLE,))

    def test_on_the_field_not_the_speed_button(self):
        J, b = self.fake(part=12); vis = b.visible_ones(); self.assertNotIn(HM.BATTLE, vis); self.assertEqual(set(vis), {'carte', 'menu', 'discussion', HM.DPAD})
        J, b = self.fake(part=14); self.assertNotIn(HM.BATTLE, b.visible_ones())

    def test_mask_like_the_others(self):
        self.assertEqual(self.fake(buttons=False)[1].visible_ones(), ())                                               # « Afficher cette interface » = Non (celle du bouton de vitesse : « Combat : bouton de vitesse »)
        self.assertEqual(self.fake(pause=True)[1].visible_ones(), ())                                                  # menu Pause ouvert

    def test_not_during_black_screen_nor_fades_to_black(self):
        self.assertEqual(self.fake(waiting={'base': 0, 'n': 5})[1].visible_ones(), ())
        self.assertEqual(self.fake(effect={'n': 5})[1].visible_ones(), ())
        self.assertEqual(self.fake(fade={'devant': dict(a=0.3, pas=0.03, n=20)})[1].visible_ones(), ())                  # fondu au noir qui monte (fin de combat)
        self.assertEqual(self.fake(fade={'devant': dict(a=1.0)})[1].visible_ones(), ())                                  # ecran noir
        self.assertEqual(self.fake(fade={'fond': dict(a=0.5, pas=0.03, n=5)})[1].visible_ones(), ())                      # (plan de fond aussi)
        self.assertEqual(self.fake(fade={'devant': dict(a=0.5, pas=-0.03, n=15)})[1].visible_ones(), (HM.BATTLE,))        # fondu d'entree : le bouton apparait

    def test_click(self):
        J, b = self.fake(); x, y, w, h = b.rect(HM.BATTLE)
        self.assertEqual(b.press(x + w / 2, y + h / 2, (HM.BATTLE,)), HM.BATTLE); self.assertEqual(b.let_go(x + w / 2, y + h / 2, (HM.BATTLE,)), HM.BATTLE)
        self.assertEqual(b.press(x + w / 2, y + h / 2, (HM.BATTLE,)), HM.BATTLE); self.assertIsNone(b.let_go(x + w + 40, y + h / 2, (HM.BATTLE,)))     # relache ailleurs : pas de clic
        self.assertIsNone(b.under(x + w / 2, y + h / 2, ('carte', 'menu')))                                          # pas visible : pas atteignable
        self.assertNotIn(HM.BATTLE, HM.DECL)                                                                        # ne passe rien au moteur

    def test_default_position_hides_no_game_element(self):
        """A gauche de la colonne portrait (450 x 800 centree) des fenetres du jeu, aux formats usuels ; sans recouvrir les autres boutons montres dans l'editeur."""
        for W, H in ((1280, 720), (1920, 1080), (2560, 1080), (3440, 1440), (1366, 768), (1600, 900), (1280, 800)):
            J, b = self.fake(W, H); x, y, w, h = b.rect(HM.BATTLE); col0 = (W - 450.0 * H / 800.0) / 2.0
            self.assertGreaterEqual(x, 0); self.assertLessEqual(x + w, col0 - 4, '%dx%d : le bouton touche la colonne des fenetres du jeu' % (W, H)); self.assertTrue(0 <= y and y + h <= H)
            for n in ('carte', 'menu', 'discussion', HM.DPAD):
                a = b.rect(n); self.assertFalse(x < a[0] + a[2] and a[0] < x + w and y < a[1] + a[3] and a[1] < y + h, '%dx%d : recouvre %s' % (W, H, n))

    def test_movable_in_editor_and_restorable(self):
        J, b = self.fake(); x, y, w, h = b.rect(HM.BATTLE); self.assertIn(HM.BATTLE, HM.EDITOR_NAMES)
        self.assertEqual(b.take(x + 5, y + 5, HM.editor_names(RG.SPEED_TARGET)), HM.BATTLE); b.move_to(x + 5 + 400, y + 5 - 100); b.place()
        self.assertEqual(len(J.reg['bouton_vitesse_pos']), 2); self.assertEqual(J.reg['boutons_pos'], {}); x2, y2, _, _ = b.rect(HM.BATTLE); self.assertGreater(x2, x + 300); self.assertLess(y2, y)        # (position propre : plus dans 'boutons_pos')
        r = RG.Settings(None); r['bouton_vitesse_pos'] = list(J.reg['bouton_vitesse_pos']); r.reset_interface(RG.SPEED_TARGET); self.assertEqual(r['bouton_vitesse_pos'], [])        # « Rétablir cette interface » le remet en place

    def test_editor_caption(self):
        self.assertEqual(HM.CAPTION[HM.BATTLE], 'Vitesse de combat')


@unittest.skipUnless(os.environ.get('DQ_APK') and os.environ.get('DQ_SAVES') and ENGINE is not None, 'moteur reel : DQ_APK et DQ_SAVES requis')
class EngineReplay(unittest.TestCase):
    """Moteur reel : meme combat (memes entrees par pas du moteur) rejoue a 1, 2 et 3 pas par image affichee avec la boucle de la visionneuse (VC.avancer) : memes paquets, memes messages, meme fin ; seul le temps change."""
    MAX_STEPS = int(os.environ.get('DQ_PAS_MAX') or 1100)                       # pas du moteur compares (1100 = 37 s de combat, une trentaine de secondes de test)

    def replay(self, f):
        sys.path.insert(0, os.environ.get('DQ_OUTILS', HERE))
        wdir = tempfile.mkdtemp(prefix='sv_vc_'); eng = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], wdir); eng.load_save(4)
        for _ in range(200): eng.step(0, 0)
        eng.impose_scroll_mode(2)
        dirs = [ENGINE.LEFT, ENGINE.UP, ENGINE.RIGHT, ENGINE.DOWN]; n = 0
        while eng.state.part != ENGINE.PART_BATTLE and n < 6000: d = dirs[(n // 24) % 4]; eng.step(d, d if n % 24 == 0 else 0); n += 1
        self.assertEqual(eng.state.part, ENGINE.PART_BATTLE)
        trace = []; state = {'rel': None, 'att': 0, 'k': 0}
        def input_buf():
            p = decl = 0
            if state['rel'] is not None: eng.send_menu(state['rel'], 1, -1, 0); state['rel'] = None
            port = eng.active_menu()
            if port is not None and not eng.msg_visible:
                state['att'] += 1
                if state['att'] % 4 == 0: eng.send_menu(port, 1, -1, 0x10); state['rel'] = port
            elif eng.msg_visible and eng.ui.msg.get('feed'):
                state['att'] += 1
                if state['att'] % 4 == 0: p = decl = ENGINE.A
            else: state['att'] = 0
            return p, decl
        def perform():
            p, decl = input_buf(); pkt = eng.step(p, decl); state['k'] += 1
            trace.append((state['k'], [(t, tuple(a[:6]), tuple(round(x, 3) for x in fl[:6])) for t, a, fl in pkt if t not in (22, 28, 29)], tuple(sorted(eng.ui.msg.items())), eng.state.part, eng.msg_visible, eng.active_menu(), tuple(eng.ui.damage)))      # (+ nombres de degats, que la visionneuse prend puis vide a chaque pas)
            eng.ui.damage = []
            return not (eng.active_menu() is not None or (eng.msg_visible and eng.ui.msg.get('feed')))
        h = [0.0]; acc = 0.0; frames = 0
        while eng.state.part == ENGINE.PART_BATTLE and state['k'] < self.MAX_STEPS:
            fac = VC.factor(f, True); fac = 1.0 if (eng.active_menu() is not None or bool(eng.msg_visible and eng.ui.msg.get('feed'))) else fac      # (le rejeu lit les touches a chaque pas : attente = vitesse normale, comme avant les pas muets)
            acc, _, _ = VC.advance_time(acc, 1.0 / 60.0, fac, perform, lambda: h[0]); h[0] += 1.0 / 60.0; frames += 1
        return trace[:self.MAX_STEPS], frames

    def test_same_battle_at_all_speeds(self):
        ref, im1 = self.replay(1.0)
        for f in (2.0, 3.0):
            tr, im = self.replay(f); n = min(len(ref), len(tr)); self.assertGreater(n, self.MAX_STEPS * 0.7)
            self.assertEqual(tr[:n], ref[:n], 'x%g : le combat n\'est pas identique' % f)                       # memes paquets (hors maillages), memes messages, meme etat, pas pour pas
            self.assertLess(im, im1, 'x%g : pas plus rapide' % f)


if __name__ == '__main__':
    unittest.main(verbosity=2)
