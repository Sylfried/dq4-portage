"""Export de la mise en page des menus : pour chaque type de menu, exécute le Make_* d'origine et décrit nœuds, pièces (MenuParts),
changeurs (IBase), tables de liaison (id,no) et effets des codes (déplacement / visibilité)."""
import sys, json, struct, copy
import scene as S, runall2 as R, tracer as t, desasm as d, reloc as rl
T = S.T
SIGADDR = {}
for a, sg in t.SIG.items():
    SIGADDR[sg['cls'] + '.' + sg['name']] = a
    if '>' in sg['name'] and not sg['name'].startswith('<'): SIGADDR[sg['cls'] + '.<' + sg['name']] = a
IB = {'MenuParts.IText': 'text', 'MenuParts.IIcon': 'icon', 'MenuParts.IButton': 'button', 'MenuParts.IFrame': 'frame', 'MenuParts.IBar': 'bar'}
CODES = (-1, 0, 1, 2, 3, 4, 5)
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
BUILDS = []
def _hook_build(uc, a, sz, ud):
    r = lambda n: uc.reg_read(n)
    this = r(UC_ARM64_REG_X0)
    if a == 0xd00f3c:     # Build(indent, screenIndent, x, y, z, parent)
        fl = lambda q: struct.unpack('<f', struct.pack('<I', r(q) & 0xffffffff))[0]
        BUILDS.append(dict(this=this, indent=r(UC_ARM64_REG_X1) & 0xffffffff, scr=r(UC_ARM64_REG_X2) & 0xffffffff,
                           xyz=[fl(UC_ARM64_REG_S0), fl(UC_ARM64_REG_S1), fl(UC_ARM64_REG_S2)], parent=r(UC_ARM64_REG_X3)))
    elif a == 0xcfb590:   # Build(indent, Vector3 pos, parent)
        fl = lambda q: struct.unpack('<f', struct.pack('<I', r(q) & 0xffffffff))[0]
        BUILDS.append(dict(this=this, indent=r(UC_ARM64_REG_X1) & 0xffffffff, scr=None,
                           xyz=[fl(UC_ARM64_REG_S0), fl(UC_ARM64_REG_S1), fl(UC_ARM64_REG_S2)], parent=r(UC_ARM64_REG_X2)))
for _a in (0xd00f3c, 0xcfb590): T.uc.hook_add(UC_HOOK_CODE, _hook_build, None, _a, _a)
FCALLS = {}
def _hook_frame(uc, a, sz, ud):   # IBase.Change(int) : this = IBase
    v = uc.reg_read(UC_ARM64_REG_X1) & 0xffffffff
    FCALLS[uc.reg_read(UC_ARM64_REG_X0)] = v - (1 << 32) if v & 0x80000000 else v
T.uc.hook_add(UC_HOOK_CODE, _hook_frame, None, 0xcfa704, 0xcfa704)      # MenuParts.IBase.Change(int)
TCALLS = []
def _hook_tc(uc, a, sz, ud):      # MenuParts.SetTextColor(this, code)
    TCALLS.append((uc.reg_read(UC_ARM64_REG_X0), uc.reg_read(UC_ARM64_REG_X1) & 0xffff))
T.uc.hook_add(UC_HOOK_CODE, _hook_tc, None, 0xcfdaa0, 0xcfdaa0)

def r4(x): return round(x, 3)
def cname(o):
    return T.kname.get(T.u(o, 8), '?').replace('_TypeInfo', '') if o else None
def ibases(parts):
    lo = T.u(parts + 0x58, 8); n = T.u(lo + 0x18, 4); arr = T.u(lo + 0x10, 8)
    return [T.u(arr + 0x20 + 8 * i, 8) for i in range(n)]
def f32(a): return struct.unpack('<f', bytes(T.uc.mem_read(a, 4)))[0]

def snapshot():
    out = {}
    for o, u in T.U.items():
        if u['kind'] != 'GameObject': continue
        e = dict(pos=[r4(x) for x in T.world(u['tr'])], act=bool(u.get('active', True)))
        for c in u['comps']:
            cu = T.U[c]
            if cu['kind'] == 'MeshFilter' and cu.get('mesh'):
                m = T.U[cu['mesh']]; e['mesh'] = (tuple(map(tuple, m['vtx'])), tuple(map(tuple, m['uv'])))
            elif cu['kind'] == 'MeshRenderer':
                e['mats'] = [(T.U[mm].get('shader'), tuple(T.U[mm].get('color') or ()), tuple(T.U[mm].get('offset') or ())) for mm in cu.get('mat', []) if mm in T.U]
            elif cu['kind'] == 'TextMesh':
                e['text'] = tuple(sorted((k, str(v)) for k, v in cu.items() if k not in ('kind', 'id', 'go')))
        out[o] = e
    return out
