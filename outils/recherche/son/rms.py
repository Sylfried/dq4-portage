import sys, zipfile, numpy as np
sys.path.insert(0, '/home/claude/wt45-son/dq4_pc')
from dq4_pc import son
z = zipfile.ZipFile('/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks/split_UnityDataAssetPack.apk')
for nom in sys.argv[1:]:
    r = son.decoder_akb(z.read('assets/sound/%s.akb' % nom))
    pcm = r['pcm'].astype(np.float64) / 32768; fr = r['frequence']
    n = len(pcm) // fr
    rms = [float(np.sqrt((pcm[i*fr:(i+1)*fr] ** 2).mean())) for i in range(min(n, 20))]
    print(nom, 'dur %.1f' % (len(pcm)/fr), 'boucle', r['boucle'], 'debut/fin', r['debut']/fr, r['fin']/fr, 'rms/s:', ' '.join('%.3f' % x for x in rms))
