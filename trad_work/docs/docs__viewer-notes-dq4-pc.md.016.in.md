### Non vérifié
- **Sous Windows** : à confirmer par Sylfried (fermer dans une grotte, puis « Sauvegarde automatique » au menu de départ).
- **Où le menu de départ replace le joueur** après une sauvegarde automatique prise dans un donjon (carte du monde à l'entrée, comme sur mobile, ou dans le donjon). Le chargement brut de la banque écrite à l'entrée du donjon (`loadbank(4)`) reprend dans le donjon (`dab1`) ; le chemin du menu de départ du jeu n'a pas été rejoué. Dans les deux cas c'est le code du moteur, que la visionneuse ne modifie pas.
- Ce que le jeu fait exactement des conditions `StageStatus` (quand `isAbortSaveDungeon` est vrai) : mesuré seulement sur `dab1` dans l'échantillon.

## Avance #143 : le petit rappel du bas de l'écran est retiré (#129, 03/11/2026)

### Demande (D-220, 23 h 08)
« Supprime le petit message en bas à gauche "Échap pour le menu, F1 pour les infos" ou un truc du genre. »

### Fait
- Retiré de `window.py` : l'étiquette `etiq_conseil`, `Jeu._texte_conseil` et le dessin qui l'affichait 8 secondes après le démarrage (hors menu Échap, hors infos F1, hors captures). `t_demarrage` reste (mesures de temps réel). Le menu Échap et la touche F1 ne changent pas.
- Test : `tools/test_sans_rappel_demarrage.py` (2 tests).

### Non vérifié
- **Sous Windows** : à confirmer par Sylfried (aucun texte en bas à gauche au démarrage).

## Avance #144 : à l'atterrissage sur la carte du monde, le héros est devant ses équipiers (#135, 03/11/2026)

### Demande (D-223, 23 h 27)
« Lors de l'utilisation d'une aile de chimère (donc lors du sort téléportation et autre aussi je suppose) j'ai trouvé un léger bug, une fois atterri Doc s'est retrouvé devant Ragnar alors que l'alignement doit être reproduit lorsqu'on atterrit, donc pareil regarde comment c'est fait dans le code source et reproduis-le à l'identique. »

### Établi (désassemblage de `libdq4core.so` et mesure sur le vrai moteur, enquête confiée à un sous-agent puis rejouée par moi)
- **Le moteur place le groupe correctement** : à l'arrivée sur la carte du monde il empile les membres sur un seul point (mesuré : héros et Doc à (2495,967 ; 391,967 ; z 200) à l'arrêt après la descente, 765 images dans cet état), puis ils se séparent en marchant. Aucune étape native d'alignement (`setFormation`, `setAllPotition`, `setPartyToFirst`, `setStartPosition`) n'est passée pendant le sort Téléportation ni à l'arrivée.
- **Le défaut était dans l'ordre de dessin de la visionneuse** : les sprites à plat de la carte du monde étaient superposés par `sorted((z, y, emplacement))`, le plus grand rang devant : à position égale, le plus grand emplacement (Doc, 1) passait devant le héros (0). Le jeu fait l'inverse : `FieldPartyDraw::draw` (0x1ec5a8) trie les membres par profondeur décroissante (tri par sélection, à égalité l'emplacement le plus bas garde la tête) puis appelle `SpriteCharacter::setDepth` avec 10, 9, 8… dans cet ordre : à profondeur égale, le héros est devant. La profondeur vient de `FieldPlayerManager::draw` (0x1f0a14), qui passe `FieldStage::calcDrawPosition(position).z` à `FieldPartyDraw::setDepth`.

### Fait
- `rang_profondeur_champ(sprites)` (`window.py`) remplace le tri en ligne. Clé : (hauteur z, plus au sud, puis `-emplacement` pour les membres du groupe, `emplacement` pour les véhicules). Hauteur et « plus au sud » priment toujours ; seul l'ex æquo change. Les véhicules (emplacements ≥ 10) gardent « le plus récent devant ».
- Test : `tools/test_ordre_groupe_champ.py` (7 tests : 6 sans moteur, 1 sur le vrai moteur : sortie de l'église, sort Téléportation depuis `maout` vers la carte du monde, descente de 23 images puis arrêt empilé : le héros reste devant Doc).

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
- Tests : `tools/test_panneau_interface.py` (14 tests, dont : un clic simple ne change l'état qu'une fois, après le délai ; un double clic ne le change jamais, replié ou déplié ; troisième clic après un double clic ; clic puis glisser).

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
- Test : `tools/test_historique_messages.py` (100 tests, dont `test_point_virgule_du_patch_retire`).

### Non vérifié
- **Sous Windows** : à confirmer par Sylfried (les dialogues avec un nom d'objet n'affichent plus de « ; »).
- Les textes du patch ont été relevés dans le paquet de données ; je n'ai pas rejoué chaque dialogue du jeu.

## Avance #149 : le message de la liste vide de l'historique tient dans son cadre (#140, 03/11/2026)

### Demande (D-224, 23 h 38)
« Le texte en fond dans la fenêtre d'historique dépasse de l'encadrement quand on filtre sur tous les favoris et qu'on n'en a pas. »

### Établi (reproduit hors moteur avec le vrai code de dessin, `ui_history.py`, fenêtre de 900 x 720)
- Avec « Favoris seulement » coché et aucun favori, la liste est vide et le message « Aucun dialogue en favori : décoche « Favoris seulement », choisis un dialogue et appuie sur Entrée (ou clique son étoile) pour le garder. » était dessiné **sur une seule ligne**, centrée : bien plus large que la fenêtre, il sortait du cadre des deux côtés (même chose pour « Aucun combat en favori… »). Les messages sans favori coché (« Aucun dialogue pour l'instant. ») sont courts et tenaient.

### Fait
- `ui_historique.couper_mots(texte, largeur, larg_max)` coupe le message aux espaces ; le dessin de la liste vide l'appelle avec la largeur de la fenêtre moins 2 x 20 unités, puis centre chaque ligne, le bloc étant centré verticalement dans la liste. Un mot plus large que la limite resterait seul sur sa ligne (il ne peut pas être coupé).
- Capture après correction (900 x 720) : 3 lignes centrées dans le cadre.
- Test : `tools/test_historique_messages.py` (105 tests, dont la classe `TestMessageVide`).

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
- Tests (moteur réel, `tools/test_magie_liste.py`, 33 tests dont 5 nouveaux) : les 3 soins à PV pleins ne jouent que le 306 ; les 3 soins utiles jouent 306, 501, 501 comme avant ; Multisoin en pleine forme : 306 seul, avec un blessé : 306, 501, 501 ; un soin utile après un soin inutile rejoue son bruitage.

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
- Tests : `tools/test_parametres_sans_pause.py` (13 tests : titre, pages figées, arrêt et reprise du son, aucune entrée envoyée, pas de marche accélérée, boucle).

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
