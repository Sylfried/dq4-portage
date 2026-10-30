import tracer as t, tracer2 as t2, json, collections, sys, re, struct
import desasm as d, reloc as rl
from unicorn.arm64_const import *
tbl = []          # numero de menu -> nom de la fonction Make_* (rempli par make() : tableau MenuPortItemTable.makeFuncList du jeu)
addr = {}
cctor = {}
for rva, sg in t.SIG.items():
    if sg['cls'] == 'MenuPortItemTable' and sg['name'].startswith('Make_'): addr[sg['name']] = rva
    if sg['name'] == 'cctor': cctor[sg['cls']] = rva
SHEET_W = {0: 1024, 1: 512}
def statics(T, cn):
    k = [k for k in T.kname if T.kname[k] == cn + '_TypeInfo']
    return T.u(k[0] + 0xb8, 8) if k else None
def make():
    T = t2.Tr2()
    for cls in ('MenuParts', 'MenuMessage', 'MenuPortItem', 'MenuPortItemTable', 'Global', 'NotchFix', 'UIFix', 'MeshMaker', 'eIndent'):
        if cls in cctor:
            err = T.run(cctor[cls])
            if err: print('cctor', cls, err)
    # planches : PartsInfo prêtes
    st = statics(T, 'MenuParts')
    arr = T.u(st + 0x30, 8); n = T.u(arr + 0x18, 8)
    T.infos = []
    for i in range(n):
        o = T.u(arr + 0x20 + 8 * i, 8)
        texNo, sx, sy, ps, dps = [T.u(o + off, 4, True) for off in (0x10, 0x14, 0x18, 0x1c, 0x20)]
        W = SHEET_W[texNo]
        mat = T.newU('Material', 'UnityEngine.Material', shader='parts', sheet=texNo, part=i, color=None, tex=None)
        T.w(o + 0x28, mat)
        lst = T.new_obj(T.klass_for_type('System.Collections.Generic.List<UnityEngine.Material>') or 0, fill=False); T.list_init(lst, 8); T.w(o + 0x30, lst)
        T.uc.mem_write(o + 0x38, struct.pack('<ff', ps / W, sy / W))
        T.uc.mem_write(o + 0x40, struct.pack('<ii', W // ps, sx // ps))
        T.infos.append(dict(i=i, texNo=texNo, sx=sx, sy=sy, ps=ps, dps=dps, W=W))
    st = statics(T, 'MenuPortItemTable')              # makeFuncList : un delegue par type de menu
    arr = T.u(st + 0, 8); n = T.u(arr + 0x18, 8)
    del tbl[:]
    for i in range(n):
        dl = T.deleg.get(T.u(arr + 0x20 + 8 * i, 8))
        tbl.append(dl[1].replace('Method$', '').replace('MenuPortItemTable.', '') if dl else '?')
    return T
if __name__ == '__main__':
    T = make()
    print(T.infos[:3])
    err = T.run(0xd2370c); print('eIndent.Init', err)
    es = statics(T, 'eIndent'); print('eIndent statics', struct.unpack('<ff', T.uc.mem_read(es, 8)))
