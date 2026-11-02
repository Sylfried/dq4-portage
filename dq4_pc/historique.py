"""Historique des messages : tout ce qui a ete dit a l'ecran, avec QUI l'a dit et OU (« Une femme · Grotte », « Un soldat · Château de Bastione », « Une jarre · Bastione », « Alena », « Message général », « Combat »).

Trois morceaux :
- `Capteur` (crochets dans le moteur, installes par Moteur.__init__) : le texte d'un message n'est connu qu'a un endroit, TextBuffer::cat (appelee une fois par page de message, macros resolues, avec le nom du
  locuteur donne par le moteur lui-meme : le « @a<nom>@b » des textes du patch). Le crochet note le texte, ce nom, l'heure de jeu (status::g_Game + 4, en 1/60 s) et le CONTEXTE de l'appel, lu dans la pile :
    nom explicite du moteur (ETABLI) > installation (MaterielMenu_* : boutique, eglise, auberge... ; ETABLI par le nom du symbole) > objet fouille (TownFurnitureObject : son numero d'objet de la carte, ETABLI) >
    personnage de terrain (ScriptGroup::execute -> getPlacementCtrlId -> TownCharacterManager : numero de modele du sprite = Etat.sprites[emplacement]['id'], ETABLI) > combat (partie 0xd) > message general.
- `Historique` (donnees pures, sans pyglet ni emulateur) : liste bornee des entrees par partie, doublons ecartes, retour en arriere (sauvegarde plus ancienne rechargee), fichier JSON a cote de la visionneuse.
- des fonctions pures : nettoyage du texte, en-tete (« locuteur · lieu », via libelles.py, import protege), coupure des lignes.

Une « partie » = une aventure, reconnue par l'identifiant tire au hasard a la creation (status::g_Game + 8, 1 octet utile) et conserve dans chacune de ses sauvegardes : deux sauvegardes d'une meme aventure ont la meme
valeur, deux aventures ont (sauf une fois sur 256) deux valeurs differentes. Retour en arriere : le temps de jeu ne recule jamais, sauf si une sauvegarde plus ancienne (ou un etat instantane) est rechargee ; les entrees
plus recentes que ce temps sont alors retirees (voir Historique.synchroniser pour les limites)."""
import json, os, re, struct, time

VERSION = 1
MAX_ENTREES = 3000                 # par partie : les plus anciennes sortent
MAX_PARTIES = 6                    # parties gardees dans le fichier : la moins recemment vue sort
MAX_TEXTE = 1500                   # caracteres gardes d'un message
MARGE_T = 120                      # 2 s de jeu (1/60 s) : un retour en arriere plus petit n'en est pas un ; deux messages identiques plus proches que cela sont un doublon
CONFIRMATIONS = 3                  # images consecutives pendant lesquelles un changement de partie / un retour en arriere doit durer avant d'etre pris en compte (un instant incoherent pendant un chargement ne vide rien)
DELAI_ENREGISTREMENT = 5.0         # secondes : les ecritures sont groupees
DELAI_GROUPE = 1200                # 20 s de jeu : deux messages du meme locuteur plus proches que cela sont presentes sous un seul en-tete
PARTIE_VILLE, PARTIE_COMBAT, PARTIE_CHAMP = 0xc, 0xd, 0xe

GENRE_NOM, GENRE_PERSO, GENRE_OBJET, GENRE_INSTALLATION, GENRE_GENERAL, GENRE_COMBAT = 'n', 'p', 'o', 'f', 'g', 'c'
GENRES = (GENRE_NOM, GENRE_PERSO, GENRE_OBJET, GENRE_INSTALLATION, GENRE_GENERAL, GENRE_COMBAT)
CAT_TERRAIN, CAT_COMBAT, CAT_SYSTEME = 't', 'c', 's'
CATEGORIES = (CAT_TERRAIN, CAT_COMBAT, CAT_SYSTEME)
LIBELLE_GENERAL, LIBELLE_COMBAT, REPLI_PERSO, REPLI_OBJET = 'Message général', 'Combat', 'Personnage', 'Objet'
SEPARATEUR = ' · '

