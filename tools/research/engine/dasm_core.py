"""Desassemble libdq4core.so (ARM64) : python3 dasm_core.py <adresse|symbole> [taille_octets]  ; annotations par symboles exportes."""
import sys, re, subprocess, bisect
from capstone import *
from capstone.arm64 import *
SO = '/tmp/r3_apk/lib/arm64-v8a/libdq4core.so'
data = open(SO, 'rb').read()
import struct
e_phoff = struct.unpack_from('<Q', data, 0x20)[0]; e_phentsize, e_phnum = struct.unpack_from('<HH', data, 0x36)
segs = []
for i in range(e_phnum):
    p_type, p_flags, p_off, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack_from('<IIQQQQQQ', data, e_phoff + i * e_phentsize)
    if p_type == 1: segs.append((p_vaddr, p_off, p_filesz))
def rd(va, n):
    for v, o, s in segs:
        if v <= va < v + s: return data[o + va - v:o + va - v + n]
    return None
syms = {}
for l in open('/tmp/r3_syms.txt'):
    p = l.rstrip('\n').split(' ', 2)
    if len(p) == 3 and p[1] in 'TtWw': syms[int(p[0], 16)] = p[2]
# PLT : noms via relocations
plt = {}
try:
    out = subprocess.run(['objdump', '-d', '-j', '.plt', SO], capture_output=True, text=True).stdout
except Exception: out = ''
ks = sorted(syms)
def name_str(a):
    i = bisect.bisect_right(ks, a) - 1
    if i >= 0 and a - ks[i] < 0x2000: return '%s+%#x' % (syms[ks[i]], a - ks[i]) if a != ks[i] else syms[ks[i]]
    return None
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM); md.detail = True
def dis(a, n):
    out = []
    regs = {}
    for ins in md.disasm(rd(a, n), a):
        note = ''
        if ins.mnemonic in ('bl', 'b') and ins.operands[0].type == ARM64_OP_IMM:
            note = name_str(ins.operands[0].imm) or ''
        elif ins.mnemonic == 'adrp': regs[ins.operands[0].reg] = ins.operands[1].imm
        elif ins.mnemonic == 'add' and len(ins.operands) == 3 and ins.operands[2].type == ARM64_OP_IMM and ins.operands[1].type == ARM64_OP_REG and ins.operands[1].reg in regs:
            note = '@%#x' % (regs[ins.operands[1].reg] + ins.operands[2].imm)
        elif ins.mnemonic in ('ldr', 'ldrb', 'ldrh', 'ldrsh', 'ldrsb') and ins.operands[1].type == ARM64_OP_MEM and ins.operands[1].mem.base in regs:
            note = '@%#x' % (regs[ins.operands[1].mem.base] + ins.operands[1].mem.disp)
        out.append('%x: %-6s %-34s %s' % (ins.address, ins.mnemonic, ins.op_str, ('; ' + note) if note else ''))
    return out
if __name__ == '__main__':
    a = sys.argv[1]
    if not a.startswith('0x'):
        c = [k for k, v in syms.items() if a in v]
        if not c: raise SystemExit('symbole introuvable')
        print([ (hex(k), syms[k]) for k in c][:10]); a = hex(c[0])
    a = int(a, 16); n = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x100
    print('\n'.join(dis(a, n)))

# --- noms des stubs PLT (adrp x16 / ldr x17, [x16, #off] -> adresse GOT -> symbole d'importation ou local)
def _plt_names():
    got = {}
    out = subprocess.run(['readelf', '-rW', SO], capture_output=True, text=True).stdout
    for l in out.splitlines():
        p = l.split()
        if len(p) >= 5 and p[2].startswith('R_AARCH64_JUMP_SLOT'):
            got[int(p[0], 16)] = p[4] if len(p) > 4 else '?'
        elif len(p) >= 4 and p[2].startswith('R_AARCH64_JUMP_SLOT'):
            got[int(p[0], 16)] = '?'
    res = {}
    # section .plt
    sh = subprocess.run(['readelf', '-SW', SO], capture_output=True, text=True).stdout
    m = re.search(r'\.plt\s+PROGBITS\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)', sh)
    if not m: return res
    base = int(m.group(1), 16); size = int(m.group(3), 16)
    code = rd(base, size)
    for ins in md.disasm(code, base):
        if ins.mnemonic == 'adrp' and ins.operands[0].reg == ARM64_REG_X16: pg = ins.operands[1].imm; start = ins.address
        elif ins.mnemonic == 'ldr' and ins.operands[0].reg == ARM64_REG_X17 and ins.operands[1].type == ARM64_OP_MEM:
            ga = pg + ins.operands[1].mem.disp
            res[start] = got.get(ga, '?')
    return res
PLT = _plt_names()
_old_name = name_str
def name_str(a):
    if a in PLT: return 'plt:' + PLT[a]
    return _old_name(a)
