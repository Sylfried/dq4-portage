import re, sys
P = '/home/claude/wt-console/launch_dq4.bat'
b = open(P, 'rb').read()
assert b.endswith(b'\r\n') and b.count(b'\r\n') == b.count(b'\n') == b.count(b'\r')
lines = b.split(b'\r\n')[:-1]
# 1. language detection block (rem --- 0 ... DQLANG detection) : lines 5..12 (1-based) -> remove, keep line 4 blank
assert lines[4].startswith(b'rem --- 0. langue'), lines[4]
assert lines[5].startswith(b'rem     chaque message'), lines[5]
assert lines[6] == b'set "LOC="' and lines[10].startswith(b'if defined LOC if /i') and lines[11] == b''
del lines[4:12]
# 2. drop the _fr blocks, rename _en labels
out = []; i = 0
while i < len(lines):
    l = lines[i]
    m = re.match(rb'^:(m_\w+)_fr$', l)
    if m:
        j = i + 1
        while lines[j] != b'exit /b': j += 1
        i = j + 1; continue
    m = re.match(rb'^:(m_\w+)_en$', l)
    if m: out.append(b':' + m.group(1)); i += 1; continue
    out.append(l); i += 1
lines = out
# 3. calls
lines = [l.replace(b'_%DQLANG%', b'') for l in lines]
s = b'\r\n'.join(lines) + b'\r\n'
# 4. vocabulary: "save states" -> "savestates" in the intro
assert s.count(b'save states are in') == 1
s = s.replace(b'save states are in', b'savestates are in')
assert b'DQLANG' not in s and b'LOC' not in s and b'_fr' not in s and b'_en' not in s
open(P, 'wb').write(s)
print('ok', len(s))