def restore(snap):
    for o, e in snap.items():
        u = T.U[o]; T.set_world(u['tr'], e['pos']); u['active'] = e['act']

def describe_ibase(ib, node_of_parts, goid):
    k = cname(ib)
    kind = IB.get(k, 'other')
    e = dict(k=kind, cls=k)
    ic = T.deleg.get(T.u(ib + 0x10, 8)); sc = T.deleg.get(T.u(ib + 0x18, 8))
    e['int'] = ic[1].replace('Method$', '') if ic else None
    e['str'] = sc[1].replace('Method$', '') if sc else None
    if kind == 'icon' and ic and ic[0]:
        tg = ic[0]; e.update(partsNo=T.u(tg + 0x18, 4), vtx=T.u(tg + 0x1c, 4))
    elif kind == 'text':
        for dd in (ic, sc):
            if dd and dd[0]:
                tg = dd[0]; nm = dd[1]
                if 'DisplayClass1_0' in nm:
                    e.update(go=goid(T.u(tg + 0x18, 8)), fsize=f32(tg + 0x20), variant=1)
                else:
                    e.update(go=goid(T.u(tg + 0x10, 8)), variant=0)
                break
    elif kind == 'bar':
        e.update(vtx=T.u(ib + 0x30, 4), zero=f32(ib + 0x34), width=f32(ib + 0x38))
    elif kind == 'frame':
        for dd in (ic, sc):
            if dd and dd[0]:
                e['go'] = goid(T.u(dd[0] + 0x10, 8))
                if ib in FCALLS: e['init'] = FCALLS[ib]
                break
    elif kind == 'other':
        # IBase personnalisé : champs objet lisibles (changeurs internes)
        e['fields'] = {'%#x' % off: T.u(ib + off, 8) for off in (0x28, 0x30)}
    return e

