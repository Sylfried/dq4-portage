"""Son reel (vrai pyglet, pilote audio silencieux, sans fenetre) : prechargement des musiques et protection des jingles sur l'APK reel."""
import os, sys, time
os.environ['PYGLET_AUDIO'] = 'silent'
sys.path.insert(0, '/home/claude/wt45-son/dq4_pc')
import pyglet; pyglet.options['shadow_window'] = False
from dq4_pc import son as S
D = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks/split_UnityDataAssetPack.apk'
s = S.Son(D, '/tmp/son45_cache', log=print)
print('ok', s.ok, 'ogg', s.ogg)
if not s.ok: sys.exit(1)
s.precharger_musiques()
s.evenements([(37, 14)], image_moteur=0)
t0 = time.time()
while time.time() - t0 < 12:
    s.tick(); time.sleep(1 / 30)
print('musiques en memoire', sum(1 for k in s.dec if k.startswith('BGM')), 'attente', len(s.fond), 'travaux', len(s.jobs))
# combat accelere : jingle BGM 47 (sans boucle, 3,1 s) puis ordre d'arret de l'image 220 (4 s apres, a vitesse normale) recu tout de suite
s.evenements([(37, 47)], image_moteur=100); s.tick(); print('jingle', s.bgm_id, s.bgm_cat, 'joue', s.bgm is not None)
t1 = time.time(); s.evenements([(37, S.BGM_ARRET)], image_moteur=220); s.tick()
print("ordre d'arret retenu", len(s.attente_bgm) == 1, 'jingle toujours la', s.bgm is not None)
while s.attente_bgm and time.time() - t1 < 10:
    s.tick(); time.sleep(1 / 30)
print('ordre libere apres %.2f s (fin du jingle : 3,1 s apres son depart)' % (time.time() - t1), 'bgm', s.bgm)
s.fermer()
