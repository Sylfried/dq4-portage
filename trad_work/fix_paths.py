"""Post-pass on translated batches: old file/folder names -> current names (from docs/rename_map.md).
usage: python3 fix_paths.py [--write] batches/batch_NN.out.txt ..."""
import re, sys, collections
MAP = '/home/claude/dq4-portage/docs/rename_map.md'
row = re.compile(r'^\|\s*`([^`|]+)`[^|]*\|\s*`([^`|]+)`')
files = collections.defaultdict(set); dirs = {}
sect = None
for line in open(MAP, encoding='utf-8'):
    if line.startswith('## '): sect = line.strip()
    m = row.match(line)
    if not m: continue
    a, b = m.group(1), m.group(2)
    if a == b: continue
    if sect.startswith('## Dossiers') and not sect.startswith('## Dossiers et'):
        dirs[a] = b
    elif re.search(r'\.\w{1,5}$', a) and '<' not in a:
        base_a = re.split(r'[\\/]', a)[-1]; base_b = re.split(r'[\\/]', b)[-1]
        if base_a != base_b: files[base_a].add(base_b)
# unambiguous basename mapping
fmap = {a: next(iter(v)) for a, v in files.items() if len(v) == 1}
# dir mapping on last component + parent form
dmap = {}
for a, b in dirs.items():
    if a.startswith('dq4_pc/'): a, b = a[len('dq4_pc/'):], b[len('dq4_pc/'):]
    dmap[a.rstrip('/')] = b.rstrip('/')
pairs = []
for a, b in sorted(fmap.items(), key=lambda x: -len(x[0])):
    pairs.append((re.compile(r'(?<![\w.])' + re.escape(a) + r'(?![\w])'), b, a))
for a, b in sorted(dmap.items(), key=lambda x: -len(x[0])):
    pairs.append((re.compile(r'(?<![\w.])' + re.escape(a) + r'(?=[/\\])'), b, a))
extra = [('donnees', 'data'), ('sauvegardes', 'saves')]  # only when followed by a backslash (PC folders)
for a, b in extra:
    pairs.append((re.compile(r'(?<![\w.])' + a + r'(?=\\)'), b, a))
write = '--write' in sys.argv
SKIP = re.compile(r'migrat|renam|\bold\b|earlier|former|legacy|before D-|from before|already renamed|D-239|D-235|etapes|previous layout|used to', re.I)
tot = collections.Counter(); skipped = 0
def fix_block(text):
    global skipped
    if SKIP.search(text): skipped += 1; return text
    for rx, new, old in pairs:
        text, n = rx.subn(new, text)
        if n: tot[(old, new)] += n
    return text
for fn in [x for x in sys.argv[1:] if not x.startswith('--')]:
    src = open(fn, encoding='utf-8').read(); out = []; buf = []
    def flush():
        if buf: out.append(fix_block('\n'.join(buf))); buf.clear()
    for line in src.split('\n'):
        if line.startswith('@@ ') or line.startswith('## FILE '):
            flush(); out.append(line)
        else: buf.append(line)
    flush()
    res = '\n'.join(out)
    if write and res != src: open(fn, 'w', encoding='utf-8', newline='\n').write(res)
for (o, n), c in tot.most_common(): print(f'{c:4d}  {o} -> {n}')
print('total', sum(tot.values()), 'blocks skipped (migration/legacy context):', skipped)
