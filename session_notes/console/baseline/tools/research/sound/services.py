"""Services en ville (eglise, auberge...) avec trace des sons. usage: services.py PHASE "suite de touches" [slot] [indices_morts]"""
import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
phase = int(sys.argv[1]); key_list = sys.argv[2].split(',') if len(sys.argv) > 2 and sys.argv[2] else []
slot = int(sys.argv[3]) if len(sys.argv) > 3 else 1
deaths = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 and sys.argv[4] else []
LOOP_COUNT = int(sys.argv[5]) if len(sys.argv) > 5 else 1500
eng = new('srv'); c = eng.core; tr = Trace(eng)
eng.load_save(slot)
for _ in range(250): eng.step(0, 0)
party = c.export('_ZN6status7g_PartyE')
for i in deaths: set_hp(eng, i, 0)
print('membres', members(eng), [hit_points(eng, i)[0] for i in members(eng)])
PARTY_GOLD = 1
c.mem_w(party + 0x2e0, struct.pack('<I', 3000))
tr.evt.clear(); eng.sensor.drain()
tws = eng.E('_ZN16TownWindowSystem11m_singletonE')
mm = c.call(eng.E('_ZN27MaterielMenu_WINDOW_MANAGER12getSingletonEv'), label='mm')
c.mem_w(mm + 0x10, struct.pack('<i', 0))
c.call(eng.E('_ZN6window13CommandWindow19changeShopMenuPhaseEi'), tws, phase, label='phase')
BT = {'A': 0x10, 'B': 0x20, 'U': 2, 'D': 1, 'L': 8, 'R': 4}
ev0 = 0; waiting = 0; rel = None; k = 0; vu = None; ph0 = None
for i in range(LOOP_COUNT):
    p = d = 0
    if rel is not None: eng.send_menu(rel, 1, -1, 0); rel = None
    port = eng.active_menu()
    att_msg = eng.msg_visible and (eng.ui.msg.get('feed') or eng.message_state()[1] in (3, 5))
    if port is not None or att_msg:
        waiting += 1
        if waiting % 6 == 0:
            if port is None and att_msg: p = d = ENGINE.A
            elif k < len(key_list):
                t = key_list[k]; k += 1
                print('%5d TOUCHE %s sur port %s type %s cases %s cur %s' % (eng.frames, t, port, eng.ui.f[port].get('type'), {a: b[:14] for a, b in list(eng.ui.f[port]['cases'].items())[:8]}, eng.ui.f[port].get('cur')))
                if t.startswith('#'): eng.send_menu(port, 1, int(t[1:]), 0x10)
                else: eng.send_menu(port, 1, -1, BT[t])
                rel = port
    else: waiting = 0
    if i % 100 == 0 and os.environ.get('DBGM'): print('   dbg', eng.frames, 'port', port, 'msg', eng.msg_visible, 'att_msg', att_msg, 'actifs', [(q, f.get('type'), f['vis'], f.get('entree')) for q, f in eng.ui.f.items() if q > 1 and f.get('act')])
    prev = eng.state.part; pkt = eng.step(p, d)
    for t, v in pkt_sounds(pkt): print('%5d  SON %s' % (eng.frames, {35: 'SE %d', 36: 'stopSE %d', 37: 'BGM %#x'}[t] % v))
    for e in tr.evt[ev0:]: print('%5d  appel %s(%d) <- %s' % (e[0], e[1], e[2], ' < '.join(x.split('+')[0] for x in e[3][:4])))
    ev0 = len(tr.evt)
    for s in eng.sensor.drain(): print('%5d  texte %r' % (eng.frames, s['texte'][:100]))
    pp = [hit_points(eng, j)[0][0] for j in members(eng)]
    if pp != ph0: ph0 = pp; print('%5d  pv %s' % (eng.frames, pp))
    if eng.state.part != prev: print('%5d  partie %#x -> %#x' % (eng.frames, prev, eng.state.part))
