"""Tests objectifs (sans fenetre) de la vitesse du texte et du defilement des messages de combat.

Le moteur d'origine tourne sous Unicorn ; on compte des IMAGES DU MOTEUR (30 par seconde), pas du temps :
  - texte : images entre l'ouverture d'un message de dialogue (ui_MsgLoop actif) et la fin de l'ecriture de sa premiere page (etat 3 ou 5 : attente d'une touche) ;
  - defilement : images pendant lesquelles un message de combat attend avant de passer seul au suivant (ui_MsgLoop etat 5 sans menu de commandes), selon OptionStatus.battleSpeed.

Usage (depuis la racine du depot) :
    python3 tools/test_text_scrolling.py --apk "<dossier des APK patches>" --saves "<dossier des sauvegardes>" [--slot 4]
Les sauvegardes ne sont ouvertes qu'en lecture : le moteur ecrit dans un dossier temporaire.
"""
import argparse, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.core import engine as ENGINE

ARGS = None
SPEEDS = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 4000.0)


def start_engine(slot):
    eng = ENGINE.Engine(ARGS.apk, ARGS.saves, tempfile.mkdtemp(prefix='sv_test_texte_'))
    for _ in range(3): eng.step(0, 0)
    eng.load_save(slot)
    return eng


def text_frames(speed, slot):
    """(images entre l'ouverture du message et la fin de sa premiere page, lettres de la page)."""
    eng = start_engine(slot); eng.text_speed = speed
    for _ in range(70): eng.step(0, 0)
    eng.step(0, 0x800)                                               # menu de commandes -> « Parler » : le message de la scene s'ouvre
    t_open = None; ok = 0
    for i in range(1500):
        p = eng.active_menu()
        if eng.msg_visible: pass
        elif p is not None and i % 14 == 4 and ok < 4: eng.send_menu(p, 1, -1, 0x10); ok += 1
        elif p is not None and i % 14 == 5: eng.send_menu(p, 1, -1, 0)
        eng.step(0, 0)
        active, state, _, end, _ = eng.message_state()
        if active == 1 and t_open is None: t_open = eng.frames
        if t_open is not None and state in (3, 5): return eng.frames - t_open, end
    return None, None


