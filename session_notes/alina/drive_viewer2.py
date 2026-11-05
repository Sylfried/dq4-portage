"""Visionneuse (sans fenetre) : charge l'etat 1 (toit), fait marcher Alina vers la gauche jusqu'a la scene des compagnons, appuie sur A quand un message est affiche ; journal de chaque pas du moteur
(dir / pose de chaque personnage) ET de chaque case (col, rangee) que la visionneuse choisit pour dessiner, avec l'image du moteur au moment du dessin."""
import os, sys, math, json
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.window import game as G
from dq4_pc.world import hd as HD
from dq4_pc.core import engine as ENGINE
LOG = open(os.environ['ALINA_LOG'], 'w')
st = {'game': None, 'k': -1, 'locked': False, 'draws': [], 'ndraw': 0}
orig_uv = HD.uv_cell
def uv(f, col, row):
    g = st['game']
    st['draws'].append((g.engine.frames if g else None, col, row, f.get('nl'), f.get('tw'), f.get('th'))); return orig_uv(f, col, row)
HD.uv_cell = uv
def pad(self):
    k = st['k']
    if k < 0: return 0
    e = self.engine
    if not st['locked'] and e.flags() & ENGINE.PLAYER_LOCKED_FLAG: st['locked'] = True
    if not st['locked']: return ENGINE.LEFT if k >= 33 else 0
    return ENGINE.A if (e.msg_visible and (k % 12) < 3) else 0
G.Game.pad = pad
orig_tick = G.Game.tick
def tick(self, dt, mute=False):
    st['game'] = self
    if st['k'] < 0:
        self.load_state(1); st['k'] = 0
    st['k'] += 1
    orig_tick(self, dt, mute)
    e = self.engine.state
    cap = None
    if e.cam_pos is not None and e.cam_target is not None: cap = round(math.degrees(math.atan2(e.cam_target[0] - e.cam_pos[0], e.cam_target[2] - e.cam_pos[2])), 3)
    sp = {str(k): [s['id'], s['pose'], s['dir'], s.get('vis', True)] for k, s in sorted(e.sprites.items())}
    LOG.write(json.dumps({'k': st['k'], 'n': self.n, 'frames': self.engine.frames, 'map': e.game_map, 'msg': bool(self.engine.msg_visible), 'cap': cap, 'sp': sp, 'music': e.music, 'draws': st['draws']}) + '\n'); LOG.flush()
    st['draws'] = []
G.Game.tick = tick
from dq4_pc.main import main
main(sys.argv[1:])
