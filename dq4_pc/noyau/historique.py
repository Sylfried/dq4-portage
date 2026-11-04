"""Historique : les dialogues dits a l'ecran (hors combat), les derniers combats et les favoris.

Trois morceaux :
- `Capteur` (crochets dans le moteur, installes par Moteur.__init__) : le texte d'un message n'est connu qu'a un endroit, TextBuffer::cat (appelee une fois par page de message, macros resolues, avec le nom du
  locuteur donne par le moteur lui-meme : le « @a<nom>@b » des textes du patch, c'est-a-dire le nom que le jeu AFFICHE sur la fenetre de message). Le crochet note le texte, ce nom, l'heure de jeu
  (status::g_Game + 4, en 1/60 s) et si l'appel vient d'un combat (les messages de combat n'entrent pas dans l'historique des dialogues : le combat a le sien, historique_combat.py).
- `Historique` (donnees pures, sans pyglet ni emulateur) : les dialogues et les combats de la SESSION (en memoire, ils disparaissent a la fermeture de la visionneuse) et les favoris (le seul element
  conserve : fichier JSON a cote de la visionneuse, jusqu'a ce que le joueur retire l'etoile).
- des fonctions pures : nettoyage du texte, coupure des lignes, mise en forme des combats.

Les favoris de dialogue gardent la CLE du message (son numero dans les fichiers du jeu, « b0802000#199 » : fichier = numero // 1000 x 1000, rang = reste), pas son texte : le texte est redemande au moteur du jeu au
lancement (TextAPI::extractText, voir `Capteur.modele`), donc un message modifie dans le patch change aussi dans les favoris. Le numero est connu au crochet de ui_MsgAdd (le texte, lui, passe par TextBuffer::cat). La
liaison n'est faite que si le texte donne par les fichiers du jeu redonne EXACTEMENT ce que le joueur a lu (voir `liaison` : page du message, variables du jeu « [NONE 1,0] » remplacees par les valeurs vues) ;
sinon (texte construit par le programme, pages decoupees autrement...) le favori garde son texte, comme avant.

Un dialogue est montre comme dans le jeu : une fenetre de message, avec le nom du locuteur dans un cartouche SEULEMENT si le jeu l'affichait au moment ou le dialogue a ete dit ; sinon le texte seul, tel que le jeu
l'ecrit (les paroles d'un personnage sans nom commencent par « *: » dans le patch FR : ce debut est garde). Aucun « qui a dit cela » ni « ou » n'est deduit.
"""
import json, os, re, struct, time

VERSION = 2                        # fichier des favoris (la version 1 etait l'ancien historique des messages par partie : abandonne)
MAX_DIALOGUES = 1000               # de la session : les plus anciens sortent
MAX_COMBATS = 200
MAX_FAVORIS = 500
MAX_TEXTE = 1500                   # caracteres gardes d'un message
PAGE = '\u3221'                    # « ㈡ » : saut de page (nouvelle bulle) dans le texte d'un message des fichiers du jeu
RE_JETON = re.compile(r'\[[A-Z]+ [0-9, -]*\]')       # variable du jeu non resolue dans le texte d'un message des fichiers : « [NONE 1,0] » (le nom du heros, un nombre, un objet...)
MSG_ID_MAX = 1 << 24               # le genre du texte est range dans les bits 24 et plus de l'identifiant que prend TextAPI::extractText
SYM_UI_MSGADD = '_Z9ui_MsgAddib'   # ui_MsgAdd(int numero, bool) : le moteur ajoute un message (numero = cle dans les fichiers du jeu) ; il appelle TextBuffer::cat
SYM_EXTRACT = '_ZN7TextAPI11extractTextEPci'
ATTENTE_FENETRE = 180              # images : une page en attente est notee si la fenetre de message ne s'est jamais ouverte au bout de ce delai (3 s)
MARGE_T = 120                      # 2 s de jeu (1/60 s) : deux messages identiques plus proches que cela sont un doublon
DELAI_ENREGISTREMENT = 5.0         # secondes : les ecritures sont groupees (les favoris ne changent qu'a la main : on ecrit tout de suite, voir basculer_favori)
PARTIE_VILLE, PARTIE_COMBAT, PARTIE_CHAMP = 0xc, 0xd, 0xe

GENRE_NOM, GENRE_GENERAL = 'n', 'g'                    # message avec un nom que le jeu affiche / sans nom
CAT_TERRAIN, CAT_COMBAT = 't', 'c'                      # message hors combat / de combat (jamais range dans les dialogues)
TYPE_DIALOGUE, TYPE_COMBAT = 'd', 'c'
INTROUVABLE = '(Message introuvable dans les fichiers du jeu : %s)'

