"""#235 (audit UNI-02 et SND-07, sondage du 04/11/2026 : « pause a chaque perte de focus ») : quand la fenetre perd le focus (Alt + Tab, clic ailleurs, minimisation), le jeu s'arrete et la musique et les bruitages se
mettent en pause (Sound.SystemPause de l'original) ; au retour, le son repart la ou il s'etait arrete et le jeu reprend sans rattrapage.
- Son : `Sound.lose_focus` (faux lecteurs, sans fenetre ni carte son), y compris pendant l'ecoute de la page Son du menu et menu suspendu.
- Jeu : `Game.on_deactivate` / `on_activate` / `_loop` sur un faux Jeu (ignore si pyglet n'est pas importable : les tests Jeu ne tournent pas en CI).
    python3 tests/test_focus_loss.py"""
import os, sys, time, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np


class FakePlayer:
    def __init__(self): self.playing = True; self.volume = 1.0
    def play(self): self.playing = True
    def pause(self): self.playing = False
    def delete(self): self.playing = False


def new_sound():
    """Un Son sans pyglet (modules `pyglet` masque) avec de faux lecteurs : une musique et un bruitage en cours."""
    saved = sys.modules.get('pyglet', 0); sys.modules['pyglet'] = None
    try:
        from dq4_pc import sound as SOUND
        s = SOUND.Sound('inexistant.apk', '/tmp', log=lambda *a: None, logfile=lambda *a: None, alert=lambda *a: None)
    finally:
        if saved == 0: sys.modules.pop('pyglet', None)
        else: sys.modules['pyglet'] = saved
    s.ok = True
    s.bgm = FakePlayer(); s.bgm_end = time.time() + 30.0; s.bgm_t0 = time.time()
    s.sfx = [types.SimpleNamespace(p=FakePlayer(), end=time.time() + 5.0, category='effets', own=1.0)]
    return s


class SoundWithoutFocus(unittest.TestCase):
    def test_focus_loss_and_return(self):
        s = new_sound(); end = s.bgm_end
        s.lose_focus(True)
        self.assertFalse(s.bgm.playing); self.assertFalse(s.sfx[0].p.playing); self.assertIsNotNone(s.t_pause)
        time.sleep(0.05)
        s.lose_focus(False)
        self.assertTrue(s.bgm.playing); self.assertTrue(s.sfx[0].p.playing); self.assertIsNone(s.t_pause)
        self.assertGreater(s.bgm_end, end)                                        # (l'echeance de la musique est decalee de la duree de la pause)

    def test_idempotent(self):
        s = new_sound(); s.lose_focus(True); t = s.t_pause; s.lose_focus(True); self.assertEqual(s.t_pause, t)
        s.lose_focus(False); s.lose_focus(False); self.assertTrue(s.bgm.playing)

    def test_during_sound_page_listening(self):
        """La page Son du menu fait jouer les sons menu suspendu (`listening`) ; sans focus, rien ne joue quand meme, et le retour du focus rend la main a la page."""
        s = new_sound(); s.set_paused(True); s.listen(True)
        self.assertTrue(s.bgm.playing)                                            # (ecoute : on entend les reglages)
        s.lose_focus(True); self.assertFalse(s.bgm.playing)
        s.listen(True); self.assertFalse(s.bgm.playing)                          # (la page redemande l'ecoute : toujours muet)
        s.lose_focus(False); self.assertTrue(s.bgm.playing)                     # (retour : l'ecoute de la page reprend)

    def test_suspended_menu_remains_paused_on_return(self):
        s = new_sound(); s.set_paused(True); self.assertFalse(s.bgm.playing)
        s.lose_focus(True); s.lose_focus(False)
        self.assertFalse(s.bgm.playing)                                           # (le menu suspend encore le jeu : pas de reprise)
        s.set_paused(False); self.assertTrue(s.bgm.playing)

    def test_menu_closed_during_focus_loss(self):
        s = new_sound(); s.set_paused(True); s.lose_focus(True)
        s.set_paused(False); self.assertFalse(s.bgm.playing)                 # (toujours sans focus)
        s.lose_focus(False); self.assertTrue(s.bgm.playing)


