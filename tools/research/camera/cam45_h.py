"""Harnais moteur seul (wt45-camera) : hauteur du heros / cible / position de la camera, pas par pas."""
import os, sys, shutil
sys.path.insert(0, '/home/claude/wt45-camera/dq4_pc')
os.chdir('/home/claude/wt45-camera/dq4_pc')
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'

def new(name_str='cam45'):
    wdir = '/tmp/sv_' + name_str; shutil.rmtree(wdir, ignore_errors=True); os.makedirs(wdir)
    m = ENGINE.Engine(APK, SAVES, wdir); assert m.load_save(1)
    for _ in range(10): m.step(0, 0)
    return m

def reading(m):
    e = m.state; sp = e.sprites.get(0)
    hp = None if not sp or sp['pos'] is None else tuple(float(v) for v in sp['pos'])
    return dict(h=hp, cc=None if e.cam_target is None else tuple(float(v) for v in e.cam_target), cp=None if e.cam_pos is None else tuple(float(v) for v in e.cam_pos))
