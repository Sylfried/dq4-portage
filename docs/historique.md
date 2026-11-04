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
| 03/11 | #144 | carte du monde : à l'atterrissage (aile de chimère, Téléportation) le héros est devant ses équipiers, comme dans FieldPartyDraw::draw du jeu (#135, D-223) |
| 03/11 | #147 | fenêtre Interface : un clic simple sur la barre de titre replie ou déplie après le délai du double clic, un double clic ne change plus l'état (#145, D-225) |
| 03/11 | #148 | historique des dialogues : le « ; » des noms d'objets du patch (marque de coupure) n'est plus affiché (#139, D-224) |
| 03/11 | #149 | historique : le message « aucun favori » de la liste vide est coupé en lignes et tient dans le cadre (#140, D-224) |
| 03/11 | #150 | un sort de soin sans effet ne joue plus son bruitage de soin (le bruitage de lancement reste) (#137, D-224) |
| 03/11 | #151 | l'écran « Pause » devient « Paramètres » et ne met plus le jeu en pause : le jeu tourne derrière lui sans entrée, seuls l'Historique et la question Quitter l'arrêtent (#136, D-224) |

## Et maintenant
Le reste à faire est suivi par les **issues GitHub** de ce dépôt (#51 à #99, #101, #105, #107 à #112, #121 à #123, #126 à #131, #134 à #141 et #145 à #146, jalons 1 à 5 ; 60 ouvertes au 03/11/2026 : https://github.com/Sylfried/dq4-portage/issues). Le contexte est dans [`reprise.md`](reprise.md) (section 6), les décisions dans `docs/audit/decisions.md` et les points non vérifiés dans `docs/audit/rapport_reste_a_faire.md`. Les issues ouvertes de l'ancien dépôt `dq4-pc` (supprimé) n'ont pas été reprises telles quelles : leur état au 02/11/2026 est archivé dans `docs/audit/github_issues.md`.
| 04/11 | #152 | historique des combats complet : quels monstres étaient là, lesquels sont vaincus, enfuis, disparus ou restés, l'issue, l'or, l'expérience et les objets gagnés ; la boîte grandit en hauteur pour tout contenir (#141, D-224) |
| 04/11 | #153 | deux touches réattribuables pour rapprocher / éloigner la caméra au clavier (« Caméra (Rapprocher) » et « Caméra (Éloigner) » dans Commandes, pavé + / − ou E / W, pas de 5 % entre 50 et 200 %) (#146, D-225) |
| 04/11 | #154 | essai : le ciel de l'écran-titre est agrandi (x 3,16 en 16/9) pour ne montrer qu'un carreau de nuages, sans répétition, au lieu des bandes étirées ; plus flou ; les bandes restent avec `DQ_CIEL_BANDES=1` (#130) |
| 04/11 | #155 | un clic sur une bulle d'icône (personnage, coffre...) et un toucher du rond central de la croix donnent la touche d'action ; la boule orange clignote quand le jeu le demande (#131) |
| 04/11 | #156 | essai : les sprites des personnages (villes, donjons) penchent à moitié vers la verticale du monde au lieu d'être exactement droits à l'écran, pour ne plus sembler se pencher par rapport aux murs quand le héros monte ou descend ; taille, profondeur et pieds inchangés ; `DQ_SPRITE_INCLINAISON=0` rend l'état d'avant (#134) |
| 04/11 | #157 | plus de clic sur la bulle : un clic gauche n'importe où sur le terrain libre donne la touche d'action ; la croix s'anime (boule orange qui pulse) dès qu'une bulle d'action est affichée (#131) |
| 04/11 | #158 | caméra au clavier : Page haut rapproche et Page bas éloigne par défaut, en continu et sans saccade à la vitesse de rotation ; la ligne « Distance caméra » du menu Affichage est retirée (molette et touches la règlent) ; L / R perdent Page haut / Page bas (#146, D-226) |
| 04/11 | #159 | le réglage « Vitesse de transition » disparaît : les fondus et la cascade de combat gardent la durée du jeu (x1), un ancien fichier de réglages se charge sans erreur (#101, D-226) |
| 04/11 | #160 | le panneau Interface détecte le double clic comme Windows (délai compté depuis le début du premier appui, rectangle de tolérance, simple clic acquis dès que le double clic est impossible) : un simple clic ne fait plus attendre pour rien (#145, D-226) |
| 04/11 | #162 | l'espace insécable avant « ! », « ? » et « : » est dessinée avec la largeur d'une espace normale (5 px au lieu de 11 px dans la police du jeu) : plus d'espace trop large dans les dialogues (#161, D-226) |
| 04/11 | #164 | marche accélérée : la nuit arrive (1 + x) / 2 fois plus vite sur la carte du monde, comme les rencontres, et non x fois (x2 : 1,5 fois ; x1,5 : 1,25 fois) ; crochet sur le saut vers `FieldStage::ChangeTime`, mesuré sur le vrai moteur (#163, D-226) |
| 04/11 | #169 | la croix de l'écran a un diamètre double de celui du mobile (réduite seulement dans une fenêtre plus étroite que le portrait) et le héros court quand le pointeur est au bord de l'anneau (90 % du rayon ou plus : même vitesse que la touche d'accélérateur), il marche normalement plus près du centre ; la boule s'allume en course (#166, D-227) |
| 04/11 | #170 | les deux touches de distance de la caméra ensemble (Page haut + Page bas), Ctrl + molette et Ctrl + clic molette ramènent la distance à 100 % par une animation (vitesse du recentrage de la rotation : 5 x l'écart par seconde, au moins 60 % / s, fois « Vitesse de caméra »), au lieu d'un saut ; une touche de distance seule ou un cran de molette l'interrompt (#167, D-227 et 10 h 49) |
| 04/11 | #171 | Ctrl (la « Touche spéciale ») + une touche de la caméra (les quatre flèches, Page haut, Page bas) remet TOUS les états de la caméra à l'origine : rotation, inclinaison et distance, par les animations ; sur la carte du monde et dans un lieu qui interdit de tourner la caméra, seule la distance revient (#168, D-227) |
| 04/11 | #175 | la croix de l'écran perd 25 % de sa taille par défaut : diamètre de base une fois et demie celui du mobile (au lieu du double de #169) ; le réglage « Taille de la croix » (50 à 200 %) s'applique toujours par-dessus (#172, D-228) |
| 04/11 | #176 | le retour animé de la distance à 100 % va à la même vitesse que le recentrage de la rotation (au moins 240 par seconde au lieu de 60 % par seconde, 5 x l'écart par seconde) : un écart de X % se résorbe comme un écart de X degrés, rotation, inclinaison et distance arrivent ensemble à l'origine (#173, D-228) |
| 04/11 | #177 | le ciel de l'écran-titre est dessiné à plat à l'échelle de l'écran : la texture a la hauteur de la fenêtre (à toute taille, sans agrandissement), se répète sur la largeur, avec l'effet de vague des bandes (étirure horizontale et glissement vertical fixes à l'écran, la texture défile dessous) et le dégradé de teinte des rangées d'origine ; `DQ_CIEL_AGRANDI=1` redonne l'essai #130, `DQ_CIEL_BANDES=1` les bandes (#174, D-228) |
| 04/11 | #179 | plus aucune page du menu Paramètres n'arrête le jeu (l'Historique et la question Quitter le figeaient depuis #151) : il tourne derrière toutes les pages, sans touche ni clic ; la liste de l'historique suit ce que le jeu y écrit pendant qu'elle est ouverte (nouveaux messages en bas quand la vue est en bas, la lecture ne saute pas plus haut) (#178, D-229) |
| 04/11 | #181 | les PNJ ne sont plus cisaillés vers la verticale du monde (inclinaison de #156 retirée par défaut : elle déformait les sprites près des bords) : retour à l'état d'avant #156, sprites droits aux proportions constantes, identique au pixel ; `DQ_SPRITE_INCLINAISON` garde l'essai (#180, D-229) |
| 04/11 | #183 | le décor de carte est dessiné avec le culling des faces arrière, comme les shaders du jeu (Cull Back, lu dans le paquet de données) : un mur n'a de texture que sur sa face avant, caméra tournée on voit à travers les murs d'un intérieur ; ciel du titre et carte du monde inchangés ; `DQ_DECOR_CULL=0` redonne l'ancien rendu (#182, D-230) |
| 04/11 | #185 | les PNJ reprennent le panneau brut du jeu (correction des bords à 0 par défaut) et gardent l'inclinaison de la caméra du jeu : Haut / Bas ne les redressent plus face à la caméra ; `DQ_CORRECTION_BORDS=100` et `DQ_SPRITES_SUR_VUE=1` redonnent les anciens rendus (#184, D-231) |
| 04/11 | #187 | l'historique (touche H, ligne du menu Paramètres) n'est accessible que quand le joueur a la main sur son personnage : ni en combat, ni pendant un dialogue, une scène, un événement ou un menu du jeu ; ligne grisée, message bref, page fermée si le jeu reprend la main (#186, D-232) |
| 04/11 | #189 | le bouton de vitesse de combat est de nouveau sur le bord gauche de l'écran (sa case de la grille, plaque d'origine), plus rattaché à la boîte du bas ; `DQ_VITESSE_ANCRE=1` redonne le rattachement de #47 ; « Replacer sur le bord gauche » (#188, D-233) |
| 04/11 | #191 | la description d'un objet ne sort plus de son cadre : fiche d'objet en combat (elle recouvrait « Attaque E 74 »), menu Objets, fiche d'un sort ; texte recoupé à la largeur du cadre puis comprimé (jusqu'à x 0,7) si 2 lignes ne suffisent pas ; proportions et positions inchangées (#190, D-234) |
| 04/11 | #193 | sauvegarde automatique : lecture du code du jeu (quand : à l'arrivée sur une carte, jamais à la fermeture ; quoi : instantané de reprise, type 3 ; comment : `Cryption::Filter` puis `fopen` / `fwrite` / `fclose`) ; le portage se comporte comme l'original, aucun changement de comportement (#192, D-235) |
| 04/11 | #195 | l'historique n'affiche plus de message quand il n'est pas accessible (touche H en combat, dialogue, scène) ni quand la page se referme parce que le jeu reprend la main ; règles d'accès de #187 inchangées (#194, D-236) |
| 04/11 | #197 | rangement du projet : tout ce qui t'appartient (APK, sauvegardes, caches, réglages, journaux) dans un seul dossier `donnees\` (jamais envoyé sur GitHub) ; code rangé par dossiers (`noyau`, `monde`, `rendu`, `combat`, `menus`, `persistance`, `fenetre`) ; l'ancien `fenetre.py` (3 761 lignes) découpé en 13 modules par thème ; un seul `lancer_dq4.bat` à la racine qui reprend d'abord les anciens fichiers (copie, rien de supprimé) ; tests dans `tests\` ; chemins centralisés dans `chemins.py` ; fonctionnement du jeu inchangé (#196, plan dans `docs/plan_du_code.md`) |
| 04/11 | #199 | les sauvegardes du moteur s'écrivent par fichier temporaire puis remplacement d'un coup ; une erreur d'écriture (antivirus, disque plein) ne ferme plus le jeu : l'ancien fichier reste intact, ligne dans le journal et petit message à l'écran (#198, audit ENG-02) |
| 04/11 | #202 | les musiques Ogg qui dépassent la pleine échelle sont écrêtées au lieu de déborder (BGM14 : 3 échantillons, BGM34 : 7 ; pics inversés avant) (#200, audit SND-02) |
| 04/11 | #204 | trois bruitages dont la boucle dépasse de quelques échantillons la fin des données (SE 329, 331, 1118) sont de nouveau bouclés ; cache des bruitages versionné (#201, audit SND-03) |
| 04/11 | #205 | les surfaces transparentes du décor suivent leur vraie priorité (entier en +52 de l'objet de carte, et non une moitié des drapeaux) : l'écume au pied des cascades de `dlb1a` apparaît ; cache des cartes en version 11 (refait au premier lancement) (#203, audit MAP-01) |
| 04/11 | #207 | charger un état instantané ne touche plus au moteur s'il est abîmé ou d'une autre version de la bibliothèque du jeu (décodage et vérifications avant toute écriture ; empreinte `lib_sha` enregistrée) (#206, audit ENG-06) |
| 04/11 | #209 | la tabulation des textes de menu vaut `tabSize` espaces dans toutes les cellules qui en portent une (« Nv. » de l'ordre de marche n'est plus dessiné sur le sprite ; « ×N » des plaques de groupe repoussé vers le bord droit), plus seulement dans la liste des magies (#208, audit UI-03) |
| 04/11 | #211 | le bateau de la carte du monde est découpé comme dans le jeu (cases de 40 × 40 sur 12 colonnes, panneau de 0,8 × 0,8) : navire entier, sillage visible ; alias 194 -> 193 (#210, audit SPR-01 et SPR-05) |
| 04/11 | #213 | l'ombre du ballon est posée où le moteur la demande sur la carte du monde (32 pixels au sud de la nacelle) au lieu d'être collée dessous (paquet 15, bit 14) (#212, audit SPR-02) |
| 04/11 | #215 | l'import de sauvegardes refuse un journal abîmé ou qui n'en est pas un (somme de contrôle, avec la raison) et écrit chaque fichier en entier ou pas du tout (#214, audit ENG-07) |
| 04/11 | #216 | `Moteur.demarrer_ville` refuse un nom de carte sans fichier `.stg` (le moteur d'origine plantait) ; ticket #76 rectifié et clos : `za3f3` est une carte orpheline, `ev01` ne plante que lancée par `startTown` (audit ENG-10) |
| 04/11 | #218 | les réglages du moteur qui ne s'installent pas (moteur d'un autre APK) sont notés dans `erreurs_fenetre.log` et signalés à l'écran, au lieu d'une ligne de console invisible sur Windows (#217, audit ENG-08) |
| 04/11 | #220 | les descriptions du bas des boutiques (achat, vente), du casino et de la fiche d'objet de vente sont recoupées à la largeur du cadre (24 descriptions sur 360 dépassaient) ; la table est indexée aussi par le port (#219, audit UI-04) |
| 04/11 | #222 | le son ne se coupe plus jusqu'à la fermeture au premier échec de lecture : 3 échecs de suite le coupent un moment, nouvel essai tout seul (2 s, 10 s, 30 s), musique relancée au retour, tout noté dans `erreurs_fenetre.log` avec un message à l'écran (#221, audit SND-10 / SND-12) |
| 04/11 | #224 | la teinte plein écran de l'effet 35 couvre toute la largeur de l'écran 16/9 en combat (avant : deux bandes latérales sans teinte) (#223, audit CMB-02) |
| 04/11 | #226 | une texture de monstre absente des données (25 numéros) n'arrête plus le jeu : texture transparente à la place (#225, audit CMB-03) |
| 04/11 | #228 | le bruitage 300 des boutons suit la règle du jeu d'origine, au clavier comme au doigt : A et action seuls ; Entrée, Espace, M et les lettres du nom le jouent (#227, audit SND-08 / SND-09 / UI-01, règle de #60) |
| 04/11 | #230 | un arrêt de la musique pendant un jingle à reprise fait repartir la musique d'avant ; un morceau sans boucle fini, redemandé, repart (#229, audit SND-05 / SND-06) |
| 04/11 | #232 | repli « menus simples » : le canevas du message est lu de façon circulaire (512 lignes), le texte des combats ne disparaît plus (#231, audit CMB-04) |
