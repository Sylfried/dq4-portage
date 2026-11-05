import sys; sys.path.insert(0, '.')
from tp_lib import *
for (i, no) in ((4, 0), (4, 2), (0, 5), (2, 0)):
    for s in ('Abandonner', 'Doubler', 'Garder', 'Changer'):
        P = measure(48, i, no, s, 'P'); V = measure(48, i, no, s, 'V')
        if not P or not V: print(i, no, s, 'rien'); continue
        w0 = UM.Window(ml, 48); c = container(w0, w0.N[[n for n in w0.N if 0] or list(w0.N)[0]]) if False else None
        print('cell(%d,%d) %-11s P: largeur %.1f xl %.1f xr %.1f | V: largeur %.1f xl %.1f xr %.1f ts %.3f | dbase %.2f' % (i, no, s, P['xr'] - P['xl'], P['xl'], P['xr'], V['xr'] - V['xl'], V['xl'], V['xr'], V['ts'], V['base0'] - P['base0']))
