import sys, os, pickle, types, math
sys.path.insert(0, '/home/claude/wt45-camera/outils'); sys.path.insert(0, '/home/claude/wt45-camera/dq4_pc')
import numpy as np
import pyglet
pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import test_town_camera as T
F = T.F
name_str = sys.argv[1]; option = (sys.argv[2] != '0') if len(sys.argv) > 2 else True
tr = pickle.load(open('/tmp/cam45/tr_%s.pkl' % name_str, 'rb'))
j = T.fake_game(option=option)
T.HORLOGE[0] = 0.0
F.time = types.SimpleNamespace(perf_counter=lambda: T.HORLOGE[0], time=lambda: T.HORLOGE[0], sleep=lambda *a: None)
j.fixed_test = True
res = []
prev = None
for n, pad, h, cc, cp in tr:
    cur = (np.array(h), np.array(cc), np.array(cp))
    for a in (0.5, 1.0):                         # 2 images par pas du moteur (60 Hz pour 30 Hz)
        if prev is None or max(abs(cur[0] - prev[0])) > 1.5 or max(abs(cur[1] - prev[1])) > 1.5: hh, c1, c2 = cur
        else: hh, c1, c2 = [p + (q - p) * a for p, q in zip(prev, cur)]
        e = types.SimpleNamespace(cam_pos=c2, cam_target=c1, cam_fov=None, cam_near=None, cam_far=None, cam_yoff=None, cam_down=None, cam_free=False, cam_rot=None, sprites={0: {'pos': tuple(hh)}})
        M, _ = F.Game._town_camera(j, e, 16 / 9)
        x, y = T.ndc(M, hh); res.append((n, a, pad, y, hh[1]))
    prev = cur
ys = np.array([r[3] for r in res])
print(name_str, 'option centree', option, 'images', len(res), 'NDC y du heros : min %.5f max %.5f' % (ys.min(), ys.max()))
# ecart d'une image a l'autre et pires frames
d = np.abs(np.diff(ys)); idx = np.argsort(-d)[:8]
for i in sorted(idx): print('  pas', res[i+1][0], 'a', res[i+1][1], 'pad', res[i+1][2], 'Y heros %.3f' % res[i+1][4], 'NDC y %.5f -> %.5f' % (res[i][3], res[i+1][3]))
