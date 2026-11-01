"""Ce que la couche Unity du jeu fait AVANT la partie : logos d'entree, « Touchez l'ecran » du titre, ressources.

Tout vient du code d'origine (Boot, TapToStart, ApplicationQuit... de libil2cpp.so, relu par instruction : valeurs et adresses dans docs/notes-technique-portage-dq4.md,
section « Avant la partie »). Ce module ne depend ni du moteur ni d'OpenGL en dehors du dessin des images (pyglet.sprite)."""
import os
import pyglet

# fichiers du cache -> (archive, type d'objet Unity, nom de la ressource)
RESSOURCES = {
    'ap_sqex.png': ('base', 'Texture2D', 'sqex'),                      # logo SQUARE ENIX (Boot.m_logoTexture[1])
    'ap_arte.png': ('base', 'Texture2D', 'arte_logo720_240'),          # logo ArtePiazza (Boot.m_logoTexture[2])
    'ap_taptostart.png': ('pack', 'Texture2D', 'taptostart'),         # « Touchez l'ecran » (Resources/Title/TapToStart)
    'ap_copyright.png': ('pack', 'Texture2D', 'Retro4_copyright'),    # ligne de copyright du titre (Resources/Title/Retro4_copyright)
    'ap_licence.txt': ('pack', 'TextAsset', 'License_list_A'),         # texte de l'ecran Licence (variante Android)
    'ap_hyodai1.png': ('pack', 'Texture2D', 'hyodai1'),               # bandeau des titres de chapitre (Menu/map/hyodai1, 256 x 128, Make_Chapter)
}

# ---- Boot.Logo (MoveNext 0xCC5618) : constantes de la classe Boot
LOGO_ENTREE, LOGO_MAINTIEN, LOGO_SORTIE = 1.0, 3.0, 1.0          # c_fadeTime, c_waitTime, c_fadeTime (secondes reelles : Time.deltaTime)
LOGO_COTE = 450.0                                                  # le quad du logo est un carre de 450 unites (texture 720 x 720), centre, dans l'interface de 450 x 800

# ---- TapToStart (classe d'interface du port 12, type 73) : constantes du dump
TT_ACC, TT_ATTENTE, TT_PREMIER = 0.025, 20, 720                    # c_acc, c_cwait, c_firstWait (images)
TT_L, TT_H, TT_BAS = 223.04001, 41.48, 228.0                       # c_width, c_height ; centre 228 unites SOUS le centre de l'ecran
CP_PREMIER, CP_SECOND, CP_ACC = 690, 2508, 0.0625                  # c_copyrightFirstWait, c_copyrightSecondWait, c_copyrightAcc
CP_L, CP_H, CP_HAUT = 450.0, 40.0005, 25.0003                      # c_copyrightWidth / Height ; centre a 25 unites au-dessus du bord bas


def preparer(dossier_apk, cache, log=print):
    """Extrait des APK (une seule fois) les images et le texte propres a l'avant-partie. -> True si tout est dans le cache. Sans UnityPy ou sans APK : False (le jeu s'en passe)."""
    dest = {n: os.path.join(cache, n) for n in RESSOURCES}
    manque = [n for n, p in dest.items() if not os.path.exists(p)]
    if not manque: return True
    try:
        import UnityPy, zipfile
        os.makedirs(cache, exist_ok=True)
        log('Lecture des images du titre (une seule fois)...')
        archives = {}
        for cle in {RESSOURCES[n][0] for n in manque}:
            if cle == 'base': archives[cle] = UnityPy.load(os.path.join(dossier_apk, 'base.apk'))
            else: archives[cle] = UnityPy.load(zipfile.ZipFile(os.path.join(dossier_apk, 'split_UnityDataAssetPack.apk')).read('assets/bin/Data/datapack.unity3d'))
        for fich in manque:
            cle, genre, nom = RESSOURCES[fich]
            for o in archives[cle].objects:
                if o.type.name != genre: continue
                d = o.read()
                if d.m_Name != nom: continue
                if genre == 'Texture2D': d.image.convert('RGBA').save(dest[fich])
                else:
                    raw = d.m_Script; open(dest[fich], 'wb').write(raw.encode('utf-8', 'surrogateescape') if isinstance(raw, str) else bytes(raw))
                break
        return all(os.path.exists(p) for p in dest.values())
    except Exception as ex:
        log('Images du titre indisponibles : %r' % (ex,)); return False


