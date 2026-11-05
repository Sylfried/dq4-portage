"""Sonde poker (Global::setMinigame(0) -> ev04, type 48) avec 500 jetons dans le moteur de TEST. mode : viewer (held=0x10, decl=0x10) | kw (decl=0x100) | menu (MenuPort [1, bouton, manette])"""
import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
mode = sys.argv[1]
m = hl.new('poker' + mode); assert m.load_save(1)
for _ in range(60): m.step(0, 0)
c = m.core; L = m.L; G = m._global(); slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
player = struct.unpack('<Q', c.mem(L + 0x23d428, 8))[0]; c.mem_w(player + 0x2e8, struct.pack('<i', 500))
c.call(m.E('_ZN6Global11setMinigameEi'), G, 0, label='a'); c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, 0, label='b'); c.call(m.E('_ZN6Global11startCasinoEv'), G, label='c')
def state(tag, cnt):
    ports = {p: (f.get('type'), f.get('entree')) for p, f in m.ui.f.items() if f.get('act') and p >= 2}
    cells = {p: {k: v[:14] for k, v in list(f.get('cases', {}).items())[:8]} for p, f in m.ui.f.items() if f.get('act') and p >= 12}
    print(tag, 'img', m.frames, 'pk', dict(sorted(cnt.items())), 'msg', m.msg_visible, 'menu', m.active_menu(), 'ports', ports, 'cells', cells, flush=True)
def run(n, tag, held=0, fa=0):
    cnt = collections.Counter()
    for i in range(n):
        pkt = m.step(held if i == 0 else 0, fa if i == 0 else 0)
        for t, a, f in pkt: cnt[t] += 1
    state(tag, cnt)
def A(tag, n=2):
    if mode == 'kw': run(n, tag, fa=0x100)
    elif mode == 'viewer': run(n, tag, held=0x10, fa=0x10)
    else:
        p = m.active_menu()
        if p is None: run(n, tag); return
        m.send_menu(p, 1, 0, 0x10); run(n, tag); m.send_menu(p, 1, -1, 0)
run(100, 'attente')
for k in range(8):
    A('A#%d' % k); run(90, ' after')
