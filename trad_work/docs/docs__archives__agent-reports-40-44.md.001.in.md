# Rapports finaux des agents des lots #40 à #44

Rapports bruts remis par les sous-agents de la session du 31/10 au 02/11 (enquêtes, audits, correctifs) ; les notes utiles sont déjà fusionnées dans `docs/notes-*.md`. Les chemins `/tmp/...` cités n'existent plus.

---

## Agent a7fa4380330259e25 — 31/10 16:16

RAPPORT : ombres (A) et eau des grottes (B). Rien n'a été modifié dans le dépôt (`git status` propre ; `git apply --check` OK pour les deux patchs). Tout est dans le dossier de travail S = /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/enq_deco

== CAUSE COMMUNE à B et aux ombres de décor (vérifiée) ==
La visionneuse ignore le `_Color` des matériaux de carte et trace tout le décor « opaque » (`data.py::_texture()` ne lit pas `_Color` ; `window.py::_tracer_decor` utilise cutoff 0,5, écriture de profondeur, LESS). Le jeu d'origine choisit le shader à l'exécution dans `FldObject.set_shader` (RVA 0xCD5414) :
- nom de texture sans ".tim", OU `_Color.a != 1` -> `Custom/fld_trans` (Blend SrcAlpha/OneMinusSrcAlpha, ZWrite off, ZTest LEqual, file 3000 + `prio` via `FldObject.set_priority` 0xCD7DA8) ;
- sinon texture RGBA32 -> `fld_atest` (rejette seulement alpha == 0) ; sinon `fld_normal`.
Dans tous les `fld_*` : couleur finale = texture x (couleur de sommet x `_Color`).

