"""Rejoue les ordres de son du moteur dans la vraie classe Son (faux lecteurs, horloge simulee a 30 images / s, facteur = vitesse d'horloge du moteur) et ecrit la ligne du temps AUDIBLE."""
import sys, types
sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
import os as _os
sys.path.insert(0, _os.environ.get('SON_DIR', '/home/claude/wt45-son/dq4_pc'))
sys.modules['pyglet'] = None
import numpy as np
from dq4_pc import sound as SOUND

import os, time as _time
RT = bool(os.environ.get('RT'))                       # RT=1 : horloge reelle (le decodage prend son vrai temps), les images du moteur sont cadencees a 30 x facteur par seconde
class H:
    t = 1000.0
    t0 = _time.time()
if RT:
    SOUND.time = _time
else:
    SOUND.time = types.SimpleNamespace(time=lambda: H.t, sleep=lambda x: None)
def now(): return _time.time() - H.t0 if RT else H.t - 1000.0

class FakePlayer:
    def __init__(self): self.volume = 1.0; self.playing = False; self.deleted = False; self.t0 = None
    def queue(self, src): self.src = src
    def play(self): self.playing = True; self.t0 = H.t
    def pause(self): self.playing = False
    def delete(self): self.deleted = True; self.playing = False
class FakeSource:
    def __init__(self, media, ad, fmt, pcm, begin, end): self.pos = 0; self.n = len(pcm); self.end = end
class FakeMedia:
    Player = FakePlayer; Source = object

class Replay:
    def __init__(self, apk, cache='/tmp/son45_cache', talk=print):
        import os; os.makedirs(cache, exist_ok=True)
        self.s = SOUND.Sound(apk, cache, log=lambda *a: None)
        s = self.s; s.ok = True; s.ogg = True; s.media = FakeMedia; s.AudioFormat = lambda **kw: kw; s.AudioData = None
        SOUND.LoopSource = FakeSource
        self.talk = talk; self.lines = []
        o_bgm, o_sfx, o_stopb, o_stopse = s._launch_bgm, s._launch_sfx, s.stop_bgm, s.stop_sfx
        def lb(ident, r, restart=False):
            n0 = s.bgm
            o_bgm(ident, r, restart)
            if s.bgm is not n0 and s.bgm is not None: self.note('PLAY music/jingle BGM%02d (%s, %.1f s%s, vol %.2f)' % (ident, s.bgm_category, len(r['pcm']) / r['frequence'], ', loop' if r['boucle'] else '', s.bgm.volume))
        def ls(ident, r):
            n0 = len(s.sfx); o_sfx(ident, r)
            if len(s.sfx) > n0: self.note('PLAY SE%04d (%s, %.2f s, vol %.2f)' % (ident, s.sfx[-1].category, len(r['pcm']) / r['frequence'], s.sfx[-1].p.volume))
            else: self.note('SE%04d NOT PLAYED (category muted?)' % ident)
        def sb():
            if s.bgm is not None: self.note('STOP music BGM%s' % s.bgm_id)
            o_stopb()
        s._launch_bgm, s._launch_sfx, s.stop_bgm = lb, ls, sb
    def note(self, txt): self.lines.append((now(), txt)); self.talk('  t=%7.2f  %s' % (now(), txt))
    def wait_decoding(self):
        for name_str, (fut, rap) in list(self.s.jobs.items()): fut.result()
    def image(self, evts, dt=1.0 / 30, e=None):
        """une image : les ordres du moteur, puis tick, puis le temps avance de dt"""
        if evts:
            self.talk('  t=%7.2f  engine orders %s' % (now(), evts))
            if e is not None and 'image_moteur' in SOUND.Sound.events.__code__.co_varnames: self.s.events(evts, engine_frame=e)
            else: self.s.events(evts)
            if not RT: self.wait_decoding()
        self.s.tick()
        if RT:
            self.t_img = getattr(self, 't_img', _time.time()) + dt
            d = self.t_img - _time.time()
            if d > 0: _time.sleep(d)
        else: H.t += dt
