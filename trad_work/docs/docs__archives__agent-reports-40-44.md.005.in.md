## Agent a4b9be7dca00268af — 01/11 22:13

RAPPORT agent-recherche (worktree /home/claude/wt-recherche, branche agent-recherche, base main 1e87ca6, aucun push). 2 commits : 48333ba (enquête 2) et 69e588f (enquête 1). Arbre propre.

=== RÉPONSE POUR L'UTILISATEUR (à relayer telle quelle) ===

ENQUÊTE 1 : assombrir ou flèche ?
Sur mobile il n'y a pas vraiment de choix entre les deux : ce sont deux choses sans rapport.
- L'assombrissement, c'est l'état « appuyé ». Il n'existe que pour le doigt. Quand on pose le doigt sur un bouton, le jeu le met en « enfoncé » : la plaque change de motif (décalage de texture), ou, pour un bouton qui n'est qu'une icône, sa couleur passe à 75 %. Tant que le doigt reste sur le bouton, il reste sombre. Si on glisse le doigt hors du bouton, il se rallume ; si on revient, il se rassombrit. On relâche sur le bouton pour valider.
- Il n'y a PAS de flèche de sélection dans les menus mobiles, ni de curseur clavier/manette. Sur mobile il n'y a donc pas de « survol » non plus : on appuie ou on n'appuie pas.
- Les flèches qu'on voit dans le jeu ont d'autres rôles : le ▶ doré du tour de combat (BattleUpCursor), les boutons ◀ ▶ de changement de page, les ▲▼ sur certaines plaques, et le ▼ de fin de page d'un texte. Ce ne sont pas des marqueurs de sélection.
- Le message « curseur » que le moteur envoie ([4,n]) est ignoré par Unity.
Donc votre convention PC (cadre jaune souris, flèche clavier, assombrissement au clic) est une addition PC cohérente : seul l'assombrissement au clic vient de l'original.
Écart corrigé dans la visionneuse : une flèche de page ◀ ▶ appuyée ne s'assombrissait pas (elle ne faisait que s'éclaircir au survol), et une plaque restait sombre si la souris sortait du bouton pendant l'appui. C'est corrigé : flèche appuyée à 75 %, plaque/flèche qui se rallument quand le pointeur sort et se rassombrissent quand il revient.

ENQUÊTE 2 : le sort « Morph »
- Ce n'est pas un sort de combat : c'est un événement d'histoire (église, la grenouille/lapin et Élisa). L'effet est un petit nuage animé (modèle 5902, 29 images, son 361) affiché sur le personnage qui se transforme.
- Vous aviez raison sur l'ordre : le nuage était dessiné DERRIÈRE le personnage (et un peu décalé, parce que la caméra de la visionneuse n'est pas celle du moteur). Dans Unity il se dessine après les personnages, donc devant. Corrigé : devant, et ancré sur le personnage.
- La latence venait du premier affichage : la texture du nuage n'était chargée qu'au moment d'apparaître (2,7 s mesurées, contre 0,05 s une fois en mémoire). Corrigé : ces textures d'effets (186) sont maintenant préparées en arrière-plan avec le reste (la première préparation dure environ 3 s de plus, une seule fois).
- Les autres effets (entailles du prologue, combat, titre) ont été comparés avant/après : identiques.

=== DÉTAIL PAR POINT ===

Commits (messages terminés par Co-Authored-By + Claude-Session, deux lignes séparées) :
- 48333ba Ville : effets-maillages devant les personnages et ancrés sur eux ; textures d'effets m\d{4} préparées en arrière-plan. Fichiers : dq4_pc/fenetre.py, dq4_pc/donnees.py.
- 69e588f Menus : flèche de pagination appuyée assombrie x0,75 et rallumée si le doigt sort. Fichiers : dq4_pc/fenetre.py, dq4_pc/ui_menu.py.
pyflakes : seuls les avertissements connus (sel, racine, em, ax) ; 'struct' inutilisé dans data.py existait déjà. py_compile ok. Régression : clic sur la fenêtre Objets pixel-identique.

