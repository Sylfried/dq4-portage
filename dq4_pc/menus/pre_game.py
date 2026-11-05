"""Ce que la couche Unity du jeu fait AVANT la partie : logos d'entree, « Touchez l'ecran » du titre, ressources.

Tout vient du code d'origine (Boot, TapToStart, ApplicationQuit... de libil2cpp.so, relu par instruction : valeurs et adresses dans docs/technical-notes-dq4-port.md,
section « Avant la partie »). Ce module ne depend ni du moteur ni d'OpenGL en dehors du dessin des images (pyglet.sprite)."""
import os
import pyglet
from dq4_pc.language import tr, N_

# fichiers du cache -> (archive, type d'objet Unity, nom de la ressource)
RESOURCES = {
    'ap_sqex.png': ('base', 'Texture2D', 'sqex'),                      # logo SQUARE ENIX (Boot.m_logoTexture[1])
    'ap_arte.png': ('base', 'Texture2D', 'arte_logo720_240'),          # logo ArtePiazza (Boot.m_logoTexture[2])
    'ap_taptostart.png': ('pack', 'Texture2D', 'taptostart'),         # « Touchez l'ecran » (Resources/Title/TapToStart)
    'ap_copyright.png': ('pack', 'Texture2D', 'Retro4_copyright'),    # ligne de copyright du titre (Resources/Title/Retro4_copyright)
    'ap_licence.txt': ('pack', 'TextAsset', 'License_list_A'),         # texte de l'ecran Licence (variante Android)
    'ap_hyodai1.png': ('pack', 'Texture2D', 'hyodai1'),               # bandeau des titres de chapitre (Menu/map/hyodai1, 256 x 128, Make_Chapter)
}

# ---- Boot.Logo (MoveNext 0xCC5618) : constantes de la classe Boot
LOGO_FADE_IN, LOGO_HOLD, LOGO_FADE_OUT = 1.0, 3.0, 1.0          # c_fadeTime, c_waitTime, c_fadeTime (secondes reelles : Time.deltaTime)
LOGO_SIDE = 450.0                                                  # le quad du logo est un carre de 450 unites (texture 720 x 720), centre, dans l'interface de 450 x 800

# ---- TapToStart (classe d'interface du port 12, type 73) : constantes du dump
TT_ACC, TT_WAIT, TT_FIRST_WAIT = 0.025, 20, 720                    # c_acc, c_cwait, c_firstWait (images)
TT_L, TT_H, TT_BOTTOM = 223.04001, 41.48, 228.0                       # c_width, c_height ; centre 228 unites SOUS le centre de l'ecran
CP_FIRST, CP_SECOND, CP_ACC = 690, 2508, 0.0625                  # c_copyrightFirstWait, c_copyrightSecondWait, c_copyrightAcc
CP_L, CP_H, CP_TOP = 450.0, 40.0005, 25.0003                      # c_copyrightWidth / Height ; centre a 25 unites au-dessus du bord bas


# ---- Logo du titre : ECART VOULU avec l'APK (demande de Sylfried, 03/11/2026, issue #108 : « doubler la taille du logo et du sous-titre »)
# Le logo est un maillage du moteur (paquets 21 / 22, carte `ev01`) : modele 8901 = « DRAGON QUEST » + « IV » + « TM » + sous-titre (« L'epopee des Elus »), modele 8900 = l'eclat anime sur le logo ;
# tous deux a la meme position (0, 1, 0), sommets en coordonnees locales du panneau (x vers la droite de la camera, mirroir d'Unity, y vers le haut), x de -4,549 a 4,549 pour « DRAGON QUEST ».
LOGO_MODELS = (8900, 8901)
LOGO_SCALE = 1.5                     # facteur d'agrandissement voulu (1 = l'APK) : 2 d'abord (#108, 19 h 38), ramene a 1,5 sur demande de Sylfried (21 h 05)
LOGO_HALF_WIDTH = 4.549              # demi-largeur locale de « DRAGON QUEST » (lue sur les sommets du paquet 22)
LOGO_Y_FIXED = 0.70                     # ordonnee locale du point qui ne bouge pas : le logo grandit autour de ce point (ce qui le laisse au-dessus de « Touchez l'ecran » et sous le haut de l'ecran ; voir notes)
LOGO_WIDTH_MARGIN = 0.96              # le logo agrandi ne depasse jamais 96 % de la largeur de la fenetre (fenetre tres etroite) ; il ne devient jamais plus petit que celui de l'APK


