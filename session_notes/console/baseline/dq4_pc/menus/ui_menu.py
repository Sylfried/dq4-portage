"""Fenetres de menu du jeu d'origine : mise en page exacte (lue dans le code Unity du jeu, voir tools/ui_il2cpp), dessinee avec les feuilles du jeu.

Le fichier de mise en page (cache/ui_layout.json) decrit, pour chaque type de fenetre (Make_* de MenuPortItemTable) : les objets (position, maillage,
materiaux, texte), les elements modifiables (IText / IIcon / IButton / IBar...) et leurs liaisons (id, no) -> element, et l'effet de chaque code
(deplacement / affichage). Ce module applique les messages du moteur (setItemParam*, setItemCode, curseur) a ces objets et les dessine.
Repere du jeu : portrait 450 x 800, X vers la droite, Z vers le haut, origine au centre de l'ecran, Y = profondeur (plus grand = devant)."""
import os, re, json, math, time
import numpy as np
import pyglet
from pyglet import gl
from pyglet.graphics.shader import Shader, ShaderProgram
from dq4_pc.language import tr

VERTEX = '''#version 330 core
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

LINE_HEIGHT = 1.246     # (police de repli GMaruGoPro-M, utilisee seulement sans ui_garrir.*) hauteur de ligne de la police en « em » (OS/2 winAscent + winDescent de GMaruGoPro-M) : recoupe l'espacement des barres PV/MF (28 px) et le centrage des boutons
FONT_SIZE = 19.0        # (repli GMaruGoPro-M) taille native de la police du jeu (GMaruGoPro-M, Font.fontSize) : 1 caractere = taille_caractere * 0.1 * 19 unites
TEXT_MARKS = {0: (1.0, None), 1: (1.0, 8.0), 2: (1.0, 'base'), 3: (1.0, 9.0), 4: (1.0, 6.25), 5: ('x14', 'base')}   # "^n" en tete d'un texte (IText) : (echelle x, taille de caractere)
TEXT_CENTERING = os.environ.get('DQ_TEXTE_ORIGINAL', '') not in ('1', 'true')      # DQ_TEXTE_ORIGINAL=1 (test) : placement vertical exact du jeu d'origine, sans le recentrage optique (voir text_recentering)


def first_line_baseline(zp, row, n, step, asc):
    """Ordonnee (unites, vers le haut) de la ligne de base de la 1re ligne d'un TextMesh : TextMesh.anchor pose le point d'ancrage zp en haut (row 0), au milieu (1) ou en bas (2) d'un bloc de n lignes de hauteur `step`
    (= interligne de la police x characterSize x 0,1 x lineSpacing) ; la ligne de base est `asc` (ascent de la police x characterSize x 0,1) sous le haut de la ligne, quel que soit lineSpacing.
    Verifie sur la capture du mobile (ecran4 : « Rat volant » 1 ligne, « Scarapince / x2 » 3 lignes, onglet « Ragnar »), a 0,3 unite pres."""
    hb = n * step
    return zp + (hb if row == 2 else hb / 2 if row == 1 else 0.0) - asc


def text_recentering(leading, u, ls):
    """Remontee (unites) a appliquer au texte pour centrer l'encre dans sa ligne. Le jeu a regle lineSpacing (0,441 cibles, 0,481 plaques de monstres, 0,801 onglets / boutons / noms...) pour la police japonaise : la boite de ligne
    est raccourcie de (1 - ls) mais la ligne de base reste a `ascent` du haut de la ligne, donc avec SE-GARRIR (encre centree dans sa boite naturelle de 23,5 px) le texte descend de (1 - ls) x interligne x u / 2 sous le centre de sa boite
    (6,5 unites pour « Rat volant » et les plaques : texte colle au bas du cadre). Applique aux trois ancrages verticaux (l'ecart encre / boite ne depend pas de l'ancrage ; seul le cas milieu a une reference mobile, ecran4). lineSpacing >= 1 (PV / PM / Nv., regles sur les jauges) : 0. ECART VOLONTAIRE avec le jeu d'origine, qui a le meme defaut."""
    return leading * u * (1.0 - ls) / 2 if TEXT_CENTERING and ls < 1.0 else 0.0


# Etats d'un bouton (MenuParts.BUTTON_STATE_*, param (id, 0) d'une plaque) : 0 normal, 1 enfonce, 2 invisible, 3 grise (shader gris), 4 inverse (shader inverse, enfonce).
STATE_NORMAL, STATE_PRESSED, STATE_INVISIBLE, STATE_GRAYED, STATE_INVERTED = 0, 1, 2, 3, 4
AUTO_CAPTION = 'Sauvegarde automatique'      # chaine 623 du jeu (patch FR) : l'etiquette de la plaque auto quand le moteur n'en envoie pas (il ne l'envoie qu'avec un data5.dat valide)
TEXT_GRAY = 3                               # MenuParts.TEXT_COLOR_GRAY : couleur de texte d'un bouton grise (palette du jeu)
AUTO_BUTTON = 4                              # numero du bouton « Sauvegarde automatique » du menu de depart (type 53, cellule (4, 1) du moteur, banque 4 = data5.dat)


def is_state_active(state):
    """Un bouton reagit-il au contact (souris, tactile) et a la validation ? MenuParts.IButton : le fichier de rappel des etats (RVA 0xD043CC) coupe le test de contact (`defaultIsHit`, 0xCFDB6C) pour les etats 2 (invisible),
    3 (grise) et 4 (inverse) ; normal et enfonce le laissent actif. Un bouton grise n'est donc ni survole ni choisi, et le moteur ne recoit rien."""
    return state not in (STATE_INVISIBLE, STATE_GRAYED, STATE_INVERTED)


def expand_tabs(s, tab_size):
    """TextMesh.tabSize : une tabulation vaut `tabSize` fois la largeur d'une espace (8 pour « Cout en PM:\t  2 » des magies et la ligne « Nv. » de l'ordre de marche, 25 pour le « x2 » des plaques de groupe) ; la police du jeu n'a pas de glyphe pour « \t » :
    elle comptait pour rien et le texte suivant collait a ce qui precedait (« Nv. » dessine sur le sprite du personnage, « x2 » colle a gauche de la plaque). Cellule sans tabSize : inchange."""
    if not tab_size or not isinstance(s, str) or '\t' not in s: return s
    return s.replace('\t', ' ' * max(0, int(round(tab_size))))


def auto_plate_available(code_auto, engine_label_text):
    """La sauvegarde automatique existe-t-elle ? Le moteur le dit par le code 0 du menu de depart (1 : data5.dat valide, 0 : absent ou illisible) et n'envoie l'etiquette de la cellule (4, 1) que dans le premier cas ;
    `code_auto` None (code pas encore recu) : l'etiquette tranche."""
    if code_auto is not None: return code_auto != 0
    return bool((engine_label_text or '').strip())


def read_borders(path):
    """frameData (TextAsset du jeu) : nombre de maillages, puis pour chacun : nb sommets, nb indices, sommets (x, y, z, u, v), indices."""
    import struct
    b = open(path, 'rb').read(); n = struct.unpack_from('<i', b, 0)[0]; p = 4; out = []
    for _ in range(n):
        nv, ni = struct.unpack_from('<ii', b, p); p += 8
        v = np.frombuffer(b, '<f4', nv * 5, p).reshape(nv, 5); p += 20 * nv
        t = np.frombuffer(b, '<i4', ni, p); p += 4 * ni
        out.append(dict(vtx=[[float(x[0]), float(x[2])] for x in v], uv=[[float(x[3]), float(x[4])] for x in v], tri=[int(i) for i in t]))
    return out


def three_lines(t1, t0):
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


def limit_lines(t, num=3, lh=28.0, margin=3.0):
    """Fenetre de message : le canevas montre exactement `num` lignes de `lh` pixels (plus une marge de 3 pixels, le defilement du moteur commence a -3) au lieu de 3,5 lignes : la mise en page d'origine
    laisse voir le haut de la ligne suivante sous la derniere ligne (canevas de 100,5 pour des lignes de 28 : type 0 ; combat : lignes de 34)."""
    import copy
    cv = t['canvas']; zmax = max(v[2] for v in cv['vtx']); zmin = min(v[2] for v in cv['vtx']); h = num * lh + margin
    if zmax - zmin <= h + 0.5: return t
    t = copy.deepcopy(t); cv = t['canvas']
    for v in cv['vtx']:
        if v[2] == zmin: v[2] = zmax - h
    for u, v in zip(cv['uv'], cv['vtx']):
        if v[2] == zmax - h: u[1] = h / 512.0
    return t


def full_text(t):
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


class PageLayout:
    """cache/ui_layout.json : {'header': {...}, 'types': {numero: {...}}} ; cadres : maillages des fenetres (frameData)"""
    def __init__(self, path, borders=None):
        with open(path, encoding='utf-8') as f: d = json.load(f)
        self.hdr = d['header']; self.types = d['types']; self.message = d.get('message')       # message : fenetre de dialogue (MenuMessage), absente des anciens fichiers
        if self.message:                                                 # combat (type 1) : 3 lignes comme le terrain ; le cadre d'origine (4 lignes) reste en type 4, pour les messages qui en ont quatre
            ts = self.message['types']; ts.append(ts[1]); ts[1] = three_lines(ts[1], ts[0])
            for i in (2, 3): ts[i] = limit_lines(full_text(ts[i]), 3, 34.0)
            ts[0] = limit_lines(ts[0], 3, 28.0)                          # messages d'action du combat : texte de la meme taille que dans les dialogues
        self.info = self.hdr['info']; self.colors = [tuple(c) for c in self.hdr['colors']]
        self.pushed = tuple(self.hdr['pushed'])
        self.borders = read_borders(borders) if borders and os.path.exists(borders) else []


# MenuPortItemTable.name_button_param (RVA 0xCF8E00-0xCF8F98, .cctor) : (nombre de rangees, ordonnee de depart, pas) de la liste Make_NameButton ; le moteur choisit la mise en page par le code 6 de la fenetre
# (`<Make_NameButton>b__0`, 0xD08BE8 : les rangees 0 a nombre - 1 sont activees et posees en `initial - step x rank`, les autres sont desactivees jusqu'a la 6e). L'exporteur ne peut pas jouer cette fonction (« List index »).
NAMES_PRESETS = ((4, 382.0, 67.0), (5, 382.0, 67.0), (5, 434.0, 67.0), (6, 434.0, 67.0), (5, 412.0, 67.0))
NAMES_START, NAMES_STEP = 382.0, 67.0         # mise en page exportee : rangee k a l'ordonnee 382 - 67 k (NAME_BUTTON_Y, NAME_BUTTON_DY)
CARD_COST_X_MAX = 214.0              # fiche d'un sort (type 7) : bord droit utile de la ligne de cout (cadre de droite : x 63 a 221, mesure sur les captures, moins la marge des plaques)
CARD_DESC_X_MAX = 148.0              # fiche d'un sort (type 7) : bord droit utile de la description (cadre du bas : x -226 a 155,5, jusqu'au bouton de retour, moins la marge des plaques) ; le cadre n'a que 2 lignes de haut
BATTLE_DESC_X_MAX = 56.0              # infos d'un objet en combat (type 38) : bord droit utile de la description (cellule de gauche : x -226 a 64,7, mesure sur une capture du moteur reel, moins la marge) ; la cellule n'a que 2 lignes de haut, la cellule « Attaque E 24 » est a sa droite
# Descriptions d'objets et de sorts : (type de fenetre, port, numero de chaine) -> bord droit utile (unites d'interface) de leur cadre, qui ne montre que 2 lignes. Le port est dans la cle : la fenetre du casino (type 46)
# a quatre autres cellules de texte au meme numero de chaine (les listes, port 0 a 3) qui ne sont pas des descriptions. Le texte francais du patch a des lignes de 38 caracteres, ou une seule ligne de 50
# (« Peut aussi etre utilisee comme objet au / combat. », « Au combat, ils peuvent inverser le cours du temps. ») : il sortait du cadre et recouvrait « Attaque E 74 » (type 38) ou le bouton du sac (type 10). Render._texte le recoupe a cette largeur puis, si
# 2 lignes ne suffisent pas, le comprime (Render._adjust_description).
DESCRIPTIONS = {(7, 0, 1): CARD_DESC_X_MAX, (10, 0, 4): CARD_DESC_X_MAX, (38, 2, 3): BATTLE_DESC_X_MAX,
                (46, 4, 3): CARD_DESC_X_MAX, (60, 4, 4): CARD_DESC_X_MAX, (61, 4, 4): CARD_DESC_X_MAX, (63, 0, 4): CARD_DESC_X_MAX, (70, 0, 3): CARD_DESC_X_MAX}      # 46, 60, 61, 63, 70 : barre du bas des boutiques et du casino (meme cadre que la fiche d'un sort ; Suppose : fenetres non ouvertes dans le moteur, #219)
BUTTON_COMPRESSION_TYPES = (48,)       # fenetres dont les etiquettes de bouton sont comprimees pour tenir dans leur plaque MEME avec la police d'origine : le poker du casino (type 48, SVC-03 : « Abandonner » sortait des 5 boutons sous les cartes et se chevauchait ; choix du joueur : police reduite)
COMPRESSION_MIN = 0.7                 # compression horizontale maximale d'une description qui ne tient pas en 2 lignes


def compress_label(original_font, fit_x, window_type):
    """Un texte plus large que sa plaque est-il comprime pour y tenir ? Toujours avec la police de repli ; avec la police d'origine (SE-GARRIR) seulement quand la fenetre pose une limite (`fit_x` : ligne de cout de la fiche d'un sort) ou
    pour les etiquettes de bouton des fenetres de BUTTON_COMPRESSION_TYPES (poker). Ailleurs un texte francais plus long que son bouton depasse comme sur le mobile (choix du joueur, audit UI-05)."""
    return (not original_font) or fit_x is not None or window_type in BUTTON_COMPRESSION_TYPES


def uv_icon(info, no, scroll_offset):
    """PartsInfo.SetUV : 4 sommets (HG, HD, BD, BG) de l'icone numero `no` dans la feuille."""
    n = no + info['startNo']; w = info['widthNum']
    col = int(math.fmod(n, w)); lig = int(n / w)          # division entiere du C (vers zero)
    u0 = col * info['uvsize']; v0 = -(info['startV'] + lig * info['uvsize']); u1 = u0 + info['uvsize']; v1 = v0 - info['uvsize']
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


SHEET_ALPHA = {}                           # feuille (0 = MenuTexture, 1 = Button...) -> opacite (hauteur x largeur, uint8) de la feuille du jeu, posee par Rendu : sert a mesurer le bord VISIBLE d'un cadre


def visible_edges(vtx, uv, tris, alpha, threshold=127):
    """(x0, x1, z0, z1) du dessin VISIBLE d'une maille de cadre, dans le repere local de la maille (unites d'interface), ou None.
    Un cadre est une grille de cases dont celles du bord ont une marge transparente dans la feuille, de taille differente d'un cadre a l'autre (le cadre des dialogues : 6 unites a droite, 4,5 en haut ; celui de Oui / Non : presque
    rien) : poser deux cadres bord a bord sur les bords de leurs mailles les decale de ces marges. Pour chaque case (maille, triangles `tris`), on cherche dans `alpha` les colonnes et les rangees dont l'opacite depasse `threshold`
    (la colonne de texture croit avec x, la rangee decroit quand z monte : v = -rangee / hauteur de la feuille)."""
    h, l = alpha.shape; x0 = z0 = 1e9; x1 = z1 = -1e9; views = set()
    for i in range(0, len(tris) - 2, 3):
        ids = tris[i:i + 3]; P = [vtx[j] for j in ids]; U = [uv[j] for j in ids]
        bx0, bx1 = min(p[0] for p in P), max(p[0] for p in P); bz0, bz1 = min(p[1] for p in P), max(p[1] for p in P)
        if bx1 - bx0 < 1e-6 or bz1 - bz0 < 1e-6: continue
        c0 = min(u[0] for u in U) * l; c1 = max(u[0] for u in U) * l; r0 = min(-u[1] for u in U) * h; r1 = max(-u[1] for u in U) * h
        if c1 - c0 < 1e-6 or r1 - r0 < 1e-6: continue
        lookup_key = (round(bx0, 3), round(bx1, 3), round(bz0, 3), round(bz1, 3), round(c0, 3), round(r0, 3))
        if lookup_key in views: continue
        views.add(lookup_key)
        ca, ra = int(math.floor(c0 + 1e-6)), int(math.floor(r0 + 1e-6))
        a = alpha[ra:int(math.ceil(r1 - 1e-6)), ca:int(math.ceil(c1 - 1e-6))] > threshold
        if not a.any(): continue
        cols = np.where(a.any(axis=0))[0]; ranks = np.where(a.any(axis=1))[0]
        fx0 = max((ca + cols[0] - c0) / (c1 - c0), 0.0); fx1 = min((ca + cols[-1] + 1 - c0) / (c1 - c0), 1.0)        # fractions de la case, depuis la gauche et depuis le haut
        fh = max((ra + ranks[0] - r0) / (r1 - r0), 0.0); fb = min((ra + ranks[-1] + 1 - r0) / (r1 - r0), 1.0)
        x0 = min(x0, bx0 + (bx1 - bx0) * fx0); x1 = max(x1, bx0 + (bx1 - bx0) * fx1); z1 = max(z1, bz1 - (bz1 - bz0) * fh); z0 = min(z0, bz1 - (bz1 - bz0) * fb)
    return (x0, x1, z0, z1) if x0 < 1e8 else None


class Window:
    """Une fenetre de menu ouverte (un port du moteur) : etat modifiable d'apres les messages du moteur."""
    def __init__(self, ml, typ):
        self.ml = ml; self.typ = typ; self.t = ml.types[str(typ)]
        self.N = {}
        for n in self.t['nodes']:
            m = n.get('mesh')
            self.N[n['id']] = dict(id=n['id'], par=n['par'], pos=list(n['pos']), act=n['act'], mats=[dict(x) for x in n.get('mats', [])],
                                   vtx=[list(v) for v in m['vtx']] if m else None, uv=[list(v) for v in m['uv']] if m else None, sub=m['sub'] if m else None,
                                   text=dict(n['text']) if n.get('text') is not None else None, buttonId=(n.get('parts') or {}).get('buttonId'), pad=(n.get('parts') or {}).get('gamepad') or 0, etat=0, tcol=0, tscale=1.0)
        self.parts = list(self.t['parts']); self.n_parts = len(self.parts)         # copie de la liste : l'eglise (type 66) y ajoute les parties de ses boutons
        name_str = self.t.get('name', '')                                              # types que le portage anime ou complete : le jeu les fait par du code que l'exporteur ne voit pas
        self.church = name_str.startswith('Make_ChurchRoot'); self.eg_ids = []; self.church_texts = {}      # eglise : elements ajoutes, textes recus avant la creation des boutons
        self.status = name_str.startswith('Make_BattleUpStatus'); self.shake = {}; self.t_cursor = None      # plaques des membres en combat : secousses en cours (membre -> etat), debut du clignotement de la fleche
        self.names = name_str.startswith('Make_MonsterName')                            # plaques de monstres : marques de groupe (decor du combat : elles ne comptent pas dans l'etendue de la fenetre)
        if self.names:
            for node in self._marks(): node['marque'] = True
        self.begin = name_str.startswith('Make_StartMenuSelect')                       # menu de depart : cadre choisi par le code 3
        if name_str.startswith('Make_YesNo'): self._push_yes_no()                  # Oui / Non : les deux plaques l'une sur l'autre (D-231)
        self.vals_code = {}; self.auto_grayed = False                              # derniere valeur de chaque code recu ; plaque « Sauvegarde automatique » grisee par la visionneuse (voir auto_plate)
        for pt in self.parts:
            node = self.N.get(pt['node'])
            for ib in pt['ib']:
                if ib['k'] == 'bar' and node and node['vtx'] and ib['vtx'] + 1 < len(node['vtx']):      # IBar.firstFunc : zero/largeur lus sur le quad
                    ib['zero'] = node['vtx'][ib['vtx']][0]; ib['width'] = node['vtx'][ib['vtx'] + 1][0] - node['vtx'][ib['vtx']][0]
                elif ib['k'] == 'frame' and ib.get('init') is not None: self._border(ib, ib['init'])
        self.params = {}
        for p in self.t['params']: self.params[(p['id'], p['no'])] = p
        self.codes = {}
        for c in self.t['codes']: self.codes.setdefault(c['id'], []).append(c)
        for lst in self.codes.values():                       # codes « fonction » (plaque de monstre...) : le code -1 = rien a montrer, etat de depart
            for e in lst:
                if e['kind'] == 'func':
                    for nid, dd in ((e.get('fx') or {}).get('-1') or {}).get('d', {}).items():
                        if int(nid) in self.N and dd.get('act') is False: self.N[int(nid)]['act'] = False
        self.is_name_list = name_str.startswith('Make_NameButton'); self.names_offset = {}       # liste de boutons nommes (type 8) : decalage deja applique a chaque rangee (voir _name_entries)
        if self.t.get('name', '').startswith('Make_NameButton'):       # liste de 6 boutons mais le moteur n'en pilote que 5 (codes 0 a 4) : le 6e (en bas, sous « Sauvegarde rapide ») reste cache tant qu'aucun code ne le montre
            for e in self.codes.get(5, []):
                for nid, dd in ((e.get('fx') or {}).get('0') or {}).get('d', {}).items():
                    if int(nid) in self.N and dd.get('act') is False: self.N[int(nid)]['act'] = False
        if self.t.get('name', '').startswith('Make_StartMenuSecond'):     # menu de depart : la case « Sauv. cloud » (bouton 8) n'existe plus pour le moteur (octet g_isAmazon) ; le portage y met son bouton « Sauvegardes » (export / import), libelle pose ici
            self.param_str(5, 0, tr('Sauvegardes'))
        if name_str.startswith('Make_Chapter('):               # titre de chapitre : l'exporteur voit le quad de MenuParts.CreateFromTexture(« Menu/map/hyodai1 », bFitWidth = true, haspect = 1) avec son maillage par defaut (carre de 450) et sans texture (creee par le code)
            for node in self.N.values():                  # CreateFromTexture ajuste la largeur (450) et deduit la hauteur de la texture (256 x 128 : 225) : bandeau dore a fond bleu, centre
                if node['vtx'] and node['mats'] and node['mats'][0].get('sheet') is None:
                    node['vtx'] = [[-225.0, 112.5], [225.0, 112.5], [225.0, -112.5], [-225.0, -112.5]]; node['mats'][0] = dict(node['mats'][0], sheet='hyodai1', color=[1.0, 1.0, 1.0, 1.0])
        self.vu = True; self.selected = None; self.selected_node = None; self.press_node = None; self.order = 0
        self.map_name = None; self.game_map = None            # fenetre de carte (type 25) : nom du plan, texture (posee par la visionneuse)
        self.symbols = []; self.t_blink = None; self.map_mode = 3      # carte du monde : lieux decouverts (x, y en pixels du plan de 256 x 192), debut du clignotement ; mode de filtrage du plan
        self.special = None                                                # petite carte du monde : lieu special (code 4), (x, y) en pixels du plan de 256 x 192, ou None

    # ---- application des messages
    def _ib(self, p):
        if 'parts' not in p or p['parts'] >= len(self.parts): return None, None
        pt = self.parts[p['parts']]
        return pt, (pt['ib'][p['base']] if p['base'] < len(pt['ib']) else None)

    def _border(self, ib, v):
        node = self.N.get(ib.get('go'))
        if node and 0 <= v < len(self.ml.borders):
            c = self.ml.borders[v]; node['vtx'] = [list(x) for x in c['vtx']]; node['uv'] = [list(x) for x in c['uv']]; node['sub'] = {'0': c['tri']}

    def _barre(self, ib, pt, v):
        node = self.N.get(pt['node'])
        if node and node['vtx']:
            o = ib['vtx']
            if v < 0: o -= 4; v = ~v
            if o + 2 < len(node['vtx']) and o >= 0:
                x = ib['zero'] + ib['width'] * v * 0.01
                node['vtx'][o + 1][0] = x; node['vtx'][o + 2][0] = x

    def _wrapped(self, p):
        w = (p.get('custom') or {}).get('wrap')
        if not w or w['parts'] >= len(self.parts): return None, None
        pt = self.parts[w['parts']]
        return pt, (pt['ib'][w['base']] if w['base'] < len(pt['ib']) else None)

    def param_int(self, i, no, v):
        p = self.params.get((i, no))
        if not p: return
        if 'custom' in p:
            cu = p['custom']; pt, ib = self._wrapped(p)
            if cu.get('cls', '').endswith('ICityMap'): return                                       # fenetre de carte (type 25) : le nom de la texture du plan (Menu/map) est pose par la visionneuse (map_name)
            if cu.get('cls', '').endswith('StatusIconChanger'): self._status_icon(i, v); return       # icones d'etat (mort, poison, sort scelle) et couleur du nom
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
            node = self.N.get(pt['node'])
            if node and node['uv']:
                info = self.ml.info[ib['partsNo']]; o = ib['vtx']
                for j, uv in enumerate(uv_icon(info, v, 0)):
                    if o + j < len(node['uv']): node['uv'][o + j] = list(uv)
        elif k == 'text':
            if ib.get('go') in self.N: self.N[ib['go']]['tcol'] = v
        elif k == 'bar': self._barre(ib, pt, v)
        elif k == 'button':
            node = self.N.get(pt['node'])
            if node: node['etat'] = v
        elif k == 'frame': self._border(ib, v)

    def _item_num(self, i, v):
        """ItemNumCTRL.Changer(v) (0xD08060) : compteur passif a deux chiffres d'une ligne de la liste d'objets (Sub_ItemButton : IBase 3 = dizaines, IBase 4 = unites, feuille 12, cases de 32 px).
        v < 2 : deux cases vides (icone 1) ; sinon dizaines = (v / 10) % 10 (icone 16 x chiffre, ou 1 si zero), unites = icone 16 x (v % 10) ; 100 et plus se replient modulo 100 (123 -> 23).
        Les deux chiffres sont les IBase 3 et 4 de la MenuParts de la ligne (celle de l'element (ligne, 0))."""
        p0 = self.params.get((i, 0))
        if not p0 or p0.get('parts') is None or p0['parts'] >= len(self.parts): return
        pt = self.parts[p0['parts']]; node = self.N.get(pt['node'])
        if node is None or not node['uv'] or len(pt['ib']) < 5: return
        if v < 2: dz, one = 1, 1
        else: d = (v // 10) % 10; dz = d * 16 if d else 1; one = (v % 10) * 16
        for ib, no in ((pt['ib'][3], dz), (pt['ib'][4], one)):
            if ib['k'] != 'icon': continue
            info = self.ml.info[ib['partsNo']]; o = ib['vtx']
            for j, uv in enumerate(uv_icon(info, no, 0)):
                if o + j < len(node['uv']): node['uv'][o + j] = list(uv)

    def param_str(self, i, no, s):
        if self.church: self.church_texts[(i, no)] = s
        p = self.params.get((i, no))
        if not p: return
        if 'custom' in p:
            cu = p['custom']; pt, ib = self._wrapped(p)
            if cu.get('cls', '').endswith('BattleBar') and ib and ib['k'] == 'bar':      # BattleBar.Change(string) = RedApply : barre « rouge » = valeur courante
                self._barre(ib, pt, ~cu.get('_v', 0))
            return
        pt, ib = self._ib(p)
        if not ib or ib['k'] != 'text': return
        node = self.N.get(ib.get('go'))
        if not node or node['text'] is None: return
        base = node.setdefault('base', dict(cs=node['text']['characterSize']))
        node['tscale'] = 1.0; node['text']['characterSize'] = base['cs']
        if ib.get('variant') == 1 and '^' in s:
            j = s.index('^')
            if j + 1 < len(s):
                c = ord(s[j + 1]) - 48
                if 0 <= c <= 5:
                    ui_scale, cs = TEXT_MARKS[c]
                    hiro = self.ml.hdr['lang']['hiro']
                    node['tscale'] = hiro if ui_scale == 1.0 and c == 0 else (min(hiro * 1.4, 1.0) if c == 5 else 1.0)
                    if isinstance(cs, float): node['text']['characterSize'] = cs
                    elif cs == 'base': node['text']['characterSize'] = ib.get('fsize', base['cs'])
                s = s[:j] + s[j + 2:]
        elif ib.get('variant') == 1 and ib.get('fsize'): node['text']['characterSize'] = ib['fsize']
        if (self.typ, i, no) in DESCRIPTIONS: node['wrap_x'] = DESCRIPTIONS[(self.typ, i, no)]; node['wrap_n'] = 2        # description d'un sort ou d'un objet : le cadre montre 2 lignes ; si le texte est plus large ou plus haut, il est recoupe a la largeur du cadre (Render._adjust_description)
        if self.typ == 7 and no == 2: node['fit_x'] = CARD_COST_X_MAX                # fiche d'un sort (Make_MagicInfo), ligne « Cout en PM  2/ 30 » (ancree a gauche, x 75) : elle doit tenir dans son cadre, voir Render._texte
        s = expand_tabs(s, node['text'].get('tabSize'))                              # voir tabuler : toutes les cellules a tabSize (types 8, 20, 31, 33, 34, 35, 39), plus seulement la liste des magies (#208, audit UI-03)
        node['text']['text'] = s; node['vu'] = True

    def code(self, i, c):
        self.vals_code[i] = c
        if self.church and i == 0: self._church(c)
        elif self.status: self._status(i, c)
        elif self.names and i == 4: self._reset_marks()
        elif self.begin and i == 3: self._start(c)
        elif getattr(self, 'is_name_list', False) and i == 6: self._name_entries(c); return      # (getattr : les tests construisent des Fenetre factices sans cet attribut)
        for e in self.codes.get(i, []):
            if e['kind'] == 'active':
                pt = self.parts[e['parts']]
                if pt['node'] in self.N: self.N[pt['node']]['act'] = (c != 0)
            elif e['kind'] == 'func':
                fx = (e.get('fx') or {}).get(str(c))
                if not fx: self._mask_code(e, c); continue
                for nid, dd in fx['d'].items():
                    node = self.N.get(int(nid))
                    if not node: continue
                    if 'pos' in dd: node['pos'] = list(dd['pos'])
                    if 'act' in dd: node['act'] = bool(dd['act'])
                cache = {int(n) for v in e['fx'].values() for n, dd in v['d'].items() if dd.get('act') is False}
                for nid in cache:                   # un element que d'autres codes masquent est visible pour celui-ci s'il ne le masque pas
                    if str(nid) not in fx['d'] and nid in self.N: self.N[nid]['act'] = True
                for t in fx.get('tc', []):          # MenuParts.SetTextColor(code) : couleur des textes marques du masque
                    pt = self.parts[t['parts']] if t.get('parts') is not None else None
                    if pt:
                        for j, ib in enumerate(pt['ib']):
                            if (t['mask'] >> j) & 1 and ib['k'] == 'text' and ib.get('go') in self.N: self.N[ib['go']]['tcol'] = t['color']

    def _name_entries(self, c):
        """Make_NameButton, code 6 (`<Make_NameButton>b__0`) : mise en page de la liste. Le preset `c` (NAMES_PRESETS) donne le nombre de rangees visibles et l'ordonnee de la premiere : les rangees suivantes (jusqu'a la 6e) sont desactivees, donc ni
        dessinees ni cliquables (la 5e rangee, vide, restait visible et menait, au toucher, a une magie inexistante : <ERR ...> a l'ecran). Les codes de rangee (0 cache, 1 / 2 visible) arrivent apres et priment."""
        if not isinstance(c, int) or not 0 <= c < len(NAMES_PRESETS) or len(self.parts) < 7: return
        num, initial, step = NAMES_PRESETS[c]
        for k in range(6):
            nid = self.parts[1 + k]['node']; root = self.N.get(nid)
            if root is None: continue
            root['act'] = k < num and self.vals_code.get(k) != 0        # (rejeu d'une fenetre : le code de la rangee peut etre deja connu)
            dz = (initial - step * k) - (NAMES_START - NAMES_STEP * k)                   # decalage voulu de la rangee k (le jeu pose la plaque, ses textes la suivent)
            d = dz - self.names_offset.get(k, 0.0)
            if abs(d) > 1e-6:
                for node in self.N.values():
                    x = node; lineage = False
                    while x is not None:
                        if x['id'] == nid: lineage = True; break
                        x = self.N.get(x['par'])
                    if lineage: node['pos'][2] += d
                self.names_offset[k] = dz

    def _mask_code(self, e, c):
        """Fonction de code dont l'argument est un MASQUE DE BITS sur des elements actifs / inactifs (Make_Casino_Poker b__1 : bit n = zone tactile de numero n, cartes 0 a 4 et « Donner » 5 ; le moteur envoie 63 pour toutes).
        L'exporteur de mise en page n'a essaye que les valeurs 0 a 5 : le tableau `fx` ignore les autres. Si le tableau est bien de cette forme (pour CHAQUE valeur connue, les elements inactifs sont exactement ceux dont le bit
        de leur numero de bouton est a 0, parmi ceux que la valeur 0 desactive), on applique la meme regle a la valeur recue : l'element de numero de bouton n est actif quand le bit n est a 1. Sinon rien (comme avant)."""
        fxs = e.get('fx') or {}
        ok = e.get('_masque')
        if ok is None:
            ok = e['_masque'] = False
            try:
                zero = {int(n) for n, dd in (fxs.get('0') or {}).get('d', {}).items() if dd.get('act') is False}
                bid = {n: self.N[n]['buttonId'] for n in zero if n in self.N and self.N[n]['buttonId'] is not None and self.N[n]['buttonId'] >= 0}
                if zero and len(bid) == len(zero) and len(set(bid.values())) == len(bid):
                    ok = True
                    for k, v in fxs.items():
                        if k.lstrip('-').isdigit() and int(k) >= 0:
                            off = {int(n) for n, dd in (v.get('d') or {}).items() if dd.get('act') is False}
                            if off != {n for n in zero if not (int(k) >> bid[n]) & 1}: ok = False; break
                    e['_masque'] = ok; e['_masque_ids'] = bid if ok else None
            except Exception: ok = e['_masque'] = False
        if not ok or not isinstance(c, int) or c < 0: return
        for n, b in e['_masque_ids'].items():
            if n in self.N: self.N[n]['act'] = bool((c >> b) & 1)

    # ---- eglise (type 66, Make_ChurchRoot)
    # Le jeu fait les boutons dans le code de la fenetre (Sub_ShopButton) : l'exporteur de mise en page n'en voit que le titre et le bouton de sortie (« Rien »). On les refait ici d'apres le code recu du moteur
    # (0 : cinq boutons, sinon quatre) : (x, z depuis le bas de l'ecran, largeur sans les bordures) ; maillage a neuf decoupes de la plaque de sortie, bouton n = numero n, manette 16 (valider).
    CHURCH = {True: ((-111.5, 170.75, 177.1), (111.5, 170.75, 177.1), (-145.0, 106.25, 110.0), (0.0, 106.25, 110.0), (145.0, 106.25, 110.0)),
              False: ((0.0, 170.75, 177.1), (-145.0, 106.25, 110.0), (0.0, 106.25, 110.0), (145.0, 106.25, 110.0))}

    def _church(self, c):
        for n in self.eg_ids: self.N.pop(n, None)
        self.eg_ids = []; del self.parts[self.n_parts:]
        tpl = next((n for n in self.N.values() if n['vtx'] and n['mats'] and n['mats'][0].get('part') == 7 and n['buttonId'] is not None), None)      # plaque de bouton existante : la sortie (« Rien », manette 32)
        label = next((n for n in self.N.values() if tpl and n['par'] == tpl['id'] and n['text'] is not None), None)
        pt0 = next((pt for pt in self.parts if tpl and pt['node'] == tpl['id']), None)
        if tpl is None or label is None or pt0 is None: return
        ax = sorted({abs(v[0]) for v in tpl['vtx']})
        if len(ax) < 2: return
        inside, outside = ax[-2], ax[-1]; nid = max(self.N) + 1
        for no, (x, z, wid) in enumerate(self.CHURCH[c == 0]):
            vtx = [[math.copysign(wid / 2 + (outside - inside) if abs(abs(v[0]) - outside) < 1e-3 else wid / 2, v[0]), v[1]] for v in tpl['vtx']]
            bid, tid = nid, nid + 1; nid += 2; z -= 400.0
            self.N[bid] = dict(id=bid, par=tpl['par'], pos=[x, tpl['pos'][1], z], act=True, mats=[dict(m) for m in tpl['mats']], vtx=vtx, uv=[list(u) for u in tpl['uv']], sub=tpl['sub'], text=None, buttonId=no, pad=0x10, etat=0, tcol=0, tscale=1.0)
            self.N[tid] = dict(id=tid, par=bid, pos=[x + label['pos'][0] - tpl['pos'][0], label['pos'][1], z + label['pos'][2] - tpl['pos'][2]], act=True, mats=[dict(m) for m in label['mats']], vtx=None, uv=None, sub=None, text=dict(label['text']), buttonId=None, pad=0, etat=0, tcol=0, tscale=1.0)
            self.eg_ids += [bid, tid]
            self.parts.append(dict(node=bid, ib=[dict(ib, go=tid) if ib['k'] == 'text' else dict(ib) for ib in pt0['ib']]))
            tb = next((j for j, ib in enumerate(self.parts[-1]['ib']) if ib['k'] == 'text'), None)
            if tb is None: continue
            self.params[(no, 0)] = dict(id=no, no=0, parts=len(self.parts) - 1, base=tb)         # remplace les liaisons exportees (parties absentes de la mise en page)
            if (no, 0) in self.church_texts: self.param_str(no, 0, self.church_texts[(no, 0)])

    # ---- combat : plaques des membres (type 29, Make_BattleUpStatus)
    SHAKE = ((-6, 6), (6, -6), (6, -6), (-6, 6), (6, 6), (-6, -6), (-6, -6), (6, 6))         # MenuMessage.s_shakeTable : decalage de chaque image, de la derniere (7) a la premiere (0) ; somme nulle
    BLINK = 0.7                                                                                # BattleUpCursor.c_waitTime : secondes entre les deux teintes de la fleche

    def _icon(self, pt, ib, no):
        """IIcon.Change(no) : les quatre UV de l'icone numero `no` de la feuille de l'element."""
        node = self.N.get(pt['node'])
        if node and node['uv']:
            for j, uv in enumerate(uv_icon(self.ml.info[ib['partsNo']], no, 0)):
                if ib['vtx'] + j < len(node['uv']): node['uv'][ib['vtx'] + j] = list(uv)

    def _member_root(self, i):
        """Noeud de la plaque du membre i (celui que le code -1 cache), ou None."""
        for e in self.codes.get(i, []):
            if e['kind'] == 'func' and 'Sub_BattleUpStatus' in (e.get('method') or ''):
                k = next(iter((((e.get('fx') or {}).get('-1') or {}).get('d') or {})), None)
                if k is not None and int(k) in self.N: return int(k)
        return None

    def _status(self, i, c):
        """Ids 0 a 3 = plaques : le code 8 lance ShakeFrame (m_shake = 8), le code -1 cache la plaque. Id 5 = fleche du membre qui agit : un code >= 0 l'affiche (SetActive), la deplace et BattleUpCursor.ForceUpdate la remet sur l'icone 2."""
        if i == 5:
            if c >= 0: self.t_cursor = time.monotonic(); self._cursor_icon(2, True)
            return
        rid = self._member_root(i)
        if rid is None: return
        if c == 8:
            sec = self.shake.get(i)
            if sec is None:                                   # la plaque entiere se deplace : sa racine, ses textes, sa barre, son visage
                every = {rid}; added = True
                while added:
                    added = False
                    for node in self.N.values():
                        if node['par'] in every and node['id'] not in every: every.add(node['id']); added = True
                sec = self.shake[i] = dict(base={n: list(self.N[n]['pos']) for n in every}, dx=0.0, dz=0.0)
            sec['m'] = 8
        elif c < 0: self._end_shake(i, False)

    def _end_shake(self, i, red):
        """Fin de ShakeFrame : la plaque revient a sa place ; rouge : m_shakeEndCallback = BattleBar.RedApply (la barre rouge rejoint la valeur courante)."""
        sec = self.shake.pop(i, None)
        if sec is None: return
        for n, b in sec['base'].items():
            if n in self.N: self.N[n]['pos'][0] = b[0]; self.N[n]['pos'][2] = b[2]
        if red: self.param_str(i, 5, '')

    def _cursor_icon(self, no, reveal=False):
        """Icone de la fleche de cible (feuille 10) ; montrer : SetActive(true) du code >= 0 (l'exporteur ne le voit pas : le code ne fait que la deplacer, la fleche restait cachee)."""
        for pt in self.parts:
            for ib in pt['ib']:
                if ib['k'] == 'icon' and ib.get('partsNo') == 10:
                    self._icon(pt, ib, no); self.n_cursor = no
                    if reveal and pt['node'] in self.N: self.N[pt['node']]['act'] = True
                    return

    def tick(self, t=None):
        """Une image du jeu (30 Hz) : secousse des plaques (ShakeFrame.Update : un decalage de la table par image, puis le rouge de la barre) ; la fleche de cible clignote en temps reel (BattleUpCursor.Update)."""
        for i in list(self.shake):
            sec = self.shake[i]; sec['m'] -= 1
            dx, dz = self.SHAKE[sec['m']]; sec['dx'] += dx; sec['dz'] += dz
            for n, b in sec['base'].items():
                if n in self.N: self.N[n]['pos'][0] = b[0] + sec['dx']; self.N[n]['pos'][2] = b[2] + sec['dz']
            if sec['m'] == 0: self._end_shake(i, True)
        if self.t_cursor is not None:
            no = 2 + int(((time.monotonic() if t is None else t) - self.t_cursor) / self.BLINK) % 2
            if no != getattr(self, 'n_cursor', 2): self._cursor_icon(no)

    # ---- icones d'etat (MenuPortItemTable.StatusIconChanger)
    def _status_icon(self, i, v):
        """StatusIconChanger : v = icone | (couleur << 16). La premiere icone (feuille 13) prend `v & 3` (0 rien, 1 croix = mort, 2 tete de mort = poison), la seconde l'oeil (3) si le bit 2 est leve (sort scelle) ;
        la couleur (palette de l'en-tete : blanc, jaune = a l'article de la mort, rouge = mort) teinte la matiere de cette feuille. i = rang de la partie qui porte deux icones de la feuille 13."""
        pts = [pt for pt in self.parts if sum(1 for ib in pt['ib'] if ib['k'] == 'icon' and ib.get('partsNo') == 13) == 2]
        if not 0 <= i < len(pts): return
        pt = pts[i]; i1, i2 = [ib for ib in pt['ib'] if ib['k'] == 'icon' and ib.get('partsNo') == 13]
        self._icon(pt, i1, v & 3); self._icon(pt, i2, ((v >> 2) & 1) * 3)
        node = self.N.get(pt['node']); cs = self.ml.colors; c = (v >> 16) & 0xffff
        if node and c < len(cs):
            for m in node['mats']:
                if m.get('part') == 13: m['color'] = list(cs[c])

    # ---- combat : marques de groupe sous les monstres (MonsterMarkList, type 31)
    def _marks(self):
        """Les 12 marques du type 31 : parties d'une seule icone de la feuille 6 (Button), dans l'ordre des parties."""
        return [self.N[pt['node']] for pt in self.parts if len(pt['ib']) == 1 and pt['ib'][0]['k'] == 'icon' and pt['ib'][0].get('partsNo') == 6 and pt['node'] in self.N]

    def _reset_marks(self):
        """MonsterMarkList.Reset (code 4) : toutes les marques sont cachees."""
        for node in self._marks(): node['act'] = False

    # ---- menu de depart (type 54, Make_StartMenuSelect)
    def _start(self, c):
        """Code 3 : IFrame.Change(0xDB + code) choisit le cadre (219 : 316 de haut, 220 : 262, 221 : 260) ; code 2 : un seul bouton, plus bas, les deux autres caches."""
        if not 0 <= c <= 2: return
        border_part = next((ib for pt in self.parts for ib in pt['ib'] if ib['k'] == 'frame'), None)
        if border_part is not None: self._border(border_part, 0xDB + c); self._tab_title(border_part, c)
        bt = sorted((n for n in self.N.values() if n['buttonId'] is not None and n['buttonId'] >= 0 and n['pad'] == 0x10 and n['mats'] and n['mats'][0].get('part') == 7), key=lambda n: n['buttonId'])
        if not bt: return
        for node in self.N.values():
            if node['par'] is not None and '_z0' not in node: node['_z0'] = node['pos'][2]
        dz = (-266.25 - bt[0]['_z0']) if c == 2 else 0.0                     # le premier bouton (et ses textes) descend a 135,75 du bas de l'ecran
        for node in self.N.values():
            if node['id'] == bt[0]['id'] or node['par'] == bt[0]['id']: node['pos'][2] = node['_z0'] + dz
        for node in bt[1:]: node['act'] = (c != 2)

    def _tab_title(self, border_part, c):
        """Titre du type 54 : le texte est pose pour le cadre 219 (onglet de 241,5 de large, 316 de haut) ; les cadres 220 (sans onglet) et 221 (onglet de 301,5, 260 de haut) changent la hauteur
        et la largeur de l'onglet : le titre le suit (en bas : la hauteur perdue ; au centre : la moitie de la largeur gagnee), sinon il flotte au-dessus de l'onglet (liste « Reprendre » / « Auto »).
        Choix du portage : le code d'origine (0xD0A604) ne deplace que les boutons, mais le texte envoye au code 2 est bien le titre de l'onglet."""
        tx = next((n for n in self.N.values() if n['par'] == border_part.get('go') and n['text'] is not None), None)
        if tx is None: return
        if '_x0' not in tx: tx['_x0'] = tx['pos'][0]; tx['_z0'] = tx['pos'][2]
        def tab(v):
            if not 0 <= v < len(self.ml.borders): return None
            vt = self.ml.borders[v]['vtx']; h = max(p[1] for p in vt); xs = [p[0] for p in vt if p[1] >= h - 12.5]
            return (h, max(xs)) if max(xs) < 400.0 else None             # pas d'onglet : toute la largeur
        o0, oc = tab(0xDB), tab(0xDB + c)
        if o0 is None or oc is None: return
        tx['pos'][0] = tx['_x0'] + (oc[1] - o0[1]) / 2.0; tx['pos'][2] = tx['_z0'] + (oc[0] - o0[0])

    def selection(self, button):
        """Bouton choisi (curseur) : les elements de ce numero passent a l'etat « appuye »."""
        self.selected = button

    # ---- plaques de noms de monstres (MenuPortItemTable.MonsterNamePlate, type 31)
    def _plate_nodes(self, i):
        for e in self.codes.get(i, []):
            fx = e.get('fx') or {}
            border = next(iter(((fx.get('-1') or {}).get('d') or {}).keys()), None)
            text = next(iter(((fx.get('1') or {}).get('d') or {}).keys()), None)
            if border is not None and text is not None: return int(border), int(text)
        return None, None

    def plate(self, i, name_str, prm, code):
        """ReceiveParameters(code >= 1) : nom du monstre, fenetre ajustee a une ou deux lignes (VariableWindow 142 x 18 ou 36), masque des monstres du groupe."""
        border, text = self._plate_nodes(i)
        if border is None or border not in self.N or text not in self.N: return
        pl = getattr(self, 'pl', None)
        if pl is None: pl = self.pl = {}
        nc = self.N[border]
        if 'base_vtx' not in nc: nc['base_vtx'] = [list(v) for v in nc['vtx']]; pl_off = [a - b for a, b in zip(self.N[text]['pos'], nc['pos'])]; nc['off_texte'] = pl_off
        if name_str[:1] == '^' and len(name_str) >= 2: name_str = name_str[2:]                    # marque de couleur : retiree par la plaque
        two = '\n' in name_str
        nc['vtx'] = [[x, z if two else (z - 9.0 if z > 0 else z + 9.0)] for x, z in nc['base_vtx']]       # fenetre de 36 -> 18 de haut : lignes du haut/bas rapprochees du centre
        nt = self.N[text]; nt['text']['text'] = expand_tabs(name_str, nt['text'].get('tabSize')); nt['vu'] = True; nt['tcol'] = 0        # « nom \n \t×N » : la tabulation (tabSize 25) repousse « ×N » vers le bord droit de la plaque
        mask = (prm[4] & 0xffff if len(prm) > 4 else 0) | ((prm[5] & 0xffff) << 16 if len(prm) > 5 else 0)
        pl[i] = dict(cadre=border, texte=text, masque=mask, code=code, two=two)
        nc['act'] = True

    def arrange(self, n, proj):
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
        self._reset_marks(); marks = self._marks(); k = 0
        for i in lst:                                                       # MonsterMarkList.SetMark : choix de cible (code 2) = une marque de la couleur de la plaque sous chaque monstre du groupe, a x du monstre, z = -64
            if pl[i]['code'] != 2 or not proj: continue
            for x in (proj(pl[i]['masque'], True) or []):
                if k >= len(marks): break
                node = marks[k]; k += 1; node['pos'] = [x, 0.0, -64.0]; node['act'] = True
                for j, uv in enumerate(uv_icon(self.ml.info[6], 5 + i, 0)): node['uv'][j] = list(uv)

    def buttons(self, ident=False):
        """Zones tactiles (MenuParts d'un bouton : numero, touche de manette envoyee au moteur au relachement) : [(numero, manette, x0, z0, x1, z1, profondeur)] en unites d'interface ; ident : l'identifiant de l'element s'ajoute en fin de tuple."""
        out = []
        for node in self.N.values():
            if not node['pad'] or node['buttonId'] is None or not node['vtx'] or not is_state_active(node['etat']) or not self.visible(node['id']): continue
            xs = [node['pos'][0] + v[0] for v in node['vtx']]; zs = [node['pos'][2] + v[1] for v in node['vtx']]
            out.append((node['buttonId'], node['pad'], min(xs), min(zs), max(xs), max(zs), node['pos'][1]) + ((node['id'],) if ident else ()))
        return out

    def bottom(self):
        """Ordonnee (unites d'interface) du bord bas des parties visibles de la fenetre."""
        zs = [node['pos'][2] + v[1] for node in self.N.values() if node['vtx'] and node['mats'] and not node.get('marque') and self.visible(node['id']) for v in node['vtx']]
        return min(zs) if zs else 0.0

    def extent(self):
        """(bas, haut) en unites d'interface des parties visibles de la fenetre, ou None si rien n'est dessine."""
        zs = [node['pos'][2] + v[1] for node in self.N.values() if node['vtx'] and node['mats'] and not node.get('marque') and self.visible(node['id']) for v in node['vtx']]
        return (min(zs), max(zs)) if zs else None

    def visible_extent(self):
        """(x0, x1, z0, z1) du dessin VISIBLE des parties montrees de la fenetre, en unites d'interface (voir `visible_edges` : les marges transparentes des cadres ne comptent pas) ; les bords des mailles quand la feuille n'est pas connue. None si rien n'est dessine."""
        r = None
        for node in self.N.values():
            if not (node['vtx'] and node['mats'] and not node.get('marque') and self.visible(node['id'])): continue
            lookup_key = (id(node['vtx']), len(node['vtx']), node['mats'][0].get('sheet'))
            if node.get('_vis_cle') != lookup_key:
                al = SHEET_ALPHA.get(node['mats'][0].get('sheet')); sub = (node.get('sub') or {}).get('0')
                node['_vis_cle'] = lookup_key; node['_vis'] = (visible_edges(node['vtx'], node['uv'], sub, al) if (al is not None and sub and node['uv']) else None) or (min(v[0] for v in node['vtx']), max(v[0] for v in node['vtx']), min(v[1] for v in node['vtx']), max(v[1] for v in node['vtx']))
            b = node['_vis']; b = (node['pos'][0] + b[0], node['pos'][0] + b[1], node['pos'][2] + b[2], node['pos'][2] + b[3])
            r = b if r is None else (min(r[0], b[0]), max(r[1], b[1]), min(r[2], b[2]), max(r[3], b[3]))
        return r

    def rects(self):
        """Rectangles (x0, z0, x1, z1) des elements dessines (visibles, avec maillage) de la fenetre : les cadres et les plaques."""
        out = []
        for node in self.N.values():
            if node['vtx'] and node['mats'] and not node.get('marque') and self.visible(node['id']):
                xs = [node['pos'][0] + v[0] for v in node['vtx']]; zs = [node['pos'][2] + v[1] for v in node['vtx']]
                out.append((min(xs), min(zs), max(xs), max(zs)))
        return out

    def center_menu(self):
        """Menu de depart (type 53) : le jeu colle ses boutons au bord bas de l'ecran portrait ; la visionneuse les centre en hauteur (le groupe entier : « Sauvegarde automatique », les quatre choix, Licence, Sauvegardes, retour)
        dans un cadre noir. Le decalage se calcule sur la mise en page complete (visible ou non) pour que le groupe ne bouge pas quand un bouton apparait ou disparait. -> decalage applique (unites)."""
        for node in self.N.values():
            if '_zc' not in node: node['_zc'] = node['pos'][2]
        zs = [node['_zc'] + v[1] for node in self.N.values() if node['vtx'] and node['mats'] for v in node['vtx']]
        if not zs: return 0.0
        dz = -(min(zs) + max(zs)) / 2.0
        for node in self.N.values(): node['pos'][2] = node['_zc'] + dz
        return dz

    def hide_empty_plate(self, button):
        """Plaque de bouton dont le moteur n'a envoye aucune etiquette (case inexistante : « Sauvegarde automatique » sans fichier data5.dat lisible) : cachee, avec ses textes ; remontree des qu'une etiquette arrive.
        La mise en page ne change pas (le cadre du menu de depart garde la place) ; une plaque cachee n'est ni survolee ni choisie (`buttons` ignore les elements invisibles)."""
        for pl in self.N.values():
            if pl['buttonId'] != button or not pl['mats'] or pl['mats'][0].get('part') != 7 or not pl['vtx']: continue
            tx = [n for n in self.N.values() if n['par'] == pl['id'] and n['text'] is not None]
            empty = bool(tx) and not any((n['text'].get('text') or '').strip() for n in tx)
            if empty: pl['act'] = False; pl['_vide'] = True
            elif pl.pop('_vide', False): pl['act'] = True

    def gray_texts(self):
        """Texte gris (TEXT_COLOR_GRAY) sur les plaques de bouton grisees (etat 3), blanc de nouveau quand elles ne le sont plus. Le shader gris du jeu ne fait que retirer la couleur : sur la plaque grise du menu de depart
        la difference ne se voit presque pas ; le texte gris montre qu'elle est inactive (choix de la visionneuse : le jeu, lui, ne change la couleur du texte que pour les boutons qui l'ont demande)."""
        for pl in self.N.values():
            if pl['buttonId'] is None or not pl['mats'] or pl['mats'][0].get('part') != 7: continue
            for t in self.N.values():
                if t['par'] != pl['id'] or t['text'] is None: continue
                if pl['etat'] == STATE_GRAYED: t['tcol'] = TEXT_GRAY; t['_gris'] = True
                elif t.pop('_gris', False): t['tcol'] = 0

    def auto_plate(self, button=AUTO_BUTTON, label_text=AUTO_CAPTION):
        """Menu de depart : plaque « Sauvegarde automatique » (voir _auto_plate) puis texte gris des plaques grisees."""
        self._auto_plate(button, label_text); self.gray_texts()

    def _auto_plate(self, button=AUTO_BUTTON, label_text=AUTO_CAPTION):
        """Menu de depart (type 53) : la plaque « Sauvegarde automatique » reste TOUJOURS visible, avec son etiquette ; sans sauvegarde auto elle est grisee (etat 3 : shader gris) donc inactive (`is_state_active` : ni survol, ni clic,
        ni validation au clavier ; le moteur, qui n'a pas de cellule 4 dans ce cas, ne recoit rien). Le jeu d'origine, lui, CACHE cette plaque (code 0 = 0 : cadre 215 / 216 puis SetActive(false)) ; la demande de l'utilisateur
        (grisee, jamais disparue) l'emporte. Avec DQ_AUTO_CACHEE : comportement d'origine. Idempotent (appelee a chaque image)."""
        pl = next((n for n in self.N.values() if n['buttonId'] == button and n['mats'] and n['mats'][0].get('part') == 7 and n['vtx']), None)
        if pl is None: return
        tx = [n for n in self.N.values() if n['par'] == pl['id'] and n['text'] is not None]
        tag_label = ' '.join((n['text'].get('text') or '').strip() for n in tx).strip()
        if self.auto_grayed and tag_label == label_text: tag_label = ''                  # notre propre etiquette de remplacement n'est pas celle du moteur (compte seulement tant que le code 0 manque)
        if auto_plate_available(self.vals_code.get(0), tag_label):
            if self.auto_grayed: self.auto_grayed = False; self.param_int(button, 0, STATE_NORMAL)         # la sauvegarde auto est apparue : plaque normale (le moteur donne l'etiquette)
            pl['act'] = True; pl.pop('_vide', None); return
        if os.environ.get('DQ_AUTO_CACHEE'): pl['act'] = False; pl['_vide'] = True; return           # (comparaison) comme le jeu d'origine : plaque cachee
        pl['act'] = True; pl.pop('_vide', None)
        if not self.auto_grayed or not tag_label: self.param_str(button, 1, label_text)
        self.auto_grayed = True; self.param_int(button, 0, STATE_GRAYED)

    def menu_border(self, margin=22.0, visible_ones=False):
        """Rectangle (x0, z0, x1, z1) de toute la mise en page (plaques, boutons), agrandi de `margin` : le cadre noir du menu de depart ; `visible_ones` : seulement les elements montres (listes de journaux : le cadre change de hauteur)."""
        node_list = [node for node in self.N.values() if node['vtx'] and node['mats'] and (not visible_ones or self.visible(node['id']))]
        xs = [node['pos'][0] + v[0] for node in node_list for v in node['vtx']]
        zs = [node['pos'][2] + v[1] for node in node_list for v in node['vtx']]
        return (min(xs) - margin, min(zs) - margin, max(xs) + margin, max(zs) + margin) if xs else None

    def center_visible(self):
        """(x, z) du centre de ce que la fenetre montre (cadre, onglet, plaques, bouton de retour), en unites d'interface ; None si rien. Les fenetres d'avant-partie (liste des journaux, choix du sexe) sont posees sur le bord bas-droit
        de l'ecran portrait : la visionneuse les centre (par le repere de dessin, sans toucher aux positions)."""
        r = self.menu_border(0.0, True)
        return ((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0) if r else None

    def extent_x(self):
        """(gauche, droite) en unites d'interface de toutes les parties de la fenetre (visibles ou non : la mise en page ne change pas), ou None : limites dans lesquelles un texte doit tenir. Mis en cache."""
        c = getattr(self, '_ex_cache', None)
        if c is None:
            xs = [node['pos'][0] + v[0] for node in self.N.values() if node['vtx'] and node['mats'] for v in node['vtx']]
            c = self._ex_cache = ((min(xs), max(xs)) if xs else None,)
        return c[0]

    YES_NO_SPACING = 1.0                       # espace entre les deux plaques empilees (celui qui separait les deux plaques cote a cote : de -0,5 a +0,5)

    def _push_yes_no(self):
        """Oui / Non (Make_YesNo, type 1) : sur mobile les deux plaques du cadre sont cote a cote (« Oui » a gauche, « Non » a droite, 134 x 48 unites chacune, une unite entre les deux) ; ici elles sont l'une sur l'autre,
        « Oui » au-dessus de « Non », comme sur DS (demande de Sylfried du 04/11/2026 : la pile est posee sur le coin haut droit de la boite de dialogue, voir `Game._ui_yesno`). La pile garde la colonne de la plaque de gauche
        (x de -134,5 a -0,5) ; les mailles (cadre, plaque, texte) sont deplacees d'un bloc, rien d'autre ne change : le curseur du moteur range deja Oui / Non en une colonne (haut = Oui, bas = Non), les zones tactiles
        et la selection suivent les noeuds deplaces. Sans deux plaques numerotees (autre mise en page), rien n'est change."""
        plates = sorted((n for n in self.N.values() if n['buttonId'] is not None and n['mats'] and n['mats'][0].get('part') == 7 and n['vtx']), key=lambda n: n['pos'][0])
        if len(plates) != 2 or plates[0]['par'] != plates[1]['par']: return
        border = self.N.get(plates[0]['par'])                                             # le cadre (deux panneaux) est le parent commun des deux plaques
        if border is None or not border['vtx'] or len(border['vtx']) % 4: return
        g, d = plates; dx = g['pos'][0] - d['pos'][0]                                    # decalage horizontal : la plaque de droite passe sur la colonne de gauche
        middle = (g['pos'][0] + d['pos'][0]) / 2.0 - border['pos'][0]                      # frontiere entre les deux panneaux du cadre (repere local du cadre)
        quads = [range(i, i + 4) for i in range(0, len(border['vtx']), 4)]
        right = [q for q in quads if sum(border['vtx'][i][0] for i in q) / 4.0 > middle]; left = [q for q in quads if q not in right]
        if not right or not left: return
        zs = [border['vtx'][i][1] for q in left for i in q]; dz = -(max(zs) - min(zs) + self.YES_NO_SPACING)       # la hauteur d'un panneau + l'ecart
        for q in right:
            for i in q: border['vtx'][i][0] += dx; border['vtx'][i][1] += dz
        tracked = {d['id']}; changed = True                                                # la plaque de droite et tout ce qui en descend (son texte)
        while changed:
            changed = False
            for n in self.N.values():
                if n['id'] not in tracked and n['par'] in tracked: tracked.add(n['id']); changed = True
        for nid in tracked: n = self.N[nid]; n['pos'][0] += dx; n['pos'][2] += dz

    def visible(self, nid):
        while nid is not None:
            node = self.N.get(nid)
            if node is None: return True
            if not node['act']: return False
            nid = node['par']
        return True


BORDER_WITH_NAME = 191                          # frameData du cadre de dialogue AVEC onglet de nom (192 = sans onglet : celui du type 0 de ui_layout.json)
WHO_POS = (-104.5, 4.0, -104.0)               # MenuMessage.m_who : position locale du TextMesh du nom ; la hauteur s'y ajoute BIAS_FONT_Y (= lang['dy'], ajoute par Render._texte)
WHO_SIZE = 10.0                             # characterSize du TextMesh du nom (celui des dialogues vaut 10,4975)


class MessageWindow:
    """Fenetre de message du jeu (MenuMessage) : cadre (frameData) + canevas de texte dessine par le moteur + curseur de fin de page.
    Le canevas est une texture 512 x 512 qui boucle ; le defilement `[3, y]` decale l'origine verticale de ses UV de (y & 0x1ff) / 512."""
    def __init__(self, ml):
        self.ml = ml; self.d = ml.message; self.vu = True; self.selected = None; self.selected_node = None; self.order = 0
        self.type = -1; self.y = 0; self.feed = False; self.N = {}; self.who = ''; self.with_name = False; self._base = None
        self.typ = -1; self.t = 0                                    # (pour Render._texte, qui lit ces deux champs des fenetres de menu : numero de type, image de la mise en page)
        self.select_language(0, 0, False)

    @staticmethod
    def _node(nid, pos, vtx, uv, tris, mat):
        return dict(id=nid, par=None, pos=pos, act=True, mats=[mat], vtx=vtx, uv=uv, sub={'0': tris}, text=None, buttonId=None, etat=0, tcol=0, tscale=1.0)

    def select_language(self, typ, y, feed, who=''):
        """typ = type de fenetre (0 terrain, 1-3 combat), y = defilement du canevas, feed = curseur de fin de page, qui = nom de l'interlocuteur ('' : aucun).
        MenuMessage.NoticeReceive, commande 4 : le nom n'est montre que sur la fenetre du terrain (m_nowType == 0) ; le cadre devient alors frameData 191 (le meme que 192 + un onglet colle au bord haut-gauche, souligne)
        et le TextMesh « m_who » recoit le nom. Les cotes servant a poser la fenetre (etendue(), bas()) restent ceux du cadre sans onglet : l'onglet depasse vers le haut, il ne decale rien."""
        ts = self.d['types']; t = ts[typ] if 0 <= typ < len(ts) else ts[0]
        fm = self.d.get('frame_mats') or [{'sheet': 0, 'part': 4}]
        who = (who or '').strip(); has_tab = bool(who) and typ == 0 and len(self.ml.borders) > BORDER_WITH_NAME
        if typ != self.type or has_tab != self.with_name:
            self.type = typ; self.with_name = has_tab; w = t['win']; cv = t['canvas']; fl = t['feed_local']; fd = self.d['feed']
            fmesh = self._base = t['frame_mesh']
            if has_tab: c = self.ml.borders[BORDER_WITH_NAME]; fmesh = dict(vtx=c['vtx'], uv=c['uv'], tris=c['tri'])
            self.N = {
                'cadre': self._node('cadre', list(w), fmesh['vtx'], fmesh['uv'], fmesh['tris'], dict(sheet=fm[0]['sheet'], part=fm[0]['part'], color=None)),
                'canevas': self._node('canevas', [w[0], w[1] + 4.0, w[2]], [[v[0], v[2]] for v in cv['vtx']], [list(u) for u in cv['uv']], cv['tris'], dict(sheet='msg', color=[1, 1, 1, 1])),
                'curseur': self._node('curseur', [w[0] + fl[0], w[1] + fl[1] + 6.0, w[2] + fl[2]], fd['vtx'], fd['uv'], fd['tris'], dict(sheet=fd['mats'][0]['sheet'], part=fd['mats'][0]['part'], color=None)),
            }
            if has_tab:                                                  # TextMesh « m_who » : position locale (-104,5 ; 4 ; BIAS_FONT_Y - 104), taille 10, ancre « haut centre », texte centre, blanc
                node = self._node('qui', [w[0] + WHO_POS[0], w[1] + WHO_POS[1], w[2] + WHO_POS[2] + self.ml.hdr['lang']['dy']], [], [], {}, None)
                node['mats'] = []; node['text'] = dict(text=who, characterSize=WHO_SIZE, lineSpacing=1.0, anchor=1, alignment=1, font=0); self.N['qui'] = node
            self.uv0 = [list(u) for u in cv['uv']]; self._ty = None
        if has_tab: self.N['qui']['text']['text'] = who
        self.who = who if has_tab else ''; self.t += 1
        self.N['curseur']['act'] = bool(feed); self.feed = bool(feed)
        if y != self.y or typ != getattr(self, '_ty', None):
            self.y = y; self._ty = typ
            dv = (int(y) & 0x1ff) / 512.0
            self.N['canevas']['uv'] = [[u[0], u[1] + dv] for u in self.uv0]

    def visible(self, nid):
        node = self.N.get(nid)
        return bool(node and node['act'])

    def extent(self):
        c = self.N.get('cadre')
        if not c or not c['vtx']: return None
        vt = self._base['vtx'] if self.with_name else c['vtx']          # (l'onglet du nom ne compte pas : le Oui/Non et l'echelle gardent la place du cadre sans onglet)
        return (c['pos'][2] + min(v[1] for v in vt), c['pos'][2] + max(v[1] for v in vt))

    def visible_extent(self):
        """(x0, x1, z0, z1) du dessin VISIBLE du cadre des dialogues (sans l'onglet du nom), en unites d'interface (voir `visible_edges`) ; les bords de la maille quand la feuille n'est pas connue."""
        c = self.N.get('cadre')
        if not c or not c['vtx']: return None
        b = getattr(self, '_vis', None)
        if b is None or b[0] != (self.type, self.with_name):
            m = self._base if self.with_name else dict(vtx=c['vtx'], uv=c['uv'], tris=(c['sub'] or {}).get('0'))
            al = SHEET_ALPHA.get(c['mats'][0].get('sheet')) if c['mats'] else None
            v = visible_edges(m['vtx'], m['uv'], m['tris'], al) if (al is not None and m.get('tris')) else None
            self._vis = b = ((self.type, self.with_name), v or (min(p[0] for p in m['vtx']), max(p[0] for p in m['vtx']), min(p[1] for p in m['vtx']), max(p[1] for p in m['vtx'])))
        v = b[1]; return (c['pos'][0] + v[0], c['pos'][0] + v[1], c['pos'][2] + v[2], c['pos'][2] + v[3])

    def bottom(self):
        """Ordonnee (unites d'interface) du bord bas du cadre."""
        c = self.N.get('cadre')
        return c['pos'][2] + min(v[1] for v in c['vtx']) if c and c['vtx'] else 0.0

    def extent_x(self):
        """(gauche, droite) du cadre, unites d'interface (Render._texte : limites dans lesquelles un texte doit tenir)."""
        c = self.N.get('cadre')
        return (c['pos'][0] + min(v[0] for v in c['vtx']), c['pos'][0] + max(v[0] for v in c['vtx'])) if c and c['vtx'] else None

    def rects(self):
        c = self.N.get('cadre')
        if not c or not c['vtx']: return []
        return [(c['pos'][0] + min(v[0] for v in c['vtx']), c['pos'][2] + min(v[1] for v in c['vtx']), c['pos'][0] + max(v[0] for v in c['vtx']), c['pos'][2] + max(v[1] for v in c['vtx']))]


THIN_SPACES = '\u00a0\u202f\u2009'                       # espaces que la police du jeu dessine plus larges (U+00A0 : 11 px au lieu de 5) ou n'a pas (U+202F, U+2009)


class BitmapFont:
    """Police bitmap Unity du jeu pour la langue anglaise (et le patch FR) : « SE-GARRIR » (Font « Garrick », 20 px, 218 glyphes) ; elle remplace GMaruGoPro-M, la police japonaise.
    Les donnees (ui_garrir.json : metriques et rectangles des glyphes ; ui_garrir.png : atlas 256 x 256, alpha) sont extraites de base.apk par prepare_resources.
    Un TextMesh de caractere de taille cs affiche 1 px de police = cs * 0.1 unite d'interface ; la largeur d'une ligne = somme des « advance » des glyphes (pas de crenage)."""
    PAD = 2                                                       # marge (px de police) autour d'une ligne : certains glyphes depassent leur « advance » (W, ’, …)
    UP, DOWN = 22, 9                                             # lignes de texture au-dessus / au-dessous de la ligne de base

    def __init__(self, json_path, png_path):
        from PIL import Image
        d = json.load(open(json_path, encoding='utf-8'))
        self.leading = d['lineSpacing']; self.ascent = d['ascent']
        atlas = np.asarray(Image.open(png_path).convert('RGBA'))[::-1, :, 3]      # ligne n = v * 256 (coordonnees de texture d'Unity : v = 0 en bas)
        self.G = {}
        for code, vx, vy, vw, vh, adv, flip, ux, uy, uw, uh in d['glyphes']:
            c0, c1 = int(round(ux * 256)), int(round((ux + uw) * 256)); ra, rb = int(round(uy * 256)), int(round((uy + uh) * 256))
            b = atlas[min(ra, rb):max(ra, rb), c0:c1]
            if flip: b = b.T[::-1, ::-1]                          # glyphe « flipped » : stocke transpose dans l'atlas
            self.G[code] = (int(round(adv)), int(round(vx)), int(round(-vy - self.ascent)), np.ascontiguousarray(b))      # (advance, decalage x, haut du glyphe par rapport a la ligne de base (vers le bas), bitmap)
        self.tex = {}; self.wid = {}; self.fallback = None

    def _glyph(self, c):
        if c in THIN_SPACES and 32 in self.G: return self.G[32]      # espace insecable (U+00A0), fine (U+202F) ou mince (U+2009) = l'espace normale (5 px) : le glyphe 160 de la police a un advance de 11 px (le patch FR met U+00A0 avant « ! », « ? » et « : »)
        g = self.G.get(ord(c))
        if g is not None: return g
        if c < ' ': return (0, 0, 0, np.zeros((0, 0), np.uint8))       # caracteres de controle (« \r » en fin de ligne) : ni largeur ni dessin
        return None

    def width_px(self, text):
        """Largeur d'une ligne en px de police (somme des advance ; un caractere absent de la police compte comme une espace)."""
        w = self.wid.get(text)
        if w is None:
            w = self.wid[text] = sum((self._glyph(c) or self.G[32])[0] for c in text)
        return w

    def line(self, text):
        """-> (texture, largeur, hauteur, base) en px de police ; base = distance du haut de l'image a la ligne de base."""
        r = self.tex.get(text)
        if r is None:
            if len(self.tex) > 800:
                for t, *_ in self.tex.values(): t.delete() if hasattr(t, 'delete') else None
                self.tex.clear()
            W = int(self.width_px(text)) + 2 * self.PAD; H = self.UP + self.DOWN
            a = np.zeros((H, W), np.uint8); x = self.PAD
            for c in text:
                g = self._glyph(c) or self.G[32]
                adv, vx, top, b = g
                if b.size:
                    y0 = self.UP + top; x0 = x + vx; h, w = b.shape
                    sub = a[max(y0, 0):y0 + h, max(x0, 0):x0 + w]
                    bb = b[max(-y0, 0):max(-y0, 0) + sub.shape[0], max(-x0, 0):max(-x0, 0) + sub.shape[1]]
                    sub[...] = np.maximum(sub, bb)
                x += adv
            rgba = np.zeros((H, W, 4), np.uint8); rgba[..., :3] = 255; rgba[..., 3] = a
            img = pyglet.image.ImageData(W, H, 'RGBA', np.ascontiguousarray(rgba[::-1]).tobytes(), pitch=W * 4)
            t = img.get_texture(); gl.glBindTexture(t.target, t.id)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)      # filtre bilineaire, comme l'atlas du jeu (Texture2D.filterMode = Bilinear)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
            r = self.tex[text] = (t, W, H, self.UP)
        return r


class Texts:
    """Lignes de texte -> textures (police du jeu rendue par Pillow, blanche ; la couleur est appliquee au dessin)."""
    def __init__(self, font):
        self.font = font; self.pol = {}; self.tex = {}; self.bitmap = None; self.messages = None
        d = os.path.dirname(font); j, g = os.path.join(d, 'ui_garrir.json'), os.path.join(d, 'ui_garrir.png')
        m = os.path.join(d, 'ui_messages.font')                   # police des messages du jeu (celle du canevas de texte du moteur : dialogues et combat), facultative : sans elle l'historique garde SE-GARRIR
        if os.path.exists(m) and not os.environ.get('DQ_POLICE_GMARU'):
            try:
                from dq4_pc.menus.message_font import MessageFont
                self.messages = MessageFont(m)
            except Exception as e: print(tr('Police des messages illisible (%r) : SE-GARRIR a la place.') % (e,), flush=True)
        if os.path.exists(j) and os.path.exists(g) and not os.environ.get('DQ_POLICE_GMARU'):        # DQ_POLICE_GMARU=1 (test) : ancienne police japonaise, pour comparer
            try: self.bitmap = BitmapFont(j, g)
            except Exception as e: print(tr('Police SE-GARRIR illisible (%r) : police japonaise GMaruGoPro-M a la place.') % (e,), flush=True)
    def _font(self, px):
        from PIL import ImageFont
        f = self.pol.get(px)
        if f is None:
            for path in (self.font, 'DejaVuSans.ttf', 'arial.ttf'):
                try: f = ImageFont.truetype(path, px); break
                except Exception: f = None
            if f is None: f = ImageFont.load_default()
            self.pol[px] = f
        return f
    def line(self, text, px):
        """-> (texture, largeur, hauteur, base) ; base = distance du haut de l'image a la ligne de base."""
        k = (text, px)
        r = self.tex.get(k)
        if r is None:
            from PIL import Image, ImageDraw
            if len(self.tex) > 600:
                for t, *_ in self.tex.values(): t.delete() if hasattr(t, 'delete') else None
                self.tex.clear()
            f = self._font(px); asc, desc = f.getmetrics(); w = int(math.ceil(f.getlength(text))) + 4; h = asc + desc + 4
            im = Image.new('L', (w, h), 0); ImageDraw.Draw(im).text((2, 2 + asc), text, font=f, fill=255, anchor='ls')
            a = np.zeros((h, w, 4), np.uint8); a[..., :3] = 255; a[..., 3] = np.asarray(im)
            img = pyglet.image.ImageData(w, h, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=w * 4)
            t = img.get_texture(); gl.glBindTexture(t.target, t.id)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
            r = self.tex[k] = (t, w, h, 2 + asc)
        return r


class Render:
    """Dessine des Fenetre sur l'ecran : prog GL maison, feuilles 0 (MenuTexture) et 1 (Button)."""
    def __init__(self, ml, sheets, font):
        self.ml = ml; self.neighbors = []                      # voisins : fenetres visibles de l'image (leurs cadres servent a compresser les textes d'une fenetre sans cadre)
        self.prog = ShaderProgram(Shader(VERTEX, 'vertex'), Shader(FRAG, 'fragment'))
        self._white = None                                  # texture blanche de 1 pixel (carres de couleur unie : lieux de la carte du monde)
        self.tex = {}
        from dq4_pc.world.hd import _dilate
        for k, arr in sheets.items():
            SHEET_ALPHA[k] = np.ascontiguousarray(arr[..., 3])             # (opacite d'origine : bords visibles des cadres)
            arr = _dilate(arr, 3)                          # pixels transparents = couleur du bord voisin (alpha inchange) : les cases de ces feuilles gardent du blanc / rose sous leurs pixels transparents, que le filtrage lineaire ramenait en liseré clair (« aura ») autour des icones et des portraits
            h, w = arr.shape[:2]
            img = pyglet.image.ImageData(w, h, 'RGBA', np.ascontiguousarray(arr[::-1]).tobytes(), pitch=w * 4)
            t = img.get_texture(); gl.glBindTexture(t.target, t.id)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            self.tex[k] = t
        self.texts = Texts(font)

    def update_canvas(self, a, name_str='msg'):
        """Canevas de texte du moteur (512 x 512 octets d'opacite) -> texture « msg » (blanc, alpha = opacite), qui boucle comme dans Unity."""
        h, w = a.shape
        rgba = np.empty((h, w, 4), np.uint8); rgba[..., :3] = 255; rgba[..., 3] = a
        img = pyglet.image.ImageData(w, h, 'RGBA', np.ascontiguousarray(rgba).tobytes(), pitch=w * 4)      # ligne 0 en premier = v 0, comme la texture Unity
        t = img.get_texture(); gl.glBindTexture(t.target, t.id)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        self.tex[name_str] = t

    # ---- construction des elements a dessiner
    def _items(self, win):
        """-> liste de (profondeur, ordre, genre, donnees) d'une fenetre."""
        items = []; o = 0
        for node in win.N.values():
            if not win.visible(node['id']): continue
            o += 1
            if node['vtx']: items.append((node['pos'][1], o, 'm', (win, node)))
            if node['text'] is not None and node['text'].get('text'): items.append((node['pos'][1] + 0.001, o, 't', (win, node)))
        items.sort(key=lambda x: (x[0], x[1]))
        return items

    def draw_all(self, wins, cx, cy, s, vp):
        """fens : liste de Fenetre ; (cx, cy) = pixel du centre de l'ecran du jeu ; s = pixels par unite ; vp = (largeur, hauteur) de la fenetre."""
        if not wins: return
        items = []
        for wi, win in enumerate(wins): items += [(d, wi, o, g, x) for d, o, g, x in self._items(win)]
        for wi, win in enumerate(wins):
            if getattr(win, 'typ', 0) in (25, 26) and win.game_map is not None: items.append((1.0, wi, 0, 'c', (win, None)))         # plan : au-dessus du fond du cadre (profondeur 0), sous le marqueur (12 et plus)
        items.sort(key=lambda x: x[:3])                      # comme Unity (objets transparents tries par profondeur sur la camera) : profondeur d'abord, puis la fenetre la plus recente devant ; le fond d'une fenetre ne recouvre plus les boutons d'une autre
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA); gl.glDisable(gl.GL_DEPTH_TEST)
        self.prog.use(); self.prog['vp'] = (float(vp[0]), float(vp[1]))
        lot = None; buf = []
        def drain():
            nonlocal buf
            if buf and lot:
                a = np.concatenate(buf).astype(np.float32); n = len(a)
                vl = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', a[:, 0:2].ravel()), tex_coords=('f', a[:, 2:4].ravel()), colors=('f', a[:, 4:8].ravel()))
                gl.glActiveTexture(gl.GL_TEXTURE0); gl.glBindTexture(lot[0].target, lot[0].id); self.prog['mode'] = lot[1]
                vl.draw(gl.GL_TRIANGLES); vl.delete()
            buf = []
        ok_num = {id(win): {n.get('buttonId') for n in win.N.values() if n.get('pad') and not (n['pad'] & 0xA0) and n.get('buttonId') is not None and n.get('vtx')} for win in wins}       # numeros portes par un bouton de validation (manette 16 / 64)
        for _, _, _, g, (win, node) in items:
            if g == 'c':
                drain(); lot = None; self._map(win, cx, cy, s, vp); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            elif g == 'm':
                for k, mat in enumerate(node['mats']):
                    idx = node['sub'].get(str(k))
                    if not idx: continue
                    sh = mat.get('sheet')
                    if sh not in self.tex: continue
                    col = list(mat.get('color') or (1, 1, 1, 1)); mode = 0; off = (0.0, 0.0)
                    if k == 0 and node['buttonId'] is not None and 'part' in mat and mat['part'] == 10 and node['buttonId'] < 0 and win.selected_node == node['id']:
                        if getattr(win, 'press_node', None) == node['id']: col = [c * 0.75 for c in col]        # fleche de page APPUYEE : comme le mobile (IButton(Material), DisplayClass6_0.b__0 : Material.color = 0,75 sur les quatre canaux)
                        else: col[:3] = [1.4, 1.4, 1.4]                                 # fleche de page survolee (PC, le mobile n'a pas de survol) : eclaircie
                    elif k == 0 and node['buttonId'] is not None and (node['buttonId'] >= 0 or win.selected_node == node['id']) and 'part' in mat and mat['part'] == 7:
                        if not is_state_active(node['etat']): state = node['etat']              # grise / inverse / invisible : ni survol ni curseur (le test de contact est coupe)
                        elif win.selected_node is not None: state = 1 if node['id'] == win.selected_node else node['etat']       # souris : seul l'element pointe (ou appuye) est en surbrillance, pas toute la rangee qui partage son numero
                        else: state = 1 if (win.selected is not None and win.selected == node['buttonId'] and not ((node['pad'] or 0) & 0xA0 and node['buttonId'] in ok_num[id(win)])) else node['etat']       # un bouton d'annulation (manette 32 / 128, ex. « Rien ») qui partage son numero avec un bouton de validation (« Acheter ») ne s'allume pas avec lui
                        if state == 1 or state == 4: off = self.ml.pushed
                        if state == 2: col[3] = 0.0
                        if state == 3: mode = 1
                        if state == 4: mode = 2
                    if col[3] <= 0: continue
                    t = self.tex[sh]
                    if lot != (t, mode): drain(); lot = (t, mode)
                    v = np.array(node['vtx'], np.float32); u = np.array(node['uv'], np.float32)
                    ia = np.array(idx, np.int64); vv = v[ia]; uu = u[ia] + np.array(off, np.float32)
                    x = cx + (node['pos'][0] + vv[:, 0]) * s; y = cy + (node['pos'][2] + vv[:, 1]) * s
                    c = np.tile(np.array(col, np.float32), (len(ia), 1))
                    buf.append(np.column_stack([x, y, uu[:, 0], uu[:, 1], c]))
            else:
                drain(); lot = None
                self._text(win, node, cx, cy, s)
        drain()

    def _plate_model(self):
        """Maillage de la plaque de bouton du jeu (feuille Button, partie 7, neuf morceaux de la fenetre « liste » Make_NameButton) : sommets, UV, indices, couleur."""
        m = getattr(self, '_plate_model_cache', None)
        if m is None:
            m = False
            for t in self.ml.types.values():
                for n in t.get('nodes', []):
                    mm = n.get('mesh'); mats = n.get('mats') or []
                    if mm and mats and mats[0].get('sheet') == 1 and mats[0].get('part') == 7 and len(mm['vtx']) == 36 and n.get('parts', {}).get('buttonId') == 0:
                        m = (np.array(mm['vtx'], np.float32), np.array(mm['uv'], np.float32), np.array(mm['sub']['0'], np.int64), list(mats[0].get('color') or (1, 1, 1, 1))); break
                if m: break
            self._plate_model_cache = m
        return m or None

    def plate(self, x, y, w, h, vp, chosen=False, corner=None, grayed=False):
        """Dessine le fond d'un bouton exactement comme les fenetres du jeu (ex. « Soigner tous ») dans le rectangle pixel (x, y, w, h) : les coins gardent leurs proportions (celles du modele : 16 unites de coin pour sa hauteur),
        le milieu s'etire. choisi : version enfoncee de la feuille (celle d'un bouton choisi dans le jeu). coin : cote des coins en pixels (les 16 unites d'origine, quelle que soit la hauteur : boutons de l'ecran).
        grise : bouton inactif (shader gris du jeu, et assombri a 55 % : la couleur retiree se voit a peine sur cette plaque grise).
        -> False si la plaque du jeu est indisponible."""
        mod = self._plate_model()
        if mod is None or 1 not in self.tex: return False
        vtx, uv, idx, col = mod
        xs = sorted({round(float(v[0]), 2) for v in vtx}); zs = sorted({round(float(v[1]), 2) for v in vtx})          # quatre abscisses et quatre ordonnees : bords et limites des coins
        cap = min((xs[1] - xs[0]) * h / (zs[-1] - zs[0]) if corner is None else corner, w / 2.0, h / 2.0)                    # le coin garde sa proportion avec la hauteur de la plaque (ou la taille demandee)
        X = {xs[0]: x, xs[1]: x + cap, xs[2]: x + w - cap, xs[3]: x + w}; Y = {zs[3]: y + h, zs[2]: y + h - cap, zs[1]: y + cap, zs[0]: y}
        px = np.array([X[round(float(v[0]), 2)] for v in vtx[idx]], np.float32); py = np.array([Y[round(float(v[1]), 2)] for v in vtx[idx]], np.float32)
        uu = uv[idx] + (np.array(self.ml.pushed, np.float32) if chosen else 0.0)
        if grayed: col = [col[0] * 0.55, col[1] * 0.55, col[2] * 0.55, col[3]]
        a = np.column_stack([px, py, uu[:, 0], uu[:, 1], np.tile(np.array(col, np.float32), (len(idx), 1))]).astype(np.float32)
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA); gl.glDisable(gl.GL_DEPTH_TEST)
        self.prog.use(); self.prog['vp'] = (float(vp[0]), float(vp[1]))
        vl = self.prog.vertex_list(len(a), gl.GL_TRIANGLES, position=('f', a[:, 0:2].ravel()), tex_coords=('f', a[:, 2:4].ravel()), colors=('f', a[:, 4:8].ravel()))
        t = self.tex[1]; gl.glActiveTexture(gl.GL_TEXTURE0); gl.glBindTexture(t.target, t.id); self.prog['mode'] = 1 if grayed else 0
        vl.draw(gl.GL_TRIANGLES); vl.delete(); self.prog.stop()
        return True

    def _map(self, win, cx, cy, s, vp):
        """Plan de la fenetre de carte : texture 4:3 (plan agrandi, voile compris). Petite carte (type 25, ICityMap : CreateFromTexture 450 x 337,5 pose en (2, -2) sous le cadre, echelle locale 0,99) : de x = -223 a 222,5,
        de z = 398 a 63,875 ; grande carte du monde (type 26) : rectangle de 450 x 337,5 de x = -225 a 225 (position d'origine non lue : garde)."""
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA); gl.glDisable(gl.GL_DEPTH_TEST)
        self.prog.use(); self.prog['vp'] = (float(vp[0]), float(vp[1]))
        if getattr(win, 'typ', 0) == 25: xa, xb, zh, zb = -223.0, 222.5, 398.0, 398.0 - 334.125
        else: xa, xb, zh, zb = -225.0, 225.0, 400.0, 400.0 - 337.5
        x0, x1, y1, y0 = cx + xa * s, cx + xb * s, cy + zh * s, cy + zb * s
        u0, v0, u1, v1 = getattr(win, 'map_uv', None) or (0.0, 0.0, 1.0, 1.0)          # grande carte du monde : fenetre de 256 x 192 pixels du plan de 1024 x 1024, centree sur le joueur
        a = np.array([[x0, y0, u0, v0], [x1, y0, u1, v0], [x1, y1, u1, v1], [x0, y0, u0, v0], [x1, y1, u1, v1], [x0, y1, u0, v1]], np.float32)
        vl = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', a[:, 0:2].ravel()), tex_coords=('f', a[:, 2:4].ravel()), colors=('f', np.ones(24, np.float32)))
        t = win.game_map; gl.glActiveTexture(gl.GL_TEXTURE0); gl.glBindTexture(t.target, t.id); self.prog['mode'] = getattr(win, 'map_mode', 3)         # plans agrandis (HD, voile compris) : filtrage lineaire ; grande carte du monde : bilineaire net
        vl.draw(gl.GL_TRIANGLES); vl.delete(); self.prog['mode'] = 0
        sp = getattr(win, 'special', None)
        if sp is not None:                                                            # code 4 : lieu special, croix rouge (MenuTexture, feuille 5, case 3 ; AddIcon 1,2 x 16 = 21,6 unites), coin bas gauche en (-227 + x k, 402 - y k) (ancrage suppose comme la plume)
            info = self.ml.info[5]; t = self.tex.get(info['tex']); k = 450.0 / 256.0
            if t is not None:
                uv = uv_icon(info, 3, 0); xl, yb = cx + (-227.0 + sp[0] * k) * s, cy + (402.0 - sp[1] * k) * s; xr, yt = xl + 21.6 * s, yb + 21.6 * s
                a = np.array([[xl, yt, *uv[0]], [xr, yt, *uv[1]], [xr, yb, *uv[2]], [xl, yt, *uv[0]], [xr, yb, *uv[2]], [xl, yb, *uv[3]]], np.float32)
                vl = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', a[:, 0:2].ravel()), tex_coords=('f', a[:, 2:4].ravel()), colors=('f', np.ones(24, np.float32)))
                gl.glBindTexture(t.target, t.id); self.prog['mode'] = 0; vl.draw(gl.GL_TRIANGLES); vl.delete()
        sy = getattr(win, 'symbols', None)
        if sy:                                                                        # lieux decouverts (BlinkMapSymbol) : carres rouges de 4 unites dont la transparence va et vient (0,5 par seconde : 1 -> 0 -> 1 en 4 s)
            if self._white is None:
                self._white = pyglet.image.ImageData(1, 1, 'RGBA', b'\xff\xff\xff\xff').get_texture()
            al = abs(1.0 - ((time.monotonic() - (win.t_blink or 0.0)) % 4.0) / 2.0); k = 450.0 / 256.0; q = []
            for xb, yb in sy:
                a0, b0 = cx + (-225.0 + xb * k - 2.0) * s, cy + (400.0 - yb * k - 2.0) * s; a1, b1 = a0 + 4.0 * s, b0 + 4.0 * s          # carre de 4 unites centre sur le lieu (comme le marqueur du joueur, de 24 unites, centre sur sa position)
                q += [[a0, b0], [a1, b0], [a1, b1], [a0, b0], [a1, b1], [a0, b1]]
            q = np.array(q, np.float32); n = len(q)
            vl = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', q.ravel()), tex_coords=('f', np.zeros(n * 2, np.float32)), colors=('f', np.tile(np.array([1.0, 0.0, 0.0, al], np.float32), n)))
            t = self._white; gl.glBindTexture(t.target, t.id); vl.draw(gl.GL_TRIANGLES); vl.delete()

    PLATE_MARGIN = 7.0          # marge (unites d'interface) laissee de chaque cote entre le texte et le bord de la plaque d'un bouton

    def _plate_width(self, win, node, zp):
        """Largeur utile (unites) de la plaque de bouton (partie 7) qui porte ce texte centre, ou None : la plaque dont le rectangle contient le point d'ancrage du texte."""
        t = node['text']; col = t['anchor'] % 3
        if col != 1 and win.typ not in (53, 54): return None                 # (textes a gauche / a droite d'une plaque : seulement les listes du menu de depart, les autres fenetres gardent leur mise en page)
        c = node.get('_pl')
        if c is None or c[0] is not win.t:
            r = None
            for o in win.N.values():
                if o is node or not o['vtx'] or not o['mats'] or o['mats'][0].get('part') != 7 or o['buttonId'] is None: continue
                xs = [o['pos'][0] + v[0] for v in o['vtx']]; zs = [o['pos'][2] + v[1] for v in o['vtx']]
                if min(xs) <= node['pos'][0] <= max(xs) and min(zs) <= zp <= max(zs): r = (min(xs), max(xs)); break
            node['_pl'] = c = (win.t, r)
        r = c[1]
        if r is None: return None
        xa = node['pos'][0]
        if col == 1: return r[1] - r[0] - 2 * self.PLATE_MARGIN                                      # texte centre : la plaque entiere
        return (r[1] - self.PLATE_MARGIN - xa) if col == 0 else (xa - r[0] - self.PLATE_MARGIN)      # texte a gauche / a droite de son point d'ancrage (ex. « Chapitre 1 Nv. 1 001:07 » d'une ligne de journal) : jusqu'au bord de la plaque

    def _adjust_description(self, node, lines, layout, nmax, bm, u, ts, s, emy):
        """Description dont le cadre montre `nmax` lignes sur `layout` unites de large : (lignes, facteur de compression). Un texte qui tient deja (au plus `nmax` lignes, aucune plus large que le cadre) est laisse tel quel, avec les retours a la ligne du patch.
        Sinon les retours a la ligne sont remplaces par des espaces et le texte est recoupe a la largeur du cadre ; s'il faut encore plus de `nmax` lignes, il est comprime en largeur (jusqu'a COMPRESSION_MIN) pour tenir en `nmax` lignes."""
        lookup_key = (tuple(lines), layout, nmax, u, ts, s)
        c = node.get('_adj')
        if c is not None and c[0] == lookup_key: return c[1]
        px = max(6, int(round(emy * s)))
        def wid(x):
            x = re.sub(r'@c\d', '', x)
            return bm.width_px(x) * u * ts if bm else (self.texts.line(x, px)[1] - 4) / s * ts
        useful = list(lines)
        while useful and not useful[-1].strip(): useful.pop()
        if not useful or (len(useful) <= nmax and all(wid(l.strip()) <= layout + 0.5 for l in useful)): res = (lines, 1.0)
        else:
            words = ' '.join(l.strip() for l in useful).split()
            def cut(d):
                out = []; cur = ''
                for w in words:
                    attempt = cur + ' ' + w if cur else w
                    if cur and wid(attempt) > d: out.append(cur); cur = w
                    else: cur = attempt
                if cur: out.append(cur)
                return out
            f = 1.0; out = cut(layout)
            while not (len(out) <= nmax and max(wid(l) for l in out) <= layout / f + 0.5) and f > COMPRESSION_MIN + 1e-9:
                f = max(COMPRESSION_MIN, round(f - 0.05, 4)); out = cut(layout / f)
            res = (out, f)
        node['_adj'] = (lookup_key, res)
        return res

    def _text(self, win, node, cx, cy, s):
        t = node['text']; lang = self.ml.hdr['lang']
        lines = t['text'].split('\n')
        bm = self.texts.bitmap                                         # police d'origine (SE-GARRIR) : 1 px de police = characterSize * 0.1 unite ; sinon GMaruGoPro-M rendue par Pillow
        u = t['characterSize'] * 0.1
        if bm: emy = u; step = bm.leading * u * t['lineSpacing']; asc = bm.ascent * u
        else: emy = FONT_SIZE * u; step = LINE_HEIGHT * emy * t['lineSpacing']; asc = 0.88 * emy
        zp = node['pos'][2] - lang['dy']                                  # le jeu ajoute dy a la position du texte (compensation de l'interligne de la police)
        ts = node['tscale']
        if node.get('wrap_x') is not None:                                # description plus large ou plus haute que son cadre : recoupee, puis comprimee si 2 lignes ne suffisent pas
            lines, f = self._adjust_description(node, lines, node['wrap_x'] - node['pos'][0], node.get('wrap_n', 2), bm, u, ts, s, emy); ts *= f
        N = len(lines)
        row = t['anchor'] // 3; col = t['anchor'] % 3
        base0 = first_line_baseline(zp, row, N, step, asc)               # TextMesh.anchor : le point d'ancrage est le haut (0-2), le milieu (3-5) ou le bas (6-8) du bloc de texte
        if bm: base0 += text_recentering(bm.leading, u, t['lineSpacing'])      # (police d'origine seulement : les reglages du jeu sont calcules pour la police japonaise, GMaruGoPro-M, quand elle sert de repli)
        px = max(6, int(round(emy * s)))
        def tint(i):
            pal = self.ml.colors[i] if 0 <= i < len(self.ml.colors) else (1, 1, 1, 1)
            return (min(pal[0], 1.0), min(pal[1], 1.0), min(pal[2], 1.0), 1.0)
        segs_l = []; cur = node['tcol']                                    # « @cN » change la couleur du texte (palette du jeu) ; elle se prolonge d'une ligne a l'autre
        for l in lines:
            segs = []; pos = 0
            for m in re.finditer(r'@c(\d)', l):
                if m.start() > pos: segs.append((l[pos:m.start()], cur))
                cur = int(m.group(1)); pos = m.end()
            if pos < len(l): segs.append((l[pos:], cur))
            segs_l.append(segs)
        if bm: wid = [sum(bm.width_px(t) * u * ts for t, _ in segs) for segs in segs_l]
        else: wid = [sum((self.texts.line(t, px)[1] - 4) / s * ts for t, _ in segs) for segs in segs_l]
        bl = max(wid) if wid else 0.0
        layout = self._plate_width(win, node, zp)
        if layout is None and win.extent_x() is None and not win.rects():              # fenetre sans cadre propre (titre et etiquettes d'un reglage) : le cadre est dans une autre fenetre visible, on prend le plus petit rectangle qui contient le point d'ancrage
            xa = node['pos'][0]; z_a = node['pos'][2] - lang['dy']; r_min = None
            for v in self.neighbors:
                for (x0, z0, x1, z1) in v.rects():
                    if x0 <= xa <= x1 and z0 <= z_a <= z1 and (r_min is None or (x1 - x0) * (z1 - z0) < (r_min[2] - r_min[0]) * (r_min[3] - r_min[1])): r_min = (x0, z0, x1, z1)
            if r_min:
                layout = {0: r_min[2] - self.PLATE_MARGIN - xa, 1: 2 * min(xa - r_min[0], r_min[2] - xa) - 2 * self.PLATE_MARGIN, 2: xa - r_min[0] - self.PLATE_MARGIN}[col]
        if layout is None and bl > 0:                                     # hors plaque de bouton : le texte doit tenir dans la largeur de sa fenetre (a partir de son point d'ancrage, avec la meme marge)
            ex = win.extent_x(); xa = node['pos'][0]
            if ex and ex[0] <= xa <= ex[1]:
                layout = {0: ex[1] - self.PLATE_MARGIN - xa, 1: 2 * min(xa - ex[0], ex[1] - xa) - 2 * self.PLATE_MARGIN, 2: xa - ex[0] - self.PLATE_MARGIN}[col]
                if layout < 0.4 * bl: layout = None                         # (ancrage trop pres du bord pour que ce soit le texte qui soit trop large)
        if node.get('fit_x') is not None and col == 0: layout = node['fit_x'] - node['pos'][0]      # limite posee par la fenetre (ligne de cout de la fiche d'un sort) : le cadre n'est pas un element de la fenetre
        if layout and bl > layout and compress_label(bool(bm), node.get('fit_x'), win.typ):      # texte plus large que le bouton qui le porte (traduction plus longue que l'original) : compresse en largeur pour tenir dedans (avec la police d'origine : seulement la ligne de cout de la fiche d'un sort, « Cout en PM 10/ 30 » est plus long que « MP Cost 10/ 30 » et sortait du cadre)
            f = max(0.7, layout / bl); ts *= f; wid = [w * f for w in wid]; bl *= f
        for i, segs in enumerate(segs_l):
            if not segs: continue
            lw = wid[i]
            al = {0: 0.0, 1: (bl - lw) / 2, 2: bl - lw}[t['alignment']]  # alignement de la ligne dans le bloc
            bx = {0: 0.0, 1: bl / 2, 2: bl}[col]
            xs = node['pos'][0] - bx + al
            y_base = base0 - i * step
            for text, ci in segs:
                if bm:                                                   # texture a la taille native de la police (1 px = 1 px de police), agrandie par le filtre bilineaire comme dans Unity
                    tex, w, h, b = bm.line(text); k = u * s
                    x = cx + xs * s - bm.PAD * k * ts; y = cy + y_base * s - (h - b) * k
                    wd = w * k * ts; ht = h * k; advance = bm.width_px(text) * u * ts
                else:
                    tex, w, h, b = self.texts.line(text, px)
                    x = cx + xs * s - 2 * ts; y = cy + y_base * s - (h - b)
                    wd = w * ts; ht = h; advance = (w - 4) / s * ts
                a = np.array([[x, y, 0, 0], [x + wd, y, 1, 0], [x + wd, y + ht, 1, 1], [x, y, 0, 0], [x + wd, y + ht, 1, 1], [x, y + ht, 0, 1]], np.float32)
                vl = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', a[:, 0:2].ravel()), tex_coords=('f', a[:, 2:4].ravel()), colors=('f', np.tile(np.array(tint(ci), np.float32), 6)))
                gl.glActiveTexture(gl.GL_TEXTURE0); gl.glBindTexture(tex.target, tex.id); self.prog['mode'] = 0
                vl.draw(gl.GL_TRIANGLES); vl.delete()
                xs += advance


class Manager:
    """Recoit ce que l'interface du jeu memorise (Interface.obs) et tient une Fenetre par port de menu."""
    def __init__(self, ml):
        self.ml = ml; self.f = {}
    def open_menu(self, port, typ):
        t = self.ml.types.get(str(typ))
        if t and not t.get('err') and t.get('nodes'): self.f[port] = Window(self.ml, typ)
        else: self.f.pop(port, None)
    def shutdown(self, port): self.f.pop(port, None)
    def replay(self, ui):
        """Les fenetres des ports 2 a 11 (menus du terrain) sont creees par le moteur au demarrage, avant que la visionneuse n'ecoute : on rejoue leur creation et leur contenu."""
        for port, f in sorted(ui.f.items()):
            if f.get('type') is None: continue
            self.open_menu(port, f['type'])
            for (i, no), txt in f['cases'].items(): self.param_str(port, i, no, txt)
            for (i, no), v in (f.get('ints') or {}).items(): self.param_int(port, i, no, v)
            for i, c in f['indic'].items(): self.code(port, i, c)
            for i, q in (f.get('plaq') or {}).items():
                if 'nom' in q and 'prm' in q: self.plate(port, i, q['nom'], q['prm'], q['code'])
            if f.get('dispo') is not None: self.arrange(port, f['dispo'])
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
    proj = None            # appelee avec un masque de monstres -> (x min, x max) en unites d'interface, ou None ; proj(masque, True) -> la liste des abscisses, une par monstre (fournie par la visionneuse)
    def plate(self, port, i, name_str, prm, code):
        f = self.f.get(port)
        if f: f.plate(i, name_str, prm, code)
    def arrange(self, port, n):
        f = self.f.get(port)
        if f: f.arrange(n, self.proj)
    def tick(self):
        """Une image du jeu : animations des fenetres (secousse des plaques de combat, clignotement de la fleche de cible)."""
        for f in self.f.values(): f.tick()


RESOURCES = {'ui_MenuTexture.png': 'MenuTexture', 'ui_Button.png': 'Button'}


def extract_garrir(o, d, json_path, png_path):
    """Police bitmap SE-GARRIR (Font Unity) -> ui_garrir.json (metriques, glyphes : code, vert x y l h, advance, flipped, uv x y l h) et ui_garrir.png (atlas RGBA, tel que le rend UnityPy)."""
    t = o.read_typetree()
    d.m_Texture.read().image.convert('RGBA').save(png_path)
    gl_ = [[r['index'], r['vert']['x'], r['vert']['y'], r['vert']['width'], r['vert']['height'], r['advance'], int(bool(r['flipped'])),
            r['uv']['x'], r['uv']['y'], r['uv']['width'], r['uv']['height']] for r in t['m_CharacterRects']]
    with open(json_path, 'w', encoding='utf-8') as f: json.dump({'nom': t['m_Name'], 'fontSize': t['m_FontSize'], 'lineSpacing': t['m_LineSpacing'], 'ascent': t['m_Ascent'], 'descent': t['m_Descent'], 'pixelScale': t['m_PixelScale'], 'glyphes': gl_}, f)


def prepare_resources(apk_folder, cache, log=print):
    """Extrait des APK du jeu (une seule fois) : feuilles MenuTexture et Button, police, maillages des cadres. -> True si tout est la."""
    dest = {n: os.path.join(cache, n) for n in list(RESOURCES) + ['ui_font.otf', 'ui_frameData.bin']}
    dest_g = [os.path.join(cache, n) for n in ('ui_garrir.json', 'ui_garrir.png')]            # police d'origine SE-GARRIR (facultative : sans elle, GMaruGoPro-M)
    try:
        from dq4_pc.menus.message_font import extract_message_font
        extract_message_font(apk_folder, cache, log)                         # police des messages (facultative), meme quand les autres ressources sont deja la
    except Exception as e: log(tr('Police des messages non extraite : %r') % (e,))
    if all(os.path.exists(p) for p in list(dest.values()) + dest_g): return True
    try:
        import UnityPy, zipfile
        os.makedirs(cache, exist_ok=True)
        log(tr('Lecture des ressources de menu du jeu (une seule fois)...'))
        base = UnityPy.load(os.path.join(apk_folder, 'base.apk'))
        for o in base.objects:
            if o.type.name == 'Texture2D':
                d = o.read()
                for file_name, name_str in RESOURCES.items():
                    if d.m_Name == name_str and not os.path.exists(dest[file_name]): d.image.convert('RGBA').save(dest[file_name])
            elif o.type.name == 'Font':
                d = o.read()
                if d.m_Name == 'GMaruGoPro-M' and d.m_FontData and not os.path.exists(dest['ui_font.otf']):
                    open(dest['ui_font.otf'], 'wb').write(bytes(d.m_FontData))
                elif d.m_Name == 'SE-GARRIR' and not all(os.path.exists(p) for p in dest_g):
                    try: extract_garrir(o, d, *dest_g)
                    except Exception as e: log(tr('Police SE-GARRIR non extraite : %r') % (e,))
        if not os.path.exists(dest['ui_frameData.bin']):
            pack = UnityPy.load(zipfile.ZipFile(os.path.join(apk_folder, 'split_UnityDataAssetPack.apk')).read('assets/bin/Data/datapack.unity3d'))
            for o in pack.objects:
                if o.type.name == 'TextAsset':
                    d = o.read()
                    if d.m_Name == 'frameData':
                        raw = d.m_Script; open(dest['ui_frameData.bin'], 'wb').write(raw.encode('utf-8', 'surrogateescape') if isinstance(raw, str) else bytes(raw)); break
        return all(os.path.exists(p) for p in dest.values())
    except Exception as e:
        log(tr('Ressources de menu indisponibles : %r') % (e,)); return False
