import sys, os
sys.path.insert(0, '/home/claude/dq4-portage')
import pyglet
pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.menus import ui_menu as UM
C = '/tmp/audit_final/interface/uicache'
bm = UM.BitmapFont(C + '/ui_garrir.json', C + '/ui_garrir.png')
print('espace', bm.G[32][0], 'tab glyph', bm.G.get(9), 'nbsp(160)', bm.G.get(160, (None,))[0])
u = 6.63 * 0.1
X0, PL, PR = 102.0, -99.0 + 79.0, 99.0 + 79.0
print('x ancre', X0, 'plaque x', PL, PR, 'marge plaque', UM.Render.PLATE_MARGIN)
for s in ('Coût en PM:\t  2', 'Coût en PM:\t 10', 'Coût en PM:\t  0', 'Coût en PM:\t 30', 'MP Cost:\t  2', 'MP Cost:\t 10', 'Coût en PM : \t  2', 'Coût en PM :\t  2', 'PM:\t  2', 'Coût PM:\t  2', 'Coût :\t  2', 'Coût en PM:', 'MP Cost:', 'Coût en PM  2/ 30'):
    t = UM.expand_tabs(s, 8)
    w = bm.width_px(t); wu = w * u
    print('%-22r %4d px  %6.1f u  fin x=%6.1f  depassement plaque %+6.1f  depassement (bord-marge 7) %+6.1f' % (s, w, wu, X0 + wu, X0 + wu - PR, X0 + wu - (PR - 7)))
# position du nombre
for lab in ('Coût en PM:', 'MP Cost:'):
    a = bm.width_px(lab) * u; b = bm.width_px(lab + ' ' * 8 + '  ') * u
    print(lab, 'label fin x=%.1f' % (X0 + a), 'chiffre commence x=%.1f' % (X0 + b))
