"""Fenetre « Historique » (page 'historique' du menu Pause, voir pause.py) : deux onglets, Dialogues (hors combat) et Combats ; le plus recent en bas. Une case a cocher « Favoris seulement » (a droite des onglets) ne garde dans
la liste de l'onglet ouvert que ses favoris ; elle est commune aux deux onglets (elle reste cochee quand on change d'onglet et quand on rouvre la fenetre) et son etat est enregistre dans les reglages (cle `historique_favoris_seuls`, ecrite a chaque changement) :
elle est retrouvee telle quelle d'une session a l'autre, comme les favoris eux-memes (fichier historique_favoris.json, voir history.py).

LA LISTE EST UNE SEULE COLONNE CONTINUE : les plus anciennes entrees en haut, les plus recentes en bas, et la vue s'ouvre tout en bas (derniere entree visible). Le defilement est continu, au pixel : aucune page, aucun cran, aucune
mise en page qui depend de la position (les boites sont posees une fois pour toutes, la position ne fait que les deplacer) ; une entree qui depasse du bord de la liste est simplement coupee par un cadre de decoupe (glScissor), comme du
texte qui defile. Liste plus courte que la fenetre : collee en bas, comme un fil de messages (le plus recent reste toujours au meme endroit, en bas). Fonctions pures : `arrange` (empilement), `element_au_repere`.

Chaque element est dessine dans une BOITE DE DIALOGUE du jeu (la fenetre de message du terrain, 3 lignes : cadre 452 x 126 unites d'interface, tire de la mise en page d'origine ; meme echelle que dans le jeu ; classe
`Box`), avec le cadre et l'onglet du nom du jeu (frameData 192 et 191, dessines par ui_menu.MessageWindow), la police d'origine SE-GARRIR et les lignes posees comme dans le jeu : un dialogue avec le nom du locuteur
dans l'onglet SEULEMENT si le jeu l'affichait quand il a ete dit ; un combat avec son issue, chaque espece d'ennemis (qui est vaincu, enfui, disparu ou reste), l'or et l'experience gagnes et les objets obtenus.
Un dialogue tient dans une boite de 3 lignes (la suite est dans une boite suivante, « 2/2 » : simple etiquette, le defilement ne s'y arrete pas). Un COMBAT GRANDIT EN HAUTEUR pour tout contenir (#141) : la boite a autant
de lignes que le combat en demande, au moins 3 ; le cadre du jeu est etire (c'est un cadre a neuf morceaux : seul le milieu s'allonge, les coins gardent leur taille) ; au-dela de MAX_BATTLE_LINES lignes, le reste
continue dans une boite suivante. Une etoile en haut a droite de chaque element le met en favori (il est alors garde
dans un fichier jusqu'a ce qu'on retire l'etoile ; le reste de l'historique disparait quand on ferme la visionneuse). Le fond de la fenetre est aussi transparent que les autres fenetres du jeu (hud_mobile.GAME_OPACITY).
Le jeu NE S'ARRETE PAS tant que la fenetre est ouverte (#178 : aucune pause dans aucun menu) : aucune touche ni clic n'arrive au jeu, mais il continue de tourner et d'ecrire dans l'historique ; la liste suit (`follow_game` : les nouveaux
messages s'ajoutent en bas quand la vue est en bas ; quand on lit plus haut, la liste ne bouge pas, elle se met a jour au retour en bas).
Clavier : haut / bas (message precedent / suivant, repete si la touche est maintenue), page precedente / suivante (une page de la fenetre moins deux lignes), debut / fin, gauche / droite (onglet), Entree, Menu ou Action
(etoile du message choisi), F ou Carte (case « Favoris seulement »), la touche de l'historique (Dialogues -> Combats -> ferme), Echap / Annuler (retour). Souris : molette (2 lignes par cran), barre de defilement (fleches : une ligne,
piste : une page, curseur : glisser), glisser dans la liste (le contenu suit le pointeur), clic sur un onglet, sur la case ou sur une etoile.
MESSAGE CHOISI (`selected`, cible de la touche Entree) : haut / bas passent de message en message (ils ne font pas defiler la liste) ; la vue ne defile QUE pour montrer en entier le message choisi, quand il est coupe par un bord de la
fenetre ou hors de la fenetre, et du minimum necessaire (son bord rejoint le bord de la fenetre : `offset_to_see`). A la souris, le message survole est le message choisi. Le message choisi porte la petite fleche doree, au clavier
comme a la souris, et rien d'autre : ni grisé ni eclairci au survol ou au choix (derogation a la regle generale des menus). Defiler a la molette, a la barre ou en glissant ne change pas le message choisi ; au clavier, un message
choisi qui n'est plus du tout dans la fenetre est d'abord remplace par le plus proche message visible."""
import pyglet
from pyglet import gl
from dq4_pc.core import history as HI
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.persistence import settings as RG
from dq4_pc.menus import ui_menu as UM
from dq4_pc.language import tr, N_

GOLD = (255, 235, 4); WHITE = (255, 255, 255); GRAY = (150, 150, 150); HELPTEXT = (175, 175, 175); STAR = (255, 210, 40); EMPTY_STAR = (20, 20, 20)
DRAG_TOLERANCE = 6.0               # pixels : en dessous, un appui dans la liste n'est pas un glissement
TABS = ((N_('Dialogues'), 'dialogues'), (N_('Combats'), 'combats'))            # (noms traduits au dessin)
O_DIALOGUES, O_BATTLES = 0, 1
FILTER_CAPTION = N_('Favoris seulement')
BOX_SCALE = 1.12                 # agrandissement des fenetres du jeu par rapport a H / 800 (= fenetre.UI_ZOOM) : la boite de l'historique a la taille d'une boite de dialogue du jeu a l'ecran
TEXT_SCALE = 1.09                     # un pixel de la police d'origine (SE-GARRIR) = 1,09 unite d'interface dans le canevas de message du jeu (mesure : ligne de 371 pixels de police = 407 pixels a l'ecran a l'echelle 1,008 ; l'en-tete de la mise en page annonce 1,105, le moteur arrondit les avances)
EMPTY_MESSAGES = {'dialogues': N_("Aucun dialogue pour l'instant."), 'combats': N_("Aucun combat pour l'instant.")}
EMPTY_FAVORITES = {'dialogues': N_('Aucun dialogue en favori : décoche « Favoris seulement », choisis un dialogue et appuie sur Entrée (ou clique son étoile) pour le garder.'),
                 'combats': N_('Aucun combat en favori : décoche « Favoris seulement », choisis un combat et appuie sur Entrée (ou clique son étoile) pour le garder.')}            # (traduits au dessin, en entier avant d'etre coupes aux mots)


THIN_SPACES = '\u00a0\u202f\u2009'          # espace insecable (U+00A0), fine (U+202F) et mince (U+2009) : le patch FR met U+00A0 avant « ! », « ? » et « : »
NORMAL_SPACE = str.maketrans({c: ' ' for c in THIN_SPACES})


def normal_spaces(font, text):
    """Historique seulement (#161, D-243) : avec la police SE-GARRIR, l'espace insecable (glyphe 160 : 11 px d'avance), la fine et la mince sont dessinees comme l'espace normale du jeu (5 px) : sinon l'espace avant « ! », « ? » et « : » est presque doublee.
    Les autres menus (ui_menu.py) gardent la largeur que la police donne a ces caracteres, comme le jeu d'origine ; la police des messages (MessageFont) aussi (c'est celle du moteur : son U+00A0 fait 5 px)."""
    return text.translate(NORMAL_SPACE) if isinstance(font, UM.BitmapFont) else text


