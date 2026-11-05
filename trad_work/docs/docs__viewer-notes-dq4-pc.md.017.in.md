### Fait
- `battle_history.py` : `Suivi` note le sort de chaque monstre (`vaincu` / `fui` / `disparu`, un seul), les objets ; `ennemis()` rend `{nom, total, vaincus, fuis, disparus}` ; `fabriquer_combat` ajoute `objets: [{nom}]` (victoire seulement) ; trois crochets internes (`CROCHETS_INTERNES`, instruction vérifiée : sur un moteur différent seul cet événement est perdu) ; noms d'objets et de monstres demandés au moteur.
- `history.py` : `Element.objets`, `ligne_espece` (« Gluant ×3 : 1 vaincu, 1 enfui, 1 disparu » ; « Golem : resté » ; tous vaincus : « Gluant ×3 »), `lignes_combat` (une ligne par espèce, puis « Or : N     Expérience : N », puis « Objets : a, b »), validation `ennemis_valides` / `objets_valides` ; **les favoris d'avant (sans `fuis`, `disparus`, `objets`) sont relus tels quels** (0 et liste vide).
- `ui_history.py` : une boîte de combat a autant de lignes que son texte (entête comprise), 3 au moins, **12 au plus** (`MAX_LIGNES_COMBAT`), puis une boîte suivante (« 2/2 ») ; le cadre du jeu (frameData 192, 9 morceaux, coins de 12 unités) est **étiré** par `etirer_cadre` (les sommets de la moitié haute montent, les coins gardent leur taille, le bas ne bouge pas) ; `disposer` accepte une hauteur par boîte. Les dialogues gardent la boîte de 3 lignes.
- Tests : `test_battle_history.py` (71 : crochets, sorts, objets, noms demandés au moteur, moteur inattendu, vrai moteur avec fuite / disparition / objet) et `test_message_history.py` (112 : hauteur des boîtes, cadre étiré avec la vraie mise en page, favoris complets et ancien format).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (boîtes de combat plus hautes, cadre bien étiré ; un combat réel avec un monstre qui s'enfuit ; un objet gagné).
- **Non vérifié** : un monstre qui « disparaît » dans un vrai combat (vérifié seulement par un état forcé dans la mémoire, pas par un monstre qui disparaît de lui-même) ; le comportement du jeu quand le sac est plein (les objets restent listés) ; si le groupe a fui alors que **tous** les monstres avaient déjà fui ou disparu (l'issue resterait « Fuite »).
- Un monstre « resté » = ni vaincu, ni enfui, ni disparu quand le combat se termine (fuite ou défaite du groupe) : c'est une déduction (le moteur ne le dit pas).
- En défaite, comme en fuite, le jeu ne verse ni or, ni expérience, ni objets : rien n'est affiché.
- Hors périmètre, constaté : `test_defaite` du vrai moteur (3 × monstre n° 150) donne une victoire avec la sauvegarde de ce poste (échec identique avant ce correctif).

## Avance #153 : touches de distance de la caméra (#146, 04/11/2026)

### Demande (D-225, 03/11 23 h 47)
« J'ai dit qu'on supprimait l'option pour choisir la vitesse de transition non ? Comme pour les options pour changer la distance de la caméra depuis le menu, il faut plutôt ajouter 2 nouvelles entrées pour les contrôler aussi au clavier ». **Lecture retenue (supposé)** : le réglage « Vitesse de transition » disparaît (c'est #101, pas encore faite : elle reste ouverte et n'est pas touchée ici) et la distance de la caméra, déjà réglable par le curseur « Distance caméra » et la molette, reçoit deux touches réattribuables.

### Fait
- `settings.py` : deux actions, `cam_pres` (« Caméra (Rapprocher) », pavé + ou E) et `cam_loin` (« Caméra (Éloigner) », pavé − ou W). Touches par défaut libres (ni ZQSD, ni flèches, ni les chiffres des états, ni V, ni M, ni H, ni A / R). Un ancien `reglages.json` reçoit ces touches ; si le joueur avait pris l'une d'elles pour une autre action, elle lui reste et la nouvelle action n'a pas cette touche.
- `window.py` : `_maj_distance_clavier` (à chaque image affichée, avec `_maj_camera`) : un pas de **5 %** à l'appui, puis, touche maintenue plus de **0,4 s**, un pas toutes les **0,08 s** (environ 60 % par seconde) ; arrondi au pas de 5 % (91 % → 90 % ou 95 %) ; bornes **50 à 200 %** ; passe par `regler_distance`, donc la même valeur que le curseur, la molette et les infos F1. Mêmes conditions que la molette (`_zoom_possible` : terrain libre d'une ville, d'un donjon, d'une tour ou carte du monde ; jamais un menu, un message ou un combat). Les deux touches ensemble ne font rien.
- `pause.py` : deux lignes dans la section « Caméra au clavier » de Commandes, à la suite des quatre flèches, avec une aide.
- Tests : `tools/test_distance_camera_clavier.py` (18 tests : actions et touches par défaut sans conflit, ancien fichier, réattribution, lignes du menu, pas, répétition, bornes, arrondi, rien hors du terrain). Suites voisines OK.
- **Établi (vraie fenêtre et vrai moteur, sous Xvfb, sauvegarde 2 = ville de Caf1)** : les événements de touche simulés par `on_key_press` / `on_key_release` font passer la distance de 100 % à 105 % à l'appui, puis, maintenue, jusqu'à 200 % (pas de 5 %, environ 60 % par seconde) ; pavé + et E rapprochent (195 → 190 …), pavé − et W éloignent ; la valeur s'arrête à 200 %.

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (touches, cadence de la répétition, lignes du menu).
- Les touches par défaut (pavé + / −, E / W) sont un choix de Claude : modifiables dans Commandes.
- Pas de 5 % et cadence de répétition : choisis pour coller au curseur du menu (pas de 5 %) ; à ajuster si trop lent ou trop rapide.
- « Vitesse de transition » est toujours dans Commandes (#101 non faite).
- Hors périmètre, constaté : `test_vitesse_combat.test_hors_combat_la_marche_garde_ses_reglages` échoue (faux jeu du test sans `pause`, depuis #151).

## Avance #154 : essai de zoom du ciel de l'écran-titre (#130, 04/11/2026)

### Demande (03/11 23 h 08)
« Pour le fond qui défile de l'écran titre, possible de zoomer l'image pour ne garder que la texture sans effet de répétition ? Au moins pour essayer. »

### Fait (essai, par défaut)
- `title_sky.py` : `zoom_ecran(aspect)` = `aspect / 0,5625` (16/9 : **x 3,16** ; 21/9 : x 4,15 ; 1 en portrait) et `matrice_zoom(M, z)` (x et y d'écran multipliés par z autour du centre, profondeur intacte).
- `window.py` : au dessin du décor du titre, le groupe du ciel (« kumo », seul dans son groupe de texture : vérifié à l'exécution, sinon repli sur les bandes) est tracé avec `matrice_zoom(M, zoom)` ; les bandes étirées ne sont plus ajoutées. La fenêtre entière montre alors ce que montrait la zone portrait du jeu d'origine : moins d'un carreau de large, donc **aucune répétition horizontale**, et un peu plus d'une rangée de haut.
- Retour à l'ancien rendu (bandes étirées) : `DQ_CIEL_BANDES=1`. Zoom d'essai : `DQ_CIEL_ZOOM=2.5` (valeur forcée, jamais inférieure à 1).
- Tests : `tools/test_titre_ciel.py` (26 tests, dont 4 nouveaux : zoom selon le format, fenêtre entière = zone portrait, variable d'essai, matrice).

### Établi (captures sous Xvfb, 1920 x 1080, avant / après)
- Avant : les mêmes nuages reviennent 3 à 6 fois (en largeur comme en hauteur), atténués par les bandes étirées.
- Après : un seul grand nuage, aucune répétition visible, mais l'image est **nettement plus floue** (la texture du ciel est petite : x 3,16) ; le dégradé et les couleurs restent ceux du jeu. Le logo, le dragon et l'île ne changent pas.

### À trancher / non vérifié
- **Sous Windows** : à juger par Sylfried (netteté, vitesse de défilement apparente : le ciel glisse à la même vitesse dans la texture, donc x 3,16 plus vite à l'écran en valeur absolue).
- Une ou plusieurs valeurs intermédiaires (ex. `DQ_CIEL_ZOOM=2`) gardent un peu de répétition mais restent plus nettes ; non essayées (supposé).
- Le mode « agrandi » (F2, texture du décor en HD) pourrait adoucir le flou : non essayé sur le titre.
- Vu aussi en 21/9 (2560 x 1080, zoom x 4,15) : aucune répétition, encore plus flou.

## Avance #155 : bulles cliquables et rond central de la croix (#131, 04/11/2026)

### Demande (D-225, 03/11 23 h 19)
« Il faudrait faire en sorte qu'en cliquant sur une bulle (au-dessus d'un PNJ, d'un coffre...) je puisse valider l'action et faire ce qui est prévu, comme si j'appuyais sur la touche espace. Sinon, dans la version mobile, le cercle au centre de la croix directionnelle sert aussi de touche d'action : il faudrait reproduire l'exact même comportement pour cette touche, ainsi que son affichage lorsqu'on clique ou qu'on peut cliquer. »

### Établi
- Une bulle est le carré de 0,96 du paquet 19 / 20 (`Moteur.icones`, emplacements 0 à 15) ; le paquet 19 avec un emplacement **>= 16** n'est pas une bulle mais le clignotement de la croix (`TouchPad.SetPadBlink`) : il était ignoré, il est désormais lu (`Etat.pad_clignote`, numéro d'icône < 0 = arrêt).
- Un toucher de la croix (relâchement sans glissement) donne au moteur le bit de la touche d'action (analyse de `TouchPad.internalUpdate`, déjà relevée avant cette avance) ; que le « glissement » commence au seuil de la zone morte (`c_MoveThreshold` 10 unités, 0,124 du rayon) est une **déduction** (supposé).
- Mesuré au vrai moteur et à la vraie fenêtre (Xvfb, sauvegarde 2, bulle forcée au-dessus du héros) : le carré de la bulle est projeté avec la matrice de la ville (même formule que `DQ_PROJ`) ; un clic au centre donne `clic_a`, un clic à 5 pixels du coin de l'écran rien ; un toucher du rond central donne `clic_a`, un appui à 0,3 du diamètre (glissement vers la droite) pas d'action au relâchement ; `pad_clignote` vrai dessine la boule orange et son halo.

### Fait
- (retiré par l'avance #157 : `bulles.py`, projection et clic sur la bulle) ; `window.py` : `_icones` garde les 4 coins monde de chaque bulle (`icone_quads`), `_bulle_sous` les projette (matrice de la dernière image) et `on_mouse_press` donne `clic_a` (la touche A, comme l'espace) sur le terrain libre uniquement ; clic droit inchangé (annuler).
- `hud_mobile.py` : `croix_glisse` (sorti du rond central), `croix_relacher()` (True = toucher du rond central) ; `fenetre.on_mouse_release` donne `clic_a` sur le terrain libre ; le rond central s'éclaire (boule orange + halo, morceaux `CurLight` et `CurBS` de la feuille `Button`) pendant un toucher et **clignote** (période de 1 s) quand le jeu le demande ; les directions ne changent pas.
- Tests : `tools/test_bulles_et_croix.py`, devenu `tools/test_croix_et_clic.py` à l'avance #157 (27 tests : projection, quadrilatère, paquets 19, toucher / glissement de la croix, clic sur la bulle, terrain libre seulement, emplacement 0).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (clic sur une bulle réelle, toucher de la croix).
- **Supposé** : la zone du toucher est le seuil de glissement du jeu (0,124 du rayon : environ 14 pixels de rayon en 1080p, plus petit que la boule dessinée) ; si c'est trop petit à la souris, l'agrandir (par exemple au rayon de la boule, 0,25) est un réglage d'une constante.
- **Supposé** : l'éclairage pendant le toucher et la période de clignotement (1 s) sont des choix du portage (les constantes du jeu, `MOVE_WAIT_TIME` / `MOVE_LIMIT_ALPHA`, sont inutilisées) ; quand le jeu envoie ce clignotement (tutoriel seulement ? à chaque action possible ?) n'a pas été relevé.
- La bulle n'a pas été vue dessinée à côté de son carré projeté (la sauvegarde de ce poste est sur l'écran noir du chapitre 1) : la projection est celle de `DQ_PROJ`, mais l'alignement visuel reste à confirmer.
- Une bulle cachée derrière un personnage ou un décor reste cliquable (pas de test de profondeur).

## Avance #156 : sprites inclinés vers la verticale du monde (#134, 04/11/2026)

### Demande (D-225, 03/11 23 h 27)
« Il y a une sorte d'effet d'optique avec ce PNJ, autant l'aplatissement sur les bords comme on a vu c'est nickel, autant quand mon perso monte ou descend sur la carte, j'ai l'impression que les sprites des PNJ (peut-être autres ?) se penchent alors que sur mobile ils restent bien droits. »

### Établi
- Depuis la correction des bords (`Jeu._panneau_ville`), le panneau d'un personnage est **exactement vertical à l'écran** partout (bords gauche / droit à moins de 0,01 px de la verticale, mesuré sur 15 états de caméra et 30 positions : `tools/test_sprites_droits.py`).
- Les **verticales du monde** (arêtes de murs, portes) penchent, elles, à l'écran : 11 à 19 degrés à 9 unités du centre en 16/9 (caméra à 47 degrés), 4 à 6,5 degrés sur le portrait d'origine ; l'angle change de plus de 5 degrés quand le héros monte ou descend (le personnage change de hauteur à l'écran). Le sprite reste à 0 : il paraît pencher **par rapport au décor** (c'est l'illusion d'optique de #134, cause établie par le calcul, pas par un essai sur Windows).
- Rendu réel (Xvfb, sauvegarde 2, château de Bastione, `DQ_SPRITE_INCLINAISON` à 0, 50 et 100 dans la même image du jeu) : à 0 le PNJ du bord gauche est droit, à 100 il penche du même côté que les murs voisins, à 50 entre les deux, pieds au même endroit.

### Fait
- `Jeu._panneau_ville(..., inc)` : après la correction des bords, le panneau est **cisaillé** vers la verticale du monde, pieds fixes : le haut glisse de `inc` x tan(inclinaison d'une verticale du monde au pied) x hauteur à l'écran, à la **même profondeur** (z-buffer, recouvrements, taille et position du bas inchangés). Au centre de l'image la verticale du monde est droite : rien ne change.
- `Jeu._inclinaison_sprites()` : 0,5 par défaut (essai), variable d'environnement `DQ_SPRITE_INCLINAISON` de 0 (bords verticaux, état d'avant) à 100 (parallèle aux murs).
- Tests : `tools/test_sprites_droits.py` (10 tests : bords verticaux partout, profondeur et centre inchangés, garde-fou du panneau d'origine, constat des verticales du monde, angle exact du cisaillement, taille / profondeur inchangées, écart sprite / mur divisé par deux, réglage par variable d'environnement, caméra inconnue).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried que le sprite ne « se penche » plus quand le héros monte ou descend ; si le cisaillement lui paraît trop fort ou trop faible : `DQ_SPRITE_INCLINAISON=30` ou `70` (ou 0 pour revenir en arrière), puis fixer la valeur définitive.
- **Supposé** : 50 % par défaut (milieu entre « droit » et « parallèle aux murs ») ; le cisaillement d'un sprite en pixel art peut montrer de légers escaliers sur les bords.
- Sur le mobile, les sprites sont aussi cisaillés par la perspective du panneau d'origine (4 à 6 degrés, non mesuré sur l'appareil) : la comparaison avec « droits sur mobile » n'a pas pu être faite ici.

## Avance #157 : plus de clic sur la bulle, la croix s'anime (#131, 04/11/2026)

### Demande (D-226, 04/11 09 h 44)
« Finalement supprime le fait de "cliquer sur la bulle", cliquer partout sur l'écran suffit, mais par contre je n'ai pas l'animation sur le joystick de la croix directionnelle quand une action est réalisable. »

### Établi
- Le jeu d'origine ne lie le clignotement de la croix (`TouchPad.SetPadBlink`, paquet 19 avec un emplacement >= 16) qu'à son **tutoriel** (voir `docs/audit/specs/numpad_menus_audit.md`) : sur une bulle ordinaire le moteur n'envoie rien, d'où l'absence d'animation constatée par Sylfried.
- Rendu réel (Xvfb, sauvegarde 2, château de Bastione, bulle forcée au-dessus du héros) : sans bulle la boule est grise ; avec une bulle elle est orange avec son halo ; la bulle retirée, elle redevient grise.

### Fait
- Retrait de `bulles.py`, de `Jeu._bulle_sous` et de `icone_quads` ; `on_mouse_press` : un clic gauche sur le **terrain libre** (ni menu, ni message, ni carte, ni combat, ni effet), hors boutons et croix du HUD, donne la touche d'action (`clic_a`, comme l'espace). Clic droit = annuler, inchangé.
- `hud_mobile.Boutons.action_possible()` : vrai quand le jeu fait clignoter la croix (paquet 19) ou, sur le terrain libre, quand une bulle d'icône est affichée (position posée, opacité > 0,02) ; la croix pulse alors (boule orange et halo, 1 s).
- Tests : `tools/test_croix_et_clic.py` (23 tests : paquet 19, toucher et glissement de la croix, `action_possible`, clic n'importe où, pas de clic d'action hors du terrain libre).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (clic n'importe où, animation de la croix devant un personnage ou un coffre).
- **Supposé** : « cliquer partout » = un clic gauche sur le terrain libre donne la touche d'action (lecture de sa phrase) ; « action réalisable » = une bulle d'icône est affichée sur la cible ; l'animation est une extension du portage (le jeu d'origine ne l'a que pour son tutoriel).
- Un clic gauche sur le terrain sans cible fait la même chose que la touche d'action sans cible (rien, ou le message du jeu).

## Avance #158 : caméra au clavier en continu, Page haut / Page bas, plus d'option de distance (#146, 04/11/2026)

### Demande (D-226, 04/11 09 h 44)
« Supprime l'option pour changer la distance de la caméra. Touches par défaut pour rapprocher la caméra : Page haut. Touche par défaut pour éloigner la caméra : Page bas. Ces 2 touches ne doivent pas être saccadées, il faut un effet fluide pour que tant qu'on maintient la touche la caméra avance ou recule (à la même vitesse qu'elle tourne). »

### Établi
- Le pas de 5 % avec répétition (avance #153) est remplacé par un mouvement **continu** : `Jeu._maj_distance_clavier` change la distance à chaque image selon le temps écoulé, de `CAM_DIST_VIT` = `CAM_LACET_VIT` (100) pourcents par seconde, multiplié par « Vitesse de caméra » et par le multiplicateur de l'accélérateur si la touche est tenue, comme la rotation. À vitesse x1 : de 100 % à 50 % en 0,5 s, de 100 % à 200 % en 1 s. Le zoom garde sa valeur exacte (le réglage enregistré est arrondi au pour cent).
- Une touche ne sert qu'à une action (`test_touche_menu`) : Page haut / Page bas étaient la seconde touche par défaut de L / R (pages des menus du jeu) ; L / R gardent **A** et **R**. Le menu d'Échap et l'historique lisent Page haut / Page bas directement et ne changent pas.
- Un ancien `reglages.json` : les défauts de l'avance #153 (pavé + / −, E / W) deviennent Page haut / Page bas, et Page haut / Page bas sont retirées de L / R ; un choix du joueur est gardé (une touche déjà prise par un autre choix n'est pas reprise à la caméra).
