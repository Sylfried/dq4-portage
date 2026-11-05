### 4.2 Portage

- `hud_mobile.py:18-20` : bouton `mode_carte` du HUD, colonne de gauche (0.4, 3), icône **fixe 19**, plaque procédurale, sans touche (`DECL 0`) ; visible seulement carte ouverte et `carte_deux_vues` (`visibles()` l.170, `window.py:1930`) ; `window.py:1937-1942` envoie `envoyer_menu(carte[25], 1, -1, 2)` (clé 2 = `PAD_U` : conforme). `_carte_ports` (`window.py:1336`) fusionne le type 23 dans le 22.
- Verdict : **approché** (fonction juste, apparence et position inventées) ; icône **fausse** hors petite carte du monde (20 sur la grande carte, 2 en ville). L'original n'est pas un bouton du HUD mais un bouton **dans la fenêtre** en bas à droite.

### 4.3 Corrections

1. Corriger `layout.py:99` : passer `typ - min(t pour R.tbl[t] == R.tbl[typ])`, régénérer `/tmp/uicache/ui_layout.json`. Le type 22 aura alors ses deux boutons (Retour (187.5, -366), Mode (187.5, -300), plaques 64 x 55.5, touches PAD_B/0x20 et PAD_U).
2. Icône du bouton Mode = valeur reçue du moteur (`param_int` du type 22, item 0) : 19 / 20 / 2, jamais 19 en dur.
3. Si le bouton de la fenêtre est cliquable, supprimer `mode_carte` du HUD ; sinon le garder avec icône dynamique et, de préférence, la vraie plaque (`Rendu.plaque`).
4. À mesurer : l'effet du correctif de `layout.py:99` sur les groupes 13..17, 35..37, 58/59, 60/61, 75/76 (même mécanisme, hors périmètre de cet audit).

### 4.4 Supposé

- Que `Make_Status` / `Make_BattleIM` / `Make_ShopBuy` / `Make_ShopBuyInfo` / `Make_NetworkRoot` testent leur 2e argument de la même manière : seul `Make_MapButton` a été lu ligne à ligne.

---

## 5. `PortalButton` (type 74)

- `Make_PortalButton` (0xCF71BC) crée un `MenuPortItem` vide ; la classe `PortalButton : MenuParts` (`Setup` 0xD0F408) fabrique un bouton à texture `Title/PotalButton` (128 x 128 x `s_scale 0.75` = 96 x 96), touche `0x2000000` / `0x200`, `Build(indent 4, écran 2 = RightTop, x = -70, y = 0, z = -60)`.
- Utilisé uniquement par `MaterielMenu_LOAD` (écran titre / chargement), `MenuPortSendPortal` (0x156490) envoie un message. **Ne fait pas partie du HUD de jeu.** Rien à reproduire dans `hud_mobile.py` (verdict : sans objet).

---

## 6. Autres valeurs « estimées / choisies » du portage

| Où | Valeur du portage | Ce que dit l'original | Verdict |
|---|---|---|---|
| `hud_mobile.py:26-31`, docs/notes-visionneuse:300, 305 | facteurs 1.25/1/0.75, 165, 85/256, 0.5, 0.15, fondu 0.4 | voir section 1.2 | à corriger |
| `hud_mobile.py:70-117` plaques (docs:220) | dégradé procédural, « ressemblance non mesurée » | plaque `Button` (feuille 1, partie 7), 9-tranches, coins de 16 unités, appuyé = uv + 0.1875 | approché : utiliser `Rendu.plaque` |
| `hud_mobile.py:18` positions par défaut (0.4, 1/3/12/14) | colonne gauche, pas de `g_pad_pos` | pos 1 : croix au centre, boutons à droite | choix de l'utilisateur (retour #36) ; option `g_pad_pos` non reliée |
| docs/notes-visionneuse:212 | pas des chiffres de dégâts 12.8 | `HoppingNumber`, `m_dps` 16 x 0.8 | déjà corrigé ; fidèle |
| docs/notes-visionneuse:229, 233 | oscillation du curseur doré « inventée » | pas de curseur dans les menus Unity : la sélection est l'état « appuyé » | reste inventé ; l'original n'a pas de curseur oscillant |
| docs/notes-technique:135 `NormalControl::execute` | « non vérifié » (bit 4 = `openMap`, sinon bit 5 = `openShopList`) | non relu dans cet audit (le moteur envoie bien les icônes 2 / 19 / 20 aux boutons) | inchangé |
| docs/notes-technique:87 | ItemNumCTRL, ICityMap « non reproduits » | ItemNumCTRL entièrement décodé (section 2) ; ICityMap : tout reproduit sauf le code 4 | à mettre à jour |
| docs/notes-visionneuse:296 | ancrage de la plume « pas vérifié » | confirmé : `AddIcon(Vector3.zero, 31, true, 0.5)`, origine = coin bas-gauche | à mettre à jour (établi) |

