### 1.3 Où la visionneuse ignore en silence

Établi par `grep` sur `dq4_pc/*.py` : **aucun** `NotImplementedError`, `TODO`, `FIXME`. Les « silences » sont :
- `Etat.appliquer` : pas de branche `else`. Un type inconnu (1, 6, 16, 17, 18, 27, 30, 33) est ignoré sans journal. C'est la source du trou §1.
- `except Exception: pass` : `window.py` ×8 (l.285, 363, 412, 415, 598, 766, 1109, 1115 : changement de mode de fenêtre, fermeture d'un processus, écriture de cache), `sound.py` ×12 (chargement et lecture des sons : un fichier son illisible disparaît sans message), `pause.py` ×4, `saves.py` ×2 (l.130, 144), `saves_screen.py:70`. Le plus gênant pour la jouabilité : `sound.py` (une musique qui n'est pas décodable est un silence sans trace). Non vérifié : combien de BGM échouent en réalité (je n'ai pas lancé le décodeur sur les 686 fichiers).
- `data.py:161` : palette animée ignorée (« ignorée ») ; `data.py:307-355` : modèles 3D non pris en charge (maillage non skinné, autre shader, animation comprimée) → modèle absent de l'écran, message de journal seulement.
- `Moteur.step` lève `RuntimeError('le moteur s est arrete …')` quand Unicorn plante (`engine.py:588`) : c'est le seul cas où l'arrêt est bruyant. Dans le balayage : 1 cas sur 529 (`ev01`, voir §5).

---

## 2. Types MenuPort 1 à 80

Source des classes du moteur : `menutypes3_raw.txt` (nombre d'appels de création par classe, scan statique). Source des noms `Make_*` : `ui_layout.json` (`/tmp/uicache4`). Établi : **tous les types sont exportés** (mise en page extraite du code Unity sous Unicorn) **sauf 73, 77 et 80** (erreur d'export : 73 « Touchez l'écran » et 80 Licence sont lus à la main, `window.py:2706`, `2718`, `pre_game.py` ; 77 = réseau, inutile sur PC). Tous les autres types sont dessinés par le chemin générique de `ui_menu.py` ; les entrées passent par `_saisie_menu` (`window.py:1592`) ou la souris.

Classes `IBase` personnalisées : **les cinq sont prises en charge** (`ui_menu.py:199-204, 229, 250, 347-413, 849`) : `StatusIconChanger` (types 4, 5, 20, 21, 46, 60, 61, 67), `ItemNumCTRL` (9), `ICityMap` (25), `BattleBar` (29), `MonsterMarkList` (31). La ligne « Lacunes : classes IBase personnalisées non reproduites » de `technical-notes-dq4-port.md` (section « Interface d'origine : fenêtres et menus ») est donc **périmée** (à corriger dans les notes).

Colonne « Niveau » :
- **Vu (doc)** : une capture ou une trace documentée existe dans les notes (référence `V` = notes-visionneuse, `T` = notes-technique, avec le numéro de ligne).
- **Vu (moi)** : je l'ai ouvert dans le moteur cette fois-ci.
- **Rendu seul** : mise en page exportée et dessinée par le chemin générique ; aucune trace d'un essai réel dans les notes.
- **Contourné / Absent / Inconnu** : voir la ligne.

| Type | `Make_*` | Classes moteur qui l'ouvrent | Écran de jeu | Traitement visionneuse | Niveau |
|---|---|---|---|---|---|
| 1 | YesNo | `CommonMenu_YESNO` | Oui / Non (toutes les questions) | générique ; suit la fenêtre de message `window.py:2120, 2148` ; curseur moteur (grille) | Vu (doc V18, V161, V251) |
| 2 | Money | `MaterielMenu_SHOP_*`, `CHURCH_*`, `INN_ROOT`, `TownMenu_*` | or affiché | générique | Vu (doc V251, V258) |
| 3 | RootMenu | `TownMenu_ROOT` | menu du terrain : Objets / Magie / Carac. / Divers | générique | Vu (doc V7, V251) |
| 4 | LeftCharaList | ~25 classes `TownMenu_*`, `MaterielMenuExtra_ChangeHostage` | colonne des personnages | `StatusIconChanger` `ui_menu.py:202` | Vu (doc V161) |
| 5 | TargetCharaList | `BattleExecStatus`, `MenuItem_RightCharaList_*` | cible d'objet / de sort | idem | Rendu seul |
| 6 | Pageing | `MenuItem_Pageing_*` | pages d'une liste | générique ; L / R = pages `window.py:2568` | Rendu seul |
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
| 22-23 | MapButton | `FieldImageMap`, `TownImageMap` | bouton « mode de la carte » | `window.py:1875` | Vu (doc V236, T188) |
| 24 | ShopMap | `TownImageMap` (9) | liste des boutiques de la ville | `Moteur.boutiques` `engine.py:` ; `window.py:2540` | Vu (doc V264, T133) |
| 25 | CityMap | `FieldImageMap`, `TownImageMap` | plan de la ville / carte réduite | `ICityMap` `ui_menu.py:201, 849` ; `engine.py:314` | Vu (doc, nombreux) |
| 26 | WorldLargeMap | `FieldImageMap` | grande carte du monde | `window.py:2165` | Vu (doc V327) |
| 27 | Config | `TownMenu_OPERATION_SETTING` (7) | paramètres du jeu d'origine | **contourné** : le bouton ouvre le menu Pause de la visionneuse (patch `engine.py:465`) ; la fenêtre d'origine n'est jamais ouverte | Contourné (volontaire, `notes-technique:242`) |
| 28 | MonsterEncyclopedia | `MaterielMenu_PICTUREBOOK_ROOT/DETAIL` | **Bestiaire** (partie 0x10) | partie 0x10 gérée (mise à jour du 04/11/2026 ; constat du 02/11 : non gérée) | **Présent** (liste, fiche et monstre dessinés, jouable au clavier : audit services SVC-04 ; constat du 02/11 : monstre non dessiné, §3.1 point 5) |
| 29 | BattleUpStatus | `BattleMenuSub_HISTORY` | bandeau d'état des personnages (combat) | `BattleBar` `ui_menu.py:204, 250`, secousse `347` | Vu (doc T85) |
| 30 | BattleRoot | `BattleMenu_ROOT` | Combattre / Fuir | générique | Vu (doc T90) |
| 31 | MonsterName | `BattleMenu_*` | plaques des monstres | `engine.py:286`, marques `ui_menu.py:407` | Vu (doc V61, T93) ; tri / évitement des plaques non reproduits |
| 32 | BattleAction | `BattleMenu_ACTIONMENU`, `ARRAYMENU` | menu d'actions | générique | Vu (doc T90) |
| 33-34 | BattleTarget, BattleGo | `BattleMenu_ATTACK`, `BattleGo` | cible, « Combattre » | générique | Rendu seul |
| 35-37 | BattleIM (×3) | `BattleMenu_MAGIC`, `ITEM`, `TACTICSMENU`, `ARRAY_*` | sorts, objets, tactiques | générique | Rendu seul |
| 38 | BattleInfo | `BattleMenu_ITEM`, `MAGIC` | description en combat | générique | Rendu seul |
| 39-40 | BattleEnemyTarget, BattlePartyTarget | `BattleMenu_*2ENEMY`, `*2PARTY` | cibles | générique | Rendu seul |
| 41-42 | BattleChangeButton, ChangeInfo | `BattleMenu_ARRAY_*`, `SetBattleChangeInfo` | changement de rang | générique | Rendu seul |
| 43 | BattleHoppingNumber | `BattleMenu_setHoppingNumber` | nombres de dégâts | `engine.py:273`, `window.py:2004` | Vu (doc V148) |
| 44 | Casino_CoinShop | `MaterielMenu_COINSALEROOM_ROOT` | échange d'argent contre des jetons | générique | **Inconnu** |
| 45-46 | Casino_GiftList, GiftTarget | `MaterielMenu_CHANGEGIFT_*` | prix contre jetons | générique | **Inconnu** |
| 47 | Casino_Slot | `MaterielMenu_SLOT` | machine à sous | générique ; mise réglable au clavier (mise à jour du 04/11/2026 ; constat du 02/11 : non réglable, §3) | **Vu (moi)** : moteur + capture GL ; jouable au clavier : SVC-04 |
| 48 | Casino_Poker | `MaterielMenuPoker{Betcoin,Changecard,Selectcard}` | poker | idem ; table et cartes dessinées (mise à jour du 04/11/2026 ; constat du 02/11 : non dessinées, §3) | **Vu (moi)** : moteur + capture GL ; jouable et dessiné au clavier : SVC-04 |
| 49-51 | Casino_FightStadium{Bet, Select, Coin} | `MaterielMenu_FIGHT_STADIUM` | arène des monstres (casino) | générique | **Inconnu** |
| 52 | StartMenuFirst | `TownPlayerManager` | 1er menu de départ | `pre_game.py` | Vu (doc V334) |
| 53 | StartMenuSecond | `MaterielMenu_LOAD` | menu de départ | `window.py:2116, 2186` | Vu (doc V334, T197) |
| 54 | StartMenuSelect | `MaterielMenu_LOAD/SAVE`, `MaterialMenu_Network` | liste des journaux | `window.py` + `saves.py` | Vu (doc V334-351, T107) |
| 55 | StartNameEntry | `MaterielMenu_NameEdit` | saisie du nom | `name_entry.py`, `window.py:2746` | Vu (doc V382) ; clavier « inventé » (G-099) |
| 56 | SaveOverwrite | `MaterielMenu_SAVE` | sauvegarde à l'église (écrasement) | générique | **Inconnu en jeu** (G-120, jamais confirmé sous Windows) |
| 57 | ShopRoot | `MaterielMenu_SHOP_ROOT`, `BANK_ROOT` | racine boutique / banque | générique | **Inconnu en jeu** |
| 58-59 | ShopBuy (×2) | `MaterielMenu_SHOP_BUYMENU` | liste d'achat | `window.py:1612` (◀ ▶ = quantité) | Rendu seul (`notes-technique:240`) |
| 60-61 | ShopBuyInfo (×2) | `MaterielMenu_SHOP_WHOSE` | « Qui va le porter ? » | `StatusIconChanger` | Rendu seul |
| 62 | ShopSellItemList | `MaterielMenu_SHOP_WHO_SELL` | liste de vente | générique | Rendu seul |
| 63 | ShopSellItemInfo | `MaterielMenu_SHOP_WHO_SELL` | quantité à vendre | `window.py:1612` | Rendu seul |
| 64-65 | BankDeposit, BankDraw | `MaterielMenu_BANK_PUTIN`, `BANK_DRAW` | banque | générique | **Inconnu en jeu** |
| 66 | ChurchRoot | `MaterielMenu_CHURCH_ROOT` | menu du prêtre | générique | Vu (doc V7 : liste de l'église) |
| 67 | ChurchWork | `MaterielMenu_CHURCH_MIRACLE` | résurrection, bénédiction | `StatusIconChanger` | **Inconnu** |
| 68 | Chapter2Status | `MaterielMenu_MARTIAL_COLOSSEUM` | arène martiale (chapitre 2) | générique | **Inconnu** |
| 69 | TorunekoMiseban | `MaterielMenu_EXTRA_SIDEJOB_SELL` | boutique de Torneko | générique | **Inconnu** |
| 70 | NENE_ItemView | `MaterielMenu_EXTRA_NENE` | objets de Nénè | générique | **Inconnu** |
| 71 | FightStadiumAbort | `BattleMenu_StadiumAbort` | abandon d'un combat d'arène | générique | **Inconnu** |
| 72 | ViewVolumeDecision | `TownFurnitureManager::TwinklePoint` | décision de « volume de vue » (meubles ? Supposé) | générique | **Inconnu** |
| 73 | TitleTouch | `TownOpeningManager` | « Touchez l'écran » du titre | lu à la main `window.py:2706` | Vu (doc T184, T197) |
| 74 | PortalButton | `MaterielMenu_LOAD` | bouton du portail Square Enix | aucun code propre | Non vérifié (inutile sur PC) |
| 75-79 | Network* | `MaterialMenu_Network` | réseau / nuage | inutilisé sur PC : case « Sauv. cloud » retirée `engine.py:350` | Contourné (77 : export en erreur) |
| 80 | License | `MaterielMenu_LOAD` | licence | lu à la main `window.py:2718` | Vu (doc T204) |

**Types sans aucune trace de test réel** (Rendu seul, Inconnu, Absent) : 5, 6, 7, 10, 11, 13-21, 33-42, 44-51, 56-65, 67-72, 74. Un test réel veut dire : le moteur les a ouverts et la visionneuse les a dessinés dans une session. Pour les ouvrir sans jouer 30 heures, il faut un point d'entrée par type (voir §5.4 : balayage « fenêtres »).

---

## 3. Matrice des fonctionnalités

Statuts : **Présent** (vu fonctionner, preuve citée), **Partiel** (une partie marche, le reste est un trou prouvé), **Absent** (prouvé à l'écran ou dans le code), **Inconnu** (aucune trace de test ; le code ne permet pas de conclure). « Comment tester » dit le chemin le plus court.

### 3.1 Casino : constats détaillés (le plus gros apport de cet audit)

Le casino est une **partie distincte du moteur** : `Global::startCasino` (appelé par `cmd_mini_game` ← `MaterielMenu_SlotEnter`) passe en partie **0xf**. `Global::setMinigame(0)` lance le **poker** (carte `ev04`, fenêtre de port 12, type 48), toute autre valeur la **machine à sous** (carte `ev05`, type 47). Établi par `probe_grid.py` (moteur seul). La visionneuse ne définit que les parties 3, 0xc, 0xd, 0xe (`engine.py:8-11`) : **0xf (casino) et 0x10 (bestiaire) n'existent pas dans son code**.

Ce que j'ai observé (Établi : moteur sous Unicorn avec 500 jetons écrits dans le moteur de test, et captures GL de la visionneuse réelle) :

1. **Machine à sous, côté moteur : jouable.** `envoyer_menu(12, 1, 1, 0x2)` ×3 (flèche ▲ du bouton 1) fait passer les jetons de 500 à 497 et la mise à 3 ; `[1, 0, 0x10]` (« Lancer ») lance les rouleaux (684 paquets 4 = rotations d'objets de carte), un nouvel appui les arrête, un message de résultat s'affiche (`probe_slot4.py`).
2. **Machine à sous, côté visionneuse : bien dessinée, jouable à la souris, pas au clavier.**
   - `gl_slot_b330.png` : la machine entière, la table des gains, « Jetons 500 », « Parier combien ? », ▲ 0 ▼, « Lancer » sont à l'écran.
   - Souris (clics sur ▲ ×3 puis « Lancer ») : `gl_slotms_b350.png` montre « Jetons 497 » et des rouleaux en mouvement.
   - **Clavier** (Haut ×3 puis Entrée) : `gl_slotkb_b420.png` est **identique à l'image sans entrée** (mise 0, « Jetons 500 », rien ne tourne). Cause lue dans le code : `_saisie_menu` (`window.py:1597-1621`) ne met dans `z` que les boutons de manette 0x10 ; ▲ et ▼ sont des boutons de manette 0x2 et 0x1 (types 47 et 48, `ui_layout.json`), donc **inaccessibles au curseur local** ; la fenêtre n'a pas de grille moteur (`probe_grid.py` : `grille = None`), donc les flèches du clavier ne sont pas transmises. Un joueur au clavier ne peut ni miser ni lancer (mise 0 : « Lancer » ne fait rien).
   - L'animation d'événement d'un gros gain (paquet 6, émis par `CasinoSlot::setBingoAnim` via `FldStage::eventAnim`) serait ignorée (aucune branche pour le paquet 6) ; **non observée** : mes sondes n'ont pas obtenu de gain.
3. **Poker, côté moteur : jouable.** La mise passe par les mêmes boutons ▲ ▼ (500 → 497, mise 3). Le bouton 0 (étiquette « DONNER ») pressé avec une mise de 0 ramène à la ville proprement (retour à `mak1f1`, partie 0xc, jetons intacts, 219 images) ; la main complète (échange de cartes, résultat) n'a **pas** été jouée (`probe_poker3.py` s'arrête là).
4. **Poker, côté visionneuse : table et cartes invisibles.** `gl_poker_b330.png` : écran **noir** avec seulement les fenêtres (table des gains, « Jetons 500 / Pariés 0 », message « Combien voulez-vous miser ? »). La carte `ev04` n'a **ni sol, ni texture** (« 0 groupes », 1 objet) : tout ce qu'on voit au poker sont des maillages dynamiques envoyés par les paquets 21 / 22 (5 modèles, 485 puis 450 paquets 22 par 90 images). La visionneuse ne les dessine **qu'en `PARTIE_VILLE` et en combat** (`window.py:2913`, condition `e.partie == MO.PARTIE_VILLE`). **Preuve causale** : avec un lanceur extérieur au dépôt qui force `etat.partie = 0xc` à l'affichage seulement (`gl_casino.py`, `CAS_FORCEVILLE=1`), `gl_pokerv_b330.png` montre **les cinq cartes face cachée**. Le correctif probable est de ne pas réserver ce bloc à la ville (casino 0xf, bestiaire 0x10) : **Supposé** (je n'ai pas modifié le dépôt, et je n'ai pas vérifié que les cartes retournées, la main gagnante et les animations passent aussi).
5. **Bestiaire (`Global::startBook`, partie 0x10, déclenché par `TownMenuItemSelectCommand::menuUpdate`, c'est-à-dire un bouton du menu du terrain)** : le moteur envoie 3 paquets de caméra / modèle (10, 11, 21) et ouvre le type 28. `gl_book_b230.png` : la **liste des monstres** (page 1, noms, « ??? » pour les inconnus, flèches de page) s'affiche, mais un **petit morceau de l'église `mak1f1`** transparaît derrière les boutons (la caméra du bestiaire regarde la dernière carte). `gl_booksel_b330.png` (après avoir choisi « Gluant » avec Entrée) : la **fiche** s'affiche avec ses chiffres (Vaincus 8, Expérience, Or…), mais **à la place du monstre on voit l'église `mak1f1`** (la dernière carte de ville, redessinée dans le cadre). Le moteur envoie bien le monstre : paquet 21 `[0, 0]` puis paquet 22 (maillage de 16 à 20 sommets en (0, 0, -62,25), emplacement 0), caméra en (0, 0, -83) (`probe_book2.py`, Établi). Il n'est pas dessiné. J'ai essayé de forcer l'affichage en partie ville (`CAS_FORCEVILLE=1`) : la capture est **identique octet pour octet** (`cmp`), donc la garde `PARTIE_VILLE` (`window.py:2913`) n'est **pas** la seule cause ici ; la cause n'est **pas trouvée** (Non vérifié : caméra de ville contre caméra du bestiaire, la carte non masquée, ou texture `m0`).

### 3.2 Matrice

| Fonctionnalité | Statut | Preuve | Comment tester |
|---|---|---|---|
| Boutiques : achat / vente / quantité (types 57-63, script `cmd_menu_shop`) | **Inconnu** (fenêtres : rendu seul) | types exportés, ◀ ▶ de quantité codés `window.py:1612` ; le moteur y arrive par `CommandWindow::changeShopMenuPhase` (graphe d'appels) ; aucun balayage ne les ouvre (au chargement, seul le type 12 apparaît) ; G-092 (autre agent) | Jouer : parler à un marchand (par ex. village de départ), acheter, vendre, vérifier l'or et le sac. Automatique : N2 (§5), noter les types 57-63. |
| Église : prêtre (type 66) | **Partiel** | liste de l'église vue dans le prologue (`mak1f1`, doc V7) | Parler au prêtre de `mak1f1` : Sauvegarder, Revenir à la vie, Prière |
| Église : résurrection / pénitence (type 67) | **Inconnu** | aucune trace | Avoir un personnage mort, parler au prêtre |
| Sauvegarde à l'église (`cmd_menu_save`, type 56) | **Inconnu en jeu** | écriture dans `--saves-ecriture` lue dans le code (`engine.py:41, 53`) ; jamais confirmée sous Windows (G-120) | Sauvegarder, quitter, relancer, « Continuer » ; comparer `data1.dat` |
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
