import re
tsv={}
for l in open('/home/claude/dq4-portage/docs/rename_identifiers.tsv',encoding='utf-8').read().split('\n')[1:]:
    if '\t' in l:
        a,b=l.split('\t',1); tsv[a]=b
seen={}
for n in ('006','007','008','009','010'):
    s=open(f'docs/docs__archives__agent-reports-40-44.md.{n}.in.md',encoding='utf-8').read()
    for t in re.findall(r'`([^`\n]+)`',s):
        seen.setdefault(t,n)
for t,n in seen.items():
    subs=[(w,tsv[w]) for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]*",t) if w in tsv and len(w)>2]
    if subs: print(n,repr(t)[:90],'|',subs)
