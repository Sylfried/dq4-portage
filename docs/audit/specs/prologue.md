# Dragon Quest IV (Android) : l'ouverture du prologue et la boîte violette du choix de sauvegarde

Suite de `/tmp/specs/moteur_avant_partie.md` (§5.4, « Ouverture observée sur mlb1a »). Deux retours de Sylfried :

1. « il y a des encadrés au début d'un chapitre qui apparaissent sur fond noir, et au début du prologue une animation (des coups d'épée) avant que le vrai jeu se lance : je n'ai rien eu de tout ça » (sa capture : le mot « Prologue » en blanc sur la scène) ;
2. une boîte violette apparaît entre le choix de la sauvegarde et la saisie du nom (comme celle de la fin de combat).

Branche `prologue` (depuis `main` d381c1d), répertoire de travail `/home/claude/wt-prologue`. Rien n'a été poussé, `docs/` et le README n'ont pas été touchés.

Conventions : RVA = adresses de `libil2cpp.so` (octet fichier = RVA − 0x4000), adresses du moteur = vaddr de `libdq4core.so`. « **Établi** » = lu dans le code ou observé dans une trace ; « **Supposé** » = déduit ; « **Inconnu** » = non vérifié. Les numéros d'image sont ceux du moteur (premier champ de `DQ_PKTALL`, identiques aux `MSG image N` de `DQ_UIDBG`).

---

## 1. Résumé

1. Le prologue enchaîne quatre choses : un titre de chapitre (bandeau doré à fond bleu portant « Prologue », sur écran noir), une attente noire, des coups d'épée (modèles `5303` / `5311` + bruitages `412`, `416`, `403`) vus par une caméra qui regarde le vide, puis un travelling qui ramène la caméra sur le héros et révèle la salle. Il se termine sur `cmd_key_wait_type_b` (attend un appui) puis le message « Eh bien alors, [nom] ? ».
2. Le portage perdait trois éléments : (a) **un seul plan de fondu** dessiné *derrière* les fenêtres, alors que le moteur en pilote **deux** (bit 14 du paquet 9) ; (b) la **texture du bandeau** (`Menu/map/hyodai1`, créée par code, absente de l'export de mise en page) ; (c) les coups d'épée étaient hors de l'écran à cause du recentrage de la caméra sur le héros (option « centrer la caméra », corrigé par l'agent caméra, commit `75eae46`, fusionné dans `retours-18h02`).
3. La boîte violette est un **message reçu après la fermeture** d'une fenêtre : `[N, 2]` détruit le port côté Unity, les messages qui suivent dans la même image n'ont plus de destinataire ; le portage les appliquait à la fenêtre fermée qui revivait une image en « fenêtre simple ». Corrigé (`Interface.appliquer`), vérifié image par image sur les transitions voisines.
4. **Correction d'une note du dépôt** : `docs/notes-technique-portage-dq4.md` et le commentaire de `moteur.py` disaient « bit 14 = plan devant l'interface » ; la lecture d'IL2CPP donne l'inverse (§3).
5. L'appui qui termine l'attente de touche n'est **pas** bloqué par `tick` : `cmd_key_wait_type_b::isEnd` lit le 2ᵉ argument de `GameUpdate` (`decl`), n'importe quelle valeur non nulle convient, `BTN_PAROLE` (Espace) en est une (§6).

---

## 2. Ce que le moteur envoie (journal `DQ_PKTALL`, paquets 22 / 28 / 29 exclus)

