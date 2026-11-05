import json, collections
D = json.load(open('mesures.json')); rows = D['rows']
KEYS = {(7,0,1):148,(10,0,4):148,(38,2,3):56,(46,4,3):148,(60,4,4):148,(61,4,4):148,(63,0,4):148,(70,0,3):148}
for r in rows:
    k = (r['typ'], r['id'], r['no'])
    if k not in KEYS: continue
    lim = KEYS[k]; n = 0; changed = 0; wrapped = 0; comp = 0; same = 0; ovP = 0; ovV = 0; minTs = 1; maxdxr = 0
    for e in r['real']:
        p, v = e['P'], e['V']
        if not p or not v: continue
        n += 1
        ch = (v['lines'] != p['lines']) or v['ts'] < 0.999 or abs(v['xl'] - p['xl']) > 0.05 or abs(v['xr'] - p['xr']) > 0.05
        if v['lines'] != p['lines']: wrapped += 1
        if v['ts'] < 0.999: comp += 1; minTs = min(minTs, v['ts'])
        if ch: changed += 1
        else: same += 1
        if p['xr'] > lim + 0.5: ovP += 1
        if v['xr'] > lim + 0.5: ovV += 1
    print(k, r['name'], 'chaines', n, 'modifiees', changed, 'recoupees', wrapped, 'comprimees', comp, 'ts min %.2f' % minTs, 'identiques', same, '| depassent la limite %g: mode jeu %d, visionneuse %d' % (lim, ovP, ovV))
