## 7. Notes à fusionner dans les documents du Projet

À reprendre dans `technical-notes-dq4-port.md` et `viewer-notes-dq4-pc.md` :
1. **Table des paquets avec statut** (§1) : remplacer la ligne « Table des paquets -> fonctions Unity » par la table avec les cinq statuts et les émetteurs.
2. **Paquet 33 `map_color_rate`** (§1.1) : émis à 171 / 529 cartes ; `cmd_map_color_rate` (0xD14E44) = `Field.SetColor(r, g, b, 1)` ; remplace la mention « `mlb1a` seulement » (`notes-technique:233`).
3. **Périmé** : « Lacunes : classes `IBase` personnalisées non reproduites » (`notes-technique`, section Interface d'origine) : les cinq classes sont portées (`ui_menu.py:199-413`).
4. **Parties du moteur** : 3 départ, 0xc ville, 0xd combat, 0xe carte du monde, **0xf casino, 0x10 bestiaire** (la visionneuse ne connaît pas 0xf ni 0x10) ; `Global::startCasino` ← `cmd_mini_game` ; `setMinigame(0)` = poker `ev04`, autre = machine à sous `ev05` ; `startBook` ← `TownMenuItemSelectCommand::menuUpdate` ; `startSurechigai` ← `cmd_change_surechigai_part`.
5. **Entrée clavier des menus** : les boutons de manette 0x2 / 0x1 (▲ ▼ de la mise du casino, quantités) sont inaccessibles au clavier si la fenêtre n'a pas de grille moteur.
6. **Pas de `startTown` pour tester l'arrivée** : le héros garde la position de la carte précédente.
7. **`g_Option + 5`** imposé par la visionneuse est enregistré dans les sauvegardes du jeu (§4).
8. **Mots de touches** : le moteur ne met le bit « A » du terrain que si `arg2 == 0x100` exactement (`Global::NativeExec`, 0x17d3d8-0x17d400) ; 0x400 → 0x20, 0x800 → 0x40, 0x1000 → 0x80, 0x2000 → 0x400 ; les menus du casino (`MaterielMenu_SLOT::menuUpdate`, `MaterielMenuPokerSelectcard`, `…Changecard`, `FIGHT_STADIUM::messageUpdate`) lisent ce mot directement (`scan_keyword.py`).
