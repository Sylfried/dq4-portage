"""Test de la priorite du jeu sur les reglages du joueur : « quand le jeu fixe lui-meme une valeur par script, il prime sur le reglage du joueur ».

  1. regles pures (game_priority.py) : effective_value, effective_factor, letters_per_frame, fade_duration ;
  2. vitesse de marche (`Game._speed_factor`, sur un faux objet) : sans effet pendant un evenement (verrou du joueur, dont le fondu de sortie), appliquee en terrain libre et pendant le fondu d'arrivee (#107) ;
  3. moteur d'origine (si --apk et --saves sont donnes) : vitesse du texte fixee par le jeu (le mot de vitesse du message est modifie en cours de route) ; fondu lance par une commande de script du jeu
     (la sauvegarde --slot-fondu, par defaut 2 : debut du prologue, commande fade_out de 30 images) non raccourci, fondu du moteur raccourci.

    python3 tools/test_game_priority.py [--apk "<dossier des APK patches>" --saves "<dossier des sauvegardes>" [--slot 4] [--slot-fondu 2]]
Les sauvegardes ne sont ouvertes qu'en lecture : le moteur ecrit dans un dossier temporaire.
"""
import argparse, os, sys, tempfile, types, unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.core import game_priority as PJ
from dq4_pc.core import engine as ENGINE
from dq4_pc.window import game as F

ARGS = None


class PureRules(unittest.TestCase):
    def test_effective_value(self):
        for player, game in ((4.0, None), (16.0, None), (0.5, 8), (4000.0, 0), (0, 0.0), (None, 3)):
            self.assertEqual(PJ.effective_value(player, game), player if game is None else game, (player, game))
        self.assertEqual(PJ.effective_value(16.0), 16.0)
        self.assertEqual(PJ.effective_value(16.0, 0), 0, 'une valeur du jeu egale a zero est une valeur du jeu')

    def test_effective_factor(self):
        self.assertEqual(PJ.effective_factor(2.0, False), 2.0)
        self.assertEqual(PJ.effective_factor(2.0, True), 1.0)
        self.assertEqual(PJ.effective_factor(0.5, True), 1.0)
        self.assertEqual(PJ.effective_factor(3.0, True, neutral=1.5), 1.5)

    def test_letters_per_frame(self):
        for player in (0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 4000.0):
            self.assertEqual(PJ.letters_per_frame(player, PJ.STANDARD_LETTERS), player, 'dialogue ordinaire : le reglage du joueur')
            self.assertEqual(PJ.letters_per_frame(player, 400), 400, 'fenetre de combat (vitesse 100) : celle du jeu')
            self.assertEqual(PJ.letters_per_frame(player, 8), 8, 'vitesse fixee par le jeu (mot 2) : celle du jeu, quel que soit le reglage')
            self.assertEqual(PJ.letters_per_frame(player, 2), 2, 'vitesse fixee par le jeu (mot 0,5) : plus lente que le standard, elle prime aussi')
        self.assertEqual(PJ.letters_per_frame(16.0, 8, standard=8), 16.0, 'un autre standard (autre jeu) : le reglage s\'applique a celui-la')

    def test_fade_duration(self):
        for duration, factor, expected in ((30, 1.0, 30), (30, 2.0, 15), (45, 2.0, 22), (60, 4.0, 15), (1, 4.0, 1), (0, 4.0, 0), (3, 4.0, 1), (30, 0.5, 30)):
            self.assertEqual(PJ.fade_duration(duration, factor), expected, (duration, factor))
            self.assertEqual(PJ.fade_duration(duration, factor, script=True), duration, 'fondu de script : duree du script')
        self.assertEqual(PJ.fade_duration(30, 2.0, script=False), 15)

    def test_mark_outside_packet_fields(self):
        """La marque des fondus de script n'empiete sur aucun champ de l'entier du paquet 9 (duree 0x7ff, couleur 0x800, sortie 0x1000, blanc 0x2000, plan de fond 0x4000)."""
        self.assertEqual(PJ.SCRIPT_FADE_MARK & 0x7fff, 0)
        e = ENGINE.State(); ENGINE.State.fade_speed = 2.0
        try:
            e._fade(0x1000 | 30, ()); self.assertEqual(e.fade['n'], 15, 'fondu du moteur raccourci')
            e._fade(0x1000 | 30 | PJ.SCRIPT_FADE_MARK, ()); self.assertEqual(e.fade['n'], 30, 'fondu de script : intact')
            e._fade(0x5000 | 30 | PJ.SCRIPT_FADE_MARK, ()); self.assertEqual(e.background_fade['n'], 30); self.assertEqual(e.background_fade['fin'], 1.0, 'les autres champs sont lus comme avant')
            e._fade(0x1000 | 0x800 | 30, (0.1, 0.2, 0.3)); self.assertEqual(e.fade['n'], 30, 'fondu en couleur : jamais raccourci'); self.assertEqual(e.fade['col'], (0.1, 0.2, 0.3))
        finally: ENGINE.State.fade_speed = 1.0


