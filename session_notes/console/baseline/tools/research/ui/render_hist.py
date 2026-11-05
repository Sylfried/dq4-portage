"""Rendu hors moteur de la fenetre Historique (iteration rapide) : python3 render_hist.py OUTPUT.png [onglet] [filtre] [fin] [largeur] [hauteur]"""
import sys, os, types
WT = os.environ.get('WT', '/home/claude/wt45-ui')
sys.path.insert(0, WT + '/dq4_pc'); sys.path.insert(0, WT + '/outils')
os.chdir(WT + '/dq4_pc')
import numpy as np
import pyglet
from pyglet import gl
from PIL import Image
out = sys.argv[1]; tab = int(sys.argv[2]) if len(sys.argv) > 2 else 0; sieve = len(sys.argv) > 3 and sys.argv[3] == '1'; end = int(sys.argv[4]) if len(sys.argv) > 4 else -1
W = int(sys.argv[5]) if len(sys.argv) > 5 else 1280; H = int(sys.argv[6]) if len(sys.argv) > 6 else 720
win = pyglet.window.Window(W, H, visible=True)
from dq4_pc.menus import ui_menu as UM; from dq4_pc.persistence import settings as RG; from dq4_pc.menus import pause as PA; from dq4_pc.menus import ui_history as UH; from dq4_pc.core import history as HI
import test_message_history as T
CACHE = '/tmp/uicache4'
ml = UM.PageLayout(os.path.join(CACHE, 'ui_layout.json'), os.path.join(CACHE, 'ui_frameData.bin'))
sheets = {0: np.array(Image.open(os.path.join(CACHE, 'ui_MenuTexture.png')).convert('RGBA')), 1: np.array(Image.open(os.path.join(CACHE, 'ui_Button.png')).convert('RGBA'))}
render = UM.Render(ml, sheets, os.path.join(CACHE, 'ui_font.otf'))
h = T.new(None); T.fill(h)
J = types.SimpleNamespace(reg=RG.Settings(None), history=h, width=W, height=H, ui_render=render, mouse=None, args=types.SimpleNamespace(cache=CACHE), pause_game=lambda o: None)
P = PA.Pause(J); P.opened = True; P.stack = ['historique']
v = UH.HistoryView(P); v.enter(tab)
if sieve: v.toggle_filter()
if end >= 0: v.end = v.selected = end
P.mouse_mode = False
win.switch_to(); gl.glClearColor(0.1, 0.25, 0.1, 1); win.clear()
v.draw_all()
pyglet.image.get_buffer_manager().get_color_buffer().save(out)
print('ok', out, 'vis', v.vis, 'elements', len(v.elements))
