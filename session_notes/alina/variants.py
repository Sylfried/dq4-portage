import os, sys, tempfile
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
pre = int(sys.argv[1]); post = int(sys.argv[2]); n = int(sys.argv[3])
folder = tempfile.mkdtemp(prefix='sv_alina_')
m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], folder)
for _ in range(pre): m.step(0, 0)
print('load', m.load_save(1))
for _ in range(post): m.step(0, 0)
prev = None
for i in range(n):
    m.step(0, 0)
    e = m.state
    if e.game_map != prev: print('step', i + 1, 'frames', m.frames, 'map', e.game_map, 'music', e.music); prev = e.game_map
