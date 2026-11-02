"""Fenetre « Historique » (page 'historique' du menu Pause, voir pause.py) : deux onglets, Dialogues (hors combat) et Combats ; le plus recent en bas. Une case a cocher « Favoris seulement » (a droite des onglets) ne garde dans
la liste de l'onglet ouvert que ses favoris ; elle est commune aux deux onglets (elle reste cochee quand on change d'onglet, et quand on rouvre la fenetre pendant la session : elle n'est pas enregistree).

Chaque element est dessine dans une BOITE DE DIALOGUE STANDARD, toujours de la meme taille (la fenetre de message du terrain, 3 lignes : cadre 452 x 126 unites d'interface, tire de la mise en page d'origine ; meme
echelle que dans le jeu ; classe `Boite`), avec le cadre et l'onglet du nom du jeu (frameData 192 et 191, dessines par ui_menu.FenetreMessage), la police d'origine SE-GARRIR et les lignes posees comme dans le jeu :
un dialogue avec le nom du locuteur dans l'onglet SEULEMENT si le jeu l'affichait quand il a ete dit ; un combat avec son issue, ses ennemis, l'or et l'experience. Un texte qui depasse les 3 lignes (combat a
beaucoup d'ennemis) continue dans une boite suivante (page 2/2...) : le cadre ne grandit jamais. Une etoile en haut a droite de chaque element le met en favori (il est alors garde dans un fichier jusqu'a ce qu'on
retire l'etoile ; le reste de l'historique disparait quand on ferme la visionneuse). Le fond de la fenetre est aussi transparent que les autres fenetres du jeu (hud_mobile.OPACITE_JEU).
Le moteur est arrete tant que la fenetre est ouverte (Pause.ouvrir -> pause_jeu) : le message affiche reste tel quel et aucune touche n'arrive au jeu.
Clavier : haut / bas (un element), page precedente / suivante (une page), debut / fin, gauche / droite (onglet), Entree, Menu ou Action (etoile de l'element choisi), F ou Carte (case « Favoris seulement »), la touche de
l'historique (Dialogues -> Combats -> ferme), Echap / Annuler (retour). Souris : molette, barre de defilement, glisser dans la liste, clic sur un onglet, sur la case ou sur une etoile."""
import pyglet
from pyglet import gl
import historique as HI
import hud_mobile as HM
import reglages as RG
import ui_menu as UM

OR = (255, 235, 4); BLANC = (255, 255, 255); GRIS = (150, 150, 150); AIDE = (175, 175, 175); ETOILE = (255, 210, 40); VIDE_ETOILE = (20, 20, 20)
TOLERANCE_GLISSE = 6.0               # pixels : en dessous, un appui dans la liste n'est pas un glissement
ONGLETS = (('Dialogues', 'dialogues'), ('Combats', 'combats'))
O_DIALOGUES, O_COMBATS = 0, 1
LIBELLE_FILTRE = 'Favoris seulement'
ECHELLE_BOITE = 1.12                 # agrandissement des fenetres du jeu par rapport a H / 800 (= fenetre.UI_ZOOM) : la boite de l'historique a la taille d'une boite de dialogue du jeu a l'ecran
TEXTE_ECH = 1.09                     # un pixel de la police d'origine (SE-GARRIR) = 1,09 unite d'interface dans le canevas de message du jeu (mesure : ligne de 371 pixels de police = 407 pixels a l'ecran a l'echelle 1,008 ; l'en-tete de la mise en page annonce 1,105, le moteur arrondit les avances)
VIDES = {'dialogues': 'Aucun dialogue pour l\'instant.', 'combats': 'Aucun combat pour l\'instant.'}
VIDES_FAVORIS = {'dialogues': 'Aucun dialogue en favori : décoche « Favoris seulement », choisis un dialogue et appuie sur Entrée (ou clique son étoile) pour le garder.',
                 'combats': 'Aucun combat en favori : décoche « Favoris seulement », choisis un combat et appuie sur Entrée (ou clique son étoile) pour le garder.'}


