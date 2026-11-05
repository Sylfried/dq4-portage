import json, collections
D = json.load(open('mesures.json')); rows = D['rows']
print('cells', len(rows), 'src', collections.Counter(r['src'] for r in rows))
def d(r, m, k): 
    a, b = r['probe'][m], r['probe']['P']
    return None if (a is None or b is None) else a[k] - b[k]
cat = collections.Counter(); big = []
for r in rows:
    P = r['probe']['P']
    if P is None: cat['rien'] += 1; continue
    dV = d(r, 'V', 'base0'); dC = d(r, 'C', 'base0'); dT = d(r, 'T', 'xr'); dW = d(r, 'W', 'xr')
    dx = d(r, 'V', 'xl'); ts = d(r, 'V', 'ts')
    key = []
    if abs(dV) > 0.05: key.append('recentre')
    if abs(dx) > 0.05 or abs(ts) > 1e-3: key.append('x/ts')
    cat[tuple(key)] += 1
    if abs(dV) > 0.05: big.append((round(dV, 2), r['typ'], r['name'], r['id'], r['no'], r['anchor'], round(r['ls'], 3), r['cs']))
print(cat)
big.sort(reverse=True)
print('recentrage max', big[:12]); 
import statistics
print('n recentre', len(big), 'min', min(b[0] for b in big), 'max', max(b[0] for b in big), 'median', statistics.median(b[0] for b in big))
# recentrage par ls
bl = collections.defaultdict(list)
for b in big: bl[(b[6], b[7])].append(b[0])
for k, v in sorted(bl.items()): print(k, len(v), v[0])
