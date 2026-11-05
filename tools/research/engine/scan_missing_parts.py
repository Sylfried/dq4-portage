"""Types dont la table de parametres (id,no)->parts reference des parts absents de l'export : python3 scan_missing_parts.py [ui_layout.json]"""
import json, sys
L = json.load(open(sys.argv[1] if len(sys.argv) > 1 else '/tmp/r3_layout/ui_layout.json'))
for k, t in sorted(L['types'].items(), key=lambda x: int(x[0])):
    if 'parts' not in t: print(k, t['name'], 'ERREUR', t.get('err')); continue
    n = len(t['parts']); missing = sorted({p['parts'] for p in t['params'] if p.get('parts') is not None and p['parts'] >= n})
    codes_fn = [c for c in t['codes'] if c['kind'] == 'func']
    if missing: print(k, t['name'], 'parts exportes', n, 'references manquantes', len(missing), '(%d..%d)' % (missing[0], missing[-1]), 'codes func', [(c['id'], c['method'].split('.')[-1]) for c in codes_fn])
