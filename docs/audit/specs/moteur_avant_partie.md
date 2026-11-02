# Dragon Quest IV (Android) : le moteur avant la partie

Spécification côté moteur (`libdq4core.so`, C++ ARM64, exécuté sans modification sous Unicorn) de tout ce qui précède le jeu
proprement dit : démarrage, écran-titre, menu de départ, sauvegardes, nouvelle partie, saisie du nom, ouverture.
Elle sert de cahier des charges à la couche « Unity » réécrite en Python/pyglet (`dq4_pc/fenetre.py`).

Méthode : lecture du désassemblage (`/tmp/r2_asm/*.s`, 317 fichiers) **et** observation dynamique avec la sonde
`/tmp/specs/sonde_titre.py` (le moteur est piloté comme le ferait Unity : octets de manette + messages de menu).
Le dépôt `/home/claude/dq4-portage` n'a pas été modifié.

Conventions :
- les adresses sont des vaddr de la lib ; à l'exécution on ajoute `LIB_BASE = 0x10000000` ;
- « **Établi** » = vérifié par la sonde ou par un désassemblage sans ambiguïté ; « **Supposé** » = déduit, non vérifié (voir §9) ;
- touches de la visionneuse : A = ESPACE, B = RETOUR ARRIÈRE ; octets de manette du jeu : A 0x10, B 0x20, bas 1, haut 2, droite 4, gauche 8.

---

## 1. Résumé

1. Le moteur est piloté par quatre points d'entrée : `DevInit`, `MenuPortInit`, `GameInit`, puis `GameUpdate(tenu, nouveau)` à chaque image.
   Toute l'interaction « avant partie » passe par **des octets de manette** (titre) et **des messages de menu** `[1, case, pad]`
   déposés dans la file du port de la fenêtre active (menus).
2. Le titre se passe en deux appuis sur A (octet pad 0x10 en 2e argument de `GameUpdate`), séparés par un fondu. Le second lance
   `Global::startGame` puis la partie 3 (GameStart) qui ouvre `MaterielMenu_LOAD`, le vrai menu de départ.
3. Le menu de départ (fenêtre port 13, type 53) a 5 entrées de jeu (Continuer, Reprendre, Créer, Supprimer, Sauvegarde auto) plus
   Sauv. cloud et Licence. Les valeurs de cellule à renvoyer au moteur ne sont **pas** les numéros de ligne affichés : 0, 1, 2, 3, 4, 8 (cloud), 11 (licence).
4. Les sauvegardes sont `data1..5.dat` (15 360 octets chacun, chiffrement XOR par xorshift32 amorcé par un CRC32 de `"vb76Eg43"`) et
   `data9.dat` (512 octets, banque la plus récente). Un format et un chiffrement entièrement décodés, voir `/tmp/specs/dq4_sauvegarde.py`.
5. Nouveau jeu : choix d'une banque, saisie du nom (fenêtre type 55, clavier **local à Unity**, protocole `[2, longueur]` + octets UTF-8 empaquetés),
   choix du sexe (cases 0 = masculin, 1 = féminin), `makeDiary` (0x194a50) initialise tout, écrit la carte `mlb1a` et sauve la banque en type 4,
   puis `Global::startFirstTown()` démarre sur **mlb1a** (carte du prologue) et non sur ev01 ni mak1f1.
6. La visionneuse gère déjà le menu de départ, la liste des banques, Continuer et la confirmation de suppression. Il lui manque : les
   logos animés et le « Tap to start » du titre, **toute la saisie du nom / sexe**, l'écran Licence (écran noir bloquant), les messages du port 0
   (Quitter, Portail, volumes) et la vérification du prologue.

---

## 2. Séquence de démarrage et devoirs de l'hôte (a)

### 2.1 Points d'entrée

| Appel | Rôle | Établi |
|---|---|---|
| `DevInit(...)` | enregistre notamment le chemin de sauvegarde (`Backup_SetSavePath` 0x152b98). Chemin vide = sauvegardes désactivées (`IsEnable` 0x152bbc). | oui |
| `MenuPortInit` | crée les ports de menu (file de messages moteur/hôte). | oui |
| `GameInit` | initialise le jeu ; langue `g_lang` à lib+0x24f680 (0 = JA, sinon texte latin). | oui |
| `GameUpdate(tenu, nouveau)` | une image. 1er argument : boutons tenus, 2e : boutons nouvellement pressés. **Seul l'octet pad du 2e argument déclenche l'appui du titre.** Un message MenuPort `[1,-1,0x10]` sur le port 12 ne le déclenche pas. | oui |

