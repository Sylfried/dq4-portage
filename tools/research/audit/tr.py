import json, sys
p='/root/.claude/projects/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/subagents/agent-ad9be5b9dfd5bdfb2.jsonl'
rows=[]
for l in open(p):
    try: o=json.loads(l)
    except Exception: continue
    rows.append(o)
def txt(c):
    if isinstance(c,str): return c
    out=[]
    for b in c:
        if b.get('type')=='text': out.append(b['text'])
        elif b.get('type')=='tool_result':
            cc=b.get('content')
            out.append(txt(cc) if not isinstance(cc,str) else cc)
        elif b.get('type')=='tool_use': out.append('TOOL_USE '+json.dumps(b['input'])[:600])
    return '\n'.join(out)
for a in sys.argv[1:]:
    i=int(a.split(':')[0]); n=int(a.split(':')[1]) if ':' in a else 3000
    print('#####', i); print(txt(rows[i]['message']['content'])[:n])
