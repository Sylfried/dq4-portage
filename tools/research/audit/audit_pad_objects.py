"""Localise dans datapack.unity3d les SphereCollider / MonoBehaviour (candidats : objet TouchPad) et affiche leur GameObject, hierarchie, maillages."""
import zipfile, UnityPy, sys
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks/'
z = zipfile.ZipFile(APK + 'split_UnityDataAssetPack.apk')
env = UnityPy.load(z.read('assets/bin/Data/datapack.unity3d'))
for k, v in env.files.items():
    print(k, type(v).__name__, len(getattr(v, 'objects', {}) or {}))
    for k2, v2 in getattr(v, 'files', {}).items():
        print('   ', k2, type(v2).__name__, len(getattr(v2, 'objects', {}) or {}))
for o in env.objects:
    if o.type.name in ('SphereCollider', 'MonoBehaviour', 'MeshCollider'):
        r = o.read()
        gname = None
        try: gname = r.m_GameObject.read().m_Name
        except Exception as e: gname = '?' + str(e)
        print(o.type.name, o.path_id, 'GO=', gname, {k: v for k, v in (r.__dict__ if hasattr(r, '__dict__') else {}).items() if k.startswith('m_') and k not in ('m_GameObject',)} if o.type.name != 'MonoBehaviour' else '')
