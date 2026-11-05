"""Rend la fenetre Make_BattleIM (type 35, liste des sorts en COMBAT) avec le vrai moteur de dessin et la vraie police.
usage: render35.py OUT.png S NOM|COUT [NOM|COUT ...]   (jusqu'a 4 rangees ; \\t = tabulation) ; ecrit OUT.json (mesures du premier cout)."""
import sys, os, json
sys.path.insert(0, '/home/claude/dq4-portage')
import numpy as np, pyglet
pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from pyglet import gl
from PIL import Image
out = sys.argv[1]; S = float(sys.argv[2]); rows = [a.replace('\\t', '\t').split('|') for a in sys.argv[3:]]
W, H = 1280, 380
win = pyglet.window.Window(W, H, visible=True)
from dq4_pc.menus import ui_menu as UM
C = '/tmp/audit_final/interface/uicache'
ml = UM.PageLayout(os.path.join(C, 'ui_layout.json'), os.path.join(C, 'ui_frameData.bin'))
sheets = {0: np.array(Image.open(os.path.join(C, 'ui_MenuTexture.png')).convert('RGBA')), 1: np.array(Image.open(os.path.join(C, 'ui_Button.png')).convert('RGBA'))}
render = UM.Render(ml, sheets, os.path.join(C, 'ui_font.otf'))
wnd = UM.Window(ml, 35)
for i in range(4):
    wnd.code(i, 2 if i < len(rows) else 0)
    if i < len(rows): wnd.param_str(i, 0, rows[i][0]); wnd.param_str(i, 1, rows[i][1])
cost_ids = [1753, 1819, 1885, 1951]; plate_ids = [1704, 1770, 1836, 1902]
cx = W / 2; cy = H - 100 + 218 * S
win.switch_to(); gl.glClearColor(0.1, 0.3, 0.08, 1); win.clear()
render.draw_all([wnd], cx, cy, S, (W, H))
pyglet.image.get_buffer_manager().get_color_buffer().save(out)
bm = render.texts.bitmap; res = []
for k, r in enumerate(rows):
    node = wnd.N[cost_ids[k]]; pl = wnd.N[plate_ids[k]]; u = node['text']['characterSize'] * 0.1; txt = node['text']['text']
    res.append(dict(row=k, text=txt, x_anchor=node['pos'][0], plate_x=[pl['pos'][0] - 94, pl['pos'][0] + 94], plate_z=[pl['pos'][2] - 26, pl['pos'][2] + 26], width_px=bm.width_px(txt), width_u=bm.width_px(txt) * u,
                    end_x=node['pos'][0] + bm.width_px(txt) * u, over=node['pos'][0] + bm.width_px(txt) * u - (pl['pos'][0] + 94), tscale=node['tscale'], fit_x=node.get('fit_x'), z_text_center=node['pos'][2] - ml.hdr['lang']['dy']))
json.dump(dict(S=S, cx=cx, cy=cy, rows=res), open(out + '.json', 'w'), indent=1); print(json.dumps(res))
