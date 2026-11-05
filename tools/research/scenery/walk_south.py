"""Harnais sans fenetre (pas de GL, pas de xvfb) : ville de depart (maout) puis marche vers le bas (DOWN) ; journal : carte, position du heros, camera (pos / cible) du moteur."""
import os, sys, time, shutil
sys.path.insert(0, '/home/claude/wt45-decor/dq4_pc'); os.chdir('/home/claude/wt45-decor/dq4_pc')
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'; SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'
wdir = '/tmp/sv_dc_h'; shutil.rmtree(wdir, ignore_errors=True); os.makedirs(wdir)
m = ENGINE.Engine(APK, SAVES, wdir); print('slot 1', m.load_save(1), flush=True)
for i in range(30): m.step(0, 0)
m.start_town(sys.argv[1])
N = int(sys.argv[2]); t0 = time.time()
for i in range(N):
    if m.msg_visible: m.step(0, ENGINE.A if i % 6 == 0 else 0)
    else:
        sp = m.state.sprites.get(0); hp = sp.get('pos') if sp else None
        if hp is not None and i % 3000 < 1500 and abs(hp[0] - float(sys.argv[3])) > 0.12 and float(hp[2]) > float(sys.argv[4]):
            k = ENGINE.LEFT if hp[0] > float(sys.argv[3]) else ENGINE.RIGHT; m.step(k, k)
        else: m.step(ENGINE.DOWN, ENGINE.DOWN)
    e = m.state
    if i % 100 == 0:
        sp = e.sprites.get(0); hp = sp.get('pos') if sp else None
        print(i, e.game_map, 'heros', None if hp is None else tuple(round(float(x), 2) for x in hp), 'cam', None if e.cam_pos is None else tuple(round(x, 2) for x in e.cam_pos), 'cible', None if e.cam_target is None else tuple(round(x, 2) for x in e.cam_target), '%.0fs' % (time.time() - t0), flush=True)
