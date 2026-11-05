"""Capture des resultats des combats pour l'historique des combats : ennemis vaincus, or gagne, experience gagnee.

    capteur = CapteurCombat(moteur)         # une fois, apres la creation du Moteur (installe des crochets en LECTURE SEULE dans l'emulateur ; n'ecrit rien dans la memoire du moteur)
    for combat in capteur.maj(moteur): ...  # UNE fois par image du moteur, apres moteur.step ; renvoie les combats TERMINES a cette image (le plus souvent une liste vide)

Chaque combat : {'t': temps de jeu a la fin (1/60 s, status::g_Game + 4), 'ennemis': [{'nom': 'Gluant', 'total': 3, 'vaincus': 1, 'fuis': 1, 'disparus': 0}, ...] (un element par espece, dans l'ordre
d'apparition ; ce qui reste, total - vaincus - fuis - disparus, est encore la quand le combat se termine : fuite ou defaite du groupe), 'or': int, 'xp': int, 'issue': 'victoire' | 'fuite' | 'defaite',
'objets': [{'nom': 'Herbe médicinale'}, ...] (les objets que le jeu donne au groupe a la fin du combat : « Le gluant laisse tomber un coffre au trésor ! »)}. Or et experience : ceux du message de victoire
du jeu, 0 pour une fuite ou une defaite (le moteur ne les verse pas).

Methode (ETABLI par lecture du moteur desassemble puis par mesure : voir outils/test_historique_combat.py) :
- Les MORTS sont notees par un crochet sur BattleActorManager2::execMonsterDeath(this, i), la fonction que le jeu appelle une fois par monstre vaincu (pas pour un monstre qui s'enfuit ou disparait) et qui ajoute
  l'experience du monstre a g_Party + 0x2f8 et son or a g_Party + 0x2fc. Ce sont ces deux compteurs que BattleExecVictory01 / BattleExecVictory20 lisent pour fabriquer les messages « N points d'experience » et « N pieces d'or »
  (getBattleExp / getBattleGold, apres le doublement eventuel de reflectBattleExp / reflectBattleGold) : on prend donc le plus grand de leurs relevés d'une image a l'autre, jusqu'a leur remise a zero.
- Les monstres qui S'ENFUIENT et ceux qui DISPARAISSENT sont notes par deux crochets au milieu de BattleActorManager2::checkDeathMonster (la routine qui, a chaque image, passe en revue les monstres morts,
  enfuis ou disparus ; elle les compte inline dans +0x7d24 / +0x7d28, les lit BattleEndTask::initialize, et n'appelle execMonsterDeath que pour un mort) : juste avant l'incrementation du compteur de fuites
  (+0x98, `ldr w8, [x23, #0xd24]`) et de disparitions (+0xc0, `ldr w8, [x23, #0xd28]`), w20 est l'indice du monstre (meme indice que pour execMonsterDeath). Chaque monstre n'y passe qu'une fois
  (un masque des monstres deja traites, +0xd30, l'en protege).
- Les OBJETS gagnes sont donnes par BattleExecVictory32::setup (la tache qui suit la victoire : « laisse tomber un coffre au trésor ! », « Ragnar l'ouvre. », « Il contient un arc de chasseur ! ») : elle appelle
  PartyStatus::giveItem(objet = tache + 0xc), qui renvoie l'indice du membre qui le prend, ou -1 quand il va dans le sac (mesure : « Ragnar met l'arc de chasseur dans le sac. » avec -1) ; dans les deux cas l'objet est
  obtenu. Crochet juste apres l'appel (+0x28, `cmn w0, #1`) : x20 = la tache. NON VERIFIE : ce que fait le jeu quand le sac lui-meme est plein. Le nom de l'objet est demande au
  moteur lui-meme (TextAPI::extractText(tampon, 0x4000000 | numero), ce que le jeu fait pour la macro « nom d'objet »), entre deux images, jamais dans un crochet ; le « ; » (marque de coupure des noms du patch) est retire.
- Le DEBUT est PartyStatus::startBattle, la FIN est Global::endBattle(bool) (argument vrai = groupe anéanti), la VICTOIRE BattleExecDefeatMonster::initialize (la routine « tous les ennemis sont vaincus »,
  qui verse l'experience), la FUITE BattleExecEscape::setup (appelee a chaque TENTATIVE de fuite, reussie ou non : la fuite reussie est donc « tentative faite, pas de victoire, combat termine »).
- Les ENNEMIS sont relevés a chaque image dans g_Monster (12 emplacements de 0x538 octets a partir de +8 ; +0x4f8 = numero du monstre, -1 si vide ; +0x4fc = numero du groupe) : un monstre = un emplacement occupe ;
  l'espece est le numero du monstre. Les renforts appeles en cours de combat s'ajoutent au total.
- Les NOMS sont ceux des plaques de monstres que le moteur envoie a Unity (Moteur.ui, fenetre de type 31 : « Rat volant », « Gluant\\n\\n\\t×3 » -> « Gluant »), associes aux groupes dans l'ordre (la plaque j porte le
  j-ieme groupe), seulement quand il y a autant de plaques que de groupes et avant la premiere mort. Sans plaque (attaque surprise : le jeu n'en affiche pas ; plaques d'un autre nombre de groupes), le nom
  est demande au moteur lui-meme a la fin du combat, par le numero du monstre (TextAPI::extractText(tampon, 0x6000000 | numero) : « londuleux », « armure ;errante », « scara$somniaque » -> « Londuleux »,
  « Armure errante », « Scara-somniaque ») ; « Monstre » si le moteur ne repond pas.
Tout est protege : une erreur ne renvoie rien et ne s'ecrit qu'une fois dans la console. Un combat dont on n'a pas vu le debut (etat instantane charge en plein combat, capteur cree pendant un combat) n'est jamais
rapporte : mieux vaut ne rien dire que de dire faux."""
import re, struct
from dq4_pc.langue import tr, N_

