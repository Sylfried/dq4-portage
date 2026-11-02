"""Rend hors ecran une fenetre d'un type donne avec des parametres choisis (sans moteur) : xvfb-run -a python3 rend_type.py <type> <sortie.png> [--code i=c ...] [--avant-codes]
DQ4_SRC = dossier dq4_pc a utiliser (defaut : le worktree /home/claude/wt-audit). Ne modifie rien dans le depot."""
import sys, os
sys.path.insert(0, os.environ.get('DQ4_SRC', '/home/claude/wt-audit/dq4_pc'))
import numpy as np, pyglet
from pyglet import gl
from PIL import Image
import ui_menu as UI
typ = int(sys.argv[1]); sortie = sys.argv[2]
codes = [tuple(int(x) for x in a.split('=')) for a in sys.argv[3:] if '=' in a]
W, H = 450, 800
win = pyglet.window.Window(W, H, visible=False)
cache = '/tmp/r3_res'
ml = UI.MiseEnPage('/tmp/r3_layout/ui_layout.json', cache + '/ui_frameData.bin')
fe = {0: np.array(Image.open(cache + '/ui_MenuTexture.png').convert('RGBA')), 1: np.array(Image.open(cache + '/ui_Button.png').convert('RGBA'))}
rd = UI.Rendu(ml, fe, cache + '/ui_font.otf'); f = UI.Fenetre(ml, typ)
def textes():
    if typ == 54:
        f.param_str(3, 0, 'Choisir une sauvegarde')
        for i, (a, b) in enumerate([('Chapitre 1', 'Ragnar  Nv.5'), ('Chapitre 2', 'Alena  Nv.9'), ('Chapitre 3', 'Torneko  Nv.12')]): f.param_str(i, 0, a); f.param_str(i, 1, b); f.param_str(i, 2, '')
    elif typ == 66:
        for i, s in enumerate(['Prier', 'Ressusciter', 'Guerir poison', 'Lever malediction', 'Sauvegarder']): f.param_str(i, 0, s)
        f.param_str(6, 0, 'Eglise'); f.param_str(5, 0, 'Quitter')
if '--avant-codes' in sys.argv:
    textes()
    for i, c in codes: f.code(i, c)
else:
    for i, c in codes: f.code(i, c)
    textes()
rd.voisins = [f]
win.switch_to(); gl.glClearColor(0.18, 0.25, 0.4, 1); win.clear()
rd.dessiner([f], W / 2, H / 2, 1.0, (W, H))
pyglet.image.get_buffer_manager().get_color_buffer().save(sortie); print('ecrit', sortie)
if typ == 66: print('zones', [(b[0], hex(b[1]), [round(x, 1) for x in b[2:6]]) for b in sorted(f.boutons())])
