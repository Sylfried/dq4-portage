import sys, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.world.data import Data
d = Data('/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks/split_UnityDataAssetPack.apk', sys.argv[1])
gos = d._gos(); no = int(sys.argv[2]); pid = gos['c%04d' % no]
root = d._objs[pid].read(); seen = set()
def visit(g):
    comps = d._components(g)
    for k in ('SkinnedMeshRenderer', 'MeshRenderer'):
        if k in comps:
            r = comps[k].read()
            for mref in r.m_Materials:
                mat = mref.deref_parse_as_object(); sh = mat.m_Shader.deref_parse_as_object()
                if sh.m_ParsedForm.m_Name in seen: continue
                seen.add(sh.m_ParsedForm.m_Name); pf = sh.m_ParsedForm
                print('shader', pf.m_Name, 'props', [(p.m_Name, int(p.m_Type)) for p in pf.m_PropInfo.m_Props])
                for ss in pf.m_SubShaders:
                    print(' subshader tags', {t[0]: t[1] for t in ss.m_Tags.tags} if hasattr(ss.m_Tags, 'tags') else ss.m_Tags, 'LOD', ss.m_LOD)
                    for p in ss.m_Passes:
                        st = p.m_State; print('  attrs', [a for a in dir(st) if not a.startswith('_')]); b = st.rtBlend0; print('  rtBlend0', {a: getattr(getattr(b, a), 'val', getattr(b, a)) for a in dir(b) if not a.startswith('_')})
                        def v(x): return getattr(x, 'val', x)
                        print('  pass state: rgbaBlend', v(st.rgbaBlend) if hasattr(st, 'rgbaBlend') else None, 'srcBlend', v(st.srcBlend) if hasattr(st,'srcBlend') else None, 'dstBlend', v(st.destBlend) if hasattr(st,'destBlend') else None,
                              'zwrite', v(st.zWrite), 'ztest', v(st.zTest), 'cull', v(st.culling), 'alphaTest', v(st.alphaTest) if hasattr(st,'alphaTest') else None, 'tags', {t[0]: t[1] for t in p.m_State.m_Tags.tags} if hasattr(p.m_State.m_Tags,'tags') else None)
                        print('   name', p.m_State.m_Name, 'lighting', v(st.lighting) if hasattr(st,'lighting') else None)
                print(' material colors', [(kk, [round(c.r,2),round(c.g,2),round(c.b,2),round(c.a,2)]) for kk, c in mat.m_SavedProperties.m_Colors], 'floats', [(kk, vv) for kk, vv in mat.m_SavedProperties.m_Floats], 'renderQueue', getattr(mat, 'm_CustomRenderQueue', None))
    t = comps['Transform'].read()
    for ch in t.m_Children: visit(d._objs[ch.deref_parse_as_object().m_GameObject.path_id].read())
visit(root)
