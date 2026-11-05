#!/bin/bash
cd /home/claude/wt-console
export PYTHONDONTWRITEBYTECODE=1 PYGLET_HEADLESS=1 PYGLET_AUDIO=silent DQ4_DATA=/tmp/console_data
unset DQ_APK DQ_SAVES
OUT=/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/console/noengine_results.txt
: > $OUT
for f in tests/test_*.py; do
  n=$(basename $f .py)
  r=$(timeout 300 python3 -W ignore $f 2>&1 | grep -E "^(Ran|OK|FAILED|FAIL:|ERROR:)" | tr '\n' ' ' | cut -c1-400)
  echo "$n: $r" >> $OUT
done
echo FINISHED >> $OUT
