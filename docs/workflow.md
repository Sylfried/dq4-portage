# Manière de travailler

## Branches
- `main` : toujours lançable et testée sur le PC de test. On n'y pousse pas directement.
- Une branche par sujet, créée depuis `main` : `feat/<sujet>`, `fix/<sujet>`, `recherche/<sujet>`, `docs/<sujet>` (ex. `feat/sous-menus-objets`).
- Pull request vers `main` (fusion « squash »), description avec `Closes #<numéro>`. La branche est supprimée après fusion.

## Commits
Courts, au présent, préfixés : `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`. Un commit = une idée.

## Issues
- Chaque tâche, bug ou piste de recherche a une issue (modèles dans `.github/ISSUE_TEMPLATE`).
- Étiquettes : `type:` bug / feature / recherche / chore ; `zone:` rendu / interface / moteur / son / sauvegardes / outillage ; `prio:` haute / basse.
- Jalons : **M1 Village jouable 16/9**, **M2 Monde et combats**, **M3 Son et finitions**.

## Avant de fusionner (test sur le PC de test)
1. Double-clic sur `dq4_pc\lancer_dq4.bat` avec la branche récupérée.
2. Marcher, ouvrir une porte, changer de carte, ouvrir/fermer le menu, lire un message : rien ne régresse.
3. Cocher la liste dans la pull request.

## Règles du projet
- **Aucun contenu Square Enix** dans le dépôt (voir `.gitignore`). Les outils lisent les fichiers de l'utilisateur sur son PC.
- Projet séparé du patch FR : ne jamais toucher à ses fichiers (Excel, `DQ_Patch_FR.exe`, `build_exe.bat`).
- Les sauvegardes de l'utilisateur ne sont jamais modifiées (les nouvelles vont dans `dq4_pc\sauvegardes`).

## Délégation (30/10/2026)
Sylfried laisse à Claude la gestion des issues, commits, pushs, pull requests et fusions (squash vers `main`, branche supprimée ensuite). Les fusions restent précédées d'une vérification en cloud ; les tests sur le PC de test se font sur les fichiers copiés avant ou pendant la PR.

## Dépôts (30/10/2026)
Le dépôt d'origine `dq4-pc` a été séparé : ce dépôt (`dq4-portage`) garde le portage natif ; l'essai Unity (piste 3) vit dans `dq4-portage-unity` ; le patch français reste dans `dq456-traductions-fr`. Les issues d'avant la séparation sont dans `dq4-pc`. Le moteur (`dq4_pc/`) est ici ; l'essai Unity en dépend.