PARTIE_COMBAT = 0xd
NB_EMPLACEMENTS = 12                   # g_Monster : 12 monstres au plus
DEBUT_MONSTRES, PAS_MONSTRE = 8, 0x538 # g_Monster + 8 : tableau de MonsterStatus
OFF_NUMERO, OFF_GROUPE = 0x4f8, 0x4fc  # dans un MonsterStatus : numero du monstre (-1 = emplacement vide), numero du groupe de la rencontre
OFF_XP, OFF_OR = 0x2f8, 0x2fc         # dans g_Party : experience et or du combat en cours (versees a la victoire)
OFF_DEFAITE = 0x509                    # g_BattleResult + 0x509 : le groupe a perdu (ExitTask::terminate le teste avant d'appeler endBattle)
INCONNU = 0xffffffff
NOM_INCONNU = N_('Monstre')                      # (nom de remplacement quand le moteur ne repond pas : traduit a la capture, voir CapteurCombat)
ISSUES = ('victoire', 'fuite', 'defaite')
MAX_IMAGES_SANS_COMBAT = 20            # images de suite hors de la partie « combat » avant d'abandonner un suivi (la fin normale arrive toujours avant le changement de partie)
MAX_SAUT_IMAGES = 8                    # ecart maximal de Moteur.images entre deux appels de maj sans parler de rupture (etat instantane charge...)

# crochets (symboles du moteur) : evenement -> nom
CROCHETS = (('debut', '_ZN6status11PartyStatus11startBattleEv'), ('mort', '_ZN19BattleActorManager216execMonsterDeathEi'), ('victoire', '_ZN23BattleExecDefeatMonster10initializeEv'),
            ('fuite', '_ZN16BattleExecEscape5setupEv'), ('fin', '_ZN6Global9endBattleEb'))
# crochets au MILIEU d'une fonction : (evenement, symbole, decalage, instruction attendue a cet endroit). L'instruction est verifiee avant d'installer le crochet : un moteur different ne recoit pas de crochet
# au hasard (seul l'evenement correspondant est alors perdu, la capture continue).
SYM_CONTROLE_MORTS = '_ZN19BattleActorManager217checkDeathMonsterEv'
SYM_OBJET_GAGNE = '_ZN19BattleExecVictory325setupEv'
CROCHETS_INTERNES = (('monstre_enfui', SYM_CONTROLE_MORTS, 0x98, 0xb94d26e8),         # ldr w8, [x23, #0xd24] : compteur de fuites de monstres
                     ('monstre_disparu', SYM_CONTROLE_MORTS, 0xc0, 0xb94d2ae8),       # ldr w8, [x23, #0xd28] : compteur de disparitions
                     ('objet', SYM_OBJET_GAGNE, 0x28, 0x3100041f))                    # cmn w0, #1 : juste apres PartyStatus::giveItem
