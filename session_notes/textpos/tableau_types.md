# Position des textes de l’interface : viewer vs jeu mobile (5 novembre 2026)

Généré par `/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/textpos/build_tableau.py` à partir de `mesures.json` (même dossier). Aucun fichier du dépôt n’a été modifié.

## Méthode et lecture

- Banc de mesure : `Render._text` de la visionneuse (vraie police SE-GARRIR), sans écran (headless), unités d’interface (1 u ≈ 1,008 px à 720p, ≈ 1,5 px à 1080p). 465 cellules de texte liées à un paramètre (80 types `Make_*`).
- **P** = mise en page exportée de l’APK pure (aucun écart de la visionneuse). **V** = réglages par défaut. **O** = `DQ_TEXTE_ORIGINAL=1` (ne retire QUE le recentrage vertical ; recoupe, compression et espaces fines restent actifs).
- Écart = V − P. `Δz` : décalage vertical de la ligne de base (positif = vers le haut) ; `Δx` : plus grand décalage d’un bord (gauche ou droit) sur les chaînes réelles ; `ts` : échelle horizontale minimale (1 = pas de compression).
- Chaînes : « observé » = chaînes françaises réelles de ce port (audit du moteur) ; « frère » = chaînes d’une cellule voisine du même groupe et du même numéro ; « aucune » = seulement une chaîne-sonde (`Abcdefgh`), donc position vérifiée, largeur non.
- Drapeaux : **R** recentrage vertical (`text_recentering`, D-143 / D-174, PR #45) ; **T** espaces fines (`THIN_SPACES`, #161 / #162) ; **K** compression horizontale ; **W** recoupe en lignes (descriptions) ; **d** dépasse son plaque/cadre dès le mode jeu (P) : trop long en français, classe d, laissé tel quel (D-133, C-13) ; **K\*** compression du poker (chaînes non observées).
- Classes : **a** identique (écart < 0,05 u) ; **b** petit écart voulu (recentrage seul, ≤ 7 u) ; **c** écart plus grand ou à question (compression, recoupe, espaces fines, poker) ; **d** dépassement dû à la longueur du français (indépendant de l’écart V − P, signalé en plus par le drapeau).

## Bilan

- Cellules : **53** a, **387** b, **25** c (sur 465). Drapeaux : K 2, K* 6, R 404, T 13, W 12, d 15.
- Recentrage vertical (R) : 404 cellules ; de 0.07 à 6.54 u (≈ 0.1 à 6.6 px à 720p), médiane 2.32 u. 61 cellules à interligne ≥ 1 : inchangées. Par interligne : 0.441 → 6.5 u (8) ; 0.801 → 2.3 u (296) ; 0.817 → 2.1 u (4) ; 0.841 → 1.9 u (27) ; 0.873 → 1.3 u (4) ; 0.881 → 1.4 u (44) ; 0.921 → 0.9 u (3) ; 0.929 → 0.9 u (5) ; 0.962 → 0.4 u (6).
- Aucun défaut d’ancre mal lue, de ligne manquante, de `\r\n` perdu, de tabulation mal calculée ni de texte caché par une plaque n’a été trouvé dans le mode P (mise en page exportée).

## Écarts au niveau de la fenêtre (le texte bouge avec elle)

| Type | Nom | Écart |
|---|---|---|
| 1 | YesNo | D-231 `_push_yes_no` : les deux plaques (côte à côte sur mobile) sont empilées, « Oui » au-dessus de « Non » (dx −135 u, dz −49 u pour la seconde) ; demande de Sylfried du 04/11 ; le texte suit sa plaque, placement relatif inchangé |
| 7 | MagicInfo | `fit_x` 214 u (CARD_COST_X_MAX) sur la ligne de coût (cellule 0/2) : compression x0,90 ; description (0/1) recoupée à 148 u (`DESCRIPTIONS`) |
| 10 | ItemInfo | description (0/4) recoupée à 148 u |
| 12 | Chapter | bandeau de chapitre : le quad « hyodai1 » (450 x 225) est reconstruit par la visionneuse ; pas de texte déplacé |
| 31 | MonsterName | plaques des noms de monstres : largeur recalculée par `_plate_width`, marge `PLATE_MARGIN` 7 u (les 4 cellules de nom ne sont pas liées à un paramètre) |
| 38 | BattleInfo | description (2/3) recoupée à 56 u + compression jusqu’à x0,70 (D-234) |
| 46 | Casino_GiftTarget | description (4/3) recoupée à 148 u (supposé : fenêtre non ouverte dans le moteur, #219) |
| 48 | Casino_Poker | étiquettes de bouton comprimées pour tenir dans la plaque, même avec la police d’origine (`BUTTON_COMPRESSION_TYPES`, SVC-03, « police réduite » : choix de Sylfried) |
| 53 | StartMenuSecond | `center_menu` : le groupe de boutons est centré en hauteur (dz = 200,1 u) dans un cadre noir ; bouton « Sauvegardes » à la place de « Sauv. cloud » (D-72) |
| 54 | StartMenuSelect | `_tab_title` : le titre suit l’onglet (code 2 : +30 u en x, −56 u en z) ; choix du portage, PR #39 ; `CENTERED_WINDOWS` : fenêtre centrée à l’écran |
| 55 | StartNameEntry | `CENTERED_WINDOWS` ; saisie du nom dessinée à la main (positions non retrouvées dans le code) |
| 60 | ShopBuyInfo | description (4/4) recoupée à 148 u |
| 61 | ShopBuyInfo | description (4/4) recoupée à 148 u (supposé, #219) |
| 63 | ShopSellItemInfo | description (0/4) recoupée à 148 u (supposé, #219) |
| 66 | ChurchRoot | `_church` : fenêtre reconstruite (plaque de sortie recopiée) |
| 70 | NENE_ItemView | description (0/3) recoupée à 148 u (supposé, #219) |
| 80 | License | licence dessinée à la main (positions non retrouvées dans le code) |

Hors `Make_*` : fenêtre de message du terrain (`MessageWindow`, types de message 0 à 3) : `three_lines` (cadre du type 1 réduit de 188 à 126 u, PR #20), `limit_lines` (canevas de 3 lignes exactes au lieu de 3,5 : bas −240,5 → −227 u, PR #32), `full_text` (types 2 et 3 agrandis de 1/0,9 : 459 → 510 u de large, 122 → 135,6 u de haut, PR #30, D-62), position de la boîte `_dz_message` / `MSG_BOTTOM` −362 / `CB_MSG_BOTTOM` −338 (option `--msg-origine`), échelle globale `UI_ZOOM` 1,12 (toute l’interface : rapports internes inchangés).

## Par type

| Type | Nom | Cellules | a | b | c | d | Écart de fenêtre |
|---|---|---|---|---|---|---|---|
| 1 | YesNo | 2 | 0 | 2 | 0 | 0 | oui (voir ci-dessus) |
| 2 | Money | 1 | 0 | 1 | 0 | 0 |  |
| 3 | RootMenu | 4 | 0 | 4 | 0 | 0 |  |
| 4 | LeftCharaList | 16 | 0 | 16 | 0 | 0 |  |
| 5 | TargetCharaList | 12 | 0 | 12 | 0 | 2 |  |
| 6 | Pageing | 1 | 0 | 1 | 0 | 0 |  |
| 7 | MagicInfo | 4 | 0 | 2 | 2 | 0 | oui (voir ci-dessus) |
| 8 | NameButton | 10 | 0 | 10 | 0 | 4 |  |
| 9 | ItemList | 4 | 0 | 3 | 1 | 0 |  |
| 10 | ItemInfo | 5 | 1 | 3 | 1 | 0 | oui (voir ci-dessus) |
| 11 | BCInfo | 1 | 0 | 1 | 0 | 0 |  |
| 12 | Chapter | 2 | 2 | 0 | 0 | 0 | oui (voir ci-dessus) |
| 13 | Status | 4 | 2 | 2 | 0 | 0 |  |
| 14 | Status | 2 | 1 | 1 | 0 | 0 |  |
| 15 | Status | 3 | 0 | 3 | 0 | 0 |  |
| 16 | Status | 2 | 2 | 0 | 0 | 0 |  |
| 17 | Status | 4 | 3 | 1 | 0 | 0 |  |
| 18 | OperationItemList | 1 | 1 | 0 | 0 | 0 |  |
| 19 | Senreki | 4 | 2 | 2 | 0 | 0 |  |
| 20 | MemberShift | 12 | 0 | 12 | 0 | 0 |  |
| 21 | MemberShiftButton | 13 | 0 | 12 | 1 | 0 |  |
| 22 | MapButton | 0 | 0 | 0 | 0 | 0 | sans texte lié |
| 23 | MapButton | 0 | 0 | 0 | 0 | 0 | sans texte lié |
| 24 | ShopMap | 4 | 2 | 2 | 0 | 0 |  |
| 25 | CityMap | 0 | 0 | 0 | 0 | 0 | sans texte lié |
| 26 | WorldLargeMap | 0 | 0 | 0 | 0 | 0 | sans texte lié |
| 27 | Config | 3 | 0 | 3 | 0 | 0 |  |
| 28 | MonsterEncyclopedia | 16 | 3 | 13 | 0 | 0 |  |
| 29 | BattleUpStatus | 16 | 8 | 8 | 0 | 0 |  |
| 30 | BattleRoot | 4 | 0 | 4 | 0 | 0 |  |
| 31 | MonsterName | 0 | 0 | 0 | 0 | 0 | oui (voir ci-dessus) |
| 32 | BattleAction | 5 | 0 | 5 | 0 | 0 |  |
| 33 | BattleTarget | 6 | 0 | 6 | 0 | 0 |  |
| 34 | BattleGo | 2 | 0 | 2 | 0 | 0 |  |
| 35 | BattleIM | 12 | 0 | 12 | 0 | 0 |  |
| 36 | BattleIM | 8 | 0 | 8 | 0 | 0 |  |
| 37 | BattleIM | 12 | 0 | 12 | 0 | 0 |  |
| 38 | BattleInfo | 7 | 1 | 5 | 1 | 0 | oui (voir ci-dessus) |
| 39 | BattleEnemyTarget | 7 | 0 | 7 | 0 | 0 |  |
| 40 | BattlePartyTarget | 7 | 0 | 7 | 0 | 0 |  |
| 41 | BattleChangeButton | 2 | 0 | 2 | 0 | 0 |  |
| 42 | BattleChangeInfo | 8 | 0 | 8 | 0 | 0 |  |
| 43 | BattleHoppingNumber | 0 | 0 | 0 | 0 | 0 | sans texte lié |
| 44 | Casino_CoinShop | 10 | 0 | 10 | 0 | 0 |  |
| 45 | Casino_GiftList | 7 | 1 | 6 | 0 | 0 |  |
| 46 | Casino_GiftTarget | 21 | 2 | 18 | 1 | 0 | oui (voir ci-dessus) |
| 47 | Casino_Slot | 6 | 0 | 6 | 0 | 0 |  |
| 48 | Casino_Poker | 16 | 0 | 10 | 6 | 0 | oui (voir ci-dessus) |
| 49 | Casino_FightStadiumBet | 7 | 0 | 7 | 0 | 0 |  |
| 50 | Casino_FightStadiumSelect | 10 | 0 | 10 | 0 | 0 |  |
| 51 | Casino_FightStadiumCoin | 2 | 0 | 2 | 0 | 0 |  |
| 52 | StartMenuFirst | 1 | 0 | 1 | 0 | 0 |  |
| 53 | StartMenuSecond | 7 | 0 | 7 | 0 | 0 | oui (voir ci-dessus) |
| 54 | StartMenuSelect | 7 | 0 | 5 | 2 | 0 | oui (voir ci-dessus) |
| 55 | StartNameEntry | 4 | 0 | 4 | 0 | 0 | oui (voir ci-dessus) |
| 56 | SaveOverwrite | 2 | 0 | 0 | 2 | 0 |  |
| 57 | ShopRoot | 4 | 0 | 3 | 1 | 0 |  |
| 58 | ShopBuy | 10 | 4 | 6 | 0 | 0 |  |
| 59 | ShopBuy | 10 | 4 | 6 | 0 | 0 |  |
| 60 | ShopBuyInfo | 22 | 2 | 18 | 2 | 5 | oui (voir ci-dessus) |
| 61 | ShopBuyInfo | 14 | 2 | 10 | 2 | 4 | oui (voir ci-dessus) |
| 62 | ShopSellItemList | 13 | 1 | 12 | 0 | 0 |  |
| 63 | ShopSellItemInfo | 9 | 6 | 2 | 1 | 0 | oui (voir ci-dessus) |
| 64 | BankDeposit | 10 | 0 | 10 | 0 | 0 |  |
| 65 | BankDraw | 11 | 0 | 11 | 0 | 0 |  |
| 66 | ChurchRoot | 2 | 0 | 1 | 1 | 0 | oui (voir ci-dessus) |
| 67 | ChurchWork | 19 | 0 | 19 | 0 | 0 |  |
| 68 | Chapter2Status | 2 | 0 | 2 | 0 | 0 |  |
| 69 | TorunekoMiseban | 7 | 1 | 6 | 0 | 0 |  |
| 70 | NENE_ItemView | 3 | 1 | 1 | 1 | 0 | oui (voir ci-dessus) |
| 71 | FightStadiumAbort | 1 | 0 | 1 | 0 | 0 |  |
| 72 | ViewVolumeDecision | 0 | 0 | 0 | 0 | 0 | sans texte lié |
| 73 | TitleTouch | 0 | 0 | 0 | 0 | 0 | sans texte lié |
| 74 | PortalButton | 0 | 0 | 0 | 0 | 0 | sans texte lié |
| 75 | NetworkRoot | 0 | 0 | 0 | 0 | 0 | sans texte lié |
| 76 | NetworkRoot | 0 | 0 | 0 | 0 | 0 | sans texte lié |
| 77 | NetworkPLST | 0 | 0 | 0 | 0 | 0 | sans texte lié |
| 78 | NetworkCODE | 0 | 0 | 0 | 0 | 0 | sans texte lié |
| 79 | NetworkITEM | 2 | 1 | 1 | 0 | 0 |  |
| 80 | License | 0 | 0 | 0 | 0 | 0 | oui (voir ci-dessus) |

## Par cellule

`id/no` : paramètre du jeu. `anc/al` : ancre (0 à 8) / alignement. `ls` : interligne exporté. `tab` : tabSize. `Δz` en u (px à 720p). `dép.` : dépassement du plaque/cadre en mode P (u).

| Type | id/no | anc/al | ls | tab | chaînes | Δz u (px) | Δx u | ts | dép. | Drapeaux | Cl. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 YesNo | 0/0 | 4/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 1 YesNo | 1/0 | 4/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 2 Money | 0/0 | 2/2 | 0.801 |  | observé 3 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 3 RootMenu | 0/1 | 7/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 3 RootMenu | 1/1 | 7/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 3 RootMenu | 2/1 | 7/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 3 RootMenu | 3/1 | 7/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 0/1 | 1/1 | 0.801 |  | frère 4 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 0/2 | 0/0 | 0.801 |  | frère 2 | +2.33 (+2.3) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 0/3 | 0/0 | 0.801 |  | frère 5 | +2.33 (+2.3) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 0/5 | 0/0 | 0.801 |  | frère 2 | +2.20 (+2.2) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 1/1 | 1/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 1/2 | 0/0 | 0.801 |  | observé 1 | +2.33 (+2.3) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 1/3 | 0/0 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 1/5 | 0/0 | 0.801 |  | observé 1 | +2.20 (+2.2) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 2/1 | 1/1 | 0.801 |  | observé 2 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 2/2 | 0/0 | 0.801 |  | observé 2 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 2/3 | 0/0 | 0.801 |  | observé 4 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 2/5 | 0/0 | 0.801 |  | observé 2 | +2.19 (+2.2) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 3/1 | 1/1 | 0.801 |  | observé 4 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 3/2 | 0/0 | 0.801 |  | observé 2 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 3/3 | 0/0 | 0.801 |  | observé 4 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 4 LeftCharaList | 3/5 | 0/0 | 0.801 |  | observé 2 | +2.19 (+2.2) | 0.0 | 1.00 |  | R | b |
| 5 TargetCharaList | 0/1 | 1/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 5 TargetCharaList | 0/2 | 0/0 | 0.801 |  | observé 5 | +2.33 (+2.3) | 0.0 | 1.00 | 18 | R d | b |
| 5 TargetCharaList | 0/3 | 0/0 | 0.801 |  | observé 9 | +2.33 (+2.3) | 0.0 | 1.00 |  | R | b |
| 5 TargetCharaList | 0/5 | 0/0 | 0.801 |  | observé 1 | +2.19 (+2.2) | 0.0 | 1.00 |  | R | b |
| 5 TargetCharaList | 1/1 | 1/1 | 0.801 |  | observé 2 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 5 TargetCharaList | 1/2 | 0/0 | 0.801 |  | observé 3 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 5 TargetCharaList | 1/3 | 0/0 | 0.801 |  | observé 2 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 5 TargetCharaList | 1/5 | 0/0 | 0.801 |  | observé 1 | +2.20 (+2.2) | 0.0 | 1.00 |  | R | b |
| 5 TargetCharaList | 2/1 | 1/1 | 0.801 |  | frère 3 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 5 TargetCharaList | 2/2 | 0/0 | 0.801 |  | frère 7 | +2.32 (+2.3) | 0.0 | 1.00 | 18 | R d | b |
| 5 TargetCharaList | 2/3 | 0/0 | 0.801 |  | frère 11 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 5 TargetCharaList | 2/5 | 0/0 | 0.801 |  | frère 2 | +2.19 (+2.2) | 0.0 | 1.00 |  | R | b |
| 6 Pageing | 0/0 | 4/1 | 0.801 |  | observé 9 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 7 MagicInfo | 0/0 | 4/1 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 7 MagicInfo | 0/1 | 0/0 | 0.962 |  | observé+desc. 112 | +0.45 (+0.5) | 152.2 | 1.00 |  | R T W | c |
| 7 MagicInfo | 0/2 | 0/0 | 0.881 |  | observé 1 | +1.39 (+1.4) | 15.1 | 0.90 |  | R K | c |
| 7 MagicInfo | 0/3 | 4/1 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 8 NameButton | 0/0 | 4/1 | 0.841 |  | observé 7 | +1.96 (+2.0) | 0.0 | 1.00 |  | R | b |
| 8 NameButton | 0/1 | 3/0 | 0.841 | 8.0 | observé 1 | +1.24 (+1.2) | 0.0 | 1.00 | 36 | R d | b |
| 8 NameButton | 1/0 | 4/1 | 0.841 |  | observé 5 | +1.96 (+2.0) | 0.0 | 1.00 |  | R | b |
| 8 NameButton | 1/1 | 3/0 | 0.841 | 8.0 | frère 1 | +1.24 (+1.2) | 0.0 | 1.00 | 36 | R d | b |
| 8 NameButton | 2/0 | 4/1 | 0.841 |  | observé 5 | +1.96 (+2.0) | 0.0 | 1.00 |  | R | b |
| 8 NameButton | 2/1 | 3/0 | 0.841 | 8.0 | frère 1 | +1.24 (+1.2) | 0.0 | 1.00 | 36 | R d | b |
| 8 NameButton | 3/0 | 4/1 | 0.841 |  | observé 4 | +1.96 (+2.0) | 0.0 | 1.00 |  | R | b |
| 8 NameButton | 3/1 | 3/0 | 0.841 | 8.0 | frère 1 | +1.24 (+1.2) | 0.0 | 1.00 | 36 | R d | b |
| 8 NameButton | 4/0 | 4/1 | 0.841 |  | observé 1 | +1.96 (+2.0) | 0.0 | 1.00 |  | R | b |
| 8 NameButton | 5/0 | 4/1 | 0.841 |  | frère 21 | +1.96 (+2.0) | 0.0 | 1.00 |  | R | b |
| 9 ItemList | 0/2 | 3/0 | 0.841 |  | observé 9 | +1.86 (+1.9) | 0.0 | 1.00 |  | R | b |
| 9 ItemList | 1/2 | 3/0 | 0.841 |  | observé 5 | +1.86 (+1.9) | 0.0 | 1.00 |  | R W | c |
| 9 ItemList | 2/2 | 3/0 | 0.841 |  | observé 3 | +1.85 (+1.9) | 0.0 | 1.00 |  | R | b |
| 9 ItemList | 3/2 | 3/0 | 0.841 |  | observé 3 | +1.85 (+1.9) | 0.0 | 1.00 |  | R | b |
| 10 ItemInfo | 0/1 | 4/1 | 0.801 |  | observé 9 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 10 ItemInfo | 0/2 | 3/0 | 0.921 |  | observé 9 | +0.92 (+0.9) | 0.0 | 1.00 |  | R | b |
| 10 ItemInfo | 0/3 | 3/0 | 1.002 |  | observé 16 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 10 ItemInfo | 0/4 | 0/0 | 0.962 |  | observé+desc. 111 | +0.45 (+0.5) | 152.2 | 1.00 |  | R T W | c |
| 10 ItemInfo | 0/5 | 4/1 | 0.801 |  | observé 3 | +2.26 (+2.3) | 0.0 | 1.00 |  | R | b |
| 11 BCInfo | 0/1 | 4/1 | 0.801 |  | observé 6 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 12 Chapter | 0/0 | 1/1 | 1.603 |  | observé 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 12 Chapter | 0/1 | 4/1 | 1.002 |  | observé 1 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 13 Status | 0/0 | 0/0 | 0.801 |  | observé 2 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 13 Status | 0/1 | 2/2 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 13 Status | 0/2 | 0/0 | 1.210 |  | observé 3 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 13 Status | 0/3 | 0/0 | 1.210 |  | observé 3 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 14 Status | 0/0 | 1/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 14 Status | 0/1 | 0/0 | 1.042 |  | observé 3 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 15 Status | 0/0 | 1/1 | 0.801 |  | observé 2 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 15 Status | 0/1 | 0/0 | 0.994 |  | observé 1 | +0.07 (+0.1) | 0.0 | 1.00 |  | R | b |
| 15 Status | 0/2 | 0/0 | 0.994 |  | observé 0 | +0.07 (+0.1) | 0.0 | 1.00 |  | R | b |
| 16 Status | 0/0 | 0/0 | 2.212 |  | observé 1 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 16 Status | 0/1 | 2/2 | 2.212 |  | observé 2 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 17 Status | 0/0 | 0/0 | 3.910 |  | observé 2 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 17 Status | 0/1 | 0/0 | 3.910 |  | observé 2 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 17 Status | 0/2 | 0/0 | 3.910 |  | observé 2 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 17 Status | 0/3 | 0/0 | 0.978 |  | observé 2 | +0.25 (+0.2) | 0.0 | 1.00 |  | R | b |
| 18 OperationItemList | 0/0 | 0/0 | 1.194 |  | observé 2 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 19 Senreki | 0/0 | 0/0 | 1.362 |  | observé 1 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 19 Senreki | 0/1 | 2/2 | 1.362 |  | observé 2 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 19 Senreki | 0/2 | 0/0 | 0.801 |  | observé 2 | +2.84 (+2.9) | 0.0 | 1.00 |  | R | b |
| 19 Senreki | 0/3 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 20 MemberShift | 0/1 | 0/0 | 0.801 |  | observé 2 | +2.45 (+2.5) | 0.0 | 1.00 | 62 | R | b |
| 20 MemberShift | 0/2 | 0/0 | 0.817 | 8.0 | observé 2 | +2.14 (+2.2) | 0.0 | 1.00 | 43 | R | b |
| 20 MemberShift | 0/3 | 0/0 | 0.801 |  | observé 1 | +2.20 (+2.2) | 0.0 | 1.00 |  | R | b |
| 20 MemberShift | 1/1 | 0/0 | 0.801 |  | observé 2 | +2.45 (+2.5) | 0.0 | 1.00 | 62 | R | b |
| 20 MemberShift | 1/2 | 0/0 | 0.817 | 8.0 | observé 2 | +2.14 (+2.2) | 0.0 | 1.00 | 43 | R | b |
| 20 MemberShift | 1/3 | 0/0 | 0.801 |  | observé 1 | +2.20 (+2.2) | 0.0 | 1.00 |  | R | b |
| 20 MemberShift | 2/1 | 0/0 | 0.801 |  | observé 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 20 MemberShift | 2/2 | 0/0 | 0.817 | 8.0 | observé 0 | +2.14 (+2.2) | 0.0 | 1.00 |  | R | b |
| 20 MemberShift | 2/3 | 0/0 | 0.801 |  | observé 1 | +2.19 (+2.2) | 0.0 | 1.00 |  | R | b |
| 20 MemberShift | 3/1 | 0/0 | 0.801 |  | observé 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 20 MemberShift | 3/2 | 0/0 | 0.817 | 8.0 | observé 0 | +2.14 (+2.2) | 0.0 | 1.00 |  | R | b |
| 20 MemberShift | 3/3 | 0/0 | 0.801 |  | observé 1 | +2.19 (+2.2) | 0.0 | 1.00 |  | R | b |
| 21 MemberShiftButton | 4/0 | 3/0 | 0.962 |  | observé 1 | +0.45 (+0.5) | 6.0 | 1.00 |  | R T | c |
| 21 MemberShiftButton | 0/1 | 0/0 | 0.801 |  | observé 2 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 21 MemberShiftButton | 0/2 | 0/0 | 0.962 |  | observé 2 | +0.45 (+0.5) | 0.0 | 1.00 |  | R | b |
| 21 MemberShiftButton | 0/3 | 0/0 | 0.801 |  | observé 2 | +2.20 (+2.2) | 0.0 | 1.00 |  | R | b |
| 21 MemberShiftButton | 0/6 | 0/0 | 0.801 |  | observé 2 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 21 MemberShiftButton | 1/1 | 0/0 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 21 MemberShiftButton | 1/2 | 0/0 | 0.962 |  | observé 1 | +0.45 (+0.5) | 0.0 | 1.00 |  | R | b |
| 21 MemberShiftButton | 1/3 | 0/0 | 0.801 |  | observé 1 | +2.19 (+2.2) | 0.0 | 1.00 |  | R | b |
| 21 MemberShiftButton | 1/6 | 0/0 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 21 MemberShiftButton | 2/1 | 0/0 | 0.801 |  | frère 2 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 21 MemberShiftButton | 2/2 | 0/0 | 0.962 |  | frère 2 | +0.45 (+0.5) | 0.0 | 1.00 |  | R | b |
| 21 MemberShiftButton | 2/3 | 0/0 | 0.801 |  | frère 2 | +2.19 (+2.2) | 0.0 | 1.00 |  | R | b |
| 21 MemberShiftButton | 2/6 | 0/0 | 0.801 |  | frère 2 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 24 ShopMap | 0/0 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 24 ShopMap | 0/1 | 0/0 | 1.442 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 24 ShopMap | 0/2 | 2/2 | 1.442 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 24 ShopMap | 0/3 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 27 Config | 0/0 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 27 Config | 0/1 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 27 Config | 0/2 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 12/2 | 0/0 | 1.426 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 28 MonsterEncyclopedia | 12/3 | 0/0 | 1.426 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 28 MonsterEncyclopedia | 12/4 | 2/2 | 1.426 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 28 MonsterEncyclopedia | 12/1 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 0/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 1/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 2/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 3/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 4/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 5/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 6/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 7/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 8/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 9/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 10/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 28 MonsterEncyclopedia | 11/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 29 BattleUpStatus | 0/1 | 1/1 | 0.801 |  | observé 1 | +2.19 (+2.2) | 0.0 | 1.00 |  | R | b |
| 29 BattleUpStatus | 0/2 | 0/0 | 1.258 |  | observé 1 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 29 BattleUpStatus | 0/3 | 2/2 | 1.258 |  | observé 3 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 29 BattleUpStatus | 0/4 | 1/1 | 0.873 |  | observé 12 | +1.32 (+1.3) | 0.0 | 1.00 |  | R | b |
| 29 BattleUpStatus | 1/1 | 1/1 | 0.801 |  | observé 1 | +2.19 (+2.2) | 0.0 | 1.00 |  | R | b |
| 29 BattleUpStatus | 1/2 | 0/0 | 1.258 |  | observé 1 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 29 BattleUpStatus | 1/3 | 2/2 | 1.258 |  | observé 1 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 29 BattleUpStatus | 1/4 | 1/1 | 0.873 |  | observé 0 | +1.32 (+1.3) | 0.0 | 1.00 |  | R | b |
| 29 BattleUpStatus | 2/1 | 1/1 | 0.801 |  | frère 2 | +2.19 (+2.2) | 0.0 | 1.00 |  | R | b |
| 29 BattleUpStatus | 2/2 | 0/0 | 1.258 |  | frère 1 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 29 BattleUpStatus | 2/3 | 2/2 | 1.258 |  | frère 4 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 29 BattleUpStatus | 2/4 | 1/1 | 0.873 |  | frère 12 | +1.32 (+1.3) | 0.0 | 1.00 |  | R | b |
| 29 BattleUpStatus | 3/1 | 1/1 | 0.801 |  | frère 2 | +2.19 (+2.2) | 0.0 | 1.00 |  | R | b |
| 29 BattleUpStatus | 3/2 | 0/0 | 1.258 |  | frère 1 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 29 BattleUpStatus | 3/3 | 2/2 | 1.258 |  | frère 4 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 29 BattleUpStatus | 3/4 | 1/1 | 0.873 |  | frère 12 | +1.32 (+1.3) | 0.0 | 1.00 |  | R | b |
| 30 BattleRoot | 0/1 | 7/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 30 BattleRoot | 1/1 | 7/1 | 0.801 |  | frère 2 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 30 BattleRoot | 2/1 | 7/1 | 0.801 |  | frère 2 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 30 BattleRoot | 3/1 | 7/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 32 BattleAction | 4/0 | 4/1 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 32 BattleAction | 0/1 | 7/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 32 BattleAction | 1/1 | 7/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 32 BattleAction | 2/1 | 7/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 32 BattleAction | 3/1 | 7/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 33 BattleTarget | 4/0 | 4/1 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 33 BattleTarget | 4/1 | 4/1 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 33 BattleTarget | 0/0 | 3/0 | 0.441 | 25.0 | observé 1 | +6.54 (+6.6) | 0.0 | 1.00 |  | R | b |
| 33 BattleTarget | 1/0 | 3/0 | 0.441 | 25.0 | observé 1 | +6.54 (+6.6) | 0.0 | 1.00 |  | R | b |
| 33 BattleTarget | 2/0 | 3/0 | 0.441 | 25.0 | frère 7 | +6.54 (+6.6) | 0.0 | 1.00 |  | R | b |
| 33 BattleTarget | 3/0 | 3/0 | 0.441 | 25.0 | frère 7 | +6.54 (+6.6) | 0.0 | 1.00 |  | R | b |
| 34 BattleGo | 0/0 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 34 BattleGo | 0/1 | 3/0 | 0.841 | 8.0 | aucune 0 | +1.24 (+1.2) | 0.0 | 1.00 |  | R | b |
| 35 BattleIM | 4/0 | 4/1 | 0.801 |  | frère 4 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 35 BattleIM | 4/1 | 4/1 | 0.801 |  | frère 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 35 BattleIM | 4/2 | 3/0 | 0.801 |  | frère 7 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 35 BattleIM | 5/0 | 4/1 | 0.801 |  | frère 4 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 35 BattleIM | 0/0 | 4/1 | 0.801 |  | frère 4 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 35 BattleIM | 0/1 | 3/0 | 0.841 | 8.0 | frère 1 | +1.24 (+1.2) | 0.0 | 1.00 |  | R | b |
| 35 BattleIM | 1/0 | 4/1 | 0.801 |  | frère 4 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 35 BattleIM | 1/1 | 3/0 | 0.841 | 8.0 | frère 1 | +1.24 (+1.2) | 0.0 | 1.00 |  | R | b |
| 35 BattleIM | 2/0 | 4/1 | 0.801 |  | frère 4 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 35 BattleIM | 2/1 | 3/0 | 0.841 | 8.0 | frère 1 | +1.24 (+1.2) | 0.0 | 1.00 |  | R | b |
| 35 BattleIM | 3/0 | 4/1 | 0.801 |  | frère 4 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 35 BattleIM | 3/1 | 3/0 | 0.841 | 8.0 | frère 1 | +1.24 (+1.2) | 0.0 | 1.00 |  | R | b |
| 36 BattleIM | 4/0 | 4/1 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 36 BattleIM | 4/1 | 4/1 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 36 BattleIM | 4/2 | 3/0 | 0.801 |  | frère 7 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 36 BattleIM | 5/0 | 4/1 | 0.801 |  | observé 3 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 36 BattleIM | 0/2 | 3/0 | 0.841 |  | observé 4 | +1.75 (+1.8) | 0.0 | 1.00 |  | R | b |
| 36 BattleIM | 1/2 | 3/0 | 0.841 |  | observé 2 | +1.75 (+1.8) | 0.0 | 1.00 |  | R | b |
| 36 BattleIM | 2/2 | 3/0 | 0.841 |  | observé 2 | +1.75 (+1.8) | 0.0 | 1.00 |  | R | b |
| 36 BattleIM | 3/2 | 3/0 | 0.841 |  | observé 2 | +1.75 (+1.8) | 0.0 | 1.00 |  | R | b |
| 37 BattleIM | 4/0 | 4/1 | 0.801 |  | frère 4 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 37 BattleIM | 4/1 | 4/1 | 0.801 |  | frère 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 37 BattleIM | 4/2 | 3/0 | 0.801 |  | frère 7 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 37 BattleIM | 5/0 | 4/1 | 0.801 |  | frère 4 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 37 BattleIM | 0/1 | 3/0 | 0.801 |  | frère 1 | +2.20 (+2.2) | 0.0 | 1.00 |  | R | b |
| 37 BattleIM | 0/2 | 3/0 | 0.801 |  | frère 7 | +1.94 (+2.0) | 0.0 | 1.00 |  | R | b |
| 37 BattleIM | 1/1 | 3/0 | 0.801 |  | frère 1 | +2.20 (+2.2) | 0.0 | 1.00 |  | R | b |
| 37 BattleIM | 1/2 | 3/0 | 0.801 |  | frère 7 | +1.94 (+2.0) | 0.0 | 1.00 |  | R | b |
| 37 BattleIM | 2/1 | 3/0 | 0.801 |  | frère 1 | +2.20 (+2.2) | 0.0 | 1.00 |  | R | b |
| 37 BattleIM | 2/2 | 3/0 | 0.801 |  | frère 7 | +1.94 (+2.0) | 0.0 | 1.00 |  | R | b |
| 37 BattleIM | 3/1 | 3/0 | 0.801 |  | frère 1 | +2.20 (+2.2) | 0.0 | 1.00 |  | R | b |
| 37 BattleIM | 3/2 | 3/0 | 0.801 |  | frère 7 | +1.94 (+2.0) | 0.0 | 1.00 |  | R | b |
| 38 BattleInfo | 2/0 | 4/1 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 38 BattleInfo | 2/1 | 4/1 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 38 BattleInfo | 2/2 | 3/0 | 0.801 |  | observé 7 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 38 BattleInfo | 2/3 | 3/0 | 1.010 |  | observé+desc. 111 | +0.00 (+0.0) | 199.9 | 0.75 |  | T K W | c |
| 38 BattleInfo | 2/4 | 3/0 | 1.010 |  | observé 6 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 38 BattleInfo | 0/0 | 4/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 38 BattleInfo | 1/0 | 4/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 39 BattleEnemyTarget | 4/0 | 4/1 | 0.801 |  | frère 7 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 39 BattleEnemyTarget | 4/1 | 4/1 | 0.801 |  | frère 2 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 39 BattleEnemyTarget | 4/2 | 3/0 | 0.801 |  | frère 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 39 BattleEnemyTarget | 0/0 | 3/0 | 0.441 | 25.0 | frère 7 | +6.54 (+6.6) | 0.0 | 1.00 |  | R | b |
| 39 BattleEnemyTarget | 1/0 | 3/0 | 0.441 | 25.0 | frère 7 | +6.54 (+6.6) | 0.0 | 1.00 |  | R | b |
| 39 BattleEnemyTarget | 2/0 | 3/0 | 0.441 | 25.0 | frère 7 | +6.54 (+6.6) | 0.0 | 1.00 |  | R | b |
| 39 BattleEnemyTarget | 3/0 | 3/0 | 0.441 | 25.0 | frère 7 | +6.54 (+6.6) | 0.0 | 1.00 |  | R | b |
| 40 BattlePartyTarget | 4/0 | 4/1 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 40 BattlePartyTarget | 4/1 | 4/1 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 40 BattlePartyTarget | 4/2 | 3/0 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 40 BattlePartyTarget | 0/0 | 4/1 | 0.881 |  | observé 3 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 40 BattlePartyTarget | 1/0 | 4/1 | 0.881 |  | observé 1 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 40 BattlePartyTarget | 2/0 | 4/1 | 0.881 |  | frère 7 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 40 BattlePartyTarget | 3/0 | 4/1 | 0.881 |  | frère 7 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 41 BattleChangeButton | 0/0 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 41 BattleChangeButton | 1/0 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 42 BattleChangeInfo | 0/1 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 42 BattleChangeInfo | 0/2 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 42 BattleChangeInfo | 0/3 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 42 BattleChangeInfo | 0/4 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 42 BattleChangeInfo | 0/5 | 0/0 | 0.901 |  | aucune 0 | +1.15 (+1.2) | 0.0 | 1.00 |  | R | b |
| 42 BattleChangeInfo | 0/6 | 0/0 | 0.901 |  | aucune 0 | +1.15 (+1.2) | 0.0 | 1.00 |  | R | b |
| 42 BattleChangeInfo | 0/7 | 0/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 42 BattleChangeInfo | 0/8 | 0/0 | 0.801 |  | aucune 0 | +2.07 (+2.1) | 0.0 | 1.00 |  | R | b |
| 44 Casino_CoinShop | 0/0 | 3/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 44 Casino_CoinShop | 0/1 | 5/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 44 Casino_CoinShop | 0/2 | 5/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 44 Casino_CoinShop | 0/4 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 44 Casino_CoinShop | 0/3 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 44 Casino_CoinShop | 1/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 44 Casino_CoinShop | 2/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 44 Casino_CoinShop | 3/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 44 Casino_CoinShop | 4/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 44 Casino_CoinShop | 5/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 45 Casino_GiftList | 6/0 | 2/2 | 2.460 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 45 Casino_GiftList | 0/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 45 Casino_GiftList | 1/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 45 Casino_GiftList | 2/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 45 Casino_GiftList | 3/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 45 Casino_GiftList | 4/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 45 Casino_GiftList | 5/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 4/0 | 4/1 | 1.002 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 46 Casino_GiftTarget | 4/1 | 3/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 4/2 | 3/0 | 1.002 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 46 Casino_GiftTarget | 4/3 | 0/0 | 1.002 |  | frère+desc. 111 | +0.00 (+0.0) | 152.2 | 1.00 |  | T W | c |
| 46 Casino_GiftTarget | 4/4 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 0/1 | 1/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 0/2 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 0/3 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 0/5 | 0/0 | 0.801 |  | aucune 0 | +2.33 (+2.3) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 1/1 | 1/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 1/2 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 1/3 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 1/5 | 0/0 | 0.801 |  | aucune 0 | +2.33 (+2.3) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 2/1 | 1/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 2/2 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 2/3 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 2/5 | 0/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 3/1 | 1/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 3/2 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 3/3 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 46 Casino_GiftTarget | 3/5 | 0/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 47 Casino_Slot | 0/0 | 2/2 | 0.801 |  | aucune 0 | +2.33 (+2.3) | 0.0 | 1.00 |  | R | b |
| 47 Casino_Slot | 0/1 | 0/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 47 Casino_Slot | 0/2 | 0/0 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 47 Casino_Slot | 0/4 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 47 Casino_Slot | 0/3 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 47 Casino_Slot | 1/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 48 Casino_Poker | 0/0 | 0/0 | 0.825 |  | aucune 0 | +2.16 (+2.2) | 0.0 | 1.00 |  | R | b |
| 48 Casino_Poker | 0/1 | 2/2 | 0.825 |  | aucune 0 | +2.16 (+2.2) | 0.0 | 1.00 |  | R | b |
| 48 Casino_Poker | 0/2 | 0/0 | 0.929 |  | aucune 0 | +0.87 (+0.9) | 0.0 | 1.00 |  | R | b |
| 48 Casino_Poker | 0/3 | 2/2 | 0.929 |  | aucune 0 | +0.87 (+0.9) | 0.0 | 1.00 |  | R | b |
| 48 Casino_Poker | 0/4 | 0/0 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 48 Casino_Poker | 0/7 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 48 Casino_Poker | 0/5 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 48 Casino_Poker | 1/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 48 Casino_Poker | 2/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 48 Casino_Poker | 0/6 | 0/0 | 0.929 |  | aucune 0 | +0.87 (+0.9) | 0.0 | 1.00 |  | R | b |
| 48 Casino_Poker | 4/0 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R K* | c |
| 48 Casino_Poker | 4/1 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R K* | c |
| 48 Casino_Poker | 4/2 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R K* | c |
| 48 Casino_Poker | 4/3 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R K* | c |
| 48 Casino_Poker | 4/4 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R K* | c |
| 48 Casino_Poker | 4/5 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R K* | c |
| 49 Casino_FightStadiumBet | 1/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 49 Casino_FightStadiumBet | 2/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 49 Casino_FightStadiumBet | 0/3 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 49 Casino_FightStadiumBet | 0/0 | 3/0 | 0.921 |  | aucune 0 | +0.92 (+0.9) | 0.0 | 1.00 |  | R | b |
| 49 Casino_FightStadiumBet | 0/1 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 49 Casino_FightStadiumBet | 0/2 | 5/0 | 0.921 |  | aucune 0 | +0.92 (+0.9) | 0.0 | 1.00 |  | R | b |
| 49 Casino_FightStadiumBet | 0/4 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 50 Casino_FightStadiumSelect | 4/0 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 50 Casino_FightStadiumSelect | 4/1 | 5/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 50 Casino_FightStadiumSelect | 0/0 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 50 Casino_FightStadiumSelect | 0/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 50 Casino_FightStadiumSelect | 1/0 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 50 Casino_FightStadiumSelect | 1/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 50 Casino_FightStadiumSelect | 2/0 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 50 Casino_FightStadiumSelect | 2/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 50 Casino_FightStadiumSelect | 3/0 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 50 Casino_FightStadiumSelect | 3/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 51 Casino_FightStadiumCoin | 0/0 | 0/0 | 0.929 |  | aucune 0 | +0.87 (+0.9) | 0.0 | 1.00 |  | R | b |
| 51 Casino_FightStadiumCoin | 0/1 | 2/2 | 0.929 |  | aucune 0 | +0.87 (+0.9) | 0.0 | 1.00 |  | R | b |
| 52 StartMenuFirst | 0/1 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 53 StartMenuSecond | 4/1 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 53 StartMenuSecond | 0/1 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 53 StartMenuSecond | 1/1 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 53 StartMenuSecond | 2/1 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 53 StartMenuSecond | 3/1 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 53 StartMenuSecond | 5/0 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 53 StartMenuSecond | 6/0 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 54 StartMenuSelect | 3/0 | 4/1 | 0.801 |  | observé 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 54 StartMenuSelect | 0/1 | 3/0 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R W | c |
| 54 StartMenuSelect | 0/2 | 3/0 | 0.881 |  | observé 1 | +1.31 (+1.3) | 0.0 | 1.00 |  | R W | c |
| 54 StartMenuSelect | 1/1 | 3/0 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 54 StartMenuSelect | 1/2 | 3/0 | 0.881 |  | observé 1 | +1.31 (+1.3) | 0.0 | 1.00 |  | R | b |
| 54 StartMenuSelect | 2/1 | 3/0 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 54 StartMenuSelect | 2/2 | 3/0 | 0.881 |  | observé 0 | +1.31 (+1.3) | 0.0 | 1.00 |  | R | b |
| 55 StartNameEntry | 0/0 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 55 StartNameEntry | 1/0 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 55 StartNameEntry | 2/0 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 55 StartNameEntry | 3/0 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 56 SaveOverwrite | 0/0 | 3/0 | 0.801 |  | observé 2 | +2.32 (+2.3) | 0.0 | 1.00 |  | R W | c |
| 56 SaveOverwrite | 0/1 | 3/0 | 0.881 |  | observé 2 | +1.31 (+1.3) | 0.0 | 1.00 |  | R W | c |
| 57 ShopRoot | 6/0 | 4/0 | 0.801 |  | observé 1 | +2.32 (+2.3) | 3.0 | 1.00 |  | R T | c |
| 57 ShopRoot | 0/0 | 4/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 57 ShopRoot | 1/0 | 4/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 57 ShopRoot | 5/0 | 4/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 58 ShopBuy | 6/0 | 4/0 | 1.002 |  | observé 1 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 58 ShopBuy | 6/1 | 1/1 | 2.460 |  | observé 2 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 58 ShopBuy | 6/2 | 1/1 | 2.460 |  | observé 32 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 58 ShopBuy | 6/3 | 2/2 | 2.460 |  | observé 32 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 58 ShopBuy | 0/1 | 3/0 | 0.801 |  | observé 2 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 58 ShopBuy | 1/1 | 3/0 | 0.801 |  | observé 3 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 58 ShopBuy | 2/1 | 3/0 | 0.801 |  | observé 3 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 58 ShopBuy | 3/1 | 3/0 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 58 ShopBuy | 4/1 | 3/0 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 58 ShopBuy | 5/1 | 3/0 | 0.801 |  | observé 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 59 ShopBuy | 6/0 | 4/0 | 1.002 |  | frère 1 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 59 ShopBuy | 6/1 | 1/1 | 2.205 |  | frère 12 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 59 ShopBuy | 6/2 | 1/1 | 2.205 |  | frère 32 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 59 ShopBuy | 6/3 | 2/2 | 2.205 |  | frère 32 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 59 ShopBuy | 0/1 | 3/0 | 0.801 |  | frère 12 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 59 ShopBuy | 1/1 | 3/0 | 0.801 |  | frère 12 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 59 ShopBuy | 2/1 | 3/0 | 0.801 |  | frère 12 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 59 ShopBuy | 3/1 | 3/0 | 0.801 |  | frère 12 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 59 ShopBuy | 4/1 | 3/0 | 0.801 |  | frère 12 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 59 ShopBuy | 5/1 | 3/0 | 0.801 |  | frère 12 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 4/0 | 4/0 | 1.002 |  | observé 1 | +0.00 (+0.0) | 2.8 | 1.00 |  | T | c |
| 60 ShopBuyInfo | 4/1 | 4/1 | 1.002 |  | observé 5 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 60 ShopBuyInfo | 4/2 | 3/0 | 0.881 |  | observé 10 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 4/3 | 3/0 | 1.002 |  | observé 8 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 60 ShopBuyInfo | 4/4 | 0/0 | 1.002 |  | observé+desc. 111 | +0.00 (+0.0) | 152.2 | 1.00 |  | T W | c |
| 60 ShopBuyInfo | 4/5 | 4/1 | 0.801 |  | frère 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 0/1 | 1/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 0/2 | 0/0 | 0.881 |  | observé 4 | +1.39 (+1.4) | 0.0 | 1.00 | 18 | R d | b |
| 60 ShopBuyInfo | 0/3 | 0/0 | 0.881 |  | observé 8 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 0/5 | 0/0 | 0.801 |  | observé 1 | +2.33 (+2.3) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 1/1 | 1/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 1/2 | 0/0 | 0.881 |  | observé 2 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 1/3 | 0/0 | 0.881 |  | observé 1 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 1/5 | 0/0 | 0.801 |  | observé 0 | +2.33 (+2.3) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 2/1 | 1/1 | 0.801 |  | frère 7 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 2/2 | 0/0 | 0.881 |  | frère 16 | +1.39 (+1.4) | 0.0 | 1.00 | 18 | R d | b |
| 60 ShopBuyInfo | 2/3 | 0/0 | 0.881 |  | frère 17 | +1.39 (+1.4) | 0.0 | 1.00 | 15 | R d | b |
| 60 ShopBuyInfo | 2/5 | 0/0 | 0.801 |  | frère 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 3/1 | 1/1 | 0.801 |  | frère 7 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 60 ShopBuyInfo | 3/2 | 0/0 | 0.881 |  | frère 16 | +1.39 (+1.4) | 0.0 | 1.00 | 18 | R d | b |
| 60 ShopBuyInfo | 3/3 | 0/0 | 0.881 |  | frère 17 | +1.39 (+1.4) | 0.0 | 1.00 | 15 | R d | b |
| 60 ShopBuyInfo | 3/5 | 0/0 | 0.801 |  | frère 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 61 ShopBuyInfo | 4/0 | 4/0 | 1.002 |  | frère 1 | +0.00 (+0.0) | 2.8 | 1.00 |  | T | c |
| 61 ShopBuyInfo | 4/1 | 4/1 | 1.002 |  | frère 7 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 61 ShopBuyInfo | 4/2 | 3/0 | 0.881 |  | frère 16 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 61 ShopBuyInfo | 4/3 | 3/0 | 1.002 |  | frère 17 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 61 ShopBuyInfo | 4/4 | 0/0 | 1.002 |  | frère+desc. 111 | +0.00 (+0.0) | 152.2 | 1.00 |  | T W | c |
| 61 ShopBuyInfo | 4/5 | 4/1 | 0.801 |  | frère 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 61 ShopBuyInfo | 0/1 | 1/1 | 0.801 |  | frère 7 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 61 ShopBuyInfo | 0/2 | 0/0 | 0.881 |  | frère 16 | +1.39 (+1.4) | 0.0 | 1.00 | 18 | R d | b |
| 61 ShopBuyInfo | 0/3 | 0/0 | 0.881 |  | frère 17 | +1.39 (+1.4) | 0.0 | 1.00 | 15 | R d | b |
| 61 ShopBuyInfo | 0/5 | 0/0 | 0.801 |  | frère 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 61 ShopBuyInfo | 1/1 | 1/1 | 0.801 |  | frère 7 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 61 ShopBuyInfo | 1/2 | 0/0 | 0.881 |  | frère 16 | +1.39 (+1.4) | 0.0 | 1.00 | 18 | R d | b |
| 61 ShopBuyInfo | 1/3 | 0/0 | 0.881 |  | frère 17 | +1.39 (+1.4) | 0.0 | 1.00 | 15 | R d | b |
| 61 ShopBuyInfo | 1/5 | 0/0 | 0.801 |  | frère 1 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 0/2 | 3/0 | 0.841 |  | aucune 0 | +1.85 (+1.9) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 0/3 | 4/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 0/4 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 1/2 | 3/0 | 0.841 |  | aucune 0 | +1.86 (+1.9) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 1/3 | 4/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 1/4 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 2/2 | 3/0 | 0.841 |  | aucune 0 | +1.85 (+1.9) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 2/3 | 4/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 2/4 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 3/2 | 3/0 | 0.841 |  | aucune 0 | +1.85 (+1.9) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 3/3 | 4/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 3/4 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 62 ShopSellItemList | 4/0 | 4/0 | 1.002 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 63 ShopSellItemInfo | 0/0 | 4/0 | 1.002 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 63 ShopSellItemInfo | 0/1 | 4/1 | 1.002 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 63 ShopSellItemInfo | 0/2 | 3/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 63 ShopSellItemInfo | 0/3 | 3/0 | 1.002 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 63 ShopSellItemInfo | 0/4 | 0/0 | 1.002 |  | frère+desc. 111 | +0.00 (+0.0) | 9.9 | 1.00 |  | T | c |
| 63 ShopSellItemInfo | 0/5 | 3/0 | 1.002 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 63 ShopSellItemInfo | 0/6 | 5/2 | 1.002 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 63 ShopSellItemInfo | 0/7 | 5/2 | 1.002 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 63 ShopSellItemInfo | 1/0 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 64 BankDeposit | 0/0 | 3/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 64 BankDeposit | 0/1 | 5/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 64 BankDeposit | 0/4 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 64 BankDeposit | 0/5 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 64 BankDeposit | 0/3 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 64 BankDeposit | 1/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 64 BankDeposit | 2/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 64 BankDeposit | 3/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 64 BankDeposit | 4/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 64 BankDeposit | 5/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 65 BankDraw | 0/0 | 3/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 65 BankDraw | 0/1 | 5/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 65 BankDraw | 0/2 | 5/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 65 BankDraw | 0/4 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 65 BankDraw | 0/5 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 65 BankDraw | 0/3 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 65 BankDraw | 1/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 65 BankDraw | 2/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 65 BankDraw | 3/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 65 BankDraw | 4/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 65 BankDraw | 5/0 | 2/2 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 66 ChurchRoot | 6/0 | 3/0 | 0.801 |  | observé 1 | +2.32 (+2.3) | 6.0 | 1.00 |  | R T | c |
| 66 ChurchRoot | 5/0 | 4/1 | 0.801 |  | observé 1 | +2.20 (+2.2) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 4/0 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 4/1 | 5/2 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 4/2 | 4/1 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 0/1 | 1/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 0/2 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 0/3 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 0/5 | 0/0 | 0.801 |  | aucune 0 | +2.33 (+2.3) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 1/1 | 1/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 1/2 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 1/3 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 1/5 | 0/0 | 0.801 |  | aucune 0 | +2.33 (+2.3) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 2/1 | 1/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 2/2 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 2/3 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 2/5 | 0/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 3/1 | 1/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 3/2 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 3/3 | 0/0 | 0.881 |  | aucune 0 | +1.39 (+1.4) | 0.0 | 1.00 |  | R | b |
| 67 ChurchWork | 3/5 | 0/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 68 Chapter2Status | 0/1 | 1/1 | 0.801 |  | observé 1 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 68 Chapter2Status | 0/2 | 0/0 | 0.801 |  | observé 1 | +2.33 (+2.3) | 0.0 | 1.00 |  | R | b |
| 69 TorunekoMiseban | 6/0 | 2/2 | 2.460 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 69 TorunekoMiseban | 0/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 69 TorunekoMiseban | 1/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 69 TorunekoMiseban | 2/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 69 TorunekoMiseban | 3/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 69 TorunekoMiseban | 4/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 69 TorunekoMiseban | 5/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 70 NENE_ItemView | 0/1 | 3/0 | 0.801 |  | aucune 0 | +2.32 (+2.3) | 0.0 | 1.00 |  | R | b |
| 70 NENE_ItemView | 0/2 | 3/0 | 1.002 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |
| 70 NENE_ItemView | 0/3 | 0/0 | 1.002 |  | frère+desc. 111 | +0.00 (+0.0) | 152.2 | 1.00 |  | T W | c |
| 71 FightStadiumAbort | 0/0 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 79 NetworkITEM | 0/0 | 4/1 | 0.801 |  | aucune 0 | +2.45 (+2.5) | 0.0 | 1.00 |  | R | b |
| 79 NetworkITEM | 0/1 | 1/1 | 1.202 |  | aucune 0 | +0.00 (+0.0) | 0.0 | 1.00 |  |  | a |

## Chiffres détaillés

### Descriptions recoupées et comprimées (`DESCRIPTIONS`, 111 à 112 chaînes françaises par cellule : descriptions d’objets du moteur)

| Cellule | Limite u | Chaînes | Modifiées | dont recoupées | dont comprimées | Dépassent en mode jeu | Dépassent en V | ts min |
|---|---|---|---|---|---|---|---|---|
| 7/0/1 MagicInfo | 148 | 112 | 17 | 11 | 0 | 11 | 0 | 1.00 |
| 10/0/4 ItemInfo | 148 | 111 | 17 | 11 | 0 | 11 | 0 | 1.00 |
| 38/2/3 BattleInfo | 56 | 111 | 101 | 95 | 18 | 98 | 0 | 0.75 |
| 46/4/3 Casino_GiftTarget | 148 | 111 | 17 | 11 | 0 | 11 | 0 | 1.00 |
| 60/4/4 ShopBuyInfo | 148 | 111 | 17 | 11 | 0 | 11 | 0 | 1.00 |
| 61/4/4 ShopBuyInfo | 148 | 111 | 17 | 11 | 0 | 11 | 0 | 1.00 |
| 63/0/4 ShopSellItemInfo | 148 | 111 | 6 | 0 | 0 | 0 | 0 | 1.00 |
| 70/0/3 NENE_ItemView | 148 | 111 | 17 | 11 | 0 | 11 | 0 | 1.00 |

### Poker (type 48, plaques de 72 u des boutons 4/0 à 4/5)

| Libellé | Largeur jeu | Largeur viewer | ts |
|---|---|---|---|
| Abandonner | 103,4 | 72,4 | 0,700 |
| Changer | 71,6 | 58,0 | 0,810 |
| Doubler | 68,6 | 58,0 | 0,845 |
| Garder | 59,7 | 58,0 | 0,972 |

La compression vise toutes les cellules du type 48, pas seulement les plaques : la cellule 2/0 (ligne d’information, alignée à droite) est comprimée de la même façon si son texte dépasse (supposé : effet de bord, non voulu).

## Textes propres à la visionneuse (absents du jeu d’origine, non jugés)

- Menu Échap (`dq4_pc/menus/pause.py`, textes `texts_en/pause.py`) : reprendre, états instantanés, affichage, son, commandes, retour au titre ; fenêtres noires et curseur du jeu, textes dessinés par la visionneuse.
- Historique (`dq4_pc/menus/ui_history.py`) : deux onglets (Dialogues, Combats), case « Favoris seulement » ; chaque entrée dans une boîte de dialogue du jeu (cadre 452 x 126 u) avec la police SE-GARRIR.
- Écran « Sauvegardes » (`dq4_pc/menus/saves_screen.py`) : exporter / importer, remplace « Sauv. cloud » ; dessiné dans le style des autres menus.
- Notifications (`toast`) : « État N enregistré / chargé / vide », « Sauvegarde impossible… », erreurs ; lignes d’information F1 (en haut à droite) ; bouton « Vitesse de combat » (`hud_mobile.py`).
- Saisie du nom et licence (type 80) : dessinées à la main, positions non retrouvées dans le code (mise en page inventée).
- Éditeur d’interface (aperçu), `menu_display.py` : menus simples en Pillow/pyglet pour les fenêtres sans mise en page.

## Non couvert ou non vérifié

- Aucune chaîne réelle observée pour les types 24, 27, 28, 34, 39, 41, 42, 44 à 53 (casino), 55, 62 à 65, 67, 69 à 71, 79 : position vérifiée seulement avec la sonde `Abcdefgh`.
- Ancre basse (anchor 7, 12 cellules) et `\n` final : le modèle n’est vérifié que sur capture mobile pour les ancres haute et milieu. Une chaîne qui finit par `\n` dans une cellule à ancre milieu ou basse (ex. 10/0/3 « Disparaît après une\nseule utilisation.\n ») compte une ligne vide en plus (décalage de 11,8 u si Unity l’ignore) : à vérifier sur capture.
- Les cellules à ancre milieu du type 4, 5, 30, 32, 46, 60, 61, 67 ont l’ancre décalée de +18 à +26 u du centre de la plaque (zone d’icône) : cohérent d’une fenêtre à l’autre, supposé voulu par la mise en page.
- Issue #138 (premier bouton d’une liste plus haut dans sa plaque) : les décalages de texte sont identiques d’une ligne à l’autre dans le banc, pas de cause côté visionneuse trouvée ; à voir sous Windows.
