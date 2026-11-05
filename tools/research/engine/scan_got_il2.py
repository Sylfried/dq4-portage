"""Methodes IL2CPP qui chargent un emplacement GOT (adrp+ldr) : python3 scan_got_il2.py 0x1b937b8"""
import os, sys, struct, bisect
os.environ.setdefault('DQ_IL2', '/home/claude/il2')
sys.path.insert(0, '/home/claude/dq4-portage/tools/ui_il2cpp')
import disasm as d
tgt = int(sys.argv[1], 16); off = tgt & 0xfff; page = tgt & ~0xfff
data = open('/home/claude/il2/libil2cpp.so', 'rb').read()
ks = sorted(d.names)
# segment texte : RVA -> offset fichier = RVA - 0x4000 (cf. consigne)
lo = ks[0]; hi = ks[-1] + 0x400
res = set()
for rva in range(lo, hi, 4):
    o = rva - 0x4000
    w = struct.unpack_from('<I', data, o)[0]
    if (w >> 22) == 0x3E5 and ((w >> 10) & 0xFFF) == off // 8:
        rn = (w >> 5) & 31
        for j in range(1, 10):
            x = struct.unpack_from('<I', data, o - 4 * j)[0]
            if (x & 0x9F000000) == 0x90000000 and (x & 31) == rn:
                imm = ((x >> 5) & 0x7FFFF) << 2 | ((x >> 29) & 3)
                if imm & (1 << 20): imm -= 1 << 21
                if (((rva - 4 * j) & ~0xfff) + (imm << 12)) == page:
                    k = bisect.bisect_right(ks, rva) - 1; res.add(d.names[ks[k]])
                break
print('\n'.join(sorted(res)))
