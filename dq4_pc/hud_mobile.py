"""Boutons tactiles de la version mobile, affiches a l'ecran hors combat : Carte, Commandes (menu), Discussion de groupe, et la croix (manette tactile, utilisable a la souris).
En combat, seul le bouton propre au portage « Vitesse des combats » (Normal, Rapide, Tres rapide ; clic = vitesse suivante) est montre : pas de bouton equivalent dans le jeu mobile, il n'envoie rien au moteur.

Le jeu d'origine les dessine dans la couche Unity (TouchPad : « Map Button » = touche 0x1000, « Command Button » = 0x800, « Talk Button » = 0x400 ; icones 3, 4 et 15 de la feuille
MenuTexture, rangee de 32 px a y = 224). Le moteur dit quand ils sont visibles par le mot Global.Flag (premier mot de sa sortie) : (Flag & (8 | 0x30047)) == 8 (pad present, ni verrou du
joueur, fondu, effet d'ecran, interface verrouillee ni pause) ; la Carte exige en plus le bit 0x20. Les positions se reglent sur une grille de 32 x 18 cases (aimantation facultative).

La croix est celle de TouchPad (feuille « Button » : anneau, huit pastilles de direction avec leur fleche, boule) ; dans le code d'origine l'anneau ne bouge pas (seule la boule suit le doigt) et il est toujours opaque. Sur PC
elle est fixe (en bas a droite par defaut, a deplacer dans l'editeur d'interface) : un appui dans sa zone de prise (1,178 rayon) la prend, la boule suit la souris (limitee a 0,4526 rayon), la direction est l'un des huit secteurs de
45 degres, comme les touches du clavier (elle suit donc la camera). Le bouton « mode de la carte » n'est plus ici : c'est celui de la fenetre de la carte (type 22)."""
import math, os
import numpy as np
import pyglet
from pyglet import gl

COLS, LIGNES = 32, 18                       # grille de l'ecran (cases proportionnelles a la fenetre)
NOMS = ('carte', 'menu', 'discussion')
CROIX = 'croix'
COMBAT = 'combat'                            # bouton « Vitesse des combats » (propre au portage) : montre en combat seulement, a la place des trois boutons du terrain
BOUTONS = NOMS + (COMBAT,)                   # tous les boutons rectangulaires
NOMS_ED = BOUTONS + (CROIX,)                 # elements places dans l'editeur d'interface
DEFAUT = {'carte': (0.4, 1), 'menu': (0.4, 12), 'discussion': (0.4, 14), COMBAT: (0.4, 8)}      # coin superieur gauche (colonne, ligne) : colonne de gauche (la croix est en bas a droite), Carte en haut, Commandes puis Discussion plus bas ; vitesse des combats entre les deux : a gauche des fenetres de combat (colonne portrait centree), elle n'en cache aucune
DECL = {'carte': 0x1000, 'menu': 0x800, 'discussion': 0x400}
ICONE = {'carte': 3, 'menu': 4, 'discussion': 15}
LIBELLE = {'carte': 'Carte', 'menu': 'Commandes', 'discussion': 'Discussion', COMBAT: 'Vitesse des combats', CROIX: 'Croix'}
LIGNE_ICONES = 224                           # ordonnee de la rangee d'icones dans la feuille (PartsInfo[3])
# Plaques des boutons (TouchPad.CreateMenuButton 0xD2377C : plaque (t x 40 + 32) x (t x 32 + 32) pour une taille t) en unites de l'interface d'origine (450 x 800) : (largeur, hauteur, cote de l'icone = 48 x taille d'icone)
PLAQUE_DQ = {'carte': (72.0, 64.0, 57.6), 'menu': (72.0, 64.0, 57.6), 'discussion': (63.0, 56.8, 48.0), COMBAT: (118.0, 60.0, 0.0)}      # (le bouton de vitesse des combats n'a pas d'icone : plaque plus large qui porte « Vitesse » et la vitesse courante)
COIN_PLAQUE = 16.0                           # coins de la plaque 9 tranches (feuille « Button », partie 7), en unites d'interface

