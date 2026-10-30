import struct, json
import desasm as d
so = d.so
# PT_DYNAMIC
e_phoff = struct.unpack_from('<Q', so, 0x20)[0]; e_phentsize, e_phnum = struct.unpack_from('<HH', so, 0x36)
dyn = None
for i in range(e_phnum):
    t,fl,off,va,pa,fs,ms,al = struct.unpack_from('<IIQQQQQQ', so, e_phoff+i*e_phentsize)
    if t == 2: dyn = (off, fs)
tags = {}
for i in range(dyn[1]//16):
    tg, v = struct.unpack_from('<QQ', so, dyn[0]+i*16)
    if tg == 0: break
    tags.setdefault(tg, v)
rela, relasz = tags[7], tags[8]
R = {}
o = d.v2o(rela)
for i in range(relasz//24):
    off, info, add = struct.unpack_from('<QQq', so, o+i*24)
    if info & 0xffffffff == 1027: R[off] = add
S = {m['Address']: m['Value'] for m in d.D['ScriptString']}
M = {}
for k in ('ScriptMetadata','ScriptMetadataMethod'):
    for m in d.D[k]: M[m['Address']] = m['Name']
def res(a):
    t = R.get(a)
    if t is None: return None
    return t, S.get(t), M.get(t)
if __name__ == '__main__':
    import sys
    for a in sys.argv[1:]:
        a = int(a, 16); print(hex(a), res(a))
