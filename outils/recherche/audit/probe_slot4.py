"""Sonde 4 : machine a sous avec jetons ; la mise passe par MenuPort (bouton 1, manette 2 = haut / 1 = bas), Lancer = bouton 0 manette 0x10."""
import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
m = hl.nouveau('slot4'); assert m.charger_sauvegarde(1)
for _ in range(60): m.step(0, 0)
c = m.core; L = m.L; G = m._global(); slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
joueur = struct.unpack('<Q', c.mem(L + 0x23d428, 8))[0]
c.mem_w(joueur + 0x2e8, struct.pack('<i', 500))
c.call(m.E('_ZN6Global11setMinigameEi'), G, 1, label='a'); c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, 0, label='b'); c.call(m.E('_ZN6Global11startCasinoEv'), G, label='c')
tous = collections.Counter()
def run(n, tag):
    cnt = collections.Counter(); ex = {}
    for i in range(n):
        pq = m.step(0, 0)
        for t, a, f in pq:
            cnt[t] += 1; tous[t] += 1
            if t in (5, 6, 7, 22, 35) and len(ex.setdefault(t, [])) < 3: ex[t].append((m.images, a[:2]))
    f12 = m.ui.f.get(12, {})
    print(tag, 'img', m.images, 'pq', dict(sorted(cnt.items())), 'msg', m.msg_visible, 'menu', m.menu_actif(), 'cases', {k: v[:10] for k, v in list(f12.get('cases', {}).items())[:7]}, dict(ex), flush=True)
run(80, 'attente')
for k in range(3):
    m.envoyer_menu(12, 1, 1, 0x2); run(2, 'mise+'); m.envoyer_menu(12, 1, -1, 0); run(3, ' rel')
m.envoyer_menu(12, 1, 0, 0x10); run(3, 'Lancer'); m.envoyer_menu(12, 1, -1, 0); run(3, ' rel')
run(150, 'rotation')
for k in range(3):
    m.envoyer_menu(12, 1, 0, 0x10); run(3, 'Stop%d' % k); m.envoyer_menu(12, 1, -1, 0); run(60, ' apres')
run(300, 'fin')
print('TOTAL paquets', dict(sorted(tous.items())))
