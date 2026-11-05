import re,sys
tsv={}
for l in open('/home/claude/dq4-portage/docs/rename_identifiers.tsv',encoding='utf-8').read().split('\n')[1:]:
    if '\t' in l:
        a,b=l.split('\t',1); tsv[a]=b
FILEMAP={'fenetre.py':'window.py','reglages.py':'settings.py','moteur.py':'engine.py','donnees.py':'data.py','avant_partie.py':'pre_game.py','ecran_sauvegardes.py':'saves_screen.py','saisie_nom.py':'name_entry.py','entrees.py':'inputs.py','objets_carte.py':'map_objects.py','reglages.json':'settings.json'}
a=open(sys.argv[1],encoding='utf-8').read(); b=open(sys.argv[2],encoding='utf-8').read()
def norm(s): return re.sub(r'(\d),(\d)', r'\1.\2', s)
TOK = re.compile(r"0x[0-9A-Fa-f]+|\d+(?:[.,]\d+)?|[A-Za-z]+_[A-Za-z0-9_]+|[a-z]+[A-Z][A-Za-z0-9]*|#\d+|D-\d+|[A-Z]+-\d+|`[^`\n]+`")
nb=norm(b)
miss=[t for t in TOK.findall(norm(a)) if t not in nb]
unexp=[]
for t in miss:
    def sub(m):
        w=m.group(0)
        return tsv.get(w,w)
    t2=re.sub(r"[A-Za-z_][A-Za-z0-9_]*",sub,t)
    for o,n in FILEMAP.items(): t2=t2.replace(o,n)
    if t2 in nb: continue
    unexp.append((t,t2))
for t,t2 in unexp: print('UNEXPLAINED',repr(t),'->',repr(t2))
print(len(miss),'missing;',len(unexp),'unexplained')
