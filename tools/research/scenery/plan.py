import pickle, json, numpy as np, sys
maps = sys.argv[1:]
plan = []; n = 20
for name_str in maps:
    c = pickle.load(open('/tmp/cache_dc45/carte10_%s.pkl' % name_str, 'rb')); T = c['textures']
    centers = []
    for k, (pos, uv, col) in c['groupes'].items():
        t = T.get(k)
        if t is None or (isinstance(k, tuple) and k[0] == 'tr'): continue
        if not (t[..., 3] < 250).any(): continue
        P = pos.reshape(-1, 3, 3); fl = ((P[..., 1].max(1) - P[..., 1].min(1)) < 1e-3)
        if fl.any(): centers.append(P[fl].mean(1))
    centers = np.concatenate(centers)
    tx, ty, tz = [float(v) for v in np.median(centers, axis=0)]
    print(name_str, 'cible', round(tx, 2), round(ty, 2), round(tz, 2), 'nflat', len(centers))
    for k, tag in ((1.0, 'g'), (0.33, 'z')):
        off = np.array([0.0, 28.94, -26.96]) * k
        plan.append(dict(n=n, carte=name_str, pos=[tx, ty + off[1], tz + off[2]], cib=[tx, ty, tz], tag=tag))
        n += 14
json.dump(plan, open('/tmp/dc/plan.json', 'w')); print('frames', [p['n'] + 13 for p in plan])
