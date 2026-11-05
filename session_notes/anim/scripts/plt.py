import sys, struct, json, bisect
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
from capstone import *
from capstone.arm64 import *
eng = bp.boot(); c = eng.core; L = c.LIB_BASE
syms = {}
for l in open('/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/syms.txt'):
    p = l.split()
    if len(p) == 3 and p[1] in 'TtWw': syms[int(p[0], 16)] = p[2]
ks = sorted(syms)
def nm(a):
    i = bisect.bisect_right(ks, a) - 1
    return (syms[ks[i]], a - ks[i]) if i >= 0 else (None, 0)
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM); md.detail = True
base, size = int(sys.argv[1], 16), int(sys.argv[2], 16)
code = c.mem(L + base, size)
res = {}
pg = None
for ins in md.disasm(code, base):
    if ins.mnemonic == 'adrp' and ins.operands[0].reg == ARM64_REG_X16: pg = ins.operands[1].imm; start = ins.address
    elif ins.mnemonic == 'ldr' and ins.operands[0].reg == ARM64_REG_X17 and ins.operands[1].type == ARM64_OP_MEM:
        ga = pg + ins.operands[1].mem.disp
        tgt = struct.unpack('<Q', c.mem(L + ga, 8))[0]
        rel = tgt - L
        n, off = nm(rel) if 0 <= rel < 0x300000 else (None, 0)
        res[start] = (hex(rel) if 0 <= rel < 0x300000 else hex(tgt), n, off)
json.dump(res, open(sys.argv[3], 'w'))
print(len(res))
for k in list(res)[:5]: print(hex(k), res[k])
