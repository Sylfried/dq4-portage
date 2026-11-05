import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
m = hl.new('book2'); assert m.load_save(1)
for _ in range(60): m.step(0, 0)
c = m.core; G = m._global()
c.call(m.E('_ZN6Global9startBookEv'), G, label='book')
def run(n, tag):
    cnt = collections.Counter(); ex = {}
    for i in range(n):
        for t, a, f in m.step(0, 0):
            cnt[t] += 1
            if t in (21, 22, 10, 11) and len(ex.setdefault(t, [])) < 2: ex[t].append((m.frames, a[:2], [round(x, 2) for x in f[:3]]))
    print(tag, 'part', hex(m.state.part), 'pk', dict(sorted(cnt.items())), ex, 'models', dict(m.state.models), 'meshes', {k: (len(v['v']), [round(x, 2) for x in v['pos']]) for k, v in m.state.meshes.items()}, 'cam', m.state.cam_pos, m.state.cam_target, flush=True)
run(120, 'liste')
p = m.active_menu(); print('menu', p)
m.send_menu(12, 1, 0, 0x10); run(3, 'select'); m.send_menu(12, 1, -1, 0); run(120, 'detail')
