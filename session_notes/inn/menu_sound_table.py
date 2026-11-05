import os, sys, struct, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import capstone, zipfile
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc import sound as S
m = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_inn_')); c = m.core
L = c.LIB_BASE
tbl = c.mem(L + 0xc4c94, 15)
cs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
z = zipfile.ZipFile(os.path.join(APK, 'split_UnityDataAssetPack.apk'))
def dur(b):
    d = z.read('assets/sound/BGM%02d.akb' % b); h = S.read_header(d); return h['echantillons'] / h['frequence'], h['fin'] > 0
print('type(w1) idx byte -> target | start_delay(frames) BGM duration(frames) | file duration s, loops | window s')
for w1 in range(1, 16):
    idx = w1 - 1
    target = 0x1582dc + 4 * tbl[idx]
    # emulate the tiny block: set w8=0x64, w9=0x2b by default ; track instructions until branch to 0x15836c
    regs = {'w8': 0x64, 'w9': 0x2b}; delay = 0xf; pc = target; steps = 0
    while steps < 10:
        ins = list(cs.disasm(c.mem(L + pc, 4), pc))[0]
        if ins.mnemonic == 'mov':
            r, v = [x.strip() for x in ins.op_str.split(',')]
            if r in ('w8', 'w9'): regs[r] = 0 if v == 'wzr' else int(v.strip('#'), 0)
        elif ins.mnemonic == 'str' and 'x0, #8' in ins.op_str:
            delay = regs['w8']
        elif ins.mnemonic == 'b':
            nxt = int(ins.op_str[1:], 16)
            if nxt == 0x15836c: break
        print('      ', hex(pc), ins.mnemonic, ins.op_str) if os.environ.get('V') else None
        pc += 4; steps += 1
    bgm, dframes = regs['w9'], regs['w8']
    d, lp = dur(bgm)
    print('%2d idx=%2d tbl=%3d -> %#x | delay=%3d BGM%02d dur=%3d frames | file %.3f s loop=%s | heard window %.3f s (%.1f%% of file)' % (w1, idx, tbl[idx], target, delay, bgm, dframes, d, lp, (dframes - delay) / 30.0, 100.0 * ((dframes - delay) / 30.0) / d))
