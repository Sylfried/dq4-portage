## Agent aebaa615370b7f262 — 01/11 16:44

Audit terminé. Livrable : /tmp/specs/audit_menus_pave.md (par élément, établi/supposé séparés, liste de corrections par priorité en section 7). Scripts : /tmp/specs/scripts/audit_reproduire.sh (régénère les listings dans /tmp/r4_repro/), audit_values.py (recalcule tous les nombres), audit_dis.py, audit_eng.py, audit_scan_itemparam.py, audit_pad_meshes.py. Dépôt non modifié.

Conclusions établies (RVA et preuves dans le document) :

1. TouchPad : c_PadScaleTBL = (1.225, 1, 0.775), pas 1.25/1/0.75. Anneau = 256 x 0.63 x sc = 161.28 de diamètre (portage 165). Pastilles centrées à 104/256 = 0.406 du diamètre (portage 0.332 : faux). Zone morte 0.124 R (portage 0.15), course de la boule 0.4526 R (portage 0.5), prise par collider de 1.178 R. Le fondu à 40 % après 0.5 s est inventé : MOVE_WAIT_TIME et MOVE_LIMIT_ALPHA sont des constantes mortes. Boule orange et halo seulement au clignotement tutoriel, pas pendant le déplacement. Les 8 secteurs de 45° sont fidèles. Défaut du jeu : g_pad_pos = 1 (croix au centre, boutons à droite). Anneau flottant non établi : seule la boule suit le doigt.

2. Boutons HUD : icônes (3, 4, 15) et touches (0x1000, 0x800, 0x400) fidèles ; plaques d'origine 72x64 (Carte, Commandes) et 63x56.8 (Discussion), non carrées ; plaque 9-tranches de la feuille Button (le portage utilise un dégradé choisi à l'œil).

3. ItemNumCTRL (type 9) : compteur passif à deux chiffres. Changer(v) : v < 2 donne deux cases vides, sinon dizaines et unités. Le portage l'ignore, donc les quantités ne s'affichent jamais. Règle exacte dans le document.

4. ICityMap (type 25) : lieux et voile fidèles. Écarts mineurs : plan x -223..222.5, z 398..63.875 (échelle 0.99) et marqueur (≤ 2.5 unités). Le code 4 (croix rouge, feuille 5 case 3) est absent. ui_menu.py:187 contient une NameError latente (variable s non définie).

5. Mode de la carte : bug du pipeline dans tools/ui_il2cpp/layout.py:99. CreateMenuPortItem (0xCE43DC, `sub w2, w21, w0`) passe type moins le premier indice du délégué, mais le script passe le type brut. Le type 22 est donc exporté avec un seul bouton. Original : bouton Mode dans la fenêtre à (187.5, -300), plaque 64x55.5, icône donnée par le moteur (19 petite carte, 20 grande carte, 2 ville). Le HUD du portage fixe l'icône à 19. Les groupes 13-17, 35-37, 58/59, 60/61, 75/76 sont probablement touchés aussi (à vérifier).

6. PortalButton : écran titre uniquement, sans objet pour le HUD.

Priorités : (1) layout.py:99 puis régénération ; (2) ItemNumCTRL ; (3) constantes de la croix ; (4) boule et halo ; (5) retirer ou assumer le fondu ; (6) icône et position du bouton Mode ; (7) plan et marqueur ; (8) code 4 ; (9) NameError ; (10) vraies plaques.

