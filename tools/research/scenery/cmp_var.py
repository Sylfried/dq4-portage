import json, numpy as np
from PIL import Image
p = json.load(open('/tmp/dc/plan2.json'))
def img(n): return np.asarray(Image.open('/tmp/m_dc_var_b%d.png' % (n + 15)).convert('RGB')).astype(np.int16)
by = {}
for e in p: by.setdefault(e['tag'], {})[e['var']] = e['n']
for tag, d in by.items():
    if not all(os.path.exists('/tmp/m_dc_var_b%d.png' % (d[v] + 15)) for v in d) if False else False: pass
    try: A = {v: img(n) for v, n in d.items()}
    except FileNotFoundError: print(tag, 'not ready'); continue
    out = [tag]
    for v in ('po', 'bo'):
        if v in A:
            df = np.abs(A['av'] - A[v]).max(-1); out.append('%s: diff>8 %d px (%.3f%%) avg %.3f' % (v, (df > 8).sum(), 100 * (df > 8).mean(), df.mean()))
    print(' | '.join(out))
