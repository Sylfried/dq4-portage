"""Fenetres de menu du jeu d'origine : mise en page exacte (lue dans le code Unity du jeu, voir outils/ui_il2cpp), dessinee avec les feuilles du jeu.

Le fichier de mise en page (cache/ui_layout.json) decrit, pour chaque type de fenetre (Make_* de MenuPortItemTable) : les objets (position, maillage,
materiaux, texte), les elements modifiables (IText / IIcon / IButton / IBar...) et leurs liaisons (id, no) -> element, et l'effet de chaque code
(deplacement / affichage). Ce module applique les messages du moteur (setItemParam*, setItemCode, curseur) a ces objets et les dessine.
Repere du jeu : portrait 450 x 800, X vers la droite, Z vers le haut, origine au centre de l'ecran, Y = profondeur (plus grand = devant)."""
import os, re, json, math, time
import numpy as np
import pyglet
from pyglet import gl
from pyglet.graphics.shader import Shader, ShaderProgram

VERT = '''#version 330 core
in vec2 position; in vec2 tex_coords; in vec4 colors;
uniform vec2 vp;
out vec2 v_uv; out vec4 v_col;
void main() { gl_Position = vec4(position.x / vp.x * 2.0 - 1.0, position.y / vp.y * 2.0 - 1.0, 0.0, 1.0); v_uv = tex_coords; v_col = colors; }'''
FRAG = '''#version 330 core
in vec2 v_uv; in vec4 v_col; out vec4 fragColor;
uniform sampler2D tex; uniform int mode;
void main() {
    vec4 c;
    if (mode == 3) {                                                                               // plan de carte : texels nets, seule la frontiere entre deux texels est adoucie (« sharp bilinear »)
        vec2 ts = vec2(textureSize(tex, 0)); vec2 p = v_uv * ts; vec2 seam = floor(p + 0.5);
        vec2 aa = max(fwidth(p), vec2(1e-4)); c = texture(tex, (seam + clamp((p - seam) / aa, -0.5, 0.5)) / ts); }
    else c = texture(tex, v_uv);
    if (mode == 1) { float g = dot(c.rgb, vec3(0.299, 0.587, 0.114)); c.rgb = vec3(g); }          // bouton grise
    else if (mode == 2) { c.rgb = vec3(1.0) - c.rgb; }                                            // bouton inverse
    c *= v_col;
    if (c.a < 0.004) discard;
    fragColor = c; }'''

HAUTEUR_LIGNE = 1.246     # hauteur de ligne de la police en « em » (OS/2 winAscent + winDescent de GMaruGoPro-M) : recoupe l'espacement des barres PV/PM (28 px) et le centrage des boutons
TAILLE_POLICE = 19.0        # taille native de la police du jeu (GMaruGoPro-M, Font.fontSize) : 1 caractere = taille_caractere * 0.1 * 19 unites
MARQUES_TEXTE = {0: (1.0, None), 1: (1.0, 8.0), 2: (1.0, 'base'), 3: (1.0, 9.0), 4: (1.0, 6.25), 5: ('x14', 'base')}   # "^n" en tete d'un texte (IText) : (echelle x, taille de caractere)


def lire_cadres(chemin):
    """frameData (TextAsset du jeu) : nombre de maillages, puis pour chacun : nb sommets, nb indices, sommets (x, y, z, u, v), indices."""
    import struct
    b = open(chemin, 'rb').read(); n = struct.unpack_from('<i', b, 0)[0]; p = 4; out = []
    for _ in range(n):
        nv, ni = struct.unpack_from('<ii', b, p); p += 8
        v = np.frombuffer(b, '<f4', nv * 5, p).reshape(nv, 5); p += 20 * nv
        t = np.frombuffer(b, '<i4', ni, p); p += 4 * ni
        out.append(dict(vtx=[[float(x[0]), float(x[2])] for x in v], uv=[[float(x[3]), float(x[4])] for x in v], tri=[int(i) for i in t]))
    return out


def trois_lignes(t1, t0):
    """(correctif propose) type 1 (combat : cadre 188 de haut, canevas 164 = 4 lignes de 34) ramene a la hauteur de la fenetre du terrain (type 0 : cadre 126, 3 lignes) :
    les deux rangees hautes du cadre et le haut du canevas descendent de dz, le bord bas ne bouge pas ; V du bas du canevas = hauteur / 512 (le haut reste a V = 0)."""
    import copy
    t = copy.deepcopy(t1)
    h1 = max(v[1] for v in t1['frame_mesh']['vtx']) - min(v[1] for v in t1['frame_mesh']['vtx'])
    h0 = max(v[1] for v in t0['frame_mesh']['vtx']) - min(v[1] for v in t0['frame_mesh']['vtx'])
    dz = h1 - h0
    mid = (max(v[1] for v in t1['frame_mesh']['vtx']) + min(v[1] for v in t1['frame_mesh']['vtx'])) / 2
    for v in t['frame_mesh']['vtx']:
        if v[1] > mid: v[1] -= dz
    cv = t['canvas']; zmax = max(v[2] for v in cv['vtx']); zmin = min(v[2] for v in cv['vtx'])
    for v in cv['vtx']:
        if v[2] == zmax: v[2] -= dz
    hv = (zmax - dz - zmin) / 512.0 / (t.get('scale') or 1.0)
    for u, v in zip(cv['uv'], cv['vtx']):
        if v[2] == zmin: u[1] = hv
    return t


def limiter_lignes(t, nb=3, lh=28.0, marge=3.0):
    """Fenetre de message : le canevas montre exactement `nb` lignes de `lh` pixels (plus une marge de 3 pixels, le defilement du moteur commence a -3) au lieu de 3,5 lignes : la mise en page d'origine
    laisse voir le haut de la ligne suivante sous la derniere ligne (canevas de 100,5 pour des lignes de 28 : type 0 ; combat : lignes de 34)."""
    import copy
    cv = t['canvas']; zmax = max(v[2] for v in cv['vtx']); zmin = min(v[2] for v in cv['vtx']); h = nb * lh + marge
    if zmax - zmin <= h + 0.5: return t
    t = copy.deepcopy(t); cv = t['canvas']
    for v in cv['vtx']:
        if v[2] == zmin: v[2] = zmax - h
    for u, v in zip(cv['uv'], cv['vtx']):
        if v[2] == zmax - h: u[1] = h / 512.0
    return t


def texte_plein(t):
    """Types de message de combat 2 et 3 (messages des actions) : la mise en page d'origine dessine leur canevas de texte a 90 % (`scale` 0,9 : 490 pixels du canevas dans 441 unites), ce qui rend le texte
    plus petit que dans les dialogues du terrain et le message de debut de combat. On agrandit toute la fenetre (cadre, canevas, curseur de fin de page) de 1 / scale autour de son coin bas gauche, puis on la recentre :
    le texte a la taille des autres dialogues, avec autant de signes par ligne que dans l'original (bord bas inchange)."""
    import copy
    f = 1.0 / (t.get('scale') or 1.0)
    if abs(f - 1.0) < 1e-6: return t
    t = copy.deepcopy(t)
    for v in t['frame_mesh']['vtx']: v[0] *= f; v[1] *= f
    for v in t['canvas']['vtx']: v[0] *= f; v[2] *= f
    fl = t['feed_local']; t['feed_local'] = [fl[0] * f, fl[1], fl[2] * f]
    w0 = max(v[0] for v in t['frame_mesh']['vtx']) / f; w1 = w0 * f                  # largeur du cadre avant / apres
    t['win'] = [t['win'][0] - (w1 - w0) / 2, t['win'][1], t['win'][2]]
    return t


