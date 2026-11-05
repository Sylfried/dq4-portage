### `manifest.json` (établi / supposé)
- **Établi** : le jeu ne lit pas `manifest.json` (aucune occurrence dans le code managé, seulement les ressources .NET, ni dans les chaînes de `libdq4core.so`). Son contenu : `date` (3 novembre 21 h 24 UTC), `package` (`com.square_enix.android_googleplay.dq4`), `device` (`SM S938B`), `files` (taille et sha256 de `data1.dat` à `data5.dat` et `data9.dat`). **Supposé** : écrit par l'outil qui a copié les sauvegardes du téléphone, pas par le jeu.
- **Pas intégré** : chaque journal a déjà son contrôle (en-tête + somme, `format_journal.verifier`) et l'import contrôle les tailles ; le manifeste n'apporte rien au jeu. L'import l'ignore (test) ; il peut rester dans le dossier.
- **Constat utile** (sha256 du dossier de Sylfried, 05/11 01 h) : `data3.dat`, `data4.dat` et `data5.dat` sont **identiques à ceux du manifeste** (copie du téléphone) ; `data1.dat`, `data2.dat` et `data9.dat` **ne le sont pas** (`data2.dat` = l'ancien du portage du 3 novembre 18 h 25 ; `data1.dat` et `data9.dat` réécrits depuis, sans doute par le jeu).

### Non vérifié
- Windows : relancer le jeu deux fois après avoir effacé `avant_import_…` : il ne revient pas, `reprise.json` apparaît dans `donnees\`.

## Avance #282 : la console du lanceur se ferme avec la fenêtre du jeu

### Demande
Sylfried (05/11/2026, 01 h 07) : « Fais en sorte que le CMD qui s'ouvre lors du lancement du jeu se ferme automatiquement en fermant la fenêtre du jeu »

### Cause (établie dans le fichier)
`launch_dq4.bat` finissait par `echo Fin du programme.` puis `pause` : la console attendait une touche après chaque fermeture du jeu.

### Fait (D-236)
- Après la ligne qui lance `python -m dq4_pc`, le lanceur lit le code de sortie (`set "CODE=%errorlevel%"`). **Code 0** (fermeture normale de la fenêtre, y compris le menu Quitter) : plus de pause, `exit /b 0`, la console se ferme. **Autre code** (le jeu a planté, Python lève une exception) : message « Le jeu s'est arrêté sur une erreur (code N) », `pause`, puis `exit /b N` ; l'erreur reste donc lisible.
- Les pauses d'avant le lancement (Python introuvable, création de l'environnement ou installation des modules échouée, lecture de la mise en page des fenêtres échouée) sont gardées : elles expliquent pourquoi le jeu ne démarre pas.
- Fins de ligne CRLF conservées (fichier réécrit en binaire).
- `tests/test_launcher.py` (3 tests sans Windows, dans la CI) : CRLF, aucune `pause` hors du bloc d'erreur après la ligne de lancement, `exit /b %CODE%` en dernière ligne, chaque pause d'avant suit un message ; 3 mutations (pause ajoutée, `exit /b` retiré, LF) toutes tuées.

### Non vérifié
- Windows : fermer la fenêtre du jeu par la croix, Alt + F4 et le menu Quitter ferme la console ; le comportement sur une erreur (garder la console ouverte) n'a pas été vu non plus. Un processus du jeu qui ne se terminerait pas (fil non démon) garderait la console ouverte : rien de tel n'est connu.

## Avance #284 : Commandes : un seul groupe « Caméra »

### Demande
Sylfried (05/11/2026, 01 h 07) : « Regroupe toutes les options de caméra directement dans un groupe nommé "Caméra" » ; « Change le texte "Tourne la caméra à gauche ou à droite" par "Tourne la caméra" »

### Fait (D-237)
- Page Commandes (`Pause._e_commandes`) : l'intertitre **« Caméra »** regroupe, dans cet ordre, « Caméra (Gauche) », « Caméra (Droite) », « Inverser gauche / droite », les lignes d'information « Clic molette maintenu + déplacement : Tourne la caméra » et « Clic molette : Recentre la caméra », puis « Vitesse de caméra » (qui était sous « Vitesses »). Les intertitres « Caméra au clavier » et « Caméra à la souris » disparaissent. « Vitesses » commence par « Vitesse de marche ».
- `GESTES_SOURIS` : « Tourne la caméra ». Les aides des lignes, les touches par défaut et `reglages.json` ne changent pas.
- `tests/test_pause_pages.py` (29 tests) : liste des intertitres, contenu exact du groupe, plus de « Vitesse de caméra » sous « Vitesses », textes des deux informations ; 3 mutations (ancien texte, ancien intertitre, vitesse remise sous « Vitesses ») toutes tuées.

### Non vérifié
- Windows : l'aspect de la page (le groupe tient-il sans défilement ? les deux lignes d'information au milieu du groupe sont affichées comme avant : geste à gauche, effet en gris à droite).

## Avance #286 : Caméra : la rotation est celle du jeu (compagnons d'Alina), angle du toit

### Demande
Sylfried (05/11/2026, 01 h 07) : « Il y a encore un bug dans la caméra lorsque les compagnons rejoignent Alina, elle va tourner un peu puis se téléporter sur ses compagnons pour ensuite suivre la scène, comme je t'ai dis reprend le comportement de la caméra comme sur la version mobile, dans les moments où on peut la contrôler comme dans les moments où le jeu la controle », puis « Profites-en aussi pour regarder si l'angle d'origine de la caméra une fois qu'on est sorti de la chambre d'Alina c'est celui actuellement proposé par le jeu ou bien si c'est un bug, pour t'aider tu peux charger l'état 1 qui est directement le moment où tu atterris sur le toit ».

### Cause (établie, mesurée avec le vrai moteur)
- D-233 (#278) faisait tourner la caméra **dans la visionneuse, à côté du jeu** : la vue montrée était le cap du moteur + un « lacet » du joueur, et un poids `cam_w` faisait glisser ce lacet vers 0 en ≈ 0,4 s dès que le jeu prenait la caméra (`cam_jeu`).
- La scène des compagnons (début du chapitre 2, cartes `ev01` puis `cbout`, journal pas à pas de la caméra du jeu) : le jeu fixe un cap **absolu** de 180 ° (≈ 2,8 ° par pas, pas 114 à 158 environ), puis mène la **cible** vers les compagnons (≈ (4 ; 6 ; 4,5), au plus 0,46 par pas, pas 164 à 178 environ), puis revient. Avec un lacet du joueur non nul, la visionneuse montrait le cap du jeu **plus** le lacet, puis le faisait glisser : la vue « tournait un peu » puis sautait avec la cible = ce que décrit Sylfried. Avec un lacet nul, la visionneuse montrait déjà exactement la caméra du moteur (vérifié).
- Ce n'est donc pas une erreur de la scène du jeu, c'est la rotation ajoutée par la visionneuse.

### Fait (D-234)
- **Plus aucune rotation à côté du jeu.** Sur le terrain libre d'une ville, d'un donjon ou d'une tour (`Jeu._camera_pilotable`), les flèches ← → (« Caméra (Gauche) » / « Caméra (Droite) »), le clic molette et son glissement envoient au moteur **les boutons de caméra du jeu** : les bits 4 et 5 (0x10, 0x20) des touches tenues, qui sont A et B ailleurs mais que `window::NormalControl::checkCamera` lit comme boutons de caméra sur le terrain d'une ville (1 = gauche, 2 = droite, 3 = les deux = retour au nord). `Moteur.CAM_G`, `CAM_D`, `CAM_PAS`, `ROT_CAM_*`.
- **Le jeu fait tout le reste** : `TownPlayerManager::setCameraRot` tourne d'un cran (0x200 sur 65536 par tour = 2,8125 °) par pas, borne selon les limites du lieu, refuse sous verrou, en scène ou dans un lieu qui l'interdit, tient le joueur pendant le retour au nord (animation du jeu, ≈ 5,6 ° par pas), tourne lui-même les directions de marche et garde la rangée des sprites (vérifié : le héros marche vers le fond de l'écran après un quart de tour, même rangée de sprite). `field.py` ne tourne plus rien, `Jeu.pad()` n'a plus de rotation. À l'entrée d'une carte le jeu remet le cap à 0.
- **« Vitesse de caméra »** (x1 à x4) : le jeu ne tourne que d'un cran par pas ; pour x2 à x4, la visionneuse fait faire au moteur les crans de plus tout de suite (`Moteur.camera_tourner`, appelé après un pas dont `Moteur.camera_attente()` — `TownPlayerManager + 0x698` — montre que le jeu a pris le bouton ; sinon rien : verrou, scène…). Vitesse non entière répartie d'un pas à l'autre. Le glissement du clic molette suit le pointeur par crans (jusqu'à `CAM_GLISSE_PAS` = 6 par pas), 180 ° pour un déplacement égal à la hauteur de la fenêtre (200 px sur 720 : +50,6 °) ; la rotation restante à faire est abandonnée si le jeu refuse.
- **Image** : `Jeu._interpoler_camera` interpole la caméra entre deux pas du moteur (30 Hz) comme un couple : la cible suit le déplacement, la position tourne **en arc autour de la cible** (cap par le plus court chemin, distance et hauteur à part). Sans cela un cran de rotation (1,7 unité à 34 de distance) dépassait le seuil de saut (`CAM_SAUT_VILLE`, 1,5) et la rotation s'affichait à 30 images par seconde. Une coupure (cible qui saute, angle posé d'un coup par un script, plus de `CAM_SAUT_ROT` = 0,35 de la distance par pas, ≈ 20 °) n'est pas interpolée.
- **Inchangé** : touches, gestes, réglages (`vitesse_camera`, `camera_inverser_gd`), pas d'accélération, ni sur la carte du monde ni sur l'écran-titre ; F1 donne le cap du moteur. `Jeu.on_deactivate` abandonne la rotation demandée à la souris et le retour au nord en attente.
- **Retirés** : `CAM_LACET_VIT`, `CAM_RECENTRE_LACET`, `CAM_MENE_DIST`, `CAM_SCENE_TAU`, `DIR_BITS`, `_maj_camera`, `_camera_menee`, `_coupure_camera`, `_lacet_eff`, `_tourner_dir`, `t_cam`, les états `lacet` et `cam_w`.
- Tests : `test_engine_camera.py` (nouveau, **vrai moteur**, sauvegarde 1 : un cran de 2,8125 ° par pas dans chaque sens, bouton gardé en attente, n crans de plus exacts, x2 / x4 en marche continue, les deux boutons = retour au nord sans à-coup avec joueur tenu puis rendu, marche relative à la caméra et même rangée du sprite ; ignoré sans `DQ_APK` / `DQ_SAVES`), `test_entries.py` (geste, boutons envoyés, vitesse, glissement par crans, refus du jeu, pression double, retour au nord, hors terrain), `test_town_camera.py` (la vue ne dépend que du moteur, interpolation en arc, coupures), `test_focus_loss.py`, `test_loading.py`, `test_keyboard_sfx.py` adaptés.

### Établi
- La scène des compagnons au pas près (journal du vrai moteur) et la cause ci-dessus ; avec la caméra tournée à 105 ° **avant** la scène, la scène démarre au même pas et le jeu tourne de 105 ° à 180 ° (cap absolu), puis mène la cible et revient : aucun saut dans les images enregistrées (montage), rendu en temps réel fluide.
- x2 / x4 : 5,6 ° / 11,25 ° par pas ; un glissement de 200 px : +50,6 ° ; un clic molette à 110,7 ° : retour à 0 en 20 pas.
- 49 mutations du code nouveau (sens, bits, garde du jeu, type en attente, vitesse, crans de plus, glissement, pression double, hors terrain, oubli après un menu, interpolation et coupures, perte du focus…) : 7 avaient survécu, chacune a reçu son test ; toutes tuées.
- **Angle du toit (état 1)** : 60,05 ° est bien la valeur du **moteur** à cet instant (cap lu dans le moteur). La visionneuse ne l'écrit jamais (elle n'écrit plus la caméra du tout) ; sans action du joueur le jeu part de 0 à l'entrée d'une carte et le retour au nord ramène à 0. Ce n'est pas un bug de la visionneuse.

### Supposé
- Cet angle est posé par un script du jeu au moment de l'atterrissage / de la sortie de la chambre (candidats dans le code : `cmd_map_camera_default_angle` à 0x21fe20, `__cmd_map_camera_move::initialize` à 0x221aa0, `__cmd_map_camera_angle::initialize` à 0x221bec, `__cmd_set_camera_angle_abs::initialize` à 0x222360) : script exact non identifié.

### Non vérifié
- Windows : clavier et clic molette réels ; sensation de la vitesse x1 (84,4 °/s ; D-233 : 100 °/s ; celle du mobile n'est pas mesurée).
- Ce que montre le mobile à cet endroit (seul l'état 1 était disponible) : si l'angle de 60 ° y est le même, c'est le jeu qui le décide, la visionneuse n'y change rien.
- Les autres scènes que celle des compagnons, DQ5 / DQ6 (non regardés).
- **À faire valider par Sylfried** (ce que la caméra du jeu impose, voir D-234) : vitesse x1 = 84,4 °/s ; recentrer = retour au **nord** (cap 0), pas à « la vue du jeu » (sur le toit : 60 ° → 0), animé par le jeu, joueur tenu pendant ce temps et non interrompable par les flèches ; la rotation vit dans l'état du moteur (elle n'est toujours pas enregistrée par la visionneuse).

## Avance #288 : version anglaise de l'outil (D-238)

### Demande
Sylfried (05/11/2026, 01 h 07) : « Je veux désormais une version anglaise de l'outil, donc proposes une traduction anglaise de tout ce qui est fait et qui est propre à l'outil, je ne parle pas du texte in-game comme les interfaces, dialogues, menu in-game ou autre, je veux qu'un anglais qui charge des roms anglaises puissent également naviguer dans les paramètres, l'historique etc en anglais. Tu vas donc rajouter une ligne d'option dans "Affichage" au-dessus de "Plein-écran" avec commes options : "Système", "Anglais", "Français" lorsque l'affichage est en français, sinon "System", "English", "French" quand l'affichage est en anglais, et bien sûr système suit le réglage de la langue du PC pour afficher automatiquement FR ou EN (si le PC est en Français, peu importe lequel, alors tu mets "Français", sinon automatiquement en Anglais) et "Système" sera le choix par défaut »

### Fait (D-238)
- **Ligne « Langue »** en tête de la page Affichage (au-dessus de « Plein écran ») : Système / Anglais / Français, ou System / English / French quand l'outil est en anglais. **Système** (défaut) = français si Windows est en français, quelle que soit la variante (identifiant primaire 0x0C : France, Belgique, Canada, Suisse…), anglais sinon. Le choix est dans `reglages.json` (clé `langue` : `systeme`, `en`, `fr`) ; il s'applique tout de suite.
- **Principe** (`dq4_pc\language.py`) : le texte **français du code est la clé**. `tr('texte')` rend le même texte en français (donc le français ne change pas, octet pour octet : rejoué sur 11 433 textes dessinés et 204 aides de la page Paramètres) et sa traduction en anglais ; `N_('texte')` marque les constantes de module, traduites au moment de dessiner ; un texte sans traduction reste en français ; les textes à trous sont traduits puis formatés (`tr('%d fichiers') % n`). Les traductions sont dans `dq4_pc\texts_en\` (621 entrées : `pause` 316, `menus` 115, `fenetre` 88, `divers` 102 ; une clé n'existe que dans un fichier).
- **Ce qui est traduit** : toutes les pages de Paramètres (aides, infobulles, noms de touches, fenêtre Oui / Non), l'Historique (onglets, favoris, aide, résultats de combat), l'écran Sauvegardes (export / import, erreurs), le titre de la fenêtre, les notifications, la console et `erreurs_fenetre.log`, l'aide `--help`, les messages de démarrage et de migration, les licences (déjà en anglais). `main.py` règle la langue **avant** la migration et avant l'analyseur de la ligne de commande ; le processus de préparation du cache la reçoit par `DQ4_LANGUE`.
- **Lanceur** `launch_dq4.bat` : chaque message existe en deux versions (étiquettes `:m_xxx_fr` / `:m_xxx_en`), choisies d'après la langue d'affichage de Windows (`PreferredUILanguages`, sinon `LocaleName`) ; le jeu, lui, suit le réglage « Langue ». Fichier toujours en ASCII et CRLF.
- **Tests** : `test_langue` (règles du catalogue : mêmes trous, pas de doublon, rien d'orphelin, tout `tr` / `N_` du code a sa traduction ; dans la CI), `test_langue_pages`, `test_langue_pause` (33), `test_langue_menus` (35), `test_langue_fenetre` (46), `test_lanceur` (7) ; plus de 40 mutations, toutes détectées. Les tests qui attendent des textes français fixent la langue sur `fr` (la CI est en anglais) ; la ligne « Langue » en tête d'Affichage a décalé les index de `test_mode_fenetre`, `test_ecrans` et `test_lignes_inactives`.

### Termes choisis (à relire)
Paramètres → Settings ; Commandes → Controls ; Historique → History ; Sauvegardes → Saves ; journal (data1.dat…) → adventure log ; état instantané → save state ; Discussion → Talk ; Croix → D-pad ; Fuite (issue d'un combat) → Escaped ; Bestiaire → Bestiary ; menu Divers → Misc menu ; « essai » (titre) → trial ; onglet Dialogues → Dialogue ; typographie anglaise : pas d'espace avant « : ». Pluriel : 0 est au singulier en français et au pluriel en anglais (« 0 save states »).

### Laissé en français (voulu)
Le texte du jeu (dialogues, menus du jeu, noms) ; les traces des options de test (`--shot`, `--touches-test`, `DQ_*`) ; le journal de l'émulateur ; les dates `jj/mm/aaaa` de la page États ; les lettres de la saisie du nom (c'est une fonction du jeu) ; les commentaires, docstrings et documents du dépôt.

### Établi / supposé / non vérifié
- **Établi** (tests, vrai dessin sans fenêtre, 40 mutations) : français inchangé ; aucun mot français ne reste dans les écrans anglais testés ; `python -m dq4_pc --help` parle les deux langues (vrai processus) ; la page Paramètres a été rendue en images anglaise et française : rien ne déborde (l'anglais dépasse le français de 23 % au plus).
- **Supposé** : les tailles réelles sous Windows (polices et DPI du poste) ; les messages du `.bat` selon la langue de Windows (le fichier est relu comme du texte, pas exécuté).
- **Non vérifié à l'image** : l'Historique et l'écran Sauvegardes en anglais, les notifications en haut de l'écran de jeu, le titre de la fenêtre (non rafraîchi quand on change de langue pendant la partie : il se traduit à la création).
- **Limites connues** : les favoris de l'historique gardent « Monstre » / « Objet n°… » dans la langue du moment où ils ont été enregistrés ; le choix de langue ne change pas le texte du jeu (une ROM anglaise a déjà son texte anglais).
- **Découvert au passage** : l'aide du réglage Son « Général » dit « le jeu, lui, reste en pause », ce qui est faux depuis #178 (texte français non corrigé ici, signalé pour l'audit).

### À valider sur Windows
Ouvrir Paramètres > Affichage : la ligne « Langue » est la première ; passer en Anglais puis en Français et parcourir les pages (Affichage, Son, Commandes, Interface, États, Modifications), l'Historique (F2 ou la touche choisie) et l'écran Sauvegardes ; lancer avec Windows en anglais pour voir les messages du `.bat` en anglais.
