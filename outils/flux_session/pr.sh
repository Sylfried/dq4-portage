#!/bin/bash
# usage: pr.sh "titre sans prefixe" corps.md   (branche courante ; pousse, cree la PR, fusionne en squash, revient sur main)
set -e
cd /home/claude/dq4-portage
br=$(git branch --show-current)
git push -q -u origin "$br" 2>&1 | tail -2
n=$(gh api "repos/Sylfried/dq4-portage/pulls?state=all&per_page=100" --jq 'length')
num=$((n+1))
python3 - "$1" "$2" "$br" "$num" <<'PY'
import json,sys
t,corps,br,num=sys.argv[1:5]
body=open(corps,encoding='utf-8').read().rstrip()+"\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nhttps://claude.ai/code/session_014GF7TUJhoy5Df7FLvSTYtw\n"
json.dump({"title":"Avance #%s : %s"%(num,t),"head":br,"base":"main","body":body},open('/tmp/pr.json','w'))
PY
res=$(gh api repos/Sylfried/dq4-portage/pulls --input /tmp/pr.json --jq '.number')
echo "PR $res"
gh api -X PUT repos/Sylfried/dq4-portage/pulls/$res/merge -f merge_method=squash --jq '.merged'
git checkout -q main && git pull -q origin main && git log --oneline | head -2
