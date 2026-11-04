"""Option « PV et PM restaures au niveau superieur » (reglage `soin_niveau`, Moteur.soin_niveau) : le moteur d'origine tourne sous Unicorn.

    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 -m unittest outils.test_niveau_pv

Sans ces deux variables, les tests du moteur sont ignores (seules les constantes sont verifiees). Les sauvegardes ne sont ouvertes qu'en lecture : le moteur ecrit dans un dossier temporaire.
Ce qui est mesure :
  - appel direct de status::HaveStatus::levelup(bool) sur des membres du groupe (PV 3, PM 1 avant) : option desactivee, les PV et PM restent ; option activee, ils passent au maximum du NOUVEAU niveau ;
  - un vrai combat gagne (monstre force, un membre a 1 point du niveau suivant) : la montee de niveau du jeu passe par cette fonction avec l'argument faux (appelee par HaveStatusInfo::levelup), et le membre
    sort du combat avec tous ses PV quand l'option est activee, sans changement quand elle est desactivee."""
import os, struct, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import moteur as MO
from dq4_pc.persistance import reglages as RG

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
OFF_HP, OFF_PV_MAX, OFF_PM, OFF_PM_MAX = 0x22, 0x24, 0x26, 0x28          # dans HaveStatus (le meme ordre que getHp / getHpMax / getMp / getMpMax du moteur)
PAS_JOUEUR, OFF_HAVESTATUS = 0x530, 0x58                                  # PlayerStatus : taille ; HaveStatus a +0x58 (HaveStatusInfo +0x10, puis +0x48)