def chemins(cache):
    """Chemins du cache -> dict nom court -> chemin (seulement ceux qui existent)."""
    return {n[3:].rsplit('.', 1)[0]: os.path.join(cache, n) for n in RESSOURCES if os.path.exists(os.path.join(cache, n))}


class Logos:
    """Boot.Logo : un logo apres l'autre, sur fond noir. Entree en fondu (1 s), maintien (3 s), sortie en fondu (1 s). Un toucher pendant l'entree saute le maintien,
    pendant le maintien il lance la sortie tout de suite. Francais / anglais : SQUARE ENIX puis ArtePiazza (l'avertissement japonais n'est montre qu'en langue 0)."""
    def __init__(self, fichiers):
        self.liste = [fichiers[n] for n in ('sqex', 'arte') if n in fichiers]
        self.i = 0; self.phase = 0; self.t = 0.0; self.alpha = 0.0; self.saute = False; self.sprites = {}
    @property
    def fini(self): return self.i >= len(self.liste)
    @property
    def ok(self): return bool(self.liste)

    def toucher(self):
        """Un appui (clic, touche) : saute le maintien du logo courant."""
        if self.fini: return
        if self.phase == 0: self.saute = True
        elif self.phase == 1: self.phase = 2; self.t = 0.0

    def maj(self, dt):
        """Avance de dt secondes reelles."""
        if self.fini: return
        self.t += dt
        if self.phase == 0:
            self.alpha = min(1.0, self.t / LOGO_ENTREE)
            if self.t >= LOGO_ENTREE:
                self.alpha = 1.0; self.t = 0.0; self.phase = 2 if self.saute else 1; self.saute = False
        elif self.phase == 1:
            if self.t >= LOGO_MAINTIEN: self.phase = 2; self.t = 0.0
        else:
            self.alpha = max(0.0, 1.0 - self.t / LOGO_SORTIE)
            if self.t >= LOGO_SORTIE: self.i += 1; self.phase = 0; self.t = 0.0; self.alpha = 0.0; self.saute = False

    def dessiner(self, largeur, hauteur):
        """Carre de 450 unites (hauteur de la fenetre = 800 unites) au centre de l'ecran, fusion alpha."""
        if self.fini: return
        import pyglet
        sp = self.sprites.get(self.i)
        if sp is None:
            img = pyglet.image.load(self.liste[self.i]); sp = self.sprites[self.i] = pyglet.sprite.Sprite(img)
        cote = LOGO_COTE * hauteur / 800.0
        sp.update(x=(largeur - cote) / 2, y=(hauteur - cote) / 2, scale_x=cote / sp.image.width, scale_y=cote / sp.image.height)
        sp.opacity = int(round(255 * self.alpha)); sp.draw()


