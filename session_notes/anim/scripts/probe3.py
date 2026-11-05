"""Sonde 3 : balayage des messages (ids) pour retrouver les noms des actions."""
import sys, os, struct, tempfile, json, time
os.environ.update(PYGLET_HEADLESS='1', PYGLET_AUDIO='silent', PYTHONDONTWRITEBYTECODE='1')
os.environ.setdefault('DQ4_DATA', '/tmp/anim_data')
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735'
eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_anim_'))
c = eng.core
buf = c.malloc(0x2000)
gm = eng.E('_ZN7TextAPI10getMessageEPci'); ie = eng.E('_ZN7TextAPI14isExistMessageEi')
def msg(i):
    c.mem_w(buf, b'\0' * 0x100)
    c.call(gm, buf, i, label='gm')
    raw = c.mem(buf, 0x100); n = raw.find(b'\0')
    return raw[:n].decode('utf-8', 'replace')
lo, hi = int(sys.argv[1], 0), int(sys.argv[2], 0)
out = {}
t0 = time.time()
for i in range(lo, hi):
    m = msg(i)
    if m != 'not found.': out[i] = m
print('n', len(out), 'temps %.1f' % (time.time() - t0), flush=True)
json.dump(out, open(sys.argv[3], 'w'), ensure_ascii=False)
