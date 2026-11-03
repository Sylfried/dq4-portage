# Lacunes déjà identifiées (agent « audit-github », lot PR #43, version révisée à la reprise)

**Mis à jour le 03/11/2026 à 16 h 47** (réponses de Sylfried, D-191 à D-202 : G-008, G-012, G-015, G-039c, G-058, G-108, G-162, G-205, G-212 ; avant : tri des statuts après la lecture de Sylfried de 15 h 50, D-163 à D-190 : ~80 lignes ; G-019, G-050, G-096, G-104, G-107, G-112, G-140 à G-143, G-146, G-149, G-150, G-173, G-211 ; `dq4-pc` n'existe plus). Lecture seule. Ce fichier recense **ce que les documents et le code disent déjà** : « Non résolu », « Non vérifié », « Pas fait », « Pas rejoué », « Supposé », issues ouvertes de `dq4-pc`, restes déclarés dans les 42 PR de `dq4-portage` et dans les PR/issues de `dq4-pc`, README, `docs/historique.md`, `docs/workflow.md`, notes techniques et notes de la visionneuse. Il ne cherche **pas** de lacunes nouvelles dans le jeu : la couverture fonctionnelle (casino, églises, banque, PNJ, scripts…) est l'objet de l'agent « couverture ».

**Contrôle fait à la reprise (02/11)** : le fichier du prédécesseur a été relu en entier ; toutes les références « notes l.N » étaient ambiguës (deux fichiers de notes) et plusieurs étaient fausses ; elles sont **toutes remplacées** par `NV:N` (= `docs/notes-visionneuse-dq4-pc.md`, ligne N) ou `NT:N` (= `docs/notes-technique-portage-dq4.md`, ligne N), vérifiées une à une sur `main` (08f5785). Corrections de fond : G-103 (les facteurs 1,225 / 1 / 0,775 de la croix sont **prouvés** par le code d'origine depuis l'audit de #39, plus « choisis »), G-034 (seul le genre 18 reste non dessiné), G-045 (la cadence du moteur est établie ; seul le rythme réel des fondus d'Unity est supposé), G-093 (reformulé : le code ne nomme que 4 parties, un traitement générique des autres n'est pas exclu). Ajouts : sections I (lacunes oubliées par le prédécesseur, dont G-173) et J (lot en cours #43, avec les messages de 02 h 27 à 02 h 38 lus dans la transcription), lignes G-147 à G-152. Les liens D-xx renvoient au registre `decisions.md` révisé (D-100 à D-103, D-120 à D-136, D-140 à D-148 et D-46 à D-49, D-17 à D-19 sont nouveaux). Recherche dans le code : **aucun** `TODO`, `FIXME` ni `NotImplemented` dans `dq4_pc/*.py` (établi par grep).

**Colonnes** : ID ; description ; source ; statut probable (**ouvert** = rien ne dit que c'est réglé ; **traité, à reconfirmer** = corrigé mais pas confirmé par Sylfried ou testé seulement sous Linux ; **en cours** = dans le lot #43 ; **obsolète** = périmé) ; **classement PROVISOIRE** : `[décision]` de Sylfried, `[oubli]` de Claude, `[bug]`, `[à vérifier]` (non tranchable sans test Windows / capture mobile) ; lien vers `decisions.md` (D-xx) et contradictions (C-xx).

Les classements sont des hypothèses de lecture : seuls les messages de Sylfried (registre `decisions.md`) tranchent. **Aucun test Windows** n'a été fait (pas d'accès). Un `[décision]` classé « de Claude » signifie : choix consigné par Claude, **non formulé** par Sylfried.

## A. Plateforme, vérification Windows/GPU, distribution

| ID | Description | Source | Statut | Classement | Lien |
|---|---|---|---|---|---|
| G-001 | **Rendu OpenGL réel sous Windows jamais vérifié** : toutes les captures viennent de Mesa sous xvfb **03/11** : Sylfried : « le reste fonctionne » ; #52. | PR #39-#42 ; NV:326(a), NV:345(a) | ouvert (reste : anticrénelage, suréchantillonnage, 2 moniteurs) | [à vérifier] | D-11 |
| G-002 | Régénération du cache et de `ui_layout.json` (`GENERATION` 3) par `lancer_dq4.bat` non vérifiée sous Windows **03/11** : premier lancement Windows : « aucun souci ». | PR #39, #41 ; NV:326(a) | **clos (03/11)** | [à vérifier] |  |
| G-003 | MSAA x4 par défaut, alpha-to-coverage, suréchantillonnage, x8, performance 4K non vérifiés sur GPU réel | PR #41 (« Non vérifié ») | ouvert (à tester : anticrénelage x4, suréchantillonnage ; #52) | [à vérifier] |  |
| G-004 | Plein écran : flash au lancement et changement de résolution non vérifiés ; `resolution` sans effet au lancement en plein écran | PR #41 ; NV:400 | **clos (03/11)** : plein écran OK ; deux moniteurs dans #52 | [à vérifier] | D-129 |
| G-005 | **Plein écran exclusif** (vraie bascule de résolution, refus du moniteur, Alt-Tab, restauration du bureau, multi-moniteurs, DPI) : non vérifié ; **fonction à retirer** (demande 02:12) **03/11** : fonction retirée en #43 (plein écran / fenêtre seulement). | PR #42 ; NV:423 ; `fenetre.py:272,724` | **clos (#43)** | [décision] | D-30, C-1 |
| G-006 | F11 / Alt+Entrée avec un vrai clavier ; Alt Gr sur AZERTY (= Ctrl + Alt sous Windows) **03/11** : F11 et Alt + Entrée fonctionnent (Alt Gr non précisé). | PR #28 ; NV:243, NV:423 | **clos (03/11)** | [à vérifier] | D-28 |
| G-007 | Glisser de la fenêtre « Interface » à la vraie souris (corrigé en #42 ; **supposé** que Windows envoie les mêmes événements) **03/11** : « la fenêtre glisse bien à la souris ». | PR #41 ; NV:397, NV:435 | **clos (03/11)** | [à vérifier] | D-35, D-128 |
| G-008 | Performance Windows à vitesse x3/x4/x8 (budget 30 ms par image) ; taux de rencontres à grande vitesse sur longue marche ; fondus x3/x4 sur vraie transition **03/11 16 h 47** : la marche x3 / x4 et l'accélérateur Maj restent (D-201) ; la vitesse de transition devient x4 fixe pour les transitions de porte (D-197, #101) : à tester aussi, avec le combat « Très rapide ». | PR #33, #42 ; NV:429 | ouvert (à tester ; #53, #101) | [à vérifier] | D-29b |
| G-009 | « Énorme zoom au lancement » (résolution enregistrée 3840x2160 > écran) : corrigé en #25, **non testable ici** | PR #25 ; NV:199 | ouvert (« pas encore testé » ; #52) | [à vérifier] |  |
| G-010 | Boîtes de dialogue Windows d'export/import (tkinter absent de l'environnement : seul le repli par dossiers a tourné) **03/11** : premier lancement, import et export : « aucun souci ». | PR #40 ; NV:353, NV:362 | **clos (03/11)** | [à vérifier] | D-72 |
| G-011 | Premier import **sans aucun journal** : les boutons du menu de départ (fixés à la création du moteur) ne changent qu'au relancement ; le panneau le dit | PR #40 ; NV:362 | ouvert (limite connue) | [à vérifier] | D-72 |
| G-012 | Extraction de `hyodai1` (bandeau « Prologue ») sous Windows : sans UnityPy ou sans APK, le bandeau est absent **03/11 16 h 47** : « Yes je vois le cadre » (D-192). | NT:229 ; PR #40 | **clos (03/11, 16 h 47)** | [à vérifier] |  |
| G-013 | Licence : Unicorn indiqué GPL v2 (sa description) alors que ses métadonnées disent « BSD » : **à vérifier avant toute redistribution** **03/11** : à traiter comme GPL v2 : `docs/licences.md` ; choix avant le `.exe` dans #87. | PR #40 ; NV:357 | **clos (03/11, D-170)** | [à vérifier] | D-05 |
| G-014 | Python 3.15 : le lanceur n'essaie que 3.13, 3.12, 3.11, 3.14, 3.10 (`lancer_dq4.bat:15`) ; l'issue #26 dit « validé sur pdc (Python 3.15) » **03/11** : premier lancement : « aucun souci ». | issues #12, #26 | **clos (03/11)** | [à vérifier] |  |
| G-015 | **Packaging .exe** sans contenu Square Enix : pas fait, aucun fichier de packaging **03/11 16 h 47** : option « `.exe` launcher » ajoutée. | issue #18 | ouvert (format non tranché, D-195 ; #87) | [décision] de fait (priorité jamais donnée) | §9 |
| G-016 | **CI minimale** (compilation + fichiers interdits) : pas fait ; `.github/` ne contient que 3 modèles d'issue + `pull_request_template.md` **03/11** : CI faite : `.github/workflows/ci.yml`. | issue #21 | **clos (#49)** | [oubli] |  |
| G-017 | Étendre à DQ5 et DQ6 | issue #19 | ouvert | [décision] (reporté ; intention confirmée : Nimzo/DQ5 cité le 02/11) | D-14 |
| G-018 | Scripts de recherche (désassemblage, hooks) hors dépôt (`/tmp/specs/`) : à ranger dans `outils/` **03/11** : `/tmp/specs` n'existe plus (environnement de session) ; à recréer au besoin. | issue #20 | **clos (caduc, 03/11)** | [oubli] |  |
| G-019 | **Pas de manette** : aucun `pyglet.input` / `joystick` dans `dq4_pc/*.py` (grep) ; l'issue #8 reste à moitié faite (remappage clavier fait) **Sylfried (03/11) : « pour la suite on pourra prévoir d'utiliser une manette »** (D-150) ; l'issue #8 n'existe plus (`dq4-pc` supprimé). À faire après le clavier complet (G-096, D-155). | issue #8 ; PR #15 | ouvert, **retenu pour la suite** (03/11, D-167 ; #61) | [décision] prise | §9 |
| G-020 | Ratios autres que 16/9 (16:10, 21:9, 4:3) : « le décor ne doit pas montrer le vide autour des cartes » non vérifié ; crédits du titre mesurés sur 4 formats seulement **03/11** : « les ratios sont OK ». | issue #24 ; PR #42 | **clos (03/11)** | [à vérifier] | D-01 |
| G-021 | Fenêtre plus grande que l'écran : correctif Windows (`ajuster_taille`) non testable | `fenetre.py:70-90` ; PR #25 | ouvert (« pas encore testé » ; #52) | [à vérifier] |  |
| G-022 | Environnement de test : 2 coeurs, un seul xvfb, cache à reconstruire ; première préparation ~1 min 30 à 2 min au premier lancement | PR #10, #18 ; NV:82 ; NT:71 | ouvert (limite) | [à vérifier] | |
| G-023 | **Aucune capture du jeu mobile** : tailles de texte, interligne, placement vertical (~1 px), croix, dragon, éclats d'épée, plume de la carte, etc. comparés au code, pas à l'image **03/11** : Sylfried a comparé lui-même : « nickel sur ces points » ; des captures restent utiles pour les caméras d'attaque (#92). | PR #41, #42, #36, #19 ; NV:326(d), NV:345 ; NT:232 | **clos (03/11)** | [à vérifier] | D-11 |

## B. Moteur, protocole, mémoire

| ID | Description | Source | Statut | Classement | Lien |
|---|---|---|---|---|---|
| G-040 | Paquets **non traités** par `moteur.py:100-190,607` : **1 `fld_color`, 27 `field_load`, 30 `field_scale`** (rôle non décodé dans les notes ; la carte du monde marche sans eux, effet réel inconnu) | NT:78 (table des 38) vs handlers ; issue #13 ; NT:144-145 | ouvert | [à vérifier] | |
| G-041 | **Paquet 6 `fld_event_anim`** (animations d'événements, FEAN) non rejoué : peut concerner des scènes d'histoire | NV:141 ; PR #17 ; issue #13 | ouvert | [à vérifier] | |
| G-042 | **Paquets 16 `chara_sleep_pose`, 17 `chara_sleep_near`, 18 `chara_pose`** (personnages couchés, maillages `s_meshLie*`, shader `Custom/CharaSleep`) : jamais vus, non rejoués | NT:113, NT:78 | ouvert | [à vérifier] | |
| G-043 | **Paquet 33 `map_color_rate`** (teinte de la carte, ouverture de `mlb1a`) ignoré ; sous-titre des chapitres suivants jamais vu **03/11** : teinte jour / nuit et nom du chapitre 1 : OK ; reste le paquet 33, les paquets 16 / 17 et le sous-titre des chapitres suivants. | PR #40 ; NT:233 | ouvert (#58) | [à vérifier] |  |
| G-044 | **Allocateur « bump » de 256 Mo, jamais libéré** (`h_free` renvoie 0 ; `raise MemoryError('tas epuise')`) : arrêt possible sur longue session ; aucune mesure | `emu_core.py:292,370-371,~615` ; issue #11 | ouvert | [bug] latent | |
| G-045 | Rythme **réel** des fondus d'Unity « 30 Hz » supposé (la cadence du moteur, elle, est établie : `Boot` fixe `fixedDeltaTime = 1/30`) | NV:345(f) ; NV:105 ; NT:209 | ouvert | [à vérifier] | |
| G-046 | `SetFadePriority` non reproduit (appelé par `MenuMessage.SetCanvasMesh`) | NT:228 | ouvert | [à vérifier] | |
| G-047 | `snd_vol.dat` (table de volumes), fondus entre musiques (`PlayBGM` côté Unity), bruitages 3D / positionnels non étudiés | NT:123 | ouvert | [à vérifier] | |
| G-048 | `g_isAmazon` forcé à 1 : réseau / cloud / portail jamais gérés (cellule 8) | NT:200, NT:217 ; PR #39 | ouvert (volontaire) | [décision] de Claude | D-71 |
| G-049 | Moteur modifié **en mémoire** (patch 0x16ef28 « Paramètres », constantes `drawSymbol` 1600 px, crochets de vitesse du texte, `g_isAmazon`) alors que la règle dit « le moteur d'origine ne se modifie pas » **03/11** : règle reformulée et crochets listés dans les notes techniques. | `moteur.py:16,382-407,457-474` ; PR #4, #41 | **clos (#49)** | [à vérifier] | D-12, C-6 |

## C. Carte du monde

| ID | Description | Source | Statut | Classement | Lien |
|---|---|---|---|---|---|
| G-030 | Horizon : le moteur n'envoie que 25 colonnes ; la carte entière est lue depuis PR dq4-pc #70 (probablement réglé) | issue #45 ; PR dq4-pc #70 | traité, à reconfirmer | [à vérifier] | |
| G-031 | **Autres moyens de transport (bateau, ballon…) jamais étudiés** ; « pas de marche sur l'eau/bateau testée » | issue #45 ; NV:44 | ouvert | [oubli] — **grave pour la jouabilité** | |
| G-032 | Entrée dans une ville par son icône : à vérifier pour les autres villes | issue #45 | ouvert | [à vérifier] | |
| G-033 | **Emplacements 10 à 12** de la carte du monde (ids 4289, 4279) créés sans jamais recevoir de position : non dessinés (les alliés ?) | NT:110 ; NT:172 | ouvert | [à vérifier] | |
| G-034 | Genre d'icône **18** (32x16) non dessiné (19 et 20 ajoutés en PR #4) | NV:44 ; PR #4 | ouvert | [à vérifier] | |
| G-035 | Code 4 de la petite carte (lieu spécial, croix rouge) : jamais reçu dans nos sauvegardes, rendu vérifié seulement par valeur factice | NV:240, NV:323(4), NV:325 ; NT:126, NT:187 | ouvert | [à vérifier] | |
| G-036 | **Grande carte du monde (type 26)** : rectangle d'origine non lu, ancien rectangle (-225 à 225) conservé | NV:327 ; NT:187 | ouvert | [à vérifier] | |
| G-037 | Ancrage de la plume et des carrés rouges (centré / bas gauche) supposé, sans capture de référence **03/11** : comparaison au mobile « nickel ». | PR #34, #35 ; NV:285, NV:296 ; NT:187 | **clos (03/11)** | [à vérifier] |  |
| G-038 | Ordre d'affichage des compagnons sur la carte du monde non vérifié avec un vrai compagnon (profondeur `0,04 + rang x 0,0005`) | NV:178 ; PR #22 | ouvert | [à vérifier] | |
| G-039 | Alliés qui prennent de la distance en courant sur la carte du monde ; « alliés sur la carte du monde non mesurés » | PR #35, #37 ; NT:172 | ouvert | [à vérifier] | D-61 |
| G-039b | Zoom de la minicarte à 400 % après réglage de l'angle : non reproduit (garde-fou ajouté) | PR #23 ; NV:187 | ouvert | [bug] latent | |
| G-039c | Pièces `MAP_DIFF` du plan (parties découvertes ou non) non reproduites **03/11 16 h 47** : « c'est bon désormais » (D-192) ; pièces reproduites (`_plan_monde_fenetre`). | PR #18 ; NV:147 | **clos (03/11, 16 h 47)** | [à vérifier] |  |

## D. Villes, décors, caméra, sprites

| ID | Description | Source | Statut | Classement | Lien |
|---|---|---|---|---|---|
| G-050 | **Toits et décors qui cachent le héros** : silhouette supprimée (« absente du jeu d'origine ») ; transparence des toits non faite ; issue dq4-pc #6 ouverte **Sylfried (03/11) : on laisse les toits tels qu'ils sont, « c'est le fonctionnement du mobile »** (D-151). | PR #2 ; issue #6 | **clos (03/11)** | [validé] | D-93, C-9 |
| G-051 | Eau des villes (séquences / mouvements au chargement) : traitée en PR #17 pour les séquences automatiques ; « eau des villes » encore citée ouverte par PR #9 **03/11** : « tout est OK ». | PR #9, #17 | **clos (03/11)** | [à vérifier] |  |
| G-052 | Animations de matériaux (**SRA**), d'événements (**FEAN**), clé de palette liée à un événement en cours : non rejouées | NV:141 ; PR #17 | ouvert | [à vérifier] | |
| G-053 | Événements **FEMV** non faits ; bateaux animés au chargement non faits | PR #3 ; NV:83 ; NT:43 | ouvert | [à vérifier] | |
| G-054 | **Débordement des vagues d'eau sur le sol** des grottes : non reproduit **03/11** : « c'est résolu ». | PR #21, #22 ; NV:208 | **clos (03/11)** | [bug] latent |  |
| G-055 | **Murs invisibles et escalier de `dbout`** (collisions internes au moteur ; enquête 31/10 sans résultat probant) : « à revérifier avec la correction de Y » **03/11** : décor caché dans la carte, « c'est résolu » ; #78 fermée. | PR #18, #21, #22 ; NV:171, NV:208, NV:221 | **clos (03/11)** | [à vérifier] — risque de blocage |  |
| G-056 | **Clignotements** : plusieurs causes corrigées (#12, #20, #33), reste « non reproduits sans l'endroit exact » **03/11** : « tout est OK ». | PR #21, #22 ; NV:208 | **clos (03/11)** | [bug] possible |  |
| G-057 | Fleurs qui scintillent : cause A (z-fighting) corrigée ; alpha-to-coverage ne couvre que MSAA ; avec anticrénelage **et** suréchantillonnage sur « Aucun », seule A est corrigée | PR #41 | traité, à reconfirmer avec l'anticrénelage (#52) | [à vérifier] | D-130 |
| G-058 | **Coffres** : sens d'animation à l'envers, orientation vers le joueur (déjà touchés en #18, #21, #22) **03/11 16 h 47** : sens d'ouverture OK : « c'est bon dans le bon sens » (D-192). | message 02:12 | **clos (03/11, 16 h 47)** | [bug] | D-42 |
| G-059 | **Dragon de l'écran titre** : deux orientations, placement 1 pour 1 du mobile, logo non centré, fond répétitif ; `TITRE_DRAGON_HAUT = 0` supposé **03/11** : « le dragon du titre il est bon ». | message 02:12 ; PR #42 ; NV:439 | **clos (03/11)** | [bug] | D-33, D-11, C-7 |
| G-060 | **Bulle « ! »** : cas exact des tonneaux non reproduit, seule la dérive avec la caméra corrigée **03/11** : « les bulles aussi ». | PR #42 ; NV:448 | **clos (03/11)** | [à vérifier] | D-29c |
| G-061 | **Caméra du père** (`mlb1a`) : symptôme non reproduit, correction du défaut mesuré (traînée à la course) **03/11** : « tout est OK ». | PR #42 ; NV:443 | **clos (03/11)** | [à vérifier] | D-29g |
| G-062 | Caméra : sous verrou (`cam_bloquee`) la rotation / l'inclinaison choisies par l'utilisateur sont coupées d'un coup | NV §Caméra (#42), l.441-445 | ouvert | [à vérifier] | |
| G-063 | `angle_camera` (flèches haut/bas) est **sauvegardé** : un appui accidentel décale le tangage en permanence **03/11** : ne plus enregistrer l'angle ; option de distance supprimée ; deux touches avancer / reculer. | NV §Caméra (#42), l.441-445 | [décision] retenue (03/11, D-172 ; #83) | [bug] latent |  |
| G-064 | Caméra du monde et du combat : angle non revérifié par l'équivalence numérique de #42 | NV:441-445 | ouvert | [à vérifier] | D-29f |
| G-065 | Caméra bornée à 120 ° non rencontrée ; **signe de l'inclinaison des sprites 2D** (`SENS_TANGAGE`) à vérifier à l'écran ; scène à caméra visible avec héros près d'un bord, chutes, sorts de retour non jouées ; billboards non vérifiés sur tous les types d'objets | PR #28 ; NV:216, NV:238, NV:366 | ouvert | [à vérifier] | |
| G-066 | Jambes du héros et compagnons pendant la course (« il glisse un peu ») | PR #28 ; NV:239, NV:243 | probablement obsolète depuis #37 | [à vérifier] | D-61 |
| G-067 | Ombres décalées à la course : non reproduit | PR #33 ; NV:279 | ouvert | [à vérifier] | |
| G-068 | Jarre / coffre avec message en capture : testé seulement dans une sonde sans fenêtre | NV:365 | ouvert | [à vérifier] | |
| G-069 | **Auberge, titres de chapitre, écran de chargement, générique, sifflet/ballon, sol qui soigne** : séquences à fondu attendu, **jamais rejouées** (le générique `TownEndrollManager` existe dans le moteur) | PR #10 | ouvert (à tester par Sylfried, #90) | [à vérifier] — voir agent couverture |  |

## E. Combat

| ID | Description | Source | Statut | Classement | Lien |
|---|---|---|---|---|---|
| G-070 | **Combats de boss et de plusieurs monstres** : à vérifier **03/11** : boss du chapitre 1 et groupes : OK. | issue #15 (commentaire 10:40) | **clos (03/11)** ; boss final dans #56 | [à vérifier] |  |
| G-071 | **Effets de sorts, flashs, effets d'écran** (`cmd_screen_effect`, effets 3, 5, 6) **03/11** : des ennemis lancent des sorts de défense : à vérifier que la défense augmente vraiment. | issue #56 ; PR #7 ; dq4-pc PR #66 | ouvert (#56, #68) | [à vérifier] |  |
| G-072 | `BackColor` (fond de couleur de combat) : valeur estimée (couleur moyenne du sol), non lue dans les données de la carte | issue #56 ; NV:53 ; NT:74 | ouvert | [à vérifier] | |
| G-073 | `cmd_chara` en combat (sprites en combat). **Roulis de la caméra de combat : sans objet** (relu le 03/11/2026) : `Fenetre._rot_camera` applique les trois angles du moteur, `rot_unity(-x, -(y + 180), z)` (`fenetre.py:1152-1155`), le roulis n'est donc plus ignoré ; **établi par lecture**, non vu à l'écran (aucune capture d'un combat avec roulis non nul) | issue #56 ; NV:53 | ouvert (roulis : **clos par relecture**) | [à vérifier] | |
| G-074 | Ordre de tracé des monstres qui se recouvrent : instabilité latente ; Scarapince (visage caché par la carapace) à confirmer **03/11** : « l'ordre de tracé est bon désormais ». | PR #20 ; dq4-pc PR #54 (F9, depuis supprimée en #15) | **clos (03/11)** | [à vérifier] |  |
| G-075 | Un monstre endormi/paralysé pourrait cesser d'être mis à jour (donc s'effacer) | NT:55 ; dq4-pc PR #66 | ouvert | [bug] possible | |
| G-076 | « L'animation du 2e monstre s'arrête après un coup » : non reproduit sur 6 600 images, « en attente de précisions » | dq4-pc PR #70 | ouvert | [à vérifier] | |
| G-077 | Un seul combat étudié en détail pour la vibration (2 Glacyclones) ; effet dépendant de la fréquence d'écran | PR #20 | ouvert | [à vérifier] | |
| G-078 | Fin de combat : victoire, expérience, montée de niveau, game over vérifiés en partie (« pas de combat gagné dans mes essais automatiques ») **03/11** : victoire, montée de niveau, game over : OK. | PR #35 | **clos (03/11)** | [à vérifier] — **grave** |  |
| G-079 | **Retour à l'écran titre depuis un combat ou une boutique, puis nouvelle partie sans relancer** : non vérifié **03/11** : nouvelle partie sans relancer : OK ; retour au titre depuis un combat ou une boutique : pas testé. | PR #41 | ouvert (#56) | [à vérifier] | D-76 |
| G-080 | Sort **Morph** (événement d'histoire : église, grenouille / lapin et Élisa) : taille et position du nuage non vérifiées ; Morph d'un monstre en combat non vérifié **03/11** : Morph de la cinématique de début : OK. | NV:409 ; PR #41 | traité (03/11), Morph en combat non vu | [à vérifier] | D-136 |
| G-081 | Fenêtres de combat : texte d'action « Attaquer / ▼ / cible » sans cadre, cadre de titre (type 54), niveau « ? » du 2e personnage ; taille des chiffres de dégâts non mesurée sur le mobile **03/11** : « pour les fenêtres de combat tout est bon ». | NT:107 ; NV:63, NV:148 ; PR #18 | **clos (03/11)** | [à vérifier] |  |
| G-082 | Tri / évitement des chevauchements de fenêtres, marques sous les monstres, taille de police **03/11** : « pour les fenêtres de combat tout est bon ». | NT:93 | **clos (03/11)** | [à vérifier] |  |

## F. Menus, interface, avant-partie, boutiques

| ID | Description | Source | Statut | Classement | Lien |
|---|---|---|---|---|---|
| G-090 | **Classes `IBase` personnalisées non reproduites** : `StatusIconChanger` (types 4, 5, 20, 21, 46, 60, 61, 67), nombres d'objets, plaque de monstre, carte de ville ; en partie corrigées par l'audit de #39 | NT:87 ; NV:63 ; dq4-pc PR #68 ; PR #39 | ouvert (#98 : à reproduire, principe D-169) | [à vérifier] |  |
| G-091 | `MonsterMarkList`, type 66 (église) : « incomplet » en #68, repris en #39 | NT:87, NT:93 ; NV:63 | traité, repris dans #98 | [à vérifier] |  |
| G-092 | **Boutiques (types 28, 58, 59, 60, 63)** : achat/vente codés mais **jamais joués** (aucune sauvegarde de test n'y mène) ; quantités gauche/droite non vérifiées | PR #39, #41 ; NT:185 ; NV:326(b), NV:408 | ouvert | [à vérifier] — **grave pour la jouabilité** | D-81, D-134 |
| G-093 | **Casino, banque, église (confession)** : noms de fenêtres présents dans l'éditeur (groupes « Boutiques et banque », « Casino » : `Casino_Slot`, `Casino_Poker`, `Casino_FightStadium*`, `BankDeposit/BankDraw`, `ChurchRoot` ; `pause.py:41-54`), aucun test documenté ; le code ne nomme que 4 parties (`moteur.py:8-11`), un traitement générique des autres n'est pas exclu | NT/NV (aucune mention) ; code | ouvert | [à vérifier] — voir agent couverture | D-16 |
| G-094 | Choix grisés (PM insuffisants, objets inutilisables), pages et défilement, curseurs gauche/droite : jamais testés explicitement | issue #3 | ouvert | [à vérifier] | |
| G-095 | Y, Select sans effet ; Y ouvre la fenêtre « carte de la ville » (désormais via M) | PR #15 ; NV:123 | ouvert (volontaire) | [décision] de Claude | |
| G-096 | Écran Divers : le clavier pilote la liste mais **« Sauvegarde rapide » reste à la souris** **Exigence de Sylfried (03/11, D-155) : tous les boutons de l'interface doivent être accessibles au clavier** ; celui-ci n'en est qu'un cas, l'inventaire complet reste à faire. | PR #34 | ouvert (exigence **suspendue** le 03/11, D-165 ; #59) | [exigence] | D-32 |
| G-097 | Plaque « Sauvegarde automatique » : **cachée** quand le moteur n'envoie pas d'étiquette ; doit être **grisée** | PR #41 ; NV:383 ; message 02:12 | traité (#43) | [bug] | D-32, C-3 |
| G-098 | **« Revenir à l'écran titre » efface la sauvegarde automatique** (`killbank(4,false)`) : comportement du bouton d'origine **03/11** : comportement d'origine gardé. | PR #41 | **clos (03/11, D-184)** | [décision] ou [à vérifier] | D-76 |
| G-099 | **Clavier du nom** : disposition du portage (celle d'origine non retrouvée, `SetMode` 0xCE11BC) ; nom refusé (message 833011) non déclenché ; choix du sexe à la manette | PR #39 ; NT:209 | ouvert | [à vérifier] | D-94 |
| G-100 | Démo de caméra de la première phase du titre : rôle non établi (« supposé : le 1er appui termine la phase d'attraction ») | NT:197, NT:209 ; NV:345(f) | ouvert | [à vérifier] | |
| G-101 | Éclats d'épée (taille/place), bandeau « Prologue » (hauteur 225 supposée), teinte du prologue | PR #40 ; NV:373 ; NT:229, NT:232-233 | ouvert | [à vérifier] | |
| G-102 | Options de la fenêtre Paramètres d'origine (volumes, « Taille de la croix ») **plus joignables** ; la valeur de la sauvegarde reste utilisée | PR #41 | ouvert (volontaire) | [décision] de Claude | D-76, D-123 |
| G-103 | Croix : barre de rotation de la caméra et bouton de position de la croix non reproduits (« sans objet sur PC ») ; option `g_pad_pos` non reliée. (Facteurs de taille 1,225 / 1 / 0,775 : **prouvés** par `c_PadScaleTBL`, plus un choix) **03/11** : tailles de la croix : OK. | NV:327, NV:323(3) ; NT:189 | ouvert (barre de rotation : #97) | [à vérifier] | D-66 |
| G-104 | Curseur doré oscillant des menus : « inventé », aucun équivalent dans le jeu d'origine. **Caduc (relu le 03/11/2026)** : le curseur est **fixe** dans le code courant (`pause.py:161-167`, `dx = 0.0`, texture du jeu `MenuTexture` 194..237 x 297..327) ; Sylfried a de plus demandé de **garder la petite flèche** dans l'historique (#48). Établi par lecture ; la PR qui a retiré l'oscillation n'est pas identifiable (historique aplati par #46) | PR #27 ; NV:233, NV:327 | **clos (caduc)** | [établi] | D-95 |
| G-105 | Survol : bug « Rien » / mauvais bouton allumé quand la souris bouge, **non reproduit** (magasin inaccessible) ; trois durcissements ajoutés. Nouveau symptôme le 02/11 : souris inutilisable ~1 s après le clavier | PR #25, #27, #28 ; NV:231 ; message 02:12 | ouvert (confirmé imparfait le 03/11, souris et clavier ; #80) | [bug] | D-44 |
| G-106 | Cause exacte de l'Échap qui sélectionnait « Sauvegarde rapide » non prouvée (corrigée par le gel de la souris) **03/11** : « tout est OK ». | PR #28 ; NV:243 ; `fenetre.py:870,1925` | **clos (03/11)** | [bug] possible | D-44 |
| G-107 | `Menu_Echap_DQ4_PC.xlsx` (spécification de Sylfried) **non régénéré** après les réorganisations de #26, #27 et suivantes **Plus d'actualité** (Sylfried, 03/11, D-157) : rien à régénérer. | PR #25-#27 ; NV:202, NV:221 | **clos (03/11)** | [clos] | D-57 |
| G-108 | Mode « menus simples » (sans `ui_layout.json`) : fenêtre de carte non dessinée, cadres de secours bleus | NV:193, NV:326(e) | traité : repli automatique gardé, pas d'option (D-194 ; #99) | [à vérifier] |  |
| G-109 | Taille des textes hors dialogues : pas de référence | PR #27 ; NV:220 | ouvert | [à vérifier] | |
| G-110 | Position de la fenêtre « Interface » : gardée pour la session seulement | NV:397 | ouvert | [décision] de Claude | D-128 |
| G-111 | **Le jeu doit l'emporter sur le réglage du joueur « pour tout »** (script qui change la valeur, ex. Nimzo/DQ5) ; `defilement_force` n'existe que pour les combats ; dialogues du terrain : crochet distinct, jamais automatiques **03/11** : dialogues du terrain pour DQ5 : D-186, #88. | message 02:12 ; `reglages.py:42-43` ; NV:390 ; `moteur.py:382-407` | traité (#43) | [oubli] | D-14, C-10 |
| G-112 | Mapping « Moyen = 2, Lent = 3 », libellés « Masqué / Masquée » demandés à validation **« Masqué / Masquée » : validés par Sylfried le 03/11 à 14 h 19** (D-154). | PR #42 | **clos (03/11)** : libellés validés ; mapping sans objet depuis #44 | [validé] | D-88, D-89 |
| G-113 | Ordre des pages / bouton « Paramètres » → Pause : le patch du moteur est réappliqué après chargement d'un état | NT:242 | traité | [à vérifier] | D-76 |
| G-114 | Souris / molette : clic molette + déplacement (rotation), clic molette (direction), Ctrl + clic molette (zoom) : **aucune occurrence de `MIDDLE`** dans le code | message 02:12 ; `fenetre.py:560` | traité (#43), vu OK le 03/11 | [décision] (nouvelle demande) | D-34 |
| G-115 | Nom de Ragnar « trop bas » : ancrage « middle » supposé ~1 px plus bas **03/11** : « Non c'est bon ». | message 02:12 ; NV:407 | **clos (03/11, D-185)** | [bug] possible | D-43 |
| G-116 | F1 en haut à droite par défaut | message 02:14 | traité (#43) | [décision] | D-45 |
| G-117 | Plein écran : interrupteur simple, Alt+Entrée / F11 **03/11** : F11 / Alt + Entrée OK. | message 02:12 | **clos (03/11)** | [décision] | D-30 |
| G-118 | Correction des bords : suppression de l'option (`reglages.py:32`, `pause.py:292`), toujours active | message 02:12 | traité (#43) | [décision] | D-31 |
| G-119 | Dragon : autres modèles fbx non vérifiés ; retour moteur de fin d'animation non implémenté ; fbx dessinés seulement dans les scènes de ville | PR #42 ; NV:439 | ouvert | [à vérifier] | |

## G. Son, sauvegardes, performance

| ID | Description | Source | Statut | Classement | Lien |
|---|---|---|---|---|---|
| G-120 | **Sauvegarde réelle à l'église puis rechargement** : jamais confirmée sous Windows (issue #9 prio:haute ouverte) **03/11** : sauvegarde à l'église, sauvegardes auto, hors églises, création et suppression de journal : OK. | issue #9 ; `moteur.py:45-58` ; `fenetre.py:333` | **clos (03/11)** | [à vérifier] — **grave pour la jouabilité** |  |
| G-121 | Rendu audio sur haut-parleurs « à vérifier sur le PC » ; catégories de son 302 / 303 supposées « interface » | dq4-pc PR #75 ; NT:244 ; NV:391 | ouvert | [à vérifier] | D-125 |
| G-122 | Bruitage de début de combat : le moteur n'en demande aucun (seule la musique change) ; « si un bruitage précis te manque, dis-moi » | PR #8 | ouvert | [à vérifier] | D-145 |
| G-123 | Sauvegardes d'origine jamais modifiées : garantie par construction, non testée sur toutes les voies (import, états) **03/11** : « tout est OK ». | issue #9 ; PR #40 | **clos (03/11)** | [à vérifier] |  |
| G-124 | Export / import : une `data9.dat` et les états dans le zip ; vérification de taille seulement | PR #40 | traité | [à vérifier] | |
| G-125 | Performance du lancement : fenêtre figée ~3 s corrigée, « à reconfirmer sur pdc, puis fermer » **03/11** : « tout est OK ». | issue #40 (commentaire) | **clos (03/11)** | [à vérifier] |  |
| G-126 | Chargement de carte : ~55 textures d'un coup (blocage 0,1 à 0,5 s) ; à étaler ou mettre en cache GPU | issue #40 | ouvert | [à vérifier] | |
| G-127 | Préparation du cache : ~1 min 30 à 2 min, ~340 Mo ; plusieurs invalidations de version (carte3 à carte8, `HD.VERSION` 3) | PR #10, #17-#24 ; NV:82 | ouvert (limite) | [à vérifier] | |
| G-128 | Volume réel du bip 300 (`s_seVolume` × volume du fichier) non comparé au jeu Android | NV:367 | ouvert | [à vérifier] | |

## H. Documentation et suivi

| ID | Description | Source | Statut | Classement | Lien |
|---|---|---|---|---|---|
| G-140 | **Suivi d'issues périmé** : 27 issues ouvertes dans `dq4-pc`, dont plusieurs faites (#2, #5, #7, #10, #17, #23, #40, #56) ; `dq4-portage` (issues activées) n'en a aucune ni jalon, et ses 10 étiquettes sont celles par défaut de GitHub **`dq4-pc` n'existe plus** (Sylfried, 03/11, D-160) ; l'état des issues au 02/11 est dans `github_issues.md`. **Réponse (03/11, 14 h 25, D-161)** : oui aux issues pour le reste à faire ; 38 issues créées dans `dq4-portage` (#51 à #88). | API REST ; issues | **clos (03/11)** : `dq4-pc` supprimé | [clos] | C-12 |
| G-141 | « Issue #55 » citée par PR #9, #10 et NT:71 : n'existe nulle part (c'est une PR fermée dans `dq4-pc`) Mentions corrigées dans les notes (en-tête des notes techniques) ; `dq4-pc` n'existe plus. | PR #9, #10 ; NT:71 ; `depot-github-dq4-pc.md` | **clos (#49)** | [clos] | |
| G-142 | Documents du Projet (`depot-github-dq4-pc.md`) toujours centrés sur `dq4-pc` Document du Projet remplacé par `depot-github-dq4-portage.md` (#50). | `/home/claude/pjdocs/` | **clos (#50)** | [clos] | C-11 |
| G-143 | `Menu_Echap_DQ4_PC.xlsx` : même point que G-107 Même point que G-107 : **plus d'actualité** (D-157). | PR #25-#27 | **clos (03/11)** | [clos] | D-57 |
| G-144 | NT:144-145 « Inconnues / prochaines étapes » liste encore les paquets 4, 6, 14, 15, 18, 19-20, 27-30 « à décoder » alors que 4, 14, 15, 19, 20, 28, 29 sont traités **03/11** : section « Inconnues / prochaines étapes » déjà à jour depuis le 02/11 (la ligne était périmée). | NT:144-145 | **clos (#100)** | [oubli] |  |
| G-145 | NV:85-86 « Reste à faire » renvoie au « suivi des issues du dépôt » (périmé, G-140) **03/11** : section « Reste à faire » des notes de la visionneuse renvoie aux issues. | NV:85-86 | **clos (#100)** | [oubli] |  |
| G-146 | Piste 3 Unity : en pause, hors périmètre ; dépôt `dq4-portage-unity` **non lu** L'issue #57 a disparu avec `dq4-pc` ; la décision (pause, hors périmètre) tient. | issue #57 ; dq4-pc PR #67, #79 | en pause | [décision] | D-09 |
| G-147 | NT:70 « Lien id de modèle 3D (8900…, titre) → objet Unity : non résolu » est périmé pour le dragon (c1018 résolu en #42) ; reste vrai pour les autres modèles / boss (issue #16) | NT:70 ; PR #42 | ouvert | [oubli] | |
| G-148 | `docs/historique.md` : « Prochaine issue : #1 (sprites en HD) » alors que #1 est fermée ; le tableau s'arrête au 30/10 **03/11** : `docs/historique.md` complété jusqu'à #100. | `docs/historique.md` | **clos (#100)** | [oubli] |  |
| G-149 | `docs/workflow.md` : « description avec `Closes #<numéro>` », « branche supprimée après fusion », une issue par tâche — aucun n'est appliqué dans `dq4-portage` (PR « Avance #N » sans issue ; **43 branches distantes** (`main` + 42 branches de PR non supprimées, `delete_branch_on_merge` = false)) `workflow.md` aligné sur l'usage réel en #49 (suivi par PR, pas d'issues, pas de `Closes`). | `workflow.md` ; API REST | **clos (#49)** ; suppression des branches fusionnées : décision 2, en attente | [clos] | C-12 |
| G-150 | README : « `dq4-pc` : issues et pull requests (#1 à #78) » alors que les PR vont jusqu'à #79 et les issues jusqu'à #57 README corrigé (PR #1 à #49, `dq4-pc` supprimé). | README | **clos (#49)** | [clos] | |
| G-151 | Mémoire utilisateur : aucune entrée n'est postérieure au 30/10 22:50 sur le portage ; les décisions du 31/10-02/11 (D-30, D-31, D-14…) n'y sont pas **03/11** : mémoire du projet mise à jour le 03/11. | mémoire | **clos (#100)** | [oubli] | §11 de `decisions.md` |
| G-152 | Projets/doc du Projet : `project_read` non disponible pour cet agent ; les copies `/home/claude/pjdocs/` sont identiques aux `docs/` du dépôt pour 2 documents sur 3 **03/11** : documents du Projet resynchronisés le 03/11. | pjdocs | **clos (#100)** | [à vérifier] |  |

## I. Lacunes que le prédécesseur n'avait pas reprises

| ID | Description | Source | Statut | Classement | Lien |
|---|---|---|---|---|---|
| G-160 | `Global::NativeExec` : `arg2 = 0x2000 → bit 0x400` « non étudié » (entrée du moteur non connue) | NV:16 | ouvert | [à vérifier] | |
| G-161 | Maj = courir : interprétation de « Maj : toujours courir » à confirmer (touche maintenue) **03/11** : « tout est OK ». | NV:213-214 | **clos (03/11)** | [à vérifier] | D-58 |
| G-162 | Espace = action puis discussion de groupe si rien déclenché au bout de 3 pas : un cas où une action existe sans poser le bit 0x4 ouvrirait la discussion en plus **03/11** : « Espace ne fait plus les discussions de groupe » lu comme « le cas limite n'arrive plus ». **03/11 16 h 47** : corrigé : la discussion de groupe n'est plus sur Espace mais sur Alt / Alt Gr (D-198, D-60). | NV:217 | **clos (03/11, 16 h 47)** | [à vérifier] | D-58 |
| G-163 | Rendu d'une ville entière à 40 % : fond uni possible aux bords (le zoom 40-400 % a été remplacé par « Distance caméra » 50-200 %) | NV:218 | probablement obsolète | [à vérifier] | |
| G-164 | Boutiques : types 28 et 63 non vérifiés | NV:408 | ouvert | [à vérifier] | D-134 |
| G-165 | Dialogues du terrain : **jamais automatiques** (400 images d'attente mesurées) ; seul le défilement des combats existe. Sylfried parle d'un script de DQ5 (Nimzo) qui change la valeur : cas non rencontré en DQ4 **03/11** : sujet DQ5 : #88. | NV:390 ; message 02:12 | **clos (03/11, D-186)** pour DQ4 | [à vérifier] | D-14, D-124 |
| G-166 | Pause et aperçu de l'éditeur gardent `ui_font.otf` (la police du jeu SE-GARRIR n'y est pas utilisée) | NV:407 | ouvert | [décision] de Claude | |
| G-167 | Vitesse du texte = crochet de la visionneuse (le jeu d'origine n'a pas cette option) | NV:390 ; `moteur.py:382-407` | ouvert (volontaire) | [décision] | D-78, D-124 |
| G-168 | Ombre des personnages sur la carte du monde non comparée au mobile ; ombre masquée pour les feuilles 193 / 194 **03/11** : « les ombres sont OK » ; feuille 193 = bateaux (le moteur masque leur ombre), la feuille 194 n'existe pas dans les textures. | NV:157, NV:167 ; PR #19, #21 | **clos (03/11)** | [à vérifier] |  |
| G-169 | Menu Échap : ressemblance du style à la capture mobile « non mesurée » (couleurs choisies à l'œil) **03/11** : comparaison au mobile « nickel ». | NV:220 | **clos (03/11)** | [à vérifier] |  |
| G-170 | Flèches opposées : tant qu'une des deux reste enfoncée après la pression double, rien ne bouge (le relâchement n'est jamais simultané) **03/11** : « pour les flèches aussi ». | NV:224 | **clos (03/11)** | [à vérifier] |  |
| G-171 | Compagnons en ville : essais successifs (#30, #33, #34, #35, #36, #37) ; état actuel « tout accélère » (horloge) ; PNJ en mouvement et course x4 non mesurés **03/11** : « tout est OK ». | PR #37 ; NV:282, NV:295, NV:304 | **clos (03/11)** | [à vérifier] | D-61 |
| G-172 | Dernier état du bouton « Menu Pause » (PR #35-#37) retiré en #41 : la notice de #35 (NV:293) décrit encore sa plaque « copie » | NV:293 ; PR #41 | obsolète | [oubli] (doc) | D-68, D-76 |
| G-173 | Entrée (Commandes), Espace (Discussion) et M (Carte) ne jouent **pas** le bruitage 300 alors que le clic sur le bouton à l'écran le joue (comme `TouchPad.internalUpdate`) : écart de fidélité mineur signalé, non corrigé **Règle de Sylfried (03/11, D-156) : au clavier, un bruitage seulement là où le toucher en joue un, jamais ajouté de force** ; à traiter au cas par cas. | NV:368 | ouvert, **règle confirmée le 03/11** (D-166 ; #60) | [oubli] | D-103 |

## J. Lot en cours (PR #43) : tout ce qui est demandé depuis 02 h 12 (état : demandé, pas encore fusionné)

| ID | Demande (source) | Mission | Classement | Lien |
|---|---|---|---|---|
| G-200 | Dragon à une seule orientation, composition 1 pour 1 du mobile (zone portrait au centre), logo centré, fond moins répétitif (02:12) **03/11** : dragon bon (D-190). | titre2 | **clos (03/11)** | D-33, D-11 |  |
| G-201 | Plaque « Sauvegarde automatique » toujours présente, grisée si pas de sauvegarde auto ; choix laissé à Claude (02:12, 02:13) | titre2 | traité (#43) | D-32 |  |
| G-202 | Molette cliquée : rotation ; clic simple : direction ; Ctrl + clic : zoom (02:12) | entrées | traité (#43), vu OK le 03/11 | D-34 |  |
| G-203 | Le jeu prend le dessus sur le réglage (vitesse du texte et « tout ») (02:12) | options | traité (#43) | D-14 |  |
| G-204 | Correction des bords : suppression de l'option, toujours active (02:12) | fenêtre2 | traité (#43) | D-31 |  |
| G-205 | Coffres : animation dans le bon sens, orientés vers le joueur (02:12) **03/11 16 h 47** : sens d'ouverture OK (D-192). | coffres | **clos (03/11, 16 h 47)** | D-42 |  |
| G-206 | Plein écran exclusif supprimé ; plein écran / fenêtré par Alt+Entrée et F11 ; interrupteur dans les options (02:12) **03/11** : F11 / Alt + Entrée OK. | fenêtre2 | **clos (03/11)** | D-30 |  |
| G-207 | Nom de Ragnar « trop bas, t'en penses quoi ? » (02:12) : demande d'avis **03/11** : « Non c'est bon ». | options | **clos (03/11, D-185)** | D-43 |  |
| G-208 | Souris inutilisable ~1 s après le clavier (02:12) | entrées | traité (#43) | D-44 |  |
| G-209 | F1 en haut à droite par défaut (02:14) | entrées | traité (#43) | D-45 |  |
| G-210 | Option « Lissage des textures » supprimée, lissage toujours actif (02:27) | fenêtre2 | traité (#43) | D-46 |  |
| G-211 | `camera_centree` activée par défaut (02:29). **Clos par #47** : l'option « Centrer la caméra sur le joueur » est supprimée, la caméra est toujours centrée tant que le joueur l'a (`fenetre.py:1171-1172`) ; les clés `camera_centree` et `suivi_camera_v` sont dans `CLES_OBSOLETES` (`reglages.py:99-100`). Le `reglages.json` de Sylfried n'a donc plus d'effet sur ce point. Le lissage des textures est lui aussi toujours actif (option retirée) | #47 | **clos** | [établi] | D-47 |
| G-212 | « Vitesse de l'accélérateur » → « Multiplicateur de l'accélérateur » (02:35) **03/11 16 h 47** : le multiplicateur de l'accélérateur reste (D-201). | combat | traité (#43) | D-48 |  |
| G-213 | Vitesse des combats x1 / x2 / x3 (libellés Normal > Rapide > Très rapide), en combat et dans Commandes sous les lignes de l'accélérateur, non accélérable par l'accélérateur (02:35) **03/11 16 h 47** : l'accélérateur reste (D-201), la vitesse de combat aussi. | combat | traité (#43) | D-49 |  |
| G-214 | Précision (02:37) : le changement de vitesse du combat change la vitesse des **animations et des dialogues, mais PAS celle de la musique ni des bruitages** | combat | traité (#43) | D-18 |  |
| G-215 | Historique des messages avec l'indication de qui a parlé (nom, « message général », « une femme dans une grotte », « un soldat dans le château de Bastione », « un objet récupéré dans une jarre ») (02:36) | histo + libelles | traité (#43), vu OK le 03/11 | D-17 |  |
| G-216 | **Audit complet** : fonctionnalités absentes (casino, églises, banque…), menus, interrupteurs, variables, PNJ, scripts, avec classement décision / oubli / bug (02:12) **03/11** : rapport « ce qu'il reste » : `rapport_reste_a_faire.md`. | cet audit + couverture | traité (#44) | D-16, D-19 |  |

Sylfried a interrompu le travail de la session principale à 02:37:30 et 02:38:07 (heure locale ; la transcription, en UTC, dit 01:37:30Z et 01:38:07Z : « [Request interrupted by user] »). Ses messages de 02:37 et 02:38 précisent la vitesse du combat et confirment « tout doit être prit en compte depuis mon message envoyé à 2h12 ».

## K. Les 10 lacunes les plus graves pour la jouabilité (classement de lecture)

1. **G-092** boutiques (achat / vente / quantité) : jamais jouées, aucune sauvegarde de test n'y mène.
2. **G-120** sauvegarde réelle à l'église puis rechargement : jamais confirmée sous Windows (issue #9, prio:haute) ; liée à G-123 (originaux intacts).
3. **G-093** casino, banque, église (confession), mini-jeux : aucun test documenté (à trancher par l'agent couverture).
4. **G-031** autres moyens de transport (bateau, ballon) : jamais étudiés ; sans eux la progression de l'aventure est suspendue.
5. **G-001 / G-023** rendu Windows / GPU réel jamais vérifié, aucune comparaison avec le mobile.
6. **G-044** allocateur sans libération : arrêt `MemoryError` possible sur longue session.
7. **G-070, G-071, G-078** boss, groupes de monstres, effets de sorts, victoire / montée de niveau / game over : non vérifiés.
8. **G-041, G-042, G-043, G-052, G-069** scènes d'histoire (FEAN, poses couchées, teinte, auberge, chapitres, générique) non rejouées.
9. **G-055** murs invisibles et escalier de `dbout` : risque de blocage ; **G-079** retour au titre depuis un combat ou une boutique puis nouvelle partie sans relancer non vérifié.
10. **G-099 / G-098** nom (refusé, clavier inventé), sexe à la manette ; effacement de la sauvegarde auto par « Revenir à l'écran titre ».

Déjà dans le lot en cours (§J) : G-058 (coffres), G-059 (dragon), G-097 (sauvegarde auto), G-105 (souris), G-111 (priorité du jeu), G-114 à G-118.

## L. Volumes (comptés par script sur ce fichier)

- **161 lignes numérotées** : 144 lacunes (sections A à I) + 17 demandes du lot en cours (§J, G-200 à G-216).
- Statuts des 144 lacunes : ouvert 111 (dont 4 « volontaire » et 4 « limite »), traité à reconfirmer 15, traité 3 (dont 1 en partie), en cours 11, obsolète ou probablement obsolète 3, autres 1 (en pause).
- Classement provisoire (un tag principal par ligne ; une ligne en porte parfois deux) : **[à vérifier] 97, [oubli] 19, [décision] 17, [bug] 12**. La grande part de « à vérifier » vient de l'absence de test Windows/GPU et de capture du mobile : ce n'est pas un jugement de gravité.
- Recherche de marqueurs dans le code (`TODO`, `FIXME`, `NotImplemented`) : aucun (établi).
