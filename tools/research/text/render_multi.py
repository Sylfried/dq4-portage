"""Rend plusieurs fenetres (33 cible, 29 etat, 31 plaques, 32 commandes) a l'echelle 1.688 (celle des captures de Sylfried), en mode « original » (sans recentrage) puis « recentre » :
xvfb-run python3 render_multi.py <dossier_sortie> [dq4_pc]"""
import sys, os
out = sys.argv[1]; src = sys.argv[2] if len(sys.argv) > 2 else '/home/claude/wt45-texte/dq4_pc'
sys.path.insert(0, src)
import numpy as np, pyglet
if os.environ.get('HL'): pyglet.options['headless'] = True
from pyglet import gl
from PIL import Image
from dq4_pc.menus import ui_menu as UI
S = 1.688; W, H = 810, 483
win = pyglet.window.Window(W, H, visible=False)
cache = '/tmp/uicache4'
ml = UI.PageLayout(cache + '/ui_layout.json', cache + '/ui_frameData.bin')
wnd = {0: np.array(Image.open(cache + '/ui_MenuTexture.png').convert('RGBA')), 1: np.array(Image.open(cache + '/ui_Button.png').convert('RGBA'))}
rd = UI.Render(ml, wnd, cache + '/ui_font.otf')
def win33():
    f = UI.Window(ml, 33); f.param_str(4, 0, 'Ragnar'); f.param_str(4, 1, 'Attaquer'); f.param_str(0, 0, 'Rat volant'); f.param_str(1, 0, 'Scarapince\n\n\t×2'); return f
def win32():
    f = UI.Window(ml, 32)
    for i, t in enumerate(['Attaquer', 'Magie', 'Objets', 'Défense']): f.param_str(i, 1, t)
    f.param_str(4, 0, 'Ragnar'); return f
def win29():
    f = UI.Window(ml, 29); f.param_str(0, 1, 'Ragnar'); f.param_str(0, 2, 'PV\nPM\nNv.'); f.param_str(0, 3, ' 44\n  0\n  5'); f.param_str(1, 1, 'Doc'); f.param_str(1, 2, 'PV\nPM\nNv.'); f.param_str(1, 3, ' 33\n 30\n  ?'); f.code(0, 0); f.code(1, 0); return f
def win31():
    f = UI.Window(ml, 31)
    f.plate(0, 'Rat volant', [66, 66, -3, -1, 3, 0], 1); f.plate(1, 'Scarapince\n\n\t×2', [66, 66, -3, -1, 3, 0], 1)
    f.arrange(2, None)
    pl = f.pl; node = f.N[pl[1]['cadre']]; nt = f.N[pl[1]['texte']]; node['pos'][0] += 160; nt['pos'][0] += 160
    return f
CX = float(os.environ.get('CX', '405')); CY = float(os.environ.get('CY', '240'))
os.makedirs(out, exist_ok=True)
for mode in ('orig', 'cen'):
    UI.TEXT_CENTERING = (mode == 'cen')
    for name_str, mk in (('t33', win33), ('t32', win32), ('t29', win29), ('t31', win31)):
        f = mk(); rd.neighbors = [f]
        win.switch_to(); gl.glClearColor(0.1, 0.4, 0.1, 1); win.clear()
        rd.draw_all([f], CX if name_str != 't33' else 402.7, {'t33': 692.0, 't32': 692.0, 't29': -150.0}.get(name_str, CY), S, (W, H))
        im = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
        a = np.frombuffer(im.get_data('RGBA', W * 4), np.uint8).reshape(H, W, 4)[::-1]
        Image.fromarray(a[..., :3].copy()).save('%s/%s_%s.png' % (out, name_str, mode)); print('written', name_str, mode, flush=True)

# ---- feuilles de contact : fenetres variees (portrait 450 x 800, echelle 1), textes d'exemple dans toutes les cases texte
EX = ['Ragnar', 'Épée de fer', 'PV  44', 'Potion', 'Objets', 'Quitter', 'Guérir', 'Alena']
def generic_win(typ):
    f = UI.Window(ml, typ); k = 0
    for (i, no), p in sorted(f.params.items()):
        if 'custom' in p: continue
        pt, ib = f._ib(p)
        if ib and ib['k'] == 'text': f.param_str(i, no, EX[k % len(EX)]); k += 1
    return f
W2, H2 = 450, 800
win2 = pyglet.window.Window(W2, H2, visible=False)
rd2 = UI.Render(ml, wnd, cache + '/ui_font.otf')
TYPES = [3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17, 19, 20, 21, 24, 28, 30, 34, 35, 36, 44, 46, 53, 54, 57, 58, 60, 62, 66]
for typ in TYPES:
    for mode in ('orig', 'cen'):
        UI.TEXT_CENTERING = (mode == 'cen')
        try:
            f = generic_win(typ); rd2.neighbors = [f]
            win2.switch_to(); gl.glClearColor(0.1, 0.4, 0.1, 1); win2.clear()
            rd2.draw_all([f], W2 / 2, H2 / 2, 1.0, (W2, H2))
            im = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
            a = np.frombuffer(im.get_data('RGBA', W2 * 4), np.uint8).reshape(H2, W2, 4)[::-1]
            Image.fromarray(a[..., :3].copy()).save('%s/g%d_%s.png' % (out, typ, mode))
        except Exception as e: print('error', typ, mode, repr(e), flush=True)
    print('written g', typ, flush=True)
