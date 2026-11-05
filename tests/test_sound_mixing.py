"""Test du mixage du son (categories, volumes, interrupteurs) sans fenetre ni carte son : les lecteurs de pyglet sont remplaces par de faux lecteurs qui gardent leur volume.

    python3 tools/test_sound_mixing.py
"""
import os, sys, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.modules['pyglet'] = None                                             # (pas de pyglet : ni fenetre ni pilote audio ; Son le prend pour « son indisponible » et on lui donne de faux lecteurs)
from dq4_pc import sound as SOUND


class FakePlayer:
    def __init__(self): self.volume = 1.0; self.playing = False; self.deleted = False
    def queue(self, src): pass
    def play(self): self.playing = True
    def pause(self): self.playing = False
    def delete(self): self.deleted = True; self.playing = False


class FakeSource:
    def __init__(self, *a): self.pos = 0


class FakeMedia:
    Player = FakePlayer
    Source = object


def data(seconds, looping, volume=1.0, frequency=1000):
    n = int(seconds * frequency)
    return dict(pcm=np.zeros((n, 1), np.int16), frequence=frequency, debut=0 if not looping else n // 4, fin=0 if not looping else n, volume=volume, boucle=looping)


def new_sound():
    s = SOUND.Sound('inexistant.apk', '/tmp', log=lambda *a: None)
    s.ok = True; s.ogg = True; s.media = FakeMedia; s.AudioFormat = lambda **kw: kw; s.AudioData = None
    SOUND.LoopSource = FakeSource
    for i in (300, 316, 400, 500): s.dec['SE%04d' % i] = data(1.0, False, volume=0.5)
    s.dec['SE0500'] = data(2.0, True, volume=1.0)                      # bruitage en boucle
    s.dec['BGM02'] = data(60.0, True, volume=0.8)                       # musique (boucle)
    s.dec['BGM08'] = data(5.0, False, volume=1.0)                       # jingle (court, sans boucle)
    s.dec['BGM01'] = data(111.0, False, volume=1.0)                     # morceau long sans boucle : de la musique
    return s


class Categories(unittest.TestCase):
    def test_sfx_category(self):
        for i in range(300, 305): self.assertEqual(SOUND.category_sfx(i), 'interface')
        for i in (299, 305, 316, 408, 501, 1129): self.assertEqual(SOUND.category_sfx(i), 'effets')
        self.assertEqual(SOUND.category_sfx(409), 'jingles', 'fanfare de victoire')

    def test_bgm(self):
        self.assertEqual(SOUND.category_bgm(False, True, 60.0), 'musique')               # en boucle
        self.assertEqual(SOUND.category_bgm(False, False, 5.0), 'jingles')               # court sans boucle
        self.assertEqual(SOUND.category_bgm(True, False, 5.0), 'jingles')                # demande avec reprise de la musique d'avant
        self.assertEqual(SOUND.category_bgm(False, False, 111.0), 'musique')             # long sans boucle
        self.assertEqual(SOUND.category_bgm(True, True, 5.0), 'musique')                 # en boucle : on ne revient jamais a la musique d'avant

    def test_game_option(self):
        self.assertEqual([round(SOUND.game_option_volume(i), 2) for i in range(5)], [0.2, 0.4, 0.6, 0.8, 1.0])
        self.assertEqual(SOUND.game_option_volume(9), 1.0); self.assertEqual(SOUND.game_option_volume(-3), 0.2)


class Gain(unittest.TestCase):
    def test_default(self):
        m = SOUND.Mixer()
        for c in SOUND.CATEGORIES: self.assertEqual(m.gain(c), 1.0)

    def test_product(self):
        m = SOUND.Mixer(general=0.5, music=0.8, jingles=0.6, effects=0.4, interface=0.2)
        self.assertAlmostEqual(m.gain('musique'), 0.4); self.assertAlmostEqual(m.gain('jingles'), 0.3)
        self.assertAlmostEqual(m.gain('effets'), 0.2); self.assertAlmostEqual(m.gain('interface'), 0.1)
        self.assertAlmostEqual(m.gain('musique', 0.5), 0.2)                                 # volume propre au fichier
        m.game['musique'] = 0.6; m.game['effets'] = 0.2                                      # options « volume » du jeu : musique + jingles / bruitages + interface
        self.assertAlmostEqual(m.gain('musique'), 0.24); self.assertAlmostEqual(m.gain('jingles'), 0.18)
        self.assertAlmostEqual(m.gain('effets'), 0.04); self.assertAlmostEqual(m.gain('interface'), 0.02)

    def test_switch_and_bounds(self):
        m = SOUND.Mixer(); m.active['effets'] = False
        self.assertEqual(m.gain('effets'), 0.0); self.assertEqual(m.gain('interface'), 1.0)
        m.general = 3.0; self.assertEqual(m.gain('musique'), 1.0)                          # jamais plus de 1
        m.general = -1.0; self.assertEqual(m.gain('musique'), 0.0)


class Reading(unittest.TestCase):
    def test_volumes_applied_immediately(self):
        s = new_sound()
        s.play_bgm(2); s.play_sfx(300); s.play_sfx(316)
        self.assertEqual(s.bgm_category, 'musique'); self.assertAlmostEqual(s.bgm.volume, 0.8)
        v = {x.ident: x for x in s.sfx}
        self.assertEqual(v[300].category, 'interface'); self.assertEqual(v[316].category, 'effets')
        self.assertAlmostEqual(v[300].p.volume, 0.5); self.assertAlmostEqual(v[316].p.volume, 0.5)
        s.set_mix(general=0.5, volumes={'musique': 0.5, 'effets': 0.2, 'interface': 1.0})
        self.assertAlmostEqual(s.bgm.volume, 0.5 * 0.5 * 0.8)                              # la musique en cours change
        self.assertAlmostEqual(v[316].p.volume, 0.5 * 0.2 * 0.5)                           # les bruitages en cours aussi
        self.assertAlmostEqual(v[300].p.volume, 0.5 * 1.0 * 0.5)

    def test_switches(self):
        s = new_sound()
        s.play_bgm(2); s.play_sfx(316)
        s.set_mix(active_flags={'musique': False, 'effets': False})
        self.assertEqual(s.bgm.volume, 0.0); self.assertEqual(s.sfx[0].p.volume, 0.0)
        s.play_sfx(316); s.play_sfx(316)
        self.assertEqual(len(s.sfx), 1, 'un bruitage court n\'est pas joue quand sa categorie est coupee')
        s.play_sfx(300); self.assertEqual(len(s.sfx), 2, 'les sons de l\'interface restent actifs')
        s.set_mix(active_flags={'musique': True, 'effets': True})
        self.assertAlmostEqual(s.bgm.volume, 0.8); self.assertAlmostEqual(s.sfx[0].p.volume, 0.5)

    def test_just_launched_sfx_never_released_by_next_steps(self):
        """Marche acceleree : le moteur fait plusieurs pas (donc plusieurs tick()) a la suite dans la meme image affichee, juste apres l'ordre du bruitage de porte ou de sortie de village ; un lecteur qui ne se
        dit pas encore « en lecture » ne doit pas faire perdre le bruitage. Passe le delai de grace, un lecteur arrete est libere comme avant."""
        s = new_sound(); s.play_sfx(316); x = s.sfx[0]
        x.p.playing = False                                                  # (le lecteur ne s'annonce pas encore)
        for _ in range(8): s.tick()                                          # huit pas a la suite
        self.assertEqual(len(s.sfx), 1); self.assertFalse(x.p.deleted)
        x.begin -= SOUND.SFX_GRACE + 0.01; s.tick()                             # delai de grace passe : lecteur arrete = bruitage libere
        self.assertEqual(s.sfx, []); self.assertTrue(x.p.deleted)

    def test_playing_sfx_kept_until_its_end(self):
        s = new_sound(); s.play_sfx(316); x = s.sfx[0]
        x.begin -= 10.0; s.tick(); self.assertEqual(len(s.sfx), 1)             # en lecture : garde
        x.end = 0.0; s.tick(); self.assertEqual(s.sfx, [])                    # duree depassee : libere

    def test_transition_sfx_played_in_full(self):
        """Porte (309) puis transition de carte (305, demande par le moteur entre le debut du fondu et le chargement : voir test_transition_sfx) : le chargement de la carte bloque la boucle jusqu'a 0,5 s et le moteur
        fait plusieurs pas a la suite (marche acceleree) ; les deux bruitages restent joues, a leur volume, jusqu'a la fin de leur duree d'origine, puis sont liberes."""
        s = new_sound(); s.dec['SE0309'] = data(1.5, False, volume=0.4); s.dec['SE0305'] = data(1.0, False, volume=0.5)
        s.events([(35, 309)]); [s.tick() for _ in range(6)]
        s.events([(35, 305)]); [s.tick() for _ in range(6)]
        self.assertEqual([x.ident for x in s.sfx], [309, 305]); self.assertEqual([x.category for x in s.sfx], ['effets', 'effets'])
        self.assertEqual([round(x.p.volume, 3) for x in s.sfx], [0.4, 0.5])
        for x in s.sfx: x.begin -= 0.5; x.end -= 0.5                          # le chargement de la carte a bloque la boucle 0,5 s
        s.tick()
        self.assertEqual([x.ident for x in s.sfx], [309, 305]); self.assertFalse(any(x.p.deleted for x in s.sfx))
        for x in s.sfx: x.begin -= 0.9; x.end -= 0.9                          # 1,4 s ecoulees : le 305 (1,0 s + 0,5 s de marge) est encore la, le 309 (1,5 s) aussi
        s.tick(); self.assertEqual([x.ident for x in s.sfx], [309, 305])
        for x in s.sfx: x.end = 0.0                                           # duree depassee : liberes
        s.tick(); self.assertEqual(s.sfx, [])

    def test_loop_cut_then_reopened(self):
        s = new_sound(); s.set_mix(active_flags={'effets': False})
        s.play_sfx(500)
        self.assertEqual(len(s.sfx), 1, 'un bruitage en boucle est lance meme coupe (volume nul)')
        self.assertEqual(s.sfx[0].p.volume, 0.0)
        s.set_mix(active_flags={'effets': True}); self.assertAlmostEqual(s.sfx[0].p.volume, 1.0)

    def test_jingle_and_resume(self):
        s = new_sound()
        s.play_bgm(2); music = s.bgm
        s.play_bgm(SOUND.BGM_RESTART + 8)
        self.assertEqual(s.bgm_category, 'jingles'); self.assertEqual(s.resume, 2)
        s.set_mix(volumes={'jingles': 0.25, 'musique': 0.5}); self.assertAlmostEqual(s.bgm.volume, 0.25)
        s.set_mix(active_flags={'jingles': False}); self.assertEqual(s.bgm.volume, 0.0)
        self.assertIsNot(s.bgm, music)
        s.set_mix(active_flags={'jingles': True})
        s.play_bgm(1)                                                                       # long morceau sans boucle : de la musique
        self.assertEqual(s.bgm_category, 'musique'); self.assertAlmostEqual(s.bgm.volume, 0.5)

    def test_victory_fanfare_is_a_jingle(self):
        """SE 409 (victoire) : volume et interrupteur de « Jingles et fanfares », mais l'option « bruitages » du jeu (pas celle de la musique)."""
        s = new_sound(); s.dec['SE0409'] = data(2.9, False, volume=0.6)
        s.set_mix(volumes={'jingles': 0.5, 'effets': 0.1}, game={'musique': 1.0, 'effets': 0.4})
        s.play_sfx(409); x = s.sfx[-1]
        self.assertEqual(x.category, 'jingles'); self.assertAlmostEqual(x.p.volume, 0.5 * 0.6 * 0.4)
        s.set_mix(game={'musique': 0.2, 'effets': 1.0}); self.assertAlmostEqual(x.p.volume, 0.5 * 0.6, msg='regle tout de suite, avec l\'option des bruitages')
        s.set_mix(active_flags={'jingles': False}); self.assertEqual(x.p.volume, 0.0)
        n = len(s.sfx); s.play_sfx(409); self.assertEqual(len(s.sfx), n, 'jingles coupes : la fanfare n\'est pas jouee')
        s.set_mix(active_flags={'jingles': True, 'effets': False}); s.play_sfx(409); self.assertEqual(len(s.sfx), n + 1, 'bruitages coupes : la fanfare, elle, joue')

    def test_listening_during_pause(self):
        s = new_sound(); s.play_bgm(2); s.play_sfx(316)
        players = [s.bgm] + [x.p for x in s.sfx]
        s.set_paused(True); self.assertTrue(all(not p.playing for p in players))
        s.listen(True); self.assertTrue(all(p.playing for p in players), 'page Son : les sons reprennent')
        s.set_mix(volumes={'musique': 0.5}); self.assertAlmostEqual(s.bgm.volume, 0.4)
        s.listen(False); self.assertTrue(all(not p.playing for p in players), 'on quitte la page : de nouveau en pause')
        s.set_paused(False); self.assertTrue(all(p.playing for p in players))
        s.set_paused(True); s.listen(True); s.set_paused(False)
        self.assertFalse(s.listening); self.assertTrue(all(p.playing for p in players))

    def test_old_names(self):
        s = new_sound(); s.set_volumes(0.3, 0.6)
        self.assertAlmostEqual(s.vol_m, 0.3); self.assertAlmostEqual(s.vol_b, 0.6)
        self.assertAlmostEqual(s.mix.vol['musique'], 0.3); self.assertAlmostEqual(s.mix.vol['effets'], 0.6)


def wait(s):
    """Laisse finir les decodages de fond, puis tick() (le decodage tourne dans un fil)."""
    for name_str, (fut, rap) in list(s.jobs.items()): fut.result()
    s.tick()


class Preload(unittest.TestCase):
    """SN : les musiques que le moteur demande puis arrete aussitot en combat (BGM 23 : defaite du groupe ; jingles) sont decodees d'avance et gardees en memoire."""

    def sound(self):
        s = new_sound(); s.decoded = []
        def decode(name_str): s.decoded.append(name_str); return data(113.0 if name_str == 'BGM23' else 4.0, name_str == 'BGM03')       # (BGM 3 : la musique du moment, avec boucle)
        s._decode = decode
        return s

    def test_nothing_before_the_first_music(self):
        s = self.sound(); s.preload_music((23, 47))
        for _ in range(3): wait(s)
        self.assertEqual(s.decoded, [], 'tant qu\'aucune musique ne joue, rien n\'est decode d\'avance')
        s.play_bgm(3); wait(s)                                                 # la musique du jeu passe la premiere
        self.assertEqual(s.decoded[0], 'BGM03'); self.assertIsNotNone(s.bgm)

    def test_one_music_at_a_time_then_all_in_memory(self):
        s = self.sound(); s.play_bgm(3); wait(s); s.preload_music((47, 23, 9))
        wait(s); self.assertEqual(len(s.jobs), 1, 'une seule musique a la fois')
        for _ in range(5): wait(s)
        self.assertEqual(s.decoded, ['BGM03', 'BGM47', 'BGM23', 'BGM09'], 'dans l\'ordre demande')
        for name_str in ('BGM47', 'BGM23', 'BGM09'): self.assertIn(name_str, s.dec)

    def test_not_ahead_of_requested_decoding(self):
        s = self.sound(); s.play_bgm(3); wait(s); s.preload_music((23,))
        s.play_bgm(5)                                                              # decodage demande par le moteur : le prechargement attend
        s.tick(); self.assertEqual(list(s.jobs), ['BGM05'], 'le prechargement ne passe pas devant un son demande')
        for _ in range(4): wait(s)
        self.assertIn('BGM23', s.dec)

    def test_pinned_never_evicted(self):
        s = self.sound(); s.play_bgm(3); wait(s); s.preload_music((23,))
        for _ in range(3): wait(s)
        self.assertIn('BGM23', s.dec)
        for i in range(200): s.dec['SE%04d' % (1000 + i)] = data(0.1, False)
        s._purge()
        self.assertIn('BGM23', s.dec, 'une musique epinglee reste')
        self.assertLessEqual(len([k for k in s.dec if k not in s.pinned]), 80, 'le reste suit la regle des 80 sons')

    def test_defeat_requested_then_stopped_is_played(self):
        """Le moteur demande BGM 23 (tout le groupe est battu) : la musique part tout de suite, sans attendre un decodage que l'arret du moteur annulerait."""
        s = self.sound(); s.play_bgm(3); wait(s); s.preload_music((23,))
        for _ in range(3): wait(s)
        s.play_bgm(SOUND.BGM_STOP); self.assertIsNone(s.bgm)
        s.play_bgm(23); self.assertIsNotNone(s.bgm, 'jouee dans l\'image meme de l\'ordre'); self.assertEqual(s.bgm_id, 23)
        self.assertEqual(s.jobs, {})

    def test_without_preloading_stop_cancels_decoding(self):
        """Ce que le prechargement evite : musique non decodee, ordre puis arret avant la fin du decodage -> rien ne joue."""
        s = self.sound(); s.play_bgm(23); s.play_bgm(SOUND.BGM_STOP); wait(s)
        self.assertIsNone(s.bgm)

    def test_disabled(self):
        s = self.sound(); s.ok = False; s.preload_music((23,)); self.assertEqual(s.background, [])


class ProtectionJingle(unittest.TestCase):
    """SN : un jeu accelere (combat x2, x3) enchaine les ordres de musique du moteur plus vite : la fanfare etait coupee (montee de niveau, BGM 47 de 3,1 s : 1,75 s a x3). Un ordre qui serait arrive apres le jingle
    a vitesse normale attend l'heure ou il serait arrive (image du moteur, 30 par seconde) ou la fin du jingle ; sans image du moteur, rien ne change. Horloge simulee ; jingle = BGM 8 (5 s), musique = BGM 2 (boucle)."""

    def setUp(self):
        import types
        self.h = 1000.0; self.old = SOUND.time
        SOUND.time = types.SimpleNamespace(time=lambda: self.h)
        self.s = new_sound()

    def tearDown(self): SOUND.time = self.old

    def order(self, v, e, dt=0.0):
        self.h += dt; self.s.events([(37, v)], engine_frame=e); self.s.tick()

    def advance(self, dt): self.h += dt; self.s.tick()

    def launch_jingle(self, v=8, e=100, restart=False):
        s = self.s; self.order(2, 0); self.assertEqual(s.bgm_id, 2)
        self.order(v | (SOUND.BGM_RESTART if restart else 0), e); self.assertEqual(s.bgm_category, 'jingles'); self.t0 = self.h

    def test_normal_speed_nothing_changes(self):
        s = self.s; self.launch_jingle()
        self.order(SOUND.BGM_STOP, 160, dt=2.0)                                      # image 160 = 2 s apres l'image 100 : l'heure qu'il est
        self.assertIsNone(s.bgm); self.assertEqual(len(s.bgm_queue), 0)

    def test_x3_stop_held_until_normal_time(self):
        s = self.s; self.launch_jingle()
        self.order(SOUND.BGM_STOP, 160, dt=0.7)                                      # a x3 : l'ordre de l'image 160 arrive a 0,7 s au lieu de 2 s
        self.assertEqual(s.bgm_id, 8); self.assertIsNotNone(s.bgm); self.assertEqual(len(s.bgm_queue), 1)
        self.advance(1.2); self.assertIsNotNone(s.bgm, '1,9 s : pas encore')
        self.advance(0.15); self.assertIsNone(s.bgm, '2,05 s : l\'ordre part a l\'heure normale'); self.assertEqual(len(s.bgm_queue), 0)

    def test_order_after_jingle_end_leaves_at_jingle_end(self):
        s = self.s; self.launch_jingle()
        self.order(SOUND.BGM_STOP, 400, dt=1.0); self.order(2, 430, dt=0.1)               # images 400 et 430 : 10 s et 11 s apres (le jingle dure 5 s)
        self.assertEqual(len(s.bgm_queue), 2)
        self.advance(3.8); self.assertEqual(len(s.bgm_queue), 2, '4,9 s : le jingle joue encore')
        self.advance(0.2)
        self.assertEqual(len(s.bgm_queue), 0); self.assertEqual(s.bgm_id, 2, 'les ordres partent dans l\'ordre : arret puis musique 2'); self.assertEqual(s.bgm_category, 'musique')

    def test_sfx_never_retained(self):
        s = self.s; self.launch_jingle()
        self.order(SOUND.BGM_STOP, 300, dt=0.5); s.events([(35, 316)], engine_frame=301)
        self.assertEqual([x.ident for x in s.sfx], [316])

    def test_without_engine_frame_or_jingle_or_cut_jingles(self):
        s = self.s; self.launch_jingle()
        s.events([(37, SOUND.BGM_STOP)]); self.assertIsNone(s.bgm, 'sans image du moteur : tout de suite')
        self.order(2, 0); self.order(5, 10, dt=0.1); self.assertEqual(len(s.bgm_queue), 0, 'une musique avec boucle n\'est pas un jingle')
        s.set_mix(active_flags={'jingles': False}); self.order(8, 100); self.order(SOUND.BGM_STOP, 500, dt=0.1)
        self.assertIsNone(s.bgm, 'jingles coupes : rien a proteger')

    def test_jingle_with_resume_then_next_jingle(self):
        s = self.s; self.launch_jingle(restart=True); self.assertEqual(s.resume, 2)
        self.order(SOUND.BGM_RESTART + 8, 400, dt=1.0)                                  # 2e fanfare, apres la fin de la 1re a vitesse normale
        self.assertEqual(len(s.bgm_queue), 1); self.assertEqual(s.bgm_id, 8)
        self.advance(4.1)
        self.assertEqual(len(s.bgm_queue), 0); self.assertEqual(s.bgm_id, 8); self.assertEqual(s.resume, 2, 'la musique d\'avant a repris, puis le 2e jingle l\'a gardee a reprendre (pas le 1er jingle)')

    def test_pause_releases_nothing(self):
        s = self.s; self.launch_jingle()
        self.order(SOUND.BGM_STOP, 160, dt=0.5)
        s.set_paused(True); self.advance(100.0); self.assertEqual(len(s.bgm_queue), 1)
        s.set_paused(False); self.assertEqual(len(s.bgm_queue), 1, 'la pause decale les echeances')
        self.advance(1.0); self.assertEqual(len(s.bgm_queue), 1); self.advance(0.6); self.assertEqual(len(s.bgm_queue), 0)

    def test_loading_a_state_empties_the_queue(self):
        s = self.s; self.launch_jingle(); self.order(SOUND.BGM_STOP, 300, dt=0.2); self.assertEqual(len(s.bgm_queue), 1)
        s.restore_bgm({'id': 2, 'pos': 0.0, 'reprise': None}); self.assertEqual(len(s.bgm_queue), 0); self.assertEqual(s.bgm_id, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
