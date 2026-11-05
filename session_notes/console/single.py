import ast, os, re, sys, json, collections
ROOT = '/home/claude/wt-console'
SINK = {'print','log','note','talk','j','exit','SystemExit','_wait','out','show'}
words = collections.defaultdict(set)
for d, _, fs in os.walk(os.path.join(ROOT, sys.argv[1])):
    if '__pycache__' in d: continue
    for f in fs:
        if not f.endswith('.py'): continue
        p = os.path.join(d, f); rel = os.path.relpath(p, ROOT)
        tree = ast.parse(open(p, encoding='utf-8').read())
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and (getattr(n.func, 'id', None) or getattr(n.func, 'attr', None)) in SINK:
                for a in n.args:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str) and re.fullmatch(r"[A-Za-z_' ]{3,40}[ :]*", a.value):
                        words[a.value.strip()].add(os.path.basename(rel))
for w in sorted(words): print('%-34s %s' % (w, ','.join(sorted(words[w]))[:90]))
