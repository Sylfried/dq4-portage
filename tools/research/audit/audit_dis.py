"""Desassembleur annote de libil2cpp.so pour l'audit menus / croix.
Usage : DQ_IL2=/home/claude/il2 python3 audit_dis.py <RVA debut hex> [<RVA fin hex> | +<longueur>]   (ou -n NomClasse.methode)
Annote : appels (noms ScriptMethod), emplacements TypeInfo / MethodInfo / chaines (par relocation R_AARCH64_RELATIVE),
constantes flottantes (ldr s/d depuis un litteral ou une page), offsets de champs (via dump.cs : champ de la classe courante)."""
import sys, os, struct, re
sys.path.insert(0, '/home/claude/dq4-portage/tools/ui_il2cpp')
os.environ.setdefault('DQ_IL2', '/home/claude/il2')
import disasm as d
import reloc as rl
from capstone.arm64 import *

def res_slot(a):
    r = rl.R.get(a)
    if r is None: return None
    s = rl.S.get(r); m = rl.M.get(r)
    return ('STR:' + repr(s[:70])) if s is not None else (m if m else '@%#x' % r)

def f32(b): return struct.unpack('<f', b[:4])[0]

def dis(start, end, annot=True):
    code = d.rd(start, end - start); regs = {}; out = []
    for ins in d.md.disasm(code, start):
        note = ''
        mn = ins.mnemonic; ops = ins.operands
        try:
            if mn == 'adrp':
                regs[ops[0].reg] = ops[1].imm
            elif mn in ('ldr', 'ldrsw', 'ldur', 'ldrb', 'ldrh', 'ldp') and len(ops) >= 2 and ops[1].type == ARM64_OP_MEM:
                mem = ops[1].mem
                if mem.base in regs:
                    a = regs[mem.base] + mem.disp
                    nm = ins.reg_name(ops[0].reg)
                    if mn == 'ldr' and nm[0] in 'sd':
                        b = d.rd(a, 8)
                        note = 'const %r' % (f32(b) if nm[0] == 's' else struct.unpack('<d', b)[0]) if b else ''
                    else:
                        note = res_slot(a) or ('@%#x' % a)
            elif mn == 'ldr' and ops[-1].type == ARM64_OP_IMM:
                a = ops[-1].imm; b = d.rd(a, 8); nm = ins.reg_name(ops[0].reg)
                if b: note = 'lit %r' % (f32(b) if nm[0] == 's' else struct.unpack('<d', b)[0] if nm[0] == 'd' else b.hex())
            elif mn == 'add' and len(ops) == 3 and ops[1].type == ARM64_OP_REG and ops[1].reg in regs and ops[2].type == ARM64_OP_IMM:
                a = regs[ops[1].reg] + ops[2].imm
                note = res_slot(a) or ('@%#x' % a)
            elif mn in ('bl', 'b') and ops[0].type == ARM64_OP_IMM:
                a = ops[0].imm; note = d.names.get(a, 'sub_%x' % a)
            elif mn == 'fmov' and ops[-1].type == ARM64_OP_FP:
                note = 'fimm %r' % ops[-1].fp
        except Exception as e:
            note = '?' + str(e)
        out.append('%x: %-6s %-38s %s' % (ins.address, mn, ins.op_str, ('; ' + note) if note else ''))
    return out

def find(name):
    r = [a for a, n in d.names.items() if n == name]
    return r

if __name__ == '__main__':
    args = sys.argv[1:]
    if args[0] == '-n':
        for a in find(args[1]): print('# %s @ %#x' % (args[1], a))
        a = find(args[1])[0]; s = a
        # fin = prochaine methode connue
        nxt = sorted(x for x in d.names if x > a)[0]
        e = nxt
    else:
        s = int(args[0], 16)
        e = int(args[1], 16) if len(args) > 1 and not args[1].startswith('+') else s + int(args[1][1:], 16) if len(args) > 1 else s + 0x200
    print('\n'.join(dis(s, e)))


# ---------------------------------------------------------------- annotation des champs (instance / statiques) d'une classe de dump.cs
def class_fields(klass_name):
    """-> (instance{offset:nom}, statique{offset:nom}) lus dans dump.cs (section Fields de la classe)."""
    inst, stat = {}, {}
    entry = False
    for l in open(os.path.join(d.BASE, 'dump.cs'), encoding='utf-8', errors='replace'):
        m = re.match(r'^(?:public |private |internal |protected )?(?:static |sealed |abstract )*(?:class|struct|enum|interface) (\S+)', l)
        if m: entry = (m.group(1) == klass_name); continue
        if not entry: continue
        if l.startswith('\t// Properties') or l.startswith('\t// Methods'): break
        m = re.match(r'\t(?:\[.*\] )?((?:public|private|protected|internal)[^;]*?) (\S+); // 0x([0-9A-F]+)', l)
        if m:
            decl, nm, off = m.group(1), m.group(2), int(m.group(3), 16)
            (stat if ' static ' in (' ' + decl + ' ') else inst)[off] = nm
    return inst, stat

