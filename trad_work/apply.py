"""usage: apply.py <depot (worktree)> <dossier des lots> -> remplace commentaires et docstrings traduits ; verifie que l'arbre du code est identique."""
import glob, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trad_lib as T
repo, bdir = sys.argv[1], sys.argv[2]
tr = {}
for p in sorted(glob.glob(os.path.join(bdir, 'batch_*.out.txt'))): tr.update(T.read_batch(p))
files = subprocess.check_output(['git', 'ls-files', '*.py'], cwd=repo, text=True).split()
changed = 0; nrep = 0; left = []; bad = 0
for f in files:
    p = os.path.join(repo, f); src = open(p, encoding='utf-8', newline='').read()
    new, n, missing = T.apply_translations(src, tr)
    left += [(f, m['kind'], m['text'][:70]) for m in missing]
    if new == src: continue
    if T.neutral_dump(src) != T.neutral_dump(new): print('ARBRE DIFFERENT', f); bad += 1; continue
    compile(new, f, 'exec')
    open(p, 'w', encoding='utf-8', newline='').write(new); changed += 1; nrep += n
print(f'{changed} fichiers modifies, {nrep} remplacements, {len(left)} textes sans traduction, {bad} erreurs')
with open(os.path.join(bdir, 'sans_traduction.txt'), 'w', encoding='utf-8') as fh:
    for f, k, t in left: fh.write(f'{f}\t{k}\t{t}\n')
sys.exit(1 if bad else 0)
