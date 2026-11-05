# Audit : croix tactile, fenêtres de carte, compteur de quantité, boutons mobiles

Portage PC de Dragon Quest IV (Android) : dépôt `/home/claude/dq4-portage` (lu seulement, rien modifié).
Sources d'origine : `libil2cpp.so` (couche Unity C#, RVA = adresse virtuelle, offset fichier = RVA - 0x4000), `/home/claude/il2/dump.cs`, `/tmp/libdq4core.so` (moteur C++), `/tmp/uicache/ui_layout.json` (mise en page exportée), scène `level1` (UnityPy).
Repère d'origine : interface de 450 unités de large, portrait de référence 450 x 800 (haut z = +400, bas z = -400 ; `NotchFix.AdjustmentValue` = 0 sur PC). Le portage convertit par `H / 800`.

Légende des verdicts : **fidèle** / **approché** (bon principe, valeur fausse) / **faux** / **absent** / **inventé** (rien dans l'original).
Chaque section sépare **Établi (preuve)** (lu dans le code ou les données, RVA ou chemin cité) de **Supposé** (déduit, à confirmer).

Scripts reproductibles : voir la dernière section. Valeurs dérivées : `python3 -I /tmp/specs/scripts/audit_valeurs.py`.

---

## 1. TouchPad : croix tactile (`UnityEngine`, `TouchPad : MonoBehaviour`, dump.cs ligne 264989)

RVA : `SetPadBlink 0xD227A4`, `SetActivity 0xD22920`, `SetPosPadSize 0xD22DE4`, `SetPadPos 0xD22E60`, `IconVisible 0xD23254`, `IsTouchMap 0xD23358`, `Awake 0xD234BC`, `SetVisibleColMove 0xD2359C`, `CreateMenuButton 0xD2377C`, `CalcScreenPosition 0xD23938`, `MoveCheck 0xD23C2C`, `internalUpdate 0xD241B4`, `FixedUpdate 0xD2538C`.

### 1.1 Établi (preuve)

**Échelles (`c_PadScaleTBL`, FieldRVA)** : `(1.225, 1.0, 0.775)`, indexées par `g_pad_size` (0 Grande, 1 Moyenne = défaut, 2 Petite). L'ordre est confirmé ; `SetPadPos` pose `MPad.localScale = 0.63 x TBL[g_pad_size]` (`c_PadBaseScaleXY = 0.63`).

**Anneau** : maillage `MPad` (scène `level1`, objet `PadRoot`) = quad de -128 à +128, uv 256..512 de la texture `Button` ; diamètre = 256 x 0.63 x sc :

| g_pad_size | sc | diamètre (unités) | rayon |
|---|---|---|---|
| 0 Grande | 1.225 | 197.57 | 98.78 |
| 1 Moyenne | 1.0 | 161.28 | 80.64 |
| 2 Petite | 0.775 | 124.99 | 62.50 |

**Pastilles** (maillages `Dirs`, `DirNormal`, `DirLight`) : quads de 128 x 64 (uv `Button` 384..512 x 192..256 pour la normale, 256..384 x 192..256 pour l'orange), **centre à 104 unités locales** de l'origine de l'anneau (les quads s'étendent radialement de 72 à 136). `Dirs` contient 7 quads (tous les secteurs sauf le bas) ; `DirNormal` / `DirLight` sont le huitième (bas), l'objet `Dirs` est tourné de `-45 x secteur + 270` degrés (`MoveCheck` 0xD24088). Donc 8 pastilles toujours visibles, dont une orange quand une direction est tenue.
**Boule** `CurNomal` (uv 448..512 x 128..192, quad 64 x 64), `CurLight` (boule orange, uv 384..448), `CurBS` (halo, uv 320..384).

**Seuils** (champs statiques, valeur de base x sc) : zone morte `c_MoveThreshold` = 10 ; course de la boule `c_moveNakaLimit` = 36.5 ; départ du déplacement `c_MoveBeginLimit` = 16 ; `c_AnyThreshold` = 8 ; `c_MoveRingLimit` = 56 ; `c_MoveReversLimit` = 8 ; rayon du collider de prise `c_padColRad` = 95. Rapportés au rayon de l'anneau (80.64 à sc = 1) : zone morte **0.1240**, course de la boule **0.4526**, départ 0.1984, any 0.0992, ring limit 0.6944, collider **1.178**.
La boule (`m_siMovePad`) suit le doigt à `colMove.position + décalage` borné à 36.5 x sc (`MoveCheck` 0xD23E78..0xD23F1C : normalisation si `d² > nakaLimit²`).

**Secteurs** : `((int((deg + 180) / 22.5) + 1) >> 1) & 7` (secteurs de 45 degrés centrés sur les 8 directions, `MoveCheck` 0xD23FFC..0xD2407C) ; `c_padDirTable = (4, 6, 2, 10, 8, 9, 1, 5)` en bits `PAD_U = 1, PAD_D = 2, PAD_L = 4, PAD_R = 8` donc (gauche, gauche+bas, bas, bas+droite, droite, droite+haut, haut, haut+gauche). Le portage (`hud_mobile.py:233`, secteur 45 degrés) donne les mêmes huit directions.

**Position par défaut** (`SetPadPos` 0xD22E60, `SetPosPadSize` 0xD22DE4) : `PAD_POS_LEFT = 0, CENTER_LEFT = 1, RIGHT = 2, CENTER_RIGHT = 3`. x du centre : pos 0 = -120, pos 2 = +120, pos 1 et 3 = 0 ; pour pos 0/2 un décalage supplémentaire de 80 x (1 - sc) vers l'extérieur ; z = 134.5 - 80 x (1 - sc) au-dessus du bas (ancre `CenterBottom`, indent 7). **Défaut du moteur : `g_pad_pos = 1`, `g_pad_size = 1`** (`MaterielMenu_LOAD::makeDiary` 0x194A50) : croix au milieu en bas, x = 0.

**États** (`ePadState`) : `NONE 0, MOVE_BEGIN 1, MOVE 2, ROT_OR_FLICK 3`. Un tap court sans mouvement envoie `PAD_ANY = 256` (0x100). Barre de rotation de la caméra `l_RotBar` (objet de la croix, activé/désactivé dans `MoveCheck`), constantes `c_RotThreshold = 8`, `ROT_PRESS_HIT_X = 160`, `c_rotResetWidth = 20` (dump.cs) ; sémantique (rotation de la caméra par glissement hors de la croix) supposée.

**Visibilité** : `SetVisibleColMove` (0xD2359C) : `CurNormal = b & ~l_padBlink` ; `CurLight` et `CurBS` activés **seulement si `l_padBlink`** (statique 0x8C, posé par `SetPadBlink`, c'est le clignotement du **tutoriel**, halo pulsant de 1.0 à 1.5 sur 1 s) ; `Dirs = b` ; `DirLight = ((m_press & 0xF) != 0) & b` ; `DirNormal = ((m_press & 0xF) == 0) & b`.
`IconVisible(b)` (0xD23254) : PadPos, Command, Talk = `b` ; Map = `IsTouchMap & b` (`Global.Flag` : `IsTouchDir = IsEnable(8)`, `IsTouchRot = IsEnable(0x10)`, `IsTouchMap = IsEnable(0x20)`, `IsEnable(a) = (Flag & (0x30047 | a)) == a`).

**Transparence** : `MOVE_WAIT_TIME = 0.5` et `MOVE_LIMIT_ALPHA = 0.4` sont déclarées (dump.cs) mais **aucun code de `TouchPad` (0xD227A4..0xD25A00) ne charge un littéral 0.4 ni n'appelle `set_color`** : constantes mortes. L'anneau est toujours opaque.

**Son** : seul `SE 300` sur le bouton PadPos et les boutons du HUD (`CreateMenuButton` / `internalUpdate`) ; aucun son pour la croix elle-même.

**Flottement** : `SetPadPos` n'a que 3 appelants (`SetPosPadSize`, `Start`, `internalUpdate` pour le bouton PadPos). Aucun code ne déplace l'anneau vers le doigt ; ce qui suit le doigt est la boule (`m_siMovePad`, bornée à 36.5 x sc du centre du collider).

### 1.2 Comparaison avec `dq4_pc/hud_mobile.py`

| Élément | Original (établi) | Portage | Verdict |
|---|---|---|---|
| Facteurs de taille | 1.225 / 1 / 0.775 | `ECHELLE_CROIX = (1.25, 1.0, 0.75)` (l.27) | approché : remplacer |
| Diamètre moyen | 161.28 (= 256 x 0.63) | `DIAM_CROIX = 165.0` (l.26) | approché (+2.3 %) : 161.28 |
| Position des pastilles | centre à 104/256 = **0.40625** du diamètre | `RAYON_PASTILLE = 85/256 = 0.332` (l.28) | **faux** : 0.40625 (pastilles 19 unités/256 trop près du centre) |
| Zone morte | 0.1240 R | `ZONE_MORTE = 0.15` (l.30) | approché : 0.124 |
| Course de la boule | 0.4526 R | `COURSE_BOULE = 0.5` (l.29) | approché : 0.4526 |
| Prise de la croix | collider de 95 x sc = 1.178 R | appui « dans l'anneau » (R) (`croix_glisser`) | approché : zone de prise 1.178 R |
| Secteurs | 8 secteurs de 45 degrés | idem (l.222-233) | **fidèle** |
| Fondu à 40 % après 0.5 s | **absent** (constantes mortes) | `ATTENTE_CROIX, ALPHA_CROIX = 0.5, 0.4` (l.31, 285) ; alpha 0.95 tenue | **inventé** (déduit des noms de constantes inutilisées) |
| Boule orange + halo quand une direction est tenue | boule orange et halo **seulement en clignotement tutoriel** ; seule la pastille de la direction devient orange | `poser('halo')` + `boule_on` dès qu'un secteur est tenu (l.296-297) | **faux** : garder `boule` normale, pas de halo (sauf éventuel mode tutoriel) |
| Pastille orange | 1 pastille (secteur tenu), les 7 autres normales | `pastille_on` sur le secteur tenu (l.295) | fidèle |
| Position par défaut | `g_pad_pos = 1` : centre-bas, x = 0 | en bas à droite, `g_pad_pos` ignoré | choix assumé (retour du 01/11/2026 : boutons à gauche) ; non fidèle |
| Barre de rotation caméra `l_RotBar` | rotation au doigt hors croix | absente | absent (sans objet à la souris) |

### 1.3 Boutons du HUD (`TouchPad.CreateMenuButton` 0xD2377C)

Plaque = `(w x 40 + 32) x (w x 32 + 32)` pour une taille `s` ; icône = `48 x iconSize` (feuille 3 de `MenuTexture`) ; touches `PAD_Y = 0x1000`, `PAD_X = 0x800`, `PAD_B = 0x400`.

| Bouton | Touche | Icône | Taille | Plaque | Icône (unités) | Position du centre |
|---|---|---|---|---|---|---|
| Carte (`l_btMap`) | 0x1000 | 3 | 1.0 | 72 x 64 | 57.6 (x 1.2) | x = ±44, z = -12 depuis le haut ; ancre `RightTop` si la croix est à gauche (pos 0/1), sinon `LeftTop` ; profondeur -32 |
| Commandes (`l_btCommand`) | 0x800 | 4 | 1.0 | 72 x 64 | 57.6 | x = ±44, z = 278 depuis le bas |
| Discussion (`l_btTalk`) | 0x400 | 15 | 0.775 | 63 x 56.8 | 48 | x = ±39.5, z = 188 |
| Position de la croix (`l_btPadPos`) | 0 | 17 | 0.55 | 54 x 49.6 | 48 | x = ±35, z = 104.5 ; fait cycler `l_padPos`, SE 300 |

Colonne du bas : `LeftBottom` (indent 6) si la croix est à droite (pos 2/3), sinon `RightBottom` (indent 8).
Pas de bouton « Mode de la carte » dans `TouchPad` : il appartient à la fenêtre `MapButton` (section 4).

Portage (`hud_mobile.py:18-20`, `taille()` l.137) : plaque carrée `H/18 x 1.6` (71.1 px à H = 800), `ICONE = {carte 3, mode_carte 19, menu 4, discussion 15}` : numéros d'icônes **fidèles**, touches `DECL` fidèles (0x1000, 0x800, 0x400), visibilité `visibles()` (l.170) fidèle à `IconVisible`.
Écarts : plaques non carrées dans l'original (72 x 64, 63 x 56.8) ; plaque du portage = dégradé procédural « choisi à l'œil » (`plaque`, `cadre`, l.70-117, docs/viewer-notes-dq4-pc.md:220) alors que l'original est la plaque 9-tranches de la feuille `Button` (feuille 1, partie 7, coins de 16 unités, état appuyé = décalage uv de 0.1875). `Rendu.plaque` (`ui_menu.py:587`) dessine déjà la vraie plaque et peut être réutilisée.
Le bouton PadPos n'existe pas dans le portage (sans objet sur PC).

### 1.4 Supposé / non établi

- Le centre dessiné de la pastille coïncide avec le centre du quad (104) : le maillage le confirme, l'image du quad 128 x 64 n'a pas été comparée pixel à pixel à une capture Android.
- L'absence de fondu est établie pour le code C# de `TouchPad`. Une animation ou un shader extérieur à ce code n'est pas exclu (aucune trace dans la scène lue).
- La remarque « la croix du téléphone apparaît sous le doigt » (docs/viewer-notes-dq4-pc.md:305) n'est pas contredite : c'est la **boule** qui suit le doigt (bornée à 36.5 x sc). Rien n'établit un anneau flottant ; seule une capture Android (appui loin du centre) peut trancher.
- Sémantique exacte de `c_MoveRingLimit` (56 x sc) : comparée à la distance du doigt dans `MoveCheck` (0xD23D84, 0xD23F48) et fait sortir de l'état de déplacement ; valeur établie, effet précis supposé.

---

## 2. `MenuPortItemTable.ItemNumCTRL` (type 9, `Make_ItemList`)

Constructeur `0xD08128`, `Changer 0xD08060`.

### 2.1 Établi

- C'est un **compteur passif à deux chiffres**, pas un sélecteur : il pilote deux icônes de la feuille 12 (`Button`, `startNo = 6`, `widthNum = 16`, cases de 32 px, `sy = 192`).
- `Changer(v)` : si `v < 2` les deux chiffres reçoivent `Change(1)` (case vide en (224, 192)) ; sinon dizaines = `(v / 10) % 10` -> `Change(dizaines != 0 ? dizaines x 16 : 1)`, unités -> `Change(unités x 16)`. Donc **0 et 1 n'affichent rien**, 2..99 affichent le nombre, 100 et plus se replient modulo 100 (123 donne « 23 »).
- Numéro d'icône -> case : colonne `(6 + n) % 16`, ligne `(6 + n) // 16` (même règle que `uv_icone`, `ui_menu.py:114`) : le chiffre `d` est dans la colonne x = 192 à y = 192 + 32 d ; blanc = `Change(1)`.
- Utilisé par `Sub_ItemButton` (0xCEE1D4), appelé 4 fois par `Make_ItemList` : ligne `no` en `z = 382 - 67 x no` (depuis `RightBottom`), x = -146 ; bouton `CreateButton(170, 22)`, touche `PAD_A`.
  Structure d'une ligne (IBase de la `MenuParts` du bouton) : 0 bouton ; 1 icône d'objet (feuille 0, (18, 4), taille 0.8) param `(ligne, 0)` ; 2 marque d'équipement (feuille 6, (10, 6), taille 0.6) param `(ligne, 1)` ; 3 dizaines (feuille 12, indent 6, (0, 6), taille 0.6) ; 4 unités (feuille 12, (10, 6), taille 0.6) ; 5 texte du nom (x = -38) param `(ligne, 2)` ; param `(ligne, 3)` = `ItemNumCTRL(IBase 3, IBase 4)` = la **quantité**.
- Le moteur envoie la quantité par `setItemParam(ligne, 3, nombre)` (p. ex. `TownMenuItemSelectTargetItem::menuSetup`).
- `ui_layout.json` type 9 : `(id, 3)` = `custom ItemNumCTRL`, champs `0x28` / `0x30` non résolus car ce sont des delegates, pas des IBase (`tools/ui_il2cpp/layout.py:145` ne calcule `wrap` que pour le champ `0x28`).

### 2.2 Portage

`ui_menu.py:182` `param_int` : seule la branche `BattleBar` existe pour un `custom` ; **ItemNumCTRL est ignoré**, les cases de chiffres restent vides : **les quantités de la liste d'objets ne s'affichent jamais** (docs/technical-notes-dq4-port.md:87 : « non reproduit »). Verdict : **absent**.

### 2.3 Correction

Dans `Fenetre.param_int` : si `cu['cls']` finit par `ItemNumCTRL`, prendre `p = self.params[(i, 0)]['parts']` (la `MenuParts` de la ligne), IBase 3 = dizaines, IBase 4 = unités, puis appliquer la règle `Changer(v)` ci-dessus avec `uv_icone(info_feuille12, no, o)` sur le quad de chaque chiffre. Valeur d'icône par défaut des deux chiffres à l'ouverture : 1 (vide). Exemples : 57 -> (80, 112), 9 -> (1, 144), 10 -> (16, 0), 100 -> (1, 0).

---

## 3. `ICityMap` (type 25 : petite carte du monde, carte des villes, `Make_CityMap` 0xCF0684)

`ICityMap` ctor `0xD081D8`, `b__0 0xD082C4`, code 4 `b__4 0xD09504`, code 5 `b__5 0xD09624`, `BlinkMapSymbol.SetParameter 0xD0E0D0`, `Update 0xD0E688`, `MAP_DIFF.CheckSet 0xD08444`.

### 3.1 Établi

- **Cadre** : `CreateWindow0(430, 319.5)` construit en `LeftTop` (-2, 0, +2) -> monde (-227, 402), 454 x 343.5 avec les bordures de 12.
- **Plan** (`CreateFromTexture("Menu/map/" + nom, bFitWidth = true, haspect = 0.75)`) : quad 450 x 337.5, `Build(indent 0, écran 0, x = 2, y = 12, z = -2)`, `localScale = 0.99` -> **445.5 x 334.125**, x de -223 à 222.5, z de 398 à 63.875 (profondeur 12).
- **Marqueur du joueur** (`posf`) : `AddIcon(Vector3.zero, 31, bInBounds = true, 0.5)` = plume 24 x 24, coin bas-gauche = origine, enfant du plan ; code 1 : x local = `posx x 450/256` ; code 2 : z local = `-posy x 450/256` ; y local = 4. Monde : `(-223 + 0.99 x 1.7578 x x, 398 - 0.99 x 1.7578 x y)`.
- **Code 3** (lieux découverts, `BlinkMapSymbol`) : un carré de 4 x 4 par court, coin haut-gauche à `(lo x 1.7578, -hi x 1.7578)` sous une racine en (0, 14, 0) ; **sans échelle 0.99** ; couleur (1, 0, 0, 1), shader `Custom/SmallMapSymbol` ; `m_blinkRate = 0.5` ; alpha triangle 1 -> 0 -> 1 sur 4 s.
- **Code 4** (lieu spécial, un court) : `Create(5)`, `AddIcon(Vector3.zero, 3, true, 1.2)` = **croix rouge** (feuille 5 de `MenuTexture`, y = 288, cases de 16 px, icône n. 3), quad 21.6, profondeur 13, position `(lo x 1.7578, 13, -hi x 1.7578)` sous la racine (-227, 402).
- **Code 5** (voile) : `Texture2D` 256 x 192 ARGB32, `filterMode = Point`, `TextAsset "Menu/map/dsdq4wmap01m"` (RGBA) ; 16 x 16 blocs de 10 x 10 pixels dont le coin est (48, 16) ; bit levé = bloc copié ; quad 450 x 337.5 en profondeur 12.5, `localScale 0.99`, `Build(0, 2, 12.5, -2)`.
- **Ordre de profondeur** : cadre 0 < plan 12 < voile 12.5 < code 4 : 13 < lieux 14 < marqueur ~ 15.96.
- `MAP_DIFF.CheckSet` : si `flag & (1 << m_bits)`, la pièce `Menu/map/<nom>` (RVB, 3 octets par pixel) est copiée sur `m_width` pixels par ligne en `(m_x, m_y)`, pas de destination 1024 : le portage (`plan_monde`) est fidèle ; type 26 : offset uv u = x/1024 - 0.125, v = (y - 1024)/1024 - 0.09375 (cohérent).

### 3.2 Portage et verdicts

| Élément | Portage | Verdict |
|---|---|---|
| Cadre type 25/26/24 | nœud en (-227, 0, 402), vtx 454 x 343.5 (`ui_layout.json`) | fidèle |
| Rectangle du plan | `ui_menu.py:606-612` : x -225..225, z 400 -> 62.5 | approché : original x -223..222.5, z 398 -> 63.875 (écart <= 2.5 unités) |
| Marqueur | `window.py:1480` : `-225 + mx x 450/256`, `400 - my x 337.5/192` | approché : manque le décalage (2, -2) et l'échelle 0.99 (écart <= 2.5) ; ancrage bas-gauche déjà correct (docs/…:296) |
| Lieux (code 3) | `ui_menu.py:~622` carrés 4 x 4 centrés sur `-225 + x k`, `400 - y k` | **fidèle** (confirme docs/notes-technique:159), alpha |1 - (t mod 4)/2| exact |
| Voile (code 5) | blocs 10 x 10 depuis (48, 16), filtre Point | **fidèle** (à 0.99 et 2 unités près) |
| Code 4 (croix rouge) | « non affiché » (docs/notes-visionneuse:240) | **absent** (le moteur l'envoie ; l'icône est une croix rouge) |
| Profondeur | plan à 1.0 (`ui_menu.py:527`) | fidèle (ordre conservé) |
| Nom du plan | vient de `fenetre._plan_fenetre` (`f['cases'].get((0,0))`) | fonctionne ; mais `ui_menu.py:187` : `self.nom_carte = s` avec `s` **non défini** (NameError latente, la branche `param_int` n'a pas de `s`) : à supprimer ou corriger |

### 3.3 Corrections

1. Plan : `x0 = -223`, `z0 = 398`, taille 445.5 x 334.125 (échelle 0.99 appliquée au plan et au voile).
2. Marqueur : `x = -223 + 1.740234 x px`, `z = 398 - 1.740234 x py` (coin bas-gauche de la plume).
3. Lieux (code 3) : inchangés (pas d'échelle 0.99).
4. Code 4 : dessiner la croix rouge (feuille 5, case 3 de `MenuTexture` : x 48..64, y 288..304, quad 21.6) en `(-227 + lo x 1.7578, 402 - hi x 1.7578)`, ancrage bas-gauche (supposé comme la plume).
5. Supprimer la ligne `ui_menu.py:187` (variable `s` inexistante).

### 3.4 Supposé

- Ancrage du code 4 (bas-gauche) par analogie avec la plume (même `bInBounds = true`).
- Forme exacte du shader `Custom/SmallMapSymbol` (non lisible via UnityPy) ; couleur (1, 0, 0, 1) établie.

---

## 4. Bouton « Mode de la carte » : `Make_MapButton` (types 22 et 23) et bug du pipeline

### 4.1 Établi

- **`CreateMenuPortItem` (0xCE4294)** appelle le délégué avec `type - Array.IndexOf(makeFuncList, délégué)` : `0xCE43DC : sub w2, w21, w0` (w21 = type, w0 = premier indice du même délégué), puis `blr`. Donc type 22 -> `Make_MapButton(port, 0)`, type 23 -> `Make_MapButton(port, 1)` ; de même pour `Make_Status` (13..17), `Make_BattleIM` (35..37), `Make_ShopBuy` (58/59), `Make_ShopBuyInfo` (60/61), `Make_NetworkRoot` (75/76) (`/tmp/specs/type_to_make.txt`).
- **Type 22 (`Make_MapButton` 0xCF0414, arg 0)** : fenêtre 54 x 112 (cadre 78 x 136) ancrée `RightBottom` (2, 0, -2), avec **deux boutons** ; **type 23 (arg 1)** : fenêtre 54 x 47 (78 x 71), bouton Retour seul.
- **Retour** (`Sub_BackButton` 0xCE4C94) : `CreateButton(32, 23.5)` -> plaque 64 x 55.5 ; touche `0x400` si `bExternalToggle` sinon `0x20` (menu : `PAD_B`) ; icône 11 à 1.3 (62.4) ; centre (187.5, -366).
- **Mode** (type 22 seulement) : `CreateButton(32, 23.5, gamepad = 2 = PAD_U)`, `AddIcon(…, no = 2, false, 1.2)` = 57.6 ; centre (187.5, -300).
- **Icône pilotée par le moteur** : `SetTableForItemParam(0, 0, partsIdx, 1)` ; le moteur envoie : 2 en ville (`TownImageMap::checkData`+0x378 ; type 22 si plan et liste des boutiques sont disponibles, sinon type 23), **20** (`FieldImageMap::open`+0x410 : la première vue ouverte est la grande carte, état 2, type 26) et 19 / 20 selon la vue (`FieldImageMap::execute` : 19 en passant à l'état 1 = petite carte type 25, 20 en passant à l'état 2). Touche haut (PAD_U) : 1 <-> 2 (code de sortie 4) ; le code 5 pose le drapeau 0x20.
- `ui_layout.json` pour le type 22 contient la variante à un seul bouton (78 x 71) : **erreur d'export**. `tools/ui_il2cpp/layout.py:99` : `T.run(R.addr[nm[:-2]], [7, typ])` passe le **type** (22) et non `typ - premier indice` (0).

### 4.2 Portage

- `hud_mobile.py:18-20` : bouton `mode_carte` du HUD, colonne de gauche (0.4, 3), icône **fixe 19**, plaque procédurale, sans touche (`DECL 0`) ; visible seulement carte ouverte et `carte_deux_vues` (`visibles()` l.170, `window.py:1930`) ; `window.py:1937-1942` envoie `envoyer_menu(carte[25], 1, -1, 2)` (clé 2 = `PAD_U` : conforme). `_carte_ports` (`window.py:1336`) fusionne le type 23 dans le 22.
- Verdict : **approché** (fonction juste, apparence et position inventées) ; icône **fausse** hors petite carte du monde (20 sur la grande carte, 2 en ville). L'original n'est pas un bouton du HUD mais un bouton **dans la fenêtre** en bas à droite.

### 4.3 Corrections

1. Corriger `layout.py:99` : passer `typ - min(t pour R.tbl[t] == R.tbl[typ])`, régénérer `/tmp/uicache/ui_layout.json`. Le type 22 aura alors ses deux boutons (Retour (187.5, -366), Mode (187.5, -300), plaques 64 x 55.5, touches PAD_B/0x20 et PAD_U).
2. Icône du bouton Mode = valeur reçue du moteur (`param_int` du type 22, item 0) : 19 / 20 / 2, jamais 19 en dur.
3. Si le bouton de la fenêtre est cliquable, supprimer `mode_carte` du HUD ; sinon le garder avec icône dynamique et, de préférence, la vraie plaque (`Rendu.plaque`).
4. À mesurer : l'effet du correctif de `layout.py:99` sur les groupes 13..17, 35..37, 58/59, 60/61, 75/76 (même mécanisme, hors périmètre de cet audit).

### 4.4 Supposé

- Que `Make_Status` / `Make_BattleIM` / `Make_ShopBuy` / `Make_ShopBuyInfo` / `Make_NetworkRoot` testent leur 2e argument de la même manière : seul `Make_MapButton` a été lu ligne à ligne.

---

## 5. `PortalButton` (type 74)

- `Make_PortalButton` (0xCF71BC) crée un `MenuPortItem` vide ; la classe `PortalButton : MenuParts` (`Setup` 0xD0F408) fabrique un bouton à texture `Title/PotalButton` (128 x 128 x `s_scale 0.75` = 96 x 96), touche `0x2000000` / `0x200`, `Build(indent 4, écran 2 = RightTop, x = -70, y = 0, z = -60)`.
- Utilisé uniquement par `MaterielMenu_LOAD` (écran titre / chargement), `MenuPortSendPortal` (0x156490) envoie un message. **Ne fait pas partie du HUD de jeu.** Rien à reproduire dans `hud_mobile.py` (verdict : sans objet).

---

## 6. Autres valeurs « estimées / choisies » du portage

| Où | Valeur du portage | Ce que dit l'original | Verdict |
|---|---|---|---|
| `hud_mobile.py:26-31`, docs/notes-visionneuse:300, 305 | facteurs 1.25/1/0.75, 165, 85/256, 0.5, 0.15, fondu 0.4 | voir section 1.2 | à corriger |
| `hud_mobile.py:70-117` plaques (docs:220) | dégradé procédural, « ressemblance non mesurée » | plaque `Button` (feuille 1, partie 7), 9-tranches, coins de 16 unités, appuyé = uv + 0.1875 | approché : utiliser `Rendu.plaque` |
| `hud_mobile.py:18` positions par défaut (0.4, 1/3/12/14) | colonne gauche, pas de `g_pad_pos` | pos 1 : croix au centre, boutons à droite | choix de l'utilisateur (retour #36) ; option `g_pad_pos` non reliée |
| docs/notes-visionneuse:212 | pas des chiffres de dégâts 12.8 | `HoppingNumber`, `m_dps` 16 x 0.8 | déjà corrigé ; fidèle |
| docs/notes-visionneuse:229, 233 | oscillation du curseur doré « inventée » | pas de curseur dans les menus Unity : la sélection est l'état « appuyé » | reste inventé ; l'original n'a pas de curseur oscillant |
| docs/notes-technique:135 `NormalControl::execute` | « non vérifié » (bit 4 = `openMap`, sinon bit 5 = `openShopList`) | non relu dans cet audit (le moteur envoie bien les icônes 2 / 19 / 20 aux boutons) | inchangé |
| docs/notes-technique:87 | ItemNumCTRL, ICityMap « non reproduits » | ItemNumCTRL entièrement décodé (section 2) ; ICityMap : tout reproduit sauf le code 4 | à mettre à jour |
| docs/notes-visionneuse:296 | ancrage de la plume « pas vérifié » | confirmé : `AddIcon(Vector3.zero, 31, true, 0.5)`, origine = coin bas-gauche | à mettre à jour (établi) |

---

## 7. À corriger par ordre de priorité

### A. Établi (preuve), numérique

1. **Bug du pipeline `tools/ui_il2cpp/layout.py:99`** : passer `type - premier indice du même délégué` (preuve : `sub w2, w21, w0` en 0xCE43DC). Régénérer `ui_layout.json`. Effets immédiats : type 22 (bouton Mode dans la fenêtre), puis groupes 13..17, 35..37, 58/59, 60/61, 75/76 à contrôler.
2. **ItemNumCTRL (type 9) absent** : implémenter `Changer(v)` dans `ui_menu.Fenetre.param_int` (quantités des listes d'objets : actuellement jamais affichées). Règle : v < 2 -> vides ; sinon dizaines = `(v / 10) % 10` (icône 16 x d, ou 1), unités = 16 x (v % 10).
3. **Géométrie de la croix** : `ECHELLE_CROIX = (1.225, 1.0, 0.775)` ; `DIAM_CROIX = 161.28` ; `RAYON_PASTILLE = 104/256 = 0.40625` ; `ZONE_MORTE = 0.124` ; `COURSE_BOULE = 0.4526` ; zone de prise 1.178 x le rayon.
4. **Boule orange et halo** : pas en cours de déplacement, seulement en clignotement tutoriel ; seule la pastille du secteur tenu s'allume.
5. **Fondu de la croix à 40 %** : **inventé** (constantes mortes `MOVE_WAIT_TIME` / `MOVE_LIMIT_ALPHA`), à retirer ou à garder comme option PC assumée (non fidèle).
6. **Icône du bouton Mode** : 19 / 20 / 2 selon le moteur (petite carte du monde, grande carte, ville) ; position d'origine dans la fenêtre (187.5, -300), plaque 64 x 55.5, touche `PAD_U`.
7. **Plan et marqueur de la carte** : rectangle x -223..222.5, z 398..63.875 ; marqueur `-223 + 1.740234 px`, `398 - 1.740234 py` (écart <= 2.5 unités : correction mineure).
8. **Code 4 d'`ICityMap`** : afficher la croix rouge (feuille 5, case 3, 21.6) en `(-227 + lo x 1.7578, 402 - hi x 1.7578)`.
9. **`ui_menu.py:187`** : `s` non défini (NameError latente) à supprimer.
10. **Plaques des boutons du HUD** : vraie plaque 9-tranches (`Rendu.plaque`) et formats 72 x 64 (Carte, Commandes), 63 x 56.8 (Discussion) au lieu du carré de 71.1.

### B. Supposé (à confirmer par capture Android ou lecture supplémentaire)

1. Pas d'anneau flottant : la boule suit le doigt, l'anneau reste fixe (aucun code ne le déplace) ; à vérifier par une capture d'appui hors du centre.
2. Absence de fondu : vrai pour le code C# de `TouchPad`, pas prouvé pour une animation extérieure.
3. Ancrage bas-gauche de la croix rouge (code 4) par analogie avec la plume.
4. Effet de la correction 1 sur les autres groupes de types (seul `Make_MapButton` a été lu en détail).
5. Défaut `g_pad_pos = 1` (croix centrée, boutons à droite) : l'option « Position de la croix » n'est pas branchée ; le retour #36 demande les boutons à gauche, donc à traiter comme préférence, pas comme erreur.

---

## 8. Reproduction

Tout se lance sans rien modifier dans le dépôt :

- `bash /tmp/specs/scripts/audit_reproduire.sh` : régénère dans `/tmp/r4_repro/` les listings annotés de toutes les méthodes citées (désassemblage ARM64 avec noms de méthodes, constantes flottantes, chaînes, champs), les maillages de la croix (`audit_pad_meshes.py`), le balayage des appels moteur vers l'interface (`audit_scan_itemparam.py`) et `audit_values.py`.
- `python3 -I /tmp/specs/scripts/audit_valeurs.py` : recalcule tous les nombres dérivés de ce document (diamètres, rapports au rayon, positions de la croix, boutons, plan, marqueur, chiffres).
- `DQ_IL2=/home/claude/il2 python3 -I /tmp/specs/scripts/audit_dis.py <RVA début> <RVA fin>` : désassemblage annoté d'une plage de `libil2cpp.so`.
- `python3 /tmp/specs/scripts/audit_eng.py dis|sym|xref ...` : même chose pour le moteur `libdq4core.so` ; `audit_scan_itemparam.py [sous-chaîne]` : appels du moteur à `setItemParam (0x225070)` et `setItemCode (0x225060)` avec leurs immédiats et leur fonction appelante (`audit_scan_itemparam.py MapButton`, `ImageMap`).
- Images : `/tmp/specs/img/icons_sheet3.png`, `icons_sheet3b.png` (feuille 3, icônes 0..31), `icons_sheet5.png` (feuille 5, croix rouge du code 4), `button_sheet12.png` (chiffres de la feuille 12).
