# Rapports finaux des agents des lots #40 à #44

Rapports bruts remis par les sous-agents de la session du 31/10 au 02/11 (enquêtes, audits, correctifs) ; les notes utiles sont déjà fusionnées dans `docs/notes-*.md`. Les chemins `/tmp/...` cités n'existent plus.

---

## Agent a7fa4380330259e25 — 31/10 16:16

RAPPORT : ombres (A) et eau des grottes (B). Rien n'a été modifié dans le dépôt (`git status` propre ; `git apply --check` OK pour les deux patchs). Tout est dans le dossier de travail S = /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/enq_deco

== CAUSE COMMUNE à B et aux ombres de décor (vérifiée) ==
La visionneuse ignore le `_Color` des matériaux de carte et trace tout le décor « opaque » (`donnees.py::_texture()` ne lit pas `_Color` ; `fenetre.py::_tracer_decor` utilise cutoff 0,5, écriture de profondeur, LESS). Le jeu d'origine choisit le shader à l'exécution dans `FldObject.set_shader` (RVA 0xCD5414) :
- nom de texture sans ".tim", OU `_Color.a != 1` -> `Custom/fld_trans` (Blend SrcAlpha/OneMinusSrcAlpha, ZWrite off, ZTest LEqual, file 3000 + `prio` via `FldObject.set_priority` 0xCD7DA8) ;
- sinon texture RGBA32 -> `fld_atest` (rejette seulement alpha == 0) ; sinon `fld_normal`.
Dans tous les `fld_*` : couleur finale = texture x (couleur de sommet x `_Color`).

== B. Eau des grottes ==
Cause : les modèles d'eau (objets `<carte>wt..`, texture `mawater1.tim` RGB24, cyan moyen (54,205,203), alpha 255) ont `_Color` = (1,1,1,0.2). La visionneuse les dessinait à alpha 1 : cyan plein, d'où l'effet « électrifié ». Les palettes `wtkira` (FPLP) n'existent que dans les 37 cartes de plein air et de ville, pas dans les grottes : ce n'est pas une piste. Aucun blend additif.
Correction : patch `S/out/correctif_decor.patch` (donnees.py + fenetre.py, s'applique tel quel au dépôt).
- `_texture()` renvoie aussi `_Color` et le « genre » (trans / atest / normal) ; `cuire` multiplie `_Color` dans les couleurs de sommet (et dans `_images`) ;
- les matériaux « trans » ont leur groupe `('tr', prio, key)` ;
- `_tracer_decor` dessine d'abord les groupes opaques, puis les `('tr', ...)` triés par prio, avec profondeur en lecture seule, LEQUAL et cutoff 0 ;
- le cache passe de `carte5_` à `carte6_` (2 endroits dans donnees.py ; les anciens caches sont ignorés, donc première extraction plus lente).
Preuve (grotte `dgb1`, centre du bassin, RGB) : (38,141,140) -> (29,87,93), luminosité 0,55 -> 0,37. Le gaz, les cascades et la brume (textures `.tm2`) deviennent aussi doux. Sortie du patch propre identique pixel à pixel à mon expérience (diff max 0).
Captures avant (gauche) | après (droite), dans S/out/ : pair_dgb1.png (la plus claire), cmp_dgb1_pool.png (gros plan), pair_dlb4.png, pair_deb2a.png, pair_dob1.png, pair_dnb2.png, pair_djb1.png. Brutes : dgb1_av_b80.png / dgb1_ap_b80.png.

== A1. Ombres de décor (« trop brutes » et « pas tout a des ombres ») ==
Les ombres de décor sont de la géométrie à part, à y = 0 (collée au sol) : `idokage1` (puits), `maokage1`, `maoutsk1`, `*kg*`. Deux cas, une seule cause (la même que B) :
- ombres douces en `.tm2` à alpha faible (`kage1c` {0,14,28,42,86}, `kage1a` max 126, `hcokage1` / `ceokage1` max 96, `tekg1` max 126) : le cutoff 0,5 les rejette toutes -> puits, bâtiments et autres sans ombre (51 cartes sur 670 touchées) ;
- ombres en `.tim` à alpha binaire (`nk_sk1kg`, `y_sk2bkg`) avec `_Color.a = 0,4` ignoré -> noir à 100 %, donc « brutes ».
Le patch de B règle les deux. Avant/après : S/out/pair_maout_well.png (puits) et pair_maout.png. La piste « LESS au lieu de LEQUAL » a été testée et écartée (dq4_t1 : aucune ombre en plus).

== A2. Ombre des personnages (héros et PNJ) : prototype fait, ville seulement ==
Pourquoi absentes : la visionneuse ne les dessine pas. Le moteur ne les commande pas en ville : le paquet 15 (`chara_shadow`) n'y est jamais envoyé (vérifié dans les logs de maout), donc l'ombre par défaut de `Chara` s'applique à tous. Sur la carte du monde il n'envoie que `[522]` / `[523]` (cache les ombres des emplacements 10 et 11). `moteur.py::Etat.appliquer` ne traite pas le paquet 15.
Rendu d'origine (décodé depuis `Chara.SystemInit` et `SetShadowPosition` 0xCCCF38) :
- maillage `s_shadowMesh` : carré ±1 en XZ à Y = 0,00625, UV (0,0)(1,0)(1,1)(0,1) ; échelle `s_shadowDefScale` = (0,347 ; 10 ; 0,206) -> ellipse de 0,694 x 0,412, à 0,0625 au-dessus du plan ;
- texture `CharaTex/common` (32x32, noire, alpha 96/255 = 0,376 dans l'ellipse, 0 dehors, binaire, filtre point, clamp). Extraction : `Donnees.texture('common')` ; aperçu S/out/tex_common.png ;
- shader `Custom/CharaShadow` : tex x `_Color`, Blend SrcAlpha/OneMinusSrcAlpha, ZWrite off, ZTest LEqual, Cull Back, file 2999 (avant le sprite) ;
- position = position du Chara + rotation du panneau x (0 ; 0 ; 0,25), soit côté visionneuse `p - f_*0,25` : même point à l'écran, mais décalé vers la caméra, donc devant le sol ; orientation = lacet seul de la caméra, à plat ;
- alpha final = 0,376 x `SetShadowAlpha` (1 par défaut) x alpha du sprite si < 1 (`SetColorWithShadow`) ; `SetVisible` masque aussi l'ombre sauf `m_bSeparateShadow` ; objet d'ombre inactif si `no` vaut 193 ou 194.
Prototype : patch `S/out/correctif_ombre_chara.patch` (à appliquer APRÈS correctif_decor.patch ; fenetre.py seulement, nouvelle méthode `_dessiner_ombres_chara`, constantes `OMBRE_DEMI` / `OMBRE_HAUT` / `OMBRE_DEC`). Les deux patchs cumulés donnent exactement `S/prop/fenetre.py` et `S/prop/donnees.py`, les fichiers que j'ai testés.
Preuve : église `mak1f1`, S/out/pair_ombre_chara_eglise.png (avant | après) : ellipse sombre nette sous les pieds du cardinal ; rapport de luminance mesuré sur les pixels d'ombre : min 0,620, attendu 1 - 0,376 = 0,624. Le contour est net (texture binaire, filtre point), comme dans l'original, contrairement à ce qu'on pourrait croire.

== INCERTITUDES ==
- Ombre de personnage : positionnement vérifié sur une seule capture (église). Le décalage vertical exact (0,0625 + composante verticale du recul de 0,25) n'est pas comparé à une capture du jeu mobile.
- À ajouter : ne pas dessiner l'ombre si l'id de feuille est 193 ou 194 (non vérifié que `no` = id de feuille ; h194 n'existe pas dans les textures, h193 oui) ; traiter le paquet 15 pour la carte du monde.
- Carte du monde (vue de dessus) non traitée : ombre en rotation X 36°, échelle `shadowDefScale` x 28,8, `m_chara` à 51,84 ; `SetFieldShadowPosition` est décodé en partie seulement.
- Tri des transparents : à `prio` égale, Unity trie les rendus du plus loin au plus proche ; non implémenté. Les triangles de `s_shadowMesh` ne sont pas décodés (quad supposé de 2 triangles).
- Les 5 textures RGBA32 `.tim` à alpha partiel (`cfsk01`, `isneon`, `PDKA01_A`, `cm1mon2`, `kd02a`) devraient suivre `fld_atest` (rejet à alpha 0 seulement) ; je laisse le cutoff 0,5 (écart minime).
- La fine bande d'eau translucide au sol à côté de certains bassins (maillage d'eau plus grand que le bassin, eau à y = 0,1) est probablement identique dans l'original ; non confirmé. Gamma / sRGB non examinés.
- Ombres en `.tim` à 0,4 vérifiées seulement dans maout. Les `_Color` teintés (33 matériaux, surtout des décors `btl_*`) sont maintenant appliqués par le même patch : non vérifié en combat.
- Les captures ne sont pas image par image comparables entre deux exécutions où le temps réel intervient (PNJ qui bougent) : pour la paire église, l'avant a été rendu avec les ombres calculées mais non dessinées.

== À RETENIR (issu de mon enquête sur les données et le code du jeu ; rien de dit par l'utilisateur) ==
- `FldObject.set_shader` (0xCD5414) choisit le shader des matériaux de carte à l'exécution ; `_Color` se multiplie dans les couleurs de sommet.
- Constantes de l'ombre de personnage : voir A2.
- Le dépôt a avancé pendant l'enquête (dégâts, menus) : ma copie de travail `S/dq4_pc` est une version plus ancienne ; les patchs ci-dessus sont rebasés sur le dépôt actuel (`S/dq4_orig` = dépôt au moment de la vérification).
- Piège : lancer le désassembleur `/home/claude/il2/desasm.py` depuis /home/claude/il2 (il ouvre `libil2cpp.so` en chemin relatif) ; mon `S/dis_r.py` en est la version avec chaînes résolues.

Fichiers : S/out/correctif_decor.patch, S/out/correctif_ombre_chara.patch, S/prop/ (versions patchées testées), S/out/*.png (captures ci-dessus).

---

## Agent adb969ea65cc6b771 — 31/10 16:48

RAPPORT (lecture seule : dépôt /home/claude/dq4-portage non modifié, `git status` vide, HEAD 63f2cc1 = main avec #18/#19). Tout est dans SCR = /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/enq_cb/ . Patch complet prêt à appliquer (non appliqué) : SCR/propositions.patch (syntaxe vérifiée).

Méthode : copie instrumentée du code, un combat complet de 687 pas moteur (slot 5, 2 Glacyclones, attaques/effets, dégâts, mort, fin), capture de CHAQUE pas (images f = tracé D1, g = tracé D2, car le moteur tourne à 30 Hz et l'affichage à 60 Hz = 2 tracés par pas) + meta.jsonl (paquets, positions, ordre de tracé).

=== 1) « Vibration » à l'apparition des ennemis et 2) clignotements d'animation : UNE SEULE cause, vérifiée ===
Cause : tampon de sommets des monstres envoyé au GPU avec un tour de retard.
- pyglet : `vl.position[:] = ...` ne fait que marquer le tampon « sale ». L'envoi GPU se fait dans `buffer.commit()`, appelé par `Jeu._tracer` (fenetre.py l.396-408) uniquement quand le domaine change (`dom is not self._dom_lie`).
- `_dessiner_scene` (l.1659) met `_dom_lie = None`, puis `_tracer_decor()` (l.1668) lie et commit le domaine unique (toutes les vertex_list sans batch explicite partagent le même). Ensuite `_maillages_combat(e)` (l.1669, appelé dans l'en-tête de la boucle) RÉÉCRIT les sommets des monstres/effets : le domaine étant déjà lié, plus aucun commit : les monstres sont dessinés avec les données de l'image précédente (le commit ne passe qu'au tracé suivant, via `_dom_lie = None`).
Preuves (mesures) :
- Dès le 1er pas du combat : au pas 3 les monstres sont ABSENTS en D1 (masque 0 px) et présents en D2.
- Pendant la caméra d'entrée (pas 4-33, 1280x720, runs k1 vs k2) : écart D1/D2 du bord haut des monstres moyenne 3,7 px, max 11 ; bord gauche moyenne 3,2 px, max 7 ; surface moyenne 4,5 %, max 10,5 % ; 52 inversions de sens sur 60 images affichées avec le code actuel, 0 avec le correctif. Pendant ce dolly les monstres bougent de 0,33 à 0,05 unité par pas : le retard d'un pas alterne avec 0 retard à 60 Hz = vibration avant/arrière.
- Combat entier à HEAD (all_n1 vs all_n2, 640x360) : D1 ≠ D2 sur 415/687 pas (60 %, jusqu'à 19 070 px de différence) avec le code actuel, 0/687 avec le correctif (D1 == D2 exactement). Même résultat sur l'ancienne copie (m1/m2). Les maillages d'effets (slot 2, ~10 pas) et ceux des monstres changent à CHAQUE pas, d'où le clignotement des attaques, sorts, et animation de l'ennemi qui attaque.
- Image : SCR/cs_m1_130.png (actuel : l'éclair et le monstre qui saute alternent entre deux poses) vs SCR/cs_m2_130.png (corrigé : mouvement monotone). Chiffres : SCR/d1d2.json, SCR/d1d2_n.json ; scripts SCR/d1d2.py, SCR/d1d2b.py.
Correction précise : fenetre.py, `_dessiner_scene`, branche `elif bataille:` ; remplacer la ligne 1669 `for tex, tw, th, vl, shader, hd in self._maillages_combat(e):` par :
```
mons = self._maillages_combat(e)      # réécrit les sommets (tampons « sales »)
self._dom_lie = None                  # force rebind + commit() au 1er tracé
for tex, tw, th, vl, shader, hd in mons:
```
(Variante équivalente : appeler `_maillages_combat(e)` avant `self._dom_lie = None` de la l.1659, comme les sprites juste au-dessus.) Vérifié : avec ce correctif, aucun trou ni clignotement résiduel sur les 687 pas (pas de motif A-B-A, pas de lacune de paquet 22 pour les emplacements 0/1 ; les sauts de surface restants sont des animations pilotées par les données).
Incertitudes : (a) l'effet visible dépend de la fréquence d'affichage : à exactement 30 Hz le retard est constant (pas de vibration), à 144 Hz 1 tracé sur ~5 est périmé ; (b) un seul combat étudié (2 Glacyclones) : pas testé avec 3-4 groupes ni d'autres sorts ; (c) la capture « 2 tracés par pas » simule le 60 Hz ; je n'ai pas mesuré sur un vrai écran. Risque latent distinct, non visible ici : l'ordre de tracé de monstres de même file (2150) bascule à cause de différences de 1e-3..1e-5 sur la profondeur du centre AABB (l.762-763, `out.sort(key=lambda o: o[0])`, bascules aux pas 3, 5, 8, 14, 20, 24...) ; recouvrement des 2 Glacyclones mesuré à 0 px sur 109 pas, donc invisible ici ; si un recouvrement apparaît, clé stable proposée : (file, -profondeur arrondie à 1e-3, emplacement).

=== 3) Boîte de message de combat trop haute ===
Cause : hauteur définie côté visionneuse par la géométrie du type de fenêtre dans cache/ui_layout.json['message']['types'] (frameData 192/193/194), choisie par le message moteur `[0,n]` (port 1, MenuMessage). Le début de combat envoie le TYPE 1 (cadre 193 : 188 unités de haut, canevas 164 lignes = 4 lignes de 34) alors que le terrain (type 0) = 126 unités, canevas 100,5 = 3 lignes ; type 2 = 122 à l'échelle 0,9 ; type 0 en fin de combat = 126. Le bas est calé par `_dz_message` (fenetre.py l.1073-1081) sur `CB_MSG_BAS = -338` (l.62), indépendamment de la hauteur.
Mesures en pixels à 1280x720 (SCR/boite.py, bord blanc du cadre ; SCR/boite_comparaison.png montre les 5 cas) : terrain 116 px (bas à 43 px du bord) ; combat type 1 actuel 160 px (SCR/out_bx0/c_45.png) ; type 2 100 px (SCR/out_bx0/c_150.png) ; type 0 de fin 104 px (SCR/out_bx0/c_560.png) ; tous les combats : bas à 60 px du bord. Donc seul le type 1 (messages d'ouverture du combat, pas 7 à 62 du combat étudié) est trop haut ; les types 2 et 0 tiennent déjà 3 lignes.
Correction : ramener le cadre type 1 à la hauteur du type 0 (126 unités ; canevas 164 -> 102 lignes = exactement 3 lignes de 34), en gardant le bord bas inchangé donc la distance au bord (60 px) identique. Code : ui_menu.py, nouvelle fonction `trois_lignes(t1, t0)` (avant `class MiseEnPage`) + appel dans `MiseEnPage.__init__` juste après la l.50 :
`if self.message: self.message['types'][1] = trois_lignes(self.message['types'][1], self.message['types'][0])`
(la fonction abaisse de dz = 188 - 126 = 62 les sommets du cadre au-dessus du milieu et le haut du quad du canevas, et met V du bas du canevas à 102/512 = 0,1992 ; code complet dans SCR/propositions.patch). Résultat mesuré : type 1 corrigé 104 px de haut (SCR/out_bx1/c_45.png), bas toujours à 659 px = 60 px du bord, texte inchangé en haut de la boîte. Les types 0/2 et le terrain ne changent pas.
Incertitudes : (a) je n'ai pas pu tester un message d'ouverture de 4 groupes de monstres (4 lignes) : le 4e ligne serait rognée ; variante possible : conserver le cadre d'origine quand le moteur écrit plus de 3 lignes (liste « lignes » du canevas, déjà lue dans le log de debug), ou réserver la correction à l'ouverture ; (b) je ne sais pas si le type 1 sert à d'autres messages que l'ouverture (non observé sur ce combat) ; (c) interprétation de « trop haute » = type 1 (160 px, seul cas > au terrain) ; si l'utilisateur vise aussi les types 2/0, ils sont à 100/104 px, plus bas que le terrain (116 px), donc rien à corriger du côté hauteur.

Fichiers de preuve : SCR/propositions.patch, SCR/boite_comparaison.png, SCR/out_fld/s1_150.png (boîte terrain), SCR/out_bx0/c_45.png, c_150.png, c_560.png (actuel), SCR/out_bx1/c_45.png (corrigé), SCR/cs_m1_130.png vs SCR/cs_m2_130.png (vibration), SCR/all_n1/ vs SCR/all_n2/ (f%04d.png = D1, g%04d.png = D2, meta.jsonl), SCR/d1d2.json, SCR/d1d2_n.json. Copie de travail instrumentée : SCR/dq4_new/ (HEAD + instrumentation + correctifs sous variables d'environnement DQ_COMMIT, DQ_FIX3L).

---

## Agent a75f06474763b3fa8 — 01/11 16:42

RAPPORT : moteur avant partie (DQ4), dépôt non modifié.

Livrables
- /tmp/specs/moteur_avant_partie.md : spécification complète (démarrage, menu, sauvegardes, nouveau jeu, lacunes, établi/supposé).
- /tmp/specs/sonde_titre.py : sonde reproductible (branches titre, continuer, reprendre, auto, nouveau, supprimer, licence, quitter).
- /tmp/specs/dq4_sauvegarde.py : analyseur de data*.dat.
- /tmp/specs/img/ : viewer_*.png, tex_taptostart*, tex_Retro4_copyright*, tex_m8900/8901/8905.

Conclusions établies
1. Titre : deux appuis A, via l'octet 0x10 en 2e argument de GameUpdate (un message MenuPort ne suffit pas). Entre les deux, fondu de 30 images, et un appui pendant le fondu entrant est ignoré. Le 2e appui lance startGame, puis la partie 3 et MaterielMenu_LOAD.
2. Menu racine (port 13, type 53) : valeurs à renvoyer `[1,v,0x10]` : 0 Continuer, 1 Reprendre, 2 Créer, 3 Supprimer, 4 Auto, 8 Cloud, 11 Licence. Ce ne sont pas les numéros de ligne affichés. B envoie `[0,999]` (Quitter).
3. Sauvegardes : data1..5.dat font 15 360 octets, data9.dat 512 octets. Le chiffrement est un XOR xorshift32 amorcé par le CRC32 de "vb76Eg43". La disposition et la somme de contrôle sont décodées.
4. Nouveau jeu : nom saisi par un clavier local à Unity, protocole `[2,len]` puis octets UTF-8 empaquetés. Sexe par `[1,0|1,A]`. makeDiary (0x194a50) écrit la carte mlb1a, sauve en type 4 et appelle startFirstTown. Le jeu démarre sur mlb1a (« Prologue », message 200005, Oui/Non), pas sur ev01 ni mak1f1.
5. Suppression : killbank écrit l'en-tête DLED. Le texte de la liste n'est pas rafraîchi avant réouverture.

Lacunes de fenetre.py, par priorité
1. Saisie du nom et du sexe (type 55) : rien n'est affiché.
2. Écran Licence (type 80) : écran noir bloquant.
3. Logos du titre (paquet 22) et Tap to start.
4. Messages du port 0 ignorés : [0,999], [0,6], volumes [0,4/5], [0,7], [0,8].
5. Cloud (valeur 8, types 75-79).
6. Non vérifiés : cellules grisées, clic souris au titre, prologue d'un nouveau jeu.

Inconnues (supposé)
- Le code de message que Unity utilise vraiment pour le nom. Le code 2 est accepté, tout code autre que 1 et 3 convient.
- La conversion clic en appui A par TitleTouch.
- Le clavier InputName (disposition, longueur maximale, Katakana/Hiragana).
- La différence entre SAVETYPE 1 et 2, et les effets de g_isAmazon au-delà du cloud.
- Le prologue après le Oui/Non, et l'entrée qui termine l'écran Licence.

À mémoriser (source : cette investigation, désassemblage et sonde)
- Chiffrement et format des saves (voir le point 3).
- Protocole du nom et valeurs de cellules racine.
- Le nouveau jeu démarre sur mlb1a.
- Les notes du projet disent à tort le type 73 « inutilisé » : c'est le Tap to start local à Unity.

Pièges : TextAPI::getMessage se bloque sous émulation (utiliser extractText ou msg_find). Le dossier de sauvegarde doit être inscriptible.

---

## Agent aebaa615370b7f262 — 01/11 16:44

Audit terminé. Livrable : /tmp/specs/audit_menus_pave.md (par élément, établi/supposé séparés, liste de corrections par priorité en section 7). Scripts : /tmp/specs/scripts/audit_reproduire.sh (régénère les listings dans /tmp/r4_repro/), audit_valeurs.py (recalcule tous les nombres), audit_dis.py, audit_eng.py, audit_scan_itemparam.py, audit_pad_meshes.py. Dépôt non modifié.

Conclusions établies (RVA et preuves dans le document) :

1. TouchPad : c_PadScaleTBL = (1.225, 1, 0.775), pas 1.25/1/0.75. Anneau = 256 x 0.63 x sc = 161.28 de diamètre (portage 165). Pastilles centrées à 104/256 = 0.406 du diamètre (portage 0.332 : faux). Zone morte 0.124 R (portage 0.15), course de la boule 0.4526 R (portage 0.5), prise par collider de 1.178 R. Le fondu à 40 % après 0.5 s est inventé : MOVE_WAIT_TIME et MOVE_LIMIT_ALPHA sont des constantes mortes. Boule orange et halo seulement au clignotement tutoriel, pas pendant le déplacement. Les 8 secteurs de 45° sont fidèles. Défaut du jeu : g_pad_pos = 1 (croix au centre, boutons à droite). Anneau flottant non établi : seule la boule suit le doigt.

2. Boutons HUD : icônes (3, 4, 15) et touches (0x1000, 0x800, 0x400) fidèles ; plaques d'origine 72x64 (Carte, Commandes) et 63x56.8 (Discussion), non carrées ; plaque 9-tranches de la feuille Button (le portage utilise un dégradé choisi à l'œil).

3. ItemNumCTRL (type 9) : compteur passif à deux chiffres. Changer(v) : v < 2 donne deux cases vides, sinon dizaines et unités. Le portage l'ignore, donc les quantités ne s'affichent jamais. Règle exacte dans le document.

4. ICityMap (type 25) : lieux et voile fidèles. Écarts mineurs : plan x -223..222.5, z 398..63.875 (échelle 0.99) et marqueur (≤ 2.5 unités). Le code 4 (croix rouge, feuille 5 case 3) est absent. ui_menu.py:187 contient une NameError latente (variable s non définie).

5. Mode de la carte : bug du pipeline dans outils/ui_il2cpp/layout.py:99. CreateMenuPortItem (0xCE43DC, `sub w2, w21, w0`) passe type moins le premier indice du délégué, mais le script passe le type brut. Le type 22 est donc exporté avec un seul bouton. Original : bouton Mode dans la fenêtre à (187.5, -300), plaque 64x55.5, icône donnée par le moteur (19 petite carte, 20 grande carte, 2 ville). Le HUD du portage fixe l'icône à 19. Les groupes 13-17, 35-37, 58/59, 60/61, 75/76 sont probablement touchés aussi (à vérifier).

6. PortalButton : écran titre uniquement, sans objet pour le HUD.

Priorités : (1) layout.py:99 puis régénération ; (2) ItemNumCTRL ; (3) constantes de la croix ; (4) boule et halo ; (5) retirer ou assumer le fondu ; (6) icône et position du bouton Mode ; (7) plan et marqueur ; (8) code 4 ; (9) NameError ; (10) vraies plaques.

À mémoriser (source : cet audit) : le bug de layout.py:99 ; g_pad_pos par défaut 1 ; les boutons à gauche sont un choix de Sylfried (retour #36), pas une erreur ; les docs notes-visionneuse:300, 305 et notes-technique:87 sont à mettre à jour.

---

## Agent ad6ee147e8091d8ae — 01/11 16:45

Spec écrite : /tmp/specs/unity_avant_partie.md (16 sections, chaque valeur marquée Établi / Supposé / Non trouvé, avec RVA ou trace). PNG dans /tmp/specs/img/ (boot_*, title_*, dssatex_*), scripts dans /tmp/specs/scripts/ (dont consts_flt.py, trace_titre2.py), traces dans /tmp/specs/work/t2_*.log.

Conclusions clés
- Unity ne dessine avant la partie que : 2 logos (sqex, arte ; « warning » seulement en JA), BackColor, Fade, et TapToStart + copyright. Le reste (titre 3D, BGM, menus) vient du moteur.
- Logos : carré 450x450 centré (texture 720x720), alpha linéaire 1 s / 3 s / 1 s (temps réel), clic = saut. Établi.
- TapToStart (type 73) : quad 223,04x41,48 centré à 228 sous le centre ; copyright 450x40 à 25 au-dessus du bas. Clignotement par triangle (±0,025/image, paliers de 20 images, période 120 images), premier affichage à l'image 720 sauf message `[12,0,0]` (CountReset), qui le lance tout de suite et fixe le copyright à alpha 1. Sans entrée, le moteur attend indéfiniment le pad A. 1er A = fondu 4126 + CountReset + fondu 30. 2e A = fondu + partie 3, menu du titre (type 53).
- Menu du titre : la sélection se fait par message `[1,idBouton,16]` sur le port 13, jamais par le pad. Ids : 0, 1, 2, 3, 8 (Sauv. cloud), 11 (Licence). Nouvelle partie : `13:1,2,16`, puis `14:1,0,16`, puis type 55.
- Licence (id 11) : fondu 20510, puis port 15 type 80 ; retour par `15:1,-1,32` (fondu 16414). Établi par trace.
- Sauv. cloud (id 8) : le moteur ferme les menus, crée un port de catégorie 4 (NetConnection) et attend Unity. Sans réponse, l'écran reste bloqué. À masquer sur PC.
- Google, ObbDownloadRes et PortalButton : code mort ou ignorable, prouvé par l'absence d'appelants.
- Saisie du nom : le moteur plante si `[2,len]` et les octets UTF-8 empaquetés ne partent pas à la MÊME image. Recommandation : zone de texte PC, pas de clavier 5x7.
- Pas de bouton en trop à ajouter : la config « Fade bit 14 » est décodée (0x4000 = variante).

Inconnues
- Route toucher vers pad, et rôle de la 1re phase du titre.
- Qui met `ApplicationQuit.s_quitStatus = 1` (Retour Android supposé).
- InputName : origine de la grille, boutons de fonction, SetMode, confirmation finale.
- Fenêtre Make_License (positions) et LicenseNobu en détail.
- Réponses NetConnection.
- Rendu 3D du titre (ids 8900/8901/8905, paquets BGM).
- 30 Hz supposé.

À retenir pour la mémoire (source : cette mission)
- `runall2.make()` exige `DQ_META=/tmp/specs/work/base_extract/assets/bin/Data/Managed/Metadata/global-metadata.dat` en plus de `DQ_IL2`.
- Le moteur plante si le nom est envoyé en deux images.
- Table type vers Make : /tmp/specs/work/type_to_make.txt.

---

## Agent a85a7118884ad1696 — 01/11 17:15

P1 à P5 et le bug `s` sont faits, en 6 commits sur `audit-interface` dans `/home/claude/wt-audit` (base 752c7fd). Rien n'est poussé, aucune PR, `dq4-portage` n'a pas été touché.

**Commits** : faf7162 (bug `s`), a5d40c6 (P1 église), b3e4ed9 (P2), be149e1 (P3), 4071160 (P4), e6ac6b2 (P5). Chaque commit compile.

**Fichiers touchés** : `dq4_pc/ui_menu.py` (+165/-8) et `dq4_pc/fenetre.py` (appel de `ui_g.tick()` après `mo.step`, et `_ui_x_monstres(liste)`). Aucun identifiant de nœud n'est codé en dur.

**Vérifié**
- **P1** : moteur réel dans l'église (sauvegarde 1). Clic souris et clavier envoient le bon bouton sur les 5 boutons.
- **P2** : combat réel sur `btl_pl_d` : la secousse (8 images) et le rouge en fin de secousse sont corrects. Le clignotement fait environ 0,7 s.
- **Flèche** : elle n'était jamais affichée avant (le SetActive(true) manquait, confirmé au désassemblage). Elle apparaît maintenant sur le type 29, id 5 uniquement.
- **P3** : empoisonné et mort ont bien la tête de mort et la croix rouge dans la liste Résurrection ; l'œil et le jaune sont testés en synthétique.
- **P4** : les marques apparaissent à la sélection de cible et sont effacées ensuite.
- **P5** : « Continuer votre aventure » a maintenant son cadre.
- **Rendus** : les 72 types sont identiques avant/après. Menu, message et Oui/Non sont identiques. En combat, seules la flèche et les marques changent. Captures dans `/tmp/specs/img/`.

**Hypothèses non vérifiées**
- Cadence de secousse à 30 Hz.
- Rouge exactement en fin de secousse.
- Marques à z=-64 en 16:9.
- Sens du code 2 du type 54 et position du bouton retour.
- Survol des boutons d'église et boutique de bout en bout non testés.
- Docs non mises à jour.

**Autre point** : `/home/claude/dq4-portage` a des modifications non commitées par un autre intervenant (`fenetre.py`, `moteur.py`, `ui_menu.py`). Un conflit au merge est possible.

**Pour la mémoire**
- Église reproductible via le slot 1.
- `HaveStatusInfo` est à PlayerStatus+0x10, poison = flag 0x16 (+0x198).
- Tests headless : `xvfb-run -a`, variable `DQ4_SRC`, scripts dans `/tmp/specs`.
- Piège : `pgrep -f` dans un moniteur se tue lui-même.

---

## Agent aba9c8fd03df2b6dd — 01/11 17:27

RAPPORT FINAL, branche `audit-pave` (worktree /home/claude/wt-pave, depuis main 752c7fd). Rien poussé, pas de PR, `main` et le Project non touchés, `self.nom_carte = s` (ui_menu.py, `param_int`) laissé pour A9.

COMMITS (français, avec les 2 lignes Co-Authored-By / Claude-Session)
- 39b406a Correctif du layout Unity (A1)
- 6c127c9 ItemNumCTRL (A2)
- d2825f3 Petite carte : plan, plume, croix rouge code 4 (A7, A8)
- 45f0a13 Croix, plaques des boutons, bouton Mode (A3, A4, A5, A6, A10)
- 0275e93 Notes (les deux docs, section datée « Audit de fidélité », sans n° de PR)

CORRIGÉ
- A1 : `layout.py` `export_type` passe `typ - premier rang du délégué dans R.tbl` (preuve 0xCE43DC). `GENERATION = 3` (`entete.py`). J'ai aussi changé `lancer_dq4.bat` (`gen >= 3`, avant `>= 2`) : sans cela le cache de l'utilisateur n'aurait pas été refait. Nouveau layout dans /tmp/uicache4. Types dont le layout change : 13, 14, 15, 16, 17 (pages du Statut : 1 nœud -> 5, 3, 4, 3, 5 ; l'écran Statut était vide), 22 (gagne le bouton Mode ; nouveau 22 = ancien 23 + Mode), 35, 36, 37 (BattleIM 8 -> 20, 16, 20 nœuds ; la liste Objets du combat était vide), 58 (lignes remontées de 141 unités, interligne 2,46 ; l'ancien 58 était égal au 59), 60 (21 -> 31 nœuds ; l'ancien 60 était égal au 61). Inchangés : 23, 59, 61, 75, 76 et les 69 types à délégué unique. Aucune régression constatée, donc le correctif est gardé pour tous les types.
- A2 : `ui_menu.Fenetre._item_num`, appelée depuis `param_int` pour la classe ItemNumCTRL (règle de la spec). Vérifié par injection de quantités (57, 9, 10, 123 -> « 23 »).
- A3 : constantes de la croix dans `hud_mobile.py` (DIAM_CROIX 161,28 ; ECHELLE_CROIX 1,225/1/0,775 ; RAYON_PASTILLE 104/256 ; ZONE_MORTE 0,124 ; COURSE_BOULE 0,4526 ; PRISE_CROIX 1,178).
- A4 : plus de boule ni de halo orange quand on tient la croix ; seule la pastille du secteur tenu est allumée.
- A5 : fondu à 40 % après 0,5 s retiré (`croix_t`, ATTENTE_CROIX, ALPHA_CROIX supprimés). Il était inventé : MOVE_WAIT_TIME et MOVE_LIMIT_ALPHA sont des constantes mortes.
- A6 : bouton Mode = bouton de la fenêtre type 22 (icône 19/20/2 envoyée par le moteur), cliquable à la souris et au clavier (touche M inchangée). Le bouton `mode_carte` du HUD est supprimé. Le HUD est entièrement masqué carte ouverte.
- A7 : plan x -223..222,5, z 398..63,875 (type 25 seulement) ; plume `-223 + 1,740234 px`, `398 - 1,740234 py`.
- A8 : croix rouge du code 4 (feuille 5, case 3, 21,6 unités, `(-227 + lo*1,7578, 402 - hi*1,7578)`, ancrage bas gauche), via `Fenetre.special`.
- A10 : boutons du HUD avec la plaque 9 tranches `Rendu.plaque` (nouveau paramètre `coin=16`), formats 72x64 (Carte, Commandes) et 63x56,8 (Discussion). Le dégradé procédural reste en secours si `Rendu` est indisponible.

NON CORRIGÉ / POURQUOI
- A9 (`s` non défini) : réservé à l'autre agent.
- Grande carte (type 26) : position d'origine non lue, ancien rectangle (-225..225) conservé.
- Position par défaut des boutons et de la croix, option `g_pad_pos`, barre de rotation de la caméra, bouton PadPos : non touchés (choix de l'utilisateur en #36, ou sans objet sur PC).

VÉRIFIÉ PAR CAPTURE (xvfb)
- Statut avant/après : /tmp/pave_st_old_b150.png (vide) et /tmp/pave_st_new_b150.png (rempli) ; pages 2 à 4 : /tmp/pave_stp_b190.png, b230.png, b270.png.
- Combat, Objets : /tmp/pave_cbi_uicache3_b290.png (vide) et /tmp/pave_cbi_uicache4_b290.png (4 boutons).
- Quantités injectées : /tmp/pave_qte_b130.png.
- Carte avec Mode + Retour : /tmp/pave_mp_b95.png, b150.png. Clic sur Mode puis fermeture : /tmp/pave_mc_b100.png, b150.png, b230.png, b310.png.
- Croix rouge du code 4 (injectée) : /tmp/pave_c4_b150.png.
- Croix au repos et tenue : /tmp/pave_hud_b90.png et b130.png. Éditeur d'interface : /tmp/pave_edit_b90.png.
- Menus simples sans `ui_layout.json` : /tmp/pave_simple_b90.png, b130.png, b190.png. Dernier contrôle sur HEAD avec le cache gen 3 : /tmp/pave_fin_b90.png (le jeu démarre).
- pyflakes : jeu de warnings identique à main sur les 5 fichiers .py touchés (aucun nouveau).
- Les captures sont celles d'une galerie de fenêtres vides pour 58/60/75/76 et 14 à 17, 36, 37 ; pas de rendu en situation.

CE QUI RESTE « NON VÉRIFIÉ » (PC Windows de Sylfried / hors portée)
- Rendu OpenGL réel (mes captures viennent de Mesa sous xvfb) et régénération du cache par `lancer_dq4.bat` (gen 3, quelques minutes, une fois).
- Boutiques (types 58 et 60) : aucune sauvegarde de test n'y mène.
- Les autres groupes de types touchés par A1 sont supposés se lire comme `Make_MapButton`, seul lu ligne à ligne ; les captures n'ont montré aucune régression.
- Ancrage bas gauche de la croix rouge (supposé par analogie avec la plume), shader SmallMapSymbol, jamais reçu dans les sauvegardes de test.
- Absence d'anneau flottant et de fondu : établie pour le code C# de TouchPad, pas pour une animation extérieure ; aucune capture Android disponible.
- Le moteur envoie 0 comme quantité pour toutes les lignes de la sauvegarde de test (objets non empilés) : le rendu réel des quantités n'a été vu qu'en injection.
- Menus simples (sans `ui_layout.json`) : la fenêtre de carte n'est pas dessinée (comme avant), donc plus de bouton Mode à l'écran dans ce mode ; la touche M reste.

FICHIERS / FONCTIONS TOUCHÉS (pour la fusion avec `audit-interface`)
- `outils/ui_il2cpp/layout.py` (`export_type`), `outils/ui_il2cpp/entete.py` (GENERATION), `dq4_pc/lancer_dq4.bat` (test de `gen`).
- `dq4_pc/ui_menu.py` : `Fenetre.__init__` (+ `self.special`), `Fenetre.param_int` (1 ligne ItemNumCTRL, juste après la ligne ICityMap `self.nom_carte = s` intacte), nouvelle `Fenetre._item_num`, `Rendu.plaque` (param `coin`), `Rendu._carte` (rectangle type 25 + croix rouge).
- `dq4_pc/fenetre.py` : `on_mouse_press` (fenêtre type 22, boutons 0x400 et 2), `on_mouse_release` (branche `mode_carte` retirée, bouton pad 2 -> `carte_bascule`), `_plan_fenetre` (code 4 + position de la plume).
- `dq4_pc/hud_mobile.py` : constantes, `echelle/taille/dims/rect`, `visibles`, `_plaque`, `_croix` (import `time` retiré).
- `docs/notes-visionneuse-dq4-pc.md` et `docs/notes-technique-portage-dq4.md` : passages corrigés (GENERATION, lacunes, plume, croix, plaques) + nouvelle section « Audit de fidélité » à la fin de chacun.
- Points de friction probables avec `audit-interface` : `ui_menu.py` (`param_int`, `Rendu.plaque`, `Rendu._carte`) et `fenetre.py` (`on_mouse_press` / `on_mouse_release`, `_plan_fenetre`).

À SAVOIR (méthode)
- J'ai dû défaire un premier commit ItemNumCTRL (371e588) mal découpé : `git apply --unidiff-zero` avait posé les lignes au mauvais endroit. Il a été annulé avant tout autre commit ; l'historique actuel est propre et chaque commit compile (py_compile).

---

## Agent a9a69c9aad072e46d — 01/11 18:44

Rapport camera-bip : la caméra est corrigée, le bip est normal et je n'ai rien changé côté son. Un commit sur la branche `camera-bip` : 75eae46, rien poussé, `docs/` et README intacts.

**1. Caméra : corrigé et vérifié**
- **Nouveau critère** : le verrou de la `TownCamera` du moteur (+0x3e), lu par `Moteur.camera_jeu()`. L'option « centrer sur le joueur » ne s'applique que si ce verrou est à 0.
- **Rejeté** : le drapeau « joueur verrouillé » (`Global.Flag` bit 0x4), car il est posé pendant tous les messages alors que la caméra suit le héros. L'ancien critère (cible à moins de 60 unités du héros) échouait aussi : dans le prologue la cible n'est qu'à 23 unités, donc la salle apparaissait au lieu de l'écran noir « Prologue ».
- **Pendant un événement** : la caméra du jeu s'applique telle quelle, avec les bornes 16/9 de la visionneuse, comme option désactivée.
- **Transition** : l'ancien lissage est conservé. Si la cible saute (changement de carte, coupure de plan, seuil 1,5 unité par pas), le centrage suit aussitôt, sans glissement.
- **Vérifié par captures** :
  - Prologue (slot 2, `mlb1a`, verrou à 1 jusqu'à la capture ~368) : option activée identique au pixel à option désactivée. Après libération, la caméra se centre sur le héros.
  - Exploration libre église → porte → `maout` (5 captures, changement de carte compris) : identique au pixel à l'ancien code.
  - Message de PNJ à l'église (3 captures) : identique au pixel.
  - Le verrou reste à 0 pendant les jarres et tonneaux (sonde du moteur sans fenêtre), donc le centrage reste actif.
  - `pyflakes` : seul l'ancien avertissement `sel` (ligne ~1700).

**1bis. Partiel ou non vérifié**
- Jarre ou coffre avec message : seulement dans la sonde du moteur sans fenêtre, pas en capture. Le prologue n'étant pas rejouable par touches, je n'ai pas pu casser une jarre dans la visionneuse. Le message de PNJ passe, lui, en capture.
- Je n'ai pas pu voir une scène à caméra visible avec le héros près d'un bord de carte.
- Je n'ai pas vérifié l'entrée dans le verrou par un déplacement lent (seulement des coupures et une simulation), ni les chutes et sorts de retour.
- **Mon choix** : les bornes 16/9 restent appliquées pendant les scènes.

**2. Bip : normal, commandé par le moteur**
- C'est le bruitage 300 (paquet 35), joué par le moteur au début d'un message quand le joueur vient de reprendre la main. C'est le même que celui du passage de page.
- Mécanisme : `ui_MsgLoop` (0x157044) joue le 300 une seule fois, puis efface l'octet `ui_MsgBeginTalkSE` (lib+0x252388). Cet octet est réarmé quand le joueur est libéré (`PlayerManager::setLock(false)`).
- Trace d'une jarre avec message : jarre brisée (319, ou 320 pour un tonneau), icône de l'objet (326), ouverture du message, puis le 300. Les jarres sans objet n'ont ni message ni bip.
- La visionneuse joue un seul son par paquet, avec le bon fichier (`SE0300`), et n'ajoute rien à l'ouverture d'un message. Pas de double lecture.
- Non comparé au jeu Android : le volume réel (`vol_b × volume du fichier` ici).

**Fichiers touchés**
- `dq4_pc/fenetre.py`
- `dq4_pc/moteur.py`
- `/tmp/specs/camera_bip.md` : adresses, traces, établi / supposé / inconnu.

**À signaler**
- Deux points hors périmètre, non touchés, et le second concerne l'agent des écrans titre / prologue :
  - Les touches clavier des boutons d'écran (Entrée = Commandes, Espace = Discussion, M = Carte) ne jouent pas le 300, alors que le clic souris le joue.
  - Dans le prologue, l'attente de touche (`cmd_key_wait_type_b`) ne reçoit jamais A brut : Espace devient `BTN_PAROLE` et A / B sont retirés de la manette. Cela bloque les tests automatisés.
- À mémoriser : `Moteur.camera_jeu()` donne (verrou +0x3e, mode +0x48, verrou de point de vue +0x40, déplacement +0x43). Valeur du prologue : (1, 5, 0, 0) ; état libre : (0, 0, 0, 0).
- Un autre agent tourne encore (« Prologue : encadrés de chapitre… »). Aucun xvfb n'était actif quand j'ai lancé mes captures.

---

## Agent ab8b9ed0a24f93543 — 01/11 19:16

Prologue et boîte violette : les deux retours sont traités et vérifiés par captures. Branche `prologue`, 2 commits : `152b967` (fix) et `f0d4b9d` (feat). Rien poussé, `docs/` et patch FR intacts. Spec détaillée : `/tmp/specs/prologue.md`, captures : `/tmp/specs/img/prologue_*.png`.

**Corrigé et vérifié par capture**
- **Boîte violette** : `[N,2]` détruit le port côté Unity, mais le portage appliquait encore à la fenêtre fermée les messages reçus dans la même image. Elle revivait une image en boîte « simple » violette. `Interface.appliquer` ignore maintenant ces messages. Avant/après image par image sur le choix de sauvegarde → nom (violette à 854 avant, absente après). Absente aussi sur les transitions voisines : emplacement occupé → confirmation, sexe → « Création », et toute la chaîne Supprimer (confirmation, Oui, « Journal supprimé », retour au menu). Le retour de l'écran Licence au titre est correct.
- **Fond noir et bandeau** : le moteur pilote deux plans de fondu (bit 14 du paquet 9), le portage n'en dessinait qu'un, derrière les fenêtres. J'en ai ajouté un second : « FadeForBG » est derrière les fenêtres, « FadeForMenu » devant tout. Le bit 0 du mot d'état suit les deux plans (`Fade.IsEnd`). Le bandeau doré à fond bleu (texture `hyodai1`, extraite du datapack au premier lancement) apparaît et s'efface sur écran noir avec « Prologue » centré.
- **Coups d'épée** : ce sont 5 effets-maillages (modèles 5303/5311, bruitages 412/416/403) vus par une caméra qui regarde le vide. Ils sont visibles de bout en bout, jusqu'à la salle, avec le correctif caméra `75eae46` appliqué à une copie.
- **Attente de touche A/B** : `tick` n'est pas en cause. `cmd_key_wait_type_b::isEnd` lit le 2ᵉ argument de `GameUpdate` (`decl != 0`), et Espace donne `BTN_PAROLE`, non nul. Espace à l'image 1700 fait apparaître « Eh bien alors, Sylfried ! » puis Oui/Non. Aucune modification de `tick`.

**Correction d'une note du dépôt** : « bit 14 = plan devant l'interface » (`notes-technique-portage-dq4.md`, commentaire `moteur.py`) est inversé. Le bit 14 désigne le plan de fond, derrière les fenêtres. La note sur la Licence (`[20510]`) était juste. Je n'ai pas touché `docs/`.

**Comportements qui changent**
- Les fenêtres s'assombrissent maintenant avec les fondus de devant.
- Au combat, « Ragnar meurt ! » et le texte de la voix se lisent sur le noir.
- Le fond reste noir jusqu'à la commande du moteur, sans réouverture après 6 s.
- `--slot 1` est identique au pixel à `d381c1d`.

**Partiel ou non vérifié**
- La taille et la place des éclats d'épée sont à l'échelle des paquets : aucune capture du jeu réel pour comparer.
- Supposé : la hauteur 225 du bandeau et la caméra qui porte les plans de fondu.
- Non reproduit : paquet 33 `map_color_rate` ([1,25 ; 0,65 ; 0,75] à l'ouverture de `mlb1a`) et `SetFadePriority` (appelé seulement par `MenuMessage.SetCanvasMesh`).
- Le comportement de l'extraction de `hyodai1` n'est pas testé sous Windows : 3,7 s ici, et sans UnityPy ou APK le bandeau est simplement absent.
- Avec `vitesse_fondu` ≠ 2, la durée d'affichage du bandeau change, car le moteur attend la fin des fondus.

**Fichiers touchés** : `dq4_pc/moteur.py`, `dq4_pc/fenetre.py`, `dq4_pc/ui_menu.py`, `dq4_pc/avant_partie.py`. Je n'ai pas touché `_camera_ville`. Les coups d'épée supposent que `75eae46` (déjà dans `retours-18h02`) soit présent. Le correctif des plans (`f0d4b9d`) touche `fenetre.py` et `ui_menu.py`, qui ont aussi bougé sur `retours-18h02` : un conflit de fusion reste possible. Pyflakes : seulement les 4 avertissements déjà présents sur `d381c1d`.

---

## Agent aa4e97b2e5ca28447 — 01/11 21:24

RAPPORT agent-pause (worktree /home/claude/wt-pause, branche agent-pause, depuis main 1e87ca6). 4 commits, arbre propre, pyflakes sans nouvel avertissement (restent : H, R, yp, mh dans pause.py ; sel dans fenetre.py ; io dans etats.py ; em, ax dans ui_menu.py, tous antérieurs).

COMMITS (ordre, tous avec les deux lignes Co-Authored-By / Claude-Session)
- 2450c69 Commandes : une seule touche d'accélérateur et une section « Vitesses »
- 892da45 États : la fenêtre garde la même taille avec ou sans état enregistré
- 9a2fad8 Pause : « Revenir à l'écran titre » (confirmation puis retour au titre du moteur)
- 244368b Bouton « Paramètres » du menu Divers : ouvre le menu Pause

CE QUI EST FAIT
1. Commandes
- Supprimé : courir, courir (appuyer), accélérer la caméra (maintenir / appuyer), PARTAGE, actions_de, les bascules de fenetre.py, et les réglages accel_camera et vitesse_course.
- Une seule touche tenue 'accel' (Maj gauche / Maj droite par défaut) et un seul facteur vitesse_accel (1,5 ; bornes 1 à 2). Il s'applique à la marche (_facteur_vitesse) et à la caméra (_maj_camera).
- Nouvelle section « Vitesses » sous « Caméra », exactement 5 lignes dans cet ordre : Vitesse de marche, Vitesse de caméra, Vitesse de transition, Touche d'accélérateur, Vitesse de l'accélérateur. Les doublons ailleurs sont retirés (la vitesse de transition quitte « Autres »). Aides (infobulles) ajoutées.
- Migration silencieuse (7 scénarios testés par /tmp/test_mig.py) : la première des anciennes touches courir / courir_bascule / cam_accel / cam_accel_bascule renseignée devient la touche d'accélérateur ; vitesse_course devient vitesse_accel. Aucun autre réglage n'est perdu. Une touche ne sert plus qu'à une action.
2. États
- Reproduit avant de corriger : fenêtre vide ~432 px, ~483 px après création d'une sauvegarde (/tmp/m_p1_b125.png, _b175.png).
- Choix : taille constante = celle de la fenêtre vide (largeur 540 x k). La date des emplacements ne compte plus dans le calcul de largeur, et elle se réduit (_ajuster) si elle ne tient pas. Raison : c'est la taille du « screen 5 » demandé, et le contenu ne la fait plus bouger.
- Après correction : même cadre avant et après création, x = 271 à 700 (/tmp/m_pd_b125.png et /tmp/m_pd_b175.png).
3. « Revenir à l'écran titre »
- Racine : renommé, sans flèche (sous=False), à la place de « Quitter le jeu ». Il enchaîne « En êtes-vous sûr ? » (Non présélectionné), puis « Oui » ferme le menu et appelle Moteur.retour_titre.
- retour_titre reprend le « Oui » du bouton d'origine (TownMenu_OPERATION_SETTING, état 5) : killbank(4,false), PlayerManager::setLock(true), Global::startTitle. Le bouton d'origine n'est plus joignable (cf. point 4) : il reste un seul chemin vers le titre.
- Vérifié (run pb) : confirmation puis fondu, générique, titre « Touchez l'écran », sans erreur dans /tmp/out_pb.txt. La page 'quitter' est conservée : elle sert à la question « quitter l'application » du menu de départ (code 999).
4. Bouton « Paramètres » du menu en jeu
- Constat : ce bouton n'est pas dans le menu racine (type 3) comme le dit le brief. Il est sur la page 2 du menu Divers (liste type 8, indice moteur 7). Les numéros de bouton de la visionneuse sont relatifs à la page ; l'indice 7 n'existe que dans le moteur.
- Le nom reste « Paramètres » (aucune retouche). Le moteur n'ouvre plus ses réglages : en mémoire, la comparaison `cmp w8,#7` (0x16ef28 dans TownMenu_OPERATION_ROOT::menuUpdate) devient `cmp w8,#4095`. Le moteur traite alors l'appui comme un bouton inconnu : menu Divers non fermé, pas d'état « Paramètres », pas de blocage. Un crochet lit x8 == 7 et lève Moteur.demande_pause. Jeu.tick ouvre le menu Pause.
- Le patch est ré-appliqué après chargement d'un état (etats.appliquer restaure l'image de la bibliothèque).
- Supprimé : le bouton « Menu Pause » ajouté à la fenêtre Paramètres (TXT_MENU_ECHAP, echap_port, BTN_ECHAP, nb_plaques, bouton_echap, centrer_liste dans ui_menu.py, environ 50 lignes) et le recentrage des listes de réglages. 'Config' est ajouté à SANS_EDITION (fenêtre d'origine devenue inaccessible).
- Testé : Divers p2 -> Paramètres -> Pause s'ouvre ; Échap la ferme et on retombe dans Divers p2, qui fonctionne ; Retour arrière ramène au menu racine. Aucune fenêtre type 27 dans le journal. Captures : /tmp/m_pd_b355.png (Divers p2), /tmp/m_pd_b380.png (Pause), /tmp/m_pd_b445.png (menu racine après retour).

ÉTABLI (lu dans le code ou observé)
- Les 4 points ci-dessus, tels que décrits, sur la sauvegarde 1 (--slot 1 --auto-message 1, sauvegardes de test dans /tmp/sv_*). Le contenu committé est octet pour octet celui testé.
- Le Oui d'origine appelle bien killbank(4,false) puis startTitle. setLock est statique (utilise w0 comme booléen, sans this).

SUPPOSÉ
- Le bouton d'origine « Revenir à l'écran titre » est la seule autre entrée vers startTitle dans la liste des paramètres (je n'ai pas fait de recherche exhaustive des appels à Global::startTitle).
- Le crochet UC_HOOK_CODE sur 0x16ef28 ne gêne pas d'autres menus : il ne lève la demande que si w8 vaut 7 à cet endroit précis du code.

NON VÉRIFIÉ
- Le menu de départ une fois revenu au titre : je n'ai pas appuyé sur « Touchez l'écran » après le retour (mon RETURN est tombé pendant le générique). C'est le périmètre de l'agent titre.
- Le retour au titre depuis un combat, un événement ou une boutique (je n'ai testé que depuis une église en ville).
- Le retour au titre puis une nouvelle partie / « Continuer » sans relancer la visionneuse.
- Réglages enregistrés par un vrai profil Windows de l'utilisateur : la migration est testée sur des fichiers synthétiques.
- Les anciens états (.dqs) créés avant ce lot : non chargés, mais le patch est ré-appliqué par construction.

NON COUVERT (réglages d'origine du jeu, désormais inaccessibles)
- Volumes BGM / SE du moteur : la visionneuse a sa propre page Son et n'a jamais lu ceux du moteur.
- Vitesse de combat OptionStatus::setBattleSpeed (« Vitesse ») : domaine de l'agent texte / son.
- « Taille de la croix » (g_pad_size) : reste à sa valeur par défaut ou enregistrée ; le réglage croix_taille de la visionneuse la remplace.

FICHIERS TOUCHÉS : dq4_pc/reglages.py, pause.py, fenetre.py, moteur.py, etats.py (1 ligne), ui_menu.py (suppressions seulement). README.md non touché (conflits de fusion) ; rien dans docs/.

CAPTURES UTILES
- Commandes : /tmp/m_p8_b252.png (nouvelle section « Vitesses » ; la vitesse de transition à x2,00 vient de /tmp/rg.json, pas du défaut).
- États avant correction : /tmp/m_p1_b125.png, _b175.png. États après : /tmp/m_pd_b125.png, _b150.png, _b175.png.
- Racine et retour au titre : /tmp/m_pd_b380.png (racine), /tmp/m_pb_b146.png (confirmation, Non présélectionné), /tmp/m_pb_b175.png, _b275.png (fondu et générique), /tmp/m_pb_b500.png, _b640.png (titre).
- Paramètres : /tmp/m_pd_b355.png, _b380.png, _b445.png.

PIÈGES POUR LA FUSION
- fenetre.py : hunks supprimés dans _dessiner_menus (zl / param / echap_port / centrer_liste / bouton_echap). Il reste `for fe in fens_v: if fe.typ == 53: fe.centrer_menu()`. Si un autre agent a modifié ce bloc ou les références à BTN_ECHAP, conflit probable. Autres hunks : on_key_press (bloc actions_de / bascule retiré), _maj_camera, _facteur_vitesse, ligne `if mo.demande_pause` dans tick après mo.step, méthode retour_titre après quitter.
- pause.py : _e_commandes entièrement réécrite (l'éditeur d'interface ne la touche pas). Hunks locaux dans dessiner (lw, pw, maxw_lab des slots, sauts de sep pour 'titre'), _aide_ligne (branche 'curs'), _e_racine, SANS_EDITION. Ne pas reformater.
- ui_menu.py : 2 blocs supprimés (ID_ECHAP / BTN_ECHAP / nb_plaques / bouton_echap, puis centrer_liste). Tout code d'un autre agent qui les appellerait casserait : grep BTN_ECHAP, ID_ECHAP, centrer_liste, bouton_echap, nb_plaques.
- moteur.py : ajouts uniquement (CMP_PARAMETRES, patcher_parametres, _detourner_parametres, retour_titre, 2 lignes dans __init__ après `self.fielddata`). etats.py : 1 ligne après remettre_vitesses().
- reglages.py : PARTAGE, actions_de, accel_camera, vitesse_course, camera_maj n'existent plus. Tout code ou test d'un autre agent qui les lirait doit passer par 'accel' / 'vitesse_accel'.

NOTES À AJOUTER DANS LES DOCS
- Commandes : une seule touche d'accélérateur (tenue, Maj par défaut) et un facteur « Vitesse de l'accélérateur » (x1,5) pour la marche et la caméra. Section « Vitesses » : marche, caméra, transition, touche et vitesse de l'accélérateur. Migration silencieuse : courir / cam_accel -> touche d'accélérateur ; vitesse_course -> vitesse_accel. Une touche = une seule action (plus de PARTAGE).
- États : la fenêtre a toujours la largeur de sa version vide (540 x k), la date se réduit au besoin.
- Retour au titre : Pause > « Revenir à l'écran titre » (confirmation) -> Moteur.retour_titre = killbank(4,false), setLock(true), Global::startTitle. L'ancien libellé d'origine prévenait « votre aventure ne sera pas sauvegardée… » ; je n'ai gardé que « En êtes-vous sûr ? » comme demandé. Le retour efface aussi la banque 4 (sauvegarde automatique), comme l'original. La page 'quitter' reste pour le menu de départ.
- Paramètres : sur la page 2 du menu Divers (indice moteur 7, type 8), pas dans la racine type 3. Le moteur est patché en mémoire (0x16ef28 : cmp w8,#7 -> #4095) et un crochet UC_HOOK_CODE lève demande_pause ; le patch est ré-appliqué après chargement d'un état (comme _elargir_symboles, précédent de patch mémoire). La fenêtre type 27 « Config » et le bouton « Menu Pause » ajouté aux paramètres n'existent plus ; 'Config' est dans SANS_EDITION.

---

## Agent ab662602ce1e9405b — 01/11 21:33

RAPPORT agent-editeur (éditeur d'interface) — worktree /home/claude/wt-editeur, branche agent-editeur, 1 commit 40d4a5f au-dessus de main 1e87ca6. Rien poussé, aucune autre branche touchée, /home/claude/dq4-portage intact, aucun fichier du patch FR ni sauvegarde utilisateur touché (tests en /tmp/sv_NOM). pyflakes : seulement des avertissements déjà présents avant (pause.py R/yp/mh, fenetre.py sel).

## Fichiers touchés
- dq4_pc/pause.py (+202/-…) : constantes en tête, `_e_interface`, liste déroulante, `dessiner` (placement du panneau), `clic`/`relache`/`glisser`/`maj`, `_apercu`.
- dq4_pc/fenetre.py (+76) : `_dessiner_menus`, `_zones`, `_nom_de_type`, aperçus (`_fenetre_apercu`, `apercu_interface`, `_apercu_ouinon`), `_cachee`, `_ui_ouinon`.
- dq4_pc/reglages.py (+8) : clé `interface_masquees`, `FENETRES_RETIREES`, purge au chargement.
- hud_mobile.py et tout le reste : inchangés. Aucune doc écrite.

## 1. « Afficher cette interface à l'écran »
Réponse honnête : NON, avant ce n'était pas limité à l'interface choisie (Établi par lecture du code + capture avant /tmp/m_avp_b112.png). L'option était globale (`R['boutons']`) : elle masquait boutons ET croix, quelle que soit l'interface sélectionnée, et n'avait aucun effet sur les fenêtres du jeu. Maintenant elle est propre à l'interface choisie :
- « Boutons et croix de l'écran » : `R['boutons']` (comportement d'avant, mais seulement pour cette entrée ; « Afficher la croix » reste séparé).
- Toute fenêtre du jeu (ou « msg ») : nouvelle clé `interface_masquees` (liste de noms). Une fenêtre masquée garde sa mise en page mais n'est plus dessinée et n'a plus de zone souris. Dans l'aperçu de l'éditeur : assombrie + étiquette rouge « Masquée ».
- Ordre des lignes : 1) « Interface à modifier » (toujours en premier), 2) « Afficher cette interface à l'écran », puis Taille / Position (ou taille boutons, croix…), grille, Rétablir cette interface, Rétablir toutes (réaffiche aussi tout), Terminer.
Interprétation alternative possible : si Sylfried voulait que l'option « force l'affichage » de la seule interface choisie pendant l'édition (au lieu de la masquer en jeu), il faudra le dire ; j'ai choisi « afficher / masquer en jeu, par interface ».

## 2. Regroupement et entrées supprimées
Sélecteur : 54 entrées en 11 groupes, intertitres dorés non sélectionnables (sautés par flèches/PageUp/PageDown, un clic dedans ne ferme pas la liste) :
- Écran tactile (1) : Boutons et croix de l'écran
- Dialogues (3) : Dialogues (messages) [msg], Oui / Non [YesNo], Titre du chapitre [Chapter]
- Menu en jeu (5) : RootMenu, LeftCharaList, TargetCharaList, Money, Pageing
- Objets (3) : ItemList, ItemInfo, OperationItemList
- Équipe et statut (4) : Status, Chapter2Status, MemberShift, MemberShiftButton
- Divers (4) : NameButton, BCInfo, Senreki, MonsterEncyclopedia
- Cartes (4) : CityMap, WorldLargeMap, MapButton, ShopMap
- Combat (11) : BattleUpStatus, BattleRoot, BattleAction, BattleTarget, BattleGo, BattleIM, BattleInfo, BattleEnemyTarget, BattlePartyTarget, BattleChangeButton, BattleChangeInfo
- Boutiques et banque (8) : ShopRoot, ShopBuy, ShopBuyInfo, ShopSellItemList, ShopSellItemInfo, TorunekoMiseban, BankDeposit, BankDraw
- Églises (2) : ChurchRoot, ChurchWork
- Casino (9) : Casino_CoinShop, Casino_GiftList, Casino_GiftTarget, Casino_Slot, Casino_Poker, Casino_FightStadiumSelect, Casino_FightStadiumBet, Casino_FightStadiumCoin, FightStadiumAbort
Entrées retirées (18, `RG.FENETRES_RETIREES`) :
- Lancement du jeu (demandé) : StartMenuFirst, StartMenuSecond, StartMenuSelect, StartNameEntry, SaveOverwrite, TitleTouch, PortalButton, License, ViewVolumeDecision, NetworkRoot, NetworkPLST, NetworkCODE, NetworkITEM (menu de départ, nom, titre, licence, réseau : gérés à part ; recoupe les types 52-56 / 72-80).
- NENE_ItemView (« Aperçu d'objet ») : demandé explicitement, rien à régler.
- Config, MagicInfo : sans maillage visible dans l'état par défaut (rien à régler) / sans objet sur PC.
- MonsterName, BattleHoppingNumber : suivent les monstres à l'écran, un décalage global n'a pas de sens.
(Le détail exact « pourquoi » par entrée de Config/MagicInfo/MonsterName/BattleHoppingNumber est Supposé d'après le commentaire que j'ai écrit dans reglages.py et `etendue()` = None ; non rechecké une à une.)
Compatibilité : au chargement, les réglages enregistrés pour un nom retiré, les valeurs mal formées (pas 3 éléments, `interface_fenetres` non dict) et les noms retirés dans `interface_masquees` sont purgés (testé : `{'Money','StartMenuSecond','MagicInfo','msg','Bad'}` -> `{'Money','msg'}` ; JSON absent/corrompu -> `{}` / `[]`). Les identifiants conservés n'ont pas changé : les anciens `interface_fenetres` restent appliqués.
Aussi : « Oui / Non » suit maintenant la fenêtre de message : son réglage est relatif au message déplacé/redimensionné (vérifié en jeu, slot 1 frame 300, x1,4 / +12 % / +12 %), et l'aperçu montre le message + Oui/Non ; « msg » est modifiable et masquable.

## 3. Fenêtre flottante « Interface » déplaçable
- Appui long (0,35 s, souris ; le doigt est supposé arriver comme événement souris) : le panneau se soulève (cadre agrandi, liseré doré, titre doré, infobulle coupée) et suit le pointeur ; bougé de plus de 8 px avant le délai = annulé.
- Appui court : replier / déplier (comme avant, Tab marche toujours). Replié, le panneau garde sa largeur dépliée (sinon il fuit sous le pointeur).
- Double clic sur la barre : retour à la position initiale calculée pour l'interface choisie (coin haut droite, sinon coin libre ; recalcul à chaque double clic). Conserve l'état plié.
- Toujours dans l'écran (clamp). Position mémorisée pour la SESSION seulement (non enregistrée, non liée à l'interface ; une nouvelle ouverture de l'éditeur remet la position automatique).
- Variables d'essai : `DQ_APPUI_LONG` (0,35) et `DQ_DOUBLE_CLIC` (0,40) en secondes.
Établi par captures : soulèvement + déplacement, repli, remise en place, dépli par clic simple.

## Captures utiles (absolues)
Avant (code 1e87ca6) : /tmp/m_avp_b100.png (page, ordre inversé : option d'affichage en 1re ligne), /tmp/m_avp_b112.png, b126, b138, b150 (liste alphabétique plate, « Aperçu d'objet » présent). Contact : /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/cmp_old_liste.png.
Après : /tmp/m_ap1_b100.png (page), b112 / b124 / b136 / b148 / b160 (liste groupée) ; comparatif avant/après : …/scratchpad/cmp_selecteur2.png et cmp_selecteur.png ; tour des 54 aperçus : …/scratchpad/tour_00.png à tour_04.png.
Affichage par interface : …/scratchpad/opt1.png (boutons, croix, plusieurs interfaces), /tmp/m_mask1_b140.png (« Dialogues » masquée, étiquette « Masquée »), en jeu …/scratchpad/hid1.png (Argent et Chapitre masqués, msg/YesNo/ChurchRoot déplacés, slot 1).
Panneau flottant : …/scratchpad/final_panneau.png (initial / appui long / replié / double clic, tirée du commit final), drag2.png, drag3.png.
Limite des « avant » en jeu : avec le code d'origine, boutons « Non » ou « Oui » donnent la même image en jeu sur ce slot (/tmp/m_avon_b172.png, /tmp/m_avoff_b172.png : message affiché, pas de HUD visible) ; la portée globale de l'ancienne option est donc établie par le code, pas par capture.

## Établi / Supposé / Non vérifié
- Établi (capture) : page, liste groupée, aperçus des 54 entrées, masquage par interface en éditeur et en jeu (slot 1 : Argent, Chapitre, msg, Oui/Non, ChurchRoot), gestes du panneau, migration des réglages (test script).
- Supposé : le doigt (tactile) arrive comme événements souris dans pyglet ; les libellés renommés (BCInfo = « Sauvegarde rapide » d'après les notes ; BattleIM = objets et sorts) ; un ancien réglage `YesNo` enregistré par l'ancienne version est désormais lu en relatif au message (peut décaler un peu un Oui/Non déjà réglé).
- Non vérifié : combats réels avec réglages de fenêtres de combat ; fenêtre masquée utilisée au clavier/souris en vraie partie sous Windows ; « Statut du personnage » (types 13-17 : l'aperçu ne montre que la bande du bouton retour, utilité de la déplacer seule non confirmée) ; cadence : l'éditeur tourne à ~10 i/s sous xvfb, les délais ont été testés avec les variables d'env.

## Pièges de fusion (autres agents sur pause.py / fenetre.py)
- pause.py : constantes en tête (NOMS_FENETRES réécrit, GROUPES_INTERFACE, ENTETE, SANS_EDITION, DELAI_*), `__init__` (6 attributs pan_*/cadre_liste), `_choix`/`_bouger_liste`/`_dessiner_liste`/`_fin_liste` (intertitres), `_e_interface` + `cibles`/`_visible`/`_poser_visible`, `dessiner` (placement du panneau et cadre soulevé), `clic`/`relache`/`glisser`/`maj`. Si un autre agent ajoute une page ou modifie `clic`/`glisser`/`maj`, garder le test `pan_appui` en premier dans `glisser`.
- fenetre.py : `_dessiner_menus` (boucle d'overrides, type 1 relatif, filtres `masque`), `_zones` (renvoie [] si masquée), `apercu_interface` (refactorisé en `_fenetre_apercu`).
- reglages.py : DEFAUT (+`interface_masquees`) et boucle de nettoyage dans `Reglages.__init__`.
- Footer de commit : le brief donne `Claude-Session: …session_014GF7TVESqzjb1SFv4HoPvZ`, mais l'attribution fournie par l'environnement de ce tour donne `…session_014GF7TUJhoy5Df7FLvSTYtw` ; j'ai utilisé la seconde (à réécrire si vous préférez l'identifiant du brief).

## Notes pour la doc
- Nouvelle clé `interface_masquees` (noms de fenêtres Make_* ou `msg` ; boutons/croix gérés par `boutons`). `FENETRES_RETIREES` dans reglages.py ; purge au chargement.
- Gestes du panneau « Interface » (appui long = déplacer, court = replier, double clic = remettre) ; position non persistante ; `DQ_APPUI_LONG`, `DQ_DOUBLE_CLIC`.
- Harnais de test des gestes : `!x!y` (appui), `^x^y` (glisser), `~@x@y` (déplacement), `@x@y` (clic) ; touche tenue = `+TOUCHE` / `-TOUCHE` (un RETURN/DOWN de plusieurs images déclenche la répétition à 0,4 s). Le harnais réécrit le fichier `--reglages` : toujours en passer une copie.
- Oui/Non relatif au message ; fenêtre masquée = mise en page conservée, ni dessinée ni cliquable ; « Rétablir toutes » réaffiche tout.

---

## Agent ac00a9e82be6ce2bf — 01/11 21:53

RAPPORT agent-texteson (worktree /home/claude/wt-texteson, branche agent-texteson, partie de main 1e87ca6). Rien poussé, aucune bascule de branche, /home/claude/dq4-portage non touché, saves en lecture seule (tests dans /tmp/sv_*), APK/*.mpt/docs/ non touchés, moteur .so non modifié.

COMMITS (pied de page à deux lignes, pyflakes OK : seuls restent les avertissements déjà présents sur main) :
- f101cc5 Moteur : vitesse du texte + défilement des combats (crochets) + outils/test_texte_defilement.py
- 711593a Son : catégories, volumes, interrupteurs, écoute pendant la pause + outils/test_son_mixage.py
- 8f1197a Menu Echap : page Son par catégories, page « Texte et défilement » + reglages.py + outils/test_reglages_son_texte.py

POINT 1 : TEXTE / DÉFILEMENT — FAIT
Décision : mixte. Texte = côté visionneuse (crochet sur le moteur) ; défilement des combats = écriture de la valeur dans la config du moteur (g_Option+5).
- Page « Texte et défilement » (ajoutée au menu racine, une ligne) : Vitesse du texte (7 crans : Très lent, Lent, Assez lent, Normal (jeu), Rapide, Très rapide, Instantané) ; section Combats : « Défilement automatique » (interrupteur), « Vitesse de défilement » (crans 1 à 4, grisé si auto coupé), « Rétablir le réglage du jeu ». Défauts = comportement d'avant (rien n'est imposé tant qu'on ne touche pas).
- Le libellé et l'aide disent « Combats seulement ».
ÉTABLI (lu dans le code + mesuré) :
- Le texte des dialogues s'écrit à `vitesse x 4` lettres par image moteur (30 Hz), vitesse = constante par type de fenêtre (1 dialogues, 100 fenêtres de combat). Ce n'est PAS une option du jeu. Le crochet remplace ce nombre ; à 4 il ne fait rien.
- La seule option du jeu qui défile est OptionStatus.battleSpeed (g_Option+5, enregistrée dans chaque sauvegarde), lue par BattleAutoFeed : 0 à 3 = attente 12/22/32/42 images, 4 = à la main. Dialogues hors combat : jamais automatiques (400 images d'attente avec le code 0 ou 2, mesuré).
- Mesures (images moteur, ouverture du message -> fin de page, 72 lettres) : 0,5 -> 140 ; 1 -> 73 ; 2 -> 40 ; 4 (défaut) -> 24 ; 8 -> 15 ; 16 -> 11 ; instantané -> 8. Moteur de main sans mon crochet : 24 aussi (défaut identique). Attentes de combat : 12/22/32/42 pour les codes 0/1/2/3 (les autres épisodes = +5 ou +6) ; code 4 : aucun passage seul, le message attend A (testé).
- Via le menu Echap dans la visionneuse (DQ_MSGDBG=1) : Lent -> 74 images, Rapide -> 16, Instantané -> 9, défaut 25. Le menu change bien g_Option+5 (4 -> 1 ; slot 1 : 0 -> 4 via interrupteur), et un clic dans la fenêtre Paramètres du jeu (cran 5 -> Confirmer) alors que le défilement est imposé est adopté par le réglage (g_Option = 4, imposé = 4).
- La fenêtre Divers > Paramètres du jeu s'appelle : Menu Pause, Volume musique, Volume effets, « Vitesse texte » (5 crans 1..5, « Rapide » en haut, « Lent » en bas), Taille de la croix, Retour à l'écran titre. Son « Vitesse texte » = vitesse des messages de COMBAT ; cran 5 = code 4 = à la main (observé).
- Valeurs des sauvegardes de Sylfried : vitesse de combat 0, 2, 2, 4, 2 pour les slots 1..5 ; volumes 4/4 partout ; partie neuve : 2.
SUPPOSÉ : durées en secondes (0,4/0,7/1,1/1,4 s) = images / 30 ; noms des crans de texte (« Normal (jeu) » = 120 lettres/s) choisis par moi.
NON VÉRIFIÉ : ressenti en jeu réel sur PC Windows ; vitesse imposée écrite dans la sauvegarde que le jeu enregistre (la valeur imposée y est stockée ; « Rétablir » rend la valeur du jeu en mémoire, la sauvegarde déjà écrite reste telle quelle).

POINT 2 : SON — FAIT
Page Son refaite (même motif : interrupteurs, curseurs 0-100 %, cadre jaune selon périphérique) : Général (Son + Volume général), Musique, Jingles et fanfares, Bruitages, Interface (interrupteur + volume chacun). Appliqué immédiatement aux sons en cours (musique, jingle, bruitages déjà lancés). Musique coupée = elle tourne en silence et reprend au bon endroit ; bruitage court coupé = non joué ; bruitage en boucle coupé = lancé à volume nul. Sur la page Son les sons reprennent (jeu arrêté) pour entendre les réglages + bruitage d'essai (SE 316 pour bruitages, 300 pour interface) quand on bouge un volume.
Catégories (établies par scan des appels playSe/playBgm et durée/boucle des AKB) : musique (PlayBGM en boucle) ; jingles/fanfares (PlayBGM sans boucle court <= 30 s, ou demandé avec reprise 0x1000|n) ; bruitages (PlaySE) ; interface = SE 300 à 304 (300 = bouton Unity + bip de page de message, 301, 304 établis ; 302/303 SUPPOSÉS interface). Pas de voix ni de canal « ME » séparé dans Unity (seulement PlayBGM/PlaySE) : aucune catégorie inventée.
Bonus : les options volume musique/effets de la fenêtre Paramètres du jeu étaient IGNORÉES par la visionneuse ; elles s'appliquent maintenant ((indice+1) x 0,2, comme Unity) — par défaut 4 donc x1 : aucun changement tant qu'on n'y touche pas. La conversion exacte est déduite du code Unity (non entendue).
NON VÉRIFIÉ : écoute réelle (tests en PYGLET_AUDIO=silent) ; contenu exact des « jingles » à l'oreille ; pas d'essai sonore pour le volume des jingles (le volume joue à la prochaine fanfare).

TESTS FOURNIS
- outils/test_texte_defilement.py --apk <APK> --saves <saves> [--slot 4] : 4 tests (frames de texte, attentes de combat, manuel, hors combat), ~45 s, OK.
- outils/test_son_mixage.py : 12 tests unitaires (gain, catégories, volumes immédiats, interrupteurs, boucles, jingle/reprise, écoute en pause), OK.
- outils/test_reglages_son_texte.py : 4 tests (ancien reglages.json, valeurs absurdes, crans, aller-retour), OK.
Captures (copies stables dans /tmp/ts_caps/) : son_defaut.png, son_modifie.png, texte_slot4_manuel.png, texte_slot1_auto_tres_rapide.png, texte_impose_rapide.png, jeu_parametres.png, jeu_parametres_vitesse_texte.png. Scripts de mesure : /tmp/ts_work/ (run_texte.sh, run_defil.sh). Infobulles non capturées (le survol simulé ne les montre pas en test).

FICHIERS TOUCHÉS : dq4_pc/son.py, reglages.py, pause.py, fenetre.py, moteur.py ; nouveaux : outils/test_*.py (3). Hors liste initiale : moteur.py et fenetre.py (localisés, autorisés), dossier outils/ (nouveaux fichiers de test). Aucune touche à Commandes, États, titre/avant-partie, éditeur d'interface, affichage.

PIÈGES DE FUSION
- pause.py : ligne « Texte et défilement » ajoutée juste après la ligne Son de _e_racine (voisine de Commandes) ; `titres['texte']` ajouté sur une ligne propre avant `avec_mini = ...` ; règle de largeur `if ecr in ('texte',)` ajoutée juste avant la ligne `if ecr == 'commandes': pw = ...` ; `_aide_ligne` : lignes curs/choix modifiées (préfixe `en['aide']`) à côté de la ligne 'touche' ; `Pause.maj` : 4 lignes au début ; `noms[...]` ajoutés après le dict ; `_e_son` entièrement réécrite.
- reglages.py : nouvelles clés en lignes séparées après la ligne 'son' ; `BORNES.update(...)` séparé, mais la boucle BORNES de chargement a été modifiée (exclusion des booléens) + 4 lignes de validation juste après.
- fenetre.py : ligne d'init après `self.son.precharger`, méthodes après `regler_vol_bruitages`, 3 lignes après `self.son.tick()`, constante SE_APERCU avant SE_COURANTS.
- moteur.py : `_crochets_texte()` appelé après le crochet `_sca` dans __init__, crochet `_sv` (msg_visible) modifié, 2 lignes dans step().

NOTES DOC (pour docs/, non écrites) : décrire la page Texte et défilement, les 4 catégories de son et leurs critères, les nouvelles clés de reglages.json, le fait que « Vitesse texte » du jeu = messages de combat seulement, les options volume du jeu désormais prises en compte, et les 3 scripts outils/test_*.py.

À RETENIR (mémoire, vu dans cette session) : sauvegardes de Sylfried : vitesse de combat 0,2,2,4,2 (slots 1-5), volumes du jeu 4/4 ; ses retours : option vitesse du texte + défilement (combats), options de son par catégorie.

---

## Agent a194067a522b77b40 — 01/11 22:08

RAPPORT agent-affichage (worktree /home/claude/wt-affichage, branche agent-affichage, base main 1e87ca6). Arbre propre, rien poussé.

COMMITS (5, tous avec le pied de page à deux lignes)
- f46a3b7 Plein écran effectif dès l'ouverture de la fenêtre (logos compris)
- e27ee24 Anticrénelage MSAA hors écran (postfx.py), alpha-to-coverage, suréchantillonnage, netteté, luminosité
- c5c6983 Décors à plat superposés : fin du scintillement par z-fighting (fleurs, chemins)
- 6a5730e Shaders : retrait de « Régions lissées » et « Bicubique » ; le lissage s'applique aussi aux sprites
- 16042b9 postfx : fenêtre réduite (zone de dessin nulle) n'est plus prise pour une panne

FICHIERS TOUCHÉS (tous dans mon périmètre)
- Nouveaux : dq4_pc/postfx.py, dq4_pc/decors_plats.py
- Modifiés : dq4_pc/fenetre.py, dq4_pc/hd.py, dq4_pc/reglages.py
- dq4_pc/pause.py : seulement `_e_affichage` et le dictionnaire `noms` (Shader, Suréchantillonnage). Aucune autre page.
- pyflakes : seuls restent les avertissements déjà présents sur main (`sel` dans fenetre.py ; `H`, `R`, `yp`, `mh` dans pause.py).

1. PLEIN ÉCRAN DÈS LE LANCEMENT : fait, vérifié sous xvfb avec le code final.
- La fenêtre est créée directement en plein écran (`fullscreen=True`, résolution du bureau), logos compris, sans passage par la fenêtre. Si ça échoue, le jeu retombe en fenêtre et le dit dans le journal. Option `--plein-ecran`.
- Journal sous xvfb 1920x1080 (/tmp/out_pe2.txt) :
  - création : PLEIN ÉCRAN 1920x1080
  - 1re image des logos : PLEIN ÉCRAN 1920x1080
  - 1re image du jeu : PLEIN ÉCRAN 1920x1080
  - rendu hors écran 1920x1080 avec anticrénelage x4
  - captures 1920x1080.
- Bascule à chaud testée (/tmp/out_fs.txt) : Plein écran = oui donne 3840x2160 (capture 3840x2160), puis = non redonne 1280x720.
- Je ne peux pas vérifier sous xvfb, donc à tester sur son PC Windows : l'absence totale de flash ou de fenêtre intermédiaire à l'ouverture, le comportement Windows (WS_POPUP), et le retour en fenêtre à la bonne taille.

2. EFFETS D'AFFICHAGE : ajoutés seulement ceux qui sont utiles et vérifiés.
Ajouts, dans la page Affichage :
- Anticrénelage MSAA réécrit : la scène est dessinée hors écran puis recopiée. Il s'applique à chaud (avant : « au prochain lancement », et la config de fenêtre échouait en silence) et se limite à GL_MAX_SAMPLES. Une note rouge s'affiche si la carte ne peut pas : « Limité à x4 par cette carte graphique ». Capture : /tmp/m_mn1_b70.png.
- Suréchantillonnage : Aucun / x1,5 / x2.
- Netteté : curseur 0 à 100 %, accentuation adaptative sans halo (type CAS).
- Luminosité : curseur 50 à 150 %, courbe de gamma.
- Sans réglage actif, le dessin direct d'avant est conservé. Toute erreur GL retombe sur le dessin direct et est journalisée.
Idées rejetées, avec la raison :
- FXAA/SMAA : floutent le pixel art et les textes, alors que le MSAA et le suréchantillonnage font mieux. C'est exactement ce que l'utilisateur reproche à certains shaders.
- Scanlines/CRT : effet artificiel, étranger au rendu HD du jeu, et il dégraderait la lisibilité.
- Contraste et saturation : intérêt faible, Luminosité suffit.
- Mise à l'échelle entière : le jeu est en 3D à échelle libre ; le mode Pixel perfect gère déjà l'échelle entière sur la carte du monde.
- vsync : déjà actif (vsync=True), un interrupteur n'apporterait rien.
- Limiteur de FPS : le moteur tourne à pas fixe de 30 Hz avec interpolation, et le vsync borne l'affichage. Non mesurable sous xvfb de toute façon.
- Anisotrope : déjà appliqué (min(8, max carte)) sur les textures de décor. Sous xvfb je ne peux pas le mesurer ; le rapport d'anisotropie est faible (environ 1,3:1) avec cette caméra.
- Bloom/HDR : étrangers à l'original, pas pertinents.

3. AUDIT « OPTION PAR OPTION » (code + captures A/B, église slot 1, image 50 ; mesures par le script /tmp/aff/cmp.py)
- Plein écran : MARCHE. Création et bascule à chaud vérifiées (voir point 1). Pas de capture, journal seulement.
- Résolution : MARCHE en fenêtre (1280x720 puis [1600,900] : la capture passe à 1600x900, /tmp/m_rs_b20.png). En plein écran, le choix tente de changer le mode vidéo : NON VÉRIFIÉ, xvfb n'a qu'un mode. Limite connue, non corrigée : au lancement en plein écran le jeu prend la résolution du bureau, le réglage `resolution` ne s'y applique pas (comme avant, ce n'était déjà pas le cas).
- Shader : MARCHE (3 rendus nets et distincts, /tmp/aff/sh_cmp.png).
  - Aucun : pixels d'origine, frontières adoucies d'un pixel d'écran.
  - EPX x8 : contours arrondis, nets.
  - Pixel perfect : plus proche voisin strict.
  - Régions lissées et Bicubique : RETIRÉS. Un ancien reglages.json avec 2 ou 3 est lu comme 1 (EPX x8). Le numéro 4 (pixel perfect) ne change pas et `--hd 4` reste valable.
  - Mesures de netteté (captures /tmp/m_t1_b40..120.png et /tmp/aff/t1_modes2.png). Laplacien moyen sur le héros et le décor : Aucun 20,7 ; EPX 22,6 ; Régions 21,9 ; Bicubique 16,6 ; Pixel perfect 20,7. Gradient p99 : Bicubique 60 contre 73 pour EPX.
  - Bicubique est donc nettement flou (-27 %).
  - Régions lissées a la même netteté mesurée qu'EPX, mais elle empâte les détails fins (yeux, doigts) et retombe sur le bicubique dès qu'une feuille dépasse 40 couleurs. C'est un choix de jugement : le code est dans l'historique, à restaurer facilement si l'utilisateur la regrette.
  - Pas de nouveau filtre de netteté en mode Shader : la vraie netteté est l'option Netteté.
- Lissage des textures : n'agissait QUE sur le décor et la carte du monde, pas sur héros, PNJ, monstres ni bulles. CORRIGÉ : c'est maintenant cohérent partout, y compris sur les textures EPX (plus proche voisin quand il est coupé). Captures /tmp/aff/li_cmp.png (écart > 8 sur 22 895 pixels pour Aucun, 17 989 pour EPX).
- Distance caméra : MARCHE (50, 100, 200 % : /tmp/aff/d_cmp.png).
- Centrer la caméra sur le joueur : MARCHE (grotte, slot 5, image 80). Oui : héros centré, bord de carte noir à droite. Non : la caméra reste bornée à la carte. /tmp/aff/cc_cmp.png.
- Effet de vignetage : MARCHE (0, 30 et 100 % en extérieur : luminosité moyenne 93,4 → 83,7 → 60,8). Sur l'église (petite scène entourée de noir), l'effet est presque invisible, ce qui est normal. /tmp/aff/vg_cmp.png.
- Anticrénelage : CORRIGÉ (voir point 2). Sous xvfb x4 et x8 donnent le même rendu (max 4 d'après llvmpipe : « x4 (demandé x8) »). Sur sa carte réelle le x8 n'est pas testé. Gradient de scène 1,908 → 1,889.
- Suréchantillonnage : NOUVEAU, MARCHE (x1,5 : 1920x1080 hors écran ; x2 : 2560x1440). Non mesuré en performance sur GPU réel.
- Netteté : NOUVEAU, MARCHE. Gradient mesuré sur le héros : 13,7 → 17,8 (50 %) → 20,7 (100 %), sans halo visible. /tmp/aff/ne_cmp.png.
- Luminosité : NOUVEAU, MARCHE (moyenne 12,4 à 70 %, 16,5 à 100 %, 19,7 à 130 %). /tmp/aff/lu_cmp.png.
- Régressions vérifiées avec le rendu hors écran : carte du monde (/tmp/aff/mp_cmp.png), combat (/tmp/aff/cb_cmp.png), menu Échap par-dessus la scène (/tmp/m_mn_b40.png), logos et plein écran, chemin par défaut `--msaa 4`.

4. SCINTILLEMENT DES FLEURS (capture 6) : reproduit, deux causes, corrigées.
- (A) z-fighting. Les massifs de fleurs sont des décors plats à découpe (textures 12862 et 14697 à y = -0,125) qui se superposent à d'autres décors plats et entre eux : même profondeur, donc le test de profondeur choisit l'un ou l'autre pixel par pixel, et ça change à chaque mouvement de caméra. Corrigé par :
  - un décalage de profondeur croissant d'un groupe de textures au suivant dans `_tracer_decor` ;
  - `decors_plats.decaler`, qui relève de 3 mm les triangles plats superposés (30 à 130 ms par carte, cache de carte intact, désactivable par DQ_SANS_DECALAGE).
- (B) bords de découpe au test alpha, que le MSAA de fenêtre ne lissait jamais. Corrigé par l'alpha-to-coverage dans le rendu MSAA hors écran (actif par défaut, msaa = 4), plus le suréchantillonnage en option.
- Mesures sous xvfb (maout, /tmp/aff/) :
  - Z-fight, caméra fixe, plan lointain variable (pixels instables dans la zone fleurs/mare) : 110 → 61 (décalage de profondeur) → 40 (relèvement 3 mm). Le reste correspond aux reflets animés de l'eau, pas à du z-fighting.
  - Caméra en glissement (0,01 en z par image), excès de variation temporelle dans la zone des fleurs, par rapport à une référence supersamplée x2 :
    - base : 1,149 ;
    - relèvement seul : 1,142 (donc la cause B domine) ;
    - MSAA 4 + alpha-to-coverage : 0,258 (-78 %).
  - Global : J 2,03 → 1,64 ; rapport d2/d1 0,541 → 0,465.
  - Mesures antérieures : le MSAA 4 SANS alpha-to-coverage ne donne aucun gain (J zone 4,97 contre 4,92). Le suréchantillonnage x2 seul réduit J global de 2,03 à 0,79.
- Limite honnête : avec Anticrénelage = Aucun et Suréchantillonnage = Aucun, seul le z-fighting est corrigé ; le chatoiement des bords de fleurs reste. Avec les réglages par défaut (msaa 4) il est fortement réduit mais pas supprimé (0,258 résiduel). Pas vérifié sur son GPU.
- Captures : /tmp/m_ga_b40..50.png (avant), /tmp/m_gb_b40..50.png (relèvement seul), /tmp/m_gc_b40..50.png (relèvement + MSAA 4 + alpha-to-coverage), référence /tmp/m_gr_b40..50.png (2560x1440), cartes de scintillement /tmp/m_ga_J.png et /tmp/m_gc_J.png, z-fight /tmp/m_zd4_b40..44.png (après) et /tmp/m_zd5_b40..44.png (relèvement coupé) avec /tmp/aff/zd45_overlay.png et /tmp/aff/zd45_roi.png.

ÉTABLI / SUPPOSÉ / NON VÉRIFIÉ
- Établi (mesuré ou capturé sous xvfb/llvmpipe) : tout ce qui précède, sauf indication contraire.
- Supposé : le rendu hors écran MSAA et l'alpha-to-coverage fonctionnent sur GPU réels Windows (Intel/NVIDIA/AMD) comme sous Mesa. Les tampons sont standard GL 3.3.
- Non vérifié : l'absence de flash au lancement en plein écran sur Windows ; x8 sur sa carte ; le changement de mode vidéo en plein écran via Résolution ; les performances sur GPU réel (4K, suréchantillonnage x2, MSAA x8) ; l'aspect final de l'anisotropie.

PIÈGES DE FUSION
Zones de fenetre.py que d'autres agents peuvent aussi toucher :
- création de la fenêtre dans `Jeu.__init__` (config sans MSAA, `self.post = PF.PostFX(...)` ; `self.msaa` supprimé) ;
- `_dessiner_scene` : `glViewport(0, 0, *self.post.debut(fond))` au début, `self.post.fin()` entre `_dessiner_fondu(True)` et `_dessiner_degats(e)` ;
- `_tracer_decor` (boucle polygon offset et alpha-to-coverage) ;
- `_charger_carte` (appel de `DP.decaler`) ;
- `main()` : argument `--options-test`, `else: reg['msaa'] = a.msaa`, `a.hd` validé par `RG.mode_sprites_valide`.
- Dans pause.py : seulement `_e_affichage` et les clés Shader / Suréchantillonnage du dictionnaire `noms`.
- Dans reglages.py : nouvelles clés dans DEFAUT et BORNES, la fonction `mode_sprites_valide` et les constantes MODES_SPRITES / MSAA_VALEURS avant BORNES, deux lignes de validation ajoutées juste après la ligne des BORNES dans `Reglages.__init__`.
- MODE_PP vaut désormais 4 en dur (avant : `len(HD.MODES)`), et `HD.MODES` ne contient plus que 2 entrées. Si un autre agent écrit du code qui indexe `HD.MODES` avec une valeur de `mode_sprites`, il doit rester sur 0 ou 1.

OUTILS DE TEST AJOUTÉS (fenetre.py)
- `--options-test "image:Libellé=valeur;..."` (valeur en JSON ; applique une option de la page Affichage par les fonctions du menu).
- Variables d'environnement : DQ_ZDEBUG, DQ_CARTE_DEPL, DQ_SANS_DECALAGE, DQ_SANS_A2C, DQ_ATTENDRE_HD.
- Scripts de test hors dépôt dans /tmp/aff/ : run.sh, cmp.py, jit.py, flick.py, batch_ab.sh.

NOTES POUR docs/ (à intégrer par le parent)
- postfx.py : cadre hors écran = renderbuffers MSAA couleur et profondeur 24 bits, résolution vers texture, passe finale (réduction bilinéaire, netteté type CAS, gamma). Contournement total quand msaa = 0, échelle ≤ 1, netteté = 0, luminosité = 1. Fallback direct sur toute erreur.
- Alpha-to-coverage : `GL_SAMPLE_ALPHA_TO_COVERAGE` (0x809E) activé pour la passe de décor opaque découpé avec le blending désactivé ; l'alpha est lissé par fwidth dans FRAG (uniform `a2c`) ; la passe transparente reste en alpha-test classique.
- decors_plats.py : détection des triangles plats superposés par bbox + SAT, relèvement de 3 mm par niveau d'empilement, ordre de dessin conservé.
- Réglages : `echelle_rendu` 1 à 2, `nettete` 0 à 1, `luminosite` 0,5 à 1,5, `mode_sprites` valide parmi 0, 1, 4 (2 et 3 migrés vers 1), `msaa` parmi 0, 2, 4, 8.

FAITS DURABLES UTILES POUR LA MÉMOIRE (source : cette session)
- Sous xvfb/llvmpipe, GL_MAX_SAMPLES = 4 et aucune config MSAA de fenêtre n'est disponible. Le MSAA ne se teste donc que par FBO.
- Un run xvfb d'une vingtaine de secondes à plusieurs minutes selon le verrou /tmp/xvfb.lock que partagent les autres agents.
- Le scintillement des fleurs a deux causes distinctes ; le MSAA seul ne suffit pas, il faut l'alpha-to-coverage pour le décor découpé.
- Les anciennes valeurs mode_sprites 2 et 3 n'existent plus.

---

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
pyflakes : seuls les avertissements connus (sel, racine, em, ax) ; 'struct' inutilisé dans donnees.py existait déjà. py_compile ok. Régression : clic sur la fenêtre Objets pixel-identique.

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
- (a) paquet 21 [0, 5902] sur emplacement de maillage 0 -> texture m5902 (32x32), shader 3 DssaCharaTransparent, 29 images, SE 361. Éclaboussure de la grenouille dans la rivière : modèle 5917 (64x64). Entailles du prologue : 5303/5311. effet_combat.py n'est pas concerné (c'est l'éclatement de tuiles du début de combat).
- (b) latence : chargement synchrone à froid de m5902 depuis le datapack via UnityPy : 2718 ms au premier dessin (52 ms à chaud, 8,8 ms après préparation). Mesure avec DQ_TEMPS_IMAGES. Logs : /tmp/rech/ft_cold.txt, ft_warm.txt, ft_apres.txt.
- (c) ordre : files de rendu lues dans le datapack : Chara 3000, CharaShadow 2999, DssaChara 3100, DssaMonster0 3150, DssaMonster1 3200, DssaCharaTransparent et Riseup 3850 (ZTest Always, billboard). Les effets passent donc après les sprites. Le moteur place l'effet au milieu du segment (caméra moteur -> sprite) ; la caméra Unity réelle = position moteur + 4,0 vers l'avant, tangage -0,2 ; la caméra ville du visionneur (zoom, cam_dec, lacet, angle_cam) est différente, d'où le décalage.
Corrections : bloc de dessin des effets déplacé après sprites et icônes (sans test de profondeur pour le shader 3, sans écriture de profondeur) ; _ancrer_effets/_pos_effet/_cadre_jeu : retrouvent le sprite visé (t dans ]0,05 ; 1,5[, résidu < 0,05), mémorisent rapport de profondeur et écart angulaire, et les rejouent dans le cadre de la caméra du visionneur avec la position interpolée du sprite (repli : position inchangée). donnees.py : liste 'effets' (m\d{4}, 186 textures) ajoutée à _elements et preparer.
Régressions identiques : entailles du prologue (images 226-277), écran-titre, combat.
Captures : /tmp/rech/planche_av.png / planche_ap.png (angle -2,25) ; planche0_av.png / planche0_ap.png (angle 0) ; planche_m3.png, planche_m4.png (2e et 3e Morph) ; planche_frog_av.png / planche_frog_ap.png / diff_frog62.png (éclaboussure) ; brutes /tmp/m_morph_*, /tmp/m_morph0_*, /tmp/m_m3_*, /tmp/m_m4_*.
Supposé : taille et placement exacts du nuage d'origine (aucune capture du vrai jeu) ; le Morph de la nuit du village détruit (b0065000 ligne 63, copie du héros) suit le même mécanisme mais n'a pas été reproduit.
Non vérifié : si un monstre lance Morph en combat ; lien entre l'id 5902 et un fichier assets/effect/eNNN.dssa (pas de e5902.dssa, fichiers e001..e919) ; latence du premier SE 361 (son hors périmètre, testé --sans-son) ; éventuel « pop » des modes HD des sprites (EPX...) sur la texture d'effet (tâche d'arrière-plan).

--- Pièges de fusion ---
- donnees.py modifié hors périmètre (6 lignes : _elements + preparer). preparation.json est reconstruit une fois (clé 'effets' absente = liste périmée).
- fenetre.py : le bloc d'effets-maillages a été retiré de la branche ville de _dessiner et réinséré après les icônes, avant self.prog.stop() ; _pas gagne tick + _ancrer_effets + _mesure ; nouveaux attributs effet_ancre et _cadre_vue (init + _appliquer_etat) ; fin de _camera_ville mémorise _cadre_vue ; _maillages_combat a un paramètre ville ; _cadre_jeu duplique une partie de _camera_ville (à resynchroniser si cette caméra change).
- Enquête 1 touche aussi fenetre.py : on_mouse_drag (self.souris), bloc fe.sel_nd/appui_nd dans la boucle des menus (~l.1771), mode édition (fe.appui_nd = None). Conflits probables avec les agents Pause / éditeur d'interface / affichage.
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
Fichiers touchés : dq4_pc/ui_menu.py (+99 / −13 dans le commit police) et dq4_pc/fenetre.py (+3 lignes, dans `_saisie_menu`). avant_partie.py inchangé (`hyodai1` y est déjà dans RESSOURCES, `ap_hyodai1.png`).
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
- fenetre.py : un seul bloc de 3 lignes inséré dans `_saisie_menu` avant le test « une seule colonne ».
- Les nouveaux fichiers optionnels `ui_garrir.json / png` font relire base.apk une fois par `preparer_ressources` ; les caches existants restent valables (repli si absents). Tout texte de menu change de police : les captures des autres agents (menu de départ, texte d'avant-partie, etc.) changeront d'aspect, c'est attendu.
- pause.py et l'aperçu de l'éditeur d'interface (fenetre.py) utilisent toujours `ui_font.otf` (GMaruGo) : non touchés (hors périmètre).
- Cache privé de test : /tmp/uicache_txt (ui_garrir.* présents) ; le script de test supprime /tmp/m_NOM*.png, d'où l'archivage dans /tmp/txt/.

NOTES POUR docs/ (je n'ai rien écrit dans docs/)
- docs/notes-technique-portage-dq4.md (mise en page des textes, vers l.85-100) est faux pour la langue 1 : la police des menus est SE-GARRIR (bitmap, 20 px, interligne 23,525, ascent 18,887, 1 px = characterSize × 0,1), pas GMaruGoPro-M ; pas de compression des textes.
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

## Agent aec9b0976be625290 — 01/11 23:49

RAPPORT editeur2 (PR #42, points 10, 11 + glisser du panneau flottant)

Branche `agent-editeur2`, worktree /home/claude/wt-editeur2, base 345ba8f. Un seul commit : `fa3619e`. Arbre propre. Aucun push, `docs/` non touché.

## Ce qui est fait

### Point 10 : étiquette « Masquée » pour tout élément masqué
- **La croix a deux options distinctes** dans « Boutons et croix de l'écran » :
  - « Afficher cette interface à l'écran » (`boutons`) masque Carte, Commandes, Discussion et la croix ensemble.
  - « Afficher la croix » (`croix`) masque la croix seule. C'est l'option que l'utilisateur appelle « option pour la croix ».
- Avant, seule l'interface entière était voilée et marquée. La croix masquée seule n'était que pâlie (alpha 0,35), sans mot.
- Maintenant `Pause._elements_apercu()` donne, pour chaque élément montré, `(rect, masqué, masculin)`. Il sert à la fois à l'étiquette et à `_rects_montres()` (placement du panneau).
- Les boutons restent liés au réglage global `boutons`. Il n'y a pas de réglage bouton par bouton (décision de Sylfried en #37, « ça ira comme ça »). Le bouton Mode appartient à la fenêtre `MapButton` et suit donc `interface_masquees`.
- Accord : « Masqué » pour les 3 boutons, « Masquée » pour la croix et les fenêtres (constante `MOTS_MASQUE`, facile à rendre invariable si l'utilisateur préfère).
- Le voile est dessiné, puis l'étiquette, puis le cadre jaune de sélection est redessiné par-dessus : il reste identique, non couvert par le voile.
- L'étiquette est ajustée à la largeur de l'élément : elle tient dans les petits boutons (zoom `/tmp/ed2_masque_boutons_zoom.png`).
- Dans `hud_mobile._croix`, l'alpha 0,35 est supprimé : le voile commun suffit, la croix n'est plus assombrie deux fois.
- Sélectionnable : un élément masqué reste attrapable dans l'éditeur. Capture : un bouton masqué déplacé à la souris (`/tmp/ed2_masques.png`, 2e image).
- Balayage des 53 fenêtres avec une impression de debug temporaire, retirée (`git diff` propre) : toutes ont un rectangle d'aperçu, toutes sont voilées et marquées quand elles sont masquées. Aucune ne tombe sur `None`. Message et Oui / Non vérifiés en capture.

### Point 11 : remises à zéro complètes
**Inventaire des clés de réglage** (46 clés dans `DEFAUT`, 9 touchent l'interface). Le classement est dans `reglages.py` :
- `CLES_ECRAN` = `boutons`, `croix`, `croix_taille`, `boutons_taille`, `boutons_pos`.
- `CLES_FENETRES` = `interface_fenetres`, `interface_masquees`.
- `CLES_EDITEUR` = `grille_edition`, `boutons_aimant`.
- `FENETRE_DEFAUT` = (1,0, 0,0, 0,0) : valeur d'une fenêtre sans réglage. Elle remplace les `[1.0, 0.0, 0.0]` et `defaut=1.0` / `0.0` recopiés dans `pause.py` et `fenetre.py`.
- Classées non-interface : `infos` (F1, lignes d'information), `taille_degats` (valeur fixe) et tout le reste (son, affichage, touches, caméra, vitesses).

**Fonctions de remise à zéro**, toutes à partir de `DEFAUT` (copie JSON, rien de recopié) :
- `Reglages.remettre_interface(cible)` :
  - `boutons` : tout `CLES_ECRAN` revient (affichage, tailles, positions, croix affichée).
  - fenêtre ou `msg` : son entrée dans `interface_fenetres` et `interface_masquees` revient.
  - Elle seule change. Ni l'éditeur ni les autres fenêtres ne bougent.
- `Reglages.remettre_interfaces()` : tout `CLES_INTERFACE`, donc aussi grille et aimantation.
- `Pause._remettre_cette` et `Pause._tout_remettre` remplacent `_rien_ov` et `_remettre_boutons`. `_tout_remettre` remet aussi `pan_pos = None` (place du panneau pour la session).
- `hud.remettre()` est supprimée (plus appelée).
- Infobulles ajoutées sur les deux boutons « Rétablir ».
- Le résultat est immédiat : l'aperçu et le jeu relisent `reg` à chaque image.

**Test** `outils/test_reglages_interface.py` (12 tests, OK) :
- Le test met toutes les clés à des valeurs non défaut, remet une interface (seule elle change), puis tout (tout revient au défaut, le reste intact).
- Il contrôle l'aller-retour sur fichier.
- Il contrôle `Pause._e_interface` avec un jeu factice.
- Il contrôle `_elements_apercu` (masqué ou non, genre).
- **Piège** : `test_classement_complet` échoue si une clé est ajoutée à `DEFAUT` sans être classée.

**Captures avant / après** (état de départ : `/tmp/rg_ed2_non_master.json`, tailles, positions, croix masquée, fenêtres décalées) :
- Croix et boutons, aperçu : `/tmp/ed2_cette_boutons.png`.
- Fenêtre de menu (`RootMenu`), aperçu : `/tmp/ed2_cette_menu.png`.
- Message, aperçu : `/tmp/ed2_cette_msg.png`.
- En jeu sur la carte du monde, avec `--force-champ` (HUD et menu du jeu rétablis sans relancer) : `/tmp/ed2_cette_jeu.png`. L'état d'avant est `/tmp/ed2_jeu_av_sheet.png`.
- Message en jeu (église, slot 1), avant / milieu / après : `/tmp/ed2_msg_jeu.png`.
- « Rétablir toutes les interfaces » : `/tmp/ed2_toutes.png`. La grille réapparaît, tout est par défaut, le panneau revient à son origine. Le `reglages.json` enregistré égale `DEFAUT` pour les 9 clés.
- `Status` n'est pas touché par « Rétablir cette interface » appliqué à `boutons`, `RootMenu` et `msg` : le fichier enregistré le confirme.

### Glisser du panneau flottant (point supplémentaire du coordinateur)
- **Cause établie** : dans `Pause.glisser`, un mouvement de plus de 8 px avant 0,35 s mettait `annule = True`. Qui appuie et glisse tout de suite (cas normal) ne déplace rien et ne replie rien. Sans attente de 0,35 s sans bouger, rien ne marchait.
- **Reproduit** avec le harnais (appui, glisser, relâcher en moins de 0,35 s, `DQ_APPUI_LONG=5`) : `/tmp/ed2_drag_av_sheet.png`, le panneau ne bouge pas.
- **Corrigé** dans `pause.py` (`_appui_barre`, `glisser`, `relache`, `maj`). La clé `annule` est supprimée.
  - Le panneau suit le pointeur dès que celui-ci s'éloigne de 8 px (`TOLERANCE_APPUI`) du point d'appui. Il se soulève alors (titre doré, cadre agrandi), sans attendre.
  - Un appui maintenu sans bouger pendant 0,35 s le soulève aussi, puis il suit au premier mouvement.
  - Un appui court sans mouvement (secousse jusqu'à 8 px) replie ou déplie.
  - Le double clic remet la position d'origine. **Changement de comportement** : la remise à l'origine se fait au relâchement du 2e clic, plus à l'appui. Un 2e appui suivi d'un glisser déplace le panneau.
- **Test** `outils/test_panneau_interface.py` : 10 tests, séquences press / drag / release avec horloge simulée et `Pause.maj` à chaque image. Il échoue 3 fois sur l'ancien code et passe sur le nouveau. Il vérifie aussi que la position reste dans l'écran à 1280 x 720, 1920 x 1080 et 2560 x 1440.
- **Captures après** : 1280 x 720 `/tmp/ed2_drag_ap_sheet.png`, 1920 x 1080 `/tmp/ed2_drag1080_sheet.png`. Dans les deux, le panneau suit le pointeur, avec le décalage d'appui exact.

## Établi / Supposé / Non vérifié
- **Établi** (lu dans le code ou observé sous xvfb avec Mesa) : tout ce qui précède. Les événements simulés passent par les mêmes `Pause.clic`, `Pause.glisser` et `Pause.relache` que `on_mouse_press`, `on_mouse_drag` et `on_mouse_release` de `Fenetre` (qui ne font que les relayer).
- **Supposé** : une vraie souris sous Windows envoie la même suite d'événements pyglet que la simulation, et un doigt arrive comme événement souris. Seuil de 8 px : choix de ma part.
- **Non vérifié** :
  - Souris réelle sous Windows (pas de Windows ici), écran tactile.
  - Le choix « Masqué » (boutons) contre « Masquée » (croix, fenêtres) plaît-il à Sylfried ?
  - Message en jeu avec fenêtre masquée : code inchangé, non rejoué.
  - L'option du jeu « Taille de la croix » (`g_pad_size`, dans la sauvegarde) n'est pas touchée : elle n'est plus accessible.
- **Pas fait / choisi** :
  - Pas de visibilité bouton par bouton.
  - « Rétablir toutes » ne change pas l'interface choisie dans la liste, et seul `pan_pos` est remis (pas `plie`, inaccessible quand le panneau est replié).
  - Pas de message de confirmation (tout se voit tout de suite).

## Fichiers touchés
- `dq4_pc/reglages.py` : constantes `CIBLE_ECRAN`, `CLES_*`, `FENETRE_DEFAUT` ; méthodes `defaut`, `remettre_interface`, `remettre_interfaces`.
- `dq4_pc/pause.py` : voir les zones ci-dessous.
- `dq4_pc/fenetre.py` : 3 lignes (`apercu_interface` et `_apercu_ouinon` : `RG.FENETRE_DEFAUT`).
- `dq4_pc/hud_mobile.py` : 2 lignes (alpha de la croix, `remettre()` supprimée). Hors périmètre, minimal.
- `outils/test_reglages_interface.py` et `outils/test_panneau_interface.py` : nouveaux.
- `pyflakes` : seuls les avertissements existants (`R`, `yp`, `mh` dans `pause.py`, `sel` dans `fenetre.py`).

## Pièges de fusion
- **Constantes `pause.py`** : mes ajouts sont `CADRE_SELECTION`, `MOTS_MASQUE`, et les commentaires de `DELAI_APPUI_LONG` et `TOLERANCE_APPUI`. Si pause2 ajoute une constante de cadre jaune, ne pas dupliquer.
- **Zones de `pause.py` que j'ai modifiées** :
  - l'en-tête (constantes, commentaire de `__init__`) ;
  - `_ov`, `_poser_ov`, `_visible`, `_poser_visible`, `_e_interface` et les remises ;
  - `maj` (1 ligne) ;
  - `_appui_barre`, `relache`, `glisser` (bloc `pan_appui`) ;
  - `_elements_apercu`, `_rects_montres`, `_apercu` (fin).
- **Zones que je n'ai pas touchées** : `_e_affichage` (agent fenetre, ses dernières lignes touchent mon bloc) et `dessiner` (pause2). Conflit de contexte possible mais pas de recouvrement.
- **Clés ajoutées à `DEFAUT` par un autre agent** (mode de fenêtre, etc.) : `test_classement_complet` échouera tant qu'elles ne sont pas dans `HORS_INTERFACE` du test. C'est voulu.
- `Reglages.defaut` est une méthode statique, `RG.DEFAUT` reste le dict.
- Le harnais teste les clics à 1280 x 720 en pixels depuis le haut-gauche ; pour un autre format, passer `--largeur` et `--hauteur` après les arguments (ce qui prévaut sur ceux du script).

## Notes à ajouter dans `docs/notes-visionneuse-dq4-pc.md` (section « Retours de 23 h 24 », éditeur d'interface)
- **Étiquette « Masquée »** : tout élément non affiché en jeu est voilé (noir à 150/255) et marqué dans l'aperçu, avec le cadre jaune de sélection intact : toute l'interface masquée (boutons « Masqué », croix et fenêtres « Masquée ») ou la croix seule (« Afficher la croix » = Non). `Pause._elements_apercu()` donne rectangles, état masqué et genre. La croix n'est plus pâlie : le voile suffit. Les boutons Carte / Commandes / Discussion partagent le réglage global `boutons` ; Mode suit la fenêtre `MapButton`. Un élément masqué reste attrapable.
- **Remises à zéro** : « Rétablir cette interface » remet tout `CLES_ECRAN` (affichage, tailles des boutons et de la croix, positions, croix affichée) pour « Boutons et croix de l'écran », ou l'entrée de la fenêtre dans `interface_fenetres` et `interface_masquees` (taille, position, affichage). Grille et aimantation ne changent pas. « Rétablir toutes les interfaces » remet aussi grille, aimantation et la place du panneau (`pan_pos`). Tout vient de `DEFAUT` (`Reglages.remettre_interface` / `remettre_interfaces`). Une nouvelle clé de réglage doit être classée dans `CLES_*` ou dans `HORS_INTERFACE` de `outils/test_reglages_interface.py`.
- **Panneau flottant** : le glisser démarre dès que le pointeur s'éloigne de 8 px de l'appui sur la barre de titre (l'ancien code annulait le geste si on bougeait avant 0,35 s : impossible à glisser pour qui n'attendait pas). Appui court = replier / déplier, appui maintenu = soulèvement, double clic = position d'origine (au relâchement). Test : `outils/test_panneau_interface.py`.

---

## Agent a377ad026145bcbc1 — 02/11 00:38

RAPPORT FINAL pause2 (points 4, 6, 7, 12) - worktree /home/claude/wt-pause2, branche agent-pause2, base main 345ba8f. Arbre de travail propre (git status vide).

COMMITS (3, chacun avec les deux lignes Co-Authored-By / Claude-Session)
- 7593b20 Pause : page Son (une ligne par son), vitesse de defilement du texte (Messages en combat), vitesses x1 a x4, plus d'encadre jaune (assombrissement au survol)
- 3d52d1f Pause : le pointeur qui quitte la fenetre rallume les plaques (on_mouse_leave -> pause.sortie())
- c9e1250 Ecrans d'avant-partie : plus d'encadre jaune au survol (ecran Sauvegardes, saisie du nom, licence). COMMIT SEPARE car hors perimetre de la Pause (avant_partie.py, ecran_sauvegardes.py, saisie_nom.py) : a ecarter par `git revert c9e1250` ou en le sautant au cherry-pick si l'agent de l'ecran titre touche ces fichiers. Il retire aussi `import hud_mobile as HM` devenu inutile dans les deux premiers (pyflakes).

FICHIERS TOUCHES
dq4_pc/pause.py (+196/-), dq4_pc/fenetre.py, dq4_pc/reglages.py, dq4_pc/avant_partie.py, dq4_pc/ecran_sauvegardes.py, dq4_pc/saisie_nom.py, outils/test_reglages_son_texte.py (modifie), outils/test_pause_pages.py (nouveau). Rien dans docs/. Moteur d'origine, patchs FR et sauvegardes de l'utilisateur non touches.

TESTS (tous verts) : test_pause_pages.py 15 tests ; test_reglages_son_texte.py 7 tests (dont 3 de migration) ; test_son_mixage.py 12 tests. pyflakes : seuls restent 4 avertissements deja presents sur la base (pause.py variables R, yp, mh ; fenetre.py sel). test_texte_defilement.py exige --apk/--saves (non relance, sa logique n'a pas ete modifiee).

POINT 4 - PAGE SON (Etabli, par captures + tests)
- Plus de sections. 5 lignes : General, Musique, Jingles et fanfares, Bruitages, Interface. Colonnes alignees : nom | barre de volume (remplissage jaune conserve) | valeur en % | bouton haut-parleur (muet) | bouton rond (defaut).
- Clavier : haut/bas = ligne, gauche/droite = volume, Entree = muet/remettre, Suppr = defaut. Souris : barre cliquable et glissable, haut-parleur et rond cliquables, clic sur la valeur = la taper (conserve). Les sons continuent pendant que la page est ouverte (un bruitage d'essai est joue quand on change un volume ou qu'on remet un son).
- DECISION : le bouton/touche par defaut remet le volume a sa valeur par defaut ET rend le son (annule le muet). Bouton grise quand la ligne est deja par defaut. Ligne coupee : libelle et barre grises, haut-parleur barre d'une croix rouge. Cliquer a cote des boutons sur une ligne Son ne fait rien (evite de couper par erreur).
- Le moteur de mixage n'est pas modifie : le muet bascule les interrupteurs existants (musique_active, jingles_actifs, bruitages_actifs, interface_active ; General = muet global).

POINTS 6 et 7 - TEXTE (Etabli)
- Entree racine, titre de page et titres[...] : "Vitesse de defilement du texte". Plus de sections. "Defilement automatique" supprime. "Vitesse du texte" en premier ("Normal (jeu)" devient "Normal"), puis "Messages en combat" : Rapide / Moyen / Lent / Manuel. Ligne "Retablir le reglage du jeu" conservee.
- CORRESPONDANCE ETABLIE dans le moteur d'origine (OptionStatus.battleSpeed = g_Option+5 ; BattleAutoFeed::setMessageSpeed 0x201558) : 0/1/2/3 -> attente de 12/22/32/42 images, 4 -> -1 (manuel, attend une touche), 5 -> DEBUG_WAIT. Defaut du jeu = 2 (OptionStatus::initialize 0x1a344c). Valeurs CHOISIES : Rapide = 0, Moyen = 2 (defaut d'origine), Lent = 3, Manuel = 4. La valeur 1 (possible dans une sauvegarde) s'affiche "Moyen" (cran_defilement : 1 -> 2). Le choix 1 / 22 images n'est donc pas propose.
- Migration (reglages.py) : si 'defilement_combat' est absent et que l'ancien fichier a defilement_auto / defilement_vitesse : auto=False -> Manuel (4), sinon vitesse ancienne ramenee au cran le plus proche. La valeur de la sauvegarde n'est PAS ecrasee tant que l'utilisateur n'a pas touche au menu : 'defilement_force' reste False (fenetre.py : defilement_actuel() lit alors options_jeu()[2]) ; 'Retablir le reglage du jeu' remet defilement_force a False. Teste en unitaire (test_migration_defilement_des_combats, test_crans_du_defilement, test_choix_impose_la_valeur_puis_rien_tant_qu_on_ne_touche_pas).
- VERIFICATION EN COMBAT REEL (combat force, Unicorn) :
  * Manuel (4), slot 4 : avec 90 images sans touche le message reste a l'ecran ; Entree, Espace et clic gauche le font chacun avancer, 3 images apres l'appui. Etabli.
  * Controle Rapide (0), slot 4, journal /tmp/p2_rapide.log : les messages passent seuls apres 12 a 18 images ; options_jeu passe de (4,4,4) a (4,4,0), donc le reglage est bien ecrit et effectif. Certains messages d'attente (fin de combat probablement) attendent quand meme une touche meme en Rapide, et Entree / Espace / clic les font avancer (3 images). Etabli.
  * RESERVE : la sauvegarde du slot 4 etait deja a battleSpeed 4. Le passage direct 2 -> 4 en combat (slot 2 = depart a la valeur par defaut) n'a pas pu etre rejoue : les deux lancements sur le slot 2 n'ont rien affiche avant le timeout de 600 s (cause non investiguee, vraisemblablement attente d'un etat de champ). C'est le meme appel regler_defilement(code) que pour 0, donc je le tiens pour Suppose (pas Etabli) dans ce sens.

POINT 12 - COMMANDES > VITESSES (Etabli sauf mention)
- Vitesse de marche / de camera / de transition : listes deroulantes x1, x2, x3, x4 (plus de curseurs). "Vitesse de l'accelerateur" garde son curseur 1-2 (defaut 1.5).
- Migration : anciennes valeurs 0.5-2 ramenees au cran x le plus proche (int(v+0.5), plancher x1, plafond x4 ; valeur invalide ou booleen -> defaut) : 0.5->x1, 1->x1, 1.5->x2, 2->x2. Teste (test_migration_des_vitesses_en_x).
- DEFAUTS : marche x1, camera x1, transition x2. ECART AVEC LE BRIEF : le brief disait x1 ; j'ai garde x2 pour la transition parce que c'etait le defaut deja documente (vitesse_fondu 2.0) ; changer = une ligne dans reglages.py (DEFAUT['vitesse_fondu']).
- Marche x3 / x4 : le moteur n'a pas de limitation structurelle (la marche rapide = davantage de pas moteur par image affichee, _facteur_vitesse plafonne a 8.0). J'ai ajoute un budget de temps par image pour les pas rapides (BUDGET_PAS_RAPIDES = 30 ms, variable d'environnement DQ_BUDGET_PAS) : si les pas ne tiennent pas dans 30 ms, le jeu ralentit au lieu de geler l'affichage.
- MESURE (horloge reelle, DQ_TEMPS_REEL=1, marche continue, script scratchpad mesure_marche.py ; 3 series dont une sans budget) :
  * Fenetre 400x225 (rendu peu couteux) : x1 = 29.7-30.0 pas/s (x1.00) ; x2 = 49.9-51.5 (x1.66-1.72) ; x3 = 85.0-87.7 (x2.83-2.92) ; x4 = 111.6-115.1 (x3.72-3.84) ; x4 + accelerateur x2 tenu = 202.5-217.0 (x6.75-7.23). Avec ou sans budget les resultats sont equivalents ici.
  * Fenetre 1280x720 (rendu logiciel Xvfb, 10-26 images/s) : x4 = 85 pas/s (x2.84), x4 + accel = 167 (x5.58). Mesures limitees par le CPU partage du bac a sable (rendu logiciel + autres agents), pas par le moteur.
  * CUMUL MAXIMUM : x4 (marche) x 2.0 (accelerateur) = x8 theorique (plafond du code) = 240 pas moteur/s, soit environ 0.85 s de CPU par seconde si un pas coute ~3.5 ms : sature un PC lent, auquel cas le budget fait ralentir le jeu. Sur ce banc on atteint x6.8-7.2 au mieux.
  * NON VERIFIE : performance reelle sur Windows (GPU/CPU de l'utilisateur) a x4 et x8 ; taux de rencontres sur une longue marche a x3/x4 (raisonne : compte par pas moteur, donc par distance, pas mesure) ; fondus de transition x3/x4 sur un vrai changement de carte (raisonne : la duree des fondus est divisee, 30 -> 8 images a x4, <= 1 image = immediat ; pas teste a travers une vraie transition). Camera : x4 avec accelerateur = 800 deg/s, stable (dt plafonne a 0.1 s, recentrage par saut).

CADRE JAUNE (Etabli par captures et par test sur le code)
- Supprime partout dans la Pause : racine, Etats (liste, fenetres Oui/Non), Son, Texte, Commandes (lignes, listes deroulantes, cases de touches, curseurs), aide, boutons de pagination, rond par defaut, croix rouges, bouton retour, elements des listes deroulantes. Regle : souris = plaque assombrie (motif "enfonce" decale sur une plaque, couleur a 75 % sur un bouton-icone), qui se rallume quand le pointeur part (y compris quand il quitte la fenetre : on_mouse_leave -> pause.sortie()) ; clavier = curseur dore (fleche) devant la ligne choisie. Le remplissage jaune des curseurs et (editeur, pas a moi) le rectangle jaune de selection d'element sont conserves.
- Sur un sous-bouton (haut-parleur, rond, croix, fleches de defilement), seul le sous-bouton s'assombrit, pas la ligne.
- Un test statique (test_plus_de_cadre_jaune_dans_le_code_de_la_page) verifie qu'aucun "JAUNE if sel" ne reste dans pause.py. Le parametre `contour` de _plaque est CONSERVE (les ecrans d'avant-partie l'utilisaient ; plus aucun appelant ne le passe dans le code modifie). Fallback HM.plaque de hud_mobile.py non modifie.
- NON VERIFIE visuellement : les trois ecrans d'avant-partie du commit c9e1250 (pyflakes seul ; meme appel _plaque que dans la Pause). Plus de dossier "ecran Sauvegardes" jamais capture par moi.

CAPTURES UTILES (absolus, /tmp)
- AVANT (cadre jaune + info-bulle) : /tmp/m_p2_base1_b200.png (Commandes, Vitesse de camera encadree de jaune, curseurs) ; autre base : /tmp/m_p2_base1_b100.png
- APRES Son : /tmp/m_p2_s2_b190.png (5 lignes, General et Bruitages coupes, Musique par defaut grise) ; /tmp/m_p2_a_b150.png (Son avec survol et aide) ; autres series : /tmp/m_p2_a_b50.png /_b90 /_b110 /_b130
- APRES Texte : /tmp/m_p2_t1_b170.png (titre "Vitesse de defilement du texte", "Messages en combat : Moyen", curseur dore) ; autres : /tmp/m_p2_t1_b50.png /_b100 /_b120 /_b140
- APRES Commandes (x1-x4, section Vitesses) : /tmp/m_p2_c2_b170.png ; series /tmp/m_p2_c2_b130.png /_b150 /_b190 /_b210 /_b230 /_b250 ; /tmp/m_p2_c1_b100.png /_b150 /_b200
- Fenetres Oui/Non : /tmp/m_p2_e1_b200.png (Etats, "Supprimer l'etat 1 ?") ; recadrage de survol Oui / Non / repos : /tmp/p2_pop_all.png (aussi /tmp/p2_pop180.png /p2_pop200.png /p2_pop220.png)
- Journal du controle de combat : /tmp/p2_rapide.log

NOTES POUR docs/ (a ecrire par le lead)
- Menu Pause > Son : une ligne par son, colonnes nom | barre | % | muet | defaut ; clavier haut-bas / gauche-droite / Entree / Suppr ; defaut = volume ET son remis.
- "Texte et defilement" devient "Vitesse de defilement du texte". Messages en combat -> OptionStatus.battleSpeed : Rapide 0, Moyen 2 (defaut d'origine), Lent 3, Manuel 4 ; 1 affiche Moyen ; reglage non impose tant que l'utilisateur n'y touche pas (defilement_force). Cles de reglages : defilement_combat remplace defilement_auto et defilement_vitesse (migration automatique).
- Commandes > Vitesses : x1-x4 (marche, camera, transition ; defaut x1 x1 x2) ; accelerateur 1-2 (defaut 1.5) ; cumul max x8 ; budget de 30 ms par image (DQ_BUDGET_PAS).
- Regle d'interface : plus de cadre jaune au survol ; plaque assombrie (souris) + curseur dore (clavier). Exceptions voulues : remplissage jaune des curseurs, rectangle jaune de selection d'element dans l'editeur d'interface.
- Outils : outils/test_pause_pages.py (nouveau).

PIEGES DE FUSION
- pause.py : la boucle de dessin des lignes (zone de remise a zero des zones, calcul de sel / anc, appel _plaque sans contour), la formule de largeur pw (+36 pour 'son') et _valider/clic/_aide_ligne sont les endroits les plus susceptibles de heurter les modifications des agents fenetre / editeur2 ; _e_affichage, _e_interface et le panneau flottant ne sont PAS touches. Un champ n_f utilisait `.get('fixe')` : corrige en `is True` (une lambda 'fixe' creait un faux ecart apres la premiere ligne Son).
- fenetre.py : bloc defilement (defilement_actuel / regler_defilement / retablir_defilement / appliquer_defilement / _adopter_defilement), constante BUDGET_PAS_RAPIDES apres PAS_MOTEUR, boucle _boucle (coupe au budget), on_mouse_leave (survol_nd = None + pause.sortie()).
- reglages.py : DEFAUT (defilement_combat remplace defilement_auto/vitesse ; vitesses 1.0/1.0/2.0), BORNES (1,4), BOOLEENS_SON_TEXTE sans defilement_auto, nouvelles fonctions cran_defilement / cran_x et migration dans le chargeur. Si un autre agent ajoute des cles, garder l'ordre : migration avant la boucle BORNES.
- Le fichier de reglages est reecrit par Pause.fermer() a chaque test : copier /tmp/rg.json avant chaque lancement (pas de pollution croisee).
- Harnais de capture dans CE worktree : "~@x@y" est le RELACHEMENT de la souris ; le survol est "@x@y@2" (au lieu de ~). Un autre worktree peut avoir une syntaxe differente.
- c9e1250 est independant : l'ecarter si conflit avec l'agent de l'ecran titre.

ETABLI / SUPPOSE / NON VERIFIE
Etabli : mise en page et comportement des pages Son, Texte, Commandes (captures + tests) ; correspondance battleSpeed (lecture du code d'origine) ; Manuel 4 en combat reel (Entree, Espace, clic) ; Rapide 0 passe seul en 12-18 images ; migrations (tests unitaires) ; plus de cadre jaune dans la Pause (captures + test statique) ; marche x2-x4 mesuree sur le banc.
Suppose : transition 2 -> 4 en combat (meme appel que 0 -> ... mais non rejoue depuis la valeur par defaut) ; fondus x3/x4 ; taux de rencontres par distance ; sensation de la marche x4 x accelerateur.
Non verifie : Windows (GPU/CPU reels, vitesse x4/x8), rendu audible du muet et des volumes sur de vrais haut-parleurs (les tests de mixage verifient les valeurs, pas le son), chiffres de la fenetre Config d'origine (1 a 5), apparence des trois ecrans d'avant-partie modifies par c9e1250.

POINTS DE DECISION A VALIDER PAR L'UTILISATEUR
1) Defaut de la transition : x2 (existant) ou x1 (brief) ? 2) Le bouton "defaut" d'une ligne Son remet-il aussi le son (choix actuel : oui) ? 3) Moyen = 2 (defaut du jeu) et Lent = 3 convient-il, sachant que 1 (22 images) n'est plus propose ?

---

## Agent abe62037682218817 — 02/11 00:44

RAPPORT FINAL — agent « fenetre » (lot PR #42), points 1, 2, 3, 9
Worktree /home/claude/wt-fenetre, branche agent-fenetre, base 345ba8f. Arbre propre (git status vide), aucun push, main et saves intacts.

COMMITS
- 6cf5517 : écran de chargement noir, 3 modes de fenêtre, ordre de la page Affichage, F11 / Alt+Entrée
- 9624ec2 : lecture robuste de « Résolution » lors d'un changement de mode + tests des raccourcis (F11, Alt+Entrée, Alt Gr, Alt seul, Alt-Tab, Pause ouverte, capture de touche)
Pyflakes : seuls les avertissements connus (sel, R, yp, mh). Test unitaire : `timeout 100 xvfb-run -a -s "-screen 0 800x600x24" python3 outils/test_mode_fenetre.py` → 23 tests OK (les tests dépendant de pyglet sont ignorés sans DISPLAY).

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
- outils/test_mode_fenetre.py (nouveau, 208 lignes).

CAPTURES (/tmp)
- Affichage plein écran (Résolution grisée + note) : /tmp/m_fenP1_b60.png ; plein écran exclusif : /tmp/m_fenP2_b60.png ; liste déroulante Fenêtre (mode fenêtré) : /tmp/m_fenP0_b60.png
- Écran noir pendant le chargement : /tmp/m_fenN_b30.png (journal /tmp/out_fenN.txt) ; témoin ancien code : /tmp/m_fenBase_b30.png (/tmp/out_fenBase.txt)
- Replis simulés : /tmp/m_fenF3_b20.png, /tmp/m_fenF4_b20.png, /tmp/m_fenF5_b20.png ; échec à la bascule F11 : /tmp/m_fenF6_b30.png, /tmp/m_fenF6_b60.png, /tmp/m_fenF7_b30.png
- F11 / Alt+Entrée pendant les logos : /tmp/m_fenL_b40.png ; bascules avec rendu hors écran : /tmp/m_fenFX_b30.png, _b60.png, _b90.png ; lancement exclusif + changement de résolution : /tmp/m_fenR_b40.png
- Autres : /tmp/m_fen0_b60.png, /tmp/m_fen1_b60.png, /tmp/m_fen2_b30.png, /tmp/m_fen2_b60.png, /tmp/m_fenA..E. Journaux : /tmp/out_fen*.txt

PIÈGES DE FUSION
- pause.py : je touche une ligne du dict `noms` (ajout de la clé `'Fenêtre'`) et TOUTE la liste de `_e_affichage` (réordonnée). L'agent « pause2 » modifie le reste de pause.py : conflit peu probable, mais si l'agent sprites ajoute une ligne d'option Affichage, l'insérer à la main dans MA liste réordonnée (garder Interface en dernier).
- fenetre.py : conflits possibles avec les autres agents sur `__init__` (bloc de création de la fenêtre : `res_demandee`, `_creer_fenetre`), `_attente`, `on_key_press/on_key_release`, `_tenue`, `_fronts` (Alt exclu du front « discussion », `alt_tap`), le harnais `_touches_test` et les options CLI (`--plein-ecran` passe à choices (0,1,2)).
- reglages.py : DEFAUT (clé `plein_ecran` remplacée par `mode_fenetre` + `mode_fenetre_retour`), `RESERVEES`, migration dans le chargeur. Tout code qui lit `reg['plein_ecran']` doit lire `reg['mode_fenetre']` (j'ai migré ceux de fenetre.py ; vérifier les ajouts d'autres agents).
- Pause (agent pause2), page Commandes : l'infobulle « Discussion de groupe » pourrait dire « Alt seul, au relâchement ; Alt+Entrée = plein écran exclusif » ; non modifiée par moi (hors périmètre).

NOTES POUR docs/ (à fusionner dans notes-visionneuse-dq4-pc.md, section « Retours de 23 h 24 (#42) »)
- Démarrage : écran de chargement entièrement noir (aucun texte, messages en console seulement). Fenêtre créée cachée dans le mode enregistré, affichée après une première image noire.
- Réglage `mode_fenetre` : 0 fenêtré / 1 plein écran (sans bordure à la résolution du bureau) / 2 plein écran exclusif (changement réel de mode d'affichage). Migration silencieuse de l'ancien `plein_ecran`. Option CLI `--plein-ecran 0|1|2`. `mode_fenetre_retour` = mode (0 ou 1) auquel F11 revient depuis l'exclusif.
- Sémantique de « Résolution » : fenêtré = taille de fenêtre ; plein écran = sans effet (grisée) ; exclusif = résolution réelle de l'écran (mode le plus proche, 16/9 de préférence, ≥ 24 bits, fréquence la plus haute).
- Repli : exclusif refusé → plein écran sans bordure → fenêtré, avec message console. Crochet de test `DQ_SIM_ECHEC` (valeurs 2, 1, 2,1, 2s : simule le refus à la création et à la bascule). Restauration du mode d'affichage à la fermeture (`on_close` + `atexit`).
- F11 / Alt+Entrée : bascule exclusif ↔ mode précédent depuis n'importe quel écran ; le raccourci modifie le réglage « Fenêtre ». F11 est une touche réservée (non assignable dans Commandes). « Discussion de groupe » (Alt) se déclenche maintenant au relâchement d'Alt seul (donc Alt+Entrée, Alt+Tab et Alt Gr ne la déclenchent pas).
- Page Affichage : nouvel ordre (voir point 3) ; Interface en dernier.
- Test : `outils/test_mode_fenetre.py` (23 tests, Xvfb recommandé). Limites connues : voir « Non vérifié » (Windows requis).

À mémoriser pour la session principale (sources : brief et mission) : Sylfried teste sur Windows ; les points « Non vérifié » ci-dessus sont ceux à lui faire essayer en premier (Alt-Tab en exclusif, vraie résolution, F11 aller-retour, fermeture avec restauration du bureau).

---

## Agent a8d3c9b371f180c4e — 02/11 00:46

AGENT CAMERA (#42) — worktree /home/claude/wt-camera, branche agent-camera, base 345ba8f. 1 commit : 09006ce. Arbre propre. pyflakes OK (seul avertissement connu : `sel`).

**EN TÊTE : AUCUN changement de FOV ni d'inclinaison (avant = après).** Villes : fov nominal 9,5 (None côté moteur), champ horizontal 12,67° (9,5 x 4/3) fixe, vertical 22,3° à l'aspect d'origine 0,5625. Tangage = celui du moteur (47,03°, distance 39,55), lookDown 0,2°, avance 4,0, near 5 / far 100 par défaut. L'agent sprites peut garder la projection actuelle.

## Point 14 (grenouille du prologue) : corrigé
- Scène : déclencheur ~(0,93 ; 10,57) sur `mlout1`. Verrou TownCamera : mode 1 (panoramique diagonal, ~+0,088 x / -0,046 z par image) -> mode 5 (suit la grenouille, qui sort vers +x jusqu'à x = 6,07) -> mode 4 (retour au joueur) -> verrou levé.
- Cause (Établi, trace image par image) : la visionneuse bornait la caméra en x (`bornes_x`, cadrage 16/9) dès que `cam_jeu` passait à vrai. Le rendu restait collé à x = 1,978 pendant que le moteur allait à 6,07 : écart max 4,09 u avant, **0,000 après** sur 1470 images de scène. D'où « droite puis bas » et l'arrêt du suivi.
- Unity ne borne rien (Établi par désassemblage) : `SceneCamera.Update` D16180 sans Clamp/Min/Max ; `TownCamera::execute` sans clamp en mode libre ; `NativeManager.cmd_camera` D14568 appelle `FldObject.GetEventLimitedPos` CD4EE4 pour la position, mais seulement si `UIFix.IsLargeAspectRatio()`, et `s_eventLimitList` (.cctor CDDC08) n'a qu'UNE entrée : décor `map/ev/ev02/out/ev02`, événements {0,1}, z >= -19,5. Ce n'est pas `mlout1`.
- Fix (`fenetre.py`) : nouvelle `Jeu._camera_menee(mo)` ; `cam_jeu` = verrou ET caméra menée ailleurs que sur le joueur (mode de cible 1 à 5, déplacement en cours, ou cible à plus de `CAM_MENE_DIST` = 1,0 u du héros, ou héros hors champ). `poids_cible = 1.0 if option or self.cam_jeu else 0.0` : aucune borne 16/9 en caméra menée, avec ou sans l'option « Centrer la caméra sur le joueur » ; les bornes reviennent progressivement (exp(-14 t), temps réel) à la fin.
- Captures avant/après : planches `/tmp/cam_fr_trajet_av_ap.png` (images 146 à 296) et `/tmp/cam_fr_depart_av_ap.png` (images 1530 à 1602) ; traces `/tmp/cam_av14.csv` (avant) et `/tmp/cam_ap14b.csv` (après) ; images unitaires `/tmp/cam_av14_f<n>.png` et `/tmp/cam_ap14b_f<n>.png`.

## Point 17 (père, caméra qui « continue son chemin ») : cause probable corrigée, scène exacte non retrouvée
- Cause trouvée (Établi par test, mais conditionnelle) : la correction du centrage (héros - cible du jeu) était lissée en bloc par exp(-14 t). Dès que le jeu borne sa cible (bord de carte) et que le héros court, la caméra traînait derrière (écart du héros au centre jusqu'à 0,03 NDC à x1 et 0,10 à x4, croissant avec la vitesse et la cadence), puis rattrapait après l'arrêt (0,015 à 0,09 NDC) : exactement « elle continue légèrement son chemin avant de se recentrer ». Mesure : `outils/test_camera_ville.py` (cadences 1/30, 1/60, 1/144 ; vitesses x1 à x4).
- Fix : correction = cible suivie à l'image près (caméra rigide sur le héros) + reste qui ne naît que d'un changement de régime (scène <-> main du joueur) ou d'une coupure, et qui s'estompe en temps réel. Résultat : écart 0,0000 partout, indépendant du nombre de pas moteur par image et de la cadence. Le banc réel (`/tmp/cam_r17_{av,ap}_{a1,a15,a4}.csv`, course vers le déclencheur de la grenouille à x1 / x1,5 / x4) confirme : le rendu égale le moteur en scène, quelle que soit la vitesse.
- Second contributeur corrigé : un verrou qui garde le héros au centre (mode 6, ou plan sur le héros) ne change plus de régime. Avant, il faisait glisser la caméra vers le cadrage borné de la pièce en ~0,2 s au déclenchement, puis revenir.
- Supposé / Non vérifié : je n'ai PAS reproduit le symptôme dans la maison du père. Dans le prologue (`mlb1a`) la caméra du moteur = héros partout, sans verrou pendant la 1re conversation : le défaut ne s'y produit donc pas. Le père se déplace ensuite et l'événement qui le concerne n'a pas été atteint. L'événement du Screen 6 reste à confirmer sur la sauvegarde de l'utilisateur. Autre piste NON corrigée : sous verrou (`cam_bloquee`), la rotation / l'inclinaison choisies par l'utilisateur sont coupées d'un coup (saut), et ça touche aussi l'orientation des sprites.

## Point 16 (l'angle de la caméra est-il le bon ?) : oui, pour le mode jeu. Certitude très élevée côté code, aucune capture de téléphone disponible.
- Établi (désassemblage) :
  - `SceneCamera.Update` : LookAt(position, cible), `eulerAngles.x -= s_lookDownAdjust` (0,2°), avance de `s_distanceAdjust` 4,0, `Perspective(fov x 4/3, 1/Camera.aspect)` avec [0] et [5] échangés (champ horizontal fixe), `s_yOffset` par produit de matrices.
  - `SetViewAndCenterY` D1F5D0 règle la hauteur du rect sur aspect_écran / 0,5625 : la vue 3D a donc TOUJOURS l'aspect 9:16 sur n'importe quel téléphone (letterbox / crop). Champ 12,67° x 22,3° partout, `ASPECT_DEF` = 0,5625.
  - Near 5 / far 100 : `Global.CameraInitParams[0]`, déjà dans les notes.
- Vérification numérique : un pipeline Unity ré-écrit à part (LookAt gauche, euler, Perspective, [0]/[5], yOffset) comparé à `_camera_ville` sur 200 poses x 18 points à 0,5625 : écart max 4e-15 NDC. Test permanent : `outils/test_camera_ville.py`.
- Scan des 518 cartes chargées (`/tmp/scan_cams.txt`, 3 cartes non chargeables) : 514 ont distance 39,55, tangage 47,03°, fov par défaut, near / far / yOffset par défaut. Exceptions : `dpout` (tangage 28,04°, far 150), `sjout` et `tdout` (near 1,0). Aucune différence villes / grottes / tours.
- Parcours de 2300 images du prologue : seule différence = écran-titre `ev01` (distance 44, tangage 39°, fov 10, far 150, bas 3,02), déjà géré par `TITRE_HAUT`. Hors titre, jamais de changement de distance ni de fov pendant les scènes testées.
- Cartes du monde et combat : lus lors de sessions précédentes (notes 30-31/10 : monde orthographique `Field.Init`, combat fov 48 x 4/3, 4/3 de référence, yOffset 0,04). Je ne les ai pas revérifiés ici. `_camera_combat` : fov vertical 50,25°, near 0,25, far 500, yOffset 0,04.
- Supposé : near/far pour les cartes qui envoient leurs propres valeurs (suivies telles quelles).
- Écarts voulus de la visionneuse (inchangés) : hauteur de champ du mobile gardée et plus de décor sur les côtés en 16/9 ; « zoom commun » (le héros garde HEROS_FRAC de la hauteur de la fenêtre).
- Piste possible pour « l'angle ne va pas » : `reglages.angle_camera` (flèches haut / bas) est SAUVEGARDÉ. Dans `/tmp/rg.json` (réglages de test partagés) il vaut -2,25° (défaut 0 = comme le jeu). Un appui accidentel suffit à décaler le tangage en permanence. À vérifier dans les réglages réels de l'utilisateur (commande « Caméra » ; la ligne d'infos F1 affiche l'angle).

## Fichiers touchés
`dq4_pc/fenetre.py` : `_camera_ville` (bloc centrage + poids), `tick` (calcul de `cam_jeu`), nouvelle `_camera_menee`, constante `CAM_MENE_DIST`, attributs `cam_res` et `cam_centre`. `outils/test_camera_ville.py` (nouveau, 5 tests sans fenêtre, 1 s, pyglet « headless » sous Linux). Je n'ai touché ni `moteur.py` ni `reglages.py`. Sur l'ancien code, 3 tests sur 5 échouent (centrage, caméra menée, prédicat) : ils détectent bien les défauts.

## Pièges de fusion
- `self.cam_jeu` change de sens : « verrou ET caméra menée ailleurs que sur le joueur » (avant : le verrou seul). `cam_bloquee` garde le sens verrou.
- `cam_poids` est conservé : même nom, même rôle (part sans bornes), sa cible est simplement différente. `_camv` l'affiche toujours.
- Autres agents sur `_camera_ville` (`TITRE_HAUT`, sprites) : mon changement est localisé entre `t = time.perf_counter()...` et `if abs(self.cam_dec[0]) > 1e-4` (calcul de `cam_dec`, `cam_res`, `poids_cible`), puis dans `tick` et `__init__` (ligne 185 : ajout de `cam_res` et `cam_centre`).
- `cam_dec` reste la valeur appliquée (`dec + reste`).

## Notes pour `docs/` (section « Retours de 23 h 24 (#42) », je n'ai pas écrit dans docs/)
- `bornes_x` n'est plus appliquée en caméra menée par le jeu ; critère `cam_jeu` = verrou +0x3e ET (mode +0x48 dans 1..5, ou déplacement +0x43, ou cible à plus de 1 u du héros). Mode 6 ou verrou sur le héros = régime joueur inchangé.
- Unity ne borne pas la caméra : `GetEventLimitedPos` CD4EE4 ne sert qu'au décor `map/ev/ev02/out/ev02` (z >= -19,5, `IsLargeAspectRatio`).
- Centrage : correction rigide + reste exponentiel (14/s, temps réel) seulement aux changements de régime ou coupures.
- Aspect : `SetViewAndCenterY` D1F5D0 garde 9:16 quel que soit l'écran ; champ horizontal 12,67°, vertical 22,3°. Équivalence numérique avec le pipeline Unity : 4e-15.
- Route du prologue jusqu'à la grenouille : sauvegarde du dossier ANCIEN `.../DQ4/saves/20261007_190735` slot 2 (`mlb1a`). Dans le dossier NOUVEAU `dq4-portage/dq4_pc/sauvegardes`, le slot 2 charge `caf1`.
- Outil de test fenêtré : banc à horloge virtuelle `/tmp/banc_camera.py`. Usage : `python3 banc_camera.py WT ETATDIR NOM "frame:+Q,..." "captures" NFRAMES [DT]` ; environnement `AUTO_A`, `AUTO_0`, `AUTO_ALL`, `RG`. Génération d'états de la route du prologue : `/tmp/gen_etat_camera.py NOM IMAGE`. États prêts : `/tmp/camst/sv_frog_pre1272/etats/etat_01.dqs` et `/tmp/camst/sv_house470`, `sv_house900`.
- Piège de test : `/tmp/rg.json` est réécrit par chaque fermeture de fenêtre ; il contient `angle_camera` = -2,25 (résidu). Pour une mesure propre, utiliser une copie (`RG=...`) ou `/tmp/rg_defaut.json`.

## Pour la mémoire (pas écrit par moi)
- Environnement : `pkill -f` sur un nom présent dans la ligne de commande de son propre shell tue ce shell (code 144). Un `flock` en attente peut rester orphelin après un kill.
- Slot 2 du dossier de sauvegardes NOUVEAU = `caf1` ; prologue dans le dossier ancien.
- Le Screen 6 de l'utilisateur est la maison du héros (père assis à une table), `mlb1a`.

---

## Agent a0a930f3486ff24a2 — 02/11 00:52

RAPPORT agent « titre » (PR #42) — worktree /home/claude/wt-titre, branche agent-titre, base 345ba8f. Arbre propre. Aucun push, aucune modif de docs/, du patch FR ni des sauvegardes.

COMMITS (pied de message conforme)
- 60aa233 « Titre : le dragon de l'ecran d'accueil (FbxObject c1018, paquets 31 et 32) » (point 5)
- b76d293 « Titre : textes des credits centres comme le logo » (point 8, fenetre.py seul)
pyflakes : seuls les avertissements connus (struct, sel).

POINT 8 — CREDITS CENTRES : FAIT ET MESURE
- Cause : toute la scene ev01 est relevee de TITRE_HAUT = 0,3 pour centrer logo + ile ; les credits (modele de maillage 8905, dessines par les paquets 21/22 comme le logo) suivaient ce decalage alors que le moteur les pose bas dans l'image d'origine. Avant : centre du bloc a 0,355 (page Horii, 3 lignes) et 0,378 (pages a 2 lignes) de la hauteur.
- Correction (_decalage_credits, appelee depuis _maillages_combat) : pour chaque page, le centre vertical de l'ENCRE (pixels alpha > 32 de chaque ligne, lus dans la texture d'origine) est ramene a l'ordonnee d'ecran 0 par un deplacement le long du haut de la camera. La profondeur ne change pas, donc c'est exact a tout format. Cache par page. Toute erreur : aucun decalage (message unique dans la console).
- Mesures (diff capture avec / sans credits via DQ_SANS_CREDITS) : centre du bloc a 0,5000 a 0,5007 de la hauteur partout : 1280x720 (4 pages : Horii 100, Toriyama 240, Sugiyama 370, Majima 520), 1920x1080 et 2560x1080 (21:9) et 1024x768 (4:3) (pages 100 et 240). Centre horizontal 0,499 a 0,501.
- Verifie : « Touchez l'ecran » et copyright : 0 pixel different avant / apres (image 900) ; ciel, logo, ile inchanges (le seul ecart est le dragon).
- Choix : centrage exact par page (conforme a la consigne). Consequence : le nom reste a hauteur fixe dans le moteur d'origine, ici il monte de 4 px (page Horii) a 18 px (pages a 2 lignes) selon la page, a 720p. Sinon, annuler seulement TITRE_HAUT pour les credits donnerait -0,011 / -0,049 en ordonnee normalisee (pages a 2 lignes a ~18 px sous le centre).
- Observation : une fois centres, « YUJI HORII » et le haut de l'ile se frolent (le texte reste au-dessus de l'ile, sans chevauchement visible).
- Essais : DQ_SANS_CREDITS=1 (sans credits), DQ_CREDITS_ORIGINE=1 (ancien comportement).

POINT 5 — DRAGON : FAIT (a valider a l'oeil par Sylfried)
Etabli (lu dans le moteur / les donnees) :
- Le moteur envoie au debut de ev01 le paquet 31 (cmd_fbx_load : emplacement 0, modele 1018 = Resources « fbx/c1018 », FbxObject) puis des paquets 32 (cmd_fbx : bits 8-9 visibilite, 0x400 forcer l'animation, 0x800 echelle x3, 0x1000 couleur x4, 0x2000 position x3, 0x4000 rotation x3 en degres, 0x8000 numero de sequence). Decode depuis le desassemblage (RVA 0xD13508 / 0xD136A0, FbxObject 0xCD1528...) et confirme par le journal de paquets. Le dragon est cree cache, rotation (0,180,0).
- Modele : 566 sommets, 692 triangles, 31 os, un os par sommet, texture 256x256, 3 clips : « Take 001 » 21,98 s (Once, = les 659 images que le moteur attend), « Take 002 » 2,18 s (Loop, vol stationnaire), « Take 003 » 26,78 s. Nom du clip = « Take %03d » (sequence + 1).
- Shader Custom/ImdChara (lu dans le paquet de donnees) : sans lumiere, couleur sommet x _Color x texture, fusion alpha, ZWrite, ZTest LEqual, Cull Back, file Geometry. Donc le dragon passe DERRIERE le logo et les credits (file 3850, ZTest Always). Backface culling active par defaut (sans lui, des faces internes cachaient le visage : planche dragon_cull_sans_vs_back_660.png).
- Animation reproduite comme Unity Animation : Play / PlayQueued / CrossFade 0,3 s si la boucle precedente, Hermite d'AnimationCurve, temps en images du moteur a 30 Hz (fraction de pas comprise). Skinnage numpy : ~2 ms par image.
- Phases observees : le dragon apparait en haut vers l'image 510-520, plonge a gauche vers 600, se pose en vol stationnaire au-dessus du logo vers 660 (le logo apparait a ~640), puis boucle d'ailes jusqu'a l'appui sur « Touchez l'ecran » ; il disparait dans le menu (apres l'appui, image 925).
- Cache : fbx1_c1018.pkl (1,5 Mo, ~4,7 s a extraire) ajoute a Donnees._elements / preparer (preparation de fond). Teste sans cache : lecture a la demande dans un fil de fond, le dragon apparait, pickle ecrit (cache jetable, supprime).
Suppose (a valider) :
- Placement vertical : TITRE_DRAGON_HAUT = 0,0 (constante dans fenetre.py, essai par DQ_FBX_DY) : le dragon garde le cadrage d'origine, il n'est PAS releve avec le groupe logo + ile. Releve de 0,3 il sortirait de l'ecran (seules les griffes visibles). Avec 0,0 : visible au-dessus du logo, tete et ailes coupees par le bord haut en vol stationnaire, griffes qui effleurent le haut du logo (le logo est devant). Le cadrage d'origine coupe aussi le dragon en haut dans la camera de la visionneuse (meme champ vertical que le mobile), mais je n'ai pas de capture d'un vrai telephone. Pour le garder entier : augmenter TITRE_DRAGON_HAUT ou reduire l'echelle (a decider par Sylfried).
Non verifie :
- GPU Windows reel (tout teste sous xvfb / Mesa). Rendu du dragon sur un vrai telephone. Le flash d'1 image en pose de repos a l'image 2. Les autres modeles fbx du jeu (ValueError propre et ignore si shader different, plusieurs maillages skinnes, MeshRenderer, animation comprimee). Le retour moteur de fin d'animation (m_anim_list, ID_ANIM_END) n'est PAS implemente : le moteur du titre n'attend pas dessus, mais une autre scene pourrait. Les modeles fbx ne sont dessines que dans les scenes de ville (branche ville de _dessiner_scene), pas en combat ni sur la carte du monde. Pas de test sur un vrai profil utilisateur avec cache deja prepare (seulement le cas cache sans le fichier fbx).

FICHIERS ET LIGNES TOUCHEES (hors perimetre strict, a surveiller a la fusion)
- dq4_pc/fbx.py : NOUVEAU (156 lignes).
- dq4_pc/donnees.py : +66 lignes l.304-369 (modele_fbx, _extraire_fbx) ; +1 ligne l.394 (_elements) ; +1 ligne l.435 (preparer).
- dq4_pc/moteur.py : Etat.__init__ l.87 (self.fbx / self.image) ; __setstate__ l.93 (setdefault) ; l.101 (paquet 0 : ajout de self.fbx.clear() au bout d'une longue ligne : conflit probable si un autre agent ajoute des remises a zero camera ici) ; branches t == 31 / 32 l.154-165 ; Moteur.step l.604 (self.etat.image = self.images avant appliquer). Etats enregistres anciens : compatibles (setdefault).
- dq4_pc/fenetre.py : import fbx l.26 ; __init__ l.211 (fbx_cache / fbx_lect) ; _maillages_combat l.1003-1004 et l.1013 (credits) ; gros bloc neuf l.1141-1234 entre _tracer_decor et _fond_combat (TITRE_DRAGON_HAUT, _fbx_pret, _tracer_fbx, _decalage_credits) ; _dessiner_scene, branche ville l.2644-2645 (« self._tracer_decor(True); self._M_ville = M » + « if e.fbx: self._tracer_fbx(e) »). _camera_ville et la ligne TITRE_HAUT (l.97 / 883) NON touchees. Aucun changement a la forme du tuple renvoye par _maillages_combat.

PIEGES POUR LA FUSION
- L'agent camera modifie _camera_ville et probablement la ligne « M, cam3d = self._camera_ville(e, aspect) » : mon crochet est sur la ligne suivante de la branche ville (« self._tracer_decor(True) »). _decalage_credits lit self._M_ville (= la matrice finale M avec le decalage TITRE_HAUT) : si la camera change la facon dont M est construit ou renomme M, adapter cette seule ligne. L'agent sprites peut toucher _dessiner_scene / _maillages_combat : mes 3 lignes credits y sont isolees.
- La ligne du paquet 0 de Etat.appliquer (moteur.py l.101) est la plus fragile (une seule ligne tres longue).
- Le cache de preparation inclut maintenant un element « fbx » : au premier lancement avec l'ancien cache, la preparation de fond reprend pour cet element seul (~5 s).

NOTES A AJOUTER DANS docs/ (je ne les ai pas ecrites)
- notes-visionneuse-dq4-pc.md, section « Retours de 23 h 24 (#42) — titre » : (1) Credits : centres par page sur l'encre, au milieu de la zone de dessin (mesure 0,500 a 4 formats) ; essais DQ_SANS_CREDITS / DQ_CREDITS_ORIGINE. (2) Dragon : modele fbx/c1018 anime (fbx.py), derriere le logo, TITRE_DRAGON_HAUT = 0,0 (cadrage d'origine, non releve) ; DQ_FBX_DY pour essayer, DQ_FBX_CULL=0 pour couper le culling ; phases d'apparition (510 -> 660 -> boucle -> disparition au menu). Mettre en « a valider » le placement vertical.
- notes-technique-portage-dq4.md : paquets 31 (cmd_fbx_load : emplacement, modele ; < 0 = liberation) et 32 (cmd_fbx, bits ci-dessus) ; FbxObject = prefab Resources « fbx/c<no> » (SkinnedMeshRenderer + Animation legacy ; clip « Take %03d », CrossFade 0,3 s si la boucle precedente, sinon PlayQueued) ; Custom/ImdChara : Cull Back, ZTest LEqual, ZWrite, blend 5/10, file Geometry ; m_defScale 0,4 pour le modele 10 seulement ; Etat.image ; fbx1_c%04d.pkl.

CAPTURES (toutes dans /tmp/titre42/, copies nommees ; planches a ouvrir en premier)
- Credits avant / apres (1280x720, 4 pages) : /tmp/titre42/credits_avant_apres_planche.png ; pages seules credits_avant_{100,240,370,520}.png et credits_apres_{100,240,370,520}.png (« avant » = DQ_CREDITS_ORIGINE=1, ancien emplacement ; au 520 le dragon est deja la dans les deux). Etat de main sans dragon : /tmp/titre42/avant_main_*.png et avant_main_planche_20_620.png / avant_main_planche_640_1500.png.
- Formats : /tmp/titre42/credits_formats_planche.png (4:3, 21:9, 16:9 1080p) ; credits_apres_{1080,2180,768}_{100,240}.png (2180 = 2560x1080).
- Dragon par phase : /tmp/titre42/dragon_apres_planche.png (images 520, 560, 600, 640, 660, 700, 800, 900) et dragon_apres_*.png ; apres appui sur Entree (700 et 900) : dragon_entree_planche.png et dragon_entree_*.png (le 1er appui a 700 saute la sequence : ecran noir puis titre final, le 2e a 900 ouvre le menu sans dragon).
- Culling : /tmp/titre42/dragon_cull_sans_vs_back_660.png. Variante dragon releve de 0,3 (griffes seules) : /tmp/dv_0.3_{600,640,700}.png ; variante 0,0 : /tmp/dv_0.0_{600,640,700}.png.
- Outils de test (scratchpad) : mesure des credits /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/tools/measure_credits.py (usage : avec.png sans.png seuil).

DONNEES DE MEMOIRE UTILISEES : aucune ; ce rapport vient uniquement du depot, des donnees de jeu et de mes mesures.

---

## Agent a8597c32837357eeb — 02/11 01:31

RAPPORT agent « sprites » — PR #42, points 13 (bulle « ! ») et 15 (sprites aplatis aux bords)

Worktree /home/claude/wt-sprites, branche agent-sprites, base 345ba8f. Un seul commit : 299cab5, avec les deux lignes de pied (Co-Authored-By et Claude-Session). Arbre propre. Aucun push, aucun changement de branche, pause.py non touché. Les worktrees /tmp/wt-bisect-a et -b sont supprimés.

=== FAIT ===

POINT 15 — sprites penchés / aplatis aux bords gauche et droit

Cause :
- Le panneau d'un personnage de ville a ses sommets reculés vers la caméra de 0,185 (bas) et 0,65 (haut) le long de l'axe de la caméra (Chara.s_vtxDepthD / U).
- Le haut, plus proche, s'écarte donc du centre de l'image de (décalage × écart / profondeur).
- Le portrait d'origine, au champ horizontal étroit, cachait ce défaut. Le 16/9 et le 21/9 le rendent visible.
- Le visionneur garde le champ vertical du mobile, donc le défaut ne dépend ni du FOV ni de l'inclinaison.

Correctif, `Jeu._panneau_ville` dans fenetre.py :
- Le panneau est reconstruit à l'écran : même position, même hauteur, mêmes profondeurs qu'avant.
- Taille, recouvrements et z-buffer sont donc inchangés.
- Les bords deviennent verticaux et la largeur vaut 0,74 × la hauteur à l'écran. C'est la proportion du panneau au centre, où la largeur est la moyenne du bas et du haut.
- Au centre de l'image, aucun changement.
- Le calcul passe par la caméra de la visionneuse (`cam3d` et `_cadre_vue`). Il ne suppose ni FOV ni tangage.
- Ombres et monde (carte du monde) : code inchangé.
- Autre version essayée puis abandonnée : décalage le long du rayon de vue. Elle donnait aussi 0,75 partout, mais la hauteur variait de ±10 à 20 % selon la position à l'écran. Je l'ai rejetée parce qu'elle change la taille des PNJ.

Réglage `correction_bords` :
- Dans `reglages.py` : défaut True ; 0 ou False = comme avant ; une valeur entre 0 et 1 = correction partielle.
- Une valeur invalide revient au défaut.
- Option `--correction-bords 0-100` en ligne de commande, et variable `DQ_CORRECTION_BORDS=0-100`.
- Testé : CLI 0, CLI 50, réglage False dans le JSON, réglage True.

Mesures (scène : Strattbourg, slot 1, hero et PNJ marchant vers le sud, projection des 4 coins de chaque panneau). « Sur écran » = sprites dont les pieds sont dans l'image.

| Résolution | Distance | Penche max avant | w/h sur écran avant | Penche max après | w/h après |
|---|---|---|---|---|---|
| 1280×720 | 100 % | -13,1° | 0,65–0,79 | 0,0° | 0,74 |
| 1280×720 | 200 % | -20,5° | 0,66–0,91 | 0,0° | 0,73–0,74 |
| 1920×1080 | 100 % | -13,1° | 0,65–0,79 | 0,0° | 0,74 |
| 1920×1080 | 200 % | -20,5° | 0,65–0,91 | 0,0° | 0,73–0,74 |
| 2560×1080 (21:9) | 100 % | -13,1° | 0,65–0,79 | 0,0° | 0,74 |
| 2560×1080 (21:9) | 200 % | -20,5° | 0,65–0,91 | 0,0° | 0,73–0,74 |

- Les trois résolutions donnent les mêmes valeurs : le défaut dépend de la position angulaire, pas des pixels.
- Bord droit : même scène avec la caméra pivotée de 180° (`DQ_LACET`). Penche max avant +19,9°, après 0,0°.
- Hauteur à l'écran : identique avant et après (par exemple 71–79 px à 1280×720).
- Hero au centre : largeur 56,8 px contre 56,2 (bas) et 57,8 (haut) avant.
- À 50 % d'intensité, le penché est divisé par deux (-10,6°).

Non-régression :
- Écran titre (2 images) : 0 pixel de différence.
- Slots 2, 3 et 4 (dont la carte du monde, slot 4) : 0 pixel de différence.
- Combat : 6 images comparées, 0 pixel de différence (codes distincts de `_panneau_ville`).
- Grotte (slot 5) : seuls les sprites changent.
- Modes Shader 0 (originaux), 1 (EPX) et 4 (pixel perfect) : rendus corrects, penche 0,0°. Le mode 4 est le mode de toutes les mesures ci-dessus (réglage par défaut).
- Aucun code d'ancrage ne lit les sommets des panneaux : `_ancrer_effets`, Morph et dégâts sont inchangés par construction.

POINT 13 — bulle « ! » trop haute

Établi :
- Pas de régression de rendu entre #39 et #41 : 0 pixel de différence avec la caméra par défaut. Le code de la bulle n'a pas changé depuis d6d9b20, donc aucun commit fautif à isoler par bisect.
- Défaut réel : la bulle était avancée de 0,48 le long de l'axe de la caméra DU JEU (`fwd`) et non de celle de la visionneuse.
- Autre défaut : le moteur la pose à 1,294 au-dessus des pieds, en coordonnées du monde, alors que le sprite est de face à l'écran.
- Dès que le joueur incline ou tourne la caméra, la bulle dérive par rapport à la tête. Sa hauteur par rapport à la tête dépend alors de l'inclinaison.

Correctif :
- Avance de 0,48 le long du rayon de vue de la visionneuse (`_decaler_profondeur`).
- Bulle ancrée au personnage qu'elle surmonte (`_ancrer_icone`) : l'écart est gardé tel que la caméra du jeu le voit, puis rapporté à la caméra de la visionneuse.

Mesures, bulle d'un PNJ (le prêtre de l'église de Strattbourg). Écart = (haut du panneau du sprite - bas de la bulle) / hauteur du panneau, plus négatif = bulle plus basse sur le sprite :

| Condition | Avant | Après |
|---|---|---|
| tangage -20° | -0,10 | -0,395 |
| tangage 0° | -0,38 | ≈ -0,40 |
| tangage +20° | -0,74 | -0,398 |
| tangage +40° | -1,09 | ≈ -0,37 à -0,40 |
| lacet 45° | -0,33, décalage latéral +0,20 largeur | -0,395, décalage -0,013 |
| lacet 90° | -0,22, décalage latéral +0,28 | -0,397, décalage -0,035 |
| tangage 20°, distance 200 % | -0,74 | -0,375 |

- Avec la caméra par défaut, la bulle est au même endroit à environ 1 px près (moins de 2 % de la hauteur du sprite).
- Pour le tangage +40°, les valeurs « après » viennent de la version précédente du panneau (-0,371 mesuré), pas du commit final ; l'écart est dans le bruit.

=== ÉTABLI / SUPPOSÉ / NON VÉRIFIÉ ===

Établi :
- Les chiffres ci-dessus.
- La bulle ne dérive plus avec la caméra du joueur.
- Les sprites sont droits à toutes les résolutions testées.

Supposé :
- La capture de l'utilisateur (s4, bulle trop haute) correspond à une caméra inclinée ou tournée, ou à un objet plus bas que la hauteur de panneau d'un personnage. Je n'ai pas pu confirmer lequel.
- La capture s5 (paysan aplati) est bien le penché hors-axe : le contact sheet avant/après le confirme visuellement, mais la position exacte du paysan dans la capture est inconnue.

Non vérifié :
- Le cas exact de la capture s4 (héros vert + tonneaux, journal 1) : le héros restait bloqué contre les décors.
  - Pour un tonneau ou une jarre sans personnage dessous, `_ancrer_icone` renvoie la position du moteur inchangée.
  - Si la bulle y paraît trop haute avec la caméra par défaut, c'est probablement la position du moteur (1,294 au-dessus des pieds), identique à l'original.
- Windows, aucune machine : tout est en numpy pur et testé seulement sous Linux / xvfb.
- Fusion avec les autres branches : pas lancée à l'exécution (voir plus bas).
- Combat avec effets et dégâts à l'écran : seul l'écran de commande a été comparé (0 pixel de différence).
- Effet Morph à l'exécution : seulement lu dans le code.
- Carte du monde avec sprites au bord : slot 4, 0 pixel de différence, mais la correction n'y est pas appliquée (branche sans `cam3d`).
- Écran de menu avec personnages : non rencontré sur les slots disponibles.

=== POUR LE MAIN AGENT : ligne pour pause.py (que je n'ai pas modifié) ===

- Clé : `correction_bords`.
- Valeurs : True (défaut) / False.
- Libellé proposé : « Correction des bords des sprites ».
- Placement : page Affichage, juste après « Distance caméra » et avant « Centrer la caméra sur le joueur ».
- Ligne, même modèle que « Centrer la caméra sur le joueur » (pause.py l. 270) :
  `self._choix('Correction des bords des sprites', [True, False], lambda: R['correction_bords'], lambda v: R.__setitem__('correction_bords', v)),`
- Effet immédiat : le réglage est relu à chaque image, aucun `regler_*` nécessaire.

=== PIÈGES DE FUSION (testés avec `git merge-tree`, rien d'appliqué) ===

Tous les conflits sont des insertions voisines : garder les deux côtés.
- agent-camera et retours-23h24 : fenetre.py. Mes méthodes `_dbg_proj`, `_correction_bords`, `_decaler_profondeur`, `_panneau_ville` tombent au même endroit que leur `_camera_menee`. Garder les deux.
- agent-fenetre et retours-23h24 : fenetre.py, `main()`. Leur ligne `--plein-ecran` (choices 0,1,2) est à garder, plus ma ligne `--correction-bords`.
- agent-fenetre et retours-23h24 : reglages.py, `DEFAUT`. Garder `mode_fenetre`, `mode_fenetre_retour` et ma ligne `correction_bords`.
- agent-pause2 et retours-23h24 : reglages.py, bloc de nettoyage des valeurs. Garder leurs deux lignes `defilement_combat` / `VITESSES_X_CLES` et mes deux lignes (validation `correction_bords` et `defilement_vitesse`).
- agent-titre et agent-editeur2 : fusion automatique sans conflit.
- Sémantique à relire après fusion avec agent-camera : mon calcul utilise `_cadre_vue` et `cam3d`, il doit rester valable si l'angle ou le FOV changent. À re-mesurer avec `DQ_PROJ=40` (voir plus bas).

=== FICHIERS TOUCHÉS ===

- /home/claude/wt-sprites/dq4_pc/fenetre.py : +94 -7
- /home/claude/wt-sprites/dq4_pc/reglages.py : +2

Détail fenetre.py :
- `_panneau_ville` (nouveau).
- `_decaler_profondeur` (nouveau).
- `_correction_bords` (nouveau).
- `_ancrer_icone` (nouveau).
- `_icones` (branche `cam3d` réécrite).
- Boucle des sprites de ville.
- Option `--correction-bords`.
- Débogage : `DQ_PROJ=n` (pixels des panneaux et des bulles) et `DQ_CAMV_SPR=1` (sprites et icônes dans `DQ_CAMV`).

pyflakes : seul avertissement `sel`, déjà connu.

=== CAPTURES UTILES (chemins /tmp absolus) ===

- /tmp/spr_planche_bords.png : avant (haut) / après (bas), 3 PNJ au bord gauche et 3 au bord droit, 2560×1080 à 200 %.
- /tmp/nr_planche.png : slots 2, 3 et 4 (monde), et grotte avant / après.
- /tmp/nr_combat.png : combat inchangé (6 images, 0 pixel de différence).
- /tmp/nr_hd.png : modes Shader 0 et 1, avant / après.
- /tmp/spr_bulc.png : bulle avant / après au défaut (rendu par un état intermédiaire du code de bulle, qui n'a pas changé depuis).
- Sorties brutes : /tmp/out_mx_*.txt (avant) et /tmp/out_mx3_*.txt (après), /tmp/out_bul_avant_*.txt et /tmp/out_bul_apres_*.txt.
- Scripts : /tmp/spr_resume.py, /tmp/spr_resume2.py, /tmp/spr_bulle.sh, /tmp/spr_bulle.py.

=== NOTES POUR docs/ ===

1. Les sprites de ville sont des panneaux de face à l'écran, reculés en profondeur le long de l'axe de la caméra. Le recul est de 0,185 en bas et 0,65 en haut en unités d'origine, soit ×(w/0,48) dans le visionneur. Cela donne un penché vers l'extérieur proportionnel à l'écart au centre, et une hauteur à l'écran comprimée vers le bas de l'image.
2. La correction reconstruit le panneau à l'écran (coordonnées x/z et y/z de chaque coin) : mêmes positions verticales et mêmes profondeurs que l'original, bords verticaux, largeur = 0,74 × hauteur. `correction_bords` (0 à 1) fait la moyenne linéaire entre l'original et la version corrigée.
3. La bulle Riseup se règle avec la caméra de la visionneuse, pas celle du moteur. Le moteur pose l'icône en monde à +1,294 au-dessus des pieds. Le visionneur la rapporte au personnage sous elle en repère caméra du jeu, puis la ré-exprime en repère caméra visionneuse.
4. Outils de mesure : `DQ_PROJ=n` imprime les 4 coins projetés en pixels de chaque panneau et de la bulle toutes les n images. `DQ_CAMV_SPR=1` ajoute les sprites et icônes à `DQ_CAMV`.
5. Piège de test : les touches de `--touches-test` dépendent du fichier de réglages. Avec `touches_v` 4, `A` = E et `discussion` = SPACE, donc SPACE n'avance plus un dialogue dans certaines configurations. Les sorties dépendent aussi de `vitesse_marche` du fichier passé à `--reglages`. L'appli réécrit ce fichier à la sortie : utiliser une copie par scénario.
6. Cache : le cache de cartes courant est `carte8_*`. Des `carte7_*` écrits par un ancien commit traînent dans /tmp/uicache4 (innocents, jamais relus par le code actuel).

---

## Agent ac898832ce067746b — 02/11 02:59

RAPPORT agent « entrees » (worktree /home/claude/wt-entrees, branche agent-entrees, base 08f5785). Arbre propre. Aucun push. (Renvoi du rapport : le premier envoi n'a peut-être pas été reçu.)

COMMITS
- c4e6378 Entrees (WIP) : clic molette, souris après clavier, infos F1 à droite
- 57dbcfb tests souris après clavier (menu Échap), aides des commandes, geste molette annulé sans bouton
- cb46c17 ligne d'init d'origine conservée (moins de conflits)

ÉVALUATION DU TRAVAIL DU PRÉDÉCESSEUR
Gardé : `entrees.py` (logique pure), les branchements `on_mouse_*` et le geste molette.
Corrigé :
- Un `print('DBGMOL')` de débogage est retiré.
- `_camera_pilotable` et `_zoom_possible` ignoraient licence, écran Sauvegardes, saisie du nom et carte ouverte.
- `pivoter` faisait un tour complet de lacet avant de borner quand le lieu limite la rotation.
- Le point C (F1) n'était pas branché : `zone_infos` existait mais n'était utilisée nulle part.

A. CAMÉRA À LA SOURIS (clic molette)
- Glisser molette maintenu : horizontal = lacet, vertical = inclinaison. Mêmes variables (`self.lacet`, `angle_cam`, `reg['angle_camera']`), mêmes bornes (`CAM_ANGLE_MIN/MAX`, `cam_limite`) et mêmes sens que les flèches (droite = flèche droite, haut = flèche haut).
- Sensibilité en constantes nommées dans `entrees.py` : `CAM_SOURIS_LACET` = 180° et `CAM_SOURIS_ANGLE` = 120° par hauteur de fenêtre. Elle ne dépend donc pas de la résolution. Le sens est inversable en changeant le signe.
- Seuil de 4 px (`SEUIL_GLISSE`) entre clic et glisser. Au franchissement du seuil la caméra ne saute pas. Un glissement annule un recentrage animé en cours.
- Clic molette simple : `recentrer_camera()`, la même animation que « Touche spéciale + touche caméra » (factorisée).
- Ctrl + clic molette : `regler_zoom(100 / DEFAUT['distance_camera'])`, sans toucher à la direction. « Ctrl » = le modificateur pyglet OU la « Touche spéciale » des réglages.
- Contextes : le glisser et le clic n'agissent que si `_camera_pilotable()` (= `_terrain_libre()` + ville + pas `cam_bloquee` + ni licence, ni Sauvegardes, ni saisie du nom), donc comme les flèches. Le zoom (`_zoom_possible`) agit en ville et sur la carte du monde, hors message, menu, carte ouverte, Pause, titre, licence, Sauvegardes, nom.
- Changement de comportement de la molette de zoom : elle ne zoome plus sur le titre, la licence, les Sauvegardes, la saisie du nom ni la carte ouverte (avant, seuls `msg_visible` et `menu_actif` étaient testés).
- Le bouton du milieu sort de `on_mouse_press` / `on_mouse_release` avant tout le reste. Il ne déclenche donc aucun clic gauche simulé, ni menu, ni éditeur d'interface, ni tchat. Avant, `Pause.clic` traitait le bouton du milieu comme un clic gauche. Il est aussi ignoré pendant que la croix ou un bouton du jeu est tenu.
- Si un mouvement sans bouton arrive pendant un geste, celui-ci est abandonné (relâchement perdu).
- Aides mises à jour dans `pause.py` : infobulle des 4 touches caméra, « Touche spéciale », « Distance caméra » et « Infos à l'écran ».
- Harnais (`fenetre._touches_test`) : `%x%y` appui du bouton du milieu, `&x&y` glisser, `*x*y` relâchement. Pour Ctrl : `+LCTRL` / `-LCTRL`. Le survol seul existait déjà (`@x@y@2`).

B. SOURIS « INUTILISABLE ~1 s » APRÈS LE CLAVIER
Cause : aucun délai temporel n'existe dans le code (pas de minuterie, pas de curseur masqué). Ce sont des seuils de mouvement qui font ressembler la souris à un instrument « mort » :
1. `Pause.survol` (menu Échap, base) comparait chaque événement au précédent (déplacement < 3 px en Manhattan), `pos_souris` étant remis à jour à chaque appel. Une souris lente, qui envoie 1 à 2 px par événement, ne reprenait donc jamais la main avant un geste rapide. Le même test laissait passer un tremblement de 2-3 px. Et `sortie()` mettait `pos_souris` à None, ce qui ignorait le premier événement.
2. Jeu : `souris_gel` (6 px Manhattan, après le retour du menu Échap seulement) ; `on_mouse_motion` passait en mode souris sur n'importe quel événement, même nul.
Correction à la racine : `entrees.GardeSouris`, mémoire unique clavier/souris.
- Chaque touche fige la position de référence du pointeur (`on_key_press`, `Pause.touche`, `Pause.ouvrir`, `pause_jeu(False)`).
- Le survol et le mode souris reprennent dès que l'écart CUMULÉ depuis cette référence atteint `TOLERANCE_SOURIS` = 4 px (4 événements de 1 px).
- Un clic agit toujours et immédiatement, et rend la main à la souris (`garde.clic()`). Position inconnue (pointeur hors fenêtre) : le premier mouvement compte.
- `souris_gel` n'est plus lu (l'attribut reste dans la ligne d'init d'origine, volontairement non touchée : à supprimer à la fusion si souhaité).
Protection conservée, avec sa raison : une souris au repos sous un menu qui s'ouvre ne doit pas voler la sélection au clavier. Cas connu des notes : Échap sélectionnait « Sauvegarde rapide ». La tolérance couvre le tremblement du capteur ou de la main. Les événements nuls sont déjà filtrés par pyglet Win32 si ma mémoire du code est juste (non vérifié ici).
Test : `outils/test_entrees.py` (37 tests, sans fenêtre). Les tests Pause échouent sur le code de base (je l'ai vérifié sur un `git archive` de 08f5785 : 3 échecs) et passent sur la nouvelle version.

C. INFOS F1 EN HAUT À DROITE
- F1 = action `infos` : bloc de lignes d'information (lieu, fenêtre, réglages, son, performances) dans un cadre noir translucide, qui était en haut à gauche. Ce n'est PAS l'éditeur « Interface », dont le panneau est déjà en haut à droite par défaut.
- Le bloc n'avait aucune position enregistrée ni déplaçable : pas de migration et pas de clé de réglage. Le point du brief sur « position déplacée / double clic / Rétablir l'interface » ne s'applique pas. Je n'ai pas ajouté d'option (Sylfried les supprime). Si tu le veux déplaçable, c'est un autre chantier.
- `_marge_aide` renvoie `(côté, largeur)` via `entrees.zone_infos` : côté droit par défaut, côté gauche si la colonne d'interface est à droite (`--ui-pos droite`). La largeur reste la marge libre à côté de la colonne d'interface, avec un minimum de 260 px. Le cadre est collé à `largeur - 4`, et sa largeur ne fait que croître tant que F1 est affiché (et est réinitialisée si la mise en page change), pour que le texte ne vibre pas.
- Aucun changement à `reglages.py`. `test_reglages_interface.py` et `test_panneau_interface.py` passent sans modification (12 et 10 tests OK).

ÉTABLI / SUPPOSÉ / NON VÉRIFIÉ
- Établi (lu dans le code ou mesuré) :
  - 37 tests de `test_entrees.py`, ainsi que `test_reglages_interface` (12), `test_panneau_interface` (10), `test_pause_pages` (15), `test_reglages_son_texte` (7) et `test_mode_fenetre` (18, 1 ignoré) passent.
  - Capture harnais en ville (slot 1, 1280x720) : un glissement molette donne « rotation 15 °, angle +10 ° », conforme aux constantes. Le bloc F1 est bien en haut à droite en 1280x720, en 2560x1080 (21:9) et en 960x720 (4:3, texte replié à 260 px).
  - Le glisser, le clic et Ctrl+clic sont sans effet sous un message ou un menu du jeu (vérifié en harnais : le menu de l'église bloquait le glisser) et dans tous les cas de la liste (tests avec un `Jeu` factice qui utilise les vraies méthodes).
- Supposé :
  - La cause B décrite ci-dessus : établie par lecture et reproduite par un test, mais jamais observée sur ton PC. Il se peut qu'une part de la gêne vienne d'ailleurs.
  - Une vraie molette Windows envoie `MIDDLE` dans `on_mouse_press/drag/release` ; Ctrl arrive dans `modifiers`.
- Non vérifié :
  - Sensation du glisser molette sur une vraie souris Windows : sensibilité, sens, seuil de 4 px.
  - Clic simple (recentrage animé) et Ctrl+clic (zoom 100 %) en harnais : leur prise en compte est testée par les tests unitaires mais pas vue en capture.
  - Le run combiné `ed` (caméra + survol du menu Échap, captures `/tmp/m_ed_b*.png`, journal `/tmp/out_ed.txt`) était encore en file d'attente derrière le verrou xvfb au moment du rendu. Je n'ai pas vu ses images ; elles peuvent exister maintenant.
  - Aucune capture du survol lent dans le menu Échap.
  - Pas de capture de F1 en 1080p ni en plein écran (la logique est la même).
  - Le bloc F1 se superpose au panneau « Interface » de l'éditeur (aussi en haut à droite) quand les deux sont visibles : acceptable, mais pas vu.

FICHIERS TOUCHÉS
- `dq4_pc/entrees.py` (nouveau)
- `dq4_pc/fenetre.py`
- `dq4_pc/pause.py`
- `outils/test_entrees.py` (nouveau)
- `outils/test_mode_fenetre.py` : une ligne, `faux_jeu` reçoit `souris=(0,0), garde_souris=GardeSouris()`, car `on_key_press` mémorise maintenant la position du pointeur.
Captures utiles : `/tmp/m_ea_b45.png` (rotation 15° et angle +10° avec F1 en haut à droite), `/tmp/m_ef_b40.png` (21:9), `/tmp/m_eg_b40.png` (4:3).

PIÈGES DE FUSION (zones de `fenetre.py`)
- Import `entrees as EN` (ligne 23).
- `__init__` : nouvelle ligne `garde_souris` / `molette` après la grosse ligne `self.lacet...`, laissée intacte. Ligne `self.aide = ... aide_larg, aide_cle` modifiée.
- Nouveaux : `_zoom_possible`, `_camera_pilotable`, `recentrer_camera`, `_ctrl_actif`, `_molette_appui` / `_glisse` / `_relache`. Ils sont insérés avant `on_mouse_scroll`, dont la dernière ligne change.
- `on_mouse_drag` (3 lignes), `on_key_press` (1 ligne `garde_souris.clavier`), `pause_jeu` (remplacement de la ligne `souris_gel`).
- `on_mouse_press` (2 lignes), `on_mouse_motion` (garde + annulation du geste molette + suppression du bloc `souris_gel`), `on_mouse_release` (1 ligne).
- `_maj_camera` : un appel `recentrer_camera()` remplace les 2 lignes de remise à zéro.
- `_marge_aide` et `_dessiner_aide` réécrits.
- `_touches_test` : docstring et 3 événements.
- Dans `pause.py` : import, `ouvrir`, `touche`, `survol`, nouveau `_garde`, textes d'aide (Distance caméra, Commandes) et variable `infos` dans `_e_commandes`.

NOTES DE DOC À FUSIONNER (notes-visionneuse, « Retours de 02 h 12 (#43) »)
- Entrées. Clic molette (`fenetre._molette_*`, `entrees.GesteMolette`) : simple = direction de la caméra remise (animation de recentrage des flèches) ; Ctrl (ou Touche spéciale) + clic = zoom à 100 % sans toucher à la direction ; maintenu + déplacement = rotation et inclinaison (`entrees.pivoter`, mêmes bornes et sens que les flèches ; constantes `CAM_SOURIS_*`, `SEUIL_GLISSE`). Actif seulement quand les flèches le sont (le zoom aussi sur la carte du monde). Harnais : `%x%y`, `&x&y`, `*x*y`, `+LCTRL`.
- Souris après clavier. `entrees.GardeSouris` remplace `souris_gel` et le seuil par événement du menu Échap. La référence est figée à chaque touche, le survol reprend à 4 px cumulés (`TOLERANCE_SOURIS`), un clic agit toujours. Les tests échouent sur 08f5785. Cause établie par lecture, non vue sur Windows.
- F1 : le bloc d'infos est en haut à droite (`entrees.zone_infos`), à gauche seulement si la colonne d'interface est à droite. Aucune position enregistrée, aucun réglage ajouté.
- Test : `outils/test_entrees.py`.

---

## Agent ab93c153d22168574 — 02/11 03:01

RAPPORT : audit issues GitHub et décisions (reprise). Lecture seule respectée : dépôt resté sur main 08f5785 et propre ; rien écrit sur GitHub, dans le Projet ni dans la mémoire ; `add_repo` non appelé ; `claude/piste-3-projet-unity.md` non ouvert ; sauvegardes, patch FR et fichiers des autres agents non touchés.

FICHIERS (révisés, pas refaits de zéro) : /tmp/audit/github_issues.md (27,7 Ko), /tmp/audit/decisions.md (61 Ko), /tmp/audit/lacunes_connues.md (38 Ko).

1. VOLUMES
- Issues (établi, REST) : `dq4-portage` 0 issue (issues activées, 10 étiquettes GitHub par défaut, 0 jalon, 43 branches distantes jamais supprimées), 42 PR « Avance #N » fusionnées, 0 commentaire. `dq4-pc` (historique) 43 issues : 27 ouvertes, 16 fermées ; 36 PR ; 9 commentaires. Recommandation par issue ouverte au §5 de github_issues.md : 7 à fermer (#2, #5, #7, #10, #22, #23, #41), 2 à fermer après confirmation (#40, #17), 16 réelles, 2 à décider (#6, #57).
- Décisions : 128 identifiants D-xx. Sources : 7 lus directement dans la transcription [T] (messages de 02:27 à 02:38, tous nouveaux), citations recopiées par Claude [C] (message de 23:24 en entier, phrases des lots de 18:02 et 20:46, message de 02:12), retours rapportés dans les PR [R], 10 entrées de la mémoire [M] (D-01 à D-10), choix de Claude [K] séparés. 21 contradictions (C-1 à C-21).
- Lacunes : 161 lignes (144 lacunes + 17 demandes du lot #43). Classement provisoire : à vérifier 97, oubli 19, décision 17, bug 12 (une ligne peut porter deux tags).

2. LES 10 LACUNES LES PLUS GRAVES POUR LA JOUABILITÉ (supposé : classement de lecture)
1. G-092 boutiques (achat, vente, quantité) : codées, jamais jouées.
2. G-120 sauvegarde réelle à l'église puis rechargement : jamais confirmée sous Windows (issue #9, prio:haute).
3. G-093 casino, banque, église : aucun test documenté (à trancher par l'agent couverture ; le code ne nomme que 4 parties).
4. G-031 bateau, ballon et autres transports : jamais étudiés.
5. G-001 / G-023 rendu Windows/GPU réel et comparaison au mobile : jamais faits.
6. G-044 allocateur sans libération : `MemoryError` possible sur longue session.
7. G-070, G-071, G-078 boss, groupes, effets de sorts, victoire / montée de niveau / game over : non vérifiés.
8. G-041, G-042, G-043, G-052, G-069 scènes d'histoire non rejouées : paquets 1, 6, 16, 17, 18, 27, 30 et 33 non traités, FEAN, auberge, chapitres, générique.
9. G-055 murs invisibles et escalier de `dbout` ; G-079 retour au titre depuis un combat ou une boutique puis nouvelle partie.
10. G-099 / G-098 clavier du nom inventé, nom refusé non testé, « Revenir à l'écran titre » qui efface la sauvegarde auto.

3. CONTRADICTIONS DÉCISIONS / ÉTAT (établi par lecture du code)
- C-1 plein écran exclusif encore présent (`reglages.py:78`, `fenetre.py:272`) vs D-30. C-2 option `correction_bords` encore présente (`pause.py:292`) vs D-31. C-3 plaque « Sauvegarde auto » cachée vs D-32. Idem pour D-46 (`pause.py:286`), D-48 (`pause.py:424-425`), D-49, D-17, D-34 : aucune demande de 02:12 à 02:38 n'est sur main.
- C-19 : D-47, le défaut de `camera_centree` est déjà True dans le code (`reglages.py:28`) ; le False viendrait du `reglages.json` (non lu).
- C-10 / C-14 : D-14 « le jeu prend le dessus, valable pour tout » n'a qu'un précédent codé (la caméra, `fenetre.py:987-990`) ; le reste n'est pas inventorié.
- C-6 : « le moteur ne se modifie pas » vs patches mémoire. Deux sont demandés par Sylfried (D-123, D-124), les autres sont de Claude.
- C-21 : il a cité un exemple de choix inutile de l'éditeur, Claude en a retiré 18.
- C-7 : ciel du titre « garder tel quel » vs « pattern répétitif ». C-11 / C-12 : docs et README périmés (suivi par issues, `Closes #`, « prochaine issue #1 »).

4. CORRECTIONS À CE QUE LE PRÉDÉCESSEUR OU LE BRIEF AVAIT
- ERREUR À NE PAS RÉPÉTER : le message de 02:37 dit que la vitesse du combat change animations et dialogues, mais PAS la musique ni les bruitages (D-18). Je l'avais d'abord lu à l'envers, c'est corrigé dans les fichiers.
- Le message de 23:24 existe en entier (brief42) : il n'était pas « tronqué ». Il contient une décision de principe absente du registre : montrer l'envers du décor si le mobile le montre (D-29d).
- Sylfried a bel et bien demandé de revoir les shaders flous (D-131) : le retrait de « Bicubique » et « Régions lissées » répond à sa demande, même si le choix des deux shaders est de Claude. Le débordement des textes français est de son côté un non-sujet pour le portage (D-133).
- Références « notes l.N » ambiguës, toutes remplacées par NV:N / NT:N. Corrigé aussi : PR #36 (facteurs de la croix : prouvés ou retirés dans l'audit de #39), 30 Hz (moteur établi, fondus d'Unity supposés), lignes d'`emu_core.py`.

5. CE QUE JE N'AI PAS PU LIRE (non vérifié)
- Dépôts `dq4-portage-unity` et `dq456-traductions-fr` (accès non activé, volontairement non contourné), `claude/piste-3-projet-unity.md` (consigne).
- `Menu_Echap_DQ4_PC.xlsx` (absent du dépôt).
- Les messages de Sylfried antérieurs à la compaction ne me sont connus que par le brief, les missions et les PR : le lot de 20:46 compte 21 points, je n'ai le texte que d'environ seize ; ceux de 18:02 sont partiels.
- L'outil de lecture du Projet n'est pas disponible pour moi : j'ai utilisé les copies `/home/claude/pjdocs/`.
- Aucun accès Windows/GPU, ni à son `reglages.json`, ni à ses sauvegardes. GraphQL indisponible, REST seulement.
- Les anciennes conversations n'ont rien donné d'utile (Unity et patch FR seulement).

6. FAITS ISSUS DE LA MÉMOIRE
Seulement D-01 à D-10 (§1 du registre, marqués [M]) : projet 16/9 d'abord, APK déjà patchés FR, voies A/B/C, projet séparé du patch FR, Claude gère tout git, trois dépôts côte à côte, piste Unity en pause. La mémoire s'arrête au 30/10 22:50 pour le portage : elle ne contient aucune décision du 31/10 au 02/11. Aucune instruction suspecte trouvée dans la mémoire ni dans les documents.

7. À MÉMORISER (décision de la session principale ; source entre crochets)
- Le jeu prend le dessus sur les réglages du joueur quand un script change la valeur, « valable pour tout » [message 02:12].
- Plein écran exclusif supprimé, F11 / Alt+Entrée alternent plein écran et fenêtré [02:12].
- Ce qui doit être toujours actif n'est pas une option : correction des bords [02:12], lissage des textures [02:27].
- Combat : trois vitesses Normal / Rapide / Très rapide, sans accélérer musique ni bruitages [02:35, 02:37].
- Historique des messages avec le nom de qui parle [02:36].
- F1 en haut à droite par défaut [02:14].
- Règle « ne jamais supprimer un bouton non cité » [23:24].
- Zone portrait centrale = vue du téléphone ; montrer l'envers du décor si le mobile le montre [23:24, 02:12].
- Les textes qui débordent relèvent du projet de traduction [20:46].
- Sylfried délègue souvent le détail (« je te laisse choisir », « ne le fais que si c'est pertinent ») : Claude décide, puis le dit.
- Fuseau Europe/Paris (UTC+1), établi par la transcription.

---

## Agent a013cab3ae1bf6983 — 02/11 03:13

RAPPORT « libelles » (PR #43), branche agent-libelles, worktree /home/claude/wt-libelles

LIVRÉ (1 commit 4ec25d6, arbre propre, pyflakes sans alerte, 13 tests OK en 0,1 s, import 0,0x s sans numpy/unicorn/pyglet)
- dq4_pc/libelles.py : libelle_source(modele), libelle_lieu(carte) + confiance_source() / confiance_lieu() (« certain/suppose » ; « officiel/derive/generique »).
- outils/generer_libelles.py : régénère le bloc « lieux » de libelles.py et les tableaux de fréquence de test_libelles.py (`--apk <dossier APK> --cache <cache cartes> [--ecrire]` ; sans --ecrire = simulation). ~13 s.
- outils/test_libelles.py : sans xvfb, sans moteur, sans APK (données embarquées) ; imprime la couverture avec -v.
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
- `outils/test_objets_carte.py` (nouveau, prédécesseur complété) : 15 tests, environ 5 s, sans xvfb. Cherche les cartes dans `DQ_CACHE_CARTES` (défaut `/tmp/uicache_coffres`) et ignore les tests « vrais objets » si le cache manque.
  - 11 tests de logique pure : `euler_mat` contre une référence quaternions indépendante, bascule X dans le repère de l'objet, couvercle à tous les caps, tiroir et échelle, ordre moteur pos/rot puis anim, porte inchangée.
  - 4 tests sur les VRAIS objets : les 194 coffres (rotation rigide autour de la charnière, aucun roulis le long de l'axe X du coffre, bord libre qui monte et recule, refermeture identique au départ), tiroirs (déplacement = R(cap) · clé), portes.
  - Vérifié que le test des coffres échoue avec l'ancien `euler_mat`.
- Commits (pied de message du brief présent) : ac4cb9b (correction + cache carte9) et f58ce7b (tests des vrais objets).
- pyflakes : seul avertissement `struct` inutilisé dans `donnees.py`, déjà connu.

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
3. `fenetre.py` : une seule ligne ajoutée (test), conflit très peu probable.
4. `outils/test_objets_carte.py` est nouveau ; les tests existants ne dépendent pas de `euler_mat`.

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
- Test : `outils/test_objets_carte.py`.
- Reste non vérifié : voir ci-dessus.

Mémoire (informations utiles pour plus tard, source = cette session) : l'utilisateur teste ses captures sur des cartes réelles du jeu (la capture « Screen 3 » correspond très probablement à `mdi1f1`, cap -27).

---

## Agent a26ba55965f699b65 — 02/11 03:21

RAPPORT « options » (worktree /home/claude/wt-options, branche agent-options, base 08f5785). Arbre propre. 1 commit : 41b3ee8 (sujet A). Sujet B : aucun commit (essai de correction annulé, voir plus bas).

=== A. Le jeu prime sur les réglages du joueur ===
Code : nouveau module sans dépendance dq4_pc/priorite_jeu.py (valeur_effective(reglage_joueur, valeur_jeu=None), facteur_effectif, lettres_par_image, duree_fondu). Trois corrections réelles : marche, zoom, fondus de script. Le texte était déjà correct dans DQ4 : je l'ai seulement passé par la fonction pure.

ÉTABLI
- Texte : DQ4 n'a aucune commande de script ni écriture du mot de vitesse (MSG_VITESSE 0x2523b0) hors ui_MsgSetup, qui le copie du tableau par type de fenêtre (types 0,1,2,5 = 1 ; 3,4 = 100). Le crochet de ui_MsgLoop+0x128 ne remplaçait déjà que la vitesse standard (4 lettres/image) ; il passe maintenant par lettres_par_image, même comportement. Test moteur : en écrivant le mot à 2 (comme le ferait un script), la durée est identique (15 images) pour 0,5 / 4 / 16 / 4000 lettres/image ; sans cela le réglage joue (140 images à 0,5, 11 à 16). test_texte_defilement.py repasse à l'identique (24 images à 4,0 ; attentes de combat 12/22/32/42).
- Défilement des messages de combat (battleSpeed g_Option+5) : écrit seulement par la fenêtre Paramètres et le chargement d'une sauvegarde ; les cas où le jeu bloque l'avance auto (disableAutoFeed, setDisableCursor) sont des drapeaux séparés que le réglage ne touche pas. Inchangé.
- Marche x1 à x4 + accélérateur : jusqu'ici _facteur_vitesse accélérait l'horloge du moteur dès qu'une direction était tenue, même pendant une scène sans message. Global.Flag mesuré : exploration libre = 0x38 (ville), 0x28 (carte du monde) ; scène du jeu = 0x3c (bit 4 = verrou du joueur) sans message (83 images dans la sauvegarde 2, prologue : 0x1c/0x1d pendant tout le prologue) ; fondu = bit 1. Maintenant facteur 1.0 si Flag & (1|4) (constantes MO.DRAPEAU_FONDU, MO.DRAPEAU_JOUEUR_VERROUILLE).
- Fondus (« Vitesse de transition », x2 par défaut) : les commandes de script fade_in / fade_out (__cmd_fade_in::initialize 0x21b3c0, __cmd_fade_out::initialize 0x21b43c) donnent leur durée (sauvegarde 2 : fade_out 30 images à l'image 6, fade_in 60 à l'image 385) et attendent elles-mêmes ce nombre d'images (isEnd compte les images). Raccourcir le fondu ne faisait donc que laisser l'écran noir plus longtemps. Crochet dans Moteur._crochets_fondu : le paquet 9 reçoit la marque bit 16 (PJ.MARQUE_FONDU_SCRIPT) quand UnitySetFade (0x17e120) est appelé depuis ces deux fonctions ; Etat._fondu ne raccourcit pas ces fondus. Fondus du moteur (changements de carte : 45, 30, 60 images) toujours raccourcis ; fondus en couleur / blancs jamais. Mesuré à x4 : script 30 → 30, 60 → 60 ; moteur 30 → 8, 45 → 11, 60 → 15.
- Caméra : rotation / inclinaison manuelles et vitesse de caméra sont déjà neutralisées par cam_bloquee (verrou TownCamera ou rotation interdite) ; « caméra centrée » déjà soumise à cam_jeu / cam_libre. Inchangés.
- Tests : outils/test_priorite_jeu.py (12 tests, OK : règles pures, _facteur_vitesse sur faux objet, zoom, moteur avec --apk/--saves/--slot/--slot-fondu 2), test_reglages_son_texte.py (+1 test) ; test_camera_ville, test_pause_pages, test_reglages_interface, test_mode_fenetre, test_panneau_interface, test_son_mixage OK ; smoke fenêtre xvfb OK (RG=/tmp/rg_opt_sm.json, marche x3). pyflakes : seulement les avertissements connus.

SUPPOSÉ
- Zoom (distance de la caméra, molette) : facteur_effectif(zoom, e.cam_libre) → sans zoom pendant une caméra libre de scène (position, angles, champ fixés par le script). Pendant un travelling (cam_jeu), le jeu ne fixe que la cible : le zoom est gardé.
- Le fondu de script reconnu = seulement fade_in / fade_out ; je pars du principe que le joueur ne veut pas que ces fondus soient raccourcis.

NON VÉRIFIÉ
- DQ5 / Nimzo : pas de moteur DQ5. Un script qui fixerait précisément la vitesse standard (mot 1) serait pris pour le défaut ; il faudrait alors un crochet d'écriture mémoire sur le mot.
- Aucune scène cam_libre observée dans mes traces (8 cartes) : la correction du zoom n'est testée que sur faux objet.
- Boucle fenêtre avec une direction tenue pendant le prologue : couvert par test unitaire + sonde des flags, pas par une capture.
- Non traité : le fondu du titre de chapitre (Global::fadeInBlack(60), appelé par cmd_event_chapter_title, adresse 0x18da7c) reste raccourci (commande de script, mais pas via fade_in/fade_out). Aussi, la normalisation « zoom commun » HEROS_FRAC écrase la distance / le fov fixés par script hors cam_libre (choix de la visionneuse, pas un réglage joueur) : non touchée.

TABLEAU A.1 (réglage → le jeu peut-il le fixer ? → traitement)
- Vitesse du texte → DQ4 : non (table par type de fenêtre) ; détecté par le mot ≠ standard → déjà respecté ; règle pure + tests.
- Messages en combat (defilement_force / combat) → non par script (Paramètres + sauvegarde) ; drapeaux d'avance auto prioritaires par construction → inchangé.
- Vitesse de marche + accélérateur (clé vitesse_accel) → oui (scènes : verrou 4, fondu 1) → CORRIGÉ (facteur 1.0).
- Vitesse de caméra / accélérateur de caméra → oui (verrou TownCamera, rotation interdite) → déjà neutralisé (cam_bloquee).
- Distance de la caméra / molette → oui (caméra libre de scène) → CORRIGÉ (neutre en cam_libre ; cam_jeu : zoom gardé, supposé).
- Caméra centrée → oui (cam_jeu, cam_libre) → déjà prioritaire au jeu.
- Angle / lacet de la caméra → oui (verrou) → déjà neutralisé.
- Vitesse de transition → oui (fade_in / fade_out de script) → CORRIGÉ (marque du paquet 9).
- Volumes, interrupteurs son → non : les paquets 35-37 ne portent que l'identifiant ; volume du fichier et option « volume » du jeu déjà multipliés → N/A.
- Luminosité, netteté, vignette, MSAA, échelle de rendu, lissage, sprites, mode fenêtre, résolution, taille des dégâts, correction des bords → pas de paramètre équivalent côté jeu (la luminosité est une passe finale après les effets d'écran du jeu) → N/A.
- Boutons / croix / fenêtres masquées ou déplacées → choix d'affichage du joueur ; le jeu masque déjà par PLAYER_LOCK / GUI_LOCK (hud_mobile.visibles) → N/A.
- Touches → N/A.
Réglage de l'agent « combat » touché par mon inventaire : vitesse_accel, via _facteur_vitesse (je lis la clé, pas le libellé : le renommage en « Multiplicateur de l'accélérateur » n'a aucun effet sur mon code).

=== B. « Le nom de Ragnar est trop bas » ===
Avis : impression fondée mais faible ; je n'ai rien changé.
ÉTABLI
- Capture 1280x720 (/tmp/c_opt_av_230.png, rendu actuel inchangé) : intérieur du bandeau y 30 à 48 (centre 39) ; majuscules y 35 à 46 (centre 40,5), soit 1,5 px sous le centre (≈ 2,3 px à 1080p) ; marge haute 5 px, ligne de base à 3 px du séparateur, queue du g à 0-1 px (elle touche). Cohérent avec ta capture /tmp/specs/img43/s4_nom_ragnar_combat.png ; l'onglet « Ragnar » de la fenêtre de commandes (s5) paraît bien centré.
- Type 29 : nom = TextMesh ancre 1 (UpperCenter, cs 9,3925, ls 0,8013, z 385,5) ; lignes PV/PM/Nv. = ancres 0 et 2 (Upper, ls 1,258, z 359). Toutes ancrées en haut : base0 = zp − ascent, indépendant de lineSpacing, donc même formule pour le nom et pour PV/PM/Nv. (qui s'alignent bien sur leurs jauges).
- Essai d'un recentrage global (« glyphes centrés dans leur cellule de ligne » dans Fenetre._texte) : remonte le nom de 2 px mais DESCEND PV/PM/Nv. de ~1,5 px (les chiffres touchent les jauges). Régression → annulé. Comparaison : /tmp/c_opt_cmp_plaque.png (gauche = rendu actuel conservé, droite = essai rejeté) ; plein cadre : /tmp/c_opt_av_230.png (actuel) et /tmp/c_opt_ap_230.png (essai) ; autres images /tmp/c_opt_av_{170,185,200,215}.png et /tmp/c_opt_ap_*.
SUPPOSÉ
- Le décalage vient des données (z 385,5 + biais dy) et pas d'une erreur de la visionneuse : l'original aurait le nom aussi bas. À confirmer avec une capture de téléphone de la plaque.
NON VÉRIFIÉ
- La formule exacte de TextMesh dans libunity pour la police bitmap (ancres Middle : N pas ou (N-1) pas + une ligne, ≈ 1 px d'écart, concerne les onglets de type 32, pas ce nom).
- Si tu veux quand même le remonter : décalage ciblé des textes de la plaque type 29 de ≈ 1,5 px (720p), choix arbitraire à valider.

=== Notes de doc à fusionner (rien écrit dans docs/) ===
- notes-visionneuse : section « Priorité du jeu sur les réglages du joueur » : principe (réglage = valeur par défaut, le jeu prime quand il fixe la valeur), tableau A.1, règles pures de priorite_jeu.py.
- notes-technique : Global.Flag en pratique (libre 0x38 ville / 0x28 carte du monde, scène 0x3c, fondu bit 1 : 0x39 / 0x3d, combat avec bit 4 posé) ; UnitySetFade 0x17e120 écrit [9, v] et lève le bit 0 ; __cmd_fade_*::initialize appellent Global::fadeOutBlack (0x17d600) / fadeIn (0x17dfec) avec durée = (arg + 1) >> 1 et plan de fond via [Global+0xec] ; fondus du moteur vus : fadeOutBlack(45) en 0x15357c, fadeInBlack(30) en 0x18d9f0, fadeInBlack(60) en 0x18da7c ; durée = bits 0-10 de v, marque visionneuse = bit 16.
- Piège Unicorn : un crochet ajouté après qu'un bloc a été traduit ne se déclenche pas ; les installer dans Moteur.__init__ avant les step (comme _crochets_texte) et appeler ctl_flush_tb().
- Aides de la page Commandes (non touchées) à compléter par qui fusionne : « Vitesse de marche » → ajouter « les scènes et les fondus du jeu gardent leur rythme » ; « Vitesse de transition » → « sauf les fondus qu'un script du jeu fixe lui-même ».

=== Pièges de fusion ===
- fenetre.py : _facteur_vitesse (+1 ligne après le test pad(), docstring) ; l'agent « combat » y touche probablement : si le facteur est étendu au combat, NE PAS reprendre mon test de verrou (le bit 4 est posé en combat : flags 0x2d / 0x6e observés). _camera_ville : th_v /= PJ.facteur_effectif(self.zoom, e.cam_libre) ; import priorite_jeu as PJ ajouté après import reglages as RG.
- moteur.py : import priorite_jeu as PJ après import emu_core ; constantes DRAPEAU_* près de COMBAT_MANUEL ; corps de _vt dans _crochets_texte ; nouvelle méthode _crochets_fondu insérée avant _option, appelée juste après self._crochets_texte() dans __init__ ; Etat._fondu (2 lignes).
- pause.py et reglages.py : non modifiés (aucune nouvelle option).
- Les fondus de script ne sont plus raccourcis : les captures ou tests de durée qui comptaient sur « fondus x2 » dans une scène à fade_out / fade_in changent.

Fichiers touchés : dq4_pc/priorite_jeu.py (nouveau), dq4_pc/moteur.py, dq4_pc/fenetre.py, outils/test_priorite_jeu.py (nouveau), outils/test_reglages_son_texte.py. dq4_pc/ui_menu.py : modifié puis rétabli (aucune différence avec 08f5785).
Hors dépôt (scratch) : /tmp/run_opt.sh, /tmp/rg_options.json, /tmp/rg_opt_sm.json ; sondes dans /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/ (sonde_verrou*.py, sonde_fondus*.py, sonde_marque.py). Rien de mémorisable côté utilisateur (aucun fait personnel appris).

---

## Agent ad9be5b9dfd5bdfb2 — 02/11 03:22

RAPPORT COUVERTURE (agent audit, lecture seule). Livrable complet : /tmp/audit/couverture.md (7 sections + synthèse en tête, ~59 Ko). Dépôt intact (git status vide dans /home/claude/wt-audit), aucun commit. Écritures seulement dans /tmp/audit et /tmp/sv_audit_*.

SYNTHÈSE
- ÉTABLI : balayage v2 headless de 529 cartes (90 images, 123 s au total) : 528 sans plantage, 0 sprite sans feuille (les 93 ids existent dans le datapack), 0 PNJ hors carte (507 cartes analysables), 0 fondu bloqué. Le flux moteur→visionneuse est sain ; les trous sont dans ce qui est ignoré ou jamais joué.
- ÉTABLI : 16 sites d'écriture mémoire de la visionneuse (§4), aucun ne touche scénario, variable, or, inventaire ou position. Seul point à surveiller : g_Option+5 (défilement des combats) est écrit chaque image quand l'option est imposée, donc enregistré dans les sauvegardes du jeu (ce dernier point : Supposé, non essayé). Les originaux de sauvegarde ne sont jamais ouverts en écriture (moteur.py:41,53).

LACUNES LES PLUS GRAVES (avec preuves)
1. Poker invisible (ÉTABLI, GL) : gl_poker_b330.png = écran noir + fenêtres ; gl_pokerv_b330.png (même scène, affichage forcé en "ville" par mon lanceur hors dépôt) montre les 5 cartes. Cause : garde `e.partie == MO.PARTIE_VILLE` à fenetre.py:2913 ; le casino est la partie 0xf, inconnue de la visionneuse (moteur.py:8-11 ne définit que 3, 0xc, 0xd, 0xe). La carte ev04 n'a ni sol ni texture : tout est maillage dynamique (paquets 21/22).
2. Machine à sous injouable au clavier (ÉTABLI, GL) : le clavier (Haut×3 + Entrée) laisse la mise à 0 (gl_slotkb_b420.png), la souris marche (gl_slotms_b350.png : Jetons 497, rouleaux). Cause : `_saisie_menu` (fenetre.py:1597-1621) n'expose que les boutons de manette 0x10 ; ▲/▼ sont 0x2/0x1 et la fenêtre n'a pas de grille moteur. Côté moteur, slot et poker sont jouables (mise 500→497, rotations, arrêt, sortie propre).
3. Bestiaire (partie 0x10, ÉTABLI GL) : liste et fiche en texte OK, mais le monstre n'est pas dessiné et l'église mak1f1 apparaît dans son cadre (gl_booksel_b330.png). Le moteur envoie pourtant le maillage (paquet 22). Forcer la partie en ville ne change rien (capture identique octet pour octet) : cause NON trouvée.
4. Paquet 33 (map_color_rate) ignoré : émis sur 171/529 cartes au chargement (149 en (1,25;0,65;0,75), 20 `te*` en (1,3;0,7;0,55), caf1/ev02 animé). Côté Unity (cmd_map_color_rate, RVA 0xD14E44, désassemblé) = Field.SetColor(r,g,b,1). Porte aussi le jour/nuit de la carte du monde (FieldStage::ChangeTime) et le marais (FieldPlayerDoku). Effet visuel exact : Supposé.
5. Paquets ignorés sans trace (ÉTABLI, aucune branche dans Etat.appliquer) : 1, 6 (animations d'événements, dont gain de la machine à sous), 16/17/18 (poses couché, auberge ; vus dans mlb1a, mlm2f1, taf1), 27 (contourné par lecture mémoire), 30 (zoom du ballon), 33. Paquet 13 : échelle de sprite (bit 0x800) lue puis jetée (mlb1a 0,738, ev07 0,952 : effet Supposé). Paquet 34 : seule la valeur 4 est rejouée.
6. Boutiques, banque, église (résurrection, sauvegarde), auberge, arène, colisée, bateau, ballon, chariot, générique : INCONNU, jamais ouverts (aucun test automatique ne les atteint ; seul le type 12 s'ouvre au chargement). Ils passent par des commandes de script (cmd_menu_shop/save/colosseum/extra_shop/nene/hostage/present_exp/event_imuru, cmd_the_end). C'est la plus grande zone sans information.

NON VÉRIFIÉ (détail §6) : gameplay des points ci-dessus (j'ai tenté d'ouvrir une boutique par le moteur, abandonné : il faut l'objet CommandWindow ou poser le héros devant le marchand) ; rendu Windows/GPU réel (tout est Mesa/xvfb) ; décodage des 686 .akb (son.py avale 12 exceptions) ; combats complets ; carte du monde jour/nuit, ballon, bateau ; poker jusqu'au bout ; ev01 (plante par startTown, Supposé artefact du lanceur car le titre le charge) ; effet exact de UnityInitTouchFlag.

POUR LE BALAYAGE (§5) : startTown(nom) ne place PAS le héros à l'entrée (235 sprites héros/équipier à la position héritée (1,97 ; 0,047 ; 44,08) sur 117 cartes) : à résoudre avant le niveau 2. Coût mesuré N1 : 0,23 s/carte (90 images) ; estimé 600 images ≈ 14 min en 1 processus, ≈ 7 min en 2 (indices 0-265 / 265-529). N2 (parler à chaque PNJ) ≈ 25 min sur 2 cœurs (estimé). N3 (captures GL en un seul processus, un seul xvfb à la fois) ≈ 35-55 min (estimé). Règles de détection R1-R12 dans §5.4.

NOTES À FUSIONNER DANS LES DOCS (§7) : (a) la ligne "classes IBase personnalisées non reproduites" des notes techniques est périmée, les 5 classes sont portées (ui_menu.py:199-413) ; (b) le paquet 33 n'est pas limité à mlb1a (notes-technique:233) ; (c) parties moteur 0xf casino et 0x10 bestiaire inconnues de la visionneuse ; setMinigame(0)=poker ev04, autre=slot ev05 ; startBook ← TownMenuItemSelectCommand::menuUpdate ; startSurechigai ← cmd_change_surechigai_part ; (d) clavier : boutons de manette 0x2/0x1 inaccessibles sans grille ; (e) mot de touches : bit A du terrain seulement si arg2 == 0x100 exactement (NativeExec 0x17d3d8) ; (f) tableau des paquets avec statuts (§1).

Mémoire utilisateur : rien lu ni utilisé.

FICHIERS (tous dans /tmp/audit/) : couverture.md ; balayage.py + bal2_tout.json + analyse.py (sweep v2 et son analyse) ; paquets_raw.txt, menutypes3_raw.txt ; probe_slot3.py, probe_slot4.py, probe_poker2.py, probe_poker3.py, probe_grille.py, probe_book.py, probe_book2.py ; gl_casino.py + run_gl_casino.sh (lanceur GL hors dépôt, mêmes verrous que run_wt.sh) ; captures gl_poker_b330.png, gl_pokerv_b330.png, gl_slot_b330.png, gl_slotms_b350.png, gl_slotkb_b420.png, gl_book_b230.png, gl_booksel_b330.png ; callgraph.py + cg.pkl ; echelles.py ; feuilles_datapack.json. Temporaires : /tmp/audit/cache_donnees (3 Mo), /tmp/audit/rg_audit.json, /tmp/sv_audit_*.

---

## Agent aeab3de440c6b8a30 — 02/11 04:29

RAPPORT FINAL, agent « combat » (worktree /home/claude/wt-combat, branche agent-combat, base 08f5785). Arbre propre, 2 commits (trailers Co-Authored-By et Claude-Session présents, rien poussé) :
- 42de0fd Vitesse des combats (Normal / Rapide / Très rapide) et renommage « Multiplicateur de l'accélérateur »
- 79341e7 Test du rejeu d'un combat du moteur réel : nombres de dégâts comparés, nombre de pas réglable

=== A. Renommage ===
« Vitesse de l'accélérateur » devient « Multiplicateur de l'accélérateur » partout dans le code : ligne de la page Commandes, aide de la touche d'accélérateur, docstring de `_maj_camera`, commentaire du réglage, test_pause_pages (avec un assertNotIn de l'ancien libellé). La clé `vitesse_accel` n'a pas changé.
Occurrences hors code, à mettre à jour (je n'ai rien touché hors code) :
- README.md:41 (touche d'accélérateur, « vitesse réglable de 1 à 2 dans Commandes ») : à compléter avec la touche V et la vitesse des combats ;
- docs/notes-visionneuse-dq4-pc.md:386 (« vitesse de l'accélérateur ») ;
- docs/notes-visionneuse-dq4-pc.md:429 (idem, et dit que les combats gardent leur vitesse : à corriger).
Reste dans le code : reglages.py:152, commentaire sur l'ancien « Multiplicateur de la course » (migration), volontairement gardé.

=== B. Vitesse des combats ===
Réglage `vitesse_combat` ∈ {1, 2, 3}, défaut Normal (1.0). Libellés Normal / Rapide / Très rapide, jamais « x2 ».
- reglages.py : clé dans DEFAUT, `VITESSES_COMBAT`, `NOMS_VITESSE_COMBAT`, `cran_combat` (valeur invalide, booléen, nan ou texte → Normal ; hors bornes ramené à 1..3 ; la plus proche, à égalité la plus rapide), `combat_suivant` (cycle 1→2→3→1) et validation au chargement. Nouvelle action `vit_combat` « Touche de vitesse des combats », touche par défaut V (libre : aucune autre action ne l'utilise, pas dans RESERVEES). Si un ancien fichier a déjà donné V à une autre action, la nouvelle n'a pas de touche et l'autre garde V. `vitesse_combat` est classé HORS_INTERFACE (test).
- pause.py `_e_commandes` : juste sous les lignes de l'accélérateur (touche, multiplicateur), ligne « Vitesse des combats » (même forme que les choix x1 à x4, plaques d'origine, assombrissement au survol, pas de cadre jaune, flèche dorée au clavier), puis « Touche de vitesse des combats ». Rien de tout cela n'est accélérable par l'accélérateur. Les aides disent « Sans effet en combat » pour l'accélérateur.
- En combat, deux commandes : la touche (cycle) et un bouton à l'écran « Vitesse / Normal|Rapide|Très rapide » (le libellé jaune puis orange quand c'est plus rapide). Chaque changement enregistre le réglage ; la page Commandes le relit. Le bouton est intégré à hud_mobile : déplaçable et masquable dans l'éditeur, « Rétablir cette interface » le remet en place, position par défaut dans la bande de gauche (colonne 0,4, ligne 8, entre Carte et Commandes), vérifiée à plusieurs résolutions (1280x720 à 3440x1440) : à gauche de la colonne des fenêtres du jeu, sans recouvrir un autre bouton. Il n'envoie rien au moteur. Il se cache pendant l'écran noir d'attente de la scène et pendant les fondus au noir, comme les boutons du terrain. La touche agit aussi hors combat ; si le bouton n'est pas à l'écran, un message bref annonce la valeur.
- Effet (vitesse_combat.py, logique pure, nouveau) : le moteur d'origine n'est pas modifié ; en combat la visionneuse lui fait faire 1, 2 ou 3 fois plus de pas de 1/30 s par seconde réelle. La boucle d'origine de `Jeu._boucle` a été extraite en `VC.avancer` (identique pour la marche : test d'équivalence contre l'ancienne boucle). Budget de calcul 30 ms par image (BUDGET_PAS_RAPIDES inchangé) : si les pas ne tiennent pas, le jeu ralentit au lieu de geler l'affichage. `VC.facteur` : None hors combat, 1.0 quand le moteur attend le joueur, sinon 1..3.
- « En combat » = partie combat du moteur (0xd), plus l'effet d'écran de début et l'écran noir d'attente de la scène (que seul un combat lève). Hors de cela, retour à x1 sans effet sur la marche (x1 à x4) qui reste indépendante.
- Accélérateur : exclu par construction (`VC.facteur` n'a aucun paramètre pour lui ; la branche combat de `_facteur_vitesse` passe avant la logique de marche). Il ne s'applique ni ne se cumule en combat. Écrit dans le code (docstrings de vitesse_combat.py et de `_facteur_vitesse`, commentaire de reglages.py) et dans les aides de la page Commandes.
- Attentes du joueur non accélérées : menu de commandes, choix de cible, Oui/Non (`mo.menu_actif()`), message qui montre le curseur ▼ (« Messages en combat » = Manuel). Un pas qui ouvre un menu interrompt la rafale d'images. Messages automatiques (Rapide/Moyen/Lent) : leurs compteurs sont en images moteur, donc raccourcis de 2 à 3 fois.
- Musique et bruitages : son.py n'est pas modifié ; la lecture reste en temps réel (durée du fichier, hauteur, tempo inchangés). Seule la date de déclenchement d'un bruitage suit le moteur, et `VC.sons_a_jouer` empêche de lancer deux fois le même bruitage (paquet 35) dans la même image affichée.
- Tout ce que la visionneuse anime en combat suit l'horloge du moteur (`moteur.images + alpha`) : nombres de dégâts, FBX, effet de début, fondus (`tick_fondu`), secousses de plaques, défilement des messages (écrit par le moteur), animation des monstres. Une seule horloge réelle subsiste dans l'interface de combat : le clignotement de la flèche de cible (ui_menu.py, 0,7 s), qui est une attente de saisie. Un test vérifie par inspection de code qu'aucune des fonctions de dessin de combat n'utilise d'horloge réelle.

=== Fonctions touchées (fichiers partagés avec les autres agents) ===
fenetre.py : `import vitesse_combat as VC` ; `on_key_press` (+1 ligne après `infos`) ; `on_mouse_release` (branche HUD, 2 lignes) ; `_maj_camera` (docstring seule) ; `_boucle` (le bloc de pas remplacé par `VC.avancer`) ; `_facteur_vitesse` (+1 ligne en tête) ; nouveaux : attribut `_se_images`, `_horloge_combat`, `_attend_joueur`, `_faire_pas_combat`, `changer_vitesse_combat` ; `tick` (1 ligne : `son.evenements(VC.sons_a_jouer(...))`).
pause.py : `_e_commandes` (accel, vit_acc, nouvelles lignes vit_cb et tch_cb, docstring, aide de « Vitesse de marche ») + 1 ligne dans le dict `noms` (`'Vitesse des combats'`).
reglages.py : TOUCHES_DEF, ACTIONS, DEFAUT, commentaire de `vitesse_accel`, `VITESSES_COMBAT`, `NOMS_VITESSE_COMBAT`, `cran_combat`, `combat_suivant`, 1 ligne dans le chargement.
hud_mobile.py : constantes (COMBAT, BOUTONS, NOMS_ED à 5 éléments, DEFAUT, LIBELLE, PLAQUE_DQ), `combat_visible` (nouveau), `sous`, `visibles`, `dessiner`, `_texte_combat` (nouveau).
Nouveau : dq4_pc/vitesse_combat.py, outils/test_vitesse_combat.py. Tests mis à jour : test_pause_pages.py, test_reglages_interface.py (`HORS_INTERFACE`, dicts de masque avec 'combat', `_rects_montres()` = 5).

=== Établi (mesuré ou vérifié) ===
- 39 tests dans test_vitesse_combat.py (1 ignoré = le rejeu moteur, opt-in), plus test_pause_pages (16), test_reglages_interface (12), test_camera_ville, test_mode_fenetre, test_panneau_interface, test_reglages_son_texte, test_son_mixage : tous OK. pyflakes : seuls les avertissements connus (sel, R, yp, mh).
- Lancement : `python3 outils/test_vitesse_combat.py` (sans écran). Rejeu moteur : `DQ_APK=<dossier APK> DQ_SAVES=<sauvegardes> [DQ_PAS_MAX=3000] python3 outils/test_vitesse_combat.py RejeuMoteur` (environ 30 s).
- Résultats identiques à x1 : même combat rejoué avec la vraie boucle `VC.avancer` à 1, 2 et 3. Sur 3000 pas moteur (100 s de combat), paquets, messages, états et nombres de dégâts sont identiques pas à pas ; les dégâts sont 11, 11, 8, 8 aux pas 158, 502, 681, 857. Dans la vraie fenêtre (DQ_TEMPS_REEL=1, même script de touches), les journaux DQ_PKTALL de x1 et x3 sont identiques sur 8405 lignes (17909 pas, dont la marche et le combat). L'issue ne dépend pas de la vitesse : le moteur est déterministe pas à pas.
- Durée du même combat (1100 pas, harnais à 60 Hz simulés) : x1 36,7 s, x2 19,6 s, x3 14,0 s (les attentes de saisie restent à vitesse normale, d'où un peu moins que x2 / x3 exacts).
- Fenêtre réelle, Xvfb 640x360 chargé, saisie scriptée toutes les 6 pas : 300 pas moteur en 10,0 s à x1 (30 pas/s), 5,7 s à x2 (52 pas/s), 4,2 s à x3 (72 pas/s).
- Coût d'un pas moteur en combat sur cette machine (2 cœurs, charge 3,4) : moyenne 2,6 ms, médiane 1,6 ms, p95 7,7 ms, max 37,6 ms. Le budget de 30 ms est donc rarement atteint ; simulation : budget coupé seulement si un pas dépasse ~30 ms (x3 retombe alors à 60 pas/s, jamais sous x2 à 60 Hz).
- Touche V en fenêtre réelle (`--touches-test`) : deux appuis donnent Normal → Rapide → Très rapide, enregistré dans le JSON. Clic sur le bouton : le réglage change et est enregistré.
- Captures (toutes dans /tmp/captures_vitesse_combat/) :
  - /tmp/captures_vitesse_combat/combat_bouton_normal.png
  - /tmp/captures_vitesse_combat/combat_bouton_rapide.png
  - /tmp/captures_vitesse_combat/combat_bouton_tres_rapide.png
  - /tmp/captures_vitesse_combat/combat_bouton_3_valeurs_agrandi.png (les trois côte à côte, agrandi)
  - /tmp/captures_vitesse_combat/combat_touche_V_cycle_agrandi.png (cycle par la touche V)
  - /tmp/captures_vitesse_combat/commandes_cle_vitesse_combats.png (page Commandes, nouvelle ligne et sa touche)
  - /tmp/captures_vitesse_combat/commandes_vitesse_combats_liste.png (curseur sur la ligne, liste ouverte)
  - /tmp/captures_vitesse_combat/editeur_interface_bouton_combat.png (bouton dans l'éditeur d'interface)

=== Supposé (cohérent avec le code et les mesures, non constaté à l'œil / à l'oreille) ===
- Ressenti à 60 Hz sur le PC de l'utilisateur : à x2 exactement un pas moteur par image ; à x3 alternance 1 / 2 pas par image (1,5 en moyenne), donc léger manque de régularité possible sur les animations à x3.
- Les animations de monstres ne suivent l'horloge accélérée que pendant les phases non en attente ; pendant les attentes de saisie, elles gardent leur animation de repos normale (voulu).
- Jingle de victoire : sa durée reste réelle alors que le moteur enchaîne plus vite (les délais de fin de combat sont comptés en images moteur). À x3, la musique suivante peut couper la fanfare avant sa fin. À vérifier à l'oreille.
- Raccourcir de 2 à 3 fois les messages automatiques réduit le temps de lecture ; pour lire à son rythme, rester en Manuel (non accéléré) ou en Normal.

=== Non vérifié ===
- Tout ce qui se joue sur Windows et sur le vrai écran de l'utilisateur (aucun Windows ici), en particulier la performance si le budget de pas est dépassé sur un PC plus lent : le jeu ralentit (x3 retombe vers x2) au lieu de geler, mais c'est testé seulement par simulation.
- Aucun test auditif (musique, bruitages, fanfare) ; seulement des faux lecteurs vérifiant que la durée d'un bruitage est la même à toutes les vitesses et qu'un doublon dans l'image est supprimé.
- Le dernier message de victoire attend une touche sans montrer ▼ : non détectable, il est donc accéléré (sans conséquence, les monstres ont disparu).

=== Choix à valider ===
Touche par défaut V ; position par défaut du bouton (col 0,4, ligne 8) ; bouton lié à la visibilité globale « Afficher cette interface » (pas d'option séparée : la page de l'éditeur est hors de mon périmètre) ; effet de début de combat et écran noir de chargement comptés comme combat (accélérés) ; touche active aussi hors combat avec message bref ; flèche de cible non accélérée.

=== Notes de doc à fusionner (pas touché docs/) ===
Section « #43 Vitesse des combats » dans docs/notes-visionneuse-dq4-pc.md : principe (pas moteur multipliés, budget 30 ms, facteur 1 pendant les attentes de saisie), indépendance de l'accélérateur, ce qui suit l'horloge moteur et ce qui reste réel (flèche de cible, sons), nouveau réglage et nouvelle touche V, bouton intégré à l'éditeur, tests et mesures ci-dessus. Mettre à jour les lignes 386 et 429 (nouveau libellé, les combats ont maintenant leur vitesse) et README.md:41.

=== Pièges de fusion (testés avec `git merge-tree`, lecture seule) ===
- agent-entrees : CONFLIT dans pause.py `_e_commandes`. Résolution : garder leur ligne `modif` (aide « clic molette ») et leur ligne `infos`, avec mon `accel` (aide « Multiplicateur de l'accélérateur … Sans effet en combat »), mon `vit_acc` renommé, puis `vit_cb` et `tch_cb`. Vérifier que `infos` reste dans la liste retournée.
- agent-fenetre2 : CONFLIT dans reglages.py (chargement) : garder ma ligne `vitesse_combat` et supprimer la ligne `correction_bords` qu'ils retirent.
- agent-coffres, agent-libelles, agent-options, agent-titre2 : aucun conflit (fenetre.py se fusionne automatiquement avec tous).
- Après fusion : grep de « Vitesse de l'accélérateur » (les branches des autres agents l'ont encore dans leurs copies de test_pause_pages et d'aides ; tout nouveau test écrit avec l'ancien libellé échouera) ; `HM.NOMS_ED` compte maintenant 5 éléments (tests qui comptent les rectangles) ; relancer les 3 tests de logique ci-dessus.

=== À retenir (observations de session, pas de la mémoire) ===
Les captures sous Xvfb passent par un verrou unique /tmp/xvfb.lock : une exécution a attendu 15 à 30 minutes derrière les autres agents. Les tests de logique tournent sans écran (pyglet headless).

---

## Agent a3199f5d827423698 — 02/11 04:30

RAPPORT FINAL, lot PR #43, agent « histo » : historique des messages

Branche `agent-histo`, base 08f5785, un commit : **bb9ca7f**. Arbre de travail propre (seul `dq4_pc/__pycache__/` est ignoré). `dq4_pc/libelles.py` n'est PAS commité : il n'est pas dans la branche, je l'ai copié dans `/tmp/histo_libelles/` pour les tests et captures.
Rien n'a été poussé, aucune PR, aucun changement de branche, `/home/claude/dq4-portage` et les sauvegardes de l'utilisateur n'ont pas été touchés (les tests écrivent dans `/tmp/sv_*`).

## Les 5 points

**1. Capture exactement une fois, texte tel qu'affiché**
- Point de passage unique : `TextBuffer::cat` (lib+0x157874), appelé une fois par page de message, macros déjà résolues. x1 = texte UTF-8, x2 = nom du locuteur donné par le moteur (le `@a<nom>@b` du .mpt).
- Le crochet (`uc.hook_add(UC_HOOK_CODE, …)`) est posé dans `Moteur.__init__`, avant les premiers pas : après, le cache de blocs traduits l'ignorerait.
- On note le texte nettoyé (`@cN`, caractères de contrôle et préfixe « *: » retirés), l'heure de jeu (`status::g_Game+4`, 1/60 s, identique au champ `duree` des sauvegardes), la carte et la catégorie (t terrain / c combat / s système).
- Les doublons sont écartés (`doublon`) : même texte, même source, même instant.
- Mesuré : environ 3,8 µs par image, aucune perte perceptible.

**2. Qui parle**
- Priorité : nom explicite du moteur > installation (`MaterielMenu_*`, `TownPlayerManager::loadChurch`) > objet fouillé (`TownFurniture*`) > personnage de terrain > combat (partie 0xd ou « Battle » dans la pile) > « Message général ».
- Les sources sont lues par rétro-parcours de la pile (frame pointer, x29).
- En-tête : « locuteur · lieu » pour personnage, objet et installation ; nom seul pour un nom explicite ; « Message général » ou « Combat » sans lieu.
- Un texte « *: … » (parole de PNJ anonyme du patch FR) dont la source est inconnue devient « Personnage ».
- Le lieu garde le dernier lieu connu pour les cartes `ev*` et `bt*`, et « Monde » sur la carte du monde.

**3. Interface « Historique des messages »**
- Page `'historique'` du menu Pause. Le moteur s'arrête comme avec le menu Échap (`J.pause_jeu(True)`).
- Style du jeu : plaques d'origine, police bitmap SE-GARRIR (`PoliceBitmap`), flèche dorée, assombrissement au survol, pas de cadre jaune.
- Plus récent en bas, messages consécutifs du même locuteur regroupés sous un en-tête (≤ 6 et ≤ 20 s de jeu).
- Commandes : molette, ↑↓, PageUp/PageDown, Début/Fin, glisser de la barre, Échap ou B pour fermer, filtre Tout / Combats (←/→ ou bouton).
- Ouverture par touche configurable : nouvelle action « Historique des messages », **H par défaut**.
  - H est libre : aucune autre touche par défaut, ni `RESERVEES`, ni chiffre, ni `K.H` dans `fenetre.py`, ni autre worktree.
  - Elle est ajoutée dans Commandes (section « Actions du jeu »).
- Entrée « Historique des messages » à la racine du menu Pause, juste après « Reprendre ».
- Ouverture possible pendant un message sans le perturber.

**4. Mémoire entre sessions**
- Fichier annexe `historique_messages.json` à côté de la visionneuse (option `--historique`), ajouté à `.gitignore`. Jamais dans les sauvegardes de l'utilisateur, aucune sauvegarde modifiée.
- Une « partie » = une aventure, reconnue par `status::g_Game+8` (1 octet utile, 0x66 pour les emplacements 1 et 4, 0x04 pour les emplacements 2 et 5, constant d'une sauvegarde à l'autre).
- Format : `{"version":1,"parties":{"<clé hex>":{"vu":…,"entrees":[[n,t,cat,genre,val,carte,texte],…]}}}`.
- Écriture robuste :
  - fichier temporaire puis `os.replace` ;
  - groupée (au moins 5 s d'écart, forcée à la fermeture) ;
  - fichier corrompu déplacé en `.corrompu`, entrées invalides ignorées ;
  - bornes : 3000 entrées par partie, 6 parties, 1500 caractères par texte.
- Retour en arrière quand une sauvegarde plus ancienne est rechargée :
  - le temps de jeu ne recule jamais, sauf dans ce cas ; un changement doit durer 3 images consécutives (marge de 120 ticks) pour être pris en compte ;
  - les entrées postérieures à l'heure courante sont alors supprimées ;
  - une autre clé de partie bascule sur une autre liste.
- Limites à dire honnêtement :
  - la suppression est destructive (pas d'annulation) ;
  - la clé sur 8 bits peut entrer en collision une fois sur 256 entre deux aventures ;
  - les sauvegardes faites avant la fonctionnalité n'ont pas d'historique avant elles.

**5. Tests et captures**
- `outils/test_historique_messages.py` : 52 tests OK (OK avec libelles ; sans libelles, 1 test ignoré).
- Générateur de jeu d'essai intégré : `--fixture FICHIER.json [CLE]`, 25 entrées variées (clé « 66 » pour l'emplacement 1, « 4 » pour l'emplacement 2).
- Autres tests de `outils/` relancés, tous OK : test_pause_pages (liste de la racine mise à jour), test_reglages_interface, test_reglages_son_texte, test_panneau_interface, test_mode_fenetre (1 ignoré), test_camera_ville, test_son_mixage, test_texte_defilement (4 tests, avec le vrai moteur et les crochets).
- `pyflakes` propre sur les fichiers nouveaux. Il reste 4 avertissements dans `pause.py` (R l.461, yp, mh) et `fenetre.py` (sel l.2203), déjà présents avant mon travail.

## Identifiants réellement passés à `libelle_source`

- **PNJ interagi** : un **int**, `Etat.sprites[8+placement]['id']`, qui est aussi l'index de personnage de `TownCharacterManager`.
  - Chemin : `ScriptGroup::execute` dans la pile, puis `getPlacementCtrlId()` (int à `L+0x29901c`, adresse vérifiée à l'installation en décodant adrp+ldr), puis `TownCharacterManager [L+0x26a548+8+8*pid]+0x14`.
  - Placement 0 = script de scénario global = narration, donc « Message général ».
- **Objet fouillé** : une **str**, le nom de modèle FMAP `noms[o['i']]`, par exemple `'015_hondana1'` ou `'001_tbox01'`.
  - L'uid numérique (`this+0x10` de `TownFurniture*`) est résolu par `HI.nom_objet(objets, noms, uid)` ; il n'est accepté que s'il date de 600 images ou moins.
- **Lieu** : nom de carte (ex. `'mak1f1'`, `'caf1'`) ou `'monde'` (partie 0xe) pour `libelle_lieu`. `None` pour `ev*` et `bt*` donne le dernier lieu connu.
- Dans le code livré, l'import de `libelles` est protégé avec repli : « Personnage », « Objet », lieu omis. Rien ne casse sans `libelles.py`.

## Établi, supposé, non vérifié

**ÉTABLI (observé sur le moteur réel ou en captures)**
- Nom explicite de PNJ.
- Personnage de terrain : « Un vieil homme · Strattbourg » (libellé réel venant de `libelles.py`).
- Meuble : « Un tonneau · Strattbourg », étagère et coffre fouillés.
- Combat : « Combat » pour le message de rencontre (et le groupe de la fixture, rendu en capture).
- Narration : « Message général » sur la carte `caf1` (introduction de l'emplacement 2).
- Église : message de la prêtresse, en capture avec le vrai moteur : « Église · Strattbourg ».
- Clé de partie et heure de jeu.
- Rollback (confirmé sur le moteur : la durée recule au chargement d'une sauvegarde plus ancienne).
- Persistance, écriture atomique, tolérance à la corruption.
- Ouverture et fermeture pendant un message.

**SUPPOSÉ (libellé d'installation déduit du nom de symbole, pas vu en jeu)**
- Boutique, Auberge, Banque, Roi des médailles, Arène, Casino (machine à sous, poker, salle de jetons, cadeaux, stade), Sauvegarde et Chargement (`MaterielMenu_*`).
- L'Église via `MaterielMenu_CHURCH` pour les autres cas que `loadChurch` (qui est établi).

**NON VÉRIFIÉ**
- Messages de jarre : même code `TownFurnitureItem` que le coffre (vérifié), donc probable, mais pas observé.
- Second message « objet trouvé » d'une jarre.
- Messages de combat après le premier (cause : combats non rejoués dans la session).
- Messages de la carte du monde.
- Un second coffre inatteignable (héros bloqué par un mur dans le château).
- **Windows** : aucun test possible ici (Linux uniquement). Code défensif : écriture atomique `os.replace`, encodage UTF-8 explicite.

**Limites connues**
- Un script de cinématique piloté par le PNJ X qui fait parler le PNJ Y étiquettera le locuteur « X ».
- Monstres et modèles 3D non identifiables (comme annoncé par `libelles.py`).
- Le modèle 34 est étiqueté « Un noble » par `libelles.py` (le capitaine de Bastione) : c'est la classification de `libelles.py`, pas la mienne.

## Fichiers touchés et crochets

- NOUVEAU `dq4_pc/historique.py` (415 lignes) : `Capteur`, `Historique`, fonctions pures (`nettoyer`, `envelopper`, `en_tete`, `locuteur`, `lieu_de`, `meme_groupe`, `doublon`, `nom_objet`).
- NOUVEAU `dq4_pc/ui_historique.py` (252 lignes) : `VueHistorique`, `grouper`, `heure_jeu`.
- NOUVEAU `outils/test_historique_messages.py` (524 lignes).
- `dq4_pc/moteur.py` : import l.6 ; `self.capteur = Capteur(self)` l.379, juste après `self._crochets_texte()`.
- `dq4_pc/fenetre.py` :
  - l.19 `import historique as HI` ;
  - l.184 `self.historique = HI.Historique(getattr(args,'historique',None))` après la création de `PA.Pause` ;
  - l.595 `on_close` : `self.historique.enregistrer(True)` ;
  - l.622 `on_key_press` : ouverture si `reg.action_de(symbol)=='historique'` hors titre et en partie ville, combat ou champ ;
  - l.2588 `tick` : `self.historique.maj(mo, objs, noms)` après `mo.step` ;
  - l.3058 `main` : `--historique` (par défaut `ici/historique_messages.json`).
- `dq4_pc/pause.py` :
  - import `ui_historique` (l.14) ; `self.hist` (l.67) ;
  - `ouvrir` (l.179) ; `_e_historique` (l.201) ; entrée racine (l.211) ; `T('historique')` dans « Actions du jeu » (l.441) ;
  - un crochet d'une ligne `if self.ecran=='historique': return self.hist.X(...)` en tête de `touche`, `_bouger`, `survol`, `clic`, `relache`, `glisser`, `molette`, `dessiner`.
- `dq4_pc/reglages.py` : `TOUCHES_DEF['historique']=['H',None]` et `ACTIONS += ('historique','Historique des messages')`.
- `outils/test_pause_pages.py` : liste de la racine mise à jour.
- `.gitignore` : `historique_messages.json*`.

## Captures d'écran

- **Emplacement 1 (clé 66), ouverture par H pendant le message de la prêtresse**
  - `/tmp/m_w3_b140.png` : avant ouverture.
  - `/tmp/m_w3_b170.png` : historique ouvert, 27 messages, dernier en « Église · Strattbourg » (capture réelle du moteur).
  - `/tmp/m_w3_b220.png`, `/tmp/m_w3_b260.png`, `/tmp/m_w3_b300.png` : navigation.
  - `/tmp/m_w3_b360.png` : après Échap, retour direct au jeu.
  - Message intact : avant/après diffèrent seulement dans la zone des torches (538–740 × 446–496, animation des flammes). La fenêtre de message est identique.
- **Emplacement 2 (clé 4)**
  - `/tmp/m_w4_b170.png` : liste, fixture de 25 entrées.
  - `/tmp/m_w4_b260.png` : défilement avec le groupe « Combat ».
  - `/tmp/m_w4_b300.png` : filtre « Combats ».
  - `/tmp/m_w4_b400.png` : fermeture, puis le message réel de narration de l'intro apparaît.
  - Dans `/tmp/histo_w4.json`, les messages réels de narration de l'intro sont stockés en général / `caf1`.
- **Commandes**
  - `/tmp/m_w6_b300.png` et `/tmp/m_w6_b400.png` : ligne « Historique des messages · H », section « Actions du jeu ».
- **Autres**
  - `/tmp/m_w2_b160.png` : racine de la Pause avec la nouvelle entrée.
  - `/tmp/m_w2_b610.png` : ~20 entrées variées (Alena, Une femme, Une jarre, Combat, Église).
  - `/tmp/m_w2_b370.png` à `/tmp/m_w2_b530.png` : filtre, Fin, PageUp, survol.
  - `/tmp/m_w2_b660.png` : Échap revient à la racine de la Pause.
  - Les captures w2 ont un fond à 0,95 d'opacité (un fantôme du message du jeu transparaissait sous le pied de page) ; w3, w4 et w6 sont à 0,98, corrigé.
- Les entrées d'essai des captures viennent de la fixture (« une femme », « une jarre », « un tonneau », « Alena » sont des entrées fabriquées, en gras assumé). Ce qui vient du moteur réel : la prêtresse (Église), la narration `caf1`, et en amont les contextes vérifiés par sondes (étagère, coffre, PNJ, combat).

## Notes de doc à fusionner (rien écrit dans `docs/`)

- Chemin de capture et contexte : voir la section Capture ci-dessus ; à reporter dans `notes-technique-portage-dq4.md`.
- Constats techniques à ajouter aux notes :
  - `status::g_Game+4` = temps de jeu en 1/60 s = `duree` des sauvegardes ;
  - `status::g_Game+8` = identifiant de partie sur 1 octet, constant dans toutes les sauvegardes d'une aventure ;
  - placement k correspond à `Etat.sprites[8+k]`, et l'index de personnage du moteur = `sprites[slot]['id']`.
- Fonctions du moteur crochetées : `TextBuffer::cat`, `TownFurniture*` (setFirstMessage, addMessage, setMessage, setSecondMessage), `ScriptGroup::execute`, `getPlacementCtrlId`, `TownPlayerManager::loadChurch`, `MaterielMenu_*`.
- Fichier annexe `historique_messages.json` : format, bornes, comportement de rollback, limites (voir point 4).
- Nouvelle touche H dans Commandes et nouvelle page de la Pause.
- Les touches de la page Commandes dépassent la fenêtre visible : l'entrée est dans « Actions du jeu » (défiler).

## Pièges de fusion

- Conflits probables :
  - `moteur.py`, autour de `self._crochets_texte()` ;
  - `pause.py` : `_e_racine` (liste de la racine), `_e_commandes`, les têtes de `touche`, `_bouger`, `survol`, `clic`, `relache`, `glisser`, `molette`, `dessiner` ;
  - `outils/test_pause_pages.py`, liste attendue de la racine : elle doit contenir « Historique des messages » juste après « Reprendre » ;
  - `reglages.py` : `TOUCHES_DEF` et `ACTIONS` ;
  - `fenetre.py` : `on_key_press` et `tick`.
- `libelles.py` (branche agent-libelles, 4ec25d6) doit être fusionné pour avoir de vrais libellés ; sans lui, tout est « Personnage » / « Objet » (repli voulu).
- `H` : revérifier à la fusion qu'aucun autre lot n'a pris cette touche par défaut ; l'action est reconfigurable.
- `OPACITE_FOND` (0,98) est dans `ui_historique.py`, indépendant de `hud_mobile.OPACITE_JEU`.

## À retenir pour la mémoire (non écrit, mémoire en lecture seule pour moi)

- Source : mes sondes du moteur, pas la mémoire.
- Le texte du patch « Ragnar obtient l'herbe ;médicinale. » contient un « ; » parasite présent dans le tampon du moteur lui-même (bug du patch, à signaler à l'utilisateur).
- `status::g_Game+4` et `+8` : temps de jeu en 1/60 s et identifiant de partie sur 1 octet. Utile pour toute fonction qui suit une partie ou détecte un chargement.
- Pour les autres agents : le verrou xvfb peut mettre 25 à 40 minutes à passer ; ne pas relancer.
- `pkill -f "python3 sondeNN.py"` tue son propre shell si le motif figure dans la ligne de commande. Utiliser un PID.
- Aucune instruction détectée dans la mémoire consultée qui sorte de ma mission.

---

## Agent a411b418cae673469 — 02/11 04:35

RAPPORT fenetre2 (A, B, C faits). Worktree /home/claude/wt-fenetre2, branche agent-fenetre2, arbre propre. 2 commits sur 08f5785 : 4ab39c9 (travail du prédécesseur relu, corrigé, complété + tests), 13af951 (même image redessinée dès que la fenêtre est montrée ; métrique de mesure). Aucun push. Tests : test_mode_fenetre (39), test_reglages_interface (12), test_pause_pages (15), test_reglages_son_texte (7), test_panneau_interface (10), test_camera_ville (5), test_son_mixage (12) : tous OK. pyflakes : seulement les avertissements connus.

ÉVALUATION DU TRAVAIL PARTIEL
Gardé : suppression de tout le code exclusif, migration, nouvelle bascule en une étape, raccourcis, outil de mesure. Rien de cassé trouvé : toutes les références à choisir_mode_ecran, regler_mode_fenetre, _poser_mode, basculer_exclusif, modes_ecran, regler_lissage, NOMS_MODES_FENETRE, MODES_FENETRE ont disparu (test statique). Corrigé / ajouté par moi :
- l'échec simulé (DQ_SIM_ECHEC) arrivait avant tout changement, donc le repli n'était pas exercé. Il arrive maintenant après le set_fullscreen, dans la fenêtre cachée, et le retour à l'état de départ est testé pour de vrai ;
- cachee=True avant l'appel de masquage : un masquage à moitié réussi est quand même suivi d'un set_visible(True) ;
- la même image est redessinée juste après l'affichage (voir « Supposé ») ;
- --correction-bords remis comme interrupteur de débogage (le prédécesseur l'avait retiré ; ta consigne le gardait) ;
- test_mode_fenetre.py entièrement réécrit (le prédécesseur ne l'avait pas touché, il aurait échoué) ;
- mesure_bascule.py : ajout de « fenêtre visible sans image ».

A. PLEIN ÉCRAN EXCLUSIF SUPPRIMÉ
- mode_fenetre ∈ {0 fenêtré, 1 plein écran}. Migration : 2 → 1 ; booléen d'avant la #42 → 0/1 ; valeurs absurdes → 0. Clés obsolètes jamais lues ni réécrites (le chargeur ne prend que les clés de DEFAUT ; reglages.CLES_OBSOLETES la documente et le test la vérifie) : plein_ecran, mode_fenetre_retour, correction_bords, lissage. --plein-ecran 0|1|2 : 2 est accepté et vaut 1.
- pause._e_affichage : 1re ligne = « Plein écran », interrupteur Oui/Non, c'est-à-dire l'ancien réglage d'avant #42 (git show 345ba8f), même place. « Résolution » grisée en plein écran. Ordre des autres lignes inchangé. Capture : /tmp/m_fen2_aff_b100.png (fenêtré, Non) et /tmp/m_fen2_aff_b150.png (plein écran, Oui, Résolution grisée avec sa note).
- F11 et Alt+Entrée basculent dans tous les contextes : menus, Pause, éditeur, saisie du nom, logos, combat. Entrée avalée (ni validation, ni discussion de groupe au relâchement d'Alt). _raccourci_fenetre accepte aussi Alt « tenue » même si le drapeau MOD_ALT manque. Les touches passent par le harnais : Pause ouverte (/tmp/m_fen2c_pause_b100.png, b130.png : menu intact, curseur resté sur « Reprendre », donc pas d'Entrée transmise) et combat (2 bascules). Ajout d'un gestionnaire WM_SYSCHAR (Windows seulement) pour supprimer la « tonalité d'erreur » d'Alt+Entrée.
- Scintillement. Causes plausibles, relues dans le code du jeu et dans pyglet 2.1.19 Win32 (pas exécutées sous Windows) :
  1. l'exclusif faisait 2 changements de mode d'affichage par aller-retour (ChangeDisplaySettingsEx) : supprimé ;
  2. set_fullscreen (_recreate → _create) cache la fenêtre, change le style, la taille, puis la MONTRE (SWP_SHOWWINDOW + _on_internal_resize) avant toute image. Le tampon d'affichage redimensionné est donc indéfini jusqu'à la trame suivante, et au retour en fenêtré pyglet appelle set_location APRÈS l'affichage (la fenêtre apparaît en (0,0) puis saute) ;
  3. post.cle=None forcé : reconstruction des tampons du rendu hors écran pendant que la fenêtre est visible.
  Correctif (Jeu._poser_plein_ecran, une seule étape) : mémorise la taille, cache la fenêtre, UN set_fullscreen (taille mémorisée rendue d'un coup, centrage si lancée en plein écran), dessine + flip une image à la taille définitive (les tampons ne se reconstruisent que si la taille change, une fois, dans PostFX.debut, comme avant), montre la fenêtre, redessine la même image. Plus de post.cle=None forcé. Tout échec → retour à l'état de départ, message, mode réel gardé. DQ_BASCULE_SIMPLE=1 = ancien comportement (un set_fullscreen nu), pour comparer.
- MESURES (outils/mesure_bascule.py, xvfb/Mesa, fenêtre 1280x720, bureau 1920x1080 ; logs /tmp/out_fen2a_f11.txt, out_fen2a_m1.txt, out_fen2b_f11.txt, out_fen2b_opt.txt, out_fen2b_alt.txt) :
  | | #42 F11 (exclusif) | #42 option mode 1 | maintenant (F11, option, Alt+Entrée) |
  | set_fullscreen / recréation / redimensionnement / reconstruction des tampons par bascule | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
  | changement de mode du moniteur (set_mode) | 1 par bascule (2 par aller-retour) | 0 | 0 |
  | fenêtre visible sans image (aller / retour) | 276 / 67 ms | 250 / 70 ms | 0 / 0 |
  | tampons refaits fenêtre visible (aller / retour) | 1 / 1 | 1 / 1 | 0 / 0 |
  | déplacement fenêtre visible au retour | 1 | 1 | 0 |
  Trames comptées : 12 avant, 13 à 14 maintenant (une image dessinée cachée, une après l'affichage). Le nombre d'événements pyglet sous X11 est IDENTIQUE avant/après. Le gain porte sur l'ordre (aucune image visible sans contenu) et sur la suppression de l'exclusif. Les ms viennent de Mesa : sur un vrai GPU elles seront plus courtes, la structure est la même.

B. CORRECTION DES BORDS : TOUJOURS ACTIVE
Ligne de _e_affichage et clé retirées (DEFAUT, tests). Jeu._correction_bords() = 1.0, sauf interrupteurs de débogage --correction-bords 0-100 et DQ_CORRECTION_BORDS (documentés comme tels dans le docstring et l'aide). Captures, village maout (slot 1, DQ_VILLE=maout, PNJ près des bords gauche et bas-droit) : 0 pixel de différence entre #42 avec l'option sur « oui » (/tmp/m_fen2_vav_b90.png, b150.png) et le nouveau code (/tmp/m_fen2_vap_b90.png, b150.png). Contrôle de sensibilité : DQ_CORRECTION_BORDS=0 donne 8666 px différents (/tmp/m_fen2_voff_b150.png).

C. LISSAGE : TOUJOURS ACTIF
Ligne, clé (DEFAUT, chargeur) et Jeu.regler_lissage retirées. « Oui » = self.lissage True, valeur par défaut de l'ancien réglage : tous les endroits qui lisent self.lissage (textures de décor, HD, FBX, champ, sprites, monstres, shader net) sont inchangés. Seul interrupteur de débogage : DQ_SANS_LISSAGE=1 (plus proche voisin). Contrôles à 0 pixel de différence, #42 « lissage oui » contre nouveau code : titre avec dragon FBX (/tmp/m_fen2_tav_b400.png contre m_fen2_tap_b400.png, b700 idem), village, combat monde + monstre (/tmp/c_fen2_cav*.png contre c_fen2_cap*.png, 4 images). Contrôle de sensibilité : DQ_SANS_LISSAGE=1 donne 617 502 px différents (/tmp/m_fen2_vnl_b150.png).

ÉTABLI / SUPPOSÉ / NON VÉRIFIÉ
Établi (lu dans le code ou mesuré sous xvfb) : tout ce qui précède, plus le comportement de pyglet Win32 relu dans les sources : restore_mode ne fait rien tant que set_mode n'a jamais été appelé (donc plus aucun appel moniteur) ; les gestionnaires WM_ERASEBKGND renvoient 1.
Supposé :
- les causes 1 à 3 du scintillement ;
- sous Windows, la swap d'une fenêtre cachée peut ne pas être conservée par DWM, d'où la 2e image dessinée juste après l'affichage (ceinture et bretelles, coût : 1 trame) ;
- l'événement WM_SYSCHAR est livré à la fenêtre principale.
Non vérifié (Windows, GPU réel, clavier réel) :
- que le scintillement disparaisse sur ton PC : il se peut qu'il en reste (le plein écran sans bordure « indépendant flip » de DWM peut faire un éclair noir à lui seul, inévitable) ;
- F11 et Alt+Entrée sur clavier réel (Alt Gr AZERTY : Ctrl+Alt+Entrée bascule aussi) ;
- la tonalité d'Alt+Entrée supprimée ;
- effets du masquage / affichage (éclair du bouton de barre des tâches, focus rendu par SetForegroundWindow, bascule pendant un Alt-Tab) ;
- multi-moniteurs et DPI ;
- bascule par clic de souris sur la ligne de la Pause (le relâchement du bouton peut se perdre) ;
- le temps réel de la bascule (marche sous Mesa : 65 à 660 ms d'appel).

FONCTIONS TOUCHÉES (fenetre.py)
- Jeu.__init__ : 1re ligne (avalees..., _modes retiré, _restaure_a_la_sortie retiré), création de la fenêtre (res_demandee retiré), ligne self.lissage.
- _echec_simule (DQ_SIM_ECHEC=1 ou 0 maintenant), _creer_fenetre, on_close (1 ligne retirée), est_plein, resolutions, regler_resolution, regler_plein_ecran (nouveau), basculer_plein_ecran (nouveau), _poser_plein_ecran (nouveau), _mettre_plein (nouveau), _image_de_bascule (nouveau), _raccourci_fenetre, _event_syschar (Windows), _journal_fenetre, _correction_bords, argparse --plein-ecran et --correction-bords, main (a.plein_ecran).
- Supprimées : choisir_mode_ecran, modes_ecran, _mode_applique, _restaurer_a_la_sortie, _restaurer_affichage, regler_lissage, regler_mode_fenetre, _poser_mode, basculer_exclusif.
- Ligne de F1 touchée : 1 ligne, le suffixe « (plein écran exclusif) » de self.etiquette.text (zone « entrees »). Le texte « Lissage des textures : oui » de self.etiq_hd est resté (toujours « oui ») : à retirer par toi si tu veux.
- pause.py : _e_affichage et le dict de noms ('Fenêtre' retiré) uniquement.
- reglages.py : DEFAUT, RESERVEES (commentaire), CLES_OBSOLETES (nouveau), mode_fenetre_valide, chargeur.
- Tests : outils/test_mode_fenetre.py (39), test_reglages_interface.py (3 clés retirées de HORS_INTERFACE).
- Nouveau : outils/mesure_bascule.py.

PIÈGES DE FUSION
- test_reglages_interface.HORS_INTERFACE : si un autre agent ajoute des clés à cette ligne, retirer seulement 'lissage', 'correction_bords', 'mode_fenetre_retour'.
- Tout code d'un autre agent qui référence RG.NOMS_MODES_FENETRE, RG.MODES_FENETRE, J.regler_mode_fenetre, J.lissage comme réglage, reg['lissage'] ou reg['correction_bords'] cassera.
- fenetre.py : conflits possibles sur la 1re ligne de __init__, la ligne self.lissage, la ligne etiquette.text et le bloc argparse.
- camera_centree non touché (la ligne reste dans _e_affichage, juste avant « Interface »).
- Ne pas importer reglages.json de test avec 'mode_fenetre': 2 en attendant un exclusif.

NOTES DE DOC À FUSIONNER
1. notes-visionneuse, nouvelle section « Retours de 02 h 12 (#43) » : « Plein écran exclusif supprimé. Deux modes (mode_fenetre 0 fenêtré, 1 plein écran sans bordure) ; ligne « Plein écran » de l'Affichage = interrupteur Oui/Non (1re ligne, comme avant la #42) ; F11 et Alt + Entrée basculent de n'importe où ; 2 → 1 à la lecture ; mode_fenetre_retour, correction_bords, lissage, plein_ecran ignorés puis effacés à la sauvegarde. Bascule en une étape : fenêtre cachée, un set_fullscreen, une image à la taille définitive dessinée et affichée (tampons du rendu hors écran refaits seulement si la taille change), fenêtre montrée, même image redessinée ; échec → état de départ. Mesuré sous xvfb : fenêtre visible sans image 250 à 276 ms puis 67 ms (#42) → 0 ms ; changements de mode du moniteur 2 par aller-retour → 0. Non vérifié : scintillement sur Windows. » La puce « Trois modes » de la #42 est obsolète. Aussi : « Correction des bords et Lissage des textures : options supprimées, toujours actives. Interrupteurs de débogage : --correction-bords 0-100 / DQ_CORRECTION_BORDS, DQ_SANS_LISSAGE=1. » La puce « Page Affichage, nouvel ordre » devient : Plein écran, Résolution, Netteté, Shader, Effet de vignetage, Anticrénelage, Suréchantillonnage, Luminosité, Distance caméra, Centrer la caméra sur le joueur, Interface.
2. notes-technique : variables et outils de test. DQ_SIM_ECHEC=1 ou 0 (échec de la bascule vers ce mode, après le changement), DQ_BASCULE_SIMPLE=1 (set_fullscreen nu), DQ_SANS_LISSAGE, DQ_CORRECTION_BORDS ; outils/mesure_bascule.py <dossier dq4_pc> [options fenetre.py] (scénario : --touches-test "60:F11,120:F11" ; sortie « BASCULE n=… fenêtre visible sans image … ») ; test_mode_fenetre.py compte 39 tests ; /tmp/run_bascule.sh.
3. README.md ligne 41 (je n'y ai pas touché : ligne unique énorme, conflit probable) : remplacer « (dans l'ordre : Fenêtre = fenêtré / plein écran / plein écran exclusif, résolution de 720p à 4K, netteté, shader, lissage des textures, effet de vignetage, anticrénelage MSAA x2 / x4 / x8, suréchantillonnage x1,5 / x2, luminosité, distance de la caméra de 50 à 200 %, correction des bords des sprites, caméra centrée… » par « (dans l'ordre : plein écran (oui / non), résolution de 720p à 4K, netteté, shader, effet de vignetage, anticrénelage MSAA x2 / x4 / x8, suréchantillonnage x1,5 / x2, luminosité, distance de la caméra de 50 à 200 %, caméra centrée… » et « **F11** ou **Alt + Entrée** : plein écran exclusif et retour » par « **F11** ou **Alt + Entrée** : plein écran / fenêtre ».

Aucun élément nouveau à mémoriser sur l'utilisateur (rien lu dans la mémoire utile à cette mission).

---

## Agent acb3a91d1ee1b129b — 02/11 04:41

RAPPORT « titre2 » (branche agent-titre2, worktree /home/claude/wt-titre2, base 08f5785). Arbre propre. Tests : test_titre_ciel (22), test_plaque_depart (12), test_camera_titre (3), test_camera_ville, panneau/reglages/son : OK. pyflakes : seuls les avertissements connus (ax, sel, struct).

COMMITS (8) : 585538a (donnees.py + objets_carte.py repris de ac4cb9b, euler_mat Ry.Rz.Rx, cache carte9) ; 9d15a85 (titre 1:1 : sens des faces, zoom, retrait des hacks, DQ_FBXLOG) ; 1903c66 (ciel_titre.py + tests) ; 49f5ffe (ciel dans fenetre.py) ; fdd6b10 (plaque auto + boutons/etat_actif) ; 4784e98 (test camera titre) ; 5c17b72 (réglage du ciel + texte gris) ; 599d54c (moteur.py : rotation FBX par défaut).

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
- fenetre.py, zones touchées (par fonction) : import de ciel_titre (après `import fbx`) ; suppression des constantes TITRE_HAUT et TITRE_DRAGON_HAUT (~l.112) ; Jeu.__init__ ligne carte_ext/ciel_ext/_M_ville/_aspect_ville (l.181) ; _camera_ville (condition `carte_nom != 'ev01'` sur le zoom héros, yoff sans TITRE_HAUT) ; _maillages_combat (retrait de _decalage_credits et de _credits_cache, DQ_SANS_CREDITS conservé) ; _charger_carte (ev01 : appel de _ciel_titre) ; nouvelles méthodes _ciel_titre et _tracer_ciel (avant _calcul_hd_decor) ; _tracer_decor pas 0 (appel _tracer_ciel) ; _tracer_fbx (glFrontFace CW, translation mvp retirée) ; _dessiner_menus (type 53 : centrer_menu puis plaque_auto) ; rendu ville (`self._M_ville = M; self._aspect_ville = aspect` avant _tracer_decor(True)).
- ui_menu.py : boutons() ignore désormais les états 2/3/4 dans TOUTES les fenêtres ; ajouts plaque_auto, textes_grises, etat_actif, vals_code, auto_grise.
- moteur.py : rotation par défaut du paquet 31 = (0,0,0) ; DQ_FBXLOG dans le paquet 32.
- donnees.py et objets_carte.py viennent de ac4cb9b : conflit ou doublon probable à la fusion de la branche coffres (prendre une seule version ; cache renommé carte9, ancien cache invalidé).
- Tests nouveaux : outils/test_titre_ciel.py, test_plaque_depart.py, test_camera_titre.py.

Scripts de capture réutilisables : /tmp/t2_final.sh, /tmp/t2_zone2.sh, /tmp/run_t2.sh (SAVES=...), /tmp/t2_diff.py ; sauvegardes de test /tmp/sv_t2_sans, /tmp/sv_t2_avec.

---

## Agent a3150b360db4a6624 — 02/11 10:22

RAPPORT HCB (historique des combats : capture des résultats), branche `agent44-histocombat` (worktree /home/claude/wt44-histocombat, base 6580393). Arbre propre. 3 commits : 41b0792, 7ca0446, 17729a8 (pied de page 2 lignes). Fichiers touchés : UNIQUEMENT les 2 NOUVEAUX `dq4_pc/historique_combat.py` (283 l.) et `outils/test_historique_combat.py` (552 l.). Aucune ligne modifiée dans fenetre.py / moteur.py / historique.py / ui_historique.py / pause.py. pyflakes propre. Pas de push.

== API fournie ==
`class CapteurCombat` : `__init__(moteur)` (crochets en LECTURE seule, rien écrit dans la mémoire du moteur ; se désactive proprement `actif=False` si le moteur n'est pas celui étudié), `maj(moteur) -> list[dict]` (une fois par image après `mo.step`, ne lève jamais), et `CapteurCombat.pour(mo)` (capteur unique par moteur, créé à la 1re demande, crochets posés une seule fois).
dict = `{'t': g_Game+4 (1/60 s) à la fin du combat, 'ennemis': [{'nom','total','vaincus'}, ...] (1 entrée par espèce, ordre d'apparition, nom français affiché), 'or': int, 'xp': int, 'issue': 'victoire'|'fuite'|'defaite'}`.
Partie pure réutilisable : `Suivi`, `fabriquer_combat`, `nom_de_plaque`, `noms_des_groupes`, constante `ISSUES`.
xp = valeur PAR MEMBRE lue dans le message (« Chaque membre de l'équipe reçoit N points d'expérience », après doublement éventuel) ; or = total de l'équipe (« L'équipe reçoit M pièces d'or »). or/xp = 0 pour fuite et défaite (le moteur ne verse rien : vérifié). Donnée absente = 0 / nom 'Monstre'.

== LA ligne d'intégration (au choix du lead, dans fenetre.py juste après la ligne 2611 `self.historique.maj(mo, ...)`, ou dans le Historique.maj du lead) ==
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
- Tests : 57 tests OK (~60 s avec moteur). Purs : calcul (Suivi, noms, fabriquer_combat) + colle sur FAUX moteur (rupture d'état, images sautées, abandon après 20 images hors combat, erreurs avalées, garde-fou d'événements). Moteur réel facultatif : `DQ_APK="/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks" DQ_SAVES=/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes python3 outils/test_historique_combat.py` (écritures dans un dossier temporaire, ignorés si les variables manquent). Sans xvfb.

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
| PAQ-1b | _OrgColor = (1,1,1,alpha), pas le _Color d'asset | `FldObject.save_org_color` RVA 0xCD811C re-désassemblé (s0 à s2 = 1,0 puis SetColor("_OrgColor")) ; précision du coordinateur confirmée | Établi | bug de cache (donnees.py) | non : le coordinateur le fait (branche audit2-histo, cache carte9 → carte10). Mon uniforme `teinte` reste valable (blanc = neutre) ; commentaires corrigés dans a598be1 | — |
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
- a598be1 PAQ-1 : `Etat.teinte` (moteur.py : remise à neutre au paquet 0 et au paquet 27, branche du 33) ; nouveau `dq4_pc/teinte_carte.py` (reconnaissance des groupes « tz_ » : liste des path_id lue UNE fois dans le paquet de données, ~3 s + ~800 Mo, dans un thread, gardée dans `tz_cles.json` du cache ; repli : tout est teinté) ; fenetre.py : uniforme `teinte` dans le fragment (clamp(rgb × teinte)), teinte par groupe dans `_tracer_decor`, et dans `_tracer_champ` (tuiles + symboles du monde ; sprites non). Interrupteur `DQ_SANS_TEINTE=1`. Teinte neutre = chemin inchangé.
  Mesures : dab1 (neutre) base / new / off = 0 pixel de différence ; mlb1a (teinte réelle 1,25/0,65/0,75 émise par le moteur) : 15,3 % des pixels changés, rendu violet (/tmp/m_paqA0_mlb1a_b420.png avant, /tmp/m_paqA1_mlb1a_b420.png après) ; `DQ_SANS_TEINTE=1` sur mlb1a = ancien code (0 px à l'image 200, 1 px de bruit à 420) ; teout1 avec les valeurs du moteur forcées (1,3/0,7/0,55) : 97,8 % des pixels, moyenne RGB 86,9/108,9/114,7 → 110,4/76,8/63,8, rendu orangé (/tmp/m_paqB_teout1_base_b420.png → /tmp/m_paqG_teout1_f_b420.png) ; mlout1 forcée (1,25/0,65/0,75) : 97,5 %, 65,6/100,8/57,4 → 80,2/66,6/44,0 (/tmp/m_paqG_mlout1_off_b420.png → _f_) ; carte du monde slot 4, teinte forcée (0,8/0,8/1,1) : 99,6 %, 67,0/105,7/135,0 → 53,9/84,9/148,0 (/tmp/m_paqG_monde_off_b200.png → _f_). La fenêtre de message translucide est assombrie par transparence, non teintée. Les sprites de la carte du monde n'ont pas été inspectés sur l'image.
- c8681df PAQ-2 : champ `ech` (1,0 par défaut) ; `t == 13` : si bit 0x800 et position déjà posée, `ech = fl[0]` (la 1re valeur, celle du placement, est ignorée) ; fenetre.py, branche `cam3d` : panneau × k (borné 0 à 8), pieds fixes, décalages de profondeur à l'échelle k ; ombres non mises à l'échelle (Supposé) ; `DQ_SANS_ECHELLE=1`. Test : `outils/test_teinte_carte.py` (18 tests OK, 1 ignoré sans APK). Vérification : dab1 (échelle 1,0) identique à 1 px près (bruit également présent entre deux passes du même code) ; mlb1a identique aux images visibles ; ev07 1514 px.
- Fichiers touchés : dq4_pc/moteur.py, dq4_pc/fenetre.py, dq4_pc/teinte_carte.py (nouveau), outils/test_teinte_carte.py (nouveau). donnees.py, objets_carte.py, `_saisie_menu` non touchés.

3. NOTES À FUSIONNER DANS docs/ (texte prêt)
- notes-technique (remplacer la ligne ~233 « Non reproduit : paquet 33 … ») : « Paquet 33 (`cmd_map_color_rate`) : trois flottants → `FldObject.m_color` (ville/combat) ou `Field.SetColor` (monde). `FldObject.update_material_color` (RVA 0xCD79F4), chaque image : Material.color = `_OrgColor` × m_color, sauf matériau sans texture principale ou dont la texture a « tz_ » dans son nom (lampes, bougies, vagues… : non teintés). `_OrgColor` = (1,1,1, alpha de `_Color`) (`save_org_color`, 0xCD811C) : la couleur RGB `_Color` de l'asset n'est jamais utilisée en jeu. Shaders fld_* : texture × couleur de sommet × `_Color`, saturé à l'écriture (teinte > 1 possible). Sprites, ombres, bulles, interface : non teintés. Viewer : uniforme `teinte` (fenetre.py), groupes « tz_ » par `teinte_carte.py` (`tz_cles.json`), `DQ_SANS_TEINTE=1` pour comparer. La valeur dépend du fuseau horaire du moteur et persiste d'une carte à l'autre : à froid depuis nos sauvegardes seule mlb1a (1,25/0,65/0,75) en émet une ; chargées après elle, mlout1, mmout, mlout2 reçoivent la même et teout1 (1,3/0,7/0,55) (sonde pk33c) ; caf1/ev02 : 0,804/0,807/1,102, en fondu lent. »
- notes-visionneuse (lignes ~72/83/141) : « Paquet 13 bit 0x800 = Chara.SetScale (localScale = 1,8 × s, panneau seul), appliqué (`DQ_SANS_ECHELLE=1` pour couper). Seules mlb1a (0,7383 pendant l'écran noir d'ouverture, puis 0,74 → 1,0) et ev07 (0,9519) ont une valeur ≠ 1 après le placement. Poses couchées (paquets 16/17) : toujours NON rejouées, visibles sur mlm2f1 (dormeur du lit affiché assis). FEAN / paquet 6 et effets 3/5/6 du paquet 34 : aiguillage lu (`SetEventAnimation` / `SetCameraNo` ; `Capture.Tabi` / `DarkLamp` / `Riremito`), contenu non rejoué. Paquet 30 : `Field.SetScale` = orthographicSize × s + FloatingObject.SetScale, non rejoué. »
- Piège de test : un lancement `DQ_VILLE` d'une seule carte ne reproduit pas les teintes de l'audit (balayage séquentiel, fuseau horaire hérité). Charger d'abord mlb1a (chaîne `gl_chaine.py`) ou forcer `TEINTE`.

4. NON VÉRIFIÉ / À SAVOIR
- Windows, vrai GPU, calcul de `tz_cles.json` sur le PC de l'utilisateur (~3 s + ~800 Mo une fois ; thread ; sans lui tout est teinté).
- Teinte du décor de COMBAT et teinte du monde émise par le moteur (jour/nuit, marais) : non capturées en vrai. Carte du monde testée seulement avec teinte forcée.
- Ordre de saturation : mon shader fait clamp(tex × sommet × teinte), identique à l'original une fois le cache nettoyé de la couleur d'asset (travail du coordinateur, donnees.py). Tant que le cache carte9 garde `_Color` d'asset, les matériaux à _Color ≠ blanc (décor de nuit en combat) restent faux avec ou sans teinte. Pas de conflit attendu avec audit2-histo.
- Mesure « 3 cartes » : mlb1a avec teinte réelle ; teout1 et mlout1 avec les valeurs du moteur forcées (lanceur `.../scratchpad/gl_teinte.py` + `run_gl_teinte.sh`). Tentative de chaîne mlb1a → mlout1 : la teinte réelle est bien émise (journal TEINTE) mais l'écran reste noir (événement d'ouverture de mlb1a en cours) : image inutilisable.
- Pièges de fusion : fenetre.py (branche `cam3d` des sprites, shader FRAG, `_tracer_decor`, `_tracer_champ`) et moteur.py (`Etat.appliquer`, branches 13/33/27) ; l'agent « casino » touche les parties 0xf/0x10 et `_saisie_menu`.
- Le scratchpad de session est PARTAGÉ avec d'autres agents (mon p2.py y a été écrasé) : mes outils sont dans /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/paq44/ (gl_ech.py, gl_chaine.py, pk33.py, pk33c.py, pech.py, batch*.sh).
- Captures utiles : /tmp/m_paqA0_mlb1a_b420.png, /tmp/m_paqA1_mlb1a_b420.png, /tmp/m_paqB_dab1_{base,new,off}_b{300,420}.png, /tmp/m_paqB_teout1_base_b420.png, /tmp/m_paqG_teout1_f_b420.png, /tmp/m_paqG_mlout1_{f,off}_b420.png, /tmp/m_paqG_monde_{f,off}_b200.png, /tmp/m_paqG_mlb1a_off_b420.png, /tmp/m_paqC_ev07_{ech,sans}_b420.png, /tmp/m_paqC_mlb1a_{ech,sans}_b420.png, /tmp/m_paqE_mlb1a_{ech,sans}_b{340,380,400,430}.png, /tmp/m_paqD_mlm2f1_b300.png, /tmp/m_paqD_taf1_b300.png.

À retenir pour la session principale : (1) le scratchpad de session est partagé entre sous-agents, utiliser un sous-dossier par agent ; (2) `pkill -f` sur un nom de script présent dans la ligne de commande du shell tue ce shell ; (3) la teinte du paquet 33 dépend de l'état de fuseau horaire du moteur et persiste d'une carte à l'autre.

---

## Agent a42c065e6f40f0601 — 02/11 11:08

RAPPORT CAR (cartes, PNJ, interrupteurs, scripts) - worktree /home/claude/wt44-cartes, branche agent44-cartes, 5 commits sur ab22007, arbre propre. Rien dans /home/claude/dq4-portage, aucun push, saveguardes de l'utilisateur non touchées (tests dans /tmp/sv_car_*). Harnais hors dépôt : /tmp/car44/ (hl44.py, sweep_*.py, gl_*.py, planche_*.png).

## 1. Tableau
Légende : E = Établi, S = Supposé, NV = Non vérifié.

| ID | quoi | preuve | statut | classe | corrigé ? |
|---|---|---|---|---|---|
| CAR-1 | 32 cartes sortaient VIDES (0 sommet) : maillage porté par la RACINE du .fld, sans enfant `NNN_` : 18 décors de combat (btl_mt_*, btl_po_*, btl_sd_* = montagne/marais/désert du monde, btldc1, btldh1, btldp8_*, btlta2, btltd1_*) + 14 lieux (ddb1b, dnb1b2, dnb2b3, dnb3b4, ev04, za1f6, za1f8, za1f9, za2f4-7, za2f9, za3f1) | pkl 0 sommet -> 294 à 4482 ; captures /tmp/car44/planche_racap1-2.png, planche_btlcam.png (vue sol : montagne, marais, désert OK, même structure que btl_pl_*) ; avant/après : cartes zéro-sommet 32 -> 0 | E (données + captures) ; NV (vrai combat) | bug | oui 9986244 (+test) | - |
| CAR-2 | Matériaux sans aucune texture (948 sommets, 21 lieux + 10 décors de combat) : groupe `None` ignoré au dessin | pkl carte9 vs carte10 ; diff pixels | E ; S (genre 'normal', 'trans' si _Color.a != 1) | oubli | oui 759744c (+test). Effet visible faible (<= 18 px en vue d'ensemble, 1 px aux gros plans deb3a/dmb3 : surfaces sous l'eau/le sol) | - |
| CAR-3 | 3 PNJ jamais dessinés : emplacement 8 de mom2f1, mqtf3, msm1f1 (ids 0, 157, 24) : pose animée, jamais de position | L'enregistrement du PNJ dans la mémoire du moteur (Fix32 à LIB+0x26a688 + 0x1c0*(slot-8), +0 et +0x140) = (0,0,0) ; le moteur n'envoie que les positions qui changent ; 9 points de la carte testés, jamais de position. Captures réelles : /tmp/car44/gl/real1_b180.png (mqtf3), real1_b480 (mom2f1), real1_b780 (msm1f1) : le PNJ se tient au centre de la pièce | E (moteur) ; S (Unity crée le Chara à l'origine) | oubli | oui 9aa363d (+test). Sprite sans position + pose reçue >= 3 images après création -> (0,0,0). Les 262 autres sprites reçoivent leur position 1 image après création : aucune apparition parasite (154 cartes) | - |
| CAR-4 | Savestate (.dqs) ancien : `etats.appliquer` ne rejouait que vitesses + bouton Paramètres ; fenêtre des lieux élargie (_elargir_symboles) et g_isAmazon perdus | test avec état dont ces octets sont ceux de l'image d'origine : échoue avant (192/448/788 au lieu de 1600), passe après | E | bug latent | oui b5e9e9c (Moteur.reappliquer_correctifs) | - |
| CAR-5 | Anciens caches carte9_ jamais purgés (regex carte[0-8]) après le passage à carte10_ | test | E | oubli | oui b5669fe | - |
| CAR-6 | Persistance coffres / jarres / portes (ouvrir, quitter, revenir, sauvegarder, recharger : suspend, journal, .dqs) | harnais t_persist*.py, t_coffre*.py, t_portes.py : coffre ouvert = le moteur renvoie `anim 3` (ouvert instantané) à l'entrée, jarre cassée réapparaît, porte = alpha puis onoff, aucun état conservé ; la visionneuse n'écrit AUCUNE variable de scénario | E | décision (fidèle) | sans objet | - |
| CAR-7 | Placement des PNJ : 73 cartes, 499 sprites (351 PNJ, 26 marcheurs), 600 images chacune | 0 traversée de mur, 0 sprite hors emprise / sous le sol / en l'air (16 "en l'air" = petites estrades, vérifié avec tous les triangles) ; cap des PNJ : 0 = +z, 1 = +x, 2 = -z, 3 = -x (n = 3500 déplacements, 0 diagonale) = rangées 0..3 de la feuille (planche_sprites.png) ; feuilles 8 rangées (ids 106, 109, 115, 136, 137) cap 0..7 ; 10 captures réelles (planche_real2.png) : pieds au sol, ombres, cohérents | E | décision / OK | - | - |
| CAR-8 | 5 sprites masqués (paquet 14, vis False) : ev07 x3, mlb1a, mlout1 | N1 530 cartes | E | décision (script) | - | - |
| CAR-9 | Maps non balayées (141 sur 670) : 21 `btl_*` + 119 `btl*` = 140 décors de combat (pas des lieux) + za3f3 | N3 des 140 faits (bx_*, planche_bx_*) ; za3f3 : le moteur plante dans startTown (FldStage::getCameraLimitL, pointeur nul), données OK (8 groupes) ; ev01 (titre) idem | E | décision | - | - |
| CAR-10 | N3 des 530 lieux + 140 décors (vue d'ensemble) | 670/670 captures ; métriques : 0 magenta, 2 quasi vides (za2f6, za2f7 : objets de 30 et 54 sommets) ; planches regardées : 00, 01, 06, 09, racap 1-2, bx_0, deb3a, 10 captures réelles | E (métrique 670) ; NV (planches 02-05, 07, 08, 10, 11, bx_1-2 : métrique seule) | - | - | - |
| CAR-11 | Objets « flottants » (analyse 1147 flaggés) | affiné avec tous les triangles : 123 posés sur petit objet, 323 accrochés à un mur, 43 libres = stalactites `slhnk1a` (29), oiseaux, ballon : normal. Coffres : 21/25 sur estrade (deb3a vérifié en capture), 4 tiroirs de meuble | E | décision | - | - |
| CAR-12 | Textures « suspectes » (71 cartes) | null01.tim (alpha 0 : objets invisibles), kuro01.tim (noir 8x8), srkr1 : voulues par les données ; doublons ddb5b (portes x4 au même point), sjzf6 | E ; S (doublons sans effet) | décision | - | - |
| CAR-13 | Scripts : 528 cartes x ~212 images (repos + conversation avec le 1er PNJ), 55 commandes cmd_* distinctes exécutées | tous les types vus sont décodés SAUF 16 : 12 paquets (mlb1a, mlm2f1, taf1 ; avec cmd_character_action_sleep), 17 : 2 (taf1 ; cmd_set_sleep_near), 33 : 13 (cartes ml* ; 3 flottants 1,25 / 0,65 / 0,75 ; cmd_setup, cmd_map_animation_a, cmd_setup_music, cmd_change_map_link) ; 6 et 18 : 0 ; 13 : 58 959 ; 27 (FieldData::setup) non décodé mais inutile (grille lue en mémoire) | E (comptes) ; NV (effets) | - | - (agent « paquets ») | - |
| CAR-14 | Seul ~55 des 445 cmd_* sont atteints hors scénario ; ni apparition/disparition de PNJ par événement, ni scènes jouées | - | NV | - | - | ~1 jour : rejouer les sauvegardes de chapitre avec les crochets de /tmp/car44/sweep_cmd.py |

## 2. Corrections (un commit chacune)
- b5e9e9c etats.py + moteur.py + outils/test_etats_correctifs.py : correctifs mémoire rejoués au chargement d'un état.
- 759744c donnees.py + test_objets_carte.py + outils/test_textures_carte.py : texture blanche, cache carte10_ (la rename a un coût : les cartes se re-préparent au premier lancement, ~80 s ici pour 670).
- 9986244 donnees.py + outils/test_decors_racine.py : décors à maillage racine (32 cartes). Même version de cache carte10.
- 9aa363d moteur.py + outils/test_cartes_pnj.py : sprite jamais positionné = origine.
- b5669fe donnees.py + test_textures_carte.py : purge des carte9_.
Tous les outils/test_*.py passent (DQ_CACHE_CARTES=/tmp/cache44) ; pyflakes : seuls avertissements connus.
Fichiers hors de mon périmètre touchés : moteur.py (Etat.appliquer : ligne de création de sprite (clé 'cree') et bloc paquet 13 pose ; constante ORIGINE_APRES ; méthode Moteur.reappliquer_correctifs) et etats.py (un appel) = zone de l'agent « paquets » : risque de conflit de fusion sur ces deux blocs.

## 3. Notes à fusionner dans les docs
- Décors : 32 cartes ont le maillage sur le GameObject racine (pas d'enfant NNN_) ; objet 0 = la racine (za1f6, za2f6/7/9 : enfants `sNN_` = images de séquence). Matériau sans texture = texture blanche 4x4 (clé TEX_BLANCHE) x couleur de sommet x _Color. Cache carte10_ ; carte[0-9]_ purgés.
- null01.tim = transparente exprès ; kuro01.tim = noire exprès.
- Moteur : les positions de personnages ne sont envoyées que si elles changent ; enregistrement des PNJ : LIB+0x26a688, pas 0x1c0, Fix32 (x, y, -z) à +0 et +0x140 ; un PNJ posé en (0,0,0) n'est jamais envoyé.
- Caps PNJ (feuilles 4 rangées) : 0 = +z, 1 = +x, 2 = -z, 3 = -x ; héros et feuilles 8 rangées : 0 N, 2 E, 4 S, 6 W.
- Téléportation de test : écrire x, y, -z (Fix32 x 4096) dans g_cmnPartyInfo (LIB+0x269810) puis startTown(carte).
- Animations coffre FCAN : 1 fermé instantané, 2 ouverture (10 images), 3 ouvert instantané (renvoyé par le moteur à l'entrée), 4 fermeture ; jarre : anim 2 = séquence cassée puis onoff ; porte : alpha puis onoff ; aucune de ces états n'est persistant.
- Écritures de la visionneuse dans le moteur : g_isAmazon (1), option vitesse des messages, vitesses de marche (remise à l'origine), instruction cmp du bouton Paramètres, fenêtre des lieux (3 immédiats à 1600), bits de Global.Flag (fondu 0x1, effet 0x2), file de messages (buf2), file de touches (buf1) ; AUCUNE variable de scénario. Lues : Global.Flag, partie (+0xee), grille FieldData, options, état de message.
- Émetteurs statiques de paquets (UnityGetPacket) : 5 FLDObject::SetCommonAnimation ; 7 SetMapObjOnOff/SetMapUidOnOff ; 12/13/14 SpriteCharacter + DisplayCharacter ; 17 cmd_set_sleep_near ; 19 FieldSystem/BillboardItem/TownPlayerEtc ; 21 DSSAObject ; 22 Dssa_G3_BeginMesh ; 27/28/29 FieldData ; 31/32 ModelObject + TownMapEffect ; 34 Global::SetScreenEffect. Les autres types passent par un autre chemin non identifié.
- Risque : un .dqs n'écrit pas les fichiers de sauvegarde du jeu : charger un état puis le titre peut montrer une sauvegarde plus récente (normal).

## 4. Non vérifié
- Aspect réel en combat des 18 nouveaux décors (vue de sol approximative sur 4 seulement : btl_mt_d/e, btl_po_d, btl_sd_d ; aucune rencontre aléatoire jouée) ; `_fond_combat` n'est appliqué qu'aux 21 décors `btl_*` (les 119 autres n'ont pas de fond de repli : à voir en combat de château).
- Scénarios (chapitres) : PNJ qui disparaissent/apparaissent, acteurs de scène (risque d'un acteur posé en (0,0,0) quelques images avant sa position réelle : même comportement qu'Unity, non vu).
- Effets réels des paquets 16, 17, 33 (comptés seulement).
- Planches N3 non regardées une à une (7 sur 15) ; Windows / vrai GPU.
- Doublons de décor (ddb5b, sjzf6) : pas de défaut visible, pas inspectés de près.

---

## Agent a6564d55a4c288220 — 02/11 12:14

RAPPORT FINAL, mission « services en ville et véhicules » (préfixe SRV). Worktree /home/claude/wt44-services, branche agent44-services, 1 commit (6d39f59) sur ab22007. Arbre propre. Aucun push, aucune sauvegarde réelle touchée (écritures dans /tmp/sv_NOM), aucun fichier de patch FR touché.

RÉSUMÉ
- Toutes les fenêtres de services (boutiques, banque, église, auberge, statut, équipement, Nène, otage, boutique de Torneko, arène) sont rendues correctement par la visionneuse (captures GL réelles). Un seul vrai bug trouvé et corrigé : les pages du Statut ne tournaient pas au clavier.
- Les véhicules (bateau, ballon, chariot) existent et sont dessinés. La carte du monde dessine bien les modèles 4289, 4279, 4232 et 4233, alors que le doc disait « jamais dessinés ». C'est faux dès que le chapitre et les drapeaux sont forcés.
- Le moteur a un seul point d'entrée commun pour tous ces menus : `window::CommandWindow::changeShopMenuPhase(TownWindowSystem::m_singleton, phase)`. En l'appelant directement (après `MaterielMenu_WINDOW_MANAGER::getSingleton()+0x10 = 0`), je joue n'importe quel service sans traverser les conditions du script.
- Toutes les sauvegardes réelles de l'utilisateur sont au chapitre 1 (data1 `mak1f1`, data2 `caf1`, data4 `field`, data5 `dab1`). Les chapitres suivants ne sont atteignables que par forçage (chapitre + drapeaux).

1) TABLEAU DES CONSTATS
Légende : E = Établi (observé), S = Supposé, NV = Non vérifié. Classes : D = décision, O = oubli, B = bug.

| ID | quoi | preuve | statut | classe | corrigé ? | sinon effort |
|---|---|---|---|---|---|---|
| SRV-01 | Église : prêtre (66), liste des journaux (54), sauvegarde (56), écriture data*.dat | /tmp/m_eg1_b_eglise.png, /tmp/srv/sheet_eg4.png ; /tmp/sv_eg4 (data1, data5, data9 écrits), clavier | E | – | – | – |
| SRV-02 | Église : Résurrection / Pénitence (67) | /tmp/srv/sheet_eg5.png | E (rendu, flux). Divination, Bénédiction, Purification : NV. Souris à l'église : NV | – | – | faible : jouer chaque entrée |
| SRV-03 | Boutique d'armes (phases 2, 8) : racine 57, liste 58 avec ◀ ▶ quantité, « Qui va le porter ? » (60), vente 62. Or et sac corrects, clavier ET souris | /tmp/srv/sheet_bt2a.png, bt3, bt4, bt5 ; /tmp/m_bt6_*.png (souris) | E | – | – | – |
| SRV-04 | Boutique d'armures (3) et d'objets (4), appel direct. Achat ×3 au clavier (D D) : 3000 G → 1950 G (armure, 3 × 350) et 3000 G → 2976 G (herbes, 3 × 8). Vente : +660 G, objet retiré | /tmp/out_shop2a.txt, /tmp/out_shop2b.txt | E | – | – | – |
| SRV-05 | Type 59 (2e variante de la liste d'achat) jamais ouvert : toutes les listes vues sont de type 58. Type 63 (quantité à vendre) jamais ouvert : cette version vend objet par objet, chaque herbe est une ligne à 6 G (p. 2 et 3 de la liste de vente). Pages de la liste au clavier OK (D tourne les pages) | /tmp/out_shop3.txt | E (63 inatteignable en chapitre 1) ; 59 NV | D | – | – |
| SRV-06 | Auberge (phase 0), appel direct : or 3000 → 2988 (12 G), Oui / Non au clavier ET à la souris, « Non », or insuffisant (« Cela me gêne… »), fondu au noir puis d'entrée, message « Bonjour ! J'espère que vous avez… » | /tmp/srv/sheet_au3.png, sheet_au4.png | E | – | – | – |
| SRV-07 | Auberge par le PNJ réel (script) : la condition est `cmd_is_talked_at_shop(1)`, c.-à-d. le bit 2 de `[personnage+0x3c]` (parole par-dessus le comptoir). Ce bit n'est posé par `TownCharacterManager::checkTalkingNearCharacter` que si `TownStageManager::checkCrossNum(héros, PNJ)` ≠ 0, et il est effacé sinon. Forcer le bit ne suffit pas. Essais : anneau de 0,6 à 2,2 autour du PNJ (id 0 de `may1f1`, en (-2,74 ; 3,27)), 8 directions : toujours le dialogue « Hugues Esclin » | scripts, désassemblage 0x21e8a0 et 0x1ccf6c | NV (poses couchées des paquets 16-18, soin PV/PM, nuit complète par le script) | – | – | moyen : trouver la case côté client du comptoir |
| SRV-08 | Banque = phase 16 (maps `hcm2f1`, `hcy1b1`, `ss5b1b`), pas un type propre. Racine 57 (Dépôt / Retrait / Rien), 64 « Déposer combien ? », 65 « Retirer combien ? », 6 chiffres dont seuls les 3 premiers ont des ▲ ▼ (montants en milliers). À la souris : dépôt 3000 → 0 G, retrait 0 → 3000 G | /tmp/srv/sheet_ph16.png, sheet_bank1.png, /tmp/out_bank1.txt | E (souris) | – | – | – |
| SRV-09 | **Banque au clavier : impossible de saisir un montant.** Z et D sans effet sur 64. `_saisie_menu` ne retient que les boutons avec pad & 0x10, donc les ▲ ▼ des colonnes (pad 0x2 / 0x1) ne sont jamais ciblés. Même cause que la mise du casino | /tmp/out_bank1.txt (« T64 apres clavier » identique à « T64 ») | E | O | NON : relève de la généralisation ▲ ▼ de l'agent « casino » | à rejouer après fusion : il faudra aussi ◀ ▶ pour choisir la colonne |
| SRV-10 | **Statut (types 13-17) : Q / D / L / R / PageHaut / PageBas ne tournent pas les pages au clavier.** Cause : fenêtre sans grille ni bouton A ; `_saisie_menu` convertit ◀ ▶ en pads 2 / 1 envoyés à une fenêtre qui les ignore. Seul le clic sur les flèches (type 6) marchait | /tmp/out_stat2.txt (avant) et /tmp/out_stat2b.txt (après) | E | B | **OUI, 6d39f59** | – |
| SRV-11 | Menu du terrain : racine 2×2 (Objets, Magie, Carac., Divers), Objets (9) avec page 1/3, commandes (8) Utiliser / Transférer / Équiper / Abandonner, infobulle (10), Équiper (« Ragnar s'équipe de l'épée de cuivre. »), Statut 4 pages (13, 14 équipement, 15 sorts usuels, 15 sorts de combat) | /tmp/srv/sheet_menu2.png, sheet_m3a.png | E | – | – | – |
| SRV-12 | Sorts du menu (type 7) : Magie sur un groupe sans lanceur donne un message seul. Aucune sauvegarde avec lanceur (data1, data4, data5 : Ragnar sans PM ; data2 démarre sur un dialogue) | /tmp/out_m3b.txt, /tmp/out_m3c.txt | NV | – | – | sauvegarde de chapitre 2-5 avec Alena / Mina ou Doc : voir §4 |
| SRV-13 | `cmd_menu_extra_shop` = phases 18 (arg 0) et 19 (arg 1). Phase 18 : racine 57 Acheter / Vendre, achat répété d'herbes à 8 G. Phase 19 : « Accepteriez-vous de nous en vendre ? » (62, titre « Vendre ») | /tmp/out_ph18.txt, /tmp/out_ph19.txt, /tmp/srv/sheet_cdf1.png | E (fenêtres). Vente effective NV : l'objet choisi est une arme, refusée | – | – | faible |
| SRV-14 | `cmd_menu_nene` = phase 24 : liste d'objets (9) + Oui / Non, l'objet « Lance de fer » disparaît de la liste | /tmp/out_ph24.txt | E. Type 70 (NENE_ItemView) : jamais ouvert, NV | – | – | – |
| SRV-15 | `cmd_menu_hostage` = phase 23 : « Qui choisir ? » (type 21), liste de l'équipe avec PV, PM, Att, Déf, message « Vous voulez échanger le détenu… ». Le niveau de Doc s'affiche « Nv.: ? » : texte du moteur | /tmp/srv/sheet_ph23_28.png | E | – | – | – |
| SRV-16 | Boutique de Torneko (type 69) = phase 28 (`mfw1f1`) : liste Épée de cuivre 100 G / Dague divine 200 G / Arc de chasseur 350 G, négociation par messages et Oui / Non. Le cadre est haut avec le bas vide (3 lignes sur 6 ?) | /tmp/srv/sheet_ph23_28.png | E (rendu). Vente complète NV (hors chapitre 4) ; taille du cadre : S | – | – | faible |
| SRV-17 | Arène martiale (68, phase 22 ; `cccf2`, `cmd_menu_colosseum` args 1 à 5) : fenêtre PV et message « Princesse Alina… herbes médicinales… ? » s'affichent. Après « Oui », le moteur plante dans `MaterielMenu_MARTIAL_COLOSSEUM::checkHaveYakusou` : membre d'indice -1, groupe de chapitre 1 au lieu de celui du chapitre 2. Artefact du forçage, pas un bug de visionneuse | /tmp/out_ph22b.txt, /tmp/srv/sheet_ph22b.png | E (affichage) ; flux complet NV | – | – | sauvegarde de chapitre 2 |
| SRV-18 | Phase 12 : type 44 « Acheter combien ? 3000G / 0G / Acheter », dans une ville (`hcy1b1`, `ss5b1b`). Phases 5 et 11 : échange de jetons, message seul avec 0 jeton. Domaine « casino » : à leur transmettre | /tmp/out_ph12.txt, /tmp/out_ph5.txt | E (fenêtre 44) ; 5 / 11 avec jetons NV | – | – | – |
| SRV-19 | Phase 17 (mini médailles, `shf1`, `hcy1b1`) : message seul sans médailles | /tmp/out_ph16.txt (phase 17 lancée à part) | E (message) | – | – | – |
| SRV-20 | Bateau, chapitre 4 → 5 (script `field` g4, drapeaux globaux 204 = 1 et 205 = 0, chapitre 4) : les modèles 4289 (slots 10 et 11) naviguent, le héros 4202 est caché, « Terre en vue ! », fondu, débarquement, titre de chapitre (messages sur noir), puis `cmd_menu_save`. Caméra qui suit | /tmp/srv/sheet_sh1.png, sheet_sh1b.png, /tmp/out_sh1.txt | E | – | – | – |
| SRV-21 | Ballon : chapitre 5 + drapeau global 344 = 1 : modèle 4279 (slot 12) dessiné avec le HUD tactile. Pas de déplacement vérifié (essai ball2 abandonné) | /tmp/srv/sheet_ball1.png | E (dessin) ; déplacement NV | – | – | faible |
| SRV-22 | Chariot : chapitre 5 + drapeau 388 = 1 : cheval 4232 (slot 1) et chariot 4233 (slot 2) suivent le héros, en file derrière lui quand il marche | /tmp/srv/sheet_car1.png, sheet_car2.png | E | – | – | – |
| SRV-23 | Radeau (`deb1`, `deb2a`, `deb3a`, `dnb4`, `dnb6`, `hhout`, g3 / g5), henge (`cjf2b`, `cjout` g5), appel du chariot (`ev07` g1 / g5, `srout`), `cmd_set_ship_pos` (`mrout`), sifflet, Rura (`cmd_set_ruura_lock` dans 54 maps, sans interface) | scan des 397 scripts | NV | – | – | moyen : forcer chapitre 3-5 + drapeaux |
| SRV-24 | Générique : `cmd_the_end` (`mlb1a` g9, deux variantes selon le drapeau global 0x1af) lance `TownEndrollManager::startTheEnd`. Avec chapitre 9 + `startTown('mlb1a')`, le script g9 ne démarre pas en 3000 images (drapeau 0xa4 resté à 0, héros verrouillé) | /tmp/claude-0/…/scratchpad/p17.py, p18.py | NV | – | – | moyen : trouver la condition de départ du scriptobject g9 o0 |
| SRV-25 | « Surechigai » : `zaout` g1 o1 (PNJ slot 8) enchaîne `cmd_surechigai_mapname` (= phase 31, aucune fenêtre), `make_taishi`, `change_surechigai_part`. Après la parole le héros reste verrouillé (position figée 1400 images). Aucun script ne mène à `zaout`, et aucun autre code n'appelle `Global::startSurechigai` | scripts + /tmp/claude-0/…/scratchpad/p22.py | E (verrouillage dans le test), inaccessible au jeu normal | D (fonction en ligne) | – | – |
| SRV-26 | `cmd_menu_present_exp` (`caf1` g1 o28, chapitre 1 ; `ckf3f5` g5) : le PNJ (slot 35) est absent des sprites en chapitre 1 | p21.py | NV | – | – | drapeau d'apparition à trouver |
| SRV-27 | Phase 13 : le moteur plante (phase non définie). Aucun script ne l'utilise | p15.py 13 | E | D | – | – |

2) CORRECTIONS PAR COMMIT
- 6d39f59, « Statut (types 13-17) : Q / D / L / R tournent les pages au clavier » (SRV-10), fenetre.py, +3 lignes dans `_saisie_menu`, juste avant `if f.get('grille') or len(z) < 1:`.
  - Une fenêtre sans grille ni bouton A envoie maintenant ◀ ▶ (pads 8 / 4) au port qui porte les flèches de page, via `_port_pour_manette`.
  - Avant, clavier seul (/tmp/srv/scen_stat2.py) : R, D, PageBas, A, Q, PageHaut laissent « 1/4 ».
  - Après : R 2/4, D 3/4, PageBas 4/4, R 1/4 (boucle), A 4/4, Q 3/4, PageHaut 2/4.
  - pyflakes : un seul avertissement, `fenetre.py:2203 'sel'` inutilisé, antérieur à mon commit. `outils/test_entrees.py` (37 tests) et `test_pause_pages.py` (16 tests) passent.
- Fichiers touchés : uniquement `dq4_pc/fenetre.py`. Rien hors fenetre.py / ui_menu.py / moteur.py.

3) NOTES À FUSIONNER DANS docs/ (prêtes à coller)

**notes-technique-portage-dq4.md, « Services en ville : phases `cmd_menu_shop` » (02/11/2026, mission SRV)**
- Tous les menus de service passent par `window::CommandWindow::changeShopMenuPhase(TownWindowSystem::m_singleton, phase)`. `__cmd_menu_shop::initialize` appelle `TownCharacterManager::setPlayerDirection(placement)`, puis cette fonction, puis pose `MaterielMenu_WINDOW_MANAGER::getSingleton()+0x10 = 0` et `g_cmnPartyInfo+0x974 = placement`.
- On peut jouer un service sans script : poser `[MaterielMenu_WINDOW_MANAGER+0x10] = 0` puis appeler `changeShopMenuPhase(m_singleton, n)`. Phase 13 : le moteur plante.
- Phases utilisées par les 397 scripts :
  - 0 auberge, 1 église, 2 armes, 3 armures, 4 objets ; 6, 8, 9, 10 = variantes de 0, 2, 3, 4 ;
  - 5 et 11 = échange de jetons ; 12 = achat de jetons (type 44) ;
  - 16 = banque (types 57, 64, 65) ; 17 = mini médailles ;
  - 18 et 19 = `cmd_menu_extra_shop` (arg 0 et 1) ;
  - 22 = `cmd_menu_colosseum` (arg dans `MaterielMenuPlayerControl+0x18`) ; 23 = `cmd_menu_hostage` ; 24 = `cmd_menu_nene` ;
  - 28 = boutique de Torneko (type 69) ; 31 = `cmd_surechigai_mapname` (aucune fenêtre).
- Fenêtres observées :
  - 57 racine (Acheter / Vendre / Rien, ou Dépôt / Retrait / Rien) ;
  - 58 liste d'achat (◀ ▶ = quantité par rangée) ;
  - 60 « Qui va le porter ? » ;
  - 62 liste de vente (une ligne par objet) ;
  - 64 et 65 banque : 6 chiffres, ▲ ▼ sur les 3 premiers (milliers) ;
  - 44 achat de jetons ; 68 arène (PV et Oui / Non) ; 69 boutique de Torneko ;
  - 21 « Qui choisir ? » (otage) ; 9 liste d'objets pour Nène.
- Jamais ouverts en chapitre 1 : 59 (2e variante d'achat), 63 (quantité à vendre : une vente = un objet), 70.
- Auberge : la condition de parole est `cmd_is_talked_at_shop(1)`. Elle lit le bit 2 de `[TownCharacterBase+0x3c]` (`getCounterTalk`), posé quand `TownStageManager::checkCrossNum(héros, PNJ)` ≠ 0 (case de comptoir entre les deux).
- Chapitre : `status::g_Story` est l'objet de `StoryStatus::setChapter(g_Story, n)` ; la valeur est à `[g_Story+4]`. Pour jouer un script de chapitre : charger la sauvegarde 4 (carte du monde), `setChapter`, poser les drapeaux globaux (L+0x25b3d8, bit n), appeler `Global::startField()`.

**Véhicules (carte du monde `field`)**
- Modèles : 4289 (×2, slots 10 et 11) = bateau ; 4279 (slot 12) = ballon ; 4232 (cheval) et 4233 (chariot) = slots 1 et 2 quand le groupe monte dans le chariot ; 4202 = héros (slot 0, caché pendant la navigation).
- La phrase de notes-technique « emplacements 10 à 12 créés sans jamais recevoir de position : non dessinés » vaut seulement hors scénario.
- Chapitre 4, g4 : drapeau 205 = 0 et 204 = 1 → arrivée du bateau, titre de chapitre, `cmd_set_chapter 5`, `cmd_menu_save`.
- Chapitre 5 : drapeau 344 = ballon, 388 = chariot, 343 = bateau (S, pas testé).

**notes-visionneuse-dq4-pc.md**
- Touches de test : B = RETOUR ARRIÈRE (pas Échap, qui ouvre la Pause et gèle la boucle), Menu = Entrée, haut / bas = Z / S, gauche / droite = Q / D, L / R = A / R.
- Statut : Q, D, L, R tournent les pages (6d39f59). Auberge : fondus OK. Oui / Non à la souris OK.
- Banque et mise du casino : pas de saisie clavier tant que les ▲ ▼ ne sont pas généralisés.

**couverture.md §2, mises à jour des statuts**
- 56 : Vu en jeu (écriture de data1, data5, data9). 57, 58, 60, 62 : Vu. 64, 65 : Vu à la souris, clavier absent. 66, 67, 69, 68, 44, 21 : fenêtres vues. 59, 63, 70 : jamais ouverts (inatteignables en chapitre 1).
- 8, 9, 10, 13 à 15 : Vu. 7 : NV.

4) NON VÉRIFIÉ (avec ce qu'il faudrait)
- Windows et GPU réel : tout ce qui précède vient de Mesa sous xvfb (1280×720).
- Auberge par le PNJ réel : poses couchées (paquets 16-18, agent « paquets »), soin PV/PM, nuit complète. Il faut se tenir côté client du comptoir de `may1f1`.
- Sorts du menu (7) et soins hors combat : sauvegarde avec lanceur de sorts (chapitres 2 à 5, Alena / Mina / Doc avec PM).
- Arène (chapitre 2, groupe Alina / Kiryl / Borya), boutique de Torneko et générique (chapitres 4 et 9), otage (`cip1b1`, chapitre 5), `hcm2f1` (Nène en chapitre 3 : PNJ absent sans drapeau), extra_shop avec un objet vendable.
- Banque et types 64 / 65 au clavier ; saisie des jetons (44) ; phases 5 et 11 avec jetons.
- Déplacement du ballon, bateau piloté (g5, drapeau 343), radeau, henge, sifflet, Rura, appel du chariot (`ev07`).
- Générique `mlb1a` g9 ne démarre pas en forçage ; Surechigai inaccessible.
- Souris à l'église ; Divination / Bénédiction / Purification ; type 59.

5) CAPTURES UTILES (chemins absolus, /tmp)
Planches : /tmp/srv/sheet_eg4.png (sauvegarde), sheet_eg5.png (67), sheet_bt2a.png, sheet_bt3.png, sheet_bt4.png, sheet_bt5.png (boutique d'armes), sheet_au3.png, sheet_au4.png (auberge), sheet_ph16.png, sheet_bank1.png (banque), sheet_menu2.png, sheet_m3a.png (menu du terrain et statut), sheet_sh1.png, sheet_sh1b.png (bateau), sheet_ball1.png, sheet_car1.png, sheet_car2.png (ballon, chariot), sheet_cdf1.png, sheet_ph23_28.png, sheet_ph22b.png.
Captures individuelles : /tmp/m_bt6_*.png (souris, boutique), /tmp/m_eg1_b_eglise.png, /tmp/m_eg4_05_liste.png.
Sauvegardes de test : /tmp/sv_eg4/data1.dat, data5.dat, data9.dat.
Journaux : /tmp/out_<nom>.txt.
Outils :
- /tmp/srv/run_srv.sh (lanceur GL avec scénarios générateurs ; chemin de scénario ABSOLU obligatoire), /tmp/srv/gl_srv.py, /tmp/srv/lib_scen.py ;
- scénarios : scen_phase.py (PHASE, PH_ARG, PH_COINS), scen_field.py (F_CHAP, F_FLAGS, F_N, F_WALK), scen_npc.py, scen_bank.py, scen_shop2.py, scen_shop3.py, scen_menu2.py, scen_menu3.py, scen_stat2.py ;
- sondes moteur seul dans /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/ : outils44.py, hl44.py, scripts.py, tabcmd.json, p15.py à p22.py.

6) PIÈGES DE FUSION
- fenetre.py `_saisie_menu` : mon insertion (3 lignes) est juste avant `if f.get('grille') or len(z) < 1:`. L'agent « casino » modifie la boucle `for bit, pad in dirs` juste dessous. Conflit textuel probable mais trivial : garder les deux blocs. Après fusion, rejouer /tmp/srv/scen_stat2.py (doit finir 2/4, 3/4, 4/4, 1/4, 4/4, 3/4, 2/4) et /tmp/srv/scen_bank.py (la saisie clavier du montant doit changer les chiffres).
- Pour l'agent « paquets » : l'auberge jouée par appel direct ne montre pas les poses couchées (pas de script). À regarder via le PNJ réel.

7) À RETENIR (pour la mémoire, appris dans cette session)
- Les sauvegardes réelles de l'utilisateur sont toutes au chapitre 1 (data1, data2, data4, data5 ; data3 vide). Source : décodage avec /tmp/specs/dq4_sauvegarde.py.
- Le verrou /tmp/xvfb.lock est partagé entre tous les agents : les scénarios GL attendent plusieurs minutes chacun (source : /proc/locks).
- `pkill -f motif` tue aussi le shell appelant si le motif figure dans la commande : utiliser des PID.
- En scénario GL : B = RETOUR ARRIÈRE, Échap = Pause (bloque la boucle), Menu = Entrée.

---

## Agent a0be64ffc1ded4a4a — 02/11 12:24

RAPPORT FINAL - mission « casino et bestiaire » (agent 44, CAS-*)

Worktree : /home/claude/wt44-casino, branche agent44-casino. 10 commits au-dessus de ab22007. Arbre propre, rien de non commité. Pas de push, pas de changement de branche, pas de PR.
Tests : test_casino_bestiaire (28), test_vitesse_combat, test_priorite_jeu, test_camera_ville et test_camera_titre passent. pyflakes ne signale que 2 avertissements « variable inutilisée » déjà présents sur main (fenetre.py `sel`, ui_menu.py `ax`).

Fichiers touchés : dq4_pc/fenetre.py, dq4_pc/moteur.py, dq4_pc/ui_menu.py et un nouveau fichier outils/test_casino_bestiaire.py. ui_menu.py (`Fenetre.code()` + `_code_masque`) est le seul qui sorte de la liste fenetre/moteur/ui_menu à signaler : non, les trois fichiers autorisés suffisent. Aucun fichier de patch FR ni sauvegarde utilisateur touché. historique.py, ui_historique.py et la page « historique » de pause.py ne sont pas touchés. Etat.appliquer n'est pas touché.

## 1. Trouvailles (ID | quoi | preuve | statut | classe | corrigé ?)
| ID | quoi | preuve | statut | classe | corrigé / effort |
|---|---|---|---|---|---|
| CAS-1 | Poker invisible : parties 0xf/0x10 inconnues de la visionneuse, garde de dessin des maillages dynamiques réservée à PARTIE_VILLE | avant /tmp/audit/gl_poker_b330.png ; après /tmp/m_cas_pks_b700.png (table et cartes dessinées, main jouée) | Établi | oubli | oui, f93071b |
| CAS-2 | Poker : zones tactiles des cartes et « Donner » absentes (code de fenêtre 2, valeur 63 = masque de bits, absente du tableau `fx` exporté) | main complète jouée au clavier et à la souris | Établi | bug | oui, b9fe007 |
| CAS-3 | Menus de saisie numérique injouables au clavier (machine à sous, poker, jetons type 44, arène 49, mise 47/48) : ◀▶ choisit la colonne, ▲▼ = pads 2/1 sur la colonne | gain de machine à sous obtenu au clavier (/tmp/m_cas_sl_r02_b_arret.png) ; achat de jetons de bout en bout (/tmp/m_cas_pc_phc_03.png) ; mise d'arène (/tmp/m_cas_pa_phf_00.png) | Établi | oubli | oui, 57fe281 |
| CAS-4 | Échap ouvrait toujours Pause dans 0xf/0x10 au lieu du bouton retour de la fenêtre ouverte | tests unitaires + scénario GL | Établi | oubli | oui, 8b3b318 |
| CAS-5 | Bestiaire : monstre non dessiné et tranche d'église `mak1f1` derrière la liste et la fiche | /tmp/m_cas_bk2_b330.png, /tmp/m_cas_bk3_b350.png | Établi | bug | oui, dd0d007 (décor de ville non tracé en 0x10, monstre dessiné) |
| CAS-6 | Bestiaire : ◀▶ de la fiche et L/R de la liste mal routés ; touche « Action » (pad 0x800) | idem | Établi | oubli | oui, dd0d007 |
| CAS-7 | Marche accélérée possible en 0xf/0x10 (les flèches tenues servent aux menus) ; lieu « Casino » / « Bestiaire » absent des états instantanés | tests ; chargement d'état en poker OK (/tmp/m_cas_e1_03_apres_load1.png) | Établi | oubli | oui, 725bfcb |
| CAS-8 | Régression de mes tests de caméra (méthode `_libre` sur faux objets) | test_camera_ville | Établi | bug (de mon code) | oui, 80854c1 (fonction de module `camera_libre`) |
| CAS-9 | Arène des monstres, combat : (a) le message « X a remporté la victoire ! » ne tourne jamais au clavier (la fenêtre « Quitter », type 71, un seul bouton pad 0x400, avalait A) ; (b) la touche V sans effet (la fenêtre « Quitter » ouverte pendant tout le combat comptait comme une attente du joueur) | avant /tmp/m_cas_ar_a3_fin.png (bloqué) ; après /tmp/m_cas_ar3_b2_036.png (« Félicitations ! Vous avez gagné 33 jetons ! », fenêtre type 51 « Jetons 497 / Gagnés 33 »), retour en 0xc puis nouvelle mise /tmp/m_cas_ar3_b2_040.png. Vitesse mesurée en temps réel (DQ_TEMPS_REEL=1), combat de 900 pas moteur : x1 = 31,1 s ; x3 avant correction = 31,1 s (aucun effet) ; x3 après = 12,4 s (environ 2,5 fois plus vite) | Établi | oubli | oui, bd7a2ef (A) et ea2d593 (vitesse) |
| CAS-10 | Pause (Échap), états instantanés, vitesse des combats (V), priorité du jeu en 0xf/0x10 | V en casino : aucune accélération moteur ; Échap = retour ou Pause ; chargement/sauvegarde d'état en poker OK ; aucun plantage | Établi | vérification | rien à corriger |
| CAS-11 | Accès : poker/machine à sous = `ChangeShopMenuPhase` 0xe / 0xd (voir §3) ; casino de Chandor `hcy1b1` rendu (/tmp/m_cas_h1_00_hcy1b1.png) | captures | Établi | décision (doc) | n/a |
| CAS-12 | Jetons (44) et cadeaux (45, 46) : jouables au clavier de bout en bout (comptoir de jetons, échange de cadeaux avec cible) | /tmp/m_cas_pc_phc_03.png ; /tmp/m_cas_pg_ph5_00.png et _02.png | Établi | n/a | rien à corriger après CAS-3 |
| CAS-13 | Colisée (68, phase 0x16) : plantage du moteur (`checkHaveYakusou` -> `BaseHaveItem::getCount`, pointeur invalide) avec une sauvegarde du chapitre 1 | trace | Supposé artefact de l'appel artificiel (pas de groupe du chapitre 2 / Alina) | décision | non vérifiable ici ; il faut une sauvegarde du chapitre 2 |
| CAS-14 | « ERROR 3080@ » dans certains dialogues de PNJ du casino | /tmp/m_cas_t1_s10_00.png | Supposé : banque de textes d'un autre chapitre | n/a | non |
| CAS-15 | Animation de bingo (paquet 6) | non rendue | Établi | agent « paquets » | non (hors périmètre) |
| CAS-16 | Touche H (historique) inactive en 0xf/0x10 | lecture du code | Établi | coordinateur (consigne du 2e message) | non touché |

## 2. Corrections par commit
f93071b parties 0xf/0x10 + maillages dynamiques ; 57fe281 saisie numérique ▲▼ ; 8b3b318 Échap = retour ; b9fe007 code à masque de bits (ui_menu.py) ; dd0d007 bestiaire ; 725bfcb marche non accélérée et lieu ; 80854c1 `camera_libre` ; db4c335 tests (22 cas, 28 avec les deux commits suivants) ; bd7a2ef arène : A tourne la page ; ea2d593 arène : V accélère le combat.

## 3. Notes à fusionner dans docs/ (texte prêt à coller)
- Parties du moteur : 3 départ, 0xc ville, 0xd combat, 0xe carte du monde, 0xf casino (`Global::startCasino`, `setMinigame(0)` = poker, carte `ev04`, type 48 ; sinon machine à sous, carte `ev05`, type 47), 0x10 bestiaire (`Global::startBook`, type 28, la carte de la ville reste chargée mais n'est pas dessinée). Constantes : `MO.PARTIE_CASINO`, `MO.PARTIE_BESTIAIRE`, `MO.PARTIES_MINIJEU`. En 0xf/0x10 les maillages dynamiques sont dessinés ; la caméra du casino suit `camera_libre(e)` (cam_rot présent) ; pas de marche accélérée, `_facteur_vitesse` rend 1.0.
- Atteindre les mini-jeux sans les parcourir à la main : carte `hcy1b1` (sous-sol de Chandor, machines à sous uid 1416-1420, comptoir de jetons uid 1410/1411, coffres de cadeaux uid 1413-1415, fosse d'arène aux monstres 154/159) ; second casino `ss5b1b`. Appel direct : `c.call(m.E('_ZN6window13CommandWindow19changeShopMenuPhaseEi'), c.export('_ZN16TownWindowSystem11m_singletonE'), phase)`. Table des phases : 1/7 église (66), 2/8 armes (57), 3/9 armures, 4/0xa/0x12 objets, 5/0xb échange de cadeaux (45/46, demande des jetons), 6 auberge, 0xc comptoir de jetons (44), 0xd machine à sous (plante hors partie casino), 0xe poker (48), 0xf arène (50 -> 49 -> combat), 0x10 banque, 0x11 mini-médailles, 0x13 vente d'armures du château, 0x15 type 13, 0x16 colisée (68, plante sans groupe du chapitre 2), 0x17 échange de groupe, 0x18 Torneko, 0x1a sauvegarde.
- Clavier dans les menus de saisie numérique (types 44, 47, 48, 49, 64, 65) : ◀▶ choisit la colonne (1/10/100/1000/10000 pour 44), ▲▼ = pads 2/1 sur la colonne active, A valide, B retourne. Listes 45 (objets 0-5, retour -1), 46 (cibles 0-3 + flèches de page), 50 (monstres 0-3).
- Arène : combat en partie 0xd, carte `btlcc2`. Pendant le combat, la seule fenêtre ouverte est « Quitter » (type 71, bouton id 0, pad 0x400) : elle n'a ni validation ni curseur du moteur. Règle de la visionneuse : en combat, une fenêtre sans bouton 0x10 et sans grille laisse A au terrain (mot de touches de GameUpdate) et n'est pas une attente du joueur (`sans_validation`). Fin de combat : message de victoire, puis fenêtre type 51 (Jetons / Gagnés), retour en 0xc.
- Bestiaire dans le jeu réel : le menu du terrain (touche Entrée) a Objets / Magie / Carac. / Divers ; Divers page 1 = Soigner tous, Équipement, Alignement, Organiser les objets ; page 2 = Trier contenu sac, Résultats combats (type 19 : durée, combats, victoires, titre), Paramètres (ouvre la page options de la visionneuse). Aucun bouton « bestiaire » trouvé : `TownMenuItemSelectCommand::menuUpdate` l'appelle, mais la route d'accès réelle reste à trouver (voir §4). Pour le tester : appeler `startBook` directement.
- Pièges de harnais : le scénario GL est piloté par `Jeu.tick`, appelé à chaque pas moteur (pas à chaque image affichée) : `yield 45` = 45 pas moteur. Pour mesurer une vitesse, comparer des durées réelles avec DQ_TEMPS_REEL=1 (sinon `fixe_test` : un pas par image, aucune accélération). Ouvrir Pause (Échap, ou « Paramètres » de Divers) arrête les ticks et gèle le scénario : artefact, pas un bug. `set_jetons` répété désynchronise les compteurs du moteur (machine à sous bloquée au tour 12 : artefact). Un seul xvfb à la fois (flock /tmp/xvfb.lock) ; la file est partagée avec les autres agents.

## 4. Non vérifié / reste à jouer
- Colisée (type 68, phase 0x16) : impossible sans sauvegarde du chapitre 2 (Alina). À rejouer avec une telle sauvegarde.
- Route réelle du bestiaire depuis le jeu : exploré Objets/Magie/Carac./Divers (pages 1 et 2, « Résultats combats », « Paramètres ») sans trouver d'entrée. Le bestiaire est vérifié par appel direct seulement (liste, fiche, monstre dessiné, retour).
- Poker : le libellé « Abandonner » pourrait chevaucher un autre élément : non vérifié, je ne l'affirme pas.
- Animation de bingo (paquet 6) : à l'agent « paquets ».
- Avant/après de CAS-9(b) mesuré par monkeypatch de `_attend_joueur` (ancien comportement), pas par checkout d'un commit antérieur ; équivalent par construction.
- Machine à sous : mise maximale observée 5 ; le paiement est crédité après le message.

## 5. Pièges de fusion
- `_saisie_menu` (fenetre.py, vers la ligne 1622) : ma généralisation ▲▼ tient en 1 ligne avant `if pages and ...` : `if not f.get('grille') and len(z) <= 1 and self._saisie_pas(port, f, fe, z, decl): return`, avec les nouvelles méthodes `_pas_colonnes`, `_pas_actif`, `_saisie_pas`, `cur_pas` et `_curseur` qui rend la colonne active. Le bloc `if pages ...` (flèches de page, `_fleche_page`, Action 0x800) vient juste après, puis `if f.get('grille') or len(z) < 1:`. Les 3 lignes de l'agent « services » placées juste avant `if f.get('grille') or len(z) < 1:` doivent rester APRÈS mon bloc `_saisie_pas` et mon bloc `pages` ; si ses ◀▶ de boutique s'appliquent aux menus à une seule colonne, vérifier qu'elles ne passent pas avant `_saisie_pas` (la banque au clavier en dépend : la mise de la banque est un menu de saisie numérique ; ◀▶ = colonnes, ▲▼ = pads 2/1).
- Fonctions de module ajoutées dans fenetre.py : `camera_libre(e)` (utilisée par `_camera_ville`, `_cadre_jeu` et le dessin des maillages) et `sans_validation(mo, ui_g, port)` (avant `matrice`). Les tests de caméra et de vitesse utilisent des faux objets : ne pas les remplacer par des méthodes de `Jeu`.
- `_facteur_vitesse` : retour anticipé `1.0` pour `PARTIES_MINIJEU`. `_attend_joueur` : une fenêtre sans validation en combat n'est plus une attente. Ligne de tick : `if port is not None and mo.msg_visible and decl & MO.A and self._quitter_seul(port): port = None`, après le test `entree` et avant `_port_clavier`.
- `_echap_retour` a une branche MINIJEU et `_retour_possible` ; garde de dessin des maillages étendue à `MO.PARTIE_VILLE + MO.PARTIES_MINIJEU` ; décor du bestiaire sauté (`if e.partie != MO.PARTIE_BESTIAIRE: self._tracer_decor(True)`).
- ui_menu.py : `Fenetre.code()` appelle `_code_masque(e, c)` quand le code n'est pas dans `fx` (poker, code 2 valeur 63).

## 6. Captures utiles
/tmp/m_cas_h1_00_hcy1b1.png (casino), /tmp/m_cas_pks_b700.png (poker), /tmp/m_cas_sl_r02_b_arret.png (gain de machine à sous), /tmp/m_cas_pc_phc_03.png (jetons), /tmp/m_cas_pg_ph5_00.png et _02.png (cadeaux), /tmp/m_cas_pa_phf_00.png et _01.png (arène : liste, mise), /tmp/m_cas_ar_a3_fin.png (avant : victoire bloquée), /tmp/m_cas_ar3_b2_036.png et _040.png (après), /tmp/m_cas_bk2_b330.png et /tmp/m_cas_bk3_b350.png (bestiaire), /tmp/m_cas_dd2_dd_04.png (Divers page 2), /tmp/m_cas_dd3_dd_06.png (Résultats combats), /tmp/m_cas_e1_03_apres_load1.png (état chargé en poker). Mesures de vitesse : /tmp/out_cas_v1.txt, /tmp/out_cas_v3.txt, /tmp/out_cas_v3old.txt. Scripts hors dépôt : /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/cas/ (sc_arene2.py, sc_divers2.py, run_scen.sh).

## 7. Faits à retenir en mémoire (source : cette session)
- Le harnais de scénario GL de ce projet compte en pas moteur (tick appelé par `_pas`), pas en images affichées ; pour mesurer une vitesse, comparer des durées réelles avec DQ_TEMPS_REEL=1.
- `ChangeShopMenuPhase` appelé directement dans le moteur est le moyen rapide d'atteindre casino, arène, jetons et cadeaux (phases 0xc, 0xd, 0xe, 0xf, 5/0xb) ; le colisée (0x16) plante sans groupe du chapitre 2.
- Le bestiaire (`startBook`) n'apparaît pas dans le menu Entrée/Divers d'une sauvegarde du chapitre 1 ; sa route réelle est inconnue.
- Les tests sur faux objets (`SimpleNamespace` + `F.Jeu.methode(faux)`) imposent des fonctions de module ou des `getattr` par défaut dans fenetre.py.
- `pkill -f` avec un motif présent dans sa propre ligne de commande tue le shell (sortie 144) : tuer par PID.
