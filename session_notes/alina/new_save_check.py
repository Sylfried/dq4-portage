import os, sys, tempfile
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], tempfile.mkdtemp(prefix='sv_alina_'))
for _ in range(3): m.step(0, 0)
m.load_save(1)
for i in range(1, 400):
    m.step(0, 0)
    if i in (30, 60, 399): print(i, m.state.game_map, 'msg', m.msg_visible, 'flags', hex(m.flags()), 'sprites', {k: (s['id'], s['dir']) for k, s in m.state.sprites.items()})
