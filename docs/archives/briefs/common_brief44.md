# Brief commun — agents de la partie 2 de l'audit « giga complet » (PR #44)

## Le projet
Portage PC 16:9 de Dragon Quest IV (APK Android patché FR). Le moteur d'origine `libdq4core.so` tourne tel quel sous Unicorn ; la couche Unity C# est refaite dans une visionneuse pyglet (`dq4_pc/fenetre.py`, `engine.py`, `ui_menu.py`, `pause.py`, `sound.py`, `settings.py`, `postfx.py`, `flat_sceneries.py`, `fbx.py`...). Utilisateur : Sylfried, francophone, « vibecoder » (il veut des outils clé en main, il teste sur son PC Windows). Réponses courtes, honnêtes : **toujours dire ce qui est établi (lu dans le code / observé), supposé, non vérifié**.

Lis d'abord : `docs/viewer-notes-dq4-pc.md` (surtout la fin : « Retours de 23 h 24 … (#42) », « Retours de 20 h 46 … (#41) »), `docs/technical-notes-dq4-port.md` (dans ton worktree), `docs/workflow.md`, et au besoin `/tmp/specs/unity_avant_partie.md`, `/tmp/specs/prologue.md`, `/tmp/specs/camera_bip.md`, `/tmp/specs/moteur_avant_partie.md` (si présents). Dump IL2CPP : `/home/claude/il2/dump.cs` (+ `script.json`, `libil2cpp.so`, outils `/home/claude/il2/*.py` et `/tmp/specs/*.py`) — **lecture seule**.


