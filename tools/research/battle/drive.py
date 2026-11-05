"""Pilote de combat (hors depot) : moteur seul, politique de menus par scenario, chronologie en images du moteur (30 Hz)."""
import sys, os, struct, tempfile, unicorn
WT = os.environ.get('CB_WT', '/home/claude/wt45-combat')
sys.path.insert(0, WT + '/dq4_pc'); os.chdir(WT + '/dq4_pc')
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'; SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'

def start_engine(slot):
    eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_cb_'))
    for _ in range(3): eng.step(0, 0)
    eng.load_save(slot)
    for i in range(100): eng.step(0, 0x10 if i % 10 == 0 else 0)
    if eng.state.part != ENGINE.PART_FIELD:
        eng.start_field()
        for i in range(120): eng.step(0, 0)
    return eng

def force_critical(eng):
    c = eng.core; L = c.LIB_BASE
    def f1(uc, a, sz, u): c.mem_w(L + 0x25c6ed, b'\x01')
    c.uc.hook_add(unicorn.UC_HOOK_CODE, f1, None, L + 0x1a81dc, L + 0x1a81dc); c.uc.ctl_flush_tb()

def encounter(eng):
    c = eng.core
    c.call(eng.E('_ZN7Encount12forceEncountEv'), c.call(eng.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
    for i in range(900):
        eng.step([0x4, 0x8][(i // 20) % 2], 0)
        if eng.state.part == ENGINE.PART_BATTLE: return True
    return False

def policy(scenario, type_menu, cells, member_idx):
    """-> indice de bouton a valider pour ce menu."""
    t = {v: k for k, v in cells.items()}
    if type_menu == 30: return 1 if scenario == 'fuite' else 0
    if type_menu == 36 and scenario == 'objet': return 'page' if cells.get((5, 0)) == '1/3' else 0
    if type_menu == 32:
        if scenario == 'sort' and 'Magie' in t and 'Ragnar' not in cells.values(): return t['Magie'][0]
        if scenario == 'defense': return 3
        if scenario == 'objet' and 'Objets' in t: return t['Objets'][0]
        return 0
    return 0

def play(eng, scenario='attaque', scroll=2, max_frames=4000, verbose=False):
    """Joue un combat. -> liste d'evenements (image relative, texte) et nombre d'images du moteur."""
    eng.impose_scroll_mode(scroll)
    base = eng.frames; ev = []
    def j(s): ev.append((eng.frames - base, s))
    st = {'rel': None, 'menu': None, 'att': 0, 'msgatt': 0, 'msg': None}
    end = None
    for i in range(max_frames):
        p = d = 0
        if st['rel'] is not None: eng.send_menu(st['rel'], 1, -1, 0); st['rel'] = None
        port = eng.active_menu()
        if port is not None and not eng.msg_visible:
            f = eng.ui.win(port)
            if port != st['menu']: st['att'] = 0
            st['att'] += 1
            if st['att'] % 4 == 0:
                idx = policy(scenario, f['type'], f['cases'], 0)
                if idx == 'page': eng.send_menu(port, 1, -1, 4)
                else: eng.send_menu(port, 1, idx, 0x10)
                st['rel'] = port
        elif eng.msg_visible and eng.message_state()[1] in (3, 5):
            st['msgatt'] += 1
            if st['msgatt'] > 100 and st['msgatt'] % 4 == 0: p = d = ENGINE.A          # message final qui attend une touche
        else: st['msgatt'] = 0
        prev = eng.state.part; pkt = eng.step(p, d)
        m = eng.active_menu()
        if m != st['menu']:
            if m is not None: j('MENU opens type %s %s' % (eng.ui.win(m)['type'], sorted(eng.ui.win(m)['cases'].values())[:4]))
            else: j('MENU closed')
            st['menu'] = m
        em = eng.message_state(); k = (em[0], em[1] == 2, eng.msg_visible)
        for dg in eng.ui.damage: j('NUMBER %s' % (dg,))
        eng.ui.damage = []
        for t, a, f in pkt:
            if t == 35: j('SE %d' % a[0])
            elif t == 21 and a[1] > 5000: j('EFFECT model %d (slot %d)' % (a[1], a[0]))
            elif t == 9: j('FADE %d' % a[0])
            elif t == 34: j('SCREEN effect %d' % a[0])
        if em[1] == 2 and st['msg'] != 'ecrit': st['msg'] = 'ecrit'; j('MSG writing')
        elif em[1] == 5 and st['msg'] != 'attente': st['msg'] = 'attente'; j('MSG waiting')
        elif em[1] not in (2, 5): st['msg'] = None
        if prev == ENGINE.PART_BATTLE and eng.state.part != ENGINE.PART_BATTLE: end = eng.frames; j('END part')
        if end and eng.frames > end + 40: break
    return ev
