"""Historique : les dialogues dits a l'ecran (hors combat), les derniers combats et les favoris.

Trois morceaux :
- `Sensor` (crochets dans le moteur, installes par Engine.__init__) : le texte d'un message n'est connu qu'a un endroit, TextBuffer::cat (appelee une fois par page de message, macros resolues, avec le nom du
  locuteur donne par le moteur lui-meme : le « @a<nom>@b » des textes du patch, c'est-a-dire le nom que le jeu AFFICHE sur la fenetre de message). Le crochet note le texte, ce nom, l'heure de jeu
  (status::g_Game + 4, en 1/60 s) et si l'appel vient d'un combat (les messages de combat n'entrent pas dans l'historique des dialogues : le combat a le sien, battle_history.py).
- `History` (donnees pures, sans pyglet ni emulateur) : les dialogues et les combats de la SESSION (en memoire, ils disparaissent a la fermeture de la visionneuse) et les favoris (le seul element
  conserve : fichier JSON a cote de la visionneuse, jusqu'a ce que le joueur retire l'etoile).
- des fonctions pures : nettoyage du texte, coupure des lignes, mise en forme des combats.

Les favoris de dialogue gardent la CLE du message (son numero dans les fichiers du jeu, « b0802000#199 » : fichier = numero // 1000 x 1000, rang = reste), pas son texte : le texte est redemande au moteur du jeu au
lancement (TextAPI::extractText, voir `Sensor.model`), donc un message modifie dans le patch change aussi dans les favoris. Le numero est connu au crochet de ui_MsgAdd (le texte, lui, passe par TextBuffer::cat). La
liaison n'est faite que si le texte donne par les fichiers du jeu redonne EXACTEMENT ce que le joueur a lu (voir `binding` : page du message, variables du jeu « [NONE 1,0] » remplacees par les valeurs vues) ;
sinon (texte construit par le programme, pages decoupees autrement...) le favori garde son texte, comme avant.

Un dialogue est montre comme dans le jeu : une fenetre de message, avec le nom du locuteur dans un cartouche SEULEMENT si le jeu l'affichait au moment ou le dialogue a ete dit ; sinon le texte seul, tel que le jeu
l'ecrit (les paroles d'un personnage sans nom commencent par « *: » dans le patch FR : ce debut est garde). Aucun « qui a dit cela » ni « ou » n'est deduit.
"""
import json, os, re, struct, time
from dq4_pc.language import tr, N_

VERSION = 2                        # fichier des favoris (la version 1 etait l'ancien historique des messages par partie : abandonne)
MAX_DIALOGUES = 1000               # de la session : les plus anciens sortent
MAX_BATTLES = 200
MAX_FAVORITES = 500
MAX_TEXT = 1500                   # caracteres gardes d'un message
PAGE = '\u3221'                    # « ㈡ » : saut de page (nouvelle bulle) dans le texte d'un message des fichiers du jeu
RE_TOKEN = re.compile(r'\[[A-Z]+ [0-9, -]*\]')       # variable du jeu non resolue dans le texte d'un message des fichiers : « [NONE 1,0] » (le nom du heros, un nombre, un objet...)
MSG_ID_MAX = 1 << 24               # le genre du texte est range dans les bits 24 et plus de l'identifiant que prend TextAPI::extractText
SYM_UI_MSGADD = '_Z9ui_MsgAddib'   # ui_MsgAdd(int numero, bool) : le moteur ajoute un message (numero = cle dans les fichiers du jeu) ; il appelle TextBuffer::cat
SYM_EXTRACT = '_ZN7TextAPI11extractTextEPci'
WINDOW_WAIT = 180              # images : une page en attente est notee si la fenetre de message ne s'est jamais ouverte au bout de ce delai (3 s)
TIME_MARGIN = 120                      # 2 s de jeu (1/60 s) : deux messages identiques plus proches que cela sont un doublon
STORAGE_DELAY = 5.0         # secondes : les ecritures sont groupees (les favoris ne changent qu'a la main : on ecrit tout de suite, voir toggle_favorite)
PART_TOWN, PART_BATTLE, PART_FIELD = 0xc, 0xd, 0xe

KIND_NAME, KIND_GENERAL = 'n', 'g'                    # message avec un nom que le jeu affiche / sans nom
CATEGORY_TERRAIN, CATEGORY_BATTLE = 't', 'c'                      # message hors combat / de combat (jamais range dans les dialogues)
TYPE_DIALOGUE, BATTLE_TYPE = 'd', 'c'
MISSING = N_('(Message introuvable dans les fichiers du jeu : %s)')            # (traduit quand il remplace le texte d'un favori : voir History._resoudre)