---

## 7. À corriger par ordre de priorité

### A. Établi (preuve), numérique

1. **Bug du pipeline `tools/ui_il2cpp/layout.py:99`** : passer `type - premier indice du même délégué` (preuve : `sub w2, w21, w0` en 0xCE43DC). Régénérer `ui_layout.json`. Effets immédiats : type 22 (bouton Mode dans la fenêtre), puis groupes 13..17, 35..37, 58/59, 60/61, 75/76 à contrôler.
2. **ItemNumCTRL (type 9) absent** : implémenter `Changer(v)` dans `ui_menu.Fenetre.param_int` (quantités des listes d'objets : actuellement jamais affichées). Règle : v < 2 -> vides ; sinon dizaines = `(v / 10) % 10` (icône 16 x d, ou 1), unités = 16 x (v % 10).
3. **Géométrie de la croix** : `ECHELLE_CROIX = (1.225, 1.0, 0.775)` ; `DIAM_CROIX = 161.28` ; `RAYON_PASTILLE = 104/256 = 0.40625` ; `ZONE_MORTE = 0.124` ; `COURSE_BOULE = 0.4526` ; zone de prise 1.178 x le rayon.
4. **Boule orange et halo** : pas en cours de déplacement, seulement en clignotement tutoriel ; seule la pastille du secteur tenu s'allume.
5. **Fondu de la croix à 40 %** : **inventé** (constantes mortes `MOVE_WAIT_TIME` / `MOVE_LIMIT_ALPHA`), à retirer ou à garder comme option PC assumée (non fidèle).
6. **Icône du bouton Mode** : 19 / 20 / 2 selon le moteur (petite carte du monde, grande carte, ville) ; position d'origine dans la fenêtre (187.5, -300), plaque 64 x 55.5, touche `PAD_U`.
7. **Plan et marqueur de la carte** : rectangle x -223..222.5, z 398..63.875 ; marqueur `-223 + 1.740234 px`, `398 - 1.740234 py` (écart <= 2.5 unités : correction mineure).
8. **Code 4 d'`ICityMap`** : afficher la croix rouge (feuille 5, case 3, 21.6) en `(-227 + lo x 1.7578, 402 - hi x 1.7578)`.
9. **`ui_menu.py:187`** : `s` non défini (NameError latente) à supprimer.
10. **Plaques des boutons du HUD** : vraie plaque 9-tranches (`Rendu.plaque`) et formats 72 x 64 (Carte, Commandes), 63 x 56.8 (Discussion) au lieu du carré de 71.1.

### B. Supposé (à confirmer par capture Android ou lecture supplémentaire)

1. Pas d'anneau flottant : la boule suit le doigt, l'anneau reste fixe (aucun code ne le déplace) ; à vérifier par une capture d'appui hors du centre.
2. Absence de fondu : vrai pour le code C# de `TouchPad`, pas prouvé pour une animation extérieure.
3. Ancrage bas-gauche de la croix rouge (code 4) par analogie avec la plume.
4. Effet de la correction 1 sur les autres groupes de types (seul `Make_MapButton` a été lu en détail).
5. Défaut `g_pad_pos = 1` (croix centrée, boutons à droite) : l'option « Position de la croix » n'est pas branchée ; le retour #36 demande les boutons à gauche, donc à traiter comme préférence, pas comme erreur.

---

## 8. Reproduction

Tout se lance sans rien modifier dans le dépôt :

- `bash /tmp/specs/scripts/audit_reproduire.sh` : régénère dans `/tmp/r4_repro/` les listings annotés de toutes les méthodes citées (désassemblage ARM64 avec noms de méthodes, constantes flottantes, chaînes, champs), les maillages de la croix (`audit_pad_meshes.py`), le balayage des appels moteur vers l'interface (`audit_scan_itemparam.py`) et `audit_values.py`.
- `python3 -I /tmp/specs/scripts/audit_valeurs.py` : recalcule tous les nombres dérivés de ce document (diamètres, rapports au rayon, positions de la croix, boutons, plan, marqueur, chiffres).
- `DQ_IL2=/home/claude/il2 python3 -I /tmp/specs/scripts/audit_dis.py <RVA début> <RVA fin>` : désassemblage annoté d'une plage de `libil2cpp.so`.
- `python3 /tmp/specs/scripts/audit_eng.py dis|sym|xref ...` : même chose pour le moteur `libdq4core.so` ; `audit_scan_itemparam.py [sous-chaîne]` : appels du moteur à `setItemParam (0x225070)` et `setItemCode (0x225060)` avec leurs immédiats et leur fonction appelante (`audit_scan_itemparam.py MapButton`, `ImageMap`).
- Images : `/tmp/specs/img/icons_sheet3.png`, `icons_sheet3b.png` (feuille 3, icônes 0..31), `icons_sheet5.png` (feuille 5, croix rouge du code 4), `button_sheet12.png` (chiffres de la feuille 12).
