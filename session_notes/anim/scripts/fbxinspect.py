"""Inspecte les modeles fbx demandes par les effets de combat : arbre, composants, maillages, materiaux (shader, proprietes), clips (type de courbes)."""
import sys, os, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.world.data import Data
d = Data('/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks/split_UnityDataAssetPack.apk', sys.argv[1])
gos = d._gos()
out = {}
for no in [int(x) for x in sys.argv[2:]]:
    nm = 'c%04d' % no
    pid = gos.get(nm)
    if pid is None: print(no, 'ABSENT'); out[no] = None; continue
    info = dict(nodes=0, smr=0, mr=0, meshes=[], shaders=set(), clips={}, comps=set(), tex=[])
    def visit(g, depth=0):
        comps = d._components(g); info['nodes'] += 1
        info['comps'].update(comps.keys())
        for k in ('SkinnedMeshRenderer', 'MeshRenderer'):
            if k in comps:
                r = comps[k].read(); info['smr' if k[0] == 'S' else 'mr'] += 1
                for mref in r.m_Materials:
                    try:
                        mat = mref.deref_parse_as_object(); sh = mat.m_Shader.deref_parse_as_object().m_ParsedForm.m_Name; info['shaders'].add(sh)
                        props = {kk: [round(c.r, 2), round(c.g, 2), round(c.b, 2), round(c.a, 2)] for kk, c in mat.m_SavedProperties.m_Colors}
                        texn = []
                        for kk, v in mat.m_SavedProperties.m_TexEnvs:
                            if v.m_Texture.path_id:
                                t = v.m_Texture.deref_parse_as_object(); texn.append((kk, t.m_Name, t.m_Width, t.m_Height))
                        info['tex'].append((g.m_Name, sh, props, texn))
                    except Exception as ex: info['tex'].append((g.m_Name, 'ERR', str(ex)))
                try:
                    mesh = (r.m_Mesh if k[0] == 'S' else comps['MeshFilter'].read().m_Mesh).deref_parse_as_object()
                    info['meshes'].append((g.m_Name, mesh.m_Name, int(mesh.m_VertexData.m_VertexCount) if hasattr(mesh, 'm_VertexData') else None))
                except Exception as ex: info['meshes'].append((g.m_Name, 'ERR', str(ex)))
        if 'Animation' in comps and not info['clips']:
            for cref in comps['Animation'].read().m_Animations:
                c = cref.deref_parse_as_object()
                info['clips'][c.m_Name] = dict(wrap=int(c.m_WrapMode), comp=bool(getattr(c, 'm_Compressed', False)), pos=len(c.m_PositionCurves), rot=len(c.m_RotationCurves), scl=len(c.m_ScaleCurves), flt=len(c.m_FloatCurves), dur=round(max([k.time for q in list(c.m_PositionCurves) + list(c.m_RotationCurves) + list(c.m_ScaleCurves) for k in q.curve.m_Curve] + [k.time for q in c.m_FloatCurves for k in q.curve.m_Curve] + [0]), 2),
                                           flt_attrs=sorted({(q.attribute, q.path) for q in c.m_FloatCurves})[:6])
        t = comps['Transform'].read()
        for ch in t.m_Children:
            cg = d._objs[ch.deref_parse_as_object().m_GameObject.path_id].read(); visit(cg, depth + 1)
    root = d._objs[pid].read(); visit(root)
    info['shaders'] = sorted(info['shaders']); info['comps'] = sorted(info['comps'])
    out[no] = info
    print(no, json.dumps(info, default=str, ensure_ascii=False)[:1500], flush=True)
