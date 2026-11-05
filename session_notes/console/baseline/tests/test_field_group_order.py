"""Carte du monde : ordre de superposition des membres du groupe a l'atterrissage (issue #135 : « une fois atterri, Doc s'est retrouve devant Ragnar »).

    python3 tools/test_field_group_order.py                                                    (partie sans moteur : Linux sans ecran, pyglet en mode « headless »)
    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 tools/test_field_group_order.py      (ajoute le scenario du moteur reel)

Origine : FieldPartyDraw::draw (libdq4core 0x1ec5a8) trie les membres du groupe par profondeur decroissante (tri par selection, a profondeur egale l'emplacement le plus bas garde la tete) puis leur
donne SpriteCharacter::setDepth 10, 9, 8... : a profondeur egale, le heros est DEVANT ses equipiers. Un atterrissage (Zoom, aile de chimere) empile le groupe sur un seul point (mesure sur le vrai moteur : heros
et Doc a (2495,967 ; 391,967 ; z 200) apres la descente), c'est donc la regle d'egalite qui decide. Avant : `sorted((z, y, slot))` mettait le plus grand emplacement devant (Doc).

  1. sans moteur (`field_depth_rank`) : position egale -> heros devant ; hauteur z, puis « plus au sud », priment toujours ; vehicules (>= 10) : le plus recent devant, sans changer le groupe ;
  2. moteur reel (sauvegarde 1, groupe Ragnar + Doc) : sort Teleportation (action 203) lance depuis le village de maout vers le 2e lieu (carte du monde), descente jusqu'a l'arret : le groupe est empile
     (memes x, y, z) et le heros est devant Doc ; pendant la descente, Doc (au nord, z plus petit) reste derriere le heros."""
import os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.window import game as F

APK, SAVES = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES')


def sp(x, y, z=None): return {'pos': (x, y) if z is None else (x, y, z)}


class OrderWithoutEngine(unittest.TestCase):
    def test_equal_position_hero_is_in_front(self):
        r = F.field_depth_rank({0: sp(2495.967, 391.967, 200.0), 1: sp(2495.967, 391.967, 200.0)})
        self.assertGreater(r[0], r[1])

    def test_group_of_four_stacked_in_group_order(self):
        r = F.field_depth_rank({n: sp(10.0, 20.0, 200.0) for n in range(4)})
        self.assertEqual(sorted(r, key=lambda n: -r[n]), [0, 1, 2, 3])          # devant -> derriere

    def test_height_prevails(self):
        r = F.field_depth_rank({0: sp(10.0, 20.0, 180.0), 1: sp(10.0, 20.0, 200.0)})
        self.assertGreater(r[1], r[0])

    def test_southernmost_prevails_over_slot(self):
        r = F.field_depth_rank({0: sp(10.0, 20.0, 200.0), 1: sp(10.0, 26.0, 200.0)})
        self.assertGreater(r[1], r[0])
        r = F.field_depth_rank({0: sp(10.0, 26.0, 200.0), 1: sp(10.0, 20.0, 200.0)})
        self.assertGreater(r[0], r[1])

    def test_vehicles_most_recent_in_front_and_group_unchanged(self):
        r = F.field_depth_rank({0: sp(1.0, 2.0, 200.0), 1: sp(1.0, 2.0, 200.0), 10: sp(1.0, 2.0, 200.0), 11: sp(1.0, 2.0, 200.0)})
        self.assertGreater(r[11], r[10]); self.assertGreater(r[0], r[1])

    def test_sprite_without_position_ignored_and_z_absent(self):
        r = F.field_depth_rank({0: sp(1.0, 2.0), 1: {'pos': None}, 2: sp(1.0, 2.0)})
        self.assertEqual(set(r), {0, 2}); self.assertGreater(r[0], r[2])


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class RealEngineLanding(unittest.TestCase):
    BTN_TALK, BTN_MENU = 0x100, 0x800

    def advance(self, eng, n, held=0, decl=None):
        for i in range(n): eng.step(held, (held if decl is None else (decl if i == 0 else 0)))

    def test_landing_on_world_map(self):
        from dq4_pc.core import engine as ENGINE
        eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_135_')); eng.load_save(1); self.advance(eng, 120)
        for _ in range(30):
            self.advance(eng, 1, 0, self.BTN_TALK); self.advance(eng, 20)
            if not eng.msg_visible and not (eng.flags() & 4): break
        self.advance(eng, 30); c = eng.core
        ha = c.export('_ZN6status9PartyData15originalPlayer_E') + 0x530 * 12 + 0xd0                     # Doc (emplacement 12 de PlayerStatus)
        c.call(c.export('_ZN6status10HaveAction5clearEv'), ha); c.call(c.export('_ZN6status10HaveAction3addEii'), ha, 203, 0)       # 203 = Teleportation
        eng.sensor.drain(); initial = eng._map_name()
        for _ in range(300):                                                  # sortir de l'eglise (haut) : village de maout, en plein air
            self.advance(eng, 1, 2)
            if eng._map_name() != initial: break
        self.assertEqual(eng._map_name(), 'maout'); self.advance(eng, 70)
        self.advance(eng, 1, 0, self.BTN_MENU); self.advance(eng, 20)
        eng.send_menu(4, 1, 1, 0x10); self.advance(eng, 20)                   # menu racine : Magie
        eng.send_menu(5, 1, 3, 0x10); self.advance(eng, 25)                   # Doc
        eng.send_menu(8, 1, 0, 0x10); self.advance(eng, 20)                   # le sort
        eng.send_menu(8, 1, 1, 0x10)                                        # 2e lieu : sur la carte du monde
        equal_count, descent_count = 0, 0
        for _ in range(900):
            self.advance(eng, 1)
            if eng.msg_visible and eng.frames % 20 == 0: self.advance(eng, 1, 0, self.BTN_TALK)
            if eng.state.part != ENGINE.PART_FIELD: continue
            s0, s1 = eng.state.sprites.get(0), eng.state.sprites.get(1)
            if not s0 or not s1 or s0['pos'] is None or s1['pos'] is None: continue
            r = F.field_depth_rank(eng.state.sprites)
            if s0['pos'] == s1['pos']: equal_count += 1; self.assertGreater(r[0], r[1], 'empiles : le heros doit etre devant (%s)' % (s0['pos'],))
            elif s1['pos'][2] < s0['pos'][2]: descent_count += 1; self.assertGreater(r[0], r[1], 'Doc (z plus petit) doit rester derriere le heros')
        print('\n  images de descente (Doc au nord, z plus petit) : %d ; images empilees : %d ; positions finales : %s / %s' % (descent_count, equal_count, eng.state.sprites[0]['pos'], eng.state.sprites[1]['pos']), flush=True)
        self.assertGreater(descent_count, 5); self.assertGreater(equal_count, 5)          # la descente a bien ete vue, et l'arret empile aussi


if __name__ == '__main__':
    unittest.main(verbosity=2)
