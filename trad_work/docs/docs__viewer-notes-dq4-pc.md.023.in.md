### Fait
- `Etat.champ_echelle` et `Etat.flottants` (attributs de classe : un état instantané enregistré avant #252 reste valide), mis à jour par le paquet 30, remis à 1 / vide au paquet 0 (carte) et 27 (carte du monde) ; échelle bornée à 0,25 - 4 (le moteur n'envoie que 1,00 à 1,25), valeurs absentes, nulles, négatives, NaN, infinies ignorées.
- `_camera_champ` : hauteur visible × `champ_echelle`, par-dessus le zoom du joueur.
- `game.py` : sur la carte du monde, un sprite flottant est agrandi de `champ_echelle` (pieds fixes).
- Vérifié à l'écran (moteur réel, 1280 x 720, ballon injecté à l'échelle 1,25 sur la sauvegarde 4, avant / après) : le terrain montre 25 % de terrain en plus (symboles de lieux et décor à 0,8 de leur taille), l'enveloppe du ballon garde sa taille (45 → 48 px, aux arrondis du pixel près).
- `tests/test_balloon_scale.py` (10 tests, dans la CI ; les 3 de la caméra sont ignorés là-bas faute de pyglet).

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
- `tests/test_sepia_scenery.py` (6 tests).

### Non vérifié
Un vrai retour en arrière joué par le script (quand l'effet commence et finit) ; les matériaux `fld_transz` (le jeu n'a pas de variante sépia : le port les passe en sépia comme le reste) ; la carte du monde (pas de FldObject : non concernée).

## Avance #256 : effets d'écran du voyage, de la lampe et de Riremito (paquet 34, valeurs 3, 5, 6)

### Demande
Audit du 04/11/2026, UNI-06 : le paquet 34 ne rejouait que la valeur 4 (début de combat) ; voyage / ailes de Chimère (3), lampe « Ranaruta » (5) et Riremito (6) n'avaient aucun effet, et le moteur n'attendait pas leur fin.

### Établi
Trois coroutines de la classe `Capture` (`<Tabi>d__49`, `<DarkLamp>d__47`, `<Riremito>d__48`), avancées d'un pas par `LateUpdate` (30 Hz) : capture de l'écran du jeu sans interface, passe de flou (l'état de l'image précédente redessiné dans l'une de deux textures de demi-résolution), un `MoveNext`. Durées : 64 appels (voyage, départ), 45 (arrivée, bit 7), 64 (lampe), 63 (Riremito) ; aucun `Random`, aucune horloge. Voyage et lampe : sommets, couleurs et champs comparés au vrai code machine sous Unicorn, identiques au bit près ; Riremito relu à la main. La lampe et Riremito rendent l'écran noir d'un coup (appels 63 et 62) ; le départ d'un voyage laisse l'écran noir ; l'arrivée lance un fondu d'entrée de 30 images à l'appel 3 et rend la scène à l'appel 45.

### Fait
- Modules purs `rendu/effets_capture.py`, `tabi_effect.py`, `lamp_effect.py`, `riremito_effect.py`.
- `Moteur._debut_effet_ecran` / `_effet_ecran` : bit 1 levé puis abaissé après la durée de l'effet (suit « Vitesse de transition »), noir immédiat (`Etat.fondu_noir_net`), `Etat.ecran_noir` entre le départ et l'arrivée (borné à 60 s ; levé au retour au titre), fondu d'entrée (`Etat.fondu_entree_courant`). `Etat.effet_ecran` et `Etat.ecran_noir` : attributs de classe.
- `fenetre/effets_capture.py` (`EffetsCaptureMixin`) : capture, deux textures de flou, dessin ; `game.py` l'appelle depuis `_dessiner_scene` ; commandes, caméra et boutons tactiles bloqués pendant l'effet.
- Vérifié à l'écran (moteur réel, 1280 x 720, carte `caf1`, image par image) : lampe nuit et matin, Riremito (noir net à l'appel 62), voyage (départ, noir, arrivée, scène normale au dernier appel).
- `tests/test_capture_effects.py` (21 tests).

