#!/usr/bin/env python3
"""Desassemblage ARM64 de libdq4core.so annote (symboles C++ demanglés, chaines, appels PLT).
Usage : desasm_moteur.py <nom_ou_adresse_hex> [longueur_octets|fin_hex]   (adresses = vaddr de la lib, pas de base)
        desasm_moteur.py -f <sous-chaine du symbole>        (liste les symboles)
"""
import sys, struct, subprocess, re, bisect, os
from capstone import *
from capstone.arm64 import *
SO = os.environ.get('DQ_SO', '/tmp/libdq4core.so')
data = open(SO, 'rb').read()
e_phoff = struct.unpack_from('<Q', data, 0x20)[0]; e_phentsize, e_phnum = struct.unpack_from('<HH', data, 0x36)
segs = []; dyn = None
for i in range(e_phnum):
    t, fl, off, va, pa, fsz, msz, al = struct.unpack_from('<IIQQQQQQ', data, e_phoff + i * e_phentsize)
    if t == 1: segs.append((va, off, fsz, msz))
    if t == 2: dyn = (va, off, fsz)
def v2o(va):
    for v, o, s, m in segs:
        if v <= va < v + s: return o + va - v
    return None
def rd(va, n):
    o = v2o(va)
    return data[o:o + n] if o is not None else None
def cstr(va, lim=120):
    o = v2o(va)
    if o is None: return None
    e = data.find(b'\0', o, o + lim)
    s = data[o:e if e >= 0 else o + lim]
    try: return s.decode('utf-8')
    except Exception: return None
# symboles
_out = subprocess.run("nm -D --defined-only %s | c++filt" % SO, shell=True, capture_output=True, text=True).stdout
syms = {}
for l in _out.splitlines():
    m = re.match(r'([0-9a-f]+) (\w) (.*)', l)
    if m: syms.setdefault(int(m.group(1), 16), m.group(3))
starts = sorted(syms)
def symname(a):
    i = bisect.bisect_right(starts, a) - 1
    if i < 0: return None
    return '%s+%#x' % (syms[starts[i]], a - starts[i]) if a != starts[i] else syms[starts[i]]
# relocations (GLOB_DAT / JUMP_SLOT) -> noms
import struct as S
dynd = {}
p = dyn[1]
while True:
    tag, val = S.unpack_from('<qQ', data, p); p += 16
    if tag == 0: break
    dynd.setdefault(tag, []).append(val)
symtab, strtab = dynd[6][0], dynd[5][0]
def _str(off):
    o = v2o(strtab) + off; return data[o:data.index(b'\0', o)].decode()
def symi(i):
    st_name, = S.unpack_from('<I', data, v2o(symtab) + 24 * i); return _str(st_name)
got = {}; rel = {}
for tagA, tagS in ((7, 8), (23, 2)):
    if tagA in dynd:
        off = v2o(dynd[tagA][0]); n = dynd[tagS][0] // 24
        for i in range(n):
            r_off, r_info, r_add = S.unpack_from('<QQq', data, off + 24 * i)
            t, si = r_info & 0xffffffff, r_info >> 32
            if t in (1025, 1026, 257) and si: got[r_off] = symi(si)
            elif t == 1027: rel[r_off] = r_add
# PLT stubs : adrp x16,page ; ldr x17,[x16,off] ; add ; br x17
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM); md.detail = True
plt = {}
def scan_plt():
    # cherche les stubs dans la section executable, par motif
    for va, off, fsz, msz in segs:
        pass
def plt_target(a):
    b = rd(a, 16)
    if not b or len(b) < 16: return None
    ins = list(md.disasm(b, a))
    if len(ins) >= 3 and ins[0].mnemonic == 'adrp' and ins[1].mnemonic == 'ldr' and ins[2].mnemonic == 'add':
        pg = ins[0].operands[1].imm; d = ins[1].operands[1].mem.disp
        return got.get(pg + d)
    return None
def is_text(a): return a in syms
def annot(ins, regs):
    note = ''
    if ins.mnemonic == 'adrp': regs[ins.operands[0].reg] = ins.operands[1].imm
    elif ins.mnemonic == 'add' and len(ins.operands) == 3 and ins.operands[1].type == ARM64_OP_REG and ins.operands[1].reg in regs and ins.operands[2].type == ARM64_OP_IMM:
        a = regs[ins.operands[1].reg] + ins.operands[2].imm; regs[ins.operands[0].reg] = a
        s = cstr(a); n = symname(a)
        note = ('@%#x ' % a) + (repr(s) if s and len(s) > 2 and s.isprintable() else '') + (' <%s>' % n if n else '')
    elif ins.mnemonic in ('ldr', 'ldrb', 'ldrh', 'ldrsw', 'str', 'strb', 'strh') and len(ins.operands) >= 2 and ins.operands[1].type == ARM64_OP_MEM:
        mem = ins.operands[1].mem
        if mem.base in regs:
            a = regs[mem.base] + mem.disp
            g = got.get(a); n = symname(a)
            note = '@%#x' % a + (' GOT:%s' % g if g else '') + (' <%s>' % n if n else '')
            if ins.mnemonic == 'ldr' and ins.operands[0].reg_name if hasattr(ins.operands[0], 'reg_name') else False: pass
    elif ins.mnemonic in ('bl', 'b') and ins.operands[0].type == ARM64_OP_IMM:
        a = ins.operands[0].imm; n = syms.get(a) or plt_target(a) or symname(a)
        note = n or 'sub_%x' % a
    return note
def dis(start, end):
    code = rd(start, end - start); regs = {}; out = []
    for ins in md.disasm(code, start):
        note = annot(ins, regs)
        out.append('%x: %-7s %-34s %s' % (ins.address, ins.mnemonic, ins.op_str, ('; ' + note) if note else ''))
    return out
def func_range(a):
    i = bisect.bisect_right(starts, a) - 1
    s = starts[i]; e = starts[i + 1] if i + 1 < len(starts) else s + 0x400
    return s, e
if __name__ == '__main__':
    if sys.argv[1] == '-f':
        for a in starts:
            if sys.argv[2].lower() in syms[a].lower(): print('%x %s' % (a, syms[a]))
        sys.exit()
    arg = sys.argv[1]
    try: a = int(arg, 16)
    except ValueError:
        c = [x for x in starts if arg in syms[x]]
        if not c: sys.exit('introuvable'); 
        a = c[0]
        if len(c) > 1: print('# plusieurs :', [(hex(x), syms[x]) for x in c][:8], file=sys.stderr)
    if len(sys.argv) > 2:
        v = int(sys.argv[2], 16); end = a + v if v < 0x100000 else v
    else: end = func_range(a)[1]
    print('# %s' % symname(a))
    print('\n'.join(dis(a, end)))
