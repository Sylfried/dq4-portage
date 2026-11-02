#!/bin/bash
# usage: moteur_slot.sh commande [args...]
# Au plus 2 executions du vrai moteur (Unicorn) ou de la visionneuse en meme temps sur la machine (2 coeurs, 7 Go) :
# la commande attend qu'un des deux creneaux (/tmp/moteur_slot_1.lock, _2.lock) soit libre, puis le garde jusqu'a sa fin.
while true; do
  for i in 1 2; do
    exec 9>/tmp/moteur_slot_$i.lock
    if flock -n 9; then "$@"; exit $?; fi
    exec 9>&-
  done
  sleep 2
done
