"""Genere dq4_pc/cache/ui_layout.json : la mise en page EXACTE des fenetres de menu du jeu.

Principe : les fonctions MenuPortItemTable.Make_* du jeu (libil2cpp.so, ARM64) sont executees sous Unicorn avec des
« faux » appels Unity ; on relit les noeuds, maillages, textes et tables de liaison qu'elles construisent.
Rien n'est copie ni redistribue : le fichier produit reste dans cache/ (ignore par git).

Entrees : dq4_pc/cache/il2cpp/ (dump.cs, script.json, entrees/libil2cpp.so, entrees/global-metadata.dat : outils/dump_il2cpp.bat)
          dq4_pc/cache/ui_frameData.bin (extrait des APK automatiquement)
Usage   : python generer_ui.py [dossier_apk]"""
import concurrent.futures as cf, json, os, platform, subprocess, sys, tempfile, time, traceback

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.abspath(os.path.join(ICI, '..', '..'))
CACHE = os.path.join(RACINE, 'dq4_pc', 'cache')
IL2 = os.path.join(CACHE, 'il2cpp')
SORTIE = os.path.join(CACHE, 'ui_layout.json')
APKS = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(RACINE, '..', 'jeux', 'DQ4', 'patched_apks'))
JOURNAL = os.path.join(CACHE, 'ui_generation.log')
_j = None


def log(*a):
    """Affiche et ecrit dans cache/ui_generation.log (UTF-8) : permet de diagnostiquer sans console."""
    t = ' '.join(str(x) for x in a)
    try: print(t, flush=True)
    except Exception: print(t.encode('ascii', 'replace').decode(), flush=True)
    if _j:
        _j.write(t + '\n'); _j.flush()


def lancer(args, env):
    """Lance un sous-processus Python ; sortie lue en UTF-8 tolerant (la console Windows n'est pas en UTF-8)."""
    p = subprocess.run(args, cwd=ICI, env=env, capture_output=True)
    return p.returncode, (p.stdout + p.stderr).decode('utf-8', 'replace')


def main():
    global _j
    os.makedirs(CACHE, exist_ok=True)
    _j = open(JOURNAL, 'w', encoding='utf-8')
    try: import unicorn; uv = getattr(unicorn, '__version__', '?')
    except Exception as e: uv = 'absent (%r)' % (e,)
    log('Python %s, %s, unicorn %s, executable %s' % (sys.version.split()[0], platform.platform(), uv, sys.executable))
    log('Racine : %s | cache : %s | apk : %s' % (RACINE, CACHE, APKS))
    for f in ('dump.cs', 'script.json', os.path.join('entrees', 'libil2cpp.so'), os.path.join('entrees', 'global-metadata.dat')):
        if not os.path.exists(os.path.join(IL2, f)):
            raise SystemExit('Manque %s : lance d\'abord outils\\dump_il2cpp.bat' % os.path.join(IL2, f))
    for m in ('unicorn', 'capstone'):            # capstone : desassemblage du code ARM64 (obligatoire pour l'analyse des fonctions)
        try: __import__(m)
        except ImportError:
            log('Module Python manquant : %s -> installation (une seule fois)...' % m)
            r, out = lancer([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--quiet', m], os.environ)
            log(out[-800:])
            try: __import__(m)
            except ImportError: raise SystemExit('Module Python manquant : %s (pip install %s dans dq4_pc\\.venv)' % (m, m))
    frame = os.path.join(CACHE, 'ui_frameData.bin')
    if not os.path.exists(frame):
        sys.path.insert(0, os.path.join(RACINE, 'dq4_pc'))
        import ui_menu
        if not ui_menu.preparer_ressources(APKS, CACHE) or not os.path.exists(frame):
            raise SystemExit('Impossible d\'extraire frameData des APK (%s)' % APKS)
    env = dict(os.environ, PYTHONUTF8='1', DQ_IL2=IL2, DQ_META=os.path.join(IL2, 'entrees', 'global-metadata.dat'), DQ_FRAME=frame, DQ_UI_H='800', PYTHONIOENCODING='utf-8')
    tmp = tempfile.mkdtemp(prefix='dq4_ui_')
    t0 = time.time()
    ent = os.path.join(tmp, 'entete.json')
    rc, sortie = lancer([sys.executable, os.path.join(ICI, 'entete.py'), ent], env)
    log('en-tete : code %s, %.0f s' % (rc, time.time() - t0))
    if rc or not os.path.exists(ent):
        log(sortie[-6000:])
        raise SystemExit('Echec de la lecture de l\'en-tete (details : %s)' % JOURNAL)
    hdr = json.load(open(ent)); n = hdr['nTypes']
    log('Mise en page des %d types de fenetres (quelques minutes, une seule fois)...' % n)

    def un(k):
        out = os.path.join(tmp, 't%d.json' % k)
        rc, sortie = lancer([sys.executable, os.path.join(ICI, 'layout.py'), out, str(k)], env)
        try: return k, json.load(open(out, encoding='utf-8')).get(str(k)), None
        except Exception: return k, None, 'code %s : %s' % (rc, sortie[-1500:])
    types = {}; faits = 0; echecs = {}
    with cf.ThreadPoolExecutor(max_workers=max(1, min(4, (os.cpu_count() or 2)))) as ex:
        for k, res, err in ex.map(un, range(n)):
            faits += 1
            if res is not None: types[str(k)] = res
            elif err: echecs[k] = err
            if faits % 10 == 0 or faits == n: log('  %d / %d' % (faits, n))
    for k, e in echecs.items(): log('Type %d : sous-processus en echec : %s' % (k, e))
    if not types: raise SystemExit('Aucun type n\'a pu etre lu (details : %s)' % JOURNAL)
    mauvais = {k: v.get('err') for k, v in types.items() if v.get('err')}
    msg = None                                                   # fenetre de message (MenuMessage) : cadre, canevas du texte, curseur
    mj = os.path.join(tmp, 'message.json')
    rc, sortie = lancer([sys.executable, os.path.join(ICI, 'message.py'), mj], env)
    try: msg = json.load(open(mj, encoding='utf-8'))
    except Exception: log('Fenetre de message : echec (code %s) : %s' % (rc, sortie[-1500:]))
    with open(SORTIE, 'w', encoding='utf-8') as f: json.dump(dict(header=hdr, types=types, message=msg), f)
    log('OK : %s (%d types, %.0f s)' % (SORTIE, len(types), time.time() - t0))
    if mauvais: log('Types non exploitables (sans importance s\'ils ne sont pas utilises) :', mauvais)


if __name__ == '__main__':
    try: main()
    except SystemExit as e:
        if e.code not in (None, 0): log('ERREUR :', e.code)
        raise SystemExit(1 if e.code not in (None, 0) else 0)
    except BaseException:
        log('ERREUR :\n' + traceback.format_exc()); raise SystemExit(1)
