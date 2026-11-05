"""Test du retour a l'ecran-titre (issue #109) : menu Pause > « Revenir à l'écran titre » = la boite d'origine du jeu (son texte, Oui / Non), puis le fondu au noir du jeu, puis le titre.

    python3 tools/test_return_to_title.py [--apk <dossier des APK patches> --saves <dossier des sauvegardes>]
(ou DQ_APK et DQ_SAVES ; sans eux seules les parties 1 et 2 tournent). La partie 3 charge le vrai moteur (environ 1 minute) : a lancer par `tools/session_flow/engine_slot.sh`.

Partie 1 (sans moteur) : la ligne du menu Pause. Elle ferme le menu et demande le retour au titre au jeu (plus de page de confirmation du menu Pause : la question est celle du jeu) ; elle est grisee
quand le jeu n'est pas en ville ni sur la carte du monde.
Partie 2 (moteur simule) : `Engine.request_return_to_title` et les deux moments joues autour de GameUpdate (`_return_to_title_before` / `_return_to_title_after`) : les appels du moteur dans l'ordre du menu des
Parametres d'origine (TownMenu_OPERATION_SETTING::menuUpdate, etat 5), « Non » ne change rien, « Oui » efface la banque 4 puis lance Global::startTitle ; une boite fermee sans reponse libere le joueur.
Partie 3 (vrai moteur, en ville) : la boite s'ouvre et reste ouverte ; « Non » (flèche vers Non puis A) la ferme sans lancer le titre ; « Oui » (A, curseur d'origine sur Oui) lance killbank puis startTitle dans le
pas meme de GameUpdate et le fondu au noir est progressif (30 images, jamais un saut), puis la carte du titre se charge.
"""
import argparse, inspect, os, struct, sys, tempfile, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import pyglet
pyglet.options['shadow_window'] = False                     # (pas d'affichage necessaire : on ne dessine rien)
from dq4_pc.persistence import settings as RG
from dq4_pc.menus import pause as PA
from dq4_pc.core import engine as ENGINE

K = pyglet.window.key
APK = os.environ.get('DQ_APK'); SAVES = os.environ.get('DQ_SAVES'); REST = sys.argv[1:]
if __name__ == '__main__':
    _ap = argparse.ArgumentParser(); _ap.add_argument('--apk'); _ap.add_argument('--saves'); _a, REST = _ap.parse_known_args()
    APK = _a.apk or APK; SAVES = _a.saves or SAVES
CAPTION = "Revenir à l'écran titre"
PAD_DOWN = 1; PAD_A = 0x10                                    # manette du jeu envoyee aux menus : bas 1, haut 2, droite 4, gauche 8, A 16, B 32 (Game._menu_input) ; le moteur range Oui / Non en une colonne (grille 1 x 2) : « droite » de la visionneuse part en « bas »


class FakeSound:
    active = True; listening = False


class FakeGame:
    """Ce que le menu Pause demande a la fenetre."""
    def __init__(self, possible=True):
        self.reg = RG.Settings(os.path.join(tempfile.mkdtemp(prefix='retour_titre_'), 'settings.json'))
        self.sound = FakeSound(); self.args = types.SimpleNamespace(cache='/inexistant'); self.width, self.height = 1280, 720; self.mouse = None
        self.calls = []; self.possible = possible
    def window_names(self): return {}
    def pause_game(self, yes): self.calls.append(('pause_jeu', yes))
    def back_to_title(self): self.calls.append('titre')
    def back_to_title_possible(self): return self.possible


def menu(possible=True):
    J = FakeGame(possible); p = PA.Pause(J); p.opened = True; p.stack = ['racine']
    return J, p


def line(p): return next(e for e in p._entries() if e.get('l') == CAPTION)


def choose(p):
    """Place le curseur de la racine sur la ligne du retour au titre."""
    p.selected['racine'] = [e.get('l') for e in p._entries()].index(CAPTION)


