# -*- coding: utf-8 -*-
"""Bulles d'icone cliquables (#131) : fonctions pures (aucun appel OpenGL ; tout se teste sans fenetre).

Une bulle (paquets 19 / 20, « Riseup ») est un carre de 0,96 unite face a la camera, au-dessus d'un personnage, d'un coffre, d'un tonneau... Cliquer dessus donne la touche d'action (A, l'espace), comme sur mobile ou
la bulle est la zone a toucher. On projette les 4 coins du carre avec la matrice de la derniere image dessinee et on regarde si le pointeur est dedans."""
import numpy as np


def projeter(M, coins, largeur, hauteur):
    """Coins du monde (n, 3) -> liste de n points (x, y) en pixels de la fenetre (origine en bas a gauche, comme les evenements de souris), ou None si un coin est derriere la camera (w <= 0)."""
    M = np.asarray(M, float); P = np.asarray(coins, float)
    h = (M @ np.concatenate([P, np.ones((len(P), 1))], axis=1).T).T
    if np.any(h[:, 3] <= 1e-9): return None
    ndc = h[:, :2] / h[:, 3:4]
    return [((float(a) * 0.5 + 0.5) * largeur, (float(b) * 0.5 + 0.5) * hauteur) for a, b in ndc]


def dans_quadrilatere(p, pts):
    """Le point `p` est-il dans le polygone convexe `pts` (sommets dans l'ordre, sens quelconque, bords compris) ?"""
    px, py = p; signe = 0
    for i in range(len(pts)):
        x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % len(pts)]
        c = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
        if abs(c) < 1e-9: continue
        s = 1 if c > 0 else -1
        if signe == 0: signe = s
        elif s != signe: return False
    return True
