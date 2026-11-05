# Couverture fonctionnelle de la visionneuse DQ4 PC : audit en lecture seule

Date : 02/11/2026. Base : `main` 08f5785 (worktree `/home/claude/wt-audit`, branche `agent-audit`, aucun fichier du dépôt modifié, aucun commit).
Auteur : agent « couverture » (lot d'audit PR #43). Autre agent en parallèle : audit GitHub / décisions / lacunes déjà connues (`/tmp/audit/lacunes_connues.md`, `decisions.md`, `github_issues.md`).

## Synthèse (à lire en premier)

> **Mise à jour du 04/11/2026 (audit complet du jeu, domaines cartes, sprites, services, combat).** Ce document est un instantané du 02/11/2026 ; ce qui suit y est **périmé** (Établi, état de `main` au 04/11) :
> - §1 : les paquets 13 (échelle des sprites), 15 (ombres), 16, 17, 18 (poses couchées) et 33 (teinte de carte) sont **traités** par `Etat.appliquer`. Restent non traités : 6 (animations d'événement FEAN) ; 27 est contourné. *(Mise à jour du 04/11/2026 : 1 (sépia des retours en arrière, #254), 30 (zoom du terrain du ballon, #252) et 34 (valeurs 3, 5 et 6 : voyage, lampe, Riremito, #256) sont traités.)*
> - §3.1 : le **poker** (table et cartes dessinées), la **machine à sous au clavier** (colonnes ▲ ▼, A lance) et le **bestiaire** (monstre dessiné) fonctionnent : poker, machine à sous et bestiaire sont jouables et dessinés au clavier. Les parties 0xf et 0x10 sont gérées. Les constats de §3.1 et les lignes correspondantes de §2, §3.2 et §3.3 décrivent l'état du 02/11.
> - Véhicules : le bateau est découpé comme dans le jeu depuis #211 (cases de 40 × 40) ; le ballon en vol reste non vérifié.
> - Le palmarès complet de l'audit du 04/11 est dans `docs/audit/remaining_work_report.md` (section « Audit complet du 04/11/2026 »).

**Établi** (preuve citée dans le corps du document) :
- Sur 529 cartes chargées par le moteur seul (90 images chacune, 123 s en tout) : **528 sans plantage**, 0 sprite sans feuille de sprites, 0 PNJ hors de la carte (507 cartes analysables), 0 fondu bloqué. Le moteur parle donc bien à la visionneuse. Les trous sont ailleurs.
- **Quatre trous de jouabilité prouvés par une capture ou une trace** : (1) **poker** : table et cartes invisibles (`gl_poker_b330.png`) ; la cause est une garde de dessin réservée à la ville (`window.py:2913`), preuve par contournement (`gl_pokerv_b330.png` montre les 5 cartes) ; (2) **machine à sous** injouable au clavier, jouable à la souris (`gl_slotkb_b420.png` contre `gl_slotms_b350.png`) ; (3) **bestiaire** : le monstre n'est pas dessiné et l'église apparaît dans son cadre (`gl_booksel_b330.png`) ; (4) **paquet 33 (teinte de carte) ignoré sur 171 cartes sur 529**.
- **Huit types de paquets moteur sont ignorés sans aucune trace** : 1, 6, 16, 17, 18, 27 (contourné), 30, 33 ; le paquet 13 jette l'échelle des sprites ; le paquet 34 ne rejoue que l'effet n° 4 (§1). *(État du 02/11 ; au 04/11/2026, 1, 16, 17, 18, 30 et 33 sont traités et le paquet 34 rejoue aussi les valeurs 3, 5 et 6, #256.)*
- **Aucune écriture de la visionneuse dans la mémoire du moteur ne touche un drapeau de scénario, une variable, l'or, l'inventaire ou la position** (16 sites, §4). Seule option à surveiller : `g_Option + 5` (vitesse de défilement des combats), enregistrée dans les sauvegardes.

**Supposé** : l'effet visuel de la teinte (paquet 33) et de l'échelle des sprites ; que `ev01` ne plante que par le lanceur ; que les 8 sprites sans position sont cachés par script.

**Non vérifié** : tout le gameplay des boutiques, banque, église, auberge, arène, bateau, ballon, chariot et générique ; les combats complets ; les sons ; le rendu sur Windows (§6).

**Corrections à faire dans les notes** : l'inventaire « classes `IBase` non reproduites » est périmé ; le paquet 33 n'est pas limité à `mlb1a` ; les parties 0xf et 0x10 manquent (§7).

## 0. Méthode, légende, fichiers

**Légende (appliquée partout).**
- **Établi** : lu dans le code avec référence `fichier:ligne`, ou observé dans une exécution que j'ai lancée (moteur sous Unicorn, sans fenêtre, ou une capture GL), ou déduit d'un désassemblage que j'ai fait.
- **Supposé** : déduit du code ou d'un nom de fonction, jamais observé à l'écran. Chaque « Supposé » dit comment le confirmer.
- **Non vérifié** : je n'ai pas pu le regarder, ou il manque une donnée.

**Ce que j'ai fait (et pas fait).**
- Lecture : `engine.py` (décodage des paquets l.97-196, `Interface` l.230-331, crochets et patchs l.346-480, entrées l.570-610), `window.py` (entrées l.2515-2625, `_saisie_menu` l.1592-1623, dessin l.2793-2930), `ui_menu.py`, `savestates.py`, `data.py`, les deux fichiers de notes.
- Désassemblage du moteur `libdq4core.so` (outils `/tmp/specs/dasm_core.py`, `xref.py`) et de `libil2cpp.so` (`/tmp/specs/scripts/audit_dis.py`, il faut `DQ_IL2=/home/claude/il2`), graphe d'appels du moteur (`/tmp/audit/callgraph.py` → `cg.pkl`, noms démanglés).
- Exécutions **sans fenêtre** (Moteur Unicorn seul, `/tmp/audit/hl.py`) : balayage v2 des 529 cartes (123 s en tout), sondes du casino. Sept lancements GL de la visionneuse (casino, bestiaire), tous par `flock /tmp/xvfb.lock`, un seul à la fois.
- Les sauvegardes lues sont les vraies (lecture seule), toutes les écritures sont allées dans `/tmp/sv_audit_*`. Les 500 jetons des sondes du casino sont écrits dans la mémoire d'un moteur de test jetable, jamais dans une sauvegarde.
- **Pas fait** : jouer une boutique, une banque, une église, une auberge, une arène de monstres, un bateau ou un ballon (voir §6).

**Fichiers utiles (tous dans `/tmp/audit/`).**
- `coverage.md` (ce fichier).
- `sweep.py` (v2) + `bal2_tout.json` (529 cartes, 90 images chacune) + `analysis.py` (analyse du JSON) : outil de balayage et son premier résultat.
- `paquets_raw.txt` : émetteurs de paquets dans le moteur (scan statique), `menutypes3_raw.txt` : classes du moteur qui ouvrent chaque type MenuPort (1 à 80).
- `probe_slot3.py`, `probe_slot4.py` (machine à sous), `probe_poker2.py`, `probe_poker3.py`, `probe_grid.py` : sondes du casino. `gl_casino.py` + `run_gl_casino.sh` : lanceur GL d'essai (hors dépôt, appelle `fenetre.main()` après avoir lancé le mini-jeu).
- `callgraph.py`, `cg.pkl`, `scan_keyword.py` (lecteurs du mot de touches du moteur), `scales.py`.
- `feuilles_datapack.json` : les 155 feuilles de sprites `h<id>` du datapack.
- Captures GL (preuves) : `gl_poker_b330.png` (poker, écran noir) / `gl_pokerv_b330.png` (même scène avec l'affichage forcé en ville : les cartes apparaissent) ; `gl_slot_b330.png`, `gl_slotms_b350.png` (souris), `gl_slotkb_b420.png` (clavier) ; `gl_book_b230.png`, `gl_booksel_b330.png` (bestiaire). Journaux `gl_out_*.txt`.

---

## 1. Paquets moteur → visionneuse

Le moteur écrit un flux `[état, paquet…]` + un flux de flottants ; `Etat.appliquer` (`engine.py:97-196`) le décode. Le type = l'indice de `NativeManager.m_cmd_tbl` (38 entrées, `docs/technical-notes-dq4-port.md:78`). Les émetteurs viennent de `paquets_raw.txt` (scan des appels `UnityGetPacket` / `UnitySetPacket` / `UnitySetFade`…) complétés par le graphe d'appels. « Balayage » = nombre de cartes (sur 529, 90 images chacune après `Global::startTown(nom)`) où le paquet est apparu.

Lecture rapide : **traités** 0, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 14, 15, 19, 20, 21-26, 28, 29, 31, 32, 35, 36, 37 ; **partiels** 13, 34 ; **ignorés sans trace** 1, 6, 16, 17, 18, 27, 30, 33. *(Mise à jour du 04/11/2026 : 13, 15, 16, 17, 18 et 33 sont traités ; restent 1, 6, 27 contourné, 34 partiel ; **30 traité le 04/11/2026 (#252)** ; **34 traité le 04/11/2026 (#256 : valeurs 3, 5 et 6 ; durée réelle de l'effet 4 non vérifiée)**.)*

| Type | Nom Unity (`cmd_*`) | Émetteurs moteur | Traitement visionneuse | Statut | Balayage / remarque |
|---|---|---|---|---|---|
| 0 | `fld_load` | `FldStage::load`, `BattleStage::initialize` | `engine.py:100` (remise à zéro de l'état, nom de carte) ; carte chargée par `window.py:925` | Traité | 529/529 |
| 1 | `fld_color` | `cmd_map_effect_sepia` (5 scripts : `ccf2 ceout cmf3b ev07 srout`) | `Etat.sepia` depuis #254 | **Traité** | décor des villes en sépia jusqu'au chargement de carte suivant (shaders `Custom/fld_*_sepia` : gris pondéré + décalage, lus dans le paquet de données) ; les personnages gardent leurs couleurs. **Non vérifié** : un retour en arrière joué en vrai (fin de l'effet, matériaux `fld_transz` sans variante sépia). |
| 2 | `fld_alpha` | `FLDObject::SetMapObjAlpha` | `engine.py:138` → `objets_cmd` → `window.py:2244` | Traité | 6 cartes (`mnf1n1`, `mnf2n1`, `mrout`, `teout2`, `teout3`, `za1f1`) |
| 3 | `fld_pos` | `FLDObject::SetMapObjPosFX32`, `CasinoPoker::initialize` | `engine.py:140` | Traité | 8 cartes ; en poker, positions des cartes |
| 4 | `fld_rot` | `FldStage::setRotObjectUid`, `CasinoPoker::initialize` | `engine.py:142` | Traité | 2 cartes ; la machine à sous en envoie 684 par partie (rouleaux), observé en sonde |
| 5 | `fld_common_anim` | `FLDObject::SetCommonAnimation` | `engine.py:134` + fin d'animation simulée `engine.py:600-602`, `734-742` | Traité | 10 cartes |
| 6 | `fld_event_anim` | `FldStage::eventAnim` ← `cmd_map_animation` (scripts d'événements), `CasinoSlot::setBingoAnim`, `stopEventAnim`, `FLDObject::SetCameraNo` | **aucune branche** dans `Etat.appliquer` | **Non géré (ignoré en silence)** | 0/529 au chargement (déclenché par des événements). Reconnu par les notes (FEAN, `notes-visionneuse:83,141`). En sonde machine à sous : le résultat est calculé par le moteur, l'animation d'événement n'est pas jouée. |
| 7 | `fld_on_off` | `FLDObject::SetMapObjOnOff`, `SetMapUidOnOff` | `engine.py:136` | Traité | 18 cartes |
| 8 | `back_color` | `TownDataManager::setBackcolor/loadStage`, `__cmd_map_set_back_color` | `engine.py:102` | **Fait** (#111) : dégradé vertical haut / bas comme `BackColor.SetColor` ; aplat quand les deux couleurs sont égales (jour, intérieurs, combats, carte du monde : à confirmer sur Windows) | 529/529 |
| 9 | `fade` | `Global::fadeIn/Out*`, `__cmd_map_flash`, `startTown/startField/…` | `engine.py:132` + `Etat._fondu` + bit 0 du mot de drapeaux `engine.py:575-577` | Traité (deux plans, couleurs) | 529/529 |
| 10 | `camera` | `dss::Camera::send_unity` | `engine.py:144` (valeurs : 1 position, 2 cible, 4 rotation) | Traité | 528 cartes avec la valeur 3 ; valeurs 1 et 2 une fois |
| 11 | `camera_sub` | `BookCamera::initialize`, `TownEndrollManager::setup`, `TownMapEffect::setup`, `TownOpeningManager::setupCamera` | `engine.py:174` : bits 0, 1, 2, 4, 5, 7 | Traité ; **bits 3 et 6 non décodés** (jamais vus) | valeurs vues : 32, 2, 33, 34, 38 (toutes dans les bits décodés) |
| 12 | `chara_load` | `DisplayCharacter/SpriteCharacter::setup/cleanup` | `engine.py:113` | Traité | 529/529 |
| 13 | `chara` | `DisplayCharacter::draw`, `SpriteCharacter::draw` | `engine.py:190` : couleur 0x1000, position 0x2000/0x8000, pose/direction 0x4000 | **Traité depuis (mise à jour du 04/11/2026)** ; constat du 02/11 : bit 0x800 (échelle du sprite) lu puis jeté (`fl = fl[1:]`) | 528/529 cartes envoient le bit 0x800 ; valeurs de 0,022 à 1,435 ; la visionneuse dessine tout à `SPRITE_ECHELLE` = 0,045 (`window.py:106`). Voir §1.2. |
| 14 | `chara_on_off` | `BillboardCharacter/SpriteCharacter::setDisplayEnable` | `engine.py:116` | Traité | 5 paquets sur 3 cartes |
| 15 | `chara_shadow` | `SpriteCharacter::setShadowFlag`, `FieldBalloonDraw::draw`, `DisplayCharacter::draw` | `engine.py:118` | Traité | **0/529** au chargement : ombres affichées par défaut (`window.py:2876`), le moteur n'envoie rien en 90 images |
| 16 | `chara_sleep_pose` | `DisplayCharacter::draw`, `setSleepFlag` | **aucune branche** | **Traité depuis #45 (mise à jour du 04/11/2026)** ; constat du 02/11 : non géré | 3 cartes : `mlb1a` (valeurs 1280, 1281, 0x0c000100, 0x08000101), `mlm2f1` (1289), `taf1` (0x0c000208). Poses « couché » des personnages qui dorment. |
| 17 | `chara_sleep_near` | `cmd_set_sleep_near` | **aucune branche** | **Traité depuis #45 (mise à jour du 04/11/2026)** ; constat du 02/11 : non géré | `taf1` [1040, 1863] |
| 18 | `chara_pose` | `TownCharacterDraw::changePose` | **aucune branche** | **Traité depuis #45 (mise à jour du 04/11/2026)** ; constat du 02/11 : non géré | 0/529 (scripts) |
| 19 | `rise_icon_load` | `BillboardItem::draw/cleanup`, `FieldSystem::draw`, `TownPlayerEtc::draw` | `engine.py:126` | Traité | 14 cartes |
| 20 | `rise_icon` | `BillboardItem::draw`, `TownPlayerEtc::talk_icon_set_pos` | `engine.py:129` | Traité | 7 cartes |
| 21 | `mesh_load` | `DSSAObject::send_unity_load` (monstres, effets, logo, générique, poker) | `engine.py:149` | Traité | 7 cartes ; poker : 5 modèles |
| 22 | `mesh` | `Dssa_G3_BeginMesh` | `engine.py:181` | Traité (dessin **seulement en `PARTIE_VILLE` et combat**, voir §3 casino) | 1 carte (87 paquets) ; poker : 485 puis 450 par 90 images |
| 23-26 | `mesh_on_off`, `mesh_shader`, `mesh_color`, `mesh_tex_offset` | `DSSACharacter::SetShader`, `BattleEffectTransform`, `CommonEffectFlat` ; 23 : émetteur non trouvé | `engine.py:166-172` | Traité | 0/529 (combat) |
| 27 | `field_load` | `FieldData::setup/cleanup` | aucune branche | **Contourné** : la carte du monde est lue directement dans la mémoire du moteur (`_lire_monde`) | pas de paquet en ville |
| 28 | `field` | `FieldData::drawBlock` | `engine.py:104` | Traité | carte du monde seule |
| 29 | `field_symbol` | `FieldData::draw_symbol` | `engine.py:106` ; patch de la fenêtre des lieux `engine.py:508-` (§4) | Traité | carte du monde seule ; genres 19 et 20 dessinés, 18 = case vide voulue par le jeu (mise à jour du 04/11/2026 ; constat du 02/11 : non dessinés) |
| 30 | `field_scale` | `FieldData::setOffset` ← `FieldPlayerManager::balloonExec/downBalloon/rideBalloon/setScriptBalloon` ; `SpriteCharacter::setup` | `Etat.appliquer` (`champ_echelle`, `flottants`) depuis #252 | **Traité** | carte du monde en ballon : entier < 0 = `Field.SetScale` (hauteur visible du terrain × l'échelle, 1,00 à 1,25, multipliée par le zoom du joueur) ; entier >= 0 = `Field.SetFloatingObject` (le panneau du ballon, emplacement 12, grandit comme l'échelle et garde sa taille à l'écran). **Établi** (désassemblage `cmd_field_scale` D12794, `Field.SetScale` CD353C, `FloatingObject.SetScale` CD3708 ; le moteur envoie `(27, [1])` puis `(30, [12])` à chaque entrée sur la carte du monde, relevé sur la sauvegarde 4). **Non vérifié** : un vol réel (sauvegardes au chapitre 1). |
| 31 | `fbx_load` | `ModelObject::setup/cleanup`, `TownMapEffect::setup/cleanup` | `engine.py:154` + `window.py:1317` | Traité (**uniquement `SkinnedMeshRenderer` + shader `Custom/ImdChara`, animation non comprimée** : `data.py:328,340,355` lèvent une erreur et l'appelant ignore le modèle) | 4 cartes : `caf1`, `ev02`, `ev08` (libération), `ev07` (modèle 1017) |
| 32 | `fbx` | `ModelObject::draw`, `TownMapEffect::execute`, `TownModelDraw::setDisplay` | `engine.py:157` | Traité | 3 cartes, 37 paquets |
| 33 | `map_color_rate` | `FLDObject::SetRGBRate` ← `TownStageManager::loadStage/SetRGBRate` ← `cmd_set_timezone`, `__cmd_map_blend_init/color`, `CommonEffectLocation` ; `FieldData::setPaletteRate` ← `FieldStage::ChangeTime`, `FieldPlayerDoku::checkDokuDamage` | **aucune branche** | **Traité (mise à jour du 04/11/2026)** ; constat du 02/11 : non géré (ignoré en silence) | **171 cartes sur 529 au chargement** (voir §1.1) |
| 34 | `screen_effect` | `Global::SetScreenEffect` ← `NonBattleActionManager::execute` ← `FieldSystem/TownSystem::execute` | `Moteur._debut_effet_combat` (valeur & 0xf = 4, début de combat) et `Moteur._debut_effet_ecran` (3 voyage, 5 lampe, 6 Riremito, #256 ; rendu : `rendu/effets_capture.py`, `tabi_effect.py`, `lamp_effect.py`, `riremito_effect.py`, `fenetre/effets_capture.py`) | **Traité** (04/11/2026, #256 ; l'aspect à l'écran n'est pas comparé à l'original : Non vérifié) | 0/529 (déclenché en jeu) |
| 35 | `se_play` | `Sound::sePlayDirect`, `SoundManager::playSe` | `engine.py:187` → `sound.py` | Traité | 5 cartes, SE 305, 308, 309, 1156 |
| 36 | `se_stop` | `SoundManager::stopSeWithIndex` | `engine.py:187` | Traité | 0/529 |
| 37 | `bgm` | `SoundManager::play*/stop*` (12 appels) | `engine.py:187-189` ; ≥ 4096 = arrêt (`sound.py:80`) | Traité | 39 cartes au chargement ; 12 musiques distinctes (2, 14, 16, 17, 18, 21, 22, 23, 24, 26, 29) + 16384 (arrêt) |

### 1.1 Le paquet 33 en chiffres (nouveau, Établi)

Le moteur envoie la teinte de la carte (trois flottants r, g, b, 1,0 = neutre) à **171 cartes sur 529** dès le chargement :
- `(1,25 ; 0,65 ; 0,75)` sur 149 cartes : préfixes `ml`, `mm`, `mn`, `mo`, `mp`, `mq`, `mr`, `ms` (tous les villages), `ss` (41 cartes), `sj`, `sk`, `sh`, `ta` à `td`, etc. Teinte rouge-rosée (chapitres/heures du jour).
- `(1,30 ; 0,70 ; 0,55)` sur 20 cartes : toutes les `te*` (orangé).
- `(0,804 ; 0,807 ; 1,102)` sur `caf1` et `ev02`, valeur qui varie lentement (10 valeurs distinctes en 90 images : un fondu de teinte).
- Côté Unity (`cmd_map_color_rate`, RVA 0xD14E44, désassemblé) : il lit trois flottants et appelle `Field.SetColor(r, g, b, 1.0)` (carte du monde) ou écrit les trois valeurs dans l'objet de la carte (+0xd0, +0xd4, +0xd8). C'est une **multiplication de couleur sur le décor**. Établi.
- Effet visuel attendu : 32 % des cartes sont affichées sans la teinte du jeu d'origine. **Supposé** (jamais comparé à une capture Android). Le même paquet porte aussi le jour / la nuit de la carte du monde (`FieldStage::ChangeTime`) et la teinte de dégât de marais (`FieldPlayerDoku`) : ces deux cas ne sont pas vus en ville, ils sont à tester sur la carte du monde.
- Déjà connu des notes (`notes-technique:233` pour `mlb1a` seulement) ; l'étendue (171 cartes, 3 familles de valeurs) est nouvelle.

### 1.2 Autres valeurs et bits non décodés

- **Paquet 13, bit 0x800 (échelle du sprite)** : jeté (`engine.py:191`). Établi : 528 cartes l'envoient. Valeurs relevées sur 70 images : `mak1f1` et `ccf1a` 1,0 ; `mlb1a` 0,738 (héros et équipier) ; `ev07` 0,952. Sur 90 images, 18 cartes ont aussi la valeur 0,045 au tout début (`ca*`, `cb*`, `ccb*`) et 0,059 pour d'autres : probablement la valeur initiale avant la première mise à jour (non vérifié). La visionneuse force la taille des sprites (`HEROS_FRAC`, `window.py:124`). **Supposé** : sprites trop grands ou trop petits dans `mlb1a`, `ev07` et peut-être des scènes d'événements qui animent l'échelle ; à confirmer en jouant le prologue.
- **Paquet 10** : seules les valeurs 1 (position), 2 (cible) et 4 (rotation) sont décodées (`engine.py:144-148`) ; les autres bits sont ignorés (jamais vus : 1, 2 et 3 seulement).
- **Paquet 11** : bits 3 et 6 non décodés.
- **Paquet 34** : valeurs 3, 5, 6 non décodées.
- **Mot de drapeaux de sortie (`outp[0]`)** : la visionneuse écrit les bits 0 (fondu) et 1 (effet d'écran) (`engine.py:575-577`, `544-547`) et lit les autres (`drapeaux()`). Bit 3 (manette tactile) et bit 4 (limite TownCamera) : lus seulement pour l'affichage/la caméra. `UnityInitTouchFlag` est appelé par `TownSystem::initialize`, `FieldSystem::initialize`, `BattleSystem2::initialize`, `CasinoSystem::initialize`, `TownOpeningManager::setup`, `TownPlayerManager::checkMenuAction` : la visionneuse n'en tire rien (Non vérifié : effet d'une valeur différente sur le moteur).
- **`UnitySetString`** : aucun appelant direct dans le graphe d'appels (`callgraph.py up UnitySetString` ne renvoie rien) ; la visionneuse n'en lit pas le tampon. Supposé inutilisé.