À la première image, `GameUpdate` appelle `Global::startTitle` (drapeau statique 0x2582b8) : la partie initiale est donc le titre.

### 2.2 Parties du moteur (`Global+0xee`)

3 = GameStart (menu de départ), 0xc = Ville, 0xd = Combat, 0xe = Champ. Le champ « partie / suivante / précédente » (trois mots à
`Global+0xee`) permet à l'hôte de savoir quand une carte va changer.

### 2.3 Chronologie du titre (établi, sonde `--branche titre`)

| Étape | Image (environ) | Ce que fait le moteur | Devoir de l'hôte |
|---|---|---|---|
| Phase 1 : logo | 0 à ~60 | le logo se compose (paquet 22 : emplacement 2 → 12 sommets, puis emplacement 0 → 16 sommets, opacité par quad 184 → 255, textures m8900 / m8901 / m8905). Port 12 : fenêtre type 73 (`Make_TitleTouch`, **locale à Unity**, « TapToStart ») puis type 74 (`PortalButton`). | dessiner le logo, le « Tap to start », le copyright `Retro4_copyright`, le bouton Portail. |
| 1er appui A | dès ~image 5 | `cmd_fade_out(30)` 3 images plus tard, `MenuItem::SetItemCode(0,0)` en fin de fondu, `cmd_fade_in(30)`. | envoyer l'octet 0x10 (2e argument) pendant 1 image. |
| Phase 2 | pendant/après le fondu | un appui A **pendant** le fondu entrant est ignoré. | attendre la fin du fondu. |
| 2e appui A | après le fondu entrant | `cmd_start_game` 3 images plus tard, puis `Global::startGame`, puis partie 3 et `MaterielMenu_LOAD` ~30 images après. | idem. |
| Menu de départ | ~image 130 + 30 | fenêtre port 13 type 53 (StartMenuSecond) visible. | afficher le menu. |

Dans la sonde, les appuis sont donnés aux images 63 et 130 (`vers_menu_titre`) ; le fond du titre est la carte ev01 (partie 0xc, ville), la visionneuse y envoie ses appuis.
Établi : le 1er appui peut venir très tôt (image ~5) ; l'écran Retro4 / TapToStart n'est que visuel.

---

## 3. Le menu de départ (b)

### 3.1 Fenêtres, ports et types

Le moteur ouvre/ferme les fenêtres avec des messages sur le port 0 : `[N,1,cat,type]` ouvre la fenêtre N, `[N,2]` la ferme, `[N,3,vis]` règle sa visibilité.

| Port | Type | Nom moteur | Rôle |
|---|---|---|---|
| 12 | 73 | Make_TitleTouch | « Tap to start », **dessiné par Unity seul** (aucune cellule moteur) |
| 12 | 74 | PortalButton | bouton Portail → `[0,6]` |
| 12 | 12 | Make_Chapter | titre de chapitre (« Prologue ») pendant l'ouverture |
| 13 | 53 | StartMenuSecond | menu racine |
| 14 | 54 | StartMenuSelect | liste des banques (trois lignes, ou une seule pour Reprendre/Auto) |
| 15 | 55 | StartNameEntry | saisie du nom puis du sexe |
| 15 | 80 | License | écran de licence |
| 2 (dynamique) | 1 | YesNo | cases 0 « Oui » / 1 « Non » |
| — | 75 à 79 | Network | menu cloud (hors périmètre) |

`/tmp/uicache3/ui_layout.json` décrit 80 types ; 52-56, 74 et 80 y ont des nœuds, 73 seulement une erreur (type local à Unity).
Les notes du projet (`notes-visionneuse-dq4-pc.md`) disent le type 73 « inutilisé » : c'est inexact, c'est le Tap to start de Unity.

### 3.2 Menu racine (type 53)

| Libellé affiché | Cellule | **Valeur à renvoyer** `[1, valeur, 0x10]` | Genre (`LOAD+0x20`) | Remarques |
|---|---|---|---|---|
| Continuer votre aventure | (0,1) | **0** | 0 | liste des banques 0-2 |
| Reprendre une aventure interrompue | (1,1) | **1** | 3 | banque 3 (data4), une seule ligne |
| Créer un nouveau journal | (2,1) | **2** | 1 | |
| Supprimer un journal | (3,1) | **3** | 2 | |
| Sauvegarde automatique | (4,1) | **4** | 4 | banque 4 (data5) ; la cellule n'existe que si le bit 4 du statut est positionné |
| Sauv. cloud | (5,0) | **8** | | → `MaterialMenu_Network` |
| Licence | (6,0) | **11** (0xb) | | → écran Licence |

