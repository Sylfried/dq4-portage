## Agent a26ba55965f699b65 — 02/11 03:21

RAPPORT « options » (worktree /home/claude/wt-options, branche agent-options, base 08f5785). Arbre propre. 1 commit : 41b3ee8 (sujet A). Sujet B : aucun commit (essai de correction annulé, voir plus bas).

=== A. Le jeu prime sur les réglages du joueur ===
Code : nouveau module sans dépendance dq4_pc/priorite_jeu.py (valeur_effective(reglage_joueur, valeur_jeu=None), facteur_effectif, lettres_par_image, duree_fondu). Trois corrections réelles : marche, zoom, fondus de script. Le texte était déjà correct dans DQ4 : je l'ai seulement passé par la fonction pure.

ÉTABLI
- Texte : DQ4 n'a aucune commande de script ni écriture du mot de vitesse (MSG_VITESSE 0x2523b0) hors ui_MsgSetup, qui le copie du tableau par type de fenêtre (types 0,1,2,5 = 1 ; 3,4 = 100). Le crochet de ui_MsgLoop+0x128 ne remplaçait déjà que la vitesse standard (4 lettres/image) ; il passe maintenant par lettres_par_image, même comportement. Test moteur : en écrivant le mot à 2 (comme le ferait un script), la durée est identique (15 images) pour 0,5 / 4 / 16 / 4000 lettres/image ; sans cela le réglage joue (140 images à 0,5, 11 à 16). test_text_scrolling.py repasse à l'identique (24 images à 4,0 ; attentes de combat 12/22/32/42).
- Défilement des messages de combat (battleSpeed g_Option+5) : écrit seulement par la fenêtre Paramètres et le chargement d'une sauvegarde ; les cas où le jeu bloque l'avance auto (disableAutoFeed, setDisableCursor) sont des drapeaux séparés que le réglage ne touche pas. Inchangé.
- Marche x1 à x4 + accélérateur : jusqu'ici _facteur_vitesse accélérait l'horloge du moteur dès qu'une direction était tenue, même pendant une scène sans message. Global.Flag mesuré : exploration libre = 0x38 (ville), 0x28 (carte du monde) ; scène du jeu = 0x3c (bit 4 = verrou du joueur) sans message (83 images dans la sauvegarde 2, prologue : 0x1c/0x1d pendant tout le prologue) ; fondu = bit 1. Maintenant facteur 1.0 si Flag & (1|4) (constantes MO.DRAPEAU_FONDU, MO.DRAPEAU_JOUEUR_VERROUILLE).
- Fondus (« Vitesse de transition », x2 par défaut) : les commandes de script fade_in / fade_out (__cmd_fade_in::initialize 0x21b3c0, __cmd_fade_out::initialize 0x21b43c) donnent leur durée (sauvegarde 2 : fade_out 30 images à l'image 6, fade_in 60 à l'image 385) et attendent elles-mêmes ce nombre d'images (isEnd compte les images). Raccourcir le fondu ne faisait donc que laisser l'écran noir plus longtemps. Crochet dans Moteur._crochets_fondu : le paquet 9 reçoit la marque bit 16 (PJ.MARQUE_FONDU_SCRIPT) quand UnitySetFade (0x17e120) est appelé depuis ces deux fonctions ; Etat._fondu ne raccourcit pas ces fondus. Fondus du moteur (changements de carte : 45, 30, 60 images) toujours raccourcis ; fondus en couleur / blancs jamais. Mesuré à x4 : script 30 → 30, 60 → 60 ; moteur 30 → 8, 45 → 11, 60 → 15.
- Caméra : rotation / inclinaison manuelles et vitesse de caméra sont déjà neutralisées par cam_bloquee (verrou TownCamera ou rotation interdite) ; « caméra centrée » déjà soumise à cam_jeu / cam_libre. Inchangés.
- Tests : tools/test_priorite_jeu.py (12 tests, OK : règles pures, _facteur_vitesse sur faux objet, zoom, moteur avec --apk/--saves/--slot/--slot-fondu 2), test_sound_text_settings.py (+1 test) ; test_camera_ville, test_pause_pages, test_reglages_interface, test_mode_fenetre, test_panneau_interface, test_son_mixage OK ; smoke fenêtre xvfb OK (RG=/tmp/rg_opt_sm.json, marche x3). pyflakes : seulement les avertissements connus.

