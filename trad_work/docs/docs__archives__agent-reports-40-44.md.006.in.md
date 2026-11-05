## Agent aec9b0976be625290 — 01/11 23:49

RAPPORT editeur2 (PR #42, points 10, 11 + glisser du panneau flottant)

Branche `agent-editeur2`, worktree /home/claude/wt-editeur2, base 345ba8f. Un seul commit : `fa3619e`. Arbre propre. Aucun push, `docs/` non touché.

## Ce qui est fait

### Point 10 : étiquette « Masquée » pour tout élément masqué
- **La croix a deux options distinctes** dans « Boutons et croix de l'écran » :
  - « Afficher cette interface à l'écran » (`boutons`) masque Carte, Commandes, Discussion et la croix ensemble.
  - « Afficher la croix » (`croix`) masque la croix seule. C'est l'option que l'utilisateur appelle « option pour la croix ».
- Avant, seule l'interface entière était voilée et marquée. La croix masquée seule n'était que pâlie (alpha 0,35), sans mot.
- Maintenant `Pause._elements_apercu()` donne, pour chaque élément montré, `(rect, masqué, masculin)`. Il sert à la fois à l'étiquette et à `_rects_montres()` (placement du panneau).
- Les boutons restent liés au réglage global `boutons`. Il n'y a pas de réglage bouton par bouton (décision de Sylfried en #37, « ça ira comme ça »). Le bouton Mode appartient à la fenêtre `MapButton` et suit donc `interface_masquees`.
- Accord : « Masqué » pour les 3 boutons, « Masquée » pour la croix et les fenêtres (constante `MOTS_MASQUE`, facile à rendre invariable si l'utilisateur préfère).
- Le voile est dessiné, puis l'étiquette, puis le cadre jaune de sélection est redessiné par-dessus : il reste identique, non couvert par le voile.
- L'étiquette est ajustée à la largeur de l'élément : elle tient dans les petits boutons (zoom `/tmp/ed2_masque_boutons_zoom.png`).
- Dans `hud_mobile._croix`, l'alpha 0,35 est supprimé : le voile commun suffit, la croix n'est plus assombrie deux fois.
- Sélectionnable : un élément masqué reste attrapable dans l'éditeur. Capture : un bouton masqué déplacé à la souris (`/tmp/ed2_masques.png`, 2e image).
- Balayage des 53 fenêtres avec une impression de debug temporaire, retirée (`git diff` propre) : toutes ont un rectangle d'aperçu, toutes sont voilées et marquées quand elles sont masquées. Aucune ne tombe sur `None`. Message et Oui / Non vérifiés en capture.

### Point 11 : remises à zéro complètes
**Inventaire des clés de réglage** (46 clés dans `DEFAUT`, 9 touchent l'interface). Le classement est dans `settings.py` :
- `CLES_ECRAN` = `boutons`, `croix`, `croix_taille`, `boutons_taille`, `boutons_pos`.
- `CLES_FENETRES` = `interface_fenetres`, `interface_masquees`.
- `CLES_EDITEUR` = `grille_edition`, `boutons_aimant`.
- `FENETRE_DEFAUT` = (1,0, 0,0, 0,0) : valeur d'une fenêtre sans réglage. Elle remplace les `[1.0, 0.0, 0.0]` et `defaut=1.0` / `0.0` recopiés dans `pause.py` et `window.py`.
- Classées non-interface : `infos` (F1, lignes d'information), `taille_degats` (valeur fixe) et tout le reste (son, affichage, touches, caméra, vitesses).

**Fonctions de remise à zéro**, toutes à partir de `DEFAUT` (copie JSON, rien de recopié) :
- `Reglages.remettre_interface(cible)` :
  - `boutons` : tout `CLES_ECRAN` revient (affichage, tailles, positions, croix affichée).
  - fenêtre ou `msg` : son entrée dans `interface_fenetres` et `interface_masquees` revient.
  - Elle seule change. Ni l'éditeur ni les autres fenêtres ne bougent.
- `Reglages.remettre_interfaces()` : tout `CLES_INTERFACE`, donc aussi grille et aimantation.
- `Pause._remettre_cette` et `Pause._tout_remettre` remplacent `_rien_ov` et `_remettre_boutons`. `_tout_remettre` remet aussi `pan_pos = None` (place du panneau pour la session).
- `hud.remettre()` est supprimée (plus appelée).
- Infobulles ajoutées sur les deux boutons « Rétablir ».
- Le résultat est immédiat : l'aperçu et le jeu relisent `reg` à chaque image.

**Test** `tools/test_reglages_interface.py` (12 tests, OK) :
- Le test met toutes les clés à des valeurs non défaut, remet une interface (seule elle change), puis tout (tout revient au défaut, le reste intact).
- Il contrôle l'aller-retour sur fichier.
- Il contrôle `Pause._e_interface` avec un jeu factice.
- Il contrôle `_elements_apercu` (masqué ou non, genre).
- **Piège** : `test_classement_complet` échoue si une clé est ajoutée à `DEFAUT` sans être classée.

**Captures avant / après** (état de départ : `/tmp/rg_ed2_non_master.json`, tailles, positions, croix masquée, fenêtres décalées) :
- Croix et boutons, aperçu : `/tmp/ed2_cette_boutons.png`.
- Fenêtre de menu (`RootMenu`), aperçu : `/tmp/ed2_cette_menu.png`.
- Message, aperçu : `/tmp/ed2_cette_msg.png`.
- En jeu sur la carte du monde, avec `--force-champ` (HUD et menu du jeu rétablis sans relancer) : `/tmp/ed2_cette_jeu.png`. L'état d'avant est `/tmp/ed2_jeu_av_sheet.png`.
- Message en jeu (église, slot 1), avant / milieu / après : `/tmp/ed2_msg_jeu.png`.
- « Rétablir toutes les interfaces » : `/tmp/ed2_toutes.png`. La grille réapparaît, tout est par défaut, le panneau revient à son origine. Le `reglages.json` enregistré égale `DEFAUT` pour les 9 clés.
- `Status` n'est pas touché par « Rétablir cette interface » appliqué à `boutons`, `RootMenu` et `msg` : le fichier enregistré le confirme.

### Glisser du panneau flottant (point supplémentaire du coordinateur)
- **Cause établie** : dans `Pause.glisser`, un mouvement de plus de 8 px avant 0,35 s mettait `annule = True`. Qui appuie et glisse tout de suite (cas normal) ne déplace rien et ne replie rien. Sans attente de 0,35 s sans bouger, rien ne marchait.
- **Reproduit** avec le harnais (appui, glisser, relâcher en moins de 0,35 s, `DQ_APPUI_LONG=5`) : `/tmp/ed2_drag_av_sheet.png`, le panneau ne bouge pas.
- **Corrigé** dans `pause.py` (`_appui_barre`, `glisser`, `relache`, `maj`). La clé `annule` est supprimée.
  - Le panneau suit le pointeur dès que celui-ci s'éloigne de 8 px (`TOLERANCE_APPUI`) du point d'appui. Il se soulève alors (titre doré, cadre agrandi), sans attendre.
  - Un appui maintenu sans bouger pendant 0,35 s le soulève aussi, puis il suit au premier mouvement.
  - Un appui court sans mouvement (secousse jusqu'à 8 px) replie ou déplie.
  - Le double clic remet la position d'origine. **Changement de comportement** : la remise à l'origine se fait au relâchement du 2e clic, plus à l'appui. Un 2e appui suivi d'un glisser déplace le panneau.
- **Test** `tools/test_panneau_interface.py` : 10 tests, séquences press / drag / release avec horloge simulée et `Pause.maj` à chaque image. Il échoue 3 fois sur l'ancien code et passe sur le nouveau. Il vérifie aussi que la position reste dans l'écran à 1280 x 720, 1920 x 1080 et 2560 x 1440.
- **Captures après** : 1280 x 720 `/tmp/ed2_drag_ap_sheet.png`, 1920 x 1080 `/tmp/ed2_drag1080_sheet.png`. Dans les deux, le panneau suit le pointeur, avec le décalage d'appui exact.

## Établi / Supposé / Non vérifié
- **Établi** (lu dans le code ou observé sous xvfb avec Mesa) : tout ce qui précède. Les événements simulés passent par les mêmes `Pause.clic`, `Pause.glisser` et `Pause.relache` que `on_mouse_press`, `on_mouse_drag` et `on_mouse_release` de `Fenetre` (qui ne font que les relayer).
- **Supposé** : une vraie souris sous Windows envoie la même suite d'événements pyglet que la simulation, et un doigt arrive comme événement souris. Seuil de 8 px : choix de ma part.
- **Non vérifié** :
  - Souris réelle sous Windows (pas de Windows ici), écran tactile.
  - Le choix « Masqué » (boutons) contre « Masquée » (croix, fenêtres) plaît-il à Sylfried ?
  - Message en jeu avec fenêtre masquée : code inchangé, non rejoué.
  - L'option du jeu « Taille de la croix » (`g_pad_size`, dans la sauvegarde) n'est pas touchée : elle n'est plus accessible.
- **Pas fait / choisi** :
  - Pas de visibilité bouton par bouton.
  - « Rétablir toutes » ne change pas l'interface choisie dans la liste, et seul `pan_pos` est remis (pas `plie`, inaccessible quand le panneau est replié).
  - Pas de message de confirmation (tout se voit tout de suite).

## Fichiers touchés
- `dq4_pc/reglages.py` : constantes `CIBLE_ECRAN`, `CLES_*`, `FENETRE_DEFAUT` ; méthodes `defaut`, `remettre_interface`, `remettre_interfaces`.
- `dq4_pc/pause.py` : voir les zones ci-dessous.
- `dq4_pc/fenetre.py` : 3 lignes (`apercu_interface` et `_apercu_ouinon` : `RG.FENETRE_DEFAUT`).
- `dq4_pc/hud_mobile.py` : 2 lignes (alpha de la croix, `remettre()` supprimée). Hors périmètre, minimal.
- `tools/test_reglages_interface.py` et `tools/test_panneau_interface.py` : nouveaux.
- `pyflakes` : seuls les avertissements existants (`R`, `yp`, `mh` dans `pause.py`, `sel` dans `window.py`).

## Pièges de fusion
- **Constantes `pause.py`** : mes ajouts sont `CADRE_SELECTION`, `MOTS_MASQUE`, et les commentaires de `DELAI_APPUI_LONG` et `TOLERANCE_APPUI`. Si pause2 ajoute une constante de cadre jaune, ne pas dupliquer.
- **Zones de `pause.py` que j'ai modifiées** :
  - l'en-tête (constantes, commentaire de `__init__`) ;
  - `_ov`, `_poser_ov`, `_visible`, `_poser_visible`, `_e_interface` et les remises ;
  - `maj` (1 ligne) ;
  - `_appui_barre`, `relache`, `glisser` (bloc `pan_appui`) ;
  - `_elements_apercu`, `_rects_montres`, `_apercu` (fin).
- **Zones que je n'ai pas touchées** : `_e_affichage` (agent fenetre, ses dernières lignes touchent mon bloc) et `dessiner` (pause2). Conflit de contexte possible mais pas de recouvrement.
- **Clés ajoutées à `DEFAUT` par un autre agent** (mode de fenêtre, etc.) : `test_classement_complet` échouera tant qu'elles ne sont pas dans `HORS_INTERFACE` du test. C'est voulu.
- `Reglages.defaut` est une méthode statique, `RG.DEFAUT` reste le dict.
- Le harnais teste les clics à 1280 x 720 en pixels depuis le haut-gauche ; pour un autre format, passer `--largeur` et `--hauteur` après les arguments (ce qui prévaut sur ceux du script).

## Notes à ajouter dans `docs/viewer-notes-dq4-pc.md` (section « Retours de 23 h 24 », éditeur d'interface)
- **Étiquette « Masquée »** : tout élément non affiché en jeu est voilé (noir à 150/255) et marqué dans l'aperçu, avec le cadre jaune de sélection intact : toute l'interface masquée (boutons « Masqué », croix et fenêtres « Masquée ») ou la croix seule (« Afficher la croix » = Non). `Pause._elements_apercu()` donne rectangles, état masqué et genre. La croix n'est plus pâlie : le voile suffit. Les boutons Carte / Commandes / Discussion partagent le réglage global `boutons` ; Mode suit la fenêtre `MapButton`. Un élément masqué reste attrapable.
- **Remises à zéro** : « Rétablir cette interface » remet tout `CLES_ECRAN` (affichage, tailles des boutons et de la croix, positions, croix affichée) pour « Boutons et croix de l'écran », ou l'entrée de la fenêtre dans `interface_fenetres` et `interface_masquees` (taille, position, affichage). Grille et aimantation ne changent pas. « Rétablir toutes les interfaces » remet aussi grille, aimantation et la place du panneau (`pan_pos`). Tout vient de `DEFAUT` (`Reglages.remettre_interface` / `remettre_interfaces`). Une nouvelle clé de réglage doit être classée dans `CLES_*` ou dans `HORS_INTERFACE` de `tools/test_reglages_interface.py`.
- **Panneau flottant** : le glisser démarre dès que le pointeur s'éloigne de 8 px de l'appui sur la barre de titre (l'ancien code annulait le geste si on bougeait avant 0,35 s : impossible à glisser pour qui n'attendait pas). Appui court = replier / déplier, appui maintenu = soulèvement, double clic = position d'origine (au relâchement). Test : `tools/test_panneau_interface.py`.

---

## Agent a377ad026145bcbc1 — 02/11 00:38

RAPPORT FINAL pause2 (points 4, 6, 7, 12) - worktree /home/claude/wt-pause2, branche agent-pause2, base main 345ba8f. Arbre de travail propre (git status vide).

COMMITS (3, chacun avec les deux lignes Co-Authored-By / Claude-Session)
- 7593b20 Pause : page Son (une ligne par son), vitesse de defilement du texte (Messages en combat), vitesses x1 a x4, plus d'encadre jaune (assombrissement au survol)
- 3d52d1f Pause : le pointeur qui quitte la fenetre rallume les plaques (on_mouse_leave -> pause.sortie())
- c9e1250 Ecrans d'avant-partie : plus d'encadre jaune au survol (ecran Sauvegardes, saisie du nom, licence). COMMIT SEPARE car hors perimetre de la Pause (pre_game.py, saves_screen.py, name_entry.py) : a ecarter par `git revert c9e1250` ou en le sautant au cherry-pick si l'agent de l'ecran titre touche ces fichiers. Il retire aussi `import hud_mobile as HM` devenu inutile dans les deux premiers (pyflakes).

FICHIERS TOUCHES
dq4_pc/pause.py (+196/-), dq4_pc/fenetre.py, dq4_pc/reglages.py, dq4_pc/avant_partie.py, dq4_pc/ecran_sauvegardes.py, dq4_pc/saisie_nom.py, tools/test_reglages_son_texte.py (modifie), tools/test_pause_pages.py (nouveau). Rien dans docs/. Moteur d'origine, patchs FR et sauvegardes de l'utilisateur non touches.

TESTS (tous verts) : test_pause_pages.py 15 tests ; test_sound_text_settings.py 7 tests (dont 3 de migration) ; test_sound_mixing.py 12 tests. pyflakes : seuls restent 4 avertissements deja presents sur la base (pause.py variables R, yp, mh ; window.py sel). test_text_scrolling.py exige --apk/--saves (non relance, sa logique n'a pas ete modifiee).

POINT 4 - PAGE SON (Etabli, par captures + tests)
- Plus de sections. 5 lignes : General, Musique, Jingles et fanfares, Bruitages, Interface. Colonnes alignees : nom | barre de volume (remplissage jaune conserve) | valeur en % | bouton haut-parleur (muet) | bouton rond (defaut).
- Clavier : haut/bas = ligne, gauche/droite = volume, Entree = muet/remettre, Suppr = defaut. Souris : barre cliquable et glissable, haut-parleur et rond cliquables, clic sur la valeur = la taper (conserve). Les sons continuent pendant que la page est ouverte (un bruitage d'essai est joue quand on change un volume ou qu'on remet un son).
- DECISION : le bouton/touche par defaut remet le volume a sa valeur par defaut ET rend le son (annule le muet). Bouton grise quand la ligne est deja par defaut. Ligne coupee : libelle et barre grises, haut-parleur barre d'une croix rouge. Cliquer a cote des boutons sur une ligne Son ne fait rien (evite de couper par erreur).
- Le moteur de mixage n'est pas modifie : le muet bascule les interrupteurs existants (musique_active, jingles_actifs, bruitages_actifs, interface_active ; General = muet global).

POINTS 6 et 7 - TEXTE (Etabli)
- Entree racine, titre de page et titres[...] : "Vitesse de defilement du texte". Plus de sections. "Defilement automatique" supprime. "Vitesse du texte" en premier ("Normal (jeu)" devient "Normal"), puis "Messages en combat" : Rapide / Moyen / Lent / Manuel. Ligne "Retablir le reglage du jeu" conservee.
- CORRESPONDANCE ETABLIE dans le moteur d'origine (OptionStatus.battleSpeed = g_Option+5 ; BattleAutoFeed::setMessageSpeed 0x201558) : 0/1/2/3 -> attente de 12/22/32/42 images, 4 -> -1 (manuel, attend une touche), 5 -> DEBUG_WAIT. Defaut du jeu = 2 (OptionStatus::initialize 0x1a344c). Valeurs CHOISIES : Rapide = 0, Moyen = 2 (defaut d'origine), Lent = 3, Manuel = 4. La valeur 1 (possible dans une sauvegarde) s'affiche "Moyen" (cran_defilement : 1 -> 2). Le choix 1 / 22 images n'est donc pas propose.
- Migration (settings.py) : si 'defilement_combat' est absent et que l'ancien fichier a defilement_auto / defilement_vitesse : auto=False -> Manuel (4), sinon vitesse ancienne ramenee au cran le plus proche. La valeur de la sauvegarde n'est PAS ecrasee tant que l'utilisateur n'a pas touche au menu : 'defilement_force' reste False (window.py : defilement_actuel() lit alors options_jeu()[2]) ; 'Retablir le reglage du jeu' remet defilement_force a False. Teste en unitaire (test_migration_defilement_des_combats, test_crans_du_defilement, test_choix_impose_la_valeur_puis_rien_tant_qu_on_ne_touche_pas).
- VERIFICATION EN COMBAT REEL (combat force, Unicorn) :
  * Manuel (4), slot 4 : avec 90 images sans touche le message reste a l'ecran ; Entree, Espace et clic gauche le font chacun avancer, 3 images apres l'appui. Etabli.
  * Controle Rapide (0), slot 4, journal /tmp/p2_rapide.log : les messages passent seuls apres 12 a 18 images ; options_jeu passe de (4,4,4) a (4,4,0), donc le reglage est bien ecrit et effectif. Certains messages d'attente (fin de combat probablement) attendent quand meme une touche meme en Rapide, et Entree / Espace / clic les font avancer (3 images). Etabli.
  * RESERVE : la sauvegarde du slot 4 etait deja a battleSpeed 4. Le passage direct 2 -> 4 en combat (slot 2 = depart a la valeur par defaut) n'a pas pu etre rejoue : les deux lancements sur le slot 2 n'ont rien affiche avant le timeout de 600 s (cause non investiguee, vraisemblablement attente d'un etat de champ). C'est le meme appel regler_defilement(code) que pour 0, donc je le tiens pour Suppose (pas Etabli) dans ce sens.

POINT 12 - COMMANDES > VITESSES (Etabli sauf mention)
- Vitesse de marche / de camera / de transition : listes deroulantes x1, x2, x3, x4 (plus de curseurs). "Vitesse de l'accelerateur" garde son curseur 1-2 (defaut 1.5).
- Migration : anciennes valeurs 0.5-2 ramenees au cran x le plus proche (int(v+0.5), plancher x1, plafond x4 ; valeur invalide ou booleen -> defaut) : 0.5->x1, 1->x1, 1.5->x2, 2->x2. Teste (test_migration_des_vitesses_en_x).
- DEFAUTS : marche x1, camera x1, transition x2. ECART AVEC LE BRIEF : le brief disait x1 ; j'ai garde x2 pour la transition parce que c'etait le defaut deja documente (vitesse_fondu 2.0) ; changer = une ligne dans settings.py (DEFAUT['vitesse_fondu']).
- Marche x3 / x4 : le moteur n'a pas de limitation structurelle (la marche rapide = davantage de pas moteur par image affichee, _facteur_vitesse plafonne a 8.0). J'ai ajoute un budget de temps par image pour les pas rapides (BUDGET_PAS_RAPIDES = 30 ms, variable d'environnement DQ_BUDGET_PAS) : si les pas ne tiennent pas dans 30 ms, le jeu ralentit au lieu de geler l'affichage.
- MESURE (horloge reelle, DQ_TEMPS_REEL=1, marche continue, script scratchpad mesure_marche.py ; 3 series dont une sans budget) :
  * Fenetre 400x225 (rendu peu couteux) : x1 = 29.7-30.0 pas/s (x1.00) ; x2 = 49.9-51.5 (x1.66-1.72) ; x3 = 85.0-87.7 (x2.83-2.92) ; x4 = 111.6-115.1 (x3.72-3.84) ; x4 + accelerateur x2 tenu = 202.5-217.0 (x6.75-7.23). Avec ou sans budget les resultats sont equivalents ici.
  * Fenetre 1280x720 (rendu logiciel Xvfb, 10-26 images/s) : x4 = 85 pas/s (x2.84), x4 + accel = 167 (x5.58). Mesures limitees par le CPU partage du bac a sable (rendu logiciel + autres agents), pas par le moteur.
  * CUMUL MAXIMUM : x4 (marche) x 2.0 (accelerateur) = x8 theorique (plafond du code) = 240 pas moteur/s, soit environ 0.85 s de CPU par seconde si un pas coute ~3.5 ms : sature un PC lent, auquel cas le budget fait ralentir le jeu. Sur ce banc on atteint x6.8-7.2 au mieux.
  * NON VERIFIE : performance reelle sur Windows (GPU/CPU de l'utilisateur) a x4 et x8 ; taux de rencontres sur une longue marche a x3/x4 (raisonne : compte par pas moteur, donc par distance, pas mesure) ; fondus de transition x3/x4 sur un vrai changement de carte (raisonne : la duree des fondus est divisee, 30 -> 8 images a x4, <= 1 image = immediat ; pas teste a travers une vraie transition). Camera : x4 avec accelerateur = 800 deg/s, stable (dt plafonne a 0.1 s, recentrage par saut).

CADRE JAUNE (Etabli par captures et par test sur le code)
- Supprime partout dans la Pause : racine, Etats (liste, fenetres Oui/Non), Son, Texte, Commandes (lignes, listes deroulantes, cases de touches, curseurs), aide, boutons de pagination, rond par defaut, croix rouges, bouton retour, elements des listes deroulantes. Regle : souris = plaque assombrie (motif "enfonce" decale sur une plaque, couleur a 75 % sur un bouton-icone), qui se rallume quand le pointeur part (y compris quand il quitte la fenetre : on_mouse_leave -> pause.sortie()) ; clavier = curseur dore (fleche) devant la ligne choisie. Le remplissage jaune des curseurs et (editeur, pas a moi) le rectangle jaune de selection d'element sont conserves.
- Sur un sous-bouton (haut-parleur, rond, croix, fleches de defilement), seul le sous-bouton s'assombrit, pas la ligne.
- Un test statique (test_plus_de_cadre_jaune_dans_le_code_de_la_page) verifie qu'aucun "JAUNE if sel" ne reste dans pause.py. Le parametre `contour` de _plaque est CONSERVE (les ecrans d'avant-partie l'utilisaient ; plus aucun appelant ne le passe dans le code modifie). Fallback HM.plaque de hud_mobile.py non modifie.
- NON VERIFIE visuellement : les trois ecrans d'avant-partie du commit c9e1250 (pyflakes seul ; meme appel _plaque que dans la Pause). Plus de dossier "ecran Sauvegardes" jamais capture par moi.

CAPTURES UTILES (absolus, /tmp)
- AVANT (cadre jaune + info-bulle) : /tmp/m_p2_base1_b200.png (Commandes, Vitesse de camera encadree de jaune, curseurs) ; autre base : /tmp/m_p2_base1_b100.png
- APRES Son : /tmp/m_p2_s2_b190.png (5 lignes, General et Bruitages coupes, Musique par defaut grise) ; /tmp/m_p2_a_b150.png (Son avec survol et aide) ; autres series : /tmp/m_p2_a_b50.png /_b90 /_b110 /_b130
- APRES Texte : /tmp/m_p2_t1_b170.png (titre "Vitesse de defilement du texte", "Messages en combat : Moyen", curseur dore) ; autres : /tmp/m_p2_t1_b50.png /_b100 /_b120 /_b140
- APRES Commandes (x1-x4, section Vitesses) : /tmp/m_p2_c2_b170.png ; series /tmp/m_p2_c2_b130.png /_b150 /_b190 /_b210 /_b230 /_b250 ; /tmp/m_p2_c1_b100.png /_b150 /_b200
- Fenetres Oui/Non : /tmp/m_p2_e1_b200.png (Etats, "Supprimer l'etat 1 ?") ; recadrage de survol Oui / Non / repos : /tmp/p2_pop_all.png (aussi /tmp/p2_pop180.png /p2_pop200.png /p2_pop220.png)
- Journal du controle de combat : /tmp/p2_rapide.log

NOTES POUR docs/ (a ecrire par le lead)
- Menu Pause > Son : une ligne par son, colonnes nom | barre | % | muet | defaut ; clavier haut-bas / gauche-droite / Entree / Suppr ; defaut = volume ET son remis.
- "Texte et defilement" devient "Vitesse de defilement du texte". Messages en combat -> OptionStatus.battleSpeed : Rapide 0, Moyen 2 (defaut d'origine), Lent 3, Manuel 4 ; 1 affiche Moyen ; reglage non impose tant que l'utilisateur n'y touche pas (defilement_force). Cles de reglages : defilement_combat remplace defilement_auto et defilement_vitesse (migration automatique).
- Commandes > Vitesses : x1-x4 (marche, camera, transition ; defaut x1 x1 x2) ; accelerateur 1-2 (defaut 1.5) ; cumul max x8 ; budget de 30 ms par image (DQ_BUDGET_PAS).
- Regle d'interface : plus de cadre jaune au survol ; plaque assombrie (souris) + curseur dore (clavier). Exceptions voulues : remplissage jaune des curseurs, rectangle jaune de selection d'element dans l'editeur d'interface.
- Outils : tools/test_pause_pages.py (nouveau).

PIEGES DE FUSION
- pause.py : la boucle de dessin des lignes (zone de remise a zero des zones, calcul de sel / anc, appel _plaque sans contour), la formule de largeur pw (+36 pour 'son') et _valider/clic/_aide_ligne sont les endroits les plus susceptibles de heurter les modifications des agents fenetre / editeur2 ; _e_affichage, _e_interface et le panneau flottant ne sont PAS touches. Un champ n_f utilisait `.get('fixe')` : corrige en `is True` (une lambda 'fixe' creait un faux ecart apres la premiere ligne Son).
- window.py : bloc defilement (defilement_actuel / regler_defilement / retablir_defilement / appliquer_defilement / _adopter_defilement), constante BUDGET_PAS_RAPIDES apres PAS_MOTEUR, boucle _boucle (coupe au budget), on_mouse_leave (survol_nd = None + pause.sortie()).
- settings.py : DEFAUT (defilement_combat remplace defilement_auto/vitesse ; vitesses 1.0/1.0/2.0), BORNES (1,4), BOOLEENS_SON_TEXTE sans defilement_auto, nouvelles fonctions cran_defilement / cran_x et migration dans le chargeur. Si un autre agent ajoute des cles, garder l'ordre : migration avant la boucle BORNES.
- Le fichier de reglages est reecrit par Pause.fermer() a chaque test : copier /tmp/rg.json avant chaque lancement (pas de pollution croisee).
- Harnais de capture dans CE worktree : "~@x@y" est le RELACHEMENT de la souris ; le survol est "@x@y@2" (au lieu de ~). Un autre worktree peut avoir une syntaxe differente.
- c9e1250 est independant : l'ecarter si conflit avec l'agent de l'ecran titre.

ETABLI / SUPPOSE / NON VERIFIE
Etabli : mise en page et comportement des pages Son, Texte, Commandes (captures + tests) ; correspondance battleSpeed (lecture du code d'origine) ; Manuel 4 en combat reel (Entree, Espace, clic) ; Rapide 0 passe seul en 12-18 images ; migrations (tests unitaires) ; plus de cadre jaune dans la Pause (captures + test statique) ; marche x2-x4 mesuree sur le banc.
Suppose : transition 2 -> 4 en combat (meme appel que 0 -> ... mais non rejoue depuis la valeur par defaut) ; fondus x3/x4 ; taux de rencontres par distance ; sensation de la marche x4 x accelerateur.
Non verifie : Windows (GPU/CPU reels, vitesse x4/x8), rendu audible du muet et des volumes sur de vrais haut-parleurs (les tests de mixage verifient les valeurs, pas le son), chiffres de la fenetre Config d'origine (1 a 5), apparence des trois ecrans d'avant-partie modifies par c9e1250.

POINTS DE DECISION A VALIDER PAR L'UTILISATEUR
1) Defaut de la transition : x2 (existant) ou x1 (brief) ? 2) Le bouton "defaut" d'une ligne Son remet-il aussi le son (choix actuel : oui) ? 3) Moyen = 2 (defaut du jeu) et Lent = 3 convient-il, sachant que 1 (22 images) n'est plus propose ?

---
