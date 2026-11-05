import sys
sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
import collections
eng = new('pt'); c = eng.core; tr = Trace(eng)
eng.load_save(1)
for _ in range(200): eng.step(0, 0)
cnt = collections.Counter(); ex = {}
orig_step = eng.step
def step(*a, **k):
    pkt = orig_step(*a, **k)
    for t, aa, f in pkt:
        cnt[t] += 1; ex.setdefault(t, (eng.frames, list(aa[:6]), [round(x, 2) for x in f[:4]]))
    return pkt
eng.step = step
cb = Battle(eng, tr, monsters=[(3, 4), (4, 4), (5, 4)], hp=[1, 1, 1, 1, 1])
cb.launch(max_step=3000, after_battle=100)
for t in sorted(cnt): print(t, cnt[t], ex[t])
