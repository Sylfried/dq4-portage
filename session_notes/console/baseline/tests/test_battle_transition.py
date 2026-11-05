"""Transitions d'un combat (retours de 22 h 29, #47 ; avant : #45, retour de 14 h 08).

Sylfried : « L'accélération du combat doit être prise en compte dès la fin de l'animation de transition en cascade et dès l'apparition du message indiquant qu'un ennemi apparaît, et finalement je veux qu'elle dure
jusqu'à la fin donc pendant le fondu au noir » ; « Les effets de transitions au début et à la fin d'un combat eux doivent en tous cas être affectés par l'accélération de transition des paramètres, comme tout effet de transition ».

La transition = effet d'ecran de debut (la « cascade » : 57 images du jeu), ecran noir qui attend la scene, fondu d'arrivee du combat, fondus de sortie du combat, fondu de retour a la carte. Regles verifiees :
  - DUREE (images du moteur) : la cascade et chaque fondu durent ce que demande le jeu divise par « Vitesse de transition » (x1 a x4), comme un fondu de changement de carte (game_priority.fade_duration) ;
  - HORLOGE (temps reel) : la cascade est a l'horloge du jeu (30 images par seconde) quels que soient « Vitesse de combat », vitesse de marche et accelerateur ; des la fin de la cascade (ecran noir, fondu d'arrivee,
    message « X apparait ») et jusqu'au fondu de fin de combat compris, « Vitesse de combat » (x1, x1, x2, x3) s'applique ; le retour a la carte est a l'horloge du jeu tant que le joueur est verrouille (flag 4) ; des qu'il est libre (image 12 du retour, le heros marche des la 13), la marche acceleree et l'accelerateur agissent (#127, comme #107 pour un changement de carte).

    python3 tools/test_battle_transition.py        (Linux sans ecran : pyglet en mode « headless »)
    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> tools/session_flow/engine_slot.sh python3 -W ignore tools/test_battle_transition.py     (ajoute le rejeu d'un vrai combat du moteur)
Les sauvegardes ne sont ouvertes qu'en lecture : le moteur ecrit dans un dossier temporaire."""
import itertools, os, sys, tempfile, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
try:
    import pyglet
    if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
    from dq4_pc.window import game as F
except Exception as ex:
    F = None; IMPORT_ERROR = ex
from dq4_pc.core import engine as ENGINE
from dq4_pc.core import game_priority as PJ

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
STEP = 1.0 / 30.0
BATTLE_FADE = 0x1000 | 30              # paquet 9 : sortie au noir en 30 images (4126, vu a la fin de chaque combat)
ENTRY_30 = 30                          # paquet 9 : entree en 30 images


def state(part=ENGINE.PART_FIELD, fade_speed=1.0):
    e = ENGINE.State(); e.part = part; ENGINE.State.fade_speed = fade_speed; return e


