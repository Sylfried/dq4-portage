import sys, time, json, struct
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
eng = bp.boot(); rec = bp.Rec(eng); c = eng.core
print('natural', bp.natural_battle(eng), flush=True)
for i in range(120): eng.step(0, 0)
ms = bp.monsters(eng); print('monstres', ms)
g = c.export('_ZN6status9g_MonsterE')
for (i, num, grp) in ms:
    base = g + 8 + 0x538 * i
    print('mon', i, num, 'hp?', struct.unpack('<4H', c.mem(base + 0x58 + 0x22, 8)))
    c.mem_w(base + 0x58 + 0x22, struct.pack('<HH', 9999, 9999))
fo = bp.Forcer(eng, [1, 13, 4, 10])
bp.make_strong(eng)
out, pl = bp.run(eng, frames=1500, stop_when=lambda e: len(rec.execs) >= 4 and e.frames > rec.execs[-1][0] + 120)
print('forced', fo.done)
print('execs', rec.execs)
print('effects', rec.effects)
import collections
for f0, eid in rec.effects[:5]:
    seg = [(f, k) for f, k in out if f0 <= f < f0 + 150]
    models = collections.Counter(); fbx = []; ev = []
    for f, k in seg:
        for t, a, fl in k:
            if t == 21: models[a[1]] += 1
            elif t == 31: fbx.append((f, a))
            elif t in (24, 25, 33, 35): ev.append((f, t, a, fl[:3]))
    print('effet', eid, 'image', f0, 'modeles', dict(models), 'fbx', fbx[:3], 'evts', ev[:6])