TYPE_DE_LISTE = {'dialogues': TYPE_DIALOGUE, 'combats': TYPE_COMBAT}              # liste de l'historique -> type de ses elements (Historique.liste, filtre « Favoris seulement »)
ISSUES = ('victoire', 'fuite', 'defaite')
LIBELLE_ISSUE = {'victoire': 'Victoire', 'fuite': 'Fuite', 'defaite': 'Défaite'}


# ---------------------------------------------------------------------------------------------------------------------------------- elements
class Element:
    """Un element de l'historique : dialogue (type 'd' : nom affiche ou None, texte) ou combat (type 'c' : ennemis [{'nom', 'total', 'vaincus', 'fuis', 'disparus'}], or, xp, issue, objets [{'nom'}]).
    `n` : numero d'ordre (cle d'affichage), `t` : heure de jeu (1/60 s), `fav` : numero du favori correspondant (None : pas en favori)."""
    __slots__ = ('n', 'type', 't', 'nom', 'texte', 'ennemis', 'or_', 'xp', 'issue', 'fav', 'objets', 'mid', 'seg', 'val', 'lie', 'attente')

    def __init__(self, n, type_, t, nom=None, texte='', ennemis=None, or_=0, xp=0, issue='victoire', fav=None, objets=None, mid=None, seg=None, val=None):
        self.n, self.type, self.t, self.nom, self.texte = n, type_, t, nom, texte
        self.ennemis, self.or_, self.xp, self.issue, self.fav = ennemis or [], or_, xp, issue, fav
        self.objets = objets or []
        self.mid, self.seg, self.val = mid, seg, val or {}      # dialogue : numero du message dans les fichiers du jeu (None : inconnu), page du message (None : message entier), valeurs des variables [NONE a,b]
        self.lie = False                                         # favori de dialogue range par la cle (le fichier ne garde pas le texte)
        self.attente = False                                     # ... et dont le texte n'a pas encore ete redemande au moteur (voir Historique._resoudre)

    def cle(self):
        """Ce qui fait l'identite d'un element (pour reconnaitre un doublon, ou un element deja en favori) : le contenu, pas le numero."""
        if self.type == TYPE_DIALOGUE: return (TYPE_DIALOGUE, self.nom, self.texte)
        return (TYPE_COMBAT, self.t, self.issue, self.or_, self.xp, tuple((e['nom'], e['total'], e['vaincus'], e.get('fuis', 0), e.get('disparus', 0)) for e in self.ennemis),
                tuple(o['nom'] for o in self.objets))

    def vers_dict(self):
        if self.type == TYPE_DIALOGUE:
            if not self.lie: return {'k': TYPE_DIALOGUE, 'id': self.fav, 't': self.t, 'nom': self.nom, 'texte': self.texte}
            d = {'k': TYPE_DIALOGUE, 'id': self.fav, 't': self.t, 'nom': self.nom, 'mid': self.mid}          # (aucun texte : il vient des fichiers du jeu)
            if self.seg is not None: d['s'] = self.seg
            if self.val: d['v'] = dict(self.val)
            return d
        return {'k': TYPE_COMBAT, 'id': self.fav, 't': self.t, 'ennemis': [dict(e) for e in self.ennemis], 'or': self.or_, 'xp': self.xp, 'issue': self.issue, 'objets': [dict(o) for o in self.objets]}

    @staticmethod
    def depuis_dict(d, n):
        """Element d'un favori lu dans le fichier ; None s'il n'est pas valide (le reste du fichier est garde)."""
        try:
            ident, t = d['id'], d['t']
            if isinstance(ident, bool) or not isinstance(ident, int) or ident < 1 or isinstance(t, bool) or not isinstance(t, int) or t < 0: return None
            if d['k'] == TYPE_DIALOGUE:
                nom = d.get('nom')
                if not (nom is None or isinstance(nom, str)): return None
                nom = (sans_marques(nom).strip()[:60] or None) if nom else None
                if 'texte' in d:                                                               # favori qui garde son texte (avant #265, ou message que les fichiers du jeu ne redonnent pas tel quel)
                    texte = d['texte']
                    if not isinstance(texte, str) or not texte.strip(): return None
                    return Element(n, TYPE_DIALOGUE, t, nom, sans_marques(texte)[:MAX_TEXTE], fav=ident)
                mid, seg, val = d.get('mid'), d.get('s'), d.get('v', {})                      # favori range par la cle : le texte sera redemande au moteur
                if not _entier(mid) or mid < 1 or mid >= MSG_ID_MAX or not (seg is None or (_entier(seg) and 0 <= seg < 1000)): return None
                if not isinstance(val, dict) or len(val) > 20 or any(not isinstance(k, str) or not isinstance(v, str) or len(k) > 40 or len(v) > 200 for k, v in val.items()): return None
                e = Element(n, TYPE_DIALOGUE, t, nom, '', fav=ident, mid=mid, seg=seg, val=dict(val)); e.lie = e.attente = True
                return e
            if d['k'] == TYPE_COMBAT:
                issue, ennemis = d['issue'], d['ennemis']
                if issue not in ISSUES or not isinstance(ennemis, list): return None
                es = ennemis_valides(ennemis)
                gain = [d.get('or', 0), d.get('xp', 0)]
                if es is None or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in gain): return None
                obj = objets_valides(d.get('objets', []))                                      # (les favoris d'avant le #141 n'ont ni fuis, ni disparus, ni objets)
                if obj is None: return None
                return Element(n, TYPE_COMBAT, t, ennemis=es, or_=gain[0], xp=gain[1], issue=issue, fav=ident, objets=obj)
        except Exception:
            return None
        return None

    def __repr__(self): return 'Element(%r)' % (self.vers_dict(),)


