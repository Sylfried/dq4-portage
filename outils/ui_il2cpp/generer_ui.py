"""Genere dq4_pc/cache/ui_layout.json : la mise en page EXACTE des fenetres de menu du jeu.

Principe : les fonctions MenuPortItemTable.Make_* du jeu (libil2cpp.so, ARM64) sont executees sous Unicorn avec des
« faux » appels Unity ; on relit les noeuds, maillages, textes et tables de liaison qu'elles construisent.
Rien n'est copie ni redistribue : le fichier produit reste dans cache/ (ignore par git).

Entrees : dq4_pc/cache/il2cpp/ (dump.cs, script.json, entrees/libil2cpp.so, entrees/global-metadata.dat : outils/dump_il2cpp.bat)
          dq4_pc/cache/ui_frameData.bin (extrait des APK automatiquement)
Usage   : python generer_ui.py [dossier_apk]"""
import concurrent.futures as cf, json, os, subprocess, sys, tempfile, time

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.abspath(os.path.join(ICI, '..', '..'))
CACHE = os.path.join(RACINE, 'dq4_pc', 'cache')
IL2 = os.path.join(CACHE, 'il2cpp')
SORTIE = os.path.join(CACHE, 'ui_layout.json')
APKS = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(RACINE, '..', 'jeux', 'DQ4', 'patched_apks'))


def main():
    for f in ('dump.cs', 'script.json', os.path.join('entrees', 'libil2cpp.so'), os.path.join('entrees', 'global-metadata.dat')):
        if not os.path.exists(os.path.join(IL2, f)):
            raise SystemExit('Manque %s : lance d\'abord outils\\dump_il2cpp.bat' % os.path.join(IL2, f))
    for m in ('unicorn',):
        try: __import__(m)
        except ImportError: raise SystemExit('Module Python manquant : %s (pip install %s dans dq4_pc\\.venv)' % (m, m))
    frame = os.path.join(CACHE, 'ui_frameData.bin')
    if not os.path.exists(frame):
        sys.path.insert(0, os.path.join(RACINE, 'dq4_pc'))
        import ui_menu
        if not ui_menu.preparer_ressources(APKS, CACHE) or not os.path.exists(frame):
            raise SystemExit('Impossible d\'extraire frameData des APK (%s)' % APKS)
    env = dict(os.environ, DQ_IL2=IL2, DQ_META=os.path.join(IL2, 'entrees', 'global-metadata.dat'), DQ_FRAME=frame, DQ_UI_H='800', PYTHONIOENCODING='utf-8')
    tmp = tempfile.mkdtemp(prefix='dq4_ui_')
    t0 = time.time()
    ent = os.path.join(tmp, 'entete.json')
    r = subprocess.run([sys.executable, os.path.join(ICI, 'entete.py'), ent], cwd=ICI, env=env, capture_output=True, text=True)
    if r.returncode or not os.path.exists(ent):
        raise SystemExit('Echec de la lecture de l\'en-tete :\n' + (r.stdout + r.stderr)[-2000:])
    hdr = json.load(open(ent)); n = hdr['nTypes']
    print('Mise en page des %d types de fenetres (quelques minutes, une seule fois)...' % n, flush=True)

    def un(k):
        out = os.path.join(tmp, 't%d.json' % k)
        p = subprocess.run([sys.executable, os.path.join(ICI, 'layout.py'), out, str(k)], cwd=ICI, env=env, capture_output=True, text=True)
        try: return k, json.load(open(out)).get(str(k)), None
        except Exception: return k, None, (p.stdout + p.stderr)[-300:]
    types = {}; faits = 0
    with cf.ThreadPoolExecutor(max_workers=max(1, min(4, (os.cpu_count() or 2)))) as ex:
        for k, res, err in ex.map(un, range(n)):
            faits += 1
            if res is not None: types[str(k)] = res
            if faits % 10 == 0 or faits == n: print('  %d / %d' % (faits, n), flush=True)
    mauvais = {k: v.get('err') for k, v in types.items() if v.get('err')}
    with open(SORTIE, 'w', encoding='utf-8') as f: json.dump(dict(header=hdr, types=types), f)
    print('OK : %s (%d types, %.0f s)' % (SORTIE, len(types), time.time() - t0))
    if mauvais: print('Types non exploitables (sans importance s\'ils ne sont pas utilises) :', mauvais)


if __name__ == '__main__':
    main()