--- Enquête 1 : Établi / Supposé / Non vérifié ---
Établi (désassemblage de GameAssembly, RVA) :
- MenuPortItem.Update 0xD0670C : pushState 1 (appui) -> SetPush(true) ; 2 (maintenu) -> SetPush(isHit), donc glisser dehors rallume ; 3 relâché. SetPush n'a que 4 appelants : seul le toucher pilote « enfoncé ».
- MenuParts.IButton : plaque (DisplayClass5_0.b__0, 0xD043CC) : enfoncé = décalage de texture (0,1875 ; 0) ; bouton-icône (ctor(Material) 0xCFF9C8, DisplayClass6_0.b__0 0xD0469C) : Material.color = 0,75 sur les 4 canaux RGBA ; variante sans effet.
- Aucune flèche/curseur de sélection de bouton dans le build mobile. Flèches : BattleUpCursor, boutons de page (part 10), ▲▼ sur plaques, ▼ MenuMessage.
Supposé : l'original teste le premier bouton touché dans l'ordre de m_buttonList, la visionneuse prend le plus haut (pas de différence vue).
Non vérifié / non codé (proposé) : l'état `etat` piloté par le moteur pour les boutons-icônes (<0 caché, sinon 0,75) est ignoré par la visionneuse (seules les plaques l'utilisent) ; `_est_bouton` n'accepte que les parts 7 et 10 alors que 22 noeuds icônes existent (16 part 10, 6 part 3) ; le curseur clavier/manette du PC est rendu comme une plaque assombrie (ajout PC, le mobile n'en a pas).
Captures : /tmp/rech/fleche_cmp.png, /tmp/rech/fleche_av.png, /tmp/rech/fleche_ap.png, /tmp/rech/plaque_cmp.png ; brutes /tmp/m_e1fl_*, /tmp/m_e1pl_*.

