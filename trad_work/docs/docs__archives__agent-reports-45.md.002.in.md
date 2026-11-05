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
