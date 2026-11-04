import sys; sys.path.insert(0, '/tmp/cam45')
import cam45_h as H; from dq4_pc.noyau import moteur as MO
m = H.nouveau('cam45e')
nom = sys.argv[1]
m.demarrer_ville(nom)
for _ in range(80): m.step(0, 0)
n = 0; prev = None; out = []
seq = (MO.HAUT, MO.BAS, MO.GAUCHE, MO.DROITE, MO.HAUT | MO.GAUCHE, MO.BAS | MO.DROITE, MO.HAUT | MO.DROITE, MO.BAS | MO.GAUCHE)
for pad in seq:
    for i in range(160):
        m.step(pad, pad if i == 0 else 0); n += 1
        r = H.releve(m)
        if r['h'] is None or r['cc'] is None: continue
        out.append((n, pad, r['h'], r['cc'], r['cp']))
import pickle; pickle.dump(out, open('/tmp/cam45/tr_%s.pkl' % nom, 'wb'))
ys = [o[2][1] for o in out]
print(nom, 'hero Y', min(ys), max(ys))
# affiche les pas ou Y change
last = None; k = 0
for n, pad, h, cc, cp in out:
    if last is None or abs(h[1] - last) > 1e-6:
        if k < 80: print(n, pad, 'h', tuple(round(v, 3) for v in h), 'cc', tuple(round(v, 3) for v in cc), 'cpY', round(cp[1], 3))
        k += 1; last = h[1]
print('changements de Y :', k)
