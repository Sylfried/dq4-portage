## Agent acb3a91d1ee1b129b — 02/11 04:41

RAPPORT « titre2 » (branche agent-titre2, worktree /home/claude/wt-titre2, base 08f5785). Arbre propre. Tests : test_titre_ciel (22), test_plaque_depart (12), test_camera_titre (3), test_camera_ville, panneau/reglages/son : OK. pyflakes : seuls les avertissements connus (ax, sel, struct).

COMMITS (8) : 585538a (data.py + map_objects.py repris de ac4cb9b, euler_mat Ry.Rz.Rx, cache carte9) ; 9d15a85 (titre 1:1 : sens des faces, zoom, retrait des hacks, DQ_FBXLOG) ; 1903c66 (title_sky.py + tests) ; 49f5ffe (ciel dans window.py) ; fdd6b10 (plaque auto + boutons/etat_actif) ; 4784e98 (test camera titre) ; 5c17b72 (réglage du ciel + texte gris) ; 599d54c (engine.py : rotation FBX par défaut).

A. DRAGON, « 2 orientations »
Établi : le dragon est posé UNE fois par le moteur (image 2 : pos (-2,16 ; 7,0 ; 0,55), lacet 349,45°, vu de dos, il regarde +z, loin de la caméra). Sa trajectoire vient des clips FBX : Take 001 (21,98 s) puis Take 002 en boucle (2,18 s) à l'image 662 ; il entre par le haut ~420-480, pique ~540-620, se pose au-dessus du logo 660-800 en battant des ailes. Journal : /tmp/t2_fbxlog.txt (DQ_FBXLOG=1).
Cause des « 2 orientations » : le culling. Cull Back d'Unity = faces avant dans le sens horaire à l'écran, alors que GL attend l'anti-horaire. Les faces intérieures lointaines passaient à travers les faces proches supprimées : on voyait un « visage » alors que le corps était de dos. Corrigé : glFrontFace(GL_CW) dans _tracer_fbx (DQ_FBX_CULL 0/1/2 pour comparer).
Le correctif euler_mat (ac4cb9b) ne l'explique PAS : il change l'inclinaison de l'île du château (map objects, FldObject.rotateXZY), pas le dragon (FbxObject.SetRotation = Quaternion.Euler).
Supposé : sens du cap du dragon (pas de référence mobile filmée).

B. 1:1 MOBILE
Établi : la zone 9:16 centrale est le rendu du téléphone. Causes d'écart supprimées : (1) bug de zoom sur ev01 (le sprite héros caché déclenchait la formule de zoom : scène agrandie ×1,185, logo plus large que la zone) ; exclu pour ev01, et le même bug existerait sur toute carte à sprite héros caché ; (2) hacks TITRE_HAUT, TITRE_DRAGON_HAUT, _decalage_credits (+ _credits_cache, DQ_CREDITS_ORIGINE) retirés : les crédits sont placés par le moteur.
Mesure : fenêtre 1281×720 (colonnes 438..842) contre 405×720, vignette à 0 (/tmp/rg_t2n.json) : identique au pixel (moyenne 0,0004 ; ≤107 pixels sur 291 600 diffèrent, bords de texte). 405×720 contre 720×1280 réduit : écart moyen 0,6 à 1,3 (rééchantillonnage). Captures : /tmp/m_t2n1_b{300,540,720,900}.png (1281), /tmp/m_t2n2_* (405), /tmp/m_t2n3_* (720×1280).
Piège : avec la vignette par défaut (0,3, réglage utilisateur) les bords de la zone sont plus sombres d'environ 20 % en fenêtre étroite qu'en 16/9 (premier diff trompeur, comparé à /tmp/t2_cmp900.png). Ce n'est pas un écart de scène.
Non touché : « Touchez l'écran » (couche UI, échelle ui_k : 0,89 en fenêtre portrait/405 contre 1,0 en 16/9, soit y = 0,79 contre 0,82 de la hauteur ; politique UI hors périmètre).

C. LOGO / CRÉDITS
Établi : logo centré (résidu = asymétries des données du moteur) ; crédits centrés à ±1,5 px, laissés tels que le moteur les place.

