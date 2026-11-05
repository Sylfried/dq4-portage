"""Capture reelle : vraie classe Sound + pilote OpenAL de pyglet + OpenAL Soft en mode « wave » (fichier WAV, temps reel) ; rejoue la chronologie de l'auberge (images moteur 347 / 378 / 468 / 471 de la trace du vrai moteur).
usage : al_capture.py [warm|cold] ; ecrit al_<mode>.wav et al_<mode>.json"""
import sys, os, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
mode = sys.argv[1] if len(sys.argv) > 1 else 'warm'
wav = os.path.join(HERE, 'al_%s.wav' % mode)
conf = os.path.join(HERE, 'alsoft.ini')
open(conf, 'w').write('[general]\ndrivers=wave\nfrequency=44100\nchannels=stereo\n[wave]\nfile=%s\n' % wav)
os.environ['ALSOFT_CONF'] = conf; os.environ['ALSOFT_DRIVERS'] = 'wave'
os.environ['PYGLET_HEADLESS'] = '1'
sys.path.insert(0, '/home/claude/dq4-portage')
import pyglet
pyglet.options['audio'] = ('openal',); pyglet.options['shadow_window'] = False
from dq4_pc import sound as S
from dq4_pc.battle import battle_speed as VC
APK = os.environ.get('DQ_APK', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks') + '/split_UnityDataAssetPack.apk'
cache = os.path.join(HERE, 'cache_al_' + mode); os.makedirs(cache, exist_ok=True)
for f in os.listdir(cache): os.remove(os.path.join(cache, f))
snd = S.Sound(APK, cache, log=print)
assert snd.ok and snd.ogg
drv = pyglet.media.get_audio_driver(); D = time.perf_counter()          # le peripherique est ouvert : origine du temps du fichier WAV
print('pilote', type(drv).__module__)
LOG = []
def note(t, txt):
    LOG.append((t - D, txt)); print('%8.3f  %s' % (t - D, txt), flush=True)
o_launch, o_stop = snd._launch_bgm, snd.stop_bgm
def launch(ident, r, restart=False):
    n0 = snd.bgm; o_launch(ident, r, restart)
    if snd.bgm is not n0 and snd.bgm is not None: note(time.perf_counter(), 'play BGM%02d' % ident)
def stop():
    if snd.bgm is not None: note(time.perf_counter(), 'stop BGM%s' % snd.bgm_id)
    o_stop()
snd._launch_bgm, snd.stop_bgm = launch, stop
if mode == 'warm':
    snd.preload_music(); snd.events([(37, 14)], engine_frame=0)
    t = time.perf_counter()
    while time.perf_counter() - t < 25 and (snd.background or snd.jobs): snd.tick(); time.sleep(1 / 30)
    snd.stop_bgm()
else:
    snd.preload_music(); snd.background.clear()
time.sleep(1.0); LOG.clear()
# chronologie du vrai moteur (images apres le pas) : musique de la ville tourne ; arret 347 ; jingle 378 ; arret 468 ; musique de la ville 471
snd.events([(37, 14)], engine_frame=256)
t_step = time.perf_counter(); f0 = 256
for _ in range(60): snd.tick(); time.sleep(1 / 30)
orders = {347: [(37, 0x4000)], 378: [(37, 41)], 468: [(37, 0x4000)], 471: [(37, 14)]}
tn = time.perf_counter()
for f in range(f0 + 1, 520):
    ev = orders.get(f)
    if ev:
        note(time.perf_counter(), 'ordre du moteur image %d : %s' % (f, ev))
        snd.events(VC.sounds_to_play([(a, b) for a, b in ev], None), engine_frame=f)
    snd.tick()
    tn += 1 / 30; dl = tn - time.perf_counter()
    if dl > 0: time.sleep(dl)
note(time.perf_counter(), 'fin')
snd.stop_bgm(); time.sleep(0.5)
json.dump(dict(log=LOG, D=D), open(os.path.join(HERE, 'al_%s.json' % mode), 'w'))
snd.shutdown()
