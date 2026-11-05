"""Decor de combat selon l'heure du monde (retour de Sylfried, 14 h 08 : « le crepuscule ou le leve de soleil dans le decor du combat »).

Moteur reel (Unicorn) : `StageStatus + 0xcc` = heure du monde (0 a 3391, elle avance en marchant), `+ 0xc8` = zone horaire que `WorldLocation::setCurrentTimeZone` en tire :
    0 a 127 : zone 1 ; 128 a 1983 : zone 2 (jour) ; 1984 a 2239 : zone 3 (soir) ; 2240 a 3263 : zone 4 (nuit) ; 3264 a 3391 : zone 1.
`StageStatus::getBtlMapName` (0x1a4580) remplace la derniere lettre du decor par l'octet `zone` de l'octet-table « d n d e n » : zones 1 et 4 -> `_n`, zone 2 -> `_d`, zone 3 -> `_e`.
Il n'existe donc PAS de decor d'aube : le debut et la fin de nuit (zone 1) reprennent le decor de nuit. Le soir (`_e`) existe, est demande par le moteur et chaque decor de la carte du monde en a un.
Le moteur n'envoie en combat ni teinte (paquet 33) ni couleur de fond (paquet 8) : la couleur du jour, du soir et de la nuit est dans les assets (couleurs de sommet + textures `_d`, `_e`, `_n`).
Le FOND du combat est la `bg_color` du bloc FETC du decor charge (`cmd_fld_load` -> `BackColor.SetColor`, lu dans libil2cpp) : orange / rouge au soir, bleu sombre la nuit (map_tint.fetc_background, Fonds).

    DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes> python3 tools/test_battle_scenery_time_of_day.py        (DQ_CACHE=<cache des cartes> : verifie aussi les assets)"""
import os, sys, struct, tempfile, unittest, pickle, json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.core import engine as ENGINE
from dq4_pc.world import data as DO
from dq4_pc.world import map_tint as TC

APK, SAVES, CACHE = os.environ.get('DQ_APK'), os.environ.get('DQ_SAVES'), os.environ.get('DQ_CACHE')
STAGE_ADDRESS = 0x23d430          # GOT : StageStatus (g_StageStatus)
CASES = [(64, 1, 'n'), (1000, 2, 'd'), (1984, 3, 'e'), (2239, 3, 'e'), (2240, 4, 'n'), (3300, 1, 'n')]      # (heure du monde, zone attendue, lettre du decor)
WORLD_SCENERIES = ['btl_pl', 'btl_se', 'btl_sd', 'btl_mt', 'btl_po', 'btl_wd']


class Fallback(unittest.TestCase):
    def test_missing_variant_replaced_by_the_nearest(self):
        self.assertEqual(DO.fallback_sceneries('btlcc1_n'), ['btlcc1_e', 'btlcc1_d', 'btlcc1'])         # btlcc1 n'a que _d et _e dans les donnees
        self.assertEqual(DO.fallback_sceneries('btl_pl_e'), ['btl_pl_d', 'btl_pl_n', 'btl_pl'])
        self.assertEqual(DO.fallback_sceneries('btl_pl_d'), ['btl_pl_e', 'btl_pl_n', 'btl_pl'])
        self.assertEqual(DO.fallback_sceneries('btl_se_dk'), ['btl_se_n', 'btl_se_d', 'btl_se_e', 'btl_se'])      # monde sombre : le moteur demande btl_se_dk, absent des donnees (seuls pl, po, wd et tc1 l'ont)
        for name_str in ('btlcb2', 'ev01', '', None): self.assertEqual(DO.fallback_sceneries(name_str), [], name_str)


