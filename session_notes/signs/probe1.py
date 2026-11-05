"""Probe 1 : charge la sauvegarde du chapitre 2, journalise les paquets 19/20 (bulles) et les appels de TownRiseupManager::setup (pile d'appel)."""
import os, sys, struct, tempfile, shutil
sys.path.insert(0, '/home/claude/dq4-portage')
import unicorn
from dq4_pc.core import engine as ENGINE
folder = tempfile.mkdtemp(prefix='signs_p1_')
m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], folder)
c = m.core
def stack(uc, depth=8):
    out = []
    lr = uc.reg_read(c.XREG[30]); out.append(c.where(lr))
    fp = uc.reg_read(c.XREG[29])
    for _ in range(depth):
        try:
            nfp, nlr = struct.unpack('<QQ', bytes(uc.mem_read(fp, 16)))
        except Exception: break
        out.append(c.where(nlr)); fp = nfp
        if not fp: break
    return out
calls = []
def hk(uc, a, sz, u):
    calls.append((m.frames, uc.reg_read(c.XREG[1]) & 0xffffffff, stack(uc)))
for name in ('_ZN17TownRiseupManager5setupEiN3dss12Fix32Vector3E',):
    ad = c.export(name); print(name, hex(ad))
    c.uc.hook_add(unicorn.UC_HOOK_CODE, hk, None, ad, ad)
for _ in range(3): m.step(0, 0)
m.load_save(1)
for i in range(600):
    pk = m.step(0, 0)
    for t, a, f in pk:
        if t in (19, 20) and i % 1 == 0 and (t == 19 or i % 20 == 0): print('frame', m.frames, 'pkt', t, a, [round(x, 2) for x in f])
    if i % 100 == 0: print('frame', m.frames, 'part', hex(m.state.part), m.state.game_map, 'flags', hex(m.flags()))
for fr, idd, st in calls: print('Riseup::setup frame', fr, 'id', idd, st)
print('end', hex(m.state.part), m.state.game_map)
shutil.rmtree(folder, ignore_errors=True)
