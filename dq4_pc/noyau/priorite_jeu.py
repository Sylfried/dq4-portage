"""Priorite du jeu sur les reglages du joueur (sans dependance : importe par le moteur, la fenetre et les tests).

Principe : un reglage du joueur est une VALEUR PAR DEFAUT, appliquee tant que le jeu ne fixe pas lui-meme le parametre. Des que le jeu le fixe explicitement (commande de script, verrou d'evenement,
camera de scene...), sa valeur s'applique, jusqu'a ce qu'il rende la main. Le joueur ne reprend pas la main sur ce que le script a decide.
Les fonctions ci-dessous sont les regles pures (testees par outils/test_priorite_jeu.py) ; la detection du « le jeu l'a fixe » est faite par l'appelant (moteur.py, fenetre.py)."""

LETTRES_STANDARD = 4        # lettres ecrites par image du moteur par un dialogue ordinaire (mot de vitesse 1 du tableau des types de fenetre, x 4) : la valeur « par defaut » du jeu pour le texte
MARQUE_FONDU_SCRIPT = 0x10000       # bit ajoute (par la visionneuse) a l'entier du paquet 9 d'un fondu lance par une commande de script du jeu (fade_in / fade_out) ; le moteur n'utilise pas ce bit


def valeur_effective(reglage_joueur, valeur_jeu=None):
    """La valeur qui s'applique : celle du jeu quand il en a fixe une (valeur_jeu n'est pas None), sinon le reglage du joueur."""
    return reglage_joueur if valeur_jeu is None else valeur_jeu


def facteur_effectif(reglage_joueur, jeu_fixe, neutre=1.0):
    """Reglage du joueur qui MULTIPLIE une grandeur du jeu (vitesse, zoom) : quand le jeu fixe lui-meme la grandeur (jeu_fixe vrai), le facteur neutre s'applique et la valeur du jeu reste telle quelle."""
    return valeur_effective(reglage_joueur, neutre if jeu_fixe else None)


def lettres_par_image(reglage_joueur, lettres_moteur, standard=LETTRES_STANDARD):
    """Lettres ecrites a cette image du moteur. `lettres_moteur` = ce que le moteur s'apprete a ecrire (mot de vitesse de la fenetre x 4). Au standard (dialogue ordinaire), c'est le reglage du joueur ; toute autre valeur
    (fenetres de combat qui affichent leur ligne d'un coup, vitesse fixee par le jeu) est celle du jeu et le reglage du joueur n'y change rien."""
    return valeur_effective(reglage_joueur, None if lettres_moteur == standard else lettres_moteur)


def duree_fondu(duree, facteur, script=False):
    """Duree (en images) d'un fondu au noir une fois le reglage « vitesse des transitions » applique : la duree d'origine divisee par le facteur (x1 = telle quelle, un fondu d'une image ou moins est immediat).
    Un fondu lance par une commande de script du jeu garde sa duree : le script l'a fixee, et attend lui-meme ce nombre d'images."""
    return valeur_effective(max(1, int(round(duree / facteur))) if duree > 1 and facteur > 1.0 else duree, duree if script else None)
