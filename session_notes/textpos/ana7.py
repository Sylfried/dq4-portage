import json, collections
D = json.load(open('mesures.json')); rows = D['rows']
res = []
for r in rows:
    c = r['container']
    if not c or not r['real']: continue
    k, x0, x1, z0, z1 = c
    worst = None
    for e in r['real']:
        P, V = e['P'], e['V']
        if not P or not V: continue
        orp = P['xr'] - x1; olp = x0 - P['xl']; orv = V['xr'] - x1; olv = x0 - V['xl']
        o = max(orp, olp)
        if worst is None or o > worst[0]: worst = (o, orp, olp, orv, olv, e['s'], P['lines'], V['lines'], P['ts'], V['ts'], P['xl'], P['xr'])
    if worst: res.append((r, worst))
print('cellules avec chaines et conteneur', len(res))
print('--- debordement horizontal du conteneur en mode P (jeu), pire chaine, > 0,5 u')
for r, w in sorted(res, key=lambda x: -x[1][0]):
    if w[0] > 0.5:
        print('type %d %s id %d no %d [%s %s] anc %d tab %s | P: droite %+.1f gauche %+.1f | V: droite %+.1f gauche %+.1f | lignes %d->%d ts %.2f->%.2f | %r (%s)' % (r['typ'], r['name'], r['id'], r['no'], r['container'][0], r['src'], r['anchor'], r['tab'], w[1], w[2], w[3], w[4], w[6], w[7], w[8], w[9], w[5][:42], ''))
