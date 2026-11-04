"""Lanceur d'essai (hors depot) : en plein combat force, recharge successivement plusieurs decors (DQ_DECOR) avec et sans l'adoucissement des contours, a MSAA 0 et 4,
et enregistre une capture de chaque. Variables : ENC_N, CB_WT, DECORS (liste), MSAAS ("0,4"), PFX (prefixe des fichiers), CROP (x0,y0,x1,y1 en fraction), AV (liste des variantes)."""
import sys, os, time
wt = os.environ.get('CB_WT', '/home/claude/wt45-combat')
sys.path.insert(0, wt + '/dq4_pc'); os.chdir(wt + '/dq4_pc')
from dq4_pc.fenetre import jeu as F
from dq4_pc.noyau import moteur as MO
import pyglet
orig = F.Jeu.tick
st = {'enc': False, 'fait': False}
DEC = os.environ.get('DECORS', 'btl_pl_d,btl_mt_d,btl_wd_d').split(',')
MS = [int(x) for x in os.environ.get('MSAAS', '0,4').split(',')]
PFX = os.environ.get('PFX', '/tmp/cb45/dec')
VAR = os.environ.get('AV', 'avant,apres').split(',')
def tick(self, dt, muet=False):
    mo = self.moteur; c = mo.core
    if self.n == int(os.environ.get('ENC_N', '150')) and not st['enc']:
        st['enc'] = True
        c.call(mo.E('_ZN7Encount12forceEncountEv'), c.call(mo.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
    r = orig(self, dt, muet)
    if mo.etat.partie == MO.PARTIE_COMBAT and self.n_combat >= int(os.environ.get('NC', '90')) and not st['fait']:
        st['fait'] = True
        for ms in MS:
            self.reg['msaa'] = ms
            for d in DEC:
                for v in VAR:
                    if v == 'avant': os.environ['DQ_SANS_CONTOURS'] = '1'
                    else: os.environ.pop('DQ_SANS_CONTOURS', None)
                    os.environ['DQ_DECOR'] = d
                    for k, t in list(self.tex_gl.items()): t.delete()
                    self.tex_gl.clear(); self._tex_contours.clear()
                    t0 = time.time(); self._charger_carte('btl_pl_d'); dtc = time.time() - t0
                    for _ in range(2): self.dispatch_event('on_draw'); self.flip()
                    f = '%s_%s_m%d_%s.png' % (PFX, d, ms, v)
                    pyglet.image.get_buffer_manager().get_color_buffer().save(f)
                    print('capture', f, 'chargement %.2fs' % dtc, 'msaa reel', self.post.msaa, flush=True)
        os._exit(0)
    return r
F.Jeu.tick = tick
F.main()
