"""Langue de l'outil, lot « fenetre » (D-238) : messages de la console et de la fenetre du jeu, demarrage, ligne de commande (`--help`), reprise des dossiers, sauvegardes, son, moteur.
Sans fenetre ni APK (faux Jeu, fausse fenetre pyglet) : chaque scenario est joue en francais (le texte d'avant, mot pour mot) puis en anglais (plus un mot de francais : `french()` de test_language).

  1. couverture (lecture du code) : chaque texte passe a tr() / N_() dans le perimetre a sa traduction anglaise, aucune cle du catalogue n'est orpheline, rien n'est traduit a l'import, les textes passes a `_wait`,
     `_log_window`, `_note_once` sont marques N_, et AUCUN message de console n'est reste en francais sans tr() (liste blanche des traces de debogage, chacune justifiee) ;
  2. ligne de commande : l'aide `--help` (analyseur et processus complet) dans les deux langues, la langue reglee AVANT la migration et l'analyseur (reglages.json par defaut ou donne par --reglages), messages de
     demarrage (APK introuvables, migration impossible) ;
  3. reprise des dossiers (chemins.migrer), export / import de sauvegardes, etats, journaux : les raisons montrees au joueur ;
  4. fenetre : messages de Jeu (echecs d'etats et de sauvegarde, memoire du moteur, reglages manques, chargement), bascule plein ecran <-> fenetre (console et journal des erreurs), ligne de journal de la fenetre,
     moniteurs, taille ; son ; alertes de version du moteur (`Engine._record_missing`) ; preparation du cache (processus a part, langue transmise).

    python3 tests/test_window_language.py"""
import ast, contextlib, glob, io, json, os, re, shutil, subprocess, sys, tempfile, types, unittest, warnings, zipfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import _paths
import test_language as TL
from dq4_pc import paths as CH
from dq4_pc import language as LG
from dq4_pc.persistence import savestates as SS, logfile_format as FJ, saves as SA

french = TL.french


def catalog(names=('window', 'divers')):
    import importlib
    c = {}
    for name_str in names: c.update(importlib.import_module('dq4_pc.texts_en.' + name_str).EN)
    return c


OWN_CATALOG = catalog()                                                    # les entrees de ce lot (window.py, divers.py)
CATALOG = catalog(('pause', 'menus', 'window', 'divers'))                    # tout le catalogue : un meme texte n'a qu'une entree, dans le fichier du premier lot qui l'a ecrit (test_language.py : pas de doublon)
FOLDER = os.path.join(ROOT, 'dq4_pc')
WINDOW_FILES = [os.path.join('dq4_pc', 'window', f) for f in ('game.py', 'full_screen.py', 'field.py', 'keyboard_mouse.py', 'camera.py', 'options.py', 'helpers.py', 'battle_scene.py', 'snapshots.py')]
PERIMETRE = (['dq4_pc/main.py', 'dq4_pc/paths.py', 'dq4_pc/sound.py', 'dq4_pc/core/engine.py'] + WINDOW_FILES
             + ['dq4_pc/persistence/' + f for f in ('write_dir.py', 'savestates.py', 'saves.py', 'logfile_format.py', 'settings.py')]
             + sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(FOLDER, 'world', '*.py')) + glob.glob(os.path.join(FOLDER, 'render', '*.py'))))


def tree(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f: return ast.parse(f.read())


def call_name(n):
    return getattr(n.func, 'id', None) or getattr(n.func, 'attr', None)


def litteraux(path, names=('tr', 'N_')):
    """[(ligne, texte)] des textes litteraux passes a tr() / N_() (LG.tr compris)."""
    return [(n.lineno, n.args[0].value) for n in ast.walk(tree(path)) if isinstance(n, ast.Call) and call_name(n) in names and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)]


@contextlib.contextmanager
def entry(code):
    """Joue ce qui suit dans la langue `code` ('fr' ou 'en')."""
    LG.select_language(code)
    try: yield
    finally: LG.select_language('fr')


