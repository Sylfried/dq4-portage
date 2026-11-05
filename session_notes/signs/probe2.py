"""Probe 2 : carte du monde du chapitre 1 (sauvegarde 4) : table des symboles, panneaux (genre 8), position du heros."""
import os, sys, struct, tempfile, shutil
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
folder = tempfile.mkdtemp(prefix='signs_p2_')
m = ENGINE.Engine(os.environ['DQ_APK'], os.environ['DQ_SAVES'], folder)
c = m.core
for _ in range(3): m.step(0, 0)
m.load_save(int(os.environ.get('SLOT', '4')))
for i in range(100): m.step(0, 0x10 if i % 10 == 0 else 0)
print('part', hex(m.state.part), m.state.game_map)
if m.state.part != ENGINE.PART_FIELD:
    m.start_field()
    for i in range(120): m.step(0, 0)
print('part', hex(m.state.part), 'fielddata', hex(m.fielddata))
fd = m.fielddata
tbl, = struct.unpack('<Q', c.mem(fd + 0x170, 8)); n, = struct.unpack('<i', c.mem(fd + 0x1a0, 4)); nk, = struct.unpack('<i', c.mem(fd + 0x1ec, 4))
print('symboles', n, 'panneaux (kanban) charges', nk)
raw = c.mem(tbl, 10 * n)
import collections
cnt = collections.Counter()
for i in range(n):
    fl, genre, sid, x, y, w, h = struct.unpack_from('<BBhhhBB', raw, 10 * i)
    cnt[genre] += 1
    if genre == 8: print(' kanban? sym', i, 'flag', fl, 'id', sid, 'x', x, 'y', y, 'w', w, 'h', h)
print('genres', dict(cnt))
for i in range(nk):
    kx, ky = struct.unpack('<ii', c.mem(fd + 0x1f4 + 8 * i, 8)); kid, = struct.unpack('<H', c.mem(fd + 0x294 + 2 * i, 2))
    print(' kanban', i, kx, ky, 'id', kid)
print('hero', m.state.sprites.get(0, {}).get('pos'))
shutil.rmtree(folder, ignore_errors=True)