# installations (menus du moteur dont la classe porte le nom : MaterielMenu_SHOP_ROOT... ; accueil du pretre quand on charge une sauvegarde faite a l'eglise : TownPlayerManager::loadChurch) -> libelle ; le premier qui correspond (dans cet ordre) l'emporte
INSTALLATIONS = (('MaterielMenu_SHOP', 'Boutique'), ('MaterielMenu_CHURCH', 'Église'), ('TownPlayerManager10loadChurch', 'Église'), ('MaterielMenu_INN', 'Auberge'), ('MaterielMenu_BANK', 'Banque'),
                 ('MaterielMenu_MEDAL_KING', 'Roi des médailles'), ('MaterielMenu_MARTIAL_COLOSSEUM', 'Arène'),
                 ('MaterielMenu_SLOT', 'Casino'), ('MaterielMenu_POKER', 'Casino'), ('MaterielMenu_COINSALEROOM', 'Casino'), ('MaterielMenu_CHANGEGIFT', 'Casino'), ('MaterielMenu_FIGHT_STADIUM', 'Casino'),
                 ('MaterielMenu_SAVE', 'Sauvegarde'), ('MaterielMenu_LOAD', 'Sauvegarde'))
# fonctions de l'objet fouille appelees juste avant d'ecrire son message (this + 0x10 = numero d'objet de la carte, le champ « uid » de la table des objets)
FONCTIONS_MOBILIER = ('_ZN19TownFurnitureObject15setFirstMessageEv', '_ZN19TownFurnitureObject10addMessageEib', '_ZN19TownFurnitureObject10setMessageEv', '_ZN19TownFurnitureObject16setSecondMessageEv',
                      '_ZN17TownFurnitureItem16setSecondMessageEv', '_ZN17TownFurnitureGold16setSecondMessageEv', '_ZN20TownFurnitureEncount16setSecondMessageEv')
AUTO = object()                    # « utilise libelles.py s'il existe » (en_tete)


# ---------------------------------------------------------------------------------------------------------------------------------- entrees
class Entree:
    """Un message : n (numero d'ordre dans la partie), t (heure de jeu, 1/60 s), cat (CAT_*), genre + val (qui : voir GENRE_*, val = nom, numero de modele, nom de modele d'objet ou libelle d'installation), carte (identifiant de
    carte du moteur, « monde » sur la carte du monde), texte."""
    __slots__ = ('n', 't', 'cat', 'genre', 'val', 'carte', 'texte')

    def __init__(self, n, t, cat, genre, val, carte, texte):
        self.n, self.t, self.cat, self.genre, self.val, self.carte, self.texte = n, t, cat, genre, val, carte, texte

    def vers_liste(self): return [self.n, self.t, self.cat, self.genre, self.val, self.carte, self.texte]

    @staticmethod
    def depuis_liste(l):
        """Entree d'une liste lue dans le fichier ; None si elle n'est pas valide (le reste du fichier est garde)."""
        try:
            n, t, cat, genre, val, carte, texte = l
            if isinstance(n, bool) or not isinstance(n, int) or isinstance(t, bool) or not isinstance(t, int) or t < 0: return None
            if cat not in CATEGORIES or genre not in GENRES or not isinstance(texte, str) or not texte.strip(): return None
            if not (val is None or isinstance(val, str) or (isinstance(val, int) and not isinstance(val, bool))): return None
            if not (carte is None or isinstance(carte, str)): return None
            return Entree(n, t, cat, genre, val, carte[:60] if carte else None, texte[:MAX_TEXTE])
        except Exception:
            return None

    def __repr__(self): return 'Entree(%r)' % (self.vers_liste(),)


def nettoyer(texte):
    """Texte tel qu'il est affiche : codes de couleur (@c0...) et caracteres de controle retires, espaces de fin retires, retours a la ligne gardes (jamais plus d'une ligne vide). -> (texte, anonyme) ; anonyme :
    le texte commence par « *: » (paroles d'un personnage sans nom dans le patch FR) ; ce marqueur est retire, l'en-tete le remplace."""
    t = (texte or '').replace('\r', '')
    t = re.sub(r'@c\d', '', t)
    t = ''.join(ch for ch in t if ch == '\n' or (ch >= ' ' and not (0xe000 <= ord(ch) <= 0xf8ff) and ch != '\x7f'))
    anonyme = False
    m = re.match(r'\s*\*\s*:\s?', t)
    if m: t = t[m.end():]; anonyme = True
    t = '\n'.join(l.rstrip() for l in t.split('\n'))
    t = re.sub(r'\n{3,}', '\n\n', t).strip('\n ')
    return t[:MAX_TEXTE], anonyme


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


# ---------------------------------------------------------------------------------------------------------------------------------- en-tete
_lib_cache = []


