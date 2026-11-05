"""Aide des tests : dessiner une cellule de texte avec le VRAI `Render._text`, sans fenetre ni contexte GL, et relever la geometrie exacte des quads (D-243 : tous les textes de menu sont a la position exacte du jeu).

`Render._text` fait ses calculs (ancre, interligne, alignement, largeur) puis envoie un quad par segment de ligne a `self.prog.vertex_list` ; ici `prog` enregistre les quads et `ui_menu.gl` est remplace par un faux module.
La police est celle du jeu quand on la donne (`ui_garrir.json`, mesures reelles), sinon une police factice de meme interligne et meme ascent que SE-GARRIR (8 px par caractere).

    import _text_render as TR
    quads = TR.draw(window, node)          # [Quad(text, x, base, width, ts)] : x = bord gauche de l'encre de depart, base = ligne de base, ts = echelle horizontale (1 = pas de compression)"""
import os, re, sys, types, collections

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.menus import ui_menu as UM

LEADING, ASCENT = 23.525390625, 18.88671875          # SE-GARRIR : interligne et ascent (px de police)
PAD, UP, DOWN = 2, 22, 9                              # marge, lignes de texture au-dessus / au-dessous de la ligne de base (BitmapFont)
CACHE = os.environ.get('DQ_UI_CACHE') or os.environ.get('DQ_CACHE_UI') or '/tmp/audit_final/interface/uicache'

Quad = collections.namedtuple('Quad', 'text x base width ts')


class FakeFont:
    """Police factice (interface de BitmapFont utilisee par Render._text) : `advance` px par caractere, les caracteres de controle ne comptent pas. `line` ne cree aucune texture."""
    leading, ascent, PAD, UP, DOWN = LEADING, ASCENT, PAD, UP, DOWN

    def __init__(self, advance=8): self.advance = advance; self.calls = []

    def width_px(self, text): return self.advance * sum(1 for c in text if c >= ' ')

    def line(self, text):
        self.calls.append(text)
        return types.SimpleNamespace(target=0, id=0), int(self.width_px(text)) + 2 * PAD, UP + DOWN, UP


class RealFont:
    """La vraie police SE-GARRIR (ui_garrir.json / .png de `CACHE`) pour les largeurs, mais sans texture (`line` ne cree rien)."""
    def __init__(self, bm): self.bm = bm; self.leading, self.ascent = bm.leading, bm.ascent; self.PAD, self.UP, self.DOWN = bm.PAD, bm.UP, bm.DOWN

    def width_px(self, text): return self.bm.width_px(text)

    def line(self, text): return types.SimpleNamespace(target=0, id=0), int(self.bm.width_px(text)) + 2 * self.bm.PAD, self.bm.UP + self.bm.DOWN, self.bm.UP


def real_font():
    """RealFont, ou None si les fichiers de la police ne sont pas la."""
    j, g = os.path.join(CACHE, 'ui_garrir.json'), os.path.join(CACHE, 'ui_garrir.png')
    return RealFont(UM.BitmapFont(j, g)) if os.path.exists(j) and os.path.exists(g) else None


class _Prog:
    def __init__(self): self.quads = []
    def vertex_list(self, n, mode, **kw):
        p = np.asarray(kw['position'][1], dtype=float).reshape(-1, 2); self.quads.append((p[0][0], p[0][1], p[1][0], p[2][1])); return types.SimpleNamespace(draw=lambda *a, **k: None, delete=lambda: None)
    def __setitem__(self, k, v): pass


class _Gl:
    GL_TRIANGLES = 4; GL_TEXTURE0 = 0x84C0
    @staticmethod
    def glActiveTexture(*a): pass
    @staticmethod
    def glBindTexture(*a): pass


def render(font=None, neighbors=(), ml=None):
    """Un Render sans GL : prog enregistreur, `ml` (la vraie mise en page, ou une minimale : dy = 0, le texte est a la position de la cellule, sans compensation d'interligne) ; `font` None = police de repli (texts.bitmap None, GMaruGoPro-M factice de 8 px par caractere)."""
    r = object.__new__(UM.Render)
    r.ml = ml or types.SimpleNamespace(hdr={'lang': {'dy': 0.0, 'hiro': 1.0}}, colors=[(1.0, 1.0, 1.0, 1.0)] * 8)
    r.texts = types.SimpleNamespace(bitmap=font, line=lambda text, px: (types.SimpleNamespace(target=0, id=0), 8 * len(text) + 4, 30, 22))
    r.neighbors = list(neighbors); r.prog = _Prog()
    return r


