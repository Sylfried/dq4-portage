import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
for slot in (1, 2, 3, 4, 5):
    mo = nouveau('s45_%d' % slot)
    ok = mo.charger_sauvegarde(slot)
    for _ in range(150): mo.step(0, 0)
    print('slot', slot, ok, 'partie', hex(mo.etat.partie), 'carte', mo.etat.carte, 'membres', [(i, pv(mo, i)) for i in membres(mo)], flush=True)
