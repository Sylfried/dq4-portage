"""#221 (audit SND-10 et SND-12) : un echec de lecture ne coupe plus le son jusqu'a la fermeture du jeu : FAILURES_MAX echecs de suite le coupent un moment, nouvel essai tout seul (delais croissants), la musique
demandee pendant la coupure est relancee au retour, tout est note dans le journal ; les erreurs avalees (volumes, reprise apres pause) sont notees une fois. Sans fenetre ni carte son (faux lecteurs).
    python3 tests/test_sound_failures.py"""
import os, sys, time, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc import language as _LANGUAGE; _LANGUAGE.select_language('fr')          # (D-238 : ces tests attendent les textes francais, quelle que soit la langue de l'ordinateur)
sys.modules['pyglet'] = None                                             # pas de pyglet : Son le prend pour « son indisponible », on lui donne de faux lecteurs
from dq4_pc import sound as SOUND


class Outage:
    broken = False                                                     # vrai : tout nouveau lecteur refuse de jouer (peripherique retire)
    volume_refused = False


class FakePlayer:
    def __init__(self): self.playing = False; self._volume = 1.0
    @property
    def volume(self): return self._volume
    @volume.setter
    def volume(self, v):
        if Outage.volume_refused: raise OSError('volume refuse')
        self._volume = v
    def queue(self, src): pass
    def play(self):
        if Outage.broken: raise OSError('peripherique retire')
        self.playing = True
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
    Outage.broken = False; Outage.volume_refused = False
    logfile, alerts = [], []
    s = SOUND.Sound('inexistant.apk', '/tmp', log=lambda *a: None, logfile=logfile.append, alert=alerts.append)
    s.ok = True; s.ogg = True; s.media = FakeMedia; s.AudioFormat = lambda **kw: kw; s.AudioData = None
    SOUND.LoopSource = FakeSource
    for i in (300, 316, 400): s.dec['SE%04d' % i] = data(1.0, False)
    s.dec['BGM02'] = data(60.0, True); s.dec['BGM05'] = data(60.0, True)
    return s, logfile, alerts