Les libellés et les valeurs divergent : la ligne affichée « (5,0) / (6,0) » n'envoie pas 5 ou 6 (qui sont des no-op, tout comme 7) mais 8 et 11. La valeur 9 mène à une ville de debug.
`g_isAmazon` (octet à lib+0x24f684) à 1 supprime la cellule « Sauv. cloud ». B sur la racine envoie `[0,999]` (Quitter, `MenuPortSendQuit`).

Grisage (`updateActiveDiary(statut)`) : `SetItemParam(cellule,0,3)` = désactivée. Les cellules 0 et 3 sont grisées quand aucune banque 0-2 ne contient de données (même corrompues) ;
la cellule 1 l'est quand le bit 3 (banque 3 valide) est à 0 ; la cellule 4 n'existe que si le bit 4 est à 1.
Le curseur par défaut (`LOAD+0x2c`) est la banque la plus récente (`catalogRecent`) si elle est < 3 et valide, sinon la première banque valide parmi 0-2.

### 3.3 Machine à états `MaterielMenu_LOAD` (établi)

État dans `[this+0x1c]` ; genre `[0x20]` ; banque `[0x2c]` ; statut `[0x30]` ; compteur `[0x24]`. Les 30 premières images sont un délai.

| État | Rôle |
|---|---|
| 0 | `rootUpdate` (menu racine) |
| 1 / 2 | `loadbank(3)` / `loadbank(4)` (préparation de Reprendre / Auto) |
| 3 | prépare la liste (`SetItem`), puis 4 |
| 4 | `dataSelectUpdate` (liste de banques) |
| 6 | NameEdit actif (`changeStatus(6)` : `NameEdit[0x1a]` = banque, ferme LOAD, ouvre NameEdit, `setNameEditMode`) |
| 7 | `makeDiary` (création du journal) |
| 8 | suppression en cours (message, `killbank`) |
| 9 | `loadbank(banque choisie)` puis 0xb |
| 0xb | `MenuBase::close` : chargement fini, `GameStartPart` lance ensuite la ville/le champ |
| 0xc | erreur : ferme tout et `Global::startTitle` |
| 0xd | message d'information, retour à l'état 0 |
| 0xe, 0xf, 0x10 | Licence : fondu noir, affichage, fin de fondu, retour à 0 |

Résultat Oui/Non : `TownMenu_MESSAGE+0x10` vaut 1 (Oui) ou 2 (Non). La fenêtre YesNo est le type 1 sur un port dynamique (2), cases 0 « Oui » / 1 « Non ».

### 3.4 Liste des banques (type 54)

Contenu observé (sonde, banque 0 valide, banque 1 type 4, banque 2 vide) :

| Cellule | Texte |
|---|---|
| (0,1) | `@c51: Solo@c0` (code couleur `@c5` pour la ligne sélectionnée, `@c0` sinon) |
| (0,2) | `@c5Chapitre 1 Nv. 1 001:06\n Strattbourg@c0` |
| (1,1) / (1,2) | `2: Sofia` / `       000:00` (sauvegarde de type 4) |
| (2,1) / (2,2) | `Inutilisé` / (vide) |
| (3,0) | titre de la liste (« Continuer \nvotre aventure ») |
| code (3,v) | mode de liste : 0 = trois lignes, 2 = une seule ligne (Reprendre / Auto : `   Solo` / `Chapitre 1 Nv. 1 000:41`) |

Durée de jeu : unité 1/60 s (heures = f / 216 000, minutes = (f % 216 000) / 3600). Libellé de niveau : « Nv. ».
Le saut de ligne dans un libellé est écrit `; `. Un clic/appui sur la ligne i envoie `[1, i, 0x10]` au port 14 (i = banque).

**Source des données** : `profile::SaveLoad::getCatalogView()` (0x19a9ec), 5 entrées de 0x60 octets à vaddr 0x259b94 :

