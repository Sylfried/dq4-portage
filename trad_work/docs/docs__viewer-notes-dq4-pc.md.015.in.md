### Fait
- **Sortie audio** : `dq4_pc/sortie_audio.py` et `tools/test_sortie_audio.py` supprimés (retour à l'état d'avant la PR #114 pour le code : ligne « Périphérique de sortie » de la page Son, réglage `sortie_audio`, appels dans `window.py`). Le son reste sur la sortie par défaut de Windows.
- **Moniteur du plein écran** : ligne « Écran du plein écran » de la page Affichage, réglage `ecran_plein`, méthodes `valeurs_ecran`, `valeur_ecran`, `nom_ecran`, `ecran_modifiable`, `regler_ecran_plein` et paramètre `deplacer` de `regler_plein_ecran` supprimés. `screens.py` ne garde que la détection : `lister`, `ecran_de`, `principal` et `cible(liste, fenetre)` (l'écran de la fenêtre, à défaut le principal).
- **Le plein écran se fait toujours sur l'écran où se trouve la fenêtre** (interrupteur « Plein écran », F11, Alt + Entrée) : `Jeu._ecran_pour_plein` prend l'écran qui contient le **centre** de la fenêtre (`_indice_ecran_fenetre`, `get_location`) ; si c'est déjà l'écran de pyglet, un simple `set_fullscreen(True)` comme avant, sinon l'écran est passé explicitement. Au retour en fenêtre, la fenêtre retrouve sa place d'avant (inchangé). Détection : **établi** par test avec de faux moniteurs (fenêtre sur A, sur B, à cheval, déplacée entre deux passages) ; **jamais vu sur un vrai double écran Windows** avec cette détection seule (il avait testé le choix explicite).
- **Réglages** : `ecran_plein` et `sortie_audio` sont des clés obsolètes (`CLES_OBSOLETES`) : un ancien `reglages.json` qui les contient les ignore et les perd à la prochaine sauvegarde. Textes d'aide de « Plein écran » et de « Résolution » : « l'écran où se trouve la fenêtre ».
- Tests : `test_screens.py` refait (19 tests : détection, `cible`, clés obsolètes, entrée en plein écran sur l'écran de la fenêtre à chaque passage, moniteurs illisibles, échec, retour en fenêtre, page Affichage sans la ligne), `test_window_mode.py` (39), `test_inactive_lines.py` (17), `test_pause_pages.py` (28), `test_interface_settings.py` (21) adaptés. Suite sans moteur : 47 fichiers verts sur 48 (le 48e, `test_texte_defilement`, exige `--apk` et `--saves`).

### Limites connues (à connaître)
- **Établi** : si le jeu est **lancé en plein écran** (dernier mode enregistré), la fenêtre n'existe pas encore : elle se crée sur l'écran **principal** de Windows (avant, elle allait sur le moniteur choisi). Pour jouer sur l'autre écran : fenêtre d'abord (F11 la sort du plein écran), la déplacer, puis F11.
- **Supposé / non vérifié** : le pilote audio de pyglet prend la sortie par défaut de Windows au lancement ; si on la change pendant la partie, il est possible qu'il faille relancer le jeu.
- **Non vérifié** : le plein écran sur le bon écran sous Windows avec deux moniteurs. **À confirmer par Sylfried** (issue #52, test « deux moniteurs »).

## Avance #124 : sauvegarde automatique du jeu à la fermeture de l'application (#122, 03/11/2026)

> **Remplacée par l'avance #142 (plus bas) : tout ce qui suit sur une écriture à la fermeture est retiré** (le jeu d'origine n'en fait pas), et la ligne « aucune fonction du moteur n'appelle `AutoSave` » est fausse : le moteur l'appelle lui-même, à deux endroits.

### Demande (D-218 et D-219, 22 h 34)
« Les sauvegardes auto ne fonctionnent pas, normalement je dois avoir une sauvegarde in game en fermant l'application […] (et effectivement je ne dois pas en avoir en quittant via le retour à l'écran titre, je parle bien de quand je ferme l'application). Il faut que ça marche qu'on clique sur la croix ou bien qu'on fasse Alt+F4 ou qu'on ferme depuis le gestionnaire des tâches etc (et c'est bien un système de sauvegardes in-game, je ne te demande pas de créer un système de sauvegarde à part pour ça). »

### Établi (désassemblage de `libdq4core.so` et essais sur le vrai moteur)
- La sauvegarde automatique du jeu est la **banque 4** (`data5.dat`, SAVETYPE 3), la cellule « Sauvegarde automatique » du menu de départ. Le moteur l'écrit par `AutoSave(bool)` (symbole `_Z8AutoSaveb`, 0x164aa8) : avec `true`, `savebank(4, 3)` sans condition ; avec `false`, seulement si `StageStatus::isAbortSaveDungeon()` et `isAbortSaveTown()` sont vrais (sur une carte de ville ou de donjon, il faut en plus l'indicateur de `StageStatus::setAbortSave`, qui était à zéro dans l'essai : `AutoSave(false)` a renvoyé 0 en ville).
- **Aucune fonction du moteur n'appelle `AutoSave`** : c'est le Unity d'origine (code C# non disponible ici) qui le fait, vraisemblablement à la mise en veille de l'application (**supposé**). La visionneuse ne l'appelait jamais : `Jeu.on_close` n'écrivait que les réglages et l'historique.

### Fait
- `Moteur.sauvegarde_auto()` appelle `AutoSave(true)` (0 : pas de partie en cours, 1 : écrite, -1 : refusée) ; `Moteur.sauvegarde_auto_possible()` : seulement en ville, donjon ou sur la carte du monde (`PARTIE_VILLE`, `PARTIE_CHAMP`), jamais à l'écran titre (carte `ev01`, constante `CARTE_TITRE` déplacée dans `engine.py`), ni au menu de départ, aux logos, en combat, au casino ou dans le livre des monstres, ni pendant que la boîte « Revenir à l'écran titre » est ouverte.
- **« Revenir à l'écran titre » garde son effet** (D-184) : `retour_titre()` pose `retour_titre_fait` avant `killbank(4, false)` ; il retombe quand la carte du titre est arrivée (`step`) ou à l'application d'un état. Pendant le fondu et au titre, fermer l'application n'écrit rien : la banque 4 reste effacée.
- `Jeu._sauvegarde_fermeture(motif)` : une seule fois, dite dans la console (« Sauvegarde automatique écrite (fermeture de la fenêtre). »), jamais d'erreur ; rien pour les captures de test (`--shot`, sauf `DQ_SAUVEGARDE_FERMETURE=1`). Appelée au début de `on_close`, avant les réglages et l'arrêt du son.
- **Chemins de fermeture couverts** : croix et Alt + F4 (message `WM_CLOSE` → `on_close`) ; **menu Échap > Quitter > Oui** (`Jeu.quitter` fermait la fenêtre sans passer par `on_close` : ni sauvegarde ni réglages, corrigé) ; « Fin de tâche » de l'onglet Applications du gestionnaire des tâches (envoie `WM_CLOSE` aux fenêtres : **supposé**, non vérifié) ; fermeture de la fenêtre de console, Ctrl + C, Ctrl + Pause, fermeture de session et arrêt (`SetConsoleCtrlHandler` : le gestionnaire, appelé dans un autre fil, demande la fermeture à la boucle principale — Unicorn n'est utilisé que par elle — et attend au plus 4,5 s, Windows arrêtant le processus après 5 s) ; fin de session des fenêtres (`WM_ENDSESSION`). Sous Linux (essais) : SIGTERM et SIGHUP.
- **Limite établie** : un processus arrêté de force (`TerminateProcess` : « Fin de tâche » de l'onglet Détails, `taskkill /F`, coupure de courant) ne laisse aucune chance d'écrire quoi que ce soit. Aucune sauvegarde périodique n'a été ajoutée (non demandée).
- Tests : `tools/test_sauvegarde_fermeture.py` (30 tests) : quand sauvegarder, `AutoSave(true)` appelé, une seule écriture, message, erreur sans arrêt de la fermeture, ordre de `on_close`, menu Quitter, demande depuis un autre fil (console), signal SIGTERM, `WM_ENDSESSION` ; **sur le vrai moteur** : `data5.dat` écrit (15 360 octets) dans le dossier d'écriture, relu par le moteur (`loadbank(4)` : on retrouve la carte de la partie fermée alors que le journal 2 était chargé entre-temps), retour au titre : banque effacée et rien n'est réécrit ni pendant le fondu ni au titre. Essais de bout en bout de la visionneuse sous Xvfb : fermeture normale (`on_close`) et SIGTERM écrivent `data5.dat` et `data9.dat`.

### Non vérifié
- **Tout sous Windows** : la croix, Alt + F4, le menu Quitter, la fin de tâche, la console. **À confirmer par Sylfried.**
- Ce que fait exactement le Unity d'origine (moment, `AutoSave(true)` ou `(false)`), faute du code C#.
- Une fermeture en pleine animation ou en plein événement : la sauvegarde est celle du moteur à cet instant (comme `AutoSave(true)` d'origine) ; non essayé sur un cas précis.

## Avance #125 : l'erreur d'un passage plein écran ↔ fenêtre qui échoue est notée en entier (#123, 03/11/2026)

### Demande (D-218, 22 h 34)
« Je ne peux plus mettre le jeu en mode fenêtré j'ai un message m'indiquant que c'est impossible, et en faisant ça en plus mon écran clignote. » Son `reglages.json` dit `mode_fenetre` = 1 : le jeu se lance en plein écran, et la sortie du plein écran (« Fenêtre impossible ») échoue.

### Établi
- Le code de bascule (`regler_plein_ecran`, `_poser_plein_ecran`, `_mettre_plein`) n'a **pas été modifié par la PR #120** ; seul `_creer_plein_ecran` ne choisit plus l'écran (création sur l'écran principal, comme avant quand aucun choix n'était fait). Je n'ai trouvé aucune erreur évidente en relisant ce code ni celui de pyglet 2.1.19 (`Win32Window._create`, `set_fullscreen`).
- La console ne disait que « Fenêtre impossible (%r) » : le texte de l'exception, pas l'endroit où elle a eu lieu.

### Fait (diagnostic seulement)
- `Jeu._noter_echec_bascule(cible, erreur)` : à chaque échec d'un passage plein écran ↔ fenêtre, **la pile d'appels complète** de l'erreur (et, si le retour à l'état de départ échoue aussi, cette seconde erreur en note), l'état de la fenêtre (plein écran, taille, taille mémorisée, place d'avant, bureau), l'écran de la fenêtre pour pyglet, les moniteurs détectés (taille, position, principal), les versions de pyglet et de Python, dans la console **et** dans `dq4_pc/erreurs_fenetre.log` (à la suite des précédentes ; ignoré par git comme tous les `*.log` ; `DQ_JOURNAL_FENETRE` : un autre fichier). Jamais d'erreur levée par le journal.
- Tests : `test_window_mode.py` (42 tests dont 3 nouveaux : l'entrée du journal, un journal inécrivable, aucune entrée sans échec ; les échecs simulés écrivent dans un fichier temporaire).

### Non vérifié
- La cause du défaut : **inconnue** tant que l'erreur n'a pas été lue sur le PC de Sylfried (il doit refaire l'essai : lancer en plein écran, puis F11).

## Avance #132 : plein écran → fenêtre après le branchement d'un écran externe (#126, 03/11/2026)

### Demande (D-220, 23 h 08)
Le jeu est en plein écran, il branche un écran externe, le passage en fenêtre échoue ; après un relancement tout va bien, et en faisant glisser la fenêtre sur l'autre écran le plein écran marche (avec quelques scintillements au retour du plein écran sur l'autre moniteur). Son journal (`erreurs_fenetre.log`, PR #125) est joint.

### Établi (lu dans son journal)
- `OSError: [WinError -2147024890] Descripteur non valide` dans `Win32Window._create` → `Screen.get_dpi` → `GetDpiForMonitor`, pyglet 2.1.19, Python 3.14.8, Windows ; ses moniteurs : 1920 x 1200 en (0, 0) (principal) et 2560 x 1440 en (-331, -1440).
- pyglet garde pour la fenêtre un objet moniteur (`_screen`) qui porte la poignée Windows (HMONITOR) du moment de la création. Après le branchement d'un écran, Windows peut attribuer d'autres poignées : `set_fullscreen(False)` recrée la fenêtre avec cette poignée périmée et échoue ; le retour à l'état de départ réutilise la même poignée et échoue aussi (« Retour à l'état de départ impossible aussi » dans son journal), d'où « plein écran conservé » et le clignotement.
- Le plein écran vers un moniteur passé à `set_fullscreen(True, screen=…)` vient d'une lecture neuve de la liste : il marche, ce qu'il constate.

### Fait
- `Jeu._rafraichir_ecran()` : relit les moniteurs (`display.get_screens()`, objets neufs) et remplace `_screen` par celui de **mêmes position et dimensions** que l'ancien, sinon celui où se trouve la fenêtre, sinon le principal. Appelée au début de `_poser_plein_ecran`, avant que le moniteur de départ soit retenu (le retour à l'état de départ en profite aussi), dans les deux sens (plein écran → fenêtre, fenêtre → plein écran sans moniteur imposé). Ne lève jamais d'erreur (une relecture impossible laisse l'ancien moniteur).
- Tests : `test_window_mode.py` (48 tests dont 6 nouveaux : un faux moniteur périmé qui lève la même erreur que Windows ; plein écran → fenêtre, fenêtre → plein écran, retour à l'état de départ, moniteur débranché, relecture impossible). Les 4 tests de comportement échouent avec l'ancien comportement (vérifié en neutralisant la méthode).

### Non vérifié
- **Sous Windows avec un vrai branchement d'écran** : à confirmer par Sylfried (plein écran, brancher l'écran externe, repasser en fenêtre ; idem après débranchement).
- Le scintillement au retour du plein écran sur l'autre moniteur (non demandé, non traité ; le plein écran recrée la fenêtre, ce que pyglet fait à chaque changement de moniteur).

## Avance #133 : la course agit dès que le héros est libre au retour d'un combat (#127, 03/11/2026)

### Demande (D-221, 23 h 14)
« J'ai trouvé le même problème sur la touche pour courir qui ne fonctionne pas tout de suite en sortant d'un combat […] analyse partout où ce problème pourrait se trouver et règle le. » (Le problème de #107 : la course n'agissait qu'une seconde après l'arrivée sur une carte.)

### Établi (mesure sur le vrai moteur : combat forcé sur la carte du monde, direction tenue dès la fin du combat)
- Après la sortie de la partie combat, le fondu de retour dure 30 images. Global.Flag : 0x1 à l'image 0, 0x2d (joueur verrouillé, bit 4) des images 1 à 11, 0x29 dès l'image 12 (joueur libre), 0x28 à l'image 30. Le héros bouge dès l'image 13.
- `Jeu._facteur_vitesse` rendait 1.0 tant que `Etat.transition_combat()` était vrai (images 0 à 29) : environ 0,6 s sans marche accélérée ni accélérateur, malgré la touche tenue.

### Fait
- `_facteur_vitesse` : la ligne `transition_combat()` est remplacée par `Etat.garde_trans > 0` (les 1 à 3 images où le moteur change de scène entre deux fondus, joueur ni verrouillé ni libre) ; seul le verrou du joueur (Global.Flag 4) coupe ensuite l'accélération, comme pour #107.
- **Recherche des autres endroits** où l'accélération est coupée : `Etat.effet` (cascade d'entrée en combat), `attente_charge` (écran noir qui attend la scène d'un combat), `_horloge_combat`, parties de combat et mini-jeux, messages, menus du jeu, verrou du joueur : tous légitimes (le jeu a la main, ou c'est un combat). Aucun autre fondu de carte ne coupe l'accélération depuis #107. Non cherché : un cas où le verrou du joueur lui-même resterait levé trop longtemps (c'est le moteur qui décide).
- Tests : `test_game_priority.py` (retour de combat joueur libre ou verrouillé, entre deux fondus) et `test_battle_transition.py` (rejeu d'un vrai combat sur le vrai moteur : le facteur de chaque pas du retour est comparé aux vrais drapeaux).

### Non vérifié
- **Sous Windows** : à confirmer par Sylfried (tenir la course en sortant d'un combat : elle agit dès que le héros bouge).
- Avec la course tenue, le fondu de retour (en images du moteur) passe plus vite en temps réel, comme le fondu d'arrivée sur une carte depuis #107 : c'est la conséquence voulue d'une horloge plus rapide dès que le joueur est libre.

## Avance #142 : la sauvegarde automatique est celle du jeu (#128, 03/11/2026)

### Demande (D-220, 23 h 08)
« La sauvegarde auto n'a pas le même comportement que le jeu, ça ne doit pas me remettre au pixel près où j'étais, mais je crois que c'est à l'endroit d'où je viens : sur mobile en quittant le jeu dans une grotte la sauvegarde auto m'a ramené sur la map globale pile au niveau de l'entrée de la grotte, et dans un village à l'entrée du village, toujours sur la map globale, donc regarde dans le code source comment c'est fait. »

### Établi
- **`AutoSave` n'a que deux appelants dans `libdq4core.so`**, par le même raccourci (stub PLT 0x226290) : `TownPart::initialize` (appel en 0x19f988, à l'arrivée dans une ville ou un donjon) et `FieldPart::initialize` (0x19fa70, à l'arrivée sur la carte du monde). Les deux appellent `AutoSave(false)` : le moteur n'écrit alors que si les conditions de `StageStatus` (`isAbortSaveTown`, `isAbortSaveDungeon`, indicateur d'abandon de sauvegarde permis) sont réunies. La note de l'avance #124 (« aucune fonction du moteur n'appelle `AutoSave` ») était fausse : la recherche n'avait porté que sur les appels directs au symbole.
- Le code C# du cycle de vie de l'application (`OnApplicationPause`, `OnApplicationQuit`) n'appelle que `Sound$$SystemPause` et `Sound$$SystemQuit` : **le jeu d'origine n'écrit rien à la fermeture**.
- Mesuré sur le vrai moteur (échantillon de sauvegardes de la session, banque 4 = `data5.dat`, 15 360 octets) : charger le journal 1 (ville `mak1f1`) n'écrit pas `data5.dat` ; charger la sauvegarde 4 (carte du monde) l'écrit, sans aucun appel de la visionneuse ; `Global::startTown('dab1')` (donjon) depuis la carte du monde la réécrit ; `Global::startField()` aussi.
- Ce que fait le jeu en pratique : la sauvegarde automatique est celle de la **dernière arrivée** sur la carte du monde (ou dans un donjon selon ses conditions), donc « l'endroit d'où l'on vient », pas la position exacte quand on ferme : c'est ce qu'a vu Sylfried sur mobile.

### Fait
- Retiré de `engine.py` : `Moteur.sauvegarde_auto`, `Moteur.sauvegarde_auto_possible`, `retour_titre_fait`. Retiré de `window.py` : `Jeu._sauvegarde_fermeture`, les gestionnaires de la console de Windows, des signaux et du message `WM_ENDSESSION`, la demande de fermeture venue d'un autre fil dans `_boucle`, `DQ_SAUVEGARDE_FERMETURE`.
- Gardé : `Jeu.quitter` passe par `on_close` (réglages, historique, son) ; « Revenir à l'écran titre » efface toujours la banque 4 (`killbank(4, 0)`, D-184) ; rien ne la remet (le moteur ne l'écrit pas au titre).
- Conséquence assumée : sans les gestionnaires de la console, Ctrl + C et la fermeture de la console de Windows arrêtent le jeu sans passer par `on_close` (réglages et historique de la séance non enregistrés), comme avant #124. La croix, Alt + F4 et le menu Quitter les enregistrent.
- Tests : `tools/test_sauvegarde_auto.py` (12 tests ; remplace `test_sauvegarde_fermeture.py`) : plus rien de forcé dans `Moteur` et `Jeu` ; `on_close` ne touche pas au moteur ; **sur le vrai moteur** : l'arrivée en ville n'écrit pas la banque 4, l'arrivée sur la carte du monde l'écrit seul, fermer la fenêtre ne modifie aucun fichier de sauvegarde, « Revenir à l'écran titre » l'efface et rien ne la remet.
