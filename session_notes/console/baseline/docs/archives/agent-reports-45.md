# Rapports finaux des agents du lot #45 (retours du 02/11 à 14 h 08)

Rapports bruts remis par les dix sous-agents (SubagentHandback) ; les notes utiles sont déjà fusionnées dans `docs/notes-*.md` (sections « Avance #45 »). Les chemins `/tmp/...` cités n'existent plus : les scripts réutilisables sont dans `tools/research/`.

---

## Agent « ui » (ac56d17dae2fc2e50) — 02/11 20:32

RAPPORT MISSION « ui » (#45, retours de 14 h 08) — worktree /home/claude/wt45-ui, branche agent45-ui (base main 84b3f22), 9 commits, arbre propre.

Légende : Établi = vérifié par test ou capture. Supposé = déduit sans vérification directe. Non vérifié = pas testé.

## 1. Point par point

1. Historique : plus d'onglet Favoris, case à cocher « Favoris seulement » — FAIT. Établi.
 - Preuve : `Historique.liste(onglet, favoris_seuls)` (history.py), `basculer_filtre` (ui_history.py:143), test_message_history.py (76 tests OK).
 - Clavier (F), manette (action « carte »), souris, étoile et molette sont couverts par les tests de `VueHistorique`.
 - H fait messages, combats, fermeture : testé.
 - `test_pause_pages.py` (28) et `test_message_history.py` ont été adaptés.
 - Capture : /tmp/ui45_hist_apres_f1.png.
 - Choix à connaître : le filtre est commun aux deux onglets et n'est pas mémorisé entre deux ouvertures.
 - Choix à connaître : dans l'historique, Tab sert d'étoile/menu (conséquence du point 6).

2. Nom de l'interlocuteur dans la boîte de dialogue en jeu — FAIT. Établi.
 - Protocole : MenuPort port 1, commande 4. `[4,0]` = pas de nom. `[4,1]` = le paquet port 1 suivant porte le nom, un entier par caractère (engine.py:260-284, 395).
 - Source IL2CPP `MenuMessage.NoticeReceive` : le nom n'existe que si `m_nowType == 0` (fenêtre du terrain). Le cadre passe de frameData 192 à 191 (onglet).
 - `m_who` : TextMesh en (-104.5, 4.0, BIAS_FONT_Y-104.0), characterSize 10, ancre UpperCenter (ui_menu.py:654-672). `SetVisible(false)` efface le nom.
 - Moteur réel : le nom « Roi Bastien » apparaît aux images 751, 772, 800, 854, 908, 962 et 998. Il est renvoyé à chaque page.
 - Capture : /tmp/ui45_nom_dialogue_apres.png. Référence mobile : /tmp/specs/img45/ecran2_mobile_dialogue_nom_Angus.jpg. La géométrie concorde à 1 px près.
 - Aucun nom inventé : le nom vient uniquement du paquet du jeu. Il n'est jamais affiché pour les fenêtres de type 1 à 3 (combat, etc.), conformément au code d'origine.
 - Tests : `tools/test_nom_dialogue.py`, 21 tests (protocole, fenêtre, vrais cadres 191/192).
 - Supposé : les autres types de fenêtres de message se comportent comme le code IL2CPP le décrit (nom seulement en type 0). Je n'ai observé en jeu que le type 0.

3. Même cartouche de nom dans l'onglet Dialogues de l'historique — FAIT. Établi.
 - L'historique dessine le vrai cadre 191/192 du jeu via `FenetreMessage`, donc le rendu est identique à celui du jeu.
 - Sans nom : rendu inchangé (cadre 192, sans onglet).
 - Captures avec nom / sans nom : /tmp/ui45_hist_apres_d1.png, d2, d3, ainsi que les versions « avant ».

4. Deux options de défilement du texte dans une section sous « Vitesses » — FAIT, avec un écart à faire confirmer. Établi.
 - ÉCART : Sylfried a dit « menu Affichage ». J'ai placé la section « Défilement du texte » dans Commandes, sous « Vitesses », parce que la section « Vitesses » se trouve dans Commandes et non dans Affichage. C'est à lui de confirmer.
 - Si « Affichage » est vraiment voulu, il suffit de déplacer l'appel à `_defilement_texte()` (pause.py:420) vers la page Affichage.
 - Commit 8a8db96.

5. « Jeu » devient « Triches », juste sous « Commandes » — FAIT. Établi.
 - pause.py:227 (entrée du menu racine), 431 et 1082 (titre). Commit ca8d109.

6. Touches par défaut du Menu = Entrée + Tab — FAIT. Établi.
 - settings.py:9 (`'menu': ['RETURN', 'TAB']`), `ANCIEN_MENU` (ligne 14), migration `touches_v: 5`.
 - Un reglages.json qui avait encore l'ancien défaut (Entrée seule) passe à Entrée + Tab. Une personnalisation est conservée.
 - Conflits de Tab vérifiés et ↺ restaure les deux touches : `tools/test_touche_menu.py`, 15 tests OK. Commit 8ac08b5.

7. Fenêtre d'historique et entrées = vraie boîte de dialogue à 3 lignes — FAIT. Établi pour la géométrie, Supposé pour le rendu sur un vrai GPU.
 - `class Boite` (ui_history.py:45) : largeur 452, hauteur 126, onglet 246×32, pas de ligne 28, marge texte, police et cartouche. Les dimensions sont lues dans la mise en page réelle (frameData 191/192) avec repli sur les valeurs mesurées.
 - Échelle = H/800 × 1,12, la même que la boîte en jeu (`fenetre.UI_ZOOM`, testé).
 - Cadre fixe identique pour 1, 2 ou 3 lignes. Au-delà de 3 lignes, une page supplémentaire est créée avec indicateur « p/n » (`paginer`, ui_history.py:88).
 - Les combats utilisent le même cadre.
 - Positions mesurées sur une capture du jeu : texte à 11-12 px du bord, première ligne de base à 31 px du haut.
 - Captures avant/après avec 1, 2 et 3 lignes : /tmp/ui45_hist_{avant,apres}_{d1,d2,d3}.png pour Dialogues, /tmp/ui45_hist_{avant,apres}_{c1,c2}.png pour Combats, /tmp/ui45_hist_apres_d2_1080.png et /tmp/ui45_hist_apres_d2_small.png pour d'autres tailles.
 - Tests de mise en page mis à jour : classe `TestBoite` de test_message_history.py. Commit 888dada.

8. Intertitres de la liste « Interface à modifier » et bouton de vitesse de combat — FAIT. Établi.
 - a) Intertitres : gris doré terne (146,140,112) avec un filet (72,69,54), à 0,76 de la taille de police (pause.py:21-25). Le doré vif n'est plus que la valeur courante. Capture avant/après : /tmp/ui45_liste_{avant,apres}_haut.png.
 - b) Le bouton de vitesse (`hud_mobile.COMBAT`) sort de « Boutons et croix de l'écran ». Il a sa propre entrée « Combat : bouton de vitesse », première du groupe Combat. Capture : /tmp/ui45_liste_{avant,apres}_combat.png.
 - Réglages propres : visible (`bouton_vitesse`), taille (0,5 à 2,0 par pas de 0,05, `bouton_vitesse_taille`), position (`bouton_vitesse_pos`). Un bouton « Replacer sous la boîte de combat » remet l'ancrage par défaut.
 - Opacité : PAS FAIT. Aucune interface de l'éditeur n'a de réglage d'opacité. Estimation : environ 20 lignes (ajouter un alpha à `Rendu.plaque` et à `hud_mobile.cadre`).
 - Position : significative. Le bouton est ancré sous la boîte du bas tant que `bouton_vitesse_pos` est vide, puis librement déplaçable.
 - Migration : `Reglages.migrer_bouton_vitesse` (settings.py:236). La visibilité et la position d'un ancien reglages.json sont conservées. La taille ne l'est que si le bouton avait été positionné, car la plaque ancrée l'ignorait avant.
 - Tests : `test_interface_settings.py` (22, dont `MigrationBoutonVitesse` et `test_bouton_de_vitesse_seul`), `test_pause_pages.py` (`Intertitres`, `ListeInterface`), `test_battle_speed.py` (faux J adapté). Commits cccc029 (intertitres) puis b13224b (bouton).

## 2. Corrections par commit (du plus récent au plus ancien)

- 888dada Historique : boîtes fixes de dialogue à 3 lignes, cadre et onglet du nom du jeu.
- b13224b Éditeur : « Combat : bouton de vitesse » devient une interface propre.
- cccc029 Éditeur : intertitres de groupe en gris doré terne.
- 10a4fa5 Dialogues : nom de l'interlocuteur dans l'onglet (commande 4 du port 1, cadre 191).
- 8ac08b5 Touches : Menu = Entrée + Tab (migration).
- a1a0bf3 Tests de l'historique : faux jeu du menu Pause prévoyant la section Défilement du texte.
- ca8d109 Pause : « Jeu » devient « Triches ».
- 8a8db96 Pause : défilement du texte dans Commandes, sous « Vitesses ».
- 0a32321 Historique : case « Favoris seulement ».

Tests finaux (xvfb) : test_historique_messages 76 OK, test_nom_dialogue 21 OK, test_pause_pages 28 OK, test_reglages_interface 22 OK, test_vitesse_combat 42 OK (1 saut : `test_meme_combat_a_toutes_les_vitesses` exige DQ_APK et DQ_SAVES, saut présent avant mon travail), test_touche_menu 15 OK, test_entrees 37 OK. pyflakes : seulement les avertissements connus.

## 3. Notes prêtes à coller dans docs/

**Protocole du nom de l'interlocuteur (port 1 du MenuPort).** Commande 4 du port 1 : `[4,0]` = pas de nom ; `[4,1]` annonce un nom, porté par le paquet port 1 suivant (un entier par caractère). Le jeu renvoie le nom à chaque page (observé : « Roi Bastien »). Source IL2CPP `MenuMessage.NoticeReceive` : le nom n'existe que si `m_nowType == 0` (fenêtre du terrain). Le cadre passe alors de frameData 192 (base 452×126, x -223..229, z -251..-125) à 191 (même base plus un onglet de 246×32 au-dessus). `m_who` est un TextMesh en (-104.5, 4.0, BIAS_FONT_Y-104.0), characterSize 10, ancre 1 (UpperCenter), alignement 1. BIAS_FONT_Y = `hdr['lang']['dy']` = 20. `SetVisible(false)` efface le nom. Côté PC : `Interface.msg['qui']` (engine.py), `FenetreMessage.regler(typ, y, feed, qui)` (ui_menu.py). L'aperçu de l'éditeur reste sans onglet volontairement.

**Boîte de dialogue standard et historique.** Échelle en jeu = H/800 × `UI_ZOOM` (1,12) ; à 720 p, s = 1,008. Mesures sur capture du jeu : texte à 11 px du bord gauche du cadre, première ligne de base à 31 px sous le bord haut, pas de ligne 28 unités, 1 px de police = 1,09 unité. L'historique (`ui_historique.Boite`) utilise ces valeurs, lues dans la mise en page réelle avec repli sur les mesures. Un cadre fixe sert pour 1, 2 ou 3 lignes. Au-delà de 3 lignes, une page supplémentaire est créée (« p/n »). Les combats utilisent le même cadre.

**Éditeur d'interface.** Les intertitres de groupe de la liste déroulante sont en gris doré terne (146,140,112) à 0,76 de la taille ; l'or est réservé à la valeur courante. « Combat : bouton de vitesse » est une interface propre (visible, taille 0,5 à 2,0, position libre ou ancrée sous la boîte du bas), séparée de « Boutons et croix de l'écran ». Clés : `bouton_vitesse`, `bouton_vitesse_taille`, `bouton_vitesse_pos`, migrées depuis `boutons_pos['combat']`.

**Réglages.** `'menu': ['RETURN', 'TAB']` par défaut (touches_v 5). Le menu Pause a une page « Triches » (ex-« Jeu ») sous « Commandes ». La section « Défilement du texte » est dans Commandes, sous « Vitesses ».

**Trouvaille UI-1 (inoffensive).** En pyglet, `K.RETURN == K.ENTER` et `symbol_string` renvoie 'ENTER', donc `reg.action_de(K.RETURN)` vaut None. Le jeu lit les touches via `codes()`, donc aucun effet constaté.

