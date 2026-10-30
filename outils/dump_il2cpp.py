"""Extrait la STRUCTURE du code C# du jeu (classes, champs, methodes, adresses) avec Il2CppDumper.

Entrees (tes fichiers, jamais modifies) : libil2cpp.so et global-metadata.dat, pris dans tes APK.
Sorties : <racine>/dq4_pc/cache/il2cpp/  (dump.cs, script.json, DummyDll...) -> ignore par git (code du jeu).
"""
import io, json, os, subprocess, sys, urllib.request, zipfile

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
APKS = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(RACINE, '..', 'jeux', 'DQ4', 'patched_apks'))
SORTIE = os.path.join(RACINE, 'dq4_pc', 'cache', 'il2cpp')
OUTIL = os.path.join(SORTIE, 'Il2CppDumper')
ENTREES = os.path.join(SORTIE, 'entrees')


def trouver_apk(motif):
    for f in sorted(os.listdir(APKS)):
        if f.lower().endswith('.apk') and motif in f.lower():
            return os.path.join(APKS, f)
    raise SystemExit('APK introuvable (%s) dans %s' % (motif, APKS))


def extraire(apk, interne, dest):
    with zipfile.ZipFile(apk) as z:
        with z.open(interne) as src, open(dest, 'wb') as out:
            out.write(src.read())
    print('  extrait :', interne, '->', dest)


def telecharger_outil():
    exe = None
    for racine, _, fichiers in os.walk(OUTIL):
        if 'Il2CppDumper.exe' in fichiers:
            exe = os.path.join(racine, 'Il2CppDumper.exe')
    if exe:
        return exe
    print('Telechargement de Il2CppDumper (une seule fois)...')
    req = urllib.request.Request('https://api.github.com/repos/Perfare/Il2CppDumper/releases/latest', headers={'User-Agent': 'dq4-pc'})
    rel = json.load(urllib.request.urlopen(req, timeout=60))
    choix = None
    for motif in ('net472', 'net6', 'net7', 'net8'):          # net472 = .NET Framework, deja present dans Windows 10/11
        for a in rel.get('assets', []):
            if motif in a['name'].lower() and a['name'].lower().endswith('.zip'):
                choix = a; break
        if choix: break
    if not choix:
        raise SystemExit('Aucune archive Il2CppDumper trouvee dans la derniere version : ' + ', '.join(a['name'] for a in rel.get('assets', [])))
    print('  version :', rel.get('tag_name'), '/', choix['name'])
    data = urllib.request.urlopen(urllib.request.Request(choix['browser_download_url'], headers={'User-Agent': 'dq4-pc'}), timeout=300).read()
    os.makedirs(OUTIL, exist_ok=True)
    zipfile.ZipFile(io.BytesIO(data)).extractall(OUTIL)
    for racine, _, fichiers in os.walk(OUTIL):
        if 'Il2CppDumper.exe' in fichiers:
            return os.path.join(racine, 'Il2CppDumper.exe')
    raise SystemExit("Il2CppDumper.exe absent de l'archive (%s)" % choix['name'])


def main():
    os.makedirs(ENTREES, exist_ok=True)
    print('APK lus dans :', APKS)
    extraire(trouver_apk('arm64'), 'lib/arm64-v8a/libil2cpp.so', os.path.join(ENTREES, 'libil2cpp.so'))
    extraire(trouver_apk('base'), 'assets/bin/Data/Managed/Metadata/global-metadata.dat', os.path.join(ENTREES, 'global-metadata.dat'))
    exe = telecharger_outil()
    print('Extraction du code (1 a 3 minutes)...')
    r = subprocess.run([exe, os.path.join(ENTREES, 'libil2cpp.so'), os.path.join(ENTREES, 'global-metadata.dat'), SORTIE],
                       input=b'\n', cwd=os.path.dirname(exe))
    dump = os.path.join(SORTIE, 'dump.cs')
    if os.path.exists(dump):                                  # l'outil attend une touche a la fin : un code non nul apres l'ecriture est sans importance
        print('\nOK : %s (%.1f Mo)' % (dump, os.path.getsize(dump) / 1e6))
        print('Dis a Claude : "le dump est pret" (il lit le fichier sur ton PC).')
    else:
        raise SystemExit("Echec : dump.cs n'a pas ete cree (code %s). Copie le texte ci-dessus a Claude." % r.returncode)


if __name__ == '__main__':
    main()