ENTRIES_TYPE = {'dialogues': TYPE_DIALOGUE, 'combats': BATTLE_TYPE}              # liste de l'historique -> type de ses elements (History.liste, filtre « Favoris seulement »)
OUTCOMES = ('victoire', 'fuite', 'defaite')
OUTCOME_CAPTION = {'victoire': N_('Victoire'), 'fuite': N_('Fuite'), 'defaite': N_('Défaite')}            # (traduits par la fenetre au dessin : tr(OUTCOME_CAPTION[...]))


# ---------------------------------------------------------------------------------------------------------------------------------- elements
class Element:
    """Un element de l'historique : dialogue (type 'd' : nom affiche ou None, texte) ou combat (type 'c' : ennemis [{'nom', 'total', 'vaincus', 'fuis', 'disparus'}], or, xp, issue, objets [{'nom'}]).
    `n` : numero d'ordre (cle d'affichage), `t` : heure de jeu (1/60 s), `fav` : numero du favori correspondant (None : pas en favori)."""
    __slots__ = ('n', 'type', 't', 'name_str', 'text', 'enemies', 'gold', 'xp', 'outcome', 'fav', 'objects', 'mid', 'seg', 'val', 'linked', 'waiting')

    def __init__(self, n, type_, t, name_str=None, text='', enemies=None, gold=0, xp=0, outcome='victoire', fav=None, objects=None, mid=None, seg=None, val=None):
        self.n, self.type, self.t, self.name_str, self.text = n, type_, t, name_str, text
        self.enemies, self.gold, self.xp, self.outcome, self.fav = enemies or [], gold, xp, outcome, fav
        self.objects = objects or []
        self.mid, self.seg, self.val = mid, seg, val or {}      # dialogue : numero du message dans les fichiers du jeu (None : inconnu), page du message (None : message entier), valeurs des variables [NONE a,b]
        self.linked = False                                         # favori de dialogue range par la cle (le fichier ne garde pas le texte)
        self.waiting = False                                     # ... et dont le texte n'a pas encore ete redemande au moteur (voir History._resoudre)

    def lookup_key(self):
        """Ce qui fait l'identite d'un element (pour reconnaitre un doublon, ou un element deja en favori) : le contenu, pas le numero."""
        if self.type == TYPE_DIALOGUE: return (TYPE_DIALOGUE, self.name_str, self.text)
        return (BATTLE_TYPE, self.t, self.outcome, self.gold, self.xp, tuple((e['nom'], e['total'], e['vaincus'], e.get('fuis', 0), e.get('disparus', 0)) for e in self.enemies),
                tuple(o['nom'] for o in self.objects))

    def to_dict(self):
        if self.type == TYPE_DIALOGUE:
            if not self.linked: return {'k': TYPE_DIALOGUE, 'id': self.fav, 't': self.t, 'nom': self.name_str, 'texte': self.text}
            d = {'k': TYPE_DIALOGUE, 'id': self.fav, 't': self.t, 'nom': self.name_str, 'mid': self.mid}          # (aucun texte : il vient des fichiers du jeu)
            if self.seg is not None: d['s'] = self.seg
            if self.val: d['v'] = dict(self.val)
            return d
        return {'k': BATTLE_TYPE, 'id': self.fav, 't': self.t, 'ennemis': [dict(e) for e in self.enemies], 'or': self.gold, 'xp': self.xp, 'issue': self.outcome, 'objets': [dict(o) for o in self.objects]}

    @staticmethod
    def from_dict(d, n):
        """Element d'un favori lu dans le fichier ; None s'il n'est pas valide (le reste du fichier est garde)."""
        try:
            ident, t = d['id'], d['t']
            if isinstance(ident, bool) or not isinstance(ident, int) or ident < 1 or isinstance(t, bool) or not isinstance(t, int) or t < 0: return None
            if d['k'] == TYPE_DIALOGUE:
                name_str = d.get('nom')
                if not (name_str is None or isinstance(name_str, str)): return None
                name_str = (without_marks(name_str).strip()[:60] or None) if name_str else None
                if 'texte' in d:                                                               # favori qui garde son texte (avant #265, ou message que les fichiers du jeu ne redonnent pas tel quel)
                    text = d['texte']
                    if not isinstance(text, str) or not text.strip(): return None
                    return Element(n, TYPE_DIALOGUE, t, name_str, without_marks(text)[:MAX_TEXT], fav=ident)
                mid, seg, val = d.get('mid'), d.get('s'), d.get('v', {})                      # favori range par la cle : le texte sera redemande au moteur
                if not _is_integer(mid) or mid < 1 or mid >= MSG_ID_MAX or not (seg is None or (_is_integer(seg) and 0 <= seg < 1000)): return None
                if not isinstance(val, dict) or len(val) > 20 or any(not isinstance(k, str) or not isinstance(v, str) or len(k) > 40 or len(v) > 200 for k, v in val.items()): return None
                e = Element(n, TYPE_DIALOGUE, t, name_str, '', fav=ident, mid=mid, seg=seg, val=dict(val)); e.linked = e.waiting = True
                return e
            if d['k'] == BATTLE_TYPE:
                outcome, enemies = d['issue'], d['ennemis']
                if outcome not in OUTCOMES or not isinstance(enemies, list): return None
                es = valid_enemies(enemies)
                gain = [d.get('or', 0), d.get('xp', 0)]
                if es is None or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in gain): return None
                obj = valid_objects(d.get('objets', []))                                      # (les favoris d'avant le #141 n'ont ni fuis, ni disparus, ni objets)
                if obj is None: return None
                return Element(n, BATTLE_TYPE, t, enemies=es, gold=gain[0], xp=gain[1], outcome=outcome, fav=ident, objects=obj)
        except Exception:
            return None
        return None

    def __repr__(self): return 'Element(%r)' % (self.to_dict(),)


