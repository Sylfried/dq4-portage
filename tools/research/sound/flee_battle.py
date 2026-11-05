"""Fuite en combat : bouton « Fuir » du menu racine ; usage flee_battle.py [nb essais de seed] """
import sys
sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
eng = new('fuite'); c = eng.core; tr = Trace(eng)
eng.load_save(1)
for _ in range(200): eng.step(0, 0)
tr.evt.clear(); eng.sensor.drain()
cb = Battle(eng, tr, monsters=[(3, 3), (4, 3)], hp=[999, 999], verbose=True)
state = {'vu': set()}
def before(cb_, k):
    port = eng.active_menu()
    if port is not None and not eng.msg_visible and port not in state['vu']:
        state['vu'].add(port); print('   MENU port', port, eng.ui.f[port].get('type'), {a: b[:12] for a, b in eng.ui.f[port]['cases'].items()})
cb.button = {30: 3}
cb.launch(max_step=1500, before_loop=before, after_battle=200)
