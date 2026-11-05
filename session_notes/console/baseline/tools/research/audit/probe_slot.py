"""Sonde : machine a sous (casino) -> appui sur 'Lancer' (bouton 0, A) ; journalise paquets 5/6/7/22, fenetres, messages."""
import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
game = int(sys.argv[1]) if len(sys.argv) > 1 else 1; machine = int(sys.argv[2]) if len(sys.argv) > 2 else 0
m = hl.new('slot'); assert m.load_save(1)
for _ in range(60): m.step(0, 0)
c = m.core; L = m.L; G = m._global(); slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
c.call(m.E('_ZN6Global11setMinigameEi'), G, game, label='a'); c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, machine, label='b'); c.call(m.E('_ZN6Global11startCasinoEv'), G, label='c')
def run(n, tag, fa=0):
    cnt = collections.Counter(); ex = {}
    for i in range(n):
        pkt = m.step(0, fa if i == 0 else 0)
        for t, a, f in pkt:
            cnt[t] += 1
            if t in (5, 6, 7, 3, 4, 2, 33, 34, 35) and len(ex.setdefault(t, [])) < 5: ex[t].append((m.frames, a[:4], [round(x, 2) for x in f[:4]]))
    f12 = m.ui.f.get(12, {})
    print(tag, 'images', m.frames, 'paquets', dict(sorted(cnt.items())), 'msg', m.msg_visible, 'cases', {k: v[:40] for k, v in list(f12.get('cases', {}).items())[:8]}, 'indic', f12.get('indic'), 'ints', {k: v for k, v in list(f12.get('ints', {}).items())[:12]})
    for t, v in sorted(ex.items()): print('     ', t, v)
run(60, 'attente')
print('boutons: menu_actif', m.active_menu(), 'entree', m.ui.f[12].get('entree'))
m.send_menu(12, 1, 1, 0x10); run(3, 'mise +'); m.send_menu(12, 1, -1, 0); run(5, 'rel')
m.send_menu(12, 1, 0, 0x10); run(3, 'lancer'); m.send_menu(12, 1, -1, 0)
run(200, 'rotation')
for k in range(4):
    m.send_menu(12, 1, -1, 0x10); run(2, 'A%d' % k); m.send_menu(12, 1, -1, 0); run(80, 'apres A%d' % k)
