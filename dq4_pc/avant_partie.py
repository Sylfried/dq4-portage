"""Ce que la couche Unity du jeu fait AVANT la partie : logos d'entree, « Touchez l'ecran » du titre, ressources.

Tout vient du code d'origine (Boot, TapToStart, ApplicationQuit... de libil2cpp.so, relu par instruction : valeurs et adresses dans docs/notes-technique-portage-dq4.md,
section « Avant la partie »). Ce module ne depend ni du moteur ni d'OpenGL en dehors du dessin des images (pyglet.sprite)."""
import os

# fichiers du cache -> (archive, type d'objet Unity, nom de la ressource)
RESSOURCES = {
    'ap_sqex.png': ('base', 'Texture2D', 'sqex'),                      # logo SQUARE ENIX (Boot.m_logoTexture[1])
    'ap_arte.png': ('base', 'Texture2D', 'arte_logo720_240'),          # logo ArtePiazza (Boot.m_logoTexture[2])
    'ap_taptostart.png': ('pack', 'Texture2D', 'taptostart'),         # « Touchez l'ecran » (Resources/Title/TapToStart)
    'ap_copyright.png': ('pack', 'Texture2D', 'Retro4_copyright'),    # ligne de copyright du titre (Resources/Title/Retro4_copyright)
    'ap_licence.txt': ('pack', 'TextAsset', 'License_list_A'),         # texte de l'ecran Licence (variante Android)
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
