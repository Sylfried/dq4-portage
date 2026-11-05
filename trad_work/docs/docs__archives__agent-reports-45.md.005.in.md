## Agent « magie » (afd84db2f3277f278) — 02/11 21:31

RAPPORT FINAL, mission « magie » (PR #45, préfixe MG)
Worktree /home/claude/wt45-magie, branche agent45-magie (base 84b3f22). `git status` propre. Aucun push, aucun changement de branche, aucune PR. Fichiers patch FR et sauvegardes de l'utilisateur non touchés (tests dans /tmp/sv_*, RG /tmp/rg_mg1.json, cache /tmp/uicache4).

COMMITS (tous avec les 2 lignes de pied)
- 220cd36 Magie : la rangée fantôme de la liste des sorts (code 6 de Make_NameButton) n'existe plus  [points 1, 2, 4]
- b340625 Magie : « Coût en PM:<tab>  2 », la tabulation vaut 8 espaces (TextMesh.tabSize)  [point 3]
- 757c841 test de la liste des sorts, de la ligne de coût et des usages sans effet (moteur d'origine)  [points 2, 4, 5]
- 670b8a0 Fenetre.code tolère les Fenetre factices des tests (getattr noms_liste)  [correctif de mon changement : test_casino_bestiaire cassait]
- 061ac13 MG: fiche d'un sort, la ligne de coût et la description tiennent dans leurs cadres  [point 3 et point 4 : touche la zone partagée « texte », Rendu._texte]
Fichiers modifiés : dq4_pc/ui_menu.py (+56) et tools/test_magie_liste.py (nouveau, 23 tests dont 8 sur le vrai moteur).

POINT 1, reproduction : FAIT (Établi)
Sauvegarde emplacement 1 : Ragnar (PM 0) + Doc (invité niveau 255, 30 PM, sort 196 Premiers secours). Menu terrain, Magie (id bouton racine 1), Doc (id 3 du port 5), clic sur « Premiers secours » : je retrouve exactement les écrans 7 et 8 de Sylfried. Captures avant : /tmp/m_magie45av_b110.png, b180, b250, b320. Après : /tmp/m_magie45ap_b110.png, b180, b250, b320.

POINT 2, origine de <ERR 0x07000000.0> / <ERR 0x03000000.0> : FAIT (Établi)
Cause racine : le moteur règle la mise en page de la liste de boutons nommés (Make_NameButton, type 8) par le code 6 = preset (NOMS_PRESETS, MenuPortItemTable.name_button_param), que la visionneuse ignorait. Résultat : une 5e rangée fantôme restait visible et cliquable sous « Premiers secours » (la liste de Doc n'a qu'un sort). Le clic envoyait au moteur le bouton 4, c'est-à-dire un sort inexistant. Les textes <ERR 0x07000000.0> (nom absent), <ERR 0x03000000.0> (description absente) et « Coût en PM  0/ 30 » sont les chaînes de repli du moteur pour un sort absent (le « ERROR %d » aussi). Correctif : `Fenetre.code` applique le preset (`_liste_noms`) ; seules les rangées dont le code n'est pas 0 sont actives ; idempotent, preset inconnu ignoré. Le menu d'action des objets (preset 1, 5 rangées) garde sa logique. Testé de bout en bout sur le vrai moteur : liste de Doc = 1 rangée (codes [2,0,0,0,0]) ; nom, description, coût, Lancer, cible, effet et PM dépensés fonctionnent (PM 30 vers 28, PV de Ragnar 20 vers 47, message « Les blessures de Ragnar guérissent ! » affiché dans la fenêtre de message, « ; » du nom consommé).

POINT 3, « Coût en PM » : FAIT pour la liste des magies et la fiche du sort ; AUDIT PARTIEL
- Liste (b340625) : le texte du moteur est « Coût en PM:<tab>  2 » avec TextMesh.tabSize = 8. La police de la visionneuse n'avait aucun glyphe pour la tabulation (largeur nulle), d'où « Coût en PM: 2 » collé. Unity compte une tabulation comme tabSize espaces : elle devient 8 espaces. Limité à Make_NameButton.
- Fiche du sort, type 7 (061ac13) : « Coût en PM 10/ 30 » (FR) dépassait du cadre de droite (texte de 154 à 160 unités depuis x=75 pour un cadre x 63 à 221 ; la version anglaise tenait). La ligne (nœud 2) porte maintenant une limite droite `fit_x = COUT_FICHE_X_MAX = 214` (cadre moins la marge des plaques, 7) et `Rendu._texte` la comprime (facteur mini 0,7 ; ici environ 0,88) même avec la police bitmap d'origine. Le nom, « Lancer » et la description ne changent pas. Capture : /tmp/m_magie45k2_b110.png (Évac' 1/30), b180 (Protection sacrée 4/30), b250 (Multisoin 10/30), b320 (Rappel 8/30), b390 (Téléportation).
- Non vérifié : les autres fenêtres à tabSize de la mise en page : type 20 Make_MemberShift (8), 34 Make_BattleGo (8), 35 Make_BattleIM (8), 31/33/39 (monstres, 25). La même règle (tabulation = tabSize espaces) y serait fidèle à Unity, mais je ne l'ai pas généralisée faute de pouvoir tester en combat (zone « combat » d'un autre lot ; battle_history.py gère « \t×3 » à part). Extension d'une ligne : retirer `self.noms_liste` de la condition dans `Fenetre.param_str`. Écran Statut et PM courant/max d'autres écrans : non audités (les écrans PM du menu terrain, listes de personnages « PM 30/ 30 », s'affichent correctement sur les captures).

POINT 4, liste des sorts : FAIT (Établi, sauf mention)
4 rangées par page ; flèches de page et « 1/2 » (2/2, 4/4 avec 13 sorts) ; pas de sort grisé : le moteur refuse par « Pas assez de PM ! » ; clavier (BAS déplace le curseur, DROITE tourne la page, ESPACE valide, RETOUR en arrière) et clic souris fonctionnent ; Ragnar seul : message du jeu « Ragnar n'a appris aucun sort ni aptitude pour d'autres situations que le combat ! » (capture /tmp/m_magie45n_b110.png) ; seuls les membres avec sorts sont cliquables.
Autre défaut trouvé et corrigé dans 061ac13 : 9 des 18 sorts de terrain ont une description FR de 3 ou 4 lignes (coupées vers 20 caractères) pour un cadre de 2 lignes ; la 3e ligne sortait du cadre puis de l'écran (Multisoin, Rappel, Résurrection, Téléportation, Évac', Coup d'oeil, Passage sûr, Protection sacrée, Tic-tac). Au-delà de 2 lignes, `Rendu._recoupe` remplace les retours à la ligne par des espaces et recoupe à la largeur du cadre (DESC_FICHE_X_MAX = 148, le cadre va jusqu'au bouton retour) : les 18 tiennent sur 2 lignes (captures k2 ci-dessus). Le texte envoyé par le moteur n'est pas modifié ; un texte qui ne diminue pas de lignes reste tel quel ; ≤ 2 lignes : inchangé. Supposé : le mobile d'origine coupait aussi ces descriptions (cadre de 2 lignes) ; je n'ai pas pu le vérifier.

