import sys, os, struct, tempfile
sys.path.insert(0, '/home/claude/wt45-combat/dq4_pc'); os.chdir('/home/claude/wt45-combat/dq4_pc')
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'; SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'
for slot in (1, 2, 3, 4, 5):
    eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_cb_'))
    for _ in range(3): eng.step(0, 0)
    ok = eng.load_save(slot)
    for i in range(150): eng.step(0, 0)
    c = eng.core
    orig = c.export('_ZN6status9PartyData15originalPlayer_E'); party = c.export('_ZN6status7g_PartyE')
    mem = [i for i in struct.unpack('<13I', c.mem(party + 0x304, 13 * 4))]
    out = []
    for i in mem:
        if i:
            hs = orig + 0x530 * i + 0x58; h = c.mem(hs, 0x30)
            out.append((i, h[0xe], struct.unpack_from('<4H', h, 0x22)))
    print(slot, ok, eng.state.game_map, hex(eng.state.part), out, flush=True)
