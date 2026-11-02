import pickle, glob, os, sys, numpy as np, collections, json
def analyser(nom):
    c = pickle.load(open('/tmp/cache_dc45/carte10_%s.pkl' % nom, 'rb')); T = c['textures']
    tris = []; meta = []
    for k, (pos, uv, col) in c['groupes'].items():
        t = T.get(k)
        if t is None: continue
        P = pos.reshape(-1, 3, 3); cut = bool((t[..., 3] < 250).any()); tr = isinstance(k, tuple) and k[0] == 'tr'
        fl = ((P[..., 1].max(1) - P[..., 1].min(1)) < 1e-3)
        for i in range(len(P)): pass
        tris.append(P); meta += [(str(k), cut, tr, bool(f)) for f in fl]
    P = np.concatenate(tris); cut = np.array([m[1] for m in meta]); tr = np.array([m[2] for m in meta]); fl = np.array([m[3] for m in meta])
    # decalques : plats, decoupes, non 'tr'
    dec = np.nonzero(fl & cut & ~tr)[0]
    X = P[..., [0, 2]]; Y = P[..., 1]
    ax, az = X[:, 0, 0], X[:, 0, 1]; bx, bz = X[:, 1, 0], X[:, 1, 1]; cx, cz = X[:, 2, 0], X[:, 2, 1]
    det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
    ok_t = np.abs(det) > 1e-9
    res = []
    for d in dec:
        q = P[d].mean(0); qx, qz, qy = q[0], q[2], q[1]
        l0 = ((bz - cz) * (qx - cx) + (cx - bx) * (qz - cz)) / np.where(ok_t, det, 1)
        l1 = ((cz - az) * (qx - cx) + (ax - cx) * (qz - cz)) / np.where(ok_t, det, 1)
        l2 = 1 - l0 - l1
        m = ok_t & (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        m[d] = False
        yy = l0 * Y[:, 0] + l1 * Y[:, 1] + l2 * Y[:, 2]
        below = m & (yy <= qy + 1e-4) & ~cut        # sol opaque sous le decalque
        if below.any(): res.append(round(float(qy - yy[below].max()), 3))
        else: res.append(None)
    return res
if __name__ == '__main__':
    out = {}
    for nom in sys.argv[1:]:
        r = analyser(nom); v = [x for x in r if x is not None]
        out[nom] = dict(n=len(r), sans_sol=len(r) - len(v), hist=collections.Counter(v).most_common(6))
        print(nom, out[nom], flush=True)
