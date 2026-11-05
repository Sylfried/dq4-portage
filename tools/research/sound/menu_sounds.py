import sys
sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
sys.path.insert(0, '/home/claude/wt45-son/dq4_pc')
eng = new('ms'); c = eng.core
buf = c.malloc(0x40)
fn = c.export('_ZN16MenuSoundManager12setPlaySoundENS_10MENU_SOUNDE')
print('fn', fn)
for n in range(0, 17):
    c.mem_w(buf, b'\0' * 0x40)
    c.call(fn, buf, n, label='sps')
    v = struct.unpack('<8i', c.mem(buf, 32))
    print('MENU_SOUND %2d : state=%d BGM=%d  start(frame)=%d  end(frame)=%d  counter=%d  stop=%d' % (n, v[0], v[1], v[2], v[3], v[4], v[5]))
