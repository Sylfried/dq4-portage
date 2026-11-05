"""Inventaire des StatusIconChanger dans ui_layout.json : python3 inv_statusicon.py [ui_layout.json]"""
import json, sys
L = json.load(open(sys.argv[1] if len(sys.argv) > 1 else '/tmp/r3_layout/ui_layout.json'))
for k, t in sorted(L['types'].items(), key=lambda x: int(x[0])):
    N = {n['id']: n for n in t.get('nodes', [])}
    cus = [p for p in t.get('params', []) if 'custom' in p and p['custom']['cls'].endswith('StatusIconChanger')]
    if not cus: continue
    print('== type', k, t['name'], ': %d params StatusIconChanger' % len(cus))
    for p in cus[:8]:
        cu = p['custom']; w = cu.get('wrap') or {}
        pt = t['parts'][w['parts']] if w and w.get('parts') is not None and w['parts'] < len(t['parts']) else None
        ib = pt['ib'][w['base']] if pt and w['base'] < len(pt['ib']) else None
        node = N.get(pt['node']) if pt else None
        geo = ''
        if node:
            m = node.get('mesh'); xs = [v[0] for v in m['vtx']] if m else []; ys = [v[1] for v in m['vtx']] if m else []
            geo = 'node %s pos %s mesh x[%s,%s] z[%s,%s] par %s' % (node['id'], node['pos'], min(xs) if xs else None, max(xs) if xs else None, min(ys) if ys else None, max(ys) if ys else None, node['par'])
        print('  (id=%s,no=%s) fields=%s wrap=%s ib=%s %s' % (p['id'], p['no'], cu.get('fields'), w, (ib or {}).get('k'), geo))
        if ib and ib.get('k') == 'icon': print('      icon partsNo', ib.get('partsNo'), 'vtx', ib.get('vtx'), '| mats', [(m.get('sheet'), m.get('part')) for m in (node or {}).get('mats', [])])