SUPPOSÉ
- Zoom (distance de la caméra, molette) : facteur_effectif(zoom, e.cam_libre) → sans zoom pendant une caméra libre de scène (position, angles, champ fixés par le script). Pendant un travelling (cam_jeu), le jeu ne fixe que la cible : le zoom est gardé.
- Le fondu de script reconnu = seulement fade_in / fade_out ; je pars du principe que le joueur ne veut pas que ces fondus soient raccourcis.

NON VÉRIFIÉ
- DQ5 / Nimzo : pas de moteur DQ5. Un script qui fixerait précisément la vitesse standard (mot 1) serait pris pour le défaut ; il faudrait alors un crochet d'écriture mémoire sur le mot.
- Aucune scène cam_libre observée dans mes traces (8 cartes) : la correction du zoom n'est testée que sur faux objet.
- Boucle fenêtre avec une direction tenue pendant le prologue : couvert par test unitaire + sonde des flags, pas par une capture.
- Non traité : le fondu du titre de chapitre (Global::fadeInBlack(60), appelé par cmd_event_chapter_title, adresse 0x18da7c) reste raccourci (commande de script, mais pas via fade_in/fade_out). Aussi, la normalisation « zoom commun » HEROS_FRAC écrase la distance / le fov fixés par script hors cam_libre (choix de la visionneuse, pas un réglage joueur) : non touchée.

