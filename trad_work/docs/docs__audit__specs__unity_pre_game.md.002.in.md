### 8.2 `TapToStart` (Établi : `Make_TitleTouch` 0xCE4ED8, `Setup` 0xD0C1D4, `Update` 0xD0C738, `CountReset` 0xD0AF80)
Constantes (dump.cs) : `c_acc 0.025`, `c_cwait 20`, `c_firstWait 720`, `c_bias 0.68` (**inutilisé**), `c_width 223.04001`, `c_height 41.48`, `c_copyrightFirstWait 690`, `c_copyrightSecondWait 2508`, `c_copyrightWidth 450`, `c_copyrightHeight 40.0005`, `c_copyrightAcc 0.0625`.

`Make_TitleTouch` : un `MenuPortItem` + `TapToStart.Create(null)` (0xD0C158) + `AddParts` + `SetTableForCode(0, b__0)` où **code 0 = `TapToStart.CountReset`**.

**Quad « Touchez l'écran »** (ressource `Title/TapToStart`, shader `Custom/MenuParts`) : `SetVertex(0,0,0, 223.04, 41.48)`, UV (0,0,1,1) (toute la texture étirée), `Build(pivot 4 centre, écran 4 centre, pos (0, 0, -228))` -> **centre à 228 unités SOUS le centre d'écran** (en 450x800 : à 628 du haut), taille **223,04 x 41,48**, couleur de départ (1,1,1,0).
**Quad copyright** (ressource `Title/Retro4_copyright`) : `SetVertex` 450 x 40,0005, `Build(pivot 4, écran 7 bas-centre, z = 25,0003 + NotchFix(0))` -> centre à **25,0003 au-dessus du bord bas** (en 450x800 : y haut = 775), `CreateBuildDummy(7,0,0,0)`, Renderer désactivé au départ, couleur (1,1,1,0).

**Clignotement** (`Update`, par image rendue ; f = `frameCount - m_beginFrame`) :
* état initial : `m_acc = +0.025`, `m_alpha = 0`, `m_first = true`, `m_waitTouch = 720`.
* si `f >= m_waitTouch` : `m_first = false` ; `m_alpha += m_acc` ; si alpha > 1 ou < 0 : `m_waitTouch = f + 20`, alpha calé (1 si acc > 0, sinon 0), **acc = -acc**. Couleur du matériau = (1,1,1,alpha).
* résultat : montée linéaire 40 images (0,025/image), maintien 20 images (plein), descente 40 images, maintien 20 images (vide) : **période 120 images (4 s à 30 Hz)** ; **le premier affichage n'a lieu qu'après 720 images (24 s)** si `CountReset` n'est pas reçu.
* **`CountReset`** (message `[12,0,0]` du moteur) : si `m_first` : `m_waitTouch = 0` (le clignotement démarre aussitôt) ; `m_waitCopyright = 999999`, `copyrightAlpha = 1`, couleur copyright (1,1,1,1) = **copyright pleinement visible en permanence**.
* **Copyright sans `CountReset`** : attend 690 images, puis `alpha += 0.0625` par image (16 images) jusqu'à 1 ; `m_waitCopyright = 2508` ; à `f >= 2508` : `alpha -= 0.0625`/image ; < 0 : alpha 0 et `m_waitCopyright = 0xF423F` (plus jamais). (Cas non emprunté dans le flux observé, où `CountReset` arrive vers #69.)
* `TapToStart.Update` **n'envoie rien** au moteur.

**Entrée** : le toucher atteint le moteur sous forme de **pad A (0x10)** passé à `GameUpdate` (touches déclenchées) ; **Supposé** (route `TouchPad` -> bits de pad non lue en détail ; les traces confirment que le pad A (et pas un message de port) fait avancer le titre).

