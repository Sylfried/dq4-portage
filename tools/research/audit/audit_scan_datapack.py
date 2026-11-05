"""Cherche dans datapack.unity3d : GameObjects dont le nom contient pad / touch / button, MonoBehaviours dont le script est TouchPad, textures Button / MenuTexture."""
import sys, os, zipfile, pickle
import UnityPy
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks/'
z = zipfile.ZipFile(APK + 'split_UnityDataAssetPack.apk')
print([n for n in z.namelist() if 'unity3d' in n])
env = UnityPy.load(z.read('assets/bin/Data/datapack.unity3d'))
import re
rx = re.compile(r'pad|touch|button|rot|mpad|move', re.I)
n = 0
for o in env.objects:
    t = o.type.name
    if t == 'GameObject':
        g = o.read()
        if rx.search(g.m_Name): print('GO', o.path_id, g.m_Name); n += 1
    elif t == 'MonoBehaviour':
        try:
            mb = o.read(); s = mb.m_Script.read()
            if s.m_ClassName in ('TouchPad', 'MenuParts', 'PortalButton'): print('MB', o.path_id, s.m_ClassName); n += 1
        except Exception: pass
    elif t == 'Texture2D':
        g = o.read()
        if rx.search(g.m_Name) or g.m_Name in ('common', 'MenuTexture', 'Button'): print('TEX', o.path_id, g.m_Name, g.m_Width, g.m_Height)
print(n)
