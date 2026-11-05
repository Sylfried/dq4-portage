import os, sys, shutil
sys.path.insert(0, '/home/claude/wt45-decor/dq4_pc'); os.chdir('/home/claude/wt45-decor/dq4_pc')
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'; SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'
wdir = '/tmp/sv_dc_h2'; shutil.rmtree(wdir, ignore_errors=True); os.makedirs(wdir)
m = ENGINE.Engine(APK, SAVES, wdir); m.load_save(1)
for i in range(30): m.step(0, 0)
e = m.state; print('before', e.game_map, e.part, len(e.sprites), e.msg_visible if hasattr(e,'msg_visible') else None, m.msg_visible)
m.start_town('maout')
for i in range(400):
    m.step(0, 0)
    if i % 50 == 0:
        e = m.state; print(i, e.game_map, hex(e.part), 'sprites', list(e.sprites)[:6], 'msg', m.msg_visible, 'menu', m.active_menu(), 'cam', e.cam_pos, 'fade', e.fade_in_progress(), 'sp0', (e.sprites.get(0) or {}).get('pos'))