Ressources : `title_taptostart.png` (512x64, texte français « Touchez l'écran »), `title_retro4_copyright.png` (1024x64 : « ©ARMOR PROJECT / BIRD STUDIO / SPIKE CHUNSOFT / SQUARE ENIX All Rights Reserved. ©SUGIYAMA KOBO Developed by ArtePiazza »), copies `tex_taptostart*.png`, `tex_Retro4_copyright*.png`. Écrans de lancement Android (inutiles sur PC) : `title_retro4_splash*.png`.

### 8.3 Scène 3D du titre (moteur ; non détaillé)
Établi : paquets listés en 8.1 ; textures `m8900`, `m8901` (logo du titre selon les notes du dépôt), `m8905` exportées (`dssatex_m8900…8905.png`, `tex_m8901.png`…). **Non trouvé** : lien exact id 8900/8901/8905 -> objet Unity (shader supposé `DssaCharaTransparent`) ; BGM : signification binaire de `16384`, `16392`, `[1]` du paquet 37.

### 8.4 Réécriture pyglet
1. À la création du port de **type 73** (`[port,1,1,73]`), instancier l'état `TapToStart` : `debut = image courante`, `acc = 0.025`, `alpha = 0`, `premier = True`, `attente = 720`, `alpha_copy = 0`, `attente_copy = 690`.
2. À chaque image de jeu (30 Hz) : suivre exactement l'algorithme de 8.2 ; dessiner (a) le quad 223,04 x 41,48 centré en (cx, cy - 228*ech) avec alpha, (b) le copyright 450 x 40 centré en (cx, bas + 25*ech) avec alpha_copy (haut du carré à bas + 45*ech).
3. Message de port `[12,0,0]` sur ce port -> `CountReset` (si `premier` : `attente = 0` ; `attente_copy = 999999`, `alpha_copy = 1`).
4. Fermeture du port -> disparition des deux quads.
5. Entrée : clic / Entrée / Espace / A -> pad A (0x10) en « touche déclenchée » pour une image.
6. Le port 12 reçoit `[8,1]` (ignoreDraw) : ne rien dessiner par le chemin générique de menu pour ce port (le titre est entièrement dessiné par l'état `TapToStart`). Les ports 1..11 créés à l'image 0 ne contiennent aucun élément actif au titre.

---------------------------------------------------------------------------------------------------

## 9. Menu du titre (types 53 / 54) et flux « Créer un nouveau journal »

### 9.1 Menu (type 53, `Make_StartMenuSecond`, port 13 ; Établi par export `ui_layout.json` + trace)
Création #132 : port 12 type 74 (vide), **port 13 type 53**, **port 14 type 54**. Libellés envoyés par le moteur (`[11,i,no]` + chaîne) :
`i=0` « Continuer votre aventure », `1` « Reprendre une aventure interrompue », `2` « Créer un nouveau journal », `3` « Supprimer un journal » (param `no=1`) ; `5` « Sauv. cloud », `6` « Licence » (param `no=0`).
Puis `[12,0,0]` (code 0 du type) et `[10,i,0,3,0]` pour i = 0, 1, 3 (paramètres d'état des items).

Mise en page (design 450x800, repère « root » = coin bas-gauche (-225, z -402), coordonnées `xyz` de `builds`) :
| Bouton (id Unity) | Libellé | Placement |
|---|---|---|
| id 4 (item 4) | bouton sans libellé dans la trace (le moteur n'envoie que les items 0-3, 5, 6) ; usage non établi | écran 7 (bas-centre), (0, **372**) |
| id 0 | Continuer | écran 7, (0, **272,5**) |
| id 1 | Reprendre | écran 7, (0, **215**) |
| id 2 | Créer un nouveau journal | écran 7, (0, **157,5**) |
| id 3 | Supprimer un journal | écran 7, (0, **100**) |
| id 8 (item 5) | **Sauv. cloud** | écran 7, (66,5, z 34) |
| id 11 (item 6) | **Licence** | écran 6 (bas-gauche), (62,5, z 34) |
| id -1 (pad 32 = B) | bouton Retour (icône partie 3) | écran 6, (412,5, z 34) |
Textes : alignement 1 (centre), ancre 4, `characterSize 10,4975`, `lineSpacing 0,8013`, y = 8 (devant le bouton).
**Attention** : l'identifiant de bouton envoyé est celui du tableau (0, 1, 2, 3, 8, 11), pas le numéro d'item.

Code 0 du type 53 (`<Make_StartMenuSecond>b__0`, 0xD0A4E4) : change la partie de l'icône IBase n°0 selon la langue (0xD7 + 1 si langue 0 ; avec prm != 0 : 0xD9 / 0xDA) puis masque le MenuParts n°1. Établi (désassemblage) ; effet visuel exact : **Supposé** (choix de variante du logo).

### 9.2 Interactions (Établi par traces `t2_f` … `t2_m`)
* Le **pad** (bas/A) ne fait rien sur ce menu ; la sélection passe par un message de port : `envoyer_menu(13, 1, idBouton, 16)`.
* **Créer un nouveau journal** : `13: 1,2,16` -> moteur `port 13 [4,2]`, port 14 (type 54) rempli : titre « Créer un nouveau\njournal » + 3 emplacements « Inutilisé » ; `14: 1,0,16` (emplacement 0) -> ports 12-14 fermés, **port 15 type 55 (StartNameEntry)** : item 0 « Choisir le sexe », 2 « Masculin », 3 « Féminin », puis `[12,0,8]` (SetLanguage(0, 8)) et `[12,1,1]` (affiche clavier + boutons de sexe).
* **Licence** : `13: 1,11,16` -> moteur : paquet 9 **`[20510]`** (sortie 30 im., bit 14) + `[4,11]` ; **30 images plus tard (#251)** : `port 0 [15,1,1,80]` (**port 15 type 80 = License**), `port 15 [1,1,1,0]`. Retour : message `15: 1,-1,32` (bouton retour, B) -> moteur : paquet 9 **`[16414]`** (entrée 30 im.) et `port 0 [15,2]` (fermeture) ; le menu 13 reste actif dessous (aucune réouverture observée).
* **Sauv. cloud** : `13: 1,8,16` -> le moteur ferme les ports 12, 13, 14 (`[12,2]`, `[13,2]`, `[14,2]`), crée **`[15,1,4,0]` = port de catégorie 4 = `NetConnection`** (section 10), puis une fenêtre de message (port 1 : `[0,0]`, `[3,-3]`, `port 0 [1,3,1]`, `[1,4,0]`…) et **attend la réponse d'Unity** (rien reçu ensuite) : sans réponse l'écran reste bloqué. **Recommandation : ne pas afficher / ne pas accepter le bouton id 8 sur PC** (pas de Google Play Games) ou implémenter un répondeur (non établi, section 10).
* Continuer / Reprendre / Supprimer (ids 0, 1, 3) : traités par le moteur (hors périmètre Unity ; non tracés ici).

---------------------------------------------------------------------------------------------------

## 10. `NetConnection` (catégorie 4) : protocole moteur -> Unity

Établi : `MenuPort.CreateMenuPort` 0xD0F7EC (catégorie 4) ; constantes : textes de maintenance, noms de sauvegarde `DQ4_SAVEDATA.DAT`, `data7.dat`, magic `2081597150`, version 1 ; bits d'état `S_BUSY0 … S_CLOUD_IS_NEW5`.
`NoticeReceive` 0xD18A94, table sur `prm[0]` : 0 `SQMK_Auth` (si pas déjà authentifié) ; 1 si `s_presentcodeList` nul -> `Send([1, 0x321])` ; 2 `SQMK_CampaignCodeAuth` ; 3-9 rien ; 10 `CloudAuth` ; 11 `CloudSyncFileCheck` ; 12 `OpenURL("market://details?id=com.google.android.gms")` ; 13 `CloudSyncFile` ; 0x50 `OpenURL("http://sqex-bridge.jp/?utm_source=DQ4&utm_medium=app")`.
Coroutines (RVA MoveNext) : CloudAuth 0xD18E04, CloudSyncFile 0xD19074, CloudSyncFileCheck 0xD194C0, MaintenanceDialogTask 0xD1973C, SQMK_Auth 0xD198A4, SQMK_CampaignCodeAuth 0xD1A99C (dumps `_net_*.txt`).
**Non trouvé** : les réponses exactes (`Send`) de chaque coroutine et le moment où le moteur envoie les notices. Verdict portage : **fonction hors périmètre** (réseau Square Enix / Google), à masquer.

---------------------------------------------------------------------------------------------------

## 11. Écran « Licence » (type 80) : `LicensePolicy`, `LicenseNobu`

Établi : `Make_License` 0xCF7228 (l'exporteur du dépôt échoue sur ce type : `UC_ERR_READ_UNMAPPED`) :
* `MenuPortItem` ; `ratio = (Screen.height/Screen.width) / (16/9)` ; `CreateBuildVariableWindow(0, 14.0, ratio*600, 8, false)` ; `CreateWindow0(54.0, 47.0)` ; `LicenseNobu.Create(ratio)` ; texte du TextAsset `Menu/License_list_A` (variante Android ; `License_list_I` = iOS) : **23626 octets, 488 lignes, CRLF, balises riches `<color=orange>…`** (`/tmp/specs/work/textasset_license_list_a.bin`) ; `NotchFix` ; maillages de texte à y = -8 ; `Sub_BackButton` ; `LicensePolicy.Create`.
* **`LicensePolicy`** (0xD0E784) : fenêtre 360 x 46 à l'ancre 7 (bas-centre), cadre partie 0xC0, bouton ; libellé localisé : JA プライバシーポリシー, EN `Privacy Policy`, KO 개인 정보 보호 정책, ZH-TW 隱私條款, ZH-CN 隐私条款 ; `OnMouseUpAsButton` (0xD0EC60) -> `Application.OpenURL(langue == 0 ? "https://www.jp.square-enix.com/privacy/" : "https://square-enix-games.com/en_US/documents/privacy")`.
* **`LicenseNobu`** (`c_baseY 6.25` ; `Create` 0xD0EE5C, `Start` 0xD0F018, `Update` 0xD0F07C) : barre de défilement dont le curseur se **glisse avec le pointeur** (`RawPads.Ray` / `Collider.Raycast`) ; position du curseur bornée entre 6,25 et `m_scroolMax` (champ 0x70) ; `ratio = 1 - (pos - 6.25)/(max - 6.25)` ; le texte (`m_target`) est déplacé proportionnellement (`m_textS` 0x64, `m_textH`). Valeurs 80,0 et 500,0 (`0x42A00000`, `0x43FA0000`) lues dans `Create`.
* **Non trouvé** : positions / tailles exactes de la fenêtre (le calcul dépend de `ratio` et du maillage de fenêtre variable `partie 0`), hauteur du texte visible, taille de caractère.

Réécriture : au port type 80 -> afficher un fond noir (le moteur a déjà fait le fondu sortant `[20510]`), une fenêtre contenant le texte de `License_list_A` (balises `<color=orange>` à rendre en orange), défilement molette / barre, bouton « Privacy Policy » ouvrant l'URL (langue != 0 : l'URL « en_US »), bouton Retour / Échap -> `envoyer_menu(15, 1, -1, 32)`.

---------------------------------------------------------------------------------------------------

## 12. Saisie du nom (`StartNameEntry` type 55, `InputName`)

### 12.1 Fenêtre (Établi : export `ui_layout.json` type 55 + `Make_StartNameEntry` 0xCF6D6C)
Cadre `init 222` (0xDE), 2 textes (params 0 et 1 : « Choisir le sexe » …), bouton Retour (ancre 6, `xyz (412,5, 4, 34)`), **2 boutons de sexe** (params 2 « Masculin », 3 « Féminin » ; positions relatives au root : x 120,4 et 331,6, z 212), codes 3 et 4 = activer/désactiver les parties 2 et 3 ; `InputName.Setup(uol)` (0xCE34EC).

### 12.2 `InputName` : codes d'item (Établi)
* **code 0** = `SetLanguage(lng = prm >> 8 (octet signé), resultMax = prm & 0xFF)` ; observé `[12,0,8]` -> langue 0, **8 caractères maximum**.
* **code 1** = `SetVisible(prm != 0)` + `ignoreDraw` des parties 3 et 4 ; `[12,1,1]` affiche clavier + boutons de sexe, `[12,1,0]` les masque.

### 12.3 Jeux de caractères (Établi, cctor 0xCE3D54 ; `/tmp/specs/work/inputname_sets.json`)
* `C_ALPHABET` (2 pages de 35) minuscules : `abcdefghijklmnopqrstuvwxyz -,.!?＠＠＠` ; majuscules : même ordre en capitales. `＠` (U+FF20) = case vide (`C_NA`).
* `C_AA` (accents, 70 = 2 x 35) : `àáâäçèéêëìíîïñòóôöùúûüß` + `＠`… ; majuscules `ÀÁÂÄÇÈÉÊËÌÍÎÏÑÒÓÔÖÙÚÛÜß`.
* `C_LOCALIZE = [C_ALPHABET, C_AA]`. `C_HIRA` / `C_KATA` (240 = 4 pages x 12 lignes x 5 : normal, petit, dakuten, handakuten) ; `C_CAMPAIGN_MOJI` (40 : `A…Z` + `0…9`, 8 lignes x 5) ; `C_JAPANESE = [hira, kata]`, `C_CAMPAIGN = [moji, null]`.
* Étiquettes des boutons de fonction : `C_ALPHABET_ETC = ['Alphabet', 'à À', 'Maj.', null, null, 'Suppr.', 'OK']` (non localisé, présent en anglais/français) ; `C_JAPANESE_ETC = ['ひらがな','カタカナ','小文字','゛','゜','もどる','けってい']` ; `C_CAMPAIGN_ETC = ['英数', null x4, 'もどる', 'けってい']`.

### 12.4 Grille (Établi)
`BTN_X_SPAN 69`, `BTN_Y_SPAN 82`, `BTN_W1/H1 30`, `BTN_W2/H2 36` ; **5 colonnes x 7 lignes** (35 par page) ; `MakeNameButton` 0xCDFB94 : `CreateButton(30, 30, bid, 0)` ; ligne = bid / 5, colonne = bid % 5 ; position locale `x = bpos.x + col*69`, `z = bpos.z - ligne*82` ; texte `characterSize 9,5` (couche 10) ; caméra secondaire orthographique taille 225, `cullingMask 0x400` (couche 10), `depth 2`, `clearFlags 3` (profondeur seule), `pixelRect` déduit de `WorldToScreenPoint` (370, ?, -370) pour **rogner** la grille. Nom saisi : TextMesh `characterSize 9`, `tabSize 1` puis 6 ; `MakeDispName` 0xCDFCE4 = `\t` + chaque caractère (ou blanc `m_blank`) + `\t` pour chaque emplacement.
**Non trouvé / non interprété** : origine `bpos` de la grille (champs +0x4C, +0x70 de l'objet), positions des boutons de fonction (constantes brutes vues : 123,5 / 328 / 616 / 166 / 29 / 36 / 60 / 123 / 150 / 57,5 / 222 / 214 / 709 / 82), logique de `SetMode` 0xCE11BC / `SetLanguage` 0xCE1AA8 (changement de page / de mode).

### 12.5 Protocole de retour vers le moteur (Établi, vérifié sous Unicorn)
`Update` 0xCDFFFC, `m_status` (champ 0xB4) :
* **-1 = annulation** (touche retour, SE 300 = 0x12C) -> `Send(port, short[]{1, 0x20, 0})` (= message `[1, 32, 0]`).
* **1 = OK** -> `Send(port, short[]{2, longueurOctets})` **puis** `SendBytes(port, octets UTF-8 du nom)` ; `m_status = 9`. Les octets sont empaquetés petit-boutiste en shorts (`short[k] = b[2k] | b[2k+1] << 8`, `ceil(n/2)` shorts) : « Sylfried » -> `[2, 8]` + `31059, 26220, 26994, 25701`.
* **Les deux messages doivent partir à la MÊME image** : le moteur répond alors `port 15 [12,1,0]` (masque la fenêtre) et `[11,1,0]` + chaîne `Sylfried`. Envoyés à des images différentes, **le moteur plante** (`memcpy` depuis une adresse non mappée -> « le moteur s'est arrêté »). Établi (`t2_h`/`t2_i`/`t2_j`).
* Après le nom, un message `[1,0,16]` sur le port 15 conduit au rebâtissement du menu, une fenêtre de message (port 1), un fondu `[4126]` (#411) et les paquets de nouvelle partie dès #443 : **l'étape de confirmation exacte n'a pas été décodée**.

### 12.6 Réécriture pyglet (recommandation)
Ne pas reproduire le clavier en grille : au `[12,1,1]` sur le type 55, afficher la fenêtre (export type 55) + une **zone de saisie texte du PC** limitée à `resultMax` caractères ; à la validation envoyer, dans le **même appel / la même image**, `envoyer_menu(15, 2, n)` puis les shorts d'octets UTF-8 ; à l'annulation `envoyer_menu(15, 1, 32, 0)`. (Le clavier de l'original, grille 5x7 de 69 x 82, reste décrit en 12.3-12.4 si une reproduction fidèle est voulue.)

---------------------------------------------------------------------------------------------------

## 13. Table des ressources (où trouver quoi)
| Élément | Ressource | Emplacement | PNG exporté |
|---|---|---|---|
| Logos | textures pid 15, 11, 17 | `base.apk` -> `level0` / `sharedassets0` | `/tmp/specs/img/boot_warning_15.png`, `boot_sqex_11.png`, `boot_arte_logo720_240_17.png` |
| Shader logos | `Custom/Picture` (pid 19), `Custom/MenuParts` (pid 20) | sharedassets0 | GLSL `/tmp/specs/work/shader_sa0_19_gles3.txt`, `_20_` |
| Texte « quitter » | TextAsset `quitmsg` (pid 21) | sharedassets0 | `/tmp/specs/work/textasset_quitmsg.bin` |
| « Touchez l'écran » | `Title/TapToStart` (`Resources`) | datapack | `title_taptostart.png` |
| Copyright | `Title/Retro4_copyright` | datapack | `title_retro4_copyright.png` |
| Portail (mort) | `Title/PotalButton` | datapack | `title_potalbutton.png` |
| Dégradé de fond | shader `BackColor` (pid 26927) | datapack `resources.assets` | `/tmp/specs/work/shader_BackColor_p5.bin`, `p9.bin` |
| Licence | TextAsset `Menu/License_list_A` / `_I` | datapack | `/tmp/specs/work/textasset_license_list_a.bin`, `_i.bin` |
| Mailles du titre | `m8900`, `m8901`, `m8905` | datapack | `dssatex_m8900…8905.png`, `tex_m8901.png` |
| Polices / boutons de `Boot` (inutilisés) | GMaruGoPro-M, SE-GARRIR, FOTK-YDHopeL, FZHTK_TL/SL ; Menu, Button | level0 / sharedassets0 | `boot_Font_Texture_*.png`, `boot_Button_12.png`, `boot_MenuTexture_16.png`, `boot_SE-GARRIR_10.png` |

---------------------------------------------------------------------------------------------------
