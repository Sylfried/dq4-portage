import re,sys
tbl={}
for l in open('/home/claude/dq4-portage/docs/rename_identifiers.tsv',encoding='utf-8').read().split('\n')[1:]:
    p=l.split('\t')
    if len(p)==2: tbl[p[0]]=p[1]
rn=open('/home/claude/dq4-portage/docs/rename_map.md',encoding='utf-8').read()
a=open(sys.argv[1],encoding='utf-8').read(); b=open(sys.argv[2],encoding='utf-8').read()
TOK = re.compile(r"0x[0-9A-Fa-f]+|\d+(?:[.,]\d+)?|[A-Za-z]+_[A-Za-z0-9_]+|[a-z]+[A-Z][A-Za-z0-9]*|#\d+|D-\d+|[A-Z]+-\d+|`[^`\n]+`")
def norm(s): return re.sub(r'(\d),(\d)', r'\1.\2', s)
nb=norm(b)
miss=[t for t in TOK.findall(norm(a)) if t not in nb]
other=[]; ren=[]
for t in miss:
    parts=re.findall(r'[A-Za-z_][A-Za-z0-9_]*',t)
    if parts and all((p in tbl) or ('`'+p+'`' in rn) or (p+'.py' in rn) for p in parts) or any(p in tbl for p in parts) or ('`'+t.strip('`')+'`' in rn):
        ren.append(t)
    else: other.append(t)
print('NON-RENAME LOST:', other)
print('rename-explained:', len(ren))
