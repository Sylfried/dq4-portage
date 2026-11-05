## 7. Ce qui n'a pas pu être vérifié

- **Tout ce qui est Windows, GPU, plein écran, deux moniteurs, DPI, écoute réelle, fluidité à x3 / x4, antivirus, OneDrive** (les verdicts « à valider sur Windows »).
- **Le jeu mobile lui-même** : aucune capture, aucun appareil ; l'original se lit dans le code IL2CPP, le moteur natif et les données.
- **Les chapitres 2 et suivants joués de bout en bout** (la scène des compagnons d'Alina, le sous-titre du chapitre 2, bateau, ballon en vol, entrée par les autres villes, colisée, fin du jeu) : ton chapitre 2 manque toujours.
- **14 types de fenêtres jamais ouverts**, listes Magie / Objets et cibles en combat (héros du slot 4 sans sort ni objet), défaite en combat, boss final, divination / bénédiction / purification, radeau, henge, sifflet, Rura, poker jusqu'au bout, bingo.
- **Un vrai tas de 256 Mo rempli** (l'épuisement a été simulé en avançant le pointeur du tas) ; un APK anglais non patché ; les textes affichés par langue du moteur.

## 8. Ce que l'audit n'a pas touché

Aucun fichier du code, aucune sauvegarde réelle, aucun fichier du patch FR. Les `__pycache__` ignorés par git que certains relecteurs ont signalés dans `dq4_pc/` datent d'avant l'audit (essais précédents) ; ils ne sont pas versionnés.