## 4. Non vérifié

- Windows et écran réel : tout a été fait sous xvfb/Linux, rien sur GPU réel ni sur un vrai moniteur.
- L'historique rempli et la liste déroulante n'ont pas été passés dans le moteur réel de bout en bout. Mes trois exécutions en file d'attente (hnew1, ifavant, ifapres) ont été annulées pour libérer le verrou xvfb, trop encombré.
- Les captures de l'historique et de la liste viennent d'un banc hors moteur (`/tmp/ui45_off/render_hist.py` et `render_list.py`) qui utilise le vrai `Rendu`, le vrai `Pause` et la vraie `VueHistorique`.
- Seule la capture du nom en dialogue vient du moteur réel, par l'APK patchée.
- Le nom n'a été observé en jeu que pour le type de fenêtre 0 (Supposé pour les autres types).
- Une capture du jeu avec l'historique ouvert dans les trois dimensions de fenêtre n'a été faite que pour 720 p, 1080 p et une petite fenêtre, via le banc hors moteur.

## 5. Fichiers touchés (15, +1012/-197)

- Mes fichiers : dq4_pc/historique.py, ui_history.py, pause.py, settings.py ; tools/test_historique_messages.py, test_pause_pages.py, test_interface_settings.py, test_menu_key.py ; tools/test_nom_dialogue.py (nouveau) ; README.md.
- Hors périmètre, changements minimaux :
 - dq4_pc/moteur.py (12 lignes) : lecture du nom sur le port 1 et remise à zéro dans le hook SetVisible.
 - dq4_pc/ui_menu.py (44 lignes) : classe `FenetreMessage` (cadre 191, nœud « qui », `etendue_x`, `rects`).
 - dq4_pc/fenetre.py (8 lignes) : `_maj_message` passe `m.get('qui', '')`, plus 3 commentaires/docstrings.
 - dq4_pc/hud_mobile.py (46 lignes) : bouton de vitesse sorti de `NOMS_ED`, ajout de `NOMS_ED_VITESSE`, `noms_ed()`, `echelle(nom)`, position et visibilité propres.
 - tools/test_vitesse_combat.py (12 lignes) : faux J et test du glisser.
 - Je n'ai pas touché `battle_speed.py`, `inputs.py`, les fichiers du patch FR (APK, *.mpt) ni les sauvegardes.

## 6. Pièges de fusion

- ui_menu.py : l'agent « alignement du texte » travaille sur l'alignement du texte dans la zone de `FenetreMessage` (≈ lignes 654-720). Mes ajouts sont des blocs contigus (constantes `CADRE_AVEC_NOM`, `QUI_POS`, `QUI_TAILLE`, `regler(..., qui)`, `etendue_x`, `rects`). Conflit probable : le nœud « texte » et `etendue()`. À relire après fusion : `etendue()` utilise `self._base['vtx']` quand `avec_nom`.
- window.py : une seule ligne fonctionnelle (`_maj_message`, vers la ligne 1542) plus 3 commentaires. Conflit possible avec l'agent caméra/écran si leurs changements touchent ces lignes.
- hud_mobile.py et battle_speed.py : l'agent combat peut toucher le bouton de vitesse. `hud_mobile.BOUTONS` contient toujours COMBAT, mais `NOMS_ED` ne l'a plus. `hud_mobile.ancre()` retourne None si `bouton_vitesse_pos` est renseigné.
- settings.py : `CLES_INTERFACE` est vérifié par `test_interface_settings.py` (liste AUTRES). Toute nouvelle clé doit y être classée.
- pause.py : `GROUPES_INTERFACE` et `INTERFACES_PROPRES` ; si un autre agent ajoute une interface, l'ajouter aux deux et à `NOMS_FENETRES`.
- Le worktree est propre : rien d'oublié dans /home/claude/wt45-ui. Aucun push, aucun changement de branche, aucune PR.

## 7. Captures utiles (chemins absolus)

- /tmp/ui45_nom_dialogue_apres.png — dialogue en jeu avec onglet « Roi Bastien »
- /tmp/ui45_dialogue_sans_nom.png — dialogue sans nom (cadre 192 inchangé)
- /tmp/specs/img45/ecran2_mobile_dialogue_nom_Angus.jpg — référence mobile
- /tmp/ui45_hist_avant_d1.png, d2, d3 et /tmp/ui45_hist_apres_d1.png, d2, d3 — Dialogues avec 1, 2, 3 lignes
- /tmp/ui45_hist_avant_c1.png, c2 et /tmp/ui45_hist_apres_c1.png, c2 — Combats
- /tmp/ui45_hist_avant_f1.png et /tmp/ui45_hist_apres_f1.png — filtre Favoris seulement
- /tmp/ui45_hist_apres_d2_1080.png, /tmp/ui45_hist_apres_d2_small.png — autres tailles de fenêtre
- /tmp/ui45_liste_avant_haut.png, /tmp/ui45_liste_apres_haut.png — intertitres (haut de la liste)
- /tmp/ui45_liste_avant_combat.png, /tmp/ui45_liste_apres_combat.png — groupe Combat avec « Combat : bouton de vitesse »

## 8. Décisions à confirmer par Sylfried

- Section « Défilement du texte » : Commandes (fait) ou Affichage (demandé).
- Filtre Favoris commun aux deux onglets, non mémorisé.
- Pas de réglage d'opacité pour le bouton de vitesse (aucune interface de l'éditeur n'en a ; environ 20 lignes si voulu).
- Onglet du nom masqué quand le nom est vide et jamais affiché pour les fenêtres de combat (types 1 à 3).

---

## Agent « effet » (a6d50dea86708b3b9) — 02/11 20:42

RAPPORT MISSION « effet » (préfixe EF) — worktree /home/claude/wt45-effet, branche agent45-effet (base 84b3f22), 2 commits, arbre propre (git status vide), pas de push.

== RÉSUMÉ ==
Le faisceau vert n'est pas l'église : c'est le rayon de la case de soin (objet de carte `kifk01a`). Cause du « tourne de ~5° puis revient » : le mouvement de rotation de l'objet (FPMV, 800/60 s) et sa séquence de maillages (FSQD, 84/60 s) partageaient UNE horloge dans la visionneuse, celle de la séquence, qui bouclait à 84. La rotation ne dépassait donc jamais 84/800 de tour (~37°, ~5° de balancement visible) avant de revenir au départ. Corrigé : une horloge par animation, comme le moteur (FldObject.fld_motion_update). Soin PV/PM : fait par le moteur, la visionneuse ne s'en mêle pas.

== PAR POINT DE LA MISSION ==
1. Où est le rayon (carte) — FAIT, Établi pour les cartes. Objet `kifk01a` dans cmf1c (centre -0,01 ; -0,03), dmb2 (-0,86 ; 12,47) et tab1a (0,0 ; 3,5). L'anneau au sol (palette animée `tz_kifkyk1`, 24 clés cyan→vert) existe aussi dans za1f1. La capture de Sylfried (niche bleue) ressemble à cmf1c (panneaux bleus au mur) : Supposé, non prouvé (dmb2/tab1a non rendus, file d'attente xvfb saturée).
2. Comment le jeu l'active — FAIT, Établi (désassemblage + test moteur). Sol de surface de type 4 (FldCollision::getSurfaceByType / TownStageManager::getHitSurfaceIdByType(4)) → TownActionWalk::checkCureFloor (0x1d6728) → TownPlayerManager::setCureFloor (0x1df284) → PartyStatus::recovery() + TownPlayerEtc::setupCureFloorEffect (SE 0x469 = 1129, setLock) puis updateCureFloorEffect (fadeOutWhite 20, fadeIn 20, SE 0x1f5 = 501, déverrouillage). Le visuel (`kifk01a` + anneau) est un décor : il ne déclenche rien.
3. PV/PM soignés à l'entrée — FAIT, Établi. Moteur seul (Moteur.demarrer_ville cmf1c, sauvegarde 1, héros téléporté sur l'anneau après avoir fermé le message d'ouverture) : PV 1→47, 1→35, PM 0→30 dès l'entrée, fondu blanc 20/20 images, SE 1129 puis 501. La visionneuse n'intervient pas (elle ne rejoue que les paquets du moteur) : rien à corriger de ce côté. Piège de test : le message « Quelle joie de vous revoir, Ragnar ! » verrouille le joueur tant qu'on ne l'a pas fermé.
4. Cause racine de l'oscillation — FAIT, Établi. Hypothèses écartées avec preuve : (a) slerp de quaternions : non, `pmv_func` (RVA 0xCD94B8) = localRotation = rotateXZY(Euler interpolé par composante) et la visionneuse faisait déjà de l'Euler composante par composante ; (b) modulo : non, la boucle du compteur est correcte ; (c) pente de WrapMode.Loop : non, FPMV n'est pas une AnimationCurve Unity ; (d) ordre des rotations : non (rotate_xzy déjà exact, test des coffres #43 intact) ; (e) une clé sur deux : non, clés lues 0/180/360 ; (f) images moteur vs temps réel : non (PAS = 2 par image de jeu 30 Hz, unité = 1/60 s). Vrai coupable : horloge partagée. Mesure (carte réelle cmf1c, vue de dessus d'un sommet du faisceau sur 800 images) : AVANT angle min/max 0 à 36,9° (va-et-vient, période 42 images) ; APRÈS 0 à 720° (2 tours en 800 images, un tour = 400 images = 13,3 s).
5. Correctif et généralisation — FAIT (voir commits). Statistique : 96 objets de cartes ont séquence + mouvement, dont 57 avec des durées différentes (torches, oiseaux, cascades, sourcils, rayons) : tous ont maintenant deux horloges indépendantes. Animations communes (SetCommonAnimation) : idem, une horloge par clip. fbx.py : boucle du lecteur (modulo la durée) et courbes d'Hermite déjà corrects ; battle_effect.py n'a aucune rotation animée (grep). Les 17 modèles ImdChara chargeables ont 114 courbes de rotation, aucune inversion de signe ni saut > 120° entre clés ; les autres modèles (shader Custom/Effect0, maillages non skinnés, ~29) ne sont pas chargés par la visionneuse : hors périmètre.
6. Tests unitaires — FAIT. Interpolation : 0→360°, 0/90/180/270/360, angles négatifs, boucle (2e tour = 1er), pas de plus court chemin (0→270 passe par 135), composante par composante, tenue sur la dernière clé, délai de départ/entre tours, deux horloges indépendantes, migration d'ancien état, vraies cartes cmf1c/dmb2/tab1a + toutes les animations en continu de toutes les cartes. Résultats : tools/test_objets_carte.py 35 tests OK (15 existants inchangés, dont coffres/portes/tiroirs) ; tools/test_fbx_anim.py 9 OK ; test_textures_carte, test_vitesse_combat, test_decors_racine, test_teinte_carte, test_cartes_pnj OK. Vérifié que les nouveaux tests ÉCHOUENT sur le code d'avant (test_un_tour_complet_malgre_la_sequence_courte en assertion ; les tests fbx de mélange aussi). pyflakes propre sur les 4 fichiers touchés.
7. Captures avant/après — PARTIEL. Fait pour cmf1c uniquement (dmb2 et tab1a non rendus : la file xvfb partagée avait plus de 15 minutes d'attente par rendu, j'ai annulé ces deux-là pour ne pas bloquer les autres agents). Voir fichiers. Limite honnête : le faisceau a 6 filaments (symétrie 60°), donc des captures espacées de 100 images (= quart de tour, soit 30° modulo 60°) se ressemblent ; la preuve forte est le graphe de l'angle, pas les captures statiques. Les captures diffèrent aussi par les torches/flammes (qui avaient le même défaut d'horloge).
8. Non-régression — Établi pour ce qui est testé : dragon du titre (c1018, ev01) : poses simples identiques bit à bit entre l'ancien et le nouveau fbx.py ; fondus réels du dragon (Take 002 en boucle vers 001/003) : 0 pose différente sur 4000 ; coffres/portes/tiroirs : tests existants passent.

