## Avance #177 : ciel du titre à plat, à la hauteur de la fenêtre (#174, 04/11/2026)

### Demande (D-228, 04/11 11 h 30)
« Pour le fond de l'écran titre ajuste la hauteur pour automatiquement s'adapter à la hauteur de la fenêtre, et ça sera sur la largeur que la répétition se fera, et applique bien comme convenu les effets visuels qui doivent être appliqués (je crois qu'il y a une sorte d'effet de vague) » ; 11 h 44, devant la capture 16/9 : « Ce que tu as fait sur cette version est très bien ! Avec les effets visuels comme indiqué et c'est parfait ! »

### Fait
- `ciel_titre.ciel_ecran` : le ciel est un maillage plein écran en coordonnées normalisées (au fond, sans projection) ; la texture (carrée, 256 x 256) a pour HAUTEUR celle de la fenêtre (v de 0,998 en bas à 0,002 en haut, comme les rangées d'origine) à toute taille de fenêtre, sans agrandissement supplémentaire, et se répète sur la LARGEUR (`aspect` fois : 1,78 en 16/9, 2,33 en 21/9, moins d'une fois en portrait). Texture en REPEAT : aucune couture.
- L'effet de vague de l'ancien rendu en bandes est conservé et appliqué à toute la largeur : étirure horizontale ondulée (`etirure_plate`, intégrale exacte de `ETIRURE` : pente 0,52 à 1,48, jamais de retournement) et glissement vertical (`glissement_plat`, nul en haut et en bas). Il est fixe à l'écran et la texture défile dessous : les nuages se déforment en passant, et les copies d'une même tuile ne se ressemblent pas.
- Le dégradé de teinte des rangées d'origine (orange en haut et en bas, blanc au milieu) est repris tel qu'il apparaissait à l'écran (`degrade_ecran` : projection des bords et de points intermédiaires des quatre rangées par la matrice de la caméra) ; les coupures du dégradé deviennent des lignes du maillage.
- Défilement : même sens et même vitesse en tuiles que l'objet d'origine (une tuile pour 11,5 unités, 599 images) ; mesuré sur 120 images : le ciel à plat et le rendu en bandes glissent dans le même sens (vers la gauche). Le ciel étant plus grand (tuile = hauteur de la fenêtre), il avance plus vite en pixels.
- `fenetre._tracer_ciel_plat` remplace le tracé du groupe du ciel (seul dans sa texture) ; toute erreur coupe ce rendu et laisse le tracé d'origine (message sur la sortie). `DQ_CIEL_AGRANDI=1` redonne l'essai #130 (ciel agrandi), `DQ_CIEL_BANDES=1` les bandes, `DQ_CIEL_COPIES=1` les copies ; `DQ_CIEL_TUILE` (essai) change la largeur de la tuile en hauteurs de fenêtre.
- Tests : `tools/test_titre_ciel.py` (34, dont 8 nouveaux) : hauteur de texture = hauteur de fenêtre à sept formats, étendue horizontale = `aspect` tuiles, vague jamais retournée et sans dérive, défilement = décalage de u seul, triangles de même sens et sans trou (aire totale = rectangle), dégradé sommet par sommet, repli sans caméra valable. Captures 16/9, 21/9 et portrait contrôlées ; 16/9 vue et validée par Sylfried dans l'interface.

### À trancher / non vérifié
- **Supposé** : « effet de vague » = l'ondulation `ETIRURE` / `GLISSE` des bandes (seul effet de ce genre dans les notes) ; « comme convenu » = ce rendu, la teinte d'origine et la vitesse d'origine. Si un autre effet avait été convenu, il manque.
- La texture de 256 x 256 est agrandie à la hauteur de la fenêtre (1080 px en 16/9) : le ciel est flou, c'est la conséquence directe de « la hauteur de la fenêtre ».
- **Sous Windows** : le rendu réel à 1866 x 1050 et plein écran (netteté, raccords de tuile, sens et vitesse du défilement).

## Avance #179 : aucune pause dans aucun menu (#178, 04/11/2026)

### Demande (D-229, 04/11 11 h 40)
« Le menu historique met le jeu en pause, il ne faut aucune pause dans aucun menu »

