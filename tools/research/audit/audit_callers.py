"""Appelants (bl/b) d'une adresse de libil2cpp.so : DQ_IL2=... python3 audit_callers.py <RVA hex> [...]"""
import sys, os, struct
sys.path.insert(0, '/home/claude/dq4-portage/tools/ui_il2cpp'); os.environ.setdefault('DQ_IL2', '/home/claude/il2')
import disasm as d
targets = {int(a, 16) for a in sys.argv[1:]}
# parcourt les ScriptMethod (debuts de methodes) : desassemble chacune et cherche bl/b vers target
addrs = sorted(m['Address'] for m in d.D['ScriptMethod'])
import bisect
res = {}
for t in targets:
    res[t] = []
# balayage lineaire du segment executable par mots de 4 octets : bl = 0x94000000|imm26, b = 0x14000000|imm26
for v, o, s in d.segs:
    if v > 0x2000000: continue
    code = d.so[o:o + s]
    n = len(code) // 4
    words = struct.unpack('<%dI' % n, code[:n * 4])
    for i, w in enumerate(words):
        op = w >> 26
        if op in (0x25, 0x05):
            imm = w & 0x3ffffff
            if imm & 0x2000000: imm -= 0x4000000
            tgt = v + i * 4 + imm * 4
            if tgt in targets:
                pc = v + i * 4
                k = bisect.bisect_right(addrs, pc) - 1
                res[tgt].append((pc, 'bl' if op == 0x25 else 'b', d.names.get(addrs[k], '?'), addrs[k]))
for t, l in res.items():
    print('== appelants de %#x (%s)' % (t, d.names.get(t, '?')))
    for pc, k, nm, a in l: print('   %#x %s dans %s (%#x)' % (pc, k, nm, a))
