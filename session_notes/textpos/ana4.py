import json, collections
D = json.load(open('mesures.json')); rows = D['rows']; CAPH = D['CAPH']
print('cellules dont l encre des majuscules (mode P) sort verticalement de son conteneur (plaque ou plus petit cadre)')
seen = set()
for r in rows:
    c = r['container']; P = r['probe']['P']
    if not c or not P: continue
    k, x0, x1, z0, z1 = c; u = P['u']
    lo = P['base0']; hi = P['base0'] + CAPH * u; nl = P['lines']
    if lo < z0 - 0.5 or hi > z1 + 0.5:
        key = (r['typ'], r['name'], r['anchor'], round(r['ls'], 3), r['cs'], k, round(lo - z0, 1), round(z1 - hi, 1))
        if key in seen: continue
        seen.add(key)
        print('type %d %s id %d no %d | anc %d ls %.3f cs %.2f | %s h %.0f | bas encre - bord bas %+.1f ; bord haut - haut encre %+.1f' % (r['typ'], r['name'], r['id'], r['no'], r['anchor'], r['ls'], r['cs'], k, z1 - z0, lo - z0, z1 - hi))