class BackgroundFETC(unittest.TestCase):
    @staticmethod
    def map_of(r, g, b, a=0):
        """Fichier .map minimal : un bloc FETC (40 octets) dont les 4 premiers octets utiles sont r, g, b, a."""
        return b'FETC' + struct.pack('<I', 0x28) + bytes([r, g, b, a]) + bytes(28)

    def test_color_is_read_from_fetc_block(self):
        self.assertEqual(TC.fetc_background(self.map_of(192, 52, 0)), (192 / 255.0, 52 / 255.0, 0.0))        # btl_mt_e : le rouge orange du coucher de soleil
        self.assertEqual(TC.fetc_background(self.map_of(0, 0, 0)), (0.0, 0.0, 0.0))

    def test_fetc_alpha_is_ignored(self):
        self.assertEqual(TC.fetc_background(self.map_of(10, 20, 30, 0)), TC.fetc_background(self.map_of(10, 20, 30, 255)))        # alpha 0 dans les 140 decors, shader BackColor sans fusion

    def test_no_fetc_block_no_color(self):
        self.assertIsNone(TC.fetc_background(b'FHDR' + struct.pack('<I', 0x98) + bytes(0x90)))
        self.assertIsNone(TC.fetc_background(b''))

    def test_unreadable_or_absent_cache_gives_none(self):
        d = tempfile.mkdtemp(prefix='fonds_')
        self.assertIsNone(TC.read_backgrounds(d))
        with open(os.path.join(d, TC.BACKGROUNDS_FILE), 'w') as fh: fh.write('pas du json')
        self.assertIsNone(TC.read_backgrounds(d))
        with open(os.path.join(d, TC.BACKGROUNDS_FILE), 'w') as fh: json.dump({'fonds': {'btl_pl_e': [0.5, 0.25, 0.0]}}, fh)
        self.assertEqual(TC.read_backgrounds(d), {'btl_pl_e': (0.5, 0.25, 0.0)})

    def test_backgrounds_serve_cache_then_leave_estimate_if_missing(self):
        d = tempfile.mkdtemp(prefix='fonds_')
        with open(os.path.join(d, TC.BACKGROUNDS_FILE), 'w') as fh: json.dump({'fonds': {'btl_pl_e': [0.5, 0.25, 0.0]}}, fh)
        class Fake: cache = d
        f = TC.Backgrounds(Fake())
        self.assertEqual(f.color('btl_pl_e'), (0.5, 0.25, 0.0))
        self.assertIsNone(f.color('btl_inconnu_d'))


