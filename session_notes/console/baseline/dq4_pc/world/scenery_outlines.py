"""Contours des decors de combat : arbres, montagnes, touffes d'herbe, rochers.

Cause (mesuree, voir tools/test_scenery_outlines.py) : ces silhouettes sont dessinees dans des textures de 256 x 256 dont l'alpha est STRICTEMENT binaire (0 ou 255, jamais de valeur
intermediaire : 41 textures sur 140 decors) ; le decor est agrandi x6 puis affiche sur 1280 a 2560 px de large, un texel y couvre 4 a 10 pixels d'ecran. Le filtrage bilineaire adoucit
la couleur mais le contour (alpha 0,5) suit la grille de texels : marches d'escalier de 4 a 10 px sur toute la bordure, que le MSAA (qui ne lisse que les marches d'UN pixel) ne
touche pas. Les texels transparents sont en outre NOIRS (0, 0, 0) : le bilinaire assombrit d'un liseré sombre la bordure des feuillages.

Remede, sur la seule texture, sans toucher au reste du dessin :
  - l'alpha passe a une resolution x4 : deux passes EPX (Scale2x, qui redresse les marches en pentes droites sans perdre les pointes) puis un flou gaussien de 0,3 texel qui arrondit les
    coins et donne une rampe d'un pixel d'ecran (l'alpha-to-coverage et le seuil de `FRAG` en font un bord anticrenele) ;
  - la couleur (RGB) est agrandie x4 par une interpolation bilineaire (memes positions d'echantillon que le GPU : l'interieur du dessin reste celui de l'original filtre lineairement, a moins d'un niveau
    de gris en moyenne, 9 au pire sur un coin tres contraste) apres avoir donne aux texels transparents la couleur du bord opaque voisin (plus de liseré noir).
Seules les textures decoupees a alpha binaire d'au moins 128 px de cote sont traitees (feuillage, relief, rochers) : les ciels, sols, textures opaques ou semi-transparentes (melange),
petites textures de motifs (grilles, torches) restent telles quelles.
"""
import numpy as np
from dq4_pc.world import hd as HD

FACTOR = 4                  # resolution de l'alpha et de la couleur apres traitement (2 passes EPX)
PASSES_EPX = 2
SIGMA = 1.25                 # flou gaussien de l'alpha, en pixels de la texture agrandie (0,3 texel d'origine)
SIDE_MIN = 128               # plus petit cote (en texels) d'une texture traitee
PARTIAL_MAX = 0.005          # part maximale de texels d'alpha intermediaire pour une texture « binaire »
KEPT_TEXTURES = 12         # textures agrandies gardees sur la carte graphique (les plus anciennes sont rendues)


def is_sliced(arr, lookup_key=None):
    """Vrai si la texture RGBA `arr` est un decoupage a alpha binaire (feuillage, relief) a traiter. `lookup_key` : cle du groupe du decor ; ('tr', ...) = materiau transparent (melange), exclu."""
    if isinstance(lookup_key, tuple) and lookup_key and lookup_key[0] == 'tr': return False
    if arr is None or arr.ndim != 3 or arr.shape[2] != 4 or min(arr.shape[:2]) < SIDE_MIN: return False
    a = arr[..., 3]
    transp = a < 128
    if not transp.any() or transp.all(): return False
    return float(((a > 0) & (a < 255)).mean()) <= PARTIAL_MAX


def _bilinear(a, f):
    """Agrandit x f par interpolation bilineaire en boucle (REPEAT), centres de texels comme le GPU : le resultat, filtre lineairement, redonne l'image filtree de l'original (ecart < 1 niveau en moyenne)."""
    a = a.astype(np.float32)
    for ax in (0, 1):
        n = a.shape[ax]
        c = (np.arange(n * f, dtype=np.float32) + 0.5) / f - 0.5
        i0 = np.floor(c).astype(np.int64); t = (c - i0).astype(np.float32)
        t = t.reshape([-1 if k == ax else 1 for k in range(a.ndim)])
        a = np.take(a, i0 % n, axis=ax) * (1.0 - t) + np.take(a, (i0 + 1) % n, axis=ax) * t
    return a


