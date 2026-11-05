"""Rend (hors ecran) les fenetres du moteur dans l'etat ou la sauvegarde est arrivee a la condition voulue, avec la mise en page /tmp/r3_layout et le rendu de la visionneuse.
Usage : xvfb-run -a python3 render_battle.py <slot> <sortie.png> [attente_texte_action=1] ; ne modifie rien dans le depot."""
import sys, os
sys.path.insert(0, '/tmp/specs'); sys.path.insert(0, os.environ.get('DQ4_SRC', '/home/claude/wt-audit/dq4_pc'))
import numpy as np, pyglet
from pyglet import gl
from PIL import Image
from harness import *
from dq4_pc.menus import ui_menu as UI
slot = int(sys.argv[1]); output = sys.argv[2]
eng = start_engine(slot)
for i in range(100): eng.step(0, 0x10 if i % 10 == 0 else 0)
if eng.state.part != ENGINE.PART_FIELD:
    eng.start_field()
    for i in range(120): eng.step(0, 0)
c = eng.core
sing = c.call(eng.E('_ZN7Encount12getSingletonEv'), label='enc'); c.call(eng.E('_ZN7Encount12forceEncountEv'), sing, label='force')
for i in range(600):
    eng.step([0x4, 0x8][(i // 20) % 2], 0)
    if eng.state.part == ENGINE.PART_BATTLE: break
found = False
for i in range(3000):
    p = eng.active_menu(); a = 0
    if p is not None and i % 15 == 0: eng.send_menu(p, 1, -1, 0x10)
    elif p is not None and i % 15 == 1: eng.send_menu(p, 1, -1, 0)
    elif p is None and i % 10 == 0: a = 0x10
    eng.step(0, a)
    f = eng.ui.f.get(12)
    if f and f['cases'].get((0, 4)) and f['vis']: found = True; break
print('action text found', found, 'frame', eng.frames)
W, H = 450, 800
win = pyglet.window.Window(W, H, visible=False)
cache = '/tmp/r3_res'
ml = UI.PageLayout('/tmp/r3_layout/ui_layout.json', cache + '/ui_frameData.bin')
wnd = {0: np.array(Image.open(cache + '/ui_MenuTexture.png').convert('RGBA')), 1: np.array(Image.open(cache + '/ui_Button.png').convert('RGBA'))}
rd = UI.Render(ml, wnd, cache + '/ui_font.otf'); g = UI.Manager(ml); g.replay(eng.ui)
entries = sorted((f['ordre'], p) for p, f in eng.ui.f.items() if f['vis'] and p in g.f)
print('visible ports', [(p, eng.ui.f[p]['type']) for _, p in entries])
wins = [g.f[p] for _, p in entries]; rd.neighbors = wins
win.switch_to(); gl.glClearColor(0.18, 0.25, 0.4, 1); win.clear()
rd.draw_all(wins, W / 2, H / 2, 1.0, (W, H))
pyglet.image.get_buffer_manager().get_color_buffer().save(output)
print('written', output)
