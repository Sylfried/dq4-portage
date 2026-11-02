"""Harnais moteur seul (wt45-son) : trace des demandes de son (paquets 35/36/37 + appels SoundManager) avec leur appelant, messages et PV."""
import os, sys, struct, time, shutil, collections
sys.path.insert(0, '/home/claude/wt45-son/dq4_pc')
os.chdir('/home/claude/wt45-son/dq4_pc')
import unicorn
import moteur as MO
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'
PAS_JOUEUR, OFF_HS = 0x530, 0x58

def nouveau(nom='son45'):
    ecr = '/tmp/sv_' + nom; shutil.rmtree(ecr, ignore_errors=True); os.makedirs(ecr)
    return MO.Moteur(APK, SAVES, ecr)

class Trace:
    """Crochets sur les fonctions SoundManager / Sound du moteur : qui demande quoi."""
    FN = ['_ZN12SoundManager6playSeEi', '_ZN12SoundManager7playBgmEi', '_ZN12SoundManager4playEi', '_ZN12SoundManager9playStartEi', '_ZN12SoundManager11playRestartEi',
          '_ZN12SoundManager7stopBgmEi', '_ZN12SoundManager4stopEi', '_ZN12SoundManager10battlePlayEv', '_ZN12SoundManager10battleStopEv', '_ZN12SoundManager8townPlayEv',
          '_ZN12SoundManager9fieldPlayEv', '_ZN12SoundManager12lastBossPlayEv', '_ZN12SoundManager11crusingPlayEv']
    def __init__(self, mo):
        self.mo = mo; c = mo.core; self.c = c; self.evt = []
        for n in self.FN:
            try: a = c.export(n)
            except Exception: a = None
            if not a: print('absent', n); continue
            c.uc.hook_add(unicorn.UC_HOOK_CODE, self._h, n.split('SoundManager')[1], a, a)
    def _h(self, uc, adr, sz, nom):
        c = self.c
        w0 = uc.reg_read(c.XREG[0]) & 0xffffffff
        pile = []
        fp = uc.reg_read(c.XREG[29]); pile.append(c.where(uc.reg_read(c.XREG[30])))
        for _ in range(5):
            try: nfp, nlr = struct.unpack('<QQ', c.mem(fp, 16))
            except Exception: break
            if not nfp or nfp <= fp: break
            pile.append(c.where(nlr)); fp = nfp
        self.evt.append((self.mo.images, nom, w0, pile))

def pv(mo, i):
    c = mo.core; orig = c.export('_ZN6status9PartyData15originalPlayer_E')
    h = c.mem(orig + PAS_JOUEUR * i + OFF_HS, 0x30); return struct.unpack_from('<4H', h, 0x22), h[0xe]

def membres(mo):
    c = mo.core; party = c.export('_ZN6status7g_PartyE')
    return [i for i in struct.unpack('<13I', c.mem(party + 0x304, 13 * 4)) if i]

def poser_pv(mo, i, hp):
    c = mo.core; orig = c.export('_ZN6status9PartyData15originalPlayer_E')
    c.mem_w(orig + PAS_JOUEUR * i + OFF_HS + 0x22, struct.pack('<H', hp))

def pq_sons(pq): return [(t, a[0]) for t, a, f in pq if t in (35, 36, 37) and a]

class Combat:
    """Lance un combat force (monstres imposes) et le pilote : A partout (menu, message). journal = [(image, genre, detail)]"""
    def __init__(self, mo, tr, monstres=((3, 1),), hp=None, verbeux=False):
        self.mo, self.tr, self.c = mo, tr, mo.core; self.journal = []; self.verbeux = verbeux
        c = self.c
        self.enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
        self.monstres = list(monstres)
        def forcer(u, adr, sz, ud):
            for j in range(4):
                i, n = self.monstres[j] if j < len(self.monstres) else (0, 0)
                c.mem_w(self.enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(self.enc + 0x44 + 4 * j, struct.pack('<I', n))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, forcer, None, a, a)
        c.uc.ctl_flush_tb()
        self.hp = hp; self.bouton = {}

    def log(self, genre, det):
        self.journal.append((self.mo.images, genre, det))
        if self.verbeux: print('%5d %-6s %s' % (self.mo.images, genre, det), flush=True)

    def lancer(self, max_pas=9000, avant_boucle=None, apres_combat=600):
        mo, c = self.mo, self.c
        if self.hp is not None:
            for i, h in zip(membres(mo), self.hp):
                if h is not None: poser_pv(mo, i, h)
        ev0 = len(self.tr.evt)
        c.call(c.export('_ZN6Global11startBattleEv'), mo._global(), label='startBattle')
        st = {'rel': None, 'att': 0}; fin = None
        for k in range(max_pas):
            p = d = 0
            if st['rel'] is not None: mo.envoyer_menu(st['rel'], 1, -1, 0); st['rel'] = None
            port = mo.menu_actif()
            if port is not None and not mo.msg_visible:
                st['att'] += 1
                if st['att'] % 4 == 0:
                    bt = self.bouton.get(mo.ui.f[port].get('type'), -1); mo.envoyer_menu(port, 1, bt, 0x10); st['rel'] = port; self.log('menu', 'A (bouton %s) sur port %s %s' % (bt, port, mo.ui.f[port].get('type')))
            elif mo.msg_visible and (mo.ui.msg.get('feed') or mo.etat_message()[1] in (3, 5)):
                st['att'] += 1
                if st['att'] % 4 == 0: p = d = MO.A
            else: st['att'] = 0
            if avant_boucle: avant_boucle(self, k)
            prec = mo.etat.partie; pq = mo.step(p, d); mo.ui.degats = []
            for t, v in pq_sons(pq): self.log('son', {35: 'SE %d', 36: 'stopSE %d', 37: 'BGM %#x'}[t] % v)
            for e in self.tr.evt[ev0:]: self.log('appel', '%s(%d) <- %s' % (e[1], e[2], ' < '.join(x.split('+')[0] for x in e[3][:4])))
            ev0 = len(self.tr.evt)
            for s in mo.capteur.vider(): self.log('texte', str({k: (v if k != 'texte' else v[:90]) for k, v in s.items() if k in ('texte', 'genre', 'val', 'cat')}))
            ph = [pv(mo, i)[0][0] for i in membres(mo)]
            if ph != getattr(self, '_ph', None): self._ph = ph; self.log('pv', ph)
            if mo.etat.partie != MO.PARTIE_COMBAT and prec == MO.PARTIE_COMBAT: fin = mo.images; self.log('fin', 'partie %#x' % mo.etat.partie)
            if fin is not None and mo.images - fin > apres_combat: break
        return fin
