import json, collections
D = json.load(open('mesures.json')); rows = D['rows']; CAPH = D['CAPH']
print('CAPH px', CAPH)
# C : decalage vertical de l'encre des majuscules par rapport au centre du conteneur (mode P = jeu, mode V = visionneuse)
for typ in (3, 8, 9, 4, 5, 10, 20, 21, 36, 35, 58, 60, 57, 32, 30):
    out = []
    for r in rows:
        if r['typ'] != typ or not r['container'] or not r['probe']['P']: continue
        k, x0, x1, z0, z1 = r['container']
        for m in 'PV':
            pass
        P = r['probe']['P']; V = r['probe']['V']; u = P['u']
        cp = (z0 + z1) / 2
        out.append((r['id'], r['no'], k, r['anchor'], round(r['ls'], 3), r['cs'], round(P['base0'] + CAPH * u / 2 - cp, 2), round(V['base0'] + CAPH * u / 2 - cp, 2), round(z1 - z0, 1)))
    print('--- type', typ, rows[[r['typ'] for r in rows].index(typ)]['name'])
    for o in out: print('   id %d no %d %s anc %d ls %.3f cs %.2f | encre-centre P %+.2f V %+.2f (conteneur h %.1f)' % o)
