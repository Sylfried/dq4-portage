# Brief commun — agents du lot « retours de 20 h 46 » (PR #41)

## Le projet
Portage PC 16:9 de Dragon Quest IV (APK Android patché FR). Le moteur d'origine `libdq4core.so` tourne tel quel sous Unicorn ; la couche Unity C# est refaite dans une visionneuse pyglet (`dq4_pc/fenetre.py`, `engine.py`, `ui_menu.py`, `pause.py`, `sound.py`, `settings.py`...). Utilisateur : Sylfried, francophone, « vibecoder » (il veut des outils clé en main, il teste sur son PC Windows). Il faut des réponses courtes, honnêtes : **toujours dire ce qui est établi (lu dans le code / observé), supposé, non vérifié**.

Lis d'abord : `docs/viewer-notes-dq4-pc.md`, `docs/technical-notes-dq4-port.md` (dans ton worktree), et au besoin `/tmp/specs/unity_avant_partie.md` (spécification de la couche Unity, conventions UI : portrait 450 x 800, plan XZ...). Dump IL2CPP : `/home/claude/il2/dump.cs` (+ `script.json`, `libil2cpp.so`, outils `/home/claude/il2/*.py` et `/tmp/specs/scripts`, `/tmp/specs/*.py`) — **lecture seule**.

## Règles de travail (impératives)
1. Tu travailles **uniquement dans ton worktree** (donné dans ta mission), sur sa branche `agent-xxx`. **Ne touche pas** à `/home/claude/dq4-portage` (c'est le dépôt principal), ne fais **aucun** `git push`, ne change pas de branche, ne crée pas de PR. Commits sur ta branche, avec ce pied de message :
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` puis `Claude-Session: https://claude.ai/code/session_014GF7TUJhoy5Df7FLvSTYtw` (deux lignes séparées).
2. **Ne touche jamais** aux fichiers du patch FR (APK patchés, `*.mpt`...) ni aux sauvegardes de l'utilisateur (`/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes` = copie de SES vrais fichiers, **lecture seule** ; les tests écrivent dans `/tmp/sv_NOM`).
3. Un seul xvfb à la fois sur la machine (2 coeurs, plusieurs agents) : **toujours** lancer les tests via `/tmp/run_wt.sh` (verrou `flock /tmp/xvfb.lock` inclus, les autres jobs attendent). Usage :
   `/tmp/run_wt.sh /home/claude/wt-XXX NOM "image:TOUCHE,image:@x@y,image:\$texte" "images à capturer" [slot] [args window.py...]`
   → captures `/tmp/m_NOM_b<image>.png`, journal `/tmp/out_NOM.txt`. Clic : `image:@x@y` (pixels depuis le haut-gauche d'une fenêtre 1280 x 720). Touches = noms pyglet (`RETURN`, `ESCAPE`, `LEFT`...). Réglages de test : `/tmp/rg.json` (copie à toi si tu les modifies : `RG=/tmp/rg_NOM.json /tmp/run_wt.sh ...`). Cache d'interface : `CACHE=/tmp/uicache4` (par défaut). Lis les captures avec l'outil Read (images). Débogage : variables d'env `DQ_MENUDBG`, `DQ_UIDBG`, `DQ_SAVEDBG`, `DQ_PKTALL=<fichier>`. Quelques centaines d'images moteur prennent plusieurs minutes : prévois des runs ciblés, pas de runs inutiles. Slot `0` = « Continuer » du premier journal.
4. Le moteur d'origine ne se modifie pas. Ce que la visionneuse remplace (couche Unity) doit **coller au comportement mobile d'origine** (« le jeu d'origine fait foi ») sauf mention contraire de l'utilisateur.
5. Reste dans ton périmètre de fichiers (donné dans ta mission) pour limiter les conflits de fusion ; si tu dois toucher ailleurs, change le minimum (quelques lignes) et signale-le dans ton rapport. `python3 -m pyflakes` sur les fichiers modifiés avant de committer (les avertissements existants `sel`, `racine`, `em`, `ax` sont connus).
6. Ne mets aucune documentation dans `docs/` toi-même : **inclus dans ton rapport final** les notes à ajouter (je les fusionne).
7. Rapport final (court, en français) : ce qui est fait (par point), commits, **Établi / Supposé / Non vérifié**, fichiers touchés, captures utiles (chemins absolus `/tmp/...`), pièges pour la fusion.

## Les retours de l'utilisateur (message du dimanche 20 h 46, extraits utiles)
Voir ta mission. Les captures de l'utilisateur ne sont pas disponibles : fie-toi à ses mots.
