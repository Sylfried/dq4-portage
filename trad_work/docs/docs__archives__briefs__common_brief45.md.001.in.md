# Brief commun — lot « retours de 14 h 08 » (PR #45)

## Le projet
Portage PC 16:9 de Dragon Quest IV (APK Android patché FR). Le moteur d'origine `libdq4core.so` tourne tel quel sous Unicorn ; la couche Unity C# est refaite dans une visionneuse pyglet (`dq4_pc/fenetre.py`, `engine.py`, `ui_menu.py`, `pause.py`, `sound.py`, `settings.py`, `postfx.py`, `flat_sceneries.py`, `fbx.py`, `history.py`, `ui_history.py`, `inputs.py`, `battle_speed.py`...). Utilisateur : Sylfried, francophone, « vibecoder » (il veut des outils clé en main, il teste sur son PC Windows). Réponses courtes, honnêtes : **toujours dire ce qui est établi (lu dans le code / observé), supposé, non vérifié**.

Base = `main` à **84b3f22** (PR #44 fusionnée, 02/11/2026). Lis d'abord, dans ton worktree : `docs/viewer-notes-dq4-pc.md` (surtout « Avance #44 » et « Retours de 02 h 12 … (#43) » à la fin), `docs/technical-notes-dq4-port.md` (« Avance #44 : faits techniques »), `docs/workflow.md`. Dump IL2CPP : `/home/claude/il2/dump.cs` (+ `script.json`, `libil2cpp.so`, outils `/home/claude/il2/*.py` et `/tmp/specs/*.py`) — **lecture seule**.

## Le contexte de cette mission
Sylfried a envoyé (lundi 14 h 08) une liste de 17 retours. Chaque agent en traite un sous-ensemble (ta mission). Captures de référence (lis-les avec l'outil Read) dans `/tmp/specs/img45/` : `ecran1_pc_dialogue_sans_nom.png` (le PC : la boîte de dialogue n'affiche pas le nom de l'interlocuteur), `ecran2_mobile_dialogue_nom_Angus.jpg` (le MOBILE : cartouche « Angus » sur le bord haut-gauche de la boîte, soulignement sous le nom), `ecran3_pc_combat_contours.png` (le PC en combat : contours en escalier des arbres et des montagnes), `ecran4_mobile_cibles_alignement.png` (le MOBILE : choix de la cible, alignement du texte dans les boutons et les onglets), `ecran5_pc_pnj_debout_au_lieu_d_allonge.png` (le PC : un PNJ qui devrait être allongé au sol est debout).

## Format du rapport final (SubagentHandback), court et en français
1. **Par point de ta mission** : fait / partiel / pas fait, avec preuve (capture, test, ligne de code), **Établi / Supposé / Non vérifié**.
2. **Corrections** : liste par commit.
3. **Notes à fusionner dans `docs/`** (texte prêt à coller).
4. **Ce que tu n'as pas pu vérifier** (Windows, GPU réel, moniteur réel, etc.).
Ne conclus jamais « fait » sans preuve. Si un point est trop gros ou trop incertain, documente-le avec une estimation au lieu de bricoler.

## Règles de travail (impératives)
1. Tu travailles **uniquement dans ton worktree** (donné dans ta mission), sur sa branche `agent45-xxx`. **Ne touche pas** à `/home/claude/dq4-portage` (dépôt principal), ne fais **aucun** `git push`, ne change pas de branche, ne crée pas de PR. Commits sur ta branche, avec ce pied de message (deux lignes séparées) :
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
- **Pas de gros refactor** : une correction doit être petite, localisée, et ne pas changer ce qui marche (les PR #43 et #44 sont à jour : ne défais rien de ce qu'elles ont fait).
- Chaque correction a son **commit** séparé et un test ou une capture avant / après.
- Les maillages dynamiques, les parties 0xf / 0x10, `_saisie_menu` et `Etat.appliquer` sont des zones **partagées** entre agents de cette partie : change le strict minimum, signale tout ce que tu touches en dehors de ton périmètre.

## Rappels pratiques (lot #45)
- Tests moteur (unittest, depuis la racine du worktree) : `DQ_APK="/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks" DQ_SAVES=/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes DQ_CACHE_CARTES=/tmp/cache44 python3 -m unittest tools.<test>` (verrou xvfb si le test ouvre une fenêtre). `tools/test_texte_defilement.py` est un script (pas unittest) : `--apk … --saves … --slot 4`.
- Dans le worktree, lance toujours `git status` avant le rapport final (arbre propre) ; commits séparés, un par point.
- Les réglages de l'utilisateur sont enregistrés sur son PC (`reglages.json`) : tout **changement de défaut** doit migrer proprement un fichier existant (ne pas laisser l'ancien défaut gelé), et tout **nouveau réglage** a sa valeur par défaut, son bouton ↺ (`defaut=` dans `pause._choix`) et sa clé dans `settings.py`.
- Les captures de référence de Sylfried sont dans `/tmp/specs/img45/` ; ses mots exacts sont cités dans ta mission : respecte-les à la lettre, et si une consigne est ambiguë, choisis l'interprétation la plus simple, **dis laquelle** dans le rapport.
- Ordre de travail : d'abord les petites corrections sûres (un commit chacune, test ou capture à l'appui), ensuite les enquêtes plus longues.
