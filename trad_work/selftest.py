import subprocess, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trad_lib as T
os.chdir('/home/claude/dq4-portage')
files = subprocess.check_output(['git','ls-files','*.py'],text=True).split()
bad = 0; nc = nd = 0; sizes = collections.Counter()
for f in files:
    src = open(f, encoding='utf-8', newline='').read()
    try:
        its = T.comment_items(src) + T.docstring_items(src)
    except Exception as e:
        print('EXTRACT FAIL', f, repr(e)); bad += 1; continue
    tr = {i['id']: i['text'] + ' [EN]' for i in its}
    new, n, missing = T.apply_translations(src, tr)
    nc += sum(1 for i in its if i['kind']=='c'); nd += sum(1 for i in its if i['kind']=='d')
    try:
        if T.neutral_dump(src) != T.neutral_dump(new): print('AST DIFF', f); bad += 1
    except Exception as e:
        print('PARSE FAIL', f, repr(e)); bad += 1; continue
    # identite
    ident, n0, _ = T.apply_translations(src, {i['id']: i['text'] for i in its})
    if ident != src: print('IDENTITY DIFF', f); bad += 1
    # docstring runtime value check
    import ast
    t0 = ast.parse(src); t1 = ast.parse(new)
    d0 = [ast.get_docstring(n, clean=True) for n in ast.walk(t0) if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))]
    d1 = [ast.get_docstring(n, clean=True) for n in ast.walk(t1) if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))]
    for a, b in zip(d0, d1):
        if a is not None and a.strip() and not b.endswith('[EN]') and any(i['kind']=='d' and i['text']==a.strip() for i in its):
            print('DOC VALUE', f, repr(a[:60]), repr(b[-30:])); bad += 1; break
print('files', len(files), 'comment items', nc, 'docstring items', nd, 'problems', bad)
