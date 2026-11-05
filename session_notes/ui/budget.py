import sys
sys.path.insert(0, '/home/claude/dq4-portage')
import pyglet
pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.menus import ui_menu as UM
C = '/tmp/audit_final/interface/uicache'
bm = UM.BitmapFont(C + '/ui_garrir.json', C + '/ui_garrir.png'); u = 0.663
print('espace', bm.G[32][0], 'px ; champ "  2" =', bm.width_px('  2'), 'px ; champ " 10" =', bm.width_px(' 10'), 'px ; tab = 8 espaces =', 8 * bm.G[32][0], 'px')
reach = 82.0 / u; marge = 7.0 / u
print('portee ancre -> bord de plaque : 82 u = %.1f px ; avec marge de 7 u : %.1f px' % (reach, reach - marge))
for lab in ('Coût en PM:', 'MP Cost:', 'Coût PM:', 'Coût:', 'PM:', 'Coût en PM :', 'Coût PM :'):
    w = bm.width_px(lab)
    for fld in ('  2', ' 10'):
        tot = bm.width_px(lab + ' ' * 8 + fld)
        print('%-14s %3d px | nombre %-4r : total %3d px = %5.1f u : marge au bord %+6.1f u' % (lab, w, fld, tot, tot * u, 82.0 - tot * u))
