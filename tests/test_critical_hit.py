"""Coup critique (« kaishin », retour de Sylfried, 14 h 08 : « il manque l'effet de coup critique sur les ennemis ? ») : ce que le moteur demande a la visionneuse.

Moteur reel (Unicorn), slot 4, un monstre faible (Encount + 0x34 / 0x44). Le critique est force sur le heros en posant `BaseAction::kaishinFlag_` (LIB + 0x25c6ed) a la sortie de
`BaseAction::checkActorKaishin` (0x1a81dc) quand l'acteur est de notre cote (`[acteur + 8]` = 0 ; 1 = monstres, qui le tirent au sort : `rand(0x20) == 0`). Constat :
  - un SECOND modele d'effet (5344, emplacement 3) est charge au meme instant que l'effet du coup (5303, emplacement 2), 17 images ; la visionneuse le dessine comme tout modele de combat ;
  - le bruitage 407 (`SE0407.akb`, present dans les donnees) est demande, plus un 0 (aucun fichier : sans effet) ;
  - le nombre de degats est 2,5 a 3 fois plus grand (8 -> 26, 11 -> 27 mesures) et le texte « Coup critique ! » s'ajoute ;
  - AUCUN paquet 34 (`cmd_screen_effect`), pas de secousse de message, pas d'eclair : les effets d'ecran 3, 5 et 6 n'ont aucun rapport avec les critiques.

    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 tools/test_critical_hit.py"""
import os, sys, struct, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.core import engine as ENGINE

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')
MONSTER = 3


class Sound(unittest.TestCase):
    def test_sfx_0_is_not_searched_but_407_is(self):
        from dq4_pc import sound as SOUND
        s = object.__new__(SOUND.Sound); seen = []
        s._get = lambda name_str, callback: seen.append(name_str)
        s.play_sfx(0); s.play_sfx(407)
        self.assertEqual(seen, ['SE0407'])


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class RealEngine(unittest.TestCase):
    @staticmethod
    def first_hit(critical):
        """-> dict(modeles, sons, types, degats) vus jusqu'au premier nombre de degats du heros sur le monstre."""
        import unicorn
        eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_crit_'))
        for _ in range(3): eng.step(0, 0)
        eng.load_save(4)
        for i in range(100): eng.step(0, 0x10 if i % 10 == 0 else 0)
        if eng.state.part != ENGINE.PART_FIELD:
            eng.start_field()
            for i in range(120): eng.step(0, 0)
        c = eng.core; L = c.LIB_BASE; eng.impose_scroll_mode(0)                  # messages automatiques
        enc = c.call(eng.E('_ZN7Encount12getSingletonEv'), label='enc')

        def monster(uc, addr, sz, ud):
            for j in range(4):
                c.mem_w(enc + 0x34 + 4 * j, struct.pack('<I', MONSTER if j == 0 else 0)); c.mem_w(enc + 0x44 + 4 * j, struct.pack('<I', 1 if j == 0 else 0))
        a = c.export('_ZN10BattleRoot12setupMonsterEv'); c.uc.hook_add(unicorn.UC_HOOK_CODE, monster, None, a, a)
        if critical:
            def force(uc, addr, sz, ud):
                x20 = uc.reg_read(c.XREG[20]) & 0xffffffffffff
                if struct.unpack('<I', bytes(c.mem(x20 + 8, 4)))[0] == 0: c.mem_w(L + 0x25c6ed, b'\x01')
            c.uc.hook_add(unicorn.UC_HOOK_CODE, force, None, L + 0x1a81dc, L + 0x1a81dc)
        c.uc.ctl_flush_tb()
        c.call(eng.E('_ZN7Encount12forceEncountEv'), enc, label='force')
        for i in range(900):
            eng.step([0x4, 0x8][(i // 20) % 2], 0)
            if eng.state.part == ENGINE.PART_BATTLE: break
        r = dict(modeles=set(), sons=set(), types=set(), degats=None); rel = None; att = 0
        for i in range(1500):
            if rel is not None: eng.send_menu(rel, 1, -1, 0); rel = None
            port = eng.active_menu()
            if port is not None and not eng.msg_visible:
                att += 1
                if att % 4 == 0: eng.send_menu(port, 1, -1, 0x10); rel = port
            pkt = eng.step(0, 0)
            for t, a, f in pkt:
                r['types'].add(t)
                if t == 21 and len(a) >= 2 and a[1] >= 0: r['modeles'].add(a[1])
                if t == 35 and a: r['sons'].add(a[0])
            if eng.ui.damage and r['degats'] is None: r['degats'] = [d[2] for d in eng.ui.damage]
            eng.ui.damage = []
            if r['degats'] is not None: break
        return r

    def test_critical_requests_second_effect_model_and_sfx_no_screen_effect(self):
        normal, critical = self.first_hit(False), self.first_hit(True)
        self.assertIsNotNone(normal['degats']); self.assertIsNotNone(critical['degats'])
        self.assertIn(5303, normal['modeles']); self.assertNotIn(5344, normal['modeles'])
        self.assertIn(5303, critical['modeles']); self.assertIn(5344, critical['modeles'])
        self.assertNotIn(407, normal['sons']); self.assertIn(407, critical['sons'])
        self.assertNotIn(34, critical['types'])                          # pas d'effet d'ecran (cmd_screen_effect) : eclair, secousse...
        self.assertGreater(max(critical['degats']), 1.5 * max(normal['degats']))


if __name__ == '__main__': unittest.main()
