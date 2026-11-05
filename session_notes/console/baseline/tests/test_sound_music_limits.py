"""#229 (audit SND-05 et SND-06) : deux cas limites de la musique, comme dans le jeu d'origine (Sound.StopBGM / PlayBGM de SoundControl).
- Un arret de la musique PENDANT un jingle lance avec reprise (0x1000 | n) ne remet pas l'etat du jingle a zero dans Unity : la musique d'avant repart (depuis le debut). Sans jingle en cours, l'arret arrete.
- Un morceau sans boucle arrive a sa fin n'est plus « en cours » : le redemander le relance. Un morceau en train de jouer (en boucle ou non) redemande n'est pas relance (le moteur ne le redemande pas).
Sans fenetre ni carte son (faux lecteurs).
    python3 tests/test_sound_music_limits.py"""
import os, sys, time, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.modules['pyglet'] = None                                             # pas de pyglet : Son le prend pour « son indisponible », on lui donne de faux lecteurs
from dq4_pc import sound as SOUND


class FakePlayer:
    def __init__(self): self.playing = False; self.volume = 1.0
    def queue(self, src): pass
    def play(self): self.playing = True
    def pause(self): self.playing = False
    def delete(self): self.playing = False


class FakeMedia:
    Player = FakePlayer


class FakeSource:
    def __init__(self, *a): self.pos = 0


def data(seconds, looping):
    n = int(seconds * 1000)
    return dict(pcm=np.zeros((n, 1), np.int16), frequence=1000, debut=n // 4 if looping else 0, fin=n if looping else 0, volume=1.0, boucle=looping)


def new_sound():
    s = SOUND.Sound('inexistant.apk', '/tmp', log=lambda *a: None, logfile=lambda *a: None, alert=lambda *a: None)
    s.ok = True; s.ogg = True; s.media = FakeMedia; s.AudioFormat = lambda **kw: kw; s.AudioData = None
    SOUND.LoopSource = FakeSource
    s.dec['BGM02'] = data(60.0, True)                    # musique en boucle
    s.dec['BGM01'] = data(5.0, False)                    # musique sans boucle (comme BGM 1 et 34)
    s.dec['BGM48'] = data(3.0, False)                    # jingle (coffre)
    return s


RESTART = SOUND.BGM_RESTART; STOP = SOUND.BGM_STOP


class StopDuringJingle(unittest.TestCase):
    def test_stop_during_jingle_with_resume_previous_music_restarts(self):
        s = new_sound(); s.play_bgm(2); s.play_bgm(RESTART | 48)
        self.assertEqual(s.bgm_id, 48); self.assertEqual(s.resume, 2)
        p = s.bgm; s.play_bgm(STOP | 4)
        self.assertEqual(s.bgm_id, 2); self.assertIsNotNone(s.bgm); self.assertIsNot(s.bgm, p); self.assertIsNone(s.resume); self.assertIsNone(s.bgm_end)      # (la musique d'avant, en boucle, depuis le debut)

    def test_stop_without_jingle_stops(self):
        s = new_sound(); s.play_bgm(2); s.play_bgm(STOP | 4)
        self.assertIsNone(s.bgm_id); self.assertIsNone(s.bgm); self.assertIsNone(s.resume)

    def test_stop_after_jingle_end_stops_resumed_music(self):
        s = new_sound(); s.play_bgm(2); s.play_bgm(RESTART | 48)
        s.bgm_end = time.time() - 1.0; s.tick()                                    # fin du jingle : la musique d'avant reprend toute seule
        self.assertEqual(s.bgm_id, 2); self.assertIsNone(s.resume)
        s.play_bgm(STOP | 4); self.assertIsNone(s.bgm_id); self.assertIsNone(s.bgm)

    def test_jingle_without_prior_music_then_stop_stays_mute(self):
        s = new_sound(); s.play_bgm(RESTART | 48); self.assertIsNone(s.resume)
        s.play_bgm(STOP | 4); self.assertIsNone(s.bgm_id); self.assertIsNone(s.bgm)

    def test_two_stops_in_a_row(self):
        s = new_sound(); s.play_bgm(2); s.play_bgm(RESTART | 48); s.play_bgm(STOP | 4); s.play_bgm(STOP | 4)          # (le premier relance la musique, le second l'arrete)
        self.assertIsNone(s.bgm_id); self.assertIsNone(s.bgm)

    def test_a_new_order_after_the_stop(self):
        s = new_sound(); s.play_bgm(2); s.play_bgm(RESTART | 48); s.play_bgm(STOP | 4); s.play_bgm(1)
        self.assertEqual(s.bgm_id, 1); self.assertIsNone(s.resume)


class SameMusicRequestedAgain(unittest.TestCase):
    def test_playing_loop_is_not_restarted(self):
        s = new_sound(); s.play_bgm(2); p = s.bgm; s.play_bgm(2); self.assertIs(s.bgm, p)

    def test_without_loop_a_running_music_is_not_restarted(self):
        s = new_sound(); s.play_bgm(1); p = s.bgm; s.play_bgm(1); self.assertIs(s.bgm, p)

    def test_without_loop_a_finished_music_is_restarted(self):
        s = new_sound(); s.play_bgm(1); p = s.bgm; s.bgm_end = time.time() - 1.0
        s.play_bgm(1); self.assertIsNot(s.bgm, p); self.assertEqual(s.bgm_id, 1); self.assertGreater(s.bgm_end, time.time() + 3.0)

    def test_paused_track_is_not_finished(self):
        s = new_sound(); s.play_bgm(1); p = s.bgm; s.bgm_end = time.time() - 1.0; s.t_pause = time.time()
        s.play_bgm(1); self.assertIs(s.bgm, p)

    def test_another_music_always_replaces(self):
        s = new_sound(); s.play_bgm(2); p = s.bgm; s.play_bgm(1); self.assertEqual(s.bgm_id, 1); self.assertIsNot(s.bgm, p)


if __name__ == '__main__':
    unittest.main(verbosity=1)
