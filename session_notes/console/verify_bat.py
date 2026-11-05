"""Static checks of launch_dq4.bat (cannot be run on Linux): labels, calls, parentheses, CRLF, ASCII, content equal to the old English messages."""
import re, subprocess, sys
P = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/wt-console/launch_dq4.bat'
b = open(P, 'rb').read(); errors = []
def err(m): errors.append(m); print('ERROR', m)
# line endings / charset
if b.count(b'\r\n') != b.count(b'\n') or b.count(b'\r') != b.count(b'\r\n'): err('mixed or lone line endings')
if not b.endswith(b'\r\n'): err('no final CRLF')
if any(c > 127 for c in b): err('non-ASCII byte')
if errors: print('RESULT: %d error(s)' % len(errors)); sys.exit(1)
text = b.decode('ascii'); lines = text.split('\r\n')[:-1]
# labels and calls
labels = {}; calls = []
for n, l in enumerate(lines, 1):
    m = re.match(r'^:(\w+)\s*$', l)
    if m:
        if m.group(1) in labels: err('duplicate label %s' % m.group(1))
        labels[m.group(1)] = n
    for m in re.finditer(r'\bcall :(\w+)', l):
        calls.append((n, m.group(1)))
called = {c for _, c in calls}
for n, c in calls:
    if c not in labels: err('line %d: call :%s has no label' % (n, c))
for lab, n in labels.items():
    if lab not in called: err('line %d: label :%s is never called (orphan)' % (n, lab))
for l in lines:
    if re.search(r'DQLANG|%LOC|_fr\b|_en\b', l): err('language machinery left: %r' % l)
# each label block ends with exit /b before the next label / end of file
keys = sorted(labels.values()) + [len(lines) + 1]
for lab, n in labels.items():
    nxt = min(k for k in keys if k > n)
    block = [l for l in lines[n:nxt - 1] if l.strip() and not l.startswith('rem')]
    if not block or block[-1].strip().lower() != 'exit /b': err('label :%s does not end with "exit /b"' % lab)
# the main flow must stop before the first label
first = min(labels.values())
pre = [l for l in lines[:first - 1] if l.strip() and not l.startswith('rem')]
if not pre[-1].lower().startswith('exit /b'): err('main flow does not end with exit /b before the first label: %r' % pre[-1])
# parentheses: strip quoted strings, escaped parens, escaped redirections ; running depth must stay >= 0 and end at 0
depth = 0
for n, l in enumerate(lines, 1):
    s = re.sub(r'"[^"]*"', '""', l)
    s = re.sub(r'\^.', '', s)
    if re.match(r'^\s*rem\b', s): continue
    if depth > 0 and re.match(r'^\s*echo\b', s) and re.search(r'[()]', s): err('line %d: raw parenthesis in an echo inside a block (must be ^( ^)): %r' % (n, l))
    for ch in s:
        if ch == '(': depth += 1
        elif ch == ')':
            depth -= 1
            if depth < 0: err('line %d: unbalanced ")"' % n); depth = 0
    # echo lines inside a block must not contain a raw ( or )
if depth != 0: err('unbalanced parentheses at end of file: depth %d' % depth)
# every echo with a ( ) inside an if/for block uses ^( ^) : checked by the depth computation above (raw parens in echo would unbalance)
# messages equal to the old English messages
old = subprocess.run(['git', '-C', '/home/claude/wt-console', 'show', 'HEAD:launch_dq4.bat'], capture_output=True).stdout.decode('ascii').split('\r\n')
def blocks(ls, suffix):
    d = {}; cur = None
    for l in ls:
        m = re.match(r'^:(m_\w+?)(_en|_fr)?\s*$', l)
        if m: cur = (m.group(1), m.group(2) or ''); d[cur] = []; continue
        if cur and l.strip() and not l.startswith('rem'): d[cur].append(l)
        if l.strip() == 'exit /b': cur = None
    return d
ob = blocks(old, '_en'); nb = blocks(lines, '')
for (name, suf), body in ob.items():
    if suf != '_en': continue
    nbody = nb.get((name, ''))
    if nbody is None: err('message %s missing' % name); continue
    exp = [x.replace('save states are in', 'savestates are in') for x in body]
    if nbody != exp: err('message %s differs from the old English one:\n  old=%r\n  new=%r' % (name, exp, nbody))
oldfr = {k[0] for k in ob if k[1] == '_fr'}; newnames = {k[0] for k in nb}
if oldfr != {k[0] for k in ob if k[1] == '_en'} or not oldfr <= newnames: err('fr/en label sets differ')
print('labels: %d, calls: %d, final paren depth: %d' % (len(labels), len(calls), depth))
print('RESULT:', 'OK' if not errors else '%d error(s)' % len(errors))
sys.exit(1 if errors else 0)