== COMMITS ==
- f6dd216 EF1 : le rayon de soin tourne enfin d'un tour complet (une horloge par animation d'objet) — dq4_pc/objets_carte.py (+95/-33 environ : `_horloge`, `_avancer`, `_migrer_auto` ; `_semer`, `tick`, `_poser`, `_src_seq`, `anim_commune`, `restaurer` ; états `tmot`/`tseq`) et tools/test_objets_carte.py (+221).
- 8d8b9ef EF2 : fbx.py, fondu entre deux clips : mélange de rotations du même côté de la sphère — dq4_pc/fbx.py (5 lignes dans `locales`) + tools/test_fbx_anim.py (nouveau, 117 lignes). DÉFENSIF : q et -q sont la même rotation, la moyenne pondérée d'un CrossFade les annulait ou faisait faire un demi-tour ; on aligne le signe sur la première pose. Aucun défaut visible connu avant ; 224 poses sur 1890 (fondus entre instants arbitraires du dragon, qui n'arrivent pas dans le jeu) changeaient, 0 des fondus réels. Séparé de EF1 pour pouvoir être écarté sans toucher au correctif principal.
Fichiers hors périmètre : aucun (window.py, sprites, combat, caméra, etc. non touchés). Compatibilité : les instantanés enregistrés avant la correction (une seule horloge, entrées `auto` à plat, rechargés par window.py ligne ~969 via `restaurer(..., objets_auto)`) sont migrés par `_migrer_auto` (testé en synthétique seulement).

== FICHIERS / CAPTURES ==
- Avant/après cmf1c (2 lignes x 4 images 150/250/350/450, recadré) : /tmp/ef/avant_apres_cmf1c.png ; sources : /tmp/m_efav_cmf1c_b{150,250,350,450}.png (avant) et /tmp/m_efap_cmf1c_b{150,250,350,450}.png (après) ; zoom ancien : /tmp/ef/avant_cmf1c_zoom.png
- Graphe vue de dessus + courbe de l'angle sur 2 tours (avant : 0-37° ; après : 0-720°) : /tmp/ef/avant_apres_vue_dessus.png (script /tmp/ef/plot_avant_apres.py)
- Scripts d'analyse : /tmp/ef/ (scan_double.py = 96/57 objets, sim_kifk.py, scan_quat.py, scan_fondu.py, cmp_fbx.py, test_soin.py = soin sur le moteur)

