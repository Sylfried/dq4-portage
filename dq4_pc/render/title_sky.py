# -*- coding: utf-8 -*-
"""Ciel de l'ecran-titre en format large (fonctions pures : aucun appel OpenGL, tout se teste sans fenetre).

L'original compose le titre pour un ecran portrait (9:16). Son ciel (objet « kumo », modele 000_kumo2) est un tapis de carreaux de nuages IDENTIQUES : 4 rangees (empilees dans la hauteur, decalees d'un demi-carreau
l'une par rapport a l'autre) de 3 carreaux de 11,5 unites ; l'objet glisse de 0,0192 unite par image puis revient (periode 11,5) : la zone portrait en voit moins de un carreau et de largeur. En 16/9, 21/9 ou plus large,
le meme carreau apparaissait 3 a 6 fois de suite, tel quel (« on voit trop le fait que le pattern soit repetitif »).

RENDU PAR DEFAUT (#174, 04/11/2026 11 h 30) : « ajuste la hauteur pour automatiquement s'adapter a la hauteur de la fenetre, et ca sera sur la largeur que la repetition se fera, et applique bien comme convenu les effets
visuels » : le ciel est dessine a plat, a l'echelle de l'ecran (`screen_sky`) : la texture (carree, 256 x 256) a pour HAUTEUR celle de la fenetre, a toute taille de fenetre, sans agrandissement supplementaire ; elle se repete sur la
LARGEUR (1,78 fois en 16/9) ; l'effet de vague de l'ancien rendu en bandes (etirure horizontale ondulee 0,52 a 1,48 fois et glissement vertical, `STRETCH` / `SLIDE`) est applique a toute la largeur, fixe a l'ecran pendant que
la texture defile dessous (les nuages se deforment en passant) : les copies d'une meme tuile ne se ressemblent donc pas ; le degrade de teinte des rangees d'origine (orange en haut et en bas, blanc au milieu) est repris tel
qu'il apparaissait a l'ecran (`screen_gradient`) ; le defilement garde la vitesse d'origine (une tuile pour 11,5 unites de glissement de l'objet, soit 599 images du moteur). Les rendus precedents restent disponibles : `DQ_CIEL_AGRANDI=1`
(essai #130 ci-dessous), `DQ_CIEL_BANDES=1` (bandes), `DQ_CIEL_COPIES=1` (copies).

ESSAI #130 (agrandi, `DQ_CIEL_AGRANDI=1`) : l'image du ciel est AGRANDIE autour du centre de l'ecran (`screen_zoom` : x 3,16 en 16/9) de facon que la fenetre entiere ne montre que ce que montrait la zone portrait du jeu d'origine : un seul
carreau, jamais repete ; plus de bandes. L'ancienne solution (bandes etirees, ci-dessous) reste disponible avec DQ_CIEL_BANDES=1 pour comparer.

Solution precedente (bandes) : la zone portrait centrale (largeur = hauteur x 9/16) reste EXACTEMENT le ciel d'origine ; de chaque cote, a partir de son bord, des bandes de meme geometrie que les rangees du ciel
(memes y, z, memes couleurs de sommet) reprennent la texture avec une etirure horizontale qui varie en douceur le long de la bande (de 0,52 a 1,48 fois la taille d'origine, moyenne 1 : meme echelle d'ensemble), et un glissement vertical de la texture a l'interieur de chaque rangee (nul sur ses bords : les coutures entre rangees restent celles de l'original), avec des phases differentes a gauche et a droite : la meme forme de nuage n'apparait plus deux fois au meme endroit ni a la meme taille. L'etirure vaut 1 au bord de la zone :
raccord continu, aucune couture. Les coordonnees de texture suivent le defilement de l'objet (le raccord au bord reste exact a chaque image).
"""
import math
import numpy as np

