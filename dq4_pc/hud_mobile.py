"""Boutons tactiles de la version mobile, affiches a l'ecran hors combat : Carte, Commandes (menu), Discussion de groupe.

Le jeu d'origine les dessine dans la couche Unity (TouchPad : « Map Button » = touche 0x1000, « Command Button » = 0x800, « Talk Button » = 0x400 ; icones 3, 4 et 15 de la feuille
MenuTexture, rangee de 32 px a y = 224). Le moteur dit quand ils sont visibles par le mot Global.Flag (premier mot de sa sortie) : (Flag & (8 | 0x30047)) == 8 (pad present, ni verrou du
joueur, fondu, effet d'ecran, interface verrouillee ni pause) ; la Carte exige en plus le bit 0x20. Les positions se reglent sur une grille de 32 x 18 cases (aimantation facultative)."""
import os
import numpy as np
import pyglet
from pyglet import gl

COLS, LIGNES = 32, 18                       # grille de l'ecran (cases proportionnelles a la fenetre)
NOMS = ('carte', 'mode_carte', 'menu', 'discussion')
DEFAUT = {'carte': (30, 1), 'mode_carte': (30, 3), 'menu': (30, 12), 'discussion': (30, 14)}      # coin superieur gauche (colonne, ligne) : colonne de droite, comme sur le telephone (Carte en haut, Commandes puis Discussion plus bas)
DECL = {'carte': 0x1000, 'mode_carte': 0, 'menu': 0x800, 'discussion': 0x400}          # (mode_carte : pas de touche du jeu, le bouton change la vue de la carte ouverte)
ICONE = {'carte': 3, 'mode_carte': 19, 'menu': 4, 'discussion': 15}
LIBELLE = {'carte': 'Carte', 'mode_carte': 'Mode de la carte', 'menu': 'Commandes', 'discussion': 'Discussion'}
LIGNE_ICONES = 224                           # ordonnee de la rangee d'icones dans la feuille (PartsInfo[3])

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


class Boutons:
    def __init__(self, jeu):
        self.J = jeu; self.spr = {}; self.orig = {}; self.pris = None; self.appui = None; self.edition = False; self.cle = None
        self.pose_prise = None                  # (nom, decalage x, decalage y) pendant un deplacement

    # ---- geometrie
    def taille(self):
        return self.J.height / LIGNES * 1.6 * float(self.J.reg['boutons_taille'])

    def case(self, nom):
        p = self.J.reg['boutons_pos'].get(nom)
        return tuple(p) if p and len(p) == 2 else DEFAUT[nom]

    def rect(self, nom):
        """(x, y, cote) en pixels, origine en bas a gauche."""
        W, H = self.J.width, self.J.height; c = self.taille(); col, lig = self.case(nom)
        x = min(max(0.0, col * W / COLS), W - c); y = min(max(0.0, H - lig * H / LIGNES - c), H - c)
        return x, y, c

    def sous(self, x, y, visibles):
        for nom in reversed(NOMS):
            if nom not in visibles: continue
            rx, ry, c = self.rect(nom)
            if rx <= x <= rx + c and ry <= y <= ry + c: return nom
        return None

    def visibles(self):
        """Boutons a montrer : ceux que le moteur autorise (hors menu Echap, combat, effets d'ecran)."""
        J = self.J
        if not J.reg['boutons'] or J.pause.ouvert or J.moteur.etat.effet is not None: return ()
        from moteur import PARTIE_COMBAT
        if J.moteur.etat.partie == PARTIE_COMBAT: return ()
        if J.carte_ouverte: return ('mode_carte',) if J.carte_deux_vues else ()          # carte ouverte : seul le bouton qui change la vue (comme sur le mobile), s'il y en a deux
        f = J.moteur.drapeaux()
        if (f & (8 | 0x30047)) != 8: return ()
        return tuple(n for n in NOMS if n != 'mode_carte' and (n != 'carte' or f & 0x20))

    # ---- souris
    def appuyer(self, x, y, visibles):
        n = self.sous(x, y, visibles)
        if n: self.appui = n
        return n

    def relacher(self, x, y, visibles):
        """-> nom du bouton (clic complet : relachement sur le bouton appuye) ou None."""
        n, self.appui = self.appui, None
        return n if n and self.sous(x, y, visibles) == n else None

    # ---- edition des positions
    def prendre(self, x, y):
        n = self.sous(x, y, NOMS)
        if n: rx, ry, c = self.rect(n); self.pris = (n, x - rx, y - ry)
        return n

    def deplacer(self, x, y):
        if not self.pris: return
        n, dx, dy = self.pris; W, H = self.J.width, self.J.height; c = self.taille()
        px = min(max(0.0, x - dx), W - c); py = min(max(0.0, y - dy), H - c)         # coin inferieur gauche demande
        col = px * COLS / W; lig = (H - py - c) * LIGNES / H
        if self.J.reg['boutons_aimant']: col, lig = float(round(col)), float(round(lig))
        else: col, lig = round(col, 2), round(lig, 2)
        col = min(max(0.0, col), COLS - c * COLS / W); lig = min(max(0.0, lig), LIGNES - c * LIGNES / H)
        pos = dict(self.J.reg['boutons_pos']); pos[n] = [col, lig]; self.J.reg['boutons_pos'] = pos

    def poser(self): self.pris = None

    def remettre(self): self.J.reg['boutons_pos'] = {}

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

    def dessiner(self, visibles, edition=False, grille=True):
        if not visibles and not edition: return
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        W, H = self.J.width, self.J.height
        if edition:                                              # voile sombre et grille (facultative)
            fond = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); fond.opacity = 110; fond.draw()
            if grille: tracer_grille(W, H)
        for nom in NOMS:
            if nom not in visibles and not edition: continue
            x, y, c = self.rect(nom); actif = self.appui == nom or (self.pris is not None and self.pris[0] == nom)
            cadre(x, y, c, c, c / 60.0, 0.45 if actif else 0.0)                 # fond du bouton : fenetre bleu nuit a cadre blanc, comme celles du jeu mobile
            ci = c * 0.80; s, n = self._sprite(nom, ci)
            s.update(x=x + (c - ci) / 2, y=y + (c - ci) / 2, scale=ci / (32.0 * n))
            s.color = (170, 170, 170) if actif else (255, 255, 255); s.opacity = 255 if edition else 235
            s.draw()
            if edition:
                pyglet.shapes.Box(x, y, c, c, thickness=2, color=(255, 235, 130)).draw()
                et = self.J._etiq(LIBELLE[nom], max(11.0, c / 5.0), (255, 235, 130, 255)); et.x = min(max(4.0, x + c / 2 - et.content_width / 2), W - et.content_width - 4); et.y = min(y + c + 4, H - et.content_height - 2); et.draw()
