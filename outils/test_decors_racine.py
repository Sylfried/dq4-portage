"""Decors dont le maillage est porte par la RACINE de la carte (MeshFilter + MeshRenderer sur le GameObject `<nom>.fld`, aucun enfant `NNN_...`) : l'objet 0 de la carte est la racine elle-meme.
Avant, `Donnees._extraire_carte` ne regardait que les enfants numerotes : ces 32 cartes (18 decors de combat : btl_mt_*, btl_po_*, btl_sd_*, btldc1, btldh1, btldp8_*, btlta2, btltd1_* ;
14 lieux : ddb1b, dnb1b2, dnb2b3, dnb3b4, ev04, za1f6, za1f8, za1f9, za2f4..7, za2f9, za3f1) sortaient VIDES (zero sommet). Verifie (si le paquet de donnees existe : DQ_APK, sinon
/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks) qu'elles ont de la geometrie, et qu'un decor ordinaire (enfants numerotes) est inchange.

    python3 outils/test_decors_racine.py
"""
import os, shutil, sys, tempfile, unittest


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
APK = os.environ.get('DQ_APK', '/mnt/user-data/uploads/DQ Patch/jeux/DQ4/patched_apks')
PACK = os.path.join(APK, 'split_UnityDataAssetPack.apk')

RACINE = ['btl_mt_d', 'btl_po_n', 'btl_sd_e', 'btldc1', 'btldh1', 'btldp8_d', 'btlta2', 'btltd1_d', 'ddb1b', 'dnb1b2', 'dnb2b3', 'dnb3b4', 'ev04', 'za1f6', 'za1f8', 'za1f9', 'za2f4', 'za2f5', 'za2f6', 'za2f7', 'za2f9', 'za3f1']
ORDINAIRE = ['btl_pl_d', 'btlcb1_d']


@unittest.skipUnless(os.path.exists(PACK), 'pas de paquet de donnees du jeu')
class TestDecorsRacine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import donnees as DO
        cls.cache = tempfile.mkdtemp(prefix='cache_test_racine_')
        cls.d = DO.Donnees(PACK, cls.cache, log=lambda *a: None)

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.cache, ignore_errors=True)

    def sommets(self, nom):
        c = self.d.carte(nom, True)
        return sum(len(g[0]) for g in c['groupes'].values()), c

    def test_racine_porteuse(self):
        for nom in RACINE:
            n, c = self.sommets(nom)
            self.assertGreater(n, 0, nom)
            self.assertIn(0, c['plages'], nom)               # l'objet 0 de la carte a de la geometrie

    def test_decor_ordinaire_inchange(self):
        for nom in ORDINAIRE:
            n, c = self.sommets(nom)
            self.assertGreater(n, 1000, nom)
            self.assertEqual(sorted(c['plages']), [0, 1], nom)     # deux objets numerotes (000_..., 001_...), comme avant


if __name__ == '__main__':
    unittest.main(verbosity=1)
