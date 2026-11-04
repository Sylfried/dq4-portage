"""Liste deroulante « Interface a modifier » hors moteur : python3 render_liste.py SORTIE.png [courant] [haut]"""
import sys, os, types
WT = os.environ.get('WT', '/home/claude/wt45-ui')
sys.path.insert(0, WT + '/dq4_pc'); os.chdir(WT + '/dq4_pc')
import numpy as np, pyglet
from pyglet import gl
from PIL import Image
out = sys.argv[1]; courant = sys.argv[2] if len(sys.argv) > 2 else 'boutons'; haut = sys.argv[3] if len(sys.argv) > 3 else None
W, H = 1280, 720
win = pyglet.window.Window(W, H, visible=True)
from dq4_pc.menus import ui_menu as UM; from dq4_pc.persistance import reglages as RG; from dq4_pc.menus import pause as PA
CACHE = '/tmp/uicache4'
ml = UM.MiseEnPage(os.path.join(CACHE, 'ui_layout.json'), os.path.join(CACHE, 'ui_frameData.bin'))
feuilles = {0: np.array(Image.open(os.path.join(CACHE, 'ui_MenuTexture.png')).convert('RGBA')), 1: np.array(Image.open(os.path.join(CACHE, 'ui_Button.png')).convert('RGBA'))}
rendu = UM.Rendu(ml, feuilles, os.path.join(CACHE, 'ui_font.otf'))
noms = {n: [1] for n in PA.NOMS_FENETRES if n not in ('boutons', 'msg', 'bouton_vitesse')}
J = types.SimpleNamespace(reg=RG.Reglages(None), width=W, height=H, ui_rendu=rendu, souris=None, args=types.SimpleNamespace(cache=CACHE), pause_jeu=lambda o: None, noms_fenetres=lambda: noms,
                          son=types.SimpleNamespace(actif=True, ecoute=False), nouvel_echantillon=lambda: None,
                          _etiq=lambda t, taille, couleur=(255, 255, 255, 255), polices=(): pyglet.text.Label(t, font_name=tuple(polices) + ('DejaVu Sans', 'Arial'), font_size=taille, color=couleur, anchor_x='left', anchor_y='baseline'))
P = PA.Pause(J); P.ouvert = True; P.pile = ['interface']; P.cible = courant
en = P._e_interface()[0]; vals = en['vals']
P.deroule = [0, vals.index(courant)]; P.liste_top = (vals.index(haut) if haut and not haut.isdigit() else (int(haut) if haut else None)); P.liste_cur_vu = None; P.glisse_liste = None; P.mode_souris = False
k = max(0.75, H / 900.0)
win.switch_to(); gl.glClearColor(0.12, 0.2, 0.3, 1); win.clear()
P._cadre(900 - 380 * k, 330, 380 * k, 330, k)
P._dessiner_liste(en, (560, 520), 900, k, 18 * k)
pyglet.image.get_buffer_manager().get_color_buffer().save(out)
print('ok', out, len(vals))
