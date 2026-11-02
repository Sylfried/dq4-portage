"""Vue de dessus (orthographique) d'une carte du cache : outil d'enquete, pas de GL. usage: topo.py carte sortie.png [px_par_unite] [x0 x1 z0 z1]"""
import sys, pickle, numpy as np
from PIL import Image
def rendre(c, ppu=24, box=None, flat_only=False, ymax=None):
    g = c['groupes']; T = c['textures']
    allp = np.concatenate([p for p, _, _ in g.values()])
    if box is None: box = (allp[:, 0].min(), allp[:, 0].max(), allp[:, 2].min(), allp[:, 2].max())
    x0, x1, z0, z1 = box
    W = int((x1 - x0) * ppu) + 1; H = int((z1 - z0) * ppu) + 1
    img = np.zeros((H, W, 3), np.float32); img[:] = (255, 0, 255); zb = np.full((H, W), -1e9, np.float32)
    order = sorted(g.keys(), key=lambda k: (isinstance(k, tuple) and k[0] == 'tr', k[1] if isinstance(k, tuple) and k[0]=='tr' else 0))
    for k in order:
        if k not in T: continue
        pos, uv, col = g[k]; tex = T[k]; th, tw = tex.shape[:2]
        P = pos.reshape(-1, 3, 3); U = uv.reshape(-1, 3, 2)
        tr = isinstance(k, tuple) and k[0] == 'tr'
        for t in range(len(P)):
            p = P[t]
            if ymax is not None and p[:, 1].min() > ymax: continue
            sx = (p[:, 0] - x0) * ppu; sy = (p[:, 2] - z0) * ppu
            xa, xb = int(max(0, np.floor(sx.min()))), int(min(W - 1, np.ceil(sx.max())))
            ya, yb = int(max(0, np.floor(sy.min()))), int(min(H - 1, np.ceil(sy.max())))
            if xb < xa or yb < ya: continue
            d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
            if abs(d) < 1e-9: continue
            X, Y = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
            l0 = ((sy[1] - sy[2]) * (X - sx[2]) + (sx[2] - sx[1]) * (Y - sy[2])) / d
            l1 = ((sy[2] - sy[0]) * (X - sx[2]) + (sx[0] - sx[2]) * (Y - sy[2])) / d
            l2 = 1 - l0 - l1
            m = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
            if not m.any(): continue
            yv = l0 * p[0, 1] + l1 * p[1, 1] + l2 * p[2, 1]
            u = l0 * U[t, 0, 0] + l1 * U[t, 1, 0] + l2 * U[t, 2, 0]; v = l0 * U[t, 0, 1] + l1 * U[t, 1, 1] + l2 * U[t, 2, 1]
            ti = np.clip((u * tw).astype(int) % tw, 0, tw - 1); tj = np.clip(((1 - v) * th).astype(int) % th, 0, th - 1)   # (haut en premier)
            px = tex[tj, ti].astype(np.float32); a = px[..., 3:4] / 255.0
            cv = np.clip(col.reshape(-1, 3, 4)[t].mean(0), 0, 1)
            if tr: a = a * cv[3]
            sub_zb = zb[ya:yb + 1, xa:xb + 1]
            ok = m & ((a[..., 0] > 0.02) if not tr else (a[..., 0] > 0.02)) & ((yv >= sub_zb - 1e-4) if not tr else (yv >= sub_zb - 0.2))
            if tr: pass
            sub = img[ya:yb + 1, xa:xb + 1]
            rgb = px[..., :3] * cv[:3]
            sub[ok] = (sub[ok] * (1 - a[ok]) + rgb[ok] * a[ok]) if tr else (sub[ok] * (1 - (a[ok] > 0.5)) + rgb[ok] * (a[ok] > 0.5))
            if not tr: sub_zb[ok & (a[..., 0] > 0.5)] = yv[ok & (a[..., 0] > 0.5)]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)), box
if __name__ == '__main__':
    c = pickle.load(open('/tmp/cache_dc45/carte10_%s.pkl' % sys.argv[1], 'rb'))
    ppu = float(sys.argv[3]) if len(sys.argv) > 3 else 24
    box = tuple(float(v) for v in sys.argv[4:8]) if len(sys.argv) > 7 else None
    im, box = rendre(c, ppu, box); im.save(sys.argv[2]); print(box, im.size)
