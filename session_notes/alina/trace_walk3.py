"""Etat instantane 1 (toit de Burland, cbout) : le joueur marche vers la gauche (touche LEFT) jusqu'au declenchement de la scene des compagnons, puis journal pas a pas du vrai moteur.
usage: trace_walk.py sortie.json nb_pas etat.dqs [mode]   mode : 'release' (touche relachee des que le jeu verrouille le joueur) ou 'hold' (maintenue jusqu'au bout)"""
import json, math, os, sys, tempfile
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
from dq4_pc.persistence import savestates as SS
out = sys.argv[1]; nsteps = int(sys.argv[2]); path = sys.argv[3]; mode = sys.argv[4] if len(sys.argv) > 4 else 'release'
START = int(os.environ.get('WALK_START', '33'))
folder = tempfile.mkdtemp(prefix='sv_alina_')
m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], folder)
SS.apply(m, SS.read(path))
rows = []; locked_at = None
for i in range(1, nsteps + 1):
    held = ENGINE.LEFT if (i >= START and (mode == 'hold' or locked_at is None)) else 0
    if mode == 'A' and locked_at is not None:
        held = 0
        if m.msg_visible and (i % 12) < 3: held = ENGINE.A
    pkt = m.step(held, held)
    e = m.state
    if locked_at is None and m.flags() & ENGINE.PLAYER_LOCKED_FLAG: locked_at = i
    cap = None
    if e.cam_pos is not None and e.cam_target is not None:
        cap = math.degrees(math.atan2(e.cam_target[0] - e.cam_pos[0], e.cam_target[2] - e.cam_pos[2]))
    sp = {}
    for k, s in sorted(e.sprites.items()):
        sp[k] = {'id': s['id'], 'pos': None if s['pos'] is None else [round(float(x), 3) for x in s['pos']], 'pose': s['pose'], 'dir': s['dir'], 'vis': s.get('vis', True)}
    p13 = [(a[0] & 0x7ff, a[0], a[1] & 0xff, (a[1] >> 8) & 0xff, a[1]) for t, a, f in pkt if t == 13 and a and (a[0] & 0x4000) and len(a) > 1]
    snd = [(t, a[0]) for t, a, f in pkt if t in (35, 36, 37) and a]
    raw = [(t, list(a[:4]), [round(float(v), 3) for v in f[:4]]) for t, a, f in pkt if t not in (22, 28, 29)] if i in (842,843,844,845,860,861,862,863) else None
    rows.append({'raw': raw, 'i': i, 'held': held, 'frames': m.frames, 'map': e.game_map, 'msg': bool(m.msg_visible), 'flags': m.flags(), 'cap': cap,
                 'cam_target': None if e.cam_target is None else [round(float(x), 3) for x in e.cam_target],
                 'sprites': sp, 'p13': p13, 'snd': snd, 'music': e.music, 'part': e.part})
json.dump(rows, open(out, 'w'))
print('ok', len(rows), 'locked_at', locked_at)
