import sys, json; sys.path.insert(0,'/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/textpos')
from tp_lib import *
raw = json.load(open(C + '/ui_layout.json'))
# --- messages
rm = raw['message']['types']; mm = ml.message['types']
print('message : types brut', len(rm), 'apres', len(mm))
def box(t):
    fv = t['frame_mesh']['vtx']; cv = t['canvas']['vtx']
    return dict(win=t['win'], scale=t.get('scale'), frame=(round(min(v[0] for v in fv),1), round(max(v[0] for v in fv),1), round(min(v[1] for v in fv),1), round(max(v[1] for v in fv),1)),
                canvas=(round(min(v[0] for v in cv),1), round(max(v[0] for v in cv),1), round(min(v[2] for v in cv),1), round(max(v[2] for v in cv),1)), feed=t['feed_local'])
for i in range(4):
    print(i, 'brut ', box(rm[i])); print(i, 'visio', box(mm[i]))
print('type 4 (cadre combat 4 lignes) :', box(mm[4]) if len(mm) > 4 else None)
# --- Oui / Non
for ty in (1,):
    raw_nodes = {n['id']: n for n in raw['types'][str(ty)]['nodes']}
    w = UM.Window(ml, ty)
    for nid, n in w.N.items():
        r = raw_nodes[nid]
        if n['text'] is not None or n['vtx']:
            d = (round(n['pos'][0]-r['pos'][0],1), round(n['pos'][2]-r['pos'][2],1))
            print('YesNo node', nid, 'text' if n['text'] is not None else 'mesh', 'delta (dx,dz)', d, 'raw pos', r['pos'])
# --- type 54 titre
raw_nodes = {n['id']: n for n in raw['types']['54']['nodes']}
for c in (0, 1, 2):
    w = UM.Window(ml, 54); w._start(c)
    for nid, n in w.N.items():
        r = raw_nodes[nid]
        if n['text'] is not None:
            print('type54 code', c, 'node', nid, 'texte delta', (round(n['pos'][0]-r['pos'][0],1), round(n['pos'][2]-r['pos'][2],1)), 'anchor', n['text']['anchor'])
        elif n['buttonId'] is not None and n['mats'] and n['mats'][0].get('part') == 7 and c != 0:
            print('   bouton', nid, 'delta', (round(n['pos'][0]-r['pos'][0],1), round(n['pos'][2]-r['pos'][2],1)))
# --- type 53
raw_nodes = {n['id']: n for n in raw['types']['53']['nodes']}
w = UM.Window(ml, 53); dz = w.center_menu(); print('type 53 center_menu dz', dz)
# --- type 12
w = UM.Window(ml, 12)
for nid, n in w.N.items():
    print('type12', nid, n['pos'], 'vtx' if n['vtx'] else '', 'text' if n['text'] is not None else '')
