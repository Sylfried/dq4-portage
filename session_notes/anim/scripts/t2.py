import sys, time, json
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
from dq4_pc.core import engine as ENGINE
eng = bp.boot()
rec = bp.Rec(eng)
ok = bp.start_battle(eng, [(1, 2)])
print('flags', hex(eng.flags()))
for i in range(200):
    pkt = eng.step(0, 0x10 if i % 8 == 0 else 0)
    if i % 20 == 0:
        print(i, eng.frames, hex(eng.flags()), eng.message_state(), eng.msg_visible, eng.active_menu(), [t for t,a,f in pkt])
c = eng.core
# etat du moteur : tache courante ?
