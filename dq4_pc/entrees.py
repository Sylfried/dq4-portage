"""Entrees souris / clavier de la visionneuse : la logique pure (sans fenetre ni OpenGL), pour la tester (outils/test_entrees.py).
- souris_active / GardeSouris : quand le pointeur reprend la main apres un usage du clavier (survol et selection) ;
- GesteMolette / pivoter : clic molette (clic simple, Ctrl + clic, glisser = rotation de la camera) ;
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


# ---- clic molette
SEUIL_GLISSE = 4.0            # pixels : deplacement, depuis l'appui, a partir duquel un clic molette devient un glissement (en dessous : un clic ; le tremblement de la main n'en fait pas un glissement)
CAM_SOURIS_LACET = 180.0      # glissement horizontal : degres de rotation de la camera pour un deplacement egal a la hauteur de la fenetre (la sensibilite ne depend pas de la resolution) ; droite = fleche droite
CAM_SOURIS_ANGLE = 120.0      # glissement vertical : degres d'inclinaison de la camera pour un deplacement egal a la hauteur de la fenetre ; haut = fleche haut (memes bornes que les fleches). Un peu moins sensible que l'horizontal :
                              # la plage d'inclinaison est etroite (60 degres) et une main ne glisse jamais parfaitement a l'horizontale


class GesteMolette:
    """Un geste du bouton du milieu : appui, deplacements, relachement. Un clic (relachement avant d'avoir bouge de SEUIL_GLISSE pixels) est « direction » (remise de la camera) ou « zoom » (avec Ctrl) ;
    un glissement fait tourner la camera, depuis le point ou le seuil est franchi (pas de saut au debut) ; apres un glissement, le relachement ne remet rien."""

    def __init__(self, seuil=SEUIL_GLISSE):
        self.seuil = seuil; self.annuler()

    def annuler(self):
        self.en_cours = False; self.glisse = False; self.ctrl = False; self.origine = None; self.dernier = None

    def appui(self, x, y, ctrl=False):
        self.en_cours = True; self.glisse = False; self.ctrl = bool(ctrl); self.origine = (x, y); self.dernier = (x, y)

    def deplacer(self, x, y):
        """Pointeur en (x, y), bouton du milieu enfonce -> (dx, dy) en pixels (y vers le haut) a appliquer a la camera ; (0, 0) tant que le geste reste un clic."""
        if not self.en_cours: return 0.0, 0.0
        if not self.glisse:
            if math.hypot(x - self.origine[0], y - self.origine[1]) < self.seuil: return 0.0, 0.0
            self.glisse = True; self.dernier = (x, y); return 0.0, 0.0
        d = (x - self.dernier[0], y - self.dernier[1]); self.dernier = (x, y)
        return float(d[0]), float(d[1])

    def relacher(self, ctrl=False):
        """-> 'direction' (clic simple : remet la camera en place), 'zoom' (Ctrl + clic : remet le zoom en place) ou None (fin d'un glissement, ou pas d'appui)."""
        etait, glissait, ctrl_appui = self.en_cours, self.glisse, self.ctrl
        self.annuler()
        if not etait or glissait: return None
        return 'zoom' if (ctrl or ctrl_appui) else 'direction'


def pivoter(lacet, angle, dx, dy, hauteur, a_min, a_max, limite=None):
    """Glissement de (dx, dy) pixels (y vers le haut) -> (lacet, angle) en degres : memes grandeurs que les fleches de la camera. Le lacet reste entre -180 et 180 (et entre -limite et +limite si le lieu borne la rotation),
    l'angle entre a_min et a_max."""
    k = 1.0 / max(1.0, float(hauteur))
    lacet += dx * k * CAM_SOURIS_LACET
    lacet = max(-limite, min(limite, lacet)) if limite is not None else (lacet + 180.0) % 360.0 - 180.0          # (lieu borne : on s'arrete a la limite, on ne fait pas le tour ; sinon le lacet boucle comme celui des fleches)
    return lacet, min(a_max, max(a_min, angle + dy * k * CAM_SOURIS_ANGLE))


# ---- bloc d'infos de F1
def zone_infos(largeur, hauteur, colonne, ui_zoom, ui_pos='centre'):
    """Bloc d'infos de F1 (lieu, reglages, performances) : (cote, largeur disponible) ; le cote est 'droite' par defaut (en haut a droite de l'ecran), 'gauche' si la colonne d'interface occupe la droite.
    La largeur est la marge libre a cote de la colonne d'interface (portrait 450 x 800, agrandie de ui_zoom ; `colonne` faux : pas de fenetres du jeu, tout l'ecran), pour ne pas cacher ses fenetres ; au moins 260 pixels."""
    larg_col = 450 * hauteur / 800.0 * ui_zoom
    if colonne and ui_pos == 'droite': return 'gauche', int(max(260, largeur - larg_col - 16))
    if colonne and ui_pos == 'gauche': return 'droite', int(max(260, largeur - larg_col - 16))
    if colonne: return 'droite', int(max(260, (largeur - larg_col) / 2 - 16))
    return 'droite', int(max(260, largeur - 20))
