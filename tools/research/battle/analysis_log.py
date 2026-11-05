import sys, re
def read(f):
    ev = []
    for l in open(f):
        m = re.match(r'T=([\d.]+) img=(\d+) effect=(\d) waiting=(\d) fade=(\d) background=(\d) part=(0x\w+) fa=([\d.]+) fn=(\d+)', l)
        if m: ev.append(dict(T=float(m[1]), img=int(m[2]), effet=int(m[3]), att=int(m[4]), fondu=int(m[5]), fond=int(m[6]), partie=int(m[7], 16), fa=float(m[8]), fn=int(m[9])))
    return ev
def phases(ev):
    out = {}
    def found(pred, d=0):
        for i, e in enumerate(ev):
            if i >= d and pred(e): return i
    i0 = found(lambda e: e['effet'])
    if i0 is None: return out
    i1 = found(lambda e: not e['effet'], i0)
    out['cascade'] = (ev[i0]['img'], ev[i1]['img'], ev[i1]['T'] - ev[i0]['T'])
    i2 = found(lambda e: not e['att'], i1)
    out['noir_attente'] = (ev[i1]['img'], ev[i2]['img'], ev[i2]['T'] - ev[i1]['T'])
    # fondu d'entree du combat : premiere periode fondu apres i2-1
    j0 = found(lambda e: e['fondu'], i2 - 1)
    j1 = found(lambda e: not e['fondu'], j0)
    out['fondu_entree'] = (ev[j0]['img'], ev[j1]['img'], ev[j1]['T'] - ev[j0]['T'])
    # fin : derniere sortie 4126 : fondu avec fa croissante en partie combat (fa < 1 au debut) apres le debut du combat + 100 images
    k = found(lambda e: e['fondu'] and e['partie'] == 0xd and e['img'] > ev[j1]['img'] + 100 and e['fa'] < 0.5 and e['fn'] >= 5, j1)
    if k is not None:
        # fin : la derniere periode de fondu en combat jusqu'au retour
        k1 = found(lambda e: not e['fondu'], k)
        out['fondu_sortie'] = (ev[k]['img'], ev[k1]['img'], ev[k1]['T'] - ev[k]['T'])
        r = found(lambda e: e['partie'] != 0xd, k)
        if r is not None:
            r0 = found(lambda e: e['fondu'], r)
            if r0 is not None:
                r1 = found(lambda e: not e['fondu'], r0)
                out['fondu_retour'] = (ev[r0]['img'], ev[r1]['img'], ev[r1]['T'] - ev[r0]['T']) if r1 is not None else (ev[r0]['img'], None, None)
    return out
for f in sys.argv[1:]:
    ev = read(f)
    print(f)
    for k, (a, b, t) in phases(ev).items(): print('   %-14s engine frames %s -> %s = %s frames ; real time %s s ; %s frames/s' % (k, a, b, None if b is None else b - a, None if t is None else '%.2f' % t, None if (b is None or t is None or t == 0) else '%.1f' % ((b - a) / t)))
