"""Boutons tactiles de la version mobile, affiches a l'ecran hors combat : Carte, Commandes (menu), Discussion de groupe, et la croix (manette tactile, utilisable a la souris).
En combat, seul le bouton propre au portage « Vitesse de combat » (Manuel, Normal, Rapide, Tres rapide ; clic = vitesse suivante) est montre : pas de bouton equivalent dans le jeu mobile, il n'envoie rien au moteur.
Il est sur le bord gauche de l'ecran (case de la grille, depuis #188 ; DQ_VITESSE_ANCRE=1 le rattache au coin inferieur gauche de la boite du bas (commandes ou message), comme le bouton « Fuir » l'est au coin inferieur droit des commandes, c'etait le defaut de #47), et n'a pas de libelle : des fleches disent la vitesse
(triangle creux : Manuel ; un triangle : Normal ; deux : Rapide ; trois : Tres rapide). Un joueur qui le deplace dans l'editeur d'interface le garde a l'endroit choisi.

Le jeu d'origine les dessine dans la couche Unity (TouchPad : « Map Button » = touche 0x1000, « Command Button » = 0x800, « Talk Button » = 0x400 ; icones 3, 4 et 15 de la feuille
MenuTexture, rangee de 32 px a y = 224). Le moteur dit quand ils sont visibles par le mot Global.Flag (premier mot de sa sortie) : (Flag & (8 | 0x30047)) == 8 (pad present, ni verrou du
joueur, fondu, effet d'ecran, interface verrouillee ni pause) ; la Carte exige en plus le bit 0x20. Les positions se reglent sur une grille de 32 x 18 cases (aimantation facultative).

La croix est celle de TouchPad (feuille « Button » : anneau, huit pastilles de direction avec leur fleche, boule) ; dans le code d'origine l'anneau ne bouge pas (seule la boule suit le doigt) et il est toujours opaque. Sur PC
elle est fixe (en bas a droite par defaut, a deplacer dans l'editeur d'interface) : un appui dans sa zone de prise (1,178 rayon) la prend, la boule suit la souris (limitee a 0,4526 rayon), la direction est l'un des huit secteurs de
45 degres, comme les touches du clavier (elle suit donc la camera). Son diametre est une fois et demie celui du mobile (DPAD_DIAMETER ; le reglage « Taille de la croix » a 67 % redonne la taille d'origine). Tenue au BORD de l'anneau
(`dpad_run` : TRAVEL_THRESHOLD du rayon ou plus), elle fait courir le heros comme la touche d'accelerateur ; plus pres du centre il marche normalement. Le bouton « mode de la carte » n'est plus ici : c'est celui de la fenetre de la carte (type 22)."""
import math, os, time
import numpy as np
import pyglet
from pyglet import gl
from dq4_pc.language import tr, N_

COLS, LINES = 32, 18                       # grille de l'ecran (cases proportionnelles a la fenetre)
SPEED_ANCHOR_DEFAULT = False                 # bouton de vitesse de combat : False = a sa place de la grille, sur le bord gauche de l'ecran (defaut depuis #188 : « remets-le sur le bord gauche pour le moment ») ; True = rattache au coin bas gauche de la boite du bas (#47)

def speed_anchor():
    """Le bouton de vitesse de combat se rattache-t-il a la boite du bas ? Non par defaut (#188) : il reste sur le bord gauche de l'ecran, a la case de la grille (DEFAULT) ou la ou le joueur l'a place. Essai : variable d'environnement DQ_VITESSE_ANCRE=1 (rattache au coin bas gauche de la boite, #47) ou 0."""
    v = os.environ.get('DQ_VITESSE_ANCRE')
    if v is None or not v.strip(): return SPEED_ANCHOR_DEFAULT
    v = v.strip().lower()
    return True if v in ('1', 'oui', 'yes', 'true', 'vrai') else False if v in ('0', 'non', 'no', 'false', 'faux') else SPEED_ANCHOR_DEFAULT
NAMES = ('carte', 'menu', 'discussion')
DPAD = 'croix'
BATTLE = 'combat'                            # bouton « Vitesse de combat » (propre au portage) : montre en combat seulement, a la place des trois boutons du terrain
BUTTONS = NAMES + (BATTLE,)                   # tous les boutons rectangulaires
EDITOR_NAMES = BUTTONS + (DPAD,)                 # tous les elements places dans l'editeur d'interface
SCREEN_EDITOR_NAMES = NAMES + (DPAD,)              # interface « Boutons et croix de l'ecran » : Carte, Commandes, Discussion et la croix (le bouton de vitesse de combat a sa propre interface)
SPEED_EDITOR_NAMES = (BATTLE,)                  # interface « Combat : bouton de vitesse »


def editor_names(target):
    """Elements de l'editeur d'interface de la cible choisie (reglages.SCREEN_TARGET, reglages.SPEED_TARGET) ; vide pour une autre interface."""
    return SPEED_EDITOR_NAMES if target == 'bouton_vitesse' else SCREEN_EDITOR_NAMES if target == 'boutons' else ()

