"""Test de la capture des resultats de combat (dq4_pc/battle_history.py) : ennemis vaincus, or, experience.

Trois niveaux :
- calcul pur (Suivi, noms des plaques, build_battle) : aucun moteur ;
- colle (BattleSensor) sur un FAUX moteur (memoire et emulateur simules : les crochets sont declenches a la main) : debut / morts / victoire / fin, ruptures, abandons, erreurs ;
- moteur REEL facultatif : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> (la sauvegarde 1 : Ragnar et Doc dans une ville). Les combats sont forces dans un moteur jetable (la composition de
  la rencontre est ecrite dans Encount quand BattleRoot::setupMonster va la lire ; Global::startBattle lance le combat) ; chaque dict est compare au TEXTE du jeu (« reçoit N points d'expérience »,
  « N pièces d'or ») et aux compteurs du groupe dans la memoire (or avant / apres, experience de chaque membre avant / apres).

    python3 tools/test_battle_history.py
    DQ_APK=... DQ_SAVES=... python3 tools/test_battle_history.py        (une minute environ)
"""
import os, re, struct, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from dq4_pc import language as LG
LG.select_language('fr')          # (D-238 : les attentes de ce test sont en francais, quelle que soit la langue de l'ordinateur)
from dq4_pc.battle import battle_history as HC


# ---------------------------------------------------------------------------------------------------------------------------------- calcul pur
class Plates(unittest.TestCase):
    def test_plate_name(self):
        self.assertEqual(HC.plate_name('Rat volant'), 'Rat volant')
        self.assertEqual(HC.plate_name('Gluant\n\n\t×3'), 'Gluant')
        self.assertEqual(HC.plate_name('  Chauve-sourat \r\n'), 'Chauve-sourat')
        for v in ('', '\n\t', None, 3, b'x'): self.assertIsNone(HC.plate_name(v), repr(v))

    def test_name_on_two_lines(self):
        """Les noms longs sont coupes sur deux lignes par le jeu (« ; » et « $ » des textes) : le nom complet est rendu, le nombre de monstres (ligne commencant par une tabulation) retire."""
        for raw_value, name_str in (('Armure \n\nerrante', 'Armure errante'), ('Gluant de \n\nmercure\n\n\t×2', 'Gluant de mercure'), ('Scara-\n\nsomniaque', 'Scara-somniaque'),
                          ('Typhon-\n\nphonphon\n\n\t×3', 'Typhon-phonphon'), ("Rejeton de \n\nl'enfer", "Rejeton de l'enfer"), ('Gluant\n\n×3', 'Gluant'), ('Gluant\n\n\t×3\n\n', 'Gluant')):
            self.assertEqual(HC.plate_name(raw_value), name_str, repr(raw_value))

    def test_names_in_group_order(self):
        groups = [(0, 3), (0, 3), (1, 20), (2, 0), (2, 0), (2, 0), (3, 5)]
        self.assertEqual(HC.group_names(groups, ['Londuleux\n\n\t×2', 'Rat volant', 'Gluant\n\n\t×3', 'Chauve-sourat']), {3: 'Londuleux', 20: 'Rat volant', 0: 'Gluant', 5: 'Chauve-sourat'})
        self.assertEqual(HC.group_names([(1, 7), (4, 9)], ['A', 'B']), {7: 'A', 9: 'B'})                       # (les numeros de groupe ne sont pas forcement 0, 1, 2...)

    def test_no_match_no_name(self):
        self.assertEqual(HC.group_names([(0, 3), (1, 20)], ['Londuleux']), {})                                  # moins de plaques que de groupes
        self.assertEqual(HC.group_names([(0, 3)], ['Londuleux', 'Rat volant']), {})                              # plus de plaques que de groupes
        self.assertEqual(HC.group_names([(0, 3), (1, 20)], ['Londuleux', None]), {})                             # une plaque sans nom
        self.assertEqual(HC.group_names([], []), {})