# ---------------------------------------------------------------------------------------------------------------------------------- 1. le menu Pause
class MenuLine(unittest.TestCase):
    def test_line_is_last_of_root(self):
        J, p = menu(); libs = [e['l'] for e in p._entries() if e['t'] != 'sep']
        self.assertEqual(libs[-1], CAPTION)

    def test_no_more_pause_menu_confirmation_page(self):
        self.assertFalse(hasattr(PA.Pause, '_e_titre'))                                                  # la question est celle du jeu (boite d'origine), pas une page du menu
        src = inspect.getsource(PA.Pause); self.assertNotIn("_go('titre')", src); self.assertNotIn("titles['titre']", src)

    def test_validate_closes_the_menu_and_requests_return_to_game(self):
        J, p = menu(); choose(p); p.key_press(K.RETURN)
        self.assertFalse(p.opened); self.assertEqual([a for a in J.calls if a == 'titre'], ['titre'])
        self.assertIn(('pause_jeu', False), J.calls)                                                    # le jeu reprend : c'est lui qui pose la question

    def test_line_action_is_the_click_action(self):
        J, p = menu(); line(p)['ok'](); self.assertFalse(p.opened); self.assertEqual(J.calls.count('titre'), 1)

    def test_grayed_out_outside_town_and_world_map(self):
        J, p = menu(possible=False); e = line(p)
        self.assertTrue(p._inactive(e)); self.assertFalse(p._active(e)); self.assertTrue(e.get('aide'))   # grisee, avec son explication
        choose(p); p.key_press(K.RETURN)
        self.assertTrue(p.opened); self.assertNotIn('titre', J.calls)                                  # rien ne part

    def test_active_when_possible(self):
        J, p = menu(possible=True); self.assertFalse(p._inactive(line(p)))

    def test_game_knows_when_possible(self):
        from dq4_pc.window import game as F
        src = inspect.getsource(F.Game.back_to_title_possible)
        self.assertIn('PART_TOWN', src); self.assertIn('PART_FIELD', src); self.assertIn('TITLE_MAP', src); self.assertNotIn('PART_BATTLE', src)
        self.assertIn('request_return_to_title', inspect.getsource(F.Game.back_to_title))


# ---------------------------------------------------------------------------------------------------------------------------------- 2. le moteur (simule)
class FakeCountdownCore:
    """Remplace emu_core : enregistre les appels du moteur (noms de symboles), garde une memoire a mots."""
    def __init__(self): self.calls = []; self.memory = {}; self.is_open = True
    def export(self, name_str): return 0x5000 if name_str == 'gTownMenu_MESSAGE' else 0x9000
    def call(self, address, *args, label=None):
        self.calls.append((address, args))
        return (1 if self.is_open else 0) if address == '_ZN8MenuBase6isOpenEv' else 0
    def mem(self, addr, n): return self.memory.get(addr, bytes(n))
    def mem_w(self, addr, raw): self.memory[addr] = bytes(raw); self.calls.append(('mem_w', (addr, bytes(raw))))
    def names(self): return [a[0] for a in self.calls if isinstance(a[0], str) and a[0] != 'mem_w']


def simulated_engine(part=ENGINE.PART_TOWN):
    m = ENGINE.Engine.__new__(ENGINE.Engine); m.core = FakeCountdownCore(); m.E = lambda s: s; m._global = lambda: 0x7000
    m.state = types.SimpleNamespace(part=part); m.back_to_title_state = None
    return m


def answer(m, v): m.core.memory[0x5000 + ENGINE.MESSAGE_RESULT] = struct.pack('<I', v)


