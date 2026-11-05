"""Noms des personnages : chaines pointees par les premiers mots des lignes de la table des joueurs (players.json)."""
import sys, os, struct, tempfile, json
os.environ.update(PYGLET_HEADLESS='1', PYGLET_AUDIO='silent', PYTHONDONTWRITEBYTECODE='1')
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/claude/dq4-portage')
from dq4_pc.core import engine as ENGINE
APK = '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks'
SAVES = '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735'
eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_anim_'))
c = eng.core
P = json.load(open('out/players.json')); res = {}
for k, v in P.items():
    b = bytes.fromhex(v['row']); ptrs = struct.unpack('<%dQ' % (len(b) // 8), b[:len(b) // 8 * 8])
    s = []
    for p in ptrs[:12]:
        if 0x10000000 <= p < 0x20000000:
            try:
                raw = c.mem(p, 0x30); n = raw.find(b'\0'); s.append(raw[:n].decode('utf-8', 'replace') if n > 0 else '')
            except Exception: s.append(None)
        else: s.append(p)
    res[k] = s
json.dump(res, open('out/players_names.json', 'w'), ensure_ascii=False)
for k, s in res.items(): print(k, s[:8])
