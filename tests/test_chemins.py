"""Dossiers du portage (chemins.py) et reprise de l'ancienne disposition : disposition par defaut, variables d'environnement, migration sans ecrasement ni suppression,
import / export de sauvegardes avec les nouveaux dossiers, anciens etats instantanes (noms de modules d'avant le rangement du 04/11/2026). Sans fenetre ni moteur.

    python3 tests/test_chemins.py"""
import io, os, pickle, shutil, sys, tempfile, unittest, zipfile

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..'))
from dq4_pc import chemins as CH
from dq4_pc.persistance import etats as ET
from dq4_pc.persistance import sauvegardes as S


def ecrire(chemin, contenu=b'x'):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, 'wb') as f: f.write(contenu)
    return chemin


class Disposition(unittest.TestCase):
    def test_par_defaut(self):
        d = CH.Dossiers('/projet', env={})
        self.assertEqual(d.donnees, os.path.normpath('/projet/donnees'))
        for nom, attendu in (('apk', 'donnees/apk'), ('mobile', 'donnees/sauvegardes/mobile'), ('portage', 'donnees/sauvegardes/portage'), ('etats', 'donnees/sauvegardes/etats'),
                             ('cache', 'donnees/cache'), ('reglages', 'donnees/reglages/reglages.json'), ('favoris', 'donnees/reglages/historique_favoris.json'),
                             ('journal_fenetre', 'donnees/journaux/erreurs_fenetre.log')):
            self.assertEqual(getattr(d, nom), os.path.normpath('/projet/' + attendu), nom)

    def test_variables_d_environnement(self):
        d = CH.Dossiers('/projet', env={'DQ4_DONNEES': '/ailleurs/mes_donnees'})
        self.assertEqual(d.apk, os.path.normpath('/ailleurs/mes_donnees/apk')); self.assertEqual(d.cache, os.path.normpath('/ailleurs/mes_donnees/cache'))
        d = CH.Dossiers('/projet', env={'DQ4_JEUX': '/jeux/DQ4'})                      # ancien fonctionnement : APK et sauvegardes du telephone la-bas, le reste dans donnees
        self.assertEqual(d.apk, os.path.normpath('/jeux/DQ4/patched_apks')); self.assertEqual(d.mobile, os.path.normpath('/jeux/DQ4/saves'))
        self.assertEqual(d.portage, os.path.normpath('/projet/donnees/sauvegardes/portage'))

    def test_etats_et_copies_selon_le_dossier_d_ecriture(self):
        d = CH.Dossiers('/projet', env={})
        self.assertEqual(d.dossier_etats(d.portage), d.etats); self.assertEqual(d.dossier_copies(d.portage), d.sauvegardes)
        self.assertEqual(d.dossier_etats('/tmp/sv_test'), os.path.join('/tmp/sv_test', 'etats')); self.assertEqual(d.dossier_copies('/tmp/sv_test'), '/tmp/sv_test')

    def test_sauvegarde_mobile_la_plus_recente(self):
        with tempfile.TemporaryDirectory() as t:
            d = CH.Dossiers(t, env={}); self.assertIsNone(d.sauvegarde_mobile_recente())
            for n in ('20261003_100000', '20261103_222423', '20261007_190735'): ecrire(os.path.join(d.mobile, n, 'data1.dat'))
            ecrire(os.path.join(d.mobile, 'zz_un_fichier.txt'))
            self.assertEqual(os.path.basename(d.sauvegarde_mobile_recente()), '20261103_222423')


