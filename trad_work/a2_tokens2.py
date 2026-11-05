import re,glob
tsv={}
for l in open('/home/claude/dq4-portage/docs/rename_identifiers.tsv',encoding='utf-8').read().split('\n')[1:]:
    if '\t' in l:
        a,b=l.split('\t',1); tsv[a]=b
mine=[f'docs/docs__archives__agent-reports-40-44.md.{n}.in.md' for n in ('006','007','008','009','010')]
from collections import defaultdict
where=defaultdict(list)
for f in mine:
    for i,line in enumerate(open(f,encoding='utf-8').read().split('\n'),1):
        for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*",line):
            if t in tsv and ('_' in t or re.search(r'[a-z][A-Z]',t) or (t[0].isupper() and t not in ('Il','Un','Une','Le','La','Les','Des','Dans','Autres','Non','Avant','Apres','Nouveau','Fait','Tous','Toutes','Tout'))):
                where[t].append((f[-9:-6],i))
for t,v in sorted(where.items()):
    print(t,'->',tsv[t],len(v),v[:6])
