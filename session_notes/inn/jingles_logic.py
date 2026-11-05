"""Logique de la visionneuse pour chaque jingle du MenuSoundManager : horloge simulee (30 images / s, un tick() apres chaque image comme Game.tick), faux lecteurs, vraie classe Sound.
Mesure : delai entre l'ordre du moteur et Player.play(), duree entendue jusqu'a stop_bgm(), comparees a la fenetre du moteur (image de depart -> image d'arret) ; et, pour un jingle demande avec reprise (0x1000 | n), l'instant de la reprise de la musique d'avant."""
import sys, os, types, json, zipfile
sys.modules['pyglet'] = None
sys.path.insert(0, '/home/claude/dq4-portage')
import numpy as np
from dq4_pc import sound as S
T = [1000.0]
S.time = types.SimpleNamespace(time=lambda: T[0], sleep=lambda x: None)
APK = os.environ.get('DQ_APK', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks') + '/split_UnityDataAssetPack.apk'
class FakePlayer:
    log = []
    def __init__(self): self.volume = 1.0; self.playing = False
    def queue(self, src): pass
    def play(self): self.playing = True; FakePlayer.log.append(('play', T[0], self))
    def pause(self): self.playing = False
    def delete(self): FakePlayer.log.append(('delete', T[0], self))
class FakeSource:
    def __init__(self, media, ad, fmt, pcm, begin, end): self.pos = 0
class FakeMedia: Player = FakePlayer; Source = object
S.LoopSource = FakeSource
snd = S.Sound(APK, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/inn/cache_logic', log=lambda *a: None)
os.makedirs(snd.cache, exist_ok=True)
snd.ok = True; snd.ogg = True; snd.media = FakeMedia; snd.AudioFormat = lambda **kw: kw; snd.AudioData = None
def wait():
    for k, (fut, cbs) in list(snd.jobs.items()): fut.result()
def run(orders, nframes, e0=1000):
    """orders : {offset d'image: [(type, valeur)]} ; renvoie les evenements (play / stop) avec l'instant simule"""
    FakePlayer.log.clear(); ev = []
    o_launch, o_stop = snd._launch_bgm, snd.stop_bgm
    def launch(i, r, restart=False):
        n0 = snd.bgm; o_launch(i, r, restart)
        if snd.bgm is not n0 and snd.bgm is not None: ev.append(('play', i, T[0], len(r['pcm']) / r['frequence']))
    def stop():
        if snd.bgm is not None: ev.append(('stop', snd.bgm_id, T[0], None))
        o_stop()
    snd._launch_bgm, snd.stop_bgm = launch, stop
    t_order = {}
    for k in range(nframes):
        e = e0 + k
        if k in orders:
            for t, v in orders[k]: t_order[(t, v)] = T[0]
            snd.events(orders[k], engine_frame=e); wait()
        snd.tick()
        T[0] += 1 / 30.0
    snd._launch_bgm, snd.stop_bgm = o_launch, o_stop
    return ev, t_order
data = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'menu_sound_real.json')))
print('A. jingle seul demande par le moteur puis arret du moteur (comme l\'auberge) ; musique de la ville BGM14 en cours avant')
print('BGM | fenetre moteur | fichier | depart apres l\'ordre | entendu (play -> stop) | ecart a la fenetre | coupe par le moteur ?')
seen = set()
for e in data:
    fp, _, bgm = [p for p in e['plays'] if p[1] == '7playBgm'][0]
    fs = [s for s in e['stops'][1:] if s[0] > fp][0][0]
    W = fs - fp
    if bgm in seen: continue
    seen.add(bgm)
    snd.stop_bgm(); snd.bgm_queue.clear(); snd.dec.clear()
    snd.events([(37, 14)], engine_frame=1); wait(); snd.tick()
    # ordres : arret de la musique de la ville (image 5), jingle (image 5 + 31 : comme l'auberge), arret du moteur W images plus tard
    ev, to = run({5: [(37, 0x4000)], 6: [(37, bgm)], 6 + W: [(37, 0x4000)]}, 6 + W + 10)
    pl = [x for x in ev if x[0] == 'play' and x[1] == bgm][0]; st = [x for x in ev if x[0] == 'stop' and x[1] == bgm]
    dur = pl[3]
    t_start_order = to[(37, bgm)]
    if st:
        audible = st[0][2] - pl[2]
    else: audible = None
    nat = ' (le fichier est fini avant : fin naturelle %.3f s)' % dur if dur < W / 30 else ''
    print('BGM%02d | %3d img = %6.3f s | %6.3f s | %+5.0f ms | %6.3f s | %+5.0f ms | %s' % (bgm, W, W / 30.0, dur, 1000 * (pl[2] - t_start_order), audible if audible is not None else -1, 1000 * ((audible or 0) - min(W / 30.0, 1e9)), ('oui, ' + '%.3f s de fichier non joues' % max(0, dur - W / 30.0)) if dur > W / 30 + 1e-6 else 'non') + nat)
print()
print('B. jingle demande avec reprise (0x1000 | n : coffre, recrutement...) : instant de la reprise de la musique d\'avant (BGM14) apres l\'ordre')
for bgm in (48, 47, 44, 49, 43, 40, 39, 41):
    snd.stop_bgm(); snd.bgm_queue.clear(); snd.dec.clear(); snd.resume = None
    snd.events([(37, 14)], engine_frame=1); wait(); snd.tick()
    ev, to = run({5: [(37, 0x1000 | bgm)]}, 5 + 30 * 8)
    pl = [x for x in ev if x[0] == 'play' and x[1] == bgm][0]
    back = [x for x in ev if x[0] == 'play' and x[1] == 14 and x[2] > pl[2]]
    stp = [x for x in ev if x[0] == 'stop' and x[1] == bgm]
    print('BGM%02d | fichier %.3f s | depart +%.0f ms apres l\'ordre | stop du jingle + reprise BGM14 a +%.3f s apres le depart (ecart au fichier : %+.0f ms)' % (bgm, pl[3], 1000 * (pl[2] - to[(37, 0x1000 | bgm)]), (stp[0][2] - pl[2]) if stp else -1, 1000 * ((stp[0][2] - pl[2]) - pl[3]) if stp else 0))
