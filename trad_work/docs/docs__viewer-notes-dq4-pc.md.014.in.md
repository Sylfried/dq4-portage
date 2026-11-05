### Non vérifié (#103)
Rien n'a été exécuté côté outil. La lecture « l'accélérateur de la phrase du 15 h 50 était la vitesse de transition » est une **supposition**. Les bruitages 305, 309, 312, 330 et 306 restent lus dans le code, jamais rejoués.

## Avance #104 : audio validé (03/11/2026 à 17 h 07, docs seulement)

### Fait
- **Validé par Sylfried sur Windows** (D-203) : « l'audio fonctionne ». Les mentions « audio réel (Windows, haut-parleurs) non vérifié » des sections plus haut sont donc **périmées** pour le rendu général ; restent supposées les catégories de son 302 / 303 (G-121).
- **`reglages.json`** : « pas de souci pour le fichier, je peux toujours voir quand une valeur par défaut a été changée par le bouton de la flèche » : pas de test de conversion de plus ; la conversion de #101 (retrait de `vitesse_fondu`) reste à coder avec ses tests habituels.
- #99 : point « son et `reglages.json` » coché ; il reste la position de la fenêtre « Interface », `g_pad_pos`, `--ui-simple` et le « sort en trop » à vérifier.
- Aucun fichier de `dq4_pc/` ni de `tools/` modifié.

### Non vérifié (#104)
Rien n'a été exécuté côté outil. « L'audio fonctionne » est le constat de Sylfried, sans détail (volumes, boucles, jingles).

## Avance #106 : test issue par issue (#52 d'abord) et issue #105 (03/11/2026, docs seulement)

