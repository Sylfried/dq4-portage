"""Vitesse des combats : l'horloge du moteur pendant un combat (logique pure, sans fenetre ni moteur : testee par outils/test_vitesse_combat.py).

Principe : le moteur d'origine avance par pas de 1 / 30 s (Time.fixedDeltaTime). La visionneuse lui fait faire, par seconde reelle, 1, 2 ou 3 fois plus de pas pendant un combat (reglage « Vitesse des combats » :
Normal, Rapide, Tres rapide), au lieu de changer quoi que ce soit dans le moteur. Chaque pas est exactement celui du jeu : le resultat d'un combat (degats, ordre des actions, tirages au hasard, delais comptes en
images) ne depend donc pas de la vitesse ; seule la duree reelle change. Tout ce que la visionneuse anime pendant un combat est compte en pas du moteur (`moteur.images` + fraction `alpha`) : nombres de degats,
secousses des plaques, fondus, effet de debut de combat, defilement des messages (ecrit par le moteur), animation des modeles 3D ; ils suivent donc l'horloge accelere.

Ce qui n'est PAS accelere, a dessein :
  - la musique et les bruitages : ils sont lus par pyglet a leur vitesse normale (heures reelles, duree du fichier) ; seule la DATE de declenchement d'un bruitage suit le moteur. Si l'acceleration fait arriver le meme
    bruitage plusieurs fois dans la meme image affichee, il n'est lance qu'une fois (`sons_a_jouer`) ;
  - les attentes de saisie du joueur (menu de commandes, choix de la cible, message « Manuel » qui attend une touche) : le moteur y tourne a vitesse normale (`facteur`), donc le curseur et les repetitions de touche
    gardent leur cadence et les monstres leur animation de repos ;
  - la touche d'accelerateur : elle ne multiplie que la marche et la camera hors combat. `facteur` n'a volontairement aucun parametre pour elle."""
import math

PAS_MOTEUR = 1.0 / 30.0                  # le moteur d'origine avance a 30 Hz
BUDGET_PAS = 0.030                       # duree maximale (s) des pas du moteur dans une meme image affichee quand l'horloge est acceleree : au-dela, le jeu prend du retard au lieu de figer l'affichage
TOLERANCE = 0.85                         # un pas est fait des que 85 % de sa duree s'est ecoulee (ecran de 60 Hz : un pas toutes les 2 images exactement, sans gigue 2 / 3 images)
RATTRAPAGE = 3                           # au plus 3 pas de rattrapage par image affichee a vitesse normale (un blocage plus long est oublie)
VITESSE_MAX = 3.0


def facteur(vitesse, en_combat, attend_saisie):
    """Facteur d'horloge du moteur pendant un combat ; None hors combat (l'appelant applique alors la vitesse de marche). `vitesse` : reglage « Vitesse des combats » (1, 2 ou 3).
    `attend_saisie` : le moteur attend le joueur (menu de commandes, cible, message qui attend une touche) : vitesse normale."""
    if not en_combat: return None
    if attend_saisie: return 1.0
    try: v = float(vitesse)
    except (TypeError, ValueError): return 1.0
    if v != v: return 1.0
    return max(1.0, min(VITESSE_MAX, v))


def avancer(acc, dt, f, faire_pas, horloge, pas=PAS_MOTEUR, budget=BUDGET_PAS):
    """Une image affichee : l'horloge du moteur avance de `dt * f` secondes ; `faire_pas()` fait un pas du moteur autant de fois qu'elle l'exige (au plus 3 x ceil(f)), en bornant le temps de calcul a `budget`
    secondes quand f > 1 (marche acceleree, combat). `faire_pas()` renvoie False quand le moteur vient de se mettre a attendre le joueur : on s'arrete la, sans rattraper le reste.
    -> (acc restant en secondes de moteur, nombre de pas faits, budget depasse). Le reste d'horloge est oublie si le rattrapage est au maximum, si le budget est depasse ou si le moteur attend le joueur."""
    acc += min(dt * f, RATTRAPAGE * pas * max(1.0, f))
    n = 0; nmax = RATTRAPAGE * max(1, math.ceil(f)); coupe = False; attente = False; t0 = horloge()
    while acc >= pas * TOLERANCE and n < nmax:
        suite = faire_pas(); acc -= pas; n += 1
        if f > 1.0 and horloge() - t0 > budget: coupe = True; break
        if suite is False: attente = True; break
    if n == nmax or coupe or attente: acc = 0.0
    return acc, n, coupe


def sons_a_jouer(evenements, deja):
    """Ordres de son d'un pas du moteur [(type de paquet, valeur)] -> ceux a jouer, en ne lancant pas deux fois le meme bruitage (paquet 35) dans la meme image affichee : `deja` est l'ensemble des bruitages
    deja lances depuis le debut de cette image (mis a jour ici). Un arret (paquet 36) libere son bruitage : un nouveau depart apres lui est joue. La musique (paquet 37) n'est jamais filtree. `deja` None : tout passe."""
    if deja is None: return list(evenements)
    out = []
    for t, v in evenements:
        if t == 35:
            if v in deja: continue
            deja.add(v)
        elif t == 36: deja.discard(v)
        out.append((t, v))
    return out
