import sys, time, json
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
from dq4_pc.core import engine as ENGINE
t0 = time.time()
eng = bp.boot()
rec = bp.Rec(eng)
ok = bp.start_battle(eng, [(1, 2)])
print('battle', ok, 'frames', eng.frames, 'effect', eng.state.effect, 'part', hex(eng.state.part), flush=True)
for i in range(300):
    pkt = eng.step(0, 0x10 if i % 8 == 0 else 0)
    if i % 20 == 0: print(i, eng.frames, hex(eng.state.part), eng.state.effect, eng.state.fade['a'] if eng.state.fade else None, eng.active_menu(), eng.msg_visible, [t for t, a, f in pkt][:8])
print('effects', rec.effects, 'execs', rec.execs[:5])