class Fades(unittest.TestCase):
    def tearDown(self): ENGINE.State.fade_speed = 1.0

    def test_outside_battle_setting_always_shortens(self):
        for vf, expected in ((1.0, 30), (2.0, 15), (4.0, 8)):
            e = state(ENGINE.PART_FIELD, vf); e.apply([(9, [ENTRY_30], [])], lambda: ''); self.assertEqual(e.fade['n'], expected, 'x%g' % vf); self.assertFalse(e.fade['combat'])
            self.assertFalse(e.battle_transition())

    def test_battle_arrival_fade_follows_transition_speed(self):
        for vf in (1.0, 2.0, 3.0, 4.0):
            d = PJ.fade_duration(30, vf)
            e = state(ENGINE.PART_FIELD, vf); e.apply([(0, [0x100], []), (9, [ENTRY_30], [])], lambda: 'btl_pl_d')           # chargement de la scene de combat (bit 8) puis fondu d'entree, meme image du moteur
            self.assertEqual(e.fade['n'], d, 'x%g' % vf); self.assertTrue(e.fade['combat']); self.assertTrue(e.battle_transition())
            e.loading = None                                                                                                      # (la retenue du dessin apres un chargement retarde le DEBUT du fondu, pas sa duree : test_loading)
            for i in range(d - 1): e.tick_fade(); e.tick_transition(); self.assertTrue(e.battle_transition(), 'image %d' % i)
            e.tick_fade(); self.assertEqual(e.fade['n'], 0)
        self.assertEqual([PJ.fade_duration(30, v) for v in (1.0, 2.0, 3.0, 4.0)], [30, 15, 10, 8])

    def test_battle_end_and_map_return_fades_follow_transition_speed(self):
        for vf in (1.0, 2.0, 4.0):
            d, d3 = PJ.fade_duration(30, vf), PJ.fade_duration(3, vf)
            e = state(ENGINE.PART_BATTLE, vf); e.apply([(9, [BATTLE_FADE], [])], lambda: '')
            self.assertEqual(e.fade['n'], d, 'x%g' % vf); self.assertTrue(e.battle_transition())
            for _ in range(d): e.tick_fade(); e.tick_transition()
            self.assertEqual(e.fade['n'], 0); self.assertGreater(e.transition_guard, 0); self.assertTrue(e.battle_transition())       # le moteur change de scene 1 a 3 images plus tard
            e.apply([(9, [0x4000 | 3], [])], lambda: ''); self.assertEqual(e.background_fade['n'], d3 if d3 > 1 else 0)           # fondu du plan de fond (encore dans la partie combat) : meme regle
            e.tick_fade(); e.tick_transition()
            e.part = ENGINE.PART_FIELD; e.return_window = ENGINE.BATTLE_RETURN_WINDOW                                                   # (Engine.step : la partie quitte le combat)
            e.apply([(9, [ENTRY_30], [])], lambda: ''); self.assertEqual(e.fade['n'], d, 'retour x%g' % vf); self.assertTrue(e.fade['combat'])
            for _ in range(d): self.assertTrue(e.battle_transition()); e.tick_fade(); e.tick_transition()
            for _ in range(ENGINE.TRANSITION_GUARD + 2): e.tick_fade(); e.tick_transition()
            self.assertFalse(e.battle_transition())                                                                               # la transition est finie : la marche reprend ses reglages

    def test_cascade_follows_transition_speed(self):
        """Engine._start_battle_effect / _battle_effect (sans moteur : le drapeau d'effet est simule) : 57 images a x1, 57 / facteur ensuite ; la simulation de la visionneuse atteint ses 57 images au dernier dessin."""
        import math
        for vf in (1.0, 2.0, 3.0, 4.0):
            ENGINE.State.fade_speed = vf; e = ENGINE.State(); eng = types.SimpleNamespace(state=e, _effect_flag=lambda a: None)
            ENGINE.Engine._start_battle_effect(eng, 0); d = PJ.fade_duration(ENGINE.BATTLE_EFFECT_FRAMES, vf); self.assertEqual(e.effect['duree'], d); n = 0; targets = []
            while e.effect is not None:
                targets.append(math.ceil(e.effect['n'] * ENGINE.BATTLE_EFFECT_FRAMES / e.effect['duree'])); ENGINE.Engine._battle_effect(eng); n += 1
            self.assertEqual(n, d, 'x%g' % vf); self.assertEqual(targets[0], 0); self.assertGreaterEqual(targets[-1], ENGINE.BATTLE_EFFECT_FRAMES - math.ceil(ENGINE.BATTLE_EFFECT_FRAMES / d))      # (dernier dessin : la cascade est quasi finie)
            self.assertTrue(all(b >= a for a, b in zip(targets, targets[1:])))
        self.assertEqual([PJ.fade_duration(ENGINE.BATTLE_EFFECT_FRAMES, v) for v in (1.0, 2.0, 4.0)], [57, 28, 14])
        e = ENGINE.State(); e.effect = {'n': 3}; eng = types.SimpleNamespace(state=e, _effect_flag=lambda a: None)           # (etat enregistre avant la cle 'duree' : 57 images)
        for _ in range(ENGINE.BATTLE_EFFECT_FRAMES - 4): ENGINE.Engine._battle_effect(eng)
        self.assertIsNotNone(e.effect); ENGINE.Engine._battle_effect(eng); self.assertIsNone(e.effect)

    def test_arrival_window_elapses(self):
        """Un fondu lance bien apres le chargement du combat (ou une carte ordinaire) reste soumis a « Vitesse de transition »."""
        e = state(ENGINE.PART_FIELD, 2.0); e.apply([(0, [0x100], [])], lambda: 'btl_pl_d')
        for _ in range(ENGINE.BATTLE_ENTRY_WINDOW + 1): e.tick_transition()
        e.load_wait = None; e.part = ENGINE.PART_FIELD
        e.apply([(9, [ENTRY_30], [])], lambda: ''); self.assertEqual(e.fade['n'], 15); self.assertFalse(e.fade['combat']); self.assertFalse(e.battle_transition())
        e2 = state(ENGINE.PART_FIELD, 2.0); e2.apply([(0, [0], []), (9, [ENTRY_30], [])], lambda: 'mak1f1'); self.assertEqual(e2.fade['n'], 15)       # un changement de carte ordinaire reste raccourci
        self.assertFalse(e2.battle_transition())

    def test_script_and_color_fades_unchanged(self):
        e = state(ENGINE.PART_BATTLE, 4.0); e.apply([(9, [0x1000 | 0x800 | 20], [1.0, 0.0, 0.0])], lambda: ''); self.assertEqual(e.fade['n'], 20)
        e = state(ENGINE.PART_FIELD, 4.0); e.apply([(9, [PJ.SCRIPT_FADE_MARK | 0x1000 | 60], [])], lambda: ''); self.assertEqual(e.fade['n'], 60)

    def test_state_stored_before_transition(self):
        e = state(); d = dict(e.__dict__)
        for k in ('entry_window', 'return_window', 'transition_guard'): d.pop(k)
        e2 = ENGINE.State.__new__(ENGINE.State); e2.__setstate__(d); self.assertFalse(e2.battle_transition()); self.assertEqual(e2.transition_guard, 0)
        d['fade'] = {k: v for k, v in d['fade'].items() if k != 'combat'}
        e3 = ENGINE.State.__new__(ENGINE.State); e3.__setstate__(d); self.assertFalse(e3.battle_transition())                       # (plan de fondu sans la cle 'combat')


