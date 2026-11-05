"""Hierarchie des GameObjects 'MPad' du datapack (composants, transformations, maillages, materiaux)."""
import zipfile, UnityPy, sys, pickle
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks/'
z = zipfile.ZipFile(APK + 'split_UnityDataAssetPack.apk')
env = UnityPy.load(z.read('assets/bin/Data/datapack.unity3d'))
objs = {}
for o in env.objects: objs[o.path_id] = o
from collections import Counter
print(Counter(o.type.name for o in env.objects).most_common(30))
def show(pid, ind=0):
    g = objs[pid].read()
    t = g.m_Transform if hasattr(g, 'm_Transform') else None
    print(' '*ind + 'GO', pid, repr(g.m_Name))
    for c in g.m_Components:
        cp = c.component if hasattr(c, 'component') else c
        o = cp.deref() if hasattr(cp, 'deref') else cp
        r = o.read()
        info = ''
        if o.type.name == 'Transform':
            info = 'pos=%s scl=%s rot=%s' % (r.m_LocalPosition, r.m_LocalScale, r.m_LocalRotation)
            print(' '*ind + ' ', o.type.name, info)
            for ch in r.m_Children: show(ch.deref().read().m_GameObject.deref().path_id if False else ch.deref().read().m_GameObject.path_id, ind + 4)
            continue
        print(' '*ind + ' ', o.type.name, info)
for pid in (7,):
    show(pid)
