"""Scenarios de combat : usage battle_scenario.py SCENARIO ; SCENARIO = niveau | fuite | boss"""
import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
sc = sys.argv[1]
eng = new('sc_' + sc); c = eng.core; tr = Trace(eng)
eng.load_save(1)
for _ in range(200): eng.step(0, 0)
orig = c.export('_ZN6status9PartyData15originalPlayer_E')
if sc == 'niveau':
    for i in (3, 12):
        hs = orig + PLAYER_STRIDE * i + OFF_HS
        need = struct.unpack_from('<I', c.mem(hs, 0x30), 0x18)[0]
        print('member', i, 'xp required', need)
        if need > 0: c.mem_w(hs + 8, struct.pack('<I', need - 1))
tr.evt.clear(); eng.sensor.drain()
cb = Battle(eng, tr, monsters=[(3, 1)] if sc != 'fuite' else [(3, 4), (4, 4)], hp=None, verbose=True)
if sc == 'fuite':
    orig_launch = cb.launch
    # on envoie le bouton « Fuir » (n°2 ?) sur le menu racine du combat (port 13, type 30)
    def before(cb_, k):
        pass
    end = cb.launch(max_step=3000, after_battle=300)
else:
    end = cb.launch(max_step=3000, after_battle=300)
