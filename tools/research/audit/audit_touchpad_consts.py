"""TouchPad..cctor (0xD255B4) : tableaux statiques c_PadScaleTBL (float[3]) et c_padDirTable (int[8]) + flottants statiques s_*  (lus dans global-metadata.dat / libil2cpp.so)."""
import sys, struct, os
sys.path.insert(0, '/home/claude/dq4-portage/tools/ui_il2cpp')
os.environ.setdefault('DQ_IL2', '/home/claude/il2'); os.environ.setdefault('DQ_META', '/tmp/apkx/assets/bin/Data/Managed/Metadata/global-metadata.dat')
import meta
b1 = meta.field_default('60DE99C68B7A3184D02A229B91B2979BCF4A6F68568CD4AF8DC50F6EF7B16611')
b2 = meta.field_default('69751C2D07CE8A5FC1725FDF41B1472C7410327F411D7F78ED7B76C12F9FCCC4')
print('c_PadScaleTBL (float[3])  =', struct.unpack('<3f', b1[:12]))
print('c_padDirTable (int[8])    =', struct.unpack('<8i', b2[:32]))
import disasm as d
# statiques flottants poses dans .cctor : q0 lu en 0x4dc310 (16 octets -> +0x48), d1 lu en 0x4c0aa0 (8 octets -> +0x58)
q = d.rd(0x4dc310, 16); dd = d.rd(0x4c0aa0, 8)
nm = ['s_MoveRingLimit(+0x48)', 's_MoveReversLimit(+0x4C)', 's_MoveBeginLimit(+0x50)', 's_MoveThreshold(+0x54)']
for n, v in zip(nm, struct.unpack('<4f', q)): print(n, v)
for n, v in zip(['s_AnyThreshold(+0x58)', 's_moveNakaLimit(+0x5C)'], struct.unpack('<2f', dd)): print(n, v)
print('(l_padPos, l_padSize) initiaux = (1, 1) : movi v0.2s,#1 ; stur d0,[x8,#0x84] (0xd25758)')
