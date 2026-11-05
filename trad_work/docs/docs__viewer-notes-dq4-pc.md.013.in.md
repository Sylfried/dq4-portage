### Non vérifié (#47)
Windows et vrai GPU ; ressenti de la caméra des escaliers, de la cascade et des fondus raccourcis, de l'historique continu (molette, glisser, `glScissor` à une échelle ≠ 100 %) ; plein écran à deux moniteurs ; combats à plusieurs alliés (bouton de vitesse) ; `reglages.json` réel migré (`interface_v`) ; audio réel ; caméra 132 (boss final) ; mobile (aucune capture).

### Outillage de test (#47)
Nouveaux tests : `test_lignes_inactives`, `test_titre_centrage` (rendu réel, `DQ_UICACHE`), `test_bouton_vitesse`, `test_camera_combat`, `test_coffre_ennemi`, `test_bruitage_transition`. `tools/session_flow/engine_slot.sh` limite à deux le nombre d'exécutions du moteur en parallèle ; `pr.sh` lit l'URL de session dans `DQ_SESSION`. Les tests de magie et d'historique de combat attendent les sauvegardes **d'origine du mobile** (emplacement 1 : Ragnar à Strattbourg), pas celles que Sylfried a rejouées depuis.

## Avance #48 : retours de 07 h 33 (03/11/2026)

Quatre retours, traités un par un (petit lot, sans sous-agents). Légende : **Établi** (lu dans le code / mesuré / testé), **Supposé**, **Non vérifié**.

