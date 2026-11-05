"""Affiche les lignes d'un listing annote (audit_dis) entre deux adresses, sans le bruit d'initialisation IL2CPP."""
import sys
f, a, b = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
noise = ('sub_c10290', 'cbnz   w8, #', 'cbnz   w9, #', 'ldr    w8, [x0, #0xe0]', 'ldr    w9, [x0, #0xe0]', 'ldr    w9, [x8, #0xe0]', 'cbnz   w10, #', 'sub_c1018c')
for l in open(f):
    try: ad = int(l.split(':')[0], 16)
    except Exception: continue
    if a <= ad < b and not any(n in l for n in noise): print(l.rstrip())
