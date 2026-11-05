"""catalog_clean.py [--write] : remove catalog entries whose French key is no longer present as a code constant anywhere (only keys I converted)."""
import ast, os, sys, json, importlib
ROOT = '/home/claude/wt-console'; sys.path.insert(0, ROOT)
WRITE = '--write' in sys.argv
rep = json.load(open('/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/console/report.json'))
consts = set()
for sub in ('dq4_pc', 'tools'):
    for d, _, fs in os.walk(os.path.join(ROOT, sub)):
        if '__pycache__' in d or d.endswith('texts_en'): continue
        for f in fs:
            if not f.endswith('.py'): continue
            tree = ast.parse(open(os.path.join(d, f), encoding='utf-8').read())
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant) and isinstance(n.value, str): consts.add(n.value)
import ast as _a
import subprocess
changed_old = set()
files = subprocess.run(['git', '-C', ROOT, 'diff', '--name-only', 'HEAD', '--', 'dq4_pc', 'tools'], capture_output=True, text=True).stdout.split()
for rel in files:
    if not rel.endswith('.py') or '/texts_en/' in rel: continue
    old_src = subprocess.run(['git', '-C', ROOT, 'show', 'HEAD:' + rel], capture_output=True, text=True).stdout
    try: o = {n.value for n in ast.walk(ast.parse(old_src)) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    except SyntaxError: continue
    n_ = {n.value for n in ast.walk(ast.parse(open(os.path.join(ROOT, rel), encoding='utf-8').read())) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    changed_old |= (o - n_)
print('constants removed from code by this work:', len(changed_old))
# also earlier catalog keys converted by previous apply runs: the report only has the last run, so use git: keys of the catalog absent from the code now
removed = {}
for name_str in ('pause', 'menus', 'window', 'divers'):
    p = os.path.join(ROOT, 'dq4_pc/texts_en/%s.py' % name_str)
    src = open(p, encoding='utf-8').read(); tree = _a.parse(src)
    d = next(n for n in tree.body if isinstance(n, _a.Assign) and n.targets[0].id == 'EN').value
    lines = src.split('\n'); drop = set()
    for k, v in zip(d.keys, d.values):
        if k.value in changed_old and k.value not in consts:
            drop.update(range(k.lineno, v.end_lineno + 1)); removed.setdefault(name_str, []).append((k.lineno, k.value))
    if not removed.get(name_str): continue
    # drop section header comments left without entries
    out = []; i = 0
    L = [(n, l) for n, l in enumerate(lines, 1)]
    keep = [(n, l) for n, l in L if n not in drop]
    final = []
    for idx, (n, l) in enumerate(keep):
        if l.strip().startswith('#'):
            # look ahead for the next non-comment, non-blank line
            j = idx + 1
            while j < len(keep) and (keep[j][1].strip().startswith('#') or not keep[j][1].strip()): j += 1
            if j >= len(keep) or keep[j][1].strip() == '}': continue
            if keep[idx + 1][1].strip().startswith('#') : continue
        final.append(l)
    if WRITE: open(p, 'w', encoding='utf-8', newline='').write('\n'.join(final))
for name_str, ks in removed.items():
    print(name_str, len(ks))
    for ln, k in ks: print('  %d %r' % (ln, k[:110]))