D. CIEL
Établi : nouveau module pur /home/claude/wt-titre2/dq4_pc/ciel_titre.py. Hors zone portrait, des bandes de même géométrie que les rangées du ciel (y, z, couleurs identiques) reprennent la texture avec une étirure horizontale variable (0,52 à 1,48, moyenne 1) et un glissement vertical de 3 % nul aux coutures de rangées. Raccord continu au bord, défilement suivi. La zone reste le ciel d'origine : zone identique au pixel entre mode bandes et mode copies (écart 0,0 ; /tmp/m_t2g1_b900 contre /tmp/m_t2h1_b900). Secours : toute erreur donne le ciel d'origine seul ; DQ_CIEL_COPIES=1 donne l'ancien comportement ; DQ_CIEL_PARAMS=a1,a2,glisse,longueur pour les essais.
Avant / après (frame 900) : 16:9 /tmp/m_t2h1_b900.png contre /tmp/m_t2g1_b900.png ; 21:9 (1920×820) /tmp/m_t2h2_b900.png contre /tmp/m_t2g2_b900.png ; très large (1920×400) /tmp/m_t2h3_b900.png contre /tmp/m_t2g3_b900.png ; suite 16:9 /tmp/m_t2g1_b{300,540,720,900}.png ; référence mobile /tmp/m_t2z3_b900.png ; variantes rejetées /tmp/m_t2v1_b900.png et m_t2v3_b900.png. Avis honnête : le tapis régulier de copies identiques est cassé (largeurs et hauteurs variables), mais les mêmes formes de nuages restent reconnaissables. C'est la limite de « zone intacte + une seule texture ».

E. MENU DE DÉPART
Établi : plaque « Sauvegarde automatique » (cellule 4, data5) toujours visible avec son libellé. Sans data5 : état 3 (grisé), texte gris, aucune zone tactile (ni clic, ni survol, ni validation clavier). Avec data5 : normale et active, libellé du moteur conservé.
Audit de l'original (désassemblage) : code 0 = disponibilité de data5 ; le moteur n'envoie le libellé (4,1) que si data5 est valide ; l'original CACHE la plaque 4 sans data5. Les cellules 0/1/3 (type 53) sont grisées par le moteur quand elles sont indisponibles ; les listes de type 54 n'ont pas d'états. Le moteur ne bloque pas la validation d'une cellule grisée, c'est Unity qui coupe le test de contact pour les états 2/3/4 (BUTTON_STATE_*) ; la visionneuse fait désormais de même.
Choix : grisée plutôt que cachée (« je te laisse choisir »). DQ_AUTO_CACHEE=1 rétablit l'original (cachée).
Comportement changé : plaque 4 (nouvelle visibilité) ; texte gris des plaques grisées ; Continuer/Reprendre/Supprimer grisés ne sont plus cliquables.
Vérifié avec deux jeux de sauvegardes (copies dans /tmp, data5 retiré de la copie) : sans /tmp/m_t2p1_b380.png ; avec /tmp/m_t2p2_b380.png. Clic réel sur la plaque grisée : rien ne se passe (/tmp/t2c1_sheet.png), Entrée valide « Continuer ».
Non vérifié : rendu du shader gris d'origine et gris du texte sur mobile (texte gris = choix de visionneuse, Supposé) ; libellé de secours (chaîne FR du patch supposée).

NON VÉRIFIÉ (global) : Windows ; fenêtres plus larges que 4,8:1 ; fenêtre 720×1280 réelle par l'utilisateur (testée sous xvfb seulement) ; cap du dragon contre une capture mobile.

NOTES DOC À FUSIONNER (pas écrit dans docs/) :
- Culling : Cull Back = horaire à l'écran, donc glFrontFace(CW).
- Zoom héros à exclure quand le sprite 0 est caché (ev01, et toute carte semblable).
- Dragon : posé une fois, trajectoire = clips FBX Take 001 puis Take 002 à l'image 662.
- Table des états de bouton 0 normal, 1 enfoncé, 2 invisible, 3 gris, 4 inversé ; hit-test coupé pour 2/3/4.
- Le moteur cache la plaque 4 via le code 0 ; le moteur ne bloque pas les clics sur cellules grisées.
- Méthode et constantes du ciel ; variables d'environnement DQ_CIEL_COPIES, DQ_CIEL_PARAMS, DQ_AUTO_CACHEE, DQ_SANS_CREDITS, DQ_FBXLOG, DQ_FBX_CULL.
- La vignette (réglage utilisateur) rend les bords de la zone portrait différents du mobile ; à couper pour comparer 1:1.

