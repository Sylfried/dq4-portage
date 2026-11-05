"""Dossiers du portage (paths.py) et reprise de l'ancienne disposition : disposition par defaut, variables d'environnement, migration sans ecrasement ni suppression,
import / export de sauvegardes avec les nouveaux dossiers, anciens etats instantanes (noms de modules d'avant le rangement du 04/11/2026). Sans fenetre ni moteur.

    python3 tests/test_paths.py"""
import io, os, pickle, shutil, sys, tempfile, unittest, zipfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from dq4_pc import paths as CH
from dq4_pc import language as LG
from dq4_pc.persistence import savestates as SS
from dq4_pc.persistence import saves as S


def write(path, content=b'x'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f: f.write(content)
    return path


class Layout(unittest.TestCase):
    def test_default(self):
        d = CH.Folders('/projet', env={})
        self.assertEqual(d.data, os.path.normpath('/projet/data'))
        for name_str, expected in (('apk', 'data/apk'), ('mobile', 'data/saves/mobile'), ('portage', 'data/saves'), ('old_port_dir', 'data/saves/portage'), ('savestates', 'data/saves/savestates'),
                             ('cache', 'data/cache'), ('settings', 'data/settings/settings.json'), ('favorites', 'data/settings/history_favorites.json'),
                             ('window_logfile', 'data/logs/window_errors.log')):
            self.assertEqual(getattr(d, name_str), os.path.normpath('/projet/' + expected), name_str)

    def test_environment_variables(self):
        d = CH.Folders('/projet', env={'DQ4_DATA': '/ailleurs/mes_donnees'})
        self.assertEqual(d.apk, os.path.normpath('/ailleurs/mes_donnees/apk')); self.assertEqual(d.cache, os.path.normpath('/ailleurs/mes_donnees/cache'))
        d = CH.Folders('/projet', env={'DQ4_GAMES': '/jeux/DQ4'})                      # ancien fonctionnement : APK et sauvegardes du telephone la-bas, le reste dans donnees
        self.assertEqual(d.apk, os.path.normpath('/jeux/DQ4/patched_apks')); self.assertEqual(d.mobile, os.path.normpath('/jeux/DQ4/saves'))
        self.assertEqual(d.portage, os.path.normpath('/projet/data/saves'))

    def test_savestates_and_copies_per_write_folder(self):
        d = CH.Folders('/projet', env={})
        self.assertEqual(d.savestates_folder(d.portage), d.savestates); self.assertEqual(d.clones_folder(d.portage), d.saves)
        self.assertEqual(d.savestates_folder('/tmp/sv_test'), os.path.join('/tmp/sv_test', 'savestates')); self.assertEqual(d.clones_folder('/tmp/sv_test'), '/tmp/sv_test')

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
        self.assertEqual(self.read('data', 'apk', 'base.apk'), b'APK1')
        self.assertEqual(self.read('data', 'saves', 'data1.dat'), b'P1')                                        # les journaux du portage d'avant passent avant la copie du telephone (T1)
        self.assertEqual(self.read('data', 'saves', 'data2.dat'), b'T2')                                        # ... qui complete ce qui manque (la plus recente seulement)
        self.assertFalse(os.path.exists(os.path.join(self.t, 'data', 'saves', 'data3.dat')))                    # (pas celui d'une date plus ancienne)
        self.assertFalse(os.path.exists(os.path.join(self.t, 'data', 'saves', 'mobile'))); self.assertFalse(os.path.exists(os.path.join(self.t, 'data', 'saves', 'portage')))
        self.assertEqual(self.read('data', 'cache', 'carte10_a.pkl'), b'CACHE'); self.assertEqual(self.read('data', 'cache', 'il2cpp', 'dump.cs'), b'DUMP')
        self.assertEqual(self.read('data', 'saves', 'savestates', 'state_01.dqs'), b'E1')
        self.assertEqual(self.read('data', 'saves', 'before_import_20261101_101010', 'data2.dat'), b'AV')
        self.assertEqual(self.read('data', 'settings', 'settings.json'), b'{"a": 1}'); self.assertEqual(self.read('data', 'settings', 'history_favorites.json'), b'[]')
        self.assertEqual(self.read('data', 'logs', 'window_errors.log'), b'LOG')

    def test_originals_remain_except_cache(self):
        CH.migrate(self.d, log=lambda *a: None)
        for p in (('jeux', 'DQ4', 'patched_apks', 'base.apk'), ('jeux', 'DQ4', 'saves', '20261103_222423', 'data1.dat'), ('dq4_pc', 'sauvegardes', 'data1.dat'),
                  ('dq4_pc', 'sauvegardes', 'etats', 'etat_01.dqs'), ('dq4_pc', 'reglages.json'), ('dq4_pc', 'historique_favoris.json')):
            self.assertTrue(os.path.isfile(os.path.join(self.t, *p)), p)
        self.assertFalse(os.path.exists(os.path.join(self.t, 'dq4_pc', 'cache')), 'le cache est deplace (meme volume : un renommage)')

    def test_nothing_overwritten_and_resume_does_not_repeat(self):
        write(os.path.join(self.t, 'data', 'settings', 'settings.json'), b'{"nouveau": 2}')                 # reglages deja changes dans la nouvelle version : gardes
        write(os.path.join(self.t, 'data', 'saves', 'portage', 'data1.dat'), b'NEUF')                       # le dossier d'ecriture d'hier : ce que le jeu a ecrit ensuite l'emporte sur le vieux portage (P1)
        CH.migrate(self.d, log=lambda *a: None)
        self.assertEqual(self.read('data', 'settings', 'settings.json'), b'{"nouveau": 2}'); self.assertEqual(self.read('data', 'saves', 'data1.dat'), b'NEUF')
        self.assertEqual(CH.migrate(self.d, log=lambda *a: None), [])

    def test_what_you_erase_does_not_come_back(self):                                  # D-235 : le dossier avant_import_... effacé revenait a chaque demarrage (recopie depuis dq4_pc\\sauvegardes)
        CH.migrate(self.d, log=lambda *a: None)
        av = os.path.join(self.t, 'data', 'saves', 'before_import_20261101_101010'); self.assertTrue(os.path.isdir(av))
        shutil.rmtree(os.path.join(self.t, 'data', 'saves')); shutil.rmtree(os.path.join(self.t, 'data', 'settings'))        # (tout effacé : seul le fichier de reprise empeche la recopie)
        self.assertEqual(CH.migrate(self.d, log=lambda *a: None), [])
        for p in (('saves',), ('settings',)): self.assertFalse(os.path.exists(os.path.join(self.t, 'data', *p)), p)
        self.assertTrue(os.path.isfile(os.path.join(self.t, 'dq4_pc', 'sauvegardes', 'data1.dat')))              # (l'ancien dossier n'est toujours pas touché)

    def test_layout_already_in_use_nothing_is_copied(self):                 # le cas de Sylfried : la reprise a eu lieu avec une version d'avant D-235, il a effacé avant_import_... a la main
        write(os.path.join(self.t, 'data', 'saves', 'data3.dat'), b'A_MOI'); write(os.path.join(self.t, 'data', 'settings', 'settings.json'), b'{}')
        write(os.path.join(self.t, 'data', 'cache', 'x.pkl'), b'C'); write(os.path.join(self.t, 'data', 'apk', 'base.apk'), b'A'); write(os.path.join(self.t, 'data', 'logs', 'window_errors.log'), b'J')
        self.assertEqual(CH.migrate(self.d, log=lambda *a: None), [])
        self.assertEqual(sorted(os.listdir(os.path.join(self.t, 'data', 'saves'))), ['data3.dat'])
        self.assertEqual(self.read('data', 'settings', 'settings.json'), b'{}')
        with open(self.d.resume_file, encoding='utf-8') as f: stages = __import__('json').load(f)['stages']
        self.assertEqual(sorted(stages), sorted(set(CH.STAGES) - {CH.ENGLISH_STAGE})); self.assertEqual(CH.migrate(self.d, log=lambda *a: None), [])         # (rien a renommer : l'etape D-239 n'est pas notee)

    def test_unreadable_migration_file(self):
        write(self.d.resume_file, b'{pas du json')
        done = CH.migrate(self.d, log=lambda *a: None)                                                      # comme une premiere fois : copie sans rien ecraser, puis le fichier est refait
        self.assertGreaterEqual(len(done), 6); self.assertEqual(self.read('data', 'saves', 'data1.dat'), b'P1')
        self.assertEqual(CH.migrate(self.d, log=lambda *a: None), [])

    def test_a_stage_without_old_folder_writes_nothing(self):
        with tempfile.TemporaryDirectory() as empty:
            dv = CH.Folders(empty, env={}); self.assertEqual(CH.migrate(dv, log=lambda *a: None), []); self.assertFalse(os.path.exists(dv.resume_file)); self.assertFalse(os.path.exists(dv.data))

    def test_existing_cache_left_untouched(self):
        write(os.path.join(self.t, 'data', 'cache', 'autre.pkl'), b'N')
        CH.migrate(self.d, log=lambda *a: None)
        self.assertTrue(os.path.isfile(os.path.join(self.t, 'dq4_pc', 'cache', 'carte10_a.pkl'))); self.assertFalse(os.path.exists(os.path.join(self.t, 'data', 'cache', 'carte10_a.pkl')))

    def test_nothing_to_resume(self):
        with tempfile.TemporaryDirectory() as empty: self.assertEqual(CH.migrate(CH.Folders(empty, env={}), log=lambda *a: None), [])


class EnglishNames(unittest.TestCase):
    """D-239 : les dossiers et fichiers que les versions d'avant creaient en francais sont renommes sur place (sans copie, sans rien ecraser ni supprimer)."""
    @classmethod
    def setUpClass(cls): LG.select_language('fr')                      # (les phrases de la reprise sont testees en francais)

    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='en_'); self.d = CH.Folders(self.t, env={})
        o = os.path.join(self.t, 'donnees')                       # la disposition d'avant D-239, telle qu'elle est sur le PC
        write(os.path.join(o, 'apk', 'base.apk'), b'A'); write(os.path.join(o, 'cache', 'x.pkl'), b'C'); write(os.path.join(o, 'sauvegardes', 'data1.dat'), b'D1')
        write(os.path.join(o, 'sauvegardes', 'etats', 'etat_01.dqs'), b'E1'); write(os.path.join(o, 'sauvegardes', 'etats', 'etat_09.dqs'), b'E9')
        write(os.path.join(o, 'sauvegardes', 'avant_import_20261101_101010', 'data2.dat'), b'AV'); write(os.path.join(o, 'sauvegardes', 'avant_import_20261101_101010', 'etats', 'etat_02.dqs'), b'AE')
        write(os.path.join(o, 'sauvegardes', 'avant_rangement_20261102_090000', 'portage', 'etats', 'etat_05.dqs'), b'ARCH')
        write(os.path.join(o, 'reglages', 'reglages.json'), b'{"a": 1}'); write(os.path.join(o, 'reglages', 'historique_favoris.json'), b'[]'); write(os.path.join(o, 'reglages', 'historique_messages.json'), b'[1]')
        write(os.path.join(o, 'journaux', 'erreurs_fenetre.log'), b'LOG')
        write(os.path.join(o, 'reprise.json'), b'{"etapes": {"cache": "01/11/2026", "sauvegardes_portage": "01/11/2026", "reglages": "en place", "journal": "en place"}}')

    def tearDown(self): shutil.rmtree(self.t, ignore_errors=True)

    def read(self, *p):
        with open(os.path.join(self.t, *p), 'rb') as f: return f.read()

    def test_names(self):
        for old, new, is_dir in (('etats', 'savestates', True), ('etat_07.dqs', 'state_07.dqs', False), ('avant_import_20261101_101010', 'before_import_20261101_101010', True), ('avant_rangement_x', 'before_tidy_x', True),
                                 ('reglages.json', 'settings.json', False), ('reglages.json.tmp', 'settings.json.tmp', False), ('historique_favoris.json', 'history_favorites.json', False),
                                 ('erreurs_fenetre.log', 'window_errors.log', False), ('reprise.json', 'resume.json', False), ('sauvegardes', 'saves', True), ('journaux', 'logs', True)):
            self.assertEqual(CH.english_name(old, is_dir), new, old)
        for same, is_dir in (('data1.dat', False), ('cache', True), ('apk', True), ('state_01.dqs', False), ('portage', True), ('etat_1.dqs', False), ('etats', False)):
            self.assertIsNone(CH.english_name(same, is_dir), same)

    def test_complete_renaming(self):
        done = CH.migrate(self.d, log=lambda *a: None)
        self.assertTrue(any('donnees' in x and 'data' in x for x in done), done)
        self.assertFalse(os.path.exists(os.path.join(self.t, 'donnees')))
        self.assertEqual(self.read('data', 'apk', 'base.apk'), b'A'); self.assertEqual(self.read('data', 'cache', 'x.pkl'), b'C')
        self.assertEqual(self.read('data', 'saves', 'data1.dat'), b'D1')
        self.assertEqual(self.read('data', 'saves', 'savestates', 'state_01.dqs'), b'E1'); self.assertEqual(self.read('data', 'saves', 'savestates', 'state_09.dqs'), b'E9')
        self.assertEqual(self.read('data', 'saves', 'before_import_20261101_101010', 'data2.dat'), b'AV')
        self.assertEqual(self.read('data', 'saves', 'before_import_20261101_101010', 'savestates', 'state_02.dqs'), b'AE')
        self.assertEqual(self.read('data', 'saves', 'before_tidy_20261102_090000', 'portage', 'etats', 'etat_05.dqs'), b'ARCH')           # (les dossiers ranges par la reprise restent tels quels)
        self.assertEqual(self.read('data', 'settings', 'settings.json'), b'{"a": 1}'); self.assertEqual(self.read('data', 'settings', 'history_favorites.json'), b'[]')
        self.assertEqual(self.read('data', 'settings', 'history_messages.json'), b'[1]'); self.assertEqual(self.read('data', 'logs', 'window_errors.log'), b'LOG')
        self.assertFalse(os.path.exists(os.path.join(self.t, 'data', 'reprise.json')))
        with open(self.d.resume_file, encoding='utf-8') as f: stages = __import__('json').load(f)['stages']
        self.assertEqual(sorted(stages), sorted(CH.STAGES)); self.assertEqual(stages['saves_pc_port'], '01/11/2026')                      # (anciens noms d'etapes traduits, dates gardees ; les autres etapes : destination deja en service ; etape D-239 ajoutee)
        self.assertEqual(CH.migrate(self.d, log=lambda *a: None), [])                                                                    # (une seule fois)

    def test_same_files_after_renaming(self):
        before = sorted((os.path.relpath(os.path.join(r, f), os.path.join(self.t, 'donnees')), open(os.path.join(r, f), 'rb').read())
                        for r, _, files in os.walk(os.path.join(self.t, 'donnees')) for f in files if f != 'reprise.json')
        CH.migrate(self.d, log=lambda *a: None)
        after = sorted((os.path.relpath(os.path.join(r, f), os.path.join(self.t, 'data')), open(os.path.join(r, f), 'rb').read())
                       for r, _, files in os.walk(os.path.join(self.t, 'data')) for f in files if f != 'resume.json')
        self.assertEqual([c for _, c in before], [c for _, c in sorted(after, key=lambda x: [b for a, b in before].index(x[1]))])        # (aucun contenu perdu, aucun ajoute)

    def test_nothing_overwritten_on_conflict(self):
        write(os.path.join(self.t, 'data', 'settings', 'settings.json'), b'{"nouveau": 2}')                  # un reglage existe deja a la nouvelle place : il gagne, l'ancien reste ou il est
        write(os.path.join(self.t, 'data', 'saves', 'savestates', 'state_01.dqs'), b'NEUF')
        done = CH.migrate(self.d, log=lambda *a: None)
        self.assertEqual(self.read('data', 'settings', 'settings.json'), b'{"nouveau": 2}'); self.assertEqual(self.read('data', 'saves', 'savestates', 'state_01.dqs'), b'NEUF')
        self.assertEqual(self.read('data', 'settings', 'reglages.json'), b'{"a": 1}'); self.assertEqual(self.read('data', 'saves', 'savestates', 'etat_01.dqs'), b'E1')      # (a leur place d'avant, intacts)
        self.assertEqual(self.read('data', 'saves', 'savestates', 'state_09.dqs'), b'E9')                       # (le reste est renomme)
        self.assertTrue(any('NON renomme' in x for x in done), done)
        self.assertNotIn(CH.ENGLISH_STAGE, CH._read_resume(self.d))                                         # (pas note fait : le renommage sera refait au prochain demarrage)
        self.assertTrue(any('NON renomme' in x for x in CH.migrate(self.d, log=lambda *a: None)))

    def test_both_folders_exist_merge(self):
        write(os.path.join(self.t, 'data', 'saves', 'data3.dat'), b'D3')                                   # `data\\saves` existe deja (renommage interrompu) : on y remet le reste, un fichier a la fois
        done = CH.migrate(self.d, log=lambda *a: None)
        self.assertEqual(self.read('data', 'saves', 'data3.dat'), b'D3'); self.assertEqual(self.read('data', 'saves', 'data1.dat'), b'D1')
        self.assertEqual(self.read('data', 'saves', 'savestates', 'state_01.dqs'), b'E1'); self.assertFalse(os.path.exists(os.path.join(self.t, 'donnees')))
        self.assertFalse(any('NON renomme' in x for x in done), done)

    def test_locked_folder_falls_back_to_its_content(self):               # Windows : un dossier ouvert dans l'Explorateur ne se renomme pas ; ses fichiers, eux, se deplacent un par un
        actual = os.replace

        def refuse_folders(src, dst):
            if os.path.isdir(src): raise PermissionError('dossier ouvert')
            return actual(src, dst)
        with mock.patch('dq4_pc.paths.os.replace', side_effect=refuse_folders): done = CH.migrate(self.d, log=lambda *a: None)
        self.assertFalse(any('NON renomme' in x for x in done), done); self.assertFalse(os.path.exists(os.path.join(self.t, 'donnees')))
        self.assertEqual(self.read('data', 'saves', 'savestates', 'state_01.dqs'), b'E1'); self.assertEqual(self.read('data', 'apk', 'base.apk'), b'A'); self.assertEqual(self.read('data', 'settings', 'settings.json'), b'{"a": 1}')
        self.assertEqual(CH.migrate(self.d, log=lambda *a: None), [])

    def test_nothing_can_be_renamed_then_it_is_retried(self):
        def refuse_all(src, dst): raise PermissionError('acces refuse')
        with mock.patch('dq4_pc.paths.os.replace', side_effect=refuse_all): done = CH.migrate(self.d, log=lambda *a: None)
        self.assertTrue(any('NON renomme' in x and 'acces refuse' in x for x in done), done)
        self.assertEqual(self.read('donnees', 'sauvegardes', 'etats', 'etat_01.dqs'), b'E1'); self.assertEqual(self.read('donnees', 'sauvegardes', 'data1.dat'), b'D1')          # (rien n'a bouge ni disparu)
        self.assertNotIn(CH.ENGLISH_STAGE, CH._read_resume(self.d))
        done = CH.migrate(self.d, log=lambda *a: None)                                                           # le demarrage suivant termine
        self.assertFalse(any('NON renomme' in x for x in done), done); self.assertEqual(self.read('data', 'saves', 'savestates', 'state_01.dqs'), b'E1')
        self.assertIn(CH.ENGLISH_STAGE, CH._read_resume(self.d))

    def test_english_sentences(self):
        for code, begins in (('fr', ('dossiers renommes en anglais : ', 'fichier(s) renomme(s) en anglais')), ('en', ('folders renamed to English: ', 'file(s) renamed to English'))):
            shutil.rmtree(self.t); self.setUp(); LG.select_language(code)
            done = CH.migrate(self.d, log=lambda *a: None)
            for b in begins: self.assertTrue(any(b in x for x in done), (b, done))
        LG.select_language('fr')

    def test_custom_folder_is_not_renamed(self):                       # DQ4_DATA / DQ4_DONNEES : le dossier est le tien, seul son contenu est renomme
        mine = os.path.join(self.t, 'mes_donnees'); shutil.move(os.path.join(self.t, 'donnees'), mine)
        for var in ('DQ4_DATA', 'DQ4_DONNEES'):
            d = CH.Folders(self.t, env={var: mine})
            self.assertEqual(d.data, mine)
        CH.migrate(d, log=lambda *a: None)
        self.assertEqual(open(os.path.join(mine, 'saves', 'savestates', 'state_01.dqs'), 'rb').read(), b'E1'); self.assertFalse(os.path.exists(os.path.join(self.t, 'data')))

    def test_old_variable_names_still_work(self):
        self.assertEqual(CH.Folders('/p', env={'DQ4_DONNEES': '/x/d'}).data, os.path.normpath('/x/d'))
        self.assertEqual(CH.Folders('/p', env={'DQ4_JEUX': '/j/DQ4'}).apk, os.path.normpath('/j/DQ4/patched_apks'))
        self.assertEqual(CH.Folders('/p', env={'DQ4_DATA': '/new', 'DQ4_DONNEES': '/old'}).data, os.path.normpath('/new'))                  # (le nouveau nom l'emporte)

    def test_old_resume_file_is_read_before_renaming(self):
        shutil.move(os.path.join(self.t, 'donnees'), os.path.join(self.t, 'data'))                               # (dossier deja renomme, mais `reprise.json` d'avant, avec `etapes` et les anciens noms d'etapes, pas encore)
        self.assertEqual(CH._read_resume(self.d).get('saves_pc_port'), '01/11/2026')

    def test_old_layout_copied_in_english_names(self):               # la reprise de la toute premiere disposition arrive deja dans les bons noms (etats, copies de securite)
        with tempfile.TemporaryDirectory() as t:
            write(os.path.join(t, 'dq4_pc', 'sauvegardes', 'etats', 'etat_04.dqs'), b'E4'); write(os.path.join(t, 'dq4_pc', 'sauvegardes', 'avant_import_20261101_101010', 'etats', 'etat_06.dqs'), b'E6')
            write(os.path.join(t, 'dq4_pc', 'reglages.json'), b'{}'); write(os.path.join(t, 'dq4_pc', 'historique_messages.json'), b'[]'); write(os.path.join(t, 'dq4_pc', 'erreurs_fenetre.log'), b'L')
            d = CH.Folders(t, env={}); CH.migrate(d, log=lambda *a: None)
            for p in (('saves', 'savestates', 'state_04.dqs'), ('saves', 'before_import_20261101_101010', 'savestates', 'state_06.dqs'), ('settings', 'settings.json'), ('settings', 'history_messages.json'), ('logs', 'window_errors.log')):
                self.assertTrue(os.path.isfile(os.path.join(t, 'data', *p)), p)


