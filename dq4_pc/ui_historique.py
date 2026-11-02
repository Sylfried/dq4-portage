"""Fenetre « Historique des messages » (page 'historique' du menu Pause, voir pause.py) : tout ce qui a ete dit, le plus recent en bas, avec qui l'a dit et ou (historique.py).

Dans le style des menus du jeu : fenetre noire cadree de blanc, une plaque du jeu par message (ou par suite de messages du meme locuteur : un seul en-tete), texte dans la police d'origine (SE-GARRIR, PoliceBitmap),
plaque assombrie sous le pointeur, curseur dore au clavier, bouton retour du jeu. Le moteur est arrete tant que la fenetre est ouverte (Pause.ouvrir -> pause_jeu) : le message affiche reste tel quel et aucune touche n'arrive au jeu.
Defilement : molette, fleches haut / bas (un message), Page precedente / suivante (une page), Debut / Fin, barre de defilement, glisser dans la liste. Gauche / droite ou le bouton du haut : Tout / Combats."""
import pyglet
from pyglet import gl
import historique as HI
import hud_mobile as HM

OR = (255, 235, 4); BLANC = (255, 255, 255); GRIS = (150, 150, 150); LIEU = (170, 190, 215); AIDE = (120, 120, 120)
OPACITE_FOND = 0.98                  # fond de la fenetre (les fenetres du jeu : 0,68, hud_mobile.OPACITE_JEU)
MAX_GROUPE = 6                       # messages au plus sous un meme en-tete
TOLERANCE_GLISSE = 6.0               # pixels : en dessous, un appui dans la liste n'est pas un glissement
FILTRES = (('Tout', None), ('Combats', HI.CAT_COMBAT))


