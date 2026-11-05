import sys, time, json, struct
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
eng = bp.boot(); rec = bp.Rec(eng); c = eng.core
print('natural', bp.natural_battle(eng), flush=True)
for i in range(30): eng.step(0, 0)
S = c.export('_ZN19BattleEffectManager11m_singletonE')
print('singleton', hex(S), 'table ptr', hex(struct.unpack('<Q', c.mem(S, 8))[0]))
gp = c.export('_ZN19BattleEffectManager14getEffectParamEi')
tab = {}
for k in range(0, 1100):
    r = c.call(gp, S, k, label='gp')
    if r: tab[k] = c.mem(r, 0x14).hex()
print(len(tab), 'effets avec parametres')
json.dump(tab, open('out/effect_params.json', 'w'))
print(sorted(tab)[:200])
