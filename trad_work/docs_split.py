"""usage: docs_split.py <depot> <dossier de sortie> [taille cible d'un morceau en octets]
Coupe chaque .md en morceaux (aux titres, puis aux lignes vides, jamais dans un bloc de code ni au milieu d'un tableau sauf entre deux lignes)
-> docs/<nom_aplati>.NNN.in.md ; manifest.json : liste ordonnee des morceaux de chaque fichier. Concatener les morceaux traduits redonne le fichier."""
import json, os, re, subprocess, sys
repo, outdir = sys.argv[1], sys.argv[2]; target = int(sys.argv[3]) if len(sys.argv) > 3 else 30000
os.makedirs(outdir, exist_ok=True)
files = subprocess.check_output(['git', 'ls-files', '*.md'], cwd=repo, text=True).split()
prio = lambda f: (0 if f in ('README.md', 'docs/resume.md') else 1 if f.startswith('docs/audit/decisions') or f == 'docs/history.md' else 3 if f.startswith('docs/archives') else 2, f)
files.sort(key=prio)
manifest = {}
def split(text):
    lines = text.split('\n'); chunks = []; cur = []; size = 0; fence = False
    for i, line in enumerate(lines):
        if line.startswith('```'): fence = not fence
        nxt_head = (not fence) and re.match(r'#{1,3} ', line) is not None
        n = len(line.encode()) + 1
        cut = False
        if cur and not fence:
            if size >= target: cut = True                                           # assez gros : coupe des qu'on est hors bloc de code
            elif nxt_head and size >= target * 0.6: cut = True                      # titre : coupe si le morceau est deja bien rempli
        if cut and not (line.startswith('|') and cur and cur[-1].startswith('|') and size < target * 1.6 and False):
            if not (line.strip() == '' and False): chunks.append('\n'.join(cur)); cur = []; size = 0
        cur.append(line); size += n
    if cur: chunks.append('\n'.join(cur))
    return chunks
for f in files:
    text = open(os.path.join(repo, f), encoding='utf-8', newline='').read()
    assert '\r' not in text, f
    chunks = split(text)
    assert '\n'.join(chunks) == text, f
    flat = f.replace('/', '__')
    names = []
    for k, c in enumerate(chunks, 1):
        nm = f'{flat}.{k:03d}.in.md'; names.append(nm)
        open(os.path.join(outdir, nm), 'w', encoding='utf-8', newline='\n').write(c)
    manifest[f] = names
json.dump(manifest, open(os.path.join(outdir, 'manifest.json'), 'w'), indent=1)
print(len(files), 'fichiers,', sum(len(v) for v in manifest.values()), 'morceaux')
