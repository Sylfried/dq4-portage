"""Lance la visionneuse (headless) et journalise a chaque pas du moteur : carte, sprites (pose, dir), camera ; et a chaque dessin la rangee (col, row) choisie pour chaque sprite."""
import os, sys, math, json
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.window import game as G
from dq4_pc.world import hd as HD
from dq4_pc.core import engine as ENGINE
LOG = open(os.environ['ALINA_LOG'], 'w')
cur = {'n': None, 'draws': []}
orig_uv = HD.uv_cell
def uv(f, col, row):
    cur['draws'].append((col, row, f.get('tw'), f.get('th'))); return orig_uv(f, col, row)
HD.uv_cell = uv
orig_step = ENGINE.Engine.step
snd = []
def step(self, held=0, decl=None):
    pkt = orig_step(self, held, decl)
    snd[:] = [(t, a[0]) for t, a, f in pkt if t in (35, 36, 37) and a]
    return pkt
ENGINE.Engine.step = step
orig_tick = G.Game.tick
def tick(self, dt, mute=False):
    orig_tick(self, dt, mute)
    e = self.engine.state
    cap = None
    if e.cam_pos is not None and e.cam_target is not None: cap = round(math.degrees(math.atan2(e.cam_target[0] - e.cam_pos[0], e.cam_target[2] - e.cam_pos[2])), 3)
    sp = {str(k): [s['id'], s['pose'], s['dir'], None if s['pos'] is None else [round(float(x), 2) for x in s['pos']], s.get('vis', True)] for k, s in sorted(e.sprites.items())}
    LOG.write(json.dumps({'n': self.n, 'frames': self.engine.frames, 'map': e.game_map, 'msg': bool(self.engine.msg_visible), 'cap': cap, 'sp': sp, 'snd': list(snd), 'music': e.music, 'draws_since_last': cur['draws']}) + '\n'); LOG.flush()
    cur['draws'] = []
G.Game.tick = tick
from dq4_pc.main import main
main(sys.argv[1:])
