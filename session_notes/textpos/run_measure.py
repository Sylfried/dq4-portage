import sys, collections, json, time
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/textpos')
from tp_lib import *
from tp_strings import load_slots
OUT = '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/textpos/mesures.json'
S = load_slots()
pools = json.load(open('/tmp/audit_final/interface/res/pools.json'))
POOL2 = [v for k, v in pools['2'].items() if int(k) <= 173]
POOL2_LONG = POOL2
bm = RENDERS[False].texts.bitmap
Hg = bm.G[ord('H')]; CAPH = -Hg[2] - Hg[3].shape[0] * 0 ; CAPH = -Hg[2]       # hauteur de la majuscule au-dessus de la ligne de base (px de police)
DESC_KEYS = set(UM.DESCRIPTIONS)
GROUPS = {13: 13, 14: 13, 15: 13, 16: 13, 17: 13, 35: 35, 36: 35, 37: 35, 58: 58, 59: 58, 60: 60, 61: 60, 33: 33, 39: 33, 40: 33}
PROBE = 'Abcdefgh'
rows = []
t0 = time.time()
for t in sorted(ml.types, key=int):
    ty = int(t); T = ml.types[t]
    cells = text_cells(ty)
    if not cells: continue
    # sondes : cellule de cout (tabSize) -> chaine type
    for (i, no, nid, var) in cells:
        w0 = UM.Window(ml, ty); node0 = w0.N[nid]; tx = node0['text']
        ctn = container(w0, node0)
        row = dict(typ=ty, name=T.get('name', '').replace('Make_', '').replace('()', ''), id=i, no=no, node=nid, variant=var, pos=node0['pos'], anchor=tx['anchor'], align=tx['alignment'],
                   ls=tx['lineSpacing'], cs=tx['characterSize'], tab=tx.get('tabSize'), container=ctn, act0=node0['act'])
        probe = PROBE if not tx.get('tabSize') else 'Abc:\tDe'
        res = {}
        for m in MODES:
            r = measure(ty, i, no, probe, m)
            res[m] = r and {k: v for k, v in r.items() if k not in ('quads', 'text', 'node')}
        row['probe'] = res
        # chaines reelles
        key = '%d/%d/%d' % (ty, i, no); strs = sorted(S.get(key, [])); src = 'observe'
        if not strs:
            sib = set()
            for (t2, n2) in ((g, 0) for g in [k for k, v in GROUPS.items() if v == GROUPS.get(ty, ty)] or [ty]):
                for kk, vv in S.items():
                    a, b, c = kk.split('/')
                    if int(a) == t2 and int(c) == no and (int(b) == i or True): sib |= set(vv)
            strs = sorted(sib); src = 'frere'
        if (ty, i, no) in DESC_KEYS:
            extra = set(POOL2_LONG)
            if (ty, i, no) == (38, 2, 3): extra = set(x.rstrip('\n') for x in extra)   # les chaines reelles de cette cellule n'ont pas de \n final
            strs = sorted(set(strs) | extra); src = src + '+pool2'
        row['src'] = src if strs else 'aucune'
        out = []
        for s in strs[:200]:
            e = {'s': s}
            for m in ('P', 'V', 'O'):
                r = measure(ty, i, no, s, m)
                e[m] = r and {k: v for k, v in r.items() if k not in ('quads', 'node')}
                if m == 'V' and r:
                    e['V_quads'] = [(q['text'], round(q['x'], 2), round(q['base'], 2), round(q['ts'], 3)) for q in r['quads']]
            out.append(e)
        row['real'] = out
        rows.append(row)
    print('type', ty, len(cells), 'cells', round(time.time() - t0, 1), 's', flush=True)
json.dump(dict(rows=rows, CAPH=CAPH, DY=DY, leading=bm.leading, ascent=bm.ascent), open(OUT, 'w'), default=float)
print('done', len(rows))
