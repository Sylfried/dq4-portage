"""#217 (audit ENG-08) : les reglages / crochets que le moteur d'un AUTRE apk ne laisse pas installer ne sont plus silencieux : `Engine.missing_hooks` (ligne de console + liste sans doublon), puis la fenetre
les note dans `window_errors.log` et affiche un message (Game._report_missing_hooks). Sans moteur : faux moteur (memoire simulee). Avec l'APK du jeu (DQ_APK, DQ_SAVES) : le moteur d'origine n'en manque aucun.
    PYGLET_HEADLESS=1 python3 tests/test_missing_hooks.py"""
import os, shutil, struct, sys, tempfile, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc import language as _LANGUAGE; _LANGUAGE.select_language('fr')          # (D-238 : ces tests attendent les textes francais, quelle que soit la langue de l'ordinateur)
from dq4_pc.core import engine as ENGINE
APK = os.environ.get('DQ_APK', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks')
SAVES = os.environ.get('DQ_SAVES', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735')

BASE = 0x10000                                                     # adresse de la fonction simulee
ORIGINAL = (0x11000120 | (0xc0 << 10), 0x11000120 | (0x1c0 << 10), 0x11000120 | (0x314 << 10))       # add w0, w9, #imm des trois constantes de drawSymbol (masque 0xffc003e0 = 0x11000120)


def fake_engine(words=ORIGINAL, cmp_param=0x71001d1f):
    """Moteur sans emulateur : la memoire est un dictionnaire d'octets ; export() renvoie BASE ; LIB_BASE = 0 (cmp du bouton Parametres a CMP_PARAMS)."""
    mem = bytearray(0x200000)
    for dec, w in zip((0x44, 0x48, 0x4c), words): mem[BASE + dec:BASE + dec + 4] = struct.pack('<I', w)
    mem[ENGINE.Engine.CMP_PARAMS:ENGINE.Engine.CMP_PARAMS + 4] = struct.pack('<I', cmp_param)
    def write(a, d): mem[a:a + len(d)] = d
    core = types.SimpleNamespace(LIB_BASE=0, export=lambda n: BASE, mem=lambda a, n: bytes(mem[a:a + n]), mem_w=write)
    m = ENGINE.Engine.__new__(ENGINE.Engine); m.core = core; m.missing_hooks = []; m.mem = mem
    return m


def word(m, a): return struct.unpack('<I', bytes(m.mem[a:a + 4]))[0]


class WithoutEngine(unittest.TestCase):
    def test_missing_without_duplicate(self):
        m = fake_engine(); m._record_missing('a'); m._record_missing('b'); m._record_missing('a')
        self.assertEqual(m.missing_hooks, ['a', 'b'])

    def test_normal_locations_window(self):
        m = fake_engine(); m._widen_symbols()
        self.assertEqual(m.missing_hooks, [])
        for dec in (0x44, 0x48, 0x4c): self.assertEqual((word(m, BASE + dec) >> 10) & 0xfff, 1600)
        m._widen_symbols(); self.assertEqual(m.missing_hooks, [])               # deja elargie (apres le chargement d'un etat) : ni erreur ni message

    def test_locations_window_other_version(self):
        other = (ORIGINAL[0], ORIGINAL[1], 0x11000120 | (0x555 << 10))
        m = fake_engine(other); m._widen_symbols()
        self.assertEqual(len(m.missing_hooks), 1); self.assertIn('fenetre des lieux', m.missing_hooks[0])
        self.assertEqual(word(m, BASE + 0x44), ORIGINAL[0])                             # rien n'a ete touche
        m._widen_symbols(); self.assertEqual(len(m.missing_hooks), 1)           # pas de doublon

    def test_params_button(self):
        m = fake_engine(); m.patch_params()
        self.assertEqual(m.missing_hooks, []); self.assertEqual(word(m, ENGINE.Engine.CMP_PARAMS), 0x713ffd1f)
        m.patch_params(); self.assertEqual(m.missing_hooks, [])               # deja patche
        m = fake_engine(cmp_param=0xd503201f); m.patch_params()                  # autre version : nop au lieu de la comparaison
        self.assertEqual(len(m.missing_hooks), 1); self.assertIn('Paramètres', m.missing_hooks[0])
        self.assertEqual(word(m, ENGINE.Engine.CMP_PARAMS), 0xd503201f)

    def test_installers_report_their_failure(self):
        """Un moteur dont les fonctions sont introuvables : chaque installateur le dit au lieu de se taire."""
        def not_found(n): raise KeyError(n)
        for name_str in ('_text_hooks', '_fade_hooks', '_level_hooks', '_encounter_hooks', '_day_clock_hooks', '_game_time_hooks', '_magic_hooks', '_divert_params', '_widen_symbols'):
            m = fake_engine(); m.core.export = not_found
            getattr(m, name_str)()
            self.assertTrue(m.missing_hooks, name_str + ' : echec silencieux')


class Window(unittest.TestCase):
    def setUp(self):
        try: from dq4_pc.window import game as F
        except Exception as ex: raise unittest.SkipTest('fenetre non importable ici (%r)' % (ex,))
        self.F = F; d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        self.logfile = os.environ['DQ_JOURNAL_FENETRE'] = os.path.join(d, 'logs', 'window_errors.log')
        self.addCleanup(os.environ.pop, 'DQ_JOURNAL_FENETRE', None)

    def read(self):
        with open(self.logfile, encoding='utf-8') as f: return f.read()

    def test_report_once_then_only_new_ones(self):
        j = types.SimpleNamespace(_reported_hooks=0)                                  # (sans `toast` : depuis #267 aucun message a l'ecran, seulement le journal)
        eng = types.SimpleNamespace(missing_hooks=['vitesse du texte non installee', 'rencontres : CountDown::exec inattendu'])
        self.F.Game._report_missing_hooks(j, eng)
        self.assertEqual(j._reported_hooks, 2)
        txt = self.read()
        self.assertIn('vitesse du texte', txt); self.assertIn('CountDown', txt); self.assertEqual(txt.count('\n'), 2)
        eng.missing_hooks.append('sorts sans effet : menu Magie inattendu')            # trouve apres le chargement d'un etat
        self.F.Game._report_missing_hooks(j, eng)
        self.assertEqual(j._reported_hooks, 3)
        txt = self.read(); self.assertEqual(txt.count('\n'), 3); self.assertIn('menu Magie', txt)


@unittest.skipUnless(os.path.exists(os.path.join(APK, 'split_UnityDataAssetPack.apk')) and os.path.isdir(SAVES), "pas d'APK du jeu")
class RealEngine(unittest.TestCase):
    def test_original_engine_misses_none(self):
        eng = ENGINE.Engine(APK, SAVES, tempfile.mkdtemp(prefix='sv_crochets_'))
        self.assertEqual(eng.missing_hooks, [])
        self.assertTrue(eng.sensor.active); self.assertTrue(eng.battle_sensor.active)
        eng.reapply_fixes(); self.assertEqual(eng.missing_hooks, [])           # chargement d'un etat : toujours rien


if __name__ == '__main__': unittest.main(verbosity=1)