== NOTES PRÊTES À COLLER DANS docs/ ==
Rayon de soin (case de soin) et animations d'objets de carte
- Le rayon vert « qui soigne PV/PM » est l'objet de carte `kifk01a` (cartes cmf1c, dmb2, tab1a) avec un anneau au sol à palette animée `tz_kifkyk1` (aussi dans za1f1). Il est purement décoratif. L'effet de jeu vient de la surface de sol de type 4 : TownActionWalk::checkCureFloor (0x1d6728) → TownPlayerManager::setCureFloor (0x1df284) → PartyStatus::recovery() (PV et PM au maximum) + setupCureFloorEffect (SE 1129, verrouillage) / updateCureFloorEffect (fondu blanc 20, fondu d'entrée 20, SE 501, déverrouillage). Vérifié sur le moteur (cmf1c) : PV 1→47 / 1→35, PM 0→30 à l'entrée de l'anneau. La visionneuse ne doit rien faire de plus que rejouer les paquets.
- Sémantique d'origine des animations d'objets (FldObject.fld_motion_update, RVA 0xCD69DC) : chaque FLD_MOTION (mouvement FPMV) et chaque séquence de maillages (FSQD) a SA PROPRE horloge : cur_frame (+0x2c), end_frame (+0x30), repeat_num (+0x24), start_delay (+0x26), repeat_delay (+0x28). Pas par image de jeu = 2 (unité 1/60 s). Pendant un délai on applique la première clé et on décrémente le délai ; sinon on interpole puis cur += pas ; quand cur > end : repeat_num décrémenté s'il est ≥ 1 ; s'il vaut 0 on tient la dernière clé, sinon cur = dépassement et start_delay = repeat_delay. Rotation : pmv_func (0xCD94B8) = localRotation = rotateXZY(Euler interpolé linéairement composante par composante), pas de quaternion ni de plus court chemin (donc 0→360° tourne vraiment). c_pmv_func (0xCD96D8) pour flag&4. Seule différence connue : pendant le délai l'original garde cur_frame, la visionneuse le remet à 0 (conservé tel quel).
- Bug corrigé (EF1) : une seule horloge partagée mouvement/séquence. Pour `kifk01a` : séquence 84, rotation 0→180→360 en 800 → balancement de ~37°. 96 objets de cartes ont séquence + mouvement, 57 avec des durées différentes.
- Hypothèses écartées pour « tourne de ~5° » : slerp de quaternions, modulo, pente WrapMode.Loop, ordre des rotations, une clé sur deux, images moteur/temps réel.
- fbx.py : modèles Unity, rotations en quaternions (`m_EulerCurves` vide dans les 46 clips), Hermite par composante puis normalisation (comme Unity) ; boucle = modulo la durée. Fondu CrossFade : mélange du même côté de la sphère (EF2). Clips compressés non gérés. Seuls les modèles Custom/ImdChara sont dessinés.

== NON VÉRIFIÉ ==
- Windows et vrai GPU (rendus Xvfb/Mesa seulement).
- Rendus de dmb2 et tab1a (l'animation y est la même donnée, vérifiée en test sur les 3 vraies cartes, mais pas de capture).
- Carte exacte de la capture de Sylfried (cmf1c Supposé).
- Origine des étoiles/étincelles en croix autour du rayon (particules, hors mission).
- Animations de matériaux (FSRA) et animations d'événements (FEAN, paquet 6) : non rejouées par la visionneuse, non touchées.
- Migration d'ancien instantané sur une vraie sauvegarde de la visionneuse (seulement en test synthétique).
- Aucune information de la mémoire utilisateur n'a servi ; rien de nouveau à y noter.

---

## Agent « decor » (a1877ded1e12dc252) — 02/11 20:42

RAPPORT FINAL — mission « décor » (DC), worktree /home/claude/wt45-decor, branche agent45-decor, arbre propre (git status vide).

VERDICT : les pierres ne « flottent » pas à cause d'un défaut du viewer. Leur hauteur est fidèle au jeu. Je n'ai rien changé au rendu. Un seul commit : un test de mesure.

POINT 1 — carte et cadrage : FAIT.
- Établi : la carte est `maout`, bout sud du chemin de dalles nord-sud. Le « bleu » d'ecran9 est la couleur de fond `e.fond` (115,148,255), visible au-delà du bord déchiqueté de l'herbe. Ce vide n'est montré que parce que `camera_centree` (par défaut) retire le bornage de caméra du jeu. Cadrages reproduits : /tmp/m_dc_av_b117.png, /tmp/m_dc_av_b131.png, /tmp/m_dc_av_b173.png (bord sud) et /tmp/m_dc_var_b35.png.
- Non vérifié : le rognage et l'échelle exacts d'ecran9, et le bornage de caméra du jeu d'origine près du bord sud.

POINT 2 — nature des pierres : FAIT.
- Établi (données extraites) : surface plate, sans volume. C'est l'objet `020_mast1` (pierres maisiyk1..4, terre sn02/najimi02, bassin), tous sommets à y=-0,125. L'herbe dessous (`018_maoutsb1`) est à y=-0,25. Écart : 0,125.
- Établi (shaders du datapack) : fld_atest, file AlphaTest, ZWrite actif, sans mélange, découpe alpha, aucune ombre portée. Éclairage cuit dans les sommets, cohérent avec l'herbe. ZTest LEqual, Cull Back, Offset 0/0 : aucun décalage de profondeur dans le jeu.
- Établi (règle des concepteurs) : les couches de décalques sont espacées de 1/8 d'unité (0,125). Sur 63 cartes, 21 543 décalques plats découpés posés sur un sol opaque : 10 017 (46 %) à 0,125, puis 1 889 à 0,25, 1 474 à 0,375. 3 710 autres n'ont pas de sol opaque dessous. Dans maout : plus de 50 % des décalques sont à un multiple de 0,125, moins de 3 % sont coplanaires, 0 est tourné vers le bas. Le `ModelOffset` (0,01 à 0,02) ne sert que pour les fleurs hana1/hana2 dans 5 cartes et dbdoku3 dans dbout.
- Notre surélévation (`decors_plats.decaler`, 3 mm par niveau, mesurée de 6 à 12 mm) vaut moins de 0,6 px à 720p. Elle est négligeable.

POINT 3 — comparaison avec Unity et liseré sombre : PARTIEL.
- Établi (mesure GL, maout, 720p) : abaisser les pierres au niveau de l'herbe ne les déplace que de 4 px à l'écran (prédit 3,9). L'écart de 1/8 d'unité n'explique donc pas l'impression de flottement. Comparaison : /tmp/dc/cmp_av_po_pierres.png.
- Établi : le liseré sombre vient surtout du fait que les texels transparents sont (0,0,0,0) dans les textures. Le filtrage bilinéaire et les mipmaps les mélangent au bord de chaque pierre. Un étalement de couleur dans ces texels le fait disparaître : /tmp/dc/cmp_av_bo_pierres.png (gauche : actuel ; droite : sans liseré). Sur la scène sud, 2,3 % des pixels changent hors dialogue, uniquement sur les contours. Dans la zone des pierres, 750 pixels deviennent plus clairs et 0 plus sombre. Carte des écarts : /tmp/dc/diff_bo_sud1.png.
- Supposé : le jeu d'origine a le même liseré, voire plus large. Raison : shader AlphaTest sans prémultiplication, texels noirs, et notre shader « sharp-bilinear » rétrécit la zone de mélange. Le contour vert foncé est aussi en partie cuit dans la texture.
- Non vérifié : aucune capture mobile d'un chemin de pierres dans le projet pour trancher. Éclairage, ombre, MSAA et a2c écartés comme causes de la hauteur apparente.

POINT 4 — correction : PAS FAIT, volontairement.
- La hauteur est fidèle, donc rien à corriger globalement. Je n'ai rien changé au rendu des décors, ni à `fld.py`, `map_objects.py`, `flat_sceneries.py` et `window.py`. Aucun conflit à prévoir avec l'agent combat sur les bords alpha.
- Option A (non commitée) : étaler la couleur des texels opaques dans les texels transparents voisins (alpha inchangé). Fichiers prêts : /tmp/dc/proposition_bords_alpha/bords_alpha.py et test_bords_alpha.py (8 tests OK, pyflakes propre). Branchement prévu : 2 appels `self._tex(...)` de `Jeu._charger_carte` (window.py ~1273 et ~1281), `_calcul_hd_decor` inchangé. Si Sylfried la veut, il faut en faire un réglage : migration, ↺, clé `settings.py`. Le test GL a été fait avec un crochet sur `_tex` (toutes textures), pas avec le branchement décor seul.
- Option B (déconseillée) : poser les décalques sur le sol. Elle s'écarte du jeu d'origine et ne déplace que de 4 px. Le prototype `poser()` de /tmp/dc/wrap_multi.py a abaissé à tort les rebords plats de la clôture : il faudrait un plafond de hauteur et ne cibler que les décalques.

COMMIT
- b788856 « Test : hauteur des decalques plats au-dessus du sol (pierres du chemin de maout) » : `tools/test_decalques_sol.py` seul, avec les deux trailers. Il garde la mesure 0,125 / -0,125 / -0,25 des données extraites ; il ne teste pas le rendu. Commande : `DQ_CACHE_CARTES=<dossier carte10_*.pkl> python3 -W ignore tools/test_decalques_sol.py`. 2 tests OK, pyflakes propre, ignoré sans cache.

NOTES À COLLER DANS docs/ (technique du portage)
« Décalques plats au sol (pierres, terre, fleurs, herbes). Les shaders de décor du jeu (fld_normal, fld_atest, fld_trans) n'ont aucun Offset de profondeur. Les concepteurs séparent les couches par la géométrie : chaque couche est posée 1/8 d'unité (0,125) au-dessus de la précédente. Exemple maout : herbe y=-0,25, terre et pierres y=-0,125. Mesure sur 63 cartes : 46 % des décalques découpés sont à 0,125 au-dessus du sol opaque, puis 0,25 et 0,375. Le ModelOffset (0,01 à 0,02) ne concerne que les fleurs hana1/hana2 (5 cartes) et dbdoku3 (dbout). À 720p, 1/8 d'unité vaut environ 4 px : les pierres ne flottent pas par défaut. La surélévation du viewer (3 mm par niveau, 12 mm au plus) est négligeable. Le liseré sombre des pierres vient des texels transparents noirs mélangés par le filtrage ; l'original l'a probablement aussi (non vérifié). Le fond bleu d'ecran9 est la couleur de fond de maout visible au bord sud grâce à camera_centree. Test : tools/test_decalques_sol.py. »

NON VÉRIFIÉ : rendu sous Windows et vrai GPU ; capture mobile d'un chemin de pierres ; le liseré chez l'original ; l'effet de l'option A sur les décors de combat (grossissement plus fort, périmètre de l'agent combat). Les réglages mobiles par défaut de Sylfried sont inconnus.

PIÈGES DE FUSION : aucun fichier du jeu touché, un seul fichier ajouté (tools/test_decalques_sol.py). Si l'option A est retenue plus tard : nouveau module bords_alpha.py, 2 lignes dans `_charger_carte`, à coordonner avec l'agent combat.

CAPTURES : /tmp/m_dc_av_b33.png (vue d'ensemble maout), /tmp/m_dc_av_b47.png (fleurs et bassin), /tmp/m_dc_av_b117.png /tmp/m_dc_av_b131.png /tmp/m_dc_av_b173.png (bord sud), /tmp/m_dc_av_b201.png (chemin horizontal), /tmp/m_dc_var_b35.png (actuel), /tmp/m_dc_var_b131.png (pierres abaissées), /tmp/m_dc_var_b227.png (sans liseré). Vue de dessus : /tmp/dc/top_maout.png. Mesures par carte : /tmp/dc/hauteurs_all.json.

À RETENIR (mémoire) : le harnais DQ_CARTE_TEST="nom;x,y,z;cx,cy,cz" avec DQ_CARTE_SANS_SPR=1 fonctionne bien ; une caméra trop proche (k < 0,28) est coupée par le plan proche. Un harnais moteur sans GL (`Moteur`, `step(tenu, decl)`, HAUT=1 BAS=2 GAUCHE=4 DROITE=8) évite le verrou xvfb.

---

## Agent « son » (aa98dee8079978f2c) — 02/11 20:47

RAPPORT MISSION « son » (PR #45, worktree /home/claude/wt45-son, branche agent45-son, base 84b3f22). git status propre. 4 commits, rien de poussé. Perimetre : sound.py + 2 lignes de window.py + tools/test_son_mixage.py.

== REPONSE A SYLFRIED (« pas de jingle quand on meurt ? ») ==
Le jeu d'origine n'a PAS de jingle ni de bruitage propre a la mort. Etabli (moteur reel sous Unicorn, paquets 35/36/37) :
- Allie a 0 PV : seulement SE 403 (le bruit de degats, commun a tous les coups) + le message. Rien d'autre.
- Groupe battu (BattleExecVictory38) : arret de la musique (37, 16392 = 0x4008) puis BGM 23 (113,5 s, boucle, musique de la scene de la « voix »). Pas de jingle court. Aucun chemin « game over -> titre » dans le moteur.
- La couche Unity d'origine ne joue elle-meme que le SE 300 (bouton) et la reprise de musique (Sound.SystemUpdate) : cas (b) exclu, aucun jingle cache cote C#.
=> Pas de « jingle de mort manquant » a ajouter (ce serait inventer, contraire a la regle « comme le mobile »). Trois causes cote visionneuse expliquent un son de defaite/fanfare absent ou tronque, toutes corrigees (SN1 a SN3).

== INVENTAIRE (preuve = trace des paquets moteur, harnais h45/wipe/scen_combat/fuite/services/menusons dans son45_work) ==
- Allie tombe : SE 403 seul. Etabli.
- Defaite totale : 16392 puis BGM 23. Etabli.
- Victoire : SE 409 (2,91 s, snd_vol 0,6) + arret musique, en meme temps (BattleEndTask). Etabli.
- Montee de niveau : (37,16384) puis BGM 47 (3,1 s, sans boucle). Etabli (rejeu niveau).
- Fuite : SE 408 (BattleExecEscape::setup) ; echec de fuite : SE 408 + message, pas de jingle. Etabli (flee_battle.py).
- Eglise sauvegarde BGM 39, resurrection BGM 40, auberge BGM 41 (le moteur la coupe a 3 s). Etabli (services.py, moteur reel).
- Jingles de menu : table MenuSoundManager::setPlaySound(MENU_SOUND) 1..15 releve (menu_sounds.py). Etabli par desassemblage.
- Coffre / cle / medaille : BGM 48 via playRestart (0x1000|48), SupposE d'apres le code statique, NON joue dans le moteur.
- Usage reel des BGM 36, 37, 38, 42, 49 : Non verifie.
Resume « present/absent » : tout ce que le moteur demande est maintenant joue dans la visionneuse ; « absent » cote moteur = jingle de mort, jingle de fuite, jingle d'echec de fuite, game over -> titre (n'existent pas dans le jeu).

== CORRECTIONS (un commit par point) ==
SN1 08cc0d2 – musiques du moteur decodees d'avance : BGM_PRECHARGES = jingles 6, 8, 10, 13, 35-50 + 30 + 23 (22 musiques, 59 Mo), fil a part (pool_fond), une a la fois, seulement quand une musique joue et qu'aucun decodage demande n'attend, epinglees (jamais chassees par la purge LRU). Cause : BGM 23 n'etait decodee qu'a l'ordre du moteur (0,6 a 1,2 s) et arreter_bgm() annule un decodage en cours, donc un arret moteur arrive avant la fin = silence. Preuve : rejeu du moteur reel en horloge reelle, game over a x3 : ordre BGM 23 -> son 0,70 s plus tard avant ; 0 s apres (rt_avant_x3.txt / rt_apres_A_x3.txt). Etabli : le retard. Suppose : le silence complet sur un PC lent (non observe ici, seulement test unitaire).
SN2 29413f1 – jingle protege en jeu accelere. Le moteur enchaine ses ordres 2-3 fois plus vite a x2/x3 et coupait la fanfare : BGM 47 jouee 3,1 s a x1, 2,2 s a x2, 1,2 s a x3 avant ; 3,1 s a x1, x2 et x3 apres (rt_niveau_avant_x*.txt / rt_niveau_apres_x*.txt). Mecanisme : evenements(evts, image_moteur=None) ; tant qu'un jingle (categorie jingles, sans boucle) joue, un ordre de musique qui serait arrive apres lui a vitesse normale est retenu jusqu'a min(heure normale = image/30 s, fin du jingle), file FIFO, videe au chargement d'etat / son coupe, pause ne libere rien, bruitages jamais retenus. A x1, sans image moteur, jingles coupes ou musique en boucle : aucun changement. window.py : image_moteur=mo.images (ligne 2779). Aucune logique de vitesse touchee. Test reel sans fenetre (vrai pyglet, pilote silent, APK reel) : ordre d'arret libere apres 3,17 s pour un jingle de 3,1 s.
SN3 d8d11ac – SE 409 (fanfare de victoire) range dans « Jingles et fanfares » (SE_JINGLES, categorie_se) ; l'option « volume bruitages » du jeu reste appliquee (Mixage.gain(cat, propre, option=None), les SE passent option='effets'). Aucun reglage nouveau, pas de migration de reglages.json ; sons identiques par defaut. Choix de classement (Suppose : une fanfare doit suivre le curseur « Jingles et fanfares »), annulable en vidant SE_JINGLES.
SN4 c94433d – commentaires seulement (durees mesurees).
Tests : tools/test_son_mixage.py 14 -> 30 (7 Precharge, 8 ProtectionJingle dont 5 echouent si la protection est neutralisee, 1 fanfare 409) OK ; test_reglages_son_texte 7 OK ; test_vitesse_combat 42 OK (1 skipped, comme avant). pyflakes : seulement soundfile/SourceBoucle (connus) ; window.py : dims et sel existaient deja a 84b3f22.

== NOTES PRETES A FUSIONNER DANS LES DOCS ==
1. Sons du moteur : seuls paquets son = 35 (PlaySE SE%04d), 36 (StopSE), 37 (PlayBGM ; >=0x4000 stop, 0x1000|n = playRestart avec reprise de la musique d'avant). Mort d'un allie = SE 403 ; groupe battu = 0x4008 puis BGM 23 ; victoire = SE 409 ; niveau = BGM 47 ; fuite et echec = SE 408 ; eglise 39, resurrection 40, auberge 41 ; coffre 48 (non joue). Unity ne joue que SE 300 et la reprise (Sound.SystemUpdate).
2. Decodage : BGM 23 0,59 s seule (0,7-1,2 s en jeu), BGM 30 0,43 s, jingles 0,01-0,14 s ; prechargement = SN1 (59 Mo).
3. Vitesse : un pas moteur = 1/30 s a vitesse normale ; le son doit se caler sur l'image du moteur, pas sur l'horloge murale (SN2).
4. snd_vol.dat : 1171 flottants indices par numero de son (BGM = volumes d'en-tete AKB, SE tous a 1,0 sauf SE 409 = 0,6) ; le produit en-tete x snd_vol n'est pas verifie.
5. Harnais : PartyStatus::add rend membres() peu fiable (groupe reel en slot 1 = [3, 12], tuer Doc = indice 12) ; fuite = bouton 3 ; eglise/banque par changeShopMenuPhase ; une liste d'eglise est sous un message (priorite menu avant le « A » du message, Oui/Non port 2).

== NON VERIFIE ==
Fenetre reelle avec son (la file xvfb avait ~12 attentes : test annule, process tue, rien ne traine) ; remplace par un test de la vraie classe Son avec vrai pyglet silencieux sans fenetre. Vitesse de decodage sous Windows / PC lent ; ecoute reelle ; BGM 48 dans le moteur ; semantique de snd_vol ; 30 images/s = vitesse normale (Suppose) ; si Sylfried joue a x2/x3 (SN2 ne change rien a x1).

== PIEGES DE FUSION ==
window.py : 2 lignes (225 : precharger_musiques() apres precharger(SE_COURANTS) ; 2779 : image_moteur=mo.images) : conflit possible si l'agent « combat » touche ces lignes. Etat.appliquer, battle_speed.py, pause.py, settings.py non touches. Signature Son.evenements(evts, image_moteur=None) compatible avec test_vitesse_combat.

== CHEMINS /tmp UTILES ==
Prive : /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/son45_work/ : replay.py + run_replay.py (RT=1 horloge reelle, SON_DIR=.../avant pour l'ancien sound.py, MARCHE, SUITE ; usage run_replay.py niveau|wipe FACTEUR), real_pyglet.py, rt_*.txt (preuves avant/apres), b1_out.txt, scan_imm.txt, avant/son.py. Cache /tmp/son45_cache.

== A RETENIR (memoire) ==
Le scratchpad est partage avec d'autres agents : utiliser un sous-dossier prive. Ne jamais lancer pkill -f avec un motif present dans sa propre ligne de commande (tue son shell). Deux rejeux avec le meme nom ecrasent /tmp/sv_NOM (FileExistsError). import pyglet sans ecran exige pyglet.options['shadow_window']=False.

---

## Agent « camera » (a62435950b4b9be62) — 02/11 20:51

RAPPORT agent « camera » (CA), lot 45, worktree /home/claude/wt45-camera, branche agent45-camera (base main 84b3f22). Arbre propre (`git status` vide), 4 commits, aucun push. Tous les tools/test_*.py passent en sans-écran (test_texte_defilement exige des arguments, sans rapport). test_mode_fenetre complet (39) vu OK sous xvfb avant le découpage en commits ; l'arbre final est identique octet pour octet.

1) POINT PAR POINT

1. Écran du plein écran : FAIT (code et tests). Nouveau réglage sur la page Affichage, sous « Plein écran » : liste des moniteurs vus par pyglet (« Écran 1 (1920x1080), principal »).
 - Automatique (↺) = l'écran où se trouve la fenêtre, à défaut le principal. Clé `ecran_plein` dans settings.py : None, ou indice + position + dimensions + nom.
 - Utilisé à chaque entrée en plein écran (F11, Alt+Entrée, interrupteur, lancement en plein écran). Déjà en plein écran, changer le choix déplace la fenêtre tout de suite.
 - Au lancement suivant, l'écran est retrouvé par nom, puis position + dimensions, puis indice + dimensions, puis dimensions seules. S'il n'existe plus : repli sur l'écran de la fenêtre, ligne « Écran N (absent) » + note rouge, choix conservé, jamais d'exception.
 - Retour en fenêtre : la fenêtre revient là où elle était (position mémorisée par pyglet). Si cette position n'existe plus (écran débranché, ou lancement en plein écran), elle est recentrée sur le moniteur du plein écran.
 - Bug corrigé au passage : `set_fullscreen(False, *taille)` passait la taille comme écran/mode (pyglet veut width=/height=), d'où une fenêtre 640x480 au retour d'un lancement en plein écran.
 - Établi : tools/test_ecrans.py (35 tests, faux Screen : ordre changé, résolution changée, doublons de nom, écran illisible, JSON absurde) et test_mode_fenetre. Vrai pyglet X11 avec 2 moniteurs (/tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/cam45/multi.out) : choix du moniteur 2 donne 800x600, retour en fenêtre à (40,30), déplacement 1<->2 en plein écran, recentrage à (80,60). Limite : les deux écrans Xvfb sont superposés en (0,0), donc seules les tailles sont discriminantes.
 - Capture de la page : /tmp/m_cam45aff_b120.png.
 - Non vérifié : Windows réel multi-moniteurs, DPI différents par écran, position réelle des écrans, comportement de pyglet quand on glisse la fenêtre d'un écran à l'autre.

2. Escaliers / glissement vertical : AUCUN glissement parasite trouvé, aucun code de caméra modifié. Un test est ajouté. Établi par désassemblage et mesures, pas par un ressenti.
 - Moteur : TownCamera::execute (0x1d165c) fait setTarget(position du joueur) à chaque pas quand la caméra n'est pas verrouillée (+0x3e = 0), sans Lerp ni amortissement en Y. Mesuré sur la rampe à 45° de `ckf4` (ΔY ≈ 0,113 par pas à la marche) : cible Y = héros Y − 0,047 et caméra Y = héros Y + 28,89, au pas près.
 - Unity : SceneCamera n'a aucun champ de lissage. `cmd_camera` fait seulement passer la position par FldObject.GetEventLimitedPos, et seulement sur écran très large avec une limite d'événement (c'est de l'X/Z, pas de l'Y).
 - Visionneuse : `_camera_ville` ne corrige que X/Z (`cam_dec`, `cam_res`), jamais Y. Simulation avec la vraie `_camera_ville` et l'interpolation de `_interpoler` sur la trace moteur de `ckf4` (2552 images) : NDC y du héros constant (−0,01512, écart < 1e-9) en montée, à l'arrêt et en descente. Idem à 30/60/144 images par seconde, avec ou sans « Centrer la caméra ».
 - Généralisé : balayage de 529 cartes, soit une vingtaine à pentes de 1 à 6 unités (châteaux, tours, grottes : `ckf4`, `ckout`, `ciido`, `cdido`, `chout`, `ckf3f5`, `cef2`, `dbout`, `cjf2b`…). Amplitude de la cible caméra égale à celle du héros, au centième près. Les seuls écarts viennent de cartes où le héros sort sur la carte du monde.
 - Conclusion : le mouvement vertical vu dans les escaliers est la caméra d'origine qui suit la hauteur du héros 1:1 (le décor défile quand la pente monte ou descend). Ce n'est pas un lissage comme dans le cas du père. Il est identique sur le téléphone, et indépendant de la course ou de la marche, ce qui colle à « que je coure ou non ».
 - À décider avec Sylfried : si ce suivi l'importune, ce serait une NOUVELLE option (caméra qui ignore la hauteur du héros), pas un correctif de bug. Je ne l'ai pas faite : « le jeu d'origine fait foi ».
 - Non vérifié : trace réelle d'une montée par la vraie action d'escalier entre étages (`TownKaidanAction2`, objets d'id commun 0x8a/0x8b) : je n'ai pas réussi à la déclencher dans le harnais. Établi par la liste des appels : elle n'appelle aucune fonction de TownCamera, donc même chemin d'exécution que ci-dessus. Échelles, cordes (TownActionRura), ponts et chutes (TownFallAction, qui verrouille la caméra) non tracés. Le ressenti sur la machine de Sylfried n'est pas vérifié.

3. Remises à zéro de la molette : FAIT. Ctrl + molette (haut OU bas) = distance par défaut (la molette seule zoome toujours). Clic molette sans déplacement = position de la caméra (rotation + inclinaison). Ctrl + clic molette = les deux. Un clic suivi d'un déplacement de 4 px ou plus est une rotation, rien n'est remis.
 - Conflit : l'ancien « Ctrl + clic = zoom seul » est retiré, car c'est maintenant Ctrl + molette. « Clic molette = direction » est gardé (c'était déjà la remise de la position : pas de conflit).
 - Les trois gestes sont dans Commandes (lignes d'information en lecture seule, capture /tmp/m_cam45cmd_b175.png) et dans les aides des entrées Distance caméra, Touche spéciale et touches de caméra.
 - Établi : 49 tests dans test_entries.py.
 - Non vérifié : la sensation avec une vraie souris.

4. Inversions de la caméra souris : FAIT. Sur la page Commandes, section « Caméra à la souris » : « Inverser gauche / droite » et « Inverser haut / bas ». Clés `camera_inverser_gd` / `camera_inverser_hb`, défaut Non (comportement actuel), ↺ rétablit Non, valeur absurde dans le JSON = Non.
 - Chaque réglage n'inverse que son axe (`entrees.pivoter`, bornes conservées). Flèches du clavier et remises à zéro inchangées.
 - Établi par test (faux événements, 4 combinaisons).

2) COMMITS (un par point ; les 2 lignes Co-Authored-By et Claude-Session sont en pied de chaque message)
 - 57ada9e  Écran du plein écran (point 1)
 - 4145112  Souris : Ctrl + molette, clic molette, Ctrl + clic molette (point 3)
 - 4b452e4  Inverser gauche/droite et haut/bas (point 4)
 - 91a2ab1  Test « pente sans glissement vertical » dans test_town_camera.py (point 2, test seul)

3) NOTES À FUSIONNER DANS LES DOCS (prêtes à coller)
 - Réglages : `ecran_plein` (None ou dict indice/x/y/largeur/hauteur/nom), `camera_inverser_gd`, `camera_inverser_hb` (booléens, défaut Non). Aucun changement de défaut existant : pas de migration. `ecran_plein` est nettoyé à la lecture (`ecrans.valide`).
 - Nouveau module `dq4_pc/ecrans.py` (logique pure des moniteurs) et tools/test_ecrans.py (35 tests).
 - API : `Jeu.regler_plein_ecran(oui, deplacer=False)`, `_poser_plein_ecran(plein, ecran=None)`, `_mettre_plein(plein, taille, ecran=None)`, `regler_ecran_plein`, `valeurs_ecran`, `nom_ecran`, `note_ecran`. `GesteMolette.relacher()` rend 'direction' / 'tout' / None (plus 'zoom'). `entrees.pivoter(..., inverser_gd=False, inverser_hb=False)`.
 - Contrôles : Ctrl + molette = distance par défaut ; clic molette = position ; Ctrl + clic molette = les deux. Ctrl = Ctrl du clavier ou « Touche spéciale ».
 - pyglet 2.1.19 : sur X11 Xinerama sans RandR, `XlibScreenXinerama` n'a pas `is_primary` (`get_default_screen` plante : limite de pyglet, `lister` protège avec try/except). Xvfb avec RandR ne montre qu'un écran. L'ancien `set_fullscreen(False, *taille)` était faux.
 - Caméra, établi : TownCamera::execute fait setTarget(joueur) à chaque pas ; modes +0x48 : 0 rien, 5 un personnage, 6 le joueur, 1 à 4 déplacements (MoveBase). Aucun lissage en Y côté moteur, Unity ou visionneuse. `cmd_camera` (Unity, D14568) passe la position par FldObject.GetEventLimitedPos (limites d'événement, seulement sur écran très large, via UIFix.IsLargeAspectRatio) : piste possible pour les bornes 16/9 `bornes_x`, non explorée.
 - Escaliers entre étages : `TownKaidanAction2` (objets d'id commun 138/139) déplace le héros par TownActionMoveToTarget et n'appelle aucune fonction de TownCamera. Liste des cartes à escaliers : /tmp/cam45/kaidan.json (une centaine de cartes).
 - Piège de test moteur : `startTown(nom)` sans téléportation place le héros en (0, 0,047, 0,78), souvent bloqué. Rampe d'essai : `ckf4`, marche HAUT / BAS.

4) NON VÉRIFIÉ (récapitulatif)
 Windows et vrai multi-moniteurs ; DPI par écran ; position réelle des écrans ; sensation souris ; montée par la vraie action d'escalier entre étages ; échelles, cordes, chutes ; ressenti de Sylfried sur le point 2.

FICHIERS TOUCHÉS
 dq4_pc/ecrans.py (nouveau), dq4_pc/fenetre.py, dq4_pc/pause.py, dq4_pc/reglages.py, dq4_pc/entrees.py. Tests : tools/test_ecrans.py (nouveau), test_window_mode.py, test_entries.py, test_interface_settings.py, test_town_camera.py. Hors périmètre strict, changement minimal : pause.py et window.py sont des zones partagées (voir pièges).

CAPTURES ET OUTILS (/tmp)
 /tmp/m_cam45aff_b120.png (Affichage), /tmp/m_cam45cmd_b175.png (Commandes), /tmp/cam45/ (harnais cam45_h.py, t_st.py, t_ndc.py, tr_ckf4.pkl, kaidan.json), RG /tmp/rg_cam45.json.

PIÈGES DE FUSION
 - pause.py, page Affichage : ma ligne « Écran du plein écran » (`ecr`) est insérée juste après `fen`. Si l'agent « ui » réordonne ou renomme, mettre à jour la liste `ORDRE` de PageAffichage dans test_window_mode.py (j'y ai ajouté 'Écran du plein écran' en 2e position et décalé `e[2]`) et le faux `J` de ce test (valeurs_ecran, valeur_ecran, nom_ecran, note_ecran).
 - pause.py, `_e_commandes` : j'ai ajouté `inverse()`, la section « Caméra à la souris », 5 lignes 'sep' avec `v=`, et un cas dans `dessiner`. Les modifications de l'aide de la ligne « Touche spéciale » et des 4 touches caméra sont aussi à moi.
 - settings.py : deux lignes DEFAUT insérées, `BOOLEENS_SON_TEXTE` étendu (autre agent probable : ajouter ses clés à la suite).
 - test_interface_settings.py : deux lignes `HORS_INTERFACE |=` (une par commit).
 - window.py : `regler_plein_ecran` et `_poser_plein_ecran` ont un nouveau paramètre ; `_molette_relache` / `on_mouse_scroll` modifiés. À surveiller si l'agent « combat » touche `regler_fondu`, ou si un autre agent change la bascule.
 - Faux de test_entries.py (`Faux`) dépend de la liste de méthodes de `Jeu` copiées.

---

## Agent « chargement » (a3e5cc796bd50fbd6) — 02/11 21:03

RAPPORT FINAL, mission « chargement » (préfixe CH)

Worktree /home/claude/wt45-chargement, branche agent45-chargement (depuis 84b3f22). Working tree propre, rien poussé, branche inchangée. Pas de fichier dans docs/ (notes plus bas). Aucune sauvegarde de Sylfried écrite (tests dans /tmp/sv_*). Tous les commits portent les deux lignes Co-Authored-By / Claude-Session.

RÉSUMÉ
- Point 1, rideau au lancement : PARTIEL. Une cause réelle trouvée et corrigée (CH-1). Les causes propres à Windows ne sont pas vérifiables ici : mesures défensives, non vérifiées.
- Point 2, micro-images au changement de carte : FAIT côté moteur et viewer sous Linux/xvfb. Le rendu sur vrai GPU et Windows reste non vérifié.

COMMITS (dans l'ordre)
1. f37696e Suivi horodaté du démarrage et des changements de carte (DQ_SUIVI), outil de diagnostic. Nouveau dq4_pc/suivi_charge.py plus des points de mesure dans window.py. Sans DQ_SUIVI, aucun effet.
2. 6239b16 CH-1 : titre, la 1re image montrait un ciel sans ses bandes latérales (l'« effet de rideau »). Une ligne dans Jeu._tracer_ciel : `self._dom_lie = None`.
3. 0be4137 CH-2 : retenue du dessin pendant un changement de carte.
4. 9848871 CH-3 : le temps du chargement n'est plus rattrapé par le moteur.
5. 9b06b98 CH-4 : lancement Windows (transitions DWM coupées, 2e image noire). NON VÉRIFIÉ.
6. 664c01f CH-2b : la retenue compte ses propres images (robuste au rechargement d'un état).
7. a5100a6 CH-2c : pas d'interpolation de caméra à l'image qui lève la retenue.
8. 31c5225 CH-3b : absorption limitée à un vrai blocage (> 133 ms), 3 images au plus par chargement.

POINT 1 : RIDEAU AU LANCEMENT
Établi (journal DQ_SUIVI sous xvfb, captures avant/après) :
- Cause CH-1. `_tracer` ne valide les tampons que quand le domaine change (`_dom_lie`). Les bandes de ciel du titre sont créées après le 1er tracé de l'image, donc elles ne partaient pas. 1re image : ciel biaisé avec bords noirs (/tmp/m_chg_d0_b1.png, ligne 360 non noire de x=278 à 1256). Image suivante : plein écran. Après correction : x=0 à 1279 (/tmp/m_chg_d1_b1.png).
- Chronologie du lancement : fenêtre créée cachée à +0,037 s, image noire présentée à +0,058, fenêtre montrée à +0,061. Taille 1280x720 à la création, à l'affichage et dans on_resize : pas de redimensionnement. Logos 426 images, pire écart 107 ms. Titre : ev01 se charge dans la 1re image dessinée, et le moteur a déjà fait 3 pas, donc le fondu du titre est à 0,87 à la 1re image.
- Hypothèses écartées ou sans effet visible sous Linux : taille puis redimensionnement, tampon non vidé, désynchro logos/fondu (13 % du fondu déjà écoulé, non corrigé), préparation du cache (fil d'arrière-plan), caméra fausse (déjà complète au 1er dessin).
- Création du rendu hors écran (MSAA) pendant l'affichage : il est maintenant créé sous le noir de la retenue des changements de carte (CH-2). Au tout 1er dessin du titre il reste dans la 1re image visible. Je n'ai pas préchargé ev01 ni le PostFX dans le constructeur (pas de défaut visible démontré, évite de toucher au code de démarrage).
Non vérifié, Windows uniquement (CH-4) : animation d'ouverture DWM, présentation d'un flip sur fenêtre cachée, stalls de la 1re image sur vrai GPU, flash du plein écran (G-004 inchangé).
- `transitions_dwm` : DWMWA_TRANSITIONS_FORCEDISABLED pendant l'ouverture, remis 2 s après la 1re image. Toute erreur est sans effet (hors Windows : rien). Testé avec un faux dwmapi (3 tests).
- 2e image noire juste après `set_visible(True)`.
Raison : pas de Windows ici. Cause supposée : un fondu d'ouverture de la fenêtre par-dessus le noir puis les logos, ou le fond de classe de la fenêtre le temps du chargement.
Si CH-4 ne change rien chez Sylfried, il peut se retirer sans risque. CH-1 est la correction certaine.

POINT 2 : MICRO-IMAGES AU CHANGEMENT DE CARTE
Chronologie du moteur (106 cartes de villes + mort → église + sortie d'église) :
- image k : paquet 0 (décor), 8, 9 (fondu d'entrée, repart de l'opacité 1), 11, 12 (personnages créés sans position), 37.
- image k+1 : paquet 10 (caméra) et 13 positions.
- k+2 : 13 sans position.
- k+6 ou k+12 : poses/directions.
- Quelques PNJ ne sont placés que plus tard, voire jamais (alors à l'origine après ORIGINE_APRES).
- Le paquet 0 ne remet pas la caméra à zéro.
Conséquence : à l'image k, décor neuf + caméra de la carte d'avant + aucun personnage placé, sous 3 à 7 % d'opacité de la scène. Plus, en temps réel, le chargement synchrone du décor (la 1re image d'une scène a coûté 56 à 793 ms) rattrapé par le moteur : 3 pas d'un coup, donc le fondu saute.

CH-2, retenue (Etat.chargement, engine.py + window.py) :
- Posée au paquet 0 si l'écran est couvert : opacité ≥ 0,9 sur un plan, ou fondu d'entrée de plus d'une image lancé dans le même lot.
- Levée par Etat.maj_chargement : au moins 1 image du moteur, caméra reçue, personnages visibles placés (2 images d'attente au plus), tuiles reçues sur la carte du monde, garde-fou 6 images.
- Pendant la retenue, Jeu._dessiner_scene ne dessine que le noir et les fondus (même chemin que « scène pas arrivée »), et tick_fondu suspend le fondu d'entrée. Les durées de fondu ne changent pas : le fondu démarre une image plus tard, sur une scène complète. Vérifié par test (durée exacte conservée).
- Le rendu hors écran est créé sous ce noir.
CH-3 (+CH-3b) : après `_charger_carte`, `t_boucle = None` (l'horloge du moteur repart). `_absorber_blocage` fait de même pour une image de plus de 4 pas parmi les 3 qui suivent un chargement. Mon 1er seuil (2 pas, 6 images) figeait le moteur sur un rendu logiciel lent (6 images de suite au même pas moteur) : mesuré, corrigé en CH-3b.

Mesures avant/après (harnais moteur seul /tmp/chg/mesure.py, réglage par défaut vitesse des fondus x2). Une « image fautive » = image du moteur où la scène est visible à plus de 2 % alors que caméra, personnages ou tuiles ne sont pas en place.
- 106 cartes de villes par téléportation (/tmp/chg/o_tpmax_*.txt) : 111 images fautives avant, 0 après. L'oracle en signale 4 sur une carte (mom2f1). C'est un PNJ que le moteur lui-même ne place que 6 images après sa création, à l'origine : comportement du moteur, pas de la retenue. Retenue : 1 image (105 cartes), 2 images (1 carte).
- Mort → église (slots 1, 2, 4, monstre 100) : 2 chargements chacun, avec 1 image fautive à 7 % avant, 0 après (/tmp/chg/o_mort*_*.txt). Slot 4, bataille forcée : 'ev01 → btl_pl_d' puis 'btl_pl_d → mak1f1', même résultat.
- Sortie d'église, slot 1 (/tmp/chg/o_marche*) : mak1f1 → maout, 1 image fautive avant, 0 après. Chargement du slot (ev01 → mak1f1) idem.
- Téléportation depuis la carte du monde (slot 4, 10 cartes) : 10 images fautives avant, 0 après.
- Carte du monde : entrée/sortie sans paquet 0 (27/28), couverte par la garde existante « carte du monde pas envoyée ». La retenue n'intervient pas. Au pas où les tuiles arrivent, le fondu est à 0,87 et le héros est placé.
- Viewer sous xvfb, temps réel, rendu logiciel, chargement mak1f1 (journaux /tmp/suivi_tr_avant.txt et /tmp/suivi_tr_apres.txt) :
  - avant : 1re image visible à fondu 0,80, puis sauts de moteur +3/+2.
  - après : 3 dessins noirs 'noir (retenue du chargement)' à fondu 1,00, puis 1re image visible à fondu 0,93, caméra et 3/3 personnages en place, fondu régulier (1 pas moteur par pas de fondu).
- Viewer, mode un-pas-par-image (/tmp/suivi_ap1.txt) : dessin 'noir (retenue)' puis 'scène' avec caméra neuve et 3/3 personnages.
- Avec MSAA 4 (/tmp/suivi_msaa.txt, aussi lancé sans écran via pyglet headless) : même séquence, « Rendu hors écran x4 » créé sous la retenue.

Pas de mesure viewer pour : porte/escalier sortant d'un bâtiment par touches, entrée/sortie de combat avec effet, chargement d'état.
- Porte/escalier : le héros ne bougeait pas avec mes touches de test. La sortie d'église (mak1f1 → maout) est mesurée au niveau moteur, pas en viewer.
- Combat avec effet : couverte seulement au niveau moteur (bataille forcée).
- Chargement d'état : `_appliquer_etat` charge la carte lui-même et remet t_boucle à zéro, aucun paquet 0 ; je n'ai pas lancé de test viewer.

Non traité, par choix : une coupure franche sans fondu (écran non couvert). Elle garde le comportement d'origine, car il faudrait figer la dernière image affichée. Je n'ai pas relevé de cas dans les parcours testés (portes, mort, sorties, combat forcé).

À savoir : poses et directions des personnages n'arrivent qu'à k+6 ou k+12, y compris dans le jeu d'origine. Je ne les attends pas (ce serait retarder le fondu d'au moins 5 images).

TESTS
- Nouveau tools/test_chargement.py : 22 tests (règles d'Etat, absorption, interpolation, DWM simulé, moteur d'origine sur 5 téléportations avec --apk/--saves).
- Suite complète tools/test_*.py exécutée en headless sur le code final : tout OK. Deux exceptions de mon script seulement (passage d'arguments), relancées à la main avec les bons : test_etats_correctifs OK, test_texte_defilement OK (OK avant les commits CH-2c/CH-3b, non relancé depuis ; ils ne touchent ni le texte ni les états).
- pyflakes OK sur engine.py, load_tracking.py, test_loading.py. window.py : 2 avertissements déjà présents à 84b3f22 (dims, sel), pas sur mes lignes.

LIGNES TOUCHÉES DANS LES FICHIERS PARTAGÉS (à rebaser avec « caméra » et « combat »)
window.py :
- import suivi_charge + hooks SV.noter (Jeu.__init__ début, _creer_fenetre, _demarrer_moteur, constructeur).
- fonction transitions_dwm avant class Jeu.
- _creer_fenetre : 3 lignes autour de set_visible(True) (dwm_coupe, 2e flip noir, note du journal).
- on_draw : 1re image (planification DWM), appel de _absorber_blocage, _suivre_dessin.
- Jeu._absorber_blocage et Jeu._suivre_dessin (méthodes ajoutées).
- _instantane : champ `ret` ajouté (la clé `cle`, utilisée par _coupure_camera, est inchangée) ; _interpoler : une condition en plus.
- _charger_carte : une note de journal en fin.
- _dessiner_scene : `retenu`, `t_boucle = None` après le chargement, condition de la garde noire étendue, warm-up PostFX, tag _dessin_genre.
- _tracer_ciel : `_dom_lie = None`.
engine.py :
- constantes CHARGEMENT_*.
- Etat : attribut chargement, __setstate__, appliquer (début, paquet 0, paquet 10, bloc après la boucle), maj_chargement, ligne dans tick_fondu.
- Moteur.step : appel de maj_chargement avant tick_fondu.

NOTES À FUSIONNER DANS docs (prêtes à coller)
Texte complet dans /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/notes_chargement.md (sections : chronologie d'un changement de carte, retenue du dessin, règle _dom_lie, blocages de chargement, DQ_SUIVI, Windows).
Points clés :
- Au paquet 0, Etat.appliquer ne remet pas la caméra à zéro : caméra, personnages et teinte arrivent à k+1.
- Règle de dessin : toute liste de sommets créée ou réécrite après le 1er `_tracer` d'une image doit remettre `self._dom_lie = None`.
- DQ_SUIVI=1 (console) ou DQ_SUIVI=chemin donne un journal horodaté du lancement et des 16 dessins qui suivent un chargement.

À RETENIR (appris dans cette mission, pas de mémoire modifiée)
- Le viewer se lance sans X ni verrou xvfb : poser pyglet.options['headless']=True avant d'importer fenetre (scripts /tmp/chg/apres_viewer_h.py et avant_viewer_h.py). Utile quand la file /tmp/xvfb.lock dépasse 15 tâches (attente de plus de 30 min mesurée ce soir).
- /tmp/chg/mesure.py (moteur seul, mode avant/après) et /tmp/chg/analyse_suivi.py (lecteur de journal DQ_SUIVI) sont réutilisables.

FICHIERS DE PREUVE
/tmp/m_chg_d0_b1.png (avant) et /tmp/m_chg_d1_b1.png (après) ; /tmp/suivi_ap1.txt, /tmp/suivi_msaa.txt, /tmp/suivi_tr_avant.txt, /tmp/suivi_tr_apres.txt, /tmp/suivi_tr_h_*.txt ; /tmp/chg/o_*.txt (mesures moteur).

---

## Agent « texte » (af2afb0233cfb4a16) — 02/11 21:19

RAPPORT TX (agent45-texte). Résumé : le placement vertical / horizontal de la visionneuse est DÉJÀ identique au jeu d'origine, donc il n'y a pas de décalage visionneuse / mobile à corriger. Le texte « trop bas » existe aussi dans le jeu d'origine. J'ai quand même appliqué, comme demandé, une correction globale en un seul endroit : un recentrage optique, qui s'écarte volontairement du mobile. Elle est dans un commit séparé que tu peux écarter si tu préfères rester fidèle.

1. PAR POINT

a) Cause racine du décalage visionneuse / jeu : FAIT, aucun décalage. ÉTABLI.
- Le jeu utilise des TextMesh Unity (ancre 0-8, alignement, characterSize, lineSpacing exportés dans `ui_layout.json`). Ce n'est pas un composant UI Text ni TextMeshPro.
- Le moteur envoie les noms de groupes de monstres sous la forme `'Nom\n\n\t×2'` : 3 lignes (saut, ligne vide, tabulation, ×2). Je l'ai lu dans le journal du combat avec `TXSTR` / `TXPLAQ` : `'Glacyclone\n\n\t×2'`. C'est pourquoi « ×2 » est à 2 pas de ligne sous le nom.
- La capture mobile (ecran4) et la capture PC (ecran3) ont la même échelle : 1,688 px par unité (traits du cadre à 754,5 px).
- Texte « Ragnar » de l'onglet : profil de lignes identique pixel pour pixel sur le PC et le mobile. La base est à 8 px au-dessus du trait du corps de fenêtre des deux côtés, et le bord gauche à 30,5 px du trait du cadre des deux côtés.
- Formule actuelle de la visionneuse (bloc de N lignes de pas = interligne 23,525 × characterSize × 0,1 × lineSpacing, ancre haut / milieu / bas, base à ascent 18,887 sous le haut de la ligne, biais dy de 20) : elle redonne les lignes de base du mobile à ±0,6 unité.
  - « Rat volant » (1 ligne) : −13,4 unités sous le centre du bouton ; mobile −13,5.
  - « Scarapince » / « ×2 » (3 lignes) : −3,3 / −23,9 ; mobile −3,4 / −24,2.
- Rendu hors écran du type 33 (choix de cible) à l'échelle du mobile : onglets, « Rat volant », « Scarapince / ×2 » à ±1 px de la capture du mobile.
- Plaque PC « Scarapince ×2 » : lignes de base à 46 et 82 px sous le bord intérieur haut ; bouton mobile (même chaîne) : 47 et 82.
- Cause du « trop bas » :
  - Unity pose la ligne de base à `ascent` sous le haut de la ligne quel que soit `lineSpacing` (donnée du glyphe).
  - Les `lineSpacing` du jeu (0,441 cibles, 0,481 plaques de monstres, 0,801 onglets / boutons / noms, 0,873…) raccourcissent la boîte de ligne ; ils sont réglés pour la police japonaise.
  - L'encre de SE-GARRIR, centrée dans sa boîte naturelle de 23,5 px, descend donc de (1 − lineSpacing) × 23,525 × characterSize × 0,1 / 2 sous le centre de sa boîte.
  - Cela donne 6,5 unités (11 px à 1,688) pour « Rat volant » et les plaques de monstres, et 2,3 unités pour onglets et boutons.
  - C'est ce qui colle « ×2 » et « Rat volant » au bas du cadre.
- SUPPOSÉ : pour les ancrages haut et bas, aucune référence mobile. Le décalage encre / boîte ne dépend pas de l'ancrage, donc je l'applique pareil, mais je n'ai pas pu le confronter au mobile (nom dans la bande d'état, plaques de monstres).

b) Correction globale : FAIT (écart volontaire du jeu d'origine).
- Fonction `recentrage_texte(interligne, u, ls)` dans `dq4_pc/ui_menu.py`, appelée une seule fois par `Rendu._texte`. Elle remonte le texte de (1 − ls) × interligne × u / 2 quand `lineSpacing` < 1.
- Elle s'applique à tous les textes de menu et de combat qui passent par `Rendu._texte`, uniquement avec la police SE-GARRIR.
- `lineSpacing` ≥ 1 (PV / PM / Nv., listes) : inchangé, ils sont réglés sur les jauges.
- `DQ_TEXTE_ORIGINAL=1` restitue le placement exact du jeu. Pas de réglage dans le menu Pause : cela aurait touché `pause.py`, `settings.py` et `window.py`, zones des autres agents. Si Sylfried veut un bouton, c'est un ajout de 3 lignes (clé `texte_recentre`, `defaut=True`, `pause._choix`).
- Interprétation retenue : Sylfried demande d'améliorer l'alignement (« rien que tu puisses faire ? ») donc on s'écarte du mobile. Si tu préfères rester fidèle au mobile, écarte le commit f756c63 ; le premier commit n'a aucun effet visible.

c) Mesures avant / après (ÉTABLI).
- Rendu hors écran à l'échelle des captures (`/tmp/tx45/t33_cible_viewer_original.png` et `_recentre.png`) :
  - « Rat volant » : encre centrée sur le bouton, 0,6 px d'écart contre 11 px avant.
  - « Scarapince » / « ×2 » : marges 13 / 11 px dans le bouton ; avant, « ×2 » touchait le bas.
  - En-tête « Doc » de la plaque d'état : centre de l'encre à 5 px sous le centre de la bande (3 unités), 1 px après.
  - PV / PM / Nv. : inchangés.
- Captures réelles de combat à 1280×720, mêmes images, `DQ_TEXTE_ORIGINAL=1` contre défaut (`/tmp/tx45/c_avant_126.png`, `/tmp/tx45/c_apres_126.png`, comparaison `/tmp/tx45/combat_reel_avant_apres.png`) :
  - nom « Ragnar » de la plaque d'état : remonté de 2 px, centre de l'encre à 0,5 px du centre de la bande (2,5 px avant) ;
  - plaque « Glacyclone ×2 » : remontée de 5 px, centrée ;
  - onglet « Ragnar » : −2 px ; boutons « Attaquer » : −2 px ;
  - 3831 pixels changent, uniquement dans les textes.
- Autres fenêtres : 31 types rendus avant / après avec des libellés d'exemple (boutique 57 / 58 / 60, menu terrain 4 / 5, départ 53 / 54, église 66, listes 35 / 36, 3 / 30, Statut 13–17…) : seuls les textes bougent, vers le centre, sans régression visible. Feuilles `/tmp/tx45/feuille_gA.png`, `feuille_gB.png`, `feuille_g30.png`, `etat_plaques_avant_apres.png`, `commandes_avant_apres.png`.
- Pas rendues : l'historique et le cartouche de nom (zone de l'agent « ui »).
- Les retours à la ligne tombent au même endroit que sur le mobile (3 lignes, « ×2 » sous « Scarapince ») : ÉTABLI sur le rendu, d'après la capture. Les débordements de texte français ne sont pas touchés (D-133).

2. CORRECTIONS (branche agent45-texte, base 84b3f22, arbre propre)
- ab76eb9 : `base_premiere_ligne()` isolée dans `ui_menu.py` ; aucun changement de rendu ; `tools/test_texte_recentrage.py` (3 tests calés sur les mesures du mobile).
- f756c63 : `recentrage_texte()` + appel dans `Rendu._texte` ; 5 tests de plus (8 au total). Pyflakes : seul l'avertissement connu `ax` ; test_plaque_depart (12), test_panneau_interface (10) et test_reglages_interface (15) passent.

3. NOTES À FUSIONNER DANS docs/ (à coller dans `viewer-notes-dq4-pc.md`, remplace « Nom de Ragnar trop bas » de #43)

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

## Agent « magie » (afd84db2f3277f278) — 02/11 21:31

RAPPORT FINAL, mission « magie » (PR #45, préfixe MG)
Worktree /home/claude/wt45-magie, branche agent45-magie (base 84b3f22). `git status` propre. Aucun push, aucun changement de branche, aucune PR. Fichiers patch FR et sauvegardes de l'utilisateur non touchés (tests dans /tmp/sv_*, RG /tmp/rg_mg1.json, cache /tmp/uicache4).

COMMITS (tous avec les 2 lignes de pied)
- 220cd36 Magie : la rangée fantôme de la liste des sorts (code 6 de Make_NameButton) n'existe plus  [points 1, 2, 4]
- b340625 Magie : « Coût en PM:<tab>  2 », la tabulation vaut 8 espaces (TextMesh.tabSize)  [point 3]
- 757c841 test de la liste des sorts, de la ligne de coût et des usages sans effet (moteur d'origine)  [points 2, 4, 5]
- 670b8a0 Fenetre.code tolère les Fenetre factices des tests (getattr noms_liste)  [correctif de mon changement : test_casino_bestiaire cassait]
- 061ac13 MG: fiche d'un sort, la ligne de coût et la description tiennent dans leurs cadres  [point 3 et point 4 : touche la zone partagée « texte », Rendu._texte]
Fichiers modifiés : dq4_pc/ui_menu.py (+56) et tools/test_magie_liste.py (nouveau, 23 tests dont 8 sur le vrai moteur).

POINT 1, reproduction : FAIT (Établi)
Sauvegarde emplacement 1 : Ragnar (PM 0) + Doc (invité niveau 255, 30 PM, sort 196 Premiers secours). Menu terrain, Magie (id bouton racine 1), Doc (id 3 du port 5), clic sur « Premiers secours » : je retrouve exactement les écrans 7 et 8 de Sylfried. Captures avant : /tmp/m_magie45av_b110.png, b180, b250, b320. Après : /tmp/m_magie45ap_b110.png, b180, b250, b320.

POINT 2, origine de <ERR 0x07000000.0> / <ERR 0x03000000.0> : FAIT (Établi)
Cause racine : le moteur règle la mise en page de la liste de boutons nommés (Make_NameButton, type 8) par le code 6 = preset (NOMS_PRESETS, MenuPortItemTable.name_button_param), que la visionneuse ignorait. Résultat : une 5e rangée fantôme restait visible et cliquable sous « Premiers secours » (la liste de Doc n'a qu'un sort). Le clic envoyait au moteur le bouton 4, c'est-à-dire un sort inexistant. Les textes <ERR 0x07000000.0> (nom absent), <ERR 0x03000000.0> (description absente) et « Coût en PM  0/ 30 » sont les chaînes de repli du moteur pour un sort absent (le « ERROR %d » aussi). Correctif : `Fenetre.code` applique le preset (`_liste_noms`) ; seules les rangées dont le code n'est pas 0 sont actives ; idempotent, preset inconnu ignoré. Le menu d'action des objets (preset 1, 5 rangées) garde sa logique. Testé de bout en bout sur le vrai moteur : liste de Doc = 1 rangée (codes [2,0,0,0,0]) ; nom, description, coût, Lancer, cible, effet et PM dépensés fonctionnent (PM 30 vers 28, PV de Ragnar 20 vers 47, message « Les blessures de Ragnar guérissent ! » affiché dans la fenêtre de message, « ; » du nom consommé).

POINT 3, « Coût en PM » : FAIT pour la liste des magies et la fiche du sort ; AUDIT PARTIEL
- Liste (b340625) : le texte du moteur est « Coût en PM:<tab>  2 » avec TextMesh.tabSize = 8. La police de la visionneuse n'avait aucun glyphe pour la tabulation (largeur nulle), d'où « Coût en PM: 2 » collé. Unity compte une tabulation comme tabSize espaces : elle devient 8 espaces. Limité à Make_NameButton.
- Fiche du sort, type 7 (061ac13) : « Coût en PM 10/ 30 » (FR) dépassait du cadre de droite (texte de 154 à 160 unités depuis x=75 pour un cadre x 63 à 221 ; la version anglaise tenait). La ligne (nœud 2) porte maintenant une limite droite `fit_x = COUT_FICHE_X_MAX = 214` (cadre moins la marge des plaques, 7) et `Rendu._texte` la comprime (facteur mini 0,7 ; ici environ 0,88) même avec la police bitmap d'origine. Le nom, « Lancer » et la description ne changent pas. Capture : /tmp/m_magie45k2_b110.png (Évac' 1/30), b180 (Protection sacrée 4/30), b250 (Multisoin 10/30), b320 (Rappel 8/30), b390 (Téléportation).
- Non vérifié : les autres fenêtres à tabSize de la mise en page : type 20 Make_MemberShift (8), 34 Make_BattleGo (8), 35 Make_BattleIM (8), 31/33/39 (monstres, 25). La même règle (tabulation = tabSize espaces) y serait fidèle à Unity, mais je ne l'ai pas généralisée faute de pouvoir tester en combat (zone « combat » d'un autre lot ; battle_history.py gère « \t×3 » à part). Extension d'une ligne : retirer `self.noms_liste` de la condition dans `Fenetre.param_str`. Écran Statut et PM courant/max d'autres écrans : non audités (les écrans PM du menu terrain, listes de personnages « PM 30/ 30 », s'affichent correctement sur les captures).

POINT 4, liste des sorts : FAIT (Établi, sauf mention)
4 rangées par page ; flèches de page et « 1/2 » (2/2, 4/4 avec 13 sorts) ; pas de sort grisé : le moteur refuse par « Pas assez de PM ! » ; clavier (BAS déplace le curseur, DROITE tourne la page, ESPACE valide, RETOUR en arrière) et clic souris fonctionnent ; Ragnar seul : message du jeu « Ragnar n'a appris aucun sort ni aptitude pour d'autres situations que le combat ! » (capture /tmp/m_magie45n_b110.png) ; seuls les membres avec sorts sont cliquables.
Autre défaut trouvé et corrigé dans 061ac13 : 9 des 18 sorts de terrain ont une description FR de 3 ou 4 lignes (coupées vers 20 caractères) pour un cadre de 2 lignes ; la 3e ligne sortait du cadre puis de l'écran (Multisoin, Rappel, Résurrection, Téléportation, Évac', Coup d'oeil, Passage sûr, Protection sacrée, Tic-tac). Au-delà de 2 lignes, `Rendu._recoupe` remplace les retours à la ligne par des espaces et recoupe à la largeur du cadre (DESC_FICHE_X_MAX = 148, le cadre va jusqu'au bouton retour) : les 18 tiennent sur 2 lignes (captures k2 ci-dessus). Le texte envoyé par le moteur n'est pas modifié ; un texte qui ne diminue pas de lignes reste tel quel ; ≤ 2 lignes : inchangé. Supposé : le mobile d'origine coupait aussi ces descriptions (cadre de 2 lignes) ; je n'ai pas pu le vérifier.

POINT 5, actions sans utilité : FAIT sur le moteur ; DÉCISION À TRANCHER pour le message
Preuves par traces de paquets sur le vrai moteur (tests MoteurReel) :
- Premiers secours sur Ragnar aux PV pleins : le moteur affiche « Doc lance le sort Premiers secours ! » puis « Les blessures de Ragnar guérissent ! » (le même message qu'à PV bas, trompeur), et ne dépense AUCUN PM (30 vers 30). Règle : `BaseAction::useMp` (0x1a7424) ne dépense que si l'octet [this+0x14] vaut 1 (l'action a eu un effet). Sur blessé : PM 30 vers 28, PV 20 vers 47.
- Rappel sur un vivant ; Antipoison sans poison : « Mais rien ne se passe. », aucun PM dépensé (le texte b0802000.mpt contient aussi « Mais il ne se passe rien. » et « Mais le sort échoue. »).
- Antipoison sur un empoisonné : « Ragnar n'est plus empoisonné ! », PM 30 vers 28. Rappel sur un mort : « Ragnar revient à la vie ! », PM 30 vers 22.
- PM insuffisants : « Pas assez de PM ! », rien de dépensé, rien d'appliqué.
- Objets (essais sur le moteur, scripts dans le scratchpad) : un objet sans effet n'est pas consommé.
La visionneuse laisse le moteur décider et affiche ses messages (fenêtre de message vérifiée par capture : /tmp/m_magie45m_b390.png). Il n'y a donc pas de bug côté visionneuse. Le souhait de Sylfried (un message du type « ça n'a pas grande utilité ») est un écart assumé par rapport à l'original, pour les sorts de soin à PV pleins. Je ne l'ai pas implémenté, c'est à lui de trancher. Si oui : cas à repérer côté moteur (PV avant = PV après, PM inchangés) et message à ajouter dans la zone « effet ». Non vérifié : lecture des sons (seuls les ids SE 300/306/501 observés côté moteur).

NOTES POUR LA DOC (prêtes à coller)
- Sorts de terrain (ids moteur 196 à 216) : 196 Premiers secours (2 PM), 197 Soins partiels (4), 198 Soins complets (6), 199 Multisoin (10, sans cible), 200 Rappel (8), 201 Résurrection (15), 202 Antipoison (2), 203 Téléportation (1), 204 Évac' (1), 205 Coup d'oeil (2), 206 Passage sûr (2), 207 Protection sacrée (4), 208 Tic-tac (4), 209 Mappille (0), 212 Détectrésor (0), 213 Fouille (2), 216 Sifflet (0). L'id 214 (Discreto) donne une description <ERR 0x03000000.0> et « ERROR 0 » (id artificiel). Les ids 157 à 160, s'ils sont appris, apparaissent dans la liste de terrain avec des noms <ERR 0x07000000.0>.
- Ids de boutons : menu racine Objets=2, Magie=1, Caractéristiques=4, Divers=5 ; Magie : port 5 liste des persos (Doc=3, Ragnar=2), port 8 liste des sorts (port 7 = pagination), cmd(8,rangée) ouvre la fiche (port 12 : nom, description, coût « Coût en PM  2/ 30 » = coût/PM courants, « Lancer »), cible = cmd(6,k) ; sort sans cible : « Lancer » = rangée 2 du port 8. Objets : cmd(4,2), puis cmd(5,3) (Sac), port 9 liste, port 8 menu d'action (preset 1), port 6 cible. Entrées : A=16, B=32, flèches 8/4/2/1, menu 0x800, parole 0x100. Clavier de la visionneuse : A=ESPACE, B=RETOUR ARRIÈRE.
- Make_NameButton : racine + 6 parts de rangée ; code 6 = preset (NOMS_PRESETS : (nombre de rangées, ordonnée de départ, pas)) ; code de rangée 0 caché, 1 visible, 2 sur deux lignes (nom relevé, ligne de coût). Pour les ports < 12, la commande 1 n'efface pas `cases` : les textes d'anciennes rangées cachées subsistent mais ne s'affichent pas.
- TextMesh.tabSize : une tabulation = tabSize espaces (pas de taquets).
- Offsets moteur : PlayerStatus = `_ZN6status9PartyData15originalPlayer_E` + 0x530*i ; HaveStatus +0x58 (PV +0x22, PV max +0x24, PM +0x26, PM max +0x28) ; HaveStatusInfo = HaveStatus − 0x48 (StatusChange +0x198, poison id 0x16) ; HaveAction +0xd0 (getCount, getAction(i), add(id,0), clear).
- Police bitmap (SE-GARRIR) : l'espace avance de 5 px ; avec elle `Rendu._texte` ne comprimait jamais le texte (porte `not bm`) : tout dépassement FR n'est donc corrigé nulle part ailleurs que par des limites explicites comme `fit_x`.

NON TRAITÉ / NON VÉRIFIÉ
- Tabulations des types 20, 31, 33, 34, 35, 39 (voir point 3).
- Téléportation : interface du choix de destination non testée (seul le début de la fiche l'est). Sort de combat (id 26) de l'emplacement 3 non testé. Descriptions d'objets (menu Objets) non auditées : le recoupage ne s'applique qu'au type 7.
- Aspect de la tabulation (écart de 8 espaces) comparé à l'original mobile : Supposé fidèle (sémantique Unity), pas comparé à une capture mobile.
- Sons : lecture non vérifiée.
- Source des cadres du haut (nom | Lancer | coût) et du bas de la fiche : non identifiée dans le code (la fenêtre type 7 n'a aucun maillage) ; mes limites 214 et 148 viennent de mesures sur les captures (cadre de coût x 63 à 221 ; cadre du bas jusqu'à 155,5, en unités). Si la mise en page des cadres change, ces deux constantes (COUT_FICHE_X_MAX, DESC_FICHE_X_MAX en haut de ui_menu.py) sont à revoir.

PIÈGES DE FUSION
- ui_menu.py : constantes NOMS_PRESETS, NOMS_DEPART, NOMS_PAS, COUT_FICHE_X_MAX, DESC_FICHE_X_MAX ; `Fenetre.__init__` (noms_liste, noms_dec) ; `Fenetre.code` (branche code 6) ; `Fenetre.param_str` (tabulation et marqueurs fit_x / wrap_x, juste avant `nd['text']['text'] = s`) ; nouvelle méthode `Fenetre._liste_noms` ; `Rendu._texte` (zone « texte ») : `N = len(lignes)` déplacé après le recoupage, deux lignes ajoutées (wrap_x, fit_x) et la condition de compression devient `(not bm or fit_x)` ; nouvelle méthode `Rendu._recoupe`.
- Les fenêtres Make_NameButton sont touchées globalement (menu d'action des objets : logique inchangée).
- Les tests d'autres lots qui fabriquent de fausses Fenetre doivent passer par getattr (déjà fait dans `code`).
- Tests : `python3 tools/test_magie_liste.py` (partie interface, 15 tests) ; avec `DQ_APK="/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks" DQ_SAVES=/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes` : 23 tests OK en 22 s. Passent aussi : test_casino_bestiaire, test_plaque_depart, test_reglages_interface, test_panneau_interface, test_pause_pages, test_historique_messages, test_reglages_son_texte. pyflakes : seul l'avertissement connu `ax` (ui_menu.py:1076, antérieur).

À TRANCHER PAR LE COORDINATEUR / SYLFRIED
1. Message sur les soins à PV pleins (écart par rapport à l'original, voir point 5).
2. Généraliser la tabulation aux types 20, 34, 35 (combat) après test en combat.
3. Le recoupage des descriptions modifie l'affichage du texte du patch FR (sans changer le texte) : à confirmer par rapport à ce que Sylfried voit sur son mobile.

INFORMATIONS À RETENIR (mémoire, apprises dans cette session)
- Emplacement 1 : Ragnar (PM 0) + Doc (invité niveau 255, 30 PM, sort 196) ; sorts de terrain ids 196 à 216 ; Objets=bouton 2, Magie=bouton 1 ; A=ESPACE, B=RETOUR ARRIÈRE.
- Le verrou xvfb (/tmp/xvfb.lock) est très disputé : un job peut attendre 15 minutes et plus.

CAPTURES (absolues)
Avant : /tmp/m_magie45av_b110.png, b180, b250, b320. Après : /tmp/m_magie45ap_b110.png, b180, b250, b320. Fiche du sort après 061ac13 : /tmp/m_magie45k2_b110.png, b180, b250, b320, b390 ; /tmp/m_magie45j_b110.png (Multisoin) et b180 (Premiers secours). Message de lancement : /tmp/m_magie45m_b390.png. Ragnar seul : /tmp/m_magie45n_b110.png. Liste paginée : /tmp/m_magie45m_b180.png et /tmp/m_magie45k_b110.png à b740. Écrans de Sylfried : /tmp/specs/img45/ecran7_pc_magie_liste_cout_pm.png et /tmp/specs/img45/ecran8_pc_magie_ecran_ERR.png.
