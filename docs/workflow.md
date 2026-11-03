# Manière de travailler

Usage dans `dq4-portage` (relevé le 02/11/2026 sur les 46 premières pull requests, remis à jour le 03/11/2026) : **le travail passe par pull request** (« Avance #N : titre ») et, **depuis le 03/11/2026, le reste à faire est suivi par des issues** (#51 à #88, demande de Sylfried). Avant cette date le dépôt n'avait aucune issue. **Tout se fait dans ce dépôt** : l'ancien dépôt `dq4-pc` a été supprimé le 03/11/2026 (Sylfried).

## Branches
- `main` : toujours lançable et testée sur le PC de test. On n'y pousse pas directement.
- Une branche par sujet, créée depuis `main`. Les premières portaient un préfixe (`feat/<sujet>`, `fix/<sujet>`, `docs/<sujet>`) ; la suite a pris des noms libres (`retours-18h02`, `lot45`, `audit2-histo`). Aucune règle de nom n'est imposée.
- Les branches fusionnées **ne sont pas supprimées** pour l'instant : `delete_branch_on_merge` est désactivé, il reste de nombreuses branches distantes (une par pull request fusionnée ; 57 au 03/11/2026, `main` comprise). Les supprimer est une décision de Sylfried (décision 2 de `docs/audit/rapport_reste_a_faire.md`), qui n'est pas encore prise : ne pas y toucher sans son accord.

## Pull requests
- Titre : **« Avance #N : titre »**, où N est le numéro de la pull request (nombre de PR existantes + 1). Corps court, en français, avec les sections « Retours », « Tests », « À trancher » et « Non vérifié » (le modèle `.github/pull_request_template.md` en donne le squelette).
- Fusion **en squash** vers `main`. `outils/flux_session/pr.sh "titre" corps.md` fait tout : pousse la branche, ouvre la pull request, la fusionne par l'API REST (le GraphQL est bloqué en session cloud), revient sur `main` et fait `git pull` (voir `outils/flux_session/LISEZMOI.md`).
- **Issues** : une PR qui règle une issue écrit `Closes #n` dans son corps (la fusion en squash la ferme) ; une PR qui n'en règle qu'une partie la cite sans mot-clé. **Issues et PR partagent la même numérotation** : « Avance #N » porte le vrai numéro de la PR (`pr.sh` prend le plus grand numéro existant + 1), donc la série saute quand des issues sont créées (après #50, la PR suivante est #89).
- **Pas d'issues ouvertes après coup** pour du travail déjà fait (un historique d'issues créées puis fermées le même jour n'apporte rien) : l'historique, ce sont les PR « Avance #N », `docs/historique.md` et les notes. Seules les anciennes issues qui ont encore un reste sont reprises.
- Un gros lot est fait par des sous-agents en parallèle (un worktree et une branche chacun), fusionnés dans une branche de lot, avec la suite de tests complète sur l'arbre fusionné avant la pull request (voir `docs/reprise.md`, §5).

## Commits
Courts, au présent, préfixés : `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`. Un commit = une idée. Les commits de Claude se terminent par le pied `Co-Authored-By` et la ligne `Claude-Session` de la session en cours.

## Suivi des tâches et des numéros
- **Le reste à faire est dans les issues GitHub** (38 issues #51 à #88 créées le 03/11/2026, une par chantier, bug ou test). Jalons : 1 « Validation Windows » (#51 à #58), 2 « Clavier complet et manette » (#59 à #61), 3 « Chapitre 2 et services » (#62 à #65), 4 « Moteur et finitions » (#66 à #85), 5 « Distribution et extensions » (#86 à #88). Étiquettes : `type:feature`, `type:bug`, `type:recherche` (celles des modèles d'issue), `test-windows` (à vérifier sur le PC de Sylfried), `priorité:haute`, `bloqué` (attend Sylfried : sauvegardes, test, décision), `accessibility`. Le détail des constats reste dans `docs/audit/` (`lacunes_connues.md`, `rapport_reste_a_faire.md`), que chaque issue cite ; les notes (`docs/notes-visionneuse-dq4-pc.md`, « À trancher par Sylfried ») et `docs/reprise.md` (sujets ouverts) donnent le contexte.
- **À tenir à jour à chaque PR** : fermer (`Closes #n`) ou commenter les issues concernées, ouvrir une issue pour tout défaut ou reste nouveau, mettre à jour les docs.
- Les **anciens numéros d'issues** (#1 à #57) sont ceux de l'ancien dépôt `dq4-pc`, **supprimé le 03/11/2026** : une mention « issue #16 » dans les notes ou dans une ancienne pull request désigne cette ancienne issue, pas une issue de ce dépôt (**attention** : depuis le 03/11 les issues de ce dépôt sont #51 à #88 ; une mention antérieure au 03/11 d'une « issue #56 » ou « #57 » désigne l'ancien dépôt). Leur état réel au 02/11/2026 (43 issues dont 27 ouvertes) est conservé dans `docs/audit/github_issues.md` ; les restes qui comptent sont dans `docs/audit/rapport_reste_a_faire.md`.
- Les modèles d'issue de `.github/ISSUE_TEMPLATE` (tâche, bug, recherche) servent de nouveau : les étiquettes `type:feature`, `type:bug` et `type:recherche` qu'ils demandent ont été créées le 03/11/2026.

## Avant de fusionner et après
1. Avant la fusion : vérification en cloud, sans écran (`PYGLET_HEADLESS=1`, tests ciblés ou `outils/flux_session/lancer_tests.sh` pour toute la suite). Rien de cela ne valide Windows ni un vrai GPU.
2. Après la fusion : sur le PC de test, `git pull --ff-only origin main`, double-clic sur `dq4_pc\lancer_dq4.bat`, puis marcher, ouvrir une porte, changer de carte, ouvrir et fermer le menu, lire un message : rien ne régresse. Les points qui n'ont pu être vus que sous Linux sont listés dans « Non vérifié » de la pull request.

## Règles du projet
- **Aucun contenu Square Enix** dans le dépôt (voir `.gitignore`, ne jamais forcer avec `git add -f`). Les outils lisent les fichiers de l'utilisateur sur son PC. Pas de dump IL2CPP, pas de capture du jeu.
- Projet séparé du patch FR : ne jamais toucher à ses fichiers (APK patchés, `*.mpt`, Excel, `DQ_Patch_FR.exe`, `build_exe.bat`).
- Les sauvegardes de l'utilisateur ne sont jamais modifiées (les nouvelles vont dans `dq4_pc\sauvegardes`) ; les tests lisent une copie en lecture seule et écrivent dans `/tmp`.
- Le jeu d'origine fait foi : ce que la visionneuse remplace doit coller au comportement du mobile, sauf demande contraire.
- **Le moteur** : le fichier `libdq4core.so` n'est jamais modifié. En mémoire, seuls existent les correctifs ciblés et les crochets listés dans `docs/notes-technique-portage-dq4.md` (section « Écritures et crochets en mémoire du moteur ») ; **tout nouveau correctif ou crochet s'ajoute à cette liste**, avec sa garde (instruction d'origine vérifiée avant d'écrire) et son rôle. Aucun ne doit toucher un scénario, l'or, l'inventaire ni la position du héros sans accord de Sylfried.

## Délégation (30/10/2026)
Sylfried laisse à Claude la gestion des commits, pushs, pull requests et fusions (squash vers `main` ; la suppression des branches fusionnées attend la décision ci-dessus). Les fusions restent précédées d'une vérification en cloud ; les tests sur le PC de test se font sur les fichiers copiés avant ou pendant la PR.

## Dépôts (30/10/2026)
Le dépôt d'origine `dq4-pc` a été séparé : ce dépôt (`dq4-portage`) garde le portage natif ; l'essai Unity (piste 3) vit dans `dq4-portage-unity` ; le patch français reste dans `dq456-traductions-fr`. `dq4-pc` n'existe plus (supprimé le 03/11/2026). Le moteur (`dq4_pc/`) est ici ; l'essai Unity en dépend.
