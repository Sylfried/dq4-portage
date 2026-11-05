"""Un seul dossier de sauvegardes (D-232 ; demande de Sylfried du 04/11/2026 à 23 h 55 : « tu ne pourrais juste pas stocker tous les fichiers directement dans le dossier "sauvegardes" ou un seul sous-dossier pour coller
à la logique des états ? Comme ça si je veux transférer toutes les sauvegardes du mobile sur le patch je n'ai pas besoin de faire de gymnastique mentale à deviner quel fichier mettre dans quel dossier »), sans fenêtre ni moteur :

  1. disposition : `data\\saves` reçoit data1.dat à data5.dat, data9.dat ET `savestates\\` (comme le .zip d'export) ; `portage` n'est plus qu'un autre nom de ce dossier ;
  2. reprise des anciens `saves\\portage` et `saves\\mobile\\<date>` au démarrage : les journaux sont COPIÉS dans `saves\\` (le portage d'abord, puis la copie du téléphone la plus récente, sans rien écraser : ce que le jeu lisait
     avant, fichier par fichier), puis les deux anciens dossiers sont DÉPLACÉS tels quels dans `before_tidy_<date>\\` ; rien n'est supprimé, une seconde reprise ne fait rien ;
  3. cas réel de Sylfried : fichiers du portage plus anciens que ceux du téléphone, `manifest.json` dans la copie du téléphone, vieux `dq4_pc\\saves` encore là (ne doit pas passer devant les fichiers d'aujourd'hui) ;
  4. sécurité : un journal déjà posé dans `saves\\` n'est pas écrasé, une erreur de déplacement laisse tout en place (le jeu lit déjà `saves\\`), DQ4_JEUX (copie du téléphone ailleurs) n'est pas touché ;
  5. le moteur lit ce dossier (`effective_files`), l'export le met à plat et l'import y écrit.

    python3 tests/test_saves_in_one_folder.py
"""
import os, shutil, sys, tempfile, unittest, zipfile
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc import language as _LANGUAGE; _LANGUAGE.select_language('fr')          # (D-238 : ces tests attendent les textes francais, quelle que soit la langue de l'ordinateur)
from dq4_pc import paths as CH
from dq4_pc.persistence import saves as S

NAMES = CH.LOGFILE_NAMES