def wrap_words(text, width_px, max_width):
    """Coupe `text` en lignes aux espaces pour qu'aucune ne depasse `max_width` (largeur(t) = largeur d'une ligne t, dans l'unite de max_width). Un mot seul plus large que la limite reste seul sur sa ligne (il ne peut pas etre coupe). -> liste de lignes, jamais vide."""
    lines = []; cur = ''
    for word in text.split():
        cand = word if not cur else cur + ' ' + word
        if cur and width_px(cand) > max_width: lines.append(cur); cur = word
        else: cur = cand
    lines.append(cur)
    return lines


WHEEL_STEP = 2.0                    # lignes de texte (Box.STEP : 28 unites) par cran de molette : un pas fin et constant, jamais une entree entiere
ENTRIES_MARGIN = 6.0                    # (en k) vide au-dessus de la premiere boite et sous la derniere de la liste (le contenu n'est jamais colle au bord de la fenetre de decoupe)
TOLERANCE_PX = 0.5                   # pixels : en dessous, un message est « entierement visible » (arrondis du dessin)
ELEMENT_SPACING, PAGE_SPACING = 12.0, 4.0      # (en k) vide entre deux elements, entre deux boites d'un meme element
MAX_BATTLE_LINES = 12               # lignes de texte (entete comprise) qu'une boite de combat peut contenir avant de continuer dans une boite suivante (la boite fait alors 126 + 9 x 28 = 378 unites de haut)


def arrange(inputs, border_top, tab_top, spacing, page_spacing, margin):
    """Empile toute la liste dans UNE colonne, du plus ancien (en haut) au plus recent (en bas). `inputs` : un tuple par element, (nombre de boites, onglet du nom sur la premiere ?) ou (nombre de boites, onglet ?,
    [hauteur du cadre de chaque boite]) quand les boites n'ont pas toutes la meme hauteur (un combat grandit avec son texte) ; `border_top` est la hauteur des autres. Distances en pixels, comptees depuis
    le haut du contenu (vers le bas) : -> (boites, debuts, fins, hauteur).
    boites : (element, boite, nombre de boites, haut, haut de l'onglet, haut du cadre) ; `topmost` = bord superieur de la boite, onglet du nom compris (le cadre commence `tab_top` plus bas) ;
    debuts[i], fins[i] : haut de la premiere boite et bas de la derniere de l'element i ; hauteur : hauteur du contenu, marges haute et basse comprises (0 si la liste est vide).
    Ne depend d'aucune position de defilement : la position ne fait que deplacer le tout."""
    boxes = []; starts = []; ends = []; y = margin
    for i, ent in enumerate(inputs):
        num, with_name = ent[0], ent[1]; tops = ent[2] if len(ent) > 2 else ()
        starts.append(y)
        for p in range(max(1, num)):
            hn = tab_top if (p == 0 and with_name) else 0.0; hc = tops[p] if p < len(tops) else border_top
            boxes.append((i, p, max(1, num), y, hn, hc)); y += hn + hc
            if p < max(1, num) - 1: y += page_spacing
        ends.append(y); y += spacing
    return boxes, starts, ends, ((y - spacing + margin) if inputs else 0.0)


def extent(starts, ends, hc, i):
    """Ce qu'il faut montrer pour que le message i soit « entierement visible » : (haut, bas) en pixels depuis le haut du contenu. Le message lui-meme (debuts[i] : onglet du nom compris, fins[i]) ; pour le premier et le dernier
    de la liste, la marge de la liste en plus (le premier va jusqu'au haut du contenu, le dernier jusqu'au bas : quand on y arrive, la liste est tout en haut / tout en bas)."""
    return (0.0 if i == 0 else starts[i]), (hc if i == len(starts) - 1 else ends[i])


def offset_to_see(starts, ends, hc, hv, scroll_offset, i):
    """Nouveau decalage de la vue (pixels depuis le bas : 0 = tout en bas) qui montre le message i en entier, en changeant le decalage DU MINIMUM : inchange si le message est deja entierement visible, sinon juste ce qu'il faut pour que
    son bord coupe rejoigne le bord de la fenetre (haut ou bas). Un message plus haut que la fenetre : son debut en haut de la fenetre. La fenetre fait hv pixels et montre, depuis le haut du contenu, de hc - decal - hv a hc - decal."""
    topmost, bottom = extent(starts, ends, hc, i); top = hc - scroll_offset - hv
    if bottom - topmost >= hv: top = topmost
    elif topmost < top - TOLERANCE_PX: top = topmost
    elif bottom > top + hv + TOLERANCE_PX: top = bottom - hv
    else: return scroll_offset
    return min(max(0.0, hc - hv), max(0.0, hc - hv - top))


def visible_elements(starts, ends, hc, hv, scroll_offset, fully_visible_only):
    """Indices des messages visibles dans la fenetre (voir offset_to_see) : ceux qui y sont entierement (`fully_visible_only`), sinon ceux dont une partie au moins y est."""
    top = hc - scroll_offset - hv; r = []
    for i in range(len(starts)):
        topmost, bottom = extent(starts, ends, hc, i)
        if (topmost >= top - TOLERANCE_PX and bottom <= top + hv + TOLERANCE_PX) if fully_visible_only else (ends[i] > top and starts[i] < top + hv): r.append(i)
    return r


