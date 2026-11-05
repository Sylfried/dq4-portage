"""Cherche strb/ldrb [xN,#imm] dans libdq4core pour fonctions dont le nom contient un motif : python3 scan_str.py 0x68 pattern"""
import sys, struct, bisect
sys.path.insert(0,'/tmp/specs')
import dasm_core as d
imm=int(sys.argv[1],16); pat=sys.argv[2]
ks=sorted(d.syms)
for v,o,s in d.segs:
    for i in range(0,s,4):
        w=struct.unpack_from('<I',d.data,o+i)[0]
        if (w>>22) in (0x0E4,0x0E5) and ((w>>10)&0xFFF)==imm:   # strb / ldrb unsigned offset
            va=v+i;k=bisect.bisect_right(ks,va)-1
            if k>=0 and pat.lower() in d.syms[ks[k]].lower() and va-ks[k]<0x4000:
                print('STR' if (w>>22)==0x0E4 else 'LDR',hex(va),d.syms[ks[k]],'+',hex(va-ks[k]))
