"""Capture des resultats des combats pour l'historique des combats : ennemis vaincus, or gagne, experience gagnee.

    capteur = BattleSensor(moteur)         # une fois, apres la creation du Moteur (installe des crochets en LECTURE SEULE dans l'emulateur ; n'ecrit rien dans la memoire du moteur)
    for combat in capteur.maj(moteur): ...  # UNE fois par image du moteur, apres moteur.step ; renvoie les combats TERMINES a cette image (le plus souvent une liste vide)

Chaque combat : {'t': temps de jeu a la fin (1/60 s, status::g_Game + 4), 'ennemis': [{'nom': 'Gluant', 'total': 3, 'vaincus': 1, 'fuis': 1, 'disparus': 0}, ...] (un element par espece, dans l'ordre
d'apparition ; ce qui reste, total - vaincus - fuis - disparus, est encore la quand le combat se termine : fuite ou defaite du groupe), 'or': int, 'xp': int, 'issue': 'victoire' | 'fuite' | 'defaite',
'objets': [{'nom': 'Herbe médicinale'}, ...] (les objets que le jeu donne au groupe a la fin du combat : « Le gluant laisse tomber un coffre au trésor ! »)}. Or et experience : ceux du message de victoire
du jeu, 0 pour une fuite ou une defaite (le moteur ne les verse pas).

Methode (ETABLI par lecture du moteur desassemble puis par mesure : voir tools/test_battle_history.py) :
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
- Les NOMS sont ceux des plaques de monstres que le moteur envoie a Unity (Engine.ui, fenetre de type 31 : « Rat volant », « Gluant\\n\\n\\t×3 » -> « Gluant »), associes aux groupes dans l'ordre (la plaque j porte le
  j-ieme groupe), seulement quand il y a autant de plaques que de groupes et avant la premiere mort. Sans plaque (attaque surprise : le jeu n'en affiche pas ; plaques d'un autre nombre de groupes), le nom
  est demande au moteur lui-meme a la fin du combat, par le numero du monstre (TextAPI::extractText(tampon, 0x6000000 | numero) : « londuleux », « armure ;errante », « scara$somniaque » -> « Londuleux »,
  « Armure errante », « Scara-somniaque ») ; « Monstre » si le moteur ne repond pas.
Tout est protege : une erreur ne renvoie rien et ne s'ecrit qu'une fois dans la console. Un combat dont on n'a pas vu le debut (etat instantane charge en plein combat, capteur cree pendant un combat) n'est jamais
rapporte : mieux vaut ne rien dire que de dire faux."""
import re, struct
from dq4_pc.language import tr, N_

PART_BATTLE = 0xd
SLOT_COUNT = 12                   # g_Monster : 12 monstres au plus
MONSTERS_START, MONSTER_STEP = 8, 0x538 # g_Monster + 8 : tableau de MonsterStatus
OFF_NUMBER, OFF_GROUP = 0x4f8, 0x4fc  # dans un MonsterStatus : numero du monstre (-1 = emplacement vide), numero du groupe de la rencontre
OFF_XP, OFF_GOLD = 0x2f8, 0x2fc         # dans g_Party : experience et or du combat en cours (versees a la victoire)
OFF_DEFEAT = 0x509                    # g_BattleResult + 0x509 : le groupe a perdu (ExitTask::terminate le teste avant d'appeler endBattle)
UNKNOWN = 0xffffffff
UNKNOWN_NAME = N_('Monstre')                      # (nom de remplacement quand le moteur ne repond pas : traduit a la capture, voir BattleSensor)
OUTCOMES = ('victoire', 'fuite', 'defaite')
MAX_FRAMES_WITHOUT_BATTLE = 20            # images de suite hors de la partie « combat » avant d'abandonner un suivi (la fin normale arrive toujours avant le changement de partie)
MAX_JUMP_FRAMES = 8                    # ecart maximal de Engine.images entre deux appels de maj sans parler de rupture (etat instantane charge...)

# crochets (symboles du moteur) : evenement -> nom
HOOKS = (('debut', '_ZN6status11PartyStatus11startBattleEv'), ('mort', '_ZN19BattleActorManager216execMonsterDeathEi'), ('victoire', '_ZN23BattleExecDefeatMonster10initializeEv'),
            ('fuite', '_ZN16BattleExecEscape5setupEv'), ('fin', '_ZN6Global9endBattleEb'))