def logfile(raw=0x3c00): return bytes(raw)


def valid_logfile(n=0):
    """Un journal du jeu valide (en-tete « rate », somme de controle, chiffre) ; `n` le distingue des autres."""
    import struct
    from dq4_pc.persistence import logfile_format as FJ
    plain = bytearray(FJ.LOGFILE_SIZE); struct.pack_into('<II', plain, 0, FJ.MAGIE1, FJ.MAGIE2); plain[0x30] = n
    struct.pack_into('<I', plain, 8, FJ.checksum(bytes(plain))); return FJ.decrypt(bytes(plain))


class Saves(unittest.TestCase):
    """Import / export avec la disposition de data\\saves (etats et copies a cote de `portage`)."""
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='sv_'); self.d = CH.Folders(self.t, env={}); self.before = CH.FOLDERS; CH.FOLDERS = self.d

    def tearDown(self): CH.FOLDERS = self.before; shutil.rmtree(self.t, ignore_errors=True)

    def test_import_in_usual_layout(self):
        write(os.path.join(self.d.portage, 'data1.dat'), valid_logfile(1)); write(os.path.join(self.d.savestates, 'state_01.dqs'), b'e' * 2000)
        zip_ = os.path.join(self.t, 'import.zip')
        with zipfile.ZipFile(zip_, 'w') as z: z.writestr('data1.dat', valid_logfile(2)); z.writestr('savestates/state_01.dqs', b'f' * 2000)
        nj, n_savestates, copied, pb = S.import_saves([zip_], self.d.portage, self.d.mobile)
        self.assertEqual((nj, n_savestates, pb), (1, 1, []))
        with open(os.path.join(self.d.portage, 'data1.dat'), 'rb') as f: self.assertEqual(f.read(), valid_logfile(2))
        with open(os.path.join(self.d.savestates, 'state_01.dqs'), 'rb') as f: self.assertEqual(f.read(), b'f' * 2000)
        self.assertEqual(os.path.dirname(copied), self.d.saves); self.assertTrue(os.path.basename(copied).startswith('before_import_'))
        with open(os.path.join(copied, 'data1.dat'), 'rb') as f: self.assertEqual(f.read(), valid_logfile(1))
        with open(os.path.join(copied, 'savestates', 'state_01.dqs'), 'rb') as f: self.assertEqual(f.read(), b'e' * 2000)

    def test_zip_from_before_english_names(self):                          # D-239 : un .zip exporte par une version d'avant (`etats/etat_NN.dqs`) s'importe, les etats sont ecrits sous leur nouveau nom
        zip_ = os.path.join(self.t, 'ancien.zip')
        with zipfile.ZipFile(zip_, 'w') as z: z.writestr('data1.dat', valid_logfile(2)); z.writestr('etats/etat_04.dqs', b'h' * 2000); z.writestr('ETATS/ETAT_05.DQS', b'i' * 2000)
        jr, label, pb = S.read_sources([zip_]); self.assertEqual((sorted(jr), sorted(label), pb), (['data1.dat'], ['state_04.dqs', 'state_05.dqs'], []))
        S.import_saves([zip_], self.d.portage, self.d.mobile)
        with open(os.path.join(self.d.savestates, 'state_04.dqs'), 'rb') as f: self.assertEqual(f.read(), b'h' * 2000)
        self.assertFalse(os.path.exists(os.path.join(self.d.savestates, 'etat_04.dqs')))

    def test_phone_manifest_json_is_ignored(self):                          # D-235 : le jeu ne lit pas manifest.json (liste des fichiers + sha256 faite par l'outil de copie) ; les journaux ont leur propre controle
        src = os.path.join(self.t, 'copie_telephone'); write(os.path.join(src, 'data3.dat'), valid_logfile(3)); write(os.path.join(src, 'manifest.json'), b'{"files": {"data3.dat": {"size": 15360, "sha256": "0"}}}')
        jr, label, pb = S.read_sources([src]); self.assertEqual((sorted(jr), label, pb), (['data3.dat'], {}, []))
        nj, n_savestates, copied, pb = S.import_saves([src], self.d.portage, self.d.mobile); self.assertEqual((nj, n_savestates, copied, pb), (1, 0, None, []))
        self.assertFalse(os.path.exists(os.path.join(self.d.portage, 'manifest.json')))

    def test_export_takes_savestates_from_right_folder(self):
        write(os.path.join(self.d.portage, 'data1.dat'), valid_logfile(1)); write(os.path.join(self.d.savestates, 'state_02.dqs'), b'e' * 2000)
        output = os.path.join(self.t, 'sortie.zip'); self.assertEqual(S.export_saves(self.d.portage, self.d.mobile, output), (1, 1))
        with zipfile.ZipFile(output) as z: self.assertEqual(sorted(z.namelist()), ['data1.dat', 'savestates/state_02.dqs'])

    def test_specific_write_folder(self):                            # (tests, --saves-ecriture) : tout reste sous ce dossier
        wdir = os.path.join(self.t, 'autre'); write(os.path.join(wdir, 'data1.dat'), valid_logfile(1))
        zip_ = os.path.join(self.t, 'i.zip')
        with zipfile.ZipFile(zip_, 'w') as z: z.writestr('data1.dat', valid_logfile(2)); z.writestr('savestates/state_03.dqs', b'g' * 2000)
        _, _, copied, _ = S.import_saves([zip_], wdir, self.d.mobile)
        self.assertTrue(os.path.isfile(os.path.join(wdir, 'savestates', 'state_03.dqs'))); self.assertEqual(os.path.dirname(copied), wdir)


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
