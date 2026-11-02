import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
m = hl.nouveau('book2'); assert m.charger_sauvegarde(1)
for _ in range(60): m.step(0, 0)
c = m.core; G = m._global()
c.call(m.E('_ZN6Global9startBookEv'), G, label='book')
def run(n, tag):
    cnt = collections.Counter(); ex = {}
    for i in range(n):
        for t, a, f in m.step(0, 0):
            cnt[t] += 1
            if t in (21, 22, 10, 11) and len(ex.setdefault(t, [])) < 2: ex[t].append((m.images, a[:2], [round(x, 2) for x in f[:3]]))
    print(tag, 'partie', hex(m.etat.partie), 'pq', dict(sorted(cnt.items())), ex, 'modeles', dict(m.etat.modeles), 'maillages', {k: (len(v['v']), [round(x, 2) for x in v['pos']]) for k, v in m.etat.maillages.items()}, 'cam', m.etat.cam_pos, m.etat.cam_cible, flush=True)
run(120, 'liste')
p = m.menu_actif(); print('menu', p)
m.envoyer_menu(12, 1, 0, 0x10); run(3, 'select'); m.envoyer_menu(12, 1, -1, 0); run(120, 'detail')
