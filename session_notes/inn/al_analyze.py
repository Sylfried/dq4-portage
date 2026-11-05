import sys, os, json, zipfile
import numpy as np, soundfile as sf
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc import sound as S
HERE = os.path.dirname(os.path.abspath(__file__))
mode = sys.argv[1] if len(sys.argv) > 1 else 'warm'
x, fs = sf.read(os.path.join(HERE, 'al_%s.wav' % mode), dtype='float32', always_2d=True)
info = json.load(open(os.path.join(HERE, 'al_%s.json' % mode)))
print('wav: %d frames, %.3f s, fs=%d, ch=%d ; D (perf_counter) = %.3f' % (len(x), len(x) / fs, fs, x.shape[1], info['D']))
log = {}
for t, txt in info['log']: log.setdefault(txt, []).append(t)
z = zipfile.ZipFile(os.path.join(os.environ.get('DQ_APK', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks'), 'split_UnityDataAssetPack.apk'))
r = S.decode_akb(z.read('assets/sound/BGM41.akb')); ref = r['pcm'].astype(np.float32) / 32768.0
env = np.abs(x).max(axis=1)
def t_of(n): return n / fs
# jingle onset by cross-correlation of the first 0.5 s of BGM41 (scaled by gain) with the wav, searched in a window around the play call
t_play = [t for t in log if t.startswith('play BGM41')][0]; tp = log[t_play][0]
t_stop41 = [t for t in log if t.startswith('stop BGM41')]; ts = log[t_stop41[0]][0]
print('appel play BGM41 a t=%.3f, appel stop a t=%.3f (%.3f s apres)' % (tp, ts, ts - tp))
a = int((tp - 0.3) * fs); b = int((tp + 1.2) * fs)
seg = x[a:b, 0]
tmpl = ref[:int(0.5 * fs), 0]
# normalised correlation via FFT
n = len(seg) + len(tmpl)
cc = np.fft.irfft(np.fft.rfft(seg, n) * np.conj(np.fft.rfft(tmpl, n)), n)[:len(seg) - len(tmpl)]
k = int(np.argmax(np.abs(cc))); onset = (a + k) / fs
gain = float(np.dot(seg[k:k+len(tmpl)], tmpl) / np.dot(tmpl, tmpl))
print('debut du jingle trouve dans le WAV : t=%.3f s => latence appel play -> premier echantillon %.0f ms ; gain mesure %.3f (attendu 0.490)' % (onset, 1000 * (onset - tp), gain))
# end of jingle: last sample above threshold in [ts-0.3, ts+1.0], before the town music (which starts at ts+0.067 : play BGM14)
t_next = [t for t in log if t.startswith('play BGM14')][-1]; tn = log[t_next][0]
print('appel play BGM14 (musique de la ville) a t=%.3f' % tn)
# position in the file at the cut: cross-correlate the end of the heard jingle: find where the heard signal stops matching ref -> use envelope of residual
heard = x[int(onset * fs): int(onset * fs) + len(ref), 0]
m = min(len(heard), len(ref))
resid = heard[:m] - gain * ref[:m, 0]
w = int(0.01 * fs)
rms_r = np.array([np.sqrt((resid[i:i+w] ** 2).mean()) for i in range(0, m - w, w)])
rms_h = np.array([np.sqrt((heard[i:i+w] ** 2).mean()) for i in range(0, m - w, w)])
rms_ref = np.array([np.sqrt(((gain * ref[i:i+w, 0]) ** 2).mean()) for i in range(0, m - w, w)])
# first 10 ms block (after 2 s) where heard ~ 0 while ref is clearly nonzero
cut = None
for i in range(int(2.0 / 0.01), len(rms_h)):
    if rms_h[i] < 0.1 * rms_ref[i] and rms_ref[i] > 0.003: cut = i; break
print('le jingle entendu est coupe a %.2f s de sa position dans le fichier (le fichier dure %.3f s)' % (cut * 0.01 if cut else -1, len(ref) / fs))
print('=> duree entendue : %.0f ms ; instant du silence (horloge du pilote) t=%.3f ; stop demande a t=%.3f (silence %.0f ms apres)' % (1000 * cut * 0.01, onset + cut * 0.01, ts, 1000 * (onset + cut * 0.01 - ts)))
for i in range(int(2.8 / 0.01), min(len(rms_h), int(3.4 / 0.01)), 2): print('   %.2f s  entendu %.4f  attendu %.4f' % (i * 0.01, rms_h[i], rms_ref[i]))
