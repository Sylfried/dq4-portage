"""Sonde : demarre le casino (Global::startCasino, comme cmd_mini_game) depuis la sauvegarde 1 et journalise paquets / fenetres / messages.  python3 probe_casino.py [type_jeu] [type_machine] [images]"""
import sys, struct, collections, time
sys.path.insert(0, '/tmp/audit')
import hl
game = int(sys.argv[1]) if len(sys.argv) > 1 else 0; machine = int(sys.argv[2]) if len(sys.argv) > 2 else 0; N = int(sys.argv[3]) if len(sys.argv) > 3 else 400
m = hl.new('casino'); assert m.load_save(1)
for _ in range(60): m.step(0, 0)
c = m.core; L = m.L
G = m._global()
slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
print('Global', hex(G), 'objet SLOT', hex(slotobj), 'partie avant', hex(m.state.part))
c.call(m.E('_ZN6Global11setMinigameEi'), G, game, label='setMinigame')
c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, machine, label='setSlotType')
c.call(m.E('_ZN6Global11startCasinoEv'), G, label='startCasino')
cnt = collections.Counter(); seen = {}; xs = {}; last = None
try:
    for i in range(N):
        pkt = m.step(0, 0)
        for t, a, f in pkt:
            cnt[t] += 1
            if t not in seen: seen[t] = (i, a[:6], [round(x, 3) for x in f[:6]])
            if t in (6, 0, 10, 11, 21, 31, 3, 4) and len(xs.setdefault(t, [])) < 6: xs[t].append((i, a[:6], [round(x, 3) for x in f[:6]]))
        ports = tuple(sorted((p, f['type']) for p, f in m.ui.f.items() if f.get('act') and p >= 2))
        state = (hex(m.state.part), m.state.game_map, ports, m.msg_visible)
        if state != last: last = state; print('image', i, 'partie/carte/ports/msg', state, flush=True)
except Exception as ex:
    print('EXCEPTION a l image', i, str(ex)[:500])
print('paquets', dict(sorted(cnt.items())))
for k, v in sorted(seen.items()): print('  type', k, 'premier a', v)
for t, v in sorted(xs.items()): print('  type', t, v)
