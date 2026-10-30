"""Remplace MenuParts.SystemInit (chargement Resources) : polices/shaders/couleurs/frameData réels, hors Unity."""
import struct, re
import runall2 as R, reloc as rl
import os
FRAME = os.environ.get('DQ_FRAME', 'frameData.bin')

def klass_of(T, name):
    for tok, nm in rl.M.items():
        if nm == name + '_TypeInfo':
            k = T.klass.get(tok) or T.new_klass(tok); T.w(tok, k); return k
    return None
def arr(T, items, esize, kname=None):
    n = len(items); o = T.alloc(0x20 + esize * n + 16); T.w(o + 0x18, n, 8); T.obj[o] = len(T.obj) + 1
    for i, raw in enumerate(items): T.uc.mem_write(o + 0x20 + esize * i, raw)
    return o
def load_frames(T, path=FRAME):
    b = open(path, 'rb').read(); n = struct.unpack_from('<i', b, 0)[0]; p = 4; objs = []
    kml = klass_of(T, 'MeshList')
    for i in range(n):
        nv, ni = struct.unpack_from('<ii', b, p); p += 8
        v = [struct.unpack_from('<5f', b, p + 20 * j) for j in range(nv)]; p += 20 * nv
        t = struct.unpack_from('<%di' % ni, b, p); p += 4 * ni
        m = T.new_obj(kml or 0, fill=False)
        T.w(m + 0x10, arr(T, [struct.pack('<3f', *x[:3]) for x in v], 12))
        T.w(m + 0x18, arr(T, [struct.pack('<2f', *x[3:]) for x in v], 8))
        T.w(m + 0x20, arr(T, [struct.pack('<i', x) for x in t], 4))
        objs.append(m)
    return arr(T, [struct.pack('<Q', o) for o in objs], 8)

def system_init(T, frame_path=FRAME, lang=1):
    st = R.statics(T, 'MenuParts')
    T.w(st + 0x60, T.newU('Font', 'UnityEngine.Font'))
    for off, nm in ((0x38, 'font'), (0x40, 'gray'), (0x48, 'reverse'), (0x50, 'picture'), (0x58, 'parts')):
        T.w(st + off, T.newU('Shader', 'UnityEngine.Shader', name=nm))
    cl = T.u(st + 0x70, 8); fl = T.u(st + 0x78, 8); n = T.u(cl + 0x18, 8)
    for i in range(n):
        col = list(struct.unpack('<4f', bytes(T.uc.mem_read(cl + 0x20 + 16 * i, 16))))
        m = T.newU('Material', 'UnityEngine.Material', shader='font', color=[round(x, 4) for x in col], tex=None, sheet='font')
        T.w(fl + 0x20 + 8 * i, m)
    T.w(st + 0x68, load_frames(T, frame_path))
    # langue : GetLangages.m_langagesNumber (0 = ja, 1 = en : la langue que le patch français remplace) -> MenuParts.LangParam.Apply
    sl = T.u(st + 0x20, 8)
    T.run(0xcfd5e8, [sl + 0x20 + 0x18 * lang])
    return n

def make_message(T, port=0):
    """Construit la fenêtre de message (MenuMessage..ctor) : plusieurs fenêtres se placent par rapport à elle (MenuMessage.m_window)."""
    obj = T.new_obj(klass_of(T, 'MenuMessage') or 0)
    err = T.run(0xcfab44, [obj, port])
    T.msg = obj
    return err
