"""Liste les appels (bl/b) vers une methode de libil2cpp.so : python3 scan_il2.py <RVA hex | sous-chaine de nom> ; DQ_IL2=/home/claude/il2"""
import os, sys, struct
os.environ.setdefault('DQ_IL2', '/home/claude/il2')
sys.path.insert(0, '/home/claude/dq4-portage/tools/ui_il2cpp')
import disasm as d
target = sys.argv[1]
if target.startswith('0x'): targets = {int(target, 16)}
else: targets = {a for a, n in d.names.items() if target in n}
print('cibles', [(hex(t), d.names.get(t)) for t in sorted(targets)][:10])
lo = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x1c00000
code = d.rd(lo, hi - lo)
for i in range(0, len(code) - 3, 4):
    w = struct.unpack_from('<I', code, i)[0]
    if (w >> 26) in (0x25, 0x05):
        imm = w & 0x3ffffff
        if imm & 0x2000000: imm -= 0x4000000
        t = lo + i + imm * 4
        if t in targets:
            a = lo + i
            ks = [k for k in d.names if k <= a]
            f = max(ks) if ks else 0
            print(hex(a), 'bl' if w >> 26 == 0x25 else 'b', 'dans', hex(f), d.names.get(f))
