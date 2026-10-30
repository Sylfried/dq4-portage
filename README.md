# Dragon Quest IV : portage PC (essai)

Portage natif sur PC de **Dragon Quest IV (Android)**, à partir de la version déjà patchée en français. Premier objectif : un affichage **16/9** propre.

## Principe (« voie A »)
Le jeu Android est un moteur C++ autonome (`libdq4core.so`, ARM64) piloté par une couche Unity. On garde le moteur tel quel et on réécrit la couche Unity :

- `emu_core.py` : chargeur ELF AArch64 + [Unicorn](https://www.unicorn-engine.org/) qui exécute `libdq4core.so` ;
- `moteur.py` / `pktlog.py` : pilotage du moteur (`GameUpdate`…), décodage des paquets moteur → Unity, file de messages des menus ;
- `fld.py` / `donnees.py` : lecture des cartes et sprites dans les données Unity (UnityPy) ;
- `fenetre.py` : fenêtre pyglet/OpenGL (décor 3D, sprites, caméra 16/9, messages, menus, clavier).

Plan B (recompilation x64) puis plan C (émulateur Android) uniquement si la voie A échoue : elle fonctionne aujourd'hui.

## ⚠️ Aucun contenu Square Enix ici
Ce dépôt ne contient **que du code et des notes**. Le programme lit *tes* fichiers (APK patchés, sauvegardes) sur *ton* PC ; rien n'est copié ni distribué. Les APK, `.so`, données Unity, sauvegardes, caches et captures du jeu sont exclus par `.gitignore` : ne jamais les forcer (`git add -f`). Ce dépôt est séparé du patch FR (jamais de modification de ses fichiers).

## Lancer (Windows)
Disposition attendue (le dépôt est le dossier `portage_pc`) :

```
DQ Patch\
  jeux\DQ4\patched_apks\   (base.apk, split_config.arm64_v8a.apk, split_UnityDataAssetPack.apk)
  jeux\DQ4\saves\<horodatage>\data1.dat
  portage_pc\              <- ce dépôt
    dq4_pc\lancer_dq4.bat  <- double-clic
```
`lancer_dq4.bat` crée un environnement Python local (3.13 > 3.12 > 3.11 > 3.14 > 3.10), installe `numpy pillow unicorn pyglet UnityPy` une fois, puis ouvre la fenêtre. Les nouvelles sauvegardes vont dans `dq4_pc\sauvegardes` (les tiennes ne sont jamais modifiées).

Touches : flèches / ZQSD = marcher ou déplacer le curseur ; Entrée / Espace = valider, avancer un message, parler ; Retour arrière / X = menu de commandes, annuler ; F2 = style des sprites (originaux, EPX, régions lissées, bicubique) ; F3 = lissage du décor (mipmaps, anisotrope) oui / non ; F4 = compteur d'images/s ; Échap = quitter.

## Où en est-on
Voir [`docs/notes-visionneuse-dq4-pc.md`](docs/notes-visionneuse-dq4-pc.md) (état, protocole, « reste à faire ») et [`docs/notes-technique-portage-dq4.md`](docs/notes-technique-portage-dq4.md) (architecture du jeu, protocole moteur → Unity). L'historique des étapes déjà faites est dans [`docs/historique.md`](docs/historique.md). Le suivi du travail se fait dans les **issues** ; la manière de travailler est dans [`docs/workflow.md`](docs/workflow.md).
