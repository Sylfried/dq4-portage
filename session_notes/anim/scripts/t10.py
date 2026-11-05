import sys, struct
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
eng = bp.boot(); rec = bp.Rec(eng); c = eng.core
assert bp.natural_battle(eng)
for i in range(120): eng.step(0, 0)
g = c.export('_ZN6status9g_MonsterE')
for (i, num, grp) in bp.monsters(eng): c.mem_w(g + 8 + 0x538 * i + 0x58 + 0x22, struct.pack('<HH', 9999, 9999))
bp.make_strong(eng, 999, 999)
orig, mem = bp.players(eng); print('orig', hex(orig), 'membres', mem)
fo = bp.Forcer(eng, [13, 50])
out, pl = bp.run(eng, frames=1500, stop_when=lambda e: len(fo.done) >= 2 and e.frames > fo.done[-1][0] + 300)
print('forced', fo.done); print('execs', [(f, hex(a), act) for f, a, act in rec.execs]); print('effects', rec.effects)