# crochets au MILIEU d'une fonction : (evenement, symbole, decalage, instruction attendue a cet endroit). L'instruction est verifiee avant d'installer le crochet : un moteur different ne recoit pas de crochet
# au hasard (seul l'evenement correspondant est alors perdu, la capture continue).
SYM_DEATH_CHECK = '_ZN19BattleActorManager217checkDeathMonsterEv'
SYM_ITEM_WON = '_ZN19BattleExecVictory325setupEv'
INTERNAL_HOOKS = (('monstre_enfui', SYM_DEATH_CHECK, 0x98, 0xb94d26e8),         # ldr w8, [x23, #0xd24] : compteur de fuites de monstres
                     ('monstre_disparu', SYM_DEATH_CHECK, 0xc0, 0xb94d2ae8),       # ldr w8, [x23, #0xd28] : compteur de disparitions
                     ('objet', SYM_ITEM_WON, 0x28, 0x3100041f))                    # cmn w0, #1 : juste apres PartyStatus::giveItem
SYM_ITEM_NAME = '_ZN7TextAPI11extractTextEPci'
KIND_ITEM = 0x4000000                                                              # « nom d'objet » dans les macros de texte du jeu (setMACRO0(0xa, 0x4000000, numero))
KIND_MONSTER = 0x6000000                                                            # « nom de monstre » (BattleActorMacro::setMacroActor : setMACRO0(1, 0x6000000, numero de monstre))
OFF_TASK_ITEM = 0xc                                                                # BattleExecVictory32 : numero de l'objet a donner
UNKNOWN_ITEM_NAME = N_('Objet n°%d')


# ---------------------------------------------------------------------------------------------------------------------------------- partie pure (sans emulateur)
def plate_name(text):
    """Nom affiche sur une plaque de monstre ; None si vide. Le jeu ecrit « Gluant\\n\\n\\t×3 » (la mention du nombre, qui commence par une tabulation, est retiree) et coupe les noms longs sur deux lignes :
    « Armure \\n\\nerrante » -> « Armure errante » ; « Scara-\\n\\nsomniaque » -> « Scara-somniaque » (un tiret en fin de ligne est recolle sans espace). Limite : « Psaro l'Exter-\\n\\nminateur » donne
    « Psaro l'Exter-minateur » (le moteur ne dit pas si le tiret est une coupure de mot ou un vrai trait d'union)."""
    if not isinstance(text, str): return None
    name_str = ''
    for raw_value in text.replace('\r', '').split('\n'):
        if raw_value.startswith('\t'): break                                                 # « \t×3 » : le nombre de monstres du groupe
        line = ''.join(ch for ch in raw_value if ch >= ' ' and ch != '\x7f').strip()
        if not line: continue
        if re.fullmatch(r'×\s*\d+', line): break
        name_str = line if not name_str else (name_str + line if name_str.endswith('-') else name_str + ' ' + line)
    return name_str or None


def group_names(groups, plates):
    """Associe les noms des plaques aux monstres. groupes : [(numero de groupe, numero de monstre)] des emplacements occupes ; plaques : [nom, ...] dans l'ordre des plaques (la plaque j = le j-ieme groupe,
    les groupes etant pris dans l'ordre de leur numero). -> {numero de monstre: nom} ; {} si le nombre de plaques n'est pas celui des groupes (on n'invente pas)."""
    order = sorted({g for g, _m in groups})
    names = [plate_name(p) for p in plates]
    if not order or len(order) != len(names) or any(n is None for n in names): return {}
    by_group = {}
    for g, m in groups: by_group.setdefault(g, m)
    return {by_group[g]: n for g, n in zip(order, names)}


def _monster(num): return {'num': num, 'vaincu': False, 'fui': False, 'disparu': False}


def _is_gone(m): return m['vaincu'] or m['fui'] or m['disparu']


