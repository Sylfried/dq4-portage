### Fait
- `fenetre/constantes.py` : `PADS_BRUITAGE = 0x810` et `bruit_bouton(manette)`, le seul critère.
- `fenetre/clavier_souris.py:on_mouse_press` : un clic sur un bouton de menu joue le bruitage seulement si `bruit_bouton` ; retour et mode de la fenêtre de la carte (0x400, 2) muets. Carte ouverte au clavier (M : changer de vue, fermer ; flèches de la liste des boutiques) : muet.
- `fenetre/affichage_menus.py` (`_saisie_menu`, `_saisie_pas`) : B, flèches de page (L / R, ◀ ▶ d'une autre fenêtre, quantité des boutiques), ▲ ▼ et changement de colonne de la saisie numérique : muets ; A (et l'action 0x800 de la fiche du bestiaire) : bruitage. Les messages au moteur partent comme avant.
- Terrain : Entrée (Commandes), Espace (Discussion) et M (Carte) jouent le bruitage 300 quand le moteur autorise le bouton : `hud_mobile.Boutons.permis(nom)` (même condition que `visibles`, sans le réglage d'affichage « boutons » : la touche reste sonore si l'on masque les boutons). Un clic sur le bouton à l'écran ne joue pas deux fois (le bruit part à l'appui).
- Saisie du nom : une lettre ajoutée au clavier joue le bruitage comme le clic sur la lettre. Licence : le retour (manette 0x20, clic droit) est muet, le bouton « politique » (A) garde son bruitage.
- Inchangé : les bruitages demandés par le moteur (annulation, curseur : paquet 35), l'écran des sauvegardes et le menu Échap (fonctions du portage), les sons d'aperçu des volumes.
- `tests/test_keyboard_sfx.py` (25 tests ; dans la CI la règle seule, le reste demande pyglet) : table des manettes, `permis` = `visibles`, vraies méthodes de `Jeu` sur un faux jeu (clic, menu au clavier, saisie numérique, touches du terrain, carte ouverte, lettres du nom) ; sur l'ancien code, 8 cas de comportement échouent (plus `permis`, absent). Voisins relancés : croix et clic, entrées, touche menu, retour au titre, pause, casino, historique, son (tous verts) ; visionneuse complète lancée 200 images sans erreur.

### Non vérifié
Windows (oreille : B, flèches, ▲ ▼, retour de la carte sans bip ; Entrée, Espace, M et lettres du nom avec bip). Si le moteur joue lui-même un bruitage d'annulation à la fermeture de la carte (paquet 35), il reste audible ; si le jeu d'origine joue un bruitage à la frappe d'une lettre au toucher (3 sites `PlaySE(300)` de `InputName.Update`, correspondance exacte non lue) : Supposé.

## Avance #230 : arrêt de la musique pendant un jingle, morceau sans boucle redemandé (#229, audit SND-05 / SND-06, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi par lecture du code d'origine (`SoundControl`, pas par une trace du jeu) : `StopBGM` ne remet pas l'état du jingle à zéro, donc un arrêt reçu pendant un jingle lancé avec reprise (`0x1000 | n`) fait **repartir la musique d'avant** ; redemander un morceau en cours le relance. La visionneuse effaçait la reprise (silence) et ignorait toute redemande du morceau en cours, y compris d'un morceau sans boucle (BGM 1, 34) déjà terminé. Aucune occurrence dans les traces (le moteur arrête puis lance la nouvelle musique ; seul `playRestart(48)`, coffre / médaille, utilise la reprise) : Non vérifié en jeu.

### Fait
- `sound.py:jouer_bgm` : l'ordre d'arrêt garde le numéro de la musique à reprendre et la relance après l'arrêt (sans jingle, ou jingle déjà fini et reprise déjà faite : arrêt normal).
- `sound.py:_bgm_finie` + `jouer_bgm` : un morceau sans boucle dont l'heure de fin est passée (pas en pause) n'est plus « en cours » : le redemander le relance. Un morceau qui joue encore, en boucle ou non, n'est pas relancé (inchangé).
- `tests/test_sound_music_limits.py` (11 tests, dans la CI, faux lecteurs) ; 2 échouent sur l'ancien code. Voisins relancés : échecs du son, mixage, décodage, bruitage de transition, réglages du son, retour au titre, sauvegarde automatique.

### Non vérifié
Une occurrence réelle (aucune connue) ; le relancement d'un morceau **en cours** redemandé (`playBgm` / `playStart`, le moteur ne réémet pas `play`) : volontairement non reproduit, un redémarrage à tort serait plus gênant que l'écart ; Windows.

## Avance #232 : repli « menus simples », le canevas du message est lu de façon circulaire (#231, audit CMB-04, 04/11/2026)

### Constat (audit du 04/11/2026)
Établi : dans le repli sans `ui_layout.json`, `Moteur.lire_message` découpait `a[top:top + h]` sans modulo alors que le défilement du moteur croît sans borne et que le canevas de message d'Unity est une texture circulaire de 512 lignes ; après une quinzaine de lignes (cumulées sur plusieurs combats) le texte devenait vide. Avec la vraie interface (`ui_menu.regler`, `y & 0x1ff`) : aucun problème. Atteignable seulement si `ui_layout.json` manque du cache.

