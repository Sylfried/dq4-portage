#!/bin/bash
# usage: merge_pile.sh <n° PR> <n° PR precedent (0 si aucun)> <worktree> <branche> <ancienne tete (sha) de la branche precedente, a retirer> <fichier commentaire ou -> <n° issue ou ->
# Pile de PR : la precedente est fusionnee en « squash » (autre sha) : on rebase cette branche sur main en retirant les commits de la precedente ; si l'arbre obtenu est identique a celui de la CI verte, fusion sans nouvelle CI.
N="$1"; APRES="$2"; WT="$3"; BR="$4"; OLDBASE="$5"; COM="$6"; ISS="$7"
R=Sylfried/dq4-portage
if [ "$APRES" != "0" ]; then
  for i in $(seq 1 540); do
    S=$(gh api repos/$R/pulls/$APRES --jq '"\(.merged) \(.state)"' 2>/dev/null)
    case "$S" in "true "*) break;; "false closed") echo "PR $APRES fermee sans fusion : arret"; exit 1;; esac
    sleep 20
  done
  echo "PR $APRES fusionnee"
fi
SHA0=$(git -C /home/claude/dq4-portage ls-remote origin "$BR" | cut -f1)       # (tete reelle de la branche : l'API des PR peut rendre l'ancienne juste apres un push force)
for i in $(seq 1 540); do CI=$(gh api repos/$R/commits/$SHA0/check-runs --jq '.check_runs[]|"\(.name):\(.status):\(.conclusion)"' 2>/dev/null); echo "$CI" | grep -q "completed" && break; sleep 20; done
echo "CI (tete empilee $SHA0): $CI"
echo "$CI" | grep -q "completed:success" || { echo "CI PAS VERTE, pas de fusion"; exit 1; }
cd "$WT" || exit 1
git fetch -q origin main
TREE0=$(git rev-parse "$SHA0^{tree}")
if [ "$APRES" != "0" ]; then
  git rebase --onto origin/main "$OLDBASE" "$BR" 2>&1 | tail -2
  git status | grep -q "rebase in progress" && { git rebase --abort; echo "CONFLIT au rebase : arret"; exit 1; }
  TREE1=$(git rev-parse HEAD^{tree})
  git push -q --force-with-lease="$BR:$SHA0" origin "$BR" 2>&1 | tail -2
  NEW=$(git rev-parse HEAD); git ls-remote origin "$BR" | grep -q "$NEW" || { echo "push refuse"; exit 1; }
  if [ "$TREE0" != "$TREE1" ]; then
    echo "arbre different de celui de la CI verte : attente d'une nouvelle CI"
    for i in $(seq 1 540); do CI=$(gh api repos/$R/commits/$NEW/check-runs --jq '.check_runs[]|"\(.name):\(.status):\(.conclusion)"' 2>/dev/null); echo "$CI" | grep -q "completed" && break; sleep 20; done
    echo "$CI" | grep -q "completed:success" || { echo "CI PAS VERTE (apres rebase), pas de fusion"; exit 1; }
  else echo "arbre identique a celui de la CI verte : fusion sans nouvelle CI"; fi
  sleep 3
fi
TITRE=$(gh api repos/$R/pulls/$N --jq '.title')
for i in 1 2 3 4 5 6; do M=$(gh api repos/$R/pulls/$N --jq '.merged' 2>/dev/null); [ "$M" = "true" ] && break; gh api -X PUT repos/$R/pulls/$N/merge -f merge_method=squash -f commit_title="$TITRE (#$N)" --jq '.merged' 2>&1 | tail -1; sleep 12; done
M=$(gh api repos/$R/pulls/$N --jq '.merged'); echo "merged=$M"; [ "$M" = "true" ] || exit 1
cd /home/claude/dq4-portage && git checkout -q main && git pull -q origin main && git log --oneline -1
if [ -n "$COM" ] && [ "$COM" != "-" ]; then gh api -X POST repos/$R/issues/$ISS/comments -F body=@"$COM" --jq '.html_url'; fi
