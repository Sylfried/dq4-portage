"""Type Unity (MenuPort [N,1,cat,type]) -> fonctions du moteur : on cherche `mov wA, #imm ; strh wA, [xB, #0x60]` (champ « type » lu par MenuItem::setup/Setup2/OpenItem -> MenuPort::Open(this, cat, [this+0x60]))"""
import sys, collections; sys.path.insert(0,'/tmp/specs')
import dasm_core as d
from capstone.arm64 import *
code = d.data[:0x233960]
md = d.md; md.skipdata=True
insns = list(md.disasm(code,0))
res = collections.defaultdict(set)
for k,ins in enumerate(insns):
    if ins.mnemonic == 'strh' and ins.operands[1].type==ARM64_OP_MEM and ins.operands[1].mem.disp==0x60 and ins.operands[0].type==ARM64_OP_REG:
        r = ins.operands[0].reg
        if md.reg_name(r) in ('wzr',): continue
        imm=None
        for j in range(k-1, max(k-12,0), -1):
            p=insns[j]
            if p.mnemonic in ('mov','movz') and p.operands[0].type==ARM64_OP_REG and p.operands[0].reg==r and p.operands[1].type==ARM64_OP_IMM:
                imm=p.operands[1].imm; break
        if imm is not None:
            fn=(d.nom(ins.address) or '?').split('+')[0]
            res[imm].add(fn)
for t in sorted(res): print(t, '; '.join(sorted(res[t])))
