"""Dossiers du portage (paths.py) et reprise de l'ancienne disposition : disposition par defaut, variables d'environnement, migration sans ecrasement ni suppression,
import / export de sauvegardes avec les nouveaux dossiers, anciens etats instantanes (noms de modules d'avant le rangement du 04/11/2026). Sans fenetre ni moteur.

    python3 tests/test_paths.py"""
import io, os, pickle, shutil, sys, tempfile, unittest, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from dq4_pc import paths as CH
from dq4_pc.persistence import savestates as SS
from dq4_pc.persistence import saves as S


def write(path, content=b'x'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f: f.write(content)
    return path


class Layout(unittest.TestCase):
    def test_default(self):
        d = CH.Folders('/projet', env={})
        self.assertEqual(d.data, os.path.normpath('/projet/donnees'))
        for name_str, expected in (('apk', 'donnees/apk'), ('mobile', 'donnees/sauvegardes/mobile'), ('portage', 'donnees/sauvegardes'), ('old_port_dir', 'donnees/sauvegardes/portage'), ('savestates', 'donnees/sauvegardes/etats'),
                             ('cache', 'donnees/cache'), ('settings', 'donnees/reglages/reglages.json'), ('favorites', 'donnees/reglages/historique_favoris.json'),
                             ('window_logfile', 'donnees/journaux/erreurs_fenetre.log')):
            self.assertEqual(getattr(d, name_str), os.path.normpath('/projet/' + expected), name_str)

    def test_environment_variables(self):
        d = CH.Folders('/projet', env={'DQ4_DONNEES': '/ailleurs/mes_donnees'})
        self.assertEqual(d.apk, os.path.normpath('/ailleurs/mes_donnees/apk')); self.assertEqual(d.cache, os.path.normpath('/ailleurs/mes_donnees/cache'))
        d = CH.Folders('/projet', env={'DQ4_JEUX': '/jeux/DQ4'})                      # ancien fonctionnement : APK et sauvegardes du telephone la-bas, le reste dans donnees
        self.assertEqual(d.apk, os.path.normpath('/jeux/DQ4/patched_apks')); self.assertEqual(d.mobile, os.path.normpath('/jeux/DQ4/saves'))
        self.assertEqual(d.portage, os.path.normpath('/projet/donnees/sauvegardes'))

    def test_savestates_and_copies_per_write_folder(self):
        d = CH.Folders('/projet', env={})
        self.assertEqual(d.savestates_folder(d.portage), d.savestates); self.assertEqual(d.clones_folder(d.portage), d.saves)
        self.assertEqual(d.savestates_folder('/tmp/sv_test'), os.path.join('/tmp/sv_test', 'etats')); self.assertEqual(d.clones_folder('/tmp/sv_test'), '/tmp/sv_test')

    def test_most_recent_mobile_save(self):
        with tempfile.TemporaryDirectory() as t:
            d = CH.Folders(t, env={}); self.assertIsNone(d.recent_mobile_save())
            for n in ('20261003_100000', '20261103_222423', '20261007_190735'): write(os.path.join(d.mobile, n, 'data1.dat'))
            write(os.path.join(d.mobile, 'zz_un_fichier.txt'))
            self.assertEqual(os.path.basename(d.recent_mobile_save()), '20261103_222423')


class Migration(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='migr_'); self.d = CH.Folders(self.t, env={})
        r = self.t
        write(os.path.join(r, 'jeux', 'DQ4', 'patched_apks', 'base.apk'), b'APK1'); write(os.path.join(r, 'jeux', 'DQ4', 'patched_apks', 'split_config.arm64_v8a.apk'), b'APK2')
        write(os.path.join(r, 'jeux', 'DQ4', 'saves', '20261103_222423', 'data1.dat'), b'T1'); write(os.path.join(r, 'jeux', 'DQ4', 'saves', '20261007_190735', 'data1.dat'), b'T0')
        write(os.path.join(r, 'jeux', 'DQ4', 'saves', '20261103_222423', 'data2.dat'), b'T2'); write(os.path.join(r, 'jeux', 'DQ4', 'saves', '20261007_190735', 'data3.dat'), b'T3_ancien')
        write(os.path.join(r, 'dq4_pc', 'cache', 'carte10_a.pkl'), b'CACHE'); write(os.path.join(r, 'dq4_pc', 'cache', 'il2cpp', 'dump.cs'), b'DUMP')
        write(os.path.join(r, 'dq4_pc', 'sauvegardes', 'data1.dat'), b'P1'); write(os.path.join(r, 'dq4_pc', 'sauvegardes', 'etats', 'etat_01.dqs'), b'E1')
        write(os.path.join(r, 'dq4_pc', 'sauvegardes', 'avant_import_20261101_101010', 'data2.dat'), b'AV')
        write(os.path.join(r, 'dq4_pc', 'reglages.json'), b'{"a": 1}'); write(os.path.join(r, 'dq4_pc', 'historique_favoris.json'), b'[]'); write(os.path.join(r, 'dq4_pc', 'erreurs_fenetre.log'), b'LOG')

    def tearDown(self): shutil.rmtree(self.t, ignore_errors=True)

    def read(self, *p):
        with open(os.path.join(self.t, *p), 'rb') as f: return f.read()

    def test_complete_resume(self):
        done = CH.migrate(self.d, log=lambda *a: None)
        self.assertGreaterEqual(len(done), 6)
        self.assertEqual(self.read('donnees', 'apk', 'base.apk'), b'APK1')
        self.assertEqual(self.read('donnees', 'sauvegardes', 'data1.dat'), b'P1')                                        # les journaux du portage d'avant passent avant la copie du telephone (T1)
        self.assertEqual(self.read('donnees', 'sauvegardes', 'data2.dat'), b'T2')                                        # ... qui complete ce qui manque (la plus recente seulement)
        self.assertFalse(os.path.exists(os.path.join(self.t, 'donnees', 'sauvegardes', 'data3.dat')))                    # (pas celui d'une date plus ancienne)
        self.assertFalse(os.path.exists(os.path.join(self.t, 'donnees', 'sauvegardes', 'mobile'))); self.assertFalse(os.path.exists(os.path.join(self.t, 'donnees', 'sauvegardes', 'portage')))
        self.assertEqual(self.read('donnees', 'cache', 'carte10_a.pkl'), b'CACHE'); self.assertEqual(self.read('donnees', 'cache', 'il2cpp', 'dump.cs'), b'DUMP')
        self.assertEqual(self.read('donnees', 'sauvegardes', 'etats', 'etat_01.dqs'), b'E1')
        self.assertEqual(self.read('donnees', 'sauvegardes', 'avant_import_20261101_101010', 'data2.dat'), b'AV')
        self.assertEqual(self.read('donnees', 'reglages', 'reglages.json'), b'{"a": 1}'); self.assertEqual(self.read('donnees', 'reglages', 'historique_favoris.json'), b'[]')
        self.assertEqual(self.read('donnees', 'journaux', 'erreurs_fenetre.log'), b'LOG')

    def test_originals_remain_except_cache(self):
        CH.migrate(self.d, log=lambda *a: None)
        for p in (('jeux', 'DQ4', 'patched_apks', 'base.apk'), ('jeux', 'DQ4', 'saves', '20261103_222423', 'data1.dat'), ('dq4_pc', 'sauvegardes', 'data1.dat'),
                  ('dq4_pc', 'sauvegardes', 'etats', 'etat_01.dqs'), ('dq4_pc', 'reglages.json'), ('dq4_pc', 'historique_favoris.json')):
            self.assertTrue(os.path.isfile(os.path.join(self.t, *p)), p)
        self.assertFalse(os.path.exists(os.path.join(self.t, 'dq4_pc', 'cache')), 'le cache est deplace (meme volume : un renommage)')

    def test_nothing_overwritten_and_resume_does_not_repeat(self):
        write(os.path.join(self.t, 'donnees', 'reglages', 'reglages.json'), b'{"nouveau": 2}')                 # reglages deja changes dans la nouvelle version : gardes
        write(os.path.join(self.t, 'donnees', 'sauvegardes', 'portage', 'data1.dat'), b'NEUF')                       # le dossier d'ecriture d'hier : ce que le jeu a ecrit ensuite l'emporte sur le vieux portage (P1)
        CH.migrate(self.d, log=lambda *a: None)
        self.assertEqual(self.read('donnees', 'reglages', 'reglages.json'), b'{"nouveau": 2}'); self.assertEqual(self.read('donnees', 'sauvegardes', 'data1.dat'), b'NEUF')
        self.assertEqual(CH.migrate(self.d, log=lambda *a: None), [])

    def test_what_you_erase_does_not_come_back(self):                                  # D-235 : le dossier avant_import_... effacé revenait a chaque demarrage (recopie depuis dq4_pc\\sauvegardes)
        CH.migrate(self.d, log=lambda *a: None)
        av = os.path.join(self.t, 'donnees', 'sauvegardes', 'avant_import_20261101_101010'); self.assertTrue(os.path.isdir(av))
        shutil.rmtree(os.path.join(self.t, 'donnees', 'sauvegardes')); shutil.rmtree(os.path.join(self.t, 'donnees', 'reglages'))        # (tout effacé : seul le fichier de reprise empeche la recopie)
        self.assertEqual(CH.migrate(self.d, log=lambda *a: None), [])
        for p in (('sauvegardes',), ('reglages',)): self.assertFalse(os.path.exists(os.path.join(self.t, 'donnees', *p)), p)
        self.assertTrue(os.path.isfile(os.path.join(self.t, 'dq4_pc', 'sauvegardes', 'data1.dat')))              # (l'ancien dossier n'est toujours pas touché)

    def test_layout_already_in_use_nothing_is_copied(self):                 # le cas de Sylfried : la reprise a eu lieu avec une version d'avant D-235, il a effacé avant_import_... a la main
        write(os.path.join(self.t, 'donnees', 'sauvegardes', 'data3.dat'), b'A_MOI'); write(os.path.join(self.t, 'donnees', 'reglages', 'reglages.json'), b'{}')
        write(os.path.join(self.t, 'donnees', 'cache', 'x.pkl'), b'C'); write(os.path.join(self.t, 'donnees', 'apk', 'base.apk'), b'A'); write(os.path.join(self.t, 'donnees', 'journaux', 'erreurs_fenetre.log'), b'J')
        self.assertEqual(CH.migrate(self.d, log=lambda *a: None), [])
        self.assertEqual(sorted(os.listdir(os.path.join(self.t, 'donnees', 'sauvegardes'))), ['data3.dat'])
        self.assertEqual(self.read('donnees', 'reglages', 'reglages.json'), b'{}')
        with open(self.d.resume_file, encoding='utf-8') as f: stages = __import__('json').load(f)['etapes']
        self.assertEqual(sorted(stages), sorted(CH.STAGES)); self.assertEqual(CH.migrate(self.d, log=lambda *a: None), [])

    def test_unreadable_migration_file(self):
        write(self.d.resume_file, b'{pas du json')
        done = CH.migrate(self.d, log=lambda *a: None)                                                      # comme une premiere fois : copie sans rien ecraser, puis le fichier est refait
        self.assertGreaterEqual(len(done), 6); self.assertEqual(self.read('donnees', 'sauvegardes', 'data1.dat'), b'P1')
        self.assertEqual(CH.migrate(self.d, log=lambda *a: None), [])

    def test_a_stage_without_old_folder_writes_nothing(self):
        with tempfile.TemporaryDirectory() as empty:
            dv = CH.Folders(empty, env={}); self.assertEqual(CH.migrate(dv, log=lambda *a: None), []); self.assertFalse(os.path.exists(dv.resume_file))

    def test_existing_cache_left_untouched(self):
        write(os.path.join(self.t, 'donnees', 'cache', 'autre.pkl'), b'N')
        CH.migrate(self.d, log=lambda *a: None)
        self.assertTrue(os.path.isfile(os.path.join(self.t, 'dq4_pc', 'cache', 'carte10_a.pkl'))); self.assertFalse(os.path.exists(os.path.join(self.t, 'donnees', 'cache', 'carte10_a.pkl')))

    def test_nothing_to_resume(self):
        with tempfile.TemporaryDirectory() as empty: self.assertEqual(CH.migrate(CH.Folders(empty, env={}), log=lambda *a: None), [])


def logfile(raw=0x3c00): return bytes(raw)


def valid_logfile(n=0):
    """Un journal du jeu valide (en-tete « rate », somme de controle, chiffre) ; `n` le distingue des autres."""
    import struct
    from dq4_pc.persistence import logfile_format as FJ
    plain = bytearray(FJ.LOGFILE_SIZE); struct.pack_into('<II', plain, 0, FJ.MAGIE1, FJ.MAGIE2); plain[0x30] = n
    struct.pack_into('<I', plain, 8, FJ.checksum(bytes(plain))); return FJ.decrypt(bytes(plain))


class Saves(unittest.TestCase):
    """Import / export avec la disposition de donnees\\sauvegardes (etats et copies a cote de `portage`)."""
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='sv_'); self.d = CH.Folders(self.t, env={}); self.before = CH.FOLDERS; CH.FOLDERS = self.d

    def tearDown(self): CH.FOLDERS = self.before; shutil.rmtree(self.t, ignore_errors=True)

    def test_import_in_usual_layout(self):
        write(os.path.join(self.d.portage, 'data1.dat'), valid_logfile(1)); write(os.path.join(self.d.savestates, 'etat_01.dqs'), b'e' * 2000)
        zip_ = os.path.join(self.t, 'import.zip')
        with zipfile.ZipFile(zip_, 'w') as z: z.writestr('data1.dat', valid_logfile(2)); z.writestr('etats/etat_01.dqs', b'f' * 2000)
        nj, n_savestates, copied, pb = S.import_saves([zip_], self.d.portage, self.d.mobile)
        self.assertEqual((nj, n_savestates, pb), (1, 1, []))
        with open(os.path.join(self.d.portage, 'data1.dat'), 'rb') as f: self.assertEqual(f.read(), valid_logfile(2))
        with open(os.path.join(self.d.savestates, 'etat_01.dqs'), 'rb') as f: self.assertEqual(f.read(), b'f' * 2000)
        self.assertEqual(os.path.dirname(copied), self.d.saves); self.assertTrue(os.path.basename(copied).startswith('avant_import_'))
        with open(os.path.join(copied, 'data1.dat'), 'rb') as f: self.assertEqual(f.read(), valid_logfile(1))
        with open(os.path.join(copied, 'etats', 'etat_01.dqs'), 'rb') as f: self.assertEqual(f.read(), b'e' * 2000)

    def test_phone_manifest_json_is_ignored(self):                          # D-235 : le jeu ne lit pas manifest.json (liste des fichiers + sha256 faite par l'outil de copie) ; les journaux ont leur propre controle
        src = os.path.join(self.t, 'copie_telephone'); write(os.path.join(src, 'data3.dat'), valid_logfile(3)); write(os.path.join(src, 'manifest.json'), b'{"files": {"data3.dat": {"size": 15360, "sha256": "0"}}}')
        jr, label, pb = S.read_sources([src]); self.assertEqual((sorted(jr), label, pb), (['data3.dat'], {}, []))
        nj, n_savestates, copied, pb = S.import_saves([src], self.d.portage, self.d.mobile); self.assertEqual((nj, n_savestates, copied, pb), (1, 0, None, []))
        self.assertFalse(os.path.exists(os.path.join(self.d.portage, 'manifest.json')))

    def test_export_takes_savestates_from_right_folder(self):
        write(os.path.join(self.d.portage, 'data1.dat'), valid_logfile(1)); write(os.path.join(self.d.savestates, 'etat_02.dqs'), b'e' * 2000)
        output = os.path.join(self.t, 'sortie.zip'); self.assertEqual(S.export_saves(self.d.portage, self.d.mobile, output), (1, 1))
        with zipfile.ZipFile(output) as z: self.assertEqual(sorted(z.namelist()), ['data1.dat', 'etats/etat_02.dqs'])

    def test_specific_write_folder(self):                            # (tests, --saves-ecriture) : tout reste sous ce dossier
        wdir = os.path.join(self.t, 'autre'); write(os.path.join(wdir, 'data1.dat'), valid_logfile(1))
        zip_ = os.path.join(self.t, 'i.zip')
        with zipfile.ZipFile(zip_, 'w') as z: z.writestr('data1.dat', valid_logfile(2)); z.writestr('etats/etat_03.dqs', b'g' * 2000)
        _, _, copied, _ = S.import_saves([zip_], wdir, self.d.mobile)
        self.assertTrue(os.path.isfile(os.path.join(wdir, 'etats', 'etat_03.dqs'))); self.assertEqual(os.path.dirname(copied), wdir)