def _is_integer(x): return isinstance(x, int) and not isinstance(x, bool)


def valid_enemies(enemies):
    """Liste d'especes [{'nom', 'total', 'vaincus', 'fuis', 'disparus'}] verifiee et copiee (fuis et disparus : 0 s'ils manquent, comme dans les favoris d'avant le #141) ; None si elle n'est pas valide."""
    if not isinstance(enemies, list): return None
    es = []
    for e in enemies:
        if not isinstance(e, dict): return None
        name_str, tot, vai, fui, dis = e.get('nom'), e.get('total'), e.get('vaincus'), e.get('fuis', 0), e.get('disparus', 0)
        if not isinstance(name_str, str) or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in (tot, vai, fui, dis)): return None
        es.append({'nom': without_marks(name_str)[:60], 'total': tot, 'vaincus': vai, 'fuis': fui, 'disparus': dis})
    return es[:12]


def valid_objects(objects):
    """Liste d'objets gagnes [{'nom'}] verifiee et copiee ; None si elle n'est pas valide."""
    if not isinstance(objects, list): return None
    out = []
    for o in objects:
        if not isinstance(o, dict) or not isinstance(o.get('nom'), str): return None
        out.append({'nom': without_marks(o['nom']).strip()[:60]})
    return out[:8]


def without_marks(text):
    """Retire le « ; » du texte du patch : une marque de coupure placee juste apres une espace dans les noms d'objets (« bâton de ;cyprès », « l'herbe ;médicinale »), pas de la ponctuation (aucun « ; » de ponctuation
    dans les textes du patch ; voir docs/viewer-notes-dq4-pc.md, avance #148). L'espace qui la precede reste : « l'herbe médicinale »."""
    return text.replace(';', '')


def clean(text):
    """Texte tel que le jeu l'affiche : codes de couleur (@c0...) et caracteres de controle retires, espaces de fin retires, retours a la ligne gardes (jamais plus d'une ligne vide). Le « *: » du debut des paroles
    d'un personnage sans nom est GARDE (c'est le texte du jeu). Le « ; » (marque de coupure des noms d'objets du patch) est retire (#139)."""
    t = (text or '').replace('\r', '')
    t = re.sub(r'@c\d', '', t)
    t = without_marks(t)
    t = ''.join(ch for ch in t if ch == '\n' or (ch >= ' ' and not (0xe000 <= ord(ch) <= 0xf8ff) and ch != '\x7f'))
    t = '\n'.join(l.rstrip() for l in t.split('\n'))
    t = re.sub(r'\n{3,}', '\n\n', t).strip('\n ')
    return t[:MAX_TEXT]


