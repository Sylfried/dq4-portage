"""usage: check_idents.py <depot> <dossier final> : identifiants cites par la traduction qui n'existent pas dans le code ET qui n'etaient pas dans le texte francais."""
import glob, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trad_lib as T
repo, fdir = sys.argv[1], sys.argv[2]
code = ''
for f in subprocess.check_output(['git', 'ls-files', '*.py'], cwd=repo, text=True).split():
    code += open(os.path.join(repo, f), encoding='utf-8').read() + '\n'
words = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', code))
ID = re.compile(r'`([A-Za-z_][A-Za-z0-9_.]*)(?:\(\))?`|\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)\b|\b([a-z_][a-z0-9_]{3,})\(')
n = 0
for p in sorted(glob.glob(os.path.join(fdir, 'batch_*.out.txt'))):
    nb = os.path.basename(p).replace('.out.', '.in.')
    out = T.read_batch(p); inp = T.read_batch(os.path.join(os.path.dirname(os.path.dirname(p)), 'batches', nb))
    for i, t in out.items():
        src = inp.get(i, '')
        for m in ID.finditer(t):
            tok = next(g for g in m.groups() if g)
            if tok in src: continue
            parts = [x for x in tok.split('.') if x]
            if all(x in words for x in parts): continue
            if tok.endswith(('.py', '.json', '.md', '.log', '.dat', '.dqs', '.txt', '.bat', '.apk', '.zip', '.pkl')): continue
            n += 1; print(f'{os.path.basename(p)[6:8]} {i} {tok}')
print('total', n)
