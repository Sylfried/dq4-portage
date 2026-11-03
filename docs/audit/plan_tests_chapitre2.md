# Plan de test à rejouer avec la sauvegarde du chapitre 2

Écrit le 03/11/2026 (décision D-168 : Sylfried fournira la sauvegarde du chapitre 2 « dès que possible » et demande de « garder bien tous ces tests en mémoire »). Aucune sauvegarde réelle n'existe au-delà du chapitre 1 : **rien de ce qui suit n'a jamais été vu**. Issues liées : #62 à #65, #58, #56, #90, #99. Légende des cases : `[ ]` à faire.

## 0. Avant de commencer
- [ ] Recevoir la sauvegarde du chapitre 2 (et, si possible, des captures du mobile aux mêmes endroits) ; la mettre dans une **copie en lecture seule** (les vraies sauvegardes ne sont jamais modifiées).
- [ ] Lancer la suite de tests automatiques existante sur cette sauvegarde (`outils/flux_session/lancer_tests.sh`, voir `docs/reprise.md` §4) : certains tests n'ont de sens qu'avec une sauvegarde plus avancée.
- Pour chaque défaut : une issue (carte, touches, sauvegarde utilisée, capture sans contenu du jeu), étiquette `type:bug`.

## 1. Cartes et scénario (#62)
- [ ] Rejouer les cartes du chapitre 2 : PNJ de scénario qui apparaissent ou disparaissent (CAR-14), menus qui changent.
- [ ] Colisée et arène jusqu'au bout ; générique de fin.
- [ ] Titre et **sous-titre des chapitres suivants** ; paquet 33 (`map_color_rate`, teinte à l'ouverture de `mlb1a`) ; paquets 16 / 17 des cartes `ml*` (#58).
- [ ] Séquences à fondu : auberge, écran de chargement, sifflet, ballon, sol qui soigne (#90).

## 2. Services (#63)
- [ ] Auberge par le PNJ ; sorts du menu (Magie) ; divination ; bénédiction ; purification.
- [ ] Radeau ; henge ; sifflet ; Rura.

## 3. Boutiques, bestiaire, banque (#64)
- [ ] Boutiques types **28**, **59**, **63**, **70** (dont la boutique de Torneko et le « surechigai », G-164) : achat et vente, quantités gauche / droite, choix grisés (PM insuffisants, objets inutilisables), pages et défilement.
- [ ] **Bestiaire** : aucun bouton trouvé au chapitre 1 ; voir si un objet ou un chapitre le débloque.
- [ ] Banque : dépôt et retrait, **3 150 G** (la colonne exacte choisie par ◀ ▶ n'a jamais été testée ; sujet suspendu avec #59, mais à la souris le test reste valable).

## 4. Casino de Chandor (#65, #81)
- [ ] Poker : libellé « Abandonner » (chevauchement possible) ; bingo : animation du paquet 6 (#66).
- [ ] « ERROR 3080@ » dans des dialogues de PNJ du casino (texte du patch FR : ne pas y toucher ; noter l'endroit exact).

## 5. Combats plus avancés (#56)
- [ ] Effets de sorts (défense augmentée, flashs, effets d'écran 3 / 5 / 6, #68), Morph d'un monstre en combat, boss, boss final (caméra 132).
- [ ] Retour au titre depuis un combat ou une boutique.
- [ ] Décors d'aube et de coucher de soleil.
- [ ] Caméra pendant les attaques (#92) : à comparer d'abord avec des ennemis du **chapitre 1** (l'archer vert ; l'Ornythox n'est plus un exemple sûr, Sylfried, 03/11 à 16 h 47) ; ensuite avec ceux du chapitre 2.

## 6. Menus
- [ ] Statut (pages), liste des sorts de chaque personnage : une rangée fantôme a été supprimée en #45 (`outils/test_magie_liste.py`) ; Sylfried a confirmé (03/11, 16 h 47 : « Exactement ») que c'était bien le « sort en trop » ; **vérifier sur Windows qu'il a disparu** (#99).
- [ ] Choix grisés, pages et curseurs gauche / droite des menus (G-094).
- [x] Coffres : le couvercle s'ouvre dans le bon sens (Sylfried, 03/11 à 16 h 47 : « c'est bon dans le bon sens »).