def output(f, *a, **k):
    """-> (resultat, texte imprime) de f(*a, **k)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): r = f(*a, **k)
    return r, buf.getvalue()


def without_paths(t):
    """Le texte sans les chemins (dossiers temporaires) : ce ne sont pas des mots."""
    return re.sub(r'(?:[A-Za-z]:)?[\\/][^\s\'")]+', ' ', t)


def write(path, content=b'x'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f: f.write(content)
    return path


# ======================================================================================================================================================
class Couverture(unittest.TestCase):
    """Lecture du code : rien ne manque, rien ne traine."""
    def test_each_code_text_has_its_translation(self):
        missing_items = []; identiques = []
        for p in PERIMETRE:
            for line, t in litteraux(p):
                if t not in CATALOG:
                    if french(t): missing_items.append('%s:%d %r' % (p, line, t))                                  # (« Casino », « Normal », « Menu »... : identiques en anglais, sans entree)
                elif CATALOG[t] == t: identiques.append('%s:%d %r' % (p, line, t))
        self.assertEqual(missing_items, [], 'textes passes a tr() / N_() sans traduction (window.py, divers.py)')
        self.assertEqual(identiques, [], 'traduction identique au francais')

    def test_no_orphan_key(self):
        """Chaque entree de window.py et divers.py sert dans le code (un texte change ou retire dans le code ne laisse pas sa traduction derriere lui)."""
        utilisees = set()
        for d, _, fs in os.walk(FOLDER):
            for f in fs:
                if f.endswith('.py') and '__pycache__' not in d: utilisees.update(t for _, t in litteraux(os.path.relpath(os.path.join(d, f), ROOT)))
        self.assertEqual(sorted(k for k in OWN_CATALOG if k not in utilisees), [])

    def test_nothing_is_translated_at_import(self):
        """`tr(...)` ne s'execute que dans une fonction (la langue change en cours de partie) ; une constante de module est marquee N_ et traduite a l'affichage."""
        fautifs = []
        for p in PERIMETRE:
            a = tree(p); parents = {id(c): n for n in ast.walk(a) for c in ast.iter_child_nodes(n)}
            for n in ast.walk(a):
                if isinstance(n, ast.Call) and call_name(n) == 'tr':
                    x = n
                    while id(x) in parents and not isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)): x = parents[id(x)]
                    if not isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)): fautifs.append('%s:%d' % (p, n.lineno))
        self.assertEqual(fautifs, [])

    def test_texts_passed_to_a_translating_function_are_marked(self):
        """`_wait(text)`, `_log_window(when)` et `_note_once(lookup_key, e)` traduisent leur argument : le texte litteral doit etre passe a N_(), sinon le test de couverture ne le voit pas."""
        nus = []
        for p in PERIMETRE:
            for n in ast.walk(tree(p)):
                if isinstance(n, ast.Call) and call_name(n) in ('_attente', '_journal_fenetre', '_une_fois') and n.args and isinstance(n.args[0], ast.Constant):
                    if isinstance(n.func, ast.Attribute): nus.append('%s:%d %r' % (p, n.lineno, n.args[0].value))
        self.assertEqual(nus, [])

    def test_tr_n_and_lg_are_imported_where_used(self):
        """Un `tr(...)` ajoute dans un module qui ne l'importe pas ne plante qu'au moment du message (souvent une erreur rare : echec de bascule, son coupe...) : on le voit ici, a la lecture du code."""
        unlinked = []
        for p in PERIMETRE:
            a = tree(p); lies = set()
            for n in ast.walk(a):
                if isinstance(n, (ast.Import, ast.ImportFrom)): lies.update((x.asname or x.name).split('.')[0] for x in n.names)
                elif isinstance(n, (ast.FunctionDef, ast.ClassDef)): lies.add(n.name)
                elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store): lies.add(n.id)
                elif isinstance(n, ast.arg): lies.add(n.arg)
            unlinked += ['%s:%d %s' % (p, n.lineno, n.id) for n in ast.walk(a) if isinstance(n, ast.Name) and n.id in ('tr', 'N_', 'LG') and isinstance(n.ctx, ast.Load) and n.id not in lies]
        self.assertEqual(unlinked, [])

    # liste blanche : (fichier, debut du texte) des messages de console que le joueur ne voit pas (traces des options de test et des variables DQ_*, journal interne du moteur)
    DEBUG = (
        ('sound.py', 'Son : image '),                                    # DQ_SON : ordres du moteur
        ('engine.py', 'fopen '), ('engine.py', 'MSGDBG '), ('engine.py', 'ENVOI '), ('engine.py', 'MSG image '), ('engine.py', 'FBX image '),          # DQ_SAVEDBG, DQ_MSGDBG, DQ_MENUDBG, DQ_FBXLOG
        ('camera.py', 'PROJ n='), ('camera.py', 'CAMV n='), ('camera.py', '   sprites'),                                                              # DQ_PROJ, DQ_CAMV
        ('keyboard_mouse.py', 'FRONT discussion'),
        ('game.py', 'SPRITES'), ('game.py', 'n=%d p='), ('game.py', 'FLAG n='), ('game.py', 'ETAT n='), ('game.py', 'combat'), ('game.py', 'capture :'),     # DQ_SPR, DQ_DEBUG, --shot, --shots-combat
        ('game.py', 'OPTION %s'), ('game.py', 'PAS moteur='),                                                                                          # --options-test, DQ_PAS
        ('full_screen.py', 'pyglet %s, Python'),                       # versions des logiciels dans le journal d'une bascule ratee : des noms propres
        ('field.py', 'decors_plats :'),                                # nom du module + exception : un identifiant, pas une phrase
        ('fld.py', 'nobj'),                                            # outil en ligne de commande de lecture des FLD
        ('savestates.py', 'etat : fichier ouvert non restaure'),            # journal du moteur d'origine (Silencieux), pas la console
    )

    def test_no_console_message_left_in_french_without_tr(self):
        """Un `print(...)` / `log(...)` / `toast(...)` dont le texte est un litteral (ou un litteral formate) doit passer par tr() ; sinon il est dans la liste blanche DEBUG. emu_core.py (journal de l'emulateur,
        outil de developpement) n'est pas balaye."""
        names = {'print', 'log', '_manque', 'toast', '_noter', '_echec', 'add_note', 'noter_erreur'}
        nus = []; seen = set()
        for p in PERIMETRE:
            for n in ast.walk(tree(p)):
                if not isinstance(n, ast.Call) or not n.args: continue
                name_str = call_name(n)
                if name_str == 'append' and not (isinstance(n.func.value, ast.Name) and n.func.value.id in ('done', 'pb', 'state')): continue
                if name_str not in names and name_str != 'append': continue
                a = n.args[0]
                while isinstance(a, ast.BinOp): a = a.left                             # 'texte %s' % x, 'debut' + x
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and len(a.value) > 1:
                    base = os.path.basename(p); ok = [d for d in self.DEBUG if d[0] == base and a.value.startswith(d[1])]
                    if ok: seen.add(ok[0])
                    else: nus.append('%s:%d %r' % (p, n.lineno, a.value[:80]))
        self.assertEqual(nus, [], 'messages de console en francais sans tr()')
        self.assertEqual([d for d in self.DEBUG if d not in seen], [], 'entree de la liste blanche qui ne correspond plus a rien')


# ======================================================================================================================================================
try:
    from dq4_pc import main as P
except Exception as _ex:
    P = None; _ERROR_P = _ex