class MiseEnPage:
    """cache/ui_layout.json : {'header': {...}, 'types': {numero: {...}}} ; cadres : maillages des fenetres (frameData)"""
    def __init__(self, chemin, cadres=None):
        with open(chemin, encoding='utf-8') as f: d = json.load(f)
        self.hdr = d['header']; self.types = d['types']; self.message = d.get('message')       # message : fenetre de dialogue (MenuMessage), absente des anciens fichiers
        if self.message:                                                 # combat (type 1) : 3 lignes comme le terrain ; le cadre d'origine (4 lignes) reste en type 4, pour les messages qui en ont quatre
            ts = self.message['types']; ts.append(ts[1]); ts[1] = trois_lignes(ts[1], ts[0])
            for i in (2, 3): ts[i] = limiter_lignes(texte_plein(ts[i]), 3, 34.0)
            ts[0] = limiter_lignes(ts[0], 3, 28.0)                          # messages d'action du combat : texte de la meme taille que dans les dialogues
        self.infos = self.hdr['info']; self.couleurs = [tuple(c) for c in self.hdr['colors']]
        self.pousse = tuple(self.hdr['pushed'])
        self.cadres = lire_cadres(cadres) if cadres and os.path.exists(cadres) else []


def uv_icone(info, no, decal):
    """PartsInfo.SetUV : 4 sommets (HG, HD, BD, BG) de l'icone numero `no` dans la feuille."""
    n = no + info['startNo']; w = info['widthNum']
    col = int(math.fmod(n, w)); lig = int(n / w)          # division entiere du C (vers zero)
    u0 = col * info['uvsize']; v0 = -(info['startV'] + lig * info['uvsize']); u1 = u0 + info['uvsize']; v1 = v0 - info['uvsize']
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


