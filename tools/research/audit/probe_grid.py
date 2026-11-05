import sys, struct
sys.path.insert(0, '/tmp/audit')
import hl
for game, machine in tuple((j, 0) for j in map(int, sys.argv[1:])):
    m = hl.new('gr%d' % game); assert m.load_save(1)
    for _ in range(60): m.step(0, 0)
    c = m.core; L = m.L; G = m._global(); slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
    player = struct.unpack('<Q', c.mem(L + 0x23d428, 8))[0]; c.mem_w(player + 0x2e8, struct.pack('<i', 500))
    c.call(m.E('_ZN6Global11setMinigameEi'), G, game, label='a'); c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, machine, label='b'); c.call(m.E('_ZN6Global11startCasinoEv'), G, label='c')
    for _ in range(150): m.step(0, 0)
    print('game', game, 'map', m.state.game_map, 'part', hex(m.state.part), 'ports', {p: (f.get('type'), f.get('grille'), f.get('entree'), f.get('vis')) for p, f in m.ui.f.items() if f.get('act') and p >= 2}, 'active_menu', m.active_menu(), 'msg', m.msg_visible)
