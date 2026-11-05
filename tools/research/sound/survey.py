import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
for slot in (1, 2, 3, 4, 5):
    eng = new('s45_%d' % slot)
    ok = eng.load_save(slot)
    for _ in range(150): eng.step(0, 0)
    print('slot', slot, ok, 'part', hex(eng.state.part), 'map', eng.state.game_map, 'members', [(i, hit_points(eng, i)) for i in members(eng)], flush=True)
