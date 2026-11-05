import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
eng = new('b1'); c = eng.core
tr = Trace(eng)
eng.load_save(1)
for _ in range(200): eng.step(0, 0)
party = c.export('_ZN6status7g_PartyE')
for m in (1, 2, 4): c.call(c.export('_ZN6status11PartyStatus3addEi'), party, m, label='add')
print('membres', members(eng))
mem = members(eng)
for i in mem: set_hp(eng, i, 40)
tr.evt.clear()
hp = eval(sys.argv[3]) if len(sys.argv) > 3 else None
cb = Battle(eng, tr, monsters=eval(sys.argv[1]), hp=None, verbose=True)
if hp:
    for i, h in zip(mem, hp): set_hp(eng, i, h)
t0 = time.time(); end = cb.launch(max_step=int(sys.argv[2]))
print('fin', end, 'duree %.1f' % (time.time() - t0), 'pv', [hit_points(eng, i)[0] for i in mem])
