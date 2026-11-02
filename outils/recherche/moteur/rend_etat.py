"""Rendu synthetique : icones d'etat (types 4, 20, 60) et fleche de cible (type 29) ; xvfb-run -a python3 rend_etat.py <prefixe> ; DQ4_SRC = dossier dq4_pc"""
import sys, os
sys.path.insert(0, os.environ.get('DQ4_SRC', '/home/claude/wt-audit/dq4_pc'))
import numpy as np, pyglet
from pyglet import gl
from PIL import Image
import ui_menu as UI
pref = sys.argv[1]
W, H = 450, 800
win = pyglet.window.Window(W, H, visible=False)
cache = '/tmp/r3_res'
ml = UI.MiseEnPage('/tmp/r3_layout/ui_layout.json', cache + '/ui_frameData.bin')
fe = {0: np.array(Image.open(cache + '/ui_MenuTexture.png').convert('RGBA')), 1: np.array(Image.open(cache + '/ui_Button.png').convert('RGBA'))}
rd = UI.Rendu(ml, fe, cache + '/ui_font.otf')
def rendre(f, nom):
    rd.voisins = [f]; win.switch_to(); gl.glClearColor(0.18, 0.25, 0.4, 1); win.clear(); rd.dessiner([f], W / 2, H / 2, 1.0, (W, H))
    pyglet.image.get_buffer_manager().get_color_buffer().save(nom); print('ecrit', nom)
VALS = [0, 1 | (2 << 16), 2 | (1 << 16), 2 | 4 | (0 << 16)]            # sain ; mort (croix, nom rouge) ; poison a l'article de la mort (tete de mort, nom jaune) ; poison + sort scelle (oeil)
for typ, no in ((4, 7), (20, 5)):
    f = UI.Fenetre(ml, typ)
    for (i, n), p in sorted(f.params.items()):
        pt, ib = f._ib(p) if 'custom' not in p else (None, None)
        if ib and ib['k'] == 'text': f.param_str(i, n, ['Ragnar', 'Doc', 'Alena', 'Torneko'][i % 4] if n == 0 else 'x%d' % n)
    for i, v in enumerate(VALS): f.param_int(i, no, v)
    rendre(f, '%s_type%d.png' % (pref, typ))
f = UI.Fenetre(ml, 29)
for i in range(4): f.code(i, 0)
f.code(5, 0)
if hasattr(f, 'tick'):
    t0 = f.t_curseur
    rendre(f, pref + '_fleche_0s.png'); f.tick(t0 + 0.8); rendre(f, pref + '_fleche_0_8s.png'); f.tick(t0 + 1.5); rendre(f, pref + '_fleche_1_5s.png')
else: rendre(f, pref + '_fleche_0s.png')