class GameWithoutFocus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: from dq4_pc.window import game as window; cls.WND = window
        except Exception as ex: raise unittest.SkipTest('fenetre non importable ici (%r)' % (ex,))

    def fake_game(self):
        calls = []
        sound = types.SimpleNamespace(out_of_focus=False)
        def lose(yes): sound.out_of_focus = bool(yes); calls.append(bool(yes))
        sound.lose_focus = lose
        hud = types.SimpleNamespace(dpad_on=True, press_state='carte', dpad_drop=lambda: setattr(hud, 'dpad_on', False))
        wheel = types.SimpleNamespace(in_progress=True, cancel=lambda: setattr(wheel, 'in_progress', False))
        j = types.SimpleNamespace(_ready=True, _focus_lost=False, sound=sound, hud=hud, wheel=wheel, press_state=('p', 1, 2), hovered=[1], acc=0.7, t_loop=1.0, alpha=0.4, n_loop=0,
                                  args=types.SimpleNamespace(keys_test=False, shots_loop=False, options_test=False), hd_jobs={}, pad_prev=9, prev_action={'x': 1}, rep={'a': 1}, mouse=(3, 4),
                                  mouse_guard=types.SimpleNamespace(keyboard=lambda pos: calls.append(('garde', pos))), pad=lambda: 0, _held=lambda a: False, camera_oubliee=0)
        j._camera_oublier = lambda: setattr(j, 'camera_oubliee', j.camera_oubliee + 1)
        j.calls = calls
        return j

    def test_loss_of_focus(self):
        j = self.fake_game(); self.WND.Game.on_deactivate(j)
        self.assertTrue(j._focus_lost); self.assertEqual(j.calls, [True])
        self.assertFalse(j.wheel.in_progress); self.assertFalse(j.hud.dpad_on); self.assertIsNone(j.hud.press_state); self.assertIsNone(j.press_state); self.assertIsNone(j.hovered)      # (boutons de souris tenus : relaches)
        self.assertEqual(j.camera_oubliee, 1)                                      # (rotation de la camera demandee a la souris : abandonnee)

    def test_loop_frozen_without_focus(self):
        j = self.fake_game(); self.WND.Game.on_deactivate(j)
        j.acc = 0.7; j.alpha = 0.4; j.t_loop = 1.0; j.n_loop = 0
        self.WND.Game._loop(j, 0.016)                                              # (retourne avant tout pas du moteur : un faux Jeu n'a pas de moteur)
        self.assertEqual((j.acc, j.alpha, j.t_loop), (0.0, 1.0, None)); self.assertEqual(j.n_loop, 1)

    def test_loop_pauses_sound_if_event_came_before_loading(self):
        j = self.fake_game(); j._ready = False; self.WND.Game.on_deactivate(j)
        self.assertTrue(j._focus_lost); self.assertEqual(j.calls, [])           # (rien n'existe encore : pas d'appel)
        j._ready = True; self.WND.Game._loop(j, 0.016); self.assertEqual(j.calls, [True])

    def test_focus_regained(self):
        j = self.fake_game(); self.WND.Game.on_deactivate(j); j.acc = 0.3; j.t_loop = 5.0; j.rep = {'a': 1}
        self.WND.Game.on_activate(j)
        self.assertFalse(j._focus_lost); self.assertEqual(j.calls[-2:], [False, ('garde', (3, 4))]); self.assertEqual((j.acc, j.t_loop), (0.0, None)); self.assertEqual(j.rep, {})
        self.assertEqual(j.pad_prev, 0)                                            # (les touches tenues au retour ne sont pas un nouvel appui)

    def test_return_before_loading(self):
        j = self.fake_game(); j._ready = False; j._focus_lost = True; self.WND.Game.on_activate(j)
        self.assertFalse(j._focus_lost); self.assertEqual(j.calls, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
