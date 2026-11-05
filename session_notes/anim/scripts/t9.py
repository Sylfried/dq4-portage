"""Cycle de vie des emplacements fbx : tous les paquets 31 (chargement / liberation) pendant 3 effets fbx consecutifs, puis le 5e."""
import sys, os, time, json, struct
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
eng = bp.boot(); c = eng.core; rec = bp.Rec(eng)
assert bp.natural_battle(eng)
for i in range(120): eng.step(0, 0)
g = c.export('_ZN6status9g_MonsterE')
for (i, num, grp) in bp.monsters(eng): c.mem_w(g + 8 + 0x538 * i + 0x58 + 0x22, struct.pack('<HH', 9999, 9999))
bp.make_strong(eng)
ids = [int(x) for x in sys.argv[1:]]
rec.override = list(ids)
ev = []
def log(e, pkt):
    for t, a, f in pkt:
        if t == 31: ev.append((e.frames, list(a)))
out, pl = bp.run(eng, frames=3200, log=log, stop_when=lambda e: len(rec.overridden) >= len(ids) and e.frames > rec.overridden[-1][0] + 300)
print('overridden', rec.overridden)
print('31', ev)
