"""Sonde : Global::startBook (menu « Bestiaire », partie 0x10) dans le moteur de test. Ce que le moteur envoie et ce que la visionneuse en saurait."""
import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
m = hl.new('book'); assert m.load_save(1)
for _ in range(60): m.step(0, 0)
c = m.core; G = m._global()
c.call(m.E('_ZN6Global9startBookEv'), G, label='book')
cnt = collections.Counter(); ex = {}
for i in range(240):
    for t, a, f in m.step(0, 0):
        cnt[t] += 1
        if t in (0, 10, 11, 21, 22) and len(ex.setdefault(t, [])) < 2: ex[t].append((m.frames, a[:3]))
print('partie', hex(m.state.part), 'carte', m.state.game_map, 'paquets', dict(sorted(cnt.items())), ex)
print('ports', {p: (f.get('type'), f.get('entree')) for p, f in m.ui.f.items() if f.get('act') and p >= 2}, 'menu_actif', m.active_menu(), 'msg', m.msg_visible)
print('maillages', {k: (len(v['v']), v['pos']) for k, v in list(m.state.meshes.items())[:6]}, 'modeles', dict(list(m.state.models.items())[:6]))
