"""Cherche dans libdq4core.so les appels aux fonctions d'envoi vers l'interface Unity : setItemParam (PLT 0x225070 : item, id, no, donnee), setItemCode (0x225060 : item, code, valeur)
et le texte setItemParam chaine (0x225190..), avec les valeurs immediates passees (mov w1/w2/w3 #imm) et la fonction appelante.
Usage : python3 audit_scan_itemparam.py [sous-chaine du nom de fonction]"""
import sys, struct
import audit_eng as E
flt = sys.argv[1] if len(sys.argv) > 1 else ''
lo, hi = 0x1000, 0x230000
code = E.rd(lo, hi - lo)
tgt = {0x225070: 'setItemParam', 0x225060: 'setItemCode'}
n = len(code) // 4
words = struct.unpack('<%dI' % n, code[:n * 4])
def movimm(w):
    # MOVZ w : 0x52800000 | imm16<<5 | rd
    if w & 0x7f800000 == 0x52800000:
        return w & 0x1f, (w >> 5) & 0xffff
for k, w in enumerate(words):
    if w >> 26 == 0x25:           # BL
        imm = w & 0x3ffffff
        if imm & 0x2000000: imm -= 0x4000000
        a = lo + 4 * k; t = a + imm * 4
        if t in tgt:
            regs = {}
            for j in range(max(0, k - 14), k):
                m = movimm(words[j])
                if m: regs[m[0]] = m[1]
            nm = E.symof(a)
            if flt in nm:
                print('%x %-12s %-44s w1=%s w2=%s w3=%s' % (a, tgt[t], nm, regs.get(1), regs.get(2), regs.get(3)))
