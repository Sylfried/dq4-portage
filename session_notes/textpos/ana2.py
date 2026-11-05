import json, collections
D = json.load(open('mesures.json')); rows = D['rows']
for r in rows:
    P = r['probe']['P'];  V = r['probe']['V']
    if P and (abs(V['xl'] - P['xl']) > 0.05 or abs(V['ts'] - P['ts']) > 1e-3):
        print('PROBE x/ts', r['typ'], r['name'], r['id'], r['no'], 'xl', round(P['xl'], 2), round(V['xl'], 2), 'ts', round(P['ts'], 3), round(V['ts'], 3), 'ctn', r['container'])
# vraies chaines : ecarts V-P
n = 0; chg = collections.Counter(); ex = collections.defaultdict(list)
for r in rows:
    for e in r['real']:
        P, V = e['P'], e['V']
        if not P or not V: continue
        n += 1
        k = []
        if P['lines'] != V['lines']: k.append('lignes %d->%d' % (P['lines'], V['lines']))
        if abs(V['ts'] - P['ts']) > 1e-3: k.append('ts')
        if abs(V['xl'] - P['xl']) > 0.05 or abs(V['xr'] - P['xr']) > 0.05: k.append('x')
        if k:
            chg[tuple(k)] += 1
            ex[tuple(k)].append((r['typ'], r['name'], r['id'], r['no'], e['s'][:50], round(P['xl'], 1), round(P['xr'], 1), round(V['xl'], 1), round(V['xr'], 1), round(P['ts'], 3), round(V['ts'], 3)))
print('chaines mesurees', n, chg)
for k, v in ex.items():
    print(k)
    for x in v[:25]: print('  ', x)
