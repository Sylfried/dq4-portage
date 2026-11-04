"""#76 (audit ENG-10) : `Moteur.demarrer_ville` refuse un nom de carte sans fichier `assets/map/<nom>.stg` au lieu de laisser le moteur d'origine planter (pointeur nul dans FldStage::getCameraLimitL) ;
`za3f3` (carte orpheline : aucun `.stg` dans l'APK) en est le cas connu. Sans moteur : faux moteur et faux APK. Avec l'APK du jeu (DQ_APK) : les 529 cartes de l'APK sont acceptees, `za3f3` refusee.
    python3 tests/test_carte_inconnue.py"""
import os, sys, tempfile, types, unittest, zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import emu_core as T
from dq4_pc.noyau import moteur as MO
APK = os.environ.get('DQ_APK', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/patched_apks')


def faux_moteur(zip_path, appels):
    core = types.SimpleNamespace(fs=T.ApkFs([zip_path]) if zip_path else None, call=lambda *a, **k: appels.append((a, k)), cstr=lambda b: b)
    m = MO.Moteur.__new__(MO.Moteur); m.core = core; m.E = lambda n: n; m._global = lambda: 0; return m


class SansMoteur(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='stg_'); self.z = os.path.join(self.t, 'p.apk')
        with zipfile.ZipFile(self.z, 'w') as z: z.writestr('assets/map/abc.stg', b'x')

    def test_carte_presente(self):
        appels = []; faux_moteur(self.z, appels).demarrer_ville('abc'); self.assertEqual(len(appels), 1); self.assertEqual(appels[0][1], {'label': 'startTown'})

    def test_carte_absente_refusee_sans_appeler_le_moteur(self):
        appels = []
        with self.assertRaises(ValueError) as cm: faux_moteur(self.z, appels).demarrer_ville('za3f3')
        self.assertIn('za3f3', str(cm.exception)); self.assertEqual(appels, [])

    def test_sans_systeme_de_fichiers_comme_avant(self):
        appels = []; faux_moteur(None, appels).demarrer_ville('quelconque'); self.assertEqual(len(appels), 1)


@unittest.skipUnless(os.path.exists(os.path.join(APK, 'split_UnityDataAssetPack.apk')), 'pas d\'APK du jeu')
class AvecLApk(unittest.TestCase):
    def test_cartes_de_l_apk(self):
        fs = T.ApkFs([os.path.join(APK, 'split_UnityDataAssetPack.apk')])
        noms = sorted(n[len('assets/map/'):-4] for n in fs.names if n.startswith('assets/map/') and n.endswith('.stg'))
        self.assertGreaterEqual(len(noms), 500); self.assertIn('ev01', noms); self.assertNotIn('za3f3', noms)
        for n in ('mak1f1', 'za3f1', 'za3f5'): self.assertIsNotNone(fs.open('map/%s.stg' % n), n)
        self.assertIsNone(fs.open('map/za3f3.stg'))


if __name__ == '__main__': unittest.main(verbosity=1)
