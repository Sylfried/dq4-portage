### Non vérifié
Windows ; un vrai changement d'APK entre l'enregistrement et le chargement.

## Avance #209 : la tabulation des textes de menu partout où le jeu en règle une (#208, audit UI-03, 04/11/2026)

### Constat (audit du 04/11/2026)
`TextMesh.tabSize` : une tabulation vaut `tabSize` fois la largeur d'une espace. Les mises en page exportées en portent une dans les types 8, 20, 34, 35 (8), 31, 33, 39 (25) et 78 (1), mais `ui_menu.param_str` ne la remplaçait que pour la liste des magies (`noms_liste`), et `plaque()` (plaques de monstres) écrivait le texte tel quel ; la police du jeu n'a pas de glyphe pour `\t` (largeur 0). Établi (vrai moteur + vrai rendu, rendus comparés de l'audit) : dans « Ordre de marche » (type 20) la ligne « Nv.: 5 » était dessinée **sur le sprite** du personnage ; dans chaque combat contre un groupe (type 31) le « ×N » était collé à gauche de la plaque. Supposé pour 33, 34, 35, 39 (fenêtres jamais ouvertes pendant l'audit).

### Fait
- `menus/ui_menu.py:tabuler(s, tab_size)` (nouvelle fonction) : `\t` -> `round(tabSize)` espaces ; cellule sans `tabSize` : texte inchangé. Utilisée par `param_str` (condition `noms_liste` supprimée : la liste des magies garde exactement le même résultat) et par `plaque()`.
- Mesuré avec la vraie police (SE-GARRIR, espace de 5 px, « × » de 16 px, caractère 9,3925, texte ancré en x = -74, plaque de -71 à +71) : « ×2 » finit à x = 68,8 (dans la plaque), jusqu'à « ×9 ». « ×10 » finirait vers x = 79, soit 8 unités au-delà du bord (supposé identique dans l'original avec les mêmes constantes ; groupe de 10 monstres identiques : rare) : non compressé.
- `tests/test_menu_tab.py` (7 tests, avec pyglet en mode sans fenêtre ; non ajouté à la CI qui n'installe pas pyglet).

### Non vérifié
Windows ; types 33, 34, 35, 39 (lignes de coût du type 35 : même tabulation que le type 8, qui déborde déjà de 36 unités, voir le sondage UI-05) ; « ×10 » et plus en combat.

## Avance #211 : le bateau de la carte du monde est bien découpé, plus grand, avec son sillage (#210, audit SPR-01 et SPR-05, 04/11/2026)

### Constat (audit du 04/11/2026)
La feuille `h193` (bateau, 512 × 512) était découpée comme une feuille de personnage (cases de 24 × 32, 3 colonnes) et dessinée dans le panneau d'un personnage (24,9 × 33,2 pixels de carte). `Chara.SetTexture` (branche de l'identifiant 193) lui donne le maillage `mesh12` : **carré de 0,8 × 0,8, cases de 40 × 40, 12 colonnes** ; le moteur envoie deux sprites (navire : rangées 0 à 4 ; sillage : rangées 5 à 9 ; `pose` = colonne jusqu'à 10, `dir` = rangée, +5 pour le sillage). Établi par désassemblage, scénario du chapitre 4 (drapeaux 204 = 1, 205 = 0) et captures de la visionneuse réelle : navire rogné, morceau changeant avec la colonne, sillage perdu. `Chara.SetTexture` remplace aussi 194 par 193.

### Fait
- `monde/hd.py` : `FEUILLES_SPECIALES` (193 : cases 40 × 40, 12 colonnes, 10 rangées utiles, panneau × 1,667 en largeur et × 1,25 en hauteur : 40 pixels de carte, 41,5 avec l'échelle de la carte), `ALIAS_FEUILLES` (194 -> 193), `geometrie_feuille` et `uv_case` (le calcul des UV de la case, sorti de la boucle de dessin).
- `fenetre/champ.py` : `_feuille_orig`, `_calcul_hd`, `_feuille` suivent le découpage de la feuille ; l'atlas HD du bateau a son fichier de cache (`hd_epx_v3_h193_g40x40x12x10.npy`, environ 52 Mo, calculé en arrière-plan à la première rencontre ; l'ancien `hd_*_h193.npy` n'est plus lu).
- `fenetre/jeu.py` : colonne = `pose % colonnes de la feuille` ; panneau du sprite = panneau d'un personnage × `pw`, `ph` de la feuille (1 pour tous les personnages).
- Vérifié par captures GL de la visionneuse (sprites 4289 et 4290 injectés, modes originaux et EPX) : navire entier dans ses 5 directions, sillage visible, alias 194 identique.
- `tests/test_special_sheets.py` (7 tests, dans la CI : découpage, alias, couleur de chaque case lue avec `uv_case`, vraie feuille quand elle est dans le cache : rangées 0 à 3 pleines, 4e à 8 cases, sillage rangées 5 à 9).

### Non vérifié
Rendu de l'original (aucune capture) ; Windows ; le bateau en situation réelle (mouvement, rotation de la direction, accostage : seule la feuille a été vérifiée par sprites injectés) ; poids de l'atlas HD (52 Mo de mémoire vidéo, avec mipmaps).

## Avance #213 : l'ombre du ballon à sa place sur la carte du monde (#212, audit SPR-02, 04/11/2026)

### Constat (audit du 04/11/2026)
`cmd_chara_shadow` (paquet 15) : bit 12 = position de l'ombre (3 flottants), bit 13 = opacité (1 flottant), **bit 14 = `SetFieldShadowPosition` (3 flottants)**. `Etat.appliquer` ne lisait pas le bit 14 (et ne retirait pas le flottant du bit 13). Établi (scénario du chapitre 5, drapeau 344 = 1) : le ballon envoie `0x440c` + `[2495,97 ; 383,97 ; -1]` à chaque image pour un sprite en `(2496 ; 352 ; 20)` : l'ombre doit être 32 pixels de carte (2 tuiles) plus au sud ; elle était collée sous la nacelle.

### Fait
- `noyau/moteur.py` : le flottant d'opacité est retiré, puis `s['ombre_champ'] = (x, y, hauteur)` si le bit 14 est présent. `fenetre/jeu.py` (boucle des sprites, carte du monde) : l'ombre du sprite est posée à cette position (arrondie en pixel perfect) ; sans `ombre_champ`, comme avant.
- Capture de la visionneuse réelle (scénario du ballon) avant / après : l'ombre sous la nacelle disparaît et revient 32 pixels de carte plus bas (68 pixels d'écran à 1280 × 720), par-dessus la maison de la carte.
- `tests/test_balloon_shadow.py` (5 tests, dans la CI : le paquet 0x440c réel, ordre des flottants des bits 12 / 13 / 14, paquets sans bit 14 inchangés, paquet tronqué).

### Non vérifié
Rendu de l'original (aucune capture) ; Windows ; que l'ombre passe bien par-dessus les bâtiments de la carte (supposé) ; le vol complet du ballon (seul le départ au sol a été rejoué).

## Avance #215 : l'import de sauvegardes contrôle la somme des journaux et écrit sans fichier à moitié écrit (#214, audit ENG-07, 04/11/2026)

### Constat (audit du 04/11/2026)
`sauvegardes.importer` ne contrôlait que la taille des journaux et écrivait directement. Un journal abîmé (ou qui n'en est pas un) était importé, puis refusé par le moteur (« banque vide », sans raison pour le joueur) ; l'écriture directe pouvait laisser un fichier à moitié écrit. Établi : le moteur ne plante pas sur un journal abîmé (statut invalide, retour au titre).

### Fait
- `persistance/format_journal.py` (nouveau) : `dechiffrer` (filtre du jeu, `Cryption::Filter`), `somme`, `verifier(nom, octets)` -> `None` ou la raison : en-tête « rate » + somme de contrôle des 0x3660 premiers octets ; banque neuve (`DWEN`) ou supprimée (`DLED`) valides ; `data9.dat` sans somme. Vérifié sur 452 journaux réels (sauvegardes du téléphone et écritures du moteur) : aucune fausse alerte ; seul le fichier de bruit de l'audit est refusé.
- `persistance/ecriture.py` (nouveau) : `ecrire_atomique` (déplacée depuis `CoreJeu`, qui garde le même nom) ; `sauvegardes.importer` l'utilise : chaque fichier est écrit en entier ou pas du tout, un échec laisse l'ancien fichier et est signalé dans « Ignorés », les autres fichiers passent ; rien d'écrit = erreur claire.
- `lire_sources` refuse un journal abîmé avec sa raison. `test_chemins` : journaux valides fabriqués (`journal_valide`) au lieu d'octets quelconques.
- `tests/test_saves_import.py` (13 tests, dans la CI : valide, banques vides, octet changé, somme changée, bruit, import partiel, tout refusé, échec d'écriture simulé sans fichier temporaire oublié, vraies sauvegardes).

### Non vérifié
Windows ; un export fait avec un autre jeu (même format ?) : seul le format du jeu est reconnu.

## Avance #216 : un nom de carte sans données est refusé au lieu de planter le moteur (#76, audit ENG-10, 04/11/2026)

### Constat (audit du 04/11/2026)
Le ticket #76 (« `startTown` plante pour `za3f3` et `ev01`, les données sont correctes ») était mal posé. Établi : **`za3f3` n'a pas de `.stg`** dans `split_UnityDataAssetPack.apk` (le paquet graphique a bien son `.map` et son `.fld` : carte orpheline, 529 `.stg` pour 530 cartes) ; le moteur ne teste pas l'existence du fichier et déréférence un pointeur nul (`FldStage::getCameraLimitL` + 0x1c, reproduit dans 4 contextes sur 4). **`ev01`** (carte du titre) plante seulement quand on la lance par `startTown` après le chargement d'une sauvegarde (`TownOpeningManager::draw` -> `TownCharacterManager::setRotate`) ; démarrée par le titre elle se charge sans erreur (partie 12, 4 sprites) : artefact du lanceur de test, pas un défaut de données. Les 8 autres cartes d'événement (`ev02` à `ev09`) se chargent. Supposé : qu'aucun déplacement du jeu ne mène à `za3f3` (la table des déplacements n'a pas été balayée en entier).

### Fait
- `noyau/moteur.py:Moteur.demarrer_ville` (chemin d'essai `DQ_VILLE`) : refuse un nom sans `assets/map/<nom>.stg` avec une erreur claire (`ValueError`) au lieu de laisser le moteur planter ; les 529 cartes de l'APK sont acceptées.
- `tests/test_unknown_map.py` (4 tests, dans la CI). Ticket #76 clos avec explication (aucun défaut du portage à corriger).

### Non vérifié
Aucun déplacement du jeu vers `za3f3` (supposé).


## Avance #218 : les réglages du moteur qui ne s'installent pas sont signalés au joueur (#217, audit ENG-08, 04/11/2026)

### Constat (audit du 04/11/2026)
Chaque réglage posé dans le moteur d'origine (vitesse du texte, défilement des combats, PV/PM au niveau supérieur, rencontres, horloge jour / nuit, sorts sans effet, fondus de script, fenêtre des lieux, bouton « Paramètres », historiques) vérifie l'instruction qu'il remplace ; sur un autre APK le réglage n'est pas installé et seule la console le disait (invisible sur Windows). `_elargir_symboles` et `patcher_parametres` se taisaient même complètement. Établi : avec l'APK étudié, aucun point n'est manqué.

### Fait
- `noyau/moteur.py` : `Moteur.crochets_manques` + `Moteur._manque(texte)` (console, liste sans doublon : `reappliquer_correctifs` repasse après le chargement d'un état) remplacent les `print` des 8 installateurs ; messages ajoutés pour la fenêtre des lieux (instruction différente ; « déjà élargie » reste silencieux), le bouton « Paramètres » (ni d'origine ni déjà patché) et les deux historiques inactifs.
- `fenetre/jeu.py:Jeu._signaler_crochets_manques` (modèle : `_signaler_echecs_ecriture`) : une ligne par point dans `erreurs_fenetre.log` et un message à l'écran de 8 s ; les points trouvés plus tard (après le chargement d'un état) sont annoncés à leur tour, jamais deux fois.
- `tests/test_missing_hooks.py` (7 tests, dans la CI : faux moteur avec instruction d'origine / différente / déjà patchée, doublons, chaque installateur sans fonction ; journal et message ; moteur réel : liste vide et les deux historiques actifs).
- Non touché : `ctl_flush_tb` avalé dans `CapteurCombat` (le capteur est créé avant la première image : aucun bloc déjà traduit à vider ; ne sert qu'à un capteur créé plus tard par les outils d'essai).

### Non vérifié
Un autre APK (aucun disponible : le message n'a été vu que sur faux moteur) ; Windows.

## Avance #220 : les descriptions du bas des boutiques, du casino et de la vente sont recoupées à la largeur de leur cadre (#219, audit UI-04, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi (mise en page réelle, police réelle, 360 descriptions du patch) : la barre de description du bas des fenêtres du casino (type 46), d'achat (60, 61), de vente (63) et de la fiche d'objet de vente (70) n'était pas dans `ui_menu.DESCRIPTIONS` : 24 descriptions sur 360 dépassaient du cadre (pire : +72 unités, sous le bouton retour), 3 avaient plus de 2 lignes. Type 63 : texte plus petit (8,29), aucune ligne trop large, 3 descriptions de plus de 2 lignes. Supposé : le rôle des cellules (fenêtres non ouvertes dans le moteur).

### Fait
- `menus/ui_menu.py` : `DESCRIPTIONS` indexée par **(type, port, numéro de chaîne)** au lieu de (type, numéro) : la fenêtre du casino (46) a quatre autres textes au numéro 3 (listes, ports 0 à 3) qu'un simple ajout aurait recoupés. Anciennes entrées : (7, 0, 1), (10, 0, 4), (38, 2, 3) ; nouvelles : (46, 4, 3), (60, 4, 4), (61, 4, 4), (63, 0, 4), (70, 0, 3), bord droit 148 comme la fiche d'un sort. Le texte du moteur n'est pas modifié : c'est le rendu qui recoupe (et comprime jusqu'à ×0,7 si 2 lignes ne suffisent pas).
- `tests/test_item_description.py` (22 tests, à la main : pyglet) : table, un seul port recoupé par fenêtre, vraie mise en page (chaque clé désigne une cellule de texte du bas), 360 descriptions avec la vraie police pour 46 / 60 / 61 / 70 et pour 63 (aucune ne sort, aucun mot perdu).
- Capture hors écran avant / après (vrai rendu, fenêtres 60 et 46) : la ligne qui passait sous le bouton retour passe sur 2 lignes dans le cadre ; les listes du casino ne bougent pas.

### Non vérifié
Windows ; le moteur n'a pas ouvert ces fenêtres (rôle des cellules supposé d'après la géométrie).

## Avance #222 : un échec de lecture ne coupe plus le son jusqu'à la fermeture du jeu (#221, audit SND-10 et SND-12, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi (lecture de `sound.py`) : `_lancer_se` et `_lancer_bgm` faisaient `self.ok = False` sur n'importe quelle exception de lecture (périphérique retiré ou changé, pilote) : tout le son était coupé jusqu'à la fermeture, sans trace hors console. La reprise après pause et `_appliquer_volumes` avalaient leurs erreurs (SND-12). Non vérifié : un déclenchement réel (changement de périphérique sous Windows).

### Fait
- `sound.py` : compteur d'échecs consécutifs (`ECHECS_MAX` = 3) ; à 3, le son est coupé un moment puis rouvert tout seul (`DELAIS_REESSAI` 2 s, 10 s, puis 30 s) ; à la réouverture un seul échec recoupe aussitôt (délai suivant) ; un son qui part remet le compteur à zéro. Pendant la coupure rien n'est tenté (pas d'échecs en cascade) et la dernière musique de fond demandée est gardée : elle est relancée au retour (un arrêt la supprime, un jingle à reprise la laisse). Pas de pilote audio au départ (pyglet absent) : ni coupure ni nouvel essai, comme avant.
- Journal : chaque échec, la coupure et le retour vont dans `erreurs_fenetre.log` (au plus 40 lignes par session) ; message à l'écran « Son interrompu : nouvel essai automatique » et « Son rétabli ». Erreurs avalées (volume de la musique / des bruitages, reprise après pause) : notées une seule fois par session.
- `fenetre/jeu.py` : `noter_erreur(texte)` (écriture dans le journal des erreurs, ne lève jamais) remplace les trois copies du même code (échecs d'écriture des sauvegardes, réglages du moteur non appliqués, son).
- `tests/test_sound_failures.py` (13 tests, dans la CI : faux lecteurs sans carte son).

### Non vérifié
Un vrai changement ou retrait de périphérique audio (Windows) ; la durée réelle d'une panne de pilote (les délais sont un choix).

## Avance #224 : la teinte plein écran de l'effet 35 couvre toute la largeur 16/9 (#223, audit CMB-02, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi (capture de la visionneuse, effet 35 forcé dans un combat, 1280 × 720) : l'effet 35 est un quad plein écran de 12,9 × 12,9 (paquet 25, modèle 5035) calé sur le champ 4:3 d'origine ; avec le combat élargi en 16/9 (choix de Sylfried) il ne couvrait que x 108 à 1202 sur 1280 : deux bandes latérales sans teinte. Supposé : les autres quads larges (effet 9, 7 unités) sont plus grands que le champ et corrects. Quel déclencheur du jeu utilise l'effet 35 : non vérifié (forcé).

### Fait
- `combat/effets_plein_ecran.py` (nouveau) : `elargir(loc, modele, aspect)` étire en largeur de `aspect / (4/3)`, autour de son centre, les coordonnées locales d'un maillage de combat dont le modèle est dans `MODELES_PLEIN_ECRAN` (5035 seul) ; rien pour un écran 4:3 ou plus étroit ni pour un autre modèle.
- `fenetre/scene_combat.py:_maillages_combat` : appel juste après la lecture des coordonnées locales (combat seulement).
- Capture avant / après (vrai rendu, 1280 × 720) : teinte sur toute la largeur après. `tests/test_full_screen_effects.py` (7 tests, dans la CI).

### Non vérifié
Windows ; les autres effets d'écran (3, 5, 6 : #68).

## Avance #226 : une texture de monstre absente n'arrête plus le jeu (#225, audit CMB-03, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi : `_texture_monstre` lisait `donnees.texture('m%03d')` dans un `try` qui ne couvrait que les exceptions ; quand la fonction renvoie `None` (25 numéros de monstre sans texture `m<id>` dans les données), `self._tex(None, ...)` plantait et le processus s'arrêtait (reproduit avec le monstre 199 forcé). Aucun de ces numéros n'est dans les 255 formations : pas atteignable par un combat normal. Non vérifié : un usage scénarisé.

### Fait
- `fenetre/scene_combat.py:_texture_monstre` : `None` = même repli que l'exception (texture transparente 16 × 16, monstre non dessiné) avec une ligne de console ; vérifié avec la visionneuse complète (monstre 199 forcé : le combat se déroule).
- `tests/test_missing_monster_texture.py` (3 tests, à la main : pyglet, donc pas dans la CI).

### Non vérifié
Un usage scénarisé de ces numéros ; Windows.

## Avance #228 : le bruitage des boutons suit la règle du jeu d'origine, au clavier comme au doigt (#227, audit SND-08 / SND-09 / UI-01, règle de #60 / D-156, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi (désassemblage de `MenuPortItem.Update`, 8 sites d'appel de `Sound.PlaySE` dans 3 classes) : à l'appui d'un bouton de menu le jeu joue `PlaySE(300)` seulement si la touche de manette du bouton est A (0x10) ou action (0x800) ; B (0x20), retour (0x400), flèches (1, 2, 4, 8) et zone 0x80 sont muets ; les boutons du terrain (`TouchPad.internalUpdate`) jouent le bruitage. Le portage le jouait pour tout bouton cliqué et, au clavier, pour B, flèches de page, ▲ ▼, changement de colonne de la saisie numérique, fermeture et mode de la carte, retour de la licence ; il ne le jouait pas pour Entrée (Commandes), Espace (Discussion), M (Carte) ni pour les lettres tapées dans la saisie du nom (G-173). Règle de Sylfried (#60, D-156, D-166) : le clavier joue le bruitage dans les mêmes situations qu'au doigt. Les menus du jeu n'ont que les manettes A, B, flèches et action (inventaire des 80 types) : aucun bouton à bascule.
