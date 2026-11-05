"""apply.py ROOT [--write] : replace console strings by English. Reads maps.py (T, SITE, EXTRA_TR, SKIP)."""
import ast, os, re, sys, json, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(sys.argv[1]); WRITE = '--write' in sys.argv
sys.path.insert(0, ROOT)
import maps; importlib.reload(maps)
from dq4_pc import language as LG
CAT = LG.catalog()
ACC = re.compile('[àâäçéèêëîïôöùûüÿœÀÂÇÉÈÊËÎÏÔÙÛÜŒ«»…°]')
SINKS = {'print','log','note','_wait','warn','warning','exit','SystemExit','error','info','debug','critical','L','_record_missing','_failure','_note_once','_note','note_error','_log_window','show','out'}
SINKS |= set(getattr(maps, 'EXTRA_SINKS', ()))
SINKS -= set(getattr(maps, 'NOT_SINKS', ()))
def fname(f):
    if isinstance(f, ast.Name): return f.id
    if isinstance(f, ast.Attribute): return f.attr
def norm(s):
    for a, b in (('Fullscreen','Full screen'),('fullscreen','full screen'),('Save state','Savestate'),('save state','savestate')): s = s.replace(a, b)
    return s
def lit(new, orig):
    q = orig[0] if orig[0] in '\'"' else ("'" if True else '"')
    if orig[:1] in 'rRbBfF' and len(orig) > 1: q = orig[1]
    if orig.startswith(('"""', "'''")): q = orig[0]
    def esc(s, q):
        return s.replace('\\', '\\\\').replace(q, '\\' + q).replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')
    if q not in new: return q + esc(new, q) + q
    other = '"' if q == "'" else "'"
    if other not in new: return other + esc(new, other) + other
    return q + esc(new, q) + q
def role(n, call, parents):
    x = n
    while id(x) in parents and parents[id(x)] is not call:
        p = parents[id(x)]
        if isinstance(p, (ast.JoinedStr, ast.IfExp, ast.Starred, ast.Tuple, ast.List, ast.BoolOp, ast.keyword)): pass
        elif isinstance(p, ast.BinOp) and isinstance(p.op, (ast.Mod, ast.Add)): pass
        elif isinstance(p, ast.Call) and fname(p.func) in ('tr', 'N_'): pass
        elif isinstance(p, ast.Call) and isinstance(p.func, ast.Attribute) and p.func.attr == 'format' and p.func.value is x: pass
        else: return 'other'
        x = p
    return 'text'
def offsets(src):
    lines = src.splitlines(keepends=True); starts = []; pos = 0
    for l in lines: starts.append(pos); pos += len(l)
    def off(lineno, col_bytes):
        line = lines[lineno - 1]; return starts[lineno - 1] + len(line.encode('utf-8')[:col_bytes].decode('utf-8'))
    return off
report = {'changed': [], 'unresolved': [], 'skipped': []}
files = []
ONLY = [a.split('=',1)[1] for a in sys.argv if a.startswith('--only=')]
for sub in (ONLY or ['dq4_pc', 'tools']):
    for d, _, fs in os.walk(os.path.join(ROOT, sub)):
        if '__pycache__' in d: continue
        for f in sorted(fs):
            if f.endswith('.py'): files.append(os.path.join(d, f))
