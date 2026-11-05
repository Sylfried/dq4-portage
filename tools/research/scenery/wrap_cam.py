import sys, os
sys.path.insert(0, '/home/claude/wt45-decor/dq4_pc')
from dq4_pc.window import game as F
orig = F.Game._draw_scene
n = [0]
def patched(self):
    e = self.engine.state
    n[0] += 1
    if n[0] in (30, 60, 100): print('CAMLOG', n[0], e.game_map, e.cam_pos, e.cam_target, e.cam_fov, e.cam_down, flush=True)
    return orig(self)
F.Game._draw_scene = patched
F.main()
