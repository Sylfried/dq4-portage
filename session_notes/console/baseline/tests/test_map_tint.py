"""Test de la teinte du decor (paquet 33, `cmd_map_color_rate`) et de l'echelle des sprites (paquet 13, bit 0x800) : decodage dans `State.apply`, reconnaissance des groupes « tz_ »,
interrupteur de debogage ; partie « moteur reel » facultative (--apk et --saves : la teinte arrive apres le paquet 0 a chaque chargement de carte).

    python3 tools/test_map_tint.py [--apk "<dossier des APK patches>" --saves "<dossier des sauvegardes>"]
Sans ecran, sans GL. Les sauvegardes ne sont ouvertes qu'en lecture (le moteur ecrit dans un dossier temporaire).
"""
import argparse, os, pickle, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.core import engine as ENGINE
from dq4_pc.world import map_tint as TC

ARGS = None


def pkt(*packets): return [(t, list(a), list(f)) for t, a, f in packets]


class StateDecoding(unittest.TestCase):
    def test_default_neutral(self):
        self.assertEqual(ENGINE.State().tint, (1.0, 1.0, 1.0))

    def test_packet_33(self):
        e = ENGINE.State(); e.apply(pkt((33, [], [1.25, 0.65, 0.75])), lambda: 'x')
        self.assertEqual(e.tint, (1.25, 0.65, 0.75))
        e.apply(pkt((33, [], [0.8, 0.8, 1.1])), lambda: 'x')                       # la derniere teinte gagne (fondu de teinte : un paquet par image)
        self.assertEqual(e.tint, (0.8, 0.8, 1.1))

    def test_incomplete_packet_33_ignored(self):
        e = ENGINE.State(); e.apply(pkt((33, [], [1.25, 0.65])), lambda: 'x')
        self.assertEqual(e.tint, (1.0, 1.0, 1.0))

    def test_new_map_resets_to_neutral(self):
        e = ENGINE.State(); e.apply(pkt((33, [], [1.3, 0.7, 0.55])), lambda: 'x')
        e.apply(pkt((0, [0], [])), lambda: 'mlb1a')
        self.assertEqual(e.tint, (1.0, 1.0, 1.0))
        e.apply(pkt((0, [0], []), (33, [], [1.25, 0.65, 0.75])), lambda: 'mlb1a')      # le moteur envoie la teinte APRES le paquet 0, dans la meme image
        self.assertEqual(e.tint, (1.25, 0.65, 0.75))

    def test_world_map_loading_resets_neutral(self):
        e = ENGINE.State(); e.apply(pkt((33, [], [1.3, 0.7, 0.55])), lambda: 'x')
        e.apply(pkt((27, [1], [])), lambda: 'x')
        self.assertEqual(e.tint, (1.0, 1.0, 1.0))

    def test_old_stored_state(self):
        e = ENGINE.State(); d = dict(e.__dict__); del d['tint']
        e2 = ENGINE.State.__new__(ENGINE.State); e2.__setstate__(d)
        self.assertEqual(e2.tint, (1.0, 1.0, 1.0))
        e3 = pickle.loads(pickle.dumps(ENGINE.State()))
        self.assertEqual(e3.tint, (1.0, 1.0, 1.0))


class TzGroups(unittest.TestCase):
    IDS = {101, 202}

    def test_neutral(self):
        self.assertTrue(TC.neutral_tint((1.0, 1.0, 1.0)))
        self.assertTrue(TC.neutral_tint(None))
        self.assertFalse(TC.neutral_tint((1.25, 0.65, 0.75)))
        self.assertFalse(TC.neutral_tint((1.0, 1.0, 0.99)))

    def test_identifier(self):
        self.assertTrue(TC.group_tz(101, self.IDS)); self.assertFalse(TC.group_tz(303, self.IDS))

    def test_transparent(self):
        self.assertTrue(TC.group_tz(('tr', 3, 202), self.IDS)); self.assertFalse(TC.group_tz(('tr', 3, 303), self.IDS))

    def test_animated_palette(self):
        self.assertTrue(TC.group_tz(('pam', 'tz_damg01', 0, 0), self.IDS)); self.assertTrue(TC.group_tz(('tr', 1, ('pam', 'tz_kifkyk1', 2, 0)), self.IDS))
        self.assertFalse(TC.group_tz(('pam', 'wtkira1', 0, 0), self.IDS)); self.assertFalse(TC.group_tz(('pam', 'doku00', 1, 0), self.IDS))

    def test_unknown_entries_all_tinted(self):
        self.assertFalse(TC.group_tz(101, None)); self.assertFalse(TC.group_tz(101, set()))

    def test_cache_file(self):
        import json
        d = tempfile.mkdtemp(prefix='tz_')
        self.assertIsNone(TC.read(d))
        with open(os.path.join(d, TC.FILE), 'w') as fh: json.dump({'ids': [5, 7]}, fh)
        self.assertEqual(TC.read(d), {5, 7})
        with open(os.path.join(d, TC.FILE), 'w') as fh: fh.write('pas du json')
        self.assertIsNone(TC.read(d))

    def test_keys_read_from_cache_without_touching_packet(self):
        import json
        d = tempfile.mkdtemp(prefix='tz_')
        with open(os.path.join(d, TC.FILE), 'w') as fh: json.dump({'ids': [9]}, fh)
        fake = types.SimpleNamespace(cache=d)                              # aucune methode : un acces au paquet de donnees leverait
        self.assertEqual(TC.TzKeys(fake).ids(), {9})