def heure_jeu(t):
    """Temps de jeu (1/60 s) -> « 1:05:12 »."""
    s = max(0, int(t)) // 60
    return '%d:%02d:%02d' % (s // 3600, s % 3600 // 60, s % 60)


def onglet_suivant(i, d=1): return (i + d) % len(ONGLETS)


def touche_suivante(onglet):
    """Touche de l'historique dans la fenetre : Dialogues -> Combats ; Combats -> fermer (None)."""
    return O_COMBATS if onglet == O_DIALOGUES else None


class Boite:
    """Boite de dialogue du terrain (MenuMessage type 0) a 3 lignes, en unites d'interface du jeu (800 de haut) : la taille du cadre (frameData 192), de l'onglet du nom (frameData 191) et le placement des lignes
    de texte. Les dimensions viennent de la mise en page d'origine quand elle est chargee (`depuis`), sinon des valeurs mesurees sur les captures du jeu. Une seule boite pour tout : 1, 2 ou 3 lignes, dialogue ou combat."""
    LARG, HAUT = 452.0, 126.0                  # cadre : x -223 a 229, z -251 a -125
    ONGLET_L, ONGLET_H = 246.0, 32.0           # onglet du nom : x -223 a 23, z -125 a -93 (depasse au-dessus du cadre)
    LIGNES, PAS = 3, 28.0                      # trois lignes de 28 (MiseEnPage : limiter_lignes(types[0], 3, 28.0))
    TEXTE_X, BASE_1 = 12.0, 37.2               # bord gauche du texte et ligne de base de la 1re ligne : distances au coin haut gauche du cadre (mesurees sur une capture du jeu : texte a 11 px du trait gauche du cadre, 1re ligne de base a 31 px du trait haut, a l'echelle 1,008)
    NOM_X, NOM_HAUT = 118.5, -21.0             # milieu du nom (depuis le bord gauche du cadre) et haut du texte du nom (depuis le haut du cadre : MenuMessage.m_who, 21 au-dessus) -- repli sans mise en page

    def __init__(self, larg=None, haut=None, onglet=None, x0=-223.0, z0=-251.0, win=(0.0, 10.0, 86.0), texte_ech=TEXTE_ECH):
        if larg: self.LARG = larg
        if haut: self.HAUT = haut
        if onglet: self.ONGLET_L, self.ONGLET_H = onglet
        self.x0, self.z0, self.win, self.texte_ech = x0, z0, tuple(win), texte_ech

    @classmethod
    def depuis(cls, ml):
        """Boite lue dans la mise en page d'origine (MiseEnPage) ; les valeurs mesurees si elle manque ou est inutilisable."""
        try:
            t = ml.message['types'][0]; vt = t['frame_mesh']['vtx']; xs = [v[0] for v in vt]; zs = [v[1] for v in vt]
            onglet = None
            if len(ml.cadres) > UM.CADRE_AVEC_NOM:
                c = ml.cadres[UM.CADRE_AVEC_NOM]['vtx']; hs = [v for v in c if v[1] > max(zs) + 0.5]
                if hs: onglet = (max(v[0] for v in hs) - min(v[0] for v in hs), max(v[1] for v in hs) - max(zs))
            return cls(max(xs) - min(xs), max(zs) - min(zs), onglet, min(xs), min(zs), t['win'])
        except Exception:
            return cls()

    MARGES = 120.0                              # (en unites de k) marges de la fenetre de l'historique autour de la boite : gauche, colonne de l'etoile, barre de defilement

    def echelle(self, H, W, k):
        """Pixels par unite : celle des fenetres du jeu (H / 800 x ECHELLE_BOITE), reduite pour que la boite, sa colonne d'etoile et les marges tiennent dans la fenetre de la visionneuse."""
        return max(0.3, min(H / 800.0 * ECHELLE_BOITE, (W - 40 * k - self.MARGES * k) / self.LARG))

    def base(self, rang):
        """Distance de la ligne de base de la ligne `rang` (0, 1, 2) au haut du cadre, unites."""
        return self.BASE_1 + rang * self.PAS

    def largeur_texte(self):
        """Largeur utile d'une ligne de texte (unites) : du bord gauche du texte a la marge droite du canevas (le canevas est large de LARG - 18)."""
        return self.LARG - self.TEXTE_X - 12.0


def paginer(rangees, avec_entete, lignes=3):
    """Rangees de texte -> pages de `lignes` rangees au plus (au moins une page, meme vide) ; sur la 1re page d'un combat, l'entete (issue et heure) prend une rangee."""
    pages = []; cap = max(1, lignes - (1 if avec_entete else 0)); i = 0
    while True:
        pages.append(list(rangees[i:i + cap])); i += cap; cap = lignes
        if i >= len(rangees): return pages


def rangees_de(e, mesure, largeur):
    """Rangees de texte d'un element, coupees a `largeur` (mesure(chaine) -> largeur dans la meme unite) : le texte d'un dialogue (ses retours a la ligne gardes) ; pour un combat les especes d'ennemis cote a cote
    (separees par une virgule, une espece n'est jamais coupee si elle tient seule) puis l'or et l'experience d'une victoire sur leur propre rangee (l'issue et l'heure sont dans l'entete)."""
    if e.type != HI.TYPE_COMBAT: return HI.envelopper(e.texte, largeur, mesure)
    brut = HI.lignes_combat(e); gain = brut[-1] if e.issue == 'victoire' else None
    especes = brut[:-1] if gain else brut; out = []; cur = ''
    for sp in especes:
        cand = sp if not cur else cur + ', ' + sp
        if cur and mesure(cand + ',') > largeur: out.append(cur + ','); cur = sp
        else: cur = cand
        if mesure(cur) > largeur: out.extend(HI.envelopper(cur, largeur, mesure)); cur = ''
    if cur: out.append(cur)
    if gain: out.append(gain)
    return out


class VueHistorique:
    def __init__(self, pause):
        self.P = pause; self.J = pause.J
        self.onglet = O_DIALOGUES; self.elements = []
        self.fin = 0; self.sel = 0; self.vis = 1                      # dernier element visible (en bas), element choisi au clavier, nombre d'elements visibles a la derniere image
        self.zones = []; self.zones_etoile = []; self.zones_onglet = []; self.barre = None; self.glisse_barre = None
        self.zone_ret = None
        self.favoris_seuls = False; self.zone_filtre = None             # case « Favoris seulement » : cochee ? ; sa zone a l'ecran (clic)
        self.drag = None                                               # glissement dans la liste : [y de depart, fin de depart, deplace ?]
        self._spr = {}; self._lignes = {}
        self._boite = None; self._boite_ml = None; self._fens = {}              # boite de dialogue standard (Boite) et les deux fenetres de message du jeu qui servent a dessiner son cadre (avec / sans onglet)

    # ---- donnees
    def entrer(self, onglet=O_DIALOGUES):
        """A l'ouverture de la page : recharge la liste (le moteur est arrete, elle ne change plus), en bas sur l'element le plus recent."""
        self.onglet = onglet if 0 <= onglet < len(ONGLETS) else O_DIALOGUES
        self.glisse_barre = None; self.drag = None; self._lignes.clear()
        self.recharger()

    def recharger(self, garder=False):
        h = getattr(self.J, 'historique', None)
        self.elements = h.liste(ONGLETS[self.onglet][1], self.favoris_seuls) if h is not None else []
        n = len(self.elements)
        if garder: self.fin = max(0, min(n - 1, self.fin)); self.sel = max(0, min(n - 1, self.sel))
        else: self.fin = self.sel = max(0, n - 1)
        self.zones = []; self.zones_etoile = []

    def changer_onglet(self, i):
        i %= len(ONGLETS)
        if i != self.onglet: self.onglet = i; self.recharger()

    def basculer_filtre(self):
        """Coche ou decoche « Favoris seulement » (valable pour les deux onglets). L'element choisi, s'il est dans la nouvelle liste, reste choisi ; sinon on se place sur le plus recent."""
        cur = self.courant(); cle = cur.cle() if cur is not None else None
        self.favoris_seuls = not self.favoris_seuls; self.recharger()
        if cle is not None:
            for i in range(len(self.elements) - 1, -1, -1):
                if self.elements[i].cle() == cle: self.aller(i); break
        return self.favoris_seuls

    def courant(self):
        return self.elements[self.sel] if 0 <= self.sel < len(self.elements) else None

    def etoile(self, i=None):
        """Met en favori (ou retire des favoris) l'element i (le choisi par defaut) ; -> True si c'est maintenant un favori. Avec « Favoris seulement », l'element retire disparait de la liste."""
        h = getattr(self.J, 'historique', None)
        if h is None: return False
        e = self.courant() if i is None else (self.elements[i] if 0 <= i < len(self.elements) else None)
        if e is None: return False
        r = h.basculer_favori(e)
        if self.favoris_seuls: self.recharger(garder=True)
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
        elif symbol == K.F or act == 'carte': self.basculer_filtre()                          # (F, ou la touche Carte : « Favoris seulement »)
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
        if self._dans(self.zone_filtre, x, y): self.basculer_filtre(); return
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

    def _boite_jeu(self):
        """Boite de dialogue standard (dimensions de la mise en page d'origine si elle est chargee) ; gardee."""
        r = getattr(self.J, 'ui_rendu', None); ml = getattr(r, 'ml', None)
        if self._boite is None or self._boite_ml is not ml: self._boite = Boite.depuis(ml) if ml is not None else Boite(); self._boite_ml = ml
        return self._boite

    def _pages_de(self, bm, e, B, s, taille):
        """Pages d'un element : liste de listes de rangees de texte (3 rangees au plus, l'entete d'un combat comprise). Gardees (cle : element, echelle)."""
        cle = (e.n, e.type, int(s * 100))
        r = self._lignes.get(cle)
        if r is None:
            if len(self._lignes) > 4000: self._lignes.clear()
            if bm: mes = lambda t: bm.largeur(t) * B.texte_ech
            else: mes = lambda t: self.P._et(t, taille).content_width * 0.9 / s
            r = self._lignes[cle] = paginer(rangees_de(e, mes, B.largeur_texte()), e.type == HI.TYPE_COMBAT, B.LIGNES)
        return r

    def _etoile(self, cx, cy, rayon, pleine):
        """Etoile de favori : doree quand l'element est en favori, grise et creuse sinon."""
        if pleine:
            pyglet.shapes.Star(cx, cy, rayon, rayon * 0.45, 5, rotation=0, color=ETOILE + (255,)).draw()
        else:
            pyglet.shapes.Star(cx, cy, rayon, rayon * 0.45, 5, rotation=0, color=GRIS + (255,)).draw()
            pyglet.shapes.Star(cx, cy, rayon * 0.6, rayon * 0.27, 5, rotation=0, color=VIDE_ETOILE + (255,)).draw()

    def _largeur_filtre(self, bm, sc, taille, k):
        """Largeur de la plaque de la case « Favoris seulement » : marge, case, marge, petite etoile, libelle, marge."""
        return 14 * k + 18 * k + 9 * k + 2 * 8 * k + 7 * k + self._larg(bm, LIBELLE_FILTRE, sc, taille) + 14 * k

    def _filtre(self, bm, sc, taille, asc, k, fx, ty, th):
        """Case a cocher « Favoris seulement » : une plaque a la hauteur des onglets, a droite du dernier onglet (le groupe onglets + case est centre dans la fenetre), avec la case, une petite etoile et le libelle ;
        doree quand elle est cochee. Sa zone (clic) est gardee dans `zone_filtre`."""
        P = self.P; cb = 18 * k; rs = 8 * k
        fw = self._largeur_filtre(bm, sc, taille, k)
        zone = (fx, ty, fx + fw, ty + th); self.zone_filtre = zone
        sur = (P._sur(zone) if hasattr(P, '_sur') else False) and P.mode_souris
        self._plaque(fx, ty, fw, th, k, sur)
        on = self.favoris_seuls; coul = OR if on else BLANC
        bx, by = fx + 14 * k, ty + (th - cb) / 2
        pyglet.shapes.Rectangle(bx, by, cb, cb, color=(0, 0, 0)).draw()
        for (xa, ya, xb, yb) in ((bx, by, bx + cb, by), (bx, by + cb, bx + cb, by + cb), (bx, by, bx, by + cb), (bx + cb, by, bx + cb, by + cb)):
            pyglet.shapes.Line(xa, ya, xb, yb, thickness=max(1.5, 1.6 * k), color=coul + (255,)).draw()
        if on:                                                                      # la coche (deux traits)
            pyglet.shapes.Line(bx + cb * 0.2, by + cb * 0.5, bx + cb * 0.42, by + cb * 0.22, thickness=max(2.0, 2.6 * k), color=OR + (255,)).draw()
            pyglet.shapes.Line(bx + cb * 0.42, by + cb * 0.22, bx + cb * 0.84, by + cb * 0.82, thickness=max(2.0, 2.6 * k), color=OR + (255,)).draw()
        ex = bx + cb + 9 * k + rs; ey = ty + th / 2
        pyglet.shapes.Star(ex, ey, rs * 1.15, rs * 0.5, 5, rotation=0, color=(ETOILE if on else GRIS) + (255,)).draw()
        self._ligne(bm, LIBELLE_FILTRE, ex + rs + 7 * k, ty + th / 2 - (asc * 0.37 if bm else 6 * k), sc, coul, taille)

    def _plaque(self, x, y, w, h, k, choisi):
        J = self.J; r = getattr(J, 'ui_rendu', None)
        if r is not None and r.plaque(x, y, w, h, (J.width, J.height), choisi, coin=14 * k): return
        HM.plaque(x, y, w, h, k, choisi, None)

    def _fenetre_boite(self, avec):
        """Fenetre de message du jeu (ui_menu.FenetreMessage) qui dessine le cadre d'une boite : avec l'onglet du nom (frameData 191) ou sans (192), sans le canevas ni le curseur de fin de page ; None si la mise en page
        d'origine n'est pas chargee (la boite est alors dessinee avec un cadre simple)."""
        f = self._fens.get(avec)
        if f is None:
            f = False
            r = getattr(self.J, 'ui_rendu', None); ml = getattr(r, 'ml', None)
            if ml is not None and getattr(ml, 'message', None):
                try:
                    g = UM.FenetreMessage(ml); g.regler(0, 0, False, 'x' if avec else '')
                    if g.avec_nom == avec:
                        g.N['canevas']['act'] = False; g.N['curseur']['act'] = False; f = g
                except Exception: f = False
            self._fens[avec] = f
        return f or None

    def _boite_dessin(self, B, bx, by, s, k, nom, choisi, bm, taille):
        """Cadre de la boite dont le coin bas gauche est (bx, by), a l'echelle s : le cadre du jeu (et l'onglet du nom avec son texte, comme le jeu les pose), sinon un cadre simple ; plus clair quand l'element est choisi."""
        J = self.J; r = getattr(J, 'ui_rendu', None); f = self._fenetre_boite(bool(nom)) if r is not None else None
        fait = False
        if f is not None:
            try:
                if nom: f.N['qui']['text']['text'] = nom
                r.dessiner([f], bx - (B.win[0] + B.x0) * s, by - (B.win[2] + B.z0) * s, s, (J.width, J.height)); fait = True
            except Exception: self._fens[bool(nom)] = False
        if not fait:                                                      # (repli : cadre noir translucide du menu et, pour un nom, un petit cadre collé en haut a gauche)
            HM.cadre(bx + 4 * s, by + 4 * s, (B.LARG - 8) * s, (B.HAUT - 8) * s, k, fond=(0, 0, 0), opacite=HM.OPACITE_JEU)
            if nom:
                HM.cadre(bx + 4 * s, by + (B.HAUT - 6) * s, (B.ONGLET_L - 8) * s, (B.ONGLET_H + 2) * s, k, fond=(0, 0, 0), opacite=HM.OPACITE_JEU)
                sc = s * B.texte_ech if bm else 1.0; lw = self._larg(bm, nom, sc, taille)
                self._ligne(bm, nom, bx + (B.NOM_X - 0.0) * s - lw / 2, by + (B.HAUT + 7) * s, sc, BLANC, taille)
        if choisi:
            v = pyglet.shapes.Rectangle(bx + 7 * s, by + 7 * s, (B.LARG - 14) * s, (B.HAUT - 14) * s, color=(255, 255, 255)); v.opacity = 38; v.draw()

    def _blocs(self, bm, B, s, taille, ly0, ly1, ecart, ecart_page):
        """Boites visibles, de bas en haut : (element, page, nombre de pages, y du bas, hauteur du cadre, hauteur de l'onglet, rangees de texte). Toutes les boites ont la MEME hauteur de cadre (celle de la boite de
        dialogue du jeu), que le texte tienne sur 1, 2 ou 3 rangees ; seul l'onglet du nom (premiere page d'un dialogue avec nom) s'y ajoute au-dessus. Met a jour `vis` (elements dont la premiere page est visible)."""
        blocs = []; y = ly0; i = min(self.fin, len(self.elements) - 1); plein = False
        while i >= 0 and not plein:                                               # de bas en haut : les pages d'un element de la derniere a la premiere ; chacune est une boite de la meme taille
            e = self.elements[i]; pages = self._pages_de(bm, e, B, s, taille); avec_nom = e.type == HI.TYPE_DIALOGUE and bool(e.nom)
            for p in range(len(pages) - 1, -1, -1):
                hn = B.ONGLET_H * s if (p == 0 and avec_nom) else 0.0; hb = B.HAUT * s
                if blocs and y + hb + hn > ly1: plein = True; break
                blocs.append((i, p, len(pages), y, hb, hn, pages[p])); y += hb + hn + (ecart if p == 0 else ecart_page)
            i -= 1
        self.vis = max(1, len({b[0] for b in blocs if b[1] == 0})); self._borner()
        return blocs

    def dessiner(self):
        J = self.J; P = self.P; W, H = J.width, J.height; k = max(0.75, H / 900.0)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        voile = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); voile.opacity = 90; voile.draw()
        bm = self._bm(); B = self._boite_jeu(); s = B.echelle(H, W, k)                      # s : pixels par unite d'interface = ceux d'une boite de dialogue du jeu
        su = max(0.8, min(2.4, H / 700.0)) if bm else 1.0; taille = 17 * k                  # su : un pixel de police du jeu = su pixels d'ecran (titre, onglets, aide) ; taille : police du systeme (repli)
        sc = s * B.texte_ech if bm else 1.0; taille_b = 20 * s                               # idem pour le texte des boites : comme dans le jeu (1,105 unite par pixel de police)
        asc = (bm.ascent * su) if bm else 18 * k
        kb = 1.1 * k; bw, bh = 64 * kb, 55.5 * kb
        lgs = [self._larg(bm, nom, su, taille) + 44 * k for nom, _ in ONGLETS]; tw = max(lgs + [120 * k]); gap = 10 * k
        larg_onglets = tw * len(ONGLETS) + gap * (len(ONGLETS) - 1); fw = self._largeur_filtre(bm, su, taille, k)
        larg_ligne = larg_onglets + 14 * k + fw                                                       # la ligne des onglets : les onglets puis la case « Favoris seulement »
        pw = min(W - 20 * k, max(B.LARG * s + B.MARGES * k, larg_ligne + 2 * 34 * k)); h = H - 2 * 30 * k - bh - 10 * k
        x0 = (W - pw) / 2; y1 = (H + h + bh + 10 * k) / 2; y0 = y1 - h
        HM.cadre(x0, y0, pw, h, k, fond=(0, 0, 0), opacite=HM.OPACITE_JEU)                # aussi transparent que les autres fenetres du jeu
        titre = 'Historique'
        wt = self._larg(bm, titre, su * 1.25, taille * 1.3)
        self._ligne(bm, titre, x0 + (pw - wt) / 2, y1 - 24 * k - asc * 1.25, su * 1.25, BLANC, taille * 1.3)
        # onglets (plaques du jeu : l'onglet ouvert est la plaque « choisie »)
        th = 34 * k; ty = y1 - 100 * k; self.zones_onglet = []                      # (sous le titre : ses plaques ne doivent pas le recouvrir)
        tx = x0 + (pw - larg_ligne) / 2
        for i, (nom, cle) in enumerate(ONGLETS):
            zx = tx + i * (tw + gap); zone = (zx, ty, zx + tw, ty + th); self.zones_onglet.append(zone + (i,))
            sur = (P._sur(zone) if hasattr(P, '_sur') else False) and P.mode_souris
            self._plaque(zx, ty, tw, th, k, i == self.onglet or sur)
            lf = self._larg(bm, nom, su, taille); self._ligne(bm, nom, zx + (tw - lf) / 2, ty + th / 2 - (asc * 0.37 if bm else 6 * k), su, OR if i == self.onglet else BLANC, taille)
        self._filtre(bm, su, taille, asc, k, tx + larg_onglets + 14 * k, ty, th)                  # case « Favoris seulement » (a droite des onglets)
        # aide (une ou deux lignes, selon la largeur de la fenetre)
        ks = (J.reg['touches'].get('historique') or [None])[0] if hasattr(J.reg, '__getitem__') else None
        kn = RG.nom_touche(ks) if ks else None
        aide = ['Haut / Bas : parcourir', 'Gauche / Droite : onglet', 'Entrée : favori ★', 'F : favoris seulement'] + (['%s : suite' % kn] if kn else []) + ['Échap : fermer']
        la_max = pw - 24 * k; mes_aide = lambda t: self._larg(bm, t, su * 0.72, taille * 0.72)
        lignes_aide = []; cur = ''
        for a in aide:
            cand = a if not cur else cur + '     ' + a
            if cur and mes_aide(cand) > la_max: lignes_aide.append(cur); cur = a
            else: cur = cand
        lignes_aide.append(cur)
        pas_aide = (bm.interligne * su * 0.72) if bm else 17 * k
        # zone de la liste : la boite (taille du jeu) a gauche, la colonne de l'etoile a sa droite, la barre de defilement au bord
        ecart, ecart_page = 12 * k, 4 * k
        groupe = B.LARG * s + 44 * k; lx0 = x0 + (pw - groupe) / 2; lx1 = lx0 + groupe; ly1 = ty - 14 * k; ly0 = y0 + 40 * k + (len(lignes_aide) - 1) * pas_aide
        self.zones = []; self.zones_etoile = []; self.barre = None
        n = len(self.elements)
        if not n:
            msg = (VIDES_FAVORIS if self.favoris_seuls else VIDES)[ONGLETS[self.onglet][1]]
            lm = self._larg(bm, msg, su, taille); self._ligne(bm, msg, x0 + max(20 * k, (pw - lm) / 2), (ly0 + ly1) / 2, su, GRIS, taille)
        else:
            mouse = P.mode_souris; blocs = self._blocs(bm, B, s, taille_b, ly0, ly1, ecart, ecart_page)
            haut_de = {}
            for b in blocs: haut_de[b[0]] = min(haut_de.get(b[0], b[1]), b[1])                    # page la plus haute montree de chaque element (la main du curseur n'y est dessinee qu'une fois)
            for (i, p, np_, yb, hb, hn, rangees) in blocs:
                e = self.elements[i]; nom = e.nom if (e.type == HI.TYPE_DIALOGUE and p == 0 and e.nom) else None
                zone = (lx0, yb, lx1, yb + hb + hn); self.zones.append(zone + (i,))
                choisi = (P._pointeur_dans(zone) and self.glisse_barre is None) if mouse else i == self.sel
                self._boite_dessin(B, lx0, yb, s, k, nom, choisi, bm, taille_b)                       # cadre du jeu (+ onglet et nom)
                if choisi and not mouse and p == haut_de[i]: P._curseur(x0 + 4 * k, yb + hb / 2, min(hb * 0.7, 28 * k))
                rang = 0
                if e.type == HI.TYPE_COMBAT and p == 0:                                # entete : l'issue du combat a gauche, l'heure de jeu a droite
                    base = yb + hb - B.base(0) * s; self._ligne(bm, HI.LIBELLE_ISSUE.get(e.issue, ''), lx0 + B.TEXTE_X * s, base, sc, OR, taille_b)
                    ht = heure_jeu(e.t); self._ligne(bm, ht, lx0 + (B.LARG - 14) * s - self._larg(bm, ht, sc * 0.8, taille_b * 0.8), base, sc * 0.8, AIDE, taille_b * 0.8); rang = 1
                for l in rangees:
                    self._ligne(bm, l, lx0 + B.TEXTE_X * s, yb + hb - B.base(rang) * s, sc, BLANC, taille_b); rang += 1
                rs = 11 * k; ex = lx0 + B.LARG * s + 22 * k; ey = yb + hb - (B.BASE_1 - 7) * s     # etoile dans la colonne a droite de la boite, a la hauteur de la 1re ligne
                z = (ex - rs * 1.3, ey - rs * 1.3, ex + rs * 1.3, ey + rs * 1.3); self.zones_etoile.append(z + (i,))
                self._etoile(ex, ey, rs * (1.15 if (mouse and P._pointeur_dans(z)) else 1.0), e.fav is not None)
                if np_ > 1:                                                          # page « 1/2 » sous l'etoile
                    t = '%d/%d' % (p + 1, np_); self._ligne(bm, t, ex - self._larg(bm, t, su * 0.72, taille * 0.72) / 2, ey - rs * 1.3 - 6 * k - (asc * 0.72 if bm else 12 * k), su * 0.72, AIDE, taille * 0.72)
            if n > self.vis: self.barre = P._barre_defilement(x0 + pw - 14 * k, ly1, ly0, n, self.vis, max(0, self.fin - self.vis + 1), k, self.glisse_barre is not None)
        for j, l in enumerate(lignes_aide):                                          # aide et bouton retour
            la = self._larg(bm, l, su * 0.72, taille * 0.72); self._ligne(bm, l, x0 + (pw - la) / 2, y0 + 14 * k + (len(lignes_aide) - 1 - j) * pas_aide, su * 0.72, AIDE, taille * 0.72)
        bx = x0 + pw - bw - 8 * k; by = y0 - 8 * k - bh; self.zone_ret = (bx, by, bx + bw, by + bh)
        P._bouton_retour(bx, by, bw, bh, P._sur(self.zone_ret))