@unittest.skipIf(F is None, 'window.py non importable ici')
class Clock(unittest.TestCase):
    @staticmethod
    def game(e, battle_speed=1.0, walk=1.0, accel=1.0, accel_held=False, direction=True, menu=None, flags=0x28):
        j = types.SimpleNamespace(reg={'vitesse_combat': battle_speed, 'vitesse_marche': walk, 'vitesse_accel': accel})
        j.engine = types.SimpleNamespace(state=e, msg_visible=False, active_menu=lambda: menu, flags=lambda: flags, ui=types.SimpleNamespace(msg={'feed': False}))
        j.pad = lambda: ENGINE.UP if direction else 0; j._held = lambda a: accel_held and a == 'accel'; j.hud = types.SimpleNamespace(dpad_run=lambda: False); j.pause = types.SimpleNamespace(opened=False)
        for name_str in ('_battle_clock', '_wait_for_player'): setattr(j, name_str, types.MethodType(getattr(F.Game, name_str), j))
        j.factor = lambda: F.Game._speed_factor(j)
        return j

    SETTINGS = list(itertools.product((0.0, 1.0, 2.0, 3.0), (1.0, 2.0, 4.0), (1.0, 1.5, 2.0), (False, True)))

    def test_cascade_on_game_clock(self):
        for vc, walk, accel, held_name in self.SETTINGS:
            e = state(ENGINE.PART_FIELD); e.effect = {'n': 5}
            self.assertEqual(self.game(e, vc, walk, accel, held_name).factor(), 1.0, 'cascade %s' % ((vc, walk, accel, held_name),))

    def test_battle_speed_applies_from_cascade_end_through_final_fade(self):
        for vc, walk, accel, held_name in self.SETTINGS:
            expected = max(1.0, vc); r = (vc, walk, accel, held_name)
            e = state(ENGINE.PART_FIELD); e.load_wait = {'base': 0, 'n': 1}
            self.assertEqual(self.game(e, *r).factor(), expected, 'ecran noir apres la cascade %s' % (r,))
            e = state(ENGINE.PART_BATTLE); e.entry_window = 5; e.apply([(9, [ENTRY_30], [])], lambda: '')
            self.assertEqual(self.game(e, *r).factor(), expected, 'fondu d\'arrivee et message « X apparait » %s' % (r,))
            e = state(ENGINE.PART_BATTLE); e.apply([(9, [BATTLE_FADE], [])], lambda: ''); self.assertTrue(e.battle_transition())
            self.assertEqual(self.game(e, *r).factor(), expected, 'fondu au noir de fin de combat %s' % (r,))
            e.transition_guard = 5; e.fade['n'] = 0
            self.assertEqual(self.game(e, *r).factor(), expected, 'images entre deux fondus, encore dans la partie combat %s' % (r,))

    def test_return_to_map_game_clock_while_player_locked(self):
        """Fondu de retour : horloge du jeu tant que le joueur est verrouille (flag 4, images 1 a 11) et entre deux fondus ; des que le verrou tombe, la marche et l'accelerateur agissent (#127)."""
        for vc, walk, accel, held_name in self.SETTINGS:
            r = (vc, walk, accel, held_name)
            e = state(ENGINE.PART_FIELD); e.return_window = 5; e.apply([(9, [ENTRY_30], [])], lambda: ''); self.assertTrue(e.battle_transition())
            self.assertEqual(self.game(e, *r, flags=0x2d).factor(), 1.0, 'fondu de retour, joueur verrouille %s' % (r,))
            expected = max(0.25, min(8.0, walk * (accel if held_name else 1.0)))
            self.assertEqual(self.game(e, *r, flags=0x29).factor(), expected, 'fondu de retour, joueur libre %s' % (r,))
            e.fade['n'] = 0; e.transition_guard = 4
            self.assertEqual(self.game(e, *r, flags=0x1).factor(), 1.0, 'entre deux fondus sur la carte %s' % (r,))

    def test_battle_turns_keep_accelerating(self):
        for vc in (0.0, 1.0, 2.0, 3.0):
            for walk, accel, held_name in ((1.0, 1.0, False), (4.0, 2.0, True)):
                self.assertEqual(self.game(state(ENGINE.PART_BATTLE), vc, walk, accel, held_name).factor(), max(1.0, vc))                     # hors transition : la vitesse de combat s'applique
                self.assertEqual(self.game(state(ENGINE.PART_BATTLE), vc, walk, accel, held_name, menu=13).factor(), max(1.0, vc))           # (les attentes du joueur aussi : les monstres gardent leur allure)

    def test_walk_keeps_settings_outside_transition(self):
        self.assertEqual(self.game(state(ENGINE.PART_FIELD), 3.0, 2.0, 1.5, True).factor(), 3.0)
        self.assertEqual(self.game(state(ENGINE.PART_FIELD), 3.0, 4.0, 2.0, True).factor(), 8.0)

    def test_step_triggering_cascade_stops_catchup(self):
        """Marche acceleree (jusqu'a 8 pas par image) : quand un des pas leve l'effet de debut de combat, les pas restants de l'image n'ont pas a raccourcir la cascade : le rattrapage s'arrete (True = on continue)."""
        e = state(ENGINE.PART_FIELD); calls = []
        j = types.SimpleNamespace(engine=types.SimpleNamespace(state=e), _step=lambda mute=False: calls.append(mute))
        self.assertTrue(F.Game._terrain_step(j)); self.assertTrue(F.Game._do_battle_step(types.SimpleNamespace(engine=j.engine, _t_real_step=0.0, _wait_for_player=lambda: False, _step=j._step)))
        def lift(mute=False): e.effect = {'n': 0}
        j._step = lift; self.assertFalse(F.Game._terrain_step(j))                                       # la cascade vient de commencer pendant ce pas : stop
        self.assertTrue(F.Game._terrain_step(j))                                                         # (deja en transition : on continue normalement)
        e.effect = None
        jc = types.SimpleNamespace(engine=types.SimpleNamespace(state=e), _t_real_step=0.0, _wait_for_player=lambda: False, _step=lift)
        self.assertFalse(F.Game._do_battle_step(jc))                                                  # idem pendant un combat accelere (fondu de sortie)