ASPECT_PORTRAIT = 0.5625              # SceneCamera.ASPECT_DEF : ecran portrait 450 x 800
STEP_PER_TILE = 16                  # colonnes de bande par carreau (11,5 unites) : l'etirure varie sur ~ 0,6 carreau, au moins 9 colonnes par ondulation
STRETCH = ((0.30, 0.61, 0.0), (0.18, 1.37, 1.7))        # (amplitude, longueur d'onde en carreaux, phase) des deux ondulations de l'etirure horizontale (somme des amplitudes < 1 : le sens de la texture ne s'inverse jamais)
SIDE_PHASE = (0.0, 2.3)                                 # phases ajoutees a gauche (0) et a droite (1) : deux cotes differents
SLIDE = ((0.03, 1.9, 0.5),)                           # idem pour le glissement vertical de la texture au milieu de chaque rangee (fraction de la hauteur du carreau) ; nul aux bords de la rangee : leur raccord est intact
SUB_ROWS = 4                                        # une rangee des bandes est decoupee en 4 pour suivre le glissement (nul au bord de la rangee, maximal au milieu)
RAMP = 0.6                                             # distance (en carreaux) sur laquelle l'effet monte de 0 a 1 (lissage cubique) : raccord sans cassure au bord de la zone
import os
if os.environ.get('DQ_CIEL_PARAMS'):                                    # (test) "a1,a2,glisse,longueur_glisse" : essais de reglage
    _p = [float(x) for x in os.environ['DQ_CIEL_PARAMS'].split(',')]
    STRETCH = ((_p[0], STRETCH[0][1], STRETCH[0][2]), (_p[1], STRETCH[1][1], STRETCH[1][2])); SLIDE = ((_p[2], _p[3], 0.5),)
MAX_COLUMNS = 600                                      # garde-fou (fenetre absurdement large)


TILE_WIDTH = 1.0                    # rendu a plat (#174) : largeur d'une tuile a l'ecran, en hauteurs de fenetre (texture carree : 1)
TILE_COLUMNS = 24                    # colonnes de maillage par tuile (la plus courte onde de l'etirure : 0,61 tuile, soit 14 colonnes)
SCREEN_LINES = 9                       # lignes de maillage dans la hauteur (profil du glissement vertical et degrade de teinte ; les coupures du degrade s'y ajoutent)
if os.environ.get('DQ_CIEL_TUILE'):                                     # (test) largeur de la tuile en hauteurs de fenetre
    try: TILE_WIDTH = max(0.2, float(os.environ['DQ_CIEL_TUILE']))
    except ValueError: pass


def stretch_plate(d):
    """Rendu a plat : abscisse de texture (en tuiles) a la distance `d` (en tuiles, tableau) du bord gauche de la fenetre. Integrale exacte de 1 + somme des ondes de `STRETCH` : G(0) = 0, pente entre 0,52 et 1,48 (jamais de retournement),
    echelle d'ensemble 1 (la somme des ondes est de moyenne nulle). Meme effet de vague que les bandes, mais periodique et sans rampe : il s'applique a toute la largeur."""
    d = np.asarray(d, float); G = d.copy()
    for a, lg, ph in STRETCH:
        w = 2.0 * math.pi / lg
        G = G + a / w * (math.cos(ph) - np.cos(w * d + ph))
    return G


def flat_sliding(d):
    """Rendu a plat : glissement vertical de la texture (fraction de sa hauteur, avant le profil sin(pi t) qui l'annule en haut et en bas de la fenetre) a la distance `d` (tuiles) du bord gauche."""
    d = np.asarray(d, float); g = np.zeros_like(d)
    for a, lg, ph in SLIDE: g = g + a * np.sin(2.0 * math.pi * d / lg + ph)
    return g


def screen_gradient(M, rows, x_probe):
    """Degrade de teinte du ciel d'origine tel qu'il apparait a l'ecran : -> (y, couleurs) : `y` = ordonnees d'ecran normalisees croissantes (-1 bas, +1 haut), `colors` (n, 4) = couleur de sommet correspondante, a partir de la
    projection (matrice `M`) des bords et de quelques points intermediaires de chaque rangee d'origine (la couleur est lineaire dans le monde, pas a l'ecran). Les points hors de l'objectif (derriere la camera) sont ignores."""
    M = np.asarray(M, float); ys, cs = [], []
    for r in rows:
        t = np.linspace(0.0, 1.0, 9)
        y = r.bottom[0] + t * (r.topmost[0] - r.bottom[0]); z = r.bottom[1] + t * (r.topmost[1] - r.bottom[1])
        h = M @ np.stack([np.full_like(y, x_probe), y, z, np.ones_like(y)])
        ok = h[3] > 1e-6
        if not ok.any(): continue
        ys.append((h[1][ok] / h[3][ok])); cs.append(np.asarray(r.bottom[3], float)[None] + t[ok, None] * (np.asarray(r.topmost[3], float) - np.asarray(r.bottom[3], float))[None])
    if not ys: return np.array([-1.0, 1.0]), np.ones((2, 4))
    y = np.concatenate(ys); c = np.concatenate(cs); o = np.argsort(y, kind='stable')
    y, c = y[o], c[o]
    guard = np.concatenate([[True], np.diff(y) > 1e-9]); return y[guard], c[guard]