def _entier(x): return isinstance(x, int) and not isinstance(x, bool)


def ennemis_valides(ennemis):
    """Liste d'especes [{'nom', 'total', 'vaincus', 'fuis', 'disparus'}] verifiee et copiee (fuis et disparus : 0 s'ils manquent, comme dans les favoris d'avant le #141) ; None si elle n'est pas valide."""
    if not isinstance(ennemis, list): return None
    es = []
    for e in ennemis:
        if not isinstance(e, dict): return None
        nom, tot, vai, fui, dis = e.get('nom'), e.get('total'), e.get('vaincus'), e.get('fuis', 0), e.get('disparus', 0)
        if not isinstance(nom, str) or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in (tot, vai, fui, dis)): return None
        es.append({'nom': sans_marques(nom)[:60], 'total': tot, 'vaincus': vai, 'fuis': fui, 'disparus': dis})
    return es[:12]


def objets_valides(objets):
    """Liste d'objets gagnes [{'nom'}] verifiee et copiee ; None si elle n'est pas valide."""
    if not isinstance(objets, list): return None
    out = []
    for o in objets:
        if not isinstance(o, dict) or not isinstance(o.get('nom'), str): return None
        out.append({'nom': sans_marques(o['nom']).strip()[:60]})
    return out[:8]


def sans_marques(texte):
    """Retire le « ; » du texte du patch : une marque de coupure placee juste apres une espace dans les noms d'objets (« bâton de ;cyprès », « l'herbe ;médicinale »), pas de la ponctuation (aucun « ; » de ponctuation
    dans les textes du patch ; voir docs/notes-visionneuse-dq4-pc.md, avance #148). L'espace qui la precede reste : « l'herbe médicinale »."""
    return texte.replace(';', '')


def nettoyer(texte):
    """Texte tel que le jeu l'affiche : codes de couleur (@c0...) et caracteres de controle retires, espaces de fin retires, retours a la ligne gardes (jamais plus d'une ligne vide). Le « *: » du debut des paroles
    d'un personnage sans nom est GARDE (c'est le texte du jeu). Le « ; » (marque de coupure des noms d'objets du patch) est retire (#139)."""
    t = (texte or '').replace('\r', '')
    t = re.sub(r'@c\d', '', t)
    t = sans_marques(t)
    t = ''.join(ch for ch in t if ch == '\n' or (ch >= ' ' and not (0xe000 <= ord(ch) <= 0xf8ff) and ch != '\x7f'))
    t = '\n'.join(l.rstrip() for l in t.split('\n'))
    t = re.sub(r'\n{3,}', '\n\n', t).strip('\n ')
    return t[:MAX_TEXTE]