class Failures(unittest.TestCase):
    def test_normal_operation_without_trace(self):
        s, j, a = new_sound()
        s.play_sfx(300); s.play_bgm(2); s.play_sfx(316)
        self.assertTrue(s.ok); self.assertEqual((s.failures, s.outages, j, a), (0, 0, [], []))

    def test_one_or_two_failures_do_not_cut(self):
        s, j, a = new_sound(); Outage.broken = True
        s.play_sfx(300); s.play_sfx(316)
        self.assertTrue(s.ok); self.assertEqual(s.failures, 2); self.assertEqual(len(j), 2); self.assertEqual(a, [])
        Outage.broken = False; s.play_sfx(400)                                     # un son qui part remet le compteur a zero
        self.assertEqual(s.failures, 0); self.assertTrue(s.ok); self.assertEqual(a, [])

    def test_three_failures_in_a_row_cut_then_retry(self):
        s, j, a = new_sound(); Outage.broken = True
        for i in (300, 316, 400): s.play_sfx(i)
        self.assertFalse(s.ok); self.assertIsNotNone(s.retry); self.assertEqual(len(a), 1); self.assertIn('interrompu', a[0])
        self.assertTrue(any('interrupted' in l for l in j)); self.assertAlmostEqual(s.retry - time.time(), SOUND.RETRY_DELAYS[0], delta=0.5)
        s.tick(); self.assertFalse(s.ok)                                            # trop tot : rien
        s.retry = time.time() - 1; s.tick()                                       # delai ecoule : le son est rouvert
        self.assertTrue(s.ok); self.assertIsNone(s.retry); self.assertEqual(s.failures, SOUND.FAILURES_MAX - 1)
        s.play_sfx(300)                                                             # toujours en panne : un seul echec recoupe, delai plus long
        self.assertFalse(s.ok); self.assertAlmostEqual(s.retry - time.time(), SOUND.RETRY_DELAYS[1], delta=0.5)
        s.retry = time.time() - 1; s.tick(); Outage.broken = False              # la sortie est revenue
        s.play_sfx(300)
        self.assertTrue(s.ok); self.assertEqual(s.failures, 0); self.assertEqual(len(a), 3); self.assertIn('rétabli', a[-1]); self.assertTrue(any('restored' in l for l in j))
        s.play_sfx(316); self.assertEqual(len(a), 3)                                # le retour n'est annonce qu'une fois

    def test_increasing_then_constant_delays(self):
        s, j, a = new_sound(); Outage.broken = True; seen = []
        for _ in range(6):
            for i in (300, 316, 400): s.play_sfx(i)
            seen.append(round(s.retry - time.time())); s.retry = time.time() - 1; s.tick()
        self.assertEqual(seen[:3], [2, 10, 30]); self.assertTrue(all(v == 30 for v in seen[2:]), seen)

    def test_music_requested_during_cut_restarted_on_return(self):
        s, j, a = new_sound(); Outage.broken = True
        for i in (300, 316, 400): s.play_sfx(i)
        self.assertFalse(s.ok)
        s.events([(37, 2)]); s.events([(35, 300)])                          # le moteur demande la musique 2 : retenue (le bruitage est perdu)
        self.assertEqual(s.bgm_lost, 2); self.assertIsNone(s.bgm)
        Outage.broken = False; s.retry = time.time() - 1; s.tick()
        self.assertTrue(s.ok); self.assertIsNotNone(s.bgm); self.assertEqual(s.bgm_id, 2); self.assertIsNone(s.bgm_lost)
        self.assertEqual(s.failures, 0)                                               # la musique est partie : retabli

    def test_stop_during_cut_deletes_music_to_restart(self):
        s, j, a = new_sound(); Outage.broken = True
        for i in (300, 316, 400): s.play_sfx(i)
        s.events([(37, 2)]); s.events([(37, SOUND.BGM_STOP)])
        self.assertIsNone(s.bgm_lost)
        s.events([(37, 5), (37, SOUND.BGM_RESTART + 8)]); self.assertEqual(s.bgm_lost, 5)       # un jingle a reprise ne remplace pas la musique de fond

    def test_failed_music_is_kept_for_return(self):
        s, j, a = new_sound(); Outage.broken = True
        s.play_bgm(2)
        self.assertEqual(s.bgm_lost, 2); self.assertEqual(s.failures, 1)
        s.play_bgm(SOUND.BGM_RESTART + 5)                                           # un jingle rate n'est pas a relancer
        self.assertEqual(s.bgm_lost, 2)

    def test_sound_off_attempts_nothing(self):
        s, j, a = new_sound(); Outage.broken = True
        for i in (300, 316, 400): s.play_sfx(i)
        n = len(j); s.play_sfx(300); s.play_sfx(316); s.play_bgm(5)                 # appels directs (clic de menu...) pendant la coupure : ni essai ni echec ni ligne de journal
        self.assertEqual((len(j), s.outages, s.failures), (n, 1, 3)); self.assertEqual(s.bgm_lost, 5)

    def test_sound_absent_from_the_start_does_not_retry(self):
        s, j, a = new_sound(); s.ok = False                                       # pas de pilote audio (import de pyglet impossible) : ni coupure ni nouvel essai
        s.tick(); self.assertFalse(s.ok); self.assertIsNone(s.retry)


class SwallowedErrors(unittest.TestCase):
    def test_refused_volume_noted_once(self):
        s, j, a = new_sound(); s.play_bgm(2); s.play_sfx(300)
        Outage.volume_refused = True
        s.set_mix(general=0.5); s.set_mix(general=0.4)
        lines = [l for l in j if 'volume' in l]
        self.assertEqual(len(lines), 2, lines)                                    # une fois pour la musique, une fois pour les bruitages, pas a chaque reglage
        self.assertTrue(s.ok)

    def test_resume_after_pause_refused_noted_once(self):
        s, j, a = new_sound(); s.play_bgm(2)
        s.set_paused(True); Outage.broken = True
        s.set_paused(False); s.set_paused(True); s.set_paused(False)
        self.assertEqual(len([l for l in j if 'resume' in l]), 1)

    def test_log_capped(self):
        s, j, a = new_sound()
        for k in range(100): s._note('essai %d' % k)
        self.assertEqual(len(j), SOUND.NOTES_MAX)

    def test_failing_log_or_alert_break_nothing(self):
        s, j, a = new_sound()
        def breaks(t): raise RuntimeError('disque plein')
        s.logfile = breaks; s.alert = breaks; Outage.broken = True
        for i in (300, 316, 400): s.play_sfx(i)
        self.assertFalse(s.ok)


if __name__ == '__main__': unittest.main(verbosity=1)
