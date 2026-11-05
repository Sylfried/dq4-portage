"""Inventaire : type de fenetre MenuPort (MENUITEM_TYPE) -> fonctions du moteur qui l'ouvrent (appels a MenuItem::setup / Setup2 avec un immediat dans w1)."""
import sys, collections; sys.path.insert(0,'/tmp/specs')
import dasm_core as d
from capstone.arm64 import *
code = d.data[:0x233960]
md = d.md; md.skipdata=True
insns = list(md.disasm(code,0))
tg = {}
for a,n in d.PLT.items():
    if n.startswith('_ZN8MenuItem5setupE') or n.startswith('_ZN8MenuItem6Setup2E') or n.startswith('_ZN8MenuItem5SetupE'): tg[a]=n
for a,n in d.syms.items():
    if n.startswith('MenuItem::setup(') or n.startswith('MenuItem::Setup2('): tg[a]=n
print('targets', {hex(a):n for a,n in tg.items()}, file=sys.stderr)
res = collections.defaultdict(set)
unk = []
for k,ins in enumerate(insns):
    if ins.mnemonic in ('bl','b') and ins.operands and ins.operands[0].type==ARM64_OP_IMM and ins.operands[0].imm in tg:
        imm=None
        for j in range(k-1, max(k-16,0), -1):
            p=insns[j]
            if p.mnemonic in ('mov','movz') and p.operands[0].type==ARM64_OP_REG and md.reg_name(p.operands[0].reg) in ('w1','x1'):
                imm = p.operands[1].imm if p.operands[1].type==ARM64_OP_IMM else 'reg'; break
            if p.mnemonic in ('bl','blr','ret'): break
        fn=(d.name_str(ins.address) or '?').split('+')[0]
        if isinstance(imm,int): res[imm].add(fn)
        else: unk.append((fn, hex(ins.address)))
for t in sorted(res): print(t, '; '.join(sorted(res[t])))
print('UNRESOLVED', unk)
