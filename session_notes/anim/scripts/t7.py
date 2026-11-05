import sys, time, json, struct
sys.path.insert(0, '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/scripts')
import bp
eng = bp.boot(); c = eng.core
gi = c.export('_ZN6status10ExcelParam16getCharaInitDataEv')
base = c.call(gi, label='ci')
print('init table', hex(base))
lv = c.export('_ZN6status10HaveStatus14getLevelupInfoEi')
res = {}
for pid in range(0, 40):
    row = c.mem(base + 0x58 * pid, 0x58)
    t = c.call(lv, pid, label='lv')
    ent = []
    if t:
        for lvl in range(0, 100):
            e = c.mem(t + 0x18 * lvl, 0x18)
            a, b = struct.unpack_from('<HH', e, 0x10)
            if a or b: ent.append((lvl, a, b, e[0x15]))
    res[pid] = dict(row=row.hex(), learn=ent)
    print(pid, row.hex(' ', 4)[:100], ent[:3], len(ent), flush=True)
json.dump(res, open('out/players.json', 'w'))
