## Agent a013cab3ae1bf6983 — 02/11 03:13

RAPPORT « libelles » (PR #43), branche agent-libelles, worktree /home/claude/wt-libelles

LIVRÉ (1 commit 4ec25d6, arbre propre, pyflakes sans alerte, 13 tests OK en 0,1 s, import 0,0x s sans numpy/unicorn/pyglet)
- dq4_pc/libelles.py : libelle_source(modele), libelle_lieu(carte) + confiance_source() / confiance_lieu() (« certain/suppose » ; « officiel/derive/generique »).
- tools/generer_libelles.py : régénère le bloc « lieux » de libelles.py et les tableaux de fréquence de test_libelles.py (`--apk <dossier APK> --cache <cache cartes> [--ecrire]` ; sans --ecrire = simulation). ~13 s.
- tools/test_libelles.py : sans xvfb, sans moteur, sans APK (données embarquées) ; imprime la couverture avec -v.
Rien d'autre touché (ni wt-histo, ni dq4-portage, ni docs/). APK, ressources, patch FR et sauvegardes en lecture seule.

CE QUE LE MOTEUR FOURNIT (vérifié en chargeant 4 sauvegardes sous Unicorn, `Moteur(APK, saves, tmp)`)
- Personnage : Etat.sprites[emplacement]['id'] = entier = feuille de sprite h<id> (carte du monde : +4096, déjà géré). libelle_source accepte l'entier, 'h019', '19', ou directement le dict Etat.sprites[i]. Exemple relevé à Bastione (caf1) : 36 -> « Un roi », 17/15 -> « Un soldat », 18 -> « Un chevalier », 5 -> « Un vieil homme ».
- Décor : nom de modèle FMAP, donnees.carte(nom)['noms'][objet] (« 012_tubo01 ») ; libelle_source accepte avec ou sans numéro de groupe et « (Clone) ».
- Lieu : Etat.carte (« caf1 », « mak1f1 »). PIÈGE VÉRIFIÉ : sur la carte du monde (Etat.partie == 0xe) Etat.carte garde le nom de la DERNIÈRE VILLE (« maout » avec partie 14). libelle_lieu(etat) accepte l'objet Etat et rend « Monde » si partie == 0xe ; sinon passer 'monde'.
- Emplacement 0 = chef de groupe jouable (id 106 sur deux sauvegardes du chapitre 1, 100 dans ev01) : libellé « Un aventurier » ; son nom doit venir du message, pas d'ici.

COUVERTURE (chiffres du test)
- Personnages : 3590 placements dans les scripts, 174 modèles. Nommés : 158 modèles = 3509 placements (97,7 %), dont certains 950 (26,5 %), supposés 2559. Non nommés volontairement : 16 modèles 3D (158, 161, 162, 164, 166, 167, 169, 170, 192, 196, 197, 210-213, 215) = 81 placements (le 215 en fait 37).
- Décors : 1939 noms de modèles, 16955 occurrences (vus ≥ 2 fois) ; 36 libellés couvrent 4868 occurrences (le reste = fleurs, herbe, lumières, murs, piliers, décor sans message). Tous les objets à examiner demandés sont couverts : jarre, tonneau, coffre, étagère, commode, tiroir, caisse, puits, lit, panneau, fourneau, cheminée, sac, livre, tombe, statue, trône, armure, porte, chaise, table, etc.
- Lieux : 670 cartes du jeu (.fld) : nom officiel du patch FR 248, dérivé 31 (« Château de X », « Château de Bastione »), générique 192, sans lieu 199 (dont 140 cartes de combat bt, 9 ev, 1 fk, 23 za, 25 s?).

RÈGLE DES LIEUX (une seule, documentée) : le moteur nomme un lieu d'après les 2 premières lettres de la carte (SaveLoad::getPlaceNameNo + TextAPI::extractText, entrée NN-1 de b1007000) ; tout l'intérieur d'un lieu (maisons, auberge, église, puits, étages) rend le nom du lieu (« Strattbourg », jamais « Maison, Strattbourg »). Préfixe c? : « Château de X » sauf noms déjà « Palais… ». Sans nom officiel : c -> « Château », d -> « Grotte », t -> « Tour », m -> « Ville », s? avec maisons/auberge (sb, se, sj) -> « Village » ; bt, ev, fk, za, autres s? -> None.

ÉTABLI
- Format des placements de scripts, table de conversion du moteur (types 2/3/4), nom officiel par préfixe (lu dans le moteur, tous les préfixes cohérents), texte FR de chaque nom, id des sprites sur 4 sauvegardes, « Etat.carte périmé sur la carte du monde ».
- Planches vues avec Read : les 155 feuilles h utilisées ; 183 = ballon et 193 = bateaux confirmés sur la carte du monde (ids 4279 / 4289).
SUPPOSÉ
- Tout le classement visuel marqué 'S' (métier, âge, sexe d'après l'image seule) ; les noms d'objets déduits du romaji (tubo, taru, hondana, tansu, kb...) : modèles 3D non rendus à l'écran ; « Château de X » pour cb cd cf cg ci ck ; « Château de Bastione » pour ca (le moteur n'a pas de nom pour 'ca' ; appuyé par la sauvegarde 2 et par le script de caf1 qui renvoie vers haout = Bastione).
NON VÉRIFIÉ
- Les types 3 (165, 199-204, 221-230, 298, 300 -> « Un monstre ») et 4 (299 -> « Un meuble ») : déduits de la table du moteur, pas vus en jeu ; comment histo obtiendra l'identité d'un monstre/modèle 3D (ils n'apparaissent pas dans Etat.sprites) n'est pas résolu. Aucun test avec fenêtre.

CAS DOUTEUX À FAIRE RELIRE
- Sprite 9 (195 placements, 43 dans des auberges) : « Un homme » ; peut-être l'aubergiste. 11, 65, 220 « Un homme costaud ».
- 15/16/17 « Un soldat », 18 et 152 « Un chevalier » (frontière floue). 19, 144 « Un guerrier ».
- 34 « Un noble », 37 « Un jeune noble », 35 et 38 « Une dame » (38 se tient à côté du roi 36 : probablement la reine), 79 et 82 « Un roi ».
- 148, 149 « Un ange » (ck = Zénithia) ; 68, 75, 153, 155 « Un magicien » ; 21 « Un prêtre » (lu dans les églises) ; 66 « Un marin » (carte mndoc).
- 131 et 52 « Un chien » (peut-être un loup) ; 45, 46, 47 « Un chat » ; 138, 141 « Un félin ».
- 69, 70, 71, 72 (village mq, bonnets sarcelle) : « Un homme / Une femme / Un garçon » sans race.
- 216, 217 (héroïne aux cheveux verts, ev08) « Une jeune femme ».
- Lieux : dp = 29 cartes d'un donjon à 8 niveaux que le moteur nomme « Chapelle du Coteau » (gardé, règle du moteur) ; cc, ch, cl, cm restent « Château » (nom non connu du moteur) ; tous les d* « Grotte » (peut être un tunnel, une mine) ; mg, ml, mp « Ville » ; za (3 tours de 9 étages) et la plupart des s? : None, par prudence.
- Les 16 modèles 3D du type 2 restent sans nom (le 215 est placé 37 fois dans 27 cartes) : vérifier à l'écran si l'on veut un libellé.

NOTES POUR LA DOC (à fusionner, rien écrit dans docs/)
- Feuilles de sprite h<id> : 3 colonnes x 4 lignes de 24x32 (ligne 0 dos, 1 profil, 2 face, 3 profil) ; 128x256 = 8 lignes pour les 10 personnages jouables (100, 103...127 de 3 en 3) ; h193 = bateaux 512x512.
- Placements de personnages : `scriptobject` ; six int32 (a0, modèle, direction, x, y, z) à o + (W(o+0x14)&~3) + (W(o+0x20)&~3) ; table de conversion à 0xfda20 (36 triplets clé, cible, type : 2 = modèle 3D 310-325, 3 = monstre 0-18, 4 = meuble).
- getPlaceNameNo : 2 premières lettres du nom de carte ; 0x0c0000NN ; texte = entrée NN-1 de b1007000 (n = 52 donne encore « ソロタウン », non traduit, aucun préfixe ne l'utilise).
- Etat.carte reste la dernière ville quand Etat.partie == 0xe.

PIÈGES DE FUSION
- 3 fichiers neufs, aucun conflit attendu. Les blocs entre « # === DEBUT GENERE » et « # === FIN GENERE » sont écrits par le générateur : ne pas les éditer à la main.
- Le générateur remplit le cache de cartes donné par --cache (j'ai utilisé /tmp/uicache4 : une centaine de carte8_*.pkl ajoutés, inoffensif). Le jeu compte 670 cartes (.fld) et non 523 : 523 était le contenu du cache d'alors.
- Côté histo : ev* (événements) et bt* rendent None -> garder le dernier lieu connu ; ne pas passer Etat.carte seul sur la carte du monde ; préférer le nom lu dans le message à « Un aventurier » pour les personnages jouables.
- Rien à mémoriser sur l'utilisateur.

---

## Agent a85fdfd2cea49649d — 02/11 03:15

RAPPORT agent « coffres » (Screen 3), worktree /home/claude/wt-coffres, branche agent-coffres, base 08f5785. Arbre propre, 2 commits.

## Verdict
Cause racine trouvée, corrigée globalement et vérifiée par captures avant/après sur toutes les orientations rencontrées. Un défaut de rotation des objets de carte, pas un problème de « tourner le coffre vers le joueur ». Le coffre garde son cap propre (celui de la carte) et son couvercle pivote autour de SA charnière arrière.

## Constats
1. **Cause racine : ordre des rotations faux dans `donnees.euler_mat`.**
   - Désassemblage de `FldObject.rotateXZY` (0xCD47F0) : q = (AngleAxis(ry, up) * AngleAxis(-rz, forward)) * AngleAxis(-rx, right).
   - Axes lus : statiques `Vector3` aux décalages 0x18, 0x48 et 0x3C (confirmés dans le dump).
   - Produit de quaternions relu instruction par instruction : q2*q3 puis (q2*q3)*q1, donc X d'abord (repère de l'objet), puis Z, puis le cap Y en dernier. Matrice = Ry·Rz·Rx.
   - Le code d'avant (#21) faisait Rx·Ry·Rz, donc la bascule du couvercle (clé FPMV rx = -60) se faisait autour de l'axe X du monde, pas de celui du coffre. La note #21 « ordre X, Y, Z » était fausse.
   - Conséquence : seul un coffre de cap 0 s'ouvrait bien. Cap ±90 : couvercle de côté. Cap 180 : couvercle vers l'avant, dans le coffre. Cap -27 : couvercle de travers, face extérieure vers le joueur.
2. **Deuxième défaut, même famille : `c_pmv_func` ignoré.**
   - Les mouvements communs (flag & 4) lisent leur déplacement dans le repère de l'objet : position = MultiplyPoint(TRS(pos, rotateXZY(rot), scl)) de l'objet (0xCD96D8). `update_pmv_one` (0xCD6824) choisit CPMV (4) quand flag & 4, sinon PMV (1).
   - La visionneuse ajoutait le déplacement tel quel (monde). Les tiroirs (`hikidashi1b`, clé posZ) de cap ≠ 0 sortaient de côté.
3. **Représentation des coffres (lue dans les données).**
   - Un coffre = 2 objets de carte : `tbox01` (corps, sans animation) et `tbox02` (couvercle, origine = charnière arrière haute, table FCAN).
   - Animation 1 = fermé, 2 = ouverture (rotation X de 0 à -60 en 10 unités, 5 images de jeu), 3 = tenu ouvert, 4 = fermeture.
   - Aucun modèle 3D séparé, pas de 4 ou 8 orientations : un seul cap Y par objet.
   - Sur les 194 coffres, 184 ont le cap 0. Les 10 autres : `ham1f1` (90), `hcy1b1` (90 x3), `mdi1f1` (-27), `sjout` (rz = -7), `ss5b1b` (-90 x2), `tcf1` (180), `tcf3` (180).
   - Flag de billboard = 0 : les coffres ne se tournent jamais vers la caméra. Seuls tonneaux et jarres (flag 4) le font.
4. **Aucune logique Unity de coffre dans le dump.**
   - Pas de classe TreasureBox ou TownChara pour ça ; tout passe par `FldObject`.
   - Moteur : `TownFurnitureObject::openObject` n'envoie que `SetCommonAnimation(objet, 2)` (fermeture = 4) via le paquet 5. Aucune rotation vers le joueur.
   - Le paquet 4 (`cmd_fld_rot`) n'est émis que par `FldStage::setRotObjectUid`, sans appelant direct dans le .so (donc par script d'événement éventuellement), et par `CasinoPoker::initialize`.
5. **Animations communes de tout le jeu** (scan des 523 cartes) :
   - Coffres : rotation X seule.
   - Tiroirs : posZ seule.
   - Portes (door01-06, wdoor01-06) et battants d'armoires (tansu*) : rotation Y seule, donc inchangés.
   - Jarres et tonneaux : billboards, hors sujet.
   - Seuls coffres et tiroirs étaient touchés (10 coffres, environ 9 tiroirs de cap ≠ 0 : chf2, dpb4b/5b, mkm1f1, mmout, sey1f1, shb1, za2f8, za3f2).
6. **Effet de bord voulu : la pose initiale des objets inclinés (rx ou rz ≠ 0 avec ry ≠ 0) change aussi.**
   - Environ 280 objets, 71 types : falaises `dlkm1a`, touffes `kb0x`, `tate01b`, `ken01b`, `tenkuzyo2e` (l'île du titre), etc.
   - Indice que le nouvel ordre est celui voulu par les concepteurs : les paires `dlkm1a` (40, 6, 0) / (-40, 186, 0) penchent dans la même direction du monde avec Ry·Rx, et en sens opposés avec l'ancien ordre.

## Corrections (fichiers et fonctions)
- `dq4_pc/donnees.py` :
  - `euler_mat` retourne `Ry @ Rz @ Rx` (docstring refaite).
  - Cache `carte8_` devient `carte9_` dans 3 endroits : `Donnees.carte`, `_elements`, et `_purger_anciens` (purge `carte[0-8]_`). Les sommets des objets inclinés sont cuits avec `euler_mat` : le cache doit être refait.
- `dq4_pc/objets_carte.py` : dans `ObjetsCarte._poser`, un mouvement avec `flag & 4` ajoute son déplacement dans le repère de l'objet (`pos += _rot(rot) @ (scl * dp)`) ; les autres mouvements (flag 0 ou 1) inchangés.
- `dq4_pc/fenetre.py` : seule la ligne du prédécesseur est conservée, `DQ_CARTE_SANS_SPR=1`.
  - C'est un crochet de test dans le bloc `DQ_CARTE_TEST` de la méthode d'image (~l.2801). Il vide `e.sprites` pour que le héros ne masque pas l'objet.
  - Aucune fonction du périmètre interdit touchée (`_panneau_ville`, `_correction_bords`, `_decaler_profondeur`, titre, modes de fenêtre, souris).
- `tools/test_objets_carte.py` (nouveau, prédécesseur complété) : 15 tests, environ 5 s, sans xvfb. Cherche les cartes dans `DQ_CACHE_CARTES` (défaut `/tmp/uicache_coffres`) et ignore les tests « vrais objets » si le cache manque.
  - 11 tests de logique pure : `euler_mat` contre une référence quaternions indépendante, bascule X dans le repère de l'objet, couvercle à tous les caps, tiroir et échelle, ordre moteur pos/rot puis anim, porte inchangée.
  - 4 tests sur les VRAIS objets : les 194 coffres (rotation rigide autour de la charnière, aucun roulis le long de l'axe X du coffre, bord libre qui monte et recule, refermeture identique au départ), tiroirs (déplacement = R(cap) · clé), portes.
  - Vérifié que le test des coffres échoue avec l'ancien `euler_mat`.
- Commits (pied de message du brief présent) : ac4cb9b (correction + cache carte9) et f58ce7b (tests des vrais objets).
- pyflakes : seul avertissement `struct` inutilisé dans `data.py`, déjà connu.

## Captures avant/après (chemins absolus, avant = haut ou 1re ligne, après = dessous)
Colonnes : images 9, 12, 14, 16, 22, 40.
- `/tmp/coffres_captures/mdi1f1_avant_haut_apres_bas.png` : coffre de cap -27, caméra par défaut. **C'est très probablement la scène de la capture de l'utilisateur.**
- `/tmp/coffres_captures/ss5b1b_cap-90_avant_haut_apres_bas.png` : cap -90.
- `/tmp/coffres_captures/hcy1b1_cap90_et_tcf1_cap180_avant_apres.png`
- `/tmp/coffres_captures/mdi1f1_cap-27_et_ham1f1_cap90_avant_apres.png`
- `/tmp/coffres_captures/tiroirs_sey1f1_cap90_chf2_cap-90_avant_apres.png` : tiroirs, qui sortaient de côté et sortent maintenant vers l'avant du meuble.
- `/tmp/coffres_captures/caf1_cap0_temoin_camera_0_35_-35.png` : témoin cap 0 (inchangé) avec la caméra tournée.
- `/tmp/coffres_captures/titre_ile_avant_gauche_apres_droite.png` ; plein cadre : `/tmp/coffres_captures/titre_avant_700.png` et `/tmp/coffres_captures/titre_apres_700.png`.
- Outils (non commités) : `/tmp/cof/chest_shot.sh`, `/tmp/cof/batch2.sh`, `/tmp/cof/batch3.sh`, `/tmp/cof/sheet.py`. Base « avant » : copie `/tmp/coffres_avant`. Cache complet carte9 de mes essais : `/tmp/uicache_coffres` (523 cartes ; ne touche pas `/tmp/uicache4`).

## Établi / Supposé / Non vérifié
**Établi** (lu dans le code ou observé) :
- Ordre `rotateXZY` et axes (désassemblage + dump).
- `pmv_func` et `c_pmv_func` : somme des angles d'Euler puis `rotateXZY`, échelle multiplicative, déplacement de `c_pmv_func` dans le repère de l'objet.
- Choix CPMV par `flag & 4`.
- Le moteur n'envoie que les animations 2 (ouvrir) et 4 (fermer) pour les coffres.
- Les 194 coffres, les tiroirs et des portes de toutes les cartes passent les tests.
- Captures sous xvfb (Mesa) : les couvercles s'ouvrent vers l'arrière du coffre à tous les caps, les tiroirs sortent vers l'avant.

**Supposé :**
- Que la capture de l'utilisateur vient de `mdi1f1` (boutique à écusson « sac », plancher, pilier blanc ; seul coffre de cap -27 ; le rendu avant en caméra par défaut a le couvercle face extérieure vers le joueur). Identification par ressemblance, pas par sauvegarde.
- Que « orientés vers le joueur » désigne les coffres de cap ≠ 0.
- Que l'original ne tourne pas le coffre vers la caméra : flag 0, pas de rotation envoyée. Si on veut qu'il le fasse quand la caméra tourne, ce serait un ajout non fidèle.

**Non vérifié :**
- Aucune comparaison avec une capture du téléphone (aucune disponible).
- Pas de partie jouée avec ouverture réelle d'un coffre (animation lancée par `DQ_ANIM_TEST`, même chemin `anim_commune` que le paquet 5).
- Rendu GPU Windows.
- Qui appelle `setRotObjectUid` par script (un événement pourrait tourner un objet).
- Sens 2 contre 4 des portes : choisi par le moteur (non lu), la visionneuse joue le numéro reçu.

## Pièges de fusion / à signaler
1. **Titre (`ev01`)** : l'île du château (`tenkuzyo2e`, rot (-43, 39, -18)) change d'inclinaison. Le « haut » de l'île passe de (-0,24 ; 0,56 ; 0,79) à (0,25 ; 0,70 ; 0,67) : avant, château penché vers la gauche ; après, château quasi vertical, île inclinée dans l'autre sens. Conforme au code d'origine, mais l'agent « titre » doit le savoir avant de recaler « dragon et château » sur le mobile.
2. **Cache** : le nom `carte9_` doit rester le plus grand entre agents. Si un autre agent change aussi le préfixe, prendre le max et garder la purge `carte[0-N]_`. Au premier lancement, les 523 cartes sont préparées de nouveau (préparation en arrière-plan : 0,1 à 0,3 s par carte en test).
3. `window.py` : une seule ligne ajoutée (test), conflit très peu probable.
4. `tools/test_objets_carte.py` est nouveau ; les tests existants ne dépendent pas de `euler_mat`.

## Notes de doc à fusionner (notes-visionneuse + notes-technique)
**Coffres, tiroirs : rotation des objets de carte (#43).**
- Coffres de cap ≠ 0 s'ouvrant de côté ou vers l'avant, tiroirs sortant de côté (Screen 3 du 02/11).
- Cause : `donnees.euler_mat` composait Rx·Ry·Rz alors que `FldObject.rotateXZY` (0xCD47F0) fait (AngleAxis(ry, up) * AngleAxis(-rz, forward)) * AngleAxis(-rx, right) : X d'abord dans le repère de l'objet, Z, puis Y (le cap) en dernier = Ry·Rz·Rx. L'ordre « X, Y, Z » de #21 était une erreur de lecture.
- Les mouvements communs (FPMV, flag & 4) sont lus par `c_pmv_func` (0xCD96D8) dans le repère de l'objet ; `update_pmv_one` (0xCD6824) choisit CPMV (4) quand flag & 4, sinon PMV (1).
- Un coffre = `tbox01` (corps) + `tbox02` (couvercle, origine = charnière arrière haute). Animation 2 = ouverture (rx 0 à -60), 3 = tenu, 4 = fermeture. Le moteur n'envoie que `SetCommonAnimation` 2 ou 4 (`TownFurnitureObject::openObject / closeObject`), jamais de rotation vers le joueur.
- Caps des coffres : 184 sur 194 à 0 ; les autres dans `ham1f1`, `hcy1b1`, `mdi1f1`, `sjout`, `ss5b1b`, `tcf1`, `tcf3`.
- Animations communes du jeu : coffres rx, tiroirs posZ, portes et armoires ry (inchangées).
- Cache `carte9_`.
- Effet de bord : environ 280 objets inclinés changent d'orientation, dont l'île du titre.
- Test : `tools/test_objets_carte.py`.
- Reste non vérifié : voir ci-dessus.

Mémoire (informations utiles pour plus tard, source = cette session) : l'utilisateur teste ses captures sur des cartes réelles du jeu (la capture « Screen 3 » correspond très probablement à `mdi1f1`, cap -27).

---
