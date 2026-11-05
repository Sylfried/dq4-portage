"""Cherche dans data.unity3d (base.apk) et datapack.unity3d les objets lies a TouchPad : MonoBehaviour(TouchPad), GameObjects Pad / Map Button, maillages, etc."""
import sys, os, zipfile, io
import UnityPy
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks/'
def load(apk, inner):
    z = zipfile.ZipFile(APK + apk); return UnityPy.load(z.read(inner))
env = load('base.apk', 'assets/bin/Data/data.unity3d')
from collections import Counter
print(Counter(o.type.name for o in env.objects))
for o in env.objects:
    if o.type.name == 'MonoBehaviour':
        try:
            t = o.read(); sc = t.m_Script.read().m_ClassName if t.m_Script else None
        except Exception as e: sc = '?' + str(e)
        print('MB', o.path_id, sc)
    elif o.type.name == 'GameObject':
        print('GO', o.path_id, o.read().m_Name)
