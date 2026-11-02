# Historique du projet

Le projet a démarré le 29/10/2026 (avant la création de ce dépôt). Jusqu'au 30/10, chaque étape est reprise dans une issue **fermée** du jalon *M0 Fondations (terminé)* de l'ancien dépôt `dq4-pc` (les numéros #25 à #37 ci-dessous sont les siens). Depuis la séparation des dépôts, le suivi se fait **par pull request** dans `dq4-portage` (voir [`workflow.md`](workflow.md)) : la seconde table les reprend toutes, de #1 à #46. Le détail technique est dans `docs/notes-*.md`.

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

## Les pull requests de `dq4-portage` (#1 à #46)
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

## Et maintenant
Il n'y a pas d'issue ouverte dans ce dépôt : ce qui reste à faire (validation sous Windows et sur un vrai GPU, décisions en attente de Sylfried, oublis de la liste de l'audit, bugs connus, points non vérifiés) est dans [`reprise.md`](reprise.md) (section 6) et dans `docs/audit/rapport_reste_a_faire.md`. Les 27 issues encore ouvertes de `dq4-pc` au 02/11/2026 n'ont pas été reprises ici ; les jalons *M1 Village jouable 16/9*, *M2 Monde et combats* et *M3 Son et finitions*, que citait l'ancien `workflow.md`, n'existent pas dans `dq4-portage` (aucun jalon).
