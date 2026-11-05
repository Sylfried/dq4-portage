import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/textpos')
from tp_lib import *
import collections
hid = []
for t in sorted(ml.types, key=int):
    ty = int(t); T = ml.types[t]
    if not T.get('nodes'): continue
    w = UM.Window(ml, ty)
    for tn in w.N.values():
        if tn['text'] is None: continue
        dT = tn['pos'][1] + 0.001; ax = tn['pos'][0]; az = tn['pos'][2] - DY
        for m in w.N.values():
            if m is tn or not m['vtx'] or not m['mats']: continue
            if m['pos'][1] <= dT: continue
            xs = [m['pos'][0] + v[0] for v in m['vtx']]; zs = [m['pos'][2] + v[1] for v in m['vtx']]
            if min(xs) <= ax <= max(xs) and min(zs) <= az <= max(zs):
                # le maillage a-t-il de l'opacite a cet endroit ? approx : couleur alpha de la matiere
                col = m['mats'][0].get('color') or (1, 1, 1, 1)
                hid.append((ty, T['name'], tn['id'], round(dT, 3), m['id'], round(m['pos'][1], 3), m['mats'][0].get('part'), round(col[3], 2), m['buttonId']))
print(len(hid))
for h in hid[:60]: print(h)
