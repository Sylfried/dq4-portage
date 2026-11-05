"""Sonde 7 : table des actions (700 lignes) -> description, message d'execution (textes rendus par le moteur)."""
import sys, os, struct, tempfile, json
os.environ.update(PYGLET_HEADLESS='1', PYGLET_AUDIO='silent', PYTHONDONTWRITEBYTECODE='1')
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735'
eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_anim_'))
c = eng.core
buf = c.malloc(0x2000)
gm = eng.E('_ZN7TextAPI10getMessageEPci')
def msg(i):
    c.mem_w(buf, b'\0' * 0x200); c.call(gm, buf, i, label='gm')
    raw = c.mem(buf, 0x200); n = raw.find(b'\0'); return raw[:n].decode('utf-8', 'replace')
import zipfile
z = zipfile.ZipFile(APK + '/split_UnityDataAssetPack.apk'); rng = []
for n in z.namelist():
    if '/msg/en/b' in n and n.endswith('.mpt'):
        d = z.read(n)
        if d[:4] == b'MPT0': sz, a, b, cnt = struct.unpack('<IIII', d[4:20]); rng.append((a, b))
def exists(i): return any(a <= i <= b for a, b in rng)
rows = json.load(open('out/actions_raw.json'))['rows']
res = {}
for k, h in enumerate(rows):
    b = bytes.fromhex(h)
    ex = struct.unpack('<I', b[0:4])[0]; desc = struct.unpack('<I', b[0x20:0x24])[0]; eff = struct.unpack('<H', b[0x26:0x28])[0]
    res[k] = dict(exec=ex, desc=desc, eff=eff, mp=b[0x3a], row=h, exec_txt=msg(ex) if ex and exists(ex) else '', desc_txt=msg(desc) if desc and exists(desc) else '')
json.dump(res, open('out/actions_txt.json', 'w'), ensure_ascii=False)
print(len(res))