== B. Eau des grottes ==
Cause : les modèles d'eau (objets `<carte>wt..`, texture `mawater1.tim` RGB24, cyan moyen (54,205,203), alpha 255) ont `_Color` = (1,1,1,0.2). La visionneuse les dessinait à alpha 1 : cyan plein, d'où l'effet « électrifié ». Les palettes `wtkira` (FPLP) n'existent que dans les 37 cartes de plein air et de ville, pas dans les grottes : ce n'est pas une piste. Aucun blend additif.
Correction : patch `S/out/correctif_decor.patch` (data.py + window.py, s'applique tel quel au dépôt).
- `_texture()` renvoie aussi `_Color` et le « genre » (trans / atest / normal) ; `cuire` multiplie `_Color` dans les couleurs de sommet (et dans `_images`) ;
- les matériaux « trans » ont leur groupe `('tr', prio, key)` ;
- `_tracer_decor` dessine d'abord les groupes opaques, puis les `('tr', ...)` triés par prio, avec profondeur en lecture seule, LEQUAL et cutoff 0 ;
- le cache passe de `carte5_` à `carte6_` (2 endroits dans data.py ; les anciens caches sont ignorés, donc première extraction plus lente).
Preuve (grotte `dgb1`, centre du bassin, RGB) : (38,141,140) -> (29,87,93), luminosité 0,55 -> 0,37. Le gaz, les cascades et la brume (textures `.tm2`) deviennent aussi doux. Sortie du patch propre identique pixel à pixel à mon expérience (diff max 0).
Captures avant (gauche) | après (droite), dans S/out/ : pair_dgb1.png (la plus claire), cmp_dgb1_pool.png (gros plan), pair_dlb4.png, pair_deb2a.png, pair_dob1.png, pair_dnb2.png, pair_djb1.png. Brutes : dgb1_av_b80.png / dgb1_ap_b80.png.

== A1. Ombres de décor (« trop brutes » et « pas tout a des ombres ») ==
Les ombres de décor sont de la géométrie à part, à y = 0 (collée au sol) : `idokage1` (puits), `maokage1`, `maoutsk1`, `*kg*`. Deux cas, une seule cause (la même que B) :
- ombres douces en `.tm2` à alpha faible (`kage1c` {0,14,28,42,86}, `kage1a` max 126, `hcokage1` / `ceokage1` max 96, `tekg1` max 126) : le cutoff 0,5 les rejette toutes -> puits, bâtiments et autres sans ombre (51 cartes sur 670 touchées) ;
- ombres en `.tim` à alpha binaire (`nk_sk1kg`, `y_sk2bkg`) avec `_Color.a = 0,4` ignoré -> noir à 100 %, donc « brutes ».
Le patch de B règle les deux. Avant/après : S/out/pair_maout_well.png (puits) et pair_maout.png. La piste « LESS au lieu de LEQUAL » a été testée et écartée (dq4_t1 : aucune ombre en plus).

== A2. Ombre des personnages (héros et PNJ) : prototype fait, ville seulement ==
Pourquoi absentes : la visionneuse ne les dessine pas. Le moteur ne les commande pas en ville : le paquet 15 (`chara_shadow`) n'y est jamais envoyé (vérifié dans les logs de maout), donc l'ombre par défaut de `Chara` s'applique à tous. Sur la carte du monde il n'envoie que `[522]` / `[523]` (cache les ombres des emplacements 10 et 11). `engine.py::Etat.appliquer` ne traite pas le paquet 15.
Rendu d'origine (décodé depuis `Chara.SystemInit` et `SetShadowPosition` 0xCCCF38) :
- maillage `s_shadowMesh` : carré ±1 en XZ à Y = 0,00625, UV (0,0)(1,0)(1,1)(0,1) ; échelle `s_shadowDefScale` = (0,347 ; 10 ; 0,206) -> ellipse de 0,694 x 0,412, à 0,0625 au-dessus du plan ;
- texture `CharaTex/common` (32x32, noire, alpha 96/255 = 0,376 dans l'ellipse, 0 dehors, binaire, filtre point, clamp). Extraction : `Donnees.texture('common')` ; aperçu S/out/tex_common.png ;
- shader `Custom/CharaShadow` : tex x `_Color`, Blend SrcAlpha/OneMinusSrcAlpha, ZWrite off, ZTest LEqual, Cull Back, file 2999 (avant le sprite) ;
- position = position du Chara + rotation du panneau x (0 ; 0 ; 0,25), soit côté visionneuse `p - f_*0,25` : même point à l'écran, mais décalé vers la caméra, donc devant le sol ; orientation = lacet seul de la caméra, à plat ;
- alpha final = 0,376 x `SetShadowAlpha` (1 par défaut) x alpha du sprite si < 1 (`SetColorWithShadow`) ; `SetVisible` masque aussi l'ombre sauf `m_bSeparateShadow` ; objet d'ombre inactif si `no` vaut 193 ou 194.
Prototype : patch `S/out/correctif_ombre_chara.patch` (à appliquer APRÈS correctif_decor.patch ; window.py seulement, nouvelle méthode `_dessiner_ombres_chara`, constantes `OMBRE_DEMI` / `OMBRE_HAUT` / `OMBRE_DEC`). Les deux patchs cumulés donnent exactement `S/prop/fenetre.py` et `S/prop/donnees.py`, les fichiers que j'ai testés.
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
- Piège : lancer le désassembleur `/home/claude/il2/disasm.py` depuis /home/claude/il2 (il ouvre `libil2cpp.so` en chemin relatif) ; mon `S/dis_r.py` en est la version avec chaînes résolues.

Fichiers : S/out/correctif_decor.patch, S/out/correctif_ombre_chara.patch, S/prop/ (versions patchées testées), S/out/*.png (captures ci-dessus).

---

## Agent adb969ea65cc6b771 — 31/10 16:48

RAPPORT (lecture seule : dépôt /home/claude/dq4-portage non modifié, `git status` vide, HEAD 63f2cc1 = main avec #18/#19). Tout est dans SCR = /tmp/claude-0/-home-claude/17145693-c62f-5af6-a741-2d4f94a36edf/scratchpad/enq_cb/ . Patch complet prêt à appliquer (non appliqué) : SCR/propositions.patch (syntaxe vérifiée).

Méthode : copie instrumentée du code, un combat complet de 687 pas moteur (slot 5, 2 Glacyclones, attaques/effets, dégâts, mort, fin), capture de CHAQUE pas (images f = tracé D1, g = tracé D2, car le moteur tourne à 30 Hz et l'affichage à 60 Hz = 2 tracés par pas) + meta.jsonl (paquets, positions, ordre de tracé).

=== 1) « Vibration » à l'apparition des ennemis et 2) clignotements d'animation : UNE SEULE cause, vérifiée ===
Cause : tampon de sommets des monstres envoyé au GPU avec un tour de retard.
- pyglet : `vl.position[:] = ...` ne fait que marquer le tampon « sale ». L'envoi GPU se fait dans `buffer.commit()`, appelé par `Jeu._tracer` (window.py l.396-408) uniquement quand le domaine change (`dom is not self._dom_lie`).
- `_dessiner_scene` (l.1659) met `_dom_lie = None`, puis `_tracer_decor()` (l.1668) lie et commit le domaine unique (toutes les vertex_list sans batch explicite partagent le même). Ensuite `_maillages_combat(e)` (l.1669, appelé dans l'en-tête de la boucle) RÉÉCRIT les sommets des monstres/effets : le domaine étant déjà lié, plus aucun commit : les monstres sont dessinés avec les données de l'image précédente (le commit ne passe qu'au tracé suivant, via `_dom_lie = None`).
Preuves (mesures) :
- Dès le 1er pas du combat : au pas 3 les monstres sont ABSENTS en D1 (masque 0 px) et présents en D2.
- Pendant la caméra d'entrée (pas 4-33, 1280x720, runs k1 vs k2) : écart D1/D2 du bord haut des monstres moyenne 3,7 px, max 11 ; bord gauche moyenne 3,2 px, max 7 ; surface moyenne 4,5 %, max 10,5 % ; 52 inversions de sens sur 60 images affichées avec le code actuel, 0 avec le correctif. Pendant ce dolly les monstres bougent de 0,33 à 0,05 unité par pas : le retard d'un pas alterne avec 0 retard à 60 Hz = vibration avant/arrière.
- Combat entier à HEAD (all_n1 vs all_n2, 640x360) : D1 ≠ D2 sur 415/687 pas (60 %, jusqu'à 19 070 px de différence) avec le code actuel, 0/687 avec le correctif (D1 == D2 exactement). Même résultat sur l'ancienne copie (m1/m2). Les maillages d'effets (slot 2, ~10 pas) et ceux des monstres changent à CHAQUE pas, d'où le clignotement des attaques, sorts, et animation de l'ennemi qui attaque.
- Image : SCR/cs_m1_130.png (actuel : l'éclair et le monstre qui saute alternent entre deux poses) vs SCR/cs_m2_130.png (corrigé : mouvement monotone). Chiffres : SCR/d1d2.json, SCR/d1d2_n.json ; scripts SCR/d1d2.py, SCR/d1d2b.py.
Correction précise : window.py, `_dessiner_scene`, branche `elif bataille:` ; remplacer la ligne 1669 `for tex, tw, th, vl, shader, hd in self._maillages_combat(e):` par :
```
mons = self._maillages_combat(e)      # réécrit les sommets (tampons « sales »)
self._dom_lie = None                  # force rebind + commit() au 1er tracé
for tex, tw, th, vl, shader, hd in mons:
```
(Variante équivalente : appeler `_maillages_combat(e)` avant `self._dom_lie = None` de la l.1659, comme les sprites juste au-dessus.) Vérifié : avec ce correctif, aucun trou ni clignotement résiduel sur les 687 pas (pas de motif A-B-A, pas de lacune de paquet 22 pour les emplacements 0/1 ; les sauts de surface restants sont des animations pilotées par les données).
Incertitudes : (a) l'effet visible dépend de la fréquence d'affichage : à exactement 30 Hz le retard est constant (pas de vibration), à 144 Hz 1 tracé sur ~5 est périmé ; (b) un seul combat étudié (2 Glacyclones) : pas testé avec 3-4 groupes ni d'autres sorts ; (c) la capture « 2 tracés par pas » simule le 60 Hz ; je n'ai pas mesuré sur un vrai écran. Risque latent distinct, non visible ici : l'ordre de tracé de monstres de même file (2150) bascule à cause de différences de 1e-3..1e-5 sur la profondeur du centre AABB (l.762-763, `out.sort(key=lambda o: o[0])`, bascules aux pas 3, 5, 8, 14, 20, 24...) ; recouvrement des 2 Glacyclones mesuré à 0 px sur 109 pas, donc invisible ici ; si un recouvrement apparaît, clé stable proposée : (file, -profondeur arrondie à 1e-3, emplacement).

=== 3) Boîte de message de combat trop haute ===
Cause : hauteur définie côté visionneuse par la géométrie du type de fenêtre dans cache/ui_layout.json['message']['types'] (frameData 192/193/194), choisie par le message moteur `[0,n]` (port 1, MenuMessage). Le début de combat envoie le TYPE 1 (cadre 193 : 188 unités de haut, canevas 164 lignes = 4 lignes de 34) alors que le terrain (type 0) = 126 unités, canevas 100,5 = 3 lignes ; type 2 = 122 à l'échelle 0,9 ; type 0 en fin de combat = 126. Le bas est calé par `_dz_message` (window.py l.1073-1081) sur `CB_MSG_BAS = -338` (l.62), indépendamment de la hauteur.
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

Lacunes de window.py, par priorité
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