class Constantes(unittest.TestCase):
    def test_reglage_desactive_par_defaut(self):
        self.assertIs(RG.DEFAUT['soin_niveau'], False)
        self.assertIn('soin_niveau', RG.BOOLEENS_SON_TEXTE)               # une valeur qui n'est pas un booleen retombe sur « desactive »

    def test_instruction_visee(self):
        """`tbz w20, #0, #+0x10` : bit 0 du registre w20, saut de 16 octets."""
        w = MO.TBZ_W20_0
        self.assertEqual(w >> 24, 0x36); self.assertEqual(w & 0x1f, 20); self.assertEqual((w >> 5) & 0x3fff, 4); self.assertEqual(MO.HAVESTATUS_LEVELUP_FIN, 0x3f8)


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class MoteurReel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_niv_')); cls.c = cls.mo.core
        cls.mo.charger_sauvegarde(1)
        for _ in range(200): cls.mo.step(0, 0)
        cls.orig = cls.c.export('_ZN6status9PartyData15originalPlayer_E'); cls.party = cls.c.export('_ZN6status7g_PartyE')
        cls.membres = [i for i in struct.unpack('<13I', cls.c.mem(cls.party + 0x304, 13 * 4)) if i]

    def hs(self, i): return self.orig + PAS_JOUEUR * i + OFF_HAVESTATUS

    def etat(self, i):
        h = self.c.mem(self.hs(i), 0x30); return h[0xe], struct.unpack_from('<4H', h, OFF_HP)

    def poser(self, i, hp, mp):
        self.c.mem_w(self.hs(i) + OFF_HP, struct.pack('<H', hp)); self.c.mem_w(self.hs(i) + OFF_PM, struct.pack('<H', mp))

    def test_crochet_installe(self):
        self.assertIs(self.mo.soin_niveau, False)                          # par defaut : comme le jeu

    def test_appel_direct(self):
        fn = self.mo.E('_ZN6status10HaveStatus7levelupEb'); i = self.membres[0]
        for soin in (False, True):
            self.mo.soin_niveau = soin; self.poser(i, 3, 1)
            niv0, _ = self.etat(i); self.c.call(fn, self.hs(i), 0, label='levelup'); niv, (hp, hpm, mp, mpm) = self.etat(i)
            self.assertEqual(niv, niv0 + 1)
            if soin: self.assertEqual((hp, mp), (hpm, mpm)); self.assertGreater(hpm, 3)
            else: self.assertEqual((hp, mp), (3, 1))
        self.mo.soin_niveau = False

    def test_combat_gagne(self):
        import unicorn
        for soin in (False, True):
            hp = self.combat_avec_niveau(soin)
            self.assertIsNotNone(hp, 'le combat ne se termine pas')
            niv0, niv, (h, hm, m, mm), appels = hp
            self.assertEqual(niv, niv0 + 1, 'une montee de niveau')
            self.assertEqual(appels, [0], 'HaveStatus::levelup appelee une fois, avec l\'argument faux')
            if soin: self.assertEqual(h, hm)
            else: self.assertEqual(h, 2)

    def combat_avec_niveau(self, soin):
        import unicorn
        mo, c = self.mo, self.c
        if not hasattr(type(self), '_depart'):
            type(self)._enc = c.call(c.export('_ZN7Encount12getSingletonEv'), label='enc')
            def forcer(u, adr, sz, ud):                                                     # rencontre : un monstre du groupe 3 (numero de monstre, nombre) a Encount + 0x34 / 0x44
                for j in range(4):
                    i, n = (3, 1) if j == 0 else (0, 0)
                    c.mem_w(self._enc + 0x34 + 4 * j, struct.pack('<I', i)); c.mem_w(self._enc + 0x44 + 4 * j, struct.pack('<I', n))
            a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, forcer, None, a, a)
            fn = mo.E('_ZN6status10HaveStatus7levelupEb'); type(self)._appels = []
            c.uc.hook_add(unicorn.UC_HOOK_CODE, lambda uc, ad, sz, u: self._appels.append(uc.reg_read(c.XREG[1]) & 0xff), None, fn, fn)
            c.uc.ctl_flush_tb(); type(self)._depart = True
        self._appels.clear(); mo.soin_niveau = soin
        i = next(m for m in self.membres if struct.unpack_from('<I', c.mem(self.hs(m), 0x30), 0x18)[0] > 0)
        need = struct.unpack_from('<I', c.mem(self.hs(i), 0x30), 0x18)[0]
        c.mem_w(self.hs(i) + 8, struct.pack('<I', need - 1)); self.poser(i, 2, 0)           # a 1 point du niveau suivant, 2 PV
        for m in self.membres:
            if m != i: c.mem_w(self.hs(m) + OFF_PM, struct.pack('<H', 0))                  # les autres n'ont plus de PM : personne ne peut soigner (un sort de soin d'un compagnon fausserait la mesure)
        niv0, _ = self.etat(i)
        c.call(c.export('_ZN6Global11startBattleEv'), mo._global(), label='startBattle')
        n = 0
        while mo.etat.partie != MO.PARTIE_COMBAT and n < 1500: mo.step(0, 0); n += 1
        st = {'rel': None, 'att': 0}
        for _ in range(6000):
            p = d = 0
            if st['rel'] is not None: mo.envoyer_menu(st['rel'], 1, -1, 0); st['rel'] = None
            port = mo.menu_actif()
            if port is not None and not mo.msg_visible:
                st['att'] += 1
                if st['att'] % 4 == 0: mo.envoyer_menu(port, 1, -1, 0x10); st['rel'] = port
            elif mo.msg_visible and (mo.ui.msg.get('feed') or mo.etat_message()[1] in (3, 5)):
                st['att'] += 1
                if st['att'] % 4 == 0: p = d = MO.A
            else: st['att'] = 0
            prec = mo.etat.partie; mo.step(p, d); mo.ui.degats = []
            if mo.etat.partie != MO.PARTIE_COMBAT and prec == MO.PARTIE_COMBAT:
                niv, pv = self.etat(i); mo.soin_niveau = False
                return niv0, niv, pv, list(self._appels)
        mo.soin_niveau = False
        return None


if __name__ == '__main__':
    unittest.main()
