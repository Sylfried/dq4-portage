"""Chronologie d'une nuit a l'auberge : vrai moteur (30 Hz en temps reel) + vraie classe Sound (vrai pyglet, pilote silencieux), appels identiques a Game.tick.
usage : inn_rt.py [cold|warm] ; DQ_SPEED=1 (facteur d'horloge du moteur)"""
import sys, os, struct, time
os.environ.setdefault('PYGLET_AUDIO', 'silent'); os.environ.setdefault('PYGLET_HEADLESS', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import pyglet; pyglet.options['shadow_window'] = False
from dq4_pc import sound as S
from dq4_pc.battle import battle_speed as VC
mode = sys.argv[1] if len(sys.argv) > 1 else 'warm'
speed = float(os.environ.get('DQ_SPEED', '1'))
m = new(1); c = m.core
cache = '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/inn/cache_' + mode
os.makedirs(cache, exist_ok=True)
for f in os.listdir(cache): os.remove(os.path.join(cache, f))
snd = S.Sound(m.apk_data, cache, log=lambda *a: None)
assert snd.ok and snd.ogg, 'pyglet/soundfile indisponible'
T0 = [time.perf_counter()]
def now(): return time.perf_counter() - T0[0]
LOG = []
def note(txt, **kw):
    LOG.append((now(), txt, kw)); print('%8.3f  %s' % (now(), txt), flush=True)
# instruments
o_launch, o_stop, o_events = snd._launch_bgm, snd.stop_bgm, snd.events
def launch(ident, r, restart=False):
    n0 = snd.bgm; o_launch(ident, r, restart)
    if snd.bgm is not n0 and snd.bgm is not None:
        note('Player.play() BGM%02d (cat %s, fichier %.3f s, volume %.3f)' % (ident, snd.bgm_category, len(r['pcm']) / r['frequence'], snd.bgm.volume), ident=ident, pcm=len(r['pcm']), fr=r['frequence'])
        snd._rt = dict(ident=ident, p=snd.bgm, t_play=now())
def stop():
    if snd.bgm is not None:
        rt = getattr(snd, '_rt', None)
        pos = snd.bgm.time if rt and rt['p'] is snd.bgm else None
        note('stop_bgm() BGM%s ; Player.time (horloge maitre) = %s' % (snd.bgm_id, ('%.3f s' % pos) if pos is not None else '?'), pos=pos)
    o_stop()
def events(evts, engine_frame=None):
    for t, v in evts:
        if t in (35, 36, 37): note('  ordre du moteur recu : %s %s (image moteur %s)' % ({35: 'SE', 36: 'stopSE', 37: 'BGM'}[t], hex(v) if t == 37 and v >= 0x1000 else v, engine_frame))
    o_events(evts, engine_frame)
snd._launch_bgm, snd.stop_bgm, snd.events = launch, stop, events
if mode == 'warm':
    snd.preload_music(); snd.events([(37, 14)], engine_frame=0)
    t = time.perf_counter()
    while time.perf_counter() - t < 25 and (snd.background or snd.jobs): snd.tick(); time.sleep(1 / 30)
    print('prechargement : %d musiques en memoire, %d en attente' % (sum(1 for k in snd.dec if k.startswith('BGM')), len(snd.background)))
    snd.stop_bgm(); LOG.clear()
else:
    snd.preload_music(); snd.background.clear()      # cold : rien n'est decode d'avance
party = c.export('_ZN6status7g_PartyE'); c.mem_w(party + 0x2e0, struct.pack('<I', 3000))
tws = m.E('_ZN16TownWindowSystem11m_singletonE')
mm = c.call(m.E('_ZN27MaterielMenu_WINDOW_MANAGER12getSingletonEv'), label='mm'); c.mem_w(mm + 0x10, struct.pack('<i', 0))
m.sensor.drain()
# la musique de la ville joue avant l'auberge (comme en jeu)
snd.events([(37, 14)], engine_frame=m.frames); 
for _ in range(15): snd.tick(); time.sleep(1 / 30)
LOG.clear(); T0[0] = time.perf_counter()
c.call(m.E('_ZN6window13CommandWindow19changeShopMenuPhaseEi'), tws, 0, label='phase')
waiting = 0; rel = None; step_dur = []; t_next = time.perf_counter(); steps = []
for i in range(1100):
    p = d = 0
    if rel is not None: m.send_menu(rel, 1, -1, 0); rel = None
    port = m.active_menu()
    att_msg = m.msg_visible and (m.ui.msg.get('feed') or m.message_state()[1] in (3, 5))
    if port is not None or att_msg:
        waiting += 1
        if waiting % 6 == 0:
            if port is None and att_msg: p = d = ENGINE.A
            else: m.send_menu(port, 1, -1, 0x10); rel = port
    else: waiting = 0
    t_step0 = time.perf_counter(); m.step(p, d); sd = time.perf_counter() - t_step0; step_dur.append(sd)
    steps.append((m.frames, now()))
    if m.state.sounds: snd.events(VC.sounds_to_play(m.state.sounds, None), engine_frame=m.frames); m.state.sounds = []
    snd.tick()
    t_next += 1.0 / (30.0 * speed)
    dl = t_next - time.perf_counter()
    if dl > 0: time.sleep(dl)
    elif dl < -0.1: t_next = time.perf_counter()
    if m.state.part == 0xc and m.frames > 600 and not snd.bgm_queue and i > 700: break
note('fin')
import json
json.dump(dict(log=[(a, b) for a, b, k in LOG], step_dur_ms=[round(x * 1000, 1) for x in step_dur], steps=steps), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inn_rt_%s.json' % mode), 'w'))
print('duree des pas du moteur : moyenne %.1f ms, max %.1f ms, >33 ms : %d sur %d' % (1000 * sum(step_dur) / len(step_dur), 1000 * max(step_dur), sum(1 for x in step_dur if x > 1 / 30), len(step_dur)))
snd.shutdown()