files += [os.path.join(ROOT, f) for f in getattr(maps, 'EXTRA_FILES', ())]
for p in files:
    rel = os.path.relpath(p, ROOT)
    if rel.endswith('language.py') or '/texts_en/' in rel: continue
    src = open(p, encoding='utf-8').read(); tree = ast.parse(src); parents = {id(c): n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
    off = offsets(src)
    docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant): docs.add(id(n.body[0].value))
    cands = {}   # const node id -> (const, kind, role)
    def add(c, kind, r):
        if id(c) in docs: return
        cands.setdefault(id(c), (c, kind, r))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            nm = fname(node.func)
            if nm in SINKS:
                for a in node.args:
                    for c in ast.walk(a):
                        if isinstance(c, ast.Constant) and isinstance(c.value, str): add(c, 'sink:' + nm, role(c, node, parents))
                for k in node.keywords:
                    if k.arg in ('file', 'flush', 'end', 'sep', 'alert'): continue
                    for c in ast.walk(k.value):
                        if isinstance(c, ast.Constant) and isinstance(c.value, str): add(c, 'sink:' + nm, role(c, node, parents))
            elif nm in ('add_argument', 'ArgumentParser', 'add_parser', 'add_argument_group', 'add_subparsers'):
                for k in node.keywords:
                    if k.arg in ('help', 'description', 'epilog', 'usage', 'title'):
                        for c in ast.walk(k.value):
                            if isinstance(c, ast.Constant) and isinstance(c.value, str): add(c, 'argparse', role(c, node, parents))
        elif isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            for a in node.exc.args:
                for c in ast.walk(a):
                    if isinstance(c, ast.Constant) and isinstance(c.value, str): add(c, 'raise', role(c, node.exc, parents))
        elif isinstance(node, ast.Assert) and node.msg is not None:
            for c in ast.walk(node.msg):
                if isinstance(c, ast.Constant) and isinstance(c.value, str): add(c, 'assert', 'text')
    # extra tr/N_ literals (outside sinks) listed per file
    extra = set(maps.EXTRA_TR.get(rel, ()))
    if extra:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and fname(node.func) in ('tr', 'N_') and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value in extra:
                add(node.args[0], 'extra', 'text')
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in getattr(maps, 'FORCE', {}).get(rel, {}) and id(n) not in docs:
            cands[id(n)] = (n, 'force', 'text')
        elif rel in getattr(maps, 'FORCE_MULTI', ()) and isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in maps.T and (' ' in n.value or '%' in n.value) and id(n) not in docs:
            cands[id(n)] = (n, 'forcemulti', 'text')
    skip_kinds = maps.SKIP_RAISE.get(rel, ())
    edits = []
    for cid, (c, kind, r) in cands.items():
        v = c.value; par = parents.get(id(c))
        in_tr = isinstance(par, ast.Call) and fname(par.func) in ('tr', 'N_') and par.args and par.args[0] is c
        site = (rel, c.lineno, v)
        if kind == 'raise' and rel in maps.SKIP_RAISE and (maps.SKIP_RAISE[rel] == '*' or v in maps.SKIP_RAISE[rel]):
            report['skipped'].append((rel, c.lineno, v)); continue
        new = None
        if kind == 'force': new = maps.FORCE[rel][v]
        elif kind == 'forcemulti': new = maps.T[v]
        elif site in maps.SITE: new = maps.SITE[site]
        elif v in maps.T and r == 'text': new = maps.T[v]
        elif in_tr and v in CAT and r == 'text' and (kind != 'sink:print' or True): new = norm(CAT[v])
        if new is None:
            if (ACC.search(v) or maps.looks_french(v)) and len(v.strip()) > 1 and r == 'text': report['unresolved'].append((rel, c.lineno, kind, v))
            continue
        if new == v and not in_tr: continue
        target = par if in_tr else c
        # span
        s0 = off(target.lineno, target.col_offset); s1 = off(target.end_lineno, target.end_col_offset)
        orig_seg = src[off(c.lineno, c.col_offset):off(c.end_lineno, c.end_col_offset)]
        edits.append((s0, s1, lit(new, orig_seg), rel, c.lineno, v, new))
    edits.sort(key=lambda e: e[0], reverse=True)
    # dedupe overlapping
    out = src; last = None
    for s0, s1, text, rel_, ln, v, new in edits:
        if last is not None and s1 > last: continue
        out = out[:s0] + text + out[s1:]; last = s0
        report['changed'].append((rel_, ln, v, new))
    for old, new in getattr(maps, 'TEXT_EDITS', {}).get(rel, ()):
        if out.count(old) == 0 and out.count(new) >= 1: continue
        assert out.count(old) == 1, (rel, old, out.count(old))
        out = out.replace(old, new); report['changed'].append((rel, 0, old, new))
    if WRITE and out != src:
        with open(p, 'w', encoding='utf-8', newline='') as f: f.write(out)
json.dump(report, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'report.json'), 'w'), ensure_ascii=False, indent=1)
print('changed', len(report['changed']), 'unresolved', len(report['unresolved']), 'skipped', len(report['skipped']))
for r in report['unresolved']: print('UNRESOLVED %s:%d %s %s' % (r[0], r[1], r[2], json.dumps(r[3], ensure_ascii=False)[:230]))
