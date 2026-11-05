import sys, time, json
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
from dq4_pc.core import engine as ENGINE
eng = bp.boot()
rec = bp.Rec(eng); c = eng.core
c.call(eng.E('_ZN7Encount12forceEncountEv'), c.call(eng.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
ok = False
for i in range(900):
    eng.step([0x4, 0x8][(i // 20) % 2], 0)
    if eng.state.part == ENGINE.PART_BATTLE: ok = True; break
print('natural battle', ok, eng.frames, flush=True)
for i in range(400):
    pkt = eng.step(0, 0x10 if i % 8 == 0 else 0)
    if i % 20 == 0:
        print(i, eng.frames, hex(eng.flags()), eng.message_state(), eng.msg_visible, eng.active_menu(), [t for t,a,f in pkt])
print(rec.effects, rec.execs[:4])
