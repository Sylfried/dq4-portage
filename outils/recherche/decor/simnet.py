import sys, pickle, numpy as np
sys.path.insert(0, '/home/claude/wt45-decor/dq4_pc')
import bords_alpha as B
from PIL import Image
def bil(a, u, v):      # a (h,w,4) float ; u,v en texels (centre des texels a +0.5)
    h, w = a.shape[:2]; x = u - 0.5; y = v - 0.5
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    def g(xx, yy): return a[np.clip(yy, 0, h - 1), np.clip(xx, 0, w - 1)]
    return (g(x0, y0) * (1 - fx) + g(x0 + 1, y0) * fx) * (1 - fy) + (g(x0, y0 + 1) * (1 - fx) + g(x0 + 1, y0 + 1) * fx) * fy
def rendre(tex, s, cut=0.5, net=True, bgc=(0.45, 0.8, 0.35)):
    a = tex.astype(np.float32) / 255; h, w = a.shape[:2]
    H, W = int(h * s), int(w * s)
    X, Y = np.meshgrid((np.arange(W) + 0.5) / s, (np.arange(H) + 0.5) / s)
    if net:
        wd = 1.0 / s
        bx = np.floor(X + 0.5); by = np.floor(Y + 0.5)
        X = bx + np.clip((X - bx) / wd, -0.5, 0.5); Y = by + np.clip((Y - by) / wd, -0.5, 0.5)
    f = bil(a, X, Y)
    al = f[..., 3]; fw = np.abs(np.gradient(al, axis=1)) + np.abs(np.gradient(al, axis=0))
    cov = np.clip((al - cut) / np.maximum(fw, 1e-4) + 0.5, 0, 1)[..., None]
    back = np.zeros_like(f[..., :3]); back[:] = bgc
    return f[..., :3] * cov + back * (1 - cov)
if __name__ == '__main__':
    c = pickle.load(open('/tmp/cache_dc45/carte10_maout.pkl', 'rb')); T = c['textures']
    rows = []
    for k in (12327, 15081):
        a = T[k]; b = B.etaler(a)
        ra = rendre(a, 2.5); rb = rendre(b, 2.5)
        rows.append(np.concatenate([ra, rb, np.clip(np.abs(ra - rb) * 3, 0, 1)], 1))
        print(k, float(np.abs(ra - rb).mean()), float(np.abs(ra - rb).max()))
    Image.fromarray((np.concatenate(rows, 0) * 255).astype(np.uint8)).resize((960, 640 if False else int(960 * np.concatenate(rows, 0).shape[0] / np.concatenate(rows, 0).shape[1])), Image.NEAREST).save('/tmp/dc/simnet.png')