def fake_game_walk(walk=2.0, accel=1.5, flags=0x28, msg=False, part=ENGINE.PART_TOWN, direction=ENGINE.RIGHT, accel_held=False, transition_guard=0):
    eng = types.SimpleNamespace(state=types.SimpleNamespace(part=part, effect=None, load_wait=None, transition_guard=transition_guard, battle_transition=lambda: False), msg_visible=msg, active_menu=lambda: None, flags=lambda: flags)
    return types.SimpleNamespace(reg={'vitesse_marche': walk, 'vitesse_accel': accel}, engine=eng, pad=lambda: direction, _held=lambda a: accel_held and a == 'accel', hud=types.SimpleNamespace(dpad_run=lambda: False), pause=types.SimpleNamespace(opened=False), _battle_clock=lambda: False)           # (hors combat : la branche « vitesse des combats » de Game._speed_factor ne joue pas)


class WalkSpeed(unittest.TestCase):
    def factor(self, **kw): return F.Game._speed_factor(fake_game_walk(**kw))

    def test_free_field(self):
        self.assertEqual(self.factor(), 2.0)
        self.assertEqual(self.factor(accel_held=True), 3.0, 'accelerateur tenu : x2 x 1,5')
        self.assertEqual(self.factor(flags=0x28 | 0x40), 2.0, 'verrou de l\'interface seul (bit 0x40) : sans effet ici')

    def test_game_has_control(self):
        self.assertEqual(self.factor(flags=0x28 | 0x4), 1.0, 'verrou du joueur (evenement, scene) sans message : marche non acceleree')
        self.assertEqual(self.factor(flags=0x3c, accel_held=True), 1.0)
        self.assertEqual(self.factor(flags=0x28 | 0x5), 1.0, 'fondu de sortie (joueur verrouille) : non acceleree')
        self.assertEqual(self.factor(flags=0x3d), 1.0)

    def test_arrival_fade_player_free(self):
        """#107 : le fondu d'arrivee sur une carte (flag 1 seul, le heros marche deja) n'empeche plus la marche acceleree (mesure : flags 0x39 pendant les 30 images, 0x3d + verrou pendant le fondu de sortie)."""
        self.assertEqual(self.factor(flags=0x39), 2.0)
        self.assertEqual(self.factor(flags=0x39, accel_held=True), 3.0, 'accelerateur tenu des la premiere image apres la porte')

    def test_return_from_battle_player_free(self):
        """#127 : au retour d'un combat le fondu de retour dure 30 images mais le joueur est libre des l'image 12 (mesure sur le vrai moteur : flags 0x2d jusqu'a l'image 11, puis 0x29, le heros marche des l'image 13) :
        la marche acceleree et l'accelerateur (course) agissent des que le verrou tombe, et non a la fin du fondu."""
        self.assertEqual(self.factor(flags=0x29), 2.0)
        self.assertEqual(self.factor(flags=0x29, accel_held=True), 3.0, 'course tenue des la fin du verrou, fondu de retour encore en cours')
        self.assertEqual(self.factor(flags=0x2d, accel_held=True), 1.0, 'joueur verrouille (images 1 a 11 du retour) : horloge du jeu')

    def test_between_two_battle_fades(self):
        """Le moteur change de scene 1 a 3 images apres la sortie au noir (State.transition_guard) : horloge du jeu, meme si le verrou n'est pas encore pose (image 0 du retour : flags 0x1)."""
        self.assertEqual(self.factor(flags=0x1, transition_guard=5, accel_held=True), 1.0)
        self.assertEqual(self.factor(flags=0x29, transition_guard=0, accel_held=True), 3.0)

    def test_unchanged(self):
        self.assertEqual(self.factor(msg=True), 1.0)
        self.assertEqual(self.factor(part=ENGINE.PART_BATTLE), 1.0)
        self.assertEqual(self.factor(direction=0), 1.0, 'aucune direction tenue')
        self.assertEqual(self.factor(walk=1.0, accel=1.0), 1.0)


