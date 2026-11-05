"""#237 (audit SND-01, sondage du 04/11/2026 : « aligner sur l'original ») : le volume de chaque son est celui de l'en-tete du fichier multiplie par `assets/sound/snd_vol.dat` (1171 flottants, indices = numero de fichier
BGM ou numero de bruitage), comme `SoundControl.Play` d'Unity : 49 musiques de 0,7 a 0,95 et la fanfare SE0409 a 0,6. Fichier absent ou indice hors table : 1,0.
Sans fenetre ni carte son (faux lecteurs, faux APK).
    python3 tests/test_sound_volumes.py"""
import os, sys, tempfile, unittest, zipfile
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


def apk_with(table):
    """Un faux APK (zip) qui contient assets/sound/snd_vol.dat (ou rien si table est None)."""
    f = os.path.join(tempfile.mkdtemp(prefix='apk_vol_'), 'faux.apk')
    with zipfile.ZipFile(f, 'w') as z:
        z.writestr('assets/readme.txt', 'x')
        if table is not None: z.writestr('assets/sound/snd_vol.dat', np.asarray(table, '<f4').tobytes())
    return f


def table_standard():
    t = np.ones(1171, np.float32); t[1] = 0.7; t[2] = 0.8; t[14] = 1.0; t[409] = 0.6
    return t


def new_sound(apk, **kw):
    s = SOUND.Sound(apk, tempfile.mkdtemp(prefix='cache_son_'), log=lambda *a: None, logfile=lambda *a: None, alert=lambda *a: None, **kw)
    s.ok = True; s.ogg = True; s.media = FakeMedia; s.AudioFormat = lambda **kw: kw; s.AudioData = None
    SOUND.LoopSource = FakeSource
    return s


def data(volume, looping=True, seconds=2.0):
    n = int(seconds * 1000)
    return dict(pcm=np.zeros((n, 1), np.int16), frequence=1000, debut=0, fin=n if looping else 0, volume=volume, boucle=looping)


class VolumeTable(unittest.TestCase):
    def test_read(self):
        s = new_sound(apk_with(table_standard()))
        for ident, v in ((1, 0.7), (2, 0.8), (14, 1.0), (409, 0.6), (300, 1.0), (1170, 1.0)): self.assertAlmostEqual(s.vol_snd(ident), v, 6, ident)

    def test_outside_table(self):
        s = new_sound(apk_with(table_standard()))
        for ident in (-1, 1171, 5000): self.assertEqual(s.vol_snd(ident), 1.0, ident)

    def test_missing_or_unreadable_file(self):
        self.assertEqual(new_sound(apk_with(None)).vol_snd(1), 1.0)
        self.assertEqual(new_sound('inexistant.apk').vol_snd(409), 1.0)
        self.assertEqual(new_sound(apk_with([0.5, 0.5, 0.5])).vol_snd(1), 0.5)               # (table plus courte : valable pour ses indices, 1,0 au-dela)
        self.assertEqual(new_sound(apk_with([0.5, 0.5, 0.5])).vol_snd(500), 1.0)

    def test_absurd_value_ignored(self):
        t = table_standard(); t[3] = 0.0; t[4] = 7.5; t[5] = float('nan'); t[6] = -1.0; s = new_sound(apk_with(t))
        for ident in (3, 4, 5, 6): self.assertEqual(s.vol_snd(ident), 1.0, ident)            # (0, > 1, nan, negatif : pas de silence ni de gain)

    def test_read_only_once(self):
        s = new_sound(apk_with(table_standard())); s.vol_snd(1); t = s._table_vol; s.vol_snd(2); self.assertIs(s._table_vol, t)


class PlayedVolume(unittest.TestCase):
    def test_music(self):
        s = new_sound(apk_with(table_standard()))
        s.bgm_request = 1; s._launch_bgm(1, data(0.65))
        self.assertAlmostEqual(s.bgm.volume, 0.65 * 0.7, 6); self.assertAlmostEqual(s.bgm_own_volume, 0.65 * 0.7, 6)
        s.bgm_request = 14; s._launch_bgm(14, data(0.9))
        self.assertAlmostEqual(s.bgm.volume, 0.9, 6)                                         # (BGM14 : 1,0, inchangee)

    def test_fanfare_sfx(self):
        s = new_sound(apk_with(table_standard()))
        s._launch_sfx(409, data(1.0, False)); self.assertAlmostEqual(s.sfx[-1].p.volume, 0.6, 6); self.assertAlmostEqual(s.sfx[-1].own, 0.6, 6)
        s._launch_sfx(300, data(1.0, False)); self.assertAlmostEqual(s.sfx[-1].p.volume, 1.0, 6)

    def test_sliders_and_options_stay_multiplied(self):
        s = new_sound(apk_with(table_standard()), music_volume=0.5)
        s.mix.game['musique'] = 0.8
        s.bgm_request = 2; s._launch_bgm(2, data(0.75))
        self.assertAlmostEqual(s.bgm.volume, 0.5 * 0.8 * 0.75 * 0.8, 6)                       # curseur x option du jeu x en-tete x snd_vol
        s.mix.vol['musique'] = 1.0; s._apply_volumes(); self.assertAlmostEqual(s.bgm.volume, 1.0 * 0.8 * 0.75 * 0.8, 6)      # (un reglage change plus tard garde le facteur du fichier)

    def test_without_table_nothing_changes(self):
        s = new_sound(apk_with(None)); s.bgm_request = 1; s._launch_bgm(1, data(0.65)); self.assertAlmostEqual(s.bgm.volume, 0.65, 6)


if __name__ == '__main__':
    unittest.main(verbosity=2)
