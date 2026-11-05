import sys, os, time, traceback
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.world.data import Data
d = Data('/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks/split_UnityDataAssetPack.apk', sys.argv[1])
for no in [int(x) for x in sys.argv[2:]]:
    t0 = time.time()
    try:
        r = d.fbx_model(no)
        print(no, 'OK', {k: (len(v) if hasattr(v, '__len__') else v) for k, v in r.items() if k in ('noms', 'v', 'tri', 'clips')}, 'clips', list(r['clips']), '%.1fs' % (time.time() - t0), flush=True)
    except Exception as ex:
        print(no, 'ERREUR', type(ex).__name__, ex, '%.1fs' % (time.time() - t0), flush=True)
