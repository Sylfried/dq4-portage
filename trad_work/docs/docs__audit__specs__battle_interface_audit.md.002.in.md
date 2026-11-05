## 6. Type 66 = `Make_ChurchRoot` (« Église ») : parties manquantes

### Constat (établi)
- Export : 4 nœuds, 2 parties (cadre + titre ; bouton retour `Sub_ShopAbort`), mais **31 paramètres** qui citent les parties 2 à 30. `scan_missing_parts.py` : c'est le seul type dans ce cas (les boutiques 57-63 sont complètes).
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

Précautions communes : ne pas coder d'identifiants de nœud (ils changent à chaque régénération) ; le cache de l'utilisateur doit être régénéré avec le générateur actuel (`header.gen = 2`, absent des anciens `ui_layout.json`) ; retrouver les nœuds par structure (parties, `ib`, `mats[].part`). Rendu de contrôle : `xvfb-run -a python3 /tmp/specs/rend_combat.py 1 sortie.png` et `render_type.py`.

### P1. Église (type 66) : fenêtre inutilisable aujourd'hui
1. Dans `tools/ui_il2cpp/layout.py` (boucle `CODES = (-1, 0, 1, 2, 3, 4, 5)`), pour chaque code `func`, comparer la liste des nœuds / parties du `MenuPortItem` avant et après l'appel et exporter les nœuds créés dans `fx[code]['new']` (nœud, maillage, matériaux, `parts`/`ib`). Les paramètres existent déjà.
2. Dans `Fenetre.code` (ui_menu.py:240) : pour une entrée `fx[code]['new']`, rendre visibles les nœuds du code reçu et masquer ceux des autres codes. Le moteur n'envoie que les codes 0 et 1 (table 6).
3. Variante sans toucher à l'exporteur : dans `Fenetre.__init__`, pour `typ == 66`, construire les 4 / 5 boutons de la table 6 (maillage 9 découpes largeur + 32 x 56, matériau feuille 1 partie 7, texte centré cs 9,3925) et brancher `params[(no, 0)]` sur leurs textes ; ajouter les zones tactiles (`buttonId = no`, manette 16).

### P2. Combat, type 29 : secousse, rouge de la barre, curseur
1. `Fenetre.code(i, c)` : si `c == 8` et `self.typ == 29`, `self.secousse[i] = 8`. Les nœuds à déplacer = la plaque du membre `i` (la partie dont `ib[0]` est un `frame`, plus tous les nœuds dont `par` est cette racine : textes, barres, visage).
2. Ajouter `Fenetre.tick()` appelé une fois par image du jeu avant `Rendu.dessiner` (dans `_dessiner_menus`, window.py:1545, 30 Hz) : `m -= 1` ; si `m >= 0` ajouter `TABLE[m]` à `pos` des nœuds (`TABLE = [(-6,6),(6,-6),(6,-6),(-6,6),(6,6),(-6,-6),(-6,-6),(6,6)]`, indices 7 à 0) ; à `m == 0` appeler `_barre(ib, pt, ~cu['_v'])` pour la barre PV du membre (RedApply).
3. Curseur : compter 0,7 s en temps réel depuis le dernier `code(5, k)` ; basculer l'UV du nœud du curseur entre `uv_icone(infos[10], 2)` et `uv_icone(infos[10], 3)`.
4. Garder la mise à jour du rouge par la chaîne vide du moteur (ui_menu.py:215-218).

### P3. `StatusIconChanger` (types 4, 5, 20, 21, 46, 60, 61, 67)
1. `Fenetre.param_int` (ui_menu.py:185) : avant le `return`, `if cu.get('cls','').endswith('StatusIconChanger'): self._icone_etat(i, v); return`.
2. `_icone_etat(i, v)` : prendre la `i`-ième partie qui contient deux `ib` d'icônes de `partsNo == 13` ; `ib1`/`ib2` = ces deux icônes ; écrire dans `nd['uv']` à `ib['vtx'] + j` les quatre UV de `uv_icone(infos[13], v & 3, 0)` pour `ib1` et `uv_icone(infos[13], ((v >> 2) & 1) * 3, 0)` pour `ib2` ; mettre `nd['mats'][k]['color'] = couleurs[v >> 16]` pour le `k` dont `part == 13` (`Rendu.dessiner` lit déjà `mat['color']`, ui_menu.py:550 ; pas de changement de rendu).
3. Supprimer la référence à `s` dans la branche `ICityMap` de `param_int` (ui_menu.py:187).

