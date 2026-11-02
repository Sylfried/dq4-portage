import sys, collections
sys.path.insert(0, '/tmp/audit')
import hl, balayage as B
m = B.moteur('ech', 1)
for nom in sys.argv[1:]:
    m.demarrer_ville(nom); sc = {}; ids = {}
    for i in range(70):
        for t, a, f in m.step(0, 0):
            if t == 12 and len(a) >= 2 and a[1] >= 0: ids[a[0]] = a[1]
            if t == 13 and a and a[0] & 0x800 and f: sc[a[0] & 0x7ff] = round(float(f[0]), 4)
    print(nom, {s: (ids.get(s), v) for s, v in sorted(sc.items())}, flush=True)
