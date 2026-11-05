"""Sonde 1 : demarre le vrai moteur (sans fenetre), lit la table des actions (excelParam + 0x70, 0x48 octets) et les textes."""
import sys, os, struct, tempfile, json, time
os.environ.update(PYGLET_HEADLESS='1', PYGLET_AUDIO='silent', PYTHONDONTWRITEBYTECODE='1')
os.environ.setdefault('DQ4_DATA', '/tmp/anim_data')
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
APK = os.environ.get('DQ_APK', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks')
SAVES = os.environ.get('DQ_SAVES', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735')
OUT = sys.argv[1]
t0 = time.time()
eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_anim_'))
print('moteur pret en %.1f s' % (time.time() - t0), flush=True)
c = eng.core
u32 = lambda a: struct.unpack('<I', c.mem(a, 4))[0]; u64 = lambda a: struct.unpack('<Q', c.mem(a, 8))[0]
exc = c.export('_ZN6status10excelParamE')
print('excelParam symbole', hex(exc), 'valeur', hex(u64(exc)), flush=True)
base = u64(exc + 0x70)
print('table des actions', hex(base), flush=True)
rows = []
N = 700
raw = c.mem(base, 0x48 * N)
for i in range(N): rows.append(raw[0x48 * i:0x48 * (i + 1)].hex())
json.dump(dict(base=base, rows=rows), open(OUT, 'w'))
print('ecrit', OUT)