class Migration(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='migr_'); self.d = CH.Dossiers(self.t, env={})
        r = self.t
        ecrire(os.path.join(r, 'jeux', 'DQ4', 'patched_apks', 'base.apk'), b'APK1'); ecrire(os.path.join(r, 'jeux', 'DQ4', 'patched_apks', 'split_config.arm64_v8a.apk'), b'APK2')
        ecrire(os.path.join(r, 'jeux', 'DQ4', 'saves', '20261103_222423', 'data1.dat'), b'T1'); ecrire(os.path.join(r, 'jeux', 'DQ4', 'saves', '20261007_190735', 'data1.dat'), b'T0')
        ecrire(os.path.join(r, 'dq4_pc', 'cache', 'carte10_a.pkl'), b'CACHE'); ecrire(os.path.join(r, 'dq4_pc', 'cache', 'il2cpp', 'dump.cs'), b'DUMP')
        ecrire(os.path.join(r, 'dq4_pc', 'sauvegardes', 'data1.dat'), b'P1'); ecrire(os.path.join(r, 'dq4_pc', 'sauvegardes', 'etats', 'etat_01.dqs'), b'E1')
        ecrire(os.path.join(r, 'dq4_pc', 'sauvegardes', 'avant_import_20261101_101010', 'data2.dat'), b'AV')
        ecrire(os.path.join(r, 'dq4_pc', 'reglages.json'), b'{"a": 1}'); ecrire(os.path.join(r, 'dq4_pc', 'historique_favoris.json'), b'[]'); ecrire(os.path.join(r, 'dq4_pc', 'erreurs_fenetre.log'), b'LOG')

    def tearDown(self): shutil.rmtree(self.t, ignore_errors=True)

    def lire(self, *p):
        with open(os.path.join(self.t, *p), 'rb') as f: return f.read()

    def test_reprise_complete(self):
        fait = CH.migrer(self.d, log=lambda *a: None)
        self.assertGreaterEqual(len(fait), 6)
        self.assertEqual(self.lire('donnees', 'apk', 'base.apk'), b'APK1'); self.assertEqual(self.lire('donnees', 'sauvegardes', 'mobile', '20261103_222423', 'data1.dat'), b'T1')
        self.assertEqual(self.lire('donnees', 'sauvegardes', 'mobile', '20261007_190735', 'data1.dat'), b'T0')
        self.assertEqual(self.lire('donnees', 'cache', 'carte10_a.pkl'), b'CACHE'); self.assertEqual(self.lire('donnees', 'cache', 'il2cpp', 'dump.cs'), b'DUMP')
        self.assertEqual(self.lire('donnees', 'sauvegardes', 'portage', 'data1.dat'), b'P1'); self.assertEqual(self.lire('donnees', 'sauvegardes', 'etats', 'etat_01.dqs'), b'E1')
        self.assertEqual(self.lire('donnees', 'sauvegardes', 'avant_import_20261101_101010', 'data2.dat'), b'AV')
        self.assertEqual(self.lire('donnees', 'reglages', 'reglages.json'), b'{"a": 1}'); self.assertEqual(self.lire('donnees', 'reglages', 'historique_favoris.json'), b'[]')
        self.assertEqual(self.lire('donnees', 'journaux', 'erreurs_fenetre.log'), b'LOG')

    def test_les_originaux_restent_sauf_le_cache(self):
        CH.migrer(self.d, log=lambda *a: None)
        for p in (('jeux', 'DQ4', 'patched_apks', 'base.apk'), ('jeux', 'DQ4', 'saves', '20261103_222423', 'data1.dat'), ('dq4_pc', 'sauvegardes', 'data1.dat'),
                  ('dq4_pc', 'sauvegardes', 'etats', 'etat_01.dqs'), ('dq4_pc', 'reglages.json'), ('dq4_pc', 'historique_favoris.json')):
            self.assertTrue(os.path.isfile(os.path.join(self.t, *p)), p)
        self.assertFalse(os.path.exists(os.path.join(self.t, 'dq4_pc', 'cache')), 'le cache est deplace (meme volume : un renommage)')

    def test_rien_n_est_ecrase_et_la_reprise_ne_se_repete_pas(self):
        ecrire(os.path.join(self.t, 'donnees', 'reglages', 'reglages.json'), b'{"nouveau": 2}')                 # reglages deja changes dans la nouvelle version : gardes
        ecrire(os.path.join(self.t, 'donnees', 'sauvegardes', 'portage', 'data1.dat'), b'NEUF')
        CH.migrer(self.d, log=lambda *a: None)
        self.assertEqual(self.lire('donnees', 'reglages', 'reglages.json'), b'{"nouveau": 2}'); self.assertEqual(self.lire('donnees', 'sauvegardes', 'portage', 'data1.dat'), b'NEUF')
        self.assertEqual(CH.migrer(self.d, log=lambda *a: None), [])

    def test_cache_deja_present_n_est_pas_touche(self):
        ecrire(os.path.join(self.t, 'donnees', 'cache', 'autre.pkl'), b'N')
        CH.migrer(self.d, log=lambda *a: None)
        self.assertTrue(os.path.isfile(os.path.join(self.t, 'dq4_pc', 'cache', 'carte10_a.pkl'))); self.assertFalse(os.path.exists(os.path.join(self.t, 'donnees', 'cache', 'carte10_a.pkl')))

    def test_rien_a_reprendre(self):
        with tempfile.TemporaryDirectory() as vide: self.assertEqual(CH.migrer(CH.Dossiers(vide, env={}), log=lambda *a: None), [])


def journal(octets=0x3c00): return bytes(octets)


def journal_valide(n=0):
    """Un journal du jeu valide (en-tete « rate », somme de controle, chiffre) ; `n` le distingue des autres."""
    import struct
    from dq4_pc.persistance import format_journal as FJ
    clair = bytearray(FJ.TAILLE_JOURNAL); struct.pack_into('<II', clair, 0, FJ.MAGIE1, FJ.MAGIE2); clair[0x30] = n
    struct.pack_into('<I', clair, 8, FJ.somme(bytes(clair))); return FJ.dechiffrer(bytes(clair))


