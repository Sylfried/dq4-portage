"""Enquete #45 decor : plusieurs cartes / cameras dans UN seul lancement (le verrou xvfb est rare). Plan : JSON de {n, carte, pos, cib} ; DC_WT = racine du depot a tester.
Variantes d'essai (jamais dans le depot) : DC_POSER=1 : les decalques plats decoupes sont ramenes sur le sol opaque qui est dessous ; DC_BORDS=1 : couleur des texels transparents etalee (bords_alpha)."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.environ['DC_WT'], 'dq4_pc'))
from dq4_pc.window import game as F
plan = json.load(open(os.environ.get('DQ_DC_PLAN', '/tmp/dc/plan.json')))
orig = F.Game._draw_scene
def patched(self):
    action = None
    for p in plan:
        if p['n'] <= self.n_loop: action = p
    if action is not None:
        os.environ['DQ_CARTE_TEST'] = '%s;%s;%s' % (action['carte'], ','.join('%.4f' % v for v in action['pos']), ','.join('%.4f' % v for v in action['cib']))
        os.environ['DQ_CARTE_SANS_SPR'] = '1'
        v = action.get('var', 'av')
        if v != VAR[0]:                                   # nouvelle variante : on recharge la carte (textures comprises) avec les bascules
            VAR[0] = v; self.map_name = ''; self.tex_gl = {}
    return orig(self)
F.Game._draw_scene = patched
VAR = ['av']

def place(c):
    g = c['groupes']; T = c['textures']
    meta = []; tris = []
    for k, (pos, uv, col) in g.items():
        t = T.get(k)
        if t is None: continue
        P = pos.reshape(-1, 3, 3); cut = bool((t[..., 3] < 250).any()); tr = isinstance(k, tuple) and k[0] == 'tr'
        fl = ((P[..., 1].max(1) - P[..., 1].min(1)) < 1e-3)
        tris.append(P); meta += [(k, i, cut, tr, bool(fl[i])) for i in range(len(P))]
    P = np.concatenate(tris); cut = np.array([m[2] for m in meta]); tr = np.array([m[3] for m in meta]); fl = np.array([m[4] for m in meta])
    X = P[..., [0, 2]]; Y = P[..., 1]
    ax, az = X[:, 0, 0], X[:, 0, 1]; bx, bz = X[:, 1, 0], X[:, 1, 1]; cx, cz = X[:, 2, 0], X[:, 2, 1]
    det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz); ok_t = np.abs(det) > 1e-9; ds = np.where(ok_t, det, 1)
    new_offsets = {}
    for d in np.nonzero(fl & cut & ~tr)[0]:
        q = P[d].mean(0)
        l0 = ((bz - cz) * (q[0] - cx) + (cx - bx) * (q[2] - cz)) / ds; l1 = ((cz - az) * (q[0] - cx) + (ax - cx) * (q[2] - cz)) / ds; l2 = 1 - l0 - l1
        m = ok_t & (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6); m[d] = False
        yy = l0 * Y[:, 0] + l1 * Y[:, 1] + l2 * Y[:, 2]
        below = m & (yy <= q[1] + 1e-4) & ~cut
        if below.any(): new_offsets[meta[d][:2]] = float(yy[below].max()) + 0.002 - q[1]
    for (k, i), dy in new_offsets.items():
        pos, uv, col = g[k]; p2 = np.array(pos, np.float32, copy=True).reshape(-1, 3, 3); p2[i, :, 1] += dy; g[k] = (p2.reshape(-1, 3), uv, col)
    print('DC_POSER : %d decalques ramenes au sol' % len(new_offsets), flush=True)
od = F.DP.shift
def dec2(c, log=None):
    if os.environ.get('DC_POSER') or VAR[0] == 'po': place(c)
    return od(c, log)
F.DP.shift = dec2
import bords_alpha as B
ot_ = F.Game._tex
F.Game._tex = lambda self, arr, repeat, mip=0: ot_(self, B.etaler(arr) if (os.environ.get('DC_BORDS') or VAR[0] == 'bo') else arr, repeat, mip)
F.main()