def draw(win, node, font=None, r=None, s=1.0):
    """Dessine `node` de la fenetre `win` (cx = cy = 0, echelle `s`) et rend ses quads. `font` : FakeFont par defaut ; pour la police de repli passer `r` (un render(None))."""
    if r is None: r = render(font if font is not None else FakeFont())
    bm = r.texts.bitmap; r.prog.quads = []
    old = UM.gl; UM.gl = _Gl
    try: r._text(win, node, 0.0, 0.0, s)
    finally: UM.gl = old
    u = node['text']['characterSize'] * 0.1; out = []
    for text, (x0, y0, x1, y1) in zip(_segments(node), r.prog.quads):
        if bm:
            ts = (x1 - x0) / ((int(bm.width_px(text)) + 2 * bm.PAD) * u * s)
            out.append(Quad(text, (x0 + bm.PAD * u * s * ts) / s, y0 / s + bm.DOWN * u, (x1 - x0) / s, ts))
        else:
            ts = (x1 - x0) / (8 * len(text) + 4)
            out.append(Quad(text, (x0 + 2 * ts) / s, (y0 + 8) / s, (x1 - x0) / s, ts))
    return out


def _segments(node):
    """Textes des segments dans l'ordre ou Render._text les dessine (une ligne = un segment par couleur « @cN »)."""
    out = []
    for l in node['text']['text'].split('\n'):
        pos = 0
        for m in re.finditer(r'@c(\d)', l):
            if m.start() > pos: out.append(l[pos:m.start()])
            pos = m.end()
        if pos < len(l): out.append(l[pos:])
    return out


def make_window(typ, cells, port=0, name_str='Make_Test()', plates=()):
    """Fenetre synthetique de type `typ` : une cellule de texte par element de `cells` ({'pos': [x, y, z], 'anchor', 'alignment', 'ls', 'cs', 'tab'} : tous facultatifs), liee au parametre (port, k) ; noeud numero 10 + k.
    `plates` : plaques de bouton (partie 7, comme celles du jeu) {'pos': [x, z], 'w', 'h'} (largeur et hauteur totales), noeuds 100 + k, numero de bouton k : le texte qui a son ancre dedans etait comprime pour y tenir."""
    def text(k, c):
        return {'id': 10 + k, 'par': 1, 'pos': list(c.get('pos', [0.0, 4.0, 0.0])), 'act': True, 'mats': [],
                'text': {'font': 'font', 'characterSize': c.get('cs', 9.945), 'text': None, 'anchor': c.get('anchor', 3), 'alignment': c.get('alignment', 0), 'lineSpacing': c.get('ls', 0.801), 'tabSize': c.get('tab')}}
    def plate(k, c):
        w, h = c['w'] / 2.0, c['h'] / 2.0
        return {'id': 100 + k, 'par': 1, 'pos': [c['pos'][0], 4.0, c['pos'][1]], 'act': True, 'mats': [{'part': 7}], 'parts': {'buttonId': k, 'gamepad': 0x10},
                'mesh': {'vtx': [[-w, h], [w, h], [w, -h], [-w, -h]], 'uv': [[0, 0], [1, 0], [1, 1], [0, 1]], 'sub': {'0': [0, 1, 2, 0, 2, 3]}}}
    t = {'name': name_str, 'err': None, 'nodes': [{'id': 1, 'par': None, 'pos': [0.0, 0.0, 0.0], 'act': True, 'mats': []}] + [plate(k, c) for k, c in enumerate(plates)] + [text(k, c) for k, c in enumerate(cells)],
         'parts': [{'node': 1, 'ib': [{'k': 'text', 'go': 10 + k, 'variant': 0} for k in range(len(cells))]}], 'params': [{'id': port, 'no': k, 'parts': 0, 'base': k} for k in range(len(cells))], 'codes': [], 'builds': []}
    return UM.Window(types.SimpleNamespace(types={str(typ): t}, info=[], borders=[], hdr={'lang': {'hiro': 1.0}}, pushed=(0.0, 0.0)), typ)
