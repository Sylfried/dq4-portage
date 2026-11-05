"""Cherche les fonctions de libdq4core qui chargent un emplacement GOT : python3 scan_got.py 0x23d7b8"""
import sys, struct, bisect
sys.path.insert(0,'/tmp/specs')
import dasm_core as d
off = int(sys.argv[1],16) & 0xfff
page = int(sys.argv[1],16) & ~0xfff
ks = sorted(d.syms)
for v,o,s in d.segs:
    for i in range(0, s, 4):
        w = struct.unpack_from('<I', d.data, o+i)[0]
        if (w>>22)==0x3E5 and ((w>>10)&0xFFF)==off//8:
            va = v+i
            # chercher adrp dans les 12 instrs precedentes avec la page voulue
            rn = (w>>5)&31
            ok=False
            for j in range(1,14):
                x = struct.unpack_from('<I', d.data, o+i-4*j)[0]
                if (x & 0x9F000000)==0x90000000 and (x&31)==rn:
                    imm = ((x>>5)&0x7FFFF)<<2 | ((x>>29)&3)
                    if imm & (1<<20): imm -= 1<<21
                    p = ((v+i-4*j)&~0xfff) + (imm<<12)
                    ok = (p==page); break
            if ok:
                k = bisect.bisect_right(ks, va)-1
                print(hex(va), d.syms[ks[k]] if k>=0 else '?', '+', hex(va-ks[k]))
