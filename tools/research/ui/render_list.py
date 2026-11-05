"""Liste deroulante « Interface a modifier » hors moteur : python3 render_list.py OUTPUT.png [courant] [haut]"""
import sys, os, types
WT = os.environ.get('WT', '/home/claude/wt45-ui')
sys.path.insert(0, WT + '/dq4_pc'); os.chdir(WT + '/dq4_pc')
import numpy as np, pyglet
from pyglet import gl
from PIL import Image
out = sys.argv[1]; current_item = sys.argv[2] if len(sys.argv) > 2 else 'boutons'; topmost = sys.argv[3] if len(sys.argv) > 3 else None
W, H = 1280, 720
win = pyglet.window.Window(W, H, visible=True)
from dq4_pc.menus import ui_menu as UM; from dq4_pc.persistence import settings as RG; from dq4_pc.menus import pause as PA
CACHE = '/tmp/uicache4'
ml = UM.PageLayout(os.path.join(CACHE, 'ui_layout.json'), os.path.join(CACHE, 'ui_frameData.bin'))
sheets = {0: np.array(Image.open(os.path.join(CACHE, 'ui_MenuTexture.png')).convert('RGBA')), 1: np.array(Image.open(os.path.join(CACHE, 'ui_Button.png')).convert('RGBA'))}
render = UM.Render(ml, sheets, os.path.join(CACHE, 'ui_font.otf'))
names = {n: [1] for n in PA.WINDOW_NAMES if n not in ('boutons', 'msg', 'bouton_vitesse')}
J = types.SimpleNamespace(reg=RG.Settings(None), width=W, height=H, ui_render=render, mouse=None, args=types.SimpleNamespace(cache=CACHE), pause_game=lambda o: None, window_names=lambda: names,
                          sound=types.SimpleNamespace(active=True, listening=False), new_sample=lambda: None,
                          _lbl=lambda t, size_value, color=(255, 255, 255, 255), fonts=(): pyglet.text.Label(t, font_name=tuple(fonts) + ('DejaVu Sans', 'Arial'), font_size=size_value, color=color, anchor_x='left', anchor_y='baseline'))
P = PA.Pause(J); P.opened = True; P.stack = ['interface']; P.target = current_item
entry = P._entries_interface()[0]; vals = entry['vals']
P.open_dropdown = [0, vals.index(current_item)]; P.entries_top = (vals.index(topmost) if topmost and not topmost.isdigit() else (int(topmost) if topmost else None)); P.entries_cur_seen = None; P.dragging_entries = None; P.mouse_mode = False
k = max(0.75, H / 900.0)
win.switch_to(); gl.glClearColor(0.12, 0.2, 0.3, 1); win.clear()
P._border(900 - 380 * k, 330, 380 * k, 330, k)
P._draw_entries(entry, (560, 520), 900, k, 18 * k)
pyglet.image.get_buffer_manager().get_color_buffer().save(out)
print('ok', out, len(vals))
