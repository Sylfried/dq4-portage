"""Sonde 4 : lit les messages des tables b08xxxxx (noms, descriptions, messages d'execution) en ne visitant que les plages declarees dans les en-tetes MPT."""
import sys, os, struct, tempfile, json, time, zipfile
os.environ.update(PYGLET_HEADLESS='1', PYGLET_AUDIO='silent', PYTHONDONTWRITEBYTECODE='1')
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735'
z = zipfile.ZipFile(APK + '/split_UnityDataAssetPack.apk')
ranges = []
for n in z.namelist():
    if '/msg/en/b08' in n and n.endswith('.mpt'):
        d = z.read(n); sz, a, b, cnt = struct.unpack('<IIII', d[4:20]); ranges.append((a, b))
eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_anim_'))
c = eng.core
buf = c.malloc(0x2000)
gm = eng.E('_ZN7TextAPI10getMessageEPci')
def msg(i):
    c.mem_w(buf, b'\0' * 0x100)
    c.call(gm, buf, i, label='gm')
    raw = c.mem(buf, 0x100); n = raw.find(b'\0')
    return raw[:n].decode('utf-8', 'replace')
out = {}; t0 = time.time()
for a, b in ranges:
    for i in range(a, b + 1):
        m = msg(i)
        if m != 'not found.': out[i] = m
    print(a, len(out), '%.1f' % (time.time() - t0), flush=True)
json.dump(out, open(sys.argv[1], 'w'), ensure_ascii=False)