# ---- croix (TouchPad) : morceaux de la feuille « Button » (512 x 512), (x, y, largeur, hauteur) en pixels depuis le haut a gauche
ART_CROIX = {'anneau': (256, 256, 256, 256), 'pastille': (384, 192, 128, 64), 'pastille_on': (256, 192, 128, 64), 'boule': (448, 128, 64, 64)}      # (CurLight 384, 128 et CurBS 320, 128 : boule orange et halo du clignotement du tutoriel, inexistant sur PC)
# Valeurs d'origine (TouchPad, libil2cpp.so, RVA ; audit de fidelite du 01/11/2026) : c_PadScaleTBL, MPad 256 x 0,63, Dirs a 104 unites du centre, c_MoveThreshold 10, c_moveNakaLimit 36,5, c_padColRad 95 pour un rayon de 80,64
DIAM_CROIX = 161.28                           # diametre de l'anneau (256 x c_PadBaseScaleXY 0,63 ; unites de l'interface d'origine, 800 de haut : echelle H / 800) avant l'option du jeu et le reglage du portage
ECHELLE_CROIX = (1.225, 1.0, 0.775)           # option « Taille de la croix » du jeu (g_pad_size : 0 Grande, 1 Moyenne (defaut), 2 Petite) -> facteur (c_PadScaleTBL)
RAYON_PASTILLE = 104.0 / 256.0                # distance du centre de l'anneau au centre d'une pastille (fraction du diametre ; le quad de 128 x 64 va de 72 a 136 unites)
COURSE_BOULE = 0.4526                         # deplacement maximal de la boule (fraction du rayon de l'anneau : 36,5 / 80,64)
ZONE_MORTE = 0.124                            # en dessous (fraction du rayon : 10 / 80,64), aucune direction
PRISE_CROIX = 1.178                           # rayon de la zone de prise (fraction du rayon de l'anneau : collider de 95 / 80,64, un peu plus large que l'anneau dessine)

# ---- style des fenetres du jeu mobile (capture du menu des commandes) : fond bleu nuit translucide, cadre en cinq traits (gris, gris clair, blanc, gris, gris fonce), coins arrondis ;
# boutons = plaques grises a degrade (claires en haut, sombres en bas), bordure gris clair. Dessines en tableaux (distance au bord) puis gardes en textures : aucun cout par image.
FOND_DQ = (8, 16, 40); OPACITE_FOND = 0.82
OPACITE_JEU = 0.68                                                                                    # fond des fenetres du jeu : noir a 68 % d'opacite (mesure sur les fenetres du terrain, a travers lesquelles on voit le decor)
BORDS_DQ = ((138, 138, 138), (205, 205, 205), (255, 255, 255), (132, 132, 132), (41, 41, 41))       # traits du cadre de l'exterieur vers l'interieur
PLAQUE_HAUT, PLAQUE_BAS = (86, 87, 85), (34, 37, 31)                                                  # degrade du fond d'une plaque (haut -> bas)
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


def _garder(cle, fabrique):
    t = _textures.get(cle)
    if t is None:
        if len(_textures) > 80: _textures.clear()
        t = _textures[cle] = fabrique()
    return t


def _melange():
    """Melange alpha de la texture blittee : pyglet.shapes le coupe a la fin de chaque dessin, il faut le remettre avant un blit (sinon coins et fond translucide sortent opaques)."""
    gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)


