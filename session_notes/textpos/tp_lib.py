"""Banc de mesure de la position des textes de menu : rend une cellule de texte (Render._text, vraie police SE-GARRIR) dans plusieurs modes
et releve la geometrie exacte des quads (x, ligne de base, largeur). Unites d'interface (S = 1, cx = cy = 0).
Modes : P = mise en page exportee de l'APK pure (aucun ecart de la visionneuse) ; V = reglages par defaut ; O = DQ_TEXTE_ORIGINAL=1 ; plus des modes d'isolation."""
import os, sys, json, copy, re
sys.path.insert(0, '/home/claude/dq4-portage')
os.environ.setdefault('PYGLET_HEADLESS', '1')
import numpy as np, pyglet
pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from PIL import Image

C = '/tmp/audit_final/interface/uicache'
win = pyglet.window.Window(64, 64, visible=True)
from dq4_pc.menus import ui_menu as UM

ml = UM.PageLayout(os.path.join(C, 'ui_layout.json'), os.path.join(C, 'ui_frameData.bin'))
sheets = {0: np.array(Image.open(os.path.join(C, 'ui_MenuTexture.png')).convert('RGBA')), 1: np.array(Image.open(os.path.join(C, 'ui_Button.png')).convert('RGBA'))}
REAL_THIN = UM.THIN_SPACES; REAL_DESC = dict(UM.DESCRIPTIONS); REAL_COMPRESS = UM.compress_label
DY = ml.hdr['lang']['dy']


class Dummy:
    def draw(self, *a, **k): pass
    def delete(self): pass


class Rec:
    active = False; quads = []; last = None


rec = Rec()


class ProgProxy:
    def __init__(self, real): self.__dict__['real'] = real
    def vertex_list(self, n, mode, **kw):
        if rec.active:
            p = np.asarray(kw['position'][1], dtype=float).reshape(-1, 2)
            rec.quads.append((rec.last, p[0][0], p[0][1], p[1][0], p[2][1])); return Dummy()
        return self.real.vertex_list(n, mode, **kw)
    def __getattr__(self, k): return getattr(self.real, k)
    def __getitem__(self, k): return self.real[k]
    def __setitem__(self, k, v): self.real[k] = v


def make_render():
    r = UM.Render(ml, sheets, os.path.join(C, 'ui_font.otf'))
    r.prog = ProgProxy(r.prog)
    bm = r.texts.bitmap; orig = bm.line
    def line(text, _o=orig): rec.last = text; return _o(text)
    bm.line = line
    return r


RENDERS = {True: make_render(), False: make_render()}      # cle : THIN_SPACES actif (les caches de largeur dependent du reglage)

MODES = {
    'P': dict(center=False, thin=False, wrap=False, fit=False),     # mise en page de l'APK pure
    'V': dict(center=True, thin=True, wrap=True, fit=True),         # visionneuse par defaut
    'O': dict(center=False, thin=True, wrap=True, fit=True),        # DQ_TEXTE_ORIGINAL=1
    'C': dict(center=True, thin=False, wrap=False, fit=False),      # P + recentrage seul
    'T': dict(center=False, thin=True, wrap=False, fit=False),      # P + espaces fines seules
    'W': dict(center=False, thin=False, wrap=True, fit=True),       # P + recoupe / compression seules
}


def apply_mode(m):
    UM.TEXT_CENTERING = m['center']; UM.THIN_SPACES = REAL_THIN if m['thin'] else ''
    UM.DESCRIPTIONS = dict(REAL_DESC) if m['wrap'] else {}
    UM.compress_label = REAL_COMPRESS if m['fit'] else (lambda *a, **k: False)
    return RENDERS[m['thin']]


def text_cells(typ):
    """[(id, no, node_id, variant)] des cellules de texte liees a un (id, no) de la fenetre `typ`."""
    t = ml.types[str(typ)]; out = []
    if 'params' not in t: return out
    for p in t['params']:
        if p.get('parts') is None or p['parts'] >= len(t['parts']) or 'custom' in p or p.get('textcolor') is not None: continue
        pt = t['parts'][p['parts']]
        if p['base'] >= len(pt['ib']): continue
        ib = pt['ib'][p['base']]
        if ib['k'] == 'text': out.append((p['id'], p['no'], ib.get('go'), ib.get('variant')))
    return out


def measure(typ, i, no, s, mode, prep=None):
    """Rend la cellule (i, no) du type `typ` avec la chaine `s` en mode `mode` ; -> dict de mesures ou None (rien dessine)."""
    m = MODES[mode]; r = apply_mode(m)
    w = UM.Window(ml, typ)
    if prep: prep(w)
    w.param_str(i, no, s)
    pr = w.params.get((i, no)); pt, ib = w._ib(pr); node = w.N[ib['go']]
    if not m['fit']: node.pop('fit_x', None); node.pop('wrap_x', None)
    return measure_node(w, node, r)


def measure_node(w, node, r):
    t = node['text']
    if not t or not t.get('text'): return None
    rec.quads = []; rec.active = True
    try: r._text(w, node, 0.0, 0.0, 1.0)
    finally: rec.active = False
    bm = r.texts.bitmap; u = t['characterSize'] * 0.1; qs = []
    for text, x0, y0, x1, y1 in rec.quads:
        wpx = int(bm.width_px(text)) + 2 * bm.PAD
        ts = (x1 - x0) / (wpx * u)
        xo = x0 + bm.PAD * u * ts
        base = y0 + (bm.UP + bm.DOWN - bm.UP) * u            # (h - b) = DOWN = 9 : ligne de base = bas de l'image + 9 px de police
        qs.append(dict(text=text, x=xo, xend=xo + bm.width_px(text) * u * ts, base=base, ts=ts))
    if not qs: return dict(node=node['id'], quads=[], lines=0)
    bases = sorted({round(q['base'], 3) for q in qs}, reverse=True)
    asc = bm.ascent * u; desc = (bm.leading - bm.ascent) * u
    return dict(node=node['id'], quads=qs, lines=len(bases), base0=bases[0], baseN=bases[-1], xl=min(q['x'] for q in qs), xr=max(q['xend'] for q in qs),
                ts=min(q['ts'] for q in qs), top=bases[0] + asc, bottom=bases[-1] - desc, u=u, cs=t['characterSize'], text=t['text'])


def container(w, node, zp=None):
    """(genre, x0, x1, z0, z1) du plus petit element (plaque de bouton de preference) qui contient le point d'ancrage du texte, ou (None...) ; coordonnees absolues."""
    ax = node['pos'][0]; az = node['pos'][2] - DY if zp is None else zp
    best = None
    for o in w.N.values():
        if o is node or not o['vtx'] or not o['mats']: continue
        xs = [o['pos'][0] + v[0] for v in o['vtx']]; zs = [o['pos'][2] + v[1] for v in o['vtx']]
        if min(xs) <= ax <= max(xs) and min(zs) <= az <= max(zs):
            plate = o['mats'][0].get('part') == 7 and o['buttonId'] is not None
            area = (max(xs) - min(xs)) * (max(zs) - min(zs))
            key = (0 if plate else 1, area)
            if best is None or key < best[0]: best = (key, ('plaque' if plate else 'cadre', min(xs), max(xs), min(zs), max(zs)))
    return best[1] if best else None
