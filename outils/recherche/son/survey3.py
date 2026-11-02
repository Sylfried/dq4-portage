import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
mo = nouveau('s45c'); c = mo.core
mo.charger_sauvegarde(1)
for _ in range(150): mo.step(0, 0)
party = c.export('_ZN6status7g_PartyE')
print([hex(x) for x in struct.unpack('<28I', c.mem(party + 0x2d0, 28*4))])
for n in ('_ZN6status9PartyData9addMemberEi', '_ZN6status9PartyData11setupMemberEi'):
    print(n, c.export(n))