### Sorts sans effet : « Mais il ne se passe rien. »
- Demande : si un message officiel existe, l'utiliser plutôt que « Mais rien ne se passe. ». Il existe : « Mais il ne se passe rien. » est le message qu'Évac' hors donjon affiche déjà (id 0xc3d6d, texte du patch FR). `Moteur._crochets_magie` l'écrit désormais (`MSG_IL_NE_SE_PASSE_RIEN`) à la place de 0xc3d6b pour un sort qui coûte des PM sans les faire baisser (soins à PV pleins, Multisoin en pleine forme : un seul message).
- **Inchangés** : les messages d'échec propres au jeu, qui disent encore « Mais rien ne se passe. » (Rappel sur un vivant, Antipoison sans poison, Sifflet) ; ce sont les textes du jeu, pas un ajout de la visionneuse. Évac' garde « Mais il ne se passe rien. ».
- Établi : l'id lu en mémoire pendant le lancement d'Évac' (`UseActionParam + MAGIE_RESULTAT`) est 0xc3d6d ; le champ « échec » de la table des actions pour cette action (0xaae7e) n'est PAS le message affiché (essai à vide : « ERROR 700030 »). Test : `test_magie_liste` (29, avec les sauvegardes d'origine du mobile). **Bruitages : voir l'Avance #150** (le bruitage de soin est coupé quand le sort n'a aucun effet).

### Vitesse de transition : x1 par défaut
- `reglages.DEFAUT['vitesse_fondu']` passe de 2,0 à **1,0** (la cascade d'entrée en combat dure de nouveau 1,9 s et les fondus 30 images, comme le jeu). Les crans x1 à x4 restent au choix.
- **Migration** (nouvelle clé `vitesse_fondu_v` = 2) : un `reglages.json` enregistré avant (sans cette clé) dont la vitesse vaut encore l'ancien défaut x2 passe à x1 **une seule fois** ; tout autre cran est conservé ; ensuite la clé est enregistrée et un x2 choisi par Sylfried reste x2. **Limite** : on ne peut pas distinguer un x2 voulu d'un x2 resté par défaut ; si Sylfried l'avait choisi exprès, il doit le remettre une fois.
- Tests : `test_reglages_son_texte` (+1, `test_vitesse_de_transition_par_defaut_x1`), `test_reglages_interface` (clé classée hors interface).

### Historique : ↑ ↓ message par message, sans grisé
- **Clavier** : ↑ / ↓ (et la répétition de la touche maintenue) choisissent le message précédent / suivant, un à la fois ; ils ne font plus défiler la liste. La vue ne défile que pour montrer **en entier** le message choisi, quand il est coupé par un bord de la fenêtre ou hors de la fenêtre, et **du minimum** : son bord rejoint le bord de la fenêtre (`ui_historique.decalage_pour_voir`, `etendue`, `elements_visibles` : fonctions pures testées). Le premier et le dernier message se montrent avec la marge de la liste (on arrive tout en haut / tout en bas). Un message plus haut que la fenêtre : son début en haut. PgHaut / PgBas défilent d'une page (le message choisi devient le plus proche message entièrement visible) ; Début / Fin choisissent le premier / dernier message.
- **Message choisi** : `VueHistorique.sel` ; plus de « repère » (`element_au_repere`, `hauteur_repere`, `REPERE_BAS/HAUT`, `pmax`, `sel_manuel` supprimés). Au clavier, un clic ou la touche Entrée agissent sur lui. À la souris, le message **survolé** devient le message choisi (image par image, y compris pendant la molette) ; la molette, la barre et le glissement ne changent pas le choix. Si le message choisi n'est plus du tout dans la fenêtre (molette), le premier appui sur ↑ ↓ le remplace par le plus proche message visible, sans avancer d'un rang de plus.
- **Plus de grisé** (dérogation à la règle générale des menus, demandée pour l'historique seulement) : la boîte n'est plus éclaircie (rectangle blanc translucide supprimé de `_boite_dessin`) au survol ni au choix ; seule la **petite flèche dorée** marque le message choisi, au clavier comme à la souris. Les onglets, la case « Favoris seulement » et l'étoile gardent leur surbrillance habituelle.
- Texte d'aide : « Haut / Bas : message précédent / suivant », « Molette : défiler ».
- Tests : `test_historique_messages` (99 ; 8 tests réécrits ou nouveaux : message par message, défilement minimal, messages coupés en haut / en bas, toutes les longueurs de liste, molette puis clavier, aucun grisé). Captures du vrai dessin (harnais hors dépôt) : flèche seule, pas de grisé, message choisi collé au bord haut après sept ↑.
- **Non vérifié** : ressenti du défilement instantané (pas d'animation) ; répétition de la touche maintenue avec le vrai `Pause.maj` (seulement l'appel, simulé) ; Windows / GPU.

### À trancher par Sylfried (#48) (**tranché le 03/11 à 15 h 50 : `decisions.md` § 5d, D-163 à D-190**)
1. **x1 par défaut** : si tu avais choisi x2 toi-même, la migration l'a ramené à x1 une fois ; le remettre une fois suffit.
2. **Défilement de l'historique au clavier** : instantané (le bord du message rejoint le bord de la fenêtre). Un défilement doux (quelques images) est possible si tu le préfères.
3. **PgHaut / PgBas** dans l'historique : défilent d'une page et déplacent le choix sur le message entièrement visible le plus proche ; veux-tu plutôt qu'ils sautent de N messages ?

### Non vérifié (#48)
Windows et vrai GPU ; le texte exact « Mais il ne se passe rien. » est celui du patch FR lu en jeu (moteur réel), pas comparé à un mobile ; `reglages.json` réel migré (`vitesse_fondu_v`) ; ressenti de l'historique.

## Avance #49 et #50 : docs, CI et décisions du 03/11/2026 (docs seulement)

Aucun changement de code dans `dq4_pc/` ni dans les tests. Relecture du rapport « ce qu'il reste » avec Sylfried (13 h 45 à 14 h 19, il ne pouvait pas tester). Ce qu'il a dit sert à **structurer le projet et le reste à faire** ; rien n'est lancé.

### Fait
- **#49** : README, `docs/workflow.md`, notes techniques (section « Écritures et crochets en mémoire du moteur » : 27 crochets vérifiés à l'exécution, 18 sites qui écrivent, S10 sorts du menu Magie, S11 décompte du bruitage de sortie), fiches d'audit périmées (caméra, curseur doré, roulis), CI `.github/workflows/ci.yml` (compilation + fichiers interdits ; **verte sur GitHub** pour la PR #49).
- **#50** : le dépôt `dq4-pc` **n'existe plus** (Sylfried) : références corrigées partout (README, workflow, reprise, audit) ; l'état de ses issues au 02/11 est conservé dans `docs/audit/github_issues.md`. Décisions du 03/11 enregistrées (`docs/audit/decisions.md` § 5c, D-149 à D-160 ; `remaining_work_report.md`, « Réponses de Sylfried » et « Cap fixé » ; `known_gaps.md`). Document du Projet `depot-github-dq4-pc.md` remplacé par `depot-github-dq4-portage.md`.

### Décisions de Sylfried (03/11)
- **Toits** : laissés tels quels, « c'est le fonctionnement du mobile ». **Éditeur d'interface** : supprimer tout ce qui n'a aucun élément à modifier (les 18 entrées retirées suivent ce critère). **« Masqué / Masquée »** : validés. **`Menu_Echap_DQ4_PC.xlsx`** : plus d'actualité.
- **Manette** : prévue pour la suite. **Licence d'Unicorn** : vérification acceptée (à faire).
- **Tous les boutons de l'interface accessibles au clavier** (exigence). **Bruitage au clavier** : seulement dans les mêmes situations qu'au toucher (jamais ajouté de force ; par exemple un bip par caractère du nom *si* le toucher en joue un).
- **Sauvegardes du chapitre 2** : il les fournira dès que possible.
- **Tout tenir à jour** (CI, documents, `.md`) à chaque PR.

### Reste à faire (structuré, rien de lancé)
1. Validation Windows / vrai GPU. 2. Clavier complet : inventaire des boutons qui n'y sont pas (cas connu : « Sauvegarde rapide » de l'écran Divers, G-096), puis correction, avec la règle du bruitage (G-173). 3. Manette. 4. Chapitre 2 (jouer ses cartes, PNJ et menus dès les sauvegardes). 5. Licence d'Unicorn. 6. Paquets du moteur (6, 30, effets d'écran 3 / 5 / 6) et petits oublis.

### Suivi par issues (03/11/2026, PR #89)
Sylfried (14 h 25) : « je veux bien des issues sur le reste à faire ». **38 issues créées dans `dq4-portage` (#51 à #88)**, en 5 jalons (1 Validation Windows #51-#58, 2 Clavier complet et manette #59-#61, 3 Chapitre 2 et services #62-#65, 4 Moteur et finitions #66-#85 dont 11 bugs, 5 Distribution et extensions #86-#88) ; nouvelles étiquettes `type:feature`, `type:bug`, `type:recherche`, `test-windows`, `priorité:haute`, `bloqué`. Pas d'issues rétroactives pour le travail déjà fait (choix de Claude : les 50 PR « Avance #N » et `docs/history.md` font foi). Issues et PR partagent la même numérotation : `pr.sh` prend le plus grand numéro + 1, donc la PR suivante est #89 (la série « Avance #N » saute de #50 à #89). Détail : `docs/workflow.md`, `docs/audit/remaining_work_report.md` (« Suivi dans GitHub »).

### À trancher par Sylfried (#50) (**tranché le 03/11 à 15 h 50 : `decisions.md` § 5d, D-163 à D-190**)
1. ~~**Issues dans `dq4-portage` ?**~~ **Réglé le 03/11 à 14 h 25** : oui, pour le reste à faire (voir ci-dessus).
2. **Branches fusionnées** : supprimer les 56 branches distantes déjà fusionnées (décision 2 de l'audit) ? Il a demandé si cela change quelque chose : non (tout est dans `main`, les PR restent consultables) ; **non fait** sans un « oui » explicite.

### Non vérifié (#50)
Tout ce qui a été vu l'a été sous Linux (Mesa) ; la CI n'a tourné qu'une fois (verte), sans essai d'un fichier interdit réel (le motif a été essayé en local).

## Avance #100 : lecture du reste à faire et ménage (03/11/2026, docs seulement)

Aucun changement de code dans `dq4_pc/` ni dans les tests (phase gestion de projet, D-189). Sylfried a lu la liste « tout ce qu'il reste à faire » (15 h 50) et répondu point par point. Légende : **Établi**, **Supposé**, **Non vérifié**.

### Fait
- **Branches** : les 57 branches fusionnées ont été supprimées **par Sylfried** (le proxy de la session refusait toute écriture sur les branches, 403) et la suppression automatique est activée (D-163). `main` est la seule branche.
- **Issues** : 7 fermées (#51, #54, #55, #57, #78, #82, #86), 10 créées (#90 à #99), 11 réécrites ou complétées (#52, #53, #56, #58 à #62, #80, #83, #88) et commentaires sur #75 et #87 ; nouvelles étiquettes `à décider` et `priorité:basse`. Bilan : 48 issues, 41 ouvertes.
- **Décisions** : D-163 à D-190 (`decisions.md` § 5d). L'exigence « tous les boutons au clavier » (D-155) est **suspendue** (D-165) : « à creuser », #59.
- **Lacunes** : 86 des 161 lignes de `known_gaps.md` retriées (63 closes, 25 traitées, 71 ouvertes ensuite). La ligne G-039c (« pièces `MAP_DIFF` non reproduites ») était périmée : les pièces sont reproduites (`_plan_monde_fenetre`).
- **Licence d'Unicorn** (#86) : à traiter comme GPL v2 (`docs/licenses.md`) ; choix à faire avant le `.exe` (#87).
- **Plan de test du chapitre 2** : `docs/audit/chapter2_test_plan.md` (D-168).
- **Ménage** : briefs des lots déplacés dans `docs/archives/briefs/` ; modèles d'issue alignés sur le format des issues (Contexte, Critères, Références) et nouveau modèle « Test sur Windows » ; `history.md` complété jusqu'à #100 ; `resume.md` §6 réécrit ; pointeurs « Reste à faire » corrigés ; README à jour.

### Validé par Sylfried sur Windows (établi par lui)
Premier lancement du `.bat` ; sauvegardes (église, automatiques, hors églises, création et suppression de journal) ; plein écran (F11, Alt + Entrée) et autres ratios ; comparaison au mobile (tailles de texte, placements, croix, plume, dragon du titre) ; combat de boss du chapitre 1, groupes, Morph de la cinématique, game over, nouvelle partie sans relancer ; historique après combats ; teinte jour / nuit (carte et villes) ; fenêtre « Interface » glissée à la souris ; murs de `dbout` et vagues d'eau des grottes résolus ; ordre de tracé des monstres, fenêtres de combat, escaliers : « tout bon ».

### À trancher par Sylfried (#100) (**tranché le 03/11 à 16 h 47 : voir « Avance #102 » ci-dessous**)
1. **Licence** : (a) rester sur « scripts + `.bat` qui télécharge Unicorn », (b) publier le portage sous GPL v2 pour embarquer Unicorn dans un `.exe`, (c) un autre émulateur ; et choisir une licence pour le code du portage (`docs/licenses.md`, #87).
2. **Accélérateur et jingle** (#96) : lecture retenue (supposé) = pendant un jingle, la touche d'accélérateur est neutre, sauf pour une transition de carte à carte. **Remplacé le 03/11 à 16 h 47** (D-197) : plus d'accélérateur hors combat, transitions de porte à x4 fixe (#101) ; #96 fermée.
3. **Espace et discussion de groupe** : « Espace ne fait plus les discussions de groupe » est lu comme « le cas limite n'arrive plus » ; si c'est la discussion de groupe qui ne s'ouvre plus du tout avec Espace, le dire.
4. **Petits restes** (#99) : mode « menus simples » (garder, simplifier, retirer ?), bandeau « Prologue » (le cadre doré à fond bleu s'affiche-t-il ?), « sort en trop » (est-ce la rangée fantôme supprimée en #45 ?), coffres (sens d'ouverture).

### Non vérifié (#100)
Rien n'a été exécuté côté outil. Les affirmations sur le code de ce paragraphe (pièces `MAP_DIFF` reproduites, rangée fantôme de la liste des sorts supprimée en #45) sont lues dans le code et les notes, non revues à l'écran. Licence : textes publics lus (COPYING, métadonnées), pas d'avis juridique. Les lectures « à confirmer » ci-dessus sont des interprétations de phrases de Sylfried.

## Avance #102 : réponses de 16 h 47 (03/11/2026, docs seulement)

### Fait
- **Issues** : #101 créée (transitions à x4) ; #53, #87, #92, #99 réécrites ; #96 fermée (remplacée par #101) ; commentaire sur #75. Bilan : 49 issues (#51 à #99 et #101), 41 ouvertes, 8 fermées (#51, #54, #55, #57, #78, #82, #86, #96).
- **Décisions** : D-191 à D-200 (`decisions.md` § 5e) ; D-180, D-182, D-188 et D-190 annotées.
- **Lacunes** : G-008, G-012, G-015, G-039c, G-058, G-108, G-162, G-205, G-212, G-213 mises à jour.
- **Licences** : `docs/licenses.md` complété (option « `.exe` launcher », « Faut-il un fichier `LICENSE` ? ») ; **aucun fichier `LICENSE` créé** (pas nécessaire aujourd'hui, D-196).
- **Plan de test du chapitre 2** : caméra des attaques (ennemis du chapitre 1 d'abord), coffres cochés, « sort en trop » à vérifier.
- Aucun fichier de `dq4_pc/` ni de `tools/` modifié.

### Validé par Sylfried sur Windows (16 h 47, établi par lui)
Pièces `MAP_DIFF` du plan du monde ; bandeau « Prologue » (cadre doré à fond bleu) ; sens d'ouverture des coffres.

### Décidé, pas encore codé
- **Transitions à x4** (#101 ; seul le réglage « Vitesse de transition » disparaît, marche et Maj restent : D-201) : ce qu'il faut savoir avant de coder. Les bruitages de transition (lus dans le moteur, **non rejoués**) sont **305** (sortie de ville ou de carte, escalier), **309** (porte), **312** (`TownFallAction`), **330** (`TownSubeAction`) et **306** (sort de déplacement) ; le 305 n'est joué qu'à mi-fondu, donc la transition doit être reconnue à son départ. Voir « Bruitages : transition de carte et coffre d'ennemi » plus haut.
- **Menus simples** : repli automatique seulement, sans option (D-194).

### À trancher par Sylfried (#102)
1. **Étendue de la suppression des vitesses** (#101) : **tranché à 17 h 01 (D-201)** : seul le réglage « Vitesse de transition » disparaît ; la marche et la touche Maj restent.
2. **Sort de déplacement (306)** : **tranché à 17 h 03 (D-202)** : durée d'origine ; Sylfried le teste, peut-être accélérable avec Maj.
3. **Format de distribution** (#87) : scripts + `.bat`, `.exe` launcher, ou `.exe` qui embarque Unicorn (GPL v2) : « on verra ».
4. **Audio réel et `reglages.json`** (#99) : **expliqué à 17 h 03 (D-202)** : jamais vus sur son PC (essais sans haut-parleurs, fichiers de réglages fabriqués) ; rien à décider. **Réglé à 17 h 07 (D-203)** : l'audio fonctionne ; pas de souci pour `reglages.json`.

### Non vérifié (#102)
Rien n'a été exécuté côté outil. Les bruitages 305, 309, 312, 330 et 306 sont lus dans le code du moteur, jamais rejoués. L'idée qu'un `.exe` launcher n'ait pas les obligations d'une redistribution d'Unicorn est une **supposition** (pas un avis juridique). La citation de la documentation GitHub sur les dépôts sans licence a été lue le 03/11/2026.

## Avance #103 : précision de 17 h 01 (03/11/2026, docs seulement)

### Fait
- **Précision de Sylfried** (D-201) : « Ah pardon si la vitesse de marche et l'accélération à la touche SHIFT doit rester ! je parlais surtout de l'accélération des transitions ! ». Seul le réglage « Vitesse de transition » disparaît ; la marche, la caméra et l'accélérateur Maj ne changent pas. Ma lecture de 16 h 47 (« Avance #102 ») était trop large.
- **Issues** : #101 retitrée et réécrite (« Transitions : retirer le réglage « Vitesse de transition »… ») ; #53 retrouve son périmètre (marche x3 / x4 et accélérateur, plus combat « Très rapide » et transitions à x4) ; commentaire correctif sur #96 (reste fermée).
- **17 h 03 (D-202)** : le sort de déplacement (306) n'est pas raccourci (Sylfried le teste lui-même, peut-être avec Maj) ; #99 : « audio réel » et `reglages.json` expliqués, rien à décider.
- **Documents** : D-197 précisée, D-201 et D-202 ajoutées ; G-008, G-212 et G-213 corrigées ; `resume.md`, rapport et `history.md` alignés.
- Aucun fichier de `dq4_pc/` ni de `tools/` modifié.