PIÈGES DE FUSION :
- window.py, zones touchées (par fonction) : import de ciel_titre (après `import fbx`) ; suppression des constantes TITRE_HAUT et TITRE_DRAGON_HAUT (~l.112) ; Jeu.__init__ ligne carte_ext/ciel_ext/_M_ville/_aspect_ville (l.181) ; _camera_ville (condition `carte_nom != 'ev01'` sur le zoom héros, yoff sans TITRE_HAUT) ; _maillages_combat (retrait de _decalage_credits et de _credits_cache, DQ_SANS_CREDITS conservé) ; _charger_carte (ev01 : appel de _ciel_titre) ; nouvelles méthodes _ciel_titre et _tracer_ciel (avant _calcul_hd_decor) ; _tracer_decor pas 0 (appel _tracer_ciel) ; _tracer_fbx (glFrontFace CW, translation mvp retirée) ; _dessiner_menus (type 53 : centrer_menu puis plaque_auto) ; rendu ville (`self._M_ville = M; self._aspect_ville = aspect` avant _tracer_decor(True)).
- ui_menu.py : boutons() ignore désormais les états 2/3/4 dans TOUTES les fenêtres ; ajouts plaque_auto, textes_grises, etat_actif, vals_code, auto_grise.
- engine.py : rotation par défaut du paquet 31 = (0,0,0) ; DQ_FBXLOG dans le paquet 32.
- data.py et map_objects.py viennent de ac4cb9b : conflit ou doublon probable à la fusion de la branche coffres (prendre une seule version ; cache renommé carte9, ancien cache invalidé).
- Tests nouveaux : tools/test_titre_ciel.py, test_start_menu_plate.py, test_title_camera.py.

Scripts de capture réutilisables : /tmp/t2_final.sh, /tmp/t2_zone2.sh, /tmp/run_t2.sh (SAVES=...), /tmp/t2_diff.py ; sauvegardes de test /tmp/sv_t2_sans, /tmp/sv_t2_avec.

---

## Agent a3150b360db4a6624 — 02/11 10:22

RAPPORT HCB (historique des combats : capture des résultats), branche `agent44-histocombat` (worktree /home/claude/wt44-histocombat, base 6580393). Arbre propre. 3 commits : 41b0792, 7ca0446, 17729a8 (pied de page 2 lignes). Fichiers touchés : UNIQUEMENT les 2 NOUVEAUX `dq4_pc/historique_combat.py` (283 l.) et `tools/test_historique_combat.py` (552 l.). Aucune ligne modifiée dans window.py / engine.py / history.py / ui_history.py / pause.py. pyflakes propre. Pas de push.