def logo_factor(original_width, desired=LOGO_SCALE, margin=LOGO_WIDTH_MARGIN):
    """Facteur d'agrandissement du logo : `desired`, reduit (jusqu'a 1) pour que le logo agrandi tienne dans `margin` de la largeur de la fenetre. `original_width` = largeur du logo
    de l'APK en fraction de la largeur de la fenetre (0 a 1)."""
    if original_width <= 0.0: return max(1.0, desired)             # largeur non mesurable : on applique le facteur voulu tel quel
    return max(1.0, min(desired, margin / original_width))


def upscale_logo(loc, factor, y_fixed=LOGO_Y_FIXED):
    """Sommets locaux (n, 3 : x, y, profondeur) du logo agrandis de `factor` autour du point (0, y_fixed) du panneau : x et y changent, la profondeur (ordre de dessin des couches du panneau : eclat devant le logo, etc.)
    reste celle du moteur. Renvoie un nouveau tableau."""
    import numpy as np
    output = np.array(loc, np.float32, copy=True)
    output[:, 0] *= factor
    output[:, 1] = y_fixed + factor * (output[:, 1] - y_fixed)
    return output


def prepare(apk_folder, cache, log=print):
    """Extrait des APK (une seule fois) les images et le texte propres a l'avant-partie. -> True si tout est dans le cache. Sans UnityPy ou sans APK : False (le jeu s'en passe)."""
    dest = {n: os.path.join(cache, n) for n in RESOURCES}
    missing = [n for n, p in dest.items() if not os.path.exists(p)]
    if not missing: return True
    try:
        import UnityPy, zipfile
        os.makedirs(cache, exist_ok=True)
        log(tr('Lecture des images du titre (une seule fois)...'))
        archives = {}
        for lookup_key in {RESOURCES[n][0] for n in missing}:
            if lookup_key == 'base': archives[lookup_key] = UnityPy.load(os.path.join(apk_folder, 'base.apk'))
            else: archives[lookup_key] = UnityPy.load(zipfile.ZipFile(os.path.join(apk_folder, 'split_UnityDataAssetPack.apk')).read('assets/bin/Data/datapack.unity3d'))
        for file_name in missing:
            lookup_key, kind, name_str = RESOURCES[file_name]
            for o in archives[lookup_key].objects:
                if o.type.name != kind: continue
                d = o.read()
                if d.m_Name != name_str: continue
                if kind == 'Texture2D': d.image.convert('RGBA').save(dest[file_name])
                else:
                    raw = d.m_Script; open(dest[file_name], 'wb').write(raw.encode('utf-8', 'surrogateescape') if isinstance(raw, str) else bytes(raw))
                break
        return all(os.path.exists(p) for p in dest.values())
    except Exception as ex:
        log(tr('Images du titre indisponibles : %r') % (ex,)); return False


def paths(cache):
    """Chemins du cache -> dict nom court -> chemin (seulement ceux qui existent)."""
    return {n[3:].rsplit('.', 1)[0]: os.path.join(cache, n) for n in RESOURCES if os.path.exists(os.path.join(cache, n))}


class Logos:
    """Boot.Logo : un logo apres l'autre, sur fond noir. Entree en fondu (1 s), maintien (3 s), sortie en fondu (1 s). Un toucher pendant l'entree saute le maintien,
    pendant le maintien il lance la sortie tout de suite. Francais / anglais : SQUARE ENIX puis ArtePiazza (l'avertissement japonais n'est montre qu'en langue 0)."""
    def __init__(self, files):
        self.entries = [files[n] for n in ('sqex', 'arte') if n in files]
        self.i = 0; self.phase = 0; self.t = 0.0; self.alpha = 0.0; self.skip = False; self.sprites = {}
    @property
    def finished(self): return self.i >= len(self.entries)
    @property
    def ok(self): return bool(self.entries)

    def touch(self):
        """Un appui (clic, touche) : saute le maintien du logo courant."""
        if self.finished: return
        if self.phase == 0: self.skip = True
        elif self.phase == 1: self.phase = 2; self.t = 0.0

    def do_update(self, dt):
        """Avance de dt secondes reelles."""
        if self.finished: return
        self.t += dt
        if self.phase == 0:
            self.alpha = min(1.0, self.t / LOGO_FADE_IN)
            if self.t >= LOGO_FADE_IN:
                self.alpha = 1.0; self.t = 0.0; self.phase = 2 if self.skip else 1; self.skip = False
        elif self.phase == 1:
            if self.t >= LOGO_HOLD: self.phase = 2; self.t = 0.0
        else:
            self.alpha = max(0.0, 1.0 - self.t / LOGO_FADE_OUT)
            if self.t >= LOGO_FADE_OUT: self.i += 1; self.phase = 0; self.t = 0.0; self.alpha = 0.0; self.skip = False

    def draw_all(self, width_px, height_px):
        """Carre de 450 unites (hauteur de la fenetre = 800 unites) au centre de l'ecran, fusion alpha."""
        if self.finished: return
        import pyglet
        sp = self.sprites.get(self.i)
        if sp is None:
            img = pyglet.image.load(self.entries[self.i]); sp = self.sprites[self.i] = pyglet.sprite.Sprite(img)
        side = LOGO_SIDE * height_px / 800.0
        sp.update(x=(width_px - side) / 2, y=(height_px - side) / 2, scale_x=side / sp.image.width, scale_y=side / sp.image.height)
        sp.opacity = int(round(255 * self.alpha)); sp.draw()


