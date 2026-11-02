"""Sonde poker (Global::setMinigame(0) -> ev04, type 48) avec 500 jetons dans le moteur de TEST. mode : viewer (held=0x10, decl=0x10) | kw (decl=0x100) | menu (MenuPort [1, bouton, manette])"""
import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
mode = sys.argv[1]
m = hl.nouveau('poker' + mode); assert m.charger_sauvegarde(1)
for _ in range(60): m.step(0, 0)
c = m.core; L = m.L; G = m._global(); slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
joueur = struct.unpack('<Q', c.mem(L + 0x23d428, 8))[0]; c.mem_w(joueur + 0x2e8, struct.pack('<i', 500))
c.call(m.E('_ZN6Global11setMinigameEi'), G, 0, label='a'); c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, 0, label='b'); c.call(m.E('_ZN6Global11startCasinoEv'), G, label='c')
def etat(tag, cnt):
    ports = {p: (f.get('type'), f.get('entree')) for p, f in m.ui.f.items() if f.get('act') and p >= 2}
    cases = {p: {k: v[:14] for k, v in list(f.get('cases', {}).items())[:8]} for p, f in m.ui.f.items() if f.get('act') and p >= 12}
    print(tag, 'img', m.images, 'pq', dict(sorted(cnt.items())), 'msg', m.msg_visible, 'menu', m.menu_actif(), 'ports', ports, 'cases', cases, flush=True)
def run(n, tag, held=0, fa=0):
    cnt = collections.Counter()
    for i in range(n):
        pq = m.step(held if i == 0 else 0, fa if i == 0 else 0)
        for t, a, f in pq: cnt[t] += 1
    etat(tag, cnt)
def A(tag, n=2):
    if mode == 'kw': run(n, tag, fa=0x100)
    elif mode == 'viewer': run(n, tag, held=0x10, fa=0x10)
    else:
        p = m.menu_actif()
        if p is None: run(n, tag); return
        m.envoyer_menu(p, 1, 0, 0x10); run(n, tag); m.envoyer_menu(p, 1, -1, 0)
run(100, 'attente')
for k in range(8):
    A('A#%d' % k); run(90, ' apres')
