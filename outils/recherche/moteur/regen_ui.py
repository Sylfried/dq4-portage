"""Regenere la mise en page des fenetres (comme outils/ui_il2cpp/generer_ui.py) SANS toucher au depot : sortie dans /tmp/r3_layout/ui_layout.json.
Entrees : /home/claude/il2 (libil2cpp.so, script.json, dump.cs), /tmp/r3_apk (global-metadata.dat), /tmp/r3_res/ui_frameData.bin (extraire_res.py)."""
import concurrent.futures as cf, json, os, subprocess, sys, tempfile, time
ICI = '/home/claude/dq4-portage/outils/ui_il2cpp'
SORTIE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/r3_layout/ui_layout.json'
env = dict(os.environ, PYTHONUTF8='1', DQ_IL2='/home/claude/il2', DQ_META='/tmp/r3_apk/assets/bin/Data/Managed/Metadata/global-metadata.dat',
           DQ_FRAME='/tmp/r3_res/ui_frameData.bin', DQ_UI_H='800', PYTHONIOENCODING='utf-8')
def lancer(args):
    p = subprocess.run(args, cwd=ICI, env=env, capture_output=True); return p.returncode, (p.stdout + p.stderr).decode('utf-8', 'replace')
tmp = tempfile.mkdtemp(prefix='r3_ui_'); t0 = time.time()
ent = os.path.join(tmp, 'entete.json'); rc, s = lancer([sys.executable, os.path.join(ICI, 'entete.py'), ent]); print('entete', rc, time.time() - t0)
if rc: print(s[-3000:]); sys.exit(1)
hdr = json.load(open(ent)); n = hdr['nTypes']
def un(k):
    out = os.path.join(tmp, 't%d.json' % k); rc, s = lancer([sys.executable, os.path.join(ICI, 'layout.py'), out, str(k)])
    try: return k, json.load(open(out, encoding='utf-8')).get(str(k)), None
    except Exception: return k, None, 'code %s : %s' % (rc, s[-800:])
types = {}
with cf.ThreadPoolExecutor(max_workers=4) as ex:
    for k, res, err in ex.map(un, range(n)):
        if res is not None: types[str(k)] = res
        elif err: print('type', k, err)
mj = os.path.join(tmp, 'message.json'); rc, s = lancer([sys.executable, os.path.join(ICI, 'message.py'), mj])
msg = json.load(open(mj, encoding='utf-8')) if os.path.exists(mj) else None
json.dump(dict(header=hdr, types=types, message=msg), open(SORTIE, 'w', encoding='utf-8'))
print('OK', SORTIE, len(types), 'types', time.time() - t0)
print({k: v.get('err') for k, v in types.items() if v.get('err')})
