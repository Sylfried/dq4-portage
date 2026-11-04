"""Entrees souris / clavier de la visionneuse : la logique pure (sans fenetre ni OpenGL), pour la tester (outils/test_entrees.py).
- souris_active / GardeSouris : quand le pointeur reprend la main apres un usage du clavier (survol et selection) ;
- zone_infos : ou se pose le bloc d'infos de F1 (en haut a droite)."""
import math

# ---- pointeur et clavier
TOLERANCE_SOURIS = 4.0        # pixels : ecart, depuis la position du pointeur quand le clavier a servi pour la derniere fois, a partir duquel la souris reprend la main (survol, selection). Compte CUMULE depuis cette position
                              # (et non d'un evenement au suivant : une souris moderne envoie des evenements de 1 a 2 pixels, jamais « assez grands » un par un) ; un tremblement de la table ou du capteur (1 a 2 px) ne reprend rien


def souris_active(ref, pos, tol=TOLERANCE_SOURIS):
    """Le pointeur a-t-il vraiment bouge ? `ref` : position (x, y) du pointeur quand le clavier a servi pour la derniere fois (None = la souris a deja la main : un clic, ou un vrai mouvement depuis) ;
    `pos` : position actuelle. Vrai si la souris a la main ou si le pointeur s'est ecarte de `ref` d'au moins `tol` pixels. Un clic n'a jamais besoin de ce test : il agit toujours."""
    if ref is None or pos is None: return True
    return math.hypot(pos[0] - ref[0], pos[1] - ref[1]) >= tol


class GardeSouris:
    """Memoire du « dernier peripherique » : le clavier (touche pressee) fige la position de reference ; le premier vrai mouvement (souris_active) ou un clic rend la main a la souris, sans delai."""

    def __init__(self, tol=TOLERANCE_SOURIS):
        self.tol = tol; self.ref = None

    def clavier(self, pos):
        """Une touche vient d'etre pressee, le pointeur est en `pos` (None : position inconnue, le premier mouvement compte)."""
        self.ref = None if pos is None else (float(pos[0]), float(pos[1]))

    def clic(self):
        self.ref = None

    @property
    def souris(self):
        return self.ref is None

    def bouge(self, pos):
        """Mouvement du pointeur en `pos` : vrai si la souris a (ou reprend) la main, faux si ce n'est qu'un tremblement apres l'usage du clavier."""
        if souris_active(self.ref, pos, self.tol): self.ref = None; return True
        return False


# ---- bloc d'infos de F1
def zone_infos(largeur, hauteur, colonne, ui_zoom, ui_pos='centre'):
    """Bloc d'infos de F1 (lieu, reglages, performances) : (cote, largeur disponible) ; le cote est 'droite' par defaut (en haut a droite de l'ecran), 'gauche' si la colonne d'interface occupe la droite.
    La largeur est la marge libre a cote de la colonne d'interface (portrait 450 x 800, agrandie de ui_zoom ; `colonne` faux : pas de fenetres du jeu, tout l'ecran), pour ne pas cacher ses fenetres ; au moins 260 pixels."""
    larg_col = 450 * hauteur / 800.0 * ui_zoom
    if colonne and ui_pos == 'droite': return 'gauche', int(max(260, largeur - larg_col - 16))
    if colonne and ui_pos == 'gauche': return 'droite', int(max(260, largeur - larg_col - 16))
    if colonne: return 'droite', int(max(260, (largeur - larg_col) / 2 - 16))
    return 'droite', int(max(260, largeur - 20))


# ---- touche A pendant une attente de « toucher »
def toucher_pour_le_moteur(p, decl, bit_a, bit_b, toucher, attend):
    """(p, decl) envoyes au moteur. `attend` : un menu du jeu attend le toucher d'ecran (Moteur.attend_toucher : le don d'experience du roi) ; `toucher` : la valeur qu'il lit (exactement 0x100). A (touche, clic, Entree, Espace) envoie ce toucher
    seul, sans A ni B ; le reste du temps rien ne change. Un message ouvert recevrait sinon A (0x10), que ce menu ne lit pas : le jeu restait fige au dernier message de niveau (#261)."""
    if attend and decl & bit_a: return p & ~(bit_a | bit_b), toucher
    return p, decl