class ReturnMachine(unittest.TestCase):
    def test_original_menu_constants(self):
        self.assertEqual(ENGINE.MSG_RETURN_TITLE, 0xcba2f); self.assertEqual(ENGINE.MESSAGE_RESULT, 0x10)

    def test_only_in_town_and_on_the_map(self):
        for part, expected in ((ENGINE.PART_TOWN, True), (ENGINE.PART_FIELD, True), (ENGINE.PART_BATTLE, False), (ENGINE.PART_CASINO, False), (ENGINE.PART_BESTIARY, False), (ENGINE.PART_INITIAL, False)):
            m = simulated_engine(part); self.assertEqual(m.request_return_to_title(), expected, part); self.assertEqual(m.back_to_title_state, 'ouvrir' if expected else None)

    def test_a_single_request_at_a_time(self):
        m = simulated_engine(); self.assertTrue(m.request_return_to_title()); self.assertFalse(m.request_return_to_title())

    def test_opening_like_original_menu(self):
        m = simulated_engine(); m.request_return_to_title(); answer(m, 2); m._return_to_title_before()               # (une ancienne reponse ne compte pas : remise a 0)
        self.assertEqual(m.back_to_title_state, 'dialogue')
        self.assertEqual(m.core.names(), ['_ZN3cmn11GameManager12getSingletonEv', '_ZN3cmn13PlayerManager7setLockEb', '_ZN16TownMenu_MESSAGE18openMessageForMENUEv', '_ZN16TownMenu_MESSAGE10addMessageEi',
                                         '_ZN16TownMenu_MESSAGE8setYesNoEv', '_ZN16TownMenu_MESSAGE19setYesNoSuperCancelEb'])
        a = {x[0]: x[1] for x in m.core.calls if isinstance(x[0], str)}
        self.assertEqual(a['_ZN3cmn13PlayerManager7setLockEb'], (1,)); self.assertEqual(a['_ZN16TownMenu_MESSAGE10addMessageEi'], (0x5000, 0xcba2f)); self.assertEqual(a['_ZN16TownMenu_MESSAGE19setYesNoSuperCancelEb'], (0x5000, 0))
        self.assertEqual(m.core.memory[0x5000 + ENGINE.MESSAGE_RESULT], bytes(4))

    def test_nothing_before_the_request(self):
        m = simulated_engine(); m._return_to_title_before(); m._return_to_title_after(); self.assertEqual(m.core.calls, []); self.assertIsNone(m.back_to_title_state)

    def test_waiting_for_answer(self):
        m = simulated_engine(); m.request_return_to_title(); m._return_to_title_before(); m.core.calls.clear(); answer(m, 0); m._return_to_title_after()
        self.assertEqual(m.back_to_title_state, 'dialogue'); self.assertEqual(m.core.names(), ['_ZN8MenuBase6isOpenEv'])                                # seulement la lecture de l'etat de la boite

    def test_no_changes_nothing(self):
        m = simulated_engine(); m.request_return_to_title(); m._return_to_title_before(); m.core.calls.clear(); answer(m, 2); m._return_to_title_after()
        self.assertIsNone(m.back_to_title_state); n = m.core.names()
        self.assertIn('_ZN8MenuBase5closeEv', n); self.assertNotIn('_ZN6Global10startTitleEv', n); self.assertNotIn('_ZN7profile8SaveLoad8killbankEib', n)
        self.assertEqual([x[1] for x in m.core.calls if x[0] == '_ZN3cmn13PlayerManager7setLockEb'], [(0,)])               # le joueur est libere

    def test_yes_erases_bank_4_then_launches_title(self):
        m = simulated_engine(); m.request_return_to_title(); m._return_to_title_before(); m.core.calls.clear(); answer(m, 1); m._return_to_title_after()
        self.assertIsNone(m.back_to_title_state); n = m.core.names()
        self.assertLess(n.index('_ZN7profile8SaveLoad8killbankEib'), n.index('_ZN6Global10startTitleEv')); self.assertEqual(n[-1], '_ZN6Global10startTitleEv')
        self.assertEqual([x[1] for x in m.core.calls if x[0] == '_ZN7profile8SaveLoad8killbankEib'], [(4, 0)])
        self.assertEqual([x[1] for x in m.core.calls if x[0] == '_ZN3cmn13PlayerManager7setLockEb'], [(1,)])

    def test_closed_box_without_answer_releases_player(self):
        m = simulated_engine(); m.request_return_to_title(); m._return_to_title_before(); m.core.calls.clear(); m.core.is_open = False; answer(m, 0); m._return_to_title_after()
        self.assertIsNone(m.back_to_title_state); self.assertEqual([x[1] for x in m.core.calls if x[0] == '_ZN3cmn13PlayerManager7setLockEb'], [(0,)]); self.assertNotIn('_ZN6Global10startTitleEv', m.core.names())
        self.assertTrue(m.request_return_to_title())                                                                        # et on peut redemander

    def test_two_moments_are_in_the_engine_step(self):
        """Le fondu du titre est un paquet lu avec ceux du pas : startTitle doit etre lance entre `pk.begin()` et `pk.packets()`, autour de GameUpdate (sinon le fondu est perdu et l'ecran saute au noir)."""
        src = inspect.getsource(ENGINE.Engine.step)
        i0 = src.index('self.pk.begin()'); i1 = src.index('_return_to_title_before()'); i2 = src.index("'GameUpdate'"); i3 = src.index('_return_to_title_after()'); i4 = src.index('self.pk.packets()')
        self.assertTrue(i0 < i1 < i2 < i3 < i4)


