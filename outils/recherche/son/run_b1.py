import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
mo = nouveau('b1'); c = mo.core
tr = Trace(mo)
mo.charger_sauvegarde(1)
for _ in range(200): mo.step(0, 0)
party = c.export('_ZN6status7g_PartyE')
for m in (1, 2, 4): c.call(c.export('_ZN6status11PartyStatus3addEi'), party, m, label='add')
print('membres', membres(mo))
mem = membres(mo)
for i in mem: poser_pv(mo, i, 40)
tr.evt.clear()
hp = eval(sys.argv[3]) if len(sys.argv) > 3 else None
cb = Combat(mo, tr, monstres=eval(sys.argv[1]), hp=None, verbeux=True)
if hp:
    for i, h in zip(mem, hp): poser_pv(mo, i, h)
t0 = time.time(); fin = cb.lancer(max_pas=int(sys.argv[2]))
print('fin', fin, 'duree %.1f' % (time.time() - t0), 'pv', [pv(mo, i)[0] for i in mem])