class Fenetre:
    """Une fenetre de menu ouverte (un port du moteur) : etat modifiable d'apres les messages du moteur."""
    def __init__(self, ml, typ):
        self.ml = ml; self.typ = typ; self.t = ml.types[str(typ)]
        self.N = {}
        for n in self.t['nodes']:
            m = n.get('mesh')
            self.N[n['id']] = dict(id=n['id'], par=n['par'], pos=list(n['pos']), act=n['act'], mats=[dict(x) for x in n.get('mats', [])],
                                   vtx=[list(v) for v in m['vtx']] if m else None, uv=[list(v) for v in m['uv']] if m else None, sub=m['sub'] if m else None,
                                   text=dict(n['text']) if n.get('text') is not None else None, buttonId=(n.get('parts') or {}).get('buttonId'), pad=(n.get('parts') or {}).get('gamepad') or 0, etat=0, tcol=0, tscale=1.0)
        self.parts = self.t['parts']
        for pt in self.parts:
            nd = self.N.get(pt['node'])
            for ib in pt['ib']:
                if ib['k'] == 'bar' and nd and nd['vtx'] and ib['vtx'] + 1 < len(nd['vtx']):      # IBar.firstFunc : zero/largeur lus sur le quad
                    ib['zero'] = nd['vtx'][ib['vtx']][0]; ib['width'] = nd['vtx'][ib['vtx'] + 1][0] - nd['vtx'][ib['vtx']][0]
                elif ib['k'] == 'frame' and ib.get('init') is not None: self._cadre(ib, ib['init'])
        self.params = {}
        for p in self.t['params']: self.params[(p['id'], p['no'])] = p
        self.codes = {}
        for c in self.t['codes']: self.codes.setdefault(c['id'], []).append(c)
        for lst in self.codes.values():                       # codes « fonction » (plaque de monstre...) : le code -1 = rien a montrer, etat de depart
            for e in lst:
                if e['kind'] == 'func':
                    for nid, dd in ((e.get('fx') or {}).get('-1') or {}).get('d', {}).items():
                        if int(nid) in self.N and dd.get('act') is False: self.N[int(nid)]['act'] = False
        if self.t.get('name', '').startswith('Make_NameButton'):       # liste de 6 boutons mais le moteur n'en pilote que 5 (codes 0 a 4) : le 6e (en bas, sous « Sauvegarde rapide ») reste cache tant qu'aucun code ne le montre
            for e in self.codes.get(5, []):
                for nid, dd in ((e.get('fx') or {}).get('0') or {}).get('d', {}).items():
                    if int(nid) in self.N and dd.get('act') is False: self.N[int(nid)]['act'] = False
        self.vu = True; self.sel = None; self.sel_nd = None; self.ordre = 0
        self.nom_carte = None; self.carte = None            # fenetre de carte (type 25) : nom du plan, texture (posee par la visionneuse)
        self.symboles = []; self.t_blink = None; self.carte_mode = 3      # carte du monde : lieux decouverts (x, y en pixels du plan de 256 x 192), debut du clignotement ; mode de filtrage du plan

    # ---- application des messages
    def _ib(self, p):
        if 'parts' not in p or p['parts'] >= len(self.parts): return None, None
        pt = self.parts[p['parts']]
        return pt, (pt['ib'][p['base']] if p['base'] < len(pt['ib']) else None)

    def _cadre(self, ib, v):
        nd = self.N.get(ib.get('go'))
        if nd and 0 <= v < len(self.ml.cadres):
            c = self.ml.cadres[v]; nd['vtx'] = [list(x) for x in c['vtx']]; nd['uv'] = [list(x) for x in c['uv']]; nd['sub'] = {'0': c['tri']}

    def _barre(self, ib, pt, v):
        nd = self.N.get(pt['node'])
        if nd and nd['vtx']:
            o = ib['vtx']
            if v < 0: o -= 4; v = ~v
            if o + 2 < len(nd['vtx']) and o >= 0:
                x = ib['zero'] + ib['width'] * v * 0.01
                nd['vtx'][o + 1][0] = x; nd['vtx'][o + 2][0] = x

    def _enrobe(self, p):
        w = (p.get('custom') or {}).get('wrap')
        if not w or w['parts'] >= len(self.parts): return None, None
        pt = self.parts[w['parts']]
        return pt, (pt['ib'][w['base']] if w['base'] < len(pt['ib']) else None)

    def param_int(self, i, no, v):
        p = self.params.get((i, no))
        if not p: return
        if 'custom' in p:
            cu = p['custom']; pt, ib = self._enrobe(p)
            if cu.get('cls', '').endswith('ICityMap'): self.nom_carte = s; return                   # fenetre de carte (type 25) : nom de la texture du plan (Menu/map)
            if cu.get('cls', '').endswith('ItemNumCTRL'): self._item_num(i, v); return              # quantite d'une ligne de la liste d'objets (type 9)
            if cu.get('cls', '').endswith('BattleBar') and ib and ib['k'] == 'bar':      # BattleBar.Change(int) : barre normale
                cu['_v'] = v; self._barre(ib, pt, v)
            return
        if 'textcolor' in p and p['textcolor'] is not None:
            for ib in self.parts[p['textcolor']]['ib']:
                if ib['k'] == 'text' and ib.get('go') in self.N: self.N[ib['go']]['tcol'] = v
            return
        pt, ib = self._ib(p)
        if not ib: return
        k = ib['k']
        if k == 'icon':
            nd = self.N.get(pt['node'])
            if nd and nd['uv']:
                info = self.ml.infos[ib['partsNo']]; o = ib['vtx']
                for j, uv in enumerate(uv_icone(info, v, 0)):
                    if o + j < len(nd['uv']): nd['uv'][o + j] = list(uv)
        elif k == 'text':
            if ib.get('go') in self.N: self.N[ib['go']]['tcol'] = v
        elif k == 'bar': self._barre(ib, pt, v)
        elif k == 'button':
            nd = self.N.get(pt['node'])
            if nd: nd['etat'] = v
        elif k == 'frame': self._cadre(ib, v)

    def _item_num(self, i, v):
        """ItemNumCTRL.Changer(v) (0xD08060) : compteur passif a deux chiffres d'une ligne de la liste d'objets (Sub_ItemButton : IBase 3 = dizaines, IBase 4 = unites, feuille 12, cases de 32 px).
        v < 2 : deux cases vides (icone 1) ; sinon dizaines = (v / 10) % 10 (icone 16 x chiffre, ou 1 si zero), unites = icone 16 x (v % 10) ; 100 et plus se replient modulo 100 (123 -> 23).
        Les deux chiffres sont les IBase 3 et 4 de la MenuParts de la ligne (celle de l'element (ligne, 0))."""
        p0 = self.params.get((i, 0))
        if not p0 or p0.get('parts') is None or p0['parts'] >= len(self.parts): return
        pt = self.parts[p0['parts']]; nd = self.N.get(pt['node'])
        if nd is None or not nd['uv'] or len(pt['ib']) < 5: return
        if v < 2: dz, un = 1, 1
        else: d = (v // 10) % 10; dz = d * 16 if d else 1; un = (v % 10) * 16
        for ib, no in ((pt['ib'][3], dz), (pt['ib'][4], un)):
            if ib['k'] != 'icon': continue
            info = self.ml.infos[ib['partsNo']]; o = ib['vtx']
            for j, uv in enumerate(uv_icone(info, no, 0)):
                if o + j < len(nd['uv']): nd['uv'][o + j] = list(uv)

    def param_str(self, i, no, s):
        p = self.params.get((i, no))
        if not p: return
        if 'custom' in p:
            cu = p['custom']; pt, ib = self._enrobe(p)
            if cu.get('cls', '').endswith('BattleBar') and ib and ib['k'] == 'bar':      # BattleBar.Change(string) = RedApply : barre « rouge » = valeur courante
                self._barre(ib, pt, ~cu.get('_v', 0))
            return
        pt, ib = self._ib(p)
        if not ib or ib['k'] != 'text': return
        nd = self.N.get(ib.get('go'))
        if not nd or nd['text'] is None: return
        base = nd.setdefault('base', dict(cs=nd['text']['characterSize']))
        nd['tscale'] = 1.0; nd['text']['characterSize'] = base['cs']
        if ib.get('variant') == 1 and '^' in s:
            j = s.index('^')
            if j + 1 < len(s):
                c = ord(s[j + 1]) - 48
                if 0 <= c <= 5:
                    ech, cs = MARQUES_TEXTE[c]
                    hiro = self.ml.hdr['lang']['hiro']
                    nd['tscale'] = hiro if ech == 1.0 and c == 0 else (min(hiro * 1.4, 1.0) if c == 5 else 1.0)
                    if isinstance(cs, float): nd['text']['characterSize'] = cs
                    elif cs == 'base': nd['text']['characterSize'] = ib.get('fsize', base['cs'])
                s = s[:j] + s[j + 2:]
        elif ib.get('variant') == 1 and ib.get('fsize'): nd['text']['characterSize'] = ib['fsize']
        nd['text']['text'] = s; nd['vu'] = True

    def code(self, i, c):
        for e in self.codes.get(i, []):
            if e['kind'] == 'active':
                pt = self.parts[e['parts']]
                if pt['node'] in self.N: self.N[pt['node']]['act'] = (c != 0)
            elif e['kind'] == 'func':
                fx = (e.get('fx') or {}).get(str(c))
                if not fx: continue
                for nid, dd in fx['d'].items():
                    nd = self.N.get(int(nid))
                    if not nd: continue
                    if 'pos' in dd: nd['pos'] = list(dd['pos'])
                    if 'act' in dd: nd['act'] = bool(dd['act'])
                cache = {int(n) for v in e['fx'].values() for n, dd in v['d'].items() if dd.get('act') is False}
                for nid in cache:                   # un element que d'autres codes masquent est visible pour celui-ci s'il ne le masque pas
                    if str(nid) not in fx['d'] and nid in self.N: self.N[nid]['act'] = True
                for t in fx.get('tc', []):          # MenuParts.SetTextColor(code) : couleur des textes marques du masque
                    pt = self.parts[t['parts']] if t.get('parts') is not None else None
                    if pt:
                        for j, ib in enumerate(pt['ib']):
                            if (t['mask'] >> j) & 1 and ib['k'] == 'text' and ib.get('go') in self.N: self.N[ib['go']]['tcol'] = t['color']

    def selection(self, bouton):
        """Bouton choisi (curseur) : les elements de ce numero passent a l'etat « appuye »."""
        self.sel = bouton

    ID_ECHAP = 900001           # element ajoute par le portage (pas dans le jeu) : bouton « Menu Echap » de la liste des Parametres
    BTN_ECHAP = 100             # son numero de bouton (la liste n'en a que 0 a 5) : jamais envoye au moteur

    def nb_plaques(self):
        """Nombre de plaques de boutons de la liste visibles (le bouton ajoute par le portage n'en fait pas partie)."""
        return sum(1 for n in self.N.values() if n['buttonId'] is not None and 0 <= n['buttonId'] < self.BTN_ECHAP and n['mats'] and n['mats'][0].get('part') == 7 and self.visible(n['id']))

    def bouton_echap(self, oui, libelle):
        """Liste de boutons des Parametres (type 8) : un bouton de plus, une rangee AU-DESSUS du premier (meme gabarit, meme pas que les autres), qui ramene au menu Echap du portage.
        Copie de la plaque du bouton 0 et de son etiquette, decalees du pas entre deux plaques ; l'espace est libre (le cadre de la fenetre garde la place d'une rangee en haut).
        oui faux : le bouton est cache. -> vrai si le bouton est visible."""
        nd = self.N.get(self.ID_ECHAP)
        if nd is None:
            if not oui: return False
            pl = {n['buttonId']: n for n in self.N.values() if n['buttonId'] in (0, 1) and n['mats'] and n['mats'][0].get('part') == 7 and n['par'] is not None}
            if len(pl) < 2: return False
            p0, p1 = pl[0], pl[1]
            et = next((n for n in self.N.values() if n['par'] == p0['id'] and n['text'] is not None and abs(n['pos'][0] - p0['pos'][0]) < 5.0), None)       # l'etiquette centree sur la plaque (l'autre texte de la plaque est a droite)
            if et is None: return False
            dz = p0['pos'][2] - p1['pos'][2]
            def copie(n, **kw):
                c = dict(n); c['pos'] = list(n['pos']); c['mats'] = [dict(m) for m in n['mats']]
                c['vtx'] = [list(v) for v in n['vtx']] if n['vtx'] else n['vtx']; c['uv'] = [list(v) for v in n['uv']] if n['uv'] else n['uv']
                c['text'] = dict(n['text']) if n['text'] is not None else None
                for k in ('_pl', '_z0', 'base', 'vu'): c.pop(k, None)            # (caches propres a chaque element)
                c.update(kw); c['pos'][2] += dz; return c
            nd = copie(p0, id=self.ID_ECHAP, buttonId=self.BTN_ECHAP, pad=0x10, etat=0, act=True)
            te = copie(et, id=self.ID_ECHAP + 1, par=self.ID_ECHAP, act=True, tscale=1.0, tcol=0)
            te['text']['text'] = libelle; te['vu'] = True
            self.N[nd['id']] = nd; self.N[te['id']] = te
        nd['act'] = bool(oui)
        return bool(oui)

    # ---- plaques de noms de monstres (MenuPortItemTable.MonsterNamePlate, type 31)
    def _noeuds_plaque(self, i):
        for e in self.codes.get(i, []):
            fx = e.get('fx') or {}
            cadre = next(iter(((fx.get('-1') or {}).get('d') or {}).keys()), None)
            texte = next(iter(((fx.get('1') or {}).get('d') or {}).keys()), None)
            if cadre is not None and texte is not None: return int(cadre), int(texte)
        return None, None

    def plaque(self, i, nom, prm, code):
        """ReceiveParameters(code >= 1) : nom du monstre, fenetre ajustee a une ou deux lignes (VariableWindow 142 x 18 ou 36), masque des monstres du groupe."""
        cadre, texte = self._noeuds_plaque(i)
        if cadre is None or cadre not in self.N or texte not in self.N: return
        pl = getattr(self, 'pl', None)
        if pl is None: pl = self.pl = {}
        nc = self.N[cadre]
        if 'base_vtx' not in nc: nc['base_vtx'] = [list(v) for v in nc['vtx']]; pl_off = [a - b for a, b in zip(self.N[texte]['pos'], nc['pos'])]; nc['off_texte'] = pl_off
        if nom[:1] == '^' and len(nom) >= 2: nom = nom[2:]                    # marque de couleur : retiree par la plaque
        deux = '\n' in nom
        nc['vtx'] = [[x, z if deux else (z - 9.0 if z > 0 else z + 9.0)] for x, z in nc['base_vtx']]       # fenetre de 36 -> 18 de haut : lignes du haut/bas rapprochees du centre
        nt = self.N[texte]; nt['text']['text'] = nom; nt['vu'] = True; nt['tcol'] = 0
        mask = (prm[4] & 0xffff if len(prm) > 4 else 0) | ((prm[5] & 0xffff) << 16 if len(prm) > 5 else 0)
        pl[i] = dict(cadre=cadre, texte=texte, masque=mask, code=code, deux=deux)
        nc['act'] = True

    def disposer(self, n, proj):
        """b__1(code = nombre de plaques) : x = centre des monstres du groupe (borne a +-142), z = 105 (69 si plus de deux plaques), rangees de 58 vers le haut."""
        pl = getattr(self, 'pl', {})
        lst = [i for i in range(min(n, 4)) if i in pl]
        xs = {}
        for i in lst:
            b = proj(pl[i]['masque']) if proj else None
            xs[i] = (b[0] + b[1]) / 2 if b else 0.0
        zs = {i: (69.0 if n > 2 else 105.0) for i in lst}
        if n > 2:
            for k, i in enumerate(sorted(lst, key=lambda i: xs[i])):
                if 1 <= k <= n - 2: zs[i] += 58.0
        for i in lst:
            d = pl[i]; x = min(max(xs[i], -142.0), 142.0); z = zs[i]
            nc, nt = self.N[d['cadre']], self.N[d['texte']]
            nc['pos'] = [x, nc['pos'][1], z]; off = nc.get('off_texte', [0, 0, 0]); nt['pos'] = [x + off[0], nt['pos'][1], z + off[2]]

    def boutons(self, ident=False):
        """Zones tactiles (MenuParts d'un bouton : numero, touche de manette envoyee au moteur au relachement) : [(numero, manette, x0, z0, x1, z1, profondeur)] en unites d'interface ; ident : l'identifiant de l'element s'ajoute en fin de tuple."""
        out = []
        for nd in self.N.values():
            if not nd['pad'] or nd['buttonId'] is None or not nd['vtx'] or nd['etat'] == 2 or not self.visible(nd['id']): continue
            xs = [nd['pos'][0] + v[0] for v in nd['vtx']]; zs = [nd['pos'][2] + v[1] for v in nd['vtx']]
            out.append((nd['buttonId'], nd['pad'], min(xs), min(zs), max(xs), max(zs), nd['pos'][1]) + ((nd['id'],) if ident else ()))
        return out

    def bas(self):
        """Ordonnee (unites d'interface) du bord bas des parties visibles de la fenetre."""
        zs = [nd['pos'][2] + v[1] for nd in self.N.values() if nd['vtx'] and nd['mats'] and self.visible(nd['id']) for v in nd['vtx']]
        return min(zs) if zs else 0.0

    def etendue(self):
        """(bas, haut) en unites d'interface des parties visibles de la fenetre, ou None si rien n'est dessine."""
        zs = [nd['pos'][2] + v[1] for nd in self.N.values() if nd['vtx'] and nd['mats'] and self.visible(nd['id']) for v in nd['vtx']]
        return (min(zs), max(zs)) if zs else None

    def rects(self):
        """Rectangles (x0, z0, x1, z1) des elements dessines (visibles, avec maillage) de la fenetre : les cadres et les plaques."""
        out = []
        for nd in self.N.values():
            if nd['vtx'] and nd['mats'] and self.visible(nd['id']):
                xs = [nd['pos'][0] + v[0] for v in nd['vtx']]; zs = [nd['pos'][2] + v[1] for v in nd['vtx']]
                out.append((min(xs), min(zs), max(xs), max(zs)))
        return out

    def centrer_liste(self, z_haut, z_bas, rangees=0):
        """Fenetre de liste de boutons (Make_NameButton) placee entre deux etiquettes (« Rapide » / « Lent », « Bas » / « Haut » du reglage des vitesses et volumes) : les boutons visibles sont centres entre elles.
        Le jeu les place par du code (commandes 6 a 8, non extraites : « List index ») ; sans cela le dernier bouton tombe sur l'etiquette du bas. Le bouton retour (racine) ne bouge pas ; None remet la mise en page d'origine ; `rangees` (avec None) : toute la liste monte de ce nombre de rangees (pas entre deux plaques)."""
        racine = next((nd['id'] for nd in self.N.values() if nd['par'] is None), None)
        enfants = [nd for nd in self.N.values() if nd['par'] is not None]
        for nd in enfants:
            if '_z0' not in nd: nd['_z0'] = nd['pos'][2]
        dz = 0.0
        if z_haut is not None:
            plaques = [nd['_z0'] for nd in enfants if nd['buttonId'] is not None and nd['buttonId'] >= 0 and nd['vtx'] and self.visible(nd['id'])]
            if plaques: dz = (z_haut + z_bas) / 2 - (max(plaques) + min(plaques)) / 2
        elif rangees:
            pl = {nd['buttonId']: nd['_z0'] for nd in enfants if nd['buttonId'] in (0, 1) and nd['mats'] and nd['mats'][0].get('part') == 7}
            if 0 in pl and 1 in pl: dz = rangees * (pl[0] - pl[1])
        for nd in enfants: nd['pos'][2] = nd['_z0'] + dz
        return dz

    def etendue_x(self):
        """(gauche, droite) en unites d'interface de toutes les parties de la fenetre (visibles ou non : la mise en page ne change pas), ou None : limites dans lesquelles un texte doit tenir. Mis en cache."""
        c = getattr(self, '_ex_cache', None)
        if c is None:
            xs = [nd['pos'][0] + v[0] for nd in self.N.values() if nd['vtx'] and nd['mats'] for v in nd['vtx']]
            c = self._ex_cache = ((min(xs), max(xs)) if xs else None,)
        return c[0]

    def visible(self, nid):
        while nid is not None:
            nd = self.N.get(nid)
            if nd is None: return True
            if not nd['act']: return False
            nid = nd['par']
        return True


class FenetreMessage:
    """Fenetre de message du jeu (MenuMessage) : cadre (frameData) + canevas de texte dessine par le moteur + curseur de fin de page.
    Le canevas est une texture 512 x 512 qui boucle ; le defilement `[3, y]` decale l'origine verticale de ses UV de (y & 0x1ff) / 512."""
    def __init__(self, ml):
        self.ml = ml; self.d = ml.message; self.vu = True; self.sel = None; self.sel_nd = None; self.ordre = 0
        self.type = -1; self.y = 0; self.feed = False; self.N = {}
        self.regler(0, 0, False)

    @staticmethod
    def _nd(nid, pos, vtx, uv, tris, mat):
        return dict(id=nid, par=None, pos=pos, act=True, mats=[mat], vtx=vtx, uv=uv, sub={'0': tris}, text=None, buttonId=None, etat=0, tcol=0, tscale=1.0)

    def regler(self, typ, y, feed):
        """typ = type de fenetre (0 terrain, 1-3 combat), y = defilement du canevas, feed = curseur de fin de page."""
        ts = self.d['types']; t = ts[typ] if 0 <= typ < len(ts) else ts[0]
        fm = self.d.get('frame_mats') or [{'sheet': 0, 'part': 4}]
        if typ != self.type:
            self.type = typ; w = t['win']; cv = t['canvas']; fl = t['feed_local']; fd = self.d['feed']
            self.N = {
                'cadre': self._nd('cadre', list(w), t['frame_mesh']['vtx'], t['frame_mesh']['uv'], t['frame_mesh']['tris'], dict(sheet=fm[0]['sheet'], part=fm[0]['part'], color=None)),
                'canevas': self._nd('canevas', [w[0], w[1] + 4.0, w[2]], [[v[0], v[2]] for v in cv['vtx']], [list(u) for u in cv['uv']], cv['tris'], dict(sheet='msg', color=[1, 1, 1, 1])),
                'curseur': self._nd('curseur', [w[0] + fl[0], w[1] + fl[1] + 6.0, w[2] + fl[2]], fd['vtx'], fd['uv'], fd['tris'], dict(sheet=fd['mats'][0]['sheet'], part=fd['mats'][0]['part'], color=None)),
            }
            self.uv0 = [list(u) for u in cv['uv']]
        self.N['curseur']['act'] = bool(feed); self.feed = bool(feed)
        if y != self.y or typ != getattr(self, '_ty', None):
            self.y = y; self._ty = typ
            dv = (int(y) & 0x1ff) / 512.0
            self.N['canevas']['uv'] = [[u[0], u[1] + dv] for u in self.uv0]

    def visible(self, nid):
        nd = self.N.get(nid)
        return bool(nd and nd['act'])

    def etendue(self):
        c = self.N.get('cadre')
        return (c['pos'][2] + min(v[1] for v in c['vtx']), c['pos'][2] + max(v[1] for v in c['vtx'])) if c and c['vtx'] else None

    def bas(self):
        """Ordonnee (unites d'interface) du bord bas du cadre."""
        c = self.N.get('cadre')
        return c['pos'][2] + min(v[1] for v in c['vtx']) if c and c['vtx'] else 0.0


class Textes:
    """Lignes de texte -> textures (police du jeu rendue par Pillow, blanche ; la couleur est appliquee au dessin)."""
    def __init__(self, police):
        self.police = police; self.pol = {}; self.tex = {}
    def _font(self, px):
        from PIL import ImageFont
        f = self.pol.get(px)
        if f is None:
            for chemin in (self.police, 'DejaVuSans.ttf', 'arial.ttf'):
                try: f = ImageFont.truetype(chemin, px); break
                except Exception: f = None
            if f is None: f = ImageFont.load_default()
            self.pol[px] = f
        return f
    def ligne(self, texte, px):
        """-> (texture, largeur, hauteur, base) ; base = distance du haut de l'image a la ligne de base."""
        k = (texte, px)
        r = self.tex.get(k)
        if r is None:
            from PIL import Image, ImageDraw
            if len(self.tex) > 600:
                for t, *_ in self.tex.values(): t.delete() if hasattr(t, 'delete') else None
                self.tex.clear()
            f = self._font(px); asc, desc = f.getmetrics(); w = int(math.ceil(f.getlength(texte))) + 4; h = asc + desc + 4
            im = Image.new('L', (w, h), 0); ImageDraw.Draw(im).text((2, 2 + asc), texte, font=f, fill=255, anchor='ls')
            a = np.zeros((h, w, 4), np.uint8); a[..., :3] = 255; a[..., 3] = np.asarray(im)
            img = pyglet.image.ImageData(w, h, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=w * 4)
            t = img.get_texture(); gl.glBindTexture(t.target, t.id)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
            r = self.tex[k] = (t, w, h, 2 + asc)
        return r


class Rendu:
    """Dessine des Fenetre sur l'ecran : prog GL maison, feuilles 0 (MenuTexture) et 1 (Button)."""
    def __init__(self, ml, feuilles, police):
        self.ml = ml; self.voisins = []                      # voisins : fenetres visibles de l'image (leurs cadres servent a compresser les textes d'une fenetre sans cadre)
        self.prog = ShaderProgram(Shader(VERT, 'vertex'), Shader(FRAG, 'fragment'))
        self._blanc = None                                  # texture blanche de 1 pixel (carres de couleur unie : lieux de la carte du monde)
        self.tex = {}
        from hd import _dilater
        for k, arr in feuilles.items():
            arr = _dilater(arr, 3)                          # pixels transparents = couleur du bord voisin (alpha inchange) : les cases de ces feuilles gardent du blanc / rose sous leurs pixels transparents, que le filtrage lineaire ramenait en liseré clair (« aura ») autour des icones et des portraits
            h, w = arr.shape[:2]
            img = pyglet.image.ImageData(w, h, 'RGBA', np.ascontiguousarray(arr[::-1]).tobytes(), pitch=w * 4)
            t = img.get_texture(); gl.glBindTexture(t.target, t.id)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            self.tex[k] = t
        self.textes = Textes(police)

    def maj_canevas(self, a, nom='msg'):
        """Canevas de texte du moteur (512 x 512 octets d'opacite) -> texture « msg » (blanc, alpha = opacite), qui boucle comme dans Unity."""
        h, w = a.shape
        rgba = np.empty((h, w, 4), np.uint8); rgba[..., :3] = 255; rgba[..., 3] = a
        img = pyglet.image.ImageData(w, h, 'RGBA', np.ascontiguousarray(rgba).tobytes(), pitch=w * 4)      # ligne 0 en premier = v 0, comme la texture Unity
        t = img.get_texture(); gl.glBindTexture(t.target, t.id)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        self.tex[nom] = t

    # ---- construction des elements a dessiner
    def _items(self, fen):
        """-> liste de (profondeur, ordre, genre, donnees) d'une fenetre."""
        items = []; o = 0
        for nd in fen.N.values():
            if not fen.visible(nd['id']): continue
            o += 1
            if nd['vtx']: items.append((nd['pos'][1], o, 'm', (fen, nd)))
            if nd['text'] is not None and nd['text'].get('text'): items.append((nd['pos'][1] + 0.001, o, 't', (fen, nd)))
        items.sort(key=lambda x: (x[0], x[1]))
        return items

    def dessiner(self, fens, cx, cy, s, vp):
        """fens : liste de Fenetre ; (cx, cy) = pixel du centre de l'ecran du jeu ; s = pixels par unite ; vp = (largeur, hauteur) de la fenetre."""
        if not fens: return
        items = []
        for wi, fen in enumerate(fens): items += [(d, wi, o, g, x) for d, o, g, x in self._items(fen)]
        for wi, fen in enumerate(fens):
            if getattr(fen, 'typ', 0) in (25, 26) and fen.carte is not None: items.append((1.0, wi, 0, 'c', (fen, None)))         # plan : au-dessus du fond du cadre (profondeur 0), sous le marqueur (12 et plus)
        items.sort(key=lambda x: x[:3])                      # comme Unity (objets transparents tries par profondeur sur la camera) : profondeur d'abord, puis la fenetre la plus recente devant ; le fond d'une fenetre ne recouvre plus les boutons d'une autre
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA); gl.glDisable(gl.GL_DEPTH_TEST)
        self.prog.use(); self.prog['vp'] = (float(vp[0]), float(vp[1]))
        lot = None; buf = []
        def vider():
            nonlocal buf
            if buf and lot:
                a = np.concatenate(buf).astype(np.float32); n = len(a)
                vl = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', a[:, 0:2].ravel()), tex_coords=('f', a[:, 2:4].ravel()), colors=('f', a[:, 4:8].ravel()))
                gl.glActiveTexture(gl.GL_TEXTURE0); gl.glBindTexture(lot[0].target, lot[0].id); self.prog['mode'] = lot[1]
                vl.draw(gl.GL_TRIANGLES); vl.delete()
            buf = []
        ok_num = {id(fen): {n.get('buttonId') for n in fen.N.values() if n.get('pad') and not (n['pad'] & 0xA0) and n.get('buttonId') is not None and n.get('vtx')} for fen in fens}       # numeros portes par un bouton de validation (manette 16 / 64)
        for _, _, _, g, (fen, nd) in items:
            if g == 'c':
                vider(); lot = None; self._carte(fen, cx, cy, s, vp); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            elif g == 'm':
                for k, mat in enumerate(nd['mats']):
                    idx = nd['sub'].get(str(k))
                    if not idx: continue
                    sh = mat.get('sheet')
                    if sh not in self.tex: continue
                    col = list(mat.get('color') or (1, 1, 1, 1)); mode = 0; off = (0.0, 0.0)
                    if k == 0 and nd['buttonId'] is not None and 'part' in mat and mat['part'] == 10 and nd['buttonId'] < 0 and fen.sel_nd == nd['id']:
                        col[:3] = [1.4, 1.4, 1.4]                                       # fleche de page survolee (PC) : eclaircie
                    elif k == 0 and nd['buttonId'] is not None and (nd['buttonId'] >= 0 or fen.sel_nd == nd['id']) and 'part' in mat and mat['part'] == 7:
                        if fen.sel_nd is not None: etat = 1 if nd['id'] == fen.sel_nd else nd['etat']       # souris : seul l'element pointe (ou appuye) est en surbrillance, pas toute la rangee qui partage son numero
                        else: etat = 1 if (fen.sel is not None and fen.sel == nd['buttonId'] and not ((nd['pad'] or 0) & 0xA0 and nd['buttonId'] in ok_num[id(fen)])) else nd['etat']       # un bouton d'annulation (manette 32 / 128, ex. « Rien ») qui partage son numero avec un bouton de validation (« Acheter ») ne s'allume pas avec lui
                        if etat == 1 or etat == 4: off = self.ml.pousse
                        if etat == 2: col[3] = 0.0
                        if etat == 3: mode = 1
                        if etat == 4: mode = 2
                    if col[3] <= 0: continue
                    t = self.tex[sh]
                    if lot != (t, mode): vider(); lot = (t, mode)
                    v = np.array(nd['vtx'], np.float32); u = np.array(nd['uv'], np.float32)
                    ia = np.array(idx, np.int64); vv = v[ia]; uu = u[ia] + np.array(off, np.float32)
                    x = cx + (nd['pos'][0] + vv[:, 0]) * s; y = cy + (nd['pos'][2] + vv[:, 1]) * s
                    c = np.tile(np.array(col, np.float32), (len(ia), 1))
                    buf.append(np.column_stack([x, y, uu[:, 0], uu[:, 1], c]))
            else:
                vider(); lot = None
                self._texte(fen, nd, cx, cy, s)
        vider()

    def _modele_plaque(self):
        """Maillage de la plaque de bouton du jeu (feuille Button, partie 7, neuf morceaux de la fenetre « liste » Make_NameButton) : sommets, UV, indices, couleur."""
        m = getattr(self, '_mdl_plaque', None)
        if m is None:
            m = False
            for t in self.ml.types.values():
                for n in t.get('nodes', []):
                    mm = n.get('mesh'); mats = n.get('mats') or []
                    if mm and mats and mats[0].get('sheet') == 1 and mats[0].get('part') == 7 and len(mm['vtx']) == 36 and n.get('parts', {}).get('buttonId') == 0:
                        m = (np.array(mm['vtx'], np.float32), np.array(mm['uv'], np.float32), np.array(mm['sub']['0'], np.int64), list(mats[0].get('color') or (1, 1, 1, 1))); break
                if m: break
            self._mdl_plaque = m
        return m or None

    def plaque(self, x, y, w, h, vp, choisi=False):
        """Dessine le fond d'un bouton exactement comme les fenetres du jeu (ex. « Soigner tous ») dans le rectangle pixel (x, y, w, h) : les coins gardent leurs proportions (16 unites pour 50 de haut),
        le milieu s'etire. choisi : version enfoncee de la feuille (celle d'un bouton choisi dans le jeu). -> False si la plaque du jeu est indisponible."""
        mod = self._modele_plaque()
        if mod is None or 1 not in self.tex: return False
        vtx, uv, idx, col = mod
        xs = sorted({round(float(v[0]), 2) for v in vtx}); zs = sorted({round(float(v[1]), 2) for v in vtx})          # quatre abscisses et quatre ordonnees : bords et limites des coins
        cap = min((xs[1] - xs[0]) * h / (zs[-1] - zs[0]), w / 2.0, h / 2.0)                                              # le coin garde sa proportion avec la hauteur de la plaque
        X = {xs[0]: x, xs[1]: x + cap, xs[2]: x + w - cap, xs[3]: x + w}; Y = {zs[3]: y + h, zs[2]: y + h - cap, zs[1]: y + cap, zs[0]: y}
        px = np.array([X[round(float(v[0]), 2)] for v in vtx[idx]], np.float32); py = np.array([Y[round(float(v[1]), 2)] for v in vtx[idx]], np.float32)
        uu = uv[idx] + (np.array(self.ml.pousse, np.float32) if choisi else 0.0)
        a = np.column_stack([px, py, uu[:, 0], uu[:, 1], np.tile(np.array(col, np.float32), (len(idx), 1))]).astype(np.float32)
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA); gl.glDisable(gl.GL_DEPTH_TEST)
        self.prog.use(); self.prog['vp'] = (float(vp[0]), float(vp[1]))
        vl = self.prog.vertex_list(len(a), gl.GL_TRIANGLES, position=('f', a[:, 0:2].ravel()), tex_coords=('f', a[:, 2:4].ravel()), colors=('f', a[:, 4:8].ravel()))
        t = self.tex[1]; gl.glActiveTexture(gl.GL_TEXTURE0); gl.glBindTexture(t.target, t.id); self.prog['mode'] = 0
        vl.draw(gl.GL_TRIANGLES); vl.delete(); self.prog.stop()
        return True

    def _carte(self, fen, cx, cy, s, vp):
        """Plan de la fenetre de carte (ICityMap) : texture 4:3 (plan agrandi, voile compris) affichee en 450 x 337,5 sous le cadre (de x = -225 a 225, de z = 400 vers le bas)."""
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA); gl.glDisable(gl.GL_DEPTH_TEST)
        self.prog.use(); self.prog['vp'] = (float(vp[0]), float(vp[1]))
        x0, x1, y1, y0 = cx - 225.0 * s, cx + 225.0 * s, cy + 400.0 * s, cy + (400.0 - 337.5) * s
        u0, v0, u1, v1 = getattr(fen, 'carte_uv', None) or (0.0, 0.0, 1.0, 1.0)          # grande carte du monde : fenetre de 256 x 192 pixels du plan de 1024 x 1024, centree sur le joueur
        a = np.array([[x0, y0, u0, v0], [x1, y0, u1, v0], [x1, y1, u1, v1], [x0, y0, u0, v0], [x1, y1, u1, v1], [x0, y1, u0, v1]], np.float32)
        vl = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', a[:, 0:2].ravel()), tex_coords=('f', a[:, 2:4].ravel()), colors=('f', np.ones(24, np.float32)))
        t = fen.carte; gl.glActiveTexture(gl.GL_TEXTURE0); gl.glBindTexture(t.target, t.id); self.prog['mode'] = getattr(fen, 'carte_mode', 3)         # plans agrandis (HD, voile compris) : filtrage lineaire ; grande carte du monde : bilineaire net
        vl.draw(gl.GL_TRIANGLES); vl.delete(); self.prog['mode'] = 0
        sy = getattr(fen, 'symboles', None)
        if sy:                                                                        # lieux decouverts (BlinkMapSymbol) : carres rouges de 4 unites dont la transparence va et vient (0,5 par seconde : 1 -> 0 -> 1 en 4 s)
            if self._blanc is None:
                self._blanc = pyglet.image.ImageData(1, 1, 'RGBA', b'\xff\xff\xff\xff').get_texture()
            al = abs(1.0 - ((time.monotonic() - (fen.t_blink or 0.0)) % 4.0) / 2.0); k = 450.0 / 256.0; q = []
            for xb, yb in sy:
                a0, b0 = cx + (-225.0 + xb * k - 2.0) * s, cy + (400.0 - yb * k - 2.0) * s; a1, b1 = a0 + 4.0 * s, b0 + 4.0 * s          # carre de 4 unites centre sur le lieu (comme le marqueur du joueur, de 24 unites, centre sur sa position)
                q += [[a0, b0], [a1, b0], [a1, b1], [a0, b0], [a1, b1], [a0, b1]]
            q = np.array(q, np.float32); n = len(q)
            vl = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', q.ravel()), tex_coords=('f', np.zeros(n * 2, np.float32)), colors=('f', np.tile(np.array([1.0, 0.0, 0.0, al], np.float32), n)))
            t = self._blanc; gl.glBindTexture(t.target, t.id); vl.draw(gl.GL_TRIANGLES); vl.delete()

    MARGE_PLAQUE = 7.0          # marge (unites d'interface) laissee de chaque cote entre le texte et le bord de la plaque d'un bouton

    def _largeur_plaque(self, fen, nd, zp):
        """Largeur utile (unites) de la plaque de bouton (partie 7) qui porte ce texte centre, ou None : la plaque dont le rectangle contient le point d'ancrage du texte."""
        t = nd['text']
        if t['anchor'] % 3 != 1: return None
        c = nd.get('_pl')
        if c is None or c[0] is not fen.t:
            r = None
            for o in fen.N.values():
                if o is nd or not o['vtx'] or not o['mats'] or o['mats'][0].get('part') != 7 or o['buttonId'] is None: continue
                xs = [o['pos'][0] + v[0] for v in o['vtx']]; zs = [o['pos'][2] + v[1] for v in o['vtx']]
                if min(xs) <= nd['pos'][0] <= max(xs) and min(zs) <= zp <= max(zs): r = max(xs) - min(xs) - 2 * self.MARGE_PLAQUE; break
            nd['_pl'] = c = (fen.t, r)
        return c[1]

    def _texte(self, fen, nd, cx, cy, s):
        t = nd['text']; lang = self.ml.hdr['lang']
        lignes = t['text'].split('\n'); N = len(lignes)
        em = TAILLE_POLICE * t['characterSize'] * 0.1 * nd['tscale']; emy = TAILLE_POLICE * t['characterSize'] * 0.1
        pas = HAUTEUR_LIGNE * emy * t['lineSpacing']; asc = 0.88 * emy
        zp = nd['pos'][2] - lang['dy']                                  # le jeu ajoute dy a la position du texte (compensation de l'interligne de la police)
        ts = nd['tscale']
        row = t['anchor'] // 3; col = t['anchor'] % 3
        hb = N * pas                                                    # hauteur du bloc de texte
        haut = zp + (hb if row == 2 else hb / 2 if row == 1 else 0.0)       # TextMesh.anchor : le point d'ancrage est le haut (0-2), le milieu (3-5) ou le bas (6-8) du bloc de texte
        base0 = haut - asc
        px = max(6, int(round(emy * s)))
        def teinte(i):
            pal = self.ml.couleurs[i] if 0 <= i < len(self.ml.couleurs) else (1, 1, 1, 1)
            return (min(pal[0], 1.0), min(pal[1], 1.0), min(pal[2], 1.0), 1.0)
        segs_l = []; cur = nd['tcol']                                    # « @cN » change la couleur du texte (palette du jeu) ; elle se prolonge d'une ligne a l'autre
        for l in lignes:
            segs = []; pos = 0
            for m in re.finditer(r'@c(\d)', l):
                if m.start() > pos: segs.append((l[pos:m.start()], cur))
                cur = int(m.group(1)); pos = m.end()
            if pos < len(l): segs.append((l[pos:], cur))
            segs_l.append(segs)
        larg = [sum((self.textes.ligne(t, px)[1] - 4) / s * ts for t, _ in segs) for segs in segs_l]
        bl = max(larg) if larg else 0.0
        dispo = self._largeur_plaque(fen, nd, zp)
        if dispo is None and fen.etendue_x() is None and not fen.rects():              # fenetre sans cadre propre (titre et etiquettes d'un reglage) : le cadre est dans une autre fenetre visible, on prend le plus petit rectangle qui contient le point d'ancrage
            xa = nd['pos'][0]; z_a = nd['pos'][2] - lang['dy']; r_min = None
            for v in self.voisins:
                for (x0, z0, x1, z1) in v.rects():
                    if x0 <= xa <= x1 and z0 <= z_a <= z1 and (r_min is None or (x1 - x0) * (z1 - z0) < (r_min[2] - r_min[0]) * (r_min[3] - r_min[1])): r_min = (x0, z0, x1, z1)
            if r_min:
                dispo = {0: r_min[2] - self.MARGE_PLAQUE - xa, 1: 2 * min(xa - r_min[0], r_min[2] - xa) - 2 * self.MARGE_PLAQUE, 2: xa - r_min[0] - self.MARGE_PLAQUE}[col]
        if dispo is None and bl > 0:                                     # hors plaque de bouton : le texte doit tenir dans la largeur de sa fenetre (a partir de son point d'ancrage, avec la meme marge)
            ex = fen.etendue_x(); xa = nd['pos'][0]
            if ex and ex[0] <= xa <= ex[1]:
                dispo = {0: ex[1] - self.MARGE_PLAQUE - xa, 1: 2 * min(xa - ex[0], ex[1] - xa) - 2 * self.MARGE_PLAQUE, 2: xa - ex[0] - self.MARGE_PLAQUE}[col]
                if dispo < 0.4 * bl: dispo = None                         # (ancrage trop pres du bord pour que ce soit le texte qui soit trop large)
        if dispo and bl > dispo:                                         # texte plus large que le bouton qui le porte (traduction plus longue que l'original) : compresse en largeur pour tenir dedans
            f = max(0.7, dispo / bl); ts *= f; larg = [w * f for w in larg]; bl *= f
        for i, segs in enumerate(segs_l):
            if not segs: continue
            lw = larg[i]
            ax = {0: 0.0, 1: lw / 2, 2: lw}[col]                         # point d'ancrage horizontal sur la ligne
            al = {0: 0.0, 1: (bl - lw) / 2, 2: bl - lw}[t['alignment']]  # alignement de la ligne dans le bloc
            bx = {0: 0.0, 1: bl / 2, 2: bl}[col]
            xs = nd['pos'][0] - bx + al
            y_base = base0 - i * pas
            for texte, ci in segs:
                tex, w, h, b = self.textes.ligne(texte, px)
                x = cx + xs * s - 2 * ts; y = cy + y_base * s - (h - b)
                wd = w * ts
                a = np.array([[x, y, 0, 0], [x + wd, y, 1, 0], [x + wd, y + h, 1, 1], [x, y, 0, 0], [x + wd, y + h, 1, 1], [x, y + h, 0, 1]], np.float32)
                vl = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', a[:, 0:2].ravel()), tex_coords=('f', a[:, 2:4].ravel()), colors=('f', np.tile(np.array(teinte(ci), np.float32), 6)))
                gl.glActiveTexture(gl.GL_TEXTURE0); gl.glBindTexture(tex.target, tex.id); self.prog['mode'] = 0
                vl.draw(gl.GL_TRIANGLES); vl.delete()
                xs += (w - 4) / s * ts