def game_time(t):
    """Temps de jeu (1/60 s) -> « 1:05:12 »."""
    s = max(0, int(t)) // 60
    return '%d:%02d:%02d' % (s // 3600, s % 3600 // 60, s % 60)


def next_tab(i, d=1): return (i + d) % len(TABS)


def next_key(tab):
    """Touche de l'historique dans la fenetre : Dialogues -> Combats ; Combats -> fermer (None)."""
    return O_BATTLES if tab == O_DIALOGUES else None


class Box:
    """Boite de dialogue du terrain (MenuMessage type 0) a 3 lignes, en unites d'interface du jeu (800 de haut) : la taille du cadre (frameData 192), de l'onglet du nom (frameData 191) et le placement des lignes
    de texte. Les dimensions viennent de la mise en page d'origine quand elle est chargee (`from_ml`), sinon des valeurs mesurees sur les captures du jeu. Une seule boite pour tout : 1, 2 ou 3 lignes, dialogue ou combat."""
    WIDTH, UP = 452.0, 126.0                  # cadre : x -223 a 229, z -251 a -125
    TAB_L, TAB_H = 246.0, 32.0           # onglet du nom : x -223 a 23, z -125 a -93 (depasse au-dessus du cadre)
    LINES, STEP = 3, 28.0                      # trois lignes de 28 (PageLayout : limit_lines(types[0], 3, 28.0))
    TEXT_X, BASE_1 = 12.0, 37.2               # bord gauche du texte et ligne de base de la 1re ligne : distances au coin haut gauche du cadre (mesurees sur une capture du jeu : texte a 11 px du trait gauche du cadre, 1re ligne de base a 31 px du trait haut, a l'echelle 1,008)
    NAME_X, NAME_TOP = 118.5, -21.0             # milieu du nom (depuis le bord gauche du cadre) et haut du texte du nom (depuis le haut du cadre : MenuMessage.m_who, 21 au-dessus) -- repli sans mise en page

    def __init__(self, wid=None, topmost=None, tab=None, x0=-223.0, z0=-251.0, win=(0.0, 10.0, 86.0), text_scale=TEXT_SCALE):
        if wid: self.WIDTH = wid
        if topmost: self.UP = topmost
        if tab: self.TAB_L, self.TAB_H = tab
        self.x0, self.z0, self.win, self.text_scale = x0, z0, tuple(win), text_scale

    @classmethod
    def from_ml(cls, ml):
        """Boite lue dans la mise en page d'origine (PageLayout) ; les valeurs mesurees si elle manque ou est inutilisable."""
        try:
            t = ml.message['types'][0]; vt = t['frame_mesh']['vtx']; xs = [v[0] for v in vt]; zs = [v[1] for v in vt]
            tab = None
            if len(ml.borders) > UM.BORDER_WITH_NAME:
                c = ml.borders[UM.BORDER_WITH_NAME]['vtx']; hs = [v for v in c if v[1] > max(zs) + 0.5]
                if hs: tab = (max(v[0] for v in hs) - min(v[0] for v in hs), max(v[1] for v in hs) - max(zs))
            return cls(max(xs) - min(xs), max(zs) - min(zs), tab, min(xs), min(zs), t['win'])
        except Exception:
            return cls()

    MARGINS = 120.0                              # (en unites de k) marges de la fenetre de l'historique autour de la boite : gauche, colonne de l'etoile, barre de defilement

    def scale_factor(self, H, W, k):
        """Pixels par unite : celle des fenetres du jeu (H / 800 x BOX_SCALE), reduite pour que la boite, sa colonne d'etoile et les marges tiennent dans la fenetre de la visionneuse."""
        return max(0.3, min(H / 800.0 * BOX_SCALE, (W - 40 * k - self.MARGINS * k) / self.WIDTH))

    def base(self, rank):
        """Distance de la ligne de base de la ligne `rank` (0, 1, 2...) au haut du cadre, unites."""
        return self.BASE_1 + rank * self.STEP

    BASE_MSG = 35.0                            # idem avec la police des messages du jeu (celle du canevas du moteur) : le canevas commence 15 unites sous le haut du cadre, la cellule d'une ligne a 20 rangees au-dessus de la ligne de base

    def base_msg(self, rank):
        """Comme `base`, pour le texte dessine avec la police des messages du jeu."""
        return self.BASE_MSG + rank * self.STEP

    def top_for(self, lines):
        """Hauteur du cadre (unites) pour `lines` lignes de texte : celle de la boite du jeu jusqu'a 3 lignes, puis une ligne (STEP) de plus par ligne."""
        return self.UP + max(0, int(lines) - self.LINES) * self.STEP

    def text_width(self):
        """Largeur utile d'une ligne de texte (unites) : du bord gauche du texte a la marge droite du canevas (le canevas est large de WIDTH - 18)."""
        return self.WIDTH - self.TEXT_X - 12.0


def stretch_border(vtx, extra):
    """Sommets d'un cadre a neuf morceaux (frameData 192 : coins de 12 unites, milieu qui s'etire) allonges de `extra` unites vers le haut : tout sommet de la moitie haute monte, les coins du haut gardent leur taille, le
    milieu s'allonge (ses UV ne changent pas : le motif du milieu est etire, comme le fait le jeu quand il agrandit un cadre). -> nouvelle liste (la mise en page d'origine n'est jamais modifiee)."""
    if not vtx: return []
    zs = [v[1] for v in vtx]; mi = (min(zs) + max(zs)) / 2.0
    return [[v[0], v[1] + (extra if v[1] > mi else 0.0)] + list(v[2:]) for v in vtx]


def box_lines(page, is_first, battle):
    """Nombre de lignes de texte d'une boite : les rangees de la page, plus l'entete (issue et heure) sur la premiere boite d'un combat ; trois au moins (la boite du jeu)."""
    return max(Box.LINES, len(page) + (1 if (battle and is_first) else 0))


def paginate(rows, with_header, lines=3):
    """Rangees de texte -> pages de `lines` rangees au plus (au moins une page, meme vide) ; sur la 1re page d'un combat, l'entete (issue et heure) prend une rangee."""
    pages = []; cap = max(1, lines - (1 if with_header else 0)); i = 0
    while True:
        pages.append(list(rows[i:i + cap])); i += cap; cap = lines
        if i >= len(rows): return pages


def wrap_like_the_game(font, text):
    """Lignes de `text` coupees comme le moteur coupe un message (MessageFont.couper : les retours a la ligne du texte gardes, sans espace en fin de ligne ni ligne vide a la fin ; au moins une ligne)."""
    lines = [l.rstrip(' ') for l in font.wrap_text(text)]
    while lines and not lines[-1]: lines.pop()
    return lines or ['']


def rows_of(e, measure, width_px, font=None):
    """Rangees de texte d'un element, coupees a `width_px` (mesure(chaine) -> largeur dans la meme unite) : le texte d'un dialogue (ses retours a la ligne gardes) ; pour un combat une rangee par espece d'ennemis (avec le
    sort de chacun), puis l'or et l'experience, puis les objets (HI.battle_lines) ; une ligne trop large pour la boite continue sur la rangee suivante. L'issue et l'heure sont dans l'entete.
    Avec `font` (la police des messages du jeu, MessageFont) les lignes sont coupees exactement comme le moteur coupe les siennes et `measure`, `width_px` ne servent pas."""
    cut = (lambda t: wrap_like_the_game(font, t)) if font is not None else (lambda t: HI.wrap_text(t, width_px, measure))
    if e.type != HI.BATTLE_TYPE: return cut(e.text)
    out = []
    for l in HI.battle_lines(e): out.extend(cut(l))
    return out


class HistoryView:
    def __init__(self, pause):
        self.P = pause; self.J = pause.J
        self.tab = O_DIALOGUES; self.elements = []
        self.pos = 0.0                                                  # position de defilement, en pixels : 0 = tout en bas (le plus recent visible), plus grand = plus ancien (voir decal et repere)
        self.selected = 0                                                    # message choisi (fleche doree, touche Entree) : choisi par haut / bas, par un clic ou, a la souris, par le survol (voir dessiner)
        self.hc = self.hv = 0.0; self.step = Box.STEP                  # hauteur du contenu, de la fenetre de la liste (pixels) et d'une ligne de texte (pixels), mesures a la derniere image ; avant la premiere image : rien a defiler
        self.center_target = None                                             # element a ramener au milieu de la vue des que la liste est mesuree (aller)
        self.starts = []; self.ends = []                               # haut de la premiere boite et bas de la derniere de chaque element, pixels depuis le haut du contenu (mesures a la derniere image ; vides tant que la liste n'est pas mesuree)
        self.zones = []; self.star_zones = []; self.tab_zones = []; self.barre = None; self.dragging_bar = None
        self.zone_ret = None
        self.favorites_only = self._read_filter(); self.filter_zone = None  # case « Favoris seulement » : cochee ? (reglage enregistre) ; sa zone a l'ecran (clic)
        self.drag = None                                               # glissement dans la liste : [y de depart, decalage de depart, deplace ?]
        self._spr = {}; self._lines = {}; self._layout = None; self._prev_s = None
        self._box = None; self._box_layout = None; self._wins = {}              # boite de dialogue standard (Boite) et les deux fenetres de message du jeu qui servent a dessiner son cadre (avec / sans onglet)

    # ---- donnees
    def enter(self, tab=O_DIALOGUES):
        """A l'ouverture de la page : recharge la liste, tout en bas sur l'element le plus recent (ensuite elle suit le jeu : `follow_game`)."""
        self.tab = tab if 0 <= tab < len(TABS) else O_DIALOGUES
        self.dragging_bar = None; self.drag = None; self._lines.clear()
        self.favorites_only = self._read_filter()
        h = getattr(self.J, 'history', None)
        if h is not None and hasattr(h, 'refresh'): h.refresh()          # (les favoris ranges par la cle : leur texte est redemande au jeu, voir History.actualiser)
        self.reload()

    def reload(self, keep=False):
        h = getattr(self.J, 'history', None)
        self.elements = h.entries(TABS[self.tab][1], self.favorites_only) if h is not None else []
        n = len(self.elements); self._layout = None; self.center_target = None; self.starts = []; self.ends = []
        if keep: self.selected = max(0, min(n - 1, self.selected))
        else: self.pos = 0.0; self.selected = max(0, n - 1)
        self.zones = []; self.star_zones = []

    def follow_game(self):
        """Le jeu tourne derriere la fenetre (#178) et peut ecrire dans l'historique (un dialogue, la fin d'un combat). Appele a chaque image : quand la vue est tout en bas (rien n'est cache plus bas), la liste est remplacee par la
        liste a jour ; le message choisi reste le meme (reconnu par son objet), sauf s'il etait le dernier : le choix suit alors le plus recent. Quand on lit plus haut, un glissement ou la barre est en cours, la liste ne bouge pas
        (la lecture ne saute pas) ; elle se met a jour des qu'on revient en bas. -> True si la liste a change."""
        h = getattr(self.J, 'history', None)
        if h is None or self.scroll_offset() > 0.5 or self.drag is not None or self.dragging_bar is not None: return False
        el = h.entries(TABS[self.tab][1], self.favorites_only); anc = self.elements
        if len(el) == len(anc) and all(a is b for a, b in zip(el, anc)): return False
        cur = self.current_item(); follow = cur is None or self.selected >= len(anc) - 1
        self.elements = el; n = len(el); self._layout = None; self.center_target = None; self.starts = []; self.ends = []; self.zones = []; self.star_zones = []; self.pos = 0.0
        i = None if follow else next((k for k, e in enumerate(el) if e is cur), None)
        self.selected = max(0, n - 1) if i is None else i
        return True

    def change_tab(self, i):
        i %= len(TABS)
        if i != self.tab: self.tab = i; self.reload()

    # ---- case « Favoris seulement » : son etat est un reglage (historique_favoris_seuls), garde d'une session a l'autre
    def _read_filter(self):
        try: return self.J.reg['historique_favoris_seuls'] is True
        except Exception: return False

    def _write_filter(self, on):
        """Enregistre l'etat de la case dans les reglages (reglages.json, tout de suite : une fermeture brutale ne le perd pas). Une erreur n'empeche jamais de cocher ou de decocher."""
        try: reg = self.J.reg; reg['historique_favoris_seuls'] = bool(on); reg.store()
        except Exception: pass

    def toggle_filter(self):
        """Coche ou decoche « Favoris seulement » (valable pour les deux onglets, enregistre dans les reglages). L'element choisi, s'il est dans la nouvelle liste, reste choisi (et la vue se recentre sur lui) ; sinon on se place sur le plus recent."""
        cur = self.current_item(); lookup_key = cur.lookup_key() if cur is not None else None
        self.favorites_only = not self.favorites_only; self._write_filter(self.favorites_only); self.reload()
        if lookup_key is not None:
            for i in range(len(self.elements) - 1, -1, -1):
                if self.elements[i].lookup_key() == lookup_key: self.go_to(i); break
        return self.favorites_only

    def current_item(self):
        return self.elements[self.selected] if 0 <= self.selected < len(self.elements) else None

    def star(self, i=None):
        """Met en favori (ou retire des favoris) l'element i (l'element actif par defaut) ; -> True si c'est maintenant un favori. Avec « Favoris seulement », l'element retire disparait de la liste (la vue reste ou elle est)."""
        h = getattr(self.J, 'history', None)
        if h is None: return False
        e = self.current_item() if i is None else (self.elements[i] if 0 <= i < len(self.elements) else None)
        if e is None: return False
        r = h.toggle_favorite(e)
        if self.favorites_only: self.reload(keep=True)
        return r

    # ---- defilement continu (aucune page, aucun cran : la position est un nombre de pixels)
    def span(self):
        """Distance (pixels) dont la vue peut monter depuis le bas : 0 quand toute la liste tient dans la fenetre."""
        return max(0.0, self.hc - self.hv)

    def scroll_offset(self):
        """Decalage reel de la vue (pixels) : la position bornee a la plage de defilement."""
        return min(max(self.pos, 0.0), self.span())

    def page_px(self): return max(self.step, self.hv - 2 * self.step)

    def _visible_elements(self, fully_visible_only):
        n = len(self.elements)
        if not n or len(self.starts) != n: return []
        return visible_elements(self.starts, self.ends, self.hc, self.hv, self.scroll_offset(), fully_visible_only)

    def _bring_into_view(self, fully_visible_only=False):
        """Le message choisi doit etre dans la fenetre : sinon (la liste a defile sans lui : molette, barre, glissement, page), c'est le plus proche message visible (le premier s'il est au-dessus de la fenetre, le dernier s'il est
        en dessous). `fully_visible_only` : seuls comptent les messages entierement visibles (a defaut, ceux qui le sont en partie). -> True si le message choisi a change."""
        v = self._visible_elements(fully_visible_only) or (self._visible_elements(False) if fully_visible_only else [])
        if not v or self.selected in v: return False
        self.selected = v[0] if self.selected < v[0] else v[-1]; return True

    def _show(self, i):
        """Defile du minimum pour montrer le message i en entier (rien si la liste n'est pas encore mesuree : la vue se placera des qu'elle le sera)."""
        if len(self.starts) != len(self.elements): self.center_target = i; return
        self.pos = offset_to_see(self.starts, self.ends, self.hc, self.hv, self.scroll_offset(), i)

    def move_by(self, d):
        """Haut / bas : le message d rangs plus loin (negatif : plus ancien, vers le haut de l'ecran), borne a la liste ; la vue defile seulement si ce message n'est pas entierement visible, du minimum necessaire. Repete par Pause.maj tant que la touche est maintenue."""
        n = len(self.elements)
        if not n: return
        if not self._bring_into_view(): self.selected = max(0, min(n - 1, self.selected + int(d)))          # (un message choisi sorti de la fenetre par la molette ou la barre : cet appui le remplace par le plus proche message visible, sans avancer d'un rang de plus)
        self._show(self.selected)

    def page(self, d):
        """Page precedente (d negatif) / suivante : la vue defile de la hauteur de la fenetre moins deux lignes ; le message choisi, s'il sort de la fenetre, devient le plus proche message entierement visible."""
        self.pos = min(self.span(), max(0.0, self.scroll_offset() - d * self.page_px())); self._bring_into_view(True)

    def to_top(self):
        if self.elements: self.selected = 0; self.pos = self.span()
    def to_bottom(self):
        if self.elements: self.selected = len(self.elements) - 1; self.pos = 0.0

    def scroll_by(self, px):
        """Souris (molette, barre, glissement) : la vue monte de `px` pixels vers les anciens (positif) ou descend vers les recents (negatif), bornee a la plage de defilement."""
        self.pos = min(self.span(), max(0.0, self.scroll_offset() + px))

    def go_to(self, i):
        """Choisit l'element i ; la vue se recentre sur lui des que la liste est mesuree (dessin suivant)."""
        n = len(self.elements)
        if not n: return
        self.selected = max(0, min(n - 1, i)); self.center_target = self.selected

    # ---- entrees
    def key_press(self, symbol, modifiers=0):
        K = pyglet.window.key; P = self.P; action = self.J.reg.action_of(symbol)
        P.mouse_mode = False
        if symbol in (K.ESCAPE, K.BACKSPACE) or action == 'B': P.back(); return True
        if action == 'historique':                                               # la touche qui ouvre l'historique : Dialogues -> Combats -> ferme tout
            suite = next_key(self.tab)
            if suite is None: P.shutdown()
            else: self.change_tab(suite)
            return True
        if symbol == K.UP or action == 'haut': self.move_by(-1); P._repeat(symbol, 'v', -1)
        elif symbol == K.DOWN or action == 'bas': self.move_by(1); P._repeat(symbol, 'v', 1)
        elif symbol == K.PAGEUP or action == 'L': self.page(-1)
        elif symbol == K.PAGEDOWN or action == 'R': self.page(1)
        elif symbol == K.HOME: self.to_top()
        elif symbol == K.END: self.to_bottom()
        elif symbol == K.LEFT or action == 'gauche': self.change_tab(self.tab - 1)
        elif symbol == K.RIGHT or action == 'droite': self.change_tab(self.tab + 1)
        elif symbol == K.F or action == 'carte': self.toggle_filter()                          # (F, ou la touche Carte : « Favoris seulement »)
        elif symbol in (K.RETURN, K.ENTER) or action in ('menu', 'A'): self.star()
        return True

    def wheel(self, sy):
        """Un cran de molette = WHEEL_STEP lignes de texte, vers les anciens quand on remonte la molette (un pas fin et constant ; proportionnel au mouvement pour les pavés tactiles)."""
        self.P.mouse_mode = True
        self.scroll_by(max(-5.0, min(5.0, float(sy))) * WHEEL_STEP * self.step)

    def hovered(self, x, y):
        P = self.P; p = P.mouse_pos; P.mouse_pos = (x, y)
        if p is None or abs(x - p[0]) + abs(y - p[1]) < 3: return
        P.mouse_mode = True

    @staticmethod
    def _inside(z, x, y): return z is not None and z[0] <= x <= z[2] and z[1] <= y <= z[3]

    def click(self, x, y, button):
        M = pyglet.window.mouse; P = self.P
        P.mouse_mode = True; P.mouse_pos = (x, y)
        if button == M.RIGHT: P.back(); return
        if self._inside(self.zone_ret, x, y): P.back(); return
        for z in self.tab_zones:
            if self._inside(z, x, y): self.change_tab(z[4]); return
        if self._inside(self.filter_zone, x, y): self.toggle_filter(); return
        b = self.barre
        if b and b['x0'] <= x <= b['x1'] and b['y0'] <= y <= b['y1']:
            if y > b['ptop']: self.scroll_by(self.step)                                 # fleche du haut : une ligne vers les anciens
            elif y < b['pbot']: self.scroll_by(-self.step)
            elif b['pouce'][0] <= y <= b['pouce'][1]: self.dragging_bar = b['pouce'][1] - y
            elif y > b['pouce'][1]: self.scroll_by(self.page_px())                       # piste au-dessus du curseur : une page vers les anciens
            else: self.scroll_by(-self.page_px())
            return
        for z in self.star_zones:
            if self._inside(z, x, y): self.selected = z[4]; self.star(z[4]); return
        for (x0, y0, x1, y1, i) in self.zones:
            if x0 <= x <= x1 and y0 <= y <= y1: self.selected = i; break
        self.drag = [y, self.scroll_offset(), False]

    def release(self, x, y, button):
        self.dragging_bar = None; self.drag = None

    def drag_to(self, x, y):
        b = self.barre
        if self.dragging_bar is not None:
            if not b: self.dragging_bar = None; return
            free = b['ptop'] - b['pbot'] - b['th']
            if free > 0:
                from_top = max(0.0, min(1.0, (b['ptop'] - (y + self.dragging_bar)) / free)) * (b['n'] - b['vis'])      # le curseur de la barre donne la distance depuis le haut du contenu
                self.pos = min(self.span(), max(0.0, self.span() - from_top))
            return
        d = self.drag
        if d is None: return
        if not d[2] and abs(y - d[0]) < DRAG_TOLERANCE: return
        d[2] = True
        self.pos = min(self.span(), max(0.0, d[1] + (d[0] - y)))                    # le contenu suit le pointeur, pixel par pixel (le pointeur descend : la liste descend, on remonte vers les plus anciens)

    # ---- dessin
    def _bm(self):
        r = getattr(self.J, 'ui_render', None)
        return r.texts.bitmap if r is not None and getattr(r, 'texts', None) is not None else None

    def _bmm(self):
        """Police des messages du jeu (celle du canevas de texte du moteur : tous les glyphes du jeu, avec ses regles de placement et de coupure) pour le texte des boites ; None si elle n'a pas ete extraite (on garde SE-GARRIR)."""
        r = getattr(self.J, 'ui_render', None); t = getattr(r, 'texts', None) if r is not None else None
        return getattr(t, 'messages', None)

    def _text_width(self, bm, text, sc, size_value):
        if bm: return bm.width_px(normal_spaces(bm, text)) * sc
        return self.P._label(text, size_value).content_width

    def _line(self, bm, text, x, ybase, sc, clr, size_value):
        """Une ligne de texte dont la ligne de base est en ybase : police bitmap du jeu (une texture par ligne, teintee), sinon police du systeme."""
        if not text.strip(): return
        if bm:
            text = normal_spaces(bm, text); tex, w, h, base = bm.line(text)
            lookup_key = (text, clr); sp = self._spr.get(lookup_key)
            if sp is None or sp.image is not tex:
                if len(self._spr) > 600: self._spr.clear()
                sp = self._spr[lookup_key] = pyglet.sprite.Sprite(tex); sp.color = clr[:3]
            sp.update(x=x - bm.PAD * sc, y=ybase - (h - base) * sc, scale=sc); sp.draw()
        else:
            label = self.P._label(text, size_value, tuple(clr) + (255,)); label.x = x; label.y = ybase; label.draw()

    def _game_box(self):
        """Boite de dialogue standard (dimensions de la mise en page d'origine si elle est chargee) ; gardee."""
        r = getattr(self.J, 'ui_render', None); ml = getattr(r, 'ml', None)
        if self._box is None or self._box_layout is not ml: self._box = Box.from_ml(ml) if ml is not None else Box(); self._box_layout = ml
        return self._box

    def _pages_of(self, bm, e, B, s, size_value):
        """Pages d'un element : liste de listes de rangees de texte (3 rangees au plus, l'entete d'un combat comprise). Gardees (cle : element, echelle)."""
        lookup_key = (e.n, e.type, int(s * 100))
        r = self._lines.get(lookup_key)
        if r is None:
            if len(self._lines) > 4000: self._lines.clear()
            if bm: mes = lambda t: bm.width_px(normal_spaces(bm, t)) * B.text_scale
            else: mes = lambda t: self.P._label(t, size_value).content_width * 0.9 / s
            battle = e.type == HI.BATTLE_TYPE
            r = self._lines[lookup_key] = paginate(rows_of(e, mes, B.text_width(), self._bmm()), battle, MAX_BATTLE_LINES if battle else B.LINES)
        return r

    def _star(self, cx, cy, radius, solid):
        """Etoile de favori : doree quand l'element est en favori, grise et creuse sinon."""
        if solid:
            pyglet.shapes.Star(cx, cy, radius, radius * 0.45, 5, rotation=0, color=STAR + (255,)).draw()
        else:
            pyglet.shapes.Star(cx, cy, radius, radius * 0.45, 5, rotation=0, color=GRAY + (255,)).draw()
            pyglet.shapes.Star(cx, cy, radius * 0.6, radius * 0.27, 5, rotation=0, color=EMPTY_STAR + (255,)).draw()

    def _filter_width(self, bm, sc, size_value, k):
        """Largeur de la plaque de la case « Favoris seulement » : marge, case, marge, petite etoile, libelle, marge."""
        return 14 * k + 18 * k + 9 * k + 2 * 8 * k + 7 * k + self._text_width(bm, tr(FILTER_CAPTION), sc, size_value) + 14 * k

    def _filter(self, bm, sc, size_value, asc, k, fx, ty, th):
        """Case a cocher « Favoris seulement » : une plaque a la hauteur des onglets, a droite du dernier onglet (le groupe onglets + case est centre dans la fenetre), avec la case, une petite etoile et le libelle ;
        doree quand elle est cochee. Sa zone (clic) est gardee dans `filter_zone`."""
        P = self.P; cb = 18 * k; rs = 8 * k
        fw = self._filter_width(bm, sc, size_value, k)
        zone = (fx, ty, fx + fw, ty + th); self.filter_zone = zone
        over = (P._hovered(zone) if hasattr(P, '_hovered') else False) and P.mouse_mode
        self._plate(fx, ty, fw, th, k, over)
        on = self.favorites_only; clr = GOLD if on else WHITE
        bx, by = fx + 14 * k, ty + (th - cb) / 2
        pyglet.shapes.Rectangle(bx, by, cb, cb, color=(0, 0, 0)).draw()
        for (xa, ya, xb, yb) in ((bx, by, bx + cb, by), (bx, by + cb, bx + cb, by + cb), (bx, by, bx, by + cb), (bx + cb, by, bx + cb, by + cb)):
            pyglet.shapes.Line(xa, ya, xb, yb, thickness=max(1.5, 1.6 * k), color=clr + (255,)).draw()
        if on:                                                                      # la coche (deux traits)
            pyglet.shapes.Line(bx + cb * 0.2, by + cb * 0.5, bx + cb * 0.42, by + cb * 0.22, thickness=max(2.0, 2.6 * k), color=GOLD + (255,)).draw()
            pyglet.shapes.Line(bx + cb * 0.42, by + cb * 0.22, bx + cb * 0.84, by + cb * 0.82, thickness=max(2.0, 2.6 * k), color=GOLD + (255,)).draw()
        ex = bx + cb + 9 * k + rs; ey = ty + th / 2
        pyglet.shapes.Star(ex, ey, rs * 1.15, rs * 0.5, 5, rotation=0, color=(STAR if on else GRAY) + (255,)).draw()
        self._line(bm, tr(FILTER_CAPTION), ex + rs + 7 * k, ty + th / 2 - (asc * 0.37 if bm else 6 * k), sc, clr, size_value)

    def _plate(self, x, y, w, h, k, chosen):
        J = self.J; r = getattr(J, 'ui_render', None)
        if r is not None and r.plate(x, y, w, h, (J.width, J.height), chosen, corner=14 * k): return
        HM.plate(x, y, w, h, k, chosen, None)

    def _box_window(self, has_tab, extra=0):
        """Fenetre de message du jeu (ui_menu.MessageWindow) qui dessine le cadre d'une boite : avec l'onglet du nom (frameData 191) ou sans (192), sans le canevas ni le curseur de fin de page ; None si la mise en page
        d'origine n'est pas chargee (la boite est alors dessinee avec un cadre simple). `extra` : lignes de texte en plus des 3 de la boite du jeu (un combat) : le cadre (sans onglet) est allonge d'autant (stretch_border)."""
        lookup_key = (has_tab, int(extra) if not has_tab else 0)
        f = self._wins.get(lookup_key)
        if f is None:
            f = False
            r = getattr(self.J, 'ui_render', None); ml = getattr(r, 'ml', None)
            if ml is not None and getattr(ml, 'message', None):
                try:
                    g = UM.MessageWindow(ml); g.select_language(0, 0, False, 'x' if has_tab else '')
                    if g.with_name == has_tab:
                        g.N['canevas']['act'] = False; g.N['curseur']['act'] = False; f = g
                        if lookup_key[1] > 0: g.N['cadre']['vtx'] = stretch_border(g.N['cadre']['vtx'], lookup_key[1] * Box.STEP)
                except Exception: f = False
            self._wins[lookup_key] = f
        return f or None

    def _draw_box(self, B, bx, by, s, k, name_str, bm, size_value, extra=0):
        """Cadre de la boite dont le coin bas gauche est (bx, by), a l'echelle s : le cadre du jeu (et l'onglet du nom avec son texte, comme le jeu les pose), sinon un cadre simple. Toujours le meme : le message choisi n'est ni
        grise ni eclairci (il porte seulement la petite fleche, voir dessiner)."""
        J = self.J; r = getattr(J, 'ui_render', None); f = self._box_window(bool(name_str), extra) if r is not None else None
        done = False
        if f is not None:
            try:
                if name_str: f.N['qui']['text']['text'] = name_str
                r.draw_all([f], bx - (B.win[0] + B.x0) * s, by - (B.win[2] + B.z0) * s, s, (J.width, J.height)); done = True
            except Exception: self._wins[(bool(name_str), int(extra) if not name_str else 0)] = False
        if not done:                                                      # (repli : cadre noir translucide du menu et, pour un nom, un petit cadre collé en haut a gauche)
            HM.border(bx + 4 * s, by + 4 * s, (B.WIDTH - 8) * s, (B.UP + extra * B.STEP - 8) * s, k, background=(0, 0, 0), opacity=HM.GAME_OPACITY)
            if name_str:
                HM.border(bx + 4 * s, by + (B.UP + extra * B.STEP - 6) * s, (B.TAB_L - 8) * s, (B.TAB_H + 2) * s, k, background=(0, 0, 0), opacity=HM.GAME_OPACITY)
                sc = s * B.text_scale if bm else 1.0; lw = self._text_width(bm, name_str, sc, size_value)
                self._line(bm, name_str, bx + (B.NAME_X - 0.0) * s - lw / 2, by + (B.UP + extra * B.STEP + 7) * s, sc, WHITE, size_value)

    def _measure(self, bm, B, s, k, size_value, hv):
        """Pose TOUTE la liste dans une colonne (disposer : un dialogue a la hauteur de la boite de dialogue du jeu, que le texte tienne sur 1, 2 ou 3 rangees, et l'onglet du nom, sur la premiere boite d'un
        dialogue avec nom, s'y ajoute au-dessus ; un combat a autant de lignes que son texte en demande, trois au moins : box_lines), pour l'echelle s et une fenetre de liste de hauteur hv (pixels). La mise en page ne depend jamais de la position de defilement. Met a jour la geometrie du defilement (hauteur du contenu,
        de la fenetre, d'une ligne), garde la position proportionnelle quand l'echelle change, ramene au milieu l'element demande par `go_to`, borne la position et garde les bords des elements (debuts, fins) pour la navigation
        au clavier. -> boites : (element, boite, nombre de boites, haut, haut de l'onglet, haut du cadre, rangees de texte) ; haut = pixels depuis le haut du contenu."""
        els = self.elements; n = len(els)
        lookup_key = (id(els), n, int(s * 100), int(k * 100), bm is not None, self._bmm() is not None)
        if self._layout is None or self._layout[0] != lookup_key:
            pages = [self._pages_of(bm, e, B, s, size_value) for e in els]
            ent = [(len(pg), e.type == HI.TYPE_DIALOGUE and bool(e.name_str), [B.top_for(box_lines(page, j == 0, e.type == HI.BATTLE_TYPE)) * s for j, page in enumerate(pg)]) for pg, e in zip(pages, els)]
            boxes, starts, ends, hc = arrange(ent, B.UP * s, B.TAB_H * s, ELEMENT_SPACING * k, PAGE_SPACING * k, ENTRIES_MARGIN * k)
            self._layout = (lookup_key, [(i, p, num, h, hn, hb, pages[i][p]) for (i, p, num, h, hn, hb) in boxes], starts, ends, hc)
        boxes, starts, ends, hc = self._layout[1:]
        self._geometry(starts, ends, hc, hv, B.STEP * s, s)
        return boxes

    def _geometry(self, starts, ends, hc, hv, step, s):
        """Partie pure de _mesurer (testee sans police ni GL) : la liste fait `hc` pixels de haut (debuts / fins : haut de la premiere boite et bas de la derniere de chaque element), la fenetre de la liste `hv`, une ligne de texte `step`,
        a l'echelle s. Garde la position proportionnelle quand l'echelle change, ramene au milieu l'element demande par `go_to`, borne la position et garde les bords des elements pour la navigation au clavier."""
        n = len(starts)
        if self._prev_s and abs(s - self._prev_s) > 1e-6: self.pos *= s / self._prev_s                 # fenetre redimensionnee : la vue reste au meme endroit de la liste
        self._prev_s = s; self.hc, self.hv, self.step = hc, float(hv), step
        if self.center_target is not None:
            i, self.center_target = self.center_target, None
            if 0 <= i < n: self.pos = min(self.span(), max(0.0, hc - (starts[i] + ends[i]) / 2.0 - self.hv / 2.0)); self.selected = i
        self.starts, self.ends = list(starts), list(ends)
        self.pos = min(self.span(), max(0.0, self.pos))
        self.selected = max(0, min(n - 1, self.selected)) if n else 0

    def _slice(self, x, y, w, h):
        """Cadre de decoupe (glScissor) sur le rectangle (x, y, w, h) de la fenetre (pixels de la fenetre : mis a l'echelle du tampon d'image sur un ecran a forte densite) : ce qui deborde de la liste est coupe, comme un texte qui defile.
        -> True si le cadre est actif (a fermer par glDisable(GL_SCISSOR_TEST)) ; False si on n'a pas pu l'installer (les boites coupees ne sont alors pas dessinees)."""
        try:
            W, H = self.J.width, self.J.height; fb = self.J.get_framebuffer_size() if hasattr(self.J, 'get_framebuffer_size') else (W, H)
            rx, ry = fb[0] / float(max(1, W)), fb[1] / float(max(1, H))
            gl.glEnable(gl.GL_SCISSOR_TEST); gl.glScissor(int(max(0, x * rx)), int(max(0, y * ry)), int(max(1, round(w * rx))), int(max(1, round(h * ry))))
            return True
        except Exception:
            return False

    def draw_all(self):
        J = self.J; P = self.P; W, H = J.width, J.height; k = max(0.75, H / 900.0)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        veil = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); veil.opacity = 90; veil.draw()
        bm = self._bm(); B = self._game_box(); s = B.scale_factor(H, W, k)                      # s : pixels par unite d'interface = ceux d'une boite de dialogue du jeu
        su = max(0.8, min(2.4, H / 700.0)) if bm else 1.0; size_value = 17 * k                  # su : un pixel de police du jeu = su pixels d'ecran (titre, onglets, aide) ; taille : police du systeme (repli)
        sc = s * B.text_scale if bm else 1.0; size_b = 20 * s                               # idem pour le texte des boites : comme dans le jeu (1,105 unite par pixel de police)
        fm = self._bmm()                                                                       # texte des boites : la police des messages du jeu quand elle est la (un pixel de son canevas = une unite d'interface), sinon SE-GARRIR
        if fm is not None: sc = s * fm.SCALE; text_baseline = B.base_msg
        else: fm = bm; text_baseline = B.base
        asc = (bm.ascent * su) if bm else 18 * k
        kb = 1.1 * k; bw, bh = 64 * kb, 55.5 * kb
        lgs = [self._text_width(bm, tr(name_str), su, size_value) + 44 * k for name_str, _ in TABS]; tw = max(lgs + [120 * k]); gap = 10 * k
        tabs_width = tw * len(TABS) + gap * (len(TABS) - 1); fw = self._filter_width(bm, su, size_value, k)
        line_width = tabs_width + 14 * k + fw                                                       # la ligne des onglets : les onglets puis la case « Favoris seulement »
        pw = min(W - 20 * k, max(B.WIDTH * s + B.MARGINS * k, line_width + 2 * 34 * k)); h = H - 2 * 30 * k - bh - 10 * k
        x0 = (W - pw) / 2; y1 = (H + h + bh + 10 * k) / 2; y0 = y1 - h
        HM.border(x0, y0, pw, h, k, background=(0, 0, 0), opacity=HM.GAME_OPACITY)                # aussi transparent que les autres fenetres du jeu
        title_screen = tr('Historique')
        wt = self._text_width(bm, title_screen, su * 1.25, size_value * 1.3)
        self._line(bm, title_screen, x0 + (pw - wt) / 2, y1 - 24 * k - asc * 1.25, su * 1.25, WHITE, size_value * 1.3)
        # onglets (plaques du jeu : l'onglet ouvert est la plaque « choisie »)
        th = 34 * k; ty = y1 - 100 * k; self.tab_zones = []                      # (sous le titre : ses plaques ne doivent pas le recouvrir)
        tx = x0 + (pw - line_width) / 2
        for i, (name_str, lookup_key) in enumerate(TABS):
            zx = tx + i * (tw + gap); zone = (zx, ty, zx + tw, ty + th); self.tab_zones.append(zone + (i,))
            over = (P._hovered(zone) if hasattr(P, '_hovered') else False) and P.mouse_mode
            self._plate(zx, ty, tw, th, k, i == self.tab or over)
            name_str = tr(name_str); lf = self._text_width(bm, name_str, su, size_value); self._line(bm, name_str, zx + (tw - lf) / 2, ty + th / 2 - (asc * 0.37 if bm else 6 * k), su, GOLD if i == self.tab else WHITE, size_value)
        self._filter(bm, su, size_value, asc, k, tx + tabs_width + 14 * k, ty, th)                  # case « Favoris seulement » (a droite des onglets)
        # aide (une ou deux lignes, selon la largeur de la fenetre)
        ks = (J.reg['touches'].get('historique') or [None])[0] if hasattr(J.reg, '__getitem__') else None
        kn = RG.key_name(ks) if ks else None
        helptext = [tr('Haut / Bas : message précédent / suivant'), tr('Molette : défiler'), tr('Gauche / Droite : onglet'), tr('Entrée : favori ★'), tr('F : favoris seulement')] + ([tr('%s : suite') % tr(kn)] if kn else []) + [tr('Échap : fermer')]
        max_line_width = pw - 24 * k; measure_help = lambda t: self._text_width(bm, t, su * 0.72, size_value * 0.72)
        help_lines = []; cur = ''
        for a in helptext:
            cand = a if not cur else cur + '     ' + a
            if cur and measure_help(cand) > max_line_width: help_lines.append(cur); cur = a
            else: cur = cand
        help_lines.append(cur)
        helptext_step = (bm.leading * su * 0.72) if bm else 17 * k
        # zone de la liste : la boite (taille du jeu) a gauche, la colonne de l'etoile a sa droite, la barre de defilement au bord
        group = B.WIDTH * s + 44 * k; lx0 = x0 + (pw - group) / 2; lx1 = lx0 + group; ly1 = ty - 14 * k; ly0 = y0 + 40 * k + (len(help_lines) - 1) * helptext_step
        self.zones = []; self.star_zones = []; self.barre = None
        n = len(self.elements)
        if not n:
            self.hc = self.hv = 0.0; self.pos = 0.0; self._layout = None
            msg = tr((EMPTY_FAVORITES if self.favorites_only else EMPTY_MESSAGES)[TABS[self.tab][1]])
            vl = wrap_words(msg, lambda t: self._text_width(bm, t, su, size_value), pw - 40 * k)                 # le message tient dans la fenetre : coupe en plusieurs lignes, centrees (il debordait du cadre quand il etait long)
            step_v = (bm.leading * su) if bm else 28 * k; y_v = (ly0 + ly1) / 2 + (len(vl) - 1) * step_v / 2
            for j, l in enumerate(vl): self._line(bm, l, x0 + (pw - self._text_width(bm, l, su, size_value)) / 2, y_v - j * step_v, su, GRAY, size_value)
        else:
            mouse = P.mouse_mode; hv = ly1 - ly0
            boxes = self._measure(bm, B, s, k, size_b, hv)
            screen_top = ly0 + self.hc - round(self.scroll_offset())                      # ordonnee du haut du contenu (position entiere : le texte garde le meme dessin a chaque position) ; le contenu est colle en bas quand il est plus court que la fenetre
            sliced = self._slice(x0, ly0, pw, hv)                              # tout ce qui deborde de la liste est coupe
            dragging = self.drag is not None and self.drag[2]
            try:
                views = []; top_of = {}
                for b in boxes:                                                    # seules les boites qui touchent la fenetre de la liste sont dessinees (de la plus ancienne, en haut, a la plus recente)
                    (i, p, np_, topmost, hn, hb, rows) = b; yb = screen_top - topmost - hn - hb; yt = yb + hb + hn
                    if yt <= ly0 or yb >= ly1 or (not sliced and (yb < ly0 or yt > ly1)): continue
                    views.append((b, yb, yt)); top_of[i] = min(top_of.get(i, p), p)       # (page la plus haute montree de chaque element : la fleche dorée n'y est dessinee qu'une fois)
                    if mouse and self.dragging_bar is None and not dragging and P._pointer_in((lx0, max(yb, ly0), lx1, min(yt, ly1))): self.selected = i      # a la souris, le message survole est le message choisi (choisi avant le dessin : une seule fleche)
                for ((i, p, np_, topmost, hn, hb, rows), yb, yt) in views:
                    e = self.elements[i]; name_str = e.name_str if (e.type == HI.TYPE_DIALOGUE and p == 0 and e.name_str) else None
                    zone = (lx0, max(yb, ly0), lx1, min(yt, ly1)); self.zones.append(zone + (i,))                      # (la zone d'une boite coupee ne depasse pas la fenetre de la liste : pas de clic sur les onglets ou l'aide)
                    extra = max(0, box_lines(rows, p == 0, e.type == HI.BATTLE_TYPE) - B.LINES)                # lignes en plus de la boite du jeu (un combat)
                    self._draw_box(B, lx0, yb, s, k, name_str, bm, size_b, extra)                      # cadre du jeu (+ onglet et nom) : aucun grisé au survol ni au choix
                    if i == self.selected and p == top_of[i]: P._cursor(x0 + 4 * k, yb + hb / 2, min(hb * 0.7, 28 * k))      # le message choisi (clavier ou souris) : la petite fleche, et rien d'autre
                    rank = 0
                    if e.type == HI.BATTLE_TYPE and p == 0:                                # entete : l'issue du combat a gauche, l'heure de jeu a droite
                        base = yb + hb - text_baseline(0) * s; self._line(fm, tr(HI.OUTCOME_CAPTION.get(e.outcome, '')), lx0 + B.TEXT_X * s, base, sc, GOLD, size_b)
                        ht = game_time(e.t); self._line(fm, ht, lx0 + (B.WIDTH - 14) * s - self._text_width(fm, ht, sc * 0.8, size_b * 0.8), base, sc * 0.8, HELPTEXT, size_b * 0.8); rank = 1
                    for l in rows:
                        self._line(fm, l, lx0 + B.TEXT_X * s, yb + hb - text_baseline(rank) * s, sc, WHITE, size_b); rank += 1
                    rs = 11 * k; ex = lx0 + B.WIDTH * s + 22 * k; ey = yb + hb - (B.BASE_1 - 7) * s     # etoile dans la colonne a droite de la boite, a la hauteur de la 1re ligne
                    z = (ex - rs * 1.3, max(ey - rs * 1.3, ly0), ex + rs * 1.3, min(ey + rs * 1.3, ly1))
                    if z[1] < z[3]: self.star_zones.append(z + (i,))
                    self._star(ex, ey, rs * (1.15 if (mouse and P._pointer_in(z)) else 1.0), e.fav is not None)
                    if np_ > 1:                                                          # « 1/2 » sous l'etoile : la boite fait partie d'une suite (simple etiquette)
                        t = '%d/%d' % (p + 1, np_); self._line(bm, t, ex - self._text_width(bm, t, su * 0.72, size_value * 0.72) / 2, ey - rs * 1.3 - 6 * k - (asc * 0.72 if bm else 12 * k), su * 0.72, HELPTEXT, size_value * 0.72)
            finally:
                if sliced: gl.glDisable(gl.GL_SCISSOR_TEST)
            if self.hc > self.hv + 0.5: self.barre = P._scroll_bar(x0 + pw - 14 * k, ly1, ly0, self.hc, self.hv, self.span() - self.scroll_offset(), k, self.dragging_bar is not None)      # curseur proportionnel, position continue (distance depuis le haut du contenu)
        for j, l in enumerate(help_lines):                                          # aide et bouton retour
            text_line_width = self._text_width(bm, l, su * 0.72, size_value * 0.72); self._line(bm, l, x0 + (pw - text_line_width) / 2, y0 + 14 * k + (len(help_lines) - 1 - j) * helptext_step, su * 0.72, HELPTEXT, size_value * 0.72)
        bx = x0 + pw - bw - 8 * k; by = y0 - 8 * k - bh; self.zone_ret = (bx, by, bx + bw, by + bh)
        P._back_button(bx, by, bw, bh, P._hovered(self.zone_ret))
