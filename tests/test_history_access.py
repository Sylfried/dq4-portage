"""Test (sans moteur ni affichage) de l'acces a l'historique (#187 : « l'historique doit pouvoir etre accessible uniquement quand j'ai le controle de mon perso, donc pas pendant un combat ni pendant un moment ou le jeu
prend le controle ») : `Game.player_control`, `Game.history_possible`, `Game._history_key`, la ligne « Historique » du menu Paramètres et la fermeture de la page quand le jeu reprend la main.

    python3 tools/test_history_access.py

  1. player_control : vrai seulement sur le terrain (ville, carte du monde) sans verrou du joueur (Global.Flag 4), message, menu du jeu, effet d'ecran, chargement ni combat ; un fondu seul (flag 1) n'y change rien ;
  2. history_possible : en plus, jamais a l'ecran titre ;
  3. touche H : ouvre la page quand c'est possible, sinon un message bref et aucune page ; la touche est branchee sur `_history_key` dans on_key_press (et plus sur l'ouverture directe) ;
  4. menu Paramètres : la ligne « Historique » est active / inactive (grisee, infobulle) selon `history_possible` ; sans cette methode (faux jeu minimal) elle reste active ;
  5. Pause.maj : page historique ouverte puis le jeu reprend la main (combat, dialogue, scene) : la page se ferme (retour a la racine, ou menu ferme si elle avait ete ouverte par la touche) avec un message ; tant que le joueur a la main, la liste suit le jeu (#178).
"""
import inspect, os, sys, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.window import game as F
from dq4_pc.menus import pause as PA
from dq4_pc.core import engine as ENGINE


def fake_game(part=ENGINE.PART_TOWN, flag=0, msg=False, menu=None, effect=None, waiting=None, guard=0, title_screen=None):
    """Ce que `player_control` lit du moteur et de la fenetre."""
    e = types.SimpleNamespace(part=part, effect=effect, load_wait=waiting, transition_guard=guard)
    eng = types.SimpleNamespace(state=e, msg_visible=msg, active_menu=lambda: menu, flags=lambda: flag)
    j = types.SimpleNamespace(engine=eng, title_screen=title_screen, calls=[])
    j._battle_clock = lambda: F.Game._battle_clock(j)
    j.player_control = lambda: F.Game.player_control(j)
    j.history_possible = lambda: F.Game.history_possible(j)
    j.pause = types.SimpleNamespace(open_menu=lambda page=None: j.calls.append(page))
    return j


class TestPlayerControl(unittest.TestCase):
    def test_player_free_on_terrain(self):
        for part in (ENGINE.PART_TOWN, ENGINE.PART_FIELD): self.assertTrue(F.Game.player_control(fake_game(part=part)), part)

    def test_not_in_battle(self):
        self.assertFalse(F.Game.player_control(fake_game(part=ENGINE.PART_BATTLE)))
        self.assertFalse(F.Game.player_control(fake_game(effect={'n': 3, 'duree': 57})), 'cascade d\'entree en combat')
        self.assertFalse(F.Game.player_control(fake_game(waiting=object())), 'ecran noir qui attend la scene du combat')
        self.assertFalse(F.Game.player_control(fake_game(guard=2)), 'entre deux fondus d\'un combat')

    def test_not_when_game_takes_control(self):
        self.assertFalse(F.Game.player_control(fake_game(flag=ENGINE.PLAYER_LOCKED_FLAG)), 'evenement, scene, dialogue, fondu de sortie : joueur verrouille')
        self.assertFalse(F.Game.player_control(fake_game(flag=ENGINE.PLAYER_LOCKED_FLAG | ENGINE.FADE_FLAG)))
        self.assertFalse(F.Game.player_control(fake_game(msg=True)), 'message visible')
        self.assertFalse(F.Game.player_control(fake_game(menu=3)), 'menu du jeu (commandes, boutique, Divers...)')

    def test_a_fade_alone_does_not_count(self):
        self.assertTrue(F.Game.player_control(fake_game(flag=ENGINE.FADE_FLAG)), 'fondu d\'arrivee ou de retour de combat, joueur libre (#107, #127)')
        self.assertTrue(F.Game.player_control(fake_game(flag=0x8 | 0x20)), 'autres bits de Global.Flag (manette, carte autorisee)')

    def test_other_parts(self):
        others = [p for p in (getattr(ENGINE, n) for n in dir(ENGINE) if n.startswith('PART_')) if p not in (ENGINE.PART_TOWN, ENGINE.PART_FIELD)]
        self.assertTrue(others)
        for p in others: self.assertFalse(F.Game.player_control(fake_game(part=p)), 'partie %r : ni ville ni carte du monde' % (p,))