class PureTracking(unittest.TestCase):
    def test_one_monster_per_occupied_slot(self):
        s = HC.Tracking(); s.see([(0, 3), (1, 3), (2, 20)]); s.see([(0, 3), (1, 3), (2, 20)])
        self.assertEqual([m['num'] for m in s.monsters], [3, 3, 20])                                                  # revu a chaque image : pas recompte
        self.assertEqual(s.present_count(), 3)

    def test_appearance_order_and_grouping(self):
        s = HC.Tracking(); s.assign_names({3: 'Londuleux', 20: 'Rat volant'}); s.see([(0, 20), (1, 3), (2, 20)]); s.dead(1, 3); s.dead(0, 20)
        self.assertEqual(s.enemies(), [{'nom': 'Rat volant', 'total': 2, 'vaincus': 1, 'fuis': 0, 'disparus': 0}, {'nom': 'Londuleux', 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}])

    def test_slot_released_then_reoccupied_is_reinforcement(self):
        s = HC.Tracking(); s.assign_names({0: 'Gluant', 9: 'Roi des gluants'}); s.see([(0, 0), (1, 0)]); s.dead(0, 0)
        s.see([(0, 0), (1, 0)])                                                                                      # le monstre vaincu reste dans son emplacement jusqu'au nettoyage
        s.see([(1, 0)])                                                                                              # nettoye
        s.see([(0, 9), (1, 0)])                                                                                      # un renfort arrive dans l'emplacement libre
        self.assertEqual(s.enemies(), [{'nom': 'Gluant', 'total': 2, 'vaincus': 1, 'fuis': 0, 'disparus': 0}, {'nom': 'Roi des gluants', 'total': 1, 'vaincus': 0, 'fuis': 0, 'disparus': 0}])

    def test_number_change_in_slot(self):
        s = HC.Tracking(); s.see([(0, 0)]); s.see([(0, 5)])                                                            # transformation / remplacement entre deux releves : nouveau monstre
        self.assertEqual([m['num'] for m in s.monsters], [0, 5])

    def test_death_of_never_seen_monster(self):
        s = HC.Tracking(); s.dead(4, 7)
        self.assertEqual(s.enemies(), [{'nom': HC.UNKNOWN_NAME, 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}]); self.assertEqual(s.deaths, 1)

    def test_several_deaths_in_same_frame(self):
        s = HC.Tracking(); s.see([(0, 0), (1, 0), (2, 0)]); s.dead(0, 0); s.dead(1, 0); s.dead(2, 0)
        self.assertEqual(s.enemies(), [{'nom': HC.UNKNOWN_NAME, 'total': 3, 'vaincus': 3, 'fuis': 0, 'disparus': 0}]); self.assertEqual(s.outcome(), 'victoire')

    def test_unknown_names_distinct_numbers(self):
        s = HC.Tracking(); s.see([(0, 1), (1, 2)])
        self.assertEqual([e['nom'] for e in s.enemies()], [HC.UNKNOWN_NAME, HC.UNKNOWN_NAME])                          # deux especes sans nom : deux entrees, jamais fondues
        s.assign_names({1: 'A', 2: 'A'}); self.assertEqual(s.enemies(), [{'nom': 'A', 'total': 2, 'vaincus': 0, 'fuis': 0, 'disparus': 0}])           # meme nom = meme espece pour le joueur

    def test_an_already_known_name_is_not_changed(self):
        s = HC.Tracking(); s.assign_names({1: 'Gluant'}); s.assign_names({1: 'Autre'}); self.assertEqual(s.names[1], 'Gluant')

    def test_counters_keep_largest_reading(self):
        s = HC.Tracking(); s.counters(3, 7); s.counters(6, 13); s.counters(0, 0); s.counters(5, 10)
        self.assertEqual((s.xp, s.gold), (6, 13))

    def test_outcomes(self):
        s = HC.Tracking(); s.see([(0, 1), (1, 1)]); s.dead(0, 1)
        self.assertEqual(s.outcome(), 'fuite')                                                                          # un monstre vaincu sur deux, pas de routine de victoire : parti
        s.escape_attempts = 3; self.assertEqual(s.outcome(), 'fuite')
        self.assertEqual(s.outcome(defeat=True), 'defaite')
        s.victory = True; self.assertEqual(s.outcome(defeat=True), 'victoire')                                         # la routine de victoire l'emporte sur un drapeau de defaite resté d'un combat precedent
        s2 = HC.Tracking(); s2.see([(0, 1)]); s2.dead(0, 1); self.assertEqual(s2.outcome(), 'victoire')                    # tous vaincus, meme sans la routine
        self.assertEqual(HC.Tracking().outcome(), 'fuite')                                                                  # rien vu, rien vaincu : le groupe est parti

    def test_gold_and_experience_only_for_victory(self):
        for defeat, won in ((False, True), (True, False)):
            s = HC.Tracking(); s.see([(0, 1), (1, 1)]); s.dead(0, 1); s.counters(5, 9)
            if won: s.dead(1, 1)
            d = HC.build_battle(s, 1234, defeat=defeat)
            self.assertEqual((d['or'], d['xp']), (9, 5) if won else (0, 0)); self.assertEqual(d['issue'], 'victoire' if won else 'defaite')
        s = HC.Tracking(); s.see([(0, 1), (1, 1)]); s.dead(0, 1); s.counters(5, 9); d = HC.build_battle(s, 1)
        self.assertEqual((d['issue'], d['or'], d['xp']), ('fuite', 0, 0))                                              # fuite apres une mort : ni or ni experience (le moteur ne les verse pas)

    def test_dict_shape(self):
        s = HC.Tracking(); s.assign_names({0: 'Gluant'}); s.see([(0, 0)]); s.dead(0, 0); s.counters(2, 3)
        d = HC.build_battle(s, 12345)
        self.assertEqual(d, {'t': 12345, 'ennemis': [{'nom': 'Gluant', 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}], 'or': 3, 'xp': 2, 'issue': 'victoire', 'objets': []})
        self.assertEqual(sorted(d), ['ennemis', 'issue', 'objets', 'or', 't', 'xp']); self.assertIn(d['issue'], HC.OUTCOMES)
        for e in d['ennemis']: self.assertEqual(sorted(e), ['disparus', 'fuis', 'nom', 'total', 'vaincus'])
        self.assertTrue(all(type(v) is int for v in (d['t'], d['or'], d['xp'])))

    def test_fled_and_vanished_monsters(self):
        """#141 : chaque monstre a UN sort (vaincu, enfui ou disparu) ; ce qui n'a aucun sort est encore la a la fin."""
        s = HC.Tracking(); s.assign_names({0: 'Gluant', 5: 'Golem'}); s.see([(0, 0), (1, 0), (2, 0), (3, 5)]); s.dead(0, 0); s.fled(1, 0); s.vanished(2, 0)
        self.assertEqual(s.enemies(), [{'nom': 'Gluant', 'total': 3, 'vaincus': 1, 'fuis': 1, 'disparus': 1}, {'nom': 'Golem', 'total': 1, 'vaincus': 0, 'fuis': 0, 'disparus': 0}])
        self.assertEqual(s.deaths, 1)                                                                                  # (seuls les morts comptent comme « morts » : ni une fuite ni une disparition)

    def test_a_fled_monster_is_not_a_victory(self):
        s = HC.Tracking(); s.see([(0, 0), (1, 0)]); s.dead(0, 0); s.fled(1, 0)
        self.assertEqual(s.outcome(), 'victoire')                                                                       # (plus aucun monstre : tous vaincus ou partis, au moins un vaincu)
        s = HC.Tracking(); s.see([(0, 0), (1, 0)]); s.dead(0, 0)
        self.assertEqual(s.outcome(), 'fuite')                                                                          # un monstre reste : le groupe est parti
        s.victory = True; self.assertEqual(s.outcome(), 'victoire')                                                    # (la routine de victoire du jeu a le dernier mot)

    def test_spell_of_a_monster_never_seen_or_already_decided(self):
        s = HC.Tracking(); s.fled(4, 7); s.vanished(5, 7)
        self.assertEqual(s.enemies(), [{'nom': HC.UNKNOWN_NAME, 'total': 2, 'vaincus': 0, 'fuis': 1, 'disparus': 1}])
        s = HC.Tracking(); s.see([(0, 3)]); s.fled(0, 3); s.fled(0, 3)                                               # meme emplacement, sort deja note : un autre monstre
        self.assertEqual(s.enemies(), [{'nom': HC.UNKNOWN_NAME, 'total': 2, 'vaincus': 0, 'fuis': 2, 'disparus': 0}])

    def test_won_items(self):
        s = HC.Tracking(); s.assign_names({0: 'Gluant'}); s.see([(0, 0)]); s.dead(0, 0); s.counters(2, 3)
        s.item(12, 'herbe médicinale'); s.item(40, 'pierre de vie')
        d = HC.build_battle(s, 1)
        self.assertEqual(d['objets'], [{'nom': 'herbe médicinale'}, {'nom': 'pierre de vie'}])
        s2 = HC.Tracking(); s2.see([(0, 0), (1, 0)]); s2.dead(0, 0); s2.item(12, 'x')
        self.assertEqual(HC.build_battle(s2, 1)['objets'], [])                                                    # pas de victoire : pas d'objets rapportes


# ---------------------------------------------------------------------------------------------------------------------------------- colle sur un faux moteur
LIB = 0x10000000
A_PARTY, A_MONSTER, A_GAME, A_RESULT = 0x1000, 0x2000, 0x1f000, 0x1e000
FUNCTION_NAMES = {'_ZN6status15BasePartyStatus12getBattleExpEv': 0x30000, '_ZN6status15BasePartyStatus13getBattleGoldEv': 0x30010, '_ZN6status13MonsterStatus8isEnableEv': 0x30020,
                  '_ZN6status11PartyStatus11startBattleEv': 0x30100, '_ZN19BattleActorManager216execMonsterDeathEi': 0x30110, '_ZN23BattleExecDefeatMonster10initializeEv': 0x30120,
                  '_ZN16BattleExecEscape5setupEv': 0x30130, '_ZN6Global9endBattleEb': 0x30140,
                  HC.SYM_DEATH_CHECK: 0x30200, HC.SYM_ITEM_WON: 0x30300, HC.SYM_ITEM_NAME: 0x30400}
