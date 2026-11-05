### 3.3 Les lacunes les plus graves pour la jouabilité, classées

*Mise à jour du 04/11/2026 : les points 1 (poker), 2 (machine à sous au clavier), 4 (teinte), 5 (poses couchées), 6 (bestiaire) et 8 (échelle des sprites) sont traités ; le point 9 (sons) l'est en partie (échecs de lecture notés dans le journal, #222). Restent : 5 (animations d'événement, paquet 6), 7 (ballon, effets d'écran 3, 5, 6), 3 (blocs de progression jamais joués : à valider sur Windows).*

1. **Poker invisible** (cartes et table) : Établi, GL + cause + preuve par contournement (§3.1.4).
2. **Machine à sous injouable au clavier** (mise réglable à la souris seulement) : Établi, GL (§3.1.2).
3. **Boutiques, banque, église (résurrection, sauvegarde), arène, véhicules : jamais joués** : Inconnu, ce sont les blocs de progression. Aucun test automatique n'ouvre ces fenêtres (seul le type 12 apparaît au chargement). C'est la plus grande zone sans information.
4. **Paquet 33 (teinte de carte) ignoré sur 171 cartes sur 529** (jour, soir, scènes teintées, marais, carte du monde) : Établi côté moteur, effet visuel Supposé.
5. **Poses couchées (16, 17, 18) et animations d'événement (6) non gérées** : scènes d'auberge, dormeurs, événements ; Établi (aucune branche), 3 cartes au chargement + scripts.
6. **Bestiaire** : liste et fiche (texte) affichées, mais le monstre n'est pas dessiné et l'église `mak1f1` apparaît dans son cadre (Établi : `gl_booksel_b330.png` ; cause non trouvée).
7. **Ballon (30) et effets d'écran 3, 5, 6 (34)** : Établi (non gérés).
8. **Échelle des sprites (paquet 13, bit 0x800) jetée** : Établi ; effet Supposé (`mlb1a` 0,738, `ev07` 0,952).
9. **Sons** : 12 `except: pass` dans `sound.py`, un son illisible disparaît sans trace ; Non vérifié (je n'ai pas lancé le décodeur sur les 686 fichiers).
10. **`g_Option + 5` écrit dans les sauvegardes** quand l'option « défilement » est imposée (Supposé) : §4, ligne 5.

---

## 4. Tout ce que la visionneuse écrit dans la mémoire du moteur

Méthode : `grep -n "mem_w(\|mem_write\|hook_add\|reg_write\|pack_into" dq4_pc/*.py` (hors `emu_core.py`, qui est le moteur d'émulation lui-même). Il n'y a **que 16 sites d'écriture**, tous listés ci-dessous. Verdict global (Établi) : **aucune écriture ne touche un drapeau de scénario, une variable d'événement, l'or, l'inventaire, la position du héros ou une pièce de casino.** Les seules données de jeu écrites sont des **options** (`g_Option + 5`) et des **vitesses de marche remises à leur valeur d'origine**.

| # | Où | Quoi | Quand | Verdict |
|---|---|---|---|---|
| 1 | `engine.py:350` | `G_IS_AMAZON = 1` (octet de la bibliothèque) | une fois, après `GameInit` | **Légitime** : retire la case « Sauv. cloud » du menu de départ (le jeu fait pareil pour la version Amazon). Aucun effet sur la partie. |
| 2 | `engine.py:367, 373, 376` | crochets de code `UC_HOOK_CODE` sur `MenuPort::SetVisible`, `FieldData::drawBlock`, `FLDObject::SetCommonAnimation` | à chaque appel | **Lecture seule** (ils notent un registre). Légitime. |
| 3 | `engine.py:398-399` | écrit le registre `x8` dans `ui_MsgLoop` (lettres par image) | chaque image de texte, seulement si la vitesse du texte ≠ 4 | **Légitime** (réglage de la visionneuse « vitesse du texte »). Garde : vérifie l'instruction d'origine (`SXTH_W20_W8`), sinon ne fait rien. |
| 4 | `engine.py:407` | crochet sur `OptionStatus::setBattleSpeed` | quand le joueur change l'option dans les Paramètres d'origine | **Lecture seule** (rappel). |
| 5 | `engine.py:423, 427, 434` | écrit `status::g_Option + 5` (vitesse de défilement des messages de combat) à chaque image | tant que l'option « défilement » de la visionneuse est imposée ; remise de la valeur d'origine quand on la lâche | **Légitime mais à surveiller** : cette valeur fait partie de `OptionStatus`, donc **elle est écrite dans les sauvegardes** du jeu (notes-technique:241). Une partie sauvegardée pendant que l'option est imposée garde la valeur imposée. Pas un drapeau de scénario. Supposé : effet sur la sauvegarde (non essayé). |
| 6 | `engine.py:441-453` (`_elargir_symboles`) | trois constantes immédiates de `FieldData::drawSymbol` portées à 1600 | une fois à la création du moteur | **Légitime** (affichage des lieux de la carte du monde en 16/9). Garde : le motif d'instruction est vérifié avant l'écriture. Mineur : `etats.appliquer` (`savestates.py:46`) remet l'image d'origine de la bibliothèque ; le patch revient avec les pages modifiées de l'état, mais **un état enregistré avant l'existence du patch le perd** (`savestates.py:60-61` ne ré-applique que `remettre_vitesses` et `patcher_parametres`). |
| 7 | `engine.py:465` (`patcher_parametres`) + crochet `engine.py:474` | `cmp w8, #7` → `cmp w8, #4095` dans `TownMenu_OPERATION_ROOT::menuUpdate` | à la création + après chaque chargement d'état | **Légitime / décision** : le bouton « Paramètres » ouvre le menu Pause de la visionneuse. **Conséquence** : la fenêtre de réglages d'origine (type 27 : volumes, vitesse, taille de la croix, « Revenir à l'écran titre ») n'est plus jamais ouverte ; `Moteur.retour_titre` rejoue le retour au titre. |
| 8 | `engine.py:484` (`_creer_canevas`) | tampon de paramètres de message (largeur, hauteur du canevas) puis appel direct de `SDrawCTRL::CanvasSetup` | une fois | **Légitime** (Unity le fait par un message de port). |
| 9 | `engine.py:516` (`remettre_vitesses`) | vitesses de marche (`TownPlayerAction::walkSpeed/walkSpeed2`, `FieldPlayer::Speed`, deux constantes à `0x27520c/0x275210`) remises aux valeurs d'origine | chargement d'un état | **Légitime** : répare un état enregistré par une ancienne version pendant une course. La course elle-même accélère l'horloge, pas ces valeurs (`engine.py:508`). |
| 10 | `engine.py:547` (`_drapeau_effet`) | bit 1 du mot de drapeaux de sortie (`outp[0]`) | pendant un effet d'écran (début de combat ; voyage, lampe et Riremito depuis #256) | **Légitime** (émule `Capture.ScreenEffect`). Risque : si le bit n'était jamais baissé, le moteur attendrait ; la fenêtre le borne (`ATTENTE_CHARGE_MAX`). |
| 11 | `engine.py:577` | bit 0 du mot de drapeaux de sortie (`outp[0]`) | chaque image | **Légitime** (émule `Fade.FadePlane.CheckFade` : « un fondu est en cours »). Établi par les notes (`notes-technique:61`). |
| 12 | `engine.py:673, 709` | tampons de messages Unity → moteur (`buf1/buf2`) | à chaque touche / clic de menu | **Légitime** : c'est `MenuPort.Send`. Seules les actions du joueur y passent. |
| 13 | `engine.py:742` (`_finir_anims`) | efface le bit 0 de l'état d'une animation d'objet de carte (`table + idx * 32 + 0x14`) après une durée | après un paquet 5 (porte, coffre, jarre) | **Légitime** (émule le rappel « animation finie » d'Unity). **Risque** : la durée est estimée (`duree_anim` lue dans les données, sinon `DUREE_ANIM` constante) ; une durée fausse libère trop tôt ou trop tard un script qui attend la fin d'un coffre ou d'une porte. Pas un drapeau de scénario. Supposé exact. |
| 14 | `savestates.py:46-50` (`appliquer`) | réécrit toute la mémoire du moteur (image de bibliothèque, tas, données, TLS) | chargement d'un état `.dqs` demandé par le joueur | **Légitime**. L'état vient du joueur ; la version est vérifiée (`VERSION`). |
| 15 | `engine.py:60-64` (`h_fclose`) | l'écriture des fichiers de sauvegarde du moteur est redirigée vers `--saves-ecriture` | à la fermeture d'un fichier | **Légitime** : les vrais fichiers lus (`--saves-lecture`) ne sont pas modifiés (Établi par la lecture du code : `engine.py:41, 53` écrit toujours dans `dossier_ecriture`, les originaux ne sont ouverts qu en lecture ; non vérifié par somme de contrôle). |
| 16 | `pktlog.py:11-14` | crochets mémoire / code qui **lisent** le tampon de paquets | chaque image | **Lecture seule**. |

**Ce qui n'y est pas** (Établi par absence dans le `grep`) : aucune écriture d'or, d'objets, de niveau, de position du héros, de drapeau de coffre, de variable d'événement, d'état des PNJ. Les sondes de ce rapport (500 jetons en `joueur + 0x2e8`) sont des **écritures de mon moteur de test**, pas du code de la visionneuse.

---

## 5. Plan du balayage des cartes (phase suivante)

**Parc réel** : 529 fichiers `.stg` dans `split_UnityDataAssetPack.apk` (`assets/map/`) = 520 villes / donjons / tours + 9 cartes d'événement `ev01`-`ev09` (le « 518 » de la consigne est un ancien décompte ; 523 cartes sont déjà en cache `carte8_*.pkl`, `ev02`-`ev09` s'extraient à la demande en ~5 s la première fois). Il y a aussi des décors de combat `btl_pl_*` (hors `.stg`).

### 5.1 Trois niveaux, du moins cher au plus cher

| Niveau | Quoi | Outil | Coût mesuré / estimé | Parallèle |
|---|---|---|---|---|
| **N1** moteur seul (déjà fait en version 90 images) | `Global::startTown(nom)`, N images, relevé des paquets, sprites, ports, fondus, sons, plantages | `/tmp/audit/balayage.py DEB FIN IMAGES SORTIE.json` | **Mesuré** : 529 cartes × 90 images = **123 s** en tout (0,23 s / carte, 1 moteur recréé) sur la machine chargée (charge ~3 sur 2 cœurs). **Estimé** 600 images : ~14 min en 1 processus, **~7 min en 2** | oui, 2 processus (§5.3) |
| **N2** moteur + interactions | pour chaque PNJ / coffre / porte / escalier de la carte : poser le héros à côté, appuyer sur « parler » (`step(0, 0x100)`), appuyer sur A tant qu'un message est visible, relever les fenêtres ouvertes (types), les paquets non gérés (§1), les plantages, les messages bloqués (> 1500 images), les boucles de menu | à écrire (`balayage_n2.py`) sur la base de `hl.py` et des sondes `probe_*.py` | **Supposé** ~6 s / carte (≈ 8 PNJ × 300 images) → **~50 min en 1 processus, ~25 min en 2**. Non mesuré. | oui, 2 processus |
| **N3** capture GL de la visionneuse | un seul processus `window.py` qui enchaîne les cartes (technique de `/tmp/audit/gl_casino.py` : on enveloppe `Jeu.tick` pour appeler `demarrer_ville(nom)` toutes les N images et on capture au milieu) | à écrire ; verrou `flock /tmp/xvfb.lock` | **Supposé** 4 à 6 s / carte (carte déjà en cache, 1280 x 720, Mesa) → **35 à 55 min**, plus ~2 min de préparation du cache au premier passage. Un lancement complet de la visionneuse avec deux captures prend de l'ordre de la minute (non chronométré avec précision ; démarrage du moteur et préparation du cache compris) | **non** : un seul xvfb à la fois (2 cœurs) ; ne rien lancer d'autre en même temps |

### 5.2 Sorties par carte

- N1 / N2 : un JSON par carte dans `/tmp/balayage/n1/<carte>.json` (le fichier global `bal2_tout.json` a le bon format, 411 Ko pour 529 cartes). Champs : `ok`, `exc` + `tb` (plantage), `pkts` (comptes par type), `vals` (valeurs distinctes des types rares), `f13`, `echelles`, `cams`, `bgm`, `se`, `modeles`, `fbx`, `sprites` (id + position finale + visible), `cam`, `ports` (type des fenêtres ouvertes), `msg`, `fondu`, `drapeaux`, `partie`, `t`.
- N3 : `/tmp/balayage/n3/<carte>_a.png` (image 60) et `_b.png` (image 180), plus un petit JSON (temps de chargement, nombre de groupes de la carte, message de journal).

### 5.3 Découpage en deux processus

`sweep.py` prend déjà `DEB FIN`. Deux processus sur les 2 cœurs : `python3 sweep.py 0 265 600 /tmp/balayage/n1_a.json` et `python3 sweep.py 265 529 600 /tmp/balayage/n1_b.json`. Chaque processus crée son propre moteur (`hl.nouveau(tag)` avec `tag = 'bal2_<DEB>'` → dossier d'écriture `/tmp/sv_audit_bal2_<DEB>`), donc pas de conflit. Le script **recrée le moteur et recharge la sauvegarde après chaque plantage** (sinon tout ce qui suit échoue en cascade : c'est ce qui a rendu inutilisable le premier balayage `bal_tout.json`). N3 passe seul, après N1 et N2.

### 5.4 Outil de détection (`/tmp/audit/analyse.py`, à étendre)

Règles appliquées au JSON, avec le résultat **déjà obtenu** sur les 529 cartes (90 images) :

| Règle | Source | Résultat actuel (Établi) |
|---|---|---|
| R1 plantage du moteur | `exc` + PC / symbole | **1 / 529** : `ev01` (`TownCharacterManager::setRotate` + 0xc, déréférencement nul, depuis `TownOpeningManager::draw`). **Supposé** : artefact (la carte est lancée hors du flux du titre), car la visionneuse la charge sans problème par le titre (son journal affiche `carte ev01 : 11 groupes` à chaque lancement). |
| R2 paquets non gérés (§1) | `pkts` | 33 : **171 cartes** ; 16 : 3 ; 17 : 1 ; 6, 18, 30, 34 : 0 (se déclenchent par événements, ce que N2 doit atteindre) |
| R3 sprite sans feuille | `sprites[*].id` contre `feuilles_datapack.json` | **0** : les 93 identifiants distincts ont tous une feuille `h<id>` dans le datapack (155 feuilles). Note : 98 feuilles seulement dans le cache `/tmp/uicache4` ; les 57 autres s'extraient à la demande. |
| R4 sprite jamais positionné | `sprites[*].pos is None` | **6 cartes, 8 sprites** : `ev07` (127, 135, 7), `mlb1a` (7), `mlout1` (174), `mom2f1` (0), `mqtf3` (157), `msm1f1` (24). **Supposé** : personnages cachés par script, à regarder en N2. |
| R5 sprite hors de la carte | `sprites[*].pos` contre les sommets de `carte8_*.pkl` (marge 3) | **237 sprites au départ**, dont **235 = héros / équipier à la position héritée (1,97 ; 0,047 ; 44,08)** sur 117 cartes : `startTown(nom)` **ne place pas le héros à l'entrée de la carte** (il garde la position de la carte précédente). Les 2 autres : `mnf2n1` (héros à (-7,95 ; -2,6), un peu hors du sol). **Aucun PNJ n'est hors carte** sur 507 cartes analysées. |
| R6 modèle / fbx absent | `modeles`, `fbx` | maillages 319 et 325 : textures `m319`, `m325` présentes ; fbx 1017 : extractible (`Donnees.modele_fbx`, dictionnaire de maillages). **0 manque.** |
| R7 messages / fenêtres inattendus au chargement | `msg`, `ports` | 4 cartes avec un message visible, 1 avec un port ouvert (type 12, titre de chapitre). Rien d'anormal. |
| R8 fondu non fini | `fondu` | 0 carte |
| R9 BGM / SE inconnus | `bgm`, `se` | BGM 2, 14, 16, 17, 18, 21, 22, 23, 24, 26, 29, 16384 (arrêt) ; SE 305, 308, 309, 1156. **Non vérifié** : existence des fichiers `.akb` correspondants (686 fichiers dans `assets/sound`). |
| R10 (N3) image vide | histogramme de l'image | à écrire : plus de 97 % de pixels de la couleur de fond = scène non dessinée. **Aurait détecté** le poker (`ev04 : 0 groupes`, écran noir, §3). |
| R11 (N3) texture manquante | pixels magenta (255, 0, 255) ou carte à 0 groupe | à écrire |
| R12 (N3) régression | image perceptuelle contre le passage précédent | à écrire |

### 5.5 Ce que le balayage N1 ne voit pas (limites déclarées)

- Les événements scriptés (paquets 6, 16, 17, 18, 30, 34, FEAN, FEMV) : il faut N2 et des sauvegardes à différents points du scénario (le seul slot lu ici est celui du début, église `mak1f1`).
- Le rendu (tout ce qui est GL) : seul N3 le voit.
- La carte du monde (une seule « carte », `Global::startField`) et les combats (179 monstres `.dssa`, 163 caméras `.cam`) : à balayer à part (un monstre par groupe via `Global::startBattle`, caméra par caméra) ; non étudié ici. `Global::directStartBattle` n'a aucun appelant (outil de débogage), c'est peut-être le moyen le plus court : **Non vérifié**.
- L'entrée par la porte : tant que le héros n'est pas posé à l'entrée, les cartes sont vues depuis une position héritée. À résoudre avant N2 (piste : lire la position de départ de la carte dans la table des liens, `ExtraMapLink`, ou rejouer le lien depuis la carte voisine).

---

## 6. Ce que je n'ai pas pu vérifier

**Non vérifié, avec la raison et le moyen de le faire.**
1. **Boutiques, banque, église (résurrection, sauvegarde), auberge, arène, colisée, bateau, ballon, chariot, générique de fin** : aucune sauvegarde de test n'y mène (seul le slot 1 : début, église `mak1f1`), et leur ouverture passe par des commandes de script (`cmd_menu_shop`, `cmd_menu_save`, `cmd_menu_colosseum`, `cmd_menu_extra_shop`, `cmd_menu_nene`, `cmd_menu_hostage`, `cmd_menu_present_exp`, `cmd_menu_event_imuru`, `cmd_the_end`) qu'il faudrait déclencher avec un `CommandParameter` valide et l'objet `CommandWindow` (`changeShopMenuPhase(this, phase)` lit `this+0x10`), ou en posant le héros devant le marchand. J'ai essayé : trop long pour la fenêtre de l'audit. Piste : N2 (§5).
2. **Rendu sur le PC Windows réel** : toutes mes captures viennent de Mesa sous xvfb (G-001 / G-023).
3. **Effet visuel exact du paquet 33 et de l'échelle des sprites** : aucune capture du jeu Android à comparer (Supposé).
4. **Sons** : l'existence et le décodage des 686 `.akb` ; `sound.py` avale les erreurs.
5. **Poker jusqu'au bout** (échange de cartes, résultat, double ou rien) et machine à sous jusqu'à un gain : non jouées.
6. **Combats** : boss, groupes, effets de sorts, victoire, montée de niveau, game over (G-070, G-071, G-078).
7. **Carte du monde** : jour / nuit, marais, ballon, bateau.
8. **Types de fenêtres 5-7, 10, 11, 13-21, 33-42, 44-51, 56-65, 67-72, 74** : jamais vus ouverts dans une session (§2).
9. **Cartes placées à leur entrée** : `Global::startTown(nom)` garde la position du héros de la carte précédente (117 cartes sur 507 : héros et équipier à (1,97 ; 0,047 ; 44,08)). Ce que je vois est donc l'état « au chargement, héros mal placé », pas l'arrivée par une porte.
10. **`UnityInitTouchFlag`** (valeur 1 / 2 / 0 selon la partie) : effet côté Unity non étudié ; la visionneuse n'en tire rien.
11. **`ev01`** : plante si on l'appelle par `startTown` (§5.4 R1) ; je n'ai pas vérifié qu'il s'agit bien d'un artefact du lanceur (le chargement par le titre fonctionne).
12. **Les vraies sauvegardes de Sylfried** : je ne les ai ouvertes qu'en lecture ; aucune somme de contrôle avant / après.
13. **Mémoire** : allocateur sans libération (G-044) ; je n'ai pas mesuré la croissance du tas pendant le balayage (un moteur, 529 cartes, 1 recréation).

**Fichiers temporaires à ne pas garder** : `/tmp/audit/cache_donnees` (extraction des textures, 100 Mo environ), `/tmp/sv_audit_*` (sauvegardes jetables des sondes), `/tmp/audit/gl_*.png` (captures utiles, à garder), `/tmp/audit/rg_audit.json` (réglages jetables copiés de `/tmp/rg.json`).
