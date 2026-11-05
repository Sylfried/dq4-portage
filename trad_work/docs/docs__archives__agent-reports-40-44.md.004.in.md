## 3. Fenêtre flottante « Interface » déplaçable
- Appui long (0,35 s, souris ; le doigt est supposé arriver comme événement souris) : le panneau se soulève (cadre agrandi, liseré doré, titre doré, infobulle coupée) et suit le pointeur ; bougé de plus de 8 px avant le délai = annulé.
- Appui court : replier / déplier (comme avant, Tab marche toujours). Replié, le panneau garde sa largeur dépliée (sinon il fuit sous le pointeur).
- Double clic sur la barre : retour à la position initiale calculée pour l'interface choisie (coin haut droite, sinon coin libre ; recalcul à chaque double clic). Conserve l'état plié.
- Toujours dans l'écran (clamp). Position mémorisée pour la SESSION seulement (non enregistrée, non liée à l'interface ; une nouvelle ouverture de l'éditeur remet la position automatique).
- Variables d'essai : `DQ_APPUI_LONG` (0,35) et `DQ_DOUBLE_CLIC` (0,40) en secondes.
Établi par captures : soulèvement + déplacement, repli, remise en place, dépli par clic simple.

## Captures utiles (absolues)
Avant (code 1e87ca6) : /tmp/m_avp_b100.png (page, ordre inversé : option d'affichage en 1re ligne), /tmp/m_avp_b112.png, b126, b138, b150 (liste alphabétique plate, « Aperçu d'objet » présent). Contact : /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/cmp_old_liste.png.
Après : /tmp/m_ap1_b100.png (page), b112 / b124 / b136 / b148 / b160 (liste groupée) ; comparatif avant/après : …/scratchpad/cmp_selecteur2.png et cmp_selecteur.png ; tour des 54 aperçus : …/scratchpad/tour_00.png à tour_04.png.
Affichage par interface : …/scratchpad/opt1.png (boutons, croix, plusieurs interfaces), /tmp/m_mask1_b140.png (« Dialogues » masquée, étiquette « Masquée »), en jeu …/scratchpad/hid1.png (Argent et Chapitre masqués, msg/YesNo/ChurchRoot déplacés, slot 1).
Panneau flottant : …/scratchpad/final_panneau.png (initial / appui long / replié / double clic, tirée du commit final), drag2.png, drag3.png.
Limite des « avant » en jeu : avec le code d'origine, boutons « Non » ou « Oui » donnent la même image en jeu sur ce slot (/tmp/m_avon_b172.png, /tmp/m_avoff_b172.png : message affiché, pas de HUD visible) ; la portée globale de l'ancienne option est donc établie par le code, pas par capture.

