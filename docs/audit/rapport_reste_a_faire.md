> **Copie du Claude Doc « DQ4 PC — Ce qu'il reste après l'audit »** (lien : https://claude.ai/artifact/5q6Cs8Br27SGqahx1AkvD4), exportée le 02/11/2026 au soir. Le rapport date de l'état **#44**. Depuis, l'avance **#45** (PR fusionnée, `main` 71fcd53) a traité : les **poses couchées** (oubli n° 1, paquets 16 / 17 / 18, shader `CharaSleep`), la cause de l'effet de rideau au lancement et des micro-images au changement de carte, le décor de combat selon l'heure (le soir existe, l'aube non), l'effet de coup critique, les rencontres aléatoires à marche accélérée, le menu Magie. Puis **#46** (docs et audit versés au dépôt), **#47** (retours de 22 h 29 : pause, caméra toujours centrée, titre, combat, historique, sorts, bruitages) et **#48** (retours de 07 h 33 du 03/11 : sorts sans effet, transition x1, historique au clavier). Le reste de la liste est **inchangé** et doit être reconfirmé avant d'être cité ; les réponses de Sylfried du 03/11 sont dans la section « Réponses de Sylfried (03/11/2026) » ci-dessous. Les points nouveaux de #45 sont dans `docs/notes-visionneuse-dq4-pc.md` (« Avance #45 », sous-sections « À trancher par Sylfried » et « Non vérifié (#45) »).

# DQ4 PC — Ce qu'il reste après l'audit

2026-11-02 · @Sylfried

## En bref

> **Mise à jour du 03/11/2026 à 15 h 50 (lecture de Sylfried)** : voir la section « Lecture du 03/11 » plus bas. Les compteurs ci-dessous (18 / 15 / 11 / 20) datent du 02/11 ; l'état à jour est dans les issues GitHub (#51 à #99 et #101) et dans `lacunes_connues.md` (réponses de 16 h 47 : section « Lecture du 03/11 (16 h 47) »).

Le portage fonctionne sur tout ce que j'ai pu essayer sous Linux, mais **rien n'a été validé sous Windows ni sur un vrai GPU** : c'est le premier reste. Ce rapport compte **18 points qui attendent ta décision**, **15 oublis** de ma part, **11 bugs** connus ou probables et **20 points non vérifiés**. Aucun défaut bloquant n'a été vu dans les parcours testés (sauvegardes du chapitre 1) ; deux risques de blocage ne sont pas écartés (murs invisibles, mémoire sur longue session) et les chapitres suivants n'ont jamais été joués.

Lecture : **décision** = c'est à toi de trancher ; **oubli** = c'est à moi de le faire ; **bug** = défaut constaté ou probable ; **non vérifié** = codé ou lu dans le moteur, jamais vu fonctionner pour de vrai. Sources : l'audit du 02/11 (lacunes, couverture, décisions, issues GitHub) et les cinq agents de la PR #44. Les références G-xxx, D-xx, PAQ, CAR, SRV, CAS renvoient à ces fichiers d'audit.

## Audit complet du 04/11/2026 (demande de Sylfried, 14 h 52) : où on en est

Relecture de tout le jeu d'origine contre le portage (moteur, cartes, sprites, services, interface, son, Unity, combat : neuf domaines). Chaque écart net est corrigé par une issue et une PR, laissées ouvertes jusqu'à ta validation sur Windows ; ce qui touche à tes choix passe par un sondage. Les marques sont celles du reste du dossier : Établi, Supposé, Non vérifié.

**Corrigé** (issue puis PR) : ENG-02 (#198, #199), SND-02 (#200, #202), SND-03 (#201, #204), MAP-01 (#203, #205), ENG-06 (#206, #207), UI-03 (#208, #209), SPR-01 et SPR-05 (#210, #211), SPR-02 (#212, #213), ENG-07 (#214, #215), ENG-10 (#76, #216), ENG-08 (#217, #218), UI-04 (#219, #220), SND-10 et SND-12 (#221, #222), CMB-02 (#223, #224), CMB-03 (#225, #226), SND-08, SND-09 et UI-01 (#227, #228), SND-05 et SND-06 (#229, #230), CMB-04 (#231, #232).

**Laissé sans changement par discernement** (dis-le-moi si tu veux autre chose) : UI-02 (priorité du contact entre deux boutons qui se recouvrent : seul le type 8 est concerné) ; CMB-05 (textures de monstres en Clamp : rendu plus propre que l'original supposé, rendu réel de l'original non vérifié) ; Q1 (retour au titre depuis un combat : absent de l'original, fonction du portage, conservée) ; MAP-06 (décors sombres `_dk` : repli sur `_n`, rien à faire) ; SPR-07 et SPR-08 (décisions déjà prises).

**Sans objet ou réfuté** : G-034 clos (genre 18 = case vide voulue), G-072 périmé (fond lu dans FETC), G-075 réfuté (#79 close), #68 (le paquet 34 n'est jamais émis en combat), UNI-02 en partie (une touche restée enfoncée quand la fenêtre perd le focus : le `KeyStateHandler` de pyglet 2.1.19 les relâche tout seul sur `on_deactivate`, Établi par lecture de sa source ; reste le gel du jeu et la pause du son, dans le sondage).

**Décisions du sondage du 04/11/2026** (tes réponses, chacune devient une issue et une PR) :
- Perte de focus (UNI-02, SND-07) : **pause à chaque perte de focus** (jeu gelé, son en pause, reprise sans rattrapage).
- Zoom des scènes (UNI-08) : **le jeu l'emporte dans ses scènes**, avec **une transition en début de scène qui remet le zoom par défaut**, comme la réinitialisation actuelle au clavier ou à la souris.
- Ballon (MAP-02, UNI-05, SPR-06) : **reproduire l'original** (échelle ×1,00 à ×1,25 multipliée par ton zoom).
- Ciel des bords (MAP-05) : **prolonger le ciel** (`ev09`, `dpout`).
- Volumes (SND-01) : **aligner sur l'original** (lecture de `snd_vol.dat`).
- Temps de jeu (ENG-04) : **recaler sur l'heure réelle**.
- Générique de fin (UNI-01, SVC-02) : **reproduction fidèle** (textures du moteur, quads à décalage d'UV).
- Fichiers `.dqs` (ENG-05) : **liste blanche de classes** au chargement.
- « ERROR 3080 » (SVC-01) : **laissé tel quel** (comportement du jeu de base ; à voir avec le projet de traduction si c'est un souci de textes).
- Débordements du français (UI-05) : **rien à changer** tant qu'ils dépassent comme sur mobile (traités dans l'autre projet, les APK seront changés ensuite).
- Plaque « Sauvegarde automatique » grisée : **gardée** ; écriture à la fermeture : **non** (comme l'original) ; proportions d'interface (×1,12, commandes 510 / 459) : **gardées** ; `pause.py` et `ui_menu.py` : **non découpés**.
- Poker « Abandonner » (SVC-03) : **police réduite** (décidé plus tôt). Mémoire du moteur (ENG-01) : alerte à 200 Mo + sauvegarde automatique (par discernement).

**Reste à faire sans décision à prendre** : FSRA, FEAN et FEMV non rejoués (UNI-03, MAP-03, taille M à L), paquets 1, 6, 30 et 34 partiel (SVC-06), phase 23 à rejouer avec le vrai PNJ (SVC-08), préchargement de la musique de la carte suivante (SND-11), entrée de la position de la caméra (UNI-07).

## Décisions de Sylfried

Dix-huit points où je ne peux pas trancher à ta place. Pour chacun, ma recommandation : si tu ne dis rien, je la suis.

| # | Sujet | Question | Ma recommandation | Réf. |
|---|---|---|---|---|
| 1 | Toits et décors | Rendre les toits transparents quand ils cachent le héros, ou garder la silhouette supprimée ? | Garder tel quel, fermer l'issue #6 si tu ne vois pas de grêne sur mobile | G-050, D-93, #6 |
| 2 | Suivi du projet | Issues dans `dq4-portage` (aucune aujourd'hui) ou suivi par PR seulement ? | Suivi par PR : corriger `workflow.md` et le README, supprimer les 43 branches fusionnées | G-140, G-149 |
| 3 | Piste Unity | Laisser en pause ou fermer l'issue #57 ? | Laisser en pause, hors périmètre | G-146, #57 |
| 4 | Manette | La faire maintenant ? Aucun code de manette n'existe, l'issue #8 est à moitié faite | Seulement si tu joues à la manette | G-019, #8 |
| 5 | DQ5 et DQ6 | Quand étendre le portage ? | Après la validation Windows de DQ4 | G-017, #19 |
| 6 | Packaging .exe | Préparer un exécutable sans contenu Square Enix ? | Après la validation Windows | G-015, #18 |
| 7 | Shaders retirés | « Régions lissées » et « Bicubique » ont été retirés (bicubique : −27 % de netteté). On les remet ? | Laisser retirés | D-86, C-8 |
| 8 | Entrées retirées de l'éditeur | J'en ai retiré 18 alors que tu en citais une ; la liste ne t'a jamais été montrée | Je te la donne, tu dis lesquelles remettre | D-127, C-21 |
| 9 | Pixel perfect par défaut | Garder ce réglage par défaut (choisi après un retour « décor bizarre ») ? | Garder | D-85 |
| 10 | Curseur doré qui oscille | Inventé par moi, absent du jeu d'origine : garder ? | Retirer si tu ne l'as jamais vu sur mobile | G-104, D-95 |
| 11 | Clavier du nom | Disposition du portage (l'originale est introuvable) : garder ? | Garder | G-099, D-94 |
| 12 | « Revenir à l'écran titre » | Efface la sauvegarde automatique, comme le bouton d'origine : garder ce comportement ? | Garder (fidélité) | G-098, D-76 |
| 13 | Options d'origine injoignables | Volumes et taille de la croix de la fenêtre d'origine ne sont plus accessibles depuis que « Paramètres » ouvre la Pause | Rien à faire, les réglages existent côté PC | G-102, C-20 |
| 14 | Touche H au casino et au bestiaire | Inactive là-bas (pas de dialogues du terrain dans ces parties) | Laisser inactive | CAS |
| 15 | Moteur modifié en mémoire | La règle « le moteur ne se modifie pas » n'est pas exacte : le fichier est intact, mais 16 sites d'écriture existent (aucun ne touche un scénario ni une variable) | Reformuler la règle dans les docs | G-049, C-6 |
| 16 | Fenêtre « Interface » | Position gardée pour la session seulement : l'enregistrer ? | Garder ainsi | G-110, D-128 |
| 17 | Paquets 1 et 27 | Leur rôle n'est pas décodé et la carte du monde marche sans eux : les implémenter ? | Les laisser ignorés jusqu'à un défaut visible | G-040, PAQ-8, PAQ-9 |
| 18 | Licence d'Unicorn | GPL v2 ou BSD : les sources se contredisent | Vérifier avant toute redistribution | G-013, D-05 |

La fusion de « Messages en combat » et « Vitesse des combats » dans la PR #44 rend sans objet la validation du mapping Moyen / Lent et du doublon de libellé « Rapide » (D-88, C-16). Les libellés « Masqué / Masquée » (D-89) ont été validés le 03/11.

## Réponses de Sylfried (03/11/2026)

Relecture de ce rapport avec Sylfried le 03/11 (13 h 45, puis 14 h 04 et 14 h 17). Il ne pouvait pas tester : au travail. Ce qu'il a dit sert à **structurer le projet et le reste à faire**, pas à lancer un chantier tout de suite. Ses phrases sont reproduites dans `decisions.md` (§ 5c, D-149 à D-160).

| # | Sujet | Réponse | Suite |
|---|---|---|---|
| 1 | Toits et décors | **Laisser tel quel : « c'est le fonctionnement du mobile »** | **Clos** (D-93 validé, G-050 clos) ; rien à faire |
| 2 | Suivi du projet | **Issues pour le reste à faire : oui** (14 h 25) ; « `dq4-pc` n'existe plus, on fait tout depuis `dq4-portage`, même sur GitHub » | **Fait** : 38 issues #51 à #88 (voir « Suivi dans GitHub » ci-dessous). Pas d'issues rétroactives pour le travail fait (choix de Claude, D-161). Suppression des 56 branches fusionnées : en attente de son « oui » (D-162) |
| 3 | Piste Unity | Recommandation suivie : en pause, hors périmètre | L'issue #57 a disparu avec `dq4-pc` ; la décision tient |
| 4 | Manette | **« Pour la suite, on pourra prévoir d'utiliser une manette »** | **Retenue pour la suite** (pas maintenant) : à planifier ; aucun code de manette n'existe (G-019) |
| 5, 6, 7, 9, 11, 12, 13, 14, 15, 16, 17 | voir tableau ci-dessus | **Recommandation suivie** (par défaut) | 15 : règle reformulée dans les notes techniques, section « Écritures et crochets en mémoire du moteur » (**18 sites qui écrivent** et 27 crochets depuis #47 et #48, au lieu de 16 et 22 : relevé du 03/11 sur `main` b0d71b8, nombre de crochets vérifié à l'exécution) |
| 8 | Entrées retirées de l'éditeur d'interface | **« Il fallait supprimer tout ce qui n'avait pas d'élément à modifier »** (son cas de test : rien à modifier, section vide) | **Clos** : le retrait des 18 entrées (`FENETRES_RETIREES`) suit ce critère ; les fenêtres du lancement du jeu en sont exclues comme il l'avait demandé (D-127). Pas de liste à lui montrer |
| 10 | Curseur doré | **Sans objet** | Le curseur est fixe dans le code (`pause.py:161-167`) ; la petite flèche est gardée dans l'historique (#48) |
| 18 | Licence d'Unicorn | **« Ok pour la vérification »** | **À faire** (lecture seule : licence réelle du paquet `unicorn`, avant toute redistribution) |
| D-89 | Libellés « Masqué / Masquée » | Il demande ce qu'il y a à valider | Je lui ai répondu : seulement l'**accord du mot** (« Masquée » pour la croix et les fenêtres, « Masqué » pour les boutons). **Validé par Sylfried le 03/11 à 14 h 19** (« ça me va ») ; clos |

**Nouvelles exigences et décisions du 03/11 (14 h 17)** : voir aussi la section « Cap fixé » ci-dessous.

- **Tous les boutons de l'interface doivent être accessibles au clavier** (exigence générale ; « Sauvegarde rapide » de l'écran Divers n'en est qu'un cas, G-096). Inventaire complet à faire avant de corriger.
- **Bruitage au clavier : uniquement dans les mêmes situations qu'au toucher.** S'il y a un bip pour chaque caractère du nom au doigt, alors le clavier le joue aussi ; sinon on n'en ajoute pas « de force ». Remplace la formulation de l'oubli n° 8.
- **`Menu_Echap_DQ4_PC.xlsx` : n'est plus d'actualité.** Rien à régénérer (oubli n° 7 clos ; G-107 et G-143 clos).
- **Tout tenir à jour : CI, documents, fichiers `.md`.** Fait pour cette fois en #49 (docs, audit, CI) et #50 (dépôt `dq4-pc`, décisions du 03/11) ; à refaire à chaque PR.
- **Sauvegardes du chapitre 2** : il les fournira dès que possible (elles permettront de jouer au-delà du chapitre 1 ; les tests actuels n'utilisent que le chapitre 1).
- **`dq4-pc` n'existe plus** : ses 27 issues ouvertes ne peuvent plus être fermées ni lues. Les 7 à fermer (#2, #5, #7, #10, #22, #23, #41) n'ont plus rien à fermer. L'état de chacune au 02/11 reste dans `docs/audit/github_issues.md`.

**Chantiers choisis le 03/11** : « Docs + CI à jour » seulement. **Non choisis** : « petits oublis » (sauvegarde rapide au clavier, bruitage 300, icône du genre 18) et « paquets du moteur » (6, 30, effets d'écran 3 / 5 / 6).

**Points de ce rapport rendus caducs** : G-104 (curseur oscillant), G-211 / D-47 (option de caméra supprimée), G-073 pour le roulis de la caméra de combat (appliqué par `_rot_camera`), G-107 / G-143 (Excel), G-050 (toits) ; voir `lacunes_connues.md` et `decisions.md`.

## Cap fixé par Sylfried (03/11/2026) : ce qui structure la suite

Rien de ceci n'est lancé. Ordre indicatif, à confirmer par lui.

1. **Validation Windows / vrai GPU** : toujours le premier reste (rien n'est validé sous Windows).
2. **Clavier complet** : **suspendu le 03/11 à 15 h 50** (D-165) : Sylfried doute que ce soit adapté à une interface tactile ; « à creuser » (#59). La règle du bruitage (même endroit que le mobile) est confirmée (#60).
3. **Manette** : prévue « pour la suite » (aucun code aujourd'hui) ; pas de menu de choix du périphérique, une 3e colonne dans Commandes, logo selon la manette branchée (D-167, #61). La navigation des menus dépend de #59.
4. **Chapitre 2** : dès qu'il fournit les sauvegardes, rejouer les PNJ de scénario, les cartes et les menus du chapitre 2 (jamais testés).
5. ~~Vérifier la licence d'Unicorn~~ **fait le 03/11** (D-170) : à traiter comme GPL v2 ; choix à faire par Sylfried avant le `.exe` (`docs/licences.md`, #87).
6. **Paquets du moteur et petits oublis** (liste « Oublis de Claude » ci-dessous), selon ses retours de test.

## Suivi dans GitHub (depuis le 03/11/2026)

Le reste à faire de ce rapport est repris dans **75 issues de `dq4-portage` (#51 à #99, #101, #105, #107 à #112, #121 à #123, #126 à #131, #134 à #141 et #145 à #146, dont 15 fermées au 03/11)**, classées en 5 jalons ; chaque issue cite les fiches de `lacunes_connues.md` et les lignes de ce rapport. Étiquettes : `type:feature`, `type:bug`, `type:recherche`, `test-windows`, `priorité:haute`, `priorité:basse`, `bloqué` (attend Sylfried), `à décider`, `accessibility`. Ce rapport reste le constat ; **les issues sont le suivi** (à fermer par `Closes #n` dans les PR).

| Jalon | Issues | Contenu |
|---|---|---|
| 1. Validation Windows | #51 à #58, #90 | premier lancement (fermée), rendu OpenGL, performance, sauvegarde à l'église (fermée), comparaison au mobile (fermée), combats, historique (fermée), teinte jour / nuit et cartes `ml*`, séquences à fondu |
| 2. Clavier complet et manette | #59 à #61, #93 | interface au clavier et à la manette (à creuser), bruitage au clavier, manette, bruitage du coffre lâché |
| 3. Chapitre 2 et services | #62 à #65 | chapitre 2 (bloqué : sauvegardes), services, boutiques et bestiaire, casino |
| 4. Moteur et finitions | #66 à #85, #91 à #92, #94 à #95, #97 à #99, #101 | paquets 6 et 30, effets d'écran, carte du monde, icône 18, son, approximations, modèles 3D, restes `BackColor` / `cmd_chara`, 11 bugs (2 résolus : #78, #82), bouton de vitesse, caméra des attaques, historique au clavier, défilement du texte, vitesses hors combat (#101 ; #96 « accélérateur et jingle » fermée), barre de rotation de la croix, classes d'interface, petits restes |
| 5. Distribution et extensions | #86 à #88 | licence d'Unicorn (fermée : GPL v2), .exe, DQ5 et DQ6 |

## Lecture du 03/11 (14 h 36 à 15 h 50) : ce qui est validé, ce qui reste

Sylfried a lu la liste « tout ce qu'il reste à faire » et répondu point par point (décisions D-163 à D-190 dans `decisions.md` § 5d). **Phase gestion de projet : aucun correctif sur l'outil.** Ci-dessous, les 20 points « Non vérifié » avec leur résultat.

| # | Point | Résultat (Sylfried, Windows) | Suite |
|---|---|---|---|
| 1 | Rendu OpenGL | « le reste fonctionne » ; **anticrénelage et suréchantillonnage à tester** ; 2 moniteurs, fenêtre plus grande que l'écran, zoom 4K : pas testés | #52 |
| 2 | Sauvegarde à l'église | OK, ainsi que sauvegardes auto, hors églises, création et suppression de journal | #54 fermée |
| 3 | Lanceur `.bat` | « aucun souci » | #51 fermée |
| 4 | Performance x3, x4, x8 | intitulé expliqué ; pas testé | #53 |
| 5 | Comparaison avec le mobile | « nickel sur ces points » | #55 fermée |
| 6 | Historique en jeu | « fonctionnel après un ou plusieurs combats » ; le nouveau défilement n'est pas testé | #57 fermée, #94 |
| 7 | Bruitage de transition | pas testé | #75 |
| 8 | Repos des ennemis à x2 et x3 | pas testé | #56 |
| 9 | Teinte jour / nuit | OK sur la carte et dans les villes ; nom du chapitre 1 à son début OK | #58 (reste les cartes `ml*`) |
| 10 | Chapitres 2 et suivants | sauvegarde à venir | #62, `plan_tests_chapitre2.md` |
| 11 | Services | attendent le chapitre 2 | #63 |
| 12 | Boutiques 28 / 59 / 63 / 70 | attendent le chapitre 2 | #64 |
| 13 | Banque au clavier | suspendu avec l'exigence du clavier complet | #59 |
| 14 | Accès au bestiaire | attend le chapitre 2 | #64 |
| 15 | Décors de combat corrigés | aube et coucher de soleil : Sylfried les teste ; plus aucun défaut visuel la nuit | #56 |
| 16 | Boss, groupes, Morph, effets, game over | boss du chapitre 1 OK, groupes OK, Morph de la cinématique OK, game over OK ; **effets de sorts à tester** (défense) ; boss final plus tard | #56 |
| 17 | Retour au titre, nouvelle partie | nouvelle partie sans relancer OK ; **retour au titre depuis un combat ou une boutique : pas testé** | #56 |
| 18 | Paquets 16, 17, 33 des cartes `ml*` | pas précisé | #58 |
| 19 | Poker, bingo | attendent le chapitre 2 | #65 |
| 20 | Ratios autres que 16/9 | « OK » | clos |

**Oublis de Claude** : n° 6 (clavier) suspendu (#59) ; n° 8 (bruitage 300) règle confirmée (#60) ; n° 14 (CI, scripts) CI faite en #49, scripts de recherche introuvables (caduc) ; n° 15 (documentation) à jour en #49, #50 et #100. **Bugs connus** : n° 4 (`dbout`) et n° 8 (vagues d'eau) **résolus** (#78, #82 fermées) ; n° 6 (survol) **confirmé imparfait**, souris et clavier (#80) ; n° 9 (angle de caméra) : décision D-172 (#83) ; n° 1 (bruitage de transition) pas testé (#75). Les autres bugs (n° 2, 3, 5, 7, 10, 11) n'ont pas été rencontrés : à tester ou à corriger plus tard.

**Nouveaux sujets nés de la lecture** : bouton de vitesse dessiné à gauche avant sa place (#91), caméra des attaques (#92), bruitage du coffre lâché (#93), historique message par message et PgHaut / PgBas par 3 (#94), « Défilement du texte » dans Affichage (#95), accélérateur et jingle (#96, remplacée à 16 h 47 par #101), barre de rotation de la croix (#97), classes d'interface du jeu (#98), petits restes (#99).

## Lecture du 03/11 (16 h 47) : réponses à mes questions

Sylfried a répondu aux treize points que je lui avais soumis (décisions D-191 à D-200, `decisions.md` § 5e). **Toujours en phase gestion de projet : rien n'est codé.**

| Point | Réponse de Sylfried | Suite |
|---|---|---|
| « Performances à x3, x4 et x8 » | « prévois que je dois vérifier ça aussi » | #53 réécrite : combat « Très rapide » puis transitions à x4 |
| `MAP_DIFF` | « c'est bon désormais » | clos (G-039c) |
| Feuilles d'ombre 193 et 194 ; points « sans issue » | « Oki » | clos |
| Bandeau « Prologue » (`hyodai1`) | « Yes je vois le cadre » | clos (G-012) |
| Coffres | « c'est bon dans le bon sens » | clos (G-058, G-205) |
| Mode « menus simples » | garder comme solution de secours, **pas d'option**, utilisé quand nécessaire | repli automatique déjà en place ; G-108 traité |
| Format de distribution | « On verra pour les portages » : scripts + `.bat` ou `.exe` launcher | #87 ; pas tranché |
| Fichier `LICENSE` | « Fais le si il le faut » | pas nécessaire aujourd'hui, pas créé (`docs/licences.md`) |
| Accélérateur et jingle | « supprime l'option pour choisir la valeur d'accélération… x4 en vitesse de transition… » | **#101** ; #96 fermée |
| Espace et discussion de groupe | retirée d'Espace, mise sur une autre touche (Alt / Alt Gr) | clos (G-162), lecture corrigée |
| « Sort en trop » | « Exactement » : la rangée fantôme supprimée en #45 | à vérifier sur Windows (#99) |
| Caméra des attaques | « juste la caméra qui bouge pendant des attaques » ; l'Ornythox n'est plus sûr, l'archer vert est peut-être meilleur | #92 réécrite : vérifier d'abord avec des ennemis du chapitre 1 |

**Précision de 17 h 01 (D-201)** : la vitesse de marche et l'accélérateur à la touche Maj **restent** ; seul le réglage « Vitesse de transition » disparaît (#101). **Tranché à 17 h 03 (D-202)** : le sort de déplacement (306) n'est pas raccourci, Sylfried le teste lui-même ; « audio réel » et `reglages.json` (#99) : expliqués ; **réglés à 17 h 07 (D-203)** : « l'audio fonctionne », la conversion de `reglages.json` n'a pas besoin de test (bouton ↺). **Plus rien à lui demander sur ce lot.**

**À 17 h 19 (D-204) et 17 h 22 (D-205)** : Sylfried renonce à une liste globale de tout ce qu'il doit tester : il teste **issue par issue, en rentrant ce soir, en commençant par #52** (fiche de test donnée à 17 h 20). Nouvelle issue **#105** (jalon 5, `à décider`, `priorité:basse`) : décider des modificateurs et des triches qu'il voudrait ajouter, **à traiter en tout dernier** ; sa liste reste à fournir (Claude n'en propose aucune d'office).

**Retours du test de #52 (19 h 38, D-206 à D-212)** : antialiasing x2 / x4 / x8 « fonctionne » (pas de différence visible) et à renommer « Antialiasing » (fait, #113) ; suréchantillonnage x2 saccade (→ #53) ; deux moniteurs « Nickel » ; la liste des résolutions ne montre que les tailles qui tiennent sur l'écran (voulu : le test 3840 x 2160 passe par `reglages.json`). Nouvelles issues : **#107** course après une transition (corrigée dans #113, à confirmer), **#108** logo et sous-titre du titre x2, **#109** retour au titre comme l'original (dialogue Oui / Non puis transition), **#110** caméra sur la butte du village du prologue, **#111** fond dégradé du prologue, **#112** choix du périphérique de sortie audio (**retiré à 21 h 05, D-216 et D-217 : essayé sous Windows, il ne marche pas sur son matériel ; le son reste sur la sortie par défaut de Windows ; le choix du moniteur du plein écran est retiré aussi**). **À 19 h 41 (D-213)** : « tu peux directement appliquer les correctifs nécessaires » : la phase « gestion de projet » est levée pour ces corrections.

## Oublis de Claude

Quinze choses que j'ai laissées de côté ou pas finies. Les quatre premières sont des paquets du moteur que la visionneuse ne sait pas encore dessiner ; ce sont les plus visibles en jeu.

| # | Ce qui manque | Effet pour le joueur | Réf. |
|---|---|---|---|
| 1 | Poses couchées (paquets 16, 17, 18) | Les personnages endormis ou allongés restent debout | PAQ-3, G-042 |
| 2 | Animations d'événements FEAN (paquet 6) | Scènes d'histoire et bingo du casino incomplets | PAQ-5, G-041, G-052 |
| 3 | Échelle du terrain `field_scale` (paquet 30) | Problème possible avec le ballon | PAQ-6, G-040 |
| 4 | Effets d'écran 3, 5 et 6 | Flashs de certains sorts absents | PAQ-7, G-071 |
| 5 | PNJ de scénario qui apparaissent ou disparaissent | Jamais rejoués, comportement inconnu | CAR-14 |
| 6 | Boutons de l'interface inaccessibles au clavier | **Exigence du 03/11 : tous les boutons doivent être accessibles au clavier.** Cas connu : « Sauvegarde rapide » de l'écran Divers (reste à la souris) ; inventaire complet à faire | G-096, D-155 |
| 7 | ~~`Menu_Echap_DQ4_PC.xlsx`~~ | **Plus d'actualité** (Sylfried, 03/11) : rien à régénérer | G-107, G-143, D-157 |
| 8 | Bruitage 300 (clic) | **Règle du 03/11** : au clavier, un bruitage seulement là où le toucher en joue un (une note par caractère à la saisie du nom *si* le toucher en joue une), jamais ajouté de force. Entrée, Espace et M ne jouent pas le bruitage 300 que joue le clic sur le bouton : à aligner sous cette règle, cas par cas. **Fait le 04/11 (#228, audit SND-08 / SND-09 / UI-01) : A et action seuls jouent le bruitage au clic comme au clavier, Entrée / Espace / M le jouent, une lettre tapée aussi ; à valider sur Windows** | G-173, D-156 |
| 9 | Événements FEMV, bateaux animés au chargement | Absents | G-053 |
| 10 | Icône de genre 18, emplacements 10 à 12 de la carte du monde | Possibles éléments non dessinés | G-033, G-034 |
| 11 | Son : table de volumes, fondus entre musiques, bruitages 3D | Jamais étudiés | G-047 |
| 12 | Fond de combat estimé, roulis de la caméra de combat, priorité des fondus | Approximations connues | G-072, G-073, G-046 |
| 13 | Autres modèles 3D (boss, autres dragons) | Lien identifiant de modèle vers objet non résolu | G-119, G-147, #16 |
| 14 | CI minimale, scripts de recherche à ranger dans `outils/` | Pas de garde-fou automatique | G-016, G-018 |
| 15 | Documentation périmée | **Mise à jour en #49 et #50** : `workflow.md`, README, reprise, notes, audit, document du Projet sur les dépôts. À tenir à jour à chaque PR (demande du 03/11) | G-141 à G-150 |

Les cartes vides, les PNJ jamais dessinés, la teinte jour et nuit, l'échelle des sprites, le poker invisible et les pages du Statut au clavier ne figurent plus ici : ils sont traités dans la PR #44 (dernière section).

## Bugs connus

Onze défauts constatés ou probables. Les trois plus sérieux (n° 2 à 4) peuvent bloquer une partie ; aucun n'a été vu en jouant les sauvegardes du chapitre 1.

| # | Bug | Gravité | Ce qu'on sait | Réf. |
|---|---|---|---|---|
| 1 | Bruitage de transition perdu (porte, sortie de village) à accélérateur élevé | Moyenne | Atténué (un bruitage tout juste lancé reste 0,4 s), cause ni reproduite ni trouvée | #44 |
| 2 | `startTown` plante pour les cartes `za3f3` et `ev01` | Moyenne | **Clos le 04/11/2026 (#76, #216)** : `za3f3` est une carte orpheline (aucun `.stg` dans l'APK) et `ev01` ne plante que lancée par `startTown` (le titre la charge par un autre chemin) ; `demarrer_ville` refuse maintenant un nom sans `.stg` | CAR |
| 3 | Allocateur de 256 Mo jamais libéré | Haute (latent) | Arrêt `MemoryError` possible sur longue session, aucune mesure | G-044, #11 |
| 4 | Murs invisibles et escalier de `dbout` | Haute (latent) | Risque de blocage ; l'enquête du 31/10 n'a rien prouvé | G-055 |
| 5 | Monstre endormi ou paralysé qui pourrait s'effacer | Moyenne | Hypothèse lue dans le code, non reproduite | G-075 |
| 6 | Survol à la souris : mauvais bouton allumé | Basse | Jamais reproduit ; trois durcissements ajoutés ; la souris inutilisable 1 s après le clavier est corrigée (#43) | G-105 |
| 7 | « ERROR 3080@ » dans des dialogues de PNJ du casino | Inconnue | Supposé : banque de textes d'un autre chapitre ; je ne touche pas aux fichiers du patch FR | CAS-14 |
| 8 | Vagues d'eau qui débordent sur le sol des grottes | Basse | Non reproduit | G-054 |
| 9 | Angle de caméra (flèches haut et bas) sauvegardé | Basse | Un appui accidentel décale le tangage durablement | G-063 |
| 10 | Zoom de la minicarte à 400 % | Basse | Garde-fou ajouté, cause non reproduite | G-039b |
| 11 | Blocage de 0,1 à 0,5 s au chargement d'une carte | Basse | Environ 55 textures envoyées d'un coup | G-126 |

## Anciennes issues (dépôt `dq4-pc`, supprimé)

Le dépôt `dq4-pc` n'existe plus (Sylfried, 03/11/2026) : ses 27 issues ouvertes ne peuvent plus être consultées ni fermées. Leur contenu et leur état réel au 02/11 sont conservés dans `docs/audit/github_issues.md` ; les restes qui comptent sont repris dans ce rapport. `dq4-portage` n'a aucune issue ; son suivi se fait par PR (« Avance #N »).

| Verdict au 02/11 | Issues | Suite |
|---|---|---|
| Faites (7) | #2 (sauf les classes `IBase`), #5, #7 (sauf les coffres, traités en #43), #10, #22, #23, #41 | Plus rien à fermer ; les restes (`IBase`) sont dans « Oublis » |
| Faites côté code, confirmation manquante (2) | #40 (« à reconfirmer sur pdc »), #17 (son : vérifier les haut-parleurs) | À confirmer avec le test Windows |
| Reste réel (16) | #3, #4, #8 (manette : voir « Cap fixé »), #9 (**priorité haute** : sauvegarde réelle sous Windows), #11 (allocateur), #12 (Python 3.15), #13 (paquets 1, 6, 16, 17, 18, 27, 30, 33), #15, #16, #18, #19, #20, #21, #24, #45, #56 | Suivis dans ce rapport (oublis, bugs, non vérifié) |
| Décidées (2) | #6 (toits : on garde, c'est le fonctionnement du mobile), #57 (piste Unity : en pause) | Décisions 1 et 3 |

## Non vérifié

Vingt points codés, lus dans le moteur ou testés avec des valeurs forcées, mais jamais vus fonctionner pour de vrai. Tout ce qui est marqué « vu » ailleurs dans ce rapport l'a été sous Linux (Mesa, sans fenêtre réelle sur ton PC).

| # | Élément | Ce qui manque | Comment le vérifier |
|---|---|---|---|
| 1 | Rendu OpenGL sous Windows, vrai GPU | Antialiasing x4, suréchantillonnage, 4K, plein écran : tout vient de Mesa (G-001, G-003, G-004) | Lancer sur ton PC |
| 2 | Sauvegarde à l'église puis rechargement sous Windows | Issue #9, priorité haute (G-120) | Sauvegarder, quitter, relancer, charger |
| 3 | Lanceur `.bat` | Cache, Python, boîtes de dialogue d'import et d'export (G-002, G-010, G-014) | Premier lancement propre |
| 4 | Performance à x3, x4, x8 | Budget de 30 ms par image, fondus (G-008) | Jouer à grande vitesse |
| 5 | Comparaison avec le mobile | Tailles de texte, placements au pixel, croix, plume : aucune capture mobile (G-023) | Captures côte à côte |
| 6 | Fenêtre d'historique en jeu | Dessin et touche H vus sous Linux seulement ; un combat réel jusqu'à l'historique en fenêtre | Gagner un combat, ouvrir H deux fois |
| 7 | Cause du bruitage de transition perdu | Le héros restait bloqué sur la sauvegarde 4 | Une porte accessible, accélérateur haut |
| 8 | Animation de repos des ennemis à x2 et x3 | Comptée par pas de moteur, jamais regardée | La regarder en combat |
| 9 | Teinte réelle jour et nuit de la carte du monde | Testée avec des valeurs forcées ; nuit en combat jamais comparée à un téléphone | Carte du monde à différentes heures |
| 10 | Chapitres 2 et suivants | Toutes les sauvegardes réelles sont au chapitre 1 : colisée, arène jusqu'au bout, générique, titres de chapitre | Une sauvegarde plus avancée |
| 11 | Services à jouer pour de vrai | Auberge par le PNJ, sorts du menu, divination, bénédiction, purification, radeau, henge, sifflet, Rura | Sauvegarde avec lanceur de sorts, puis parcours |
| 12 | Boutiques types 28, 59, 63, 70 | Boutique de Torneko, surechigai (G-164) | Les trouver en jeu |
| 13 | Banque au clavier | Colonne exacte choisie par ◀ ▶ : le scénario ne couvre qu'un chiffre | Saisir 3 150 G au clavier |
| 14 | Accès au bestiaire | Aucun bouton trouvé dans le menu du chapitre 1 ; ouvert par appel direct | Voir si un objet ou un chapitre le débloque |
| 15 | Décors de combat corrigés | 18 nouveaux, 4 vus en vue approximative ; 7 planches de contrôle sur 15 jamais regardées | Les regarder |
| 16 | Boss, groupes, Morph, effets de sorts, game over | G-070, G-071, G-078, G-080 (victoire et montée de niveau, eux, vus en vrai combat) | Combats variés |
| 17 | Retour au titre depuis un combat ou une boutique, nouvelle partie sans relancer | G-079 | Le faire |
| 18 | Paquets 16, 17, 33 des cartes `ml*` | Comptés, jamais vus ; sous-titre des chapitres (G-043) | Cartes `ml*` |
| 19 | Poker : libellé « Abandonner » et animation du bingo | Chevauchement possible ; animation (paquet 6) non rejouée | Casino de Chandor |
| 20 | Ratios autres que 16/9 | 16:10, 21:9, 4:3 : « pas de vide autour des cartes » non vérifié (G-020) | Redimensionner la fenêtre |

La liste des types de menu sans test réel (couverture, §2) date du début de l'audit : plusieurs ont été vus depuis (Statut, boutiques, église, banque, casino, arène). Elle est à rejouer avant d'être citée.

## Livré dans la PR #44

Branche `audit2-histo`, pas encore ouverte en PR. Après fusion des cinq agents d'audit, 19 fichiers de tests passent, plus le test moteur de la vitesse de combat.

- **Historique** : trois onglets (Dialogues hors combat, Combats avec ennemis, or et expérience, Favoris), nom du locuteur seulement s'il était affiché, fond translucide, touche H en cycle (messages, combats, fermer). Dialogues et combats disparaissent à la fermeture, les favoris restent jusqu'à suppression.

- **Combat** : réglage unique « Vitesse de combat » (Manuel, Normal, Rapide, Très rapide) avec bouton à flèches à côté de « Fuir » ; la vitesse des ennemis suit. Combats de nuit : cause trouvée (couleur de l'asset jamais utilisée par le jeu), décor corrigé.

- **Réglages** : boutons ↺ de retour à la valeur par défaut sur chaque ligne à valeurs ; option, désactivée par défaut, pour regagner tous les PV et PM à chaque niveau (vérifiée sur un vrai combat gagné).

- **Carte du monde** : cycle jour et nuit (teinte des décors) et échelle des sprites.

- **Audit** : 32 cartes qui sortaient vides corrigées, 3 PNJ jamais dessinés, états enregistrés qui oubliaient les correctifs, pages du Statut au clavier, saisie des montants au clavier (banque, jetons, mises), poker enfin visible et jouable, arrêt de la victoire dans l'arène et touche de vitesse qui n'agissait pas en arène.

- **Docs** : README et notes mises à jour (sections « Avance #44 »).
