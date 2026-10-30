"""Export de la fenetre de message (MenuMessage) : pour chaque type de fenetre (MenuMessage.canvas_data), position de la fenetre, cadre
(frameData), quadrilatere du canevas de texte (le texte est dessine par le moteur) et position du curseur de fin de page.
Usage : python message.py sortie.json   (variables DQ_IL2, DQ_META, DQ_FRAME comme layout.py)"""
import sys, json, struct
import scene as S, runall2 as R, menusys as M, layout as L
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
T = S.T
r4 = lambda x: round(float(x), 4)


def lire_cadres():
    b = open(M.FRAME, 'rb').read(); n = struct.unpack_from('<i', b, 0)[0]; p = 4; out = []
    for i in range(n):
        nv, ni = struct.unpack_from('<ii', b, p); p += 8
        v = [struct.unpack_from('<5f', b, p + 20 * j) for j in range(nv)]; p += 20 * nv
        t = list(struct.unpack_from('<%di' % ni, b, p)); p += 4 * ni
        out.append((v, t))
    return out


CADRES = lire_cadres()
st = R.statics(T, 'MenuMessage')
parts_fen = T.u(st + 8, 8)                                   # MenuMessage.m_window (MenuParts)
go_fen = T.U[parts_fen]['go']
mf_fen = [c for c in T.U[go_fen]['comps'] if T.U[c]['kind'] == 'MeshFilter'][0]
TOUS = []


def _cadre(uc, a, sz, ud):
    """m_frame.Change(n) : appel de delegue non emule -> on pose nous-memes le maillage de cadre n sur la fenetre (puis on saute l'appel)."""
    n = uc.reg_read(UC_ARM64_REG_X1) & 0xffffffff
    v, t = CADRES[n]
    m = T.U[mf_fen].get('mesh')
    if not m: m = T.U[mf_fen]['mesh'] = T.newU('Mesh', 'UnityEngine.Mesh', vtx=[], uv=[], tris={}, sub=1)
    T.U[m]['vtx'] = [tuple(x[:3]) for x in v]; T.U[m]['uv'] = [tuple(x[3:]) for x in v]; T.U[m]['tris'] = {0: t}
    TOUS.append(n)
    uc.reg_write(UC_ARM64_REG_PC, 0xcfa644)


T.uc.hook_add(UC_HOOK_CODE, _cadre, None, 0xcfa640, 0xcfa640)


def exporter():
    cd = T.u(st + 0, 8); n = T.u(cd + 0x18, 4)
    msg = T.msg
    canvas_go = T.u(msg + 0x18, 8)
    types = []
    for no in range(n):
        raw = struct.unpack('<iiffffff', bytes(T.uc.mem_read(cd + 0x20 + 32 * no, 32)))
        T.uc.mem_write(msg + 0x5c, b'\xff\xff')              # m_nowType : force le recalcul
        del TOUS[:]
        err = T.run(0xcfa4b4, [msg, no])
        cm = T.U[T.u(msg + 0x28, 8)]
        fen = T.U[go_fen]; feed_parts = T.u(msg + 0x20, 8); feed_go = T.U[feed_parts]['go']
        fm = T.U[mf_fen].get('mesh'); fm = T.U[fm] if fm else None
        t = dict(no=no, err=err, frame=raw[0], indent=raw[1], cursor=[r4(raw[2]), r4(raw[3])], yDif=r4(raw[4]), scale=r4(raw[5]), shift=r4(raw[6]),
                 flag=struct.unpack('<i', struct.pack('<f', raw[7]))[0] & 0xff,
                 win=[r4(x) for x in T.world(fen['tr'])],
                 canvas=dict(vtx=[[r4(v[0]), r4(v[1]), r4(v[2])] for v in cm['vtx']], uv=[[r4(x) for x in v] for v in cm['uv']], tris=cm['tris'].get(0)),
                 canvas_local=[r4(x) for x in T.U[T.U[canvas_go]['tr']].get('lpos', [0, 0, 0])],
                 feed_local=[r4(x) for x in T.U[T.U[feed_go]['tr']].get('lpos', [0, 0, 0])],
                 frame_mesh=dict(vtx=[[r4(v[0]), r4(v[2])] for v in fm['vtx']], uv=[[r4(x) for x in v] for v in fm['uv']], tris=fm['tris'].get(0)) if fm else None)
        types.append(t)
    fg = T.U[T.U[T.u(msg + 0x20, 8)]['go']]
    feed = None
    for c in fg['comps']:
        cu = T.U[c]
        if cu['kind'] == 'MeshFilter' and cu.get('mesh'):
            m = T.U[cu['mesh']]; feed = dict(vtx=[[r4(v[0]), r4(v[2])] for v in m['vtx']], uv=[[r4(x) for x in v] for v in m['uv']], tris=m['tris'].get(0))
    for c in fg['comps']:
        if T.U[c]['kind'] == 'MenuParts': feed['parts'] = dict(nowParts=T.u(c + 0x20, 4, True))
        if T.U[c]['kind'] == 'MeshRenderer' and feed:
            feed['mats'] = [dict(sheet=T.U[mm].get('sheet'), part=T.U[mm].get('part')) for mm in T.U[c].get('mat', []) if mm in T.U]
    mr = [c for c in T.U[go_fen]['comps'] if T.U[c]['kind'] == 'MeshRenderer'][0]
    fen_mats = [dict(sheet=T.U[mm].get('sheet'), part=T.U[mm].get('part')) for mm in T.U[mr].get('mat', []) if mm in T.U]
    return dict(types=types, feed=feed, frame_mats=fen_mats, canvas_size=512, screenH=T.screen[1])


if __name__ == '__main__':
    out = exporter()
    json.dump(out, open(sys.argv[1], 'w'))
    for t in out['types']:
        print(t['no'], 'err', t['err'], 'frame', t['frame'], 'indent', t['indent'], 'win', t['win'], 'canvas', t['canvas']['vtx'][:3], 'feed', t['feed_local'])
