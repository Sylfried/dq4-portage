"""Boutons tactiles de la version mobile, affiches a l'ecran hors combat : Carte, Commandes (menu), Discussion de groupe.

Le jeu d'origine les dessine dans la couche Unity (TouchPad : « Map Button » = touche 0x1000, « Command Button » = 0x800, « Talk Button » = 0x400 ; icones 3, 4 et 15 de la feuille
MenuTexture, rangee de 32 px a y = 224). Le moteur dit quand ils sont visibles par le mot Global.Flag (premier mot de sa sortie) : (Flag & (8 | 0x30047)) == 8 (pad present, ni verrou du
joueur, fondu, effet d'ecran, interface verrouillee ni pause) ; la Carte exige en plus le bit 0x20. Les positions se reglent sur une grille de 32 x 18 cases (aimantation facultative)."""
import os
import numpy as np
import pyglet
from pyglet import gl

COLS, LIGNES = 32, 18                       # grille de l'ecran (cases proportionnelles a la fenetre)
NOMS = ('carte', 'menu', 'discussion')
DEFAUT = {'carte': (30, 1), 'menu': (30, 12), 'discussion': (30, 14)}      # coin superieur gauche (colonne, ligne) : colonne de droite, comme sur le telephone (Carte en haut, Commandes puis Discussion plus bas)
DECL = {'carte': 0x1000, 'menu': 0x800, 'discussion': 0x400}
ICONE = {'carte': 3, 'menu': 4, 'discussion': 15}
LIBELLE = {'carte': 'Carte', 'menu': 'Commandes', 'discussion': 'Discussion'}
LIGNE_ICONES = 224                           # ordonnee de la rangee d'icones dans la feuille (PartsInfo[3])


class Boutons:
    def __init__(self, jeu):
        self.J = jeu; self.spr = {}; self.pris = None; self.appui = None; self.edition = False; self.cle = None
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
        f = J.moteur.drapeaux()
        if (f & (8 | 0x30047)) != 8: return ()
        return tuple(n for n in NOMS if n != 'carte' or f & 0x20)

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
    def _sprite(self, nom):
        s = self.spr.get(nom)
        if s is None:
            from PIL import Image
            f = os.path.join(self.J.args.cache, 'ui_MenuTexture.png')
            try: im = Image.open(f).convert('RGBA'); n = ICONE[nom]; a = np.array(im.crop((n * 32, LIGNE_ICONES, n * 32 + 32, LIGNE_ICONES + 32)))
            except Exception: a = np.zeros((32, 32, 4), np.uint8); a[..., 3] = 120
            img = pyglet.image.ImageData(32, 32, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=128)
            t = img.get_texture(); gl.glBindTexture(t.target, t.id)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            s = self.spr[nom] = pyglet.sprite.Sprite(t)
        return s

    def dessiner(self, visibles, edition=False):
        if not visibles and not edition: return
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        W, H = self.J.width, self.J.height
        if edition:                                              # grille et consignes
            fond = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); fond.opacity = 110; fond.draw()
            for i in range(COLS + 1):
                l = pyglet.shapes.Line(i * W / COLS, 0, i * W / COLS, H, thickness=1, color=(255, 255, 255)); l.opacity = 38; l.draw()
            for j in range(LIGNES + 1):
                l = pyglet.shapes.Line(0, j * H / LIGNES, W, j * H / LIGNES, thickness=1, color=(255, 255, 255)); l.opacity = 38; l.draw()
        for nom in NOMS:
            if nom not in visibles and not edition: continue
            x, y, c = self.rect(nom); s = self._sprite(nom)
            s.update(x=x, y=y, scale=c / 32.0)
            actif = self.appui == nom or (self.pris is not None and self.pris[0] == nom)
            s.color = (170, 170, 170) if actif else (255, 255, 255); s.opacity = 255 if edition else 225
            s.draw()
            if edition:
                pyglet.shapes.Box(x, y, c, c, thickness=2, color=(255, 235, 130)).draw()
                et = self.J._etiq(LIBELLE[nom], max(11.0, c / 5.0), (255, 235, 130, 255)); et.x = min(max(4.0, x + c / 2 - et.content_width / 2), W - et.content_width - 4); et.y = min(y + c + 4, H - et.content_height - 2); et.draw()
