"""Extraction / remise en place des commentaires et docstrings d'un fichier Python.
Les identifiants de traduction sont des empreintes du texte : une meme phrase est traduite une seule fois, et la remise en place
retrouve ses elements dans la version ACTUELLE du fichier (les lignes ont pu bouger depuis l'extraction)."""
import ast, hashlib, io, re, tokenize

SKIP_FIRST = re.compile(r'^(noqa|type:|pragma|fmt:|pylint|mypy|isort|-\*-|!|coding[:=])', re.I)
HAS_WORD = re.compile(r'[A-Za-zÀ-ÿ]{3,}')


def sha(kind, text):
    return hashlib.sha1((kind + '\0' + text).encode('utf-8')).hexdigest()[:12]


def char_col(line, byte_col):
    return len(line.encode('utf-8')[:byte_col].decode('utf-8', errors='ignore'))


def comment_items(src):
    """-> liste d'elements {'kind': 'c', 'rows': (r1, r2), 'col': c, 'full': bool, 'text': str}"""
    lines = src.split('\n')
    toks = [t for t in tokenize.generate_tokens(io.StringIO(src).readline) if t.type == tokenize.COMMENT]
    items = []; cur = None
    for t in toks:
        (row, col), s = t.start, t.string
        if row <= 2 and (s.startswith('#!') or 'coding' in s): cur = None; continue
        body = s[1:]
        if body.startswith(' '): body = body[1:]
        body = body.rstrip()
        full = lines[row - 1][:col].strip() == ''
        if full and cur is not None and cur['rows'][1] == row - 1 and cur['col'] == col:
            cur['rows'] = (cur['rows'][0], row); cur['lines'].append(body)
            continue
        cur = {'kind': 'c', 'rows': (row, row), 'col': col, 'full': full, 'lines': [body]}
        items.append(cur)
        if not full: cur = None
    out = []
    for it in items:
        text = '\n'.join(it['lines'])
        if SKIP_FIRST.match(it['lines'][0].strip()) or not HAS_WORD.search(text): continue
        it['text'] = text; it['id'] = sha('c', text); out.append(it)
    return out


def _dedent_doc(raw):
    ls = raw.split('\n')
    rest = ls[1:]
    ind = min((len(l) - len(l.lstrip(' \t')) for l in rest if l.strip()), default=0)
    out = [ls[0].strip()] + [l[ind:].rstrip() if l.strip() else '' for l in rest]
    return '\n'.join(out).strip('\n')


def docstring_items(src):
    """-> liste d'elements {'kind': 'd', 'span': (r1, c1, r2, c2) en caracteres, 'text': str, 'lead_nl', 'trail_nl', 'indent', 'prefix', 'quote'}"""
    lines = src.split('\n')
    tree = ast.parse(src)
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)): continue
        if not n.body: continue
        e = n.body[0]
        if not (isinstance(e, ast.Expr) and isinstance(e.value, ast.Constant) and isinstance(e.value.str if False else e.value.value, str)): continue
        v = e.value
        r1, r2 = v.lineno, v.end_lineno
        c1 = char_col(lines[r1 - 1], v.col_offset); c2 = char_col(lines[r2 - 1], v.end_col_offset)
        lit = (lines[r1 - 1][c1:] + '\n' + '\n'.join(lines[r1:r2 - 1]) + '\n' + lines[r2 - 1][:c2]) if r2 > r1 else lines[r1 - 1][c1:c2]
        m = re.match(r'([rRuU]*)("""|\'\'\'|"|\')', lit)
        if not m: continue
        raw = v.value
        text = _dedent_doc(raw)
        if not HAS_WORD.search(text): continue
        out.append({'kind': 'd', 'span': (r1, c1, r2, c2), 'text': text, 'id': sha('d', text), 'lead_nl': raw.startswith('\n'),
                    'trail_nl': bool(re.search(r'\n[ \t]*\Z', raw)), 'indent': c1, 'prefix': m.group(1), 'quote': m.group(2)})
    return out


def render_doc(it, new):
    lines = new.strip('\n').split('\n'); ind = ' ' * it['indent']
    if it['lead_nl']: body = '\n' + '\n'.join(ind + l if l.strip() else '' for l in lines)
    else: body = lines[0] + ''.join('\n' + (ind + l if l.strip() else '') for l in lines[1:])
    if it['trail_nl']: body += '\n' + ind
    q = it['quote']; prefix = it['prefix']
    if len(q) == 1 and '\n' in body: q = '"""'
    raw_ok = 'r' in prefix.lower() and q not in body and not body.rstrip('\n ').endswith('\\')
    if raw_ok: lit_prefix = prefix
    else:
        lit_prefix = prefix.replace('r', '').replace('R', '')
        body = body.replace('\\', '\\\\')
    if not raw_ok:
        body = body.replace(q, '\\' + '\\'.join(q)) if len(q) == 3 else body.replace(q, '\\' + q)
        if body.endswith(q[0]) and len(q) == 3: body = body[:-1] + '\\' + q[0]
    return lit_prefix + q + body + q


def neutral_dump(src):
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.body:
            e = n.body[0]
            if isinstance(e, ast.Expr) and isinstance(e.value, ast.Constant) and isinstance(e.value.value, str): e.value.value = ''
    return ast.dump(tree)


def apply_translations(src, tr, want_kinds=('c', 'd')):
    """-> (nouvelle source, nb remplaces, liste des elements sans traduction)"""
    lines = src.split('\n'); edits = []; missing = []
    for it in (comment_items(src) if 'c' in want_kinds else []) + (docstring_items(src) if 'd' in want_kinds else []):
        new = tr.get(it['id'])
        if new is None: missing.append(it); continue
        if new == it['text']: continue
        if it['kind'] == 'c':
            r1, r2 = it['rows']; col = it['col']
            if it['full']:
                nl = [' ' * col + ('# ' + l if l.strip() else '#') for l in new.split('\n')]
                edits.append((r1, 0, r2, len(lines[r2 - 1]), '\n'.join(nl)))
            else:
                edits.append((r1, col, r1, len(lines[r1 - 1]), '# ' + ' '.join(x.strip() for x in new.split('\n') if x.strip())))
        else:
            r1, c1, r2, c2 = it['span']
            edits.append((r1, c1, r2, c2, render_doc(it, new)))
    edits.sort(key=lambda e: (e[0], e[1]), reverse=True)
    for r1, c1, r2, c2, text in edits:
        head = lines[r1 - 1][:c1]; tail = lines[r2 - 1][c2:]
        lines[r1 - 1:r2] = (head + text + tail).split('\n')
    return '\n'.join(lines), len(edits), missing


# ---- format des lots : « @@ id » puis le texte --------------------------------------------------
def write_batch(path, groups):
    """groups : liste de (fichier, [(id, kind, text)])"""
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        for fn, its in groups:
            f.write(f'## FILE {fn}\n')
            for i, kind, text in its: f.write(f'@@ {i} {kind}\n{text}\n')


def read_batch(path):
    out = {}; cur = None; buf = []
    for line in open(path, encoding='utf-8').read().split('\n'):
        if line.startswith('@@ '):
            if cur: out[cur] = '\n'.join(buf).rstrip('\n')
            cur = line.split()[1]; buf = []
        elif line.startswith('## FILE '):
            if cur: out[cur] = '\n'.join(buf).rstrip('\n'); cur = None; buf = []
        elif cur is not None: buf.append(line)
    if cur: out[cur] = '\n'.join(buf).rstrip('\n')
    return out
