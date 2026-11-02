"""Liste les appels (bl/b) vers une fonction de libdq4core : python3 scan_calls.py <sous-chaine_de_symbole | 0xadresse>"""
import sys, struct; sys.path.insert(0, '/tmp/specs')
import dasm_core as d
cible = sys.argv[1]
if cible.startswith('0x'): targets = {int(cible, 16)}
else: targets = {a for a, n in d.syms.items() if cible in n} | {a for a, n in d.PLT.items() if cible in n}
print('cibles', [hex(t) for t in targets])
code = d.data[:0x233960]
for i in range(0, len(code) - 3, 4):
    w = struct.unpack_from('<I', code, i)[0]
    if (w >> 26) in (0x25, 0x05):                      # bl / b
        imm = w & 0x3ffffff
        if imm & 0x2000000: imm -= 0x4000000
        t = i + imm * 4
        if t in targets: print(hex(i), 'bl' if w >> 26 == 0x25 else 'b', d.nom(i))