DEFAULT = {'carte': (0.4, 1), 'menu': (0.4, 12), 'discussion': (0.4, 14), BATTLE: (0.4, 8)}      # coin superieur gauche (colonne, ligne) : colonne de gauche (la croix est en bas a droite), Carte en haut, Commandes puis Discussion plus bas ; vitesse des combats entre les deux : a gauche des fenetres de combat (colonne portrait centree), elle n'en cache aucune
DECL = {'carte': 0x1000, 'menu': 0x800, 'discussion': 0x400}
ICON = {'carte': 3, 'menu': 4, 'discussion': 15}
CAPTION = {'carte': N_('Carte'), 'menu': N_('Commandes'), 'discussion': N_('Discussion'), BATTLE: N_('Vitesse de combat'), DPAD: N_('Croix')}            # (noms des elements dans l'editeur d'interface : traduits au dessin)
ICON_ROW = 224                           # ordonnee de la rangee d'icones dans la feuille (PartsInfo[3])
# Plaques des boutons (TouchPad.CreateMenuButton 0xD2377C : plaque (t x 40 + 32) x (t x 32 + 32) pour une taille t) en unites de l'interface d'origine (450 x 800) : (largeur, hauteur, cote de l'icone = 48 x taille d'icone)
DQ_PLATE = {'carte': (72.0, 64.0, 57.6), 'menu': (72.0, 64.0, 57.6), 'discussion': (63.0, 56.8, 48.0), BATTLE: (118.0, 60.0, 0.0)}      # (le bouton de vitesse des combats n'a pas d'icone : plaque plus large qui porte « Vitesse » et la vitesse courante)
PLATE_CORNER = 16.0                           # coins de la plaque 9 tranches (feuille « Button », partie 7), en unites d'interface

# ---- croix (TouchPad) : morceaux de la feuille « Button » (512 x 512), (x, y, largeur, hauteur) en pixels depuis le haut a gauche
DPAD_ART = {'anneau': (256, 256, 256, 256), 'pastille': (384, 192, 128, 64), 'pastille_on': (256, 192, 128, 64), 'boule': (448, 128, 64, 64), 'boule_on': (384, 128, 64, 64), 'halo': (320, 128, 64, 64)}      # (CurLight 384, 128 et CurBS 320, 128 : boule orange et halo du clignotement de la croix, TouchPad.SetPadBlink ; #131)
# Valeurs d'origine (TouchPad, libil2cpp.so, RVA ; audit de fidelite du 01/11/2026) : c_PadScaleTBL, MPad 256 x 0,63, Dirs a 104 unites du centre, c_MoveThreshold 10, c_moveNakaLimit 36,5, c_padColRad 95 pour un rayon de 80,64
DPAD_DIAMETER = 1.5 * 161.28                     # diametre de l'anneau en unites de l'interface d'origine (800 de haut : echelle H / 800) avant l'option du jeu et le reglage du portage : UNE FOIS ET DEMIE celui du mobile (256 x c_PadBaseScaleXY 0,63 = 161,28). Historique (04/11/2026) : le double (#169, 10 h 46 : la croix, petite sur un ecran de PC, se manie a la souris), puis « reduit la taille de la croix de 25 % par defaut » (11 h 30, #172) : 0,75 x 2 = 1,5 ; le reglage « Taille de la croix » (50 a 200 %) s'applique par-dessus
DPAD_SCALE = (1.225, 1.0, 0.775)           # option « Taille de la croix » du jeu (g_pad_size : 0 Grande, 1 Moyenne (defaut), 2 Petite) -> facteur (c_PadScaleTBL)
DOT_RADIUS = 104.0 / 256.0                # distance du centre de l'anneau au centre d'une pastille (fraction du diametre ; le quad de 128 x 64 va de 72 a 136 unites)
BALL_TRAVEL = 0.4526                         # deplacement maximal de la boule (fraction du rayon de l'anneau : 36,5 / 80,64)
DEAD_ZONE = 0.124                            # en dessous (fraction du rayon : 10 / 80,64), aucune direction
DPAD_WIDTH_MAX = 0.75                     # diametre maximal de la croix (fraction de la largeur de la fenetre) : au portrait 9:16 le double du mobile en prend 0,72 ; une fenetre plus etroite la reduit pour qu'elle tienne
TRAVEL_THRESHOLD = 0.9                            # course a la croix : le pointeur atteint le bord de l'anneau (fraction du rayon, 1 = le bord dessine ; la prise va jusqu'a 1,178) ; en dessous, le heros marche. Valeur choisie (suppose : « quand le joystick touche les bords »)
BLINK_PERIOD = 1.0                        # clignotement du rond central (secondes par cycle) : valeur choisie par le portage (les constantes du jeu, MOVE_WAIT_TIME / MOVE_LIMIT_ALPHA, sont inutilisees ; supposé)
DPAD_GRAB = 1.178                           # rayon de la zone de prise (fraction du rayon de l'anneau : collider de 95 / 80,64, un peu plus large que l'anneau dessine)

