import re,sys
tbl={}
for l in open('/home/claude/dq4-portage/docs/rename_identifiers.tsv',encoding='utf-8').read().split('\n')[1:]:
    p=l.split('\t')
    if len(p)==2: tbl[p[0]]=p[1]
for f in sys.argv[1:]:
    s=open(f,encoding='utf-8').read()
    out=set()
    for m in re.finditer(r'[A-Za-z_][A-Za-z0-9_]*',s):
        t=m.group(0)
        if t not in tbl: continue
        nxt=s[m.end():m.end()+1]; prv=s[m.start()-1:m.start()]
        if '_' in t or (t.isupper() and len(t)>2) or nxt=='(' or prv=='`' or prv=='.':
            out.add((t,tbl[t]))
    print(f.split('.md.')[1][:3], sorted(out))