class Sauvegardes(unittest.TestCase):
    """Import / export avec la disposition de donnees\\sauvegardes (etats et copies a cote de `portage`)."""
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='sv_'); self.d = CH.Dossiers(self.t, env={}); self.avant = CH.DOSSIERS; CH.DOSSIERS = self.d

    def tearDown(self): CH.DOSSIERS = self.avant; shutil.rmtree(self.t, ignore_errors=True)

    def test_import_dans_la_disposition_habituelle(self):
        ecrire(os.path.join(self.d.portage, 'data1.dat'), journal_valide(1)); ecrire(os.path.join(self.d.etats, 'etat_01.dqs'), b'e' * 2000)
        zip_ = os.path.join(self.t, 'import.zip')
        with zipfile.ZipFile(zip_, 'w') as z: z.writestr('data1.dat', journal_valide(2)); z.writestr('etats/etat_01.dqs', b'f' * 2000)
        nj, ne, copie, pb = S.importer([zip_], self.d.portage, self.d.mobile)
        self.assertEqual((nj, ne, pb), (1, 1, []))
        with open(os.path.join(self.d.portage, 'data1.dat'), 'rb') as f: self.assertEqual(f.read(), journal_valide(2))
        with open(os.path.join(self.d.etats, 'etat_01.dqs'), 'rb') as f: self.assertEqual(f.read(), b'f' * 2000)
        self.assertEqual(os.path.dirname(copie), self.d.sauvegardes); self.assertTrue(os.path.basename(copie).startswith('avant_import_'))
        with open(os.path.join(copie, 'data1.dat'), 'rb') as f: self.assertEqual(f.read(), journal_valide(1))
        with open(os.path.join(copie, 'etats', 'etat_01.dqs'), 'rb') as f: self.assertEqual(f.read(), b'e' * 2000)

    def test_export_reprend_les_etats_du_bon_dossier(self):
        ecrire(os.path.join(self.d.portage, 'data1.dat'), journal_valide(1)); ecrire(os.path.join(self.d.etats, 'etat_02.dqs'), b'e' * 2000)
        sortie = os.path.join(self.t, 'sortie.zip'); self.assertEqual(S.exporter(self.d.portage, self.d.mobile, sortie), (1, 1))
        with zipfile.ZipFile(sortie) as z: self.assertEqual(sorted(z.namelist()), ['data1.dat', 'etats/etat_02.dqs'])

    def test_dossier_d_ecriture_particulier(self):                            # (tests, --saves-ecriture) : tout reste sous ce dossier
        ecr = os.path.join(self.t, 'autre'); ecrire(os.path.join(ecr, 'data1.dat'), journal_valide(1))
        zip_ = os.path.join(self.t, 'i.zip')
        with zipfile.ZipFile(zip_, 'w') as z: z.writestr('data1.dat', journal_valide(2)); z.writestr('etats/etat_03.dqs', b'g' * 2000)
        _, _, copie, _ = S.importer([zip_], ecr, self.d.mobile)
        self.assertTrue(os.path.isfile(os.path.join(ecr, 'etats', 'etat_03.dqs'))); self.assertEqual(os.path.dirname(copie), ecr)


class AnciensEtats(unittest.TestCase):
    def test_un_pickle_d_avant_le_rangement_se_relit(self):
        from dq4_pc.noyau import moteur as MO
        e = MO.Etat(); e.carte = 1234
        # on fabrique un pickle tel que l'ancienne version l'ecrivait : le module de la classe s'appelait `moteur`
        anciens = (MO.Etat.__module__, MO.Interface.__module__); sys.modules['moteur'] = MO
        try:
            MO.Etat.__module__ = 'moteur'; MO.Interface.__module__ = 'moteur'
            octets = pickle.dumps({'etat': e, 'ui': MO.Interface()}, protocol=pickle.HIGHEST_PROTOCOL)
        finally:
            MO.Etat.__module__, MO.Interface.__module__ = anciens; del sys.modules['moteur']
        self.assertIn(b'moteur', octets); self.assertNotIn(b'dq4_pc', octets)
        with self.assertRaises(ModuleNotFoundError): pickle.loads(octets)               # (sans la correspondance, c'est bien le probleme)
        p = ET._charger(octets)
        self.assertIsInstance(p['etat'], MO.Etat); self.assertEqual(p['etat'].carte, 1234); self.assertIsInstance(p['ui'], MO.Interface)

    def test_un_pickle_actuel_se_relit(self):
        from dq4_pc.noyau import moteur as MO
        self.assertEqual(ET._charger(pickle.dumps(MO.Etat())).__class__, MO.Etat)

    def test_tous_les_anciens_noms_existent(self):
        for ancien, nouveau in ET.ANCIENS_MODULES.items():
            f = os.path.join(CH.RACINE, *nouveau.split('.')) + '.py'
            self.assertTrue(os.path.isfile(f), '%s -> %s' % (ancien, nouveau))


if __name__ == '__main__':
    unittest.main(verbosity=1)