== API fournie ==
`class CapteurCombat` : `__init__(moteur)` (crochets en LECTURE seule, rien écrit dans la mémoire du moteur ; se désactive proprement `actif=False` si le moteur n'est pas celui étudié), `maj(moteur) -> list[dict]` (une fois par image après `mo.step`, ne lève jamais), et `CapteurCombat.pour(mo)` (capteur unique par moteur, créé à la 1re demande, crochets posés une seule fois).
dict = `{'t': g_Game+4 (1/60 s) à la fin du combat, 'ennemis': [{'nom','total','vaincus'}, ...] (1 entrée par espèce, ordre d'apparition, nom français affiché), 'or': int, 'xp': int, 'issue': 'victoire'|'fuite'|'defaite'}`.
Partie pure réutilisable : `Suivi`, `fabriquer_combat`, `nom_de_plaque`, `noms_des_groupes`, constante `ISSUES`.
xp = valeur PAR MEMBRE lue dans le message (« Chaque membre de l'équipe reçoit N points d'expérience », après doublement éventuel) ; or = total de l'équipe (« L'équipe reçoit M pièces d'or »). or/xp = 0 pour fuite et défaite (le moteur ne verse rien : vérifié). Donnée absente = 0 / nom 'Monstre'.

== LA ligne d'intégration (au choix du lead, dans window.py juste après la ligne 2611 `self.historique.maj(mo, ...)`, ou dans le Historique.maj du lead) ==
`for combat in HC.CapteurCombat.pour(mo).maj(mo): <consommateur du lead>(combat)`   (avec `import historique_combat as HC`). Rien à créer ailleurs.

== Établi (mesuré sur le vrai moteur Unicorn, sauvegarde 1, combats forcés) ==
- Victoire : dict identique au texte du jeu (« reçoit N points d'expérience », « N pièces d'or ») ET à la mémoire (or du groupe avant/après ; expérience de chaque membre avant/après). Test de mutation : un xp faussé de +1 fait échouer le test.
- Plusieurs espèces (2 et 4, ordre d'apparition vérifié), plusieurs membres (Ragnar gagne, Doc invité n'en gagne pas bien que le message dise « chaque membre »), doublement d'or/xp (BaseAction::doubleFlag_ : le dict donne le nombre du message).
- Fuite réussie après tentatives ratées (BattleExecEscape::setup tire à CHAQUE tentative, pas seulement à la réussite) et fuite après une mort : issue 'fuite', or/xp 0, vaincus partiels corrects.
- Défaite / game over atteint (monstre n°150 ×3) : issue 'defaite', or/xp 0.
- Deux combats d'affilée : 2 dicts distincts, t croissant.
- Combat interrompu par un état instantané chargé (en ville, ou à mi-combat) : rien de faux, pas de plantage, combat suivant bien rapporté. Capteur créé en plein combat ou après d'autres combats (blocs déjà traduits, ctl_flush_tb) : correct.
- Noms : balayage des numéros 0..187 : pour tous les monstres ordinaires le nom du dict = nom du message d'apparition du jeu (plaques moteur type 31, une plaque = un groupe).
- Coût de maj : hors combat 0,3 à 3 µs/image (contre 0,7 à 1,5 ms par pas du moteur), en combat ~46 µs en moyenne.
- Tests : 57 tests OK (~60 s avec moteur). Purs : calcul (Suivi, noms, fabriquer_combat) + colle sur FAUX moteur (rupture d'état, images sautées, abandon après 20 images hors combat, erreurs avalées, garde-fou d'événements). Moteur réel facultatif : `DQ_APK="/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks" DQ_SAVES=/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes python3 tools/test_historique_combat.py` (écritures dans un dossier temporaire, ignorés si les variables manquent). Sans xvfb.

== Supposé ==
- Les noms de plaque sont fiables jusqu'à la 1re mort (au-delà les correspondances ne sont plus sûres : nom 'Monstre' pour une espèce arrivée plus tard, ex. renfort invoqué).
- Un trait d'union en fin de ligne de plaque est recollé sans espace : « Scara-somniaque », « Typhon-phonphon », « Pterrori-dactyle » (cohérent avec le message). Cas ambigu : « Psaro l'Exter-minateur » (coupure de mot ou vrai tiret ? le moteur ne le dit pas).
- Issue 'fuite' déduite (aucune routine de victoire ni drapeau de défaite, combat terminé) : cas d'un monstre qui s'enfuit seul = même issue.

== Non vérifié ==
- Combats de scénario / boss scriptés (BattleScriptManager) : noms de boss lus (Pruslas, Rashaverak, Aamon, Barbatos, Lord Lionel, Dickenz...) mais pas confrontés à un message d'apparition (le jeu n'en émet pas) ; victoire/défaite scriptée non jouée.
- Monstres qui fuient d'eux-mêmes, Windows/GPU réel (test moteur seul).
- Autres sauvegardes que la 1 (groupe de 2 membres).

== Limites à connaître (par conception) ==
- Un combat dont le début n'a pas été vu (état chargé en plein combat, capteur créé en plein combat) n'est JAMAIS rapporté (plutôt rien que du faux).
- Un emplacement vidé puis re-rempli par le même monstre dans la même image serait sous-compté.
- L'abandon d'un combat sans endBattle (retour au titre) : suivi jeté après 20 images hors combat.