def libelles():
    """Module libelles.py (un autre agent l'ecrit : libelle_source, libelle_lieu) ou None s'il est absent ou casse."""
    if not _lib_cache:
        try: import libelles as L
        except Exception: L = None
        _lib_cache.append(L)
    return _lib_cache[0]


def _appel(lib, nom, arg):
    f = getattr(lib, nom, None) if lib is not None else None
    if f is None: return None
    try:
        r = f(arg)
        return r.strip() if isinstance(r, str) and r.strip() else None
    except Exception:
        return None


def lieu_de(carte, lib=AUTO):
    """Nom court du lieu d'une carte (« Grotte »), None s'il est inconnu (omis de l'en-tete)."""
    if lib is AUTO: lib = libelles()
    return _appel(lib, 'libelle_lieu', carte) if carte else None


def locuteur(e, lib=AUTO):
    """Celui qui parle : le nom du moteur tel quel, sinon le libelle de libelles.py (« Une femme »), sinon un mot generique (« Personnage », « Objet »), « Message général », « Combat »."""
    if lib is AUTO: lib = libelles()
    if e.genre == GENRE_NOM: return str(e.val).strip() or LIBELLE_GENERAL
    if e.genre == GENRE_PERSO: return (_appel(lib, 'libelle_source', e.val) if e.val is not None else None) or REPLI_PERSO
    if e.genre == GENRE_OBJET: return (_appel(lib, 'libelle_source', e.val) if e.val is not None else None) or REPLI_OBJET
    if e.genre == GENRE_INSTALLATION: return str(e.val) if e.val else LIBELLE_GENERAL
    if e.genre == GENRE_COMBAT: return LIBELLE_COMBAT
    return LIBELLE_GENERAL


def en_tete(e, lib=AUTO):
    """« Une femme · Grotte », « Alena », « Message général », « Combat » : un nom donne par le moteur, un message general et un combat n'ont pas de lieu ; un lieu inconnu est omis."""
    qui = locuteur(e, lib)
    if e.genre in (GENRE_NOM, GENRE_GENERAL, GENRE_COMBAT): return qui
    lieu = lieu_de(e.carte, lib)
    return qui + SEPARATEUR + lieu if lieu else qui


def meme_groupe(a, b, lib=AUTO):
    """Deux messages qui se suivent sont-ils presentes sous un seul en-tete ? Meme en-tete et moins de DELAI_GROUPE de temps de jeu entre les deux."""
    return a is not None and b is not None and 0 <= b.t - a.t <= DELAI_GROUPE and en_tete(a, lib) == en_tete(b, lib)


def doublon(a, b):
    """b repete a (meme locuteur, meme lieu, meme texte, moins de MARGE_T apres) : le moteur a reaffiche le message (page revenue, question reposee)."""
    return a is not None and (a.genre, a.val, a.carte, a.texte) == (b.genre, b.val, b.carte, b.texte) and abs(b.t - a.t) <= MARGE_T