def screen_sky(aspect, phi_tiles, gradient=None, tile=None, lines=None):
    """Ciel a plat, a l'echelle de l'ecran (#174) : triangles (positions, coordonnees de texture, couleurs) en coordonnees normalisees (x et y de -1 a 1, profondeur au fond), pour une fenetre de rapport
    largeur / hauteur `aspect`. La texture a pour hauteur celle de la fenetre (v de 0,998 en bas a 0,002 en haut, comme les rangees d'origine) et pour largeur `tile` hauteurs de fenetre (`TILE_WIDTH`) ; elle se repete sur la
    largeur (u en tuiles, texture en REPEAT). `phi_tiles` = defilement de l'objet en tuiles (le contenu glisse vers +x quand il augmente, comme l'objet d'origine). `gradient` = (y, couleurs) de `screen_gradient` (blanc si None).
    L'etirure (`stretch_plate`) et le glissement (`flat_sliding`) sont fixes a l'ecran : la texture defile dessous."""
    tile = TILE_WIDTH if tile is None else float(tile); aspect = float(aspect)
    tile_ndc = 2.0 * tile / aspect; dx = tile_ndc / TILE_COLUMNS
    K = int(math.ceil(2.0 / dx)) + 1
    i = np.arange(K + 1); X = -1.0 + i * dx; d = i / float(TILE_COLUMNS)                 # d : tuiles depuis le bord gauche
    t = np.linspace(0.0, 1.0, (SCREEN_LINES if lines is None else int(lines)) + 1)
    if gradient is not None:                                                                  # les coupures du degrade (bords des rangees d'origine) deviennent des lignes du maillage
        yc = (np.asarray(gradient[0], float) + 1.0) / 2.0
        t = np.unique(np.round(np.concatenate([t, yc[(yc > 0.0) & (yc < 1.0)]]), 6))
    if gradient is None: col = np.ones((len(t), 4))
    else: col = np.stack([np.interp(2.0 * t - 1.0, gradient[0], gradient[1][:, k]) for k in range(4)], axis=1)
    U = stretch_plate(d) - float(phi_tiles)
    dv = flat_sliding(d)
    uu = np.repeat(U[:, None], len(t), axis=1)
    vv = 0.998 - 0.996 * t[None] + dv[:, None] * np.sin(math.pi * t)[None]
    pos = np.zeros((K + 1, len(t), 3)); pos[:, :, 0] = X[:, None]; pos[:, :, 1] = (2.0 * t - 1.0)[None]; pos[:, :, 2] = BACKGROUND_Z
    uv = np.stack([uu, vv], axis=2); cc = np.repeat(col[None], K + 1, axis=0)
    tri_indices = lambda a: WideSky._triangles(a)
    return tri_indices(pos).astype(np.float32), tri_indices(uv).astype(np.float32), tri_indices(cc).astype(np.float32)


BACKGROUND_Z = 0.9999                          # profondeur (normalisee) du ciel a plat : au fond, devant le plan eloigne (le test de profondeur GL_LESS le laisse passer), derriere tout le reste


def zone_portrait(width_px, height_px):
    """Colonne portrait 9:16 du milieu de la fenetre, en pixels : (x du bord gauche, largeur). Toute la fenetre quand elle est plus etroite (ou egale) que le portrait."""
    wz = min(float(width_px), float(height_px) * ASPECT_PORTRAIT)
    return (width_px - wz) / 2.0, wz


def half_zone_ndc(aspect):
    """Demi-largeur de la zone portrait en coordonnees d'ecran normalisees (-1..1) pour une fenetre de rapport largeur / hauteur `aspect`."""
    return min(1.0, ASPECT_PORTRAIT / float(aspect))


def screen_zoom(aspect):
    """Zoom (essai #130) du ciel de l'ecran-titre, centre sur l'ecran : 1 pour une fenetre aussi etroite que le portrait (ou plus), sinon `aspect / ASPECT_PORTRAIT` (16/9 : x 3,16 ; 21/9 : x 4,15) : la fenetre entiere
    montre alors ce que montrait la seule zone portrait du jeu d'origine (moins d'un carreau de nuages de large), donc le meme carreau n'y est jamais repete. `DQ_CIEL_ZOOM` (test) force une valeur."""
    try:
        if os.environ.get('DQ_CIEL_ZOOM'): return max(1.0, float(os.environ['DQ_CIEL_ZOOM']))
    except ValueError: pass
    return max(1.0, float(aspect) / ASPECT_PORTRAIT)


