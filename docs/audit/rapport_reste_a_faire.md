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

La fusion de « Messages en combat » et « Vitesse des combats » dans la PR #44 rend sans objet la validation du mapping Moyen / Lent et du doublon de libellé « Rapide » (D-88, C-16). Les libellés « Masqué / Masquée » (D-89) ont été validés le 03/11.

## Réponses de Sylfried (03/11/2026)

Relecture de ce rapport avec Sylfried le 03/11 (13 h 45, puis 14 h 04 et 14 h 17). Il ne pouvait pas tester : au travail. Ce qu'il a dit sert à **structurer le projet et le reste à faire**, pas à lancer un chantier tout de suite. Ses phrases sont reproduites dans `decisions.md` (§ 5c, D-149 à D-160).

| # | Sujet | Réponse | Suite |
|---|---|---|---|
| 1 | Toits et décors | **Laisser tel quel : « c'est le fonctionnement du mobile »** | **Clos** (D-93 validé, G-050 clos) ; rien à faire |
| 2 | Suivi du projet | Recommandation suivie (suivi par PR). **Nouveau** : « `dq4-pc` n'existe plus, on fait tout depuis `dq4-portage`, même sur GitHub » | Docs corrigées (#49, #50). **Question ouverte** : veut-il aussi des issues dans `dq4-portage` pour le reste à faire ? (jusqu'ici : aucune) |
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
2. **Clavier complet** : tous les boutons de l'interface atteignables au clavier (inventaire, puis correction), avec la règle du bruitage ci-dessus.
3. **Manette** : prévue « pour la suite » (aucun code aujourd'hui). À faire après le clavier complet : la navigation au clavier sert de base.
4. **Chapitre 2** : dès qu'il fournit les sauvegardes, rejouer les PNJ de scénario, les cartes et les menus du chapitre 2 (jamais testés).
5. **Vérifier la licence d'Unicorn** avant toute redistribution ou `.exe`.
6. **Paquets du moteur et petits oublis** (liste « Oublis de Claude » ci-dessous), selon ses retours de test.

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
| 8 | Bruitage 300 (clic) | **Règle du 03/11** : au clavier, un bruitage seulement là où le toucher en joue un (une note par caractère à la saisie du nom *si* le toucher en joue une), jamais ajouté de force. Entrée, Espace et M ne jouent pas le bruitage 300 que joue le clic sur le bouton : à aligner sous cette règle, cas par cas | G-173, D-156 |
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
