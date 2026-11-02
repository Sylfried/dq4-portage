"""Poker : boucle de jeu 'joueur automatique' : message visible -> A (comme la fenetre) ; sinon menu -> bouton 0 (A) ; observe jusqu'a la fin / 3000 images."""
import sys, struct, collections
sys.path.insert(0, '/tmp/audit')
import hl
m = hl.nouveau('poker3'); assert m.charger_sauvegarde(1)
for _ in range(60): m.step(0, 0)
c = m.core; L = m.L; G = m._global(); slotobj = struct.unpack('<Q', c.mem(L + 0x23db38, 8))[0]
joueur = struct.unpack('<Q', c.mem(L + 0x23d428, 8))[0]; c.mem_w(joueur + 0x2e8, struct.pack('<i', 500))
c.call(m.E('_ZN6Global11setMinigameEi'), G, 0, label='a'); c.call(m.E('_ZN17MaterielMenu_SLOT11setSlotTypeEi'), slotobj, 0, label='b'); c.call(m.E('_ZN6Global11startCasinoEv'), G, label='c')
vus = []; tot = collections.Counter(); derniere = None
def piece(): return struct.unpack('<i', c.mem(joueur + 0x2e8, 4))[0]
for it in range(60):
    for _ in range(30): 
        for t, a, f in m.step(0, 0): tot[t] += 1
    if m.etat.partie != 0xf: print('sortie du casino a l image', m.images, 'partie', hex(m.etat.partie), 'carte', m.etat.carte); break
    p = m.menu_actif(); f = m.ui.f.get(12, {}); cs = f.get('cases', {})
    sig = (m.msg_visible, f.get('entree'), tuple(sorted((k, v[:16]) for k, v in cs.items())))
    if sig != derniere: vus.append((m.images, m.msg_visible, f.get('entree'), piece(), {k: v[:16] for k, v in list(cs.items())[:9]})); derniere = sig
    if m.msg_visible and not (f.get('entree')):
        for t, a, f_ in m.step(0x10, 0x10): tot[t] += 1
    elif p is not None:
        m.envoyer_menu(p, 1, 0, 0x10)
        for _ in range(3):
            for t, a, f_ in m.step(0, 0): tot[t] += 1
        m.envoyer_menu(p, 1, -1, 0)
print('etats distincts', len(vus), 'pieces', piece(), 'paquets', dict(sorted(tot.items())))
for v in vus[:14]: print(v)