class TitreTouch:
    """TapToStart (type 73 du port 12) : « Touchez l'ecran » qui clignote et ligne de copyright. Compte des images de jeu (30 Hz).
    Sans le message CountReset du moteur (code 0), le premier affichage n'a lieu qu'apres 720 images ; avec, il demarre tout de suite et le copyright reste plein."""
    def __init__(self, image0, fichiers):
        self.debut = image0; self.acc = TT_ACC; self.alpha = 0.0; self.premier = True; self.attente = TT_PREMIER
        self.alpha_c = 0.0; self.etat_c = 0; self.sprites = {}; self.fichiers = fichiers

    def reset(self):
        """TapToStart.CountReset : le moteur annonce la fin de la premiere phase du titre."""
        if self.premier: self.attente = 0
        self.etat_c = 5; self.alpha_c = 1.0

    def maj(self, image):
        """Une image de jeu (TapToStart.Update, une fois par image rendue)."""
        f = image - self.debut
        if f >= self.attente:
            self.premier = False; self.alpha += self.acc
            if self.alpha > 1.0 or self.alpha < 0.0:
                self.attente = f + TT_ATTENTE; self.alpha = 1.0 if self.acc > 0 else 0.0; self.acc = -self.acc
        c = self.etat_c
        if c == 0 and f >= CP_PREMIER: self.etat_c = 1
        elif c == 1:
            self.alpha_c = min(1.0, self.alpha_c + CP_ACC)
            if self.alpha_c >= 1.0: self.etat_c = 2
        elif c == 2 and f >= CP_SECOND: self.etat_c = 3
        elif c == 3:
            self.alpha_c = max(0.0, self.alpha_c - CP_ACC)
            if self.alpha_c <= 0.0: self.etat_c = 4

    def dessiner(self, cx, cy, ech, hauteur):
        """(cx, cy, ech) = repere de la colonne d'interface (voir Jeu._ui_repere) ; hauteur = hauteur de la fenetre."""
        import pyglet
        for nom, alpha, w, h, x, y in (('taptostart', self.alpha, TT_L, TT_H, cx, cy - TT_BAS * ech), ('copyright', self.alpha_c, CP_L, CP_H, cx, CP_HAUT * ech)):
            if alpha <= 0.001 or nom not in self.fichiers: continue
            sp = self.sprites.get(nom)
            if sp is None: sp = self.sprites[nom] = pyglet.sprite.Sprite(pyglet.image.load(self.fichiers[nom]))
            sp.update(x=x - w * ech / 2, y=y - h * ech / 2, scale_x=w * ech / sp.image.width, scale_y=h * ech / sp.image.height)
            sp.opacity = int(round(255 * min(1.0, alpha))); sp.draw()


# ---- Ecran « Licence » (type 80, Make_License / LicensePolicy / LicenseNobu)
URL_CONFIDENTIALITE = 'https://square-enix-games.com/en_US/documents/privacy'       # LicensePolicy.OnMouseUpAsButton : langue != 0 (le japonais ouvre https://www.jp.square-enix.com/privacy/)
LI_CADRE = (-215.0, -345.0, 215.0, 330.0)
LI_TEXTE = (-198.0, -262.0, 186.0, 272.0)                  # zone du texte (x0, y0, x1, y1), unites d'interface
LI_POLITIQUE = (-198.0, -334.0, 90.0, -284.0)              # bouton « Privacy Policy »
LI_RETOUR = (136.0, -337.0, 198.0, -285.0)
LI_TITRE_Y = 302.0