def enter_battle(eng):
    for i in range(100): eng.step(0, 0x10 if i % 10 == 0 else 0)
    if eng.state.part != ENGINE.PART_FIELD:
        eng.start_field()
        for i in range(120): eng.step(0, 0)
    c = eng.core
    c.call(eng.E('_ZN7Encount12forceEncountEv'), c.call(eng.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
    for i in range(600):
        eng.step([0x4, 0x8][(i // 20) % 2], 0)
        if eng.state.part == ENGINE.PART_BATTLE: return True
    return False


def battle_waits(code, slot, n=900):
    """Attentes (en images) des messages de combat qui passent seuls, defilement impose = code. Renvoie (liste des attentes, option du jeu a la fin)."""
    eng = start_engine(slot); eng.impose_scroll_mode(code)
    assert enter_battle(eng), 'pas de combat'
    t5 = None; menu_vu = False; res = []
    for i in range(n):
        p = eng.active_menu()
        if p is not None and i % 15 == 0: eng.send_menu(p, 1, -1, 0x10)
        elif p is not None and i % 15 == 1: eng.send_menu(p, 1, -1, 0)
        eng.step(0, 0)
        state = eng.message_state()[1]
        if p is not None: menu_vu = True
        if state == 5 and t5 is None: t5 = eng.frames; menu_vu = p is not None
        elif state != 5 and t5 is not None:
            if not menu_vu: res.append(eng.frames - t5)
            t5 = None
        if eng.state.part != ENGINE.PART_BATTLE and i > 100: break
    return res, eng.game_options()[2]


def manual_waits_for_key(slot):
    """Defilement a la main : un message de combat reste affiche tant qu'on n'appuie pas (150 images sans touche), puis passe a la touche A."""
    eng = start_engine(slot); eng.impose_scroll_mode(ENGINE.BATTLE_MANUAL)
    assert enter_battle(eng), 'pas de combat'
    t5 = None
    for i in range(900):
        p = eng.active_menu()
        if p is not None and i % 15 == 0: eng.send_menu(p, 1, -1, 0x10)
        elif p is not None and i % 15 == 1: eng.send_menu(p, 1, -1, 0)
        eng.step(0, 0)
        if eng.message_state()[1] == 5 and p is None and eng.active_menu() is None:
            t5 = t5 or eng.frames
            if eng.frames - t5 >= 150: break
        else: t5 = None
    else: return None
    for _ in range(150): eng.step(0, 0)                                  # (le message ne doit toujours pas bouger : la boucle ci-dessus avait deja attendu 150 images)
    remainder = eng.message_state()[1] == 5
    eng.step(0, 0x10)
    for _ in range(40): eng.step(0, 0)
    return remainder, eng.message_state()[1] != 5 or eng.active_menu() is not None


def dialogue_outside_battle(code, slot):
    """Un message de dialogue (hors combat) attend la touche 400 images meme avec le defilement automatique de la sauvegarde : renvoie True s'il n'est pas passe seul."""
    eng = start_engine(slot); eng.impose_scroll_mode(code)
    for _ in range(70): eng.step(0, 0)
    eng.step(0, 0x800); ok = 0; t5 = None
    for i in range(1500):
        p = eng.active_menu()
        if eng.msg_visible: pass
        elif p is not None and i % 14 == 4 and ok < 4: eng.send_menu(p, 1, -1, 0x10); ok += 1
        elif p is not None and i % 14 == 5: eng.send_menu(p, 1, -1, 0)
        eng.step(0, 0)
        state = eng.message_state()[1]
        if state == 5 and t5 is None: t5 = eng.frames
        if t5 is not None:
            if state != 5: return False
            if eng.frames - t5 >= 400: return True
    return None


class TextAndScroll(unittest.TestCase):
    def test_text_speed(self):
        mesures = {v: text_frames(v, ARGS.slot) for v in SPEEDS}
        for v, (n, letters) in mesures.items(): print('vitesse %6.1f lettres/image : %4s images (%s lettres)' % (v, n, letters))
        frames = [mesures[v][0] for v in SPEEDS]
        self.assertTrue(all(n is not None for n in frames))
        self.assertEqual(frames, sorted(frames, reverse=True), 'plus la vitesse monte, moins il faut d\'images')
        self.assertGreater(frames[0], 4 * frames[3], 'x1/8 de la vitesse du jeu : au moins 4 fois plus long')
        self.assertLessEqual(frames[-1], frames[3] // 2, 'instantane : au plus la moitie du temps du jeu')
        letters = mesures[4.0][1]
        for v in (0.5, 1.0, 2.0):                                         # ecriture lente : le temps est dans les lettres, a l'image pres
            self.assertAlmostEqual(mesures[v][0], letters / v, delta=letters / v * 0.08 + 6)

    def test_battle_scrolling(self):
        expected = {0: 12, 1: 22, 2: 32, 3: 42}                            # BattleAutoFeed::setMessageSpeed : attente en images selon OptionStatus.battleSpeed
        for code, n in expected.items():
            res, option = battle_waits(code, ARGS.slot)
            print('defilement %d : attentes %s' % (code, res))
            self.assertEqual(option, code)
            self.assertGreaterEqual(len(res), 3)
            self.assertEqual(min(res), n)
        res, option = battle_waits(ENGINE.BATTLE_MANUAL, ARGS.slot)
        print('defilement manuel : attentes %s' % (res,))
        self.assertEqual(res, [], 'a la main : aucun message ne passe seul')

    def test_manual_waits_for_key(self):
        r = manual_waits_for_key(ARGS.slot)
        print('manuel : message encore la apres 300 images sans touche = %s, passe a la touche A = %s' % r if r else 'manuel : pas de message mesurable')
        self.assertIsNotNone(r)
        self.assertTrue(r[0] and r[1])

    def test_dialogue_outside_battle_never_automatic(self):
        for code in (0, 2):
            self.assertTrue(dialogue_outside_battle(code, ARGS.slot), 'defilement %d : le dialogue ne doit pas passer seul' % code)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apk', required=True); ap.add_argument('--saves', required=True); ap.add_argument('--slot', type=int, default=4)
    ARGS, remainder = ap.parse_known_args()
    unittest.main(argv=[sys.argv[0]] + remainder, verbosity=2)
