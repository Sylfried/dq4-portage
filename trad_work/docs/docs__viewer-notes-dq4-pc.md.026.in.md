## Avance #290 : tout le projet en anglais, étape 1 (D-239)

### Demande
Sylfried (05/11/2026, 01 h 07) : « Revois toute l'organisation du projet pour changer la convention de nommage pour avoir tous les dossiers, les fichiers, les variables des fichiers pythons etc, bref tout en anglais »

### Fait (D-239, étape 1)
- **Dossiers et fichiers** : 327 déplacés ou renommés (`git mv`, l'historique des fichiers est conservé) : `noyau` → `core`, `fenetre` → `window`, `monde` → `world`, `rendu` → `render`, `combat` → `battle`, `persistance` → `persistence`, `textes_en` → `texts_en`, `outils` → `tools` (et ses sous-dossiers), `lancer_dq4.bat` → `launch_dq4.bat`, les tests (`test_langue.py` → `test_language.py`…), les documents (`docs/historique.md` → `docs/history.md`…). Correspondance complète : `docs/rename_map.md`.
- **Identifiants du code** : 4 830 noms (modules, classes, fonctions, méthodes, attributs, variables, arguments, constantes) : `Moteur` → `Engine`, `Etat` → `State`, `Jeu` → `Game`, `Fenetre` → `Window`, `mo` → `eng`, `reglages` → `settings`… Correspondance complète : `docs/rename_identifiers.tsv`. Méthode : un seul jeu de noms pour tout le dépôt, appliqué sur les jetons Python (pas de recherche-remplacement de texte), avec une analyse de portée (variables locales, attributs de classe, arguments nommés) qui a vérifié qu'aucun renommage ne fait se rencontrer deux noms ; les chaînes qui servent de nom (`getattr`, `hasattr`, `setattr`, `__slots__`, noms de fichiers Python, extraits de code lus par les tests) suivent.
- **Resté en français, voulu** : les textes affichés au joueur (clés de `tr()`), les commentaires, docstrings et documents ; les **clés** de dictionnaires, de `reglages.json` et des états instantanés, les identifiants de pages du menu Pause (`racine`, `affichage`, `son`…), les noms des variables GLSL (ce sont des chaînes, pas des identifiants) ; les options de la ligne de commande (`--largeur`, `--saves-ecriture`…, on garde les mêmes) ; les dossiers créés sur son PC (`donnees\…`), étape 2.
- **Anciens fichiers relus** : un état instantané (`.dqs`) enregistré avant ce changement garde les anciens noms d'attributs dans ses objets : `OLD_ATTRIBUTES` (`core/engine.py`, 42 noms), `OLD_MODULES` et `OLD_CLASSES` (`persistence/savestates.py`) les remettent sous leur nom actuel à la lecture ; réglages inchangés (clés françaises). Vérifié sur ses vrais `etat_01.dqs` et sur deux autres.
- **Corrigé au passage** : les constantes GLSL `VERT` (« vertex », pas « vert ») s'appellent `VERTEX…` et non `GREEN…` ; la prose française des commentaires et docstrings que le renommage avait touchée (456 mots courants qui sont aussi des identifiants : « Vitesse », « SANS », « liste »…) est rétablie ; un message du jeu qui citait `generer_ui.bat` cite `generate_ui.bat` ; les `.bat` gardent leurs fins de ligne CRLF.
- **Tests** : 100 scripts, 1 608 tests, tous OK (30 ignorés, comme avant ; `test_text_scrolling` demande `--apk` et `--saves`, comme avant) ; nouveau test `test_names_before_the_english_rename` (anciens noms d'attributs, ancien chemin de module `dq4_pc.noyau.moteur` et ancienne classe `Etat` relus) ; CI : `compileall dq4_pc tests tools`. Captures du jeu (fenêtre de la sauvegarde 4 et de la sauvegarde 1, 150 images) **identiques au pixel** avant et après.

### Établi / supposé / non vérifié
- **Établi** : tests, captures identiques, vrais états instantanés relus.
- **Supposé** : le comportement sous Windows (même code, mêmes chemins relatifs) ; les raccourcis qui pointaient sur `lancer_dq4.bat` sont à refaire.
- **Non vérifié** : les scripts de `tools/research/` (archives non maintenues) : compilés, pas exécutés ; la reprise d'un état instantané enregistré avant ce changement *dans le jeu lancé sous Windows* (relu et reconstruit ici avec le code actuel).
- **Limites** : les noms de variables locales très courtes ont reçu un nom anglais générique (même nom partout où le même mot était utilisé : `ne` → `n_savestates`, `ou` → `locations`…) ; commentaires, docstrings et documents sont restés en français (question posée à Sylfried, pas encore de réponse).

### À valider sur Windows
Double-clic sur `launch_dq4.bat` : le jeu démarre comme avant ; charger un état instantané enregistré avant ce changement ; ouvrir Paramètres, Historique et Sauvegardes.


## Avance #291 : tout le projet en anglais, étape 2 : les dossiers de ton PC (D-239)

### Demande
Sylfried (05/11/2026, 01 h 07) : « Revois toute l'organisation du projet pour changer la convention de nommage pour avoir tous les dossiers, les fichiers, les variables des fichiers pythons etc, bref tout en anglais » (suite de #290).

### Fait (D-239, étape 2)
- **Noms créés sur ton PC** : `donnees` → `data`, `sauvegardes` → `saves`, `etats\etat_NN.dqs` → `savestates\state_NN.dqs`, `avant_import_<date>` → `before_import_<date>`, `avant_rangement_<date>` → `before_tidy_<date>`, `reglages\reglages.json` → `settings\settings.json`, `historique_favoris.json` → `history_favorites.json`, `historique_messages.json` → `history_messages.json`, `journaux\erreurs_fenetre.log` → `logs\window_errors.log`, `reprise.json` → `resume.json` (clé `etapes` → `stages`). Variables d'environnement `DQ4_DONNEES` → `DQ4_DATA`, `DQ4_JEUX` → `DQ4_GAMES` (les anciens noms restent reconnus). Table complète : `docs/rename_map.md`.
- **Renommage sur place au premier démarrage** (`paths.migrate`, avant toutes les autres reprises ; `launch_dq4.bat` l'appelle déjà) : un simple renommage, **sans copie** (le cache et les APK pèsent plusieurs centaines de Mo) ; si un nom existe déjà à la nouvelle place, les deux dossiers sont fusionnés fichier par fichier et un fichier déjà présent n'est jamais écrasé (l'ancien reste où il est, la phrase « NON renomme » le dit) ; rien n'est supprimé (un dossier vidé est retiré, seulement s'il est vide) ; si Windows refuse (dossier ouvert dans l'Explorateur), on essaie fichier par fichier, sinon la phrase dit quoi faire et le renommage est refait au démarrage suivant ; une fois réussi il est noté (`english_names` dans `resume.json`) et ne se refait plus. Avec `DQ4_DATA` / `DQ4_DONNEES`, le dossier est à toi : seul son contenu est renommé.
- **Reprise des dispositions encore plus anciennes** (`jeux\DQ4`, `dq4_pc\sauvegardes`, `dq4_pc\reglages.json`…) : elle arrive directement sous les nouveaux noms ; les anciens noms d'étapes de `resume.json` / `reprise.json` sont traduits (`sauvegardes_portage` → `saves_pc_port`…).
- **Export / import** : l'export s'appelle `dq4_saves_<date>.zip` et range `savestates/state_NN.dqs` ; un `.zip` d'avant (`etats/etat_NN.dqs`) ou un `etat_NN.dqs` isolé s'importe toujours et s'écrit sous son nouveau nom.
- **Textes** : les messages de la console, l'aide de la ligne de commande, le texte de l'écran « Sauvegardes » et celui de la licence citent les nouveaux noms (français et anglais) ; `launch_dq4.bat`, `tools\*.bat`, `.gitignore` (`/data/` ; `donnees/` reste ignoré tant que le dossier n'est pas renommé) et la CI (`^data/` interdit dans le dépôt) aussi.
- **Resté en l'état, à dessein** : les noms de fichiers *internes* du cache (`carte11_*.pkl`, `plan_monde.npz`, `son_*.npz`… : il se recalcule, les renommer le ferait refaire) ; les variables d'environnement de débogage `DQ_*` (une centaine, pour les essais) ; les options de la ligne de commande ; les identifiants de pages du menu Pause (`etats`, `reglages`…).
- **Vérifié** : 100 scripts, 1 620 tests (33 pour `test_paths` dont le renommage normal, le conflit, la fusion, le dossier verrouillé, un dossier personnalisé, les phrases en deux langues et l'import d'un ancien `.zip`) ; essai de bout en bout avec ses vrais fichiers (`donnees\sauvegardes\data1.dat`…, `etats\etat_01.dqs`, `reglages\reglages.json`, `portage\`) : tout est au bon endroit, **mêmes empreintes MD5**, `donnees` n'existe plus, un deuxième lancement ne fait rien, le jeu démarre, charge la sauvegarde 1 et relit l'état instantané.

### Établi / supposé / non vérifié
- **Établi** : tests, essai de bout en bout sur Linux avec ses fichiers.
- **Supposé** : `os.replace` d'un dossier se comporte comme sous Linux sur son disque Windows (renommage atomique sur le même volume) ; le repli fichier par fichier couvre le cas « dossier ouvert ».
- **Non vérifié** : le premier démarrage *sur son Windows* après `git pull` (c'est ce qu'il doit valider) ; les raccourcis qui pointaient sur `lancer_dq4.bat`.

### À valider sur Windows
Après `git pull`, double-clic sur `launch_dq4.bat` (ferme d'abord les fenêtres de l'Explorateur ouvertes dans `donnees`) : la console dit « dossiers renommés en anglais », `donnees` est devenu `data` avec le même contenu, le jeu démarre, ta sauvegarde et tes états instantanés sont là.

## Avance #309 : audit complet du 05/11/2026, ce qui manque et ce qui bug (D-240)

### Demande
Sylfried (05/11/2026, 01 h 07, point 9) : relancer un audit complet, clore les sujets et issues concernés, en créer de nouveaux si de nouveaux problèmes sont trouvés ; « je ne te demande pas de modifier quoique ce soit, juste de faire l'état général du projet pour le comparer à la version mobile ».

### Fait (documents et issues seulement)
- **Huit relecteurs en lecture seule** (moteur, Unity, services, interface, cartes, sprites, combat, son) sur `main` = `becda5c` ; rapport : `docs/audit/audit_2026-11-05.md` (ce qui manque, ce qui bug, décisions, inventaire, constats du 04/11 revus, verdict sur chacune des 123 issues ouvertes, ce qui n'a pas pu être vérifié).
- **Issues** : 11 fermées (#71, #74, #83, #101, #122, #146, #167, #168, #173, #233, #243 : recherches terminées, fonctions supprimées par D-226, issue remplacée par #128) ; **17 créées** (#292 à #308 : moteur arrêté sans trace, lanceur et migration, dépendances, états `.dqs`, documents périmés, générique de fin, FSRA, trois décisions, textes de l'outil, cache de cartes, modèles 3D de combat, deux bugs de combat, son) ; 14 commentées (#64, #66, #69, #73, #77, #81, #88, #93, #245, #249, #251, #253, #263, #285) ; #249 en priorité haute ; étiquette `test-windows` ajoutée à #235. Les issues dont le test Windows est demandé restent ouvertes.
- **Constats principaux** : le générique de fin est le plus gros manque (#297) ; le ciel d'`ev09` se décale quand le plan défile (#249) ; un moteur arrêté ferme la fenêtre sans trace (#292) ; « ERROR 3080 » ne vient pas du patch FR (#81) ; l'angle de caméra sur le toit après la chambre d'Alina vient du script de `cbf3` et non de la visionneuse (#285) ; les FEMV sont du code mort dans Unity (#66, #69) ; aucune régression de comportement dans les PR #196 à #291 (**rectifié en #310 : le renommage D-239 plantait sous Windows, voir plus bas**).
- **Rien dans le code** : aucun fichier de `dq4_pc/`, `tools/`, `tests/` n'a changé.

### Établi / supposé / non vérifié
- **Établi** : les essais sur le moteur réel (ancien état relu, écriture refusée, tas épuisé, cinq langues, déterminisme, durée des pas), les balayages (529 cartes, 4 761 passes de sprites, 255 formations, 171 effets, 685 sons), les tests du dépôt relancés sur copie.
- **Supposé** : ce qui se verrait à l'écran pour FEAN, FSRA, le générique et les fbx de combat ; la taille des panneaux des PNJ (#303).
- **Non vérifié** : tout ce qui est Windows, GPU, écoute ; le jeu mobile (aucune capture) ; les chapitres 2 et suivants joués de bout en bout ; 14 types de fenêtres jamais ouverts.

### À faire de ton côté
Aucun test Windows nouveau. Cinq questions à trancher : #299, #303, #302, #307 et #93.

## Avance #310 : plantage au démarrage sous Windows, `_hidden` pris par pyglet (D-241)

### Demande
Sylfried (05/11/2026, 10 h 09) : journal de la console collé, sans texte, du premier lancement de `launch_dq4.bat` après `git pull` : le jeu s'arrête (code 1) sur `TypeError: 'bool' object is not callable` (`dq4_pc/window/menu_display.py`, `_draw_menus`), après « Rendu hors écran : 1920 x 1200 (x1), anticrénelage x8 ». Un clic de souris pendant « Chargement du moteur... » avait aussi laissé `AttributeError: 'Game' object has no attribute 'engine'` (affiché, non fatal).

### Cause (établie en lisant le code de pyglet 2.1.19)
- Le renommage D-239 (#290) a fait de la méthode `_cachee(typ)` de `Game` une méthode `_hidden(typ)`. La fenêtre Windows de pyglet (`Win32Window`, `pyglet/window/win32/__init__.py`, ligne 125) a un **attribut de classe `_hidden = False`** (fenêtre cachée ou non) : il masque la méthode, et `self._hidden(wnd.typ)` devient `False(...)`, d'où `'bool' object is not callable`.
- Sous Linux, ni la fenêtre sans tête ni X11 n'ont cet attribut : les 1 620 tests, les captures et l'audit D-240 n'ont rien vu. Le contrôle de collisions de D-239 ne regardait que les noms du projet, pas ceux des classes de bibliothèques.
- Le clic pendant les logos : `on_mouse_press` lisait `self.engine` **avant** de tester `self._ready`, alors que le moteur est créé plus tard (défaut ancien : l'ancien code lisait `self.moteur` dans le même ordre ; sous Windows une exception d'une fonction de rappel est seulement affichée).

### Fait
- Méthode renommée `_menu_hidden` (`window/menu_display.py`, `window/battle_scene.py`, deux tests qui la simulent, `docs/rename_identifiers.tsv`). `on_mouse_press` teste `_ready` d'abord.
- **Nouveau test** `tests/test_window_name_collisions.py` : lit le code de pyglet pour Windows, X11, macOS, Wayland et sans tête, et refuse tout nom de `dq4_pc/window/*.py` (méthode, attribut de classe, `self.x = ...`) déjà pris par la fenêtre de pyglet, sauf `_width`, `_height`, `_screen` (écrits exprès dans `full_screen.py`) et les `on_*` (vrais événements, vérifiés). Il échoue sur l'ancien code (3 échecs) et passe avec la correction.
- **Autres collisions cherchées, aucune trouvée** : toutes les classes héritant d'une classe de bibliothèque ou du projet (`pickle.Unpickler`, `unittest.TestCase`, `pyglet.media.Source`, les classes du projet qui en héritent), les variables locales dont le nom masque un module, une fonction globale ou un builtin utilisé plus haut dans la même fonction, les noms d'attributs écrits dans des chaînes (`getattr`, `setattr`, `hasattr` : 0 ancien nom), les attributs posés sur des objets de pyglet ou de numpy (tous sur des objets du projet).

### Établi / supposé / non vérifié
- **Établi** : la cause (code de pyglet lu, erreur du journal identique) ; le test de non-régression échoue sans le correctif et passe avec ; suite complète du dépôt relancée sous Linux.
- **Supposé** : que ce soit la seule collision de ce genre (les contrôles ci-dessus ne couvrent que ce qui s'analyse dans le code, pas ce qui se fait par `exec` ou noms construits).
- **Non vérifié** : le jeu sous Windows après la correction (rendu des menus, combat, plein écran) : Claude ne peut pas le lancer.

### À faire de ton côté
`git pull`, puis relancer `launch_dq4.bat` (le raccourci doit pointer sur `launch_dq4.bat`, plus sur `lancer_dq4.bat`). **#289 reste ouverte** : à valider quand le jeu tourne.