class SpriteScale(unittest.TestCase):
    def _state(self):
        e = ENGINE.State(); e.apply(pkt((12, [0, 106], []), (12, [1, 130], [])), lambda: 'x'); return e

    def test_default_scale(self):
        e = self._state(); self.assertEqual(e.sprites[0]['ech'], 1.0)

    def test_first_update_ignored_then_scale_read(self):
        e = self._state()
        e.apply(pkt((13, [0x6800, 1537], [0.062, 1.08, 0.047, -3.2])), lambda: 'x')      # 1re mise a jour (le personnage est place) : echelle de depart sans suite (0,062, puis 1,0 une image apres), ignoree ; les flottants suivants restent alignes
        s = e.sprites[0]; self.assertEqual(s['ech'], 1.0); self.assertAlmostEqual(s['pos'][0], 1.08, 4); self.assertAlmostEqual(s['pos'][2], -3.2, 4); self.assertEqual((s['pose'], s['dir']), (1, 6))
        e.apply(pkt((13, [0x800], [1.0])), lambda: 'x'); self.assertEqual(e.sprites[0]['ech'], 1.0)
        e.apply(pkt((13, [0x800], [0.7383])), lambda: 'x'); self.assertAlmostEqual(e.sprites[0]['ech'], 0.7383, 4); self.assertAlmostEqual(e.sprites[0]['pos'][0], 1.08, 4)
        self.assertEqual(e.sprites[1]['ech'], 1.0)

    def test_color_with_scale(self):
        e = self._state(); e.sprites[1]['pos'] = (0.0, 0.0, 0.0)                              # deja place
        e.apply(pkt((13, [0x1800 | 1], [0.5, 1.0, 0.5, 0.25, 0.75])), lambda: 'x')
        s = e.sprites[1]; self.assertEqual(s['ech'], 0.5); self.assertEqual(s['col'], (1.0, 0.5, 0.25, 0.75))

    def test_recreated_sprite_reset_to_1(self):
        e = self._state(); e.sprites[0]['pos'] = (0.0, 0.0, 0.0); e.apply(pkt((13, [0x800], [0.5])), lambda: 'x'); self.assertEqual(e.sprites[0]['ech'], 0.5)
        e.apply(pkt((12, [0, 106], [])), lambda: 'x'); self.assertEqual(e.sprites[0]['ech'], 1.0)


class RealEngine(unittest.TestCase):
    def test_tint_after_loading(self):
        apk = (ARGS.apk if ARGS else None) or os.environ.get('DQ_APK'); saves = (ARGS.saves if ARGS else None) or os.environ.get('DQ_SAVES')
        if not apk or not saves: self.skipTest('moteur reel : --apk et --saves (ou DQ_APK et DQ_SAVES)')
        m = ENGINE.Engine(apk, saves, tempfile.mkdtemp(prefix='sv_teinte_')); self.assertTrue(m.load_save(1))
        for _ in range(10): m.step(0, 0)
        for game_map, expected in (('mlb1a', (1.25, 0.65, 0.75)), ('teout1', (1.3, 0.7, 0.55)), ('dab1', (1.0, 1.0, 1.0))):
            m.start_town(game_map)
            for _ in range(60): m.step(0, 0)
            self.assertEqual(m.state.game_map, game_map)
            for a, b in zip(m.state.tint, expected): self.assertAlmostEqual(a, b, 3, game_map)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--apk'); ap.add_argument('--saves'); ARGS, remainder = ap.parse_known_args()
    unittest.main(argv=[sys.argv[0]] + remainder, verbosity=2)
