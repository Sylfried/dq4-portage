"""Acces au code machine de libil2cpp.so (segments, adresses -> noms) et desassemblage (capstone, facultatif : sert seulement a l'analyse manuelle)."""
import sys, json, struct, re, os
try:
    from capstone import *
    from capstone.arm64 import *
except ImportError:
    Cs = None
BASE = os.environ.get('DQ_IL2', '.')          # dossier contenant libil2cpp.so, script.json, dump.cs
_so = [p for p in (os.path.join(BASE, 'libil2cpp.so'), os.path.join(BASE, 'entrees', 'libil2cpp.so')) if os.path.exists(p)]
if not _so: raise SystemExit('libil2cpp.so introuvable dans ' + BASE + ' (lance outils\\dump_il2cpp.bat)')
so = open(_so[0], 'rb').read()
# segments PT_LOAD
e_phoff = struct.unpack_from('<Q', so, 0x20)[0]; e_phentsize, e_phnum = struct.unpack_from('<HH', so, 0x36)
segs = []
for i in range(e_phnum):
    p_type, p_flags, p_off, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack_from('<IIQQQQQQ', so, e_phoff + i*e_phentsize)
    if p_type == 1: segs.append((p_vaddr, p_off, p_filesz))
def v2o(va):
    for v, o, s in segs:
        if v <= va < v + s: return o + va - v
    return None
def rd(va, n):
    o = v2o(va); return so[o:o+n] if o is not None else None
D = json.load(open(os.path.join(BASE, 'script.json'), encoding='utf-8'))
names = {}
for m in D['ScriptMethod']: names[m['Address']] = m['Name']
data = {}
for m in D['ScriptMetadata']: data[m['Address']] = m['Name']
for m in D['ScriptMetadataMethod']: data[m['Address']] = m['Name']
for m in D['ScriptString']: data[m['Address']] = 'STR:' + repr(m['Value'][:60])
# noms depuis dump.cs (RVA -> Classe.methode)
cls = None
for l in open(os.path.join(BASE, 'dump.cs'), encoding='utf-8', errors='replace'):
    mm = re.match(r'^(?:public |private |internal |protected )?(?:static |sealed |abstract )*(?:class|struct|enum|interface) (\S+)', l)
    if mm: cls = mm.group(1); continue
    mm = re.match(r'\t// RVA: 0x([0-9A-F]+) Offset', l)
    if mm: pend = int(mm.group(1), 16); continue
    if l.startswith('\t') and 'pend' in globals() and pend is not None and '(' in l and not l.strip().startswith('//'):
        nm = re.search(r'(\S+)\(', l)
        if nm and pend not in names: names[pend] = '%s.%s' % (cls, nm.group(1))
        pend = None
md = None
if Cs is not None: md = Cs(CS_ARCH_ARM64, CS_MODE_ARM); md.detail = True
def dis(start, end, show=True):
    code = rd(start, end - start); regs = {}; out = []
    for ins in md.disasm(code, start):
        note = ''
        if ins.mnemonic == 'adrp':
            regs[ins.operands[0].reg] = ins.operands[1].imm
        elif ins.mnemonic in ('ldr', 'ldrsw', 'ldur') and len(ins.operands) >= 2 and ins.operands[1].type == ARM64_OP_MEM:
            mem = ins.operands[1].mem
            if mem.base in regs:
                a = regs[mem.base] + mem.disp
                if a in data: note = data[a]
                else:
                    b = rd(a, 8)
                    if b and ins.reg_name(ins.operands[0].reg)[0] in 'sd':
                        note = 'const %s' % (struct.unpack('<f', b[:4])[0] if ins.reg_name(ins.operands[0].reg)[0] == 's' else struct.unpack('<d', b)[0])
                    else: note = '@%#x' % a
        elif ins.mnemonic == 'ldr' and ins.operands[-1].type == ARM64_OP_IMM:     # litteral
            a = ins.operands[-1].imm; b = rd(a, 8)
            if b: note = 'const %s' % (struct.unpack('<f', b[:4])[0] if ins.reg_name(ins.operands[0].reg)[0] == 's' else struct.unpack('<d', b)[0] if ins.reg_name(ins.operands[0].reg)[0] == 'd' else b.hex())
        elif ins.mnemonic == 'add' and len(ins.operands) == 3 and ins.operands[1].type == ARM64_OP_REG and ins.operands[1].reg in regs and ins.operands[2].type == ARM64_OP_IMM:
            a = regs[ins.operands[1].reg] + ins.operands[2].imm
            note = data.get(a, '@%#x' % a)
        elif ins.mnemonic in ('bl', 'b') and ins.operands[0].type == ARM64_OP_IMM:
            a = ins.operands[0].imm; note = names.get(a, 'sub_%x' % a)
        out.append('%x: %-6s %-36s %s' % (ins.address, ins.mnemonic, ins.op_str, ('; ' + note) if note else ''))
    return out
if __name__ == '__main__':
    s = int(sys.argv[1], 16); e = int(sys.argv[2], 16)
    print('\n'.join(dis(s, e)))