class Tracking:
    """Ce que l'on sait d'un combat en cours (donnees pures : aucune dependance au moteur ; voir BattleSensor pour la lecture de la memoire)."""

    def __init__(self):
        self.monsters = []             # un par monstre vu, dans l'ordre d'apparition : {'num': numero du monstre, 'vaincu': bool, 'fui': bool, 'disparu': bool} (au plus un des trois)
        self.objects = []               # objets gagnes : {'id': numero, 'nom': nom}, dans l'ordre
        self.places = {}               # emplacement -> indice dans monstres (occupant actuel)
        self.names = {}                 # numero de monstre -> nom
        self.deaths = 0                 # monstres vaincus (crochet execMonsterDeath)
        self.victory = False          # BattleExecDefeatMonster::initialize a eu lieu
        self.escape_attempts = 0      # BattleExecEscape::setup (reussie ou non)
        self.xp = 0; self.gold = 0      # plus grands relevés des compteurs du groupe (g_Party + 0x2f8 / 0x2fc)

    def see(self, occupants):
        """Un relevé des emplacements : occupants = [(emplacement, numero de monstre)] des emplacements occupes. Un nouvel occupant (emplacement libre qui se remplit, ou autre numero) est un nouveau monstre ;
        un emplacement qui se vide est oublie (le monstre vaincu ou parti est deja compte)."""
        seen = set()
        for e, num in occupants:
            seen.add(e); i = self.places.get(e)
            if i is None or self.monsters[i]['num'] != num:
                self.monsters.append(_monster(num)); self.places[e] = len(self.monsters) - 1
        for e in [e for e in self.places if e not in seen]: del self.places[e]

    def _record_fate(self, lookup_key, slot, num):
        """Le jeu declare que le monstre de cet emplacement est vaincu / enfui / disparu (cle : 'vaincu', 'fui' ou 'disparu'). Un monstre jamais vu (parti dans l'image de son apparition) est ajoute, de meme qu'un monstre
        dont le sort est deja note (autre monstre arrive dans le meme emplacement)."""
        i = self.places.get(slot)
        if i is None or self.monsters[i]['num'] != num or _is_gone(self.monsters[i]):
            self.monsters.append(_monster(num)); i = len(self.monsters) - 1; self.places[slot] = i
        self.monsters[i][lookup_key] = True

    def dead(self, slot, num):
        """Le jeu declare vaincu le monstre de cet emplacement (crochet execMonsterDeath)."""
        self.deaths += 1; self._record_fate('vaincu', slot, num)

    def fled(self, slot, num):
        """Le monstre de cet emplacement s'est enfui (le jeu le compte dans checkDeathMonster)."""
        self._record_fate('fui', slot, num)

    def vanished(self, slot, num):
        """Le monstre de cet emplacement a disparu (idem)."""
        self._record_fate('disparu', slot, num)

    def item(self, number, name_str):
        """Le jeu donne un objet au groupe a la fin du combat."""
        self.objects.append({'id': int(number), 'nom': name_str})

    def counters(self, xp, gold):
        """Relevé des compteurs d'experience et d'or du combat : ils ne font que croitre (doublement compris) jusqu'a leur remise a zero apres le message ; on garde le plus grand."""
        if xp > self.xp: self.xp = xp
        if gold > self.gold: self.gold = gold

    def assign_names(self, names):
        for num, name_str in names.items(): self.names.setdefault(num, name_str)

    def present_count(self): return len(self.places)

    def outcome(self, defeat=False):
        """Issue du combat a sa fin : la routine de victoire du jeu a tourne (victoire) ; sinon le groupe est anéanti (defaite) ; sinon tous les monstres vus sont vaincus (victoire) ; sinon le groupe est parti (fuite)."""
        if self.victory: return 'victoire'
        if defeat: return 'defaite'
        if self.deaths > 0 and all(_is_gone(m) for m in self.monsters): return 'victoire'
        return 'fuite'

    def enemies(self):
        """[{'nom', 'total', 'vaincus', 'fuis', 'disparus'}] une entree par espece (meme nom, ou meme numero quand le nom est inconnu), dans l'ordre de la premiere apparition."""
        species = {}
        for m in self.monsters:
            name_str = self.names.get(m['num'])
            lookup_key = ('n', name_str) if name_str else ('?', m['num'])
            e = species.setdefault(lookup_key, {'nom': name_str or tr(UNKNOWN_NAME), 'total': 0, 'vaincus': 0, 'fuis': 0, 'disparus': 0})
            e['total'] += 1; e['vaincus'] += 1 if m['vaincu'] else 0; e['fuis'] += 1 if m['fui'] else 0; e['disparus'] += 1 if m['disparu'] else 0
        return list(species.values())


