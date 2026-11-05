#!/bin/bash
cd /home/claude/dq4-portage
export PYGLET_HEADLESS=1 DQ_APK="/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks" DQ_SAVES=/mnt/user-data/uploads/dq4-portage/donnees/sauvegardes/mobile/20261007_190735 DQ_CACHE_CARTES=/tmp/cache44 PYGLET_AUDIO=silent
for f in tests/test_*.py; do
  n=$(basename $f .py)
  r=$(timeout 900 python3 -W ignore $f --apk "$DQ_APK" --saves "$DQ_SAVES" 2>&1 | tail -3 | tr '\n' ' ')
  case "$r" in *unrecognized*) r=$(timeout 900 python3 -W ignore $f 2>&1 | tail -3 | tr '\n' ' ');; esac
  echo "$n: $r"
done
echo END