POINT 5, actions sans utilité : FAIT sur le moteur ; DÉCISION À TRANCHER pour le message
Preuves par traces de paquets sur le vrai moteur (tests MoteurReel) :
- Premiers secours sur Ragnar aux PV pleins : le moteur affiche « Doc lance le sort Premiers secours ! » puis « Les blessures de Ragnar guérissent ! » (le même message qu'à PV bas, trompeur), et ne dépense AUCUN PM (30 vers 30). Règle : `BaseAction::useMp` (0x1a7424) ne dépense que si l'octet [this+0x14] vaut 1 (l'action a eu un effet). Sur blessé : PM 30 vers 28, PV 20 vers 47.
- Rappel sur un vivant ; Antipoison sans poison : « Mais rien ne se passe. », aucun PM dépensé (le texte b0802000.mpt contient aussi « Mais il ne se passe rien. » et « Mais le sort échoue. »).
- Antipoison sur un empoisonné : « Ragnar n'est plus empoisonné ! », PM 30 vers 28. Rappel sur un mort : « Ragnar revient à la vie ! », PM 30 vers 22.
- PM insuffisants : « Pas assez de PM ! », rien de dépensé, rien d'appliqué.
- Objets (essais sur le moteur, scripts dans le scratchpad) : un objet sans effet n'est pas consommé.
La visionneuse laisse le moteur décider et affiche ses messages (fenêtre de message vérifiée par capture : /tmp/m_magie45m_b390.png). Il n'y a donc pas de bug côté visionneuse. Le souhait de Sylfried (un message du type « ça n'a pas grande utilité ») est un écart assumé par rapport à l'original, pour les sorts de soin à PV pleins. Je ne l'ai pas implémenté, c'est à lui de trancher. Si oui : cas à repérer côté moteur (PV avant = PV après, PM inchangés) et message à ajouter dans la zone « effet ». Non vérifié : lecture des sons (seuls les ids SE 300/306/501 observés côté moteur).

NOTES POUR LA DOC (prêtes à coller)
- Sorts de terrain (ids moteur 196 à 216) : 196 Premiers secours (2 PM), 197 Soins partiels (4), 198 Soins complets (6), 199 Multisoin (10, sans cible), 200 Rappel (8), 201 Résurrection (15), 202 Antipoison (2), 203 Téléportation (1), 204 Évac' (1), 205 Coup d'oeil (2), 206 Passage sûr (2), 207 Protection sacrée (4), 208 Tic-tac (4), 209 Mappille (0), 212 Détectrésor (0), 213 Fouille (2), 216 Sifflet (0). L'id 214 (Discreto) donne une description <ERR 0x03000000.0> et « ERROR 0 » (id artificiel). Les ids 157 à 160, s'ils sont appris, apparaissent dans la liste de terrain avec des noms <ERR 0x07000000.0>.
- Ids de boutons : menu racine Objets=2, Magie=1, Caractéristiques=4, Divers=5 ; Magie : port 5 liste des persos (Doc=3, Ragnar=2), port 8 liste des sorts (port 7 = pagination), cmd(8,rangée) ouvre la fiche (port 12 : nom, description, coût « Coût en PM  2/ 30 » = coût/PM courants, « Lancer »), cible = cmd(6,k) ; sort sans cible : « Lancer » = rangée 2 du port 8. Objets : cmd(4,2), puis cmd(5,3) (Sac), port 9 liste, port 8 menu d'action (preset 1), port 6 cible. Entrées : A=16, B=32, flèches 8/4/2/1, menu 0x800, parole 0x100. Clavier de la visionneuse : A=ESPACE, B=RETOUR ARRIÈRE.
- Make_NameButton : racine + 6 parts de rangée ; code 6 = preset (NOMS_PRESETS : (nombre de rangées, ordonnée de départ, pas)) ; code de rangée 0 caché, 1 visible, 2 sur deux lignes (nom relevé, ligne de coût). Pour les ports < 12, la commande 1 n'efface pas `cases` : les textes d'anciennes rangées cachées subsistent mais ne s'affichent pas.
- TextMesh.tabSize : une tabulation = tabSize espaces (pas de taquets).
- Offsets moteur : PlayerStatus = `_ZN6status9PartyData15originalPlayer_E` + 0x530*i ; HaveStatus +0x58 (PV +0x22, PV max +0x24, PM +0x26, PM max +0x28) ; HaveStatusInfo = HaveStatus − 0x48 (StatusChange +0x198, poison id 0x16) ; HaveAction +0xd0 (getCount, getAction(i), add(id,0), clear).
- Police bitmap (SE-GARRIR) : l'espace avance de 5 px ; avec elle `Rendu._texte` ne comprimait jamais le texte (porte `not bm`) : tout dépassement FR n'est donc corrigé nulle part ailleurs que par des limites explicites comme `fit_x`.

NON TRAITÉ / NON VÉRIFIÉ
- Tabulations des types 20, 31, 33, 34, 35, 39 (voir point 3).
- Téléportation : interface du choix de destination non testée (seul le début de la fiche l'est). Sort de combat (id 26) de l'emplacement 3 non testé. Descriptions d'objets (menu Objets) non auditées : le recoupage ne s'applique qu'au type 7.
- Aspect de la tabulation (écart de 8 espaces) comparé à l'original mobile : Supposé fidèle (sémantique Unity), pas comparé à une capture mobile.
- Sons : lecture non vérifiée.
- Source des cadres du haut (nom | Lancer | coût) et du bas de la fiche : non identifiée dans le code (la fenêtre type 7 n'a aucun maillage) ; mes limites 214 et 148 viennent de mesures sur les captures (cadre de coût x 63 à 221 ; cadre du bas jusqu'à 155,5, en unités). Si la mise en page des cadres change, ces deux constantes (COUT_FICHE_X_MAX, DESC_FICHE_X_MAX en haut de ui_menu.py) sont à revoir.

PIÈGES DE FUSION
- ui_menu.py : constantes NOMS_PRESETS, NOMS_DEPART, NOMS_PAS, COUT_FICHE_X_MAX, DESC_FICHE_X_MAX ; `Fenetre.__init__` (noms_liste, noms_dec) ; `Fenetre.code` (branche code 6) ; `Fenetre.param_str` (tabulation et marqueurs fit_x / wrap_x, juste avant `nd['text']['text'] = s`) ; nouvelle méthode `Fenetre._liste_noms` ; `Rendu._texte` (zone « texte ») : `N = len(lignes)` déplacé après le recoupage, deux lignes ajoutées (wrap_x, fit_x) et la condition de compression devient `(not bm or fit_x)` ; nouvelle méthode `Rendu._recoupe`.
- Les fenêtres Make_NameButton sont touchées globalement (menu d'action des objets : logique inchangée).
- Les tests d'autres lots qui fabriquent de fausses Fenetre doivent passer par getattr (déjà fait dans `code`).
- Tests : `python3 tools/test_magie_liste.py` (partie interface, 15 tests) ; avec `DQ_APK="/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks" DQ_SAVES=/mnt/user-data/uploads/dq4-portage/dq4_pc/sauvegardes` : 23 tests OK en 22 s. Passent aussi : test_casino_bestiaire, test_plaque_depart, test_reglages_interface, test_panneau_interface, test_pause_pages, test_historique_messages, test_reglages_son_texte. pyflakes : seul l'avertissement connu `ax` (ui_menu.py:1076, antérieur).

À TRANCHER PAR LE COORDINATEUR / SYLFRIED
1. Message sur les soins à PV pleins (écart par rapport à l'original, voir point 5).
2. Généraliser la tabulation aux types 20, 34, 35 (combat) après test en combat.
3. Le recoupage des descriptions modifie l'affichage du texte du patch FR (sans changer le texte) : à confirmer par rapport à ce que Sylfried voit sur son mobile.

INFORMATIONS À RETENIR (mémoire, apprises dans cette session)
- Emplacement 1 : Ragnar (PM 0) + Doc (invité niveau 255, 30 PM, sort 196) ; sorts de terrain ids 196 à 216 ; Objets=bouton 2, Magie=bouton 1 ; A=ESPACE, B=RETOUR ARRIÈRE.
- Le verrou xvfb (/tmp/xvfb.lock) est très disputé : un job peut attendre 15 minutes et plus.

CAPTURES (absolues)
Avant : /tmp/m_magie45av_b110.png, b180, b250, b320. Après : /tmp/m_magie45ap_b110.png, b180, b250, b320. Fiche du sort après 061ac13 : /tmp/m_magie45k2_b110.png, b180, b250, b320, b390 ; /tmp/m_magie45j_b110.png (Multisoin) et b180 (Premiers secours). Message de lancement : /tmp/m_magie45m_b390.png. Ragnar seul : /tmp/m_magie45n_b110.png. Liste paginée : /tmp/m_magie45m_b180.png et /tmp/m_magie45k_b110.png à b740. Écrans de Sylfried : /tmp/specs/img45/ecran7_pc_magie_liste_cout_pm.png et /tmp/specs/img45/ecran8_pc_magie_ecran_ERR.png.
