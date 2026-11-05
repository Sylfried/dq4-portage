"""Balayage des effets de combat par fourche (fork) : le moteur est amene une fois a un combat pret, puis chaque lot de LOT effets tourne dans un fils
(les emplacements fbx ne sont jamais liberes pendant un combat : un lot trop long les epuise et le moteur s'arrete). Chaque effet remplace l'attaque d'arme de Ragnar (argument 303 de setupEffect).
Sortie : JSON {id: {...}} ; arguments : sortie lot id1 id2 ... (ou 'tous')."""
import sys, os, time, json, struct, collections
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
from dq4_pc.core import engine as ENGINE
out_path, LOT = sys.argv[1], int(sys.argv[2])
ids = sorted(int(k) for k in json.load(open('out/effect_params.json')))
want = [int(x) for x in sys.argv[3:]] or ids
t0 = time.time()
eng = bp.boot(); c = eng.core; rec = bp.Rec(eng)
assert bp.natural_battle(eng)
for i in range(120): eng.step(0, 0)
g = c.export('_ZN6status9g_MonsterE')
for (i, num, grp) in bp.monsters(eng): c.mem_w(g + 8 + 0x538 * i + 0x58 + 0x22, struct.pack('<HH', 9999, 9999))
bp.make_strong(eng)
print('pret apres %.0fs, monstres %s' % (time.time() - t0, bp.monsters(eng)), flush=True)

def analyse(chunk, allpk, ov):
    starts = sorted(ov); res = {}
    for n, (f0, k) in enumerate(starts):
        f1 = starts[n + 1][0] - 5 if n + 1 < len(starts) else f0 + 300
        models = collections.Counter(); fbxl = []; sh = []; tint = []; se = []; scr = []; fade = []; slots = {}; col = []; off = 0; n22 = 0
        for f, kp in allpk:
            if not (f0 - 5 <= f < f1): continue
            for t, a, fl in kp:
                if t == 21: models[a[1]] += 1
                elif t == 22: n22 += 1
                elif t == 31: fbxl.append((f - f0, list(a)))
                elif t == 24: sh.append((f - f0, list(a)))
                elif t == 25: col.append((f - f0, fl[:4]))
                elif t == 26: off += 1
                elif t == 33: tint.append((f - f0, fl[:3]))
                elif t == 34: scr.append((f - f0, list(a), fl[:4]))
                elif t == 9: fade.append((f - f0, list(a), fl[:4]))
                elif t == 35: se.append((f - f0, a[0]))
                elif t == 32:
                    s = a[0] & 0xff; d = slots.setdefault(s, dict(n=0, vis=0, flags=set(), f_first=f - f0, f_last=f - f0, pos0=None, scl0=None, col0=None, anim=[]))
                    d['n'] += 1; d['f_last'] = f - f0; d['flags'] |= {a[0] & 0xfffffc00} ; d['vis'] += (a[0] >> 8) & 1
                    if d['pos0'] is None: d['pos0'] = fl[:6]
                    if (a[0] >> 15) & 1 and len(d['anim']) < 4: d['anim'].append(a[1] if len(a) > 1 else None)
        loaded = {s for _, (s, m) in [(x, y) for x, y in fbxl if y[1] >= 0]}
        res[k] = dict(f0=f0, f1=f1, models={str(m): n for m, n in models.items()}, n22=n22, fbx=fbxl, shaders=sh[:4], n_col=len(col), col0=col[:2], n_off=off, tint=[tint[:2], len(tint)], scr=scr[:3], fade=fade[:3], se=se[:10],
                      slots={str(s): dict(d, flags=sorted(d['flags'])) for s, d in slots.items() if s in loaded})
    return res

results = {}
chunks = [want[i:i + LOT] for i in range(0, len(want), LOT)]
for chunk in chunks:
    r, w = os.pipe(); pid = os.fork()
    if pid == 0:
        os.close(r)
        try:
            rec.override = list(chunk); rec.overridden = []
            out, pl = bp.run(eng, frames=2600, stop_when=lambda e: len(rec.overridden) >= len(chunk) and e.frames > rec.overridden[-1][0] + 230)
            res = analyse(chunk, out, rec.overridden); res['_ov'] = rec.overridden; res['_ok'] = True
        except BaseException as ex:
            res = {'_ok': False, '_err': repr(ex)[:300], '_ov': rec.overridden}
        os.write(w, json.dumps(res).encode()); os.close(w); os._exit(0)
    os.close(w); data = b''
    while True:
        b = os.read(r, 1 << 20)
        if not b: break
        data += b
    os.close(r); os.waitpid(pid, 0)
    try: res = json.loads(data)
    except Exception: res = {'_ok': False, '_err': 'fils sans sortie'}
    print('lot', chunk, 'ok' if res.get('_ok') else 'ECHEC %s' % res.get('_err'), 'recus', len([k for k in res if not k.startswith('_')]), '%.0fs' % (time.time() - t0), flush=True)
    for k, v in res.items():
        if not k.startswith('_'): results[k] = v
    json.dump(results, open(out_path, 'w'))
print('fin %.0fs' % (time.time() - t0))
