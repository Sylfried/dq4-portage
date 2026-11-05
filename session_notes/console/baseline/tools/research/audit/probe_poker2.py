import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
m = hl.new('poker2'); assert m.load_save(1)
for _ in range(60): m.step(0, 0)
c = m.core; L = m.L; G = m._global(); slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
player = struct.unpack('<Q', c.mem(L + 0x23d428, 8))[0]; c.mem_w(player + 0x2e8, struct.pack('<i', 500))
c.call(m.E('_ZN6Global11setMinigameEi'), G, 0, label='a'); c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, 0, label='b'); c.call(m.E('_ZN6Global11startCasinoEv'), G, label='c')
def r(n, tag, held=0, fa=0):
    cnt = collections.Counter()
    for i in range(n):
        for t, a, f in m.step(held if i == 0 else 0, fa if i == 0 else 0): cnt[t] += 1
    f = m.ui.f.get(12, {}); cs = f.get('cases', {})
    print(tag, 'img', m.frames, 'msg', m.msg_visible, 'entree', f.get('entree'), 'mise', cs.get((0, 3)), 'btn', cs.get((1, 0)), 'dyn', {k: v for k, v in cnt.items() if k != 22}, 'p22', cnt.get(22, 0), flush=True)
r(100, 'attente'); r(2, 'A', 0x10, 0x10); r(90, ' ap')
for k in range(3):
    m.send_menu(12, 1, 1, 0x2); r(2, 'mise+1'); m.send_menu(12, 1, -1, 0); r(3, ' rel')
m.send_menu(12, 1, 0, 0x10); r(2, 'valider'); m.send_menu(12, 1, -1, 0); r(120, ' ap')
for k in range(4):
    m.send_menu(12, 1, 0, 0x10); r(2, 'bouton0 #%d' % k); m.send_menu(12, 1, -1, 0); r(100, ' ap')
