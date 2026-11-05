"""Option « PV et PM restaures au niveau superieur » (reglage `level_heal`, Engine.level_heal) : le moteur d'origine tourne sous Unicorn.

    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 -m unittest tools.test_level_hp

Sans ces deux variables, les tests du moteur sont ignores (seules les constantes sont verifiees). Les sauvegardes ne sont ouvertes qu'en lecture : le moteur ecrit dans un dossier temporaire.
Ce qui est mesure :
  - appel direct de status::HaveStatus::levelup(bool) sur des membres du groupe (PV 3, PM 1 avant) : option desactivee, les PV et PM restent ; option activee, ils passent au maximum du NOUVEAU niveau ;
  - un vrai combat gagne (monstre force, un membre a 1 point du niveau suivant) : la montee de niveau du jeu passe par cette fonction avec l'argument faux (appelee par HaveStatusInfo::levelup), et le membre
    sort du combat avec tous ses PV quand l'option est activee, sans changement quand elle est desactivee."""
import os, struct, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.core import engine as ENGINE
from dq4_pc.persistence import settings as RG

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
OFF_HP, OFF_HP_MAX, OFF_MP, OFF_MP_MAX = 0x22, 0x24, 0x26, 0x28          # dans HaveStatus (le meme ordre que getHp / getHpMax / getMp / getMpMax du moteur)
PLAYER_STRIDE, OFF_HAVESTATUS = 0x530, 0x58                                  # PlayerStatus : taille ; HaveStatus a +0x58 (HaveStatusInfo +0x10, puis +0x48)


class Constants(unittest.TestCase):
    def test_setting_disabled_by_default(self):
        self.assertIs(RG.DEFAULT['soin_niveau'], False)
        self.assertIn('soin_niveau', RG.SOUND_TEXT_BOOLEANS)               # une valeur qui n'est pas un booleen retombe sur « desactive »

    def test_targeted_instruction(self):
        """`tbz w20, #0, #+0x10` : bit 0 du registre w20, saut de 16 octets."""
        w = ENGINE.TBZ_W20_0
        self.assertEqual(w >> 24, 0x36); self.assertEqual(w & 0x1f, 20); self.assertEqual((w >> 5) & 0x3fff, 4); self.assertEqual(ENGINE.HAVESTATUS_LEVELUP_END, 0x3f8)


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class RealEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_niv_')); cls.c = cls.eng.core
        cls.eng.load_save(1)
        for _ in range(200): cls.eng.step(0, 0)
        cls.orig = cls.c.export('_ZN6status9PartyData15originalPlayer_E'); cls.party = cls.c.export('_ZN6status7g_PartyE')
        cls.members = [i for i in struct.unpack('<13I', cls.c.mem(cls.party + 0x304, 13 * 4)) if i]

    def hs(self, i): return self.orig + PLAYER_STRIDE * i + OFF_HAVESTATUS

    def state(self, i):
        h = self.c.mem(self.hs(i), 0x30); return h[0xe], struct.unpack_from('<4H', h, OFF_HP)

    def place(self, i, hp, mp):
        self.c.mem_w(self.hs(i) + OFF_HP, struct.pack('<H', hp)); self.c.mem_w(self.hs(i) + OFF_MP, struct.pack('<H', mp))

    def test_hook_installed(self):
        self.assertIs(self.eng.level_heal, False)                          # par defaut : comme le jeu

    def test_direct_call(self):
        fn = self.eng.E('_ZN6status10HaveStatus7levelupEb'); i = self.members[0]
        for heal in (False, True):
            self.eng.level_heal = heal; self.place(i, 3, 1)
            level0, _ = self.state(i); self.c.call(fn, self.hs(i), 0, label='levelup'); level_nodes, (hp, hpm, mp, mpm) = self.state(i)
            self.assertEqual(level_nodes, level0 + 1)
            if heal: self.assertEqual((hp, mp), (hpm, mpm)); self.assertGreater(hpm, 3)
            else: self.assertEqual((hp, mp), (3, 1))
        self.eng.level_heal = False

    def test_battle_won(self):
        import unicorn
        for heal in (False, True):
            hp = self.battle_with_level(heal)
            self.assertIsNotNone(hp, 'le combat ne se termine pas')
            level0, level_nodes, (h, hm, m, mm), calls = hp
            self.assertEqual(level_nodes, level0 + 1, 'une montee de niveau')
            self.assertEqual(calls, [0], 'HaveStatus::levelup appelee une fois, avec l\'argument faux')
            if heal: self.assertEqual(h, hm)
            else: self.assertEqual(h, 2)

    def battle_with_level(self, heal):
        import unicorn
        eng, c = self.eng, self.c
        if not hasattr(type(self), '_started'):
            type(self)._enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
            def force(u, addr, sz, ud):                                                     # rencontre : un monstre du groupe 3 (numero de monstre, nombre) a Encount + 0x34 / 0x44
                for j in range(4):
                    i, n = (3, 1) if j == 0 else (0, 0)
                    c.mem_w(self._enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(self._enc + 0x44 + 4 * j, struct.pack('<I', n))
            a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, force, None, a, a)
            fn = eng.E('_ZN6status10HaveStatus7levelupEb'); type(self)._calls = []
            c.uc.hook_add(unicorn.UC_HOOK_CODE, lambda uc, ad, sz, u: self._calls.append(uc.reg_read(c.XREG[1]) & 0xff), None, fn, fn)
            c.uc.ctl_flush_tb(); type(self)._started = True
        self._calls.clear(); eng.level_heal = heal
        i = next(m for m in self.members if struct.unpack_from('<I', c.mem(self.hs(m), 0x30), 0x18)[0] > 0)
        need = struct.unpack_from('<I', c.mem(self.hs(i), 0x30), 0x18)[0]
        c.mem_w(self.hs(i) + 8, struct.pack('<I', need - 1)); self.place(i, 2, 0)           # a 1 point du niveau suivant, 2 PV
        for m in self.members:
            if m != i: c.mem_w(self.hs(m) + OFF_MP, struct.pack('<H', 0))                  # les autres n'ont plus de PM : personne ne peut soigner (un sort de soin d'un compagnon fausserait la mesure)
        level0, _ = self.state(i)
        c.call(c.export('_ZN6Global11startBattleEv'), eng._global(), label='startBattle')
        n = 0
        while eng.state.part != ENGINE.PART_BATTLE and n < 1500: eng.step(0, 0); n += 1
        st = {'rel': None, 'att': 0}
        for _ in range(6000):
            p = d = 0
            if st['rel'] is not None: eng.send_menu(st['rel'], 1, -1, 0); st['rel'] = None
            port = eng.active_menu()
            if port is not None and not eng.msg_visible:
                st['att'] += 1
                if st['att'] % 4 == 0: eng.send_menu(port, 1, -1, 0x10); st['rel'] = port
            elif eng.msg_visible and (eng.ui.msg.get('feed') or eng.message_state()[1] in (3, 5)):
                st['att'] += 1
                if st['att'] % 4 == 0: p = d = ENGINE.A
            else: st['att'] = 0
            prev = eng.state.part; eng.step(p, d); eng.ui.damage = []
            if eng.state.part != ENGINE.PART_BATTLE and prev == ENGINE.PART_BATTLE:
                level_nodes, hit_points = self.state(i); eng.level_heal = False
                return level0, level_nodes, hit_points, list(self._calls)
        eng.level_heal = False
        return None


if __name__ == '__main__':
    unittest.main()
