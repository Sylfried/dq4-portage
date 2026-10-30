"""Lissage HD des feuilles de sprites : plusieurs algorithmes d'agrandissement x8 (EPX, regions lissees, bicubique), calcules
au chargement et mis en cache (aucun fichier du jeu modifie).

Chaque case (24x32) est agrandie séparément puis replacée dans un nouvel atlas avec une marge (gouttière) qui répète
les bords de la case : le filtrage bilinéaire et les mipmaps ne peuvent donc pas faire déborder la case voisine.
Les pixels transparents reprennent la couleur du bord opaque voisin pour éviter les liserés sombres au filtrage.
"""
import numpy as np

VERSION = 2          # a incrementer quand un algorithme change (invalide les caches)
FACTEUR = 8


def _cle(a):
    """Clé de comparaison de pixels : RGBA sur 32 bits, tout pixel quasi transparent = 0."""
    k = np.ascontiguousarray(a).view('<u4')[..., 0].copy()
    k[a[..., 3] < 8] = 0
    return k


def _dilater(a, pas=2):
    """Donne aux pixels transparents la couleur d'un voisin opaque (alpha inchangé), `pas` fois."""
    a = a.copy()
    for _ in range(pas):
        op = a[..., 3] >= 8
        if op.all() or not op.any(): break
        pad = np.pad(a, ((1, 1), (1, 1), (0, 0)))
        po = np.pad(op, 1)
        h, w = op.shape
        nouveau = a.copy(); fait = op.copy()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            vois = pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]; vo = po[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            prendre = ~fait & vo
            nouveau[prendre, :3] = vois[prendre, :3]; fait |= prendre
        a = nouveau
    return a


def _x2(a):
    """EPX (Scale2x) : chaque pixel devient 4 ; les coins prennent la couleur du voisin quand deux voisins adjacents sont identiques."""
    k = _cle(a)
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


def _nb_alpha(case): return len(np.unique(case[..., 3]))


def agrandir_epx(case, passes=3):
    """EPX/Scale2x itere (x8) ; repli bicubique si l'alpha est deja adouci (feuilles filtrees d'origine)."""
    if _nb_alpha(case) > 8: return agrandir_bicubique(case, 2 ** passes)
    a = _dilater(case)
    for _ in range(passes): a = _x2(a)
    return a


def agrandir_case(case, passes=3):
    return agrandir_epx(case, passes)


def agrandir_feuille(arr, larg, haut, colonnes, lignes, algo=None, gout=4):
    """Feuille de sprites -> (atlas HD, case_l, case_h) ; la case (col, ligne) commence à
    (col*(case_l+2*gout)+gout, ligne*(case_h+2*gout)+gout) dans l'atlas (origine en haut à gauche)."""
    algo = algo or agrandir_epx
    cl, ch = larg * FACTEUR, haut * FACTEUR
    pl, ph = cl + 2 * gout, ch + 2 * gout
    atlas = np.zeros((lignes * ph, colonnes * pl, 4), np.uint8)
    for r in range(lignes):
        for c in range(colonnes):
            case = arr[r * haut:(r + 1) * haut, c * larg:(c + 1) * larg]
            if case.shape[:2] != (haut, larg): continue
            g = np.pad(algo(case), ((gout, gout), (gout, gout), (0, 0)), mode='edge')
            atlas[r * ph:(r + 1) * ph, c * pl:(c + 1) * pl] = g
    return atlas, cl, ch


# ---- autres algorithmes -------------------------------------------------------------------------------------------

def _matrice_interp(n_in, f, sigma=0.0):
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


def agrandir_bicubique(case, f=8):
    """Interpolation bicubique x f (alpha pre-multiplie, contraste d'alpha pour garder une silhouette nette)."""
    from PIL import Image
    h, w = case.shape[:2]
    im = Image.fromarray(_dilater(case)).convert('RGBa').resize((w * f, h * f), Image.BICUBIC).convert('RGBA')
    a = np.array(im)
    al = a[..., 3].astype(np.float32) / 255
    a[..., 3] = (np.clip((al - 0.5) * 3 + 0.5, 0, 1) * 255).astype(np.uint8)
    return _dilater(a, 3)


def agrandir_regions(case, passes=2, f=2, flou=0.9, max_classes=40):
    """Regions lissees : EPX x2**passes, puis chaque couleur devient un masque interpole en bilineaire x f, floute, et
    chaque pixel prend la couleur dont le masque est le plus fort (contours arrondis, aplats nets). Repli bicubique si trop de couleurs."""
    a = _dilater(case)
    for _ in range(passes): a = _x2(a)
    k = _cle(a)
    uniq, inv = np.unique(k, return_inverse=True)
    if len(uniq) > max_classes: return agrandir_bicubique(case, f * 2 ** passes)
    h, w = k.shape
    inv = inv.reshape(h, w)
    Ry, Rx = _matrice_interp(h, f, flou * f), _matrice_interp(w, f, flou * f)
    best = None; lab = np.zeros((h * f, w * f), np.int32)
    for c in range(len(uniq)):
        m = (inv == c).astype(np.float32)
        v = Ry @ m @ Rx.T
        if best is None: best = v
        else:
            sup = v > best; best = np.where(sup, v, best); lab[sup] = c
    couleur = np.zeros((len(uniq), 4), np.uint8)
    for c in range(len(uniq)):
        y, x = np.argwhere(inv == c)[0]; couleur[c] = a[y, x]
        if uniq[c] == 0: couleur[c, 3] = 0
    return _dilater(couleur[lab], 3)


# (nom affiche, identifiant de cache, fonction) ; l'indice 0 = sprites d'origine (pixels nets, sans agrandissement)
MODES = [('Originaux (pixels nets)', None, None),
         ('EPX x8', 'epx', agrandir_epx),
         ('Regions lissees', 'reg', agrandir_regions),
         ('Bicubique (doux)', 'bic', lambda c: agrandir_bicubique(c, FACTEUR))]
