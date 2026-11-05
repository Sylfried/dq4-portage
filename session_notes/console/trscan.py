import ast, os, sys, json, pickle, collections, importlib
sys.path.insert(0, '/home/claude/wt-console')
ROOT='/home/claude/wt-console'
from dq4_pc import language as LG
CAT = LG.catalog()
uses = collections.defaultdict(list)   # key -> [(file,line,col,in_sink)]
sinkpos = set()
rows = pickle.load(open('inv2.pkl','rb'))
for r in rows:
    if not r[3].startswith('flow'): sinkpos.add((r[0], r[1], r[2]))
for d,_,fs in os.walk(ROOT+'/dq4_pc'):
    for f in fs:
        if not f.endswith('.py') or '/texts_en' in d or f=='language.py': continue
        p=os.path.join(d,f); rel=os.path.relpath(p,ROOT)
        tree=ast.parse(open(p,encoding='utf-8').read())
        for n in ast.walk(tree):
            for c in ast.walk(n) if False else []: pass
        # all Constant strings, mark whether inside tr/N_ call as first arg
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and (getattr(n.func,'id',None) or getattr(n.func,'attr',None)) in ('tr','N_') and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value,str):
                c=n.args[0]
                uses[c.value].append((rel,c.lineno,c.col_offset,(rel,c.lineno,c.col_offset) in sinkpos, getattr(n.func,'id',None) or n.func.attr))
pickle.dump((dict(uses),CAT),open('uses.pkl','wb'))
shared=0
for k,v in sorted(uses.items(), key=lambda kv: kv[1][0]):
    sk=[u for u in v if u[3]]
    if sk and len(sk)<len(v):
        shared+=1
        print('SHARED', json.dumps(k,ensure_ascii=False)[:100], [(u[0].split('/')[-1],u[1],u[3],u[4]) for u in v])
print(shared)
