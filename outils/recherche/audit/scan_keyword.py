"""Lecteurs du mot de touches du terrain (u16 a *(GOT 0x23da30)+2) : fonctions qui chargent le slot GOT 0x23da30 puis lisent un demi-mot +2 ; masques testes."""
import sys, collections
sys.path.insert(0, '/tmp/specs')
import dasm_core as d
from capstone.arm64 import *
code = d.data[:0x233960]; md = d.md; md.skipdata = True
insns = list(md.disasm(code, 0))
slot = 0x23da30
res = collections.defaultdict(list)
regs = {}; got = {}   # reg -> page ; reg -> 'clef'
cur = None
for k, ins in enumerate(insns):
    if ins.mnemonic == 'adrp': regs[ins.operands[0].reg] = ins.operands[1].imm
    elif ins.mnemonic == 'ldr' and len(ins.operands) == 2 and ins.operands[1].type == ARM64_OP_MEM and ins.operands[1].mem.base in regs and regs[ins.operands[1].mem.base] + ins.operands[1].mem.disp == slot:
        got[ins.operands[0].reg] = k
        # fenetre de 30 insns apres : ldrh [reg,#2]
        for j in range(k + 1, min(k + 40, len(insns))):
            p = insns[j]
            if p.mnemonic in ('ldrh', 'ldr', 'ldrb', 'ldrsh') and p.operands[1].type == ARM64_OP_MEM and p.operands[1].mem.base == ins.operands[0].reg:
                masks = []
                for q in insns[j + 1:j + 8]:
                    if q.mnemonic in ('tst', 'and', 'tbnz', 'tbz', 'ubfx') : masks.append(q.mnemonic + ' ' + q.op_str)
                res[(d.nom(ins.address) or '?').split('+')[0]].append('%s %s | %s' % (hex(p.address), p.op_str, '; '.join(masks[:3])))
for fn, v in sorted(res.items()):
    print(fn)
    for x in v: print('    ', x)
