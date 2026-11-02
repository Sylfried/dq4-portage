# -*- coding: utf-8 -*-
"""Ciel de l'ecran-titre en format large (fonctions pures : aucun appel OpenGL, tout se teste sans fenetre).

L'original compose le titre pour un ecran portrait (9:16). Son ciel (objet « kumo », modele 000_kumo2) est un tapis de carreaux de nuages IDENTIQUES : 4 rangees (empilees dans la hauteur, decalees d'un demi-carreau
l'une par rapport a l'autre) de 3 carreaux de 11,5 unites ; l'objet glisse de 0,0192 unite par image puis revient (periode 11,5) : la zone portrait en voit moins de un carreau et de largeur. En 16/9, 21/9 ou plus large,
le meme carreau apparaissait 3 a 6 fois de suite, tel quel (« on voit trop le fait que le pattern soit repetitif »).

Solution (une seule idee) : la zone portrait centrale (largeur = hauteur x 9/16) reste EXACTEMENT le ciel d'origine ; de chaque cote, a partir de son bord, des bandes de meme geometrie que les rangees du ciel
(memes y, z, memes couleurs de sommet) reprennent la texture avec une etirure horizontale qui varie en douceur le long de la bande (de 0,5 a 1,5 fois la taille d'origine, moyenne 1 : meme echelle d'ensemble), et un glissement vertical de la texture a l'interieur de chaque rangee (nul sur ses bords : les coutures entre rangees restent celles de l'original), avec des phases differentes a gauche et a droite : la meme forme de nuage n'apparait plus deux fois au meme endroit ni a la meme taille. L'etirure vaut 1 au bord de la zone :
raccord continu, aucune couture. Les coordonnees de texture suivent le defilement de l'objet (le raccord au bord reste exact a chaque image).
"""
import math
import numpy as np

ASPECT_PORTRAIT = 0.5625              # SceneCamera.ASPECT_DEF : ecran portrait 450 x 800
PAS_PAR_CARREAU = 16                  # colonnes de bande par carreau (11,5 unites) : l'etirure varie sur ~ 0,6 carreau, au moins 9 colonnes par ondulation
ETIRURE = ((0.34, 0.61, 0.0), (0.20, 1.37, 1.7))        # (amplitude, longueur d'onde en carreaux, phase) des deux ondulations de l'etirure horizontale (somme des amplitudes < 1 : le sens de la texture ne s'inverse jamais)
PHASE_COTE = (0.0, 2.3)                                 # phases ajoutees a gauche (0) et a droite (1) : deux cotes differents
GLISSE = ((0.09, 0.83, 0.5),)                           # idem pour le glissement vertical de la texture au milieu de chaque rangee (fraction de la hauteur du carreau) ; nul aux bords de la rangee : leur raccord est intact
SOUS_RANGEES = 4                                        # une rangee des bandes est decoupee en 4 pour suivre le glissement (nul au bord de la rangee, maximal au milieu)
RAMPE = 0.6                                             # distance (en carreaux) sur laquelle l'effet monte de 0 a 1 (lissage cubique) : raccord sans cassure au bord de la zone
import os
if os.environ.get('DQ_CIEL_PARAMS'):                                    # (test) "a1,a2,glisse,longueur_glisse" : essais de reglage
    _p = [float(x) for x in os.environ['DQ_CIEL_PARAMS'].split(',')]
    ETIRURE = ((_p[0], ETIRURE[0][1], ETIRURE[0][2]), (_p[1], ETIRURE[1][1], ETIRURE[1][2])); GLISSE = ((_p[2], _p[3], 0.5),)
MAX_COLONNES = 600                                      # garde-fou (fenetre absurdement large)


def zone_portrait(largeur, hauteur):
    """Colonne portrait 9:16 du milieu de la fenetre, en pixels : (x du bord gauche, largeur). Toute la fenetre quand elle est plus etroite (ou egale) que le portrait."""
    wz = min(float(largeur), float(hauteur) * ASPECT_PORTRAIT)
    return (largeur - wz) / 2.0, wz