def dis_fields(start, end, cls, this_regs=('x19',), verbose=True):
    """Comme dis(), mais annote [reg,#off] : statiques de `cls` quand reg vient de [TypeInfo+0xb8], champs d'instance quand reg est dans this_regs (ou x0 au debut)."""
    inst, stat = class_fields(cls)
    code = d.rd(start, end - start); regs = {}; kind = {}; out = []
    for r in this_regs: kind[r] = 'this'
    kind['x0'] = 'this'
    for ins in d.md.disasm(code, start):
        mn = ins.mnemonic; ops = ins.operands; note = ''
        rn = lambda o: ins.reg_name(o.reg)
        try:
            if mn == 'adrp': regs[ops[0].reg] = ops[1].imm
            elif mn in ('ldr', 'ldrb', 'ldrh', 'ldrsw', 'ldur', 'ldp', 'str', 'strb', 'strh', 'stur', 'stp') and any(o.type == ARM64_OP_MEM for o in ops):
                eng = [o for o in ops if o.type == ARM64_OP_MEM][0]; mem = eng.mem; base = ins.reg_name(mem.base); disp = mem.disp
                if mn.startswith('ld') and mn != 'ldp' and mem.base in regs and not mem.index:
                    a = regs[mem.base] + disp
                    s = res_slot(a); nm = rn(ops[0])
                    if nm[0] in 'sd' and mn == 'ldr':
                        b = d.rd(a, 8); note = 'const %r' % (f32(b) if nm[0] == 's' else struct.unpack('<d', b)[0]) if b else ''
                    else: note = s or ''
                    if s: kind[nm] = 'slot:' + s
                    elif nm[0] in 'xw': kind.pop(nm, None)
                    if nm[0] in 'xw' and ops[0].reg in regs: del regs[ops[0].reg]
                    if not note: note = '@%#x' % a
                else:
                    k = kind.get(base, '')
                    if k == 'this' and disp in inst: note = 'this.' + inst[disp]
                    elif k == 'statics' and disp in stat: note = cls + '.' + stat[disp]
                    elif k == 'statics': note = 'static+%#x' % disp
                    if mn.startswith('ld') and mn != 'ldp':
                        nm = rn(ops[0])
                        if ops[0].reg in regs: del regs[ops[0].reg]
                        if k.startswith('slot:') and disp == 0: kind[nm] = 'class:' + k[5:]
                        elif k.startswith('class:') and disp == 0xb8: kind[nm] = 'statics' if k[6:].startswith(cls + '_TypeInfo') else 'statics?'
                        elif k == 'statics' : kind.pop(nm, None)
                        else: kind.pop(nm, None)
            elif mn in ('bl',):
                note = d.names.get(ops[0].imm, 'sub_%x' % ops[0].imm)
                for i in range(0, 19): kind.pop('x%d' % i, None)
            elif mn == 'b' and ops[0].type == ARM64_OP_IMM:
                note = d.names.get(ops[0].imm, '-> %x' % ops[0].imm)
            elif mn == 'mov' and len(ops) == 2 and ops[1].type == ARM64_OP_REG:
                src = rn(ops[1]); dst = rn(ops[0])
                if src in kind: kind[dst] = kind[src]
                else: kind.pop(dst, None)
            elif mn == 'add' and len(ops) == 3 and ops[1].type == ARM64_OP_REG and ops[1].reg in regs and ops[2].type == ARM64_OP_IMM:
                note = res_slot(regs[ops[1].reg] + ops[2].imm) or ''
            elif mn == 'fmov' and ops[-1].type == ARM64_OP_FP:
                note = 'fimm %r' % ops[-1].fp
            elif mn == 'fmov' and ops[-1].type == ARM64_OP_REG and ins.reg_name(ops[-1].reg)[0] == 'w':
                pass
            elif mn == 'mov' and len(ops) == 2 and ops[1].type == ARM64_OP_IMM:
                v = ops[1].imm & 0xffffffff
                try:
                    fl = struct.unpack('<f', struct.pack('<I', v))[0]
                    if v >= 0x38000000 and v < 0x7f000000 or (v >= 0xb8000000 and v < 0xff000000): note = 'as float %r' % fl
                except Exception: pass
        except Exception as e:
            note = '?' + str(e)
        out.append('%x: %-6s %-38s %s' % (ins.address, mn, ins.op_str, ('; ' + note) if note else ''))
    return out