# ---------------------------------------------------------------------------------------------------------------------------------- donnees
class Historique:
    """Entrees de la partie en cours et fichier. Le fichier est a cote de la visionneuse (jamais dans le dossier des sauvegardes du jeu, que l'on ne modifie pas) :
    {"version": 1, "parties": {"66": {"vu": 1.7e9, "entrees": [[n, t, cat, genre, val, carte, texte], ...]}}}."""

    def __init__(self, chemin=None, horloge=time.time):
        self.chemin = chemin; self.horloge = horloge
        self.parties = {}                                   # cle de partie -> {'vu': date, 'entrees': [Entree]}
        self.cle = None                                     # partie en cours
        self.dernier_t = None                               # dernier temps de jeu vu pour cette partie
        self._cand = None                                   # (changement en attente, nombre d'images de suite)
        self._sale = False; self._t_ecr = 0.0
        self._carte_connue = None                           # derniere carte dont le lieu est connu (les cartes d'evenement et de combat n'en ont pas : on garde le dernier)
        self.erreur = None
        self.charger()

    # ---- fichier
    def charger(self):
        """Lit le fichier. Un fichier illisible est mis de cote (.corrompu) et on repart de zero ; une entree invalide est ignoree sans perdre les autres."""
        self.parties = {}
        if not self.chemin or not os.path.exists(self.chemin): return
        try:
            with open(self.chemin, encoding='utf-8') as f: d = json.load(f)
            if not isinstance(d, dict) or d.get('version') != VERSION or not isinstance(d.get('parties'), dict): raise ValueError('format inconnu')
            for cle, p in d['parties'].items():
                if not isinstance(cle, str) or not isinstance(p, dict) or not isinstance(p.get('entrees'), list): continue
                es = [x for x in (Entree.depuis_liste(l) for l in p['entrees']) if x is not None][-MAX_ENTREES:]
                vu = p.get('vu'); self.parties[cle] = {'vu': float(vu) if isinstance(vu, (int, float)) and not isinstance(vu, bool) else 0.0, 'entrees': es}
            self._elaguer_parties()
        except Exception as ex:
            self.erreur = repr(ex); self.parties = {}
            try: os.replace(self.chemin, self.chemin + '.corrompu')
            except Exception: pass
            print('Historique des messages illisible (%s) : mis de cote, on repart de zero (%r)' % (self.chemin, ex), flush=True)

    def enregistrer(self, force=False):
        """Ecrit le fichier s'il a change (ecriture atomique : fichier temporaire puis remplacement). Les ecritures sont groupees : au plus une toutes les DELAI_ENREGISTREMENT secondes, `force` pour la fermeture."""
        if not self.chemin or not self._sale: return False
        now = self.horloge()
        if not force and now - self._t_ecr < DELAI_ENREGISTREMENT: return False
        self._t_ecr = now
        try:
            d = {'version': VERSION, 'parties': {c: {'vu': p['vu'], 'entrees': [e.vers_liste() for e in p['entrees']]} for c, p in self.parties.items()}}
            os.makedirs(os.path.dirname(os.path.abspath(self.chemin)), exist_ok=True)
            tmp = self.chemin + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
            os.replace(tmp, self.chemin); self._sale = False
            return True
        except Exception as ex:
            self.erreur = repr(ex); print('Historique des messages non enregistre :', ex, flush=True)
            return False

    def _elaguer_parties(self):
        while len(self.parties) > MAX_PARTIES:
            vieille = min((c for c in self.parties if c != self.cle), key=lambda c: self.parties[c]['vu'], default=None)
            if vieille is None: break
            del self.parties[vieille]

    # ---- partie en cours
    def entrees(self, categorie=None):
        """Entrees de la partie en cours, de la plus ancienne a la plus recente ; `categorie` (CAT_COMBAT...) pour n'en garder qu'une sorte, '!c' pour tout sauf les combats."""
        p = self.parties.get(self.cle)
        es = p['entrees'] if p else []
        if categorie is None: return list(es)
        if categorie.startswith('!'): return [e for e in es if e.cat != categorie[1:]]
        return [e for e in es if e.cat == categorie]

    def _partie(self, cle):
        p = self.parties.get(cle)
        if p is None: p = self.parties[cle] = {'vu': self.horloge(), 'entrees': []}
        return p

    def synchroniser(self, cle, t):
        """A appeler a chaque image du jeu avec la cle de partie et le temps de jeu courants. Choisit la partie et retire les entrees d'un futur qui n'a plus eu lieu.
        - partie differente de la courante, ou temps qui recule de plus de MARGE_T : pris en compte seulement s'il dure CONFIRMATIONS images de suite ;
        - puis les entrees plus recentes que `t` sont retirees (la sauvegarde rechargee est plus ancienne que ces messages).
        Limites : le retour en arriere est detruit definitivement (recharger ensuite une sauvegarde plus recente ne les rend pas) ; la cle ne compte que 256 valeurs (deux aventures peuvent la partager : leurs
        historiques se melangent alors jusqu'au premier retour en arriere) ; une sauvegarde faite avant l'installation de l'historique n'a pas de messages avant elle."""
        if cle is None or t is None: return
        if self.cle is None:
            self.cle = cle; self._partie(cle); self._tronquer(t); self.dernier_t = t; self._cand = None; self._init_carte(); return
        chg = None
        if cle != self.cle: chg = ('cle', cle)
        elif self.dernier_t is not None and t + MARGE_T < self.dernier_t: chg = ('t', cle)
        if chg is None:
            self._cand = None; self.dernier_t = t; return
        if self._cand is not None and self._cand[0] == chg: n = self._cand[1] + 1
        else: n = 1
        self._cand = (chg, n)
        if n < CONFIRMATIONS: return
        self._cand = None
        if chg[0] == 'cle':
            self.enregistrer(True); self.cle = cle; self._partie(cle); self._elaguer_parties(); self._init_carte()
        self._tronquer(t); self.dernier_t = t

    def _tronquer(self, t):
        p = self._partie(self.cle); p['vu'] = self.horloge()
        avant = len(p['entrees'])
        p['entrees'] = [e for e in p['entrees'] if e.t <= t]
        if len(p['entrees']) != avant: self._sale = True
        self._init_carte()

    def _init_carte(self):
        self._carte_connue = None
        for e in reversed(self.parties.get(self.cle, {}).get('entrees', ())):
            if e.carte and lieu_de(e.carte) is not None: self._carte_connue = e.carte; break

    def ajouter(self, texte, genre, val, carte, t, cat=CAT_TERRAIN, anonyme=False):
        """Ajoute un message (texte brut du moteur) a la partie en cours ; -> l'Entree, ou None (vide, doublon, aucune partie)."""
        if self.cle is None: return None
        texte, anon = nettoyer(texte)
        if not texte: return None
        if genre == GENRE_GENERAL and (anonyme or anon): genre, val = GENRE_PERSO, None                  # « *: ... » sans personnage identifie
        if carte and lieu_de(carte) is not None: self._carte_connue = carte
        elif genre != GENRE_COMBAT: carte = self._carte_connue                                           # carte d'evenement / de combat : on garde le dernier lieu connu
        p = self._partie(self.cle); es = p['entrees']
        n = (es[-1].n + 1) if es else 1
        e = Entree(n, int(t), cat if cat in CATEGORIES else CAT_TERRAIN, genre, val, carte, texte)
        if es and doublon(es[-1], e): return None
        es.append(e)
        if len(es) > MAX_ENTREES: del es[:len(es) - MAX_ENTREES]
        p['vu'] = self.horloge(); self._sale = True
        return e

    # ---- liaison avec le moteur
    def maj(self, moteur, objets=None, noms=None):
        """Une fois par image du moteur : synchronise la partie / le temps de jeu, range les messages notes par le Capteur et ecrit le fichier si besoin (ecriture groupee)."""
        cap = getattr(moteur, 'capteur', None)
        if cap is None or not cap.actif: return
        try:
            jeu = moteur.etat.partie in (PARTIE_VILLE, PARTIE_COMBAT, PARTIE_CHAMP)
            recus = cap.vider()
            if not jeu: return
            t, uid = cap.temps_et_cle()
            if t is not None and not (t == 0 and uid == 0): self.synchroniser('%x' % uid, t)
            for r in recus:
                genre, val = r['genre'], r['val']
                if genre == GENRE_OBJET and isinstance(val, int): val = nom_objet(objets, noms, val)             # numero d'objet de la carte -> nom du modele
                self.ajouter(r['texte'], genre, val, r['carte'], r['t'], r['cat'], r.get('anonyme', False))
            self.enregistrer()
        except Exception as ex:                                              # l'historique ne doit jamais arreter le jeu
            if self.erreur is None: print('Historique des messages : erreur (%r)' % (ex,), flush=True)
            self.erreur = repr(ex)