== Pièges de fusion ==
- Ne PAS mettre `maj` dans une boucle qui l'appellerait plusieurs fois par image du moteur : appeler exactement une fois par `mo.step` (le delta d'images est comparé : écart >8 ou état remplacé = rupture, suivi abandonné).
- `Moteur.etat` est remplacé par etats.appliquer : le capteur le détecte, mais garder le consommateur du lead indépendant de l'objet etat.
- Les dicts sortent à l'image où endBattle s'exécute ; 't' est l'horloge de jeu (même base que historique.Capteur.temps_et_cle).
- Le texte brut des messages de combat contient « ; » et « $ » (marques de coupure du patch) : ne pas les confondre avec les noms de monstres, qui sont déjà nettoyés ici.

== Notes à fusionner dans docs/ (à ton choix) ==
- Crochets (symboles) : début `_ZN6status11PartyStatus11startBattleEv` ; mort `_ZN19BattleActorManager216execMonsterDeathEi` (x1 = indice parmi les emplacements OCCUPÉS) ; victoire `_ZN23BattleExecDefeatMonster10initializeEv` ; fuite (tentative) `_ZN16BattleExecEscape5setupEv` ; fin `_ZN6Global9endBattleEb` (bit0 = anéantissement, + drapeau g_BattleResult+0x509).
- Mémoire : g_Party+0x2e0 or du groupe, +0x2f8 expérience du combat (par membre), +0x2fc or du combat (équipe) ; g_Monster 12 emplacements à +8, pas 0x538, +0x4f8 n° de monstre (0xffffffff = vide), +0x4fc n° de groupe ; expérience d'un membre = originalPlayer_+0x530*k+0x60 (0xffffffff = n'en gagne pas).
- Plaques de monstres : Moteur.ui fenêtre type 31, `dispo` = nombre de groupes, plaque j = j-ième groupe (indice de groupe trié) ; elles n'arrivent qu'à l'ouverture du choix de cible (pas au début du combat) ; texte « Nom\n\n\t×3 » ou « Début \n\nsuite » pour un nom coupé.
- Forcer une rencontre en test : crochet sur `BattleRoot::setupMonster`, écrire dans Encount (`Encount::getSingleton`) les n° à +0x34+4j et les nombres à +0x44+4j ; lancer avec `Global::startBattle(mo._global())`.

== Faits mémorisables (source : cette mission, mesures sur le moteur) ==
Aucune préférence utilisateur nouvelle. Faits projet : le moteur ne verse ni or ni xp pour une fuite ; BattleExecEscape::setup tire à chaque tentative de fuite.

---

## Agent aba2eb4af16a27785 — 02/11 10:24

RAPPORT PAQ (agent 44, paquets moteur ignorés) — version complète, mesures du dernier lot GL incluses. Worktree /home/claude/wt44-paquets, branche agent44-paquets, base ab22007. 2 commits, arbre propre : a598be1 (PAQ-1, paquet 33) et c8681df (PAQ-2, paquet 13). Trailer à deux lignes sur les deux. Rien poussé.

