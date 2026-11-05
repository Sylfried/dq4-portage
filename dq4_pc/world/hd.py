"""Lissage HD des feuilles de sprites : agrandissement x8 EPX, calcule
au chargement et mis en cache (aucun fichier du jeu modifie).

Chaque case (24x32) est agrandie séparément puis replacée dans un nouvel atlas avec une marge (gouttière) qui répète
les bords de la case : le filtrage bilinéaire et les mipmaps ne peuvent donc pas faire déborder la case voisine.
Les pixels transparents reprennent la couleur du bord opaque voisin pour éviter les liserés sombres au filtrage.
"""
import numpy as np

VERSION = 3          # a incrementer quand un algorithme change (invalide les caches)
FACTOR = 8


# Feuilles qui ne se decoupent pas en cases de personnage de 24 x 32 sur 3 colonnes. Chara.SetTexture (libdq4core, libunity 0xCCC6F8) : l'identifiant 193, le bateau de la carte du monde (deux sprites : le navire,
# rangees 0 a 4, et son sillage, rangees 5 a 9), prend le maillage « mesh12 » : carre de 0,8 x 0,8 (contre 0,48 x 0,64 pour un personnage), cases de 40 x 40, 12 colonnes ; 194 est un alias de 193.
# identifiant -> (largeur de case, hauteur de case, colonnes, rangees, rapport de largeur du panneau, rapport de hauteur du panneau)
SPECIAL_SHEETS = {193: (40, 40, 12, 10, 0.8 / 0.48, 0.8 / 0.64)}
SHEET_ALIASES = {194: 193}


def sheet_geometry(ident, arr, wid=24, topmost=32, cols=3):
    """Decoupage de la feuille `h<ident>` : dict(ident, larg, haut, cols, nl, pw, ph, standard). ident : l'alias est deja resolu (193 pour 194) ; nl : rangees (4 pour un personnage, 8 si la 5e rangee n'est pas vide) ;
    pw, ph : rapport du panneau dessine a celui d'un personnage (1 sauf pour le bateau)."""
    ident = SHEET_ALIASES.get(ident, ident)
    if ident in SPECIAL_SHEETS:
        l, h, c, nl, pw, ph = SPECIAL_SHEETS[ident]
        return dict(ident=ident, larg=l, haut=h, cols=c, nl=nl, pw=pw, ph=ph, standard=False)
    nl = 8 if arr[4 * topmost:5 * topmost, :cols * wid, 3].any() else 4
    return dict(ident=ident, larg=wid, haut=topmost, cols=cols, nl=nl, pw=1.0, ph=1.0, standard=True)


def uv_cell(f, col, row):
    """(u0, u1, v0, v1) de la case (colonne, rangee) d'un atlas de feuille `f` (origine ou HD, gouttieres exclues) ; v1 = haut de la case (Unity : v = 0 en bas de la texture)."""
    pl, ph, g = f['cl'] + 2 * f['g'], f['ch'] + 2 * f['g'], f['g']
    return (col * pl + g) / f['tw'], (col * pl + g + f['cl']) / f['tw'], 1 - (row * ph + g + f['ch']) / f['th'], 1 - (row * ph + g) / f['th']


def _key(a):
    """Clé de comparaison de pixels : RGBA sur 32 bits, tout pixel quasi transparent = 0."""
    k = np.ascontiguousarray(a).view('<u4')[..., 0].copy()
    k[a[..., 3] < 8] = 0
    return k


