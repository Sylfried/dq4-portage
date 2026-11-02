import sys
sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
import collections
mo = nouveau('pt'); c = mo.core; tr = Trace(mo)
mo.charger_sauvegarde(1)
for _ in range(200): mo.step(0, 0)
cnt = collections.Counter(); ex = {}
orig_step = mo.step
def step(*a, **k):
    pq = orig_step(*a, **k)
    for t, aa, f in pq:
        cnt[t] += 1; ex.setdefault(t, (mo.images, list(aa[:6]), [round(x, 2) for x in f[:4]]))
    return pq
mo.step = step
cb = Combat(mo, tr, monstres=[(3, 4), (4, 4), (5, 4)], hp=[1, 1, 1, 1, 1])
cb.lancer(max_pas=3000, apres_combat=100)
for t in sorted(cnt): print(t, cnt[t], ex[t])
