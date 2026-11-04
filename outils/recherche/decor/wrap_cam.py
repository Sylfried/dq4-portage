import sys, os
sys.path.insert(0, '/home/claude/wt45-decor/dq4_pc')
from dq4_pc.fenetre import jeu as F
orig = F.Jeu._dessiner_scene
n = [0]
def patched(self):
    e = self.moteur.etat
    n[0] += 1
    if n[0] in (30, 60, 100): print('CAMLOG', n[0], e.carte, e.cam_pos, e.cam_cible, e.cam_fov, e.cam_bas, flush=True)
    return orig(self)
F.Jeu._dessiner_scene = patched
F.main()