### Fait
- `noyau/moteur.py:lire_message` : `a[(haut + k) % 512]` (même repli que l'interface d'origine, qui lit `(102 + k + (y & 0x1ff)) % 512`) ; le bas du canevas reprend au début au lieu de donner des lignes vides. Défilement négatif et réglages incohérents : inchangés.
- `tests/test_message_fallback.py` (9 tests, dans la CI, moteur factice) ; 2 échouent sur l'ancien code.

### Non vérifié
Le repli en jeu réel (il faudrait retirer `ui_layout.json` du cache) ; Windows.

## Avance #234 : bilan de l'audit complet, documents d'audit mis à jour, décisions du sondage (#233, 04/11/2026)

### Demande (14 h 52)
Relire tout le jeu d'origine contre le portage, corriger ce qui est mal fait ou inachevé, ajouter ce qui manque, poser un sondage pour ce qui touche à tes choix.

### Fait
- Neuf domaines relus (moteur, cartes, sprites, services, interface, son, Unity, combat) ; chaque écart net a eu son issue et sa PR (`docs/audit/remaining_work_report.md`, section « Audit complet du 04/11/2026 »).
- `docs/audit/known_gaps.md`, `coverage.md`, notes techniques : statuts périmés mis à jour (poker, machine à sous au clavier, bestiaire, teinte, poses couchées, véhicules, générique de fin = groupe 8).
- Tes réponses au sondage (4 séries) sont dans la section « Décisions du sondage du 04/11/2026 » du rapport ; elles décident des prochaines issues (focus, zoom des scènes, ballon, ciel, volumes, temps de jeu, générique, `.dqs`).

### Non vérifié
Rien de nouveau côté code ; documents seulement.

## Avance #236 : pause du jeu et du son à chaque perte de focus de la fenêtre (#235, audit UNI-02 / SND-07, 04/11/2026)

### Demande
Sondage du 04/11/2026 : « Pause à chaque perte de focus ». Audit UNI-02 / SND-07 : l'original appelle `Sound.SystemPause` quand l'application perd le focus ; la visionneuse laissait le jeu et la musique tourner.

