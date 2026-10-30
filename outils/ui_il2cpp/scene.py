import sys, json, struct
import runall2 as R, tracer as t
import desasm as d, menusys as M
import os
T = R.make()
_H = int(os.environ.get('DQ_UI_H', '800')); T.screen = (450, _H); T.aspect = 450.0 / _H
T.run(0xd2370c)
M.system_init(T)
M.make_message(T)
def dump(typ, show=True):
    nm = R.tbl[typ]
    id0 = len(T.obj)
    keep = set(T.U)
    err = T.run(R.addr[nm[:-2]], [7, typ])
    out = []
    for o, u in T.U.items():
        if u['kind'] != 'GameObject' or o in keep: continue
        tr = u['tr']; w = T.world(tr); sc = T.pscale(tr)
        e = dict(id=u['id'], name=u.get('name'), pos=[round(x, 3) for x in w], scale=[round(x, 3) for x in sc], par=T.U[T.U[tr]['parent']]['go'] and T.U[T.U[T.U[tr]['parent']]['go']]['id'] if T.U[tr]['parent'] else None)
        for c in u['comps']:
            cu = T.U[c]
            if cu['kind'] == 'MeshFilter' and cu.get('mesh'):
                m = T.U[cu['mesh']]; e['mesh'] = dict(vtx=m['vtx'], uv=m['uv'], tris=m['tris'])
            elif cu['kind'] == 'MeshRenderer':
                e['mats'] = [dict(sheet=T.U[m].get('sheet'), part=T.U[m].get('part'), color=T.U[m].get('color')) for m in cu.get('mat', []) if m in T.U]
            elif cu['kind'] == 'TextMesh':
                e['text'] = {k: v for k, v in cu.items() if k not in ('kind', 'id', 'go')}
            elif cu['kind'] == 'MenuParts':
                e['parts'] = dict(nowParts=T.u(c + 0x20, 4, True), buttonId=T.u(c + 0x48, 2, True), gamepad=T.u(c + 0x4a, 2, True))
        out.append(e)
    return nm, err, out
if __name__ == '__main__':
    typ = int(sys.argv[1])
    nm, err, out = dump(typ)
    print(nm, err, len(out), 'objets')
    for e in out:
        m = e.get('mesh')
        print(e['id'], e['name'], 'pos', e['pos'], 'sc', e['scale'], 'par', e['par'], 'mats', e.get('mats'), 'text', e.get('text'), 'parts', e.get('parts'),
              ('mesh nv=%d' % len(m['vtx']) + ' bbox=%s' % ((min(v[0] for v in m['vtx']), max(v[0] for v in m['vtx']), min(v[2] for v in m['vtx']), max(v[2] for v in m['vtx'])),)) if m and m['vtx'] else '')
    for e in T.log[:0]: print(e)
