import json, sys
rep = json.load(open('report.json'))
sel = sys.argv[1:]
seen = set()
for rel, ln, kind, v in rep['unresolved']:
    if not any(rel.startswith(s) for s in sel): continue
    if (rel, ln) in seen: continue
    seen.add((rel, ln))
    src = open('/home/claude/wt-console/' + rel, encoding='utf-8').read().splitlines()
    print('%s:%d: %s' % (rel, ln, src[ln-1].strip()[:400]))
