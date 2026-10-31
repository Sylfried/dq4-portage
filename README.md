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

Touches par défaut (modifiables dans le menu Échap > Commandes ; **F1** = infos à l'écran, réattribuable aussi) : **Z Q S D** (se déplacer, par rapport à la caméra), **Flèches ← →** (tourner la caméra des villes, donjons et tours, comme sur mobile), **Flèches ↑ ↓** (relever / abaisser l'angle de la caméra ; appuyer sur les deux flèches d'une même direction recentre la caméra en douceur, par le plus court chemin : 1° plutôt que 359° ; sur la carte du monde la vue reste de dessus, sans rotation ni inclinaison), **Espace** (bouton d'action : parler, examiner, ouvrir un coffre, casser un tonneau ou une jarre, valider), **Alt / Alt Gr** (discussion de groupe), **Entrée** (ouvre le menu de commandes hors combat, valide dans un menu), **Retour arrière** (annuler / retour), **M** (carte), **Maj** (courir, maintenu ; « Courir (appuyer) » : une touche à attribuer qui active la course jusqu'à un nouvel appui ; la course n'accélère que le héros : les PNJ gardent leur vitesse et leurs animations), **Maj + touche de la caméra** (accélère la caméra : « Accélérer la caméra (maintenir) » / « (appuyer) », les deux Maj par défaut, multiplicateur de 1 à 4 dans Commandes), **Ctrl + touche de la caméra** (« Touche spéciale », réattribuable : remet la caméra à zéro dans tous les sens ; les lieux dont le jeu verrouille la caméra ne tournent pas), **A / Page haut** et **R / Page bas** (page précédente / suivante des menus). **Boutons de la version mobile à l'écran** (Carte, Mode de la carte (seulement carte ouverte : passe de la vue détaillée à la carte du monde entière, avec ses zones non explorées grisées et ses lieux rouges clignotants), Commandes, Discussion de groupe, sur des plaques comme dans la version mobile ; clic de souris). **Éditeur d'interface** (menu Échap > Commandes > Interface) : afficher / masquer l'interface à l'écran, liste déroulante de tout ce qu'on peut modifier (boutons de l'écran et toutes les fenêtres du jeu : dialogues, menus, magasins, combat...), taille et position de chaque élément avec aperçu, placement des boutons et des fenêtres par glisser-déposer, avec grille (affichage et aimantation au choix) pour toutes les interfaces. **Chiffres 1 à 9 et 0 = enregistrer l'état instantané n° 1 à 10, Ctrl + chiffre = le charger, Ctrl + Maj = annuler le dernier chargement.** **Échap = menu** (reprendre, **États** (un seul menu : créer, charger ou supprimer un état instantané, avec miniature et confirmation de la suppression), **Affichage** : plein écran, résolution de 720p à 4K, shader (style des sprites et du décor, pixel perfect...), lissage, distance de la caméra de 50 à 200 % (indépendante du shader), caméra centrée sur le héros (même près du bord de la carte), effet de vignetage, anticrénelage ; **Son** ; **Commandes** : interface (boutons à l'écran), touches de déplacement et de caméra, vitesse de déplacement et de la caméra (0,5 à 2), multiplicateur de la course (1 à 2 ; 1,5 par défaut), compagnons à distance constante en courant (essai, désactivé par défaut), accélération de la caméra comme la course, vitesse des transitions (0,5 à 2), touches des actions du jeu, avec une barre de défilement quand la liste ne tient pas ; chaque touche se remet à celle d'origine avec le bouton ↺ de sa ligne (ou Début) et chaque case se vide avec sa croix rouge (ou Suppr) ; quitter : Oui / Non). Les fenêtres du menu sont noires, avec le curseur doré du jeu ; le bouton retour du jeu (en bas à droite de la fenêtre) remonte d'un cran, comme Échap, Retour arrière ou le clic droit. Les curseurs se règlent en glissant, aux flèches ou en cliquant sur la valeur pour la taper ; le bouton ↺ à droite du curseur (ou Suppr) remet la valeur par défaut. La molette de la souris règle aussi la distance de la caméra. **F1 = infos seulement.** Les réglages sont enregistrés dans `dq4_pc\reglages.json`, les états dans `dq4_pc\sauvegardes\etats\` ; ils ne contiennent aucun fichier du jeu. Options de la ligne de commande : `--reglages fichier.json`, `--sans-son`, `--hd`, `--msaa`, `--carte-zoom` (zoom de 0,5 à 2 ; 1 = distance de la caméra à 100 %), `--volume-musique`, `--volume-bruitages` (elles passent avant les réglages du menu).

## Où en est-on
Voir [`docs/notes-visionneuse-dq4-pc.md`](docs/notes-visionneuse-dq4-pc.md) (état, protocole, « reste à faire ») et [`docs/notes-technique-portage-dq4.md`](docs/notes-technique-portage-dq4.md) (architecture du jeu, protocole moteur → Unity). L'historique des étapes est dans [`docs/historique.md`](docs/historique.md). La manière de travailler est dans [`docs/workflow.md`](docs/workflow.md).
