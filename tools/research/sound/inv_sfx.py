import sys, zipfile
sys.path.insert(0, '/home/claude/wt45-son/dq4_pc')
from dq4_pc import sound
z = zipfile.ZipFile('/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks/split_UnityDataAssetPack.apk')
for i in [int(x) for x in sys.argv[1:]]:
    n = 'assets/sound/SE%04d.akb' % i
    if n not in z.namelist(): print('SE%04d MISSING' % i); continue
    r = sound.decode_akb(z.read(n))
    print('SE%04d %6.2fs loop=%s vol=%.2f samples=%d channels=%d' % (i, len(r['pcm'])/r['frequence'], r['boucle'], r['volume'], r['frequence'], r['pcm'].shape[1]))
