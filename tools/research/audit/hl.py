"""Harnais sans fenetre : Moteur (Unicorn) seul. Usage : voir les fonctions. Ecritures de sauvegarde dans /tmp/sv_audit_<nom>."""
import os, sys, time, collections, shutil
sys.path.insert(0, '/home/claude/wt-audit/dq4_pc')
os.chdir('/home/claude/wt-audit/dq4_pc')
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'
def new(name_str='h', read_dir=SAVES):
    wdir = '/tmp/sv_audit_' + name_str; shutil.rmtree(wdir, ignore_errors=True); os.makedirs(wdir)
    return ENGINE.Engine(APK, read_dir, wdir)
class ExampleCounter:
    def __init__(self): self.n = collections.Counter(); self.ex = {}
    def note(self, pkt, image):
        for t, a, f in pkt:
            self.n[t] += 1
            self.ex.setdefault(t, (image, a[:6], [round(x, 3) for x in f[:6]]))
if __name__ == '__main__':
    slot = int(sys.argv[1]) if len(sys.argv) > 1 else 1; N = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    t0 = time.time(); m = new('t%d' % slot); print('init %.1fs' % (time.time() - t0))
    ok = m.load_save(slot); print('slot', slot, ok)
    c = ExampleCounter(); t0 = time.time()
    for i in range(N):
        pkt = m.step(0, 0); c.note(pkt, i)
    print('%d frames in %.1fs ; map=%s part=%#x sprites=%d' % (N, time.time() - t0, m.state.game_map, m.state.part, len(m.state.sprites)))
    for t in sorted(c.n): print(t, c.n[t], c.ex[t])
