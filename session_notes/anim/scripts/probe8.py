"""Objets utilisables en combat : status::UseItem::isBattleUse / getBattleUseAction / getUseType pour chaque numero d'objet."""
import sys, os, struct, tempfile, json
os.environ.update(PYGLET_HEADLESS='1', PYGLET_AUDIO='silent', PYTHONDONTWRITEBYTECODE='1')
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735'
eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_anim_'))
c = eng.core
f = {n: eng.E('_ZN6status7UseItem%d%sEi' % (len(n), n)) for n in ('isBattleUse', 'getBattleUseAction', 'getUseType', 'getUseAction', 'getItemType', 'getUseArea')}
res = {}
for i in range(0, 520):
    r = {n: c.call(a, i, label=n) for n, a in f.items()}
    res[i] = {n: (-1 if v is None else v & 0xffffffff) for n, v in r.items()}
json.dump(res, open('out/items_use.json', 'w'))
print(sum(1 for v in res.values() if v['isBattleUse'] & 0xff), 'objets utilisables en combat')
