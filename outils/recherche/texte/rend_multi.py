"""Rend plusieurs fenetres (33 cible, 29 etat, 31 plaques, 32 commandes) a l'echelle 1.688 (celle des captures de Sylfried), en mode « original » (sans recentrage) puis « recentre » :
xvfb-run python3 rend_multi.py <dossier_sortie> [dq4_pc]"""
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
ml = UI.MiseEnPage(cache + '/ui_layout.json', cache + '/ui_frameData.bin')
fe = {0: np.array(Image.open(cache + '/ui_MenuTexture.png').convert('RGBA')), 1: np.array(Image.open(cache + '/ui_Button.png').convert('RGBA'))}
rd = UI.Rendu(ml, fe, cache + '/ui_font.otf')
def fen33():
    f = UI.Fenetre(ml, 33); f.param_str(4, 0, 'Ragnar'); f.param_str(4, 1, 'Attaquer'); f.param_str(0, 0, 'Rat volant'); f.param_str(1, 0, 'Scarapince\n\n\t×2'); return f
def fen32():
    f = UI.Fenetre(ml, 32)
    for i, t in enumerate(['Attaquer', 'Magie', 'Objets', 'Défense']): f.param_str(i, 1, t)
    f.param_str(4, 0, 'Ragnar'); return f
def fen29():
    f = UI.Fenetre(ml, 29); f.param_str(0, 1, 'Ragnar'); f.param_str(0, 2, 'PV\nPM\nNv.'); f.param_str(0, 3, ' 44\n  0\n  5'); f.param_str(1, 1, 'Doc'); f.param_str(1, 2, 'PV\nPM\nNv.'); f.param_str(1, 3, ' 33\n 30\n  ?'); f.code(0, 0); f.code(1, 0); return f
def fen31():
    f = UI.Fenetre(ml, 31)
    f.plaque(0, 'Rat volant', [66, 66, -3, -1, 3, 0], 1); f.plaque(1, 'Scarapince\n\n\t×2', [66, 66, -3, -1, 3, 0], 1)
    f.disposer(2, None)
    pl = f.pl; nd = f.N[pl[1]['cadre']]; nt = f.N[pl[1]['texte']]; nd['pos'][0] += 160; nt['pos'][0] += 160
    return f
CX = float(os.environ.get('CX', '405')); CY = float(os.environ.get('CY', '240'))
os.makedirs(out, exist_ok=True)
for mode in ('orig', 'cen'):
    UI.RECENTRAGE_TEXTE = (mode == 'cen')
    for nom, mk in (('t33', fen33), ('t32', fen32), ('t29', fen29), ('t31', fen31)):
        f = mk(); rd.voisins = [f]
        win.switch_to(); gl.glClearColor(0.1, 0.4, 0.1, 1); win.clear()
        rd.dessiner([f], CX if nom != 't33' else 402.7, {'t33': 692.0, 't32': 692.0, 't29': -150.0}.get(nom, CY), S, (W, H))
        im = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
        a = np.frombuffer(im.get_data('RGBA', W * 4), np.uint8).reshape(H, W, 4)[::-1]
        Image.fromarray(a[..., :3].copy()).save('%s/%s_%s.png' % (out, nom, mode)); print('ecrit', nom, mode, flush=True)

# ---- feuilles de contact : fenetres variees (portrait 450 x 800, echelle 1), textes d'exemple dans toutes les cases texte
EX = ['Ragnar', 'Épée de fer', 'PV  44', 'Potion', 'Objets', 'Quitter', 'Guérir', 'Alena']
def fen_generique(typ):
    f = UI.Fenetre(ml, typ); k = 0
    for (i, no), p in sorted(f.params.items()):
        if 'custom' in p: continue
        pt, ib = f._ib(p)
        if ib and ib['k'] == 'text': f.param_str(i, no, EX[k % len(EX)]); k += 1
    return f
W2, H2 = 450, 800
win2 = pyglet.window.Window(W2, H2, visible=False)
rd2 = UI.Rendu(ml, fe, cache + '/ui_font.otf')
TYPES = [3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17, 19, 20, 21, 24, 28, 30, 34, 35, 36, 44, 46, 53, 54, 57, 58, 60, 62, 66]
for typ in TYPES:
    for mode in ('orig', 'cen'):
        UI.RECENTRAGE_TEXTE = (mode == 'cen')
        try:
            f = fen_generique(typ); rd2.voisins = [f]
            win2.switch_to(); gl.glClearColor(0.1, 0.4, 0.1, 1); win2.clear()
            rd2.dessiner([f], W2 / 2, H2 / 2, 1.0, (W2, H2))
            im = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
            a = np.frombuffer(im.get_data('RGBA', W2 * 4), np.uint8).reshape(H2, W2, 4)[::-1]
            Image.fromarray(a[..., :3].copy()).save('%s/g%d_%s.png' % (out, typ, mode))
        except Exception as e: print('erreur', typ, mode, repr(e), flush=True)
    print('ecrit g', typ, flush=True)
