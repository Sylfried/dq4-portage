"""Sonde 2 : textes des actions (TextAPI::getMessage)."""
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
u32 = lambda a: struct.unpack('<I', c.mem(a, 4))[0]
buf = c.malloc(0x2000)
def msg(i):
    c.mem_w(buf, b'\0' * 0x200)
    r = c.call(eng.E('_ZN7TextAPI10getMessageEPci'), buf, i, label='gm')
    raw = c.mem(buf, 0x200); n = raw.find(b'\0')
    try: return raw[:n].decode('utf-8', 'replace')
    except Exception: return raw[:n].hex()
print(eng.E('_ZN7TextAPI14isExistMessageEi'))
for i in (0xcaa56, 0xcaa57, 0xcaa58, 0xc3938, 0xc3926, 0xc3928, 0xc3922, 0xc3924, 0xc3a67, 0xc3d71):
    print(hex(i), repr(msg(i)))
