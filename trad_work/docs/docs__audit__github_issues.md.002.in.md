### 3.2 Issues fermées (16)

| # | Titre | Fermée | État réel |
|---|---|---|---|
| 1 | Sprites HD : lissage par shader + MSAA | 30/10 09:49 (PR #39) | **fait** : `hd.py:68` EPX x8. Les « styles lissés » ont ensuite été retirés (PR portage #41). MSAA : `postfx.py`, non vérifié sur GPU réel |
| 14 | Sortir du village : carte du monde | 30/10 10:10 (PR #43) | **fait** (PR portage #4, #9, #12) |
| 25 | Cadrage du projet et décisions de départ | 30/10 | historique M0 (voir `decisions.md`, D-01 à D-06) |
| 26 | Voie A : chargeur ELF + Unicorn | 30/10 | **fait** (`emu_core.py`) ; 61 constructeurs, `DevInit`, etc. |
| 27 | Protocole moteur -> Unity décodé | 30/10 | **fait** pour l'essentiel ; restes = #13 |
| 28 | Démarrer le moteur sans Unity, charger une sauvegarde | 30/10 | **fait** ; l'écriture reste à tester (#9) |
| 29 | Lecture des données Unity | 30/10 | **fait** (`fld.py`, `data.py`) |
| 30 | Premier rendu (église) | 30/10 | remplacé par #31 |
| 31 | Visionneuse temps réel pyglet 16/9 | 30/10 | **fait** ; retour : « ça fonctionne » |
| 32 | Portes et changement de carte | 30/10 | **fait**, amélioré par PR portage #3 |
| 33 | Sprites nets : sharp bilinear | 30/10 | **fait**, refait en PR portage #13/#23 |
| 34 | Cadrage 16/9 du village | 30/10 | **fait**, refait en PR portage #2/#12 |
| 35 | Messages : texte français du moteur | 30/10 | **fait**, refait en PR dq4-pc #69 (fenêtre de message d'origine) |
| 36 | Menus : file MenuPort, saisie clavier | 30/10 | **fait** ; retour : « un peu mieux, mais pas mal d'imperfections » (-> #22) |
| 37 | Dépôt GitHub, règles de travail | 30/10 | **fait** (`docs/workflow.md`) |
| 44 | Carte du monde : icônes (paquet 29) | 30/10 11:33 (PR #47) | **fait** (genres 19-20 ajoutés par PR portage #4 ; genre 18 voir G-034) |

### 3.3 Pull requests de dq4-pc (36)

#38 historique ; #39 sprites HD (ferme #1) ; #42 délégation git ; #43 carte du monde (ferme #14) ; #46 combat décor/monstres ; #47 carte miroir et icônes (ferme #44) ; #48 fond de combat ; #49 filets des tuiles ; #50 icônes à l'endroit ; #51 combat décor tourné 180° ; #52 monstres sans clignotement ; #53, #55 docs ; #54 F9 ordre des parties ; #58-#60 outils IL2CPP ; #61 pont Unity preuve 1 ; #62 combat d'après le code Unity ; #63 table des 38 paquets ; #64 F1 cadre translucide ; #65-#67 piste 3 combat et pause ; #68 fenêtres et menus d'origine ; #69 message d'origine, plaques de monstres ; #70 carte du monde dézoomée ; #71 monstres en mode immédiat, fondus ; #72 souris = tactile, flèches ; #73 sprites cachés, bulles Riseup ; #74 pixel perfect ; #75 musiques et bruitages ; #76 docs ; #77-#79 piste 3 et lanceur (changement de PC, dépôt `dq4-portage-unity`).

Phrases de Sylfried rapportées dans ces PR (à ne pas confondre avec des citations directes) : « dézommer la map », « mieux upscale TOUS les sprites 2D » (PR #70, 30/10 ~19 h 44) ; « sprites à l'envers » (PR #50) ; combats « buggés » (PR #51) ; bande noire à l'horizon (PR #48) ; F1 avec cadre translucide (PR #64).

## 4. Ce que je n'ai pas pu établir ici

- Le contenu de `dq4-portage-unity` et `dq456-traductions-fr` (accès non activé, volontairement non contourné).
- Si des issues ont été supprimées ou transférées avant la création de `dq4-portage` : l'API ne le dit pas.
- Si les commentaires « Retour de test pdc » reproduisent fidèlement ses messages : ils sont rédigés par Claude.
- L'état Windows/GPU de toute fonctionnalité (aucun accès).
- Si les 43 branches distantes de `dq4-portage` contiennent autre chose que ce qui a été fusionné : non comparées à `main`.
- Le contenu du fichier `Menu_Echap_DQ4_PC.xlsx` (spécification de Sylfried citée par les PR #25 à #27) : absent du dépôt.
- Si le jeton GitHub de la session a le droit d'écrire (non testé, volontairement : audit en lecture seule).

**Références documentaires périmées sur le suivi (établi, lecture des fichiers)** :
- `README.md:23` : « `dq4-pc` (ancien) … issues et pull requests (#1 à #78) » ; les PR vont jusqu'à #79 et les issues jusqu'à #57.
- `README.md:24` : « Prochaine issue : #1 (sprites en HD) » alors que #1 est fermée depuis le 30/10 (PR #39 de `dq4-pc`) ; mêmes mots dans `docs/history.md`, dont le tableau s'arrête au 30/10.
- `docs/workflow.md:6,27` : « description avec `Closes #<numéro>` », « branche supprimée après fusion » : aucune des 42 PR ne ferme d'issue et aucune branche n'est supprimée.
- `docs/viewer-notes-dq4-pc.md:85-86` : « Reste à faire : suivi dans les issues du dépôt » (G-145).
- `docs/technical-notes-dq4-port.md:70` : « Lien id de modèle 3D (8900…) -> objet Unity : non résolu », vrai pour les boss et autres modèles, faux pour le dragon (c1018, PR #42). `NT:144-145` liste encore comme « à décoder » des paquets déjà traités.
- `/home/claude/pjdocs/depot-github-dq4-pc.md` (copie du document du Projet) : décrit `dq4-pc` comme dépôt actif.

## 5. Recommandations sur les 27 issues ouvertes de `dq4-pc` (rien n'a été fait)

Recommandation de lecture, à décider par Sylfried ; aucune issue n'a été fermée, ouverte ni commentée.

| Recommandation | Issues | Raison |
|---|---|---|
| **Fermer, c'est fait** (7) | #2 (sauf `IBase`, G-090), #5, #7 (sauf coffres : lot #43), #10, #23, #22, #41 | preuves au §3.1 ; #22 et #41 sont obsolètes (cycles « Retours de HH h MM » et retrait des shaders flous) |
| **Fermer après confirmation de Sylfried** (2) | #40 (« à reconfirmer sur pdc, puis fermer »), #17 (son : vérifier les haut-parleurs sur le PC) | le code est fait, la confirmation manque |
| **Garder ouvertes : reste réel** (16) | #3, #4, #8 (manette), #9 (**prio:haute**, sauvegarde réelle), #11 (allocateur), #12 (clarifier 3.15), #13 (paquets 1, 6, 16, 17, 18, 27, 30, 33), #15, #16, #18, #19, #20, #21, #24, #45, #56 | voir les lignes correspondantes du §3.1 et `known_gaps.md` (G-xxx) |
| **Garder, à décider** (2) | #6 (toits : le jeu d'origine les rend-il transparents ? silhouette retirée par Claude, D-93), #57 (piste Unity en pause) | dépend d'une décision de Sylfried |

Total : 7 + 2 + 16 + 2 = 27, soit les 27 issues ouvertes (vérifié contre la liste du §3.1).

**Suggestion de procédure** (non appliquée) : le suivi actif est dans `dq4-portage` (issues activées, aucune ouverte). Soit y recréer les restes réels avec les étiquettes `type:` / `zone:` / `prio:`, soit assumer le suivi par PR et corriger `workflow.md` et le README (G-140, G-149). Dans les deux cas, supprimer les 42 branches fusionnées.
