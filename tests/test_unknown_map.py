"""#76 (audit ENG-10) : `Engine.start_town` refuse un nom de carte sans fichier `assets/map/<name_str>.stg` au lieu de laisser le moteur d'origine planter (pointeur nul dans FldStage::getCameraLimitL) ;
`za3f3` (carte orpheline : aucun `.stg` dans l'APK) en est le cas connu. Sans moteur : faux moteur et faux APK. Avec l'APK du jeu (DQ_APK) : les 529 cartes de l'APK sont acceptees, `za3f3` refusee.
    python3 tests/test_unknown_map.py"""
import os, sys, tempfile, types, unittest, zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.core import emu_core as T
from dq4_pc.core import engine as ENGINE
APK = os.environ.get('DQ_APK', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks')


def fake_engine(zip_path, calls):
    core = types.SimpleNamespace(fs=T.ApkFs([zip_path]) if zip_path else None, call=lambda *a, **k: calls.append((a, k)), cstr=lambda b: b)
    m = ENGINE.Engine.__new__(ENGINE.Engine); m.core = core; m.E = lambda n: n; m._global = lambda: 0; return m


class WithoutEngine(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='stg_'); self.z = os.path.join(self.t, 'p.apk')
        with zipfile.ZipFile(self.z, 'w') as z: z.writestr('assets/map/abc.stg', b'x')

    def test_map_present(self):
        calls = []; fake_engine(self.z, calls).start_town('abc'); self.assertEqual(len(calls), 1); self.assertEqual(calls[0][1], {'label': 'startTown'})

    def test_absent_map_refused_without_calling_engine(self):
        calls = []
        with self.assertRaises(ValueError) as cm: fake_engine(self.z, calls).start_town('za3f3')
        self.assertIn('za3f3', str(cm.exception)); self.assertEqual(calls, [])

    def test_without_filesystem_as_before(self):
        calls = []; fake_engine(None, calls).start_town('quelconque'); self.assertEqual(len(calls), 1)


@unittest.skipUnless(os.path.exists(os.path.join(APK, 'split_UnityDataAssetPack.apk')), 'pas d\'APK du jeu')
class WithApk(unittest.TestCase):
    def test_apk_maps(self):
        fs = T.ApkFs([os.path.join(APK, 'split_UnityDataAssetPack.apk')])
        names = sorted(n[len('assets/map/'):-4] for n in fs.names if n.startswith('assets/map/') and n.endswith('.stg'))
        self.assertGreaterEqual(len(names), 500); self.assertIn('ev01', names); self.assertNotIn('za3f3', names)
        for n in ('mak1f1', 'za3f1', 'za3f5'): self.assertIsNotNone(fs.open('map/%s.stg' % n), n)
        self.assertIsNone(fs.open('map/za3f3.stg'))


if __name__ == '__main__': unittest.main(verbosity=1)
