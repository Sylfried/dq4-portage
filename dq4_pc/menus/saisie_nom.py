"""Saisie du nom du heros (classe InputName de la couche Unity d'origine, ecran « Saisir un nom » de la creation d'un journal).

Dans le jeu, c'est Unity qui tient ce clavier : le moteur ouvre la fenetre de type 55 (port 15), envoie `[12,0,8]` (8 caracteres au plus) puis `[12,1,1]` (clavier visible) et attend :
  - OK : `[2, n]` puis les n octets UTF-8 du nom empaquetes deux par deux (petit-boutiste), envoyes a la MEME image (sinon le moteur plante) ;
  - Retour : `[1, -1, 32]` (touche B sur la fenetre).
Les jeux de caracteres sont ceux de InputName (cctor) pour la langue francaise : alphabet (minuscules / majuscules, + espace - , . ! ?) et lettres accentuees, en pages de 5 colonnes x 7 lignes.
Les positions exactes de l'original (origine de la grille, boutons de fonction) n'ont pas ete retrouvees dans le code : la disposition est dessinee ici dans le style des fenetres du jeu.
Le clavier de l'ordinateur sert aussi (tout caractere de la grille), comme la souris et les fleches + Entree."""
import time
import pyglet
from pyglet import gl

VIDE = '＠'                           # case vide de la grille (C_NA)
ALPHABET = ('abcdefghijklmnopqrstuvwxyz -,.!?' + VIDE * 3, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ -,.!?' + VIDE * 3)       # C_ALPHABET : minuscules, majuscules
ACCENTS = ('àáâäçèéêëìíîïñòóôöùúûüß' + VIDE * 12, 'ÀÁÂÄÇÈÉÊËÌÍÎÏÑÒÓÔÖÙÚÛÜß' + VIDE * 12)                      # C_AA
PAGES = (ALPHABET, ACCENTS)           # C_LOCALIZE
FONCTIONS = ('Alphabet', 'à À', 'Maj.', 'Suppr.', 'OK')                   # C_ALPHABET_ETC (non localise dans le jeu)
COLS, LIGNES = 5, 7
SE_BOUTON = 300                       # bruitage d'appui sur un bouton de menu (comme fenetre.SE_BOUTON)
N_GRILLE = COLS * LIGNES               # 35 cases ; puis 35 a 39 = boutons de fonction ; 40 = Retour
I_ALPHA, I_ACC, I_MAJ, I_SUPPR, I_OK, I_RETOUR = 35, 36, 37, 38, 39, 40
CARS = {c for p in PAGES for page in p for c in page if c != VIDE}      # caracteres acceptes au clavier

# disposition (unites d'interface, origine au centre de la colonne de 450 x 800, Y vers le haut)
CADRE = (-215.0, -345.0, 215.0, 330.0)
TITRE_Y = 292.0
FENTES_Y, FENTE_L, FENTE_H, FENTE_PAS = 238.0, 40.0, 46.0, 46.0
GRILLE_Y0, GRILLE_PAS_Y, GRILLE_PAS_X, CASE_L, CASE_H = 172.0, 45.0, 72.0, 64.0, 37.0
FONC_Y, FONC_PAS, FONC_L, FONC_H = -158.0, 83.0, 79.0, 40.0
RETOUR_L, RETOUR_H = 62.0, 52.0
BLANC = (255, 255, 255, 255); OR = (255, 235, 4, 255); GRIS = (128, 128, 128, 255); AIDE = (170, 170, 170, 255); ROUGE = (255, 90, 90, 255)
JAUNE = (255, 235, 4)


class SaisieNom:
    def __init__(self, jeu):
        self.J = jeu; self.actif = False; self.texte = ''; self.max = 8; self.mode = 0; self.maj = 0; self.cur = 0
        self.zones = []; self.souris = None; self.t0 = 0.0

    # ---- etat
    def ouvrir(self, maxi=8):
        self.actif = True; self.texte = ''; self.max = max(1, min(30, maxi)); self.mode = 0; self.maj = 0; self.cur = 0; self.t0 = time.time(); self.souris = None

    def fermer(self): self.actif = False

    def page(self): return PAGES[self.mode][self.maj]

    def _ajouter(self, c):
        if c == VIDE or len(self.texte.encode('utf-8')) + len(c.encode('utf-8')) > 30 or len(self.texte) >= self.max: return False
        self.texte += c; return True

    def _supprimer(self):
        if not self.texte: return False
        self.texte = self.texte[:-1]; return True

    def _valider(self):
        if self.texte: self.J._saisie_nom_ok(self.texte); return True
        return False

    def appuyer(self, i):
        """Appui sur la case i (grille, bouton de fonction ou Retour). -> vrai si quelque chose a change (son de bouton)."""
        if i < N_GRILLE: return self._ajouter(self.page()[i])
        if i == I_ALPHA: ok = self.mode != 0; self.mode = 0; return ok
        if i == I_ACC: ok = self.mode != 1; self.mode = 1; return ok
        if i == I_MAJ: self.maj ^= 1; return True
        if i == I_SUPPR: return self._supprimer()
        if i == I_OK: return self._valider()
        if i == I_RETOUR: self.J._saisie_nom_retour(); return True
        return False

    # ---- entrees
    def _pas(self, i, dx, dy):
        """Case voisine de i dans la direction (dx, dy ; dy > 0 = vers le haut) : la grille de 5 x 7, puis la rangee des boutons de fonction, puis Retour ; on boucle."""
        if i < N_GRILLE:
            r, c = divmod(i, COLS)
            if dx: return r * COLS + (c + dx) % COLS
            r -= dy
            return I_ALPHA + c if (r < 0 or r >= LIGNES) else r * COLS + c
        if i < I_RETOUR:
            f = i - I_ALPHA
            if dx: return I_ALPHA + (f + dx) % 5
            if dy > 0: return (LIGNES - 1) * COLS + f
            return I_RETOUR if f >= 3 else f                         # vers le bas : Retour (a droite) ou le haut de la grille
        return I_OK if dy > 0 else (I_ALPHA + 3 if dx < 0 else (I_ALPHA if dx > 0 else 0))

    def bouger(self, dx, dy):
        """Fleches : saute les cases vides de la page."""
        i = self.cur
        for _ in range(N_GRILLE + 2):
            i = self._pas(i, dx, dy)
            if i >= N_GRILLE or self.page()[i] != VIDE: break
        self.cur = i

    def touche(self, symbol, modifiers=0):
        """Touche physique. -> vrai si elle a ete prise (les lettres arrivent par texte())."""
        K = pyglet.window.key
        d = {K.LEFT: (-1, 0), K.RIGHT: (1, 0), K.UP: (0, 1), K.DOWN: (0, -1)}.get(symbol)
        if d: self.souris = None; self.bouger(*d); return True
        if symbol in (K.RETURN, K.ENTER):
            if self.appuyer(self.cur): self.J.son.jouer_se(SE_BOUTON)
            return True
        if symbol == K.BACKSPACE:
            if self._supprimer(): self.J.son.jouer_se(SE_BOUTON)
            return True
        if symbol == K.ESCAPE: self.J._saisie_nom_retour(); self.J.son.jouer_se(SE_BOUTON); return True
        if symbol == K.TAB: self.souris = None; self.mode = 1 - self.mode; return True
        return True                                             # le clavier est a la saisie : aucune autre touche n'agit sur le jeu

    def texte_saisi(self, t):
        """Caracteres tapes au clavier : ceux de la grille sont ajoutes (le curseur passe sur OK pour valider d'un Entree)."""
        for c in t:
            if c in CARS and self._ajouter(c): self.cur = I_OK; self.souris = None
        return True

    def clic(self, x, y, bouton):
        M = pyglet.window.mouse
        if bouton == M.RIGHT: self._supprimer() and self.J.son.jouer_se(SE_BOUTON); return
        for x0, y0, x1, y1, i in self.zones:
            if x0 <= x <= x1 and y0 <= y <= y1:
                self.cur = i; self.souris = i
                if self.appuyer(i): self.J.son.jouer_se(SE_BOUTON)
                return

    def survol(self, x, y):
        for x0, y0, x1, y1, i in self.zones:
            if x0 <= x <= x1 and y0 <= y <= y1:
                if self.souris != i: self.souris = i; self.cur = i
                return
        self.souris = None

    # ---- dessin
    def dessiner(self, cx, cy, ech):
        """(cx, cy, ech) : repere de la colonne d'interface (Jeu._ui_repere) ; la fenetre est reduite pour tenir dans la hauteur de l'ecran."""
        ech = min(ech, 0.97 * self.J.height / (CADRE[3] - CADRE[1]))
        P = self.J.pause; k = ech * 800.0 / 900.0
        U = lambda x, y: (cx + x * ech, cy + y * ech)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        x0, y0 = U(CADRE[0], CADRE[1]); x1, y1 = U(CADRE[2], CADRE[3]); P._cadre(x0, y0, x1 - x0, y1 - y0, k)
        def texte(t, x, y, taille, coul=BLANC, ancre=1):
            """Texte de `taille` unites de haut centre (ancre 1), a gauche (0) ou a droite (2) en (x, y) (unites)."""
            et = P._et(t, taille * ech * 0.75, coul); w = et.content_width; px, py = U(x, y)
            et.x = px - (w / 2 if ancre == 1 else (w if ancre == 2 else 0)); et.y = py - taille * ech * 0.30; et.draw()
        P._melange(); texte('Saisir un nom', 0, TITRE_Y, 26)
        # champ : une fente par caractere possible
        n = self.max; x_deb = -(n * FENTE_PAS - (FENTE_PAS - FENTE_L)) / 2
        t = time.time() - self.t0
        for j in range(n):
            xc = x_deb + j * FENTE_PAS + FENTE_L / 2; a, b = U(xc - FENTE_L / 2, FENTES_Y - FENTE_H / 2)
            r = pyglet.shapes.BorderedRectangle(a, b, FENTE_L * ech, FENTE_H * ech, border=max(1, int(1.5 * ech)), color=(14, 16, 22), border_color=(200, 200, 196) if j == len(self.texte) else (112, 114, 110)); r.draw()
            if j < len(self.texte): texte(self.texte[j], xc, FENTES_Y, 28)
            elif j == len(self.texte) and int(t * 2) % 2 == 0:
                u, v = U(xc - 10, FENTES_Y - FENTE_H / 2 + 6); pyglet.shapes.Rectangle(u, v, 20 * ech, max(2, 2.5 * ech), color=JAUNE).draw()
        P._melange()
        zones = []; page = self.page()
        mode_souris = self.J.dernier_peripherique == 'souris'       # dernier peripherique utilise : souris = encadrement jaune de la touche survolee ; clavier / manette = curseur dore (fleche) sur la touche choisie
        def bouton(i, xc, yc, w, h, etiquette, taille, enfonce=False, grise=False):
            a, b = U(xc - w / 2, yc - h / 2); sel = (i == self.cur) and not mode_souris; sur = mode_souris and self.souris == i
            P._plaque(a, b, w * ech, h * ech, k, enfonce or sel or sur)                  # (souris : la plaque sous le pointeur s'assombrit, sans encadre jaune)
            if sel: P._curseur(max(a - 24 * ech, U(CADRE[0] + 3, 0)[0]), b + h * ech / 2, 28 * ech)          # (la fleche ne sort pas du cadre : « Alphabet » est collee a son bord)
            P._melange(); texte(etiquette, xc, yc, taille, GRIS if grise else BLANC)
            zones.append((a, b, a + w * ech, b + h * ech, i))
        for i in range(N_GRILLE):
            r, c = divmod(i, COLS); ch = page[i]
            if ch == VIDE: continue
            bouton(i, (c - 2) * GRILLE_PAS_X, GRILLE_Y0 - r * GRILLE_PAS_Y, CASE_L, CASE_H, ch if ch != ' ' else '␣', 22, False, len(self.texte) >= self.max)
        for f, lib in enumerate(FONCTIONS):
            i = I_ALPHA + f; actif = (f == 0 and self.mode == 0) or (f == 1 and self.mode == 1) or (f == 2 and self.maj == 1)
            bouton(i, (f - 2) * FONC_PAS, FONC_Y, FONC_L, FONC_H, lib, 16, actif, f == 4 and not self.texte)
        a, b = U(CADRE[2] - RETOUR_L - 14, CADRE[1] + 12); w, h = RETOUR_L * ech, RETOUR_H * ech
        sur = mode_souris and self.souris == I_RETOUR; sel = self.cur == I_RETOUR and not mode_souris
        P._bouton_retour(a, b, w, h, sel or sur)
        if sel: P._curseur(a - 24 * ech, b + h / 2, 28 * ech)
        zones.append((a, b, a + w, b + h, I_RETOUR)); self.zones = zones
        P._melange(); texte('Clavier : taper le nom', CADRE[0] + 18, CADRE[1] + 44, 13, AIDE, 0); texte('Entrée : valider · Échap : retour', CADRE[0] + 18, CADRE[1] + 26, 13, AIDE, 0)
