import sys, pickle
sys.path.insert(0,'.')
from mpt import *
files=load()
texts=[]   # (file_base, entry_id, bytes)
bad=0
for base,d in sorted(files.items()):
    i0,i1,n,toff,xoff,xsize,ents=parse(d)
    tb=toff+xoff
    for (eid,ln,off) in ents:
        raw=d[tb+off*4:tb+off*4+ln]
        texts.append((base,eid,raw))
pickle.dump(texts,open('texts.pkl','wb'))
print(len(texts))
n=0
for base,eid,raw in texts:
    try: s=raw.decode('utf-8')
    except Exception: bad+=1; continue
    if 'Ouaf' in s or 'ouaf' in s:
        n+=1
        print(base,eid,repr(s)); print([hex(ord(c)) for c in s if not (c.isascii() and c.isalnum())])
print('bad',bad,'n',n)