@unittest.skipIf(P is None, 'principal non importable ici')
class CommandLine(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='lang_cmd_'); self.d = CH.Folders(self.t, env={}); self.before = (CH.FOLDERS, CH.migrate)

    def tearDown(self): CH.FOLDERS, CH.migrate = self.before; LG.select_language('fr'); shutil.rmtree(self.t, ignore_errors=True)

    def settings(self, language, path=None):
        path = path or self.d.settings; os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f: json.dump({'langue': language}, f)
        return path

    def helpers(self):
        """{option: texte d'aide} de l'analyseur construit dans la langue courante."""
        return {a.option_strings[0]: a.help for a in P.build_parser(self.d)._actions if a.help and a.option_strings[0] != '-h'}

    def test_help_text_is_in_the_chosen_language(self):
        with entry('fr'): fr = self.helpers()
        with entry('en'): ang = self.helpers()
        self.assertEqual(sorted(fr), sorted(ang)); self.assertGreaterEqual(len(fr), 33)
        self.assertEqual(fr['--apk'], 'dossier des 3 APK (version francaise) ; par defaut data\\apk')                              # le francais d'avant, mot pour mot
        self.assertEqual(fr['--sans-son'], 'coupe le son pour cette session (le menu Echap permet de le remettre)')
        self.assertEqual(ang['--apk'], 'folder of the 3 game APK files; default data\\apk')
        for option in fr:
            self.assertNotEqual(ang[option], fr[option], option)
            self.assertFalse(french(ang[option]), '%s : %r' % (option, ang[option]))
            self.assertNotIn('%', ang[option].replace('%%', ''), option)                  # (argparse formate l'aide avec % : un pourcentage nu la casserait)
        self.assertEqual(sorted(o for o in fr if fr[o].startswith('(test) ')), sorted(o for o in ang if ang[o].startswith('(test) ')))          # les options de test restent annoncees comme telles

    def test_format_help_does_not_crash_in_both_languages(self):
        for code in ('fr', 'en'):
            with entry(code): text = P.build_parser(self.d).format_help()
            self.assertIn('--saves-ecriture', text); self.assertIn('usage: dq4_pc', text)

    def test_settings_file_from_command_line(self):
        self.assertEqual(P.settings_file(['--slot', '2'], self.d), self.d.settings)
        self.assertEqual(P.settings_file(['--reglages', 'a.json', '--slot', '2'], self.d), 'a.json')
        self.assertEqual(P.settings_file(['--slot', '2', '--reglages=b.json'], self.d), 'b.json')
        self.assertEqual(P.settings_file(['--reglages'], self.d), self.d.settings)                  # valeur manquante : c'est l'analyseur qui s'en plaindra

    def test_language_comes_from_setting_not_computer(self):
        self.settings('en'); self.assertEqual(P.set_language([], self.d), 'en')
        self.settings('fr'); self.assertEqual(P.set_language([], self.d), 'fr')
        other = self.settings('en', os.path.join(self.t, 'autre', 'settings.json'))
        self.assertEqual(P.set_language(['--reglages', other], self.d), 'en')                           # --reglages l'emporte sur le fichier par defaut ('fr')
        os.remove(self.d.settings); self.assertEqual(P.set_language([], self.d), LG.select_language('systeme'))     # pas de fichier : la langue de l'ordinateur

    def main(self, argv):
        """main(argv) sans migration reelle ni fenetre : -> (langues vues par migrer, texte imprime, code de sortie)."""
        CH.FOLDERS = self.d; views = []; CH.migrate = lambda d=None, log=print: views.append(LG.current_language()) or []
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit) as cm: P.main(argv)
        return views, buf.getvalue(), cm.exception.code

    def main_text(self, argv):
        CH.FOLDERS = self.d; CH.migrate = lambda d=None, log=print: []
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit) as cm: P.main(argv)
        return buf.getvalue(), cm.exception.code

    def test_apks_not_found_in_french_and_english(self):
        empty = os.path.join(self.t, 'vide'); os.makedirs(empty)
        self.settings('fr'); text, code = self.main_text(['--apk', empty]); self.assertEqual(code, 1)
        self.assertEqual(text, 'Jeu : APK dans %s\n\nLes APK francais sont introuvables.\nMets base.apk, split_config.arm64_v8a.apk et split_UnityDataAssetPack.apk dans :\n   %s\n(et, si tu en as une, les fichiers data1.dat... de ta sauvegarde du telephone dans %s). Autre dossier : set DQ4_DATA=chemin\\vers\\data\n'
                         % (empty, os.path.normpath(empty), self.d.saves))
        self.settings('en'); text, code = self.main_text(['--apk', empty]); self.assertEqual(code, 1)
        self.assertEqual(text, 'Game: APK files in %s\n\nThe game APK files were not found.\nPut base.apk, split_config.arm64_v8a.apk and split_UnityDataAssetPack.apk in:\n   %s\n(and, if you have one, the data1.dat... files of your phone save in %s). Other folder: set DQ4_DATA=path\\to\\data\n'
                         % (empty, os.path.normpath(empty), self.d.saves))
        self.assertFalse(french(without_paths(text)), text)

    def test_language_is_set_before_migration(self):
        """Les messages de la migration (chemins.migrer) sont dans la langue du reglage : reglages.json par defaut, ou celui de --reglages ; et la langue ne depend pas de celle de l'ordinateur."""
        empty = os.path.join(self.t, 'vide'); os.makedirs(empty)
        self.settings('en'); views, _, _ = self.main(['--apk', empty]); self.assertEqual(views, ['en'])
        self.settings('fr'); views, _, _ = self.main(['--apk', empty]); self.assertEqual(views, ['fr'])
        other = self.settings('en', os.path.join(self.t, 'autre.json')); views, text, _ = self.main(['--apk', empty, '--reglages', other])
        self.assertEqual(views, ['en']); self.assertIn('The game APK files were not found.', text)

    def test_migration_impossible(self):
        CH.FOLDERS = self.d
        def breaks(d=None, log=print): raise RuntimeError('boum')
        CH.migrate = breaks
        for code, att in (('fr', "Migration des fichiers impossible (RuntimeError('boum')) : le jeu continue avec les dossiers actuels."),
                          ('en', "File migration failed (RuntimeError('boum')): the game continues with the current folders.")):
            self.settings(code)
            with self.assertRaises(SystemExit): _, text = output(P.main, ['--apk', os.path.join(self.t, 'vide')])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit): P.main(['--apk', os.path.join(self.t, 'vide')])
            self.assertEqual(buf.getvalue().splitlines()[0], att)

    def launch(self, *args, env=None):
        e = dict(os.environ, DQ4_DATA=os.path.join(self.t, 'data'), PYTHONDONTWRITEBYTECODE='1', PYGLET_HEADLESS='1', PYGLET_AUDIO='silent'); e.update(env or {})
        return subprocess.run([sys.executable, '-m', 'dq4_pc', *args], cwd=ROOT, env=e, capture_output=True, text=True, timeout=180)

    def test_python_m_dq4_pc_help_in_both_languages(self):
        """Le vrai processus : `--help` ne ouvre rien, lit la langue dans le fichier de --reglages et imprime l'aide dans cette langue (les noms d'options restent les vrais)."""
        for code in ('fr', 'en'):
            r = self.launch('--reglages', self.settings(code, os.path.join(self.t, code + '.json')), '--help')
            if r.returncode != 0 and 'ModuleNotFoundError' in r.stderr: self.skipTest('dependances absentes : ' + r.stderr.strip().splitlines()[-1])
            self.assertEqual(r.returncode, 0, r.stderr); self.assertEqual(r.stderr, '')
            if code == 'fr': self.assertIn('dossier des 3 APK (version francaise)', r.stdout)
            else:
                self.assertIn('folder of the 3 game APK files', r.stdout)
                text = re.sub(r'--[\w-]+|\{[^}]*\}|\b[A-Z][A-Z_]{2,}\b', ' ', r.stdout)                  # sans les noms d'options, leurs valeurs et les listes de choix
                self.assertFalse(french(text), [m for m in re.findall(r"[a-zA-Z']+", text.lower().replace("'", ' ')) if m in TL.FRENCH_WORDS])


