import os, sys, struct, shutil, tempfile
sys.path.insert(0, '/home/claude/dq4-portage')
import unicorn
from dq4_pc.core import engine as ENGINE

APK = os.environ.get('DQ_APK', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks')
SAVES = os.environ.get('DQ_SAVES', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735')

def new(slot=1, warm=250):
    f = tempfile.mkdtemp(prefix='sv_inn_')
    m = ENGINE.Engine(APK, SAVES, f)
    for _ in range(3): m.step(0, 0)
    m.load_save(slot)
    for _ in range(warm): m.step(0, 0)
    return m

class Trace:
    FN = ['_ZN12SoundManager6playSeEi', '_ZN12SoundManager7playBgmEi', '_ZN12SoundManager4playEi', '_ZN12SoundManager9playStartEi', '_ZN12SoundManager11playRestartEi',
          '_ZN12SoundManager7stopBgmEi', '_ZN12SoundManager4stopEi', '_ZN12SoundManager10battlePlayEv', '_ZN12SoundManager10battleStopEv', '_ZN12SoundManager8townPlayEv',
          '_ZN12SoundManager9fieldPlayEv', '_ZN5Sound12sePlayDirectEi']
    def __init__(self, eng, extra=()):
        self.eng = eng; c = eng.core; self.c = c; self.evt = []
        for n in list(self.FN) + list(extra):
            a = c.export(n)
            if not a: print('absent', n); continue
            c.uc.hook_add(unicorn.UC_HOOK_CODE, self._h, n, a, a)
        c.uc.ctl_flush_tb()
    def _h(self, uc, addr, sz, name_str):
        c = self.c
        w0 = uc.reg_read(c.XREG[0]) & 0xffffffff
        w1 = uc.reg_read(c.XREG[1]) & 0xffffffff
        stack = [c.where(uc.reg_read(c.XREG[30]))]
        fp = uc.reg_read(c.XREG[29])
        for _ in range(5):
            try: nfp, nlr = struct.unpack('<QQ', c.mem(fp, 16))
            except Exception: break
            if not nfp or nfp <= fp: break
            stack.append(c.where(nlr)); fp = nfp
        self.evt.append((self.eng.frames, name_str, w0, w1, stack))
