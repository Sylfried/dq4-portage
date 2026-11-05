import json, zipfile, sys, numpy as np
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc import sound as S
z = zipfile.ZipFile('/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks/split_UnityDataAssetPack.apk')
data = json.load(open('menu_sound_real.json'))
def info(b):
    d = z.read('assets/sound/BGM%02d.akb' % b); r = S.decode_akb(d); fr = r['frequence']
    def rms(a, b_):
        seg = r['pcm'][int(a * fr):int(b_ * fr)].astype(np.float64) / 32768; return float(np.sqrt((seg ** 2).mean())) if len(seg) else 0.0
    return len(r['pcm']) / fr, rms
rows = []
print('type | BGM | delai | fenetre moteur (lecture -> arret) | fichier | ecart | RMS des 100 ms avant la coupure | reprise')
for e in data:
    evs = e['plays'] + e['stops'] + e['others']
    # ordre d'appel reel : plays, stops sont rangés par categorie ; on retire le 1er arret (celui de setPlaySound, horodatage perime)
    stops = e['stops'][1:]
    fp, _, bgm = [p for p in e['plays'] if p[1] == '7playBgm'][0]
    fs = [s for s in stops if s[0] > fp][0][0]
    resume = [p for p in e['plays'] if p[1] == '4play' and p[0] > fs]
    dur, rms = info(bgm); win = (fs - fp) / 30.0
    d = dur - win
    rows.append((e['type'], bgm, fp - 1, fs - fp, win, dur))
    if d > 0.02: txt = 'coupe %.3f s (%.0f %%) ; RMS %.4f (milieu de morceau)' % (d, 100 * d / dur, rms(win - 0.1, win))
    else: txt = 'fichier fini avant l\'arret (%.3f s de silence)' % (-d)
    print('%2d | BGM%02d | %2d img | %3d img = %6.3f s | %6.3f s | %s | %s' % (e['type'], bgm, fp - 1, fs - fp, win, dur, txt, ('BGM %d' % resume[0][2]) if resume else '-'))