# ======================================================================================================================================================
class Resume(unittest.TestCase):
    """chemins.migrer : les phrases de la reprise de l'ancienne disposition."""
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='lang_migr_'); self.d = CH.Folders(self.t, env={}); r = self.t
        write(os.path.join(r, 'jeux', 'DQ4', 'patched_apks', 'base.apk'), b'APK1')
        write(os.path.join(r, 'jeux', 'DQ4', 'saves', '20261103_222423', 'data1.dat'), b'T1')
        write(os.path.join(r, 'dq4_pc', 'cache', 'carte10_a.pkl'), b'CACHE')
        write(os.path.join(r, 'dq4_pc', 'sauvegardes', 'data1.dat'), b'P1'); write(os.path.join(r, 'dq4_pc', 'sauvegardes', 'etats', 'etat_01.dqs'), b'E1')
        write(os.path.join(r, 'dq4_pc', 'reglages.json'), b'{"a": 1}'); write(os.path.join(r, 'dq4_pc', 'erreurs_fenetre.log'), b'LOG')
        write(os.path.join(self.d.old_port_dir, 'data2.dat'), b'portage2'); write(os.path.join(self.d.mobile, '20261103_222423', 'data3.dat'), b'tel3')

    def tearDown(self): LG.select_language('fr'); shutil.rmtree(self.t, ignore_errors=True)

    def migrate(self):
        lines = []; done = CH.migrate(self.d, log=lines.append); return done, lines

    def test_in_french_text_is_as_before(self):
        with entry('fr'): done, lines = self.migrate()
        for ph in ('cache deplace : dq4_pc\\cache -> data\\cache', '1 fichier(s) APK copie(s) : jeux\\DQ4\\patched_apks -> data\\apk',
                   '1 fichier(s) de reglages copie(s) : dq4_pc -> data\\settings', 'journal des erreurs copie : data\\logs'):
            self.assertIn(ph, done)
        self.assertTrue(any(ph.startswith('anciens dossiers ranges : sauvegardes\\mobile, sauvegardes\\portage') or ph.startswith('anciens dossiers ranges : ') for ph in done), done)
        self.assertEqual(lines, ['Migration : ' + ph for ph in done])

    def test_in_english_no_french_word_left(self):
        with entry('en'): done, lines = self.migrate()
        self.assertIn('cache moved: dq4_pc\\cache -> data\\cache', done); self.assertIn('1 APK file(s) copied: jeux\\DQ4\\patched_apks -> data\\apk', done)
        self.assertIn('1 settings file(s) copied: dq4_pc -> data\\settings', done); self.assertIn('error log copied: data\\logs', done)
        self.assertGreaterEqual(len(done), 6); self.assertEqual(lines, ['Migration: ' + ph for ph in done])
        for ph in lines: self.assertFalse(french(ph), ph)

    def test_tidy_up_impossible(self):
        """Un dossier nomme data1.dat occupe la place : l'ancien dossier ne bouge pas, et la phrase le dit (avec la raison)."""
        write(os.path.join(self.d.old_port_dir, 'data1.dat'), b'portage1'); os.makedirs(os.path.join(self.d.saves, 'data1.dat'))
        with entry('fr'): done, _ = self.migrate()
        self.assertTrue(any(ph.startswith('anciens dossiers de sauvegardes NON ranges (') and 'data1.dat' in ph and ph.endswith(') : ils restent en place') for ph in done), done)
        shutil.rmtree(self.t); self.setUp(); write(os.path.join(self.d.old_port_dir, 'data1.dat'), b'portage1'); os.makedirs(os.path.join(self.d.saves, 'data1.dat'))
        with entry('en'): done, _ = self.migrate()
        phrase = [ph for ph in done if ph.startswith('old save folders NOT moved (')]
        self.assertEqual(len(phrase), 1, done); self.assertTrue(phrase[0].endswith('): they stay in place')); self.assertFalse(french(without_paths(phrase[0])), phrase[0])

    def test_migration_only_process_takes_language_from_setting(self):
        """`python -m dq4_pc.paths` (lance par launch_dq4.bat avant le jeu) lit la langue dans reglages.json avant de migrer."""
        import runpy
        data = os.path.join(self.t, 'new_data'); rg = os.path.join(data, 'settings', 'settings.json'); os.makedirs(os.path.dirname(rg))
        with open(rg, 'w', encoding='utf-8') as f: json.dump({'langue': 'en'}, f)
        with mock.patch.dict(os.environ, {'DQ4_DATA': data}), mock.patch('os.replace'), mock.patch('shutil.copy2'), mock.patch('shutil.copyfile'):
            LG.select_language('fr')
            with warnings.catch_warnings(): warnings.simplefilter('ignore'); output(runpy.run_module, 'dq4_pc.paths', run_name='__main__')
        self.assertEqual(LG.current_language(), 'en')


# ======================================================================================================================================================
def logfile(n):
    """Un journal valide de 15 360 octets (comme test_saves_import)."""
    import struct
    plain = bytearray(FJ.LOGFILE_SIZE); struct.pack_into('<II', plain, 0, FJ.MAGIE1, FJ.MAGIE2); plain[200] = n % 256
    struct.pack_into('<I', plain, 8, FJ.checksum(bytes(plain)))
    return FJ.decrypt(bytes(plain))


