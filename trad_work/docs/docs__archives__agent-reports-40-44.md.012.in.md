- agent-coffres, agent-libelles, agent-options, agent-titre2 : aucun conflit (window.py se fusionne automatiquement avec tous).
- Après fusion : grep de « Vitesse de l'accélérateur » (les branches des autres agents l'ont encore dans leurs copies de test_pause_pages et d'aides ; tout nouveau test écrit avec l'ancien libellé échouera) ; `HM.NOMS_ED` compte maintenant 5 éléments (tests qui comptent les rectangles) ; relancer les 3 tests de logique ci-dessus.

=== À retenir (observations de session, pas de la mémoire) ===
Les captures sous Xvfb passent par un verrou unique /tmp/xvfb.lock : une exécution a attendu 15 à 30 minutes derrière les autres agents. Les tests de logique tournent sans écran (pyglet headless).

---

## Agent a3199f5d827423698 — 02/11 04:30

RAPPORT FINAL, lot PR #43, agent « histo » : historique des messages

Branche `agent-histo`, base 08f5785, un commit : **bb9ca7f**. Arbre de travail propre (seul `dq4_pc/__pycache__/` est ignoré). `dq4_pc/libelles.py` n'est PAS commité : il n'est pas dans la branche, je l'ai copié dans `/tmp/histo_libelles/` pour les tests et captures.
Rien n'a été poussé, aucune PR, aucun changement de branche, `/home/claude/dq4-portage` et les sauvegardes de l'utilisateur n'ont pas été touchés (les tests écrivent dans `/tmp/sv_*`).

## Les 5 points

**1. Capture exactement une fois, texte tel qu'affiché**
- Point de passage unique : `TextBuffer::cat` (lib+0x157874), appelé une fois par page de message, macros déjà résolues. x1 = texte UTF-8, x2 = nom du locuteur donné par le moteur (le `@a<nom>@b` du .mpt).
- Le crochet (`uc.hook_add(UC_HOOK_CODE, …)`) est posé dans `Moteur.__init__`, avant les premiers pas : après, le cache de blocs traduits l'ignorerait.
- On note le texte nettoyé (`@cN`, caractères de contrôle et préfixe « *: » retirés), l'heure de jeu (`status::g_Game+4`, 1/60 s, identique au champ `duree` des sauvegardes), la carte et la catégorie (t terrain / c combat / s système).
- Les doublons sont écartés (`doublon`) : même texte, même source, même instant.
- Mesuré : environ 3,8 µs par image, aucune perte perceptible.

**2. Qui parle**
- Priorité : nom explicite du moteur > installation (`MaterielMenu_*`, `TownPlayerManager::loadChurch`) > objet fouillé (`TownFurniture*`) > personnage de terrain > combat (partie 0xd ou « Battle » dans la pile) > « Message général ».
- Les sources sont lues par rétro-parcours de la pile (frame pointer, x29).
- En-tête : « locuteur · lieu » pour personnage, objet et installation ; nom seul pour un nom explicite ; « Message général » ou « Combat » sans lieu.
- Un texte « *: … » (parole de PNJ anonyme du patch FR) dont la source est inconnue devient « Personnage ».
- Le lieu garde le dernier lieu connu pour les cartes `ev*` et `bt*`, et « Monde » sur la carte du monde.

**3. Interface « Historique des messages »**
- Page `'historique'` du menu Pause. Le moteur s'arrête comme avec le menu Échap (`J.pause_jeu(True)`).
- Style du jeu : plaques d'origine, police bitmap SE-GARRIR (`PoliceBitmap`), flèche dorée, assombrissement au survol, pas de cadre jaune.
- Plus récent en bas, messages consécutifs du même locuteur regroupés sous un en-tête (≤ 6 et ≤ 20 s de jeu).
- Commandes : molette, ↑↓, PageUp/PageDown, Début/Fin, glisser de la barre, Échap ou B pour fermer, filtre Tout / Combats (←/→ ou bouton).
- Ouverture par touche configurable : nouvelle action « Historique des messages », **H par défaut**.
  - H est libre : aucune autre touche par défaut, ni `RESERVEES`, ni chiffre, ni `K.H` dans `window.py`, ni autre worktree.
  - Elle est ajoutée dans Commandes (section « Actions du jeu »).