class Gestionnaire:
    """Recoit ce que l'interface du jeu memorise (Interface.obs) et tient une Fenetre par port de menu."""
    def __init__(self, ml):
        self.ml = ml; self.f = {}
    def ouvrir(self, port, typ):
        t = self.ml.types.get(str(typ))
        if t and not t.get('err') and t.get('nodes'): self.f[port] = Fenetre(self.ml, typ)
        else: self.f.pop(port, None)
    def fermer(self, port): self.f.pop(port, None)
    def rejouer(self, ui):
        """Les fenetres des ports 2 a 11 (menus du terrain) sont creees par le moteur au demarrage, avant que la visionneuse n'ecoute : on rejoue leur creation et leur contenu."""
        for port, f in sorted(ui.f.items()):
            if f.get('type') is None: continue
            self.ouvrir(port, f['type'])
            for (i, no), txt in f['cases'].items(): self.param_str(port, i, no, txt)
            for (i, no), v in (f.get('ints') or {}).items(): self.param_int(port, i, no, v)
            for i, c in f['indic'].items(): self.code(port, i, c)
            for i, q in (f.get('plaq') or {}).items():
                if 'nom' in q and 'prm' in q: self.plaque(port, i, q['nom'], q['prm'], q['code'])
            if f.get('dispo') is not None: self.disposer(port, f['dispo'])
            if f.get('cur') is not None: self.selection(port, f['cur'])
    def param_int(self, port, i, no, v):
        f = self.f.get(port)
        if f: f.param_int(i, no, v)
    def param_str(self, port, i, no, s):
        f = self.f.get(port)
        if f: f.param_str(i, no, s)
    def code(self, port, i, c):
        f = self.f.get(port)
        if f: f.code(i, c)
    def selection(self, port, b):
        f = self.f.get(port)
        if f: f.selection(b)
    proj = None            # appelee avec un masque de monstres -> (x min, x max) en unites d'interface, ou None (fournie par la visionneuse)
    def plaque(self, port, i, nom, prm, code):
        f = self.f.get(port)
        if f: f.plaque(i, nom, prm, code)
    def disposer(self, port, n):
        f = self.f.get(port)
        if f: f.disposer(n, self.proj)


