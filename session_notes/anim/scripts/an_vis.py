import json, sys, collections, ast
res = collections.defaultdict(lambda: dict(n=0, seen=0, fill=0.0, boxpx=0, fbx=set(), models=set(), seen_frames=[]))
for l in open(sys.argv[1]):
    d = json.loads(l)
    if d.get('kind') != 'shot': continue
    k = int(d['label'][1:]); r = res[k]; r['n'] += 1
    mod = {int(s): m for s, m in d['models'].items()}
    sl = d['slots']
    if isinstance(sl, str):
        try: sl = ast.literal_eval(sl)
        except Exception: sl = {}
    for s, st in sl.items():
        if st.get('model') == 5000 + k:
            r['models'].add(st['model']); r['seen'] += 1; r['seen_frames'].append(d['n'])
            r['fill'] = max(r['fill'], st.get('fill', 0.0) or 0.0); r['boxpx'] = max(r['boxpx'], st.get('diff_in_box', 0) or 0)
    r['fbx'] |= set(d['fbx'].values())
import json as _j
_out = {k: dict(shots=r["n"], seen=r["seen"], frames=r["seen_frames"], fill=r["fill"], px=r["boxpx"], fbx=sorted(r["fbx"])) for k, r in res.items()}
_j.dump(_out, open(sys.argv[2], "w")) if len(sys.argv) > 2 else None
for k in sorted(res):
    r = res[k]; print(k, 'shots', r['n'], 'vus', r['seen'], 'frames', r['seen_frames'][:6], 'fill max %.3f' % r['fill'], 'px', r['boxpx'], 'fbx', sorted(r['fbx']))