1. TABLEAU DES CONSTATS
| ID | quoi | preuve | statut | classe | corrigé ? | effort |
| PAQ-1 | Paquet 33 (teinte du décor) ignoré | `cmd_map_color_rate` RVA 0xD14E44 → `FldObject.m_color` (ville/combat) ou `Field.SetColor` (monde) ; `update_material_color` RVA 0xCD79F4 : Material.color = _OrgColor × m_color sauf matériau sans texture principale ou dont le nom de texture contient « tz_ » ; shaders fld_* décodés (blob LZ4, GLES3) = texture × couleur de sommet × _Color, saturé à l'écriture ; sprites/ombres/UI non touchés | Établi | oubli | oui, a598be1 | — |
| PAQ-1b | _OrgColor = (1,1,1,alpha), pas le _Color d'asset | `FldObject.save_org_color` RVA 0xCD811C re-désassemblé (s0 à s2 = 1,0 puis SetColor("_OrgColor")) ; précision du coordinateur confirmée | Établi | bug de cache (data.py) | non : le coordinateur le fait (branche audit2-histo, cache carte9 → carte10). Mon uniforme `teinte` reste valable (blanc = neutre) ; commentaires corrigés dans a598be1 | — |
| PAQ-2 | Paquet 13 bit 0x800 (échelle sprite) jeté | `cmd_chara` RVA 0xD12EA8 : Chara.SetScale → localScale = 1,8 × s sur le panneau ; balayage 529 cartes / 1062 personnages | Établi | oubli | oui, c8681df | — |
| PAQ-2b | Valeurs 0,025 à 0,08 (« 0,045 / 0,059 » de l'audit) = valeur de départ de la 1re mise à jour (placement), suivie de 1,0 en une image | sweep13 | Établi | — | ignorées dans le code | — |
| PAQ-2c | Hypothèse de l'audit « sprites mal dimensionnés dans mlb1a » | mlb1a : 0,7383 de l'image moteur 23 à 438 pendant l'ÉCRAN NOIR d'ouverture, puis 0,74 → 1,0 en 10 images ; en GL le héros est visible quand il vaut déjà 1,0 : captures avec / sans échelle identiques (1 px de bruit). ev07 (0,9519) : 1514 px changés (0,2 %), sprite 5 % plus petit | Établi (réfuté pour mlb1a) | — | — | — |
| PAQ-3 | Paquets 16/17 : poses couchées (dormeurs) non rejouées | mlm2f1 : paquet 16 = 0xc000508 / 0x509 (personnages 8 et 9, bit sleep) ; capture /tmp/m_paqD_mlm2f1_b300.png : l'homme du lit est affiché assis/debout ; mlb1a : sleep posé à l'image 20 puis retiré à 21 (sans effet) ; taf1 : 17 [1040, 1863] (pas de dormeur évident, /tmp/m_paqD_taf1_b300.png) | Établi (écart visible) ; mécanisme Supposé | oubli | non | 1 à 2 jours : shader CharaSleep, `_sleepMatrix`, `CalcLieBillboard` (0xCCD1A8), `SetSleepDir` (0xCCC5A0), `lieSetPosition` (0xCCCED4), `SetSleepNear` ; vérifier sur mlm2f1 |
| PAQ-4 | Paquet 18 (`changePose`) | 0 carte sur 529 | Établi (jamais émis au chargement) | oubli sans effet observable | non | — |
| PAQ-5 | Paquet 6 (`fld_event_anim`) | `cmd_fld_event_anim` RVA 0xD1298C : ≥ 0x1000 → `FldObject.SetCameraNo(v & 0x3fff)` ; sinon `SetEventAnimation(v)` (0xCD637C) ; 0/529 au chargement, déclenché par scripts | Établi (aiguillage) ; format FEAN Non vérifié | oubli | non | ~1 jour (données FEAN, rejeu) ; vérifier sur une scène scriptée |
| PAQ-6 | Paquet 30 (`field_scale`) | `cmd_field_scale` RVA 0xD12794 : int ≥ 0 → `Field.SetFloatingObject` ; flottant → `Field.SetScale` (0xCD353C) : orthographicSize = base × s + `FloatingObject.SetScale` sur chaque objet flottant ; émetteurs : ballon (`balloonExec`, `downBalloon`, `rideBalloon`, `setScriptBalloon`) | Établi (formule du zoom) ; base de l'échelle et caméra du monde Non vérifié | oubli | non | 0,5 jour ; il faut une sauvegarde en ballon (aucune) |
| PAQ-7 | Paquet 34, effets 3/5/6 | `cmd_screen_effect` RVA 0xD15024 → `Capture.ScreenEffect` RVA 0xCC6474 : (v & 0xf) 3 → `Tabi` (bit 7 en paramètre), 5 → `DarkLamp` (bit 7), 6 → `Riremito`, sinon `BattleEffect` (seul le 4 est rejoué) ; coroutines | Établi (aiguillage) ; formules Non vérifié | oubli | non | ~1 jour par effet |
| PAQ-8 | Paquet 1 (`fld_color`) | `cmd_fld_color` RVA 0xD12C98 → `FldObject.calculateExecSepia` ; aucun émetteur, 0/529 | Établi (cible) ; inutilisé Supposé | décision | non | — |
| PAQ-9 | Paquet 27 (`field_load`) | contourné : monde lu dans la mémoire du moteur (`_lire_monde`) ; ma branche remet seulement la teinte à neutre | Établi | décision | partiel | — |

2. CORRECTIONS (un commit par paquet)
- a598be1 PAQ-1 : `Etat.teinte` (engine.py : remise à neutre au paquet 0 et au paquet 27, branche du 33) ; nouveau `dq4_pc/teinte_carte.py` (reconnaissance des groupes « tz_ » : liste des path_id lue UNE fois dans le paquet de données, ~3 s + ~800 Mo, dans un thread, gardée dans `tz_cles.json` du cache ; repli : tout est teinté) ; window.py : uniforme `teinte` dans le fragment (clamp(rgb × teinte)), teinte par groupe dans `_tracer_decor`, et dans `_tracer_champ` (tuiles + symboles du monde ; sprites non). Interrupteur `DQ_SANS_TEINTE=1`. Teinte neutre = chemin inchangé.
  Mesures : dab1 (neutre) base / new / off = 0 pixel de différence ; mlb1a (teinte réelle 1,25/0,65/0,75 émise par le moteur) : 15,3 % des pixels changés, rendu violet (/tmp/m_paqA0_mlb1a_b420.png avant, /tmp/m_paqA1_mlb1a_b420.png après) ; `DQ_SANS_TEINTE=1` sur mlb1a = ancien code (0 px à l'image 200, 1 px de bruit à 420) ; teout1 avec les valeurs du moteur forcées (1,3/0,7/0,55) : 97,8 % des pixels, moyenne RGB 86,9/108,9/114,7 → 110,4/76,8/63,8, rendu orangé (/tmp/m_paqB_teout1_base_b420.png → /tmp/m_paqG_teout1_f_b420.png) ; mlout1 forcée (1,25/0,65/0,75) : 97,5 %, 65,6/100,8/57,4 → 80,2/66,6/44,0 (/tmp/m_paqG_mlout1_off_b420.png → _f_) ; carte du monde slot 4, teinte forcée (0,8/0,8/1,1) : 99,6 %, 67,0/105,7/135,0 → 53,9/84,9/148,0 (/tmp/m_paqG_monde_off_b200.png → _f_). La fenêtre de message translucide est assombrie par transparence, non teintée. Les sprites de la carte du monde n'ont pas été inspectés sur l'image.
- c8681df PAQ-2 : champ `ech` (1,0 par défaut) ; `t == 13` : si bit 0x800 et position déjà posée, `ech = fl[0]` (la 1re valeur, celle du placement, est ignorée) ; window.py, branche `cam3d` : panneau × k (borné 0 à 8), pieds fixes, décalages de profondeur à l'échelle k ; ombres non mises à l'échelle (Supposé) ; `DQ_SANS_ECHELLE=1`. Test : `tools/test_teinte_carte.py` (18 tests OK, 1 ignoré sans APK). Vérification : dab1 (échelle 1,0) identique à 1 px près (bruit également présent entre deux passes du même code) ; mlb1a identique aux images visibles ; ev07 1514 px.
- Fichiers touchés : dq4_pc/moteur.py, dq4_pc/fenetre.py, dq4_pc/teinte_carte.py (nouveau), tools/test_teinte_carte.py (nouveau). data.py, map_objects.py, `_saisie_menu` non touchés.

3. NOTES À FUSIONNER DANS docs/ (texte prêt)
- notes-technique (remplacer la ligne ~233 « Non reproduit : paquet 33 … ») : « Paquet 33 (`cmd_map_color_rate`) : trois flottants → `FldObject.m_color` (ville/combat) ou `Field.SetColor` (monde). `FldObject.update_material_color` (RVA 0xCD79F4), chaque image : Material.color = `_OrgColor` × m_color, sauf matériau sans texture principale ou dont la texture a « tz_ » dans son nom (lampes, bougies, vagues… : non teintés). `_OrgColor` = (1,1,1, alpha de `_Color`) (`save_org_color`, 0xCD811C) : la couleur RGB `_Color` de l'asset n'est jamais utilisée en jeu. Shaders fld_* : texture × couleur de sommet × `_Color`, saturé à l'écriture (teinte > 1 possible). Sprites, ombres, bulles, interface : non teintés. Viewer : uniforme `teinte` (window.py), groupes « tz_ » par `map_tint.py` (`tz_cles.json`), `DQ_SANS_TEINTE=1` pour comparer. La valeur dépend du fuseau horaire du moteur et persiste d'une carte à l'autre : à froid depuis nos sauvegardes seule mlb1a (1,25/0,65/0,75) en émet une ; chargées après elle, mlout1, mmout, mlout2 reçoivent la même et teout1 (1,3/0,7/0,55) (sonde pk33c) ; caf1/ev02 : 0,804/0,807/1,102, en fondu lent. »
- notes-visionneuse (lignes ~72/83/141) : « Paquet 13 bit 0x800 = Chara.SetScale (localScale = 1,8 × s, panneau seul), appliqué (`DQ_SANS_ECHELLE=1` pour couper). Seules mlb1a (0,7383 pendant l'écran noir d'ouverture, puis 0,74 → 1,0) et ev07 (0,9519) ont une valeur ≠ 1 après le placement. Poses couchées (paquets 16/17) : toujours NON rejouées, visibles sur mlm2f1 (dormeur du lit affiché assis). FEAN / paquet 6 et effets 3/5/6 du paquet 34 : aiguillage lu (`SetEventAnimation` / `SetCameraNo` ; `Capture.Tabi` / `DarkLamp` / `Riremito`), contenu non rejoué. Paquet 30 : `Field.SetScale` = orthographicSize × s + FloatingObject.SetScale, non rejoué. »
- Piège de test : un lancement `DQ_VILLE` d'une seule carte ne reproduit pas les teintes de l'audit (balayage séquentiel, fuseau horaire hérité). Charger d'abord mlb1a (chaîne `gl_chaine.py`) ou forcer `TEINTE`.

4. NON VÉRIFIÉ / À SAVOIR
- Windows, vrai GPU, calcul de `tz_cles.json` sur le PC de l'utilisateur (~3 s + ~800 Mo une fois ; thread ; sans lui tout est teinté).
- Teinte du décor de COMBAT et teinte du monde émise par le moteur (jour/nuit, marais) : non capturées en vrai. Carte du monde testée seulement avec teinte forcée.
- Ordre de saturation : mon shader fait clamp(tex × sommet × teinte), identique à l'original une fois le cache nettoyé de la couleur d'asset (travail du coordinateur, data.py). Tant que le cache carte9 garde `_Color` d'asset, les matériaux à _Color ≠ blanc (décor de nuit en combat) restent faux avec ou sans teinte. Pas de conflit attendu avec audit2-histo.
- Mesure « 3 cartes » : mlb1a avec teinte réelle ; teout1 et mlout1 avec les valeurs du moteur forcées (lanceur `.../scratchpad/gl_teinte.py` + `run_gl_teinte.sh`). Tentative de chaîne mlb1a → mlout1 : la teinte réelle est bien émise (journal TEINTE) mais l'écran reste noir (événement d'ouverture de mlb1a en cours) : image inutilisable.
- Pièges de fusion : window.py (branche `cam3d` des sprites, shader FRAG, `_tracer_decor`, `_tracer_champ`) et engine.py (`Etat.appliquer`, branches 13/33/27) ; l'agent « casino » touche les parties 0xf/0x10 et `_saisie_menu`.
- Le scratchpad de session est PARTAGÉ avec d'autres agents (mon p2.py y a été écrasé) : mes outils sont dans /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/paq44/ (gl_ech.py, gl_chaine.py, pk33.py, pk33c.py, pech.py, batch*.sh).
- Captures utiles : /tmp/m_paqA0_mlb1a_b420.png, /tmp/m_paqA1_mlb1a_b420.png, /tmp/m_paqB_dab1_{base,new,off}_b{300,420}.png, /tmp/m_paqB_teout1_base_b420.png, /tmp/m_paqG_teout1_f_b420.png, /tmp/m_paqG_mlout1_{f,off}_b420.png, /tmp/m_paqG_monde_{f,off}_b200.png, /tmp/m_paqG_mlb1a_off_b420.png, /tmp/m_paqC_ev07_{ech,sans}_b420.png, /tmp/m_paqC_mlb1a_{ech,sans}_b420.png, /tmp/m_paqE_mlb1a_{ech,sans}_b{340,380,400,430}.png, /tmp/m_paqD_mlm2f1_b300.png, /tmp/m_paqD_taf1_b300.png.

À retenir pour la session principale : (1) le scratchpad de session est partagé entre sous-agents, utiliser un sous-dossier par agent ; (2) `pkill -f` sur un nom de script présent dans la ligne de commande du shell tue ce shell ; (3) la teinte du paquet 33 dépend de l'état de fuseau horaire du moteur et persiste d'une carte à l'autre.

---
