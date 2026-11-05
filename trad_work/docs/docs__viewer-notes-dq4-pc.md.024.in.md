### Établi / supposé / non vérifié
- Établi : 0 pixel de différence avec le canevas du vrai moteur pour tout ce qui précède ; rendu de l'historique vérifié sur une capture (n → `и`, r → `я`, mêmes lignes que la boîte de dialogue).
- Supposé : DQ5 et DQ6 utilisent le même format de fichier de police (le code ne connaît aucun caractère : si le format change, la lecture échoue avec un message clair et le repli SE-GARRIR prend le relais).
- Non vérifié : rendu sur Windows.

## Avance #273 : notifications de sauvegarde rétablies

### Demande
Sylfried (04/11/2026, 23 h 02) : « Remets les notifications pour les sauvegardes alors... » (D-228 / #268 avaient retiré toutes les notifications du haut de l'écran).

### Fait (D-230)
- `Jeu.toast`, `Jeu.toasts` et le dessin du bandeau noir en haut de l'écran sont de retour, **pour les sauvegardes seulement** :
  - états instantanés : « État N enregistré » (touche chiffre), « État N chargé » et « État N vide » (Ctrl + chiffre), « Chargement annulé », « Aucun chargement à annuler » (Ctrl + Maj), « <Enregistrement|Chargement> de l'état N impossible : … » (en plus de la console et du journal, ajoutés par #268) ;
  - « Sauvegarde impossible : le jeu continue (détails dans erreurs_fenetre.log) » (6 s) quand le moteur n'a pas pu écrire une sauvegarde ;
  - « Sauvegardes importées » (retour de l'écran Sauvegardes après un import).
- **Restent retirés** (D-228 maintenu) : vitesse de combat hors combat, plein écran / fenêtre impossible, mémoire du moteur à 78 % et 94 %, réglages du moteur non appliqués, interruption du son (le crochet `alerte` de `sound.py` n'est pas branché), ouverture de la page de confidentialité impossible : console et `erreurs_fenetre.log` seulement.
- `tests/test_sans_notifications.py` devient `tests/test_save_notifications.py` : liste blanche (lecture du code par `ast` : chaque `toast(...)` est un message de sauvegarde, et chacun est utilisé), et comportement (le message expire, annuler le chargement, échec d'état dans la console, le journal et à l'écran, import, la vitesse de combat ne montre rien). `test_ecriture_sauvegarde` reprend son contrôle du message. Capture headless : « État 3 enregistré » en haut de l'écran.

### Non vérifié
- À regarder sur Windows : chiffre (enregistrer), Ctrl + chiffre (charger), Ctrl + Maj (annuler), import de sauvegardes ; la touche de vitesse de combat hors combat n'affiche rien.
- Choix de Claude : les avertissements de mémoire du moteur (qui préviennent d'un arrêt possible du jeu) sont restés retirés, car ils ne concernent pas une sauvegarde ; à rétablir sur demande.

## Avance #274 : Oui / Non empilés en haut à droite de la boîte de dialogue

### Demande
Sylfried (04/11/2026, 23 h 02, capture d'écran) : « Les options OUI/NON apparaissent par-dessus le nom du locuteur, je propose une variante qui copie le fonctionnement sur DS : tu les mets l'un sur l'autre posé sur le coin en haut à droite de la boîte de dialogue avec les bords droits alignés. »

### Fait (D-231)
- **Empilement** : `Fenetre._empiler_oui_non` (type 1, `Make_YesNo`, à la création) met la plaque « Non » sous « Oui » : même colonne (celle de gauche, x de -134,5 à -0,5), une unité entre les deux (l'espace qui séparait les plaques côte à côte). Le panneau droit du cadre, la plaque de droite et son texte sont déplacés d'un bloc ; les zones de clic et la sélection suivent les nœuds déplacés. Étendue de la fenêtre : de -10 à 87 (avant : de 39 à 87). Autre mise en page (pas deux plaques sœurs) : rien n'est touché. Le curseur du moteur rangeait déjà Oui / Non en une colonne (haut = Oui, bas = Non) : le clavier et la manette n'ont pas changé.
- **Pose** : la pile est posée sur le coin haut droit de la boîte de dialogue, **bord droit visible aligné** sur celui de la boîte, et **1 unité visible** au-dessus de son bord haut (avant : 4 unités entre les mailles, 8,5 visibles ; `OUINON_ECART` = 1). Elle suit toujours la boîte, à sa place d'origine ou descendue (avant : seulement quand la boîte était descendue).
- **Bords visibles, pas bords des mailles** : les cadres ont des marges transparentes différentes (6 unités à droite et 4,5 en haut pour la boîte, presque rien pour Oui / Non) ; `bords_visibles` les mesure dans la feuille du jeu (opacité > 127, `ALPHA_FEUILLES` posé par `Rendu` avant la dilatation), `Fenetre.etendue_visible` et `FenetreMessage.etendue_visible` donnent le dessin visible, `MenusMixin._ouinon_sur_message` en tire le décalage vertical et les deux bords droits. Mesuré sur une capture headless 1280 x 720 : bords droits de la boîte, de « Oui » et de « Non » tous à x = 862.
- **Éditeur d'interface** : les réglages de « Oui / Non » (taille, décalage) restent relatifs à la boîte de dialogue ; la taille se change autour du bord bas et du bord droit de la pile, de sorte que le coin ne bouge pas. L'aperçu montre la nouvelle disposition (cadre jaune = la pile). Sans boîte de dialogue, la pile garde sa place d'origine avec les réglages du joueur.
- `tests/test_stacked_yes_no.py` (19 tests, dont 2 exécutés sans pyglet en CI, les autres passés s'il manque) : empilement sur une mise en page synthétique et sur la vraie (cache d'interface), étendues, zones de clic, autre mise en page intacte, `bords_visibles` (seuil, plusieurs cases, rien de visible), pose (bas et droite à toutes les échelles, réglage de position relatif, mesure manquante), branchement dans le code. Six mutations vérifiées (écart, déplacement vertical, déplacement du texte, signe de l'alignement, écart de pose, appel à la création).

### Non vérifié
- À regarder sur Windows : retour au titre, achat, suppression d'un état, tout dialogue à Oui / Non ; la pile est en haut à droite, ne cache pas le nom du locuteur ; flèches haut / bas, clic et manette choisissent Oui ou Non au bon endroit.
- Suppose (non vu en jeu) : les dialogues Oui / Non du combat se posent de la même façon (même chemin de code, boîte de combat descendue) ; les réglages déjà enregistrés pour « Oui / Non » dans l'éditeur s'appliquent maintenant au coin de la pile (valeurs relatives inchangées).

## Avance #276 : Un seul dossier de sauvegardes (data1 à data5, data9, etats)

### Demande
Sylfried (04/11/2026, 23 h 55) : « Tu ne pourrais juste pas stocker tous les fichiers directement dans le dossier "sauvegardes" ou un seul sous-dossier pour coller à la logique des états ? Comme ça si je veux transférer toutes les sauvegardes du mobile sur le patch je n'ai pas besoin de faire de gymnastique mentale à deviner quel fichier mettre dans quel dossier. »

### Fait (D-232)
- **Un seul dossier** : `donnees\sauvegardes\` contient `data1.dat` à `data5.dat`, `data9.dat`, `etats\` et les copies `avant_import_<date>\` : le contenu du .zip d'export. Le jeu y lit **et** y écrit ; `Dossiers.portage` est devenu un autre nom de `sauvegardes` (les états y étaient déjà : `sauvegardes\etats`). Transférer les sauvegardes du téléphone = copier ses `dataN.dat` dans ce dossier.
- **Reprise au démarrage** (`chemins._ranger_anciens_dossiers`, appelée par `migrer`, donc par le lanceur et par le jeu) : les journaux de l'ancien `sauvegardes\portage` (ce que le jeu écrivait, prioritaire) puis ceux de la copie du téléphone la plus récente (`sauvegardes\mobile\<date>`) sont **copiés** dans `sauvegardes\` sans rien écraser (c'est l'ordre dans lequel le jeu les lisait, fichier par fichier : la partie en cours ne change pas) ; puis `portage\` et `mobile\` sont **déplacés tels quels** dans `sauvegardes\avant_rangement_<date>\` (avec le `manifest.json` et les copies plus anciennes). Rien n'est supprimé. Une erreur (fichier ouvert...) laisse les anciens dossiers en place et le jeu lit déjà `sauvegardes\` ; la reprise suivante termine. Une seconde reprise ne fait rien.
- **Ordre de priorité** : la reprise du 04/11 passe **avant** celle de l'ancienne disposition (`dq4_pc\sauvegardes`, `jeux\DQ4\saves`), qui ne remplit plus que ce qui manque : le vieux `dq4_pc\sauvegardes` encore présent sur le PC de Sylfried ne doit pas passer devant ses fichiers du jour.
- `DQ4_JEUX` (copie du téléphone ailleurs, lue seulement) : sans effet, comme `--saves-lecture` pour les tests. `NOMS` (saves.py) vient de `chemins.NOMS_JOURNAUX`. Aides de `--saves-lecture` / `--saves-ecriture`, message « APK introuvables », `launch_dq4.bat` (fins de ligne CRLF conservées), README, workflow, reprise et plan du code à jour.
- `tests/test_saves_in_one_folder.py` (16 tests, sans pyglet : la CI les exécute) : disposition, reprise du cas réel (portage plus ancien que le téléphone, manifeste, vieux `dq4_pc`), rien d'écrasé ni perdu, seconde reprise vide, erreur de déplacement ou de copie, `DQ4_JEUX`, lecture par le moteur, export à plat = contenu du dossier. `test_paths.py` adapté.

### Non vérifié
- À regarder sur Windows au premier lancement : le Continuer propose les mêmes journaux qu'avant ; `sauvegardes\` contient `dataN.dat` et `etats\` ; `avant_rangement_<date>\` contient `portage\` et `mobile\`.
- Chez Sylfried, `data2.dat` à `data4.dat` du portage (1 à 3 novembre) sont **plus anciens** que ceux du téléphone (3 novembre, 21 h 24) : le jeu lisait déjà les plus anciens, la reprise garde cet ordre (aucun choix à la date). Pour avoir ceux du téléphone, les copier dans `sauvegardes\` (jeu fermé) : ils remplacent les fichiers actuels, que la copie d'import ne sauvegarde pas (copie manuelle = pas de `avant_import`).
- Le jeu écrit maintenant dans les fichiers copiés du téléphone : l'original reste sur le téléphone.

## Avance #278 : Caméra : rotation gauche / droite et recentrage rétablis (rien d'autre)

> **Remplacé par l'avance #286 (D-234)** pour tout ce qui touche à la façon de tourner : la rotation n'est plus ajoutée par la visionneuse (`lacet`, `cam_w`, `_camera_menee`, `_coupure_camera`, marche et sprites tournés par pas de 45°, `CAM_SCENE_TAU`, effacement en ≈ 0,4 s) mais faite par le jeu lui-même. Restent valables : les touches, les gestes, les réglages, ce qui reste retiré (zoom, inclinaison, centrage) et la liste des cas non vérifiés sur Windows.

### Demande
Sylfried (05/11/2026, 00 h 00), après D-226 (#264) : « Quand je parlais de retourner sur le fonctionnement de la caméra de la version mobile il faut donc garder le fait de pouvoir la tourner à gauche et à droite et la recentrer... Donc remets ces possibilités là uniquement avec toutes les options à l'identique dans les commandes avec par défaut : Gauche > Flèche gauche, Droite > Flèche droite, Gauche + Droite > Recentre la caméra, Maintiens clic molette + direction > contrôler la caméra (gauche/droite uniquement), Clic molette > recentrer la caméra, Vitesse de caméra : x1, plus la possibilité d'accélérer la caméra comme avant. »

### Fait (D-233)
- **Rotation rétablie, rien d'autre.** `Jeu._camera_ville` reste la caméra du jeu (position, cible, champ, décalage : aucun zoom, aucune inclinaison, aucun centrage, aucun lissage) ; le seul ajout est la rotation du joueur (`lacet`, degrés, non enregistrée) **autour de la cible du jeu** : distance, tangage et place de la cible à l'écran ne changent pas, le cap change du lacet (positif = vers +X = flèche droite). Le repère des sprites, les panneaux de décor, l'orientation des personnages (`phi`) et les directions de marche (pas de 45°, `_tourner_dir`) suivent la rotation.
- **Touches** : `cam_gauche` / `cam_droite` (flèches ← → par défaut, réattribuables, page Commandes > « Caméra au clavier ») tournent la caméra à `CAM_LACET_VIT` = 100 ° / s × « Vitesse de caméra » ; **les deux ensemble** la recentrent par une animation (240 ° / s au moins, plus court chemin ; une flèche restée enfoncée après la double pression ne fait rien, une nouvelle pression seule annule le recentrage). ↑ ↓ ne font rien sur le terrain (menus seulement). **L'accélérateur n'accélère plus la caméra** (aide de la touche et du multiplicateur : marche seulement).
- **Souris** : clic molette maintenu + déplacement = tourner (`GesteMolette` + `pivoter`, gauche / droite seulement, le vertical ne tourne rien, 180 ° pour une hauteur de fenêtre, pas de saut au début) ; clic molette (sans déplacement) = recentrer ; `Inverser gauche / droite` (Commandes > « Caméra à la souris », Non par défaut ; ne touche pas les flèches ni le recentrage). Deux lignes d'information (lecture seule) rappellent les gestes. La molette ne fait toujours rien sur le terrain.
- **Réglages** : `vitesse_camera` (x1 par défaut, x1 à x4, page Commandes > Vitesses, sous « Vitesse de marche ») et `camera_inverser_gd` reviennent ; `distance_camera`, `angle_camera` et `camera_inverser_hb` restent dans `CLES_OBSOLETES`. Un ancien `reglages.json` qui les contenait garde sa vitesse et son sens de glisser.
- **Le jeu l'emporte dans ses scènes** (comme avant D-226, UNI-08) : TownCamera verrouillée et menée ailleurs que sur le joueur (`_camera_menee`), caméra libre d'une scène, verrou, lieu qui interdit la rotation (limite négative) ou la borne (`cam_limite`) : un poids `cam_w` (0 = rotation du joueur, 1 = caméra du jeu) rejoint sa cible en exp(−`CAM_SCENE_TAU` t), `CAM_SCENE_TAU` = 6 / s, ≈ 0,4 s pour 90 %, sans à-coup ; une coupure du jeu (changement de carte, plan de scène : `_coupure_camera`) est immédiate. Pendant ce temps les flèches et le clic molette ne tournent rien (`_camera_pilotable`). C'est ce qui évite le problème de la cinématique des compagnons qui avait motivé D-226 : la scène ne subit plus la rotation du joueur.
- Ni sur la carte du monde, ni sur l'écran-titre, ni dans les mini-jeux. F1 affiche « Caméra : rotation N ° ».
- Tests : `test_entries.py` (+ 25 tests : geste, rotation, branchement dans un faux `Jeu`, flèches, recentrage, scènes, déplacement), `test_town_camera.py` (rotation autour de la cible, effacement en douceur, câblage de la boucle et du dessin, réglages, ancien fichier), `test_pause_pages`, `test_perte_focus`, `test_reglages_son_texte`, `test_reglages_interface`, `test_ecrans` rétablis pour la vitesse et le sens de la caméra.

### Établi
- 23 mutations du code (sens du déplacement, sens de la rotation, accélérateur, scène, verrou, coupure, recentrage, glisser, inversion, titre, câblage…) : toutes tuées par les tests ; une avait survécu (le relâchement du bouton du milieu après un changement d'état du terrain) et a reçu son test.
- Rendus sans fenêtre (église de la sauvegarde 1) : la flèche droite tenue 50 images fait tourner la salle d'environ 85 ° autour de sa cible, les personnages et les panneaux de décor suivent ; les deux flèches ensemble ramènent la vue du jeu en douceur (aucun saut d'une image à l'autre) ; `DQ_LACET=90` donne la vue de côté attendue.

### Non vérifié
- Windows : clavier et clic molette réels, sensation de la vitesse x1 (100 ° / s, supposé proche du mobile : non mesuré).
- Le glisser du clic molette et la marche sous caméra tournée : testés sur un faux jeu, pas vus à l'image (dans le seul lieu de la sauvegarde de test, un message restait ouvert).
- La scène des compagnons au début du chapitre 2 avec une rotation faite avant la scène : l'effacement est supposé suffisant.
- Aux bords de la carte, la cible du jeu est bornée : la rotation se fait autour d'elle, le héros peut s'écarter du centre pendant le mouvement (comme sur mobile, non vérifié).
- Barre de rotation de la caméra du mobile (G-103) : toujours non reproduite. La rotation n'est pas enregistrée (elle repart de 0 au lancement).
- DQ5 / DQ6 : même réglage à prévoir (non regardé).

## Avance #280 : la reprise de l'ancienne disposition ne se fait qu'une fois (le dossier `avant_import_…` ne revient plus)

### Demande
Sylfried (05/11/2026, 01 h 07) : « Pourquoi dans le dossier des sauvegardes le dossier "avant_import_20261101_192625" revient en rechargeant le jeu ? Il faut qu'il disparaisse et que les fichiers directement dans le dossier `donnees\sauvegardes` soient pris en compte (d'ailleurs j'ai rajouté le fichier "manifest.json" qui est utilisé par la version mobile, en as-tu l'utilité de l'intégrer ?) »

### Cause (établie, sur le PC de Sylfried)
- `dq4_pc\sauvegardes\` existe encore (D-232 : « rien n'est supprimé ») et contient `avant_import_20261101_192625\`. `chemins.migrer` (lancée par `launch_dq4.bat` puis par le jeu) **recopiait à chaque démarrage** tout ce qui manquait dans `donnees\sauvegardes` : le dossier effacé à la main revenait. Même défaut pour un journal `dataN.dat`, `etats\`, les réglages ou le journal d'erreurs effacés. Les fichiers directs de `donnees\sauvegardes` étaient bien lus par le jeu (D-232 : lecture et écriture dans ce seul dossier) ; la reprise ne les écrasait pas.

### Fait (D-235)
- **Chaque reprise ne se fait qu'une fois** : `donnees\reprise.json` (`{"etapes": {nom: date}}`) note les étapes faites (`cache`, `apk`, `sauvegardes_portage`, `sauvegardes_telephone`, `reglages`, `journal`) ; le rangement des anciens `portage\` et `mobile\` (D-232) déplace ses dossiers, il ne se répète donc pas de lui-même.
- **Une destination déjà en service compte comme faite** (`_deja_en_service`) : journaux ou `etats\` dans `donnees\sauvegardes`, un `.json` dans `reglages\`, un `.apk` dans `apk\`, le cache, le journal d'erreurs. C'est le cas de Sylfried : au premier lancement le fichier est écrit avec « en place » pour chaque étape et plus rien n'est recopié. Fichier illisible : comme une première fois (copie sans rien écraser, puis fichier refait). Une étape sans ancien dossier n'écrit rien (installation neuve : pas de `reprise.json`).
- Rien n'est supprimé ni écrasé : `dq4_pc\sauvegardes\` et `dq4_pc\reglages.json` restent en place, à effacer à la main quand tu as vérifié.
- `tests/test_paths.py` (20 tests, dans la CI) : tout effacé dans `donnees\` ne revient pas, disposition déjà en service (le cas réel) sans rien recopier, fichier de reprise illisible, installation vide sans fichier ; 3 mutations du code toutes tuées (une avait d'abord survécu : le test efface maintenant aussi `reglages\` et `sauvegardes\`).
