# Manière de travailler

## Branches
- `main` : toujours lançable et testée sur pdc. On n'y pousse pas directement.
- Une branche par sujet, créée depuis `main` : `feat/<sujet>`, `fix/<sujet>`, `recherche/<sujet>`, `docs/<sujet>` (ex. `feat/sous-menus-objets`).
- Pull request vers `main` (fusion « squash »), description avec `Closes #<numéro>`. La branche est supprimée après fusion.

## Commits
Courts, au présent, préfixés : `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`. Un commit = une idée.

## Issues
- Chaque tâche, bug ou piste de recherche a une issue (modèles dans `.github/ISSUE_TEMPLATE`).
- Étiquettes : `type:` bug / feature / recherche / chore ; `zone:` rendu / interface / moteur / son / sauvegardes / outillage ; `prio:` haute / basse.
- Jalons : **M1 Village jouable 16/9**, **M2 Monde et combats**, **M3 Son et finitions**.

## Avant de fusionner (test sur pdc)
1. Double-clic sur `dq4_pc\lancer_dq4.bat` avec la branche récupérée.
2. Marcher, ouvrir une porte, changer de carte, ouvrir/fermer le menu, lire un message : rien ne régresse.
3. Cocher la liste dans la pull request.

## Règles du projet
- **Aucun contenu Square Enix** dans le dépôt (voir `.gitignore`). Les outils lisent les fichiers de l'utilisateur sur son PC.
- Projet séparé du patch FR : ne jamais toucher à ses fichiers (Excel, `DQ_Patch_FR.exe`, `build_exe.bat`).
- Les sauvegardes de l'utilisateur ne sont jamais modifiées (les nouvelles vont dans `dq4_pc\sauvegardes`).

## Délégation (30/10/2026)
Sylfried laisse à Claude la gestion des issues, commits, pushs, pull requests et fusions (squash vers `main`, branche supprimée ensuite). Les fusions restent précédées d'une vérification en cloud ; les tests sur pdc se font sur les fichiers copiés avant ou pendant la PR.

## Deux discussions en parallèle (30/10/2026)
- **Piste 1** (visionneuse pyglet fidèle, en lisant le code Unity d'origine) : zone `dq4_pc/`, `outils/`, `docs/notes-*.md`. Issue #56.
- **Piste 3** (essai Unity comme afficheur) : zone `unity_pc/`, `outils/`, `docs/piste-3-*`. Issue #57. Fiche de reprise : `docs/piste-3-projet-unity.md`.
- `git pull` avant chaque nouvelle branche ; une PR = un sujet ; ne pas réécrire les documents de l'autre piste. Les docs du Projet Claude sont remplacés en entier à chaque écriture : chaque discussion n'écrit que les siens (la piste 3 : `claude/piste-3-projet-unity.md` seulement).

