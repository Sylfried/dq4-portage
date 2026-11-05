"""Harnais de combat (moteur reel sous Unicorn, sans fenetre) pour l'audit des animations alliees du 05/11/2026.
Lecture seule du depot : on importe dq4_pc depuis /home/claude/dq4-portage sans rien y ecrire.

Fonctions :
  boot()                    -> Engine pret, sauvegarde du chapitre 1 chargee, carte du monde
  Rec                       -> enregistreur : appels de BattleEffectManager::setupEffect(id) et paquets de combat par image
  start_battle(eng, groupe) -> force un combat contre `groupe` = [(monstre, nombre), ...]
  force_actions(eng, queue) -> a chaque tour d'un ALLIE, remplace l'action choisie par la suivante de la file
  run(...)                  -> joue le combat (A toutes les 8 images comme le balayage de l'audit)
"""
import sys, os, struct, tempfile, time, json
os.environ.update(PYGLET_HEADLESS='1', PYGLET_AUDIO='silent', PYTHONDONTWRITEBYTECODE='1')
os.environ.setdefault('DQ4_DATA', '/tmp/claude-0/-home-claude/45fdf246-f4ad-5078-9633-8be9ccf9e9c9/scratchpad/anim/dq4data')
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/claude/dq4-portage')
import unicorn
from dq4_pc.core import engine as ENGINE

APK = os.environ.get('DQ_APK', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks')
SAVES = os.environ.get('DQ_SAVES', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735')
PB = ENGINE.PART_BATTLE


def boot(slot=4):
    eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_anim_'))
    for _ in range(3): eng.step(0, 0)
    eng.load_save(slot)
    for i in range(100): eng.step(0, 0x10 if i % 10 == 0 else 0)
    if eng.state.part != ENGINE.PART_FIELD:
        eng.start_field()
        for i in range(120): eng.step(0, 0)
    return eng


def u32(c, a): return struct.unpack('<I', c.mem(a, 4))[0]
def u64(c, a): return struct.unpack('<Q', c.mem(a, 8))[0]


class Rec:
    """Crochets en lecture seule : setupEffect(id), lancement d'actions."""
    def __init__(self, eng):
        self.eng = eng; c = eng.core; self.c = c
        self.effects = []          # (image moteur, id d'effet demande a BattleEffectManager::setupEffect)
        self.execs = []            # (image moteur, acteur, action, source) : BattleActorExec::setup
        self.override = []         # file d'identifiants d'effets qui remplacent, un par un, l'argument 303 (attaque d'arme de Ragnar) de setupEffect
        self.overridden = []       # (image, identifiant demande)
        a = c.export('_ZN19BattleEffectManager11setupEffectEi')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, self._eff, None, a, a)
        b = c.export('_ZN15BattleActorExec5setupEPN6status14UseActionParamE')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, self._exec, None, b, b)
        c.uc.ctl_flush_tb()

    def _eff(self, uc, adr, sz, ud):
        arg = uc.reg_read(self.c.XREG[1]) & 0xffffffff
        if self.override and arg == 303:
            arg = self.override.pop(0); uc.reg_write(self.c.XREG[1], arg); self.overridden.append((self.eng.frames, arg))
        self.effects.append((self.eng.frames, arg))

    def _exec(self, uc, adr, sz, ud):
        p = uc.reg_read(self.c.XREG[1]) & 0xffffffffffff
        try:
            actor = u64(self.c, p); act = u32(self.c, p + 0x1d8)
        except Exception: actor = act = -1
        self.execs.append((self.eng.frames, actor, act))


def players(eng):
    """(base de originalPlayer_, ids des membres du groupe)"""
    c = eng.core
    orig = c.export('_ZN6status9PartyData15originalPlayer_E'); party = c.export('_ZN6status7g_PartyE')
    mem = [i for i in struct.unpack('<13I', c.mem(party + 0x304, 13 * 4)) if i]
    return orig, mem


def make_strong(eng, hp=999, mp=99):
    c = eng.core; orig, mem = players(eng)
    for i in mem:
        hs = orig + 0x530 * i + 0x58
        c.mem_w(hs + 0x22, struct.pack('<H', hp)); c.mem_w(hs + 0x24, struct.pack('<H', hp)); c.mem_w(hs + 0x26, struct.pack('<H', mp)); c.mem_w(hs + 0x28, struct.pack('<H', mp))