class OldSavestates(unittest.TestCase):
    def test_a_pickle_from_before_the_tidy_up_can_be_reread(self):
        from dq4_pc.core import engine as ENGINE
        e = ENGINE.State(); e.game_map = 1234
        # on fabrique un pickle tel que l'ancienne version l'ecrivait : le module de la classe s'appelait `engine`
        old_dirs = (ENGINE.State.__module__, ENGINE.Interface.__module__); sys.modules['moteur'] = ENGINE
        try:
            ENGINE.State.__module__ = 'moteur'; ENGINE.Interface.__module__ = 'moteur'
            raw = pickle.dumps({'etat': e, 'ui': ENGINE.Interface()}, protocol=pickle.HIGHEST_PROTOCOL)
        finally:
            ENGINE.State.__module__, ENGINE.Interface.__module__ = old_dirs; del sys.modules['moteur']
        self.assertIn(b'moteur', raw); self.assertNotIn(b'dq4_pc', raw)
        with self.assertRaises(ModuleNotFoundError): pickle.loads(raw)               # (sans la correspondance, c'est bien le probleme)
        p = SS._load(raw)
        self.assertIsInstance(p['etat'], ENGINE.State); self.assertEqual(p['etat'].game_map, 1234); self.assertIsInstance(p['ui'], ENGINE.Interface)

    def test_a_current_pickle_can_be_reread(self):
        from dq4_pc.core import engine as ENGINE
        self.assertEqual(SS._load(pickle.dumps(ENGINE.State())).__class__, ENGINE.State)

    def test_all_old_names_exist(self):
        for old, new in SS.OLD_MODULES.items():
            f = os.path.join(CH.ROOT, *new.split('.')) + '.py'
            self.assertTrue(os.path.isfile(f), '%s -> %s' % (old, new))


if __name__ == '__main__':
    unittest.main(verbosity=1)