class TitleTouch:
    """TapToStart (type 73 du port 12) : « Touchez l'ecran » qui clignote et ligne de copyright. Compte des images de jeu (30 Hz).
    Sans le message CountReset du moteur (code 0), le premier affichage n'a lieu qu'apres 720 images ; avec, il demarre tout de suite et le copyright reste plein."""
    def __init__(self, image0, files):
        self.begin = image0; self.acc = TT_ACC; self.alpha = 0.0; self.first = True; self.waiting = TT_FIRST_WAIT
        self.alpha_c = 0.0; self.state_c = 0; self.sprites = {}; self.files = files

    def reset(self):
        """TapToStart.CountReset : le moteur annonce la fin de la premiere phase du titre."""
        if self.first: self.waiting = 0
        self.state_c = 5; self.alpha_c = 1.0

    def do_update(self, image):
        """Une image de jeu (TapToStart.Update, une fois par image rendue)."""
        f = image - self.begin
        if f >= self.waiting:
            self.first = False; self.alpha += self.acc
            if self.alpha > 1.0 or self.alpha < 0.0:
                self.waiting = f + TT_WAIT; self.alpha = 1.0 if self.acc > 0 else 0.0; self.acc = -self.acc
        c = self.state_c
        if c == 0 and f >= CP_FIRST: self.state_c = 1
        elif c == 1:
            self.alpha_c = min(1.0, self.alpha_c + CP_ACC)
            if self.alpha_c >= 1.0: self.state_c = 2
        elif c == 2 and f >= CP_SECOND: self.state_c = 3
        elif c == 3:
            self.alpha_c = max(0.0, self.alpha_c - CP_ACC)
            if self.alpha_c <= 0.0: self.state_c = 4

    def draw_all(self, cx, cy, ui_scale, height_px):
        """(cx, cy, ech) = repere de la colonne d'interface (voir Game._ui_reference) ; hauteur = hauteur de la fenetre."""
        import pyglet
        for name_str, alpha, w, h, x, y in (('taptostart', self.alpha, TT_L, TT_H, cx, cy - TT_BOTTOM * ui_scale), ('copyright', self.alpha_c, CP_L, CP_H, cx, CP_TOP * ui_scale)):
            if alpha <= 0.001 or name_str not in self.files: continue
            sp = self.sprites.get(name_str)
            if sp is None: sp = self.sprites[name_str] = pyglet.sprite.Sprite(pyglet.image.load(self.files[name_str]))
            sp.update(x=x - w * ui_scale / 2, y=y - h * ui_scale / 2, scale_x=w * ui_scale / sp.image.width, scale_y=h * ui_scale / sp.image.height)
            sp.opacity = int(round(255 * min(1.0, alpha))); sp.draw()


# ---- Ecran « Licence » (type 80, Make_License / LicensePolicy / LicenseNobu)
PRIVACY_URL = 'https://square-enix-games.com/en_US/documents/privacy'       # LicensePolicy.OnMouseUpAsButton : langue != 0 (le japonais ouvre https://www.jp.square-enix.com/privacy/)
LICENSE_BORDER = (-215.0, -345.0, 215.0, 330.0)
LICENSE_TEXT = (-198.0, -262.0, 186.0, 272.0)                  # zone du texte (x0, y0, x1, y1), unites d'interface
LICENSE_POLICY = (-198.0, -334.0, 90.0, -284.0)              # bouton « Privacy Policy »
LICENSE_BACK = (136.0, -337.0, 198.0, -285.0)
LICENSE_TITLE_Y = 302.0
LICENSE_TITLE = N_('Licence')                    # (dessine par Pause._et, qui le traduit ; « Privacy Policy » est le texte du jeu)


