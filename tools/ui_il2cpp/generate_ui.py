"""Genere data/cache/ui_layout.json : la mise en page EXACTE des fenetres de menu du jeu.

Principe : les fonctions MenuPortItemTable.Make_* du jeu (libil2cpp.so, ARM64) sont executees sous Unicorn avec des
« faux » appels Unity ; on relit les noeuds, maillages, textes et tables de liaison qu'elles construisent.
Rien n'est copie ni redistribue : le fichier produit reste dans cache/ (ignore par git).

Entrees : data/cache/il2cpp/ (dump.cs, script.json, entrees/libil2cpp.so, entrees/global-metadata.dat : tools/dump_il2cpp.bat)
          data/cache/ui_frameData.bin (extrait des APK automatiquement)
Usage   : python generate_ui.py [apk_folder]"""
import concurrent.futures as cf, json, os, platform, subprocess, sys, tempfile, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
from dq4_pc import paths as CH
CACHE = CH.FOLDERS.cache
IL2 = os.path.join(CACHE, 'il2cpp')
OUTPUT = os.path.join(CACHE, 'ui_layout.json')
APKS = sys.argv[1] if len(sys.argv) > 1 else CH.FOLDERS.apk
LOG = os.path.join(CACHE, 'ui_generation.log')
_j = None


def log(*a):
    """Affiche et ecrit dans cache/ui_generation.log (UTF-8) : permet de diagnostiquer sans console."""
    t = ' '.join(str(x) for x in a)
    try: print(t, flush=True)
    except Exception: print(t.encode('ascii', 'replace').decode(), flush=True)
    if _j:
        _j.write(t + '\n'); _j.flush()


def launch(args, env):
    """Lance un sous-processus Python ; sortie lue en UTF-8 tolerant (la console Windows n'est pas en UTF-8)."""
    p = subprocess.run(args, cwd=HERE, env=env, capture_output=True)
    return p.returncode, (p.stdout + p.stderr).decode('utf-8', 'replace')


def main():
    global _j
    os.makedirs(CACHE, exist_ok=True)
    _j = open(LOG, 'w', encoding='utf-8')
    try: import unicorn; uv = getattr(unicorn, '__version__', '?')
    except Exception as e: uv = 'missing (%r)' % (e,)
    log('Python %s, %s, unicorn %s, executable %s' % (sys.version.split()[0], platform.platform(), uv, sys.executable))
    log('Root: %s | cache: %s | apk: %s' % (ROOT, CACHE, APKS))
    for f in ('dump.cs', 'script.json', os.path.join('entrees', 'libil2cpp.so'), os.path.join('entrees', 'global-metadata.dat')):
        if not os.path.exists(os.path.join(IL2, f)):
            raise SystemExit('Missing %s: run tools\\dump_il2cpp.bat first' % os.path.join(IL2, f))
    for m in ('unicorn', 'capstone'):            # capstone : desassemblage du code ARM64 (obligatoire pour l'analyse des fonctions)
        try: __import__(m)
        except ImportError:
            log('Python module missing: %s -> installing (one time only)...' % m)
            r, out = launch([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--quiet', m], os.environ)
            log(out[-800:])
            try: __import__(m)
            except ImportError: raise SystemExit('Python module missing: %s (pip install %s in .venv)' % (m, m))
    frame = os.path.join(CACHE, 'ui_frameData.bin')
    if not os.path.exists(frame):
        from dq4_pc.menus import ui_menu
        if not ui_menu.prepare_resources(APKS, CACHE) or not os.path.exists(frame):
            raise SystemExit('Cannot extract frameData from the APK files (%s)' % APKS)
    env = dict(os.environ, PYTHONUTF8='1', DQ_IL2=IL2, DQ_META=os.path.join(IL2, 'entrees', 'global-metadata.dat'), DQ_FRAME=frame, DQ_UI_H='800', PYTHONIOENCODING='utf-8')
    tmp = tempfile.mkdtemp(prefix='dq4_ui_')
    t0 = time.time()
    ent = os.path.join(tmp, 'entete.json')
    rc, output = launch([sys.executable, os.path.join(HERE, 'header.py'), ent], env)
    log('header: code %s, %.0f s' % (rc, time.time() - t0))
    if rc or not os.path.exists(ent):
        log(output[-6000:])
        raise SystemExit('Failed to read the header (details: %s)' % LOG)
    hdr = json.load(open(ent)); n = hdr['nTypes']
    log('Laying out the %d window types (a few minutes, one time only)...' % n)

    def one(k):
        out = os.path.join(tmp, 't%d.json' % k)
        rc, output = launch([sys.executable, os.path.join(HERE, 'layout.py'), out, str(k)], env)
        try: return k, json.load(open(out, encoding='utf-8')).get(str(k)), None
        except Exception: return k, None, 'code %s : %s' % (rc, output[-1500:])
    types = {}; done_count = 0; failures = {}
    with cf.ThreadPoolExecutor(max_workers=max(1, min(4, (os.cpu_count() or 2)))) as ex:
        for k, res, err in ex.map(one, range(n)):
            done_count += 1
            if res is not None: types[str(k)] = res
            elif err: failures[k] = err
            if done_count % 10 == 0 or done_count == n: log('  %d / %d' % (done_count, n))
    for k, e in failures.items(): log('Type %d: subprocess failed: %s' % (k, e))
    if not types: raise SystemExit('No type could be read (details: %s)' % LOG)
    bad = {k: v.get('err') for k, v in types.items() if v.get('err')}
    msg = None                                                   # fenetre de message (MenuMessage) : cadre, canevas du texte, curseur
    mj = os.path.join(tmp, 'message.json')
    rc, output = launch([sys.executable, os.path.join(HERE, 'message.py'), mj], env)
    try: msg = json.load(open(mj, encoding='utf-8'))
    except Exception: log('Message window: failed (code %s): %s' % (rc, output[-1500:]))
    with open(OUTPUT, 'w', encoding='utf-8') as f: json.dump(dict(header=hdr, types=types, message=msg), f)
    log('OK: %s (%d types, %.0f s)' % (OUTPUT, len(types), time.time() - t0))
    if bad: log('Unusable types (harmless if they are not used):', bad)


if __name__ == '__main__':
    try: main()
    except SystemExit as e:
        if e.code not in (None, 0): log('ERROR:', e.code)
        raise SystemExit(1 if e.code not in (None, 0) else 0)
    except BaseException:
        log('ERROR:\n' + traceback.format_exc()); raise SystemExit(1)
