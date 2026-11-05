import json, collections, statistics
D = json.load(open('mesures.json')); rows = D['rows']
PX = 1.008          # 1 u en px a 720p
NB = '   '
def cls_cell(r):
    P = r['probe']['P']; V = r['probe']['V']
    info = dict(r=r, dz=0.0, dx=0.0, ts=1.0, lines=0, ovP=0.0, ovV=0.0, nbsp=False, flags=[], cls='a', n=len(r['real']), why=[])
    if P is None or V is None:
        info['cls'] = '?'; info['why'].append('rien dessine (sonde)'); return info
    info['dz'] = V['base0'] - P['base0']
    # chaines reelles
    maxdx = 0.0; ts = 1.0; nl = 0; ovp = 0.0; ovv = 0.0; maxdz_r = 0.0
    c = r['container']
    for e in r['real']:
        p, v = e['P'], e['V']
        if not p or not v: continue
        if any(ch in e['s'] for ch in NB): info['nbsp'] = True
        dxl = v['xl'] - p['xl']; dxr = v['xr'] - p['xr']
        # decalage horizontal du bord gauche, ou de la largeur : on retient le pire des deux
        d = max(abs(dxl), abs(dxr)); maxdx = max(maxdx, d)
        ts = min(ts, v['ts'])
        if v['lines'] != p['lines']: nl += 1
        maxdz_r = max(maxdz_r, abs(v['base0'] - p['base0']))
        if c:
            k, x0, x1, z0, z1 = c
            ovp = max(ovp, p['xr'] - x1, x0 - p['xl'])
            ovv = max(ovv, v['xr'] - x1, x0 - v['xl'])
    info.update(dx=maxdx, ts=ts, lines=nl, ovP=ovp, ovV=ovv)
    f = info['flags']
    if abs(info['dz']) > 0.05: f.append('R')            # recentrage vertical
    if info['nbsp'] and maxdx > 0.5: f.append('T')      # espaces fines
    if ts < 0.999: f.append('K')                        # compression horizontale
    if nl: f.append('W')                                # recoupe en lignes
    if ovp > 0.5: f.append('d')                         # depasse le conteneur meme en mode jeu
    # classe
    big = (ts < 0.999) or nl or ('T' in f) or abs(info['dz']) > 7
    if big: info['cls'] = 'c'
    elif 'R' in f: info['cls'] = 'b'
    else: info['cls'] = 'a'
    return info

I = [cls_cell(r) for r in rows]
cnt = collections.Counter(i['cls'] for i in I)
print('classes', cnt)
fl = collections.Counter(f for i in I for f in i['flags']); print('flags', fl)
print('cells with d overflow and class', collections.Counter(i['cls'] for i in I if 'd' in i['flags']))
# cellules c : details
for i in I:
    if i['cls'] == 'c':
        r = i['r']; print(r['typ'], r['name'], r['id'], r['no'], 'anc', r['anchor'], 'ls %.3f' % r['ls'], i['flags'], 'dz %.2f dx %.2f ts %.3f lines %d n %d src %s' % (i['dz'], i['dx'], i['ts'], i['lines'], i['n'], r['src']))
json.dump([dict(typ=i['r']['typ'], id=i['r']['id'], no=i['r']['no'], cls=i['cls'], flags=i['flags'], dz=i['dz'], dx=i['dx'], ts=i['ts'], lines=i['lines'], ovP=i['ovP'], ovV=i['ovV']) for i in I], open('classes.json', 'w'))