TABLEAU A.1 (réglage → le jeu peut-il le fixer ? → traitement)
- Vitesse du texte → DQ4 : non (table par type de fenêtre) ; détecté par le mot ≠ standard → déjà respecté ; règle pure + tests.
- Messages en combat (defilement_force / combat) → non par script (Paramètres + sauvegarde) ; drapeaux d'avance auto prioritaires par construction → inchangé.
- Vitesse de marche + accélérateur (clé vitesse_accel) → oui (scènes : verrou 4, fondu 1) → CORRIGÉ (facteur 1.0).
- Vitesse de caméra / accélérateur de caméra → oui (verrou TownCamera, rotation interdite) → déjà neutralisé (cam_bloquee).
- Distance de la caméra / molette → oui (caméra libre de scène) → CORRIGÉ (neutre en cam_libre ; cam_jeu : zoom gardé, supposé).
- Caméra centrée → oui (cam_jeu, cam_libre) → déjà prioritaire au jeu.
- Angle / lacet de la caméra → oui (verrou) → déjà neutralisé.
- Vitesse de transition → oui (fade_in / fade_out de script) → CORRIGÉ (marque du paquet 9).
- Volumes, interrupteurs son → non : les paquets 35-37 ne portent que l'identifiant ; volume du fichier et option « volume » du jeu déjà multipliés → N/A.
- Luminosité, netteté, vignette, MSAA, échelle de rendu, lissage, sprites, mode fenêtre, résolution, taille des dégâts, correction des bords → pas de paramètre équivalent côté jeu (la luminosité est une passe finale après les effets d'écran du jeu) → N/A.
- Boutons / croix / fenêtres masquées ou déplacées → choix d'affichage du joueur ; le jeu masque déjà par PLAYER_LOCK / GUI_LOCK (hud_mobile.visibles) → N/A.
- Touches → N/A.
Réglage de l'agent « combat » touché par mon inventaire : vitesse_accel, via _facteur_vitesse (je lis la clé, pas le libellé : le renommage en « Multiplicateur de l'accélérateur » n'a aucun effet sur mon code).

=== B. « Le nom de Ragnar est trop bas » ===
Avis : impression fondée mais faible ; je n'ai rien changé.
ÉTABLI
- Capture 1280x720 (/tmp/c_opt_av_230.png, rendu actuel inchangé) : intérieur du bandeau y 30 à 48 (centre 39) ; majuscules y 35 à 46 (centre 40,5), soit 1,5 px sous le centre (≈ 2,3 px à 1080p) ; marge haute 5 px, ligne de base à 3 px du séparateur, queue du g à 0-1 px (elle touche). Cohérent avec ta capture /tmp/specs/img43/s4_nom_ragnar_combat.png ; l'onglet « Ragnar » de la fenêtre de commandes (s5) paraît bien centré.
- Type 29 : nom = TextMesh ancre 1 (UpperCenter, cs 9,3925, ls 0,8013, z 385,5) ; lignes PV/PM/Nv. = ancres 0 et 2 (Upper, ls 1,258, z 359). Toutes ancrées en haut : base0 = zp − ascent, indépendant de lineSpacing, donc même formule pour le nom et pour PV/PM/Nv. (qui s'alignent bien sur leurs jauges).
- Essai d'un recentrage global (« glyphes centrés dans leur cellule de ligne » dans Fenetre._texte) : remonte le nom de 2 px mais DESCEND PV/PM/Nv. de ~1,5 px (les chiffres touchent les jauges). Régression → annulé. Comparaison : /tmp/c_opt_cmp_plaque.png (gauche = rendu actuel conservé, droite = essai rejeté) ; plein cadre : /tmp/c_opt_av_230.png (actuel) et /tmp/c_opt_ap_230.png (essai) ; autres images /tmp/c_opt_av_{170,185,200,215}.png et /tmp/c_opt_ap_*.
SUPPOSÉ
- Le décalage vient des données (z 385,5 + biais dy) et pas d'une erreur de la visionneuse : l'original aurait le nom aussi bas. À confirmer avec une capture de téléphone de la plaque.
NON VÉRIFIÉ
- La formule exacte de TextMesh dans libunity pour la police bitmap (ancres Middle : N pas ou (N-1) pas + une ligne, ≈ 1 px d'écart, concerne les onglets de type 32, pas ce nom).
- Si tu veux quand même le remonter : décalage ciblé des textes de la plaque type 29 de ≈ 1,5 px (720p), choix arbitraire à valider.

=== Notes de doc à fusionner (rien écrit dans docs/) ===
- notes-visionneuse : section « Priorité du jeu sur les réglages du joueur » : principe (réglage = valeur par défaut, le jeu prime quand il fixe la valeur), tableau A.1, règles pures de game_priority.py.
- notes-technique : Global.Flag en pratique (libre 0x38 ville / 0x28 carte du monde, scène 0x3c, fondu bit 1 : 0x39 / 0x3d, combat avec bit 4 posé) ; UnitySetFade 0x17e120 écrit [9, v] et lève le bit 0 ; __cmd_fade_*::initialize appellent Global::fadeOutBlack (0x17d600) / fadeIn (0x17dfec) avec durée = (arg + 1) >> 1 et plan de fond via [Global+0xec] ; fondus du moteur vus : fadeOutBlack(45) en 0x15357c, fadeInBlack(30) en 0x18d9f0, fadeInBlack(60) en 0x18da7c ; durée = bits 0-10 de v, marque visionneuse = bit 16.
- Piège Unicorn : un crochet ajouté après qu'un bloc a été traduit ne se déclenche pas ; les installer dans Moteur.__init__ avant les step (comme _crochets_texte) et appeler ctl_flush_tb().
- Aides de la page Commandes (non touchées) à compléter par qui fusionne : « Vitesse de marche » → ajouter « les scènes et les fondus du jeu gardent leur rythme » ; « Vitesse de transition » → « sauf les fondus qu'un script du jeu fixe lui-même ».

=== Pièges de fusion ===
- window.py : _facteur_vitesse (+1 ligne après le test pad(), docstring) ; l'agent « combat » y touche probablement : si le facteur est étendu au combat, NE PAS reprendre mon test de verrou (le bit 4 est posé en combat : flags 0x2d / 0x6e observés). _camera_ville : th_v /= PJ.facteur_effectif(self.zoom, e.cam_libre) ; import priorite_jeu as PJ ajouté après import reglages as RG.
- engine.py : import priorite_jeu as PJ après import emu_core ; constantes DRAPEAU_* près de COMBAT_MANUEL ; corps de _vt dans _crochets_texte ; nouvelle méthode _crochets_fondu insérée avant _option, appelée juste après self._crochets_texte() dans __init__ ; Etat._fondu (2 lignes).
- pause.py et settings.py : non modifiés (aucune nouvelle option).
- Les fondus de script ne sont plus raccourcis : les captures ou tests de durée qui comptaient sur « fondus x2 » dans une scène à fade_out / fade_in changent.

Fichiers touchés : dq4_pc/priorite_jeu.py (nouveau), dq4_pc/moteur.py, dq4_pc/fenetre.py, tools/test_priorite_jeu.py (nouveau), tools/test_reglages_son_texte.py. dq4_pc/ui_menu.py : modifié puis rétabli (aucune différence avec 08f5785).
Hors dépôt (scratch) : /tmp/run_opt.sh, /tmp/rg_options.json, /tmp/rg_opt_sm.json ; sondes dans /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/ (sonde_verrou*.py, sonde_fondus*.py, sonde_marque.py). Rien de mémorisable côté utilisateur (aucun fait personnel appris).

---

## Agent ad9be5b9dfd5bdfb2 — 02/11 03:22

RAPPORT COUVERTURE (agent audit, lecture seule). Livrable complet : /tmp/audit/couverture.md (7 sections + synthèse en tête, ~59 Ko). Dépôt intact (git status vide dans /home/claude/wt-audit), aucun commit. Écritures seulement dans /tmp/audit et /tmp/sv_audit_*.

SYNTHÈSE
- ÉTABLI : balayage v2 headless de 529 cartes (90 images, 123 s au total) : 528 sans plantage, 0 sprite sans feuille (les 93 ids existent dans le datapack), 0 PNJ hors carte (507 cartes analysables), 0 fondu bloqué. Le flux moteur→visionneuse est sain ; les trous sont dans ce qui est ignoré ou jamais joué.
- ÉTABLI : 16 sites d'écriture mémoire de la visionneuse (§4), aucun ne touche scénario, variable, or, inventaire ou position. Seul point à surveiller : g_Option+5 (défilement des combats) est écrit chaque image quand l'option est imposée, donc enregistré dans les sauvegardes du jeu (ce dernier point : Supposé, non essayé). Les originaux de sauvegarde ne sont jamais ouverts en écriture (engine.py:41,53).

LACUNES LES PLUS GRAVES (avec preuves)
1. Poker invisible (ÉTABLI, GL) : gl_poker_b330.png = écran noir + fenêtres ; gl_pokerv_b330.png (même scène, affichage forcé en "ville" par mon lanceur hors dépôt) montre les 5 cartes. Cause : garde `e.partie == MO.PARTIE_VILLE` à window.py:2913 ; le casino est la partie 0xf, inconnue de la visionneuse (engine.py:8-11 ne définit que 3, 0xc, 0xd, 0xe). La carte ev04 n'a ni sol ni texture : tout est maillage dynamique (paquets 21/22).
2. Machine à sous injouable au clavier (ÉTABLI, GL) : le clavier (Haut×3 + Entrée) laisse la mise à 0 (gl_slotkb_b420.png), la souris marche (gl_slotms_b350.png : Jetons 497, rouleaux). Cause : `_saisie_menu` (window.py:1597-1621) n'expose que les boutons de manette 0x10 ; ▲/▼ sont 0x2/0x1 et la fenêtre n'a pas de grille moteur. Côté moteur, slot et poker sont jouables (mise 500→497, rotations, arrêt, sortie propre).
3. Bestiaire (partie 0x10, ÉTABLI GL) : liste et fiche en texte OK, mais le monstre n'est pas dessiné et l'église mak1f1 apparaît dans son cadre (gl_booksel_b330.png). Le moteur envoie pourtant le maillage (paquet 22). Forcer la partie en ville ne change rien (capture identique octet pour octet) : cause NON trouvée.
4. Paquet 33 (map_color_rate) ignoré : émis sur 171/529 cartes au chargement (149 en (1,25;0,65;0,75), 20 `te*` en (1,3;0,7;0,55), caf1/ev02 animé). Côté Unity (cmd_map_color_rate, RVA 0xD14E44, désassemblé) = Field.SetColor(r,g,b,1). Porte aussi le jour/nuit de la carte du monde (FieldStage::ChangeTime) et le marais (FieldPlayerDoku). Effet visuel exact : Supposé.
5. Paquets ignorés sans trace (ÉTABLI, aucune branche dans Etat.appliquer) : 1, 6 (animations d'événements, dont gain de la machine à sous), 16/17/18 (poses couché, auberge ; vus dans mlb1a, mlm2f1, taf1), 27 (contourné par lecture mémoire), 30 (zoom du ballon), 33. Paquet 13 : échelle de sprite (bit 0x800) lue puis jetée (mlb1a 0,738, ev07 0,952 : effet Supposé). Paquet 34 : seule la valeur 4 est rejouée.
6. Boutiques, banque, église (résurrection, sauvegarde), auberge, arène, colisée, bateau, ballon, chariot, générique : INCONNU, jamais ouverts (aucun test automatique ne les atteint ; seul le type 12 s'ouvre au chargement). Ils passent par des commandes de script (cmd_menu_shop/save/colosseum/extra_shop/nene/hostage/present_exp/event_imuru, cmd_the_end). C'est la plus grande zone sans information.

NON VÉRIFIÉ (détail §6) : gameplay des points ci-dessus (j'ai tenté d'ouvrir une boutique par le moteur, abandonné : il faut l'objet CommandWindow ou poser le héros devant le marchand) ; rendu Windows/GPU réel (tout est Mesa/xvfb) ; décodage des 686 .akb (sound.py avale 12 exceptions) ; combats complets ; carte du monde jour/nuit, ballon, bateau ; poker jusqu'au bout ; ev01 (plante par startTown, Supposé artefact du lanceur car le titre le charge) ; effet exact de UnityInitTouchFlag.

POUR LE BALAYAGE (§5) : startTown(nom) ne place PAS le héros à l'entrée (235 sprites héros/équipier à la position héritée (1,97 ; 0,047 ; 44,08) sur 117 cartes) : à résoudre avant le niveau 2. Coût mesuré N1 : 0,23 s/carte (90 images) ; estimé 600 images ≈ 14 min en 1 processus, ≈ 7 min en 2 (indices 0-265 / 265-529). N2 (parler à chaque PNJ) ≈ 25 min sur 2 cœurs (estimé). N3 (captures GL en un seul processus, un seul xvfb à la fois) ≈ 35-55 min (estimé). Règles de détection R1-R12 dans §5.4.

NOTES À FUSIONNER DANS LES DOCS (§7) : (a) la ligne "classes IBase personnalisées non reproduites" des notes techniques est périmée, les 5 classes sont portées (ui_menu.py:199-413) ; (b) le paquet 33 n'est pas limité à mlb1a (notes-technique:233) ; (c) parties moteur 0xf casino et 0x10 bestiaire inconnues de la visionneuse ; setMinigame(0)=poker ev04, autre=slot ev05 ; startBook ← TownMenuItemSelectCommand::menuUpdate ; startSurechigai ← cmd_change_surechigai_part ; (d) clavier : boutons de manette 0x2/0x1 inaccessibles sans grille ; (e) mot de touches : bit A du terrain seulement si arg2 == 0x100 exactement (NativeExec 0x17d3d8) ; (f) tableau des paquets avec statuts (§1).

Mémoire utilisateur : rien lu ni utilisé.

FICHIERS (tous dans /tmp/audit/) : coverage.md ; sweep.py + bal2_tout.json + analysis.py (sweep v2 et son analyse) ; paquets_raw.txt, menutypes3_raw.txt ; probe_slot3.py, probe_slot4.py, probe_poker2.py, probe_poker3.py, probe_grid.py, probe_book.py, probe_book2.py ; gl_casino.py + run_gl_casino.sh (lanceur GL hors dépôt, mêmes verrous que run_wt.sh) ; captures gl_poker_b330.png, gl_pokerv_b330.png, gl_slot_b330.png, gl_slotms_b350.png, gl_slotkb_b420.png, gl_book_b230.png, gl_booksel_b330.png ; callgraph.py + cg.pkl ; scales.py ; feuilles_datapack.json. Temporaires : /tmp/audit/cache_donnees (3 Mo), /tmp/audit/rg_audit.json, /tmp/sv_audit_*.

---

## Agent aeab3de440c6b8a30 — 02/11 04:29

RAPPORT FINAL, agent « combat » (worktree /home/claude/wt-combat, branche agent-combat, base 08f5785). Arbre propre, 2 commits (trailers Co-Authored-By et Claude-Session présents, rien poussé) :
- 42de0fd Vitesse des combats (Normal / Rapide / Très rapide) et renommage « Multiplicateur de l'accélérateur »
- 79341e7 Test du rejeu d'un combat du moteur réel : nombres de dégâts comparés, nombre de pas réglable

=== A. Renommage ===
« Vitesse de l'accélérateur » devient « Multiplicateur de l'accélérateur » partout dans le code : ligne de la page Commandes, aide de la touche d'accélérateur, docstring de `_maj_camera`, commentaire du réglage, test_pause_pages (avec un assertNotIn de l'ancien libellé). La clé `vitesse_accel` n'a pas changé.
Occurrences hors code, à mettre à jour (je n'ai rien touché hors code) :
- README.md:41 (touche d'accélérateur, « vitesse réglable de 1 à 2 dans Commandes ») : à compléter avec la touche V et la vitesse des combats ;
- docs/viewer-notes-dq4-pc.md:386 (« vitesse de l'accélérateur ») ;
- docs/viewer-notes-dq4-pc.md:429 (idem, et dit que les combats gardent leur vitesse : à corriger).
Reste dans le code : settings.py:152, commentaire sur l'ancien « Multiplicateur de la course » (migration), volontairement gardé.

=== B. Vitesse des combats ===
Réglage `vitesse_combat` ∈ {1, 2, 3}, défaut Normal (1.0). Libellés Normal / Rapide / Très rapide, jamais « x2 ».
- settings.py : clé dans DEFAUT, `VITESSES_COMBAT`, `NOMS_VITESSE_COMBAT`, `cran_combat` (valeur invalide, booléen, nan ou texte → Normal ; hors bornes ramené à 1..3 ; la plus proche, à égalité la plus rapide), `combat_suivant` (cycle 1→2→3→1) et validation au chargement. Nouvelle action `vit_combat` « Touche de vitesse des combats », touche par défaut V (libre : aucune autre action ne l'utilise, pas dans RESERVEES). Si un ancien fichier a déjà donné V à une autre action, la nouvelle n'a pas de touche et l'autre garde V. `vitesse_combat` est classé HORS_INTERFACE (test).
- pause.py `_e_commandes` : juste sous les lignes de l'accélérateur (touche, multiplicateur), ligne « Vitesse des combats » (même forme que les choix x1 à x4, plaques d'origine, assombrissement au survol, pas de cadre jaune, flèche dorée au clavier), puis « Touche de vitesse des combats ». Rien de tout cela n'est accélérable par l'accélérateur. Les aides disent « Sans effet en combat » pour l'accélérateur.
- En combat, deux commandes : la touche (cycle) et un bouton à l'écran « Vitesse / Normal|Rapide|Très rapide » (le libellé jaune puis orange quand c'est plus rapide). Chaque changement enregistre le réglage ; la page Commandes le relit. Le bouton est intégré à hud_mobile : déplaçable et masquable dans l'éditeur, « Rétablir cette interface » le remet en place, position par défaut dans la bande de gauche (colonne 0,4, ligne 8, entre Carte et Commandes), vérifiée à plusieurs résolutions (1280x720 à 3440x1440) : à gauche de la colonne des fenêtres du jeu, sans recouvrir un autre bouton. Il n'envoie rien au moteur. Il se cache pendant l'écran noir d'attente de la scène et pendant les fondus au noir, comme les boutons du terrain. La touche agit aussi hors combat ; si le bouton n'est pas à l'écran, un message bref annonce la valeur.
- Effet (battle_speed.py, logique pure, nouveau) : le moteur d'origine n'est pas modifié ; en combat la visionneuse lui fait faire 1, 2 ou 3 fois plus de pas de 1/30 s par seconde réelle. La boucle d'origine de `Jeu._boucle` a été extraite en `VC.avancer` (identique pour la marche : test d'équivalence contre l'ancienne boucle). Budget de calcul 30 ms par image (BUDGET_PAS_RAPIDES inchangé) : si les pas ne tiennent pas, le jeu ralentit au lieu de geler l'affichage. `VC.facteur` : None hors combat, 1.0 quand le moteur attend le joueur, sinon 1..3.
- « En combat » = partie combat du moteur (0xd), plus l'effet d'écran de début et l'écran noir d'attente de la scène (que seul un combat lève). Hors de cela, retour à x1 sans effet sur la marche (x1 à x4) qui reste indépendante.
- Accélérateur : exclu par construction (`VC.facteur` n'a aucun paramètre pour lui ; la branche combat de `_facteur_vitesse` passe avant la logique de marche). Il ne s'applique ni ne se cumule en combat. Écrit dans le code (docstrings de battle_speed.py et de `_facteur_vitesse`, commentaire de settings.py) et dans les aides de la page Commandes.
- Attentes du joueur non accélérées : menu de commandes, choix de cible, Oui/Non (`mo.menu_actif()`), message qui montre le curseur ▼ (« Messages en combat » = Manuel). Un pas qui ouvre un menu interrompt la rafale d'images. Messages automatiques (Rapide/Moyen/Lent) : leurs compteurs sont en images moteur, donc raccourcis de 2 à 3 fois.
- Musique et bruitages : sound.py n'est pas modifié ; la lecture reste en temps réel (durée du fichier, hauteur, tempo inchangés). Seule la date de déclenchement d'un bruitage suit le moteur, et `VC.sons_a_jouer` empêche de lancer deux fois le même bruitage (paquet 35) dans la même image affichée.
- Tout ce que la visionneuse anime en combat suit l'horloge du moteur (`moteur.images + alpha`) : nombres de dégâts, FBX, effet de début, fondus (`tick_fondu`), secousses de plaques, défilement des messages (écrit par le moteur), animation des monstres. Une seule horloge réelle subsiste dans l'interface de combat : le clignotement de la flèche de cible (ui_menu.py, 0,7 s), qui est une attente de saisie. Un test vérifie par inspection de code qu'aucune des fonctions de dessin de combat n'utilise d'horloge réelle.

=== Fonctions touchées (fichiers partagés avec les autres agents) ===
window.py : `import vitesse_combat as VC` ; `on_key_press` (+1 ligne après `infos`) ; `on_mouse_release` (branche HUD, 2 lignes) ; `_maj_camera` (docstring seule) ; `_boucle` (le bloc de pas remplacé par `VC.avancer`) ; `_facteur_vitesse` (+1 ligne en tête) ; nouveaux : attribut `_se_images`, `_horloge_combat`, `_attend_joueur`, `_faire_pas_combat`, `changer_vitesse_combat` ; `tick` (1 ligne : `son.evenements(VC.sons_a_jouer(...))`).
pause.py : `_e_commandes` (accel, vit_acc, nouvelles lignes vit_cb et tch_cb, docstring, aide de « Vitesse de marche ») + 1 ligne dans le dict `noms` (`'Vitesse des combats'`).
settings.py : TOUCHES_DEF, ACTIONS, DEFAUT, commentaire de `vitesse_accel`, `VITESSES_COMBAT`, `NOMS_VITESSE_COMBAT`, `cran_combat`, `combat_suivant`, 1 ligne dans le chargement.
hud_mobile.py : constantes (COMBAT, BOUTONS, NOMS_ED à 5 éléments, DEFAUT, LIBELLE, PLAQUE_DQ), `combat_visible` (nouveau), `sous`, `visibles`, `dessiner`, `_texte_combat` (nouveau).
Nouveau : dq4_pc/vitesse_combat.py, tools/test_vitesse_combat.py. Tests mis à jour : test_pause_pages.py, test_interface_settings.py (`HORS_INTERFACE`, dicts de masque avec 'combat', `_rects_montres()` = 5).

=== Établi (mesuré ou vérifié) ===
- 39 tests dans test_battle_speed.py (1 ignoré = le rejeu moteur, opt-in), plus test_pause_pages (16), test_reglages_interface (12), test_camera_ville, test_mode_fenetre, test_panneau_interface, test_reglages_son_texte, test_son_mixage : tous OK. pyflakes : seuls les avertissements connus (sel, R, yp, mh).
- Lancement : `python3 tools/test_vitesse_combat.py` (sans écran). Rejeu moteur : `DQ_APK=<dossier APK> DQ_SAVES=<sauvegardes> [DQ_PAS_MAX=3000] python3 tools/test_vitesse_combat.py RejeuMoteur` (environ 30 s).
- Résultats identiques à x1 : même combat rejoué avec la vraie boucle `VC.avancer` à 1, 2 et 3. Sur 3000 pas moteur (100 s de combat), paquets, messages, états et nombres de dégâts sont identiques pas à pas ; les dégâts sont 11, 11, 8, 8 aux pas 158, 502, 681, 857. Dans la vraie fenêtre (DQ_TEMPS_REEL=1, même script de touches), les journaux DQ_PKTALL de x1 et x3 sont identiques sur 8405 lignes (17909 pas, dont la marche et le combat). L'issue ne dépend pas de la vitesse : le moteur est déterministe pas à pas.
- Durée du même combat (1100 pas, harnais à 60 Hz simulés) : x1 36,7 s, x2 19,6 s, x3 14,0 s (les attentes de saisie restent à vitesse normale, d'où un peu moins que x2 / x3 exacts).
- Fenêtre réelle, Xvfb 640x360 chargé, saisie scriptée toutes les 6 pas : 300 pas moteur en 10,0 s à x1 (30 pas/s), 5,7 s à x2 (52 pas/s), 4,2 s à x3 (72 pas/s).
- Coût d'un pas moteur en combat sur cette machine (2 cœurs, charge 3,4) : moyenne 2,6 ms, médiane 1,6 ms, p95 7,7 ms, max 37,6 ms. Le budget de 30 ms est donc rarement atteint ; simulation : budget coupé seulement si un pas dépasse ~30 ms (x3 retombe alors à 60 pas/s, jamais sous x2 à 60 Hz).
- Touche V en fenêtre réelle (`--touches-test`) : deux appuis donnent Normal → Rapide → Très rapide, enregistré dans le JSON. Clic sur le bouton : le réglage change et est enregistré.
- Captures (toutes dans /tmp/captures_vitesse_combat/) :
  - /tmp/captures_vitesse_combat/combat_bouton_normal.png
  - /tmp/captures_vitesse_combat/combat_bouton_rapide.png
  - /tmp/captures_vitesse_combat/combat_bouton_tres_rapide.png
  - /tmp/captures_vitesse_combat/combat_bouton_3_valeurs_agrandi.png (les trois côte à côte, agrandi)
  - /tmp/captures_vitesse_combat/combat_touche_V_cycle_agrandi.png (cycle par la touche V)
  - /tmp/captures_vitesse_combat/commandes_cle_vitesse_combats.png (page Commandes, nouvelle ligne et sa touche)
  - /tmp/captures_vitesse_combat/commandes_vitesse_combats_liste.png (curseur sur la ligne, liste ouverte)
  - /tmp/captures_vitesse_combat/editeur_interface_bouton_combat.png (bouton dans l'éditeur d'interface)

=== Supposé (cohérent avec le code et les mesures, non constaté à l'œil / à l'oreille) ===
- Ressenti à 60 Hz sur le PC de l'utilisateur : à x2 exactement un pas moteur par image ; à x3 alternance 1 / 2 pas par image (1,5 en moyenne), donc léger manque de régularité possible sur les animations à x3.
- Les animations de monstres ne suivent l'horloge accélérée que pendant les phases non en attente ; pendant les attentes de saisie, elles gardent leur animation de repos normale (voulu).
- Jingle de victoire : sa durée reste réelle alors que le moteur enchaîne plus vite (les délais de fin de combat sont comptés en images moteur). À x3, la musique suivante peut couper la fanfare avant sa fin. À vérifier à l'oreille.
- Raccourcir de 2 à 3 fois les messages automatiques réduit le temps de lecture ; pour lire à son rythme, rester en Manuel (non accéléré) ou en Normal.

=== Non vérifié ===
- Tout ce qui se joue sur Windows et sur le vrai écran de l'utilisateur (aucun Windows ici), en particulier la performance si le budget de pas est dépassé sur un PC plus lent : le jeu ralentit (x3 retombe vers x2) au lieu de geler, mais c'est testé seulement par simulation.
- Aucun test auditif (musique, bruitages, fanfare) ; seulement des faux lecteurs vérifiant que la durée d'un bruitage est la même à toutes les vitesses et qu'un doublon dans l'image est supprimé.
- Le dernier message de victoire attend une touche sans montrer ▼ : non détectable, il est donc accéléré (sans conséquence, les monstres ont disparu).

=== Choix à valider ===
Touche par défaut V ; position par défaut du bouton (col 0,4, ligne 8) ; bouton lié à la visibilité globale « Afficher cette interface » (pas d'option séparée : la page de l'éditeur est hors de mon périmètre) ; effet de début de combat et écran noir de chargement comptés comme combat (accélérés) ; touche active aussi hors combat avec message bref ; flèche de cible non accélérée.

=== Notes de doc à fusionner (pas touché docs/) ===
Section « #43 Vitesse des combats » dans docs/viewer-notes-dq4-pc.md : principe (pas moteur multipliés, budget 30 ms, facteur 1 pendant les attentes de saisie), indépendance de l'accélérateur, ce qui suit l'horloge moteur et ce qui reste réel (flèche de cible, sons), nouveau réglage et nouvelle touche V, bouton intégré à l'éditeur, tests et mesures ci-dessus. Mettre à jour les lignes 386 et 429 (nouveau libellé, les combats ont maintenant leur vitesse) et README.md:41.

=== Pièges de fusion (testés avec `git merge-tree`, lecture seule) ===
- agent-entrees : CONFLIT dans pause.py `_e_commandes`. Résolution : garder leur ligne `modif` (aide « clic molette ») et leur ligne `infos`, avec mon `accel` (aide « Multiplicateur de l'accélérateur … Sans effet en combat »), mon `vit_acc` renommé, puis `vit_cb` et `tch_cb`. Vérifier que `infos` reste dans la liste retournée.
- agent-fenetre2 : CONFLIT dans settings.py (chargement) : garder ma ligne `vitesse_combat` et supprimer la ligne `correction_bords` qu'ils retirent.