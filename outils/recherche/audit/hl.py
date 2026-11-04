"""Harnais sans fenetre : Moteur (Unicorn) seul. Usage : voir les fonctions. Ecritures de sauvegarde dans /tmp/sv_audit_<nom>."""
import os, sys, time, collections, shutil
sys.path.insert(0, '/home/claude/wt-audit/dq4_pc')
os.chdir('/home/claude/wt-audit/dq4_pc')
from dq4_pc.noyau import moteur as MO
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'
def nouveau(nom='h', lecture=SAVES):
    ecr = '/tmp/sv_audit_' + nom; shutil.rmtree(ecr, ignore_errors=True); os.makedirs(ecr)
    return MO.Moteur(APK, lecture, ecr)
class Compteur:
    def __init__(self): self.n = collections.Counter(); self.ex = {}
    def noter(self, pq, image):
        for t, a, f in pq:
            self.n[t] += 1
            self.ex.setdefault(t, (image, a[:6], [round(x, 3) for x in f[:6]]))
if __name__ == '__main__':
    slot = int(sys.argv[1]) if len(sys.argv) > 1 else 1; N = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    t0 = time.time(); m = nouveau('t%d' % slot); print('init %.1fs' % (time.time() - t0))
    ok = m.charger_sauvegarde(slot); print('slot', slot, ok)
    c = Compteur(); t0 = time.time()
    for i in range(N):
        pq = m.step(0, 0); c.noter(pq, i)
    print('%d images en %.1fs ; carte=%s partie=%#x sprites=%d' % (N, time.time() - t0, m.etat.carte, m.etat.partie, len(m.etat.sprites)))
    for t in sorted(c.n): print(t, c.n[t], c.ex[t])
