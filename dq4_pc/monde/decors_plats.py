"""Decors a plat superposes a la meme hauteur (massifs de fleurs sur une autre bordure, chemin sur pelouse...) : correctif du scintillement par z-fighting.

Deux triangles horizontaux a la meme hauteur ont la meme profondeur a l'arrondi pres : le test de profondeur donne l'un ou l'autre pixel par pixel, et le resultat change a chaque
mouvement de la camera (les fleurs « scintillent »). Au chargement d'une carte on releve tres legerement (3 millimetres d'unite de ville, soit moins d'un dixieme de pixel) chaque triangle
plat qui en recouvre un autre deja dessine a sa hauteur, d'autant que de triangles empiles ; le dernier dessine l'emporte, toujours. Les groupes de textures sont copies : le cache de carte reste intact.
"""
import numpy as np

PAS = 0.003            # hauteur ajoutee par triangle empile (unites de ville)
TOL_Y = 0.0015         # deux triangles plats dont la hauteur differe de moins que cela sont consideres comme coplanaires
TOL_PLAT = 1e-3        # un triangle est plat si ses trois sommets ont la meme hauteur a cela pres


def _recouvre(a, b):
    """Les deux triangles (3 x 2, plan xz) ont-ils une intersection d'aire non nulle ? Axe separateur sur chaque arete."""
    for t in (a, b):
        for i in range(3):
            x0, z0 = t[i]; x1, z1 = t[(i + 1) % 3]
            ax, az = -(z1 - z0), x1 - x0
            pa = [p[0] * ax + p[1] * az for p in a]; pb = [p[0] * ax + p[1] * az for p in b]
            if max(pa) <= min(pb) + 1e-6 or max(pb) <= min(pa) + 1e-6: return False
    return True


def decaler(c, log=None):
    """Releve les triangles plats superposes de `c['groupes']` (remplace par un nouveau dictionnaire de groupes ; le cache de carte n'est pas touche). -> nombre de triangles releves."""
    groupes, textures = c['groupes'], c['textures']
    brut = []                                        # (ordre de dessin, cle, triangles T (n, 3, 3), indices plats, hauteurs, decoupe ?)
    haut_deco = set()
    for ordre, (cle, (pos, uv, col)) in enumerate(groupes.items()):
        if cle not in textures or len(pos) % 3: continue
        T = np.asarray(pos).reshape(-1, 3, 3)
        idx = np.nonzero((T[..., 1].max(1) - T[..., 1].min(1)) < TOL_PLAT)[0]
        if not len(idx): continue
        tex = textures[cle]; decoupe = bool(tex.ndim == 3 and tex.shape[2] == 4 and (tex[..., 3] < 250).any()) or (isinstance(cle, tuple) and cle[0] == 'tr')
        ys = T[idx, :, 1].mean(1); seau = np.round(ys / (2 * TOL_Y)).astype(int)
        if decoupe: haut_deco.update(seau.tolist())
        brut.append((ordre, cle, T, idx, ys, seau, decoupe))
    if not haut_deco: return 0
    proches = np.array(sorted(haut_deco | {h - 1 for h in haut_deco} | {h + 1 for h in haut_deco}))
    plats = []                                       # (ordre de dessin, cle, indice du triangle, hauteur, triangle xz, decoupe ?) : seulement les triangles a une hauteur ou se trouve un triangle decoupe
    for ordre, cle, T, idx, ys, seau, decoupe in brut:
        garde = np.nonzero(np.isin(seau, proches))[0]
        for j in garde: plats.append((ordre, cle, int(idx[j]), float(ys[j]), T[idx[j]][:, [0, 2]].astype(float), decoupe))
    if len(plats) < 2: return 0
    seaux = {}                                       # hauteur arrondie -> triangles (les seaux voisins sont aussi regardes : une limite de seau peut separer deux hauteurs proches)
    for k, p in enumerate(plats): seaux.setdefault(int(round(p[3] / (2 * TOL_Y))), []).append(k)
    boite = np.array([[p[3], p[4][:, 0].min(), p[4][:, 0].max(), p[4][:, 1].min(), p[4][:, 1].max()] for p in plats])        # hauteur, x min / max, z min / max de chaque triangle
    sous = {}                                        # triangle -> triangles dessines avant lui, a la meme hauteur, qu'il recouvre (au moins l'un des deux est decoupe : deux triangles pleins et opaques ne scintillent pas visiblement)
    for sx, liste in seaux.items():
        deco = [k for k in liste if plats[k][5]]
        if not deco: continue
        voisins = np.array([m for sy in (sx - 1, sx, sx + 1) for m in seaux.get(sy, ())]); B = boite[voisins]
        for d in deco:
            y, x0, x1, z0, z1 = boite[d]
            ok = (np.abs(B[:, 0] - y) <= TOL_Y) & (B[:, 2] >= x0) & (B[:, 1] <= x1) & (B[:, 4] >= z0) & (B[:, 3] <= z1) & (voisins != d)
            for m in voisins[ok]:
                a, b = plats[d], plats[int(m)]
                if not _recouvre(a[4], b[4]): continue
                dessous, dessus = (int(m), d) if (b[0], b[2]) < (a[0], a[2]) else (d, int(m))
                sous.setdefault(dessus, set()).add(dessous)
    if not sous: return 0
    niveau = {}
    for k in sorted(sous, key=lambda k: (plats[k][0], plats[k][2])):            # dans l'ordre de dessin : le niveau d'un triangle suit celui des triangles dessous
        niveau[k] = 1 + max(niveau.get(m, 0) for m in sous[k])
    nouveaux = {}
    for k, n in niveau.items():
        a = plats[k]; cle = a[1]
        if cle not in nouveaux: nouveaux[cle] = np.array(groupes[cle][0], np.float32, copy=True).reshape(-1, 3, 3)
        nouveaux[cle][a[2], :, 1] += n * PAS
    g2 = dict(groupes)
    for cle, T in nouveaux.items(): g2[cle] = (T.reshape(-1, 3), groupes[cle][1], groupes[cle][2])
    c['groupes'] = g2
    if log: log('décor : %d triangles plats superposés relevés (%d groupes)' % (len(niveau), len(nouveaux)))
    return len(niveau)
