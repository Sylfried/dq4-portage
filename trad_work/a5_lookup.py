import re, sys, glob
tsv = {}
for l in open('/home/claude/dq4-portage/docs/rename_identifiers.tsv', encoding='utf-8').read().split('\n')[1:]:
    p = l.split('\t')
    if len(p) == 2: tsv[p[0]] = p[1]
seen = {}
for f in sorted(glob.glob('docs/docs__archives__briefs__common_brief*.in.md')):
    s = open(f, encoding='utf-8').read()
    for m in re.findall(r'`([^`\n]+)`', s):
        for t in re.findall(r'[A-Za-z_][A-Za-z0-9_]*', m):
            if t in tsv and t not in seen:
                seen[t] = tsv[t]
for k, v in sorted(seen.items()): print(k, '->', v)
