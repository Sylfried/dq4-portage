"""Rejoue les ordres de son du moteur dans la vraie classe Son (faux lecteurs, horloge simulee a 30 images / s, facteur = vitesse d'horloge du moteur) et ecrit la ligne du temps AUDIBLE."""
import sys, types
sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
import os as _os
sys.path.insert(0, _os.environ.get('SON_DIR', '/home/claude/wt45-son/dq4_pc'))
sys.modules['pyglet'] = None
import numpy as np
from dq4_pc import son as SON

import os, time as _time
RT = bool(os.environ.get('RT'))                       # RT=1 : horloge reelle (le decodage prend son vrai temps), les images du moteur sont cadencees a 30 x facteur par seconde
class H:
    t = 1000.0
    t0 = _time.time()
if RT:
    SON.time = _time
else:
    SON.time = types.SimpleNamespace(time=lambda: H.t, sleep=lambda x: None)
def maintenant(): return _time.time() - H.t0 if RT else H.t - 1000.0

class FauxLecteur:
    def __init__(self): self.volume = 1.0; self.playing = False; self.supprime = False; self.t0 = None
    def queue(self, src): self.src = src
    def play(self): self.playing = True; self.t0 = H.t
    def pause(self): self.playing = False
    def delete(self): self.supprime = True; self.playing = False
class FauxSource:
    def __init__(self, media, ad, fmt, pcm, debut, fin): self.pos = 0; self.n = len(pcm); self.fin = fin
class FauxMedia:
    Player = FauxLecteur; Source = object

class Rejeu:
    def __init__(self, apk, cache='/tmp/son45_cache', talk=print):
        import os; os.makedirs(cache, exist_ok=True)
        self.s = SON.Son(apk, cache, log=lambda *a: None)
        s = self.s; s.ok = True; s.ogg = True; s.media = FauxMedia; s.AudioFormat = lambda **kw: kw; s.AudioData = None
        SON.SourceBoucle = FauxSource
        self.talk = talk; self.lignes = []
        o_bgm, o_se, o_stopb, o_stopse = s._lancer_bgm, s._lancer_se, s.arreter_bgm, s.arreter_se
        def lb(ident, r, relance=False):
            n0 = s.bgm
            o_bgm(ident, r, relance)
            if s.bgm is not n0 and s.bgm is not None: self.note('JOUE musique/jingle BGM%02d (%s, %.1f s%s, vol %.2f)' % (ident, s.bgm_cat, len(r['pcm']) / r['frequence'], ', boucle' if r['boucle'] else '', s.bgm.volume))
        def ls(ident, r):
            n0 = len(s.se); o_se(ident, r)
            if len(s.se) > n0: self.note('JOUE SE%04d (%s, %.2f s, vol %.2f)' % (ident, s.se[-1].cat, len(r['pcm']) / r['frequence'], s.se[-1].p.volume))
            else: self.note('SE%04d NON JOUE (categorie coupee ?)' % ident)
        def sb():
            if s.bgm is not None: self.note('ARRET musique BGM%s' % s.bgm_id)
            o_stopb()
        s._lancer_bgm, s._lancer_se, s.arreter_bgm = lb, ls, sb
    def note(self, txt): self.lignes.append((maintenant(), txt)); self.talk('  t=%7.2f  %s' % (maintenant(), txt))
    def attendre_decodage(self):
        for nom, (fut, rap) in list(self.s.jobs.items()): fut.result()
    def image(self, evts, dt=1.0 / 30, e=None):
        """une image : les ordres du moteur, puis tick, puis le temps avance de dt"""
        if evts:
            self.talk('  t=%7.2f  ordres moteur %s' % (maintenant(), evts))
            if e is not None and 'image_moteur' in SON.Son.evenements.__code__.co_varnames: self.s.evenements(evts, image_moteur=e)
            else: self.s.evenements(evts)
            if not RT: self.attendre_decodage()
        self.s.tick()
        if RT:
            self.t_img = getattr(self, 't_img', _time.time()) + dt
            d = self.t_img - _time.time()
            if d > 0: _time.sleep(d)
        else: H.t += dt