def write(path, content=b'x'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f: f.write(content)
    return path


def content(*p):
    with open(os.path.join(*p), 'rb') as f: return f.read()


def all_files(root):
    return sorted(os.path.relpath(os.path.join(r, f), root) for r, _, fs in os.walk(root) for f in fs)


class Layout(unittest.TestCase):
    def test_a_single_folder(self):
        d = CH.Folders('/projet', env={})
        self.assertEqual(d.portage, d.saves); self.assertEqual(d.savestates, os.path.join(d.saves, 'savestates'))
        self.assertEqual(d.savestates_folder(d.portage), os.path.join(d.saves, 'savestates')); self.assertEqual(d.clones_folder(d.portage), d.saves)

    def test_game_file_names(self):
        self.assertEqual(NAMES, ('data1.dat', 'data2.dat', 'data3.dat', 'data4.dat', 'data5.dat', 'data9.dat')); self.assertEqual(S.NAMES, NAMES)

    def test_no_code_still_stores_in_port(self):
        """Le dossier `portage` n'existe plus que comme ancien nom (paths.py : repris puis range) ; aucun autre module ne le construit."""
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc')
        for folder, _d, files in os.walk(root):
            for f in files:
                if f.endswith('.py') and f != 'paths.py':
                    with open(os.path.join(folder, f), encoding='utf-8') as fh: src = fh.read()
                    self.assertNotIn("'portage'", src, f); self.assertNotIn('sauvegardes\\\\portage', src, f)


class Resume(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='un_dossier_'); self.d = CH.Folders(self.t, env={}); self.sv = self.d.saves

    def tearDown(self): shutil.rmtree(self.t, ignore_errors=True)

    def migrate(self, d=None): return CH.migrate(d or self.d, log=lambda *a: None)

    def sylfried_case(self):
        """Ce que son PC contenait au 04/11/2026 : portage (data1, data5, data9 d'aujourd'hui ; data2 à data4 plus anciens), copie du téléphone plus récente pour data2 à data4, plus un manifeste, et un vieux dq4_pc\\sauvegardes."""
        for name_str in ('data1.dat', 'data5.dat', 'data9.dat'): write(os.path.join(self.d.old_port_dir, name_str), b'portage_' + name_str.encode())
        for name_str in ('data2.dat', 'data3.dat', 'data4.dat'): write(os.path.join(self.d.old_port_dir, name_str), b'portage_vieux_' + name_str.encode())
        phone = os.path.join(self.d.mobile, '20261103_222423')
        for name_str in NAMES: write(os.path.join(phone, name_str), b'tel_' + name_str.encode())
        write(os.path.join(phone, 'manifest.json'), b'{"device": "SM S938B"}'); write(os.path.join(self.d.mobile, '20261007_190735', 'data1.dat'), b'tel_ancien')
        write(os.path.join(self.sv, 'before_import_20261101_192625', 'data2.dat'), b'AV'); write(os.path.join(self.d.savestates, 'state_01.dqs'), b'E1')
        write(os.path.join(self.t, 'dq4_pc', 'sauvegardes', 'data1.dat'), b'tres_vieux'); write(os.path.join(self.t, 'dq4_pc', 'sauvegardes', 'data3.dat'), b'tres_vieux3')

    def test_logfiles_moved_up_into_saves(self):
        self.sylfried_case(); done = self.migrate()
        self.assertTrue(any('anciens dossiers ranges' in ph for ph in done), done)
        for name_str in ('data1.dat', 'data5.dat', 'data9.dat'): self.assertEqual(content(self.sv, name_str), b'portage_' + name_str.encode(), name_str)                  # le portage (ce que le jeu ecrivait) passe devant
        for name_str in ('data2.dat', 'data3.dat', 'data4.dat'): self.assertEqual(content(self.sv, name_str), b'portage_vieux_' + name_str.encode(), name_str)            # ... meme plus ancien : comme avant (aucun choix a la date)
        self.assertEqual(sorted(f for f in os.listdir(self.sv) if f.endswith('.dat')), sorted(NAMES))

    def test_phone_copy_completes_what_is_missing(self):
        write(os.path.join(self.d.old_port_dir, 'data1.dat'), b'portage1')
        for name_str in NAMES: write(os.path.join(self.d.mobile, '20261103_222423', name_str), b'tel_' + name_str.encode())
        write(os.path.join(self.d.mobile, '20261007_190735', 'data3.dat'), b'tel_ancien3'); write(os.path.join(self.d.mobile, '20261007_190735', 'data1.dat'), b'tel_ancien1')
        self.migrate()
        self.assertEqual(content(self.sv, 'data1.dat'), b'portage1'); self.assertEqual(content(self.sv, 'data3.dat'), b'tel_data3.dat')                     # la copie la plus recente, pas une plus ancienne

    def test_old_folders_tidied_as_is_nothing_lost(self):
        self.sylfried_case(); before = set(all_files(self.sv)); self.migrate()
        placement = [x for x in os.listdir(self.sv) if x.startswith('before_tidy_')]; self.assertEqual(len(placement), 1)
        for under in ('portage', 'mobile'): self.assertFalse(os.path.exists(os.path.join(self.sv, under)), under)                                      # plus de portage\ ni de mobile\
        r = os.path.join(self.sv, placement[0])
        self.assertEqual(content(r, 'portage', 'data2.dat'), b'portage_vieux_data2.dat'); self.assertEqual(content(r, 'mobile', '20261103_222423', 'manifest.json'), b'{"device": "SM S938B"}')
        self.assertEqual(content(r, 'mobile', '20261007_190735', 'data1.dat'), b'tel_ancien')
        after = set(all_files(self.sv))
        for f in before:                                                                                                                                # chaque fichier d'avant est la OU on l'a range, avec le meme contenu
            if f.startswith(('portage' + os.sep, 'mobile' + os.sep)): self.assertIn(os.path.join(placement[0], f), after, f)
            else: self.assertIn(f, after, f)
        self.assertEqual(content(self.sv, 'savestates', 'state_01.dqs'), b'E1'); self.assertEqual(content(self.sv, 'before_import_20261101_192625', 'data2.dat'), b'AV')    # etats et copies d'import : a leur place

    def test_a_second_resume_does_nothing(self):
        self.sylfried_case(); self.migrate(); before = all_files(self.t)
        self.assertEqual(self.migrate(), []); self.assertEqual(all_files(self.t), before)

    def test_old_dq4_pc_folder_does_not_outrank_todays_files(self):
        """Il reste chez lui un `dq4_pc\\saves` d'avant le premier rangement (copie, pas deplacement) : ses vieux data1 et data3 ne doivent pas remplacer ceux du portage."""
        self.sylfried_case(); self.migrate()
        self.assertEqual(content(self.sv, 'data1.dat'), b'portage_data1.dat'); self.assertEqual(content(self.sv, 'data3.dat'), b'portage_vieux_data3.dat')
        self.assertEqual(content(self.t, 'dq4_pc', 'sauvegardes', 'data1.dat'), b'tres_vieux')                                                      # (et il n'est pas touche)

    def test_save_file_already_in_saves_is_not_overwritten(self):
        """Il a deja copie les data du telephone dans `saves\\` : ils gagnent ; ceux de l'ancien portage ne sont pas perdus (ranges)."""
        write(os.path.join(self.sv, 'data1.dat'), b'copie_du_telephone'); write(os.path.join(self.d.old_port_dir, 'data1.dat'), b'ancien_portage'); write(os.path.join(self.d.old_port_dir, 'data2.dat'), b'portage2')
        self.migrate()
        self.assertEqual(content(self.sv, 'data1.dat'), b'copie_du_telephone'); self.assertEqual(content(self.sv, 'data2.dat'), b'portage2')
        r = os.path.join(self.sv, [x for x in os.listdir(self.sv) if x.startswith('before_tidy_')][0]); self.assertEqual(content(r, 'portage', 'data1.dat'), b'ancien_portage')

    def test_nothing_to_tidy(self):
        write(os.path.join(self.sv, 'data1.dat'), b'a'); self.assertEqual(self.migrate(), []); self.assertEqual(all_files(self.sv), ['data1.dat'])

    def test_empty_folder_is_tidied_without_copying(self):
        os.makedirs(self.d.old_port_dir); self.migrate()
        self.assertFalse(os.path.exists(self.d.old_port_dir)); self.assertEqual(sorted(f for f in os.listdir(self.sv) if f.endswith('.dat')), [])

    def test_a_move_error_leaves_everything_in_place(self):
        self.sylfried_case()
        actual = os.replace

        def refuse_folders(src, dst):                                    # Windows : un dossier dont un fichier est ouvert ne se deplace pas ; les copies de fichiers (tmp -> destination) passent
            if os.path.isdir(src): raise PermissionError('fichier ouvert')
            return actual(src, dst)
        with mock.patch('dq4_pc.paths.os.replace', side_effect=refuse_folders):
            done = self.migrate()
        self.assertTrue(any('NON ranges' in ph and 'fichier ouvert' in ph for ph in done), done)
        self.assertTrue(os.path.isdir(self.d.old_port_dir) and os.path.isdir(self.d.mobile))                                                            # rien n'a bouge
        self.assertEqual(content(self.sv, 'data1.dat'), b'portage_data1.dat')                                                                           # (le jeu lit deja sauvegardes : copie faite avant le deplacement)
        done = self.migrate()                                                                                                                           # puis la reprise suivante termine
        self.assertTrue(any('anciens dossiers ranges' in ph for ph in done), done); self.assertFalse(os.path.exists(self.d.old_port_dir))

    def test_a_file_that_cannot_be_placed_stops_the_tidy_up(self):
        """Un dossier nomme `data1.dat` occupe la place : le journal du portage n'a pas pu etre copie, donc l'ancien dossier ne bouge pas."""
        write(os.path.join(self.d.old_port_dir, 'data1.dat'), b'portage1'); os.makedirs(os.path.join(self.sv, 'data1.dat'))
        done = self.migrate()
        self.assertTrue(any('NON ranges' in ph and 'data1.dat' in ph for ph in done), done); self.assertTrue(os.path.isfile(os.path.join(self.d.old_port_dir, 'data1.dat')))

    def test_dq4_games_phone_copy_is_not_touched(self):
        games = os.path.join(self.t, 'ailleurs', 'DQ4'); d = CH.Folders(self.t, env={'DQ4_GAMES': games})
        for name_str in NAMES: write(os.path.join(games, 'saves', '20261007_190735', name_str), b'tel_' + name_str.encode())
        write(os.path.join(d.saves, 'portage', 'data1.dat'), b'p')
        self.assertEqual(CH.migrate(d, log=lambda *a: None), [])
        self.assertTrue(os.path.isfile(os.path.join(games, 'saves', '20261007_190735', 'data1.dat'))); self.assertTrue(os.path.isfile(os.path.join(d.saves, 'portage', 'data1.dat')))
        self.assertTrue(d.recent_mobile_save().endswith('20261007_190735'))                                                                      # (le jeu la lit toujours en second)


class WithEngineAndZips(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='un_dossier_zip_'); self.d = CH.Folders(self.t, env={}); self.before = CH.FOLDERS; CH.FOLDERS = self.d

    def tearDown(self): CH.FOLDERS = self.before; shutil.rmtree(self.t, ignore_errors=True)

    def test_copying_phone_files_is_enough(self):
        """Le geste voulu : les data1.dat... du telephone dans `saves\\`, rien d'autre ; le moteur les lit (dossier d'ecriture d'abord) et l'export les range a plat avec les etats."""
        for name_str in NAMES: write(os.path.join(self.d.saves, name_str), b'tel_' + name_str.encode())
        write(os.path.join(self.d.savestates, 'state_01.dqs'), b'e' * 2000)
        self.assertEqual(sorted(S.effective_files(self.d.portage, None)), sorted(NAMES))
        output = os.path.join(self.t, 'sortie.zip'); self.assertEqual(S.export_saves(self.d.portage, None, output), (6, 1))
        with zipfile.ZipFile(output) as z: self.assertEqual(sorted(z.namelist()), sorted(NAMES + ('savestates/state_01.dqs',)))

    def test_folder_content_is_that_of_zip(self):
        """Ce que l'export met dans le .zip est ce que le dossier contient (a part les copies de securite) : le dossier se copie d'un PC a l'autre comme le .zip se decompresse."""
        for name_str in NAMES: write(os.path.join(self.d.saves, name_str), b'j' + name_str.encode())
        write(os.path.join(self.d.savestates, 'state_02.dqs'), b'e' * 2000); write(os.path.join(self.d.saves, 'before_import_20261101_101010', 'data1.dat'), b'AV')
        output = os.path.join(self.t, 'sortie.zip'); S.export_saves(self.d.portage, None, output)
        with zipfile.ZipFile(output) as z: in_zip = sorted(z.namelist())
        folder = sorted(f.replace(os.sep, '/') for f in all_files(self.d.saves) if not f.startswith('before_'))
        self.assertEqual(in_zip, folder)


if __name__ == '__main__':
    unittest.main(verbosity=1)
