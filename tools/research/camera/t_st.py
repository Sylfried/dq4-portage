import sys; sys.path.insert(0, '/tmp/cam45')
import cam45_h as H; from dq4_pc.core import engine as ENGINE
m = H.new('cam45e')
name_str = sys.argv[1]
m.start_town(name_str)
for _ in range(80): m.step(0, 0)
n = 0; prev = None; out = []
seq = (ENGINE.UP, ENGINE.DOWN, ENGINE.LEFT, ENGINE.RIGHT, ENGINE.UP | ENGINE.LEFT, ENGINE.DOWN | ENGINE.RIGHT, ENGINE.UP | ENGINE.RIGHT, ENGINE.DOWN | ENGINE.LEFT)
for pad in seq:
    for i in range(160):
        m.step(pad, pad if i == 0 else 0); n += 1
        r = H.reading(m)
        if r['h'] is None or r['cc'] is None: continue
        out.append((n, pad, r['h'], r['cc'], r['cp']))
import pickle; pickle.dump(out, open('/tmp/cam45/tr_%s.pkl' % name_str, 'wb'))
ys = [o[2][1] for o in out]
print(name_str, 'hero Y', min(ys), max(ys))
# affiche les pas ou Y change
last = None; k = 0
for n, pad, h, cc, cp in out:
    if last is None or abs(h[1] - last) > 1e-6:
        if k < 80: print(n, pad, 'h', tuple(round(v, 3) for v in h), 'cc', tuple(round(v, 3) for v in cc), 'cpY', round(cp[1], 3))
        k += 1; last = h[1]
print('Y changes:', k)
