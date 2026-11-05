"""Priorite du jeu sur les reglages du joueur (sans dependance : importe par le moteur, la fenetre et les tests).

Principe : un reglage du joueur est une VALEUR PAR DEFAUT, appliquee tant que le jeu ne fixe pas lui-meme le parametre. Des que le jeu le fixe explicitement (commande de script, verrou d'evenement,
camera de scene...), sa valeur s'applique, jusqu'a ce qu'il rende la main. Le joueur ne reprend pas la main sur ce que le script a decide.
Les fonctions ci-dessous sont les regles pures (testees par tools/test_game_priority.py) ; la detection du « le jeu l'a fixe » est faite par l'appelant (engine.py, window.py)."""

STANDARD_LETTERS = 4        # lettres ecrites par image du moteur par un dialogue ordinaire (mot de vitesse 1 du tableau des types de fenetre, x 4) : la valeur « par defaut » du jeu pour le texte
SCRIPT_FADE_MARK = 0x10000       # bit ajoute (par la visionneuse) a l'entier du paquet 9 d'un fondu lance par une commande de script du jeu (fade_in / fade_out) ; le moteur n'utilise pas ce bit


def effective_value(player_setting, game_value=None):
    """La valeur qui s'applique : celle du jeu quand il en a fixe une (game_value n'est pas None), sinon le reglage du joueur."""
    return player_setting if game_value is None else game_value


def effective_factor(player_setting, game_fixed, neutral=1.0):
    """Reglage du joueur qui MULTIPLIE une grandeur du jeu (vitesse, zoom) : quand le jeu fixe lui-meme la grandeur (game_fixed vrai), le facteur neutre s'applique et la valeur du jeu reste telle quelle."""
    return effective_value(player_setting, neutral if game_fixed else None)


def letters_per_frame(player_setting, engine_letters, standard=STANDARD_LETTERS):
    """Lettres ecrites a cette image du moteur. `engine_letters` = ce que le moteur s'apprete a ecrire (mot de vitesse de la fenetre x 4). Au standard (dialogue ordinaire), c'est le reglage du joueur ; toute autre valeur
    (fenetres de combat qui affichent leur ligne d'un coup, vitesse fixee par le jeu) est celle du jeu et le reglage du joueur n'y change rien."""
    return effective_value(player_setting, None if engine_letters == standard else engine_letters)


def fade_duration(duration, factor, script=False):
    """Duree (en images) d'un fondu au noir une fois le reglage « vitesse des transitions » applique : la duree d'origine divisee par le facteur (x1 = telle quelle, un fondu d'une image ou moins est immediat).
    Un fondu lance par une commande de script du jeu garde sa duree : le script l'a fixee, et attend lui-meme ce nombre d'images."""
    return effective_value(max(1, int(round(duration / factor))) if duration > 1 and factor > 1.0 else duration, duration if script else None)
