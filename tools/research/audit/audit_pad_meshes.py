"""Maillages du TouchPad (scene level1 du datapack) : sommets + UV (en pixels de la feuille 'Button' 512x512), materiau."""
import zipfile, UnityPy, sys, struct, json
from UnityPy.helpers.MeshHelper import MeshHandler
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks/'
z = zipfile.ZipFile(APK + 'split_UnityDataAssetPack.apk')
env = UnityPy.load(z.read('assets/bin/Data/datapack.unity3d'))
bundle = [v for v in env.files.values() if hasattr(v, 'files')][0]
lv = bundle.files['level1']; res = bundle.files['resources.assets']
print('externals level1:', [getattr(e, 'path', e) for e in getattr(lv, 'externals', [])])
names = {'MPad(ring)': 16515, 'CurNomal': 18969, 'DirNormal': 17830, 'Dirs': 17199, 'CurLight': 19987, 'CurBS': 19498, 'DirLight': 18415}
for n, pid in names.items():
    o = res.objects[pid]; m = o.read(); h = MeshHandler(m); h.process()
    v = h.m_Vertices; uv = h.m_UV0
    print('=== %s mesh %d %r  verts=%d tris=%d submeshes=%d' % (n, pid, m.m_Name, len(v), len(h.get_triangles()[0]) if h.get_triangles() else -1, len(h.get_triangles())))
    for i in range(len(v)):
        print('   %2d  xyz=(%8.3f %8.3f %8.3f)  uv=(%.5f %.5f) -> px(%6.1f %6.1f)' % (i, v[i][0], v[i][1], v[i][2], uv[i][0], uv[i][1], uv[i][0]*512, (1-uv[i][1])*512))
    pass
# materiau
mt = res.objects[1].read()
print('material 1:', mt.m_Name, mt.m_Shader)
for k, v in mt.m_SavedProperties.m_TexEnvs.items() if hasattr(mt.m_SavedProperties, 'm_TexEnvs') else []:
    print('  tex', k, v)