### Non vérifié
L'aspect exact face à l'original (aucune capture de référence) ; le contenu initial des textures de flou (noir supposé) ; l'interface dessinée par-dessus l'effet (supposé) ; le tourbillon du voyage, elliptique en 16/9 (le maillage est en coordonnées d'écran normalisées) ; 28 et 14 rangées gardées comme sur mobile (le jeu en calcule moins en 16/9) ; la cadence de 30 Hz ; la capture contient la vignette et le fondu du fond ; la durée réelle de l'effet de début de combat (57 images dans le port, non revérifiée).

## Avance #258 : un seul launch_dq4.bat (celui de dq4_pc supprimé)

### Demande
Remarque de Sylfried (04/11/2026, 20 h 31) : deux fichiers `launch_dq4.bat` dans le dépôt.

### Établi
La PR #197 avait laissé `dq4_pc\launch_dq4.bat`, un fichier de deux lignes qui appelle le vrai lanceur de la racine (pour d'éventuels anciens raccourcis). Le sondage D-237 demandait pourtant « un seul `launch_dq4.bat` à la racine ; `dq4_pc\` ne contient plus que du code », et le README comme `docs/code_plan.md` annonçaient « le seul lanceur » : c'était le seul fichier non code de `dq4_pc\` suivi par git. Écart avec ton choix, laissé par moi.

### Fait
- `dq4_pc\launch_dq4.bat` supprimé ; table « ancien nom → nouveau » de `docs/code_plan.md` corrigée. Le vrai lanceur (racine), les tests et la CI ne l'utilisaient pas.
- Vérifié : aucun autre fichier non code suivi dans `dq4_pc\` ; plus qu'un `launch_dq4.bat` suivi par git.

### À savoir
Un raccourci Windows qui pointait vers `dq4_pc\launch_dq4.bat` est à refaire vers `launch_dq4.bat` à la racine. Sur le PC de test, la suppression passe par `git pull` (tracé par git).

## Avance #260 : ménage : jeux, test_faisabilite et vieux fichiers supprimés du PC

### Demande
Sylfried (04/11/2026, 20 h 57 et 20 h 58) : supprimer `jeux\`, les deux fichiers non suivis et les fichiers et dossiers de test inutiles, « de partout ».

### Établi
- `test_faisabilite\` (`lancer_test.bat`, `test_core.py`, `rapport_test.txt`, 44 Ko) : le premier essai du 30/10 (verdict « réussi : le moteur du jeu s'exécute sur PC, sans Unity ») ; `dq4_pc\core\emu_core.py` en est la suite, aucun test ni script ne l'appelle ; le dossier n'a jamais été suivi par git.
- `dq4_pc\echantillons_message.npz` et `tools\ui_il2cpp\grande_pile.py` : non suivis, plus référencés dans le code (recherche dans tout le dépôt).
- `jeux\` : au moment de la demande, `donnees\` venait d'être créé par le premier lancement du nouveau lanceur (19 h 58) ; `jeux\` n'a été supprimé qu'après comparaison octet à octet des 3 APK et des 7 fichiers de sauvegarde du mobile avec `donnees\apk` et `donnees\sauvegardes\mobile`.
- Gardés : `tests\` (91 fichiers, la suite de la CI), `tools\session_flow\`, `tools\research\`, le modèle d'issue `test_windows`, `docs/audit/chapter2_test_plan.md`.

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
- `tests/test_exp_gift_touch.py` (13 tests : détection du menu avec une mémoire simulée, conversion, modèle de `NativeExec`, branchement) ; ajouté à la CI.
- Non vérifié : l'accélération des gains du casino par un appui (G-217).

## Avance #264 : Caméra du jeu, telle quelle : plus de zoom, de rotation ni d'inclinaison du joueur

### Demande
Sylfried (04/11/2026, 22 h 14), après avoir signalé un problème au début de la cinématique où les compagnons le rejoignent : « Reviens au fonctionnement de base de la caméra. Supprime le zoom / dézoom, le fait de changer d'angle [...] tu reviens au comportement EXACT du jeu. »

### Fait
- La caméra des villes, donjons et tours est celle du jeu telle quelle : `SceneCamera.Update` (position, cible, `LookAt`, tangage - lookDownAdjust, avance de distanceAdjust, décalage vertical, rotation libre des scènes) avec le champ horizontal fov x 4/3 et la hauteur de champ de l'écran portrait d'origine (donc plus de décor sur les côtés en 16/9). Plus de centrage sur le héros (la cible bornée du jeu fait foi aux bords de la carte), de lissage de hauteur (escaliers), de reste qui glisse au changement de régime, de mélange scène / joueur ni de taille du héros imposée (« zoom commun »).
- Retirés : zoom / distance (molette, touches, menu, `--carte-zoom`), rotation et inclinaison (flèches, clic molette), recentrage animé, remises à zéro (Ctrl), inversions de la souris, « Vitesse de caméra ». Les flèches ne servent plus que dans les menus ; la molette sert au menu Échap et à la licence.
- Carte du monde : la hauteur visible est celle du jeu (échelle du ballon comprise), sans zoom du joueur.
- Réglages : clés retirées placées dans `CLES_OBSOLETES` (un ancien `reglages.json` se lit, les clés ne sont pas réécrites).
- Tests : `test_town_camera.py` réécrit, trois fichiers supprimés (`test_camera_ctrl_tout`, `test_distance_camera_clavier`, `test_zoom_scene`), dix adaptés (`test_camera_titre`, `test_ballon_echelle`, `test_entrees`, `test_ecrans`, `test_pause_pages`, `test_perte_focus`, `test_priorite_jeu`, `test_reglages_interface`, `test_reglages_son_texte`, `test_sprites_droits`).

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
- `Jeu.toast`, `Jeu.toasts` et le dessin du bandeau noir en haut de l'écran n'existent plus. Les appels supprimés : changement de vitesse de combat hors combat (touche), états instantanés (enregistré, chargé, vide, annulé, échecs), sauvegardes importées, ouverture d'un dossier impossible (écran-titre), plein écran / fenêtre impossible, sauvegarde impossible (#198), mémoire du moteur à 78 % et 94 %, réglages du moteur non appliqués, interruption du son (le crochet `alerte` de `sound.py` reste mais n'est plus branché).
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
- `dq4_pc/menus/message_font.py` (nouveau, sans pyglet sauf pour la texture) : lecture du fichier de police du jeu (format TNOF : en-tête de 28 octets, table de 65 536 entrées, glyphes compressés), tous les glyphes, aucun caractère écrit dans le code. Copié dans le cache sous `ui_messages.font` au démarrage (`preparer_ressources`, une seule fois).
- Placement du moteur (`SDrawCTRL::PutChar`, `TextCanvas::PutChar`) : avance = largeur du glyphe ; glyphes à drapeau (V, W, t, v, w, y) posés un pixel plus à gauche et avançant de deux pixels de moins ; espace de 6 (celle du moteur, pas celle de la police) ; tabulation 15 ; `;` et `$` non dessinés (langue 1) ; un code absent de la police prend le glyphe du `@` (comme le jeu). L'image est une pose de glyphes sans mélange, comme le canevas du moteur : 1 unité d'interface par pixel du canevas.
- Coupure des lignes du moteur (`CTextAutoReturn::AutoReturn`, limite 410) : `PoliceMessages.couper`. Les pages et les lignes de l'historique sont donc celles de la boîte de dialogue.
- `ui_history.py` : corps du texte et en-tête des combats avec cette police (nom du locuteur, onglets, aide : SE-GARRIR comme avant) ; la mise en page de la boîte (`Boite`) est inchangée.
- Sans la police (paquet de données absent ou illisible) : repli sur SE-GARRIR, avec un message dans la console.
- `tests/test_message_font.py` (27 tests) : 22 sans moteur (CI) sur une police synthétique ; 5 contre le vrai moteur sous Unicorn : pixels de `PutChar` identiques pour des phrases françaises, les lettres russes et les glyphes à drapeau, pour les 221 glyphes de la police, coupure identique à `AutoReturn` sur un échantillon de ~400 messages du jeu et sur des cas construits (`$`, `;`, tirets, espaces larges, mot trop long). Contrôle des tests : changer l'espace à 5, supprimer le crénage, la limite à 400 ou la largeur de `$` fait échouer les comparaisons.
