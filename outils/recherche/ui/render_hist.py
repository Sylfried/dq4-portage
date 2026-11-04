"""Rendu hors moteur de la fenetre Historique (iteration rapide) : python3 render_hist.py SORTIE.png [onglet] [filtre] [fin] [largeur] [hauteur]"""
import sys, os, types
WT = os.environ.get('WT', '/home/claude/wt45-ui')
sys.path.insert(0, WT + '/dq4_pc'); sys.path.insert(0, WT + '/outils')
os.chdir(WT + '/dq4_pc')
import numpy as np
import pyglet
from pyglet import gl
from PIL import Image
out = sys.argv[1]; onglet = int(sys.argv[2]) if len(sys.argv) > 2 else 0; filtre = len(sys.argv) > 3 and sys.argv[3] == '1'; fin = int(sys.argv[4]) if len(sys.argv) > 4 else -1
W = int(sys.argv[5]) if len(sys.argv) > 5 else 1280; H = int(sys.argv[6]) if len(sys.argv) > 6 else 720
win = pyglet.window.Window(W, H, visible=True)
from dq4_pc.menus import ui_menu as UM; from dq4_pc.persistance import reglages as RG; from dq4_pc.menus import pause as PA; from dq4_pc.menus import ui_historique as UH; from dq4_pc.noyau import historique as HI
import test_historique_messages as T
CACHE = '/tmp/uicache4'
ml = UM.MiseEnPage(os.path.join(CACHE, 'ui_layout.json'), os.path.join(CACHE, 'ui_frameData.bin'))
feuilles = {0: np.array(Image.open(os.path.join(CACHE, 'ui_MenuTexture.png')).convert('RGBA')), 1: np.array(Image.open(os.path.join(CACHE, 'ui_Button.png')).convert('RGBA'))}
rendu = UM.Rendu(ml, feuilles, os.path.join(CACHE, 'ui_font.otf'))
h = T.nouveau(None); T.remplir(h)
J = types.SimpleNamespace(reg=RG.Reglages(None), historique=h, width=W, height=H, ui_rendu=rendu, souris=None, args=types.SimpleNamespace(cache=CACHE), pause_jeu=lambda o: None)
P = PA.Pause(J); P.ouvert = True; P.pile = ['historique']
v = UH.VueHistorique(P); v.entrer(onglet)
if filtre: v.basculer_filtre()
if fin >= 0: v.fin = v.sel = fin
P.mode_souris = False
win.switch_to(); gl.glClearColor(0.1, 0.25, 0.1, 1); win.clear()
v.dessiner()
pyglet.image.get_buffer_manager().get_color_buffer().save(out)
print('ok', out, 'vis', v.vis, 'elements', len(v.elements))
