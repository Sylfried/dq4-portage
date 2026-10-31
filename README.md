# Dragon Quest IV : portage PC natif (sans Unity)

Portage natif sur PC de **Dragon Quest IV (Android)**, à partir de la version déjà patchée en français. Premier objectif : un affichage **16/9** propre, avec les fenêtres, les menus, la souris (= tactile du mobile), la musique et les bruitages d'origine.

## Principe (« voie A »)
Le jeu Android est un moteur C++ autonome (`libdq4core.so`, ARM64) piloté par une couche Unity. On garde le moteur tel quel et on réécrit la couche Unity en Python :

- `dq4_pc/emu_core.py` : chargeur ELF AArch64 + [Unicorn](https://www.unicorn-engine.org/) qui exécute `libdq4core.so` ;
- `dq4_pc/moteur.py` / `pktlog.py` : pilotage du moteur (`GameUpdate`…), décodage des paquets moteur → Unity, file de messages des menus ;
- `dq4_pc/fld.py` / `donnees.py` : lecture des cartes et sprites dans les données Unity (UnityPy) ;
- `dq4_pc/fenetre.py` : fenêtre pyglet/OpenGL (décor 3D, sprites, combat, carte du monde, caméra 16/9, souris et clavier) ;
- `dq4_pc/ui_menu.py` : fenêtres et menus d'origine, dont la mise en page est lue dans le code C# du jeu (`outils/ui_il2cpp/`) ;
- `dq4_pc/son.py` : musiques et bruitages d'origine (conteneur AKB) ;
- `dq4_pc/hd.py` : agrandissement des sprites (EPX, régions lissées, bicubique) et mode pixel perfect.

## Les dépôts du projet
| Dépôt | Rôle |
|---|---|
| **`dq4-portage`** (celui-ci) | le portage natif, sans Unity |
| `dq4-portage-unity` | essai « Unity comme afficheur » (piste 3), alimenté par le moteur de ce dépôt |
| `dq456-traductions-fr` | patch français des APK (jamais modifié ici) |
| `dq4-pc` (ancien) | dépôt d'origine, avant la séparation ; ses issues et pull requests (#1 à #78) gardent l'historique du suivi |

## ⚠️ Aucun contenu Square Enix ici
Ce dépôt ne contient **que du code et des notes**. Le programme lit *tes* fichiers (APK patchés, sauvegardes) sur *ton* PC ; rien n'est copié ni distribué. Les APK, `.so`, données Unity, sauvegardes, caches et captures du jeu sont exclus par `.gitignore` : ne jamais les forcer (`git add -f`).

## Lancer (Windows)
Il faut les 3 APK français et une sauvegarde, dans le dossier `jeux\DQ4` **de ce dépôt** (le projet ne dépend d'aucun autre dossier ; variable `DQ4_JEUX` pour en indiquer un autre). Disposition simple, dans ce dépôt :

```
dq4-portage\
  jeux\DQ4\patched_apks\   (base.apk, split_config.arm64_v8a.apk, split_UnityDataAssetPack.apk)
  jeux\DQ4\saves\<horodatage>\data1.dat
  dq4_pc\lancer_dq4.bat      <- double-clic
```
`lancer_dq4.bat` crée un environnement Python local (3.13 > 3.12 > 3.11 > 3.14 > 3.10), installe `numpy pillow unicorn pyglet UnityPy capstone soundfile` une fois, puis ouvre la fenêtre. Les nouvelles sauvegardes vont dans `dq4_pc\sauvegardes` (les tiennes ne sont jamais modifiées). Au premier lancement après une mise à jour, le lanceur refait la mise en page des menus d'origine (quelques minutes, une seule fois) et le jeu prépare de nouveau le cache des cartes en arrière-plan (environ une minute et demie, le jeu reste jouable) : les animations de décor (eau, lampes, scintillements) viennent de ce cache.

Touches par défaut (modifiables dans le menu Échap > Touches) : **Haut Z / ↑, Bas S / ↓, Gauche Q / ←, Droite D / →, E** (parler, examiner, valider, avancer un message), **Retour arrière** (annuler), **Entrée** (menu de commandes, hors combat ; avance aussi les messages), **Espace** (discussion de groupe), **M** (carte), **Maj** (courir, maintenu), **A / Page haut** et **R / Page bas** (page précédente / suivante des menus). **Boutons de la version mobile à l'écran** (Carte, Commandes, Discussion de groupe ; clic de souris) : menu Échap > Boutons à l'écran (afficher / masquer, taille, placement par glisser-déposer sur une grille aimantée). **Chiffres 1 à 9 et 0 = enregistrer l'état instantané n° 1 à 10, Ctrl + chiffre = le charger, Ctrl + Maj = annuler le dernier chargement.** **Échap = menu** (reprendre, états instantanés avec miniature, affichage : style des sprites et du décor, échelle pixel perfect, lissage, zoom de la carte du monde, résolution de 720p à 4K, angle de la caméra, plein écran, anticrénelage ; jeu : vitesse de déplacement, course, taille des nombres de dégâts, sens de la molette ; boutons à l'écran ; son ; touches ; quitter). Les curseurs se règlent en glissant, aux flèches ou en cliquant sur la valeur pour la taper ; le bouton ↺ à gauche du curseur (ou Suppr) remet la valeur par défaut. **F1 = infos seulement.** Les réglages sont enregistrés dans `dq4_pc\reglages.json`, les états dans `dq4_pc\sauvegardes\etats\` ; ils ne contiennent aucun fichier du jeu. Options de la ligne de commande : `--reglages fichier.json`, `--sans-son`, `--hd`, `--msaa`, `--carte-zoom`, `--volume-musique`, `--volume-bruitages` (elles passent avant les réglages du menu).

## Où en est-on
Voir [`docs/notes-visionneuse-dq4-pc.md`](docs/notes-visionneuse-dq4-pc.md) (état, protocole, « reste à faire ») et [`docs/notes-technique-portage-dq4.md`](docs/notes-technique-portage-dq4.md) (architecture du jeu, protocole moteur → Unity). L'historique des étapes est dans [`docs/historique.md`](docs/historique.md). La manière de travailler est dans [`docs/workflow.md`](docs/workflow.md).
