"""Analyse de bal2_tout.json (balayage v2) : echecs, paquets rares, textures manquantes, PNJ sans position, sons, etc."""
import json, sys, collections, os
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else '/tmp/audit/bal2_tout.json'))
print('cartes', len(d), 'ok', sum(v['ok'] for v in d.values()), 'echecs', sum(not v['ok'] for v in d.values()), 'temps total', round(sum(v['t'] for v in d.values()), 1))
print('ECHECS :')
for k, v in d.items():
    if not v['ok']:
        e = v.get('exc', '')
        pc = [l.strip() for l in e.split('\\n') if 'PC =' in l or 'ERREUR' in l]
        print('  ', k, '|', ' ; '.join(pc)[:200] if pc else e[:200])
tot = collections.Counter(); cartes_par_type = collections.defaultdict(list)
for k, v in d.items():
    for t, n in (v.get('pkts') or {}).items(): tot[int(t)] += n; cartes_par_type[int(t)].append(k)
print('PAQUETS (type : total, nb cartes) :')
for t in sorted(tot): print('  ', t, tot[t], len(cartes_par_type[t]))
print('ABSENTS de la liste 0..37 :', [t for t in range(38) if t not in tot])
print('AU-DELA de 37 :', [t for t in tot if t > 37])

print('\n=== VALEURS DES TYPES RARES ===')
for t in ('2','3','4','5','7','14','16','17','19','20','21','22','31','32','33','35','37'):
    seen = collections.OrderedDict()
    for k, v in d.items():
        for val in (v.get('vals') or {}).get(t, []):
            key = json.dumps(val)
            seen.setdefault(key, []).append(k)
    print('type', t, ':', len(seen), 'valeurs distinctes')
    for key, cs in list(seen.items())[:6]:
        print('   ', key[:140], '<-', cs[:5], '(%d cartes)' % len(cs))
print('\n=== f13 (bits de drapeaux du paquet 13) ===')
c = collections.Counter()
for v in d.values():
    for k, n in (v.get('f13') or {}).items(): c[k] += n
print(dict(c))
print('echelles', sorted({e for v in d.values() for e in (v.get('echelles') or [])})[:40])
print('cams', collections.Counter(k for v in d.values() for k in (v.get('cams') or {})))
