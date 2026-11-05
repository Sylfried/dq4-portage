import ast, os, re, sys, json
ROOT = '/home/claude/wt-console'
sub = sys.argv[1]
for d, _, fs in os.walk(os.path.join(ROOT, sub)):
    if '__pycache__' in d: continue
    for f in sorted(fs):
        if not f.endswith('.py'): continue
        p = os.path.join(d, f); rel = os.path.relpath(p, ROOT)
        src = open(p, encoding='utf-8').read(); tree = ast.parse(src)
        docs = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant): docs.add(id(n.body[0].value))
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
                v = n.value
                if re.search(r'[A-Za-z]{3,}', v) and re.search(r'[ %]', v) and not re.search(r'[A-Za-z]{3,}[ ,:;]+[A-Za-z]{2,}', v) and not v.startswith(('/', '#')):
                    print('%s:%d %s' % (rel, n.lineno, json.dumps(v, ensure_ascii=False)[:170]))
