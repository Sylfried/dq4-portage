"""Police des messages du jeu : celle que le moteur utilise pour dessiner les dialogues et les messages de combat dans son canevas de texte (SDrawCTRL / TextCanvas), pas la police de menu SE-GARRIR.

Le fichier (`assets/English.font` du paquet de donnees, copie dans le cache par `extract_message_font`) est lu tel quel, avec TOUS ses glyphes : un caractere que le patch ou un autre jeu de la serie (DQ5, DQ6) ajoute a la police
s'affiche donc sans rien changer ici. Format (relevé dans `SFont::Load`, `FontHeader::GetGlyph`) :
  - 28 octets d'en-tete : « TNOF », puis (a l'octet 24) la hauteur d'une cellule de glyphe (24) ;
  - table de 65 536 entrees de 4 octets (code UTF-16 -> entree) : octet de poids fort = largeur du glyphe (bits 0 a 6) et drapeau (bit 7), les 24 autres bits = position du glyphe dans les donnees ;
  - donnees : pour chaque glyphe, `width_px x height_px` octets d'opacite (0 a 255), en ligne, compresses : un octet « 1xxxxxxx » repete le octet suivant `xxxxxxx` fois, un octet « 0xxxxxxx » est suivi de `xxxxxxx` octets
    tels quels, un octet 0 termine.
Placement (`SDrawCTRL::PutChar` 0x1575a0 et `TextCanvas::PutChar` 0x152820 de libdq4core.so ; verifie pixel pour pixel contre le canevas du vrai moteur, tests/test_message_font.py) : la position d'ecriture avance de la
largeur du glyphe ; un glyphe a drapeau (V, W, t, v, w, y du patch) est pose un pixel plus a gauche et avance de deux pixels de moins (crenage) ; l'espace avance de la largeur d'espace du moteur (6, `obj + 0x38`) et pas de la
largeur du glyphe (5) ; la tabulation de `obj + 0x3c` ; l'espace large U+3000 de `obj + 0x3a` ; les retours a la ligne (U+000A, U+000D) ne font rien ; « $ » n'est pas dessine pour la langue 1 (anglais) et « ; » n'est dessine
(comme une espace) que pour la langue 2 ; un code absent de la police est dessine avec le glyphe du « @ » (entree 0x40 de la table : `[FontHeader + 0x128]`). Chaque glyphe REMPLACE les pixels de sa cellule (il n'y a pas de
melange) ; un ecart entre les lettres (`g_letterSpace`, 0 en jeu) s'ajoute a chaque avance.
Module sans pyglet : seule `line` (la texture d'une ligne) en a besoin."""
import struct
import numpy as np
from dq4_pc.language import tr

TABLE_SIZE = 65536
TABLE_START = 28
DATA_START = TABLE_START + 4 * TABLE_SIZE       # le fichier du jeu : les donnees suivent la table (SFont::Load copie 0x40000 octets de table)
BASELINE = 20                                    # rangee de la cellule ou passe la ligne de base : le bas des majuscules est a la rangee 19 (mesure sur le canevas du moteur : cellule du haut a 15 unites sous le cadre, 1re ligne de base a 35 unites, 20 + 15)
CODE_DEFAULT = 0x40                                    # glyphe des codes absents de la police : le « @ »


