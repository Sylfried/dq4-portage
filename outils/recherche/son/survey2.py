import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
mo = nouveau('s45b'); c = mo.core
mo.charger_sauvegarde(1)
for _ in range(150): mo.step(0, 0)
orig = c.export('_ZN6status9PartyData15originalPlayer_E'); party = c.export('_ZN6status7g_PartyE')
print('party+0x304', struct.unpack('<13I', c.mem(party + 0x304, 52)))
for i in range(14):
    b = c.mem(orig + PAS_JOUEUR * i, PAS_JOUEUR)
    hs = b[OFF_HS:OFF_HS + 0x30]
    print(i, 'presence', b[0x67], 'id', struct.unpack_from('<H', hs, 0)[0], 'niv', struct.unpack_from('<H', hs, 0xe)[0], 'pv', struct.unpack_from('<4H', hs, 0x22))