def cle_message(mid):
    """La cle d'un message comme on la cite pour le patch : fichier (numero // 1000 x 1000, 7 chiffres) # rang : 802199 -> « b0802000#199 »."""
    return 'b%07d#%d' % (mid // 1000 * 1000, mid % 1000)


def valeurs(modele, texte):
    """Valeurs des variables du jeu (« [NONE 1,0] ») qui font du texte des fichiers `modele` le texte lu `texte` : {} si le modele n'a pas de variable (ou si le texte les montre telles quelles, comme les fichiers) et que
    les deux sont identiques ; {variable: valeur} si le texte se retrouve en remplacant chaque variable ; None si le modele ne redonne pas ce texte."""
    mod = nettoyer(modele)
    if mod == texte: return {}
    jetons = RE_JETON.findall(mod)
    if not jetons: return None
    r = re.match('^' + '(.*?)'.join(re.escape(m) for m in RE_JETON.split(mod)) + '$', texte, re.S)
    if r is None: return None
    vals = {}
    for j, v in zip(jetons, r.groups()):
        if vals.setdefault(j, v) != v: return None                                  # (la meme variable a deux valeurs : pas le meme message)
    return vals


def liaison(brut, texte):
    """Comment retrouver `texte` (ce que le joueur a lu, nettoye) dans le texte des fichiers du jeu `brut` : (page, valeurs des variables), `page` = rang de la page du message (separees par ㈡) ou None pour le message
    entier ; None si aucune page ni le message entier ne redonne EXACTEMENT ce texte (alors on garde le texte du favori)."""
    essais = [(None, brut)] + ([(i, p) for i, p in enumerate(brut.split(PAGE))] if PAGE in brut else [])
    for page, mod in essais:
        v = valeurs(mod, texte)
        if v is not None: return page, v
    return None


def texte_lie(brut, seg, val):
    """Texte d'un favori range par la cle : la page `seg` (None : tout le message) du texte des fichiers du jeu `brut`, variables remplacees par les valeurs gardees (une variable inconnue reste telle quelle). '' si `brut` manque
    ou n'a pas cette page."""
    if not brut: return ''
    if seg is not None:
        pages = brut.split(PAGE)
        if seg >= len(pages): return ''
        brut = pages[seg]
    t = RE_JETON.sub(lambda m: val.get(m.group(0), m.group(0)), nettoyer(brut))
    return t.strip('\n ')[:MAX_TEXTE]


def envelopper(texte, largeur, mesure):
    """Coupe `texte` en lignes de `largeur` au plus (mesure(chaine) -> largeur) : les retours a la ligne du texte sont gardes, la coupure se fait aux espaces (pas aux espaces insecables) ; un mot plus large que la ligne est coupe."""
    lignes = []
    for para in texte.split('\n'):
        if not para.strip(): lignes.append(''); continue
        cur = ''
        for mot in re.split(r' +', para):
            cand = mot if not cur else cur + ' ' + mot
            if cur and mesure(cand) > largeur: lignes.append(cur); cur = mot
            else: cur = cand
            while mesure(cur) > largeur and len(cur) > 1:                               # mot plus large que la ligne
                i = len(cur) - 1
                while i > 1 and mesure(cur[:i]) > largeur: i -= 1
                lignes.append(cur[:i]); cur = cur[i:]
        lignes.append(cur)
    while lignes and not lignes[-1]: lignes.pop()
    return lignes or ['']


def pluriel(n, mot_masc):
    """« 1 vaincu », « 2 vaincus » (mot au masculin singulier)."""
    return '%d %s%s' % (n, mot_masc, 's' if n > 1 else '')


def ligne_espece(e):
    """Une espece d'ennemis, sur une ligne : « Gluant ×3 » quand tous sont vaincus (« Gluant » s'il n'y en avait qu'un), sinon le sort de chacun : « Gluant ×3 : 1 vaincu, 1 enfui, 1 disparu » ; ceux qui ne sont ni vaincus,
    ni enfuis, ni disparus sont encore la quand le combat se termine (le groupe a fui ou a ete vaincu) : « 2 restés »."""
    tot, vai, fui, dis = e['total'], e['vaincus'], e.get('fuis', 0), e.get('disparus', 0)
    base = '%s ×%d' % (e['nom'], tot) if tot > 1 else e['nom']
    if vai >= tot: return base
    reste = max(0, tot - vai - fui - dis)
    if tot == 1: return '%s : %s' % (base, 'enfui' if fui else 'disparu' if dis else 'resté')
    sorts = [pluriel(n, mot) for n, mot in ((vai, 'vaincu'), (fui, 'enfui'), (dis, 'disparu'), (reste, 'resté')) if n > 0]
    return '%s : %s' % (base, ', '.join(sorts))


def lignes_combat(c):
    """Lignes de texte d'un combat (Element de type 'c'), une par rangee : une par espece d'ennemi (ligne_espece : qui etait la, qui est vaincu, enfui, disparu ou reste), puis, pour une victoire, l'or et l'experience
    gagnes, puis les objets obtenus (« Objets : Herbe médicinale, Pierre de vie »). Rien n'est ecrit quand il n'y a pas eu d'objet."""
    out = [ligne_espece(e) for e in c.ennemis]
    if not out: out.append('Ennemis inconnus')
    if c.issue == 'victoire':
        out.append('Or : %d\u00a0\u00a0\u00a0\u00a0\u00a0Expérience : %d' % (c.or_, c.xp))          # (espaces insecables : la coupure des lignes ne les fait pas disparaitre)
        if c.objets: out.append('Objets : ' + ', '.join(o['nom'] for o in c.objets))
    return out


def element_de_combat(n, combat):
    """Element de type 'c' d'un dict de historique_combat.CapteurCombat.maj ; None si le dict est inexploitable."""
    try:
        issue = combat['issue']
        if issue not in ISSUES: return None
        es = [{'nom': str(e['nom'])[:60], 'total': int(e['total']), 'vaincus': int(e['vaincus']), 'fuis': int(e.get('fuis', 0)), 'disparus': int(e.get('disparus', 0))} for e in combat['ennemis']][:12]
        objets = [{'nom': sans_marques(str(o['nom'])).strip()[:60]} for o in combat.get('objets', [])][:8]
        return Element(n, TYPE_COMBAT, int(combat['t']), ennemis=es, or_=max(0, int(combat['or'])), xp=max(0, int(combat['xp'])), issue=issue, objets=objets)
    except Exception:
        return None


# ---------------------------------------------------------------------------------------------------------------------------------- donnees
class Historique:
    """Dialogues et combats de la session (en memoire) + favoris (fichier). Le fichier est a cote de la visionneuse (jamais dans le dossier des sauvegardes du jeu, que l'on ne modifie pas) :
    {"version": 2, "suivant": 7, "favoris": [{"k": "d", "id": 3, "t": 12345, "nom": "Alena", "texte": "..."}, {"k": "c", "id": 5, "t": 1, "ennemis": [...], "or": 3, "xp": 4, "issue": "victoire", "objets": [{"nom": "Herbe médicinale"}]}]}."""

    def __init__(self, chemin=None, horloge=time.time):
        self.chemin = chemin; self.horloge = horloge
        self.dialogues = []                                 # Element 'd' de la session, du plus ancien au plus recent
        self.combats = []                                   # Element 'c' de la session
        self.favoris = []                                   # Element (d ou c) gardes dans le fichier, dans l'ordre ou ils ont ete mis en favori
        self.suivant = 1                                    # prochain numero de favori
        self._n = 0                                         # compteur des numeros d'ordre (dialogues, combats, favoris : jamais deux fois le meme)
        self._attente = []                                  # pages d'un message deja preparees par le moteur mais pas encore lues (voir _pages)
        self._feed = False; self._a_vu = False; self._n_att = 0       # curseur de fin de page de l'image precedente ; fenetre de message vue ouverte depuis la rafale ; images d'attente
        self._sale = False; self._t_ecr = 0.0
        self.erreur = None
        self._cap = None; self._modeles = {}                # Capteur du moteur (une fois qu'il existe) ; texte des fichiers du jeu deja demande, par numero de message
        self.charger()

    def _num(self):
        self._n += 1; return self._n

    # ---- fichier des favoris
    def charger(self):
        """Lit le fichier des favoris. Un fichier illisible est mis de cote (.corrompu) et on repart de zero ; un favori invalide est ignore sans perdre les autres."""
        self.favoris = []; self.suivant = 1
        if not self.chemin or not os.path.exists(self.chemin): return
        try:
            with open(self.chemin, encoding='utf-8') as f: d = json.load(f)
            if not isinstance(d, dict) or d.get('version') != VERSION or not isinstance(d.get('favoris'), list): raise ValueError('format inconnu')
            vus = set()
            for x in d['favoris']:
                e = Element.depuis_dict(x, self._num()) if isinstance(x, dict) else None
                if e is not None and e.fav not in vus: vus.add(e.fav); self.favoris.append(e)
            self.favoris = self.favoris[-MAX_FAVORIS:]
            s = d.get('suivant')                                              # prochain numero enregistre : jamais un numero deja pris, ni un numero deja donne puis retire
            self.suivant = max([e.fav + 1 for e in self.favoris] + [s if isinstance(s, int) and not isinstance(s, bool) and s > 0 else 1])
        except Exception as ex:
            self.erreur = repr(ex); self.favoris = []; self.suivant = 1
            try: os.replace(self.chemin, self.chemin + '.corrompu')
            except Exception: pass
            print('Favoris de l\'historique illisibles (%s) : mis de cote, on repart de zero (%r)' % (self.chemin, ex), flush=True)

    def enregistrer(self, force=False):
        """Ecrit le fichier s'il a change (ecriture atomique : fichier temporaire puis remplacement). Les ecritures sont groupees : au plus une toutes les DELAI_ENREGISTREMENT secondes, `force` pour la fermeture."""
        if not self.chemin or not self._sale: return False
        now = self.horloge()
        if not force and now - self._t_ecr < DELAI_ENREGISTREMENT: return False
        self._t_ecr = now
        try:
            d = {'version': VERSION, 'suivant': self.suivant, 'favoris': [e.vers_dict() for e in self.favoris]}
            os.makedirs(os.path.dirname(os.path.abspath(self.chemin)), exist_ok=True)
            tmp = self.chemin + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
            os.replace(tmp, self.chemin); self._sale = False
            return True
        except Exception as ex:
            self.erreur = repr(ex); print('Favoris de l\'historique non enregistres :', ex, flush=True)
            return False

    # ---- listes
    def liste(self, onglet, favoris_seuls=False):
        """Elements d'un onglet de l'historique, du plus ancien au plus recent : 'dialogues' ou 'combats' (et 'favoris' : tous les favoris, voir ci-dessous). `favoris_seuls` : l'option « Favoris seulement » de la fenetre -> seuls les
        favoris de cette sorte d'element (dialogues ou combats) : ceux du fichier, donc aussi ceux des sessions precedentes, dans l'ordre ou ils ont ete mis en favori (le plus recent en bas)."""
        if favoris_seuls and onglet in TYPE_DE_LISTE: return [f for f in self.favoris if f.type == TYPE_DE_LISTE[onglet]]
        return list({'dialogues': self.dialogues, 'combats': self.combats, 'favoris': self.favoris}.get(onglet, ()))

    # ---- favoris
    def basculer_favori(self, e):
        """Met l'element en favori (une copie est gardee dans le fichier, immediatement) ou le retire. Un element de la liste des favoris qu'on « desetoile » disparait de cette liste ; l'element de la session qui
        lui correspond perd son etoile. -> True si l'element est maintenant en favori."""
        if e is None: return False
        if e.fav is not None:
            self.retirer_favori(e.fav); return False
        if len(self.favoris) >= MAX_FAVORIS: del self.favoris[0]
        copie = Element(self._num(), e.type, e.t, e.nom, e.texte, [dict(x) for x in e.ennemis], e.or_, e.xp, e.issue, fav=self.suivant, objets=[dict(o) for o in e.objets], mid=e.mid)
        self._lier(copie)
        e.fav = self.suivant; self.suivant += 1
        self.favoris.append(copie); self._sale = True; self.enregistrer(True)
        return True

    def _modele(self, mid):
        """Texte du message `mid` dans les fichiers du jeu (demande au moteur ; garde), ou None (pas de moteur, message inconnu)."""
        if mid in self._modeles: return self._modeles[mid]
        cap = self._cap
        if cap is None or not hasattr(cap, 'modele'): return None
        try: brut = cap.modele(mid)
        except Exception: brut = None
        self._modeles[mid] = brut
        return brut

    def _lier(self, f):
        """Un favori de dialogue dont on connait la cle : si le texte des fichiers du jeu redonne EXACTEMENT le texte lu, le favori est range par la cle (le fichier ne gardera pas le texte) ; sinon il garde son texte."""
        if f.type != TYPE_DIALOGUE or not f.mid: return
        brut = self._modele(f.mid)
        l = liaison(brut, f.texte) if brut else None
        if l is not None: f.seg, f.val = l; f.lie = True; f.attente = False

    def _resoudre(self):
        """Redemande au moteur le texte des favoris ranges par la cle (0,13 ms l'appel : les 500 favoris du fichier en 65 ms). Un message qui n'existe plus ou n'a plus cette page : une ligne le dit, avec la cle."""
        if self._cap is None: return
        for f in self.favoris:
            if not f.attente: continue
            f.texte = texte_lie(self._modele(f.mid), f.seg, f.val) or INTROUVABLE % cle_message(f.mid)
            f.attente = False; f.n = self._num()                                   # (nouveau numero : la mise en page gardee par la fenetre ne vaut plus)

    def actualiser(self):
        """A l'ouverture de l'historique : les textes des favoris ranges par la cle sont redemandes au moteur. Les fichiers du jeu ne changent pas pendant que la visionneuse tourne, mais le moteur choisit certaines
        variantes d'un texte selon la partie en cours (le sexe du heros : « ma mignonne » / « mon chou ») : un favori montre donc le texte tel que la partie actuelle le donnerait."""
        self._modeles.clear()
        for f in self.favoris:
            if f.lie: f.attente = True
        try: self._resoudre()
        except Exception as ex: self.erreur = repr(ex); print('Historique : texte des favoris non redemande (%r)' % (ex,), flush=True)

    def retirer_favori(self, ident):
        self.favoris = [f for f in self.favoris if f.fav != ident]
        for e in self.dialogues + self.combats:
            if e.fav == ident: e.fav = None
        self._sale = True; self.enregistrer(True)

    # ---- ajout
    def ajouter(self, texte, nom, t, mid=None):
        """Ajoute un dialogue de la session (texte brut du moteur, nom affiche par le jeu ou None, numero du message dans les fichiers du jeu ou None) ; -> l'Element, ou None (vide, doublon)."""
        texte = nettoyer(texte)
        if not texte: return None
        nom = (sans_marques(str(nom)).strip()[:60] or None) if nom else None
        e = Element(self._num(), TYPE_DIALOGUE, int(t), nom, texte, mid=mid if _entier(mid) and 0 < mid < MSG_ID_MAX else None)
        if self.dialogues:
            d = self.dialogues[-1]
            if d.cle() == e.cle() and abs(e.t - d.t) <= MARGE_T: return None             # le moteur a reaffiche le message (page revenue, question reposee)
        self.dialogues.append(e)
        if len(self.dialogues) > MAX_DIALOGUES: del self.dialogues[:len(self.dialogues) - MAX_DIALOGUES]
        return e

    def ajouter_combat(self, combat):
        """Ajoute un combat termine (dict de historique_combat.CapteurCombat.maj) ; -> l'Element, ou None."""
        e = element_de_combat(self._num(), combat)
        if e is None: return None
        self.combats.append(e)
        if len(self.combats) > MAX_COMBATS: del self.combats[:len(self.combats) - MAX_COMBATS]
        return e

    # ---- liaison avec le moteur
    def maj(self, moteur, objets=None, noms=None):
        """Une fois par pas du moteur : range les messages notes par le Capteur (dialogues hors combat) et les combats termines (CapteurCombat), et ecrit les favoris si besoin."""
        try:
            cap = getattr(moteur, 'capteur', None)
            if cap is not None and cap.actif:
                self._cap = cap
                jeu = moteur.etat.partie in (PARTIE_VILLE, PARTIE_COMBAT, PARTIE_CHAMP)
                recus = cap.vider()
                if not jeu: self._attente = []
                else: self._pages(moteur, recus)
            cc = getattr(moteur, 'capteur_combat', None)
            if cc is not None:
                for c in cc.maj(moteur): self.ajouter_combat(c)
            self._resoudre()
            self.enregistrer()
        except Exception as ex:                                              # l'historique ne doit jamais arreter le jeu
            if self.erreur is None: print('Historique : erreur (%r)' % (ex,), flush=True)
            self.erreur = repr(ex)

    def _ranger(self, r):
        if r['cat'] == CAT_COMBAT: return                                    # les messages de combat n'entrent pas dans les dialogues
        self.ajouter(r['texte'], r['val'] if r['genre'] == GENRE_NOM else None, r['t'], r.get('mid'))

    def _liberer(self, n):
        """Range les `n` premieres pages en attente (toutes si n est None)."""
        k = len(self._attente) if n is None else min(n, len(self._attente))
        pages, self._attente = self._attente[:k], self._attente[k:]
        for r in pages: self._ranger(r)

    def _pages(self, moteur, recus):
        """Le moteur prepare TOUTES les pages d'un message d'un coup (plusieurs TextBuffer::cat dans la meme image, meme temps de jeu) : ne noter que celles que le joueur a lues, sinon l'historique
        montrerait la page suivante avant sa lecture. La premiere page est notee tout de suite ; chaque fois que le curseur de fin de page s'eteint (le joueur tourne la page, Moteur.ui.msg['feed']) la suivante
        est notee ; tout ce qui reste est note quand la fenetre de message se ferme ou quand un nouveau message arrive. Les messages de combat (defilement automatique) ne sont jamais retenus."""
        msg = getattr(getattr(moteur, 'ui', None), 'msg', None)
        feed = bool(msg.get('feed')) if isinstance(msg, dict) else False
        chute = self._feed and not feed; self._feed = feed
        visible = bool(getattr(moteur, 'msg_visible', True))
        if recus:
            self._liberer(None)                                      # nouveau message : le precedent est fini (ses pages restantes ont ete lues ou sautees)
            self._a_vu = visible; self._n_att = 0
            prec = None
            for r in recus:
                cle = (r['genre'], r['val'], r['cat'], r['carte'], r['t'])
                if prec is not None and cle == prec and r['cat'] != CAT_COMBAT: self._attente.append(r)                # page suivante du meme message
                else: self._ranger(r)
                prec = cle
            return
        if not self._attente: return
        if visible: self._a_vu = True
        else: self._n_att += 1
        if (not visible and self._a_vu) or self._n_att > ATTENTE_FENETRE: self._liberer(None)      # la fenetre s'est fermee (ou ne s'est jamais ouverte) : le message est fini
        elif chute: self._liberer(1)


# ---------------------------------------------------------------------------------------------------------------------------------- crochets dans le moteur
class Capteur:
    """Crochet sur le moteur (Unicorn) : TextBuffer::cat, appelee une fois par page de message. Les messages notes attendent dans `sortie` jusqu'a ce que Historique.maj les prenne (chacun : texte, genre, val = nom que le
    jeu affiche ou None, cat, carte, t, mid = numero du message dans les fichiers du jeu ou None). Le numero vient d'un second crochet, sur ui_MsgAdd(numero, bool) : TextBuffer::cat y est appelee (la pile le montre) ;
    une page qui n'en vient pas (texte construit par le programme) n'a pas de numero. Une erreur dans un crochet ne doit jamais arreter le moteur."""

    def __init__(self, moteur):
        self.actif = False; self.sortie = []; self._mid = None; self._tampon = None
        self.m = moteur; c = self.c = moteur.core
        try:
            import unicorn
            self.g_game = c.export('_ZN6status6g_GameE'); cat = c.export('_ZN10TextBuffer3catEPKcS1_')
            if not self.g_game or not cat: return
            c.uc.hook_add(unicorn.UC_HOOK_CODE, self._cat, None, cat, cat)
            self.actif = True
        except Exception as ex:
            print('Historique : crochets non installes (%r)' % (ex,), flush=True)
            return
        try:
            add = c.export(SYM_UI_MSGADD)
            if add: c.uc.hook_add(unicorn.UC_HOOK_CODE, self._add, None, add, add)
        except Exception as ex:
            print('Historique : numeros de message non captes (%r)' % (ex,), flush=True)

    def _add(self, uc, adr, taille, _):
        """Entree de ui_MsgAdd : le numero du message (1er argument) que TextBuffer::cat va recevoir."""
        try: self._mid = uc.reg_read(self.c.XREG[0]) & 0xffffffff
        except Exception: self._mid = None

    def modele(self, mid):
        """Texte du message `mid` tel que le moteur le tire des fichiers du jeu (TextAPI::extractText, genre 1 = message) : brut, avec les sauts de page « ㈡ » et les variables « [NONE 1,0] » ; None si le moteur n'en a pas.
        A appeler entre deux images (jamais depuis un crochet), comme les noms de historique_combat."""
        try:
            c = self.c; f = c.export(SYM_EXTRACT)
            if not f or not isinstance(mid, int) or not 0 < mid < MSG_ID_MAX: return None
            if self._tampon is None: self._tampon = c.malloc(8192)
            c.mem_w(self._tampon, b'\0' * 16)
            c.call(f, self._tampon, (1 << 24) | mid, label='texte du message', timeout_s=10)
            t = c.read_cstr(self._tampon).decode('utf-8', 'replace')
            return t if t.strip() and not t.startswith('<ERR') else None
        except Exception:
            return None

    def temps_et_cle(self):
        """-> (temps de jeu en 1/60 s, identifiant de la partie) lus dans status::g_Game."""
        try:
            t, uid = struct.unpack('<2I', self.c.mem(self.g_game + 4, 8)); return t, uid
        except Exception:
            return None, 0

    def vider(self):
        s, self.sortie = self.sortie, []
        return s

    def _pile(self, uc, n=24):
        """Noms des fonctions de la pile d'appels (chaine des pointeurs de cadre), de l'appelante immediate vers la racine."""
        c = self.c; noms = [c.where(uc.reg_read(c.XREG[30])).split('+')[0]]
        fp = uc.reg_read(c.XREG[29])
        for _ in range(n):
            try: nfp, nlr = struct.unpack('<QQ', c.mem(fp, 16))
            except Exception: break
            if not nfp or nfp <= fp: break
            noms.append(c.where(nlr).split('+')[0]); fp = nfp
        return noms

    def _cat(self, uc, adr, taille, _):
        try:
            c = self.c; x1, x2 = uc.reg_read(c.XREG[1]), uc.reg_read(c.XREG[2])
            texte = c.read_cstr(x1).decode('utf-8', 'replace') if x1 else ''
            if not texte.strip(): return
            nom = c.read_cstr(x2).decode('utf-8', 'replace').strip() if x2 else ''           # le nom que le jeu affiche sur la fenetre de message (vide : aucun)
            e = self.m.etat
            pile = self._pile(uc)
            combat = e.partie == PARTIE_COMBAT or any('Battle' in s for s in pile)
            t, _u = self.temps_et_cle()
            mid = getattr(self, '_mid', None) if pile and pile[0] == SYM_UI_MSGADD else None            # (l'appelante immediate de TextBuffer::cat est ui_MsgAdd : le numero vient de cet appel)
            self.sortie.append({'texte': texte, 'genre': GENRE_NOM if nom else GENRE_GENERAL, 'val': nom or None, 'cat': CAT_COMBAT if combat else CAT_TERRAIN,
                                'carte': 'monde' if e.partie == PARTIE_CHAMP else e.carte, 't': t or 0, 'mid': mid})
            if len(self.sortie) > 500: del self.sortie[:250]                      # (jamais vide faute de Historique.maj : on ne grossit pas sans fin)
        except Exception:
            pass