def zoom_matrix(M, z):
    """Matrice de projection `M` (4 x 4, colonnes d'espace de coordonnees homogenes) suivie d'un agrandissement `z` de l'image autour du centre de l'ecran (x et y d'ecran multiplies par z ; la profondeur ne change pas)."""
    S = np.diag([float(z), float(z), 1.0, 1.0])
    return S @ np.asarray(M, float)


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _waves(t, waves, side):
    return sum(a * np.sin(2.0 * math.pi * t / lg + ph + SIDE_PHASE[side]) for a, lg, ph in waves)


def deformation(d, side, period=11.5):
    """Deformation de la texture a la distance `d` (unites du monde, tableau) du bord de la zone portrait, du `side` 0 (gauche) ou 1 (droite).
    -> (G, dv) : G = abscisse de texture parcourue, en unites du monde (G(0) = 0, G'(0) = 1, G' reste entre 0,52 et 1,48 : monotone, et d'ensemble G ~ d : meme echelle). dv = glissement vertical (fraction de texture, dv(0) = 0, dv'(0) = 0) : le
    constructeur l'applique avec un profil en sin(pi t) sur la hauteur de chaque rangee, car les rangees du ciel sont empilees avec un decalage d'un demi-carreau et ne se raccordent que si leurs bords lisent la texture de v = 0 a 1."""
    d = np.asarray(d, float)
    step = period / 256.0
    n = int(math.ceil(float(d.max() if d.size else 0.0) / step)) + 2
    td = np.arange(n) * step / period                                   # table fine (1/256 de carreau), integree au trapeze : G exacte a la precision de la table, deterministe
    s = 1.0 + _smooth(td / RAMP) * _waves(td, STRETCH, side)
    G = np.concatenate([[0.0], np.cumsum((s[1:] + s[:-1]) * 0.5 * step)])
    dv = _smooth(d / period / RAMP) * _waves(d / period, SLIDE, side)
    return np.interp(d, np.arange(n) * step, G), dv


