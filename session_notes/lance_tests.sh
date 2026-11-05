#!/bin/bash
# usage: lance_tests.sh <worktree> <sortie.log> [fichiers...]
cd "$1"; OUT="$2"; shift 2
export PYGLET_HEADLESS=1 PYGLET_AUDIO=silent PYTHONDONTWRITEBYTECODE=1 DQ_APK=/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks DQ_SAVES=/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735 DQ_UI_CACHE=/tmp/audit_final/interface/uicache
FILES="$@"; [ -z "$FILES" ] && FILES=$(ls tests/test_*.py)
: > "$OUT"
for f in $FILES; do
  if timeout 300 python3 "$f" > /tmp/t_$$.log 2>&1; then echo "OK   $f" >> "$OUT"; else echo "FAIL $f" >> "$OUT"; tail -5 /tmp/t_$$.log | sed 's/^/     /' >> "$OUT"; fi
done
echo FIN >> "$OUT"
