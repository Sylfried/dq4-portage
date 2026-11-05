"""Harnais moteur seul (wt45-son) : trace des demandes de son (paquets 35/36/37 + appels SoundManager) avec leur appelant, messages et PV."""
import os, sys, struct, time, shutil, collections
sys.path.insert(0, '/home/claude/wt45-son/dq4_pc')
os.chdir('/home/claude/wt45-son/dq4_pc')
import unicorn
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'
PLAYER_STRIDE, OFF_HS = 0x530, 0x58

def new(name_str='son45'):
    wdir = '/tmp/sv_' + name_str; shutil.rmtree(wdir, ignore_errors=True); os.makedirs(wdir)
    return ENGINE.Engine(APK, SAVES, wdir)

class Trace:
    """Crochets sur les fonctions SoundManager / Sound du moteur : qui demande quoi."""
    FN = ['_ZN12SoundManager6playSeEi', '_ZN12SoundManager7playBgmEi', '_ZN12SoundManager4playEi', '_ZN12SoundManager9playStartEi', '_ZN12SoundManager11playRestartEi',
          '_ZN12SoundManager7stopBgmEi', '_ZN12SoundManager4stopEi', '_ZN12SoundManager10battlePlayEv', '_ZN12SoundManager10battleStopEv', '_ZN12SoundManager8townPlayEv',
          '_ZN12SoundManager9fieldPlayEv', '_ZN12SoundManager12lastBossPlayEv', '_ZN12SoundManager11crusingPlayEv']
    def __init__(self, eng):
        self.eng = eng; c = eng.core; self.c = c; self.evt = []
        for n in self.FN:
            try: a = c.export(n)
            except Exception: a = None
            if not a: print('absent', n); continue
            c.uc.hook_add(unicorn.UC_HOOK_CODE, self._h, n.split('SoundManager')[1], a, a)
    def _h(self, uc, addr, sz, name_str):
        c = self.c
        w0 = uc.reg_read(c.XREG[0]) & 0xffffffff
        stack = []
        fp = uc.reg_read(c.XREG[29]); stack.append(c.where(uc.reg_read(c.XREG[30])))
        for _ in range(5):
            try: nfp, nlr = struct.unpack('<QQ', c.mem(fp, 16))
            except Exception: break
            if not nfp or nfp <= fp: break
            stack.append(c.where(nlr)); fp = nfp
        self.evt.append((self.eng.frames, name_str, w0, stack))

def hit_points(eng, i):
    c = eng.core; orig = c.export('_ZN6status9PartyData15originalPlayer_E')
    h = c.mem(orig + PLAYER_STRIDE * i + OFF_HS, 0x30); return struct.unpack_from('<4H', h, 0x22), h[0xe]

def members(eng):
    c = eng.core; party = c.export('_ZN6status7g_PartyE')
    return [i for i in struct.unpack('<13I', c.mem(party + 0x304, 13 * 4)) if i]

def set_hp(eng, i, hp):
    c = eng.core; orig = c.export('_ZN6status9PartyData15originalPlayer_E')
    c.mem_w(orig + PLAYER_STRIDE * i + OFF_HS + 0x22, struct.pack('<H', hp))

def pkt_sounds(pkt): return [(t, a[0]) for t, a, f in pkt if t in (35, 36, 37) and a]

class Battle:
    """Lance un combat force (monstres imposes) et le pilote : A partout (menu, message). journal = [(image, genre, detail)]"""
    def __init__(self, eng, tr, monsters=((3, 1),), hp=None, verbose=False):
        self.eng, self.tr, self.c = eng, tr, eng.core; self.logfile = []; self.verbose = verbose
        c = self.c
        self.enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
        self.monsters = list(monsters)
        def force(u, addr, sz, ud):
            for j in range(4):
                i, n = self.monsters[j] if j < len(self.monsters) else (0, 0)
                c.mem_w(self.enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(self.enc + 0x44 + 4 * j, struct.pack('<I', n))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, force, None, a, a)
        c.uc.ctl_flush_tb()
        self.hp = hp; self.button = {}

    def log(self, kind, det):
        self.logfile.append((self.eng.frames, kind, det))
        if self.verbose: print('%5d %-6s %s' % (self.eng.frames, kind, det), flush=True)

    def launch(self, max_step=9000, before_loop=None, after_battle=600):
        eng, c = self.eng, self.c
        if self.hp is not None:
            for i, h in zip(members(eng), self.hp):
                if h is not None: set_hp(eng, i, h)
        ev0 = len(self.tr.evt)
        c.call(c.export('_ZN6Global11startBattleEv'), eng._global(), label='startBattle')
        st = {'rel': None, 'att': 0}; end = None
        for k in range(max_step):
            p = d = 0
            if st['rel'] is not None: eng.send_menu(st['rel'], 1, -1, 0); st['rel'] = None
            port = eng.active_menu()
            if port is not None and not eng.msg_visible:
                st['att'] += 1
                if st['att'] % 4 == 0:
                    bt = self.button.get(eng.ui.f[port].get('type'), -1); eng.send_menu(port, 1, bt, 0x10); st['rel'] = port; self.log('menu', 'A (bouton %s) sur port %s %s' % (bt, port, eng.ui.f[port].get('type')))
            elif eng.msg_visible and (eng.ui.msg.get('feed') or eng.message_state()[1] in (3, 5)):
                st['att'] += 1
                if st['att'] % 4 == 0: p = d = ENGINE.A
            else: st['att'] = 0
            if before_loop: before_loop(self, k)
            prev = eng.state.part; pkt = eng.step(p, d); eng.ui.damage = []
            for t, v in pkt_sounds(pkt): self.log('son', {35: 'SE %d', 36: 'stopSE %d', 37: 'BGM %#x'}[t] % v)
            for e in self.tr.evt[ev0:]: self.log('appel', '%s(%d) <- %s' % (e[1], e[2], ' < '.join(x.split('+')[0] for x in e[3][:4])))
            ev0 = len(self.tr.evt)
            for s in eng.sensor.drain(): self.log('texte', str({k: (v if k != 'texte' else v[:90]) for k, v in s.items() if k in ('texte', 'genre', 'val', 'cat')}))
            ph = [hit_points(eng, i)[0][0] for i in members(eng)]
            if ph != getattr(self, '_ph', None): self._ph = ph; self.log('pv', ph)
            if eng.state.part != ENGINE.PART_BATTLE and prev == ENGINE.PART_BATTLE: end = eng.frames; self.log('fin', 'partie %#x' % eng.state.part)
            if end is not None and eng.frames - end > after_battle: break
        return end
