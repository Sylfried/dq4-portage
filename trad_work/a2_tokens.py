import re,sys,glob
tsv={}
for l in open('/home/claude/dq4-portage/docs/rename_identifiers.tsv',encoding='utf-8').read().split('\n')[1:]:
    if '\t' in l:
        a,b=l.split('\t',1); tsv[a]=b
files=sorted(glob.glob('docs/docs__archives__agent-reports-40-44.md.0[01][0-9].in.md'))
mine=[f for f in files if any(f.endswith('.%s.in.md'%n) for n in ('006','007','008','009','010'))]
from collections import Counter
c=Counter()
for f in mine:
    s=open(f,encoding='utf-8').read()
    for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*",s):
        if t in tsv: c[t]+=1
for t,n in sorted(c.items(), key=lambda x:-x[1]):
    print(n,t,'->',tsv[t])
