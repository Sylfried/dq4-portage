import sys; sys.path.insert(0,'/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/textpos')
from tp_lib import *
from tp_strings import load_slots
S = load_slots()
tot=0; have=0; miss=collections.Counter() if False else {}
import collections
miss=collections.defaultdict(list)
for t in sorted(ml.types, key=int):
    ty=int(t)
    for i,no,nid,var in text_cells(ty):
        tot+=1
        k='%d/%d/%d'%(ty,i,no)
        if S.get(k): have+=1
        else: miss[ty].append((i,no))
print(tot,have)
for k,v in miss.items(): print(k, v)
bad=[(k,len(v)) for k,v in S.items() if any('\r' in s for s in v)]
print('with CR', bad)
nb=[(k,[s for s in v if ' ' in s][:2]) for k,v in S.items() if any(' ' in s for s in v)]
print('with NBSP', nb[:30])