class MessageFont:
    """Police des messages du jeu (voir le module). `width_px(text)` : avance de la position d'ecriture (pixels du canevas = unites d'interface, 1 pour 1) ; `line(text)` : la texture d'une ligne, comme BitmapFont."""
    PAD = 1                                           # colonnes de marge a gauche de la texture (un glyphe a drapeau deborde d'un pixel a gauche de la position d'ecriture)
    SCALE = 1.0                                         # une unite d'interface par pixel du canevas (mesure : 434 unites de large pour 0,8477 x 512 pixels de canevas)

    LIMIT = 410                                      # largeur d'une ligne de dialogue en pixels du canevas (`CTextAutoReturn` : [0x2523c4], valeur lue dans le moteur pendant un dialogue)

    def __init__(self, path=None, data=None, language=1, space=6, wide_space=6, tab_width=15, spacing=0):
        if data is None:
            with open(path, 'rb') as f: data = f.read()
        if data[:4] != b'TNOF': raise ValueError('message font unreadable (signature)')
        self.d = data
        self.table = np.frombuffer(data, '<u4', TABLE_SIZE, TABLE_START)
        self.height_px = struct.unpack_from('<H', data, 24)[0] or 24
        self.base = DATA_START
        self.language, self.space, self.wide_space, self.tab_width, self.spacing = language, space, wide_space, tab_width, spacing
        self.tex = {}; self.wid = {}; self._g = {}
        self.G = self                                 # (pour les outils qui testent `code in font.G`)

    def __contains__(self, code):
        return 0 <= code < TABLE_SIZE and bool(self.table[code] >> 24)

    # ---- glyphes
    def glyph(self, code):
        """-> (drapeau, largeur, bitmap hauteur x largeur uint8) du glyphe de `code` (celui du « @ » si la police ne l'a pas : GetGlyph)."""
        g = self._g.get(code)
        if g is None:
            e = int(self.table[code]) if 0 <= code < TABLE_SIZE else 0
            if not (e >> 24): e = int(self.table[CODE_DEFAULT])
            width_px = (e >> 24) & 0x7f; flag = (e >> 31) & 1; n = width_px * self.height_px
            output = bytearray(); i = self.base + (e & 0xffffff); d = self.d
            while len(output) < n and i < len(d):
                t = d[i]; i += 1; k = t & 0x7f
                if k == 0: break
                if t & 0x80: output += d[i:i + 1] * k; i += 1
                else: output += d[i:i + k]; i += k
            output = bytes(output[:n]).ljust(n, b'\0')
            g = self._g[code] = (flag, width_px, np.frombuffer(output, np.uint8).reshape(self.height_px, width_px) if width_px else np.zeros((self.height_px, 0), np.uint8))
        return g

    # ---- placement
    def plan(self, text):
        """-> (cellules, fin) : cellules = [(x, glyphe)] avec x la colonne de la cellule (position d'ecriture, moins 1 pour un glyphe a drapeau) ; fin = position d'ecriture a la fin du texte."""
        pen = 0; cel = []
        for ch in text:
            c = ord(ch)
            if c > 0xffff: c = 0xfffd
            if c in (0x0a, 0x0d): continue
            if c == 0x09: pen += self.tab_width; continue
            if c == 0x20: pen += self.space; continue
            if c == 0x3000: pen += self.wide_space; continue
            if c == 0x24 and self.language == 1: continue
            if c == 0x3b:
                if self.language == 2: pen += self.space
                continue
            g = self.glyph(c); flag, w = g[0], g[1]
            cel.append((pen - flag, g)); pen += (w - 2 if flag else w) + self.spacing
        return cel, pen

    def width_px(self, text):
        """Avance de la position d'ecriture sur une ligne (pixels du canevas) : de quoi couper les lignes comme le moteur."""
        w = self.wid.get(text)
        if w is None:
            if len(self.wid) > 20000: self.wid.clear()
            w = self.wid[text] = self.plan(text)[1]
        return w

    def cut_width(self, c):
        """Largeur qu'un caractere ajoute a une ligne pour le calcul des coupures (`CTextAutoReturn::AutoReturn`) : comme l'avance du dessin, mais « $ » compte sa largeur (il n'est pas dessine) et « ; » compte 0."""
        k = ord(c)
        if k > 0xffff: k = 0xfffd
        if k == 0x09: return self.tab_width
        if k == 0x20: return self.space
        if k == 0x3b: return self.space if self.language == 2 else 0
        if k == 0x3000: return self.wide_space
        g = self.glyph(k)
        return (g[1] - 2 if g[0] else g[1]) + self.spacing

    def wrap_text(self, text, limit=None):
        """Lignes d'un texte coupe comme le moteur (`CTextAutoReturn::AutoReturn`, 0x157ed0) : la largeur de la ligne est cumulee caractere par caractere ; quand elle atteint la limite, on revient au dernier point de coupure
        (apres une espace, un « ㈠ » ou un tiret) et on passe a la ligne ; sans point de coupure le caractere qui depasse reste sur la ligne. Un saut de ligne du texte remet la largeur a zero, et celui qui suit
        immediatement une coupure automatique est avale. -> liste de lignes (l'espace qui precede une coupure reste en fin de ligne)."""
        limit = self.LIMIT if limit is None else limit
        t = text; n = len(t); i = 0; output = []; w = 0; cand = None      # cand = (i, longueur de sortie) apres le dernier point de coupure
        while i < n:
            c = t[i]; i += 1
            if c == '\r': continue
            if c == '\n': output.append('\n'); w = 0; cand = None; continue
            w += self.cut_width(c); output.append(c)
            cut = c == ' ' or c == '\u3220'
            if c == '-':
                cut = True
                if self.language == 1: cut = not (i - 2 >= 0 and t[i - 2] == '-') and not (i < n and t[i] == '-')
            if cut: cand = (i, len(output))
            if w >= limit:
                if cand is not None:
                    i = cand[0]; del output[cand[1]:]
                output.append('\n'); w = 0; cand = None
                if i < n and t[i] == '\n': i += 1
        return ''.join(output).split('\n')

    def pixels(self, text):
        """Image (hauteur x largeur, uint8) de la ligne, la position d'ecriture a la colonne PAD : exactement ce que le moteur ecrit dans son canevas (chaque glyphe remplace sa cellule)."""
        cel, end = self.plan(text)
        right = max([end] + [x + g[1] for x, g in cel]) + 2 * self.PAD
        a = np.zeros((self.height_px, max(right, 1)), np.uint8)
        for x, (_, w, bm) in cel:
            if w: a[:, self.PAD + x:self.PAD + x + w] = bm
        return a

    def line(self, text):
        """-> (texture, largeur, hauteur, base) en pixels du canevas ; base = distance du haut de l'image a la ligne de base (comme BitmapFont.ligne)."""
        r = self.tex.get(text)
        if r is None:
            import pyglet
            from pyglet import gl
            if len(self.tex) > 800:
                for t, *_ in self.tex.values(): t.delete() if hasattr(t, 'delete') else None
                self.tex.clear()
            a = self.pixels(text); H, W = a.shape
            rgba = np.zeros((H, W, 4), np.uint8); rgba[..., :3] = 255; rgba[..., 3] = a
            img = pyglet.image.ImageData(W, H, 'RGBA', np.ascontiguousarray(rgba[::-1]).tobytes(), pitch=W * 4)
            t = img.get_texture(); gl.glBindTexture(t.target, t.id)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)      # filtre bilineaire, comme la texture du canevas du jeu
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
            r = self.tex[text] = (t, W, H, BASELINE)
        return r


def extract_message_font(apk_folder, cache, log=print, name_str='English.font', dest='ui_messages.font'):
    """Copie la police des messages du paquet de donnees du jeu (split_UnityDataAssetPack.apk, assets/English.font) dans le cache, une seule fois. -> True si elle y est."""
    import os, zipfile
    path = os.path.join(cache, dest)
    if os.path.exists(path): return True
    try:
        os.makedirs(cache, exist_ok=True)
        with zipfile.ZipFile(os.path.join(apk_folder, 'split_UnityDataAssetPack.apk')) as z: raw = z.read('assets/' + name_str)
        if raw[:4] != b'TNOF': raise ValueError('unexpected signature')
        with open(path + '.tmp', 'wb') as f: f.write(raw)
        os.replace(path + '.tmp', path); return True
    except Exception as ex:
        log('Message font not extracted (%r): using the SE-GARRIR menu font instead.' % (ex,)); return False