class TestHistoryPossible(unittest.TestCase):
    def test_possible_when_free(self): self.assertTrue(F.Game.history_possible(fake_game()))
    def test_not_on_title_screen(self): self.assertFalse(F.Game.history_possible(fake_game(title_screen=object())))
    def test_not_in_battle_nor_dialogue(self):
        for kw in (dict(part=ENGINE.PART_BATTLE), dict(msg=True), dict(flag=ENGINE.PLAYER_LOCKED_FLAG), dict(menu=1)): self.assertFalse(F.Game.history_possible(fake_game(**kw)), kw)


class TestKey(unittest.TestCase):
    def test_opens_when_player_has_control(self):
        j = fake_game(); F.Game._history_key(j); self.assertEqual(j.calls, ['historique'])

    def test_does_nothing_without_message_otherwise(self):          # #194 : le joueur n'a pas a etre informe
        for kw in (dict(part=ENGINE.PART_BATTLE), dict(msg=True), dict(flag=ENGINE.PLAYER_LOCKED_FLAG)):
            j = fake_game(**kw); F.Game._history_key(j); self.assertEqual(j.calls, [], kw)

    def test_on_key_press_goes_through_the_rule(self):
        src = inspect.getsource(F.Game.on_key_press)
        i = src.index("action_of(symbol) == 'historique'"); line = src[i:src.index('\n', i)]
        self.assertIn('self._history_key()', line); self.assertNotIn("self.pause.ouvrir('historique')", line)


def menu(j, stack=None):
    p = PA.Pause.__new__(PA.Pause); p.J = j; p.opened = True; p.stack = stack or ['racine']; p.selected = {}; return p


def history_line(p):
    return next(entry for entry in p._entries_root() if entry.get('l') == 'Historique')


class TestMenu(unittest.TestCase):
    def test_line_active_when_player_has_control(self):
        p = menu(fake_game()); entry = history_line(p); self.assertFalse(PA.Pause._inactive(entry)); self.assertTrue(p._active(entry))

    def test_line_grayed_otherwise_with_tooltip(self):
        for kw in (dict(part=ENGINE.PART_BATTLE), dict(msg=True), dict(flag=ENGINE.PLAYER_LOCKED_FLAG), dict(menu=2)):
            p = menu(fake_game(**kw)); entry = history_line(p); self.assertTrue(PA.Pause._inactive(entry), kw); self.assertFalse(p._active(entry), kw)
            self.assertIn('main sur votre personnage', entry.get('aide', ''))

    def test_line_follows_game_state_each_frame(self):
        j = fake_game(); p = menu(j); self.assertFalse(PA.Pause._inactive(history_line(p)))
        j.engine.msg_visible = True; self.assertTrue(PA.Pause._inactive(history_line(p)))
        j.engine.msg_visible = False; self.assertFalse(PA.Pause._inactive(history_line(p)))

    def test_minimal_fake_game_keeps_active_line(self):
        p = menu(types.SimpleNamespace()); self.assertFalse(PA.Pause._inactive(history_line(p)))


class TestClosing(unittest.TestCase):
    """Pause.maj sur la page « historique » (les autres pages et `shutdown` sont remplaces par des espions)."""
    def pause(self, j, stack):
        p = menu(j, stack); p.calls = []; p.hist = types.SimpleNamespace(follow_game=lambda: p.calls.append('suit'))
        p.J.sound = types.SimpleNamespace(listening=False, listen=lambda e: None, tick=lambda: None)
        p.pan_fold_at = None; p.pan_pressed = None; p.rep = None
        p.shutdown = lambda: p.calls.append('ferme'); return p

    def test_follows_the_game_while_the_player_has_control(self):
        j = fake_game(); p = self.pause(j, ['racine', 'historique']); p.do_update(); self.assertEqual(p.calls, ['suit']); self.assertEqual(p.stack, ['racine', 'historique'])

    def test_game_regains_control_back_to_root(self):          # sans message (#194)
        for kw in (dict(part=ENGINE.PART_BATTLE), dict(msg=True), dict(flag=ENGINE.PLAYER_LOCKED_FLAG)):
            j = fake_game(); p = self.pause(j, ['racine', 'historique']); p.do_update(); self.assertEqual(p.stack, ['racine', 'historique'])
            for k, v in kw.items():
                if k == 'part': j.engine.state.part = v
                elif k == 'msg': j.engine.msg_visible = v
                elif k == 'flag': j.engine.flags = lambda v=v: v
            p.do_update(); self.assertEqual(p.stack, ['racine'], kw); self.assertNotIn('ferme', p.calls)

    def test_opened_by_key_menu_closes(self):
        j = fake_game(msg=True); p = self.pause(j, ['historique']); p.do_update(); self.assertEqual(p.calls, ['ferme'])

    def test_other_pages_are_not_touched(self):
        for page in ('racine', 'affichage', 'son', 'commandes'):
            j = fake_game(part=ENGINE.PART_BATTLE, msg=True); p = self.pause(j, ['racine'] + ([page] if page != 'racine' else [])); stack = list(p.stack); p.do_update()
            self.assertEqual(p.stack, stack, page)


if __name__ == '__main__':
    unittest.main(verbosity=2)
