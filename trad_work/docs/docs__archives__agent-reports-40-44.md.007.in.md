## Agent abe62037682218817 — 02/11 00:44

RAPPORT FINAL — agent « fenetre » (lot PR #42), points 1, 2, 3, 9
Worktree /home/claude/wt-fenetre, branche agent-fenetre, base 345ba8f. Arbre propre (git status vide), aucun push, main et saves intacts.

COMMITS
- 6cf5517 : écran de chargement noir, 3 modes de fenêtre, ordre de la page Affichage, F11 / Alt+Entrée
- 9624ec2 : lecture robuste de « Résolution » lors d'un changement de mode + tests des raccourcis (F11, Alt+Entrée, Alt Gr, Alt seul, Alt-Tab, Pause ouverte, capture de touche)
Pyflakes : seuls les avertissements connus (sel, R, yp, mh). Test unitaire : `timeout 100 xvfb-run -a -s "-screen 0 800x600x24" python3 tools/test_mode_fenetre.py` → 23 tests OK (les tests dépendant de pyglet sont ignorés sans DISPLAY).

PAR POINT
1. Écran noir au démarrage : FAIT. `_attente` ne dessine plus aucun texte (message seulement en console) ; le Label « Chargement du moteur... » de la boucle est retiré ; « Chargement de la carte... » (option --slot uniquement) aussi. Autres textes d'attente trouvés : « Chargement de la sauvegarde... » (retiré), `etiq_conseil` (astuce de menu, pas au démarrage, laissée). Pas de faute « Suréchantillonage » dans le code (libellé déjà « Suréchantillonnage »).
2. Trois modes : FAIT. Réglage `mode_fenetre` (0 fenêtré, 1 plein écran sans bordure à la résolution du bureau = comportement actuel, 2 exclusif = vrai changement de mode d'affichage vers « Résolution »). L'ancien booléen `plein_ecran` est migré silencieusement (True→1, False→0), puis n'est plus écrit. CLI `--plein-ecran 0/1/2`. Fenêtre créée directement dans le mode enregistré (cachée, première image noire, puis affichée : pas de flash). Repli défensif exclusif → plein écran → fenêtré, message console, à la création et à la bascule. FBO postfx : `post.cle = None` forcé après chaque changement de mode (recréation à la bonne taille, vérifiée avec msaa 4, ×1,5, netteté, luminosité).
   Sémantique de « Résolution » : mode 0 = taille de la fenêtre ; mode 1 = grisée, note « Sans effet en plein écran » (le bureau décide) ; mode 2 = résolution réelle de l'écran (choix du mode le plus proche, 16/9 de préférence, profondeur ≥ 24 bits, fréquence la plus haute). Note : dans l'ancien code, changer la résolution en plein écran ne faisait déjà rien (no-op pyglet, établi par lecture du code).
3. Ordre Affichage : FAIT (Fenêtre > Résolution > Netteté > Shader > Lissage des textures > Effet de vignetage > Anticrénelage > Suréchantillonnage > Luminosité > Distance caméra > Centrer la caméra sur le joueur, puis Interface en dernier ; libellés inchangés).
9. F11 / Alt+Entrée : FAIT. Fonctionne partout (logos, titre, menu de départ, jeu, menu Pause), seconde pression = retour au mode précédent. Décision : le raccourci CHANGE le réglage « Fenêtre » (le menu montre le mode réel, le prochain lancement le retrouve) ; le mode d'avant est mémorisé dans `mode_fenetre_retour` (jamais 2). Conflits : F11 est « réservée » (retirée des touches assignables, en plus d'Échap), la touche est avalée (ni validation ni action de jeu) ; « Discussion de groupe » sur Alt est devenue « Alt seul, au relâchement » (Alt+Entrée ne la déclenche donc plus ; Alt Gr ignoré) ; la touche Entrée seule valide toujours.

ÉTABLI (observé sous Xvfb / lu dans le code)
- Logos → carte : pixels non noirs pendant les 3 attentes = 0 avec mon code, contre 1595 / 2151 / 1637 avec le code d'avant (témoin /tmp/out_fenBase.txt).
- Migration, bornes, aller-retour d'enregistrement, F11 retiré d'un ancien fichier : tests unitaires.
- Repli simulé (variable `DQ_SIM_ECHEC` = 2 | 1 | 2,1 | 2s, au lancement et à la bascule F11), F11 et Alt+Entrée pendant les logos, bascules répétées, rendu hors écran recréé à 1920x1080 / 2880x1620, pas d'erreur ; capture en 1920x1080, 1280x720, 1920x1080 selon les bascules.
- Persistance du mode et lancement direct en exclusif ; `--options-test` : changement de Résolution accepté en exclusif, puis Fenêtre=0 → retour fenêtré 1280x720.
- Pyglet 2.1.19 Win32 (lu dans le code) : `fullscreen=True` = fenêtre sans bordure à la taille de l'écran sans changement de mode ; `set_mode` échoue en silence (d'où mon repli qui contrôle la taille réellement obtenue).
SUPPOSÉ
- Le changement de mode d'affichage réel (ChangeDisplaySettings) fonctionne sous Windows comme dans pyglet ; la restauration à la fermeture (`on_close` + `atexit`) remet bien le bureau ; la fenêtre cachée puis affichée évite tout flash blanc ; le choix de fréquence (la plus haute) convient.
NON VÉRIFIÉ (nécessite Windows : Xvfb n'a qu'un seul mode 1920x1080)
- Vraie bascule de résolution, refus du moniteur, restauration du bureau en cas de plantage, Alt-Tab en exclusif (non géré : le moniteur garde la résolution du jeu jusqu'à F11 ou fermeture), multi-moniteurs, mise à l'échelle DPI, Alt Gr sur clavier AZERTY réel, Alt+Entrée avec le comportement de touches de Windows (j'ai testé via le harnais avec MOD_ALT).

FICHIERS TOUCHÉS
- dq4_pc/fenetre.py (+243/−~50) : fonction `choisir_mode_ecran`, `Jeu.__init__` (création fenêtre), `_creer_fenetre`, `modes_ecran`, `resolutions` / `regler_resolution`, `regler_mode_fenetre`, `_poser_mode`, `basculer_exclusif`, `_raccourci_fenetre`, `_attente`, `on_key_press`, `on_key_release`, `_tenue`, `_fronts`, harnais (`_touches_test`, MOD_ALT), CLI, `on_close`.
- dq4_pc/reglages.py (+22) : DEFAUT (`mode_fenetre`, `mode_fenetre_retour`, sans `plein_ecran`), `MODES_FENETRE`, `NOMS_MODES_FENETRE`, `mode_fenetre_valide`, migration dans le chargeur, `RESERVEES = ('ESCAPE','F11')`.
- dq4_pc/pause.py (+15, minimal) : une ligne dans le dict `noms` (`'Fenêtre': RG.NOMS_MODES_FENETRE`) et réécriture de `_e_affichage` uniquement.
- tools/test_mode_fenetre.py (nouveau, 208 lignes).

CAPTURES (/tmp)
- Affichage plein écran (Résolution grisée + note) : /tmp/m_fenP1_b60.png ; plein écran exclusif : /tmp/m_fenP2_b60.png ; liste déroulante Fenêtre (mode fenêtré) : /tmp/m_fenP0_b60.png
- Écran noir pendant le chargement : /tmp/m_fenN_b30.png (journal /tmp/out_fenN.txt) ; témoin ancien code : /tmp/m_fenBase_b30.png (/tmp/out_fenBase.txt)
- Replis simulés : /tmp/m_fenF3_b20.png, /tmp/m_fenF4_b20.png, /tmp/m_fenF5_b20.png ; échec à la bascule F11 : /tmp/m_fenF6_b30.png, /tmp/m_fenF6_b60.png, /tmp/m_fenF7_b30.png
- F11 / Alt+Entrée pendant les logos : /tmp/m_fenL_b40.png ; bascules avec rendu hors écran : /tmp/m_fenFX_b30.png, _b60.png, _b90.png ; lancement exclusif + changement de résolution : /tmp/m_fenR_b40.png
- Autres : /tmp/m_fen0_b60.png, /tmp/m_fen1_b60.png, /tmp/m_fen2_b30.png, /tmp/m_fen2_b60.png, /tmp/m_fenA..E. Journaux : /tmp/out_fen*.txt

PIÈGES DE FUSION
- pause.py : je touche une ligne du dict `noms` (ajout de la clé `'Fenêtre'`) et TOUTE la liste de `_e_affichage` (réordonnée). L'agent « pause2 » modifie le reste de pause.py : conflit peu probable, mais si l'agent sprites ajoute une ligne d'option Affichage, l'insérer à la main dans MA liste réordonnée (garder Interface en dernier).
- window.py : conflits possibles avec les autres agents sur `__init__` (bloc de création de la fenêtre : `res_demandee`, `_creer_fenetre`), `_attente`, `on_key_press/on_key_release`, `_tenue`, `_fronts` (Alt exclu du front « discussion », `alt_tap`), le harnais `_touches_test` et les options CLI (`--plein-ecran` passe à choices (0,1,2)).
- settings.py : DEFAUT (clé `plein_ecran` remplacée par `mode_fenetre` + `mode_fenetre_retour`), `RESERVEES`, migration dans le chargeur. Tout code qui lit `reg['plein_ecran']` doit lire `reg['mode_fenetre']` (j'ai migré ceux de window.py ; vérifier les ajouts d'autres agents).
- Pause (agent pause2), page Commandes : l'infobulle « Discussion de groupe » pourrait dire « Alt seul, au relâchement ; Alt+Entrée = plein écran exclusif » ; non modifiée par moi (hors périmètre).

NOTES POUR docs/ (à fusionner dans viewer-notes-dq4-pc.md, section « Retours de 23 h 24 (#42) »)
- Démarrage : écran de chargement entièrement noir (aucun texte, messages en console seulement). Fenêtre créée cachée dans le mode enregistré, affichée après une première image noire.
- Réglage `mode_fenetre` : 0 fenêtré / 1 plein écran (sans bordure à la résolution du bureau) / 2 plein écran exclusif (changement réel de mode d'affichage). Migration silencieuse de l'ancien `plein_ecran`. Option CLI `--plein-ecran 0|1|2`. `mode_fenetre_retour` = mode (0 ou 1) auquel F11 revient depuis l'exclusif.
- Sémantique de « Résolution » : fenêtré = taille de fenêtre ; plein écran = sans effet (grisée) ; exclusif = résolution réelle de l'écran (mode le plus proche, 16/9 de préférence, ≥ 24 bits, fréquence la plus haute).
- Repli : exclusif refusé → plein écran sans bordure → fenêtré, avec message console. Crochet de test `DQ_SIM_ECHEC` (valeurs 2, 1, 2,1, 2s : simule le refus à la création et à la bascule). Restauration du mode d'affichage à la fermeture (`on_close` + `atexit`).
- F11 / Alt+Entrée : bascule exclusif ↔ mode précédent depuis n'importe quel écran ; le raccourci modifie le réglage « Fenêtre ». F11 est une touche réservée (non assignable dans Commandes). « Discussion de groupe » (Alt) se déclenche maintenant au relâchement d'Alt seul (donc Alt+Entrée, Alt+Tab et Alt Gr ne la déclenchent pas).
- Page Affichage : nouvel ordre (voir point 3) ; Interface en dernier.
- Test : `tools/test_mode_fenetre.py` (23 tests, Xvfb recommandé). Limites connues : voir « Non vérifié » (Windows requis).

À mémoriser pour la session principale (sources : brief et mission) : Sylfried teste sur Windows ; les points « Non vérifié » ci-dessus sont ceux à lui faire essayer en premier (Alt-Tab en exclusif, vraie résolution, F11 aller-retour, fermeture avec restauration du bureau).

---

## Agent a8d3c9b371f180c4e — 02/11 00:46

AGENT CAMERA (#42) — worktree /home/claude/wt-camera, branche agent-camera, base 345ba8f. 1 commit : 09006ce. Arbre propre. pyflakes OK (seul avertissement connu : `sel`).

**EN TÊTE : AUCUN changement de FOV ni d'inclinaison (avant = après).** Villes : fov nominal 9,5 (None côté moteur), champ horizontal 12,67° (9,5 x 4/3) fixe, vertical 22,3° à l'aspect d'origine 0,5625. Tangage = celui du moteur (47,03°, distance 39,55), lookDown 0,2°, avance 4,0, near 5 / far 100 par défaut. L'agent sprites peut garder la projection actuelle.

## Point 14 (grenouille du prologue) : corrigé
- Scène : déclencheur ~(0,93 ; 10,57) sur `mlout1`. Verrou TownCamera : mode 1 (panoramique diagonal, ~+0,088 x / -0,046 z par image) -> mode 5 (suit la grenouille, qui sort vers +x jusqu'à x = 6,07) -> mode 4 (retour au joueur) -> verrou levé.
- Cause (Établi, trace image par image) : la visionneuse bornait la caméra en x (`bornes_x`, cadrage 16/9) dès que `cam_jeu` passait à vrai. Le rendu restait collé à x = 1,978 pendant que le moteur allait à 6,07 : écart max 4,09 u avant, **0,000 après** sur 1470 images de scène. D'où « droite puis bas » et l'arrêt du suivi.
- Unity ne borne rien (Établi par désassemblage) : `SceneCamera.Update` D16180 sans Clamp/Min/Max ; `TownCamera::execute` sans clamp en mode libre ; `NativeManager.cmd_camera` D14568 appelle `FldObject.GetEventLimitedPos` CD4EE4 pour la position, mais seulement si `UIFix.IsLargeAspectRatio()`, et `s_eventLimitList` (.cctor CDDC08) n'a qu'UNE entrée : décor `map/ev/ev02/out/ev02`, événements {0,1}, z >= -19,5. Ce n'est pas `mlout1`.
- Fix (`window.py`) : nouvelle `Jeu._camera_menee(mo)` ; `cam_jeu` = verrou ET caméra menée ailleurs que sur le joueur (mode de cible 1 à 5, déplacement en cours, ou cible à plus de `CAM_MENE_DIST` = 1,0 u du héros, ou héros hors champ). `poids_cible = 1.0 if option or self.cam_jeu else 0.0` : aucune borne 16/9 en caméra menée, avec ou sans l'option « Centrer la caméra sur le joueur » ; les bornes reviennent progressivement (exp(-14 t), temps réel) à la fin.
- Captures avant/après : planches `/tmp/cam_fr_trajet_av_ap.png` (images 146 à 296) et `/tmp/cam_fr_depart_av_ap.png` (images 1530 à 1602) ; traces `/tmp/cam_av14.csv` (avant) et `/tmp/cam_ap14b.csv` (après) ; images unitaires `/tmp/cam_av14_f<n>.png` et `/tmp/cam_ap14b_f<n>.png`.

## Point 17 (père, caméra qui « continue son chemin ») : cause probable corrigée, scène exacte non retrouvée
- Cause trouvée (Établi par test, mais conditionnelle) : la correction du centrage (héros - cible du jeu) était lissée en bloc par exp(-14 t). Dès que le jeu borne sa cible (bord de carte) et que le héros court, la caméra traînait derrière (écart du héros au centre jusqu'à 0,03 NDC à x1 et 0,10 à x4, croissant avec la vitesse et la cadence), puis rattrapait après l'arrêt (0,015 à 0,09 NDC) : exactement « elle continue légèrement son chemin avant de se recentrer ». Mesure : `tools/test_camera_ville.py` (cadences 1/30, 1/60, 1/144 ; vitesses x1 à x4).
- Fix : correction = cible suivie à l'image près (caméra rigide sur le héros) + reste qui ne naît que d'un changement de régime (scène <-> main du joueur) ou d'une coupure, et qui s'estompe en temps réel. Résultat : écart 0,0000 partout, indépendant du nombre de pas moteur par image et de la cadence. Le banc réel (`/tmp/cam_r17_{av,ap}_{a1,a15,a4}.csv`, course vers le déclencheur de la grenouille à x1 / x1,5 / x4) confirme : le rendu égale le moteur en scène, quelle que soit la vitesse.
- Second contributeur corrigé : un verrou qui garde le héros au centre (mode 6, ou plan sur le héros) ne change plus de régime. Avant, il faisait glisser la caméra vers le cadrage borné de la pièce en ~0,2 s au déclenchement, puis revenir.
- Supposé / Non vérifié : je n'ai PAS reproduit le symptôme dans la maison du père. Dans le prologue (`mlb1a`) la caméra du moteur = héros partout, sans verrou pendant la 1re conversation : le défaut ne s'y produit donc pas. Le père se déplace ensuite et l'événement qui le concerne n'a pas été atteint. L'événement du Screen 6 reste à confirmer sur la sauvegarde de l'utilisateur. Autre piste NON corrigée : sous verrou (`cam_bloquee`), la rotation / l'inclinaison choisies par l'utilisateur sont coupées d'un coup (saut), et ça touche aussi l'orientation des sprites.

## Point 16 (l'angle de la caméra est-il le bon ?) : oui, pour le mode jeu. Certitude très élevée côté code, aucune capture de téléphone disponible.
- Établi (désassemblage) :
  - `SceneCamera.Update` : LookAt(position, cible), `eulerAngles.x -= s_lookDownAdjust` (0,2°), avance de `s_distanceAdjust` 4,0, `Perspective(fov x 4/3, 1/Camera.aspect)` avec [0] et [5] échangés (champ horizontal fixe), `s_yOffset` par produit de matrices.
  - `SetViewAndCenterY` D1F5D0 règle la hauteur du rect sur aspect_écran / 0,5625 : la vue 3D a donc TOUJOURS l'aspect 9:16 sur n'importe quel téléphone (letterbox / crop). Champ 12,67° x 22,3° partout, `ASPECT_DEF` = 0,5625.
  - Near 5 / far 100 : `Global.CameraInitParams[0]`, déjà dans les notes.
- Vérification numérique : un pipeline Unity ré-écrit à part (LookAt gauche, euler, Perspective, [0]/[5], yOffset) comparé à `_camera_ville` sur 200 poses x 18 points à 0,5625 : écart max 4e-15 NDC. Test permanent : `tools/test_camera_ville.py`.
- Scan des 518 cartes chargées (`/tmp/scan_cams.txt`, 3 cartes non chargeables) : 514 ont distance 39,55, tangage 47,03°, fov par défaut, near / far / yOffset par défaut. Exceptions : `dpout` (tangage 28,04°, far 150), `sjout` et `tdout` (near 1,0). Aucune différence villes / grottes / tours.
- Parcours de 2300 images du prologue : seule différence = écran-titre `ev01` (distance 44, tangage 39°, fov 10, far 150, bas 3,02), déjà géré par `TITRE_HAUT`. Hors titre, jamais de changement de distance ni de fov pendant les scènes testées.
- Cartes du monde et combat : lus lors de sessions précédentes (notes 30-31/10 : monde orthographique `Field.Init`, combat fov 48 x 4/3, 4/3 de référence, yOffset 0,04). Je ne les ai pas revérifiés ici. `_camera_combat` : fov vertical 50,25°, near 0,25, far 500, yOffset 0,04.
- Supposé : near/far pour les cartes qui envoient leurs propres valeurs (suivies telles quelles).
- Écarts voulus de la visionneuse (inchangés) : hauteur de champ du mobile gardée et plus de décor sur les côtés en 16/9 ; « zoom commun » (le héros garde HEROS_FRAC de la hauteur de la fenêtre).
- Piste possible pour « l'angle ne va pas » : `reglages.angle_camera` (flèches haut / bas) est SAUVEGARDÉ. Dans `/tmp/rg.json` (réglages de test partagés) il vaut -2,25° (défaut 0 = comme le jeu). Un appui accidentel suffit à décaler le tangage en permanence. À vérifier dans les réglages réels de l'utilisateur (commande « Caméra » ; la ligne d'infos F1 affiche l'angle).

## Fichiers touchés
`dq4_pc/fenetre.py` : `_camera_ville` (bloc centrage + poids), `tick` (calcul de `cam_jeu`), nouvelle `_camera_menee`, constante `CAM_MENE_DIST`, attributs `cam_res` et `cam_centre`. `tools/test_camera_ville.py` (nouveau, 5 tests sans fenêtre, 1 s, pyglet « headless » sous Linux). Je n'ai touché ni `engine.py` ni `settings.py`. Sur l'ancien code, 3 tests sur 5 échouent (centrage, caméra menée, prédicat) : ils détectent bien les défauts.

## Pièges de fusion
- `self.cam_jeu` change de sens : « verrou ET caméra menée ailleurs que sur le joueur » (avant : le verrou seul). `cam_bloquee` garde le sens verrou.
- `cam_poids` est conservé : même nom, même rôle (part sans bornes), sa cible est simplement différente. `_camv` l'affiche toujours.
- Autres agents sur `_camera_ville` (`TITRE_HAUT`, sprites) : mon changement est localisé entre `t = time.perf_counter()...` et `if abs(self.cam_dec[0]) > 1e-4` (calcul de `cam_dec`, `cam_res`, `poids_cible`), puis dans `tick` et `__init__` (ligne 185 : ajout de `cam_res` et `cam_centre`).
- `cam_dec` reste la valeur appliquée (`dec + reste`).
