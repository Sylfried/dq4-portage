import ast, os, re, sys, json, pickle
exec(open('inventory.py').read().split('class V')[0].replace('ROOT = sys.argv[1]','ROOT=""'))
ROOT='/home/claude/wt-console'
covered=set((r[0],r[1],r[2]) for r in pickle.load(open('inv2.pkl','rb')))
sub = sys.argv[1:] or ['dq4_pc']
for s in sub:
  for d,_,fs in os.walk(os.path.join(ROOT,s)):
    if '__pycache__' in d or '/texts_en' in d: continue
    for f in sorted(fs):
        if not f.endswith('.py') or f=='language.py': continue
        p=os.path.join(d,f); rel=os.path.relpath(p,ROOT)
        src=open(p,encoding='utf-8').read(); tree=ast.parse(src)
        parents={id(c):n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
        docs=set()
        for n in ast.walk(tree):
            if isinstance(n,(ast.Module,ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant) and isinstance(n.body[0].value.value,str): docs.add(id(n.body[0].value))
        for n in ast.walk(tree):
            if isinstance(n,ast.Constant) and isinstance(n.value,str) and id(n) not in docs:
                if (rel,n.lineno,n.col_offset) in covered: continue
                par=parents.get(id(n))
                if isinstance(par,ast.Call) and (getattr(par.func,'id',None) or getattr(par.func,'attr',None)) in ('tr','N_'): continue
                v=n.value
                if len(v.strip())<4 or not has_fr(v): continue
                print('%s:%d %s' % (rel,n.lineno,json.dumps(v,ensure_ascii=False)[:200]))
