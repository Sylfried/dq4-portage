"""#214 (audit ENG-07) : l'import de sauvegardes controle la somme de chaque journal (un fichier abime ou qui n'est pas un journal du jeu est refuse avec sa raison au lieu de donner « banque vide » au chargement) et ecrit chaque
fichier en entier ou pas du tout (fichier temporaire puis remplacement : un echec laisse l'ancien fichier intact). Sans fenetre ni moteur ; les vraies sauvegardes (DQ_SAVES) sont aussi controlees si elles sont la.
    python3 tests/test_import_sauvegardes.py"""
import os, shutil, struct, sys, tempfile, unittest, zipfile
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc import langue as LG
LG.regler('fr')          # (D-238 : les attentes de ce test sont en francais, quelle que soit la langue de l'ordinateur)
from dq4_pc import chemins as CH
from dq4_pc.persistance import ecriture as EC
from dq4_pc.persistance import format_journal as FJ
from dq4_pc.persistance import sauvegardes as S
SAVES = os.environ.get('DQ_SAVES', '/mnt/user-data/uploads/dq4-portage/jeux/DQ4/saves/20261007_190735')


def journal(n=0, mot0=FJ.MAGIE1):
    """Journal du jeu en clair puis chiffre ; `n` le distingue des autres ; mot0 = FJ.NEUVE / FJ.SUPPRIMEE pour une banque vide."""
    c = bytearray(FJ.TAILLE_JOURNAL); struct.pack_into('<II', c, 0, mot0, FJ.MAGIE2); c[0x30] = n
    struct.pack_into('<I', c, 8, FJ.somme(bytes(c))); return FJ.dechiffrer(bytes(c))


def ecrire(chemin, contenu):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, 'wb') as f: f.write(contenu)


def lire(chemin):
    with open(chemin, 'rb') as f: return f.read()


class Verifier(unittest.TestCase):
    def test_valide(self): self.assertIsNone(FJ.verifier('data1.dat', journal(1)))

    def test_banques_vides(self):                                       # banque neuve (DWEN) ou supprimee (DLED) : valides, sans somme
        for m in (FJ.NEUVE, FJ.SUPPRIMEE):
            c = bytearray(FJ.TAILLE_JOURNAL); struct.pack_into('<I', c, 0, m); self.assertIsNone(FJ.verifier('data3.dat', FJ.dechiffrer(bytes(c))), hex(m))

    def test_un_octet_change(self):
        j = bytearray(journal(1)); j[0x500] ^= 1; self.assertIn('somme', FJ.verifier('data1.dat', bytes(j)))

    def test_somme_changee(self):
        c = bytearray(FJ.dechiffrer(journal(1))); c[8] ^= 0xff; self.assertIn('somme', FJ.verifier('data2.dat', FJ.dechiffrer(bytes(c))))

    def test_bruit_et_fichier_vide(self):
        self.assertIn('pas un journal', FJ.verifier('data1.dat', bytes(range(256)) * 60)); self.assertIn('pas un journal', FJ.verifier('data1.dat', bytes(FJ.TAILLE_JOURNAL)))

    def test_data9_et_tailles_hors_champ(self):                         # data9 (512 octets) : pas de somme ; la taille est controlee ailleurs
        self.assertIsNone(FJ.verifier('data9.dat', bytes(512))); self.assertIsNone(FJ.verifier('data1.dat', b'xx'))


@unittest.skipUnless(os.path.isdir(SAVES), 'pas de sauvegardes d\'origine')
class VraiesSauvegardes(unittest.TestCase):
    def test_toutes_acceptees(self):
        n = 0
        for nom in S.NOMS:
            p = os.path.join(SAVES, nom)
            if os.path.isfile(p): self.assertIsNone(FJ.verifier(nom, lire(p)), nom); n += 1
        self.assertGreater(n, 0)


