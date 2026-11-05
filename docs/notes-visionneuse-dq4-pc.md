# Visionneuse PC de DQ4 (dq4_pc) : notes (mises à jour le 31/10/2026)

> **Rangement du 04/11/2026 (#196)** : les chemins `dq4_pc/xxx.py` cités plus bas datent d'avant le rangement du projet (modules maintenant dans `dq4_pc/noyau`, `monde`, `menus`, `fenetre`…, `fenetre.py` découpé en plusieurs modules ; `dq4_pc/cache` et `jeux/DQ4` remplacés par `donnees/`). Table de correspondance ancien nom → nouveau dans [`plan_du_code.md`](plan_du_code.md) ; les numéros de ligne ne valent plus, chercher le nom de la fonction.

Complète `notes-technique-portage-dq4.md` (référence pour le protocole moteur->Unity). Remplace ses sections « Rendu : état » et « Inconnues » pour la visionneuse.

## Ce qui marche
- Fenêtre pyglet 16/9 (GL 3.3) : décor, sprites nets, caméra du moteur, marche au clavier, **portes qui s'ouvrent, changement de carte** (église `mak1f1` -> village `maout`), fond de ciel, cadrage large.
- **Messages** (fenêtre bleue, texte FR du moteur, défilement, ouverture/fermeture), **menus** (liste de l'église, menu de commandes du terrain Objets/Magie/Carac./Divers + équipe + or, choix du personnage) avec navigation clavier : testés en cloud (captures) ; retour de l'utilisateur sur pdc : « un peu mieux, pas mal d'imperfections ».
- Moteur ~2-4 ms/image (Unicorn), tick 30 Hz. 720 images avec touches aléatoires : aucun plantage.

## Architecture (dossier `dq4_pc`)
- `emu_core.py` (chargeur ELF + Unicorn), `pktlog.py` (paquets), `moteur.py` (`Moteur`, `Etat`, `Interface`), `fld.py` + `donnees.py` (UnityPy -> maillages, feuilles de sprites, cache `carte6_<nom>.pkl`), `hd.py` (agrandissement HD des sprites), `fenetre.py` (fenêtre, shaders, clavier, portes, cadrage, message, menus), `lancer_dq4.bat` (venv + modules, Python 3.13 > 3.12 > 3.11 > 3.14 > 3.10).
- Options `fenetre.py` : `--apk --saves-lecture --saves-ecriture --cache --slot --largeur --hauteur --hd --msaa --shot --images --script "n:masque,..." --auto-message`; variable `DQ_DEBUG=1` = trace des entrées. Test sans écran (Linux) : `xvfb-run -a python3 dq4_pc/fenetre.py ... --shot x.png --images N --script "..."`.

## Entrées : GameUpdate(arg1, arg2)
- `arg1` = touches **maintenues** (marche) ; `arg2` = touches **venant d'être pressées**. Haut 0x1, Bas 0x2, Gauche 0x4, Droite 0x8, OK 0x10/0x40, Annuler 0x20/0x80.
- `Global::NativeExec` convertit `arg2` en mot de touches du terrain (u16 à `*(GOT 0xa30)+2`) : **arg2 == 0x100 EXACTEMENT** (bit15 ignoré) -> bit 0x10 (parler/examiner ; la fenêtre de PNJ proche s'ouvre) ; **0x400** -> bit 0x20 (parler si flag `+0x971`) ; **0x800 -> bit 0x40 = ouvrir le menu de commandes** (`NormalControl::execute` -> `openMenu`) ; **0x1000 -> bit 0x80 = carte / liste des magasins** (flag global : bit4 carte, bit5 liste ; ouvre « Magasin d'armes… » ; non géré à l'affichage) ; 0x2000 -> bit 0x400 (non étudié).
- Mapping de la visionneuse : sur le terrain (ni message ni menu actif) A = 0x100 seul, Annuler = 0x800 ; message affiché : A = 0x10 ; menu actif : les touches ne vont PAS à `GameUpdate`, elles sont injectées dans la file interface->moteur (voir plus bas).
- `FLDObject::SetCommonAnimationEnd(idx)` existe aussi côté flux d'entrée (`inp`, paquets d'entrée type 1) : alternative à l'écriture directe du bit0.

## File de messages MenuPort (interface <-> moteur)
- `MenuPortInit(32, buf1, 129, buf2, 1089)` : les tampons sont alloués par l'appelant (nous : `malloc(0x2000)` chacun ; 4096 shorts lus). **buf2 = moteur -> interface**, **buf1 = interface -> moteur**. Même format : `[0..31]` tête par port, `[32..63]` queue (= indice du champ « suivant » du dernier message), `[64]` pointeur libre (démarre à 65) ; message = `[n, n shorts, suivant]` (indices absolus en shorts, suivant 0 = fin).
- **Sans consommation la file déborde** (écrase la mémoire voisine) : `Moteur._consommer_messages()` lit les 32 listes après chaque `GameUpdate`, remet têtes/queues à 0 et `[64]=65`. Les messages d'initialisation (ex. libellés Objets/Magie/Carac./Divers du port 4) sont émis AVANT la 1re image : ils doivent être mémorisés (`Interface`), pas jetés.
- `UnityMenuLoop` (appelée au début de `GameUpdate`) : pour chaque port enregistré (table `*(LIB+0x252098)`, entrées de 0x20 octets : +0x28 n° de port, +0x30 objet, +0x38 callback, nombre à `LIB+0x252094`), dépile un message et appelle le callback. Callback standard = `MenuItem::NoticeFromUnity`.
- **Interface -> moteur** (`NoticeFromUnity`) : message `[3, 1, idx, pad]` sur le port de la fenêtre. `idx` = ligne touchée/choisie (-1 = aucune) ; `pad` : bit0 bas, bit1 haut, bit2 gauche, bit3 droite, bits 4/6 OK, bits 5/7 annuler. **Le curseur appartient à Unity** : pour déplacer, envoyer `[1, ligne, 0]` (le moteur répond `[4, ligne]` sur le port) ; pour valider, `[1, -1, 0x10]` puis `[1, -1, 0]` à l'image suivante (Annuler 0x20). Sans « touche idx » préalable, OK choisit la ligne 0. Un message `[1, ...]` seul sur flèche bas/haut ne bouge rien.
- Fenêtre qui attend les touches : port dont l'objet MenuItem a `+8 == 1` (actif) ET `+0x50 != 0` (saisie permise) ; l'or (port 3) est actif mais sans saisie, l'équipe (port 5) est visible mais inactive tant qu'on n'a pas choisi une commande.

## Messages moteur -> interface
- Port 0 (système) : `[N, 1, type, style]` définit la fenêtre N (N=1..11 à l'init, puis 12+ dynamiques ; style = n° de gabarit Unity, positions/tailles inconnues côté moteur) ; `[N, 2]` ferme N ; `[N, 3, v]` montre/cache N (N=1 = message) ; `[0, 4|5, 127]`, `[0,7,76,76]`, `[0,8,2,1]` = volumes/divers.
- Port P (liste) : `[1,a,b,c]` ouvre (visible) ; `[7,0]` ferme ; `[11, ligne, colonne]` annonce que le message suivant du MÊME port est le texte (UTF-16, '\n' possible) de la case ; `[12, ligne, x]` indicateur de ligne (0/1) ; `[10, ligne, ...]` style de ligne ; `[4, i]` curseur sur la ligne i ; `[5,0]`/`[6,0]` ticks à chaque image (ignorer).
- Contenus vus : port 2 Oui/Non ; port 3 or ; port 4 Objets/Magie/Carac./Divers (colonne 1) ; port 5 équipe (colonnes 1 nom, 2 libellé PV/PM, 3 valeurs, 5 numéro ; lignes 2,3 = persos) ; port 12 liste de l'église (ligne 6 = titre, 0-4 choix, 5 « Rien ») ; port 13 liste du titre (Continuer / Reprendre / Créer / Supprimer / Sauv. cloud / Licence) ou choix du perso ; ports 12-14 aussi pour la liste des magasins (colonne 0 = noms séparés par '\n', colonne 2 = prix, colonne 3 = « 1/3 »).
- Fenêtre de message = port 1 : `[0,0]` nouvelle page/vider, `[3, y]` défilement (pixels du canevas), `[4,x]` ?, `[1,1]` attente d'appui (curseur ▼, non dessiné), `[1,0]` fin d'attente. Texte rendu PAR LE MOTEUR dans le canevas `SDrawCTRL` (objet `LIB+0x252330`, tampon à `+0x10`, 1 octet/pixel d'opacité) créé par `CanvasSetup(obj, short*)` avec `[0, 1,0, 0,0 ...]` (ints aux offsets 2,6,10,14,18 = texId, ?, largeur 512, hauteur 256, drapeau) ; zone visible = `(int16 LIB+0x2523a0)+1` lignes × `int16(obj+0x42)`, haut = `int16(obj+0x4a)+3`. Visibilité : hook sur `MenuPort::SetVisible` (port `*(obj+0x30)`). **Correction 30/10 soir : le canevas fait 512 x 512 (`CANEVAS_H = 512`), pas 256.**

## Autres découvertes (rappel)
- FLD `.map` : objets FMAP = enregistrements 0x50 ; `mdl_id` = préfixe du GameObject enfant (`003_wdoor04`, `022_door01`). Paquet 5 = animation d'objet (porte...) : `index | anim<<16` ; **Unity doit remettre le bit0 de l'octet +0x14 de `table[idx*32]` à 0 à la fin** (visionneuse : 18 images), sinon le joueur est bloqué. Paquet 8 = couleur de fond (octet signé/31). Paquet 33 = teinte (non utilisé).
- Sprites `h<id>` 24×32. **Styles (F2 les fait défiler ; depuis #41 il n'en reste que 0, 1 et 4 : « Régions lissées » et « Bicubique » ont été retirés, voir « Retours de 20 h 46 »)** : 0 originaux (shader « sharp bilinear »), 1 **EPX ×8** (défaut), 2 **régions lissées** (EPX ×4 puis chaque couleur = masque interpolé et flouté, la plus forte l'emporte), 3 **bicubique** (doux). `hd.py` les calcule ×8 par case, en **tâche de fond** (l'original s'affiche en attendant) avec **cache disque** `cache/hd_<algo>_v<VERSION>_h<id>.npy` (incrémenter `hd.VERSION` si un algorithme change) ; chaque case est replacée dans un atlas avec une gouttière de 4 px (bords répétés) + mipmaps (2 niveaux) ; les pixels transparents reprennent la couleur du voisin opaque (pas de liseré). Les feuilles à alpha déjà adouci (ex. `h106`) passent en bicubique. xBR / ScaleFX réels : non portés (à faire si besoin).
- Performance : le tracé réutilise les listes de sommets (une par emplacement de sprite) et ne lie le VAO qu'une fois par image (`_tracer`) ; F1 affiche ou masque le bloc d'aide (cadre noir translucide), F4 affiche images/s, pire image, durée moteur et dessin Python. Au chargement d'une carte, créer ~55 textures de décor bloque ~0,1-0,5 s (à lisser plus tard).
- Décor : mipmaps trilinéaires + anisotrope (jusqu'à ×8, F3 pour comparer) et anticrénelage matériel MSAA ×4 (`--msaa 0` pour couper ; repli automatique si la carte ne le propose pas ; non vérifiable en cloud : le serveur d'affichage logiciel n'en propose pas). Caméra : FOV vertical 20°, cadrage 16/9 par décalage en x (marge 0,85). Portes : battants pivotant de 90° (approximation).
- Libellés de menus FR : fichier de textes du moteur `assets/msg/en/b1004000.mpt` (Parler, Magie, Objets, Examiner, Équiper…).

## Carte du monde dans la visionneuse
- `Moteur` : `Etat.partie`, `Etat.champ` (paquet 28) ; `demarrer_champ()` (option d'essai `--force-champ`). `Donnees.texture(nom)` lit une texture Unity par nom (cache `tex_<nom>.npy`).
- `fenetre.py` (30/10) : **caméra orthographique vue de dessus, comme `Field.Init` du jeu** (`_camera_champ`) ; hauteur visible = `CH_VUE_HAUT` ≈ **20,2 tuiles** (31/10 : le héros a la même taille que dans les villes, voir « Zoom commun » plus bas ; l'écran portrait d'origine en montre 28,4 en hauteur et 16 en largeur, `CH_VUE_HAUT` valait 28,4 avant) quelle que soit la fenêtre (en 16/9 : ~36 tuiles de large) ; **molette = zoom** (x1,1 par cran, 0,4 à 4 ; 0,5 à 2 depuis #27) ou `--carte-zoom`. Héros et compagnons **à plat** (haut du sprite = nord), taille d'origine ~24,9 x 33,2 px (`CH_ECHELLE` 1,0368, `Chara.SetFieldMode`). Sol : `_maj_champ` construit un maillage couvrant la zone visible (bornes arrondies à 4 tuiles) à partir de **la carte entière lue dans le moteur** (`Moteur._lire_monde` : grille CWorldMap 256 x 256 à `FieldData+0x188`, table des blocs de 6 octets à `+0x180`, décalages d'animation de l'eau en `0x275830/34/38`, même règle que `FieldData::drawBlock`, vérifiée 1300/1300 ; objet `FieldData` capturé par un crochet sur `drawBlock`). Le moteur n'envoie que 25 colonnes (paquet 28) : insuffisant dès qu'on dézoome ; ce paquet ne sert plus que de repli. `DQ_ETAT=1` : état du moteur.
- Icônes (paquet 29) : `Etat.symboles`, table `CH_ICONES` (genre -> case de l'atlas), dessinées à plat (tête en bas dans l'atlas, retournées) par `_tracer_champ`. Carte en miroir en x (correction d'orientation) et atlas en `GL_NEAREST` (net).
- Limites : genres 18/19/20 non dessinés ; pas de marche sur l'eau/bateau testée ; la fenêtre d'icônes (paquet 29) reste celle du moteur.

## Combat dans la visionneuse
- `Etat` : `cam_rot`, `cam_fov`, `modeles` (paquet 21), `maillages` (paquet 22), `mesh_etat` (paquets 21/23/24/25/26 : shader, visibilité, couleur, décalage de texture). `fenetre.py` : `_camera_combat` = **caméra du Unity d'origine** (euler `(-ax, -(ay+180), az)`, champ nominal 48 ×4/3 horizontal sur vue 4/3 -> 50,25° vertical, near 0,25, far 500, décalage vertical 0,04), décor **×6** (aucune autre correction), monstres = sommets tournés par `caméra × Euler(0,180,0)` (`_maillages_combat`). Détails et sources (classe/méthode) : `docs/notes-technique-portage-dq4.md`, section Combat.
- Leviers d'essai (la transformation est celle du code d'origine ; ils ne servent qu'à comparer) : **F7** scène en miroir gauche/droite (`DQ_CB="miroir_x,dec_z"`, défaut `0,0`), **F9** quads des monstres en ordre inverse (`DQ_ORDRE=1` au départ) ; états affichés dans la ligne d'aide. F6 et F8 (sol rehaussé, décor tourné) et `DQ_CB2` n'existent plus.
- Monstres : une liste de sommets de capacité fixe par emplacement (`CB_CAP`), alpha par quad (octet de couleur du paquet 22) x `Material.color` (paquet 25), **ordre des triangles = ordre des paquets** (shader `DssaMonster*` : pas d'écriture de profondeur), `glDepthMask` coupé pendant leur tracé, monstres triés par file de rendu puis du plus loin au plus proche.
- Tests sans écran : `--images-combat N` (capture N images après le début d'un combat), `--script-combat "n:masque,..."` (touches pendant un combat, n = images depuis son début), `--shots-combat "a,b,c"` (captures intermédiaires `<shot>_<n>.png` à ces images de combat, avec l'image moteur et les maillages affichés dans le journal), variable `DQ_PKT=fichier` (journal des paquets de combat : image, emplacement, nb de sommets, position, boîte).
- Fond : le moteur n'envoie pas de couleur de fond en combat (paquet 8 absent) et le décor laisse un vide entre le bord du sol et le dôme du ciel (plaine : dôme `plsora_d` dont l'anneau bas est à y = 3,7) ; `_fond_combat` calcule la couleur moyenne du sol à la périphérie de l'arène (texture x couleur de sommet) et s'en sert comme couleur d'effacement. Estimation : la vraie couleur du fond de caméra est côté Unity (inconnue).
- Test : `DQ_DECOR=btl_pl_d` force un autre décor de combat (comparer plaine/forêt sans attendre la bonne rencontre).
- Limites : effets et chiffres de dégâts, fenêtres : voir section Interface d'origine, couleur de fond du décor encore estimée (le code d'origine la prend dans les données de la carte : `cmd_fld_load` -> `BackColor.SetColor(0, ...)`), roulis de la caméra ignoré (toujours 0 en combat).

## Interface d'origine dans la visionneuse (`ui_menu.py`, 30/10/2026)
- Les fenêtres du jeu (cadres, boutons, icônes, barres de PV/PM, textes colorés) sont dessinées d'après la **mise en page exportée du code d'origine** (`cache/ui_layout.json`, voir `docs/notes-technique-portage-dq4.md`, section Interface d'origine). `ui_menu.py` : `MiseEnPage` (JSON), `Fenetre` (une fenêtre = un type de menu, reçoit les paramètres/codes envoyés par le moteur), `Rendu` (maillages + textes), `Gestionnaire` (fenêtres ouvertes par port). `moteur.py` : `Interface.obs` relaie ouverture/fermeture/paramètres/codes/sélection.
- **Génération** : `outils\generer_ui.bat` (≈ 2 min, une seule fois) ; `lancer_dq4.bat` la lance tout seul si `cache\ui_layout.json` manque et que `cache\il2cpp\dump.cs` existe. Sans ce fichier, la visionneuse garde ses fenêtres simplifiées (`--ui-simple` les force).
- **Disposition 16:9** : la colonne portrait est centrée et mise à l'échelle H/800 (`--ui-pos centre|droite|gauche`) ; même champ de vision vertical que l'original, donc les monstres restent dans la bande libre entre le bandeau du haut et les fenêtres du bas.
- F1 affiche / masque les lignes d'infos (depuis #15 : lieu, fenêtre, performances, réglages choisis ; cadre translucide, repliées dans la marge gauche pour ne pas couvrir le bandeau des personnages).
- **Fenêtre de message d'origine** (`FenetreMessage`, `Rendu.maj_canevas`) : cadre `frameData`, canevas 512 x 512 du moteur avec défilement par décalage d'UV, curseur ▼ ; remplace l'ancienne boîte bleue. Absente du `ui_layout.json` d'avant le 30/10 soir : `lancer_dq4.bat` le refait automatiquement.
- **Visibilité** : une fenêtre n'est dessinée que si le moteur la demande à l'image courante (voir notes techniques) ; plus de fenêtre « Combattre » derrière le menu de commandes. Plaques de nom de monstre (type 31) dessinées au-dessus des monstres.
- Test en cloud : `DQ_UIDBG=1` journalise les messages des fenêtres (ports 0, 1 et >= 12), l'état des fenêtres et les lignes du canevas de message.
- Limites : voir « Lacunes » dans les notes techniques (classes `IBase` personnalisées, type 66, curseur de liste). Le texte d'action sous le bandeau des personnages (« Attaquer / ▼ / cible ») s'affiche sans cadre propre.

## Saisie : clavier et souris (30/10/2026, #38 #39)
- **Souris = tactile du mobile** : appui sur un bouton du menu actif (il s'enfonce), relâchement sur le même bouton = sélection ; clic gauche sur le message = page suivante ; clic droit = Annuler (B). Les zones sont celles du jeu d'origine (`Fenetre.boutons()`), le bouton le plus en avant prime.
- **Clavier** : flèches (gauche/droite comprises) déplacent le curseur dans les grilles de menus ; une seule colonne : gauche/droite = page précédente/suivante ; Entrée = valider, Retour arrière / X = annuler. Menus du moteur à grille (Oui/Non, combat) : les flèches sont transmises au moteur ; menus tactiles : curseur local d'après la position des boutons.
- **Fenêtre de message du terrain** descendue en bas de l'écran (`--msg-origine` pour l'ancienne position), Oui/Non avec elle ; textes colorés `@cN`.
- Tests sans écran : `--clics "image:x:y[:d],..."` (pixels depuis le haut gauche, d = clic droit ; appui à l'image, relâchement 3 images plus tard).

## Sprites du terrain (30/10/2026, #40)
- Sprites cachés / montrés par le moteur (paquet 14) respectés ; fondus d'apparition par la couleur alpha (paquet 13, déjà en place) ; bulles « ! » au-dessus des villageois (paquets 19/20, feuille d'icônes des menus, nécessite `cache\ui_MenuTexture.png`, créé avec les fenêtres d'origine). Ombres sous les personnages, personnages couchés et icônes sur la carte du monde : pas encore.

## Avancées du 31/10/2026 (dépôt `dq4-portage`, PR #1 à #10)
Retours d'essai sur kpl-031, traités un par un ; les détails techniques (sources classe / méthode, adresses) sont dans `notes-technique-portage-dq4.md`.
- **Données dans le dépôt (#1)** : les APK et sauvegardes sont lus dans `jeux\DQ4\` du dépôt (`patched_apks`, `saves`) ; plus aucune dépendance aux autres projets.
- **Villes (#2)** : caméra comme Unity, personnages de face à l'écran, plus de silhouette derrière le décor. **Portes, jarres, tonneaux (#3)** animés comme dans le jeu (paquets 2 à 5 et 7, tables FCAN / FPMV / FSEQ ; `objets_carte.py`).
- **Carte du monde (#4)** : fenêtre des lieux élargie pour le 16/9 (les sprites apparaissent dès qu'ils sont en partie à l'écran), icônes de lieu 19 et 20. **Eau animée (#9)** : motifs de tuiles de `Field.UpdatePattern`, pas toutes les 17 images (mise à jour sur place des UV).
- **Menus (#5, #6)** : le survol de la souris sélectionne le bouton comme les flèches ; texte ancré en bas du bouton, tri par profondeur entre fenêtres, interface agrandie de 12 % (`UI_ZOOM`).
- **Début de combat (#7)** : effet d'écran d'origine (`Capture.BattleEffect` : l'écran se brise en 32 colonnes de morceaux et tombe, puis noir) ; le moteur attend sa fin (bit 1 du mot de drapeaux) ; écran noir jusqu'au chargement du combat (plus de flash de la mauvaise carte). Test : `--shots-effet "1,20,40"`.
- **Son (#8)** : jingles avec reprise de la musique précédente (`0x1000 | n`), arrêt seulement pour les valeurs >= `0x4000`, 14 bruitages en boucle jusqu'à l'ordre d'arrêt.
- **Cache et fondus (#10)** : préparation du cache en arrière-plan (cartes, sprites, monstres ; ~340 Mo, une fois, ~2 min ; `--sans-preparation` pour les tests), plus de gel à la première carte inconnue ; le bit 0 du mot de drapeaux (« fondu en cours ») est maintenu jusqu'à la fin du fondu (auberge, titres de chapitre, écran de chargement, menus pendant un fondu).
- **Reste** (mis à jour en #17) : animations de matériaux (SRA, 26 cartes) et animations d'événements (FEAN / paquet 6), événements FEMV, effets d'écran 3 / 5 / 6 (voyage, lampe sombre, Riremito) non rejoués, écran de choix de sauvegarde (menu de chargement d'origine), clignotements d'écran à reconfirmer sur PC.

## Reste à faire
Le reste à faire est suivi par les **issues GitHub de `dq4-portage`** (https://github.com/Sylfried/dq4-portage/issues : #51 à #99, #101, #105, #107 à #112, #121 à #123, #126 à #131, #134 à #141 et #145 à #146, jalons 1 à 5 ; 60 ouvertes au 03/11/2026). Décisions de Sylfried : `docs/audit/decisions.md` (§ 5c, 5d et 5e, D-149 à D-225). **Décidé, pas encore codé (D-197 et D-201, #101)** : le réglage « Vitesse de transition » va être retiré ; seules les transitions de porte et de carte seront raccourcies, à x4 fixe, reconnues à leur bruitage (la vitesse de marche, la caméra et l'accélérateur Maj ne changent pas) ; les passages de ces notes qui décrivent « Vitesse de transition » décrivent donc l'état actuel, pas la cible. État des lacunes : `docs/audit/lacunes_connues.md`. Points non vérifiés : `docs/audit/rapport_reste_a_faire.md` (« Lecture du 03/11 »). Contexte pour reprendre : `docs/reprise.md` §6. **Les rubriques « À trancher » et « Non vérifié » plus bas sont datées** : celles de #45 à #50 ont été tranchées ou reprises par la lecture du 03/11 (voir § 5d).

## Monstres de combat et mode F2 (30/10)
- Les textures de monstres (`m<id>`, effets compris) suivent le mode de sprites F2 : original (pixels nets, filtre `net`) ou agrandi par l'algorithme HD choisi (`_texture_monstre`, calcul en tâche de fond, l'original sert en attendant ; cache disque `hd_<algo>_v<n>_m<id>.npy` ; plafond 4096 px de côté, moins de passes sinon ; mipmaps à 2 niveaux).

## Mode « pixel perfect » (F2, dernier mode ; `--hd 4`, 30/10/2026, #41)
- « Originaux (pixels nets) » garde un adoucissement d'un demi-pixel aux frontières des texels et, sur la carte du monde, une taille de héros de 1,04 x l'original : ce n'est pas du pixel perfect. Le dernier mode de F2 l'est vraiment : **plus proche voisin strict** (`net = 2` dans le shader) pour les sprites, monstres, icônes ; **carte du monde à échelle entière** (k pixels d'écran par pixel de la carte, **k ∈ {1, 2, 4, 8}** (31/10, `PP_ECHELLES`) : le plus proche, à l'échelle logarithmique, de `hauteur / (CH_VUE_HAUT x 16) x zoom`, soit x2 en 720p et x4 à 1094 px de haut ; la molette passe à l'échelle suivante ou précédente) ; **caméra calée sur un pixel de la carte** (le défilement se fait par pas de k pixels d'écran, comme sur le jeu d'origine), positions des sprites et des icônes de lieux arrondies au pixel, héros à 24 x 32 exactement, tuiles sans recul d'UV (les centres des pixels d'écran ne tombent jamais sur un bord de texel). Vérifié en capture : 100 % de blocs k x k uniformes (k = 2 et 3) sur la carte, défilement compris.
- Ville et combat sont en perspective : l'échelle n'est jamais entière, le mode donne seulement des texels nets sans lissage. Les fenêtres d'interface (échelle H/800) ne sont pas concernées.


## Son (`son.py`, F8, 30/10/2026, #42)
- Le module `son.py` lit les `.akb` directement dans l'APK de données (rien n'est copié), les décode (MS-ADPCM en numpy, Ogg via le module `soundfile`) et les joue avec `pyglet.media` : une musique à la fois avec **boucle à l'échantillon près** (source maison `SourceBoucle`), jusqu'à 24 bruitages en parallèle. Le décodage se fait en tâche de fond (0,3 à 0,7 s pour une musique) ; les bruitages décodés sont mis en cache dans `cache/son_SExxxx.npz`.
- `moteur.Etat` mémorise les paquets 35 / 36 / 37 (`sons`, et `musique` = dernière musique demandée) ; la fenêtre les transmet à `Son` à chaque image. Au chargement d'une sauvegarde, les bruitages perdus sont ignorés mais la musique de la carte est gardée.
- **F8** coupe / remet le son (la musique en cours reprend). Options : `--sans-son`, `--volume-musique` (0,7), `--volume-bruitages` (0,8) ; ils multiplient le volume propre à chaque fichier.
- `lancer_dq4.bat` installe `soundfile` (une seule fois, y compris dans un environnement déjà créé : `.venv\sound_ok.txt`). Sans lui, les musiques sont absentes (message au démarrage) mais les bruitages restent actifs.
- Test sans carte son (cloud) : `PYGLET_AUDIO=silent` ; `DQ_SON=1` journalise les ordres reçus du moteur et les bruitages joués.
- Le rendu réel (haut-parleurs) n'est vérifié que sur ton PC : décodage et boucle sont validés par comparaison avec ffmpeg et par test de la source.

## Boucle à pas fixe, zoom commun, scintillements (31/10/2026, #12)
- **Cadence** : le moteur d'origine tourne à **30 pas par seconde** (`Boot` fixe `Time.fixedDeltaTime = 1/30` ; `MainLoop.Update` appelle `NativeManager.Update` une fois par image rendue, Android limite Unity à 30 images/s ; `MainLoopEx.FixedUpdate` ne sert qu'aux appareils sans NEON, `Boot.s_useFixedUpdate = IsNotNeonSupport()`). Avant, la visionneuse planifiait `tick` toutes les 1/30 s dans l'horloge pyglet pendant que le dessin tournait à part (60 Hz) : le nombre d'images affichées par pas variait (1, 2 ou 3) et le rythme moyen baissait quand une image était lente, d'où des saccades et une marche plus lente que sur mobile.
- `Jeu._boucle` (exécutée avant chaque dessin, `pyglet.app.run(interval=0)`, le dessin suit la synchronisation verticale) : accumulateur d'horloge réelle, **un pas de moteur par 1/30 s** (tolérance de 15 % pour qu'un écran de 60 Hz fasse un pas toutes les 2 images exactement, au plus 3 pas de rattrapage, un blocage plus long est oublié). **F4** affiche les pas de moteur par seconde (doit rester à 30,0).
- **Interpolation** (`_instantane`, `_interpoler`, `on_draw` → `_dessiner`) : positions des personnages et de la caméra (carte du monde : `champ['cam']` ; villes : `cam_pos`, `cam_cible`) calculées entre le pas précédent et le pas actuel (alpha = fraction du pas), donc un mouvement continu à toute cadence d'écran (60, 75, 144 Hz) avec un pas de retard. Pas d'interpolation en combat (les monstres sont des maillages envoyés à chaque pas), ni au-delà d'un saut (24 px sur la carte, 1,5 unité en ville), ni à un changement de carte. En pixel perfect, héros et caméra sont arrondis à partir des mêmes valeurs interpolées : l'écart héros / caméra reste constant (vérifié : toujours (0, 2) px de carte).
- Mode capture de test (`--shot`) : un pas par image affichée, sans horloge ni interpolation (reproductible).
- **Zoom commun** : `HEROS_FRAC` ≈ 0,1026 = hauteur du panneau du héros (1,44 unité de ville, 32 px sur la carte) / hauteur de la fenêtre, mesurée dans les villes en 16/9 (caméra d'origine, 39,55 de la cible dont 4 d'avance, fov 9,5 x 4/3 sur l'écran 0,5625). `CH_VUE_HAUT = 32/16 x CH_ECHELLE / HEROS_FRAC` ≈ 20,2 tuiles sur la carte du monde ; dans `_camera_ville` (hors caméra libre des scènes) le champ vertical est recalculé pour que le héros occupe `HEROS_FRAC` quelle que soit la distance ou le fov de la ville, de la grotte ou de la tour (sauf quand le jeu tient la caméra dans une scène : depuis #244 son champ s'applique tel quel, voir « Avance #244 »). (Inversion stricte des tuiles du portrait : 16 de haut sur la carte, soit HEROS_FRAC ≈ 0,13 : une seule constante à changer.)
- **Scintillements corrigés** : (1) au retour d'une fuite, une image montrait le décor du combat avec la caméra d'une ville (partie = carte du monde mais `champ` pas encore reçu, carte = `btl_*`) : noir tant que la scène suivante n'est pas là ; (2) les lignes d'aide (haut à gauche) disparaissaient pendant l'effet de début de combat et les écrans noirs : `_dessiner_aide` les dessine aussi dans les sorties anticipées ; (3) la grille de tuiles de la carte du monde gardait une taille variable et était recréée (suppression + création côté GPU) toutes les ~20 images de marche : largeur constante, sommets remplacés sur place (a-coups de dessin /2). Méthode : captures de toutes les images d'une séquence + détecteur « image différente puis retour à la précédente » (`pixels changés(i, i+1)` et `(i+1, i+2)` grands, `(i, i+2)` petit) sur un combat (début, attaques, fuite) et un changement de carte.

## F2 / F3 / décors, correctif du filtre « net » (31/10/2026, #13)
- **F2 = sprites ET décors.** Le cycle est : Originaux (pixels nets) → EPX x8 → Pixel perfect (depuis #41 ; il comptait avant Régions lissées et Bicubique). **Sur la carte du monde, le mode Pixel perfect compte en plus x1, x2, x4, x8** : chaque appui sur F2 passe à l'échelle suivante (comme la molette) puis revient au premier mode ; l'échelle de départ est x1. En ville et en combat (perspective), Pixel perfect = texels nets sans échelle entière (rien à choisir).
- **Décors de ville et de combat** (`_decor_hd`, `_tracer_decor`) : les modes agrandis (EPX ; avant #41 aussi régions / bicubique) s'appliquent aussi au décor. Les textures du décor (256 px en combat, 8 à 128 px en ville) sont agrandies dans la tâche de fond (jointures en enroulement, plafond 4096 px, 8 jeux gardés au maximum) ; le décor d'origine s'affiche en attendant. **Correctif (#14) : en « Originaux » et en pixel perfect, le décor garde son rendu d'origine lissé** (mipmaps + anisotrope ; le plus proche voisin strict donnait des texels géants sur les montagnes et l'herbe de combat, jugé « bizarre ») ; seuls les sprites, monstres et la carte du monde passent en pixels nets. **Pixel perfect est le mode par défaut** (`--hd 4`).
- **F3 = lissage des textures** (`lissage`, `_filtrer`) : agrandissement LINEAR si oui, NEAREST si non (réduction toujours en mipmaps + anisotrope). Il agit sur la carte du monde, les décors et les sprites (hors pixel perfect, où le filtre est toujours « plus proche voisin »). Avant, il ne touchait que les textures de la ville déjà chargées et ne changeait rien dans les autres cas.
- **Correctif du mode « net » (`net = 1`)** : la référence du filtre « bilinéaire net » était le **centre** du texel au lieu de sa **frontière** : environ 72 % de chaque texel était un mélange 50/50 avec le voisin (image molle, y compris pour les sprites en « Originaux »). Elle est maintenant la frontière la plus proche (`b = floor(p + 0.5)`), et le niveau de mipmap vient des dérivées de l'UV d'origine (`textureLod`) pour ne pas flouter les bords des texels des décors à mipmaps.
- **Carte du monde** : l'atlas `field` (1024², 64 x 64 tuiles de 16 px) est recopié dans un atlas avec **gouttière de 2 px** par tuile (bords répliqués, 1280²) : plus de bavure entre tuiles voisines avec LINEAR / bilinéaire net. Les icônes gardent la texture d'origine (`champ_tex_ico`).
- **Caméra** (question « comme sur mobile ? ») : position et angles viennent des paquets du moteur, la projection est celle de `SceneCamera.Update` : ville = champ horizontal fixe (fov x 4/3) sur l'écran portrait 0,5625 ; carte du monde = orthographique vue de dessus, nord en haut (`Field.Init`). **Combat** : la caméra d'origine ne remplit pas l'écran du mobile, `Global..cctor` lui donne une zone de **42 % de la hauteur** de l'écran (`InitParam` : `viewH` = 0,42, `viewY` = `NotchFix.BattleCamAdjustmentValue`, `yOffset` 0,04), soit un rapport 0,5625 / 0,42 ≈ 1,34 = 4:3 (la vue de la DS) : d'où le champ vertical de 50,25° de `_camera_combat`. En 16/9 la visionneuse garde ce champ vertical et montre plus de décor sur les côtés (79° au lieu de 64° en horizontal). Pas de comparaison pixel à pixel avec une capture de téléphone réelle.

## Menu Échap, réglages, touches, états instantanés (31/10/2026, #15)
- **Seule touche fixe : Échap (menu)** (depuis #25 ; F1 = infos à l'écran est une action réattribuable). F2/F3/F4/F5/F7/F8/F9 ont disparu : tout est dans le menu (`pause.py`, classe `Pause`) ; F5 = option `--force-champ`, F7/F9 = variables d'essai (`DQ_CB`...), F8 = réglage « Son ». Pendant le menu, le moteur et le son sont à l'arrêt (`Jeu.pause_jeu`, `Son.mettre_en_pause` décale les fins de musique) et la scène reste affichée, assombrie ; navigation aux flèches / touches réglées (haut, bas, gauche, droite, A, B) ou souris (survol, clic, curseurs, clic droit = retour, molette).
- **Réglages** (`reglages.py`, `reglages.json` à côté de `fenetre.py`, ignoré par git) : shader (0..4), zoom (depuis #26, en pourcentage de 40 à 400 %, indépendant du shader ; depuis #27 : `distance_camera`, 50 à 200 %, l'ancien `zoom` est converti ; avant : distance d'affichage x1 / x2 / x4 / x8 en #25, échelle pixel perfect et zoom de la carte avant #25), lissage, plein écran, anticrénelage (au prochain lancement), infos à l'écran, son et volumes, touches. Les options de ligne de commande (`--hd`, `--msaa`, `--carte-zoom`, `--volume-*`) priment sur le fichier pour la session.
- **Touches** : deux touches par action (`TOUCHES_DEF`), capture dans le menu (Échap annule, Suppr efface, Échap seule non réattribuable ; une touche déjà prise est retirée de l'ancienne action). `pad()` lit les actions : haut / bas / gauche / droite / A / B = bits du pad du moteur ; X et Start (depuis #26 : Entrée) = ouvrir le menu de commandes sur le terrain (BTN_MENU 0x800) ; L / R = gauche / droite dans les menus (page précédente / suivante). Y (0x1000) ouvre la fenêtre de type 25 « ma_map1 » (carte de la ville), que la visionneuse ne sait pas dessiner : non transmis. Start / Select / FL / FR (0x2000, 0x4000, 0x40, 0x80) n'ont aucun effet dans le moteur.
- **États instantanés** (`etats.py`) : mémoire du moteur (tas 2,4 Mo, données et TLS de 64 Ko, pages de la bibliothèque modifiées par rapport à `elf.img`, pointeurs du chargeur) + état Python (`Moteur.etat`, `ui`, images, animations, messages, grille...) + état de la visionneuse (objets animés de la carte, eau de la carte du monde). Fichier `DQ4ETAT1` : JSON d'infos + miniature PNG + pickle zlib (~ 250 Ko), dans `<sauvegardes>/etats/etat_NN.dqs`. Aucun fichier du jeu dedans, mais un état ne se recharge qu'avec l'APK qui l'a produit. `Interface` garde `ints` et `dispo` pour que `Gestionnaire.rejouer` reconstruise les fenêtres d'origine après un chargement. Vérifié : rechargé dans un nouveau lancement, le jeu redonne exactement la même image (ville, carte du monde avec menu de commandes ouvert, combat ; au plus 1 niveau d'écart sur 91 pixels en combat).
- **Liste blanche de classes (depuis #242, audit ENG-05)** : `etats._Depickler.find_class` n'accepte que `Etat` et `Interface` du moteur, les types de base, les tableaux numpy (`numpy.core` et `numpy._core`) et `OrderedDict` / `defaultdict` / `deque` ; tout autre nom (`os.system`, `eval`, `subprocess`, `Moteur`, nom pointé) fait refuser le fichier (`UnpicklingError` en français, rien n'est exécuté). `lire` ne décode que le conteneur externe (octets) ; `appliquer` refuse avant d'écrire dans le moteur (#206). États relus sur de vrais états : ville, carte du monde, combat.
- Options d'essai : `--touches-test "n:NOM,..."` (touches, `+NOM` / `-NOM` maintenue / relâchée, `@x@y` clic, `cN+k` = k images de boucle après N images de combat) et `--shots-boucle "n,..."` (captures `<shot>_b<n>.png`, la dernière quitte), `--reglages` pour ne pas toucher au vrai fichier.

## Combat : boîte de message, mise en page des menus (31/10/2026, #16)
- **Boîte de message du combat** descendue à la position du menu de commandes (`CB_MSG_BAS` = -338 en coordonnées d'interface, zone `CB_ZONE_MENUS`) ; `--msg-origine` garde la place d'origine (portrait).
- **Mise en page des menus** (`outils/ui_il2cpp/`) : la langue du jeu est réglée avant la lecture des textes (`menusys.regler_langue`), `GENERATION = 2` dans `entete.py` (3 depuis l'audit de fidélité du 01/11/2026 : voir la dernière section ; tampon `gen` de `cache/ui_layout.json` : une mise en page plus ancienne est refaite au lancement par `lancer_dq4.bat`, une seule fois, quelques minutes). Boutons à texte centré (`ui_menu.py`, `NameButton`).

## Animations de décor : eau, lampes, palettes (31/10/2026, #17)
Cause du « il manque l'eau dans les grottes » : la visionneuse n'avait jamais joué les animations qui tournent **sans ordre du moteur** (`FldObject.Update` : `update_seq`, `update_pmv`, `update_plp`). Trois sources sont maintenant rejouées :
- **Séquences de maillages automatiques** (FMAP `seq_obj_id` à l'offset 64 → entrée de FSEQ ; 8 courts : objet, séquence, groupe, délai de départ, délai entre deux tours, nombre de tours (-1 = sans fin), valeurs initiales) : les images de chaque sous-maillage sont les enfants `sNN_*` du modèle (la valeur d'une clé = indice de l'enfant, `GetChild`) ; sommets, **UV et couleurs** sont interpolés entre les deux clés (`seq_build_mesh`). C'est ce qui fait défiler l'eau des bassins (UV décalés de 0,5 sur 1000 images, en boucle) et vaciller les lampes (`akari2a` : 6 cases d'atlas en 24 images). Entrées dont `_repeat_num` = 0 : jamais lancées seules (pilotées par commande).
- **Mouvements automatiques** (FMAP `pmv_id` à l'offset 66 → FPMV) : objets qui bougent en continu (drapeaux, flammes...), mêmes règles de délai et de tours.
- **Palettes animées** (FPLP : nom, FPAM, événement, objet ; FPAM : clés avec durée en 1/60 s + palette) : les surfaces concernées (eau scintillante, marais empoisonné, sols qui blessent) reçoivent la texture de la clé courante (`pam/<nom>.NNN` du paquet de données : `wtkira1`, `doku00`, `doku01`, `dpkk1b`, `hcneon1a`, `tz_damg01`, `tz_kifkyk1`, `dpout`...). `Donnees._groupe_pam` sépare ces surfaces en groupes `('pam', nom, id, événement)` ; `PalettesCarte` (dans `objets_carte.py`) donne l'image courante ; une animation liée à un événement (numéro >= 1) reste à l'image 0 tant que l'événement n'est pas en cours.
- Correction au passage : l'indice des images d'une séquence de maillages était décalé de 1 (images = [base, s00...]) ; il utilise maintenant les enfants seuls (jarres et tonneaux qui se brisent vérifiés : les morceaux s'écartent puis se posent).
- **Cache `carte4_<nom>.pkl`** (était `carte3`) : la première fois, toutes les cartes sont préparées de nouveau en arrière-plan (~1,5 min, le jeu reste jouable) et les anciens `carte[0-3]_*.pkl` sont supprimés (`_purger_anciens`).
- **États instantanés** : `objets_auto` (délai / tours restants) et `palettes` (image, clé) sont enregistrés et rechargés. Vérifié par comparaison : un état rechargé évolue exactement comme l'original (écart 0 après 40 images).
- **Coût** : mise à jour par pas de 30 Hz, `_poser` optimisé (tableaux d'origine, clés de mouvement et matrices de rotation en cache) : au pire 2,3 ms par pas sur la carte la plus chargée (52 objets animés), contre 6,6 ms avant l'optimisation ; résultat identique au calcul d'origine (écart 0). 670 cartes extraites sans erreur ; 61 cartes ont des palettes animées, 480 des objets automatiques.
- **Essais** : `DQ_CARTE_TEST="nom;x,y,z;cx,cy,cz"` montre une carte avec une caméra fixe (partie sans combat ni carte du monde), `DQ_ANIM_TEST="objet:numéro:image"` lance une animation commune à cette image de boucle ; avec `--shots-boucle`.
- **Pas rejoué** : animations de matériaux (SRA, couleur de matériau animée), animations d'événements (FEAN / paquet 6), clé de palette quand `event_id` >= 1 (reste à l'image 0).
- **Dégâts sur les ennemis** (corrigé en #18) : le jeu d'origine en affiche bien (voir « Boutons, carte, dégâts » plus bas) ; l'affirmation « code mort » de cette ligne était fausse.

## Boutons mobiles, carte, nombres de dégâts, options (31/10/2026, #18)
- **Boutons de la version mobile** (`hud_mobile.py`, classe `Boutons`) : le jeu d'origine les dessine dans la couche Unity (`TouchPad` : « Map Button » = touche 0x1000, « Command Button » = 0x800, « Talk Button » = 0x400 = discussion de groupe ; 0x100 = parler / examiner). Icônes 3, 4 et 15 de la feuille MenuTexture (rangée de 32 px à y = 224). Visibilité : le moteur écrit `Global.Flag` dans le premier mot de sa sortie (`Moteur.drapeaux()`) ; boutons visibles si `(Flag & (8 | 0x30047)) == 8` (pad présent, ni verrou du joueur, fondu, effet d'écran, interface verrouillée, pause), la Carte exige en plus le bit 0x20. Positions sur une grille de 32 x 18 cases proportionnelle à la fenêtre (`boutons_pos`, coin supérieur gauche ; aimantation facultative) ; édition par glisser-déposer dans le menu Échap (le moteur reste arrêté). Le pad directionnel et la barre de rotation de caméra de l'original ne sont pas reproduits (clavier).
- **Entrées du terrain** (`tick`) : le moteur veut un seul bouton à la fois dans `decl` : A -> 0x100, puis bouton à l'écran, puis Entrée -> 0x800, Espace -> 0x400, M -> 0x1000. Entrée et Espace valent A quand un message est affiché ; M ferme la fenêtre de carte. Retour arrière / clic droit n'ouvrent plus le menu (le mobile n'a pas de bouton B).
- **Fenêtre de carte** (type 25 `Make_CityMap`, `ICityMap`) : le moteur envoie sur un port dynamique le nom de la texture (`dsdq4wmap01` pour la carte du monde, `<ville>_map1`...), puis `[12,1,x]`, `[12,2,y]` (marqueur, en pixels du plan de 256 x 192). Le plan est affiché en 450 x 337,5 sous le cadre (`Rendu._carte`) et l'icône du marqueur (nœud 1527) est centrée sur `(x, y)`. Les textures `*_map*` sont préparées avec le cache (`liste['plans']`). Pas fait : les pièces `MAP_DIFF` (parties du plan découvertes ou non).
- **Nombres de dégâts** (type 43 `Make_BattleHoppingNumber`) : `BattleActorAnimation::setResultAnimation` appelle `BattleMenu_setHoppingNumbers(monstre, hauteur, dégâts)` quand la cible est un monstre et que les dégâts sont >= 1 (rien pour les héros, les soins, les esquives). Messages : port 0 `[p,1,cat,43]`, puis sur le port `[12,0,0]` suivi de `[monstre, hauteur, dégâts]` (le numéro du monstre en `a[0]` était pris pour une commande : `Interface.appliquer` l'intercepte, `Interface.degats`). Côté Unity : `HoppingNumber.Create` à la position du maillage du monstre projetée par la caméra, plus `min(hauteur x 1,85 ; 160)` unités d'interface. Quatre chiffres au plus (feuille MenuTexture, PartsInfo[11], cellules de 16 px en (576, 288)), 2 ticks de décalage entre chiffres, chaque chiffre visible 19 ticks (1 tick = 1 image du moteur) avec un saut de 0, 4, 6, 6, 4, 2, 0, 2 unités. Taille du glyphe non mesurée sur le mobile : réglage « Taille des nombres de dégâts » (160 % par défaut ; option retirée du menu en #27, la valeur 160 % reste en dur dans `reglages.DEFAUT['taille_degats']`). Essai : `DQ_CALLHOP="image:monstre:hauteur:dégâts"` appelle la fonction du moteur.
- **Coffres** : l'origine du modèle `tbox01/02` est la charnière (bord supérieur du coffre) et les cartes la placent à 0,5 **sous** le sol : tous les coffres étaient enfoncés d'une unité (vérifié sur 164 coffres de toutes les cartes : bas du modèle = sol - 1). `donnees._extraire_carte` relève leur origine de 1 (cache `carte5_<nom>.pkl`). **Explication corrigée en #22 : c'était le signe de Y de toutes les positions d'objets, pas un défaut propre aux coffres.**
- **Préparation du cache dans un processus à part** (`python donnees.py <paquet> <cache>`, priorité basse) : dans un thread, ses extractions en Python pur prenaient le verrou de l'interpréteur (GIL) et saccadaient le jeu pendant la première minute. Le processus s'arrête quand l'entrée standard se ferme.
- **Options** : résolution de 720p à 4K, angle de la caméra des villes (-20 à +40 degrés), vitesse de déplacement et course (touche maintenue, facteur réglable : le pas du moteur est accéléré tant qu'une direction est tenue, l'animation de marche suit), curseurs réglables à la souris (glisser) ou en tapant la valeur, sens de la molette des menus inversé, plus de message « touches par défaut rétablies » (il décalait l'interface), erreur `'Jeu' object has no attribute 'pause'` corrigée (la souris bougeait avant la création du menu), raccourcis d'états (1 à 9 et 0 enregistrent, Ctrl + chiffre charge, Ctrl + Maj annule le dernier chargement).

## Décor : eau, ombres douces, ombres des personnages (31/10/2026, #19)
- **Cause commune de l'eau « électrifiée » et des ombres brutes ou absentes** : la visionneuse ignorait le `_Color` des matériaux de carte et dessinait tout le décor opaque (cutoff 0,5, profondeur écrite). Le jeu choisit le shader à l'exécution (`FldObject.set_shader`, RVA 0xCD5414) : nom de texture sans `.tim` **ou** `_Color.a != 1` -> `Custom/fld_trans` (Blend SrcAlpha / OneMinusSrcAlpha, ZWrite off, ZTest LEqual, file 3000 + `prio`, `FldObject.set_priority`) ; sinon texture RGBA32 -> `fld_atest` (rejette alpha == 0) ; sinon `fld_normal`. Couleur finale = texture x (couleur de sommet x `_Color`).
- **Eau des grottes** : les modèles `<carte>wt..` (texture `mawater1.tim`, cyan (54, 205, 203)) ont `_Color` = (1, 1, 1, 0,2) : traçés à alpha 1 ils donnaient un cyan plein. Mesuré dans `dgb1` : (38, 141, 140) -> (29, 87, 93). Les palettes `wtkira` n'existent que dans les cartes de plein air et de ville, pas de blend additif.
- **Ombres du décor** (`idokage1` des puits, `maokage1`, `*kg*`...) : textures `.tm2` à alpha faible (`kage1c` {0, 14, 28, 42, 86}...) rejetées par le cutoff 0,5 (puits, bâtiments... sans ombre : 51 cartes sur 670) ; textures `.tim` à alpha binaire avec `_Color.a` = 0,4 ignoré (noir à 100 %, « brutes »). `donnees._texture` renvoie `_Color` et le genre, `cuire` multiplie `_Color` dans les couleurs de sommet, groupes `('tr', prio, clé)` tracés après les opaques triés par `prio`, profondeur en lecture seule. Cache `carte6_<nom>.pkl`.
- **Ombre des personnages** (`_dessiner_ombres_chara`, villes et donjons) : `Chara.s_shadowMesh` (carré +-1 en XZ à Y = 0,00625), échelle `s_shadowDefScale` (0,347 ; 10 ; 0,206), texture `CharaTex/common` (ellipse noire d'alpha 96 / 255, bord net), shader `Custom/CharaShadow` (file 2999), position = personnage décalée de 0,25 le long du rayon de la caméra, à plat (lacet seul). Le moteur n'envoie pas le paquet 15 (`chara_shadow`) en ville : l'ombre par défaut s'applique à tous. La visionneuse garde taille et opacité d'origine mais **adoucit le bord** (dégradé au lieu du bord net). Pas fait : carte du monde (vue de dessus, `SetFieldShadowPosition`), paquet 15, ombre masquée pour les feuilles 193 / 194.

## Combat : vibration, clignotements, boîte de message à 3 lignes (31/10/2026, #20)
- **Vibration des ennemis à l'apparition et clignotements des animations : une seule cause.** Les sommets des monstres et des effets étaient envoyés au GPU **avec un tour de retard** : pyglet ne fait que marquer le tampon « sale » (`vl.position[:] = ...`), l'envoi se fait dans `buffer.commit()`, appelé par `_tracer` seulement quand le domaine change ; `_dessiner_scene` liait le domaine pour le décor, puis `_maillages_combat` réécrivait les sommets sans nouveau `commit` : les monstres sortaient avec les données de l'image précédente. Le moteur tourne à 30 Hz et l'affichage à 60 Hz (2 tracés par pas) : un tracé sur deux était périmé, d'où le va-et-vient pendant le travelling d'entrée (52 inversions de sens sur 60 images) et les sauts des attaques et des sorts. Correctif : `_dom_lie = None` après `_maillages_combat` (mesuré sur un combat de 687 pas : tracé 1 et tracé 2 identiques sur 687 pas contre 415 différents avant). Risque latent non visible : l'ordre de tracé de monstres de même file bascule sur des écarts de profondeur de 1e-3 à 1e-5 (`out.sort`, clé stable possible : file, profondeur arrondie, emplacement).
- **Boîte de message du combat** : sa géométrie vient du type de fenêtre choisi par le moteur (`[0, n]` du port 1, `ui_layout.json['message']['types']`) ; le début de combat envoie le type 1 (cadre de 188 unités, canevas de 4 lignes de 34) alors que le terrain (type 0) fait 126 unités (3 lignes). `trois_lignes` (ui_menu.py) ramène le type 1 à la hauteur du type 0, bord bas inchangé (la distance au bord reste celle de `CB_MSG_BAS`) ; le cadre d'origine reste disponible (type 4) et sert quand le canevas contient une 4e ligne (4 groupes de monstres). Mesuré à 1280 x 720 : 160 px -> 104 px, bas à 60 px du bord.


## Réglages, ombres, grande carte du monde, coffres (31/10/2026, #21)
- **Volumes** : musique et bruitages à 100 % par défaut (`reglages.DEFAUT`, `son.py`). Chaque curseur du menu Échap a un bouton carré ↺ à sa gauche (doré quand la valeur diffère du défaut, gris sinon) ; la touche Suppr remet à la valeur par défaut le curseur sélectionné (`Pause._curs(..., defaut=RG.DEFAUT[clé])`, `zones_def`).
- **« Aura » autour du héros qui masque les compagnons** : `_dessiner_ombres_chara` laissait `ZWrite` coupé, `ZTest = LEQUAL` et le seuil `cutoff` à 0 ; le panneau (transparent) du personnage suivant, tracé sans rejet des pixels transparents, écrivait la profondeur sur tout son rectangle et cachait les sprites derrière. Le tracé des ombres remet maintenant `ZWrite`, `LESS` et `cutoff = 0,05`.
- **Ombres des personnages** (paquet 15, `cmd_chara_shadow`, `0xD13150`) : `v & 0xff` = personnage ; bits 8-9 visible (bit 8), 10-11 ombre séparée (bit 10), bit 12 position de l'ombre (3 flottants), bit 13 alpha (flottant), bit 14 position d'ombre sur la carte du monde (3 flottants). `Moteur` les mémorise dans `sprites[idx]` (`ombre`, `ombre_sep`, `ombre_pos`, `ombre_a`) ; les villes les respectent (ombre masquée ou déplacée comme le jeu). Carte du monde : `Chara.SetFieldMode` (`0xCCD660`) met l'ombre à l'échelle `(0,347 ; 10 ; 0,206) x 28,8`, tournée de 36° (le personnage à 51,84) et `SetFieldPosition` la pose en `(x, -1, -y)`, au même `x, z` que le personnage : `_dessiner_ombres_champ` dessine une ombre douce aplatie sous chaque personnage de la carte du monde, seulement quand le jeu la montre (paquet 15). **Non vérifié visuellement contre le mobile** (le code montre positions et masquage ; on n'a pas déterminé si les tuiles la recouvrent).
- **Grande carte du monde** (type 26, `Make_WorldLargeMap`, cadre 1505, marqueur 1526) : `LoadLargeWorldMap(flag)` (`0xCF10B0`) compose un plan de 1024 x 1024 : fond `dsdq4lmap0_1024` (TextAsset, RVB brut, haut en premier) + pièces `P<bit>_<x>_<y>_<largeur>` (`MAP_DIFF.CheckSet`, `0xD08444` : si `flag & (1 << bit)`, les lignes de la pièce sont copiées en `(x, y)`). Le moteur envoie le drapeau en indicateur 0, la position du héros en indicateurs 1 et 2 (`(12,0,flag)`, `(12,1,x)`, `(12,2,y)`, pixels du plan) ; la fenêtre ne montre qu'un rectangle de 256 x 192 pixels centré sur le héros (décalages de texture `x/1024 - 0,125` et `(y-1024)/1024 - 0,09375`), le marqueur (la plume) reste au centre. `Donnees.plan_monde()` (cache `plan_monde.npz`), `Fenetre._plan_monde_fenetre`, `Rendu._carte(carte_uv)`. Le plan est maintenant tracé **entre** le fond du cadre (profondeur 0) et le marqueur (12 et plus) : posé avant tout, il était assombri aux deux tiers par le fond translucide du cadre (vaut aussi pour les plans des villes, type 25). Les pièces `P0` à `P6` sont les lieux découverts (la Tour, l'Arbre du Monde dans le désert...).
- **Coffres : le couvercle s'ouvrait vers le bas** : le jeu calcule la rotation d'un objet de carte avec `FldObject.rotateXZY` (`0xCD47F0`, appelée par `init_fld`, `SetCommonAnimation`, `pmv_func`, `c_pmv_func`) : `q = AngleAxis(-rx, droite) * AngleAxis(ry, haut) * AngleAxis(-rz, avant)`, angles X et Z **inversés** et ordre X, Y, Z (et non `Quaternion.Euler`, Z-X-Y). La clé du couvercle est `rx = -60` : avec la convention d'Unity il plongeait dans le coffre (intérieur noir plat sans couvercle) ; avec celle du jeu il se relève de 60°. `donnees.euler_mat` reprend la fonction du jeu (les rotations autour de Y seules ne changent pas ; `ev01` : nuages et ciel inclinés changent). L'intérieur noir bordé d'or est bien dans la texture d'origine (`tkrbox1.tim`). Cache `carte7_<nom>.pkl` (était `carte6`) : les cartes sont préparées de nouveau au premier lancement.
- **Anciens états instantanés** : un état enregistré avant les nombres de dégâts n'avait pas `Interface.degats` (`'Interface' object has no attribute 'degats'` au chargement) ; `etats.appliquer` le crée.
- **Pas résolu** : (1) l'eau des grottes (`dab1`) : la couche d'eau suit exactement le polygone du bassin (comparaison avec/sans la couche : seule la surface du bassin change) ; le débordement des « vagues » sur le sol n'a pas été retrouvé, il faudrait la capture ou l'état au bon endroit ; (2) murs invisibles et escalier de la colline de `dbout` : aucun état dans cette carte, pas reproduit (les collisions viennent de `dbout.map`, lu par le moteur) — **à revérifier avec #22** : les objets de cette colline étaient enfoncés dans le relief (signe de Y) ; (3) clignotements : 21 images consécutives de la ville, de la carte du monde et d'une grotte ne montrent que des animations voulues (flammes des braises, eau, sprite du héros), pas de scintillement parasite.


## Signe de Y des objets, carte du monde, musique, menu Échap (31/10/2026, #22)
- **Cause des arbres et de la ruine « enfoncés » (colline de `dbout`) : le signe de Y.** `ChunkFile.readPosition` (`0xCCEB58`) lit x, y, z puis **nie y** (`fneg`) ; le jeu s'en sert pour les positions des objets de carte (`FLD_MAP_OBJ`) et des clés de mouvement (`ReadMotion`, FPMV). Position réelle d'un objet = `(x, -y_fichier, z)` ; `FldObject.fld_set_obj_matrix` (`0xCD78E4`) la pose telle quelle, et `cmd_fld_pos` (`0xD12AA8`) n'inverse rien (le moteur envoie des positions déjà dans le repère d'Unity). Mesure : sur la colline de `dbout`, `y_fichier + hauteur du relief` vaut −0,15 ± 0,05 pour les 15 objets (arbres, ruine `008_dboisi1`, sol `012_dbokg1`) ; la corrélation y_objet / relief est négative dans les cartes à relief (`teout1` −0,82, `tdout` −0,92, `ss4out` −1,0…). Le « +1 des coffres » (#19, y fichier −0,5 devenu +0,5) n'était que ce signe : remplacé par la négation générale dans `donnees._extraire_carte` ; `fld.pmv` nie aussi le y des clés de position. Cache `carte8_<nom>.pkl` (était `carte7`) : les cartes sont préparées de nouveau au premier lancement. Vérifié : ruine debout au sommet de la colline, arbres sur les pentes ; coffres, grotte à eau (`dab1`) et ville inchangés.
- **`FldObject.ModelOffset`** (décalage Y par préfixe de matériau) : sans rapport, c'est un décalage de 0,02 contre le z-fighting (`GetOffset`).
- **Carte du monde** : la touche Carte ouvre la version 1 (type 25, ville / carte simple), une deuxième pression la version 2 (type 26, carte qui se complète, par `pad` haut = 2 envoyé au bouton de la fenêtre de type 25), une troisième ferme. Le bouton de sortie (fenêtres 22 / 23 `Make_MapButton`, bouton `-1`, manette `0x400` ; la fenêtre 22 a en plus, depuis l'audit de fidélité du 01/11/2026, le bouton Mode, manette `2`) était inactif après un passage par le menu Échap : le clic envoie maintenant `BTN_DISCUSSION` (`decl 0x400`) comme la touche ; la phase de la carte est lue dans `[0x275d18]` (2 = grande carte + bouton).
- **Ordre des compagnons sur la carte du monde** : `rang` (position dans le groupe) pose le décalage de profondeur des sprites (`0.04 + rang * 0.0005`) : le premier du groupe est devant. Corrigé par l'avance #144 (`rang_profondeur_champ`) : à position égale, c'était le dernier du groupe qui passait devant.
- **Musique à la reprise d'un état** : `Son.etat_bgm()` / `restaurer_bgm()` (identifiant, position en secondes, jingle) ; la position est calculée avant `play()` (lire `src.pos` après avait 1,5 s de retard à cause du pré-remplissage) ; les états instantanés enregistrent `viewer['musique']`.
- **Menu Échap** : thème des menus du jeu (fond bleu nuit `FOND_DQ`, liseré en 3 traits `BORDS_DQ`, sélection = triangle, texte blanc) ; bouton ↺ à droite de la valeur des curseurs ; les choix à 3 valeurs ou plus (Sprites, Résolution, échelle, anticrénelage) s'ouvrent en liste déroulante (`deroule`, `zones_pop`) ; Oui / Non basculent directement (depuis #23 : interrupteur, voir plus bas). Tableau Excel de l'arborescence fourni à Sylfried (feuilles Menu, Écrans, Valeurs, Touches) : il le modifie, Claude applique.

## Rendu net des sprites, décors et boutons, menu Échap (31/10/2026, #23)
- **Pixels parasites et contour flou autour des sprites (heros, PNJ)** : les feuilles de sprites d'origine n'avaient pas de gouttière (cases collées, texels transparents non dilatés). Le filtre « sharp bilinear » (et le linéaire) mélangeait alors les pixels de la case voisine au bord de la case (points bruns) et la couleur noire des texels transparents (liseré sombre ou vert). `_feuille_orig` construit maintenant l'atlas comme les feuilles HD : `hd.agrandir_feuille(..., facteur=1)` avec une **gouttière de 2 px** (`GOUT_ORIG`) et la couleur des pixels transparents propagée du voisin opaque (`HD._dilater`). Toutes les feuilles de sprites portent la clé `g` (gouttière) et le calcul des UV est unique : `pl = cl + 2g`, `ph = ch + 2g`, origine `col * pl + g`. Vérifié sur la carte du monde (modes 0 et pixel perfect) et dans une ville (modes 0, 3, 4).
- **Décors 3D flous (jarres, tonneaux, coffres, pierres)** : `_tracer_decor` dessinait tout avec `net = 0` (linéaire + mipmaps), donc des textures de 32-64 px étirées en flou. En ville et en donjon, avec le style « Originaux » ou « Pixel perfect » et le lissage actif, il utilise maintenant `net = 1` (texels nets, seule la frontière entre deux texels est adoucie, comme les sprites). Les styles HD et les peintures de combat gardent `net = 0`. `DQ_DECOR_FLOU=1` rétablit l'ancien rendu (comparaison).
- **Boutons de l'écran (`hud_mobile.py`)** : l'icône de 32 px était agrandie en linéaire jusqu'à 72-108 px (flou). Elle est maintenant agrandie d'abord par blocs entiers `n = ceil(c / 32)` (plus proche voisin : chaque pixel d'origine devient un bloc net) puis réduite à la taille exacte par le filtre linéaire ; un sprite par (icône, n) ; couleur des pixels transparents dilatée d'un pixel (`_icone`).
- **Menu Échap** : Oui / Non = **interrupteur** coulissant (`_interrupteur`, `LARG_SW`, `HAUT_SW`, position animée par libellé dans `pos_sw`) avec le texte « Oui » (or) / « Non » à sa gauche ; Entrée ou clic bascule, ← = Non, → = Oui. Tous les autres choix, **même à deux valeurs**, sont des listes déroulantes (`sw` = deux valeurs booléennes ; sinon `liste`). Résolutions triées par largeur puis par hauteur (`J.resolutions()`). Le texte d'aide du pied s'adapte (interrupteur / liste).
- **Zoom de la carte du monde qui passe à 400 % après un réglage de l'angle de caméra** : non reproduit (zoom_carte reste à 1,0 en simulation clavier). Piste : la répétition d'une direction maintenue (`rep`) s'appliquait à la ligne **sélectionnée au moment de l'image**, donc, si la sélection changeait pendant la répétition (survol de la souris, changement d'écran), elle modifiait un autre réglage. Garde-fou : `_repeter` mémorise `(écran, ligne)` de départ et `maj` arrête la répétition horizontale dès que la sélection n'est plus la même. À surveiller.
- Cache : inchangé (`carte8_<nom>.pkl`). Les feuilles de sprites d'origine sont reconstruites au lancement (pas de cache disque).

## Halo des héros, états datés, menu Échap noir, transitions, vignettage (31/10/2026, #24)
- **Pixels résiduels autour de Ragnar** : les 11 feuilles de sprites des héros (`h100` à `h127`, 256 x 128) ont un **halo** d'alpha 1 à 105 (RVB violet foncé, reste du filtrage d'origine) autour d'un corps d'alpha 204 à 255 ; l'histogramme n'a aucun alpha entre 105 et 204. Sans rejet, le halo se voyait en liseré lilas flou (surtout sur un décor clair, comme le sable) et le corps laissait voir le décor. `HD.nettoyer_feuille(arr, seuil=128)` : alpha < 128 devient 0, sinon 255 ; appliqué à la feuille d'origine (`_feuille_orig`, donc aussi à celles des styles HD qui en partent). Les feuilles des PNJ et des monstres ont un alpha binaire et ne changent pas. `HD.VERSION` 3 : les atlas HD des héros sont recalculés (avant, l'alpha « adouci » les envoyait en bicubique ; ils passent désormais en EPX comme les autres).
- **États instantanés** : `NB_ETATS = 9` (touches 1 à 9 ; la touche 0 n'est plus un emplacement ; un ancien `etat_10.dqs` reste sur le disque, ignoré). Le nom d'un état est sa **date et son heure** (`31/10/2026  19:21:05`, `Pause._date_fr`) au lieu du nom technique de la carte ; à droite, le lieu seulement s'il est lisible (« Carte du monde », « Combat »). Même chose dans le panneau de la miniature.
- **Menu Échap au design du jeu mobile** : fond noir, cadre en cinq traits (gris 138, gris clair 205, blanc 255, gris 132, gris foncé 41, de l'extérieur vers l'intérieur) mesurés sur la fenêtre de message d'origine (`BORDS_DQ`, `_cadre`) ; palette de texte du jeu (`MenuPortItemTable`, couleurs 0 à 3 : blanc, jaune 255 235 4 pour la sélection et les valeurs actives, rouge, gris 128) ; police du jeu (`cache/ui_font.otf`, famille `FOT-GMaruGo Pro`, enregistrée par `pyglet.font.add_file` au premier affichage, `Pause._et`, repli sur les polices du système ; le glyphe ↺ n'existe pas dans cette police : le texte d'aide dit « bouton rond »). Le bleu nuit d'avant (`(7, 11, 65)`) était une invention à partir des menus DS. Les cadres de secours de `fenetre.py` (sans `ui_layout.json`) restent bleus.
- **Transitions** : un changement de carte = fondu au noir de 30 images (`cmd_fade`, `Etat._fondu`), un blocage de 2 images, puis fondu d'entrée de 30 images (mesuré en sortant du château : fondu de sortie à l'image 171, d'entrée à 203). Réglage `vitesse_fondu` (Jeu : « Vitesse des transitions entre cartes », x1 à x4, **x2 par défaut**) : `Etat.vitesse_fondu` divise la durée des fondus au noir (ni blancs ni colorés : bits 0x800 et 0x2000 absents) ; le moteur attend la fin du fondu par le bit 0 du mot de sortie, qui retombe donc plus tôt.
- **Vignettage** (`_dessiner_vignette`, réglage `vignette`, Affichage : « Vignettage (bords assombris) », « Effet de vignetage » depuis #27, **30 %** par défaut) : dégradé radial elliptique noir (texture 512 x 288 étirée, intact jusqu'à 45 % du rayon), sous le fondu et l'interface, ni en combat ni sur la carte du monde (entièrement 2D). Il donne du volume aux décors et aux sprites 2D plats loin du centre et masque le fond uni hors de la carte, sans rien changer à leur forme. Pistes si cela ne suffit pas : ombre de contact sous les arbres et objets 2D (comme celle des personnages), brume de distance, léger assombrissement des sprites vers les bords.


## Zoom au lancement, survol par bouton, menu Échap selon l'Excel (31/10/2026, #25)
- **Énorme zoom au lancement (corrigé en code, non testable sur un vrai Windows ici)** : le réglage enregistré était 3840 x 2160, plus grand que l'écran. Windows réduit alors la fenêtre mais pyglet 2.1 (Win32) garde la taille demandée (`_width` / `_height` ne sont mis à jour que par `WM_SIZE`, ignoré pendant la création) : viewport et tampon de dessin deux fois trop grands, donc scène agrandie (seul le quart haut-gauche visible, centre de la scène en bas à droite) jusqu'au premier redimensionnement. `fenetre.ajuster_taille` ramène la taille demandée à `zone_utile()` (écran moins 16 px de largeur et 100 px de hauteur, en gardant le 16/9 ; plancher 320 x 180) ; `_verifier_taille_reelle` relit la zone cliente (`GetClientRect`) pendant les 90 premières images puis toutes les 120 et corrige `_width` / `_height` si besoin ; la liste des résolutions du menu ne propose que celles qui tiennent. Résolution par défaut : 1920 x 1080.
- **Message du prêtre pendant l'écran de démarrage, puis « je ne peux pas bouger »** : non reproduit. Ordre observé en test : ciel (`ev01`), église (`mak1f1`) avec fondu d'entrée, message environ 20 pas moteur plus tard ; la marche fonctionne dès que le message est fermé. Hypothèse : conséquence du zoom (fenêtre de message hors de la partie visible, le moteur attend la touche A). À revérifier après la correction du zoom.
- **Survol par bouton** : `Fenetre.sel_nd` (identifiant du nœud) prend le pas sur `fen.sel` (numéro de bouton, partagé par plusieurs nœuds : toute la ligne d'une boutique, « Acheter » et « Rien » ensemble) ; `Fenetre.boutons(True)` renvoie aussi l'identifiant, `_zones` / `_bouton_sous` le transmettent, `survol_nd` (souris) et `appui_nd` (bouton enfoncé) l'alimentent, `on_mouse_leave` l'efface. Le curseur clavier garde le comportement d'origine (tous les nœuds du numéro sélectionné).
- **Menu Échap selon `Menu_Echap_DQ4_PC.xlsx`** : Pause = Reprendre, Sauvegarder un état, Charger un état, Jeu, Quitter le jeu. **Jeu** = vitesse de déplacement, vitesse des transitions (absente de l'Excel, gardée), course, vitesse de la course, taille des nombres de dégâts, puis les sous-menus **Affichage**, **Son**, **Commandes**. **Affichage** = Plein écran, Résolution, Shader (ex-« Sprites »), Lissage des textures, Distance d'affichage, Angle de la caméra, Vignettage (absent de l'Excel, gardé), Anticrénelage. **Commandes** = Interface, les touches (colonnes Touche 1 / 2), Afficher les infos à l'écran (nouvelle action `infos`, F1 par défaut), Rétablir les touches par défaut. **Interface** = Afficher les boutons à l'écran, Changer le dispositionnement de l'interface. Supprimés : molette inversée (toujours inversée : molette vers le haut = ligne suivante), zoom de la carte du monde (la molette sur la carte du monde zoome toujours, sans être enregistrée), infos à l'écran (F1), échelle pixel perfect (remplacée par la distance). Seule Échap reste réservée (`RG.RESERVEES`).
- **Distance d'affichage (remplacée en #26 par le zoom en pourcentage, voir plus bas)** (`reglages['distance']` : 1, 2, 4, 8 ; `Jeu.distance`, `regler_distance`) : x1 = vue habituelle (en pixel perfect, échelle automatique selon la fenêtre) ; x2 / x4 / x8 = champ 2 / 4 / 8 fois plus large et plus haut. Villes, grottes, tours : `th_v *= distance` dans `_camera_ville` ; carte du monde : hauteur visible `CH_VUE_HAUT x distance / zoom` (`_camera_champ`) et `_k_auto` divise par la distance. **Limite** : en pixel perfect l'échelle ne descend pas sous 1 pixel d'écran par pixel de carte, donc en 720p x2, x4 et x8 donnent la même vue sur la carte du monde (en 1080p, x4 et x8 ; en 4K les quatre sont distinctes). Les autres styles de rendu suivent exactement la distance. Le combat n'est pas concerné.
- **Angle de la caméra sur la carte du monde (supprimé en #27 : la carte du monde est toujours vue de dessus)** : un angle **négatif** incline la vue (de 0 à 20 degrés, `CH_INCLINAISON_MAX`) : matrice orthographique inclinée (`y_écran = (hauteur x sin - (z - cz) x cos) / dh`, profondeur le long de l'axe de la caméra), zone de sol chargée agrandie de 1 / cos. C'est une inclinaison **orthographique** : à -20 degrés le sol est raccourci de 6 % en hauteur (peu visible) ; un angle positif ne change rien (la vue est déjà de dessus). Les sprites restent à plat sur le sol. Un rendu en perspective serait plus marqué mais casserait le pixel perfect.
- **Anticrénelage** : renommé, avec une note rouge sous la valeur (« Sera appliqué au prochain lancement du jeu ») tant que la valeur choisie diffère de celle du lancement (`Jeu.args.msaa`). `_choix(..., note=...)`, la ligne monte de quelques pixels pour laisser la place.
- **Placement des boutons** : écran `placement` dans la pile du menu (plus un mode à part) : les boutons de l'écran sont dessinés sans voile, le panneau « Disposition de l'interface » est collé en bas (Taille des boutons, Aimantation à la grille, Rétablir les positions d'origine, Terminer) ; un clic hors du panneau saisit un bouton, glisser le déplace (`Pause.cadre_panneau`, `hud.prendre / deplacer / poser`) ; Échap ou clic droit termine (réglages enregistrés).
- **Touche des infos** : `infos` fait partie de `TOUCHES_DEF` / `ACTIONS` ; `on_key_press` et le menu testent `reg.action_de(symbol) == 'infos'`. Le petit rappel de démarrage (« Échap : menu    F1 : infos », en bas à gauche, 8 s) a été **retiré** à sa demande (#129, avance #143).
- **Reste** : zoom de la carte du monde à 400 % après un réglage de l'angle (non reproduit), débordement de l'eau des grottes, murs invisibles de `dbout`, clignotements, ordre des compagnons non vérifié.

## Touches ZQSD / flèches = caméra, zoom 40-400 %, menu Échap à plat, plaques (31/10/2026, #26)
- **Courir accélère tout** (question) : la course règle le nombre de pas moteur par image (`_facteur_vitesse`), donc les PNJ, les animations et les scripts vont aussi plus vite. Une course qui n'agirait que sur le héros demanderait de toucher à la vitesse du seul héros dans le moteur : non fait.
- **Espacement des chiffres de dégâts** (question) : sur mobile, `HoppingNumber` avance de `PartsInfo[11].m_dps` = 16 unités par chiffre, pour un quad de 32 unités (échelle 0,8) : l'encre d'un chiffre (environ 7 px sur 16) laisse donc à peine un blanc entre deux chiffres, ils se touchent presque. Le pas de 21,0 de la visionneuse était une estimation : il est maintenant de 12,8 (16 x 0,8), à l'échelle 1 de « Taille des nombres de dégâts ».
- **Nouvelles touches par défaut** (`reglages.py`, `touches_v` = 3 : une liste enregistrée plus ancienne est abandonnée) : **ZQSD** = déplacement ; **flèches** = caméra (← → rotation, ↑ ↓ angle) ; **Espace** = bouton A (action, validation) ; **Entrée** = menu de commandes sur le terrain ; dans un menu du jeu ou un message elle envoie A (front montant `fr['menu']`, comme Espace) ; **Retour arrière** = B ; **M** = carte ; **Maj** (gauche ou droite) = courir (maintenu : interprétation de « Maj : toujours courir », à confirmer) ; Discussion de groupe n'a plus de touche (Espace, voir plus bas) ; page précédente = A / Page haut, page suivante = R / Page bas. Dans un menu, un message ou un combat, les flèches redeviennent des directions (`pad()` ; `_terrain_libre()` décide : ni menu Échap, ni message, ni menu ou carte du jeu, ni combat, ni effet d'écran).
- **Caméra aux flèches** (`_maj_camera`, à chaque image affichée ; `CAM_LACET_VIT` 100 degrés / s, `CAM_TANGAGE_VIT` 45 degrés / s) : ← → tournent la caméra autour du héros (`Fenetre.lacet`, villes, donjons et tours seulement ; pas pendant une caméra libre de scène), ↑ ↓ relèvent ou abaissent l'angle (`angle_cam`, enregistré dans `reglages['angle_camera']`, bornes `CAM_ANGLE_MIN / MAX`). **← et → ensemble remettent la rotation à 0, ↑ et ↓ ensemble remettent l'angle par défaut** (interprétation de « toucher deux directions remet la caméra par défaut dans cette direction » : deux flèches opposées d'un même axe ; à confirmer). Le réglage « Angle de la caméra » a disparu du menu. La rotation n'est pas enregistrée : retour à 0 au lancement.
- **Déplacement par rapport à la caméra** : la direction demandée à l'écran (8 directions) est tournée de round(lacet / 45) crans avant d'aller au moteur (`_tourner_dir`). Le moteur ne connaît que 8 directions du monde : la marche est donc quantifiée par pas de 45 degrés alors que la caméra tourne en continu. Les 8 rangées des feuilles des héros et les 4 des PNJ sont décalées de la même façon (rangée affichée = round((rangée x 360 / n - lacet) / (360 / n)) % n), pour les héros, compagnons, PNJ et monstres de terrain (le décalage ne touchait que les PNJ avant : « changer l'angle ne change pas l'orientation de tous les sprites »).
- **Objets du décor qui font face à la caméra** (`objets_carte.py`) : les objets de la carte dont le drapeau de billboard est posé (4 = rotation en Y, 32 = rotation complète) sont reposés à chaque changement de caméra (`ObjetsCarte.orienter`, appelé par `_orienter_decor`) ; leurs quads sont construits autour du centre de leur base. C'est ce qui manquait aux tonneaux, jarres, coffres... (ils restaient de profil quand la caméra tournait). Vérifié dans l'église à 40 et 90 degrés ; non vérifié sur tous les types d'objets du jeu.
- **Espace = bouton d'action pour tout, sinon discussion de groupe** : Espace envoie A au moteur. S'il n'a rien déclenché au bout de 3 pas moteur (`attente_action`), la visionneuse envoie BTN_DISCUSSION. « Rien déclenché » = le moteur n'a pas verrouillé le héros (`Global.Flag` bit 0x4) ni ouvert un message, un menu ou un effet. Vérifié : en terrain libre sans cible, BTN_PAROLE (0x100) puis BTN_DISCUSSION (0x400) trois pas plus tard. **Non vérifié** : un cas où une action existe mais ne positionne pas le bit 0x4 (la discussion s'ouvrirait en plus).
- **Zoom 40-400 %, indépendant du shader (remplacé en #27 par « Distance caméra » de 50 à 200 %, zoom interne = 100 / distance)** (`Fenetre.zoom`, `reglages['zoom']`, `regler_zoom`, `_zoom_valide`) : curseur « Zoom » du menu Affichage et molette (hors menu et hors combat, x1,1 par cran, villes et carte du monde). 100 % = vue habituelle de la ville (champ de `_camera_ville`) ou de la carte du monde (`CH_VUE_HAUT`). Changer de shader ne modifie plus le cadrage : l'échelle automatique du pixel perfect n'intervient plus que dans le rendu des sprites. Vérifié sur la carte du monde, pixel perfect contre un autre shader, 100 % et 200 % : cadrage identique. `--carte-zoom` (1 = 100 %) passe avant le réglage. Remplace la distance d'affichage de #25. **Non vérifié** : le rendu d'une ville entière à 40 % (zone de sol chargée par le moteur, fond uni possible aux bords).
- **Menu Échap à plat (réorganisé en #27, voir plus bas)** : Pause = Reprendre, Sauvegarder un état, Charger un état, **Affichage**, **Son**, **Commandes**, Quitter le jeu (le bouton « Jeu » est supprimé). Affichage = Plein écran, Résolution, Shader, Lissage des textures, Zoom, Vignettage, **Taille des nombres de dégâts**, Anticrénelage. Commandes = **Vitesse de déplacement, Course (maintenir la touche) oui / non, Vitesse de la course, Vitesse des transitions entre cartes**, Interface, puis les touches. La liste défile quand elle ne tient pas (la sélection reste visible).
- **Style des plaques de la version mobile** (`hud_mobile.cadre`, `plaque`) : dégradé vertical sombre, liseré clair et bordure dorée sur la ligne sélectionnée, générés par distance signée en numpy dans une texture mise en cache (`_texture`, `_garder`), à la taille de l'élément. Appliqué aux lignes du menu Échap (`pause.py`, `_cadre` appelle `HM.cadre`), au cadre du menu et aux boutons de l'écran (Carte, Discussion de groupe, Commandes : plaque derrière l'icône). **Ressemblance à la capture mobile non mesurée** : couleurs et dégradé choisis à l'œil (captures à comparer). *(Pour les boutons de l'écran, remplacé par la plaque 9 tranches du jeu lors de l'audit de fidélité du 01/11/2026 ; le dégradé ne sert plus qu'au menu Échap et de secours.)*
- **Raté / limites** : la rotation de la caméra n'agit pas sur la carte du monde (vue de dessus fixe, nord en haut) ; le déplacement reste à 8 directions ; la molette règle le zoom aussi en ville (avant : seulement le monde) ; le fichier Excel du menu (`Menu_Echap_DQ4_PC.xlsx`) n'a pas été régénéré ; les points de #25 non reproduits restent ouverts (zoom 400 % de la minicarte après un changement d'angle, message de démarrage), ainsi que le débordement de l'eau des grottes, les murs invisibles de `dbout`, les clignotements et l'ordre des compagnons.

## Recentrage animé, menu Échap noir avec barre de défilement (31/10/2026, #27)
- **Recentrage animé de la caméra** (`_etat_axe`, `_maj_camera`) : appuyer sur les deux flèches d'une même direction (← + → ou ↑ + ↓) lance une animation vers la valeur d'origine au lieu d'un saut. Le lacet est gardé dans [-180, 180[ : revenir à 0 par le plus court chemin se résume à aller tout droit vers 0 (359 degrés = -1, donc 1 degré de rotation et non 359). Vitesse : au moins `CAM_RECENTRE_LACET` = 240 degrés / s (90 pour l'angle), et 5 x l'écart par seconde quand il est grand, le tout multiplié par « Vitesse de la caméra ». Tant qu'une des deux flèches reste enfoncée après la pression double, rien ne bouge (le relâchement n'est jamais simultané) ; une nouvelle pression d'une seule flèche annule le recentrage. Vérifié en capture : lacet de 120 degrés au départ, images intermédiaires distinctes, vue recentrée ensuite.
- **Carte du monde : plus d'angle ni de rotation** : `_camera_champ` est une vue de dessus stricte (l'inclinaison de #25 et `CH_INCLINAISON_MAX` sont supprimés) ; `_maj_camera` ne fait rien hors des villes, donjons et tours.
- **Réglages** : « Distance caméra » remplace « Zoom » (50 à 200 % ; 200 % = plus loin ; zoom interne = 100 / distance, `regler_distance`, `--carte-zoom` reste un zoom : 1 = 100 %) ; « Effet de vignetage » ; « Aucun » remplace « Originaux (pixels nets) » ; « Taille des nombres de dégâts » supprimée. Nouveaux : **Vitesse de la caméra** (0,5 à 2, rotation, angle et recentrage), **Vitesse de transition** (0,5 à 2, ex « Vitesse des transitions entre cartes », défaut x2), **Multiplicateur de la course** (1 à 2, défaut x2, ex « Vitesse de la course »), **Vitesse de déplacement** (0,5 à 2). « Course (maintenir la touche) oui / non » disparaît : **Courir (maintenir)** = Maj (deux cases) et **Courir (appuyer)** (nouvelle action `courir_bascule`, **sans touche par défaut**, un appui active la course, le suivant la coupe, avec une info à l'écran) sont des touches. Défauts de la vitesse de transition et du multiplicateur de course : tout au bout du curseur.
- **Menu Commandes** : Interface, Haut, Bas, Gauche, Droite, Vitesse de déplacement, Courir (maintenir), Courir (appuyer), Multiplicateur de la course, Caméra (Haut / Bas / Gauche / Droite), Vitesse de la caméra, Vitesse de transition, Action, Menu, Annuler/Retour, Carte, Discussion de groupe, Infos à l'écran, Rétablir les touches par défaut. Chaque ligne de touche a son bouton rond ↺ (touches d'origine de cette action : `Reglages.action_par_defaut` retire à l'autre action la touche d'origine qu'elle aurait prise ; clavier : Début) et une croix rouge par case (la croix du jeu, case 50..60 x 291..300 de MenuTexture ; clavier : Suppr efface la case choisie). Les curseurs gardent leur bouton ↺.
- **Barre de défilement** (`_barre_defilement`, `_clic_barre`, `_glisser_barre`) : à droite de la liste quand les lignes ne tiennent pas (à 1080p, Commandes : 17 lignes sur 21 ; en 720p la vue défile). Flèches haut et bas (une ligne), curseur à saisir et glisser, clic dans la piste (une page), molette (deux lignes) ; la vue suit la sélection quand elle change (clavier) mais pas quand on la déplace à la barre. La fenêtre se referme sur la dernière ligne visible.
- **Style du menu Échap** : fenêtres **noires et opaques** (`HM.cadre(..., fond=(0,0,0), opacite=1)`), plus de jaune (ligne choisie = plaque éclaircie, cases de touches éclaircies, contours des interrupteurs et du bouton rond en blanc), **curseur doré du jeu** (MenuTexture 194..237 x 297..327, pointe à droite) à la place du triangle, avec une petite oscillation de gauche à droite (**inventée** : les boutons des menus du jeu n'ont pas de curseur, la sélection y est l'état « enfoncé »), **chevrons** « > » sur les lignes qui ouvrent un autre menu, **bouton retour du jeu** en bas à droite de la fenêtre (cadre de la feuille Button en neuf morceaux, 32 px d'angle réduits de moitié, état enfoncé au survol, icône de la case 11 de la rangée d'icônes, comme le noeud 1501 des menus du jeu) à la place de toutes les lignes « Retour » (sauf le placement des boutons : « Terminer ») ; il n'est pas dans le cycle du clavier (Échap, Retour arrière et le clic droit font la même chose). Écran Quitter : « Oui » / « Non », **Non** présélectionné. Textes hors boutons (titres, intertitre, aide, titres de colonnes, texte de la miniature) centrés ; le texte des lignes est centré verticalement dans leur plaque et réduit quand les lignes sont serrées.
- **Coins carrés et fond opaque dans le menu Échap (corrigé)** : `pyglet.shapes.*.draw()` coupe `GL_BLEND` à la fin de son dessin ; les textures des cadres et plaques (`HM.cadre`, `HM.plaque`) étaient donc blittées sans mélange alpha, d'où des coins à fond opaque et aucun fond translucide. `HM._melange()` remet le mélange avant chaque blit (profite aussi aux boutons de l'écran).
- **Survol dans les menus du jeu (écran 1, magasin) : non reproduit** : la sauvegarde de test est sur la carte du monde, sans accès à un magasin ni à un état en magasin. Trois durcissements : le bouton d'annulation (manette 32 / 128) qui partage son numéro avec un bouton de validation (« Rien » et « Acheter » ont tous deux le numéro 0) n'est plus allumé par ce numéro (`ui_menu`, `ok_num`) ; le dernier élément survolé reste allumé quand la souris sort de tout bouton (`on_mouse_motion`) ; une fenêtre qui n'est pas survolée n'allume rien par numéro (`sel_nd = -1`). **À confirmer sur Windows.**
- **Taille des textes hors dialogues : inchangée** : la visionneuse reprend les tailles de la mise en page d'origine ; sans capture de référence du jeu mobile je n'ai pas de proportion à corriger. À préciser (quelle fenêtre, trop grand ou trop petit).
- **Limites** : l'oscillation du curseur est une invention ; la molette déplace la sélection dans les listes qui tiennent à l'écran et fait défiler la vue dans celles qui défilent ; le fichier Excel du menu n'est pas régénéré ; les points ouverts de #25 et #26 restent ouverts (débordement de l'eau des grottes, murs invisibles de `dbout`, clignotements, ordre des compagnons non vérifié, message de démarrage).

## Retours de 22 h 33 : clavier, éditeur d'interface, caméra, carte du monde (31/10/2026, #28)
- **Carte (touche M) : bug des fenêtres fantômes** : les fenêtres de carte (types 22, 23, 25, 26) restent « actives » après la fermeture ; seules celles qui sont visibles disent que la carte est ouverte (`_carte_ports` : fenêtres visibles, plus les fenêtres seulement actives si une carte est visible, car la 2e vue est créée sans être montrée). C'était la cause des flèches qui repartaient sur le personnage, de la discussion de groupe déclenchée et de la touche carte qui ne marchait plus après une première fermeture.
- **Clavier** : Espace n'ouvre plus la discussion de groupe (action seule) ; **Alt gauche / Alt Gr** par défaut pour la discussion (migration v3 -> v4 si ces touches sont libres) ; Ctrl ne déclenche rien en dehors des combinaisons (mesuré : seule Alt envoie 0x400). **Échap** sert de touche Annuler dans les menus du jeu et la carte (`_echap_retour`), sinon il ouvre le menu Échap ; au retour du menu Échap la souris est « gelée » tant qu'elle n'a pas bougé de 6 px (`souris_gel`), pour qu'une souris immobile ne change pas la sélection. Dans le menu Échap : deux modes de sélection (flèche dorée figée au clavier, encadrement jaune à la souris : `mode_souris`).
- **Caméra** : **Maj + touche de la caméra** = 2 fois plus rapide (`CAM_ACCEL`, option `camera_maj`) ; **touche modificatrice** (`modif`, Ctrl par défaut, réattribuable) + touche de la caméra = retour animé à la vue d'origine dans toutes les directions ; Ctrl + chiffre charge toujours l'état. **Lieux verrouillés** : `TownCamera` (objet statique `_ZN10TownCamera11m_singletonE`, +0x34 limite gauche, +0x38 limite droite en 1/4096 de tour, +0x3e verrou) lu à chaque pas (`Moteur.camera_ville`) : limite < 0 (-182 dans les grottes) = rotation interdite, > 0 (5461 = 120 degrés) = rotation bornée, 0 = libre. Testé : église libre, grotte (`dab1`) immobile ; un lieu borné à 120 degrés n'a pas été rencontré. **Sprites 2D** (tonneaux, jarres) : `ObjetsCarte.orienter` les incline aussi du tangage de la caméra (`SENS_TANGAGE`, signe non vérifié à l'écran).
- **Course** : `_facteur_vitesse` ne multiplie plus les pas du moteur (qui accélérait tout) mais les variables de vitesse du héros du moteur (`TownPlayerAction::walkSpeed` 819, `walkSpeed2` 655, `FieldPlayer::Speed` 12288, réécrites à chaque image par `Moteur.vitesse_heros`, plafonnées à x2 ; au-delà, le reste passe par des pas de moteur en plus). Mesuré : x1,5 = 1,5 fois la distance par pas. Les PNJ (vitesse, animations) et les scripts gardent leur horloge ; **limites** : les jambes du héros gardent leur cadence d'origine (il glisse un peu plus vite), les compagnons suivent sa piste plus loin derrière, non vérifié avec un groupe complet. Multiplicateur de course par défaut : 1,5 (réglage enregistré à 2,0 ramené à 1,5 à la migration).
- **Carte du monde, 2e vue** (`FieldImageMap::open` du moteur, `Make_CityMap` de l'interface Unity, fenêtre type 25) : le moteur envoie le nom du plan (`dsdq4wmap01`), la position du joueur (codes 1 et 2, pixels du plan de 256 x 192), le code 3 suivi d'une **liste de lieux découverts** (un nombre par lieu : x + 256 y), le code 4 (un lieu spécial, nombre seul, non reçu en début de partie : **non affiché**) et le code 5 suivi du **voile** (16 nombres, un bit par bloc de 10 x 10 pixels non exploré, grille de 16 x 16 blocs qui commence en x = 48, y = 16 ; **x = 56 était faux** jusqu'en #32). `Interface` range ces listes dans `f['listes']` (le message qui suit le code n'est plus pris pour une commande). Rendu (jusqu'en #32) : le voile est la silhouette grisée des terres (`dsdq4wmap01m`, `Donnees.voile_monde`) posée en filtre « plus proche voisin » sur le plan (depuis #33 : plan agrandi en HD et voile lissé, voir plus bas), et les lieux sont des carrés rouges de 4 unités (`BlinkMapSymbol`) dont la transparence passe de 1 à 0 puis à 1 en 4 s. **Bouton de l'écran « Mode de la carte »** (icône 19) : visible seulement carte ouverte avec deux vues, bascule dans les deux sens (testé) ; M garde son cycle ouvrir / changer de vue / fermer.
- **Éditeur d'interface** (menu Échap > Affichage > Interface depuis #33, `pause.py`) : liste déroulante des 80 types de fenêtres du jeu avec des noms français (`NOMS_FENETRES`), taille relative et décalage de chacune (`interface_fenetres`, appliqués dans `_dessiner_menus` ; les zones tactiles suivent), « Afficher l'interface à l'écran », aperçu de la fenêtre choisie, panneau déplacé en haut quand l'aperçu est en bas. Les boîtes de dialogue ont leur entrée (`msg`). Tout se remet par défaut (une fenêtre, ou tout).
- **Menu Échap** : textes ajustés pour ne plus dépasser (`_ajuster`), marges symétriques à gauche et à droite avec la barre de défilement dans la marge, cases de touches plus hautes, ligne Interface fixée en haut de la liste Commandes avec les en-têtes « Touche 1 / Touche 2 » en dessous, flèche de sélection figée, fond du menu Échap de la même opacité que les autres menus (`HM.OPACITE_FOND`).
- **Non reproduit / à vérifier sur Windows** : Échap qui a sélectionné « Sauvegarde rapide » (corrigé par le gel de la souris, la cause exacte n'est pas prouvée), Alt Gr (= Ctrl + Alt sous Windows), jambes du héros et compagnons pendant la course, sens du tangage des sprites 2D, caméra bornée à 120 degrés, code 4 de la carte du monde.

## Retours de 23 h 55 : caméra centrée, menu États, éditeur, accélération de la caméra, boîtes de combat (01/11/2026, #30)
- **Caméra centrée sur le héros** (villes, donjons, tours ; option Affichage « Caméra centrée sur le héros », activée par défaut) : le moteur borne la cible de la caméra aux bords de la carte (`cam_cible` = position du héros, `e.sprites[0]['pos']`, tant qu'elle n'est pas bornée) et la visionneuse bornait encore `x` (`bornes_x`). Quand l'option est active, `_camera_ville` suit la position du héros (écart lissé `cam_dec`, borné à `CAM_CENTRE_MAX` = 60 unités : au-delà, c'est une scène du jeu qui déplace la caméra et on la laisse faire) et ne borne plus `x`. Vérifié : hero au centre de l'écran contre un bord. La caméra de la carte du monde (`e.champ['cam']`) suivait déjà le héros.
- **Menu États** : un seul menu « États » (Action : créer / charger / supprimer ; liste des 10 emplacements avec miniature) ; la suppression passe par un écran de confirmation « Supprimer l'état n (date) ? Oui / Non », désactivable (option « Confirmer la suppression », en plus de la demande). Pas de bouton de retour à la racine du menu Échap.
- **Éditeur d'interface** : « Rétablir toutes les interfaces », barre de défilement dans la liste déroulante (molette, glisser, clic dans la barre), aimantation à la grille et affichage de la grille pour toutes les interfaces (réglages `boutons_aimant`, `grille_edition`), et quand on choisit une interface seuls les éléments modifiables qui lui sont liés restent à l'écran.
- **Accélération de la caméra comme la course** : actions `cam_accel` (maintenir) et `cam_accel_bascule` (appuyer), **Maj gauche et Maj droite par défaut**, multiplicateur `accel_camera` (1 à 4, 2 par défaut) ; l'ancienne option `camera_maj` est supprimée (migration : désactivée = pas de touche attribuée). Maj sert à la fois à courir et à accélérer la caméra : le groupe `PARTAGE` (`reglages.py`) autorise le partage entre ces quatre actions seulement ; toute autre touche reste exclusive. « Touche modificatrice » devient « **Touche spéciale** ».
- **Touches : cases centrées** (menu Commandes) : texte centré dans la case (largeur et hauteur mesurées, `_cap` met la taille de police en cache).
- **Boîtes de combat** : les fenêtres de message de combat de types 2 et 3 (« Ragnar attaque ! », dégâts...) portent un facteur `scale` de 0,9 dans `ui_layout.json` : le texte (490 texels pour 441 unités de toile) était 10 % plus petit que dans les autres dialogues. `MiseEnPage.__init__` (`ui_menu.py`) applique `texte_plein` aux types 2 et 3 : le texte est rendu à la taille des autres boîtes (vérifié sur captures 1080p : hauteur des lettres identique au type 1). **Incertitude** : si la remarque visait plutôt le vide des boîtes à trois lignes quand le message n'a qu'une ligne, ce n'est pas réglé.
- **Compagnons accélérés (essai de #30, remplacé en #33 par des poussées d'historique toujours actives)** : en ville, `TownPartyAction::normalMove` enregistre à chaque pas du héros sa position dans un historique (`[x19]`, entrées de 12 octets, 126 entrées) ; les compagnons lisent l'entrée `k x espacement`, l'espacement (statique en `libdq4core + 0x24de94`, 8 ou 10 selon la salle) étant fixé par `AdjustArray(n)` à chaque image. Ils vont donc déjà aussi vite que le héros (pas de PNJ concernés), mais comme l'espacement est un nombre d'**images**, leur distance est multipliée par le facteur de vitesse. L'option « Compagnons à distance constante (essai) » (`compagnons_distance`) accroche `AdjustArray` (hook de code Unicorn sur l'entrée de la fonction) et divise `n` par le facteur de vitesse du héros (`Moteur._ecart_f`, minimum 2) : vérifié que l'espacement passe de 10 à 5 pour x2 sans erreur ; **non vérifié visuellement** (sauvegarde de test sans compagnons : le nombre de membres `[obj + 0x23c]` est forcé à 4 mais le moteur n'en produit pas de sprites) ; `AdjustArray` réorganise l'historique quand l'espacement change, des sauts de compagnons au début ou à la fin de la course sont possibles. **Carte du monde** : `FieldParty::getMemberPosition` lit l'entrée `i x 0x54` octets (7 entrées de 12 octets, constante compilée dans l'instruction, pas de statique) ; patcher l'immédiat risque de désaccorder `collisionSide`, `fixSidePos` et `getSidePos` : **non fait**.

## Retours de 00 h 33 : infobulles, éditeur replié, boutiques, survol des menus, course en diagonale (01/11/2026, #32)
- **Menu États** : la confirmation de suppression est une fenêtre (Oui / Non, « Non » présélectionné ; Entrée valide, Échap ou clic droit ferme, clic sur un bouton) ; l'option « Confirmer la suppression » et l'écran intermédiaire disparaissent. Libellé « Centrer la caméra sur le joueur ».
- **Accélération de la caméra** : multiplicateur de 1 à 2, **1,5 par défaut** (un ancien 2,0 enregistré repasse à 1,5). « Touche spéciale » est placée juste sous « Discussion de groupe » dans Commandes.
- **Infobulles** (`Pause._dessiner_infobulle`) : l'aide en pied de fenêtre disparaît ; une bulle apparaît au bout de 0,4 s de survol (curseurs : glisser, ← / →, taper la valeur, Suppr ; cases de touches ; liste des états) et pendant la saisie d'une touche. Les textes longs sont coupés sur 3 espaces puis par largeur.
- **Éditeur d'interface** : la fenêtre de réglage s'ouvre **toujours en haut à gauche** et se replie / se déplie (Tab ou clic sur la barre de titre ; repliée, seule la barre reste). **Aperçu des dialogues** : une vraie page de dialogue du jeu, mémorisée au fil de la partie (`echantillons_message.npz`, 12 au plus, à côté de `reglages.json`) et tirée au hasard quand on choisit « Dialogues » (texte de repli sans échantillon). Les messages du terrain montrent **3 lignes exactement** : le canevas du moteur fait 4 lignes de 28 unités et le cadre en cache 3,5 (la 4e ligne dépassait de la demi-ligne) ; `limiter_lignes` (`ui_menu.py`) coupe maillage et UV du canevas à trois lignes (types 0 : 87 texels ; types 2 et 3 : 105 après `texte_plein`).
- **Compagnons** (#32 ; l'écart constant est revenu en #33, sans option, par des poussées d'historique) : l'option « distance constante » est **supprimée** (essai de #30 : le moteur règle déjà leur vitesse sur le héros par l'historique de positions, voir les notes techniques) ; seul le déplacement du héros est accéléré, pas les animations.
- **Survol des menus du jeu** : (1) seul le port « actif » du moteur s'allumait : dans « Divers » plusieurs fenêtres reçoivent la saisie (liste de boutons, pagination, « Sauvegarde rapide », bouton retour), le survol d'un bouton d'une autre fenêtre ne l'allumait pas ; (2) les éléments **sans numéro** (bouton retour, flèches de page : numéro -1, manette 32 / 4 / 8) étaient exclus du survol et de l'affichage « appuyé ». `fenetre.on_mouse_motion` les accepte s'ils ont un dessin de bouton (partie 7) ou de flèche (partie 10) ; le cadre de fenêtre qui couvre l'écran (manette 128) n'en est pas un ; `Rendu` allume l'élément pointé (plaque : décalage UV « appuyé » ; flèche : éclaircie, ajout PC).
- **Textes dans les boutons** : `Rendu._largeur_plaque` / `_texte` compressent en largeur (jusqu'à 70 %) un texte centré plus large que la plaque qui le porte, marge de 7 unités (« Organiser les objets » dépassait de sa plaque de 198 unités). Les textes qui tiennent ne changent pas. **Attention aux tests du cloud : un `ui_layout.json` d'une ancienne génération (sans `gen` dans l'en-tête) place les textes 20 unités trop bas** ; refaire la mise en page avec l'extracteur du dépôt.
- **Alt dans le menu « Divers »** : la touche de discussion de groupe ne valide plus rien dans un menu (elle envoyait A, d'où la sauvegarde rapide proposée).
- **Plume de la carte** : l'élément « vous êtes ici » de la fenêtre type 25 était cherché par son numéro (1527) ; ce numéro change d'une génération de la mise en page à l'autre (1531 aujourd'hui) : la plume manquait chez Sylfried et pas dans les tests du cloud. Il est maintenant trouvé par son dessin (partie 3). **Qualité de la carte** : le plan (256 x 192, ou la fenêtre de 256 x 192 du plan du monde) est échantillonné en « sharp bilinear » (mode 3 du fragment shader : texels nets, seule la frontière entre deux texels est adoucie) au lieu du filtre linéaire. Le fond de la carte est une peinture douce à l'origine : le gain est surtout sur les contours, la plume et les zones découvertes.
- **Touche M en ville (liste des boutiques)** (remplacé en #33 : M ouvre le plan, puis la liste, puis ferme ; plus de passage de boutique en boutique par M) : voir les notes techniques (`TownImageMap`, fenêtre type 24 `ShopMap`). M ouvre la carte directement sur la liste (nom de la boutique, objets, prix, « 1/3 »), M passe à la boutique suivante, la dernière ferme ; Retour arrière ferme ; le bouton « Mode de la carte » alterne liste et plan. Une ville sans boutique garde la carte seule.
- **Bulle au-dessus des boutiques** : non créée. Les bulles du moteur (`TownRiseupManager`) viennent des personnages (`TownCharacterBase::execRiseup`), des objets ramassés, du groupe, des étincelles et des scripts : aucun appel propre aux boutiques ; la visionneuse affiche déjà celles que le moteur envoie.
- **Course en diagonale sur la carte du monde** : `FieldPlayer::move` lit **deux constantes locales** pour les diagonales (`libdq4core + 0x27520c` et `+ 0x275210`, Fix32 2,0 chacune, posées par l'initialiseur statique `0x1eec50`) au lieu de `Speed` (3,0). `Moteur.VITESSES_HEROS` les multiplie aussi (mesuré : diagonale x2 quand la course est active). Les diagonales du ballon (`+ 0x275214 / 0x275218`, 3,0) ne sont pas touchées.
- **Pas vérifié / à surveiller** : tous les tests ont été faits dans le cloud (Linux, police de remplacement) ; la compression des textes des boutons est une correction PC (le mobile n'a peut-être pas ce dépassement) ; l'aperçu des dialogues dépend des pages déjà vues pendant la partie.

## Retours de 01 h 31 : course sans écart, rencontres, cartes, menus, clignotements (01/11/2026, #33)
- **Compagnons à la course (écart constant)** *(remplacé en #34 : retour à la première version, voir plus bas)* : le héros court sans que l'équipe se disperse, et les animations ne changent pas (seule la vitesse de déplacement du héros augmente). Le moteur règle les compagnons sur un historique de positions ; le visionneur y ajoute des positions intermédiaires interpolées quand le héros va plus vite (`Moteur._pousser_historique`, crochets sur `TownPartyAction::normalMove` et `FieldParty::normalArray`, détails dans les notes techniques). Mesuré en ville et sur la carte du monde avec deux membres ; pas vérifié sur une vraie sauvegarde à trois ou quatre membres.
- **Taux de rencontre à la course** : calculé sur la distance parcourue, pas sur le temps passé à avancer (crochet sur `Encount::execWalk`, compteur accéléré de `h - 1` par pas). Mesuré sur le compteur du moteur, pas sur une longue marche réelle.
- **Touche M** : en ville, M ouvre d'abord le **plan**, un 2e appui la **liste des boutiques**, un 3e ferme (le bouton « mode » de l'écran fait la même chose) ; M ne passe plus d'une boutique à l'autre, ce sont les flèches ← / → de la liste (ou ses boutons). Un seul panneau de carte est visible à la fois, avec le bouton retour (vérifié en listant les fenêtres du moteur) ; sur la carte du monde, grande carte puis petite carte puis fermeture, comme avant.
- **Petite carte du monde** : (1) le voile commençait 8 pixels trop à droite (x = 56 au lieu de 48) : la zone explorée n'était pas la bonne ; (2) plan agrandi en Lanczos x4 avec deux passes EPX pour arrondir les terres, voile à contour arrondi et limites de blocs adoucies (`hd.agrandir_plan`, `hd.voiler_plan`, texture 1024 x 768 recalculée quand le voile change, environ 0,3 s) ; les plans de villes sont aussi agrandis (Lanczos, sans EPX). **Pas vérifié** : ce que Sylfried appelle « interface sous la carte » (je n'ai pas pu retrouver une fenêtre qui reste affichée sous le plan : seules la carte et le bouton retour sont visibles) ; le rendu sur Windows.
- **Textes trop grands** : un texte plus large que sa **fenêtre** (en plus de celui qui dépasse de sa plaque de bouton) est compressé en largeur jusqu'à 70 %, depuis son point d'ancrage (`Rendu._texte`, `Fenetre.etendue_x`).
- **« Aura » des sprites de menus** : les cases de la feuille `MenuTexture` ont du **blanc ou du rose sous leurs pixels transparents** (le cœur de « Carac. » : RVB 255, 149, 255), que le filtre linéaire mélangeait au bord de l'icône (liseré clair). Les couleurs des pixels transparents prennent maintenant celle du voisin opaque (`hd._dilater`, comme pour les sprites ; alpha inchangé) pour les deux feuilles du menu et les bulles d'icône.
- **Menus** : « Interface » est le dernier élément du menu **Affichage** (il n'est plus dans Commandes) ; la flèche de pliage suit le titre « Interface » ; l'aperçu des dialogues est un **texte d'essai aléatoire** (« Aperçu d'un message. », etc., `Jeu.ESSAIS`) : les pages déjà vues ne sont plus mémorisées (le fichier `echantillons_message.npz` n'est plus ni lu ni écrit) ; l'écran Commandes a quatre sections (Déplacement, Caméra, Actions du jeu, Autres) en intertitres dorés.
- **Clignotements** : (1) icônes de lieux de la carte du monde : leurs sommets étaient réécrits **après** le premier tracé de l'image, donc partaient au GPU avec une image de retard (et une image vide quand leur nombre changeait), même cause que pour les monstres en #20 ; correctif `_dom_lie = None` avant leur tracé ; (2) fin de combat : l'écran noir d'attente de la carte montrait encore la fenêtre de statut du groupe (la « boîte violette » en haut à gauche) ; les fenêtres ne sont plus dessinées dans cet état (carte `btl_*` hors combat). Les carrés rouges de la petite carte **clignotent volontairement** (`BlinkMapSymbol`, 4 s). Aucun des deux correctifs n'est mesuré sur plusieurs images consécutives sur un vrai Windows.
- **Flou des sprites à la transition vers le combat** : normal. `Capture.SetBlur(true)` : le jeu d'origine adoucit la capture pendant l'effet (`EFFET_FLOU`, biais de mipmap).
- **Ombres décalées à la course** : non reproduit. Les ombres utilisent la même position interpolée que les sprites ; reste possible un effet de perspective sur les compagnons éloignés. À revoir avec une capture.

## Retours de 11 h 34 : alliés, carte, fin de combat, menu États, Divers, Oui / Non (01/11/2026, #34)
- **Alliés qui tremblent** : retour à la **première version** (#30) : en ville, le crochet `AdjustArray` divise l'écart d'historique des compagnons par le facteur de vitesse ; les positions interpolées de #33 (cause probable du tremblement) sont retirées. Limite connue : **sur la carte du monde les alliés prennent de la distance quand on court** (comme avant #33). *(En ville, le crochet de #34 faisait téléporter l'allié à la course : corrigé en #35.)* Fluidité non mesurée : le héros ne bougeait pas dans mes essais automatiques, retour fait par construction.
- **Ombre** : rien à faire (Sylfried : plus de problème).
- **Rencontres** : toujours **aléatoires**. Le « 16 » est le nombre de pas de marche entre deux **tirages** (`Encount::execWalk`) : à chaque tirage le jeu fait `dss::rand(4)` et ne déclenche que si le résultat est 0 ; ce n'est donc pas un combat garanti tous les 16 pas. Courir ne change que la fréquence des tirages par seconde (par distance, elle est celle d'origine). Les compteurs de protection (`[+ 0x22]`) ne sont pas tous décodés.
- **Petite carte du monde, carrés rouges** : ils étaient posés avec leur coin haut-gauche sur le point du lieu (donc décalés de 2 unités vers le bas et la droite) ; ils sont maintenant **centrés sur le point**, comme le marqueur du joueur (qui coïncide avec le lieu quand le héros se tient dessus : même coordonnées, vérifié sur le slot 4). **Pas vérifié** : l'ancrage exact du jeu d'origine (aucune capture de référence), à confirmer à l'œil.
- **Boîte à la fin d'un combat** : le jeu ferme le **fondu au noir** alors que la fenêtre de statut du groupe (port 12, état `COMBAT`) est encore « visible » : elle apparaissait seule sur l'écran noir. Les fenêtres sont maintenant masquées dès que le fondu atteint 0,6 pendant l'état combat. **Reste possible** : le message de fin (« Ragnar s'enfuit ! ») reste affiché sur le noir, avec sa boîte, tant qu'il est affiché. *(Corrigé en #35 : la dernière boîte part dès le début du fondu.)*
- **Menu États et menu Échap** : la fenêtre a la **transparence des menus du jeu** (`HM.OPACITE_JEU` = 0,68), le voile derrière elle est moins sombre (opacité 90 au lieu de 150), les boutons ont **le dessin des boutons du jeu** (plaque partie 7 de la feuille `Button`, comme « Soigner tous », image « appuyée » à la sélection ; `Rendu.plaque`, `PausePC._plaque`). Le texte « Image du moteur … » de la miniature des états est supprimé.
- **Écran Divers (pages 1 / 2)** : **Échap** et **Retour arrière** ramènent en arrière (le bouton retour du jeu, pad 0x20, est celui de la liste du port 8, pas de la fenêtre qui a le clavier), les flèches ← / → tournent les pages. Le clavier pilote maintenant la **liste** (port 8) ; « Sauvegarde rapide » (port 11) n'est atteignable qu'à la souris.
- **Réglages de vitesse et de volume (type 27)** : les plaques de boutons sont **centrées entre les deux étiquettes** (« Rapide » en haut, « Lent » en bas) : les codes 6, 7, 8 de la liste (type 8) ne sont pas extraits, c'est une **heuristique** (`Fenetre.centrer_liste`). Le titre (« Volume musique ») est compressé comme les autres textes : les textes des fenêtres sans cadre propre sont mesurés sur les cadres des fenêtres voisines (`Rendu.voisins`).
- **Oui / Non** : la fenêtre est collée à **4 unités** sous la boîte de message (`OUINON_ECART`), au lieu d'un écart fixe plus grand.

## Retours de 13 h 08 : bouton Menu Échap, dernière boîte de combat, alliés à la course, plume (01/11/2026, #35)
- **Bouton « Menu Échap » dans la fenêtre Paramètres** : une rangée de plus **juste au-dessus de « Volume musique »**, avec le **même gabarit et le même pas** (67 unités) que les cinq autres, donc alignée ; le cadre avait la place d'une rangée en haut (marges de ~19 unités en haut et ~25 en bas, plus équilibrées qu'avant). Il ouvre le **menu Échap** du portage (souris : clic, le bouton s'allume au survol ; clavier : ↑ depuis le premier bouton, puis Entrée). Il n'existe pas dans le jeu d'origine : la plaque est une **copie** de celle du premier bouton de la liste (type 8) et de son étiquette (`Fenetre.bouton_echap`, bouton n° 100, jamais envoyé au moteur). Il n'apparaît **que dans la liste des Paramètres** (pas dans Divers, ni dans les réglages de volume, de vitesse, de taille de la croix). **Échap** au clavier garde son rôle de retour en arrière.
- **Dernière boîte de dialogue d'un combat** : elle **disparaît maintenant au début du fondu au noir** de la transition, sauf si une page attend une touche (la boîte reste alors, pour qu'on puisse la lire et la valider). Avant, le jeu ne la fermait qu'après le fondu, donc elle restait affichée sur l'écran qui noircit (`Jeu._boite_fin_combat`).
- **Compagnon qui se téléporte quand on court** (sortie d'église, DOc) : cause trouvée. Le crochet de #34 donnait au jeu un écart **impair** (par ex. 5 au lieu de 8) alors que, en régime établi, le jeu ne décale que les entrées **paires** de l'historique : le compagnon lisait des entrées jamais mises à jour, restées sur les positions d'arrivée (les portes de l'église), puis retombait sur le héros à l'arrêt. L'écart est maintenant **toujours pair** (au plus 2 de changement par appel, pas de nouvelle disposition de l'historique imposée au jeu). Mesuré (église de `mak1f1`, héros + 1 allié, vitesses x1,25 / x1,5 / x2) : **aucun saut de plus d'une demi-case**, distance héros - allié ≤ ~0,96 case. **Limites** : au démarrage et à l'arrêt de la course l'allié change de distance par paliers (jusqu'à ~0,3 à 0,46 case, lissé) ; à x1,5 l'écart reste un peu plus grand qu'à la marche (~12 %, arrondi à une entrée paire) ; **sur la carte du monde les alliés prennent toujours de la distance en courant** (le jeu y lit toujours l'entrée 7 i). Pas essayé sous Windows.
- **Plume de la petite carte du monde** : l'icône (24 x 24) a son origine **en bas à gauche** (sommets de (0, 0) à (24, 24)) et la **pointe de la plume est ce coin** : elle est maintenant posée sur le point `(-225 + x * 450 / 256, 400 - y * 337.5 / 192)`, au lieu d'être centrée dessus. Vérifié en capture (la pointe est sur la case du héros). **Pas vérifié** : l'ancrage exact du jeu d'origine (aucune capture de référence), à confirmer à l'œil comme les carrés rouges. *(Établi depuis dans le code : `AddIcon(Vector3.zero, 31, true, 0.5)`, origine = coin bas gauche ; coordonnées corrigées lors de l'audit de fidélité du 01/11/2026.)*
- **Pas vérifié** : combat avec une vraie victoire (mes essais automatiques perdent toujours le combat) ; la boîte « Ragnar meurt ! » sur l'écran noir disparaît désormais elle aussi, avec la même règle.

## Retours de 14 h 25 : croix à l'écran, boutons à gauche, Taille de la croix, alliés (01/11/2026, #36)
- **Croix à l'écran, utilisable à la souris** (`hud_mobile.Boutons`, `_croix`, `croix_*`) : art d'origine de la feuille `Button` (anneau 256 x 256, huit pastilles 128 x 64 avec leur flèche, boule 64 x 64, halo ; la pastille et la boule de la direction tenue sont les versions orange). Un appui dans l'anneau la prend, la boule suit la souris (limitée à la moitié du rayon, 0,4526 depuis l'audit de fidélité), **huit secteurs de 45°** (zone morte 15 % du rayon, 0,124 depuis l'audit de fidélité) -> bits haut / bas / gauche / droite ajoutés à ceux du clavier **avant** la rotation de la caméra (`Jeu.pad`) : mêmes directions que ZQSD. ~~Presque transparente (40 %) après 0,5 s sans appui.~~ *(Retiré lors de l'audit de fidélité du 01/11/2026 : fondu inventé.)* Visible dans les mêmes conditions que les boutons (drapeau `Global.Flag`, ni menu, ni combat, ni carte ouverte) ; un appui tant qu'un message est affiché sert à tourner la page (comme avant). **En bas à droite par défaut** (à une demi-case du coin), **diamètre = 165 x (hauteur / 800) x option « Taille de la croix » du jeu (`g_pad_size` : 0 Grande 1,25 / 1 Moyenne 1 / 2 Petite 0,75) [valeurs corrigées dans l'audit de fidélité du 01/11/2026 : 161,28 et 1,225 / 1 / 0,775] x réglage « Taille de la croix »** (`croix_taille`, 50 à 200 %). Réglages : `croix` (afficher), `croix_taille`, position dans `boutons_pos['croix']`. Vérifié en capture (carte du monde : glisser à gauche / en haut déplace le héros, la pastille et la boule s'allument ; ville : bas de la croix = touche S, même déplacement ; 720p et 1080p ; option du jeu « Grande » = anneau plus grand).
- **Éditeur d'interface** : l'entrée « Boutons de l'écran » devient « Boutons et croix de l'écran » : « Taille des boutons », **« Afficher la croix »**, **« Taille de la croix »**, la croix se glisse comme un bouton (grille aimantée) ; masquée, elle reste visible (très pâle) dans l'éditeur pour être placée. Le panneau de réglage s'ouvre maintenant **en haut à droite** (les boutons sont à gauche, la croix en bas à droite).
- **Boutons Carte, Commandes, Discussion (et Mode de la carte) : à gauche par défaut** (colonne 0,4, mêmes lignes qu'avant : 1, 3, 12, 14). Les positions déjà enregistrées par le joueur sont conservées.
- **Fenêtre « Taille de la croix » (menu Paramètres)** : les trois boutons (Grande, Moyenne, Petite) **montent d'une rangée** (le premier est à la place du premier bouton de Paramètres ; `centrer_liste(None, None, 1)`, condition : fenêtre de titre type 27, pas d'étiquettes de réglage, 3 plaques).
- **Compagnons à la course** : plainte « Doc est collé à Ragnar ». **Non reproduit** : mesures en ville (église de `mak1f1` et sortie `maout`, `vitesse_course` 1,5, réglages du PC de Sylfried) : marche **0,80** case (écart du jeu 10), course **0,72** en régime établi (écart 6 x 0,24) ; en ville courante (écart 8) marche 0,64, course 0,72 ; à l'arrêt la distance reste celle de la course ; au départ depuis l'immobilité l'allié se détache après 3 pas (au lieu de 5) puis garde 0,72. Seul défaut trouvé : une image sans direction tenue pendant la course (une touche relâchée avant que l'autre soit enfoncée) ramenait le facteur à 1 et l'écart oscillait 6 / 8 : **anti-rebond** (`Moteur._aa` garde le facteur de course 6 appels de plus). Avec une coupure sur 5 pas l'écart reste fixe (6) ; distance 0,59 car ces pas-là sont à vitesse de marche. **Si le problème persiste, il faut le lieu exact** (nom de la carte, d'où on part, si on a changé de direction). **Carte du monde non faite** : dans les sauvegardes disponibles le héros y est seul (aucun allié à mesurer).
- **Pas vérifié** : l'ordre des tailles de la croix du jeu et les trois facteurs (1,25 / 1 / 0,75, valeurs choisies ; l'ordre Grande = 0, Moyenne = 1 (défaut), Petite = 2 vient du code : le curseur de la liste se place sur `g_pad_size`) ; l'écart exact de la croix d'origine (la croix du téléphone apparaît sous le doigt, celle du PC est fixe) ; l'option « Position de la croix » (`g_pad_pos`, valeur 1 par défaut) n'est pas utilisée.

## Retours de 15 h 25 et 15 h 32 : course sur toute l'horloge, bouton Menu Pause, réinitialisation des interfaces (01/11/2026, #37)
- **Course : retour à la toute première version, refaite proprement.** `_facteur_vitesse` (marche x course, 0,25 à 8) multiplie de nouveau **l'horloge du moteur** (`_boucle` : `acc += dt * f`, au plus `3 * ceil(f)` pas par image) : le héros, **les PNJ et toutes les animations** vont plus vite ensemble. Retirés : `Moteur.vitesse_heros` / `VITESSES_HEROS` (variables de vitesse du héros, #32 à #36), les crochets `_aa` (`TownPartyAction::AdjustArray`) et `_ew` (`Encount::execWalk`) et leurs variables (`_h_ecart`, `ecart_constant`, `_n_jeu`, `_f_mem`, `_f_cnt`, `_acc_enc`). Les anciennes sections (#30 à #36) décrivant ces rustines sont de l'historique.
- **Pourquoi plus de rustines** : le moteur fait simplement plus de pas par seconde, chaque pas est celui du jeu. L'historique des compagnons avance d'un pas à chaque pas du héros (écart inchangé, en ville comme sur la carte du monde) et `Encount::execWalk` compte par pas (taux de rencontre identique pour une même distance). Plus de risque de traverser les murs non plus : la foulée reste 0,16 par pas.
- **Mesures** (église de `mak1f1` puis `maout`, réglages par défaut, horloge réelle `DQ_TEMPS_REEL=1`) : marche 30 pas moteur/s, course x1,5 **~45 pas/s** (33 pas en 0,72 s) ; foulée du héros 0,16 par pas dans les deux cas ; distance de l'allié **0,80 en marche** (sonde moteur, écart du jeu 10 : 5 x 0,16) et **0,79 à 0,80 en course** ; constantes de vitesse du héros inchangées. Pas mesuré : PNJ en mouvement (aucun ne se déplace dans ces salles, mais leurs déplacements sont par pas), alliés sur la carte du monde (la sauvegarde de test n'en a pas), course à x4.
- **Chargement d'un état** : `Moteur.remettre_vitesses()` remet les cinq constantes de vitesse du héros à leur valeur d'origine (un état enregistré par une version #32 à #36 pendant une course les contenait majorées et plus rien ne les réécrit).
- **Bouton de la fenêtre Paramètres : « Menu Échap » devient « Menu Pause »** (`TXT_MENU_ECHAP` reste le nom de la constante) ; le menu s'appelait déjà « Pause » ; Échap l'ouvre toujours. Vérifié par capture (le libellé tient dans la plaque).
- **Éditeur d'interface : même réinitialisation complète pour tous les types** : « Rétablir cette interface » est maintenant le libellé de l'entrée pour **les boutons et la croix** (positions **et** tailles, via `Pause._remettre_boutons` ; l'affichage de la croix reste un choix du joueur) comme pour les dialogues et les fenêtres du jeu (taille + position horizontale + verticale, via `_rien_ov`) ; « Rétablir toutes les interfaces » reprend les deux. Avant, le choix « Boutons » ne rétablissait que les positions. Les ↺ de chaque curseur restent. Pas de réglage bouton par bouton (demande de Sylfried : « ça ira comme ça »). Vérifié par capture et par le fichier de réglages enregistré.

## Retour de 15 h 39 : libellé de la confirmation pour quitter (01/11/2026, #38)
- **« Quitter le jeu ? » devient « En êtes-vous sûr ? »** : seulement la ligne de question de l'écran de confirmation (`Pause._e_quitter`, au-dessus de Oui / Non) ; l'entrée « Quitter le jeu » du menu Pause et le titre « Quitter » de la fenêtre ne changent pas. Vérifié par capture.
- **Course** : question de Sylfried sur la possibilité d'accélérer le déplacement sans la vitesse globale : réponse donnée dans la conversation (c'est possible, c'était la version #32 à #36 ; coût : écart des compagnons, taux de rencontre, animations du héros non accélérées, risque de traverser les murs au-delà de x2 ; d'où le retour à l'horloge entière en #37).


## Audit de fidélité : croix, boutons de l'écran, bouton Mode, petite carte, listes (01/11/2026)
Branche `audit-pave`, sans numéro de PR. Détail des preuves (adresses, valeurs, types touchés) : voir « Audit de fidélité » des notes techniques. Ici : ce qui change à l'écran et ce qui reste à vérifier.

- **Établi et appliqué** : (1) les fenêtres Statut, la liste « Objets » du combat et le bouton Mode de la carte manquaient à cause d'une erreur du pipeline de mise en page (`layout.py`, argument des constructeurs `Make_*`) ; corrigé, `GENERATION` passe à 3 : **le jeu refait `ui_layout.json` au prochain lancement par `lancer_dq4.bat`** (quelques minutes, une fois). (2) Les quantités de la liste d'objets (`ItemNumCTRL`) s'affichent. (3) Croix : anneau 161,28 unités, échelles 1,225 / 1 / 0,775, pastilles à 104/256 du diamètre, zone morte 0,124 R, course de la boule 0,4526 R, prise 1,178 R ; **plus de boule orange ni de halo quand on la tient** (seule la pastille du secteur s'allume) ; **plus de fondu** (l'anneau est toujours opaque). (4) Petite carte : plan de -223 à 222,5 (largeur) et de 398 à 63,875, plume à `-223 + 1,740234 x`, `398 - 1,740234 y` ; croix rouge du code 4 (lieu spécial). (5) Boutons Carte, Commandes, Discussion : plaque du jeu (9 tranches, état appuyé), formats 72 x 64 et 63 x 56,8. (6) Bouton Mode : celui de la fenêtre de la carte (icône envoyée par le moteur), à la souris comme au clavier (touche M inchangée) ; le bouton Mode du HUD n'existe plus, et le HUD est entièrement masqué carte ouverte.
- **Retiré (inventé)** : le fondu à 40 % de la croix après 0,5 s (`croix_t`, `ATTENTE_CROIX`, `ALPHA_CROIX`), la boule et le halo orange en cours de déplacement, le diamètre 165 et les facteurs 1,25 / 0,75 (choisis en #36).
- **Vérifié par capture (xvfb)** : Statut (4 pages) avant / après, « Objets » du combat avant / après, fenêtres de carte avec Mode + Retour (clic souris : bascule puis fermeture), croix au repos et tenue, éditeur d'interface (3 plaques + croix), quantités par injection, croix rouge du code 4 par injection, jeu sans `ui_layout.json`.
- **Non vérifié** : (a) sur le PC Windows de Sylfried : rendu OpenGL réel (mes captures viennent de Mesa sous xvfb), régénération du cache par `lancer_dq4.bat`, dimensions des plaques et de la croix à ses résolutions ; (b) boutiques (types 58 et 60) : aucune sauvegarde de test n'y mène ; (c) ancrage de la croix rouge (supposé bas gauche), forme du shader de ses symboles ; (d) comparaison avec une capture Android (aucune disponible) : pas d'anneau flottant, pas d'animation extérieure à `TouchPad` ; (e) le bouton Mode n'existe plus dans les « menus simples » (sans `ui_layout.json`), où la fenêtre de la carte n'est de toute façon pas dessinée (comme avant) : la touche M reste disponible.
- **Pas fait** : grande carte du monde (type 26) : rectangle d'origine non lu, ancien rectangle conservé ; barre de rotation de la caméra de la croix et bouton de position de la croix (sans objet sur PC) ; position par défaut des boutons et de la croix (retour de Sylfried en #36) ; option `g_pad_pos` non reliée ; curseur doré oscillant des menus (inventé, aucun équivalent dans le jeu d'origine).
- **Fichiers touchés** : `outils/ui_il2cpp/layout.py` (`export_type`), `outils/ui_il2cpp/entete.py`, `dq4_pc/lancer_dq4.bat`, `dq4_pc/ui_menu.py` (`Fenetre.param_int`, `_item_num`, `special`, `Rendu.plaque`, `Rendu._carte`), `dq4_pc/fenetre.py` (`on_mouse_press`, `on_mouse_release`, `_plan_fenetre`), `dq4_pc/hud_mobile.py` (constantes, `Boutons.*`, `_plaque`, `_croix`).

## Avant la partie : logos, titre, menu de départ, nom, licence (01/11/2026, #39)
Demande de Sylfried : tout ce qui précède le lancement d'une partie (écrans de lancement, écran-titre, continuer / créer / supprimer une aventure). Les faits tirés du code d'origine sont dans les notes techniques (« Avant la partie ») ; ici : ce qui s'affiche, comment tester, ce qui reste à vérifier.

- **Déroulement** (sans option : `--slot` vaut 0 par défaut) : logos **SQUARE ENIX** puis **ArtePiazza** (fondu 1 s, maintien 3 s, fondu 1 s, comme `Boot.Logo` ; un clic ou une touche pendant l'entrée saute le maintien) → **titre** (ciel et logo du moteur, « Touchez l'écran » clignotant, ligne de copyright ; premier appui = fin de la démo, second = menu) → **menu de départ** → partie. Le moteur se charge pendant les logos (les logos ne rallongent pas le démarrage). `--slot 1` à `5` charge directement ce journal comme avant (sans logos ni titre) ; `--sans-logos` saute les logos ; `--logos` les joue même pour une capture (test).
- **Menu de départ** : Continuer votre aventure, Reprendre une aventure interrompue, Créer un nouveau journal, Supprimer un journal, Sauvegarde automatique, Licence, Retour (en bas à droite). Souris, flèches + Entrée / Espace, Échap et Retour arrière = annuler. Les listes de journaux (type 54) montrent nom du héros, chapitre, niveau, durée de jeu et lieu, « Inutilisé » pour un emplacement vide ; le menu et les messages (« Voulez-vous vraiment… », Oui / Non) sont ceux du moteur.
  - **Continuer / Reprendre / Auto** : charge la banque choisie puis la partie reprend (ville ou carte du monde) avec le fondu d'origine.
  - **Créer** : emplacement → (confirmation si l'emplacement est déjà pris) → **saisie du nom** → choix du sexe → création → prologue (testé jusqu'à `mlb1a`).
  - **Supprimer** : emplacement → confirmation Oui / Non → le moteur vide la banque (`DLED`).
  - **Licence** : fondu au noir, texte de licence d'origine (titres en orange) dans une fenêtre à défilement (molette, flèches, Page haut / bas, Début / Fin, ou en glissant la barre), bouton « Privacy Policy » (ouvre la page de confidentialité dans le navigateur), Retour ferme.
  - Échap à la racine : « En êtes-vous sûr ? » (Oui / Non) du moteur ; le menu Pause n'existe pas avant la partie.
- **Saisie du nom** (`saisie_nom.py`) : fenêtre dessinée dans le style du jeu : une fente par caractère (8 au plus, valeur envoyée par le moteur), grille de 5 colonnes x 7 lignes (alphabet minuscules / majuscules, lettres accentuées, espace - , . ! ?) et boutons « Alphabet », « à À », « Maj. », « Suppr. », « OK », bouton Retour. Souris (clic droit = effacer), **clavier de l'ordinateur** (tout caractère de la grille ; après une frappe le curseur passe sur OK, Entrée valide ; Retour arrière efface ; Tab = Alphabet / accents ; Échap = Retour), flèches + Entrée. Un nom refusé par le moteur affiche **son** message (« Désolé, ce nom ne peut pas être utilisé. », fenêtre de message habituelle).
- **Images extraites une seule fois** : `cache/ap_*.png` et `ap_licence.txt` (logos, « Touchez l'écran », copyright, texte de licence) viennent des APK au premier lancement (`avant_partie.preparer`, avant les logos).
- **À savoir après la mise à jour** : `GENERATION` passe à 3 (audit de fidélité) : `lancer_dq4.bat` refait `ui_layout.json` une fois (quelques minutes) et le cache des cartes se refait en arrière-plan.
- **Corrections au passage** : liste « Reprendre / Auto » (le titre flottait au-dessus de son onglet : `Fenetre._titre_onglet`) ; « Sauv. cloud » retirée (sans Google Play Games ni serveur, l'original la retire aussi pour Amazon : octet `g_isAmazon` du moteur mis à 1, plaque masquée) ; ports du moteur : drapeau `ferme` (un message d'arrêt tardif ne rouvre plus un écran fermé).
- **Vérifié (captures et scénarios sous xvfb, Mesa)** : logos (durées et fondus) ; titre (clignotement, copyright, deux appuis) ; menu racine sans case cloud ; Continuer → chargement ; Créer sur emplacement vide (nom, sexe, création, prologue) et sur emplacement occupé (confirmation) ; Supprimer (confirmation, `DLED` écrit) ; Reprendre et Auto (listes) ; Licence (texte, défilement, retour) ; Échap à la racine ; annulation du nom ; `--slot 1` ; premier lancement avec cache vide (`preparer`) ; l'ensemble refait sur la branche fusionnée avec la mise en page de génération 3.
- **Non vérifié (honnêtement)** : (a) **rendu OpenGL réel sur le PC Windows** (mes captures viennent de Mesa) et la régénération du cache par `lancer_dq4.bat` ; (b) la **disposition du clavier du nom est la mienne** : l'origine de la grille et les boutons de fonction de l'original n'ont pas été retrouvés dans le code (la page de départ est en minuscules, Retour arrière / « Suppr. » efface, OK exige au moins un caractère : choix du portage) ; (c) le **nom refusé** (message 833011 du moteur) n'a pas été déclenché en test ; (d) le choix du sexe à la manette (curseur) ; (e) les entrées « En ligne », Sauv. cloud, Network et le bouton de portail (`[0,6]`) ne sont pas reproduits (sans objet sur PC) ; (f) la **démo de caméra** de la première phase du titre (rôle non établi) et la cadence réelle des fondus (30 Hz supposé) ; (g) le ciel du titre est tuilé pour remplir le 16/9 (garder tel quel, décision du 01/11).
- **Fichiers** : `dq4_pc/avant_partie.py` (nouveau), `dq4_pc/saisie_nom.py` (nouveau), `dq4_pc/fenetre.py` (titre, menus, nom, licence, Échap, options), `dq4_pc/moteur.py` (`PARTIE_DEPART`, `G_IS_AMAZON`, drapeau `ferme`, `DQ_MENUDBG`), `dq4_pc/ui_menu.py` (`_titre_onglet`, cloud masqué), `dq4_pc/pause.py` (`ouvrir(page)`), `README.md`.

## Retours de 18 h 02 : menu de départ, Sauvegardes, licence, saisie du nom (01/11/2026, #40)
Retours de Sylfried après #39 (5 captures). Ce qui concerne le menu de départ, les sauvegardes, la licence et la saisie du nom (le prologue, la caméra et le bip sont traités plus bas, dans la même section).

- **Menu de départ centré dans un cadre noir** : le groupe de boutons est centré en hauteur (`Fenetre.centrer_menu`, décalage de −(min + max) / 2 de tous les maillages) et entouré du cadre noir des autres menus (`Fenetre.cadre_menu`, `fenetre._cadre_depart`, marge de 22 unités). Pas de changement pour les listes de journaux (type 54), qui restent en bas comme dans l'original.
- **Bouton « Sauvegardes »** (à la place de « Sauv. cloud », plaque 8 du menu racine) : ouvre un écran du portage (`ecran_sauvegardes.py`, cadre noir, plaques et bouton Retour du jeu) avec **Exporter** et **Importer**. Souris (survol = cadre jaune), clavier (flèches + Entrée / Espace, curseur doré, Échap / Retour arrière = fermer) et clic droit = fermer.
  - **Exporter** : boîte « Enregistrer sous » de Windows (tkinter, dans un fil à part : la fenêtre du jeu reste vivante), nom proposé `dq4_sauvegardes_AAAAMMJJ_HHMMSS.zip`. Le .zip contient `data1.dat` à `data5.dat`, `data9.dat` (tels que le moteur les lit : dossier d'écriture d'abord, sinon dossier de lecture) et `etats/etat_NN.dqs` (états instantanés).
  - **Importer** : boîte « Ouvrir » (un .zip de ce genre, ou des `data1.dat`… copiés depuis un téléphone Android, ou des `etat_NN.dqs`). Les tailles sont vérifiées (journal 15 360 octets, `data9.dat` 512). **Rien n'est écrasé sans copie** : les fichiers du dossier d'écriture remplacés sont d'abord copiés dans `<sauvegardes>/avant_import_<date>/` ; le dossier de lecture (tes sauvegardes d'origine) n'est jamais modifié. Après l'import, le moteur relit le catalogue (`SaveLoad::getCatalogView` / `getCatalogRecent`) : les listes Continuer / Reprendre / Supprimer / Auto montrent aussitôt les nouveaux journaux.
  - **Limite connue** : l'état grisé / absent des boutons du menu de départ (par exemple « Continuer » grisé quand il n'y avait aucun journal, ou « Sauvegarde automatique » absent) est fixé par le moteur à la création du menu ; si l'import le change, le panneau le dit (« relance le jeu »).
  - **Sans tkinter** (ou si la boîte échoue) : repli sur des dossiers du portage : export dans `<sauvegardes>/export/`, import depuis `<sauvegardes>/import/` (le dossier s'ouvre dans l'Explorateur s'il est vide).
- **Licence** : une section en anglais, en tête du texte d'origine, décrit le portage (projet de fan non officiel, sans contenu du jeu, moteur d'origine sous émulateur Unicorn, couche Unity réécrite en Python / pyglet, aucune donnée envoyée sur Internet) et liste les composants utilisés (Python, Unicorn Engine, pyglet, NumPy, Pillow, UnityPy, Capstone, SoundFile / libsndfile) avec leur licence. Le texte d'origine suit, **inchangé**. La licence d'Unicorn est donnée « GNU GPL v2 » (c'est ce que dit sa description ; ses métadonnées de paquet affichent « BSD » par erreur) ; à vérifier si tu redistribues quoi que ce soit.
- **Textes des listes** : le texte aligné à droite (chapitre, niveau, durée) ne dépasse plus de la plaque (`Fenetre._largeur_plaque` : pour les types 53 et 54, la largeur disponible va jusqu'au bord de la plaque, marge de 7 unités).
- **Saisie du nom : flèche ou cadre jaune selon le dernier périphérique** : après un clic / un mouvement de souris, seul le bouton survolé a son cadre jaune (pas de flèche) ; après une touche, le curseur doré apparaît et le cadre jaune disparaît. La flèche reste dans le cadre de la fenêtre. Même règle que le menu Pause (`J.dernier_peripherique`, changé par `on_key_press` / `on_mouse_*`).
- **Fichiers** : `dq4_pc/sauvegardes.py` (nouveau : export, import, boîtes de dialogue), `dq4_pc/ecran_sauvegardes.py` (nouveau : l'écran), `dq4_pc/ui_menu.py` (`centrer_menu`, `cadre_menu`, `_largeur_plaque`), `dq4_pc/fenetre.py`, `dq4_pc/moteur.py` (`statut_catalogue`, `relire_journaux`, `DQ_SAVEDBG`), `dq4_pc/saisie_nom.py`, `dq4_pc/avant_partie.py` (`LICENCE_PROJET`).
- **Vérifié (xvfb)** : menu centré et cadre ; panneau (souris et clavier jusqu'à la plaque) ; export (6 fichiers dans un .zip) ; import (journaux 1 et 2 échangés : la liste « Continuer » les montre échangés, sans relancer) ; listes Auto / Reprendre / Créer / Supprimer sans débordement ; saisie du nom (souris = pas de flèche, clavier = flèche) ; texte de licence.
- **Non vérifié** : les **boîtes de dialogue Windows** (tkinter n'existe pas dans mon environnement : seul le repli par dossiers a été exécuté) ; le cas « premier import sans aucun journal » n'a été vu qu'au niveau du message (les boutons du menu ne se mettent à jour qu'au relancement).
- **Caméra pilotée par le jeu** (#47 : l'option « Centrer la caméra sur le joueur » n'existe plus, la caméra est toujours centrée tant que le joueur l'a) : l'option « Centrer la caméra sur le joueur » ne valait que lorsque le joueur avait la caméra. Quand le jeu la pilote (scène, événement, prologue, chute, sort de retour), la caméra du jeu s'applique telle quelle (avec les bornes 16/9 de la visionneuse, comme option désactivée). Critère : le **verrou de la `TownCamera` du moteur** (`Moteur.camera_jeu()`, octet +0x3e), lu à chaque pas du moteur ; `cam_jeu`, `cam_poids` (entrée / sortie en douceur des bornes 16/9), `cam_saut` (coupure de plan ou changement de carte : le centrage suit aussitôt), `CAM_SAUT_VILLE` (1,5 unité par pas). Les scènes à caméra libre (`cam_libre`, paquet 11 bit 7) gardent l'ancien comportement ; la carte du monde n'est pas concernée. `DQ_CAMV=n` affiche l'état toutes les n images.
  - **Pourquoi ni le drapeau « joueur verrouillé » ni la distance** : le bit 0x4 de `Global.Flag` est posé pendant tout message (le héros est figé) alors que la caméra suit toujours le héros : il aurait supprimé le centrage à chaque dialogue. L'ancien critère (cible à moins de 60 unités du héros) ne marchait pas dans le prologue (cible à 23 unités : la salle apparaissait au lieu de l'écran noir « Prologue »).
  - **Vérifié** (captures xvfb) : prologue (verrou à 1 jusqu'à l'image ~368) : option activée = option désactivée au pixel ; après libération, caméra centrée ; exploration libre église → porte → `maout` et message de PNJ : identiques au pixel à l'ancien code ; le verrou reste à 0 pendant jarres et tonneaux (sonde du moteur).
  - **Non vérifié** : une scène à caméra **visible** avec le héros près d'un bord de carte (aucune n'a pu être jouée) ; l'entrée dans le verrou par un déplacement lent ; chutes et sorts de retour (appelants identifiés, non joués) ; jarre / coffre avec message en capture (seulement dans la sonde sans fenêtre).
- **Le « bip » à l'ouverture d'une boîte de dialogue est normal** : c'est le bruitage 300 (`SE0300`, paquet 35), commandé **par le moteur** : `ui_MsgLoop` (0x157044) le joue au début d'un message si le joueur vient de reprendre la main (octet `ui_MsgBeginTalkSE`, lib + 0x252388, armé par `PlayerManager::setLock(false)`), puis à chaque passage à la page suivante (c'est « le même bip »). Les messages suivants d'un même événement n'en font pas à l'ouverture, seulement au changement de page. La visionneuse joue un seul son par paquet, avec le bon fichier ; rien n'a été changé. Un tonneau ou une jarre vide ne donne ni message ni bip. **Non comparé** au jeu Android : le volume réel (`s_seVolume` × volume du fichier supposé).
  - Écart de fidélité mineur signalé, non corrigé : les touches Entrée (Commandes), Espace (Discussion) et M (Carte) ne jouent pas le bruitage 300 alors qu'un clic sur le même bouton à l'écran le joue (comme `TouchPad.internalUpdate`).
- **Prologue** (nouveau journal) : le portage montre maintenant la séquence d'origine : fond noir, **bandeau doré à fond bleu « Prologue »** (apparition puis fondu), **cinq coups d'épée** (traînées et éclats, vus par une caméra qui regarde le vide), puis la caméra revient vers le héros et la salle apparaît ; Espace (ou Entrée) termine l'attente de touche, puis « Eh bien alors, [nom] ? ». Il manquait : un **second plan de fondu** (le moteur en pilote deux ; le bit 14 du paquet 9 choisit « FadeForBG », derrière les fenêtres, ou « FadeForMenu », devant tout), la **texture du bandeau** (`hyodai1`, extraite des APK une seule fois au premier lancement, 3,7 s) et la caméra (voir plus haut). La note « bit 14 = plan devant l'interface » était inversée : corrigée dans les notes techniques.
- **Boîte violette de la transition liste → saisie du nom** : un message du moteur arrivait après la fermeture de la fenêtre (même image) et la faisait revivre une image en boîte « simple » violette ; il est maintenant ignoré (`Interface.appliquer`). C'est le même mécanisme que la boîte de fin de combat. Vérifié sur choix de la sauvegarde → nom, emplacement occupé → confirmation, sexe → création, Supprimer, Licence → titre.
  - **Vérifié** (xvfb) : bandeau, coups d'épée, salle (nouveau journal complet) ; `--slot 1` identique au pixel avant / après sur 6 images ; combat : identique sauf les effets de bord ci-dessous.
  - **Effets de bord** : les fenêtres s'assombrissent avec les fondus de devant ; en fin de combat « Ragnar meurt ! » et le texte de la voix se lisent sur le noir (avant, la boîte était masquée) ; le fond reste noir jusqu'à la commande du moteur.
  - **Non vérifié** : la **taille et la place des éclats d'épée** par rapport au jeu d'origine (60 à 80 pixels à 720p, valeurs tirées des paquets ; aucune capture du vrai jeu) ; la hauteur du bandeau (225, supposée) ; la teinte de la carte du prologue (paquet 33, ignoré) ; l'extraction de `hyodai1` sous Windows (sans UnityPy ou sans APK, le bandeau est simplement absent) ; le comportement avec une « vitesse des transitions » autre que 2.



## Retours de 20 h 46 : avant-partie centrée, Pause, éditeur d'interface, affichage, textes, son (01/11/2026, #41)
Demande de Sylfried (vingt points, 10 captures). Travail fait par six enquêtes en parallèle puis fusionné. **Établi** = lu dans le code ou mesuré sous xvfb (Mesa) ; **Supposé** = déduit ; **Non vérifié** = à essayer sur son PC Windows.

### Avant la partie
- **Logo du titre relevé** : toute la scène de la carte `ev01` (ciel, logo, île) monte de `TITRE_HAUT = 0,3` (coordonnées d'écran normalisées, +1 = demi-hauteur ; décalage `s_yOffset` de `_camera_ville`) : le groupe logo + île a son centre au milieu de l'écran (haut du logo à 148 px, bas de l'île à 570 px sur 720). « Touchez l'écran » et le copyright (dessinés par la visionneuse) ne bougent pas. Une seule valeur à régler si le décalage ne plaît pas (`DQ_TITRE_DY` pour essayer).
- **Menus d'avant-partie centrés** : la liste des journaux (type 54 : Continuer, Créer, Supprimer, Reprendre, Auto) et le choix du sexe (type 55 vu comme fenêtre du moteur) sont posés par le jeu au bas de l'écran portrait ; ils sont maintenant centrés à l'écran dans le cadre noir du menu de départ (`FENETRES_CENTREES`, `Fenetre.centre_visible()` : décalage du repère de dessin, positions intactes, les zones tactiles suivent). Le nom, la Licence et l'écran Sauvegardes l'étaient déjà. **Restent à leur place** : les boîtes de dialogue (message + Oui / Non : suppression, écrasement…).
- **Plaque du haut sans texte** : le moteur n'envoie l'étiquette de la case 4 (« Sauvegarde automatique ») que si `data5.dat` est lisible ; sans lui la plaque existait vide. Reproduit en retirant `data5.dat`. Elle est cachée (`Fenetre.cacher_plaque_vide(4)`) : mise en page inchangée, plaque ni survolée ni choisie. **Cause chez Sylfried** : « Revenir à l'écran titre » appelle `killbank(4, false)` comme le bouton d'origine : **la sauvegarde automatique est effacée au retour au titre** (comportement du jeu d'origine, voir plus bas). **Supposé** : l'original cache aussi la plaque (non vu sur mobile).

### Menu Pause (Échap)
- **Commandes** : plus de touches « Courir » / « Accélérer la caméra » (maintenir / appuyer) ; une seule **touche d'accélérateur** (tenue, Maj par défaut) et un **multiplicateur de l'accélérateur** (x1,5, de 1 à 2) pour la marche et la caméra. Nouvelle section **« Vitesses »** sous « Caméra » : Vitesse de marche, Vitesse de caméra, Vitesse de transition, Touche d'accélérateur, Multiplicateur de l'accélérateur (renommé en #43). Migration silencieuse des anciens `reglages.json` (`courir` / `cam_accel` → touche d'accélérateur, `vitesse_course` → `vitesse_accel` ; `accel_camera` abandonné). Une touche = une seule action.
- **États** : la fenêtre garde la largeur de sa version vide (540 x k) ; la date se réduit au besoin.
- **« Revenir à l'écran titre »** (ex-« Quitter le jeu », sans flèche) : confirmation « En êtes-vous sûr ? » puis `Moteur.retour_titre` = `killbank(4, false)`, `PlayerManager::setLock(true)`, `Global::startTitle`, comme le « Oui » du bouton d'origine (`TownMenu_OPERATION_SETTING`, état 5), qui n'est plus joignable. La page `quitter` reste pour la question « quitter l'application » du menu de départ.
- **Bouton « Paramètres » du menu en jeu** (page 2 du menu Divers, liste type 8, indice moteur 7 ; pas dans la racine) : garde son nom et ouvre le menu Pause. Le moteur est patché en mémoire (`cmp w8, #7` → `#4095` à 0x16ef28 dans `TownMenu_OPERATION_ROOT::menuUpdate`) et un crochet lève `Moteur.demande_pause` ; ré-appliqué après chargement d'un état. La fenêtre d'origine (type 27 « Config ») et le bouton « Menu Pause » qu'on y avait ajouté n'existent plus. **Non couvert** : « Taille de la croix » d'origine (remplacée par `croix_taille`).
- **Texte et défilement** (nouvelle page) : **Vitesse du texte** (7 crans, de Très lent à Instantané, « Normal (jeu) » = 4 lettres par image moteur ; le jeu d'origine n'a pas cette option : crochet de la visionneuse), section **Combats** : **Défilement automatique** (interrupteur) et **Vitesse de défilement** (4 crans) = `OptionStatus.battleSpeed` (`g_Option + 5`, enregistré dans chaque sauvegarde ; attente 12 / 22 / 32 / 42 images, 4 = à la main). **Les dialogues du terrain ne défilent jamais seuls** (400 images d'attente mesurées) : seul le défilement des combats existe. Aucune valeur n'est imposée tant qu'on n'y touche pas.
- **Son** : catégories Général, Musique, Jingles et fanfares, Bruitages, Interface (SE 300 à 304 : bip de message et boutons ; 302 / 303 supposés), chacune avec interrupteur et volume 0-100 %, appliqués tout de suite aux sons en cours ; sur la page Son les sons reprennent (jeu arrêté) pour entendre les réglages. Unity n'a ni voix ni canal « ME » : aucune catégorie inventée. Les options volume du jeu (fenêtre Paramètres d'origine, `(indice + 1) x 0,2`) sont prises en compte (inaccessibles depuis le retrait de cette fenêtre : valeur de la sauvegarde).
- Outils : `outils/test_son_mixage.py`, `test_reglages_son_texte.py`, `test_texte_defilement.py` (`--apk`, `--saves`, `--slot`).

### Éditeur d'interface
- **« Afficher cette interface à l'écran »** ne concernait pas que l'interface choisie (c'était `R['boutons']`, global : boutons et croix, aucun effet sur les fenêtres du jeu) ; il est maintenant propre à l'interface choisie : « Boutons et croix de l'écran » → `boutons` ; toute fenêtre du jeu ou « msg » → clé `interface_masquees` (liste de noms ; fenêtre masquée : mise en page conservée, ni dessinée ni cliquable ; dans l'aperçu de l'éditeur, assombrie avec l'étiquette « Masquée »). Ordre : 1) Interface à modifier, 2) Afficher cette interface à l'écran, puis taille / position, grille, rétablir.
- **54 entrées en 11 groupes** (intertitres dorés non sélectionnables) : Écran tactile, Dialogues (messages, Oui / Non, Titre du chapitre), Menu en jeu, Objets, Équipe et statut, Divers, Cartes, Combat, Boutiques et banque, Églises, Casino. **18 entrées retirées** (`RG.FENETRES_RETIREES`) : lancement du jeu (StartMenuFirst / Second / Select, StartNameEntry, SaveOverwrite, TitleTouch, PortalButton, License, ViewVolumeDecision, Network*), « Aperçu d'objet » (`NENE_ItemView`), `Config`, `MagicInfo`, `MonsterName`, `BattleHoppingNumber`. Réglages enregistrés des noms retirés purgés au chargement. « Oui / Non » est maintenant relatif à la fenêtre de message.
- **Fenêtre flottante « Interface » déplaçable** : appui long (0,35 s) = déplacer (soulèvement + liseré doré), appui court = replier / déplier (Tab marche toujours), double clic sur la barre = retour à la position initiale calculée pour l'interface choisie ; toujours dans l'écran ; position gardée pour la session seulement. `DQ_APPUI_LONG`, `DQ_DOUBLE_CLIC`. **Supposé** : un doigt arrive comme événement souris. Harnais de test : `!x!y` (appui), `^x^y` (glisser), `~@x@y` (déplacement), `+TOUCHE` / `-TOUCHE` (touche tenue).

### Affichage
- **Plein écran dès l'ouverture de la fenêtre** (logos compris) : `fullscreen=True` à la création à la résolution du bureau ; repli en fenêtre si échec (`--plein-ecran`). **Non vérifié** : absence de flash sous Windows ; le réglage `resolution` ne s'applique pas au lancement en plein écran.
- **Rendu hors écran** (`postfx.py`) : renderbuffers MSAA couleur + profondeur 24 bits, résolution vers texture, passe finale (réduction bilinéaire, netteté type CAS, gamma). Contournement total sans réglage actif (msaa 0, échelle ≤ 1, netteté 0, luminosité 1) ; repli sur le dessin direct à toute erreur GL. Nouveaux réglages : `msaa` (0, 2, 4, 8 ; à chaud, plafonné à `GL_MAX_SAMPLES` avec une note rouge), `echelle_rendu` (suréchantillonnage x1,5 / x2), `nettete` (0 à 100 %), `luminosite` (50 à 150 %). FXAA / SMAA, scanlines, contraste / saturation, mise à l'échelle entière, vsync, limiteur d'images, bloom : écartés (floutent le pixel art ou sans objet).
- **Shaders** : « Régions lissées » et « Bicubique » **retirés** (le bicubique mesurait -27 % de netteté) ; un ancien `mode_sprites` 2 ou 3 devient 1 (EPX x8), le 4 (pixel perfect) garde son numéro (`--hd 4` valable). **Lissage des textures** : n'agissait que sur le décor et la carte du monde, il s'applique maintenant aussi aux sprites, monstres et bulles.
- **Fleurs qui scintillent** : deux causes : (A) z-fighting entre décors plats à découpe superposés (relèvement de 3 mm des triangles superposés par `decors_plats.py` + décalage de profondeur par groupe de textures) ; (B) bords de découpe au test alpha non lissés par le MSAA de fenêtre → alpha-to-coverage dans le rendu hors écran. Mesuré : variation temporelle -78 % avec msaa 4. **Limite** : avec anticrénelage et suréchantillonnage sur « Aucun », seul (A) est corrigé.
- Outils : `--options-test "image:Libellé=valeur;..."`, `DQ_ZDEBUG`, `DQ_CARTE_DEPL`, `DQ_SANS_DECALAGE`, `DQ_SANS_A2C`.

### Textes, boutiques, effets
- **Police des menus** : en langue 1 (celle du patch FR) la police est la police bitmap Unity **SE-GARRIR** (« Garrick », serif, 20 px, interligne 23,525, ascent 18,887, 218 glyphes, atlas 256 x 256), **pas** GMaruGoPro-M (japonaise, utilisée à tort jusqu'ici ; `DQ_POLICE_GMARU=1` pour comparer). Extraite de `base.apk` (`ui_garrir.json` / `.png`, `PoliceBitmap`). **Les textes ne sont plus comprimés** : l'écart texte / plaque est celui du mobile (le texte déborde comme sur mobile). Corrige aussi la police du bandeau de chapitre (`Make_Chapter` : seule image = `Menu/map/hyodai1`, déjà affichée ; titre dans le nœud 1558). **Supposé** : placement vertical ~1 px plus bas ; pas de comparaison au pixel avec le mobile. `pause.py` et l'aperçu de l'éditeur gardent `ui_font.otf`.
- **Boutiques** : le curseur clavier garde la rangée entière ; dans les types 58 / 59 (achat) et 63 (quantité de vente), gauche / droite (déplacement, caméra, L / R) envoient `[port, 1, rangée, 8 ou 4]` comme le toucher d'une flèche ; le moteur ne fait que ±1 (quantité de 1 à 9 avec bouclage ; pas de ±10 dans l'original). **Non vérifié** : types 28 et 63.
- **Sort Morph** : événement d'histoire (église, grenouille / lapin et Élisa), pas un sort de combat ; nuage = modèle 5902 (32 x 32, 29 images, SE 361, shader 3). (1) **Ordre** : les effets-maillages de ville (files de rendu : Chara 3000, DssaChara 3100, DssaMonster0 3150, DssaMonster1 3200, DssaCharaTransparent / Riseup 3850, ZTest Always) passent **après** les sprites : dessinés devant et ancrés sur le personnage visé (`_ancrer_effets`). (2) **Latence** : première texture chargée à froid (2,7 s mesurées, 0,05 s à chaud) ; les 186 textures d'effets `m\d{4}` sont préparées en arrière-plan avec le reste (`donnees.py`, `preparation.json` reconstruit une fois). **Non vérifié** : taille et placement exacts du nuage d'origine ; Morph d'un monstre en combat.
- **Texte du prologue sur écran noir** (« Et c'est ainsi que commence notre histoire… ») : **clos** (Sylfried, 01/11 à 23 h 33 : « c'est bon » ; rien n'a été changé). Notes d'enquête, avant ce retour :  Message moteur 200119 (`@a@bEt c'est ainsi que commence notre histoire...\n@c0@`, sans nom) ; côté Unity, `MenuMessage` n'a que les types de canevas 0 (terrain) à 3 (combat) : aucun mode centré / sans cadre ; **Supposé** : l'original l'affiche comme un message normal. Le moment n'a pas pu être reproduit (il faut jouer le prologue jusqu'au bout) : il faut voir la capture de Sylfried ou une description de ce qui choque.

### Règle « case assombrie » / « flèche » sur mobile (réponse à Sylfried)
- **Assombrir = état « appuyé », uniquement au doigt** (`MenuPortItem.Update` 0xD0670C : pushState 1 = `SetPush(true)`, 2 = `SetPush(isHit)`, 3 = relâché ; `SetPush` n'a que 4 appelants). Plaque : décalage de texture (0,1875 ; 0) (`IButton`, 0xD043CC) ; bouton-icône : `Material.color` à 0,75 sur les 4 canaux (0xCFF9C8, 0xD0469C). Le doigt qui sort rallume la case, qui se rassombrit au retour ; on valide en relâchant sur le bouton.
- **Il n'y a pas de flèche de sélection** dans les menus du build mobile (ni curseur clavier / manette) ; le message curseur `[4, n]` du moteur est ignoré par Unity. Les flèches du jeu sont : ▶ doré du tour de combat (`BattleUpCursor`), boutons ◀ ▶ de changement de page, ▲▼ de certaines plaques, ▼ de fin de page. La convention du portage (cadre jaune à la souris, flèche au clavier) est donc **une addition PC** ; seul l'assombrissement au clic vient de l'original. Corrigé : une flèche de page appuyée s'assombrit à 75 %, plaque et flèche se rallument quand le pointeur sort. **Non codé** : état `etat` piloté par le moteur pour les boutons-icônes (< 0 caché, sinon 0,75) ignoré ; `_est_bouton` n'accepte que les parts 7 et 10.


## Retours de 23 h 24 : fenêtre, Pause, éditeur, titre (dragon), caméra, sprites (01/11/2026, #42)
Dix-sept points de Sylfried, traités par six enquêtes en parallèle puis fusionnés. **Établi** = lu dans le code ou mesuré sous xvfb (Mesa) ; **Supposé** = déduit ; **Non vérifié** = à essayer sur son PC Windows. Sylfried a validé tout le lot #41, y compris le texte noir du prologue (clos, rien changé).

### Démarrage et fenêtre
- **Écran de chargement noir** : plus aucun texte au démarrage (« Chargement de la sauvegarde... », « Chargement du moteur... », « Chargement de la carte... » retirés ; messages seulement en console). La fenêtre est créée cachée dans le mode enregistré puis affichée après une première image noire. Mesuré : 0 pixel non noir pendant les attentes (1595 à 2151 avant).
- **[Remplacé en #43 : plus de plein écran exclusif ; voir la section #43.] Trois modes** (`mode_fenetre`) : 0 fenêtré, 1 **plein écran** (fenêtre sans bordure à la résolution du bureau = le plein écran d'avant, pyglet Win32 `fullscreen=True`), 2 **plein écran exclusif** (vrai changement de mode d'affichage vers « Résolution » : mode le plus proche, 16/9 de préférence, ≥ 24 bits, fréquence la plus haute ; restauré à la fermeture par `on_close` + `atexit`). Ancien booléen `plein_ecran` migré (vrai → 1) puis plus écrit. `--plein-ecran 0|1|2`. Repli défensif exclusif → plein écran → fenêtré avec message console, à la création et à la bascule ; le rendu hors écran (`postfx.py`) est recréé après chaque changement de mode. Sémantique de « Résolution » : fenêtré = taille de la fenêtre ; plein écran = sans effet (ligne grisée, note) ; exclusif = résolution réelle de l'écran.
- **[Remplacé en #43 : F11 / Alt + Entrée basculent plein écran ↔ fenêtré.] F11 / Alt + Entrée** : bascule exclusif ↔ mode précédent (`mode_fenetre_retour`, jamais 2) depuis n'importe quel écran (logos, titre, menu de départ, jeu, Pause) ; le raccourci **modifie le réglage « Fenêtre »**. F11 est une touche réservée (non assignable). « Discussion de groupe » (Alt) se déclenche maintenant au **relâchement d'Alt seul** : Alt + Entrée, Alt + Tab et Alt Gr ne la déclenchent plus. `DQ_SIM_ECHEC` (2, 1, 2,1, 2s) simule un refus. Test : `outils/test_mode_fenetre.py` (23 tests). **Non vérifié** (Windows) : vraie bascule de résolution, refus du moniteur, restauration du bureau après plantage, Alt-Tab en exclusif (non géré : le moniteur garde la résolution du jeu), multi-moniteurs, DPI, Alt Gr sur AZERTY réel.
- **Page Affichage, nouvel ordre** (état #42 ; lissage des textures et correction des bords ont été supprimés en #43, voir l'ordre actuel dans la section #43) : Fenêtre, Résolution, Netteté, Shader, Lissage des textures, Effet de vignetage, Anticrénelage, Suréchantillonnage, Luminosité, Distance caméra, **Correction des bords des sprites** (nouvelle), Centrer la caméra sur le joueur, Interface (en dernier).

### Pause : Son, Vitesse de défilement du texte, Commandes, cadre jaune
- **Son** : plus de sections ; une ligne par type de son (Général, Musique, Jingles et fanfares, Bruitages, Interface) : nom | barre de volume | % | bouton haut-parleur (muet) | bouton rond (défaut). Clavier : haut / bas = ligne, gauche / droite = volume, Entrée = muet, Suppr = défaut ; souris : barre cliquable / glissable. **Défaut = volume par défaut ET son remis** (décision de l'agent, à valider par Sylfried). Ligne coupée : grisée, haut-parleur barré. Le mixage n'a pas changé (le muet bascule les interrupteurs existants ; Général = muet global).
- **« Texte et défilement » devient « Vitesse de défilement du texte »** : plus de sections ni de « Défilement automatique ». « Vitesse du texte » (Très lent à Instantané, « Normal (jeu) » devient « Normal ») puis **« Messages en combat »** : Rapide / Moyen / Lent / Manuel = `OptionStatus.battleSpeed` 0 / **2** / 3 / 4 (`BattleAutoFeed::setMessageSpeed` 0x201558 : 0..3 = attente 12 / 22 / 32 / 42 images, 4 = manuel, 5 = debug ; défaut du jeu = 2, `OptionStatus::initialize` 0x1a344c ; la valeur 1 d'une sauvegarde s'affiche « Moyen »). Manuel : le message attend une touche (Entrée, Espace ou clic : vérifié en combat réel). Rien n'est imposé tant qu'on ne touche pas au menu (`defilement_force`). Clé `defilement_combat` remplace `defilement_auto` / `defilement_vitesse` (migration). **Supposé** : passage direct de 2 à 4 en combat (non rejoué depuis la valeur par défaut).
- **Commandes > Vitesses** : vitesse de marche, de caméra et de transition en **choix x1, x2, x3, x4** (plus de curseurs ; migration : valeur ancienne 0,5 à 2 → cran le plus proche, plancher x1) ; le multiplicateur de l'accélérateur garde son curseur (1 à 2, défaut 1,5 ; les combats ont depuis leur propre vitesse, voir #43). Défauts : marche x1, caméra x1, **transition x2** (l'ancien défaut ; à ramener à x1 par `DEFAUT['vitesse_fondu']` si besoin). Mesuré (horloge réelle, rendu léger) : x2 ≈ x1,7, x3 ≈ x2,9, x4 ≈ x3,8 ; avec l'accélérateur ×2 jusqu'à ≈ x7. Plafond du code : `_facteur_vitesse` ≤ 8 ; **budget de 30 ms par image pour les pas rapides** (`BUDGET_PAS_RAPIDES`, `DQ_BUDGET_PAS`) : si le PC ne suit pas, le jeu ralentit au lieu de geler l'affichage. **Non vérifié** : performance sous Windows à x4 / x8, taux de rencontres sur une longue marche à x3 / x4 (compté par pas moteur donc par distance : raisonné), fondus x3 / x4 sur une vraie transition.
- **Plus d'encadré jaune** sur les boutons, lignes et curseurs de la Pause (et des écrans d'avant-partie : Sauvegardes, nom, licence) : la souris assombrit la plaque (motif « enfoncé », ou couleur à 75 % pour un bouton-icône) et la rallume quand le pointeur sort (`on_mouse_leave` → `pause.sortie()`) ; le clavier garde le curseur doré. **Conservés** : remplissage jaune des jauges, rectangle jaune de sélection d'un élément dans l'éditeur. Test statique : plus de `JAUNE if sel` dans `pause.py`. Test : `outils/test_pause_pages.py`.

### Éditeur d'interface
- **Étiquette « Masquée / Masqué »** pour tout élément masqué individuellement (croix : option « Afficher la croix » ; fenêtres du jeu) ou en bloc (« Afficher cette interface » des boutons : « Masqué » pour Carte / Commandes / Discussion) : voile + étiquette, cadre jaune de sélection redessiné par-dessus, l'élément reste attrapable. `Pause._elements_apercu()` donne rectangle, état et genre (`MOTS_MASQUE`). La croix n'est plus pâlie en plus du voile. Les trois boutons partagent le réglage global `boutons` (pas de visibilité bouton par bouton, décision de #37).
- **Rétablir** : « Rétablir cette interface » remet tout l'état par défaut de l'interface choisie (`Reglages.remettre_interface`) : pour « Boutons et croix de l'écran » `CLES_ECRAN` (affichage, tailles, positions, croix affichée) ; pour une fenêtre ou `msg` son entrée dans `interface_fenetres` et `interface_masquees` (taille, position, affichage). « Rétablir toutes les interfaces » (`remettre_interfaces`) remet aussi la grille, l'aimantation et la place du panneau. Tout vient de `DEFAUT`. Une nouvelle clé de réglage doit être classée dans `CLES_*` ou dans `HORS_INTERFACE` de `outils/test_reglages_interface.py`.
- **Fenêtre « Interface » déplaçable (correction)** : l'ancien code annulait le geste si on bougeait avant 0,35 s : impossible à glisser pour qui n'attendait pas. Maintenant le panneau suit le pointeur dès qu'il s'éloigne de 8 px (`TOLERANCE_APPUI`) de l'appui sur la barre de titre (soulèvement immédiat) ; appui maintenu 0,35 s sans bouger = soulèvement aussi ; appui court = replier / déplier ; double clic = position d'origine **au relâchement** du 2e clic. Test : `outils/test_panneau_interface.py`. **Supposé** : une vraie souris Windows envoie la même suite d'événements que la simulation.

### Écran titre : crédits centrés et dragon
- **Crédits centrés** : les pages de crédits (modèle de maillage 8905, dessiné par les paquets 21 / 22 comme le logo) suivaient le relèvement `TITRE_HAUT` de la scène ; le centre de l'**encre** de chaque page est ramené au milieu de la zone de dessin (`_decalage_credits`, déplacement le long du haut de la caméra, profondeur inchangée : exact à tout format ; cache par page). Mesuré : centre du bloc à 0,500 de la hauteur sur 1280 x 720, 1920 x 1080, 2560 x 1080 et 1024 x 768. « Touchez l'écran », copyright, ciel, logo, île : inchangés. Conséquence : le nom monte de 4 à 18 px selon la page à 720p. `DQ_SANS_CREDITS`, `DQ_CREDITS_ORIGINE=1` pour comparer.
- **Dragon de l'écran d'accueil** : `fbx.py` (nouveau). Le moteur envoie le paquet 31 (`cmd_fbx_load` : emplacement 0, modèle 1018 = `Resources/fbx/c1018`, FbxObject) puis des paquets 32 (`cmd_fbx` : bits 8-9 visibilité, 0x400 forcer l'animation, 0x800 échelle x3, 0x1000 couleur x4, 0x2000 position x3, 0x4000 rotation x3 en degrés, 0x8000 numéro de séquence). Modèle : 566 sommets, 692 triangles, 31 os (un os par sommet), texture 256 x 256, clips « Take 001 » (21,98 s, Once = les 659 images que le moteur attend), « Take 002 » (2,18 s, boucle : vol stationnaire), « Take 003 ». Animation comme Unity `Animation` (Play / PlayQueued / CrossFade 0,3 s si la boucle précédente, Hermite), temps en images moteur à 30 Hz, skinnage numpy ≈ 2 ms par image. Shader `Custom/ImdChara` : sans lumière, couleur sommet x `_Color` x texture, fusion alpha, ZWrite, ZTest LEqual, Cull Back : le dragon passe **derrière** le logo et les crédits (file 3850, ZTest Always). Phases : apparition en haut vers l'image 510, plongée à gauche ~600, vol stationnaire au-dessus du logo ~660, boucle d'ailes jusqu'à l'appui sur « Touchez l'écran », disparition au menu. Cache `fbx1_c1018.pkl` (préparation de fond, ≈ 5 s une fois). **Supposé / à valider** : placement vertical `TITRE_DRAGON_HAUT = 0,0` (cadrage d'origine, non relevé avec le logo ; relevé de 0,3 il sortirait de l'écran) : le haut du dragon est coupé par le bord haut de l'image (même champ vertical que le mobile ; aucune capture du téléphone pour comparer) ; `DQ_FBX_DY` pour essayer, `DQ_FBX_CULL=0` pour couper le culling. **Non vérifié** : les autres modèles fbx du jeu (un seul maillage skinné, shader ImdChara supposés), retour moteur de fin d'animation non implémenté, fbx dessinés seulement dans les scènes de ville.

### Caméra (grenouille du prologue, angle, père)
- **Grenouille du prologue (mlout1)** : la visionneuse bornait la caméra en x (`bornes_x`, cadrage 16/9) dès que le verrou `TownCamera` était levé, alors que le moteur allait jusqu'à x = 6,07 : le rendu restait collé à x = 1,978 (écart max 4,09 u) d'où « droite puis bas » et l'arrêt du suivi. **Unity ne borne rien** (`SceneCamera.Update` D16180 sans Clamp ; `TownCamera::execute` sans clamp en mode libre ; `GetEventLimitedPos` CD4EE4 ne sert qu'au décor `map/ev/ev02/out/ev02`, z ≥ -19,5, quand `UIFix.IsLargeAspectRatio()`). Correctif : `Jeu._camera_menee(mo)` : `cam_jeu` = verrou ET caméra menée ailleurs que sur le joueur (mode de cible 1 à 5, déplacement en cours, cible à plus de `CAM_MENE_DIST` = 1,0 u du héros, ou héros hors champ) ; aucune borne 16/9 en caméra menée, avec ou sans l'option « Centrer la caméra sur le joueur » ; les bornes reviennent progressivement (exp(-14 t), temps réel). Mesuré : écart rendu / moteur 0,000 sur 1470 images.
- **Caméra qui « continue son chemin » en courant (père, `mlb1a`)** : le centrage était lissé en bloc par exp(-14 t) ; quand le jeu borne sa cible, la caméra traînait derrière le héros (jusqu'à 0,03 NDC à x1, 0,10 à x4) puis rattrapait à l'arrêt. Maintenant la correction suit la cible à l'image près (caméra rigide) + un reste qui ne naît que d'un changement de régime (scène ↔ main du joueur) ou d'une coupure, estompé en temps réel : écart 0,0000 indépendant des pas moteur par image et de la cadence ; un verrou qui garde le héros au centre (mode 6) ne change plus de régime. Test : `outils/test_camera_ville.py`. **Non vérifié** : le symptôme n'a pas été reproduit dans la maison du père (caméra moteur = héros, sans verrou pendant la 1re conversation) ; scène exacte à confirmer chez Sylfried. Piste non corrigée : sous verrou (`cam_bloquee`) la rotation / l'inclinaison choisies par l'utilisateur sont coupées d'un coup.
- **L'angle est-il bon ?** Oui pour le mode jeu (**Établi** par désassemblage, aucune capture du téléphone) : `SceneCamera.Update` : LookAt, tangage - `s_lookDownAdjust` 0,2°, avance `s_distanceAdjust` 4,0, `Perspective(fov x 4/3, 1/aspect)` avec [0] et [5] échangés (champ horizontal fixe 12,67° pour un fov nominal de 9,5), `s_yOffset` ; `SetViewAndCenterY` D1F5D0 garde une vue 3D toujours 9:16 (champ vertical 22,3°) sur tout téléphone. Pipeline Unity ré-écrit à part comparé à `_camera_ville` : écart max 4e-15 NDC sur 200 poses x 18 points. 514 des 518 cartes ont distance 39,55 et tangage 47,03° ; exceptions : `dpout` (28,04°, far 150), `sjout` et `tdout` (near 1,0) ; titre `ev01` (distance 44, tangage 39°, fov 10) déjà géré. Monde (orthographique) et combat non revérifiés. **Piste** : `angle_camera` (flèches haut / bas) est **sauvegardé** : un appui accidentel décale le tangage en permanence (la ligne F1 affiche l'angle ; l'option se remet à 0 dans Commandes).

### Sprites : bulle « ! » et bords aplatis
- **Sprites penchés / aplatis près des bords** : le panneau d'un personnage de ville a ses sommets reculés vers la caméra de 0,185 (bas) et 0,65 (haut) le long de l'axe de la caméra (`Chara.s_vtxDepthD / U`) ; le haut, plus proche, s'écarte du centre de l'image proportionnellement à l'écart : penché vers l'extérieur (jusqu'à -13° à 100 % de distance, -20° à 200 %, ±20° aux bords), invisible au portrait étroit du mobile, visible en 16/9 et 21/9 ; indépendant de la résolution et du FOV. Correctif `Jeu._panneau_ville` : panneau reconstruit à l'écran (mêmes position, hauteur et profondeurs : taille, recouvrements et z-buffer inchangés), bords verticaux, largeur = 0,74 x hauteur (proportion du panneau au centre). Mesuré : inclinaison 0,0° et largeur / hauteur 0,73 à 0,74 partout (avant : 0,65 à 0,91) ; au centre, aucun changement ; titre, monde, combat : 0 pixel de différence. **Réglage `correction_bords`** (défaut vrai ; 0 = comme avant ; entre 0 et 1 = partielle ; ligne « Correction des bords des sprites » de l'Affichage ; `--correction-bords 0-100`, `DQ_CORRECTION_BORDS`). Un décalage le long du rayon de vue donnait aussi 0,75 mais changeait la hauteur des PNJ de ±10 à 20 % : écarté.
- **Bulle « ! »** : pas de régression de rendu entre #39 et #41 (0 pixel de différence, code inchangé depuis d6d9b20, aucun bisect possible). Défauts réels corrigés : la bulle était avancée de 0,48 le long de l'axe de la caméra **du jeu** et posée à 1,294 au-dessus des pieds en coordonnées du monde : dès que le joueur incline ou tourne la caméra (flèches), sa hauteur sur la tête dépendait de l'inclinaison (de -0,10 à -1,09 de la hauteur du panneau). Maintenant avance le long du rayon de vue de la visionneuse (`_decaler_profondeur`) et ancrage au personnage surmonté (`_ancrer_icone` : écart gardé tel que la caméra du jeu le voit, rapporté à la caméra de la visionneuse) : écart -0,37 à -0,40 à tous les angles. **Non vérifié** : le cas exact de la capture de Sylfried (tonneaux) : pour un tonneau sans personnage dessous la position du moteur est gardée telle quelle (1,294 au-dessus des pieds, comme l'original) ; si elle paraît trop haute caméra par défaut, c'est la position du moteur.
- Outils : `DQ_PROJ=n` (pixels des 4 coins des panneaux et des bulles), `DQ_CAMV_SPR=1`.

## Retours de 02 h 12 : titre (dragon, château, fond), coffres, souris, plein écran, vitesse des combats, historique (02/11/2026, #43)
Retours de Sylfried (lundi 02 h 12 à 02 h 38, 5 captures) traités par neuf enquêtes en parallèle puis fusionnés ; la reprise d'une première série d'agents interrompue est incluse. **Établi** = lu dans le code ou mesuré sous xvfb (Mesa) ; **Supposé** = déduit ; **Non vérifié** = à essayer sur son PC Windows. Les décisions de Sylfried sont reprises dans le registre de l'audit (`decisions.md`).

### Écran titre
- **Dragon « à deux orientations »** : cause = le **culling** (**Établi**). `Cull Back` d'Unity écarte les faces vues dans le sens horaire à l'écran, GL attend l'anti-horaire : les faces intérieures lointaines passaient à travers les faces proches supprimées, on voyait un « visage » alors que le corps était de dos. Corrigé : `glFrontFace(GL_CW)` dans `_tracer_fbx` (`DQ_FBX_CULL` 0 / 1 / 2 pour comparer). Le dragon est posé **une seule fois** par le moteur (image 2 : position (-2,16 ; 7,0 ; 0,55), lacet 349,45°, de dos, regarde +z) ; sa trajectoire vient des clips : « Take 001 » (21,98 s) puis « Take 002 » en boucle à l'image 662 (entre par le haut vers 420-480, pique vers 540-620, se pose au-dessus du logo vers 660-800). Rotation par défaut du paquet 31 = (0, 0, 0) (`FbxObject` ne la pose pas). `DQ_FBXLOG=1` trace les paquets 31 / 32. **Supposé** : le sens du cap (aucune capture du téléphone).
- **Île du château** : la correction de `euler_mat` (voir Coffres) redresse l'île (`tenkuzyo2e`, rot (-43, 39, -18)) : château presque vertical au lieu d'être penché à gauche.
- **1:1 avec le mobile** : la zone 9:16 centrale de la fenêtre est le rendu du téléphone (**Établi** par mesure : fenêtre 1281 x 720 colonnes 438..842 contre fenêtre 405 x 720, vignette à 0 : moyenne 0,0004, au plus 107 pixels sur 291 600 diffèrent, bords de texte). Écarts supprimés : (1) **bug de zoom du héros sur `ev01`** (le sprite 0, caché, déclenchait la formule de zoom commun : scène agrandie x1,185, logo plus large que la zone) : exclu pour `ev01` ; (2) hacks `TITRE_HAUT`, `TITRE_DRAGON_HAUT`, `_decalage_credits` (+ cache, `DQ_CREDITS_ORIGINE`) **retirés** : logo et crédits sont placés par le moteur (logo centré, crédits à ±1,5 px). `DQ_SANS_CREDITS` conservé. **Piège** : avec la vignette par défaut (0,3) les bords de la zone sont plus sombres d'environ 20 % en fenêtre étroite qu'en 16/9 ; couper la vignette pour comparer. **Non touché** : « Touchez l'écran » (couche UI, échelle `ui_k` 0,89 en portrait contre 1,0 en 16/9).
- **Fond non répétitif** (`ciel_titre.py`, fonction pure + tests) : hors de la zone portrait, des bandes de même géométrie que les rangées du ciel reprennent la texture avec une étirure horizontale variable (0,52 à 1,48) et un glissement vertical de 3 % nul aux coutures ; raccord continu au bord. La zone portrait reste le ciel d'origine (identique au pixel). Repli sur le ciel d'origine à toute erreur ; `DQ_CIEL_COPIES=1` = ancien tapis de copies, `DQ_CIEL_PARAMS=a1,a2,glisse,longueur` pour essayer. **Limite honnête** : les mêmes formes de nuages restent reconnaissables (une seule texture).
- **Menu de départ : plaque « Sauvegarde automatique »** (case 4, `data5`) : **toujours visible** avec son libellé ; sans `data5` elle est **grisée** (état de bouton 3, texte gris, aucune zone tactile : ni clic, ni survol, ni validation au clavier). **L'original la cache** (code 0 = disponibilité de `data5`, libellé `(4, 1)` envoyé seulement si valide) : le choix « grisée » est celui de Sylfried (« je te laisse choisir ») ; `DQ_AUTO_CACHEE=1` rétablit l'original. États de bouton : 0 normal, 1 enfoncé, 2 invisible, 3 gris, 4 inversé ; **Unity coupe le test de contact pour 2 / 3 / 4** (le moteur ne bloque pas la validation d'une cellule grisée) : la visionneuse fait de même, donc Continuer / Reprendre / Supprimer grisés ne sont plus cliquables. Le moteur grise lui-même les cellules 0 / 1 / 3 du type 53 quand elles sont indisponibles ; les listes type 54 n'ont pas d'états. **Non vérifié** : le gris exact du shader d'origine et du texte (choix de la visionneuse).

### Coffres et objets de carte (cause racine : ordre des rotations)
- **Cause** (**Établi**, désassemblage de `FldObject.rotateXZY` 0xCD47F0) : la matrice est **Ry · Rz · Rx** (X d'abord dans le repère de l'objet, puis Z, puis le cap Y en dernier) ; `donnees.euler_mat` faisait Rx · Ry · Rz (l'ordre « X, Y, Z » noté en #21 était une erreur de lecture). Le couvercle (clé FPMV rx = -60) basculait donc autour de l'axe X du **monde** : seul un coffre de cap 0 s'ouvrait bien (cap ±90 : de côté ; 180 : vers l'avant, dans le coffre ; -27 : de travers). Corrigé ; cache des cartes renommé `carte9_` (les sommets des objets inclinés sont cuits avec `euler_mat` ; les anciens caches sont purgés, les cartes se préparent de nouveau au premier lancement).
- **Deuxième défaut de la même famille** : les mouvements communs (FPMV, `flag & 4`) lisent leur déplacement dans le **repère de l'objet** (`c_pmv_func` 0xCD96D8 ; `update_pmv_one` 0xCD6824 choisit CPMV quand `flag & 4`) ; la visionneuse l'ajoutait dans le repère du monde : les tiroirs de cap ≠ 0 sortaient de côté (≈ 9 tiroirs : `chf2`, `dpb4b` / `5b`, `mkm1f1`, `mmout`, `sey1f1`, `shb1`, `za2f8`, `za3f2`). `objets_carte.py` `_poser`.
- **Un coffre** = deux objets de carte : `tbox01` (corps) et `tbox02` (couvercle, origine = charnière arrière haute, animations FCAN : 1 fermé, 2 ouverture rx 0 → -60, 3 tenu ouvert, 4 fermeture). **Le coffre ne se tourne jamais vers le joueur ni la caméra** (billboard 0 ; seuls les jarres et tonneaux sont des billboards) ; le moteur n'envoie que `SetCommonAnimation` 2 ou 4 (`TownFurnitureObject::openObject` / `closeObject`). 184 coffres sur 194 ont le cap 0 ; les autres : `ham1f1`, `hcy1b1` (x3), `mdi1f1` (-27), `sjout`, `ss5b1b` (x2), `tcf1`, `tcf3`. **Supposé** : la capture de Sylfried vient de `mdi1f1` ; « orientés vers le joueur » = coffres de cap ≠ 0.
- **Effet de bord voulu** : environ 280 objets inclinés (71 types : falaises `dlkm1a`, touffes `kb0x`, `tenkuzyo2e`…) changent d'orientation. Indice que le nouvel ordre est celui des concepteurs : les paires `dlkm1a` (40, 6, 0) / (-40, 186, 0) penchent maintenant dans la même direction du monde. Test : `outils/test_objets_carte.py` (15 tests, vrais objets via `DQ_CACHE_CARTES`).

### Entrées : clic molette, souris après clavier, F1
- **Clic molette** (`entrees.py` : `GesteMolette`, `pivoter`) : maintenu + déplacement = la caméra tourne (horizontal = lacet, vertical = inclinaison ; mêmes variables, bornes et sens que les flèches ; `CAM_SOURIS_LACET` 180° et `CAM_SOURIS_ANGLE` 120° par hauteur de fenêtre, seuil `SEUIL_GLISSE` 4 px) ; **clic simple** = direction remise (même animation que « Touche spéciale + touche caméra », `recentrer_camera`) ; **Ctrl + clic** (modificateur Ctrl ou « Touche spéciale ») = zoom à 100 %, sans toucher à la direction. N'agit que là où les flèches agissent (le zoom aussi sur la carte du monde). Le bouton du milieu ne déclenche plus aucun clic gauche simulé (avant, `Pause.clic` le traitait comme un clic gauche). Changement : la molette ne zoome plus sur le titre, la licence, les Sauvegardes, la saisie du nom ni la carte ouverte. Harnais : `%x%y` (appui), `&x&y` (glisser), `*x*y` (relâchement), `+LCTRL`. **Non vérifié** : la sensation sur une vraie souris Windows (sensibilité, sens).
- **Souris inutilisable ~1 s après le clavier** : **aucune minuterie** n'existe dans le code ; c'étaient des seuils de mouvement : `Pause.survol` comparait chaque événement au précédent (< 3 px) donc une souris lente (1-2 px par événement) ne reprenait jamais la main, et `souris_gel` (6 px, après le menu Échap) gelait le survol. Remplacés par `entrees.GardeSouris` : la position du pointeur est figée à chaque touche, le survol reprend dès **4 px cumulés** (`TOLERANCE_SOURIS`), un clic agit toujours et immédiatement. Garde-fou conservé : une souris au repos sous un menu qui s'ouvre ne vole pas la sélection au clavier (cas connu : Échap sélectionnait « Sauvegarde rapide »). Test : `outils/test_entrees.py` (37). **Supposé** : la cause décrite (reproduite par test, jamais observée sur son PC).
- **F1** = bloc d'infos à l'écran (lieu, fenêtre, réglages, son, performances), **pas** l'éditeur « Interface » : il passe **en haut à droite** (à gauche seulement si la colonne d'interface est à droite, `--ui-pos droite`). Aucune position enregistrée ni réglage ajouté.
- **Suivi de la caméra sur le joueur** (« Centrer la caméra sur le joueur » ; **option supprimée en #47** : la caméra est toujours centrée, voir Avance #47) : activé par défaut (c'était déjà la valeur du code ; le `reglages.json` de Sylfried contenait `false`). Une clé de version (`suivi_camera_v`) remet la valeur à `true` **une seule fois** pour les fichiers qui n'ont pas cette clé ; un choix ultérieur est conservé.

### Fenêtre et affichage
- **Plein écran exclusif supprimé** (décision de Sylfried) : `mode_fenetre` ∈ {0 fenêtré, 1 plein écran sans bordure}. Migration : 2 → 1, booléen d'avant #42 → 0 / 1 ; clés obsolètes (`plein_ecran`, `mode_fenetre_retour`, `correction_bords`, `lissage`) ignorées puis effacées (`reglages.CLES_OBSOLETES`). `--plein-ecran 0|1|2` : 2 vaut 1. **Page Affichage** : la première ligne redevient l'interrupteur **« Plein écran »** (Oui / Non, comme avant #42) ; « Résolution » grisée en plein écran. **F11** et **Alt + Entrée** basculent depuis n'importe quel écran (Entrée avalée : ni validation ni discussion de groupe ; gestionnaire `WM_SYSCHAR` sous Windows contre la tonalité d'erreur).
- **Scintillement** : causes plausibles, relues dans pyglet 2.1.19 Win32 (**non exécutées sous Windows**) : (1) l'exclusif faisait 2 changements de mode du moniteur par aller-retour ; (2) `set_fullscreen` cache la fenêtre, change le style et la taille puis la **montre** avant toute image (tampon indéfini jusqu'à la trame suivante) et, au retour en fenêtré, `set_location` arrive après l'affichage (la fenêtre apparaît en (0, 0) puis saute) ; (3) `post.cle = None` forcé reconstruisait les tampons du rendu hors écran fenêtre visible. Correctif `Jeu._poser_plein_ecran` (une seule étape) : fenêtre cachée, un `set_fullscreen`, une image dessinée et affichée à la taille définitive, fenêtre montrée, même image redessinée ; plus de `post.cle = None` forcé ; tout échec → retour à l'état de départ. Mesuré (xvfb) : « fenêtre visible sans image » 250-276 ms (aller) et 67 ms (retour) → 0 ; changements de mode du moniteur 2 par aller-retour → 0. `DQ_BASCULE_SIMPLE=1` = ancien comportement ; `DQ_SIM_ECHEC=1|0` simule un refus ; `outils/mesure_bascule.py`. **Non vérifié** : que le scintillement disparaisse sur son PC (Windows peut faire un éclair noir à lui seul en plein écran sans bordure « indépendant flip »), Alt Gr AZERTY, multi-moniteurs, DPI.
- **Correction des bords des sprites** et **Lissage des textures** : options **supprimées**, toujours actives (décision de Sylfried : « c'est exactement la correction que j'attendais » ; « mets oui par défaut et supprime l'option »). Captures identiques au pixel à #42 avec l'option sur « oui ». Interrupteurs de **débogage** seulement : `--correction-bords 0-100` / `DQ_CORRECTION_BORDS`, `DQ_SANS_LISSAGE=1`.
- **Page Affichage, ordre actuel** : Plein écran, Résolution, Netteté, Shader, Effet de vignetage, Anticrénelage, Suréchantillonnage, Luminosité, Distance caméra, Centrer la caméra sur le joueur (supprimé en #47), Interface.

### Le jeu prime sur les réglages du joueur (`priorite_jeu.py`)
Principe (décision de Sylfried) : un réglage du joueur est une **valeur par défaut** ; dès qu'un script du jeu fixe le paramètre, la valeur du jeu s'applique. Inventaire complet par réglage dans le rapport de l'agent ; en résumé :
- **Vitesse du texte** : DQ4 n'a aucune commande de script ni écriture du mot de vitesse (`MSG_VITESSE` 0x2523b0) hors `ui_MsgSetup` (table par type de fenêtre) ; le crochet ne remplace que la vitesse standard : déjà correct, passé par la fonction pure `lettres_par_image`. **Non vérifié** : DQ5 / Nimzo (pas de moteur DQ5).
- **Marche x1-x4 + accélérateur** : corrigé. `_facteur_vitesse` accélérait l'horloge dès qu'une direction était tenue, même pendant une scène sans message ; maintenant facteur 1 si `Global.Flag & (1 | 4)` (fondu / verrou du joueur ; exploration libre = 0x38 en ville, 0x28 sur la carte du monde, scène = 0x3c).
- **Fondus de script** : `fade_in` / `fade_out` du script (`__cmd_fade_*::initialize` 0x21b3c0 / 0x21b43c) comptent leurs images eux-mêmes : les raccourcir ne faisait que prolonger l'écran noir. Le paquet 9 reçoit la marque bit 16 (`PJ.MARQUE_FONDU_SCRIPT`) quand `UnitySetFade` (0x17e120) est appelé depuis ces deux fonctions ; `Etat._fondu` ne les raccourcit plus. Les fondus du moteur (changements de carte) restent raccourcis par « Vitesse de transition » ; les fondus en couleur jamais. Mesuré à x4 : script 30 → 30 et 60 → 60 images ; moteur 30 → 8, 45 → 11, 60 → 15. **Non traité** : le fondu du titre de chapitre (`Global::fadeInBlack(60)`) reste raccourci.
- **Zoom** (molette) : neutre quand la scène fixe une caméra libre (`cam_libre`) ; pendant un travelling (`cam_jeu`) le zoom est gardé (**Supposé**). Caméra manuelle, vitesse de caméra, caméra centrée : déjà soumises à `cam_bloquee` / `cam_jeu` / `cam_libre`.
- Piège Unicorn : un crochet ajouté après qu'un bloc est traduit ne se déclenche pas ; installer dans `Moteur.__init__` avant les pas (`_crochets_texte`, `_crochets_fondu`). Tests : `outils/test_priorite_jeu.py` (12).

### Vitesse des combats (`vitesse_combat.py`) — réglage unifié en #44 (4 vitesses, voir « Avance #44 »)
- **« Multiplicateur de l'accélérateur »** remplace « Vitesse de l'accélérateur » (clé `vitesse_accel` inchangée). Nouvelle ligne **« Vitesse des combats »** dans Commandes > Vitesses, juste sous les lignes de l'accélérateur : **Normal / Rapide / Très rapide** (x1 / x2 / x3, `vitesse_combat`), plus une touche réglable (**V** par défaut, action `vit_combat`) et un **bouton à l'écran** en combat (éditeur d'interface : déplaçable / masquable, « Rétablir » le remet ; position par défaut colonne 0,4 / ligne 8).
- **Effet** : en combat le moteur fait 1, 2 ou 3 fois plus de pas de 1/30 s par seconde réelle (`VC.avancer`, boucle extraite de `Jeu._boucle` ; budget de calcul 30 ms par image : le jeu ralentit au lieu de geler). Accélérés : animations, effets, nombres de dégâts, fondus, **messages automatiques** (Rapide / Moyen / Lent). **Non accélérés** (précision de Sylfried) : **musique et bruitages** (durée, hauteur, tempo inchangés ; seule la date de déclenchement d'un bruitage suit le moteur, `VC.sons_a_jouer` empêche d'empiler le même bruitage dans la même image) ; attentes du joueur (menus, choix de cible, Oui / Non, message « Manuel »). « En combat » = partie 0xd du moteur + effet d'écran de début + écran noir d'attente de la scène.
- **L'accélérateur ne joue pas en combat** (« ne doit pas pouvoir être accéléré via l'accélérateur ») : interprétation retenue = l'accélérateur multiplie marche et caméra hors combat uniquement. À corriger si Sylfried l'entendait autrement.
- **Déterminisme** (**Établi**) : le même combat rejoué à x1, x2 et x3 donne paquets, messages, états et dégâts identiques pas à pas (3000 pas, dégâts 11, 11, 8, 8) ; journaux `DQ_PKTALL` identiques sur 8405 lignes en fenêtre réelle. Durées du même combat sous harnais : 36,7 s / 19,6 s / 14,0 s. **Supposé** : à x3 alternance 1 / 2 pas par image à 60 Hz (légère irrégularité possible) ; la durée de la fanfare de victoire reste réelle alors que le moteur enchaîne plus vite (à x3 la musique suivante peut la couper : à vérifier à l'oreille). Tests : `outils/test_vitesse_combat.py` (39 ; rejeu moteur : `DQ_APK=… DQ_SAVES=… python3 outils/test_vitesse_combat.py RejeuMoteur`).

### Historique des messages (`historique.py`, `ui_historique.py`) — remplacé en #44
- La première version (messages avec « qui / où », fichier par partie, `libelles.py`) a été **abandonnée en #44** : voir la section « Avance #44 », sous-section « Historique ». Restent valables : le crochet `TextBuffer::cat` (lib + 0x157874), l'heure de jeu `status::g_Game + 4`, le tri des pages d'un message (page k + 1 notée après la lecture de la page k) et le point suivant.
- **À signaler au projet de traduction** (fichier du patch FR, non modifié) : le texte « Ragnar obtient l'herbe ;médicinale. » contient un « ; » présent dans le tampon du moteur lui-même. **Précisé par l'avance #148** : c'est une marque de coupure des noms d'objets du patch, retirée de l'historique.

### Nom de Ragnar « trop bas » (captures s4 / s5) — repris et corrigé en #45 (voir « Avance #45 », alignement des textes)
Impression fondée mais faible, **rien changé**. Mesure à 1280 x 720 : intérieur du bandeau y 30 à 48 (centre 39), majuscules y 35 à 46 (centre 40,5) : **1,5 px sous le centre** (≈ 2,3 px à 1080p), la queue du g touche le séparateur. Le nom (type 29) est un TextMesh d'ancre 1 (UpperCenter, z 385,5) ; PV / PM / Nv. sont ancrés en haut aussi (z 359) et s'alignent bien sur leurs jauges. Un recentrage global remontait le nom de 2 px mais faisait **descendre PV / PM / Nv. de ~1,5 px** (chiffres sur les jauges) : régression, annulé. **Supposé** : l'écart vient des données de l'interface d'origine (l'original aurait le nom aussi bas). Si Sylfried le veut quand même : décalage ciblé de ≈ 1,5 px des textes de la plaque type 29 (choix arbitraire, sans référence mobile). Comparaisons : `/tmp/c_opt_cmp_plaque.png` (non conservées dans le dépôt).

### Audit (première partie, lecture seule)
Quatre rapports ont été produits (issues et décisions : 128 décisions, 21 contradictions, 161 lacunes ; couverture des fonctionnalités : 529 cartes balayées, 528 sans plantage) ; ils alimentent le rapport « ce qu'il reste à faire », livré à part. Constats les plus graves pour la jouabilité : poker du casino invisible (partie 0xf inconnue de la visionneuse, garde `e.partie == PARTIE_VILLE` à `fenetre.py`), machine à sous injouable au clavier (`_saisie_menu` n'expose que les boutons 0x10), bestiaire (partie 0x10) sans monstre dessiné, paquets 1 / 6 / 16-18 / 27 / 30 / 33 ignorés (le 33 = `map_color_rate`, émis sur 171 cartes), boutiques / banque / église / auberge / arène / bateau / ballon / générique jamais ouverts dans un test.

### Outils et variables ajoutés (#43)
`DQ_FBXLOG`, `DQ_FBX_CULL`, `DQ_CIEL_COPIES`, `DQ_CIEL_PARAMS`, `DQ_CIEL_BANDES`, `DQ_CIEL_ZOOM`, `DQ_AUTO_CACHEE`, `DQ_SANS_CREDITS`, `DQ_SANS_LISSAGE`, `DQ_CORRECTION_BORDS`, `DQ_BASCULE_SIMPLE`, `DQ_SIM_ECHEC`, `DQ_CACHE_CARTES`, `DQ_CARTE_SANS_SPR`, `--historique`, `--correction-bords`, harnais `%x%y` / `&x&y` / `*x*y` / `+LCTRL`. Tests : `test_entrees` (37), `test_objets_carte` (15), `test_titre_ciel` (22), `test_plaque_depart` (12), `test_camera_titre` (3), `test_priorite_jeu` (12), `test_vitesse_combat` (39), `test_historique_messages` (61), `test_libelles` (13), `test_mode_fenetre` (28), `test_reglages_interface` (15), `test_pause_pages` (16), `mesure_bascule.py`.

### Non vérifié (honnêtement)
Tout ce qui dépend de Windows et d'un vrai GPU : disparition du scintillement, F11 / Alt + Entrée sur clavier réel, sensation du glisser molette, fanfare de victoire à x3, perf à x3 sur un PC lent. Aucune capture du téléphone : cap du dragon, gris d'une plaque, position du nom de Ragnar. Messages de jarre, de combat au-delà du premier, de la carte du monde dans l'historique. DQ5 / Nimzo.

## Avance #44 : historique refait, vitesse de combat, ↺, niveau supérieur, nuit, cartes et PNJ (02/11/2026)

### Historique (`historique.py`, `historique_combat.py`, `ui_historique.py`)
- **Refonte demandée par Sylfried** : plus de « qui l'a dit » ni de lieu (`libelles.py`, `generer_libelles.py` et leurs tests supprimés). Trois onglets : **Dialogues** (hors combat), **Combats**, **Favoris**.
- **Dialogues** : même fenêtre que le jeu (cadre noir translucide, police d'origine). Le **nom du locuteur** est dans un cartouche **seulement si le jeu l'affichait quand le dialogue a été dit** (2e argument de `TextBuffer::cat` = le « @a<nom>@b » du patch) ; sinon le texte seul, avec son « *: » du début quand le patch FR en met un. Les messages de combat n'y entrent jamais. Les pages d'un message ne sont notées qu'une fois lues (inchangé).
- **Combats** (complétés par l'Avance #152) : par combat, l'issue (Victoire / Fuite / Défaite), les ennemis (« Gluant ×3 » si tous vaincus, « Golem ×2 : 1 vaincu, 1 resté » sinon), l'or, l'expérience et les objets d'une victoire. Capture en **lecture seule** par `CapteurCombat` (crochets sur `BattleActorManager2::execMonsterDeath`, `PartyStatus::startBattle`, `Global::endBattle`, `BattleExecDefeatMonster::initialize`, `BattleExecEscape::setup` ; or et expérience = compteurs `g_Party + 0x2f8 / 0x2fc` que le jeu lit pour ses propres messages). Un combat dont on n'a pas vu le début n'est jamais rapporté.
- **Durée de vie** : dialogues (1000 au plus) et combats (200) vivent **en mémoire** et disparaissent à la fermeture de la visionneuse. Une **étoile** (Entrée, Action ou clic) copie l'élément dans `historique_favoris.json` (à côté de la visionneuse, dans `.gitignore`, jamais dans le dossier des sauvegardes), écrit tout de suite ; retirer l'étoile (dans n'importe quel onglet) l'enlève du fichier. Fichier illisible → mis de côté en `.corrompu` ; favori invalide → ignoré sans perdre les autres ; numéros de favori jamais réutilisés.
- **Touche H = comme M** : 1er appui ouvre les messages, 2e les combats, 3e ferme tout (aussi depuis l'entrée « Historique » du menu Pause). Fond de la fenêtre et des éléments à `HM.OPACITE_JEU` (0,68), comme les autres fenêtres.
- **Vérifié** : 58 tests (`outils/test_historique_messages.py`, dont le crochet `TextBuffer::cat` avec un faux émulateur et le cycle H dans le menu Pause) ; 57 tests de la capture des combats sur le vrai moteur (`outils/test_historique_combat.py`). **Non vérifié** : le dessin de la fenêtre sur Windows / vrai GPU ; un combat réel joué jusqu'à l'historique dans la fenêtre.

### Vitesse de combat (un seul réglage)
- « Messages en combat » et « Vitesse des combats » sont **fusionnés** en **« Vitesse de combat »** : **Manuel** (vitesse normale, messages passés à la main), **Normal**, **Rapide** (x2), **Très rapide** (x3). La touche de Commandes (V par défaut) s'appelle « Changer la vitesse en combat » et ne fait plus que passer à la vitesse suivante. Bouton à l'écran : en bas à gauche de la boîte de commandes, à côté de « Fuir », avec des flèches (▶, ▶▶…) à la place du libellé.
- Rapide / Très rapide font faire plus de pas de 1/30 s au moteur par seconde réelle, **animations des ennemis comprises** ; pendant les attentes du joueur le moteur garde l'allure choisie mais seuls les pas à cadence normale lisent les touches (`fenetre.tick(muet=True)` : curseur et répétition inchangés).
- **Non vérifié à l'œil** : l'animation de repos des monstres à x2 / x3 (codé, testé par comptage de pas, jamais regardé en fenêtre).

### Boutons ↺ (valeurs par défaut)
- Chaque ligne à valeurs du menu Pause (`_choix(..., defaut=...)`) a un bouton ↺ qui remet la valeur d'origine (vitesses du texte, de marche, d'accélérateur, de combat, son, affichage, option des PV / PM…). Rien d'autre n'est touché.

### Combats de nuit (cause trouvée)
- Les décors `btl_*_n` sortaient noirs : la visionneuse multipliait par la couleur RGB `_Color` de l'asset. Le moteur d'origine fait `FldObject.save_org_color` (RVA 0xCD811C, fin de `init_fld`) : `_OrgColor` = (1, 1, 1, alpha de `_Color`) et `Material.color` = `_OrgColor` x teinte ; la couleur RGB d'asset n'est **jamais** utilisée en jeu. Le cache des cartes ne garde donc plus que l'alpha (version `carte10_`). **Vérifié** sur une capture de combat de nuit ; **non comparé** à un téléphone (conclusion tirée du désassemblage).

### PV et PM restaurés au niveau supérieur (option, désactivée par défaut)
- Page « Jeu » du menu Pause. `HaveStatus::levelup(bool)` : le booléen vrai remet PV et PM au maximum ; les montées de niveau normales appellent `levelup(false)`. Le crochet (`Moteur._crochets_niveau`, instruction `tbz w20, #0` à `levelup + 0x3f8`) force le bit 0 de x20 quand l'option est active. **Vérifié sur un vrai combat gagné** (`outils/test_niveau_pv.py` : PV 2/39 → 39/39 avec l'option, 2 sans).

### Bruitages de transition (porte, sortie de village)
- Défense ajoutée : un bruitage tout juste lancé n'est pas libéré avant 0,4 s (`SE_GRACE` dans `son.py`), même si les pas suivants d'une image affichée à marche accélérée font passer `Son.tick()` avant le début de la lecture. **Cause trouvée en #47** : voir « Bruitage de transition de carte » dans la section Avance #47 (le moteur ne demandait plus le bruitage 305 quand le fondu raccourci amenait le chargement de la carte avant le décompte de 15 images).

### Cycle jour / nuit et échelle des sprites (agent « paquets »)
- **Paquet 33 (teinte du décor)** : `cmd_map_color_rate` donne r, g, b ; `Material.color` = `_OrgColor` x teinte, **sauf** pour les matériaux dont la texture contient « tz_ » (lampes, bougies, torches, vagues). Carte du monde incluse. `DQ_SANS_TEINTE=1` pour comparer. **Testé avec des valeurs de teinte forcées** (18 tests `outils/test_teinte_carte.py`) ; la teinte réelle d'une journée n'a pas été capturée.
- **Paquet 13, bit 0x800** : `Chara.SetScale` (échelle 1,8 x s du panneau, pas de l'ombre) ; la première valeur de placement est ignorée ; `DQ_SANS_ECHELLE=1` pour comparer. Seules `mlb1a` (0,74) et `ev07` (0,95) diffèrent de 1,0 après placement.

### Cartes, PNJ et états (agent « cartes »)
- **32 cartes sortaient vides** (maillage porté par le GameObject racine, sans enfant `NNN_`) : 18 décors de combat (montagne, marais, désert du monde…) et 14 lieux ; corrigé. Matériaux sans texture : texture blanche 4x4 x couleur de sommet x `_Color` (948 sommets). Caches `carte[0-9]_` anciens purgés.
- **3 PNJ jamais dessinés** (emplacement 8 de `mom2f1`, `mqtf3`, `msm1f1`) : le moteur n'envoie que les positions qui changent et un PNJ posé en (0, 0, 0) n'en reçoit jamais ; un sprite animé sans position au bout de 3 images est placé à l'origine (comportement d'Unity).
- **États enregistrés (.dqs)** : `etats.appliquer` ne rejouait que les vitesses et le bouton Paramètres ; tous les correctifs mémoire sont maintenant rejoués (`Moteur.reappliquer_correctifs`, dont la fenêtre des lieux et `g_isAmazon`).
- **Constats sans changement** (décisions du jeu d'origine) : coffres, jarres et portes ne gardent aucun état (le moteur renvoie « coffre ouvert » à l'entrée, la jarre cassée réapparaît) ; la visionneuse n'écrit **aucune** variable de scénario ; 73 cartes / 499 sprites sans traversée de mur ; `null01.tim` transparent et `kuro01.tim` noir sont voulus par les données.
- **Notes moteur** : enregistrement des PNJ à `LIB+0x26a688`, pas 0x1c0, Fix32 (x, y, -z) en +0 et +0x140 ; caps des feuilles de 4 rangées : 0 = +z, 1 = +x, 2 = -z, 3 = -x (feuilles de 8 rangées : 0 N, 2 E, 4 S, 6 W) ; animations de coffre FCAN : 1 fermé, 2 ouverture (10 images), 3 ouvert, 4 fermeture ; téléportation de test : écrire x, y, -z (x 4096) dans `g_cmnPartyInfo` (LIB+0x269810) puis `startTown(carte)`.
- **Non vérifié** : l'aspect réel en combat des 18 nouveaux décors (4 vus en vue de sol approximative) ; `za3f3` et `ev01` plantent dans `startTown` (pointeur nul dans `FldStage::getCameraLimitL`) : *rectifié le 04/11/2026 (audit, #76)* : `za3f3` est une carte orpheline (`.map` et `.fld` sans `.stg`, jamais démarrée par le jeu), `ev01` ne plante que lancée par `startTown` (le titre la charge par un autre chemin) ; effets réels des paquets 16, 17 et 33 des cartes `ml*` (comptés seulement) ; scénarios (PNJ qui apparaissent / disparaissent) ; 7 planches de contrôle sur 15 jamais regardées une à une.

### Services en ville, église, boutiques, banque, véhicules (agent « services »)
- **Vu dans la fenêtre réelle** (captures GL sous Linux) : église (sauvegarde, résurrection / pénitence), boutiques d'armes, d'armures et d'objets (achat ×3, vente, « Qui va le porter ? », clavier **et** souris), auberge (fondus, Oui / Non, or insuffisant), banque (souris), menu du terrain et Statut, boutique de Torneko, arène (affichage), otage, Nène, bateau, ballon (dessin), chariot. Les véhicules sont **dessinés** (le doc disait « jamais dessinés » : vrai seulement hors scénario).
- **Bug corrigé** : les pages du **Statut** (types 13-17) ne tournaient pas au clavier (Q / D / L / R / PageHaut / PageBas) : `_saisie_menu` envoyait ◀ ▶ à une fenêtre sans grille ni bouton A ; trois lignes dans `fenetre.py` les envoient au port qui porte les flèches de page. Avant / après : « 1/4 » figé, puis 2/4, 3/4, 4/4, 1/4.
- **Banque au clavier : saisie d'un montant impossible avant la fusion** (même cause que la mise du casino : `_saisie_menu` ne retenait que les boutons à pad & 0x10, jamais les ▲ ▼ des colonnes) ; la généralisation ▲ ▼ de l'agent « casino » (section suivante) la couvre : **rejoué sur l'arbre fusionné** (scénario `scen_bank.py`) : Z / D modifient maintenant le chiffre des milliers (0 → 3 pour 3000 G) alors qu'avant la fusion « T64 après clavier » était identique à « T64 » ; le dépôt validé à la souris vide bien les 3000 G. Les pages du Statut tournent au clavier (1/4 → 2/4 → 3/4 → 4/4 → 1/4 → 4/4 → 3/4 → 2/4). **Non vérifié** : la colonne exacte choisie par ◀ ▶ dans la banque (le scénario ne couvre qu'un chiffre).
- **Non vérifié** : auberge jouée par le PNJ réel (condition de parole par-dessus le comptoir), sorts du menu (aucune sauvegarde avec lanceur), arène jusqu'au bout (chapitre 2 requis), générique, radeau, henge, sifflet, Rura, divination / bénédiction / purification, types 59 / 63 / 70. Les chapitres suivants ne sont atteignables que par forçage (toutes les sauvegardes réelles sont au chapitre 1).

### Casino, arène des monstres et bestiaire (agent « casino »)
- **Poker invisible : corrigé.** Le moteur a deux parties de plus que la visionneuse ne connaissait : **0xf casino** (`Global::startCasino`, `setMinigame(0)` = poker, carte `ev04`, type 48 ; sinon machine à sous, carte `ev05`, type 47) et **0x10 bestiaire** (`Global::startBook`, type 28). Constantes `MO.PARTIE_CASINO`, `MO.PARTIE_BESTIAIRE`, `MO.PARTIES_MINIJEU` ; en 0xf / 0x10 les maillages dynamiques (table, cartes) sont dessinés ; le décor du bestiaire n'est plus tracé (la tranche d'église `mak1f1` apparaissait derrière la liste).
- **Menus de saisie numérique jouables au clavier** (machine à sous, poker, jetons type 44, arène 49, mises 47 / 48) : ◀ ▶ choisit la colonne (1 / 10 / 100 / 1000 / 10000 pour le type 44), ▲ ▼ = pads 2 / 1 sur la colonne active, A valide, B retourne (`_saisie_pas`). Vérifié : gain de machine à sous, achat de jetons de bout en bout, mise d'arène, échange de cadeaux. **La banque (types 64 / 65) utilise le même mécanisme : à rejouer au clavier après cette fusion (non revérifié).**
- **Poker** : zones tactiles des cartes et « Donner » absentes (code de fenêtre 2, valeur 63 = masque de bits absente du tableau exporté, `Fenetre._code_masque` dans `ui_menu.py`) : corrigé, main complète jouée au clavier et à la souris.
- **Échap** = bouton retour de la fenêtre ouverte dans le casino et le bestiaire (au lieu de la Pause) ; **pas de marche accélérée** en 0xf / 0x10 ; lieu « Casino » / « Bestiaire » lisible dans les états instantanés (chargement d'un état en plein poker vérifié).
- **Bestiaire** : fiche et liste au clavier (◀ ▶ de la fiche, L / R de la liste, touche Action pad 0x800), monstre dessiné. **Route d'accès réelle introuvable** (aucun bouton « bestiaire » dans Objets / Magie / Carac. / Divers d'une sauvegarde du chapitre 1 ; `TownMenuItemSelectCommand::menuUpdate` l'appelle) : vérifié par appel direct de `startBook` seulement.
- **Arène des monstres (combat réel, carte `btlcc2`)** : (a) le message « X a remporté la victoire ! » ne tournait jamais au clavier (la fenêtre « Quitter », type 71, un seul bouton pad 0x400, avalait A) ; (b) la touche V (vitesse de combat) n'avait aucun effet (cette fenêtre, ouverte tout le combat, comptait comme une attente du joueur). Corrigés : en combat, une fenêtre sans bouton 0x10 ni grille laisse A au terrain et n'est pas une attente. Mesure en temps réel, combat de 900 pas moteur : x1 = 31,1 s ; x3 avant = 31,1 s ; x3 après = 12,4 s (≈ 2,5 fois plus vite). Fin : « Félicitations ! Vous avez gagné 33 jetons ! », fenêtre type 51 (Jetons / Gagnés), retour en 0xc puis nouvelle mise.
- **Accès sans parcours manuel** : carte `hcy1b1` (sous-sol de Chandor : machines à sous uid 1416-1420, comptoir de jetons uid 1410 / 1411, coffres de cadeaux uid 1413-1415, fosse d'arène) ; second casino `ss5b1b`. Appel direct : `c.call(m.E('_ZN6window13CommandWindow19changeShopMenuPhaseEi'), c.export('_ZN16TownWindowSystem11m_singletonE'), phase)` ; phases 0xc comptoir de jetons (44), 0xd machine à sous (plante hors partie casino), 0xe poker (48), 0xf arène (50 → 49 → combat), 5 / 0xb échange de cadeaux (45 / 46), 0x13 vente d'armures du château, 0x15 type 13, 0x16 colisée (68), 0x17 échange de groupe, 0x18 Torneko, 0x1a sauvegarde.
- **Non vérifié** : colisée (phase 0x16, plante avec un groupe du chapitre 1 : il faut une sauvegarde du chapitre 2 avec Alina) ; animation du bingo (paquet 6, non rejouée) ; « ERROR 3080@ » dans certains dialogues de PNJ du casino (supposé : banque de textes d'un autre chapitre) ; libellé « Abandonner » du poker (chevauchement possible) ; touche H (historique) inactive en 0xf / 0x10 (voulu : pas de dialogues du terrain dans ces parties, à trancher).
- **Pièges de test** : le scénario GL est piloté par `Jeu.tick`, appelé à chaque pas moteur (`yield 45` = 45 pas moteur) ; pour mesurer une vitesse, comparer des durées réelles avec `DQ_TEMPS_REEL=1` ; ouvrir la Pause gèle le scénario ; `set_jetons` répété désynchronise les compteurs du moteur. Les tests de caméra et de vitesse utilisent des faux objets : `camera_libre(e)` et `sans_validation(mo, ui_g, port)` sont des fonctions de module, ne pas les remettre en méthodes. Tests : `outils/test_casino_bestiaire.py` (28).

### Non vérifié (#44)
Windows et vrai GPU ; la cause de la perte des bruitages de transition ; l'animation des ennemis à x2 / x3 ; la teinte jour / nuit réelle de la carte du monde ; le dessin de la fenêtre d'historique dans le jeu (voir captures de la section si présentes).

## Avance #45 : retours de 14 h 08 (02/11/2026)

### Historique et dialogues (agent « ui »)
- **Pas d'onglet « Favoris »** : une **case à cocher** « Favoris seulement » filtre la sélection courante (Dialogues ou Combats). Le filtre est commun aux deux onglets et **n'est pas conservé** d'une session à l'autre (Supposé, à confirmer).
- **Nom de l'interlocuteur dans la boîte de dialogue vivante**, comme sur mobile : un onglet au-dessus du cadre (frameData 191, cadre de base + onglet de 246 × 32), seulement quand le jeu envoie un nom. L'historique reprend la même mise en page (nom dans l'onglet ; sans nom, rendu habituel).
- **Taille fixe des boîtes** : historique et dialogues utilisent le même cadre, que le texte ait 1, 2 ou 3 lignes (au-delà de 3 : une page de plus « p/n »). (Depuis l'Avance #152, seule la boîte de l'**historique des combats** grandit en hauteur ; le cadre des dialogues ne change pas.)
- **Touches du menu par défaut** : Entrée et Tab (`touches_v` 5 ; les anciennes valeurs par défaut sont migrées, les touches choisies par le joueur ne bougent pas).
- **Menu Pause** : « Jeu » devient **« Triches »** (renommé **« Modifications »** en #47), juste sous « Commandes ». La section **« Défilement du texte »** (les deux options) est dans **Commandes, sous « Vitesses »** : c'est là que se trouve la section Vitesses ; Sylfried avait demandé « Affichage » → **à confirmer**.
- **Liste des interfaces** : les intertitres de groupe sont en gris doré terne ; l'or n'est plus que la valeur courante (« Boutons et croix… » n'était pas un titre mais la valeur sélectionnée). **« Combat : bouton de vitesse »** devient une interface propre (visible, taille 0,5 à 2,0, position libre ou ancrée sous la boîte du bas), séparée de « Boutons et croix de l'écran » (clés `bouton_vitesse`, `bouton_vitesse_taille`, `bouton_vitesse_pos`, migrées depuis `boutons_pos['combat']`).

### Caméra, écran et souris (agent « caméra »)
- **Moniteur du plein écran** (**retiré en #120, 03/11/2026** : le plein écran se fait sur l'écran de la fenêtre) : ligne « Écran du plein écran » (page Affichage, sous « Plein écran »), réglage `ecran_plein` ; la liste vient de pyglet, repli sur l'écran de la fenêtre si le moniteur a disparu. Logique pure dans `dq4_pc/ecrans.py` (35 tests).
- **Molette** : Ctrl + molette haut / bas = distance de caméra par défaut ; clic molette = position par défaut ; Ctrl + clic molette = les deux. Ctrl = Ctrl du clavier ou « Touche spéciale ».
- **Inversions** : `camera_inverser_gd` et `camera_inverser_hb` (Commandes, section « Caméra à la souris », défaut Non).
- **Escaliers** (essai fait en #47 : hauteur lissée, voir Avance #47) : aucun lissage de la hauteur de la caméra n'existe (moteur, Unity ni visionneuse) ; la caméra suit le héros en Y à chaque pas. La montée / descente ressentie vient de la hauteur du héros lui-même. Option « la caméra ignore la hauteur du héros » **proposée, non faite**.
- **Non vérifié** : Windows et vrai multi-moniteurs ; DPI par écran ; sensation de la souris réelle.

### Rayon de soin et animations d'objets (agent « effet »)
- Le rayon vert qui soigne PV et PM de l'équipe (`kifk01a`) **tournait de ~5° puis revenait** : mouvement (FPMV) et séquence de maillages (FSQD) partageaient une seule horloge ; chacun a la sienne dans le jeu. Corrigé dans `objets_carte.py` (états `tmot` / `tseq`, migration des anciens instantanés) ; fondu CrossFade de `fbx.py` du même côté de la sphère. Tests : `test_objets_carte` (35), `test_fbx_anim` (9). 96 cartes ont séquence + mouvement.
- Ce n'est pas la scène de l'église ; le soin vient de la surface de sol de type 4 (voir notes techniques).

### Décor : pierres qui « flottent » (agent « décor »)
- Mesure sur 63 cartes : les décalques plats (pierres, terre, fleurs, herbes) sont posés **1/8 d'unité (0,125)** au-dessus de la couche du dessous, comme dans le jeu (aucun Offset de profondeur dans les shaders). À 720 p, ~4 px : **fidèle, rien changé** (test `outils/test_decalques_sol.py`). Le liseré sombre vient des texels transparents noirs ; correctif possible (« option A », mélange de couleur des bords alpha) **non appliqué** : voir combat.

### Son (agent « son »)
- **Pas de jingle de mort dans le jeu d'origine** : un allié à 0 PV = SE 403 seul ; groupe battu = arrêt de musique (0x4008) puis BGM 23 ; victoire = SE 409 ; niveau = BGM 47 ; fuite et échec = SE 408. Rien à inventer.
- Corrigé côté visionneuse : musiques du moteur **décodées d'avance** (`BGM_PRECHARGES`, 22 musiques, 59 Mo, fil à part) ; **jingle protégé en jeu accéléré** (BGM 47 jouée 3,1 s à x1 comme à x3, contre 1,2 s avant) ; SE 409 rangé dans « Jingles et fanfares ». 30 tests.

### Lancement et changement de carte (agent « chargement »)
- **Effet de rideau au lancement** : cause trouvée et corrigée (CH-1) : la 1re image du titre montrait un ciel sans bandes latérales (bords noirs). Les causes propres à Windows (animation d'ouverture de la fenêtre, CH-4) sont des **mesures défensives non vérifiées** (retirables sans risque).
- **Micro-images au changement de carte** : le dessin est **retenu** (noir + fondus seulement) jusqu'à ce que décor, caméra et personnages soient en place (`Etat.chargement`, au plus 6 images) ; le temps du chargement n'est plus rattrapé par le moteur (le fondu ne saute plus). Mesuré : 111 images fautives → 0 sur 106 cartes. Durée des fondus inchangée.
- **Journal `DQ_SUIVI`** : `DQ_SUIVI=1` (console) ou `DQ_SUIVI=chemin` ; horodate le lancement et les 16 dessins qui suivent un chargement.
- **Non traité** : coupure franche sans fondu (écran non couvert) ; poses et directions des PNJ arrivent à k+6 ou k+12 comme dans le jeu d'origine.
- **Non vérifié** : Windows, vrai GPU, porte / escalier par touches en viewer, chargement d'un état.

### Alignement des textes de menu et de combat (agent « texte »)
- **Établi** : la visionneuse place déjà les TextMesh comme le jeu d'origine (texte « Ragnar » de l'onglet identique au pixel près sur captures mobile et PC, « Rat volant » et « Scarapince / ×2 » à ±1 px). Le texte « trop bas » (noms d'ennemis, onglets, boutons) existe **aussi dans le jeu d'origine** : les `lineSpacing` du jeu (0,441 cibles, 0,481 plaques de monstres, 0,801 onglets, boutons et noms) sont réglés pour la police japonaise ; avec SE-GARRIR l'encre descend de (1 − ls) × 23,525 × u / 2 sous le centre de sa boîte.
- **Correction (écart volontaire du jeu d'origine, à la demande de Sylfried)** : `ui_menu.recentrage_texte` remonte tout texte de `lineSpacing` < 1 de cet écart, en un seul endroit (`Rendu._texte`). `lineSpacing` ≥ 1 (PV / PM / Nv., listes) inchangé. `DQ_TEXTE_ORIGINAL=1` rend le placement exact du jeu. Mesures 1280 × 720 : nom de la plaque d'état −2 px, plaque de monstre −5 px, onglet −2 px, boutons −2 px. Commit séparé f756c63, écartable.
- **Non vérifié** : ancrages haut et bas (aucune capture mobile des plaques de monstres ni du nom dans la bande d'état) ; fenêtre de choix de cible (type 33) vue seulement en rendu hors écran, pas en combat à plusieurs groupes ; Windows et GPU réel. Historique, aperçu de l'éditeur et cartouche de nom ne passent pas par `Rendu._texte` : non recentrés.

### Combat : transitions, vitesses, contours, heure, coup critique (agent « combat »)
- **Cascade d'entrée et fondu de fin de combat à la durée du jeu**, quel que soit le réglage (accélérateur, vitesse de marche, « Vitesse de transition », Vitesse de combat, caméra) : `Etat.transition_combat()` (cascade, attente de chargement, garde de 8 images, fondus marqués « combat », fenêtres de 12 images à l'entrée et au retour) ; `Jeu._facteur_vitesse` rend 1.0 dans ces phases. Temps réel GL : cascade 1,9 s à x1 comme à x3 (2,17 s / 1,07 s avant) ; fondu de fin ≈ 0,95 s (0,61 s / 0,16 s avant). Les fondus étaient divisés par deux par `vitesse_fondu` = 2. Preuve principale en images du moteur (`test_transition_combat`, 15 tests, 72 combinaisons de réglages).
- **Vitesses auto sans temps mort** : Normal, Rapide et Très rapide imposent l'attente automatique la plus courte (`CODE_DEFILEMENT_AUTO = 0` : 12 images entre deux messages ; l'ancien Normal imposait le code 2 = 32 images). Attaque simple à x1 : 171 → 91 images (5,7 → 3,0 s) ; effet du coup → nombre de dégâts : 23 → 13 images (0,77 → 0,43 s). Manuel (code 4) inchangé ; animations, musique et bruitages inchangés. **Tour avec sort non mesuré** (aucun lanceur de sorts pilotable).
- **Contours des décors de combat** (`contours_decor.py`) : les silhouettes d'arbres et de montagnes sont des textures 256 × 256 à alpha binaire agrandies x6, d'où des escaliers de texels que le MSAA ne lisse pas, plus un liseré sombre (texels transparents noirs filtrés). Correction : alpha x4 (EPX 2 passes, flou 0,3 texel) et extension de couleur du bord opaque, sur les seules textures découpées à alpha binaire de 128 px et plus. Rugosité du contour −29 % à −52 %, surface ±0,4 %. `DQ_SANS_CONTOURS=1` redonne l'original. Coût 0,1 à 0,25 s par texture au chargement du décor. Ajout du portage, pas une copie d'Unity. Avec MSAA 0 il reste les marches d'un pixel (alpha-test dur).
- **Heure et décor de combat** : le soir **existe** (décor `_e`, orange, déjà affiché) ; l'**aube n'existe pas** comme décor (début et fin de nuit = `_n`). Rien à ajouter, mais `donnees.decors_de_secours()` prend la variante voisine si le moteur en demande une absente (avant : décor vide).
- **Coup critique** : l'effet existe et est dessiné (modèle d'effet 5344 en plus du 5303, SE 407, texte « Coup critique ! », dégâts ×3 environ) ; rien ne manquait. `son.py` ignore le bruitage 0 (plus de message « SE0000 illisible »).
- **Non vérifié** : Windows et vrai GPU (llvmpipe seulement) ; fluidité réelle des tours auto ; disparition du liseré sur l'écran de Sylfried ; demande de `btlcc1_n` ou des `_dk` manquants par le jeu.

### Personnages couchés et rencontres aléatoires (agent « sprites »)
- **PNJ allongé dessiné debout** : la visionneuse ignorait les paquets 16, 17 et 18. Le soldat du château (`taf1`) reçoit `0x0c000508` (paquet 16) et `[1040, 1863]` (paquet 17). Nouveau `pose_couchee.py` : le personnage couché a son propre chemin de sommets (`PC.sommets`), à plat (rectangle du panneau 0,48 × 0,64 vu de dessus, tourné de l'angle du sommeil et de la caméra), ombre non tracée. Il ne passe jamais par `_panneau_ville` : la correction de l'aplatissement des bords ne force donc **aucune** verticale (PNJ debout identiques au pixel près avant / après). Même mécanique pour le héros et les compagnons (`cmd_set_player_sleep` → paquets 0x08000500 / 0x08000501) et pour `cmd_character_action_sleep` (PNJ, 0x509 sur `mlm2f1`). 20 tests.
- **Cycle jour / nuit (réponse à la question, rien changé)** : il suit la **distance parcourue sur la carte du monde**, ni le temps réel ni l'horloge du moteur : +2 par pas où la position change, cycle de 3392 unités = 1696 pas marchés. À l'arrêt, dans un menu ou en combat : gelé. La marche accélérée et l'accélérateur l'accélèrent en proportion (cycle complet 56,6 s à x1 et 18,9 s à x3 sur l'horloge nominale) ; les combats rapides n'ont aucun effet. Les villes ont des zones horaires fixées par script.
- **Rencontres aléatoires (1 + a) / 2 par seconde réelle** quand la marche est accélérée d'un facteur a : x2 → 1,5 fois plus de combats par seconde, x4 → 2,5 fois (au lieu de a fois). Implémentation : `rencontres.py`, crochet Unicorn dans `CountDown::exec` (+0xc) qui multiplie la perte du compteur par (1 + a) / (2a) avec report des fractions ; pas de tirage supplémentaire, x1 identique au jeu. Mesuré sur le vrai moteur (24 000 pas) : 1,49 et 2,53 fois à x2 et x4 sur la carte du monde, 1,43 et 2,37 en donjon (bruit statistique ±7-10 %). Pas de rencontres aléatoires en ville (`encountFlag_` = 0). Aide ajoutée à la ligne « Vitesse de marche » du menu Pause. Tests : `test_rencontres` (9), `outils/simuler_rencontres.py`.
- **Supposé / non vérifié** : le crochet n'a pas été vu dans la visionneuse GL avec de vraies rencontres ; le facteur utilisé est nominal (si la machine ne tient pas le débit, les rencontres par seconde tombent un peu sous (1 + a) / 2) ; rendu GL d'un compagnon couché ou d'un lit qui recouvre un corps (profondeur vérifiée en géométrie seulement) ; déclenchements en partie (auberge, malade) non joués.

### Menu Magie (agent « magie »)
- **Cause de l'écran buggé** (`<ERR 0x07000000.0>`, `<ERR 0x03000000.0>`) : le moteur règle la liste de boutons nommés (`Make_NameButton`, type 8) par le **code 6 = preset** (`NOMS_PRESETS`), que la visionneuse ignorait. Une 5e rangée fantôme restait visible et cliquable sous « Premiers secours » (la liste de Doc n'a qu'un sort) ; le clic envoyait au moteur un sort inexistant, dont les chaînes de repli sont ces `<ERR …>`. Corrigé dans `Fenetre.code` / `_liste_noms` : seules les rangées dont le code n'est pas 0 sont actives. Vérifié de bout en bout sur le vrai moteur (liste de Doc = 1 rangée ; PM 30 → 28, PV de Ragnar 20 → 47, message de soin affiché).
- **« Coût en PM »** : le texte du moteur est `Coût en PM:<tab>  2` et `TextMesh.tabSize` = 8 ; la police de la visionneuse n'avait aucun glyphe de tabulation. Une tabulation vaut maintenant 8 espaces (limité à `Make_NameButton`). Dans la fiche du sort (type 7), « Coût en PM 10/ 30 » dépassait du cadre en français : limite droite `COUT_FICHE_X_MAX` = 214, compression (facteur mini 0,7, ici ~0,88). Les descriptions FR de 3 ou 4 lignes (9 sorts de terrain sur 18) sont **recoupées** à la largeur du cadre pour tenir sur 2 lignes (`Rendu._recoupe`, `DESC_FICHE_X_MAX` = 148) ; le texte du moteur n'est pas modifié. Supposé : le mobile coupait aussi ces descriptions.
- **Actions sans utilité** : traité en #47 (hors combat, un sort qui coûte des PM sans les faire baisser affiche « Mais il ne se passe rien. » ; voir Avance #47 et #48). Détail d'origine : `BaseAction::useMp` ne dépense que si l'action a eu un effet ; avant #47 la visionneuse affichait fidèlement le message de succès du moteur (« Les blessures de Ragnar guérissent ! »).
- **Non traité / non vérifié** : tabulations des types 20, 31, 33, 34, 35, 39 (combat, même règle probable) ; interface du choix de destination de Téléportation ; sort de combat de l'emplacement 3 ; descriptions du menu Objets ; sons.

### À trancher par Sylfried (**tranché le 03/11 à 15 h 50 : `decisions.md` § 5d, D-163 à D-190**)
- Section « Défilement du texte » : dans **Commandes sous « Vitesses »** (où se trouve la section Vitesses) ou dans **Affichage** comme demandé ?
- Recentrage des textes : écart volontaire avec le mobile (retirable : commit `f756c63`, ou `DQ_TEXTE_ORIGINAL=1`) ; en faire une option du menu Pause ?
- Liseré sombre des pierres au sol (« option A », mélange de couleur des bords alpha) : à appliquer aux décors de villes comme aux décors de combat ?
- Bouton de vitesse de combat : un réglage d'opacité ? (Filtre « Favoris seulement » : tranché en #47, voir Avance #47.)

### Non vérifié (#45)
Windows et vrai GPU (tout est en Mesa / llvmpipe) ; multi-moniteurs réel ; sensation de la souris ; CH-4 (animation d'ouverture de la fenêtre sous Windows) ; fluidité réelle des tours auto et tour avec sort ; liseré des contours sur l'écran de Sylfried ; rencontres vues en vraie fenêtre ; compagnon couché ou lit recouvrant un corps ; ancrages haut et bas du recentrage des textes ; fenêtre de choix de cible vue en combat à plusieurs groupes ; tabulations des fenêtres de combat ; historique rempli dans une vraie session.

### Outillage de test (#45)
- Les tests tournent **sans écran virtuel** avec `PYGLET_HEADLESS=1` (EGL) : plus d'attente sur `/tmp/xvfb.lock`. Lancer `python3 outils/test_X.py` (et non `-m unittest outils.X` : certains tests importent leurs voisins) ; variables `DQ_APK`, `DQ_SAVES`, `DQ_CACHE_CARTES`, `PYGLET_AUDIO=silent`.
- Fichiers de tests ajoutés : `test_ecrans`, `test_nom_dialogue`, `test_decalques_sol`, `test_chargement`, `test_texte_recentrage`, `test_contours_decor`, `test_coup_critique`, `test_decor_combat_heure`, `test_transition_combat`, `test_enchainement_tours`, `test_pose_couchee`, `test_rencontres`, `test_magie_liste` ; `outils/simuler_rencontres.py`.

## Avance #47 : retours de 22 h 29 (03/11/2026)

Lot traité avant celui des oublis du rapport d'audit (mis en pause : branche `agent47-docs`, non fusionnée). Neuf chantiers en parallèle. Légende : **Établi** (lu dans le code / mesuré / testé), **Supposé**, **Non vérifié**.

### Menu Pause : lignes inactives, « Modifications » (agent « pause »)
- **Lignes inactives** : une ligne qui ne peut pas être modifiée (`off` de `pause._choix` ou d'une entrée, relu à chaque image) est **entièrement grisée**, jamais choisie, survolée ni cliquée (le curseur et ↑ ↓ / molette la sautent) ; seule l'infobulle d'aide reste au survol. Les textes rouges `note=` sont supprimés (`Jeu.note_ecran` devient `Jeu.ecran_modifiable()`, `Rendu.plaque(grise=False)`). Les emplacements vides de la page « États » suivent la même règle. Règle valable pour toutes les cases du menu.
- **« Triches » devient « Modifications »** (libellé seul ; la clé `soin_niveau` ne change pas).
- Rouge conservé volontairement : message d'erreur sous un cadre, étiquette « Masquée » de l'éditeur d'interface, croix rouge du bouton muet.
- Test : `outils/test_lignes_inactives.py` (17). **Non vérifié** : Windows / vrai GPU, plein écran réel à deux moniteurs (simulé).

### Historique : une seule liste continue (agent « histo »)
- Dialogues et Combats : **une seule colonne**, plus ancien en haut, plus récent en bas, ouverte tout en bas ; défilement **au pixel** (molette 2 lignes, ↑ ↓ une ligne répétée, PgHaut / PgBas, Début / Fin, barre glissable, glisser), découpe `glScissor`. Plus de crans ni de pages. Liste courte collée en bas. Entrée ou clic sur l'étoile = favori du message choisi (`ui_historique.disposer`, `VueHistorique.pos`). Le choix du message par ↑ ↓ (« repère » doré, ↑ ↓ qui défilent d'une ligne) a été remplacé en #48 : voir Avance #48.
- **Favoris** : déjà conservés d'une session à l'autre (test sur deux sessions). Nouveau réglage `historique_favoris_seuls` (case « Favoris seulement », défaut décoché, pas de ligne Pause) : le « Supposé » de #45 sur le filtre non conservé est caduc.
- Test : `test_historique_messages` (96). **Non vérifié** : `glScissor` à une échelle autre que 100 %, ressenti molette / glisser, vraie session avec moteur.

### Sorts : message des sorts sans effet hors combat (agent « magie » ; texte changé en #48)
- Hors combat, un sort du menu Magie qui coûte des PM et **ne les fait pas baisser** (l'action n'a pas eu d'effet) affiche dans la boîte du jeu **« Mais il ne se passe rien. »** (message du moteur 0xc3d6d, aucune chaîne en dur ; en #47 : « Mais rien ne se passe. », 0xc3d6b, remplacé en #48). Un seul message pour un soin de groupe. Messages d'échec propres au jeu, sorts à 0 PM, sorts avec effet et combat : inchangés. Remplace le « Écart demandé, non implémenté » de #45.
- C'est le message officiel qu'Évac' hors donjon affiche déjà.
- Crochets en mémoire (`Moteur._crochets_magie`, vérifiés à l'installation, repli sur le jeu d'origine) : 0x16ca70 / 0x16ca74, 0x16dbe0 / 0x16dbe4, 0x16dd38 (détail dans les notes techniques). Test : `test_magie_liste` (29, avec les sauvegardes d'origine du mobile). **Non vérifié** : sorts des chapitres suivants, combat non rejoué (inchangé par construction).

### Caméra : toujours centrée, « Caméra au clavier », escaliers (agent « caméra »)
- **Option « Centrer la caméra sur le joueur » supprimée** (clés `camera_centree` et `suivi_camera_v` dans `CLES_OBSOLETES` : un ancien `reglages.json` reste lisible). La caméra des villes, donjons, tours et intérieurs est **toujours centrée sur le héros**, sauf quand le jeu la prend : `TownCamera` verrouillée (+0x3e) avec mode de cible (+0x48) et écart héros / cible (`Jeu._camera_menee`), caméra libre d'une scène (paquet 11, bit 7), casino et bestiaire (mini-jeux). Les anciennes bornes 16/9 sont retirées (Unity ne borne rien) ; carte du monde inchangée. Balayage des 529 cartes : 9 ont un verrou (mlb1a prologue, ev07, tatop : caméra menée ailleurs ; dib2, dib3a, skb1a, skb2a, slf3, sqf4 : verrou mode 0, cible = héros). Le drapeau `Global.Flag` bit 0x4 est rejeté comme critère (posé pendant tout message).
- **« Caméra » devient « Caméra au clavier »** (page Commandes).
- **Escaliers** (essai demandé, sans option) : la hauteur de la caméra est **lissée** (`CAM_Y_TAU` = 1 s, `CAM_Y_MAX` = 3 unités, `Jeu.cam_ref_y`) ; coupure du jeu ou caméra de scène = hauteur du jeu aussitôt. Retrait : `git revert 029b3f3` ou `CAM_Y_TAU = 0`. Mesures : rampe de `chf2` +1,94 u en 40 pas (héros 43 px plus haut puis recentré en 3 à 4 s) ; descente de `teout5` plafonnée à 3 u ; terrain plat inchangé. **Supposé / non vérifié** : la sensation (1 s et 3 u à l'estime).
- Tests : `test_camera_ville` (9), `test_reglages_interface` (classe `CameraToujoursCentree`), `test_mode_fenetre`, `test_priorite_jeu`.

### Écran-titre décentré : cause et correction (agent « titre »)
- **Cause** (pas une régression récente) : avec « Centrer la caméra sur le joueur » sur Non, `_camera_ville` appliquait les bornes 16/9 de la carte du titre `ev01` (milieu à x = +4,5 u, alors que le jeu place sa caméra à x = 0) : la caméra glissait de 4,5 u (≈ 29 % de la hauteur de fenêtre à 1430 × 815, ≈ 15 % de la largeur) et le logo, le dragon, l'île et le ciel partaient à gauche ; « Touchez l'écran » (couche d'interface centrée sur la fenêtre) ne bougeait pas. Code identique depuis #39 (le défaut Oui masquait le problème). Reproduit par capture.
- **Correction** : `CARTE_TITRE = 'ev01'` : sur l'écran-titre, ni centrage, ni lacet / angle hérités d'une partie, ni reste de centrage, ni zoom de distance ; la molette ne zoome plus sur le titre. Avec la suppression de l'option et des bornes, la cause racine a disparu aussi pour les autres cartes.
- Tests : `test_camera_titre` (7), `test_titre_centrage` (rendu réel, 3 formats, ~100 s, via `moteur_slot.sh`, `DQ_UICACHE`), `test_titre_ciel` (22). Logo à −0,014 hauteur ≈ 11 px = placement du jeu. **Non vérifié** : Windows / GPU / DPI, redimensionnement en vol, retour au titre depuis une partie (test unitaire seulement).

### Combat : transitions, vitesse, bouton de vitesse, cadre des commandes (agent « vitesse »)
- **Cascade et fondus de combat suivent « Vitesse de transition »** (annule la règle de #45 « durée du jeu quel que soit le réglage »). Cascade d'entrée : 57 images / facteur (`Moteur._debut_effet_combat`, `Etat.effet['duree']`, `Jeu._dessiner_effet` avance la simulation proportionnellement). Fondus d'arrivée, de fin de combat et de retour à la carte : 30 / facteur (`Etat._fondu`, plus d'exclusion « combat »). Avec x2 (défaut de #47, devenu x1 en #48) : cascade 28 images (0,93 s au lieu de 1,9 s), fondus 15 images. Fondus de script, de couleur et de blanc inchangés.
- **Vitesse de combat de la fin de la cascade au fondu de fin compris** : `Jeu._facteur_vitesse` vaut 1.0 seulement pendant la cascade (`Etat.effet`) et pendant le fondu d'arrivée sur la carte après le combat ; l'écran noir qui attend la scène, le fondu d'arrivée en combat, le message « X apparaît », les tours et le fondu au noir de fin sont à la vitesse de combat (Manuel et Normal 1, Rapide 2, Très rapide 3). Le fondu de fin suit donc les deux réglages (images : transition ; temps réel : combat), lecture littérale de la demande. Preuve : `test_transition_combat` (vrai moteur, x1 / x2 / x4, 72 combinaisons de réglages).
- **Bouton de vitesse qui apparaissait une image au mauvais endroit** (cause racine) : l'ancre était prise sur n'importe quelle fenêtre visible (bandeau de l'équipe, noms des monstres) et, avant la première boîte, sur la case par défaut de la grille (à gauche de l'écran). Elle n'est plus calculée que sur la boîte des messages et les fenêtres de commandes (`RG.FENETRES_COMMANDES_COMBAT`), reste en place entre deux boîtes et existe dès la première image ; garde-fou `Boutons._ancre_prete`. Correction annexe : le décalage vertical du message était oublié si le joueur avait réglé « Dialogues ». Test : `test_bouton_vitesse` (position du bouton à chaque image d'un vrai combat ; échoue sans le correctif).
- **Cadre des commandes à la largeur des dialogues** : cadre des commandes 459 unités, messages d'action (types 2 et 3) 510, d'où un saut de 23 px du bouton au début d'un tour. Taille par défaut des 7 fenêtres de commandes = 510 / 459 (`reglages.DEFAUT['interface_fenetres']`, `FENETRES_COMMANDES_COMBAT`, `LARGEUR_COMMANDES`) ; ↺ et « Rétablir » y reviennent (`RG.fenetre_defaut`). Migration : clé `interface_v` = 2, un `reglages.json` plus ancien reçoit la taille une seule fois (fenêtre absente ou à [1, 0, 0]) ; un choix explicite est conservé.
- **Reste** : entre « X apparaît » (459) et le premier menu de commandes (510), le bouton se décale encore de 22,5 px, une fois par combat ; les 4 premières images l'ancrent sur la boîte de terrain (1,8 px de saut).
- **Non vérifié** : Windows / GPU ; ressenti de la cascade et du fondu raccourcis ; combats à plusieurs alliés (`BattleChangeInfo`) ; `reglages.json` réel migré ; rejeu moteur de `test_vitesse_combat` (`RejeuMoteur`) non relancé par le chantier.

### Décor de combat selon l'heure (agent « décor »)
- **Le jeu n'a pas de décor de combat d'aube** : la variante est choisie par la zone horaire du monde (jour `_d`, soir `_e`, nuit et aube `_n`) ; le soir `_e` est un vrai coucher de soleil (ciel et collines orange), déjà affiché. Le lever de soleil existe sur la carte du monde et en ville, pas en combat. **Ce que Sylfried a vu sur mobile n'est pas établi** (hypothèse : le décor `_e`). Tableau et adresses dans les notes techniques.
- **Fond du décor = `bg_color` du bloc FETC** de la carte de combat (cache `fonds_decor.json`, `teinte_carte.Fonds`), plus une estimation du sol ; `DQ_FOND_ESTIME=1` force l'ancien comportement. Gain d'exactitude : 0 à 0,43 % des pixels changent sur les décors du monde (bords), rien sur les donjons et tours.
- Secours des variantes absentes : `donnees.decors_de_secours` traite `_dk` (n, d, e, puis nom sans lettre ; **supposé**, aucun `_dk` de combat n'existe pour se, sd, mt).
- Test : `test_decor_combat_heure`. **Non vérifié** : rendu de `BackColor` sur appareil ; `MoteurReel` non rejoué après les modifications finales (captures forcées aux heures 1000, 2000, 2500, 3300 lues).

### Caméra de combat : rien à ajouter (agent « camcombat »)
- Les mouvements de caméra des attaques et des sorts (secousses, plongées, glissements de boss) **viennent du moteur** (un paquet 10 par image) et la visionneuse les applique déjà tels quels (`Etat.appliquer` → `Jeu._rot_camera` → `_camera_combat`) ; l'horloge est celle du moteur, donc `_facteur_vitesse` s'applique sans rien de plus. Le roulis est géré mais le jeu n'en envoie jamais (0 sur 198 caméras balayées) : G-073 (roulis) sans objet. Aucun mouvement ignoré trouvé : aucun code modifié, un test ajouté (`test_camera_combat`, 16).
- Les secousses des premiers monstres sont discrètes (1,1° de tangage ≈ 16 px à 720p, 13 images). **Ce que Sylfried a vu sur mobile n'est pas établi** : il faut le nom du monstre ou de l'attaque (ou des effets d'écran 3 / 5 / 6, flashs de sorts, qui ne sont pas des caméras).
- **Non vérifié** : comparaison avec le mobile ; quel sort ennemi déclenche quelle caméra (table effet → caméra non décodée, 1 à 2 h) ; caméra 132 (boss final).

### Bruitages : transition de carte et coffre d'ennemi (agent « son »)
- **Bruitage de transition de carte (cause trouvée)** : le bruitage 305 n'est pas perdu par la visionneuse, le **moteur ne le demande plus**. `Global::startTown` / `startField` (et `ChangeGamePart`, `startFirstTown`, `startDebugTown`) lancent le fondu au noir de 30 images (paquet 9) et arment un décompte de 15 (octet `LIB + 0x258254`, décrémenté par `Global::NativeExec`) ; à 0, `TownSystem::playTownExitSE` / `FieldSystem::playFieldExitSE` jouent le SE 305 seulement si l'ancienne scène vit encore. Le jeu charge la carte suivante à la fin du fondu (30 images). Avec le fondu raccourci (« Vitesse de transition »), le chargement détruisait l'ancienne scène avant les 15 images : x1 SE à +14 (chargement à +32), x2 marge de 3 images, x3 et x4 aucun bruitage (défaut x2 à la limite d'où des bruitages « manquants » au hasard ; supposé : réglage x3 ou x4 chez Sylfried). La porte (SE 309) n'est pas concernée.
- **Correction** (`moteur.py`) : `Etat._fondu` mémorise `rapport_fondu` (durée jouée / durée d'origine) et `Moteur._decompte_sortie` (appelée dans `step` après `appliquer`) remet le décompte à la même proportion (jamais moins de 1) quand il vient d'être armé et qu'un fondu raccourci de cette sortie arrive (fenêtre de 2 images). Rapport 1 (x1, fondus de script) : aucune écriture ; durée des fondus inchangée. Vérifié sur le moteur réel (église ↔ village, village ↔ carte du monde, x1 à x4) et dans la boucle de la visionneuse avec accélérateur (journal du son 300, 309, 305). Tests : `test_bruitage_transition` (9, échoue sans le correctif), `test_son_mixage` (+1). Autres émetteurs de bruitage de changement de carte (lus, non rejoués) : `TownDoorAction` 309, `TownKaidanAction::update` 305 direct (escalier), `TownFallAction` 312, `TownSubeAction` 330, `TownMenu_MAGIC_MOVE::moveTown` 306.
- **Coffre lâché par un ennemi : le jeu ne joue aucun bruitage d'ouverture.** Messages (« X laisse tomber un coffre au trésor ! », « Ragnar l'ouvre. », « Il contient Y ! », « Ragnar met Y dans le sac. ») = tâche `BattleExecItem` (quatre sous-tâches `BattleExecVictory30` / `31` / `31a` / `32`) : texte et `giveItem` seulement, aucun appel au gestionnaire de sons ; Unity n'a que trois sites d'appel direct à `Sound.PlaySE` (`InputName.Update`, `MenuPortItem.Update`, `TouchPad.internalUpdate`). Moteur réel, butin forcé : seuls paquets de son = le bip 300 au début de chacun des 4 messages. Test : `test_coffre_ennemi` (2). **Supposé** : Sylfried se souvient du bip 300, de la version DS ou du coffre de ville (`TownFurnitureObject::openObject`). **Non vérifié** : mobile ; chapitre 3 réel (butin forcé en chapitre 1). Rien n'a été ajouté (le jeu fait foi).
- **Non vérifié (son)** : audio réel (Windows, haut-parleurs) ; escalier, téléportation, chute (même décompte, jamais rejoués) ; chemin `ChangeGamePart`.

### À trancher par Sylfried (#47) (**tranché le 03/11 à 15 h 50 : `decisions.md` § 5d, D-163 à D-190**)
1. **Fondu de fin de combat** : accéléré aussi par la vitesse de combat (fait, lecture littérale) ou de durée réelle fixe ? (recommandation : laisser accéléré).
2. **Bouton de vitesse** : le décalage restant de 22,5 px une fois par combat (entre « X apparaît » et le premier menu) te gêne-t-il ? (recommandation : l'accepter).
3. ~~Vitesse de transition x2 par défaut~~ : tranché en #48, le défaut est **x1**.
4. **Menu Pause** : l'infobulle d'aide reste au survol d'une ligne grisée (recommandation : garder) ; étendre la règle des lignes inactives aux écrans d'avant-partie ?
5. ~~Historique : ↑ ↓ défilent d'une ligne~~ : tranché en #48, ↑ ↓ passent de message en message ; liste courte collée en bas (gardée).
6. ~~Évac' hors donjon~~ : tranché en #48, son message devient aussi celui des sorts sans effet.
7. **Escaliers** : garder le lissage (1 s, 3 u) ou l'allonger (`CAM_Y_TAU` 1,5 à 2) ou retirer ? À tester sur Windows.
8. **Décor de combat d'aube / de coucher de soleil** et **angles de caméra des attaques** : le jeu ne contient rien de plus que ce que la visionneuse affiche déjà ; il faut une capture mobile (lieu, heure) ou le nom du monstre / de l'attaque pour chercher autre chose.
9. **Coffre lâché** : aucun bruitage d'origine ; en vouloir un quand même (option du menu Son, désactivée par défaut) ?

### Non vérifié (#47)
Windows et vrai GPU ; ressenti de la caméra des escaliers, de la cascade et des fondus raccourcis, de l'historique continu (molette, glisser, `glScissor` à une échelle ≠ 100 %) ; plein écran à deux moniteurs ; combats à plusieurs alliés (bouton de vitesse) ; `reglages.json` réel migré (`interface_v`) ; audio réel ; caméra 132 (boss final) ; mobile (aucune capture).

### Outillage de test (#47)
Nouveaux tests : `test_lignes_inactives`, `test_titre_centrage` (rendu réel, `DQ_UICACHE`), `test_bouton_vitesse`, `test_camera_combat`, `test_coffre_ennemi`, `test_bruitage_transition`. `outils/flux_session/moteur_slot.sh` limite à deux le nombre d'exécutions du moteur en parallèle ; `pr.sh` lit l'URL de session dans `DQ_SESSION`. Les tests de magie et d'historique de combat attendent les sauvegardes **d'origine du mobile** (emplacement 1 : Ragnar à Strattbourg), pas celles que Sylfried a rejouées depuis.

## Avance #48 : retours de 07 h 33 (03/11/2026)

Quatre retours, traités un par un (petit lot, sans sous-agents). Légende : **Établi** (lu dans le code / mesuré / testé), **Supposé**, **Non vérifié**.

### Sorts sans effet : « Mais il ne se passe rien. »
- Demande : si un message officiel existe, l'utiliser plutôt que « Mais rien ne se passe. ». Il existe : « Mais il ne se passe rien. » est le message qu'Évac' hors donjon affiche déjà (id 0xc3d6d, texte du patch FR). `Moteur._crochets_magie` l'écrit désormais (`MSG_IL_NE_SE_PASSE_RIEN`) à la place de 0xc3d6b pour un sort qui coûte des PM sans les faire baisser (soins à PV pleins, Multisoin en pleine forme : un seul message).
- **Inchangés** : les messages d'échec propres au jeu, qui disent encore « Mais rien ne se passe. » (Rappel sur un vivant, Antipoison sans poison, Sifflet) ; ce sont les textes du jeu, pas un ajout de la visionneuse. Évac' garde « Mais il ne se passe rien. ».
- Établi : l'id lu en mémoire pendant le lancement d'Évac' (`UseActionParam + MAGIE_RESULTAT`) est 0xc3d6d ; le champ « échec » de la table des actions pour cette action (0xaae7e) n'est PAS le message affiché (essai à vide : « ERROR 700030 »). Test : `test_magie_liste` (29, avec les sauvegardes d'origine du mobile). **Bruitages : voir l'Avance #150** (le bruitage de soin est coupé quand le sort n'a aucun effet).

### Vitesse de transition : x1 par défaut
- `reglages.DEFAUT['vitesse_fondu']` passe de 2,0 à **1,0** (la cascade d'entrée en combat dure de nouveau 1,9 s et les fondus 30 images, comme le jeu). Les crans x1 à x4 restent au choix.
- **Migration** (nouvelle clé `vitesse_fondu_v` = 2) : un `reglages.json` enregistré avant (sans cette clé) dont la vitesse vaut encore l'ancien défaut x2 passe à x1 **une seule fois** ; tout autre cran est conservé ; ensuite la clé est enregistrée et un x2 choisi par Sylfried reste x2. **Limite** : on ne peut pas distinguer un x2 voulu d'un x2 resté par défaut ; si Sylfried l'avait choisi exprès, il doit le remettre une fois.
- Tests : `test_reglages_son_texte` (+1, `test_vitesse_de_transition_par_defaut_x1`), `test_reglages_interface` (clé classée hors interface).

### Historique : ↑ ↓ message par message, sans grisé
- **Clavier** : ↑ / ↓ (et la répétition de la touche maintenue) choisissent le message précédent / suivant, un à la fois ; ils ne font plus défiler la liste. La vue ne défile que pour montrer **en entier** le message choisi, quand il est coupé par un bord de la fenêtre ou hors de la fenêtre, et **du minimum** : son bord rejoint le bord de la fenêtre (`ui_historique.decalage_pour_voir`, `etendue`, `elements_visibles` : fonctions pures testées). Le premier et le dernier message se montrent avec la marge de la liste (on arrive tout en haut / tout en bas). Un message plus haut que la fenêtre : son début en haut. PgHaut / PgBas défilent d'une page (le message choisi devient le plus proche message entièrement visible) ; Début / Fin choisissent le premier / dernier message.
- **Message choisi** : `VueHistorique.sel` ; plus de « repère » (`element_au_repere`, `hauteur_repere`, `REPERE_BAS/HAUT`, `pmax`, `sel_manuel` supprimés). Au clavier, un clic ou la touche Entrée agissent sur lui. À la souris, le message **survolé** devient le message choisi (image par image, y compris pendant la molette) ; la molette, la barre et le glissement ne changent pas le choix. Si le message choisi n'est plus du tout dans la fenêtre (molette), le premier appui sur ↑ ↓ le remplace par le plus proche message visible, sans avancer d'un rang de plus.
- **Plus de grisé** (dérogation à la règle générale des menus, demandée pour l'historique seulement) : la boîte n'est plus éclaircie (rectangle blanc translucide supprimé de `_boite_dessin`) au survol ni au choix ; seule la **petite flèche dorée** marque le message choisi, au clavier comme à la souris. Les onglets, la case « Favoris seulement » et l'étoile gardent leur surbrillance habituelle.
- Texte d'aide : « Haut / Bas : message précédent / suivant », « Molette : défiler ».
- Tests : `test_historique_messages` (99 ; 8 tests réécrits ou nouveaux : message par message, défilement minimal, messages coupés en haut / en bas, toutes les longueurs de liste, molette puis clavier, aucun grisé). Captures du vrai dessin (harnais hors dépôt) : flèche seule, pas de grisé, message choisi collé au bord haut après sept ↑.
- **Non vérifié** : ressenti du défilement instantané (pas d'animation) ; répétition de la touche maintenue avec le vrai `Pause.maj` (seulement l'appel, simulé) ; Windows / GPU.

### À trancher par Sylfried (#48) (**tranché le 03/11 à 15 h 50 : `decisions.md` § 5d, D-163 à D-190**)
1. **x1 par défaut** : si tu avais choisi x2 toi-même, la migration l'a ramené à x1 une fois ; le remettre une fois suffit.
2. **Défilement de l'historique au clavier** : instantané (le bord du message rejoint le bord de la fenêtre). Un défilement doux (quelques images) est possible si tu le préfères.
3. **PgHaut / PgBas** dans l'historique : défilent d'une page et déplacent le choix sur le message entièrement visible le plus proche ; veux-tu plutôt qu'ils sautent de N messages ?

### Non vérifié (#48)
Windows et vrai GPU ; le texte exact « Mais il ne se passe rien. » est celui du patch FR lu en jeu (moteur réel), pas comparé à un mobile ; `reglages.json` réel migré (`vitesse_fondu_v`) ; ressenti de l'historique.

## Avance #49 et #50 : docs, CI et décisions du 03/11/2026 (docs seulement)

Aucun changement de code dans `dq4_pc/` ni dans les tests. Relecture du rapport « ce qu'il reste » avec Sylfried (13 h 45 à 14 h 19, il ne pouvait pas tester). Ce qu'il a dit sert à **structurer le projet et le reste à faire** ; rien n'est lancé.

### Fait
- **#49** : README, `docs/workflow.md`, notes techniques (section « Écritures et crochets en mémoire du moteur » : 27 crochets vérifiés à l'exécution, 18 sites qui écrivent, S10 sorts du menu Magie, S11 décompte du bruitage de sortie), fiches d'audit périmées (caméra, curseur doré, roulis), CI `.github/workflows/ci.yml` (compilation + fichiers interdits ; **verte sur GitHub** pour la PR #49).
- **#50** : le dépôt `dq4-pc` **n'existe plus** (Sylfried) : références corrigées partout (README, workflow, reprise, audit) ; l'état de ses issues au 02/11 est conservé dans `docs/audit/github_issues.md`. Décisions du 03/11 enregistrées (`docs/audit/decisions.md` § 5c, D-149 à D-160 ; `rapport_reste_a_faire.md`, « Réponses de Sylfried » et « Cap fixé » ; `lacunes_connues.md`). Document du Projet `depot-github-dq4-pc.md` remplacé par `depot-github-dq4-portage.md`.

### Décisions de Sylfried (03/11)
- **Toits** : laissés tels quels, « c'est le fonctionnement du mobile ». **Éditeur d'interface** : supprimer tout ce qui n'a aucun élément à modifier (les 18 entrées retirées suivent ce critère). **« Masqué / Masquée »** : validés. **`Menu_Echap_DQ4_PC.xlsx`** : plus d'actualité.
- **Manette** : prévue pour la suite. **Licence d'Unicorn** : vérification acceptée (à faire).
- **Tous les boutons de l'interface accessibles au clavier** (exigence). **Bruitage au clavier** : seulement dans les mêmes situations qu'au toucher (jamais ajouté de force ; par exemple un bip par caractère du nom *si* le toucher en joue un).
- **Sauvegardes du chapitre 2** : il les fournira dès que possible.
- **Tout tenir à jour** (CI, documents, `.md`) à chaque PR.

### Reste à faire (structuré, rien de lancé)
1. Validation Windows / vrai GPU. 2. Clavier complet : inventaire des boutons qui n'y sont pas (cas connu : « Sauvegarde rapide » de l'écran Divers, G-096), puis correction, avec la règle du bruitage (G-173). 3. Manette. 4. Chapitre 2 (jouer ses cartes, PNJ et menus dès les sauvegardes). 5. Licence d'Unicorn. 6. Paquets du moteur (6, 30, effets d'écran 3 / 5 / 6) et petits oublis.

### Suivi par issues (03/11/2026, PR #89)
Sylfried (14 h 25) : « je veux bien des issues sur le reste à faire ». **38 issues créées dans `dq4-portage` (#51 à #88)**, en 5 jalons (1 Validation Windows #51-#58, 2 Clavier complet et manette #59-#61, 3 Chapitre 2 et services #62-#65, 4 Moteur et finitions #66-#85 dont 11 bugs, 5 Distribution et extensions #86-#88) ; nouvelles étiquettes `type:feature`, `type:bug`, `type:recherche`, `test-windows`, `priorité:haute`, `bloqué`. Pas d'issues rétroactives pour le travail déjà fait (choix de Claude : les 50 PR « Avance #N » et `docs/historique.md` font foi). Issues et PR partagent la même numérotation : `pr.sh` prend le plus grand numéro + 1, donc la PR suivante est #89 (la série « Avance #N » saute de #50 à #89). Détail : `docs/workflow.md`, `docs/audit/rapport_reste_a_faire.md` (« Suivi dans GitHub »).

### À trancher par Sylfried (#50) (**tranché le 03/11 à 15 h 50 : `decisions.md` § 5d, D-163 à D-190**)
1. ~~**Issues dans `dq4-portage` ?**~~ **Réglé le 03/11 à 14 h 25** : oui, pour le reste à faire (voir ci-dessus).
2. **Branches fusionnées** : supprimer les 56 branches distantes déjà fusionnées (décision 2 de l'audit) ? Il a demandé si cela change quelque chose : non (tout est dans `main`, les PR restent consultables) ; **non fait** sans un « oui » explicite.

### Non vérifié (#50)
Tout ce qui a été vu l'a été sous Linux (Mesa) ; la CI n'a tourné qu'une fois (verte), sans essai d'un fichier interdit réel (le motif a été essayé en local).

## Avance #100 : lecture du reste à faire et ménage (03/11/2026, docs seulement)

Aucun changement de code dans `dq4_pc/` ni dans les tests (phase gestion de projet, D-189). Sylfried a lu la liste « tout ce qu'il reste à faire » (15 h 50) et répondu point par point. Légende : **Établi**, **Supposé**, **Non vérifié**.

### Fait
- **Branches** : les 57 branches fusionnées ont été supprimées **par Sylfried** (le proxy de la session refusait toute écriture sur les branches, 403) et la suppression automatique est activée (D-163). `main` est la seule branche.
- **Issues** : 7 fermées (#51, #54, #55, #57, #78, #82, #86), 10 créées (#90 à #99), 11 réécrites ou complétées (#52, #53, #56, #58 à #62, #80, #83, #88) et commentaires sur #75 et #87 ; nouvelles étiquettes `à décider` et `priorité:basse`. Bilan : 48 issues, 41 ouvertes.
- **Décisions** : D-163 à D-190 (`decisions.md` § 5d). L'exigence « tous les boutons au clavier » (D-155) est **suspendue** (D-165) : « à creuser », #59.
- **Lacunes** : 86 des 161 lignes de `lacunes_connues.md` retriées (63 closes, 25 traitées, 71 ouvertes ensuite). La ligne G-039c (« pièces `MAP_DIFF` non reproduites ») était périmée : les pièces sont reproduites (`_plan_monde_fenetre`).
- **Licence d'Unicorn** (#86) : à traiter comme GPL v2 (`docs/licences.md`) ; choix à faire avant le `.exe` (#87).
- **Plan de test du chapitre 2** : `docs/audit/plan_tests_chapitre2.md` (D-168).
- **Ménage** : briefs des lots déplacés dans `docs/archives/briefs/` ; modèles d'issue alignés sur le format des issues (Contexte, Critères, Références) et nouveau modèle « Test sur Windows » ; `historique.md` complété jusqu'à #100 ; `reprise.md` §6 réécrit ; pointeurs « Reste à faire » corrigés ; README à jour.

### Validé par Sylfried sur Windows (établi par lui)
Premier lancement du `.bat` ; sauvegardes (église, automatiques, hors églises, création et suppression de journal) ; plein écran (F11, Alt + Entrée) et autres ratios ; comparaison au mobile (tailles de texte, placements, croix, plume, dragon du titre) ; combat de boss du chapitre 1, groupes, Morph de la cinématique, game over, nouvelle partie sans relancer ; historique après combats ; teinte jour / nuit (carte et villes) ; fenêtre « Interface » glissée à la souris ; murs de `dbout` et vagues d'eau des grottes résolus ; ordre de tracé des monstres, fenêtres de combat, escaliers : « tout bon ».

### À trancher par Sylfried (#100) (**tranché le 03/11 à 16 h 47 : voir « Avance #102 » ci-dessous**)
1. **Licence** : (a) rester sur « scripts + `.bat` qui télécharge Unicorn », (b) publier le portage sous GPL v2 pour embarquer Unicorn dans un `.exe`, (c) un autre émulateur ; et choisir une licence pour le code du portage (`docs/licences.md`, #87).
2. **Accélérateur et jingle** (#96) : lecture retenue (supposé) = pendant un jingle, la touche d'accélérateur est neutre, sauf pour une transition de carte à carte. **Remplacé le 03/11 à 16 h 47** (D-197) : plus d'accélérateur hors combat, transitions de porte à x4 fixe (#101) ; #96 fermée.
3. **Espace et discussion de groupe** : « Espace ne fait plus les discussions de groupe » est lu comme « le cas limite n'arrive plus » ; si c'est la discussion de groupe qui ne s'ouvre plus du tout avec Espace, le dire.
4. **Petits restes** (#99) : mode « menus simples » (garder, simplifier, retirer ?), bandeau « Prologue » (le cadre doré à fond bleu s'affiche-t-il ?), « sort en trop » (est-ce la rangée fantôme supprimée en #45 ?), coffres (sens d'ouverture).

### Non vérifié (#100)
Rien n'a été exécuté côté outil. Les affirmations sur le code de ce paragraphe (pièces `MAP_DIFF` reproduites, rangée fantôme de la liste des sorts supprimée en #45) sont lues dans le code et les notes, non revues à l'écran. Licence : textes publics lus (COPYING, métadonnées), pas d'avis juridique. Les lectures « à confirmer » ci-dessus sont des interprétations de phrases de Sylfried.

## Avance #102 : réponses de 16 h 47 (03/11/2026, docs seulement)

### Fait
- **Issues** : #101 créée (transitions à x4) ; #53, #87, #92, #99 réécrites ; #96 fermée (remplacée par #101) ; commentaire sur #75. Bilan : 49 issues (#51 à #99 et #101), 41 ouvertes, 8 fermées (#51, #54, #55, #57, #78, #82, #86, #96).
- **Décisions** : D-191 à D-200 (`decisions.md` § 5e) ; D-180, D-182, D-188 et D-190 annotées.
- **Lacunes** : G-008, G-012, G-015, G-039c, G-058, G-108, G-162, G-205, G-212, G-213 mises à jour.
- **Licences** : `docs/licences.md` complété (option « `.exe` launcher », « Faut-il un fichier `LICENSE` ? ») ; **aucun fichier `LICENSE` créé** (pas nécessaire aujourd'hui, D-196).
- **Plan de test du chapitre 2** : caméra des attaques (ennemis du chapitre 1 d'abord), coffres cochés, « sort en trop » à vérifier.
- Aucun fichier de `dq4_pc/` ni de `outils/` modifié.

### Validé par Sylfried sur Windows (16 h 47, établi par lui)
Pièces `MAP_DIFF` du plan du monde ; bandeau « Prologue » (cadre doré à fond bleu) ; sens d'ouverture des coffres.

### Décidé, pas encore codé
- **Transitions à x4** (#101 ; seul le réglage « Vitesse de transition » disparaît, marche et Maj restent : D-201) : ce qu'il faut savoir avant de coder. Les bruitages de transition (lus dans le moteur, **non rejoués**) sont **305** (sortie de ville ou de carte, escalier), **309** (porte), **312** (`TownFallAction`), **330** (`TownSubeAction`) et **306** (sort de déplacement) ; le 305 n'est joué qu'à mi-fondu, donc la transition doit être reconnue à son départ. Voir « Bruitages : transition de carte et coffre d'ennemi » plus haut.
- **Menus simples** : repli automatique seulement, sans option (D-194).

### À trancher par Sylfried (#102)
1. **Étendue de la suppression des vitesses** (#101) : **tranché à 17 h 01 (D-201)** : seul le réglage « Vitesse de transition » disparaît ; la marche et la touche Maj restent.
2. **Sort de déplacement (306)** : **tranché à 17 h 03 (D-202)** : durée d'origine ; Sylfried le teste, peut-être accélérable avec Maj.
3. **Format de distribution** (#87) : scripts + `.bat`, `.exe` launcher, ou `.exe` qui embarque Unicorn (GPL v2) : « on verra ».
4. **Audio réel et `reglages.json`** (#99) : **expliqué à 17 h 03 (D-202)** : jamais vus sur son PC (essais sans haut-parleurs, fichiers de réglages fabriqués) ; rien à décider. **Réglé à 17 h 07 (D-203)** : l'audio fonctionne ; pas de souci pour `reglages.json`.

### Non vérifié (#102)
Rien n'a été exécuté côté outil. Les bruitages 305, 309, 312, 330 et 306 sont lus dans le code du moteur, jamais rejoués. L'idée qu'un `.exe` launcher n'ait pas les obligations d'une redistribution d'Unicorn est une **supposition** (pas un avis juridique). La citation de la documentation GitHub sur les dépôts sans licence a été lue le 03/11/2026.

## Avance #103 : précision de 17 h 01 (03/11/2026, docs seulement)

### Fait
- **Précision de Sylfried** (D-201) : « Ah pardon si la vitesse de marche et l'accélération à la touche SHIFT doit rester ! je parlais surtout de l'accélération des transitions ! ». Seul le réglage « Vitesse de transition » disparaît ; la marche, la caméra et l'accélérateur Maj ne changent pas. Ma lecture de 16 h 47 (« Avance #102 ») était trop large.
- **Issues** : #101 retitrée et réécrite (« Transitions : retirer le réglage « Vitesse de transition »… ») ; #53 retrouve son périmètre (marche x3 / x4 et accélérateur, plus combat « Très rapide » et transitions à x4) ; commentaire correctif sur #96 (reste fermée).
- **17 h 03 (D-202)** : le sort de déplacement (306) n'est pas raccourci (Sylfried le teste lui-même, peut-être avec Maj) ; #99 : « audio réel » et `reglages.json` expliqués, rien à décider.
- **Documents** : D-197 précisée, D-201 et D-202 ajoutées ; G-008, G-212 et G-213 corrigées ; `reprise.md`, rapport et `historique.md` alignés.
- Aucun fichier de `dq4_pc/` ni de `outils/` modifié.

### Non vérifié (#103)
Rien n'a été exécuté côté outil. La lecture « l'accélérateur de la phrase du 15 h 50 était la vitesse de transition » est une **supposition**. Les bruitages 305, 309, 312, 330 et 306 restent lus dans le code, jamais rejoués.

## Avance #104 : audio validé (03/11/2026 à 17 h 07, docs seulement)

### Fait
- **Validé par Sylfried sur Windows** (D-203) : « l'audio fonctionne ». Les mentions « audio réel (Windows, haut-parleurs) non vérifié » des sections plus haut sont donc **périmées** pour le rendu général ; restent supposées les catégories de son 302 / 303 (G-121).
- **`reglages.json`** : « pas de souci pour le fichier, je peux toujours voir quand une valeur par défaut a été changée par le bouton de la flèche » : pas de test de conversion de plus ; la conversion de #101 (retrait de `vitesse_fondu`) reste à coder avec ses tests habituels.
- #99 : point « son et `reglages.json` » coché ; il reste la position de la fenêtre « Interface », `g_pad_pos`, `--ui-simple` et le « sort en trop » à vérifier.
- Aucun fichier de `dq4_pc/` ni de `outils/` modifié.

### Non vérifié (#104)
Rien n'a été exécuté côté outil. « L'audio fonctionne » est le constat de Sylfried, sans détail (volumes, boucles, jingles).

## Avance #106 : test issue par issue (#52 d'abord) et issue #105 (03/11/2026, docs seulement)

### Fait
- **Issue #105 créée** (jalon 5, `type:feature`, `à décider`, `priorité:basse`) : décider des modificateurs et des triches que Sylfried voudrait ajouter, **à traiter en tout dernier** (D-205). Sa liste reste à fournir ; faisabilité à étudier cas par cas (moteur `libdq4core.so` non modifié sous Unicorn : **supposé, non vérifié**).
- **Séance de test du soir** (D-204) : Sylfried renonce à la liste globale et teste **une issue à la fois**, à partir de #52 (anticrénelage, suréchantillonnage, deux moniteurs, fenêtre plus grande que l'écran). Fiche de test donnée dans la conversation (menu Échap, page « Affichage » ; critères de l'issue inchangés).
- Bilan : 50 issues (#51 à #99, #101 et #105), 42 ouvertes, 8 fermées (#51, #54, #55, #57, #78, #82, #86, #96).
- Aucun fichier de `dq4_pc/` ni de `outils/` modifié.

### Non vérifié
Rien n'a été exécuté côté outil. Les réglages de la fiche #52 sont lus dans `pause.py` (établi), jamais vus sous Windows par Claude.

## Avance #113 : retours du test de #52, libellé « Antialiasing », course après une porte (03/11/2026)

### Retours (Sylfried, 19 h 38 et 19 h 41)
Voir D-206 à D-213 (`docs/audit/decisions.md` § 5e) : antialiasing et deux moniteurs validés, suréchantillonnage x2 qui saccade, résolution 4K absente de la liste (voulu), six nouvelles issues (#107 à #112), phase « gestion de projet » levée pour les corrections du soir.

### Fait
- **Libellé « Antialiasing »** (D-206) : page Affichage du menu Échap (`pause.py`) et affichage de test (`fenetre.py`) ; test `test_mode_fenetre.py` mis à jour. La clé `msaa` de `reglages.json` ne change pas.
- **Course après une porte (#107, D-208)** : **mesure sur le vrai moteur** (sauvegarde 1, porte de l'église, direction tenue) : fondu de sortie = drapeaux `0x3d` (fondu + joueur verrouillé), chargement `0x3c`, fondu d'arrivée = `0x39` pendant 30 images alors que le héros marche dès la 12e image, puis `0x38`. `Jeu._facteur_vitesse` coupait la marche accélérée pendant tout le drapeau « fondu » (1 s) : **elle ne le fait plus**, seul le verrou du joueur (bit 4) la coupe. Le fondu d'arrivée suit donc l'accélération quand la touche est tenue (supposé acceptable ; il durait 1 s). Les fondus de combat (`Etat.transition_combat`) restent à l'horloge du jeu. Ce passage remplace, pour le fondu, la règle « facteur 1 si `Global.Flag & (1 | 4)` » de la section « Marche x1-x4 + accélérateur » plus haut. Tests : `test_priorite_jeu.py` (nouveau cas, 0x39 → accéléré ; 0x3d et 0x2d restent à 1), `test_casino_bestiaire.py`, `test_transition_combat.py`, `test_vitesse_combat.py` : OK.
- **Résolutions** : pas de changement (la liste ne propose que les tailles qui tiennent sur l'écran, `Jeu.resolutions`) ; le test « résolution enregistrée 3840 x 2160 » (#52) passe par `reglages.json`.

### Non vérifié
- La course après une porte **sous Windows** (Sylfried confirme) ; le bruitage et la durée des transitions n'ont pas été rejoués au clavier.
- #108 à #112 : en cours (voir les PR suivantes).

## Avance #114 : choix du périphérique de sortie audio (#112, 03/11/2026)

### Demande (D-207, 19 h 38)
« pouvoir changer de périphérique pour le son peut être vraiment top aussi, à rajouter tout en haut de la fenêtre pour régler les volumes ».

### Fait
- **Établi (lu dans le code de pyglet 2.1.19, non exécutable ici : Linux)** : sous Windows 8 et plus, pyglet prend d'abord le pilote XAudio2 ; `pyglet.media.devices.get_audio_device_manager().get_output_devices()` liste les sorties actives (`id`, `name`) et `get_audio_driver().set_device(device)` recrée le moteur audio sur cette sortie puis chaque lecteur en cours reprend (`Player.on_driver_reset`). Sans `set_device` (autre pilote, audio coupé), la ligne est grisée.
- **`dq4_pc/sortie_audio.py`** (logique pure, testable avec de faux pilotes) : liste des sorties gardée 1,5 s, valeurs du menu (Automatique, sorties détectées, puis la sortie enregistrée si elle n'est plus branchée, libellé « … (non branchée) »), changement, retour à Automatique (`set_device` avec `id = None` : la sortie par défaut, que le pilote suit tout seul), remise de la sortie enregistrée au lancement. Tout est dans des `try / except` : une erreur laisse le son comme il était et s'affiche dans la console.
- **Réglage** `sortie_audio` de `reglages.json` : `null` = Automatique (défaut), sinon `{id, nom}` ; une valeur illisible redevient Automatique.
- **Menu Échap > Son** : « Périphérique de sortie » tout en haut de la page (liste déroulante, bouton rond « par défaut » = Automatique) ; au changement, un bruitage d'essai est joué sur la nouvelle sortie. La page s'ouvre sur cette ligne (le test de clavier de la page Son a été recalé).
- Tests : `outils/test_sortie_audio.py` (11 tests : réglage, liste, cache, sortie non branchée, changement, erreurs, lancement), `test_pause_pages.py` (ligne en tête, grisée sans pilote capable). Démarrage de la visionneuse sous xvfb (audio « silent ») : sans erreur.

### Non vérifié (à faire par Sylfried sur Windows)
- Le changement de sortie **réel** (casque, haut-parleurs, TV) : jamais essayé ; la musique en cours doit reprendre sur la nouvelle sortie, les bruitages suivants aussi ; la sortie enregistrée doit revenir au lancement suivant.
- Le retour à « Automatique » après avoir choisi une sortie (supposé : `set_device` avec `id = None`).
- Débrancher la sortie choisie pendant le jeu : non géré (le pilote de pyglet réagit comme il le fait d'habitude) ; seul le lancement suivant retombe sur la sortie par défaut.

## Avance #115 : écran titre, logo et sous-titre deux fois plus grands (#108, 03/11/2026)

### Demande (D-209, 19 h 38)
« Peux-tu doubler la taille du logo et du sous-titre de l'écran titre ? » : **écart voulu avec l'APK** (règle habituelle : rendu le plus similaire possible).

### Fait
- **Établi** : le logo est dessiné par le moteur (maillages billboard de la carte `ev01`, paquets 21 / 22) : modèle **8901** = « DRAGON QUEST », « IV », TM et sous-titre (« L'épopée des Élus »), modèle **8900** = l'éclat animé sur le logo (agrandi avec lui).
- `avant_partie.py` : `LOGO_ECHELLE = 2.0`, `facteur_logo` (réduit le facteur si le logo agrandi dépasserait 96 % de la largeur de la fenêtre, jamais sous x1) et `agrandir_logo` (x et y agrandis autour du point fixe y = 0,70 du panneau ; profondeur des couches inchangée). `Jeu._agrandir_logo_titre` / `_maillages_combat` (`fenetre.py`) l'appliquent **seulement sur la carte du titre**.
- Variables d'essai : `DQ_LOGO_ECHELLE` (1 = le logo de l'APK) et `DQ_LOGO_Y`.
- **Mesuré sur captures** (Mesa, sans écran) à 16:9 (1280x720), 16:10 (1280x800), 4:3 (1024x768) et 21:9 (2560x1080) : largeur du lettrage = 2,00 x l'APK (± 3 %), logo dans la fenêtre et centré, bas du « IV » au moins 2 % de la hauteur au-dessus de « Touchez l'écran », même placement à tous les formats. Test : `outils/test_titre_logo.py` (12 tests, dont le rendu réel, ~2 min via `moteur_slot.sh` avec `DQ_APK`, `DQ_SAVES`, `DQ_UICACHE`).

### Supposé / non vérifié
- Supposé : « boutons » = « Touchez l'écran » (le menu de départ cache le logo) ; le dragon n'est pas recouvert dans la pose échantillonnée, l'île du château frôle le « V » sans le recouvrir.
- Non vérifié : le rendu sous Windows, les autres poses du dragon sur toute l'animation. **À confirmer par Sylfried.**

## Avance #116 : « Revenir à l'écran titre » comme dans le jeu d'origine (#109, 03/11/2026)

### Demande (D-210, 19 h 38)
« Pour le bouton pour revenir à l'écran titre actuel, reprend exactement le même fonctionnement que sa version de base, ça ouvrait un dialogue avec le texte associé et ça demandait si oui ou non on le voulait vraiment et ensuite il y avait un effet de transition, là c'est trop brut. »

### Fait
- Avant : la ligne ouvrait une page « En êtes-vous sûr ? » dessinée par la visionneuse, puis le retour au titre était brut. Maintenant la ligne **ferme le menu et fait ouvrir au moteur la boîte du jeu** (texte d'origine `0xCBA2F`, choix Oui / Non, curseur d'origine sur « Oui »), puis :
  - **Oui** : `killbank(4, false)`, déverrouillage, `Global::startTitle` avec le **fondu de 30 images** du jeu ;
  - **Non** : la boîte se ferme et le joueur est déverrouillé.
- **Établi** (lu dans le moteur, appels faits par le code d'origine du bouton des Paramètres) : `TownMenu_MESSAGE::openMessageForMENU`, `addMessage(0xCBA2F)`, `setYesNo`, `setYesNoSuperCancel(false)` ; le résultat est lu à `gTownMenu_MESSAGE + 0x10` (1 = Oui, 2 = Non, remis à 0 à l'ouverture) ; fermeture par `MenuBase::isOpen` / `close` ; verrouillage par `PlayerManager::setLock`. La boîte est une grille de 1 x 2.
- `moteur.py` : `demander_retour_titre`, `_retour_titre_avant` / `_retour_titre_apres` (autour de `GameUpdate` dans `step`), `retour_titre` (fermeture de la boîte dans le même pas). Page `titre` de `pause.py` supprimée ; ligne grisée quand la boîte n'est pas disponible (`Jeu.retour_titre_possible`).
- Test : `outils/test_retour_titre.py` (21 tests, dont le moteur réel via `moteur_slot.sh`). Correctifs de deux tests cassés par les PR précédentes : `test_lignes_inactives.py` (faux jeu sans la ligne de sortie audio de la PR #114) et son contrôle « aucun mot `triche` » (le README parlait encore d'« option de triche » depuis le renommage en « Modifications », #47 : reformulé).

### Écart avec le comportement précédent (à décider par Sylfried)
- **Établi** : la boîte d'origine est prévue **en ville et sur la carte du monde** ; en **combat, casino et bestiaire** elle ne reçoit aucune touche. La ligne est donc **grisée** dans ces cas (avant : le retour brut marchait en combat). Autre possibilité : une boîte dessinée par la visionneuse avec le même texte et le même fondu, mais ce ne serait plus « le même fonctionnement que l'APK ».

### Non vérifié
- Le rendu de la boîte et du fondu sous Windows ; le texte exact affiché (lu dans le moteur, pas vu à l'écran sur Windows). **À confirmer par Sylfried.**

## Avance #117 : la caméra suit la butte du village du prologue (#110, 03/11/2026)

### Demande (D-211, 19 h 38)
« Dans le prologue, il y a une petite butte au milieu du village, et en marchant dessus la caméra doit pouvoir un peu se surélever, là elle reste sur le même plan donc il y a encore des ajustements à faire sur la caméra. »

### Cause (établi)
- Le moteur d'origine suit la hauteur du héros à chaque pas (`TownCamera::execute` : `setTarget(joueur)` puis `calcPursue`, décalage rigide ; `SceneCamera.Update` ne lisse rien en Y). Le lissage de hauteur ajouté en #47 (pour les escaliers) retardait aussi la caméra sur les **petits** reliefs : sur la butte de `mlout1` (+0,5 u en ~8 pas), le héros montait puis redescendait à l'écran de **18 à 29 px** (à 720 p) au lieu de rester au centre.

### Fait
- `fenetre.py` : fonction `hauteur_camera` et constante `CAM_Y_RELIEF = 0,6` : **bande morte** autour de la hauteur de repos. Tant que le jeu reste à moins de 0,6 u de cette hauteur (butte, rampe douce, bosse), la caméra le suit **exactement**, comme sur mobile. Au-delà (escaliers, étages) le lissage de #47 (`CAM_Y_TAU`, `CAM_Y_MAX`) joue comme avant. La hauteur de repos est une contraction de la cible : continue, jamais plus brusque qu'avant, à la montée comme à la descente. Coupure du jeu ou caméra prise par le jeu : inchangé (hauteur du jeu aussitôt).
- **Mesuré** (rejeu de la trace du moteur réel dans `Jeu._camera_ville`) : butte de `mlout1` : héros à **0 px** de l'écart au centre (comme le mobile) contre 18 à 29 px avant. Escalier de `chf2` : retard maximal **0,95 u** (1,21 u avant, soit environ 22 % de moins), `teout5` inchangé (borne 3 u).
- Test : `outils/test_camera_ville.py` (14 tests : butte suivie exactement à toute cadence, escalier toujours lissé au-delà, invariants de la fonction, coupure).

### Écart à connaître
- Les escaliers de #47 sont un peu **moins** retardés qu'avant (la bande morte de 0,6 u est suivie exactement) ; le ressenti de l'escalier est à confirmer.

### Non vérifié
- Le ressenti sous Windows (butte du prologue, un escalier de ville, une tour). **À confirmer par Sylfried.**

## Avance #118 : fond des villes en dégradé (#111, 03/11/2026)

### Demande (D-212, 19 h 38)
« La couleur du fond de la map dans le prologue n'est également pas la bonne, il doit y avoir un dégradé comme sur le mobile, là c'est juste une couleur unie. »

### Cause (établi)
- Côté jeu, `NativeManager.cmd_back_color` (RVA 0xD14F44) lit **six** flottants (haut r, g, b ; bas r, g, b) et appelle `BackColor.SetColor(haut, bas, 0)` (0xCC43F8). `BackColor` est un quadrilatère plein écran (shader « BackColor » : `gl_Position = in_POSITION0`, couleur de sommet, file Background, ZTest Always, ZWrite Off) dont les deux sommets du haut portent la couleur du haut et ceux du bas la couleur du bas : un **dégradé vertical linéaire** sur toute l'image. La visionneuse n'en gardait que la **moyenne** (`Etat.fond`) : fond uni.
- Les deux couleurs viennent de `param_map_backcolor` (`TownDataManager::setBackcolor`) et **dépendent de l'heure du monde** : village du prologue (`mlout1`) = **aplat le jour et à l'aube**, dégradé rose-gris vers orange **le soir**, bleu nuit vers bleu plus sombre **la nuit**.

### Fait
- `moteur.py` : `Etat.fond_haut` / `fond_bas` (remis à None à chaque chargement de carte) ; `fond` (la moyenne) reste la couleur d'effacement. `fenetre.py` : `Jeu._tracer_degrade_fond` dessine le quadrilatère après l'effacement et avant la scène, **seulement pour une ville dont les deux couleurs diffèrent**. Aplat (jour, intérieurs noirs, combats, carte du monde) : inchangé au pixel près (`mlout1` de jour : 0 pixel différent). Teinte jour / nuit (`teinte_carte.py`, paquet 33) non touchée.
- Test : `outils/test_fond_degrade.py` (10 tests : décodage du paquet 8, `degrade_fond`, rendu GL d'un vrai dégradé linéaire, moteur réel `mlout1` à l'heure du soir et du jour).
- Vu sur capture (Mesa, heure du monde 1984, `mlout1`) : avant, bande unie brun-rose à droite de la carte ; après, dégradé rose-gris en haut vers orange en bas.

### À savoir (décision / confirmation par Sylfried)
- **De jour, le village du prologue a bien un fond uni dans les données du jeu** (les deux couleurs sont égales) : le dégradé n'apparaît que le **soir et la nuit**. Si le dégradé vu sur mobile était de jour, ce n'est pas cette source.
- Le changement touche **toutes les villes extérieures** le soir et la nuit (environ 98 cartes) et 7 cartes même de jour : à regarder sur Windows. La carte du monde et les cartes `ev*` n'ont pas été vérifiées.

### Non vérifié
- Le rendu sous Windows (le tampon d'image de la capture est en 5-6-5 bits : les anneaux concentriques vus sur la capture viennent de là, supposé).

## Avance #119 : logo de l'écran titre 1,5 fois plus grand au lieu de 2 (#108, 03/11/2026)

### Demande (D-215, 21 h 05)
« Finalement je veux le logo agrandit en 1,5x au lieu de 2x. » Il remplace sa demande de 19 h 38 (D-209, « doubler »). Écart voulu avec l'APK (le logo de l'APK = 1).

### Fait
- `avant_partie.py` : `LOGO_ECHELLE = 1.5` (le reste de l'agrandissement d'#115 est inchangé : point fixe y = 0,70, réduction si le logo dépasserait 96 % de la largeur, jamais sous x1). Variable d'essai `DQ_LOGO_ECHELLE` (1 = APK) toujours valable.
- `test_titre_logo.py` (12 tests) : constante 1,5 ; rapport de largeur 1,5 à ±0,05 à 16:9, 16:10, 4:3 et 21:9 ; test de réduction refait avec des largeurs de fenêtre où la réduction joue encore (0,7 à 0,9).
- **Mesuré** (rendu réel, Mesa sans écran, image 770) : les 12 tests passent, dont le rendu à 1280x720, 1280x800, 1024x768 et 2560x1080 ; capture 16:9 regardée : logo centré, « IV » au-dessus de la zone de « Touchez l'écran », dragon et île du château non recouverts.

### Non vérifié
- Le rendu sous Windows. **À confirmer par Sylfried.**

## Avance #120 : plus de choix du moniteur du plein écran ni du périphérique audio (#112, 03/11/2026)

### Demande (D-216 et D-217, 21 h 05)
Après avoir essayé #112 sous Windows (« Mon écran externe avec baffes intégrées ne coopère pas […], mais en connectant des écouteurs je n'ai pas pu changer de périphérique ») : « Supprimer les options pour choisir l'écran ou la sortie audio, il faut tout simplement que quand on active le plein écran (par les options ou via les raccourcis clavier) […] la fenêtre détecte sur quel écran il est et qu'il se mette en plein écran sur celui ci, et le son on le laisse sur le périphérique par défaut au pire ça se règle sur windows. »

### Fait
- **Sortie audio** : `dq4_pc/sortie_audio.py` et `outils/test_sortie_audio.py` supprimés (retour à l'état d'avant la PR #114 pour le code : ligne « Périphérique de sortie » de la page Son, réglage `sortie_audio`, appels dans `fenetre.py`). Le son reste sur la sortie par défaut de Windows.
- **Moniteur du plein écran** : ligne « Écran du plein écran » de la page Affichage, réglage `ecran_plein`, méthodes `valeurs_ecran`, `valeur_ecran`, `nom_ecran`, `ecran_modifiable`, `regler_ecran_plein` et paramètre `deplacer` de `regler_plein_ecran` supprimés. `ecrans.py` ne garde que la détection : `lister`, `ecran_de`, `principal` et `cible(liste, fenetre)` (l'écran de la fenêtre, à défaut le principal).
- **Le plein écran se fait toujours sur l'écran où se trouve la fenêtre** (interrupteur « Plein écran », F11, Alt + Entrée) : `Jeu._ecran_pour_plein` prend l'écran qui contient le **centre** de la fenêtre (`_indice_ecran_fenetre`, `get_location`) ; si c'est déjà l'écran de pyglet, un simple `set_fullscreen(True)` comme avant, sinon l'écran est passé explicitement. Au retour en fenêtre, la fenêtre retrouve sa place d'avant (inchangé). Détection : **établi** par test avec de faux moniteurs (fenêtre sur A, sur B, à cheval, déplacée entre deux passages) ; **jamais vu sur un vrai double écran Windows** avec cette détection seule (il avait testé le choix explicite).
- **Réglages** : `ecran_plein` et `sortie_audio` sont des clés obsolètes (`CLES_OBSOLETES`) : un ancien `reglages.json` qui les contient les ignore et les perd à la prochaine sauvegarde. Textes d'aide de « Plein écran » et de « Résolution » : « l'écran où se trouve la fenêtre ».
- Tests : `test_ecrans.py` refait (19 tests : détection, `cible`, clés obsolètes, entrée en plein écran sur l'écran de la fenêtre à chaque passage, moniteurs illisibles, échec, retour en fenêtre, page Affichage sans la ligne), `test_mode_fenetre.py` (39), `test_lignes_inactives.py` (17), `test_pause_pages.py` (28), `test_reglages_interface.py` (21) adaptés. Suite sans moteur : 47 fichiers verts sur 48 (le 48e, `test_texte_defilement`, exige `--apk` et `--saves`).

### Limites connues (à connaître)
- **Établi** : si le jeu est **lancé en plein écran** (dernier mode enregistré), la fenêtre n'existe pas encore : elle se crée sur l'écran **principal** de Windows (avant, elle allait sur le moniteur choisi). Pour jouer sur l'autre écran : fenêtre d'abord (F11 la sort du plein écran), la déplacer, puis F11.
- **Supposé / non vérifié** : le pilote audio de pyglet prend la sortie par défaut de Windows au lancement ; si on la change pendant la partie, il est possible qu'il faille relancer le jeu.
- **Non vérifié** : le plein écran sur le bon écran sous Windows avec deux moniteurs. **À confirmer par Sylfried** (issue #52, test « deux moniteurs »).

## Avance #124 : sauvegarde automatique du jeu à la fermeture de l'application (#122, 03/11/2026)

> **Remplacée par l'avance #142 (plus bas) : tout ce qui suit sur une écriture à la fermeture est retiré** (le jeu d'origine n'en fait pas), et la ligne « aucune fonction du moteur n'appelle `AutoSave` » est fausse : le moteur l'appelle lui-même, à deux endroits.

### Demande (D-218 et D-219, 22 h 34)
« Les sauvegardes auto ne fonctionnent pas, normalement je dois avoir une sauvegarde in game en fermant l'application […] (et effectivement je ne dois pas en avoir en quittant via le retour à l'écran titre, je parle bien de quand je ferme l'application). Il faut que ça marche qu'on clique sur la croix ou bien qu'on fasse Alt+F4 ou qu'on ferme depuis le gestionnaire des tâches etc (et c'est bien un système de sauvegardes in-game, je ne te demande pas de créer un système de sauvegarde à part pour ça). »

### Établi (désassemblage de `libdq4core.so` et essais sur le vrai moteur)
- La sauvegarde automatique du jeu est la **banque 4** (`data5.dat`, SAVETYPE 3), la cellule « Sauvegarde automatique » du menu de départ. Le moteur l'écrit par `AutoSave(bool)` (symbole `_Z8AutoSaveb`, 0x164aa8) : avec `true`, `savebank(4, 3)` sans condition ; avec `false`, seulement si `StageStatus::isAbortSaveDungeon()` et `isAbortSaveTown()` sont vrais (sur une carte de ville ou de donjon, il faut en plus l'indicateur de `StageStatus::setAbortSave`, qui était à zéro dans l'essai : `AutoSave(false)` a renvoyé 0 en ville).
- **Aucune fonction du moteur n'appelle `AutoSave`** : c'est le Unity d'origine (code C# non disponible ici) qui le fait, vraisemblablement à la mise en veille de l'application (**supposé**). La visionneuse ne l'appelait jamais : `Jeu.on_close` n'écrivait que les réglages et l'historique.

### Fait
- `Moteur.sauvegarde_auto()` appelle `AutoSave(true)` (0 : pas de partie en cours, 1 : écrite, -1 : refusée) ; `Moteur.sauvegarde_auto_possible()` : seulement en ville, donjon ou sur la carte du monde (`PARTIE_VILLE`, `PARTIE_CHAMP`), jamais à l'écran titre (carte `ev01`, constante `CARTE_TITRE` déplacée dans `moteur.py`), ni au menu de départ, aux logos, en combat, au casino ou dans le livre des monstres, ni pendant que la boîte « Revenir à l'écran titre » est ouverte.
- **« Revenir à l'écran titre » garde son effet** (D-184) : `retour_titre()` pose `retour_titre_fait` avant `killbank(4, false)` ; il retombe quand la carte du titre est arrivée (`step`) ou à l'application d'un état. Pendant le fondu et au titre, fermer l'application n'écrit rien : la banque 4 reste effacée.
- `Jeu._sauvegarde_fermeture(motif)` : une seule fois, dite dans la console (« Sauvegarde automatique écrite (fermeture de la fenêtre). »), jamais d'erreur ; rien pour les captures de test (`--shot`, sauf `DQ_SAUVEGARDE_FERMETURE=1`). Appelée au début de `on_close`, avant les réglages et l'arrêt du son.
- **Chemins de fermeture couverts** : croix et Alt + F4 (message `WM_CLOSE` → `on_close`) ; **menu Échap > Quitter > Oui** (`Jeu.quitter` fermait la fenêtre sans passer par `on_close` : ni sauvegarde ni réglages, corrigé) ; « Fin de tâche » de l'onglet Applications du gestionnaire des tâches (envoie `WM_CLOSE` aux fenêtres : **supposé**, non vérifié) ; fermeture de la fenêtre de console, Ctrl + C, Ctrl + Pause, fermeture de session et arrêt (`SetConsoleCtrlHandler` : le gestionnaire, appelé dans un autre fil, demande la fermeture à la boucle principale — Unicorn n'est utilisé que par elle — et attend au plus 4,5 s, Windows arrêtant le processus après 5 s) ; fin de session des fenêtres (`WM_ENDSESSION`). Sous Linux (essais) : SIGTERM et SIGHUP.
- **Limite établie** : un processus arrêté de force (`TerminateProcess` : « Fin de tâche » de l'onglet Détails, `taskkill /F`, coupure de courant) ne laisse aucune chance d'écrire quoi que ce soit. Aucune sauvegarde périodique n'a été ajoutée (non demandée).
- Tests : `outils/test_sauvegarde_fermeture.py` (30 tests) : quand sauvegarder, `AutoSave(true)` appelé, une seule écriture, message, erreur sans arrêt de la fermeture, ordre de `on_close`, menu Quitter, demande depuis un autre fil (console), signal SIGTERM, `WM_ENDSESSION` ; **sur le vrai moteur** : `data5.dat` écrit (15 360 octets) dans le dossier d'écriture, relu par le moteur (`loadbank(4)` : on retrouve la carte de la partie fermée alors que le journal 2 était chargé entre-temps), retour au titre : banque effacée et rien n'est réécrit ni pendant le fondu ni au titre. Essais de bout en bout de la visionneuse sous Xvfb : fermeture normale (`on_close`) et SIGTERM écrivent `data5.dat` et `data9.dat`.

### Non vérifié
- **Tout sous Windows** : la croix, Alt + F4, le menu Quitter, la fin de tâche, la console. **À confirmer par Sylfried.**
- Ce que fait exactement le Unity d'origine (moment, `AutoSave(true)` ou `(false)`), faute du code C#.
- Une fermeture en pleine animation ou en plein événement : la sauvegarde est celle du moteur à cet instant (comme `AutoSave(true)` d'origine) ; non essayé sur un cas précis.

## Avance #125 : l'erreur d'un passage plein écran ↔ fenêtre qui échoue est notée en entier (#123, 03/11/2026)

### Demande (D-218, 22 h 34)
« Je ne peux plus mettre le jeu en mode fenêtré j'ai un message m'indiquant que c'est impossible, et en faisant ça en plus mon écran clignote. » Son `reglages.json` dit `mode_fenetre` = 1 : le jeu se lance en plein écran, et la sortie du plein écran (« Fenêtre impossible ») échoue.

### Établi
- Le code de bascule (`regler_plein_ecran`, `_poser_plein_ecran`, `_mettre_plein`) n'a **pas été modifié par la PR #120** ; seul `_creer_plein_ecran` ne choisit plus l'écran (création sur l'écran principal, comme avant quand aucun choix n'était fait). Je n'ai trouvé aucune erreur évidente en relisant ce code ni celui de pyglet 2.1.19 (`Win32Window._create`, `set_fullscreen`).
- La console ne disait que « Fenêtre impossible (%r) » : le texte de l'exception, pas l'endroit où elle a eu lieu.

### Fait (diagnostic seulement)
- `Jeu._noter_echec_bascule(cible, erreur)` : à chaque échec d'un passage plein écran ↔ fenêtre, **la pile d'appels complète** de l'erreur (et, si le retour à l'état de départ échoue aussi, cette seconde erreur en note), l'état de la fenêtre (plein écran, taille, taille mémorisée, place d'avant, bureau), l'écran de la fenêtre pour pyglet, les moniteurs détectés (taille, position, principal), les versions de pyglet et de Python, dans la console **et** dans `dq4_pc/erreurs_fenetre.log` (à la suite des précédentes ; ignoré par git comme tous les `*.log` ; `DQ_JOURNAL_FENETRE` : un autre fichier). Jamais d'erreur levée par le journal.
- Tests : `test_mode_fenetre.py` (42 tests dont 3 nouveaux : l'entrée du journal, un journal inécrivable, aucune entrée sans échec ; les échecs simulés écrivent dans un fichier temporaire).

### Non vérifié
- La cause du défaut : **inconnue** tant que l'erreur n'a pas été lue sur le PC de Sylfried (il doit refaire l'essai : lancer en plein écran, puis F11).

## Avance #132 : plein écran → fenêtre après le branchement d'un écran externe (#126, 03/11/2026)

### Demande (D-220, 23 h 08)
Le jeu est en plein écran, il branche un écran externe, le passage en fenêtre échoue ; après un relancement tout va bien, et en faisant glisser la fenêtre sur l'autre écran le plein écran marche (avec quelques scintillements au retour du plein écran sur l'autre moniteur). Son journal (`erreurs_fenetre.log`, PR #125) est joint.

### Établi (lu dans son journal)
- `OSError: [WinError -2147024890] Descripteur non valide` dans `Win32Window._create` → `Screen.get_dpi` → `GetDpiForMonitor`, pyglet 2.1.19, Python 3.14.8, Windows ; ses moniteurs : 1920 x 1200 en (0, 0) (principal) et 2560 x 1440 en (-331, -1440).
- pyglet garde pour la fenêtre un objet moniteur (`_screen`) qui porte la poignée Windows (HMONITOR) du moment de la création. Après le branchement d'un écran, Windows peut attribuer d'autres poignées : `set_fullscreen(False)` recrée la fenêtre avec cette poignée périmée et échoue ; le retour à l'état de départ réutilise la même poignée et échoue aussi (« Retour à l'état de départ impossible aussi » dans son journal), d'où « plein écran conservé » et le clignotement.
- Le plein écran vers un moniteur passé à `set_fullscreen(True, screen=…)` vient d'une lecture neuve de la liste : il marche, ce qu'il constate.

### Fait
- `Jeu._rafraichir_ecran()` : relit les moniteurs (`display.get_screens()`, objets neufs) et remplace `_screen` par celui de **mêmes position et dimensions** que l'ancien, sinon celui où se trouve la fenêtre, sinon le principal. Appelée au début de `_poser_plein_ecran`, avant que le moniteur de départ soit retenu (le retour à l'état de départ en profite aussi), dans les deux sens (plein écran → fenêtre, fenêtre → plein écran sans moniteur imposé). Ne lève jamais d'erreur (une relecture impossible laisse l'ancien moniteur).
- Tests : `test_mode_fenetre.py` (48 tests dont 6 nouveaux : un faux moniteur périmé qui lève la même erreur que Windows ; plein écran → fenêtre, fenêtre → plein écran, retour à l'état de départ, moniteur débranché, relecture impossible). Les 4 tests de comportement échouent avec l'ancien comportement (vérifié en neutralisant la méthode).

### Non vérifié
- **Sous Windows avec un vrai branchement d'écran** : à confirmer par Sylfried (plein écran, brancher l'écran externe, repasser en fenêtre ; idem après débranchement).
- Le scintillement au retour du plein écran sur l'autre moniteur (non demandé, non traité ; le plein écran recrée la fenêtre, ce que pyglet fait à chaque changement de moniteur).

## Avance #133 : la course agit dès que le héros est libre au retour d'un combat (#127, 03/11/2026)

### Demande (D-221, 23 h 14)
« J'ai trouvé le même problème sur la touche pour courir qui ne fonctionne pas tout de suite en sortant d'un combat […] analyse partout où ce problème pourrait se trouver et règle le. » (Le problème de #107 : la course n'agissait qu'une seconde après l'arrivée sur une carte.)

### Établi (mesure sur le vrai moteur : combat forcé sur la carte du monde, direction tenue dès la fin du combat)
- Après la sortie de la partie combat, le fondu de retour dure 30 images. Global.Flag : 0x1 à l'image 0, 0x2d (joueur verrouillé, bit 4) des images 1 à 11, 0x29 dès l'image 12 (joueur libre), 0x28 à l'image 30. Le héros bouge dès l'image 13.
- `Jeu._facteur_vitesse` rendait 1.0 tant que `Etat.transition_combat()` était vrai (images 0 à 29) : environ 0,6 s sans marche accélérée ni accélérateur, malgré la touche tenue.

### Fait
- `_facteur_vitesse` : la ligne `transition_combat()` est remplacée par `Etat.garde_trans > 0` (les 1 à 3 images où le moteur change de scène entre deux fondus, joueur ni verrouillé ni libre) ; seul le verrou du joueur (Global.Flag 4) coupe ensuite l'accélération, comme pour #107.
- **Recherche des autres endroits** où l'accélération est coupée : `Etat.effet` (cascade d'entrée en combat), `attente_charge` (écran noir qui attend la scène d'un combat), `_horloge_combat`, parties de combat et mini-jeux, messages, menus du jeu, verrou du joueur : tous légitimes (le jeu a la main, ou c'est un combat). Aucun autre fondu de carte ne coupe l'accélération depuis #107. Non cherché : un cas où le verrou du joueur lui-même resterait levé trop longtemps (c'est le moteur qui décide).
- Tests : `test_priorite_jeu.py` (retour de combat joueur libre ou verrouillé, entre deux fondus) et `test_transition_combat.py` (rejeu d'un vrai combat sur le vrai moteur : le facteur de chaque pas du retour est comparé aux vrais drapeaux).

### Non vérifié
- **Sous Windows** : à confirmer par Sylfried (tenir la course en sortant d'un combat : elle agit dès que le héros bouge).
- Avec la course tenue, le fondu de retour (en images du moteur) passe plus vite en temps réel, comme le fondu d'arrivée sur une carte depuis #107 : c'est la conséquence voulue d'une horloge plus rapide dès que le joueur est libre.

## Avance #142 : la sauvegarde automatique est celle du jeu (#128, 03/11/2026)

### Demande (D-220, 23 h 08)
« La sauvegarde auto n'a pas le même comportement que le jeu, ça ne doit pas me remettre au pixel près où j'étais, mais je crois que c'est à l'endroit d'où je viens : sur mobile en quittant le jeu dans une grotte la sauvegarde auto m'a ramené sur la map globale pile au niveau de l'entrée de la grotte, et dans un village à l'entrée du village, toujours sur la map globale, donc regarde dans le code source comment c'est fait. »

### Établi
- **`AutoSave` n'a que deux appelants dans `libdq4core.so`**, par le même raccourci (stub PLT 0x226290) : `TownPart::initialize` (appel en 0x19f988, à l'arrivée dans une ville ou un donjon) et `FieldPart::initialize` (0x19fa70, à l'arrivée sur la carte du monde). Les deux appellent `AutoSave(false)` : le moteur n'écrit alors que si les conditions de `StageStatus` (`isAbortSaveTown`, `isAbortSaveDungeon`, indicateur d'abandon de sauvegarde permis) sont réunies. La note de l'avance #124 (« aucune fonction du moteur n'appelle `AutoSave` ») était fausse : la recherche n'avait porté que sur les appels directs au symbole.
- Le code C# du cycle de vie de l'application (`OnApplicationPause`, `OnApplicationQuit`) n'appelle que `Sound$$SystemPause` et `Sound$$SystemQuit` : **le jeu d'origine n'écrit rien à la fermeture**.
- Mesuré sur le vrai moteur (échantillon de sauvegardes de la session, banque 4 = `data5.dat`, 15 360 octets) : charger le journal 1 (ville `mak1f1`) n'écrit pas `data5.dat` ; charger la sauvegarde 4 (carte du monde) l'écrit, sans aucun appel de la visionneuse ; `Global::startTown('dab1')` (donjon) depuis la carte du monde la réécrit ; `Global::startField()` aussi.
- Ce que fait le jeu en pratique : la sauvegarde automatique est celle de la **dernière arrivée** sur la carte du monde (ou dans un donjon selon ses conditions), donc « l'endroit d'où l'on vient », pas la position exacte quand on ferme : c'est ce qu'a vu Sylfried sur mobile.

### Fait
- Retiré de `moteur.py` : `Moteur.sauvegarde_auto`, `Moteur.sauvegarde_auto_possible`, `retour_titre_fait`. Retiré de `fenetre.py` : `Jeu._sauvegarde_fermeture`, les gestionnaires de la console de Windows, des signaux et du message `WM_ENDSESSION`, la demande de fermeture venue d'un autre fil dans `_boucle`, `DQ_SAUVEGARDE_FERMETURE`.
- Gardé : `Jeu.quitter` passe par `on_close` (réglages, historique, son) ; « Revenir à l'écran titre » efface toujours la banque 4 (`killbank(4, 0)`, D-184) ; rien ne la remet (le moteur ne l'écrit pas au titre).
- Conséquence assumée : sans les gestionnaires de la console, Ctrl + C et la fermeture de la console de Windows arrêtent le jeu sans passer par `on_close` (réglages et historique de la séance non enregistrés), comme avant #124. La croix, Alt + F4 et le menu Quitter les enregistrent.
- Tests : `outils/test_sauvegarde_auto.py` (12 tests ; remplace `test_sauvegarde_fermeture.py`) : plus rien de forcé dans `Moteur` et `Jeu` ; `on_close` ne touche pas au moteur ; **sur le vrai moteur** : l'arrivée en ville n'écrit pas la banque 4, l'arrivée sur la carte du monde l'écrit seul, fermer la fenêtre ne modifie aucun fichier de sauvegarde, « Revenir à l'écran titre » l'efface et rien ne la remet.

### Non vérifié
- **Sous Windows** : à confirmer par Sylfried (fermer dans une grotte, puis « Sauvegarde automatique » au menu de départ).
- **Où le menu de départ replace le joueur** après une sauvegarde automatique prise dans un donjon (carte du monde à l'entrée, comme sur mobile, ou dans le donjon). Le chargement brut de la banque écrite à l'entrée du donjon (`loadbank(4)`) reprend dans le donjon (`dab1`) ; le chemin du menu de départ du jeu n'a pas été rejoué. Dans les deux cas c'est le code du moteur, que la visionneuse ne modifie pas.
- Ce que le jeu fait exactement des conditions `StageStatus` (quand `isAbortSaveDungeon` est vrai) : mesuré seulement sur `dab1` dans l'échantillon.

## Avance #143 : le petit rappel du bas de l'écran est retiré (#129, 03/11/2026)

### Demande (D-220, 23 h 08)
« Supprime le petit message en bas à gauche "Échap pour le menu, F1 pour les infos" ou un truc du genre. »

### Fait
- Retiré de `fenetre.py` : l'étiquette `etiq_conseil`, `Jeu._texte_conseil` et le dessin qui l'affichait 8 secondes après le démarrage (hors menu Échap, hors infos F1, hors captures). `t_demarrage` reste (mesures de temps réel). Le menu Échap et la touche F1 ne changent pas.
- Test : `outils/test_sans_rappel_demarrage.py` (2 tests).

### Non vérifié
- **Sous Windows** : à confirmer par Sylfried (aucun texte en bas à gauche au démarrage).

## Avance #144 : à l'atterrissage sur la carte du monde, le héros est devant ses équipiers (#135, 03/11/2026)

### Demande (D-223, 23 h 27)
« Lors de l'utilisation d'une aile de chimère (donc lors du sort téléportation et autre aussi je suppose) j'ai trouvé un léger bug, une fois atterri Doc s'est retrouvé devant Ragnar alors que l'alignement doit être reproduit lorsqu'on atterrit, donc pareil regarde comment c'est fait dans le code source et reproduis-le à l'identique. »

### Établi (désassemblage de `libdq4core.so` et mesure sur le vrai moteur, enquête confiée à un sous-agent puis rejouée par moi)
- **Le moteur place le groupe correctement** : à l'arrivée sur la carte du monde il empile les membres sur un seul point (mesuré : héros et Doc à (2495,967 ; 391,967 ; z 200) à l'arrêt après la descente, 765 images dans cet état), puis ils se séparent en marchant. Aucune étape native d'alignement (`setFormation`, `setAllPotition`, `setPartyToFirst`, `setStartPosition`) n'est passée pendant le sort Téléportation ni à l'arrivée.
- **Le défaut était dans l'ordre de dessin de la visionneuse** : les sprites à plat de la carte du monde étaient superposés par `sorted((z, y, emplacement))`, le plus grand rang devant : à position égale, le plus grand emplacement (Doc, 1) passait devant le héros (0). Le jeu fait l'inverse : `FieldPartyDraw::draw` (0x1ec5a8) trie les membres par profondeur décroissante (tri par sélection, à égalité l'emplacement le plus bas garde la tête) puis appelle `SpriteCharacter::setDepth` avec 10, 9, 8… dans cet ordre : à profondeur égale, le héros est devant. La profondeur vient de `FieldPlayerManager::draw` (0x1f0a14), qui passe `FieldStage::calcDrawPosition(position).z` à `FieldPartyDraw::setDepth`.

### Fait
- `rang_profondeur_champ(sprites)` (`fenetre.py`) remplace le tri en ligne. Clé : (hauteur z, plus au sud, puis `-emplacement` pour les membres du groupe, `emplacement` pour les véhicules). Hauteur et « plus au sud » priment toujours ; seul l'ex æquo change. Les véhicules (emplacements ≥ 10) gardent « le plus récent devant ».
- Test : `outils/test_ordre_groupe_champ.py` (7 tests : 6 sans moteur, 1 sur le vrai moteur : sortie de l'église, sort Téléportation depuis `maout` vers la carte du monde, descente de 23 images puis arrêt empilé : le héros reste devant Doc).

### Non vérifié
- **Sous Windows** : à confirmer par Sylfried (aile de chimère, Téléportation, Zoom : le héros est devant ses équipiers à l'atterrissage).
- Le sens « rang plus grand = devant » du tracé à plat est lu dans le code (hauteur 0,04 + rang × 0,0005, caméra de dessus, `GL_LESS`), pas vérifié par une capture GL ; de même `SpriteCharacter::setDepth` plus grand = devant n'est pas vérifié dans le code Unity.
- L'objet « Aile de chimère » lui-même n'a pas été essayé, seulement le sort Téléportation (même chemin natif `ruraUp` / `ruraDown` / `startField`, non vérifié identique).
- Atterrissage dans une ville ou un donjon : le moteur y empile aussi le groupe, mais le dessin des villes (panneaux par emplacement) n'a pas été mesuré ; si le défaut y persiste, regarder l'échelle `ech` et la profondeur du panneau entre les emplacements 0 et 1.

## Avance #147 : fenêtre Interface, un clic simple attend le délai du double clic (#145, 03/11/2026)

### Demande (D-225, 23 h 45)
« La fenêtre interface, il faut qu'elle attende de savoir si je fais un double clic avant qu'elle se ferme car elle doit se replier ou se déplier uniquement via un seul clic mais du coup via un double clic elle change 2 fois d'état c'est perturbant. »

### Établi
- Avant : le panneau de l'éditeur d'interface (`pause.py`, barre de titre) se repliait dès le relâchement d'un appui court ; le second appui d'un double clic (dans `DELAI_DOUBLE_CLIC` = 0,40 s) remettait le panneau à sa place mais, le premier clic ayant déjà plié, l'état changeait deux fois à l'écran.

### Fait
- Un appui court seul arme un pliage (`pan_plier_a` = relâchement + `DELAI_DOUBLE_CLIC`) que `Pause.maj` exécute une fois le délai écoulé sans second appui (`_plier_en_attente`). Un double clic annule le pliage en attente et remet seulement le panneau à sa place : aucun changement d'état. Un clic suivi tout de suite d'un glisser plie d'abord (comme avant) puis le panneau suit le pointeur. Tab reste immédiat et annule un pliage en attente ; la fermeture de l'éditeur ou du menu l'annule aussi.
- Tests : `outils/test_panneau_interface.py` (14 tests, dont : un clic simple ne change l'état qu'une fois, après le délai ; un double clic ne le change jamais, replié ou déplié ; troisième clic après un double clic ; clic puis glisser).

### Non vérifié
- **Sous Windows** : à confirmer par Sylfried (le délai de 0,40 s peut être changé par `DQ_DOUBLE_CLIC`).
- Le délai est celui de la visionneuse, pas le délai de double clic du système Windows.

## Avance #148 : le « ; » des noms d'objets n'apparaît plus dans l'historique des dialogues (#139, 03/11/2026)

### Demande (D-224, 23 h 37)
« Supprime les ";" de l'affichage des dialogues dans l'historique, c'est un caractère spécial qui ne doit pas être lu […] enfin affiché. »

### Établi (relevé dans les banques de textes du patch, `assets/msg/en/*.mpt` du paquet de données)
- Le « ; » vient des **noms d'objets** du patch (« bâton de ;cyprès », « épée de ;cuivre », « herbe ;médicinale »…) : 407 des 408 occurrences relevées sont **juste après une espace et avant une lettre** (302 dans `b1000000.mpt`, 87 dans `b1002000.mpt`, quelques-unes dans `b1003000`, `b1004000`, `b1005000`). Aucun « ; » de ponctuation française (espace avant **et** après) n'a été trouvé dans ces textes. Le moteur remet le nom tel quel dans le message (« Ragnar obtient l'herbe ;médicinale. »), le « ; » est donc dans le tampon que le crochet de l'historique lit.
- **Supposé** : c'est un point de coupure possible pour le nom dans une fenêtre étroite (comme le « $ » des noms dans le projet de traduction) ; ce que fait exactement le jeu de ce caractère à l'écran n'a pas été regardé ici.

### Fait
- `historique.sans_marques` retire tous les « ; » ; appelée par `nettoyer` (texte de chaque dialogue), pour le nom du locuteur, et à la relecture d'un favori déjà enregistré avec un « ; » (il reste reconnu : l'identité d'un favori est son contenu). L'espace qui précède reste : « l'herbe médicinale ».
- Test : `outils/test_historique_messages.py` (100 tests, dont `test_point_virgule_du_patch_retire`).

### Non vérifié
- **Sous Windows** : à confirmer par Sylfried (les dialogues avec un nom d'objet n'affichent plus de « ; »).
- Les textes du patch ont été relevés dans le paquet de données ; je n'ai pas rejoué chaque dialogue du jeu.

## Avance #149 : le message de la liste vide de l'historique tient dans son cadre (#140, 03/11/2026)

### Demande (D-224, 23 h 38)
« Le texte en fond dans la fenêtre d'historique dépasse de l'encadrement quand on filtre sur tous les favoris et qu'on n'en a pas. »

### Établi (reproduit hors moteur avec le vrai code de dessin, `ui_historique.py`, fenêtre de 900 x 720)
- Avec « Favoris seulement » coché et aucun favori, la liste est vide et le message « Aucun dialogue en favori : décoche « Favoris seulement », choisis un dialogue et appuie sur Entrée (ou clique son étoile) pour le garder. » était dessiné **sur une seule ligne**, centrée : bien plus large que la fenêtre, il sortait du cadre des deux côtés (même chose pour « Aucun combat en favori… »). Les messages sans favori coché (« Aucun dialogue pour l'instant. ») sont courts et tenaient.

### Fait
- `ui_historique.couper_mots(texte, largeur, larg_max)` coupe le message aux espaces ; le dessin de la liste vide l'appelle avec la largeur de la fenêtre moins 2 x 20 unités, puis centre chaque ligne, le bloc étant centré verticalement dans la liste. Un mot plus large que la limite resterait seul sur sa ligne (il ne peut pas être coupé).
- Capture après correction (900 x 720) : 3 lignes centrées dans le cadre.
- Test : `outils/test_historique_messages.py` (105 tests, dont la classe `TestMessageVide`).

### Non vérifié
- **Sous Windows** : à confirmer par Sylfried (fenêtre d'historique, case « Favoris seulement » cochée, aucun favori, onglets Dialogues puis Combats).
- Fenêtre très étroite : testée seulement à 900 x 720 et 1280 x 720 (hors moteur).

## Avance #150 : un sort de soin sans effet ne joue plus son bruitage de soin (#137, 03/11/2026)

### Demande (D-224, 23 h 35)
« Ça affiche bien qu'il ne se passe rien mais il y a encore les 2 bruitages qui sont joués, le premier qui est similaire à tous les sorts qui indique qu'un sort a été lancé, et le 2ème qui dépend du sort […] il faut donc garder le premier bruitage dans tous les cas mais pas le 2ème si le sort échoue mais le garder si le sort fait véritablement quelque chose. »

### Établi (mesuré au moteur réel : crochet sur `SoundManager::playSe`, sauvegarde 1 du mobile, Doc lance ses sorts sur Ragnar)
| cas | bruitages (id, adresse de retour dans `menuUpdate`) avant le correctif |
|---|---|
| Premiers secours, PV pleins | 306 (`menuUpdate` + 0x548), 501 (`menuUpdate` + 0x114) |
| Premiers secours, Ragnar blessé | 306, 501 (+ 0xFC), 501 (+ 0x114) |
| Multisoin, PV pleins | 306 (`useMagicNoTarget`) seulement |
| Multisoin, un blessé | 306, 501, 501 |
- **Le « premier bruitage »** est le **306**, joué par `TownMenu_MAGIC_CHARSELECT::menuUpdate` (et `useMagicNoTarget` pour un sort de groupe) au lancement, le même pour tous les sorts : gardé dans tous les cas.
- **Le « 2ᵉ »** est le **501**, joué à l'étape du message de résultat par `menuUpdate` (+ 0xFC si le sort a servi, hors Antipoison ; + 0x114 pour les actions 196 à 198, **sans regarder si le soin a servi** : c'est la cause). Pour Premiers secours, Soins partiels et Soins complets à PV pleins, il restait donc un 501 alors que le message dit « Mais il ne se passe rien. ». Pour un sort de groupe sans effet, la règle de l'avance #47 (boucle des cibles vidée) coupe déjà ce bruitage : rien à changer.

### Fait
- `Moteur._crochets_magie` : quand la règle « sort sans effet » remplace le résultat d'un sort sur une cible, un crochet placé avant l'instruction `sub w8, w8, #0xc4` de `menuUpdate` (+ 0x100) met le numéro d'action à une valeur hors de 196 à 198 : la comparaison suivante saute l'appel du bruitage de soin. Le crochet ne sert qu'une fois (le drapeau est remis à zéro) et seulement si l'instruction attendue est bien là (sinon message dans la console, bruitage gardé).
- Tests (moteur réel, `outils/test_magie_liste.py`, 33 tests dont 5 nouveaux) : les 3 soins à PV pleins ne jouent que le 306 ; les 3 soins utiles jouent 306, 501, 501 comme avant ; Multisoin en pleine forme : 306 seul, avec un blessé : 306, 501, 501 ; un soin utile après un soin inutile rejoue son bruitage.

### Non vérifié
- **Sous Windows** : à confirmer par Sylfried à l'oreille (Premiers secours sur un personnage aux PV pleins : un seul son ; sur un blessé : comme avant). Je n'ai mesuré que les appels du moteur, pas l'audio.
- Les autres sorts hors combat qui échouent avec le propre message d'échec du jeu (Rappel sur un vivant, Antipoison sans poison, Sifflet) ne jouent que le bruitage de lancement d'après leurs appels, sans changement de ma part : non rejoués un par un ici.

## Avance #151 : l'écran « Pause » devient « Paramètres » et ne met plus le jeu en pause (#136, 03/11/2026)

### Demande (D-224, 23 h 32)
« L'écran pause doit désormais s'appeler [ne plus s'appeler] "Pause" mais "Paramètres", et il ne doit plus mettre le jeu en pause. » (lecture retenue : titre « Paramètres » ; le jeu continue derrière lui. Le « ne… plus » manquait dans le message : à confirmer.)

### Établi (vrai moteur, sauvegarde 5, carte du monde)
- Avant : `Jeu._boucle` s'arrêtait dès que le menu était ouvert (`if self.pause.ouvert: … return`) et `pause_jeu(True)` mettait le son en pause.
- Mesure après correctif (pas du moteur à l'image de boucle donnée) : menu fermé 71 → menu ouvert (Échap à l'image 400) 83 puis 87 sur la page Historique, **puis 87 sans changement** : le moteur tourne à ~30 pas par seconde sur la racine et les pages de réglages, et s'arrête sur l'Historique.

### Fait
- Le titre de la racine est « Paramètres » (`Pause.dessiner`). Les libellés internes, les noms de modules et les anciennes sections de ces notes gardent « Pause » (historique daté).
- **Le jeu tourne derrière le menu, sans aucune entrée** : `Jeu.tick` envoie (0, 0) au moteur quand le menu est ouvert (les touches du menu, Z Q S D et flèches comprises, ne font pas marcher le héros ; un clic ne va pas au jeu) ; `_facteur_vitesse` rend 1,0 menu ouvert (pas de marche accélérée) ; le son continue (`pause_jeu` ne le coupe plus).
- **Deux pages arrêtent le jeu** (`Pause.PAGES_FIGEES`) : l'**Historique** (lecture d'un combat qui avance tout seul en vitesse rapide) et la question **Quitter**. `Jeu._synchroniser_gel` coupe / rend le son et remet l'horloge à zéro (pas de rattrapage) quand on entre / sort de ces pages. Choix du portage, pas demandé tel quel : à confirmer. **Remplacé en #179 : aucune page ne fige plus le jeu (D-229).**
- README : « menu Paramètres (Échap) ».
- Tests : `outils/test_parametres_sans_pause.py` (13 tests : titre, pages figées, arrêt et reprise du son, aucune entrée envoyée, pas de marche accélérée, boucle).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (menu Échap ouvert : le jeu continue derrière, le héros ne bouge pas quand on navigue au clavier).
- **En combat**, le combat continue aussi derrière le menu (en vitesse rapide, les messages avancent seuls) : c'est la conséquence directe de « ne plus mettre le jeu en pause » ; à dire si tu veux garder le jeu arrêté en combat.
- Le bouton « Reprendre » de la racine garde son nom (il ferme le menu) : peut-être « Fermer » ? Non demandé.
- Je n'ai pas comparé avec le comportement de la fenêtre « Paramètres » d'origine du mobile (le jeu y est-il arrêté ?) : non vérifié.

## Avance #152 : historique des combats complet (#141, 04/11/2026)

### Demande (D-224, 03/11 23 h 40)
« Pour l'historique des combats, je t'autorise à agrandir en hauteur la taille des boîtes de dialogue pour tout contenir sachant qu'il faut comme information : quel monstre a fui, quel monstre a disparu, quel monstre est mort, quels étaient les monstres, si on a fui, si on a perdu, si on a gagné, l'expérience totale gagnée, l'or total gagné et les objets obtenus à la fin du combat. »

### Établi (lecture du moteur désassemblé, puis mesure sur le vrai moteur)
- **Monstre qui s'enfuit / qui disparaît** : `BattleActorManager2::checkDeathMonster()` (0x1ff570) passe en revue, à chaque image, les monstres « morts » (`HaveStatusInfo::isDeath`) pas encore traités (masque `+0xd30`) : si `isEscapeFlag` (bit 4 de `+0x424`) il incrémente `+0x7d24` (fuites), sinon si `isDisappearFlag` (bit 5) `+0x7d28` (disparitions), sinon il appelle `execMonsterDeath` (+0x7d20, morts). Deux crochets au milieu de la fonction, sur ces deux incrémentations (`+0x98` et `+0xc0`, instruction vérifiée avant installation), donnent l'indice du monstre (`w20`, le même indice que pour `execMonsterDeath`). **Mesuré** : combat réel Londuleux ×2 + Gluant ×1, le jeu écrit « Le gluant s'enfuit ! » et le crochet note le Gluant enfui ; Londuleux ×4 avec un monstre enfui et un disparu forcés dans la mémoire : 2 vaincus, 1 enfui, 1 disparu.
- **Objets gagnés** : après la victoire, `BattleExecVictory32::setup()` (0x203c6c) appelle `PartyStatus::giveItem(objet = tâche + 0xc)` : il renvoie l'indice du membre qui le prend, ou **-1 quand l'objet va dans le sac** (mesuré : « Il contient un arc de chasseur ! » puis « Ragnar met l'arc de chasseur dans le sac. » avec -1 ; l'objet est obtenu dans les deux cas, d'où l'absence de distinction). Crochet juste après l'appel (`+0x28`, `cmn w0, #1`). `MonsterParty::checkDropItem(i)` (appelée à la mort d'un monstre) écrit le butin dans `g_Monster + 0x3eac` (+ `0x3eb0` : monstre qui l'a laissé) ; un seul objet par combat (champ unique) : le crochet note pourtant chaque appel de la tâche.
- **Nom d'un objet / d'un monstre** : `TextAPI::extractText(tampon, genre | numéro)` (0x17f750), ce que le jeu appelle pour ses macros de nom : genre `0x4000000` = objet (« bâton de ;cyprès »), `0x6000000` = monstre (« londuleux », « armure ;errante », « scara$somniaque »). Appel fait **entre deux images** (dans `CapteurCombat.maj`, jamais dans un crochet), nom gardé ; « ; » retiré, « $ » → « - ». Les noms de monstres viennent toujours des plaques (casse exacte) ; **nouveau** : sans plaque (attaque surprise ; plaques d'un autre nombre de groupes), le nom est demandé au moteur par le numéro, avec une majuscule (avant : « Monstre »).
- Constat au passage : les monstres peuvent s'enfuir en plein combat (le test réel `test_victoire_deux_especes` supposait que tous étaient vaincus : il ne tenait que par chance ; il compte maintenant vaincus + enfuis + disparus et compare les fuites au message « s'enfuit » du jeu).

### Fait
- `historique_combat.py` : `Suivi` note le sort de chaque monstre (`vaincu` / `fui` / `disparu`, un seul), les objets ; `ennemis()` rend `{nom, total, vaincus, fuis, disparus}` ; `fabriquer_combat` ajoute `objets: [{nom}]` (victoire seulement) ; trois crochets internes (`CROCHETS_INTERNES`, instruction vérifiée : sur un moteur différent seul cet événement est perdu) ; noms d'objets et de monstres demandés au moteur.
- `historique.py` : `Element.objets`, `ligne_espece` (« Gluant ×3 : 1 vaincu, 1 enfui, 1 disparu » ; « Golem : resté » ; tous vaincus : « Gluant ×3 »), `lignes_combat` (une ligne par espèce, puis « Or : N     Expérience : N », puis « Objets : a, b »), validation `ennemis_valides` / `objets_valides` ; **les favoris d'avant (sans `fuis`, `disparus`, `objets`) sont relus tels quels** (0 et liste vide).
- `ui_historique.py` : une boîte de combat a autant de lignes que son texte (entête comprise), 3 au moins, **12 au plus** (`MAX_LIGNES_COMBAT`), puis une boîte suivante (« 2/2 ») ; le cadre du jeu (frameData 192, 9 morceaux, coins de 12 unités) est **étiré** par `etirer_cadre` (les sommets de la moitié haute montent, les coins gardent leur taille, le bas ne bouge pas) ; `disposer` accepte une hauteur par boîte. Les dialogues gardent la boîte de 3 lignes.
- Tests : `test_historique_combat.py` (71 : crochets, sorts, objets, noms demandés au moteur, moteur inattendu, vrai moteur avec fuite / disparition / objet) et `test_historique_messages.py` (112 : hauteur des boîtes, cadre étiré avec la vraie mise en page, favoris complets et ancien format).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (boîtes de combat plus hautes, cadre bien étiré ; un combat réel avec un monstre qui s'enfuit ; un objet gagné).
- **Non vérifié** : un monstre qui « disparaît » dans un vrai combat (vérifié seulement par un état forcé dans la mémoire, pas par un monstre qui disparaît de lui-même) ; le comportement du jeu quand le sac est plein (les objets restent listés) ; si le groupe a fui alors que **tous** les monstres avaient déjà fui ou disparu (l'issue resterait « Fuite »).
- Un monstre « resté » = ni vaincu, ni enfui, ni disparu quand le combat se termine (fuite ou défaite du groupe) : c'est une déduction (le moteur ne le dit pas).
- En défaite, comme en fuite, le jeu ne verse ni or, ni expérience, ni objets : rien n'est affiché.
- Hors périmètre, constaté : `test_defaite` du vrai moteur (3 × monstre n° 150) donne une victoire avec la sauvegarde de ce poste (échec identique avant ce correctif).

## Avance #153 : touches de distance de la caméra (#146, 04/11/2026)

### Demande (D-225, 03/11 23 h 47)
« J'ai dit qu'on supprimait l'option pour choisir la vitesse de transition non ? Comme pour les options pour changer la distance de la caméra depuis le menu, il faut plutôt ajouter 2 nouvelles entrées pour les contrôler aussi au clavier ». **Lecture retenue (supposé)** : le réglage « Vitesse de transition » disparaît (c'est #101, pas encore faite : elle reste ouverte et n'est pas touchée ici) et la distance de la caméra, déjà réglable par le curseur « Distance caméra » et la molette, reçoit deux touches réattribuables.

### Fait
- `reglages.py` : deux actions, `cam_pres` (« Caméra (Rapprocher) », pavé + ou E) et `cam_loin` (« Caméra (Éloigner) », pavé − ou W). Touches par défaut libres (ni ZQSD, ni flèches, ni les chiffres des états, ni V, ni M, ni H, ni A / R). Un ancien `reglages.json` reçoit ces touches ; si le joueur avait pris l'une d'elles pour une autre action, elle lui reste et la nouvelle action n'a pas cette touche.
- `fenetre.py` : `_maj_distance_clavier` (à chaque image affichée, avec `_maj_camera`) : un pas de **5 %** à l'appui, puis, touche maintenue plus de **0,4 s**, un pas toutes les **0,08 s** (environ 60 % par seconde) ; arrondi au pas de 5 % (91 % → 90 % ou 95 %) ; bornes **50 à 200 %** ; passe par `regler_distance`, donc la même valeur que le curseur, la molette et les infos F1. Mêmes conditions que la molette (`_zoom_possible` : terrain libre d'une ville, d'un donjon, d'une tour ou carte du monde ; jamais un menu, un message ou un combat). Les deux touches ensemble ne font rien.
- `pause.py` : deux lignes dans la section « Caméra au clavier » de Commandes, à la suite des quatre flèches, avec une aide.
- Tests : `outils/test_distance_camera_clavier.py` (18 tests : actions et touches par défaut sans conflit, ancien fichier, réattribution, lignes du menu, pas, répétition, bornes, arrondi, rien hors du terrain). Suites voisines OK.
- **Établi (vraie fenêtre et vrai moteur, sous Xvfb, sauvegarde 2 = ville de Caf1)** : les événements de touche simulés par `on_key_press` / `on_key_release` font passer la distance de 100 % à 105 % à l'appui, puis, maintenue, jusqu'à 200 % (pas de 5 %, environ 60 % par seconde) ; pavé + et E rapprochent (195 → 190 …), pavé − et W éloignent ; la valeur s'arrête à 200 %.

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (touches, cadence de la répétition, lignes du menu).
- Les touches par défaut (pavé + / −, E / W) sont un choix de Claude : modifiables dans Commandes.
- Pas de 5 % et cadence de répétition : choisis pour coller au curseur du menu (pas de 5 %) ; à ajuster si trop lent ou trop rapide.
- « Vitesse de transition » est toujours dans Commandes (#101 non faite).
- Hors périmètre, constaté : `test_vitesse_combat.test_hors_combat_la_marche_garde_ses_reglages` échoue (faux jeu du test sans `pause`, depuis #151).

## Avance #154 : essai de zoom du ciel de l'écran-titre (#130, 04/11/2026)

### Demande (03/11 23 h 08)
« Pour le fond qui défile de l'écran titre, possible de zoomer l'image pour ne garder que la texture sans effet de répétition ? Au moins pour essayer. »

### Fait (essai, par défaut)
- `ciel_titre.py` : `zoom_ecran(aspect)` = `aspect / 0,5625` (16/9 : **x 3,16** ; 21/9 : x 4,15 ; 1 en portrait) et `matrice_zoom(M, z)` (x et y d'écran multipliés par z autour du centre, profondeur intacte).
- `fenetre.py` : au dessin du décor du titre, le groupe du ciel (« kumo », seul dans son groupe de texture : vérifié à l'exécution, sinon repli sur les bandes) est tracé avec `matrice_zoom(M, zoom)` ; les bandes étirées ne sont plus ajoutées. La fenêtre entière montre alors ce que montrait la zone portrait du jeu d'origine : moins d'un carreau de large, donc **aucune répétition horizontale**, et un peu plus d'une rangée de haut.
- Retour à l'ancien rendu (bandes étirées) : `DQ_CIEL_BANDES=1`. Zoom d'essai : `DQ_CIEL_ZOOM=2.5` (valeur forcée, jamais inférieure à 1).
- Tests : `outils/test_titre_ciel.py` (26 tests, dont 4 nouveaux : zoom selon le format, fenêtre entière = zone portrait, variable d'essai, matrice).

### Établi (captures sous Xvfb, 1920 x 1080, avant / après)
- Avant : les mêmes nuages reviennent 3 à 6 fois (en largeur comme en hauteur), atténués par les bandes étirées.
- Après : un seul grand nuage, aucune répétition visible, mais l'image est **nettement plus floue** (la texture du ciel est petite : x 3,16) ; le dégradé et les couleurs restent ceux du jeu. Le logo, le dragon et l'île ne changent pas.

### À trancher / non vérifié
- **Sous Windows** : à juger par Sylfried (netteté, vitesse de défilement apparente : le ciel glisse à la même vitesse dans la texture, donc x 3,16 plus vite à l'écran en valeur absolue).
- Une ou plusieurs valeurs intermédiaires (ex. `DQ_CIEL_ZOOM=2`) gardent un peu de répétition mais restent plus nettes ; non essayées (supposé).
- Le mode « agrandi » (F2, texture du décor en HD) pourrait adoucir le flou : non essayé sur le titre.
- Vu aussi en 21/9 (2560 x 1080, zoom x 4,15) : aucune répétition, encore plus flou.

## Avance #155 : bulles cliquables et rond central de la croix (#131, 04/11/2026)

### Demande (D-225, 03/11 23 h 19)
« Il faudrait faire en sorte qu'en cliquant sur une bulle (au-dessus d'un PNJ, d'un coffre...) je puisse valider l'action et faire ce qui est prévu, comme si j'appuyais sur la touche espace. Sinon, dans la version mobile, le cercle au centre de la croix directionnelle sert aussi de touche d'action : il faudrait reproduire l'exact même comportement pour cette touche, ainsi que son affichage lorsqu'on clique ou qu'on peut cliquer. »

### Établi
- Une bulle est le carré de 0,96 du paquet 19 / 20 (`Moteur.icones`, emplacements 0 à 15) ; le paquet 19 avec un emplacement **>= 16** n'est pas une bulle mais le clignotement de la croix (`TouchPad.SetPadBlink`) : il était ignoré, il est désormais lu (`Etat.pad_clignote`, numéro d'icône < 0 = arrêt).
- Un toucher de la croix (relâchement sans glissement) donne au moteur le bit de la touche d'action (analyse de `TouchPad.internalUpdate`, déjà relevée avant cette avance) ; que le « glissement » commence au seuil de la zone morte (`c_MoveThreshold` 10 unités, 0,124 du rayon) est une **déduction** (supposé).
- Mesuré au vrai moteur et à la vraie fenêtre (Xvfb, sauvegarde 2, bulle forcée au-dessus du héros) : le carré de la bulle est projeté avec la matrice de la ville (même formule que `DQ_PROJ`) ; un clic au centre donne `clic_a`, un clic à 5 pixels du coin de l'écran rien ; un toucher du rond central donne `clic_a`, un appui à 0,3 du diamètre (glissement vers la droite) pas d'action au relâchement ; `pad_clignote` vrai dessine la boule orange et son halo.

### Fait
- (retiré par l'avance #157 : `bulles.py`, projection et clic sur la bulle) ; `fenetre.py` : `_icones` garde les 4 coins monde de chaque bulle (`icone_quads`), `_bulle_sous` les projette (matrice de la dernière image) et `on_mouse_press` donne `clic_a` (la touche A, comme l'espace) sur le terrain libre uniquement ; clic droit inchangé (annuler).
- `hud_mobile.py` : `croix_glisse` (sorti du rond central), `croix_relacher()` (True = toucher du rond central) ; `fenetre.on_mouse_release` donne `clic_a` sur le terrain libre ; le rond central s'éclaire (boule orange + halo, morceaux `CurLight` et `CurBS` de la feuille `Button`) pendant un toucher et **clignote** (période de 1 s) quand le jeu le demande ; les directions ne changent pas.
- Tests : `outils/test_bulles_et_croix.py`, devenu `outils/test_croix_et_clic.py` à l'avance #157 (27 tests : projection, quadrilatère, paquets 19, toucher / glissement de la croix, clic sur la bulle, terrain libre seulement, emplacement 0).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (clic sur une bulle réelle, toucher de la croix).
- **Supposé** : la zone du toucher est le seuil de glissement du jeu (0,124 du rayon : environ 14 pixels de rayon en 1080p, plus petit que la boule dessinée) ; si c'est trop petit à la souris, l'agrandir (par exemple au rayon de la boule, 0,25) est un réglage d'une constante.
- **Supposé** : l'éclairage pendant le toucher et la période de clignotement (1 s) sont des choix du portage (les constantes du jeu, `MOVE_WAIT_TIME` / `MOVE_LIMIT_ALPHA`, sont inutilisées) ; quand le jeu envoie ce clignotement (tutoriel seulement ? à chaque action possible ?) n'a pas été relevé.
- La bulle n'a pas été vue dessinée à côté de son carré projeté (la sauvegarde de ce poste est sur l'écran noir du chapitre 1) : la projection est celle de `DQ_PROJ`, mais l'alignement visuel reste à confirmer.
- Une bulle cachée derrière un personnage ou un décor reste cliquable (pas de test de profondeur).

## Avance #156 : sprites inclinés vers la verticale du monde (#134, 04/11/2026)

### Demande (D-225, 03/11 23 h 27)
« Il y a une sorte d'effet d'optique avec ce PNJ, autant l'aplatissement sur les bords comme on a vu c'est nickel, autant quand mon perso monte ou descend sur la carte, j'ai l'impression que les sprites des PNJ (peut-être autres ?) se penchent alors que sur mobile ils restent bien droits. »

### Établi
- Depuis la correction des bords (`Jeu._panneau_ville`), le panneau d'un personnage est **exactement vertical à l'écran** partout (bords gauche / droit à moins de 0,01 px de la verticale, mesuré sur 15 états de caméra et 30 positions : `outils/test_sprites_droits.py`).
- Les **verticales du monde** (arêtes de murs, portes) penchent, elles, à l'écran : 11 à 19 degrés à 9 unités du centre en 16/9 (caméra à 47 degrés), 4 à 6,5 degrés sur le portrait d'origine ; l'angle change de plus de 5 degrés quand le héros monte ou descend (le personnage change de hauteur à l'écran). Le sprite reste à 0 : il paraît pencher **par rapport au décor** (c'est l'illusion d'optique de #134, cause établie par le calcul, pas par un essai sur Windows).
- Rendu réel (Xvfb, sauvegarde 2, château de Bastione, `DQ_SPRITE_INCLINAISON` à 0, 50 et 100 dans la même image du jeu) : à 0 le PNJ du bord gauche est droit, à 100 il penche du même côté que les murs voisins, à 50 entre les deux, pieds au même endroit.

### Fait
- `Jeu._panneau_ville(..., inc)` : après la correction des bords, le panneau est **cisaillé** vers la verticale du monde, pieds fixes : le haut glisse de `inc` x tan(inclinaison d'une verticale du monde au pied) x hauteur à l'écran, à la **même profondeur** (z-buffer, recouvrements, taille et position du bas inchangés). Au centre de l'image la verticale du monde est droite : rien ne change.
- `Jeu._inclinaison_sprites()` : 0,5 par défaut (essai), variable d'environnement `DQ_SPRITE_INCLINAISON` de 0 (bords verticaux, état d'avant) à 100 (parallèle aux murs).
- Tests : `outils/test_sprites_droits.py` (10 tests : bords verticaux partout, profondeur et centre inchangés, garde-fou du panneau d'origine, constat des verticales du monde, angle exact du cisaillement, taille / profondeur inchangées, écart sprite / mur divisé par deux, réglage par variable d'environnement, caméra inconnue).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried que le sprite ne « se penche » plus quand le héros monte ou descend ; si le cisaillement lui paraît trop fort ou trop faible : `DQ_SPRITE_INCLINAISON=30` ou `70` (ou 0 pour revenir en arrière), puis fixer la valeur définitive.
- **Supposé** : 50 % par défaut (milieu entre « droit » et « parallèle aux murs ») ; le cisaillement d'un sprite en pixel art peut montrer de légers escaliers sur les bords.
- Sur le mobile, les sprites sont aussi cisaillés par la perspective du panneau d'origine (4 à 6 degrés, non mesuré sur l'appareil) : la comparaison avec « droits sur mobile » n'a pas pu être faite ici.

## Avance #157 : plus de clic sur la bulle, la croix s'anime (#131, 04/11/2026)

### Demande (D-226, 04/11 09 h 44)
« Finalement supprime le fait de "cliquer sur la bulle", cliquer partout sur l'écran suffit, mais par contre je n'ai pas l'animation sur le joystick de la croix directionnelle quand une action est réalisable. »

### Établi
- Le jeu d'origine ne lie le clignotement de la croix (`TouchPad.SetPadBlink`, paquet 19 avec un emplacement >= 16) qu'à son **tutoriel** (voir `docs/audit/specs/audit_menus_pave.md`) : sur une bulle ordinaire le moteur n'envoie rien, d'où l'absence d'animation constatée par Sylfried.
- Rendu réel (Xvfb, sauvegarde 2, château de Bastione, bulle forcée au-dessus du héros) : sans bulle la boule est grise ; avec une bulle elle est orange avec son halo ; la bulle retirée, elle redevient grise.

### Fait
- Retrait de `bulles.py`, de `Jeu._bulle_sous` et de `icone_quads` ; `on_mouse_press` : un clic gauche sur le **terrain libre** (ni menu, ni message, ni carte, ni combat, ni effet), hors boutons et croix du HUD, donne la touche d'action (`clic_a`, comme l'espace). Clic droit = annuler, inchangé.
- `hud_mobile.Boutons.action_possible()` : vrai quand le jeu fait clignoter la croix (paquet 19) ou, sur le terrain libre, quand une bulle d'icône est affichée (position posée, opacité > 0,02) ; la croix pulse alors (boule orange et halo, 1 s).
- Tests : `outils/test_croix_et_clic.py` (23 tests : paquet 19, toucher et glissement de la croix, `action_possible`, clic n'importe où, pas de clic d'action hors du terrain libre).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (clic n'importe où, animation de la croix devant un personnage ou un coffre).
- **Supposé** : « cliquer partout » = un clic gauche sur le terrain libre donne la touche d'action (lecture de sa phrase) ; « action réalisable » = une bulle d'icône est affichée sur la cible ; l'animation est une extension du portage (le jeu d'origine ne l'a que pour son tutoriel).
- Un clic gauche sur le terrain sans cible fait la même chose que la touche d'action sans cible (rien, ou le message du jeu).

## Avance #158 : caméra au clavier en continu, Page haut / Page bas, plus d'option de distance (#146, 04/11/2026)

### Demande (D-226, 04/11 09 h 44)
« Supprime l'option pour changer la distance de la caméra. Touches par défaut pour rapprocher la caméra : Page haut. Touche par défaut pour éloigner la caméra : Page bas. Ces 2 touches ne doivent pas être saccadées, il faut un effet fluide pour que tant qu'on maintient la touche la caméra avance ou recule (à la même vitesse qu'elle tourne). »

### Établi
- Le pas de 5 % avec répétition (avance #153) est remplacé par un mouvement **continu** : `Jeu._maj_distance_clavier` change la distance à chaque image selon le temps écoulé, de `CAM_DIST_VIT` = `CAM_LACET_VIT` (100) pourcents par seconde, multiplié par « Vitesse de caméra » et par le multiplicateur de l'accélérateur si la touche est tenue, comme la rotation. À vitesse x1 : de 100 % à 50 % en 0,5 s, de 100 % à 200 % en 1 s. Le zoom garde sa valeur exacte (le réglage enregistré est arrondi au pour cent).
- Une touche ne sert qu'à une action (`test_touche_menu`) : Page haut / Page bas étaient la seconde touche par défaut de L / R (pages des menus du jeu) ; L / R gardent **A** et **R**. Le menu d'Échap et l'historique lisent Page haut / Page bas directement et ne changent pas.
- Un ancien `reglages.json` : les défauts de l'avance #153 (pavé + / −, E / W) deviennent Page haut / Page bas, et Page haut / Page bas sont retirées de L / R ; un choix du joueur est gardé (une touche déjà prise par un autre choix n'est pas reprise à la caméra).

### Fait
- Menu Affichage : la ligne « Distance caméra » est retirée (la molette, Ctrl + molette et les touches la règlent). Elle reste affichée dans les infos F1.
- Tests : `outils/test_distance_camera_clavier.py` (19 tests : défauts, migration, menu, vitesse, fluidité sans à-coup, bornes, vitesse de caméra et accélérateur, conditions d'action) ; `test_mode_fenetre.py` (ordre de la page Affichage).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (fluidité réelle, vitesse du zoom).
- **Supposé** : « à la même vitesse qu'elle tourne » = même nombre par seconde (100 % / s et 100 ° / s, mêmes réglages de vitesse). Si trop vite ou trop lent : la constante `CAM_DIST_VIT`.
- L / R n'ont plus Page haut / Page bas : en menu de jeu, A et R tournent les pages (réattribuable dans Commandes).

## Avance #159 : plus de réglage de vitesse de transition (#101, 04/11/2026)

### Demande (D-226, 04/11 09 h 45)
« Et supprime l'option pour changer la vitesse de transition, on la laisse à 1x tout court. »

### Établi
- Cette décision **remplace** celle de #101 (16 h 47 le 03/11 : transitions de porte à x4 fixe, reconnues à leur bruitage) : les transitions gardent la **durée du jeu (x1)**, sans accélération ni reconnaissance par bruitage.
- Le moteur garde son paramètre interne `Etat.vitesse_fondu` (1,0, durée d'origine) : les tests le font varier, plus aucun réglage du joueur ne le change.

### Fait
- `reglages.py` : clés `vitesse_fondu` et `vitesse_fondu_v` retirées (défauts, bornes, crans x1 à x4, migration de l'ancien défaut x2). Un ancien `reglages.json` qui les contient se charge sans erreur ; la clé est ignorée et n'est plus réécrite.
- `pause.py` : la ligne « Vitesse de transition » de Commandes › Vitesses est retirée ; `fenetre.py` : plus de `regler_fondu` ni de lecture du réglage au démarrage.
- Tests mis à jour : `test_reglages_son_texte.py` (plus de réglage, ancien fichier ignoré), `test_pause_pages.py`, `test_reglages_interface.py`.

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (la ligne n'est plus dans Commandes › Vitesses ; les transitions durent la durée du jeu).
- Le critère « x4 pour les portes » de #101 est abandonné (décision du 04/11) : à fermer quand Sylfried valide.

## Avance #160 : double clic du panneau Interface détecté comme Windows (#145, 04/11/2026)

### Demande (D-226, 04/11 09 h 44)
« Aligne toi sur le fonctionnement de windows pour détecter un double clic car là ça prend un peu de temps pour que la fenêtre agisse s'il s'agit finalement que d'un simple clic. »

### Établi
- Avant (#145, première version) : un clic simple sur la barre de titre du panneau Interface ne repliait / dépliait qu'après un délai fixe compté **depuis le relâchement**, quoi que fasse la souris ensuite.
- Windows juge un double clic ainsi : le second appui arrive **moins de `GetDoubleClickTime` (500 ms par défaut) après le DÉBUT du premier** et **dans le rectangle `SM_CXDOUBLECLK` x `SM_CYDOUBLECLK` (4 x 4 px par défaut) centré sur le premier**.

### Fait
- `pause.py` : `double_clic_systeme()` lit le délai et le rectangle du système sous Windows (ctypes `user32`), sinon 500 ms et 4 x 4 px (`DQ_DOUBLE_CLIC` force le délai) ; `_double_possible(x, y, t)` applique la règle de Windows.
- Le délai court depuis le **début** de l'appui. Si l'appui a déjà duré plus que le délai, le clic simple agit dès le relâchement.
- Le clic simple agit **dès que le double clic est impossible**, sans attendre la fin du délai : pointeur sorti du rectangle (`survol`), autre appui hors du rectangle (`clic`), début d'un glisser, ou délai écoulé (`maj`).
- Un vrai double clic reste neutre : retour à la position d'origine, aucun changement d'état à aucun moment.
- `test_panneau_interface.py` : 19 tests (6 nouveaux : délai compté depuis le début de l'appui, rectangle, pointeur sorti, appui ailleurs, appui plus long que le délai).

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried (le délai réel du système et la tolérance de position, qu'il peut régler dans Windows).
- **Supposé** : le rectangle 4 x 4 px de Windows est étroit ; sur un écran à haute densité de pixels, un tremblement de la main peut sortir du rectangle et le panneau agit alors plus tôt (comportement identique à celui d'une fenêtre Windows).

## Avance #162 : l'espace avant « ! » n'est plus trop large (#161, 04/11/2026)

### Demande (D-226, 04/11 09 h 44)
Capture « Ragnar lance l'aile de chimère en l'air ! » : « c'est le mauvais espace qui est affiché avant le « ! » donc ça en fait un trop large ». Sylfried propose d'aller chercher les règles du projet de traduction ; le code et ce projet ont suffi (consulté via l'API GitHub, sans clone).

### Établi
- Les textes du patch FR (`assets/msg/en/*.mpt`) mettent **U+00A0** avant « ! » (8 582 fois), « ? » (3 951) et « : » (170).
- Police `SE-GARRIR` (extraite du `base.apk` patché, 218 glyphes) : espace normale **advance 5**, glyphe 160 (U+00A0) **advance 11**, sans dessin ; U+202F et U+2009 n'existent pas (déjà dessinées comme l'espace normale).
- Projet de traduction (`PROJET.md`, 26/10) : « l'espace insécable n'existe pas dans Large.font (menus) », test de Sylfried sur DQ4 : espace normale = bon, insécable = mauvais (cas du « ; »).

### Fait
- `ui_menu.py` : `PoliceBitmap._glyphe` dessine U+00A0, U+202F et U+2009 comme l'espace normale (`ESPACES_FINES`) ; largeur d'une ligne et texture suivent. Le glyphe 160 garde son advance dans les données de la police.
- Effet de bord : l'historique des combats écrit `Or : n` + 5 U+00A0 + `Expérience : n` ; l'écart passe de 55 px de police (5 x 11) à 25 px (5 espaces).
- Test : `outils/test_espace_insecable.py` (police factice, vraie police si `DQ_CACHE_UI`, texture de ligne de même taille).
- Comparaison avant / après sur les vraies lignes du jeu (rendu de `PoliceBitmap.ligne`) : « en l'air !» passe de 2 espaces visuelles à une.

### À trancher / non vérifié
- **Sous Windows** : à confirmer par Sylfried sur son écran (capture du dialogue d'origine).
- **Supposé** : le jeu d'origine dessine la même espace de 11 px ; la correction s'écarte donc peut-être du mobile, dans le sens demandé. Si une espace plus fine que 5 px est préférée avant « ! », elle se règle dans `PoliceBitmap._glyphe`.

## Avance #164 : la nuit arrive (1 + x) / 2 fois plus vite en course (#163, 04/11/2026)

### Demande (D-226, 04/11 09 h 44)
« Je veux que la course ait le même effet accélératif que pour les combats, au lieu de faire venir 2x plus vite la nuit si l'accélérateur est en x2 je veux qu'elle vienne juste 1,5x plus vite, si l'accélérateur est en 1,5 alors elle doit venir en 1,25x plus vite, etc. »

### Établi
- Carte du monde : le temps du monde (`status::g_Stage + 0xcc`, cycle 0xd40) avance de 2 par image du moteur où le héros a changé de position (`FieldStage::ChangeTime(0)` appelé à la fin de `FieldPlayerDoku::checkDokuDamage`). La marche accélérée fait tourner le moteur a fois plus vite, donc la nuit arrivait a fois plus vite par seconde.
- La règle demandée est celle des rencontres aléatoires (#45, « Vitesse de marche » dans Commandes › Vitesses) : (1 + a) / 2.

### Fait
- `moteur.py` : `_crochets_horloge_jour` (crochet sur le saut terminal de `checkDokuDamage`, + 0x38) ; `rencontres.py` : `Passeur` (fraction (1 + a) / (2 a) des appels, fractions cumulées). Les appels sautés vont directement au `ret` de la fonction. A x1 (ou plus lent) : le jeu d'origine, à l'identique. Vérification du code attendu au démarrage (message et aucun crochet si le désassemblage ne correspond plus).
- `pause.py` : les aides de « Vitesse de marche » et « Multiplicateur de l'accélérateur » citent maintenant l'arrivée de la nuit.
- Test : `outils/test_horloge_jour.py` (4 tests de formule, 2 sur le vrai moteur avec `DQ_APK` / `DQ_SAVES`).
- Mesure sur le vrai moteur (carte du monde, sauvegarde 4, 491 pas dans le couloir de `simuler_rencontres.py`, combats coupés) : temps du monde par pas 2,000 à x1 ; 1,666 à x1,5 ; 1,499 à x2 ; 1,332 à x3 ; 1,246 à x4, soit **par seconde 1,25 ; 1,50 ; 2,00 ; 2,49 fois** celle de x1. Le héros marche exactement de la même façon (positions identiques image par image à x1 et à x4).

### À trancher / non vérifié
- **Supposé** : « le même effet accélératif que pour les combats » désigne la règle des rencontres (1 + x) / 2 ; la vitesse de combat (Rapide, Très rapide) ne touche pas l'horloge du monde.
- **Sous Windows** : à confirmer par Sylfried (marche longue sur la carte du monde avec l'accélérateur).
- **Établi** : seule la carte du monde fait avancer l'horloge (`ChangeTime(0)` n'est appelé que par `checkDokuDamage`) ; villes et donjons ne sont pas concernés.

## Avance #169 : croix x2 et course au bord de l'anneau (#166, 04/11/2026)

### Demande (D-227, 04/11 10 h 46)
« Double la taille de la croix directionnelle, et fais en sorte que lorsque le joystick touche les bords le personnage se met à courir, sinon il marche normalement. »

### Fait
- `hud_mobile.DIAM_CROIX` = 2 x 161,28 : le diamètre de base de l'anneau est le double de celui du mobile (à 800 de haut : 322,56 ; à 1080 : 435 px). Le réglage « Taille de la croix » (50 à 200 %) s'applique par-dessus : **50 % = la taille du mobile**, 200 % = le quadruple. Une fenêtre plus étroite que le portrait 9:16 réduit la croix (`LARGEUR_CROIX_MAX` = 0,75 de la largeur : le double du mobile en prend 0,72 au portrait) pour qu'elle ne sorte pas de l'écran (la vidéo du 04/11 est une fenêtre de 394 x 1102).
- `Boutons.croix_course()` : croix tenue dans une direction à `COURSE_SEUIL` = 0,9 du rayon de l'anneau ou plus (la prise va jusqu'à 1,178). `Jeu._facteur_vitesse` applique alors le multiplicateur de l'accélérateur comme la touche d'accélérateur tenue (les deux ensemble ne se cumulent pas) ; plus près du centre, le héros marche normalement (« Vitesse de marche » seule). La direction envoyée au jeu ne change pas. La boule s'allume (halo) tant que la croix est au bord, pour que le joueur sache qu'il court.
- Tests : `outils/test_croix_course.py` (16 tests : constante, diamètre selon la hauteur et le réglage, fenêtres étroites, croix dans l'écran à 5 formats, seuil, 24 directions, croix lâchée, direction inchangée, vraie `Jeu._facteur_vitesse`). Les faux jeux des tests de vitesse existants reçoivent une croix factice (`croix_course` faux).

### À trancher / non vérifié
- **Supposé** : « touche les bords » = le pointeur atteint 90 % du rayon de l'anneau ; « double » = le diamètre de base (un réglage enregistré à 100 % donne donc le double sans rien changer dans `reglages.json`).
- **Sous Windows** : taille de la croix (plus grande qu'avant : elle peut gêner l'image), seuil de la course (si trop tôt ou trop tard : `COURSE_SEUIL`), halo en course.

## Avance #170 : retour animé de la distance de la caméra à 100 % (#167, 04/11/2026)

### Demande (D-227, 04/11 10 h 46 et 10 h 49)
« Appuyer simultanément sur les 2 touches pour avancer ou reculer la caméra doit la faire revenir au zoom initial » ; puis : « Il doit aussi y avoir un effet de transition quand je remet le zoom par défaut (à la souris comme au clavier) ».

### Fait
- `Jeu._maj_distance_clavier` (à chaque image, avec `_maj_camera`) : **les deux touches ensemble** (« Caméra (Rapprocher) » + « Caméra (Éloigner) », Page haut + Page bas par défaut) lancent le retour de la distance à 100 % (`RG.DEFAUT['distance_camera']`) par une **animation**, comme les deux flèches opposées pour la rotation : pas par image = max(`CAM_RECENTRE_DIST` = 60 % / s, 5 x l'écart par seconde) x « Vitesse de caméra » (l'accélérateur n'y change rien), arrivée exacte sur 100 % (de 200 % à 100 % : environ 0,6 s ; de 50 % à 100 % : environ 0,5 s). Tant qu'il reste une touche enfoncée après la pression double (le relâchement n'est jamais exactement simultané), rien ne se passe (`dist_bloque`) ; une nouvelle pression seule, ou un cran de molette, interrompt l'animation ; un menu, un message ou un combat l'annule.
- `Jeu.distance_par_defaut` (Ctrl + molette, Ctrl + clic molette) ne saute plus à 100 % : elle lance la même animation (`dist_retour`). La molette seule et le curseur du menu Échap restent immédiats.
- Textes d'aide (page Commandes et aide des deux touches) mis à jour.
- Tests : `outils/test_distance_camera_clavier.py` (27 tests : l'ancien « les deux touches ne font rien » est remplacé par 9 tests : retour progressif et monotone depuis 200, 150, 70 et 50 %, durée, déjà à 100 %, vitesse de caméra et accélérateur, poursuite après le relâchement, touche restée enfoncée, interruption par une touche seule, Ctrl + molette, arrêt hors du terrain) ; `outils/test_entrees.py` : Ctrl + molette et Ctrl + clic molette lancent le retour (`dist_retour`) au lieu de mettre 100 d'un coup, un cran de molette l'interrompt.
- Capture sur la ville `maout` (distance de départ 200 % ; fond sans décor dans cette scène de test) : le héros grossit image après image, 200, 192, 184, ... 118, ... 100 % en 37 images.

### À trancher / non vérifié
- **Supposé** : vitesse du retour (60 % / s au minimum, 5 x l'écart par seconde, comme la rotation) ; « les deux touches » = Page haut + Page bas ou leurs remplaçantes réattribuées.
- **Sous Windows** : le ressenti de l'animation (trop rapide / trop lente : `CAM_RECENTRE_DIST` et le facteur 5) ; la pression double des deux touches du clavier réel.

## Avance #171 : Ctrl + touche de caméra remet tous les états de la caméra (#168, 04/11/2026)

### Demande (D-227, 04/11 10 h 46)
« CTRL + touche du clavier pour la caméra réinitialise TOUS les états de la caméra ».

### Fait
- Avant : Ctrl (la « Touche spéciale » des réglages) + une flèche ne remettait que la rotation et l'inclinaison (retour animé) ; la distance restait, et Ctrl + Page haut / Page bas zoomait comme sans Ctrl.
- `Jeu.reinitialiser_camera` : la position (`recentrer_camera`, si `_camera_pilotable` : terrain libre d'une ville, d'un donjon ou d'une tour, lieu sans interdiction de tourner) ET la distance (`distance_par_defaut`, retour animé de l'avance #170). Appelée par `_maj_camera` pour Ctrl + une des quatre flèches (sur la carte du monde et dans un lieu qui interdit de tourner, seule la distance revient) et par `_maj_distance_clavier` pour Ctrl + Page haut ou Page bas (même condition que la molette : `_zoom_possible`).
- Les touches tenues ensuite ne font plus rien ; Ctrl relâchée avant la touche, la touche seule n'agit pas tant qu'elle n'est pas relâchée (même logique que les deux flèches opposées). Les deux touches de distance sans Ctrl ne remettent toujours que la distance (#167), les deux flèches opposées que la position.
- Aide de la page Commandes mise à jour.
- Tests : `outils/test_camera_ctrl_tout.py` (15 tests : les trois états reviennent depuis plusieurs départs, par animation monotone, sans Ctrl rien ne change, carte du monde / lieu bloqué / hors terrain, effet d'écran).

### À trancher / non vérifié
- **Supposé** : « tous les états de la caméra » = rotation, inclinaison et distance ; « touche du clavier pour la caméra » = les quatre flèches, Page haut et Page bas (ou leurs remplaçantes réattribuées).
- Pendant un effet d'écran, Ctrl + Page haut / Page bas ne remet que la distance (la molette zoome encore à ce moment, les flèches ne tournent pas).
- **Sous Windows** : Ctrl + flèche, Ctrl + Page haut, Ctrl + Page bas au clavier réel.

## Avance #175 : croix réduite de 25 % par défaut (#172, 04/11/2026)

### Demande (D-228, 04/11 11 h 30)
« Finalement réduit la taille de la croix de 25 % par défaut »

### Fait
- `hud_mobile.DIAM_CROIX` = 1,5 x 161,28 (241,92 unités sur 800 de haut ; à 1080 de haut : 327 px) : 25 % de moins que le double de l'avance #169 (0,75 x 2 = 1,5 fois le mobile). Le réglage « Taille de la croix » (50 à 200 %, 100 % par défaut) s'applique toujours par-dessus ; 67 % redonne la taille du mobile. Le plafond des fenêtres étroites (`LARGEUR_CROIX_MAX` = 0,75 de la largeur) et le seuil de la course (`COURSE_SEUIL`) ne changent pas.
- Test : `outils/test_croix_course.py` mis à jour (constante, diamètres à 800 de haut, 16/9 jamais réduite).

### À trancher / non vérifié
- **Supposé** : « de 25 % » = 25 % de moins que la taille par défaut actuelle (et non 25 % de moins que le mobile) ; un `reglages.json` à 100 % prend la nouvelle taille sans rien changer.
- **Sous Windows** : la taille ressentie.

## Avance #176 : le retour du zoom va à la vitesse du recentrage des directions (#173, 04/11/2026)

### Demande (D-228, 04/11 11 h 30)
« La transition pour remettre le niveau de zoom par défaut doit aller à la même vitesse que pour les directions »

### Fait
- `fenetre.CAM_RECENTRE_DIST` = `CAM_RECENTRE_LACET` (240 par seconde au minimum, au lieu de 60 % par seconde en #170) ; la loi reste « au moins ce minimum, ou 5 x l'écart par seconde, fois « Vitesse de caméra » » comme pour la rotation. Un écart de X % se résorbe donc comme un écart de X degrés : au clavier (les deux touches, Ctrl + touche de caméra) comme à la souris (Ctrl + molette, Ctrl + clic molette), et rotation, inclinaison et distance arrivent ensemble à l'origine pour Ctrl + touche. De 200 % à 100 % : environ 21 images (0,35 s) au lieu de 37 (0,6 s).
- Tests : `outils/test_camera_ctrl_tout.py` (16) : rotation et distance arrivent à la même image (à une image près) pour sept paires d'écarts égaux, et suivent la même part de l'écart restant en route ; `test_distance_camera_clavier.py` (28) : constante égale à celle de la rotation, durées et pas maximal d'une image.

### À trancher / non vérifié
- **Supposé** : « la même vitesse » = les mêmes nombres que la rotation (240 par seconde) appliqués aux pourcents ; l'inclinaison garde son minimum propre (90 degrés par seconde, plage plus étroite).
- **Sous Windows** : le ressenti du retour du zoom et des directions ensemble.


## Avance #177 : ciel du titre à plat, à la hauteur de la fenêtre (#174, 04/11/2026)

### Demande (D-228, 04/11 11 h 30)
« Pour le fond de l'écran titre ajuste la hauteur pour automatiquement s'adapter à la hauteur de la fenêtre, et ça sera sur la largeur que la répétition se fera, et applique bien comme convenu les effets visuels qui doivent être appliqués (je crois qu'il y a une sorte d'effet de vague) » ; 11 h 44, devant la capture 16/9 : « Ce que tu as fait sur cette version est très bien ! Avec les effets visuels comme indiqué et c'est parfait ! »

### Fait
- `ciel_titre.ciel_ecran` : le ciel est un maillage plein écran en coordonnées normalisées (au fond, sans projection) ; la texture (carrée, 256 x 256) a pour HAUTEUR celle de la fenêtre (v de 0,998 en bas à 0,002 en haut, comme les rangées d'origine) à toute taille de fenêtre, sans agrandissement supplémentaire, et se répète sur la LARGEUR (`aspect` fois : 1,78 en 16/9, 2,33 en 21/9, moins d'une fois en portrait). Texture en REPEAT : aucune couture.
- L'effet de vague de l'ancien rendu en bandes est conservé et appliqué à toute la largeur : étirure horizontale ondulée (`etirure_plate`, intégrale exacte de `ETIRURE` : pente 0,52 à 1,48, jamais de retournement) et glissement vertical (`glissement_plat`, nul en haut et en bas). Il est fixe à l'écran et la texture défile dessous : les nuages se déforment en passant, et les copies d'une même tuile ne se ressemblent pas.
- Le dégradé de teinte des rangées d'origine (orange en haut et en bas, blanc au milieu) est repris tel qu'il apparaissait à l'écran (`degrade_ecran` : projection des bords et de points intermédiaires des quatre rangées par la matrice de la caméra) ; les coupures du dégradé deviennent des lignes du maillage.
- Défilement : même sens et même vitesse en tuiles que l'objet d'origine (une tuile pour 11,5 unités, 599 images) ; mesuré sur 120 images : le ciel à plat et le rendu en bandes glissent dans le même sens (vers la gauche). Le ciel étant plus grand (tuile = hauteur de la fenêtre), il avance plus vite en pixels.
- `fenetre._tracer_ciel_plat` remplace le tracé du groupe du ciel (seul dans sa texture) ; toute erreur coupe ce rendu et laisse le tracé d'origine (message sur la sortie). `DQ_CIEL_AGRANDI=1` redonne l'essai #130 (ciel agrandi), `DQ_CIEL_BANDES=1` les bandes, `DQ_CIEL_COPIES=1` les copies ; `DQ_CIEL_TUILE` (essai) change la largeur de la tuile en hauteurs de fenêtre.
- Tests : `outils/test_titre_ciel.py` (34, dont 8 nouveaux) : hauteur de texture = hauteur de fenêtre à sept formats, étendue horizontale = `aspect` tuiles, vague jamais retournée et sans dérive, défilement = décalage de u seul, triangles de même sens et sans trou (aire totale = rectangle), dégradé sommet par sommet, repli sans caméra valable. Captures 16/9, 21/9 et portrait contrôlées ; 16/9 vue et validée par Sylfried dans l'interface.

### À trancher / non vérifié
- **Supposé** : « effet de vague » = l'ondulation `ETIRURE` / `GLISSE` des bandes (seul effet de ce genre dans les notes) ; « comme convenu » = ce rendu, la teinte d'origine et la vitesse d'origine. Si un autre effet avait été convenu, il manque.
- La texture de 256 x 256 est agrandie à la hauteur de la fenêtre (1080 px en 16/9) : le ciel est flou, c'est la conséquence directe de « la hauteur de la fenêtre ».
- **Sous Windows** : le rendu réel à 1866 x 1050 et plein écran (netteté, raccords de tuile, sens et vitesse du défilement).

## Avance #179 : aucune pause dans aucun menu (#178, 04/11/2026)

### Demande (D-229, 04/11 11 h 40)
« Le menu historique met le jeu en pause, il ne faut aucune pause dans aucun menu »

### Fait
- `Pause.PAGES_FIGEES` est vide (c'était `('historique', 'quitter')`) : le jeu, le son et l'horloge tournent derrière TOUTES les pages du menu Paramètres, sans recevoir ni touche ni clic (`Jeu.tick`, inchangé). Le mécanisme d'arrêt (`fige_le_jeu`, `_synchroniser_gel`, retour anticipé de `_boucle`) est gardé tel quel, inutilisé : une page ajoutée à `PAGES_FIGEES` l'arrêterait de nouveau (cela contredirait D-229).
- Mesuré dans le jeu (ville `maout`, historique ouvert à l'image 60) : écart moyen entre les images 90 et 200 de la scène derrière la fenêtre = 0,0 avant (jeu figé), 4,07 après (le jeu avance).
- Conséquence traitée : le jeu écrit maintenant dans l'historique pendant qu'on le lit. `VueHistorique.suivre_le_jeu` (appelée à chaque image par `Pause.maj` sur la page Historique) remplace la liste par la liste à jour quand la vue est tout en bas : le message choisi reste le même (reconnu par son objet), sauf s'il était le dernier (le choix suit alors le plus récent). Plus haut dans la liste, pendant un glissement ou avec la barre, la liste ne bouge pas (la lecture ne saute pas) ; elle se met à jour au retour en bas. Onglet Combats et « Favoris seulement » : mêmes règles.
- Tests : `outils/test_parametres_sans_pause.py` (15) : aucune page du menu (toutes les `_e_*` plus racine, historique et quitter) ne fige le jeu, `PAGES_FIGEES` vide, le mécanisme d'arrêt est essayé avec une page de test ; `outils/test_historique_messages.py` (122) : 10 tests de `suivre_le_jeu` (rien de neuf, nouveau message en bas, choix ailleurs qui ne saute pas, lecture plus haut, glissement, onglet Combats, liste pleine, favoris seulement, sans historique, appel par `Pause.maj`).

### À trancher / non vérifié
- **Supposé** : « aucun menu » = toutes les pages du menu Paramètres (Historique et Quitter comprises), pas les fenêtres propres du jeu.
- Effet voulu à connaître : un combat qui avance seul (vitesse rapide) ou un message minuté continue pendant la lecture de l'historique, et les rencontres aléatoires peuvent survenir pendant la question « Quitter » (le jeu ne reçoit aucune entrée).
- **Sous Windows** : historique ouvert, la scène derrière bouge, le son continue, la liste reste lisible quand un message ou un combat s'ajoute.

## Avance #181 : PNJ sans le cisaillement de #156 (#180, 04/11/2026)

### Demande (D-229, 04/11 11 h 40)
« Finalement remet l'affichage des PNJ comme sur la version mobile, de l'exact même façon, car là il y a des comportements bizarres où on peut les voir s'étirer et autre quand ils s'approchent du bord »

### Établi
- Comparaison de rendus (village de Maout, 1920 x 1080, même image du jeu) près des bords gauche / droit : (1) état de la veille = correction des bords + cisaillement à 50 % de #156 : parallélogramme, tête décalée, pixels en escalier ; (2) correction des bords seule (état d'avant #156) : rectangle droit, proportion constante (0,738) ; (3) panneau brut d'origine (`DQ_CORRECTION_BORDS=0`) : penché vers l'extérieur de 15 à 20 degrés et trop large (jusqu'à 0,9 au lieu de 0,75) en 16/9.
- Le cisaillement (#156) est la seule modification récente du dessin des sprites : c'est lui qui crée l'étirement signalé.

### Fait
- `Jeu.INCLINAISON_SPRITES_DEF` : 0,5 -> 0 (bords exactement verticaux). Rendu **identique au pixel** à l'état d'avant #156 (0 pixel de différence, mesuré). L'essai reste disponible : `DQ_SPRITE_INCLINAISON` de 0 à 100. La correction des bords (toujours complète) est inchangée.
- Tests : `outils/test_sprites_droits.py` (11) : nouveau test de l'état livré (correction 1, inclinaison 0 : rectangle droit et proportion 0,738 +- 0,008 pour les 15 états de caméra et 30 positions), test de la variable d'environnement adapté (défaut 0).

### À trancher / non vérifié
- **Supposé** : « comme sur la version mobile, de l'exact même façon » = sprites droits aux proportions constantes, comme sur le portrait du mobile (le panneau d'origine n'y penche que de 4 à 6 degrés), donc l'état (2). Le panneau brut (3) n'est PAS remis : il reproduirait en 16/9 l'inclinaison et l'élargissement que la correction des bords (« exactement la correction que j'attendais », #43) retire. Si Sylfried voulait le brut : `DQ_CORRECTION_BORDS=0` (ou changer `_correction_bords`).
- L'impression d'optique de #134 (le sprite paraît pencher par rapport aux murs quand le héros monte ou descend) revient : c'est le prix du retour à l'état d'avant (cause établie : les verticales du monde penchent à l'écran, le sprite reste droit).
- **Sous Windows** : PNJ près des bords gauche et droit, droits et sans étirement.

## Avance #183 : murs des intérieurs, faces arrière cachées (#182, 04/11/2026)

### Demande (D-230, 04/11 13 h 25)
« En intérieur les murs doivent devenir transparents, je crois que le comportement exact c'est que les faces externes n'ont pas de textures et donc si on tourne la caméra alors on doit automatiquement pouvoir voir à travers les murs (regarde comment c'est fait dans le jeu et refais le pareil) »

### Établi
- Lu dans le paquet de données (ShaderLab `culling` de chaque `Shader` « Custom/... ») : `fld_normal`, `fld_atest`, `fld_trans`, `fld_transz`, `fld_normal_sepia`, `fld_atest_sepia`, `fld_trans_sepia` = **culling 2 (Cull Back)** ; `Custom/Field` (carte du monde) = 0 (sans culling) ; `Custom/ImdChara` = 2 (déjà géré pour les modèles 3D) ; `CharaShadow` = 2 ; `Chara`, `DssaChara`, `DssaMonster*`, `Effect0` = 0.
- La visionneuse dessinait le décor sans culling : les faces externes des murs, normalement invisibles, bouchaient la vue quand la caméra tournait. Pas de texture transparente dans les données : ce sont les faces arrière qui sont supprimées par le shader.

### Fait
- `Jeu._culling_decor(actif)` : culling des faces arrière, face avant = sens horaire à l'écran (Unity est en main gauche ; `GL_CW`, comme les modèles 3D). `_tracer_decor` le règle groupe par groupe (opaques puis transparents), sauf le ciel du titre (ses propres sommets, `ciel_plat` / `ciel_zoom`), et le coupe après les groupes (bandes / copies du ciel, ombres, sprites, effets inchangés). `DQ_DECOR_CULL` : 0 = ancien rendu, 2 = sens inverse (essai : il cache les sols et montre les faces externes, donc faux).
- Mesure (même image) : église `mak1f1` caméra tournée de 150 degrés : le mur de devant disparaît et la salle, le tapis et le héros se voient ; caméra de base : 0 pixel de différence dans `mak1f1` et `mlb1a`, 58 à 235 pixels dans `chf1b` et `caf1`, 1 347 sur 576 000 dans le village de Maout (arêtes des clôtures, vues de leur face avant : rien de manquant) ; titre : 53 pixels.
- Tests : `outils/test_decor_culling.py` (5) : réglages GL par défaut, coupé, variable d'essai, groupe par groupe sauf le ciel, autres réglages GL inchangés.

### À trancher / non vérifié
- **Supposé** : le sens des faces est celui des triangles du cache (aucun objet de carte à échelle négative sur les 670 cartes : 0 sur 18 374, donc pas d'inversion à corriger) ; une échelle négative dans le modèle lui-même (Transform local, absente du cache) n'a pas été cherchée.
- Pas regardé : les fonds de combat (`btl_*`, même chemin de dessin, mêmes shaders) et les donjons.
- **Sous Windows** : intérieurs (église, château, maisons), donjons, fonds de combat : rien de manquant dans la vue normale, murs de devant invisibles caméra tournée.

## Avance #185 : PNJ au panneau brut du jeu, sans s'aligner sur la caméra inclinée (#184, 04/11/2026)

### Demande (D-231, 04/11 13 h 25)
« Reviens à la position brute des PNJ pour le moment, exactement comme dans le jeu, ils doivent garder aussi le même comportement et avec le nouveau système de caméra ils ne doivent pas s'aligner si on monte ou descend la caméra »

### Établi
- Après #181 (cisaillement retiré), les PNJ restaient reconstruits à l'écran par la correction des bords (#134 : bords verticaux, proportion 0,738, `Jeu._panneau_ville(t = 1)`) : ce n'est pas le panneau du jeu (`Chara.normalBillboard` : rectangle 0,48 x 0,64 qui prend la rotation de la caméra, sommets décalés en profondeur de 0,185 au bas et 0,65 au haut vers la caméra).
- Le panneau d'origine, avec la rotation de la caméra de la VUE, se redresse face à la caméra à chaque inclinaison (Haut / Bas) : le personnage « s'aligne » sur la vue (en vue de dessus, il reste de face comme un autocollant).

### Fait
- `CORRECTION_BORDS_DEF = 0.0` : `Jeu._correction_bords()` vaut 0 par défaut (panneau d'origine, `_panneau_ville` renvoie les sommets du jeu) ; `DQ_CORRECTION_BORDS=100` ou `--correction-bords 100` redonnent la correction complète.
- `Jeu._camera_ville` calcule aussi `self._cadre_sprites` : le repère (droite, haut, avant) de la caméra DU JEU avec la rotation autour du héros (lacet) mais SANS l'inclinaison de la visionneuse (même formule que `_cadre_jeu` : tangage du jeu - `lookDownAdjust`). `Jeu._repere_sprites(cam3d, corr)` le donne à la boucle des sprites quand la correction est nulle ; correction > 0 : repère de la vue (la reconstruction à l'écran en a besoin) ; pose couchée, ombres, bulles : inchangés. `DQ_SPRITES_SUR_VUE=1` redonne l'alignement sur la vue (essai).
- Effet : au cadrage du jeu (aucune inclinaison) le rendu est exactement celui du mobile (PNJ qui penchent vers l'extérieur près des bords : défaut connu de l'original, accepté « pour le moment ») ; Haut / Bas ne changent plus le panneau (4 coins identiques en monde) ; Gauche / Droite le font tourner de face avec l'inclinaison du jeu.
- Rendu (Maout, 1920 x 1080) : cadrage du jeu normal ; inclinaison forte : les PNJ se couchent (ils sont debout dans le monde, vus d'en haut) au lieu de rester de face.
- Tests : `outils/test_sprites_droits.py` (18) : défaut = panneau d'origine, correction complète toujours droite, repère des sprites = repère du jeu, inchangé par Haut / Bas (+- 15, 30, 80 degrés), suit le lacet, caméra libre et mini-jeux.

### À trancher / non vérifié
- **Supposé** : « ne doivent pas s'aligner si on monte ou descend la caméra » = le personnage ne se redresse plus face à la caméra quand on l'incline. Conséquence : à forte inclinaison (vue de dessus) les PNJ et le héros paraissent couchés, comme des objets debout. Si tu préfères qu'ils restent de face à la caméra : `DQ_SPRITES_SUR_VUE=1` (ancien alignement), à passer en réglage ou en comportement par défaut.
- Non vérifié : le rendu sous Windows ; les donjons, tours et la pose couchée (inchangée) n'ont pas été regardés un par un.

## Avance #187 : l'historique seulement quand le joueur a la main (#186, 04/11/2026)

### Demande (D-232, 04/11 13 h 25)
« L'historique doit pouvoir être accessible uniquement quand j'ai le contrôle de mon perso, donc pas pendant un combat ni pendant un moment où le jeu prend le contrôle »

### Établi
- Avant : la touche H ouvrait l'historique en ville, sur la carte du monde et en combat, même pendant un message ; la ligne « Historique » du menu Paramètres était toujours active.
- Le moteur dit lui-même quand le joueur a la main : verrou du joueur (`Global.Flag` bit 4 : événement, scène, discussion, fondu de sortie), message affiché, menu du jeu ouvert, effet d'écran / chargement, partie « combat » (même condition que la marche accélérée, `Jeu._facteur_vitesse`).

### Fait
- `Jeu.controle_joueur()` : vrai seulement en ville / donjon / tour / carte du monde, joueur non verrouillé, sans message, sans menu du jeu, sans effet d'écran ni chargement, hors combat (partie combat, cascade d'entrée, écran noir d'attente, entre deux fondus). Un fondu seul (arrivée sur une carte, retour de combat, joueur libre) n'y compte pas. `Jeu.historique_possible()` : en plus, jamais à l'écran titre.
- Touche H (`Jeu._touche_historique`) : ouvre la page si possible, sinon ne fait rien (le message « Historique indisponible : le jeu a la main » de #187 est retiré en #195).
- Menu Paramètres : la ligne « Historique » est grisée (infobulle : « Disponible seulement quand vous avez la main sur votre personnage… ») quand ce n'est pas possible, relue à chaque image.
- `Pause.maj` : page historique ouverte alors que le jeu reprend la main (il tourne derrière le menu depuis #179) : retour à la racine (ou menu fermé si la page venait de la touche H) (le message « Historique fermé : le jeu a repris la main » de #187 est retiré en #195).
- Tests : `outils/test_historique_acces.py` (19) : table de vérité de `controle_joueur`, écran titre, touche H (ouvre / message), ligne du menu active / grisée / relue, faux jeu minimal, fermeture automatique.

### À trancher / non vérifié
- **Supposé** : le menu du jeu ouvert (commandes, Divers, boutique) compte comme « le jeu a la main » : en passant par « Paramètres » du menu Divers, la ligne Historique est grisée ; la touche H reste utilisable après avoir fermé ce menu.
- **Non vérifié sous Windows** : H en ville, pendant un dialogue, une scène, un combat ; fermeture automatique quand un événement reprend la main (cas rare : le jeu ne reçoit aucune entrée derrière le menu).

## Avance #189 : bouton de vitesse de combat sur le bord gauche (#188, 04/11/2026)

### Demande (D-233, 04/11 13 h 30)
« … et pour le bouton d'accélération du combat remets-le sur le bord gauche pour le moment »

### Établi
- Depuis #47 le bouton était rattaché au coin bas gauche de la boîte du bas (commandes ou message) à la taille de la plaque « Fuir » (`Jeu._ancrer_vitesse_combat`, `Boutons.ancre`) ; sa case de la grille (colonne 0,4, ligne 8 sur 18 : le bord gauche de l'écran) ne servait plus qu'une fois déplacé par le joueur.

### Fait
- `hud_mobile.ANCRAGE_VITESSE_DEF = False` et `hud_mobile.ancrage_vitesse()` : par défaut `Boutons.ancre()` est vide et `Boutons._ancre_prete()` toujours vrai : le bouton est à sa case de la grille, sur le bord gauche, à la taille de sa plaque d'origine (118 x 60), dès la première image du combat. Une position choisie par le joueur (`bouton_vitesse_pos`) est gardée. `DQ_VITESSE_ANCRE=1` redonne le rattachement de #47 (le calcul de l'ancre de la fenêtre est conservé).
- Interface « Combat : bouton de vitesse » : la ligne « Replacer sous la boîte de combat » devient « Replacer sur le bord gauche » (même effet : position d'origine) tant que le rattachement est coupé.
- Mesure sur le vrai moteur (combat forcé sur la carte du monde, 1280 x 720, position à CHAQUE image dessinée) : x = 16 px et y = 346 px à toutes les images, aucun décalage au début d'un tour ni à la première image.
- Tests : `outils/test_bouton_vitesse.py` (25 dont 8 avec le moteur) : variable d'environnement, bord gauche même avec une ancre connue, visible dès la première image, position du joueur gardée, rattachement redemandé, rien hors combat, vrai combat (`CombatReelBordGauche`, rattachement `CombatReel` avec `DQ_VITESSE_ANCRE=1`).

### À trancher / non vérifié
- « pour le moment » : le rattachement sous la boîte reste prêt (`DQ_VITESSE_ANCRE=1`) ; à reprendre quand tu voudras en refaire le défaut.
- **Sous Windows** : le bouton sur le bord gauche à chaque image d'un combat, y compris en 16/9 large (écran 2560 x 1440) ; le clic change toujours la vitesse.

## Avance #191 : descriptions d'objets recoupées à leur cadre (#190, 04/11/2026)

### Demande (D-234, 04/11 13 h 30)
« Revois aussi la taille de certaines interfaces, là par exemple le texte ne tient pas, s'il le faut reviens sur les proportions, les positions et les designs strictement originaux et on avisera après » (capture : « Peut aussi être utilisée comme objet de combat. » sur la cellule « Attaque E 74 »).

### Établi
- Reproduit sur le vrai moteur (combat forcé, Objets → Épée de cuivre, texte remplacé par celui du patch) : fiche d'objet en combat = fenêtre de type 38, description = chaîne (2, 3) ancrée à x = -214 au milieu de la cellule de gauche (bord droit de la cellule x ≈ 64,7 mesuré sur la capture : 704 px sur 1280, cadre de 447 px pour 452 unités), « Attaque E 24 » = chaîne (2, 4) dans la cellule de droite (x 75). Cellule de 2 lignes.
- Les 360 descriptions du patch (`assets/msg/en/b0831000.mpt` et `b0835000.mpt`, deux tables jumelles de 180 objets ; lecture : séparateurs `@a@b`, `@cN@`, octets de contrôle) ont des lignes de 38 caractères ou une seule ligne de 50 : avec la vraie police SE-GARRIR, 254 sur 360 dépassent la cellule de combat (270 unités depuis x = -214) et 25 le cadre du menu Objets (359 unités depuis x = -211, jusqu'au bouton du sac).
- Les proportions du port ne sont pas en cause (fenêtres de combat à 510/459 depuis #47, mise à l'échelle uniforme) : le texte est plus large que la cellule d'origine à toutes les tailles. Rien n'a été ramené aux proportions, positions et designs d'origine.

### Fait
- `ui_menu.DESCRIPTIONS = {(7, 1), (10, 4), (38, 3)}` : (type de fenêtre, numéro de chaîne) -> bord droit utile (`DESC_FICHE_X_MAX` 148 pour la fiche d'un sort et le menu Objets, `DESC_COMBAT_X_MAX` 56 pour la fiche d'objet en combat). `Fenetre.param_str` pose `wrap_x` / `wrap_n = 2` sur le texte.
- `Rendu._ajuste_description` (remplace `_recoupe`) : un texte qui tient (au plus 2 lignes, aucune plus large que le cadre) est laissé tel quel, retours à la ligne du patch compris ; sinon les retours sont remplacés par des espaces et le texte recoupé à la largeur du cadre ; s'il faut encore plus de 2 lignes, il est comprimé en largeur par pas de 0,05 jusqu'à `COMPRESSION_MIN` = 0,7. Résultat gardé par texte dans `nd['_adj']` (le dessin est refait à chaque image).
- Mesure sur les 360 descriptions réelles : après, aucune ne dépasse (2 lignes au plus, largeur dans le cadre, aucun mot perdu) ; 39 sont comprimées en combat (plus forte : x 0,75), aucune dans le menu Objets.
- Rendus sur le vrai moteur : avant / après (« Peut aussi être utilisée comme objet au / combat. » recouvrait « Attaque »), ligne unique de 50 caractères, deux lignes de 36 et 31 caractères (comprimées), menu Objets du village de Maout.
- Tests : `outils/test_description_objet.py` (16 dont 3 avec la vraie police et les 360 textes) ; `outils/test_magie_liste.py` reprend les tests de recoupe.

### À trancher / non vérifié
- Sous Windows (écrans 1920 x 1200 et 2560 x 1440) : non vu.
- Autres fenêtres qui ont la même barre de description en bas : boutiques (types 46, 60, 61, 63) et fiche d'objet de la boutique de vente (70). Les chaînes de description sont (46, 3), (60, 4), (61, 4), (63, 4), (70, 3) ; leur bord droit n'a pas été mesuré (barre supposée identique : 148). Non ajoutées sans capture. → ajoutées en #220 (mise en page réelle, police réelle et capture hors écran).
- Si les proportions d'origine sont quand même voulues : `reglages.LARGEUR_COMMANDES` (fenêtres de combat) et `fenetre.UI_ZOOM` (1,12) sont les deux réglages du port ; ils ne changent rien à ce défaut.

## Avance #193 : sauvegarde automatique, lecture du code du jeu (#192, 04/11/2026)

### Demande (D-235, 04/11 13 h 33)
« Pareil pour la sauvegarde auto, regarde le code du jeu pour savoir comment est écrite la sauvegarde et ce qui est sauvegardé et comment ». Le détail technique est dans `docs/notes-technique-portage-dq4.md`, section « Sauvegarde automatique : quand, quoi, comment ».

### Établi
- **Quand** : `AutoSave(bool)` est appelée par `TownPart::initialize` et `FieldPart::initialize` seulement : à l'arrivée sur une carte, jamais à la fermeture. Relevé sur le moteur réel : écrite à l'arrivée sur la carte du monde et à l'entrée de `dab1`, `tbf3`, `dkf1a`, `taf2a`, `sjm2f1` ; non écrite à l'entrée de `mak1f1`, `hhk1f1`, `mlm1f1`, `mbk1f1`, `mfk1f1`, `sif1`, `cbf2`, `sqf4`.
- **Quoi** : `data5.dat` (banque 4), 15 360 octets, type de sauvegarde 3 = instantané de reprise (carte courante, position exacte, groupe, chapitre, joueur, monstres, drapeaux de campagne, somme de contrôle) ; `data9` (journal le plus récent) n'est pas touché.
- **Comment** : `Cryption::Filter` (xorshift32 graine CRC) puis `fopen("wb")` / `fwrite` / `fclose`, non atomique. Effacée par « Revenir à l'écran titre » (`killbank(4)`).
- **Portage** : la visionneuse n'écrit rien elle-même ; le moteur écrit `data5.dat` dans `dq4_pc\sauvegardes` (lu en premier au démarrage). La fermeture de la fenêtre n'enregistre que réglages, historique et son : pas d'écriture à la fermeture, comme l'original.

### Non établi / à trancher
- Règle complète du saut d'écriture (valeur en `StageStatus + 0x28`, source du bit 17, conditions de `FieldPart`) : le tableau est un relevé, pas la règle. Sous Windows : non vu.
- Écarts voulus de la visionneuse (inchangés) : plaque « Sauvegarde automatique » grisée au lieu de cachée (`DQ_AUTO_CACHEE=1` rétablit l'original) ; états instantanés `etat_NN.dqs` distincts de la suspension `data4`. À Sylfried de dire s'il les garde, et s'il veut une écriture à la fermeture (absente de l'original).

## Avance #195 : historique sans message d'indisponibilité (#194, 04/11/2026)

### Demande (D-236, 04/11 14 h 37)
« Supprime le message indiquant qu'on ne peut pas ouvrir l'historique en combat, pas la peine d'en informer le joueur. Sinon tout est nickel ! »

### Fait
- `Jeu._touche_historique` : quand le joueur n'a pas la main, la touche H ne fait plus rien (plus de message « Historique indisponible : le jeu a la main ») ; elle reste acquittée.
- `Pause.maj` : la page historique qui se referme parce que le jeu reprend la main le fait sans le message « Historique fermé : le jeu a repris la main ». Les constantes `MSG_HISTORIQUE_INDISPONIBLE` et `MSG_HISTORIQUE_FERME` sont supprimées. Les règles d'accès de #187 (`controle_joueur`, `historique_possible`) ne changent pas.
- `outils/test_historique_acces.py` : les trois tests qui attendaient un message vérifient maintenant qu'il n'y en a aucun (19 tests passent).

### À trancher / non vérifié
- L'infobulle de la ligne « Historique » grisée du menu Paramètres (« Disponible seulement quand vous avez la main… ») est gardée : elle n'apparaît qu'au survol de la ligne. À retirer aussi si Sylfried le veut.
- Sous Windows : non vu.

## Avance #197 : rangement du projet (#196, 04/11/2026)

### Demande (D-237, D-238, 04/11 14 h 57)
« Refais aussi une passe sur la structure du projet [...] clean un peu le tout avec des dossiers, revoir la qualité du code, simplifier l'utilisation, centraliser les sauvegardes et les nommages car par exemple le dossier `jeux` reprend l'exacte forme de l'autre projet de traduction. »
- **D-237 (sondage)** : « Un dossier `donnees\` dans le projet (Recommandé) » : `apk\`, `sauvegardes\{mobile\<date>, portage, etats, avant_import_<date>}`, `cache\`, `reglages\`, `journaux\` ; un seul `lancer_dq4.bat` à la racine ; `dq4_pc\` ne contient plus que du code.
- **D-238 (sondage)** : « dossiers + nettoyage sûr + découpage des fichiers seulement si ça permet de mieux structurer [...] je te laisse juger si c'est nécessaire de le faire, et si oui comment le faire ».

### Fait
- Plan complet et table ancien nom → nouveau : `docs/plan_du_code.md`.
- Code rangé en paquets : `noyau` (moteur émulé), `monde` (cartes, décors, sprites), `rendu`, `combat`, `menus`, `persistance`, `fenetre`. `dq4_pc/fenetre.py` (3 761 lignes, 254 fonctions dans une seule classe `Jeu`) est découpé en 13 modules par thème ; la classe `Jeu` est assemblée par héritage de neuf « mixins ». Vérifié par l'arbre syntaxique : les 254 fonctions sont strictement identiques à celles d'avant, rien d'autre n'a changé dans le code du jeu.
- `dq4_pc/chemins.py` : tous les dossiers et fichiers en un seul endroit (`Dossiers`), variables d'environnement `DQ4_DONNEES` et `DQ4_JEUX` (ancien fonctionnement), reprise de l'ancienne disposition `chemins.migrer()` : copie sans jamais écraser ni supprimer (le cache, lourd, est déplacé d'un coup s'il n'existe pas encore dans `donnees\cache`). `dq4_pc/principal.py` : lecture des arguments et ouverture de la fenêtre (ancienne `fenetre.main`).
- `persistance/etats.py` : les états instantanés enregistrés avant le rangement se rechargent (table `ANCIENS_MODULES` + `Unpickler.find_class`).
- Un seul lanceur `lancer_dq4.bat` à la racine (Python, `.venv` à la racine, reprise des anciens fichiers, génération des mises en page, lancement) ; l'ancien `dq4_pc\lancer_dq4.bat` redirige vers lui. `outils\generer_ui.bat` et `outils\dump_il2cpp.bat` suivent.
- Tests dans `tests\` (`test_chemins.py` : 15 tests nouveaux ; `tests/_chemins.py` : aides communes). Entretien : six tests déjà en échec avant le rangement sont réparés, sans toucher au jeu (`test_mode_fenetre` : valeur par défaut de la correction des bords depuis #184 ; `test_historique_messages` : code de `Pause.maj` changé par #187 ; `test_casino_bestiaire`, `test_priorite_jeu`, `test_transition_combat`, `test_vitesse_combat` : fausse fenêtre sans `pause`). Nettoyage sûr : variables et imports inutilisés.
- CI : compilation de `dq4_pc tests outils`, motifs interdits (+`donnees`), tests `test_chemins` et `test_rencontres`.

### Non fait / à savoir
- `menus/pause.py` (1 459 lignes) et `menus/ui_menu.py` (1 255 lignes) restent d'un seul tenant : un fichier par page du menu Paramètres serait possible, mais le gain est moindre que pour `fenetre.py` et le risque non nul ; à reprendre si Sylfried le souhaite.
- Cache : les fichiers du cache sont des dictionnaires et des tableaux numpy sans référence aux modules du code (supposé, non vérifié sur son PC) ; en cas de doute, supprimer `donnees\cache` (il est refait).
- Les anciens dossiers (`jeux\`, `dq4_pc\sauvegardes`, `dq4_pc\reglages.json`…) ne sont pas supprimés : à effacer à la main après vérification.
- Sous Windows : non vu (double-clic sur `lancer_dq4.bat` à la racine, premier démarrage avec reprise des fichiers).

## Avance #199 : écriture des sauvegardes atomique, sans plantage (#198, audit ENG-02, 04/11/2026)

### Constat (audit du 04/11/2026)
`CoreJeu.h_fclose` écrivait `data*.dat` directement ; une erreur d'E/S (antivirus qui verrouille le fichier, disque plein) levait une exception dans le crochet, le moteur s'arrêtait et la fenêtre se fermait (`Jeu.tick` sans `try`). Établi par lecture et par essai sur le moteur réel ; fichier tronqué après un arrêt brutal : supposé ; Windows : non vérifié.

### Fait
- `CoreJeu.ecrire_atomique(chemin, octets)` : fichier `.tmp` à côté, `fsync`, puis `os.replace` (remplacement d'un coup) ; deux essais espacés de 0,25 s ; en cas d'échec l'ancien fichier reste intact, le `.tmp` est retiré.
- `CoreJeu.h_fclose` : une erreur n'est plus fatale. Le moteur continue (il croit avoir écrit, comme avant), l'échec est mis dans `CoreJeu.echecs_ecriture`.
- `Jeu._signaler_echecs_ecriture` (appelée par `tick`) : ligne dans `donnees\journaux\erreurs_fenetre.log` et petit message « Sauvegarde impossible : le jeu continue (détails dans erreurs_fenetre.log) ». Rien ne change quand tout va bien.
- `tests/test_ecriture_sauvegarde.py` (6 tests, dans la CI) ; `test_sauvegarde_auto` (moteur réel) inchangé et vert.

### Non vérifié
Windows (antivirus, OneDrive) : le cas réel d'un verrou n'a pas été reproduit, seulement simulé.

## Avance #202 : Ogg écrêté au lieu de déborder (#200, audit SND-02, 04/11/2026)

### Constat (audit du 04/11/2026)
`decoder_akb` lisait les Ogg Vorbis en `int16` (`soundfile.read(dtype='int16')`) : quand le décodage dépasse la pleine échelle (surmodulation normale de Vorbis), l'échantillon déborde et un pic devient un pic de signe opposé. Établi sur un Ogg synthétique et sur les données d'origine : BGM14 (3 échantillons, vers 91 s) et BGM34 (7 échantillons) ; les 49 autres musiques et SE0409 (fanfare, Ogg aussi) n'ont aucun dépassement. Audibilité : non vérifiée (pas de carte son).

### Fait
- `son.decoder_ogg` : lecture en `float32`, mise à l'échelle 32767, **écrêtage** à ±pleine échelle, puis `int16`. Vérifié sur les vrais fichiers : seuls ces 3 + 7 échantillons changent (les autres musiques sont identiques à l'échantillon près).
- `tests/test_son_decodage.py` (4 tests ; ajouté à la CI avec `soundfile`).

### Non vérifié
Windows et l'écoute.

## Avance #204 : trois bruitages à boucle de nouveau bouclés (#201, audit SND-03, 04/11/2026)

### Constat (audit du 04/11/2026)
SE0329 (fin de boucle 62 501 pour 62 496 échantillons décodés), SE0331 (58 983 / 58 976) et SE1118 (113 314 / 113 312) déclarent une boucle dont la fin dépasse de quelques échantillons la fin des données (reste d'un bloc ADPCM). Le garde `0 < fin <= n` de `decoder_akb` les déclarait « sans boucle ». Établi par lecture des en-têtes sur les 634 bruitages : 14 boucles reconnues sur 17 déclarées. Quels événements du jeu les jouent : non vérifié (identifiants calculés).

### Fait
- `son.decoder_akb` : une fin de boucle qui dépasse de **au plus 2 048 échantillons** (`TOLERANCE_FIN_BOUCLE`) la fin des données est ramenée à la fin des données (la boucle va jusqu'au bout) ; au-delà le garde reste. Les 17 boucles déclarées sont maintenant reconnues ; aucun autre bruitage ne change.
- Cache disque des bruitages (`son_SE*.npz`) versionné (`VERSION_CACHE_SON` = 2, 5e valeur de `p`) : un cache d'avant #201 (qui garde « sans boucle ») est refait au premier usage, sans rien à supprimer à la main.
- `tests/test_son_decodage.py` : 6 tests de plus (10 au total).

### Non vérifié
Comportement exact de la bibliothèque son d'origine quand la fin dépasse (supposé : la boucle va jusqu'à la fin des données) ; l'écoute ; Windows.

## Avance #205 : surfaces transparentes triées par leur vraie priorité (#203, audit MAP-01, 04/11/2026)

### Constat (audit du 04/11/2026)
`map_objs` lisait la « priorité » d'un objet de carte dans la moitié haute de ses drapeaux (`flag >> 16` : 0 ou 4), alors que `FldObject.Load` lit les drapeaux en entier de 32 bits (+48) et la **priorité en entier de 32 bits en +52** (`FldObject.set_priority` : file de rendu 3000 + priorité). Établi par désassemblage et par lecture des 18 374 objets : 290 cartes ont des surfaces transparentes, 64 ont au moins deux priorités réelles (47 hors décors de combat : `dlb1a`, `dlb3` à `dlb5`, `dib1` à `dib3`, `teout4` à `teout6`, `zaout`, `ev06` à `ev09`, `mlout2`, `mmout`…). Mesure A / B de l'audit : sur `dlb1a` l'écume au pied des cascades manquait (12 % des pixels), `dib2` 3 %, `teout5`, `teout6`, `zaout` moins de 0,3 %. Supposé : que l'original montre bien l'écume (aucune capture d'origine).

### Fait
- `monde/fld.py:map_objs` : `prio` = entier en +52 ; `flag` = 16 bits bas des drapeaux (+48), identique à avant pour les billboards. Les clés de groupes `('tr', priorité, texture)` et le tri de `fenetre/champ.py` (`_tracer_decor`) sont inchangés : ils reçoivent maintenant la vraie priorité (sur `dlb1a` : 9 groupes transparents de priorités 10, 11, 12, 18 à 23, au lieu de 0 et 4 ; vérifié sur la vraie carte).
- Cache des cartes `carte10_` -> `carte11_` : **les cartes sont refaites en arrière-plan au premier lancement** (quelques minutes, comme pour chaque changement de version du cache) ; les `carte10_*.pkl` sont supprimés quand tout est prêt (`_purger_anciens`).
- `tests/test_fld_priorite.py` (4 tests, dans la CI) ; `test_textures_carte` adapté (carte10 purgée, carte11 gardée).

### Non vérifié
Rendu d'origine (aucune capture) ; Windows. Tri par distance d'Unity à priorité égale : non mesuré.

## Avance #207 : charger un état instantané ne touche plus au moteur s'il est inutilisable (#206, audit ENG-06, 04/11/2026)

### Constat (audit du 04/11/2026)
`persistance/etats.appliquer` réécrivait la mémoire du moteur (tas, données, pile locale) **avant** de décoder la partie Python de l'état (`pickle`). Un fichier d'état abîmé ou tronqué levait donc l'erreur après avoir déjà écrasé le moteur : la partie en cours restait dans un état mélangé. Et rien n'empêchait de charger un état enregistré avec un autre `libdq4core.so` (autre APK) : les adresses ne correspondent plus. Établi par lecture du code ; le cas « autre bibliothèque » n'a pas été observé en jeu.

### Fait
- `appliquer` : vérifie la version, **puis** l'empreinte de la bibliothèque, **puis** décode `python` et `viewer`, et seulement ensuite écrit dans le moteur. Un état refusé ne change plus rien.
- `instantane` enregistre `lib_sha` (16 premiers caractères du SHA-256 de l'image de la bibliothèque). Les états déjà enregistrés n'ont pas cette clé : ils restent chargeables comme avant (aucune migration).
- `tests/test_etats_ordre.py` (6 tests : 5 sans APK, dans la CI ; 1 avec le vrai moteur : un état tronqué laisse la mémoire intacte, l'état sain se recharge) ; `test_fld_priorite` ajouté à la CI (il y manquait depuis #205).

### Non vérifié
Windows ; un vrai changement d'APK entre l'enregistrement et le chargement.

## Avance #209 : la tabulation des textes de menu partout où le jeu en règle une (#208, audit UI-03, 04/11/2026)

### Constat (audit du 04/11/2026)
`TextMesh.tabSize` : une tabulation vaut `tabSize` fois la largeur d'une espace. Les mises en page exportées en portent une dans les types 8, 20, 34, 35 (8), 31, 33, 39 (25) et 78 (1), mais `ui_menu.param_str` ne la remplaçait que pour la liste des magies (`noms_liste`), et `plaque()` (plaques de monstres) écrivait le texte tel quel ; la police du jeu n'a pas de glyphe pour `\t` (largeur 0). Établi (vrai moteur + vrai rendu, rendus comparés de l'audit) : dans « Ordre de marche » (type 20) la ligne « Nv.: 5 » était dessinée **sur le sprite** du personnage ; dans chaque combat contre un groupe (type 31) le « ×N » était collé à gauche de la plaque. Supposé pour 33, 34, 35, 39 (fenêtres jamais ouvertes pendant l'audit).

### Fait
- `menus/ui_menu.py:tabuler(s, tab_size)` (nouvelle fonction) : `\t` -> `round(tabSize)` espaces ; cellule sans `tabSize` : texte inchangé. Utilisée par `param_str` (condition `noms_liste` supprimée : la liste des magies garde exactement le même résultat) et par `plaque()`.
- Mesuré avec la vraie police (SE-GARRIR, espace de 5 px, « × » de 16 px, caractère 9,3925, texte ancré en x = -74, plaque de -71 à +71) : « ×2 » finit à x = 68,8 (dans la plaque), jusqu'à « ×9 ». « ×10 » finirait vers x = 79, soit 8 unités au-delà du bord (supposé identique dans l'original avec les mêmes constantes ; groupe de 10 monstres identiques : rare) : non compressé.
- `tests/test_tabulation_menu.py` (7 tests, avec pyglet en mode sans fenêtre ; non ajouté à la CI qui n'installe pas pyglet).

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
- `tests/test_feuilles_speciales.py` (7 tests, dans la CI : découpage, alias, couleur de chaque case lue avec `uv_case`, vraie feuille quand elle est dans le cache : rangées 0 à 3 pleines, 4e à 8 cases, sillage rangées 5 à 9).

### Non vérifié
Rendu de l'original (aucune capture) ; Windows ; le bateau en situation réelle (mouvement, rotation de la direction, accostage : seule la feuille a été vérifiée par sprites injectés) ; poids de l'atlas HD (52 Mo de mémoire vidéo, avec mipmaps).

## Avance #213 : l'ombre du ballon à sa place sur la carte du monde (#212, audit SPR-02, 04/11/2026)

### Constat (audit du 04/11/2026)
`cmd_chara_shadow` (paquet 15) : bit 12 = position de l'ombre (3 flottants), bit 13 = opacité (1 flottant), **bit 14 = `SetFieldShadowPosition` (3 flottants)**. `Etat.appliquer` ne lisait pas le bit 14 (et ne retirait pas le flottant du bit 13). Établi (scénario du chapitre 5, drapeau 344 = 1) : le ballon envoie `0x440c` + `[2495,97 ; 383,97 ; -1]` à chaque image pour un sprite en `(2496 ; 352 ; 20)` : l'ombre doit être 32 pixels de carte (2 tuiles) plus au sud ; elle était collée sous la nacelle.

### Fait
- `noyau/moteur.py` : le flottant d'opacité est retiré, puis `s['ombre_champ'] = (x, y, hauteur)` si le bit 14 est présent. `fenetre/jeu.py` (boucle des sprites, carte du monde) : l'ombre du sprite est posée à cette position (arrondie en pixel perfect) ; sans `ombre_champ`, comme avant.
- Capture de la visionneuse réelle (scénario du ballon) avant / après : l'ombre sous la nacelle disparaît et revient 32 pixels de carte plus bas (68 pixels d'écran à 1280 × 720), par-dessus la maison de la carte.
- `tests/test_ombre_ballon.py` (5 tests, dans la CI : le paquet 0x440c réel, ordre des flottants des bits 12 / 13 / 14, paquets sans bit 14 inchangés, paquet tronqué).

### Non vérifié
Rendu de l'original (aucune capture) ; Windows ; que l'ombre passe bien par-dessus les bâtiments de la carte (supposé) ; le vol complet du ballon (seul le départ au sol a été rejoué).

## Avance #215 : l'import de sauvegardes contrôle la somme des journaux et écrit sans fichier à moitié écrit (#214, audit ENG-07, 04/11/2026)

### Constat (audit du 04/11/2026)
`sauvegardes.importer` ne contrôlait que la taille des journaux et écrivait directement. Un journal abîmé (ou qui n'en est pas un) était importé, puis refusé par le moteur (« banque vide », sans raison pour le joueur) ; l'écriture directe pouvait laisser un fichier à moitié écrit. Établi : le moteur ne plante pas sur un journal abîmé (statut invalide, retour au titre).

### Fait
- `persistance/format_journal.py` (nouveau) : `dechiffrer` (filtre du jeu, `Cryption::Filter`), `somme`, `verifier(nom, octets)` -> `None` ou la raison : en-tête « rate » + somme de contrôle des 0x3660 premiers octets ; banque neuve (`DWEN`) ou supprimée (`DLED`) valides ; `data9.dat` sans somme. Vérifié sur 452 journaux réels (sauvegardes du téléphone et écritures du moteur) : aucune fausse alerte ; seul le fichier de bruit de l'audit est refusé.
- `persistance/ecriture.py` (nouveau) : `ecrire_atomique` (déplacée depuis `CoreJeu`, qui garde le même nom) ; `sauvegardes.importer` l'utilise : chaque fichier est écrit en entier ou pas du tout, un échec laisse l'ancien fichier et est signalé dans « Ignorés », les autres fichiers passent ; rien d'écrit = erreur claire.
- `lire_sources` refuse un journal abîmé avec sa raison. `test_chemins` : journaux valides fabriqués (`journal_valide`) au lieu d'octets quelconques.
- `tests/test_import_sauvegardes.py` (13 tests, dans la CI : valide, banques vides, octet changé, somme changée, bruit, import partiel, tout refusé, échec d'écriture simulé sans fichier temporaire oublié, vraies sauvegardes).

### Non vérifié
Windows ; un export fait avec un autre jeu (même format ?) : seul le format du jeu est reconnu.

## Avance #216 : un nom de carte sans données est refusé au lieu de planter le moteur (#76, audit ENG-10, 04/11/2026)

### Constat (audit du 04/11/2026)
Le ticket #76 (« `startTown` plante pour `za3f3` et `ev01`, les données sont correctes ») était mal posé. Établi : **`za3f3` n'a pas de `.stg`** dans `split_UnityDataAssetPack.apk` (le paquet graphique a bien son `.map` et son `.fld` : carte orpheline, 529 `.stg` pour 530 cartes) ; le moteur ne teste pas l'existence du fichier et déréférence un pointeur nul (`FldStage::getCameraLimitL` + 0x1c, reproduit dans 4 contextes sur 4). **`ev01`** (carte du titre) plante seulement quand on la lance par `startTown` après le chargement d'une sauvegarde (`TownOpeningManager::draw` -> `TownCharacterManager::setRotate`) ; démarrée par le titre elle se charge sans erreur (partie 12, 4 sprites) : artefact du lanceur de test, pas un défaut de données. Les 8 autres cartes d'événement (`ev02` à `ev09`) se chargent. Supposé : qu'aucun déplacement du jeu ne mène à `za3f3` (la table des déplacements n'a pas été balayée en entier).

### Fait
- `noyau/moteur.py:Moteur.demarrer_ville` (chemin d'essai `DQ_VILLE`) : refuse un nom sans `assets/map/<nom>.stg` avec une erreur claire (`ValueError`) au lieu de laisser le moteur planter ; les 529 cartes de l'APK sont acceptées.
- `tests/test_carte_inconnue.py` (4 tests, dans la CI). Ticket #76 clos avec explication (aucun défaut du portage à corriger).

### Non vérifié
Aucun déplacement du jeu vers `za3f3` (supposé).


## Avance #218 : les réglages du moteur qui ne s'installent pas sont signalés au joueur (#217, audit ENG-08, 04/11/2026)

### Constat (audit du 04/11/2026)
Chaque réglage posé dans le moteur d'origine (vitesse du texte, défilement des combats, PV/PM au niveau supérieur, rencontres, horloge jour / nuit, sorts sans effet, fondus de script, fenêtre des lieux, bouton « Paramètres », historiques) vérifie l'instruction qu'il remplace ; sur un autre APK le réglage n'est pas installé et seule la console le disait (invisible sur Windows). `_elargir_symboles` et `patcher_parametres` se taisaient même complètement. Établi : avec l'APK étudié, aucun point n'est manqué.

### Fait
- `noyau/moteur.py` : `Moteur.crochets_manques` + `Moteur._manque(texte)` (console, liste sans doublon : `reappliquer_correctifs` repasse après le chargement d'un état) remplacent les `print` des 8 installateurs ; messages ajoutés pour la fenêtre des lieux (instruction différente ; « déjà élargie » reste silencieux), le bouton « Paramètres » (ni d'origine ni déjà patché) et les deux historiques inactifs.
- `fenetre/jeu.py:Jeu._signaler_crochets_manques` (modèle : `_signaler_echecs_ecriture`) : une ligne par point dans `erreurs_fenetre.log` et un message à l'écran de 8 s ; les points trouvés plus tard (après le chargement d'un état) sont annoncés à leur tour, jamais deux fois.
- `tests/test_crochets_manques.py` (7 tests, dans la CI : faux moteur avec instruction d'origine / différente / déjà patchée, doublons, chaque installateur sans fonction ; journal et message ; moteur réel : liste vide et les deux historiques actifs).
- Non touché : `ctl_flush_tb` avalé dans `CapteurCombat` (le capteur est créé avant la première image : aucun bloc déjà traduit à vider ; ne sert qu'à un capteur créé plus tard par les outils d'essai).

### Non vérifié
Un autre APK (aucun disponible : le message n'a été vu que sur faux moteur) ; Windows.

## Avance #220 : les descriptions du bas des boutiques, du casino et de la vente sont recoupées à la largeur de leur cadre (#219, audit UI-04, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi (mise en page réelle, police réelle, 360 descriptions du patch) : la barre de description du bas des fenêtres du casino (type 46), d'achat (60, 61), de vente (63) et de la fiche d'objet de vente (70) n'était pas dans `ui_menu.DESCRIPTIONS` : 24 descriptions sur 360 dépassaient du cadre (pire : +72 unités, sous le bouton retour), 3 avaient plus de 2 lignes. Type 63 : texte plus petit (8,29), aucune ligne trop large, 3 descriptions de plus de 2 lignes. Supposé : le rôle des cellules (fenêtres non ouvertes dans le moteur).

### Fait
- `menus/ui_menu.py` : `DESCRIPTIONS` indexée par **(type, port, numéro de chaîne)** au lieu de (type, numéro) : la fenêtre du casino (46) a quatre autres textes au numéro 3 (listes, ports 0 à 3) qu'un simple ajout aurait recoupés. Anciennes entrées : (7, 0, 1), (10, 0, 4), (38, 2, 3) ; nouvelles : (46, 4, 3), (60, 4, 4), (61, 4, 4), (63, 0, 4), (70, 0, 3), bord droit 148 comme la fiche d'un sort. Le texte du moteur n'est pas modifié : c'est le rendu qui recoupe (et comprime jusqu'à ×0,7 si 2 lignes ne suffisent pas).
- `tests/test_description_objet.py` (22 tests, à la main : pyglet) : table, un seul port recoupé par fenêtre, vraie mise en page (chaque clé désigne une cellule de texte du bas), 360 descriptions avec la vraie police pour 46 / 60 / 61 / 70 et pour 63 (aucune ne sort, aucun mot perdu).
- Capture hors écran avant / après (vrai rendu, fenêtres 60 et 46) : la ligne qui passait sous le bouton retour passe sur 2 lignes dans le cadre ; les listes du casino ne bougent pas.

### Non vérifié
Windows ; le moteur n'a pas ouvert ces fenêtres (rôle des cellules supposé d'après la géométrie).

## Avance #222 : un échec de lecture ne coupe plus le son jusqu'à la fermeture du jeu (#221, audit SND-10 et SND-12, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi (lecture de `son.py`) : `_lancer_se` et `_lancer_bgm` faisaient `self.ok = False` sur n'importe quelle exception de lecture (périphérique retiré ou changé, pilote) : tout le son était coupé jusqu'à la fermeture, sans trace hors console. La reprise après pause et `_appliquer_volumes` avalaient leurs erreurs (SND-12). Non vérifié : un déclenchement réel (changement de périphérique sous Windows).

### Fait
- `son.py` : compteur d'échecs consécutifs (`ECHECS_MAX` = 3) ; à 3, le son est coupé un moment puis rouvert tout seul (`DELAIS_REESSAI` 2 s, 10 s, puis 30 s) ; à la réouverture un seul échec recoupe aussitôt (délai suivant) ; un son qui part remet le compteur à zéro. Pendant la coupure rien n'est tenté (pas d'échecs en cascade) et la dernière musique de fond demandée est gardée : elle est relancée au retour (un arrêt la supprime, un jingle à reprise la laisse). Pas de pilote audio au départ (pyglet absent) : ni coupure ni nouvel essai, comme avant.
- Journal : chaque échec, la coupure et le retour vont dans `erreurs_fenetre.log` (au plus 40 lignes par session) ; message à l'écran « Son interrompu : nouvel essai automatique » et « Son rétabli ». Erreurs avalées (volume de la musique / des bruitages, reprise après pause) : notées une seule fois par session.
- `fenetre/jeu.py` : `noter_erreur(texte)` (écriture dans le journal des erreurs, ne lève jamais) remplace les trois copies du même code (échecs d'écriture des sauvegardes, réglages du moteur non appliqués, son).
- `tests/test_son_echecs.py` (13 tests, dans la CI : faux lecteurs sans carte son).

### Non vérifié
Un vrai changement ou retrait de périphérique audio (Windows) ; la durée réelle d'une panne de pilote (les délais sont un choix).

## Avance #224 : la teinte plein écran de l'effet 35 couvre toute la largeur 16/9 (#223, audit CMB-02, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi (capture de la visionneuse, effet 35 forcé dans un combat, 1280 × 720) : l'effet 35 est un quad plein écran de 12,9 × 12,9 (paquet 25, modèle 5035) calé sur le champ 4:3 d'origine ; avec le combat élargi en 16/9 (choix de Sylfried) il ne couvrait que x 108 à 1202 sur 1280 : deux bandes latérales sans teinte. Supposé : les autres quads larges (effet 9, 7 unités) sont plus grands que le champ et corrects. Quel déclencheur du jeu utilise l'effet 35 : non vérifié (forcé).

### Fait
- `combat/effets_plein_ecran.py` (nouveau) : `elargir(loc, modele, aspect)` étire en largeur de `aspect / (4/3)`, autour de son centre, les coordonnées locales d'un maillage de combat dont le modèle est dans `MODELES_PLEIN_ECRAN` (5035 seul) ; rien pour un écran 4:3 ou plus étroit ni pour un autre modèle.
- `fenetre/scene_combat.py:_maillages_combat` : appel juste après la lecture des coordonnées locales (combat seulement).
- Capture avant / après (vrai rendu, 1280 × 720) : teinte sur toute la largeur après. `tests/test_effets_plein_ecran.py` (7 tests, dans la CI).

### Non vérifié
Windows ; les autres effets d'écran (3, 5, 6 : #68).

## Avance #226 : une texture de monstre absente n'arrête plus le jeu (#225, audit CMB-03, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi : `_texture_monstre` lisait `donnees.texture('m%03d')` dans un `try` qui ne couvrait que les exceptions ; quand la fonction renvoie `None` (25 numéros de monstre sans texture `m<id>` dans les données), `self._tex(None, ...)` plantait et le processus s'arrêtait (reproduit avec le monstre 199 forcé). Aucun de ces numéros n'est dans les 255 formations : pas atteignable par un combat normal. Non vérifié : un usage scénarisé.

### Fait
- `fenetre/scene_combat.py:_texture_monstre` : `None` = même repli que l'exception (texture transparente 16 × 16, monstre non dessiné) avec une ligne de console ; vérifié avec la visionneuse complète (monstre 199 forcé : le combat se déroule).
- `tests/test_texture_monstre_absente.py` (3 tests, à la main : pyglet, donc pas dans la CI).

### Non vérifié
Un usage scénarisé de ces numéros ; Windows.

## Avance #228 : le bruitage des boutons suit la règle du jeu d'origine, au clavier comme au doigt (#227, audit SND-08 / SND-09 / UI-01, règle de #60 / D-156, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi (désassemblage de `MenuPortItem.Update`, 8 sites d'appel de `Sound.PlaySE` dans 3 classes) : à l'appui d'un bouton de menu le jeu joue `PlaySE(300)` seulement si la touche de manette du bouton est A (0x10) ou action (0x800) ; B (0x20), retour (0x400), flèches (1, 2, 4, 8) et zone 0x80 sont muets ; les boutons du terrain (`TouchPad.internalUpdate`) jouent le bruitage. Le portage le jouait pour tout bouton cliqué et, au clavier, pour B, flèches de page, ▲ ▼, changement de colonne de la saisie numérique, fermeture et mode de la carte, retour de la licence ; il ne le jouait pas pour Entrée (Commandes), Espace (Discussion), M (Carte) ni pour les lettres tapées dans la saisie du nom (G-173). Règle de Sylfried (#60, D-156, D-166) : le clavier joue le bruitage dans les mêmes situations qu'au doigt. Les menus du jeu n'ont que les manettes A, B, flèches et action (inventaire des 80 types) : aucun bouton à bascule.

### Fait
- `fenetre/constantes.py` : `PADS_BRUITAGE = 0x810` et `bruit_bouton(manette)`, le seul critère.
- `fenetre/clavier_souris.py:on_mouse_press` : un clic sur un bouton de menu joue le bruitage seulement si `bruit_bouton` ; retour et mode de la fenêtre de la carte (0x400, 2) muets. Carte ouverte au clavier (M : changer de vue, fermer ; flèches de la liste des boutiques) : muet.
- `fenetre/affichage_menus.py` (`_saisie_menu`, `_saisie_pas`) : B, flèches de page (L / R, ◀ ▶ d'une autre fenêtre, quantité des boutiques), ▲ ▼ et changement de colonne de la saisie numérique : muets ; A (et l'action 0x800 de la fiche du bestiaire) : bruitage. Les messages au moteur partent comme avant.
- Terrain : Entrée (Commandes), Espace (Discussion) et M (Carte) jouent le bruitage 300 quand le moteur autorise le bouton : `hud_mobile.Boutons.permis(nom)` (même condition que `visibles`, sans le réglage d'affichage « boutons » : la touche reste sonore si l'on masque les boutons). Un clic sur le bouton à l'écran ne joue pas deux fois (le bruit part à l'appui).
- Saisie du nom : une lettre ajoutée au clavier joue le bruitage comme le clic sur la lettre. Licence : le retour (manette 0x20, clic droit) est muet, le bouton « politique » (A) garde son bruitage.
- Inchangé : les bruitages demandés par le moteur (annulation, curseur : paquet 35), l'écran des sauvegardes et le menu Échap (fonctions du portage), les sons d'aperçu des volumes.
- `tests/test_bruitage_clavier.py` (25 tests ; dans la CI la règle seule, le reste demande pyglet) : table des manettes, `permis` = `visibles`, vraies méthodes de `Jeu` sur un faux jeu (clic, menu au clavier, saisie numérique, touches du terrain, carte ouverte, lettres du nom) ; sur l'ancien code, 8 cas de comportement échouent (plus `permis`, absent). Voisins relancés : croix et clic, entrées, touche menu, retour au titre, pause, casino, historique, son (tous verts) ; visionneuse complète lancée 200 images sans erreur.

### Non vérifié
Windows (oreille : B, flèches, ▲ ▼, retour de la carte sans bip ; Entrée, Espace, M et lettres du nom avec bip). Si le moteur joue lui-même un bruitage d'annulation à la fermeture de la carte (paquet 35), il reste audible ; si le jeu d'origine joue un bruitage à la frappe d'une lettre au toucher (3 sites `PlaySE(300)` de `InputName.Update`, correspondance exacte non lue) : Supposé.

## Avance #230 : arrêt de la musique pendant un jingle, morceau sans boucle redemandé (#229, audit SND-05 / SND-06, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi par lecture du code d'origine (`SoundControl`, pas par une trace du jeu) : `StopBGM` ne remet pas l'état du jingle à zéro, donc un arrêt reçu pendant un jingle lancé avec reprise (`0x1000 | n`) fait **repartir la musique d'avant** ; redemander un morceau en cours le relance. La visionneuse effaçait la reprise (silence) et ignorait toute redemande du morceau en cours, y compris d'un morceau sans boucle (BGM 1, 34) déjà terminé. Aucune occurrence dans les traces (le moteur arrête puis lance la nouvelle musique ; seul `playRestart(48)`, coffre / médaille, utilise la reprise) : Non vérifié en jeu.

### Fait
- `son.py:jouer_bgm` : l'ordre d'arrêt garde le numéro de la musique à reprendre et la relance après l'arrêt (sans jingle, ou jingle déjà fini et reprise déjà faite : arrêt normal).
- `son.py:_bgm_finie` + `jouer_bgm` : un morceau sans boucle dont l'heure de fin est passée (pas en pause) n'est plus « en cours » : le redemander le relance. Un morceau qui joue encore, en boucle ou non, n'est pas relancé (inchangé).
- `tests/test_son_musique_limites.py` (11 tests, dans la CI, faux lecteurs) ; 2 échouent sur l'ancien code. Voisins relancés : échecs du son, mixage, décodage, bruitage de transition, réglages du son, retour au titre, sauvegarde automatique.

### Non vérifié
Une occurrence réelle (aucune connue) ; le relancement d'un morceau **en cours** redemandé (`playBgm` / `playStart`, le moteur ne réémet pas `play`) : volontairement non reproduit, un redémarrage à tort serait plus gênant que l'écart ; Windows.

## Avance #232 : repli « menus simples », le canevas du message est lu de façon circulaire (#231, audit CMB-04, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi : dans le repli sans `ui_layout.json`, `Moteur.lire_message` découpait `a[top:top + h]` sans modulo alors que le défilement du moteur croît sans borne et que le canevas de message d'Unity est une texture circulaire de 512 lignes ; après une quinzaine de lignes (cumulées sur plusieurs combats) le texte devenait vide. Avec la vraie interface (`ui_menu.regler`, `y & 0x1ff`) : aucun problème. Atteignable seulement si `ui_layout.json` manque du cache.

### Fait
- `noyau/moteur.py:lire_message` : `a[(haut + k) % 512]` (même repli que l'interface d'origine, qui lit `(102 + k + (y & 0x1ff)) % 512`) ; le bas du canevas reprend au début au lieu de donner des lignes vides. Défilement négatif et réglages incohérents : inchangés.
- `tests/test_message_repli.py` (9 tests, dans la CI, moteur factice) ; 2 échouent sur l'ancien code.

### Non vérifié
Le repli en jeu réel (il faudrait retirer `ui_layout.json` du cache) ; Windows.

## Avance #234 : bilan de l'audit complet, documents d'audit mis à jour, décisions du sondage (#233, 04/11/2026)

### Demande (14 h 52)
Relire tout le jeu d'origine contre le portage, corriger ce qui est mal fait ou inachevé, ajouter ce qui manque, poser un sondage pour ce qui touche à tes choix.

### Fait
- Neuf domaines relus (moteur, cartes, sprites, services, interface, son, Unity, combat) ; chaque écart net a eu son issue et sa PR (`docs/audit/rapport_reste_a_faire.md`, section « Audit complet du 04/11/2026 »).
- `docs/audit/lacunes_connues.md`, `couverture.md`, notes techniques : statuts périmés mis à jour (poker, machine à sous au clavier, bestiaire, teinte, poses couchées, véhicules, générique de fin = groupe 8).
- Tes réponses au sondage (4 séries) sont dans la section « Décisions du sondage du 04/11/2026 » du rapport ; elles décident des prochaines issues (focus, zoom des scènes, ballon, ciel, volumes, temps de jeu, générique, `.dqs`).

### Non vérifié
Rien de nouveau côté code ; documents seulement.

## Avance #236 : pause du jeu et du son à chaque perte de focus de la fenêtre (#235, audit UNI-02 / SND-07, 04/11/2026)

### Demande
Sondage du 04/11/2026 : « Pause à chaque perte de focus ». Audit UNI-02 / SND-07 : l'original appelle `Sound.SystemPause` quand l'application perd le focus ; la visionneuse laissait le jeu et la musique tourner.

### Fait
- `fenetre/jeu.py` : `on_deactivate` (jeu gelé dans `_boucle`, `Son.perdre_focus(True)`, boutons de souris tenus relâchés : molette, croix à l'écran, bouton appuyé) et `on_activate` (son repris, horloge remise à zéro sans rattrapage, touches déjà tenues = pas de nouvel appui). Événements reçus avant la fin du chargement (`_pret`) : seul le drapeau est posé, `_boucle` met le son en pause dès qu'elle tourne.
- `son.py` : `Son.perdre_focus` (`hors_focus`) prioritaire sur l'écoute de la page Son (`_doit_pauser`) ; reprise : les échéances (jingle, bruitages) sont décalées de la durée de la pause. Un menu Paramètres qui suspend encore le jeu garde la pause après le retour du focus.
- `tests/test_perte_focus.py` (10 tests : 5 Son dans la CI, 5 faux Jeu en local) ; tous échouent sans le correctif.

### Non vérifié
Windows : Alt + Tab, minimisation, plein écran, page Son ouverte pendant l'Alt + Tab. Le clic qui redonne le focus agit comme un clic de jeu (comme avant).

## Avance #238 : volumes des sons d'après snd_vol.dat (#237, audit SND-01, 04/11/2026)

### Demande
Sondage du 04/11/2026 : « Aligner sur l'original » (audit SND-01).

### Fait
- `son.py` : `Son.vol_snd(ident)` lit `assets/sound/snd_vol.dat` (1171 flottants, little-endian) à la première utilisation ; `_lancer_bgm` et `_lancer_se` jouent `en-tête x snd_vol` comme volume propre (`bgm_propre`, `_SE.propre`), donc un changement de curseur ou d'option plus tard garde le facteur. Table absente, indice hors table ou valeur absurde (0, > 1, nan, négatif) : 1,0. Cache disque des sons inchangé (le facteur est appliqué à la lecture).
- Valeurs relues sur le vrai APK : BGM01 0,7 ; BGM02 0,8 ; BGM14 et BGM20 1,0 ; BGM21 et BGM22 0,8 ; SE0409 0,6 ; SE0300 et SE1170 1,0.
- `tests/test_son_volumes.py` (9 tests, dans la CI, faux APK et faux lecteurs).
- `docs/audit/lacunes_connues.md` G-047 et notes techniques mises à jour.

### Non vérifié
Écoute sur Windows.

## Avance #240 : temps de jeu de la sauvegarde sur l'heure réelle (#239, audit ENG-04, 04/11/2026)

### Demande
Sondage du 04/11/2026 : « Recaler sur l'heure réelle » (audit ENG-04).

### Établi
`Global::NativeExec` (+ 0x14 : `mov w1, #2` ; + 0x20 : `bl` du stub PLT 0x227d90, dont la case 0x240968 contient `GameStatus::addPlayTime`) ajoute 2 unités (1/60 s) par pas du moteur à `status::g_Game + 4`. L'historique lit le même compteur.

### Fait
- `noyau/moteur.py` : `_crochets_temps_de_jeu` (installé avec les autres crochets) ; avant la pose, on relit l'instruction `mov w1, #2`, le `bl`, les 4 instructions du stub et la case de la table des adresses ; sinon `crochets_manques` le dit. `vitesse_horloge` > 1 : l'appel est sauté (retour à l'instruction suivante) pour la fraction 1 - 1 / a des pas, régulièrement (`Passeur`, comme les rencontres et la nuit) ; x1 ou ralenti : le jeu d'origine à l'identique.
- `fenetre/jeu.py` : `Jeu._boucle` écrit `moteur.vitesse_horloge = f` (marche ET combat ; `vitesse_marche` reste réservé à la marche).
- `tests/test_temps_de_jeu.py`, `tests/test_crochets_manques.py` (installateur ajouté).

### Non vérifié
Windows, partie réelle ; le budget de calcul des pas rapides (`BUDGET_PAS_RAPIDES`) peut faire moins de pas que prévu : le temps de jeu retarde alors un peu.

## Avance #242 : liste blanche de classes pour les états instantanés (#241, audit ENG-05, 04/11/2026)

### Demande
Sondage du 04/11/2026 : « Liste blanche de classes » (audit ENG-05).

### Établi
Un `.dqs` est lu par `pickle` (`etats.lire` pour le conteneur externe, `appliquer` pour les parties `python` et `viewer`) : un fichier fabriqué exécute du code Python au chargement (charge inoffensive écrivant un fichier témoin, audit). Le portage importe des ZIP de sauvegardes (`sauvegardes.importer`) : un état reçu est un vecteur.

### Fait
- `persistance/etats.py` : `CLASSES_AUTORISEES` et `_Depickler.find_class` ; les anciens noms de modules sont traduits d'abord (`ANCIENS_MODULES`), la liste blanche s'applique ensuite. Autorisés : `dq4_pc.noyau.moteur.Etat` et `Interface`, les types de base (`list`, `dict`, `set`, `bytearray`...), `OrderedDict`, `defaultdict`, `deque`, `numpy.dtype` / `ndarray` et les fonctions de reconstruction des tableaux (`numpy.core` et `numpy._core`). Relevé fait sur de vrais états (ville, carte du monde, combat) : rien d'autre. Un nom pointé du protocole 4 (`os.system` pris dans un module autorisé) est comparé en entier : refusé.
- Refus : `UnpicklingError` avec un message en français qui donne le nom demandé ; rien n'est exécuté ; `appliquer` refuse avant d'écrire dans le moteur (#206). Les écrans qui chargent un état affichent déjà l'erreur (toast, page des états).
- `tests/test_etats_liste_blanche.py` (15 tests ; pièges `os.system`, `eval`, `exec`, `open`, `__import__`, `getattr`, `subprocess`, `shutil`, `numpy.save` / `load`, `Moteur`, `CoreJeu`, noms pointés, fichier complet piégé, conteneur externe piégé).

### Non vérifié
Un vrai état d'une ancienne version (le dossier `etats\` de ta machine est vide) ; les états d'avant #206 sans empreinte de bibliothèque suivent le même chemin.

## Avance #244 : zoom des scènes : le jeu l'emporte, transition vers 100 % au début de la scène

### Demande
Sondage du 04/11/2026 (audit UNI-08) : « le jeu l'emporte dans ses scènes, et lors du début de la scène il faut faire un effet de transition pour remettre le zoom par défaut, comme quand on veut réinitialiser le zoom actuellement au clavier ou à la souris ».

### Établi
Avant : le zoom commun (`HEROS_FRAC`) annulait les travellings / gros plans de scène obtenus par la distance ou le fov, et le zoom du joueur s'appliquait aussi quand le jeu tenait la caméra.

### Fait
- Une scène = le jeu tient la caméra : `cam_jeu` (verrou TownCamera mené ailleurs que sur le joueur) ou caméra libre (paquet 11 bit 7), dans une ville / un donjon / une tour, jamais l'écran-titre.
- Début de scène (`_suivre_scene`, à chaque pas du moteur) : retour animé du zoom à 100 % (`dist_retour` + `dist_scene`), même animation et même vitesse que la remise à zéro (#167) ; il va à son terme sous un message, continue après la scène, s'arrête sous le menu Echap ou hors terrain. Le zoom reste à 100 % ensuite.
- Pendant la scène : `_zoom_possible` est faux (molette, touches, Ctrl + molette sans effet).
- Cadrage : `cam_scene_w` (0 = zoom commun, 1 = champ du jeu), `CAM_SCENE_TAU` = 6 / s (~0,4 s pour 90 %), immédiat après une coupure ; zoom commun et champ du jeu coïncident à la distance habituelle (`HEROS_FRAC` est calculé dessus).
- Inchangé : caméra libre, mini-jeux, titre (déjà sans zoom du joueur).
- `tests/test_zoom_scene.py` (20 tests).

### Non vérifié
Une vraie scène à l'écran (ton jeu sur Windows) ; les scènes où le jeu change seulement le fov sans verrouiller la caméra restent au zoom commun (à mesurer).

## Avance #247 : alerte de la mémoire du moteur (tas de 256 Mo, 200 Mo puis 240 Mo)

### Demande
Audit du 04/11/2026, ENG-01 : le tas du moteur n'est jamais libéré ; choix par discernement (le sondage ne portait pas dessus).

### Établi
`Core.malloc` avance un pointeur dans un tas de 256 Mo, `h_free` et `h__ZdaPv` ne font rien. Mesures de l'audit : 0 octet par pas au repos, 36 Ko par chargement de carte, 0,53 Mo par combat ; extrapolé : 480 combats environ avant l'arrêt.

### Fait
- `Core.tas_utilise()`, `TAS_ALERTE` = 200 Mo, `TAS_CRITIQUE` = 240 Mo.
- `Jeu._surveiller_tas` (à chaque pas du moteur) : à 200 Mo « Mémoire du moteur à 78 % : pense à fermer puis relancer le jeu », à 240 Mo « Mémoire du moteur presque pleine (94 %) : sauvegarde et relance le jeu maintenant » ; une fois par palier, ligne dans `erreurs_fenetre.log`, réarmé si le tas redescend (chargement d'un état).
- Pas de sauvegarde écrite par l'alerte : `data5` (sauvegarde automatique du jeu) est écrite à chaque arrivée sur une carte ; un état `.dqs` rechargerait le même tas plein.
- Non fait : allocateur à listes libres (taille M, change le moteur d'origine).
- `tests/test_alerte_tas.py` (6 tests).

### Non vérifié
Un tas réellement proche de 200 Mo (heures de jeu) ; le message tel qu'il s'affiche à l'écran.

## Avance #248 : poker : « Abandonner » tient dans ses boutons (police réduite)

### Demande
Audit du 04/11/2026, SVC-03 : « Abandonner » dépasse de son bouton au poker ; décision de Sylfried (sondage antérieur) : **police réduite**.

### Établi
Scénario de l'audit relancé sur le code actuel (touches simulées jusqu'au choix des cartes à garder) : cinq plaques de 72 unités sous les cartes, « Abandonner » plus large (chevauchement avant correction). `_texte` comprimait un texte trop large seulement avec la police de repli ou si le nœud portait `fit_x`.

### Fait
- `comprimer_etiquette(police_origine, fit_x, type_fenetre)` (fonction pure) et `TYPES_COMPRESSION_BOUTONS = (48,)` : les étiquettes de la fenêtre du poker sont comprimées en largeur pour tenir dans leur plaque (marge 7 unités de chaque côté, compression minimale 0,7).
- Vérifié à l'écran avant / après (800 x 450) : les cinq étiquettes tiennent, « DONNER » aussi.
- Inchangé : les autres fenêtres gardent leurs débordements (décision UI-05).
- `tests/test_poker_police.py` (4 tests).

### Non vérifié
Rendu à d'autres tailles de fenêtre (la compression est proportionnelle) ; le poker en jeu réel côté Windows.

## Avance #250 : ciel prolongé sur dpout et ev09 (plus de coins noirs en 16/9)

### Demande
Audit du 04/11/2026, MAP-05 : les plans de ciel de `dpout` et `ev09` s'arrêtent avant les bords de la fenêtre en 16/9 ; décision de Sylfried (sondage) : **prolonger le ciel**.

### Établi
Rendu du moteur réel (1280 x 720) avant correction : `ev09` a un grand coin noir à gauche, `dpout` deux coins noirs. Plans concernés : objet `002_dpoutenk` (groupe 11768, 72 sommets, x de -20 à 20, plan plat z = 40) et `000_e9km1` (groupe 14511, 180 sommets, x de -9,1 à 17,9). `ev02` : pas de coin noir, non concernée.

### Fait
- `CIELS_ETENDUS` (constantes) : cartes et mots-clés des plans ; `TitreMixin._ciel_etendu` : pour chaque plage du plan, deux copies symétriques (par rapport à `xmin` et à `xmax`), mêmes coordonnées de texture et couleurs, ajoutées à `carte_ext` ; `champ.py` les met à jour comme les copies du titre.
- `ciel_titre.positions_copie(cur, dx)` : décalage (titre) ou `('miroir', xe)`.
- Vérifié à l'écran avant / après : plus de coin noir sur `ev09` ; `dpout` prolongé des deux côtés.
- `tests/test_ciel_etendu.py` (6 tests).

### Non vérifié
Rendu à d'autres tailles de fenêtre / formats (21:9) ; l'aspect du miroir en pleine partie sur Windows ; scènes qui déplacent la caméra sur ces cartes.

## Avance #252 : carte du monde en ballon : échelle du terrain du jeu (paquet 30) et ballon flottant

### Demande
Audit du 04/11/2026, MAP-02 / UNI-05 / SPR-06 : le paquet 30 (`field_scale`) était ignoré ; décision de Sylfried (sondage) : **reproduire l'original** (échelle du jeu × ton zoom).

### Établi
Désassemblage : `cmd_field_scale` (D12794) : entier ≥ 0 = `Field.SetFloatingObject(Chara.m_chara de cet emplacement)`, entier < 0 = `Field.SetScale(flottant)` ; `Field.SetScale` (CD353C) règle `Camera.orthographicSize = taille d'origine × échelle` puis `FloatingObject.SetScale(échelle)` (CD3708 : `localScale = échelle de départ × échelle`) sur chaque objet flottant, donc le panneau du ballon garde sa taille à l'écran quand le terrain est vu de plus loin (son ombre, transform séparé, non). Personne n'appelle `RemoveFloatingObject` (balayage de libil2cpp). Moteur lancé sur la sauvegarde 4 : à l'entrée sur la carte du monde, `(27, [1])` puis `(30, [12])` (image 31) : le ballon (emplacement 12) est toujours enregistré ; l'échelle `[-1] [1,25]` ne sort qu'en vol (relevé de l'audit, drapeau 344 forcé).

### Fait
- `Etat.champ_echelle` et `Etat.flottants` (attributs de classe : un état instantané enregistré avant #252 reste valide), mis à jour par le paquet 30, remis à 1 / vide au paquet 0 (carte) et 27 (carte du monde) ; échelle bornée à 0,25 - 4 (le moteur n'envoie que 1,00 à 1,25), valeurs absentes, nulles, négatives, NaN, infinies ignorées.
- `_camera_champ` : hauteur visible × `champ_echelle`, par-dessus le zoom du joueur.
- `jeu.py` : sur la carte du monde, un sprite flottant est agrandi de `champ_echelle` (pieds fixes).
- Vérifié à l'écran (moteur réel, 1280 x 720, ballon injecté à l'échelle 1,25 sur la sauvegarde 4, avant / après) : le terrain montre 25 % de terrain en plus (symboles de lieux et décor à 0,8 de leur taille), l'enveloppe du ballon garde sa taille (45 → 48 px, aux arrondis du pixel près).
- `tests/test_ballon_echelle.py` (10 tests, dans la CI ; les 3 de la caméra sont ignorés là-bas faute de pyglet).

### Non vérifié
Un vol réel (la montée, la descente, l'échelle qui varie d'une image à l'autre) : les sauvegardes sont au chapitre 1. Le comportement exact de `Field.Init` sur la liste des objets flottants (la liste est vidée ici à chaque chargement de la carte du monde ; le moteur réenregistre le ballon juste après). Le comportement en pixel perfect (la caméra reste calée sur les pixels de la carte, l'échelle 1,25 n'est pas entière).

## Avance #254 : effet sépia des retours en arrière (paquet 1) sur le décor des villes

### Demande
Audit du 04/11/2026, UNI-04 / MAP-04 : le paquet 1 (effet sépia des retours en arrière) était ignoré.

### Établi
`cmd_map_effect_sepia` (5 scripts : `ccf2 ceout cmf3b ev07 srout`) envoie le paquet 1 sans argument ; `FldObject.calculateExecSepia` (CDD9E0) remplace, pour chaque matériau du décor, le shader par `<nom>_sepia` (jamais retiré avant le prochain chargement de carte) ; les personnages et les menus ne sont pas touchés. Shader `Custom/fld_normal_sepia` (GLSL ES du paquet de données) : `gris = dot((0,299 ; 0,587 ; 0,114), texture × couleur de sommet × _Color)`, sortie `gris + (0,109375 ; -0,0546875 ; 0)`, alpha inchangé (la teinte rosée en découle : le décalage ajoute du rouge et retire du vert).

### Fait
- `Etat.sepia` (attribut de classe : un état instantané enregistré avant #254 reste valide) : vrai au paquet 1, faux au paquet 0.
- Shader du décor : uniforme `sepia` (formule du jeu, avant l'écriture bornée) ; `_tracer_decor` le règle pour tout le décor et le remet à 0 ensuite. `DQ_SANS_SEPIA=1` : (débogage) jamais de sépia.
- Vérifié à l'écran (moteur réel, 1280 x 720, `ceout` et `ccf2`, drapeau forcé, avant puis après) : décor entièrement en gris rosé, ciel de fond (BackColor), fenêtre de message et sprites inchangés.
- `tests/test_sepia_decor.py` (6 tests).

### Non vérifié
Un vrai retour en arrière joué par le script (quand l'effet commence et finit) ; les matériaux `fld_transz` (le jeu n'a pas de variante sépia : le port les passe en sépia comme le reste) ; la carte du monde (pas de FldObject : non concernée).

## Avance #256 : effets d'écran du voyage, de la lampe et de Riremito (paquet 34, valeurs 3, 5, 6)

### Demande
Audit du 04/11/2026, UNI-06 : le paquet 34 ne rejouait que la valeur 4 (début de combat) ; voyage / ailes de Chimère (3), lampe « Ranaruta » (5) et Riremito (6) n'avaient aucun effet, et le moteur n'attendait pas leur fin.

### Établi
Trois coroutines de la classe `Capture` (`<Tabi>d__49`, `<DarkLamp>d__47`, `<Riremito>d__48`), avancées d'un pas par `LateUpdate` (30 Hz) : capture de l'écran du jeu sans interface, passe de flou (l'état de l'image précédente redessiné dans l'une de deux textures de demi-résolution), un `MoveNext`. Durées : 64 appels (voyage, départ), 45 (arrivée, bit 7), 64 (lampe), 63 (Riremito) ; aucun `Random`, aucune horloge. Voyage et lampe : sommets, couleurs et champs comparés au vrai code machine sous Unicorn, identiques au bit près ; Riremito relu à la main. La lampe et Riremito rendent l'écran noir d'un coup (appels 63 et 62) ; le départ d'un voyage laisse l'écran noir ; l'arrivée lance un fondu d'entrée de 30 images à l'appel 3 et rend la scène à l'appel 45.

### Fait
- Modules purs `rendu/effets_capture.py`, `effet_tabi.py`, `effet_lampe.py`, `effet_riremito.py`.
- `Moteur._debut_effet_ecran` / `_effet_ecran` : bit 1 levé puis abaissé après la durée de l'effet (suit « Vitesse de transition »), noir immédiat (`Etat.fondu_noir_net`), `Etat.ecran_noir` entre le départ et l'arrivée (borné à 60 s ; levé au retour au titre), fondu d'entrée (`Etat.fondu_entree_courant`). `Etat.effet_ecran` et `Etat.ecran_noir` : attributs de classe.
- `fenetre/effets_capture.py` (`EffetsCaptureMixin`) : capture, deux textures de flou, dessin ; `jeu.py` l'appelle depuis `_dessiner_scene` ; commandes, caméra et boutons tactiles bloqués pendant l'effet.
- Vérifié à l'écran (moteur réel, 1280 x 720, carte `caf1`, image par image) : lampe nuit et matin, Riremito (noir net à l'appel 62), voyage (départ, noir, arrivée, scène normale au dernier appel).
- `tests/test_effets_capture.py` (21 tests).

### Non vérifié
L'aspect exact face à l'original (aucune capture de référence) ; le contenu initial des textures de flou (noir supposé) ; l'interface dessinée par-dessus l'effet (supposé) ; le tourbillon du voyage, elliptique en 16/9 (le maillage est en coordonnées d'écran normalisées) ; 28 et 14 rangées gardées comme sur mobile (le jeu en calcule moins en 16/9) ; la cadence de 30 Hz ; la capture contient la vignette et le fondu du fond ; la durée réelle de l'effet de début de combat (57 images dans le port, non revérifiée).

## Avance #258 : un seul lancer_dq4.bat (celui de dq4_pc supprimé)

### Demande
Remarque de Sylfried (04/11/2026, 20 h 31) : deux fichiers `lancer_dq4.bat` dans le dépôt.

### Établi
La PR #197 avait laissé `dq4_pc\lancer_dq4.bat`, un fichier de deux lignes qui appelle le vrai lanceur de la racine (pour d'éventuels anciens raccourcis). Le sondage D-237 demandait pourtant « un seul `lancer_dq4.bat` à la racine ; `dq4_pc\` ne contient plus que du code », et le README comme `docs/plan_du_code.md` annonçaient « le seul lanceur » : c'était le seul fichier non code de `dq4_pc\` suivi par git. Écart avec ton choix, laissé par moi.

### Fait
- `dq4_pc\lancer_dq4.bat` supprimé ; table « ancien nom → nouveau » de `docs/plan_du_code.md` corrigée. Le vrai lanceur (racine), les tests et la CI ne l'utilisaient pas.
- Vérifié : aucun autre fichier non code suivi dans `dq4_pc\` ; plus qu'un `lancer_dq4.bat` suivi par git.

### À savoir
Un raccourci Windows qui pointait vers `dq4_pc\lancer_dq4.bat` est à refaire vers `lancer_dq4.bat` à la racine. Sur le PC de test, la suppression passe par `git pull` (tracé par git).

## Avance #260 : ménage : jeux, test_faisabilite et vieux fichiers supprimés du PC

### Demande
Sylfried (04/11/2026, 20 h 57 et 20 h 58) : supprimer `jeux\`, les deux fichiers non suivis et les fichiers et dossiers de test inutiles, « de partout ».

### Établi
- `test_faisabilite\` (`lancer_test.bat`, `test_core.py`, `rapport_test.txt`, 44 Ko) : le premier essai du 30/10 (verdict « réussi : le moteur du jeu s'exécute sur PC, sans Unity ») ; `dq4_pc\noyau\emu_core.py` en est la suite, aucun test ni script ne l'appelle ; le dossier n'a jamais été suivi par git.
- `dq4_pc\echantillons_message.npz` et `outils\ui_il2cpp\grande_pile.py` : non suivis, plus référencés dans le code (recherche dans tout le dépôt).
- `jeux\` : au moment de la demande, `donnees\` venait d'être créé par le premier lancement du nouveau lanceur (19 h 58) ; `jeux\` n'a été supprimé qu'après comparaison octet à octet des 3 APK et des 7 fichiers de sauvegarde du mobile avec `donnees\apk` et `donnees\sauvegardes\mobile`.
- Gardés : `tests\` (91 fichiers, la suite de la CI), `outils\flux_session\`, `outils\recherche\`, le modèle d'issue `test_windows`, `docs/audit/plan_tests_chapitre2.md`.

### Fait
- Sur le PC : les quatre suppressions ci-dessus ; `git status` propre ensuite.
- Dépôt : ligne `test_faisabilite/` retirée du `.gitignore` ; mention des notes techniques complétée.

### Non vérifié
Que le jeu démarre jusqu'au bout sous Windows avec le nouveau lanceur (le premier lancement du 04/11 à 19 h 58 a bien repris les fichiers, mais je n'ai pas vu la suite) ; `dq4_pc\sauvegardes`, `dq4_pc\reglages.json`, `dq4_pc\historique_*.json` et `dq4_pc\erreurs_fenetre.log` (anciens doublons) laissés en place.

## Avance #262 : le don d'expérience du roi ne fige plus le jeu (toucher d'écran 0x100)

### Demande
Signalé par Sylfried le 04/11/2026 (21 h 15) : au chapitre 1, quand le roi de Burland donne de l'expérience à Ragnar, le jeu se fige au dernier message de statistiques (niveau 15) ; plus rien ne répond (ni clic, ni toucher, ni Espace), seul Échap ouvre « Paramètres ». Recharger la sauvegarde automatique reproduit le blocage. Il a demandé de corriger pour tout le jeu.

### Établi
- Reproduit sans fenêtre avec sa sauvegarde automatique et ses réglages (carte `caf1`) : bloqué indéfiniment, avec ou sans ses réglages ; une version d'avant #232 bloque aussi (cadre vide).
- Le moteur ne s'est pas arrêté : le message est fini (`ui_MsgLoop` à l'état 6), c'est le menu `MaterielMenu_EXTRA_PRESENT_EXP` (don d'expérience, ajout du mobile) qui attend, à son dernier état (`+0x30` = 2), que `dss::g_Pad + 2` soit non nul. `Global::NativeExec` remplit cette valeur d'après le 2e argument de `GameUpdate` : bits 10 à 13 -> 0x20 / 0x40 / 0x80 / 0x400, et 0x10 seulement quand l'argument vaut **exactement** 0x100 (le toucher d'écran). La touche A pendant un message envoie 0x10 (utile à `ui_MsgLoop`), jamais lu par ce menu.
- Essai sur le moteur bloqué : 0x100 ou 0x400 le libère aussitôt (le menu se ferme, le dialogue du roi suit), 0x110 non.
- Revue de tout le jeu : 17 fonctions lisent `g_Pad + 2`, 8 lisent le 2e argument tel quel (« non nul »). Seul ce menu bloquait : casino (machine à sous, poker, arène) = accélération des gains seulement, fenêtres de ville et de carte = boutons du portage, crédits, compteurs et messages = « non nul ».

### Fait
- `Moteur.attend_toucher` : vrai quand le menu est dans le tableau de `MenuManager` ET à son dernier état (l'état reste à 2 après la fermeture, d'où le test du tableau).
- `entrees.toucher_pour_le_moteur` (logique pure) et un branchement dans `Jeu._entrees` : message ouvert + menu en attente + A (touche, clic, Entrée, Espace) -> 0x100 seul (ni A ni B). Rien ne change le reste du temps.
- Vérifié sur le vrai moteur (sa sauvegarde automatique, ses réglages) : `attend_toucher` faux, vrai à 2300 images, faux dès l'appui ; la scène enchaîne « Faites attention à vous, McRyan. », la fin du chapitre 1, la proposition de journal puis le chapitre 2.
- `tests/test_don_exp_toucher.py` (13 tests : détection du menu avec une mémoire simulée, conversion, modèle de `NativeExec`, branchement) ; ajouté à la CI.
- Non vérifié : l'accélération des gains du casino par un appui (G-217).

## Avance #264 : Caméra du jeu, telle quelle : plus de zoom, de rotation ni d'inclinaison du joueur

### Demande
Sylfried (04/11/2026, 22 h 14), après avoir signalé un problème au début de la cinématique où les compagnons le rejoignent : « Reviens au fonctionnement de base de la caméra. Supprime le zoom / dézoom, le fait de changer d'angle [...] tu reviens au comportement EXACT du jeu. »

### Fait
- La caméra des villes, donjons et tours est celle du jeu telle quelle : `SceneCamera.Update` (position, cible, `LookAt`, tangage - lookDownAdjust, avance de distanceAdjust, décalage vertical, rotation libre des scènes) avec le champ horizontal fov x 4/3 et la hauteur de champ de l'écran portrait d'origine (donc plus de décor sur les côtés en 16/9). Plus de centrage sur le héros (la cible bornée du jeu fait foi aux bords de la carte), de lissage de hauteur (escaliers), de reste qui glisse au changement de régime, de mélange scène / joueur ni de taille du héros imposée (« zoom commun »).
- Retirés : zoom / distance (molette, touches, menu, `--carte-zoom`), rotation et inclinaison (flèches, clic molette), recentrage animé, remises à zéro (Ctrl), inversions de la souris, « Vitesse de caméra ». Les flèches ne servent plus que dans les menus ; la molette sert au menu Échap et à la licence.
- Carte du monde : la hauteur visible est celle du jeu (échelle du ballon comprise), sans zoom du joueur.
- Réglages : clés retirées placées dans `CLES_OBSOLETES` (un ancien `reglages.json` se lit, les clés ne sont pas réécrites).
- Tests : `test_camera_ville.py` réécrit, trois fichiers supprimés (`test_camera_ctrl_tout`, `test_distance_camera_clavier`, `test_zoom_scene`), dix adaptés (`test_camera_titre`, `test_ballon_echelle`, `test_entrees`, `test_ecrans`, `test_pause_pages`, `test_perte_focus`, `test_priorite_jeu`, `test_reglages_interface`, `test_reglages_son_texte`, `test_sprites_droits`).

### Établi
- Rendu avant / après du départ de la carte `cbout` (toits de Burland) : 29 pixels sur 921 600 diffèrent.
- La caméra ne dépend plus que de l'état envoyé par le moteur (test : même image quel que soit le héros ou l'historique).

### Non vérifié
- La scène des compagnons au début du chapitre 2 et le comportement aux bords de carte sous Windows. Barre de rotation de la caméra du mobile (G-103) : toujours non reproduite, et plus de rotation à la main.

## Avance #266 : Historique : un favori de dialogue garde la clé du message, plus son texte

### Demande
Sylfried (04/11/2026, 22 h 14) : « Dans l'historique des textes, est-ce que c'est le contenu du texte qui est sauvegardé ou la clé ? Si ce n'est pas le cas, il vaudrait mieux que ça soit la clé qui va chercher le contenu directement dans les fichiers du jeu [...] ça évitera de stocker l'ancien texte en cas de mise en favori. »

### Établi
- Avant : le **texte** (nettoyé) et le nom du locuteur étaient enregistrés ; aucune clé n'était captée.
- Le numéro du message est le premier argument de `ui_MsgAdd` ; `TextBuffer::cat` en est appelée directement (pile relevée sur le vrai moteur). Numéro 802199 = `b0802000#199`.
- `TextAPI::extractText(tampon, (1 << 24) | numero)` donne le texte des fichiers du jeu (0,13 ms) : sauts de page « ㈡ » et variables « [NONE 1,0] » conservés ; le moteur choisit seul les variantes selon la partie (sexe du héros).
- Sur le vrai moteur (prologue, 10 messages dont 3 injectés avec pages et variables) : étoile -> fichier sans texte ; relu dans un second moteur : même texte ; réponse du moteur modifiée : le favori suit.

### Fait
- Crochet `ui_MsgAdd`, `Capteur.modele`, fonctions `cle_message`, `valeurs`, `liaison`, `texte_lie`, favoris `lie` / `attente`, `Historique._lier`, `_resoudre`, `actualiser` (appelée à l'ouverture de l'historique).
- Garde-fou : la clé n'est utilisée que si le texte des fichiers redonne exactement le texte lu ; sinon le favori garde son texte. Message disparu : ligne « Message introuvable... » avec la clé.
- Anciens favoris lus comme avant (fichier de Sylfried : 0 favori).

### Supposé / non vérifié
- Messages à variables lus en vrai pendant le jeu : seulement avec un faux moteur (injectés, les variables restent « [NONE 1,0] »).
- Variantes selon le sexe du héros : elles suivent la partie en cours à l'ouverture de l'historique.
- Le nom du locuteur reste enregistré.

## Avance #268 : plus aucune notification en haut de l'écran (D-228)

### Demande
Sylfried (04/11/2026, 22 h 14) : « Enlève le message de notification en haut de l'écran pour le changement de vitesse quand on est hors combat, toutes les notifications tout court finalement, celles qui apparaissent en haut de l'écran. »

### Fait (D-228)
- `Jeu.toast`, `Jeu.toasts` et le dessin du bandeau noir en haut de l'écran n'existent plus. Les appels supprimés : changement de vitesse de combat hors combat (touche), états instantanés (enregistré, chargé, vide, annulé, échecs), sauvegardes importées, ouverture d'un dossier impossible (écran-titre), plein écran / fenêtre impossible, sauvegarde impossible (#198), mémoire du moteur à 78 % et 94 %, réglages du moteur non appliqués, interruption du son (le crochet `alerte` de `son.py` reste mais n'est plus branché).
- Les cas d'erreur gardent leur trace sans rien afficher : console et `erreurs_fenetre.log`. L'échec d'un état instantané passe par `Jeu._noter_echec_etat`.
- Tests adaptés : `test_historique_acces`, `test_alerte_tas`, `test_mode_fenetre`, `test_ecrans`, `test_ecriture_sauvegarde`, `test_crochets_manques`, `test_vitesse_combat`. Nouveau `tests/test_sans_notifications.py` (aucun mot `toast` dans `dq4_pc` ; l'échec d'état va au journal), ajouté à la CI.

### Non vérifié
- À regarder sur Windows : plus aucun message en haut de l'écran (touche de vitesse hors combat, états 1-9, import de sauvegardes).
- Un avertissement de mémoire du moteur ou un échec d'écriture de sauvegarde n'est plus visible à l'écran : à rétablir sur demande.

## Avance #270 : historique : la police et la coupure des messages du jeu

### Demande
Sylfried (04/11/2026, 23 h 02) : dans l'historique « certains caractères ne fonctionnent pas » (capture : n et r absents du texte du Tsar Stepan) ; « peux-tu utiliser le même moteur qui affiche les messages en temps normal pour les afficher ici ? ». À 23 h 11 : ce ne sont pas les seuls caractères spéciaux, il y en aura d'autres dans DQ5 et DQ6.

### Cause (établi)
Le patch écrit les n et r du Tsar avec `и` et `я`. Le jeu les dessine avec sa police de messages (`assets/English.font`) ; l'historique utilisait la police de menu SE-GARRIR, qui n'a pas ces glyphes.

### Fait (D-229)
- `dq4_pc/menus/police_messages.py` (nouveau, sans pyglet sauf pour la texture) : lecture du fichier de police du jeu (format TNOF : en-tête de 28 octets, table de 65 536 entrées, glyphes compressés), tous les glyphes, aucun caractère écrit dans le code. Copié dans le cache sous `ui_messages.font` au démarrage (`preparer_ressources`, une seule fois).
- Placement du moteur (`SDrawCTRL::PutChar`, `TextCanvas::PutChar`) : avance = largeur du glyphe ; glyphes à drapeau (V, W, t, v, w, y) posés un pixel plus à gauche et avançant de deux pixels de moins ; espace de 6 (celle du moteur, pas celle de la police) ; tabulation 15 ; `;` et `$` non dessinés (langue 1) ; un code absent de la police prend le glyphe du `@` (comme le jeu). L'image est une pose de glyphes sans mélange, comme le canevas du moteur : 1 unité d'interface par pixel du canevas.
- Coupure des lignes du moteur (`CTextAutoReturn::AutoReturn`, limite 410) : `PoliceMessages.couper`. Les pages et les lignes de l'historique sont donc celles de la boîte de dialogue.
- `ui_historique.py` : corps du texte et en-tête des combats avec cette police (nom du locuteur, onglets, aide : SE-GARRIR comme avant) ; la mise en page de la boîte (`Boite`) est inchangée.
- Sans la police (paquet de données absent ou illisible) : repli sur SE-GARRIR, avec un message dans la console.
- `tests/test_police_messages.py` (27 tests) : 22 sans moteur (CI) sur une police synthétique ; 5 contre le vrai moteur sous Unicorn : pixels de `PutChar` identiques pour des phrases françaises, les lettres russes et les glyphes à drapeau, pour les 221 glyphes de la police, coupure identique à `AutoReturn` sur un échantillon de ~400 messages du jeu et sur des cas construits (`$`, `;`, tirets, espaces larges, mot trop long). Contrôle des tests : changer l'espace à 5, supprimer le crénage, la limite à 400 ou la largeur de `$` fait échouer les comparaisons.

### Établi / supposé / non vérifié
- Établi : 0 pixel de différence avec le canevas du vrai moteur pour tout ce qui précède ; rendu de l'historique vérifié sur une capture (n → `и`, r → `я`, mêmes lignes que la boîte de dialogue).
- Supposé : DQ5 et DQ6 utilisent le même format de fichier de police (le code ne connaît aucun caractère : si le format change, la lecture échoue avec un message clair et le repli SE-GARRIR prend le relais).
- Non vérifié : rendu sur Windows.

## Avance #273 : notifications de sauvegarde rétablies

### Demande
Sylfried (04/11/2026, 23 h 02) : « Remets les notifications pour les sauvegardes alors... » (D-228 / #268 avaient retiré toutes les notifications du haut de l'écran).

### Fait (D-230)
- `Jeu.toast`, `Jeu.toasts` et le dessin du bandeau noir en haut de l'écran sont de retour, **pour les sauvegardes seulement** :
  - états instantanés : « État N enregistré » (touche chiffre), « État N chargé » et « État N vide » (Ctrl + chiffre), « Chargement annulé », « Aucun chargement à annuler » (Ctrl + Maj), « <Enregistrement|Chargement> de l'état N impossible : … » (en plus de la console et du journal, ajoutés par #268) ;
  - « Sauvegarde impossible : le jeu continue (détails dans erreurs_fenetre.log) » (6 s) quand le moteur n'a pas pu écrire une sauvegarde ;
  - « Sauvegardes importées » (retour de l'écran Sauvegardes après un import).
- **Restent retirés** (D-228 maintenu) : vitesse de combat hors combat, plein écran / fenêtre impossible, mémoire du moteur à 78 % et 94 %, réglages du moteur non appliqués, interruption du son (le crochet `alerte` de `son.py` n'est pas branché), ouverture de la page de confidentialité impossible : console et `erreurs_fenetre.log` seulement.
- `tests/test_sans_notifications.py` devient `tests/test_notifications_sauvegardes.py` : liste blanche (lecture du code par `ast` : chaque `toast(...)` est un message de sauvegarde, et chacun est utilisé), et comportement (le message expire, annuler le chargement, échec d'état dans la console, le journal et à l'écran, import, la vitesse de combat ne montre rien). `test_ecriture_sauvegarde` reprend son contrôle du message. Capture headless : « État 3 enregistré » en haut de l'écran.

### Non vérifié
- À regarder sur Windows : chiffre (enregistrer), Ctrl + chiffre (charger), Ctrl + Maj (annuler), import de sauvegardes ; la touche de vitesse de combat hors combat n'affiche rien.
- Choix de Claude : les avertissements de mémoire du moteur (qui préviennent d'un arrêt possible du jeu) sont restés retirés, car ils ne concernent pas une sauvegarde ; à rétablir sur demande.

## Avance #274 : Oui / Non empilés en haut à droite de la boîte de dialogue

### Demande
Sylfried (04/11/2026, 23 h 02, capture d'écran) : « Les options OUI/NON apparaissent par-dessus le nom du locuteur, je propose une variante qui copie le fonctionnement sur DS : tu les mets l'un sur l'autre posé sur le coin en haut à droite de la boîte de dialogue avec les bords droits alignés. »

### Fait (D-231)
- **Empilement** : `Fenetre._empiler_oui_non` (type 1, `Make_YesNo`, à la création) met la plaque « Non » sous « Oui » : même colonne (celle de gauche, x de -134,5 à -0,5), une unité entre les deux (l'espace qui séparait les plaques côte à côte). Le panneau droit du cadre, la plaque de droite et son texte sont déplacés d'un bloc ; les zones de clic et la sélection suivent les nœuds déplacés. Étendue de la fenêtre : de -10 à 87 (avant : de 39 à 87). Autre mise en page (pas deux plaques sœurs) : rien n'est touché. Le curseur du moteur rangeait déjà Oui / Non en une colonne (haut = Oui, bas = Non) : le clavier et la manette n'ont pas changé.
- **Pose** : la pile est posée sur le coin haut droit de la boîte de dialogue, **bord droit visible aligné** sur celui de la boîte, et **1 unité visible** au-dessus de son bord haut (avant : 4 unités entre les mailles, 8,5 visibles ; `OUINON_ECART` = 1). Elle suit toujours la boîte, à sa place d'origine ou descendue (avant : seulement quand la boîte était descendue).
- **Bords visibles, pas bords des mailles** : les cadres ont des marges transparentes différentes (6 unités à droite et 4,5 en haut pour la boîte, presque rien pour Oui / Non) ; `bords_visibles` les mesure dans la feuille du jeu (opacité > 127, `ALPHA_FEUILLES` posé par `Rendu` avant la dilatation), `Fenetre.etendue_visible` et `FenetreMessage.etendue_visible` donnent le dessin visible, `MenusMixin._ouinon_sur_message` en tire le décalage vertical et les deux bords droits. Mesuré sur une capture headless 1280 x 720 : bords droits de la boîte, de « Oui » et de « Non » tous à x = 862.
- **Éditeur d'interface** : les réglages de « Oui / Non » (taille, décalage) restent relatifs à la boîte de dialogue ; la taille se change autour du bord bas et du bord droit de la pile, de sorte que le coin ne bouge pas. L'aperçu montre la nouvelle disposition (cadre jaune = la pile). Sans boîte de dialogue, la pile garde sa place d'origine avec les réglages du joueur.
- `tests/test_oui_non_empile.py` (19 tests, dont 2 exécutés sans pyglet en CI, les autres passés s'il manque) : empilement sur une mise en page synthétique et sur la vraie (cache d'interface), étendues, zones de clic, autre mise en page intacte, `bords_visibles` (seuil, plusieurs cases, rien de visible), pose (bas et droite à toutes les échelles, réglage de position relatif, mesure manquante), branchement dans le code. Six mutations vérifiées (écart, déplacement vertical, déplacement du texte, signe de l'alignement, écart de pose, appel à la création).

### Non vérifié
- À regarder sur Windows : retour au titre, achat, suppression d'un état, tout dialogue à Oui / Non ; la pile est en haut à droite, ne cache pas le nom du locuteur ; flèches haut / bas, clic et manette choisissent Oui ou Non au bon endroit.
- Suppose (non vu en jeu) : les dialogues Oui / Non du combat se posent de la même façon (même chemin de code, boîte de combat descendue) ; les réglages déjà enregistrés pour « Oui / Non » dans l'éditeur s'appliquent maintenant au coin de la pile (valeurs relatives inchangées).

## Avance #276 : Un seul dossier de sauvegardes (data1 à data5, data9, etats)

### Demande
Sylfried (04/11/2026, 23 h 55) : « Tu ne pourrais juste pas stocker tous les fichiers directement dans le dossier "sauvegardes" ou un seul sous-dossier pour coller à la logique des états ? Comme ça si je veux transférer toutes les sauvegardes du mobile sur le patch je n'ai pas besoin de faire de gymnastique mentale à deviner quel fichier mettre dans quel dossier. »

### Fait (D-232)
- **Un seul dossier** : `donnees\sauvegardes\` contient `data1.dat` à `data5.dat`, `data9.dat`, `etats\` et les copies `avant_import_<date>\` : le contenu du .zip d'export. Le jeu y lit **et** y écrit ; `Dossiers.portage` est devenu un autre nom de `sauvegardes` (les états y étaient déjà : `sauvegardes\etats`). Transférer les sauvegardes du téléphone = copier ses `dataN.dat` dans ce dossier.
- **Reprise au démarrage** (`chemins._ranger_anciens_dossiers`, appelée par `migrer`, donc par le lanceur et par le jeu) : les journaux de l'ancien `sauvegardes\portage` (ce que le jeu écrivait, prioritaire) puis ceux de la copie du téléphone la plus récente (`sauvegardes\mobile\<date>`) sont **copiés** dans `sauvegardes\` sans rien écraser (c'est l'ordre dans lequel le jeu les lisait, fichier par fichier : la partie en cours ne change pas) ; puis `portage\` et `mobile\` sont **déplacés tels quels** dans `sauvegardes\avant_rangement_<date>\` (avec le `manifest.json` et les copies plus anciennes). Rien n'est supprimé. Une erreur (fichier ouvert...) laisse les anciens dossiers en place et le jeu lit déjà `sauvegardes\` ; la reprise suivante termine. Une seconde reprise ne fait rien.
- **Ordre de priorité** : la reprise du 04/11 passe **avant** celle de l'ancienne disposition (`dq4_pc\sauvegardes`, `jeux\DQ4\saves`), qui ne remplit plus que ce qui manque : le vieux `dq4_pc\sauvegardes` encore présent sur le PC de Sylfried ne doit pas passer devant ses fichiers du jour.
- `DQ4_JEUX` (copie du téléphone ailleurs, lue seulement) : sans effet, comme `--saves-lecture` pour les tests. `NOMS` (sauvegardes.py) vient de `chemins.NOMS_JOURNAUX`. Aides de `--saves-lecture` / `--saves-ecriture`, message « APK introuvables », `lancer_dq4.bat` (fins de ligne CRLF conservées), README, workflow, reprise et plan du code à jour.
- `tests/test_sauvegardes_un_dossier.py` (16 tests, sans pyglet : la CI les exécute) : disposition, reprise du cas réel (portage plus ancien que le téléphone, manifeste, vieux `dq4_pc`), rien d'écrasé ni perdu, seconde reprise vide, erreur de déplacement ou de copie, `DQ4_JEUX`, lecture par le moteur, export à plat = contenu du dossier. `test_chemins.py` adapté.

### Non vérifié
- À regarder sur Windows au premier lancement : le Continuer propose les mêmes journaux qu'avant ; `sauvegardes\` contient `dataN.dat` et `etats\` ; `avant_rangement_<date>\` contient `portage\` et `mobile\`.
- Chez Sylfried, `data2.dat` à `data4.dat` du portage (1 à 3 novembre) sont **plus anciens** que ceux du téléphone (3 novembre, 21 h 24) : le jeu lisait déjà les plus anciens, la reprise garde cet ordre (aucun choix à la date). Pour avoir ceux du téléphone, les copier dans `sauvegardes\` (jeu fermé) : ils remplacent les fichiers actuels, que la copie d'import ne sauvegarde pas (copie manuelle = pas de `avant_import`).
- Le jeu écrit maintenant dans les fichiers copiés du téléphone : l'original reste sur le téléphone.

## Avance #278 : Caméra : rotation gauche / droite et recentrage rétablis (rien d'autre)

> **Remplacé par l'avance #286 (D-234)** pour tout ce qui touche à la façon de tourner : la rotation n'est plus ajoutée par la visionneuse (`lacet`, `cam_w`, `_camera_menee`, `_coupure_camera`, marche et sprites tournés par pas de 45°, `CAM_SCENE_TAU`, effacement en ≈ 0,4 s) mais faite par le jeu lui-même. Restent valables : les touches, les gestes, les réglages, ce qui reste retiré (zoom, inclinaison, centrage) et la liste des cas non vérifiés sur Windows.

### Demande
Sylfried (05/11/2026, 00 h 00), après D-226 (#264) : « Quand je parlais de retourner sur le fonctionnement de la caméra de la version mobile il faut donc garder le fait de pouvoir la tourner à gauche et à droite et la recentrer... Donc remets ces possibilités là uniquement avec toutes les options à l'identique dans les commandes avec par défaut : Gauche > Flèche gauche, Droite > Flèche droite, Gauche + Droite > Recentre la caméra, Maintiens clic molette + direction > contrôler la caméra (gauche/droite uniquement), Clic molette > recentrer la caméra, Vitesse de caméra : x1, plus la possibilité d'accélérer la caméra comme avant. »

### Fait (D-233)
- **Rotation rétablie, rien d'autre.** `Jeu._camera_ville` reste la caméra du jeu (position, cible, champ, décalage : aucun zoom, aucune inclinaison, aucun centrage, aucun lissage) ; le seul ajout est la rotation du joueur (`lacet`, degrés, non enregistrée) **autour de la cible du jeu** : distance, tangage et place de la cible à l'écran ne changent pas, le cap change du lacet (positif = vers +X = flèche droite). Le repère des sprites, les panneaux de décor, l'orientation des personnages (`phi`) et les directions de marche (pas de 45°, `_tourner_dir`) suivent la rotation.
- **Touches** : `cam_gauche` / `cam_droite` (flèches ← → par défaut, réattribuables, page Commandes > « Caméra au clavier ») tournent la caméra à `CAM_LACET_VIT` = 100 ° / s × « Vitesse de caméra » ; **les deux ensemble** la recentrent par une animation (240 ° / s au moins, plus court chemin ; une flèche restée enfoncée après la double pression ne fait rien, une nouvelle pression seule annule le recentrage). ↑ ↓ ne font rien sur le terrain (menus seulement). **L'accélérateur n'accélère plus la caméra** (aide de la touche et du multiplicateur : marche seulement).
- **Souris** : clic molette maintenu + déplacement = tourner (`GesteMolette` + `pivoter`, gauche / droite seulement, le vertical ne tourne rien, 180 ° pour une hauteur de fenêtre, pas de saut au début) ; clic molette (sans déplacement) = recentrer ; `Inverser gauche / droite` (Commandes > « Caméra à la souris », Non par défaut ; ne touche pas les flèches ni le recentrage). Deux lignes d'information (lecture seule) rappellent les gestes. La molette ne fait toujours rien sur le terrain.
- **Réglages** : `vitesse_camera` (x1 par défaut, x1 à x4, page Commandes > Vitesses, sous « Vitesse de marche ») et `camera_inverser_gd` reviennent ; `distance_camera`, `angle_camera` et `camera_inverser_hb` restent dans `CLES_OBSOLETES`. Un ancien `reglages.json` qui les contenait garde sa vitesse et son sens de glisser.
- **Le jeu l'emporte dans ses scènes** (comme avant D-226, UNI-08) : TownCamera verrouillée et menée ailleurs que sur le joueur (`_camera_menee`), caméra libre d'une scène, verrou, lieu qui interdit la rotation (limite négative) ou la borne (`cam_limite`) : un poids `cam_w` (0 = rotation du joueur, 1 = caméra du jeu) rejoint sa cible en exp(−`CAM_SCENE_TAU` t), `CAM_SCENE_TAU` = 6 / s, ≈ 0,4 s pour 90 %, sans à-coup ; une coupure du jeu (changement de carte, plan de scène : `_coupure_camera`) est immédiate. Pendant ce temps les flèches et le clic molette ne tournent rien (`_camera_pilotable`). C'est ce qui évite le problème de la cinématique des compagnons qui avait motivé D-226 : la scène ne subit plus la rotation du joueur.
- Ni sur la carte du monde, ni sur l'écran-titre, ni dans les mini-jeux. F1 affiche « Caméra : rotation N ° ».
- Tests : `test_entrees.py` (+ 25 tests : geste, rotation, branchement dans un faux `Jeu`, flèches, recentrage, scènes, déplacement), `test_camera_ville.py` (rotation autour de la cible, effacement en douceur, câblage de la boucle et du dessin, réglages, ancien fichier), `test_pause_pages`, `test_perte_focus`, `test_reglages_son_texte`, `test_reglages_interface`, `test_ecrans` rétablis pour la vitesse et le sens de la caméra.

### Établi
- 23 mutations du code (sens du déplacement, sens de la rotation, accélérateur, scène, verrou, coupure, recentrage, glisser, inversion, titre, câblage…) : toutes tuées par les tests ; une avait survécu (le relâchement du bouton du milieu après un changement d'état du terrain) et a reçu son test.
- Rendus sans fenêtre (église de la sauvegarde 1) : la flèche droite tenue 50 images fait tourner la salle d'environ 85 ° autour de sa cible, les personnages et les panneaux de décor suivent ; les deux flèches ensemble ramènent la vue du jeu en douceur (aucun saut d'une image à l'autre) ; `DQ_LACET=90` donne la vue de côté attendue.

### Non vérifié
- Windows : clavier et clic molette réels, sensation de la vitesse x1 (100 ° / s, supposé proche du mobile : non mesuré).
- Le glisser du clic molette et la marche sous caméra tournée : testés sur un faux jeu, pas vus à l'image (dans le seul lieu de la sauvegarde de test, un message restait ouvert).
- La scène des compagnons au début du chapitre 2 avec une rotation faite avant la scène : l'effacement est supposé suffisant.
- Aux bords de la carte, la cible du jeu est bornée : la rotation se fait autour d'elle, le héros peut s'écarter du centre pendant le mouvement (comme sur mobile, non vérifié).
- Barre de rotation de la caméra du mobile (G-103) : toujours non reproduite. La rotation n'est pas enregistrée (elle repart de 0 au lancement).
- DQ5 / DQ6 : même réglage à prévoir (non regardé).

## Avance #280 : la reprise de l'ancienne disposition ne se fait qu'une fois (le dossier `avant_import_…` ne revient plus)

### Demande
Sylfried (05/11/2026, 01 h 07) : « Pourquoi dans le dossier des sauvegardes le dossier "avant_import_20261101_192625" revient en rechargeant le jeu ? Il faut qu'il disparaisse et que les fichiers directement dans le dossier `donnees\sauvegardes` soient pris en compte (d'ailleurs j'ai rajouté le fichier "manifest.json" qui est utilisé par la version mobile, en as-tu l'utilité de l'intégrer ?) »

### Cause (établie, sur le PC de Sylfried)
- `dq4_pc\sauvegardes\` existe encore (D-232 : « rien n'est supprimé ») et contient `avant_import_20261101_192625\`. `chemins.migrer` (lancée par `lancer_dq4.bat` puis par le jeu) **recopiait à chaque démarrage** tout ce qui manquait dans `donnees\sauvegardes` : le dossier effacé à la main revenait. Même défaut pour un journal `dataN.dat`, `etats\`, les réglages ou le journal d'erreurs effacés. Les fichiers directs de `donnees\sauvegardes` étaient bien lus par le jeu (D-232 : lecture et écriture dans ce seul dossier) ; la reprise ne les écrasait pas.

### Fait (D-235)
- **Chaque reprise ne se fait qu'une fois** : `donnees\reprise.json` (`{"etapes": {nom: date}}`) note les étapes faites (`cache`, `apk`, `sauvegardes_portage`, `sauvegardes_telephone`, `reglages`, `journal`) ; le rangement des anciens `portage\` et `mobile\` (D-232) déplace ses dossiers, il ne se répète donc pas de lui-même.
- **Une destination déjà en service compte comme faite** (`_deja_en_service`) : journaux ou `etats\` dans `donnees\sauvegardes`, un `.json` dans `reglages\`, un `.apk` dans `apk\`, le cache, le journal d'erreurs. C'est le cas de Sylfried : au premier lancement le fichier est écrit avec « en place » pour chaque étape et plus rien n'est recopié. Fichier illisible : comme une première fois (copie sans rien écraser, puis fichier refait). Une étape sans ancien dossier n'écrit rien (installation neuve : pas de `reprise.json`).
- Rien n'est supprimé ni écrasé : `dq4_pc\sauvegardes\` et `dq4_pc\reglages.json` restent en place, à effacer à la main quand tu as vérifié.
- `tests/test_chemins.py` (20 tests, dans la CI) : tout effacé dans `donnees\` ne revient pas, disposition déjà en service (le cas réel) sans rien recopier, fichier de reprise illisible, installation vide sans fichier ; 3 mutations du code toutes tuées (une avait d'abord survécu : le test efface maintenant aussi `reglages\` et `sauvegardes\`).

### `manifest.json` (établi / supposé)
- **Établi** : le jeu ne lit pas `manifest.json` (aucune occurrence dans le code managé, seulement les ressources .NET, ni dans les chaînes de `libdq4core.so`). Son contenu : `date` (3 novembre 21 h 24 UTC), `package` (`com.square_enix.android_googleplay.dq4`), `device` (`SM S938B`), `files` (taille et sha256 de `data1.dat` à `data5.dat` et `data9.dat`). **Supposé** : écrit par l'outil qui a copié les sauvegardes du téléphone, pas par le jeu.
- **Pas intégré** : chaque journal a déjà son contrôle (en-tête + somme, `format_journal.verifier`) et l'import contrôle les tailles ; le manifeste n'apporte rien au jeu. L'import l'ignore (test) ; il peut rester dans le dossier.
- **Constat utile** (sha256 du dossier de Sylfried, 05/11 01 h) : `data3.dat`, `data4.dat` et `data5.dat` sont **identiques à ceux du manifeste** (copie du téléphone) ; `data1.dat`, `data2.dat` et `data9.dat` **ne le sont pas** (`data2.dat` = l'ancien du portage du 3 novembre 18 h 25 ; `data1.dat` et `data9.dat` réécrits depuis, sans doute par le jeu).

### Non vérifié
- Windows : relancer le jeu deux fois après avoir effacé `avant_import_…` : il ne revient pas, `reprise.json` apparaît dans `donnees\`.

## Avance #282 : la console du lanceur se ferme avec la fenêtre du jeu

### Demande
Sylfried (05/11/2026, 01 h 07) : « Fais en sorte que le CMD qui s'ouvre lors du lancement du jeu se ferme automatiquement en fermant la fenêtre du jeu »

### Cause (établie dans le fichier)
`lancer_dq4.bat` finissait par `echo Fin du programme.` puis `pause` : la console attendait une touche après chaque fermeture du jeu.

### Fait (D-236)
- Après la ligne qui lance `python -m dq4_pc`, le lanceur lit le code de sortie (`set "CODE=%errorlevel%"`). **Code 0** (fermeture normale de la fenêtre, y compris le menu Quitter) : plus de pause, `exit /b 0`, la console se ferme. **Autre code** (le jeu a planté, Python lève une exception) : message « Le jeu s'est arrêté sur une erreur (code N) », `pause`, puis `exit /b N` ; l'erreur reste donc lisible.
- Les pauses d'avant le lancement (Python introuvable, création de l'environnement ou installation des modules échouée, lecture de la mise en page des fenêtres échouée) sont gardées : elles expliquent pourquoi le jeu ne démarre pas.
- Fins de ligne CRLF conservées (fichier réécrit en binaire).
- `tests/test_lanceur.py` (3 tests sans Windows, dans la CI) : CRLF, aucune `pause` hors du bloc d'erreur après la ligne de lancement, `exit /b %CODE%` en dernière ligne, chaque pause d'avant suit un message ; 3 mutations (pause ajoutée, `exit /b` retiré, LF) toutes tuées.

### Non vérifié
- Windows : fermer la fenêtre du jeu par la croix, Alt + F4 et le menu Quitter ferme la console ; le comportement sur une erreur (garder la console ouverte) n'a pas été vu non plus. Un processus du jeu qui ne se terminerait pas (fil non démon) garderait la console ouverte : rien de tel n'est connu.

## Avance #284 : Commandes : un seul groupe « Caméra »

### Demande
Sylfried (05/11/2026, 01 h 07) : « Regroupe toutes les options de caméra directement dans un groupe nommé "Caméra" » ; « Change le texte "Tourne la caméra à gauche ou à droite" par "Tourne la caméra" »

### Fait (D-237)
- Page Commandes (`Pause._e_commandes`) : l'intertitre **« Caméra »** regroupe, dans cet ordre, « Caméra (Gauche) », « Caméra (Droite) », « Inverser gauche / droite », les lignes d'information « Clic molette maintenu + déplacement : Tourne la caméra » et « Clic molette : Recentre la caméra », puis « Vitesse de caméra » (qui était sous « Vitesses »). Les intertitres « Caméra au clavier » et « Caméra à la souris » disparaissent. « Vitesses » commence par « Vitesse de marche ».
- `GESTES_SOURIS` : « Tourne la caméra ». Les aides des lignes, les touches par défaut et `reglages.json` ne changent pas.
- `tests/test_pause_pages.py` (29 tests) : liste des intertitres, contenu exact du groupe, plus de « Vitesse de caméra » sous « Vitesses », textes des deux informations ; 3 mutations (ancien texte, ancien intertitre, vitesse remise sous « Vitesses ») toutes tuées.

### Non vérifié
- Windows : l'aspect de la page (le groupe tient-il sans défilement ? les deux lignes d'information au milieu du groupe sont affichées comme avant : geste à gauche, effet en gris à droite).

## Avance #286 : Caméra : la rotation est celle du jeu (compagnons d'Alina), angle du toit

### Demande
Sylfried (05/11/2026, 01 h 07) : « Il y a encore un bug dans la caméra lorsque les compagnons rejoignent Alina, elle va tourner un peu puis se téléporter sur ses compagnons pour ensuite suivre la scène, comme je t'ai dis reprend le comportement de la caméra comme sur la version mobile, dans les moments où on peut la contrôler comme dans les moments où le jeu la controle », puis « Profites-en aussi pour regarder si l'angle d'origine de la caméra une fois qu'on est sorti de la chambre d'Alina c'est celui actuellement proposé par le jeu ou bien si c'est un bug, pour t'aider tu peux charger l'état 1 qui est directement le moment où tu atterris sur le toit ».

### Cause (établie, mesurée avec le vrai moteur)
- D-233 (#278) faisait tourner la caméra **dans la visionneuse, à côté du jeu** : la vue montrée était le cap du moteur + un « lacet » du joueur, et un poids `cam_w` faisait glisser ce lacet vers 0 en ≈ 0,4 s dès que le jeu prenait la caméra (`cam_jeu`).
- La scène des compagnons (début du chapitre 2, cartes `ev01` puis `cbout`, journal pas à pas de la caméra du jeu) : le jeu fixe un cap **absolu** de 180 ° (≈ 2,8 ° par pas, pas 114 à 158 environ), puis mène la **cible** vers les compagnons (≈ (4 ; 6 ; 4,5), au plus 0,46 par pas, pas 164 à 178 environ), puis revient. Avec un lacet du joueur non nul, la visionneuse montrait le cap du jeu **plus** le lacet, puis le faisait glisser : la vue « tournait un peu » puis sautait avec la cible = ce que décrit Sylfried. Avec un lacet nul, la visionneuse montrait déjà exactement la caméra du moteur (vérifié).
- Ce n'est donc pas une erreur de la scène du jeu, c'est la rotation ajoutée par la visionneuse.

### Fait (D-234)
- **Plus aucune rotation à côté du jeu.** Sur le terrain libre d'une ville, d'un donjon ou d'une tour (`Jeu._camera_pilotable`), les flèches ← → (« Caméra (Gauche) » / « Caméra (Droite) »), le clic molette et son glissement envoient au moteur **les boutons de caméra du jeu** : les bits 4 et 5 (0x10, 0x20) des touches tenues, qui sont A et B ailleurs mais que `window::NormalControl::checkCamera` lit comme boutons de caméra sur le terrain d'une ville (1 = gauche, 2 = droite, 3 = les deux = retour au nord). `Moteur.CAM_G`, `CAM_D`, `CAM_PAS`, `ROT_CAM_*`.
- **Le jeu fait tout le reste** : `TownPlayerManager::setCameraRot` tourne d'un cran (0x200 sur 65536 par tour = 2,8125 °) par pas, borne selon les limites du lieu, refuse sous verrou, en scène ou dans un lieu qui l'interdit, tient le joueur pendant le retour au nord (animation du jeu, ≈ 5,6 ° par pas), tourne lui-même les directions de marche et garde la rangée des sprites (vérifié : le héros marche vers le fond de l'écran après un quart de tour, même rangée de sprite). `champ.py` ne tourne plus rien, `Jeu.pad()` n'a plus de rotation. À l'entrée d'une carte le jeu remet le cap à 0.
- **« Vitesse de caméra »** (x1 à x4) : le jeu ne tourne que d'un cran par pas ; pour x2 à x4, la visionneuse fait faire au moteur les crans de plus tout de suite (`Moteur.camera_tourner`, appelé après un pas dont `Moteur.camera_attente()` — `TownPlayerManager + 0x698` — montre que le jeu a pris le bouton ; sinon rien : verrou, scène…). Vitesse non entière répartie d'un pas à l'autre. Le glissement du clic molette suit le pointeur par crans (jusqu'à `CAM_GLISSE_PAS` = 6 par pas), 180 ° pour un déplacement égal à la hauteur de la fenêtre (200 px sur 720 : +50,6 °) ; la rotation restante à faire est abandonnée si le jeu refuse.
- **Image** : `Jeu._interpoler_camera` interpole la caméra entre deux pas du moteur (30 Hz) comme un couple : la cible suit le déplacement, la position tourne **en arc autour de la cible** (cap par le plus court chemin, distance et hauteur à part). Sans cela un cran de rotation (1,7 unité à 34 de distance) dépassait le seuil de saut (`CAM_SAUT_VILLE`, 1,5) et la rotation s'affichait à 30 images par seconde. Une coupure (cible qui saute, angle posé d'un coup par un script, plus de `CAM_SAUT_ROT` = 0,35 de la distance par pas, ≈ 20 °) n'est pas interpolée.
- **Inchangé** : touches, gestes, réglages (`vitesse_camera`, `camera_inverser_gd`), pas d'accélération, ni sur la carte du monde ni sur l'écran-titre ; F1 donne le cap du moteur. `Jeu.on_deactivate` abandonne la rotation demandée à la souris et le retour au nord en attente.
- **Retirés** : `CAM_LACET_VIT`, `CAM_RECENTRE_LACET`, `CAM_MENE_DIST`, `CAM_SCENE_TAU`, `DIR_BITS`, `_maj_camera`, `_camera_menee`, `_coupure_camera`, `_lacet_eff`, `_tourner_dir`, `t_cam`, les états `lacet` et `cam_w`.
- Tests : `test_camera_moteur.py` (nouveau, **vrai moteur**, sauvegarde 1 : un cran de 2,8125 ° par pas dans chaque sens, bouton gardé en attente, n crans de plus exacts, x2 / x4 en marche continue, les deux boutons = retour au nord sans à-coup avec joueur tenu puis rendu, marche relative à la caméra et même rangée du sprite ; ignoré sans `DQ_APK` / `DQ_SAVES`), `test_entrees.py` (geste, boutons envoyés, vitesse, glissement par crans, refus du jeu, pression double, retour au nord, hors terrain), `test_camera_ville.py` (la vue ne dépend que du moteur, interpolation en arc, coupures), `test_perte_focus.py`, `test_chargement.py`, `test_bruitage_clavier.py` adaptés.

### Établi
- La scène des compagnons au pas près (journal du vrai moteur) et la cause ci-dessus ; avec la caméra tournée à 105 ° **avant** la scène, la scène démarre au même pas et le jeu tourne de 105 ° à 180 ° (cap absolu), puis mène la cible et revient : aucun saut dans les images enregistrées (montage), rendu en temps réel fluide.
- x2 / x4 : 5,6 ° / 11,25 ° par pas ; un glissement de 200 px : +50,6 ° ; un clic molette à 110,7 ° : retour à 0 en 20 pas.
- 49 mutations du code nouveau (sens, bits, garde du jeu, type en attente, vitesse, crans de plus, glissement, pression double, hors terrain, oubli après un menu, interpolation et coupures, perte du focus…) : 7 avaient survécu, chacune a reçu son test ; toutes tuées.
- **Angle du toit (état 1)** : 60,05 ° est bien la valeur du **moteur** à cet instant (cap lu dans le moteur). La visionneuse ne l'écrit jamais (elle n'écrit plus la caméra du tout) ; sans action du joueur le jeu part de 0 à l'entrée d'une carte et le retour au nord ramène à 0. Ce n'est pas un bug de la visionneuse.

### Supposé
- Cet angle est posé par un script du jeu au moment de l'atterrissage / de la sortie de la chambre (candidats dans le code : `cmd_map_camera_default_angle` à 0x21fe20, `__cmd_map_camera_move::initialize` à 0x221aa0, `__cmd_map_camera_angle::initialize` à 0x221bec, `__cmd_set_camera_angle_abs::initialize` à 0x222360) : script exact non identifié.

### Non vérifié
- Windows : clavier et clic molette réels ; sensation de la vitesse x1 (84,4 °/s ; D-233 : 100 °/s ; celle du mobile n'est pas mesurée).
- Ce que montre le mobile à cet endroit (seul l'état 1 était disponible) : si l'angle de 60 ° y est le même, c'est le jeu qui le décide, la visionneuse n'y change rien.
- Les autres scènes que celle des compagnons, DQ5 / DQ6 (non regardés).
- **À faire valider par Sylfried** (ce que la caméra du jeu impose, voir D-234) : vitesse x1 = 84,4 °/s ; recentrer = retour au **nord** (cap 0), pas à « la vue du jeu » (sur le toit : 60 ° → 0), animé par le jeu, joueur tenu pendant ce temps et non interrompable par les flèches ; la rotation vit dans l'état du moteur (elle n'est toujours pas enregistrée par la visionneuse).
