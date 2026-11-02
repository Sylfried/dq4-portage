import sys, zipfile
sys.path.insert(0, '/home/claude/wt45-son/dq4_pc')
import son
z = zipfile.ZipFile('/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks/split_UnityDataAssetPack.apk')
for i in [int(x) for x in sys.argv[1:]]:
    n = 'assets/sound/SE%04d.akb' % i
    if n not in z.namelist(): print('SE%04d ABSENT' % i); continue
    r = son.decoder_akb(z.read(n))
    print('SE%04d %6.2fs boucle=%s vol=%.2f ech=%d canaux=%d' % (i, len(r['pcm'])/r['frequence'], r['boucle'], r['volume'], r['frequence'], r['pcm'].shape[1]))
