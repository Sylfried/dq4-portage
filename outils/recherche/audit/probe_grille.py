import sys, struct
sys.path.insert(0, '/tmp/audit')
import hl
for jeu, machine in tuple((j, 0) for j in map(int, sys.argv[1:])):
    m = hl.nouveau('gr%d' % jeu); assert m.charger_sauvegarde(1)
    for _ in range(60): m.step(0, 0)
    c = m.core; L = m.L; G = m._global(); slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
    joueur = struct.unpack('<Q', c.mem(L + 0x23d428, 8))[0]; c.mem_w(joueur + 0x2e8, struct.pack('<i', 500))
    c.call(m.E('_ZN6Global11setMinigameEi'), G, jeu, label='a'); c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, machine, label='b'); c.call(m.E('_ZN6Global11startCasinoEv'), G, label='c')
    for _ in range(150): m.step(0, 0)
    print('jeu', jeu, 'carte', m.etat.carte, 'partie', hex(m.etat.partie), 'ports', {p: (f.get('type'), f.get('grille'), f.get('entree'), f.get('vis')) for p, f in m.ui.f.items() if f.get('act') and p >= 2}, 'menu_actif', m.menu_actif(), 'msg', m.msg_visible)
