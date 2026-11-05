## Agent ac898832ce067746b — 02/11 02:59

RAPPORT agent « entrees » (worktree /home/claude/wt-entrees, branche agent-entrees, base 08f5785). Arbre propre. Aucun push. (Renvoi du rapport : le premier envoi n'a peut-être pas été reçu.)

COMMITS
- c4e6378 Entrees (WIP) : clic molette, souris après clavier, infos F1 à droite
- 57dbcfb tests souris après clavier (menu Échap), aides des commandes, geste molette annulé sans bouton
- cb46c17 ligne d'init d'origine conservée (moins de conflits)

ÉVALUATION DU TRAVAIL DU PRÉDÉCESSEUR
Gardé : `inputs.py` (logique pure), les branchements `on_mouse_*` et le geste molette.
Corrigé :
- Un `print('DBGMOL')` de débogage est retiré.
- `_camera_pilotable` et `_zoom_possible` ignoraient licence, écran Sauvegardes, saisie du nom et carte ouverte.
- `pivoter` faisait un tour complet de lacet avant de borner quand le lieu limite la rotation.
- Le point C (F1) n'était pas branché : `zone_infos` existait mais n'était utilisée nulle part.

A. CAMÉRA À LA SOURIS (clic molette)
- Glisser molette maintenu : horizontal = lacet, vertical = inclinaison. Mêmes variables (`self.lacet`, `angle_cam`, `reg['angle_camera']`), mêmes bornes (`CAM_ANGLE_MIN/MAX`, `cam_limite`) et mêmes sens que les flèches (droite = flèche droite, haut = flèche haut).
- Sensibilité en constantes nommées dans `inputs.py` : `CAM_SOURIS_LACET` = 180° et `CAM_SOURIS_ANGLE` = 120° par hauteur de fenêtre. Elle ne dépend donc pas de la résolution. Le sens est inversable en changeant le signe.
- Seuil de 4 px (`SEUIL_GLISSE`) entre clic et glisser. Au franchissement du seuil la caméra ne saute pas. Un glissement annule un recentrage animé en cours.
- Clic molette simple : `recentrer_camera()`, la même animation que « Touche spéciale + touche caméra » (factorisée).
- Ctrl + clic molette : `regler_zoom(100 / DEFAUT['distance_camera'])`, sans toucher à la direction. « Ctrl » = le modificateur pyglet OU la « Touche spéciale » des réglages.
- Contextes : le glisser et le clic n'agissent que si `_camera_pilotable()` (= `_terrain_libre()` + ville + pas `cam_bloquee` + ni licence, ni Sauvegardes, ni saisie du nom), donc comme les flèches. Le zoom (`_zoom_possible`) agit en ville et sur la carte du monde, hors message, menu, carte ouverte, Pause, titre, licence, Sauvegardes, nom.
- Changement de comportement de la molette de zoom : elle ne zoome plus sur le titre, la licence, les Sauvegardes, la saisie du nom ni la carte ouverte (avant, seuls `msg_visible` et `menu_actif` étaient testés).
- Le bouton du milieu sort de `on_mouse_press` / `on_mouse_release` avant tout le reste. Il ne déclenche donc aucun clic gauche simulé, ni menu, ni éditeur d'interface, ni tchat. Avant, `Pause.clic` traitait le bouton du milieu comme un clic gauche. Il est aussi ignoré pendant que la croix ou un bouton du jeu est tenu.
- Si un mouvement sans bouton arrive pendant un geste, celui-ci est abandonné (relâchement perdu).
- Aides mises à jour dans `pause.py` : infobulle des 4 touches caméra, « Touche spéciale », « Distance caméra » et « Infos à l'écran ».
- Harnais (`fenetre._touches_test`) : `%x%y` appui du bouton du milieu, `&x&y` glisser, `*x*y` relâchement. Pour Ctrl : `+LCTRL` / `-LCTRL`. Le survol seul existait déjà (`@x@y@2`).

B. SOURIS « INUTILISABLE ~1 s » APRÈS LE CLAVIER
Cause : aucun délai temporel n'existe dans le code (pas de minuterie, pas de curseur masqué). Ce sont des seuils de mouvement qui font ressembler la souris à un instrument « mort » :
1. `Pause.survol` (menu Échap, base) comparait chaque événement au précédent (déplacement < 3 px en Manhattan), `pos_souris` étant remis à jour à chaque appel. Une souris lente, qui envoie 1 à 2 px par événement, ne reprenait donc jamais la main avant un geste rapide. Le même test laissait passer un tremblement de 2-3 px. Et `sortie()` mettait `pos_souris` à None, ce qui ignorait le premier événement.
2. Jeu : `souris_gel` (6 px Manhattan, après le retour du menu Échap seulement) ; `on_mouse_motion` passait en mode souris sur n'importe quel événement, même nul.
Correction à la racine : `entrees.GardeSouris`, mémoire unique clavier/souris.
- Chaque touche fige la position de référence du pointeur (`on_key_press`, `Pause.touche`, `Pause.ouvrir`, `pause_jeu(False)`).
- Le survol et le mode souris reprennent dès que l'écart CUMULÉ depuis cette référence atteint `TOLERANCE_SOURIS` = 4 px (4 événements de 1 px).
- Un clic agit toujours et immédiatement, et rend la main à la souris (`garde.clic()`). Position inconnue (pointeur hors fenêtre) : le premier mouvement compte.
- `souris_gel` n'est plus lu (l'attribut reste dans la ligne d'init d'origine, volontairement non touchée : à supprimer à la fusion si souhaité).
Protection conservée, avec sa raison : une souris au repos sous un menu qui s'ouvre ne doit pas voler la sélection au clavier. Cas connu des notes : Échap sélectionnait « Sauvegarde rapide ». La tolérance couvre le tremblement du capteur ou de la main. Les événements nuls sont déjà filtrés par pyglet Win32 si ma mémoire du code est juste (non vérifié ici).
Test : `tools/test_entrees.py` (37 tests, sans fenêtre). Les tests Pause échouent sur le code de base (je l'ai vérifié sur un `git archive` de 08f5785 : 3 échecs) et passent sur la nouvelle version.

C. INFOS F1 EN HAUT À DROITE
- F1 = action `infos` : bloc de lignes d'information (lieu, fenêtre, réglages, son, performances) dans un cadre noir translucide, qui était en haut à gauche. Ce n'est PAS l'éditeur « Interface », dont le panneau est déjà en haut à droite par défaut.
- Le bloc n'avait aucune position enregistrée ni déplaçable : pas de migration et pas de clé de réglage. Le point du brief sur « position déplacée / double clic / Rétablir l'interface » ne s'applique pas. Je n'ai pas ajouté d'option (Sylfried les supprime). Si tu le veux déplaçable, c'est un autre chantier.
- `_marge_aide` renvoie `(côté, largeur)` via `entrees.zone_infos` : côté droit par défaut, côté gauche si la colonne d'interface est à droite (`--ui-pos droite`). La largeur reste la marge libre à côté de la colonne d'interface, avec un minimum de 260 px. Le cadre est collé à `largeur - 4`, et sa largeur ne fait que croître tant que F1 est affiché (et est réinitialisée si la mise en page change), pour que le texte ne vibre pas.
- Aucun changement à `settings.py`. `test_interface_settings.py` et `test_interface_panel.py` passent sans modification (12 et 10 tests OK).

ÉTABLI / SUPPOSÉ / NON VÉRIFIÉ
- Établi (lu dans le code ou mesuré) :
  - 37 tests de `test_entries.py`, ainsi que `test_reglages_interface` (12), `test_panneau_interface` (10), `test_pause_pages` (15), `test_reglages_son_texte` (7) et `test_mode_fenetre` (18, 1 ignoré) passent.
  - Capture harnais en ville (slot 1, 1280x720) : un glissement molette donne « rotation 15 °, angle +10 ° », conforme aux constantes. Le bloc F1 est bien en haut à droite en 1280x720, en 2560x1080 (21:9) et en 960x720 (4:3, texte replié à 260 px).
  - Le glisser, le clic et Ctrl+clic sont sans effet sous un message ou un menu du jeu (vérifié en harnais : le menu de l'église bloquait le glisser) et dans tous les cas de la liste (tests avec un `Jeu` factice qui utilise les vraies méthodes).
- Supposé :
  - La cause B décrite ci-dessus : établie par lecture et reproduite par un test, mais jamais observée sur ton PC. Il se peut qu'une part de la gêne vienne d'ailleurs.
  - Une vraie molette Windows envoie `MIDDLE` dans `on_mouse_press/drag/release` ; Ctrl arrive dans `modifiers`.
- Non vérifié :
  - Sensation du glisser molette sur une vraie souris Windows : sensibilité, sens, seuil de 4 px.
  - Clic simple (recentrage animé) et Ctrl+clic (zoom 100 %) en harnais : leur prise en compte est testée par les tests unitaires mais pas vue en capture.
  - Le run combiné `ed` (caméra + survol du menu Échap, captures `/tmp/m_ed_b*.png`, journal `/tmp/out_ed.txt`) était encore en file d'attente derrière le verrou xvfb au moment du rendu. Je n'ai pas vu ses images ; elles peuvent exister maintenant.
  - Aucune capture du survol lent dans le menu Échap.
  - Pas de capture de F1 en 1080p ni en plein écran (la logique est la même).
  - Le bloc F1 se superpose au panneau « Interface » de l'éditeur (aussi en haut à droite) quand les deux sont visibles : acceptable, mais pas vu.

FICHIERS TOUCHÉS
- `dq4_pc/entrees.py` (nouveau)
- `dq4_pc/fenetre.py`
- `dq4_pc/pause.py`
- `tools/test_entrees.py` (nouveau)
- `tools/test_mode_fenetre.py` : une ligne, `faux_jeu` reçoit `souris=(0,0), garde_souris=GardeSouris()`, car `on_key_press` mémorise maintenant la position du pointeur.
Captures utiles : `/tmp/m_ea_b45.png` (rotation 15° et angle +10° avec F1 en haut à droite), `/tmp/m_ef_b40.png` (21:9), `/tmp/m_eg_b40.png` (4:3).

PIÈGES DE FUSION (zones de `window.py`)
- Import `entrees as EN` (ligne 23).
- `__init__` : nouvelle ligne `garde_souris` / `molette` après la grosse ligne `self.lacet...`, laissée intacte. Ligne `self.aide = ... aide_larg, aide_cle` modifiée.
- Nouveaux : `_zoom_possible`, `_camera_pilotable`, `recentrer_camera`, `_ctrl_actif`, `_molette_appui` / `_glisse` / `_relache`. Ils sont insérés avant `on_mouse_scroll`, dont la dernière ligne change.
- `on_mouse_drag` (3 lignes), `on_key_press` (1 ligne `garde_souris.clavier`), `pause_jeu` (remplacement de la ligne `souris_gel`).
- `on_mouse_press` (2 lignes), `on_mouse_motion` (garde + annulation du geste molette + suppression du bloc `souris_gel`), `on_mouse_release` (1 ligne).
- `_maj_camera` : un appel `recentrer_camera()` remplace les 2 lignes de remise à zéro.
- `_marge_aide` et `_dessiner_aide` réécrits.
- `_touches_test` : docstring et 3 événements.
- Dans `pause.py` : import, `ouvrir`, `touche`, `survol`, nouveau `_garde`, textes d'aide (Distance caméra, Commandes) et variable `infos` dans `_e_commandes`.

NOTES DE DOC À FUSIONNER (notes-visionneuse, « Retours de 02 h 12 (#43) »)
- Entrées. Clic molette (`fenetre._molette_*`, `entrees.GesteMolette`) : simple = direction de la caméra remise (animation de recentrage des flèches) ; Ctrl (ou Touche spéciale) + clic = zoom à 100 % sans toucher à la direction ; maintenu + déplacement = rotation et inclinaison (`entrees.pivoter`, mêmes bornes et sens que les flèches ; constantes `CAM_SOURIS_*`, `SEUIL_GLISSE`). Actif seulement quand les flèches le sont (le zoom aussi sur la carte du monde). Harnais : `%x%y`, `&x&y`, `*x*y`, `+LCTRL`.
- Souris après clavier. `entrees.GardeSouris` remplace `souris_gel` et le seuil par événement du menu Échap. La référence est figée à chaque touche, le survol reprend à 4 px cumulés (`TOLERANCE_SOURIS`), un clic agit toujours. Les tests échouent sur 08f5785. Cause établie par lecture, non vue sur Windows.
- F1 : le bloc d'infos est en haut à droite (`entrees.zone_infos`), à gauche seulement si la colonne d'interface est à droite. Aucune position enregistrée, aucun réglage ajouté.
- Test : `tools/test_entrees.py`.

---

## Agent ab93c153d22168574 — 02/11 03:01

RAPPORT : audit issues GitHub et décisions (reprise). Lecture seule respectée : dépôt resté sur main 08f5785 et propre ; rien écrit sur GitHub, dans le Projet ni dans la mémoire ; `add_repo` non appelé ; `claude/piste-3-projet-unity.md` non ouvert ; sauvegardes, patch FR et fichiers des autres agents non touchés.

FICHIERS (révisés, pas refaits de zéro) : /tmp/audit/github_issues.md (27,7 Ko), /tmp/audit/decisions.md (61 Ko), /tmp/audit/lacunes_connues.md (38 Ko).

1. VOLUMES
- Issues (établi, REST) : `dq4-portage` 0 issue (issues activées, 10 étiquettes GitHub par défaut, 0 jalon, 43 branches distantes jamais supprimées), 42 PR « Avance #N » fusionnées, 0 commentaire. `dq4-pc` (historique) 43 issues : 27 ouvertes, 16 fermées ; 36 PR ; 9 commentaires. Recommandation par issue ouverte au §5 de github_issues.md : 7 à fermer (#2, #5, #7, #10, #22, #23, #41), 2 à fermer après confirmation (#40, #17), 16 réelles, 2 à décider (#6, #57).
- Décisions : 128 identifiants D-xx. Sources : 7 lus directement dans la transcription [T] (messages de 02:27 à 02:38, tous nouveaux), citations recopiées par Claude [C] (message de 23:24 en entier, phrases des lots de 18:02 et 20:46, message de 02:12), retours rapportés dans les PR [R], 10 entrées de la mémoire [M] (D-01 à D-10), choix de Claude [K] séparés. 21 contradictions (C-1 à C-21).
- Lacunes : 161 lignes (144 lacunes + 17 demandes du lot #43). Classement provisoire : à vérifier 97, oubli 19, décision 17, bug 12 (une ligne peut porter deux tags).

2. LES 10 LACUNES LES PLUS GRAVES POUR LA JOUABILITÉ (supposé : classement de lecture)
1. G-092 boutiques (achat, vente, quantité) : codées, jamais jouées.
2. G-120 sauvegarde réelle à l'église puis rechargement : jamais confirmée sous Windows (issue #9, prio:haute).
3. G-093 casino, banque, église : aucun test documenté (à trancher par l'agent couverture ; le code ne nomme que 4 parties).
4. G-031 bateau, ballon et autres transports : jamais étudiés.
5. G-001 / G-023 rendu Windows/GPU réel et comparaison au mobile : jamais faits.
6. G-044 allocateur sans libération : `MemoryError` possible sur longue session.
7. G-070, G-071, G-078 boss, groupes, effets de sorts, victoire / montée de niveau / game over : non vérifiés.
8. G-041, G-042, G-043, G-052, G-069 scènes d'histoire non rejouées : paquets 1, 6, 16, 17, 18, 27, 30 et 33 non traités, FEAN, auberge, chapitres, générique.
9. G-055 murs invisibles et escalier de `dbout` ; G-079 retour au titre depuis un combat ou une boutique puis nouvelle partie.
10. G-099 / G-098 clavier du nom inventé, nom refusé non testé, « Revenir à l'écran titre » qui efface la sauvegarde auto.

3. CONTRADICTIONS DÉCISIONS / ÉTAT (établi par lecture du code)
- C-1 plein écran exclusif encore présent (`settings.py:78`, `window.py:272`) vs D-30. C-2 option `correction_bords` encore présente (`pause.py:292`) vs D-31. C-3 plaque « Sauvegarde auto » cachée vs D-32. Idem pour D-46 (`pause.py:286`), D-48 (`pause.py:424-425`), D-49, D-17, D-34 : aucune demande de 02:12 à 02:38 n'est sur main.
- C-19 : D-47, le défaut de `camera_centree` est déjà True dans le code (`settings.py:28`) ; le False viendrait du `reglages.json` (non lu).
- C-10 / C-14 : D-14 « le jeu prend le dessus, valable pour tout » n'a qu'un précédent codé (la caméra, `window.py:987-990`) ; le reste n'est pas inventorié.
- C-6 : « le moteur ne se modifie pas » vs patches mémoire. Deux sont demandés par Sylfried (D-123, D-124), les autres sont de Claude.
- C-21 : il a cité un exemple de choix inutile de l'éditeur, Claude en a retiré 18.
- C-7 : ciel du titre « garder tel quel » vs « pattern répétitif ». C-11 / C-12 : docs et README périmés (suivi par issues, `Closes #`, « prochaine issue #1 »).

4. CORRECTIONS À CE QUE LE PRÉDÉCESSEUR OU LE BRIEF AVAIT
- ERREUR À NE PAS RÉPÉTER : le message de 02:37 dit que la vitesse du combat change animations et dialogues, mais PAS la musique ni les bruitages (D-18). Je l'avais d'abord lu à l'envers, c'est corrigé dans les fichiers.
- Le message de 23:24 existe en entier (brief42) : il n'était pas « tronqué ». Il contient une décision de principe absente du registre : montrer l'envers du décor si le mobile le montre (D-29d).
- Sylfried a bel et bien demandé de revoir les shaders flous (D-131) : le retrait de « Bicubique » et « Régions lissées » répond à sa demande, même si le choix des deux shaders est de Claude. Le débordement des textes français est de son côté un non-sujet pour le portage (D-133).
- Références « notes l.N » ambiguës, toutes remplacées par NV:N / NT:N. Corrigé aussi : PR #36 (facteurs de la croix : prouvés ou retirés dans l'audit de #39), 30 Hz (moteur établi, fondus d'Unity supposés), lignes d'`emu_core.py`.

5. CE QUE JE N'AI PAS PU LIRE (non vérifié)
- Dépôts `dq4-portage-unity` et `dq456-traductions-fr` (accès non activé, volontairement non contourné), `claude/piste-3-projet-unity.md` (consigne).
- `Menu_Echap_DQ4_PC.xlsx` (absent du dépôt).
- Les messages de Sylfried antérieurs à la compaction ne me sont connus que par le brief, les missions et les PR : le lot de 20:46 compte 21 points, je n'ai le texte que d'environ seize ; ceux de 18:02 sont partiels.
- L'outil de lecture du Projet n'est pas disponible pour moi : j'ai utilisé les copies `/home/claude/pjdocs/`.
- Aucun accès Windows/GPU, ni à son `reglages.json`, ni à ses sauvegardes. GraphQL indisponible, REST seulement.
- Les anciennes conversations n'ont rien donné d'utile (Unity et patch FR seulement).

6. FAITS ISSUS DE LA MÉMOIRE
Seulement D-01 à D-10 (§1 du registre, marqués [M]) : projet 16/9 d'abord, APK déjà patchés FR, voies A/B/C, projet séparé du patch FR, Claude gère tout git, trois dépôts côte à côte, piste Unity en pause. La mémoire s'arrête au 30/10 22:50 pour le portage : elle ne contient aucune décision du 31/10 au 02/11. Aucune instruction suspecte trouvée dans la mémoire ni dans les documents.

7. À MÉMORISER (décision de la session principale ; source entre crochets)
- Le jeu prend le dessus sur les réglages du joueur quand un script change la valeur, « valable pour tout » [message 02:12].
- Plein écran exclusif supprimé, F11 / Alt+Entrée alternent plein écran et fenêtré [02:12].
- Ce qui doit être toujours actif n'est pas une option : correction des bords [02:12], lissage des textures [02:27].
- Combat : trois vitesses Normal / Rapide / Très rapide, sans accélérer musique ni bruitages [02:35, 02:37].
- Historique des messages avec le nom de qui parle [02:36].
- F1 en haut à droite par défaut [02:14].
- Règle « ne jamais supprimer un bouton non cité » [23:24].
- Zone portrait centrale = vue du téléphone ; montrer l'envers du décor si le mobile le montre [23:24, 02:12].
- Les textes qui débordent relèvent du projet de traduction [20:46].
- Sylfried délègue souvent le détail (« je te laisse choisir », « ne le fais que si c'est pertinent ») : Claude décide, puis le dit.
- Fuseau Europe/Paris (UTC+1), établi par la transcription.

---
