# Plan du code (rangement du 04/11/2026)

Ce document dit **où est quoi** depuis le rangement du projet (issue #196 : dossiers, fenêtre découpée par thème, dossier `donnees`). Rien n'a changé dans le fonctionnement du jeu : les 254 fonctions de l'ancienne classe `Game` sont strictement identiques (vérifié par comparaison de l'arbre syntaxique avant / après).

## 1. Vue d'ensemble

```
dq4-portage\
  launch_dq4.bat          le SEUL lanceur (double-clic) ; reprend d'abord tes anciens fichiers dans donnees\
  donnees\                tout ce qui est à toi (jamais envoyé sur GitHub), voir § 2
  dq4_pc\                 le code du portage (rien que du code)
    __main__.py           `python -m dq4_pc` lance le jeu
    main.py               lecture des arguments de la ligne de commande, puis ouverture de la fenêtre
    paths.py              TOUS les dossiers et fichiers (un seul endroit) + reprise de l'ancienne disposition
    sound.py              musiques et bruitages d'origine (conteneur AKB)
    language.py           langue de l'outil (français / anglais) : `tr('texte français')`, `N_()`, réglage « Langue » (D-238)
    texts_en\             les traductions anglaises (un `EN = {texte français: anglais}` par thème : pause, menus, window, divers)
    core\                 le jeu d'origine émulé et ce qu'on en lit
    world\                cartes, décors, sprites, modèles 3D : lecture et préparation
    render\               rendu hors écran (anticrénelage…), ciel du titre
    battle\               tout ce qui est propre au combat (hors fenêtre)
    menus\                fenêtres d'origine, menu Paramètres, historique, boutons à l'écran, avant la partie
    persistence\          réglages, sauvegardes, états instantanés
    window\               la fenêtre pyglet : classe `Game` en plusieurs modules par thème
  tests\                  les tests (test_*.py) et leur petite aide (_paths.py)
  tools\                 outils de travail : lecture de la mise en page des menus, scripts de session, recherche non maintenue
  docs\                   notes, audit, décisions, ce plan
```

### `dq4_pc\core\` : le moteur du jeu d'origine
| Module | Rôle |
|---|---|
| `emu_core.py` | chargeur ELF AArch64 + Unicorn qui exécute `libdq4core.so` (jamais modifié) |
| `engine.py` | pilotage du moteur : `Engine` (pas, crochets, boutons de caméra du jeu : `camera_wait`, `camera_turn`), `State` (ce qu'on décode des paquets : caméra, sprites, fondus…), `Interface` (mémoire des fenêtres de menu) |
| `pktlog.py` | journal des paquets moteur → Unity |
| `encounters.py` | rencontres aléatoires, horloge jour / nuit, vitesse de marche |
| `game_priority.py` | « le jeu l'emporte sur les réglages du joueur » (valeur imposée par un script) |
| `lying_pose.py` | poses couchées des personnages de ville (paquets 16 à 18) |
| `history.py` | capteur des dialogues (crochet du moteur) + favoris |
| `load_tracking.py` | journal de démarrage (diagnostic) |

### `dq4_pc\world\` : cartes, décors, sprites
`data.py` (lecture des données Unity avec UnityPy, cache), `fld.py` (format des cartes), `fbx.py` (modèles 3D animés), `map_objects.py` (objets animés des cartes), `hd.py` (agrandissement EPX des sprites), `flat_sceneries.py` (scintillement des décors plats), `scenery_outlines.py`, `map_tint.py` (jour / nuit).

### `dq4_pc\render\`
`postfx.py` (rendu hors écran : MSAA, suréchantillonnage, netteté, luminosité), `title_sky.py` (ciel de l'écran-titre en 16/9 ; copies de ciel décalées ou en miroir), `capture_effects.py` (squelette de la classe `Capture` du jeu : constantes, boucle de pas), `tabi_effect.py` (voyage, ailes de Chimère), `lamp_effect.py` (Ranaruta), `riremito_effect.py` (Riremito) : effets d'écran du paquet 34, modules purs.

### `dq4_pc\battle\`
`battle_effect.py` (effet de début de combat), `battle_speed.py` (horloge du moteur pendant un combat), `battle_history.py` (résultats de combat pour l'historique). La partie « fenêtre » du combat est dans `window\battle_scene.py`.

### `dq4_pc\menus\`
`ui_menu.py` (fenêtres d'origine : mise en page lue dans le code C# du jeu), `pause.py` (menu Paramètres, Échap), `ui_history.py` (fenêtre Historique), `hud_mobile.py` (boutons et croix tactiles), `pre_game.py` (logos, titre, licence), `name_entry.py` (nom du héros), `saves_screen.py` (export / import).

### `dq4_pc\persistence\`
`settings.py` (réglages du joueur, `reglages.json`), `saves.py` (export / import des `data*.dat`), `savestates.py` (états instantanés ; relit aussi les états d'avant le rangement).

### `dq4_pc\window\` : la fenêtre
La classe `Game` (fenêtre pyglet) est assemblée à partir de dix morceaux (« mixins »), un par thème, pour qu'un fichier ne dépasse pas ~650 lignes :

| Module | Contenu |
|---|---|
| `game.py` | le cœur : constructeur, boucle du moteur (`_loop`, `tick`), `on_draw`, dessin de la scène, démarrage, fermeture, retour au titre |
| `full_screen.py` | plein écran / fenêtre, résolution, moniteurs, journal des erreurs de bascule |
| `camera.py` | caméra des villes (celle du jeu, rotation comprise : flèches, clic molette et recentrage envoient au moteur les boutons de caméra du jeu, qui tourne lui-même : D-234 ; entre deux pas, interpolation en arc autour de la cible) / du combat / du titre, bords des sprites ; plus de zoom ni d'inclinaison (D-226) |
| `field.py` | terrain : cartes, décors, sprites, ombres, carte du monde, icônes de lieux |
| `battle_scene.py` | combat : monstres, fond, effets, nombres de dégâts, vitesse et pas du moteur en combat |
| `title_screen.py` | écran-titre (ciel, logo), ciel prolongé de `dpout` et `ev09`, licence, saisie du nom, écran Sauvegardes |
| `menu_display.py` | messages, fenêtres de menu du jeu, éditeur d'interface, fondus, vignette, petits messages |
| `keyboard_mouse.py` | touches, souris, manette : tous les `on_*` d'entrée |
| `snapshots.py` | états instantanés (enregistrer / charger) |
| `capture_effects.py` | effets d'écran du voyage, de la lampe et de Riremito : capture de l'écran, deux textures de flou, dessin du maillage de l'effet (l'interface reste par-dessus) |
| `options.py` | réglages du joueur appliqués au jeu en cours (son, texte, défilement, vitesse de combat) |
| `constants.py`, `shaders.py`, `helpers.py` | constantes, programmes GLSL, petites fonctions sans état |
| `inputs.py`, `screens.py` | logique pure (sans fenêtre), testée seule : gestes souris / clavier, A -> toucher d'écran du don d'expérience (#262) ; moniteurs |

Règles : un module de `window\` n'importe jamais `game.py` (pas de cycle) ; il passe par `self`. `from dq4_pc.window import game as F` donne aussi accès aux constantes et fonctions (`F.SPRITE_SCALE`…), pour les tests et les tools.

## 2. Tes fichiers : `donnees\`
```
donnees\
  apk\                       les 3 APK français (base.apk, split_config.arm64_v8a.apk, split_UnityDataAssetPack.apk)
  sauvegardes\              UN SEUL dossier (D-232) : le contenu du .zip d'export
    data1.dat … data5.dat, data9.dat    les journaux du jeu (lus et écrits par le moteur ; ceux du téléphone se copient ici)
    etats\                   les états instantanés (etat_01.dqs…)
    avant_import_<date>\     copies de sécurité faites avant chaque import de sauvegardes
    avant_rangement_<date>\  anciens dossiers portage\ et mobile\ rangés tels quels (sans danger à effacer)
  cache\                     ce que le portage calcule à partir des APK (sans danger à effacer ; il est refait)
  reglages\                  reglages.json, historique_favoris.json, historique_messages.json
  journaux\                  erreurs_fenetre.log
  reprise.json               les étapes de la reprise de l'ancienne disposition déjà faites (D-235 : elle ne se refait pas)
```
Tout est défini dans `dq4_pc\paths.py`. Variables d'environnement : `DQ4_DONNEES` (autre emplacement du dossier `donnees`), `DQ4_JEUX` (ancien fonctionnement : un dossier `jeux\DQ4` avec `patched_apks` et `saves`). Les options `--apk`, `--saves-lecture`, `--saves-ecriture`, `--cache`, `--reglages`, `--historique` restent.

**Reprise de l'ancienne disposition** (`paths.migrate`, lancée par `launch_dq4.bat` puis par le jeu ; **une seule fois par étape**, notée dans `donnees\reprise.json`, D-235) : `jeux\DQ4\patched_apks` → `donnees\apk` (copie) ; `jeux\DQ4\saves\<date la plus récente>` et `dq4_pc\sauvegardes` → `donnees\sauvegardes\{data*.dat,etats,avant_import_…}` (copie, un seul dossier depuis D-232) ; `donnees\sauvegardes\portage` et `\mobile\<date>` (disposition du 04/11) → remontés dans `donnees\sauvegardes` puis déplacés dans `avant_rangement_<date>` ; `dq4_pc\reglages.json`, `historique_favoris.json`, `historique_messages.json` → `donnees\reglages` (copie) ; `dq4_pc\erreurs_fenetre.log` → `donnees\journaux` (copie) ; `dq4_pc\cache` → `donnees\cache` (déplacé d'un coup : il pèse plusieurs centaines de Mo). Rien n'est supprimé ni écrasé : les anciens dossiers restent en place et peuvent être effacés à la main quand tu as vérifié.

## 3. Correspondance ancien nom → nouveau
| Avant | Maintenant |
|---|---|
| `dq4_pc\launch_dq4.bat` | `launch_dq4.bat` (racine ; l'ancien fichier est supprimé, depuis #258 : un raccourci qui pointait dessus est à refaire vers la racine) |
| `dq4_pc\fenetre.py` | dossier `dq4_pc\window\` (voir plus haut) ; `main()` → `dq4_pc\main.py` ; `trouver_defauts()` → `dq4_pc\paths.py` |
| `dq4_pc\emu_core.py`, `engine.py`, `pktlog.py`, `encounters.py`, `game_priority.py`, `load_tracking.py`, `lying_pose.py`, `history.py` | `dq4_pc\core\…` (même nom) |
| `dq4_pc\effet_combat.py`, `battle_speed.py`, `battle_history.py` | `dq4_pc\battle\…` |
| `dq4_pc\donnees.py`, `fld.py`, `fbx.py`, `hd.py`, `map_objects.py`, `flat_sceneries.py`, `scenery_outlines.py`, `map_tint.py` | `dq4_pc\world\…` |
| `dq4_pc\postfx.py`, `title_sky.py` | `dq4_pc\render\…` |
| `dq4_pc\ui_menu.py`, `pause.py`, `ui_history.py`, `hud_mobile.py`, `saves_screen.py`, `pre_game.py`, `name_entry.py` | `dq4_pc\menus\…` |
| `dq4_pc\reglages.py`, `saves.py`, `savestates.py` | `dq4_pc\persistence\…` |
| `dq4_pc\entrees.py`, `screens.py` | `dq4_pc\window\…` |
| `dq4_pc\sound.py` | inchangé |
| `tools\test_*.py` | `tests\test_*.py` (lancer depuis la racine : `PYGLET_HEADLESS=1 python3 tests/test_X.py`) |
| `dq4_pc\cache`, `dq4_pc\sauvegardes`, `dq4_pc\reglages.json`, `dq4_pc\historique_*.json`, `jeux\DQ4\…` | `donnees\…` |

Les anciens numéros de ligne cités dans les notes (`window.py:1234`) ne valent plus : chercher le nom de la fonction (`grep -rn "def _camera_ville" dq4_pc`).

## 3 bis. Passage à l'anglais (05/11/2026, #290)
Tous les dossiers, fichiers et noms du code sont maintenant en anglais (les noms de ce document le sont déjà). Les noms d'avant (`dq4_pc\noyau`, `fenetre`, `Moteur`, `Etat`, `Jeu`…) se retrouvent dans [`rename_map.md`](rename_map.md) (dossiers et fichiers) et [`rename_identifiers.tsv`](rename_identifiers.tsv) (identifiants). Les tableaux du § 3 gardent les noms d'avant le 05/11 dans la colonne « Avant ».

## 4. Lancer, tester, ajouter
- **Jeu** : `launch_dq4.bat`, ou à la main depuis la racine : `python -m dq4_pc [options]`.
- **Tests** : toujours depuis la racine, en script : `PYGLET_HEADLESS=1 python3 tests/test_X.py` ; `tools/session_flow/run_tests.sh` lance toute la suite. Un test qui remplace un « global » de la fenêtre (`time`, `gl`, une constante de caméra…) le fait par `_paths.set_global(name_str, value)` (il agit sur tous les modules de `dq4_pc.window`, comme le faisait l'ancien fichier unique) ; un test qui lit le texte du code utilise `_paths.source('window.py')` (tout l'ancien fichier) ou `_paths.source('pause.py')`.
- **Nouveau module** : dans le dossier du thème ; imports en `from dq4_pc.<folder> import <module> as XX` (les alias `ENGINE`, `RG`, `PA`, `UM`, `HM`… sont conservés) ; aucune importation circulaire.
- **Nouveau chemin de fichier** : dans `dq4_pc\paths.py` (classe `Folders`), jamais en dur ailleurs.
