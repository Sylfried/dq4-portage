"""Appels SoundManager::play*/playSe avec argument immediat : on remonte quelques instructions avant le bl pour trouver `mov w0, #imm`."""
import sys; sys.path.insert(0, '/tmp/specs')
import disasm_engine as D, xref as X
from capstone import *
from capstone.arm64 import *
targets = {'playSe': '_ZN12SoundManager6playSeEi', 'playBgm': '_ZN12SoundManager7playBgmEi', 'play': '_ZN12SoundManager4playEi', 'playStart': '_ZN12SoundManager9playStartEi', 'playRestart': '_ZN12SoundManager11playRestartEi'}
addr = {}
for k, v in D.syms.items():
    pass
import subprocess, re
nm = subprocess.run("nm -D --defined-only %s" % D.SO, shell=True, capture_output=True, text=True).stdout
ad = {}
for l in nm.splitlines():
    m = re.match(r'([0-9a-f]+) \w (.*)', l)
    if m: ad[m.group(2)] = int(m.group(1), 16)
for name_str, mg in targets.items():
    t = ad[mg]
    for a in X.callers(t):
        # remonter jusqu'a 6 instructions : mov w0, #imm
        code = D.rd(a - 24, 28); imm = None
        for ins in D.md.disasm(code, a - 24):
            if ins.address >= a: break
            if ins.mnemonic in ('mov', 'movz') and len(ins.operands) == 2 and ins.operands[0].type == ARM64_OP_REG and ins.operands[0].reg == ARM64_REG_W0 and ins.operands[1].type == ARM64_OP_IMM: imm = ins.operands[1].imm
            if ins.mnemonic in ('bl', 'b'): imm = None
        print('%s %s %s imm=%s' % (name_str, hex(a), D.symname(a), imm))
