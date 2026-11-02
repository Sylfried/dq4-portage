"""Services en ville (eglise, auberge...) avec trace des sons. usage: services.py PHASE "suite de touches" [slot] [indices_morts]"""
import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work')
from h45 import *
phase = int(sys.argv[1]); touches = sys.argv[2].split(',') if len(sys.argv) > 2 and sys.argv[2] else []
slot = int(sys.argv[3]) if len(sys.argv) > 3 else 1
morts = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 and sys.argv[4] else []
NIV = int(sys.argv[5]) if len(sys.argv) > 5 else 1500
mo = nouveau('srv'); c = mo.core; tr = Trace(mo)
mo.charger_sauvegarde(slot)
for _ in range(250): mo.step(0, 0)
party = c.export('_ZN6status7g_PartyE')
for i in morts: poser_pv(mo, i, 0)
print('membres', membres(mo), [pv(mo, i)[0] for i in membres(mo)])
OR_PARTY = 1
c.mem_w(party + 0x2e0, struct.pack('<I', 3000))
tr.evt.clear(); mo.capteur.vider()
tws = mo.E('_ZN16TownWindowSystem11m_singletonE')
mm = c.call(mo.E('_ZN27MaterielMenu_WINDOW_MANAGER12getSingletonEv'), label='mm')
c.mem_w(mm + 0x10, struct.pack('<i', 0))
c.call(mo.E('_ZN6window13CommandWindow19changeShopMenuPhaseEi'), tws, phase, label='phase')
BT = {'A': 0x10, 'B': 0x20, 'U': 2, 'D': 1, 'L': 8, 'R': 4}
ev0 = 0; attente = 0; rel = None; k = 0; vu = None; ph0 = None
for i in range(NIV):
    p = d = 0
    if rel is not None: mo.envoyer_menu(rel, 1, -1, 0); rel = None
    port = mo.menu_actif()
    att_msg = mo.msg_visible and (mo.ui.msg.get('feed') or mo.etat_message()[1] in (3, 5))
    if port is not None or att_msg:
        attente += 1
        if attente % 6 == 0:
            if port is None and att_msg: p = d = MO.A
            elif k < len(touches):
                t = touches[k]; k += 1
                print('%5d TOUCHE %s sur port %s type %s cases %s cur %s' % (mo.images, t, port, mo.ui.f[port].get('type'), {a: b[:14] for a, b in list(mo.ui.f[port]['cases'].items())[:8]}, mo.ui.f[port].get('cur')))
                if t.startswith('#'): mo.envoyer_menu(port, 1, int(t[1:]), 0x10)
                else: mo.envoyer_menu(port, 1, -1, BT[t])
                rel = port
    else: attente = 0
    if i % 100 == 0 and os.environ.get('DBGM'): print('   dbg', mo.images, 'port', port, 'msg', mo.msg_visible, 'att_msg', att_msg, 'actifs', [(q, f.get('type'), f['vis'], f.get('entree')) for q, f in mo.ui.f.items() if q > 1 and f.get('act')])
    prec = mo.etat.partie; pq = mo.step(p, d)
    for t, v in pq_sons(pq): print('%5d  SON %s' % (mo.images, {35: 'SE %d', 36: 'stopSE %d', 37: 'BGM %#x'}[t] % v))
    for e in tr.evt[ev0:]: print('%5d  appel %s(%d) <- %s' % (e[0], e[1], e[2], ' < '.join(x.split('+')[0] for x in e[3][:4])))
    ev0 = len(tr.evt)
    for s in mo.capteur.vider(): print('%5d  texte %r' % (mo.images, s['texte'][:100]))
    pp = [pv(mo, j)[0][0] for j in membres(mo)]
    if pp != ph0: ph0 = pp; print('%5d  pv %s' % (mo.images, pp))
    if mo.etat.partie != prec: print('%5d  partie %#x -> %#x' % (mo.images, prec, mo.etat.partie))