### P4. `MonsterMarkList`
1. `window.py:959` : faire retourner à `_ui_x_monstres` la liste des abscisses (une par monstre du masque) en plus de (min, max), par exemple un second paramètre `liste=True`.
2. `Fenetre.disposer` (ui_menu.py:324) : pour chaque plaque avec `pl[i]['code'] == 2` et un masque, activer autant de nœuds de marque (les nœuds du type 31 dont `mats[0].part == 6`) que de monstres : `pos = [x, 0.0, -64.0]`, UV = `uv_icone(infos[6], 5 + i, 0)`, `act = True`.
3. `Fenetre.code(4, c)` (ui_menu.py:240) pour le type 31 : repasser tous les nœuds de marque à `act = False` (Reset).

### P5. Type 54 (cadre de titre)
Dans `Fenetre.code(3, c)` pour `typ == 54` : `self._cadre(self.parts[0]['ib'][0], 219 + c)` ; si `c == 2`, masquer les boutons 1 et 2 et mettre le bouton 0 à `z = -266,25` ; sinon bouton 0 à -185. Test : `render_type.py 54 sortie.png --fix54 0`. Laisser le bouton retour où il est (déplacement non résolu).

### P6. Rien à faire
Types 73, 77, 80 (écrans Unity hors table) ; `BattleBar` ; texte d'action sans cadre ; niveau « ? » (ce sont les comportements d'origine).

---

## 8. Reproduire (scripts de `/tmp/specs/`)

| Script | Rôle |
|---|---|
| `extract_res.py` (sous `xvfb-run -a`) | extrait `ui_MenuTexture.png`, `ui_Button.png`, police, `ui_frameData.bin` dans `/tmp/r3_res` |
| `regen_ui.py [sortie]` | régénère la mise en page (4 min 25 s) dans `/tmp/r3_layout/ui_layout.json` ; erreurs : 73, 77, 80 |
| `disasm_method.py <rva|nom> [fin]` | désassemble une méthode IL2CPP |
| `dasm_core.py`, `scan_got.py`, `scan_str.py`, `got.py`, `scan_got_il2.py` | moteur : désassemblage avec noms PLT, références à un emplacement GOT ou à un champ, valeur d'un GOT ; IL2CPP : méthodes qui chargent un emplacement GOT |
| `harness.py`, `t6.py`, `read_logfile.py` | combat forcé sans fenêtre et journal des messages moteur -> interface (`t6.py <slot> <images> <journal.pkl>`, `read_logfile.py <pkl> <ports> ...`) |
| `t7.py <slot>` | état des membres (`PlayerStatus`), cause du niveau « ? » |
| `t_calc.py`, `t_shake.py` | `CalcScreenPosition`, `NotchHeight`, table de secousse sous le tracer |
| `inv_statusicon.py`, `scan_missing_parts.py`, `frames.py <i0> <i1>` | inventaires sur `ui_layout.json` et `frameData` |
| `render_battle.py <slot> <png>`, `render_type.py <type> <png> [--fix54 N]` | rendu hors écran avec le rendu de la visionneuse (sous `xvfb-run -a`) |

Journaux de messages : `/tmp/r3_journal_s1.pkl` (slot 1 : Ragnar + Doc), `/tmp/r3_journal_combat2.pkl` (slot 4). Images : `/tmp/specs/img/rendu_combat_s1.png`, `comp_54_66.png`, `marques_part6.png`, `curseur_part10.png` ; `/tmp/r3_part13_zoom.png`, `/tmp/r3_part6.png`.

### Limites de cet audit (supposé / non vérifié)
- Cadence de l'original pour la secousse (8 images Unity : 30 Hz supposé) ; appel de `ForceUpdate` du curseur ; sens du booléen statique qui replace le bouton retour du type 54 ; sens du code 2 de `StartMenuSelect` ; sens de `isSpell` (oeil) ; formule du maillage des boutons de 177,1.
- Les valeurs de statut (`StatusIconChanger`) viennent de la lecture du code moteur ; elles n'ont pas été vérifiées en provoquant un état (mort, poison) dans le moteur.
- Aucune comparaison avec une capture du jeu mobile n'a été faite (aucune fournie).