--- Enquête 2 : Établi / Supposé / Non vérifié ---
Reproduction : états de jeu enregistrés en headless (moteur ~700 images/s, très rapide, contre xvfb lent), scène de l'église mlb1a (Élisa sprite 143, grenouille 174, lapin 173). Trois Morph successifs vérifiés.
Établi :
- (a) paquet 21 [0, 5902] sur emplacement de maillage 0 -> texture m5902 (32x32), shader 3 DssaCharaTransparent, 29 images, SE 361. Éclaboussure de la grenouille dans la rivière : modèle 5917 (64x64). Entailles du prologue : 5303/5311. battle_effect.py n'est pas concerné (c'est l'éclatement de tuiles du début de combat).
- (b) latence : chargement synchrone à froid de m5902 depuis le datapack via UnityPy : 2718 ms au premier dessin (52 ms à chaud, 8,8 ms après préparation). Mesure avec DQ_TEMPS_IMAGES. Logs : /tmp/rech/ft_cold.txt, ft_warm.txt, ft_apres.txt.
- (c) ordre : files de rendu lues dans le datapack : Chara 3000, CharaShadow 2999, DssaChara 3100, DssaMonster0 3150, DssaMonster1 3200, DssaCharaTransparent et Riseup 3850 (ZTest Always, billboard). Les effets passent donc après les sprites. Le moteur place l'effet au milieu du segment (caméra moteur -> sprite) ; la caméra Unity réelle = position moteur + 4,0 vers l'avant, tangage -0,2 ; la caméra ville du visionneur (zoom, cam_dec, lacet, angle_cam) est différente, d'où le décalage.
Corrections : bloc de dessin des effets déplacé après sprites et icônes (sans test de profondeur pour le shader 3, sans écriture de profondeur) ; _ancrer_effets/_pos_effet/_cadre_jeu : retrouvent le sprite visé (t dans ]0,05 ; 1,5[, résidu < 0,05), mémorisent rapport de profondeur et écart angulaire, et les rejouent dans le cadre de la caméra du visionneur avec la position interpolée du sprite (repli : position inchangée). data.py : liste 'effets' (m\d{4}, 186 textures) ajoutée à _elements et preparer.
Régressions identiques : entailles du prologue (images 226-277), écran-titre, combat.
Captures : /tmp/rech/planche_av.png / planche_ap.png (angle -2,25) ; planche0_av.png / planche0_ap.png (angle 0) ; planche_m3.png, planche_m4.png (2e et 3e Morph) ; planche_frog_av.png / planche_frog_ap.png / diff_frog62.png (éclaboussure) ; brutes /tmp/m_morph_*, /tmp/m_morph0_*, /tmp/m_m3_*, /tmp/m_m4_*.
Supposé : taille et placement exacts du nuage d'origine (aucune capture du vrai jeu) ; le Morph de la nuit du village détruit (b0065000 ligne 63, copie du héros) suit le même mécanisme mais n'a pas été reproduit.
Non vérifié : si un monstre lance Morph en combat ; lien entre l'id 5902 et un fichier assets/effect/eNNN.dssa (pas de e5902.dssa, fichiers e001..e919) ; latence du premier SE 361 (son hors périmètre, testé --sans-son) ; éventuel « pop » des modes HD des sprites (EPX...) sur la texture d'effet (tâche d'arrière-plan).

--- Pièges de fusion ---
- data.py modifié hors périmètre (6 lignes : _elements + preparer). preparation.json est reconstruit une fois (clé 'effets' absente = liste périmée).
- window.py : le bloc d'effets-maillages a été retiré de la branche ville de _dessiner et réinséré après les icônes, avant self.prog.stop() ; _pas gagne tick + _ancrer_effets + _mesure ; nouveaux attributs effet_ancre et _cadre_vue (init + _appliquer_etat) ; fin de _camera_ville mémorise _cadre_vue ; _maillages_combat a un paramètre ville ; _cadre_jeu duplique une partie de _camera_ville (à resynchroniser si cette caméra change).
- Enquête 1 touche aussi window.py : on_mouse_drag (self.souris), bloc fe.sel_nd/appui_nd dans la boucle des menus (~l.1771), mode édition (fe.appui_nd = None). Conflits probables avec les agents Pause / éditeur d'interface / affichage.
- Anciens états de combat (/tmp/sv_b1) incompatibles avec le code actuel (AttributeError 'systeme'), dans les deux arbres ; état neuf : /tmp/rech/svc.

--- Recette de test ---
Prologue : saves Downloads (/mnt/user-data/uploads/Downloads/DQ Patch/jeux/DQ4/saves/20261007_190735), slot 2, puis mlout1 -> église -> parler à Élisa. Les scripts headless sont /tmp/rech/lib.py (Pilote) et h1..h19.py. Captures via /tmp/run_wt.sh, jetons @x@y survol, !x!y appui, ^x^y glisse.

--- À mémoriser (appris ici) ---
- Moteur headless ~700 images/s ; tests visionneuse sous xvfb lents ; mode test = un pas moteur par image de boucle (déterministe) (observé en testant).
- Scène Morph : save prologue (dossier Downloads ci-dessus), slot 2, mlout1 -> église -> parler à Élisa.
- Sprites : 174 grenouille, 173 lapin, 143 Élisa. Modèles d'effet : 5902 Morph, 5917 éclaboussure, 5303/5311 entailles.
- Les sauvegardes de l'utilisateur s'appellent « Solo » / « Sofià » (vu dans les dossiers de saves).
- Le build mobile n'a aucun curseur de sélection pour les boutons ; le curseur du portage est une addition PC (démontage de MenuPortItem.Update).

---

## Agent a43c4de91404229b5 — 01/11 22:19

RAPPORT agent-textes (worktree /home/claude/wt-textes, branche agent-textes, base main 1e87ca6)

COMMITS (2, propres, pied de page en deux lignes ; arbre de travail propre ; pyflakes : seuls les avertissements connus racine / ax / sel)
- 86428e2  Textes des menus : police d'origine SE-GARRIR, sans compression (bandeau de chapitre, plaques)   [points 2 et 4]
- eb2d216  Boutiques : gauche / droite changent la quantité de la rangée choisie   [point 3]
- Point 1 : aucun commit (rien de reproduit, pas de code changé).
Fichiers touchés : dq4_pc/ui_menu.py (+99 / −13 dans le commit police) et dq4_pc/fenetre.py (+3 lignes, dans `_saisie_menu`). pre_game.py inchangé (`hyodai1` y est déjà dans RESSOURCES, `ap_hyodai1.png`).
Un dernier passage sur le code après rebase (boutique de l'église, slot 1, police Garrick) est correct : /tmp/txt/fin1_sheet.png.

POINT 1 : texte du prologue sur écran noir — NON RÉSOLU
- Établi : message moteur 200119 = « @a@bEt c'est ainsi que commence notre histoire...\n@c0@ » (sans préfixe « *: », nom vide). La couche Unity (`MenuMessage`, RVA 0xCFA4B4, `NoticeReceive` 0xCFBA34) n'a que 4 types de canevas (cadres 192/193/194/194), le type 0 étant la boîte du bas. `NoticeReceive` n'agit que sur param[0] = 0..4 : type du canevas, curseur + rendu on/off, secousse (8), décalage de texture (défilement), texte de « qui parle ». Aucun mode sans cadre, centré ou lettre par lettre n'existe côté Unity. Le texte est un canevas 512x512 rendu par le moteur.
- Tenté sans succès : appel direct de `TownWindowSystem::openMessage` (ne montre rien en exploration, car `CommandWindow::MESSAGEWINDOW` appelle d'abord `InputControl::goNext(8)`, qui est refusé) ; un run complet du prologue en script (slot 2, captures /tmp/m_pro1_b2000..2750.png, résumé /tmp/txt/pro1_sheet.png) n'a atteint que l'exploration libre : il faut marcher jusqu'à la maison avant le dîner, ce qui est trop long à automatiser.
- Supposé : l'original affiche ce texte comme un message normal de type 0 (boîte du bas, même police Garrick que les menus, le moteur dessinant le canevas). Si le défaut vu par Sylfried est réel, il viendrait du contexte (boutons tactiles / HUD sur le noir, fondus, position de la boîte dans la fenêtre 16/9 ; `--msg-origine` la garde à sa place portrait) et non de la fenêtre. Il faudrait une capture de Sylfried (ou du mobile) à ce moment précis pour trancher. Non vérifié : l'aspect de l'original.

POINT 2 : bandeau de chapitre — CORRIGÉ
- Établi : la police des menus en langue 1 (anglais, celle du patch FR) est la police bitmap Unity SE-GARRIR (Font « Garrick », serif, 20 px, interligne 23,525, ascent 18,887, 218 glyphes dont le jeu français, atlas 256x256, filtre bilinéaire), pas GMaruGoPro-M (japonaise, utilisée à tort par la visionneuse). Sources : `MenuParts..cctor` 0xD03278, `LangParam.Apply` 0xCFD5E8, `SystemInit` 0xCF9A70, `CreateBuildTextMenu` 0xD02074. 1 px de police = characterSize × 0,1 unité ; largeur = somme des advances (pas de crénage). Glyphes « flipped » = transposés dans l'atlas.
- Image du bandeau : la seule texture de chapitre existante est `Menu/map/hyodai1` (450x225, ajustée en largeur) ; `Make_Chapter` (type 12) = quad `hyodai1` + nœud de texte 1532 (param 0, ancre 1, z 30) et nœud 1558 (param 1, ancre 4, z 17,5) ; le titre arrive dans le nœud 1558. L'image était déjà affichée ; seule la police était fausse. Aucune ressource supplémentaire dans RESSOURCES.
- Implémentation : classe `PoliceBitmap` + `extraire_garrir` (ui_menu.py) ; `preparer_ressources` extrait `ui_garrir.json` et `ui_garrir.png` de base.apk (fichiers optionnels : sans eux, repli sur GMaruGoPro-M). `Rendu._texte` utilise les métriques d'origine.
- Captures : /tmp/txt/cmp_chapitre.png (avant | après), /tmp/txt/avant_chapitre.png (prise en plein fondu, donc plus sombre), /tmp/txt/apres_chapitre.png.

POINT 3 : boutiques — CORRIGÉ (clavier et toucher vérifiés)
- Le curseur clavier garde la rangée entière. Dans les types 58 / 59 (Make_ShopBuy) et 63 (quantité de vente), gauche / droite (déplacement ZQSD, caméra flèches, L / R) envoient `[port, 1, rangée, 8 ou 4]`, comme le toucher d'une flèche (les rangées portent pad 16 + ◀ 8 + ▶ 4 sous un même buttonId).
- Établi : le moteur ne fait que ±1 (quantité 1 à 9 avec bouclage, les autres rangées reviennent à 1). Il n'y a pas de ±10 dans l'original, donc pas ajouté.
- Vérifié : touches (1→2→3, rangée 2, bouclage 9) et clics sur ◀ ▶ ; avant, les touches ne faisaient rien. Captures : /tmp/txt/shk2.png (après, clavier), /tmp/txt/shm.png (après, toucher), /tmp/txt/shkb.png (avant), /tmp/txt/shq.png (flux boutique), /tmp/txt/shs.png et shs2.png (vente), /tmp/txt/cmp_achat.png, cmp_qui.png, cmp_vente.png.
- Non vérifié : type 28, type 63 (écran de quantité de vente non atteint).
- Test des boutiques : `changeShopMenuPhase(phase)` via le harnais ouvre une boutique (2 = armes, 3 = armures, 0 = auberge, 1 = église).

POINT 4 : alignement sur le mobile — FAIT par construction
- Cause : la visionneuse utilisait la mauvaise police (GMaruGoPro-M) et comprimait en plus les textes trop larges. Les écarts texte / plaque sont maintenant ceux du mobile (le texte déborde comme sur mobile, sans compression ni police étrangère), ce que Sylfried acceptait.
- Captures AVANT / APRÈS de plusieurs fenêtres : /tmp/txt/ba4_sheet.png (avant) et /tmp/txt/aa4_sheet.png (après), grille 2x2 : liste des objets, menu d'objet, caractéristiques, Divers ; archives séparées avant_liste_objets / avant_menu_objet / avant_caracteristiques / avant_divers.png ; paires cmp_achat / cmp_qui / cmp_vente / cmp_chapitre.png.
- Supposé : placement vertical environ 1 px plus bas (modèle d'ancrage TextMesh). Non vérifié : aucune capture du mobile réel pour comparaison au pixel.
- `DQ_POLICE_GMARU=1` rétablit l'ancienne police (comparaison).

ÉTABLI / SUPPOSÉ / NON VÉRIFIÉ (résumé)
- Établi : police SE-GARRIR et ses métriques ; chaîne du bandeau (`Make_Chapter`, `hyodai1` seule image) ; mécanique quantité des boutiques (±1, 1..9) ; touches et clics boutique ; message 200119 sans mode spécial côté Unity.
- Supposé : l'original affiche le texte du prologue en boîte normale ; décalage vertical de 1 px.
- Non vérifié : l'aspect original du texte du prologue ; types 28 / 63 ; comparaison pixel au mobile.

PIÈGES DE FUSION
- ui_menu.py : changements dans `Rendu._texte` et `Textes.__init__`, plus nouvelle classe `PoliceBitmap` (avant `Textes`) et `extraire_garrir` ; les commentaires de `HAUTEUR_LIGNE` / `TAILLE_POLICE` les marquent comme replis. Conflit probable seulement si un autre agent retouche `_texte`.
- window.py : un seul bloc de 3 lignes inséré dans `_saisie_menu` avant le test « une seule colonne ».
- Les nouveaux fichiers optionnels `ui_garrir.json / png` font relire base.apk une fois par `preparer_ressources` ; les caches existants restent valables (repli si absents). Tout texte de menu change de police : les captures des autres agents (menu de départ, texte d'avant-partie, etc.) changeront d'aspect, c'est attendu.
- pause.py et l'aperçu de l'éditeur d'interface (window.py) utilisent toujours `ui_font.otf` (GMaruGo) : non touchés (hors périmètre).
- Cache privé de test : /tmp/uicache_txt (ui_garrir.* présents) ; le script de test supprime /tmp/m_NOM*.png, d'où l'archivage dans /tmp/txt/.

NOTES POUR docs/ (je n'ai rien écrit dans docs/)
- docs/technical-notes-dq4-port.md (mise en page des textes, vers l.85-100) est faux pour la langue 1 : la police des menus est SE-GARRIR (bitmap, 20 px, interligne 23,525, ascent 18,887, 1 px = characterSize × 0,1), pas GMaruGoPro-M ; pas de compression des textes.
- Titre de chapitre : nœud de texte 1558 de `Make_Chapter` ; image `Menu/map/hyodai1` seule.
- Boutiques : types 57 (racine), 58 / 59 (Make_ShopBuy : pad 16 + ◀ 8 + ▶ 4 par rangée), 60 / 61 (Qui va le porter ?, flèches buttonId −1), 62 (vente), 63 (quantité de vente) ; quantité 1..9 gérée par le moteur.
- Astuce de harnais : `DQ_APPEL="image:symbole:args"` avec /tmp/h_appel.py appelle une fonction du moteur ; `changeShopMenuPhase(phase)` : 0 auberge, 1 église, 2 armes, 3 armures.
- Texte du prologue : message 200119, `MenuMessage` n'a que 4 types de canevas ; tout rendu spécial serait côté moteur.

À RETENIR (mémoire, source : analyse IL2CPP et moteur de cette session)
- La police d'origine EN / FR des menus est SE-GARRIR (bitmap Unity) ; les notes techniques disent à tort GMaruGoPro-M.
- `changeShopMenuPhase(phase)` ouvre une boutique (2 armes, 3 armures).
- Atlas SE-GARRIR : les glyphes « flipped » sont stockés transposés.

CAPTURES UTILES (chemins absolus) : /tmp/txt/cmp_chapitre.png, /tmp/txt/aa4_sheet.png, /tmp/txt/ba4_sheet.png, /tmp/txt/shk2.png, /tmp/txt/shm.png, /tmp/txt/shkb.png, /tmp/txt/cmp_achat.png, /tmp/txt/cmp_qui.png, /tmp/txt/cmp_vente.png, /tmp/txt/fin1_sheet.png, /tmp/txt/pro1_sheet.png.

---