class Persistence(unittest.TestCase):
    """Les raisons montrees au joueur : export / import des sauvegardes, journaux, etats."""
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='lang_pers_'); self.d = CH.Folders(self.t, env={}); self.before = CH.FOLDERS; CH.FOLDERS = self.d
        self.wdir = self.d.portage; self.zip = os.path.join(self.t, 'i.zip')

    def tearDown(self): CH.FOLDERS = self.before; LG.select_language('fr'); shutil.rmtree(self.t, ignore_errors=True)

    def make_zip(self, **files):
        with zipfile.ZipFile(self.zip, 'w') as z:
            for name_str, d in files.items(): z.writestr(name_str.replace('__', '/'), d)

    def error(self, f, *a):
        with self.assertRaises((ValueError, Exception)) as cm: f(*a)
        return str(cm.exception)

    def test_nothing_to_export(self):
        with entry('fr'): m = self.error(SA.export_saves, self.wdir, self.d.mobile, os.path.join(self.t, 'x.zip'))
        self.assertEqual(m, 'Aucune sauvegarde a exporter (ni journal, ni etat instantane).')
        with entry('en'): m = self.error(SA.export_saves, self.wdir, self.d.mobile, os.path.join(self.t, 'x.zip'))
        self.assertEqual(m, 'Nothing to export (no adventure log, no save state).')

    def problemes(self):
        """Un import qui ecarte un journal trop court, un abime, un qui n'en est pas un, un etat trop petit et un faux .zip, mais qui garde un bon journal."""
        bad = bytearray(logfile(3)); bad[100] ^= 1
        fake_zip = write(os.path.join(self.t, 'broken.zip'), b'ceci n est pas un zip')
        self.make_zip(**{'data1.dat': logfile(2), 'data2.dat': bytes(bad), 'data3.dat': bytes(FJ.LOGFILE_SIZE), 'data4.dat': b'court', 'savestates__state_01.dqs': b'petit'})
        return SA.import_saves([self.zip, fake_zip], self.wdir, self.d.mobile)

    def test_import_problems_in_french(self):
        with entry('fr'): nj, n_savestates, copied, pb = self.problemes()
        self.assertEqual((nj, n_savestates), (1, 0))
        txt = '\n'.join(pb)
        for att in ('data4.dat : taille 5 au lieu de 15360 (i.zip)', 'data2.dat : fichier abime (somme de controle incorrecte) (i.zip)', "data3.dat : ce n'est pas un journal du jeu (en-tete inconnu) (i.zip)",
                    'state_01.dqs : fichier trop petit (i.zip)', "broken.zip : ce n'est pas un .zip valide"):
            self.assertIn(att, pb)
        self.assertEqual(len(pb), 5, txt)

    def test_import_problems_in_english(self):
        with entry('en'): nj, n_savestates, copied, pb = self.problemes()
        self.assertEqual((nj, n_savestates), (1, 0))
        for att in ('data4.dat: size 5 instead of 15360 (i.zip)', 'data2.dat: damaged file (checksum mismatch) (i.zip)', 'data3.dat: not a game adventure log (unknown header) (i.zip)',
                    'state_01.dqs: file too small (i.zip)', 'broken.zip: not a valid .zip file'):
            self.assertIn(att, pb)
        for p in pb: self.assertFalse(french(p), p)

    def test_no_file_recognized(self):
        self.make_zip(**{'lisez_moi.txt': b'x'})
        with entry('fr'): m = self.error(SA.import_saves, [self.zip], self.wdir, self.d.mobile)
        self.assertEqual(m, 'Aucun fichier de sauvegarde reconnu (data1.dat a data5.dat, data9.dat ou savestates/state_NN.dqs attendus).')
        with entry('en'): m = self.error(SA.import_saves, [self.zip], self.wdir, self.d.mobile)
        self.assertEqual(m, 'No save file recognized (expected data1.dat to data5.dat, data9.dat or savestates/state_NN.dqs).')

    def test_write_not_possible(self):
        self.make_zip(**{'data1.dat': logfile(2)})
        for code, begin, end in (('fr', 'Aucun fichier n\'a pu etre ecrit (data1.dat : ecriture impossible (', ') ; le fichier actuel est inchange).'),
                                 ('en', 'No file could be written (data1.dat: could not be written (', '); the current file is unchanged).')):
            with entry(code), mock.patch.object(SA, 'atomic_write', return_value=OSError('verrouille')):
                m = self.error(SA.import_saves, [self.zip], self.wdir, self.d.mobile)
            self.assertTrue(m.startswith(begin) and m.endswith(end) and 'verrouille' in m, m)
        self.assertFalse(french(m.replace('verrouille', '')), m)

    def test_verify_savefile(self):
        fake = FJ.decrypt(bytes(FJ.LOGFILE_SIZE)); damaged = bytearray(logfile(1)); damaged[50] ^= 1
        with entry('fr'):
            self.assertEqual(FJ.check('data1.dat', fake), "ce n'est pas un journal du jeu (en-tete inconnu)"); self.assertEqual(FJ.check('data1.dat', bytes(damaged)), 'fichier abime (somme de controle incorrecte)')
        with entry('en'):
            self.assertEqual(FJ.check('data1.dat', fake), 'not a game adventure log (unknown header)'); self.assertEqual(FJ.check('data1.dat', bytes(damaged)), 'damaged file (checksum mismatch)')
            self.assertIsNone(FJ.check('data1.dat', logfile(1)))

    def test_savestates_refused(self):
        import pickle
        trap = pickle.dumps(os.getcwd, protocol=4)
        fake_engine = types.SimpleNamespace(core=types.SimpleNamespace(uc=None, elf=types.SimpleNamespace(img=b'abc')))
        f = write(os.path.join(self.t, 'pas_un_etat.dqs'), b'DQ4ETATX' + bytes(100))
        attendus = {'fr': ("fichier d'état refusé : il demande « os.getcwd »", "etat d'une autre version (99)",
                           'etat enregistre avec une autre version de la bibliotheque du moteur (APK different) : il ne peut pas etre charge', "ce n'est pas un etat du portage"),
                    'en': ('state file refused: it asks for "posix.getcwd"', 'state from another version (99)',
                           'state saved with another version of the engine library (different APK): it cannot be loaded', 'this is not a state file of this port')}
        for code in ('fr', 'en'):
            with entry(code):
                m1 = self.error(SS._load, trap); m2 = self.error(SS.apply, fake_engine, {'version': 99})
                m3 = self.error(SS.apply, fake_engine, {'version': SS.VERSION, 'lib_sha': 'pas_la_bonne'}); m4 = self.error(SS.read, f)
            self.assertTrue(m1.startswith(attendus[code][0].replace('posix', 'nt') if os.name == 'nt' else attendus[code][0].replace('os.getcwd', 'posix.getcwd') if code == 'fr' else attendus[code][0]), (code, m1))
            self.assertEqual((m2, m3, m4), attendus[code][1:])
            if code == 'en': self.assertFalse(french(m1) or french(m2) or french(m3) or french(m4), (m1, m2, m3, m4))

    def test_file_dialog_boxes(self):
        """Les types de fichiers des boites « Enregistrer sous » / « Ouvrir » (tkinter, remplace ici par un faux)."""
        seen = {}
        fake_fd = types.ModuleType('tkinter.filedialog')
        fake_fd.asksaveasfilename = lambda **kw: seen.setdefault('enregistrer', kw['filetypes']) and ''
        fake_fd.askopenfilenames = lambda **kw: seen.setdefault('ouvrir', kw['filetypes']) and ()
        class Tk:
            def withdraw(self): pass
            def attributes(self, *a): pass
            def destroy(self): pass
        fake_tk = types.ModuleType('tkinter'); fake_tk.Tk = Tk; fake_tk.filedialog = fake_fd
        attendus = {'fr': {'enregistrer': [('Archive zip', '*.zip')], 'ouvrir': [('Sauvegardes (zip, data*.dat, state_*.dqs)', '*.zip *.dat *.dqs'), ('Tous les fichiers', '*.*')]},
                    'en': {'enregistrer': [('Zip archive', '*.zip')], 'ouvrir': [('Saves (zip, data*.dat, state_*.dqs)', '*.zip *.dat *.dqs'), ('All files', '*.*')]}}
        import time
        for code in ('fr', 'en'):
            seen.clear()
            with entry(code), mock.patch.dict(sys.modules, {'tkinter': fake_tk, 'tkinter.filedialog': fake_fd}):
                for mode in ('enregistrer', 'ouvrir'):
                    dlg = SA.Dialogue(mode, 'titre'); t0 = time.time()
                    while dlg.result is None and time.time() - t0 < 5: time.sleep(0.01)
                    self.assertEqual(dlg.result, [], dlg.error)
            self.assertEqual(seen, attendus[code])