### Fait
- `fenetre/jeu.py` : `on_deactivate` (jeu gelé dans `_boucle`, `Son.perdre_focus(True)`, boutons de souris tenus relâchés : molette, croix à l'écran, bouton appuyé) et `on_activate` (son repris, horloge remise à zéro sans rattrapage, touches déjà tenues = pas de nouvel appui). Événements reçus avant la fin du chargement (`_pret`) : seul le drapeau est posé, `_boucle` met le son en pause dès qu'elle tourne.
- `sound.py` : `Son.perdre_focus` (`hors_focus`) prioritaire sur l'écoute de la page Son (`_doit_pauser`) ; reprise : les échéances (jingle, bruitages) sont décalées de la durée de la pause. Un menu Paramètres qui suspend encore le jeu garde la pause après le retour du focus.
- `tests/test_focus_loss.py` (10 tests : 5 Son dans la CI, 5 faux Jeu en local) ; tous échouent sans le correctif.

### Non vérifié
Windows : Alt + Tab, minimisation, plein écran, page Son ouverte pendant l'Alt + Tab. Le clic qui redonne le focus agit comme un clic de jeu (comme avant).

## Avance #238 : volumes des sons d'après snd_vol.dat (#237, audit SND-01, 04/11/2026)

### Demande
Sondage du 04/11/2026 : « Aligner sur l'original » (audit SND-01).

### Fait
- `sound.py` : `Son.vol_snd(ident)` lit `assets/sound/snd_vol.dat` (1171 flottants, little-endian) à la première utilisation ; `_lancer_bgm` et `_lancer_se` jouent `en-tête x snd_vol` comme volume propre (`bgm_propre`, `_SE.propre`), donc un changement de curseur ou d'option plus tard garde le facteur. Table absente, indice hors table ou valeur absurde (0, > 1, nan, négatif) : 1,0. Cache disque des sons inchangé (le facteur est appliqué à la lecture).
- Valeurs relues sur le vrai APK : BGM01 0,7 ; BGM02 0,8 ; BGM14 et BGM20 1,0 ; BGM21 et BGM22 0,8 ; SE0409 0,6 ; SE0300 et SE1170 1,0.
- `tests/test_sound_volumes.py` (9 tests, dans la CI, faux APK et faux lecteurs).
- `docs/audit/known_gaps.md` G-047 et notes techniques mises à jour.

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
- `tests/test_play_time.py`, `tests/test_missing_hooks.py` (installateur ajouté).

### Non vérifié
Windows, partie réelle ; le budget de calcul des pas rapides (`BUDGET_PAS_RAPIDES`) peut faire moins de pas que prévu : le temps de jeu retarde alors un peu.

## Avance #242 : liste blanche de classes pour les états instantanés (#241, audit ENG-05, 04/11/2026)

### Demande
Sondage du 04/11/2026 : « Liste blanche de classes » (audit ENG-05).

### Établi
Un `.dqs` est lu par `pickle` (`etats.lire` pour le conteneur externe, `appliquer` pour les parties `python` et `viewer`) : un fichier fabriqué exécute du code Python au chargement (charge inoffensive écrivant un fichier témoin, audit). Le portage importe des ZIP de sauvegardes (`sauvegardes.importer`) : un état reçu est un vecteur.

### Fait
- `persistance/etats.py` : `CLASSES_AUTORISEES` et `_Depickler.find_class` ; les anciens noms de modules sont traduits d'abord (`ANCIENS_MODULES`), la liste blanche s'applique ensuite. Autorisés : `dq4_pc.core.engine.Etat` et `Interface`, les types de base (`list`, `dict`, `set`, `bytearray`...), `OrderedDict`, `defaultdict`, `deque`, `numpy.dtype` / `ndarray` et les fonctions de reconstruction des tableaux (`numpy.core` et `numpy._core`). Relevé fait sur de vrais états (ville, carte du monde, combat) : rien d'autre. Un nom pointé du protocole 4 (`os.system` pris dans un module autorisé) est comparé en entier : refusé.
- Refus : `UnpicklingError` avec un message en français qui donne le nom demandé ; rien n'est exécuté ; `appliquer` refuse avant d'écrire dans le moteur (#206). Les écrans qui chargent un état affichent déjà l'erreur (toast, page des états).
- `tests/test_savestates_whitelist.py` (15 tests ; pièges `os.system`, `eval`, `exec`, `open`, `__import__`, `getattr`, `subprocess`, `shutil`, `numpy.save` / `load`, `Moteur`, `CoreJeu`, noms pointés, fichier complet piégé, conteneur externe piégé).

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
- `tests/test_heap_alert.py` (6 tests).

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
- `tests/test_poker_font.py` (4 tests).

### Non vérifié
Rendu à d'autres tailles de fenêtre (la compression est proportionnelle) ; le poker en jeu réel côté Windows.

## Avance #250 : ciel prolongé sur dpout et ev09 (plus de coins noirs en 16/9)

### Demande
Audit du 04/11/2026, MAP-05 : les plans de ciel de `dpout` et `ev09` s'arrêtent avant les bords de la fenêtre en 16/9 ; décision de Sylfried (sondage) : **prolonger le ciel**.

### Établi
Rendu du moteur réel (1280 x 720) avant correction : `ev09` a un grand coin noir à gauche, `dpout` deux coins noirs. Plans concernés : objet `002_dpoutenk` (groupe 11768, 72 sommets, x de -20 à 20, plan plat z = 40) et `000_e9km1` (groupe 14511, 180 sommets, x de -9,1 à 17,9). `ev02` : pas de coin noir, non concernée.

### Fait
- `CIELS_ETENDUS` (constantes) : cartes et mots-clés des plans ; `TitreMixin._ciel_etendu` : pour chaque plage du plan, deux copies symétriques (par rapport à `xmin` et à `xmax`), mêmes coordonnées de texture et couleurs, ajoutées à `carte_ext` ; `field.py` les met à jour comme les copies du titre.
- `ciel_titre.positions_copie(cur, dx)` : décalage (titre) ou `('miroir', xe)`.
- Vérifié à l'écran avant / après : plus de coin noir sur `ev09` ; `dpout` prolongé des deux côtés.
- `tests/test_extended_sky.py` (6 tests).

### Non vérifié
Rendu à d'autres tailles de fenêtre / formats (21:9) ; l'aspect du miroir en pleine partie sur Windows ; scènes qui déplacent la caméra sur ces cartes.

## Avance #252 : carte du monde en ballon : échelle du terrain du jeu (paquet 30) et ballon flottant

### Demande
Audit du 04/11/2026, MAP-02 / UNI-05 / SPR-06 : le paquet 30 (`field_scale`) était ignoré ; décision de Sylfried (sondage) : **reproduire l'original** (échelle du jeu × ton zoom).

### Établi
Désassemblage : `cmd_field_scale` (D12794) : entier ≥ 0 = `Field.SetFloatingObject(Chara.m_chara de cet emplacement)`, entier < 0 = `Field.SetScale(flottant)` ; `Field.SetScale` (CD353C) règle `Camera.orthographicSize = taille d'origine × échelle` puis `FloatingObject.SetScale(échelle)` (CD3708 : `localScale = échelle de départ × échelle`) sur chaque objet flottant, donc le panneau du ballon garde sa taille à l'écran quand le terrain est vu de plus loin (son ombre, transform séparé, non). Personne n'appelle `RemoveFloatingObject` (balayage de libil2cpp). Moteur lancé sur la sauvegarde 4 : à l'entrée sur la carte du monde, `(27, [1])` puis `(30, [12])` (image 31) : le ballon (emplacement 12) est toujours enregistré ; l'échelle `[-1] [1,25]` ne sort qu'en vol (relevé de l'audit, drapeau 344 forcé).
