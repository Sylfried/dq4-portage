"""Sonde 4 : machine a sous avec jetons ; la mise passe par MenuPort (bouton 1, manette 2 = haut / 1 = bas), Lancer = bouton 0 manette 0x10."""
import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
m = hl.new('slot4'); assert m.load_save(1)
for _ in range(60): m.step(0, 0)
c = m.core; L = m.L; G = m._global(); slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
player = struct.unpack('<Q', c.mem(L + 0x23d428, 8))[0]
c.mem_w(player + 0x2e8, struct.pack('<i', 500))
c.call(m.E('_ZN6Global11setMinigameEi'), G, 1, label='a'); c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, 0, label='b'); c.call(m.E('_ZN6Global11startCasinoEv'), G, label='c')
every = collections.Counter()
def run(n, tag):
    cnt = collections.Counter(); ex = {}
    for i in range(n):
        pkt = m.step(0, 0)
        for t, a, f in pkt:
            cnt[t] += 1; every[t] += 1
            if t in (5, 6, 7, 22, 35) and len(ex.setdefault(t, [])) < 3: ex[t].append((m.frames, a[:2]))
    f12 = m.ui.f.get(12, {})
    print(tag, 'img', m.frames, 'pk', dict(sorted(cnt.items())), 'msg', m.msg_visible, 'menu', m.active_menu(), 'cells', {k: v[:10] for k, v in list(f12.get('cases', {}).items())[:7]}, dict(ex), flush=True)
run(80, 'attente')
for k in range(3):
    m.send_menu(12, 1, 1, 0x2); run(2, 'mise+'); m.send_menu(12, 1, -1, 0); run(3, ' rel')
m.send_menu(12, 1, 0, 0x10); run(3, 'Lancer'); m.send_menu(12, 1, -1, 0); run(3, ' rel')
run(150, 'rotation')
for k in range(3):
    m.send_menu(12, 1, 0, 0x10); run(3, 'Stop%d' % k); m.send_menu(12, 1, -1, 0); run(60, ' after')
run(300, 'fin')
print('TOTAL packets', dict(sorted(every.items())))