class Row:
    """Une rangee de carreaux du ciel : bord bas / haut (y, z, v, couleur), carreaux (xg, xd, ug, ud) et periode."""
    def __init__(self, bottom, topmost, quads):
        self.bottom, self.topmost = bottom, topmost
        self.quads = quads                                              # (n, 4) : abscisse gauche / droite, u gauche / droite, tries par abscisse
        x0, x1 = float(quads[0, 0]), float(quads[-1, 1])
        self.x0 = x0
        self.period = (x1 - x0) / (len(quads) / 2.0)                   # 2 demi-carreaux = 1 carreau de texture
        k = max(1, len(quads) // int(round((x1 - x0) / self.period)))
        one = quads[:k]
        self.quad_tile = one
        self.rate = float((one[:, 3] - one[:, 2]).sum() / (one[:, 1] - one[:, 0]).sum())      # u par unite du monde

    def u(self, x):
        """u de la texture du ciel d'origine a l'abscisse `x` (tableau, hors defilement), exactement celui des quadrilateres (y compris au-dela des 3 carreaux : le motif se repete)."""
        x = np.asarray(x, float)
        xr = self.x0 + np.mod(x - self.x0, self.period)
        i = np.clip(np.searchsorted(self.quad_tile[:, 0], xr, side='right') - 1, 0, len(self.quad_tile) - 1)
        xg, xd, ug, ud = self.quad_tile[i].T
        return ug + (xr - xg) / np.maximum(xd - xg, 1e-9) * (ud - ug)


def analyze(pos, uv, col):
    """Rangees du ciel a partir des sommets de l'objet (N sommets, N multiple de 6 : triangles de quadrilateres alignes sur x et y). ValueError si la structure n'est pas celle attendue."""
    pos = np.asarray(pos, float); uv = np.asarray(uv, float); col = np.asarray(col, float)
    if len(pos) == 0 or len(pos) % 6: raise ValueError('sky: %d vertices' % len(pos))
    P, U, C = pos.reshape(-1, 6, 3), uv.reshape(-1, 6, 2), col.reshape(-1, 6, 4)
    rank = {}
    for p, u, c in zip(P, U, C):
        xg, xd = float(p[:, 0].min()), float(p[:, 0].max()); yb, yh = float(p[:, 1].min()), float(p[:, 1].max())
        if xd - xg < 1e-6 or yh - yb < 1e-6: raise ValueError('sky: degenerate quad')
        g, d, b, h = (np.abs(p[:, 0] - xg) < 1e-4), (np.abs(p[:, 0] - xd) < 1e-4), (np.abs(p[:, 1] - yb) < 1e-4), (np.abs(p[:, 1] - yh) < 1e-4)
        if not (np.all(g | d) and np.all(b | h)): raise ValueError('sky: quad not aligned')
        corner = lambda m: (float(p[m, 1].mean()), float(p[m, 2].mean()), float(u[m, 1].mean()), c[m].mean(0))
        bottom, topmost = corner(b), corner(h)
        rank.setdefault((round(yb, 2), round(yh, 2)), {'bas': bottom, 'haut': topmost, 'q': []})['q'].append((xg, xd, float(u[g, 0].mean()), float(u[d, 0].mean())))
    out = []
    for k in sorted(rank):
        r = rank[k]; q = np.array(sorted(r['q']), float)
        if len(q) < 2 or len(q) % 2 or np.abs(q[1:, 0] - q[:-1, 1]).max() > 1e-3: raise ValueError('sky: row not contiguous')
        ra = Row(r['bas'], r['haut'], q)
        if len(q) > 2 and np.abs(q[2:, 2:] - q[:-2, 2:]).max() > 0.01: raise ValueError('sky: row not periodic')
        out.append(ra)
    return out


def zone_edges(M, rows, half, x_probe, ui_scale=33):
    """Abscisses du monde ou la zone portrait (|x d'ecran| <= demi) et la fenetre entiere (|x d'ecran| <= 1) coupent le ciel, sur la partie VISIBLE des rangees (|y d'ecran| <= 1,02).
    -> (zone_bas, zone_haut, ecran_bas, ecran_haut) : bornes exterieures de la zone (aucun point de la zone en dehors de [zone_bas, zone_haut]) et de la fenetre ; None si rien n'est visible."""
    M = np.asarray(M, float); t = np.linspace(0.0, 1.0, ui_scale)
    zb, zh, eb, eh = [], [], [], []
    for r in rows:
        y = r.bottom[0] + t * (r.topmost[0] - r.bottom[0]); z = r.bottom[1] + t * (r.topmost[1] - r.bottom[1])
        cl = np.stack([np.full_like(y, x_probe), y, z, np.ones_like(y)])
        h = M @ cl
        with np.errstate(divide='ignore', invalid='ignore'):
            ok = (h[3] > 1e-6) & (np.abs(h[1] / h[3]) <= 1.02)
        if not ok.any(): continue
        y, z = y[ok], z[ok]
        for q, bottom, topmost in ((half, zb, zh), (1.0, eb, eh)):
            ground = []
            for sg in (-1.0, 1.0):
                a = M[0, 0] - sg * q * M[3, 0]
                b = sg * q * (M[3, 1] * y + M[3, 2] * z + M[3, 3]) - (M[0, 1] * y + M[0, 2] * z + M[0, 3])
                if abs(a) < 1e-9: return None
                ground.append(b / a)
            bottom.append(np.minimum(ground[0], ground[1]).min()); topmost.append(np.maximum(ground[0], ground[1]).max())
    if not zb: return None
    return min(zb), max(zh), min(eb), max(eh)


class WideSky:
    """Bandes de ciel de part et d'autre de la zone portrait. `pos` / `uv` / `col` : sommets de l'objet « kumo » a sa position d'origine (avant defilement)."""
    def __init__(self, pos, uv, col):
        self.rows = analyze(pos, uv, col)
        self.period = self.rows[0].period
        self.step = self.period / STEP_PER_TILE
        self.x_mil = float(np.mean([(r.quads[0, 0] + r.quads[-1, 1]) / 2 for r in self.rows]))
        self._key = None; self._all = None; self._ref = []

    def _build(self, M, aspect):
        """Geometrie des bandes (positions, couleurs, etirure : tout sauf le raccord de u au bord, qui suit le defilement)."""
        self._all = None; self._ref = []
        half = half_zone_ndc(aspect)
        if half >= 1.0 - 1e-6: return                                   # fenetre aussi etroite que le portrait : rien a ajouter
        b = zone_edges(M, self.rows, half, self.x_mil)
        if b is None: return
        zb, zh, eb, eh = b
        P, U, C = [], [], []
        for side, (xs, direction, ext) in enumerate(((zb, -1.0, zb - eb), (zh, 1.0, eh - zh))):
            if ext <= 0.0: continue
            K = int(min(MAX_COLUMNS, math.ceil(ext / self.step) + 2))
            d = np.arange(K + 1) * self.step
            G, dv = deformation(d, side, self.period)
            X = xs + direction * d
            t = np.linspace(0.0, 1.0, SUB_ROWS + 1)                       # sous-rangees, du bord bas (0) au bord haut (1)
            for ri, r in enumerate(self.rows):
                lerp = lambda a, b: np.asarray(a, float)[None] + t[:, None] * (np.asarray(b, float) - np.asarray(a, float))[None]
                yz = lerp(r.bottom[:2], r.topmost[:2]); cc = lerp(r.bottom[3], r.topmost[3])                   # (S + 1, 2), (S + 1, 4) : couleur de sommet lineaire, comme le ciel d'origine
                v = r.bottom[2] + t * (r.topmost[2] - r.bottom[2])
                pos = np.zeros((K + 1, len(t), 3)); pos[:, :, 0] = X[:, None]; pos[:, :, 1:] = yz[None]
                uv = np.zeros((K + 1, len(t), 2)); uv[:, :, 0] = (direction * r.rate * G)[:, None]               # u relatif au point de depart (raccord ajoute a chaque image)
                uv[:, :, 1] = v[None] + dv[:, None] * np.sin(math.pi * t)[None]
                col = np.zeros((K + 1, len(t), 4)); col[:] = cc[None]
                if direction < 0: pos, uv, col = pos[::-1], uv[::-1], col[::-1]            # abscisses croissantes : meme sens de parcours (donc de face) que les quadrilateres d'origine
                p = self._triangles(pos)
                self._ref.append((sum(len(a) for a in P), sum(len(a) for a in P) + len(p), ri, xs))
                P.append(p); U.append(self._triangles(uv)); C.append(self._triangles(col))
        if P: self._all = (np.concatenate(P), np.concatenate(U), np.concatenate(C))

    def bands(self, M, aspect, phi):
        """-> (positions (N, 3), coordonnees de texture (N, 2), couleurs (N, 4)) en float32 : triangles des bandes de part et d'autre de la zone ; None s'il n'y a rien a ajouter.
        `phi` = deplacement en x de l'objet depuis sa position d'origine (defilement) : le u des bandes est celui du ciel d'origine au bord de la zone."""
        lookup_key = (np.asarray(M, float).tobytes(), float(aspect))
        if lookup_key != self._key: self._build(M, aspect); self._key = lookup_key
        if self._all is None: return None
        P, U, C = self._all
        U = U.copy()
        for start_idx, end, ri, xs in self._ref: U[start_idx:end, 0] += self.rows[ri].u(xs - phi)
        return P.astype(np.float32), U.astype(np.float32), C.astype(np.float32)

    @staticmethod
    def _triangles(a):
        """(n, S + 1, k) : colonnes x sous-rangees -> triangles (bas g, haut g, haut d, bas g, haut d, bas d) de chaque quadrilatere (meme ordre que le ciel d'origine)."""
        g, d = a[:-1], a[1:]
        bg, hg, hd, bd = g[:, :-1], g[:, 1:], d[:, 1:], d[:, :-1]
        return np.stack([bg, hg, hd, bg, hd, bd], axis=2).reshape(-1, a.shape[2])


def cloned_positions(cur, dx):
    """Positions des sommets d'une copie d'un plan de ciel (`ext_map`) : `dx` nombre = copie DECALEE de dx sur x (ciel du titre) ; `('miroir', xe)` = copie SYMETRIQUE par rapport au plan x = xe (x -> 2 xe - x : les points du bord xe ne bougent pas,
    l'image se prolonge sans couture ; plans de ciel de dpout et ev09, MAP-05). Tableau de sommets (n, 3), float32 ; `cur` n'est pas modifie."""
    p = np.array(cur, np.float32)
    if isinstance(dx, tuple) and dx and dx[0] == 'miroir': p[:, 0] = np.float32(2.0 * dx[1]) - p[:, 0]
    else: p[:, 0] += np.float32(dx)
    return p