def heure_jeu(t):
    """Temps de jeu (1/60 s) -> « 1:05:12 »."""
    s = max(0, int(t)) // 60
    return '%d:%02d:%02d' % (s // 3600, s % 3600 // 60, s % 60)


def grouper(entrees, lib=HI.AUTO):
    """Entrees (ordre chronologique) -> groupes : des messages qui se suivent avec le meme en-tete (HI.meme_groupe), MAX_GROUPE au plus."""
    gs = []
    for e in entrees:
        if gs and len(gs[-1]) < MAX_GROUPE and HI.meme_groupe(gs[-1][-1], e, lib): gs[-1].append(e)
        else: gs.append([e])
    return gs


class VueHistorique:
    def __init__(self, pause):
        self.P = pause; self.J = pause.J
        self.filtre = 0; self.entrees = []; self.groupes = []
        self.fin = 0; self.sel = 0; self.vis = 1                      # dernier groupe visible (en bas), groupe choisi au clavier, nombre de groupes visibles a la derniere image
        self.zones = []; self.barre = None; self.glisse_barre = None   # (x0, y0, x1, y1, groupe) des plaques dessinees ; barre de defilement ; prise du curseur de la barre
        self.zone_ret = None; self.zone_filtre = None
        self.drag = None                                               # glissement dans la liste : [y de depart, fin de depart, deplace ?]
        self._spr = {}; self._lignes = {}

    # ---- donnees
    def entrer(self):
        """A l'ouverture de la page : recharge la liste (le moteur est arrete, elle ne change plus), en bas sur le message le plus recent."""
        self.filtre = 0; self.glisse_barre = None; self.drag = None; self._lignes.clear()
        self.recharger()

    def recharger(self):
        h = getattr(self.J, 'historique', None)
        self.entrees = h.entrees(FILTRES[self.filtre][1]) if h is not None else []
        self.groupes = grouper(self.entrees)
        self.fin = self.sel = max(0, len(self.groupes) - 1); self.zones = []

    def basculer_filtre(self, d=1):
        self.filtre = (self.filtre + d) % len(FILTRES); self.recharger()

    # ---- defilement
    def _borner(self):
        n = len(self.groupes)
        self.fin = max(min(n - 1, self.vis - 1), min(n - 1, self.fin)) if n else 0
        self.sel = max(0, min(n - 1, self.sel)) if n else 0

    def aller(self, i):
        """Choisit le groupe i et amene la vue dessus."""
        n = len(self.groupes)
        if not n: return
        self.sel = max(0, min(n - 1, i))
        if self.sel > self.fin: self.fin = self.sel
        elif self.sel < self.fin - self.vis + 1: self.fin = self.sel + self.vis - 1
        self._borner()

    def bouger(self, d): self.aller(self.sel + d)

    def decaler(self, d):
        """Fait defiler la vue de d groupes (negatif : vers les plus anciens) ; la selection au clavier reste dans la vue."""
        self.fin += d; self._borner()
        if self.sel > self.fin: self.sel = self.fin
        elif self.sel < self.fin - self.vis + 1: self.sel = max(0, self.fin - self.vis + 1)

    # ---- entrees
    def touche(self, symbol, modifiers=0):
        K = pyglet.window.key; P = self.P; act = self.J.reg.action_de(symbol)
        P.mode_souris = False
        if symbol in (K.ESCAPE, K.BACKSPACE) or act == 'B': P.retour(); return True
        if act == 'historique': P.fermer(); return True                       # la touche qui ouvre l'historique le referme
        if symbol == K.UP or act == 'haut': self.bouger(-1); P._repeter(symbol, 'v', -1)
        elif symbol == K.DOWN or act == 'bas': self.bouger(1); P._repeter(symbol, 'v', 1)
        elif symbol == K.PAGEUP or act == 'L': self.bouger(-max(1, self.vis - 1))
        elif symbol == K.PAGEDOWN or act == 'R': self.bouger(max(1, self.vis - 1))
        elif symbol == K.HOME: self.aller(0)
        elif symbol == K.END: self.aller(len(self.groupes) - 1)
        elif symbol == K.LEFT or act == 'gauche': self.basculer_filtre(-1)
        elif symbol == K.RIGHT or act == 'droite': self.basculer_filtre(1)
        return True

    def molette(self, sy):
        self.P.mode_souris = True
        self.decaler(-2 if sy > 0 else 2)

    def survol(self, x, y):
        P = self.P; p = P.pos_souris; P.pos_souris = (x, y)
        if p is None or abs(x - p[0]) + abs(y - p[1]) < 3: return
        P.mode_souris = True

    def _dans(self, z, x, y): return z is not None and z[0] <= x <= z[2] and z[1] <= y <= z[3]

    def clic(self, x, y, bouton):
        M = pyglet.window.mouse; P = self.P
        P.mode_souris = True; P.pos_souris = (x, y)
        if bouton == M.RIGHT: P.retour(); return
        if self._dans(self.zone_ret, x, y): P.retour(); return
        if self._dans(self.zone_filtre, x, y): self.basculer_filtre(); return
        b = self.barre
        if b and b['x0'] <= x <= b['x1'] and b['y0'] <= y <= b['y1']:
            if y > b['ptop']: self.decaler(-1)
            elif y < b['pbot']: self.decaler(1)
            elif b['pouce'][0] <= y <= b['pouce'][1]: self.glisse_barre = b['pouce'][1] - y
            elif y > b['pouce'][1]: self.decaler(-(self.vis - 1))
            else: self.decaler(self.vis - 1)
            return
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
        pas = max(20.0, self.J.height / 14.0)                                        # un message tous les ~50 px glisses : le contenu suit le doigt a peu pres
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
        cle = (e.n, e.t, int(largeur), int(sc * 100))
        r = self._lignes.get(cle)
        if r is None:
            if len(self._lignes) > 4000: self._lignes.clear()
            r = self._lignes[cle] = HI.envelopper(e.texte, largeur / sc if bm else largeur, (lambda s: bm.largeur(s)) if bm else (lambda s: self.P._et(s, taille).content_width * 0.9))
        return r

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
        HM.cadre(x0, y0, pw, h, k, fond=(0, 0, 0), opacite=OPACITE_FOND)                  # (presque opaque : la liste est dense, le decor et le message du jeu ne doivent pas transparaitre dessous)
        titre = 'Historique des messages'
        wt = self._larg(bm, titre, sc * 1.25, taille * 1.3)
        self._ligne(bm, titre, x0 + (pw - wt) / 2, y1 - 24 * k - asc * 1.25, sc * 1.25, BLANC, taille * 1.3)
        # bouton du filtre (Tout / Combats), en haut a droite
        nom_f = FILTRES[self.filtre][0]; fw, fh = max(120 * k, self._larg(bm, 'Combats', sc, taille) + 40 * k), 34 * k
        fx, fy = x0 + pw - fw - 28 * k, y1 - 22 * k - fh
        self.zone_filtre = (fx, fy, fx + fw, fy + fh)
        sur_f = P._sur(self.zone_filtre) if hasattr(P, '_sur') else False
        self._plaque(fx, fy, fw, fh, k, sur_f)
        lf = self._larg(bm, nom_f, sc, taille); self._ligne(bm, nom_f, fx + (fw - lf) / 2, fy + fh / 2 - (asc * 0.37 if bm else 6 * k), sc, BLANC, taille)
        nb = '%d message%s' % (len(self.entrees), 's' if len(self.entrees) > 1 else '')
        self._ligne(bm, nb, x0 + 28 * k, y1 - 22 * k - fh / 2 - (asc * 0.45 * 0.9 if bm else 6 * k), sc * 0.9, GRIS, taille * 0.9)
        # zone de la liste
        padx, pady, ecart = 14 * k, 8 * k, 6 * k
        lx0, lx1 = x0 + 34 * k, x0 + pw - 30 * k - 12 * k; ly1 = y1 - 70 * k; ly0 = y0 + 40 * k
        wtxt = (lx1 - lx0) - 2 * padx
        self.zones = []; self.barre = None
        n = len(self.groupes)
        if not n:
            msg = 'Aucun message pour l\'instant.' if self.filtre == 0 else 'Aucun message de combat.'
            lm = self._larg(bm, msg, sc, taille); self._ligne(bm, msg, x0 + (pw - lm) / 2, (ly0 + ly1) / 2, sc, GRIS, taille)
        else:
            mouse = P.mode_souris; blocs = []; y = ly0; i = min(self.fin, n - 1)
            while i >= 0:
                lignes = self._rangees(bm, self.groupes[i], wtxt, sc, taille)
                hb = 2 * pady + len(lignes) * pas + sum(0.3 * pas for r in lignes if r[0] == 'txt' and r[2])
                if y + hb > ly1:
                    if not blocs:                                                  # un seul groupe plus haut que la fenetre : on n'en garde que la fin
                        garde = max(1, int((ly1 - ly0 - 2 * pady) / pas)); lignes = lignes[-garde:]; hb = ly1 - ly0
                        blocs.append((i, y, hb, lignes))
                    break
                blocs.append((i, y, hb, lignes)); y += hb + ecart; i -= 1
            self.vis = max(1, len(blocs)); self._borner()
            for (i, yb, hb, lignes) in blocs:
                zone = (lx0, yb, lx1, yb + hb); self.zones.append(zone + (i,))
                choisi = (P._pointeur_dans(zone) and self.glisse_barre is None) if mouse else i == self.sel
                self._plaque(lx0, yb, lx1 - lx0, hb, k, choisi)
                if choisi and not mouse: P._curseur(x0 + 4 * k, yb + hb / 2, min(hb * 0.7, 28 * k))
                ytop = yb + hb - pady
                for r in lignes:
                    if r[0] == 'txt' and r[2]: ytop -= 0.3 * pas
                    base = ytop - asc
                    if r[0] == 'ent':
                        _, qui, lieu, t = r
                        self._ligne(bm, qui, lx0 + padx, base, sc, OR, taille)
                        if lieu: self._ligne(bm, HI.SEPARATEUR + lieu, lx0 + padx + self._larg(bm, qui, sc, taille), base, sc, LIEU, taille)
                        ht = heure_jeu(t); self._ligne(bm, ht, lx1 - padx - self._larg(bm, ht, sc * 0.8, taille * 0.8), base, sc * 0.8, AIDE, taille * 0.8)
                    else: self._ligne(bm, r[1], lx0 + padx, base, sc, BLANC, taille)
                    ytop -= pas
            if n > self.vis: self.barre = P._barre_defilement(x0 + pw - 14 * k, ly1, ly0, n, self.vis, max(0, self.fin - self.vis + 1), k, self.glisse_barre is not None)
        # aide et bouton retour
        aide = 'Haut / Bas, Page préc. / suiv. : parcourir     Gauche / Droite : Tout / Combats     Échap : fermer'
        la = self._larg(bm, aide, sc * 0.72, taille * 0.72); self._ligne(bm, aide, x0 + (pw - la) / 2, y0 + 14 * k, sc * 0.72, AIDE, taille * 0.72)
        bx = x0 + pw - bw - 8 * k; by = y0 - 8 * k - bh; self.zone_ret = (bx, by, bx + bw, by + bh)
        P._bouton_retour(bx, by, bw, bh, P._sur(self.zone_ret))

    def _rangees(self, bm, groupe, largeur, sc, taille):
        """Rangees d'un groupe : ('ent', locuteur, lieu, temps de jeu) puis ('txt', ligne, air) pour chaque ligne de chaque message ; air : un peu d'espace avant (premiere ligne d'un message qui en suit un autre)."""
        e0 = groupe[0]; rangees = [('ent', HI.locuteur(e0), None if e0.genre in (HI.GENRE_NOM, HI.GENRE_GENERAL, HI.GENRE_COMBAT) else HI.lieu_de(e0.carte), e0.t)]
        for j, e in enumerate(groupe):
            for m, l in enumerate(self._lignes_de(bm, e, largeur, sc, taille)): rangees.append(('txt', l, m == 0 and j > 0))
        return rangees