def cadre(x, y, w, h, k, eclaire=0.0, fond=None, opacite=None):
    """Fenetre a la maniere des menus du jeu mobile : fond translucide (bleu nuit par defaut ; `fond` et `opacite` : autre couleur), cadre en cinq traits de 1,25 px a 720 p, coins
    arrondis (transparents hors du cadre). `eclaire` (0 a 1) : fond plus clair (bouton enfonce)."""
    w, h = int(round(w)), int(round(h))
    if w < 4 or h < 4: return
    fond = FOND_DQ if fond is None else tuple(fond); opacite = OPACITE_FOND if opacite is None else opacite
    def fab():
        b = max(1.0, 1.25 * k); d = _distance(w, h, 9.0 * k); n = len(BORDS_DQ)
        a = np.zeros((h, w, 4), np.float32); ring = np.clip(np.floor(d / b), 0, n).astype(int)
        for i, c in enumerate(BORDS_DQ): a[ring == i, :3] = c
        a[ring == n, :3] = np.array(fond, np.float32) * (1 - eclaire) + 90.0 * eclaire; a[..., 3] = 255.0
        a[ring == n, 3] = 255.0 * (opacite + (1 - opacite) * eclaire)
        a[..., 3] *= np.clip(d + 0.5, 0.0, 1.0)
        return _texture(a)
    t = _garder(('cadre', w, h, round(k * 100), round(eclaire * 10), fond, round(opacite * 100)), fab)
    _melange(); t.blit(int(round(x)), int(round(y)))


def plaque(x, y, w, h, k, choisi=False, contour=None):
    """Fond d'un bouton comme ceux du menu des commandes du jeu : bordure gris clair, degrade gris, coins arrondis. Choisi : plus clair (comme un bouton du jeu enfonce), sans autre marque.
    `contour` (r, g, b) : encadrement de cette couleur, plus epais que la bordure (selection a la souris)."""
    w, h = int(round(w)), int(round(h))
    if w < 4 or h < 4: return
    def fab():
        d = _distance(w, h, 6.0 * k); bw = max(1.5, 1.6 * k) if contour is None else max(2.5, 2.8 * k); t = (np.mgrid[0:h, 0:w][0] + 0.5) / h      # t : 0 en haut, 1 en bas
        haut, bas = np.array(PLAQUE_HAUT, np.float32), np.array(PLAQUE_BAS, np.float32)
        a = np.zeros((h, w, 4), np.float32)
        fond = haut[None, None, :] * (1 - t[..., None]) + bas[None, None, :] * t[..., None] + (26.0 if choisi else 0.0)
        c0, c1 = ((228, 230, 226), (150, 152, 147)) if choisi else ((186, 188, 185), (112, 114, 110))
        bord = np.array(c0, np.float32)[None, None, :] * (1 - t[..., None]) + np.array(c1, np.float32)[None, None, :] * t[..., None]
        if contour is not None: bord = np.zeros_like(bord) + np.array(contour, np.float32)
        dedans = (d >= bw)[..., None]
        a[..., :3] = np.where(dedans, fond, bord); a[..., 3] = 255.0 * np.clip(d + 0.5, 0.0, 1.0)
        return _texture(a)
    t = _garder(('plaque', w, h, round(k * 100), bool(choisi), contour), fab)
    _melange(); t.blit(int(round(x)), int(round(y)))


def contour(x, y, w, h, k, couleur, rayon=6.0):
    """Encadrement (anneau de 2,8 px a 720 p, coins arrondis, interieur transparent) de la couleur donnee : selection a la souris d'un bouton."""
    w, h = int(round(w)), int(round(h))
    if w < 4 or h < 4: return
    def fab():
        d = _distance(w, h, rayon * k); bw = max(2.5, 2.8 * k)
        a = np.zeros((h, w, 4), np.float32); a[..., :3] = np.array(couleur, np.float32)
        a[..., 3] = 255.0 * np.clip(d + 0.5, 0.0, 1.0) * (1.0 - np.clip(d - bw + 0.5, 0.0, 1.0))
        return _texture(a)
    t = _garder(('contour', w, h, round(k * 100), tuple(couleur)), fab)
    _melange(); t.blit(int(round(x)), int(round(y)))


