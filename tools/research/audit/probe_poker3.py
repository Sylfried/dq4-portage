"""Poker : boucle de jeu 'joueur automatique' : message visible -> A (comme la fenetre) ; sinon menu -> bouton 0 (A) ; observe jusqu'a la fin / 3000 images."""
import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
m = hl.new('poker3'); assert m.load_save(1)
for _ in range(60): m.step(0, 0)
c = m.core; L = m.L; G = m._global(); slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
player = struct.unpack('<Q', c.mem(L + 0x23d428, 8))[0]; c.mem_w(player + 0x2e8, struct.pack('<i', 500))
c.call(m.E('_ZN6Global11setMinigameEi'), G, 0, label='a'); c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, 0, label='b'); c.call(m.E('_ZN6Global11startCasinoEv'), G, label='c')
seen = []; tot = collections.Counter(); last_one = None
def piece(): return struct.unpack('<i', c.mem(player + 0x2e8, 4))[0]
for it in range(60):
    for _ in range(30): 
        for t, a, f in m.step(0, 0): tot[t] += 1
    if m.state.part != 0xf: print('sortie du casino a l image', m.frames, 'partie', hex(m.state.part), 'carte', m.state.game_map); break
    p = m.active_menu(); f = m.ui.f.get(12, {}); cs = f.get('cases', {})
    sig = (m.msg_visible, f.get('entree'), tuple(sorted((k, v[:16]) for k, v in cs.items())))
    if sig != last_one: seen.append((m.frames, m.msg_visible, f.get('entree'), piece(), {k: v[:16] for k, v in list(cs.items())[:9]})); last_one = sig
    if m.msg_visible and not (f.get('entree')):
        for t, a, f_ in m.step(0x10, 0x10): tot[t] += 1
    elif p is not None:
        m.send_menu(p, 1, 0, 0x10)
        for _ in range(3):
            for t, a, f_ in m.step(0, 0): tot[t] += 1
        m.send_menu(p, 1, -1, 0)
print('etats distincts', len(seen), 'pieces', piece(), 'paquets', dict(sorted(tot.items())))
for v in seen[:14]: print(v)
