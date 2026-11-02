"""Sonde 3 : machine a sous AVEC jetons (pieces ecrites dans le moteur de TEST seulement). Entrees : 'viewer' (held=0x10, decl=0x10 comme fenetre.tick avec message visible) ou 'kw' (decl=0x100)."""
import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
mode = sys.argv[1]; machine = int(sys.argv[2]) if len(sys.argv) > 2 else 0
m = hl.nouveau('slot3' + mode); assert m.charger_sauvegarde(1)
for _ in range(60): m.step(0, 0)
c = m.core; L = m.L; G = m._global(); slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
joueur = struct.unpack('<Q', c.mem(L + 0x23d428, 8))[0]
print('pieces avant', struct.unpack('<i', c.mem(joueur + 0x2e8, 4))[0])
c.mem_w(joueur + 0x2e8, struct.pack('<i', 500))
c.call(m.E('_ZN6Global11setMinigameEi'), G, 1, label='a'); c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, machine, label='b'); c.call(m.E('_ZN6Global11startCasinoEv'), G, label='c')
def run(n, tag, held=0, fa=0):
    cnt = collections.Counter(); ex = {}
    for i in range(n):
        pq = m.step(held if i == 0 else 0, fa if i == 0 else 0)
        for t, a, f in pq:
            cnt[t] += 1
            if t in (5, 6, 7, 22, 35) and len(ex.setdefault(t, [])) < 4: ex[t].append((m.images, a[:3]))
    f12 = m.ui.f.get(12, {})
    print(tag, 'img', m.images, 'pq', dict(sorted(cnt.items())), 'carte', m.etat.carte, 'partie', hex(m.etat.partie), 'msg', m.msg_visible, 'menu', m.menu_actif(), 'entree', f12.get('entree'), 'cases', {k: v[:12] for k, v in list(f12.get('cases', {}).items())[:7]}, dict(ex), flush=True)
def A(tag, n=2):
    if mode == 'kw': run(n, tag, fa=0x100)
    else: run(n, tag, held=0x10, fa=0x10)
run(80, 'attente')
for k in range(6):
    A('A#%d' % k); run(100, ' apres')
