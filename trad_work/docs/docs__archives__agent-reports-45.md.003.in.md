## Agent « chargement » (a3e5cc796bd50fbd6) — 02/11 21:03

RAPPORT FINAL, mission « chargement » (préfixe CH)

Worktree /home/claude/wt45-chargement, branche agent45-chargement (depuis 84b3f22). Working tree propre, rien poussé, branche inchangée. Pas de fichier dans docs/ (notes plus bas). Aucune sauvegarde de Sylfried écrite (tests dans /tmp/sv_*). Tous les commits portent les deux lignes Co-Authored-By / Claude-Session.

RÉSUMÉ
- Point 1, rideau au lancement : PARTIEL. Une cause réelle trouvée et corrigée (CH-1). Les causes propres à Windows ne sont pas vérifiables ici : mesures défensives, non vérifiées.
- Point 2, micro-images au changement de carte : FAIT côté moteur et viewer sous Linux/xvfb. Le rendu sur vrai GPU et Windows reste non vérifié.

COMMITS (dans l'ordre)
1. f37696e Suivi horodaté du démarrage et des changements de carte (DQ_SUIVI), outil de diagnostic. Nouveau dq4_pc/suivi_charge.py plus des points de mesure dans window.py. Sans DQ_SUIVI, aucun effet.
2. 6239b16 CH-1 : titre, la 1re image montrait un ciel sans ses bandes latérales (l'« effet de rideau »). Une ligne dans Jeu._tracer_ciel : `self._dom_lie = None`.
3. 0be4137 CH-2 : retenue du dessin pendant un changement de carte.
4. 9848871 CH-3 : le temps du chargement n'est plus rattrapé par le moteur.
5. 9b06b98 CH-4 : lancement Windows (transitions DWM coupées, 2e image noire). NON VÉRIFIÉ.
6. 664c01f CH-2b : la retenue compte ses propres images (robuste au rechargement d'un état).
7. a5100a6 CH-2c : pas d'interpolation de caméra à l'image qui lève la retenue.
8. 31c5225 CH-3b : absorption limitée à un vrai blocage (> 133 ms), 3 images au plus par chargement.

POINT 1 : RIDEAU AU LANCEMENT
Établi (journal DQ_SUIVI sous xvfb, captures avant/après) :
- Cause CH-1. `_tracer` ne valide les tampons que quand le domaine change (`_dom_lie`). Les bandes de ciel du titre sont créées après le 1er tracé de l'image, donc elles ne partaient pas. 1re image : ciel biaisé avec bords noirs (/tmp/m_chg_d0_b1.png, ligne 360 non noire de x=278 à 1256). Image suivante : plein écran. Après correction : x=0 à 1279 (/tmp/m_chg_d1_b1.png).
- Chronologie du lancement : fenêtre créée cachée à +0,037 s, image noire présentée à +0,058, fenêtre montrée à +0,061. Taille 1280x720 à la création, à l'affichage et dans on_resize : pas de redimensionnement. Logos 426 images, pire écart 107 ms. Titre : ev01 se charge dans la 1re image dessinée, et le moteur a déjà fait 3 pas, donc le fondu du titre est à 0,87 à la 1re image.
- Hypothèses écartées ou sans effet visible sous Linux : taille puis redimensionnement, tampon non vidé, désynchro logos/fondu (13 % du fondu déjà écoulé, non corrigé), préparation du cache (fil d'arrière-plan), caméra fausse (déjà complète au 1er dessin).
- Création du rendu hors écran (MSAA) pendant l'affichage : il est maintenant créé sous le noir de la retenue des changements de carte (CH-2). Au tout 1er dessin du titre il reste dans la 1re image visible. Je n'ai pas préchargé ev01 ni le PostFX dans le constructeur (pas de défaut visible démontré, évite de toucher au code de démarrage).
Non vérifié, Windows uniquement (CH-4) : animation d'ouverture DWM, présentation d'un flip sur fenêtre cachée, stalls de la 1re image sur vrai GPU, flash du plein écran (G-004 inchangé).
- `transitions_dwm` : DWMWA_TRANSITIONS_FORCEDISABLED pendant l'ouverture, remis 2 s après la 1re image. Toute erreur est sans effet (hors Windows : rien). Testé avec un faux dwmapi (3 tests).
- 2e image noire juste après `set_visible(True)`.
Raison : pas de Windows ici. Cause supposée : un fondu d'ouverture de la fenêtre par-dessus le noir puis les logos, ou le fond de classe de la fenêtre le temps du chargement.
Si CH-4 ne change rien chez Sylfried, il peut se retirer sans risque. CH-1 est la correction certaine.

POINT 2 : MICRO-IMAGES AU CHANGEMENT DE CARTE
Chronologie du moteur (106 cartes de villes + mort → église + sortie d'église) :
- image k : paquet 0 (décor), 8, 9 (fondu d'entrée, repart de l'opacité 1), 11, 12 (personnages créés sans position), 37.
- image k+1 : paquet 10 (caméra) et 13 positions.
- k+2 : 13 sans position.
- k+6 ou k+12 : poses/directions.
- Quelques PNJ ne sont placés que plus tard, voire jamais (alors à l'origine après ORIGINE_APRES).
- Le paquet 0 ne remet pas la caméra à zéro.
Conséquence : à l'image k, décor neuf + caméra de la carte d'avant + aucun personnage placé, sous 3 à 7 % d'opacité de la scène. Plus, en temps réel, le chargement synchrone du décor (la 1re image d'une scène a coûté 56 à 793 ms) rattrapé par le moteur : 3 pas d'un coup, donc le fondu saute.

CH-2, retenue (Etat.chargement, engine.py + window.py) :
- Posée au paquet 0 si l'écran est couvert : opacité ≥ 0,9 sur un plan, ou fondu d'entrée de plus d'une image lancé dans le même lot.
- Levée par Etat.maj_chargement : au moins 1 image du moteur, caméra reçue, personnages visibles placés (2 images d'attente au plus), tuiles reçues sur la carte du monde, garde-fou 6 images.
- Pendant la retenue, Jeu._dessiner_scene ne dessine que le noir et les fondus (même chemin que « scène pas arrivée »), et tick_fondu suspend le fondu d'entrée. Les durées de fondu ne changent pas : le fondu démarre une image plus tard, sur une scène complète. Vérifié par test (durée exacte conservée).
- Le rendu hors écran est créé sous ce noir.
CH-3 (+CH-3b) : après `_charger_carte`, `t_boucle = None` (l'horloge du moteur repart). `_absorber_blocage` fait de même pour une image de plus de 4 pas parmi les 3 qui suivent un chargement. Mon 1er seuil (2 pas, 6 images) figeait le moteur sur un rendu logiciel lent (6 images de suite au même pas moteur) : mesuré, corrigé en CH-3b.

Mesures avant/après (harnais moteur seul /tmp/chg/mesure.py, réglage par défaut vitesse des fondus x2). Une « image fautive » = image du moteur où la scène est visible à plus de 2 % alors que caméra, personnages ou tuiles ne sont pas en place.
- 106 cartes de villes par téléportation (/tmp/chg/o_tpmax_*.txt) : 111 images fautives avant, 0 après. L'oracle en signale 4 sur une carte (mom2f1). C'est un PNJ que le moteur lui-même ne place que 6 images après sa création, à l'origine : comportement du moteur, pas de la retenue. Retenue : 1 image (105 cartes), 2 images (1 carte).
- Mort → église (slots 1, 2, 4, monstre 100) : 2 chargements chacun, avec 1 image fautive à 7 % avant, 0 après (/tmp/chg/o_mort*_*.txt). Slot 4, bataille forcée : 'ev01 → btl_pl_d' puis 'btl_pl_d → mak1f1', même résultat.
- Sortie d'église, slot 1 (/tmp/chg/o_marche*) : mak1f1 → maout, 1 image fautive avant, 0 après. Chargement du slot (ev01 → mak1f1) idem.
- Téléportation depuis la carte du monde (slot 4, 10 cartes) : 10 images fautives avant, 0 après.
- Carte du monde : entrée/sortie sans paquet 0 (27/28), couverte par la garde existante « carte du monde pas envoyée ». La retenue n'intervient pas. Au pas où les tuiles arrivent, le fondu est à 0,87 et le héros est placé.
- Viewer sous xvfb, temps réel, rendu logiciel, chargement mak1f1 (journaux /tmp/suivi_tr_avant.txt et /tmp/suivi_tr_apres.txt) :
  - avant : 1re image visible à fondu 0,80, puis sauts de moteur +3/+2.
  - après : 3 dessins noirs 'noir (retenue du chargement)' à fondu 1,00, puis 1re image visible à fondu 0,93, caméra et 3/3 personnages en place, fondu régulier (1 pas moteur par pas de fondu).
- Viewer, mode un-pas-par-image (/tmp/suivi_ap1.txt) : dessin 'noir (retenue)' puis 'scène' avec caméra neuve et 3/3 personnages.
- Avec MSAA 4 (/tmp/suivi_msaa.txt, aussi lancé sans écran via pyglet headless) : même séquence, « Rendu hors écran x4 » créé sous la retenue.

Pas de mesure viewer pour : porte/escalier sortant d'un bâtiment par touches, entrée/sortie de combat avec effet, chargement d'état.
- Porte/escalier : le héros ne bougeait pas avec mes touches de test. La sortie d'église (mak1f1 → maout) est mesurée au niveau moteur, pas en viewer.
- Combat avec effet : couverte seulement au niveau moteur (bataille forcée).
- Chargement d'état : `_appliquer_etat` charge la carte lui-même et remet t_boucle à zéro, aucun paquet 0 ; je n'ai pas lancé de test viewer.

Non traité, par choix : une coupure franche sans fondu (écran non couvert). Elle garde le comportement d'origine, car il faudrait figer la dernière image affichée. Je n'ai pas relevé de cas dans les parcours testés (portes, mort, sorties, combat forcé).

À savoir : poses et directions des personnages n'arrivent qu'à k+6 ou k+12, y compris dans le jeu d'origine. Je ne les attends pas (ce serait retarder le fondu d'au moins 5 images).

TESTS
- Nouveau tools/test_chargement.py : 22 tests (règles d'Etat, absorption, interpolation, DWM simulé, moteur d'origine sur 5 téléportations avec --apk/--saves).
- Suite complète tools/test_*.py exécutée en headless sur le code final : tout OK. Deux exceptions de mon script seulement (passage d'arguments), relancées à la main avec les bons : test_etats_correctifs OK, test_texte_defilement OK (OK avant les commits CH-2c/CH-3b, non relancé depuis ; ils ne touchent ni le texte ni les états).
- pyflakes OK sur engine.py, load_tracking.py, test_loading.py. window.py : 2 avertissements déjà présents à 84b3f22 (dims, sel), pas sur mes lignes.

LIGNES TOUCHÉES DANS LES FICHIERS PARTAGÉS (à rebaser avec « caméra » et « combat »)
window.py :
- import suivi_charge + hooks SV.noter (Jeu.__init__ début, _creer_fenetre, _demarrer_moteur, constructeur).
- fonction transitions_dwm avant class Jeu.
- _creer_fenetre : 3 lignes autour de set_visible(True) (dwm_coupe, 2e flip noir, note du journal).
- on_draw : 1re image (planification DWM), appel de _absorber_blocage, _suivre_dessin.
- Jeu._absorber_blocage et Jeu._suivre_dessin (méthodes ajoutées).
- _instantane : champ `ret` ajouté (la clé `cle`, utilisée par _coupure_camera, est inchangée) ; _interpoler : une condition en plus.
- _charger_carte : une note de journal en fin.
- _dessiner_scene : `retenu`, `t_boucle = None` après le chargement, condition de la garde noire étendue, warm-up PostFX, tag _dessin_genre.
- _tracer_ciel : `_dom_lie = None`.
engine.py :
- constantes CHARGEMENT_*.
- Etat : attribut chargement, __setstate__, appliquer (début, paquet 0, paquet 10, bloc après la boucle), maj_chargement, ligne dans tick_fondu.
- Moteur.step : appel de maj_chargement avant tick_fondu.

NOTES À FUSIONNER DANS docs (prêtes à coller)
Texte complet dans /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/notes_chargement.md (sections : chronologie d'un changement de carte, retenue du dessin, règle _dom_lie, blocages de chargement, DQ_SUIVI, Windows).
Points clés :
- Au paquet 0, Etat.appliquer ne remet pas la caméra à zéro : caméra, personnages et teinte arrivent à k+1.
- Règle de dessin : toute liste de sommets créée ou réécrite après le 1er `_tracer` d'une image doit remettre `self._dom_lie = None`.
- DQ_SUIVI=1 (console) ou DQ_SUIVI=chemin donne un journal horodaté du lancement et des 16 dessins qui suivent un chargement.

À RETENIR (appris dans cette mission, pas de mémoire modifiée)
- Le viewer se lance sans X ni verrou xvfb : poser pyglet.options['headless']=True avant d'importer fenetre (scripts /tmp/chg/apres_viewer_h.py et avant_viewer_h.py). Utile quand la file /tmp/xvfb.lock dépasse 15 tâches (attente de plus de 30 min mesurée ce soir).
- /tmp/chg/mesure.py (moteur seul, mode avant/après) et /tmp/chg/analyse_suivi.py (lecteur de journal DQ_SUIVI) sont réutilisables.

FICHIERS DE PREUVE
/tmp/m_chg_d0_b1.png (avant) et /tmp/m_chg_d1_b1.png (après) ; /tmp/suivi_ap1.txt, /tmp/suivi_msaa.txt, /tmp/suivi_tr_avant.txt, /tmp/suivi_tr_apres.txt, /tmp/suivi_tr_h_*.txt ; /tmp/chg/o_*.txt (mesures moteur).

---

## Agent « texte » (af2afb0233cfb4a16) — 02/11 21:19

RAPPORT TX (agent45-texte). Résumé : le placement vertical / horizontal de la visionneuse est DÉJÀ identique au jeu d'origine, donc il n'y a pas de décalage visionneuse / mobile à corriger. Le texte « trop bas » existe aussi dans le jeu d'origine. J'ai quand même appliqué, comme demandé, une correction globale en un seul endroit : un recentrage optique, qui s'écarte volontairement du mobile. Elle est dans un commit séparé que tu peux écarter si tu préfères rester fidèle.

1. PAR POINT

a) Cause racine du décalage visionneuse / jeu : FAIT, aucun décalage. ÉTABLI.
- Le jeu utilise des TextMesh Unity (ancre 0-8, alignement, characterSize, lineSpacing exportés dans `ui_layout.json`). Ce n'est pas un composant UI Text ni TextMeshPro.
- Le moteur envoie les noms de groupes de monstres sous la forme `'Nom\n\n\t×2'` : 3 lignes (saut, ligne vide, tabulation, ×2). Je l'ai lu dans le journal du combat avec `TXSTR` / `TXPLAQ` : `'Glacyclone\n\n\t×2'`. C'est pourquoi « ×2 » est à 2 pas de ligne sous le nom.
- La capture mobile (ecran4) et la capture PC (ecran3) ont la même échelle : 1,688 px par unité (traits du cadre à 754,5 px).
- Texte « Ragnar » de l'onglet : profil de lignes identique pixel pour pixel sur le PC et le mobile. La base est à 8 px au-dessus du trait du corps de fenêtre des deux côtés, et le bord gauche à 30,5 px du trait du cadre des deux côtés.
- Formule actuelle de la visionneuse (bloc de N lignes de pas = interligne 23,525 × characterSize × 0,1 × lineSpacing, ancre haut / milieu / bas, base à ascent 18,887 sous le haut de la ligne, biais dy de 20) : elle redonne les lignes de base du mobile à ±0,6 unité.
  - « Rat volant » (1 ligne) : −13,4 unités sous le centre du bouton ; mobile −13,5.
  - « Scarapince » / « ×2 » (3 lignes) : −3,3 / −23,9 ; mobile −3,4 / −24,2.
- Rendu hors écran du type 33 (choix de cible) à l'échelle du mobile : onglets, « Rat volant », « Scarapince / ×2 » à ±1 px de la capture du mobile.
- Plaque PC « Scarapince ×2 » : lignes de base à 46 et 82 px sous le bord intérieur haut ; bouton mobile (même chaîne) : 47 et 82.
- Cause du « trop bas » :
  - Unity pose la ligne de base à `ascent` sous le haut de la ligne quel que soit `lineSpacing` (donnée du glyphe).
  - Les `lineSpacing` du jeu (0,441 cibles, 0,481 plaques de monstres, 0,801 onglets / boutons / noms, 0,873…) raccourcissent la boîte de ligne ; ils sont réglés pour la police japonaise.
  - L'encre de SE-GARRIR, centrée dans sa boîte naturelle de 23,5 px, descend donc de (1 − lineSpacing) × 23,525 × characterSize × 0,1 / 2 sous le centre de sa boîte.
  - Cela donne 6,5 unités (11 px à 1,688) pour « Rat volant » et les plaques de monstres, et 2,3 unités pour onglets et boutons.
  - C'est ce qui colle « ×2 » et « Rat volant » au bas du cadre.
- SUPPOSÉ : pour les ancrages haut et bas, aucune référence mobile. Le décalage encre / boîte ne dépend pas de l'ancrage, donc je l'applique pareil, mais je n'ai pas pu le confronter au mobile (nom dans la bande d'état, plaques de monstres).

b) Correction globale : FAIT (écart volontaire du jeu d'origine).
- Fonction `recentrage_texte(interligne, u, ls)` dans `dq4_pc/ui_menu.py`, appelée une seule fois par `Rendu._texte`. Elle remonte le texte de (1 − ls) × interligne × u / 2 quand `lineSpacing` < 1.
- Elle s'applique à tous les textes de menu et de combat qui passent par `Rendu._texte`, uniquement avec la police SE-GARRIR.
- `lineSpacing` ≥ 1 (PV / PM / Nv., listes) : inchangé, ils sont réglés sur les jauges.
- `DQ_TEXTE_ORIGINAL=1` restitue le placement exact du jeu. Pas de réglage dans le menu Pause : cela aurait touché `pause.py`, `settings.py` et `window.py`, zones des autres agents. Si Sylfried veut un bouton, c'est un ajout de 3 lignes (clé `texte_recentre`, `defaut=True`, `pause._choix`).
- Interprétation retenue : Sylfried demande d'améliorer l'alignement (« rien que tu puisses faire ? ») donc on s'écarte du mobile. Si tu préfères rester fidèle au mobile, écarte le commit f756c63 ; le premier commit n'a aucun effet visible.

c) Mesures avant / après (ÉTABLI).
- Rendu hors écran à l'échelle des captures (`/tmp/tx45/t33_cible_viewer_original.png` et `_recentre.png`) :
  - « Rat volant » : encre centrée sur le bouton, 0,6 px d'écart contre 11 px avant.
  - « Scarapince » / « ×2 » : marges 13 / 11 px dans le bouton ; avant, « ×2 » touchait le bas.
  - En-tête « Doc » de la plaque d'état : centre de l'encre à 5 px sous le centre de la bande (3 unités), 1 px après.
  - PV / PM / Nv. : inchangés.
- Captures réelles de combat à 1280×720, mêmes images, `DQ_TEXTE_ORIGINAL=1` contre défaut (`/tmp/tx45/c_avant_126.png`, `/tmp/tx45/c_apres_126.png`, comparaison `/tmp/tx45/combat_reel_avant_apres.png`) :
  - nom « Ragnar » de la plaque d'état : remonté de 2 px, centre de l'encre à 0,5 px du centre de la bande (2,5 px avant) ;
  - plaque « Glacyclone ×2 » : remontée de 5 px, centrée ;
  - onglet « Ragnar » : −2 px ; boutons « Attaquer » : −2 px ;
  - 3831 pixels changent, uniquement dans les textes.
- Autres fenêtres : 31 types rendus avant / après avec des libellés d'exemple (boutique 57 / 58 / 60, menu terrain 4 / 5, départ 53 / 54, église 66, listes 35 / 36, 3 / 30, Statut 13–17…) : seuls les textes bougent, vers le centre, sans régression visible. Feuilles `/tmp/tx45/feuille_gA.png`, `feuille_gB.png`, `feuille_g30.png`, `etat_plaques_avant_apres.png`, `commandes_avant_apres.png`.
- Pas rendues : l'historique et le cartouche de nom (zone de l'agent « ui »).
- Les retours à la ligne tombent au même endroit que sur le mobile (3 lignes, « ×2 » sous « Scarapince ») : ÉTABLI sur le rendu, d'après la capture. Les débordements de texte français ne sont pas touchés (D-133).

2. CORRECTIONS (branche agent45-texte, base 84b3f22, arbre propre)
- ab76eb9 : `base_premiere_ligne()` isolée dans `ui_menu.py` ; aucun changement de rendu ; `tools/test_texte_recentrage.py` (3 tests calés sur les mesures du mobile).
- f756c63 : `recentrage_texte()` + appel dans `Rendu._texte` ; 5 tests de plus (8 au total). Pyflakes : seul l'avertissement connu `ax` ; test_plaque_depart (12), test_panneau_interface (10) et test_reglages_interface (15) passent.

3. NOTES À FUSIONNER DANS docs/ (à coller dans `viewer-notes-dq4-pc.md`, remplace « Nom de Ragnar trop bas » de #43)