def demi_zone_ndc(aspect):
    """Demi-largeur de la zone portrait en coordonnees d'ecran normalisees (-1..1) pour une fenetre de rapport largeur / hauteur `aspect`."""
    return min(1.0, ASPECT_PORTRAIT / float(aspect))


def _lisse(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _ondes(t, ondes, cote):
    return sum(a * np.sin(2.0 * math.pi * t / lg + ph + PHASE_COTE[cote]) for a, lg, ph in ondes)


def deformation(d, cote, periode=11.5):
    """Deformation de la texture a la distance `d` (unites du monde, tableau) du bord de la zone portrait, du `cote` 0 (gauche) ou 1 (droite).
    -> (G, dv) : G = abscisse de texture parcourue, en unites du monde (G(0) = 0, G'(0) = 1, G' reste entre 0,46 et 1,54 : monotone, et d'ensemble G ~ d : meme echelle). dv = glissement vertical (fraction de texture, dv(0) = 0, dv'(0) = 0) : le
    constructeur l'applique avec un profil en sin(pi t) sur la hauteur de chaque rangee, car les rangees du ciel sont empilees avec un decalage d'un demi-carreau et ne se raccordent que si leurs bords lisent la texture de v = 0 a 1."""
    d = np.asarray(d, float)
    pas = periode / 256.0
    n = int(math.ceil(float(d.max() if d.size else 0.0) / pas)) + 2
    td = np.arange(n) * pas / periode                                   # table fine (1/256 de carreau), integree au trapeze : G exacte a la precision de la table, deterministe
    s = 1.0 + _lisse(td / RAMPE) * _ondes(td, ETIRURE, cote)
    G = np.concatenate([[0.0], np.cumsum((s[1:] + s[:-1]) * 0.5 * pas)])
    dv = _lisse(d / periode / RAMPE) * _ondes(d / periode, GLISSE, cote)
    return np.interp(d, np.arange(n) * pas, G), dv


class Rangee:
    """Une rangee de carreaux du ciel : bord bas / haut (y, z, v, couleur), carreaux (xg, xd, ug, ud) et periode."""
    def __init__(self, bas, haut, quads):
        self.bas, self.haut = bas, haut
        self.quads = quads                                              # (n, 4) : abscisse gauche / droite, u gauche / droite, tries par abscisse
        x0, x1 = float(quads[0, 0]), float(quads[-1, 1])
        self.x0 = x0
        self.periode = (x1 - x0) / (len(quads) / 2.0)                   # 2 demi-carreaux = 1 carreau de texture
        k = max(1, len(quads) // int(round((x1 - x0) / self.periode)))
        un = quads[:k]
        self.carreau = un
        self.taux = float((un[:, 3] - un[:, 2]).sum() / (un[:, 1] - un[:, 0]).sum())      # u par unite du monde

    def u(self, x):
        """u de la texture du ciel d'origine a l'abscisse `x` (tableau, hors defilement), exactement celui des quadrilateres (y compris au-dela des 3 carreaux : le motif se repete)."""
        x = np.asarray(x, float)
        xr = self.x0 + np.mod(x - self.x0, self.periode)
        i = np.clip(np.searchsorted(self.carreau[:, 0], xr, side='right') - 1, 0, len(self.carreau) - 1)
        xg, xd, ug, ud = self.carreau[i].T
        return ug + (xr - xg) / np.maximum(xd - xg, 1e-9) * (ud - ug)


def analyser(pos, uv, col):
    """Rangees du ciel a partir des sommets de l'objet (N sommets, N multiple de 6 : triangles de quadrilateres alignes sur x et y). ValueError si la structure n'est pas celle attendue."""
    pos = np.asarray(pos, float); uv = np.asarray(uv, float); col = np.asarray(col, float)
    if len(pos) == 0 or len(pos) % 6: raise ValueError('ciel : %d sommets' % len(pos))
    P, U, C = pos.reshape(-1, 6, 3), uv.reshape(-1, 6, 2), col.reshape(-1, 6, 4)
    rang = {}
    for p, u, c in zip(P, U, C):
        xg, xd = float(p[:, 0].min()), float(p[:, 0].max()); yb, yh = float(p[:, 1].min()), float(p[:, 1].max())
        if xd - xg < 1e-6 or yh - yb < 1e-6: raise ValueError('ciel : quadrilatere degenere')
        g, d, b, h = (np.abs(p[:, 0] - xg) < 1e-4), (np.abs(p[:, 0] - xd) < 1e-4), (np.abs(p[:, 1] - yb) < 1e-4), (np.abs(p[:, 1] - yh) < 1e-4)
        if not (np.all(g | d) and np.all(b | h)): raise ValueError('ciel : quadrilatere non aligne')
        coin = lambda m: (float(p[m, 1].mean()), float(p[m, 2].mean()), float(u[m, 1].mean()), c[m].mean(0))
        bas, haut = coin(b), coin(h)
        rang.setdefault((round(yb, 2), round(yh, 2)), {'bas': bas, 'haut': haut, 'q': []})['q'].append((xg, xd, float(u[g, 0].mean()), float(u[d, 0].mean())))
    out = []
    for k in sorted(rang):
        r = rang[k]; q = np.array(sorted(r['q']), float)
        if len(q) < 2 or len(q) % 2 or np.abs(q[1:, 0] - q[:-1, 1]).max() > 1e-3: raise ValueError('ciel : rangee non contigue')
        ra = Rangee(r['bas'], r['haut'], q)
        if len(q) > 2 and np.abs(q[2:, 2:] - q[:-2, 2:]).max() > 0.01: raise ValueError('ciel : rangee non periodique')
        out.append(ra)
    return out


def bords_zone(M, rangees, demi, x_sonde, ech=33):
    """Abscisses du monde ou la zone portrait (|x d'ecran| <= demi) et la fenetre entiere (|x d'ecran| <= 1) coupent le ciel, sur la partie VISIBLE des rangees (|y d'ecran| <= 1,02).
    -> (zone_bas, zone_haut, ecran_bas, ecran_haut) : bornes exterieures de la zone (aucun point de la zone en dehors de [zone_bas, zone_haut]) et de la fenetre ; None si rien n'est visible."""
    M = np.asarray(M, float); t = np.linspace(0.0, 1.0, ech)
    zb, zh, eb, eh = [], [], [], []
    for r in rangees:
        y = r.bas[0] + t * (r.haut[0] - r.bas[0]); z = r.bas[1] + t * (r.haut[1] - r.bas[1])
        cl = np.stack([np.full_like(y, x_sonde), y, z, np.ones_like(y)])
        h = M @ cl
        with np.errstate(divide='ignore', invalid='ignore'):
            ok = (h[3] > 1e-6) & (np.abs(h[1] / h[3]) <= 1.02)
        if not ok.any(): continue
        y, z = y[ok], z[ok]
        for q, bas, haut in ((demi, zb, zh), (1.0, eb, eh)):
            sol = []
            for sg in (-1.0, 1.0):
                a = M[0, 0] - sg * q * M[3, 0]
                b = sg * q * (M[3, 1] * y + M[3, 2] * z + M[3, 3]) - (M[0, 1] * y + M[0, 2] * z + M[0, 3])
                if abs(a) < 1e-9: return None
                sol.append(b / a)
            bas.append(np.minimum(sol[0], sol[1]).min()); haut.append(np.maximum(sol[0], sol[1]).max())
    if not zb: return None
    return min(zb), max(zh), min(eb), max(eh)


class CielLarge:
    """Bandes de ciel de part et d'autre de la zone portrait. `pos` / `uv` / `col` : sommets de l'objet « kumo » a sa position d'origine (avant defilement)."""
    def __init__(self, pos, uv, col):
        self.rangees = analyser(pos, uv, col)
        self.periode = self.rangees[0].periode
        self.pas = self.periode / PAS_PAR_CARREAU
        self.x_mil = float(np.mean([(r.quads[0, 0] + r.quads[-1, 1]) / 2 for r in self.rangees]))
        self._cle = None; self._tout = None; self._ref = []

    def _construire(self, M, aspect):
        """Geometrie des bandes (positions, couleurs, etirure : tout sauf le raccord de u au bord, qui suit le defilement)."""
        self._tout = None; self._ref = []
        demi = demi_zone_ndc(aspect)
        if demi >= 1.0 - 1e-6: return                                   # fenetre aussi etroite que le portrait : rien a ajouter
        b = bords_zone(M, self.rangees, demi, self.x_mil)
        if b is None: return
        zb, zh, eb, eh = b
        P, U, C = [], [], []
        for cote, (xs, sens, ext) in enumerate(((zb, -1.0, zb - eb), (zh, 1.0, eh - zh))):
            if ext <= 0.0: continue
            K = int(min(MAX_COLONNES, math.ceil(ext / self.pas) + 2))
            d = np.arange(K + 1) * self.pas
            G, dv = deformation(d, cote, self.periode)
            X = xs + sens * d
            t = np.linspace(0.0, 1.0, SOUS_RANGEES + 1)                       # sous-rangees, du bord bas (0) au bord haut (1)
            for ri, r in enumerate(self.rangees):
                lerp = lambda a, b: np.asarray(a, float)[None] + t[:, None] * (np.asarray(b, float) - np.asarray(a, float))[None]
                yz = lerp(r.bas[:2], r.haut[:2]); cc = lerp(r.bas[3], r.haut[3])                   # (S + 1, 2), (S + 1, 4) : couleur de sommet lineaire, comme le ciel d'origine
                v = r.bas[2] + t * (r.haut[2] - r.bas[2])
                pos = np.zeros((K + 1, len(t), 3)); pos[:, :, 0] = X[:, None]; pos[:, :, 1:] = yz[None]
                uv = np.zeros((K + 1, len(t), 2)); uv[:, :, 0] = (sens * r.taux * G)[:, None]               # u relatif au point de depart (raccord ajoute a chaque image)
                uv[:, :, 1] = v[None] + dv[:, None] * np.sin(math.pi * t)[None]
                col = np.zeros((K + 1, len(t), 4)); col[:] = cc[None]
                if sens < 0: pos, uv, col = pos[::-1], uv[::-1], col[::-1]            # abscisses croissantes : meme sens de parcours (donc de face) que les quadrilateres d'origine
                p = self._tri(pos)
                self._ref.append((sum(len(a) for a in P), sum(len(a) for a in P) + len(p), ri, xs))
                P.append(p); U.append(self._tri(uv)); C.append(self._tri(col))
        if P: self._tout = (np.concatenate(P), np.concatenate(U), np.concatenate(C))

    def bandes(self, M, aspect, phi):
        """-> (positions (N, 3), coordonnees de texture (N, 2), couleurs (N, 4)) en float32 : triangles des bandes de part et d'autre de la zone ; None s'il n'y a rien a ajouter.
        `phi` = deplacement en x de l'objet depuis sa position d'origine (defilement) : le u des bandes est celui du ciel d'origine au bord de la zone."""
        cle = (np.asarray(M, float).tobytes(), float(aspect))
        if cle != self._cle: self._construire(M, aspect); self._cle = cle
        if self._tout is None: return None
        P, U, C = self._tout
        U = U.copy()
        for deb, fin, ri, xs in self._ref: U[deb:fin, 0] += self.rangees[ri].u(xs - phi)
        return P.astype(np.float32), U.astype(np.float32), C.astype(np.float32)

    @staticmethod
    def _tri(a):
        """(n, S + 1, k) : colonnes x sous-rangees -> triangles (bas g, haut g, haut d, bas g, haut d, bas d) de chaque quadrilatere (meme ordre que le ciel d'origine)."""
        g, d = a[:-1], a[1:]
        bg, hg, hd, bd = g[:, :-1], g[:, 1:], d[:, 1:], d[:, :-1]
        return np.stack([bg, hg, hd, bg, hd, bd], axis=2).reshape(-1, a.shape[2])