# ---------------------------------------------------------------------------------------------------------------------------------- 3. le vrai moteur
@unittest.skipUnless(APK and SAVES, 'moteur reel : --apk et --saves (ou DQ_APK et DQ_SAVES)')
class RealEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import unicorn; from dq4_pc.persistence import savestates as SS
        cls.SS = SS; eng = cls.eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_retour_titre_')); c = cls.c = eng.core
        eng.load_save(1)
        for _ in range(200): eng.step(0, 0)
        cls.part0 = eng.state.part; cls.map0 = eng.state.game_map
        def counter(name_str):
            addr = c.export(name_str); n = []; c.uc.hook_add(unicorn.UC_HOOK_CODE, lambda u, a, sz, ud: n.append(eng.frames), None, addr, addr); return n
        cls.title_screen = counter('_ZN6Global10startTitleEv'); cls.kill = counter('_ZN7profile8SaveLoad8killbankEib'); c.uc.ctl_flush_tb()
        cls.initial = SS.snapshot(eng)

    def setUp(self):
        self.SS.apply(self.eng, self.initial); self.eng.back_to_title_state = None; self.title_screen.clear(); self.kill.clear()

    def box(self): return self.c.export('gTownMenu_MESSAGE')
    def is_open(self): return bool(self.c.call(self.c.export('_ZN8MenuBase6isOpenEv'), self.box()) & 1)
    def answer(self): return struct.unpack('<I', self.c.mem(self.box() + ENGINE.MESSAGE_RESULT, 4))[0]

    def step(self, n=1, p=0, d=0):
        for _ in range(n): self.eng.step(p, d); self.eng.ui.damage = []; p = d = 0

    def key_press(self, pad):
        """Une touche de la manette envoyee au menu du moteur qui a la saisie (comme Game._menu_input : [1, -1, manette]), relachee a l'image suivante, puis 8 images de repos."""
        port = self.eng.active_menu(); self.assertIsNotNone(port, 'aucun menu du moteur n\'attend de touche')
        self.eng.send_menu(port, 1, -1, pad); self.step(1); self.eng.send_menu(port, 1, -1, 0); self.step(1); self.step(8)

    def open_box(self):
        self.assertTrue(self.eng.request_return_to_title()); self.step(150)                                    # le texte s'ecrit, puis Oui / Non
        self.assertEqual(self.eng.back_to_title_state, 'dialogue'); self.assertTrue(self.is_open()); self.assertEqual(self.answer(), 0); self.assertIsNotNone(self.eng.active_menu())           # Oui / Non attend

    def test_1_box_opens_and_waits(self):
        self.open_box(); self.step(120)
        self.assertEqual(self.eng.back_to_title_state, 'dialogue'); self.assertTrue(self.is_open()); self.assertEqual(self.title_screen, [])          # elle attend : rien ne se passe sans reponse

    def test_2_no_changes_nothing(self):
        self.open_box(); self.key_press(PAD_DOWN); self.key_press(PAD_A); self.step(30)
        self.assertIsNone(self.eng.back_to_title_state); self.assertFalse(self.is_open())
        self.assertEqual(self.title_screen, []); self.assertEqual(self.kill, [])                                      # ni banque effacee, ni titre
        self.assertEqual(self.eng.state.part, self.part0); self.assertEqual(self.eng.state.game_map, self.map0)
        self.assertLess(self.eng.state.fade['a'], 0.01)                                                        # aucun fondu

    def test_3_yes_starts_fade_then_title(self):
        self.open_box(); self.key_press(PAD_A)                                                          # le curseur d'origine est sur « Oui »
        alphas = []
        for _ in range(140): self.step(1); alphas.append(self.eng.state.fade['a'])
        self.assertEqual(len(self.title_screen), 1); self.assertEqual(len(self.kill), 1); self.assertLessEqual(self.kill[0], self.title_screen[0])        # banque 4 effacee puis titre, une fois chacun
        jumps = [b - a for a, b in zip(alphas, alphas[1:])]
        self.assertLess(max(jumps), 0.1, 'le fondu saute au noir : %.3f' % max(jumps))                      # progressif (un trente-troisieme par image), jamais d'un coup
        self.assertGreaterEqual(sum(1 for a in alphas if 0.05 < a < 0.95), 20)                               # une trentaine d'images de fondu
        self.assertGreater(max(alphas), 0.99)
        self.assertFalse(self.is_open())

    def test_4_request_after_no_is_possible(self):
        self.open_box(); self.key_press(PAD_DOWN); self.key_press(PAD_A); self.step(30)
        self.open_box()                                                                                   # et la meme question se pose de nouveau


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + REST)