def tracer_grille(W, H):
    """Grille de placement de l'ecran (COLS x LIGNES cases) : traits blancs translucides."""
    gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    for i in range(COLS + 1):
        l = pyglet.shapes.Line(i * W / COLS, 0, i * W / COLS, H, thickness=1, color=(255, 255, 255)); l.opacity = 38; l.draw()
    for j in range(LIGNES + 1):
        l = pyglet.shapes.Line(0, j * H / LIGNES, W, j * H / LIGNES, thickness=1, color=(255, 255, 255)); l.opacity = 38; l.draw()


def combat_visible(e):
    """Le bouton de vitesse des combats est-il montre ? Pas pendant l'ecran noir qui attend la scene du combat (Etat.attente_charge), ni quand un fondu au noir monte ou que l'ecran est noir (debut et fin du combat) :
    comme les boutons du terrain, que le moteur cache pendant les fondus. Un fondu qui redescend (entree du combat) le laisse apparaitre."""
    if e.attente_charge is not None: return False
    for p in (e.fondu, e.fondu_fond):
        if p['a'] >= 0.999 or (p['n'] >= 1 and p['pas'] > 0): return False
    return True


class Boutons:
    def __init__(self, jeu):
        self.J = jeu; self.spr = {}; self.orig = {}; self.pris = None; self.appui = None; self.edition = False; self.cle = None
        self.pose_prise = None                  # (nom, decalage x, decalage y) pendant un deplacement
        self.croix_on = False; self.cv = (0.0, 0.0); self.art = None      # croix tenue par la souris ; position de la souris relative au centre (rayon de l'anneau = 1) ; textures

    # ---- geometrie
    def echelle(self):
        """Pixels par unite de l'interface d'origine (800 de haut), reglage « Taille des boutons » compris."""
        return self.J.height / 800.0 * float(self.J.reg['boutons_taille'])

    def taille(self):
        return PLAQUE_DQ['carte'][0] * self.echelle()

    def dims(self, nom):
        """(largeur, hauteur) en pixels : plaque d'origine d'un bouton (72 x 64, 63 x 56,8...) ou diametre de l'anneau de la croix."""
        if nom == CROIX: c = self.diametre_croix(); return c, c
        w, h, _ = PLAQUE_DQ[nom]; k = self.echelle(); return w * k, h * k

    def diametre_croix(self):
        """Diametre de l'anneau de la croix en pixels : echelle de l'interface d'origine, option « Taille de la croix » du jeu, reglage du portage."""
        return self.J.height / 800.0 * DIAM_CROIX * ECHELLE_CROIX[self.J.moteur.taille_croix()] * float(self.J.reg['croix_taille'])

    def case(self, nom):
        p = self.J.reg['boutons_pos'].get(nom)
        if p and len(p) == 2: return tuple(p)
        if nom == CROIX:                                   # d'origine : en bas a droite, a une demi-case du bord
            c = self.diametre_croix(); return (COLS - c * COLS / self.J.width - 0.6, LIGNES - c * LIGNES / self.J.height - 0.6)
        return DEFAUT[nom]

    def rect(self, nom):
        """(x, y, largeur, hauteur) en pixels, origine en bas a gauche."""
        W, H = self.J.width, self.J.height; w, h = self.dims(nom); col, lig = self.case(nom)
        x = min(max(0.0, col * W / COLS), W - w); y = min(max(0.0, H - lig * H / LIGNES - h), H - h)
        return x, y, w, h

    def sous(self, x, y, visibles):
        if CROIX in visibles:
            rx, ry, c, _ = self.rect(CROIX)
            if math.hypot(x - rx - c / 2, y - ry - c / 2) <= c / 2 * PRISE_CROIX: return CROIX
        for nom in reversed(BOUTONS):
            if nom not in visibles: continue
            rx, ry, w, h = self.rect(nom)
            if rx <= x <= rx + w and ry <= y <= ry + h: return nom
        return None

    def visibles(self):
        """Boutons a montrer : ceux que le moteur autorise (hors menu Echap, combat, effets d'ecran) ; en combat, le seul bouton de vitesse des combats (hors ecran noir et fondu au noir)."""
        J = self.J
        if not J.reg['boutons'] or J.pause.ouvert or J.moteur.etat.effet is not None: return ()
        from moteur import PARTIE_COMBAT
        if J.moteur.etat.partie == PARTIE_COMBAT: return (COMBAT,) if combat_visible(J.moteur.etat) else ()
        if J.carte_ouverte: return ()                                                  # carte ouverte : plus de bouton a l'ecran (le bouton « mode » et le retour sont ceux de la fenetre de la carte, type 22)
        f = J.moteur.drapeaux()
        if (f & (8 | 0x30047)) != 8: return ()
        return tuple(n for n in NOMS if n != 'carte' or f & 0x20) + ((CROIX,) if J.reg['croix'] else ())

    # ---- souris
    def appuyer(self, x, y, visibles):
        n = self.sous(x, y, visibles)
        if n == CROIX: self.croix_on = True; self.croix_glisser(x, y)
        elif n: self.appui = n
        return n

    def relacher(self, x, y, visibles):
        """-> nom du bouton (clic complet : relachement sur le bouton appuye) ou None."""
        n, self.appui = self.appui, None
        return n if n and self.sous(x, y, visibles) == n else None

    # ---- edition des positions
    def prendre(self, x, y):
        n = self.sous(x, y, NOMS_ED)
        if n: rx, ry = self.rect(n)[:2]; self.pris = (n, x - rx, y - ry)
        return n

    def deplacer(self, x, y):
        if not self.pris: return
        n, dx, dy = self.pris; W, H = self.J.width, self.J.height; w, h = self.dims(n)
        px = min(max(0.0, x - dx), W - w); py = min(max(0.0, y - dy), H - h)         # coin inferieur gauche demande
        col = px * COLS / W; lig = (H - py - h) * LIGNES / H
        if self.J.reg['boutons_aimant']: col, lig = float(round(col)), float(round(lig))
        else: col, lig = round(col, 2), round(lig, 2)
        col = min(max(0.0, col), COLS - w * COLS / W); lig = min(max(0.0, lig), LIGNES - h * LIGNES / H)
        pos = dict(self.J.reg['boutons_pos']); pos[n] = [col, lig]; self.J.reg['boutons_pos'] = pos

    def poser(self): self.pris = None

    # ---- croix a la souris
    def croix_glisser(self, x, y):
        """Souris deplacee (ou appuyee) : position relative au centre de l'anneau, en rayons."""
        rx, ry, c, _ = self.rect(CROIX); r = c / 2
        self.cv = ((x - rx - r) / r, (y - ry - r) / r)

    def croix_lacher(self):
        self.croix_on = False; self.cv = (0.0, 0.0)

    def croix_secteur(self):
        """Secteur de 45 degres de la direction tenue (0 haut, 1 haut-droite, 2 droite... dans le sens horaire) ou None (zone morte, croix non tenue)."""
        if not self.croix_on: return None
        vx, vy = self.cv
        if math.hypot(vx, vy) < ZONE_MORTE: return None
        return int(((math.degrees(math.atan2(vx, vy)) + 22.5) % 360.0) // 45.0)

    def croix_bits(self):
        """Direction de la croix en bits de la manette du jeu (haut / bas / gauche / droite), comme celle des touches de deplacement."""
        if self.croix_on and CROIX not in self.visibles(): self.croix_lacher(); return 0
        k = self.croix_secteur()
        if k is None: return 0
        import moteur as MO
        return (MO.HAUT, MO.HAUT | MO.DROITE, MO.DROITE, MO.BAS | MO.DROITE, MO.BAS, MO.BAS | MO.GAUCHE, MO.GAUCHE, MO.HAUT | MO.GAUCHE)[k]

    # ---- dessin
    def _icone(self, nom):
        """Icone d'origine 32 x 32 (RGBA), couleur des pixels transparents propagee d'un pixel (pas de liseré sombre quand le filtre melange les bords)."""
        a = self.orig.get(nom)
        if a is None:
            from PIL import Image
            import hd as HD
            f = os.path.join(self.J.args.cache, 'ui_MenuTexture.png')
            try: im = Image.open(f).convert('RGBA'); n = ICONE[nom]; a = np.array(im.crop((n * 32, LIGNE_ICONES, n * 32 + 32, LIGNE_ICONES + 32)))
            except Exception: a = np.zeros((32, 32, 4), np.uint8); a[..., 3] = 120
            a = self.orig[nom] = HD._dilater(a, 1)
        return a

    def _sprite(self, nom, c):
        """Sprite de l'icone pour un bouton de c pixels de cote. L'icone est d'abord agrandie par un entier n (plus proche voisin : chaque pixel d'origine devient un bloc net), puis
        reduite au pixels exacts par le filtre lineaire : les pixels restent francs, seule la frontiere entre deux pixels est adoucie (un agrandissement lineaire direct de 32 a 72 px les ecrasait)."""
        n = max(1, int(np.ceil(c / 32.0 - 1e-6)))
        s = self.spr.get((nom, n))
        if s is None:
            a = np.repeat(np.repeat(self._icone(nom), n, axis=0), n, axis=1); t_ = 32 * n
            img = pyglet.image.ImageData(t_, t_, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=t_ * 4)
            t = img.get_texture(); gl.glBindTexture(t.target, t.id)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            s = self.spr[(nom, n)] = pyglet.sprite.Sprite(t)
        return s, n

    def _plaque(self, x, y, w, h, enfonce):
        """Plaque d'origine du bouton (feuille « Button », partie 7, 9 tranches a coins de 16 unites, image « appuyee » quand le bouton est enfonce), comme les boutons des fenetres du jeu : Rendu.plaque.
        -> False sans les menus d'origine (le repli dessine le fond)."""
        r = getattr(self.J, 'ui_rendu', None)
        return bool(r is not None and r.plaque(x, y, w, h, (self.J.width, self.J.height), enfonce, coin=COIN_PLAQUE * self.echelle()))

    def _texte_combat(self, x, y, w, h):
        """Bouton de vitesse des combats : « Vitesse » en petit, au-dessus de la vitesse courante (Normal, Rapide, Très rapide : mots du menu Commandes, jamais « x2 ») ; la vitesse est plus chaude quand elle accelere.
        Police du menu Pause (celle du jeu mobile), taille proportionnelle a la plaque."""
        import reglages as RG
        v = RG.cran_combat(self.J.reg['vitesse_combat']); k = self.echelle(); pa = self.J.pause
        coul = {1.0: (255, 255, 255, 255), 2.0: (255, 235, 130, 255), 3.0: (255, 176, 80, 255)}[v]
        sous = pa._ajuster('Vitesse', 15.0 * k, (196, 200, 208, 255), w - 14 * k); sous.x = x + (w - sous.content_width) / 2; sous.y = y + h * 0.60; sous.draw()
        et = pa._ajuster(RG.NOMS_VITESSE_COMBAT[v], 21.0 * k, coul, w - 14 * k); et.x = x + (w - et.content_width) / 2; et.y = y + h * 0.17; et.draw()

    def _art_croix(self):
        """Sprites de la croix (morceaux de la feuille « Button », ancres au centre pour tourner autour)."""
        if self.art is None:
            from PIL import Image
            import hd as HD
            try: im = np.array(Image.open(os.path.join(self.J.args.cache, 'ui_Button.png')).convert('RGBA'))
            except Exception: im = np.zeros((512, 512, 4), np.uint8)
            self.art = {}
            for nom, (x, y, w, h) in ART_CROIX.items():
                a = HD._dilater(im[y:y + h, x:x + w].copy(), 1)
                t = pyglet.image.ImageData(w, h, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=w * 4).get_texture()
                gl.glBindTexture(t.target, t.id)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                t.anchor_x = w / 2.0; t.anchor_y = h / 2.0
                self.art[nom] = pyglet.sprite.Sprite(t)
        return self.art

    def _croix(self, edition=False):
        """Croix : anneau, huit pastilles (celle de la direction tenue s'allume), boule qui suit la souris. Toujours opaque et la boule reste normale (SetVisibleColMove : boule orange et halo
        seulement pendant le clignotement du tutoriel, MOVE_WAIT_TIME / MOVE_LIMIT_ALPHA sont des constantes inutilisees)."""
        art = self._art_croix(); x, y, c, _ = self.rect(CROIX); cx, cy = x + c / 2, y + c / 2; k = c / 256.0
        sect = self.croix_secteur()
        a = 1.0                                                                            # (masquee, elle reste entiere dans l'editeur : le voile « Masquée » de pause.py l'assombrit comme les autres elements)
        def poser(nom, px, py, rot=0.0, op=1.0):
            sp = art[nom]; sp.update(x=px, y=py, scale=k, rotation=rot); sp.opacity = int(255 * a * op); sp.draw()
        poser('anneau', cx, cy)
        for i in range(8):
            ang = i * 45.0; r = RAYON_PASTILLE * c
            poser('pastille_on' if sect == i else 'pastille', cx + math.sin(math.radians(ang)) * r, cy + math.cos(math.radians(ang)) * r, ang)
        vx, vy = self.cv if self.croix_on else (0.0, 0.0); n = math.hypot(vx, vy)
        if n > COURSE_BOULE: vx, vy = vx * COURSE_BOULE / n, vy * COURSE_BOULE / n
        bx, by = cx + vx * c / 2, cy + vy * c / 2
        poser('boule', bx, by)

    def dessiner(self, visibles, edition=False, grille=True):
        if not visibles and not edition: return
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        W, H = self.J.width, self.J.height
        if edition:                                              # voile sombre et grille (facultative)
            fond = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); fond.opacity = 110; fond.draw()
            if grille: tracer_grille(W, H)
        for nom in BOUTONS:
            if nom not in visibles and not edition: continue
            x, y, w, h = self.rect(nom); actif = self.appui == nom or (self.pris is not None and self.pris[0] == nom)
            vrai = self._plaque(x, y, w, h, actif)
            if not vrai: cadre(x, y, w, h, h / 60.0, 0.45 if actif else 0.0)    # sans les menus d'origine : fond de bouton dessine (fenetre bleu nuit a cadre blanc, comme celles du jeu mobile)
            if nom == COMBAT: self._texte_combat(x, y, w, h)
            else:
                ci = PLAQUE_DQ[nom][2] * self.echelle(); s, n = self._sprite(nom, ci)
                s.update(x=x + (w - ci) / 2, y=y + (h - ci) / 2, scale=ci / (32.0 * n))
                s.color = (170, 170, 170) if actif and not vrai else (255, 255, 255); s.opacity = 255 if edition else 235
                s.draw()
            if edition:
                pyglet.shapes.Box(x, y, w, h, thickness=2, color=(255, 235, 130)).draw()
                et = self.J._etiq(LIBELLE[nom], max(11.0, h / 5.0), (255, 235, 130, 255)); et.x = min(max(4.0, x + w / 2 - et.content_width / 2), W - et.content_width - 4); et.y = min(y + h + 4, H - et.content_height - 2); et.draw()
        if CROIX in visibles or edition:
            self._croix(edition)
            if edition:
                x, y, c, _ = self.rect(CROIX); actif = self.pris is not None and self.pris[0] == CROIX
                pyglet.shapes.Box(x, y, c, c, thickness=2, color=(255, 235, 130)).draw()
                et = self.J._etiq(LIBELLE[CROIX], max(11.0, self.taille() / 5.0), (255, 235, 130, 255)); et.x = min(max(4.0, x + c / 2 - et.content_width / 2), W - et.content_width - 4); et.y = min(y + c + 4, H - et.content_height - 2); et.draw()