A_TASK = 0x31000                                                                                                    # la tache BattleExecVictory32 : le numero de l'objet a +0xc
INTERNAL = {evt: (FUNCTION_NAMES[name_str] + off, word) for evt, name_str, off, word in HC.INTERNAL_HOOKS}                  # evenement -> (adresse du crochet, instruction attendue)
ITEM_NAMES = {12: 'herbe ;médicinale', 40: 'pierre de vie', 7: '<ERR 0x04000000.7>'}                                # ce que TextAPI::extractText repond
MONSTER_NAMES = {0: 'gluant', 3: 'londuleux', 34: 'armure ;errante', 74: 'scara$somniaque', 5: 'chauve-sourat'}


def ldr_w(offset, rt=0): return 0xb9400000 | ((offset // 4) << 10) | rt                                        # ldr wRt, [x0, #decalage]


class FakeUC:
    def __init__(self): self.hooks = {}; self.regs = {}
    def hook_add(self, typ, cb, ud, begin, end): self.hooks.setdefault(begin, []).append(cb)
    def reg_read(self, r): return self.regs.get(r, 0)
    def ctl_flush_tb(self): pass


class FakeCore:
    XREG = list(range(100, 131))
    def __init__(self, bad_version=False, fake_internal_word=None):
        self.ram = bytearray(0x40000); self.uc = FakeUC(); self.reads = 0; self.calls = []
        for name_str, a in FUNCTION_NAMES.items(): self.ram[a:a + 4] = struct.pack('<I', 0xd65f03c0)
        for evt, (a, word) in INTERNAL.items(): self.ram[a:a + 4] = struct.pack('<I', word ^ 1 if evt == fake_internal_word else word)
        off = {'_ZN6status15BasePartyStatus12getBattleExpEv': HC.OFF_XP, '_ZN6status15BasePartyStatus13getBattleGoldEv': HC.OFF_GOLD, '_ZN6status13MonsterStatus8isEnableEv': HC.OFF_NUMBER}
        for name_str, o in off.items(): self.ram[FUNCTION_NAMES[name_str]:FUNCTION_NAMES[name_str] + 4] = struct.pack('<I', ldr_w(o + (4 if bad_version else 0)))
        self.symbols = dict(FUNCTION_NAMES); self.symbols.update({'_ZN6status7g_PartyE': A_PARTY, '_ZN6status9g_MonsterE': A_MONSTER, '_ZN6status6g_GameE': A_GAME, '_ZN6status14g_BattleResultE': A_RESULT})
        for e in range(HC.SLOT_COUNT): self.drain(e)
    def export(self, name_str): return self.symbols.get(name_str)
    def mem(self, a, n): self.reads += 1; return bytes(self.ram[a:a + n])
    def write(self, a, fmt, *v): self.ram[a:a + struct.calcsize(fmt)] = struct.pack(fmt, *v)
    def place(self, e, num, group=0): self.write(A_MONSTER + HC.MONSTERS_START + e * HC.MONSTER_STEP + HC.OFF_NUMBER, '<2I', num, group)
    def drain(self, e): self.place(e, 0xffffffff, 0)
    def trigger(self, name_str, *args):
        for i, v in enumerate(args): self.uc.regs[self.XREG[i + 1]] = v
        for cb in self.uc.hooks[TRIGGERS[name_str]]: cb(self.uc, 0, 4, None)
    def trigger_internal(self, evt, **regs):
        """Crochet au milieu d'une fonction du moteur : regs = {'x20': valeur, 'x0': valeur}."""
        for r, v in regs.items(): self.uc.regs[self.XREG[int(r[1:])]] = v
        for cb in self.uc.hooks[INTERNAL[evt][0]]: cb(self.uc, 0, 4, None)
    def fled(self, i): self.trigger_internal('monstre_enfui', x20=i)
    def vanished(self, i): self.trigger_internal('monstre_disparu', x20=i)
    def item(self, number, placement=0):
        """rangement : ce que giveItem a renvoye (indice du membre, ou -1 : dans le sac)."""
        self.write(A_TASK + HC.OFF_TASK_ITEM, '<I', number); self.trigger_internal('objet', x20=A_TASK, x0=placement & 0xffffffff)
    # -- l'appel d'une fonction du moteur (HC.BattleSensor._item_name : TextAPI::extractText)
    def malloc(self, n): return 0x3f000
    def mem_w(self, a, b): self.ram[a:a + len(b)] = b
    def read_cstr(self, a, limit=1 << 20):
        end = self.ram.index(0, a); return bytes(self.ram[a:end])
    def call(self, f, *args, label=''):
        self.calls.append((f, args)); buf, arg = args; num = arg & 0xffffff; assert f == FUNCTION_NAMES[HC.SYM_ITEM_NAME]
        if arg & 0xf000000 == HC.KIND_MONSTER: name_str = MONSTER_NAMES.get(num, '<ERR 0x06000000.%d>' % num)
        else: assert arg & 0xf000000 == HC.KIND_ITEM; name_str = ITEM_NAMES.get(num, '<ERR 0x04000000.%d>' % num)
        self.mem_w(buf, name_str.encode('utf-8') + b'\0'); return buf


TRIGGERS = {'debut': 0x30100, 'mort': 0x30110, 'victoire': 0x30120, 'fuite': 0x30130, 'fin': 0x30140}


class FakeState:
    def __init__(self): self.part = 0xc


class FakeUI:
    def __init__(self): self.f = {}


class FakeEngine:
    def __init__(self, bad_version=False, fake_internal_word=None):
        self.core = FakeCore(bad_version, fake_internal_word); self.state = FakeState(); self.frames = 100; self.ui = FakeUI()
    def step(self, sensor, n=1):
        outputs = []
        for _ in range(n): self.frames += 1; outputs.extend(sensor.do_update(self))
        return outputs
    def plates(self, names, port=15, layout=None):
        """Comme Interface.appliquer : de nouveaux dicts a chaque rafraichissement."""
        self.ui.f[port] = {'type': 31, 'dispo': len(names) if layout is None else layout, 'plaq': {i: {'code': 2, 'nom': n, 'prm': [0, 0]} for i, n in enumerate(names)}}


def simple_battle(m, c, names=('Rat volant', 'Londuleux'), nums=(20, 3)):
    """Debut, deux monstres, plaques, deux morts, victoire, fin ; -> les dicts rendus."""
    m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, nums[0], 0); m.core.place(1, nums[1], 1)
    outputs = m.step(c, 3); m.plates(list(names)); outputs += m.step(c, 3)
    m.core.trigger('mort', 0); m.core.trigger('mort', 1)
    m.core.write(A_PARTY + HC.OFF_XP, '<2I', 6, 13); outputs += m.step(c, 2)
    m.core.trigger('victoire'); m.core.write(A_PARTY + HC.OFF_XP, '<2I', 6, 13); outputs += m.step(c, 2)
    m.core.write(A_PARTY + HC.OFF_XP, '<2I', 0, 0); m.core.write(A_GAME + 4, '<I', 5555)
    m.core.trigger('fin', 0); outputs += m.step(c, 1)
    return outputs


class Glue(unittest.TestCase):
    def setUp(self): self.m = FakeEngine(); self.c = HC.BattleSensor(self.m)

    def test_hooks_installed(self):
        self.assertTrue(self.c.active)
        self.assertEqual(sorted(self.m.core.uc.hooks), sorted([FUNCTION_NAMES[n] for _e, n in HC.HOOKS] + [a for a, _m in INTERNAL.values()]))

    def test_unexpected_internal_hook_only_that_event_lost(self):
        """Une instruction differente a l'endroit du crochet (autre moteur) : pas de crochet au hasard ; le reste de la capture fonctionne."""
        m = FakeEngine(fake_internal_word='monstre_enfui'); c = HC.BattleSensor(m)
        self.assertTrue(c.active); self.assertNotIn(INTERNAL['monstre_enfui'][0], m.core.uc.hooks); self.assertIn(INTERNAL['monstre_disparu'][0], m.core.uc.hooks)
        self.assertEqual(len(simple_battle(m, c)), 1)

    def complete_scenario(self, objects=((12, 0), (40, -1)), fled=1, vanished=2, victory=True):
        """3 Gluants et 1 Golem : le 1er Gluant meurt, un autre s'enfuit, le dernier disparait, le Golem meurt ; puis victoire (or 13, experience 6), les objets, la fin."""
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut')
        for e, (num, grp) in enumerate(((0, 0), (0, 0), (0, 0), (5, 1))): m.core.place(e, num, grp)
        outputs = m.step(c, 3); m.plates(['Gluant\n\n\t×3', 'Golem']); outputs += m.step(c, 3)
        m.core.trigger('mort', 0); outputs += m.step(c, 1)
        if fled is not None: m.core.fled(fled)
        if vanished is not None: m.core.vanished(vanished)
        outputs += m.step(c, 1); m.core.trigger('mort', 3); m.core.write(A_PARTY + HC.OFF_XP, '<2I', 6, 13); outputs += m.step(c, 2)
        if victory: m.core.trigger('victoire')
        for number, placement in objects: m.core.item(number, placement)
        outputs += m.step(c, 2); m.core.write(A_PARTY + HC.OFF_XP, '<2I', 0, 0); m.core.write(A_GAME + 4, '<I', 7777)
        m.core.trigger('fin', 0); return outputs + m.step(c, 1)

    def test_fled_vanished_monsters_and_items(self):
        """#141 : qui est mort, enfui ou disparu (par espece), l'or et l'experience, les objets (le nom est demande au moteur, le « ; » est retire ; qu'ils aillent a un membre ou dans le sac)."""
        outputs = self.complete_scenario(); self.assertEqual(len(outputs), 1); d = outputs[0]
        self.assertEqual(d['ennemis'], [{'nom': 'Gluant', 'total': 3, 'vaincus': 1, 'fuis': 1, 'disparus': 1}, {'nom': 'Golem', 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}])
        self.assertEqual((d['issue'], d['or'], d['xp'], d['t']), ('victoire', 13, 6, 7777))
        self.assertEqual(d['objets'], [{'nom': 'herbe médicinale'}, {'nom': 'pierre de vie'}])

    def test_item_name_requested_once_and_fallback_name(self):
        self.complete_scenario(objects=((12, 0), (12, 1), (7, -1), (99, 0)))
        self.assertEqual(len(self.m.core.calls), 3)                                                                   # 12, 7 et 99 : un appel par objet different (le nom est garde)

    def test_items_and_fallback_names_in_dict(self):
        d = self.complete_scenario(objects=((7, 0), (99, -1)))[0]
        self.assertEqual([o['nom'] for o in d['objets']], ['Objet n°7', 'Objet n°99'])                                 # (« <ERR ... > » n'est jamais montre)

    def test_victory_without_item(self):
        d = self.complete_scenario(objects=(), victory=True)[0]; self.assertEqual(d['objets'], [])

    def test_name_requested_from_engine_without_plate(self):
        """Attaque surprise (pas de plaque) : le nom vient du moteur par le numero du monstre, avec une majuscule ; sans reponse du moteur : « Monstre »."""
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut')
        for e, num in enumerate((3, 34, 74, 99, 3)): m.core.place(e, num, e)
        m.step(c, 4)
        for e in range(5): m.core.trigger('mort', e)
        m.core.trigger('victoire'); m.core.trigger('fin', 0); d, = m.step(c, 1)
        self.assertEqual([(e['nom'], e['total']) for e in d['ennemis']], [('Londuleux', 2), ('Armure errante', 1), ('Scara-somniaque', 1), (HC.UNKNOWN_NAME, 1)])
        self.assertEqual(len(m.core.calls), 4)                                                                       # (un appel par numero de monstre different)

    def test_plates_prevail_over_engine_name(self):
        m, c = self.m, self.c; simple_battle(m, c); self.assertEqual(m.core.calls, [])                              # les deux noms viennent des plaques : le moteur n'est pas interroge

    def test_fleeing_group_remaining_monsters_are_counted(self):
        """Le groupe s'enfuit : le monstre qui s'etait enfui est note, ceux qui restent n'ont aucun sort."""
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 3, 0); m.core.place(1, 3, 0); m.core.place(2, 3, 0)
        m.step(c, 3); m.plates(['Golem\n\n\t×3']); m.step(c, 3); m.core.fled(0); m.step(c, 1); m.core.trigger('fuite'); m.core.trigger('fin', 0)
        d, = m.step(c, 1)
        self.assertEqual((d['issue'], d['objets'], d['or'], d['xp']), ('fuite', [], 0, 0))
        self.assertEqual(d['ennemis'], [{'nom': 'Golem', 'total': 3, 'vaincus': 0, 'fuis': 1, 'disparus': 0}])

    def test_for_single_sensor_per_engine(self):
        """BattleSensor.pour(mo) : l'unique ligne d'integration ; les crochets ne sont installes qu'une fois."""
        m = FakeEngine(); a = HC.BattleSensor.for_(m); b = HC.BattleSensor.for_(m)
        self.assertIs(a, b); self.assertTrue(a.active)
        self.assertTrue(all(len(v) == 1 for v in m.core.uc.hooks.values()))
        for _ in range(3): self.assertEqual(HC.BattleSensor.for_(m).do_update(m), [])
        self.assertIsNot(HC.BattleSensor.for_(FakeEngine()), a)

    def test_for_engine_that_refuses_attribute(self):
        class Closed(FakeEngine):
            def __setattr__(self, name_str, value):
                if name_str == '_capteur_combat': raise AttributeError(name_str)
                object.__setattr__(self, name_str, value)
        m = Closed(); a = HC.BattleSensor.for_(m); self.assertIs(HC.BattleSensor.for_(m), a)
        self.assertTrue(all(len(v) == 1 for v in m.core.uc.hooks.values()))

    def test_unexpected_engine_capture_disabled(self):
        m = FakeEngine(bad_version=True); c = HC.BattleSensor(m)
        self.assertFalse(c.active); self.assertEqual(m.core.uc.hooks, {}); self.assertEqual(m.step(c, 3), [])

    def test_missing_hook_capture_disabled(self):
        m = FakeEngine(); del m.core.symbols['_ZN6Global9endBattleEb']; c = HC.BattleSensor(m)
        self.assertFalse(c.active); self.assertEqual(m.core.uc.hooks, {})                                          # (aucun crochet a moitie installe)

    def test_complete_victory(self):
        outputs = simple_battle(self.m, self.c)
        self.assertEqual(outputs, [{'t': 5555, 'ennemis': [{'nom': 'Rat volant', 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}, {'nom': 'Londuleux', 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}], 'or': 13, 'xp': 6, 'issue': 'victoire', 'objets': []}])
        self.assertIsNone(self.c.tracking)

    def test_two_consecutive_battles(self):
        a = simple_battle(self.m, self.c); self.m.state.part = 0xc; self.m.core.drain(0); self.m.core.drain(1); self.m.step(self.c, 5)
        b = simple_battle(self.m, self.c, ('Gluant', 'Chauve-sourat'), (0, 5))
        self.assertEqual([[e['nom'] for e in d['ennemis']] for d in a + b], [['Rat volant', 'Londuleux'], ['Gluant', 'Chauve-sourat']])

    def test_death_index_among_present_monsters(self):
        """execMonsterDeath(i) : i compte les emplacements OCCUPES (getMonsterStatus), pas les emplacements."""
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(2, 3, 0); m.core.place(5, 20, 1); m.core.place(9, 20, 1); m.step(c, 2)
        m.core.trigger('mort', 1); m.step(c)                                                                         # le 2e monstre present = l'emplacement 5
        self.assertEqual([(eng['num'], eng['vaincu']) for eng in c.tracking.monsters], [(3, False), (20, True), (20, False)])

    def test_previous_battle_plates_ignored(self):
        m, c = self.m, self.c; m.plates(['Vieux', 'Nom']); m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.core.place(1, 3, 1); m.step(c, 5)
        self.assertEqual(c.tracking.names, {})                                                                             # plaques d'avant le debut : jamais lues
        m.plates(['Rat volant', 'Londuleux']); m.step(c); self.assertEqual(c.tracking.names, {20: 'Rat volant', 3: 'Londuleux'})

    def test_late_plates(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.step(c, 5); self.assertEqual(c.tracking.names, {})
        m.plates(['Rat volant']); m.step(c); self.assertEqual(c.tracking.names, {20: 'Rat volant'})

    def test_no_plate_generic_name(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.step(c, 3); m.core.trigger('mort', 0)
        m.core.trigger('victoire'); m.core.trigger('fin', 0); d, = m.step(c)
        self.assertEqual(d['ennemis'], [{'nom': HC.UNKNOWN_NAME, 'total': 1, 'vaincus': 1, 'fuis': 0, 'disparus': 0}])

    def test_plates_after_a_death_ignored(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.core.place(1, 3, 1); m.step(c, 3); m.core.trigger('mort', 0); m.step(c)
        m.plates(['Londuleux']); m.step(c, 3); self.assertEqual(c.tracking.names, {})                                      # un groupe a disparu : les correspondances ne sont plus sures

    def test_defeat(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.step(c, 3); m.core.write(A_PARTY + HC.OFF_XP, '<2I', 3, 7); m.step(c)
        m.core.trigger('fin', 1); d, = m.step(c)
        self.assertEqual((d['issue'], d['or'], d['xp']), ('defaite', 0, 0)); self.assertEqual(d['ennemis'], [{'nom': HC.UNKNOWN_NAME, 'total': 1, 'vaincus': 0, 'fuis': 0, 'disparus': 0}])

    def test_defeat_reported_by_result_flag(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.step(c, 3)
        m.core.ram[A_RESULT + HC.OFF_DEFEAT] = 1; m.core.trigger('fin', 0); d, = m.step(c)                              # defaite d'un combat de scenario : endBattle(faux) mais drapeau « perdu »
        self.assertEqual(d['issue'], 'defaite')

    def test_escape(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.core.place(1, 20, 0); m.step(c, 3)
        m.core.trigger('mort', 0); m.core.write(A_PARTY + HC.OFF_XP, '<2I', 3, 7); m.step(c, 2); m.core.trigger('fuite'); m.step(c); m.core.trigger('fuite'); m.core.trigger('fin', 0); d, = m.step(c)
        self.assertEqual((d['issue'], d['or'], d['xp']), ('fuite', 0, 0)); self.assertEqual(d['ennemis'], [{'nom': HC.UNKNOWN_NAME, 'total': 2, 'vaincus': 1, 'fuis': 0, 'disparus': 0}])

    def test_reinforcement_during_battle(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.step(c, 3); m.core.place(1, 20, 0); m.step(c, 2)
        self.assertEqual([eng['num'] for eng in c.tracking.monsters], [20, 20])

    def test_outside_battle_nothing_to_do(self):
        m, c = self.m, self.c; m.step(c, 5); n = m.core.reads
        self.assertEqual(m.step(c, 1000), []); self.assertEqual(m.core.reads, n)                                    # aucune lecture de memoire hors combat

    def test_end_without_start_ignored(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.place(0, 20, 0); m.step(c, 3)
        m.core.trigger('mort', 0); m.core.trigger('victoire'); m.core.trigger('fin', 0); self.assertEqual(m.step(c, 2), [])                  # capteur cree en plein combat : rien de faux

    def test_savestate_loaded_in_battle(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.step(c, 3); self.assertIsNotNone(c.tracking)
        m.state = FakeState(); m.state.part = HC.PART_BATTLE; m.frames -= 40                                          # Engine.etat est remplace par etats.appliquer, images revient en arriere
        m.step(c); self.assertIsNone(c.tracking)
        m.core.trigger('mort', 0); m.core.trigger('victoire'); m.core.trigger('fin', 0); self.assertEqual(m.step(c, 2), [])

    def test_skipped_frames(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.step(c, 3)
        m.frames += 500; m.step(c); self.assertIsNone(c.tracking)                                                          # l'etat charge pouvait avoir le meme objet Etat : l'ecart d'images le trahit

    def test_frames_backward_same_objects(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.step(c, 3)
        m.frames -= 100; m.step(c); self.assertIsNone(c.tracking)

    def test_a_new_start_replaces_the_tracking(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.step(c, 3)
        m.core.drain(0); m.core.trigger('debut'); m.core.place(0, 3, 0); m.step(c, 2); self.assertEqual([eng['num'] for eng in c.tracking.monsters], [3])        # (le premier n'a pas fini : jamais rapporte)

    def test_battle_exit_without_end_is_abandoned(self):
        m, c = self.m, self.c; m.state.part = HC.PART_BATTLE; m.core.trigger('debut'); m.core.place(0, 20, 0); m.step(c, 3)
        m.state.part = 0xc; m.step(c, HC.MAX_FRAMES_WITHOUT_BATTLE - 1); self.assertIsNotNone(c.tracking)
        m.step(c, 3); self.assertIsNone(c.tracking)                                                                        # retour au titre, sauvegarde chargee... : on ne garde pas un faux combat

    def test_error_never_propagated(self):
        class Fake: pass
        self.assertEqual(self.c.do_update(Fake()), []); self.assertIsNotNone(self.c.error)
        self.assertEqual(self.c.do_update(self.m), [])                                                                       # le capteur continue de servir
        m, c = self.m, self.c; self.assertEqual(simple_battle(m, c)[0]['issue'], 'victoire')

    def test_failing_hook_raises_nothing(self):
        self.m.core.mem = lambda a, n: (_ for _ in ()).throw(RuntimeError('lecture impossible'))
        self.m.core.trigger('mort', 0); self.m.core.trigger('fin', 0); self.m.core.trigger('debut')                # (les crochets avalent l'erreur : l'emulateur ne s'arrete jamais)

    def test_guardrail_events(self):
        for _ in range(1000): self.m.core.trigger('victoire')
        self.assertLessEqual(len(self.c.events), 200)


# ---------------------------------------------------------------------------------------------------------------------------------- moteur reel (facultatif)
APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
RE_XP = re.compile(r"reçoit (\d+) points? d'expérience")
RE_GOLD = re.compile(r"reçoit (\d+) pièces? d'or")


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class RealEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import unicorn; from dq4_pc.core import engine as ENGINE; from dq4_pc.persistence import savestates as SS
        cls.ENGINE, cls.SS, cls.unicorn = ENGINE, SS, unicorn
        cls.eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_hcb_')); c = cls.c = cls.eng.core
        cls.eng.load_save(1)
        for _ in range(200): cls.eng.step(0, 0)
        cls.cap = HC.BattleSensor(cls.eng)
        assert cls.cap.active
        cls.groups = [(3, 1)]; cls.enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
        def force(u, addr, sz, ud):                                                       # composition de la rencontre : 4 groupes au plus, (numero de monstre, nombre) a Encount + 0x34 / 0x44
            for j in range(4):
                i, n = cls.groups[j] if j < len(cls.groups) else (0, 0)
                c.mem_w(cls.enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(cls.enc + 0x44 + 4 * j, struct.pack('<I', n))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, force, None, a, a)
        c.uc.ctl_flush_tb()
        cls.party = c.export('_ZN6status7g_PartyE'); cls.orig = c.export('_ZN6status9PartyData15originalPlayer_E'); cls.double = c.export('_ZN6status10BaseAction11doubleFlag_E')
        cls.initial = SS.snapshot(cls.eng)

    def setUp(self):
        self.SS.apply(self.eng, self.initial)
        self.battles, self.msgs = [], []
        for _ in range(3): self.step()
        self.battles.clear(); self.msgs.clear()

    # -- outils
    def party_gold(self): return struct.unpack('<I', self.c.mem(self.party + 0x2e0, 4))[0]

    def xp_members(self):
        """Experience de chaque membre du groupe (HaveStatus +8 de HaveStatusInfo + 0x48 ; -1 = pas d'experience, ex. un invite)."""
        idx = [i for i in struct.unpack('<13I', self.c.mem(self.party + 0x304, 13 * 4)) if i]
        return {i: struct.unpack('<I', self.c.mem(self.orig + 0x530 * i + 0x60, 4))[0] for i in idx}

    def step(self, p=0, d=0):
        self.eng.step(p, d); self.eng.ui.damage = []
        self.battles.extend(self.cap.do_update(self.eng))
        for r in self.eng.sensor.drain(): self.msgs.append(r['texte'].replace('\xa0', ' ').replace('\n', ' / ').strip(' /'))

    def launch(self, groups):
        ENGINE = self.ENGINE; type(self).groups = groups
        self.c.call(self.c.export('_ZN6Global11startBattleEv'), self.eng._global(), label='startBattle')
        n = 0
        while self.eng.state.part != ENGINE.PART_BATTLE and n < 1500: self.step(); n += 1
        self.assertEqual(self.eng.state.part, ENGINE.PART_BATTLE)

    def play(self, actions=('combattre',), maximum=6000, after=None):
        """Joue le combat comme le fait test_battle_speed (A sur le menu, avance des messages) ; `actions` : une par menu de tete, 'combattre' ou 'fuir' (bouton 3 du menu de type 30)."""
        ENGINE, eng = self.ENGINE, self.eng; st = {'rel': None, 'att': 0, 'k': 0}
        for i in range(maximum):
            p = d = 0
            if st['rel'] is not None: eng.send_menu(st['rel'], 1, -1, 0); st['rel'] = None
            port = eng.active_menu(); f = eng.ui.f.get(port) if port is not None else None
            if port is not None and not eng.msg_visible:
                st['att'] += 1
                if st['att'] % 4 == 0:
                    if f['type'] == 30:
                        action = actions[min(st['k'], len(actions) - 1)]; st['k'] += 1
                        eng.send_menu(port, 1, 3, 0x10) if action == 'fuir' else eng.send_menu(port, 1, -1, 0x10)
                    else: eng.send_menu(port, 1, -1, 0x10)
                    st['rel'] = port
            elif eng.msg_visible and (eng.ui.msg.get('feed') or eng.message_state()[1] in (3, 5)):
                st['att'] += 1
                if st['att'] % 4 == 0: p = d = ENGINE.A
            else: st['att'] = 0
            prev = eng.state.part; self.step(p, d)
            if after: after(i)
            if eng.state.part != ENGINE.PART_BATTLE and prev == ENGINE.PART_BATTLE: return i
        self.fail('le combat ne se termine pas')

    def number_list(self, regex):
        return [int(x) for m in self.msgs for x in regex.findall(m)]

    def check_victory(self, battle, or0, xp0):
        """Le dict, le texte du jeu et la memoire disent la meme chose."""
        self.assertEqual(battle['issue'], 'victoire')
        self.assertEqual(self.number_list(RE_XP), [battle['xp']], 'experience du message')
        self.assertEqual(self.number_list(RE_GOLD), [battle['or']], 'or du message')
        self.assertEqual(self.party_gold() - or0, battle['or'], 'or du groupe (avant / apres)')
        after = self.xp_members(); gains = {i: after[i] - xp0[i] for i in after if xp0[i] != 0xffffffff}
        self.assertTrue(gains and all(g == battle['xp'] for g in gains.values()), 'experience de chaque membre %r' % (gains,))
        for e in battle['ennemis']: self.assertEqual(e['vaincus'] + e['fuis'] + e['disparus'], e['total'])           # (un monstre peut s'enfuir : « Le gluant s'enfuit ! » -- compte comme tel, comme le message du jeu)
        self.assertEqual(sum(e['fuis'] for e in battle['ennemis']), sum(1 for m in self.msgs if "s'enfuit" in m), 'fuites des monstres : le message du jeu et le dict')
        text = ' | '.join(self.msgs).lower()
        for e in battle['ennemis']: self.assertIn(e['nom'].lower(), text, 'le nom doit etre celui que le jeu ecrit')

    # -- scenarios
    def test_victory_two_species(self):
        or0, xp0 = self.party_gold(), self.xp_members()
        self.launch([(3, 2), (0, 1)]); self.play()
        self.assertEqual(len(self.battles), 1); c = self.battles[0]
        self.assertEqual([(e['nom'], e['total']) for e in c['ennemis']], [('Londuleux', 2), ('Gluant', 1)])
        self.assertGreater(c['or'], 0); self.assertGreater(c['xp'], 0); self.check_victory(c, or0, xp0)
        self.assertGreaterEqual(c['t'], 0)

    def test_four_species_appearance_order(self):
        or0, xp0 = self.party_gold(), self.xp_members()
        self.launch([(3, 2), (20, 1), (0, 3), (5, 1)]); self.play()
        c, = self.battles
        self.assertEqual([(e['nom'], e['total']) for e in c['ennemis']], [('Londuleux', 2), ('Rat volant', 1), ('Gluant', 3), ('Chauve-sourat', 1)])
        self.check_victory(c, or0, xp0)

    def test_victory_message_per_character(self):
        """Le groupe a plusieurs membres : « Chaque membre de l'équipe reçoit N points d'expérience » (N = la valeur par membre, la meme pour tous) et « L'équipe reçoit M pièces d'or » (M = le total)."""
        self.launch([(20, 3)]); self.play(); c, = self.battles
        self.assertTrue(any('Chaque membre' in m for m in self.msgs) or len(self.xp_members()) < 2)
        self.assertEqual(self.number_list(RE_XP), [c['xp']]); self.assertEqual(self.number_list(RE_GOLD), [c['or']])

    def test_experience_doubled(self):
        """Le jeu double l'or et l'experience (BaseAction::doubleFlag_) au moment de les verser : le dict donne le nombre du message, pas celui des monstres."""
        target = self.c.export('_ZN23BattleExecDefeatMonster10initializeEv')
        h = self.c.uc.hook_add(self.unicorn.UC_HOOK_CODE, lambda u, a, s, d: self.c.mem_w(self.double, b'\x01'), None, target, target); self.c.uc.ctl_flush_tb()
        try:
            or0, xp0 = self.party_gold(), self.xp_members()
            self.launch([(20, 2)]); self.play(); c, = self.battles
        finally:
            self.c.uc.hook_del(h); self.c.mem_w(self.double, b'\x00')
        self.assertEqual((c['xp'], c['or']), (12, 28)); self.check_victory(c, or0, xp0)                       # 2 rats volants : 3 d'experience et 7 d'or chacun, doubles

    def test_escape_after_a_death(self):
        or0, xp0 = self.party_gold(), self.xp_members()
        self.launch([(3, 2), (0, 3)]); self.play(actions=('combattre', 'fuir'))
        c, = self.battles
        self.assertEqual((c['issue'], c['or'], c['xp']), ('fuite', 0, 0))
        self.assertEqual([(e['nom'], e['total'], e['vaincus']) for e in c['ennemis']], [('Londuleux', 2, 1), ('Gluant', 3, 0)])
        self.assertEqual(self.party_gold(), or0); self.assertEqual(self.xp_members(), xp0)                       # le moteur ne verse rien pour une fuite
        self.assertTrue(any("s'enfuit" in m for m in self.msgs))

    def test_successful_escape_after_failures(self):
        """« Mais l'ennemi bloque le passage ! » : BattleExecEscape::setup tourne a chaque tentative ; seule la derniere termine le combat."""
        self.launch([(3, 2), (20, 2)]); self.play(actions=('fuir',), maximum=8000)
        c, = self.battles
        self.assertEqual((c['issue'], c['or'], c['xp']), ('fuite', 0, 0)); self.assertEqual([e['vaincus'] for e in c['ennemis']], [0, 0])

    def test_defeat(self):
        or0 = self.party_gold()
        self.launch([(150, 3)]); self.play(maximum=9000)
        c, = self.battles
        self.assertEqual((c['issue'], c['or'], c['xp']), ('defaite', 0, 0))
        self.assertEqual([(e['total'], e['vaincus']) for e in c['ennemis']], [(3, 0)]); self.assertTrue(c['ennemis'][0]['nom'])
        self.assertLessEqual(self.party_gold(), or0)                                                              # (le jeu retire la moitie de l'or a un groupe anéanti)

    def test_two_consecutive_battles(self):
        self.launch([(20, 1)]); self.play(); self.launch([(3, 1), (0, 1)]); self.play()
        self.assertEqual([[e['nom'] for e in c['ennemis']] for c in self.battles], [['Rat volant'], ['Londuleux', 'Gluant']])
        self.assertLess(self.battles[0]['t'], self.battles[1]['t']); self.assertTrue(all(c['issue'] == 'victoire' for c in self.battles))

    def test_interrupted_by_state_loaded_in_town(self):
        """Etat pris en ville, charge en plein combat : rien de faux, pas de plantage, et le combat suivant est bien rapporte."""
        SS = self.SS; town = SS.snapshot(self.eng)
        self.launch([(3, 2), (0, 1)])
        for _ in range(500): self.step()
        self.assertIsNotNone(self.cap.tracking)
        SS.apply(self.eng, town)
        for _ in range(200): self.step()
        self.assertIsNone(self.cap.tracking); self.assertEqual(self.battles, [])
        self.launch([(20, 1)]); self.play(); self.assertEqual([[e['nom'] for e in c['ennemis']] for c in self.battles], [['Rat volant']])

    def test_interrupted_by_mid_battle_state(self):
        """Etat pris en plein combat : le combat joue jusqu'au bout est rapporte ; l'etat recharge puis termine ne l'est pas (on n'a pas vu le debut de ce combat-la)."""
        SS = self.SS; self.launch([(3, 2), (0, 2)])
        for _ in range(480): self.step()
        middle = SS.snapshot(self.eng); self.play(); self.assertEqual(len(self.battles), 1); self.battles.clear()
        SS.apply(self.eng, middle); self.step(); self.assertEqual(self.eng.state.part, self.ENGINE.PART_BATTLE)
        self.play(); self.assertEqual(self.battles, [])

    def test_sensor_created_mid_battle(self):
        self.launch([(20, 2)])
        for _ in range(300): self.step()
        late = HC.BattleSensor(self.eng); outputs = []
        for _ in range(4000):
            self.step(*self._key_presses()); outputs.extend(late.do_update(self.eng))
            if self.eng.state.part != self.ENGINE.PART_BATTLE: break
        self.assertEqual(outputs, [])

    def _key_presses(self):
        eng = self.eng
        if eng.msg_visible and (eng.ui.msg.get('feed') or eng.message_state()[1] in (3, 5)): return self.ENGINE.A, self.ENGINE.A
        port = eng.active_menu()
        if port is not None and not eng.msg_visible: eng.send_menu(port, 1, -1, 0x10)
        return 0, 0

    def test_sensor_created_after_battles(self):
        """Un capteur installe quand le moteur a deja execute le code de combat (blocs traduits par l'emulateur) fonctionne aussi."""
        self.launch([(20, 1)]); self.play(); self.battles.clear()
        late = HC.BattleSensor(self.eng); outputs = []
        self.launch([(3, 1)])
        orig = self.step
        def step(p=0, d=0): orig(p, d); outputs.extend(late.do_update(self.eng))
        self.step = step
        try: self.play()
        finally: del self.step
        self.assertEqual([[e['nom'] for e in c['ennemis']] for c in outputs], [['Londuleux']]); self.assertEqual(outputs[0]['xp'], self.battles[0]['xp'])

    def names_after_plates(self, ids):
        """Lance un combat contre `ids` (un de chaque) et joue jusqu'a ce que le capteur ait lu les plaques (ouverture du choix de la cible) ; -> ({numero: nom}, messages d'apparition)."""
        class Finished(Exception): pass
        def after(_i):
            if self.cap.tracking is not None and all(i in self.cap.tracking.names for i in ids): raise Finished()
        self.launch([(i, 1) for i in ids])
        try: self.play(maximum=2000, after=after)
        except Finished: pass
        return dict(self.cap.tracking.names), [m for m in self.msgs if 'apparaît' in m]

    def test_full_names_of_monsters_with_long_names(self):
        """Le nom du dict est celui que le jeu ecrit dans son message d'apparition (sans les marques de coupure « ; » et « $ »), meme quand la plaque le coupe sur deux lignes."""
        names, appearances = self.names_after_plates([0, 34, 74, 82])
        self.assertEqual(names, {0: 'Gluant', 34: 'Armure errante', 74: 'Scara-somniaque', 82: 'Gluant de mercure'})
        text = ' | '.join(appearances).lower().replace(';', '').replace('$', '-')
        for n in names.values(): self.assertIn(n.lower(), text)

    def test_plate_names_in_group_order(self):
        """Quatre especes distinctes, dans un ordre qui n'est ni celui des numeros ni l'alphabetique : chaque numero de monstre recoit SON nom (verifie par le message d'apparition)."""
        names, appearances = self.names_after_plates([20, 3, 5, 0])
        self.assertEqual(names, {20: 'Rat volant', 3: 'Londuleux', 5: 'Chauve-sourat', 0: 'Gluant'})
        self.assertEqual([m.lower() for m in appearances], ['un rat volant apparaît !', 'un londuleux apparaît !', 'un chauve-sourat apparaît !', 'un gluant apparaît !'])

    # -- #141 : monstres enfuis / disparus, objets gagnes
    def force_spell(self, slot, sort):
        """Fait partir un monstre comme le fait le jeu : etat « mort » (setDeath) et drapeau de fuite (bit 4 de HaveStatusInfo + 0x424) ou de disparition (bit 5) ; checkDeathMonster le compte alors a l'image suivante."""
        c = self.c; hsi = c.export('_ZN6status9g_MonsterE') + HC.MONSTERS_START + slot * HC.MONSTER_STEP + 0x10
        c.call(c.export('_ZN6status14HaveStatusInfo13setEscapeFlagEb' if sort == 'fui' else '_ZN6status14HaveStatusInfo16setDisappearFlagEb'), hsi, 1, label='drapeau')
        c.call(c.export('_ZN6status14HaveStatusInfo8setDeathEv'), hsi, label='setDeath')

    def test_fled_monster_and_vanished_monster(self):
        """Un monstre enfui et un monstre disparu (forces dans la memoire du jeu) sont notes par espece ; les autres sont vaincus par le groupe ; l'issue est une victoire."""
        state = {'fait': False}
        def cb(i):
            if i == 30 and not state['fait']: state['fait'] = True; self.force_spell(1, 'fui'); self.force_spell(2, 'disparu')
        self.launch([(3, 4)]); self.play(after=cb, maximum=9000)
        self.assertTrue(state['fait']); c, = self.battles
        e, = c['ennemis']; self.assertEqual((e['nom'], e['total'], e['fuis'], e['disparus']), ('Londuleux', 4, 1, 1)); self.assertEqual(e['vaincus'], 2)
        self.assertEqual(c['issue'], 'victoire'); self.assertGreater(c['xp'], 0)

    def test_item_won_at_end_of_battle(self):
        """Un objet donne par le jeu en fin de combat (« Le londuleux laisse tomber un coffre au trésor ! ... Il contient un arc de chasseur ! » ; le butin est ecrit dans le groupe de monstres comme le jeu le fait a la mort du monstre, BattleExecItem le donne) : son nom est celui du message du jeu."""
        c = self.c; mp = c.export('_ZN6status9g_MonsterE'); state = {'fait': False}
        def cb(i):                                                                                     # (le jeu ecrit le butin du monstre quand il meurt : on pose le notre juste apres, avant la victoire)
            if not state['fait'] and any('vaincu' in m for m in self.msgs):
                state['fait'] = True; c.call(c.export('_ZN6status12MonsterParty11setDropItemEi'), mp, 12, label='drop'); c.call(c.export('_ZN6status12MonsterParty18setDropItemMonsterEi'), mp, 3, label='drop monstre')
        self.launch([(3, 1)]); self.play(after=cb, maximum=9000)
        self.assertTrue(state['fait']); d, = self.battles; self.assertEqual(d['issue'], 'victoire')
        self.assertEqual(len(d['objets']), 1, self.msgs); o = d['objets'][0]
        self.assertTrue(o['nom'] and not o['nom'].startswith('Objet n'), o)
        text = ' | '.join(self.msgs).lower().replace(';', ''); self.assertIn(o['nom'].lower(), text, 'le nom doit etre celui que le jeu ecrit')

    def test_cost_outside_battle(self):
        import time
        t0 = time.perf_counter(); n = 600
        for _ in range(n): self.eng.step(0, 0)
        t1 = time.perf_counter()
        for _ in range(n): self.eng.frames += 1; self.cap.do_update(self.eng)
        t2 = time.perf_counter()
        step_us, update_us = (t1 - t0) / n * 1e6, (t2 - t1) / n * 1e6
        print('\n  hors combat : maj %.1f us par image (un pas du moteur : %.0f us)' % (update_us, step_us))
        self.assertLess(update_us, 200.0); self.assertLess(update_us, step_us * 0.1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
