import sys, pickle, numpy as np, os
sys.path.insert(0, '/home/claude/wt45-combat/dq4_pc')
from dq4_pc.world import hd as HD
from scipy import ndimage as ndi
from skimage import measure
C = '/tmp/cb45/cache'
def textures(name_str):
    c = pickle.load(open('%s/carte10_%s.pkl' % (C, name_str), 'rb'))
    return {k: t for k, t in c['textures'].items() if k in c['groupes']}

def pad_wrap(m, n): return np.pad(m, ((n, n), (n, n)), mode='wrap')

# variantes : mask binaire (h, w) float 0/1  ->  champ alpha a la resolution f x (retourne (champ, f))
def v_base(m): return m, 1
def v_gauss(s):
    def f(m):
        p = pad_wrap(m, 4); g = ndi.gaussian_filter(p, s)[4:-4, 4:-4]
        return np.maximum(g, 0.5 * m * 1.0001), 1
    return f
def epx_mask(m, passes):
    a = np.zeros(m.shape + (4,), np.uint8); a[..., 3] = (m * 255).astype(np.uint8)
    a[..., 0] = a[..., 3]  # cle sur alpha
    a = np.pad(a, ((2, 2), (2, 2), (0, 0)), mode='wrap')
    for _ in range(passes): a = HD._x2(a)
    n = 2 * 2 ** passes
    return a[n:-n, n:-n, 3].astype(np.float32) / 255.0
def v_epx(passes, sig):
    def f(m):
        e = epx_mask(m, passes); k = 2 ** passes
        if sig > 0: e = ndi.gaussian_filter(np.pad(e, k * 2, mode='wrap'), sig)[2 * k:-2 * k, 2 * k:-2 * k]
        return e, k
    return f
def v_bicub(f=4, sig=0.0):
    def fn(m):
        p = pad_wrap(m, 4)
        z = ndi.zoom(p, f, order=3, mode='nearest')
        z = z[4 * f:-4 * f, 4 * f:-4 * f]
        return np.clip(z, 0, 1), f
    return fn
VARS = {'base': v_base, 'gauss0.5': v_gauss(0.5), 'gauss0.7': v_gauss(0.7), 'epx2': v_epx(1, 0), 'epx4': v_epx(2, 0), 'epx4+g0.5': v_epx(2, 0.5 * 2), 'epx4+g1.0': v_epx(2, 1.0 * 2), 'epx4+g0.75': v_epx(2, 1.5), 'epx4+g1.5': v_epx(2, 3.0), 'epx8+g2': v_epx(3, 2.0), 'bicub4': v_bicub(4)}

def mag(field, f, target=8):
    """simule la magnification GL bilinear de la texture (field a f x) jusqu'a `target` px par texel d'origine"""
    z = target / f
    return ndi.zoom(field, z, order=1, mode='nearest') if z != 1 else field

def roughness(hi, target):
    cs = measure.find_contours(np.pad(hi, 1), 0.5)
    tot_turn = 0.0; tot_len = 0.0
    for c in cs:
        d = np.diff(c, axis=0); seg = np.hypot(d[:, 0], d[:, 1]); L = seg.sum()
        if L < 3 * target: continue
        s = np.r_[0, np.cumsum(seg)]; n = int(L / (0.25 * target)); 
        if n < 8: continue
        u = np.linspace(0, L, n); y = np.interp(u, s, c[:, 0]); x = np.interp(u, s, c[:, 1])
        dy, dx = np.diff(y), np.diff(x); th = np.unwrap(np.arctan2(dy, dx)); tot_turn += np.abs(np.diff(th)).sum(); tot_len += L
    return tot_turn / (tot_len / target) if tot_len else 0.0     # radians de virage cumules par texel de contour

if __name__ == '__main__':
    T = 8
    for name_str in sys.argv[1:]:
        for k, t in textures(name_str).items():
            a = t[..., 3]
            if not ((a == 0).any()): continue
            m = (a >= 128).astype(np.float32)
            print('== %s %s  (opaque %.1f%%)' % (name_str, str(k)[:10], 100 * m.mean()))
            ref = None
            for vn, fn in VARS.items():
                fld, f = fn(m)
                hi = mag(fld, f, T)
                mk = hi >= 0.5
                if ref is None: ref = mk
                iou = (mk & ref).sum() / max(1, (mk | ref).sum())
                print('   %-10s rugosite %.3f rad/texel   surface %+.2f%%   IoU %.4f' % (vn, roughness(hi, T), 100 * (mk.sum() / ref.sum() - 1), iou))
