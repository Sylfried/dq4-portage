"""Pour des effets donnes : nombre d'images ou un maillage d'effet (modele >= 5000) est reellement envoye (paquet 22, meshes_seen) et nombre de sommets."""
import sys, os, json, struct, time
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
ids = [int(x) for x in sys.argv[2:]]
eng = bp.boot(); c = eng.core; rec = bp.Rec(eng)
assert bp.natural_battle(eng)
for i in range(120): eng.step(0, 0)
g = c.export('_ZN6status9g_MonsterE')
for (i, num, grp) in bp.monsters(eng): c.mem_w(g + 8 + 0x538 * i + 0x58 + 0x22, struct.pack('<HH', 9999, 9999))
bp.make_strong(eng)
res = {}
for k in ids:
    r, w = os.pipe(); pid = os.fork()
    if pid == 0:
        os.close(r)
        try:
            rec.override = [k]; rec.overridden = []
            st = eng.state; seen = []; models = set()
            def log(e, pkt):
                for sl in st.meshes_seen:
                    m = st.models.get(sl) or 0
                    if m >= 5000 and m != 5303:
                        mm = st.meshes.get(sl); seen.append((e.frames, m, len(mm['v']) // 5 if mm else -1, st.mesh_state.get(sl, {}).get('vis'), st.mesh_state.get(sl, {}).get('shader')))
            bp.run(eng, frames=900, log=log, stop_when=lambda e: len(rec.overridden) >= 1 and e.frames > rec.overridden[-1][0] + 200)
            out = dict(ov=rec.overridden, n=len(seen), first=seen[:2], last=seen[-1:], nvmax=max([s[2] for s in seen] or [0]))
        except BaseException as ex: out = dict(err=repr(ex)[:200])
        os.write(w, json.dumps(out).encode()); os.close(w); os._exit(0)
    os.close(w); data = b''
    while True:
        b = os.read(r, 65536)
        if not b: break
        data += b
    os.waitpid(pid, 0); res[k] = json.loads(data.decode() or '{}'); print(k, res[k], flush=True)
json.dump(res, open(sys.argv[1], 'w'))
