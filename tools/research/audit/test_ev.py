import sys, os, time
sys.path.insert(0, '/home/claude/wt-audit/dq4_pc'); os.chdir('/home/claude/wt-audit/dq4_pc')
from dq4_pc.world import data as DN
APK = '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks/split_UnityDataAssetPack.apk'
d = DN.Data(APK, '/tmp/audit/cache_ev')
for n in sys.argv[1:]:
    t0 = time.time()
    try:
        r = d.game_map(n)
        print(n, 'OK', type(r), (list(r.keys())[:8] if isinstance(r, dict) else None), '%.1fs' % (time.time()-t0))
    except Exception as ex:
        import traceback; print(n, 'ERREUR', repr(ex)[:300]); traceback.print_exc(limit=3)
