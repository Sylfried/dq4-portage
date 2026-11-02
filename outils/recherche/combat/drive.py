"""Pilote de combat (hors depot) : moteur seul, politique de menus par scenario, chronologie en images du moteur (30 Hz)."""
import sys, os, struct, tempfile, unicorn
WT = os.environ.get('CB_WT', '/home/claude/wt45-combat')
sys.path.insert(0, WT + '/dq4_pc'); os.chdir(WT + '/dq4_pc')
import moteur as MO
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'; SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'

def demarrer(slot):
    mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_cb_'))
    for _ in range(3): mo.step(0, 0)
    mo.charger_sauvegarde(slot)
    for i in range(100): mo.step(0, 0x10 if i % 10 == 0 else 0)
    if mo.etat.partie != MO.PARTIE_CHAMP:
        mo.demarrer_champ()
        for i in range(120): mo.step(0, 0)
    return mo

def forcer_critique(mo):
    c = mo.core; L = c.LIB_BASE
    def f1(uc, a, sz, u): c.mem_w(L + 0x25c6ed, b'\x01')
    c.uc.hook_add(unicorn.UC_HOOK_CODE, f1, None, L + 0x1a81dc, L + 0x1a81dc); c.uc.ctl_flush_tb()

def rencontre(mo):
    c = mo.core
    c.call(mo.E('_ZN7Encount12forceEncountEv'), c.call(mo.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
    for i in range(900):
        mo.step([0x4, 0x8][(i // 20) % 2], 0)
        if mo.etat.partie == MO.PARTIE_COMBAT: return True
    return False

def politique(scenario, type_menu, cases, membre_idx):
    """-> indice de bouton a valider pour ce menu."""
    t = {v: k for k, v in cases.items()}
    if type_menu == 30: return 1 if scenario == 'fuite' else 0
    if type_menu == 36 and scenario == 'objet': return 'page' if cases.get((5, 0)) == '1/3' else 0
    if type_menu == 32:
        if scenario == 'sort' and 'Magie' in t and 'Ragnar' not in cases.values(): return t['Magie'][0]
        if scenario == 'defense': return 3
        if scenario == 'objet' and 'Objets' in t: return t['Objets'][0]
        return 0
    return 0

def jouer(mo, scenario='attaque', defil=2, max_images=4000, verbeux=False):
    """Joue un combat. -> liste d'evenements (image relative, texte) et nombre d'images du moteur."""
    mo.imposer_defilement(defil)
    base = mo.images; ev = []
    def j(s): ev.append((mo.images - base, s))
    st = {'rel': None, 'menu': None, 'att': 0, 'msgatt': 0, 'msg': None}
    fin = None
    for i in range(max_images):
        p = d = 0
        if st['rel'] is not None: mo.envoyer_menu(st['rel'], 1, -1, 0); st['rel'] = None
        port = mo.menu_actif()
        if port is not None and not mo.msg_visible:
            f = mo.ui.fen(port)
            if port != st['menu']: st['att'] = 0
            st['att'] += 1
            if st['att'] % 4 == 0:
                idx = politique(scenario, f['type'], f['cases'], 0)
                if idx == 'page': mo.envoyer_menu(port, 1, -1, 4)
                else: mo.envoyer_menu(port, 1, idx, 0x10)
                st['rel'] = port
        elif mo.msg_visible and mo.etat_message()[1] in (3, 5):
            st['msgatt'] += 1
            if st['msgatt'] > 100 and st['msgatt'] % 4 == 0: p = d = MO.A          # message final qui attend une touche
        else: st['msgatt'] = 0
        prec = mo.etat.partie; pq = mo.step(p, d)
        m = mo.menu_actif()
        if m != st['menu']:
            if m is not None: j('MENU ouvre type %s %s' % (mo.ui.fen(m)['type'], sorted(mo.ui.fen(m)['cases'].values())[:4]))
            else: j('MENU ferme')
            st['menu'] = m
        em = mo.etat_message(); k = (em[0], em[1] == 2, mo.msg_visible)
        for dg in mo.ui.degats: j('NOMBRE %s' % (dg,))
        mo.ui.degats = []
        for t, a, f in pq:
            if t == 35: j('SE %d' % a[0])
            elif t == 21 and a[1] > 5000: j('EFFET modele %d (emplacement %d)' % (a[1], a[0]))
            elif t == 9: j('FONDU %d' % a[0])
            elif t == 34: j('ECRAN effet %d' % a[0])
        if em[1] == 2 and st['msg'] != 'ecrit': st['msg'] = 'ecrit'; j('MSG ecriture')
        elif em[1] == 5 and st['msg'] != 'attente': st['msg'] = 'attente'; j('MSG attente')
        elif em[1] not in (2, 5): st['msg'] = None
        if prec == MO.PARTIE_COMBAT and mo.etat.partie != MO.PARTIE_COMBAT: fin = mo.images; j('FIN partie')
        if fin and mo.images > fin + 40: break
    return ev
