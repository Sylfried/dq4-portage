"""Journal pas a pas du vrai moteur apres load_save(1) : sprites (pose, dir), camera, sons, paquets 13."""
import json, math, os, sys, tempfile
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
out = sys.argv[1]; nsteps = int(sys.argv[2]) if len(sys.argv) > 2 else 260
folder = tempfile.mkdtemp(prefix='sv_alina_')
m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], folder)
for _ in range(3): m.step(0, 0)
m.load_save(1)
rows = []
for i in range(1, nsteps + 1):
    m.state.sounds = []
    pkt = m.step(0, 0)
    e = m.state
    cap = None
    if e.cam_pos is not None and e.cam_target is not None:
        cap = math.degrees(math.atan2(e.cam_target[0] - e.cam_pos[0], e.cam_target[2] - e.cam_pos[2]))
    sp = {}
    for k, s in sorted(e.sprites.items()):
        sp[k] = {'id': s['id'], 'pos': None if s['pos'] is None else [round(float(x), 3) for x in s['pos']], 'pose': s['pose'], 'dir': s['dir'], 'vis': s.get('vis', True)}
    p13 = []
    for t, a, f in pkt:
        if t == 13 and a and (a[0] & 0x4000) and len(a) > 1:
            p13.append((a[0] & 0x7ff, a[0], a[1] & 0xff, (a[1] >> 8) & 0xff, a[1]))
    other = [(t, list(a[:3])) for t, a, f in pkt if t in (35, 36, 37)]
    rows.append({'i': i, 'frames': m.frames, 'map': e.game_map, 'msg': bool(m.msg_visible), 'flags': m.flags(), 'cap': cap,
                 'cam_pos': None if e.cam_pos is None else [round(float(x), 3) for x in e.cam_pos],
                 'cam_target': None if e.cam_target is None else [round(float(x), 3) for x in e.cam_target],
                 'sprites': sp, 'p13': p13, 'snd': other, 'sounds': list(e.sounds), 'music': e.music, 'part': e.part})
json.dump(rows, open(out, 'w'))
print('ok', len(rows))
