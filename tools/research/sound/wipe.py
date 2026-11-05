"""Tout le groupe est battu (PV forces a 1, monstres nombreux) ; usage: wipe.py CHAPITRE [slot] [max_step] -> journal des sons / textes"""
import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
chapter = int(sys.argv[1]); slot = int(sys.argv[2]) if len(sys.argv) > 2 else 1; maxp = int(sys.argv[3]) if len(sys.argv) > 3 else 3500
eng = new('wipe%d' % chapter); c = eng.core; tr = Trace(eng)
eng.load_save(slot)
for _ in range(200): eng.step(0, 0)
gs = c.export('_ZN6status7g_StoryE')
if chapter > 1:
    c.call(c.export('_ZN6status11StoryStatus10setChapterEi'), gs, chapter, label='setChapter')
print('chapitre', struct.unpack('<I', c.mem(gs + 4, 4))[0], 'carte', eng.state.game_map, 'membres', members(eng))
tr.evt.clear(); eng.sensor.drain()
cb = Battle(eng, tr, monsters=[(3, 4), (4, 4), (5, 4)], hp=[1, 1, 1, 1, 1], verbose=True)
end = cb.launch(max_step=maxp, after_battle=500)