Base = `main` à **ab22007** (PR #43 fusionnée, 02/11/2026). Lis d'abord `docs/viewer-notes-dq4-pc.md` (surtout la section « Retours de 02 h 12 … (#43) » à la fin) et `docs/technical-notes-dq4-port.md` dans ton worktree.

## Le contexte de cette mission
Sylfried a demandé (lundi 02 h 12) un **audit « giga complet »** de ce qui reste : « issues GitHub, fonctionnalités jamais discutées (casino, églises, banque…), menus, interrupteurs, variables, placement des PNJ, scripts », avec un **rapport final** qui classe chaque manque ou écart en trois catégories : **(a) décision de Sylfried** (il l'a demandé ou validé), **(b) oubli de Claude** (aurait dû être fait ou vérifié), **(c) bug**. Partie 1 (lecture seule) faite : `/tmp/audit/couverture.md` (**lis §1, §3, §4, §6**), `/tmp/audit/lacunes_connues.md` (G-xxx), `/tmp/audit/decisions.md` (D-xx), `/tmp/audit/github_issues.md`. Les outils et captures de la partie 1 sont dans `/tmp/audit/` (sondes `probe_*.py`, `hl.py`, `sweep.py`, `gl_casino.py`, journaux `gl_out_*.txt`). Partie 2 = **ta mission** : enquêter plus loin **et corriger ce qui est simple et sûr** (les corrections seront fusionnées dans la PR #44) ; ce qui est gros ou incertain est seulement documenté avec une estimation.

## Format du rapport final (SubagentHandback), court et en français
1. **Trouvailles** : tableau `ID (ton préfixe + n°) | quoi | preuve | Établi / Supposé / Non vérifié | classe (décision / oubli / bug) | corrigé ? (commit) | sinon : effort estimé`.
2. **Corrections** : liste par commit.
3. **Notes à fusionner dans `docs/`** (texte prêt à coller).
4. **Ce que tu n'as pas pu vérifier** (Windows, GPU réel, chapitre non atteignable, etc.).
Ne conclus jamais « présent » ou « absent » sans preuve (capture, trace, ligne de code). Si tu ne peux pas atteindre une fonctionnalité dans le moteur de test (pas de sauvegarde au bon chapitre), dis-le et propose le chemin le plus court pour la tester.

## Règles de travail (impératives)
1. Tu travailles **uniquement dans ton worktree** (donné dans ta mission), sur sa branche `agent-xxx`. **Ne touche pas** à `/home/claude/dq4-portage` (dépôt principal), ne fais **aucun** `git push`, ne change pas de branche, ne crée pas de PR. Commits sur ta branche, avec ce pied de message (deux lignes séparées) :
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
   `Claude-Session: https://claude.ai/code/session_014GF7TUJhoy5Df7FLvSTYtw`
2. **Ne touche jamais** aux fichiers du patch FR (APK patchés, `*.mpt`...) ni aux sauvegardes de l'utilisateur (`/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes` = copie de SES vrais fichiers, **lecture seule** ; les tests écrivent dans `/tmp/sv_NOM`).
3. Un seul xvfb à la fois sur la machine (2 coeurs, plusieurs agents) : **toujours** lancer les tests via `/tmp/run_wt.sh` (verrou `flock /tmp/xvfb.lock` inclus, les autres jobs attendent). Usage :
   `/tmp/run_wt.sh /home/claude/wt-XXX NOM "image:TOUCHE,image:@x@y,image:\$texte" "image1,image2,..." [slot] [args window.py...]`
   → captures `/tmp/m_NOM_b<image>.png` (la liste des images est séparée par des **virgules**), journal `/tmp/out_NOM.txt`. Clic : `image:@x@y` (pixels depuis le haut-gauche d'une fenêtre 1280 x 720). Touches = noms pyglet (`RETURN`, `ESCAPE`, `LEFT`...). Harnais étendus : `!x!y` (appui), `^x^y` (glisser), `~@x@y` (déplacement), `+TOUCHE` / `-TOUCHE` (touche tenue). Réglages de test : `RG=/tmp/rg_NOM.json` (**fais ta propre copie** : pars de `/tmp/rg_i42.json` = réglages par défaut propres ; **n'utilise pas** `/tmp/rg.json`, pollué par un `angle_camera`). Cache d'interface : `CACHE=/tmp/uicache4` (par défaut ; si tu changes l'extraction de ressources, prends un cache à toi). Lis les captures avec l'outil Read (images). Débogage : variables d'env `DQ_MENUDBG`, `DQ_UIDBG`, `DQ_SAVEDBG`, `DQ_PKTALL=<fichier>`, `DQ_APPEL`, `DQ_CARTE_DEPL`... Quelques centaines d'images moteur prennent plusieurs minutes : prévois des runs ciblés. Slots : `0` = logos + titre + menu de départ ; `1` = journal 1 (Ragnar à Strattbourg, `mak1f1`) ; `2` = journal 2 (début, prologue / Sofiâ à Bastione selon le dossier de sauvegarde).
4. Le moteur d'origine ne se modifie pas. Ce que la visionneuse remplace (couche Unity) doit **coller au comportement mobile d'origine** (« le jeu d'origine fait foi ») sauf mention contraire de l'utilisateur.
5. Reste dans ton périmètre de fichiers (donné dans ta mission) pour limiter les conflits de fusion ; si tu dois toucher ailleurs, change le minimum (quelques lignes) et signale-le dans ton rapport. `python3 -m pyflakes` sur les fichiers modifiés avant de committer (les avertissements existants `sel`, `racine`, `em`, `ax`, `struct`, `unicorn`, `io`, `R`, `yp`, `mh`, `soundfile`, `SourceBoucle` sont connus). Tests unitaires existants dans `tools/test_*.py` : lance ceux qui touchent ton périmètre (`xvfb-run -a -s "-screen 0 800x600x24" python3 tools/<test>.py`, ou via le verrou : `flock /tmp/xvfb.lock xvfb-run ...`) et ajoute les tiens.
6. ** Généralisation** : l'utilisateur a confirmé qu'un bug décrit à partir d'une situation précise doit être réglé **de façon globale**, pas seulement pour le cas décrit. Cherche la cause racine et tous les endroits concernés.
7. Ne mets aucune documentation dans `docs/` toi-même : **inclus dans ton rapport final** les notes à ajouter (je les fusionne).
8. Rapport final (court, en français) **remis avec l'outil SubagentHandback** : ce qui est fait (par point), commits, **Établi / Supposé / Non vérifié**, fichiers touchés, captures utiles (chemins absolus `/tmp/...`), pièges pour la fusion. Ne laisse pas ton arbre de travail sale.
9. Tu n'as pas de Windows : ce que tu ne peux pas tester (GPU réel, vrai plein écran, souris physique...) doit être codé défensivement (repli propre à toute erreur) et listé en « non vérifié ».


## Contexte technique utile (acquis des lots précédents)
- Protocole MenuPort moteur↔Unity : `[N,1,cat,type]` ouvre, `[N,2]` ferme, `[N,3,vis]` ; retour Unity→moteur `Moteur.envoyer_menu(port, buttonId, pad)` (A=16, B=32, ◀8 ▶4, ▲2, ▼1). Menu de départ = type 53 ; boutiques 57–63 ; casino 44–48 ; arène 49–51, 68, 71 ; église 66–67 ; banque 57/64/65 (voir `/tmp/audit/couverture.md` §2).
- Parties du moteur connues de la visionneuse : 3 (ville), 0xc (ville), 0xd (combat), 0xe (carte du monde) ; **0xf (casino) et 0x10 (bestiaire) manquent** (`engine.py:8-11`) ; garde de dessin des maillages dynamiques à `window.py` (`e.partie == MO.PARTIE_VILLE`).
- Moteur seul sans fenêtre : `/tmp/audit/hl.py`, `Moteur` (Unicorn) ; sauvegardes dans `/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes` (lecture seule ; copie vers `/tmp/sv_NOM` pour écrire).
- Caméra : `Jeu._camera_menee`, `cam_jeu`, `angle_camera` ; sprites : `Jeu._panneau_ville` ; `Etat.appliquer` (`engine.py` ~97-196) décode les paquets ; `Etat.sprites[8 + placement]`.
- Éditeur d'interface / Pause : `pause.py`, `settings.py` ; priorité du jeu : `game_priority.py` ; vitesse des combats : `battle_speed.py` ; historique : `history.py`, `ui_history.py`, `libelles.py` ; entrées : `inputs.py`.
- Tests existants : `tools/test_*.py` (unitaires, certains sous xvfb). Lance ceux qui touchent ton périmètre, ajoute les tiens.

## Règles complémentaires de la partie 2
- **Pas de gros refactor** : une correction doit être petite, localisée, et ne pas changer ce qui marche (les 16 points de la PR #43 sont à jour : ne les défais pas).
- Chaque correction a son **commit** séparé et un test ou une capture avant / après.
- Les maillages dynamiques, les parties 0xf / 0x10, `_saisie_menu` et `Etat.appliquer` sont des zones **partagées** entre agents de cette partie : change le strict minimum, signale tout ce que tu touches en dehors de ton périmètre.
