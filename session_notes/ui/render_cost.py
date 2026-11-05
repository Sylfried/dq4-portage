"""Rend la fenetre Make_NameButton (type 8) de la liste des magies avec le vrai moteur de dessin (UM.Render) et la vraie police SE-GARRIR.
usage: render_cost.py OUT.png NOM COUT [S] ; chaines : NOM, COUT (\\t pour la tabulation). Ecrit aussi OUT.json (mesures)."""
import sys, os, json
sys.path.insert(0, '/home/claude/dq4-portage')
import numpy as np, pyglet
pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from pyglet import gl
from PIL import Image
out = sys.argv[1]; name = sys.argv[2]; cost = sys.argv[3].replace('\\t', '\t'); S = float(sys.argv[4]) if len(sys.argv) > 4 else 1.6
W, H = 1280, 360
win = pyglet.window.Window(W, H, visible=True)
from dq4_pc.menus import ui_menu as UM
C = '/tmp/audit_final/interface/uicache'
ml = UM.PageLayout(os.path.join(C, 'ui_layout.json'), os.path.join(C, 'ui_frameData.bin'))
sheets = {0: np.array(Image.open(os.path.join(C, 'ui_MenuTexture.png')).convert('RGBA')), 1: np.array(Image.open(os.path.join(C, 'ui_Button.png')).convert('RGBA'))}
render = UM.Render(ml, sheets, os.path.join(C, 'ui_font.otf'))
wnd = UM.Window(ml, 8)
for i, v in ((0, 2), (1, 0), (2, 0), (3, 0), (6, 0)): wnd.code(i, v)          # etat du vrai moteur : liste de Doc (une rangee, deux lignes)
wnd.param_str(0, 0, name); wnd.param_str(0, 1, cost)
node = wnd.N[1610]
win.switch_to(); gl.glClearColor(0.1, 0.3, 0.08, 1); win.clear()
cx = W / 2 - 79 * S; cy = H / 2 + 18 * S          # plaque (x 79, z -18) au centre de l image
render.draw_all([wnd], cx, cy, S, (W, H))
img = pyglet.image.get_buffer_manager().get_color_buffer()
img.save(out)
bm = render.texts.bitmap; u = node['text']['characterSize'] * 0.1
txt = node['text']['text']
m = dict(S=S, cx=cx, cy=cy, text=txt, node_pos=node['pos'], plate=[node['pos'][0], 79.0 - 99, 79.0 + 99], width_px=bm.width_px(txt), width_u=bm.width_px(txt) * u,
         tscale=node['tscale'], fit_x=node.get('fit_x'), tabSize=node['text'].get('tabSize'), characterSize=node['text']['characterSize'], anchor=node['text']['anchor'], dy=ml.hdr['lang']['dy'])
json.dump(m, open(out + '.json', 'w'), indent=1)
print(json.dumps(m))
