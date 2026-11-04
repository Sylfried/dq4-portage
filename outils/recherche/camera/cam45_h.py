"""Harnais moteur seul (wt45-camera) : hauteur du heros / cible / position de la camera, pas par pas."""
import os, sys, shutil
sys.path.insert(0, '/home/claude/wt45-camera/dq4_pc')
os.chdir('/home/claude/wt45-camera/dq4_pc')
from dq4_pc.noyau import moteur as MO
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'

def nouveau(nom='cam45'):
    ecr = '/tmp/sv_' + nom; shutil.rmtree(ecr, ignore_errors=True); os.makedirs(ecr)
    m = MO.Moteur(APK, SAVES, ecr); assert m.charger_sauvegarde(1)
    for _ in range(10): m.step(0, 0)
    return m

def releve(m):
    e = m.etat; sp = e.sprites.get(0)
    hp = None if not sp or sp['pos'] is None else tuple(float(v) for v in sp['pos'])
    return dict(h=hp, cc=None if e.cam_cible is None else tuple(float(v) for v in e.cam_cible), cp=None if e.cam_pos is None else tuple(float(v) for v in e.cam_pos))
