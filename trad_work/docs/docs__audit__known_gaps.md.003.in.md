## I. Lacunes que le prédécesseur n'avait pas reprises

| ID | Description | Source | Statut | Classement | Lien |
|---|---|---|---|---|---|
| G-160 | `Global::NativeExec` : `arg2 = 0x2000 → bit 0x400` « non étudié » (entrée du moteur non connue) | NV:16 | ouvert | [à vérifier] | |
| G-161 | Maj = courir : interprétation de « Maj : toujours courir » à confirmer (touche maintenue) **03/11** : « tout est OK ». | NV:213-214 | **clos (03/11)** | [à vérifier] | D-58 |
| G-162 | Espace = action puis discussion de groupe si rien déclenché au bout de 3 pas : un cas où une action existe sans poser le bit 0x4 ouvrirait la discussion en plus **03/11** : « Espace ne fait plus les discussions de groupe » lu comme « le cas limite n'arrive plus ». **03/11 16 h 47** : corrigé : la discussion de groupe n'est plus sur Espace mais sur Alt / Alt Gr (D-198, D-60). | NV:217 | **clos (03/11, 16 h 47)** | [à vérifier] | D-58 |
| G-163 | Rendu d'une ville entière à 40 % : fond uni possible aux bords (le zoom 40-400 % a été remplacé par « Distance caméra » 50-200 %) | NV:218 | probablement obsolète | [à vérifier] | |
| G-164 | Boutiques : types 28 et 63 non vérifiés | NV:408 | ouvert | [à vérifier] | D-134 |
| G-165 | Dialogues du terrain : **jamais automatiques** (400 images d'attente mesurées) ; seul le défilement des combats existe. Sylfried parle d'un script de DQ5 (Nimzo) qui change la valeur : cas non rencontré en DQ4 **03/11** : sujet DQ5 : #88. | NV:390 ; message 02:12 | **clos (03/11, D-186)** pour DQ4 | [à vérifier] | D-14, D-124 |
| G-166 | Pause et aperçu de l'éditeur gardent `ui_font.otf` (la police du jeu SE-GARRIR n'y est pas utilisée) | NV:407 | ouvert | [décision] de Claude | |
| G-167 | Vitesse du texte = crochet de la visionneuse (le jeu d'origine n'a pas cette option) | NV:390 ; `engine.py:382-407` | ouvert (volontaire) | [décision] | D-78, D-124 |
| G-168 | Ombre des personnages sur la carte du monde non comparée au mobile ; ombre masquée pour les feuilles 193 / 194 **03/11** : « les ombres sont OK » ; feuille 193 = bateaux (le moteur masque leur ombre), la feuille 194 n'existe pas dans les textures. | NV:157, NV:167 ; PR #19, #21 | **clos (03/11)** | [à vérifier] |  |
| G-169 | Menu Échap : ressemblance du style à la capture mobile « non mesurée » (couleurs choisies à l'œil) **03/11** : comparaison au mobile « nickel ». | NV:220 | **clos (03/11)** | [à vérifier] |  |
| G-170 | Flèches opposées : tant qu'une des deux reste enfoncée après la pression double, rien ne bouge (le relâchement n'est jamais simultané) **03/11** : « pour les flèches aussi ». | NV:224 | **clos (03/11)** | [à vérifier] |  |
| G-171 | Compagnons en ville : essais successifs (#30, #33, #34, #35, #36, #37) ; état actuel « tout accélère » (horloge) ; PNJ en mouvement et course x4 non mesurés **03/11** : « tout est OK ». | PR #37 ; NV:282, NV:295, NV:304 | **clos (03/11)** | [à vérifier] | D-61 |
| G-172 | Dernier état du bouton « Menu Pause » (PR #35-#37) retiré en #41 : la notice de #35 (NV:293) décrit encore sa plaque « copie » | NV:293 ; PR #41 | obsolète | [oubli] (doc) | D-68, D-76 |
| G-173 | Entrée (Commandes), Espace (Discussion) et M (Carte) ne jouent **pas** le bruitage 300 alors que le clic sur le bouton à l'écran le joue (comme `TouchPad.internalUpdate`) : écart de fidélité mineur signalé, non corrigé **Règle de Sylfried (03/11, D-156) : au clavier, un bruitage seulement là où le toucher en joue un, jamais ajouté de force** ; à traiter au cas par cas. | NV:368 | **corrigé #228 (04/11 : Entrée, Espace et M jouent le bruitage 300 quand le moteur autorise le bouton ; B, flèches, ▲ ▼, retours muets) ; à valider sur Windows** ; **règle confirmée le 03/11** (D-166 ; #60) | [oubli] | D-103 |

## J. Lot en cours (PR #43) : tout ce qui est demandé depuis 02 h 12 (état : demandé, pas encore fusionné)

| ID | Demande (source) | Mission | Classement | Lien |
|---|---|---|---|---|
| G-200 | Dragon à une seule orientation, composition 1 pour 1 du mobile (zone portrait au centre), logo centré, fond moins répétitif (02:12) **03/11** : dragon bon (D-190). | titre2 | **clos (03/11)** | D-33, D-11 |  |
| G-201 | Plaque « Sauvegarde automatique » toujours présente, grisée si pas de sauvegarde auto ; choix laissé à Claude (02:12, 02:13) | titre2 | traité (#43) | D-32 |  |
| G-202 | Molette cliquée : rotation ; clic simple : direction ; Ctrl + clic : zoom (02:12) | entrées | traité (#43), **retiré le 04/11 (D-226, #264)**, rotation et clic simple rétablis le 05/11 (D-233, #278, faits par le jeu depuis D-234, #286), zoom toujours retiré | D-34 |  |
| G-203 | Le jeu prend le dessus sur le réglage (vitesse du texte et « tout ») (02:12) | options | traité (#43) | D-14 |  |
| G-204 | Correction des bords : suppression de l'option, toujours active (02:12) | fenêtre2 | traité (#43) | D-31 |  |
| G-205 | Coffres : animation dans le bon sens, orientés vers le joueur (02:12) **03/11 16 h 47** : sens d'ouverture OK (D-192). | coffres | **clos (03/11, 16 h 47)** | D-42 |  |
| G-206 | Plein écran exclusif supprimé ; plein écran / fenêtré par Alt+Entrée et F11 ; interrupteur dans les options (02:12) **03/11** : F11 / Alt + Entrée OK. | fenêtre2 | **clos (03/11)** | D-30 |  |
| G-207 | Nom de Ragnar « trop bas, t'en penses quoi ? » (02:12) : demande d'avis **03/11** : « Non c'est bon ». | options | **clos (03/11, D-185)** | D-43 |  |
| G-208 | Souris inutilisable ~1 s après le clavier (02:12) | entrées | traité (#43) | D-44 |  |
| G-209 | F1 en haut à droite par défaut (02:14) | entrées | traité (#43) | D-45 |  |
| G-210 | Option « Lissage des textures » supprimée, lissage toujours actif (02:27) | fenêtre2 | traité (#43) | D-46 |  |
| G-211 | `camera_centree` activée par défaut (02:29). **Clos par #47** : l'option « Centrer la caméra sur le joueur » est supprimée, la caméra est toujours centrée tant que le joueur l'a (`window.py:1171-1172`) ; les clés `camera_centree` et `suivi_camera_v` sont dans `CLES_OBSOLETES` (`settings.py:99-100`). Le `reglages.json` de Sylfried n'a donc plus d'effet sur ce point. Le lissage des textures est lui aussi toujours actif (option retirée) | #47 | **clos** | [établi] | D-47 |
| G-212 | « Vitesse de l'accélérateur » → « Multiplicateur de l'accélérateur » (02:35) **03/11 16 h 47** : le multiplicateur de l'accélérateur reste (D-201). | combat | traité (#43) | D-48 |  |
| G-213 | Vitesse des combats x1 / x2 / x3 (libellés Normal > Rapide > Très rapide), en combat et dans Commandes sous les lignes de l'accélérateur, non accélérable par l'accélérateur (02:35) **03/11 16 h 47** : l'accélérateur reste (D-201), la vitesse de combat aussi. | combat | traité (#43) | D-49 |  |
| G-214 | Précision (02:37) : le changement de vitesse du combat change la vitesse des **animations et des dialogues, mais PAS celle de la musique ni des bruitages** | combat | traité (#43) | D-18 |  |
| G-215 | Historique des messages avec l'indication de qui a parlé (nom, « message général », « une femme dans une grotte », « un soldat dans le château de Bastione », « un objet récupéré dans une jarre ») (02:36) | histo + libelles | traité (#43), vu OK le 03/11 | D-17 |  |
| G-216 | **Audit complet** : fonctionnalités absentes (casino, églises, banque…), menus, interrupteurs, variables, PNJ, scripts, avec classement décision / oubli / bug (02:12) **03/11** : rapport « ce qu'il reste » : `remaining_work_report.md`. | cet audit + couverture | traité (#44) | D-16, D-19 |  |
| G-217 | **Don d'expérience du roi (chapitre 1, `MaterielMenu_EXTRA_PRESENT_EXP`) : le jeu se figeait au dernier message de niveau** (signalé le 04/11/2026 à 21 h 15) : le menu attend, à son dernier état, un déclenchement du pad du jeu (`g_Pad + 2`, rempli d'après le 2e argument de `GameUpdate` : le toucher d'écran exactement 0x100, ou 0x400 à 0x2000) ; A pendant un message envoie 0x10, jamais lu. Revue de tout le jeu : 17 fonctions lisent `g_Pad + 2` (les autres : casino, fenêtres de ville et de carte, joueur du terrain) et 8 lisent le 2e argument tel quel (« non nul ») ; seul ce menu bloquait. **Non vérifié** : l'accélération des gains du casino par un appui (machine à sous `cashAllCoin`, poker, arène : le toucher ne fait qu'accélérer, A ne l'envoie pas pendant un message) | issue #261 ; PR #262 ; `tests/test_exp_gift_touch.py` | **corrigé (#262)**, à valider sur Windows | [à vérifier] (casino) | D-213 |

Sylfried a interrompu le travail de la session principale à 02:37:30 et 02:38:07 (heure locale ; la transcription, en UTC, dit 01:37:30Z et 01:38:07Z : « [Request interrupted by user] »). Ses messages de 02:37 et 02:38 précisent la vitesse du combat et confirment « tout doit être prit en compte depuis mon message envoyé à 2h12 ».

## K. Les 10 lacunes les plus graves pour la jouabilité (classement de lecture)

1. **G-092** boutiques (achat / vente / quantité) : jamais jouées, aucune sauvegarde de test n'y mène.
2. **G-120** sauvegarde réelle à l'église puis rechargement : jamais confirmée sous Windows (issue #9, prio:haute) ; liée à G-123 (originaux intacts).
3. **G-093** casino, banque, église (confession), mini-jeux : aucun test documenté (à trancher par l'agent couverture).
4. **G-031** autres moyens de transport (bateau, ballon) : jamais étudiés ; sans eux la progression de l'aventure est suspendue.
5. **G-001 / G-023** rendu Windows / GPU réel jamais vérifié, aucune comparaison avec le mobile.
6. **G-044** allocateur sans libération : arrêt `MemoryError` possible sur longue session.
7. **G-070, G-071, G-078** boss, groupes de monstres, effets de sorts, victoire / montée de niveau / game over : non vérifiés.
8. **G-041, G-042, G-043, G-052, G-069** scènes d'histoire (FEAN, poses couchées, teinte, auberge, chapitres, générique) non rejouées.
9. **G-055** murs invisibles et escalier de `dbout` : risque de blocage ; **G-079** retour au titre depuis un combat ou une boutique puis nouvelle partie sans relancer non vérifié.
10. **G-099 / G-098** nom (refusé, clavier inventé), sexe à la manette ; effacement de la sauvegarde auto par « Revenir à l'écran titre ».

Déjà dans le lot en cours (§J) : G-058 (coffres), G-059 (dragon), G-097 (sauvegarde auto), G-105 (souris), G-111 (priorité du jeu), G-114 à G-118.

## L. Volumes (comptés par script sur ce fichier)

- **161 lignes numérotées** : 144 lacunes (sections A à I) + 17 demandes du lot en cours (§J, G-200 à G-216).
- Statuts des 144 lacunes : ouvert 111 (dont 4 « volontaire » et 4 « limite »), traité à reconfirmer 15, traité 3 (dont 1 en partie), en cours 11, obsolète ou probablement obsolète 3, autres 1 (en pause).
- Classement provisoire (un tag principal par ligne ; une ligne en porte parfois deux) : **[à vérifier] 97, [oubli] 19, [décision] 17, [bug] 12**. La grande part de « à vérifier » vient de l'absence de test Windows/GPU et de capture du mobile : ce n'est pas un jugement de gravité.
- Recherche de marqueurs dans le code (`TODO`, `FIXME`, `NotImplemented`) : aucun (établi).