def _fast_bilinear(rgb, f):
    """Meme resultat que `_bilinear` (uint8) par le redimensionnement bilineaire de PIL (centres de texels), 10 fois plus vite ; bord en boucle par une marge de 2 texels. None si PIL manque."""
    try: from PIL import Image
    except ImportError: return None
    h, w = rgb.shape[:2]
    p = np.pad(rgb, ((2, 2), (2, 2), (0, 0)), mode='wrap')
    r = np.asarray(Image.fromarray(np.ascontiguousarray(p)).resize(((w + 4) * f, (h + 4) * f), Image.BILINEAR))
    return np.ascontiguousarray(r[2 * f:-2 * f, 2 * f:-2 * f])


def _fill_transparent(rgb, opaque, step=3):
    """Donne aux texels transparents la couleur du texel opaque le plus proche, sur `step` anneaux (texture en boucle)."""
    rgb = rgb.copy(); done = opaque.copy()
    for _ in range(step):
        if done.all(): break
        new = rgb.copy(); nf = done.copy()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            v = np.roll(rgb, (dy, dx), (0, 1)); vf = np.roll(done, (dy, dx), (0, 1))
            take = ~nf & vf
            new[take] = v[take]; nf |= take
        rgb, done = new, nf
    return rgb


def _blur(m, sigma):
    """Flou gaussien separable en boucle."""
    if sigma <= 0: return m
    r = max(1, int(np.ceil(3 * sigma)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    for ax in (0, 1):
        m = sum(float(w) * np.roll(m, s, axis=ax) for w, s in zip(k, range(-r, r + 1)))
    return m


def _fast_blur(m, sigma):
    """Flou gaussien de PIL sur un masque uint8 (0 a 255), en boucle (marge de 4 sigma) ; None si PIL manque."""
    try: from PIL import Image, ImageFilter
    except ImportError: return None
    r = int(np.ceil(4 * sigma)); h, w = m.shape
    p = np.pad(m, r, mode='wrap')
    b = np.asarray(Image.fromarray(p).filter(ImageFilter.GaussianBlur(sigma)))
    return b[r:r + h, r:r + w]


def softened_alpha(mask, passes=PASSES_EPX, sigma=SIGMA):
    """Masque binaire (h, w) de bool -> alpha float32 (h * 2^passes, w * 2^passes) entre 0 et 1, en boucle."""
    h, w = mask.shape
    a = np.zeros((h, w, 4), np.uint8); a[..., 3] = np.where(mask, 255, 0)
    margin = 2
    a = np.pad(a, ((margin, margin), (margin, margin), (0, 0)), mode='wrap')
    for _ in range(passes): a = HD._x2(a)
    n = margin * 2 ** passes
    m = np.ascontiguousarray(a[n:-n, n:-n, 3])
    b = _fast_blur(m, sigma) if sigma > 0 else m
    if b is not None: return b.astype(np.float32) / 255.0
    return np.clip(_blur(m.astype(np.float32) / 255.0, sigma), 0.0, 1.0)


def soften(arr, passes=PASSES_EPX, sigma=SIGMA):
    """Texture RGBA uint8 (h, w, 4) a alpha binaire -> texture RGBA uint8 (h * f, w * f, 4) a contour adouci (voir l'en-tete du module)."""
    f = 2 ** passes
    rgb = _fill_transparent(arr[..., :3], arr[..., 3] >= 128)          # texels transparents : couleur du bord opaque voisin (3 anneaux)
    al = softened_alpha(arr[..., 3] >= 128, passes, sigma)
    out = np.empty((arr.shape[0] * f, arr.shape[1] * f, 4), np.uint8)
    fast = _fast_bilinear(rgb, f)
    out[..., :3] = fast if fast is not None else np.clip(_bilinear(rgb, f) + 0.5, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(al * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return out


def for_scenery(arr, lookup_key=None):
    """Texture a donner au GPU pour un groupe d'un decor de combat : adoucie si c'est un decoupage a traiter, sinon `arr` inchange."""
    return soften(arr) if is_sliced(arr, lookup_key) else arr
