"""Vrai moteur : ouvre le menu Magie de Doc (emplacement 1) et sort l'etat exact de la fenetre type 8 (chaines, codes)."""
import os, sys, json
sys.path.insert(0, '/home/claude/dq4-portage'); sys.path.insert(0, '/home/claude/dq4-portage/tests')
import test_magic_entries as T
t = T.RealEngine('test_doc_entries')
eng = t.ready(); t.open_list(eng)
out = {}
for port in sorted(eng.ui.f):
    f = eng.ui.f[port]
    out[port] = {'type': f.get('type'), 'cases': {'%s,%s' % k: v for k, v in (f.get('cases') or {}).items()}, 'indic': {str(k): v for k, v in (f.get('indic') or {}).items()},
                 'ints': {'%s,%s' % k: v for k, v in (f.get('ints') or {}).items()}, 'dispo': f.get('dispo'), 'cur': f.get('cur')}
json.dump(out, open(sys.argv[1], 'w'), ensure_ascii=True, indent=1)
f = eng.ui.f[8]
for k, v in sorted(f['cases'].items()): print(k, repr(v), [hex(ord(c)) for c in v if ord(c) < 32 or ord(c) > 126])
print('indic', f['indic'], 'type', f['type'])
