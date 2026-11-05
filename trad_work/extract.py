"""usage: extract.py <depot> <dossier de sortie> [taille max d'un lot en octets]
Ecrit batch_NN.in.txt (a traduire) et ids.json (id -> fichiers)."""
import json, os, subprocess, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trad_lib as T
repo, outdir = sys.argv[1], sys.argv[2]; maxb = int(sys.argv[3]) if len(sys.argv) > 3 else 60000
os.makedirs(outdir, exist_ok=True)
files = subprocess.check_output(['git', 'ls-files', '*.py'], cwd=repo, text=True).split()
files.sort(key=lambda f: (0 if f.startswith('dq4_pc/') else 1 if f.startswith('tools/') else 2, f))
seen = {}; groups = []; where = collections.defaultdict(list)
for f in files:
    src = open(os.path.join(repo, f), encoding='utf-8', newline='').read()
    its = []
    kinds = {}
    for it in T.comment_items(src) + T.docstring_items(src):
        k = 'd' if it['kind'] == 'd' else ('c' if it['full'] else 't')
        where[it['id']].append(f)
        if it['id'] in seen:
            if seen[it['id']] != k and k == 'c': seen[it['id']] = 'c'
            continue
        seen[it['id']] = k; its.append(it)
    if its: groups.append((f, [(i['id'], i['text']) for i in its]))
# lots : sans couper un element, en suivant l'ordre des fichiers
batches = []; cur = []; size = 0
for f, its in groups:
    part = []
    for i, text in its:
        n = len(text.encode()) + 30
        if size + n > maxb and (part or cur):
            if part: cur.append((f, part)); part = []
            batches.append(cur); cur = []; size = 0
        part.append((i, text)); size += n
    if part: cur.append((f, part))
if cur: batches.append(cur)
for n, b in enumerate(batches, 1):
    with open(os.path.join(outdir, f'batch_{n:02d}.in.txt'), 'w', encoding='utf-8', newline='\n') as fh:
        for f, its in b:
            fh.write(f'## FILE {f}\n')
            for i, text in its: fh.write(f'@@ {i} {seen[i]}\n{text}\n')
json.dump(where, open(os.path.join(outdir, 'ids.json'), 'w'))
tot = sum(len(t.encode()) for _, its in groups for _, t in its)
print(len(batches), 'lots,', len(seen), 'textes distincts,', tot, 'octets')
