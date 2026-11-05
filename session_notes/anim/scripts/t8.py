"""Noms des actions : on force des actions alliees dans un vrai combat et on journalise TextAPI::getMessage (identifiant -> texte rendu)."""
import sys, time, json, struct, unicorn
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
eng = bp.boot(); rec = bp.Rec(eng); c = eng.core
log = []
a = c.export('_Z26macro_processMessage_allocPKc')
pend = {}
rets = set()
def ret_hook(uc, adr, sz, ud):
    p = uc.reg_read(c.XREG[0]) & 0xffffffffffff
    try:
        raw = c.mem(p, 0x200); n = raw.find(b'\0'); seen[len(seen)] = raw[:n].decode('utf-8', 'replace')
    except Exception as ex: pass
def enter(uc, adr, sz, ud):
    lr = uc.reg_read(c.XREG[30]) & 0xffffffffffff
    if lr not in rets:
        rets.add(lr); uc.hook_add(unicorn.UC_HOOK_CODE, ret_hook, None, lr, lr); uc.ctl_flush_tb()
c.uc.hook_add(unicorn.UC_HOOK_CODE, enter, None, a, a); c.uc.ctl_flush_tb()
queue = []
# lecture du texte apres l'appel : on lit a l'entree de l'appel suivant (cf. boucle ci-dessous)
print('natural', bp.natural_battle(eng), flush=True)
for i in range(120): eng.step(0, 0)
g = c.export('_ZN6status9g_MonsterE')
import struct
for (i, num, grp) in bp.monsters(eng):
    c.mem_w(g + 8 + 0x538 * i + 0x58 + 0x22, struct.pack('<HH', 9999, 9999))
acts = [int(x) for x in sys.argv[2:]]
fo = bp.Forcer(eng, acts); bp.make_strong(eng)
seen = {}
def tick(eng_, pkt):
    pass
pend_log = []
out, pl = bp.run(eng, frames=2500, log=tick, stop_when=lambda e: len(rec.execs) >= len(acts) and e.frames > rec.execs[-1][0] + 150)
print('forced', fo.done)
print('effects', rec.effects)
json.dump(seen, open(sys.argv[1], 'w'), ensure_ascii=False)