# Texte ajoute en tete de l'ecran Licence (en anglais, comme la liste d'origine) : ce que le portage est et ce qu'il utilise. La liste d'origine (TextAsset Menu/License_list_A) suit, inchangee.
PROJECT_LICENSE = (
    "<color=orange>Dragon Quest IV PC port (unofficial)</color>\n"
    "--------------------------------------------------\n"
    "This is an unofficial, non-commercial fan project. It is not affiliated with, endorsed by or sponsored by SQUARE ENIX CO., LTD., ArtePiazza or any other rights holder. DRAGON QUEST is a trademark of SQUARE ENIX CO., LTD.\n"
    "\n"
    "This program contains no game content. It runs the original game engine (libdq4core.so) and reads the game data from the Android version of Dragon Quest IV that you own (the APK files and the save files on your own computer). Nothing from the game is copied, modified or distributed by this program, and your original files are never changed.\n"
    "\n"
    "The French text comes from an unofficial French translation patch that the user applied to those APK files.\n"
    "\n"
    "How it works: the original ARM64 game engine runs unmodified inside a CPU emulator (Unicorn). The Unity layer of the Android game (display, menus, input and sound) is re-implemented in Python (pyglet), following the behavior of the original game code. The 16:9 display, the mouse and keyboard controls, the on-screen buttons, the settings menu, the instant save states and the save export / import tool are additions of this port.\n"
    "\n"
    "Your save files, save states and settings stay on your computer (in the \"donnees\" folder of this project). This program does not send any data over the Internet; only the launcher downloads the components listed below, once, the first time it runs. The \"Privacy Policy\" button opens the publisher's web page in your browser.\n"
    "\n"
    "<color=orange>Components used by this port</color>\n"
    "--------------------------------------------------\n"
    "The Python packages below are downloaded by the launcher from the Python Package Index; none of them is distributed with this program.\n"
    "\n"
    "Python - PSF License - python.org\n"
    "Unicorn Engine (CPU emulator) - GNU GPL v2 - unicorn-engine.org\n"
    "pyglet (window, graphics, input) - BSD 3-Clause License - pyglet.org\n"
    "NumPy - BSD 3-Clause License - numpy.org\n"
    "Pillow (images) - MIT-CMU License - python-pillow.org\n"
    "UnityPy (reading the game data) - MIT License - github.com/K0lb3/UnityPy\n"
    "Capstone (reading the menu layout from the game code, once) - BSD License - capstone-engine.org\n"
    "SoundFile (music) - BSD 3-Clause License; its libsndfile library - LGPL 2.1 - github.com/bastibe/python-soundfile\n"
    "\n"
    "<color=orange>Original game notices</color>\n"
    "--------------------------------------------------\n"
    "The notices below are those of the original Android game. They are kept unchanged.\n"
    "\n\n")


