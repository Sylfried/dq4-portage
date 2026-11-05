"""usage: render_win.py OUT.png TYPE MODE [id:no=texte ...]   MODE : V (defaut) | O | P ; \\n et \\t dans les textes. Rend la fenetre `TYPE` (etat de depart, tous les codes a leur valeur par defaut) a S = 1,6."""
import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/textpos')
import tp_lib
from tp_lib import *
from pyglet import gl
out, ty, mode = sys.argv[1], int(sys.argv[2]), sys.argv[3]
S = 1.6; W, H = 760, 700
big = pyglet.window.Window(W, H, visible=True)
tp_lib.RENDERS = {True: tp_lib.make_render(), False: tp_lib.make_render()}
r = apply_mode(MODES[mode])
# la Render a ete creee sur la 1re fenetre : on refait avec ce contexte
w = UM.Window(ml, ty)
for a in sys.argv[4:]:
    k, v = a.split('=', 1); i, no = k.split(':'); w.param_str(int(i), int(no), v.replace('\\n', '\n').replace('\\t', '\t'))
if not MODES[mode]['fit']:
    for n in w.N.values(): n.pop('fit_x', None); n.pop('wrap_x', None)
for nid, n in w.N.items(): n['act'] = True
big.switch_to(); gl.glClearColor(0.1, 0.3, 0.08, 1); big.clear()
ext = w.extent() or (-400, 400)
cx = W / 2; cy = H / 2 - ((ext[0] + ext[1]) / 2) * S
r.draw_all([w], cx, cy, S, (W, H))
pyglet.image.get_buffer_manager().get_color_buffer().save(out)
print('ok', out, 'extent', ext)