SYM_NOM_OBJET = '_ZN7TextAPI11extractTextEPci'
GENRE_OBJET = 0x4000000                                                              # « nom d'objet » dans les macros de texte du jeu (setMACRO0(0xa, 0x4000000, numero))
GENRE_MONSTRE = 0x6000000                                                            # « nom de monstre » (BattleActorMacro::setMacroActor : setMACRO0(1, 0x6000000, numero de monstre))
OFF_OBJET_TACHE = 0xc                                                                # BattleExecVictory32 : numero de l'objet a donner
NOM_OBJET_INCONNU = N_('Objet n°%d')


# ---------------------------------------------------------------------------------------------------------------------------------- partie pure (sans emulateur)
def nom_de_plaque(texte):
    """Nom affiche sur une plaque de monstre ; None si vide. Le jeu ecrit « Gluant\\n\\n\\t×3 » (la mention du nombre, qui commence par une tabulation, est retiree) et coupe les noms longs sur deux lignes :
    « Armure \\n\\nerrante » -> « Armure errante » ; « Scara-\\n\\nsomniaque » -> « Scara-somniaque » (un tiret en fin de ligne est recolle sans espace). Limite : « Psaro l'Exter-\\n\\nminateur » donne
    « Psaro l'Exter-minateur » (le moteur ne dit pas si le tiret est une coupure de mot ou un vrai trait d'union)."""
    if not isinstance(texte, str): return None
    nom = ''
    for brut in texte.replace('\r', '').split('\n'):
        if brut.startswith('\t'): break                                                 # « \t×3 » : le nombre de monstres du groupe
        ligne = ''.join(ch for ch in brut if ch >= ' ' and ch != '\x7f').strip()
        if not ligne: continue
        if re.fullmatch(r'×\s*\d+', ligne): break
        nom = ligne if not nom else (nom + ligne if nom.endswith('-') else nom + ' ' + ligne)
    return nom or None


def noms_des_groupes(groupes, plaques):
    """Associe les noms des plaques aux monstres. groupes : [(numero de groupe, numero de monstre)] des emplacements occupes ; plaques : [nom, ...] dans l'ordre des plaques (la plaque j = le j-ieme groupe,
    les groupes etant pris dans l'ordre de leur numero). -> {numero de monstre: nom} ; {} si le nombre de plaques n'est pas celui des groupes (on n'invente pas)."""
    ordre = sorted({g for g, _m in groupes})
    noms = [nom_de_plaque(p) for p in plaques]
    if not ordre or len(ordre) != len(noms) or any(n is None for n in noms): return {}
    par_groupe = {}
    for g, m in groupes: par_groupe.setdefault(g, m)
    return {par_groupe[g]: n for g, n in zip(ordre, noms)}


def _monstre(num): return {'num': num, 'vaincu': False, 'fui': False, 'disparu': False}


def _sort_de(m): return m['vaincu'] or m['fui'] or m['disparu']