## Établi / Supposé / Non vérifié
- Établi (capture) : page, liste groupée, aperçus des 54 entrées, masquage par interface en éditeur et en jeu (slot 1 : Argent, Chapitre, msg, Oui/Non, ChurchRoot), gestes du panneau, migration des réglages (test script).
- Supposé : le doigt (tactile) arrive comme événements souris dans pyglet ; les libellés renommés (BCInfo = « Sauvegarde rapide » d'après les notes ; BattleIM = objets et sorts) ; un ancien réglage `YesNo` enregistré par l'ancienne version est désormais lu en relatif au message (peut décaler un peu un Oui/Non déjà réglé).
- Non vérifié : combats réels avec réglages de fenêtres de combat ; fenêtre masquée utilisée au clavier/souris en vraie partie sous Windows ; « Statut du personnage » (types 13-17 : l'aperçu ne montre que la bande du bouton retour, utilité de la déplacer seule non confirmée) ; cadence : l'éditeur tourne à ~10 i/s sous xvfb, les délais ont été testés avec les variables d'env.

## Pièges de fusion (autres agents sur pause.py / window.py)
- pause.py : constantes en tête (NOMS_FENETRES réécrit, GROUPES_INTERFACE, ENTETE, SANS_EDITION, DELAI_*), `__init__` (6 attributs pan_*/cadre_liste), `_choix`/`_bouger_liste`/`_dessiner_liste`/`_fin_liste` (intertitres), `_e_interface` + `cibles`/`_visible`/`_poser_visible`, `dessiner` (placement du panneau et cadre soulevé), `clic`/`relache`/`glisser`/`maj`. Si un autre agent ajoute une page ou modifie `clic`/`glisser`/`maj`, garder le test `pan_appui` en premier dans `glisser`.
- window.py : `_dessiner_menus` (boucle d'overrides, type 1 relatif, filtres `masque`), `_zones` (renvoie [] si masquée), `apercu_interface` (refactorisé en `_fenetre_apercu`).
- settings.py : DEFAUT (+`interface_masquees`) et boucle de nettoyage dans `Reglages.__init__`.
- Footer de commit : le brief donne `Claude-Session: …session_014GF7TVESqzjb1SFv4HoPvZ`, mais l'attribution fournie par l'environnement de ce tour donne `…session_014GF7TUJhoy5Df7FLvSTYtw` ; j'ai utilisé la seconde (à réécrire si vous préférez l'identifiant du brief).

## Notes pour la doc
- Nouvelle clé `interface_masquees` (noms de fenêtres Make_* ou `msg` ; boutons/croix gérés par `boutons`). `FENETRES_RETIREES` dans settings.py ; purge au chargement.
- Gestes du panneau « Interface » (appui long = déplacer, court = replier, double clic = remettre) ; position non persistante ; `DQ_APPUI_LONG`, `DQ_DOUBLE_CLIC`.
- Harnais de test des gestes : `!x!y` (appui), `^x^y` (glisser), `~@x@y` (déplacement), `@x@y` (clic) ; touche tenue = `+TOUCHE` / `-TOUCHE` (un RETURN/DOWN de plusieurs images déclenche la répétition à 0,4 s). Le harnais réécrit le fichier `--reglages` : toujours en passer une copie.
- Oui/Non relatif au message ; fenêtre masquée = mise en page conservée, ni dessinée ni cliquable ; « Rétablir toutes » réaffiche tout.

---

## Agent ac00a9e82be6ce2bf — 01/11 21:53

RAPPORT agent-texteson (worktree /home/claude/wt-texteson, branche agent-texteson, partie de main 1e87ca6). Rien poussé, aucune bascule de branche, /home/claude/dq4-portage non touché, saves en lecture seule (tests dans /tmp/sv_*), APK/*.mpt/docs/ non touchés, moteur .so non modifié.

COMMITS (pied de page à deux lignes, pyflakes OK : seuls restent les avertissements déjà présents sur main) :
- f101cc5 Moteur : vitesse du texte + défilement des combats (crochets) + tools/test_texte_defilement.py
- 711593a Son : catégories, volumes, interrupteurs, écoute pendant la pause + tools/test_son_mixage.py
- 8f1197a Menu Echap : page Son par catégories, page « Texte et défilement » + settings.py + tools/test_reglages_son_texte.py

POINT 1 : TEXTE / DÉFILEMENT — FAIT
Décision : mixte. Texte = côté visionneuse (crochet sur le moteur) ; défilement des combats = écriture de la valeur dans la config du moteur (g_Option+5).
- Page « Texte et défilement » (ajoutée au menu racine, une ligne) : Vitesse du texte (7 crans : Très lent, Lent, Assez lent, Normal (jeu), Rapide, Très rapide, Instantané) ; section Combats : « Défilement automatique » (interrupteur), « Vitesse de défilement » (crans 1 à 4, grisé si auto coupé), « Rétablir le réglage du jeu ». Défauts = comportement d'avant (rien n'est imposé tant qu'on ne touche pas).
- Le libellé et l'aide disent « Combats seulement ».
ÉTABLI (lu dans le code + mesuré) :
- Le texte des dialogues s'écrit à `vitesse x 4` lettres par image moteur (30 Hz), vitesse = constante par type de fenêtre (1 dialogues, 100 fenêtres de combat). Ce n'est PAS une option du jeu. Le crochet remplace ce nombre ; à 4 il ne fait rien.
- La seule option du jeu qui défile est OptionStatus.battleSpeed (g_Option+5, enregistrée dans chaque sauvegarde), lue par BattleAutoFeed : 0 à 3 = attente 12/22/32/42 images, 4 = à la main. Dialogues hors combat : jamais automatiques (400 images d'attente avec le code 0 ou 2, mesuré).
- Mesures (images moteur, ouverture du message -> fin de page, 72 lettres) : 0,5 -> 140 ; 1 -> 73 ; 2 -> 40 ; 4 (défaut) -> 24 ; 8 -> 15 ; 16 -> 11 ; instantané -> 8. Moteur de main sans mon crochet : 24 aussi (défaut identique). Attentes de combat : 12/22/32/42 pour les codes 0/1/2/3 (les autres épisodes = +5 ou +6) ; code 4 : aucun passage seul, le message attend A (testé).
- Via le menu Echap dans la visionneuse (DQ_MSGDBG=1) : Lent -> 74 images, Rapide -> 16, Instantané -> 9, défaut 25. Le menu change bien g_Option+5 (4 -> 1 ; slot 1 : 0 -> 4 via interrupteur), et un clic dans la fenêtre Paramètres du jeu (cran 5 -> Confirmer) alors que le défilement est imposé est adopté par le réglage (g_Option = 4, imposé = 4).
- La fenêtre Divers > Paramètres du jeu s'appelle : Menu Pause, Volume musique, Volume effets, « Vitesse texte » (5 crans 1..5, « Rapide » en haut, « Lent » en bas), Taille de la croix, Retour à l'écran titre. Son « Vitesse texte » = vitesse des messages de COMBAT ; cran 5 = code 4 = à la main (observé).
- Valeurs des sauvegardes de Sylfried : vitesse de combat 0, 2, 2, 4, 2 pour les slots 1..5 ; volumes 4/4 partout ; partie neuve : 2.
SUPPOSÉ : durées en secondes (0,4/0,7/1,1/1,4 s) = images / 30 ; noms des crans de texte (« Normal (jeu) » = 120 lettres/s) choisis par moi.
NON VÉRIFIÉ : ressenti en jeu réel sur PC Windows ; vitesse imposée écrite dans la sauvegarde que le jeu enregistre (la valeur imposée y est stockée ; « Rétablir » rend la valeur du jeu en mémoire, la sauvegarde déjà écrite reste telle quelle).

POINT 2 : SON — FAIT
Page Son refaite (même motif : interrupteurs, curseurs 0-100 %, cadre jaune selon périphérique) : Général (Son + Volume général), Musique, Jingles et fanfares, Bruitages, Interface (interrupteur + volume chacun). Appliqué immédiatement aux sons en cours (musique, jingle, bruitages déjà lancés). Musique coupée = elle tourne en silence et reprend au bon endroit ; bruitage court coupé = non joué ; bruitage en boucle coupé = lancé à volume nul. Sur la page Son les sons reprennent (jeu arrêté) pour entendre les réglages + bruitage d'essai (SE 316 pour bruitages, 300 pour interface) quand on bouge un volume.
Catégories (établies par scan des appels playSe/playBgm et durée/boucle des AKB) : musique (PlayBGM en boucle) ; jingles/fanfares (PlayBGM sans boucle court <= 30 s, ou demandé avec reprise 0x1000|n) ; bruitages (PlaySE) ; interface = SE 300 à 304 (300 = bouton Unity + bip de page de message, 301, 304 établis ; 302/303 SUPPOSÉS interface). Pas de voix ni de canal « ME » séparé dans Unity (seulement PlayBGM/PlaySE) : aucune catégorie inventée.
Bonus : les options volume musique/effets de la fenêtre Paramètres du jeu étaient IGNORÉES par la visionneuse ; elles s'appliquent maintenant ((indice+1) x 0,2, comme Unity) — par défaut 4 donc x1 : aucun changement tant qu'on n'y touche pas. La conversion exacte est déduite du code Unity (non entendue).
NON VÉRIFIÉ : écoute réelle (tests en PYGLET_AUDIO=silent) ; contenu exact des « jingles » à l'oreille ; pas d'essai sonore pour le volume des jingles (le volume joue à la prochaine fanfare).

TESTS FOURNIS
- tools/test_texte_defilement.py --apk <APK> --saves <saves> [--slot 4] : 4 tests (frames de texte, attentes de combat, manuel, hors combat), ~45 s, OK.
- tools/test_son_mixage.py : 12 tests unitaires (gain, catégories, volumes immédiats, interrupteurs, boucles, jingle/reprise, écoute en pause), OK.
- tools/test_reglages_son_texte.py : 4 tests (ancien reglages.json, valeurs absurdes, crans, aller-retour), OK.
Captures (copies stables dans /tmp/ts_caps/) : son_defaut.png, son_modifie.png, texte_slot4_manuel.png, texte_slot1_auto_tres_rapide.png, texte_impose_rapide.png, jeu_parametres.png, jeu_parametres_vitesse_texte.png. Scripts de mesure : /tmp/ts_work/ (run_texte.sh, run_defil.sh). Infobulles non capturées (le survol simulé ne les montre pas en test).

FICHIERS TOUCHÉS : dq4_pc/sound.py, settings.py, pause.py, window.py, engine.py ; nouveaux : tools/test_*.py (3). Hors liste initiale : engine.py et window.py (localisés, autorisés), dossier tools/ (nouveaux fichiers de test). Aucune touche à Commandes, États, titre/avant-partie, éditeur d'interface, affichage.

PIÈGES DE FUSION
- pause.py : ligne « Texte et défilement » ajoutée juste après la ligne Son de _e_racine (voisine de Commandes) ; `titres['texte']` ajouté sur une ligne propre avant `avec_mini = ...` ; règle de largeur `if ecr in ('texte',)` ajoutée juste avant la ligne `if ecr == 'commandes': pw = ...` ; `_aide_ligne` : lignes curs/choix modifiées (préfixe `en['aide']`) à côté de la ligne 'touche' ; `Pause.maj` : 4 lignes au début ; `noms[...]` ajoutés après le dict ; `_e_son` entièrement réécrite.
- settings.py : nouvelles clés en lignes séparées après la ligne 'son' ; `BORNES.update(...)` séparé, mais la boucle BORNES de chargement a été modifiée (exclusion des booléens) + 4 lignes de validation juste après.
- window.py : ligne d'init après `self.son.precharger`, méthodes après `regler_vol_bruitages`, 3 lignes après `self.son.tick()`, constante SE_APERCU avant SE_COURANTS.
- engine.py : `_crochets_texte()` appelé après le crochet `_sca` dans __init__, crochet `_sv` (msg_visible) modifié, 2 lignes dans step().

NOTES DOC (pour docs/, non écrites) : décrire la page Texte et défilement, les 4 catégories de son et leurs critères, les nouvelles clés de reglages.json, le fait que « Vitesse texte » du jeu = messages de combat seulement, les options volume du jeu désormais prises en compte, et les 3 scripts tools/test_*.py.

À RETENIR (mémoire, vu dans cette session) : sauvegardes de Sylfried : vitesse de combat 0,2,2,4,2 (slots 1-5), volumes du jeu 4/4 ; ses retours : option vitesse du texte + défilement (combats), options de son par catégorie.

---

## Agent a194067a522b77b40 — 01/11 22:08

RAPPORT agent-affichage (worktree /home/claude/wt-affichage, branche agent-affichage, base main 1e87ca6). Arbre propre, rien poussé.

COMMITS (5, tous avec le pied de page à deux lignes)
- f46a3b7 Plein écran effectif dès l'ouverture de la fenêtre (logos compris)
- e27ee24 Anticrénelage MSAA hors écran (postfx.py), alpha-to-coverage, suréchantillonnage, netteté, luminosité
- c5c6983 Décors à plat superposés : fin du scintillement par z-fighting (fleurs, chemins)
- 6a5730e Shaders : retrait de « Régions lissées » et « Bicubique » ; le lissage s'applique aussi aux sprites
- 16042b9 postfx : fenêtre réduite (zone de dessin nulle) n'est plus prise pour une panne

FICHIERS TOUCHÉS (tous dans mon périmètre)
- Nouveaux : dq4_pc/postfx.py, dq4_pc/decors_plats.py
- Modifiés : dq4_pc/fenetre.py, dq4_pc/hd.py, dq4_pc/reglages.py
- dq4_pc/pause.py : seulement `_e_affichage` et le dictionnaire `noms` (Shader, Suréchantillonnage). Aucune autre page.
- pyflakes : seuls restent les avertissements déjà présents sur main (`sel` dans window.py ; `H`, `R`, `yp`, `mh` dans pause.py).

1. PLEIN ÉCRAN DÈS LE LANCEMENT : fait, vérifié sous xvfb avec le code final.
- La fenêtre est créée directement en plein écran (`fullscreen=True`, résolution du bureau), logos compris, sans passage par la fenêtre. Si ça échoue, le jeu retombe en fenêtre et le dit dans le journal. Option `--plein-ecran`.
- Journal sous xvfb 1920x1080 (/tmp/out_pe2.txt) :
  - création : PLEIN ÉCRAN 1920x1080
  - 1re image des logos : PLEIN ÉCRAN 1920x1080
  - 1re image du jeu : PLEIN ÉCRAN 1920x1080
  - rendu hors écran 1920x1080 avec anticrénelage x4
  - captures 1920x1080.
- Bascule à chaud testée (/tmp/out_fs.txt) : Plein écran = oui donne 3840x2160 (capture 3840x2160), puis = non redonne 1280x720.
- Je ne peux pas vérifier sous xvfb, donc à tester sur son PC Windows : l'absence totale de flash ou de fenêtre intermédiaire à l'ouverture, le comportement Windows (WS_POPUP), et le retour en fenêtre à la bonne taille.

2. EFFETS D'AFFICHAGE : ajoutés seulement ceux qui sont utiles et vérifiés.
Ajouts, dans la page Affichage :
- Anticrénelage MSAA réécrit : la scène est dessinée hors écran puis recopiée. Il s'applique à chaud (avant : « au prochain lancement », et la config de fenêtre échouait en silence) et se limite à GL_MAX_SAMPLES. Une note rouge s'affiche si la carte ne peut pas : « Limité à x4 par cette carte graphique ». Capture : /tmp/m_mn1_b70.png.
- Suréchantillonnage : Aucun / x1,5 / x2.
- Netteté : curseur 0 à 100 %, accentuation adaptative sans halo (type CAS).
- Luminosité : curseur 50 à 150 %, courbe de gamma.
- Sans réglage actif, le dessin direct d'avant est conservé. Toute erreur GL retombe sur le dessin direct et est journalisée.
Idées rejetées, avec la raison :
- FXAA/SMAA : floutent le pixel art et les textes, alors que le MSAA et le suréchantillonnage font mieux. C'est exactement ce que l'utilisateur reproche à certains shaders.
- Scanlines/CRT : effet artificiel, étranger au rendu HD du jeu, et il dégraderait la lisibilité.
- Contraste et saturation : intérêt faible, Luminosité suffit.
- Mise à l'échelle entière : le jeu est en 3D à échelle libre ; le mode Pixel perfect gère déjà l'échelle entière sur la carte du monde.
- vsync : déjà actif (vsync=True), un interrupteur n'apporterait rien.
- Limiteur de FPS : le moteur tourne à pas fixe de 30 Hz avec interpolation, et le vsync borne l'affichage. Non mesurable sous xvfb de toute façon.
- Anisotrope : déjà appliqué (min(8, max carte)) sur les textures de décor. Sous xvfb je ne peux pas le mesurer ; le rapport d'anisotropie est faible (environ 1,3:1) avec cette caméra.
- Bloom/HDR : étrangers à l'original, pas pertinents.

3. AUDIT « OPTION PAR OPTION » (code + captures A/B, église slot 1, image 50 ; mesures par le script /tmp/aff/cmp.py)
- Plein écran : MARCHE. Création et bascule à chaud vérifiées (voir point 1). Pas de capture, journal seulement.
- Résolution : MARCHE en fenêtre (1280x720 puis [1600,900] : la capture passe à 1600x900, /tmp/m_rs_b20.png). En plein écran, le choix tente de changer le mode vidéo : NON VÉRIFIÉ, xvfb n'a qu'un mode. Limite connue, non corrigée : au lancement en plein écran le jeu prend la résolution du bureau, le réglage `resolution` ne s'y applique pas (comme avant, ce n'était déjà pas le cas).
- Shader : MARCHE (3 rendus nets et distincts, /tmp/aff/sh_cmp.png).
  - Aucun : pixels d'origine, frontières adoucies d'un pixel d'écran.
  - EPX x8 : contours arrondis, nets.
  - Pixel perfect : plus proche voisin strict.
  - Régions lissées et Bicubique : RETIRÉS. Un ancien reglages.json avec 2 ou 3 est lu comme 1 (EPX x8). Le numéro 4 (pixel perfect) ne change pas et `--hd 4` reste valable.
  - Mesures de netteté (captures /tmp/m_t1_b40..120.png et /tmp/aff/t1_modes2.png). Laplacien moyen sur le héros et le décor : Aucun 20,7 ; EPX 22,6 ; Régions 21,9 ; Bicubique 16,6 ; Pixel perfect 20,7. Gradient p99 : Bicubique 60 contre 73 pour EPX.
  - Bicubique est donc nettement flou (-27 %).
  - Régions lissées a la même netteté mesurée qu'EPX, mais elle empâte les détails fins (yeux, doigts) et retombe sur le bicubique dès qu'une feuille dépasse 40 couleurs. C'est un choix de jugement : le code est dans l'historique, à restaurer facilement si l'utilisateur la regrette.
  - Pas de nouveau filtre de netteté en mode Shader : la vraie netteté est l'option Netteté.
- Lissage des textures : n'agissait QUE sur le décor et la carte du monde, pas sur héros, PNJ, monstres ni bulles. CORRIGÉ : c'est maintenant cohérent partout, y compris sur les textures EPX (plus proche voisin quand il est coupé). Captures /tmp/aff/li_cmp.png (écart > 8 sur 22 895 pixels pour Aucun, 17 989 pour EPX).
- Distance caméra : MARCHE (50, 100, 200 % : /tmp/aff/d_cmp.png).
- Centrer la caméra sur le joueur : MARCHE (grotte, slot 5, image 80). Oui : héros centré, bord de carte noir à droite. Non : la caméra reste bornée à la carte. /tmp/aff/cc_cmp.png.
- Effet de vignetage : MARCHE (0, 30 et 100 % en extérieur : luminosité moyenne 93,4 → 83,7 → 60,8). Sur l'église (petite scène entourée de noir), l'effet est presque invisible, ce qui est normal. /tmp/aff/vg_cmp.png.
- Anticrénelage : CORRIGÉ (voir point 2). Sous xvfb x4 et x8 donnent le même rendu (max 4 d'après llvmpipe : « x4 (demandé x8) »). Sur sa carte réelle le x8 n'est pas testé. Gradient de scène 1,908 → 1,889.
- Suréchantillonnage : NOUVEAU, MARCHE (x1,5 : 1920x1080 hors écran ; x2 : 2560x1440). Non mesuré en performance sur GPU réel.
- Netteté : NOUVEAU, MARCHE. Gradient mesuré sur le héros : 13,7 → 17,8 (50 %) → 20,7 (100 %), sans halo visible. /tmp/aff/ne_cmp.png.
- Luminosité : NOUVEAU, MARCHE (moyenne 12,4 à 70 %, 16,5 à 100 %, 19,7 à 130 %). /tmp/aff/lu_cmp.png.
- Régressions vérifiées avec le rendu hors écran : carte du monde (/tmp/aff/mp_cmp.png), combat (/tmp/aff/cb_cmp.png), menu Échap par-dessus la scène (/tmp/m_mn_b40.png), logos et plein écran, chemin par défaut `--msaa 4`.

4. SCINTILLEMENT DES FLEURS (capture 6) : reproduit, deux causes, corrigées.
- (A) z-fighting. Les massifs de fleurs sont des décors plats à découpe (textures 12862 et 14697 à y = -0,125) qui se superposent à d'autres décors plats et entre eux : même profondeur, donc le test de profondeur choisit l'un ou l'autre pixel par pixel, et ça change à chaque mouvement de caméra. Corrigé par :
  - un décalage de profondeur croissant d'un groupe de textures au suivant dans `_tracer_decor` ;
  - `decors_plats.decaler`, qui relève de 3 mm les triangles plats superposés (30 à 130 ms par carte, cache de carte intact, désactivable par DQ_SANS_DECALAGE).
- (B) bords de découpe au test alpha, que le MSAA de fenêtre ne lissait jamais. Corrigé par l'alpha-to-coverage dans le rendu MSAA hors écran (actif par défaut, msaa = 4), plus le suréchantillonnage en option.
- Mesures sous xvfb (maout, /tmp/aff/) :
  - Z-fight, caméra fixe, plan lointain variable (pixels instables dans la zone fleurs/mare) : 110 → 61 (décalage de profondeur) → 40 (relèvement 3 mm). Le reste correspond aux reflets animés de l'eau, pas à du z-fighting.
  - Caméra en glissement (0,01 en z par image), excès de variation temporelle dans la zone des fleurs, par rapport à une référence supersamplée x2 :
    - base : 1,149 ;
    - relèvement seul : 1,142 (donc la cause B domine) ;
    - MSAA 4 + alpha-to-coverage : 0,258 (-78 %).
  - Global : J 2,03 → 1,64 ; rapport d2/d1 0,541 → 0,465.
  - Mesures antérieures : le MSAA 4 SANS alpha-to-coverage ne donne aucun gain (J zone 4,97 contre 4,92). Le suréchantillonnage x2 seul réduit J global de 2,03 à 0,79.
- Limite honnête : avec Anticrénelage = Aucun et Suréchantillonnage = Aucun, seul le z-fighting est corrigé ; le chatoiement des bords de fleurs reste. Avec les réglages par défaut (msaa 4) il est fortement réduit mais pas supprimé (0,258 résiduel). Pas vérifié sur son GPU.
- Captures : /tmp/m_ga_b40..50.png (avant), /tmp/m_gb_b40..50.png (relèvement seul), /tmp/m_gc_b40..50.png (relèvement + MSAA 4 + alpha-to-coverage), référence /tmp/m_gr_b40..50.png (2560x1440), cartes de scintillement /tmp/m_ga_J.png et /tmp/m_gc_J.png, z-fight /tmp/m_zd4_b40..44.png (après) et /tmp/m_zd5_b40..44.png (relèvement coupé) avec /tmp/aff/zd45_overlay.png et /tmp/aff/zd45_roi.png.

ÉTABLI / SUPPOSÉ / NON VÉRIFIÉ
- Établi (mesuré ou capturé sous xvfb/llvmpipe) : tout ce qui précède, sauf indication contraire.
- Supposé : le rendu hors écran MSAA et l'alpha-to-coverage fonctionnent sur GPU réels Windows (Intel/NVIDIA/AMD) comme sous Mesa. Les tampons sont standard GL 3.3.
- Non vérifié : l'absence de flash au lancement en plein écran sur Windows ; x8 sur sa carte ; le changement de mode vidéo en plein écran via Résolution ; les performances sur GPU réel (4K, suréchantillonnage x2, MSAA x8) ; l'aspect final de l'anisotropie.

PIÈGES DE FUSION
Zones de window.py que d'autres agents peuvent aussi toucher :
- création de la fenêtre dans `Jeu.__init__` (config sans MSAA, `self.post = PF.PostFX(...)` ; `self.msaa` supprimé) ;
- `_dessiner_scene` : `glViewport(0, 0, *self.post.debut(fond))` au début, `self.post.fin()` entre `_dessiner_fondu(True)` et `_dessiner_degats(e)` ;
- `_tracer_decor` (boucle polygon offset et alpha-to-coverage) ;
- `_charger_carte` (appel de `DP.decaler`) ;
- `main()` : argument `--options-test`, `else: reg['msaa'] = a.msaa`, `a.hd` validé par `RG.mode_sprites_valide`.
- Dans pause.py : seulement `_e_affichage` et les clés Shader / Suréchantillonnage du dictionnaire `noms`.
- Dans settings.py : nouvelles clés dans DEFAUT et BORNES, la fonction `mode_sprites_valide` et les constantes MODES_SPRITES / MSAA_VALEURS avant BORNES, deux lignes de validation ajoutées juste après la ligne des BORNES dans `Reglages.__init__`.
- MODE_PP vaut désormais 4 en dur (avant : `len(HD.MODES)`), et `HD.MODES` ne contient plus que 2 entrées. Si un autre agent écrit du code qui indexe `HD.MODES` avec une valeur de `mode_sprites`, il doit rester sur 0 ou 1.

OUTILS DE TEST AJOUTÉS (window.py)
- `--options-test "image:Libellé=valeur;..."` (valeur en JSON ; applique une option de la page Affichage par les fonctions du menu).
- Variables d'environnement : DQ_ZDEBUG, DQ_CARTE_DEPL, DQ_SANS_DECALAGE, DQ_SANS_A2C, DQ_ATTENDRE_HD.
- Scripts de test hors dépôt dans /tmp/aff/ : run.sh, cmp.py, jit.py, flick.py, batch_ab.sh.

NOTES POUR docs/ (à intégrer par le parent)
- postfx.py : cadre hors écran = renderbuffers MSAA couleur et profondeur 24 bits, résolution vers texture, passe finale (réduction bilinéaire, netteté type CAS, gamma). Contournement total quand msaa = 0, échelle ≤ 1, netteté = 0, luminosité = 1. Fallback direct sur toute erreur.
- Alpha-to-coverage : `GL_SAMPLE_ALPHA_TO_COVERAGE` (0x809E) activé pour la passe de décor opaque découpé avec le blending désactivé ; l'alpha est lissé par fwidth dans FRAG (uniform `a2c`) ; la passe transparente reste en alpha-test classique.
- flat_sceneries.py : détection des triangles plats superposés par bbox + SAT, relèvement de 3 mm par niveau d'empilement, ordre de dessin conservé.
- Réglages : `echelle_rendu` 1 à 2, `nettete` 0 à 1, `luminosite` 0,5 à 1,5, `mode_sprites` valide parmi 0, 1, 4 (2 et 3 migrés vers 1), `msaa` parmi 0, 2, 4, 8.

FAITS DURABLES UTILES POUR LA MÉMOIRE (source : cette session)
- Sous xvfb/llvmpipe, GL_MAX_SAMPLES = 4 et aucune config MSAA de fenêtre n'est disponible. Le MSAA ne se teste donc que par FBO.
- Un run xvfb d'une vingtaine de secondes à plusieurs minutes selon le verrou /tmp/xvfb.lock que partagent les autres agents.
- Le scintillement des fleurs a deux causes distinctes ; le MSAA seul ne suffit pas, il faut l'alpha-to-coverage pour le décor découpé.
- Les anciennes valeurs mode_sprites 2 et 3 n'existent plus.

---
