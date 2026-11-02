import os, sys, shutil
sys.path.insert(0, '/home/claude/wt45-decor/dq4_pc'); os.chdir('/home/claude/wt45-decor/dq4_pc')
import moteur as MO
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks'; SAVES = '/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes'
ecr = '/tmp/sv_dc_h3'; shutil.rmtree(ecr, ignore_errors=True); os.makedirs(ecr)
m = MO.Moteur(APK, SAVES, ecr); m.charger_sauvegarde(1)
for i in range(30): m.step(0, 0)
m.demarrer_ville('maout')
for i in range(120): m.step(0, 0)
e = m.etat; print('fond', e.fond, [round(255 * x) for x in e.fond], 'teinte', e.teinte)
