"""Rend (hors ecran) les fenetres du moteur dans l'etat ou la sauvegarde est arrivee a la condition voulue, avec la mise en page /tmp/r3_layout et le rendu de la visionneuse.
Usage : xvfb-run -a python3 rend_combat.py <slot> <sortie.png> [attente_texte_action=1] ; ne modifie rien dans le depot."""
import sys, os
sys.path.insert(0, '/tmp/specs'); sys.path.insert(0, os.environ.get('DQ4_SRC', '/home/claude/wt-audit/dq4_pc'))
import numpy as np, pyglet
from pyglet import gl
from PIL import Image
from harnais import *
import ui_menu as UI
slot = int(sys.argv[1]); sortie = sys.argv[2]
mo = demarrer(slot)
for i in range(100): mo.step(0, 0x10 if i % 10 == 0 else 0)
if mo.etat.partie != MO.PARTIE_CHAMP:
    mo.demarrer_champ()
    for i in range(120): mo.step(0, 0)
c = mo.core
sing = c.call(mo.E('_ZN7Encount12getSingletonEv'), label='enc'); c.call(mo.E('_ZN7Encount12forceEncountEv'), sing, label='force')
for i in range(600):
    mo.step([0x4, 0x8][(i // 20) % 2], 0)
    if mo.etat.partie == MO.PARTIE_COMBAT: break
trouve = False
for i in range(3000):
    p = mo.menu_actif(); a = 0
    if p is not None and i % 15 == 0: mo.envoyer_menu(p, 1, -1, 0x10)
    elif p is not None and i % 15 == 1: mo.envoyer_menu(p, 1, -1, 0)
    elif p is None and i % 10 == 0: a = 0x10
    mo.step(0, a)
    f = mo.ui.f.get(12)
    if f and f['cases'].get((0, 4)) and f['vis']: trouve = True; break
print('texte d action trouve', trouve, 'image', mo.images)
W, H = 450, 800
win = pyglet.window.Window(W, H, visible=False)
cache = '/tmp/r3_res'
ml = UI.MiseEnPage('/tmp/r3_layout/ui_layout.json', cache + '/ui_frameData.bin')
fe = {0: np.array(Image.open(cache + '/ui_MenuTexture.png').convert('RGBA')), 1: np.array(Image.open(cache + '/ui_Button.png').convert('RGBA'))}
rd = UI.Rendu(ml, fe, cache + '/ui_font.otf'); g = UI.Gestionnaire(ml); g.rejouer(mo.ui)
liste = sorted((f['ordre'], p) for p, f in mo.ui.f.items() if f['vis'] and p in g.f)
print('ports visibles', [(p, mo.ui.f[p]['type']) for _, p in liste])
fens = [g.f[p] for _, p in liste]; rd.voisins = fens
win.switch_to(); gl.glClearColor(0.18, 0.25, 0.4, 1); win.clear()
rd.dessiner(fens, W / 2, H / 2, 1.0, (W, H))
pyglet.image.get_buffer_manager().get_color_buffer().save(sortie)
print('ecrit', sortie)