# ---- style des fenetres du jeu mobile (capture du menu des commandes) : fond bleu nuit translucide, cadre en cinq traits (gris, gris clair, blanc, gris, gris fonce), coins arrondis ;
# boutons = plaques grises a degrade (claires en haut, sombres en bas), bordure gris clair. Dessines en tableaux (distance au bord) puis gardes en textures : aucun cout par image.
DQ_BACKGROUND = (8, 16, 40); BACKGROUND_OPACITY = 0.82
GAME_OPACITY = 0.68                                                                                    # fond des fenetres du jeu : noir a 68 % d'opacite (mesure sur les fenetres du terrain, a travers lesquelles on voit le decor)
DQ_EDGES = ((138, 138, 138), (205, 205, 205), (255, 255, 255), (132, 132, 132), (41, 41, 41))       # traits du cadre de l'exterieur vers l'interieur
TOP_PLATE, BOTTOM_PLATE = (86, 87, 85), (34, 37, 31)                                                  # degrade du fond d'une plaque (haut -> bas)
_textures = {}


def _distance(w, h, r):
    """Distance signee (positive a l'interieur) de chaque pixel au bord d'un rectangle a coins arrondis w x h (rayon r), tableau (h, w)."""
    yy, xx = np.mgrid[0:h, 0:w]; xx = xx + 0.5; yy = yy + 0.5
    px = np.abs(xx - w / 2.0) - (w / 2.0 - r); py = np.abs(yy - h / 2.0) - (h / 2.0 - r)
    return -(np.hypot(np.maximum(px, 0.0), np.maximum(py, 0.0)) + np.minimum(np.maximum(px, py), 0.0) - r)


def _texture(a):
    h, w = a.shape[:2]
    t = pyglet.image.ImageData(w, h, 'RGBA', np.ascontiguousarray(np.clip(a, 0, 255).astype(np.uint8)[::-1]).tobytes(), pitch=w * 4).get_texture()
    gl.glBindTexture(t.target, t.id)
    gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    return t


def _keep(lookup_key, factory):
    t = _textures.get(lookup_key)
    if t is None:
        if len(_textures) > 80: _textures.clear()
        t = _textures[lookup_key] = factory()
    return t


def _restore_blend():
    """Melange alpha de la texture blittee : pyglet.shapes le coupe a la fin de chaque dessin, il faut le remettre avant un blit (sinon coins et fond translucide sortent opaques)."""
    gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)


def border(x, y, w, h, k, highlight=0.0, background=None, opacity=None):
    """Fenetre a la maniere des menus du jeu mobile : fond translucide (bleu nuit par defaut ; `background` et `opacity` : autre couleur), cadre en cinq traits de 1,25 px a 720 p, coins
    arrondis (transparents hors du cadre). `highlight` (0 a 1) : fond plus clair (bouton enfonce)."""
    w, h = int(round(w)), int(round(h))
    if w < 4 or h < 4: return
    background = DQ_BACKGROUND if background is None else tuple(background); opacity = BACKGROUND_OPACITY if opacity is None else opacity
    def fab():
        b = max(1.0, 1.25 * k); d = _distance(w, h, 9.0 * k); n = len(DQ_EDGES)
        a = np.zeros((h, w, 4), np.float32); ring = np.clip(np.floor(d / b), 0, n).astype(int)
        for i, c in enumerate(DQ_EDGES): a[ring == i, :3] = c
        a[ring == n, :3] = np.array(background, np.float32) * (1 - highlight) + 90.0 * highlight; a[..., 3] = 255.0
        a[ring == n, 3] = 255.0 * (opacity + (1 - opacity) * highlight)
        a[..., 3] *= np.clip(d + 0.5, 0.0, 1.0)
        return _texture(a)
    t = _keep(('cadre', w, h, round(k * 100), round(highlight * 10), background, round(opacity * 100)), fab)
    _restore_blend(); t.blit(int(round(x)), int(round(y)))


def plate(x, y, w, h, k, chosen=False, outline=None):
    """Fond d'un bouton comme ceux du menu des commandes du jeu : bordure gris clair, degrade gris, coins arrondis. Choisi : plus clair (comme un bouton du jeu enfonce), sans autre marque.
    `outline` (r, g, b) : encadrement de cette couleur, plus epais que la bordure (selection a la souris)."""
    w, h = int(round(w)), int(round(h))
    if w < 4 or h < 4: return
    def fab():
        d = _distance(w, h, 6.0 * k); bw = max(1.5, 1.6 * k) if outline is None else max(2.5, 2.8 * k); t = (np.mgrid[0:h, 0:w][0] + 0.5) / h      # t : 0 en haut, 1 en bas
        topmost, bottom = np.array(TOP_PLATE, np.float32), np.array(BOTTOM_PLATE, np.float32)
        a = np.zeros((h, w, 4), np.float32)
        background = topmost[None, None, :] * (1 - t[..., None]) + bottom[None, None, :] * t[..., None] + (26.0 if chosen else 0.0)
        c0, c1 = ((228, 230, 226), (150, 152, 147)) if chosen else ((186, 188, 185), (112, 114, 110))
        edge = np.array(c0, np.float32)[None, None, :] * (1 - t[..., None]) + np.array(c1, np.float32)[None, None, :] * t[..., None]
        if outline is not None: edge = np.zeros_like(edge) + np.array(outline, np.float32)
        inside = (d >= bw)[..., None]
        a[..., :3] = np.where(inside, background, edge); a[..., 3] = 255.0 * np.clip(d + 0.5, 0.0, 1.0)
        return _texture(a)
    t = _keep(('plaque', w, h, round(k * 100), bool(chosen), outline), fab)
    _restore_blend(); t.blit(int(round(x)), int(round(y)))


