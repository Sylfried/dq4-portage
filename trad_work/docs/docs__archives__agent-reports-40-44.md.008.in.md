## Notes pour `docs/` (section « Retours de 23 h 24 (#42) », je n'ai pas écrit dans docs/)
- `bornes_x` n'est plus appliquée en caméra menée par le jeu ; critère `cam_jeu` = verrou +0x3e ET (mode +0x48 dans 1..5, ou déplacement +0x43, ou cible à plus de 1 u du héros). Mode 6 ou verrou sur le héros = régime joueur inchangé.
- Unity ne borne pas la caméra : `GetEventLimitedPos` CD4EE4 ne sert qu'au décor `map/ev/ev02/out/ev02` (z >= -19,5, `IsLargeAspectRatio`).
- Centrage : correction rigide + reste exponentiel (14/s, temps réel) seulement aux changements de régime ou coupures.
- Aspect : `SetViewAndCenterY` D1F5D0 garde 9:16 quel que soit l'écran ; champ horizontal 12,67°, vertical 22,3°. Équivalence numérique avec le pipeline Unity : 4e-15.
- Route du prologue jusqu'à la grenouille : sauvegarde du dossier ANCIEN `.../DQ4/saves/20261007_190735` slot 2 (`mlb1a`). Dans le dossier NOUVEAU `dq4-portage/dq4_pc/sauvegardes`, le slot 2 charge `caf1`.
- Outil de test fenêtré : banc à horloge virtuelle `/tmp/banc_camera.py`. Usage : `python3 banc_camera.py WT ETATDIR NOM "frame:+Q,..." "captures" NFRAMES [DT]` ; environnement `AUTO_A`, `AUTO_0`, `AUTO_ALL`, `RG`. Génération d'états de la route du prologue : `/tmp/gen_etat_camera.py NOM IMAGE`. États prêts : `/tmp/camst/sv_frog_pre1272/etats/etat_01.dqs` et `/tmp/camst/sv_house470`, `sv_house900`.
- Piège de test : `/tmp/rg.json` est réécrit par chaque fermeture de fenêtre ; il contient `angle_camera` = -2,25 (résidu). Pour une mesure propre, utiliser une copie (`RG=...`) ou `/tmp/rg_defaut.json`.

## Pour la mémoire (pas écrit par moi)
- Environnement : `pkill -f` sur un nom présent dans la ligne de commande de son propre shell tue ce shell (code 144). Un `flock` en attente peut rester orphelin après un kill.
- Slot 2 du dossier de sauvegardes NOUVEAU = `caf1` ; prologue dans le dossier ancien.
- Le Screen 6 de l'utilisateur est la maison du héros (père assis à une table), `mlb1a`.

---

## Agent a0a930f3486ff24a2 — 02/11 00:52

RAPPORT agent « titre » (PR #42) — worktree /home/claude/wt-titre, branche agent-titre, base 345ba8f. Arbre propre. Aucun push, aucune modif de docs/, du patch FR ni des sauvegardes.

COMMITS (pied de message conforme)
- 60aa233 « Titre : le dragon de l'ecran d'accueil (FbxObject c1018, paquets 31 et 32) » (point 5)
- b76d293 « Titre : textes des credits centres comme le logo » (point 8, window.py seul)
pyflakes : seuls les avertissements connus (struct, sel).

POINT 8 — CREDITS CENTRES : FAIT ET MESURE
- Cause : toute la scene ev01 est relevee de TITRE_HAUT = 0,3 pour centrer logo + ile ; les credits (modele de maillage 8905, dessines par les paquets 21/22 comme le logo) suivaient ce decalage alors que le moteur les pose bas dans l'image d'origine. Avant : centre du bloc a 0,355 (page Horii, 3 lignes) et 0,378 (pages a 2 lignes) de la hauteur.
- Correction (_decalage_credits, appelee depuis _maillages_combat) : pour chaque page, le centre vertical de l'ENCRE (pixels alpha > 32 de chaque ligne, lus dans la texture d'origine) est ramene a l'ordonnee d'ecran 0 par un deplacement le long du haut de la camera. La profondeur ne change pas, donc c'est exact a tout format. Cache par page. Toute erreur : aucun decalage (message unique dans la console).
- Mesures (diff capture avec / sans credits via DQ_SANS_CREDITS) : centre du bloc a 0,5000 a 0,5007 de la hauteur partout : 1280x720 (4 pages : Horii 100, Toriyama 240, Sugiyama 370, Majima 520), 1920x1080 et 2560x1080 (21:9) et 1024x768 (4:3) (pages 100 et 240). Centre horizontal 0,499 a 0,501.
- Verifie : « Touchez l'ecran » et copyright : 0 pixel different avant / apres (image 900) ; ciel, logo, ile inchanges (le seul ecart est le dragon).
- Choix : centrage exact par page (conforme a la consigne). Consequence : le nom reste a hauteur fixe dans le moteur d'origine, ici il monte de 4 px (page Horii) a 18 px (pages a 2 lignes) selon la page, a 720p. Sinon, annuler seulement TITRE_HAUT pour les credits donnerait -0,011 / -0,049 en ordonnee normalisee (pages a 2 lignes a ~18 px sous le centre).
- Observation : une fois centres, « YUJI HORII » et le haut de l'ile se frolent (le texte reste au-dessus de l'ile, sans chevauchement visible).
- Essais : DQ_SANS_CREDITS=1 (sans credits), DQ_CREDITS_ORIGINE=1 (ancien comportement).

