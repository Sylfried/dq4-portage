# Audit GitHub : issues et pull requests (agent « audit-github », lot PR #43)

> **Archive (03/11/2026)** : le dépôt `dq4-pc` **n'existe plus** (supprimé par Sylfried) ; ce fichier est désormais **la seule trace** de ses 43 issues et 36 pull requests, telles qu'elles étaient le 02/11/2026. Rien n'y sera fermé ni mis à jour : les §3 et §5 (« à fermer », recommandations) sont **sans objet**. Les restes qui comptent sont suivis dans `docs/audit/rapport_reste_a_faire.md`. Le suivi se fait par pull request dans `dq4-portage`.

Lecture seule. Rien n'a été écrit sur GitHub, dans le dépôt, dans le Projet claude.ai ni dans la mémoire.
Lu le 02/11/2026, `main` de `/home/claude/dq4-portage` = commit 08f5785 (PR #42 fusionnée).

**Révision à la reprise (02/11)** : le fichier du prédécesseur a été relu en entier et recoupé avec l'API REST et le code. Les comptes et la quasi-totalité des preuves sont confirmés. Corrigés : la ligne de la PR #36, la ligne de l'issue #10 (cadence 30 Hz), les numéros de ligne de l'issue #11, le détail des réglages de `dq4-portage` (§0) ; ajoutés : le §5 (recommandation par issue ouverte) et la liste des références documentaires périmées (§4). Rien n'a été écrit sur GitHub.

## 0. Périmètre, méthode, limites

**Dépôts de Sylfried vus par la session** (outil `list_repos`, 5 dépôts) :

| Dépôt | Visibilité | Lu ? | Contenu |
|---|---|---|---|
| `Sylfried/dq4-portage` | public | oui (REST) | version native sans Unity (le dépôt de travail actuel) : **0 issue, 42 PR** (toutes fusionnées en squash, 0 commentaire). Réglages établis par REST le 02/11 : issues **activées**, 10 étiquettes **par défaut de GitHub** (aucune des étiquettes `type:` / `zone:` / `prio:` de `dq4-pc`), **0 jalon**, **43 branches distantes** (`main` + 42 branches de PR jamais supprimées : `delete_branch_on_merge` = false), dernier push 02/11 00:40 UTC (PR #42) |
| `Sylfried/dq4-pc` | privé | oui (REST) | ancien dépôt, devenu historique : **43 issues** (27 ouvertes, 16 fermées) et **36 PR** (#38 à #79, toutes fermées) |
| `Sylfried/dq4-portage-unity` | public | **non** | piste 3 (Unity comme afficheur), en pause |
| `Sylfried/dq456-traductions-fr` | privé | **non** | patch FR |
| `linaben1/4BDAV-GROUP-ID` (5e de la liste) | public | non | sans rapport avec le portage (dernier push 2022), ignoré |

Les deux dépôts non lus renvoient « accès GitHub non activé pour cette session, utiliser add_repo ». Je n'ai **pas** appelé `add_repo` (audit en lecture seule, cela élargirait les droits de la session) et je n'ai pas contourné. Si Sylfried veut qu'ils soient audités, il faut l'autoriser explicitement. Le GraphQL est indisponible (jeton `GH_TOKEN` invalide en l'état) : tout vient de l'API REST limitée aux dépôts liés à la session.

**Ce qui sert de preuve** : le texte des issues, commentaires et PR (téléchargé en entier, 2 dépôts), puis un contrôle du code courant de `main` (greps en lecture seule, numéros de lignes cités). Étiquettes : **Établi** = lu dans le texte ou le code ; **Supposé** = déduit ; **Non vérifié** = nécessite Windows, un GPU réel, ou une capture du jeu mobile.

**Piège de lecture important** : les commentaires et les PR sont publiés sous le compte `Sylfried` mais **rédigés par Claude** (délégation git ; chaque commentaire se termine par « Generated with Claude Code »). Les phrases entre guillemets dans ces textes (« ça lag un peu », « il n'y a pas de son ») sont des **retours de Sylfried rapportés par Claude**, pas des copies de ses messages. Les heures GitHub sont en UTC ; l'heure locale de Sylfried (France) est UTC + 1 depuis le 25/10/2026.

## 1. Volumes

| | dq4-portage | dq4-pc |
|---|---|---|
| Issues | 0 | 43 : **27 ouvertes**, **16 fermées** |
| Pull requests | 42 (#1 à #42), toutes fusionnées | 36 (#38, #39, #42, #43, #46 à #55, #58 à #79), toutes « closed » (fusionnées dans le flux d'alors) |
| Jalons dq4-pc | | M0 Fondations (terminé), M1 Village jouable 16/9, M2 Monde et combats, M3 Son et finitions |
| Étiquettes | aucune issue | `type:feature/chore/bug/recherche`, `zone:rendu/interface/moteur/son/sauvegardes/outillage`, `prio:haute/basse` |

Numéros d'issues de dq4-pc : #1 à #37, #40, #41, #44, #45, #56, #57. (Les numéros #38, #39, #42, #43, #46 à #55, #58 à #79 sont des PR.)

**Constat majeur (établi)** : **le suivi d'issues est périmé**. Depuis la création de `dq4-portage` (30/10 23:06 UTC), aucune issue n'y a été ouverte ; les 42 PR « Avance #N » ne ferment aucune issue (le N est le numéro de l'avance, pas d'une issue). Les issues ouvertes de `dq4-pc` n'ont plus été mises à jour depuis le 30/10 ; plusieurs sont faites depuis (voir §3). `docs/historique.md` et `/home/claude/pjdocs/depot-github-dq4-pc.md` décrivent encore ce suivi.

**Anomalie documentaire (établi)** : les PR #9 et #10 de `dq4-portage` et le document de dépôt citent « l'issue #55 » (eau des villes, clignotements, lenteur au changement de carte par le puits) comme ouverte. Dans `dq4-pc`, #55 est la PR fermée « Docs : touche F9 » ; dans `dq4-portage` il n'y a aucune issue. Le suivi de ce sujet n'existe donc nulle part sous forme d'issue (il survit dans les notes et les corps de PR : eau des grottes PR #17/#19, puits/cache PR #10, clignotements PR #12/#20/#33).

## 2. dq4-portage : issues (aucune) et PR #1 à #42

Aucune issue (ouverte ou fermée). Voici ce que chaque PR a livré, avec ses restes déclarés par Claude (le « reste » est le texte de la PR, pas une vérification).

| PR | Date UTC | Titre court | Livré | Restes / non vérifié déclarés |
|---|---|---|---|---|
| #1 | 30/10 23:06 | Dossier `jeux\DQ4` du dépôt | `trouver_defauts`, variable `DQ4_JEUX`, message clair si APK absents | |
| #2 | 30/10 23:13 | Caméra des villes comme Unity | `SceneCamera.Update` reproduit, paquet 11 décodé, personnages de face, **suppression de la silhouette** (absente du jeu d'origine) | |
| #3 | 30/10 23:32 | Portes, jarres, tonneaux animés | paquets 2/3/4/5/7, FCAN/FPMV/FSEQ, `objets_carte.py`, cache `carte3` | lampes, bateaux, eau, événements FEMV (alors) |
| #4 | 30/10 23:38 | Lieux de la carte du monde en 16/9 | 3 constantes de `FieldData::drawSymbol` portées à 1600 px (**patch mémoire**), genres 19 et 20 ajoutés | |
| #5 | 30/10 23:45 | Survol souris dans les menus | survol = sélection comme les flèches | |
| #6 | 31/10 00:03 | Textes des boutons, boutons sombres, UI +12 % | ancrage TextMesh, tri par profondeur, `UI_ZOOM` | |
| #7 | 31/10 00:21 | Début de combat | effet de morceaux d'écran (`effet_combat.py`), poignée de main du mot d'état (paquet 34), écran noir | effets 3, 5, 6 non rejoués |
| #8 | 31/10 00:32 | Son : jingles, boucles | `0x1000 \| n` = PlayBGM avec reprise, 14 bruitages en boucle | « si un bruitage te manque, dis-moi » |
| #9 | 31/10 00:44 | Eau de la carte du monde | `Field.UpdatePattern` reproduit | « reste #55 » (introuvable, voir §1) |
| #10 | 31/10 01:04 | Cache en arrière-plan, fondus | `Donnees.preparer`, bit de fondu tenu jusqu'à la fin | **auberge et titres de chapitre non rejoués** |
| #11 | 31/10 01:05 | Docs | notes visionneuse | |
| #12 | 31/10 08:29 | Zoom commun, PP x1..x8, 30 Hz | boucle à pas fixe, interpolation, scintillements | |
| #13 | 31/10 09:00 | F2/F3 effectifs, décors suivent F2 | filtre net corrigé, caméra de combat vérifiée | |
| #14 | 31/10 09:16 | Décor de combat lissé, **pixel perfect par défaut** | `mode_sprites` 4 par défaut | |
| #15 | 31/10 10:01 | Menu Échap, réglages, touches, états | `pause.py`, `reglages.py`, `etats.py`, F2..F9 supprimées | Y/Select sans effet |
| #16 | 31/10 10:36 | Boîte de message en combat | langue du jeu réglée à l'extraction (`GetLangages`), `GENERATION` 2 | |
| #17 | 31/10 11:44 | Décor animé : eau, lampes, palettes | FPLP/FPAM, séquences/mouvements automatiques | **SRA, FEAN/paquet 6, clé de palette liée à un événement : non rejoués** |
| #18 | 31/10 14:59 | Menu, options, boutons mobiles, carte, dégâts, coffres | boutons à l'écran, fenêtre de carte, nombres de dégâts, options | pas de pad directionnel à l'écran (fait en #36), MAP_DIFF non reproduit, murs invisibles/escaliers de `dbout` |
| #19 | 31/10 15:18 | Eau des grottes, ombres | `fld_trans`, ombres des personnages | ombre sur la carte du monde non comparée au mobile |
| #20 | 31/10 15:42 | Vibration des monstres | cause : sommets partis au GPU avec un tour de retard | un seul combat étudié ; ordre de tracé latent |
| #21 | 31/10 16:24 | Réglages, ombres, grande carte, coffres | « aura » corrigée, grande carte du monde, `rotateXZY` pour le couvercle | **non résolu** : vagues d'eau sur le sol, murs invisibles `dbout`, clignotements |
| #22 | 31/10 17:25 | Signe de Y, touche Carte | `ChunkFile.readPosition` inverse Y | mêmes non résolus |
| #23 | 31/10 18:09 | Rendu net, interrupteurs | atlas à gouttière, filtre texels nets | zoom minicarte 400 % non reproduit |
| #24 | 31/10 18:36 | Halo des héros, états datés, menu noir, transitions, vignettage | `HD.VERSION` 3, transitions x2 | |
| #25 | 31/10 19:34 | Zoom au lancement, menu selon l'Excel | taille de fenêtre ramenée à l'écran | **non testable sur Windows** ; message du prêtre / « impossible de bouger » non reproduit |
| #26 | 31/10 20:22 | ZQSD, caméra aux flèches, zoom | nouvelles touches, Espace = action | marche à 8 directions ; Excel du menu non régénéré |
| #27 | 31/10 21:20 | Recentrage animé, menu noir | recentrage par le plus court chemin | survol « Rien » : bug non reproduit ; curseur doré oscillant inventé |
| #28 | 31/10 22:37 | Interfaces, clavier, caméra, carte du monde | éditeur d'interface (80 types), carte fantôme corrigée, course n'accélère que le héros | jambes de course, Alt Gr, code 4 de la carte non affiché |
| #29 | 31/10 22:39 | Docs | notes techniques | |
| #30 | 31/10 23:18 | Retours de 23 h 55 (13 demandes) | caméra centrée, menu États, éditeur, accélération caméra | compagnons à distance constante (essai) |
| #31 | 31/10 23:19 | Docs | notes compagnons/combat | |
| #32 | 01/11 00:15 | Retours de 00 h 33 (15 demandes) | infobulles, éditeur repliable, M en ville = liste des boutiques | non testé Windows |
| #33 | 01/11 01:22 | Retours de 01 h 31 | course, rencontres par distance, cartes | partiel |
| #34 | 01/11 11:30 | Retours de 11 h 34 | alliés (retour à la v1 de #30), carrés rouges, fin de combat, Divers | « fluidité non mesurée » |
| #35 | 01/11 13:16 | Retours de 13 h 08 | bouton Menu Échap, dernière boîte de combat, plume | ancrage plume/carrés non vérifié |
| #36 | 01/11 14:07 | Croix à l'écran | croix tactile d'origine, boutons à gauche | facteurs de taille « choisis » à l'époque ; **retirés ou prouvés lors de l'audit de fidélité de #39** : 1,25 / 0,75 et diamètre 165 inventés (NV:324), 1,225 / 1 / 0,775 lus dans le code d'origine (NV:323(3)) |
| #37 | 01/11 14:36 | Course sur toute l'horloge, Menu Pause | retour à la 1re version de la course | PNJ en mouvement, alliés monde, course x4 non mesurés |
| #38 | 01/11 14:39 | Confirmation pour quitter | « En êtes-vous sûr ? » | |
| #39 | 01/11 16:43 | Avant la partie + audit de fidélité | logos, titre, menu de départ, nom, licence, `GENERATION` 3 | **clavier du nom = celui du portage**, nom refusé, boutiques 58/60, sexe à la manette |
| #40 | 01/11 18:20 | Retours de 18 h 02 | menu centré, **Sauvegardes (export/import)**, licence, prologue, boîte violette | dialogues Windows non vérifiés, éclats d'épée, bandeau 225 supposé, paquet 33 |
| #41 | 01/11 21:26 | Retours de 20 h 46 (21 points) | avant-partie centrée, Pause, éditeur 54 entrées, `postfx.py`, police SE-GARRIR, Morph | **Windows/GPU réel entièrement non vérifié**, aucune capture du mobile |
| #42 | 02/11 00:40 | Retours de 23 h 24 | 3 modes de fenêtre, F11, Son, texte, dragon (`fbx.py`), crédits, caméra grenouille, bords des sprites | plein écran exclusif (**à retirer depuis le 02/11**, D-30), dragon vertical, bulle « ! », caméra du père, x3/x4 |

## 3. dq4-pc : les 43 issues, état réel dans le code actuel

Légende : **fait** / **partiel** / **pas fait** / **obsolète** / **indécidable**. « Preuve » = fichier:ligne de `/home/claude/dq4-portage` (dossier `dq4_pc/` sauf mention) ou PR.

### 3.1 Issues ouvertes (27)

| # | Titre | Étiquettes / jalon | Résumé | État réel | Preuve et commentaire |
|---|---|---|---|---|---|
| 2 | Menus : placement et style fidèles | feature, interface / M1 | gabarits Unity à retrouver, cadre et police du jeu | **fait** (à fermer) | gabarits lus du code d'origine : `outils/ui_il2cpp/entete.py:7` (`GENERATION = 3`), rendu `ui_menu.py` ; PR dq4-pc #68/#69 ; police SE-GARRIR (PR portage #41). Reste : classes `IBase` (G-090) |
| 3 | Sous-menus Objets / Magie / Carac. / Divers | feature, interface / M1 | listes, pages, grisés, curseurs | **en grande partie fait** | ce sont les menus du moteur rendus par `ui_menu.py` (72 types rendus sans exception, PR dq4-pc #68). **Non vérifié** : choix grisés (PM insuffisants), boutiques |
| 4 | Fenêtres à colonnes : magasins, liste des magasins, carte | feature, interface / M1 | colonnes, achat/vente, touche dédiée | **partiel** | liste des magasins via M : PR portage #32/#33 ; achat/vente (types 58/59, quantité 63) codés (PR #41) mais **jamais joués** (aucune sauvegarde de test n'atteint une boutique) |
| 5 | Messages : icône d'attente, Oui/Non, vitesse | feature, interface / M1 | ▼, Oui/Non, vitesse | **fait** (à fermer) | `pause.py:210,266,400` (page « Vitesse de défilement du texte »), `moteur.py:382-400` (crochet vitesse) ; ▼ et Oui/Non PR dq4-pc #69/#72 |
| 6 | Toits et décors qui cachent le héros | feature, rendu / M1 | transparence des toits | **obsolète par choix de Claude, à valider** | la silhouette a été supprimée (PR portage #2 : « absente du jeu d'origine ») ; la transparence des toits n'a pas été faite. Si le jeu d'origine n'a pas cette transparence, rien à faire ; **non vérifié sur mobile** |
| 7 | Animations réelles des portes et objets | feature, rendu / M1 | clips Unity, durée réelle | **fait** | `objets_carte.py:4-14` (FCAN/FPMV/FSEQ) ; PR portage #3, #17 ; coffres PR #18/#21/#22. Reste : **sens d'animation des coffres signalé le 02/11** (lot #43) |
| 8 | Manette et remappage des touches | feature, interface / M1 | manette, touches configurables | **partiel** | remappage fait (`reglages.py:6` `TOUCHES_DEF`, deux touches par action, PR portage #15). **Manette : pas fait** (aucune occurrence de `joystick`, `gamepad`, `pyglet.input` dans `dq4_pc/*.py`) |
| 9 | Sauvegardes : tester l'écriture réelle et la reprise | feature, sauvegardes, **prio:haute** / M1 | sauvegarde à l'église, rechargement, originaux intacts | **partiel, non vérifié** | écriture redirigée vers `--saves-ecriture` (`moteur.py:45-58`, `fenetre.py:333`) ; export/import (`sauvegardes.py:45,90`, PR portage #40 vérifié sous xvfb) ; états instantanés (`etats.py:66`). **Aucun document lu ne confirme une sauvegarde faite à l'église puis rechargée sur Windows** |
| 10 | Boucle à pas fixe 30 Hz | chore, moteur / M1 | cadence, dérive | **fait** (à fermer) | `fenetre.py:136` `PAS_MOTEUR`, `:2391-2394` ; PR portage #12 (394 pas en 13,13 s). Cadence du **moteur** à 30 pas/s : établie (`Boot` fixe `fixedDeltaTime = 1/30`, NV:105) ; cadence **réelle d'Unity pour les fondus** : supposée à 30 Hz (NT:209, NV:345(f)) |
| 11 | Allocateur bump 256 Mo | **bug**, moteur / M1 | épuisement mémoire | **pas fait** | `emu_core.py:292` (`HEAP_SIZE = 0x10000000`), `:370-371` (`raise MemoryError('tas epuise')`), `:616` `h_free` sans libération. Aucune mesure sur longue session trouvée |
| 12 | Python 3.15 sur pdc | chore, outillage / M1 | roues unicorn/pyglet/UnityPy/numpy | **indécidable** | `lancer_dq4.bat:15` liste 3.13, 3.12, 3.11, 3.14, 3.10 (pas 3.15). L'issue #26 dit pourtant « validé sur pdc (Python 3.15) » : à clarifier |
| 13 | Décoder les paquets restants | recherche, moteur / M2 | paquets 4, 6, 14, 18, 19-20, 24-25, 22, 32/33, 11, 33 | **partiel** | traités dans `moteur.py:100-190,607` : 0, 2-5, 7-15, 19-26, 28, 29, 31, 32, 34-37. **Absents de cette liste** (sous réserve d'un traitement ailleurs) : 1, 6, 16, 17, 18, 27, 30, 33. Voir G-040 à G-043 |
| 15 | Combats | feature, rendu+interface / M2 | décors, monstres, commandes, effets | **partiel, largement fait** | PR dq4-pc #46-#54, #62, #68-#71 ; portage #7, #16, #18, #20. Restes de l'issue : fond de ciel (fait PR #48), boss et groupes multiples, effets de sorts : **non vérifiés** (G-070 à G-081) |
| 16 | Modèles 3D : id de modèle -> asset | recherche, rendu / M2 | titre (8900), boss | **partiel** | dragon c1018 et crédits 8905 : `fbx.py` (PR portage #42). Boss et autres modèles : non vérifiés |
| 17 | Son : musique et bruitages | feature, son / M3 | `libsdlib_android.so` non étudiée | **fait côté code** (à fermer ?) | `son.py` (AKB, MS-ADPCM, boucle), PR dq4-pc #75, portage #8 ; menu Son à 5 catégories (PR #41/#42). Le rendu sur haut-parleurs « reste à vérifier sur le PC » (texte PR #75) ; le 01/11 01:44 Sylfried juge « le bouton par défaut du son c'est bon » (**supposé** : le son fonctionne chez lui) |
| 18 | Packaging : .exe sans contenu Square Enix | chore, outillage / M3 | PyInstaller | **pas fait** | aucun fichier de packaging dans le dépôt |
| 19 | Étendre l'approche à DQ5 et DQ6 | feature, moteur / M3 | réutiliser `emu_core.py` | **pas fait** (hors périmètre actuel) | à noter : Sylfried évoque « Nimzo dans DQ5 » le 02/11 02:12, donc l'intention existe |
| 20 | Ranger les scripts de recherche | chore, outillage / M1 | `disasm_dq.py`, `callers.py`... dans `outils/` | **partiel** | `outils/` contient `dump_il2cpp.py`, `ui_il2cpp/`, 8 `test_*.py` ; les scripts de désassemblage utilisés par les agents vivent dans `/tmp/specs/` (hors dépôt) |
| 21 | CI minimale | chore, outillage / M1 | GitHub Actions `py_compile` + fichiers interdits | **pas fait** | `.github/` ne contient que `ISSUE_TEMPLATE/` et `pull_request_template.md` (aucun workflow) |
| 22 | Retours de test sur pdc : lister les imperfections | **bug**, interface, prio:haute / M1 | liste vide « à compléter par Sylfried » | **obsolète** | remplacée de fait par les cycles « Retours de HH h MM » (PR portage #15 à #42). À fermer |
| 23 | Écran titre et nouvelle partie | feature, interface / M1 | démarrer sur le titre, créer une partie | **fait** | `avant_partie.py`, `saisie_nom.py` (PR portage #39-#42). Non vérifié : Windows |
| 24 | Affichage : plein écran, redimensionnement, ratios | feature, rendu / M1 | F11, ratios, taille des fenêtres, résolution interne | **partiel** | fenêtres `resizable=True` (`fenetre.py:272-277`), `ajuster_taille` (`:80`), 3 modes (`reglages.py:78` ; **à ramener à 2 : décision D-30 du 02/11**), échelle d'UI H/800, suréchantillonnage `postfx.py`. Crédits mesurés sur 1280x720, 1920x1080, 2560x1080, 1024x768 (PR #42). « Le décor ne montre pas le vide » en 21/9 et 4/3 : **non vérifié** |
| 40 | Performance : saccades sur pdc | **bug**, rendu, prio:haute | « ça lag un peu » | **fait mais jamais fermé** | commentaire : 60 i/s, pire image 18 ms, « à reconfirmer sur pdc, puis fermer » ; ensuite PR portage #10, #12, #20 |
| 41 | Sprites : xBR / ScaleFX réels | feature, rendu, prio:basse | algorithmes à voisinage large | **pas fait ; probablement obsolète** | `hd.py` n'a que EPX ; la décision du 01/11 retire « Régions lissées » et « Bicubique » (PR #41) |
| 45 | Carte du monde : finitions | (aucune) | horizon, eau, caméra, transports, autres villes | **largement fait** | eau PR #9, carte entière lue PR dq4-pc #70, caméra orthographique. Restes : bateau et autres transports, entrée par les autres villes, 3 emplacements non positionnés (G-030 à G-036) |
| 56 | Piste 1 : lire le code Unity d'origine | recherche, rendu, **prio:haute** / M2 | caméras, fenêtres, ordre de dessin | **largement fait** | PR dq4-pc #62, #68, #69, portage #2, #7, #16... Restes du commentaire du 30/10 : `BackColor`, `cmd_chara` en combat, `cmd_screen_effect`/`fade` |
| 57 | Piste 3 (essai) : Unity comme afficheur | recherche, rendu, prio:basse / M2 | pont Python -> Unity | **en pause, hors périmètre** | dépôt `dq4-portage-unity` (**non lu**) ; verdict de Sylfried le 30/10 16:25 : « l'expérience dans sa globalité ne ressemble pas à la version mobile » |

Commentaires notables (tous rédigés par Claude, sous le compte Sylfried) :
- #13 : « Carte du monde décodée (PR #43) : paquets 28, 12, 13, 29 » (30/10 10:11).
- #14 : retour de test pdc du 30/10 : « on ne peut pas sortir du village » (09:43), fermée à 10:10 par la PR #43.
- #17 : « il n'y a pas de son », « normal : libsdlib_android.so n'est pas encore étudiée » (09:43).
- #22 : « le rendu avance bien ; saccades ; pas de son ; sortie du village impossible ; demande de plusieurs styles de lissage » (09:43).
- #40 : mesures de Sylfried sur pdc après la PR #39 : 60 images/s, pire image 18 ms, moteur 2,0 ms, dessin 1,0 ms ; reste le lancement (fenêtre figée ~3 s) (09:49).
- #15 : liste « Reste à faire » du combat (10:40).
- #56 : avance et reste (15:43). #57 : verdict Unity (16:25), puis corrections (17:09).

### 3.2 Issues fermées (16)

| # | Titre | Fermée | État réel |
|---|---|---|---|
| 1 | Sprites HD : lissage par shader + MSAA | 30/10 09:49 (PR #39) | **fait** : `hd.py:68` EPX x8. Les « styles lissés » ont ensuite été retirés (PR portage #41). MSAA : `postfx.py`, non vérifié sur GPU réel |
| 14 | Sortir du village : carte du monde | 30/10 10:10 (PR #43) | **fait** (PR portage #4, #9, #12) |
| 25 | Cadrage du projet et décisions de départ | 30/10 | historique M0 (voir `decisions.md`, D-01 à D-06) |
| 26 | Voie A : chargeur ELF + Unicorn | 30/10 | **fait** (`emu_core.py`) ; 61 constructeurs, `DevInit`, etc. |
| 27 | Protocole moteur -> Unity décodé | 30/10 | **fait** pour l'essentiel ; restes = #13 |
| 28 | Démarrer le moteur sans Unity, charger une sauvegarde | 30/10 | **fait** ; l'écriture reste à tester (#9) |
| 29 | Lecture des données Unity | 30/10 | **fait** (`fld.py`, `donnees.py`) |
| 30 | Premier rendu (église) | 30/10 | remplacé par #31 |
| 31 | Visionneuse temps réel pyglet 16/9 | 30/10 | **fait** ; retour : « ça fonctionne » |
| 32 | Portes et changement de carte | 30/10 | **fait**, amélioré par PR portage #3 |
| 33 | Sprites nets : sharp bilinear | 30/10 | **fait**, refait en PR portage #13/#23 |
| 34 | Cadrage 16/9 du village | 30/10 | **fait**, refait en PR portage #2/#12 |
| 35 | Messages : texte français du moteur | 30/10 | **fait**, refait en PR dq4-pc #69 (fenêtre de message d'origine) |
| 36 | Menus : file MenuPort, saisie clavier | 30/10 | **fait** ; retour : « un peu mieux, mais pas mal d'imperfections » (-> #22) |
| 37 | Dépôt GitHub, règles de travail | 30/10 | **fait** (`docs/workflow.md`) |
| 44 | Carte du monde : icônes (paquet 29) | 30/10 11:33 (PR #47) | **fait** (genres 19-20 ajoutés par PR portage #4 ; genre 18 voir G-034) |

### 3.3 Pull requests de dq4-pc (36)

#38 historique ; #39 sprites HD (ferme #1) ; #42 délégation git ; #43 carte du monde (ferme #14) ; #46 combat décor/monstres ; #47 carte miroir et icônes (ferme #44) ; #48 fond de combat ; #49 filets des tuiles ; #50 icônes à l'endroit ; #51 combat décor tourné 180° ; #52 monstres sans clignotement ; #53, #55 docs ; #54 F9 ordre des parties ; #58-#60 outils IL2CPP ; #61 pont Unity preuve 1 ; #62 combat d'après le code Unity ; #63 table des 38 paquets ; #64 F1 cadre translucide ; #65-#67 piste 3 combat et pause ; #68 fenêtres et menus d'origine ; #69 message d'origine, plaques de monstres ; #70 carte du monde dézoomée ; #71 monstres en mode immédiat, fondus ; #72 souris = tactile, flèches ; #73 sprites cachés, bulles Riseup ; #74 pixel perfect ; #75 musiques et bruitages ; #76 docs ; #77-#79 piste 3 et lanceur (changement de PC, dépôt `dq4-portage-unity`).

Phrases de Sylfried rapportées dans ces PR (à ne pas confondre avec des citations directes) : « dézommer la map », « mieux upscale TOUS les sprites 2D » (PR #70, 30/10 ~19 h 44) ; « sprites à l'envers » (PR #50) ; combats « buggés » (PR #51) ; bande noire à l'horizon (PR #48) ; F1 avec cadre translucide (PR #64).

## 4. Ce que je n'ai pas pu établir ici

- Le contenu de `dq4-portage-unity` et `dq456-traductions-fr` (accès non activé, volontairement non contourné).
- Si des issues ont été supprimées ou transférées avant la création de `dq4-portage` : l'API ne le dit pas.
- Si les commentaires « Retour de test pdc » reproduisent fidèlement ses messages : ils sont rédigés par Claude.
- L'état Windows/GPU de toute fonctionnalité (aucun accès).
- Si les 43 branches distantes de `dq4-portage` contiennent autre chose que ce qui a été fusionné : non comparées à `main`.
- Le contenu du fichier `Menu_Echap_DQ4_PC.xlsx` (spécification de Sylfried citée par les PR #25 à #27) : absent du dépôt.
- Si le jeton GitHub de la session a le droit d'écrire (non testé, volontairement : audit en lecture seule).

**Références documentaires périmées sur le suivi (établi, lecture des fichiers)** :
- `README.md:23` : « `dq4-pc` (ancien) … issues et pull requests (#1 à #78) » ; les PR vont jusqu'à #79 et les issues jusqu'à #57.
- `README.md:24` : « Prochaine issue : #1 (sprites en HD) » alors que #1 est fermée depuis le 30/10 (PR #39 de `dq4-pc`) ; mêmes mots dans `docs/historique.md`, dont le tableau s'arrête au 30/10.
- `docs/workflow.md:6,27` : « description avec `Closes #<numéro>` », « branche supprimée après fusion » : aucune des 42 PR ne ferme d'issue et aucune branche n'est supprimée.
- `docs/notes-visionneuse-dq4-pc.md:85-86` : « Reste à faire : suivi dans les issues du dépôt » (G-145).
- `docs/notes-technique-portage-dq4.md:70` : « Lien id de modèle 3D (8900…) -> objet Unity : non résolu », vrai pour les boss et autres modèles, faux pour le dragon (c1018, PR #42). `NT:144-145` liste encore comme « à décoder » des paquets déjà traités.
- `/home/claude/pjdocs/depot-github-dq4-pc.md` (copie du document du Projet) : décrit `dq4-pc` comme dépôt actif.

## 5. Recommandations sur les 27 issues ouvertes de `dq4-pc` (rien n'a été fait)

Recommandation de lecture, à décider par Sylfried ; aucune issue n'a été fermée, ouverte ni commentée.

| Recommandation | Issues | Raison |
|---|---|---|
| **Fermer, c'est fait** (7) | #2 (sauf `IBase`, G-090), #5, #7 (sauf coffres : lot #43), #10, #23, #22, #41 | preuves au §3.1 ; #22 et #41 sont obsolètes (cycles « Retours de HH h MM » et retrait des shaders flous) |
| **Fermer après confirmation de Sylfried** (2) | #40 (« à reconfirmer sur pdc, puis fermer »), #17 (son : vérifier les haut-parleurs sur le PC) | le code est fait, la confirmation manque |
| **Garder ouvertes : reste réel** (16) | #3, #4, #8 (manette), #9 (**prio:haute**, sauvegarde réelle), #11 (allocateur), #12 (clarifier 3.15), #13 (paquets 1, 6, 16, 17, 18, 27, 30, 33), #15, #16, #18, #19, #20, #21, #24, #45, #56 | voir les lignes correspondantes du §3.1 et `lacunes_connues.md` (G-xxx) |
| **Garder, à décider** (2) | #6 (toits : le jeu d'origine les rend-il transparents ? silhouette retirée par Claude, D-93), #57 (piste Unity en pause) | dépend d'une décision de Sylfried |

Total : 7 + 2 + 16 + 2 = 27, soit les 27 issues ouvertes (vérifié contre la liste du §3.1).

**Suggestion de procédure** (non appliquée) : le suivi actif est dans `dq4-portage` (issues activées, aucune ouverte). Soit y recréer les restes réels avec les étiquettes `type:` / `zone:` / `prio:`, soit assumer le suivi par PR et corriger `workflow.md` et le README (G-140, G-149). Dans les deux cas, supprimer les 42 branches fusionnées.