def start_battle(eng, groupe, brew=None):
    """Combat force contre `groupe` (4 couples max) ; -> True si la partie combat est atteinte."""
    c = eng.core
    enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
    g = (list(groupe) + [(0, 0)] * 4)[:4]
    def forcer(u, adr, sz, ud):
        for k, (i, n) in enumerate(g):
            c.mem_w(enc + 0x34 + 4 * k, struct.pack('<I', i)); c.mem_w(enc + 0x44 + 4 * k, struct.pack('<I', n))
    a = c.export('_ZN10BattleRoot12setupMonsterEv')
    h = c.uc.hook_add(unicorn.UC_HOOK_CODE, forcer, None, a, a); c.uc.ctl_flush_tb()
    c.call(c.export('_ZN6Global11startBattleEv'), eng._global(), label='startBattle')
    for i in range(1200):
        eng.step(0, 0)
        if eng.state.part == PB: break
    c.uc.hook_del(h)
    return eng.state.part == PB


class Forcer:
    """A chaque fois que le jeu copie l'action choisie d'un ALLIE dans UseActionParam (BattleSelectTarget::setActorAction + 0x48), on remplace son numero par le suivant de la file."""
    SYM = '_ZN18BattleSelectTarget14setActorActionEPN6status14UseActionParamEN23BattleSelectTargetParam16CallTargetSelectE'
    def __init__(self, eng, queue):
        self.eng = eng; c = eng.core; self.c = c; self.queue = list(queue); self.done = []
        self.orig, _ = players(eng)
        a = c.export(self.SYM) + 0x48
        c.uc.hook_add(unicorn.UC_HOOK_CODE, self._h, None, a, a); c.uc.ctl_flush_tb()

    def _h(self, uc, adr, sz, ud):
        c = self.c; x20 = uc.reg_read(c.XREG[20]) & 0xffffffffffff
        rel = x20 - self.orig
        if not (0 <= rel < 0x530 * 16) or not self.queue: return
        act = self.queue.pop(0)
        old = u32(c, x20 + 0x484)
        c.mem_w(x20 + 0x484, struct.pack('<I', act))
        self.done.append((self.eng.frames, rel // 0x530, old, act))


def natural_battle(eng):
    """Combat « naturel » (Encount::forceEncount puis marche, comme tools/research/battle/drive.py) : le moteur choisit la formation de la zone."""
    c = eng.core
    c.call(eng.E('_ZN7Encount12forceEncountEv'), c.call(eng.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
    for i in range(900):
        eng.step([0x4, 0x8][(i // 20) % 2], 0)
        if eng.state.part == PB: return True
    return False


def monsters(eng):
    c = eng.core; g = c.export('_ZN6status9g_MonsterE'); res = []
    for i in range(12):
        num, grp = struct.unpack('<iI', c.mem(g + 8 + 0x538 * i + 0x4f8, 8))
        if num != -1 and num != 0xffffffff: res.append((i, num, grp))
    return res


class Player:
    """Joue le combat comme un joueur : menus par `eng.send_menu` (comme drive.py), A pour les messages."""
    def __init__(self, eng): self.eng = eng; self.rel = None; self.menu = None; self.att = 0; self.msgatt = 0; self.types = []

    def step(self, policy=None):
        eng = self.eng; p = d = 0
        if self.rel is not None: eng.send_menu(self.rel, 1, -1, 0); self.rel = None
        port = eng.active_menu()
        if port is not None and not eng.msg_visible:
            f = eng.ui.win(port)
            if port != self.menu: self.att = 0; self.types.append((eng.frames, f['type'], sorted(f['cases'].values())[:6]))
            self.att += 1
            if self.att % 4 == 0:
                idx = policy(f['type'], f['cases']) if policy else 0
                eng.send_menu(port, 1, idx, 0x10); self.rel = port
        elif eng.msg_visible and eng.message_state()[1] in (3, 5):
            self.msgatt += 1
            if self.msgatt > 30 and self.msgatt % 4 == 0: p = d = ENGINE.A
        else: self.msgatt = 0
        self.menu = port
        return eng.step(p, d)


KEEP = (21, 22, 24, 25, 26, 31, 32, 33, 35, 36, 9, 34)


def run(eng, frames=2000, stop_when=None, policy=None, log=None, scroll=2):
    """Joue le combat ; -> liste de (image, paquets utiles).
    Les paquets de combat (21 modele, 22 maillage, 24 shader, 25 couleur, 26 decalage de texture, 31/32 fbx, 33 teinte, 35 bruitage, 9 fondu) sont gardes."""
    if scroll is not None: eng.impose_scroll_mode(scroll)
    pl = Player(eng); out = []
    for i in range(frames):
        pkt = pl.step(policy)
        keep = [(t, list(a), [round(float(x), 3) for x in f[:6]]) if t != 22 else (22, list(a[:2]), []) for t, a, f in pkt if t in KEEP]
        if keep: out.append((eng.frames, keep))
        if log is not None: log(eng, pkt)
        if eng.state.part != PB and i > 30: break
        if stop_when and stop_when(eng): break
    return out, pl
