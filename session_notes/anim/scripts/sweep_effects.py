"""Balayage des effets par le vrai chemin du moteur : l'attaque d'arme de Ragnar demande l'effet 303 (BattleEffectManager::setupEffect) ; on remplace
l'argument par chaque numero d'effet (comme le balayage de l'audit du 05/11), setPlayerEffect pose ensuite la cible comme pour un vrai sort.
Pour chaque effet : modeles (paquet 21), fbx (31 / 32), shaders (24), couleurs (25), decalage de texture (26), teinte (33), bruitages (35), images avec maillage dynamique (22).
Sortie : JSON (argument 3)."""
import sys, time, json, struct, collections
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
from dq4_pc.core import engine as ENGINE
ids = json.load(open('out/effect_params.json')); ids = sorted(int(k) for k in ids)
lo, hi = int(sys.argv[1]), int(sys.argv[2]); ids = [k for k in ids if lo <= k < hi]
t0 = time.time()
eng = bp.boot(); c = eng.core; rec = bp.Rec(eng)
res = {}
def monsters_strong():
    g = c.export('_ZN6status9g_MonsterE')
    for (i, num, grp) in bp.monsters(eng):
        base = g + 8 + 0x538 * i; c.mem_w(base + 0x58 + 0x22, struct.pack('<HH', 9999, 9999))
pending = list(ids); rec.override = list(ids)
allpk = []
while pending:
    if eng.state.part != ENGINE.PART_BATTLE:
        if not bp.natural_battle(eng): print('pas de combat'); break
        for i in range(120): eng.step(0, 0)
        monsters_strong()
    try:
        out, pl = bp.run(eng, frames=4000, stop_when=lambda e: len(rec.overridden) >= len(ids))
    except RuntimeError as ex:
        print('ARRET DU MOTEUR apres', rec.overridden[-3:], str(ex)[:400]); break
    # run s'arrete a la fin du combat ou quand tous les effets ont ete lances
    allpk += out
    done = {k for f, k in rec.overridden}
    pending = [k for k in pending if k not in done]
    if len(rec.overridden) >= len(ids): break
    print('combat fini, restent', len(pending), flush=True)
    rec.override = list(pending)
    for i in range(60): eng.step(0, 0)
# attribution des paquets : fenetre [image d'appel, image du suivant ou +220[
ov = sorted(rec.overridden); starts = [f for f, k in ov] + [10 ** 9]
by = {}
for (f0, k), nxt in zip(ov, starts[1:]):
    by[k] = (f0, min(nxt, f0 + 220))
for k, (f0, f1) in by.items():
    models = collections.Counter(); fbx = []; fbxpk = []; sh = []; col = []; off = 0; tint = []; se = []; meshf = 0
    for f, kp in allpk:
        if not (f0 <= f < f1): continue
        for t, a, fl in kp:
            if t == 21: models[a[1]] += 1
            elif t == 31: fbx.append((f - f0, list(a)))
            elif t == 32: fbxpk.append((f - f0, list(a), fl))
            elif t == 24: sh.append((f - f0, list(a)))
            elif t == 25: col.append((f - f0, fl[:3]))
            elif t == 26: off += 1
            elif t == 33: tint.append((f - f0, fl[:3]))
            elif t == 35: se.append((f - f0, a[0]))
    res[k] = dict(f0=f0, models={str(m): n for m, n in models.items()}, fbx=fbx, fbx32=fbxpk[:10], n32=len(fbxpk), shaders=sh[:6], colors=col[:3], n_col=len(col), n_off=off, n_tint=len(tint), tint0=tint[:2], se=se[:8])
json.dump(res, open(sys.argv[3], 'w'))
for k in sorted(res):
    r = res[k]; print(k, 'modeles', r['models'], 'fbx', [x[1] for x in r['fbx']], 'tint', r['n_tint'], 'se', [s for _, s in r['se']][:3])
print('fin %.0fs' % (time.time() - t0))