class Licence:
    """Texte des licences (TextAsset Menu/License_list_A) dans une fenetre defilante, avec les titres <color=orange> en orange. Les positions exactes de la fenetre de l'original n'ont pas ete retrouvees
    (elles dependent du rapport hauteur/largeur de l'ecran) : disposition dessinee ici, defilement a la molette, aux fleches, PageHaut/PageBas, ou en glissant la barre."""
    def __init__(self, chemin):
        import re
        self.mise = None; self.zones = []; self.haut = 0.0; self.glisse = None; self.zone_barre = None; self.survol = None; self.geom = None
        txt = open(chemin, 'rb').read().decode('utf-8', 'replace').replace('\r\n', '\n').replace('\ufeff', '') if chemin else 'Texte des licences indisponible.'
        self.plan = []; out = []; n = 0; orange = False
        for m in re.split(r'(<color=orange>|</color>)', txt):
            if m == '<color=orange>': orange = True
            elif m == '</color>': orange = False
            elif m: self.plan.append((n, n + len(m), orange)); out.append(m); n += len(m)
        self.texte = ''.join(out)

    def _mise(self, J, ech):
        """TextLayout pyglet de la fenetre (recree si l'echelle change)."""
        cle = round(ech, 3)
        if self.mise is not None and self.mise[0] == cle: return self.mise[1]
        P = J.pause; P._et('x', 10)                                                                     # (enregistre la police du jeu)
        taille = 11.0 * ech * 0.75; larg = int((LI_TEXTE[2] - LI_TEXTE[0]) * ech); haut = int((LI_TEXTE[3] - LI_TEXTE[1]) * ech)
        polices = tuple(P._pol or ()) + ('Consolas', 'DejaVu Sans Mono', 'Courier New')
        doc = pyglet.text.document.FormattedDocument(self.texte)
        doc.set_style(0, len(self.texte), dict(font_name=polices, font_size=taille, color=(235, 235, 235, 255)))
        for a, b, o in self.plan:
            if o: doc.set_style(a, b, dict(color=(255, 160, 40, 255)))
        lay = pyglet.text.layout.ScrollableTextLayout(doc, width=larg, height=haut, multiline=True)
        self.mise = (cle, lay); return lay

    def maximum(self):
        lay = self.mise[1] if self.mise else None
        return max(0.0, lay.content_height - lay.height) if lay else 0.0

    def defiler(self, delta):
        self.haut = min(self.maximum(), max(0.0, self.haut + delta))

    def sur_barre(self, x, y):
        zb = self.zone_barre
        return zb is not None and self.maximum() > 0 and zb[0] <= x <= zb[2] and zb[1] <= y <= zb[3]

    def glisser(self, y):
        """Le curseur de la barre suit le pointeur (LicenseNobu : position du curseur -> proportion du texte) ; y en pixels (pyglet, vers le haut)."""
        if self.geom is None: return
        by0, bh, th = self.geom; libre = bh - th
        if libre <= 0: return
        self.haut = min(1.0, max(0.0, (by0 + bh - th / 2 - y) / libre)) * self.maximum()

    def dessiner(self, J, cx, cy, ech):
        pg = pyglet; from pyglet import gl as g
        P = J.pause; k = ech * 800.0 / 900.0
        ech = min(ech, 0.97 * J.height / (LI_CADRE[3] - LI_CADRE[1])); k = ech * 800.0 / 900.0
        U = lambda x, y: (cx + x * ech, cy + y * ech)
        g.glDisable(g.GL_DEPTH_TEST); g.glEnable(g.GL_BLEND); g.glBlendFunc(g.GL_SRC_ALPHA, g.GL_ONE_MINUS_SRC_ALPHA)
        x0, y0 = U(LI_CADRE[0], LI_CADRE[1]); x1, y1 = U(LI_CADRE[2], LI_CADRE[3]); P._cadre(x0, y0, x1 - x0, y1 - y0, k)
        P._melange()
        et = P._et('Licence', 24 * ech * 0.75); et.x = cx - et.content_width / 2; et.y = cy + LI_TITRE_Y * ech - 9 * ech; et.draw()
        lay = self._mise(J, ech); self.haut = min(self.haut, self.maximum())
        tx, ty = U(LI_TEXTE[0], LI_TEXTE[1]); lay.x = int(tx); lay.y = int(ty); lay.view_y = -int(self.haut); lay.draw()
        # barre de defilement
        bx0, by0 = U(LI_TEXTE[2] + 4, LI_TEXTE[1]); bw, bh = 8 * ech, (LI_TEXTE[3] - LI_TEXTE[1]) * ech; m = self.maximum()
        pg.shapes.Rectangle(bx0, by0, bw, bh, color=(34, 36, 42)).draw()
        if m > 0:
            th = max(26 * ech, bh * lay.height / lay.content_height); hau = by0 + bh - th - (bh - th) * (self.haut / m)
            P._plaque(bx0 - 1, hau, bw + 2, th, k * 0.6, self.glisse is not None); self.geom = (by0, bh, th)
        self.zone_barre = (bx0 - 4, by0, bx0 + bw + 4, by0 + bh)
        px0, py0 = U(LI_POLITIQUE[0], LI_POLITIQUE[1]); px1, py1 = U(LI_POLITIQUE[2], LI_POLITIQUE[3])
        P._plaque(px0, py0, px1 - px0, py1 - py0, k, False, (255, 235, 4) if self.survol == 'politique' else None); P._melange()
        e2 = P._et('Privacy Policy', 16 * ech * 0.75); e2.x = (px0 + px1) / 2 - e2.content_width / 2; e2.y = (py0 + py1) / 2 - 5 * ech; e2.draw()
        rx0, ry0 = U(LI_RETOUR[0], LI_RETOUR[1]); rx1, ry1 = U(LI_RETOUR[2], LI_RETOUR[3])
        P._bouton_retour(rx0, ry0, rx1 - rx0, ry1 - ry0, self.survol == 'retour')
        self.zones = [(px0, py0, px1, py1, 'politique'), (rx0, ry0, rx1, ry1, 'retour')]

    def zone(self, x, y):
        for a, b, c, d, nom in self.zones:
            if a <= x <= c and b <= y <= d: return nom
        return None
