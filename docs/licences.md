# Licences : le dépôt et ses dépendances

Établi le 03/11/2026 (décision D-170, issue #86 fermée). **Ce n'est pas un avis juridique** : ce sont des textes publics lus et des constats. Légende : **Établi** (lu), **Supposé**, **Non vérifié**.

## Le dépôt `dq4-portage`
- **Aucun fichier `LICENSE`** : le code du portage n'a pas de licence choisie. Choix à faire par Sylfried avant toute redistribution (voir « Choix à faire » plus bas).
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
- **(b)** Publier le portage sous GPL v2 (ou compatible) pour pouvoir embarquer Unicorn dans un `.exe`.
- **(c)** Un autre émulateur : **non évalué**.
Dans tous les cas, choisir et ajouter un fichier `LICENSE` pour le code du portage.

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
