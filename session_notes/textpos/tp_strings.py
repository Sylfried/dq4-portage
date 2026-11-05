import json, glob, collections
R = '/tmp/audit_final/interface/res/'
def load_slots():
    S = collections.defaultdict(set)
    for fn in ['terrain_slot1.json', 'terrain_slot4.json', 'combat_slot1.json', 'combat_slot4.json'] + [g.split('res/')[1] for g in glob.glob(R + 'v1/*.json')]:
        try: d = json.load(open(R + fn))
        except Exception: continue
        if isinstance(d, dict) and isinstance(d.get('slots'), dict):
            for k, v in d['slots'].items():
                for s in v: S[k].add(s)
    return S
