import os, sys, struct, tempfile
sys.path.insert(0, '/home/claude/dq4-portage')
from h import *
import capstone, bisect
m = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_inn_')); c = m.core
cs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
def sym(off):
    i = bisect.bisect_right(c.elf.func_starts, off) - 1
    if i >= 0:
        s, sz, n = c.elf.funcs[i]; return '%s+%#x' % (n, off - s)
    return '?'
def dis(name, maxn=400):
    a = c.export(name); off = a - c.LIB_BASE
    i = bisect.bisect_right(c.elf.func_starts, off) - 1; s, sz, n = c.elf.funcs[i]
    print('=== %s at %#x size %#x (funcs entry %s)' % (name, off, sz, n))
    code = c.mem(a, sz or 0x400)
    for ins in cs.disasm(code, off):
        extra = ''
        if ins.mnemonic in ('bl', 'b') and ins.op_str.startswith('#'):
            extra = '   ; ' + sym(int(ins.op_str[1:], 16))
        print('%6x: %-8s %s%s' % (ins.address, ins.mnemonic, ins.op_str, extra))
for n in sys.argv[1:]: dis(n)
