"""Fenetre « Historique » (page 'historique' du menu Pause, voir pause.py) : trois onglets, Dialogues (hors combat), Combats et Favoris ; le plus recent en bas.

Chaque element est dessine comme une fenetre de message du jeu (meme cadre noir translucide, meme police d'origine SE-GARRIR, PoliceBitmap) : un dialogue avec le nom du locuteur dans un cartouche SEULEMENT si le jeu
l'affichait quand il a ete dit ; un combat avec son issue, ses ennemis, l'or et l'experience. Une etoile en haut a droite de chaque element le met en favori (il est alors garde dans un fichier jusqu'a ce qu'on
retire l'etoile ; le reste de l'historique disparait quand on ferme la visionneuse). Le fond de la fenetre est aussi transparent que les autres fenetres du jeu (hud_mobile.OPACITE_JEU).
Le moteur est arrete tant que la fenetre est ouverte (Pause.ouvrir -> pause_jeu) : le message affiche reste tel quel et aucune touche n'arrive au jeu.
Clavier : haut / bas (un element), page precedente / suivante (une page), debut / fin, gauche / droite (onglet), Entree ou Action (etoile de l'element choisi), la touche de l'historique (Dialogues -> Combats -> ferme),
Echap / Annuler (retour). Souris : molette, barre de defilement, glisser dans la liste, clic sur un onglet, clic sur une etoile."""
import pyglet
from pyglet import gl
import historique as HI
import hud_mobile as HM
import reglages as RG

OR = (255, 235, 4); BLANC = (255, 255, 255); GRIS = (150, 150, 150); AIDE = (120, 120, 120); ETOILE = (255, 210, 40); VIDE_ETOILE = (20, 20, 20)
TOLERANCE_GLISSE = 6.0               # pixels : en dessous, un appui dans la liste n'est pas un glissement
ONGLETS = (('Dialogues', 'dialogues'), ('Combats', 'combats'), ('Favoris', 'favoris'))
O_DIALOGUES, O_COMBATS, O_FAVORIS = 0, 1, 2
VIDES = {'dialogues': 'Aucun dialogue pour l\'instant.', 'combats': 'Aucun combat pour l\'instant.',
         'favoris': 'Aucun favori : choisis un élément et appuie sur Entrée (ou clique son étoile) pour le garder.'}