À mémoriser (source : cet audit) : le bug de layout.py:99 ; g_pad_pos par défaut 1 ; les boutons à gauche sont un choix de Sylfried (retour #36), pas une erreur ; les docs notes-visionneuse:300, 305 et notes-technique:87 sont à mettre à jour.

---

## Agent ad6ee147e8091d8ae — 01/11 16:45

Spec écrite : /tmp/specs/unity_avant_partie.md (16 sections, chaque valeur marquée Établi / Supposé / Non trouvé, avec RVA ou trace). PNG dans /tmp/specs/img/ (boot_*, title_*, dssatex_*), scripts dans /tmp/specs/scripts/ (dont consts_flt.py, trace_titre2.py), traces dans /tmp/specs/work/t2_*.log.

Conclusions clés
- Unity ne dessine avant la partie que : 2 logos (sqex, arte ; « warning » seulement en JA), BackColor, Fade, et TapToStart + copyright. Le reste (titre 3D, BGM, menus) vient du moteur.
- Logos : carré 450x450 centré (texture 720x720), alpha linéaire 1 s / 3 s / 1 s (temps réel), clic = saut. Établi.
- TapToStart (type 73) : quad 223,04x41,48 centré à 228 sous le centre ; copyright 450x40 à 25 au-dessus du bas. Clignotement par triangle (±0,025/image, paliers de 20 images, période 120 images), premier affichage à l'image 720 sauf message `[12,0,0]` (CountReset), qui le lance tout de suite et fixe le copyright à alpha 1. Sans entrée, le moteur attend indéfiniment le pad A. 1er A = fondu 4126 + CountReset + fondu 30. 2e A = fondu + partie 3, menu du titre (type 53).
- Menu du titre : la sélection se fait par message `[1,idBouton,16]` sur le port 13, jamais par le pad. Ids : 0, 1, 2, 3, 8 (Sauv. cloud), 11 (Licence). Nouvelle partie : `13:1,2,16`, puis `14:1,0,16`, puis type 55.
- Licence (id 11) : fondu 20510, puis port 15 type 80 ; retour par `15:1,-1,32` (fondu 16414). Établi par trace.
- Sauv. cloud (id 8) : le moteur ferme les menus, crée un port de catégorie 4 (NetConnection) et attend Unity. Sans réponse, l'écran reste bloqué. À masquer sur PC.
- Google, ObbDownloadRes et PortalButton : code mort ou ignorable, prouvé par l'absence d'appelants.
- Saisie du nom : le moteur plante si `[2,len]` et les octets UTF-8 empaquetés ne partent pas à la MÊME image. Recommandation : zone de texte PC, pas de clavier 5x7.
- Pas de bouton en trop à ajouter : la config « Fade bit 14 » est décodée (0x4000 = variante).

Inconnues
- Route toucher vers pad, et rôle de la 1re phase du titre.
- Qui met `ApplicationQuit.s_quitStatus = 1` (Retour Android supposé).
- InputName : origine de la grille, boutons de fonction, SetMode, confirmation finale.
- Fenêtre Make_License (positions) et LicenseNobu en détail.
- Réponses NetConnection.
- Rendu 3D du titre (ids 8900/8901/8905, paquets BGM).
- 30 Hz supposé.

À retenir pour la mémoire (source : cette mission)
- `runall2.make()` exige `DQ_META=/tmp/specs/work/base_extract/assets/bin/Data/Managed/Metadata/global-metadata.dat` en plus de `DQ_IL2`.
- Le moteur plante si le nom est envoyé en deux images.
- Table type vers Make : /tmp/specs/work/type_to_make.txt.

---

## Agent a85a7118884ad1696 — 01/11 17:15

P1 à P5 et le bug `s` sont faits, en 6 commits sur `audit-interface` dans `/home/claude/wt-audit` (base 752c7fd). Rien n'est poussé, aucune PR, `dq4-portage` n'a pas été touché.

**Commits** : faf7162 (bug `s`), a5d40c6 (P1 église), b3e4ed9 (P2), be149e1 (P3), 4071160 (P4), e6ac6b2 (P5). Chaque commit compile.

**Fichiers touchés** : `dq4_pc/ui_menu.py` (+165/-8) et `dq4_pc/fenetre.py` (appel de `ui_g.tick()` après `mo.step`, et `_ui_x_monstres(liste)`). Aucun identifiant de nœud n'est codé en dur.

**Vérifié**
- **P1** : moteur réel dans l'église (sauvegarde 1). Clic souris et clavier envoient le bon bouton sur les 5 boutons.
- **P2** : combat réel sur `btl_pl_d` : la secousse (8 images) et le rouge en fin de secousse sont corrects. Le clignotement fait environ 0,7 s.
- **Flèche** : elle n'était jamais affichée avant (le SetActive(true) manquait, confirmé au désassemblage). Elle apparaît maintenant sur le type 29, id 5 uniquement.
- **P3** : empoisonné et mort ont bien la tête de mort et la croix rouge dans la liste Résurrection ; l'œil et le jaune sont testés en synthétique.
- **P4** : les marques apparaissent à la sélection de cible et sont effacées ensuite.
- **P5** : « Continuer votre aventure » a maintenant son cadre.
- **Rendus** : les 72 types sont identiques avant/après. Menu, message et Oui/Non sont identiques. En combat, seules la flèche et les marques changent. Captures dans `/tmp/specs/img/`.

**Hypothèses non vérifiées**
- Cadence de secousse à 30 Hz.
- Rouge exactement en fin de secousse.
- Marques à z=-64 en 16:9.
- Sens du code 2 du type 54 et position du bouton retour.
- Survol des boutons d'église et boutique de bout en bout non testés.
- Docs non mises à jour.

**Autre point** : `/home/claude/dq4-portage` a des modifications non commitées par un autre intervenant (`window.py`, `engine.py`, `ui_menu.py`). Un conflit au merge est possible.

**Pour la mémoire**
- Église reproductible via le slot 1.
- `HaveStatusInfo` est à PlayerStatus+0x10, poison = flag 0x16 (+0x198).
- Tests headless : `xvfb-run -a`, variable `DQ4_SRC`, scripts dans `/tmp/specs`.
- Piège : `pgrep -f` dans un moniteur se tue lui-même.

---

## Agent aba9c8fd03df2b6dd — 01/11 17:27

RAPPORT FINAL, branche `audit-pave` (worktree /home/claude/wt-pave, depuis main 752c7fd). Rien poussé, pas de PR, `main` et le Project non touchés, `self.nom_carte = s` (ui_menu.py, `param_int`) laissé pour A9.

COMMITS (français, avec les 2 lignes Co-Authored-By / Claude-Session)
- 39b406a Correctif du layout Unity (A1)
- 6c127c9 ItemNumCTRL (A2)
- d2825f3 Petite carte : plan, plume, croix rouge code 4 (A7, A8)
- 45f0a13 Croix, plaques des boutons, bouton Mode (A3, A4, A5, A6, A10)
- 0275e93 Notes (les deux docs, section datée « Audit de fidélité », sans n° de PR)

CORRIGÉ
- A1 : `layout.py` `export_type` passe `typ - premier rang du délégué dans R.tbl` (preuve 0xCE43DC). `GENERATION = 3` (`header.py`). J'ai aussi changé `launch_dq4.bat` (`gen >= 3`, avant `>= 2`) : sans cela le cache de l'utilisateur n'aurait pas été refait. Nouveau layout dans /tmp/uicache4. Types dont le layout change : 13, 14, 15, 16, 17 (pages du Statut : 1 nœud -> 5, 3, 4, 3, 5 ; l'écran Statut était vide), 22 (gagne le bouton Mode ; nouveau 22 = ancien 23 + Mode), 35, 36, 37 (BattleIM 8 -> 20, 16, 20 nœuds ; la liste Objets du combat était vide), 58 (lignes remontées de 141 unités, interligne 2,46 ; l'ancien 58 était égal au 59), 60 (21 -> 31 nœuds ; l'ancien 60 était égal au 61). Inchangés : 23, 59, 61, 75, 76 et les 69 types à délégué unique. Aucune régression constatée, donc le correctif est gardé pour tous les types.
- A2 : `ui_menu.Fenetre._item_num`, appelée depuis `param_int` pour la classe ItemNumCTRL (règle de la spec). Vérifié par injection de quantités (57, 9, 10, 123 -> « 23 »).
- A3 : constantes de la croix dans `hud_mobile.py` (DIAM_CROIX 161,28 ; ECHELLE_CROIX 1,225/1/0,775 ; RAYON_PASTILLE 104/256 ; ZONE_MORTE 0,124 ; COURSE_BOULE 0,4526 ; PRISE_CROIX 1,178).
- A4 : plus de boule ni de halo orange quand on tient la croix ; seule la pastille du secteur tenu est allumée.
- A5 : fondu à 40 % après 0,5 s retiré (`croix_t`, ATTENTE_CROIX, ALPHA_CROIX supprimés). Il était inventé : MOVE_WAIT_TIME et MOVE_LIMIT_ALPHA sont des constantes mortes.
- A6 : bouton Mode = bouton de la fenêtre type 22 (icône 19/20/2 envoyée par le moteur), cliquable à la souris et au clavier (touche M inchangée). Le bouton `mode_carte` du HUD est supprimé. Le HUD est entièrement masqué carte ouverte.
- A7 : plan x -223..222,5, z 398..63,875 (type 25 seulement) ; plume `-223 + 1,740234 px`, `398 - 1,740234 py`.
- A8 : croix rouge du code 4 (feuille 5, case 3, 21,6 unités, `(-227 + lo*1,7578, 402 - hi*1,7578)`, ancrage bas gauche), via `Fenetre.special`.
- A10 : boutons du HUD avec la plaque 9 tranches `Rendu.plaque` (nouveau paramètre `coin=16`), formats 72x64 (Carte, Commandes) et 63x56,8 (Discussion). Le dégradé procédural reste en secours si `Rendu` est indisponible.

