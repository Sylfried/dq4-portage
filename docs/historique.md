# Historique du projet

Le projet a démarré le 29/10/2026 (avant la création de ce dépôt). Jusqu'au 30/10, chaque étape est reprise dans une issue **fermée** du jalon *M0 Fondations (terminé)* de l'ancien dépôt `dq4-pc` (les numéros #25 à #37 ci-dessous sont les siens). Depuis la séparation des dépôts, le suivi se fait **par pull request** dans `dq4-portage` (voir [`workflow.md`](workflow.md)) : la seconde table les reprend toutes, de #1 à #100 (les numéros #51 à #88 et #90 à #99 sont des issues : issues et PR partagent la même numérotation). Le détail technique est dans `docs/notes-*.md`.

| Date | Étape | Issue |
|---|---|---|
| 29/10 | Cadrage : portage natif PC de DQ4, 16/9 d'abord, voies A/B/C, projet séparé du patch FR | #25 |
| 29/10 | Voie A validée : `libdq4core.so` tourne sous Unicorn (testé sur pdc et Linux) | #26 |
| 29/10 soir | Protocole moteur → Unity décodé (paquets, mot d'état, fondu) | #27 |
| 29/10 soir | Démarrage sans Unity, chargement d'une sauvegarde (`loadbank`) | #28 |
| 29/10 soir | Lecture des données Unity : cartes, textures, feuilles de sprites | #29 |
| 29/10 soir | Premier rendu côté cloud : l'église avec le personnage | #30 |
| 29-30/10 | Visionneuse pyglet 16/9 temps réel, clavier, lanceur `lancer_dq4.bat` | #31 |
| 30/10 | Portes et changement de carte (blocage signalé sur pdc, corrigé) | #32 |
| 30/10 | Sprites nets (flou signalé sur pdc, corrigé), silhouette de l'équipe | #33 |
| 30/10 | Cadrage 16/9 du village, ciel, bornes de caméra | #34 |
| 30/10 | Messages : texte français du moteur dans une fenêtre | #35 |
| 30/10 nuit | Menus : file MenuPort, liste de l'église, menu de commandes, saisie clavier | #36 |
| 30/10 | Dépôt GitHub, règles de travail, issues de départ | #37 |
| 30/10 nuit | Séparation du dépôt d'origine `dq4-pc` : portage natif (ici), essai Unity (`dq4-portage-unity`), patch français (inchangé) | — |

## Les pull requests de `dq4-portage` (#1 à #133)
Dates de fusion (squash vers `main`), heure de Paris (UTC + 1) ; titres tels qu'ils figurent sur GitHub, sans leur préfixe « Avance #N : ». Les « retours de HH h MM » sont les retours de test de Sylfried traités par la pull request. La PR #1 démarre la numérotation de ce dépôt : ses numéros ne sont pas ceux des issues de `dq4-pc`.

| Fusion | PR | Titre |
|---|---|---|
| 31/10 00h06 | #1 | le portage utilise son propre dossier `jeux\DQ4` |
| 31/10 00h13 | #2 | camera des villes comme Unity, personnages de face, plus de silhouette |
| 31/10 00h32 | #3 | portes, jarres et tonneaux animés comme dans le jeu |
| 31/10 00h38 | #4 | carte du monde : lieux visibles dans toute la zone 16/9 |
| 31/10 00h45 | #5 | survol de la souris dans les menus |
| 31/10 01h03 | #6 | textes des boutons, boutons sombres, interface agrandie |
| 31/10 01h21 | #7 | début de combat : effet de morceaux d'écran, plus de flash de la mauvaise carte |
| 31/10 01h32 | #8 | son : jingles avec reprise de la musique, bruitages en boucle |
| 31/10 01h44 | #9 | Carte du monde : eau et côtes animées |
| 31/10 02h04 | #10 | Cache préparé en arrière-plan, fondus attendus par le moteur |
| 31/10 02h05 | #11 | docs : notes de la visionneuse (31/10) |
| 31/10 09h29 | #12 | zoom commun, pixel perfect x1/x2/x4/x8, boucle à 30 Hz, scintillements |
| 31/10 10h00 | #13 | F2 pixel perfect x1/x2/x4/x8, F3 effectif, décors de combat et de ville suivent F2, filtre net corrigé |
| 31/10 10h16 | #14 | décor de combat lissé en pixel perfect, pixel perfect par défaut |
| 31/10 11h01 | #15 | Menu Échap, réglages, touches modifiables et états instantanés |
| 31/10 11h36 | #16 | boîte de message en combat et textes des boutons centrés |
| 31/10 12h44 | #17 | Décor animé : eau, lampes, palettes scintillantes, mouvements automatiques |
| 31/10 15h59 | #18 | Menu, options, boutons mobiles, carte, dégâts, coffres |
| 31/10 16h18 | #19 | Décor : eau des grottes, ombres douces, ombres des personnages |
| 31/10 16h42 | #20 | Combat : vibration et clignotements, boîte de message à 3 lignes |
| 31/10 17h24 | #21 | Réglages, ombres, grande carte du monde, coffres |
| 31/10 18h25 | #22 | Signe de Y des objets de carte, touche Carte, musique reprise, menu Échap |
| 31/10 19h09 | #23 | rendu net, interrupteurs et listes du menu Échap |
| 31/10 19h36 | #24 | halo des héros, états datés, menu Échap noir, transitions et vignettage |
| 31/10 20h34 | #25 | Zoom au lancement, survol par bouton, menu Échap selon l'Excel, distance d'affichage |
| 31/10 21h22 | #26 | ZQSD, caméra aux flèches, zoom 40-400 %, menu Échap à plat |
| 31/10 22h20 | #27 | Recentrage animé de la caméra, menu Échap noir avec barre de défilement |
| 31/10 23h37 | #28 | interfaces, clavier, caméra, carte du monde |
| 31/10 23h39 | #29 | notes techniques : carte (type 25), TownCamera, vitesse du héros |
| 01/11 00h18 | #30 | Retours de 23 h 55 : caméra centrée, menu États, éditeur, caméra accélérée, boîtes de combat |
| 01/11 00h19 | #31 | Notes techniques : compagnons, boîtes de combat |
| 01/11 01h15 | #32 | retours de 00 h 33 : infobulles, éditeur replié, boutiques, survol des menus, diagonale |
| 01/11 02h22 | #33 | Retours de 01 h 31 : course sans dispersion, rencontres par distance, cartes, menus, clignotements |
| 01/11 12h30 | #34 | Retours de 11 h 34 : alliés, carrés rouges, fin de combat, menu États, Divers, réglages, Oui / Non |
| 01/11 14h16 | #35 | Retours de 13 h 08 : bouton Menu Échap, dernière boîte de combat, alliés à la course, plume |
| 01/11 15h07 | #36 | croix à l'écran, boutons à gauche, Taille de la croix, alliés |
| 01/11 15h36 | #37 | Retours de 15 h 25 et 15 h 32 : course sur toute l'horloge, Menu Pause, réinitialisation des interfaces |
| 01/11 15h39 | #38 | Retour de 15 h 39 : confirmation pour quitter |
| 01/11 17h43 | #39 | avant la partie (logos, titre, menu de départ, nom, licence) et audit de fidélité |
| 01/11 19h20 | #40 | Retours de 18 h 02 : menu de départ centré, bouton Sauvegardes (export / import), licence du projet, prologue (fondus, bandeau), boîte violette, caméra |
| 01/11 22h26 | #41 | Retours de 20 h 46 : avant-partie centree, Pause, editeur d'interface, affichage, textes, son |
| 02/11 01h40 | #42 | Retours de 23 h 24 : fenetre (3 modes, F11), Pause, editeur d'interface, titre (dragon, credits), camera, sprites |
| 02/11 04h52 | #43 | retours de 02 h 12 : titre, coffres, souris, plein écran, vitesse des combats, historique |
| 02/11 12h25 | #44 | historique refait, vitesse de combat, jour et nuit, audit des services et du casino |
| 02/11 21h43 | #45 | retours de 14 h 08 : historique, caméra, combat, chargement, magie, sprites, textes |
| 02/11 21h57 | #46 | reprise : guide, audit restant, briefs, rapports d'agents et scripts de la session |
| 03/11 01h40 | #47 | retours de 22 h 29 : pause, caméra, titre, combat, historique, sorts, bruitages |
| 03/11 07h48 | #48 | retours de 07 h 33 : sorts sans effet, transition x1, historique au clavier |
| 03/11 13h53 | #49 | Docs et audit à jour, CI minimale |
| 03/11 14h23 | #50 | décisions du 03/11, dq4-pc supprimé, docs à jour |
| 03/11 14h33 | #89 | décisions du 14 h 25 : 38 issues pour le reste à faire, pr.sh à jour |
| 03/11 | #100 | lecture du reste à faire (15 h 50) et ménage : décisions D-163 à D-190, 10 issues, tri des lacunes, licence d'Unicorn, plan de test du chapitre 2 |
| 03/11 | #102 | réponses de 16 h 47 : décisions D-191 à D-200, transitions à x4 (#101), #96 fermée, `.exe` launcher et licence, lacunes et documents à jour |
| 03/11 | #103 | précision de 17 h 01 (D-201) : seul le réglage « Vitesse de transition » disparaît (marche et Maj restent), #101 et #53 corrigées ; sort de déplacement gardé tel quel (D-202) |
| 03/11 | #104 | audio validé et `reglages.json` sans souci (D-203), #99 mise à jour |
| 03/11 | #106 | test « issue par issue » en commençant par #52 (D-204), issue #105 : modificateurs et triches à décider en tout dernier (D-205) |
| 03/11 | #113 | retours du test de #52 (D-206 à D-213) : libellé « Antialiasing », course acceptée dès l'arrivée sur une carte (#107), issues #107 à #112 |
| 03/11 | #114 | choix du périphérique de sortie audio, première ligne de la page Son (#112, D-207) |
| 03/11 | #115 | écran titre : logo et sous-titre deux fois plus grands (#108, D-209) |
| 03/11 | #116 | « Revenir à l'écran titre » : la boîte d'origine du jeu (Oui / Non) puis son fondu, comme le bouton des Paramètres de l'APK (#109, D-210) |
| 03/11 | #117 | caméra des villes : les petits reliefs (butte du village du prologue) sont suivis exactement (#110, D-211) |
| 03/11 | #118 | fond des villes : dégradé vertical du moteur au lieu d'une couleur unie (#111, D-212) |
| 03/11 | #119 | écran titre : logo et sous-titre 1,5 fois plus grands au lieu de 2 (#108, D-215) |
| 03/11 | #120 | plus de choix du moniteur du plein écran ni du périphérique audio : plein écran sur l'écran de la fenêtre, son sur la sortie par défaut de Windows (#112 non retenue, D-216 et D-217) |
| 03/11 | #124 | sauvegarde automatique du jeu à la fermeture de l'application (croix, Alt + F4, menu Quitter, fin de tâche, console, Ctrl + C, fin de session) ; « Revenir à l'écran titre » l'efface toujours (#122, D-218 et D-219) |
| 03/11 | #125 | passage plein écran → fenêtre qui échoue : l'erreur complète (pile d'appels, état de la fenêtre et des moniteurs) est notée dans `erreurs_fenetre.log` pour trouver la cause (#123 ; correction à venir) |
| 03/11 | #132 | plein écran → fenêtre après le branchement d'un écran externe : le moniteur gardé par pyglet est relu avant chaque bascule (sa poignée Windows n'était plus valable : « Descripteur non valide ») (#126, D-220) |
| 03/11 | #133 | course (accélérateur) et marche accélérée dès que le héros est libre au retour d'un combat, et non à la fin du fondu de retour (30 images) (#127, D-221) |
| 03/11 | #142 | la sauvegarde automatique est celle du jeu : plus aucune écriture forcée à la fermeture (croix, Alt + F4, menu Quitter, console, fin de session) ; le moteur l'écrit seul (arrivée sur la carte du monde, donjon selon ses conditions) (#128, D-220 ; remplace #124) |
| 03/11 | #143 | le petit rappel « Échap : menu / F1 : infos » en bas à gauche au démarrage est retiré (#129, D-220) |

## Et maintenant
Le reste à faire est suivi par les **issues GitHub** de ce dépôt (#51 à #99, #101, #105, #107 à #112, #121 à #123, #126 à #131 et #134 à #141, jalons 1 à 5 ; 58 ouvertes au 03/11/2026 : https://github.com/Sylfried/dq4-portage/issues). Le contexte est dans [`reprise.md`](reprise.md) (section 6), les décisions dans `docs/audit/decisions.md` et les points non vérifiés dans `docs/audit/rapport_reste_a_faire.md`. Les issues ouvertes de l'ancien dépôt `dq4-pc` (supprimé) n'ont pas été reprises telles quelles : leur état au 02/11/2026 est archivé dans `docs/audit/github_issues.md`.
