"""#198 (audit ENG-02) : ecriture des sauvegardes du moteur : atomique, et une erreur d'E/S ne plante plus le jeu.
Lancer depuis la racine : PYGLET_HEADLESS=1 python3 tests/test_save_writing.py"""
import os, sys, tempfile, types, unittest, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dq4_pc import language as _LANGUAGE; _LANGUAGE.select_language('fr')          # (D-238 : ces tests attendent les textes francais, quelle que soit la langue de l'ordinateur)
from dq4_pc.core import engine as ENGINE


def fake_core(path, data=b'abc'):
    c = object.__new__(ENGINE.GameCore)                                   # sans __init__ : pas de bibliotheque ni d'emulateur pour tester l'ecriture
    c.files = {0x100: {'d': bytearray(data), 'persist': path, 'pos': 0, 'w': True, 'name': 'x'}}
    return c


class Writing(unittest.TestCase):
    def setUp(self): self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d, True)

    def test_normal_write_without_temp_file(self):
        ch = os.path.join(self.d, 'sous', 'data1.dat'); c = fake_core(ch, b'0123456789')
        c.h_fclose(0x100)
        self.assertEqual(open(ch, 'rb').read(), b'0123456789')
        self.assertEqual(os.listdir(os.path.dirname(ch)), ['data1.dat'])          # le .tmp a disparu
        self.assertFalse(c.write_failures)

    def test_replaces_the_old_file(self):
        ch = os.path.join(self.d, 'data1.dat'); open(ch, 'wb').write(b'ancien')
        fake_core(ch, b'nouveau').h_fclose(0x100)
        self.assertEqual(open(ch, 'rb').read(), b'nouveau')

    def test_write_error_keeps_old_file_and_does_not_crash(self):
        ch = os.path.join(self.d, 'data1.dat'); open(ch, 'wb').write(b'ancien')
        c = fake_core(ch, b'nouveau')
        actual = os.replace
        def refused(a, b): raise PermissionError('verrouille par un antivirus')
        os.replace = refused
        try: c.h_fclose(0x100)                                                       # aucune exception
        finally: os.replace = actual
        self.assertEqual(open(ch, 'rb').read(), b'ancien')                           # intact
        self.assertEqual(os.listdir(self.d), ['data1.dat'])                           # pas de .tmp qui traine
        self.assertEqual(len(c.write_failures), 1); self.assertIn('data1.dat', c.write_failures[0]); self.assertIn('antivirus', c.write_failures[0])
        self.assertNotIn(0x100, c.files)                                              # le fichier est ferme quand meme (comme avant)

    def test_second_attempt_succeeds(self):
        ch = os.path.join(self.d, 'data1.dat'); actual = os.replace; n = []
        def once(a, b):
            n.append(1)
            if len(n) == 1: raise PermissionError('verrou passager')
            return actual(a, b)
        os.replace = once
        try: err = ENGINE.GameCore.atomic_write(ch, b'ok', attempts=2, pause=0.0)
        finally: os.replace = actual
        self.assertIsNone(err); self.assertEqual(open(ch, 'rb').read(), b'ok'); self.assertEqual(len(n), 2)

    def test_folder_cannot_be_created(self):
        file = os.path.join(self.d, 'fichier'); open(file, 'wb').close()
        err = ENGINE.GameCore.atomic_write(os.path.join(file, 'data1.dat'), b'x', attempts=1)       # « fichier » n'est pas un dossier
        self.assertIsInstance(err, OSError)


class Window(unittest.TestCase):
    def test_report_in_log_and_message(self):
        try: from dq4_pc.window import game as F
        except Exception as ex: raise unittest.SkipTest('fenetre non importable ici (%r)' % (ex,))
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        os.environ['DQ_JOURNAL_FENETRE'] = os.path.join(d, 'logs', 'window_errors.log')
        self.addCleanup(os.environ.pop, 'DQ_JOURNAL_FENETRE', None)
        toasts = []; j = types.SimpleNamespace(toast=lambda t, duration=1.8: toasts.append((t, duration)))           # (message a l'ecran rendu aux sauvegardes : D-230)
        core = types.SimpleNamespace(write_failures=["data1.dat : PermissionError('x')"])
        F.Game._report_write_failures(j, core)
        self.assertIsNone(core.write_failures)                                       # vide : un seul message par echec
        self.assertEqual(len(toasts), 1); self.assertIn('Sauvegarde impossible', toasts[0][0])
        with open(os.environ['DQ_JOURNAL_FENETRE'], encoding='utf-8') as f: txt = f.read()
        self.assertIn('data1.dat', txt); self.assertIn('save failed', txt)


if __name__ == '__main__': unittest.main(verbosity=1)
