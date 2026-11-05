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
| Passage unités de conception -> pixels visionneuse | `Fenetre._ui_repere()` (window.py ~1205) renvoie (x centre, y centre, px par unité) = `(width/2, height/2, height/800*ui_k)`. Un point (x, z) de conception relatif au centre d'écran = pixel `(cx + x*ech, cy + z*ech)` (pyglet : y vers le haut) | Établi (code du dépôt) |
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
