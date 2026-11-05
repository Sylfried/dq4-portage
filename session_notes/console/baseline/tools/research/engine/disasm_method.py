"""Desassemble une methode IL2CPP par RVA ou nom : python3 dis.py 0xD07E74 [fin]  (DQ_IL2=/home/claude/il2)"""
import os, sys
os.environ.setdefault('DQ_IL2', '/home/claude/il2')
sys.path.insert(0, '/home/claude/dq4-portage/tools/ui_il2cpp')
import disasm as d
def end(start):
    ks = sorted(a for a in d.names if a > start); return ks[0]
if __name__ == '__main__':
    a = sys.argv[1]
    if a.startswith('0x'): s = int(a, 16)
    else:
        c = [k for k, v in d.names.items() if v == a or v.endswith(a)]
        if not c: raise SystemExit('introuvable')
        s = c[0]; print('RVA %#x' % s)
    e = int(sys.argv[2], 16) if len(sys.argv) > 2 else end(s)
    print('\n'.join(d.dis(s, e)))