- Entrée « Historique des messages » à la racine du menu Pause, juste après « Reprendre ».
- Ouverture possible pendant un message sans le perturber.

**4. Mémoire entre sessions**
- Fichier annexe `historique_messages.json` à côté de la visionneuse (option `--historique`), ajouté à `.gitignore`. Jamais dans les sauvegardes de l'utilisateur, aucune sauvegarde modifiée.
- Une « partie » = une aventure, reconnue par `status::g_Game+8` (1 octet utile, 0x66 pour les emplacements 1 et 4, 0x04 pour les emplacements 2 et 5, constant d'une sauvegarde à l'autre).
- Format : `{"version":1,"parties":{"<clé hex>":{"vu":…,"entrees":[[n,t,cat,genre,val,carte,texte],…]}}}`.
- Écriture robuste :
  - fichier temporaire puis `os.replace` ;
  - groupée (au moins 5 s d'écart, forcée à la fermeture) ;
  - fichier corrompu déplacé en `.corrompu`, entrées invalides ignorées ;
  - bornes : 3000 entrées par partie, 6 parties, 1500 caractères par texte.
- Retour en arrière quand une sauvegarde plus ancienne est rechargée :
  - le temps de jeu ne recule jamais, sauf dans ce cas ; un changement doit durer 3 images consécutives (marge de 120 ticks) pour être pris en compte ;
  - les entrées postérieures à l'heure courante sont alors supprimées ;
  - une autre clé de partie bascule sur une autre liste.
- Limites à dire honnêtement :
  - la suppression est destructive (pas d'annulation) ;
  - la clé sur 8 bits peut entrer en collision une fois sur 256 entre deux aventures ;
  - les sauvegardes faites avant la fonctionnalité n'ont pas d'historique avant elles.

**5. Tests et captures**
- `tools/test_historique_messages.py` : 52 tests OK (OK avec libelles ; sans libelles, 1 test ignoré).
- Générateur de jeu d'essai intégré : `--fixture FICHIER.json [CLE]`, 25 entrées variées (clé « 66 » pour l'emplacement 1, « 4 » pour l'emplacement 2).
- Autres tests de `tools/` relancés, tous OK : test_pause_pages (liste de la racine mise à jour), test_reglages_interface, test_reglages_son_texte, test_panneau_interface, test_mode_fenetre (1 ignoré), test_camera_ville, test_son_mixage, test_texte_defilement (4 tests, avec le vrai moteur et les crochets).
- `pyflakes` propre sur les fichiers nouveaux. Il reste 4 avertissements dans `pause.py` (R l.461, yp, mh) et `window.py` (sel l.2203), déjà présents avant mon travail.

## Identifiants réellement passés à `libelle_source`

- **PNJ interagi** : un **int**, `Etat.sprites[8+placement]['id']`, qui est aussi l'index de personnage de `TownCharacterManager`.
  - Chemin : `ScriptGroup::execute` dans la pile, puis `getPlacementCtrlId()` (int à `L+0x29901c`, adresse vérifiée à l'installation en décodant adrp+ldr), puis `TownCharacterManager [L+0x26a548+8+8*pid]+0x14`.
  - Placement 0 = script de scénario global = narration, donc « Message général ».
- **Objet fouillé** : une **str**, le nom de modèle FMAP `noms[o['i']]`, par exemple `'015_hondana1'` ou `'001_tbox01'`.
  - L'uid numérique (`this+0x10` de `TownFurniture*`) est résolu par `HI.nom_objet(objets, noms, uid)` ; il n'est accepté que s'il date de 600 images ou moins.
- **Lieu** : nom de carte (ex. `'mak1f1'`, `'caf1'`) ou `'monde'` (partie 0xe) pour `libelle_lieu`. `None` pour `ev*` et `bt*` donne le dernier lieu connu.
- Dans le code livré, l'import de `libelles` est protégé avec repli : « Personnage », « Objet », lieu omis. Rien ne casse sans `libelles.py`.

## Établi, supposé, non vérifié

**ÉTABLI (observé sur le moteur réel ou en captures)**
- Nom explicite de PNJ.
- Personnage de terrain : « Un vieil homme · Strattbourg » (libellé réel venant de `libelles.py`).
- Meuble : « Un tonneau · Strattbourg », étagère et coffre fouillés.
- Combat : « Combat » pour le message de rencontre (et le groupe de la fixture, rendu en capture).
- Narration : « Message général » sur la carte `caf1` (introduction de l'emplacement 2).
- Église : message de la prêtresse, en capture avec le vrai moteur : « Église · Strattbourg ».
- Clé de partie et heure de jeu.
- Rollback (confirmé sur le moteur : la durée recule au chargement d'une sauvegarde plus ancienne).
- Persistance, écriture atomique, tolérance à la corruption.
- Ouverture et fermeture pendant un message.

**SUPPOSÉ (libellé d'installation déduit du nom de symbole, pas vu en jeu)**
- Boutique, Auberge, Banque, Roi des médailles, Arène, Casino (machine à sous, poker, salle de jetons, cadeaux, stade), Sauvegarde et Chargement (`MaterielMenu_*`).
- L'Église via `MaterielMenu_CHURCH` pour les autres cas que `loadChurch` (qui est établi).

**NON VÉRIFIÉ**
- Messages de jarre : même code `TownFurnitureItem` que le coffre (vérifié), donc probable, mais pas observé.
- Second message « objet trouvé » d'une jarre.
- Messages de combat après le premier (cause : combats non rejoués dans la session).
- Messages de la carte du monde.
- Un second coffre inatteignable (héros bloqué par un mur dans le château).
- **Windows** : aucun test possible ici (Linux uniquement). Code défensif : écriture atomique `os.replace`, encodage UTF-8 explicite.

**Limites connues**
- Un script de cinématique piloté par le PNJ X qui fait parler le PNJ Y étiquettera le locuteur « X ».
- Monstres et modèles 3D non identifiables (comme annoncé par `libelles.py`).
- Le modèle 34 est étiqueté « Un noble » par `libelles.py` (le capitaine de Bastione) : c'est la classification de `libelles.py`, pas la mienne.

## Fichiers touchés et crochets

- NOUVEAU `dq4_pc/historique.py` (415 lignes) : `Capteur`, `Historique`, fonctions pures (`nettoyer`, `envelopper`, `en_tete`, `locuteur`, `lieu_de`, `meme_groupe`, `doublon`, `nom_objet`).
- NOUVEAU `dq4_pc/ui_historique.py` (252 lignes) : `VueHistorique`, `grouper`, `heure_jeu`.
- NOUVEAU `tools/test_historique_messages.py` (524 lignes).
- `dq4_pc/moteur.py` : import l.6 ; `self.capteur = Capteur(self)` l.379, juste après `self._crochets_texte()`.
- `dq4_pc/fenetre.py` :
  - l.19 `import historique as HI` ;
  - l.184 `self.historique = HI.Historique(getattr(args,'historique',None))` après la création de `PA.Pause` ;
  - l.595 `on_close` : `self.historique.enregistrer(True)` ;
  - l.622 `on_key_press` : ouverture si `reg.action_de(symbol)=='historique'` hors titre et en partie ville, combat ou champ ;
  - l.2588 `tick` : `self.historique.maj(mo, objs, noms)` après `mo.step` ;
  - l.3058 `main` : `--historique` (par défaut `ici/historique_messages.json`).
- `dq4_pc/pause.py` :
  - import `ui_historique` (l.14) ; `self.hist` (l.67) ;
  - `ouvrir` (l.179) ; `_e_historique` (l.201) ; entrée racine (l.211) ; `T('historique')` dans « Actions du jeu » (l.441) ;
  - un crochet d'une ligne `if self.ecran=='historique': return self.hist.X(...)` en tête de `touche`, `_bouger`, `survol`, `clic`, `relache`, `glisser`, `molette`, `dessiner`.
- `dq4_pc/reglages.py` : `TOUCHES_DEF['historique']=['H',None]` et `ACTIONS += ('historique','Historique des messages')`.
- `tools/test_pause_pages.py` : liste de la racine mise à jour.
- `.gitignore` : `historique_messages.json*`.

## Captures d'écran

- **Emplacement 1 (clé 66), ouverture par H pendant le message de la prêtresse**
  - `/tmp/m_w3_b140.png` : avant ouverture.
  - `/tmp/m_w3_b170.png` : historique ouvert, 27 messages, dernier en « Église · Strattbourg » (capture réelle du moteur).
  - `/tmp/m_w3_b220.png`, `/tmp/m_w3_b260.png`, `/tmp/m_w3_b300.png` : navigation.
  - `/tmp/m_w3_b360.png` : après Échap, retour direct au jeu.
  - Message intact : avant/après diffèrent seulement dans la zone des torches (538–740 × 446–496, animation des flammes). La fenêtre de message est identique.
- **Emplacement 2 (clé 4)**
  - `/tmp/m_w4_b170.png` : liste, fixture de 25 entrées.
  - `/tmp/m_w4_b260.png` : défilement avec le groupe « Combat ».
  - `/tmp/m_w4_b300.png` : filtre « Combats ».
  - `/tmp/m_w4_b400.png` : fermeture, puis le message réel de narration de l'intro apparaît.
  - Dans `/tmp/histo_w4.json`, les messages réels de narration de l'intro sont stockés en général / `caf1`.
- **Commandes**
  - `/tmp/m_w6_b300.png` et `/tmp/m_w6_b400.png` : ligne « Historique des messages · H », section « Actions du jeu ».
- **Autres**
  - `/tmp/m_w2_b160.png` : racine de la Pause avec la nouvelle entrée.
  - `/tmp/m_w2_b610.png` : ~20 entrées variées (Alena, Une femme, Une jarre, Combat, Église).
  - `/tmp/m_w2_b370.png` à `/tmp/m_w2_b530.png` : filtre, Fin, PageUp, survol.
  - `/tmp/m_w2_b660.png` : Échap revient à la racine de la Pause.
  - Les captures w2 ont un fond à 0,95 d'opacité (un fantôme du message du jeu transparaissait sous le pied de page) ; w3, w4 et w6 sont à 0,98, corrigé.
- Les entrées d'essai des captures viennent de la fixture (« une femme », « une jarre », « un tonneau », « Alena » sont des entrées fabriquées, en gras assumé). Ce qui vient du moteur réel : la prêtresse (Église), la narration `caf1`, et en amont les contextes vérifiés par sondes (étagère, coffre, PNJ, combat).

## Notes de doc à fusionner (rien écrit dans `docs/`)

- Chemin de capture et contexte : voir la section Capture ci-dessus ; à reporter dans `technical-notes-dq4-port.md`.
- Constats techniques à ajouter aux notes :
  - `status::g_Game+4` = temps de jeu en 1/60 s = `duree` des sauvegardes ;
  - `status::g_Game+8` = identifiant de partie sur 1 octet, constant dans toutes les sauvegardes d'une aventure ;
  - placement k correspond à `Etat.sprites[8+k]`, et l'index de personnage du moteur = `sprites[slot]['id']`.
- Fonctions du moteur crochetées : `TextBuffer::cat`, `TownFurniture*` (setFirstMessage, addMessage, setMessage, setSecondMessage), `ScriptGroup::execute`, `getPlacementCtrlId`, `TownPlayerManager::loadChurch`, `MaterielMenu_*`.
- Fichier annexe `historique_messages.json` : format, bornes, comportement de rollback, limites (voir point 4).
- Nouvelle touche H dans Commandes et nouvelle page de la Pause.
- Les touches de la page Commandes dépassent la fenêtre visible : l'entrée est dans « Actions du jeu » (défiler).

## Pièges de fusion

- Conflits probables :
  - `engine.py`, autour de `self._crochets_texte()` ;
  - `pause.py` : `_e_racine` (liste de la racine), `_e_commandes`, les têtes de `touche`, `_bouger`, `survol`, `clic`, `relache`, `glisser`, `molette`, `dessiner` ;
  - `tools/test_pause_pages.py`, liste attendue de la racine : elle doit contenir « Historique des messages » juste après « Reprendre » ;
  - `settings.py` : `TOUCHES_DEF` et `ACTIONS` ;
  - `window.py` : `on_key_press` et `tick`.
- `libelles.py` (branche agent-libelles, 4ec25d6) doit être fusionné pour avoir de vrais libellés ; sans lui, tout est « Personnage » / « Objet » (repli voulu).
- `H` : revérifier à la fusion qu'aucun autre lot n'a pris cette touche par défaut ; l'action est reconfigurable.
- `OPACITE_FOND` (0,98) est dans `ui_history.py`, indépendant de `hud_mobile.OPACITE_JEU`.

## À retenir pour la mémoire (non écrit, mémoire en lecture seule pour moi)

- Source : mes sondes du moteur, pas la mémoire.
- Le texte du patch « Ragnar obtient l'herbe ;médicinale. » contient un « ; » parasite présent dans le tampon du moteur lui-même (bug du patch, à signaler à l'utilisateur).
- `status::g_Game+4` et `+8` : temps de jeu en 1/60 s et identifiant de partie sur 1 octet. Utile pour toute fonction qui suit une partie ou détecte un chargement.
- Pour les autres agents : le verrou xvfb peut mettre 25 à 40 minutes à passer ; ne pas relancer.
- `pkill -f "python3 sondeNN.py"` tue son propre shell si le motif figure dans la ligne de commande. Utiliser un PID.
- Aucune instruction détectée dans la mémoire consultée qui sorte de ma mission.

---

## Agent a411b418cae673469 — 02/11 04:35

RAPPORT fenetre2 (A, B, C faits). Worktree /home/claude/wt-fenetre2, branche agent-fenetre2, arbre propre. 2 commits sur 08f5785 : 4ab39c9 (travail du prédécesseur relu, corrigé, complété + tests), 13af951 (même image redessinée dès que la fenêtre est montrée ; métrique de mesure). Aucun push. Tests : test_mode_fenetre (39), test_reglages_interface (12), test_pause_pages (15), test_reglages_son_texte (7), test_panneau_interface (10), test_camera_ville (5), test_son_mixage (12) : tous OK. pyflakes : seulement les avertissements connus.

ÉVALUATION DU TRAVAIL PARTIEL
Gardé : suppression de tout le code exclusif, migration, nouvelle bascule en une étape, raccourcis, outil de mesure. Rien de cassé trouvé : toutes les références à choisir_mode_ecran, regler_mode_fenetre, _poser_mode, basculer_exclusif, modes_ecran, regler_lissage, NOMS_MODES_FENETRE, MODES_FENETRE ont disparu (test statique). Corrigé / ajouté par moi :
- l'échec simulé (DQ_SIM_ECHEC) arrivait avant tout changement, donc le repli n'était pas exercé. Il arrive maintenant après le set_fullscreen, dans la fenêtre cachée, et le retour à l'état de départ est testé pour de vrai ;
- cachee=True avant l'appel de masquage : un masquage à moitié réussi est quand même suivi d'un set_visible(True) ;
- la même image est redessinée juste après l'affichage (voir « Supposé ») ;
- --correction-bords remis comme interrupteur de débogage (le prédécesseur l'avait retiré ; ta consigne le gardait) ;
- test_window_mode.py entièrement réécrit (le prédécesseur ne l'avait pas touché, il aurait échoué) ;
- measure_toggle.py : ajout de « fenêtre visible sans image ».

A. PLEIN ÉCRAN EXCLUSIF SUPPRIMÉ
- mode_fenetre ∈ {0 fenêtré, 1 plein écran}. Migration : 2 → 1 ; booléen d'avant la #42 → 0/1 ; valeurs absurdes → 0. Clés obsolètes jamais lues ni réécrites (le chargeur ne prend que les clés de DEFAUT ; reglages.CLES_OBSOLETES la documente et le test la vérifie) : plein_ecran, mode_fenetre_retour, correction_bords, lissage. --plein-ecran 0|1|2 : 2 est accepté et vaut 1.
- pause._e_affichage : 1re ligne = « Plein écran », interrupteur Oui/Non, c'est-à-dire l'ancien réglage d'avant #42 (git show 345ba8f), même place. « Résolution » grisée en plein écran. Ordre des autres lignes inchangé. Capture : /tmp/m_fen2_aff_b100.png (fenêtré, Non) et /tmp/m_fen2_aff_b150.png (plein écran, Oui, Résolution grisée avec sa note).
- F11 et Alt+Entrée basculent dans tous les contextes : menus, Pause, éditeur, saisie du nom, logos, combat. Entrée avalée (ni validation, ni discussion de groupe au relâchement d'Alt). _raccourci_fenetre accepte aussi Alt « tenue » même si le drapeau MOD_ALT manque. Les touches passent par le harnais : Pause ouverte (/tmp/m_fen2c_pause_b100.png, b130.png : menu intact, curseur resté sur « Reprendre », donc pas d'Entrée transmise) et combat (2 bascules). Ajout d'un gestionnaire WM_SYSCHAR (Windows seulement) pour supprimer la « tonalité d'erreur » d'Alt+Entrée.
- Scintillement. Causes plausibles, relues dans le code du jeu et dans pyglet 2.1.19 Win32 (pas exécutées sous Windows) :
  1. l'exclusif faisait 2 changements de mode d'affichage par aller-retour (ChangeDisplaySettingsEx) : supprimé ;
  2. set_fullscreen (_recreate → _create) cache la fenêtre, change le style, la taille, puis la MONTRE (SWP_SHOWWINDOW + _on_internal_resize) avant toute image. Le tampon d'affichage redimensionné est donc indéfini jusqu'à la trame suivante, et au retour en fenêtré pyglet appelle set_location APRÈS l'affichage (la fenêtre apparaît en (0,0) puis saute) ;
  3. post.cle=None forcé : reconstruction des tampons du rendu hors écran pendant que la fenêtre est visible.
  Correctif (Jeu._poser_plein_ecran, une seule étape) : mémorise la taille, cache la fenêtre, UN set_fullscreen (taille mémorisée rendue d'un coup, centrage si lancée en plein écran), dessine + flip une image à la taille définitive (les tampons ne se reconstruisent que si la taille change, une fois, dans PostFX.debut, comme avant), montre la fenêtre, redessine la même image. Plus de post.cle=None forcé. Tout échec → retour à l'état de départ, message, mode réel gardé. DQ_BASCULE_SIMPLE=1 = ancien comportement (un set_fullscreen nu), pour comparer.
- MESURES (tools/measure_toggle.py, xvfb/Mesa, fenêtre 1280x720, bureau 1920x1080 ; logs /tmp/out_fen2a_f11.txt, out_fen2a_m1.txt, out_fen2b_f11.txt, out_fen2b_opt.txt, out_fen2b_alt.txt) :
  | | #42 F11 (exclusif) | #42 option mode 1 | maintenant (F11, option, Alt+Entrée) |
  | set_fullscreen / recréation / redimensionnement / reconstruction des tampons par bascule | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
  | changement de mode du moniteur (set_mode) | 1 par bascule (2 par aller-retour) | 0 | 0 |
  | fenêtre visible sans image (aller / retour) | 276 / 67 ms | 250 / 70 ms | 0 / 0 |
  | tampons refaits fenêtre visible (aller / retour) | 1 / 1 | 1 / 1 | 0 / 0 |
  | déplacement fenêtre visible au retour | 1 | 1 | 0 |
  Trames comptées : 12 avant, 13 à 14 maintenant (une image dessinée cachée, une après l'affichage). Le nombre d'événements pyglet sous X11 est IDENTIQUE avant/après. Le gain porte sur l'ordre (aucune image visible sans contenu) et sur la suppression de l'exclusif. Les ms viennent de Mesa : sur un vrai GPU elles seront plus courtes, la structure est la même.

B. CORRECTION DES BORDS : TOUJOURS ACTIVE
Ligne de _e_affichage et clé retirées (DEFAUT, tests). Jeu._correction_bords() = 1.0, sauf interrupteurs de débogage --correction-bords 0-100 et DQ_CORRECTION_BORDS (documentés comme tels dans le docstring et l'aide). Captures, village maout (slot 1, DQ_VILLE=maout, PNJ près des bords gauche et bas-droit) : 0 pixel de différence entre #42 avec l'option sur « oui » (/tmp/m_fen2_vav_b90.png, b150.png) et le nouveau code (/tmp/m_fen2_vap_b90.png, b150.png). Contrôle de sensibilité : DQ_CORRECTION_BORDS=0 donne 8666 px différents (/tmp/m_fen2_voff_b150.png).

C. LISSAGE : TOUJOURS ACTIF
Ligne, clé (DEFAUT, chargeur) et Jeu.regler_lissage retirées. « Oui » = self.lissage True, valeur par défaut de l'ancien réglage : tous les endroits qui lisent self.lissage (textures de décor, HD, FBX, champ, sprites, monstres, shader net) sont inchangés. Seul interrupteur de débogage : DQ_SANS_LISSAGE=1 (plus proche voisin). Contrôles à 0 pixel de différence, #42 « lissage oui » contre nouveau code : titre avec dragon FBX (/tmp/m_fen2_tav_b400.png contre m_fen2_tap_b400.png, b700 idem), village, combat monde + monstre (/tmp/c_fen2_cav*.png contre c_fen2_cap*.png, 4 images). Contrôle de sensibilité : DQ_SANS_LISSAGE=1 donne 617 502 px différents (/tmp/m_fen2_vnl_b150.png).

ÉTABLI / SUPPOSÉ / NON VÉRIFIÉ
Établi (lu dans le code ou mesuré sous xvfb) : tout ce qui précède, plus le comportement de pyglet Win32 relu dans les sources : restore_mode ne fait rien tant que set_mode n'a jamais été appelé (donc plus aucun appel moniteur) ; les gestionnaires WM_ERASEBKGND renvoient 1.
Supposé :
- les causes 1 à 3 du scintillement ;
- sous Windows, la swap d'une fenêtre cachée peut ne pas être conservée par DWM, d'où la 2e image dessinée juste après l'affichage (ceinture et bretelles, coût : 1 trame) ;
- l'événement WM_SYSCHAR est livré à la fenêtre principale.
Non vérifié (Windows, GPU réel, clavier réel) :
- que le scintillement disparaisse sur ton PC : il se peut qu'il en reste (le plein écran sans bordure « indépendant flip » de DWM peut faire un éclair noir à lui seul, inévitable) ;
- F11 et Alt+Entrée sur clavier réel (Alt Gr AZERTY : Ctrl+Alt+Entrée bascule aussi) ;
- la tonalité d'Alt+Entrée supprimée ;
- effets du masquage / affichage (éclair du bouton de barre des tâches, focus rendu par SetForegroundWindow, bascule pendant un Alt-Tab) ;
- multi-moniteurs et DPI ;
- bascule par clic de souris sur la ligne de la Pause (le relâchement du bouton peut se perdre) ;
- le temps réel de la bascule (marche sous Mesa : 65 à 660 ms d'appel).

FONCTIONS TOUCHÉES (window.py)
- Jeu.__init__ : 1re ligne (avalees..., _modes retiré, _restaure_a_la_sortie retiré), création de la fenêtre (res_demandee retiré), ligne self.lissage.
- _echec_simule (DQ_SIM_ECHEC=1 ou 0 maintenant), _creer_fenetre, on_close (1 ligne retirée), est_plein, resolutions, regler_resolution, regler_plein_ecran (nouveau), basculer_plein_ecran (nouveau), _poser_plein_ecran (nouveau), _mettre_plein (nouveau), _image_de_bascule (nouveau), _raccourci_fenetre, _event_syschar (Windows), _journal_fenetre, _correction_bords, argparse --plein-ecran et --correction-bords, main (a.plein_ecran).
- Supprimées : choisir_mode_ecran, modes_ecran, _mode_applique, _restaurer_a_la_sortie, _restaurer_affichage, regler_lissage, regler_mode_fenetre, _poser_mode, basculer_exclusif.
- Ligne de F1 touchée : 1 ligne, le suffixe « (plein écran exclusif) » de self.etiquette.text (zone « entrees »). Le texte « Lissage des textures : oui » de self.etiq_hd est resté (toujours « oui ») : à retirer par toi si tu veux.
- pause.py : _e_affichage et le dict de noms ('Fenêtre' retiré) uniquement.
- settings.py : DEFAUT, RESERVEES (commentaire), CLES_OBSOLETES (nouveau), mode_fenetre_valide, chargeur.
- Tests : tools/test_mode_fenetre.py (39), test_interface_settings.py (3 clés retirées de HORS_INTERFACE).
- Nouveau : tools/measure_toggle.py.

PIÈGES DE FUSION
- test_reglages_interface.HORS_INTERFACE : si un autre agent ajoute des clés à cette ligne, retirer seulement 'lissage', 'correction_bords', 'mode_fenetre_retour'.
- Tout code d'un autre agent qui référence RG.NOMS_MODES_FENETRE, RG.MODES_FENETRE, J.regler_mode_fenetre, J.lissage comme réglage, reg['lissage'] ou reg['correction_bords'] cassera.
- window.py : conflits possibles sur la 1re ligne de __init__, la ligne self.lissage, la ligne etiquette.text et le bloc argparse.
- camera_centree non touché (la ligne reste dans _e_affichage, juste avant « Interface »).
- Ne pas importer reglages.json de test avec 'mode_fenetre': 2 en attendant un exclusif.

NOTES DE DOC À FUSIONNER
1. notes-visionneuse, nouvelle section « Retours de 02 h 12 (#43) » : « Plein écran exclusif supprimé. Deux modes (mode_fenetre 0 fenêtré, 1 plein écran sans bordure) ; ligne « Plein écran » de l'Affichage = interrupteur Oui/Non (1re ligne, comme avant la #42) ; F11 et Alt + Entrée basculent de n'importe où ; 2 → 1 à la lecture ; mode_fenetre_retour, correction_bords, lissage, plein_ecran ignorés puis effacés à la sauvegarde. Bascule en une étape : fenêtre cachée, un set_fullscreen, une image à la taille définitive dessinée et affichée (tampons du rendu hors écran refaits seulement si la taille change), fenêtre montrée, même image redessinée ; échec → état de départ. Mesuré sous xvfb : fenêtre visible sans image 250 à 276 ms puis 67 ms (#42) → 0 ms ; changements de mode du moniteur 2 par aller-retour → 0. Non vérifié : scintillement sur Windows. » La puce « Trois modes » de la #42 est obsolète. Aussi : « Correction des bords et Lissage des textures : options supprimées, toujours actives. Interrupteurs de débogage : --correction-bords 0-100 / DQ_CORRECTION_BORDS, DQ_SANS_LISSAGE=1. » La puce « Page Affichage, nouvel ordre » devient : Plein écran, Résolution, Netteté, Shader, Effet de vignetage, Anticrénelage, Suréchantillonnage, Luminosité, Distance caméra, Centrer la caméra sur le joueur, Interface.
2. notes-technique : variables et outils de test. DQ_SIM_ECHEC=1 ou 0 (échec de la bascule vers ce mode, après le changement), DQ_BASCULE_SIMPLE=1 (set_fullscreen nu), DQ_SANS_LISSAGE, DQ_CORRECTION_BORDS ; tools/measure_toggle.py <dossier dq4_pc> [options window.py] (scénario : --touches-test "60:F11,120:F11" ; sortie « BASCULE n=… fenêtre visible sans image … ») ; test_window_mode.py compte 39 tests ; /tmp/run_bascule.sh.
3. README.md ligne 41 (je n'y ai pas touché : ligne unique énorme, conflit probable) : remplacer « (dans l'ordre : Fenêtre = fenêtré / plein écran / plein écran exclusif, résolution de 720p à 4K, netteté, shader, lissage des textures, effet de vignetage, anticrénelage MSAA x2 / x4 / x8, suréchantillonnage x1,5 / x2, luminosité, distance de la caméra de 50 à 200 %, correction des bords des sprites, caméra centrée… » par « (dans l'ordre : plein écran (oui / non), résolution de 720p à 4K, netteté, shader, effet de vignetage, anticrénelage MSAA x2 / x4 / x8, suréchantillonnage x1,5 / x2, luminosité, distance de la caméra de 50 à 200 %, caméra centrée… » et « **F11** ou **Alt + Entrée** : plein écran exclusif et retour » par « **F11** ou **Alt + Entrée** : plein écran / fenêtre ».

Aucun élément nouveau à mémoriser sur l'utilisateur (rien lu dans la mémoire utile à cette mission).

---