### Fait
- **Issue #105 créée** (jalon 5, `type:feature`, `à décider`, `priorité:basse`) : décider des modificateurs et des triches que Sylfried voudrait ajouter, **à traiter en tout dernier** (D-205). Sa liste reste à fournir ; faisabilité à étudier cas par cas (moteur `libdq4core.so` non modifié sous Unicorn : **supposé, non vérifié**).
- **Séance de test du soir** (D-204) : Sylfried renonce à la liste globale et teste **une issue à la fois**, à partir de #52 (anticrénelage, suréchantillonnage, deux moniteurs, fenêtre plus grande que l'écran). Fiche de test donnée dans la conversation (menu Échap, page « Affichage » ; critères de l'issue inchangés).
- Bilan : 50 issues (#51 à #99, #101 et #105), 42 ouvertes, 8 fermées (#51, #54, #55, #57, #78, #82, #86, #96).
- Aucun fichier de `dq4_pc/` ni de `tools/` modifié.

### Non vérifié
Rien n'a été exécuté côté outil. Les réglages de la fiche #52 sont lus dans `pause.py` (établi), jamais vus sous Windows par Claude.

## Avance #113 : retours du test de #52, libellé « Antialiasing », course après une porte (03/11/2026)

### Retours (Sylfried, 19 h 38 et 19 h 41)
Voir D-206 à D-213 (`docs/audit/decisions.md` § 5e) : antialiasing et deux moniteurs validés, suréchantillonnage x2 qui saccade, résolution 4K absente de la liste (voulu), six nouvelles issues (#107 à #112), phase « gestion de projet » levée pour les corrections du soir.

### Fait
- **Libellé « Antialiasing »** (D-206) : page Affichage du menu Échap (`pause.py`) et affichage de test (`window.py`) ; test `test_window_mode.py` mis à jour. La clé `msaa` de `reglages.json` ne change pas.
- **Course après une porte (#107, D-208)** : **mesure sur le vrai moteur** (sauvegarde 1, porte de l'église, direction tenue) : fondu de sortie = drapeaux `0x3d` (fondu + joueur verrouillé), chargement `0x3c`, fondu d'arrivée = `0x39` pendant 30 images alors que le héros marche dès la 12e image, puis `0x38`. `Jeu._facteur_vitesse` coupait la marche accélérée pendant tout le drapeau « fondu » (1 s) : **elle ne le fait plus**, seul le verrou du joueur (bit 4) la coupe. Le fondu d'arrivée suit donc l'accélération quand la touche est tenue (supposé acceptable ; il durait 1 s). Les fondus de combat (`Etat.transition_combat`) restent à l'horloge du jeu. Ce passage remplace, pour le fondu, la règle « facteur 1 si `Global.Flag & (1 | 4)` » de la section « Marche x1-x4 + accélérateur » plus haut. Tests : `test_game_priority.py` (nouveau cas, 0x39 → accéléré ; 0x3d et 0x2d restent à 1), `test_casino_bestiary.py`, `test_battle_transition.py`, `test_battle_speed.py` : OK.
- **Résolutions** : pas de changement (la liste ne propose que les tailles qui tiennent sur l'écran, `Jeu.resolutions`) ; le test « résolution enregistrée 3840 x 2160 » (#52) passe par `reglages.json`.

### Non vérifié
- La course après une porte **sous Windows** (Sylfried confirme) ; le bruitage et la durée des transitions n'ont pas été rejoués au clavier.
- #108 à #112 : en cours (voir les PR suivantes).

## Avance #114 : choix du périphérique de sortie audio (#112, 03/11/2026)

### Demande (D-207, 19 h 38)
« pouvoir changer de périphérique pour le son peut être vraiment top aussi, à rajouter tout en haut de la fenêtre pour régler les volumes ».

### Fait
- **Établi (lu dans le code de pyglet 2.1.19, non exécutable ici : Linux)** : sous Windows 8 et plus, pyglet prend d'abord le pilote XAudio2 ; `pyglet.media.devices.get_audio_device_manager().get_output_devices()` liste les sorties actives (`id`, `name`) et `get_audio_driver().set_device(device)` recrée le moteur audio sur cette sortie puis chaque lecteur en cours reprend (`Player.on_driver_reset`). Sans `set_device` (autre pilote, audio coupé), la ligne est grisée.
- **`dq4_pc/sortie_audio.py`** (logique pure, testable avec de faux pilotes) : liste des sorties gardée 1,5 s, valeurs du menu (Automatique, sorties détectées, puis la sortie enregistrée si elle n'est plus branchée, libellé « … (non branchée) »), changement, retour à Automatique (`set_device` avec `id = None` : la sortie par défaut, que le pilote suit tout seul), remise de la sortie enregistrée au lancement. Tout est dans des `try / except` : une erreur laisse le son comme il était et s'affiche dans la console.
- **Réglage** `sortie_audio` de `reglages.json` : `null` = Automatique (défaut), sinon `{id, nom}` ; une valeur illisible redevient Automatique.
- **Menu Échap > Son** : « Périphérique de sortie » tout en haut de la page (liste déroulante, bouton rond « par défaut » = Automatique) ; au changement, un bruitage d'essai est joué sur la nouvelle sortie. La page s'ouvre sur cette ligne (le test de clavier de la page Son a été recalé).
- Tests : `tools/test_sortie_audio.py` (11 tests : réglage, liste, cache, sortie non branchée, changement, erreurs, lancement), `test_pause_pages.py` (ligne en tête, grisée sans pilote capable). Démarrage de la visionneuse sous xvfb (audio « silent ») : sans erreur.

### Non vérifié (à faire par Sylfried sur Windows)
- Le changement de sortie **réel** (casque, haut-parleurs, TV) : jamais essayé ; la musique en cours doit reprendre sur la nouvelle sortie, les bruitages suivants aussi ; la sortie enregistrée doit revenir au lancement suivant.
- Le retour à « Automatique » après avoir choisi une sortie (supposé : `set_device` avec `id = None`).
- Débrancher la sortie choisie pendant le jeu : non géré (le pilote de pyglet réagit comme il le fait d'habitude) ; seul le lancement suivant retombe sur la sortie par défaut.

## Avance #115 : écran titre, logo et sous-titre deux fois plus grands (#108, 03/11/2026)

### Demande (D-209, 19 h 38)
« Peux-tu doubler la taille du logo et du sous-titre de l'écran titre ? » : **écart voulu avec l'APK** (règle habituelle : rendu le plus similaire possible).

### Fait
- **Établi** : le logo est dessiné par le moteur (maillages billboard de la carte `ev01`, paquets 21 / 22) : modèle **8901** = « DRAGON QUEST », « IV », TM et sous-titre (« L'épopée des Élus »), modèle **8900** = l'éclat animé sur le logo (agrandi avec lui).
- `pre_game.py` : `LOGO_ECHELLE = 2.0`, `facteur_logo` (réduit le facteur si le logo agrandi dépasserait 96 % de la largeur de la fenêtre, jamais sous x1) et `agrandir_logo` (x et y agrandis autour du point fixe y = 0,70 du panneau ; profondeur des couches inchangée). `Jeu._agrandir_logo_titre` / `_maillages_combat` (`window.py`) l'appliquent **seulement sur la carte du titre**.
- Variables d'essai : `DQ_LOGO_ECHELLE` (1 = le logo de l'APK) et `DQ_LOGO_Y`.
- **Mesuré sur captures** (Mesa, sans écran) à 16:9 (1280x720), 16:10 (1280x800), 4:3 (1024x768) et 21:9 (2560x1080) : largeur du lettrage = 2,00 x l'APK (± 3 %), logo dans la fenêtre et centré, bas du « IV » au moins 2 % de la hauteur au-dessus de « Touchez l'écran », même placement à tous les formats. Test : `tools/test_titre_logo.py` (12 tests, dont le rendu réel, ~2 min via `engine_slot.sh` avec `DQ_APK`, `DQ_SAVES`, `DQ_UICACHE`).

### Supposé / non vérifié
- Supposé : « boutons » = « Touchez l'écran » (le menu de départ cache le logo) ; le dragon n'est pas recouvert dans la pose échantillonnée, l'île du château frôle le « V » sans le recouvrir.
- Non vérifié : le rendu sous Windows, les autres poses du dragon sur toute l'animation. **À confirmer par Sylfried.**

## Avance #116 : « Revenir à l'écran titre » comme dans le jeu d'origine (#109, 03/11/2026)

### Demande (D-210, 19 h 38)
« Pour le bouton pour revenir à l'écran titre actuel, reprend exactement le même fonctionnement que sa version de base, ça ouvrait un dialogue avec le texte associé et ça demandait si oui ou non on le voulait vraiment et ensuite il y avait un effet de transition, là c'est trop brut. »

### Fait
- Avant : la ligne ouvrait une page « En êtes-vous sûr ? » dessinée par la visionneuse, puis le retour au titre était brut. Maintenant la ligne **ferme le menu et fait ouvrir au moteur la boîte du jeu** (texte d'origine `0xCBA2F`, choix Oui / Non, curseur d'origine sur « Oui »), puis :
  - **Oui** : `killbank(4, false)`, déverrouillage, `Global::startTitle` avec le **fondu de 30 images** du jeu ;
  - **Non** : la boîte se ferme et le joueur est déverrouillé.
- **Établi** (lu dans le moteur, appels faits par le code d'origine du bouton des Paramètres) : `TownMenu_MESSAGE::openMessageForMENU`, `addMessage(0xCBA2F)`, `setYesNo`, `setYesNoSuperCancel(false)` ; le résultat est lu à `gTownMenu_MESSAGE + 0x10` (1 = Oui, 2 = Non, remis à 0 à l'ouverture) ; fermeture par `MenuBase::isOpen` / `close` ; verrouillage par `PlayerManager::setLock`. La boîte est une grille de 1 x 2.
- `engine.py` : `demander_retour_titre`, `_retour_titre_avant` / `_retour_titre_apres` (autour de `GameUpdate` dans `step`), `retour_titre` (fermeture de la boîte dans le même pas). Page `titre` de `pause.py` supprimée ; ligne grisée quand la boîte n'est pas disponible (`Jeu.retour_titre_possible`).
- Test : `tools/test_retour_titre.py` (21 tests, dont le moteur réel via `engine_slot.sh`). Correctifs de deux tests cassés par les PR précédentes : `test_inactive_lines.py` (faux jeu sans la ligne de sortie audio de la PR #114) et son contrôle « aucun mot `triche` » (le README parlait encore d'« option de triche » depuis le renommage en « Modifications », #47 : reformulé).

### Écart avec le comportement précédent (à décider par Sylfried)
- **Établi** : la boîte d'origine est prévue **en ville et sur la carte du monde** ; en **combat, casino et bestiaire** elle ne reçoit aucune touche. La ligne est donc **grisée** dans ces cas (avant : le retour brut marchait en combat). Autre possibilité : une boîte dessinée par la visionneuse avec le même texte et le même fondu, mais ce ne serait plus « le même fonctionnement que l'APK ».

### Non vérifié
- Le rendu de la boîte et du fondu sous Windows ; le texte exact affiché (lu dans le moteur, pas vu à l'écran sur Windows). **À confirmer par Sylfried.**

## Avance #117 : la caméra suit la butte du village du prologue (#110, 03/11/2026)

### Demande (D-211, 19 h 38)
« Dans le prologue, il y a une petite butte au milieu du village, et en marchant dessus la caméra doit pouvoir un peu se surélever, là elle reste sur le même plan donc il y a encore des ajustements à faire sur la caméra. »

### Cause (établi)
- Le moteur d'origine suit la hauteur du héros à chaque pas (`TownCamera::execute` : `setTarget(joueur)` puis `calcPursue`, décalage rigide ; `SceneCamera.Update` ne lisse rien en Y). Le lissage de hauteur ajouté en #47 (pour les escaliers) retardait aussi la caméra sur les **petits** reliefs : sur la butte de `mlout1` (+0,5 u en ~8 pas), le héros montait puis redescendait à l'écran de **18 à 29 px** (à 720 p) au lieu de rester au centre.

### Fait
- `window.py` : fonction `hauteur_camera` et constante `CAM_Y_RELIEF = 0,6` : **bande morte** autour de la hauteur de repos. Tant que le jeu reste à moins de 0,6 u de cette hauteur (butte, rampe douce, bosse), la caméra le suit **exactement**, comme sur mobile. Au-delà (escaliers, étages) le lissage de #47 (`CAM_Y_TAU`, `CAM_Y_MAX`) joue comme avant. La hauteur de repos est une contraction de la cible : continue, jamais plus brusque qu'avant, à la montée comme à la descente. Coupure du jeu ou caméra prise par le jeu : inchangé (hauteur du jeu aussitôt).
- **Mesuré** (rejeu de la trace du moteur réel dans `Jeu._camera_ville`) : butte de `mlout1` : héros à **0 px** de l'écart au centre (comme le mobile) contre 18 à 29 px avant. Escalier de `chf2` : retard maximal **0,95 u** (1,21 u avant, soit environ 22 % de moins), `teout5` inchangé (borne 3 u).
- Test : `tools/test_camera_ville.py` (14 tests : butte suivie exactement à toute cadence, escalier toujours lissé au-delà, invariants de la fonction, coupure).

### Écart à connaître
- Les escaliers de #47 sont un peu **moins** retardés qu'avant (la bande morte de 0,6 u est suivie exactement) ; le ressenti de l'escalier est à confirmer.

### Non vérifié
- Le ressenti sous Windows (butte du prologue, un escalier de ville, une tour). **À confirmer par Sylfried.**

## Avance #118 : fond des villes en dégradé (#111, 03/11/2026)

### Demande (D-212, 19 h 38)
« La couleur du fond de la map dans le prologue n'est également pas la bonne, il doit y avoir un dégradé comme sur le mobile, là c'est juste une couleur unie. »

### Cause (établi)
- Côté jeu, `NativeManager.cmd_back_color` (RVA 0xD14F44) lit **six** flottants (haut r, g, b ; bas r, g, b) et appelle `BackColor.SetColor(haut, bas, 0)` (0xCC43F8). `BackColor` est un quadrilatère plein écran (shader « BackColor » : `gl_Position = in_POSITION0`, couleur de sommet, file Background, ZTest Always, ZWrite Off) dont les deux sommets du haut portent la couleur du haut et ceux du bas la couleur du bas : un **dégradé vertical linéaire** sur toute l'image. La visionneuse n'en gardait que la **moyenne** (`Etat.fond`) : fond uni.
- Les deux couleurs viennent de `param_map_backcolor` (`TownDataManager::setBackcolor`) et **dépendent de l'heure du monde** : village du prologue (`mlout1`) = **aplat le jour et à l'aube**, dégradé rose-gris vers orange **le soir**, bleu nuit vers bleu plus sombre **la nuit**.

### Fait
- `engine.py` : `Etat.fond_haut` / `fond_bas` (remis à None à chaque chargement de carte) ; `fond` (la moyenne) reste la couleur d'effacement. `window.py` : `Jeu._tracer_degrade_fond` dessine le quadrilatère après l'effacement et avant la scène, **seulement pour une ville dont les deux couleurs diffèrent**. Aplat (jour, intérieurs noirs, combats, carte du monde) : inchangé au pixel près (`mlout1` de jour : 0 pixel différent). Teinte jour / nuit (`map_tint.py`, paquet 33) non touchée.
- Test : `tools/test_fond_degrade.py` (10 tests : décodage du paquet 8, `degrade_fond`, rendu GL d'un vrai dégradé linéaire, moteur réel `mlout1` à l'heure du soir et du jour).
- Vu sur capture (Mesa, heure du monde 1984, `mlout1`) : avant, bande unie brun-rose à droite de la carte ; après, dégradé rose-gris en haut vers orange en bas.

### À savoir (décision / confirmation par Sylfried)
- **De jour, le village du prologue a bien un fond uni dans les données du jeu** (les deux couleurs sont égales) : le dégradé n'apparaît que le **soir et la nuit**. Si le dégradé vu sur mobile était de jour, ce n'est pas cette source.
- Le changement touche **toutes les villes extérieures** le soir et la nuit (environ 98 cartes) et 7 cartes même de jour : à regarder sur Windows. La carte du monde et les cartes `ev*` n'ont pas été vérifiées.

### Non vérifié
- Le rendu sous Windows (le tampon d'image de la capture est en 5-6-5 bits : les anneaux concentriques vus sur la capture viennent de là, supposé).

## Avance #119 : logo de l'écran titre 1,5 fois plus grand au lieu de 2 (#108, 03/11/2026)

### Demande (D-215, 21 h 05)
« Finalement je veux le logo agrandit en 1,5x au lieu de 2x. » Il remplace sa demande de 19 h 38 (D-209, « doubler »). Écart voulu avec l'APK (le logo de l'APK = 1).

### Fait
- `pre_game.py` : `LOGO_ECHELLE = 1.5` (le reste de l'agrandissement d'#115 est inchangé : point fixe y = 0,70, réduction si le logo dépasserait 96 % de la largeur, jamais sous x1). Variable d'essai `DQ_LOGO_ECHELLE` (1 = APK) toujours valable.
- `test_title_logo.py` (12 tests) : constante 1,5 ; rapport de largeur 1,5 à ±0,05 à 16:9, 16:10, 4:3 et 21:9 ; test de réduction refait avec des largeurs de fenêtre où la réduction joue encore (0,7 à 0,9).
- **Mesuré** (rendu réel, Mesa sans écran, image 770) : les 12 tests passent, dont le rendu à 1280x720, 1280x800, 1024x768 et 2560x1080 ; capture 16:9 regardée : logo centré, « IV » au-dessus de la zone de « Touchez l'écran », dragon et île du château non recouverts.

### Non vérifié
- Le rendu sous Windows. **À confirmer par Sylfried.**

## Avance #120 : plus de choix du moniteur du plein écran ni du périphérique audio (#112, 03/11/2026)

### Demande (D-216 et D-217, 21 h 05)
Après avoir essayé #112 sous Windows (« Mon écran externe avec baffes intégrées ne coopère pas […], mais en connectant des écouteurs je n'ai pas pu changer de périphérique ») : « Supprimer les options pour choisir l'écran ou la sortie audio, il faut tout simplement que quand on active le plein écran (par les options ou via les raccourcis clavier) […] la fenêtre détecte sur quel écran il est et qu'il se mette en plein écran sur celui ci, et le son on le laisse sur le périphérique par défaut au pire ça se règle sur windows. »
