> **Copie du Claude Doc « DQ4 PC — Ce qu'il reste après l'audit »** (lien : https://claude.ai/artifact/5q6Cs8Br27SGqahx1AkvD4), exportée le 02/11/2026 au soir. Le rapport date de l'état **#44**. Depuis, l'avance **#45** (PR fusionnée, `main` 71fcd53) a traité : les **poses couchées** (oubli n° 1, paquets 16 / 17 / 18, shader `CharaSleep`), la cause de l'effet de rideau au lancement et des micro-images au changement de carte, le décor de combat selon l'heure (le soir existe, l'aube non), l'effet de coup critique, les rencontres aléatoires à marche accélérée, le menu Magie. Puis **#46** (docs et audit versés au dépôt), **#47** (retours de 22 h 29 : pause, caméra toujours centrée, titre, combat, historique, sorts, bruitages) et **#48** (retours de 07 h 33 du 03/11 : sorts sans effet, transition x1, historique au clavier). Le reste de la liste est **inchangé** et doit être reconfirmé avant d'être cité ; les réponses de Sylfried du 03/11 sont dans la section « Réponses de Sylfried (03/11/2026) » ci-dessous. Les points nouveaux de #45 sont dans `docs/viewer-notes-dq4-pc.md` (« Avance #45 », sous-sections « À trancher par Sylfried » et « Non vérifié (#45) »).

# DQ4 PC — Ce qu'il reste après l'audit

2026-11-02 · @Sylfried

## En bref

> **Mise à jour du 03/11/2026 à 15 h 50 (lecture de Sylfried)** : voir la section « Lecture du 03/11 » plus bas. Les compteurs ci-dessous (18 / 15 / 11 / 20) datent du 02/11 ; l'état à jour est dans les issues GitHub (#51 à #99 et #101) et dans `known_gaps.md` (réponses de 16 h 47 : section « Lecture du 03/11 (16 h 47) »).

Le portage fonctionne sur tout ce que j'ai pu essayer sous Linux, mais **rien n'a été validé sous Windows ni sur un vrai GPU** : c'est le premier reste. Ce rapport compte **18 points qui attendent ta décision**, **15 oublis** de ma part, **11 bugs** connus ou probables et **20 points non vérifiés**. Aucun défaut bloquant n'a été vu dans les parcours testés (sauvegardes du chapitre 1) ; deux risques de blocage ne sont pas écartés (murs invisibles, mémoire sur longue session) et les chapitres suivants n'ont jamais été joués.

Lecture : **décision** = c'est à toi de trancher ; **oubli** = c'est à moi de le faire ; **bug** = défaut constaté ou probable ; **non vérifié** = codé ou lu dans le moteur, jamais vu fonctionner pour de vrai. Sources : l'audit du 02/11 (lacunes, couverture, décisions, issues GitHub) et les cinq agents de la PR #44. Les références G-xxx, D-xx, PAQ, CAR, SRV, CAS renvoient à ces fichiers d'audit.

## Audit complet du 04/11/2026 (demande de Sylfried, 14 h 52) : où on en est

Relecture de tout le jeu d'origine contre le portage (moteur, cartes, sprites, services, interface, son, Unity, combat : neuf domaines). Chaque écart net est corrigé par une issue et une PR, laissées ouvertes jusqu'à ta validation sur Windows ; ce qui touche à tes choix passe par un sondage. Les marques sont celles du reste du dossier : Établi, Supposé, Non vérifié.

**Corrigé** (issue puis PR) : ENG-02 (#198, #199), SND-02 (#200, #202), SND-03 (#201, #204), MAP-01 (#203, #205), ENG-06 (#206, #207), UI-03 (#208, #209), SPR-01 et SPR-05 (#210, #211), SPR-02 (#212, #213), ENG-07 (#214, #215), ENG-10 (#76, #216), ENG-08 (#217, #218), UI-04 (#219, #220), SND-10 et SND-12 (#221, #222), CMB-02 (#223, #224), CMB-03 (#225, #226), SND-08, SND-09 et UI-01 (#227, #228), SND-05 et SND-06 (#229, #230), CMB-04 (#231, #232) ; puis, après le sondage : pause à chaque perte de focus (#235, #236), volumes des sons (#237, #238), temps de jeu (#239, #240), liste blanche `.dqs` (#241, #242), zoom des scènes (#243, #244), alerte de la mémoire du moteur (#245, #247), poker « Abandonner » (#246, #248), ciel prolongé de `dpout` et `ev09` (#249, #250), ballon et paquet 30 (#251, #252), sépia des retours en arrière (#253, #254), effets d'écran du voyage, de la lampe et de Riremito (UNI-06, #255, #256), puis le blocage du don d'expérience du roi au chapitre 1 (G-217, #261, #262 : le moteur attendait un toucher d'écran 0x100, la touche A envoyait 0x10).

**Laissé sans changement par discernement** (dis-le-moi si tu veux autre chose) : UI-02 (priorité du contact entre deux boutons qui se recouvrent : seul le type 8 est concerné) ; CMB-05 (textures de monstres en Clamp : rendu plus propre que l'original supposé, rendu réel de l'original non vérifié) ; Q1 (retour au titre depuis un combat : absent de l'original, fonction du portage, conservée) ; MAP-06 (décors sombres `_dk` : repli sur `_n`, rien à faire) ; SPR-07 et SPR-08 (décisions déjà prises).

**Sans objet ou réfuté** : G-034 clos (genre 18 = case vide voulue), G-072 périmé (fond lu dans FETC), G-075 réfuté (#79 close), #68 (le paquet 34 n'est jamais émis en combat), UNI-02 en partie (une touche restée enfoncée quand la fenêtre perd le focus : le `KeyStateHandler` de pyglet 2.1.19 les relâche tout seul sur `on_deactivate`, Établi par lecture de sa source ; reste le gel du jeu et la pause du son, dans le sondage).

**Décisions du sondage du 04/11/2026** (tes réponses, chacune devient une issue et une PR) :
- Perte de focus (UNI-02, SND-07) : **pause à chaque perte de focus** (jeu gelé, son en pause, reprise sans rattrapage).
- Zoom des scènes (UNI-08) : **le jeu l'emporte dans ses scènes**, avec **une transition en début de scène qui remet le zoom par défaut**, comme la réinitialisation actuelle au clavier ou à la souris. **Devenu sans objet pour le zoom le 04/11/2026 (D-226, #264)** : plus de zoom ni d'inclinaison du joueur, la caméra est celle du jeu. **La rotation gauche / droite du joueur est revenue le 05/11/2026 (D-233, #278)** : le jeu l'emporte toujours dans ses scènes, la rotation s'efface alors en douceur.
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

**Reste à faire sans décision à prendre** : accélération des gains du casino par un appui (machine à sous, poker, arène : le moteur la lit sur le même déclenchement que le don d'expérience ; non vérifié en jeu, G-217), FSRA, FEAN et FEMV non rejoués (UNI-03, MAP-03, taille M à L), paquet 6 (SVC-06 ; les paquets 1, 30 et 34, valeurs 3 / 5 / 6, sont traités, #254, #252 et #256 ; durée réelle de l'effet de début de combat, valeur 4, à revérifier), phase 23 à rejouer avec le vrai PNJ (SVC-08), préchargement de la musique de la carte suivante (SND-11), entrée de la position de la caméra (UNI-07).

## Audit complet du 05/11/2026 : où on en est

Relecture de tout le jeu d'origine contre le portage par huit relecteurs en lecture seule (D-240) : **rapport complet dans `docs/audit/audit_2026-11-05.md`**. Rien n'a été modifié dans le code.

- **Ce qui manque** : générique de fin (#297, le plus gros), animations d'événements FEAN (#66), couleurs de matériaux animées FSRA (#298), modèles 3D d'effets de combat (#304), manette (#61), chapitres 2 à 9 et véhicules jamais joués pour de vrai (#62 à #65, #69), entrée « Bestiaire » du menu Divers (#64), trois décisions de toi pas encore exécutées (#94, #95, #97), DQ5 / DQ6 (#88). Les FEMV sont sans objet (code mort dans Unity).
- **Ce qui bug** : le ciel d'`ev09` se décale (#249, priorité haute) ; un moteur arrêté ferme la fenêtre sans trace (#292) ; allocateur de 256 Mo jamais libéré (#77) ; combat sur une carte sans décor (#306) ; texte natif « copy of Ragnar » (#305) ; textes de l'outil (#300) ; son (#308) ; lanceur et migration des dossiers (#293) ; dépendances et CI (#294) ; états `.dqs` (#295) ; cache de cartes (#301) ; documents et commentaires périmés (#296). « ERROR 3080 » n'est pas un défaut du patch FR (#81).
- **Aucune régression de comportement** trouvée dans les PR #196 à #291 (caméra, Paramètres, notifications, historique, version anglaise, renommage, sauvegardes), sauf le ciel d'`ev09` et des commentaires et documents périmés.
- **Issues** : 11 fermées, 17 créées, 112 + 17 = 129 ouvertes après l'audit ; celles pour lesquelles un test Windows est demandé restent ouvertes.
- **Questions à trancher** : #299, #303, #302, #307 et #93.

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

**Points de ce rapport rendus caducs** : G-104 (curseur oscillant), G-211 / D-47 (option de caméra supprimée), G-073 pour le roulis de la caméra de combat (appliqué par `_rot_camera`), G-107 / G-143 (Excel), G-050 (toits) ; voir `known_gaps.md` et `decisions.md`.

## Cap fixé par Sylfried (03/11/2026) : ce qui structure la suite

Rien de ceci n'est lancé. Ordre indicatif, à confirmer par lui.

1. **Validation Windows / vrai GPU** : toujours le premier reste (rien n'est validé sous Windows).
2. **Clavier complet** : **suspendu le 03/11 à 15 h 50** (D-165) : Sylfried doute que ce soit adapté à une interface tactile ; « à creuser » (#59). La règle du bruitage (même endroit que le mobile) est confirmée (#60).
3. **Manette** : prévue « pour la suite » (aucun code aujourd'hui) ; pas de menu de choix du périphérique, une 3e colonne dans Commandes, logo selon la manette branchée (D-167, #61). La navigation des menus dépend de #59.
4. **Chapitre 2** : dès qu'il fournit les sauvegardes, rejouer les PNJ de scénario, les cartes et les menus du chapitre 2 (jamais testés).
5. ~~Vérifier la licence d'Unicorn~~ **fait le 03/11** (D-170) : à traiter comme GPL v2 ; choix à faire par Sylfried avant le `.exe` (`docs/licenses.md`, #87).
6. **Paquets du moteur et petits oublis** (liste « Oublis de Claude » ci-dessous), selon ses retours de test.
