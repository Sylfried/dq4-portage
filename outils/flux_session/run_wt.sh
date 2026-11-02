#!/bin/bash
# usage: run_wt.sh WORKTREE NOM "touches" "captures" [slot] [extra args...]
#  WORKTREE = racine du depot (ex. /home/claude/wt-xxx) ; NOM = prefixe des sorties /tmp/m_NOM_b<image>.png et /tmp/out_NOM.txt
#  touches : "image:TOUCHE,image:@x@y (clic, 1280x720 depuis le haut-gauche),image:\$texte" ; captures : "image1 image2 ..." ; --saves-lecture = SES VRAIS fichiers (lecture seule) ; --saves-ecriture = /tmp/sv_NOM (jetable)
#  Un seul xvfb a la fois sur la machine (2 coeurs) : verrou /tmp/xvfb.lock (les autres jobs attendent leur tour).
WT=$1; N=$2; T=$3; FIN=$4; SLOT=${5:-0}; shift 5 2>/dev/null
rm -rf /tmp/sv_$N; rm -f /tmp/m_${N}*.png
cd "$WT/dq4_pc"
flock /tmp/xvfb.lock env PYGLET_AUDIO=silent timeout 900 xvfb-run -a -s "-screen 0 1920x1080x24" python3 fenetre.py --apk "/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks" --saves-lecture /mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes --saves-ecriture /tmp/sv_$N --reglages ${RG:-/tmp/rg.json} --slot $SLOT --cache ${CACHE:-/tmp/uicache4} --msaa 0 --largeur 1280 --hauteur 720 --sans-preparation --sans-son --shot /tmp/m_$N.png --images 100000 --touches-test "$T" --shots-boucle "$FIN" "$@" > /tmp/out_$N.txt 2>&1
echo exit $?; tail -4 /tmp/out_$N.txt
