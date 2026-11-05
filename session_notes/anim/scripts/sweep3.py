"""Actions alliees forcees dans un vrai combat (BattleSelectTarget::setActorAction : on remplace l'action choisie par la suivante de la file), par fourche, LOT actions par fils.
Pour chaque action : execution (BattleActorExec::setup), effets demandes a setupEffect (dans la fenetre de l'action), paquets : modeles 21, fbx 31, teinte 33, bruitages 35, ecran 34.
arguments : sortie lot id1 id2 ..."""
import sys, os, time, json, struct, collections
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp, unicorn
out_path, LOT = sys.argv[1], int(sys.argv[2])
want = [int(x) for x in sys.argv[3:]]
t0 = time.time()
eng = bp.boot(); c = eng.core; rec = bp.Rec(eng)
texts = []; rets = set()
def ret_hook(uc, adr, sz, ud):
    p = uc.reg_read(c.XREG[0]) & 0xffffffffffff
    try: raw = c.mem(p, 0x200); n = raw.find(b'\0'); texts.append((eng.frames, raw[:n].decode('utf-8', 'replace')))
    except Exception: pass
def enter(uc, adr, sz, ud):
    lr = uc.reg_read(c.XREG[30]) & 0xffffffffffff
    if lr not in rets: rets.add(lr); uc.hook_add(unicorn.UC_HOOK_CODE, ret_hook, None, lr, lr); uc.ctl_flush_tb()
ma = c.export('_Z26macro_processMessage_allocPKc'); c.uc.hook_add(unicorn.UC_HOOK_CODE, enter, None, ma, ma); c.uc.ctl_flush_tb()
assert bp.natural_battle(eng)
for i in range(120): eng.step(0, 0)
g = c.export('_ZN6status9g_MonsterE')
for (i, num, grp) in bp.monsters(eng): c.mem_w(g + 8 + 0x538 * i + 0x58 + 0x22, struct.pack('<HH', 9999, 9999))
bp.make_strong(eng, hp=999, mp=999)
print('pret apres %.0fs' % (time.time() - t0), flush=True)

def analyse(chunk, allpk, fo):
    res = {}
    # fenetre d'une action = [image ou l'action est posee, image suivante ou +400[ ; execs = lancements de BattleActorExec::setup dans la fenetre (action reelle lue dans +0x1d8 du UseActionParam)
    seq = [(f, pl, new) for f, pl, old, new in fo.done]
    for n, (f0, actor, act) in enumerate(seq):
        f1 = seq[n + 1][0] if n + 1 < len(seq) else f0 + 400
        execs = [(f - f0, hex(a), x) for f, a, x in rec.execs if f0 - 3 <= f < f1]; txt = [(f - f0, t) for f, t in texts if f0 - 3 <= f < f1 and any(w in t for w in ('sort', 'lance', 'utilise', 'attaque', 'invoque', 'Mais', 'rien', 'conc', 'entonne', 'pousse', 'ressuscit', 'efficace'))][:6]
        effs = [(f - f0, k) for f, k in rec.effects if f0 - 3 <= f < f1]
        models = collections.Counter(); fbxl = []; tint = []; se = []; scr = []; fade = []; sh = []
        for f, kp in allpk:
            if not (f0 - 3 <= f < f1): continue
            for t, a, fl in kp:
                if t == 21: models[a[1]] += 1
                elif t == 31: fbxl.append((f - f0, list(a)))
                elif t == 33: tint.append((f - f0, fl[:3]))
                elif t == 34: scr.append((f - f0, list(a)))
                elif t == 9: fade.append((f - f0, list(a)))
                elif t == 35: se.append((f - f0, a[0]))
                elif t == 24: sh.append(tuple(a))
        res[str(act)] = dict(f0=f0, actor=actor, execs=execs, texts=txt, alltexts=[t for f, t in texts if f0 - 3 <= f < f1][:24], effects=effs, models={str(m): n for m, n in models.items() if m != -1}, fbx=fbxl, tint=len(tint), scr=scr[:3], fade=len(fade), se=se[:12], shaders=sorted(set(sh)))
    return res

results = {}
for i in range(0, len(want), LOT):
    chunk = want[i:i + LOT]
    r, w = os.pipe(); pid = os.fork()
    if pid == 0:
        os.close(r)
        try:
            n_e = len(rec.execs); n_f = len(rec.effects)
            fo = bp.Forcer(eng, chunk); bp.make_strong(eng, 999, 999)
            out, pl = bp.run(eng, frames=2600, stop_when=lambda e: len(fo.done) >= len(chunk) and len(rec.execs) > n_e and e.frames > rec.execs[-1][0] + 260)
            res = analyse(chunk, out, fo); res['_forced'] = fo.done; res['_ok'] = True
        except BaseException as ex:
            res = {'_ok': False, '_err': repr(ex)[:300]}
        os.write(w, json.dumps(res).encode()); os.close(w); os._exit(0)
    os.close(w); data = b''
    while True:
        b = os.read(r, 1 << 20)
        if not b: break
        data += b
    os.close(r); os.waitpid(pid, 0)
    try: res = json.loads(data)
    except Exception: res = {'_ok': False, '_err': 'fils sans sortie'}
    print('lot', chunk, 'ok' if res.get('_ok') else 'ECHEC %s' % res.get('_err'), 'forces', res.get('_forced'), '%.0fs' % (time.time() - t0), flush=True)
    for k, v in res.items():
        if not k.startswith('_'): results[k] = v
    json.dump(results, open(out_path, 'w'))
print('fin %.0fs' % (time.time() - t0))