def nom_objet(objets, noms, uid):
    """Nom du modele (« 015_hondana1 ») de l'objet de la carte courante dont le champ « uid » vaut `uid`. objets : liste des objets de la carte (donnees.carte(nom)['objets']) ; noms : numero d'objet -> nom. None si introuvable."""
    try:
        for o in objets or ():
            if o.get('uid') == uid and uid: return (noms or {}).get(o.get('i'))
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------------------------------------------------------------- crochets dans le moteur
class Capteur:
    """Crochets sur le moteur (Unicorn) : voir l'en-tete du module. Les messages notes attendent dans `sortie` jusqu'a ce que Historique.maj les prenne. Une erreur dans un crochet ne doit jamais arreter le moteur."""
    OFF_PLACEMENT = 0x29901c               # entier lu par getPlacementCtrlId() : emplacement de l'evenement dont le script s'execute (perime hors d'un script : voir _contexte)
    OFF_PERSONNAGES = 0x26a548             # TownCharacterManager::m_singleton : table des personnages de la ville (pointeurs a partir de +8) ; l'entier a +0x14 de chacun = numero de modele du sprite

    def __init__(self, moteur):
        self.actif = False; self.perso_ok = False; self.sortie = []; self._meuble = None
        self.m = moteur; c = self.c = moteur.core; self.L = moteur.L
        try:
            import unicorn
            self.g_game = c.export('_ZN6status6g_GameE'); cat = c.export('_ZN10TextBuffer3catEPKcS1_')
            if not self.g_game or not cat: return
            c.uc.hook_add(unicorn.UC_HOOK_CODE, self._cat, None, cat, cat)
            for nom in FONCTIONS_MOBILIER:
                a = c.export(nom)
                if a: c.uc.hook_add(unicorn.UC_HOOK_CODE, self._mobilier, None, a, a)
            self.perso_ok = self._verifier_emplacement()
            self.actif = True
        except Exception as ex:
            print('Historique des messages : crochets non installes (%r)' % (ex,), flush=True)

    def _verifier_emplacement(self):
        """Le moteur est celui qu'on a etudie : getPlacementCtrlId() lit bien l'entier a OFF_PLACEMENT (adrp + ldr). Sinon, on n'identifie pas les personnages (jamais de faux nom)."""
        try:
            a = self.c.export('_Z18getPlacementCtrlIdv')
            w0, w1 = struct.unpack('<2I', self.c.mem(a, 8))
            if w0 & 0x9f000000 != 0x90000000 or w1 & 0xffc00000 != 0xb9400000: return False
            immlo, immhi = (w0 >> 29) & 3, (w0 >> 5) & 0x7ffff
            imm = (immhi << 2) | immlo
            if imm & (1 << 20): imm -= 1 << 21
            page = ((a - self.L) & ~0xfff) + (imm << 12)
            return page + ((w1 >> 10) & 0xfff) * 4 == self.OFF_PLACEMENT
        except Exception:
            return False

    def temps_et_cle(self):
        """-> (temps de jeu en 1/60 s, identifiant de la partie) lus dans status::g_Game."""
        try:
            t, uid = struct.unpack('<2I', self.c.mem(self.g_game + 4, 8)); return t, uid
        except Exception:
            return None, 0

    def vider(self):
        s, self.sortie = self.sortie, []
        return s

    def _mobilier(self, uc, adr, taille, _):
        try:
            x0 = uc.reg_read(self.c.XREG[0])
            self._meuble = (struct.unpack('<i', self.c.mem(x0 + 0x10, 4))[0], self.m.images)
        except Exception:
            self._meuble = None

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

    def _contexte(self, uc, nom, e):
        """-> (genre, valeur, categorie) : qui parle, d'apres la pile d'appels (voir l'en-tete du module)."""
        pile = self._pile(uc)
        combat = e.partie == PARTIE_COMBAT or any('Battle' in s for s in pile)
        if nom: return GENRE_NOM, nom, CAT_COMBAT if combat else CAT_TERRAIN
        if combat: return GENRE_COMBAT, None, CAT_COMBAT
        for motif, lib in INSTALLATIONS:
            if any(motif in s for s in pile): return GENRE_INSTALLATION, lib, CAT_SYSTEME
        if any('TownFurniture' in s for s in pile) and self._meuble and 0 <= self.m.images - self._meuble[1] <= 600 and self._meuble[0] > 0:
            return GENRE_OBJET, self._meuble[0], CAT_TERRAIN
        if self.perso_ok and any('ScriptGroup7execute' in s for s in pile):
            try:
                pid = struct.unpack('<i', self.c.mem(self.L + self.OFF_PLACEMENT, 4))[0]
                if 1 <= pid < 0x30:                                                  # 0 = script global du scenario (narration) : pas de personnage
                    p, = struct.unpack('<Q', self.c.mem(self.L + self.OFF_PERSONNAGES + 8 + 8 * pid, 8))
                    modele = struct.unpack('<i', self.c.mem(p + 0x14, 4))[0] if p else -1
                    if modele >= 0: return GENRE_PERSO, modele, CAT_TERRAIN
            except Exception:
                pass
        return GENRE_GENERAL, None, CAT_TERRAIN

    def _cat(self, uc, adr, taille, _):
        try:
            c = self.c; x1, x2 = uc.reg_read(c.XREG[1]), uc.reg_read(c.XREG[2])
            texte = c.read_cstr(x1).decode('utf-8', 'replace') if x1 else ''
            if not texte.strip(): return
            nom = c.read_cstr(x2).decode('utf-8', 'replace').strip() if x2 else ''
            e = self.m.etat; genre, val, cat = self._contexte(uc, nom, e)
            t, _u = self.temps_et_cle()
            carte = 'monde' if e.partie == PARTIE_CHAMP else e.carte
            self.sortie.append({'texte': texte, 'genre': genre, 'val': val, 'cat': cat, 'carte': carte, 't': t or 0})
            if len(self.sortie) > 500: del self.sortie[:250]                      # (jamais vide faute de Historique.maj : on ne grossit pas sans fin)
        except Exception:
            pass