Scénario : Nouveau jeu → emplacement 3 → nom « Sylfried » → sexe masculin (mêmes clics que `moteur_avant_partie.md`). Deux relevés : réglage « vitesse des transitions » = 2 (valeur par défaut du portage : les fondus au noir sont raccourcis de moitié, **le moteur attend la fin du fondu** par le bit 0 du mot d'état, donc sa propre chronologie change) et = 1 (durées d'origine, colonne « d'origine »).

| Image (vitesse 2) | Image (d'origine) | Paquet | Sens |
|---|---|---|---|
| 1236 | 1236 | `9 [4126]` = 0x101E | plan de devant, sortie, 30 images (fondu au noir de la création du journal) |
| 1253 | 1268 | `0 [0]` (chargement de la carte `mlb1a`), `8`, `12`, `7 ×4`, `16`, `33 [1.25, 0.65, 0.75]`, `12 [8,19]`, `12 [9,7]`, `14`, `9 [30]` | carte chargée, plan de devant en entrée 30 |
| 1254 | 1269 | `9 [20481]` = 0x5001 | **plan de fond**, sortie, 1 image : fond noir immédiat |
| 1254 | 1269 | `10 [3] [1.08, 28.938, −30.159 → 1.08, 0, −3.2]` | caméra sur le héros |
| 1255 | 1270 | `10 [3] [0, 28.938, −6.959 → 0, 0, 20]` | caméra **dans le vide** (le héros sort du champ) |
| 1268 | 1283 | `9 [4097]` = 0x1001 ; message `[12, 1, 1, 12]` (port 12, type 12) | plan de devant noir immédiat ; création du bandeau |
| 1270 | 1285 | `9 [60]` | plan de devant en entrée 60 : le bandeau apparaît |
| 1362 | 1407 | `9 [4141]` = 0x102D | plan de devant, sortie 45 : le bandeau s'efface |
| 1386 | 1454 | `9 [30]` ; `[12, 2]` à 1402 (vitesse 2) | entrée 30 (écran toujours noir par le fond) ; bandeau fermé |
| 1416 | 1499 | `9 [16429]` = 0x402D | **plan de fond** en entrée 45 (le fond redevient transparent) |
| 1460 | 1543 | `21 [0, 5303]`, `35 [412]` ; `21 [0, −1]` 10 images plus tard | coup d'épée 1 (traînée), bruitage 412 |
| 1474 | 1557 | `21 [0, 5311]`, `35 [416]` ; fin 11 images plus tard | coup 2 (éclat), bruitage 416 |
| 1503 | 1586 | `21 [0, 5303]`, `35 [412]` | coup 3 |
| 1517 / 1526 | 1600 / 1609 | `21 [0, 5311]` puis `21 [1, 5311]` (emplacement 1), `35 [416]` ×2 | coup 4 (deux éclats superposés) |
| 1555 | 1638 | `21 [0, 5311]`, `35 [403]` | coup 5 (dernier, bruitage 403) |
| 1599 | 1682 | `9 [20483]` = 0x5003 | plan de fond, sortie 3 : noir juste avant le travelling |
| 1603 → 1613 | 1686 → 1696 | `10 [3]` ×10 : position x de 0 à 1,08, z de −6,959 à −30,159 (pas 0,108 / −2,32), `13 [2048] [0,748 … 1,0]` | travelling vers le héros |
| 1612 | 1695 | `9 [16429]` | plan de fond en entrée 45 : la salle apparaît |
| (appui) | 1902 (Espace à 1900) | `16 [512]`, `35 [304]` (bip d'ouverture) | fin de `cmd_key_wait_type_b`, message « Eh bien alors, … » |

Messages du port 12 (type 12) : `[1, 0, 0, 0]` (mise en place), `[11, 0, 1]` + texte `[80, 114, 111, 108, 111, 103, 117, 101]` = « Prologue » en UTF-8 (un octet par short) + `[11, 0, 0]` + `[]` (deuxième texte, vide), puis `[5, 0]` à chaque image ; fermeture par `[12, 2]` sur le port 0. Pendant le bandeau, les ports 13 à 15 (types 53 / 54 / 55, menu de départ) sont cachés ou fermés (`(cache)` dans `DQ_UIDBG`).

Côté moteur : `cmd_event_chapter_title` (0x21a708) → `__cmd_event_chapter_title::initialize` (0x21b330 : copie les 8 octets de paramètre dans `MaterielMenu_WINDOW_MANAGER + 8`, `openMaterielWindow(0x19)`, puis `CommonChapterTitle::setup`, sauf si les deux entiers du paramètre valent (0, 1)) ; `isEnd` (0x21b388) attend que l'octet `+0x18` du gestionnaire retombe, puis `CommonChapterTitle::cleanup`. **Établi** : cette séquence se déroule sur `mlb1a` à chaque nouveau journal. **Inconnu** : la valeur exacte du paramètre du prologue.

---

## 3. Les deux plans de fondu (`Fade`, lecture d'IL2CPP)

### 3.1 Établi

- `NativeManager.cmd_fade` (0xD14C70) : `Fade.l_targetLayer = (v >> 14) & 1` (0xD14D10), puis `SetFadeIn` (0xCCBB08) ou `SetFadeOutBlack` / `White` / `Color` selon le bit 12 ; durée = `v & 0x7ff` ; couleur = bits 11 / 13. Constantes `Fade.IN = 4`, `Fade.OUT = 8`, `bgLayerNo = 0`, `frontLayerNo = 8`.
- `Fade.Start` (0xCD0B7C) crée deux `Fade.FadePlane` dans `Fade.l_fade` : indice 0 nommé « **FadeForMenu** » (shader `Custom/FrontFade`), indice 1 nommé « **FadeForBG** » (shader `Custom/BackFade`). Les deux sont des enfants du transform d'un statique de `TouchPad`. Couleur initiale (0, 0, 0, 1), objet **inactif** à la création (fin du constructeur 0xCD07D4 : `SetActive(false)`).
- Shaders (lus dans `datapack.unity3d`, `m_Tags`) : `FrontFade` file **Overlay**, `BackFade` file **Background** ; tous deux ZTest Always, ZWrite off.
- `FadePlane.Command(cmd, frame, color)` (0xCCFFB0) : mémorise la couleur, lit l'opacité courante du matériau ; si `frame >= 1` : entrée = opacité visée 0, pas −a / frame ; sortie = opacité visée 1, pas (1 − a) / frame ; `count = frame`, `SetActive(true)`. Si `frame < 1` : entrée = opacité 0 et `SetActive(false)` ; sortie = opacité 1 et `SetActive(true)`.
- `FadePlane.Update` (0xCD0618) : si `count >= 1` (et le drapeau de pause global levé), `count--` ; à 0 l'opacité prend la valeur visée (objet désactivé si elle est nulle), sinon `+= pas`.
- `Fade.IsEnd` (0xCC419C) : vrai quand le `count` des **deux** plans est < 1 ; c'est lui qui fait retomber le bit 0 du mot d'état (la poignée de main que le moteur attend : `Global::IsFadeEnd`).
- `FadePlane.SetPriority(shaderNo)` (0xCD03FC) change le shader du plan ; `Fade.SetFadePriority(layer, priority)` (0xCD036C) n'est appelé que par `MenuMessage.SetCanvasMesh` (0xCFA6F8). Non reproduit, non déclenché par le prologue.

### 3.2 Conséquence et correction de la note du dépôt

Le plan 0 (bit 14 = 0) est dessiné dans la file Overlay : **devant tout, fenêtres et messages compris**. Le plan 1 (bit 14 = 1) est dans la file Background de la caméra qui porte aussi l'interface : **devant la scène, derrière les fenêtres**. La note « bit 14 = plan devant l'interface » (`docs/notes-technique-portage-dq4.md`, commentaire de `Etat._fondu`) était donc inversée ; en revanche la note sur l'écran Licence (« `[20510]` : bit 14, l'interface reste visible ») était juste. Le portage dessinait un seul plan, derrière les fenêtres, quel que soit le bit.

Valeurs vues : `4126` = 0x101E (devant, sortie 30), `30` (devant, entrée 30), `20481` = 0x5001 et `20483` (fond, sortie 1 / 3), `16429` = 0x402D (fond, entrée 45), `16387` = 0x4003 (fond, entrée 3, début de combat), `20510` = 0x501E (fond, sortie 30 : licence et mort du héros).

### 3.3 Supposé / inconnu

- **Supposé** : la caméra qui porte les deux plans est celle de l'interface (parent = transform du `TouchPad`), d'où « le fond passe devant la scène ». Cohérent avec la trace (le fondu d'entrée de 45 images du plan de fond *révèle* la salle) et avec la note de la Licence ; non confirmé par la scène Unity (non exportée).
- **Inconnu** : le fondu d'entrée d'Unity part de l'opacité *courante* du plan ; le portage repart toujours de 1 (comportement existant, conservé : il compense les fondus que Unity lance lui-même au changement de scène et que le portage ne rejoue pas).

---

## 4. Le titre de chapitre (type 12, `Make_Chapter`)

- `MenuPortItemTable.Make_Chapter` (0xCE4404), code `<Make_Chapter>b__0(short code)` (0xD0ABEC). Éléments exportés : un quad (noeud 1508, rien d'attaché) et deux textes centrés (noeuds 1532 et 1558 : y = 1, z = 30 et 17,5, taille de caractère 11,05).
- Le quad est `MenuParts.CreateFromTexture("Menu/map/hyodai1", bFitWidth = true, haspect = 1)` (0xD02764) : l'exporteur n'en voit que le maillage par défaut (carré de 450) et pas de matériau. Texture `hyodai1` : 256 × 128, RGB24, dans `datapack.unity3d` (`/tmp/specs/img/prologue_tex_hyodai1.png`) : cadre doré à fond bleu marbré.
- Le fond **noir** n'appartient pas au bandeau : c'est le plan de fond (`20481`) et le plan de devant qui couvrent la scène.
- **Établi** : nom de la texture, largeur ajustée, deux textes dont le premier porte « Prologue ». **Supposé** : hauteur 225 (450 / 2 d'après le rapport 256 × 128 ; non lue dans le code, le rendu s'accorde au cadre et au texte exportés).
- **Inconnu** : le rôle du code 0 (`fx` : le noeud 1508 est masqué pour la valeur 0 ; le moteur n'envoie aucun code, le bandeau est donc montré) et le deuxième texte (vide pour « Prologue » ; probablement le sous-titre des chapitres suivants, jamais vu ici).

---

## 5. Les coups d'épée

- Ce sont des **effets-maillages de ville** : `21 [emplacement, modèle]` charge / libère le modèle `5303` (traînée) ou `5311` (éclat) sur l'emplacement 0 ou 1 (`−1` = libérer), shader 3 `DssaCharaTransparent`, billboards ; les sommets arrivent par les paquets 22 / 28 / 29. Textures `m5303`, `m5311` déjà dans le cache. Cinq coups, 10 à 11 images chacun (tableau §2), bruitages `412` / `416` / `403`.
- Ils sont dessinés par la branche « ville » existante de `_dessiner_scene`. Ils n'étaient pas visibles parce que `_camera_ville` recentrait la caméra sur le héros (`camera_centree`, `CAM_CENTRE_MAX = 60`) : la caméra du prologue regarde le vide à 20 unités du héros, l'écart est inférieur au seuil, le recentrage ramenait la vue sur le héros. Le verrou d'évènement de la `TownCamera` (+0x3e = 1, mode +0x48 = 5, images 12 à ~368 selon l'agent caméra) est maintenant lu par `cam_jeu` (commit `75eae46`, branche `camera-bip`, déjà dans `retours-18h02`) ; **je n'ai pas touché `_camera_ville`**.
- Tailles à l'écran : 60 à 80 pixels à 720p, autour du centre. **Inconnu** : fidélité de la taille et de la place par rapport à une capture du jeu réel (aucune capture d'origine disponible ; les valeurs viennent des paquets).
- **Non reproduit** : paquet 33 `map_color_rate` [1,25 ; 0,65 ; 0,75] à l'ouverture de `mlb1a` (teinte de la carte ; paquet ignoré par le portage), paquet 34 hors combat.

---

## 6. L'attente de touche (`cmd_key_wait_type_b`) : A / B

- `cmd_key_wait_type_b` (0x21a62c) pose l'octet `+0xe` de `g_HengeNoTsue` ; `__cmd_key_wait_type_b::isEnd` (0x21b324) appelle `CommonCounterInfo::checkBottun` (0x1a2b64) qui renvoie `g_Global + 0xe4 != 0`.
- `GameUpdate(w0, w1)` (0x17e6a8) range `w0` en `g_Global + 0xe0` et `w1` en `+0xe4` : **la fin de l'attente se lit sur le 2ᵉ argument (`decl`), pas sur l'octet de manette**. `tick` retire A / B de la manette sur le terrain (`p &= ~(MO.A | MO.B)`) mais convertit A en `BTN_PAROLE` (0x100) dans `decl`, non nul : l'attente se termine. Entrée (`BTN_MENU`) la termine aussi (et ouvre le menu).
- **Vérifié** (`prologue_attente_touche.png`) : Espace à l'image 1700 → message « Eh bien alors, Sylfried ! Tu en as assez ? » à 1740, Oui / Non à 1760. **Aucune modification de `tick`.** Les captures automatisées qui n'y arrivaient pas n'envoyaient pas de touche à ce moment.

---

## 7. La boîte violette

### 7.1 Cause (établi)

`MenuPortSystem.internalUpdate` (0xD10A54) traite le port 0 en premier, puis les ports 1 à 31. `[N, 2]` appelle `Close()` et met `s_ports[N] = null` ; un message adressé à un port nul est abandonné (`if (item != null) item.NoticeReceive`). Le portage, lui, gardait la fenêtre fermée dans son dictionnaire et lui appliquait les messages suivants : la fin de la liste des journaux (`[5, 0]`, `[6, …]`, `[4, …]`) arrivait **dans la même image que la fermeture** (un port de numéro > 0 est lu après le port 0) et rouvrait la fenêtre une image, sans mise en page d'origine : boîte « simple » violette (`prologue_boite_violette_avant_detail.png`, image 854). Même mécanisme que la boîte de fin de combat.

### 7.2 Correctif

`Interface.appliquer` (`moteur.py`) : une fenêtre marquée `ferme` ignore ses messages (et vide `attente`) jusqu'à sa recréation par `[N, 1, cat, type]`. Commit `152b967`.

### 7.3 Vérifications image par image (xvfb, 1280 × 720, `--touches-test`)

| Transition | Images | Résultat |
|---|---|---|
| choix de la sauvegarde → saisie du nom (clic à 850) | 849 → 860, chaque image | boîte violette à 854 **avant** ; absente **après** (`prologue_boite_violette_avant_apres.png`) |
| emplacement occupé → confirmation (clic @640@525) | 846 → 900 | absente (image 855 vide, puis le message) |
| choix du sexe → « Création du journal » (clic à 1200) | 1196 → 1235, pas de 3 | absente |
| Supprimer : liste → confirmation → Oui → « Journal supprimé » → menu de départ | 846 → 1100 | absente à chaque étape (`prologue_suppression_*.png`) |
| Licence → retour au titre | 1096 → 1600 | le fond se rouvre (le moteur envoie l'entrée) ; menu revenu |

Balayage `DQ_UIDBG` du scénario complet jusqu'au prologue : les seules fenêtres « simples » **visibles** sont les types 73 / 74 (titre, dessinés par le portage lui-même) ; les types 53 / 54 / 55 restent cachés.

---

## 8. Modifications du portage (branche `prologue`)

| Fichier | Changement |
|---|---|
| `dq4_pc/moteur.py` | `Etat.fondu` (plan de devant) + `Etat.fondu_fond` (plan de fond) ; `_fondu` aiguille sur le bit 14 ; `tick_fondu` fait avancer les deux plans (le garde-fou « noir > 6 s » ne s'applique qu'au plan de devant) ; `fondu_en_cours()` (bit 0 du mot d'état = l'un des deux plans, comme `Fade.IsEnd`) ; `__setstate__` pour les anciens états enregistrés ; commentaires corrigés ; **correctif de la boîte violette** (`Interface.appliquer`, commit séparé) |
| `dq4_pc/fenetre.py` | `_dessiner_fondu(fond)` : plan de fond avant les dégâts / messages / fenêtres, plan de devant **après** `_dessiner_menus` (aussi dans la branche « carte pas encore envoyée ») ; chargement de `hyodai1` dans `_init_ui` ; l'astuce de fin de combat (fenêtre de statut masquée quand le noir dépasse 0,6) lit maintenant les deux plans |
| `dq4_pc/ui_menu.py` | `Make_Chapter` : le quad prend la texture `hyodai1` et la taille 450 × 225 |
| `dq4_pc/avant_partie.py` | `RESSOURCES['ap_hyodai1.png']` : extraite une seule fois du `datapack` (3,7 s ; sans UnityPy ou sans APK le bandeau est simplement absent) |

Aucun fichier de patch FR touché.

---

## 9. Régressions (comparaison pixel à pixel avec `d381c1d`, mêmes scénarios)

- `--slot 1`, images 60, 120, 200, 300, 500, 800 (Entrée à 400, Échap à 600) : **identiques au pixel**.
- Combat (`--slot 4`, marche sur la carte du monde, A en combat, images 780 → 1380 tous les 20) : identiques sauf :
  - image 800 (fondu d'entrée du combat) : les fenêtres sont maintenant **sous** le fondu de devant (elles s'assombrissent avec la scène) ;
  - images 1060 → 1180 : le message « Ragnar meurt ! » puis « Une voix sortie de nulle part se fait entendre » **se lisent sur le noir** (le fond `20510` laisse l'interface visible) ; avant, la boîte était masquée par `_boite_fin_combat` ; la fenêtre de statut reste masquée (astuce conservée) ;
  - images 1240 → 1280 et 1320 : le fond reste noir jusqu'à la commande d'entrée du moteur (`16389` à 1318) ; avant, le garde-fou « noir > 6 s » rouvrait la scène en plein texte de la voix.
- Prologue complet (`prologue_sequence_complete_camera_centree.png`, avec le correctif de caméra de `75eae46` appliqué à une copie) : bandeau, coups d'épée, salle ; option « centrer la caméra » activée.
- `python3 -m pyflakes` sur les quatre fichiers modifiés : seuls les 4 avertissements déjà présents sur `d381c1d` (`sel`, `racine`, `em`, `ax`).

---

## 10. Établi / Supposé / Inconnu

**Établi** : la chronologie des paquets (§2) ; les deux plans de fondu, leurs shaders, leur file, leurs règles `Command` / `Update` / `IsEnd` (§3.1) ; la texture et la composition du bandeau ; `isEnd` de l'attente de touche = `decl != 0` ; la cause de la boîte violette et la disparition vérifiée sur cinq transitions ; la reconstitution visuelle du prologue (bandeau sur noir, éclats, salle).

**Supposé** : la caméra porteuse des plans (donc « fond = devant la scène, derrière l'interface ») ; la hauteur 225 du bandeau ; le garde-fou « noir > 6 s » inutile pour le plan de fond (le moteur le rouvre lui-même : vérifié pour la licence, le combat et le prologue, pas pour les autres flux) ; l'astuce « statut masqué » valable aussi quand le noir vient du plan de fond (comportement existant conservé).

**Inconnu / non vérifié** : tailles et places exactes des éclats par rapport au jeu réel ; paquet 33 ; paquet 13 `[2048]` pendant le travelling (valeur 0,748 → 1,0, probablement un taux de couleur du héros) ; `SetFadePriority` ; le deuxième texte du bandeau ; durée de l'extraction de `hyodai1` sous Windows ; comportement avec `vitesse_fondu` ≠ 2 (la durée d'affichage du bandeau en dépend car le moteur attend la fin des fondus).

---

## 11. Fichiers et captures

Captures (`/tmp/specs/img/`) : `prologue_carte_chapitre.png`, `prologue_sequence_titre.png`, `prologue_sequence_epee_piece.png`, `prologue_sequence_complete_camera_centree.png`, `prologue_attente_touche.png`, `prologue_boite_violette_avant_apres.png`, `prologue_boite_violette_avant_detail.png`, `prologue_transition_sexe.png`, `prologue_suppression_confirmation.png`, `prologue_suppression_oui.png`, `prologue_suppression_retour_menu.png`, `prologue_licence_retour.png`, `prologue_combat_avant_apres.png`, `prologue_tex_hyodai1.png`.

Lanceurs : `/tmp/run_t_prologue.sh` (scénario), `/tmp/run_c_prologue.sh` (combat), `/tmp/run_t_base.sh` (copie de `d381c1d` dans `/tmp/base_d381`), `/tmp/sheet.py` (planches). Réglages de test : `/tmp/rg_nc.json` (caméra non centrée), `/tmp/rg_v1.json` (vitesse des transitions 1).
