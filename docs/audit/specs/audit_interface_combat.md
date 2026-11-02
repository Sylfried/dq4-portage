# Audit de fidélité : interface de combat et fenêtres du moteur (DQ4 Android -> PC)

Auteur : sous-agent d'audit. Dépôt `/home/claude/dq4-portage` lu en lecture seule (rien modifié). Tout ce qui est produit est dans `/tmp/specs/` et `/tmp/r3_*`.
Légende : **établi** = lu dans le code (RVA cités) ou mesuré par exécution ; **supposé** = déduit, non vérifié ; statut visionneuse : **fidèle / approximé / absent**.

Conventions : RVA IL2CPP (`libil2cpp.so`, offset fichier = RVA - 0x4000) ; adresses du moteur = adresses de `libdq4core.so`. Coordonnées d'interface : colonne portrait 450 x 800, `z` vers le haut, centre = 0 (bord haut z=+400, bord bas z=-400), `y` = profondeur (ordre de tri). Les `pos` de `ui_layout.json` sont des positions monde (le visualiseur dessine `cy + (pos_z + vtx_z) * s`, ui_menu.py:565). UV d'icône : `uv_icone(info, no)` (ui_menu.py:114), cellule `n = no + startNo`, `col = n % widthNum`, `lig = n // widthNum`.

## 0. Synthèse