def outline(x, y, w, h, k, color, radius=6.0):
    """Encadrement (anneau de 2,8 px a 720 p, coins arrondis, interieur transparent) de la couleur donnee : selection a la souris d'un bouton."""
    w, h = int(round(w)), int(round(h))
    if w < 4 or h < 4: return
    def fab():
        d = _distance(w, h, radius * k); bw = max(2.5, 2.8 * k)
        a = np.zeros((h, w, 4), np.float32); a[..., :3] = np.array(color, np.float32)
        a[..., 3] = 255.0 * np.clip(d + 0.5, 0.0, 1.0) * (1.0 - np.clip(d - bw + 0.5, 0.0, 1.0))
        return _texture(a)
    t = _keep(('contour', w, h, round(k * 100), tuple(color)), fab)
    _restore_blend(); t.blit(int(round(x)), int(round(y)))


def draw_grid(W, H):
    """Grille de placement de l'ecran (COLS x LIGNES cases) : traits blancs translucides."""
    gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    for i in range(COLS + 1):
        l = pyglet.shapes.Line(i * W / COLS, 0, i * W / COLS, H, thickness=1, color=(255, 255, 255)); l.opacity = 38; l.draw()
    for j in range(LINES + 1):
        l = pyglet.shapes.Line(0, j * H / LINES, W, j * H / LINES, thickness=1, color=(255, 255, 255)); l.opacity = 38; l.draw()


def battle_visible(e):
    """Le bouton de vitesse des combats est-il montre ? Pas pendant l'ecran noir qui attend la scene du combat (State.load_wait), ni quand un fondu au noir monte ou que l'ecran est noir (debut et fin du combat) :
    comme les boutons du terrain, que le moteur cache pendant les fondus. Un fondu qui redescend (entree du combat) le laisse apparaitre."""
    if e.load_wait is not None: return False
    for p in (e.fade, e.background_fade):
        if p['a'] >= 0.999 or (p['n'] >= 1 and p['pas'] > 0): return False
    return True