def message_key(mid):
    """La cle d'un message comme on la cite pour le patch : fichier (numero // 1000 x 1000, 7 chiffres) # rang : 802199 -> « b0802000#199 »."""
    return 'b%07d#%d' % (mid // 1000 * 1000, mid % 1000)


def value_list(model, text):
    """Valeurs des variables du jeu (« [NONE 1,0] ») qui font du texte des fichiers `model` le texte lu `text` : {} si le modele n'a pas de variable (ou si le texte les montre telles quelles, comme les fichiers) et que
    les deux sont identiques ; {variable: valeur} si le texte se retrouve en remplacant chaque variable ; None si le modele ne redonne pas ce texte."""
    mod = clean(model)
    if mod == text: return {}
    tokens = RE_TOKEN.findall(mod)
    if not tokens: return None
    r = re.match('^' + '(.*?)'.join(re.escape(m) for m in RE_TOKEN.split(mod)) + '$', text, re.S)
    if r is None: return None
    vals = {}
    for j, v in zip(tokens, r.groups()):
        if vals.setdefault(j, v) != v: return None                                  # (la meme variable a deux valeurs : pas le meme message)
    return vals


def binding(raw_value, text):
    """Comment retrouver `text` (ce que le joueur a lu, nettoye) dans le texte des fichiers du jeu `raw_value` : (page, valeurs des variables), `page` = rang de la page du message (separees par ㈡) ou None pour le message
    entier ; None si aucune page ni le message entier ne redonne EXACTEMENT ce texte (alors on garde le texte du favori)."""
    attempts = [(None, raw_value)] + ([(i, p) for i, p in enumerate(raw_value.split(PAGE))] if PAGE in raw_value else [])
    for page, mod in attempts:
        v = value_list(mod, text)
        if v is not None: return page, v
    return None


def linked_text(raw_value, seg, val):
    """Texte d'un favori range par la cle : la page `seg` (None : tout le message) du texte des fichiers du jeu `raw_value`, variables remplacees par les valeurs gardees (une variable inconnue reste telle quelle). '' si `raw_value` manque
    ou n'a pas cette page."""
    if not raw_value: return ''
    if seg is not None:
        pages = raw_value.split(PAGE)
        if seg >= len(pages): return ''
        raw_value = pages[seg]
    t = RE_TOKEN.sub(lambda m: val.get(m.group(0), m.group(0)), clean(raw_value))
    return t.strip('\n ')[:MAX_TEXT]


def wrap_text(text, width_px, measure):
    """Coupe `text` en lignes de `width_px` au plus (mesure(chaine) -> largeur) : les retours a la ligne du texte sont gardes, la coupure se fait aux espaces (pas aux espaces insecables) ; un mot plus large que la ligne est coupe."""
    lines = []
    for para in text.split('\n'):
        if not para.strip(): lines.append(''); continue
        cur = ''
        for word in re.split(r' +', para):
            cand = word if not cur else cur + ' ' + word
            if cur and measure(cand) > width_px: lines.append(cur); cur = word
            else: cur = cand
            while measure(cur) > width_px and len(cur) > 1:                               # mot plus large que la ligne
                i = len(cur) - 1
                while i > 1 and measure(cur[:i]) > width_px: i -= 1
                lines.append(cur[:i]); cur = cur[i:]
        lines.append(cur)
    while lines and not lines[-1]: lines.pop()
    return lines or ['']


def plural(n, singular, plural_form):
    """« 1 vaincu », « 2 vaincus » : le modele du singulier ou du pluriel (`singular`, `plural_form` : textes a trous « %d vaincu » / « %d vaincus », N_ ; l'anglais n'a qu'une forme mais le garde en deux)."""
    return tr(singular if n < 2 else plural_form) % n


SPELLS = ((N_('%d vaincu'), N_('%d vaincus')), (N_('%d enfui'), N_('%d enfuis')), (N_('%d disparu'), N_('%d disparus')), (N_('%d resté'), N_('%d restés')))           # vaincus, enfuis, disparus, restes


def species_line(e):
    """Une espece d'ennemis, sur une ligne : « Gluant ×3 » quand tous sont vaincus (« Gluant » s'il n'y en avait qu'un), sinon le sort de chacun : « Gluant ×3 : 1 vaincu, 1 enfui, 1 disparu » ; ceux qui ne sont ni vaincus,
    ni enfuis, ni disparus sont encore la quand le combat se termine (le groupe a fui ou a ete vaincu) : « 2 restés »."""
    tot, vai, fui, dis = e['total'], e['vaincus'], e.get('fuis', 0), e.get('disparus', 0)
    base = '%s ×%d' % (e['nom'], tot) if tot > 1 else e['nom']
    if vai >= tot: return base
    remainder = max(0, tot - vai - fui - dis)
    if tot == 1: return (tr('%s : enfui') if fui else tr('%s : disparu') if dis else tr('%s : resté')) % base
    spells = [plural(n, *words) for n, words in zip((vai, fui, dis, remainder), SPELLS) if n > 0]
    return tr('%s : %s') % (base, ', '.join(spells))


def battle_lines(c):
    """Lignes de texte d'un combat (Element de type 'c'), une par rangee : une par espece d'ennemi (species_line : qui etait la, qui est vaincu, enfui, disparu ou reste), puis, pour une victoire, l'or et l'experience
    gagnes, puis les objets obtenus (« Objets : Herbe médicinale, Pierre de vie »). Rien n'est ecrit quand il n'y a pas eu d'objet."""
    out = [species_line(e) for e in c.enemies]
    if not out: out.append(tr('Ennemis inconnus'))
    if c.outcome == 'victoire':
        out.append(tr('Or : %d\u00a0\u00a0\u00a0\u00a0\u00a0Expérience : %d') % (c.gold, c.xp))          # (espaces insecables : la coupure des lignes ne les fait pas disparaitre)
        if c.objects: out.append(tr('Objets : %s') % ', '.join(o['nom'] for o in c.objects))
    return out


def battle_element(n, battle):
    """Element de type 'c' d'un dict de battle_history.BattleSensor.maj ; None si le dict est inexploitable."""
    try:
        outcome = battle['issue']
        if outcome not in OUTCOMES: return None
        es = [{'nom': str(e['nom'])[:60], 'total': int(e['total']), 'vaincus': int(e['vaincus']), 'fuis': int(e.get('fuis', 0)), 'disparus': int(e.get('disparus', 0))} for e in battle['ennemis']][:12]
        objects = [{'nom': without_marks(str(o['nom'])).strip()[:60]} for o in battle.get('objets', [])][:8]
        return Element(n, BATTLE_TYPE, int(battle['t']), enemies=es, gold=max(0, int(battle['or'])), xp=max(0, int(battle['xp'])), outcome=outcome, objects=objects)
    except Exception:
        return None


# ---------------------------------------------------------------------------------------------------------------------------------- donnees
class History:
    """Dialogues et combats de la session (en memoire) + favoris (fichier). Le fichier est a cote de la visionneuse (jamais dans le dossier des sauvegardes du jeu, que l'on ne modifie pas) :
    {"version": 2, "suivant": 7, "favoris": [{"k": "d", "id": 3, "t": 12345, "nom": "Alena", "texte": "..."}, {"k": "c", "id": 5, "t": 1, "ennemis": [...], "or": 3, "xp": 4, "issue": "victoire", "objets": [{"nom": "Herbe médicinale"}]}]}."""

    def __init__(self, path=None, clock=time.time):
        self.path = path; self.clock = clock
        self.dialogues = []                                 # Element 'd' de la session, du plus ancien au plus recent
        self.battles = []                                   # Element 'c' de la session
        self.favorites = []                                   # Element (d ou c) gardes dans le fichier, dans l'ordre ou ils ont ete mis en favori
        self.next_id = 1                                    # prochain numero de favori
        self._n = 0                                         # compteur des numeros d'ordre (dialogues, combats, favoris : jamais deux fois le meme)
        self._wait = []                                  # pages d'un message deja preparees par le moteur mais pas encore lues (voir _pages)
        self._feed = False; self._a_vu = False; self._n_att = 0       # curseur de fin de page de l'image precedente ; fenetre de message vue ouverte depuis la rafale ; images d'attente
        self._dirty = False; self._t_write = 0.0
        self.error = None
        self._cap = None; self._models = {}                # Capteur du moteur (une fois qu'il existe) ; texte des fichiers du jeu deja demande, par numero de message
        self.load()

    def _num(self):
        self._n += 1; return self._n

    # ---- fichier des favoris
    def load(self):
        """Lit le fichier des favoris. Un fichier illisible est mis de cote (.corrompu) et on repart de zero ; un favori invalide est ignore sans perdre les autres."""
        self.favorites = []; self.next_id = 1
        if not self.path or not os.path.exists(self.path): return
        try:
            with open(self.path, encoding='utf-8') as f: d = json.load(f)
            if not isinstance(d, dict) or d.get('version') != VERSION or not isinstance(d.get('favoris'), list): raise ValueError('format inconnu')
            seen = set()
            for x in d['favoris']:
                e = Element.from_dict(x, self._num()) if isinstance(x, dict) else None
                if e is not None and e.fav not in seen: seen.add(e.fav); self.favorites.append(e)
            self.favorites = self.favorites[-MAX_FAVORITES:]
            s = d.get('suivant')                                              # prochain numero enregistre : jamais un numero deja pris, ni un numero deja donne puis retire
            self.next_id = max([e.fav + 1 for e in self.favorites] + [s if isinstance(s, int) and not isinstance(s, bool) and s > 0 else 1])
        except Exception as ex:
            self.error = repr(ex); self.favorites = []; self.next_id = 1
            try: os.replace(self.path, self.path + '.corrompu')
            except Exception: pass
            print(tr("Favoris de l'historique illisibles (%s) : mis de cote, on repart de zero (%r)") % (self.path, ex), flush=True)

    def store(self, force=False):
        """Ecrit le fichier s'il a change (ecriture atomique : fichier temporaire puis remplacement). Les ecritures sont groupees : au plus une toutes les STORAGE_DELAY secondes, `force` pour la fermeture."""
        if not self.path or not self._dirty: return False
        now = self.clock()
        if not force and now - self._t_write < STORAGE_DELAY: return False
        self._t_write = now
        try:
            d = {'version': VERSION, 'suivant': self.next_id, 'favoris': [e.to_dict() for e in self.favorites]}
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
            tmp = self.path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
            os.replace(tmp, self.path); self._dirty = False
            return True
        except Exception as ex:
            self.error = repr(ex); print(tr("Favoris de l'historique non enregistres : %s") % (ex,), flush=True)
            return False

    # ---- listes
    def entries(self, tab, favorites_only=False):
        """Elements d'un onglet de l'historique, du plus ancien au plus recent : 'dialogues' ou 'combats' (et 'favoris' : tous les favoris, voir ci-dessous). `favorites_only` : l'option « Favoris seulement » de la fenetre -> seuls les
        favoris de cette sorte d'element (dialogues ou combats) : ceux du fichier, donc aussi ceux des sessions precedentes, dans l'ordre ou ils ont ete mis en favori (le plus recent en bas)."""
        if favorites_only and tab in ENTRIES_TYPE: return [f for f in self.favorites if f.type == ENTRIES_TYPE[tab]]
        return list({'dialogues': self.dialogues, 'combats': self.battles, 'favoris': self.favorites}.get(tab, ()))

    # ---- favoris
    def toggle_favorite(self, e):
        """Met l'element en favori (une copie est gardee dans le fichier, immediatement) ou le retire. Un element de la liste des favoris qu'on « desetoile » disparait de cette liste ; l'element de la session qui
        lui correspond perd son etoile. -> True si l'element est maintenant en favori."""
        if e is None: return False
        if e.fav is not None:
            self.remove_favorite(e.fav); return False
        if len(self.favorites) >= MAX_FAVORITES: del self.favorites[0]
        copied = Element(self._num(), e.type, e.t, e.name_str, e.text, [dict(x) for x in e.enemies], e.gold, e.xp, e.outcome, fav=self.next_id, objects=[dict(o) for o in e.objects], mid=e.mid)
        self._link(copied)
        e.fav = self.next_id; self.next_id += 1
        self.favorites.append(copied); self._dirty = True; self.store(True)
        return True

    def _model(self, mid):
        """Texte du message `mid` dans les fichiers du jeu (demande au moteur ; garde), ou None (pas de moteur, message inconnu)."""
        if mid in self._models: return self._models[mid]
        cap = self._cap
        if cap is None or not hasattr(cap, 'model'): return None
        try: raw_value = cap.model(mid)
        except Exception: raw_value = None
        self._models[mid] = raw_value
        return raw_value

    def _link(self, f):
        """Un favori de dialogue dont on connait la cle : si le texte des fichiers du jeu redonne EXACTEMENT le texte lu, le favori est range par la cle (le fichier ne gardera pas le texte) ; sinon il garde son texte."""
        if f.type != TYPE_DIALOGUE or not f.mid: return
        raw_value = self._model(f.mid)
        l = binding(raw_value, f.text) if raw_value else None
        if l is not None: f.seg, f.val = l; f.linked = True; f.waiting = False

    def _resolve(self):
        """Redemande au moteur le texte des favoris ranges par la cle (0,13 ms l'appel : les 500 favoris du fichier en 65 ms). Un message qui n'existe plus ou n'a plus cette page : une ligne le dit, avec la cle."""
        if self._cap is None: return
        for f in self.favorites:
            if not f.waiting: continue
            f.text = linked_text(self._model(f.mid), f.seg, f.val) or tr(MISSING) % message_key(f.mid)
            f.waiting = False; f.n = self._num()                                   # (nouveau numero : la mise en page gardee par la fenetre ne vaut plus)

    def refresh(self):
        """A l'ouverture de l'historique : les textes des favoris ranges par la cle sont redemandes au moteur. Les fichiers du jeu ne changent pas pendant que la visionneuse tourne, mais le moteur choisit certaines
        variantes d'un texte selon la partie en cours (le sexe du heros : « ma mignonne » / « mon chou ») : un favori montre donc le texte tel que la partie actuelle le donnerait."""
        self._models.clear()
        for f in self.favorites:
            if f.linked: f.waiting = True
        try: self._resolve()
        except Exception as ex: self.error = repr(ex); print(tr('Historique : texte des favoris non redemande (%r)') % (ex,), flush=True)

    def remove_favorite(self, ident):
        self.favorites = [f for f in self.favorites if f.fav != ident]
        for e in self.dialogues + self.battles:
            if e.fav == ident: e.fav = None
        self._dirty = True; self.store(True)

    # ---- ajout
    def add(self, text, name_str, t, mid=None):
        """Ajoute un dialogue de la session (texte brut du moteur, nom affiche par le jeu ou None, numero du message dans les fichiers du jeu ou None) ; -> l'Element, ou None (vide, doublon)."""
        text = clean(text)
        if not text: return None
        name_str = (without_marks(str(name_str)).strip()[:60] or None) if name_str else None
        e = Element(self._num(), TYPE_DIALOGUE, int(t), name_str, text, mid=mid if _is_integer(mid) and 0 < mid < MSG_ID_MAX else None)
        if self.dialogues:
            d = self.dialogues[-1]
            if d.lookup_key() == e.lookup_key() and abs(e.t - d.t) <= TIME_MARGIN: return None             # le moteur a reaffiche le message (page revenue, question reposee)
        self.dialogues.append(e)
        if len(self.dialogues) > MAX_DIALOGUES: del self.dialogues[:len(self.dialogues) - MAX_DIALOGUES]
        return e

    def add_battle(self, battle):
        """Ajoute un combat termine (dict de battle_history.BattleSensor.maj) ; -> l'Element, ou None."""
        e = battle_element(self._num(), battle)
        if e is None: return None
        self.battles.append(e)
        if len(self.battles) > MAX_BATTLES: del self.battles[:len(self.battles) - MAX_BATTLES]
        return e

    # ---- liaison avec le moteur
    def do_update(self, engine, objects=None, names=None):
        """Une fois par pas du moteur : range les messages notes par le Capteur (dialogues hors combat) et les combats termines (BattleSensor), et ecrit les favoris si besoin."""
        try:
            cap = getattr(engine, 'sensor', None)
            if cap is not None and cap.active:
                self._cap = cap
                game = engine.state.part in (PART_TOWN, PART_BATTLE, PART_FIELD)
                received_list = cap.drain()
                if not game: self._wait = []
                else: self._pages(engine, received_list)
            cc = getattr(engine, 'battle_sensor', None)
            if cc is not None:
                for c in cc.do_update(engine): self.add_battle(c)
            self._resolve()
            self.store()
        except Exception as ex:                                              # l'historique ne doit jamais arreter le jeu
            if self.error is None: print(tr('Historique : erreur (%r)') % (ex,), flush=True)
            self.error = repr(ex)

    def _store_record(self, r):
        if r['cat'] == CATEGORY_BATTLE: return                                    # les messages de combat n'entrent pas dans les dialogues
        self.add(r['texte'], r['val'] if r['genre'] == KIND_NAME else None, r['t'], r.get('mid'))

    def _release(self, n):
        """Range les `n` premieres pages en attente (toutes si n est None)."""
        k = len(self._wait) if n is None else min(n, len(self._wait))
        pages, self._wait = self._wait[:k], self._wait[k:]
        for r in pages: self._store_record(r)

    def _pages(self, engine, received_list):
        """Le moteur prepare TOUTES les pages d'un message d'un coup (plusieurs TextBuffer::cat dans la meme image, meme temps de jeu) : ne noter que celles que le joueur a lues, sinon l'historique
        montrerait la page suivante avant sa lecture. La premiere page est notee tout de suite ; chaque fois que le curseur de fin de page s'eteint (le joueur tourne la page, Engine.ui.msg['feed']) la suivante
        est notee ; tout ce qui reste est note quand la fenetre de message se ferme ou quand un nouveau message arrive. Les messages de combat (defilement automatique) ne sont jamais retenus."""
        msg = getattr(getattr(engine, 'ui', None), 'msg', None)
        feed = bool(msg.get('feed')) if isinstance(msg, dict) else False
        fell = self._feed and not feed; self._feed = feed
        visible = bool(getattr(engine, 'msg_visible', True))
        if received_list:
            self._release(None)                                      # nouveau message : le precedent est fini (ses pages restantes ont ete lues ou sautees)
            self._a_vu = visible; self._n_att = 0
            prev = None
            for r in received_list:
                lookup_key = (r['genre'], r['val'], r['cat'], r['carte'], r['t'])
                if prev is not None and lookup_key == prev and r['cat'] != CATEGORY_BATTLE: self._wait.append(r)                # page suivante du meme message
                else: self._store_record(r)
                prev = lookup_key
            return
        if not self._wait: return
        if visible: self._a_vu = True
        else: self._n_att += 1
        if (not visible and self._a_vu) or self._n_att > WINDOW_WAIT: self._release(None)      # la fenetre s'est fermee (ou ne s'est jamais ouverte) : le message est fini
        elif fell: self._release(1)


# ---------------------------------------------------------------------------------------------------------------------------------- crochets dans le moteur
class Sensor:
    """Crochet sur le moteur (Unicorn) : TextBuffer::cat, appelee une fois par page de message. Les messages notes attendent dans `output` jusqu'a ce que History.maj les prenne (chacun : texte, genre, val = nom que le
    jeu affiche ou None, cat, carte, t, mid = numero du message dans les fichiers du jeu ou None). Le numero vient d'un second crochet, sur ui_MsgAdd(numero, bool) : TextBuffer::cat y est appelee (la pile le montre) ;
    une page qui n'en vient pas (texte construit par le programme) n'a pas de numero. Une erreur dans un crochet ne doit jamais arreter le moteur."""

    def __init__(self, engine):
        self.active = False; self.output = []; self._mid = None; self._buffer = None
        self.m = engine; c = self.c = engine.core
        try:
            import unicorn
            self.g_game = c.export('_ZN6status6g_GameE'); category = c.export('_ZN10TextBuffer3catEPKcS1_')
            if not self.g_game or not category: return
            c.uc.hook_add(unicorn.UC_HOOK_CODE, self._cat, None, category, category)
            self.active = True
        except Exception as ex:
            print(tr('Historique : crochets non installes (%r)') % (ex,), flush=True)
            return
        try:
            add = c.export(SYM_UI_MSGADD)
            if add: c.uc.hook_add(unicorn.UC_HOOK_CODE, self._add, None, add, add)
        except Exception as ex:
            print(tr('Historique : numeros de message non captes (%r)') % (ex,), flush=True)

    def _add(self, uc, addr, size_value, _):
        """Entree de ui_MsgAdd : le numero du message (1er argument) que TextBuffer::cat va recevoir."""
        try: self._mid = uc.reg_read(self.c.XREG[0]) & 0xffffffff
        except Exception: self._mid = None

    def model(self, mid):
        """Texte du message `mid` tel que le moteur le tire des fichiers du jeu (TextAPI::extractText, genre 1 = message) : brut, avec les sauts de page « ㈡ » et les variables « [NONE 1,0] » ; None si le moteur n'en a pas.
        A appeler entre deux images (jamais depuis un crochet), comme les noms de battle_history."""
        try:
            c = self.c; f = c.export(SYM_EXTRACT)
            if not f or not isinstance(mid, int) or not 0 < mid < MSG_ID_MAX: return None
            if self._buffer is None: self._buffer = c.malloc(8192)
            c.mem_w(self._buffer, b'\0' * 16)
            c.call(f, self._buffer, (1 << 24) | mid, label='texte du message', timeout_s=10)
            t = c.read_cstr(self._buffer).decode('utf-8', 'replace')
            return t if t.strip() and not t.startswith('<ERR') else None
        except Exception:
            return None

    def time_and_key(self):
        """-> (temps de jeu en 1/60 s, identifiant de la partie) lus dans status::g_Game."""
        try:
            t, uid = struct.unpack('<2I', self.c.mem(self.g_game + 4, 8)); return t, uid
        except Exception:
            return None, 0

    def drain(self):
        s, self.output = self.output, []
        return s

    def _stack(self, uc, n=24):
        """Noms des fonctions de la pile d'appels (chaine des pointeurs de cadre), de l'appelante immediate vers la racine."""
        c = self.c; names = [c.where(uc.reg_read(c.XREG[30])).split('+')[0]]
        fp = uc.reg_read(c.XREG[29])
        for _ in range(n):
            try: nfp, nlr = struct.unpack('<QQ', c.mem(fp, 16))
            except Exception: break
            if not nfp or nfp <= fp: break
            names.append(c.where(nlr).split('+')[0]); fp = nfp
        return names

    def _cat(self, uc, addr, size_value, _):
        try:
            c = self.c; x1, x2 = uc.reg_read(c.XREG[1]), uc.reg_read(c.XREG[2])
            text = c.read_cstr(x1).decode('utf-8', 'replace') if x1 else ''
            if not text.strip(): return
            name_str = c.read_cstr(x2).decode('utf-8', 'replace').strip() if x2 else ''           # le nom que le jeu affiche sur la fenetre de message (vide : aucun)
            e = self.m.state
            stack = self._stack(uc)
            battle = e.part == PART_BATTLE or any('Battle' in s for s in stack)
            t, _u = self.time_and_key()
            mid = getattr(self, '_mid', None) if stack and stack[0] == SYM_UI_MSGADD else None            # (l'appelante immediate de TextBuffer::cat est ui_MsgAdd : le numero vient de cet appel)
            self.output.append({'texte': text, 'genre': KIND_NAME if name_str else KIND_GENERAL, 'val': name_str or None, 'cat': CATEGORY_BATTLE if battle else CATEGORY_TERRAIN,
                                'carte': 'monde' if e.part == PART_FIELD else e.game_map, 't': t or 0, 'mid': mid})
            if len(self.output) > 500: del self.output[:250]                      # (jamais vide faute de History.maj : on ne grossit pas sans fin)
        except Exception:
            pass
