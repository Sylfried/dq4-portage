"""Lanceur d'essai (hors depot) : fenetre normale du worktree wt45-combat ; journal des transitions de combat avec l'heure reelle.
Variables : ENC_N (tick ou on force la rencontre), CRIT=1 (coup critique force), CB_LOG (fichier de journal), CB_WT (worktree)."""
import sys, os, struct, time
wt = os.environ.get('CB_WT', '/home/claude/wt45-combat')
sys.path.insert(0, wt + '/dq4_pc'); os.chdir(wt + '/dq4_pc')
from dq4_pc.window import game as F
from dq4_pc.core import engine as ENGINE
import unicorn
orig = F.Game.tick
LOG = os.environ.get('CB_LOG', '/tmp/cb45/gl.log'); open(LOG, 'w').close()
st = {'enc': False, 'prev': None, 't0': None, 'crit': False}
def note(s):
    with open(LOG, 'a') as f: f.write(s + '\n')
def tick(self, dt, mute=False):
    eng = self.engine; c = eng.core; L = c.LIB_BASE
    if os.environ.get('CRIT') == '1' and not st['crit']:
        st['crit'] = True
        def f1(uc, a, sz, u):
            x20 = uc.reg_read(c.XREG[20]) & 0xffffffffffff
            if struct.unpack('<I', bytes(c.mem(x20 + 8, 4)))[0] == 0: c.mem_w(L + 0x25c6ed, b'\x01')      # seulement quand l'acteur est de notre cote ([x20 + 8] = 0 : le heros ; 1 : les monstres, qui tirent leur critique au sort)
        c.uc.hook_add(unicorn.UC_HOOK_CODE, f1, None, L + 0x1a81dc, L + 0x1a81dc); c.uc.ctl_flush_tb()
    if os.environ.get('MONSTRE') and not st.get('mon'):
        st['mon'] = True
        enc = c.call(eng.E('_ZN7Encount12getSingletonEv'), label='enc'); idm = int(os.environ['MONSTRE'])
        def force(u, addr, sz, ud):                                  # rencontre : un seul monstre faible (Encount + 0x34 : numero, + 0x44 : nombre)
            for j in range(4):
                i, n = (idm, 1) if j == 0 else (0, 0)
                c.mem_w(enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(enc + 0x44 + 4 * j, struct.pack('<I', n))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, force, None, a, a); c.uc.ctl_flush_tb()
    if self.n == int(os.environ.get('ENC_N', '150')) and not st['enc']:
        st['enc'] = True
        c.call(eng.E('_ZN7Encount12forceEncountEv'), c.call(eng.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
        note('FORCE tick n=%d img=%d' % (self.n, eng.frames))
    r = orig(self, dt, mute)
    e = eng.state
    if os.environ.get('FXSHOT'):
        ids = set(e.models.values()); target_pos = 5344 if os.environ.get('CRIT') == '1' else 5303
        if target_pos in ids:
            st['fx'] = st.get('fx', 0) + 1
            if st['fx'] <= 16 and st['fx'] % 2 == 1:
                import pyglet
                self.dispatch_event('on_draw'); self.flip()
                pyglet.image.get_buffer_manager().get_color_buffer().save('/tmp/cb45/fx_%s_%02d.png' % (os.environ['FXSHOT'], st['fx']))
                note('FX %s %d img=%d slots=%s' % (os.environ['FXSHOT'], st['fx'], eng.frames, sorted(e.models.items())))
    lookup_key = (e.effect is not None, e.load_wait is not None, e.fade['n'] >= 1, e.background_fade['n'] >= 1, e.part)
    if lookup_key != st['prev']:
        t = time.perf_counter()
        if st['t0'] is None: st['t0'] = t
        note('T=%.3f img=%d effet=%d attente=%d fondu=%d fond=%d partie=%#x fa=%.2f fn=%d vitesse=%s' % (t - st['t0'], eng.frames, lookup_key[0], lookup_key[1], lookup_key[2], lookup_key[3], lookup_key[4], e.fade['a'], e.fade['n'], self.reg['vitesse_combat']))
        st['prev'] = lookup_key
    if e.part == ENGINE.PART_BATTLE: st['vu'] = True
    if st.get('vu') and e.part != ENGINE.PART_BATTLE and 'fin' not in st: st['fin'] = self.n
    if 'fin' in st and self.n > st['fin'] + int(os.environ.get('POST', '120')): note('QUIT n=%d' % self.n); os._exit(0)
    return r
F.Game.tick = tick
F.main()
