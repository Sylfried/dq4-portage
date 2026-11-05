import sys, time, json
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
eng = bp.boot(); rec = bp.Rec(eng)
print('natural', bp.natural_battle(eng), bp.monsters(eng), flush=True)
fo = bp.Forcer(eng, [])
bp.make_strong(eng)
out, pl = bp.run(eng, frames=900)
print('types', pl.types[:8])
print('effects', rec.effects)
print('execs', rec.execs[:12])
print('nframes', len(out), 'part', hex(eng.state.part))
import collections
cnt = collections.Counter(t for f, k in out for t, a, fl in k); print(cnt)
