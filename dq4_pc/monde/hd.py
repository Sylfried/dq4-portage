"""Lissage HD des feuilles de sprites : agrandissement x8 EPX, calcule
au chargement et mis en cache (aucun fichier du jeu modifie).

Chaque case (24x32) est agrandie séparément puis replacée dans un nouvel atlas avec une marge (gouttière) qui répète
les bords de la case : le filtrage bilinéaire et les mipmaps ne peuvent donc pas faire déborder la case voisine.
Les pixels transparents reprennent la couleur du bord opaque voisin pour éviter les liserés sombres au filtrage.
"""
import numpy as np

VERSION = 3          # a incrementer quand un algorithme change (invalide les caches)
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


def nettoyer_feuille(arr, seuil=128):
    """Feuille de sprites -> (feuille, nettoyee). Les feuilles des heros (h100 a h127) ont un halo d'alpha 1 a 105 de couleur parasite (magenta) autour du corps (alpha 204 a 255) : le jeu
    d'origine ne le montre pas (rejet des pixels transparents) ; sans ce nettoyage il apparait en liseré violet et le corps, d'alpha 0,8 a 1, laisse voir le decor. Alpha < seuil -> 0,
    sinon 255. Les feuilles a alpha binaire (PNJ, monstres) sont rendues telles quelles."""
    al = arr[..., 3]
    if not ((al > 0) & (al < 255)).any(): return arr, False
    a = arr.copy(); a[..., 3] = np.where(al >= seuil, 255, 0)
    return a, True


def agrandir_epx(case, passes=3):
    """EPX/Scale2x itere (x8) ; repli bicubique si l'alpha est deja adouci (feuilles filtrees d'origine)."""
    if _nb_alpha(case) > 8: return agrandir_bicubique(case, 2 ** passes)
    a = _dilater(case)
    for _ in range(passes): a = _x2(a)
    return a


def agrandir_case(case, passes=3):
    return agrandir_epx(case, passes)


def agrandir_feuille(arr, larg, haut, colonnes, lignes, algo=None, gout=4, facteur=FACTEUR):
    """Feuille de sprites -> (atlas HD, case_l, case_h) ; `facteur` = 1 pour les feuilles d'origine (gouttière seule) ; la case (col, ligne) commence à
    (col*(case_l+2*gout)+gout, ligne*(case_h+2*gout)+gout) dans l'atlas (origine en haut à gauche)."""
    algo = algo or agrandir_epx
    cl, ch = larg * facteur, haut * facteur
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


# (nom affiche, identifiant de cache, fonction) ; l'indice 0 = sprites d'origine (pixels nets, sans agrandissement), 1 = EPX x8 ; le mode 4 (pixel perfect) est gere par fenetre.py
# (« regions lissees » et « bicubique » ont ete retires : ils floutaient les contours au lieu de les affiner ; agrandir_bicubique ne sert plus que de repli d'EPX pour les feuilles deja adoucies)
MODES = [('Originaux (pixels nets)', None, None),
         ('EPX x8', 'epx', agrandir_epx)]


# ---- plans des fenetres de carte (256 x 256 affiches en 4:3) ------------------------------------------------------

def agrandir_plan(a, larg=1024, haut=768, epx=False):
    """Plan de carte (RGBA 256 x 256, affiche en 4:3) agrandi en Lanczos puis legerement accentue : bien plus net qu'un simple filtrage lineaire de la carte graphique (alpha pre-multiplie).
    `epx` (plan du monde, dont les terres sont en pixel art sur fond peint) : deux passes EPX arrondissent d'abord les contours des terres."""
    from PIL import Image, ImageFilter
    if epx:
        for _ in range(2): a = _x2(a)
        im = Image.fromarray(a).filter(ImageFilter.GaussianBlur(1.1))
        r = np.array(im.resize((larg, haut), Image.LANCZOS))
    else:
        r = np.array(Image.fromarray(a).convert('RGBa').resize((larg, haut), Image.LANCZOS).convert('RGBA'))
    rgb = np.array(Image.fromarray(r[..., :3]).filter(ImageFilter.UnsharpMask(radius=1.6, percent=45, threshold=2)))
    r[..., :3] = rgb
    return r


def voiler_plan(plan, masque, cle, x0=48, y0=16, bloc=10, f=4):
    """Pose sur le plan agrandi (1024 x 768) le voile des blocs non explores de la carte du monde. `masque` : silhouette grisee des terres (192 x 256 RGBA, alpha 255 sur la terre, 3 sur la mer),
    `cle` : 16 entiers, bit leve = bloc de `bloc` x `bloc` pixels non explore (16 x 16 blocs a partir de (x0, y0) dans le plan de 256 x 192). Le jeu pose des blocs carres ; ici la silhouette (contour arrondi)
    et la limite des blocs sont lissees apres agrandissement, ce qui evite l'effet d'escalier sans changer ce qui est cache."""
    h, w = masque.shape[:2]
    R = lambda n, s: _matrice_interp(n, f, s)
    Ry, Rx = R(h, 4.5), R(w, 4.5)
    terre = np.clip((masque[..., 3].astype(np.float32) - 3) / 252.0, 0, 1)
    t_hd = Ry @ terre @ Rx.T
    alpha_t = np.clip((t_hd - 0.36) * 3.0 + 0.5, 0, 1)          # seuil un peu sous 0,5 : le contour recouvre la frange verte du plan sous la silhouette
    coul = np.stack([(Ry @ (masque[..., k].astype(np.float32) * terre) @ Rx.T) / np.maximum(t_hd, 1e-3) for k in range(3)], -1)
    v = np.zeros((h, w), np.float32)
    for r, m in enumerate(cle[:16]):
        for c in range(16):
            if m >> c & 1: v[y0 + bloc * r:y0 + bloc * (r + 1), x0 + bloc * c:x0 + bloc * (c + 1)] = 1.0
    Ry2, Rx2 = R(h, 5.0), R(w, 5.0)
    v_hd = np.clip((Ry2 @ v @ Rx2.T - 0.5) * 3.0 + 0.5, 0, 1)
    a = (alpha_t * v_hd)[..., None]
    out = plan.copy()
    out[..., :3] = np.clip(plan[..., :3].astype(np.float32) * (1 - a) + coul * a + 0.5, 0, 255).astype(np.uint8)
    return out
