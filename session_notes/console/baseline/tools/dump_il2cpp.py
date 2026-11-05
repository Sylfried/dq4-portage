"""Extrait la STRUCTURE du code C# du jeu (classes, champs, methodes, adresses) avec Il2CppDumper.

Entrees (tes fichiers, jamais modifies) : libil2cpp.so et global-metadata.dat, pris dans tes APK.
Sorties : <racine>/data/cache/il2cpp/  (dump.cs, script.json, DummyDll...) -> ignore par git (code du jeu).
"""
import io, json, os, subprocess, sys, urllib.request, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
from dq4_pc import paths as CH
APKS = sys.argv[1] if len(sys.argv) > 1 else CH.FOLDERS.apk
OUTPUT = os.path.join(CH.FOLDERS.cache, 'il2cpp')
TOOL = os.path.join(OUTPUT, 'Il2CppDumper')
INPUTS = os.path.join(OUTPUT, 'entrees')


def find_apk(pattern):
    for f in sorted(os.listdir(APKS)):
        if f.lower().endswith('.apk') and pattern in f.lower():
            return os.path.join(APKS, f)
    raise SystemExit('APK introuvable (%s) dans %s' % (pattern, APKS))


def extract(apk, internal, dest):
    with zipfile.ZipFile(apk) as z:
        with z.open(internal) as src, open(dest, 'wb') as out:
            out.write(src.read())
    print('  extrait :', internal, '->', dest)


def download_tool():
    exe = None
    for root, _, files in os.walk(TOOL):
        if 'Il2CppDumper.exe' in files:
            exe = os.path.join(root, 'Il2CppDumper.exe')
    if exe:
        return exe
    print('Telechargement de Il2CppDumper (une seule fois)...')
    req = urllib.request.Request('https://api.github.com/repos/Perfare/Il2CppDumper/releases/latest', headers={'User-Agent': 'dq4-pc'})
    rel = json.load(urllib.request.urlopen(req, timeout=60))
    choice = None
    for pattern in ('net472', 'net6', 'net7', 'net8'):          # net472 = .NET Framework, deja present dans Windows 10/11
        for a in rel.get('assets', []):
            if pattern in a['name'].lower() and a['name'].lower().endswith('.zip'):
                choice = a; break
        if choice: break
    if not choice:
        raise SystemExit('Aucune archive Il2CppDumper trouvee dans la derniere version : ' + ', '.join(a['name'] for a in rel.get('assets', [])))
    print('  version :', rel.get('tag_name'), '/', choice['name'])
    data = urllib.request.urlopen(urllib.request.Request(choice['browser_download_url'], headers={'User-Agent': 'dq4-pc'}), timeout=300).read()
    os.makedirs(TOOL, exist_ok=True)
    zipfile.ZipFile(io.BytesIO(data)).extractall(TOOL)
    for root, _, files in os.walk(TOOL):
        if 'Il2CppDumper.exe' in files:
            return os.path.join(root, 'Il2CppDumper.exe')
    raise SystemExit("Il2CppDumper.exe absent de l'archive (%s)" % choice['name'])


def main():
    os.makedirs(INPUTS, exist_ok=True)
    print('APK lus dans :', APKS)
    extract(find_apk('arm64'), 'lib/arm64-v8a/libil2cpp.so', os.path.join(INPUTS, 'libil2cpp.so'))
    extract(find_apk('base'), 'assets/bin/Data/Managed/Metadata/global-metadata.dat', os.path.join(INPUTS, 'global-metadata.dat'))
    exe = download_tool()
    print('Extraction du code (1 a 3 minutes)...')
    env = dict(os.environ, DOTNET_ROLL_FORWARD='Major')      # l'outil vise .NET 6 : accepte aussi .NET 7/8/9 s'ils sont installes
    logfile = os.path.join(OUTPUT, 'journal.txt')
    lines = []
    try:
        p = subprocess.Popen([exe, os.path.join(INPUTS, 'libil2cpp.so'), os.path.join(INPUTS, 'global-metadata.dat'), OUTPUT],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=os.path.dirname(exe), env=env)
        p.stdin.write(b'\n'); p.stdin.close()                 # l'outil attend une touche a la fin
        for raw_value in p.stdout:
            l = raw_value.decode('utf-8', 'replace').rstrip()
            lines.append(l); print(' ', l)
        p.wait()
    except OSError as ex:
        lines.append('Impossible de lancer Il2CppDumper : %s' % ex); print(lines[-1])
    with open(logfile, 'w', encoding='utf-8') as fj: fj.write('\n'.join(lines) + '\n')
    dump = os.path.join(OUTPUT, 'dump.cs')
    if os.path.exists(dump):                                  # un code non nul apres l'ecriture (attente de touche) est sans importance
        print('\nOK : %s (%.1f Mo)' % (dump, os.path.getsize(dump) / 1e6))
        print('Dis a Claude : "le dump est pret" (il lit le fichier sur ton PC).')
    else:
        print("\nEchec : dump.cs n'a pas ete cree. Journal : " + logfile)
        print("Cause probable : .NET manque. Installe-le puis relance ce fichier :")
        print("    winget install Microsoft.DotNet.Runtime.8")
        raise SystemExit(1)


if __name__ == '__main__':
    main()