def build_battle(tracking, t, defeat=False):
    """Le combat termine : dict de l'API (voir l'en-tete du module). Or et experience ne comptent que pour une victoire."""
    outcome = tracking.outcome(defeat)
    won = outcome == 'victoire'
    return {'t': int(t), 'ennemis': tracking.enemies(), 'or': int(tracking.gold) if won else 0, 'xp': int(tracking.xp) if won else 0, 'issue': outcome,
            'objets': [{'nom': o['nom']} for o in tracking.objects] if won else []}


# ---------------------------------------------------------------------------------------------------------------------------------- lecture du moteur
def _ldr_w(word, base=0):
    """Decalage d'un `ldr wN, [xM, #imm]` (acces 32 bits, offset non signe) ; None si ce n'est pas cette instruction."""
    if word & 0xffc00000 != 0xb9400000 or (word >> 5) & 31 != base: return None
    return ((word >> 10) & 0xfff) * 4


_PER_ENGINE = {}                                                                         # (secours si le moteur refuse un attribut en plus : id -> (moteur, capteur))


class BattleSensor:
    def __init__(self, engine):
        self.active = False; self.error = None
        self.tracking = None; self.outputs = []; self.events = []; self._item_names = {}; self._monster_names = {}; self._buffer = None
        self._state = None; self._frame = -10 ** 9; self._outside_battle = 0; self._old_plates = {}
        self.m = engine
        try:
            import unicorn
            c = self.c = engine.core
            self.g_party = c.export('_ZN6status7g_PartyE'); self.g_monster = c.export('_ZN6status9g_MonsterE'); self.g_game = c.export('_ZN6status6g_GameE'); self.g_result = c.export('_ZN6status14g_BattleResultE')
            if not (self.g_party and self.g_monster and self.g_game and self.g_result) or not self._check():
                print(tr('Historique des combats : moteur inattendu, capture desactivee'), flush=True); return
            for evt, name_str in HOOKS:
                a = c.export(name_str)
                if not a: print(tr('Historique des combats : %s introuvable, capture desactivee') % name_str, flush=True); return
            for evt, name_str in HOOKS: c.uc.hook_add(unicorn.UC_HOOK_CODE, self._hook(evt), None, c.export(name_str), c.export(name_str))
            for evt, name_str, off, word in INTERNAL_HOOKS:                               # (en cas de moteur different, seul cet evenement est perdu)
                a = c.export(name_str)
                if not a or struct.unpack('<I', c.mem(a + off, 4))[0] != word:
                    print(tr('Historique des combats : %s inattendu (+%#x), « %s » non suivi') % (name_str, off, evt), flush=True); continue
                c.uc.hook_add(unicorn.UC_HOOK_CODE, self._hook(evt), None, a + off, a + off)
            try: c.uc.ctl_flush_tb()                                                    # (blocs deja traduits avant les crochets : un capteur cree apres quelques combats)
            except Exception: pass
            self.active = True
        except Exception as ex:
            self.error = repr(ex); print(tr('Historique des combats : crochets non installes (%r)') % (ex,), flush=True)

    @classmethod
    def for_(cls, engine):
        """Le capteur de ce moteur : cree a la premiere demande, toujours le meme ensuite (les crochets ne sont installes qu'une fois). Permet de n'ajouter qu'UNE ligne a la boucle d'images, sans rien
        creer ailleurs : `for battle in BattleSensor.for_(eng).do_update(eng): ...` juste apres `eng.step`."""
        c = getattr(engine, '_battle_sensor', None) or _PER_ENGINE.get(id(engine), (None, None))[1]
        if c is None:
            c = cls(engine)
            try: engine._battle_sensor = c
            except Exception: _PER_ENGINE[id(engine)] = (engine, c)
        return c

    # ---- verification : le moteur est celui qu'on a etudie
    def _check(self):
        """Les structures lues sont celles du moteur etudie : getBattleExp / getBattleGold lisent bien g_Party + 0x2f8 / 0x2fc, MonsterStatus::isEnable lit bien +0x4f8 (numero de monstre)."""
        try:
            c = self.c
            def offset(name_str):
                a = c.export(name_str)
                return _ldr_w(struct.unpack('<I', c.mem(a, 4))[0]) if a else None
            return (offset('_ZN6status15BasePartyStatus12getBattleExpEv') == OFF_XP and offset('_ZN6status15BasePartyStatus13getBattleGoldEv') == OFF_GOLD
                    and offset('_ZN6status13MonsterStatus8isEnableEv') == OFF_NUMBER)
        except Exception:
            return False

    def _hook(self, evt):
        def cb(uc, addr, size_value, _):
            try:
                c = self.c
                if evt == 'mort':
                    i = uc.reg_read(c.XREG[1]) & 0xffffffff                              # indice dans les monstres PRESENTS (getMonsterStatus compte les emplacements occupes), pas l'emplacement
                    occ = self._busy()
                    if 0 <= i < len(occ): self.events.append(('mort', occ[i][0], occ[i][1], occ[i][2]))
                elif evt in ('monstre_enfui', 'monstre_disparu'):
                    i = uc.reg_read(c.XREG[20]) & 0xffffffff                              # w20 : indice du monstre dans la boucle de checkDeathMonster (meme indice que pour execMonsterDeath)
                    occ = self._busy()
                    if 0 <= i < len(occ): self.events.append((evt, occ[i][0], occ[i][1]))
                elif evt == 'objet':
                    task = uc.reg_read(c.XREG[20]) & 0xffffffffffff                      # x20 : la tache BattleExecVictory32 (le numero de l'objet est a +0xc)
                    self.events.append(('objet', struct.unpack('<I', c.mem(task + OFF_TASK_ITEM, 4))[0]))
                elif evt == 'fin':
                    self.events.append(('fin', bool(uc.reg_read(c.XREG[1]) & 1), c.mem(self.g_result + OFF_DEFEAT, 1)[0] == 1))
                else: self.events.append((evt,))
                if len(self.events) > 200: del self.events[:100]               # (garde-fou si maj n'est jamais appelee)
            except Exception:
                pass
        return cb

    def _busy(self):
        """[(emplacement, numero de monstre, numero de groupe)] des emplacements occupes de g_Monster, dans l'ordre des emplacements."""
        raw_value = self.c.mem(self.g_monster + MONSTERS_START, SLOT_COUNT * MONSTER_STEP)
        out = []
        for e in range(SLOT_COUNT):
            num, grp = struct.unpack_from('<2I', raw_value, e * MONSTER_STEP + OFF_NUMBER)
            if num != UNKNOWN and num < 4096: out.append((e, num, grp))
        return out

    def clock(self):
        """Temps de jeu en 1/60 s (status::g_Game + 4, comme historique.Sensor.time_and_key)."""
        try: return struct.unpack('<I', self.c.mem(self.g_game + 4, 4))[0]
        except Exception: return 0

    # ---- une image
    def do_update(self, engine):
        """A appeler UNE fois par image du moteur, apres moteur.step. -> liste des combats termines a cette image (dicts de l'API)."""
        if not self.active: return []
        try:
            state, image = engine.state, engine.frames
            discontinuity = state is not self._state or not 0 < image - self._frame <= MAX_JUMP_FRAMES
            self._state = state; self._frame = image
            if discontinuity and (self.tracking is not None):                                       # etat instantane charge (ou images sautees) : le combat suivi n'est plus celui de la memoire
                self.tracking = None
            if self.tracking is None and not self.events and state.part != PART_BATTLE: return []        # hors combat : rien d'autre a faire (chemin le plus frequent)
            ev, self.events = self.events, []
            for e in ev: self._event(e)
            if self.tracking is not None: self._observe(engine)
            if self.outputs: out, self.outputs = self.outputs, []; return out
            return []
        except Exception as ex:                                                              # la capture ne doit jamais arreter le jeu
            if self.error is None: print(tr('Historique des combats : erreur (%r)') % (ex,), flush=True)
            self.error = repr(ex); self.tracking = None; self.events = []
            return []

    def _event(self, e):
        name_str = e[0]
        if name_str == 'debut':
            self.tracking = Tracking(); self._outside_battle = 0; self._old_plates = self._plates()                       # (plaques deja la : celles du combat precedent, a ne pas lire)
        elif self.tracking is None: return                                                    # combat dont on n'a pas vu le debut : ignore
        elif name_str == 'mort': self.tracking.dead(e[1], e[2])
        elif name_str == 'monstre_enfui': self.tracking.fled(e[1], e[2])
        elif name_str == 'monstre_disparu': self.tracking.vanished(e[1], e[2])
        elif name_str == 'objet': self.tracking.item(e[1], self._item_name(e[1]))
        elif name_str == 'victoire': self.tracking.victory = True
        elif name_str == 'fuite': self.tracking.escape_attempts += 1
        elif name_str == 'fin':
            s, self.tracking = self.tracking, None
            for m in s.monsters:                                                          # monstres sans plaque (attaque surprise...) : le nom vient du moteur, par le numero
                if m['num'] not in s.names:
                    n = self._monster_name(m['num'])
                    if n: s.assign_names({m['num']: n})
            self.outputs.append(build_battle(s, self.clock(), defeat=e[1] or e[2]))

    def _observe(self, engine):
        """Relevé de l'image pour le combat suivi : emplacements, compteurs, noms."""
        s = self.tracking
        if engine.state.part != PART_BATTLE:
            self._outside_battle += 1
            if self._outside_battle > MAX_FRAMES_WITHOUT_BATTLE: self.tracking = None                # on a quitte le combat sans passer par endBattle (retour au titre...) : abandon
            return
        self._outside_battle = 0
        occ = self._busy()
        s.see([(e, num) for e, num, _g in occ])
        xp, gold = struct.unpack('<2I', self.c.mem(self.g_party + OFF_XP, 8))
        s.counters(xp, gold)
        if occ and s.deaths == 0 and any(n not in s.names for _e, n, _g in occ): self._names(s, occ)

    def _engine_text(self, kind, number):
        """Texte que le moteur donne pour (genre, numero) -- TextAPI::extractText, ce que le jeu appelle pour une macro de nom -- ; None sans reponse. Appele entre deux images (maj), jamais depuis un crochet.
        Le « ; » (coupure des noms du patch) est retire, le « $ » (coupure avec trait d'union) devient un tiret."""
        try:
            c = self.c; f = c.export(SYM_ITEM_NAME)
            if not f: return None
            if self._buffer is None: self._buffer = c.malloc(256)
            c.mem_w(self._buffer, b'\0' * 16)
            c.call(f, self._buffer, kind | number, label='nom du moteur')
            t = c.read_cstr(self._buffer).decode('utf-8', 'replace').replace(';', '').replace('$', '-').strip()
            return t if t and not t.startswith('<ERR') else None
        except Exception:
            return None

    def _item_name(self, number):
        """Nom de l'objet (le nom que le jeu affiche) ; garde. Sans reponse : « Objet n°12 »."""
        name_str = self._item_names.get(number)
        if name_str is None: name_str = self._item_names[number] = self._engine_text(KIND_ITEM, number) or tr(UNKNOWN_ITEM_NAME) % number
        return name_str

    def _monster_name(self, number):
        """Nom du monstre, avec une majuscule (le moteur donne le nom comme dans une phrase : « londuleux ») ; garde. None sans reponse."""
        name_str = self._monster_names.get(number)
        if name_str is None:
            t = self._engine_text(KIND_MONSTER, number)
            name_str = self._monster_names[number] = (t[:1].upper() + t[1:]) if t else ''
        return name_str or None

    def _plates(self):
        """{fenetre: (dict de chaque plaque, ...)} des plaques de monstres que Engine.ui a en memoire (fenetre de type 31). On garde les objets eux-memes : le moteur en cree de nouveaux a chaque rafraichissement."""
        out = {}
        try:
            for port, f in self.m.ui.f.items():
                if f.get('type') != 31: continue
                plate_dict, layout = f.get('plaq') or {}, f.get('dispo')
                if isinstance(layout, int) and 1 <= layout <= 4 and all(j in plate_dict for j in range(layout)): out[port] = tuple(plate_dict[j] for j in range(layout))
        except Exception:
            pass
        return out

    def _names(self, s, occ):
        """Noms des plaques de monstres envoyees par le moteur a Unity, tant qu'aucun monstre n'est vaincu. Seules comptent les plaques arrivees depuis le debut de ce combat (objets differents de ceux d'alors)."""
        for port, cur in self._plates().items():
            old = self._old_plates.get(port)
            if old is not None and len(old) == len(cur) and all(a is b for a, b in zip(old, cur)): continue
            res = group_names([(g, n) for _e, n, g in occ], [p.get('nom') for p in cur])
            if res: s.assign_names(res); self._old_plates[port] = cur
