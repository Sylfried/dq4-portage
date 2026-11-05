### Alignement des textes de menu (#45, agent TX)
- **Établi** : la visionneuse place les TextMesh comme le jeu d'origine. Contrôle sur ecran4 (mobile) et ecran3 (PC), même échelle 1,688 px / unité : texte « Ragnar » de l'onglet identique au pixel près ; « Rat volant » (1 ligne) et « Scarapince / ×2 » (3 lignes) à ±1 px. Formule (`base_premiere_ligne`) : bloc de N lignes de pas interligne (23,525) × characterSize × 0,1 × lineSpacing, ancré en haut / milieu / bas du point z − dy, ligne de base à ascent (18,887 × characterSize × 0,1) sous le haut de la ligne. Test : `tools/test_texte_recentrage.py`.
- **Établi** : le moteur envoie les noms de groupes sous la forme `Nom\n\n\t×2` (3 lignes) pour les plaques (type 31) et les boutons de cible (type 33). Le pas entre le nom et « ×2 » est donc 2 × le pas d'une ligne.
- **Établi (cause du « texte trop bas »)** : les `lineSpacing` du jeu (0,441 cibles, 0,481 plaques de monstres, 0,801 onglets / boutons / noms, 0,873…) sont calculés pour la police japonaise ; ils raccourcissent la boîte de ligne mais la ligne de base reste à ascent du haut. L'encre de SE-GARRIR descend de (1 − ls) × 23,525 × u / 2 sous le centre de sa boîte (6,5 unités pour les cibles et plaques, 2,3 pour onglets et boutons). Le jeu d'origine a le même défaut.
- **Correction (#45, écart volontaire, demande de Sylfried du 02/11 à 14 h 08)** : `recentrage_texte` remonte tout texte de lineSpacing < 1 de cet écart (un seul endroit, `Rendu._texte`). lineSpacing ≥ 1 (PV / PM / Nv., listes) inchangé. `DQ_TEXTE_ORIGINAL=1` donne le placement exact du jeu. Mesures 1280×720 : nom de la plaque d'état −2 px, plaque de monstre −5 px, onglet −2 px, boutons −2 px.
- **Supposé / non vérifié** : ancrages haut et bas (aucune capture mobile du nom dans la bande d'état ni des plaques de monstres) ; la fenêtre ajustée de la plaque (VariableWindow, 142 × 18 ou 36) est reconstruite par la visionneuse (`Fenetre.plaque`), le cadre de l'original pourrait être placé autrement.
- Le texte entre ces deux jeux d'options n'est pas un réglage de la fenêtre Pause (variable d'environnement seulement).
- Débogage utile : une trace temporaire de `Fenetre.param_str` et `Fenetre.plaque` a montré les chaînes brutes ; elle n'est pas conservée.

4. NON VÉRIFIÉ
- Windows et GPU réel : mes rendus viennent de Mesa (llvmpipe).
- Je n'ai pas lancé de combat à plusieurs groupes (le slot 4 n'a qu'un groupe de glacyclones), donc la fenêtre de choix de cible (type 33) n'a été vue qu'en rendu hors écran de la mise en page avec les chaînes du moteur, pas en combat réel.
- Rendus hors écran faits avec pyglet « headless » (EGL) et non via xvfb, car le verrou `/tmp/xvfb.lock` était saturé (plus de 20 jobs en attente). Les deux captures de combat réelles sont passées par `/tmp/run_fen2_cmb.sh` (verrou respecté).
- Hors périmètre, non couverts par le recentrage : `ui_history.py` (historique), `pause.py` (aperçu de l'éditeur, garde `ui_font.otf`), cartouche de nom de l'agent « ui ». Si son cartouche réutilise un nœud TextMesh de la mise en page, il bénéficie du recentrage ; s'il dessine avec `bm.ligne` directement, il peut appeler `ui_menu.recentrage_texte(bm.interligne, u, ls)`.
- Piège de fusion : seuls `dq4_pc/ui_menu.py` (≈ 25 lignes autour de la constante `MARQUES_TEXTE`, une fonction ajoutée et 3 lignes de `Rendu._texte`) et le nouveau fichier `tools/test_texte_recentrage.py` changent ; aucun autre fichier touché.

Journal de mesures : `/tmp/specs/texte_notes.md`. Scripts de mesure et rendu hors écran : `/tmp/tx45/rend_multi.py`, `/tmp/tx45/analyse.py`.

---

## Agent « combat » (a55458f8b35b63979) — 02/11 21:23

RAPPORT FINAL, agent « combat » (préfixe CB), PR #45. Worktree /home/claude/wt45-combat, branche agent45-combat (base 84b3f22). `git status` propre, aucun push. 5 commits séparés, un par point :
- 29fc3b7 point 1 (cascade et fondus)
- acbb491 point 5 (vitesses auto)
- d5eec0c point 2 (contours)
- cea04cb point 3 (décor selon l'heure)
- 7260542 point 4 (coup critique)

Tests relancés après le dernier commit, tous OK : test_coup_critique, test_contours_decor, test_vitesse_combat (42), test_pause_pages, test_reglages_son_texte, test_teinte_carte, test_transition_combat (15), test_enchainement_tours, test_decor_combat_heure (4), test_decors_racine, test_textures_carte, test_objets_carte, test_son_mixage. pyflakes : seuls les avertissements déjà présents dans la base (`dims`, `sel`, `struct`, `soundfile`, `R/yp/mh` de pause.py).

## Point 1. Cascade avant rencontre et fondu de fin de combat : FAIT (29fc3b7)

Établi :
- La durée est maintenant celle du jeu d'origine quel que soit le réglage : accélérateur, vitesse de marche, « Vitesse de transition » (`vitesse_fondu`), Vitesse de combat, caméra.
- `Etat.transition_combat()` regroupe l'effet de cascade, l'attente de chargement, la garde de 8 images, et les fondus marqués « combat » (fenêtres de 12 images à l'entrée et au retour).
- `Jeu._facteur_vitesse` rend 1.0 dans ces phases, et `_faire_pas_combat` / `_pas_terrain` ne coupent pas une transition au milieu.
- La validation des messages et la vitesse des tours ne sont pas touchées.

Preuves :
- Images du moteur : test `MoteurReel` de test_battle_transition.py (15 tests). Segments identiques pour transition x1, x2, x4 ; facteur 1.0 sur 72 combinaisons de réglages.
- Temps réel GL (`DQ_TEMPS_REEL=1`, fenêtre normale) :

| Cas | Avant | Après |
|---|---|---|
| Cascade, x1 | 2,17 s | 1,89-1,90 s |
| Cascade, x3 | 1,07 s | 1,89-1,90 s |
| Fondu de fin, x1 | 0,61 s | ≈ 0,95-0,98 s |
| Fondu de fin, x3 | 0,16 s | ≈ 0,95-0,98 s |

  Les fondus d'entrée et de sortie étaient divisés par deux par `vitesse_fondu`=2. Après correction, les mêmes durées sortent aussi avec transition x4 + marche x4 + accélérateur maintenu.
- Mesure en temps réel bruitée (machine à 2 cœurs partagée, 26-30 images/s à x1) : la preuve principale est en images du moteur.

## Point 5. Vitesses de combat auto : FAIT (acbb491)

Établi, mesuré sur le moteur à 30 Hz (images du moteur = 1/30 s) :

| Tour typique à x1 | Avant | Après |
|---|---|---|
| Attaque simple (commande validée → menu suivant) | 171 images (5,7 s) | 91 images (3,0 s) |
| Effet du coup → nombre de dégâts | 23 images (0,77 s) | 13 images (0,43 s) |
| Critique | 245 images | 125 images |
| Fuite | 247 images | 127 images |

- Durées des effets inchangées : 5303 = 10 images, 5344 = 17 images.
- Code intermédiaire 1 : 131 images pour l'attaque simple.
- **Sort : non mesuré.** Aucun lanceur de sorts pilotable (Ragnar n'a pas de sorts, Doc est une IA).
- Normal, Rapide et Très rapide imposent maintenant l'attente automatique la plus courte (code 0, 12 images entre deux messages). L'ancien Normal imposait le code 2, soit 32 images. Rapide et Très rapide restent x2 et x3 de Normal. Manuel (code 4) est inchangé. Animations, musique, SE et point 1 sont inchangés.
- Changement dans `settings.py` : `CODE_DEFILEMENT_AUTO = 0`. Aucun réglage nouveau n'est ajouté, donc pas de ↺ ni de clé à créer.

## Point 2. Contours des arbres et montagnes : FAIT, MSAA 0 et 4 mesurés (d5eec0c)

Cause établie :
- Les silhouettes sont dans des textures 256x256 dont l'alpha est strictement binaire (0 ou 255). C'est vérifié : 41 textures découpées sur 140 décors `btl*`, sans alpha intermédiaire.
- Le décor est agrandi x6 : un texel couvre 4 à 10 pixels d'écran à 1280-2560 px de large. Le contour (alpha 0,5) suit la grille de texels, d'où des marches d'escalier que le MSAA ne lisse pas (il ne lisse que les marches d'un pixel).
- Les texels transparents sont noirs (0,0,0), ce qui crée un liseré sombre au filtrage bilinéaire. Il est visible sur la capture de Sylfried.
- Le MSAA, l'alpha-to-coverage et les mipmaps ne sont pas en cause.

Correction, nouveau module `dq4_pc/contours_decor.py` :
- Sur les seules textures découpées à alpha binaire de 128 px et plus : alpha x4 (2 passes EPX, flou de 0,3 texel), couleur agrandie en bilinéaire après extension du bord opaque sur 3 anneaux.
- Ciels, sols, matériaux transparents ('tr'), petites textures et mode EPX x8 : inchangés.
- Intérieur du dessin identique à l'original filtré (écart moyen < 1 niveau de gris).
- `DQ_SANS_CONTOURS=1` redonne l'original pour comparer.
- Coût : environ 0,1 à 0,25 s par texture traitée, au chargement du décor. Les 12 dernières textures agrandies sont gardées (5,6 Mo avec mipmaps).

Mesures (rugosité du contour en radians de virage par texel, simulation numérique des textures) :

| Décor | Avant | Après | Variation | Surface |
|---|---|---|---|---|
| pl | 0,487 | 0,301 | -38 % | +0,04 % |
| mt | 0,264 | 0,181 | -32 % | -0,03 % |
| wd | 0,800 | 0,566 | -29 % | -0,36 % |
| po | 0,467 | 0,316 | -32 % | -0,03 % |
| sd | 0,380 | 0,232 | -39 % | -0,05 % |
| se | 0,140 | 0,067 | -52 % | +0,02 % |

Captures GL avant/après à 2560x1380 (taille de l'écran de Sylfried), MSAA 0 et 4 (llvmpipe accepte x4, « msaa réel 4 »), sur pl, mt, wd, po, sd, se. La carte de différence montre que seules les silhouettes changent.

Visuel : les escaliers de la montagne, des sapins, des fougères et des touffes disparaissent, le liseré sombre aussi. Les pointes fines sont conservées. À MSAA 0, il reste les marches d'un pixel (coupure dure), qui ne sont plus des marches de texel.

Tests : tools/test_contours_decor.py (8 tests). Ils vérifient l'escalier redressé, aucune pente aggravée, une pointe d'un texel visible, la surface, la couleur sous le transparent, l'intérieur, le choix des textures, et les 140 décors réels (surface à 1,5 % près).

Comparaison avec le matériau Unity d'origine : non faite. Les textures de `fld_atest` sont celles du cache et le shader du portage les filtre déjà comme l'original. L'adoucissement est un ajout du portage, pas une copie d'Unity.

## Point 3. Crépuscule et lever de soleil en combat : FAIT (preuve et sécurité, cea04cb)

Établi sur le moteur réel :
- L'heure du monde est `StageStatus+0xcc` (0 à 3391, elle avance en marchant). `WorldLocation::setCurrentTimeZone` en tire la zone :

| Heure | Zone |
|---|---|
| 0-127 | zone 1 |
| 128-1983 | zone 2 |
| 1984-2239 | zone 3 |
| 2240-3263 | zone 4 |
| 3264-3391 | zone 1 |

- `StageStatus::getBtlMapName` (0x1a4580) remplace la lettre finale du décor par la table « d n d e n » indexée par la zone : zones 1 et 4 → `_n`, zone 2 → `_d`, zone 3 → `_e`.
- Rencontres forcées aux heures 64, 1000, 1984, 2239, 2240, 3300 → `btl_pl_n`, `_d`, `_e`, `_e`, `_n`, `_n`.
- **Le soir existe** : décor `_e`, tons orange cuits dans l'asset, demandé par le moteur, et la visionneuse l'affiche déjà. Les 6 décors du monde ont chacun `_d`, `_e`, `_n`.
- **L'aube n'existe pas** comme décor : le début et la fin de nuit (zone 1) réutilisent `_n`.
- Monde sombre (`Global::getFieldType() == 2`) : tables `btl_*_dk` sans lettre horaire.
- Le moteur n'envoie en combat ni teinte (paquet 33), ni couleur de fond (paquet 8, `UnitySetMapBackColor`). `getBattleMapBackColor` et `MenuAPI::setBattleBackDrop` ne sont pas appelés. La couleur du moment est cuite dans l'asset (couleurs de sommet et textures) : le soir est plus rouge, la nuit plus sombre et plus bleue.
- `assets/param/param_map_battle.dat` liste les décors de combat (128 lignes de 16 octets : 3 octets de couleur de fond en 5 bits + nom). La viewer garde sa couleur de fond calculée par `_fond_combat`.
- Captures GL des variantes (pl d, e, n, dk ; wd e ; mt n ; po e ; se e) : rendu correct, soir orange, nuit bleue, monde sombre violet.

Code ajouté, par sécurité : `donnees.decors_de_secours()`, utilisé dans `fenetre._charger_carte` pour les noms `btl*`. Si le moteur demande une variante absente des données, la plus proche est prise. Exemple : `btlcc1_n` n'existe pas, on prend `_e` puis `_d`. Avant, le décor était vide. Je n'ai pas pu savoir si le jeu demande réellement ce cas.

Tests : tools/test_decor_combat_heure.py. Il couvre le moteur réel (6 heures, aucun paquet 33 ni 8), les assets (`DQ_CACHE`) et les décors de secours.

## Point 4. Effet de coup critique : EXISTE et est DESSINÉ, rien ne manquait (7260542)

Établi sur le moteur réel (critique forcé sur le héros par un crochet Unicorn à 0x1a81dc, qui pose `kaishinFlag_` = LIB+0x25c6ed ; `[acteur+8]` = 0 pour le héros, 1 pour les monstres qui tirent `rand(0x20)==0`). Comparaison avec un coup normal :
- Un second modèle d'effet, **5344** (emplacement 3, 17 images), est chargé en plus du 5303 du coup normal.
- Bruitages : 400, 402, 412 en normal, plus 407 et 0 en critique. `SE0407.akb` existe dans les données ; SE0000 n'existe pas.
- Dégâts 8 → 26 (11 → 27 sur une autre mesure), plus le texte « Coup critique ! ».
- Aucun paquet 34 (`cmd_screen_effect`), pas de secousse de fenêtre de message, pas d'éclair : les effets d'écran 3, 5 et 6 n'ont aucun rapport avec les critiques.

Preuve visuelle GL : un coup normal affiche seulement l'éclat orange. Un critique ajoute une boule blanche puis une étoile d'éclats (modèle 5344). Sylfried a donc bien vu l'effet.

Code : `sound.py` ignore désormais le bruitage 0 (une ligne). Avant, « SE0000 illisible » était écrit à chaque critique. Test : tools/test_coup_critique.py.

## Fichiers touchés hors de mon périmètre (à signaler aux autres agents)
- `window.py` : `_facteur_vitesse`, `_boucle`, `_faire_pas_combat`, `_pas_terrain` (zone partagée avec l'agent caméra, hors souris, plein écran et caméra) ; `_charger_carte` et `_purger_contours` (nouveaux), plus un import.
- `pause.py` : **une seule ligne**, l'aide de « Vitesse de combat » (zone de l'agent ui).
- `engine.py` (fenêtres de transition de combat), `settings.py` (codes de défilement), `data.py` (+11 lignes) et `sound.py` (+1 ligne).
- `tools/test_pause_pages.py` ligne 138 : `('combat', 0)`.

Pièges de fusion :
- Les hunks de `window.py` (`_boucle` / `_faire_pas_combat`) peuvent chevaucher ceux de l'agent caméra.
- `sound.py` peut être modifié par l'agent « jingle de mort ».
- Le cache des cartes est `carte10_` (inchangé).

## Notes prêtes à coller dans docs/ (non écrites dans docs/)

**notes-technique-portage**
- Transitions de combat : `Etat.transition_combat()` = effet de cascade (EFFET_COMBAT_IMAGES = 57, mot d'état bit 1), attente de chargement, `garde_trans` de 8 images, fondus marqués « combat » (`fd['combat']`). Fenêtres de 12 images à l'entrée (paquet 0 bit 8) et au retour (partie 0xd → 0xe). La visionneuse y joue à 1.0 sans exception.
- `OptionStatus.battleSpeed` (g_Option+5) : 0, 1, 2, 3 = attente de 12, 22, 32, 42 images entre messages ; 4 = manuel. Vitesses auto : code 0.
- Décor de combat : `getBtlMapName` (0x1a4580), table « d n d e n » indexée par la zone horaire (`StageStatus+0xc8`) ; zone dérivée de `StageStatus+0xcc` (seuils 128, 1984, 2240, 3264, 3392) par `WorldLocation::setCurrentTimeZone` (0x1c6fb0). Pas de décor d'aube. Aucune teinte ni fond envoyés en combat. `param_map_battle.dat` : table des décors avec 3 octets de couleur de fond en 5 bits.
- Coup critique : `BaseAction::kaishinFlag_` (LIB+0x25c6ed, GOT 0x23df78) ; `checkActorKaishin` 0x1a8098 ; sortie à 0x1a81dc. Paquets : modèle 5344 (emplacement 3, 17 images), SE 407 et 0, pas de paquet 34.
- Test de pilotage d'un combat : crochet `BattleRoot::setupMonster` + `Encount+0x34/0x44` (un monstre faible, id 3).

**notes-visionneuse**
- Contours des décors de combat : `scenery_outlines.py` (alpha x4 par EPX et flou, extension de couleur) ; désactivation par `DQ_SANS_CONTOURS=1` ; limites : textures à alpha binaire de 128 px et plus.
- Décor absent : `decors_de_secours`.

## Non vérifié ou limites
- Windows et vrai GPU : tout est en llvmpipe (xvfb). MSAA 0 et 4 testés dans le logiciel de Mesa, pas sur la carte de Sylfried.
- Temps réel mesuré sur une machine à 2 cœurs partagée, bruité (la preuve du point 1 est en images du moteur).
- Tour avec sort non mesuré (point 5).
- La couleur de fond de `param_map_battle.dat` : sa lecture dans Unity n'est pas déterminée ; la viewer garde son calcul.
- Demande de `btlcc1_n` et des variantes `btl_mt_dk`, `btl_sd_dk`, `btl_se_dk` par le jeu : inconnue (les données n'ont pas ces `_dk`). Le filet de sécurité couvre les `_d`, `_e`, `_n`.
- Avec MSAA 0, le bord garde des marches d'un pixel (alpha-test dur).
- Le critique forcé est un crochet de test ; en jeu il reste tiré au sort par le moteur.
- À constater en jeu : la fluidité des tours auto (point 5), la disparition du liseré noir sur son écran.

Captures et scripts utiles (hors dépôt) :
- /tmp/cb45/captures/ : c_pl_mont_m4.png, c_pl_pins_m4.png, c_pl_pin_zoom.png (MSAA 0 et 4, avant/après), c_wd.png, diff_pl.png, mos_variantes_d_e_n_dk.png, mont_fx_crit1.png, mont_fx_normal_vs_critique.png
- /tmp/cb45/dec_btl_*_m{0,4}_{avant,apres}.png (2560x1380) et /tmp/cb45/var_btl_*_m4_apres.png
- /tmp/cb45/gl_cb.py, gl_sceneries.py, run_gl.sh, run_gl2.sh, run_tests.sh
- Caches : /tmp/cb45/cache (carte10_btl*)

---

## Agent « sprites » (a9dec662e83175ee7) — 02/11 21:29

RAPPORT lot 45 "sprites" (worktree /home/claude/wt45-sprites, branche agent45-sprites, base 84b3f22). `git status` propre. Trois commits, un par point :
- 6f5d678 Pose couchée des personnages (paquets 16 / 17 / 18)
- 6ba5342 Test : le héros et les compagnons se couchent par les mêmes paquets 16 que les PNJ (vrai moteur)
- 08f7a18 Rencontres aléatoires : (1 + a) / 2 par seconde réelle à marche accélérée
Fichiers de ma zone : dq4_pc/pose_couchee.py, dq4_pc/rencontres.py, tools/test_pose_couchee.py, tools/test_rencontres.py, tools/simulate_encounters.py (tous nouveaux).
Fichiers hors zone, changements minimes :
- engine.py : paquets 16/17/18 dans Etat.appliquer, et le crochet des rencontres.
- window.py : branche couchée dans la boucle des sprites, et une ligne dans `_boucle` (`self.moteur.vitesse_marche = 1.0 if self._horloge_combat() else f`).
- pause.py : une phrase d'aide pour « Vitesse de marche » : "Rencontres aléatoires par seconde : (1 + x) / 2 fois plus (x2 : 1,5 fois, x4 : 2,5 fois)". À coordonner avec l'agent "ui".
Aucun réglage modifié, donc rien à migrer. pyflakes propre sur mes fichiers : il reste 2 avertissements dans window.py (dims, sel) et 3 dans pause.py (R, yp, mh), tous déjà dans la base.
Tests passés : test_pose_couchee (20), test_rencontres (9, dont 4 sur le vrai moteur), test_pause_pages, test_reglages_*, test_priorite_jeu, test_casino_bestiaire, test_vitesse_combat, test_camera_ville, test_cartes_pnj, test_objets_carte, test_etats_correctifs.

=== POINT 1 : PNJ allongé dessiné debout ===
ÉTABLI
- Cause : la visionneuse ignorait les paquets 16, 17 et 18. Le soldat du château (carte taf1) reçoit `0x0c000508` (paquet 16) et `[1040, 1863]` (paquet 17).
- Lu au désassemblage du moteur et à l'IL2CPP :
  - Paquet 16 : bit 0x100 = couché, bit 0x200 = relevé, bit 0x400 = direction (`SetSleepDir`), angle = (d & 0xffff) / -182,0444 + 180, quadrant = bits 14-15.
  - Paquet 17 : hauteur du corps couché = 0,3104 si le décalage est 0, sinon décalage × 1,6 / 8192 (ici 0,3639).
  - Paquet 18 : numéro de feuille de sprites.
  - Maillage couché : même rectangle que le panneau (0,48 × 0,64), mais à plat. Le shader `Custom/CharaSleep` projette le sprite en vue de dessus, taille pleine, sans raccourci, tourné de l'angle du sommeil et de la caméra. La profondeur est celle du corps à plat (+0,1). Décalage `s_lieOffset` selon le quadrant. L'ombre est poussée de 64 sous le sol : elle n'est pas tracée.
- Le seul chemin non vertical de `Chara` est la pose couchée : le dump IL2CPP n'a que SetSleepPose, SetSleepDir et lieBillboard comme API de rotation. Il n'y a donc rien d'autre à composer avec la correction des bords.
- Composition avec la correction des bords : un personnage couché a son propre chemin (`PC.sommets`) et ne passe jamais par `_panneau_ville`. Celle-ci ne corrige que les panneaux debout, et rien n'est forcé à la verticale.
- Avant / après sur taf1 (frames 120 et 200) :
  - Le soldat est couché, tête à droite, quad 77,6 × 58,2 px, sans raccourci.
  - Les coins écran du héros sont identiques avant / après.
  - La différence d'image se limite au soldat (bbox 903,378 à 971,451). Hauteur et inclinaison des PNJ debout sont donc inchangées, au pixel près.
  - Autres lacets de caméra (DQ_LACET 40, -70, 180) : même forme vue de dessus, rapport largeur / hauteur constant à 0,75 (0,48 / 0,64), orientation qui suit la caméra.
- Généralisation par emplacement de sprite :
  - mlb1a (héros couché, paquets 0x500 / 0x0c000400 / 0x08000401 observés dans l'audit) : capture avant / après dessine le héros couché, bbox de différence limitée au héros, PNJ debout au pixel près. Montage : /tmp/sp45/mlb1a_avant_apres.png.
  - Vrai moteur : `TownPartyDraw::setSleep(true / false)` (script `cmd_set_player_sleep`) envoie 0x08000500 et 0x08000501 pour le héros et le compagnon, puis 0x200 et 0x201 au réveil. Etat les marque couchés / relevés (test automatique `test_groupe_couche...`).
  - Même mécanique pour `cmd_character_action_sleep` (PNJ, 0x509 sur mlm2f1) : le code est par emplacement.
- Images à regarder : /tmp/m_sp_taf1_{base,ap}_b200.png, /tmp/sp45/crop_{base,ap}.png (zoom), /tmp/sp45/yaws.png (3 lacets), /tmp/m_sp_mlb1a_{base,ap}_b600.png.
NON VÉRIFIÉ
- Rendu GL d'un compagnon couché ou d'un lit qui recouvre un corps (z-buffer) : la profondeur est vérifiée en géométrie (tests), pas en capture.
- Le cas de l'ombre séparée (`ombre_sep`) n'a pas été vu en capture.
- mlm2f1 (PNJ 0x509) : paquet décodé et testé, pas de capture GL.
- Les déclenchements en cours de partie (auberge, malade) n'ont pas été joués : seulement les cartes taf1 et mlb1a et le forçage moteur.

=== POINT 2 : cycle jour / nuit (question seulement, rien changé) ===
RÉPONSE : le cycle ne suit ni le temps réel ni l'horloge du moteur, mais la distance parcourue sur la carte du monde. Il avance de +2 par pas du moteur où la position du héros change ; à l'arrêt, dans un menu ou en combat, il ne bouge pas.
ÉTABLI (code)
- Temps du monde = `g_Stage+0xcc`, cycle 0xd40 = 3392, zones aux repères 0x80 / 0x7c0 / 0x8c0 / 0xcc0.
- Il n'avance que par `FieldStage::ChangeTime(0)` (+2), appelé de `FieldPlayerDoku::checkDokuDamage+0x38` quand la position a changé. `g_Game+4` n'est que le temps de jeu. Les villes ont des zones horaires fixées par script.
- Le paquet 33 (couleur du décor, `WorldLocation::calcPaletteRate`) n'est émis que quand la palette change : 24 paquets en 900 images de marche, 0 en 120 images immobiles. Côté visionneuse, `Etat.teinte` = dernière valeur reçue, sans lissage ni horloge (map_tint.py, `_teinte_decor`).
ÉTABLI (mesure moteur)
- Trace pas à pas sur la carte du monde : +2 par pas marché, 0 à l'arrêt.
- Un cycle complet = 3392 unités = 1696 pas marchés (moteur : 1698 pas, retour exact à 640).
MESURE EN SECONDES RÉELLES d'un cycle complet
- Horloge nominale : vraie `vitesse_combat.avancer`, 60 images par seconde, horloge simulée : x1 = 56,57 s, x3 = 18,87 s (rapport 3,00).
- Vraie visionneuse GL, horloge réelle, xvfb logiciel sur une machine chargée (robot dans un couloir sans entrée, rencontres coupées) :
  - x1 : 60,11 s (28,3 pas / s) ;
  - x3 : 31,21 s (54,4 pas / s). Le débit moteur plafonne sur cette machine : le nominal serait 90 pas / s. La durée réelle d'un cycle = 1698 pas ÷ pas réels par seconde.
- Effet de chaque réglage : la marche accélérée et l'accélérateur accélèrent le cycle en proportion. Les combats rapides n'ont aucun effet. Les menus et messages le gèlent.

=== POINT 3 : rencontres aléatoires (1 + a) / 2 ===
ÉTABLI (mécanisme du jeu)
- À chaque pas, `CommonWalkDamage::checkWalk` appelle `Encount::execWalk` (si `encountFlag_` = 1). Tous les 16 pas, `execWalk` lance `Encount::exec` (5 fois si [+0x2c] ≠ 0), qui appelle `CountDown::exec` (0x1f454c) : le compteur [Encount+0x134] perd 2 × [+0x144].
- Déclenchement quand le compteur devient négatif ; compteur tiré à chaque `Encount::setup` : 0x1e00 + table[rand(31)].
- Le jeu compte des pas et non du temps : a fois plus de pas par seconde = a fois plus de rencontres par seconde.
- Implémentation :
  - `rencontres.facteur_par_pas(a) = (1 + a) / (2 a)` si a > 1, sinon 1.
  - Crochet Unicorn sur `str w8, [x0]` de `CountDown::exec` (+0xc) : la perte du compteur du moteur est multipliée par ce facteur, avec report des fractions. Ce n'est pas un tirage aléatoire de plus.
  - Le tirage du compteur et la distribution des groupes de monstres ne sont pas touchés.
  - À x1, `Moteur.vitesse_marche` ≤ 1 : le crochet ne fait rien, perte identique au jeu (testé et simulé).
  - Un compteur déjà négatif ne remonte jamais.
- `a` = facteur de marche de `_facteur_vitesse()` = vitesse de marche × accélérateur quand il est tenu (jusqu'à 8). Il vaut 1 en combat.
MESURE : simulation sur le vrai moteur, 24 000 pas par vitesse, graine 1, robot qui marche, outil `tools/simulate_encounters.py`
(`Encount::brew` neutralisé pour compter les déclenchements, compteur retiré comme au retour de combat)
| Lieu | Vitesse | Rencontres | Par pas | Par pas × a, relatif à x1 | Attendu | Perte du compteur appliquée / jeu |
|---|---|---|---|---|---|---|
| Carte du monde | x1 | 179 | 0,00746 | 1,00 | 1,00 | 1,0000 |
| Carte du monde | x2 | 133 | 0,00554 | 1,49 | 1,50 | 0,7500 |
| Carte du monde | x4 | 113 | 0,00471 | 2,53 | 2,50 | 0,6250 |
| Donjon (dab1) | x1 | 157 | 0,00654 | 1,00 | 1,00 | 1,0000 |
| Donjon (dab1) | x2 | 112 | 0,00467 | 1,43 | 1,50 | 0,7500 |
| Donjon (dab1) | x4 | 93 | 0,00388 | 2,37 | 2,50 | 0,6250 |
Incertitude statistique d'environ ±7 à 10 %, écarts dans le bruit. La perte du compteur est exacte, sans hasard : 0,7500 et 0,6250.
- Villes : `encountFlag_` = 0 (lu dans caf1 et mak1f1) et le branchement de `checkWalk` (0x1c4598) saute `execWalk` : pas de rencontres aléatoires en ville, donc rien à corriger.
NON VÉRIFIÉ / LIMITES
- Pas de simulation de marche en ville : le héros n'y a pas bougé dans mes sauvegardes de test. La conclusion repose sur le désassemblage et la valeur du drapeau.
- Le crochet n'a pas été vu dans la visionneuse GL avec de vraies rencontres (les mesures GL avaient les rencontres coupées). La ligne de `_boucle` s'exécute sans erreur lors des mesures GL x3.
- Supposé : j'utilise le facteur nominal `a`. Si la machine ne tient pas le débit (budget de 30 ms par image affichée), le héros va plus lentement que a et les rencontres par seconde tombent un peu sous (1 + a) / 2 (x3 mesuré à 54 pas / s au lieu de 90 sur ma machine chargée). On pourrait utiliser le débit réel mesuré si vous le souhaitez.

=== NOTES À INTÉGRER DANS docs/ (je n'ai pas touché docs/) ===
technical-notes-dq4-port.md :
1. Paquets 16/17/18 : décodage exact (voir point 1), maillage couché + shader CharaSleep, `s_lieOffset` = (0,h,0,2), (-0,1,h,0), (0,h,-0,2), (0,1,h,0), ombre poussée de 64. Seul chemin de sprite non vertical = pose couchée. Cartes avec le paquet 16 dans l'audit : mlb1a (héros + compagnon), mlm2f1 (PNJ 9), taf1 (soldat). `cmd_set_player_sleep` → `TownPartyDraw::setSleep` → `DisplayCharacter::setSleep` → paquet 16 par emplacement du groupe ; `cmd_character_action_sleep` → `TownCharacterManager::setSleepCharacter`.
2. Jour / nuit : conclusion du point 2, données chiffrées, ChangeTime +2 par pas, 1696 pas par cycle.
3. Rencontres : mécanisme et crochet de `CountDown::exec` + 0xc, constantes (0x1e00 + table, perte 2 × [+0x144], 16 pas, [+0x1c] état, `encountFlag_`), `Encount::setup` à l'initialisation des cartes (Field et Town).
viewer-notes-dq4-pc.md :
1. Section sprites : pose couchée par `lying_pose.py`, sans `_panneau_ville`, ombre masquée.
2. Section vitesse de marche : `Moteur.vitesse_marche` écrit par `_boucle`, (1 + a) / 2 rencontres par seconde, `tools/simulate_encounters.py` et `tools/test_rencontres.py`, une phrase d'aide dans pause.py.
3. Outils : /tmp/sp45/mesure_cycle.py et cycle_sim.py (robot de mesure du cycle) ne sont pas dans le dépôt ; à reprendre si utile.

---