@unittest.skipUnless(APK and SAVES and F is not None, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class RealEngine(unittest.TestCase):
    """Rejoue de vraies rencontres (carte du monde, rencontre forcee, attaque jusqu'a la victoire) avec « Vitesse de transition » x1, x2 et x4 : durees en images du moteur ; temps reel simule avec la vraie fonction
    Game._speed_factor pour toutes les combinaisons de reglages (vitesse de combat x marche x accelerateur x touche tenue)."""
    @classmethod
    def setUpClass(cls):
        cls.settings = Clock.SETTINGS
        cls.runs = {vf: cls.replay(vf) for vf in (1.0, 2.0, 4.0)}

    @classmethod
    def replay(cls, fade_speed):
        ENGINE.State.fade_speed = fade_speed
        eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_trans_'))
        for _ in range(3): eng.step(0, 0)
        eng.load_save(4)
        for i in range(100): eng.step(0, 0x10 if i % 10 == 0 else 0)
        if eng.state.part != ENGINE.PART_FIELD:
            eng.start_field()
            for i in range(120): eng.step(0, 0)
        c = eng.core
        c.call(eng.E('_ZN7Encount12forceEncountEv'), c.call(eng.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
        step = []; packets9 = []                                                          # une entree par pas du moteur (etat APRES le pas) : image, partie, cascade, ecran noir, plan de devant (n, sortie ?), transition ?, facteurs par reglage
        att = 0; rel = None; end = None; seen_battle = False
        for i in range(6000):
            p = d = 0
            if rel is not None: eng.send_menu(rel, 1, -1, 0); rel = None
            port = eng.active_menu()
            if eng.state.part == ENGINE.PART_BATTLE and port is not None and not eng.msg_visible:
                att += 1
                if att % 4 == 0: eng.send_menu(port, 1, -1, 0x10); rel = port
            elif eng.state.part == ENGINE.PART_BATTLE and eng.msg_visible and eng.message_state()[1] in (3, 5):
                att += 1
                if att > 100 and att % 4 == 0: p = d = ENGINE.A
            else: att = 0
            if not seen_battle: p = [0x4, 0x8][(i // 20) % 2]; d = 0                    # (marche : la rencontre forcee se declenche en marchant)
            prev = eng.state.part; pkt = eng.step(p, d); eng.ui.damage = []
            for t, a, f in pkt:
                if t == 9: packets9.append((eng.frames, a[0] & 0x7ff, bool(a[0] & 0x1000), bool(a[0] & 0x4000)))
            if eng.state.part == ENGINE.PART_BATTLE: seen_battle = True
            e = eng.state
            games = [Clock.game(e, vc, walk, accel, held_name, menu=eng.active_menu(), flags=eng.flags()) for vc, walk, accel, held_name in cls.settings]
            step.append(dict(im=eng.frames, partie=e.part, effet=e.effect is not None, attente=e.load_wait is not None, fn=e.fade['n'], fsortie=e.fade['fin'] >= 1.0, trans=e.battle_transition(), verrou=bool(eng.flags() & ENGINE.PLAYER_LOCKED_FLAG), garde=e.transition_guard,
                            facteurs=[j.factor() for j in games]))
            if seen_battle and prev == ENGINE.PART_BATTLE and e.part != ENGINE.PART_BATTLE: end = eng.frames
            if end and eng.frames > end + 90: break
        assert end is not None, 'le combat ne s\'est pas termine'
        ENGINE.State.fade_speed = 1.0
        return dict(pas=step, paquets9=packets9)

    def tearDown(self): ENGINE.State.fade_speed = 1.0

    @staticmethod
    def suites(step, cond):
        """Suites d'images consecutives qui verifient `cond` : [(indice du premier pas, nombre de pas)]."""
        out = []; start_idx = None
        for k, x in enumerate(step):
            if cond(x) and start_idx is None: start_idx = k
            if not cond(x) and start_idx is not None: out.append((start_idx, k - start_idx)); start_idx = None
        if start_idx is not None: out.append((start_idx, len(step) - start_idx))
        return out

    def test_cascade_lasts_57_frames_divided_by_transition_speed(self):
        for vf, parent_idx in self.runs.items():
            casc = self.suites(parent_idx['pas'], lambda x: x['effet']); self.assertEqual(len(casc), 1, 'x%g : une cascade par combat (%r)' % (vf, casc))
            self.assertEqual(casc[0][1], PJ.fade_duration(ENGINE.BATTLE_EFFECT_FRAMES, vf), 'Vitesse de transition x%g' % vf)

    def test_battle_end_and_return_fades_follow_transition_speed(self):
        """Fondu au noir de fin (dans la partie combat) : le moteur le demande en 30 images ; Etat le rejoue en 30 / facteur."""
        for vf, parent_idx in self.runs.items():
            d = PJ.fade_duration(30, vf); self.assertIn(30, [x[1] for x in parent_idx['paquets9']])
            ends = self.suites(parent_idx['pas'], lambda x: x['partie'] == ENGINE.PART_BATTLE and x['fsortie'] and x['fn'] >= 1)
            self.assertTrue(ends, 'x%g : fondu de fin non vu' % vf); self.assertEqual(max(n for _, n in ends), d - 1, 'fin de combat, x%g' % vf)          # (apres le pas qui le lance : d - 1 images restantes)
            back = self.suites(parent_idx['pas'], lambda x: x['partie'] != ENGINE.PART_BATTLE and not x['effet'] and not x['attente'] and x['fn'] >= 1 and not x['fsortie'] and x['trans'])
            self.assertTrue(back and max(n for _, n in back) in (d - 1, d), 'retour a la carte, x%g : %r' % (vf, back))

    def test_acceleration_starts_at_cascade_end_lasts_through_end_fade(self):
        for vf, parent_idx in self.runs.items():
            step = parent_idx['pas']; casc = self.suites(step, lambda x: x['effet'])[0]; casc_end = casc[0] + casc[1]
            for k in range(casc[0], casc_end):
                for r, regl in enumerate(self.settings): self.assertEqual(step[k]['facteurs'][r], 1.0, 'cascade, image %d, %s' % (k, regl))
            ends = self.suites(step, lambda x: x['partie'] == ENGINE.PART_BATTLE and x['fsortie'] and x['fn'] >= 1)
            for k, x in enumerate(step):
                if k < casc_end or not (x['partie'] == ENGINE.PART_BATTLE or x['attente']): continue
                for r, (vc, *_r) in enumerate(self.settings): self.assertEqual(x['facteurs'][r], max(1.0, vc), 'vf x%g image %d (partie %#x), vitesse de combat %g' % (vf, k, x['partie'], vc))
            for start_idx, n in ends:                                                                  # le fondu au noir de fin : encore accelere
                for k in range(start_idx, start_idx + n):
                    for r, (vc, *_r) in enumerate(self.settings): self.assertEqual(step[k]['facteurs'][r], max(1.0, vc))
            self.assertTrue(any(x['attente'] and not x['effet'] for x in step[casc_end:casc_end + 8]) or step[casc_end]['partie'] == ENGINE.PART_BATTLE)      # (la premiere image apres la cascade est deja de l'ecran noir ou du combat)

    def test_real_time(self):
        """Temps reel = somme des 1 / (30 x facteur) : la cascade dure (57 / vitesse de transition) / 30 s quels que soient les reglages ; le fondu de fin de combat, lui, suit la vitesse de combat ; le retour a la carte reste a l'horloge du jeu tant que le joueur est verrouille, puis suit la marche (#127)."""
        for vf, parent_idx in self.runs.items():
            step = parent_idx['pas']; start_idx, n = self.suites(step, lambda x: x['effet'])[0]
            back = self.suites(step, lambda x: x['partie'] != ENGINE.PART_BATTLE and not x['effet'] and not x['attente'] and x['trans'])
            ends = self.suites(step, lambda x: x['partie'] == ENGINE.PART_BATTLE and x['fsortie'] and x['fn'] >= 1)
            for r, (vc, walk, accel, held_name) in enumerate(self.settings):
                self.assertAlmostEqual(sum(STEP / step[k]['facteurs'][r] for k in range(start_idx, start_idx + n)), PJ.fade_duration(ENGINE.BATTLE_EFFECT_FRAMES, vf) * STEP, 9, 'cascade %s x%g' % ((vc, walk, accel, held_name), vf))
                for d0, m in ends: self.assertAlmostEqual(sum(STEP / step[k]['facteurs'][r] for k in range(d0, d0 + m)), m * STEP / max(1.0, vc), 9, 'fondu de fin %s x%g' % ((vc, walk, accel, held_name), vf))
                for d0, m in back:
                    for k in range(d0, d0 + m):                                          # le retour a la carte : horloge du jeu tant que le joueur est verrouille ou entre deux fondus ; le reglage de marche des que le verrou tombe (#127)
                        expected = 1.0 if step[k]['verrou'] or step[k]['garde'] > 0 else max(0.25, min(8.0, walk * (accel if held_name else 1.0)))
                        self.assertEqual(step[k]['facteurs'][r], expected, 'retour a la carte, pas %d, %s x%g' % (k, (vc, walk, accel, held_name), vf))

if __name__ == '__main__':
    unittest.main()