def heure_jeu(t):
    """Temps de jeu (1/60 s) -> « 1:05:12 »."""
    s = max(0, int(t)) // 60
    return '%d:%02d:%02d' % (s // 3600, s % 3600 // 60, s % 60)


def onglet_suivant(i, d=1): return (i + d) % len(ONGLETS)


def touche_suivante(onglet):
    """Touche de l'historique dans la fenetre : Dialogues -> Combats ; Combats ou Favoris -> fermer (None)."""
    return O_COMBATS if onglet == O_DIALOGUES else None


class VueHistorique:
    def __init__(self, pause):
        self.P = pause; self.J = pause.J
        self.onglet = O_DIALOGUES; self.elements = []
        self.fin = 0; self.sel = 0; self.vis = 1                      # dernier element visible (en bas), element choisi au clavier, nombre d'elements visibles a la derniere image
        self.zones = []; self.zones_etoile = []; self.zones_onglet = []; self.barre = None; self.glisse_barre = None
        self.zone_ret = None
        self.drag = None                                               # glissement dans la liste : [y de depart, fin de depart, deplace ?]
        self._spr = {}; self._lignes = {}

    # ---- donnees
    def entrer(self, onglet=O_DIALOGUES):
        """A l'ouverture de la page : recharge la liste (le moteur est arrete, elle ne change plus), en bas sur l'element le plus recent."""
        self.onglet = onglet if 0 <= onglet < len(ONGLETS) else O_DIALOGUES
        self.glisse_barre = None; self.drag = None; self._lignes.clear()
        self.recharger()

    def recharger(self, garder=False):
        h = getattr(self.J, 'historique', None)
        self.elements = h.liste(ONGLETS[self.onglet][1]) if h is not None else []
        n = len(self.elements)
        if garder: self.fin = max(0, min(n - 1, self.fin)); self.sel = max(0, min(n - 1, self.sel))
        else: self.fin = self.sel = max(0, n - 1)
        self.zones = []; self.zones_etoile = []

    def changer_onglet(self, i):
        i %= len(ONGLETS)
        if i != self.onglet: self.onglet = i; self.recharger()

    def courant(self):
        return self.elements[self.sel] if 0 <= self.sel < len(self.elements) else None

    def etoile(self, i=None):
        """Met en favori (ou retire des favoris) l'element i (le choisi par defaut) ; -> True si c'est maintenant un favori. Dans l'onglet Favoris, l'element retire disparait de la liste."""
        h = getattr(self.J, 'historique', None)
        if h is None: return False
        e = self.courant() if i is None else (self.elements[i] if 0 <= i < len(self.elements) else None)
        if e is None: return False
        r = h.basculer_favori(e)
        if self.onglet == O_FAVORIS: self.recharger(garder=True)
        return r

    # ---- defilement
    def _borner(self):
        n = len(self.elements)
        self.fin = max(min(n - 1, self.vis - 1), min(n - 1, self.fin)) if n else 0
        self.sel = max(0, min(n - 1, self.sel)) if n else 0

    def aller(self, i):
        """Choisit l'element i et amene la vue dessus."""
        n = len(self.elements)
        if not n: return
        self.sel = max(0, min(n - 1, i))
        if self.sel > self.fin: self.fin = self.sel
        elif self.sel < self.fin - self.vis + 1: self.fin = self.sel + self.vis - 1
        self._borner()

    def bouger(self, d): self.aller(self.sel + d)

    def decaler(self, d):
        """Fait defiler la vue de d elements (negatif : vers les plus anciens) ; la selection au clavier reste dans la vue."""
        self.fin += d; self._borner()
        if self.sel > self.fin: self.sel = self.fin
        elif self.sel < self.fin - self.vis + 1: self.sel = max(0, self.fin - self.vis + 1)

    # ---- entrees
    def touche(self, symbol, modifiers=0):
        K = pyglet.window.key; P = self.P; act = self.J.reg.action_de(symbol)
        P.mode_souris = False
        if symbol in (K.ESCAPE, K.BACKSPACE) or act == 'B': P.retour(); return True
        if act == 'historique':                                               # la touche qui ouvre l'historique : Dialogues -> Combats -> ferme tout
            suite = touche_suivante(self.onglet)
            if suite is None: P.fermer()
            else: self.changer_onglet(suite)
            return True
        if symbol == K.UP or act == 'haut': self.bouger(-1); P._repeter(symbol, 'v', -1)
        elif symbol == K.DOWN or act == 'bas': self.bouger(1); P._repeter(symbol, 'v', 1)
        elif symbol == K.PAGEUP or act == 'L': self.bouger(-max(1, self.vis - 1))
        elif symbol == K.PAGEDOWN or act == 'R': self.bouger(max(1, self.vis - 1))
        elif symbol == K.HOME: self.aller(0)
        elif symbol == K.END: self.aller(len(self.elements) - 1)
        elif symbol == K.LEFT or act == 'gauche': self.changer_onglet(self.onglet - 1)
        elif symbol == K.RIGHT or act == 'droite': self.changer_onglet(self.onglet + 1)
        elif symbol in (K.RETURN, K.ENTER) or act in ('menu', 'A'): self.etoile()
        return True

    def molette(self, sy):
        self.P.mode_souris = True
        self.decaler(-2 if sy > 0 else 2)

    def survol(self, x, y):
        P = self.P; p = P.pos_souris; P.pos_souris = (x, y)
        if p is None or abs(x - p[0]) + abs(y - p[1]) < 3: return
        P.mode_souris = True

    @staticmethod
    def _dans(z, x, y): return z is not None and z[0] <= x <= z[2] and z[1] <= y <= z[3]

    def clic(self, x, y, bouton):
        M = pyglet.window.mouse; P = self.P
        P.mode_souris = True; P.pos_souris = (x, y)
        if bouton == M.RIGHT: P.retour(); return
        if self._dans(self.zone_ret, x, y): P.retour(); return
        for z in self.zones_onglet:
            if self._dans(z, x, y): self.changer_onglet(z[4]); return
        b = self.barre
        if b and b['x0'] <= x <= b['x1'] and b['y0'] <= y <= b['y1']:
            if y > b['ptop']: self.decaler(-1)
            elif y < b['pbot']: self.decaler(1)
            elif b['pouce'][0] <= y <= b['pouce'][1]: self.glisse_barre = b['pouce'][1] - y
            elif y > b['pouce'][1]: self.decaler(-(self.vis - 1))
            else: self.decaler(self.vis - 1)
            return
        for z in self.zones_etoile:
            if self._dans(z, x, y): self.sel = z[4]; self.etoile(z[4]); return
        for (x0, y0, x1, y1, i) in self.zones:
            if x0 <= x <= x1 and y0 <= y <= y1: self.sel = i; break
        self.drag = [y, self.fin, False]

    def relache(self, x, y, bouton):
        self.glisse_barre = None; self.drag = None

    def glisser(self, x, y):
        b = self.barre
        if self.glisse_barre is not None:
            if not b: self.glisse_barre = None; return
            libre = b['ptop'] - b['pbot'] - b['th']
            if libre > 0:
                deb = round(max(0.0, min(1.0, (b['ptop'] - (y + self.glisse_barre)) / libre)) * (b['n'] - b['vis']))
                self.decaler(deb + self.vis - 1 - self.fin)
            return
        d = self.drag
        if d is None: return
        if not d[2] and abs(y - d[0]) < TOLERANCE_GLISSE: return
        d[2] = True
        pas = max(20.0, self.J.height / 14.0)                                        # un element tous les ~50 px glisses : le contenu suit le doigt a peu pres
        cible = d[1] + int((y - d[0]) / pas)               # (le doigt descend : la liste descend, on remonte vers les plus anciens)
        self.decaler(cible - self.fin)

    # ---- dessin
    def _bm(self):
        r = getattr(self.J, 'ui_rendu', None)
        return r.textes.bitmap if r is not None and getattr(r, 'textes', None) is not None else None

    def _larg(self, bm, texte, sc, taille):
        if bm: return bm.largeur(texte) * sc
        return self.P._et(texte, taille).content_width

    def _ligne(self, bm, texte, x, ybase, sc, coul, taille):
        """Une ligne de texte dont la ligne de base est en ybase : police bitmap du jeu (une texture par ligne, teintee), sinon police du systeme."""
        if not texte.strip(): return
        if bm:
            tex, w, h, base = bm.ligne(texte)
            cle = (texte, coul); sp = self._spr.get(cle)
            if sp is None or sp.image is not tex:
                if len(self._spr) > 600: self._spr.clear()
                sp = self._spr[cle] = pyglet.sprite.Sprite(tex); sp.color = coul[:3]
            sp.update(x=x - bm.PAD * sc, y=ybase - (h - base) * sc, scale=sc); sp.draw()
        else:
            et = self.P._et(texte, taille, tuple(coul) + (255,)); et.x = x; et.y = ybase; et.draw()

    def _lignes_de(self, bm, e, largeur, sc, taille):
        """Lignes d'un element, coupees a `largeur` : le texte d'un dialogue ; les lignes de resultat d'un combat."""
        cle = (e.n, e.type, int(largeur), int(sc * 100))
        r = self._lignes.get(cle)
        if r is None:
            if len(self._lignes) > 4000: self._lignes.clear()
            mes = (lambda s: bm.largeur(s)) if bm else (lambda s: self.P._et(s, taille).content_width * 0.9)
            larg = largeur / sc if bm else largeur
            brut = HI.lignes_combat(e) if e.type == HI.TYPE_COMBAT else [e.texte]
            r = []
            for ligne in brut: r.extend(HI.envelopper(ligne, larg, mes))
            self._lignes[cle] = r
        return r

    def _etoile(self, cx, cy, rayon, pleine):
        """Etoile de favori : doree quand l'element est en favori, grise et creuse sinon."""
        if pleine:
            pyglet.shapes.Star(cx, cy, rayon, rayon * 0.45, 5, rotation=0, color=ETOILE + (255,)).draw()
        else:
            pyglet.shapes.Star(cx, cy, rayon, rayon * 0.45, 5, rotation=0, color=GRIS + (255,)).draw()
            pyglet.shapes.Star(cx, cy, rayon * 0.6, rayon * 0.27, 5, rotation=0, color=VIDE_ETOILE + (255,)).draw()

    def _plaque(self, x, y, w, h, k, choisi):
        J = self.J; r = getattr(J, 'ui_rendu', None)
        if r is not None and r.plaque(x, y, w, h, (J.width, J.height), choisi, coin=14 * k): return
        HM.plaque(x, y, w, h, k, choisi, None)

    def dessiner(self):
        J = self.J; P = self.P; W, H = J.width, J.height; k = max(0.75, H / 900.0)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        voile = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); voile.opacity = 90; voile.draw()
        bm = self._bm(); sc = max(0.8, min(2.4, H / 700.0)) if bm else 1.0; taille = 17 * k       # sc : un pixel de police du jeu = sc pixels d'ecran
        pas = (bm.interligne * sc) if bm else 24 * k; asc = (bm.ascent * sc) if bm else 18 * k
        kb = 1.1 * k; bw, bh = 64 * kb, 55.5 * kb
        pw = min(W - 60 * k, 1000 * k); h = H - 2 * 30 * k - bh - 10 * k
        x0 = (W - pw) / 2; y1 = (H + h + bh + 10 * k) / 2; y0 = y1 - h
        HM.cadre(x0, y0, pw, h, k, fond=(0, 0, 0), opacite=HM.OPACITE_JEU)                # aussi transparent que les autres fenetres du jeu
        titre = 'Historique'
        wt = self._larg(bm, titre, sc * 1.25, taille * 1.3)
        self._ligne(bm, titre, x0 + (pw - wt) / 2, y1 - 24 * k - asc * 1.25, sc * 1.25, BLANC, taille * 1.3)
        # onglets (plaques du jeu : l'onglet ouvert est la plaque « choisie »)
        th = 34 * k; ty = y1 - 70 * k; self.zones_onglet = []
        lgs = [self._larg(bm, nom, sc, taille) + 44 * k for nom, _ in ONGLETS]; tw = max(lgs + [120 * k]); gap = 10 * k
        tx = x0 + (pw - (tw * len(ONGLETS) + gap * (len(ONGLETS) - 1))) / 2
        for i, (nom, cle) in enumerate(ONGLETS):
            zx = tx + i * (tw + gap); zone = (zx, ty, zx + tw, ty + th); self.zones_onglet.append(zone + (i,))
            sur = (P._sur(zone) if hasattr(P, '_sur') else False) and P.mode_souris
            self._plaque(zx, ty, tw, th, k, i == self.onglet or sur)
            lf = self._larg(bm, nom, sc, taille); self._ligne(bm, nom, zx + (tw - lf) / 2, ty + th / 2 - (asc * 0.37 if bm else 6 * k), sc, OR if i == self.onglet else BLANC, taille)
        # zone de la liste
        padx, pady, ecart = 16 * k, 10 * k, 12 * k
        lx0, lx1 = x0 + 34 * k, x0 + pw - 30 * k - 12 * k; ly1 = ty - 14 * k; ly0 = y0 + 40 * k
        etoile_l = 34 * k                                                              # place de l'etoile (a droite, dans l'element)
        wtxt = (lx1 - lx0) - 2 * padx - etoile_l
        self.zones = []; self.zones_etoile = []; self.barre = None
        n = len(self.elements)
        if not n:
            msg = VIDES[ONGLETS[self.onglet][1]]
            lm = self._larg(bm, msg, sc, taille); self._ligne(bm, msg, x0 + max(20 * k, (pw - lm) / 2), (ly0 + ly1) / 2, sc, GRIS, taille)
        else:
            mouse = P.mode_souris; blocs = []; y = ly0; i = min(self.fin, n - 1)
            while i >= 0:
                e = self.elements[i]
                lignes = self._lignes_de(bm, e, wtxt, sc, taille)
                avec_nom = e.type == HI.TYPE_DIALOGUE and bool(e.nom)
                en_tete = e.type == HI.TYPE_COMBAT
                nl = len(lignes) + (1 if en_tete else 0)
                hb = 2 * pady + nl * pas; hn = (pas + 10 * k) if avec_nom else 0.0           # hn : le cartouche du nom, au-dessus du cadre
                if y + hb + hn > ly1:
                    if not blocs:                                                  # un seul element plus haut que la fenetre : on n'en garde que la fin
                        garde = max(1, int((ly1 - ly0 - 2 * pady - hn) / pas)); lignes = lignes[-garde:]; hb = ly1 - ly0 - hn; nl = len(lignes) + (1 if en_tete else 0)
                        blocs.append((i, y, hb, hn, lignes))
                    break
                blocs.append((i, y, hb, hn, lignes)); y += hb + hn + ecart; i -= 1
            self.vis = max(1, len(blocs)); self._borner()
            for (i, yb, hb, hn, lignes) in blocs:
                e = self.elements[i]
                zone = (lx0, yb, lx1, yb + hb + hn); self.zones.append(zone + (i,))
                choisi = (P._pointeur_dans(zone) and self.glisse_barre is None) if mouse else i == self.sel
                HM.cadre(lx0, yb, lx1 - lx0, hb, k, eclaire=0.3 if choisi else 0.0, fond=(0, 0, 0), opacite=HM.OPACITE_JEU)         # le cadre d'une fenetre de message du jeu
                if hn:                                                              # cartouche du nom (affiche par le jeu au moment ou le dialogue a ete dit)
                    nw = self._larg(bm, e.nom, sc, taille) + 2 * 14 * k
                    HM.cadre(lx0 + 16 * k, yb + hb - 2 * k, nw, hn + 2 * k, k, eclaire=0.3 if choisi else 0.0, fond=(0, 0, 0), opacite=HM.OPACITE_JEU)
                    self._ligne(bm, e.nom, lx0 + 16 * k + 14 * k, yb + hb + hn - 5 * k - asc, sc, BLANC, taille)
                if choisi and not mouse: P._curseur(x0 + 4 * k, yb + hb / 2, min(hb * 0.7, 28 * k))
                ytop = yb + hb - pady
                if e.type == HI.TYPE_COMBAT:
                    base = ytop - asc
                    self._ligne(bm, HI.LIBELLE_ISSUE.get(e.issue, ''), lx0 + padx, base, sc, OR, taille)
                    ht = heure_jeu(e.t); self._ligne(bm, ht, lx1 - padx - etoile_l - self._larg(bm, ht, sc * 0.8, taille * 0.8), base, sc * 0.8, AIDE, taille * 0.8)
                    ytop -= pas
                for l in lignes:
                    self._ligne(bm, l, lx0 + padx, ytop - asc, sc, BLANC, taille); ytop -= pas
                rs = 11 * k; ex, ey = lx1 - padx - rs, yb + hb - pady - rs                # etoile en haut a droite de l'element
                z = (ex - rs * 1.3, ey - rs * 1.3, ex + rs * 1.3, ey + rs * 1.3); self.zones_etoile.append(z + (i,))
                self._etoile(ex, ey, rs * (1.15 if (mouse and P._pointeur_dans(z)) else 1.0), e.fav is not None)
            if n > self.vis: self.barre = P._barre_defilement(x0 + pw - 14 * k, ly1, ly0, n, self.vis, max(0, self.fin - self.vis + 1), k, self.glisse_barre is not None)
        # aide et bouton retour
        ks = (J.reg['touches'].get('historique') or [None])[0] if hasattr(J.reg, '__getitem__') else None
        kn = RG.nom_touche(ks) if ks else None
        aide = 'Haut / Bas : parcourir     Gauche / Droite : onglet     Entrée : favori ★' + ('     %s : suite' % kn if kn else '') + '     Échap : fermer'
        la = self._larg(bm, aide, sc * 0.72, taille * 0.72); self._ligne(bm, aide, x0 + (pw - la) / 2, y0 + 14 * k, sc * 0.72, AIDE, taille * 0.72)
        bx = x0 + pw - bw - 8 * k; by = y0 - 8 * k - bh; self.zone_ret = (bx, by, bx + bw, by + bh)
        P._bouton_retour(bx, by, bw, bh, P._sur(self.zone_ret))
