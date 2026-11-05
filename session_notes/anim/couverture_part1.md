# Couverture des animations de combat des alliés (05/11/2026)

Sources : moteur natif réel sous Unicorn (`libdq4core.so`, sauvegarde du chapitre 1), visionneuse réelle sous Xvfb, tables du moteur, fichiers de textes du patch. Aucune modification du dépôt. Détail des méthodes en fin de fichier.

Légende des états : **OK** = tout ce que le moteur envoie est dessiné ; **partiel** = une partie seulement ; **ABSENT** = rien de visuel ; **rien à dessiner** = le moteur ne demande aucun effet (identique au jeu).

## 1. Sorts et techniques des alliés (actions apprises, table des niveaux du moteur)

Lanceurs : numéros de joueur du moteur (1 Héros, 2 Héroïne, 3 Ragnar, 4 Alina, 5 Kiryl, 6 Borya, 7 Torneko, 8 Mina, 9 Maya, 25 Psaro ; noms lus dans `b1001000.mpt`). « Effet » = identifiant demandé à `BattleEffectManager::setupEffect` (confirmé en combat réel pour chaque action : colonne vérifiée = oui).

| Action | Nom (patch FR) | Lanceurs | Effet | Ressources envoyées au viewer | Rendu viewer | Vérifié en combat réel |
|---|---|---|---|---|---|---|
| 1 | Flamme | Héros, Héroïne, Maya | 1 | maillage m5001 ; teinte plein écran (19 paquets 33) ; SE 511 | OK : maillage dessiné ; capture réelle : maillage vu sur 8 des 10 images prises, remplissage max 83 % | oui |
| 2 | Superflamme | Maya | 2 | maillage m5002 ; teinte plein écran (33 paquets 33) ; SE 512 | OK : maillage dessiné ; capture réelle : maillage vu sur 9 des 10 images prises, remplissage max 61 % | oui |
| 3 | Mégaflamme | Maya | 3 | maillage m5003 ; fbx c3 ; teinte plein écran (37 paquets 33) ; SE 513 | **partiel** : maillage dessiné, fbx non dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 59 % | oui |
| 4 | Crame | Héros, Héroïne, Maya | 4 | maillage m5004 ; SE 514 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 36 % | oui |
| 5 | Supercrame | Maya | 5 | maillage m5005 ; SE 515 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 43 % | oui |
| 6 | Mégacrame | Maya | 6 | maillage m5006 ; SE 516 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 58 % | oui |
| 7 | Bang | Maya | 7 | maillage m5007 ; teinte plein écran (18 paquets 33) ; SE 517 | OK : maillage dessiné ; capture réelle : maillage vu sur 5 des 10 images prises, remplissage max 99 % | oui |
| 8 | Superbang | Héros, Héroïne, Maya | 8 | maillage m5008 ; teinte plein écran (22 paquets 33) ; SE 518 | OK : maillage dessiné ; capture réelle : maillage vu sur 7 des 10 images prises, remplissage max 62 % | oui |
| 9 | Mégabang | Maya, Psaro | 9 | maillage m5009 ; teinte plein écran (16 paquets 33) ; SE 519 | OK : maillage dessiné ; capture réelle : maillage vu sur 10 des 10 images prises, remplissage max 64 % | oui |
| 10 | Tornade | Mina | 14 | fbx c14 ; teinte plein écran (12 paquets 33) ; SE 520 | **ABSENT** : fbx seul, jamais dessiné (seule la teinte plein écran est jouée) | oui |
| 11 | Supertornade | Mina | 15 | fbx c15 ; teinte plein écran (20 paquets 33) ; SE 521 | **ABSENT** : fbx seul, jamais dessiné (seule la teinte plein écran est jouée) | oui |
| 12 | Mégatornade | Mina | 16 | fbx c16 ; teinte plein écran (25 paquets 33) ; SE 522 | **ABSENT** : fbx seul, jamais dessiné (seule la teinte plein écran est jouée) | oui |
| 13 | Glace | Borya | 10 | fbx c10 ; SE 523 | **ABSENT** : fbx seul, jamais dessiné (rien d'affiché, seulement le son) | oui |
| 14 | Superglace | Borya | 11 | fbx c11 ; SE 524 | **ABSENT** : fbx seul, jamais dessiné (rien d'affiché, seulement le son) | oui |
| 15 | Mégaglace | Borya | 12 | fbx c12 ; SE 525 | **ABSENT** : fbx seul, jamais dessiné (rien d'affiché, seulement le son) | oui |
| 16 | Gigaglace | Borya, Psaro | 13 | fbx c13 ; SE 526 | **ABSENT** : fbx seul, jamais dessiné (rien d'affiché, seulement le son) | oui |
| 17 | Foudre | Héros, Héroïne | 17 | maillage m5017 ; teinte plein écran (13 paquets 33) ; SE 527 | OK : maillage dessiné ; capture réelle : maillage vu sur 4 des 10 images prises, remplissage max 32 % | oui |
| 18 | Superfoudre | Héros, Héroïne | 18 | maillage m5018 ; teinte plein écran (17 paquets 33) ; SE 528 | OK : maillage dessiné ; capture réelle : maillage vu sur 5 des 10 images prises, remplissage max 27 % | oui |
| 19 | Foudre ciblée | Héros, Héroïne | 19 | maillage m5019 ; teinte plein écran (37 paquets 33) ; SE 529 | OK : maillage dessiné ; capture réelle : maillage vu sur 10 des 10 images prises, remplissage max 38 % | oui |
| 20 | Kill | Kiryl | 21 | maillage m5021 ; teinte plein écran (19 paquets 33) ; SE 530 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 75 % | oui |
| 22 | Superkill | Kiryl | 22 | maillage m5022 ; teinte plein écran (20 paquets 33) ; SE 531 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 76 % | oui |
| 24 | Mégakill | Psaro | 23 | maillage m5023 ; teinte plein écran (20 paquets 33) ; SE 531 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 91 % | oui |
| 26 | Zap | Héros, Héroïne | 24 | maillage m5024 ; SE 533 | OK : maillage dessiné ; capture réelle : maillage vu sur 4 des 4 images prises, remplissage max 65 % | oui |
| 28 | Torpeur | Borya, Mina | 25 | maillage m5025 ; SE 535 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 70 % | oui |
| 29 | Torpeur ciblée | Héros, Héroïne, Mina, Psaro | 26 | maillage m5026 ; SE 536 | OK : maillage dessiné ; capture réelle : maillage vu sur 8 des 10 images prises, remplissage max 75 % | oui |
| 30 | Antimagie | Kiryl | 27 | maillage m5027 ; SE 537 | OK : maillage dessiné ; capture réelle : maillage vu sur 5 des 10 images prises, remplissage max 61 % | oui |
| 31 | Illusion | Kiryl | 28 | maillage m5028 ; SE 538 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 47 % | oui |
| 32 | Confusion | Borya | 29 | maillage m5029 ; SE 539 | OK : maillage dessiné ; capture réelle : maillage vu sur 7 des 10 images prises, remplissage max 60 % | oui |
| 34 | Aspirmagie | Borya, Maya | 30 | maillage m5030 ; SE 540 | OK : maillage dessiné ; capture réelle : maillage vu sur 7 des 10 images prises, remplissage max 69 % | oui |
| 35 | Réflexion | Borya | aucun | SE 541 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 37 | Altération | Borya, Maya | 31 | maillage m5031 ; SE 503 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 58 % | oui |
| 38 | Mégaltération | Borya, Psaro | 32 | maillage m5032 ; SE 503 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 53 % | oui |
| 39 | Protection | Kiryl | aucun | SE 502 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 42 | Mégaprotection | Kiryl | aucun | SE 502 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 43 | Isolation | Mina | aucun | SE 543 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 44 | Décuplo | Borya, Psaro | aucun | SE 544 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 47 | Pouf | Maya, Psaro | 34 | maillage m5034 ; SE 576 | OK : maillage dessiné ; capture réelle : maillage vu sur 10 des 10 images prises, remplissage max 61 % | oui |
| 48 | Immoblindage | Héros, Héroïne | aucun | SE 547 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 50 | Premiers secours | Héros, Héroïne, Kiryl, Mina | aucun | SE 501 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 53 | Soins partiels | Héros, Héroïne, Kiryl, Mina | aucun | SE 501 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 56 | Soins complets | Héros, Héroïne, Kiryl, Mina, Psaro | aucun | SE 501 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 59 | Multisoin | Kiryl, Psaro | aucun | SE 501 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 60 | Omnisoin | Héros, Héroïne | aucun | SE 501 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 61 | Rappel | Héros, Héroïne, Kiryl, Mina | aucun | SE 553 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 62 | Résurrection | Kiryl, Psaro | aucun | SE 553 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 63 | Conjuration | Mina | aucun | SE 501 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 65 | Stimulation | Mina | aucun | SE aucun | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 66 | Plouf-plouf | Héros, Héroïne | 35 | maillage m5035 ; couleur plein écran (30 paquets 25) ; SE 558 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 83 % | oui |
| 67 | Immunomagie | Héros, Héroïne | aucun | SE 559 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 68 | Accélération | Borya | aucun | SE 506 | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 70 | Cocorico | Héros, Héroïne | aucun | SE aucun | rien à dessiner (aucun effet demandé ; message + son) | oui |
| 106 | Perturbonde | Psaro | 43 | fbx c43 ; teinte plein écran (30 paquets 33) ; SE 562 | **ABSENT** : fbx seul, jamais dessiné (seule la teinte plein écran est jouée) | oui |
| 109 | Trou d'air | Psaro | 40 | fbx c40 ; teinte plein écran (18 paquets 33) ; SE 563 | **ABSENT** : fbx seul, jamais dessiné (seule la teinte plein écran est jouée) | oui |
| 127 | Explosion magique | Psaro | 42 | maillage m5042 ; fbx c42 ; teinte plein écran (49 paquets 33) ; SE 564 | **partiel** : maillage dessiné, fbx non dessiné ; capture réelle : maillage vu sur 10 des 10 images prises, remplissage max 49 % | oui |
| 128 | Orage d'éclairs | Psaro | 41 | maillage m5041 ; teinte plein écran (33 paquets 33) ; SE 565 | OK : maillage dessiné ; capture réelle : maillage vu sur 9 des 10 images prises, remplissage max 80 % | oui |
| 134 | Coupe claire | Psaro | 36 | maillage m5036 ; SE 566 | OK : maillage dessiné ; capture réelle : maillage vu sur 4 des 4 images prises, remplissage max 69 % | oui |
| 137 | Croissant lunaire | Psaro | 39 | fbx c39 ; teinte plein écran (15 paquets 33) ; SE 567 | **ABSENT** : fbx seul, jamais dessiné (seule la teinte plein écran est jouée) | oui |
| 140 | Lame du dragon | Psaro | 37 | maillage m5037 ; SE 568 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 43 % | oui |
| 142 | Lame de métal | Psaro | 38 | maillage m5038 ; SE 569 | OK : maillage dessiné ; capture réelle : maillage vu sur 3 des 10 images prises, remplissage max 28 % | oui |
| 151 | Gigalame | Héros, Héroïne | 20 | maillage m5020 ; fbx c20 ; teinte plein écran (60 paquets 33) ; SE 570 | **partiel** : maillage dessiné, fbx non dessiné ; capture réelle : maillage vu sur 2 des 10 images prises, remplissage max 48 % | oui |

Sorts de terrain (196-216 : Téléportation, Évac', Coup d'œil, Passage sûr, Protection sacrée, Tic-tac, Mappille, Détectrésor, Fouille, Discreto, Sifflet, soins du menu Magie) : aucun effet de combat (effet 0, pas de paquet), non utilisables au combat.

## 2. Attaques d'arme, critiques, esquives

| Cas | Action | Effet | Ressources | Rendu viewer |
|---|---|---|---|---|
| Attaque normale | 71 (« Attaquer ») | 300 + numéro de l'arme équipée (Ragnar, épée de cuivre n° 3 : effet 303 relevé en réel) ; mains nues : 343 / 345 d'après le désassemblage de `getWeaponEffectID` (non rejoué) | maillage m5301…m5345 (45 effets, tous présents) ; SE 410-454 selon l'arme | OK (maillages dessinés : audit du 05/11 et capture réelle de l'effet 303) |
| Variantes d'attaque | 231, 233, 234, 235 | 300 + arme (même message « attaque ! ») | idem | OK |
| Coup critique | 232 | arme + **344** demandés à la même image (« Coup critique ! ») | maillage m5344 ; SE 407 | OK (maillage m5344 dessiné) ; son 0 pour l'effet 344 lui-même |
| Esquive / « raté » | — | aucun effet demandé (messages seulement) | — | rien à dessiner |

## 3. Objets à effet utilisables en combat (20 objets du joueur ; chacun est joué dans le vrai moteur par l'action d'objet du numéro indiqué : out/forced_d.json)

| Objet (n°) | Action | Effet | Ressources | Rendu viewer |
|---|---|---|---|---|
| cartes argentées (9) | 328 | aucun | SE aucun | rien à dessiner (aucun effet demandé ; message + son) |
| boulier d'Astrae (13) | 330 | 24 | maillage m5024 ; SE 533 | OK : maillage dessiné ; capture réelle : maillage vu sur 4 des 4 images prises, remplissage max 65 % |
| bâton de foudre (18) | 331 | 5 | maillage m5005 ; SE 515 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 43 % |
| bâton du Courroux (23) | 332 | 15 | fbx c15 ; teinte plein écran (20 paquets 33) ; SE 521 | **ABSENT** : fbx seul, jamais dessiné (seule la teinte plein écran est jouée) |
| épée du Rêve (24) | 333 | 26 | maillage m5026 ; SE 536 | OK : maillage dessiné ; capture réelle : maillage vu sur 8 des 10 images prises, remplissage max 75 % |
| griffe de feu (26) | 334 | 5 | maillage m5005 ; SE 515 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 43 % |
| dague de glace (27) | 335 | 11 | fbx c11 ; SE 524 | **ABSENT** : fbx seul, jamais dessiné (rien d'affiché, seulement le son) |
| bâton d'antimagie (29) | 336 | 27 | maillage m5027 ; SE 537 | OK : maillage dessiné ; capture réelle : maillage vu sur 5 des 10 images prises, remplissage max 61 % |
| bâton de lave (30) | 337 | 7 | maillage m5007 ; teinte plein écran (18 paquets 33) ; SE 517 | OK : maillage dessiné ; capture réelle : maillage vu sur 5 des 10 images prises, remplissage max 99 % |
| épée du Massacre (31) | 338 | 32 | maillage m5032 ; SE 503 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 53 % |
| bâton du Salut (32) | 339 | 411 | modèle m5411 chargé, aucun maillage envoyé ; SE 501 | rien à dessiner : le moteur n'envoie aucun maillage (relevé en réel sur 200 images), donc rien non plus dans le jeu |
| Épée zénithienne (34) | 340 | 43 | fbx c43 ; teinte plein écran (30 paquets 33) ; SE 562 | **ABSENT** : fbx seul, jamais dessiné (seule la teinte plein écran est jouée) |
| bâton de Thalie (35) | 341 | 413 | modèle m5413 chargé, aucun maillage envoyé ; SE aucun | rien à dessiner : le moteur n'envoie aucun maillage (relevé en réel sur 200 images), donc rien non plus dans le jeu |
| épée ardente (36) | 342 | 4 | maillage m5004 ; SE 514 | OK : maillage dessiné ; capture réelle : maillage vu sur 6 des 10 images prises, remplissage max 36 % |
| bouclier de puissance (76) | 343 | aucun | SE 501 | rien à dessiner (aucun effet demandé ; message + son) |
| bouclier du Vent (78) | 344 | 24 | maillage m5024 ; SE 533 | OK : maillage dessiné ; capture réelle : maillage vu sur 4 des 4 images prises, remplissage max 65 % |
| Bouclier zénithien (80) | 345 | aucun | SE 541 | rien à dessiner (aucun effet demandé ; message + son) |
| bouclier de mercure (81) | 346 | aucun | SE 559 | rien à dessiner (aucun effet demandé ; message + son) |
| éclat d'étoile (96) | 347 | aucun | SE aucun | rien à dessiner (aucun effet demandé ; message + son) |
| bague de prière (102) | 348 | aucun | SE aucun | rien à dessiner (aucun effet demandé ; message + son) |

Numéros d'objet 207 (action 1) et 216 (action 257, « exhale … ») : sans nom dans les textes des objets du joueur (la table de noms s'arrête à 173), donc des données internes, non offertes au joueur ; leurs effets (Flamme, aucun) sont couverts ailleurs. Les objets sans effet de combat (herbes, potions…) passent par les actions de soin : message + son 501, aucun effet.