RESSOURCES = {'ui_MenuTexture.png': 'MenuTexture', 'ui_Button.png': 'Button'}


def preparer_ressources(dossier_apk, cache, log=print):
    """Extrait des APK du jeu (une seule fois) : feuilles MenuTexture et Button, police, maillages des cadres. -> True si tout est la."""
    dest = {n: os.path.join(cache, n) for n in list(RESSOURCES) + ['ui_font.otf', 'ui_frameData.bin']}
    if all(os.path.exists(p) for p in dest.values()): return True
    try:
        import UnityPy, zipfile
        os.makedirs(cache, exist_ok=True)
        log('Lecture des ressources de menu du jeu (une seule fois)...')
        base = UnityPy.load(os.path.join(dossier_apk, 'base.apk'))
        for o in base.objects:
            if o.type.name == 'Texture2D':
                d = o.read()
                for fich, nom in RESSOURCES.items():
                    if d.m_Name == nom and not os.path.exists(dest[fich]): d.image.convert('RGBA').save(dest[fich])
            elif o.type.name == 'Font':
                d = o.read()
                if d.m_Name == 'GMaruGoPro-M' and d.m_FontData and not os.path.exists(dest['ui_font.otf']):
                    open(dest['ui_font.otf'], 'wb').write(bytes(d.m_FontData))
        if not os.path.exists(dest['ui_frameData.bin']):
            pack = UnityPy.load(zipfile.ZipFile(os.path.join(dossier_apk, 'split_UnityDataAssetPack.apk')).read('assets/bin/Data/datapack.unity3d'))
            for o in pack.objects:
                if o.type.name == 'TextAsset':
                    d = o.read()
                    if d.m_Name == 'frameData':
                        raw = d.m_Script; open(dest['ui_frameData.bin'], 'wb').write(raw.encode('utf-8', 'surrogateescape') if isinstance(raw, str) else bytes(raw)); break
        return all(os.path.exists(p) for p in dest.values())
    except Exception as e:
        log('Ressources de menu indisponibles : %r' % (e,)); return False
