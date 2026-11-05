#!/bin/bash
# usage: ouvrir_empile.sh <worktree> <branche> <branche de base (la precedente de la pile)> <titre PR sans (#N)> <fichier corps PR> <num attendu>
WT="$1"; BR="$2"; BASE="$3"; TITRE="$4"; CORPS="$5"; ATT="$6"
SP=/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad
cd "$WT" || exit 1
git reset -q --soft "$BASE" || exit 1
git add -A
git commit -q -m "$TITRE

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014GF7TWaZ7HKpoCu5KRp2TJ" || exit 1
for i in 1 2 3 4 5 6; do git push -q --force-with-lease="$BR:$(git ls-remote origin "$BR" | cut -f1)" -u origin "$BR" >/dev/null 2>&1; git ls-remote origin "$BR" | grep -q "$(git rev-parse HEAD)" && break; echo "push: reprise $i"; sleep 20; done
N=""
for i in 1 2 3 4 5 6; do OUT=$(python3 $SP/ouvrir_pr.py "$BR" "$TITRE" "$CORPS" 2>&1); echo "$OUT" | tail -1; if echo "$OUT" | grep -q "^[0-9]"; then N=$(echo "$OUT" | cut -d' ' -f1); break; fi; N2=$(gh api "repos/Sylfried/dq4-portage/pulls?head=Sylfried:$BR&state=all" --jq '.[0].number' 2>/dev/null); [ -n "$N2" ] && [ "$N2" != "null" ] && { N=$N2; break; }; sleep 15; done
[ -n "$N" ] || { echo "PR NON OUVERTE"; exit 1; }
[ "$N" = "$ATT" ] || echo "ATTENTION: numero PR $N different de $ATT attendu (docs a corriger)"
echo "PR=$N"