### Fait
- `Pause.PAGES_FIGEES` est vide (c'était `('historique', 'quitter')`) : le jeu, le son et l'horloge tournent derrière TOUTES les pages du menu Paramètres, sans recevoir ni touche ni clic (`Jeu.tick`, inchangé). Le mécanisme d'arrêt (`fige_le_jeu`, `_synchroniser_gel`, retour anticipé de `_boucle`) est gardé tel quel, inutilisé : une page ajoutée à `PAGES_FIGEES` l'arrêterait de nouveau (cela contredirait D-229).
- Mesuré dans le jeu (ville `maout`, historique ouvert à l'image 60) : écart moyen entre les images 90 et 200 de la scène derrière la fenêtre = 0,0 avant (jeu figé), 4,07 après (le jeu avance).
- Conséquence traitée : le jeu écrit maintenant dans l'historique pendant qu'on le lit. `VueHistorique.suivre_le_jeu` (appelée à chaque image par `Pause.maj` sur la page Historique) remplace la liste par la liste à jour quand la vue est tout en bas : le message choisi reste le même (reconnu par son objet), sauf s'il était le dernier (le choix suit alors le plus récent). Plus haut dans la liste, pendant un glissement ou avec la barre, la liste ne bouge pas (la lecture ne saute pas) ; elle se met à jour au retour en bas. Onglet Combats et « Favoris seulement » : mêmes règles.
- Tests : `tools/test_parametres_sans_pause.py` (15) : aucune page du menu (toutes les `_e_*` plus racine, historique et quitter) ne fige le jeu, `PAGES_FIGEES` vide, le mécanisme d'arrêt est essayé avec une page de test ; `tools/test_historique_messages.py` (122) : 10 tests de `suivre_le_jeu` (rien de neuf, nouveau message en bas, choix ailleurs qui ne saute pas, lecture plus haut, glissement, onglet Combats, liste pleine, favoris seulement, sans historique, appel par `Pause.maj`).

### À trancher / non vérifié
- **Supposé** : « aucun menu » = toutes les pages du menu Paramètres (Historique et Quitter comprises), pas les fenêtres propres du jeu.
- Effet voulu à connaître : un combat qui avance seul (vitesse rapide) ou un message minuté continue pendant la lecture de l'historique, et les rencontres aléatoires peuvent survenir pendant la question « Quitter » (le jeu ne reçoit aucune entrée).
- **Sous Windows** : historique ouvert, la scène derrière bouge, le son continue, la liste reste lisible quand un message ou un combat s'ajoute.

## Avance #181 : PNJ sans le cisaillement de #156 (#180, 04/11/2026)

### Demande (D-229, 04/11 11 h 40)
« Finalement remet l'affichage des PNJ comme sur la version mobile, de l'exact même façon, car là il y a des comportements bizarres où on peut les voir s'étirer et autre quand ils s'approchent du bord »

### Établi
- Comparaison de rendus (village de Maout, 1920 x 1080, même image du jeu) près des bords gauche / droit : (1) état de la veille = correction des bords + cisaillement à 50 % de #156 : parallélogramme, tête décalée, pixels en escalier ; (2) correction des bords seule (état d'avant #156) : rectangle droit, proportion constante (0,738) ; (3) panneau brut d'origine (`DQ_CORRECTION_BORDS=0`) : penché vers l'extérieur de 15 à 20 degrés et trop large (jusqu'à 0,9 au lieu de 0,75) en 16/9.
- Le cisaillement (#156) est la seule modification récente du dessin des sprites : c'est lui qui crée l'étirement signalé.

### Fait
- `Jeu.INCLINAISON_SPRITES_DEF` : 0,5 -> 0 (bords exactement verticaux). Rendu **identique au pixel** à l'état d'avant #156 (0 pixel de différence, mesuré). L'essai reste disponible : `DQ_SPRITE_INCLINAISON` de 0 à 100. La correction des bords (toujours complète) est inchangée.
- Tests : `tools/test_sprites_droits.py` (11) : nouveau test de l'état livré (correction 1, inclinaison 0 : rectangle droit et proportion 0,738 +- 0,008 pour les 15 états de caméra et 30 positions), test de la variable d'environnement adapté (défaut 0).

### À trancher / non vérifié
- **Supposé** : « comme sur la version mobile, de l'exact même façon » = sprites droits aux proportions constantes, comme sur le portrait du mobile (le panneau d'origine n'y penche que de 4 à 6 degrés), donc l'état (2). Le panneau brut (3) n'est PAS remis : il reproduirait en 16/9 l'inclinaison et l'élargissement que la correction des bords (« exactement la correction que j'attendais », #43) retire. Si Sylfried voulait le brut : `DQ_CORRECTION_BORDS=0` (ou changer `_correction_bords`).
- L'impression d'optique de #134 (le sprite paraît pencher par rapport aux murs quand le héros monte ou descend) revient : c'est le prix du retour à l'état d'avant (cause établie : les verticales du monde penchent à l'écran, le sprite reste droit).
- **Sous Windows** : PNJ près des bords gauche et droit, droits et sans étirement.

## Avance #183 : murs des intérieurs, faces arrière cachées (#182, 04/11/2026)

### Demande (D-230, 04/11 13 h 25)
« En intérieur les murs doivent devenir transparents, je crois que le comportement exact c'est que les faces externes n'ont pas de textures et donc si on tourne la caméra alors on doit automatiquement pouvoir voir à travers les murs (regarde comment c'est fait dans le jeu et refais le pareil) »

### Établi
- Lu dans le paquet de données (ShaderLab `culling` de chaque `Shader` « Custom/... ») : `fld_normal`, `fld_atest`, `fld_trans`, `fld_transz`, `fld_normal_sepia`, `fld_atest_sepia`, `fld_trans_sepia` = **culling 2 (Cull Back)** ; `Custom/Field` (carte du monde) = 0 (sans culling) ; `Custom/ImdChara` = 2 (déjà géré pour les modèles 3D) ; `CharaShadow` = 2 ; `Chara`, `DssaChara`, `DssaMonster*`, `Effect0` = 0.
- La visionneuse dessinait le décor sans culling : les faces externes des murs, normalement invisibles, bouchaient la vue quand la caméra tournait. Pas de texture transparente dans les données : ce sont les faces arrière qui sont supprimées par le shader.

### Fait
- `Jeu._culling_decor(actif)` : culling des faces arrière, face avant = sens horaire à l'écran (Unity est en main gauche ; `GL_CW`, comme les modèles 3D). `_tracer_decor` le règle groupe par groupe (opaques puis transparents), sauf le ciel du titre (ses propres sommets, `ciel_plat` / `ciel_zoom`), et le coupe après les groupes (bandes / copies du ciel, ombres, sprites, effets inchangés). `DQ_DECOR_CULL` : 0 = ancien rendu, 2 = sens inverse (essai : il cache les sols et montre les faces externes, donc faux).
- Mesure (même image) : église `mak1f1` caméra tournée de 150 degrés : le mur de devant disparaît et la salle, le tapis et le héros se voient ; caméra de base : 0 pixel de différence dans `mak1f1` et `mlb1a`, 58 à 235 pixels dans `chf1b` et `caf1`, 1 347 sur 576 000 dans le village de Maout (arêtes des clôtures, vues de leur face avant : rien de manquant) ; titre : 53 pixels.
- Tests : `tools/test_decor_culling.py` (5) : réglages GL par défaut, coupé, variable d'essai, groupe par groupe sauf le ciel, autres réglages GL inchangés.

### À trancher / non vérifié
- **Supposé** : le sens des faces est celui des triangles du cache (aucun objet de carte à échelle négative sur les 670 cartes : 0 sur 18 374, donc pas d'inversion à corriger) ; une échelle négative dans le modèle lui-même (Transform local, absente du cache) n'a pas été cherchée.
- Pas regardé : les fonds de combat (`btl_*`, même chemin de dessin, mêmes shaders) et les donjons.
- **Sous Windows** : intérieurs (église, château, maisons), donjons, fonds de combat : rien de manquant dans la vue normale, murs de devant invisibles caméra tournée.

## Avance #185 : PNJ au panneau brut du jeu, sans s'aligner sur la caméra inclinée (#184, 04/11/2026)

### Demande (D-231, 04/11 13 h 25)
« Reviens à la position brute des PNJ pour le moment, exactement comme dans le jeu, ils doivent garder aussi le même comportement et avec le nouveau système de caméra ils ne doivent pas s'aligner si on monte ou descend la caméra »

### Établi
- Après #181 (cisaillement retiré), les PNJ restaient reconstruits à l'écran par la correction des bords (#134 : bords verticaux, proportion 0,738, `Jeu._panneau_ville(t = 1)`) : ce n'est pas le panneau du jeu (`Chara.normalBillboard` : rectangle 0,48 x 0,64 qui prend la rotation de la caméra, sommets décalés en profondeur de 0,185 au bas et 0,65 au haut vers la caméra).
- Le panneau d'origine, avec la rotation de la caméra de la VUE, se redresse face à la caméra à chaque inclinaison (Haut / Bas) : le personnage « s'aligne » sur la vue (en vue de dessus, il reste de face comme un autocollant).

### Fait
- `CORRECTION_BORDS_DEF = 0.0` : `Jeu._correction_bords()` vaut 0 par défaut (panneau d'origine, `_panneau_ville` renvoie les sommets du jeu) ; `DQ_CORRECTION_BORDS=100` ou `--correction-bords 100` redonnent la correction complète.
- `Jeu._camera_ville` calcule aussi `self._cadre_sprites` : le repère (droite, haut, avant) de la caméra DU JEU avec la rotation autour du héros (lacet) mais SANS l'inclinaison de la visionneuse (même formule que `_cadre_jeu` : tangage du jeu - `lookDownAdjust`). `Jeu._repere_sprites(cam3d, corr)` le donne à la boucle des sprites quand la correction est nulle ; correction > 0 : repère de la vue (la reconstruction à l'écran en a besoin) ; pose couchée, ombres, bulles : inchangés. `DQ_SPRITES_SUR_VUE=1` redonne l'alignement sur la vue (essai).
- Effet : au cadrage du jeu (aucune inclinaison) le rendu est exactement celui du mobile (PNJ qui penchent vers l'extérieur près des bords : défaut connu de l'original, accepté « pour le moment ») ; Haut / Bas ne changent plus le panneau (4 coins identiques en monde) ; Gauche / Droite le font tourner de face avec l'inclinaison du jeu.
- Rendu (Maout, 1920 x 1080) : cadrage du jeu normal ; inclinaison forte : les PNJ se couchent (ils sont debout dans le monde, vus d'en haut) au lieu de rester de face.
- Tests : `tools/test_sprites_droits.py` (18) : défaut = panneau d'origine, correction complète toujours droite, repère des sprites = repère du jeu, inchangé par Haut / Bas (+- 15, 30, 80 degrés), suit le lacet, caméra libre et mini-jeux.

### À trancher / non vérifié
- **Supposé** : « ne doivent pas s'aligner si on monte ou descend la caméra » = le personnage ne se redresse plus face à la caméra quand on l'incline. Conséquence : à forte inclinaison (vue de dessus) les PNJ et le héros paraissent couchés, comme des objets debout. Si tu préfères qu'ils restent de face à la caméra : `DQ_SPRITES_SUR_VUE=1` (ancien alignement), à passer en réglage ou en comportement par défaut.
- Non vérifié : le rendu sous Windows ; les donjons, tours et la pose couchée (inchangée) n'ont pas été regardés un par un.

## Avance #187 : l'historique seulement quand le joueur a la main (#186, 04/11/2026)

### Demande (D-232, 04/11 13 h 25)
« L'historique doit pouvoir être accessible uniquement quand j'ai le contrôle de mon perso, donc pas pendant un combat ni pendant un moment où le jeu prend le contrôle »

### Établi
- Avant : la touche H ouvrait l'historique en ville, sur la carte du monde et en combat, même pendant un message ; la ligne « Historique » du menu Paramètres était toujours active.
- Le moteur dit lui-même quand le joueur a la main : verrou du joueur (`Global.Flag` bit 4 : événement, scène, discussion, fondu de sortie), message affiché, menu du jeu ouvert, effet d'écran / chargement, partie « combat » (même condition que la marche accélérée, `Jeu._facteur_vitesse`).

### Fait
- `Jeu.controle_joueur()` : vrai seulement en ville / donjon / tour / carte du monde, joueur non verrouillé, sans message, sans menu du jeu, sans effet d'écran ni chargement, hors combat (partie combat, cascade d'entrée, écran noir d'attente, entre deux fondus). Un fondu seul (arrivée sur une carte, retour de combat, joueur libre) n'y compte pas. `Jeu.historique_possible()` : en plus, jamais à l'écran titre.
- Touche H (`Jeu._touche_historique`) : ouvre la page si possible, sinon ne fait rien (le message « Historique indisponible : le jeu a la main » de #187 est retiré en #195).
- Menu Paramètres : la ligne « Historique » est grisée (infobulle : « Disponible seulement quand vous avez la main sur votre personnage… ») quand ce n'est pas possible, relue à chaque image.
- `Pause.maj` : page historique ouverte alors que le jeu reprend la main (il tourne derrière le menu depuis #179) : retour à la racine (ou menu fermé si la page venait de la touche H) (le message « Historique fermé : le jeu a repris la main » de #187 est retiré en #195).
- Tests : `tools/test_historique_acces.py` (19) : table de vérité de `controle_joueur`, écran titre, touche H (ouvre / message), ligne du menu active / grisée / relue, faux jeu minimal, fermeture automatique.

### À trancher / non vérifié
- **Supposé** : le menu du jeu ouvert (commandes, Divers, boutique) compte comme « le jeu a la main » : en passant par « Paramètres » du menu Divers, la ligne Historique est grisée ; la touche H reste utilisable après avoir fermé ce menu.
- **Non vérifié sous Windows** : H en ville, pendant un dialogue, une scène, un combat ; fermeture automatique quand un événement reprend la main (cas rare : le jeu ne reçoit aucune entrée derrière le menu).

## Avance #189 : bouton de vitesse de combat sur le bord gauche (#188, 04/11/2026)

### Demande (D-233, 04/11 13 h 30)
« … et pour le bouton d'accélération du combat remets-le sur le bord gauche pour le moment »

### Établi
- Depuis #47 le bouton était rattaché au coin bas gauche de la boîte du bas (commandes ou message) à la taille de la plaque « Fuir » (`Jeu._ancrer_vitesse_combat`, `Boutons.ancre`) ; sa case de la grille (colonne 0,4, ligne 8 sur 18 : le bord gauche de l'écran) ne servait plus qu'une fois déplacé par le joueur.

### Fait
- `hud_mobile.ANCRAGE_VITESSE_DEF = False` et `hud_mobile.ancrage_vitesse()` : par défaut `Boutons.ancre()` est vide et `Boutons._ancre_prete()` toujours vrai : le bouton est à sa case de la grille, sur le bord gauche, à la taille de sa plaque d'origine (118 x 60), dès la première image du combat. Une position choisie par le joueur (`bouton_vitesse_pos`) est gardée. `DQ_VITESSE_ANCRE=1` redonne le rattachement de #47 (le calcul de l'ancre de la fenêtre est conservé).
- Interface « Combat : bouton de vitesse » : la ligne « Replacer sous la boîte de combat » devient « Replacer sur le bord gauche » (même effet : position d'origine) tant que le rattachement est coupé.
- Mesure sur le vrai moteur (combat forcé sur la carte du monde, 1280 x 720, position à CHAQUE image dessinée) : x = 16 px et y = 346 px à toutes les images, aucun décalage au début d'un tour ni à la première image.
- Tests : `tools/test_bouton_vitesse.py` (25 dont 8 avec le moteur) : variable d'environnement, bord gauche même avec une ancre connue, visible dès la première image, position du joueur gardée, rattachement redemandé, rien hors combat, vrai combat (`CombatReelBordGauche`, rattachement `CombatReel` avec `DQ_VITESSE_ANCRE=1`).