def export_type(typ):
    nm = R.tbl[typ]
    for o in [o for o, u in T.U.items() if u['kind'] == 'GameObject']: pass
    keep = set(T.U); T.tab = []; T.plist = []; T.deleg = {}; BUILDS.clear(); FCALLS.clear()
    err = T.run(R.addr[nm[:-2]], [7, typ])
    objs = {o: u for o, u in T.U.items() if o not in keep}
    gos = {o: u for o, u in objs.items() if u['kind'] == 'GameObject'}
    gid = {o: u['id'] for o, u in gos.items()}
    goid = lambda comp: gid.get(T.U[comp]['go'] if comp in T.U and 'go' in T.U[comp] else comp)
    nodes = []
    for o, u in gos.items():
        tr = u['tr']; par = T.U[tr]['parent']
        n = dict(id=u['id'], par=gid.get(T.U[par]['go']) if par else None, pos=[r4(x) for x in T.world(tr)], scale=[r4(x) for x in T.pscale(tr)], act=bool(u.get('active', True)))
        for c in u['comps']:
            cu = T.U[c]
            if cu['kind'] == 'MeshFilter' and cu.get('mesh'):
                m = T.U[cu['mesh']]
                if m['vtx']:
                    n['mesh'] = dict(vtx=[[v[0], v[2]] for v in m['vtx']], uv=[list(v) for v in m['uv']], sub={str(k): v for k, v in m['tris'].items()})
            elif cu['kind'] == 'MeshRenderer':
                n['mats'] = [dict(sheet=T.U[mm].get('sheet'), part=T.U[mm].get('part'), color=T.U[mm].get('color'), shader=T.U[mm].get('shader') if isinstance(T.U[mm].get('shader'), str) else None, offset=T.U[mm].get('offset')) for mm in cu.get('mat', []) if mm in T.U]
            elif cu['kind'] == 'TextMesh':
                n['text'] = {k: v for k, v in cu.items() if k not in ('kind', 'id', 'go')}
            elif cu['kind'] == 'MenuParts':
                n['parts'] = dict(nowParts=T.u(c + 0x20, 4, True), buttonId=T.u(c + 0x48, 2, True), gamepad=T.u(c + 0x4a, 2, True))
        nodes.append(n)
    bl = []
    for b in BUILDS:
        u = T.U.get(b['this'])
        if u and u.get('go') in gid: bl.append(dict(node=gid[u['go']], indent=b['indent'], scr=b['scr'], xyz=[r4(x) for x in b['xyz']], par=gid.get(T.U[b['parent']].get('go')) if b['parent'] in T.U else None))
    parts = []
    pidx = {}
    for i, pa in enumerate(T.plist):
        pidx[pa] = i
        u = T.U.get(pa); go = gid.get(u['go']) if u else None
        parts.append(dict(node=go, ib=[describe_ibase(ib, go, goid) for ib in ibases(pa)], _addr=[ib for ib in ibases(pa)]))
    # identifiants d'IBase -> (pièce, indice)
    where = {}
    for i, p in enumerate(parts):
        for j, ib in enumerate(p['_addr']): where[ib] = (i, j)
    params = []
    codes = []
    for e in T.tab:
        k = e['kind']
        if k == 'param': params.append(dict(id=e['id'], no=e['no'], parts=e['partsNo'], base=e['baseNo']))
        elif k == 'param_ibase':
            w = where.get(e['ibase'])
            if w: params.append(dict(id=e['id'], no=e['no'], parts=w[0], base=w[1]))
            else:
                cu_ = describe_ibase(e['ibase'], None, goid)
                if cu_.get('cls') in ('MenuPortItemTable.BattleBar', 'MenuPortItemTable.ItemNumCTRL'):
                    w2 = where.get(T.u(e['ibase'] + 0x28, 8))
                    if w2: cu_['wrap'] = dict(parts=w2[0], base=w2[1])
                params.append(dict(id=e['id'], no=e['no'], custom=cu_))
        elif k == 'param_textcolor': params.append(dict(id=e['id'], no=e['no'], textcolor=pidx.get(e['parts'])))
        elif k == 'code_parts': codes.append(dict(id=e['id'], kind='active', parts=e['partsNo']))
        elif k == 'code_func':
            dl = T.deleg.get(e['func']); c = dict(id=e['id'], kind='func', method=dl[1].replace('Method$', '') if dl else None)
            if dl and dl[1]:
                key = dl[1].replace('Method$', '').rstrip('()')
                a = SIGADDR.get(key)
                if a:
                    base = snapshot(); fx = {}
                    for code in CODES:
                        del TCALLS[:]
                        e2 = T.run(a, [dl[0], code & 0xffff, 0])
                        s2 = snapshot()
                        df = {}
                        for o, v in s2.items():
                            if o in base and v != base[o]:
                                dd = {kk: vv for kk, vv in v.items() if base[o].get(kk) != vv}
                                df[str(T.U[o]['id'])] = dd
                        fx[str(code)] = dict(err=e2, d=df)
                        if TCALLS: fx[str(code)]['tc'] = [dict(parts=pidx.get(pa_), mask=T.u(pa_ + 0x50, 4), color=(cc - 0x10000 if cc & 0x8000 else cc)) for pa_, cc in TCALLS]
                        restore(base)
                    c['fx'] = fx
            codes.append(c)
    for p in parts: p.pop('_addr')
    return dict(name=nm, err=err, nodes=nodes, parts=parts, params=params, codes=codes, builds=bl)

def jsonable(o):
    if isinstance(o, tuple): return [jsonable(x) for x in o]
    if isinstance(o, dict): return {k: jsonable(v) for k, v in o.items()}
    if isinstance(o, list): return [jsonable(x) for x in o]
    return o
if __name__ == '__main__':
    only = [int(a) for a in sys.argv[2:]] if len(sys.argv) > 2 else None
    out = {}
    for typ in range(len(R.tbl)):
        if R.tbl[typ][:-2] not in R.addr: continue
        if only and typ not in only: continue
        try: out[str(typ)] = export_type(typ)
        except Exception as e: out[str(typ)] = dict(name=R.tbl[typ], err='EXC ' + repr(e)[:200]); print(typ, 'EXC', repr(e)[:200])
    json.dump(jsonable(out), open(sys.argv[1], 'w'))
    bad = {k: v['err'] for k, v in out.items() if v.get('err')}
    print(len(out), 'types, erreurs:', bad)
