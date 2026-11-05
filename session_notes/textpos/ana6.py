import json, collections
D = json.load(open('mesures.json')); rows = D['rows']
print('--- cellules centrees (colonne 1) dont le point d ancrage n est pas au centre horizontal de la plaque/cadre qui le contient (mode P = jeu)')
seen = set()
for r in rows:
    c = r['container']; P = r['probe']['P']
    if not c or not P or r['anchor'] % 3 != 1: continue
    k, x0, x1, z0, z1 = c; cen = (x0 + x1) / 2; ax = r['pos'][0]
    if abs(ax - cen) > 1.0:
        key = (r['typ'], r['id'], r['no'])
        print('type %d %s id %d no %d | %s x[%.1f,%.1f] centre %.1f ancre %.1f ecart %+.1f' % (r['typ'], r['name'], r['id'], r['no'], k, x0, x1, cen, ax, ax - cen))
print('--- cellules a gauche (col 0) : marge entre bord gauche du conteneur et ancre ; a droite (col 2) : marge ancre / bord droit')
marg = collections.defaultdict(list)
for r in rows:
    c = r['container']
    if not c or r['anchor'] % 3 == 1 or c[0] != 'plaque': continue
    k, x0, x1, z0, z1 = c; ax = r['pos'][0]
    m = (ax - x0) if r['anchor'] % 3 == 0 else (x1 - ax)
    marg[(r['anchor'] % 3, round(m, 1))].append((r['typ'], r['id'], r['no']))
for k, v in sorted(marg.items()): print(k, len(v), v[:4])
