"""Scene level1 du datapack (celle du TouchPad : MainCamera + MPad ...). Liste GameObjects / Transform / Renderer / Mesh / Material et decode les PPtr de la MonoBehaviour TouchPad."""
import zipfile, UnityPy, sys, struct, pickle, json
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks/'
z = zipfile.ZipFile(APK + 'split_UnityDataAssetPack.apk')
env = UnityPy.load(z.read('assets/bin/Data/datapack.unity3d'))
lv = [v for v in env.files.values() if hasattr(v, 'files')][0].files['level1']
objs = lv.objects
print('objets level1 :', len(objs))
names = {}
for pid, o in objs.items():
    if o.type.name == 'GameObject': names[pid] = o.read().m_Name
for pid, o in sorted(objs.items()):
    t = o.type.name
    if t == 'GameObject':
        g = o.read()
        print('GO %d %r comps=%s' % (pid, g.m_Name, [(c.component.m_PathID if hasattr(c, 'component') else c.m_PathID) for c in g.m_Components]))
    elif t == 'Transform':
        r = o.read()
        print('  Transform %d go=%d pos=%s scl=%s rot=%s father=%s' % (pid, r.m_GameObject.m_PathID, tuple(round(x, 4) for x in (r.m_LocalPosition.x, r.m_LocalPosition.y, r.m_LocalPosition.z)), tuple(round(x, 4) for x in (r.m_LocalScale.x, r.m_LocalScale.y, r.m_LocalScale.z)), tuple(round(x, 4) for x in (r.m_LocalRotation.x, r.m_LocalRotation.y, r.m_LocalRotation.z, r.m_LocalRotation.w)), r.m_Father.m_PathID))
    elif t in ('MeshRenderer', 'MeshFilter', 'SphereCollider', 'MeshCollider', 'Camera'):
        r = o.read()
        extra = ''
        if t == 'MeshRenderer': extra = 'enabled=%s materials=%s' % (r.m_Enabled, [(m.m_FileID, m.m_PathID) for m in r.m_Materials])
        if t == 'MeshFilter': extra = 'mesh=(%d,%d)' % (r.m_Mesh.m_FileID, r.m_Mesh.m_PathID)
        if t == 'SphereCollider': extra = 'radius=%s center=%s' % (r.m_Radius, r.m_Center)
        print('  %s %d go=%d %s' % (t, pid, r.m_GameObject.m_PathID, extra))
    elif t == 'MonoBehaviour':
        raw = o.get_raw_data()
        print('  MonoBehaviour %d len=%d' % (pid, len(raw)))
        print('   hex', raw.hex())