# ======================================================================================================================================================
try:
    from dq4_pc.window import game as WND, helpers as AI, snapshots as INS
    import test_window_mode as TM
except Exception as _ex:
    WND = None


@unittest.skipIf(WND is None, 'fenetre non importable ici')
class Window(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='lang_fen_'); self.addCleanup(shutil.rmtree, self.t, True); self.addCleanup(LG.select_language, 'fr')
        self.log = os.environ['DQ_JOURNAL_FENETRE'] = os.path.join(self.t, 'logs', 'window_errors.log'); self.addCleanup(os.environ.pop, 'DQ_JOURNAL_FENETRE', None)
        os.environ.pop('DQ_SIM_ECHEC', None); self.addCleanup(os.environ.pop, 'DQ_SIM_ECHEC', None)

    def logfile(self):
        try:
            with open(self.log, encoding='utf-8') as f: return f.read()
        except OSError: return ''

    def fake(self):
        j = types.SimpleNamespace(msgs=[]); j.toast = lambda t, duration=1.8: j.msgs.append(LG.tr(t)); return j                                   # (comme Game.toast : le texte est traduit a l'affichage)

    def test_savestate_failure(self):
        for code, att in (('fr', "Chargement de l'état 3 impossible : OSError('disque')"), ('en', "Loading state 3 failed: OSError('disque')")):
            with entry(code):
                j = self.fake(); _, text = output(WND.Game._note_state_failure, j, LG.tr("Chargement de l'état %d") % 3, OSError('disque'))
            self.assertEqual(j.msgs, [att]); self.assertIn(att + ' ---\n', text); self.assertTrue(self.logfile().endswith(att + ' ---\n'))
        self.assertFalse(french(j.msgs[0].replace('disque', '')))

    def test_saving_is_impossible(self):
        for code, att, header in (('fr', 'Sauvegarde impossible : le jeu continue (détails dans window_errors.log)', 'sauvegarde impossible : data1.dat'),
                                  ('en', 'Save failed: the game continues (details in window_errors.log)', 'save failed: data1.dat')):
            with entry(code):
                j = self.fake(); core = types.SimpleNamespace(write_failures=['data1.dat']); _, text = output(WND.Game._report_write_failures, j, core)
            self.assertEqual(j.msgs, [att]); self.assertIn(header, text); self.assertIn(header, self.logfile())

    def test_engine_memory_and_missing_settings(self):
        note = []
        with mock.patch.object(WND, 'note_error', note.append):
            for code, memory, setting in (('fr', 'memoire du moteur a 98 % (250 Mo sur 256 Mo) ---\n', 'reglage du moteur non applique : a ---\n'),
                                           ('en', 'engine memory at 98 % (250 MB of 256 MB) ---\n', 'engine setting not applied: a ---\n')):
                note.clear()
                with entry(code):
                    j = types.SimpleNamespace(_heap_level=0); core = types.SimpleNamespace(heap_used=lambda: 250 << 20, HEAP_CRITICAL=240 << 20, HEAP_ALERT=200 << 20, HEAP_SIZE=256 << 20)
                    WND.Game._watch_heap(j, core)
                    eng = types.SimpleNamespace(missing_hooks=['a']); j2 = types.SimpleNamespace(_reported_hooks=0); WND.Game._report_missing_hooks(j2, eng)
                self.assertEqual(len(note), 2); self.assertTrue(note[0].endswith(memory), note[0]); self.assertTrue(note[1].endswith(setting), note[1])
                if code == 'en': self.assertFalse(french(note[0]) or french(note[1]), note)

    def test_startup_loading(self):
        for code, att in (('fr', ['Chargement du moteur...', 'Chargement de la sauvegarde...', 'Chargement de la carte...']), ('en', ['Loading the engine...', 'Loading the save...', 'Loading the map...'])):
            with entry(code):
                j = types.SimpleNamespace(switch_to=lambda: None, clear=lambda: None, flip=lambda: None, dispatch_events=lambda: None)
                _, text = output(lambda: [WND.Game._wait(j, t) for t in ('Chargement du moteur...', 'Chargement de la sauvegarde...', 'Chargement de la carte...')])
            self.assertEqual(text.splitlines(), att)

    def test_sound_focus_loss(self):
        def boum(yes): raise OSError('carte son')
        j = types.SimpleNamespace(_ready=True, sound=types.SimpleNamespace(lose_focus=boum), wheel=types.SimpleNamespace(cancel=lambda: None), hud=types.SimpleNamespace(dpad_drop=lambda: None, press_state=None), press_state=None, hovered=None,
                                  acc=0.0, t_loop=None, _camera_oublier=lambda: None, pad=lambda: 0, _held=lambda a: False, mouse_guard=types.SimpleNamespace(keyboard=lambda s: None), mouse=(0, 0))
        for code, a1, a2 in (('fr', "Son : pause a la perte du focus impossible (OSError('carte son'))", "Son : reprise au retour du focus impossible (OSError('carte son'))"),
                             ('en', "Sound: pausing on focus loss failed (OSError('carte son'))", "Sound: resuming on focus return failed (OSError('carte son'))")):
            with entry(code):
                _, t1 = output(WND.Game.on_deactivate, j); _, t2 = output(WND.Game.on_activate, j)
            self.assertEqual((t1.strip(), t2.strip()), (a1, a2))

    def test_cache_preparation_in_tool_language(self):
        """Le processus a part (monde/donnees.py) ne connait pas reglages.json : le jeu lui passe la langue (DQ4_LANGUE), pas celle de l'ordinateur."""
        for code in ('fr', 'en'):
            calls = []
            with entry(code), mock.patch('subprocess.Popen', lambda *a, **kw: calls.append(kw) or types.SimpleNamespace()):
                WND.Game._launch_preparation(types.SimpleNamespace(engine=types.SimpleNamespace(apk_data='x.apk')), 'cache')
            self.assertEqual(calls[0]['env']['DQ4_LANGUE'], code)
        with entry('en'), mock.patch('subprocess.Popen', side_effect=OSError('non')), mock.patch('threading.Thread'):
            j = types.SimpleNamespace(engine=types.SimpleNamespace(apk_data='x.apk'), data=types.SimpleNamespace(prepare=None), prep_stop=None)
            _, text = output(WND.Game._launch_preparation, j, 'cache')
        self.assertEqual(text.strip(), "Cache preparation: separate process failed (OSError('non')), running inside the game.")

    def test_preparation_process_speaks_received_language(self):
        """Vrai processus `python -m dq4_pc.world.data` (APK absent : « interrompue »)."""
        cache = os.path.join(self.t, 'cache'); os.makedirs(cache)
        for code, begin in (('fr', 'Preparation du cache interrompue : '), ('en', 'Cache preparation interrupted: ')):
            e = dict(os.environ, DQ4_LANGUE=code, PYTHONDONTWRITEBYTECODE='1')
            r = subprocess.run([sys.executable, '-m', 'dq4_pc.world.data', os.path.join(self.t, 'inexistant.apk'), cache], cwd=ROOT, env=e, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
            self.assertTrue(any(l.startswith(begin) for l in r.stdout.splitlines()), (r.stdout, r.stderr))
        self.assertEqual(r.stdout.splitlines()[0], 'Reading the game data pack (once only, a few seconds)...')

    def test_cancel_load(self):
        for code, a1, a2 in (('fr', 'Aucun chargement à annuler', 'Chargement annulé'), ('en', 'No load to undo', 'Load undone')):
            with entry(code):
                j = self.fake(); j.undo_state = None; INS.SnapshotsMixin.cancel_loading(j)
                j.undo_state = {'a': 1}; j._complete_savestate = lambda: {'b': 2}; j._apply_savestate = lambda d: None; INS.SnapshotsMixin.cancel_loading(j)
            self.assertEqual(j.msgs, [a1, a2])

    def test_window_size_too_large(self):
        with mock.patch.object(AI, 'useful_zone', lambda: (1904, 1040)):
            for code, model in (('fr', "Fenêtre 3840 x 2160 trop grande pour l'écran : %d x %d"), ('en', 'Window 3840 x 2160 too large for the screen: %d x %d')):
                with entry(code): (nw, nh), text = output(AI.adjust_size, 3840, 2160)
                self.assertEqual(text.strip(), model % (nw, nh))

    # ---- bascule plein ecran <-> fenetre (fausse fenetre de test_window_mode)
    def win(self, **k):
        f = TM.FakeWindow(WND, **k); f._log_window = types.MethodType(WND.Game._log_window, f); f.get_framebuffer_size = lambda: (f.width, f.height); return f

    def test_toggle_failure(self):
        with mock.patch.object(WND, 'useful_zone', lambda: (1904, 1040)):
            for code, line, header, lines in (
                    ('fr', "Plein écran impossible (RuntimeError('echec de set_fullscreen(True)')) : fenêtre conservé", 'passage en plein écran impossible ---',
                     ['fenêtre : plein écran = False, 1280 x 720, ', 'écran de la fenêtre pour pyglet : 1920 x 1080 en (0, 0)', 'moniteurs : 1920 x 1080 en (0, 0) (principal)']),
                    ('en', "Fullscreen failed (RuntimeError('echec de set_fullscreen(True)')): windowed mode kept", 'switch to fullscreen failed ---',
                     ['window: fullscreen = False, 1280 x 720, ', 'window screen according to pyglet: 1920 x 1080 at (0, 0)', 'monitors: 1920 x 1080 at (0, 0) (primary)'])):
                if os.path.exists(self.log): os.remove(self.log)
                f = self.win(failure='set_fullscreen(True)')
                with entry(code): render, text = output(f.set_full_screen, True)
                self.assertFalse(render)
                self.assertIn(line, text.splitlines())
                for att in [header] + lines: self.assertIn(att, text); self.assertIn(att, self.logfile())
                if code == 'en': self.assertFalse(french(without_paths(re.sub(r'Traceback.*?\n(?=\w)', '', text, flags=re.S))), text)

    def test_return_to_window_failure(self):
        with mock.patch.object(WND, 'useful_zone', lambda: (1904, 1040)):
            for code, line in (('fr', "Fenêtre impossible (RuntimeError('echec de set_fullscreen(False,1280x720)')) : plein écran conservé"),
                                ('en', "Windowed mode failed (RuntimeError('echec de set_fullscreen(False,1280x720)')): fullscreen kept")):
                f = self.win(full=True, failure='set_fullscreen(False,1280x720)')
                with entry(code): render, text = output(f.set_full_screen, False)
                self.assertTrue(render); self.assertIn(line, text.splitlines())

    def test_window_logfile_line(self):
        for code, att in (('fr', 'Fenêtre (création) : fenêtre, 1280 x 720, zone de dessin 1280 x 720, écran 1920 x 1080 (écran 1)'),
                          ('en', 'Window (creation): window, 1280 x 720, drawing area 1280 x 720, screen 1920 x 1080 (screen 1)')):
            f = self.win()
            with entry(code): _, text = output(f._log_window, 'création')
            self.assertEqual(text.strip(), att)
        for code, att in (('fr', 'Fenêtre (plein écran) : PLEIN ÉCRAN [INCOHÉRENT : fullscreen=False], '), ('en', 'Window (fullscreen): FULLSCREEN [INCONSISTENT: fullscreen=False], ')):
            f = self.win(full=True); f.fullscreen = False; f.win_mode = 1
            with entry(code): _, text = output(f._log_window, 'plein écran')
            self.assertTrue(text.startswith(att), text)
        for code, att in (('fr', 'Fenêtre (1re image du jeu) : état illisible ('), ('en', 'Window (1st game frame): state unreadable (')):
            f = self.win(); f.screen_ = None; del_f = types.SimpleNamespace()
            with entry(code): _, text = output(WND.Game._log_window, del_f, '1re image du jeu')
            self.assertTrue(text.startswith(att), text)

    def test_unreadable_monitors(self):
        for code, att in (('fr', "Moniteurs illisibles (OSError('plus de moniteurs'))"), ('en', "Monitors unreadable (OSError('plus de moniteurs'))")):
            f = self.win(); f.display = types.SimpleNamespace(get_screens=lambda: (_ for _ in ()).throw(OSError('plus de moniteurs')))
            with entry(code): _, text = output(f._read_screens, True)
            self.assertEqual(text.strip(), att)

    def test_window_title(self):
        self.assertEqual(WND.Game.WINDOW_TITLE, 'Dragon Quest IV - portage PC (essai)')           # (constante de module marquee N_ : traduite a la creation de la fenetre)
        with entry('en'): self.assertEqual(LG.tr(WND.Game.WINDOW_TITLE), 'Dragon Quest IV - PC port (trial)')

    def test_slot_text_on_the_command_line(self):
        """`--slot N` : l'etat du chargement direct, dans les deux langues (les deux phrases entieres du catalogue)."""
        for code, a, b in (('fr', 'sauvegarde 2 chargee : oui', 'sauvegarde 2 chargee : NON (fichier data2.dat introuvable ou invalide dans x)'),
                           ('en', 'save 2 loaded: yes', 'save 2 loaded: NO (file data2.dat not found or invalid in x)')):
            with entry(code):
                self.assertEqual(LG.tr('sauvegarde %d chargee : oui') % 2, a); self.assertEqual(LG.tr('sauvegarde %d chargee : NON (fichier data%d.dat introuvable ou invalide dans %s)') % (2, 2, 'x'), b)


# ======================================================================================================================================================
@unittest.skipIf(WND is None, 'moteur non importable ici')
class Engine(unittest.TestCase):
    """Alertes de version du moteur (Engine._manque) : un autre APK que celui etudie."""
    def setUp(self):
        import test_missing_hooks as TC
        self.TC = TC; self.addCleanup(LG.select_language, 'fr')

    def test_locations_window_and_settings_button(self):
        other = (self.TC.ORIGINAL[0], self.TC.ORIGINAL[1], 0x11000120 | (0x555 << 10))
        for code, locations, button in (('fr', "fenetre des lieux non elargie : FieldData::drawSymbol inattendu, les lieux de la carte du monde n'apparaissent que dans la fenetre d'origine",
                                     "bouton Paramètres : comparaison du menu Divers inattendue, le bouton ouvre les reglages d'origine du jeu et non le menu Pause"),
                                    ('en', "places window not widened: unexpected FieldData::drawSymbol, world map places only appear in the original window",
                                     "Settings button: unexpected comparison in the Misc menu, the button opens the game's original settings instead of the Pause menu")):
            with entry(code):
                m = self.TC.fake_engine(other); _, text = output(m._widen_symbols); self.assertEqual((text.strip(), m.missing_hooks), (locations, [locations]))
                m = self.TC.fake_engine(cmp_param=0xd503201f); _, text = output(m.patch_params); self.assertEqual((text.strip(), m.missing_hooks), (button, [button]))

    def test_all_installers_speak_the_tool_language(self):
        """Un moteur dont les fonctions sont introuvables : chaque installateur le dit, en francais comme avant (`KeyError`) et en anglais sans un mot de francais."""
        def not_found(n): raise KeyError(n)
        names = ('_text_hooks', '_fade_hooks', '_level_hooks', '_encounter_hooks', '_day_clock_hooks', '_game_time_hooks', '_magic_hooks', '_divert_params', '_widen_symbols')
        resultats = {}
        for code in ('fr', 'en'):
            with entry(code):
                resultats[code] = []
                for name_str in names:
                    m = self.TC.fake_engine(); m.core.export = not_found; output(getattr(m, name_str)); resultats[code] += m.missing_hooks
        self.assertEqual(len(resultats['fr']), len(resultats['en'])); self.assertGreaterEqual(len(resultats['fr']), len(names))
        for fr, ang in zip(resultats['fr'], resultats['en']):
            self.assertNotEqual(fr, ang); self.assertFalse(french(ang), ang)
        self.assertIn('vitesse du texte non installee : KeyError(\'DevInit\')'.split(':')[0], '\n'.join(resultats['fr']))


# ======================================================================================================================================================
@unittest.skipIf(WND is None, 'son non importable ici')
class Sound(unittest.TestCase):
    def new(self):
        from dq4_pc import sound as SOUND
        self.SOUND = SOUND; lines, logfile, alerts = [], [], []
        with mock.patch.dict(sys.modules, {'pyglet': None, 'soundfile': None}):                                  # ni pyglet ni soundfile : « indisponible »
            s = SOUND.Sound('inexistant.apk', self.tmp, log=lambda *a: lines.append(' '.join(str(x) for x in a)), logfile=logfile.append, alert=alerts.append)
        return s, lines, logfile, alerts

    def setUp(self): self.tmp = tempfile.mkdtemp(prefix='lang_son_'); self.addCleanup(shutil.rmtree, self.tmp, True); self.addCleanup(LG.select_language, 'fr')

    def test_sound_unavailable(self):
        with entry('fr'): s, lines, _, _ = self.new()
        self.assertEqual(lines[0], 'Musiques indisponibles : module "soundfile" absent (pip install soundfile). Les bruitages restent actifs.'); self.assertTrue(lines[1].startswith('Son indisponible ('))
        with entry('en'): s, lines, _, _ = self.new()
        self.assertEqual(lines[0], 'Music unavailable: "soundfile" module missing (pip install soundfile). Sound effects stay active.'); self.assertTrue(lines[1].startswith('Sound unavailable ('))
        self.assertFalse(french(lines[0]))

    def test_failures_cut_and_restoration(self):
        attendus = {'fr': ["bruitage 5 impossible (OSError('x')), echec 1", "bruitage 5 impossible (OSError('x')), echec 2", "bruitage 5 impossible (OSError('x')), echec 3", 'son interrompu, nouvel essai dans 2 s',
                           "volume de la musique impossible (OSError('v')), note une seule fois", 'son retabli'],
                    'en': ["sound effect 5 failed (OSError('x')), failure 1", "sound effect 5 failed (OSError('x')), failure 2", "sound effect 5 failed (OSError('x')), failure 3", 'sound interrupted, retrying in 2 s',
                           "music volume failed (OSError('v')), logged only once", 'sound restored']}
        alerts_expected = {'fr': ['Son interrompu : nouvel essai automatique', 'Son rétabli'], 'en': ['Sound interrupted: automatic retry', 'Sound restored']}
        for code in ('fr', 'en'):
            with entry(code):
                s, lines, logfile, alerts = self.new(); lines.clear()
                for _ in range(3): s._failure(LG.tr('bruitage %d') % 5, OSError('x'))
                s._note_once(LG.N_('volume de la musique'), OSError('v')); s._note_once(LG.N_('volume de la musique'), OSError('v'))       # (une seule fois)
                s._success()
            self.assertEqual(logfile, attendus[code]); self.assertEqual(alerts, alerts_expected[code])
            self.assertEqual(lines, [('Sound: ' if code == 'en' else 'Son : ') + t for t in attendus[code]])
        self.assertEqual(lines[0], 'Sound: sound effect 5 failed (OSError(\'x\')), failure 1')

    def test_music_and_resume(self):
        with entry('en'):
            s, lines, logfile, alerts = self.new()
            s._failure(LG.tr('musique %d') % 12, OSError('m')); s._note_once(LG.N_('volume des bruitages'), OSError('b')); s._note_once(LG.N_('reprise apres la pause'), OSError('p'))
        self.assertEqual(logfile, ["music track 12 failed (OSError('m')), failure 1", "sound effects volume failed (OSError('b')), logged only once", "resume after pause failed (OSError('p')), logged only once"])


if __name__ == '__main__':
    unittest.main(verbosity=1)
