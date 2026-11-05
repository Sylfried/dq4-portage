"""Sonde 2 : machine a sous. Le moteur lit-il le MOT DE TOUCHES (GameUpdate arg2) ? On envoie A (0x100) sans passer par MenuPort."""
import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
game = int(sys.argv[1]) if len(sys.argv) > 1 else 1; machine = int(sys.argv[2]) if len(sys.argv) > 2 else 0
m = hl.new('slot2'); assert m.load_save(1)
for _ in range(60): m.step(0, 0)
c = m.core; L = m.L; G = m._global(); slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
c.call(m.E('_ZN6Global11setMinigameEi'), G, game, label='a'); c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, machine, label='b'); c.call(m.E('_ZN6Global11startCasinoEv'), G, label='c')
def run(n, tag, held=0, fa=0):
    cnt = collections.Counter(); ex = {}
    for i in range(n):
        pkt = m.step(held, fa if i == 0 else 0)
        for t, a, f in pkt:
            cnt[t] += 1
            if t in (5, 6, 22) and len(ex.setdefault(t, [])) < 3: ex[t].append((m.frames, a[:3]))
    f12 = m.ui.f.get(12, {})
    print(tag, 'img', m.frames, 'pq', dict(sorted(cnt.items())), 'msg', m.msg_visible, 'cases', {k: v[:20] for k, v in list(f12.get('cases', {}).items())[:6]}, dict(ex), flush=True)
run(60, 'attente')
mode = sys.argv[3] if len(sys.argv) > 3 else 'kw'
for k in range(3):
    if mode == 'kw': run(2, 'A(0x100)#%d' % k, fa=0x100)
    else: run(2, 'viewer(held=0x10,decl=0x10)#%d' % k, held=0x10, fa=0x10)
    run(120, 'apres#%d' % k)