def text_word_frames(speed, game_word, slot):
    """Comme test_text_scrolling.text_frames, mais le mot de vitesse de la fenetre de message est ecrit a `game_word` (un script du jeu qui fixe la vitesse) des l'ouverture du message ; None = non touche.
    Renvoie (images entre l'ouverture du message et la fin de sa premiere page, lettres de la page)."""
    eng = ENGINE.Engine(ARGS.apk, ARGS.saves, tempfile.mkdtemp(prefix='sv_test_prio_'))
    for _ in range(3): eng.step(0, 0)
    eng.load_save(slot); eng.text_speed = speed
    for _ in range(70): eng.step(0, 0)
    eng.step(0, 0x800)
    t_open = None; ok = 0
    for i in range(1500):
        p = eng.active_menu()
        if eng.msg_visible: pass
        elif p is not None and i % 14 == 4 and ok < 4: eng.send_menu(p, 1, -1, 0x10); ok += 1
        elif p is not None and i % 14 == 5: eng.send_menu(p, 1, -1, 0)
        if game_word is not None and t_open is not None: eng.core.mem_w(eng.L + ENGINE.MSG_SPEED, int(game_word).to_bytes(2, 'little'))
        eng.step(0, 0)
        active, state, _, end, word = eng.message_state()
        if active == 1 and t_open is None:
            t_open = eng.frames
            if game_word is not None: eng.core.mem_w(eng.L + ENGINE.MSG_SPEED, int(game_word).to_bytes(2, 'little'))
        if t_open is not None and state in (3, 5): return eng.frames - t_open, end
    return None, None


def prologue_fades(factor, slot, n=450):
    """[(image, duree d'origine, duree appliquee, fondu de script ?)] des fondus au noir du moteur depuis le chargement de la sauvegarde `slot`."""
    eng = ENGINE.Engine(ARGS.apk, ARGS.saves, tempfile.mkdtemp(prefix='sv_test_prio_'))
    for _ in range(3): eng.step(0, 0)
    res = []; orig = ENGINE.State._fade
    def spy(self, v, f):
        r = orig(self, v, f)
        if not v & (0x800 | 0x2000): res.append((eng.frames, v & 0x7ff, (self.background_fade if v & 0x4000 else self.fade)['n'] if (v & 0x7ff) > 1 else 0, bool(v & PJ.SCRIPT_FADE_MARK)))
        return r
    ENGINE.State._fade = spy; ENGINE.State.fade_speed = factor
    try:
        eng.load_save(slot)
        for i in range(n): eng.step(0, 0x10 if i % 40 == 0 else 0)
    finally: ENGINE.State._fade = orig; ENGINE.State.fade_speed = 1.0
    return res


@unittest.skipIf(ARGS is None and '--apk' not in sys.argv, 'moteur d\'origine : --apk et --saves requis')
class Engine(unittest.TestCase):
    def test_text_fixed_by_the_game(self):
        """Mot de vitesse fixe par le jeu (2 = 8 lettres par image) : meme duree quel que soit le reglage du joueur ; sans cela le reglage s'applique."""
        without = {v: text_word_frames(v, None, ARGS.slot)[0] for v in (0.5, 16.0)}
        has_tab = {v: text_word_frames(v, 2, ARGS.slot) for v in (0.5, 4.0, 16.0, 4000.0)}
        print('reglage seul : %s ; mot fixe a 2 par le jeu : %s' % (without, has_tab))
        self.assertGreater(without[0.5], 3 * without[16.0], 'sans valeur du jeu, le reglage change la duree')
        self.assertEqual(len({n for n, _ in has_tab.values()}), 1, 'le jeu a fixe sa vitesse : le reglage du joueur n\'y change rien')
        equivalent = text_word_frames(8.0, None, ARGS.slot)                  # reglage du joueur = 8 lettres par image, rien fixe par le jeu : la meme duree que le mot 2 du jeu
        self.assertEqual(has_tab[4.0], equivalent, 'la vitesse du jeu (mot 2 = 8 lettres par image) est bien celle qui s\'applique : %s contre %s' % (has_tab[4.0], equivalent))

    def test_script_fade(self):
        raw_value = prologue_fades(1.0, ARGS.slot_fondu); fast = prologue_fades(4.0, ARGS.slot_fondu)
        print('fondus x1 : %s\nfondus x4 : %s' % (raw_value, fast))
        self.assertTrue(any(s for _, _, _, s in raw_value), 'un fondu lance par un script du jeu est reconnu (fade_out du debut du prologue)')
        self.assertTrue(any(not s and d > 4 for _, d, _, s in raw_value), 'et des fondus du moteur aussi')
        for (_, d, ap, s), (_, d4, ap4, s4) in zip(raw_value, fast):
            self.assertEqual((d, s), (d4, s4))
            self.assertEqual(ap, d if d > 1 else 0, 'x1 : duree d\'origine')
            if s: self.assertEqual(ap4, ap, 'fondu de script : jamais raccourci')
            elif d > 1: self.assertEqual(ap4, max(1, round(d / 4.0)), 'fondu du moteur : divise par 4')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apk'); ap.add_argument('--saves'); ap.add_argument('--slot', type=int, default=4); ap.add_argument('--slot-fondu', type=int, default=2, dest='slot_fondu')
    ARGS, remainder = ap.parse_known_args()
    if not (ARGS.apk and ARGS.saves): ARGS = None
    unittest.main(argv=[sys.argv[0]] + remainder, verbosity=2)