class Suivi:
    """Ce que l'on sait d'un combat en cours (donnees pures : aucune dependance au moteur ; voir CapteurCombat pour la lecture de la memoire)."""

    def __init__(self):
        self.monstres = []             # un par monstre vu, dans l'ordre d'apparition : {'num': numero du monstre, 'vaincu': bool, 'fui': bool, 'disparu': bool} (au plus un des trois)
        self.objets = []               # objets gagnes : {'id': numero, 'nom': nom}, dans l'ordre
        self.places = {}               # emplacement -> indice dans monstres (occupant actuel)
        self.noms = {}                 # numero de monstre -> nom
        self.morts = 0                 # monstres vaincus (crochet execMonsterDeath)
        self.victoire = False          # BattleExecDefeatMonster::initialize a eu lieu
        self.tentatives_fuite = 0      # BattleExecEscape::setup (reussie ou non)
        self.xp = 0; self.or_ = 0      # plus grands relevés des compteurs du groupe (g_Party + 0x2f8 / 0x2fc)

    def voir(self, occupants):
        """Un relevé des emplacements : occupants = [(emplacement, numero de monstre)] des emplacements occupes. Un nouvel occupant (emplacement libre qui se remplit, ou autre numero) est un nouveau monstre ;
        un emplacement qui se vide est oublie (le monstre vaincu ou parti est deja compte)."""
        vus = set()
        for e, num in occupants:
            vus.add(e); i = self.places.get(e)
            if i is None or self.monstres[i]['num'] != num:
                self.monstres.append(_monstre(num)); self.places[e] = len(self.monstres) - 1
        for e in [e for e in self.places if e not in vus]: del self.places[e]

    def _sort(self, cle, emplacement, num):
        """Le jeu declare que le monstre de cet emplacement est vaincu / enfui / disparu (cle : 'vaincu', 'fui' ou 'disparu'). Un monstre jamais vu (parti dans l'image de son apparition) est ajoute, de meme qu'un monstre
        dont le sort est deja note (autre monstre arrive dans le meme emplacement)."""
        i = self.places.get(emplacement)
        if i is None or self.monstres[i]['num'] != num or _sort_de(self.monstres[i]):
            self.monstres.append(_monstre(num)); i = len(self.monstres) - 1; self.places[emplacement] = i
        self.monstres[i][cle] = True

    def mort(self, emplacement, num):
        """Le jeu declare vaincu le monstre de cet emplacement (crochet execMonsterDeath)."""
        self.morts += 1; self._sort('vaincu', emplacement, num)

    def enfui(self, emplacement, num):
        """Le monstre de cet emplacement s'est enfui (le jeu le compte dans checkDeathMonster)."""
        self._sort('fui', emplacement, num)

    def disparu(self, emplacement, num):
        """Le monstre de cet emplacement a disparu (idem)."""
        self._sort('disparu', emplacement, num)

    def objet(self, numero, nom):
        """Le jeu donne un objet au groupe a la fin du combat."""
        self.objets.append({'id': int(numero), 'nom': nom})

    def compteurs(self, xp, or_):
        """Relevé des compteurs d'experience et d'or du combat : ils ne font que croitre (doublement compris) jusqu'a leur remise a zero apres le message ; on garde le plus grand."""
        if xp > self.xp: self.xp = xp
        if or_ > self.or_: self.or_ = or_

    def nommer(self, noms):
        for num, nom in noms.items(): self.noms.setdefault(num, nom)

    def nombre_presents(self): return len(self.places)

    def issue(self, defaite=False):
        """Issue du combat a sa fin : la routine de victoire du jeu a tourne (victoire) ; sinon le groupe est anéanti (defaite) ; sinon tous les monstres vus sont vaincus (victoire) ; sinon le groupe est parti (fuite)."""
        if self.victoire: return 'victoire'
        if defaite: return 'defaite'
        if self.morts > 0 and all(_sort_de(m) for m in self.monstres): return 'victoire'
        return 'fuite'

    def ennemis(self):
        """[{'nom', 'total', 'vaincus', 'fuis', 'disparus'}] une entree par espece (meme nom, ou meme numero quand le nom est inconnu), dans l'ordre de la premiere apparition."""
        especes = {}
        for m in self.monstres:
            nom = self.noms.get(m['num'])
            cle = ('n', nom) if nom else ('?', m['num'])
            e = especes.setdefault(cle, {'nom': nom or tr(NOM_INCONNU), 'total': 0, 'vaincus': 0, 'fuis': 0, 'disparus': 0})
            e['total'] += 1; e['vaincus'] += 1 if m['vaincu'] else 0; e['fuis'] += 1 if m['fui'] else 0; e['disparus'] += 1 if m['disparu'] else 0
        return list(especes.values())


def fabriquer_combat(suivi, t, defaite=False):
    """Le combat termine : dict de l'API (voir l'en-tete du module). Or et experience ne comptent que pour une victoire."""
    issue = suivi.issue(defaite)
    gagne = issue == 'victoire'
    return {'t': int(t), 'ennemis': suivi.ennemis(), 'or': int(suivi.or_) if gagne else 0, 'xp': int(suivi.xp) if gagne else 0, 'issue': issue,
            'objets': [{'nom': o['nom']} for o in suivi.objets] if gagne else []}


