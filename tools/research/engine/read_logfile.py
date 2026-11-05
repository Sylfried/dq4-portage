import pickle, sys
J = pickle.load(open(sys.argv[1], 'rb'))
ports = [int(x) for x in sys.argv[2].split(',')]
lo = int(sys.argv[3]) if len(sys.argv) > 3 else 0
hi = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
lim = int(sys.argv[5]) if len(sys.argv) > 5 else 200
def dec(a):
    if not a: return 'vide'
    c = a[0]
    if c == 10 and len(a) >= 5:
        v = (a[3] & 0xffff) | ((a[4] & 0xffff) << 16); sv = v - (1 << 32) if v & 0x80000000 else v
        return 'INT(id=%d,no=%d)=%d  [col=%d low=%d]' % (a[1], a[2], sv, sv >> 16, sv & 0xffff)
    if c == 12: return 'CODE(id=%d)=%d' % (a[1], a[2] if len(a) > 2 else None)
    if c == 11: return 'TEXT(line=%d,col=%d) follows' % (a[1], a[2])
    if c in (5, 6): return 'cmd%d' % c
    return 'cmd%d %s' % (c, a[1:])
def txt(a):
    return ''.join(chr(v & 0xffff) if (v & 0xffff) >= 32 else '\\n' if (v & 0xffff) == 10 else '' for v in a if v)
n = 0; waiting = {}
for im, pt, port, a in J:
    if port not in ports or im < lo or im > hi: continue
    if a and a[0] in (5, 6) and '-q' in sys.argv: continue
    s = dec(a)
    if port in waiting and a and not (a[0] in (1, 2, 3, 4, 5, 6, 7, 8, 10, 12) and len(a) < 4 and False):
        pass
    print(im, port, s, '' if True else '')
    n += 1
    if n >= lim: break