| # | Élément | Visionneuse aujourd'hui | Visibilité en jeu | Section |
|---|---|---|---|---|
| 1 | Type 66 « Église » : 4 ou 5 boutons créés par code (`b__0`), non exportés | **absent** (cadre vide + « Quitter ») | blocage fonctionnel dans chaque église | 6 |
| 2 | Secousse de la plaque (`ShakeFrame`, code 8) + délai du « rouge » de la barre PV (`RedApply`) | **absent** / **approximé** | à chaque coup reçu en combat | 3.2 |
| 3 | Curseur du bandeau (`BattleUpCursor`) : clignote clair/foncé toutes les 0,7 s | **approximé** (fixe, clair) | combat, saisie des ordres | 3.3 |
| 4 | `StatusIconChanger` (types 4, 5, 20, 21, 46, 60, 61, 67) | **absent** | dès qu'un membre est mort/empoisonné/ensorcelé | 1 |
| 5 | `MonsterMarkList` (losanges de couleur sous les monstres) | **absent** | choix de cible avec plusieurs groupes | 2 |
| 6 | Type 54 : cadre du titre (`IFrame.Change(0xDB + code)`) et nombre de boutons | **absent** (pas de cadre) | menu de démarrage / chargement uniquement | 4 |
| 7 | Types 73 / 77 / 80 (erreurs d'export) | sans objet | écrans Unity spécifiques (titre, réseau, licences), jamais ouverts par le flux du portage | 5 |
| 8 | `BattleBar` (barre PV/PM) | **fidèle** | | 3.1 |
| 9 | Texte d'action « Attaquer / ▼ / cible » | **fidèle** : l'original n'a pas de cadre propre | | 3.4 |
| 10 | Niveau « ? » du 2e personnage | **fidèle** : c'est le moteur qui l'envoie (membre « invité ») | | 3.5 |

Les points 9 et 10 des « lacunes connues » ne sont pas des défauts du visualiseur (preuves en 3.4 et 3.5). Le point « type 66 (boutiques) » est en réalité `Make_ChurchRoot` (les boutiques sont 57 à 63 et leur export est complet : voir `scan_parts_manquantes.py`).

Rendu hors écran de la visionneuse (mise en page régénérée) : `/tmp/specs/img/rendu_combat_s1.png` (bandeau, texte d'action, plaque de monstre, menu d'action), `/tmp/specs/img/comp_54_66.png` (type 54 aujourd'hui / avec correctif / type 66 aujourd'hui).

---

## 1. `MenuPortItemTable.StatusIconChanger`

### Code d'origine (établi)
- Classe `MenuPortItemTable.StatusIconChanger : MenuParts.IBase` ; ctor RVA `0xD07E74` ; lambda `b(int v)` RVA `0xD07F6C`.
- Champs : `[0x10]` IIcon n°1, `[0x18]` IIcon n°2 (les deux `ib` d'icônes de la feuille 13 de la plaque), `[0x20]` `Material` de la feuille 13.
- `b(v)` : `icône1.Change(v & 3)` ; `icône2.Change(((v >> 2) & 1) * 3)` (0 ou 3) ; `Material.color = MenuParts.s_colorList[v >> 16]` (liste statique +0x70 = `header['colors']` : blanc, jaune, rouge, gris, noir, cyan, vert).
- Une seule `Material` (feuille 13) est teintée : elle ne sert qu'aux deux icônes d'état, pas au cadre ni au visage.

### Données reçues du moteur (établi)
- Entier `INT(id, no)` (cmd 10), `no = 7` pour les types 4, 5, 46, 60, 61, 67 ; `no = 5` pour les types 20 et 21 ; `id` = rang du membre.
- Valeur = `icône | (couleur << 16)`, composée par `SetCharaButtonInfo` (0x162b94) avec `getActorConditionIcon` (0x162b20) et `getActorConditionColor` (0x162ad4), sur `HaveStatusInfo` :
  - icône : `isDeath` -> 1 ; sinon `isPoison` -> 2 ; puis `isSpell` -> `| 4` (sauf si `PlayerStatus+0x58 == 0x19`) ;
  - couleur : `isDeath` -> 2 (rouge) ; sinon `isNearDeath` -> 1 (jaune) ; sinon 0 (blanc).
- La même couleur est envoyée en `INT(id, 6)` (couleur du texte du nom) : déjà appliquée par le visualiseur (ui_menu.py:191, `textcolor`).

### Valeurs exactes (établi)
- Feuille 13 : `MenuTexture` (sheet 0), `sy = 304`, cellules 16 px, 64 par ligne, `startNo 0`. Cellule 0 = vide, 1 = croix (mort), 2 = tête de mort (poison), 3 = oeil (`isSpell`, interprétation « sort scellé » **supposée**, le nom du symbole est `isSpell`). Vérifié visuellement : `/tmp/r3_part13_zoom.png`.
- Le nœud de chaque plaque a un maillage de 12 quads (types 4, 5, 21, 46, 60, 61, 67) ou 3 quads (type 20). Le quad 9 est le visage (feuille 1), le quad 10 (sommets 40-43) est l'icône n°1, le quad 11 (sommets 44-47) l'icône n°2. Chaque icône mesure 19,8 x 19,8.

| Types | x de l'icône (relatif au nœud) | z icône 1 | z icône 2 |
|---|---|---|---|
| 4, 5 | 45 à 64,8 | -19,8 à 0 | -37,8 à -18 |
| 20 | 44 à 63,8 | idem | idem |
| 21 | 43 à 62,8 | idem | idem |
| 46, 60, 61, 67 | -34 à -14,2 | 30,7 à 50,5 | 12,7 à 32,5 |

- Le rang `id` correspond à la `id`-ième partie qui porte deux `IIcon` de la feuille 13 (type 4 : parties 1 à 4 ; type 60 : parties 4 et 5). L'exporteur n'a pas gardé ce lien (`custom.wrap` vide) : à reconstruire par ce critère (script `inv_statusicon.py`).
- Ne pas coder d'identifiants de nœud en dur : ils changent d'une génération du JSON à l'autre (ex. 1508 contre 1500).

### Visionneuse
- **Absent.** ui_menu.py:185-190 : toute entrée `custom` est ignorée sauf `ICityMap` et `BattleBar`, et `return` immédiat. Les icônes restent à l'UV de départ (cellule vide), aucune teinte.
- Bogue annexe, ui_menu.py:187 : `self.nom_carte = s` dans `param_int` utilise `s` qui n'existe pas (NameError si le moteur envoie un entier à un `ICityMap`).

---

## 2. `MenuPortItemTable.MonsterMarkList` (marques de groupe sous les monstres)

### Code d'origine (établi)
- Classe simple (pas de `MonoBehaviour`, aucun `Update`) : `m_pos` (+0x10, Vector3), `m_used` (+0x1C, masque), `m_list` (+0x20, `MenuParts[]`). Méthodes : ctor `0xD073C8`, `Reset` `0xD075C8`, `SetMark(int id, float x)` `0xD07640`.
- ctor : 12 `MenuParts.Create(6)` + `AddIcon` (feuille 6), `Build(indent 4, scr 4, 0,0,0)`, désactivés ; `m_pos = eIndent.CalcScreenPosition(1, 0, 0, -464)` puis `z -= NotchFix.NotchHeight()`.
  **Valeur mesurée** (`t_calc.py`, tracer) : `CalcScreenPosition(1,0,0,-464) = (0, 0, -64)` (indent 0-2 : z + 400 ; 3-5 : z ; 6-8 : z - 400 ; x = -225 / 0 / +225) ; `NotchHeight() = 0` sans encoche. Donc **`m_pos = (0, 0, -64)`** : les marques sont à 464 px du haut de l'écran 800.
- `SetMark(id, x)` : premier bit libre de `m_used`, `SetActive(true)`, `IIcon.Change(id + 5)`, `Transform.position = (x, 0, -64)` (position monde). Pas d'animation.
- `Reset` : désactive les 12 marques, `m_used = 0`. Appelé par le code `id 4` du type 31 (`<Make_MonsterName>b__0` `0xD0B3A0`).
- `MonsterNamePlate.ReceiveParameters(code)` (`0xD077B0`) : pour code >= 1, lit 6 paramètres (0-3 : rectangle x 1,85 ; 4-5 : masque 32 bits des monstres du groupe). **Si code == 2**, pour chaque monstre du masque : `NativeManager.GetMeshChara(i).position` -> `Camera.WorldToScreenPoint` -> `ScreenToWorldPoint` (caméra d'interface) -> `x` -> `SetMark(id_de_la_plaque, x)`. L'identifiant de marque est l'index de la plaque (champ +0x10 de la plaque : 0 à 3). Une marque par monstre, pas une par groupe.

### Données reçues du moteur (établi)
- `BattleMenuSub_HISTORY::SetupMonsterNamePlate(bool)` (0x15b8bc) : envoie `CODE(id 4) = 0` (Reset), puis pour chaque groupe `CODE(id i) = 1 + bool` avec ses paramètres (rect + masque), puis `CODE(id 5) = nombre de groupes`.
- `code == 2` = `SetupMonsterNamePlate(true)` (choix de cible). Observé dans le journal du combat du slot 4 : `CODE(15, id 0) = 2`, `id 1 = 2`, `id 5 = 2` ; au début de combat (slot 1) seulement code 1.

### Valeurs exactes (établi)
- Icône : feuille 6 = `Button` (sheet 1), `sx 192, sy 64`, cellules 32 px, 16 par ligne, `startNo 6`. Marque `id` = cellule `no = id + 5` -> `n = id + 11` : pixels x = 352 + 32 id, y = 64 à 96 sur `ui_Button.png`. Couleurs mesurées : id 0 rouge, 1 jaune, 2 violet, 3 orange (losanges bordés de blanc) : `/tmp/specs/img/marques_part6.png`.
- Quad : 24 x 24 (±12), échelle 1.

### Visionneuse
- **Absent.** Les 12 nœuds de marque existent dans le JSON du type 31 (feuille 1, partie 6, `act` faux), jamais activés. `Fenetre.plaque` (ui_menu.py:308) range `code` dans `pl[i]` sans jamais l'utiliser ; `Fenetre.disposer` (ui_menu.py:324) reçoit `proj` mais n'a que l'étendue (min, max) ; `_ui_x_monstres` (fenetre.py:959) calcule pourtant l'abscisse de chaque monstre avant de ne garder que min et max.
- Le code `id 4` (Reset) est routé vers `Fenetre.code` (moteur.py:285), sans effet.

---

## 3. Bandeau des personnages (type 29, `Make_BattleUpStatus` `0xCE56B4`, `Sub_BattleUpStatus` `0xCE4FF0`)

Structure (établi, export) : racine (0, 0, 400) ; par membre une plaque `frame` (maillage 196 : x 6 à 118, z -145 à -25 relatifs, soit z 255 à 375 monde), 4 textes (nom z 385,5 centré ; étiquettes ; valeurs ; **texte d'action** à z 275, taille 8,84, 3 lignes), 2 barres (HP, MP) à z 288, icône de visage (feuille 2, à x +57), et le curseur (feuille 10) à z 385. Pas des plaques : 111 en x (-225 + 111 k).
Le texte du bandeau est écrit par `BattleMenuSub_HISTORY::UpdateStatus` (0x15be80).

### 3.1 `BattleBar` : fidèle (établi)
- ctor `0xD0729C`, `b__3_0` `0xD07394` (valeur normale : x = zéro + largeur x v x 0,01 ; valeur négative = quad rouge à l'indice -4), `RedApply` `0xD07268` (`Change(~valeur)` sur la barre enveloppée). Seule la barre PV (param no 5) est une `BattleBar` ; la barre PM (no 6) est une barre ordinaire.
- Visionneuse : ui_menu.py:167-174 (`_barre`), 188-189 (`Change(int)`), 215-218 (`Change(string)` = RedApply). Déjà fidèle pour ce que le moteur envoie.
- Nuance : le moteur n'envoie le texte vide (no 5) qu'au rafraîchissement complet (`UpdateStatus(bool)`/`(short,short*)` initial) ; lors d'un coup il n'envoie que l'entier (journal slot 4 : image 321 `INT(0,5)=96` sans chaîne, chaîne vide seulement à l'image 346). Le « rouge » doit alors attendre la fin de la secousse (3.2).

### 3.2 `ShakeFrame` : secousse de plaque sur dégâts (absent) (établi)
- Classes `ShakeFrame : MenuParts` (`Update` `0xD0CACC`, ctor `0xD0CBD4`), `m_shake` (+0x60), `m_shakeEndCallback` (+0x68, `DAMEGE_APPLY_FUNC`). La plaque du bandeau est créée avec `CreateBuildFrameParts<ShakeFrame>` ; le délégué de fin cible le `BattleBar` (`DAMEGE_APPLY_FUNC` construit en `0xCE5550` avec l'objet `BattleBar` de `0xCE5504` ; la méthode est `RedApply`, **forte présomption** : le délégué est sans argument, `RedApply` est la seule méthode de `BattleBar` sans argument).
- Code `Sub_BattleUpStatus.b__0(short code)` `0xD0AFD8` : `code == 8` -> `frame.m_shake = 8` ; `code < 0` -> `SetActive(false)` ; sinon `SetActive(true)` + `MenuParts.SetTextColor(frame, code)` (codes 0 à 5 = couleur des textes 1 à 4, masque 30 : c'est ce que le visualiseur applique déjà via `fx.tc`).
- `ShakeFrame.Update` chaque image Unity : `m_shake -= 1` ; si `>= 0` : `Transform.Translate(dx, 0, dz)` avec `(dx, dz) = MenuMessage.s_shakeTable[m_shake]` (espace local) ; quand `m_shake` atteint 0 : appel du délégué (RedApply).
- Table mesurée (`t_shake.py`, `.cctor` de `MenuMessage` sous tracer), indices 0 à 7 : `(-6,6) (6,-6) (6,-6) (-6,6) (6,6) (-6,-6) (-6,-6) (6,6)`. Ordre d'application : indices 7, 6, 5, ..., 0 -> sommes cumulées (6,6) (0,0) (-6,-6) (0,0) (-6,6) (0,0) (6,-6) (0,0) : la plaque entière (avec ses textes, barres, visage) saute de ±6 unités en diagonale sur 8 images et revient exactement à sa place.
- Émetteur : `BattleMenuSub_HISTORY::ShakeStatus(short idPersonnage)` (0x15c5ec) -> `CODE(id membre) = 8`. Observé : `CODE(12, id 0) = 8` aux images 403 (slot 1), 320 et 450 (slot 4), 1 image avant la mise à jour des PV.
- Durée : 8 images Unity (supposé 30 Hz comme le moteur : 0,27 s ; la cadence d'affichage de l'original n'a pas été établie).
- Visionneuse : **absent** (`Fenetre.code`, ui_menu.py:246 : `fx.get('8')` n'existe pas, car l'exporteur n'évalue que les codes -1 à 5 : `layout.py` `CODES`). Conséquence : pas de secousse, et le « rouge » de la barre PV ne rattrape les PV qu'au prochain rafraîchissement complet (~25 images plus tard dans le journal) au lieu de 8 images après le coup : **approximé**.

### 3.3 `BattleUpCursor` : curseur clignotant (approximé) (établi)
- `BattleUpCursor : MenuParts` : `c_waitTime = 0,7`, `m_flip` (+0x60), `m_wait` (+0x64). `ForceUpdate` `0xD0C938` : `m_flip = false`, `icône.Change(2)`, `m_wait = 0` ; `Update` `0xD0C9B8` : `m_wait += Time.deltaTime` ; à >= 0,7 s : `m_flip` bascule, `icône.Change(m_flip ? 3 : 2)`, `m_wait = 0`.
- Feuille 10 (`sx 96, sy 288`, cellules 48 px, 21 par ligne, `startNo 2`) : `Change(2)` = flèche dorée claire (x 192), `Change(3)` = flèche dorée sombre (x 240) : `/tmp/specs/img/curseur_part10.png`. Le quad mesure 32 x 32 (±16).
- Position : code `id 5` -> `<Make_BattleUpStatus>b__0` `0xD0B06C` : `pos = (-200 + 111 k, 0, 385)` pour le membre k = 0..5, `-1` = caché (déjà exporté dans `fx` ; fidèle). `ForceUpdate` est appelé au changement de membre (supposé : le code lit `0xD0B06C` mais l'appel à `ForceUpdate` n'a pas été confirmé).
- Visionneuse : position fidèle (fx), **clignotement absent** (UV de départ = cellule claire, jamais changée).

### 3.4 Texte d'action « Attaquer / ▼ / cible » : fidèle (établi)
- Le moteur envoie une chaîne de 3 lignes dans `STR(id, 4)` : `"Attaquer\n▼\nTerminataure"` (journal slot 1, image 377).
- Nœud texte : ancre 1 (haut-centre), alignement centre, `characterSize 8,84`, `lineSpacing 0,8734`, `pos z = 275`. Le jeu ajoute `dy = 20` (header `lang.dy`, déjà appliqué par ui_menu.py:649) : le haut du texte est à z = 255 = **le bord bas exact du cadre de la plaque (z 255)**. Le texte pend donc juste sous la plaque.
- Il n'existe aucun second cadre : `Sub_BattleUpStatus` ne crée qu'un `CreateBuildFrameParts`, le nœud du texte n'a ni maillage ni `IFrame`, et la mise en page exportée (30 nœuds) n'a aucun autre cadre dans le bandeau.
- Visionneuse : fidèle (voir `img/rendu_combat_s1.png`). Le « manque » du cahier des lacunes est le comportement d'origine. **Supposé** : l'original ne dessine pas de contour ou d'ombre sur ce texte (aucun ne figure dans la mise en page).

### 3.5 Niveau « ? » du 2e personnage : fidèle (établi par exécution)
- Règle du moteur dans `BattleMenuSub_HISTORY::UpdateStatus(short, short*)` (0x15be80, ligne de valeurs, 0x15c13c-0x15c178) : si `PlayerStatus+0x68 != 0` la ligne 3 vaut `[espace, espace, '?']` (`UTF16_QUESTION`) ; sinon `PlayerStatus+0x66` formaté sur 3 colonnes.
- Mesure (`t7.py 1`, slot 1) : membre 0 (Ragnar) `+0x66 = 5`, `+0x68 = 0` ; membre 1 (Doc, identifiant 12) `+0x66 = 255`, `+0x68 = 1` -> « ? ». `+0x68` est `HaveStatusInfo+0x58`, l'indicateur que `HaveStatusInfo::setup(int, bool)` (0x1b7180) teste pour choisir les caractéristiques de la table `excel` plutôt que celles du niveau : membre « invité » dont le niveau n'est volontairement pas affiché. Cette interprétation d'« invité » est **supposée** ; la règle d'affichage est établie.
- Visionneuse : fidèle, le texte du moteur est affiché tel quel (`img/rendu_combat_s1.png` : « Nv. ? » pour Doc).

---

## 4. Type 54 `Make_StartMenuSelect` (`0xCF5D0C`) : cadre du titre

### Code d'origine (établi)
- Fenêtre : racine (cadre `IFrame` + texte du titre, centré, `characterSize 10,5`), 3 boutons à 2 textes (z -185 / -242,5 / -300), 1 bouton retour (feuille 10 icône, manette 32).
- **Le cadre n'a pas de maillage à l'export** : il est choisi à l'exécution par le code `id 3` (`<Make_StartMenuSelect>b__0` `0xD0A604`), que l'exporteur ne sait pas évaluer (`fx` = erreur « List index » pour -1 à 5, car la lambda lit des listes de composants).
- `b__0(code)` :
  - `IFrame.Change(0xDB + code)` sur la partie 0 : cadres `frameData` 219 (code 0 : 459 x 316), 220 (code 1 : 459 x 262), 221 (code 2 : 459 x 260) ;
  - code 2 : bouton 0 mis à `localPosition.z = 135,75` (monde -266,25 avec la racine à -402) et boutons 1 et 2 désactivés ; codes 0 et 1 : bouton 0 à `z = 217,0` (monde -185 : déjà la valeur exportée), boutons 1 et 2 actifs ;
  - le bouton retour est repositionné (x = 148 ou 117,5 ; z = 226,5 / 283,0, éventuellement + 263,5 selon un booléen statique) : **non résolu** (sens du booléen non établi).
- Émetteur : `gMI_StartMenuSelect_SetItem(cat, vue, n)` (0x193a70) : n <= 2 et `cat != 0` -> code 0, titre = message `cat` ; n <= 2 et `cat == 0` -> code 1, titre vide ; n > 2 -> code 2 (bouton unique de confirmation, **supposé**). Appelé depuis `MaterialMenu_Network` et `MaterielMenu_LOAD`.

### Visionneuse
- **Absent** : pas de cadre, le titre flotte (`img/comp_54_66.png`, colonne de gauche). En appliquant `IFrame.Change(219 + code)` on obtient la fenêtre complète (colonne du milieu : onglet de titre + corps ; boutons correctement placés dans le cadre). La reconstruction montre que les valeurs sont cohérentes (frame 219 = 316 de haut ; premier bouton à -185 dans un cadre dont le haut est à -86).
- Visibilité faible : ce type n'est atteint que par le flux titre / chargement (`pause.py` le nomme « Menu de démarrage : choix »).

---

## 5. Types 73, 77, 80 : erreurs d'export (sans objet pour le portage)

| Type | Constructeur | Cause de l'échec | Où le moteur l'utilise |
|---|---|---|---|
| 73 `Make_TitleTouch` (`0xCE4ED8`) | `TapToStart.Create` (`0xD0C158`) : composant Unity (logo clignotant, copyright en fondu : `c_firstWait 720`, `c_copyrightFirstWait 690` images) | `UcError` dans l'émulation (code Unity hors table) | `TownOpeningManager::setup/draw/cleanup` (écran d'ouverture) |
| 77 `Make_NetworkPLST` (`0xCF6280`) | fenêtre réseau avec `GetComponent` sur des `TextMesh` | `throw` (référence nulle) à `0xC103AC` | `MaterialMenu_Network` |
| 80 `Make_License` (`0xCF7228`) | `LicenseNobu.Create` (liste défilante), `Resources.Load` d'un `TextAsset` de licences | lecture mémoire non mappée | `MaterielMenu_LOAD` (menu de chargement) |

Établi : ce ne sont pas des fenêtres à table de paramètres mais des écrans Unity construits à partir de ressources (préfabriqués, texte de licence) ; le portage n'ouvre pas ces écrans (il charge les sauvegardes directement). Aucune correction à prévoir ; si le titre est un jour voulu, il faudra l'écrire à la main (images dans `/tmp/specs/img/title_*.png`, `tex_taptostart*.png`).

---

## 6. Type 66 = `Make_ChurchRoot` (« Église ») : parties manquantes

### Constat (établi)
- Export : 4 nœuds, 2 parties (cadre + titre ; bouton retour `Sub_ShopAbort`), mais **31 paramètres** qui citent les parties 2 à 30. `scan_parts_manquantes.py` : c'est le seul type dans ce cas (les boutiques 57-63 sont complètes).
- Cause : le code `id 0` (`<Make_ChurchRoot>b__0(short code)` `0xD0A360`) crée les boutons par `Sub_ShopButton(item, parent, no, 8,5, x, z, largeur)` (`0xCF28F0`) à l'exécution ; l'exporteur enregistre les paramètres de chaque appel (7 codes x 4 ou 5 boutons = 29 parties) mais pas les nœuds créés.
- Moteur : `MaterielMenu_CHURCH_ROOT::menuSetup` (0x1917d0..) n'envoie que `CODE(id 0) = 0` (5 boutons) ou `1` (4 boutons) puis les textes `STR(i, 0)` des boutons.

### Valeurs exactes (établi, lecture de `b__0`)
`Sub_ShopButton` : `CreateButton(largeur, 24, buttonId = no, manette = 0x10)` ; `Build(indent 4, scr 7, x, y = 4, z)` ; un `TextMesh` centré (taille de police 8,5 x 1,105 = 9,3925) à (0, 4, 0) du bouton ; texte au `AddParts`/`SetTableForItemParam(no, 0)`.

| Code | no | x | z (Build) | largeur |
|---|---|---|---|---|
| 0 (5 boutons) | 0 | -111,5 | 170,75 | 177,1 |
| | 1 | +111,5 | 170,75 | 177,1 |
| | 2 | -145,0 | 106,25 | 110,0 |
| | 3 | 0,0 | 106,25 | 110,0 |
| | 4 | +145,0 | 106,25 | 110,0 |
| != 0 (4 boutons) | 0 | 0,0 | 170,75 | 177,1 |
| | 1 | -145,0 | 106,25 | 110,0 |
| | 2 | 0,0 | 106,25 | 110,0 |
| | 3 | +145,0 | 106,25 | 110,0 |

Position monde d'un nœud = (x, 4, z - 400) (même règle que les boutons de `ShopRoot`, type 57) ; texte enfant à (x, 8, z - 400 + 20). Le maillage d'un bouton est un 9 découpes à coins de 16 px : demi-largeur = largeur / 2 + 16 et hauteur 24 + 32 (comparé à `ShopRoot` : mesh x ±71 pour une largeur de 110, y ±28 : **supposé** pour la largeur 177,1, la formule n'a pas été confrontée à un bouton de cette largeur).

### Visionneuse
- **Absent** (`img/comp_54_66.png`, colonne de droite : cadre vide + « Quitter »). `Gestionnaire.ouvrir` (ui_menu.py:707) accepte le type puisque `err` est nul et `nodes` non vide.

---

## 7. À corriger, par ordre de priorité, étapes concrètes

Précautions communes : ne pas coder d'identifiants de nœud (ils changent à chaque régénération) ; le cache de l'utilisateur doit être régénéré avec le générateur actuel (`header.gen = 2`, absent des anciens `ui_layout.json`) ; retrouver les nœuds par structure (parties, `ib`, `mats[].part`). Rendu de contrôle : `xvfb-run -a python3 /tmp/specs/rend_combat.py 1 sortie.png` et `rend_type.py`.

### P1. Église (type 66) : fenêtre inutilisable aujourd'hui
1. Dans `outils/ui_il2cpp/layout.py` (boucle `CODES = (-1, 0, 1, 2, 3, 4, 5)`), pour chaque code `func`, comparer la liste des nœuds / parties du `MenuPortItem` avant et après l'appel et exporter les nœuds créés dans `fx[code]['new']` (nœud, maillage, matériaux, `parts`/`ib`). Les paramètres existent déjà.
2. Dans `Fenetre.code` (ui_menu.py:240) : pour une entrée `fx[code]['new']`, rendre visibles les nœuds du code reçu et masquer ceux des autres codes. Le moteur n'envoie que les codes 0 et 1 (table 6).
3. Variante sans toucher à l'exporteur : dans `Fenetre.__init__`, pour `typ == 66`, construire les 4 / 5 boutons de la table 6 (maillage 9 découpes largeur + 32 x 56, matériau feuille 1 partie 7, texte centré cs 9,3925) et brancher `params[(no, 0)]` sur leurs textes ; ajouter les zones tactiles (`buttonId = no`, manette 16).

### P2. Combat, type 29 : secousse, rouge de la barre, curseur
1. `Fenetre.code(i, c)` : si `c == 8` et `self.typ == 29`, `self.secousse[i] = 8`. Les nœuds à déplacer = la plaque du membre `i` (la partie dont `ib[0]` est un `frame`, plus tous les nœuds dont `par` est cette racine : textes, barres, visage).
2. Ajouter `Fenetre.tick()` appelé une fois par image du jeu avant `Rendu.dessiner` (dans `_dessiner_menus`, fenetre.py:1545, 30 Hz) : `m -= 1` ; si `m >= 0` ajouter `TABLE[m]` à `pos` des nœuds (`TABLE = [(-6,6),(6,-6),(6,-6),(-6,6),(6,6),(-6,-6),(-6,-6),(6,6)]`, indices 7 à 0) ; à `m == 0` appeler `_barre(ib, pt, ~cu['_v'])` pour la barre PV du membre (RedApply).
3. Curseur : compter 0,7 s en temps réel depuis le dernier `code(5, k)` ; basculer l'UV du nœud du curseur entre `uv_icone(infos[10], 2)` et `uv_icone(infos[10], 3)`.
4. Garder la mise à jour du rouge par la chaîne vide du moteur (ui_menu.py:215-218).

### P3. `StatusIconChanger` (types 4, 5, 20, 21, 46, 60, 61, 67)
1. `Fenetre.param_int` (ui_menu.py:185) : avant le `return`, `if cu.get('cls','').endswith('StatusIconChanger'): self._icone_etat(i, v); return`.
2. `_icone_etat(i, v)` : prendre la `i`-ième partie qui contient deux `ib` d'icônes de `partsNo == 13` ; `ib1`/`ib2` = ces deux icônes ; écrire dans `nd['uv']` à `ib['vtx'] + j` les quatre UV de `uv_icone(infos[13], v & 3, 0)` pour `ib1` et `uv_icone(infos[13], ((v >> 2) & 1) * 3, 0)` pour `ib2` ; mettre `nd['mats'][k]['color'] = couleurs[v >> 16]` pour le `k` dont `part == 13` (`Rendu.dessiner` lit déjà `mat['color']`, ui_menu.py:550 ; pas de changement de rendu).
3. Supprimer la référence à `s` dans la branche `ICityMap` de `param_int` (ui_menu.py:187).

### P4. `MonsterMarkList`
1. `fenetre.py:959` : faire retourner à `_ui_x_monstres` la liste des abscisses (une par monstre du masque) en plus de (min, max), par exemple un second paramètre `liste=True`.
2. `Fenetre.disposer` (ui_menu.py:324) : pour chaque plaque avec `pl[i]['code'] == 2` et un masque, activer autant de nœuds de marque (les nœuds du type 31 dont `mats[0].part == 6`) que de monstres : `pos = [x, 0.0, -64.0]`, UV = `uv_icone(infos[6], 5 + i, 0)`, `act = True`.
3. `Fenetre.code(4, c)` (ui_menu.py:240) pour le type 31 : repasser tous les nœuds de marque à `act = False` (Reset).

### P5. Type 54 (cadre de titre)
Dans `Fenetre.code(3, c)` pour `typ == 54` : `self._cadre(self.parts[0]['ib'][0], 219 + c)` ; si `c == 2`, masquer les boutons 1 et 2 et mettre le bouton 0 à `z = -266,25` ; sinon bouton 0 à -185. Test : `rend_type.py 54 sortie.png --fix54 0`. Laisser le bouton retour où il est (déplacement non résolu).

### P6. Rien à faire
Types 73, 77, 80 (écrans Unity hors table) ; `BattleBar` ; texte d'action sans cadre ; niveau « ? » (ce sont les comportements d'origine).

---

## 8. Reproduire (scripts de `/tmp/specs/`)

| Script | Rôle |
|---|---|
| `extraire_res.py` (sous `xvfb-run -a`) | extrait `ui_MenuTexture.png`, `ui_Button.png`, police, `ui_frameData.bin` dans `/tmp/r3_res` |
| `regen_ui.py [sortie]` | régénère la mise en page (4 min 25 s) dans `/tmp/r3_layout/ui_layout.json` ; erreurs : 73, 77, 80 |
| `desm.py <rva|nom> [fin]` | désassemble une méthode IL2CPP |
| `dasm_core.py`, `scan_got.py`, `scan_str.py`, `got.py`, `scan_got_il2.py` | moteur : désassemblage avec noms PLT, références à un emplacement GOT ou à un champ, valeur d'un GOT ; IL2CPP : méthodes qui chargent un emplacement GOT |
| `harnais.py`, `t6.py`, `lire_journal.py` | combat forcé sans fenêtre et journal des messages moteur -> interface (`t6.py <slot> <images> <journal.pkl>`, `lire_journal.py <pkl> <ports> ...`) |
| `t7.py <slot>` | état des membres (`PlayerStatus`), cause du niveau « ? » |
| `t_calc.py`, `t_shake.py` | `CalcScreenPosition`, `NotchHeight`, table de secousse sous le tracer |
| `inv_statusicon.py`, `scan_parts_manquantes.py`, `frames.py <i0> <i1>` | inventaires sur `ui_layout.json` et `frameData` |
| `rend_combat.py <slot> <png>`, `rend_type.py <type> <png> [--fix54 N]` | rendu hors écran avec le rendu de la visionneuse (sous `xvfb-run -a`) |

Journaux de messages : `/tmp/r3_journal_s1.pkl` (slot 1 : Ragnar + Doc), `/tmp/r3_journal_combat2.pkl` (slot 4). Images : `/tmp/specs/img/rendu_combat_s1.png`, `comp_54_66.png`, `marques_part6.png`, `curseur_part10.png` ; `/tmp/r3_part13_zoom.png`, `/tmp/r3_part6.png`.

### Limites de cet audit (supposé / non vérifié)
- Cadence de l'original pour la secousse (8 images Unity : 30 Hz supposé) ; appel de `ForceUpdate` du curseur ; sens du booléen statique qui replace le bouton retour du type 54 ; sens du code 2 de `StartMenuSelect` ; sens de `isSpell` (oeil) ; formule du maillage des boutons de 177,1.
- Les valeurs de statut (`StatusIconChanger`) viennent de la lecture du code moteur ; elles n'ont pas été vérifiées en provoquant un état (mort, poison) dans le moteur.
- Aucune comparaison avec une capture du jeu mobile n'a été faite (aucune fournie).