# ---------------------------------------------------------------------------------------------------------------------------------- lecture du moteur
def _ldr_w(mot, base=0):
    """Decalage d'un `ldr wN, [xM, #imm]` (acces 32 bits, offset non signe) ; None si ce n'est pas cette instruction."""
    if mot & 0xffc00000 != 0xb9400000 or (mot >> 5) & 31 != base: return None
    return ((mot >> 10) & 0xfff) * 4


_PAR_MOTEUR = {}                                                                         # (secours si le moteur refuse un attribut en plus : id -> (moteur, capteur))


class CapteurCombat:
    def __init__(self, moteur):
        self.actif = False; self.erreur = None
        self.suivi = None; self.sorties = []; self.evenements = []; self._noms_objets = {}; self._noms_monstres = {}; self._tampon = None
        self._etat = None; self._image = -10 ** 9; self._hors_combat = 0; self._anciennes = {}
        self.m = moteur
        try:
            import unicorn
            c = self.c = moteur.core
            self.g_party = c.export('_ZN6status7g_PartyE'); self.g_monster = c.export('_ZN6status9g_MonsterE'); self.g_game = c.export('_ZN6status6g_GameE'); self.g_result = c.export('_ZN6status14g_BattleResultE')
            if not (self.g_party and self.g_monster and self.g_game and self.g_result) or not self._verifier():
                print(tr('Historique des combats : moteur inattendu, capture desactivee'), flush=True); return
            for evt, nom in CROCHETS:
                a = c.export(nom)
                if not a: print(tr('Historique des combats : %s introuvable, capture desactivee') % nom, flush=True); return
            for evt, nom in CROCHETS: c.uc.hook_add(unicorn.UC_HOOK_CODE, self._crochet(evt), None, c.export(nom), c.export(nom))
            for evt, nom, off, mot in CROCHETS_INTERNES:                               # (en cas de moteur different, seul cet evenement est perdu)
                a = c.export(nom)
                if not a or struct.unpack('<I', c.mem(a + off, 4))[0] != mot:
                    print(tr('Historique des combats : %s inattendu (+%#x), « %s » non suivi') % (nom, off, evt), flush=True); continue
                c.uc.hook_add(unicorn.UC_HOOK_CODE, self._crochet(evt), None, a + off, a + off)
            try: c.uc.ctl_flush_tb()                                                    # (blocs deja traduits avant les crochets : un capteur cree apres quelques combats)
            except Exception: pass
            self.actif = True
        except Exception as ex:
            self.erreur = repr(ex); print(tr('Historique des combats : crochets non installes (%r)') % (ex,), flush=True)

    @classmethod
    def pour(cls, moteur):
        """Le capteur de ce moteur : cree a la premiere demande, toujours le meme ensuite (les crochets ne sont installes qu'une fois). Permet de n'ajouter qu'UNE ligne a la boucle d'images, sans rien
        creer ailleurs : `for combat in CapteurCombat.pour(mo).maj(mo): ...` juste apres `mo.step`."""
        c = getattr(moteur, '_capteur_combat', None) or _PAR_MOTEUR.get(id(moteur), (None, None))[1]
        if c is None:
            c = cls(moteur)
            try: moteur._capteur_combat = c
            except Exception: _PAR_MOTEUR[id(moteur)] = (moteur, c)
        return c

    # ---- verification : le moteur est celui qu'on a etudie
    def _verifier(self):
        """Les structures lues sont celles du moteur etudie : getBattleExp / getBattleGold lisent bien g_Party + 0x2f8 / 0x2fc, MonsterStatus::isEnable lit bien +0x4f8 (numero de monstre)."""
        try:
            c = self.c
            def decalage(nom):
                a = c.export(nom)
                return _ldr_w(struct.unpack('<I', c.mem(a, 4))[0]) if a else None
            return (decalage('_ZN6status15BasePartyStatus12getBattleExpEv') == OFF_XP and decalage('_ZN6status15BasePartyStatus13getBattleGoldEv') == OFF_OR
                    and decalage('_ZN6status13MonsterStatus8isEnableEv') == OFF_NUMERO)
        except Exception:
            return False

    def _crochet(self, evt):
        def cb(uc, adr, taille, _):
            try:
                c = self.c
                if evt == 'mort':
                    i = uc.reg_read(c.XREG[1]) & 0xffffffff                              # indice dans les monstres PRESENTS (getMonsterStatus compte les emplacements occupes), pas l'emplacement
                    occ = self._occupes()
                    if 0 <= i < len(occ): self.evenements.append(('mort', occ[i][0], occ[i][1], occ[i][2]))
                elif evt in ('monstre_enfui', 'monstre_disparu'):
                    i = uc.reg_read(c.XREG[20]) & 0xffffffff                              # w20 : indice du monstre dans la boucle de checkDeathMonster (meme indice que pour execMonsterDeath)
                    occ = self._occupes()
                    if 0 <= i < len(occ): self.evenements.append((evt, occ[i][0], occ[i][1]))
                elif evt == 'objet':
                    tache = uc.reg_read(c.XREG[20]) & 0xffffffffffff                      # x20 : la tache BattleExecVictory32 (le numero de l'objet est a +0xc)
                    self.evenements.append(('objet', struct.unpack('<I', c.mem(tache + OFF_OBJET_TACHE, 4))[0]))
                elif evt == 'fin':
                    self.evenements.append(('fin', bool(uc.reg_read(c.XREG[1]) & 1), c.mem(self.g_result + OFF_DEFAITE, 1)[0] == 1))
                else: self.evenements.append((evt,))
                if len(self.evenements) > 200: del self.evenements[:100]               # (garde-fou si maj n'est jamais appelee)
            except Exception:
                pass
        return cb

    def _occupes(self):
        """[(emplacement, numero de monstre, numero de groupe)] des emplacements occupes de g_Monster, dans l'ordre des emplacements."""
        brut = self.c.mem(self.g_monster + DEBUT_MONSTRES, NB_EMPLACEMENTS * PAS_MONSTRE)
        out = []
        for e in range(NB_EMPLACEMENTS):
            num, grp = struct.unpack_from('<2I', brut, e * PAS_MONSTRE + OFF_NUMERO)
            if num != INCONNU and num < 4096: out.append((e, num, grp))
        return out

    def temps(self):
        """Temps de jeu en 1/60 s (status::g_Game + 4, comme historique.Capteur.temps_et_cle)."""
        try: return struct.unpack('<I', self.c.mem(self.g_game + 4, 4))[0]
        except Exception: return 0

    # ---- une image
    def maj(self, moteur):
        """A appeler UNE fois par image du moteur, apres moteur.step. -> liste des combats termines a cette image (dicts de l'API)."""
        if not self.actif: return []
        try:
            etat, image = moteur.etat, moteur.images
            rupture = etat is not self._etat or not 0 < image - self._image <= MAX_SAUT_IMAGES
            self._etat = etat; self._image = image
            if rupture and (self.suivi is not None):                                       # etat instantane charge (ou images sautees) : le combat suivi n'est plus celui de la memoire
                self.suivi = None
            if self.suivi is None and not self.evenements and etat.partie != PARTIE_COMBAT: return []        # hors combat : rien d'autre a faire (chemin le plus frequent)
            ev, self.evenements = self.evenements, []
            for e in ev: self._evenement(e)
            if self.suivi is not None: self._observer(moteur)
            if self.sorties: out, self.sorties = self.sorties, []; return out
            return []
        except Exception as ex:                                                              # la capture ne doit jamais arreter le jeu
            if self.erreur is None: print(tr('Historique des combats : erreur (%r)') % (ex,), flush=True)
            self.erreur = repr(ex); self.suivi = None; self.evenements = []
            return []

    def _evenement(self, e):
        nom = e[0]
        if nom == 'debut':
            self.suivi = Suivi(); self._hors_combat = 0; self._anciennes = self._plaques()                       # (plaques deja la : celles du combat precedent, a ne pas lire)
        elif self.suivi is None: return                                                    # combat dont on n'a pas vu le debut : ignore
        elif nom == 'mort': self.suivi.mort(e[1], e[2])
        elif nom == 'monstre_enfui': self.suivi.enfui(e[1], e[2])
        elif nom == 'monstre_disparu': self.suivi.disparu(e[1], e[2])
        elif nom == 'objet': self.suivi.objet(e[1], self._nom_objet(e[1]))
        elif nom == 'victoire': self.suivi.victoire = True
        elif nom == 'fuite': self.suivi.tentatives_fuite += 1
        elif nom == 'fin':
            s, self.suivi = self.suivi, None
            for m in s.monstres:                                                          # monstres sans plaque (attaque surprise...) : le nom vient du moteur, par le numero
                if m['num'] not in s.noms:
                    n = self._nom_monstre(m['num'])
                    if n: s.nommer({m['num']: n})
            self.sorties.append(fabriquer_combat(s, self.temps(), defaite=e[1] or e[2]))

    def _observer(self, moteur):
        """Relevé de l'image pour le combat suivi : emplacements, compteurs, noms."""
        s = self.suivi
        if moteur.etat.partie != PARTIE_COMBAT:
            self._hors_combat += 1
            if self._hors_combat > MAX_IMAGES_SANS_COMBAT: self.suivi = None                # on a quitte le combat sans passer par endBattle (retour au titre...) : abandon
            return
        self._hors_combat = 0
        occ = self._occupes()
        s.voir([(e, num) for e, num, _g in occ])
        xp, or_ = struct.unpack('<2I', self.c.mem(self.g_party + OFF_XP, 8))
        s.compteurs(xp, or_)
        if occ and s.morts == 0 and any(n not in s.noms for _e, n, _g in occ): self._noms(s, occ)

    def _texte_moteur(self, genre, numero):
        """Texte que le moteur donne pour (genre, numero) -- TextAPI::extractText, ce que le jeu appelle pour une macro de nom -- ; None sans reponse. Appele entre deux images (maj), jamais depuis un crochet.
        Le « ; » (coupure des noms du patch) est retire, le « $ » (coupure avec trait d'union) devient un tiret."""
        try:
            c = self.c; f = c.export(SYM_NOM_OBJET)
            if not f: return None
            if self._tampon is None: self._tampon = c.malloc(256)
            c.mem_w(self._tampon, b'\0' * 16)
            c.call(f, self._tampon, genre | numero, label='nom du moteur')
            t = c.read_cstr(self._tampon).decode('utf-8', 'replace').replace(';', '').replace('$', '-').strip()
            return t if t and not t.startswith('<ERR') else None
        except Exception:
            return None

    def _nom_objet(self, numero):
        """Nom de l'objet (le nom que le jeu affiche) ; garde. Sans reponse : « Objet n°12 »."""
        nom = self._noms_objets.get(numero)
        if nom is None: nom = self._noms_objets[numero] = self._texte_moteur(GENRE_OBJET, numero) or tr(NOM_OBJET_INCONNU) % numero
        return nom

    def _nom_monstre(self, numero):
        """Nom du monstre, avec une majuscule (le moteur donne le nom comme dans une phrase : « londuleux ») ; garde. None sans reponse."""
        nom = self._noms_monstres.get(numero)
        if nom is None:
            t = self._texte_moteur(GENRE_MONSTRE, numero)
            nom = self._noms_monstres[numero] = (t[:1].upper() + t[1:]) if t else ''
        return nom or None

    def _plaques(self):
        """{fenetre: (dict de chaque plaque, ...)} des plaques de monstres que Moteur.ui a en memoire (fenetre de type 31). On garde les objets eux-memes : le moteur en cree de nouveaux a chaque rafraichissement."""
        out = {}
        try:
            for port, f in self.m.ui.f.items():
                if f.get('type') != 31: continue
                plaq, dispo = f.get('plaq') or {}, f.get('dispo')
                if isinstance(dispo, int) and 1 <= dispo <= 4 and all(j in plaq for j in range(dispo)): out[port] = tuple(plaq[j] for j in range(dispo))
        except Exception:
            pass
        return out

    def _noms(self, s, occ):
        """Noms des plaques de monstres envoyees par le moteur a Unity, tant qu'aucun monstre n'est vaincu. Seules comptent les plaques arrivees depuis le debut de ce combat (objets differents de ceux d'alors)."""
        for port, cur in self._plaques().items():
            ancien = self._anciennes.get(port)
            if ancien is not None and len(ancien) == len(cur) and all(a is b for a, b in zip(ancien, cur)): continue
            res = noms_des_groupes([(g, n) for _e, n, g in occ], [p.get('nom') for p in cur])
            if res: s.nommer(res); self._anciennes[port] = cur
