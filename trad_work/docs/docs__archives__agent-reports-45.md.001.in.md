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