@unittest.skipUnless(APK and SAVES, 'moteur reel : DQ_APK=<dossier des APK patches> DQ_SAVES=<dossier des sauvegardes>')
class RealEngine(unittest.TestCase):
    @staticmethod
    def encounter(hour):
        """-> (zone lue, nom du decor, teintes et fonds recus au debut du combat) pour une rencontre sur la carte du monde a cette heure du monde (slot 4)."""
        eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_heure_'))
        for _ in range(3): eng.step(0, 0)
        eng.load_save(4)
        for i in range(100): eng.step(0, 0x10 if i % 10 == 0 else 0)
        if eng.state.part != ENGINE.PART_FIELD:
            eng.start_field()
            for i in range(120): eng.step(0, 0)
        c = eng.core
        g = struct.unpack('<Q', bytes(c.mem(eng.L + STAGE_ADDRESS, 8)))[0]
        c.mem_w(g + 0xcc, struct.pack('<i', hour))
        c.call(eng.E('_ZN3cmn13WorldLocation18setCurrentTimeZoneEv'), c.call(eng.E('_ZN3cmn13WorldLocation12getSingletonEv'), label='wl'), label='zone')
        zone = struct.unpack('<I', bytes(c.mem(g + 0xc8, 4)))[0]
        c.call(eng.E('_ZN7Encount12forceEncountEv'), c.call(eng.E('_ZN7Encount12getSingletonEv'), label='enc'), label='force')
        received_list = []; n0 = None
        for i in range(1500):
            pkt = eng.step([0x4, 0x8][(i // 20) % 2], 0)
            if n0 is not None: received_list += [(t, list(f[:3])) for t, a, f in pkt if t in (8, 33)]
            if eng.state.part == ENGINE.PART_BATTLE and n0 is None: n0 = eng.frames
            if n0 is not None and eng.frames - n0 > 40: break
        return zone, eng.state.game_map, received_list

    def test_engine_picks_day_evening_or_night_by_world_hour(self):
        for hour, zone_att, letter in CASES:
            zone, game_map, received_list = self.encounter(hour)
            self.assertEqual(zone, zone_att, 'heure %d' % hour)
            self.assertEqual(game_map, 'btl_pl_' + letter, 'heure %d : zone %d' % (hour, zone))
            self.assertEqual(received_list, [], 'heure %d : le moteur ne teinte pas le decor de combat et n envoie pas de fond' % hour)


@unittest.skipUnless(APK, 'ressources reelles : DQ_APK=<dossier des APK patches>')
class RealBackgrounds(unittest.TestCase):
    """Les 140 decors de combat du paquet de donnees (lecture du paquet : plusieurs secondes, ~1 Go : a lancer via engine_slot.sh)."""
    @classmethod
    def setUpClass(cls):
        cls.data = DO.Data(os.path.join(APK, 'split_UnityDataAssetPack.apk'), tempfile.mkdtemp(prefix='fonds_reels_'), log=lambda *a: None)
        cls.backgrounds = TC.compute_backgrounds(cls.data)

    def test_140_sceneries_have_background(self):
        self.assertEqual(len(self.backgrounds), 140)
        self.assertEqual(TC.read_backgrounds(self.data.cache), self.backgrounds)                         # et le cache est relu tel quel

    def test_evening_background_is_warmer_and_night_darker(self):
        def warmth(c): return c[0] - c[2]
        for base in ('btl_pl', 'btl_se', 'btl_sd', 'btl_mt', 'btl_wd'):
            j, e, n = (self.backgrounds['%s_%s' % (base, x)] for x in 'den')
            self.assertGreater(warmth(e), warmth(j) + 0.15, base + ' : le fond du soir est plus chaud (orange) que celui du jour')
            self.assertLess(sum(n), sum(j), base + ' : le fond de la nuit est plus sombre que celui du jour')

    def test_known_values(self):
        r = lambda name_str: tuple(round(255 * x) for x in self.backgrounds[name_str])
        self.assertEqual(r('btl_pl_d'), (77, 186, 88)); self.assertEqual(r('btl_mt_e'), (192, 52, 0)); self.assertEqual(r('btl_se_n'), (8, 38, 107)); self.assertEqual(r('btl_sd_e'), (255, 115, 33))


@unittest.skipUnless(CACHE and os.path.isdir(CACHE), 'assets : DQ_CACHE=<cache des cartes>')
class Assets(unittest.TestCase):
    @staticmethod
    def scenery(name_str):
        with open(os.path.join(CACHE, 'carte10_%s.pkl' % name_str), 'rb') as fh: return pickle.load(fh)

    def test_each_world_map_scenery_has_its_three_variants(self):
        for base in WORLD_SCENERIES:
            for letter in 'den': self.assertTrue(os.path.exists(os.path.join(CACHE, 'carte10_%s_%s.pkl' % (base, letter))), '%s_%s' % (base, letter))

    def test_evening_redder_night_darker_and_bluer_than_day(self):
        def average(name_str):
            c = self.scenery(name_str); r = [g[2][:, :3].mean(0) for g in c['groupes'].values()]
            return sum(r) / len(r)                                      # couleur de sommet moyenne : la teinte du moment est cuite dans l'asset
        for base in WORLD_SCENERIES:
            j, s, n = average(base + '_d'), average(base + '_e'), average(base + '_n')
            self.assertGreater(j.mean(), s.mean(), base + ' : le soir est plus sombre que le jour')
            self.assertGreater(s.mean(), n.mean(), base + ' : la nuit est plus sombre que le soir')
            self.assertGreater(s[0] - s[2], j[0] - j[2] + 0.1, base + ' : le soir est plus rouge (rouge - bleu)')
            self.assertGreater(j[0] - j[2], n[0] - n[2] + 0.05, base + ' : la nuit est plus bleue (rouge - bleu)')


if __name__ == '__main__': unittest.main()
