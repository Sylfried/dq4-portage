# Couverture fonctionnelle de la visionneuse DQ4 PC : audit en lecture seule

Date : 02/11/2026. Base : `main` 08f5785 (worktree `/home/claude/wt-audit`, branche `agent-audit`, aucun fichier du dépôt modifié, aucun commit).
Auteur : agent « couverture » (lot d'audit PR #43). Autre agent en parallèle : audit GitHub / décisions / lacunes déjà connues (`/tmp/audit/lacunes_connues.md`, `decisions.md`, `github_issues.md`).

## Synthèse (à lire en premier)

> **Mise à jour du 04/11/2026 (audit complet du jeu, domaines cartes, sprites, services, combat).** Ce document est un instantané du 02/11/2026 ; ce qui suit y est **périmé** (Établi, état de `main` au 04/11) :
> - §1 : les paquets 13 (échelle des sprites), 15 (ombres), 16, 17, 18 (poses couchées) et 33 (teinte de carte) sont **traités** par `Etat.appliquer`. Restent non traités : 1 (effet sépia des retours en arrière, 5 scripts), 6 (animations d'événement FEAN), 30 (zoom du terrain du ballon) ; 27 est contourné ; 34 est partiel (3, 5 et 6 non rejoués).
> - §3.1 : le **poker** (table et cartes dessinées), la **machine à sous au clavier** (colonnes ▲ ▼, A lance) et le **bestiaire** (monstre dessiné) fonctionnent : poker, machine à sous et bestiaire sont jouables et dessinés au clavier. Les parties 0xf et 0x10 sont gérées. Les constats de §3.1 et les lignes correspondantes de §2, §3.2 et §3.3 décrivent l'état du 02/11.
> - Véhicules : le bateau est découpé comme dans le jeu depuis #211 (cases de 40 × 40) ; le ballon en vol reste non vérifié.
> - Le palmarès complet de l'audit du 04/11 est dans `docs/audit/rapport_reste_a_faire.md` (section « Audit complet du 04/11/2026 »).

**Établi** (preuve citée dans le corps du document) :
- Sur 529 cartes chargées par le moteur seul (90 images chacune, 123 s en tout) : **528 sans plantage**, 0 sprite sans feuille de sprites, 0 PNJ hors de la carte (507 cartes analysables), 0 fondu bloqué. Le moteur parle donc bien à la visionneuse. Les trous sont ailleurs.
- **Quatre trous de jouabilité prouvés par une capture ou une trace** : (1) **poker** : table et cartes invisibles (`gl_poker_b330.png`) ; la cause est une garde de dessin réservée à la ville (`fenetre.py:2913`), preuve par contournement (`gl_pokerv_b330.png` montre les 5 cartes) ; (2) **machine à sous** injouable au clavier, jouable à la souris (`gl_slotkb_b420.png` contre `gl_slotms_b350.png`) ; (3) **bestiaire** : le monstre n'est pas dessiné et l'église apparaît dans son cadre (`gl_booksel_b330.png`) ; (4) **paquet 33 (teinte de carte) ignoré sur 171 cartes sur 529**.
- **Huit types de paquets moteur sont ignorés sans aucune trace** : 1, 6, 16, 17, 18, 27 (contourné), 30, 33 ; le paquet 13 jette l'échelle des sprites ; le paquet 34 ne rejoue que l'effet n° 4 (§1).
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
- Lecture : `moteur.py` (décodage des paquets l.97-196, `Interface` l.230-331, crochets et patchs l.346-480, entrées l.570-610), `fenetre.py` (entrées l.2515-2625, `_saisie_menu` l.1592-1623, dessin l.2793-2930), `ui_menu.py`, `etats.py`, `donnees.py`, les deux fichiers de notes.
- Désassemblage du moteur `libdq4core.so` (outils `/tmp/specs/dasm_core.py`, `xref.py`) et de `libil2cpp.so` (`/tmp/specs/scripts/audit_dis.py`, il faut `DQ_IL2=/home/claude/il2`), graphe d'appels du moteur (`/tmp/audit/callgraph.py` → `cg.pkl`, noms démanglés).
- Exécutions **sans fenêtre** (Moteur Unicorn seul, `/tmp/audit/hl.py`) : balayage v2 des 529 cartes (123 s en tout), sondes du casino. Sept lancements GL de la visionneuse (casino, bestiaire), tous par `flock /tmp/xvfb.lock`, un seul à la fois.
- Les sauvegardes lues sont les vraies (lecture seule), toutes les écritures sont allées dans `/tmp/sv_audit_*`. Les 500 jetons des sondes du casino sont écrits dans la mémoire d'un moteur de test jetable, jamais dans une sauvegarde.
- **Pas fait** : jouer une boutique, une banque, une église, une auberge, une arène de monstres, un bateau ou un ballon (voir §6).

**Fichiers utiles (tous dans `/tmp/audit/`).**
- `couverture.md` (ce fichier).
- `balayage.py` (v2) + `bal2_tout.json` (529 cartes, 90 images chacune) + `analyse.py` (analyse du JSON) : outil de balayage et son premier résultat.
- `paquets_raw.txt` : émetteurs de paquets dans le moteur (scan statique), `menutypes3_raw.txt` : classes du moteur qui ouvrent chaque type MenuPort (1 à 80).
- `probe_slot3.py`, `probe_slot4.py` (machine à sous), `probe_poker2.py`, `probe_poker3.py`, `probe_grille.py` : sondes du casino. `gl_casino.py` + `run_gl_casino.sh` : lanceur GL d'essai (hors dépôt, appelle `fenetre.main()` après avoir lancé le mini-jeu).
- `callgraph.py`, `cg.pkl`, `scan_keyword.py` (lecteurs du mot de touches du moteur), `echelles.py`.
- `feuilles_datapack.json` : les 155 feuilles de sprites `h<id>` du datapack.
- Captures GL (preuves) : `gl_poker_b330.png` (poker, écran noir) / `gl_pokerv_b330.png` (même scène avec l'affichage forcé en ville : les cartes apparaissent) ; `gl_slot_b330.png`, `gl_slotms_b350.png` (souris), `gl_slotkb_b420.png` (clavier) ; `gl_book_b230.png`, `gl_booksel_b330.png` (bestiaire). Journaux `gl_out_*.txt`.

---

## 1. Paquets moteur → visionneuse

Le moteur écrit un flux `[état, paquet…]` + un flux de flottants ; `Etat.appliquer` (`moteur.py:97-196`) le décode. Le type = l'indice de `NativeManager.m_cmd_tbl` (38 entrées, `docs/notes-technique-portage-dq4.md:78`). Les émetteurs viennent de `paquets_raw.txt` (scan des appels `UnityGetPacket` / `UnitySetPacket` / `UnitySetFade`…) complétés par le graphe d'appels. « Balayage » = nombre de cartes (sur 529, 90 images chacune après `Global::startTown(nom)`) où le paquet est apparu.

Lecture rapide : **traités** 0, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 14, 15, 19, 20, 21-26, 28, 29, 31, 32, 35, 36, 37 ; **partiels** 13, 34 ; **ignorés sans trace** 1, 6, 16, 17, 18, 27, 30, 33. *(Mise à jour du 04/11/2026 : 13, 15, 16, 17, 18 et 33 sont traités ; restent 1, 6, 27 contourné, 34 partiel ; **30 traité le 04/11/2026 (#252)**.)*

| Type | Nom Unity (`cmd_*`) | Émetteurs moteur | Traitement visionneuse | Statut | Balayage / remarque |
|---|---|---|---|---|---|
| 0 | `fld_load` | `FldStage::load`, `BattleStage::initialize` | `moteur.py:100` (remise à zéro de l'état, nom de carte) ; carte chargée par `fenetre.py:925` | Traité | 529/529 |
| 1 | `fld_color` | aucun émetteur trouvé (scan statique) | aucun | Non géré | 0/529. Supposé inutilisé. |
| 2 | `fld_alpha` | `FLDObject::SetMapObjAlpha` | `moteur.py:138` → `objets_cmd` → `fenetre.py:2244` | Traité | 6 cartes (`mnf1n1`, `mnf2n1`, `mrout`, `teout2`, `teout3`, `za1f1`) |
| 3 | `fld_pos` | `FLDObject::SetMapObjPosFX32`, `CasinoPoker::initialize` | `moteur.py:140` | Traité | 8 cartes ; en poker, positions des cartes |
| 4 | `fld_rot` | `FldStage::setRotObjectUid`, `CasinoPoker::initialize` | `moteur.py:142` | Traité | 2 cartes ; la machine à sous en envoie 684 par partie (rouleaux), observé en sonde |
| 5 | `fld_common_anim` | `FLDObject::SetCommonAnimation` | `moteur.py:134` + fin d'animation simulée `moteur.py:600-602`, `734-742` | Traité | 10 cartes |
| 6 | `fld_event_anim` | `FldStage::eventAnim` ← `cmd_map_animation` (scripts d'événements), `CasinoSlot::setBingoAnim`, `stopEventAnim`, `FLDObject::SetCameraNo` | **aucune branche** dans `Etat.appliquer` | **Non géré (ignoré en silence)** | 0/529 au chargement (déclenché par des événements). Reconnu par les notes (FEAN, `notes-visionneuse:83,141`). En sonde machine à sous : le résultat est calculé par le moteur, l'animation d'événement n'est pas jouée. |
| 7 | `fld_on_off` | `FLDObject::SetMapObjOnOff`, `SetMapUidOnOff` | `moteur.py:136` | Traité | 18 cartes |
| 8 | `back_color` | `TownDataManager::setBackcolor/loadStage`, `__cmd_map_set_back_color` | `moteur.py:102` | **Fait** (#111) : dégradé vertical haut / bas comme `BackColor.SetColor` ; aplat quand les deux couleurs sont égales (jour, intérieurs, combats, carte du monde : à confirmer sur Windows) | 529/529 |
| 9 | `fade` | `Global::fadeIn/Out*`, `__cmd_map_flash`, `startTown/startField/…` | `moteur.py:132` + `Etat._fondu` + bit 0 du mot de drapeaux `moteur.py:575-577` | Traité (deux plans, couleurs) | 529/529 |
| 10 | `camera` | `dss::Camera::send_unity` | `moteur.py:144` (valeurs : 1 position, 2 cible, 4 rotation) | Traité | 528 cartes avec la valeur 3 ; valeurs 1 et 2 une fois |
| 11 | `camera_sub` | `BookCamera::initialize`, `TownEndrollManager::setup`, `TownMapEffect::setup`, `TownOpeningManager::setupCamera` | `moteur.py:174` : bits 0, 1, 2, 4, 5, 7 | Traité ; **bits 3 et 6 non décodés** (jamais vus) | valeurs vues : 32, 2, 33, 34, 38 (toutes dans les bits décodés) |
| 12 | `chara_load` | `DisplayCharacter/SpriteCharacter::setup/cleanup` | `moteur.py:113` | Traité | 529/529 |
| 13 | `chara` | `DisplayCharacter::draw`, `SpriteCharacter::draw` | `moteur.py:190` : couleur 0x1000, position 0x2000/0x8000, pose/direction 0x4000 | **Traité depuis (mise à jour du 04/11/2026)** ; constat du 02/11 : bit 0x800 (échelle du sprite) lu puis jeté (`fl = fl[1:]`) | 528/529 cartes envoient le bit 0x800 ; valeurs de 0,022 à 1,435 ; la visionneuse dessine tout à `SPRITE_ECHELLE` = 0,045 (`fenetre.py:106`). Voir §1.2. |
| 14 | `chara_on_off` | `BillboardCharacter/SpriteCharacter::setDisplayEnable` | `moteur.py:116` | Traité | 5 paquets sur 3 cartes |
| 15 | `chara_shadow` | `SpriteCharacter::setShadowFlag`, `FieldBalloonDraw::draw`, `DisplayCharacter::draw` | `moteur.py:118` | Traité | **0/529** au chargement : ombres affichées par défaut (`fenetre.py:2876`), le moteur n'envoie rien en 90 images |
| 16 | `chara_sleep_pose` | `DisplayCharacter::draw`, `setSleepFlag` | **aucune branche** | **Traité depuis #45 (mise à jour du 04/11/2026)** ; constat du 02/11 : non géré | 3 cartes : `mlb1a` (valeurs 1280, 1281, 0x0c000100, 0x08000101), `mlm2f1` (1289), `taf1` (0x0c000208). Poses « couché » des personnages qui dorment. |
| 17 | `chara_sleep_near` | `cmd_set_sleep_near` | **aucune branche** | **Traité depuis #45 (mise à jour du 04/11/2026)** ; constat du 02/11 : non géré | `taf1` [1040, 1863] |
| 18 | `chara_pose` | `TownCharacterDraw::changePose` | **aucune branche** | **Traité depuis #45 (mise à jour du 04/11/2026)** ; constat du 02/11 : non géré | 0/529 (scripts) |
| 19 | `rise_icon_load` | `BillboardItem::draw/cleanup`, `FieldSystem::draw`, `TownPlayerEtc::draw` | `moteur.py:126` | Traité | 14 cartes |
| 20 | `rise_icon` | `BillboardItem::draw`, `TownPlayerEtc::talk_icon_set_pos` | `moteur.py:129` | Traité | 7 cartes |
| 21 | `mesh_load` | `DSSAObject::send_unity_load` (monstres, effets, logo, générique, poker) | `moteur.py:149` | Traité | 7 cartes ; poker : 5 modèles |
| 22 | `mesh` | `Dssa_G3_BeginMesh` | `moteur.py:181` | Traité (dessin **seulement en `PARTIE_VILLE` et combat**, voir §3 casino) | 1 carte (87 paquets) ; poker : 485 puis 450 par 90 images |
| 23-26 | `mesh_on_off`, `mesh_shader`, `mesh_color`, `mesh_tex_offset` | `DSSACharacter::SetShader`, `BattleEffectTransform`, `CommonEffectFlat` ; 23 : émetteur non trouvé | `moteur.py:166-172` | Traité | 0/529 (combat) |
| 27 | `field_load` | `FieldData::setup/cleanup` | aucune branche | **Contourné** : la carte du monde est lue directement dans la mémoire du moteur (`_lire_monde`) | pas de paquet en ville |
| 28 | `field` | `FieldData::drawBlock` | `moteur.py:104` | Traité | carte du monde seule |
| 29 | `field_symbol` | `FieldData::draw_symbol` | `moteur.py:106` ; patch de la fenêtre des lieux `moteur.py:508-` (§4) | Traité | carte du monde seule ; genres 19 et 20 dessinés, 18 = case vide voulue par le jeu (mise à jour du 04/11/2026 ; constat du 02/11 : non dessinés) |
| 30 | `field_scale` | `FieldData::setOffset` ← `FieldPlayerManager::balloonExec/downBalloon/rideBalloon/setScriptBalloon` ; `SpriteCharacter::setup` | `Etat.appliquer` (`champ_echelle`, `flottants`) depuis #252 | **Traité** | carte du monde en ballon : entier < 0 = `Field.SetScale` (hauteur visible du terrain × l'échelle, 1,00 à 1,25, multipliée par le zoom du joueur) ; entier >= 0 = `Field.SetFloatingObject` (le panneau du ballon, emplacement 12, grandit comme l'échelle et garde sa taille à l'écran). **Établi** (désassemblage `cmd_field_scale` D12794, `Field.SetScale` CD353C, `FloatingObject.SetScale` CD3708 ; le moteur envoie `(27, [1])` puis `(30, [12])` à chaque entrée sur la carte du monde, relevé sur la sauvegarde 4). **Non vérifié** : un vol réel (sauvegardes au chapitre 1). |
| 31 | `fbx_load` | `ModelObject::setup/cleanup`, `TownMapEffect::setup/cleanup` | `moteur.py:154` + `fenetre.py:1317` | Traité (**uniquement `SkinnedMeshRenderer` + shader `Custom/ImdChara`, animation non comprimée** : `donnees.py:328,340,355` lèvent une erreur et l'appelant ignore le modèle) | 4 cartes : `caf1`, `ev02`, `ev08` (libération), `ev07` (modèle 1017) |
| 32 | `fbx` | `ModelObject::draw`, `TownMapEffect::execute`, `TownModelDraw::setDisplay` | `moteur.py:157` | Traité | 3 cartes, 37 paquets |
| 33 | `map_color_rate` | `FLDObject::SetRGBRate` ← `TownStageManager::loadStage/SetRGBRate` ← `cmd_set_timezone`, `__cmd_map_blend_init/color`, `CommonEffectLocation` ; `FieldData::setPaletteRate` ← `FieldStage::ChangeTime`, `FieldPlayerDoku::checkDokuDamage` | **aucune branche** | **Traité (mise à jour du 04/11/2026)** ; constat du 02/11 : non géré (ignoré en silence) | **171 cartes sur 529 au chargement** (voir §1.1) |
| 34 | `screen_effect` | `Global::SetScreenEffect` ← `NonBattleActionManager::execute` ← `FieldSystem/TownSystem::execute` | `moteur.py:607` : seulement valeur & 0xf = 4 (début de combat) | **Partiel** : 3 (voyage), 5 (lampe), 6 (Riremito) non rejoués (`notes-technique:63`, `notes-visionneuse:83`) | 0/529 (déclenché en jeu) |
| 35 | `se_play` | `Sound::sePlayDirect`, `SoundManager::playSe` | `moteur.py:187` → `son.py` | Traité | 5 cartes, SE 305, 308, 309, 1156 |
| 36 | `se_stop` | `SoundManager::stopSeWithIndex` | `moteur.py:187` | Traité | 0/529 |
| 37 | `bgm` | `SoundManager::play*/stop*` (12 appels) | `moteur.py:187-189` ; ≥ 4096 = arrêt (`son.py:80`) | Traité | 39 cartes au chargement ; 12 musiques distinctes (2, 14, 16, 17, 18, 21, 22, 23, 24, 26, 29) + 16384 (arrêt) |

### 1.1 Le paquet 33 en chiffres (nouveau, Établi)

Le moteur envoie la teinte de la carte (trois flottants r, g, b, 1,0 = neutre) à **171 cartes sur 529** dès le chargement :
- `(1,25 ; 0,65 ; 0,75)` sur 149 cartes : préfixes `ml`, `mm`, `mn`, `mo`, `mp`, `mq`, `mr`, `ms` (tous les villages), `ss` (41 cartes), `sj`, `sk`, `sh`, `ta` à `td`, etc. Teinte rouge-rosée (chapitres/heures du jour).
- `(1,30 ; 0,70 ; 0,55)` sur 20 cartes : toutes les `te*` (orangé).
- `(0,804 ; 0,807 ; 1,102)` sur `caf1` et `ev02`, valeur qui varie lentement (10 valeurs distinctes en 90 images : un fondu de teinte).
- Côté Unity (`cmd_map_color_rate`, RVA 0xD14E44, désassemblé) : il lit trois flottants et appelle `Field.SetColor(r, g, b, 1.0)` (carte du monde) ou écrit les trois valeurs dans l'objet de la carte (+0xd0, +0xd4, +0xd8). C'est une **multiplication de couleur sur le décor**. Établi.
- Effet visuel attendu : 32 % des cartes sont affichées sans la teinte du jeu d'origine. **Supposé** (jamais comparé à une capture Android). Le même paquet porte aussi le jour / la nuit de la carte du monde (`FieldStage::ChangeTime`) et la teinte de dégât de marais (`FieldPlayerDoku`) : ces deux cas ne sont pas vus en ville, ils sont à tester sur la carte du monde.
- Déjà connu des notes (`notes-technique:233` pour `mlb1a` seulement) ; l'étendue (171 cartes, 3 familles de valeurs) est nouvelle.

### 1.2 Autres valeurs et bits non décodés

- **Paquet 13, bit 0x800 (échelle du sprite)** : jeté (`moteur.py:191`). Établi : 528 cartes l'envoient. Valeurs relevées sur 70 images : `mak1f1` et `ccf1a` 1,0 ; `mlb1a` 0,738 (héros et équipier) ; `ev07` 0,952. Sur 90 images, 18 cartes ont aussi la valeur 0,045 au tout début (`ca*`, `cb*`, `ccb*`) et 0,059 pour d'autres : probablement la valeur initiale avant la première mise à jour (non vérifié). La visionneuse force la taille des sprites (`HEROS_FRAC`, `fenetre.py:124`). **Supposé** : sprites trop grands ou trop petits dans `mlb1a`, `ev07` et peut-être des scènes d'événements qui animent l'échelle ; à confirmer en jouant le prologue.
- **Paquet 10** : seules les valeurs 1 (position), 2 (cible) et 4 (rotation) sont décodées (`moteur.py:144-148`) ; les autres bits sont ignorés (jamais vus : 1, 2 et 3 seulement).
- **Paquet 11** : bits 3 et 6 non décodés.
- **Paquet 34** : valeurs 3, 5, 6 non décodées.
- **Mot de drapeaux de sortie (`outp[0]`)** : la visionneuse écrit les bits 0 (fondu) et 1 (effet d'écran) (`moteur.py:575-577`, `544-547`) et lit les autres (`drapeaux()`). Bit 3 (manette tactile) et bit 4 (limite TownCamera) : lus seulement pour l'affichage/la caméra. `UnityInitTouchFlag` est appelé par `TownSystem::initialize`, `FieldSystem::initialize`, `BattleSystem2::initialize`, `CasinoSystem::initialize`, `TownOpeningManager::setup`, `TownPlayerManager::checkMenuAction` : la visionneuse n'en tire rien (Non vérifié : effet d'une valeur différente sur le moteur).
- **`UnitySetString`** : aucun appelant direct dans le graphe d'appels (`callgraph.py up UnitySetString` ne renvoie rien) ; la visionneuse n'en lit pas le tampon. Supposé inutilisé.

### 1.3 Où la visionneuse ignore en silence

Établi par `grep` sur `dq4_pc/*.py` : **aucun** `NotImplementedError`, `TODO`, `FIXME`. Les « silences » sont :
- `Etat.appliquer` : pas de branche `else`. Un type inconnu (1, 6, 16, 17, 18, 27, 30, 33) est ignoré sans journal. C'est la source du trou §1.
- `except Exception: pass` : `fenetre.py` ×8 (l.285, 363, 412, 415, 598, 766, 1109, 1115 : changement de mode de fenêtre, fermeture d'un processus, écriture de cache), `son.py` ×12 (chargement et lecture des sons : un fichier son illisible disparaît sans message), `pause.py` ×4, `sauvegardes.py` ×2 (l.130, 144), `ecran_sauvegardes.py:70`. Le plus gênant pour la jouabilité : `son.py` (une musique qui n'est pas décodable est un silence sans trace). Non vérifié : combien de BGM échouent en réalité (je n'ai pas lancé le décodeur sur les 686 fichiers).
- `donnees.py:161` : palette animée ignorée (« ignorée ») ; `donnees.py:307-355` : modèles 3D non pris en charge (maillage non skinné, autre shader, animation comprimée) → modèle absent de l'écran, message de journal seulement.
- `Moteur.step` lève `RuntimeError('le moteur s est arrete …')` quand Unicorn plante (`moteur.py:588`) : c'est le seul cas où l'arrêt est bruyant. Dans le balayage : 1 cas sur 529 (`ev01`, voir §5).

---

## 2. Types MenuPort 1 à 80

Source des classes du moteur : `menutypes3_raw.txt` (nombre d'appels de création par classe, scan statique). Source des noms `Make_*` : `ui_layout.json` (`/tmp/uicache4`). Établi : **tous les types sont exportés** (mise en page extraite du code Unity sous Unicorn) **sauf 73, 77 et 80** (erreur d'export : 73 « Touchez l'écran » et 80 Licence sont lus à la main, `fenetre.py:2706`, `2718`, `avant_partie.py` ; 77 = réseau, inutile sur PC). Tous les autres types sont dessinés par le chemin générique de `ui_menu.py` ; les entrées passent par `_saisie_menu` (`fenetre.py:1592`) ou la souris.

Classes `IBase` personnalisées : **les cinq sont prises en charge** (`ui_menu.py:199-204, 229, 250, 347-413, 849`) : `StatusIconChanger` (types 4, 5, 20, 21, 46, 60, 61, 67), `ItemNumCTRL` (9), `ICityMap` (25), `BattleBar` (29), `MonsterMarkList` (31). La ligne « Lacunes : classes IBase personnalisées non reproduites » de `notes-technique-portage-dq4.md` (section « Interface d'origine : fenêtres et menus ») est donc **périmée** (à corriger dans les notes).

Colonne « Niveau » :
- **Vu (doc)** : une capture ou une trace documentée existe dans les notes (référence `V` = notes-visionneuse, `T` = notes-technique, avec le numéro de ligne).
- **Vu (moi)** : je l'ai ouvert dans le moteur cette fois-ci.
- **Rendu seul** : mise en page exportée et dessinée par le chemin générique ; aucune trace d'un essai réel dans les notes.
- **Contourné / Absent / Inconnu** : voir la ligne.

| Type | `Make_*` | Classes moteur qui l'ouvrent | Écran de jeu | Traitement visionneuse | Niveau |
|---|---|---|---|---|---|
| 1 | YesNo | `CommonMenu_YESNO` | Oui / Non (toutes les questions) | générique ; suit la fenêtre de message `fenetre.py:2120, 2148` ; curseur moteur (grille) | Vu (doc V18, V161, V251) |
| 2 | Money | `MaterielMenu_SHOP_*`, `CHURCH_*`, `INN_ROOT`, `TownMenu_*` | or affiché | générique | Vu (doc V251, V258) |
| 3 | RootMenu | `TownMenu_ROOT` | menu du terrain : Objets / Magie / Carac. / Divers | générique | Vu (doc V7, V251) |
| 4 | LeftCharaList | ~25 classes `TownMenu_*`, `MaterielMenuExtra_ChangeHostage` | colonne des personnages | `StatusIconChanger` `ui_menu.py:202` | Vu (doc V161) |
| 5 | TargetCharaList | `BattleExecStatus`, `MenuItem_RightCharaList_*` | cible d'objet / de sort | idem | Rendu seul |
| 6 | Pageing | `MenuItem_Pageing_*` | pages d'une liste | générique ; L / R = pages `fenetre.py:2568` | Rendu seul |
| 7 | MagicInfo | `TownMenu_MAGIC_*` | description d'un sort | générique | Rendu seul |
| 8 | NameButton | `TownMenuItemSelectCommand` (9), `TownMenu_OPERATION_SETTING` (11) | boutons de commande | générique | Vu (doc V289, V293) |
| 9 | ItemList | `TownMenuItemSelectChara`, `…TargetItem`, `EXTRA_NENE` | sac / liste d'objets | `ItemNumCTRL` `ui_menu.py:203, 229` | Vu (doc T186, audit de fidélité 01/11) |
| 10 | ItemInfo | `MenuItem_ItemInfo_Setup` (14 appels) | description d'un objet | générique | Rendu seul |
| 11 | BCInfo | `TownMenu_OPERATION_*` | infobulle | générique | Rendu seul |
| 12 | Chapter | `MaterielMenu_EXTRA_CHAPTER_TITLE` | titre de chapitre (bandeau) | bandeau « hyodai » (#40, `notes-technique:229`) | Vu (doc ; **moi** : port 12 type 12 ouvert au chargement d'une carte du balayage) ; sous-titres des chapitres suivants jamais vus (G-043) |
| 13-17 | Status (×5) | `TownMenu_STATUS`, `TownFurnitureControlStorage` (17) | écran « Carac. » (5 pages) | générique | Rendu seul |
| 18 | OperationItemList | `TownMenu_OPERATION_ROOT`, `TownFurnitureControlStorage` | liste du menu Divers | générique | Rendu seul |
| 19 | Senreki | `TownMenu_OPERATION_CAREER` | historique de l'équipe | générique | Rendu seul |
| 20-21 | MemberShift, MemberShiftButton | `TownMenu_OPERATION_SHIFT_PARTY`, `SetMemberShiftButtonInfo` | ordre de marche | `StatusIconChanger` | Rendu seul |
| 22-23 | MapButton | `FieldImageMap`, `TownImageMap` | bouton « mode de la carte » | `fenetre.py:1875` | Vu (doc V236, T188) |
| 24 | ShopMap | `TownImageMap` (9) | liste des boutiques de la ville | `Moteur.boutiques` `moteur.py:` ; `fenetre.py:2540` | Vu (doc V264, T133) |
| 25 | CityMap | `FieldImageMap`, `TownImageMap` | plan de la ville / carte réduite | `ICityMap` `ui_menu.py:201, 849` ; `moteur.py:314` | Vu (doc, nombreux) |
| 26 | WorldLargeMap | `FieldImageMap` | grande carte du monde | `fenetre.py:2165` | Vu (doc V327) |
| 27 | Config | `TownMenu_OPERATION_SETTING` (7) | paramètres du jeu d'origine | **contourné** : le bouton ouvre le menu Pause de la visionneuse (patch `moteur.py:465`) ; la fenêtre d'origine n'est jamais ouverte | Contourné (volontaire, `notes-technique:242`) |
| 28 | MonsterEncyclopedia | `MaterielMenu_PICTUREBOOK_ROOT/DETAIL` | **Bestiaire** (partie 0x10) | partie 0x10 gérée (mise à jour du 04/11/2026 ; constat du 02/11 : non gérée) | **Présent** (liste, fiche et monstre dessinés, jouable au clavier : audit services SVC-04 ; constat du 02/11 : monstre non dessiné, §3.1 point 5) |
| 29 | BattleUpStatus | `BattleMenuSub_HISTORY` | bandeau d'état des personnages (combat) | `BattleBar` `ui_menu.py:204, 250`, secousse `347` | Vu (doc T85) |
| 30 | BattleRoot | `BattleMenu_ROOT` | Combattre / Fuir | générique | Vu (doc T90) |
| 31 | MonsterName | `BattleMenu_*` | plaques des monstres | `moteur.py:286`, marques `ui_menu.py:407` | Vu (doc V61, T93) ; tri / évitement des plaques non reproduits |
| 32 | BattleAction | `BattleMenu_ACTIONMENU`, `ARRAYMENU` | menu d'actions | générique | Vu (doc T90) |
| 33-34 | BattleTarget, BattleGo | `BattleMenu_ATTACK`, `BattleGo` | cible, « Combattre » | générique | Rendu seul |
| 35-37 | BattleIM (×3) | `BattleMenu_MAGIC`, `ITEM`, `TACTICSMENU`, `ARRAY_*` | sorts, objets, tactiques | générique | Rendu seul |
| 38 | BattleInfo | `BattleMenu_ITEM`, `MAGIC` | description en combat | générique | Rendu seul |
| 39-40 | BattleEnemyTarget, BattlePartyTarget | `BattleMenu_*2ENEMY`, `*2PARTY` | cibles | générique | Rendu seul |
| 41-42 | BattleChangeButton, ChangeInfo | `BattleMenu_ARRAY_*`, `SetBattleChangeInfo` | changement de rang | générique | Rendu seul |
| 43 | BattleHoppingNumber | `BattleMenu_setHoppingNumber` | nombres de dégâts | `moteur.py:273`, `fenetre.py:2004` | Vu (doc V148) |
| 44 | Casino_CoinShop | `MaterielMenu_COINSALEROOM_ROOT` | échange d'argent contre des jetons | générique | **Inconnu** |
| 45-46 | Casino_GiftList, GiftTarget | `MaterielMenu_CHANGEGIFT_*` | prix contre jetons | générique | **Inconnu** |
| 47 | Casino_Slot | `MaterielMenu_SLOT` | machine à sous | générique ; mise réglable au clavier (mise à jour du 04/11/2026 ; constat du 02/11 : non réglable, §3) | **Vu (moi)** : moteur + capture GL ; jouable au clavier : SVC-04 |
| 48 | Casino_Poker | `MaterielMenuPoker{Betcoin,Changecard,Selectcard}` | poker | idem ; table et cartes dessinées (mise à jour du 04/11/2026 ; constat du 02/11 : non dessinées, §3) | **Vu (moi)** : moteur + capture GL ; jouable et dessiné au clavier : SVC-04 |
| 49-51 | Casino_FightStadium{Bet, Select, Coin} | `MaterielMenu_FIGHT_STADIUM` | arène des monstres (casino) | générique | **Inconnu** |
| 52 | StartMenuFirst | `TownPlayerManager` | 1er menu de départ | `avant_partie.py` | Vu (doc V334) |
| 53 | StartMenuSecond | `MaterielMenu_LOAD` | menu de départ | `fenetre.py:2116, 2186` | Vu (doc V334, T197) |
| 54 | StartMenuSelect | `MaterielMenu_LOAD/SAVE`, `MaterialMenu_Network` | liste des journaux | `fenetre.py` + `sauvegardes.py` | Vu (doc V334-351, T107) |
| 55 | StartNameEntry | `MaterielMenu_NameEdit` | saisie du nom | `saisie_nom.py`, `fenetre.py:2746` | Vu (doc V382) ; clavier « inventé » (G-099) |
| 56 | SaveOverwrite | `MaterielMenu_SAVE` | sauvegarde à l'église (écrasement) | générique | **Inconnu en jeu** (G-120, jamais confirmé sous Windows) |
| 57 | ShopRoot | `MaterielMenu_SHOP_ROOT`, `BANK_ROOT` | racine boutique / banque | générique | **Inconnu en jeu** |
| 58-59 | ShopBuy (×2) | `MaterielMenu_SHOP_BUYMENU` | liste d'achat | `fenetre.py:1612` (◀ ▶ = quantité) | Rendu seul (`notes-technique:240`) |
| 60-61 | ShopBuyInfo (×2) | `MaterielMenu_SHOP_WHOSE` | « Qui va le porter ? » | `StatusIconChanger` | Rendu seul |
| 62 | ShopSellItemList | `MaterielMenu_SHOP_WHO_SELL` | liste de vente | générique | Rendu seul |
| 63 | ShopSellItemInfo | `MaterielMenu_SHOP_WHO_SELL` | quantité à vendre | `fenetre.py:1612` | Rendu seul |
| 64-65 | BankDeposit, BankDraw | `MaterielMenu_BANK_PUTIN`, `BANK_DRAW` | banque | générique | **Inconnu en jeu** |
| 66 | ChurchRoot | `MaterielMenu_CHURCH_ROOT` | menu du prêtre | générique | Vu (doc V7 : liste de l'église) |
| 67 | ChurchWork | `MaterielMenu_CHURCH_MIRACLE` | résurrection, bénédiction | `StatusIconChanger` | **Inconnu** |
| 68 | Chapter2Status | `MaterielMenu_MARTIAL_COLOSSEUM` | arène martiale (chapitre 2) | générique | **Inconnu** |
| 69 | TorunekoMiseban | `MaterielMenu_EXTRA_SIDEJOB_SELL` | boutique de Torneko | générique | **Inconnu** |
| 70 | NENE_ItemView | `MaterielMenu_EXTRA_NENE` | objets de Nénè | générique | **Inconnu** |
| 71 | FightStadiumAbort | `BattleMenu_StadiumAbort` | abandon d'un combat d'arène | générique | **Inconnu** |
| 72 | ViewVolumeDecision | `TownFurnitureManager::TwinklePoint` | décision de « volume de vue » (meubles ? Supposé) | générique | **Inconnu** |
| 73 | TitleTouch | `TownOpeningManager` | « Touchez l'écran » du titre | lu à la main `fenetre.py:2706` | Vu (doc T184, T197) |
| 74 | PortalButton | `MaterielMenu_LOAD` | bouton du portail Square Enix | aucun code propre | Non vérifié (inutile sur PC) |
| 75-79 | Network* | `MaterialMenu_Network` | réseau / nuage | inutilisé sur PC : case « Sauv. cloud » retirée `moteur.py:350` | Contourné (77 : export en erreur) |
| 80 | License | `MaterielMenu_LOAD` | licence | lu à la main `fenetre.py:2718` | Vu (doc T204) |

**Types sans aucune trace de test réel** (Rendu seul, Inconnu, Absent) : 5, 6, 7, 10, 11, 13-21, 33-42, 44-51, 56-65, 67-72, 74. Un test réel veut dire : le moteur les a ouverts et la visionneuse les a dessinés dans une session. Pour les ouvrir sans jouer 30 heures, il faut un point d'entrée par type (voir §5.4 : balayage « fenêtres »).

---

## 3. Matrice des fonctionnalités

Statuts : **Présent** (vu fonctionner, preuve citée), **Partiel** (une partie marche, le reste est un trou prouvé), **Absent** (prouvé à l'écran ou dans le code), **Inconnu** (aucune trace de test ; le code ne permet pas de conclure). « Comment tester » dit le chemin le plus court.

### 3.1 Casino : constats détaillés (le plus gros apport de cet audit)

Le casino est une **partie distincte du moteur** : `Global::startCasino` (appelé par `cmd_mini_game` ← `MaterielMenu_SlotEnter`) passe en partie **0xf**. `Global::setMinigame(0)` lance le **poker** (carte `ev04`, fenêtre de port 12, type 48), toute autre valeur la **machine à sous** (carte `ev05`, type 47). Établi par `probe_grille.py` (moteur seul). La visionneuse ne définit que les parties 3, 0xc, 0xd, 0xe (`moteur.py:8-11`) : **0xf (casino) et 0x10 (bestiaire) n'existent pas dans son code**.

Ce que j'ai observé (Établi : moteur sous Unicorn avec 500 jetons écrits dans le moteur de test, et captures GL de la visionneuse réelle) :

1. **Machine à sous, côté moteur : jouable.** `envoyer_menu(12, 1, 1, 0x2)` ×3 (flèche ▲ du bouton 1) fait passer les jetons de 500 à 497 et la mise à 3 ; `[1, 0, 0x10]` (« Lancer ») lance les rouleaux (684 paquets 4 = rotations d'objets de carte), un nouvel appui les arrête, un message de résultat s'affiche (`probe_slot4.py`).
2. **Machine à sous, côté visionneuse : bien dessinée, jouable à la souris, pas au clavier.**
   - `gl_slot_b330.png` : la machine entière, la table des gains, « Jetons 500 », « Parier combien ? », ▲ 0 ▼, « Lancer » sont à l'écran.
   - Souris (clics sur ▲ ×3 puis « Lancer ») : `gl_slotms_b350.png` montre « Jetons 497 » et des rouleaux en mouvement.
   - **Clavier** (Haut ×3 puis Entrée) : `gl_slotkb_b420.png` est **identique à l'image sans entrée** (mise 0, « Jetons 500 », rien ne tourne). Cause lue dans le code : `_saisie_menu` (`fenetre.py:1597-1621`) ne met dans `z` que les boutons de manette 0x10 ; ▲ et ▼ sont des boutons de manette 0x2 et 0x1 (types 47 et 48, `ui_layout.json`), donc **inaccessibles au curseur local** ; la fenêtre n'a pas de grille moteur (`probe_grille.py` : `grille = None`), donc les flèches du clavier ne sont pas transmises. Un joueur au clavier ne peut ni miser ni lancer (mise 0 : « Lancer » ne fait rien).
   - L'animation d'événement d'un gros gain (paquet 6, émis par `CasinoSlot::setBingoAnim` via `FldStage::eventAnim`) serait ignorée (aucune branche pour le paquet 6) ; **non observée** : mes sondes n'ont pas obtenu de gain.
3. **Poker, côté moteur : jouable.** La mise passe par les mêmes boutons ▲ ▼ (500 → 497, mise 3). Le bouton 0 (étiquette « DONNER ») pressé avec une mise de 0 ramène à la ville proprement (retour à `mak1f1`, partie 0xc, jetons intacts, 219 images) ; la main complète (échange de cartes, résultat) n'a **pas** été jouée (`probe_poker3.py` s'arrête là).
4. **Poker, côté visionneuse : table et cartes invisibles.** `gl_poker_b330.png` : écran **noir** avec seulement les fenêtres (table des gains, « Jetons 500 / Pariés 0 », message « Combien voulez-vous miser ? »). La carte `ev04` n'a **ni sol, ni texture** (« 0 groupes », 1 objet) : tout ce qu'on voit au poker sont des maillages dynamiques envoyés par les paquets 21 / 22 (5 modèles, 485 puis 450 paquets 22 par 90 images). La visionneuse ne les dessine **qu'en `PARTIE_VILLE` et en combat** (`fenetre.py:2913`, condition `e.partie == MO.PARTIE_VILLE`). **Preuve causale** : avec un lanceur extérieur au dépôt qui force `etat.partie = 0xc` à l'affichage seulement (`gl_casino.py`, `CAS_FORCEVILLE=1`), `gl_pokerv_b330.png` montre **les cinq cartes face cachée**. Le correctif probable est de ne pas réserver ce bloc à la ville (casino 0xf, bestiaire 0x10) : **Supposé** (je n'ai pas modifié le dépôt, et je n'ai pas vérifié que les cartes retournées, la main gagnante et les animations passent aussi).
5. **Bestiaire (`Global::startBook`, partie 0x10, déclenché par `TownMenuItemSelectCommand::menuUpdate`, c'est-à-dire un bouton du menu du terrain)** : le moteur envoie 3 paquets de caméra / modèle (10, 11, 21) et ouvre le type 28. `gl_book_b230.png` : la **liste des monstres** (page 1, noms, « ??? » pour les inconnus, flèches de page) s'affiche, mais un **petit morceau de l'église `mak1f1`** transparaît derrière les boutons (la caméra du bestiaire regarde la dernière carte). `gl_booksel_b330.png` (après avoir choisi « Gluant » avec Entrée) : la **fiche** s'affiche avec ses chiffres (Vaincus 8, Expérience, Or…), mais **à la place du monstre on voit l'église `mak1f1`** (la dernière carte de ville, redessinée dans le cadre). Le moteur envoie bien le monstre : paquet 21 `[0, 0]` puis paquet 22 (maillage de 16 à 20 sommets en (0, 0, -62,25), emplacement 0), caméra en (0, 0, -83) (`probe_book2.py`, Établi). Il n'est pas dessiné. J'ai essayé de forcer l'affichage en partie ville (`CAS_FORCEVILLE=1`) : la capture est **identique octet pour octet** (`cmp`), donc la garde `PARTIE_VILLE` (`fenetre.py:2913`) n'est **pas** la seule cause ici ; la cause n'est **pas trouvée** (Non vérifié : caméra de ville contre caméra du bestiaire, la carte non masquée, ou texture `m0`).

### 3.2 Matrice

| Fonctionnalité | Statut | Preuve | Comment tester |
|---|---|---|---|
| Boutiques : achat / vente / quantité (types 57-63, script `cmd_menu_shop`) | **Inconnu** (fenêtres : rendu seul) | types exportés, ◀ ▶ de quantité codés `fenetre.py:1612` ; le moteur y arrive par `CommandWindow::changeShopMenuPhase` (graphe d'appels) ; aucun balayage ne les ouvre (au chargement, seul le type 12 apparaît) ; G-092 (autre agent) | Jouer : parler à un marchand (par ex. village de départ), acheter, vendre, vérifier l'or et le sac. Automatique : N2 (§5), noter les types 57-63. |
| Église : prêtre (type 66) | **Partiel** | liste de l'église vue dans le prologue (`mak1f1`, doc V7) | Parler au prêtre de `mak1f1` : Sauvegarder, Revenir à la vie, Prière |
| Église : résurrection / pénitence (type 67) | **Inconnu** | aucune trace | Avoir un personnage mort, parler au prêtre |
| Sauvegarde à l'église (`cmd_menu_save`, type 56) | **Inconnu en jeu** | écriture dans `--saves-ecriture` lue dans le code (`moteur.py:41, 53`) ; jamais confirmée sous Windows (G-120) | Sauvegarder, quitter, relancer, « Continuer » ; comparer `data1.dat` |
| Auberge (sommeil, fondus) | **Partiel** | menus Oui / Non + or génériques ; poses couché gérées depuis #45 (paquets 16, 17, 18 : §1 ; constat du 02/11 : non gérées) ; vus au chargement dans 3 cartes (`mlb1a`, `mlm2f1`, `taf1`) ; G-069 | Dormir à l'auberge, regarder les personnages et la teinte |
| Banque (types 57, 64, 65) | **Inconnu** | aucune trace | Chapitre où la banque existe : dépôt, retrait |
| Casino : machine à sous (47) | **Présent** : clavier et souris (mise à jour du 04/11/2026, SVC-04) ; constat du 02/11 : souris oui, clavier non (§3.1) | `gl_slot_b330.png`, `gl_slotms_b350.png`, `gl_slotkb_b420.png` | Casino : lancer au clavier uniquement |
| Casino : poker (48) | **Présent** : table et cartes dessinées (mise à jour du 04/11/2026, SVC-04) ; constat du 02/11 : cartes et table invisibles (§3.1) | `gl_poker_b330.png` contre `gl_pokerv_b330.png` | Idem avec le poker |
| Casino : jetons (44), cadeaux (45, 46) | **Inconnu** | types exportés seulement | Casino : comptoir d'échange |
| Arène des monstres (49-51, 71), colisée (68) | **Inconnu** | `cmd_mini_game` a une branche à part quand son premier paramètre vaut 2 (début de la fonction, 0x21d6d8 : ne passe pas par `startCasino`) ; non explorée | Casino, arène : parier, regarder un combat |
| Mini-jeux et menus de scénario : `cmd_menu_nene` (70), `cmd_menu_extra_shop` (69), `cmd_menu_hostage` (types 4, 21), `cmd_menu_present_exp`, `cmd_menu_event_imuru` | **Inconnu** | commandes de script recensées par le graphe d'appels ; fenêtres exportées | Jouer les chapitres concernés ; N2 avec sauvegardes de ces chapitres |
| Bestiaire (type 28, partie 0x10) | **Présent** : liste, fiche et monstre dessinés (mise à jour du 04/11/2026, SVC-04) ; constat du 02/11 : monstre non dessiné (§3.1 point 5) | `gl_book_b230.png` | Menu du terrain → bestiaire → choisir un monstre |
| Véhicules : bateau, ballon, sifflet, Rura, henge | **Partiel** (mise à jour du 04/11/2026 : bateau et chariot dessinés, bateau découpé comme dans le jeu depuis #211 ; ballon en vol, sifflet, Rura, henge non vérifiés) ; constat du 02/11 : **Inconnu** | émetteurs recensés (`FieldPlayerManager::shipExec`, `balloonExec`, `ballonWhistle`, `ruraUp/DownExec`, `hengeStartExec`) ; **paquet 30 (zoom du ballon) traité depuis #252 (vol réel non vérifié)** ; `notes-visionneuse:44` : « pas de marche sur l'eau / bateau testée » ; G-031 | Carte du monde : monter sur le bateau, voler en ballon ; voir si le décor et les sprites suivent |
| Équipe et chariot | **Partiel** | équipiers suivent le héros (tests documentés) ; chariot (`FieldPlayerManager::getCarrierPos`, `setCarrierDepth`) : aucune trace | Chapitre 5 : chariot à l'arrière |
| Cartes de villes / donjons (529) | **Présent, avec trous** | N1 : 528 / 529 chargées sans plantage, 0 sprite sans feuille, 0 PNJ hors carte, 0 fondu bloqué (§5.4) ; trous du 02/11 : teinte (171 cartes), échelle des sprites, poses couchées, **depuis traités** (mise à jour du 04/11/2026) ; restent FSRA / FEAN / FEMV non rejoués (audit cartes, MAP-03) | N3 (capture de toutes les cartes) |
| Carte du monde | **Présent** (doc : sol, icônes, caméra, marche) | `notes-visionneuse` « Carte du monde » ; reste : jour / nuit et marais (paquet 33), ballon (30), voyage / lampe (34) | Jouer la carte du monde sur une journée de jeu |
| Sac / objets (9, 10, 18) | **Présent** (affichage) | `ItemNumCTRL` porté, doc T186 | Ouvrir le sac, utiliser un objet |
| Sorts (7, `TownMenu_MAGIC_*`) | **Partiel** | fenêtres exportées ; effets de sorts en combat : G-070, G-071 | Lancer chaque sort du menu |
| Équipement (`TownMenu_OPERATION_EQUIP`) | **Inconnu** | types 8, 9, 10, 11 génériques | Équiper / déséquiper, comparer les caractéristiques |
| Statut (13-17) | **Partiel** | exportés, pas de trace de test | « Carac. » sur chaque personnage |
| Points de sauvegarde / sauvegarde auto (data5) / suspension (data4) | **Présent** (menu de départ : Continuer, Reprendre, Auto, Supprimer, import / export) | doc V334-358, T197-214 | Suivre le menu de départ ; la plaque « Sauvegarde automatique » est toujours là (G-201) |
| Montée de niveau, victoire, game over | **Partiel / Inconnu** | « pas de combat gagné dans mes essais automatiques » (PR #35) ; G-078 | Gagner un combat de bout en bout |
| Combat de base | **Présent** (attaque, menus 29-32, nombres de dégâts, effet d'entrée) | doc | Boss, groupes, sorts : Inconnu |
| `Make_Chapter` (type 12, titre de chapitre) | **Présent** (prologue) | doc T229, `notes-technique` « Prologue » ; vu au balayage | Chapitres suivants : sous-titre jamais vu (G-043) |
| Titre / reprise / création / nom | **Présent** ; clavier du nom « inventé » (G-099) | doc | |
| Générique de fin (`TownEndrollManager::startTheEnd` ← `__cmd_the_end`) et fins | **Inconnu** | aucun code dans `dq4_pc` (`grep -i endroll|staff|ending` : rien) ; s'appuie sur le décodage générique (paquets 11, 21, 22 : maillages, uniquement en `PARTIE_VILLE`) | Sauvegarde proche de la fin, ou appel direct de la commande dans un moteur de test |
| Objets de quête, `cmd_*` de scénario | **Inconnu** | non étudiés | N2 |
| « Surechigai » (`cmd_change_surechigai_part` → `Global::startSurechigai`) | **Inconnu** | une partie du moteur qui n'a pas de gestion dans la visionneuse ; probablement le mode « croisement » des mobiles (non essayé) | Appel direct de `Global::startSurechigai` dans un moteur de test |
| Pêche / plongée | **Sans objet** | aucun symbole `fish` / `dive` dans le moteur (`symbols_all.txt`) | |

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
9. **Sons** : 12 `except: pass` dans `son.py`, un son illisible disparaît sans trace ; Non vérifié (je n'ai pas lancé le décodeur sur les 686 fichiers).
10. **`g_Option + 5` écrit dans les sauvegardes** quand l'option « défilement » est imposée (Supposé) : §4, ligne 5.

---

## 4. Tout ce que la visionneuse écrit dans la mémoire du moteur

Méthode : `grep -n "mem_w(\|mem_write\|hook_add\|reg_write\|pack_into" dq4_pc/*.py` (hors `emu_core.py`, qui est le moteur d'émulation lui-même). Il n'y a **que 16 sites d'écriture**, tous listés ci-dessous. Verdict global (Établi) : **aucune écriture ne touche un drapeau de scénario, une variable d'événement, l'or, l'inventaire, la position du héros ou une pièce de casino.** Les seules données de jeu écrites sont des **options** (`g_Option + 5`) et des **vitesses de marche remises à leur valeur d'origine**.

| # | Où | Quoi | Quand | Verdict |
|---|---|---|---|---|
| 1 | `moteur.py:350` | `G_IS_AMAZON = 1` (octet de la bibliothèque) | une fois, après `GameInit` | **Légitime** : retire la case « Sauv. cloud » du menu de départ (le jeu fait pareil pour la version Amazon). Aucun effet sur la partie. |
| 2 | `moteur.py:367, 373, 376` | crochets de code `UC_HOOK_CODE` sur `MenuPort::SetVisible`, `FieldData::drawBlock`, `FLDObject::SetCommonAnimation` | à chaque appel | **Lecture seule** (ils notent un registre). Légitime. |
| 3 | `moteur.py:398-399` | écrit le registre `x8` dans `ui_MsgLoop` (lettres par image) | chaque image de texte, seulement si la vitesse du texte ≠ 4 | **Légitime** (réglage de la visionneuse « vitesse du texte »). Garde : vérifie l'instruction d'origine (`SXTH_W20_W8`), sinon ne fait rien. |
| 4 | `moteur.py:407` | crochet sur `OptionStatus::setBattleSpeed` | quand le joueur change l'option dans les Paramètres d'origine | **Lecture seule** (rappel). |
| 5 | `moteur.py:423, 427, 434` | écrit `status::g_Option + 5` (vitesse de défilement des messages de combat) à chaque image | tant que l'option « défilement » de la visionneuse est imposée ; remise de la valeur d'origine quand on la lâche | **Légitime mais à surveiller** : cette valeur fait partie de `OptionStatus`, donc **elle est écrite dans les sauvegardes** du jeu (notes-technique:241). Une partie sauvegardée pendant que l'option est imposée garde la valeur imposée. Pas un drapeau de scénario. Supposé : effet sur la sauvegarde (non essayé). |
| 6 | `moteur.py:441-453` (`_elargir_symboles`) | trois constantes immédiates de `FieldData::drawSymbol` portées à 1600 | une fois à la création du moteur | **Légitime** (affichage des lieux de la carte du monde en 16/9). Garde : le motif d'instruction est vérifié avant l'écriture. Mineur : `etats.appliquer` (`etats.py:46`) remet l'image d'origine de la bibliothèque ; le patch revient avec les pages modifiées de l'état, mais **un état enregistré avant l'existence du patch le perd** (`etats.py:60-61` ne ré-applique que `remettre_vitesses` et `patcher_parametres`). |
| 7 | `moteur.py:465` (`patcher_parametres`) + crochet `moteur.py:474` | `cmp w8, #7` → `cmp w8, #4095` dans `TownMenu_OPERATION_ROOT::menuUpdate` | à la création + après chaque chargement d'état | **Légitime / décision** : le bouton « Paramètres » ouvre le menu Pause de la visionneuse. **Conséquence** : la fenêtre de réglages d'origine (type 27 : volumes, vitesse, taille de la croix, « Revenir à l'écran titre ») n'est plus jamais ouverte ; `Moteur.retour_titre` rejoue le retour au titre. |
| 8 | `moteur.py:484` (`_creer_canevas`) | tampon de paramètres de message (largeur, hauteur du canevas) puis appel direct de `SDrawCTRL::CanvasSetup` | une fois | **Légitime** (Unity le fait par un message de port). |
| 9 | `moteur.py:516` (`remettre_vitesses`) | vitesses de marche (`TownPlayerAction::walkSpeed/walkSpeed2`, `FieldPlayer::Speed`, deux constantes à `0x27520c/0x275210`) remises aux valeurs d'origine | chargement d'un état | **Légitime** : répare un état enregistré par une ancienne version pendant une course. La course elle-même accélère l'horloge, pas ces valeurs (`moteur.py:508`). |
| 10 | `moteur.py:547` (`_drapeau_effet`) | bit 1 du mot de drapeaux de sortie (`outp[0]`) | pendant un effet d'écran de début de combat | **Légitime** (émule `Capture.ScreenEffect`). Risque : si le bit n'était jamais baissé, le moteur attendrait ; la fenêtre le borne (`ATTENTE_CHARGE_MAX`). |
| 11 | `moteur.py:577` | bit 0 du mot de drapeaux de sortie (`outp[0]`) | chaque image | **Légitime** (émule `Fade.FadePlane.CheckFade` : « un fondu est en cours »). Établi par les notes (`notes-technique:61`). |
| 12 | `moteur.py:673, 709` | tampons de messages Unity → moteur (`buf1/buf2`) | à chaque touche / clic de menu | **Légitime** : c'est `MenuPort.Send`. Seules les actions du joueur y passent. |
| 13 | `moteur.py:742` (`_finir_anims`) | efface le bit 0 de l'état d'une animation d'objet de carte (`table + idx * 32 + 0x14`) après une durée | après un paquet 5 (porte, coffre, jarre) | **Légitime** (émule le rappel « animation finie » d'Unity). **Risque** : la durée est estimée (`duree_anim` lue dans les données, sinon `DUREE_ANIM` constante) ; une durée fausse libère trop tôt ou trop tard un script qui attend la fin d'un coffre ou d'une porte. Pas un drapeau de scénario. Supposé exact. |
| 14 | `etats.py:46-50` (`appliquer`) | réécrit toute la mémoire du moteur (image de bibliothèque, tas, données, TLS) | chargement d'un état `.dqs` demandé par le joueur | **Légitime**. L'état vient du joueur ; la version est vérifiée (`VERSION`). |
| 15 | `moteur.py:60-64` (`h_fclose`) | l'écriture des fichiers de sauvegarde du moteur est redirigée vers `--saves-ecriture` | à la fermeture d'un fichier | **Légitime** : les vrais fichiers lus (`--saves-lecture`) ne sont pas modifiés (Établi par la lecture du code : `moteur.py:41, 53` écrit toujours dans `dossier_ecriture`, les originaux ne sont ouverts qu en lecture ; non vérifié par somme de contrôle). |
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
| **N3** capture GL de la visionneuse | un seul processus `fenetre.py` qui enchaîne les cartes (technique de `/tmp/audit/gl_casino.py` : on enveloppe `Jeu.tick` pour appeler `demarrer_ville(nom)` toutes les N images et on capture au milieu) | à écrire ; verrou `flock /tmp/xvfb.lock` | **Supposé** 4 à 6 s / carte (carte déjà en cache, 1280 x 720, Mesa) → **35 à 55 min**, plus ~2 min de préparation du cache au premier passage. Un lancement complet de la visionneuse avec deux captures prend de l'ordre de la minute (non chronométré avec précision ; démarrage du moteur et préparation du cache compris) | **non** : un seul xvfb à la fois (2 cœurs) ; ne rien lancer d'autre en même temps |

### 5.2 Sorties par carte

- N1 / N2 : un JSON par carte dans `/tmp/balayage/n1/<carte>.json` (le fichier global `bal2_tout.json` a le bon format, 411 Ko pour 529 cartes). Champs : `ok`, `exc` + `tb` (plantage), `pkts` (comptes par type), `vals` (valeurs distinctes des types rares), `f13`, `echelles`, `cams`, `bgm`, `se`, `modeles`, `fbx`, `sprites` (id + position finale + visible), `cam`, `ports` (type des fenêtres ouvertes), `msg`, `fondu`, `drapeaux`, `partie`, `t`.
- N3 : `/tmp/balayage/n3/<carte>_a.png` (image 60) et `_b.png` (image 180), plus un petit JSON (temps de chargement, nombre de groupes de la carte, message de journal).

### 5.3 Découpage en deux processus

`balayage.py` prend déjà `DEB FIN`. Deux processus sur les 2 cœurs : `python3 balayage.py 0 265 600 /tmp/balayage/n1_a.json` et `python3 balayage.py 265 529 600 /tmp/balayage/n1_b.json`. Chaque processus crée son propre moteur (`hl.nouveau(tag)` avec `tag = 'bal2_<DEB>'` → dossier d'écriture `/tmp/sv_audit_bal2_<DEB>`), donc pas de conflit. Le script **recrée le moteur et recharge la sauvegarde après chaque plantage** (sinon tout ce qui suit échoue en cascade : c'est ce qui a rendu inutilisable le premier balayage `bal_tout.json`). N3 passe seul, après N1 et N2.

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
4. **Sons** : l'existence et le décodage des 686 `.akb` ; `son.py` avale les erreurs.
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

## 7. Notes à fusionner dans les documents du Projet

À reprendre dans `notes-technique-portage-dq4.md` et `notes-visionneuse-dq4-pc.md` :
1. **Table des paquets avec statut** (§1) : remplacer la ligne « Table des paquets -> fonctions Unity » par la table avec les cinq statuts et les émetteurs.
2. **Paquet 33 `map_color_rate`** (§1.1) : émis à 171 / 529 cartes ; `cmd_map_color_rate` (0xD14E44) = `Field.SetColor(r, g, b, 1)` ; remplace la mention « `mlb1a` seulement » (`notes-technique:233`).
3. **Périmé** : « Lacunes : classes `IBase` personnalisées non reproduites » (`notes-technique`, section Interface d'origine) : les cinq classes sont portées (`ui_menu.py:199-413`).
4. **Parties du moteur** : 3 départ, 0xc ville, 0xd combat, 0xe carte du monde, **0xf casino, 0x10 bestiaire** (la visionneuse ne connaît pas 0xf ni 0x10) ; `Global::startCasino` ← `cmd_mini_game` ; `setMinigame(0)` = poker `ev04`, autre = machine à sous `ev05` ; `startBook` ← `TownMenuItemSelectCommand::menuUpdate` ; `startSurechigai` ← `cmd_change_surechigai_part`.
5. **Entrée clavier des menus** : les boutons de manette 0x2 / 0x1 (▲ ▼ de la mise du casino, quantités) sont inaccessibles au clavier si la fenêtre n'a pas de grille moteur.
6. **Pas de `startTown` pour tester l'arrivée** : le héros garde la position de la carte précédente.
7. **`g_Option + 5`** imposé par la visionneuse est enregistré dans les sauvegardes du jeu (§4).
8. **Mots de touches** : le moteur ne met le bit « A » du terrain que si `arg2 == 0x100` exactement (`Global::NativeExec`, 0x17d3d8-0x17d400) ; 0x400 → 0x20, 0x800 → 0x40, 0x1000 → 0x80, 0x2000 → 0x400 ; les menus du casino (`MaterielMenu_SLOT::menuUpdate`, `MaterielMenuPokerSelectcard`, `…Changecard`, `FIGHT_STADIUM::messageUpdate`) lisent ce mot directement (`scan_keyword.py`).
