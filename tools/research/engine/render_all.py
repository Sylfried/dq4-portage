"""Rend toutes les fenetres de la mise en page avec un meme jeu de parametres (textes, icones, barres ; sans code ni valeur d'etat) : xvfb-run -a python3 render_all.py <dossier_sortie>
DQ4_SRC = dossier dq4_pc ; sert a comparer avant / apres une modification (images identiques attendues)."""
import sys, os, hashlib
sys.path.insert(0, os.environ.get('DQ4_SRC', '/home/claude/wt-audit/dq4_pc'))
import numpy as np, pyglet
from pyglet import gl
from PIL import Image
from dq4_pc.menus import ui_menu as UI
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
W, H = 450, 800
win = pyglet.window.Window(W, H, visible=False)
cache = '/tmp/r3_res'
ml = UI.PageLayout('/tmp/r3_layout/ui_layout.json', cache + '/ui_frameData.bin')
wnd = {0: np.array(Image.open(cache + '/ui_MenuTexture.png').convert('RGBA')), 1: np.array(Image.open(cache + '/ui_Button.png').convert('RGBA'))}
rd = UI.Render(ml, wnd, cache + '/ui_font.otf')
res = {}
for t in sorted(ml.types, key=int):
    d = ml.types[t]
    if d.get('err') or not d.get('nodes'): continue
    f = UI.Window(ml, int(t))
    for (i, no), p in sorted(f.params.items()):
        if 'custom' in p:
            if p['custom'].get('cls', '').endswith('BattleBar'): f.param_int(i, no, 40)
            continue
        pt, ib = f._ib(p)
        if ib is None: continue
        if ib['k'] == 'text': f.param_str(i, no, 'T%d.%d' % (i, no))
        elif ib['k'] == 'icon': f.param_int(i, no, 2 + i % 3)
        elif ib['k'] == 'bar': f.param_int(i, no, 60)
    rd.neighbors = [f]
    win.switch_to(); gl.glClearColor(0.18, 0.25, 0.4, 1); win.clear()
    rd.draw_all([f], W / 2, H / 2, 1.0, (W, H))
    img = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
    a = np.frombuffer(img.get_data('RGBA', W * 4), np.uint8)
    res[t] = hashlib.md5(a.tobytes()).hexdigest(); Image.fromarray(a.reshape(H, W, 4)[::-1]).save('%s/t%s.png' % (out, t))
open(out + '/hashes.txt', 'w').write('\n'.join('%s %s' % (k, v) for k, v in res.items()))
print(len(res), 'types rendered ->', out)
