"""Type Unity k (1..80) = objet MenuItem global au slot GOT 0x23d4f8 + 8k (cf. MenuItem::SystemInit). Utilisateurs = fonctions du moteur qui chargent ce slot."""
import sys, collections, re; sys.path.insert(0,'/tmp/specs')
import dasm_core as d
from capstone.arm64 import *
code = d.data[:0x233960]
md = d.md; md.skipdata=True
insns = list(md.disasm(code,0))
slot2t = {0x23d4f8 + 8*k: k for k in range(1, 81)}
regs = {}
res = collections.defaultdict(collections.Counter)
for ins in insns:
    if ins.mnemonic == 'adrp': regs[ins.operands[0].reg] = ins.operands[1].imm
    elif ins.mnemonic == 'ldr' and len(ins.operands)==2 and ins.operands[1].type==ARM64_OP_MEM and ins.operands[1].mem.base in regs:
        s = regs[ins.operands[1].mem.base] + ins.operands[1].mem.disp
        if s in slot2t:
            fn=(d.nom(ins.address) or '?').split('+')[0]
            res[slot2t[s]][fn]+=1
def classe(fn):
    m = re.match(r'([A-Za-z_0-9]+)::', fn)
    return m.group(1) if m else fn
for t in sorted(res):
    cl = collections.Counter()
    for fn,n in res[t].items(): cl[classe(fn)] += n
    print(t, '; '.join('%s(%d)' % (c,n) for c,n in sorted(cl.items())))
