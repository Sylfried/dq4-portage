# Licences : le dépôt et ses dépendances

Établi le 03/11/2026 (décision D-170, issue #86 fermée). **Ce n'est pas un avis juridique** : ce sont des textes publics lus et des constats. Légende : **Établi** (lu), **Supposé**, **Non vérifié**.

## Le dépôt `dq4-portage`
- **Aucun fichier `LICENSE`** : le code du portage n'a pas de licence choisie. **Pas nécessaire aujourd'hui** (voir « Faut-il un fichier `LICENSE` ? » plus bas, D-196) ; choix à faire par Sylfried avant toute redistribution d'un `.exe` ou si d'autres doivent pouvoir réutiliser le code.
- Il ne contient **aucun contenu Square Enix** (`.gitignore` strict, et la CI refuse les fichiers interdits : voir `.github/workflows/ci.yml`). `libdq4core.so`, les APK et les ressources du jeu restent chez l'utilisateur, qui les fournit lui-même.

## Unicorn (l'émulateur qui exécute `libdq4core.so`)
**Établi (lu le 03/11/2026)**
- Le paquet PyPI `unicorn` (2.1.3 et 2.1.4 ; la 2.1.4 du 09/09/2025 est celle de l'environnement cloud) déclare **`License: BSD License`** (classifier OSI « BSD ») dans ses métadonnées. **Mais** la description du même paquet dit « Distributed under free software license GPLv2 », et le paquet installé ne contient **aucun fichier de licence**.
- Le dépôt amont (`unicorn-engine/unicorn`) contient `COPYING` = **GNU General Public License version 2** (juin 1991), **sans exception de liaison**, et son README dit « This project is released under the GPL license ».
- Le `setup.py` des liaisons Python ne déclare aucune licence ni aucun fichier de licence : rien dans ce que j'ai lu n'appuie l'étiquette « BSD ».
- La bibliothèque compilée livrée avec le paquet (`libunicorn.so.2`) contient des symboles `qemu_*` : Unicorn est bâti sur QEMU.

**Supposé** : l'étiquette « BSD » de PyPI est une erreur de métadonnées ; QEMU est sous GPL v2 (connu, non relu ici).

**Conclusion de travail** : traiter Unicorn comme **GPL v2**, la lecture la plus prudente.

**Conséquences**
- Aujourd'hui, le dépôt ne contient aucun code d'Unicorn ; `dq4_pc/lancer_dq4.bat` l'installe depuis PyPI sur la machine de l'utilisateur (`pip install … unicorn …`). Le portage ne redistribue donc pas Unicorn.
- Un `.exe` qui **embarque** Unicorn (issue #87, packaging) en serait une redistribution : les obligations de la GPL v2 s'appliquent (texte de la licence, code source correspondant et, selon la lecture usuelle de la GPL, une licence compatible pour le programme qui l'embarque). **À faire confirmer** avant de publier.

## Choix à faire (par Sylfried, avant le `.exe`, issue #87)
- **(a)** Rester sur « scripts + `.bat` qui télécharge Unicorn » : rien à changer ; pas de `.exe`.
- **(a')** Un **`.exe` « launcher »** (ajouté le 03/11 à 16 h 47, D-195) : un petit exécutable qui fait ce que fait le `.bat` (trouver Python, préparer l'environnement, installer les modules depuis PyPI au premier lancement, lancer la visionneuse). Nous ne livrerions toujours pas Unicorn : c'est la machine du joueur qui le télécharge, comme avec le `.bat`. **Supposé** : même position juridique que (a) ; **à faire confirmer**. Condition : le `.exe` ne doit **pas** contenir Unicorn (un outil qui empaquette Python et ses modules dans un seul fichier l'y mettrait : à éviter pour ce mode).
- **(b)** Publier le portage sous GPL v2 (ou compatible) pour pouvoir embarquer Unicorn dans un `.exe`.
- **(c)** Un autre émulateur : **non évalué**.
Sylfried (03/11, 16 h 47) : « On verra pour les portages, est-ce que je reste sous ce format ou bien on en fait un exe en mode launcheur » : **pas tranché**, à reprendre après la validation Windows de DQ4 (issue #87).

## Faut-il un fichier `LICENSE` ? (D-196)
Sylfried (03/11, 16 h 47) : « Il faudrait le créer le fichier licence ? Fais le si il le faut ». **Réponse : pas aujourd'hui, donc pas créé.**
- **Établi** (page « Licensing a repository » de la documentation GitHub, lue le 03/11/2026) : sans licence, « the default copyright laws apply, meaning that you retain all rights to your source code and no one may reproduce, distribute, or create derivative works from your work » ; et, pour un dépôt public, « other users of GitHub.com have the right to view and fork your repository ». Le dépôt étant public, tout le monde peut donc le lire et le dupliquer sur GitHub, mais personne n'a le droit de réutiliser le code ailleurs. Cela ne gêne pas le projet tel qu'il est.
- Un `LICENSE` devient utile dans trois cas : (1) un `.exe` qui embarque Unicorn (choix (b), obligation de la GPL v2) ; (2) Sylfried veut que d'autres puissent réutiliser ou modifier le code ; (3) un launcher ou un `.exe` est distribué à d'autres joueurs (leur dire à quelles conditions ils peuvent l'utiliser et le partager).
- **Le choix du texte appartient à Sylfried** : donner une licence est irréversible pour ceux qui ont déjà une copie. Si le besoin se présente, proposition (à valider) : **GPL v2** pour (b), la licence d'Unicorn ; **MIT** si le code est livré sans Unicorn et qu'il veut une licence très ouverte (le code sous MIT peut ensuite être repris dans un ensemble sous GPL).
Dans tous les cas, ajouter un fichier `LICENSE` avant de distribuer un `.exe`.

## Autres dépendances installées par `lancer_dq4.bat`
Licence **déclarée dans les métadonnées** du paquet installé dans l'environnement cloud (`pip show`) ; les versions du PC peuvent différer. **Non vérifié** : les fichiers de licence eux-mêmes (le cas d'Unicorn montre que métadonnées et fichiers peuvent se contredire).

| Paquet | Version relevée | Licence déclarée |
|---|---|---|
| numpy | 2.5.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| pillow | 12.3.0 | MIT-CMU |
| UnityPy | 1.25.4 | MIT |
| soundfile | 0.14.0 | BSD 3-Clause |
| pyglet | 2.1.19 | non indiquée dans les métadonnées (non relue) |
| capstone | 5.0.9 | non indiquée dans les métadonnées (non relue) |