| Offset | Contenu |
|---|---|
| +0 | statut (1 valide, -1 vide/neuve, -2 somme de contrôle invalide, -3 illisible ou taille erronée) |
| +4 | octet « valide » |
| +8 | octet 0x0c du fichier |
| +0xc | nom du héros (0x20 octets) |
| +0x4c | octet 0x0d du fichier (SAVETYPE) |
| +0x50 | chapitre |
| +0x54 | niveau |
| +0x58 | identifiant du texte de lieu |
| +0x5c | durée de jeu |

`getCatalogStatus` (0x19af88) : bits 0-4 = banque valide, bits 5-9 = illisible (-3), bits 10-14 = corrompue (-2), bit 15 = un fichier de banque manque. Exemple observé : 27 (banques 0, 1, 3, 4 présentes).

### 3.5 Flux Continuer (établi)

1. Racine : `[1,0,A]` → liste (genre 0).
2. Banque valide `[1,b,A]` → état 9 : `loadbank(b)` → 0xb → fermeture → `GameStartPart` charge la ville (partie 0xc) : dans l'échantillon, mak1f1 (église) environ 30 images plus tard.
3. Banque vide : message 833003 « Créer un nouveau journal ? » + Oui/Non ; Oui → saisie du nom (voir §5), Non → retour à la liste.
4. B → retour à la racine.
5. Reprendre / Auto (genre 3 / 4) : liste d'une ligne, charge ensuite le **champ** (partie 0xe).

### 3.6 Flux Créer

1. Racine : `[1,2,A]` → liste (genre 1).
2. Ligne vide : saisie du nom directement. Ligne occupée : message 833007 « Supprimer ce journal et en créer un nouveau à la place ? » + Oui/Non (Oui → saisie du nom, Non → liste).
3. Suite au §5.

### 3.7 Flux Supprimer (établi)

1. Racine : `[1,3,A]` → liste (genre 2).
2. Ligne occupée : message de confirmation 833022 (833025 si chapitre > 4, 833040 pour une sauvegarde de type 4 : « Voulez-vous vraiment effacer « … » ? ») + Oui/Non.
3. Oui → état 8 : message 833028 « Suppression du journal en cours… », `killbank(banque,false)` écrit 15 360 octets avec l'en-tête `DLED`, puis 833029 « Journal supprimé. » qui attend un A, puis état 0.
4. Le bit de statut est effacé (27 → 25). Le texte de la liste n'est **pas** rafraîchi tant qu'on ne la rouvre pas. Non revient à la liste.

### 3.8 Autres sorties

