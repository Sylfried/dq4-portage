# Historique du projet

Le projet a démarré le 29/10/2026 (avant la création de ce dépôt). Chaque étape est reprise dans une issue **fermée** du jalon *M0 Fondations (terminé)* ; le détail technique est dans `docs/notes-*.md`.

| Date | Étape | Issue |
|---|---|---|
| 29/10 | Cadrage : portage natif PC de DQ4, 16/9 d'abord, voies A/B/C, projet séparé du patch FR | #25 |
| 29/10 | Voie A validée : `libdq4core.so` tourne sous Unicorn (testé sur pdc et Linux) | #26 |
| 29/10 soir | Protocole moteur → Unity décodé (paquets, mot d'état, fondu) | #27 |
| 29/10 soir | Démarrage sans Unity, chargement d'une sauvegarde (`loadbank`) | #28 |
| 29/10 soir | Lecture des données Unity : cartes, textures, feuilles de sprites | #29 |
| 29/10 soir | Premier rendu côté cloud : l'église avec le personnage | #30 |
| 29-30/10 | Visionneuse pyglet 16/9 temps réel, clavier, lanceur `lancer_dq4.bat` | #31 |
| 30/10 | Portes et changement de carte (blocage signalé sur pdc, corrigé) | #32 |
| 30/10 | Sprites nets (flou signalé sur pdc, corrigé), silhouette de l'équipe | #33 |
| 30/10 | Cadrage 16/9 du village, ciel, bornes de caméra | #34 |
| 30/10 | Messages : texte français du moteur dans une fenêtre | #35 |
| 30/10 nuit | Menus : file MenuPort, liste de l'église, menu de commandes, saisie clavier | #36 |
| 30/10 | Dépôt GitHub, règles de travail, issues de départ | #37 |

| 30/10 nuit | Séparation du dépôt d'origine `dq4-pc` : portage natif (ici), essai Unity (`dq4-portage-unity`), patch français (inchangé) | — |

## Et maintenant
Les jalons ouverts : **M1 Village jouable 16/9**, **M2 Monde et combats**, **M3 Son et finitions**. Prochaine issue : #1 (sprites en HD).
