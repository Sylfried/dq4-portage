### Fait
- Menu Affichage : la ligne « Distance caméra » est retirée (la molette, Ctrl + molette et les touches la règlent). Elle reste affichée dans les infos F1.
- Tests : `tools/test_distance_camera_clavier.py` (19 tests : défauts, migration, menu, vitesse, fluidité sans à-coup, bornes, vitesse de caméra et accélérateur, conditions d'action) ; `test_window_mode.py` (ordre de la page Affichage).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (fluidité réelle, vitesse du zoom).
- **Supposé** : « à la même vitesse qu'elle tourne » = même nombre par seconde (100 % / s et 100 ° / s, mêmes réglages de vitesse). Si trop vite ou trop lent : la constante `CAM_DIST_VIT`.
- L / R n'ont plus Page haut / Page bas : en menu de jeu, A et R tournent les pages (réattribuable dans Commandes).

## Avance #159 : plus de réglage de vitesse de transition (#101, 04/11/2026)

### Demande (D-226, 04/11 09 h 45)
« Et supprime l'option pour changer la vitesse de transition, on la laisse à 1x tout court. »

### Établi
- Cette décision **remplace** celle de #101 (16 h 47 le 03/11 : transitions de porte à x4 fixe, reconnues à leur bruitage) : les transitions gardent la **durée du jeu (x1)**, sans accélération ni reconnaissance par bruitage.
- Le moteur garde son paramètre interne `Etat.vitesse_fondu` (1,0, durée d'origine) : les tests le font varier, plus aucun réglage du joueur ne le change.

### Fait
- `settings.py` : clés `vitesse_fondu` et `vitesse_fondu_v` retirées (défauts, bornes, crans x1 à x4, migration de l'ancien défaut x2). Un ancien `reglages.json` qui les contient se charge sans erreur ; la clé est ignorée et n'est plus réécrite.
- `pause.py` : la ligne « Vitesse de transition » de Commandes › Vitesses est retirée ; `window.py` : plus de `regler_fondu` ni de lecture du réglage au démarrage.
- Tests mis à jour : `test_sound_text_settings.py` (plus de réglage, ancien fichier ignoré), `test_pause_pages.py`, `test_interface_settings.py`.

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (la ligne n'est plus dans Commandes › Vitesses ; les transitions durent la durée du jeu).
- Le critère « x4 pour les portes » de #101 est abandonné (décision du 04/11) : à fermer quand Sylfried valide.

## Avance #160 : double clic du panneau Interface détecté comme Windows (#145, 04/11/2026)

### Demande (D-226, 04/11 09 h 44)
« Aligne toi sur le fonctionnement de windows pour détecter un double clic car là ça prend un peu de temps pour que la fenêtre agisse s'il s'agit finalement que d'un simple clic. »

### Établi
- Avant (#145, première version) : un clic simple sur la barre de titre du panneau Interface ne repliait / dépliait qu'après un délai fixe compté **depuis le relâchement**, quoi que fasse la souris ensuite.
- Windows juge un double clic ainsi : le second appui arrive **moins de `GetDoubleClickTime` (500 ms par défaut) après le DÉBUT du premier** et **dans le rectangle `SM_CXDOUBLECLK` x `SM_CYDOUBLECLK` (4 x 4 px par défaut) centré sur le premier**.

### Fait
- `pause.py` : `double_clic_systeme()` lit le délai et le rectangle du système sous Windows (ctypes `user32`), sinon 500 ms et 4 x 4 px (`DQ_DOUBLE_CLIC` force le délai) ; `_double_possible(x, y, t)` applique la règle de Windows.
- Le délai court depuis le **début** de l'appui. Si l'appui a déjà duré plus que le délai, le clic simple agit dès le relâchement.
- Le clic simple agit **dès que le double clic est impossible**, sans attendre la fin du délai : pointeur sorti du rectangle (`survol`), autre appui hors du rectangle (`clic`), début d'un glisser, ou délai écoulé (`maj`).
- Un vrai double clic reste neutre : retour à la position d'origine, aucun changement d'état à aucun moment.
- `test_interface_panel.py` : 19 tests (6 nouveaux : délai compté depuis le début de l'appui, rectangle, pointeur sorti, appui ailleurs, appui plus long que le délai).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (le délai réel du système et la tolérance de position, qu'il peut régler dans Windows).
- **Supposé** : le rectangle 4 x 4 px de Windows est étroit ; sur un écran à haute densité de pixels, un tremblement de la main peut sortir du rectangle et le panneau agit alors plus tôt (comportement identique à celui d'une fenêtre Windows).

## Avance #162 : l'espace avant « ! » n'est plus trop large (#161, 04/11/2026)

### Demande (D-226, 04/11 09 h 44)
Capture « Ragnar lance l'aile de chimère en l'air ! » : « c'est le mauvais espace qui est affiché avant le « ! » donc ça en fait un trop large ». Sylfried propose d'aller chercher les règles du projet de traduction ; le code et ce projet ont suffi (consulté via l'API GitHub, sans clone).

### Établi
- Les textes du patch FR (`assets/msg/en/*.mpt`) mettent **U+00A0** avant « ! » (8 582 fois), « ? » (3 951) et « : » (170).
- Police `SE-GARRIR` (extraite du `base.apk` patché, 218 glyphes) : espace normale **advance 5**, glyphe 160 (U+00A0) **advance 11**, sans dessin ; U+202F et U+2009 n'existent pas (déjà dessinées comme l'espace normale).
- Projet de traduction (`PROJET.md`, 26/10) : « l'espace insécable n'existe pas dans Large.font (menus) », test de Sylfried sur DQ4 : espace normale = bon, insécable = mauvais (cas du « ; »).

### Fait
- `ui_menu.py` : `PoliceBitmap._glyphe` dessine U+00A0, U+202F et U+2009 comme l'espace normale (`ESPACES_FINES`) ; largeur d'une ligne et texture suivent. Le glyphe 160 garde son advance dans les données de la police.
- Effet de bord : l'historique des combats écrit `Or : n` + 5 U+00A0 + `Expérience : n` ; l'écart passe de 55 px de police (5 x 11) à 25 px (5 espaces).
- Test : `tools/test_espace_insecable.py` (police factice, vraie police si `DQ_CACHE_UI`, texture de ligne de même taille).
- Comparaison avant / après sur les vraies lignes du jeu (rendu de `PoliceBitmap.ligne`) : « en l'air !» passe de 2 espaces visuelles à une.

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried sur son écran (capture du dialogue d'origine).
- **Supposé** : le jeu d'origine dessine la même espace de 11 px ; la correction s'écarte donc peut-être du mobile, dans le sens demandé. Si une espace plus fine que 5 px est préférée avant « ! », elle se règle dans `PoliceBitmap._glyphe`.

## Avance #164 : la nuit arrive (1 + x) / 2 fois plus vite en course (#163, 04/11/2026)

### Demande (D-226, 04/11 09 h 44)
« Je veux que la course ait le même effet accélératif que pour les combats, au lieu de faire venir 2x plus vite la nuit si l'accélérateur est en x2 je veux qu'elle vienne juste 1,5x plus vite, si l'accélérateur est en 1,5 alors elle doit venir en 1,25x plus vite, etc. »

### Établi
- Carte du monde : le temps du monde (`status::g_Stage + 0xcc`, cycle 0xd40) avance de 2 par image du moteur où le héros a changé de position (`FieldStage::ChangeTime(0)` appelé à la fin de `FieldPlayerDoku::checkDokuDamage`). La marche accélérée fait tourner le moteur a fois plus vite, donc la nuit arrivait a fois plus vite par seconde.
- La règle demandée est celle des rencontres aléatoires (#45, « Vitesse de marche » dans Commandes › Vitesses) : (1 + a) / 2.

### Fait
- `engine.py` : `_crochets_horloge_jour` (crochet sur le saut terminal de `checkDokuDamage`, + 0x38) ; `encounters.py` : `Passeur` (fraction (1 + a) / (2 a) des appels, fractions cumulées). Les appels sautés vont directement au `ret` de la fonction. A x1 (ou plus lent) : le jeu d'origine, à l'identique. Vérification du code attendu au démarrage (message et aucun crochet si le désassemblage ne correspond plus).
- `pause.py` : les aides de « Vitesse de marche » et « Multiplicateur de l'accélérateur » citent maintenant l'arrivée de la nuit.
- Test : `tools/test_horloge_jour.py` (4 tests de formule, 2 sur le vrai moteur avec `DQ_APK` / `DQ_SAVES`).
- Mesure sur le vrai moteur (carte du monde, sauvegarde 4, 491 pas dans le couloir de `simulate_encounters.py`, combats coupés) : temps du monde par pas 2,000 à x1 ; 1,666 à x1,5 ; 1,499 à x2 ; 1,332 à x3 ; 1,246 à x4, soit **par seconde 1,25 ; 1,50 ; 2,00 ; 2,49 fois** celle de x1. Le héros marche exactement de la même façon (positions identiques image par image à x1 et à x4).

### À trancher / non vérifié
- **Supposé** : « le même effet accélératif que pour les combats » désigne la règle des rencontres (1 + x) / 2 ; la vitesse de combat (Rapide, Très rapide) ne touche pas l'horloge du monde.
- **Sous Windows** : à confirmer par Sylfried (marche longue sur la carte du monde avec l'accélérateur).
- **Établi** : seule la carte du monde fait avancer l'horloge (`ChangeTime(0)` n'est appelé que par `checkDokuDamage`) ; villes et donjons ne sont pas concernés.

## Avance #169 : croix x2 et course au bord de l'anneau (#166, 04/11/2026)

### Demande (D-227, 04/11 10 h 46)
« Double la taille de la croix directionnelle, et fais en sorte que lorsque le joystick touche les bords le personnage se met à courir, sinon il marche normalement. »

### Fait
- `hud_mobile.DIAM_CROIX` = 2 x 161,28 : le diamètre de base de l'anneau est le double de celui du mobile (à 800 de haut : 322,56 ; à 1080 : 435 px). Le réglage « Taille de la croix » (50 à 200 %) s'applique par-dessus : **50 % = la taille du mobile**, 200 % = le quadruple. Une fenêtre plus étroite que le portrait 9:16 réduit la croix (`LARGEUR_CROIX_MAX` = 0,75 de la largeur : le double du mobile en prend 0,72 au portrait) pour qu'elle ne sorte pas de l'écran (la vidéo du 04/11 est une fenêtre de 394 x 1102).
- `Boutons.croix_course()` : croix tenue dans une direction à `COURSE_SEUIL` = 0,9 du rayon de l'anneau ou plus (la prise va jusqu'à 1,178). `Jeu._facteur_vitesse` applique alors le multiplicateur de l'accélérateur comme la touche d'accélérateur tenue (les deux ensemble ne se cumulent pas) ; plus près du centre, le héros marche normalement (« Vitesse de marche » seule). La direction envoyée au jeu ne change pas. La boule s'allume (halo) tant que la croix est au bord, pour que le joueur sache qu'il court.
- Tests : `tools/test_croix_course.py` (16 tests : constante, diamètre selon la hauteur et le réglage, fenêtres étroites, croix dans l'écran à 5 formats, seuil, 24 directions, croix lâchée, direction inchangée, vraie `Jeu._facteur_vitesse`). Les faux jeux des tests de vitesse existants reçoivent une croix factice (`croix_course` faux).

### À trancher / non vérifié
- **Supposé** : « touche les bords » = le pointeur atteint 90 % du rayon de l'anneau ; « double » = le diamètre de base (un réglage enregistré à 100 % donne donc le double sans rien changer dans `reglages.json`).
- **Sous Windows** : taille de la croix (plus grande qu'avant : elle peut gêner l'image), seuil de la course (si trop tôt ou trop tard : `COURSE_SEUIL`), halo en course.

## Avance #170 : retour animé de la distance de la caméra à 100 % (#167, 04/11/2026)

### Demande (D-227, 04/11 10 h 46 et 10 h 49)
« Appuyer simultanément sur les 2 touches pour avancer ou reculer la caméra doit la faire revenir au zoom initial » ; puis : « Il doit aussi y avoir un effet de transition quand je remet le zoom par défaut (à la souris comme au clavier) ».

### Fait
- `Jeu._maj_distance_clavier` (à chaque image, avec `_maj_camera`) : **les deux touches ensemble** (« Caméra (Rapprocher) » + « Caméra (Éloigner) », Page haut + Page bas par défaut) lancent le retour de la distance à 100 % (`RG.DEFAUT['distance_camera']`) par une **animation**, comme les deux flèches opposées pour la rotation : pas par image = max(`CAM_RECENTRE_DIST` = 60 % / s, 5 x l'écart par seconde) x « Vitesse de caméra » (l'accélérateur n'y change rien), arrivée exacte sur 100 % (de 200 % à 100 % : environ 0,6 s ; de 50 % à 100 % : environ 0,5 s). Tant qu'il reste une touche enfoncée après la pression double (le relâchement n'est jamais exactement simultané), rien ne se passe (`dist_bloque`) ; une nouvelle pression seule, ou un cran de molette, interrompt l'animation ; un menu, un message ou un combat l'annule.
- `Jeu.distance_par_defaut` (Ctrl + molette, Ctrl + clic molette) ne saute plus à 100 % : elle lance la même animation (`dist_retour`). La molette seule et le curseur du menu Échap restent immédiats.
- Textes d'aide (page Commandes et aide des deux touches) mis à jour.
- Tests : `tools/test_distance_camera_clavier.py` (27 tests : l'ancien « les deux touches ne font rien » est remplacé par 9 tests : retour progressif et monotone depuis 200, 150, 70 et 50 %, durée, déjà à 100 %, vitesse de caméra et accélérateur, poursuite après le relâchement, touche restée enfoncée, interruption par une touche seule, Ctrl + molette, arrêt hors du terrain) ; `tools/test_entrees.py` : Ctrl + molette et Ctrl + clic molette lancent le retour (`dist_retour`) au lieu de mettre 100 d'un coup, un cran de molette l'interrompt.
- Capture sur la ville `maout` (distance de départ 200 % ; fond sans décor dans cette scène de test) : le héros grossit image après image, 200, 192, 184, ... 118, ... 100 % en 37 images.

### À trancher / non vérifié
- **Supposé** : vitesse du retour (60 % / s au minimum, 5 x l'écart par seconde, comme la rotation) ; « les deux touches » = Page haut + Page bas ou leurs remplaçantes réattribuées.
- **Sous Windows** : le ressenti de l'animation (trop rapide / trop lente : `CAM_RECENTRE_DIST` et le facteur 5) ; la pression double des deux touches du clavier réel.

## Avance #171 : Ctrl + touche de caméra remet tous les états de la caméra (#168, 04/11/2026)

### Demande (D-227, 04/11 10 h 46)
« CTRL + touche du clavier pour la caméra réinitialise TOUS les états de la caméra ».

### Fait
- Avant : Ctrl (la « Touche spéciale » des réglages) + une flèche ne remettait que la rotation et l'inclinaison (retour animé) ; la distance restait, et Ctrl + Page haut / Page bas zoomait comme sans Ctrl.
- `Jeu.reinitialiser_camera` : la position (`recentrer_camera`, si `_camera_pilotable` : terrain libre d'une ville, d'un donjon ou d'une tour, lieu sans interdiction de tourner) ET la distance (`distance_par_defaut`, retour animé de l'avance #170). Appelée par `_maj_camera` pour Ctrl + une des quatre flèches (sur la carte du monde et dans un lieu qui interdit de tourner, seule la distance revient) et par `_maj_distance_clavier` pour Ctrl + Page haut ou Page bas (même condition que la molette : `_zoom_possible`).
- Les touches tenues ensuite ne font plus rien ; Ctrl relâchée avant la touche, la touche seule n'agit pas tant qu'elle n'est pas relâchée (même logique que les deux flèches opposées). Les deux touches de distance sans Ctrl ne remettent toujours que la distance (#167), les deux flèches opposées que la position.
- Aide de la page Commandes mise à jour.
- Tests : `tools/test_camera_ctrl_tout.py` (15 tests : les trois états reviennent depuis plusieurs départs, par animation monotone, sans Ctrl rien ne change, carte du monde / lieu bloqué / hors terrain, effet d'écran).

### À trancher / non vérifié
- **Supposé** : « tous les états de la caméra » = rotation, inclinaison et distance ; « touche du clavier pour la caméra » = les quatre flèches, Page haut et Page bas (ou leurs remplaçantes réattribuées).
- Pendant un effet d'écran, Ctrl + Page haut / Page bas ne remet que la distance (la molette zoome encore à ce moment, les flèches ne tournent pas).
- **Sous Windows** : Ctrl + flèche, Ctrl + Page haut, Ctrl + Page bas au clavier réel.

## Avance #175 : croix réduite de 25 % par défaut (#172, 04/11/2026)

### Demande (D-228, 04/11 11 h 30)
« Finalement réduit la taille de la croix de 25 % par défaut »

### Fait
- `hud_mobile.DIAM_CROIX` = 1,5 x 161,28 (241,92 unités sur 800 de haut ; à 1080 de haut : 327 px) : 25 % de moins que le double de l'avance #169 (0,75 x 2 = 1,5 fois le mobile). Le réglage « Taille de la croix » (50 à 200 %, 100 % par défaut) s'applique toujours par-dessus ; 67 % redonne la taille du mobile. Le plafond des fenêtres étroites (`LARGEUR_CROIX_MAX` = 0,75 de la largeur) et le seuil de la course (`COURSE_SEUIL`) ne changent pas.
- Test : `tools/test_croix_course.py` mis à jour (constante, diamètres à 800 de haut, 16/9 jamais réduite).

### À trancher / non vérifié
- **Supposé** : « de 25 % » = 25 % de moins que la taille par défaut actuelle (et non 25 % de moins que le mobile) ; un `reglages.json` à 100 % prend la nouvelle taille sans rien changer.
- **Sous Windows** : la taille ressentie.

## Avance #176 : le retour du zoom va à la vitesse du recentrage des directions (#173, 04/11/2026)

### Demande (D-228, 04/11 11 h 30)
« La transition pour remettre le niveau de zoom par défaut doit aller à la même vitesse que pour les directions »

### Fait
- `fenetre.CAM_RECENTRE_DIST` = `CAM_RECENTRE_LACET` (240 par seconde au minimum, au lieu de 60 % par seconde en #170) ; la loi reste « au moins ce minimum, ou 5 x l'écart par seconde, fois « Vitesse de caméra » » comme pour la rotation. Un écart de X % se résorbe donc comme un écart de X degrés : au clavier (les deux touches, Ctrl + touche de caméra) comme à la souris (Ctrl + molette, Ctrl + clic molette), et rotation, inclinaison et distance arrivent ensemble à l'origine pour Ctrl + touche. De 200 % à 100 % : environ 21 images (0,35 s) au lieu de 37 (0,6 s).
- Tests : `tools/test_camera_ctrl_tout.py` (16) : rotation et distance arrivent à la même image (à une image près) pour sept paires d'écarts égaux, et suivent la même part de l'écart restant en route ; `test_distance_camera_clavier.py` (28) : constante égale à celle de la rotation, durées et pas maximal d'une image.

### À trancher / non vérifié
- **Supposé** : « la même vitesse » = les mêmes nombres que la rotation (240 par seconde) appliqués aux pourcents ; l'inclinaison garde son minimum propre (90 degrés par seconde, plage plus étroite).
- **Sous Windows** : le ressenti du retour du zoom et des directions ensemble.