class License:
    """Texte des licences (TextAsset Menu/License_list_A) dans une fenetre defilante, avec les titres <color=orange> en orange. Les positions exactes de la fenetre de l'original n'ont pas ete retrouvees
    (elles dependent du rapport hauteur/largeur de l'ecran) : disposition dessinee ici, defilement a la molette, aux fleches, PageHaut/PageBas, ou en glissant la barre."""
    def __init__(self, path):
        import re
        self.layout_cache = None; self.zones = []; self.topmost = 0.0; self.dragging = None; self.zone_barre = None; self.hovered = None; self.geom = None
        txt = PROJECT_LICENSE + (open(path, 'rb').read().decode('utf-8', 'replace').replace('\r\n', '\n').replace('\ufeff', '') if path else '')
        self.plan = []; out = []; n = 0; orange = False
        for m in re.split(r'(<color=orange>|</color>)', txt):
            if m == '<color=orange>': orange = True
            elif m == '</color>': orange = False
            elif m: self.plan.append((n, n + len(m), orange)); out.append(m); n += len(m)
        self.text = ''.join(out)

    def _layout(self, J, ui_scale):
        """TextLayout pyglet de la fenetre (recree si l'echelle change)."""
        lookup_key = round(ui_scale, 3)
        if self.layout_cache is not None and self.layout_cache[0] == lookup_key: return self.layout_cache[1]
        P = J.pause; P._label('x', 10)                                                                     # (enregistre la police du jeu)
        size_value = 11.0 * ui_scale * 0.75; wid = int((LICENSE_TEXT[2] - LICENSE_TEXT[0]) * ui_scale); topmost = int((LICENSE_TEXT[3] - LICENSE_TEXT[1]) * ui_scale)
        fonts = tuple(P._pol or ()) + ('Consolas', 'DejaVu Sans Mono', 'Courier New')
        doc = pyglet.text.document.FormattedDocument(self.text)
        doc.set_style(0, len(self.text), dict(font_name=fonts, font_size=size_value, color=(235, 235, 235, 255)))
        for a, b, o in self.plan:
            if o: doc.set_style(a, b, dict(color=(255, 160, 40, 255)))
        lay = pyglet.text.layout.ScrollableTextLayout(doc, width=wid, height=topmost, multiline=True)
        self.layout_cache = (lookup_key, lay); return lay

    def maximum(self):
        lay = self.layout_cache[1] if self.layout_cache else None
        return max(0.0, lay.content_height - lay.height) if lay else 0.0

    def scroll_by(self, delta):
        self.topmost = min(self.maximum(), max(0.0, self.topmost + delta))

    def on_bar(self, x, y):
        zb = self.zone_barre
        return zb is not None and self.maximum() > 0 and zb[0] <= x <= zb[2] and zb[1] <= y <= zb[3]

    def drag_to(self, y):
        """Le curseur de la barre suit le pointeur (LicenseNobu : position du curseur -> proportion du texte) ; y en pixels (pyglet, vers le haut)."""
        if self.geom is None: return
        by0, bh, th = self.geom; free = bh - th
        if free <= 0: return
        self.topmost = min(1.0, max(0.0, (by0 + bh - th / 2 - y) / free)) * self.maximum()

    def draw_all(self, J, cx, cy, ui_scale):
        pg = pyglet; from pyglet import gl as g
        P = J.pause; k = ui_scale * 800.0 / 900.0
        ui_scale = min(ui_scale, 0.97 * J.height / (LICENSE_BORDER[3] - LICENSE_BORDER[1])); k = ui_scale * 800.0 / 900.0
        U = lambda x, y: (cx + x * ui_scale, cy + y * ui_scale)
        g.glDisable(g.GL_DEPTH_TEST); g.glEnable(g.GL_BLEND); g.glBlendFunc(g.GL_SRC_ALPHA, g.GL_ONE_MINUS_SRC_ALPHA)
        x0, y0 = U(LICENSE_BORDER[0], LICENSE_BORDER[1]); x1, y1 = U(LICENSE_BORDER[2], LICENSE_BORDER[3]); P._border(x0, y0, x1 - x0, y1 - y0, k)
        P._restore_blend()
        label = P._label(LICENSE_TITLE, 24 * ui_scale * 0.75); label.x = cx - label.content_width / 2; label.y = cy + LICENSE_TITLE_Y * ui_scale - 9 * ui_scale; label.draw()
        lay = self._layout(J, ui_scale); self.topmost = min(self.topmost, self.maximum())
        tx, ty = U(LICENSE_TEXT[0], LICENSE_TEXT[1]); lay.x = int(tx); lay.y = int(ty); lay.view_y = -int(self.topmost); lay.draw()
        # barre de defilement
        bx0, by0 = U(LICENSE_TEXT[2] + 4, LICENSE_TEXT[1]); bw, bh = 8 * ui_scale, (LICENSE_TEXT[3] - LICENSE_TEXT[1]) * ui_scale; m = self.maximum()
        pg.shapes.Rectangle(bx0, by0, bw, bh, color=(34, 36, 42)).draw()
        if m > 0:
            th = max(26 * ui_scale, bh * lay.height / lay.content_height); hau = by0 + bh - th - (bh - th) * (self.topmost / m)
            P._plate(bx0 - 1, hau, bw + 2, th, k * 0.6, self.dragging is not None); self.geom = (by0, bh, th)
        self.zone_barre = (bx0 - 4, by0, bx0 + bw + 4, by0 + bh)
        px0, py0 = U(LICENSE_POLICY[0], LICENSE_POLICY[1]); px1, py1 = U(LICENSE_POLICY[2], LICENSE_POLICY[3])
        P._plate(px0, py0, px1 - px0, py1 - py0, k, self.hovered == 'politique'); P._restore_blend()          # (survol : plaque assombrie, sans encadre jaune)
        e2 = P._label('Privacy Policy', 16 * ui_scale * 0.75); e2.x = (px0 + px1) / 2 - e2.content_width / 2; e2.y = (py0 + py1) / 2 - 5 * ui_scale; e2.draw()
        rx0, ry0 = U(LICENSE_BACK[0], LICENSE_BACK[1]); rx1, ry1 = U(LICENSE_BACK[2], LICENSE_BACK[3])
        P._back_button(rx0, ry0, rx1 - rx0, ry1 - ry0, self.hovered == 'retour')
        self.zones = [(px0, py0, px1, py1, 'politique'), (rx0, ry0, rx1, ry1, 'retour')]

    def zone(self, x, y):
        for a, b, c, d, name_str in self.zones:
            if a <= x <= c and b <= y <= d: return name_str
        return None