class Buttons:
    def __init__(self, game):
        self.J = game; self.spr = {}; self.orig = {}; self.taken = None; self.press_state = None; self.editing = False; self.lookup_key = None
        self.taken_pose = None                  # (nom, decalage x, decalage y) pendant un deplacement
        self.dpad_on = False; self.dpad_dragging = False; self.cv = (0.0, 0.0); self.art = None      # croix tenue par la souris ; position de la souris relative au centre (rayon de l'anneau = 1) ; textures

    # ---- geometrie
    def scale_factor(self, name_str=None):
        """Pixels par unite de l'interface d'origine (800 de haut), reglage « Taille des boutons » compris (le bouton de vitesse de combat : sa propre taille)."""
        return self.J.height / 800.0 * float(self.J.reg['bouton_vitesse_taille' if name_str == BATTLE else 'boutons_taille'])

    def size_value(self):
        return DQ_PLATE['carte'][0] * self.scale_factor()

    def anchor(self):
        """Rattachement du bouton de vitesse de combat a la boite du bas (dict x, y, w, h en pixels, calcule par la fenetre : bord gauche et bord bas de la boite, taille de la plaque « Fuir »), ou None : hors combat, dans
        l'editeur, quand le joueur l'a place lui-meme, ou tant qu'aucune boite n'a ete vue (position de la grille)."""
        J = self.J; a = getattr(J, 'battle_anchor', None)
        if a is None or self.editing or J.reg['bouton_vitesse_pos'] or not speed_anchor(): return None
        from dq4_pc.core.engine import PART_BATTLE
        return a if J.engine.state.part == PART_BATTLE else None

    def _anchor_ready(self):
        """Le bouton de vitesse n'est montre que s'il a une place : celle que le joueur lui a donnee, ou, avec les menus d'origine, son ancre sous la boite du bas (calculee par la fenetre avant le dessin : jamais la position par defaut de la grille, qui est a gauche de l'ecran)."""
        J = self.J
        if not speed_anchor(): return True                                          # (#188) pas d'ancre : le bouton est a sa case de la grille, sur le bord gauche, des la premiere image
        return bool(J.reg['bouton_vitesse_pos']) or getattr(J, 'ui_msg', None) is None or getattr(J, 'battle_anchor', None) is not None

    def dims(self, name_str):
        """(largeur, hauteur) en pixels : plaque d'origine d'un bouton (72 x 64, 63 x 56,8...) ou diametre de l'anneau de la croix."""
        if name_str == DPAD: c = self.dpad_diameter(); return c, c
        if name_str == BATTLE:
            a = self.anchor(); t = float(self.J.reg['bouton_vitesse_taille'])
            if a and a.get('w'): return a['w'] * t, a['h'] * t       # meme plaque que « Fuir » (a la taille du reglage du bouton)
        w, h, _ = DQ_PLATE[name_str]; k = self.scale_factor(name_str); return w * k, h * k

    def dpad_diameter(self):
        """Diametre de l'anneau de la croix en pixels : echelle de l'interface d'origine, option « Taille de la croix » du jeu, reglage du portage."""
        d = self.J.height / 800.0 * DPAD_DIAMETER * DPAD_SCALE[self.J.engine.dpad_size()] * float(self.J.reg['croix_taille'])
        return min(d, DPAD_WIDTH_MAX * self.J.width)          # fenetre plus etroite que le portrait du mobile (9:16) : la croix doublee ne doit pas depasser de l'ecran

    def cell(self, name_str):
        p = self.J.reg['bouton_vitesse_pos'] if name_str == BATTLE else self.J.reg['boutons_pos'].get(name_str)
        if p and len(p) == 2: return tuple(p)
        if name_str == DPAD:                                   # d'origine : en bas a droite, a une demi-case du bord
            c = self.dpad_diameter(); return (COLS - c * COLS / self.J.width - 0.6, LINES - c * LINES / self.J.height - 0.6)
        return DEFAULT[name_str]

    def rect(self, name_str):
        """(x, y, largeur, hauteur) en pixels, origine en bas a gauche."""
        W, H = self.J.width, self.J.height; w, h = self.dims(name_str)
        if name_str == BATTLE:
            a = self.anchor()
            if a: return min(max(0.0, a['x']), W - w), min(max(0.0, a['y'] - h), H - h), w, h         # sous le coin inferieur gauche de la boite (le haut de la plaque touche son bord bas)
        col, lig = self.cell(name_str)
        x = min(max(0.0, col * W / COLS), W - w); y = min(max(0.0, H - lig * H / LINES - h), H - h)
        return x, y, w, h

    def under(self, x, y, visible_ones):
        if DPAD in visible_ones:
            rx, ry, c, _ = self.rect(DPAD)
            if math.hypot(x - rx - c / 2, y - ry - c / 2) <= c / 2 * DPAD_GRAB: return DPAD
        for name_str in reversed(BUTTONS):
            if name_str not in visible_ones: continue
            rx, ry, w, h = self.rect(name_str)
            if rx <= x <= rx + w and ry <= y <= ry + h: return name_str
        return None

    def visible_ones(self):
        """Boutons a montrer : ceux que le moteur autorise (hors menu Echap, combat, effets d'ecran) ; en combat, le seul bouton de vitesse des combats (hors ecran noir et fondu au noir)."""
        J = self.J
        if J.pause.opened or J.engine.state.effect is not None or getattr(J.engine.state, 'screen_effect', None) is not None: return ()
        from dq4_pc.core.engine import PART_BATTLE
        if J.engine.state.part == PART_BATTLE: return (BATTLE,) if J.reg['bouton_vitesse'] and battle_visible(J.engine.state) and self._anchor_ready() else ()        # (le bouton de vitesse a son propre reglage d'affichage)
        if not J.reg['boutons']: return ()
        if J.map_open: return ()                                                  # carte ouverte : plus de bouton a l'ecran (le bouton « mode » et le retour sont ceux de la fenetre de la carte, type 22)
        f = J.engine.flags()
        if (f & (8 | 0x30047)) != 8: return ()
        return tuple(n for n in NAMES if n != 'carte' or f & 0x20) + ((DPAD,) if J.reg['croix'] else ())

    def allowed(self, name_str):
        """Le moteur autorise-t-il ce bouton du terrain (Carte, Commandes, Discussion) en ce moment, que le reglage « boutons » l'affiche ou non ? Le clavier y joue le bruitage du bouton (D-156 : les mêmes situations qu'au doigt)."""
        J = self.J
        from dq4_pc.core.engine import PART_BATTLE
        if J.pause.opened or J.engine.state.effect is not None or getattr(J.engine.state, 'screen_effect', None) is not None or J.engine.state.part == PART_BATTLE or J.map_open: return False
        f = J.engine.flags()
        return (f & (8 | 0x30047)) == 8 and (name_str != 'carte' or bool(f & 0x20))

    # ---- souris
    def press(self, x, y, visible_ones):
        n = self.under(x, y, visible_ones)
        if n == DPAD: self.dpad_on = True; self.dpad_dragging = False; self.dpad_drag(x, y)
        elif n: self.press_state = n
        return n

    def let_go(self, x, y, visible_ones):
        """-> nom du bouton (clic complet : relachement sur le bouton appuye) ou None."""
        n, self.press_state = self.press_state, None
        return n if n and self.under(x, y, visible_ones) == n else None

    # ---- edition des positions
    def take(self, x, y, names=EDITOR_NAMES):
        n = self.under(x, y, names)
        if n: rx, ry = self.rect(n)[:2]; self.taken = (n, x - rx, y - ry)
        return n

    def move_to(self, x, y):
        if not self.taken: return
        n, dx, dy = self.taken; W, H = self.J.width, self.J.height; w, h = self.dims(n)
        px = min(max(0.0, x - dx), W - w); py = min(max(0.0, y - dy), H - h)         # coin inferieur gauche demande
        col = px * COLS / W; lig = (H - py - h) * LINES / H
        if self.J.reg['boutons_aimant']: col, lig = float(round(col)), float(round(lig))
        else: col, lig = round(col, 2), round(lig, 2)
        col = min(max(0.0, col), COLS - w * COLS / W); lig = min(max(0.0, lig), LINES - h * LINES / H)
        if n == BATTLE: self.J.reg['bouton_vitesse_pos'] = [col, lig]; return
        pos = dict(self.J.reg['boutons_pos']); pos[n] = [col, lig]; self.J.reg['boutons_pos'] = pos

    def place(self): self.taken = None

    # ---- croix a la souris
    def dpad_drag(self, x, y):
        """Souris deplacee (ou appuyee) : position relative au centre de l'anneau, en rayons."""
        rx, ry, c, _ = self.rect(DPAD); r = c / 2
        self.cv = ((x - rx - r) / r, (y - ry - r) / r)
        if math.hypot(*self.cv) >= DEAD_ZONE: self.dpad_dragging = True            # sorti du rond central : c'est un glissement (une direction), plus un toucher

    def dpad_drop(self):
        self.dpad_on = False; self.dpad_dragging = False; self.cv = (0.0, 0.0)

    def dpad_release(self):
        """Bouton de la souris relache sur la croix. -> True si c'etait un TOUCHER du rond central : appuye puis relache sans jamais en sortir (sans glissement) ; le jeu y voit la touche d'action (comme la touche A)."""
        tap = self.dpad_on and not self.dpad_dragging
        self.dpad_drop()
        return tap

    def dpad_sector(self):
        """Secteur de 45 degres de la direction tenue (0 haut, 1 haut-droite, 2 droite... dans le sens horaire) ou None (zone morte, croix non tenue)."""
        if not self.dpad_on: return None
        vx, vy = self.cv
        if math.hypot(vx, vy) < DEAD_ZONE: return None
        return int(((math.degrees(math.atan2(vx, vy)) + 22.5) % 360.0) // 45.0)

    def dpad_run(self):
        """La croix est-elle tenue au BORD de l'anneau (a TRAVEL_THRESHOLD du rayon ou plus, dans une direction) ? Le heros court alors (comme avec la touche d'accelerateur) ; plus pres du centre, il marche normalement."""
        return self.dpad_on and self.dpad_sector() is not None and math.hypot(*self.cv) >= TRAVEL_THRESHOLD

    def dpad_bits(self):
        """Direction de la croix en bits de la manette du jeu (haut / bas / gauche / droite), comme celle des touches de deplacement."""
        if self.dpad_on and DPAD not in self.visible_ones(): self.dpad_drop(); return 0
        k = self.dpad_sector()
        if k is None: return 0
        from dq4_pc.core import engine as ENGINE
        return (ENGINE.UP, ENGINE.UP | ENGINE.RIGHT, ENGINE.RIGHT, ENGINE.DOWN | ENGINE.RIGHT, ENGINE.DOWN, ENGINE.DOWN | ENGINE.LEFT, ENGINE.LEFT, ENGINE.UP | ENGINE.LEFT)[k]

    # ---- dessin
    def _icon(self, name_str):
        """Icone d'origine 32 x 32 (RGBA), couleur des pixels transparents propagee d'un pixel (pas de liseré sombre quand le filtre melange les bords)."""
        a = self.orig.get(name_str)
        if a is None:
            from PIL import Image
            from dq4_pc.world import hd as HD
            f = os.path.join(self.J.args.cache, 'ui_MenuTexture.png')
            try: im = Image.open(f).convert('RGBA'); n = ICON[name_str]; a = np.array(im.crop((n * 32, ICON_ROW, n * 32 + 32, ICON_ROW + 32)))
            except Exception: a = np.zeros((32, 32, 4), np.uint8); a[..., 3] = 120
            a = self.orig[name_str] = HD._dilate(a, 1)
        return a

    def _sprite(self, name_str, c):
        """Sprite de l'icone pour un bouton de c pixels de cote. L'icone est d'abord agrandie par un entier n (plus proche voisin : chaque pixel d'origine devient un bloc net), puis
        reduite au pixels exacts par le filtre lineaire : les pixels restent francs, seule la frontiere entre deux pixels est adoucie (un agrandissement lineaire direct de 32 a 72 px les ecrasait)."""
        n = max(1, int(np.ceil(c / 32.0 - 1e-6)))
        s = self.spr.get((name_str, n))
        if s is None:
            a = np.repeat(np.repeat(self._icon(name_str), n, axis=0), n, axis=1); t_ = 32 * n
            img = pyglet.image.ImageData(t_, t_, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=t_ * 4)
            t = img.get_texture(); gl.glBindTexture(t.target, t.id)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            s = self.spr[(name_str, n)] = pyglet.sprite.Sprite(t)
        return s, n

    def _plate(self, x, y, w, h, pressed, name_str=None):
        """Plaque d'origine du bouton (feuille « Button », partie 7, 9 tranches a coins de 16 unites, image « appuyee » quand le bouton est enfonce), comme les boutons des fenetres du jeu : Render.plaque.
        -> False sans les menus d'origine (le repli dessine le fond)."""
        r = getattr(self.J, 'ui_render', None)
        return bool(r is not None and r.plate(x, y, w, h, (self.J.width, self.J.height), pressed, corner=PLATE_CORNER * self.scale_factor(name_str)))

    def _battle_arrows(self, x, y, w, h):
        """Vitesse de combat en fleches, sans libelle : un triangle creux (gris) en Manuel, puis un, deux ou trois triangles pleins (Normal : blanc ; Rapide : jaune ; Tres rapide : orange, plus chaud quand ca accelere), comme le
        curseur triangulaire des menus du jeu. Groupe centre dans la plaque."""
        from dq4_pc.persistence import settings as RG
        v = RG.battle_notch(self.J.reg['vitesse_combat'])
        num = {0.0: 1, 1.0: 1, 2.0: 2, 3.0: 3}[v]; clr = {0.0: (170, 174, 182), 1.0: (255, 255, 255), 2.0: (255, 235, 130), 3.0: (255, 176, 80)}[v]
        th = h * 0.42; tw = th * 0.80; ec = tw * 0.22; total = num * tw + (num - 1) * ec           # hauteur et largeur d'un triangle, ecart entre deux
        x0 = x + (w - total) / 2.0; yc = y + h / 2.0
        for i in range(num):
            a = x0 + i * (tw + ec)
            vertices = (a, yc - th / 2, a, yc + th / 2, a + tw, yc)
            if v == 0.0:                                                                         # Manuel : triangle creux
                e = max(2.0, h * 0.045)
                pyglet.shapes.Polygon((vertices[0], vertices[1]), (vertices[2], vertices[3]), (vertices[4], vertices[5]), color=clr).draw()
                d = e * 2.1; pyglet.shapes.Polygon((a + d * 0.55, yc - th / 2 + d), (a + d * 0.55, yc + th / 2 - d), (a + tw - d * 1.1, yc), color=BOTTOM_PLATE).draw()
            else: pyglet.shapes.Triangle(*vertices, color=clr).draw()

    def _dpad_art(self):
        """Sprites de la croix (morceaux de la feuille « Button », ancres au centre pour tourner autour)."""
        if self.art is None:
            from PIL import Image
            from dq4_pc.world import hd as HD
            try: im = np.array(Image.open(os.path.join(self.J.args.cache, 'ui_Button.png')).convert('RGBA'))
            except Exception: im = np.zeros((512, 512, 4), np.uint8)
            self.art = {}
            for name_str, (x, y, w, h) in DPAD_ART.items():
                a = HD._dilate(im[y:y + h, x:x + w].copy(), 1)
                t = pyglet.image.ImageData(w, h, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=w * 4).get_texture()
                gl.glBindTexture(t.target, t.id)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                t.anchor_x = w / 2.0; t.anchor_y = h / 2.0
                self.art[name_str] = pyglet.sprite.Sprite(t)
        return self.art

    def action_possible(self):
        """Une action est-elle realisable maintenant ? (#131 : la croix s'anime alors, comme sur mobile.) Oui quand le jeu fait clignoter le rond central (paquet 19, TouchPad.SetPadBlink, tutoriel) ; sinon, sur le terrain
        libre, quand une bulle d'icone est affichee (le jeu pose la bulle sur la cible que le heros peut parler, fouiller ou ouvrir : supposé, le jeu d'origine ne lie le clignotement de la croix qu'a son tutoriel)."""
        e = self.J.engine.state
        if getattr(e, 'pad_blink', False): return True
        free = getattr(self.J, '_terrain_free', None)
        if free is not None and not free(): return False
        return any(ic.get('pos') is not None and ic.get('alpha', 0.0) > 0.02 for ic in getattr(e, 'icons', {}).values())

    def _dpad(self, editing=False):
        """Croix : anneau, huit pastilles (celle de la direction tenue s'allume), boule qui suit la souris. Toujours opaque ; la boule orange et son halo (SetVisibleColMove) pulsent quand une action est possible
        (voir action_possible) ; MOVE_WAIT_TIME / MOVE_LIMIT_ALPHA sont des constantes inutilisees."""
        art = self._dpad_art(); x, y, c, _ = self.rect(DPAD); cx, cy = x + c / 2, y + c / 2; k = c / 256.0
        sect = self.dpad_sector()
        a = 1.0                                                                            # (masquee, elle reste entiere dans l'editeur : le voile « Masquée » de pause.py l'assombrit comme les autres elements)
        def place(name_str, px, py, rot=0.0, op=1.0):
            sp = art[name_str]; sp.update(x=px, y=py, scale=k, rotation=rot); sp.opacity = int(255 * a * op); sp.draw()
        place('anneau', cx, cy)
        for i in range(8):
            ang = i * 45.0; r = DOT_RADIUS * c
            place('pastille_on' if sect == i else 'pastille', cx + math.sin(math.radians(ang)) * r, cy + math.cos(math.radians(ang)) * r, ang)
        vx, vy = self.cv if self.dpad_on else (0.0, 0.0); n = math.hypot(vx, vy)
        if n > BALL_TRAVEL: vx, vy = vx * BALL_TRAVEL / n, vy * BALL_TRAVEL / n
        bx, by = cx + vx * c / 2, cy + vy * c / 2
        if self.dpad_on and (not self.dpad_dragging or self.dpad_run()): place('halo', bx, by); place('boule_on', bx, by)                 # toucher en cours, ou course (pointeur au bord de l'anneau) : boule eclairee
        elif self.action_possible() and not editing:                                                                  # une action est possible (bulle affichee) ou le jeu fait clignoter le rond central : la boule orange et son halo apparaissent et disparaissent doucement
            ph = 0.5 - 0.5 * math.cos(2.0 * math.pi * (time.perf_counter() % BLINK_PERIOD) / BLINK_PERIOD)
            place('boule', bx, by); place('halo', bx, by, 0.0, ph); place('boule_on', bx, by, 0.0, ph)
        else: place('boule', bx, by)

    def draw_all(self, visible_ones, editing=False, grid=True):
        if not visible_ones and not editing: return
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        W, H = self.J.width, self.J.height
        if editing:                                              # voile sombre et grille (facultative)
            background = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); background.opacity = 110; background.draw()
            if grid: draw_grid(W, H)
        for name_str in BUTTONS:
            if name_str not in visible_ones: continue
            x, y, w, h = self.rect(name_str); active = self.press_state == name_str or (self.taken is not None and self.taken[0] == name_str)
            if name_str == BATTLE:                                    # comme la plaque « Fuir » : un petit cadre de fenetre du jeu (fond noir translucide, cadre en cinq traits) qui porte la plaque du bouton
                k = h / 56.0; border(x, y, w, h, k, 0.0, (0, 0, 0), GAME_OPACITY); m = 5.0 * k
                actual = self._plate(x + m, y + m, w - 2 * m, h - 2 * m, active, name_str)
                if not actual: border(x + m, y + m, w - 2 * m, h - 2 * m, k, 0.45 if active else 0.0)
            else:
                actual = self._plate(x, y, w, h, active)
                if not actual: border(x, y, w, h, h / 60.0, 0.45 if active else 0.0)    # sans les menus d'origine : fond de bouton dessine (fenetre bleu nuit a cadre blanc, comme celles du jeu mobile)
            if name_str == BATTLE: self._battle_arrows(x, y, w, h)
            else:
                ci = DQ_PLATE[name_str][2] * self.scale_factor(); s, n = self._sprite(name_str, ci)
                s.update(x=x + (w - ci) / 2, y=y + (h - ci) / 2, scale=ci / (32.0 * n))
                s.color = (170, 170, 170) if active and not actual else (255, 255, 255); s.opacity = 255 if editing else 235
                s.draw()
            if editing:
                pyglet.shapes.Box(x, y, w, h, thickness=2, color=(255, 235, 130)).draw()
                label = self.J._lbl(tr(CAPTION[name_str]), max(11.0, h / 5.0), (255, 235, 130, 255)); label.x = min(max(4.0, x + w / 2 - label.content_width / 2), W - label.content_width - 4); label.y = min(y + h + 4, H - label.content_height - 2); label.draw()
        if DPAD in visible_ones:
            self._dpad(editing)
            if editing:
                x, y, c, _ = self.rect(DPAD); active = self.taken is not None and self.taken[0] == DPAD
                pyglet.shapes.Box(x, y, c, c, thickness=2, color=(255, 235, 130)).draw()
                label = self.J._lbl(tr(CAPTION[DPAD]), max(11.0, self.size_value() / 5.0), (255, 235, 130, 255)); label.x = min(max(4.0, x + c / 2 - label.content_width / 2), W - label.content_width - 4); label.y = min(y + c + 4, H - label.content_height - 2); label.draw()
