# Plan du code (rangement du 04/11/2026)

Ce document dit **où est quoi** depuis le rangement du projet (issue #196 : dossiers, fenêtre découpée par thème, dossier `donnees`). Rien n'a changé dans le fonctionnement du jeu : les 254 fonctions de l'ancienne classe `Jeu` sont strictement identiques (vérifié par comparaison de l'arbre syntaxique avant / après).

## 1. Vue d'ensemble

```
dq4-portage\
  lancer_dq4.bat          le SEUL lanceur (double-clic) ; reprend d'abord tes anciens fichiers dans donnees\
  donnees\                tout ce qui est à toi (jamais envoyé sur GitHub), voir § 2
  dq4_pc\                 le code du portage (rien que du code)
    __main__.py           `python -m dq4_pc` lance le jeu
    principal.py          lecture des arguments de la ligne de commande, puis ouverture de la fenêtre
    chemins.py            TOUS les dossiers et fichiers (un seul endroit) + reprise de l'ancienne disposition
    son.py                musiques et bruitages d'origine (conteneur AKB)
    noyau\                le jeu d'origine émulé et ce qu'on en lit
    monde\                cartes, décors, sprites, modèles 3D : lecture et préparation
    rendu\                rendu hors écran (anticrénelage…), ciel du titre
    combat\               tout ce qui est propre au combat (hors fenêtre)
    menus\                fenêtres d'origine, menu Paramètres, historique, boutons à l'écran, avant la partie
    persistance\          réglages, sauvegardes, états instantanés
    fenetre\              la fenêtre pyglet : classe `Jeu` en plusieurs modules par thème
  tests\                  les tests (test_*.py) et leur petite aide (_chemins.py)
  outils\                 outils de travail : lecture de la mise en page des menus, scripts de session, recherche non maintenue
  docs\                   notes, audit, décisions, ce plan
```

### `dq4_pc\noyau\` : le moteur du jeu d'origine
| Module | Rôle |
|---|---|
| `emu_core.py` | chargeur ELF AArch64 + Unicorn qui exécute `libdq4core.so` (jamais modifié) |
| `moteur.py` | pilotage du moteur : `Moteur` (pas, crochets), `Etat` (ce qu'on décode des paquets : caméra, sprites, fondus…), `Interface` (mémoire des fenêtres de menu) |
| `pktlog.py` | journal des paquets moteur → Unity |
| `rencontres.py` | rencontres aléatoires, horloge jour / nuit, vitesse de marche |
| `priorite_jeu.py` | « le jeu l'emporte sur les réglages du joueur » (valeur imposée par un script) |
| `pose_couchee.py` | poses couchées des personnages de ville (paquets 16 à 18) |
| `historique.py` | capteur des dialogues (crochet du moteur) + favoris |
| `suivi_charge.py` | journal de démarrage (diagnostic) |

### `dq4_pc\monde\` : cartes, décors, sprites
`donnees.py` (lecture des données Unity avec UnityPy, cache), `fld.py` (format des cartes), `fbx.py` (modèles 3D animés), `objets_carte.py` (objets animés des cartes), `hd.py` (agrandissement EPX des sprites), `decors_plats.py` (scintillement des décors plats), `contours_decor.py`, `teinte_carte.py` (jour / nuit).

### `dq4_pc\rendu\`
`postfx.py` (rendu hors écran : MSAA, suréchantillonnage, netteté, luminosité), `ciel_titre.py` (ciel de l'écran-titre en 16/9 ; copies de ciel décalées ou en miroir), `effets_capture.py` (squelette de la classe `Capture` du jeu : constantes, boucle de pas), `effet_tabi.py` (voyage, ailes de Chimère), `effet_lampe.py` (Ranaruta), `effet_riremito.py` (Riremito) : effets d'écran du paquet 34, modules purs.

### `dq4_pc\combat\`
`effet_combat.py` (effet de début de combat), `vitesse_combat.py` (horloge du moteur pendant un combat), `historique_combat.py` (résultats de combat pour l'historique). La partie « fenêtre » du combat est dans `fenetre\scene_combat.py`.

### `dq4_pc\menus\`
`ui_menu.py` (fenêtres d'origine : mise en page lue dans le code C# du jeu), `pause.py` (menu Paramètres, Échap), `ui_historique.py` (fenêtre Historique), `hud_mobile.py` (boutons et croix tactiles), `avant_partie.py` (logos, titre, licence), `saisie_nom.py` (nom du héros), `ecran_sauvegardes.py` (export / import).

### `dq4_pc\persistance\`
`reglages.py` (réglages du joueur, `reglages.json`), `sauvegardes.py` (export / import des `data*.dat`), `etats.py` (états instantanés ; relit aussi les états d'avant le rangement).

### `dq4_pc\fenetre\` : la fenêtre
La classe `Jeu` (fenêtre pyglet) est assemblée à partir de dix morceaux (« mixins »), un par thème, pour qu'un fichier ne dépasse pas ~650 lignes :

| Module | Contenu |
|---|---|
| `jeu.py` | le cœur : constructeur, boucle du moteur (`_boucle`, `tick`), `on_draw`, dessin de la scène, démarrage, fermeture, retour au titre |
| `plein_ecran.py` | plein écran / fenêtre, résolution, moniteurs, journal des erreurs de bascule |
| `camera.py` | caméra des villes (celle du jeu + la rotation gauche / droite du joueur : flèches, clic molette, recentrage, effacée en douceur dans les scènes : D-233) / du combat / du titre, bords des sprites ; plus de zoom ni d'inclinaison (D-226) |
| `champ.py` | terrain : cartes, décors, sprites, ombres, carte du monde, icônes de lieux |
| `scene_combat.py` | combat : monstres, fond, effets, nombres de dégâts, vitesse et pas du moteur en combat |
| `titre.py` | écran-titre (ciel, logo), ciel prolongé de `dpout` et `ev09`, licence, saisie du nom, écran Sauvegardes |
| `affichage_menus.py` | messages, fenêtres de menu du jeu, éditeur d'interface, fondus, vignette, petits messages |
| `clavier_souris.py` | touches, souris, manette : tous les `on_*` d'entrée |
| `instantanes.py` | états instantanés (enregistrer / charger) |
| `effets_capture.py` | effets d'écran du voyage, de la lampe et de Riremito : capture de l'écran, deux textures de flou, dessin du maillage de l'effet (l'interface reste par-dessus) |
| `options.py` | réglages du joueur appliqués au jeu en cours (son, texte, défilement, vitesse de combat) |
| `constantes.py`, `shaders.py`, `aides.py` | constantes, programmes GLSL, petites fonctions sans état |
| `entrees.py`, `ecrans.py` | logique pure (sans fenêtre), testée seule : gestes souris / clavier, A -> toucher d'écran du don d'expérience (#262) ; moniteurs |

Règles : un module de `fenetre\` n'importe jamais `jeu.py` (pas de cycle) ; il passe par `self`. `from dq4_pc.fenetre import jeu as F` donne aussi accès aux constantes et fonctions (`F.SPRITE_ECHELLE`…), pour les tests et les outils.

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
Tout est défini dans `dq4_pc\chemins.py`. Variables d'environnement : `DQ4_DONNEES` (autre emplacement du dossier `donnees`), `DQ4_JEUX` (ancien fonctionnement : un dossier `jeux\DQ4` avec `patched_apks` et `saves`). Les options `--apk`, `--saves-lecture`, `--saves-ecriture`, `--cache`, `--reglages`, `--historique` restent.

**Reprise de l'ancienne disposition** (`chemins.migrer`, lancée par `lancer_dq4.bat` puis par le jeu ; **une seule fois par étape**, notée dans `donnees\reprise.json`, D-235) : `jeux\DQ4\patched_apks` → `donnees\apk` (copie) ; `jeux\DQ4\saves\<date la plus récente>` et `dq4_pc\sauvegardes` → `donnees\sauvegardes\{data*.dat,etats,avant_import_…}` (copie, un seul dossier depuis D-232) ; `donnees\sauvegardes\portage` et `\mobile\<date>` (disposition du 04/11) → remontés dans `donnees\sauvegardes` puis déplacés dans `avant_rangement_<date>` ; `dq4_pc\reglages.json`, `historique_favoris.json`, `historique_messages.json` → `donnees\reglages` (copie) ; `dq4_pc\erreurs_fenetre.log` → `donnees\journaux` (copie) ; `dq4_pc\cache` → `donnees\cache` (déplacé d'un coup : il pèse plusieurs centaines de Mo). Rien n'est supprimé ni écrasé : les anciens dossiers restent en place et peuvent être effacés à la main quand tu as vérifié.

## 3. Correspondance ancien nom → nouveau
| Avant | Maintenant |
|---|---|
| `dq4_pc\lancer_dq4.bat` | `lancer_dq4.bat` (racine ; l'ancien fichier est supprimé, depuis #258 : un raccourci qui pointait dessus est à refaire vers la racine) |
| `dq4_pc\fenetre.py` | dossier `dq4_pc\fenetre\` (voir plus haut) ; `main()` → `dq4_pc\principal.py` ; `trouver_defauts()` → `dq4_pc\chemins.py` |
| `dq4_pc\emu_core.py`, `moteur.py`, `pktlog.py`, `rencontres.py`, `priorite_jeu.py`, `suivi_charge.py`, `pose_couchee.py`, `historique.py` | `dq4_pc\noyau\…` (même nom) |
| `dq4_pc\effet_combat.py`, `vitesse_combat.py`, `historique_combat.py` | `dq4_pc\combat\…` |
| `dq4_pc\donnees.py`, `fld.py`, `fbx.py`, `hd.py`, `objets_carte.py`, `decors_plats.py`, `contours_decor.py`, `teinte_carte.py` | `dq4_pc\monde\…` |
| `dq4_pc\postfx.py`, `ciel_titre.py` | `dq4_pc\rendu\…` |
| `dq4_pc\ui_menu.py`, `pause.py`, `ui_historique.py`, `hud_mobile.py`, `ecran_sauvegardes.py`, `avant_partie.py`, `saisie_nom.py` | `dq4_pc\menus\…` |
| `dq4_pc\reglages.py`, `sauvegardes.py`, `etats.py` | `dq4_pc\persistance\…` |
| `dq4_pc\entrees.py`, `ecrans.py` | `dq4_pc\fenetre\…` |
| `dq4_pc\son.py` | inchangé |
| `outils\test_*.py` | `tests\test_*.py` (lancer depuis la racine : `PYGLET_HEADLESS=1 python3 tests/test_X.py`) |
| `dq4_pc\cache`, `dq4_pc\sauvegardes`, `dq4_pc\reglages.json`, `dq4_pc\historique_*.json`, `jeux\DQ4\…` | `donnees\…` |

Les anciens numéros de ligne cités dans les notes (`fenetre.py:1234`) ne valent plus : chercher le nom de la fonction (`grep -rn "def _camera_ville" dq4_pc`).

## 4. Lancer, tester, ajouter
- **Jeu** : `lancer_dq4.bat`, ou à la main depuis la racine : `python -m dq4_pc [options]`.
- **Tests** : toujours depuis la racine, en script : `PYGLET_HEADLESS=1 python3 tests/test_X.py` ; `outils/flux_session/lancer_tests.sh` lance toute la suite. Un test qui remplace un « global » de la fenêtre (`time`, `gl`, une constante de caméra…) le fait par `_chemins.poser_global(nom, valeur)` (il agit sur tous les modules de `dq4_pc.fenetre`, comme le faisait l'ancien fichier unique) ; un test qui lit le texte du code utilise `_chemins.source('fenetre.py')` (tout l'ancien fichier) ou `_chemins.source('pause.py')`.
- **Nouveau module** : dans le dossier du thème ; imports en `from dq4_pc.<dossier> import <module> as XX` (les alias `MO`, `RG`, `PA`, `UM`, `HM`… sont conservés) ; aucune importation circulaire.
- **Nouveau chemin de fichier** : dans `dq4_pc\chemins.py` (classe `Dossiers`), jamais en dur ailleurs.
