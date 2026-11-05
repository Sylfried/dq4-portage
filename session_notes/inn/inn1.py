import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
phase = int(os.environ.get('PHASE', 0)); slot = int(os.environ.get('SLOT', 1)); N = int(os.environ.get('N', 1500))
m = new(slot); c = m.core
tr = Trace(m, extra=['_ZN16MenuSoundManager12setPlaySoundENS_10MENU_SOUNDE'])
party = c.export('_ZN6status7g_PartyE'); c.mem_w(party + 0x2e0, struct.pack('<I', 3000))
tws = m.E('_ZN16TownWindowSystem11m_singletonE')
mm = c.call(m.E('_ZN27MaterielMenu_WINDOW_MANAGER12getSingletonEv'), label='mm'); c.mem_w(mm + 0x10, struct.pack('<i', 0))
tr.evt.clear(); m.sensor.drain()
c.call(m.E('_ZN6window13CommandWindow19changeShopMenuPhaseEi'), tws, phase, label='phase')
f0 = m.frames
waiting = 0; rel = None; ev0 = 0; yes_pressed = 0
for i in range(N):
    p = d = 0
    if rel is not None: m.send_menu(rel, 1, -1, 0); rel = None
    port = m.active_menu()
    att_msg = m.msg_visible and (m.ui.msg.get('feed') or m.message_state()[1] in (3, 5))
    if port is not None or att_msg:
        waiting += 1
        if waiting % 6 == 0:
            if port is None and att_msg: p = d = ENGINE.A; print('%5d  [A message]' % m.frames)
            else:
                print('%5d  [A menu port %s type %s]' % (m.frames, port, m.ui.f[port].get('type')))
                m.send_menu(port, 1, -1, 0x10); rel = port
    else: waiting = 0
    pkt = m.step(p, d)
    for t, a, f in pkt:
        if t in (35, 36, 37): print('%5d  PKT %d %s' % (m.frames, t, a[:2]))
        elif t == 9: print('%5d  PKT 9 fondu %s %s part=%#x' % (m.frames, [hex(x) for x in a[:2]], [round(x, 2) for x in f[:3]], m.state.part))
        elif t not in (22, 28, 29, 13, 10, 3, 4): print('%5d  pkt %d %s' % (m.frames, t, a[:4]))
    for e in tr.evt[ev0:]: print('%5d  appel %s(%#x,%#x) <- %s' % (e[0], e[1], e[2], e[3], ' < '.join(x.split('+')[0] for x in e[4][:4])))
    ev0 = len(tr.evt)
    for s in m.sensor.drain(): print('%5d  texte %r' % (m.frames, s.get('texte', '')[:100]))
print('fin', m.frames, 'frames from', f0)
