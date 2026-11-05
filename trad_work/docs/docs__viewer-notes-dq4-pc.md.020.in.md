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
- Tests : `tools/test_description_objet.py` (16 dont 3 avec la vraie police et les 360 textes) ; `tools/test_magie_liste.py` reprend les tests de recoupe.

### À trancher / non vérifié
- Sous Windows (écrans 1920 x 1200 et 2560 x 1440) : non vu.
- Autres fenêtres qui ont la même barre de description en bas : boutiques (types 46, 60, 61, 63) et fiche d'objet de la boutique de vente (70). Les chaînes de description sont (46, 3), (60, 4), (61, 4), (63, 4), (70, 3) ; leur bord droit n'a pas été mesuré (barre supposée identique : 148). Non ajoutées sans capture. → ajoutées en #220 (mise en page réelle, police réelle et capture hors écran).
- Si les proportions d'origine sont quand même voulues : `reglages.LARGEUR_COMMANDES` (fenêtres de combat) et `fenetre.UI_ZOOM` (1,12) sont les deux réglages du port ; ils ne changent rien à ce défaut.

## Avance #193 : sauvegarde automatique, lecture du code du jeu (#192, 04/11/2026)

### Demande (D-235, 04/11 13 h 33)
« Pareil pour la sauvegarde auto, regarde le code du jeu pour savoir comment est écrite la sauvegarde et ce qui est sauvegardé et comment ». Le détail technique est dans `docs/technical-notes-dq4-port.md`, section « Sauvegarde automatique : quand, quoi, comment ».

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
- `tools/test_historique_acces.py` : les trois tests qui attendaient un message vérifient maintenant qu'il n'y en a aucun (19 tests passent).

### À trancher / non vérifié
- L'infobulle de la ligne « Historique » grisée du menu Paramètres (« Disponible seulement quand vous avez la main… ») est gardée : elle n'apparaît qu'au survol de la ligne. À retirer aussi si Sylfried le veut.
- Sous Windows : non vu.

## Avance #197 : rangement du projet (#196, 04/11/2026)

