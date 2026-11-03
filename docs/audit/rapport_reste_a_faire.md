> **Copie du Claude Doc « DQ4 PC — Ce qu'il reste après l'audit »** (lien : https://claude.ai/artifact/5q6Cs8Br27SGqahx1AkvD4), exportée le 02/11/2026 au soir. Le rapport date de l'état **#44**. Depuis, l'avance **#45** (PR fusionnée, `main` 71fcd53) a traité : les **poses couchées** (oubli n° 1, paquets 16 / 17 / 18, shader `CharaSleep`), la cause de l'effet de rideau au lancement et des micro-images au changement de carte, le décor de combat selon l'heure (le soir existe, l'aube non), l'effet de coup critique, les rencontres aléatoires à marche accélérée, le menu Magie. Puis **#46** (docs et audit versés au dépôt), **#47** (retours de 22 h 29 : pause, caméra toujours centrée, titre, combat, historique, sorts, bruitages) et **#48** (retours de 07 h 33 du 03/11 : sorts sans effet, transition x1, historique au clavier). Le reste de la liste est **inchangé** et doit être reconfirmé avant d'être cité ; les réponses de Sylfried du 03/11 sont dans la section « Réponses de Sylfried (03/11/2026) » ci-dessous. Les points nouveaux de #45 sont dans `docs/notes-visionneuse-dq4-pc.md` (« Avance #45 », sous-sections « À trancher par Sylfried » et « Non vérifié (#45) »).

# DQ4 PC — Ce qu'il reste après l'audit

2026-11-02 · @Sylfried

## En bref

Le portage fonctionne sur tout ce que j'ai pu essayer sous Linux, mais **rien n'a été validé sous Windows ni sur un vrai GPU** : c'est le premier reste. Ce rapport compte **18 points qui attendent ta décision**, **15 oublis** de ma part, **11 bugs** connus ou probables et **20 points non vérifiés**. Aucun défaut bloquant n'a été vu dans les parcours testés (sauvegardes du chapitre 1) ; deux risques de blocage ne sont pas écartés (murs invisibles, mémoire sur longue session) et les chapitres suivants n'ont jamais été joués.

Lecture : **décision** = c'est à toi de trancher ; **oubli** = c'est à moi de le faire ; **bug** = défaut constaté ou probable ; **non vérifié** = codé ou lu dans le moteur, jamais vu fonctionner pour de vrai. Sources : l'audit du 02/11 (lacunes, couverture, décisions, issues GitHub) et les cinq agents de la PR #44. Les références G-xxx, D-xx, PAQ, CAR, SRV, CAS renvoient à ces fichiers d'audit.

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

La fusion de « Messages en combat » et « Vitesse des combats » dans la PR #44 rend sans objet la validation du mapping Moyen / Lent et du doublon de libellé « Rapide » (D-88, C-16). Les libellés « Masqué / Masquée » (D-89) restent à valider.

## Réponses de Sylfried (03/11/2026)

Relecture de ce rapport avec Sylfried le 03/11 à 13 h 45 (il ne pouvait pas tester : au travail). Il a répondu à trois questions ; pour le reste il a laissé la règle « si tu ne dis rien, je suis ma recommandation ».

| # | Sujet | Réponse | Suite |
|---|---|---|---|
| 1 | Toits et décors | **Garder tel quel** | L'issue dq4-pc #6 (toits transparents) **reste ouverte** : sa fermeture était conditionnée à une vérification sur mobile qu'il n'a pas faite |
| 2, 3, 4, 5, 6, 7, 9, 11, 12, 13, 14, 15, 16, 17 | voir tableau ci-dessus | **Recommandation suivie** (par défaut) | 2 : `workflow.md` et README corrigés (branche `docs-audit48`) ; la suppression des branches fusionnées n'est **pas faite** (à confirmer) ; 15 : règle reformulée dans les notes techniques, section « Écritures et crochets en mémoire du moteur » |
| 10 | Curseur doré | **Sans objet** | Le curseur est fixe dans le code (`pause.py:161-167`) ; la petite flèche est gardée dans l'historique (#48) |
| 8, 18 | Entrées retirées de l'éditeur ; licence d'Unicorn | **Sans réponse** | 8 : liste des 18 entrées (`FENETRES_RETIREES`) à lui montrer ; 18 : à vérifier avant toute redistribution |
| D-89 | Libellés « Masqué / Masquée » | **Sans réponse** | à valider |

**Issues de l'ancien dépôt `dq4-pc`** : Sylfried a demandé de fermer les **7** issues **#2, #5, #7, #10, #22, #23, #41** (avec un commentaire qui renvoie à la PR qui les résout). **Non fait** : la session n'a pas accès à `Sylfried/dq4-pc` (le dépôt n'est pas dans les dépôts autorisés de la session, l'API répond 403) ; il faut donner l'accès à l'application GitHub ou fermer ces issues à la main. #6 reste ouverte.

**Chantiers choisis** : « Docs + CI à jour » seulement (cette branche : rebase des docs, fichiers d'audit périmés mis à jour, test de la CI sur GitHub). **Non choisis** : les « petits oublis » (sauvegarde rapide au clavier, bruitage 300 par Entrée / Espace / M, icône du genre 18, fichier Excel) et les « paquets du moteur » (6, 30, effets d'écran 3 / 5 / 6).

**Points de ce rapport rendus caducs** : G-104 (curseur oscillant), G-211 / D-47 (option de caméra supprimée), G-073 pour le roulis de la caméra de combat (appliqué par `_rot_camera`) ; voir `lacunes_connues.md` et `decisions.md`.

## Oublis de Claude

Quinze choses que j'ai laissées de côté ou pas finies. Les quatre premières sont des paquets du moteur que la visionneuse ne sait pas encore dessiner ; ce sont les plus visibles en jeu.

| # | Ce qui manque | Effet pour le joueur | Réf. |
|---|---|---|---|
| 1 | Poses couchées (paquets 16, 17, 18) | Les personnages endormis ou allongés restent debout | PAQ-3, G-042 |
| 2 | Animations d'événements FEAN (paquet 6) | Scènes d'histoire et bingo du casino incomplets | PAQ-5, G-041, G-052 |
| 3 | Échelle du terrain `field_scale` (paquet 30) | Problème possible avec le ballon | PAQ-6, G-040 |
| 4 | Effets d'écran 3, 5 et 6 | Flashs de certains sorts absents | PAQ-7, G-071 |
| 5 | PNJ de scénario qui apparaissent ou disparaissent | Jamais rejoués, comportement inconnu | CAR-14 |
| 6 | « Sauvegarde rapide » de l'écran Divers | Reste à la souris, le clavier ne l'atteint pas | G-096 |
| 7 | `Menu_Echap_DQ4_PC.xlsx` | Ta spécification n'a pas été régénérée après les réorganisations | G-107 |
| 8 | Bruitage 300 (clic) | Entrée, Espace et M ne le jouent pas, le clic à l'écran oui | G-173 |
| 9 | Événements FEMV, bateaux animés au chargement | Absents | G-053 |
| 10 | Icône de genre 18, emplacements 10 à 12 de la carte du monde | Possibles éléments non dessinés | G-033, G-034 |
| 11 | Son : table de volumes, fondus entre musiques, bruitages 3D | Jamais étudiés | G-047 |
| 12 | Fond de combat estimé, roulis de la caméra de combat, priorité des fondus | Approximations connues | G-072, G-073, G-046 |
| 13 | Autres modèles 3D (boss, autres dragons) | Lien identifiant de modèle vers objet non résolu | G-119, G-147, #16 |
| 14 | CI minimale, scripts de recherche à ranger dans `outils/` | Pas de garde-fou automatique | G-016, G-018 |
| 15 | Documentation périmée | `workflow.md`, README (PR #1 à #78), `historique.md`, `depot-github-dq4-pc.md` du Projet, listes « prochaines étapes » des notes, « issue #55 » qui n'existe pas | G-141 à G-150 |

Les cartes vides, les PNJ jamais dessinés, la teinte jour et nuit, l'échelle des sprites, le poker invisible et les pages du Statut au clavier ne figurent plus ici : ils sont traités dans la PR #44 (dernière section).

## Bugs connus

Onze défauts constatés ou probables. Les trois plus sérieux (n° 2 à 4) peuvent bloquer une partie ; aucun n'a été vu en jouant les sauvegardes du chapitre 1.

| # | Bug | Gravité | Ce qu'on sait | Réf. |
|---|---|---|---|---|
| 1 | Bruitage de transition perdu (porte, sortie de village) à accélérateur élevé | Moyenne | Atténué (un bruitage tout juste lancé reste 0,4 s), cause ni reproduite ni trouvée | #44 |
| 2 | `startTown` plante pour les cartes `za3f3` et `ev01` | Moyenne | Pointeur nul dans `FldStage::getCameraLimitL`, données correctes | CAR |
| 3 | Allocateur de 256 Mo jamais libéré | Haute (latent) | Arrêt `MemoryError` possible sur longue session, aucune mesure | G-044, #11 |
| 4 | Murs invisibles et escalier de `dbout` | Haute (latent) | Risque de blocage ; l'enquête du 31/10 n'a rien prouvé | G-055 |
| 5 | Monstre endormi ou paralysé qui pourrait s'effacer | Moyenne | Hypothèse lue dans le code, non reproduite | G-075 |
| 6 | Survol à la souris : mauvais bouton allumé | Basse | Jamais reproduit ; trois durcissements ajoutés ; la souris inutilisable 1 s après le clavier est corrigée (#43) | G-105 |
| 7 | « ERROR 3080@ » dans des dialogues de PNJ du casino | Inconnue | Supposé : banque de textes d'un autre chapitre ; je ne touche pas aux fichiers du patch FR | CAS-14 |
| 8 | Vagues d'eau qui débordent sur le sol des grottes | Basse | Non reproduit | G-054 |
| 9 | Angle de caméra (flèches haut et bas) sauvegardé | Basse | Un appui accidentel décale le tangage durablement | G-063 |
| 10 | Zoom de la minicarte à 400 % | Basse | Garde-fou ajouté, cause non reproduite | G-039b |
| 11 | Blocage de 0,1 à 0,5 s au chargement d'une carte | Basse | Environ 55 textures envoyées d'un coup | G-126 |

## Issues GitHub

Sur les 27 issues ouvertes de `dq4-pc`, 7 sont faites et peuvent être fermées, 2 attendent ta confirmation, 16 ont un reste réel et 2 dépendent d'une décision. Je n'en ai fermé, ouvert ou commenté aucune. `dq4-portage` n'a aucune issue ; son suivi se fait par PR (42 à l'audit).

| Verdict | Issues | Raison |
|---|---|---|
| Fermer, c'est fait (7) | #2 (sauf les classes `IBase`), #5, #7 (sauf les coffres, traités en #43), #10, #22, #23, #41 | Preuves dans l'audit ; #22 et #41 sont obsolètes |
| Fermer après ta confirmation (2) | #40 (« à reconfirmer sur pdc »), #17 (son : vérifier les haut-parleurs) | Code fait, confirmation manquante |
| Garder ouvertes (16) | #3, #4, #8 (manette), #9 (**priorité haute** : sauvegarde réelle sous Windows), #11 (allocateur), #12 (Python 3.15), #13 (paquets 1, 6, 16, 17, 18, 27, 30, 33), #15, #16, #18, #19, #20, #21, #24, #45, #56 | Reste réel, voir bugs et oublis |
| À décider (2) | #6 (toits), #57 (piste Unity) | Décisions 1 et 3 plus haut |

Si tu me dis « ferme les 7 », je le fais avec un commentaire renvoyant à la PR qui les résout. La #13 est en partie traitée depuis la PR #44 (paquet 33 : teinte des décors) ; il resterait les paquets 1, 6, 16, 17, 18, 27 et 30.

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
