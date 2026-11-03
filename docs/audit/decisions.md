# Registre des décisions de Sylfried (agent « audit-github », lot PR #43, version révisée à la reprise)

Lecture seule. Établi le 02/11/2026 à partir de : dépôt `dq4-portage` (README, `docs/*.md`, 42 PR), dépôt `dq4-pc` (43 issues, commentaires, 36 PR), copies des documents du Projet dans `/home/claude/pjdocs/`, mémoire utilisateur (lecture), brief commun du lot #43 et brief du lot #42 (`/tmp/specs/brief_commun42.md`, qui reproduit **en entier** les 17 points du message de 23 h 24), résumé de contexte de la session (qui cite le message de 02 h 12 à 02 h 14), **transcription JSONL de la session principale** (les messages de 02 h 27 à 02 h 38 y sont lus directement), missions des sous-agents des lots #40 à #42 (qui recopient des phrases de Sylfried « mot pour mot »), recherche dans les anciennes conversations (sans résultat utile).

**Ce que cette révision change** : le prédécesseur disait que plusieurs citations étaient tronquées ; c'était faux pour le lot de 23 h 24 (le texte complet existe) et le texte intégral des messages de 02 h 27 à 02 h 38 était lisible. J'ai donc : (1) remplacé les citations tronquées par les textes complets (§3), (2) ajouté les phrases du lot de 18 h 02 et de 20 h 46 reproduites dans les missions (§3-A, §3-B), (3) ajouté les six messages de 02 h 27 à 02 h 38 (§5b, tous nouveaux pour ce registre, dont l'historique des messages et la vitesse des combats), (4) ajouté les retours des premières PR (§6.5), (5) corrigé deux lectures du prédécesseur (D-86 / C-8 : Sylfried avait bien demandé de revoir les shaders flous ; D-79 : les 18 entrées retirées de l'éditeur dépassent l'exemple donné) et (6) ajouté les contradictions C-13 à C-21.

## 0. Comment lire ce registre

**Source** (la colonne dit toujours d'où vient l'énoncé) :
- **[T]** lu **directement** dans la transcription de la session principale (JSONL), texte intégral. La transcription est en UTC ; chaque message de Sylfried y porte la mention « The user's timezone is Europe/Paris (UTC+01:00). Message sent at Mon 2026-11-02 02:27 local time. » : toutes les heures de ce registre sont l'**heure locale de Sylfried** (UTC+1).
- **[C]** citation de Sylfried **recopiée mot pour mot par Claude** (résumé de contexte, brief du lot #42, mission d'un sous-agent). Je n'ai pas le message d'origine pour comparer : sens fiable, mots probables.
- **[R]** « demande / retour de Sylfried » **rapporté** par Claude dans une PR ou une note, sans le texte intégral. Fiable pour le sens, pas pour les mots.
- **[M]** entrée de la mémoire utilisateur marquée `[stated]`.
- **[V]** validation explicite de Sylfried (« c'est bon », « ok »).
- **[K]** choix **de Claude** (consigné comme tel dans les PR/notes), que Sylfried n'a pas formulé. À ne pas confondre avec une décision de Sylfried.

**Limites de cette lecture** (honnêteté) :
1. La transcription ne contient que les messages **postérieurs à la compaction** (02 h 27 à 02 h 38) ; ceux de 02 h 12 à 02 h 14 n'y figurent que dans le résumé de contexte (régime [C]). Pour les périodes antérieures : message de 23 h 24 en entier dans le brief #42 ([C]), phrases choisies des lots de 18 h 02 et de 20 h 46 dans les missions ([C]), le reste dans les corps de PR (« Retours de HH h MM », régime [R]). Les lots de 18 h 02 et de 20 h 46 ne sont donc **pas** couverts en entier (le second compte 21 points, je n'ai le texte que d'environ seize).
2. Les anciennes conversations accessibles par recherche ne concernent que la piste Unity et le patch FR.
3. Le fichier `Menu_Echap_DQ4_PC.xlsx` (spécification du menu Pause rédigée par Sylfried, citée par les PR #25 à #27) n'est **pas** dans le dépôt : son contenu n'est connu que par les résumés de Claude.
4. Les dépôts `dq4-portage-unity` et `dq456-traductions-fr` et le document `claude/piste-3-projet-unity.md` n'ont pas été lus (consigne).
5. Les heures des PR sont en heure GitHub (UTC) ; l'heure locale de Sylfried = UTC + 1. Les heures des lots (18 h 02, 20 h 46, 23 h 24) sont celles que Claude a écrites dans les PR : locales.
6. Les faits tirés de la **mémoire** utilisateur sont les lignes D-01 à D-10 (étiquette [M]) ; rien d'autre dans ce registre ne vient d'elle.
7. Chaque « état sur `main` » vient d'une lecture du code à `08f5785` (pas d'exécution, pas de test Windows).

## 1. Cadrage, organisation, dépôts (29-30/10)

| ID | Date | Source | Énoncé | Effet sur le jeu / le projet | État |
|---|---|---|---|---|---|
| D-01 | 29/10 | [M] + issue #25 | Portage natif PC de Dragon Quest IV Android, **16/9 d'abord ; l'interface est traitée à part** | périmètre ; le 16/9 vient en premier, les autres ratios sont à vérifier (issue #24) | maintenu |
| D-02 | 29/10 | [M] + issue #25 | Base = APK **déjà patchés en français** (`jeux\DQ4\patched_apks`) | aucun texte du jeu n'est retraduit par le portage | maintenu |
| D-03 | 29/10 | [M] + issue #25 | Stratégie : voie A (émulation du moteur ARM) puis B (recompilation x64) puis C (émulateur Android) | voie A retenue et validée (issue #26) : le moteur original tourne tel quel sous Unicorn | maintenu |
| D-04 | 29/10 | [M] + issue #25 | Projet **séparé du patch FR** : on ne touche jamais aux Excel, à `DQ_Patch_FR.exe`, `build_exe.bat` | règle 2 du brief | maintenu |
| D-05 | 29/10 | issue #25 (rédigée par Claude) ; non attribuée à une phrase de Sylfried | Aucun contenu Square Enix distribué ; les outils lisent les fichiers de l'utilisateur | `.gitignore` strict, extraction à l'exécution | maintenu (l'attribution exacte à Sylfried est **non vérifiée**) |
| D-06 | 30/10 | [M] ; dq4-pc PR #42 | Claude gère **tout le git** : issues, commits, push, PR, fusions | workflow ; fusions en squash | maintenu |
| D-07 | 30/10 | [M] | Dépôt GitHub créé par lui-même (compte perso `Sylfried`) | | maintenu |
| D-08 | 30/10 | [M] | Trois projets côte à côte, chacun avec son dossier et son dépôt : patch FR (`dq456-traductions-fr`), natif (`dq4-portage`), Unity (`dq4-portage-unity`) ; l'ancien `dq4-pc` et l'ancien venv sont supprimés du dossier `Projet DQ` | tout ce qui sert au natif va dans `dq4-portage` (local + dépôt) | maintenu ; `dq4-pc` reste sur GitHub à titre d'historique |
| D-09 | 30/10 | [M] ; issue #57 (verdict) ; dq4-pc PR #67/#79 | **Piste Unity mise en pause** pour se concentrer sur « l'autre version » ; verdict du premier essai : « l'expérience dans sa globalité ne ressemble pas à la version mobile » (rapporté) | la fidélité à la version mobile devient le critère | maintenu |
| D-10 | 30/10 | [C] (chat Unity, réponse à la demande de captures du mobile) | « Non bah continue juste pour le moment » | la preuve 2 (combat dans Unity) est faite, puis pause | clos |

## 2. Principes de fidélité et de méthode

| ID | Date | Source | Énoncé | Effet | État |
|---|---|---|---|---|---|
| D-11 | 02/11 02:12 | [C] | « reste sur de la réalisation **1 pour 1 de la version mobile**, tu prends une zone en portrait au milieu de l'écran et tu calcules où placer le dragon et le château pour convenir à comment c'est fait sur mobile » | la zone centrale 9:16 d'un écran 16:9 doit correspondre à la vue du téléphone ; vaut pour le titre, par extension pour toute scène | maintenu |
| D-12 | brief | [K] formulé par Claude, **fondé sur D-09 et D-11** | « Le jeu d'origine fait foi » : tout ce que la visionneuse remplace (couche Unity) doit coller au comportement mobile « sauf mention contraire de l'utilisateur » ; le moteur d'origine ne se modifie pas | règle 4 du brief | maintenu ; **nuancé en §10 (C-6)** |
| D-13 | 02/11 01:42 | [C] question + confirmation | « Quand je te parle d'une situation précise où j'ai découvert un bug, tu le règles bien **de façon globale** ? Pas juste pour la situation décrite ? » | règle 6 du brief : cause racine et tous les endroits concernés | maintenu |
| D-14 | 02/11 02:12 | [C] | « quand le jeu change la valeur manuellement via un script (je crois que c'est le cas pour **Nimzo dans DQ5**), alors pareil le jeu **prend le dessus** sur la règle des paramètres du joueur, **et c'est valable pour tout** » | une valeur imposée par le jeu l'emporte sur les réglages (vitesse du texte, mais aussi tout réglage équivalent) | à implémenter dans le lot #43 (état au 02/11 : `defilement_force` n'existe que pour le défilement des combats, `reglages.py:43`) ; précédent déjà codé : la caméra (D-102, `fenetre.py:1171-1172` depuis #47) ; origine : sa demande D-124 |
| D-15 | brief | [R] | Réponses courtes et honnêtes ; toujours dire établi / supposé / non vérifié ; outils « clé en main » (« vibecoder ») ; il teste sur son PC Windows | forme des rapports | maintenu |
| D-16 | 02/11 02:12 | [C] | « Une fois que tu as fais tous ces correctifs, fais un audit giga complet pour régler des soucis sur des sujets déjà traités et faire un rapport de ce qui reste à faire, notamment au niveau des issues sur github mais aussi sur des trucs dont on n'a jamais évoqué comme : est-ce que toutes les fonctionnalités sont présentes (casino, églises, banque...), tous les menus fonctionnent, tous les interrupteurs sont bien enclenchés au bon moment, les variables sont bien définies et modifiées uniquement quand c'est demandé, les pnjs sont aux bons endroits, les bons scripts sont lancés au bon moment, bref vraiment un audit sur tout ce qu'il reste à faire pour que le jeu soit 100% jouable (bien sûr les décisions que j'ai prise doivent être prises en compte pour que tu saches si une fonctionnalité absente ou modifiée dépend d'une décision de ma part ou d'un oubli de la tienne ou tout simplement d'un bug) » | cet audit | en cours |

## 3-A. Lot de dimanche 01/11 à 18 h 02 (PR #40) : phrases reproduites dans les missions [C]

Les autres demandes de ce lot (menu de départ centré, bouton « Sauvegardes », licence, saisie du nom) ne sont connues que par le corps de la PR #40 : voir D-72, D-73 (§6.3).

| ID | Source | Énoncé | Effet | État sur `main` |
|---|---|---|---|---|
| D-100 | [C] | « normalement il y a des **encadrés au début d'un chapitre qui apparaissent sur fond noir**, et au début du prologue il y a une **animation (des coups d'épée)** avant que le vrai jeu se lance, et là je n'ai rien eu de tout ça » | bandeau « Prologue » sur noir, cinq coups d'épée, travelling vers le héros (PR #40 ; NV:371-375) | fait ; **taille des éclats et hauteur du bandeau (225) supposées**, sans capture du mobile (G-101) |
| D-101 | [C] | « un encadré violet est apparu lors de la transition vers le choix du nom (un peu comme pour la fin des combats) » | bug : message reçu après la fermeture d'une fenêtre, qui la faisait revivre une image ; corrigé (PR #40) | traité ; vérifié en images consécutives sous Mesa, **non vérifié sur Windows** |
| D-102 | [C] | « Fais en sorte que quand la caméra est contrôlée par le jeu (lors d'une cinématique par exemple) ça **bypass** l'option qui est de centrer la caméra sur le joueur ; cette option n'est valable que lorsque le joueur est libre de ses mouvements. » | l'option « Centrer la caméra sur le joueur » est ignorée quand le jeu pilote la caméra (`TownCamera` verrouillée, `Moteur.camera_jeu()`) | **fait**, établi par lecture ; **depuis #47 l'option n'existe plus** : le centrage est toujours actif sauf quand le jeu a la caméra : `fenetre.py:1171-1172` (`centre = not libre and not mini and not self.cam_jeu and not titre`). **C'est le précédent de D-14** : même principe (le jeu prend la main), limité à la caméra |
| D-103 | [C] | « Il y a un *bip* qui retentit lors de l'ouverture d'une boîte de dialogue (testé lorsque je casse un tonneau ou une jarre au tout début du jeu […]), est-ce normal ? […] » | **question**, pas un ordre. Réponse de Claude : normal, bruitage 300 commandé par le moteur (NV:367). Rien changé | clos. Écart mineur signalé et non corrigé : Entrée / Espace / M ne jouent pas le bip alors que le clic sur le bouton le joue (NV:368 ; G-173) |

## 3-B. Lot de dimanche 01/11 à 20 h 46 (PR #41, « vingt et un points ») : phrases reproduites dans les missions [C]

Ordre = celui de la source. Les effets viennent du corps de la PR #41.

| ID | Source | Énoncé | Effet | État sur `main` |
|---|---|---|---|---|
| D-120 | [C] | « Revois l'assignement des commandes : supprime toutes les options pour sélectionner la touche d'accélération pour la course et pour la caméra, fais une nouvelle section juste en dessous de "Caméra" pour avoir comme options : vitesse de marche, vitesse de caméra, vitesse de transition, touche d'accélérateur et vitesse de l'accélérateur (pour les valeurs tu te bases sur celles actuelles) » | section « Vitesses » (voir D-77) ; anciens `reglages.json` migrés (`reglages.py:153`) | fait ; la ligne « Vitesse de l'accélérateur » (`pause.py:424-425`) sera renommée par D-48 |
| D-121 | [C] | « la taille de la fenêtre s'est agrandie quand j'ai créé une sauvegarde, il faut garder la même taille, comme sur le screen 5 » | page États : la fenêtre garde sa taille (PR #41) | traité (non revérifié) |
| D-122 | [C] | « renomme donc cette option en "Revenir à l'écran titre", supprime la petite flèche qui indique que ça ouvre un autre menu car maintenant ce bouton va prendre la place du bouton originale pour revenir à l'écran titre » | voir D-76 | fait ; **effet de bord : efface la sauvegarde automatique** (comportement d'origine `killbank(4)`, G-098) |
| D-123 | [C] | « le bouton "Paramètres" du menu in-game laisse son nom mais fais plutôt en sorte qu'il ouvre le menu échap, et supprime donc tout ce qui va avec l'appui original de ce bouton » | patch mémoire du moteur (`moteur.py:460-474`, C-6) ; les options de la fenêtre d'origine (volumes, « Taille de la croix ») ne sont plus joignables (PR #41, « Plus joignables ») | fait ; conséquence acceptée **par Claude**, non discutée avec Sylfried (G-102) |
| D-124 | [C] | « Rajoute une option pour la vitesse du texte dans le menu échap ainsi que pour la vitesse de défilement (pour passer d'un dialogue à l'autre, et il faut pouvoir faire en sorte de désactiver le défilement auto pour pouvoir passer les dialogues manuellement, et je crois que cette fonction ne concerne que les combats, pas les dialogues normaux) » | page « Texte et défilement » ; **la vitesse du texte est un crochet de la visionneuse** (le jeu d'origine n'a pas cette option, `moteur.py:382-400`) ; le défilement ne concerne que les combats, comme il le croyait (PR #41) | fait ; « Défilement automatique » supprimé le soir même (D-26). **Cette phrase est la raison d'être de D-14** (priorité du jeu) |
| D-125 | [C] | « Tu penses pouvoir ajouter plus d'options pour le son ? Du genre activer/désactiver les musiques/effets et avoir un volume réglable pour tout types de sons ? » | Son en 5 catégories avec interrupteur et volume (D-78), puis une ligne par son (D-23) | fait ; rendu audio réel sur haut-parleurs non vérifié (G-121) |
| D-126 | [C] | « L'option "Afficher cette interface à l'écran" ne concerne que l'interface sélectionnée ? Car c'est censé fonctionner comme ça, et mets cette option juste en dessous de celle qui choisit l'interface à modifier (qui doit toujours être en premier de la liste) » | l'option ne concerne plus que l'interface choisie ; placée sous le sélecteur (PR #41) | traité |
| D-127 | [C] | « Revois les regroupements des interfaces car là je trouve que c'est un peu confus, supprime aussi les choix qui ne servent à rien, là le choix "Aperçu d'objet" ne laisse rien modifier (exemple de regroupement : dialogues avec OUI/NON etc, et ne compte pas les interfaces du lancement du jeu dedans) » | 54 entrées en 11 groupes ; **18 entrées retirées** (lancement du jeu, `Config`, `MagicInfo`, `MonsterName`, `BattleHoppingNumber`…) | fait. **Il a cité un seul exemple de choix inutile ; la liste des 18 est le choix de Claude** (C-21) |
| D-128 | [C] | « Rend la fenêtre "Interface" dragable, tant que c'est un appui long on peut la déplacer, un appui court pour la déplier/replier et un double clic pour la remettre à sa position initiale par rapport à l'interface choisie » | fenêtre déplaçable ; la PR #42 corrige le geste (D-35) ; position gardée pour la session seulement (G-110) | traité, à reconfirmer sur Windows (G-007) |
| D-129 | [C] | « Le plein écran (s'il est coché dans le jeu) doit être effectif dès le lancement du jeu, pas uniquement sur l'écran titre » | plein écran dès l'ouverture de la fenêtre, logos compris (PR #41) | fait ; flash au lancement non vérifié (G-004) |
| D-130 | [C] | « Tu penses pouvoir ajouter des effets d'affichage ? comme l'anti-aliasing ou ce genre de choses, mais ne le fais que si c'est pertinent » | **délégation à Claude** : MSAA x2/x4/x8, suréchantillonnage, netteté, luminosité retenus ; FXAA, SMAA, scanlines, contraste, bloom écartés (PR #41 ; D-80) | fait ; non vérifié sur GPU réel (G-003, G-057) |
| D-131 | [C] | « Revois les options d'affichage car je crois que pas tout fonctionne, et revois aussi les shaders car certains rendent juste les pixels plus flous encore » | retrait des shaders « Régions lissées » et « Bicubique » (« ils ne faisaient que flouter ») ; le lissage des textures s'applique aussi aux sprites (PR #41) | fait. **Le retrait est une réponse de Claude à une demande réelle** (D-86, C-8) |
| D-132 | [C] | « je ne sais pas comment doit être affiché ce texte mais certainement pas comme ça... » ; « je ne pense pas que ça soit la bonne police et je crois qu'il y a aussi une image à joindre non ? » ; « Chapitre 1 : Ragnar McRyan et le mystère des enfants disparus » (simple texte du jeu cité) | la police des menus est la police bitmap d'origine **SE-GARRIR** (et non GMaruGoPro-M : erreur des notes corrigée) ; le bandeau de chapitre est corrigé (PR #41) ; le texte du prologue sur noir est « finalement bon » (D-36) | traité ; pause et aperçu de l'éditeur gardent `ui_font.otf` (G-166) |
| D-133 | [C] | « les textes qui dépassent n'est pas un souci, ça va être réglé dans les traductions que je fais dans un autre projet, mais par rapport au mobile je sais que ça dépasse tout de même un peu plus que prévu, donc si tu peux t'aligner sur le mobile pour la taille des textes par rapport à la taille de l'interface pour au moins avoir les mêmes écarts que le mobile » | plus de compression du texte ; écarts texte / plaque comme sur mobile (PR #41) | fait, **sans capture du mobile** (G-023). **Règle d'audit : un texte français trop long qui déborde n'est pas un défaut du portage, c'est l'affaire du projet de traduction** (C-13) |
| D-134 | [C] | « le choix au clavier sélectionne encore toute la ligne, ça me semble une bonne idée mais il faut alors que les commandes de gauche et de droite pour les déplacements ou pour la caméra servent à sélectionner le nombre d'objets à acheter » | boutiques : gauche / droite changent la quantité de la rangée choisie (1 à 9) (PR #41 ; D-81) | codé, **jamais joué** (G-092, G-164) |
| D-135 | [C] | « Comment est fait le choix entre assombrir la case ou mettre une flèche quand il s'agit de l'appui ou du survol d'un bouton ? Je parle sur mobile […] » | **question**. Réponse de Claude : seul l'assombrissement du doigt appuyé existe sur mobile ; cadre jaune et flèche sont des ajouts PC (D-82) | clos par D-29b (cadre jaune supprimé) |
| D-136 | [C] | « j'ai eu une légère latence lors de sa transformation, et je crois que l'effet du sort morph s'est mis derrière elle alors qu'elle aurait dû se mettre devant elle (je suis pas sûr de ça) » | effet dessiné devant le personnage, ancré ; latence ramenée de 2,7 s (à froid) à 0,05 s (PR #41). **Il disait ne pas être sûr** du « derrière » | traité ; taille / place du nuage et Morph en combat non vérifiés (G-080) |

## 3. Message du dimanche 01/11 à 23:24 (6 captures, 17 points) : texte intégral [C]

Source : `/tmp/specs/brief_commun42.md` (qui recopie les 17 points). Ce lot a été implémenté dans la PR portage #42. Les décisions D-21 et D-28 ont été **modifiées** depuis (voir §5, D-30).

| ID | Point | Énoncé (intégral) | Effet (PR #42) | État |
|---|---|---|---|---|
| D-20 | 1 | « Supprime le texte au tout début "Chargement de la sauvegarde", laisse juste un écran noir » | écran de chargement entièrement noir | maintenu |
| D-21 | 2 | « Modifie le mode plein écran, je veux finalement 3 modes : fenêtré, plein écran et plein écran exclusif » | `mode_fenetre` 0/1/2 | **annulé par D-30** |
| D-22 | 3 | « Nouvel ordre pour le panneau "Affichage" : Fenêtre (le nouveau mode) > Résolution > Netteté > Shader > Lissage des textures > Vignetage > Anticrénelage > Suréchantillonage > Luminosité > Distance caméra > Centrer la caméra sur le joueur (si j'ai oublié un bouton ne le supprime pas, place le juste où tu trouverais que c'est cohérent) » | ordre appliqué ; Claude a placé « Correction des bords » (nouveau) après « Distance caméra » | maintenu ; **règle générale : ne jamais supprimer un bouton non cité** ; « Lissage des textures » sera supprimé par D-46 |
| D-23 | 4 | « Revois le panneau de son pour supprimer les sections et n'avoir qu'une ligne par son avec le nom de la ligne le type de son, la barre de volume, un bouton pour le muter et un autre pour le remettre par défaut » | une ligne par type de son | maintenu ; bouton défaut validé (D-38) |
| D-24 | 5 | « Rajoute le dragon de l'écran d'accueil » | `fbx.py`, modèle c1018 (vol d'arrivée puis vol stationnaire) | maintenu ; corrections demandées le 02/11 (D-33) |
| D-25 | 6 | « Renomme le menu "Texte et défilement" en "Vitesse de défilement du texte" » | renommé | maintenu |
| D-26 | 7 | « Supprime les sections, supprime "Défilement automatique", renomme "Vitesse de défilement" en "Messages en combat" et renomme les options en Rapide, Moyen, Lent, Manuel (et bien sûr l'option manuel nécessite d'appuyer sur une touche pour la faire défiler) et renomme "Normal (jeu)" en "Normal" » | page réduite, `defilement_combat` 0/2/3/4 ; « Moyen » = 2 et « Lent » = 3 sont des **choix de Claude** à valider (D-88) | maintenu |
| D-27 | 8 | « Screen 1 : comme pour les écrans d'avant (les textes sur le développeur, Yuji Horii etc, ne sont pas centrés comme le logo, ils sont un peu trop hauts) par contre le bouton "Touchez l'écran" lui il est bien placé... » | crédits centrés comme le logo (mesuré 0,500 de la hauteur sur 4 formats) | maintenu |
| D-28 | 9 | « Fais en sorte que F11 ou Alt+Entrée permette de passer en plein écran exclusif » | F11 / Alt+Entrée | **cible modifiée par D-30** ; les raccourcis restent |
| D-29 | 10 | « Screen 2 : masquer la croix individuellement ne lui mets pas le mot "Masqué" comme quand on masque l'interface en entier, ça serait bien que ça soit aussi indiqué pour les éléments quand ils sont cachés individuellement » | étiquette « Masquée » (croix, fenêtres) / « Masqué » (boutons) | libellés **à valider** (D-89) |
| D-29a | 11 | « Rétablir l'interface ne doit pas juste remettre les boutons en place, ça doit aussi remettre leur taille et toutes les options lié à l'interface actuel au global à leur position par défaut, pareil pour le bouton qui permet de tout rétablir » | « Rétablir cette interface » / « Rétablir toutes » remettent tout (position, taille, affichage, options liées, grille) | maintenu |
| D-29b | 12 | « Screen 3 : Mets plutôt des options en x1, x2, x3 et x4, et change aussi le fait qu'il y ait l'encadré jaune, les options du menu reprennent l'interface du mobile donc quand on les survole il y a l'option d'assombrissement du fond qui s'applique. Donc pour tous les boutons où cet encadré jaune se trouve il faut le supprimer » | marche, caméra, transition en x1..x4 (l'accélérateur garde son curseur) ; plus d'encadré jaune : le survol assombrit la plaque | maintenu ; **inverse la convention PC de la PR #41** (C-5) |
| D-29c | 13 | « Screen 4 : je crois qu'il y a eu une régression sur la bulle au-dessus de ce que je peux interagir avec, elle semble trop haute » | bulle « ! » ancrée au personnage, indépendante de l'inclinaison / rotation | traité ; cas exact (tonneaux) non reproduit (G-060) |
| D-29d | 14 | « Dans le prologue, lors de la scène avec la grenouille, la caméra ne se dirige pas directement vers elle en diagonale, elle fait droite puis bas, il me semble que la version originale fais directement un déplacement en diagonale, donc vérifie ça, et pareil quand elle s'en va la caméra doit normalement la suivre tout du long, mais là elle s'arrête assez vite, sans doute pour ne pas dévoiler l'envers du décor mais pour le coup **je veux que si dans un écran de téléphone le comportement c'est de suivre l'évènement ou le PNJ en entier alors ça doit être pareil ici aussi** » | la visionneuse bornait la caméra alors qu'Unity ne borne rien : elle suit maintenant ce que commande le jeu (écart 0,000 mesuré) | traité. **Décision de principe : on montre « l'envers du décor » si le mobile le montre** (précédent de D-11) |
| D-29e | 15 | « Screen 5 : as-tu une idée de comment on pourrait enlever cet effet de platitude aux sprites des PNJ quand ils sont trop proches des bords gauche et droit de l'écran ? » | question ouverte ; cause trouvée (panneau reculé en profondeur) et corrigée ; réglage `correction_bords` ajouté **par Claude** | **réglage à supprimer** (D-31) |
| D-29f | 16 | « D'ailleurs, es-tu sûr que l'angle de la caméra est bien le bon ? » | question ; vérifié au désassemblage et par équivalence numérique (écart 4e-15) : pas d'erreur trouvée | clos (G-064) |
| D-29g | 17 | « Screen 6 : je ne sais pas pourquoi, mais lors du déclenchement de cette scène j'ai un petit bug de la caméra, c'est comme si quand je cours et que je parle à mon père, elle continue légèrement son chemin avant de se recentrer sur moi et de lancer l'évènement » | caméra rigide sur le héros ; symptôme exact **non reproduit** | traité, à reconfirmer (G-061) |

## 4. Messages de 23:33, 01:42 et 01:44

| ID | Date | Source | Énoncé | Effet | État |
|---|---|---|---|---|---|
| D-35 | 01/11 23:33 | [C] [V] | « J'ai oublié tout à l'heure mais non je n'arrive pas à faire glisser la fenêtre "Interface" » | bug traité par la PR #42 (le geste était annulé si on bougeait avant 0,35 s) | à reconfirmer sur Windows |
| D-36 | 01/11 23:33 | [C] [V] | « Le texte noir du prologue lui finalement c'est bon » | question du texte « Et c'est ainsi que commence notre histoire… » **close, rien changé** | clos |
| D-37 | 01/11 23:33 | [C] [V] | « Pour tout le reste c'est bon » puis « Enfin tout le reste de tes rapports, pas de ce que je t'ai envoyé moi » | validation du lot #41 tel que rapporté par Claude ; ne valide **pas** ses propres demandes en cours (qu'il retestait) | clos. Lecture (supposée) : il valide les rapports, pas l'état fonctionnel |
| D-38 | 02/11 01:44 | [C] [V] | « Le bouton par défaut du son c'est bon » | décision [K] « défaut = volume ET son remis » **validée** | clos |
| D-39 | 02/11 01:44 | [C] [V] | « Ok pour la vitesse de transition » | défaut **x2** pour la vitesse des transitions validé (remplacé le 03/11 07 h 33 par **x1**, #48) | clos |
| D-40 | 02/11 01:44 | [C] | « Je test tout le reste et te fais part de mes nouveaux commentaires » | tout le reste du lot #42 (dont « Moyen = 2, Lent = 3 », « Masqué/Masquée ») n'est **pas** encore validé | ouvert |

## 5. Message de lundi 02/11, 02:12 à 02:14 (lot en cours, PR #43)

| ID | Heure | Source | Énoncé | Effet attendu | État au 02/11 sur `main` |
|---|---|---|---|---|---|
| D-30 | 02:12 | [C] | « Il y a beaucoup de scintillements de l'écran quand je passe de plein écran à fenêtré, finalement **supprime la fonction plein écran exclusif**, ne garde que plein écran et fenêtré et passe de l'un à l'autre avec **Alt+Entrée et F11**, et dans les options **reviens à un simple interrupteur** » | 2 états seulement ; interrupteur dans Affichage | **non fait** : `reglages.py:78` `MODES_FENETRE = (0, 1, 2)`, `fenetre.py:272` `mode=m` (exclusif). En cours dans le lot #43 |
| D-31 | 02:12 | [C] | « Supprime l'option pour la correction des bords des sprites, c'est exactement la correction que j'attendais donc **ne la mets pas en option, active la tout court** » | correction toujours active, sans réglage | **non fait** : `reglages.py:32,191` clé `correction_bords`, `pause.py:292` ligne de menu |
| D-32 | 02:12 | [C] | « Screen 2 : Le bouton pour reprendre la sauvegarde auto a disparue, je te rappelle aussi que ce bouton quand il n'y a pas de sauvegarde auto de disponible **il doit être grisé** » ; **02:13** : « Rectification : ce n'est pas le bouton pour la sauvegarde rapide, c'est celle de la sauvegarde auto, donc **je te laisse choisir quoi en faire** » | plaque « Sauvegarde automatique » présente et grisée si `data5.dat` absent ; latitude laissée à Claude | **contredit PR #41** (plaque cachée, « supposé identique à l'original ») ; lot #43 |
| D-33 | 02:12 | [C] | Screen 1 : « le dragon n'est pas bien orienté (**tu as réussi à lui donner 2 orientations différentes**) … le logo n'est pas parfaitement centré, et peut-être peux-tu améliorer le fond ? On voit trop le fait que le pattern soit répétitif » | dragon à une seule orientation, cadrage 1 pour 1 du mobile (D-11), logo centré, fond moins répétitif | **contredit** la note « ciel du titre tuilé pour remplir le 16/9 : garder tel quel, décision du 01/11 » (C-7) ; lot #43 |
| D-34 | 02:12 | [C] | « J'ai vu que la molette pouvait changer le zoom de la caméra, pas con, il faudrait que **clic molette + déplacement de la souris** permette de la faire tourner dans tous les sens, un **clic molette simple** remet la direction de la caméra en place, et **CTRL + clic molette** remet le zoom en place » | entrées souris supplémentaires (addition PC) | **non fait** (aucune occurrence de `MIDDLE` dans `dq4_pc/*.py` ; la molette seule est gérée, `fenetre.py:561-563`) ; lot #43 |
| D-42 | 02:12 | [C] | Screen 3 : « l'animation des coffres est pas dans le bon sens, les coffres ne sont pas toujours orientés vers le joueur il faut prendre ça en compte » | animation d'ouverture et orientation des coffres | lot #43 |
| D-43 | 02:12 | [C] | Screens 4 et 5 : « j'ai l'impression que le nom de Ragnar est trop bas, **t'en penses quoi ?** » | avis demandé (pas un ordre de modification) ; l'ancrage « middle » était « supposé ~1 px plus bas » (PR #41) | lot #43 |
| D-44 | 02:12 | [C] | « Passer du clavier à la souris rend la souris inutilisable pendant 1sec, c'est un peu perturbant » | suppression du délai ; le gel de souris existe depuis la PR #28 (`fenetre.py:870,1925-1927`, seuil de 6 px) | lot #43 |
| D-45 | 02:14 | [C] | « Mets aussi le menu **F1** en haut à droite par défaut » | position par défaut du bloc d'infos | lot #43 |
| D-14 | 02:12 | voir §2 | priorité du jeu sur les réglages | | lot #43 |
| D-16 | 02:12 | voir §2 | audit complet | | cet audit |

## 5b. Messages de lundi 02/11 de 02:27 à 02:38 [T] (lot en cours, PR #43)

Texte **intégral**, lu dans la transcription de la session principale (lignes 115, 130, 159, 177, 184 et 198 du JSONL). Aucun n'était dans le registre du prédécesseur. L'état « sur `main` » est celui du code à `08f5785` : **aucune de ces demandes n'y est encore**.

| ID | Heure | Source | Énoncé (intégral) | Effet attendu | État sur `main` |
|---|---|---|---|---|---|
| D-46 | 02:27 | [T] | « Pareil pour l'option de lissage des textures, mets oui par défaut et supprime l'option » | « Lissage des textures » toujours actif, ligne retirée du menu Affichage. « Pareil » = comme D-31 (correction des bords) | **non fait** : ligne de menu `pause.py:286`, clé `lissage` (`reglages.py:29`, défaut déjà True) |
| D-47 | 02:29 | [T] | « Et mets par défaut l'option pour le suivi de la caméra sur le joueur » | `camera_centree` à True par défaut. **Ici l'option n'est pas supprimée** (contrairement à D-46) | défaut du code **déjà True** (`reglages.py:28`) ; selon le brief, le `reglages.json` de la session contient False et la session principale le traite à la fusion (**non vérifié par moi**, fichier utilisateur non lu). La cause du False n'est pas établie |
| D-48 | 02:35 | [T] | « -Change "Vitesse de l'accélérateur" par "Multiplicateur de l'accélérateur" » | renommage (libellé et aides) | **non fait** : `pause.py:424-425` |
| D-49 | 02:35 | [T] | « -Ajoute des options pour accélerer les combats : vitesse x1, x2 et x3, accessible en combat et dans le menu des commandes sous les vitesses (juste sous toutes les lignes de l'accélérateur, ne doit pas pouvoir être accéléré via l'accélérateur) et mets plutôt des libellé : Normal > Rapide > Très rapide » | réglage de vitesse des combats à 3 niveaux (x1, x2, x3), libellés **Normal, Rapide, Très rapide**, joignable **en combat** et **dans Commandes**, sous les lignes de l'accélérateur ; l'accélérateur n'agit pas dessus | **non fait** : aucune clé de vitesse de combat dans `reglages.py` ; `_facteur_vitesse` renvoie 1,0 en combat (`fenetre.py:2405`). **Ambiguïtés** : « x1, x2, x3 » est le niveau, les libellés remplacent l'affichage ; « sous toutes les lignes de l'accélérateur » = sous « Touche d'accélérateur » et « Multiplicateur » |
| D-17 | 02:36 | [T] | « -Ajoutes aussi une fonctionnalité qui permet de garder en mémoire tout ce qui a été dit auparavant avec le nom ou une indication de qui nous l'a dit : nom du perso s'il en a un, message général, une femme dans une grotte, un soldat dans le chateau de Bastionne, un objet récupéré dans une jarre..... » | **historique des messages** : mémoriser chaque message avec son locuteur (nom du personnage, ou description : « message général », « une femme dans une grotte », « un soldat dans le château de Bastionne », « un objet récupéré dans une jarre ») | **non fait** : aucune fonction d'historique de dialogues dans `dq4_pc/*.py` (seul `l'historique des positions` des compagnons existe). **Fonctionnalité nouvelle ajoutée au portage**, sans équivalent confirmé dans le jeu mobile (non vérifié) |
| D-18 | 02:37 | [T] | « Le changement de la vitesse du combat change la vitesse des animations et les dialogues, mais pas la musique et les bruitages » | précision de D-49 : la vitesse de combat accélère **animations et dialogues** ; la **musique et les bruitages ne sont pas accélérés** | à implémenter avec D-49. Aucune trace de changement de hauteur ou de vitesse de lecture dans `son.py` (établi par grep) : un facteur appliqué à l'horloge du moteur seule suffit |
| D-19 | 02:38 | [T] | « Allez je te laisse travailler maintenant, tout doit être prit en compte depuis mon message envoyé à 2h12 » | tous les points de D-14, D-30 à D-49 sont à traiter ; l'audit (D-16) vient **après** les correctifs | cadre de la session |

Le travail de la session principale a été interrompu par Sylfried à 02:37:30 et 02:38:07 (« [Request interrupted by user] ») : D-18 et D-19 sont des précisions arrivées pendant l'exécution de D-49 et D-17.

## 6. Décisions rapportées par les PR, du 30/10 au 01/11 [R]

Chaque ligne vient d'un corps de PR de `dq4-portage` qui écrit « Demande(s) / Retour(s) / Remarque(s) de Sylfried ». Le sens est fiable, les mots non. Colonne « Aujourd'hui » : ce que dit le code ou la PR la plus récente.

### 6.1 Débuts de la visionneuse (30/10, dq4-pc)
| ID | Date | Énoncé rapporté | Effet | Aujourd'hui |
|---|---|---|---|---|
| D-50 | 30/10 | « on ne peut pas sortir du village », « il n'y a pas de son », « ça lag un peu », demande de plusieurs styles de lissage (issues #14, #17, #22, #40) | carte du monde, son, perf, styles F2 | faits ; styles « lissés » retirés ensuite (D-86) |
| D-51 | 30/10 | « dézommer la map », « mieux upscale TOUS les sprites 2D » (PR dq4-pc #70) | caméra orthographique de la carte du monde, EPX sur monstres | maintenu |
| D-52 | 30/10 | F1 : encadrement noir translucide pour les informations, affichage/masquage par F1 (PR dq4-pc #64) | cadre de l'aide | F1 = infos seulement depuis PR #15 ; position par défaut : voir D-45 |

### 6.2 Ergonomie, menu Échap/Pause, contrôles (31/10 - 01/11)
| ID | Date | Énoncé rapporté | Effet | Aujourd'hui |
|---|---|---|---|---|
| D-53 | 31/10 10:01 (PR #15) | « Échap ne doit plus quitter mais ouvrir un menu (volume, touches, shader, etc.), états instantanés comme sur émulateur, plus de raccourcis F2/F3/etc. (tout dans le menu), F1 = infos seulement, touches par défaut précises » | `pause.py`, `etats.py`, F2..F9 supprimées | maintenu |
| D-54 | 31/10 (PR #16) | en combat la boîte de dialogue descend à la position du menu de commandes ; textes de boutons centrés | | maintenu |
| D-55 | 31/10 14:59 (PR #18) | boutons de la version mobile (Carte, Commandes, Discussion) à l'écran, masquables, déplaçables à la grille ; options résolution 720p-4K, angle de caméra, vitesse de déplacement et de course, **sens de la molette inversé**, raccourcis d'états (1-9, Ctrl + chiffre) | `hud_mobile.py`, éditeur | maintenu |
| D-56 | 31/10 16:24 (PR #21, 6 captures) | volumes à 100 % par défaut avec bouton ↺ ; grande carte du monde | | maintenu |
| D-57 | 31/10 19:34 (PR #25) | menu Échap réorganisé **selon `Menu_Echap_DQ4_PC.xlsx`** (Pause > Jeu > Affichage/Son/Commandes ...) ; distance d'affichage x1/x2/x4/x8 ; molette toujours inversée ; zoom de la carte et infos F1 retirés des menus ; anticrénelage avec note rouge | | réorganisé de nouveau en #26/#27 : le fichier Excel **n'a jamais été régénéré** (G-143) |
| D-58 | 31/10 20:22 (PR #26) | **ZQSD** = déplacement ; **flèches** = caméra ; **Espace** = action ; Entrée = menu de commandes ; Retour arrière = annuler ; M = carte ; Maj = courir ; zoom 40-400 % | `reglages.py:6` | partiellement remplacé ensuite (D-60, D-61) |
| D-59 | 31/10 21:20 (PR #27) | menu noir opaque, curseur doré du jeu, barre de défilement ; « Distance caméra » 50-200 % ; « Effet de vignetage » ; shader « Aucun » ; « Taille des nombres de dégâts » **supprimée** | | maintenu |
| D-60 | 31/10 22:37 (PR #28) | Espace n'ouvre plus la discussion de groupe ; **Alt / Alt Gr** par défaut ; Échap = Annuler dans les menus du jeu | | maintenu (Alt au relâchement depuis #42) |
| D-61 | 31/10 22:37 (PR #28) puis 01/11 14:36 (PR #37) | course : « n'accélère plus que le héros ; PNJ, animations et scripts gardent leur rythme » (#28) **puis** « retour à la toute première version » : le facteur accélère l'**horloge du moteur** (héros, PNJ, animations) (#37) | `_facteur_vitesse` | **retournement** : le dernier état est « tout accélère » (C-4) |
| D-62 | 31/10 23:18 (PR #30, 13 demandes) | caméra centrée sur le héros par défaut ; menu États unique ; boîtes de combat à la taille des autres dialogues ; accélération de la caméra | | maintenu |
| D-63 | 01/11 00:15 (PR #32, 15 demandes) | « Centrer la caméra sur le joueur » ; suppression d'un état par Oui/Non ; **option de distance des compagnons supprimée** ; touche M en ville = liste des boutiques ; course en diagonale sur la carte du monde | | maintenu |
| D-64 | 01/11 01:22 (PR #33) | course sans dispersion de l'équipe ; rencontres calculées sur la distance ; M : plan, puis liste, puis fermer | | maintenu ; le mécanisme a été refait 4 fois (#33, #34, #35, #37) |
| D-65 | 01/11 11:30 (PR #34) | réponse de Claude à une question : les combats restent **aléatoires** (tirage tous les 16 pas) ; « Ombre : rien à faire (plus de problème) » | | clos |
| D-66 | 01/11 14:07 (PR #36) | croix tactile à l'écran, **en bas à droite**, masquable et redimensionnable ; boutons Carte/Commandes/Discussion **tout à gauche** | `hud_mobile.py` | maintenu |
| D-67 | 01/11 14:07-14:36 | « Pas de réglage bouton par bouton … « ça ira comme ça » » (citation du résumé de contexte, message d'origine non relu) | un seul réglage global `boutons` pour les 3 boutons (notes #42 : « décision de #37 ») | maintenu |
| D-68 | 01/11 14:36-14:39 (PR #37, #38) | bouton « Menu Échap » renommé « Menu Pause » ; « Quitter le jeu ? » devient « En êtes-vous sûr ? » | | « Menu Pause » retiré en #41 (D-76) |

### 6.3 Avant la partie et sauvegardes (01/11)
| ID | Date | Énoncé rapporté | Effet | Aujourd'hui |
|---|---|---|---|---|
| D-70 | 01/11 16:43 (PR #39) | « Deux demandes de Sylfried : (1) s'assurer que ce qui existe reflète le fonctionnement du jeu ; (2) ajouter tout ce qui précède le lancement d'une partie » | audit de fidélité ; logos, titre, menu de départ, nom, licence | maintenu |
| D-71 | 01/11 16:43 (PR #39) | « Sauv. cloud » retirée (sans objet sur PC ; l'original la retire pour Amazon) | `g_isAmazon` mis à 1 dans la mémoire du moteur | [K] ; remplacée en D-72 |
| D-72 | 01/11 18:20 (PR #40, « Retours de 18 h 02 ») | bouton « **Sauvegardes** » (export/import) à la place de « Sauv. cloud » ; rien n'est écrasé sans copie ; lecture jamais modifiée | `ecran_sauvegardes.py`, `sauvegardes.py` | maintenu |
| D-73 | 01/11 18:20 (PR #40) | menu de départ centré en hauteur dans le cadre noir ; licence avec une section en anglais en tête (projet non officiel) ; saisie du nom : flèche au clavier, cadre jaune à la souris | | cadre jaune remplacé par l'assombrissement (D-29b) |
| D-74 | 01/11 (notes #39 g) | « le ciel du titre est tuilé pour remplir le 16/9 (garder tel quel, **décision du 01/11**) » | | contredit par D-33 (C-7) |

### 6.4 Lot de 20 h 46 (21 points, 10 captures) et ce qu'il a retiré
| ID | Énoncé rapporté (PR #41) | Effet | Aujourd'hui |
|---|---|---|---|
| D-75 | logo du titre relevé (`TITRE_HAUT = 0,3`) ; **tous** les menus d'avant-partie centrés ; plein écran dès l'ouverture de la fenêtre | | maintenu |
| D-76 | « **Revenir à l'écran titre** » (ex-« Quitter le jeu ») ; le bouton « Paramètres » du menu en jeu ouvre le menu Pause ; la fenêtre d'origine « Config » et le bouton « Menu Pause » disparaissent | patch mémoire du moteur (`cmp w8,#7` -> `#4095` à 0x16ef28, `moteur.py:460-474`) | maintenu ; effet de bord : **la sauvegarde automatique est effacée au retour au titre** (comportement d'origine : `killbank(4,false)`) |
| D-77 | Commandes : plus de touches « Courir » / « Accélérer la caméra » ; section **Vitesses** ; une touche d'accélérateur | | maintenu |
| D-78 | page « Texte et défilement » (vitesse du texte, défilement des combats) ; Son en 5 catégories avec interrupteur et volume | **le jeu d'origine n'a pas l'option de vitesse du texte** : crochet de la visionneuse (`moteur.py:382-400`) | maintenu ; précisé en D-26 ; texte intégral de la demande : D-124, D-125 |
| D-79 | éditeur d'interface : 54 entrées en 11 groupes ; **18 entrées retirées** (lancement du jeu, `Config`, `MagicInfo`, `MonsterName`, `BattleHoppingNumber`...) ; fenêtre « Interface » déplaçable | | maintenu ; règle D-22 : ne rien supprimer sans demande ; texte intégral : D-126 à D-128 ; la liste des 18 est un choix de Claude (C-21) |
| D-80 | affichage : rendu hors écran (MSAA x2/x4/x8, suréchantillonnage, netteté, luminosité) ; FXAA/SMAA, scanlines, contraste, bloom écartés | `postfx.py` | maintenu |
| D-81 | boutiques : gauche/droite changent la quantité (1 à 9) ; sort Morph : effet devant le personnage | | non vérifié en jeu |
| D-82 | Sylfried demande : « assombrir ou flèche, sur mobile ? » -> réponse de Claude : seul l'**assombrissement du doigt appuyé** existe sur mobile ; **le cadre jaune (souris) et la flèche (clavier) sont une addition du portage PC** | | cadre jaune supprimé par D-29b ; flèche/curseur doré du clavier conservés |

### 6.5 Retours d'essai des premières PR (30-31/10), phrases de Sylfried citées entre guillemets dans les corps de PR [R]

Chaque PR introduit la phrase par « Retour d'essai : ». C'est Claude qui la recopie : le sens est fiable, la forme exacte non vérifiée. Ce sont des **retours de test** (bugs vus), pas des choix de conception : ils définissent seulement ce qui doit marcher.

| ID | PR / date (UTC) | Phrase citée | Effet | Aujourd'hui |
|---|---|---|---|---|
| D-140 | #3, 30/10 23:32 | « les portes, tonneaux, jarres etc. ne se mettent pas à jour quand on les utilise » | animations des objets de carte tirées des données du jeu (FCAN, FPMV, FSEQ/FSQD) | fait ; jarre / coffre avec message en capture non vérifié (G-068) ; coffres : sens à l'envers, orientation (D-42) |
| D-141 | #4, 30/10 23:38 | « il faut que les sprites de la map apparaissent dès qu'ils sont au moins en partie sur l'écran » ; « il manque certains sprites sur la map » | lieux visibles dans toute la zone 16/9 de la carte du monde ; genres 19 et 20 ajoutés | fait ; genre 18 non dessiné (G-034) |
| D-142 | #5, 30/10 23:45 | « quand je pointe ma souris sur un bouton dans un menu il faut changer l'UI comme quand je sélectionne par les flèches » | survol de la souris dans les menus | fait ; **la règle visuelle a changé depuis** (D-29b : assombrissement, plus de cadre épais ni de flèche) |
| D-143 | #6, 31/10 00:03 | « les textes des menus sont toujours décalés par rapport à la taille du bouton » ; « certains boutons sont sombres (menu principal) » ; « tu peux peut-être augmenter légèrement l'UI partout » | textes des boutons, boutons sombres, interface agrandie | fait ; refait en #41 (police SE-GARRIR, D-132, D-133) |
| D-144 | #7, 31/10 00:21 | « il y a un flash de la mauvaise map au début du combat, il faut bien mettre l'animation du début de combat » | effet de morceaux d'écran au début du combat, plus de flash | fait ; clignotements : traités sans cause unique (G-056) |
| D-145 | #8, 31/10 00:32 | « penses aussi à mettre tous les bruitages (début du combat, sortie d'une ville, escaliers, portes, jarres, attaques...) » | bruitages commandés par le moteur (paquets 35 / 36 / 37) rejoués ; Unity ne joue lui-même que le bruitage 300 | fait ; **le moteur ne demande aucun bruitage au début d'un combat** (seule la musique change) ; la PR demande à Sylfried de signaler tout bruitage manquant (G-122) |
| D-146 | #9, 31/10 00:44 | « il n'y a pas les animations sur l'eau » | carte du monde : eau et côtes animées | fait ; eau des villes et débordement des vagues des grottes : voir G-051, G-054 |
| D-147 | #10, 31/10 01:04 | « ça a pris pas mal de temps pour entrer dans un puits et changer de map » ; « il y a parfois des clignotements d'écran » | cache préparé en arrière-plan, fondus attendus par le moteur | fait ; première préparation ~1 min 30 à 2 min (G-022, G-127) |
| D-148 | #17, 31/10 11:44 | « Il manque certaines animations sur la carte, notamment l'eau (grotte) » | rejeu des animations qui tournent sans ordre du moteur (eau, lampes, palettes) | fait ; SRA, FEAN, FEMV non rejoués (G-052, G-053) |

## 7. Choix de Claude non formulés par Sylfried, à valider ou validés [K]

| ID | Date | Choix | Statut |
|---|---|---|---|
| D-85 | 31/10 (PR #14) | **pixel perfect par défaut** (`mode_sprites` 4, `reglages.py:26`) après un retour « décor bizarre » | non validé explicitement |
| D-86 | 01/11 (PR #41) | retrait des shaders « Régions lissées » et « Bicubique » (« ils ne faisaient que flouter », bicubique -27 % de netteté) | **demandé indirectement** : D-131 (« revois aussi les shaders car certains rendent juste les pixels plus flous encore ») ; le choix des deux shaders retirés est de Claude, non validé explicitement ; en tension avec le souhait du 30/10 de « plusieurs styles de lissage » (D-50), voir C-8 |
| D-87 | 01/11 (PR #41) | patch mémoire du moteur pour « Paramètres » (D-76), constantes `drawSymbol` à 1600 px (PR #4), `g_isAmazon`, crochet de vitesse du texte | non validé ; touche la règle « le moteur ne se modifie pas » (C-6) |
| D-88 | 01/11 (PR #42) | « Moyen » = valeur d'origine 2, « Lent » = 3 ; mapping `defilement_combat` 0/2/3/4 | **à valider** (liste de Claude) |
| D-89 | 01/11 (PR #42) | libellés « Masqué » (boutons) / « Masquée » (croix, fenêtres) | **à valider** (liste de Claude), voir D-29 |
| D-90 | 01/11 (PR #42) | défaut du bouton Son = volume ET son remis | **validé** (D-38) |
| D-91 | 01/11 (PR #42) | vitesse de transition x2 par défaut | **validé** (D-39) ; **remplacé en #48 : x1 par défaut** (demande de Sylfried, 03/11 07 h 33) |
| D-92 | 01/11 (PR #41) | plaque « Sauvegarde automatique » cachée quand vide | **annulé** (D-32) |
| D-93 | 30/10 (PR #2) | suppression de la silhouette du personnage caché par le décor (« absente du jeu d'origine ») | non validé ; l'issue dq4-pc #6 (toits transparents) reste ouverte |
| D-94 | 01/11 (PR #39) | clavier du nom de saisie = disposition du portage (l'originale n'a pas été retrouvée) | non validé, limite connue |
| D-95 | 31/10 (PR #27) | curseur doré qui oscille (« inventé ») | **caduc** : le curseur est fixe dans le code courant (`pause.py:161-167`, `dx = 0.0`) ; flèche gardée dans l'historique à la demande de Sylfried (#48, 03/11) |

## 8. Ce que Sylfried refuse de voir (retours négatifs → exigence)

| Quand | Rejet | Source |
|---|---|---|
| 30/10 | sprites flous, « très mauvaise qualité » ; sprites « à l'envers » ; monstres en l'air ; bande noire à l'horizon des combats ; lag | issues #33, #40 ; dq4-pc PR #48, #50, #51 |
| 31/10 | flash de la mauvaise map au début du combat ; animations d'eau absentes ; lenteur au passage du puits ; clignotements ; « aura » autour de Ragnar | PR portage #7, #9, #10, #23, #24 |
| 31/10 | énorme zoom au lancement ; boutons sombres ; textes décalés | PR #6, #25 |
| 01/11 | « texte noir du prologue » (finalement accepté) ; boîte violette ; cadre jaune | PR #40-#42 |
| 01/11 20:46 | shaders qui rendent « les pixels plus flous encore » ; cadre jaune et flèche (ajouts PC) ; textes qui dépassent (toléré, D-133) | D-131, D-82, D-133 |
| 02/11 02:12 | sauvegarde auto absente au lieu d'être grisée ; dragon à deux orientations ; fond répétitif | D-32, D-33 |
| 01/11 23:24 | texte « Chargement de la sauvegarde » ; mot « Masqué » pour la croix ; sprites aplatis | D-20, D-29, D-31 |
| 02/11 02:12 | dragon à deux orientations ; fond répétitif ; scintillements au changement fenêtré/plein écran ; souris bloquée 1 s ; coffres à l'envers | D-30 à D-44 |

## 9. Récapitulatif par type

- **Fonctionnalités retirées (par ou pour Sylfried)** : plein écran exclusif (D-30, à retirer) ; option « Correction des bords » (D-31, à retirer : la correction reste, toujours active) ; option « Lissage des textures » (D-46, à retirer : lissage toujours actif) ; texte de chargement (D-20) ; encadré jaune (D-29b) ; sections des pages Son et Texte (D-23, D-26) ; « Défilement automatique » (D-26) ; « Taille des nombres de dégâts » (D-59) ; option de distance des compagnons (D-63) ; « Sauv. cloud » (D-71, [K] puis remplacé par D-72) ; 18 entrées de l'éditeur d'interface (D-127, liste choisie par Claude, C-21). Shaders « Régions lissées » et « Bicubique » (D-131 : demandé de revoir, retrait par Claude).
- **Modifiées** : plein écran 3 modes puis 2 (D-21 -> D-30) ; vitesses curseur -> x1..x4 (D-29b) ; course : héros seul -> horloge entière (D-61) ; menu de départ centré (D-73, D-75) ; « Vitesse de l'accélérateur » -> « Multiplicateur de l'accélérateur » (D-48).
- **Ajouts voulus par Sylfried au-delà du jeu mobile** : bouton Sauvegardes export / import (D-72), clic molette (D-34), vitesse des combats x1-x3 (D-49), historique des messages (D-17), position de F1 (D-45), options d'affichage (D-130), fenêtre « Interface » déplaçable (D-128). Le principe « le jeu d'origine fait foi » (D-12) ne s'oppose donc pas aux ajouts qu'il demande lui-même ; il s'applique à tout ce que la visionneuse **remplace**.
- **Priorité du jeu sur les réglages** : D-102 (caméra, fait), D-14 (« valable pour tout », à faire pour la vitesse du texte et à inventorier ailleurs, C-14).
- **Refusées / écartées** : FXAA, SMAA, scanlines, bloom, limiteur d'images ([K], D-130) ; réglage bouton par bouton (D-67) ; réseau / cloud (D-71).
- **Reportées** : piste Unity (D-09) ; DQ5/DQ6 (issue #19, intention confirmée par la mention de Nimzo, D-14) ; packaging et CI (issues #18, #21 : jamais priorisées).
- **Hors du périmètre du portage (décision de Sylfried)** : les textes français trop longs qui débordent (D-133) : ils seront corrigés dans le projet de traduction ; ne pas les compter comme des bugs.
- **Pas de décision trouvée** : manette (issue #8, rien dit par Sylfried depuis l'issue de départ) ; ratios autres que 16/9 ; casino, banque, églises (D-16 : jamais évoqués, c'est précisément l'objet de l'audit).

## 10. Contradictions entre décisions et état actuel de `main`

| ID | Contradiction | Établi / supposé |
|---|---|---|
| C-1 | D-30 (retirer le plein écran exclusif) vs `MODES_FENETRE = (0, 1, 2)` | **établi** (`reglages.py:78`, `fenetre.py:272`). Correction attendue dans le lot #43 |
| C-2 | D-31 (correction des bords toujours active, sans option) vs clé `correction_bords` et ligne de menu | **établi** (`reglages.py:32`, `pause.py:292`) |
| C-3 | D-32 (plaque auto grisée) vs plaque **cachée** (PR #41) | **établi** (PR #41 : « masquage de la plaque automatique (supposé identique à l'original) ») |
| C-4 | D-61 : PR #28 « les PNJ gardent leur rythme » vs PR #37 « tout accélère » | **établi** (corps des PR). Je n'ai pas trouvé de message de Sylfried tranchant entre les deux ; **supposé** : la dernière version suit son retour de 15 h 25 |
| C-5 | D-82 : la PR #41 conserve « cadre jaune (souris) + flèche (clavier) » comme addition PC, D-29b l'ôte le soir même | **établi** ; l'écart vient du principe D-11/D-12 |
| C-6 | D-12 « le moteur d'origine ne se modifie pas » vs **modifications en mémoire** : constantes `drawSymbol` (PR #4), `cmp w8,#7` à 0x16ef28 (`moteur.py:460-474`, demandé par D-123), `g_isAmazon`, crochets de vitesse du texte (`moteur.py:382-407`, demandé par D-124) | **établi** pour l'existence ; le fichier `libdq4core.so` n'est pas modifié, mais son comportement l'est. Deux de ces modifications sont **demandées** par Sylfried (D-123, D-124) ; `drawSymbol` et `g_isAmazon` sont des choix de Claude [K]. À qualifier avec lui (« fait foi » vs « modifié ») |
| C-7 | D-74 « ciel du titre tuilé : garder tel quel » vs D-33 « le pattern est trop répétitif » | **établi** |
| C-8 | D-86 (retrait de « Régions lissées » et « Bicubique ») vs demande du 30/10 de « plusieurs styles de lissage » (D-50) | **nuancé à la reprise** : le 01/11 à 20 h 46 Sylfried a écrit « revois aussi les shaders car certains rendent juste les pixels plus flous encore » (D-131). Le retrait de ces deux-là est la réponse de Claude (bicubique mesuré à -27 % de netteté), jamais validée explicitement. Pas de contradiction avec ses mots ; risque de contradiction avec D-50 |
| C-9 | D-93 (silhouette supprimée car absente de l'original) vs issue dq4-pc #6 toujours ouverte | **établi** |
| C-10 | D-14 (le jeu prend le dessus) vs `defilement_force` limité aux combats | **établi** pour l'état actuel ; le texte des dialogues du terrain est géré par un crochet distinct (`moteur.py:382-400`) : à auditer |
| C-11 | la mémoire dit « dépôt privé dq4-pc » ; les docs du Projet (`depot-github-dq4-pc.md`) décrivent encore `dq4-pc` comme dépôt actif alors que le travail est dans `dq4-portage` depuis le 30/10 23:06 UTC | **établi** (documents périmés) |
| C-12 | `docs/workflow.md` / README décrivent un suivi par issues ; `dq4-portage` n'en a aucune | **établi** |
| C-13 | D-133 (« les textes qui dépassent n'est pas un souci ») vs tout rapport qui classerait un débordement de texte français comme bug du portage | **établi** pour la décision ; l'alignement des écarts sur le mobile reste à faire (G-023, pas de capture). Règle d'audit : ne pas compter le débordement du texte lui-même |
| C-14 | D-14 « valable pour tout » : seul un précédent est codé (D-102, caméra `fenetre.py:1171-1172` depuis #47). Les autres réglages que le jeu pourrait imposer (vitesse du texte, vitesse de marche, distance de caméra, volumes d'`OptionStatus`, etc.) ne sont pas inventoriés | **établi** pour le précédent ; **non vérifié** pour le reste (délégué à l'agent couverture) |
| C-15 | D-18 (le changement de vitesse du combat ne change pas la musique ni les bruitages) vs l'accélérateur actuel | pas de contradiction : aucune accélération du son dans `son.py` (grep). À conserver tel quel quand D-49 sera écrit |
| C-16 | D-26 (« Messages en combat » : Rapide, Moyen, Lent, Manuel) vs D-49 (vitesse du combat : Normal, Rapide, Très rapide) | deux réglages de sens différent avec un libellé commun (« Rapide ») : confusion possible. **Supposé** ; à signaler à Sylfried |
| C-17 | D-21 (23 h 24 : 3 modes) puis D-30 (02 h 12 : 2 modes) | revirement de Sylfried lui-même en moins de 3 h, motivé par les scintillements. D-28 (F11 / Alt+Entrée) est conservé. Ne pas réintroduire un mode exclusif |
| C-18 | PR #42 : l'option « Correction des bords » est une création de Claude (« (nouveau) » dans l'ordre D-22) ; D-29e n'en demandait pas. Sylfried la juge « exactement » ce qu'il attendait mais ne veut pas d'option (D-31) | **établi** (PR #42). Origine [K] |
| C-19 | D-47 : le défaut du code était déjà True alors que Sylfried demandait de le mettre « par défaut » | **clos par #47** : l'option est supprimée (caméra toujours centrée tant que le joueur l'a). L'écart venait probablement d'un `reglages.json` enregistré à False (jamais lu) |
| C-20 | D-123 (le bouton « Paramètres » ouvre la Pause) vs « Taille de la croix » et volumes d'origine devenus injoignables (G-102) | **établi**. Conséquence de sa demande ; la taille de la croix existe côté PC (D-66) |
| C-21 | D-127 : il cite un exemple (« Aperçu d'objet ») ; Claude retire **18** entrées, dont `Config`, `MagicInfo`, `MonsterName`, `BattleHoppingNumber`. D-22 (23 h 24) dit ensuite de ne jamais supprimer un bouton non cité | **établi** (PR #41). La liste des 18 est le choix de Claude, jamais itemisée à Sylfried |

## 11. Éléments utiles à la mémoire (à décider par la session principale ; je n'écris pas la mémoire)

Appris dans les documents, à confirmer avec Sylfried avant de les mémoriser. Entre crochets : la source. Aucun n'est déjà dans la mémoire (qui s'arrête au 30/10 22:50 pour le portage).

1. [T/C, 02/11] « Le jeu prend le dessus sur la règle des paramètres du joueur quand un script change la valeur, valable pour tout » (D-14), précédent : la caméra (D-102).
2. [C, 02/11 02:12] Plein écran exclusif supprimé ; F11 et Alt+Entrée alternent plein écran / fenêtré, interrupteur simple dans les options (D-30).
3. [C/T, 02/11] Ce qui doit être toujours actif ne devient pas une option : correction des bords (D-31), lissage des textures (D-46).
4. [C, 02/11 02:14] F1 en haut à droite par défaut (D-45).
5. [C, 01/11 23:24] Règle « ne jamais supprimer un bouton non cité, le placer de façon cohérente » (D-22).
6. [C, 02/11 01:42] Un bug décrit via une situation précise se règle globalement (D-13).
7. [C, 02/11] Plaque « Sauvegarde automatique » toujours présente et grisée si indisponible ; il laisse le choix du comportement à Claude (D-32).
8. [C, 01/11 23:24] Si le mobile montre « l'envers du décor » ou suit l'événement en entier, la version PC doit faire pareil (D-29d) ; zone portrait 9:16 centrale = vue du téléphone (D-11).
9. [C, 01/11 20:46] Les textes français qui débordent sont l'affaire du projet de traduction, pas du portage (D-133).
10. [T, 02/11 02:35-02:37] Vitesse du combat : 3 niveaux (x1, x2, x3 ; Normal, Rapide, Très rapide), n'accélère ni musique ni bruitages (D-49, D-18) ; « Multiplicateur de l'accélérateur » (D-48).
11. [T, 02/11 02:36] Historique des messages avec l'indication de qui parle (D-17).
12. [T, 02/11 02:29] Caméra centrée sur le joueur par défaut (D-47) ; **#47 : option supprimée, caméra toujours centrée**.
13. [C/T, 01-02/11] Sylfried délègue souvent le détail (« je te laisse choisir », « ne le fais que si c'est pertinent », D-32, D-130) : Claude décide, puis le dit.
14. [T, 02/11 02:38] « Tout doit être pris en compte depuis mon message de 2h12 » : l'audit vient après les correctifs (D-19).
15. [observation] Fuseau de Sylfried : Europe/Paris (UTC+1), établi par la transcription elle-même.
