"""Hypothese : le moteur attend de Unity l'appel ModelObject::setMotionEnd(emplacement) a la fin de l'animation d'un fbx d'effet (ModelObject::isEnd lit le bit de l'emplacement, mis par startAnimation, efface par setMotionEnd).
Test : on appelle setMotionEnd(emplacement) 40 images apres le chargement ; on regarde si le moteur libere l'emplacement (paquet 31 < 0) et charge le 5e fbx."""
import sys, os, time, json, struct
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
eng = bp.boot(); c = eng.core; rec = bp.Rec(eng)
assert bp.natural_battle(eng)
for i in range(120): eng.step(0, 0)
g = c.export('_ZN6status9g_MonsterE')
for (i, num, grp) in bp.monsters(eng): c.mem_w(g + 8 + 0x538 * i + 0x58 + 0x22, struct.pack('<HH', 9999, 9999))
bp.make_strong(eng)
ids = [int(x) for x in sys.argv[2:]]; mode = sys.argv[1]
rec.override = list(ids)
sme = c.export('_ZN11ModelObject12setMotionEndEi')
uif = c.export('_ZN11ModelObject14unityIndexFlagE')
ev = []; pend = []
def log(e, pkt):
    for t, a, f in pkt:
        if t == 31: ev.append((e.frames, list(a)))
        if t == 31 and a[1] >= 0: pend.append((e.frames + 40, a[0]))
    if mode == 'ack':
        for item in list(pend):
            if e.frames >= item[0]:
                pend.remove(item); c.call(sme, item[1], label='setMotionEnd'); ev.append((e.frames, 'setMotionEnd', item[1], 'flag=%#x' % struct.unpack('<I', c.mem(uif, 4))[0]))
out, pl = bp.run(eng, frames=3600, log=log, stop_when=lambda e: len(rec.overridden) >= len(ids) and e.frames > rec.overridden[-1][0] + 300)
print('overridden', rec.overridden)
print('31 / acks', ev[:8]); print('execs', [(f, hex(a), x) for f, a, x in rec.execs])
