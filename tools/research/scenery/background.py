import os, sys, shutil
sys.path.insert(0, '/home/claude/wt45-decor/dq4_pc'); os.chdir('/home/claude/wt45-decor/dq4_pc')
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'; SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'
wdir = '/tmp/sv_dc_h3'; shutil.rmtree(wdir, ignore_errors=True); os.makedirs(wdir)
m = ENGINE.Engine(APK, SAVES, wdir); m.load_save(1)
for i in range(30): m.step(0, 0)
m.start_town('maout')
for i in range(120): m.step(0, 0)
e = m.state; print('background', e.background, [round(255 * x) for x in e.background], 'tint', e.tint)
