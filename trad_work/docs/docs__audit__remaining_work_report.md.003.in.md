## Livré dans la PR #44

Branche `audit2-histo`, pas encore ouverte en PR. Après fusion des cinq agents d'audit, 19 fichiers de tests passent, plus le test moteur de la vitesse de combat.

- **Historique** : trois onglets (Dialogues hors combat, Combats avec ennemis, or et expérience, Favoris), nom du locuteur seulement s'il était affiché, fond translucide, touche H en cycle (messages, combats, fermer). Dialogues et combats disparaissent à la fermeture, les favoris restent jusqu'à suppression.

- **Combat** : réglage unique « Vitesse de combat » (Manuel, Normal, Rapide, Très rapide) avec bouton à flèches à côté de « Fuir » ; la vitesse des ennemis suit. Combats de nuit : cause trouvée (couleur de l'asset jamais utilisée par le jeu), décor corrigé.

- **Réglages** : boutons ↺ de retour à la valeur par défaut sur chaque ligne à valeurs ; option, désactivée par défaut, pour regagner tous les PV et PM à chaque niveau (vérifiée sur un vrai combat gagné).

- **Carte du monde** : cycle jour et nuit (teinte des décors) et échelle des sprites.

- **Audit** : 32 cartes qui sortaient vides corrigées, 3 PNJ jamais dessinés, états enregistrés qui oubliaient les correctifs, pages du Statut au clavier, saisie des montants au clavier (banque, jetons, mises), poker enfin visible et jouable, arrêt de la victoire dans l'arène et touche de vitesse qui n'agissait pas en arène.

- **Docs** : README et notes mises à jour (sections « Avance #44 »).
