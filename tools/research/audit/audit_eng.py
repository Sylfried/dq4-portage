"""Desassembleur du moteur libdq4core.so (AArch64) avec symboles (nm -D), references de donnees par adrp+add/ldr et recherche de references.
Usage : python3 audit_eng.py dis <nom-ou-adresse> [longueur-hex]      | python3 audit_eng.py xref <adresse donnee hex> | python3 audit_eng.py sym <regex>"""
import sys, struct, subprocess, re, bisect
from capstone import *
from capstone.arm64 import *
SO = '/tmp/libdq4core.so'
b = open(SO, 'rb').read()
e_phoff = struct.unpack_from('<Q', b, 0x20)[0]; e_phentsize, e_phnum = struct.unpack_from('<HH', b, 0x36)
segs = []
for i in range(e_phnum):
    t, fl, off, va, pa, fs, ms, al = struct.unpack_from('<IIQQQQQQ', b, e_phoff + i * e_phentsize)
    if t == 1: segs.append((va, off, fs, ms, fl))
def v2o(a):
    for va, off, fs, ms, fl in segs:
        if va <= a < va + fs: return off + a - va
def rd(a, n):
    o = v2o(a); return b[o:o + n] if o is not None else None
SYM = {}; NAME = {}
out = subprocess.run('nm -D --defined-only %s | c++filt' % SO, shell=True, capture_output=True, text=True).stdout
for l in out.splitlines():
    p = l.split(None, 2)
    if len(p) == 3:
        a = int(p[0], 16); SYM[a] = p[2]; NAME[p[2]] = a
ADDRS = sorted(SYM)
def symof(a):
    i = bisect.bisect_right(ADDRS, a) - 1
    if i < 0: return '?'
    return SYM[ADDRS[i]] + ('+%#x' % (a - ADDRS[i]) if a != ADDRS[i] else '')
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM); md.detail = True
# PLT : relocs JUMP_SLOT -> noms
def plt_names():
    names = {}
    txt = subprocess.run('readelf -r --wide %s 2>/dev/null' % SO, shell=True, capture_output=True, text=True).stdout
    return txt
def funcsize(a):
    i = bisect.bisect_right(ADDRS, a)
    return (ADDRS[i] - a) if i < len(ADDRS) else 0x400
def dis(a, n=None, annot=True):
    n = n or funcsize(a)
    code = rd(a, n); regs = {}; out = []
    for ins in md.disasm(code, a):
        note = ''
        mn = ins.mnemonic; ops = ins.operands
        try:
            if mn == 'adrp': regs[ops[0].reg] = ops[1].imm
            elif mn in ('add',) and len(ops) == 3 and ops[1].type == ARM64_OP_REG and ops[1].reg in regs and ops[2].type == ARM64_OP_IMM:
                x = regs[ops[1].reg] + ops[2].imm; note = '%#x %s' % (x, symof(x))
            elif any(o.type == ARM64_OP_MEM for o in ops):
                eng = [o for o in ops if o.type == ARM64_OP_MEM][0]
                if eng.mem.base in regs and not eng.mem.index:
                    x = regs[eng.mem.base] + eng.mem.disp; note = '%#x %s' % (x, symof(x))
            elif mn in ('bl', 'b') and ops[0].type == ARM64_OP_IMM:
                note = symof(ops[0].imm)
            elif mn == 'fmov' and ops[-1].type == ARM64_OP_FP: note = 'fimm %r' % ops[-1].fp
        except Exception as ex: note = '?'
        out.append('%x: %-6s %-40s %s' % (ins.address, mn, ins.op_str, ('; ' + note) if note else ''))
    return out
def xref_fast(t, window=12):
    """Balayage rapide des instructions : adrp xN, page ; (add xM, xN, #lo | ldr/str/ldrb... [xN, #off]) avec page+lo == t (cible octet exacte)."""
    hits = []
    for va, off, fs, ms, fl in segs:
        if not (fl & 1): continue
        n = fs // 4; words = struct.unpack_from('<%dI' % n, b, off)
        last = {}
        for i, w in enumerate(words):
            pc = va + 4 * i
            if (w & 0x9f000000) == 0x90000000:                      # adrp
                rd_ = w & 31; immlo = (w >> 29) & 3; immhi = (w >> 5) & 0x7ffff
                imm = ((immhi << 2) | immlo) << 12
                if imm & (1 << 32): imm -= 1 << 33
                last[rd_] = (pc & ~0xfff) + imm, i
            elif (w & 0xff800000) == 0x91000000:                    # add imm (64)
                rn = (w >> 5) & 31; imm12 = (w >> 10) & 0xfff; sh = (w >> 22) & 1
                if rn in last and i - last[rn][1] < window and last[rn][0] + (imm12 << (12 if sh else 0)) == t: hits.append((pc, 'add x%d, x%d' % (w & 31, rn)))
            elif (w & 0x3b000000) == 0x39000000:                    # ldr/str unsigned offset
                rn = (w >> 5) & 31; size = (w >> 30) & 3; imm12 = (w >> 10) & 0xfff
                if rn in last and i - last[rn][1] < window and last[rn][0] + (imm12 << size) == t: hits.append((pc, ('ldr' if (w >> 22) & 1 else 'str') + ' ... [x%d]' % rn))
    return hits
def resolve(x):
    if re.fullmatch(r'[0-9a-fA-F]+', x) and x not in NAME: return int(x, 16)
    if x in NAME: return NAME[x]
    c = [a for a, s in SYM.items() if x in s]
    if len(c) == 1: return c[0]
    if not c: raise SystemExit('not found: ' + x)
    for a in c: print('# candidat', hex(a), SYM[a])
    raise SystemExit(1)
def xref(target, lo=0x1000, hi=0x230000):
    """adrp+add/ldr/str referencant `target` (page + offset) : balayage des .text"""
    res = []
    for va, off, fs, ms, fl in segs:
        if not (fl & 1): continue
        code = b[off:off + fs]
        for ins in md.disasm(code, va):
            pass
    return res
if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'dis':
        a = resolve(sys.argv[2]); n = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
        print('# %s @ %#x' % (symof(a), a)); print('\n'.join(dis(a, n)))
    elif cmd == 'sym':
        rx = re.compile(sys.argv[2])
        for a in ADDRS:
            if rx.search(SYM[a]): print('%x %s' % (a, SYM[a]))
    elif cmd == 'xref':
        t = int(sys.argv[2], 16)
        for hit in xref_fast(t): print('%x %s  %s' % (hit[0], symof(hit[0]), hit[1]))
