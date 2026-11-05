"""Decors a plat superposes a la meme hauteur (massifs de fleurs sur une autre bordure, chemin sur pelouse...) : correctif du scintillement par z-fighting.

Deux triangles horizontaux a la meme hauteur ont la meme profondeur a l'arrondi pres : le test de profondeur donne l'un ou l'autre pixel par pixel, et le resultat change a chaque
mouvement de la camera (les fleurs « scintillent »). Au chargement d'une carte on releve tres legerement (3 millimetres d'unite de ville, soit moins d'un dixieme de pixel) chaque triangle
plat qui en recouvre un autre deja dessine a sa hauteur, d'autant que de triangles empiles ; le dernier dessine l'emporte, toujours. Les groupes de textures sont copies : le cache de carte reste intact.
"""
import numpy as np
from dq4_pc.language import tr

STEP = 0.003            # hauteur ajoutee par triangle empile (unites de ville)
TOL_Y = 0.0015         # deux triangles plats dont la hauteur differe de moins que cela sont consideres comme coplanaires
FLAT_TOLERANCE = 1e-3        # un triangle est plat si ses trois sommets ont la meme hauteur a cela pres


def _overlaps(a, b):
    """Les deux triangles (3 x 2, plan xz) ont-ils une intersection d'aire non nulle ? Axe separateur sur chaque arete."""
    for t in (a, b):
        for i in range(3):
            x0, z0 = t[i]; x1, z1 = t[(i + 1) % 3]
            ax, az = -(z1 - z0), x1 - x0
            pa = [p[0] * ax + p[1] * az for p in a]; pb = [p[0] * ax + p[1] * az for p in b]
            if max(pa) <= min(pb) + 1e-6 or max(pb) <= min(pa) + 1e-6: return False
    return True


def shift(c, log=None):
    """Releve les triangles plats superposes de `c['groupes']` (remplace par un nouveau dictionnaire de groupes ; le cache de carte n'est pas touche). -> nombre de triangles releves."""
    groups, textures = c['groupes'], c['textures']
    raw_value = []                                        # (ordre de dessin, cle, triangles T (n, 3, 3), indices plats, hauteurs, decoupe ?)
    scenery_top = set()
    for order, (lookup_key, (pos, uv, col)) in enumerate(groups.items()):
        if lookup_key not in textures or len(pos) % 3: continue
        T = np.asarray(pos).reshape(-1, 3, 3)
        idx = np.nonzero((T[..., 1].max(1) - T[..., 1].min(1)) < FLAT_TOLERANCE)[0]
        if not len(idx): continue
        tex = textures[lookup_key]; sliced = bool(tex.ndim == 3 and tex.shape[2] == 4 and (tex[..., 3] < 250).any()) or (isinstance(lookup_key, tuple) and lookup_key[0] == 'tr')
        ys = T[idx, :, 1].mean(1); bucket = np.round(ys / (2 * TOL_Y)).astype(int)
        if sliced: scenery_top.update(bucket.tolist())
        raw_value.append((order, lookup_key, T, idx, ys, bucket, sliced))
    if not scenery_top: return 0
    nearby = np.array(sorted(scenery_top | {h - 1 for h in scenery_top} | {h + 1 for h in scenery_top}))
    flat_items = []                                       # (ordre de dessin, cle, indice du triangle, hauteur, triangle xz, decoupe ?) : seulement les triangles a une hauteur ou se trouve un triangle decoupe
    for order, lookup_key, T, idx, ys, bucket, sliced in raw_value:
        guard = np.nonzero(np.isin(bucket, nearby))[0]
        for j in guard: flat_items.append((order, lookup_key, int(idx[j]), float(ys[j]), T[idx[j]][:, [0, 2]].astype(float), sliced))
    if len(flat_items) < 2: return 0
    buckets = {}                                       # hauteur arrondie -> triangles (les seaux voisins sont aussi regardes : une limite de seau peut separer deux hauteurs proches)
    for k, p in enumerate(flat_items): buckets.setdefault(int(round(p[3] / (2 * TOL_Y))), []).append(k)
    box = np.array([[p[3], p[4][:, 0].min(), p[4][:, 0].max(), p[4][:, 1].min(), p[4][:, 1].max()] for p in flat_items])        # hauteur, x min / max, z min / max de chaque triangle
    under = {}                                        # triangle -> triangles dessines avant lui, a la meme hauteur, qu'il recouvre (au moins l'un des deux est decoupe : deux triangles pleins et opaques ne scintillent pas visiblement)
    for sx, entries in buckets.items():
        deco = [k for k in entries if flat_items[k][5]]
        if not deco: continue
        neighbors = np.array([m for sy in (sx - 1, sx, sx + 1) for m in buckets.get(sy, ())]); B = box[neighbors]
        for d in deco:
            y, x0, x1, z0, z1 = box[d]
            ok = (np.abs(B[:, 0] - y) <= TOL_Y) & (B[:, 2] >= x0) & (B[:, 1] <= x1) & (B[:, 4] >= z0) & (B[:, 3] <= z1) & (neighbors != d)
            for m in neighbors[ok]:
                a, b = flat_items[d], flat_items[int(m)]
                if not _overlaps(a[4], b[4]): continue
                below, above = (int(m), d) if (b[0], b[2]) < (a[0], a[2]) else (d, int(m))
                under.setdefault(above, set()).add(below)
    if not under: return 0
    level = {}
    for k in sorted(under, key=lambda k: (flat_items[k][0], flat_items[k][2])):            # dans l'ordre de dessin : le niveau d'un triangle suit celui des triangles dessous
        level[k] = 1 + max(level.get(m, 0) for m in under[k])
    new_ones = {}
    for k, n in level.items():
        a = flat_items[k]; lookup_key = a[1]
        if lookup_key not in new_ones: new_ones[lookup_key] = np.array(groups[lookup_key][0], np.float32, copy=True).reshape(-1, 3, 3)
        new_ones[lookup_key][a[2], :, 1] += n * STEP
    g2 = dict(groups)
    for lookup_key, T in new_ones.items(): g2[lookup_key] = (T.reshape(-1, 3), groups[lookup_key][1], groups[lookup_key][2])
    c['groupes'] = g2
    if log: log(tr('décor : %d triangles plats superposés relevés (%d groupes)') % (len(level), len(new_ones)))
    return len(level)
