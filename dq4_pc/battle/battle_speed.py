"""Vitesse des combats : l'horloge du moteur pendant un combat (logique pure, sans fenetre ni moteur : testee par tools/test_battle_speed.py).

Principe : le moteur d'origine avance par pas de 1 / 30 s (Time.fixedDeltaTime). La visionneuse lui fait faire, par seconde reelle, 1, 2 ou 3 fois plus de pas pendant un combat (reglage « Vitesse de combat » :
Manuel et Normal : 1 ; Rapide : 2 ; Tres rapide : 3), au lieu de changer quoi que ce soit dans le moteur. Chaque pas est exactement celui du jeu : le resultat d'un combat (degats, ordre des actions, tirages au hasard, delais comptes en
images) ne depend donc pas de la vitesse ; seule la duree reelle change. Tout ce que la visionneuse anime pendant un combat est compte en pas du moteur (`engine.frames` + fraction `alpha`) : nombres de degats,
secousses des plaques, fondus, effet de debut de combat, defilement des messages (ecrit par le moteur), animation des modeles 3D ; ils suivent donc l'horloge accelere.

Ce qui n'est PAS accelere, a dessein :
  - la musique et les bruitages : ils sont lus par pyglet a leur vitesse normale (heures reelles, duree du fichier) ; seule la DATE de declenchement d'un bruitage suit le moteur. Si l'acceleration fait arriver le meme
    bruitage plusieurs fois dans la meme image affichee, il n'est lance qu'une fois (`sounds_to_play`) ;
  - la LECTURE des touches pendant les attentes du joueur (menu de commandes, choix de la cible, message « Manuel » qui attend une touche) : le moteur y tourne a la vitesse du reglage (les monstres gardent leur animation
    de repos a cette vitesse) mais seuls les pas a cadence normale (un toutes les 1 / 30 s reelles) lisent les touches ; les autres sont « muets » (fenetre.tick(muet=True)) : curseur et repetition des touches inchanges ;
  - la touche d'accelerateur : elle ne multiplie que la marche et la camera hors combat. `factor` n'a volontairement aucun parametre pour elle."""
import math

ENGINE_STEP = 1.0 / 30.0                  # le moteur d'origine avance a 30 Hz
STEP_BUDGET = 0.030                       # duree maximale (s) des pas du moteur dans une meme image affichee quand l'horloge est acceleree : au-dela, le jeu prend du retard au lieu de figer l'affichage
TOLERANCE = 0.85                         # un pas est fait des que 85 % de sa duree s'est ecoulee (ecran de 60 Hz : un pas toutes les 2 images exactement, sans gigue 2 / 3 images)
CATCHUP = 3                           # au plus 3 pas de rattrapage par image affichee a vitesse normale (un blocage plus long est oublie)
MAX_SPEED = 3.0


def factor(speed, in_battle):
    """Facteur d'horloge du moteur pendant un combat ; None hors combat (l'appelant applique alors la vitesse de marche). `speed` : reglage « Vitesse de combat » (0 Manuel, 1 Normal, 2 Rapide, 3 Tres rapide) :
    Manuel et Normal gardent l'horloge du jeu (facteur 1 ; Manuel passe en plus les messages a la main, voir reglages.scroll_code). Meme quand le moteur attend le joueur (menu de commandes, cible, message qui attend
    une touche) le facteur reste celui du reglage : les monstres gardent leur animation de repos a la vitesse choisie, et c'est la LECTURE des touches qui reste a cadence normale (pas muets, voir fenetre._do_battle_step)."""
    if not in_battle: return None
    try: v = float(speed)
    except (TypeError, ValueError): return 1.0
    if v != v: return 1.0
    return max(1.0, min(MAX_SPEED, v))


def advance_time(acc, dt, f, do_step, clock, step=ENGINE_STEP, budget=STEP_BUDGET):
    """Une image affichee : l'horloge du moteur avance de `dt * f` secondes ; `do_step()` fait un pas du moteur autant de fois qu'elle l'exige (au plus 3 x ceil(f)), en bornant le temps de calcul a `budget`
    secondes quand f > 1 (marche acceleree, combat). `do_step()` renvoie False quand le moteur vient de se mettre a attendre le joueur : on s'arrete la, sans rattraper le reste.
    -> (acc restant en secondes de moteur, nombre de pas faits, budget depasse). Le reste d'horloge est oublie si le rattrapage est au maximum, si le budget est depasse ou si le moteur attend le joueur."""
    acc += min(dt * f, CATCHUP * step * max(1.0, f))
    n = 0; nmax = CATCHUP * max(1, math.ceil(f)); cut = False; waiting = False; t0 = clock()
    while acc >= step * TOLERANCE and n < nmax:
        suite = do_step(); acc -= step; n += 1
        if f > 1.0 and clock() - t0 > budget: cut = True; break
        if suite is False: waiting = True; break
    if n == nmax or cut or waiting: acc = 0.0
    return acc, n, cut


def sounds_to_play(events, already):
    """Ordres de son d'un pas du moteur [(type de paquet, valeur)] -> ceux a jouer, en ne lancant pas deux fois le meme bruitage (paquet 35) dans la meme image affichee : `already` est l'ensemble des bruitages
    deja lances depuis le debut de cette image (mis a jour ici). Un arret (paquet 36) libere son bruitage : un nouveau depart apres lui est joue. La musique (paquet 37) n'est jamais filtree. `already` None : tout passe."""
    if already is None: return list(events)
    out = []
    for t, v in events:
        if t == 35:
            if v in already: continue
            already.add(v)
        elif t == 36: already.discard(v)
        out.append((t, v))
    return out