def _dilate(a, step=2):
    """Donne aux pixels transparents la couleur d'un voisin opaque (alpha inchangé), `step` fois."""
    a = a.copy()
    for _ in range(step):
        op = a[..., 3] >= 8
        if op.all() or not op.any(): break
        pad = np.pad(a, ((1, 1), (1, 1), (0, 0)))
        po = np.pad(op, 1)
        h, w = op.shape
        new = a.copy(); done = op.copy()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            vois = pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]; vo = po[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            take = ~done & vo
            new[take, :3] = vois[take, :3]; done |= take
        a = new
    return a


def _x2(a):
    """EPX (Scale2x) : chaque pixel devient 4 ; les coins prennent la couleur du voisin quand deux voisins adjacents sont identiques."""
    k = _key(a)
    p = lambda m: np.pad(m, ((1, 1), (1, 1)) + ((0, 0),) * (m.ndim - 2), mode='edge')
    ap, kp = p(a), p(k)
    A, D, C, B = ap[:-2, 1:-1], ap[2:, 1:-1], ap[1:-1, :-2], ap[1:-1, 2:]
    kA, kD, kC, kB = kp[:-2, 1:-1], kp[2:, 1:-1], kp[1:-1, :-2], kp[1:-1, 2:]
    h, w = k.shape
    out = np.empty((2 * h, 2 * w, 4), np.uint8)
    out[0::2, 0::2] = np.where(((kC == kA) & (kC != kD) & (kA != kB))[..., None], A, a)
    out[0::2, 1::2] = np.where(((kA == kB) & (kA != kC) & (kB != kD))[..., None], B, a)
    out[1::2, 0::2] = np.where(((kD == kC) & (kD != kB) & (kC != kA))[..., None], C, a)
    out[1::2, 1::2] = np.where(((kB == kD) & (kB != kA) & (kD != kC))[..., None], D, a)
    return out


def _alpha_count(cell): return len(np.unique(cell[..., 3]))


def clean_sheet(arr, threshold=128):
    """Feuille de sprites -> (feuille, nettoyee). Les feuilles des heros (h100 a h127) ont un halo d'alpha 1 a 105 de couleur parasite (magenta) autour du corps (alpha 204 a 255) : le jeu
    d'origine ne le montre pas (rejet des pixels transparents) ; sans ce nettoyage il apparait en liseré violet et le corps, d'alpha 0,8 a 1, laisse voir le decor. Alpha < seuil -> 0,
    sinon 255. Les feuilles a alpha binaire (PNJ, monstres) sont rendues telles quelles."""
    al = arr[..., 3]
    if not ((al > 0) & (al < 255)).any(): return arr, False
    a = arr.copy(); a[..., 3] = np.where(al >= threshold, 255, 0)
    return a, True


def upscale_epx(cell, passes=3):
    """EPX/Scale2x itere (x8) ; repli bicubique si l'alpha est deja adouci (feuilles filtrees d'origine)."""
    if _alpha_count(cell) > 8: return upscale_bicubic(cell, 2 ** passes)
    a = _dilate(cell)
    for _ in range(passes): a = _x2(a)
    return a


def upscale_cell(cell, passes=3):
    return upscale_epx(cell, passes)


def upscale_sheet(arr, wid, topmost, columns, lines, algo=None, gutter=4, factor=FACTOR):
    """Feuille de sprites -> (atlas HD, case_l, case_h) ; `factor` = 1 pour les feuilles d'origine (gouttière seule) ; la case (col, ligne) commence à
    (col*(case_l+2*gout)+gout, ligne*(case_h+2*gout)+gout) dans l'atlas (origine en haut à gauche)."""
    algo = algo or upscale_epx
    cl, ch = wid * factor, topmost * factor
    pl, ph = cl + 2 * gutter, ch + 2 * gutter
    atlas = np.zeros((lines * ph, columns * pl, 4), np.uint8)
    for r in range(lines):
        for c in range(columns):
            cell = arr[r * topmost:(r + 1) * topmost, c * wid:(c + 1) * wid]
            if cell.shape[:2] != (topmost, wid): continue
            g = np.pad(algo(cell), ((gutter, gutter), (gutter, gutter), (0, 0)), mode='edge')
            atlas[r * ph:(r + 1) * ph, c * pl:(c + 1) * pl] = g
    return atlas, cl, ch


# ---- autres algorithmes -------------------------------------------------------------------------------------------

def _interp_matrix(n_in, f, sigma=0.0):
    """Matrice (n_in*f, n_in) d'interpolation bilineaire (centres de pixels alignes), suivie d'un flou gaussien (sigma en pixels de sortie)."""
    n_out = n_in * f
    x = (np.arange(n_out) + 0.5) / f - 0.5
    i0 = np.floor(x).astype(int); t = (x - i0).astype(np.float32)
    M = np.zeros((n_out, n_in), np.float32); r = np.arange(n_out)
    M[r, np.clip(i0, 0, n_in - 1)] += 1 - t
    M[r, np.clip(i0 + 1, 0, n_in - 1)] += t
    if sigma > 0:
        d = np.arange(n_out)
        G = np.exp(-0.5 * ((d[:, None] - d[None, :]) / sigma) ** 2).astype(np.float32)
        G /= G.sum(1, keepdims=True)
        M = G @ M
    return M


def upscale_bicubic(cell, f=8):
    """Interpolation bicubique x f (alpha pre-multiplie, contraste d'alpha pour garder une silhouette nette)."""
    from PIL import Image
    h, w = cell.shape[:2]
    im = Image.fromarray(_dilate(cell)).convert('RGBa').resize((w * f, h * f), Image.BICUBIC).convert('RGBA')
    a = np.array(im)
    al = a[..., 3].astype(np.float32) / 255
    a[..., 3] = (np.clip((al - 0.5) * 3 + 0.5, 0, 1) * 255).astype(np.uint8)
    return _dilate(a, 3)


# (nom affiche, identifiant de cache, fonction) ; l'indice 0 = sprites d'origine (pixels nets, sans agrandissement), 1 = EPX x8 ; le mode 4 (pixel perfect) est gere par window.py
# (« regions lissees » et « bicubique » ont ete retires : ils floutaient les contours au lieu de les affiner ; upscale_bicubic ne sert plus que de repli d'EPX pour les feuilles deja adoucies)
MODES = [('Originaux (pixels nets)', None, None),
         ('EPX x8', 'epx', upscale_epx)]


# ---- plans des fenetres de carte (256 x 256 affiches en 4:3) ------------------------------------------------------

def upscale_plan(a, wid=1024, topmost=768, epx=False):
    """Plan de carte (RGBA 256 x 256, affiche en 4:3) agrandi en Lanczos puis legerement accentue : bien plus net qu'un simple filtrage lineaire de la carte graphique (alpha pre-multiplie).
    `epx` (plan du monde, dont les terres sont en pixel art sur fond peint) : deux passes EPX arrondissent d'abord les contours des terres."""
    from PIL import Image, ImageFilter
    if epx:
        for _ in range(2): a = _x2(a)
        im = Image.fromarray(a).filter(ImageFilter.GaussianBlur(1.1))
        r = np.array(im.resize((wid, topmost), Image.LANCZOS))
    else:
        r = np.array(Image.fromarray(a).convert('RGBa').resize((wid, topmost), Image.LANCZOS).convert('RGBA'))
    rgb = np.array(Image.fromarray(r[..., :3]).filter(ImageFilter.UnsharpMask(radius=1.6, percent=45, threshold=2)))
    r[..., :3] = rgb
    return r


def veil_plan(plan, mask, lookup_key, x0=48, y0=16, block=10, f=4):
    """Pose sur le plan agrandi (1024 x 768) le voile des blocs non explores de la carte du monde. `mask` : silhouette grisee des terres (192 x 256 RGBA, alpha 255 sur la terre, 3 sur la mer),
    `lookup_key` : 16 entiers, bit leve = bloc de `block` x `block` pixels non explore (16 x 16 blocs a partir de (x0, y0) dans le plan de 256 x 192). Le jeu pose des blocs carres ; ici la silhouette (contour arrondi)
    et la limite des blocs sont lissees apres agrandissement, ce qui evite l'effet d'escalier sans changer ce qui est cache."""
    h, w = mask.shape[:2]
    R = lambda n, s: _interp_matrix(n, f, s)
    Ry, Rx = R(h, 4.5), R(w, 4.5)
    land = np.clip((mask[..., 3].astype(np.float32) - 3) / 252.0, 0, 1)
    t_hd = Ry @ land @ Rx.T
    alpha_t = np.clip((t_hd - 0.36) * 3.0 + 0.5, 0, 1)          # seuil un peu sous 0,5 : le contour recouvre la frange verte du plan sous la silhouette
    clr = np.stack([(Ry @ (mask[..., k].astype(np.float32) * land) @ Rx.T) / np.maximum(t_hd, 1e-3) for k in range(3)], -1)
    v = np.zeros((h, w), np.float32)
    for r, m in enumerate(lookup_key[:16]):
        for c in range(16):
            if m >> c & 1: v[y0 + block * r:y0 + block * (r + 1), x0 + block * c:x0 + block * (c + 1)] = 1.0
    Ry2, Rx2 = R(h, 5.0), R(w, 5.0)
    v_hd = np.clip((Ry2 @ v @ Rx2.T - 0.5) * 3.0 + 0.5, 0, 1)
    a = (alpha_t * v_hd)[..., None]
    out = plan.copy()
    out[..., :3] = np.clip(plan[..., :3].astype(np.float32) * (1 - a) + clr * a + 0.5, 0, 255).astype(np.uint8)
    return out
