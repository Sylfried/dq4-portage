"""Assemble les donnees (table des actions, noms, balayages) en tableaux pour couverture.md. Sortie : out/tables.json + texte Markdown sur la sortie standard."""
import json, struct, os, collections
R = '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/out/'
rows = json.load(open(R + 'actions_raw.json'))['rows']
names = {int(k): v for k, v in json.load(open(R + 'action_names.json')).items()}
players = json.load(open(R + 'players.json'))
sw = json.load(open(R + 'sweep_all.json'))
forced = {}
for f in ('forced_b.json', 'forced_c.json'):
    if os.path.exists(R + f): forced.update(json.load(open(R + f)))
items = json.load(open(R + 'items_use.json'))
COMMON_SE = {400, 401, 402, 403, 404, 712}
def eff_of(a): return struct.unpack('<H', bytes.fromhex(rows[a])[0x26:0x28])[0]
def res_of(k):
    v = sw.get(str(k))
    if v is None: return None
    mods = sorted(int(m) for m in v['models'] if m != '-1'); fb = sorted({x[1][1] for x in v['fbx'] if x[1][1] >= 0})
    se = sorted({s for _, s in v['se']} - COMMON_SE - {0})
    return dict(mod=mods, fbx=fb, tint=v['tint'][1], se=se)
def status(k):
    if k == 0: return 'OK (aucun effet demandé)'
    r = res_of(k)
    if r is None: return 'inconnu'
    if r['fbx'] and r['mod']: return 'partiel (maillage dessiné, fbx c%s non dessiné)' % ','.join(map(str, r['fbx']))
    if r['fbx']: return ('ABSENT (fbx c%s seul' % ','.join(map(str, r['fbx']))) + (', teinte plein écran seule dessinée)' if r['tint'] else ', rien d\'autre que le son)')
    if r['mod']: return 'OK (maillage m%s)' % ','.join(map(str, r['mod']))
    return 'rien (teinte / son)'
learn = collections.defaultdict(set)
for pid, v in players.items():
    for l in v['learn']:
        for a in (l[1], l[2]):
            if a: learn[a].add(int(pid))
out = []
for a in sorted(set(int(k) for k in forced) | set(learn)):
    f = forced.get(str(a)); eff = eff_of(a); real = None
    if f:
        es = [e for _, e in f['effects']]
        real = es[0] if es else None
    out.append(dict(action=a, name=names.get(a, ''), pids=sorted(learn.get(a, [])), eff_table=eff, eff_real=real, res=res_of(eff) if eff else None, status=status(eff), forced=bool(f),
                    cast=(f or {}).get('texts', [])[:1], alltexts=(f or {}).get('alltexts', [])[:12], se=(res_of(eff) or {}).get('se') if eff else None,
                    se_forced=sorted({s for _, s in (f or {}).get('se', [])} - COMMON_SE - {0}), fbx_forced=[x[1] for x in (f or {}).get('fbx', [])]))
json.dump(out, open(R + 'tables.json', 'w'), ensure_ascii=False)
for o in out:
    print(o['action'], o['name'], 'pids', o['pids'], 'eff', o['eff_table'], 'reel', o['eff_real'], o['status'], 'SE', o['se_forced'])
