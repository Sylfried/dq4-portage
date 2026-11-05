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
for i in (1003012, 1003013, 1003014, 830056, 801080, 1000001):
    c.mem_w(buf, b'\xaa' * 0x80); r = c.call(gm, buf, i, label='gm'); print(i, hex(r) if r is not None else r, c.mem(buf, 0x40))
