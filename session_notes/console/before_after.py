import ast, difflib, os, subprocess, sys, json, collections
ROOT = '/home/claude/wt-console'
S = '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/console/'
files = subprocess.run(['git', '-C', ROOT, 'diff', '--name-only', 'HEAD'], capture_output=True, text=True).stdout.split()
def consts(src):
    tree = ast.parse(src); docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant): docs.add(id(n.body[0].value))
    out = [(n.lineno, n.col_offset, n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]
    out.sort(); return out
rows = []; counts = collections.OrderedDict()
for rel in sorted(files):
    path = os.path.join(ROOT, rel)
    old = subprocess.run(['git', '-C', ROOT, 'show', 'HEAD:' + rel], capture_output=True).stdout.decode('utf-8')
    new = open(path, encoding='utf-8', newline='').read()
    if rel.endswith('.py'):
        if rel.startswith('tests/') or '/texts_en/' in rel: continue
        o = consts(old); n = consts(new)
        sm = difflib.SequenceMatcher(None, [x[2] for x in o], [x[2] for x in n], autojunk=False)
        c = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal': continue
            if tag == 'replace' and (i2 - i1) == (j2 - j1):
                for a, b in zip(o[i1:i2], n[j1:j2]): rows.append((rel, b[0], a[2], b[2])); c += 1
            else:
                for a in o[i1:i2]: rows.append((rel, '', a[2], '(removed)'))
                for b in n[j1:j2]: rows.append((rel, b[0], '(added)', b[2]))
                c += max(i2 - i1, j2 - j1)
        if c: counts[rel] = c
    else:
        ol = old.replace('\r', '').split('\n'); nl = new.replace('\r', '').split('\n'); c = 0
        sm = difflib.SequenceMatcher(None, ol, nl, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal': continue
            for k in range(max(i2 - i1, j2 - j1)):
                a = ol[i1 + k] if i1 + k < i2 else '(removed)'; b = nl[j1 + k] if j1 + k < j2 else '(removed)'
                rows.append((rel, j1 + k + 1 if j1 + k < j2 else '', a, b)); c += 1
        counts[rel] = c
with open(S + 'before_after.tsv', 'w', encoding='utf-8') as f:
    f.write('file\tline\tbefore\tafter\n')
    for r in rows: f.write('\t'.join(str(x).replace('\t', ' ').replace('\n', '\\n') for x in r) + '\n')
json.dump(counts, open(S + 'counts.json', 'w'), indent=1)
print(len(rows), 'rows;', sum(counts.values()), 'strings in', len(counts), 'files')
by = collections.Counter()
for rel, c in counts.items():
    by[rel.split('/')[0] + ('/research' if rel.startswith('tools/research') else '')] += c
print(dict(by))
for rel, c in counts.items(): print('%4d %s' % (c, rel))
