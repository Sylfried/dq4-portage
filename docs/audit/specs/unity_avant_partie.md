# Spécification exacte : ce que la couche Unity fait AVANT le début d'une partie (DQ4 Android, Unity 2022.3.62f3 IL2CPP ARM64)

Sources : dump IL2CPP `/home/claude/il2/` (`dump.cs`, `script.json`, `libil2cpp.so`), scène `level0` et `sharedassets0` de `base.apk`, `resources.assets` / `datapack`, moteur `libdq4core.so` exécuté sous Unicorn (visionneuse `/home/claude/dq4-portage`, lecture seule).
Vocabulaire des preuves : **Établi** = lu dans le code (adresse RVA de la méthode, constante lue) ou observé dans une trace moteur (`/tmp/specs/work/t2_*.log`) ; **Supposé** = déduit, non vérifié ; **Non trouvé** = valeur non retrouvée.
Les RVA sont des adresses `libil2cpp.so` (octet fichier = RVA - 0x4000 pour le code). Dumps de désassemblage : `/tmp/specs/scripts/_*.txt` ; outils : section 16.

---------------------------------------------------------------------------------------------------

## 0. Conventions communes (à lire d'abord)

| Point | Valeur | Preuve |
|---|---|---|
| Conception d'interface | portrait **450 x 800** ; demi-largeur 225 (`0x43610000`), demi-hauteur H = 225 / aspect (aspect 0,5625 -> **400**) ; `eIndent.Init` 0xD2370C stocke H et 2H dans les statiques [0], [4] | Établi |
| Plan des menus | plan **XZ** : x horizontal, **z vertical vers le haut**, y = profondeur / couche (les valeurs y 4, 8 des noeuds = ordre de superposition) | Établi (export `ui_layout.json`) |
| Ancres d'écran `eIndent.CalcScreenPosition` 0xD23938 | 0 haut-gauche (x-225, z+H), 1 haut-centre, 2 haut-droite (x+225, z+H), 3 milieu-gauche, **4 centre**, 5 milieu-droite, 6 bas-gauche (z-H), **7 bas-centre**, 8 bas-droite | Établi |
| `NotchFix.AdjustmentValue` / `InputNameAdjustmentValue` | 0 sur PC (pas d'encoche) | Établi |
| Quad `MeshMaker.SetVertex(x,y,z,w,h)` | coin haut-gauche (x, z), s'étend vers (x+w, z-h) ; `Build(pivot…)` recentre sur le pivot (4 = centre, numérotation supposée identique à eIndent) | Établi (SetVertex) / Supposé (numéro de pivot) |
| Passage unités de conception -> pixels visionneuse | `Fenetre._ui_repere()` (fenetre.py ~1205) renvoie (x centre, y centre, px par unité) = `(width/2, height/2, height/800*ui_k)`. Un point (x, z) de conception relatif au centre d'écran = pixel `(cx + x*ech, cy + z*ech)` (pyglet : y vers le haut) | Établi (code du dépôt) |
| Cadence | Unity **30 Hz** (pas de `targetFrameRate`, `vSyncCount` 0 ; `Time.fixedDeltaTime = 1/30`, `maximumDeltaTime = 1/3`). `TapToStart` compte des images rendues (`Time.frameCount`), `Boot.Logo` compte en secondes réelles (`Time.deltaTime`) | Établi (constantes) / Supposé (30 Hz effectif ; cohérent avec les notes du dépôt : `FldObject.Update` +2 par image à 30 Hz) |
| Langue | `GetLangages.Init` 0xCBB1B8 (via `java.util.Locale`) : 0 JA, **1 EN (défaut ; la visionneuse passe 1 à DevInit)**, 2 KO, 3 ZH-TW, 4 ZH-CN | Établi |
| Fond de rendu | `Camera.main` : clear flags 2 (couleur unie), fond (0,0,0,0) noir, fov 60, far 1000 ; caméra orthographique `Boot` de taille `(1/aspect)*225` (= 400 en 450x800) | Établi (scène level0 + Boot.Start) |

Protocole moteur <-> Unity utilisé ci-dessous (déjà implémenté dans `dq4_pc/moteur.py`) :
* Sortie moteur = flux d'entiers `[état, paquet…, -1]`. Paquets pertinents ici : 0 `fld_load`, 8 `back_color` (6 flottants : RVB haut puis RVB bas), 9 `fade`, 10 caméra, 11 caméra_sub, 12/14 chara, 21 `mesh_load`, 31 `fbx_load`, 37 BGM.
* **Paquet 9 (`cmd_fade`, 0xD14C70)** : `v & 0x7FF` = nombre d'images ; bit 12 (0x1000) = fondu **sortant** (vers le noir) sinon entrant ; bit 14 (0x4000) = lève le drapeau statique `Fade` (variante). Valeurs vues : `4126 = 0x101E` (sortie noir 30 images), `30` (entrée 30 images), `20510 = 0x501E` (sortie noir 30 images, bit 14), `16414 = 0x401E` (entrée 30 images, bit 14). Établi (décodage) ; rôle exact du bit 14 : **Supposé** (fondu qui laisse les fenêtres UI par-dessus : voir section 11, l'écran Licence s'affiche pendant que le fondu est « noir »).
* Menus : `MenuPortSystem` (32 ports, tampons 129 / 1089). Port 0 = canal de gestion : `[port,1,catégorie,type]` crée un port, `[port,2]` le ferme. Commandes d'un port : 1 setup, 4 curseur (`[4,n]`), 5 dessin, 6 saisie autorisée, 8 ignoreDraw, 10 setItemParamInt, 11 setItemParamString (`[11,i,no]` + `STR`), 12 setItemCode (`[12,code,prm]`). Unity -> moteur : `moteur.envoyer_menu(port, 1, idBouton, masquePad)` ; masque pad : bas 1, haut 2, droite 4, gauche 8, A 16, B 32, X 64, Y 128.
* Table type -> `Make_*` (`/tmp/specs/work/type_to_make.txt`, obtenue par exécution du cctor) : 1 YesNo, 2 Money, 3 RootMenu, **52 StartMenuFirst, 53 StartMenuSecond (menu du titre), 54 StartMenuSelect (choix d'emplacement), 55 StartNameEntry, 56 SaveOverwrite, 72 ViewVolumeDecision, 73 TitleTouch (TapToStart), 74 PortalButton, 75/76 NetworkRoot, 77 NetworkPLST, 78 NetworkCODE, 79 NetworkITEM, 80 License**.

---------------------------------------------------------------------------------------------------

## 1. Chronologie complète du démarrage (Unity, avant que le moteur ne joue)

| # | Étape | Méthode (RVA) | Détail | Statut |
|---|---|---|---|---|
| 1 | Scène `level0` : objets `Main Camera`, `New Text` (TextMesh vide), MonoBehaviour **Boot** | scène | caméra noire (section 0) | Établi |
| 2 | `Boot.Start` (coroutine, MoveNext 0xCC5C6C) | | `Cursor.visible = false` (arg 0), `Cursor.lockState = 1` (Locked) ; `GetLangages.Init` | Établi |
| 3 | `GooglePlayGamesServiceManager.Init` 0xCDEF10 puis `.Auth` 0xCDEF2C | | `PlayGamesPlatform.DebugLogEnabled=false; Activate()` ; `Social.localUser.Authenticate(cb)`, le rappel `<Auth>b__4_0` est **vide** | Établi -> **ignorable sur PC** |
| 4 | `Screen.fullScreen = true` ; test chemin `.obb` | | sans effet utile sur PC | Établi |
| 5 | caméra ortho taille `(1/aspect)*225` | | | Établi |
| 6 | `ApplicationQuit.SystemInit(m_quitmsg.text)` (appelé 2 fois, même texte) ; `RemoveObbFile` | 0xCC3650 | découpe `quitmsg` sur `\t` (section 4) | Établi |
| 7 | `Logo()` : affichage des logos | MoveNext 0xCC5618 | section 2 | Établi |
| 8 | `Boot.Quiting` (0xCC4D20) | | gère le dialogue de sortie s'il a été demandé | Établi |
| 9 | `Time.fixedDeltaTime = 0.0333333`, `maximumDeltaTime = 0.3333333` ; `NativeCall.SetNoNeonMode` si CPU sans NEON ; `android.os.Build.MODEL` en majuscules | | | Établi |
| 10 | `SceneManager.LoadScene("dq4sp")` | | scène principale | Établi |
| 11 | `MainLoop.Start` (MoveNext 0xCF94C8), ordre exact : `DontDestroyOnLoad` ; `NativeCall.DeviceInit` (0xCBCA50) ; `BackColor.SystemInit` (0xCC42CC) ; `Fade.SystemInit` ; `Capture.SystemInit` ; `BillboardObject.SystemInit` ; `Chara.SystemInit` ; `Riseup.SystemInit` ; `MeshChara.SystemInit` ; `SceneCamera.SystemInit` ; `TouchPad.AdjustCameraOrtho` ; `MenuParts.SystemInit` ; `MenuPortSystem.SystemInit` (0xD10790 : GameObject « MenuPortSystem », `MenuPortSystemEx` si `Boot.s_useFixedUpdate` sinon `MenuPortSystem` ; `MenuPortInit(32, buf1, 129, buf2, 1089)`) ; `Sound.SystemInit` ; `Field.SystemInit` ; `NativeManager.Init` (0xD156B4) ; `Global.InitCamera` (0xCDE878) ; `SceneCamera.Update` ; init shaders / polices / `MeshList.Load` / `TexInfo` / `PartsInfo` | | | Établi |
| 12 | Par image : `NativeManager.Update` (0xD15758) = `SetInt` (entrées) / `GameUpdate` du moteur / `GetInt` (paquets) ; puis `SceneCamera.Update`, `Chara.UpdateBillboardShadows`, `FldObject.Update`, `Field.UpdatePattern`, `Sound.SystemUpdate` | | `MenuPortSystem.internalUpdate` appelle `ApplicationQuit.Create` (0xCC3D30, sites 0xD10DC0 et 0xD111B4) | Établi |
| 13 | Le moteur démarre en partie 0xC (TownPart, carte `ev/ev01/out/ev01` = titre), voir section 8 | | | Établi (trace) |

Rien d'autre n'est exécuté par Unity avant la partie : pas de menu de langue, pas de téléchargement (`ObbDownloadRes` est du code mort, section 5), pas d'écran de chargement propre à Unity.

---------------------------------------------------------------------------------------------------

## 2. `Boot` : logos d'entrée (`Boot.Logo`, MoveNext 0xCC5618)

### 2.1 Rôle
Trois écrans de logo noirs qui apparaissent / disparaissent en fondu avant de charger `dq4sp`.

### 2.2 Valeurs exactes (Établi)
Constantes `Boot` (dump.cs) : `c_fadeTime = 1` s, `c_waitTime = 3` s, `c_skipBias = 10` (**non utilisé** : aucun immédiat 10.0 dans le code), `c_fixedDeltaTime = 0.03333333`, `c_maximumDeltaTime = 0.3333333`.

Objet : un **Quad primitif Unity** avec `Material(m_logoShader)` (shader `Custom/Picture`, sharedassets0 pid 19), parenté à la caméra principale, `localPosition = (0, 0, 150)`, `localScale = (450, 450, 1)`, rotation identité -> un **carré 450 x 450 unités de conception, centré à l'écran** (la texture 720 x 720 le remplit ; la caméra voit 450 de large en portrait).

Liste `m_logoTexture[3]` (dans l'ordre) : (1) `warning` (sharedassets0 pid 15), (2) `sqex` (pid 11), (3) `arte_logo720_240` (pid 17). **« warning » est ignoré si la langue n'est pas 0 (JA)** : en langue 1 (EN/FR du patch) seuls sqex puis arte s'affichent.

Pour chaque logo : `mainTexture = tex`, `color = (1,1,1,0)`, puis
1. **Entrée** : `timer += Time.deltaTime` chaque image ; alpha = timer (rampe linéaire) jusqu'à timer >= 1,0 ; alpha := 1.
2. **Maintien** : timer remis à 0 ; chaque image `timer += dt` ; fin si timer >= **3,0** s.
3. **Sortie** : timer = 0 ; alpha = 1 - timer ; à timer >= 1,0 le Renderer est désactivé ; logo suivant.
4. **Saut** : un front de toucher (`Boot.Touch(ref prs)` 0xCC4FB4 = `touchCount > 0 && !précédent`) pendant l'**entrée** lève un drapeau « tapped » (champ +0x45) : après l'entrée, le maintien est sauté (on passe directement à la sortie). Un front de toucher pendant le **maintien** déclenche la sortie immédiatement.
Durée sans toucher : 5 s par logo (1 + 3 + 1) -> **10 s** (EN/FR : sqex + arte), 15 s en JA.

Shader `Custom/Picture` : fragment = `tex * _Color` ; fusion alpha (`SrcAlpha`, `OneMinusSrcAlpha` = états 5 / 10) ; `ZWrite Off`, `ZTest LEqual`, `Cull Back` ; le sommet utilise `_MainTex_ST`. (`Custom/MenuParts`, pid 20 : mêmes états, sans `_MainTex_ST`.) Fichiers : `/tmp/specs/work/shader_sa0_19_gles3.txt`, `_20_`.

### 2.3 Ressources (PNG exportés dans `/tmp/specs/img/`)
`boot_warning_15.png` (avertissement japonais pour mineurs, 720x720, texte blanc sur noir), `boot_sqex_11.png` (logo SQUARE ENIX, 720x720), `boot_arte_logo720_240_17.png` (ArtePiazza « CG Illustration & Entertainment », 720x720). Autres textures de `level0`/`sharedassets0` utilisées par du code mort : `boot_Button_12.png`, `boot_MenuTexture_16.png`, `boot_Font_Texture_*.png`, `boot_SE-GARRIR_10.png`.

### 2.4 Échange avec le moteur
Aucun (le moteur n'est pas encore initialisé : `NativeManager.Init` vient après).

### 2.5 Réécriture pyglet
1. Fond noir. Liste = `[sqex, arte]` (ajouter `warning` en tête uniquement si la langue vaut 0).
2. Par logo, avec le temps réel `dt` : phase entrée (alpha = t, t de 0 à 1 s), maintien 3 s, sortie (alpha = 1 - t sur 1 s). Dessin d'un carré de côté `450 * ech` centré en (cx, cy), fusion alpha classique, texture 720x720.
3. Entrée utilisateur : clic / Entrée / Espace pendant l'entrée -> sauter le maintien ; pendant le maintien -> sortie immédiate. Fermeture de fenêtre = quitter.
4. Ensuite seulement créer le moteur (`DevInit` langue 1), fond `BackColor` noir (section 6), boucle à 30 Hz.

---------------------------------------------------------------------------------------------------

## 3. Langue (`GetLangages`)
Établi : `Init` 0xCBB1B8 lit `java.util.Locale` -> index 0 JA, 1 EN, 2 KO, 3 ZH-TW, 4 ZH-CN (défaut EN). Statique [4] = langue lue par `Boot.Logo`, `LicensePolicy`, `Make_StartMenuSecond` b__0. **Le patch français occupe l'index 1** (les textes moteur sont déjà en français). Rien d'autre côté Unity avant la partie.

---------------------------------------------------------------------------------------------------

## 4. `ApplicationQuit` (dialogue « quitter »)

### 4.1 Rôle (Établi)
Classe statique : `s_title`, `s_message`, `s_yes`, `s_no`, `s_quitStatus` (0x20), `s_disable` (0x24). `SystemInit` (0xCC3650) découpe le TextAsset `quitmsg` (402 octets) sur `\t` (char 9) : **5 langues x (titre, message, oui, non)**.

### 4.2 Textes littéraux (Établi, `/tmp/specs/work/textasset_quitmsg.bin`)
| Langue | Titre | Message | Oui / Non |
|---|---|---|---|
| JA | 終了確認 | アプリを終了しますか？ | はい / いいえ |
| **EN (index 1, à traduire pour le FR si voulu)** | `Confirm Termination` | `Are you sure you wish to terminate the application?` | `Yes` / `No` |
| KO | 종료 확인 | 앱을 종료하시겠습니까? | 예 / 아니요 |
| ZH-TW | 確認結束 | 結束應用。還未記錄至今為止的冒險記錄，沒關係嗎？ | 是 / 否 |
| ZH-CN | (même structure, chinois simplifié) | | |

### 4.3 Mécanisme (Établi)
Dialogue **natif Android** (`com.cattlecall.unityandroidaccessor.OverrideUnityPlayerNativeActivity.ShowDialog`, résultat dans `m_result`) : `OpenQuitDialog` 0xCC3770, `GetQuitDialogResult` 0xCC3ACC, `ForceQuit` 0xCC3CAC. `Update` 0xCC3E18 = machine à états sur `s_quitStatus` (0..4) : ouvre le dialogue, `Time.timeScale` en pause, `Fade.SetFadeOutBlack(30)` (0xCC4100), résultat 1 (oui) / 2 (non). Qui met `s_quitStatus = 1` : `Update` lit un drapeau des statiques de `TouchPad` (`[8+2]` bit 1), **Supposé = touche Retour Android**. Aucun échange avec le moteur.

### 4.4 Réécriture
Fenêtre de confirmation à deux boutons (Oui / Non) ouverte par Échap ou la fermeture de la fenêtre ; textes de 4.2 (ou traduction française : « Voulez-vous vraiment quitter l'application ? », Oui / Non). Pause du jeu et fondu sortant noir de 30 images pendant la question (Établi pour le fondu, Supposé pour la reprise en fondu entrant).

---------------------------------------------------------------------------------------------------

## 5. Éléments Google / OBB / Portail : code mort ou ignorable (Établi)

| Élément | Verdict | Preuve |
|---|---|---|
| `GooglePlayGamesServiceManager` / `UnityGoogleSavedGames` | `Init` = `PlayGamesPlatform.Activate()`, `Auth` = `Authenticate(cb)` avec rappel vide : **ignorer** | 0xCDEF10, 0xCDEF2C |
| `ObbDownloadRes` (`c_obbFileSize 210`, « Reboot ») | `SystemInit` 0xD1BC18 et `DLFlow` 0xD1C20C n'ont **aucun appelant** ; champs `Boot.m_obb*` renseignés dans la scène mais inutilisés | recherche d'appelants (`xref.py`) |
| `PortalButton` | `Setup` 0xD0F408 (charge `Title/PotalButton`, quad 96x96, ancre 2 haut-droite, pos (-70, 0, -60), donc centre à (155, 340) en conception) **sans appelant** ; `Make_PortalButton` 0xCF71BC ne crée qu'un `MenuPortItem` nu : le type 74 **n'affiche rien** dans ce build. Texture : `title_potalbutton.png` (128x128) | `ref_slot.py` |
| `Boot.m_obbMenuParts/Font/Mat/obbmsg` | inutilisés | scène |

---------------------------------------------------------------------------------------------------

## 6. `BackColor` (dégradé plein écran) et `Fade`

### 6.1 BackColor (Établi)
* `SystemInit` 0xCC42CC crée le GameObject « BackColor » ; `Awake` 0xCC45BC : MeshFilter, **4 sommets en espace écran** (1,1,0), (-1,1,0), (-1,-1,0), (1,-1,0) ; 2 triangles ; couleurs de sommets = tableau statique `Color[4]` ; MeshRenderer avec `Material(Shader.Find("BackColor"))` ; parent = transform de `MainLoop`, `localScale (1,1,1)`, `localPosition (0,0,20)`.
* Shader « BackColor » (datapack `resources.assets` pid 26927 ; GLSL `/tmp/specs/work/shader_BackColor_p5.bin`, `p9.bin`) : `Queue Background`, `ZTest Always`, `ZWrite Off` ; `gl_Position = in_POSITION0; vs_COLOR0 = in_COLOR0;` fragment = couleur de sommet -> **dégradé vertical** : sommets 0 et 1 (y = +1, haut) = couleur du haut, 2 et 3 (y = -1) = couleur du bas, interpolation linéaire.
* Statiques (klass+0xB8) : [0] instance, [8] pas (= 1/images), [0xC] t, [0x10..0x1C] cible haut RGBA, [0x20..0x2C] cible bas, [0x30] `Color[4]`. cctor : pas 0, t 1,0, tout noir (0,0,0,1).
* `SetColor(int images, haut RGBA, bas RGBA)` 0xCC43F8 : images < 1 -> t = 1 et couleurs appliquées tout de suite ; sinon pas = 1/images, t = 0, cibles mémorisées. `Update` 0xCC4908 : si t < 1 : t += pas ; chaque couleur de sommet = courante + (cible - courante) * min(t,1) (**incrémental**, pas un lerp exact depuis le départ) ; calage sur la cible à t >= 1.
* Appelants : `NativeManager.cmd_back_color` 0xD14F44 (paquet 8 : 6 flottants, alpha 1, images 0 = **immédiat**), `cmd_fld_load` 0xD12060, `Make_MonsterEncyclopedia` 0xCF234C.
* Trace du titre : paquet 8 = six 0,0 -> **fond noir**.

### 6.2 Réécriture
Un rectangle plein écran derrière tout, dégradé vertical haut/bas (deux couleurs) ; paquet 8 le règle immédiatement ; sans paquet : noir. (Le dépôt gère déjà `back_color` ; vérifier seulement le noir du titre.)

### 6.3 Fade (paquet 9) : voir section 0 pour le décodage. Plan noir, rampes linéaires en images (30 Hz). Établi pour le décodage des bits, Supposé pour l'ordre fondu sortant -> entrant à l'image suivante (au démarrage : paquet 9 `[4126]` à l'image 0 puis `[30]` à l'image 1 : l'écran commence noir et apparaît en ~1 s).

---------------------------------------------------------------------------------------------------

## 7. Résumé : ce que Unity fait réellement avant le titre
Boot (logos) -> `dq4sp` -> `MainLoop` (initialisations, aucune image à l'écran sauf noir) -> le moteur pilote tout. **Il n'existe aucun écran « titre » dessiné par Unity en dehors de `TapToStart` + copyright** (section 8) ; le logo 3D du titre, le fond et la musique viennent du moteur (paquets 0, 21, 31, 11, 10, 37).

---------------------------------------------------------------------------------------------------

## 8. Titre : « Touchez l'écran » (`TapToStart`, type 73) et séquence moteur

### 8.1 Séquence observée du moteur (Établi, `/tmp/specs/work/t2_e.log`, `trace_titre_1000.log`)
| Image | Paquets / messages moteur |
|---|---|
| #0 (partie 0xC TownPart) | paquet 9 `[4126]` (sortie noir 30 im.) ; création des ports 1..11 (port 1 catégorie 2 = message ; ports 2-11 catégorie 1 types 1,2,3,4,5,6,8,9,10,11 : « Oui/Non », « Objets / Magie / Carac. / Divers »…) = menus de jeu préchargés (invisibles : Supposé) |
| #1 | paquet 0 `[0]` (charge `ev/ev01/out/ev01`) ; paquet 8 noir ; chara/fbx : paquet 31 `[0,1018]` ; paquets 21 `[0,8901]`, `[1,8900]`, `[2,8905]` (mailles du titre) ; paquet 11 `[38]` flottants `[150,10,3.0194]` ; paquet 9 `[30]` (entrée) ; **port 12 créé, type 73** : `[12,1,1,73]`, puis `[1,0,0,0]` (setup) et `[8,1]` (ignoreDraw) |
| #2 | paquet 10 (caméra) `[3]` flottants `[0, 27.7041, -34.1816, 0, 0, -0]` ; BGM : paquet 37 `[16384]`, `[1]` |
| #3 … | **rien, indéfiniment** (1000 images sans entrée : aucun nouvel événement ; le script filtre seulement les paquets 22, 28, 29, 32, 33) : le moteur attend le **pad A** |
| 1er appui A (ex. #40) | paquet 9 `[4126]` (sortie 30 im.) ; **#69 : message port 12 `[12,0,0]` = code 0 = `TapToStart.CountReset`** ; #70 paquet 9 `[30]` (entrée) |
| 2e appui A (ex. #100) | paquet 9 `[4126]`, BGM paquet 37 `[16392]` ; **#131 : partie 0x3 (GameStartPart)** : libération des mailles et fbx (paquets 21 `[0..2,-1]`), fermeture du port 12 ; #132 : ports 12 (type 74), 13 (type 53 = menu du titre), 14 (type 54) |

Interprétation : 1er appui = fin de la phase d'ouverture/démo (fondu + `CountReset`) ; 2e appui = « Touchez l'écran » validé -> fondu + menu du titre. Le **rôle exact de la première phase** (démo de caméra ?) : **Supposé**.

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

## 14. Plan de réécriture concret (ordre conseillé)
1. **Écran de logos** (section 2) avant la création du moteur : 2 images (sqex, arte), alpha linéaire 1 s / 3 s / 1 s, clic = saut. ~40 lignes pyglet ; aucune dépendance moteur.
2. **Machine `TapToStart`** (8.4) branchée sur le type de port 73 + message `[12,0,0]` ; entrée clic/Entrée -> pad A. Vérifier le fond noir (paquet 8) et les fondus (paquet 9 : bit 12 sortie, bit 14 variante).
3. **Menu du titre** (type 53) via l'export `ui_layout.json` déjà géré ; envoyer des **messages de port `[1, idBouton, 16]`** (id 0, 1, 2, 3, 8, 11) et non le pad ; **masquer le bouton id 8 (Sauv. cloud)**.
4. **Type 54** (emplacements) : message `[1, n, 16]` sur le port 14.
5. **Type 55** (nom) : section 12.6 ; **envoyer `[2,len]` + octets dans la même image**.
6. **Licence** (type 80) : fenêtre de texte défilante + bouton Privacy Policy + retour `15: 1,-1,32` (section 11) ; fondu `[20510]` -> `[16414]` déjà géré par le paquet 9.
7. Dialogue de sortie (section 4) : Échap -> confirmation.
8. Tout le reste (Google, OBB, Portail, NetConnection) : ne rien faire.

---------------------------------------------------------------------------------------------------

## 15. Inconnues (non établi, à ne pas inventer)
* Route exacte toucher -> pad (`TouchPad`) ; l'effet du **1er** appui A (rôle de la première phase du titre).
* Qui met `ApplicationQuit.s_quitStatus = 1` (Retour Android supposé).
* Valeurs inutilisées `c_skipBias`, `c_bias`.
* `InputName` : origine de la grille, boutons de fonction, `SetMode`, confirmation finale après le nom.
* Fenêtre `Make_License` (positions/tailles réelles), détails de `LicenseNobu`.
* `NetConnection` : réponses des coroutines et conditions d'ouverture côté moteur.
* Rendu 3D du titre (id 8900/8901/8905 -> objets, shader, signification des paquets BGM 16384/16392).
* Cadence réelle d'Unity (30 Hz supposé).
* Numérotation du pivot `MeshMaker.Build` (4 = centre déduit).
* Rôle exact du bit 14 du paquet 9 (fondu qui laisse l'UI visible : supposé).

---------------------------------------------------------------------------------------------------

## 16. Scripts et fichiers (reproductibles)
* `/tmp/specs/scripts/` : `da.py`, `da2.py`, `fn.py` (désassemble par nom, `LIST=1`), `xref.py` (appelants), `dr.py RVA [FIN]`, `ref_slot.py`, `consts_flt.py FICHIER [DEB [FIN]]` (constantes flottantes + appels d'un dump), `shaders.py`, `shaders2.py`, `boot_scene.py` (level0 + sharedassets0, décodage du MonoBehaviour Boot), `inputname_sets.py` (cctor InputName sous Unicorn, **sans `-I`**), `metastr.py`, `show_ui.py LOG [DEPUIS]` (décodage des traces, masque `[5,0]`/`[6,0]`), `trace_titre.py`, `trace_titre2.py` (`SCRIPT_MSG='image:port:a,b,c;…'`, `SCRIPT_PAD='image:masque,…'` ; plusieurs messages à la même image sont envoyés dans l'ordre). Dumps `_*.txt` (Boot, MainLoop, BackColor, TapToStart, InputName, Net, Make_*).
* Environnement des outils du dépôt : `DQ_IL2=/home/claude/il2` et `DQ_META=/tmp/specs/work/base_extract/assets/bin/Data/Managed/Metadata/global-metadata.dat` (sans `DQ_META`, `runall2.make()` échoue : `FileNotFoundError global-metadata.dat`).
* Traces : `/tmp/specs/work/t2_e.log` (ouverture + titre), `t2_g/h/i/j.log` (nouvelle partie, nom), `t2_k.log` (essai id 6 : sans effet), `t2_l11.log` (Licence), `t2_l8.log` (Sauv. cloud), `t2_m.log` (Licence + retour), `trace_titre_1000.log` (1000 images sans entrée).
* Table type -> Make : `/tmp/specs/work/type_to_make.txt`. Jeux de caractères : `/tmp/specs/work/inputname_sets.json`. Mise en page de référence : un `ui_layout.json` généré (ex. `/tmp/uicache/ui_layout.json`, types 53, 54, 55).
* Images : `/tmp/specs/img/` (préfixes `boot_*`, `title_*`, `dssatex_*`, `tex_*` : les miens ; les autres appartiennent à d'autres agents).