class Import(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='sv_imp_'); self.d = CH.Dossiers(self.t, env={}); self.avant = CH.DOSSIERS; CH.DOSSIERS = self.d
        self.ecr = self.d.portage; self.zip = os.path.join(self.t, 'i.zip')

    def tearDown(self): CH.DOSSIERS = self.avant; shutil.rmtree(self.t, ignore_errors=True)

    def zipper(self, **fichiers):
        with zipfile.ZipFile(self.zip, 'w') as z:
            for nom, d in fichiers.items(): z.writestr(nom.replace('__', '/'), d)

    def test_un_journal_abime_est_refuse_les_autres_passent(self):
        ecrire(os.path.join(self.ecr, 'data1.dat'), journal(1)); mauvais = bytearray(journal(3)); mauvais[100] ^= 1
        self.zipper(**{'data1.dat': journal(2), 'data2.dat': bytes(mauvais), 'data9.dat': bytes(512)})
        nj, ne, copie, pb = S.importer([self.zip], self.ecr, self.d.mobile)
        self.assertEqual((nj, ne), (2, 0)); self.assertEqual(len(pb), 1); self.assertTrue(pb[0].startswith('data2.dat : fichier abime')); self.assertIn('somme', pb[0])
        self.assertEqual(lire(os.path.join(self.ecr, 'data1.dat')), journal(2)); self.assertFalse(os.path.exists(os.path.join(self.ecr, 'data2.dat')))      # le fichier abime n'est pas ecrit
        self.assertEqual(lire(os.path.join(copie, 'data1.dat')), journal(1))

    def test_tout_refuse(self):
        self.zipper(**{'data1.dat': bytes(FJ.TAILLE_JOURNAL)})
        with self.assertRaises(ValueError) as cm: S.importer([self.zip], self.ecr, self.d.mobile)
        self.assertIn('pas un journal', str(cm.exception)); self.assertFalse(os.path.exists(os.path.join(self.ecr, 'data1.dat')))

    def test_echec_d_ecriture_laisse_l_ancien_fichier(self):
        ecrire(os.path.join(self.ecr, 'data1.dat'), journal(1)); ecrire(os.path.join(self.ecr, 'data2.dat'), journal(1))
        self.zipper(**{'data1.dat': journal(2), 'data2.dat': journal(2)})
        vrai = os.replace
        def remplace(src, dst, *a, **k):
            if os.path.basename(dst) == 'data1.dat': raise PermissionError('verrouille par un antivirus')
            return vrai(src, dst, *a, **k)
        with mock.patch('time.sleep'), mock.patch('os.replace', remplace): nj, ne, copie, pb = S.importer([self.zip], self.ecr, self.d.mobile)
        self.assertEqual(nj, 1); self.assertTrue(any(p.startswith('data1.dat : ecriture impossible') for p in pb))
        self.assertEqual(lire(os.path.join(self.ecr, 'data1.dat')), journal(1))                    # inchange
        self.assertEqual(lire(os.path.join(self.ecr, 'data2.dat')), journal(2))                    # l'autre est passe
        self.assertEqual(sorted(f for f in os.listdir(self.ecr) if f.endswith('.tmp')), [])        # aucun fichier temporaire oublie

    def test_aucun_fichier_ecrit(self):
        self.zipper(**{'data1.dat': journal(2)})
        with mock.patch('time.sleep'), mock.patch('os.replace', side_effect=PermissionError('non')):
            with self.assertRaises(ValueError) as cm: S.importer([self.zip], self.ecr, self.d.mobile)
        self.assertIn('data1.dat', str(cm.exception))


class EcritureAtomique(unittest.TestCase):
    def test_ecrit_et_remplace(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, 'sous', 'f.dat'); self.assertIsNone(EC.ecrire_atomique(p, b'abc')); self.assertEqual(lire(p), b'abc')
            self.assertIsNone(EC.ecrire_atomique(p, b'de')); self.assertEqual(lire(p), b'de'); self.assertEqual(os.listdir(os.path.dirname(p)), ['f.dat'])

    def test_le_moteur_utilise_la_meme_fonction(self):
        try: from dq4_pc.noyau import moteur as MO
        except ImportError: self.skipTest('unicorn absent')
        self.assertIs(MO.CoreJeu.ecrire_atomique, EC.ecrire_atomique)


if __name__ == '__main__': unittest.main(verbosity=1)