### Demande (D-237, D-238, 04/11 14 h 57)
« Refais aussi une passe sur la structure du projet [...] clean un peu le tout avec des dossiers, revoir la qualité du code, simplifier l'utilisation, centraliser les sauvegardes et les nommages car par exemple le dossier `jeux` reprend l'exacte forme de l'autre projet de traduction. »
- **D-237 (sondage)** : « Un dossier `donnees\` dans le projet (Recommandé) » : `apk\`, `sauvegardes\{mobile\<date>, portage, etats, avant_import_<date>}`, `cache\`, `reglages\`, `journaux\` ; un seul `launch_dq4.bat` à la racine ; `dq4_pc\` ne contient plus que du code.
- **D-238 (sondage)** : « dossiers + nettoyage sûr + découpage des fichiers seulement si ça permet de mieux structurer [...] je te laisse juger si c'est nécessaire de le faire, et si oui comment le faire ».

### Fait
- Plan complet et table ancien nom → nouveau : `docs/code_plan.md`.
- Code rangé en paquets : `noyau` (moteur émulé), `monde` (cartes, décors, sprites), `rendu`, `combat`, `menus`, `persistance`, `fenetre`. `dq4_pc/fenetre.py` (3 761 lignes, 254 fonctions dans une seule classe `Jeu`) est découpé en 13 modules par thème ; la classe `Jeu` est assemblée par héritage de neuf « mixins ». Vérifié par l'arbre syntaxique : les 254 fonctions sont strictement identiques à celles d'avant, rien d'autre n'a changé dans le code du jeu.
- `dq4_pc/paths.py` : tous les dossiers et fichiers en un seul endroit (`Dossiers`), variables d'environnement `DQ4_DONNEES` et `DQ4_JEUX` (ancien fonctionnement), reprise de l'ancienne disposition `chemins.migrer()` : copie sans jamais écraser ni supprimer (le cache, lourd, est déplacé d'un coup s'il n'existe pas encore dans `donnees\cache`). `dq4_pc/main.py` : lecture des arguments et ouverture de la fenêtre (ancienne `fenetre.main`).
- `persistance/etats.py` : les états instantanés enregistrés avant le rangement se rechargent (table `ANCIENS_MODULES` + `Unpickler.find_class`).
- Un seul lanceur `launch_dq4.bat` à la racine (Python, `.venv` à la racine, reprise des anciens fichiers, génération des mises en page, lancement) ; l'ancien `dq4_pc\launch_dq4.bat` redirige vers lui. `tools\generate_ui.bat` et `tools\dump_il2cpp.bat` suivent.
- Tests dans `tests\` (`test_paths.py` : 15 tests nouveaux ; `tests/_paths.py` : aides communes). Entretien : six tests déjà en échec avant le rangement sont réparés, sans toucher au jeu (`test_mode_fenetre` : valeur par défaut de la correction des bords depuis #184 ; `test_historique_messages` : code de `Pause.maj` changé par #187 ; `test_casino_bestiaire`, `test_priorite_jeu`, `test_transition_combat`, `test_vitesse_combat` : fausse fenêtre sans `pause`). Nettoyage sûr : variables et imports inutilisés.
- CI : compilation de `dq4_pc tests outils`, motifs interdits (+`donnees`), tests `test_chemins` et `test_rencontres`.

### Non fait / à savoir
- `menus/pause.py` (1 459 lignes) et `menus/ui_menu.py` (1 255 lignes) restent d'un seul tenant : un fichier par page du menu Paramètres serait possible, mais le gain est moindre que pour `window.py` et le risque non nul ; à reprendre si Sylfried le souhaite.
- Cache : les fichiers du cache sont des dictionnaires et des tableaux numpy sans référence aux modules du code (supposé, non vérifié sur son PC) ; en cas de doute, supprimer `donnees\cache` (il est refait).
- Les anciens dossiers (`jeux\`, `dq4_pc\sauvegardes`, `dq4_pc\reglages.json`…) ne sont pas supprimés : à effacer à la main après vérification.
- Sous Windows : non vu (double-clic sur `launch_dq4.bat` à la racine, premier démarrage avec reprise des fichiers).

## Avance #199 : écriture des sauvegardes atomique, sans plantage (#198, audit ENG-02, 04/11/2026)

### Constat (audit du 04/11/2026)
`CoreJeu.h_fclose` écrivait `data*.dat` directement ; une erreur d'E/S (antivirus qui verrouille le fichier, disque plein) levait une exception dans le crochet, le moteur s'arrêtait et la fenêtre se fermait (`Jeu.tick` sans `try`). Établi par lecture et par essai sur le moteur réel ; fichier tronqué après un arrêt brutal : supposé ; Windows : non vérifié.

### Fait
- `CoreJeu.ecrire_atomique(chemin, octets)` : fichier `.tmp` à côté, `fsync`, puis `os.replace` (remplacement d'un coup) ; deux essais espacés de 0,25 s ; en cas d'échec l'ancien fichier reste intact, le `.tmp` est retiré.
- `CoreJeu.h_fclose` : une erreur n'est plus fatale. Le moteur continue (il croit avoir écrit, comme avant), l'échec est mis dans `CoreJeu.echecs_ecriture`.
- `Jeu._signaler_echecs_ecriture` (appelée par `tick`) : ligne dans `donnees\journaux\erreurs_fenetre.log` et petit message « Sauvegarde impossible : le jeu continue (détails dans erreurs_fenetre.log) ». Rien ne change quand tout va bien.
- `tests/test_save_writing.py` (6 tests, dans la CI) ; `test_sauvegarde_auto` (moteur réel) inchangé et vert.

### Non vérifié
Windows (antivirus, OneDrive) : le cas réel d'un verrou n'a pas été reproduit, seulement simulé.

## Avance #202 : Ogg écrêté au lieu de déborder (#200, audit SND-02, 04/11/2026)

### Constat (audit du 04/11/2026)
`decoder_akb` lisait les Ogg Vorbis en `int16` (`soundfile.read(dtype='int16')`) : quand le décodage dépasse la pleine échelle (surmodulation normale de Vorbis), l'échantillon déborde et un pic devient un pic de signe opposé. Établi sur un Ogg synthétique et sur les données d'origine : BGM14 (3 échantillons, vers 91 s) et BGM34 (7 échantillons) ; les 49 autres musiques et SE0409 (fanfare, Ogg aussi) n'ont aucun dépassement. Audibilité : non vérifiée (pas de carte son).

### Fait
- `son.decoder_ogg` : lecture en `float32`, mise à l'échelle 32767, **écrêtage** à ±pleine échelle, puis `int16`. Vérifié sur les vrais fichiers : seuls ces 3 + 7 échantillons changent (les autres musiques sont identiques à l'échantillon près).
- `tests/test_sound_decoding.py` (4 tests ; ajouté à la CI avec `soundfile`).

### Non vérifié
Windows et l'écoute.

## Avance #204 : trois bruitages à boucle de nouveau bouclés (#201, audit SND-03, 04/11/2026)

### Constat (audit du 04/11/2026)
SE0329 (fin de boucle 62 501 pour 62 496 échantillons décodés), SE0331 (58 983 / 58 976) et SE1118 (113 314 / 113 312) déclarent une boucle dont la fin dépasse de quelques échantillons la fin des données (reste d'un bloc ADPCM). Le garde `0 < fin <= n` de `decoder_akb` les déclarait « sans boucle ». Établi par lecture des en-têtes sur les 634 bruitages : 14 boucles reconnues sur 17 déclarées. Quels événements du jeu les jouent : non vérifié (identifiants calculés).

### Fait
- `son.decoder_akb` : une fin de boucle qui dépasse de **au plus 2 048 échantillons** (`TOLERANCE_FIN_BOUCLE`) la fin des données est ramenée à la fin des données (la boucle va jusqu'au bout) ; au-delà le garde reste. Les 17 boucles déclarées sont maintenant reconnues ; aucun autre bruitage ne change.
- Cache disque des bruitages (`son_SE*.npz`) versionné (`VERSION_CACHE_SON` = 2, 5e valeur de `p`) : un cache d'avant #201 (qui garde « sans boucle ») est refait au premier usage, sans rien à supprimer à la main.
- `tests/test_sound_decoding.py` : 6 tests de plus (10 au total).

### Non vérifié
Comportement exact de la bibliothèque son d'origine quand la fin dépasse (supposé : la boucle va jusqu'à la fin des données) ; l'écoute ; Windows.

## Avance #205 : surfaces transparentes triées par leur vraie priorité (#203, audit MAP-01, 04/11/2026)

### Constat (audit du 04/11/2026)
`map_objs` lisait la « priorité » d'un objet de carte dans la moitié haute de ses drapeaux (`flag >> 16` : 0 ou 4), alors que `FldObject.Load` lit les drapeaux en entier de 32 bits (+48) et la **priorité en entier de 32 bits en +52** (`FldObject.set_priority` : file de rendu 3000 + priorité). Établi par désassemblage et par lecture des 18 374 objets : 290 cartes ont des surfaces transparentes, 64 ont au moins deux priorités réelles (47 hors décors de combat : `dlb1a`, `dlb3` à `dlb5`, `dib1` à `dib3`, `teout4` à `teout6`, `zaout`, `ev06` à `ev09`, `mlout2`, `mmout`…). Mesure A / B de l'audit : sur `dlb1a` l'écume au pied des cascades manquait (12 % des pixels), `dib2` 3 %, `teout5`, `teout6`, `zaout` moins de 0,3 %. Supposé : que l'original montre bien l'écume (aucune capture d'origine).

### Fait
- `monde/fld.py:map_objs` : `prio` = entier en +52 ; `flag` = 16 bits bas des drapeaux (+48), identique à avant pour les billboards. Les clés de groupes `('tr', priorité, texture)` et le tri de `fenetre/champ.py` (`_tracer_decor`) sont inchangés : ils reçoivent maintenant la vraie priorité (sur `dlb1a` : 9 groupes transparents de priorités 10, 11, 12, 18 à 23, au lieu de 0 et 4 ; vérifié sur la vraie carte).
- Cache des cartes `carte10_` -> `carte11_` : **les cartes sont refaites en arrière-plan au premier lancement** (quelques minutes, comme pour chaque changement de version du cache) ; les `carte10_*.pkl` sont supprimés quand tout est prêt (`_purger_anciens`).
- `tests/test_fld_priority.py` (4 tests, dans la CI) ; `test_textures_carte` adapté (carte10 purgée, carte11 gardée).

### Non vérifié
Rendu d'origine (aucune capture) ; Windows. Tri par distance d'Unity à priorité égale : non mesuré.

## Avance #207 : charger un état instantané ne touche plus au moteur s'il est inutilisable (#206, audit ENG-06, 04/11/2026)

### Constat (audit du 04/11/2026)
`persistance/etats.appliquer` réécrivait la mémoire du moteur (tas, données, pile locale) **avant** de décoder la partie Python de l'état (`pickle`). Un fichier d'état abîmé ou tronqué levait donc l'erreur après avoir déjà écrasé le moteur : la partie en cours restait dans un état mélangé. Et rien n'empêchait de charger un état enregistré avec un autre `libdq4core.so` (autre APK) : les adresses ne correspondent plus. Établi par lecture du code ; le cas « autre bibliothèque » n'a pas été observé en jeu.

### Fait
- `appliquer` : vérifie la version, **puis** l'empreinte de la bibliothèque, **puis** décode `python` et `viewer`, et seulement ensuite écrit dans le moteur. Un état refusé ne change plus rien.
- `instantane` enregistre `lib_sha` (16 premiers caractères du SHA-256 de l'image de la bibliothèque). Les états déjà enregistrés n'ont pas cette clé : ils restent chargeables comme avant (aucune migration).
- `tests/test_savestates_order.py` (6 tests : 5 sans APK, dans la CI ; 1 avec le vrai moteur : un état tronqué laisse la mémoire intacte, l'état sain se recharge) ; `test_fld_priorite` ajouté à la CI (il y manquait depuis #205).
