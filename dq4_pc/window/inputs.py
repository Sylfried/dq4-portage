"""Entrees souris / clavier de la visionneuse : la logique pure (sans fenetre ni OpenGL), pour la tester (tools/test_entries.py).
- mouse_active / MouseGuard : quand le pointeur reprend la main apres un usage du clavier (survol et selection) ;
- WheelGesture / pivoter : clic molette (clic simple = camera ramenee au nord par le jeu, glisser a gauche / a droite = rotation de la camera, sens reglable) ;
- info_zone : ou se pose le bloc d'infos de F1 (en haut a droite)."""
import math

# ---- pointeur et clavier
MOUSE_TOLERANCE = 4.0        # pixels : ecart, depuis la position du pointeur quand le clavier a servi pour la derniere fois, a partir duquel la souris reprend la main (survol, selection). Compte CUMULE depuis cette position
                              # (et non d'un evenement au suivant : une souris moderne envoie des evenements de 1 a 2 pixels, jamais « assez grands » un par un) ; un tremblement de la table ou du capteur (1 a 2 px) ne reprend rien


def mouse_active(ref, pos, tol=MOUSE_TOLERANCE):
    """Le pointeur a-t-il vraiment bouge ? `ref` : position (x, y) du pointeur quand le clavier a servi pour la derniere fois (None = la souris a deja la main : un clic, ou un vrai mouvement depuis) ;
    `pos` : position actuelle. Vrai si la souris a la main ou si le pointeur s'est ecarte de `ref` d'au moins `tol` pixels. Un clic n'a jamais besoin de ce test : il agit toujours."""
    if ref is None or pos is None: return True
    return math.hypot(pos[0] - ref[0], pos[1] - ref[1]) >= tol


class MouseGuard:
    """Memoire du « dernier peripherique » : le clavier (touche pressee) fige la position de reference ; le premier vrai mouvement (mouse_active) ou un clic rend la main a la souris, sans delai."""

    def __init__(self, tol=MOUSE_TOLERANCE):
        self.tol = tol; self.ref = None

    def keyboard(self, pos):
        """Une touche vient d'etre pressee, le pointeur est en `pos` (None : position inconnue, le premier mouvement compte)."""
        self.ref = None if pos is None else (float(pos[0]), float(pos[1]))

    def click(self):
        self.ref = None

    @property
    def mouse(self):
        return self.ref is None

    def has_moved(self, pos):
        """Mouvement du pointeur en `pos` : vrai si la souris a (ou reprend) la main, faux si ce n'est qu'un tremblement apres l'usage du clavier."""
        if mouse_active(self.ref, pos, self.tol): self.ref = None; return True
        return False


# ---- clic molette
DRAG_THRESHOLD = 4.0            # pixels : deplacement, depuis l'appui, a partir duquel un clic molette devient un glissement (en dessous : un clic ; le tremblement de la main n'en fait pas un glissement)
CAM_MOUSE_YAW = 180.0      # glissement horizontal : degres de rotation de la camera pour un deplacement egal a la hauteur de la fenetre (la sensibilite ne depend pas de la resolution) ; droite = fleche droite


class WheelGesture:
    """Un geste du bouton du milieu : appui, deplacements, relachement. Un clic (relachement avant d'avoir bouge de DRAG_THRESHOLD pixels, dans n'importe quel sens) recentre la camera ; un glissement la fait tourner a gauche / a droite
    (seul le deplacement horizontal compte), depuis le point ou le seuil est franchi (pas de saut au debut) ; apres un glissement, le relachement ne recentre rien (un clic suivi d'un deplacement n'est pas un clic)."""

    def __init__(self, threshold=DRAG_THRESHOLD):
        self.threshold = threshold; self.cancel()

    def cancel(self):
        self.in_progress = False; self.dragging = False; self.origin = None; self.last = None

    def press_state(self, x, y):
        self.in_progress = True; self.dragging = False; self.origin = (x, y); self.last = (x, y)

    def move_to(self, x, y):
        """Pointeur en (x, y), bouton du milieu enfonce -> deplacement horizontal en pixels (vers la droite : positif) a appliquer a la camera ; 0 tant que le geste reste un clic."""
        if not self.in_progress: return 0.0
        if not self.dragging:
            if math.hypot(x - self.origin[0], y - self.origin[1]) < self.threshold: return 0.0
            self.dragging = True; self.last = (x, y); return 0.0
        dx = x - self.last[0]; self.last = (x, y)
        return float(dx)

    def let_go(self):
        """-> True si c'etait un clic simple (la camera se recentre), False apres un glissement ou sans appui."""
        was_in_progress, was_dragging = self.in_progress, self.dragging
        self.cancel()
        return bool(was_in_progress and not was_dragging)


def rotate(requested, dx, height_px, invert_gd=False, maximum=180.0):
    """Glissement horizontal de dx pixels -> rotation de la camera a faire, en degres (positif : vers la droite, comme la fleche droite) : meme grandeur que les fleches. `requested` : ce qui restait a tourner (le jeu ne tourne que par crans,
    voir Game._camera_after_step) ; le total reste entre -maxi et +maxi. `invert_gd` (reglage « Inverser gauche / droite ») : le sens du glissement est inverse ; les fleches du clavier ne passent pas par ici.
    Les limites du lieu, les verrous et les scenes sont ceux du jeu : il refuse la rotation (Engine.camera_wait) et la demande est abandonnee."""
    if invert_gd: dx = -dx
    return max(-maximum, min(maximum, requested + dx / max(1.0, float(height_px)) * CAM_MOUSE_YAW))


# ---- bloc d'infos de F1
def info_zone(width_px, height_px, column, ui_zoom, ui_pos='centre'):
    """Bloc d'infos de F1 (lieu, reglages, performances) : (cote, largeur disponible) ; le cote est 'droite' par defaut (en haut a droite de l'ecran), 'gauche' si la colonne d'interface occupe la droite.
    La largeur est la marge libre a cote de la colonne d'interface (portrait 450 x 800, agrandie de ui_zoom ; `column` faux : pas de fenetres du jeu, tout l'ecran), pour ne pas cacher ses fenetres ; au moins 260 pixels."""
    col_width = 450 * height_px / 800.0 * ui_zoom
    if column and ui_pos == 'droite': return 'gauche', int(max(260, width_px - col_width - 16))
    if column and ui_pos == 'gauche': return 'droite', int(max(260, width_px - col_width - 16))
    if column: return 'droite', int(max(260, (width_px - col_width) / 2 - 16))
    return 'droite', int(max(260, width_px - 20))


# ---- touche A pendant une attente de « toucher »
def touch_for_engine(p, decl, bit_a, bit_b, touch, is_waiting):
    """(p, decl) envoyes au moteur. `is_waiting` : un menu du jeu attend le toucher d'ecran (Engine.awaits_touch : le don d'experience du roi) ; `touch` : la valeur qu'il lit (exactement 0x100). A (touche, clic, Entree, Espace) envoie ce toucher
    seul, sans A ni B ; le reste du temps rien ne change. Un message ouvert recevrait sinon A (0x10), que ce menu ne lit pas : le jeu restait fige au dernier message de niveau (#261)."""
    if is_waiting and decl & bit_a: return p & ~(bit_a | bit_b), touch
    return p, decl