POINT 5 — DRAGON : FAIT (a valider a l'oeil par Sylfried)
Etabli (lu dans le moteur / les donnees) :
- Le moteur envoie au debut de ev01 le paquet 31 (cmd_fbx_load : emplacement 0, modele 1018 = Resources « fbx/c1018 », FbxObject) puis des paquets 32 (cmd_fbx : bits 8-9 visibilite, 0x400 forcer l'animation, 0x800 echelle x3, 0x1000 couleur x4, 0x2000 position x3, 0x4000 rotation x3 en degres, 0x8000 numero de sequence). Decode depuis le desassemblage (RVA 0xD13508 / 0xD136A0, FbxObject 0xCD1528...) et confirme par le journal de paquets. Le dragon est cree cache, rotation (0,180,0).
- Modele : 566 sommets, 692 triangles, 31 os, un os par sommet, texture 256x256, 3 clips : « Take 001 » 21,98 s (Once, = les 659 images que le moteur attend), « Take 002 » 2,18 s (Loop, vol stationnaire), « Take 003 » 26,78 s. Nom du clip = « Take %03d » (sequence + 1).
- Shader Custom/ImdChara (lu dans le paquet de donnees) : sans lumiere, couleur sommet x _Color x texture, fusion alpha, ZWrite, ZTest LEqual, Cull Back, file Geometry. Donc le dragon passe DERRIERE le logo et les credits (file 3850, ZTest Always). Backface culling active par defaut (sans lui, des faces internes cachaient le visage : planche dragon_cull_sans_vs_back_660.png).
- Animation reproduite comme Unity Animation : Play / PlayQueued / CrossFade 0,3 s si la boucle precedente, Hermite d'AnimationCurve, temps en images du moteur a 30 Hz (fraction de pas comprise). Skinnage numpy : ~2 ms par image.
- Phases observees : le dragon apparait en haut vers l'image 510-520, plonge a gauche vers 600, se pose en vol stationnaire au-dessus du logo vers 660 (le logo apparait a ~640), puis boucle d'ailes jusqu'a l'appui sur « Touchez l'ecran » ; il disparait dans le menu (apres l'appui, image 925).
- Cache : fbx1_c1018.pkl (1,5 Mo, ~4,7 s a extraire) ajoute a Donnees._elements / preparer (preparation de fond). Teste sans cache : lecture a la demande dans un fil de fond, le dragon apparait, pickle ecrit (cache jetable, supprime).
Suppose (a valider) :
- Placement vertical : TITRE_DRAGON_HAUT = 0,0 (constante dans window.py, essai par DQ_FBX_DY) : le dragon garde le cadrage d'origine, il n'est PAS releve avec le groupe logo + ile. Releve de 0,3 il sortirait de l'ecran (seules les griffes visibles). Avec 0,0 : visible au-dessus du logo, tete et ailes coupees par le bord haut en vol stationnaire, griffes qui effleurent le haut du logo (le logo est devant). Le cadrage d'origine coupe aussi le dragon en haut dans la camera de la visionneuse (meme champ vertical que le mobile), mais je n'ai pas de capture d'un vrai telephone. Pour le garder entier : augmenter TITRE_DRAGON_HAUT ou reduire l'echelle (a decider par Sylfried).
Non verifie :
- GPU Windows reel (tout teste sous xvfb / Mesa). Rendu du dragon sur un vrai telephone. Le flash d'1 image en pose de repos a l'image 2. Les autres modeles fbx du jeu (ValueError propre et ignore si shader different, plusieurs maillages skinnes, MeshRenderer, animation comprimee). Le retour moteur de fin d'animation (m_anim_list, ID_ANIM_END) n'est PAS implemente : le moteur du titre n'attend pas dessus, mais une autre scene pourrait. Les modeles fbx ne sont dessines que dans les scenes de ville (branche ville de _dessiner_scene), pas en combat ni sur la carte du monde. Pas de test sur un vrai profil utilisateur avec cache deja prepare (seulement le cas cache sans le fichier fbx).

FICHIERS ET LIGNES TOUCHEES (hors perimetre strict, a surveiller a la fusion)
- dq4_pc/fbx.py : NOUVEAU (156 lignes).
- dq4_pc/donnees.py : +66 lignes l.304-369 (modele_fbx, _extraire_fbx) ; +1 ligne l.394 (_elements) ; +1 ligne l.435 (preparer).
- dq4_pc/moteur.py : Etat.__init__ l.87 (self.fbx / self.image) ; __setstate__ l.93 (setdefault) ; l.101 (paquet 0 : ajout de self.fbx.clear() au bout d'une longue ligne : conflit probable si un autre agent ajoute des remises a zero camera ici) ; branches t == 31 / 32 l.154-165 ; Moteur.step l.604 (self.etat.image = self.images avant appliquer). Etats enregistres anciens : compatibles (setdefault).
- dq4_pc/fenetre.py : import fbx l.26 ; __init__ l.211 (fbx_cache / fbx_lect) ; _maillages_combat l.1003-1004 et l.1013 (credits) ; gros bloc neuf l.1141-1234 entre _tracer_decor et _fond_combat (TITRE_DRAGON_HAUT, _fbx_pret, _tracer_fbx, _decalage_credits) ; _dessiner_scene, branche ville l.2644-2645 (« self._tracer_decor(True); self._M_ville = M » + « if e.fbx: self._tracer_fbx(e) »). _camera_ville et la ligne TITRE_HAUT (l.97 / 883) NON touchees. Aucun changement a la forme du tuple renvoye par _maillages_combat.

PIEGES POUR LA FUSION
- L'agent camera modifie _camera_ville et probablement la ligne « M, cam3d = self._camera_ville(e, aspect) » : mon crochet est sur la ligne suivante de la branche ville (« self._tracer_decor(True) »). _decalage_credits lit self._M_ville (= la matrice finale M avec le decalage TITRE_HAUT) : si la camera change la facon dont M est construit ou renomme M, adapter cette seule ligne. L'agent sprites peut toucher _dessiner_scene / _maillages_combat : mes 3 lignes credits y sont isolees.
- La ligne du paquet 0 de Etat.appliquer (engine.py l.101) est la plus fragile (une seule ligne tres longue).
- Le cache de preparation inclut maintenant un element « fbx » : au premier lancement avec l'ancien cache, la preparation de fond reprend pour cet element seul (~5 s).

NOTES A AJOUTER DANS docs/ (je ne les ai pas ecrites)
- viewer-notes-dq4-pc.md, section « Retours de 23 h 24 (#42) — titre » : (1) Credits : centres par page sur l'encre, au milieu de la zone de dessin (mesure 0,500 a 4 formats) ; essais DQ_SANS_CREDITS / DQ_CREDITS_ORIGINE. (2) Dragon : modele fbx/c1018 anime (fbx.py), derriere le logo, TITRE_DRAGON_HAUT = 0,0 (cadrage d'origine, non releve) ; DQ_FBX_DY pour essayer, DQ_FBX_CULL=0 pour couper le culling ; phases d'apparition (510 -> 660 -> boucle -> disparition au menu). Mettre en « a valider » le placement vertical.
- technical-notes-dq4-port.md : paquets 31 (cmd_fbx_load : emplacement, modele ; < 0 = liberation) et 32 (cmd_fbx, bits ci-dessus) ; FbxObject = prefab Resources « fbx/c<no> » (SkinnedMeshRenderer + Animation legacy ; clip « Take %03d », CrossFade 0,3 s si la boucle precedente, sinon PlayQueued) ; Custom/ImdChara : Cull Back, ZTest LEqual, ZWrite, blend 5/10, file Geometry ; m_defScale 0,4 pour le modele 10 seulement ; Etat.image ; fbx1_c%04d.pkl.

CAPTURES (toutes dans /tmp/titre42/, copies nommees ; planches a ouvrir en premier)
- Credits avant / apres (1280x720, 4 pages) : /tmp/titre42/credits_avant_apres_planche.png ; pages seules credits_avant_{100,240,370,520}.png et credits_apres_{100,240,370,520}.png (« avant » = DQ_CREDITS_ORIGINE=1, ancien emplacement ; au 520 le dragon est deja la dans les deux). Etat de main sans dragon : /tmp/titre42/avant_main_*.png et avant_main_planche_20_620.png / avant_main_planche_640_1500.png.
- Formats : /tmp/titre42/credits_formats_planche.png (4:3, 21:9, 16:9 1080p) ; credits_apres_{1080,2180,768}_{100,240}.png (2180 = 2560x1080).
- Dragon par phase : /tmp/titre42/dragon_apres_planche.png (images 520, 560, 600, 640, 660, 700, 800, 900) et dragon_apres_*.png ; apres appui sur Entree (700 et 900) : dragon_entree_planche.png et dragon_entree_*.png (le 1er appui a 700 saute la sequence : ecran noir puis titre final, le 2e a 900 ouvre le menu sans dragon).
- Culling : /tmp/titre42/dragon_cull_sans_vs_back_660.png. Variante dragon releve de 0,3 (griffes seules) : /tmp/dv_0.3_{600,640,700}.png ; variante 0,0 : /tmp/dv_0.0_{600,640,700}.png.
- Outils de test (scratchpad) : mesure des credits /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/tools/measure_credits.py (usage : avec.png sans.png seuil).

DONNEES DE MEMOIRE UTILISEES : aucune ; ce rapport vient uniquement du depot, des donnees de jeu et de mes mesures.

---

## Agent a8597c32837357eeb — 02/11 01:31

RAPPORT agent « sprites » — PR #42, points 13 (bulle « ! ») et 15 (sprites aplatis aux bords)

Worktree /home/claude/wt-sprites, branche agent-sprites, base 345ba8f. Un seul commit : 299cab5, avec les deux lignes de pied (Co-Authored-By et Claude-Session). Arbre propre. Aucun push, aucun changement de branche, pause.py non touché. Les worktrees /tmp/wt-bisect-a et -b sont supprimés.

=== FAIT ===

POINT 15 — sprites penchés / aplatis aux bords gauche et droit

Cause :
- Le panneau d'un personnage de ville a ses sommets reculés vers la caméra de 0,185 (bas) et 0,65 (haut) le long de l'axe de la caméra (Chara.s_vtxDepthD / U).
- Le haut, plus proche, s'écarte donc du centre de l'image de (décalage × écart / profondeur).
- Le portrait d'origine, au champ horizontal étroit, cachait ce défaut. Le 16/9 et le 21/9 le rendent visible.
- Le visionneur garde le champ vertical du mobile, donc le défaut ne dépend ni du FOV ni de l'inclinaison.

Correctif, `Jeu._panneau_ville` dans window.py :
- Le panneau est reconstruit à l'écran : même position, même hauteur, mêmes profondeurs qu'avant.
- Taille, recouvrements et z-buffer sont donc inchangés.
- Les bords deviennent verticaux et la largeur vaut 0,74 × la hauteur à l'écran. C'est la proportion du panneau au centre, où la largeur est la moyenne du bas et du haut.
- Au centre de l'image, aucun changement.
- Le calcul passe par la caméra de la visionneuse (`cam3d` et `_cadre_vue`). Il ne suppose ni FOV ni tangage.
- Ombres et monde (carte du monde) : code inchangé.
- Autre version essayée puis abandonnée : décalage le long du rayon de vue. Elle donnait aussi 0,75 partout, mais la hauteur variait de ±10 à 20 % selon la position à l'écran. Je l'ai rejetée parce qu'elle change la taille des PNJ.

Réglage `correction_bords` :
- Dans `settings.py` : défaut True ; 0 ou False = comme avant ; une valeur entre 0 et 1 = correction partielle.
- Une valeur invalide revient au défaut.
- Option `--correction-bords 0-100` en ligne de commande, et variable `DQ_CORRECTION_BORDS=0-100`.
- Testé : CLI 0, CLI 50, réglage False dans le JSON, réglage True.

Mesures (scène : Strattbourg, slot 1, hero et PNJ marchant vers le sud, projection des 4 coins de chaque panneau). « Sur écran » = sprites dont les pieds sont dans l'image.

| Résolution | Distance | Penche max avant | w/h sur écran avant | Penche max après | w/h après |
|---|---|---|---|---|---|
| 1280×720 | 100 % | -13,1° | 0,65–0,79 | 0,0° | 0,74 |
| 1280×720 | 200 % | -20,5° | 0,66–0,91 | 0,0° | 0,73–0,74 |
| 1920×1080 | 100 % | -13,1° | 0,65–0,79 | 0,0° | 0,74 |
| 1920×1080 | 200 % | -20,5° | 0,65–0,91 | 0,0° | 0,73–0,74 |
| 2560×1080 (21:9) | 100 % | -13,1° | 0,65–0,79 | 0,0° | 0,74 |
| 2560×1080 (21:9) | 200 % | -20,5° | 0,65–0,91 | 0,0° | 0,73–0,74 |

- Les trois résolutions donnent les mêmes valeurs : le défaut dépend de la position angulaire, pas des pixels.
- Bord droit : même scène avec la caméra pivotée de 180° (`DQ_LACET`). Penche max avant +19,9°, après 0,0°.
- Hauteur à l'écran : identique avant et après (par exemple 71–79 px à 1280×720).
- Hero au centre : largeur 56,8 px contre 56,2 (bas) et 57,8 (haut) avant.
- À 50 % d'intensité, le penché est divisé par deux (-10,6°).

Non-régression :
- Écran titre (2 images) : 0 pixel de différence.
- Slots 2, 3 et 4 (dont la carte du monde, slot 4) : 0 pixel de différence.
- Combat : 6 images comparées, 0 pixel de différence (codes distincts de `_panneau_ville`).
- Grotte (slot 5) : seuls les sprites changent.
- Modes Shader 0 (originaux), 1 (EPX) et 4 (pixel perfect) : rendus corrects, penche 0,0°. Le mode 4 est le mode de toutes les mesures ci-dessus (réglage par défaut).
- Aucun code d'ancrage ne lit les sommets des panneaux : `_ancrer_effets`, Morph et dégâts sont inchangés par construction.

POINT 13 — bulle « ! » trop haute

Établi :
- Pas de régression de rendu entre #39 et #41 : 0 pixel de différence avec la caméra par défaut. Le code de la bulle n'a pas changé depuis d6d9b20, donc aucun commit fautif à isoler par bisect.
- Défaut réel : la bulle était avancée de 0,48 le long de l'axe de la caméra DU JEU (`fwd`) et non de celle de la visionneuse.
- Autre défaut : le moteur la pose à 1,294 au-dessus des pieds, en coordonnées du monde, alors que le sprite est de face à l'écran.
- Dès que le joueur incline ou tourne la caméra, la bulle dérive par rapport à la tête. Sa hauteur par rapport à la tête dépend alors de l'inclinaison.

Correctif :
- Avance de 0,48 le long du rayon de vue de la visionneuse (`_decaler_profondeur`).
- Bulle ancrée au personnage qu'elle surmonte (`_ancrer_icone`) : l'écart est gardé tel que la caméra du jeu le voit, puis rapporté à la caméra de la visionneuse.

Mesures, bulle d'un PNJ (le prêtre de l'église de Strattbourg). Écart = (haut du panneau du sprite - bas de la bulle) / hauteur du panneau, plus négatif = bulle plus basse sur le sprite :

| Condition | Avant | Après |
|---|---|---|
| tangage -20° | -0,10 | -0,395 |
| tangage 0° | -0,38 | ≈ -0,40 |
| tangage +20° | -0,74 | -0,398 |
| tangage +40° | -1,09 | ≈ -0,37 à -0,40 |
| lacet 45° | -0,33, décalage latéral +0,20 largeur | -0,395, décalage -0,013 |
| lacet 90° | -0,22, décalage latéral +0,28 | -0,397, décalage -0,035 |
| tangage 20°, distance 200 % | -0,74 | -0,375 |

- Avec la caméra par défaut, la bulle est au même endroit à environ 1 px près (moins de 2 % de la hauteur du sprite).
- Pour le tangage +40°, les valeurs « après » viennent de la version précédente du panneau (-0,371 mesuré), pas du commit final ; l'écart est dans le bruit.

=== ÉTABLI / SUPPOSÉ / NON VÉRIFIÉ ===

Établi :
- Les chiffres ci-dessus.
- La bulle ne dérive plus avec la caméra du joueur.
- Les sprites sont droits à toutes les résolutions testées.

Supposé :
- La capture de l'utilisateur (s4, bulle trop haute) correspond à une caméra inclinée ou tournée, ou à un objet plus bas que la hauteur de panneau d'un personnage. Je n'ai pas pu confirmer lequel.
- La capture s5 (paysan aplati) est bien le penché hors-axe : le contact sheet avant/après le confirme visuellement, mais la position exacte du paysan dans la capture est inconnue.

Non vérifié :
- Le cas exact de la capture s4 (héros vert + tonneaux, journal 1) : le héros restait bloqué contre les décors.
  - Pour un tonneau ou une jarre sans personnage dessous, `_ancrer_icone` renvoie la position du moteur inchangée.
  - Si la bulle y paraît trop haute avec la caméra par défaut, c'est probablement la position du moteur (1,294 au-dessus des pieds), identique à l'original.
- Windows, aucune machine : tout est en numpy pur et testé seulement sous Linux / xvfb.
- Fusion avec les autres branches : pas lancée à l'exécution (voir plus bas).
- Combat avec effets et dégâts à l'écran : seul l'écran de commande a été comparé (0 pixel de différence).
- Effet Morph à l'exécution : seulement lu dans le code.
- Carte du monde avec sprites au bord : slot 4, 0 pixel de différence, mais la correction n'y est pas appliquée (branche sans `cam3d`).
- Écran de menu avec personnages : non rencontré sur les slots disponibles.

=== POUR LE MAIN AGENT : ligne pour pause.py (que je n'ai pas modifié) ===

- Clé : `correction_bords`.
- Valeurs : True (défaut) / False.
- Libellé proposé : « Correction des bords des sprites ».
- Placement : page Affichage, juste après « Distance caméra » et avant « Centrer la caméra sur le joueur ».
- Ligne, même modèle que « Centrer la caméra sur le joueur » (pause.py l. 270) :
  `self._choix('Correction des bords des sprites', [True, False], lambda: R['correction_bords'], lambda v: R.__setitem__('correction_bords', v)),`
- Effet immédiat : le réglage est relu à chaque image, aucun `regler_*` nécessaire.

=== PIÈGES DE FUSION (testés avec `git merge-tree`, rien d'appliqué) ===

Tous les conflits sont des insertions voisines : garder les deux côtés.
- agent-camera et retours-23h24 : window.py. Mes méthodes `_dbg_proj`, `_correction_bords`, `_decaler_profondeur`, `_panneau_ville` tombent au même endroit que leur `_camera_menee`. Garder les deux.
- agent-fenetre et retours-23h24 : window.py, `main()`. Leur ligne `--plein-ecran` (choices 0,1,2) est à garder, plus ma ligne `--correction-bords`.
- agent-fenetre et retours-23h24 : settings.py, `DEFAUT`. Garder `mode_fenetre`, `mode_fenetre_retour` et ma ligne `correction_bords`.
- agent-pause2 et retours-23h24 : settings.py, bloc de nettoyage des valeurs. Garder leurs deux lignes `defilement_combat` / `VITESSES_X_CLES` et mes deux lignes (validation `correction_bords` et `defilement_vitesse`).
- agent-titre et agent-editeur2 : fusion automatique sans conflit.
- Sémantique à relire après fusion avec agent-camera : mon calcul utilise `_cadre_vue` et `cam3d`, il doit rester valable si l'angle ou le FOV changent. À re-mesurer avec `DQ_PROJ=40` (voir plus bas).

=== FICHIERS TOUCHÉS ===

- /home/claude/wt-sprites/dq4_pc/fenetre.py : +94 -7
- /home/claude/wt-sprites/dq4_pc/reglages.py : +2

Détail window.py :
- `_panneau_ville` (nouveau).
- `_decaler_profondeur` (nouveau).
- `_correction_bords` (nouveau).
- `_ancrer_icone` (nouveau).
- `_icones` (branche `cam3d` réécrite).
- Boucle des sprites de ville.
- Option `--correction-bords`.
- Débogage : `DQ_PROJ=n` (pixels des panneaux et des bulles) et `DQ_CAMV_SPR=1` (sprites et icônes dans `DQ_CAMV`).

pyflakes : seul avertissement `sel`, déjà connu.

=== CAPTURES UTILES (chemins /tmp absolus) ===

- /tmp/spr_planche_bords.png : avant (haut) / après (bas), 3 PNJ au bord gauche et 3 au bord droit, 2560×1080 à 200 %.
- /tmp/nr_planche.png : slots 2, 3 et 4 (monde), et grotte avant / après.
- /tmp/nr_combat.png : combat inchangé (6 images, 0 pixel de différence).
- /tmp/nr_hd.png : modes Shader 0 et 1, avant / après.
- /tmp/spr_bulc.png : bulle avant / après au défaut (rendu par un état intermédiaire du code de bulle, qui n'a pas changé depuis).
- Sorties brutes : /tmp/out_mx_*.txt (avant) et /tmp/out_mx3_*.txt (après), /tmp/out_bul_avant_*.txt et /tmp/out_bul_apres_*.txt.
- Scripts : /tmp/spr_resume.py, /tmp/spr_resume2.py, /tmp/spr_bulle.sh, /tmp/spr_bulle.py.

=== NOTES POUR docs/ ===

1. Les sprites de ville sont des panneaux de face à l'écran, reculés en profondeur le long de l'axe de la caméra. Le recul est de 0,185 en bas et 0,65 en haut en unités d'origine, soit ×(w/0,48) dans le visionneur. Cela donne un penché vers l'extérieur proportionnel à l'écart au centre, et une hauteur à l'écran comprimée vers le bas de l'image.
2. La correction reconstruit le panneau à l'écran (coordonnées x/z et y/z de chaque coin) : mêmes positions verticales et mêmes profondeurs que l'original, bords verticaux, largeur = 0,74 × hauteur. `correction_bords` (0 à 1) fait la moyenne linéaire entre l'original et la version corrigée.
3. La bulle Riseup se règle avec la caméra de la visionneuse, pas celle du moteur. Le moteur pose l'icône en monde à +1,294 au-dessus des pieds. Le visionneur la rapporte au personnage sous elle en repère caméra du jeu, puis la ré-exprime en repère caméra visionneuse.
4. Outils de mesure : `DQ_PROJ=n` imprime les 4 coins projetés en pixels de chaque panneau et de la bulle toutes les n images. `DQ_CAMV_SPR=1` ajoute les sprites et icônes à `DQ_CAMV`.
5. Piège de test : les touches de `--touches-test` dépendent du fichier de réglages. Avec `touches_v` 4, `A` = E et `discussion` = SPACE, donc SPACE n'avance plus un dialogue dans certaines configurations. Les sorties dépendent aussi de `vitesse_marche` du fichier passé à `--reglages`. L'appli réécrit ce fichier à la sortie : utiliser une copie par scénario.
6. Cache : le cache de cartes courant est `carte8_*`. Des `carte7_*` écrits par un ancien commit traînent dans /tmp/uicache4 (innocents, jamais relus par le code actuel).

---
