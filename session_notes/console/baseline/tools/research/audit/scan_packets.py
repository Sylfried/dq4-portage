"""Inventaire des paquets que libdq4core.so peut emettre vers Unity : pour chaque appel a UnityGetPacket(int) / UnityGetPacket(int,int) (et UnitySetFade, UnitySetString, unity_load_fld...),
recherche de l'immediat charge dans w0 juste avant, et de la fonction appelante.  Usage : python3 scan_packets.py"""
import sys, struct, re, collections
sys.path.insert(0, '/tmp/specs')
import dasm_core as d
from capstone import *
from capstone.arm64 import *
code = d.data[:0x233960]
base = 0
targets = {}
for a, n in d.syms.items():
    if n.startswith('UnityGetPacket(') or n in ('UnitySetFade(int)', 'UnitySetString(char const*)', 'unity_load_fld(char const*, int)', 'UnityInitTouchFlag(int)', 'UnitySetMapBackColor(char const*, char const*)', 'UnitySetMapColorRate(int, int, int)', 'UnityDebugFlagShop()'):
        targets[a] = n
for a, n in d.PLT.items():
    m = {'_Z14UnityGetPacketi': 'UnityGetPacket(int)', '_Z14UnityGetPacketii': 'UnityGetPacket(int,int)', '_Z12UnitySetFadei': 'UnitySetFade(int)', '_Z14unity_load_fldPKci': 'unity_load_fld(char const*,int)',
         '_Z18UnityInitTouchFlagi': 'UnityInitTouchFlag(int)', '_Z20UnitySetMapBackColorPKcS0_': 'UnitySetMapBackColor', '_Z20UnitySetMapColorRateiii': 'UnitySetMapColorRate(int,int,int)', '_Z18UnityDebugFlagShopv': 'UnityDebugFlagShop()',
         '_ZN3dss6Camera10send_unityEv': 'dss::Camera::send_unity()', '_ZN10DSSAObject15send_unity_loadEii': 'DSSAObject::send_unity_load', '_Z14UnitySetPacketii': 'UnitySetPacket(int,int)'}
    if n in m: targets[a] = m[n]
print('cibles', {hex(a): n for a, n in targets.items()})
res = collections.defaultdict(list)
# decoder bl
md = d.md
md.skipdata = True
insns = [i for i in md.disasm(code, 0)]
print('instructions decodees', len(insns), 'sur', len(code)//4)
idx = {i.address: k for k, i in enumerate(insns)}
for k, ins in enumerate(insns):
    if ins.mnemonic in ('bl', 'b') and ins.operands[0].type == ARM64_OP_IMM and ins.operands[0].imm in targets:
        t = targets[ins.operands[0].imm]
        imm = None
        # recherche en arriere d'un mov w0, #imm (ou mov w0, wN suivi...)
        for j in range(k - 1, max(k - 14, 0), -1):
            p = insns[j]
            if p.mnemonic in ('mov', 'movz') and p.operands[0].type == ARM64_OP_REG and md.reg_name(p.operands[0].reg) in ('w0', 'x0'):
                if p.operands[1].type == ARM64_OP_IMM: imm = p.operands[1].imm
                else: imm = 'reg:' + md.reg_name(p.operands[1].reg)
                break
            if p.mnemonic in ('bl', 'blr', 'ret', 'b', 'cbz', 'cbnz') : break
            if p.operands and p.operands[0].type == ARM64_OP_REG and md.reg_name(p.operands[0].reg) in ('w0', 'x0') and p.mnemonic not in ('cmp', 'tst', 'str', 'stp', 'strb', 'strh'):
                imm = 'calc:' + p.mnemonic + ' ' + p.op_str; break
        res[(t, imm)].append((ins.address, d.name_str(ins.address)))
out = []
for (t, imm), v in sorted(res.items(), key=lambda x: (x[0][0], str(x[0][1]))):
    fn = sorted(set((n or '?').split('+')[0] for a, n in v))
    out.append('%s | type=%s | %d appels | %s' % (t, imm, len(v), '; '.join(fn)))
print('\n'.join(out))