- **Licence** : `[1,11,A]`, `fadeOutBlack`, état 0xe → 0xf → 0x10 → 0. Fenêtre type 80 sur le port 15.
- **Quitter** : B sur la racine → port 0 `[0,999]`. L'hôte doit fermer l'application.
- **Portail** : `[0,6]` (bouton PortalButton, ouvrir l'URL du portail du jeu).
- **Cloud** : valeur 8, `MaterialMenu_Network` (types 75-79). Non implémenté : masquer la cellule (`g_isAmazon = 1`) ou l'ignorer.
- **Retour au titre** : `Global::startTitle` est appelé par `GameUpdate` (1re image), `TownMenu_OPERATION_ROOT`, `TownMenu_OPERATION_SETTING`, LOAD (état 0xc), SAVE (`commandUpdate`), `TownEndrollManager::execute`,
  `TownOpeningManager::draw` (boucle d'attraction) et `cmd_set_title_part`. Il existe aussi un chemin de debug `g_UnityDebug` (« ev01 »).

---

## 4. Textes (annexe des identifiants, établi)

### 4.1 Mécanisme

`TextAPI::extractText(char*, int)` (0x17f750) sépare l'identifiant en un quartet de type `id & 0x0f000000` et une valeur de 24 bits :

- type `0x08000000 | N` → `macro_getMacroStat(7, 1004000+N)`, fichier `b1004000.mpt`, identifiant global 1004000+N ;
- types `0x0a00000N` et `0x0c00000N` : autres genres de macro (`0x0a000321` = « Inutilisé » ; `0x0a000013` = « Niv. » ; `0x08000032` = texte de lieu par défaut) ;
- type 0 (messages `TownMenu_MESSAGE`) : `MsgData::msg_find(L+0x258a18, id)` puis la chaîne à `[L+0x258a80]` ; fichier = (id/1000)*1000.

`TextAPI::getMessage` **se bloque** sous émulation (environ 90 s par appel) : ne pas l'utiliser.

### 4.2 Libellés du titre (`b1004000.mpt`, N = id & 0xffffff)

| N | Texte | N | Texte |
|---|---|---|---|
| 406 | Continuer votre aventure | 413 | Àà |
| 407 | Créer un nouveau journal | 414 | Aa |
| 408 | Supprimer un journal | 415 | Reprendre une aventure interrompue |
| 409 | Retour | 416 | Saisir un nom |
| 410 | Fin | 417 | Choisir le sexe |
| 411 | Katakana | 623 | Sauvegarde automatique |
| 412 | Hiragana | 635 | En ligne (JA) |
| | | 637 | Sauv. cloud |
| | | 645 | Licence |

### 4.3 Messages du menu LOAD (`b0833000.mpt`, identifiants globaux)

| Id | Texte | Quand |
|---|---|---|
| 833003 | Créer un nouveau journal ? | Continuer sur une banque vide |
| 833007 | Supprimer ce journal et en créer un nouveau à la place ? | Créer sur une banque occupée |
| 833011 | Désolé, ce nom ne peut pas être utilisé. | `CheckBadWord` |
| 833015 | Création du journal en cours… | après le sexe |
| 833018 | Échec de la création… | échec de `savebank` |
| 833022, 833025 | confirmation de suppression (833025 pour chapitre > 4) | Supprimer |
| 833040 | Voulez-vous vraiment effacer « … » ? | sauvegarde de type 4 |
| 833028 | Suppression du journal en cours… | état 8 |
| 833029 | Journal supprimé. | |
| 833032 | Échec de la suppression… | |
| 833035 | Impossible de lire le journal… | chargement |
| 833038 | Une version corrompue du journal a été trouvée et effacée. | |
| 833047 | Espace insuffisant… | |

Ces textes contiennent des macros : `%a00660` (banque), `%a00090` (nom du héros), `%A090%X..%Z` (accords selon le sexe).

---

## 5. Nouveau jeu : nom, sexe, création (d)

### 5.1 Fenêtre de saisie (type 55, port 15)

Machine à états de `MaterielMenu_NameEdit` (mot d'état à 0x259b84) :

| État | Rôle |
|---|---|
| 0 | init : `SetItemCode(0, mode)` avec mode 8 (hors JA) ou 4 (JA), `SetItemCode(1, 1)` |
| 1 | clavier : `InputName`, **local à Unity** (la fenêtre 55 n'est pas visible ; codes {0:8, 1:1}) |
| 2 | nom reçu : `CheckBadWord`, sinon message 833011 et retour à 1 |
| 3 | choix du sexe |

L'état 3 présente : (0,0) « Choisir le sexe », (1,0) le nom, (2,0) « Masculin », (3,0) « Féminin ».
Cases envoyées : 0 = masculin, 1 = féminin ; la valeur est stockée à 0x259b5c ; `getGender()` = (valeur != 0).
Après le sexe : message 833015 puis état LOAD 7.

### 5.2 Protocole du nom (établi côté moteur)

`MenuItem::NoticeFromUnity` (0x15445c) lit `m[0]` = nombre d'entiers, `m[1]` = code :

| Code | Effet |
|---|---|
| 1 | `[1, idx, pad]` : sélection (pad 0x10 A, 0x20 B, directions 1/2/4/8) ; relâché par `[1,-1,0]` |
| 3 | `[3, pos]` règle `g_pad_pos` |
| autre | appelle le rappel de `SetUnityOtherReceive`, qui dépile le message suivant avec `MenuPort::Receive()` |

Pour le nom : envoyer `[2, longueur_en_octets]` puis un message dont les « shorts » sont les octets UTF-8 empaquetés deux par short, petit-boutiste. 30 octets au plus sont copiés vers 0x259b5e.
Le code 2 est vérifié ; le code que Unity utilise vraiment n'est pas connu (tout code ≠ 1 et ≠ 3 arrive au rappel).
Le sexe se donne ensuite par `[1, 0|1, 0x10]` sur le port 15.

### 5.3 `makeDiary` (0x194a50)

Dans l'ordre :
1. `g_pad_pos` et `g_pad_size` = 1, puis `MenuPortSendPosPadSize` ;
2. initialisation `PartyTalk`, `Status`, `Encount` ; remise à zéro des pièces, de la banque, du tarot, etc. ;
3. `Story[8]` = sexe & 1 ; `setEventParty(0)` ; durée de jeu 0 ; `resetUniqueID` ; `setHeroName(nom UTF-8)` ;
4. si `g_lang != 0` : `MenuPortSendHeroNameSize` (message `[0,7,w,w]`) ;
5. `Global::setMapName("mlb1a")` ;
6. `savebank(NameEdit[0x1a], 4)` ; en cas de succès, `Global::startFirstTown()` (sinon message 833018).

### 5.4 Ouverture observée sur mlb1a (établi)

- Image ~281 : chargement de la carte, puis `cmd_player_lock`, `cmd_fade_out2`, `cmd_event_chapter_title` (port 12 type 12, texte « Prologue », ~200 images), `Global::fadeInBlack(60)`.
- Ensuite `cmd_fade_in2`, `cmd_effect_transfer`, `cmd_set_se`, `cmd_map_camera_gaze`, `cmd_key_wait_type_b` (attend un A), `cmd_message1(0x30d45 = 200005)` (scène d'entraînement : « Eh bien alors, [nom] ?… ») puis `cmd_menu_yes_no`.
- Le Oui/Non générique est le type 1 sur le port 2 ; on y répond par `[1, case, pad]` et **non** par l'octet pad.
- Le nouveau jeu ne passe donc ni par ev01 ni par mak1f1 (mak1f1 est la position de la banque 1 de Sylfried : 1 h 06, « Quelle joie de vous revoir, Ragnar ! »).

Valeurs initiales après `makeDiary` : durée de jeu 0, carte `mlb1a`, SAVETYPE 4, sexe selon le choix, banque = celle choisie. Le chapitre, le niveau et les statistiques initiales du groupe n'ont pas été relevés (la ligne de liste d'une sauvegarde de type 4 affiche seulement « 000:00 »).

---

## 6. Fichiers de sauvegarde et API (c)

### 6.1 Fichiers

| Fichier | Taille | Contenu |
|---|---|---|
| `data1.dat` à `data3.dat` | 0x3c00 (15 360) | banques 0-2 : trois journaux manuels |
| `data4.dat` | 15 360 | banque 3 : suspension (Reprendre) |
| `data5.dat` | 15 360 | banque 4 : sauvegarde auto |
| `data9.dat` | 512 | premier dword = banque la plus récente (`catalogRecent`) ; « DWEN » → 0 |

Sans fichier, le moteur crée `data1..5.dat` et `data9.dat` (« DWEN ») à la construction du catalogue : le dossier doit être inscriptible.

### 6.2 Chiffrement (`Cryption::Filter`, 0x152de8, conserve la taille)

- graine = CRC32 bit à bit de la chaîne `"vb76Eg43"` (polynôme 0x7a7b58c6, init 0xffffffff, inversion finale) ;
- état = xorshift32 (`<<13`, `>>17`, `<<5`) ; chaque octet est XORé avec l'octet de poids faible de l'état.

### 6.3 Disposition en clair d'une banque

| Offset | Contenu |
|---|---|
| +0 | u32 `0x65747261` (« arte ») |
| +4 | u32 `0x0bf697de` |
| +8 | u32 somme de contrôle : somme des octets des 0x3660 premiers octets, champ mis à zéro |
| +0xc | étage / banque (`g_Stage[0x2b0]`) |
| +0xd | SAVETYPE |
| +0xe, +0xf | `g_pad_pos`, `g_pad_size` |
| +0x10 | nom de carte (chaîne) |
| +0x30 | chapitre |
| +0x24c | identifiants de 14 personnages |
| +0x25c | durée de jeu (u32, 1/60 s) |
| +0x497 | nom du héros (0x20, UTF-8) |
| +0x4b7 | sexe (0 homme, 1 femme) |
| +0x109d | table de niveaux (pas 0xc8, 14 entrées) |
| 0x3660 – 0x3c00 | rempli de 0xff |

Banque vide : premier dword `DWEN` (0x4e455744, `killbank(n,true)`) ; supprimée : `DLED` (0x44454c44, `killbank(n,false)`, ramenée à `DWEN` au prochain `getCatalogView`).
Le moteur n'a aucune fonction de copie ; la synchronisation cloud est dans le menu Network.

SAVETYPE : 1/2 = sauvegarde manuelle (variantes du menu SAVE) ; 3 = suspension (`savebank(3,3)` depuis `TownMenu_OPERATION_ROOT`) ou sauvegarde auto (`AutoSave` 0x164aa8 → `savebank(4,3)`) ; 4 = nouveau jeu.

Vérifications sur l'échantillon de Sylfried : data1 = « Solo », type 1, carte mak1f1, 239 246 images ; data2 = « Sofia », type 4, mlb1a, sexe 1 ; data3 = DWEN ; data4/5 = « Solo », type 3, carte « field » ; data9 = banque 0.

### 6.4 API moteur (adresses)

| Fonction | Adresse | Remarque |
|---|---|---|
| `getCatalogView` | 0x19a9ec | 5 × 0x60 octets à 0x259b94 |
| `getCatalogStatus` | 0x19af88 | masque de bits |
| `getCatalogRecent` | 0x19b050 | banque la plus récente |
| `getSaveBank(bool)` / `setSaveBank(int)` | 0x19aed8 / 0x19b344 | |
| `memoryload(u32, void*, u32)` | 0x19ac74 | fichier absent → zéros + `DWEN`, renvoie 1 |
| `memorysave` | 0x19b2ac | |
| `killbank(int, bool)` | 0x19ae24 | bool = vide (`DWEN`) ou supprimée (`DLED`) |
| `loadbank(int)` | 0x19b060 | banque numérotée à partir de 0 |
| `savebank(int, SAVETYPE)` / `savebankAsync` | 0x19b2c8 / 0x19b3a0 | |
| `getPlaceNameNo` / `getPlaceNameByChapter` | 0x19ace8 / 0x19adfc | |
| `setCatalogMacro` | 0x19b4e8 | |
| `Profile::collectDATA` / `deliverDATA` | 0x19b824 / 0x19c284 | |
| `calcCheckSum` / `isValidData` | 0x19b78c / 0x19b800 | |
| `Backup_Exist` / `GetSize` / `Write` / `Read` | 0x152bd0 / 0x152cc4 / 0x152d28 / 0x152e58 | `Read` renvoie 0 en cas de succès |

Pour l'hôte : les appels de fichier du moteur (`fopen`/`fclose` sur `data%d.dat`) sont déjà ponts dans `dq4_pc/moteur.py` (`CoreJeu.h_fopen/h_fclose`) ; `charger_sauvegarde(numero)` = `loadbank(numero-1)`.

---

## 7. Ce que la visionneuse gère déjà (e)

Établi par captures réelles (`/tmp/specs/img/viewer_*.png`) :

| Fonction | État | Capture |
|---|---|---|
| Phase 1 du titre (sans logo ni Tap to start) | partiel | `viewer_titre_phase1.png` |
| Menu racine (type 53) et bouton Portail (74) avec la disposition d'origine | oui | `viewer_menu_titre.png` |
| Liste des banques (type 54), couleurs, « Inutilisé », bouton Retour | oui | `viewer_liste_continuer.png` |
| Continuer → chargement de mak1f1 avec message | oui | `viewer_continuer_charge_mak1f1.png` |
| Supprimer : message de confirmation + fenêtre Oui/Non | oui | `viewer_supprimer_confirmation.png` |
| Créer → saisie du nom | **rien n'est affiché** | `viewer_nouveau_nom_rien_affiche.png` |
| Licence | **écran noir, bloqué** | `viewer_licence_ecran_noir.png` |

---

## 8. Lacunes de `dq4_pc/fenetre.py` (liste concrète)

Par ordre d'importance pour le joueur :

1. **Saisie du nom et du sexe (type 55)** : aucun rendu, aucun clavier. À faire : afficher un champ + clavier (ou saisie clavier physique) ; sur validation, envoyer `[2, n]` puis les octets UTF-8 empaquetés par deux (petit-boutiste, 30 octets au plus) ; attendre le choix du sexe (fenêtre 15 : « Choisir le sexe », nom, Masculin / Féminin) et répondre `[1, 0|1, 0x10]`. Gérer B (retour). Afficher le message 833011 si le nom est refusé, 833015 pendant la création.
2. **Écran Licence (type 80)** : l'écran reste noir après `fadeOutBlack`. À faire : rendre la fenêtre 80 (texte de licence) et renvoyer un A ou un B pour revenir (états LOAD 0xf → 0x10 → 0 ; l'entrée qui termine l'état 0xf est supposée, non vérifiée).
3. **Logos et Tap to start** : dessiner les maillages du paquet 22 (emplacement 2 → 12 sommets, emplacement 0 → 16 sommets, opacité par quad 184 → 255, textures m8900 / m8901 / m8905), la texture locale `taptostart`, `Retro4_copyright`. Le ciel d'ev01 montre des bords noirs mobiles.
4. **Messages du port 0 ignorés** : `[0,999]` (Quitter : fermer l'application), `[0,6]` (Portail : ouvrir le portail), `[0,4,v]` (volume SE), `[0,5,v]` (volume BGM), `[0,7,w,w]` (taille du nom du héros, hors JA), `[0,8,pos,size]` (position/taille de la manette).
5. **Menu cloud (valeur 8, types 75-79)** : non géré ; poser `g_isAmazon = 1` pour retirer la cellule ou ignorer la valeur.
6. **Cellules grisées** (`SetItemParam(cellule,0,3)`) : rendu non vérifié dans la visionneuse.
7. **Clic souris au titre** : non vérifié ; un clic doit produire un octet pad 0x10 en 2e argument de `GameUpdate`.
8. **Prologue d'un nouveau journal** (titre de chapitre type 12, attente de touche, message + Oui/Non) : non vérifié dans la visionneuse.
9. **Raccourci `--slot N`** : charge directement (`loadbank`) et contourne le titre ; à garder pour le test, mais ne passe par aucun écran de départ.
10. **Rafraîchissement de la liste après suppression** : le moteur ne rafraîchit pas les textes, ce qui est le comportement d'origine ; ne pas chercher à le corriger.

---

## 9. Établi / supposé et inconnues

| Sujet | Statut |
|---|---|
| Séquence des deux appuis A, durées des fondus | **établi** (sonde) |
| Fenêtres, ports, types, libellés du titre | **établi** |
| Valeurs de cellule 0/1/2/3/4/8/11 et leur effet | **établi** (sonde pour 0-4 ; 8 et 11 par désassemblage et sonde de Licence) |
| Machine à états LOAD | **établi** (désassemblage + sonde) |
| Format, taille, chiffrement, somme de contrôle des banques | **établi** (échantillons réels déchiffrés, somme de contrôle concordante) |
| Protocole du nom (`[2,n]` + octets empaquetés) | **établi** côté moteur |
| Code exact de message que Unity utilise pour le nom | **supposé** (tout code ≠ 1, 3 convient) |
| Façon dont `TitleTouch` de Unity convertit le clic en appui A | **supposé** |
| Différence sémantique entre SAVETYPE 1 et 2 | inconnu |
| Effets de `g_isAmazon` au-delà de la cellule cloud | inconnu |
| Sens des entiers sans libellé des fenêtres ; disposition exacte du maillage du paquet 22 | inconnu |
| Minuterie de la boucle d'attraction (`TownOpeningManager`) | lecture de code seule |
| Suite du prologue après le Oui/Non | non explorée |
| Clavier `InputName` d'Unity (disposition, longueur maximale, boutons Katakana/Hiragana pour JA) | inconnu |

---

## 10. Reproduction

Sonde (aucune écriture dans le dépôt ; sauvegardes dans un dossier temporaire) :

```
python3 /tmp/specs/sonde_titre.py                       # toutes les branches, sauvegardes d'exemple de Sylfried
python3 /tmp/specs/sonde_titre.py --branche titre menu continuer
python3 /tmp/specs/sonde_titre.py --branche nouveau supprimer --lecture -    # premier lancement (aucune sauvegarde)
python3 /tmp/specs/sonde_titre.py --lecture /chemin/saves --apk /chemin/patched_apks
```

Branches : `titre menu continuer reprendre auto nouveau supprimer licence quitter toutes`.
Défauts : APK `/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks` ; sauvegardes `/mnt/user-data/uploads/Downloads/DQ Patch/jeux/DQ4/saves/20261007_190735`.
Sorties vérifiées : `/tmp/r2_work/sonde_a.out`, `/tmp/r2_work/sonde_b.out`.

Analyse d'une sauvegarde :

```
python3 /tmp/specs/dq4_sauvegarde.py data1.dat [--dump]
```

Visionneuse sans écran (une exécution xvfb à la fois) :

```
/tmp/r2_work/runv.sh ETIQUETTE "touches" "captures" [delai]
```

Syntaxe des touches de test : `N:NOM`, `+NOM` / `-NOM`, `@x@y` (clic en pixels depuis le coin haut gauche).

Captures : `/tmp/specs/img/` (`viewer_*.png`, `tex_taptostart*.png`, `tex_Retro4_copyright*.png`, `tex_m8900.png`, `tex_m8901.png`, `tex_m8905.png`).
