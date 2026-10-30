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
    env = dict(os.environ, DOTNET_ROLL_FORWARD='Major')      # l'outil vise .NET 6 : accepte aussi .NET 7/8/9 s'ils sont installes
    journal = os.path.join(SORTIE, 'journal.txt')
    lignes = []
    try:
        p = subprocess.Popen([exe, os.path.join(ENTREES, 'libil2cpp.so'), os.path.join(ENTREES, 'global-metadata.dat'), SORTIE],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.dirname(exe), env=env)
        p.stdin.write(b'\n'); p.stdin.close()                 # l'outil attend une touche a la fin
        for brut in p.stdout:
            l = brut.decode('utf-8', 'replace').rstrip()
            lignes.append(l); print(' ', l)
        p.wait()
    except OSError as ex:
        lignes.append('Impossible de lancer Il2CppDumper : %s' % ex); print(lignes[-1])
    with open(journal, 'w', encoding='utf-8') as fj: fj.write('\n'.join(lignes) + '\n')
    dump = os.path.join(SORTIE, 'dump.cs')
    if os.path.exists(dump):                                  # un code non nul apres l'ecriture (attente de touche) est sans importance
        print('\nOK : %s (%.1f Mo)' % (dump, os.path.getsize(dump) / 1e6))
        print('Dis a Claude : "le dump est pret" (il lit le fichier sur ton PC).')
    else:
        print("\nEchec : dump.cs n'a pas ete cree. Journal : " + journal)
        print("Cause probable : .NET manque. Installe-le puis relance ce fichier :")
        print("    winget install Microsoft.DotNet.Runtime.8")
        raise SystemExit(1)


if __name__ == '__main__':
    main()
