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
- b5e9e9c savestates.py + engine.py + tools/test_etats_correctifs.py : correctifs mémoire rejoués au chargement d'un état.
- 759744c data.py + test_map_items.py + tools/test_textures_carte.py : texture blanche, cache carte10_ (la rename a un coût : les cartes se re-préparent au premier lancement, ~80 s ici pour 670).
- 9986244 data.py + tools/test_decors_racine.py : décors à maillage racine (32 cartes). Même version de cache carte10.
- 9aa363d engine.py + tools/test_cartes_pnj.py : sprite jamais positionné = origine.
- b5669fe data.py + test_map_textures.py : purge des carte9_.
Tous les tools/test_*.py passent (DQ_CACHE_CARTES=/tmp/cache44) ; pyflakes : seuls avertissements connus.
Fichiers hors de mon périmètre touchés : engine.py (Etat.appliquer : ligne de création de sprite (clé 'cree') et bloc paquet 13 pose ; constante ORIGINE_APRES ; méthode Moteur.reappliquer_correctifs) et savestates.py (un appel) = zone de l'agent « paquets » : risque de conflit de fusion sur ces deux blocs.

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
- 6d39f59, « Statut (types 13-17) : Q / D / L / R tournent les pages au clavier » (SRV-10), window.py, +3 lignes dans `_saisie_menu`, juste avant `if f.get('grille') or len(z) < 1:`.
  - Une fenêtre sans grille ni bouton A envoie maintenant ◀ ▶ (pads 8 / 4) au port qui porte les flèches de page, via `_port_pour_manette`.
  - Avant, clavier seul (/tmp/srv/scen_stat2.py) : R, D, PageBas, A, Q, PageHaut laissent « 1/4 ».
  - Après : R 2/4, D 3/4, PageBas 4/4, R 1/4 (boucle), A 4/4, Q 3/4, PageHaut 2/4.
  - pyflakes : un seul avertissement, `window.py:2203 'sel'` inutilisé, antérieur à mon commit. `tools/test_entrees.py` (37 tests) et `test_pause_pages.py` (16 tests) passent.
- Fichiers touchés : uniquement `dq4_pc/fenetre.py`. Rien hors window.py / ui_menu.py / engine.py.

3) NOTES À FUSIONNER DANS docs/ (prêtes à coller)

**technical-notes-dq4-port.md, « Services en ville : phases `cmd_menu_shop` » (02/11/2026, mission SRV)**
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

**viewer-notes-dq4-pc.md**
- Touches de test : B = RETOUR ARRIÈRE (pas Échap, qui ouvre la Pause et gèle la boucle), Menu = Entrée, haut / bas = Z / S, gauche / droite = Q / D, L / R = A / R.
- Statut : Q, D, L, R tournent les pages (6d39f59). Auberge : fondus OK. Oui / Non à la souris OK.
- Banque et mise du casino : pas de saisie clavier tant que les ▲ ▼ ne sont pas généralisés.

**coverage.md §2, mises à jour des statuts**
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
- window.py `_saisie_menu` : mon insertion (3 lignes) est juste avant `if f.get('grille') or len(z) < 1:`. L'agent « casino » modifie la boucle `for bit, pad in dirs` juste dessous. Conflit textuel probable mais trivial : garder les deux blocs. Après fusion, rejouer /tmp/srv/scen_stat2.py (doit finir 2/4, 3/4, 4/4, 1/4, 4/4, 3/4, 2/4) et /tmp/srv/scen_bank.py (la saisie clavier du montant doit changer les chiffres).
- Pour l'agent « paquets » : l'auberge jouée par appel direct ne montre pas les poses couchées (pas de script). À regarder via le PNJ réel.

7) À RETENIR (pour la mémoire, appris dans cette session)
- Les sauvegardes réelles de l'utilisateur sont toutes au chapitre 1 (data1, data2, data4, data5 ; data3 vide). Source : décodage avec /tmp/specs/dq4_sauvegarde.py.
- Le verrou /tmp/xvfb.lock est partagé entre tous les agents : les scénarios GL attendent plusieurs minutes chacun (source : /proc/locks).
- `pkill -f motif` tue aussi le shell appelant si le motif figure dans la commande : utiliser des PID.
- En scénario GL : B = RETOUR ARRIÈRE, Échap = Pause (bloque la boucle), Menu = Entrée.

---