NON CORRIGÉ / POURQUOI
- A9 (`s` non défini) : réservé à l'autre agent.
- Grande carte (type 26) : position d'origine non lue, ancien rectangle (-225..225) conservé.
- Position par défaut des boutons et de la croix, option `g_pad_pos`, barre de rotation de la caméra, bouton PadPos : non touchés (choix de l'utilisateur en #36, ou sans objet sur PC).

VÉRIFIÉ PAR CAPTURE (xvfb)
- Statut avant/après : /tmp/pave_st_old_b150.png (vide) et /tmp/pave_st_new_b150.png (rempli) ; pages 2 à 4 : /tmp/pave_stp_b190.png, b230.png, b270.png.
- Combat, Objets : /tmp/pave_cbi_uicache3_b290.png (vide) et /tmp/pave_cbi_uicache4_b290.png (4 boutons).
- Quantités injectées : /tmp/pave_qte_b130.png.
- Carte avec Mode + Retour : /tmp/pave_mp_b95.png, b150.png. Clic sur Mode puis fermeture : /tmp/pave_mc_b100.png, b150.png, b230.png, b310.png.
- Croix rouge du code 4 (injectée) : /tmp/pave_c4_b150.png.
- Croix au repos et tenue : /tmp/pave_hud_b90.png et b130.png. Éditeur d'interface : /tmp/pave_edit_b90.png.
- Menus simples sans `ui_layout.json` : /tmp/pave_simple_b90.png, b130.png, b190.png. Dernier contrôle sur HEAD avec le cache gen 3 : /tmp/pave_fin_b90.png (le jeu démarre).
- pyflakes : jeu de warnings identique à main sur les 5 fichiers .py touchés (aucun nouveau).
- Les captures sont celles d'une galerie de fenêtres vides pour 58/60/75/76 et 14 à 17, 36, 37 ; pas de rendu en situation.

CE QUI RESTE « NON VÉRIFIÉ » (PC Windows de Sylfried / hors portée)
- Rendu OpenGL réel (mes captures viennent de Mesa sous xvfb) et régénération du cache par `launch_dq4.bat` (gen 3, quelques minutes, une fois).
- Boutiques (types 58 et 60) : aucune sauvegarde de test n'y mène.
- Les autres groupes de types touchés par A1 sont supposés se lire comme `Make_MapButton`, seul lu ligne à ligne ; les captures n'ont montré aucune régression.
- Ancrage bas gauche de la croix rouge (supposé par analogie avec la plume), shader SmallMapSymbol, jamais reçu dans les sauvegardes de test.
- Absence d'anneau flottant et de fondu : établie pour le code C# de TouchPad, pas pour une animation extérieure ; aucune capture Android disponible.
- Le moteur envoie 0 comme quantité pour toutes les lignes de la sauvegarde de test (objets non empilés) : le rendu réel des quantités n'a été vu qu'en injection.
- Menus simples (sans `ui_layout.json`) : la fenêtre de carte n'est pas dessinée (comme avant), donc plus de bouton Mode à l'écran dans ce mode ; la touche M reste.

FICHIERS / FONCTIONS TOUCHÉS (pour la fusion avec `audit-interface`)
- `tools/ui_il2cpp/layout.py` (`export_type`), `tools/ui_il2cpp/header.py` (GENERATION), `dq4_pc/launch_dq4.bat` (test de `gen`).
- `dq4_pc/ui_menu.py` : `Fenetre.__init__` (+ `self.special`), `Fenetre.param_int` (1 ligne ItemNumCTRL, juste après la ligne ICityMap `self.nom_carte = s` intacte), nouvelle `Fenetre._item_num`, `Rendu.plaque` (param `coin`), `Rendu._carte` (rectangle type 25 + croix rouge).
- `dq4_pc/fenetre.py` : `on_mouse_press` (fenêtre type 22, boutons 0x400 et 2), `on_mouse_release` (branche `mode_carte` retirée, bouton pad 2 -> `carte_bascule`), `_plan_fenetre` (code 4 + position de la plume).
- `dq4_pc/hud_mobile.py` : constantes, `echelle/taille/dims/rect`, `visibles`, `_plaque`, `_croix` (import `time` retiré).
- `docs/viewer-notes-dq4-pc.md` et `docs/technical-notes-dq4-port.md` : passages corrigés (GENERATION, lacunes, plume, croix, plaques) + nouvelle section « Audit de fidélité » à la fin de chacun.
- Points de friction probables avec `audit-interface` : `ui_menu.py` (`param_int`, `Rendu.plaque`, `Rendu._carte`) et `window.py` (`on_mouse_press` / `on_mouse_release`, `_plan_fenetre`).

À SAVOIR (méthode)
- J'ai dû défaire un premier commit ItemNumCTRL (371e588) mal découpé : `git apply --unidiff-zero` avait posé les lignes au mauvais endroit. Il a été annulé avant tout autre commit ; l'historique actuel est propre et chaque commit compile (py_compile).

---

## Agent a9a69c9aad072e46d — 01/11 18:44

Rapport camera-bip : la caméra est corrigée, le bip est normal et je n'ai rien changé côté son. Un commit sur la branche `camera-bip` : 75eae46, rien poussé, `docs/` et README intacts.

**1. Caméra : corrigé et vérifié**
- **Nouveau critère** : le verrou de la `TownCamera` du moteur (+0x3e), lu par `Moteur.camera_jeu()`. L'option « centrer sur le joueur » ne s'applique que si ce verrou est à 0.
- **Rejeté** : le drapeau « joueur verrouillé » (`Global.Flag` bit 0x4), car il est posé pendant tous les messages alors que la caméra suit le héros. L'ancien critère (cible à moins de 60 unités du héros) échouait aussi : dans le prologue la cible n'est qu'à 23 unités, donc la salle apparaissait au lieu de l'écran noir « Prologue ».
- **Pendant un événement** : la caméra du jeu s'applique telle quelle, avec les bornes 16/9 de la visionneuse, comme option désactivée.
- **Transition** : l'ancien lissage est conservé. Si la cible saute (changement de carte, coupure de plan, seuil 1,5 unité par pas), le centrage suit aussitôt, sans glissement.
- **Vérifié par captures** :
  - Prologue (slot 2, `mlb1a`, verrou à 1 jusqu'à la capture ~368) : option activée identique au pixel à option désactivée. Après libération, la caméra se centre sur le héros.
  - Exploration libre église → porte → `maout` (5 captures, changement de carte compris) : identique au pixel à l'ancien code.
  - Message de PNJ à l'église (3 captures) : identique au pixel.
  - Le verrou reste à 0 pendant les jarres et tonneaux (sonde du moteur sans fenêtre), donc le centrage reste actif.
  - `pyflakes` : seul l'ancien avertissement `sel` (ligne ~1700).

**1bis. Partiel ou non vérifié**
- Jarre ou coffre avec message : seulement dans la sonde du moteur sans fenêtre, pas en capture. Le prologue n'étant pas rejouable par touches, je n'ai pas pu casser une jarre dans la visionneuse. Le message de PNJ passe, lui, en capture.
- Je n'ai pas pu voir une scène à caméra visible avec le héros près d'un bord de carte.
- Je n'ai pas vérifié l'entrée dans le verrou par un déplacement lent (seulement des coupures et une simulation), ni les chutes et sorts de retour.
- **Mon choix** : les bornes 16/9 restent appliquées pendant les scènes.

**2. Bip : normal, commandé par le moteur**
- C'est le bruitage 300 (paquet 35), joué par le moteur au début d'un message quand le joueur vient de reprendre la main. C'est le même que celui du passage de page.
- Mécanisme : `ui_MsgLoop` (0x157044) joue le 300 une seule fois, puis efface l'octet `ui_MsgBeginTalkSE` (lib+0x252388). Cet octet est réarmé quand le joueur est libéré (`PlayerManager::setLock(false)`).
- Trace d'une jarre avec message : jarre brisée (319, ou 320 pour un tonneau), icône de l'objet (326), ouverture du message, puis le 300. Les jarres sans objet n'ont ni message ni bip.
- La visionneuse joue un seul son par paquet, avec le bon fichier (`SE0300`), et n'ajoute rien à l'ouverture d'un message. Pas de double lecture.
- Non comparé au jeu Android : le volume réel (`vol_b × volume du fichier` ici).

**Fichiers touchés**
- `dq4_pc/fenetre.py`
- `dq4_pc/moteur.py`
- `/tmp/specs/camera_bip.md` : adresses, traces, établi / supposé / inconnu.

**À signaler**
- Deux points hors périmètre, non touchés, et le second concerne l'agent des écrans titre / prologue :
  - Les touches clavier des boutons d'écran (Entrée = Commandes, Espace = Discussion, M = Carte) ne jouent pas le 300, alors que le clic souris le joue.
  - Dans le prologue, l'attente de touche (`cmd_key_wait_type_b`) ne reçoit jamais A brut : Espace devient `BTN_PAROLE` et A / B sont retirés de la manette. Cela bloque les tests automatisés.
- À mémoriser : `Moteur.camera_jeu()` donne (verrou +0x3e, mode +0x48, verrou de point de vue +0x40, déplacement +0x43). Valeur du prologue : (1, 5, 0, 0) ; état libre : (0, 0, 0, 0).
- Un autre agent tourne encore (« Prologue : encadrés de chapitre… »). Aucun xvfb n'était actif quand j'ai lancé mes captures.

---
