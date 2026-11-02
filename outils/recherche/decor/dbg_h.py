import os, sys, shutil
sys.path.insert(0, '/home/claude/wt45-decor/dq4_pc'); os.chdir('/home/claude/wt45-decor/dq4_pc')
import moteur as MO
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'; SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'
ecr = '/tmp/sv_dc_h2'; shutil.rmtree(ecr, ignore_errors=True); os.makedirs(ecr)
m = MO.Moteur(APK, SAVES, ecr); m.charger_sauvegarde(1)
for i in range(30): m.step(0, 0)
e = m.etat; print('avant', e.carte, e.partie, len(e.sprites), e.msg_visible if hasattr(e,'msg_visible') else None, m.msg_visible)
m.demarrer_ville('maout')
for i in range(400):
    m.step(0, 0)
    if i % 50 == 0:
        e = m.etat; print(i, e.carte, hex(e.partie), 'sprites', list(e.sprites)[:6], 'msg', m.msg_visible, 'menu', m.menu_actif(), 'cam', e.cam_pos, 'fondu', e.fondu_en_cours(), 'sp0', (e.sprites.get(0) or {}).get('pos'))
