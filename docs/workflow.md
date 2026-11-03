# Manière de travailler

Usage réel dans `dq4-portage` (relevé le 02/11/2026 sur les 46 premières pull requests, remis à jour le 03/11/2026) : **le suivi se fait par pull request, pas par issue**. Le dépôt n'a aucune issue, aucun jalon, et seulement les 10 étiquettes par défaut de GitHub. **Tout se fait dans ce dépôt** : l'ancien dépôt `dq4-pc` a été supprimé le 03/11/2026 (Sylfried).

## Branches
- `main` : toujours lançable et testée sur le PC de test. On n'y pousse pas directement.
- Une branche par sujet, créée depuis `main`. Les premières portaient un préfixe (`feat/<sujet>`, `fix/<sujet>`, `docs/<sujet>`) ; la suite a pris des noms libres (`retours-18h02`, `lot45`, `audit2-histo`). Aucune règle de nom n'est imposée.
- Les branches fusionnées **ne sont pas supprimées** pour l'instant : `delete_branch_on_merge` est désactivé, il reste de nombreuses branches distantes (une par pull request fusionnée : 56 au 03/11/2026, `main` comprise). Les supprimer est une décision de Sylfried (décision 2 de `docs/audit/rapport_reste_a_faire.md`), qui n'est pas encore prise : ne pas y toucher sans son accord.

## Pull requests
- Titre : **« Avance #N : titre »**, où N est le numéro de la pull request (nombre de PR existantes + 1). Corps court, en français, avec les sections « Retours », « Tests », « À trancher » et « Non vérifié » (le modèle `.github/pull_request_template.md` en donne le squelette).
- Fusion **en squash** vers `main`. `outils/flux_session/pr.sh "titre" corps.md` fait tout : pousse la branche, ouvre la pull request, la fusionne par l'API REST (le GraphQL est bloqué en session cloud), revient sur `main` et fait `git pull` (voir `outils/flux_session/LISEZMOI.md`).
- **Pas de `Closes #n`** : il n'y a aucune issue à fermer dans ce dépôt. Un sujet qui vient d'une ancienne issue la cite en clair (« voir l'ancienne issue #16 », décrite dans `docs/audit/github_issues.md`), sans mot-clé de fermeture.
- Un gros lot est fait par des sous-agents en parallèle (un worktree et une branche chacun), fusionnés dans une branche de lot, avec la suite de tests complète sur l'arbre fusionné avant la pull request (voir `docs/reprise.md`, §5).

## Commits
Courts, au présent, préfixés : `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`. Un commit = une idée. Les commits de Claude se terminent par le pied `Co-Authored-By` et la ligne `Claude-Session` de la session en cours.

## Suivi des tâches et des numéros
- Les tâches, bugs et pistes de recherche en cours sont dans les notes (`docs/notes-visionneuse-dq4-pc.md`, section « Reste à faire » et « À trancher par Sylfried »), dans `docs/reprise.md` (sujets ouverts) et dans les listes de l'audit (`docs/audit/`).
- Les **anciens numéros d'issues** (#1 à #57) sont ceux de l'ancien dépôt `dq4-pc`, **supprimé le 03/11/2026** : une mention « issue #16 » dans les notes ou dans une ancienne pull request désigne cette ancienne issue, pas une issue de ce dépôt. Leur état réel au 02/11/2026 (43 issues dont 27 ouvertes) est conservé dans `docs/audit/github_issues.md` ; les restes qui comptent sont dans `docs/audit/rapport_reste_a_faire.md`.
- Les modèles d'issue de `.github/ISSUE_TEMPLATE` existent toujours, mais ils demandent des étiquettes `type:` qui n'existent pas dans ce dépôt, et personne ne s'en sert.

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
