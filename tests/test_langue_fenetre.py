"""Langue de l'outil, lot « fenetre » (D-238) : messages de la console et de la fenetre du jeu, demarrage, ligne de commande (`--help`), reprise des dossiers, sauvegardes, son, moteur.
Sans fenetre ni APK (faux Jeu, fausse fenetre pyglet) : chaque scenario est joue en francais (le texte d'avant, mot pour mot) puis en anglais (plus un mot de francais : `francais()` de test_langue).

  1. couverture (lecture du code) : chaque texte passe a tr() / N_() dans le perimetre a sa traduction anglaise, aucune cle du catalogue n'est orpheline, rien n'est traduit a l'import, les textes passes a `_attente`,
     `_journal_fenetre`, `_une_fois` sont marques N_, et AUCUN message de console n'est reste en francais sans tr() (liste blanche des traces de debogage, chacune justifiee) ;
  2. ligne de commande : l'aide `--help` (analyseur et processus complet) dans les deux langues, la langue reglee AVANT la migration et l'analyseur (reglages.json par defaut ou donne par --reglages), messages de
     demarrage (APK introuvables, migration impossible) ;
  3. reprise des dossiers (chemins.migrer), export / import de sauvegardes, etats, journaux : les raisons montrees au joueur ;
  4. fenetre : messages de Jeu (echecs d'etats et de sauvegarde, memoire du moteur, reglages manques, chargement), bascule plein ecran <-> fenetre (console et journal des erreurs), ligne de journal de la fenetre,
     moniteurs, taille ; son ; alertes de version du moteur (`Moteur._manque`) ; preparation du cache (processus a part, langue transmise).

    python3 tests/test_langue_fenetre.py"""
import ast, contextlib, glob, io, json, os, re, shutil, subprocess, sys, tempfile, types, unittest, warnings, zipfile
from unittest import mock

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, RACINE); sys.path.insert(0, ICI)
import _chemins
import test_langue as TL
from dq4_pc import chemins as CH
from dq4_pc import langue as LG
from dq4_pc.persistance import etats as ET, format_journal as FJ, sauvegardes as SA

francais = TL.francais


def catalogue(noms=('fenetre', 'divers')):
    import importlib
    c = {}
    for nom in noms: c.update(importlib.import_module('dq4_pc.textes_en.' + nom).EN)
    return c


CAT_PROPRE = catalogue()                                                    # les entrees de ce lot (fenetre.py, divers.py)
CAT = catalogue(('pause', 'menus', 'fenetre', 'divers'))                    # tout le catalogue : un meme texte n'a qu'une entree, dans le fichier du premier lot qui l'a ecrit (test_langue.py : pas de doublon)
DOSSIER = os.path.join(RACINE, 'dq4_pc')
FEN = [os.path.join('dq4_pc', 'fenetre', f) for f in ('jeu.py', 'plein_ecran.py', 'champ.py', 'clavier_souris.py', 'camera.py', 'options.py', 'aides.py', 'scene_combat.py', 'instantanes.py')]
PERIMETRE = (['dq4_pc/principal.py', 'dq4_pc/chemins.py', 'dq4_pc/son.py', 'dq4_pc/noyau/moteur.py'] + FEN
             + ['dq4_pc/persistance/' + f for f in ('ecriture.py', 'etats.py', 'sauvegardes.py', 'format_journal.py', 'reglages.py')]
             + sorted(os.path.relpath(p, RACINE) for p in glob.glob(os.path.join(DOSSIER, 'monde', '*.py')) + glob.glob(os.path.join(DOSSIER, 'rendu', '*.py'))))


def arbre(chemin):
    with open(os.path.join(RACINE, chemin), encoding='utf-8') as f: return ast.parse(f.read())


def nom_appel(n):
    return getattr(n.func, 'id', None) or getattr(n.func, 'attr', None)


def litteraux(chemin, noms=('tr', 'N_')):
    """[(ligne, texte)] des textes litteraux passes a tr() / N_() (LG.tr compris)."""
    return [(n.lineno, n.args[0].value) for n in ast.walk(arbre(chemin)) if isinstance(n, ast.Call) and nom_appel(n) in noms and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)]


@contextlib.contextmanager
def en(code):
    """Joue ce qui suit dans la langue `code` ('fr' ou 'en')."""
    LG.regler(code)
    try: yield
    finally: LG.regler('fr')


def sortie(f, *a, **k):
    """-> (resultat, texte imprime) de f(*a, **k)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): r = f(*a, **k)
    return r, buf.getvalue()


def sans_chemins(t):
    """Le texte sans les chemins (dossiers temporaires) : ce ne sont pas des mots."""
    return re.sub(r'(?:[A-Za-z]:)?[\\/][^\s\'")]+', ' ', t)


def ecrire(chemin, contenu=b'x'):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, 'wb') as f: f.write(contenu)
    return chemin


# ======================================================================================================================================================
class Couverture(unittest.TestCase):
    """Lecture du code : rien ne manque, rien ne traine."""
    def test_chaque_texte_du_code_a_sa_traduction(self):
        manques = []; identiques = []
        for p in PERIMETRE:
            for ligne, t in litteraux(p):
                if t not in CAT:
                    if francais(t): manques.append('%s:%d %r' % (p, ligne, t))                                  # (« Casino », « Normal », « Menu »... : identiques en anglais, sans entree)
                elif CAT[t] == t: identiques.append('%s:%d %r' % (p, ligne, t))
        self.assertEqual(manques, [], 'textes passes a tr() / N_() sans traduction (fenetre.py, divers.py)')
        self.assertEqual(identiques, [], 'traduction identique au francais')

    def test_aucune_cle_orpheline(self):
        """Chaque entree de fenetre.py et divers.py sert dans le code (un texte change ou retire dans le code ne laisse pas sa traduction derriere lui)."""
        utilisees = set()
        for d, _, fs in os.walk(DOSSIER):
            for f in fs:
                if f.endswith('.py') and '__pycache__' not in d: utilisees.update(t for _, t in litteraux(os.path.relpath(os.path.join(d, f), RACINE)))
        self.assertEqual(sorted(k for k in CAT_PROPRE if k not in utilisees), [])

    def test_rien_n_est_traduit_a_l_import(self):
        """`tr(...)` ne s'execute que dans une fonction (la langue change en cours de partie) ; une constante de module est marquee N_ et traduite a l'affichage."""
        fautifs = []
        for p in PERIMETRE:
            a = arbre(p); parents = {id(c): n for n in ast.walk(a) for c in ast.iter_child_nodes(n)}
            for n in ast.walk(a):
                if isinstance(n, ast.Call) and nom_appel(n) == 'tr':
                    x = n
                    while id(x) in parents and not isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)): x = parents[id(x)]
                    if not isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)): fautifs.append('%s:%d' % (p, n.lineno))
        self.assertEqual(fautifs, [])

    def test_textes_passes_a_une_fonction_qui_traduit_sont_marques(self):
        """`_attente(texte)`, `_journal_fenetre(quand)` et `_une_fois(cle, e)` traduisent leur argument : le texte litteral doit etre passe a N_(), sinon le test de couverture ne le voit pas."""
        nus = []
        for p in PERIMETRE:
            for n in ast.walk(arbre(p)):
                if isinstance(n, ast.Call) and nom_appel(n) in ('_attente', '_journal_fenetre', '_une_fois') and n.args and isinstance(n.args[0], ast.Constant):
                    if isinstance(n.func, ast.Attribute): nus.append('%s:%d %r' % (p, n.lineno, n.args[0].value))
        self.assertEqual(nus, [])

    def test_tr_n_et_lg_sont_importes_la_ou_ils_servent(self):
        """Un `tr(...)` ajoute dans un module qui ne l'importe pas ne plante qu'au moment du message (souvent une erreur rare : echec de bascule, son coupe...) : on le voit ici, a la lecture du code."""
        non_lies = []
        for p in PERIMETRE:
            a = arbre(p); lies = set()
            for n in ast.walk(a):
                if isinstance(n, (ast.Import, ast.ImportFrom)): lies.update((x.asname or x.name).split('.')[0] for x in n.names)
                elif isinstance(n, (ast.FunctionDef, ast.ClassDef)): lies.add(n.name)
                elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store): lies.add(n.id)
                elif isinstance(n, ast.arg): lies.add(n.arg)
            non_lies += ['%s:%d %s' % (p, n.lineno, n.id) for n in ast.walk(a) if isinstance(n, ast.Name) and n.id in ('tr', 'N_', 'LG') and isinstance(n.ctx, ast.Load) and n.id not in lies]
        self.assertEqual(non_lies, [])

    # liste blanche : (fichier, debut du texte) des messages de console que le joueur ne voit pas (traces des options de test et des variables DQ_*, journal interne du moteur)
    DEBOGAGE = (
        ('son.py', 'Son : image '),                                    # DQ_SON : ordres du moteur
        ('moteur.py', 'fopen '), ('moteur.py', 'MSGDBG '), ('moteur.py', 'ENVOI '), ('moteur.py', 'MSG image '), ('moteur.py', 'FBX image '),          # DQ_SAVEDBG, DQ_MSGDBG, DQ_MENUDBG, DQ_FBXLOG
        ('camera.py', 'PROJ n='), ('camera.py', 'CAMV n='), ('camera.py', '   sprites'),                                                              # DQ_PROJ, DQ_CAMV
        ('clavier_souris.py', 'FRONT discussion'),
        ('jeu.py', 'SPRITES'), ('jeu.py', 'n=%d p='), ('jeu.py', 'FLAG n='), ('jeu.py', 'ETAT n='), ('jeu.py', 'combat'), ('jeu.py', 'capture :'),     # DQ_SPR, DQ_DEBUG, --shot, --shots-combat
        ('jeu.py', 'OPTION %s'), ('jeu.py', 'PAS moteur='),                                                                                          # --options-test, DQ_PAS
        ('plein_ecran.py', 'pyglet %s, Python'),                       # versions des logiciels dans le journal d'une bascule ratee : des noms propres
        ('champ.py', 'decors_plats :'),                                # nom du module + exception : un identifiant, pas une phrase
        ('fld.py', 'nobj'),                                            # outil en ligne de commande de lecture des FLD
        ('etats.py', 'etat : fichier ouvert non restaure'),            # journal du moteur d'origine (Silencieux), pas la console
    )

    def test_aucun_message_de_console_n_est_reste_en_francais_sans_tr(self):
        """Un `print(...)` / `log(...)` / `toast(...)` dont le texte est un litteral (ou un litteral formate) doit passer par tr() ; sinon il est dans la liste blanche DEBOGAGE. emu_core.py (journal de l'emulateur,
        outil de developpement) n'est pas balaye."""
        noms = {'print', 'log', '_manque', 'toast', '_noter', '_echec', 'add_note', 'noter_erreur'}
        nus = []; vus = set()
        for p in PERIMETRE:
            for n in ast.walk(arbre(p)):
                if not isinstance(n, ast.Call) or not n.args: continue
                nom = nom_appel(n)
                if nom == 'append' and not (isinstance(n.func.value, ast.Name) and n.func.value.id in ('fait', 'pb', 'etat')): continue
                if nom not in noms and nom != 'append': continue
                a = n.args[0]
                while isinstance(a, ast.BinOp): a = a.left                             # 'texte %s' % x, 'debut' + x
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and len(a.value) > 1:
                    base = os.path.basename(p); ok = [d for d in self.DEBOGAGE if d[0] == base and a.value.startswith(d[1])]
                    if ok: vus.add(ok[0])
                    else: nus.append('%s:%d %r' % (p, n.lineno, a.value[:80]))
        self.assertEqual(nus, [], 'messages de console en francais sans tr()')
        self.assertEqual([d for d in self.DEBOGAGE if d not in vus], [], 'entree de la liste blanche qui ne correspond plus a rien')


# ======================================================================================================================================================
try:
    from dq4_pc import principal as P
except Exception as _ex:
    P = None; _ERREUR_P = _ex


@unittest.skipIf(P is None, 'principal non importable ici')
class LigneDeCommande(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='lang_cmd_'); self.d = CH.Dossiers(self.t, env={}); self.avant = (CH.DOSSIERS, CH.migrer)

    def tearDown(self): CH.DOSSIERS, CH.migrer = self.avant; LG.regler('fr'); shutil.rmtree(self.t, ignore_errors=True)

    def reglages(self, langue, chemin=None):
        chemin = chemin or self.d.reglages; os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(chemin, 'w', encoding='utf-8') as f: json.dump({'langue': langue}, f)
        return chemin

    def aides(self):
        """{option: texte d'aide} de l'analyseur construit dans la langue courante."""
        return {a.option_strings[0]: a.help for a in P.construire_parseur(self.d)._actions if a.help and a.option_strings[0] != '-h'}

    def test_l_aide_est_dans_la_langue_choisie(self):
        with en('fr'): fr = self.aides()
        with en('en'): ang = self.aides()
        self.assertEqual(sorted(fr), sorted(ang)); self.assertGreaterEqual(len(fr), 33)
        self.assertEqual(fr['--apk'], 'dossier des 3 APK (version francaise) ; par defaut donnees\\apk')                              # le francais d'avant, mot pour mot
        self.assertEqual(fr['--sans-son'], 'coupe le son pour cette session (le menu Echap permet de le remettre)')
        self.assertEqual(ang['--apk'], 'folder of the 3 game APK files; default donnees\\apk')
        for option in fr:
            self.assertNotEqual(ang[option], fr[option], option)
            self.assertFalse(francais(ang[option]), '%s : %r' % (option, ang[option]))
            self.assertNotIn('%', ang[option].replace('%%', ''), option)                  # (argparse formate l'aide avec % : un pourcentage nu la casserait)
        self.assertEqual(sorted(o for o in fr if fr[o].startswith('(test) ')), sorted(o for o in ang if ang[o].startswith('(test) ')))          # les options de test restent annoncees comme telles

    def test_format_help_ne_plante_pas_dans_les_deux_langues(self):
        for code in ('fr', 'en'):
            with en(code): texte = P.construire_parseur(self.d).format_help()
            self.assertIn('--saves-ecriture', texte); self.assertIn('usage: dq4_pc', texte)

    def test_fichier_de_reglages_de_la_ligne_de_commande(self):
        self.assertEqual(P.fichier_reglages(['--slot', '2'], self.d), self.d.reglages)
        self.assertEqual(P.fichier_reglages(['--reglages', 'a.json', '--slot', '2'], self.d), 'a.json')
        self.assertEqual(P.fichier_reglages(['--slot', '2', '--reglages=b.json'], self.d), 'b.json')
        self.assertEqual(P.fichier_reglages(['--reglages'], self.d), self.d.reglages)                  # valeur manquante : c'est l'analyseur qui s'en plaindra

    def test_la_langue_vient_du_reglage_et_pas_de_l_ordinateur(self):
        self.reglages('en'); self.assertEqual(P.regler_langue([], self.d), 'en')
        self.reglages('fr'); self.assertEqual(P.regler_langue([], self.d), 'fr')
        autre = self.reglages('en', os.path.join(self.t, 'autre', 'reglages.json'))
        self.assertEqual(P.regler_langue(['--reglages', autre], self.d), 'en')                           # --reglages l'emporte sur le fichier par defaut ('fr')
        os.remove(self.d.reglages); self.assertEqual(P.regler_langue([], self.d), LG.regler('systeme'))     # pas de fichier : la langue de l'ordinateur

    def principal(self, argv):
        """main(argv) sans migration reelle ni fenetre : -> (langues vues par migrer, texte imprime, code de sortie)."""
        CH.DOSSIERS = self.d; vues = []; CH.migrer = lambda d=None, log=print: vues.append(LG.courante()) or []
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit) as cm: P.main(argv)
        return vues, buf.getvalue(), cm.exception.code

    def principal_texte(self, argv):
        CH.DOSSIERS = self.d; CH.migrer = lambda d=None, log=print: []
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit) as cm: P.main(argv)
        return buf.getvalue(), cm.exception.code

    def test_apk_introuvables_en_francais_et_en_anglais(self):
        vide = os.path.join(self.t, 'vide'); os.makedirs(vide)
        self.reglages('fr'); texte, code = self.principal_texte(['--apk', vide]); self.assertEqual(code, 1)
        self.assertEqual(texte, 'Jeu : APK dans %s\n\nLes APK francais sont introuvables.\nMets base.apk, split_config.arm64_v8a.apk et split_UnityDataAssetPack.apk dans :\n   %s\n(et, si tu en as une, les fichiers data1.dat... de ta sauvegarde du telephone dans %s). Autre dossier : set DQ4_DONNEES=chemin\\vers\\donnees\n'
                         % (vide, os.path.normpath(vide), self.d.sauvegardes))
        self.reglages('en'); texte, code = self.principal_texte(['--apk', vide]); self.assertEqual(code, 1)
        self.assertEqual(texte, 'Game: APK files in %s\n\nThe game APK files were not found.\nPut base.apk, split_config.arm64_v8a.apk and split_UnityDataAssetPack.apk in:\n   %s\n(and, if you have one, the data1.dat... files of your phone save in %s). Other folder: set DQ4_DONNEES=path\\to\\donnees\n'
                         % (vide, os.path.normpath(vide), self.d.sauvegardes))
        self.assertFalse(francais(sans_chemins(texte)), texte)

    def test_la_langue_est_reglee_avant_la_migration(self):
        """Les messages de la migration (chemins.migrer) sont dans la langue du reglage : reglages.json par defaut, ou celui de --reglages ; et la langue ne depend pas de celle de l'ordinateur."""
        vide = os.path.join(self.t, 'vide'); os.makedirs(vide)
        self.reglages('en'); vues, _, _ = self.principal(['--apk', vide]); self.assertEqual(vues, ['en'])
        self.reglages('fr'); vues, _, _ = self.principal(['--apk', vide]); self.assertEqual(vues, ['fr'])
        autre = self.reglages('en', os.path.join(self.t, 'autre.json')); vues, texte, _ = self.principal(['--apk', vide, '--reglages', autre])
        self.assertEqual(vues, ['en']); self.assertIn('The game APK files were not found.', texte)

    def test_migration_impossible(self):
        CH.DOSSIERS = self.d
        def casse(d=None, log=print): raise RuntimeError('boum')
        CH.migrer = casse
        for code, att in (('fr', "Migration des fichiers impossible (RuntimeError('boum')) : le jeu continue avec les dossiers actuels."),
                          ('en', "File migration failed (RuntimeError('boum')): the game continues with the current folders.")):
            self.reglages(code)
            with self.assertRaises(SystemExit): _, texte = sortie(P.main, ['--apk', os.path.join(self.t, 'vide')])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit): P.main(['--apk', os.path.join(self.t, 'vide')])
            self.assertEqual(buf.getvalue().splitlines()[0], att)

    def lancer(self, *args, env=None):
        e = dict(os.environ, DQ4_DONNEES=os.path.join(self.t, 'donnees'), PYTHONDONTWRITEBYTECODE='1', PYGLET_HEADLESS='1', PYGLET_AUDIO='silent'); e.update(env or {})
        return subprocess.run([sys.executable, '-m', 'dq4_pc', *args], cwd=RACINE, env=e, capture_output=True, text=True, timeout=180)

    def test_python_m_dq4_pc_help_dans_les_deux_langues(self):
        """Le vrai processus : `--help` ne ouvre rien, lit la langue dans le fichier de --reglages et imprime l'aide dans cette langue (les noms d'options restent les vrais)."""
        for code in ('fr', 'en'):
            r = self.lancer('--reglages', self.reglages(code, os.path.join(self.t, code + '.json')), '--help')
            if r.returncode != 0 and 'ModuleNotFoundError' in r.stderr: self.skipTest('dependances absentes : ' + r.stderr.strip().splitlines()[-1])
            self.assertEqual(r.returncode, 0, r.stderr); self.assertEqual(r.stderr, '')
            if code == 'fr': self.assertIn('dossier des 3 APK (version francaise)', r.stdout)
            else:
                self.assertIn('folder of the 3 game APK files', r.stdout)
                texte = re.sub(r'--[\w-]+|\{[^}]*\}|\b[A-Z][A-Z_]{2,}\b', ' ', r.stdout)                  # sans les noms d'options, leurs valeurs et les listes de choix
                self.assertFalse(francais(texte), [m for m in re.findall(r"[a-zA-Z']+", texte.lower().replace("'", ' ')) if m in TL.MOTS_FRANCAIS])


# ======================================================================================================================================================
class Reprise(unittest.TestCase):
    """chemins.migrer : les phrases de la reprise de l'ancienne disposition."""
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='lang_migr_'); self.d = CH.Dossiers(self.t, env={}); r = self.t
        ecrire(os.path.join(r, 'jeux', 'DQ4', 'patched_apks', 'base.apk'), b'APK1')
        ecrire(os.path.join(r, 'jeux', 'DQ4', 'saves', '20261103_222423', 'data1.dat'), b'T1')
        ecrire(os.path.join(r, 'dq4_pc', 'cache', 'carte10_a.pkl'), b'CACHE')
        ecrire(os.path.join(r, 'dq4_pc', 'sauvegardes', 'data1.dat'), b'P1'); ecrire(os.path.join(r, 'dq4_pc', 'sauvegardes', 'etats', 'etat_01.dqs'), b'E1')
        ecrire(os.path.join(r, 'dq4_pc', 'reglages.json'), b'{"a": 1}'); ecrire(os.path.join(r, 'dq4_pc', 'erreurs_fenetre.log'), b'LOG')
        ecrire(os.path.join(self.d.ancien_portage, 'data2.dat'), b'portage2'); ecrire(os.path.join(self.d.mobile, '20261103_222423', 'data3.dat'), b'tel3')

    def tearDown(self): LG.regler('fr'); shutil.rmtree(self.t, ignore_errors=True)

    def migrer(self):
        lignes = []; fait = CH.migrer(self.d, log=lignes.append); return fait, lignes

    def test_en_francais_le_texte_d_avant(self):
        with en('fr'): fait, lignes = self.migrer()
        for ph in ('cache deplace : dq4_pc\\cache -> donnees\\cache', '1 fichier(s) APK copie(s) : jeux\\DQ4\\patched_apks -> donnees\\apk',
                   '1 fichier(s) de reglages copie(s) : dq4_pc -> donnees\\reglages', 'journal des erreurs copie : donnees\\journaux'):
            self.assertIn(ph, fait)
        self.assertTrue(any(ph.startswith('anciens dossiers ranges : sauvegardes\\mobile, sauvegardes\\portage') or ph.startswith('anciens dossiers ranges : ') for ph in fait), fait)
        self.assertEqual(lignes, ['Migration : ' + ph for ph in fait])

    def test_en_anglais_plus_un_mot_de_francais(self):
        with en('en'): fait, lignes = self.migrer()
        self.assertIn('cache moved: dq4_pc\\cache -> donnees\\cache', fait); self.assertIn('1 APK file(s) copied: jeux\\DQ4\\patched_apks -> donnees\\apk', fait)
        self.assertIn('1 settings file(s) copied: dq4_pc -> donnees\\reglages', fait); self.assertIn('error log copied: donnees\\journaux', fait)
        self.assertGreaterEqual(len(fait), 6); self.assertEqual(lignes, ['Migration: ' + ph for ph in fait])
        for ph in lignes: self.assertFalse(francais(ph), ph)

    def test_rangement_impossible(self):
        """Un dossier nomme data1.dat occupe la place : l'ancien dossier ne bouge pas, et la phrase le dit (avec la raison)."""
        ecrire(os.path.join(self.d.ancien_portage, 'data1.dat'), b'portage1'); os.makedirs(os.path.join(self.d.sauvegardes, 'data1.dat'))
        with en('fr'): fait, _ = self.migrer()
        self.assertTrue(any(ph.startswith('anciens dossiers de sauvegardes NON ranges (') and 'data1.dat' in ph and ph.endswith(') : ils restent en place') for ph in fait), fait)
        shutil.rmtree(self.t); self.setUp(); ecrire(os.path.join(self.d.ancien_portage, 'data1.dat'), b'portage1'); os.makedirs(os.path.join(self.d.sauvegardes, 'data1.dat'))
        with en('en'): fait, _ = self.migrer()
        phrase = [ph for ph in fait if ph.startswith('old save folders NOT moved (')]
        self.assertEqual(len(phrase), 1, fait); self.assertTrue(phrase[0].endswith('): they stay in place')); self.assertFalse(francais(sans_chemins(phrase[0])), phrase[0])

    def test_le_processus_de_reprise_seule_prend_la_langue_du_reglage(self):
        """`python -m dq4_pc.chemins` (lance par lancer_dq4.bat avant le jeu) lit la langue dans reglages.json avant de migrer."""
        import runpy
        donnees = os.path.join(self.t, 'donnees_neuves'); rg = os.path.join(donnees, 'reglages', 'reglages.json'); os.makedirs(os.path.dirname(rg))
        with open(rg, 'w', encoding='utf-8') as f: json.dump({'langue': 'en'}, f)
        with mock.patch.dict(os.environ, {'DQ4_DONNEES': donnees}), mock.patch('os.replace'), mock.patch('shutil.copy2'), mock.patch('shutil.copyfile'):
            LG.regler('fr')
            with warnings.catch_warnings(): warnings.simplefilter('ignore'); sortie(runpy.run_module, 'dq4_pc.chemins', run_name='__main__')
        self.assertEqual(LG.courante(), 'en')


# ======================================================================================================================================================
def journal(n):
    """Un journal valide de 15 360 octets (comme test_import_sauvegardes)."""
    import struct
    clair = bytearray(FJ.TAILLE_JOURNAL); struct.pack_into('<II', clair, 0, FJ.MAGIE1, FJ.MAGIE2); clair[200] = n % 256
    struct.pack_into('<I', clair, 8, FJ.somme(bytes(clair)))
    return FJ.dechiffrer(bytes(clair))


class Persistance(unittest.TestCase):
    """Les raisons montrees au joueur : export / import des sauvegardes, journaux, etats."""
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='lang_pers_'); self.d = CH.Dossiers(self.t, env={}); self.avant = CH.DOSSIERS; CH.DOSSIERS = self.d
        self.ecr = self.d.portage; self.zip = os.path.join(self.t, 'i.zip')

    def tearDown(self): CH.DOSSIERS = self.avant; LG.regler('fr'); shutil.rmtree(self.t, ignore_errors=True)

    def zipper(self, **fichiers):
        with zipfile.ZipFile(self.zip, 'w') as z:
            for nom, d in fichiers.items(): z.writestr(nom.replace('__', '/'), d)

    def erreur(self, f, *a):
        with self.assertRaises((ValueError, Exception)) as cm: f(*a)
        return str(cm.exception)

    def test_rien_a_exporter(self):
        with en('fr'): m = self.erreur(SA.exporter, self.ecr, self.d.mobile, os.path.join(self.t, 'x.zip'))
        self.assertEqual(m, 'Aucune sauvegarde a exporter (ni journal, ni etat instantane).')
        with en('en'): m = self.erreur(SA.exporter, self.ecr, self.d.mobile, os.path.join(self.t, 'x.zip'))
        self.assertEqual(m, 'Nothing to export (no adventure log, no save state).')

    def problemes(self):
        """Un import qui ecarte un journal trop court, un abime, un qui n'en est pas un, un etat trop petit et un faux .zip, mais qui garde un bon journal."""
        mauvais = bytearray(journal(3)); mauvais[100] ^= 1
        faux_zip = ecrire(os.path.join(self.t, 'broken.zip'), b'ceci n est pas un zip')
        self.zipper(**{'data1.dat': journal(2), 'data2.dat': bytes(mauvais), 'data3.dat': bytes(FJ.TAILLE_JOURNAL), 'data4.dat': b'court', 'etats__etat_01.dqs': b'petit'})
        return SA.importer([self.zip, faux_zip], self.ecr, self.d.mobile)

    def test_problemes_d_import_en_francais(self):
        with en('fr'): nj, ne, copie, pb = self.problemes()
        self.assertEqual((nj, ne), (1, 0))
        txt = '\n'.join(pb)
        for att in ('data4.dat : taille 5 au lieu de 15360 (i.zip)', 'data2.dat : fichier abime (somme de controle incorrecte) (i.zip)', "data3.dat : ce n'est pas un journal du jeu (en-tete inconnu) (i.zip)",
                    'etat_01.dqs : fichier trop petit (i.zip)', "broken.zip : ce n'est pas un .zip valide"):
            self.assertIn(att, pb)
        self.assertEqual(len(pb), 5, txt)

    def test_problemes_d_import_en_anglais(self):
        with en('en'): nj, ne, copie, pb = self.problemes()
        self.assertEqual((nj, ne), (1, 0))
        for att in ('data4.dat: size 5 instead of 15360 (i.zip)', 'data2.dat: damaged file (checksum mismatch) (i.zip)', 'data3.dat: not a game adventure log (unknown header) (i.zip)',
                    'etat_01.dqs: file too small (i.zip)', 'broken.zip: not a valid .zip file'):
            self.assertIn(att, pb)
        for p in pb: self.assertFalse(francais(p), p)

    def test_aucun_fichier_reconnu(self):
        self.zipper(**{'lisez_moi.txt': b'x'})
        with en('fr'): m = self.erreur(SA.importer, [self.zip], self.ecr, self.d.mobile)
        self.assertEqual(m, 'Aucun fichier de sauvegarde reconnu (data1.dat a data5.dat, data9.dat ou etats/etat_NN.dqs attendus).')
        with en('en'): m = self.erreur(SA.importer, [self.zip], self.ecr, self.d.mobile)
        self.assertEqual(m, 'No save file recognized (expected data1.dat to data5.dat, data9.dat or etats/etat_NN.dqs).')

    def test_ecriture_impossible(self):
        self.zipper(**{'data1.dat': journal(2)})
        for code, debut, fin in (('fr', 'Aucun fichier n\'a pu etre ecrit (data1.dat : ecriture impossible (', ') ; le fichier actuel est inchange).'),
                                 ('en', 'No file could be written (data1.dat: could not be written (', '); the current file is unchanged).')):
            with en(code), mock.patch.object(SA, 'ecrire_atomique', return_value=OSError('verrouille')):
                m = self.erreur(SA.importer, [self.zip], self.ecr, self.d.mobile)
            self.assertTrue(m.startswith(debut) and m.endswith(fin) and 'verrouille' in m, m)
        self.assertFalse(francais(m.replace('verrouille', '')), m)

    def test_journal_verifier(self):
        faux = FJ.dechiffrer(bytes(FJ.TAILLE_JOURNAL)); abime = bytearray(journal(1)); abime[50] ^= 1
        with en('fr'):
            self.assertEqual(FJ.verifier('data1.dat', faux), "ce n'est pas un journal du jeu (en-tete inconnu)"); self.assertEqual(FJ.verifier('data1.dat', bytes(abime)), 'fichier abime (somme de controle incorrecte)')
        with en('en'):
            self.assertEqual(FJ.verifier('data1.dat', faux), 'not a game adventure log (unknown header)'); self.assertEqual(FJ.verifier('data1.dat', bytes(abime)), 'damaged file (checksum mismatch)')
            self.assertIsNone(FJ.verifier('data1.dat', journal(1)))

    def test_etats_refuses(self):
        import pickle
        piege = pickle.dumps(os.getcwd, protocol=4)
        faux_moteur = types.SimpleNamespace(core=types.SimpleNamespace(uc=None, elf=types.SimpleNamespace(img=b'abc')))
        f = ecrire(os.path.join(self.t, 'pas_un_etat.dqs'), b'DQ4ETATX' + bytes(100))
        attendus = {'fr': ("fichier d'état refusé : il demande « os.getcwd »", "etat d'une autre version (99)",
                           'etat enregistre avec une autre version de la bibliotheque du moteur (APK different) : il ne peut pas etre charge', "ce n'est pas un etat du portage"),
                    'en': ('state file refused: it asks for "posix.getcwd"', 'state from another version (99)',
                           'state saved with another version of the engine library (different APK): it cannot be loaded', 'this is not a state file of this port')}
        for code in ('fr', 'en'):
            with en(code):
                m1 = self.erreur(ET._charger, piege); m2 = self.erreur(ET.appliquer, faux_moteur, {'version': 99})
                m3 = self.erreur(ET.appliquer, faux_moteur, {'version': ET.VERSION, 'lib_sha': 'pas_la_bonne'}); m4 = self.erreur(ET.lire, f)
            self.assertTrue(m1.startswith(attendus[code][0].replace('posix', 'nt') if os.name == 'nt' else attendus[code][0].replace('os.getcwd', 'posix.getcwd') if code == 'fr' else attendus[code][0]), (code, m1))
            self.assertEqual((m2, m3, m4), attendus[code][1:])
            if code == 'en': self.assertFalse(francais(m1) or francais(m2) or francais(m3) or francais(m4), (m1, m2, m3, m4))

    def test_boites_de_dialogue_de_fichiers(self):
        """Les types de fichiers des boites « Enregistrer sous » / « Ouvrir » (tkinter, remplace ici par un faux)."""
        vus = {}
        faux_fd = types.ModuleType('tkinter.filedialog')
        faux_fd.asksaveasfilename = lambda **kw: vus.setdefault('enregistrer', kw['filetypes']) and ''
        faux_fd.askopenfilenames = lambda **kw: vus.setdefault('ouvrir', kw['filetypes']) and ()
        class Tk:
            def withdraw(self): pass
            def attributes(self, *a): pass
            def destroy(self): pass
        faux_tk = types.ModuleType('tkinter'); faux_tk.Tk = Tk; faux_tk.filedialog = faux_fd
        attendus = {'fr': {'enregistrer': [('Archive zip', '*.zip')], 'ouvrir': [('Sauvegardes (zip, data*.dat, etat_*.dqs)', '*.zip *.dat *.dqs'), ('Tous les fichiers', '*.*')]},
                    'en': {'enregistrer': [('Zip archive', '*.zip')], 'ouvrir': [('Saves (zip, data*.dat, etat_*.dqs)', '*.zip *.dat *.dqs'), ('All files', '*.*')]}}
        import time
        for code in ('fr', 'en'):
            vus.clear()
            with en(code), mock.patch.dict(sys.modules, {'tkinter': faux_tk, 'tkinter.filedialog': faux_fd}):
                for mode in ('enregistrer', 'ouvrir'):
                    dlg = SA.Dialogue(mode, 'titre'); t0 = time.time()
                    while dlg.resultat is None and time.time() - t0 < 5: time.sleep(0.01)
                    self.assertEqual(dlg.resultat, [], dlg.erreur)
            self.assertEqual(vus, attendus[code])


# ======================================================================================================================================================
try:
    from dq4_pc.fenetre import jeu as FE, aides as AI, instantanes as INS
    import test_mode_fenetre as TM
except Exception as _ex:
    FE = None


@unittest.skipIf(FE is None, 'fenetre non importable ici')
class Fenetre(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix='lang_fen_'); self.addCleanup(shutil.rmtree, self.t, True); self.addCleanup(LG.regler, 'fr')
        self.log = os.environ['DQ_JOURNAL_FENETRE'] = os.path.join(self.t, 'journaux', 'erreurs_fenetre.log'); self.addCleanup(os.environ.pop, 'DQ_JOURNAL_FENETRE', None)
        os.environ.pop('DQ_SIM_ECHEC', None); self.addCleanup(os.environ.pop, 'DQ_SIM_ECHEC', None)

    def journal(self):
        try:
            with open(self.log, encoding='utf-8') as f: return f.read()
        except OSError: return ''

    def faux(self):
        j = types.SimpleNamespace(msgs=[]); j.toast = lambda t, duree=1.8: j.msgs.append(LG.tr(t)); return j                                   # (comme Jeu.toast : le texte est traduit a l'affichage)

    def test_echec_d_etat(self):
        for code, att in (('fr', "Chargement de l'état 3 impossible : OSError('disque')"), ('en', "Loading state 3 failed: OSError('disque')")):
            with en(code):
                j = self.faux(); _, texte = sortie(FE.Jeu._noter_echec_etat, j, LG.tr("Chargement de l'état %d") % 3, OSError('disque'))
            self.assertEqual(j.msgs, [att]); self.assertIn(att + ' ---\n', texte); self.assertTrue(self.journal().endswith(att + ' ---\n'))
        self.assertFalse(francais(j.msgs[0].replace('disque', '')))

    def test_sauvegarde_impossible(self):
        for code, att, entete in (('fr', 'Sauvegarde impossible : le jeu continue (détails dans erreurs_fenetre.log)', 'sauvegarde impossible : data1.dat'),
                                  ('en', 'Save failed: the game continues (details in erreurs_fenetre.log)', 'save failed: data1.dat')):
            with en(code):
                j = self.faux(); core = types.SimpleNamespace(echecs_ecriture=['data1.dat']); _, texte = sortie(FE.Jeu._signaler_echecs_ecriture, j, core)
            self.assertEqual(j.msgs, [att]); self.assertIn(entete, texte); self.assertIn(entete, self.journal())

    def test_memoire_du_moteur_et_reglages_manques(self):
        noter = []
        with mock.patch.object(FE, 'noter_erreur', noter.append):
            for code, memoire, reglage in (('fr', 'memoire du moteur a 98 % (250 Mo sur 256 Mo) ---\n', 'reglage du moteur non applique : a ---\n'),
                                           ('en', 'engine memory at 98 % (250 MB of 256 MB) ---\n', 'engine setting not applied: a ---\n')):
                noter.clear()
                with en(code):
                    j = types.SimpleNamespace(_tas_niveau=0); core = types.SimpleNamespace(tas_utilise=lambda: 250 << 20, TAS_CRITIQUE=240 << 20, TAS_ALERTE=200 << 20, HEAP_SIZE=256 << 20)
                    FE.Jeu._surveiller_tas(j, core)
                    mo = types.SimpleNamespace(crochets_manques=['a']); j2 = types.SimpleNamespace(_crochets_signales=0); FE.Jeu._signaler_crochets_manques(j2, mo)
                self.assertEqual(len(noter), 2); self.assertTrue(noter[0].endswith(memoire), noter[0]); self.assertTrue(noter[1].endswith(reglage), noter[1])
                if code == 'en': self.assertFalse(francais(noter[0]) or francais(noter[1]), noter)

    def test_chargement_du_demarrage(self):
        for code, att in (('fr', ['Chargement du moteur...', 'Chargement de la sauvegarde...', 'Chargement de la carte...']), ('en', ['Loading the engine...', 'Loading the save...', 'Loading the map...'])):
            with en(code):
                j = types.SimpleNamespace(switch_to=lambda: None, clear=lambda: None, flip=lambda: None, dispatch_events=lambda: None)
                _, texte = sortie(lambda: [FE.Jeu._attente(j, t) for t in ('Chargement du moteur...', 'Chargement de la sauvegarde...', 'Chargement de la carte...')])
            self.assertEqual(texte.splitlines(), att)

    def test_perte_du_focus_du_son(self):
        def boum(oui): raise OSError('carte son')
        j = types.SimpleNamespace(_pret=True, son=types.SimpleNamespace(perdre_focus=boum), molette=types.SimpleNamespace(annuler=lambda: None), hud=types.SimpleNamespace(croix_lacher=lambda: None, appui=None), appui=None, survol=None,
                                  acc=0.0, t_boucle=None, _camera_oublier=lambda: None, pad=lambda: 0, _tenue=lambda a: False, garde_souris=types.SimpleNamespace(clavier=lambda s: None), souris=(0, 0))
        for code, a1, a2 in (('fr', "Son : pause a la perte du focus impossible (OSError('carte son'))", "Son : reprise au retour du focus impossible (OSError('carte son'))"),
                             ('en', "Sound: pausing on focus loss failed (OSError('carte son'))", "Sound: resuming on focus return failed (OSError('carte son'))")):
            with en(code):
                _, t1 = sortie(FE.Jeu.on_deactivate, j); _, t2 = sortie(FE.Jeu.on_activate, j)
            self.assertEqual((t1.strip(), t2.strip()), (a1, a2))

    def test_preparation_du_cache_dans_la_langue_de_l_outil(self):
        """Le processus a part (monde/donnees.py) ne connait pas reglages.json : le jeu lui passe la langue (DQ4_LANGUE), pas celle de l'ordinateur."""
        for code in ('fr', 'en'):
            appels = []
            with en(code), mock.patch('subprocess.Popen', lambda *a, **kw: appels.append(kw) or types.SimpleNamespace()):
                FE.Jeu._lancer_preparation(types.SimpleNamespace(moteur=types.SimpleNamespace(apk_donnees='x.apk')), 'cache')
            self.assertEqual(appels[0]['env']['DQ4_LANGUE'], code)
        with en('en'), mock.patch('subprocess.Popen', side_effect=OSError('non')), mock.patch('threading.Thread'):
            j = types.SimpleNamespace(moteur=types.SimpleNamespace(apk_donnees='x.apk'), donnees=types.SimpleNamespace(preparer=None), prepa_arret=None)
            _, texte = sortie(FE.Jeu._lancer_preparation, j, 'cache')
        self.assertEqual(texte.strip(), "Cache preparation: separate process failed (OSError('non')), running inside the game.")

    def test_le_processus_de_preparation_parle_la_langue_recue(self):
        """Vrai processus `python -m dq4_pc.monde.donnees` (APK absent : « interrompue »)."""
        cache = os.path.join(self.t, 'cache'); os.makedirs(cache)
        for code, debut in (('fr', 'Preparation du cache interrompue : '), ('en', 'Cache preparation interrupted: ')):
            e = dict(os.environ, DQ4_LANGUE=code, PYTHONDONTWRITEBYTECODE='1')
            r = subprocess.run([sys.executable, '-m', 'dq4_pc.monde.donnees', os.path.join(self.t, 'inexistant.apk'), cache], cwd=RACINE, env=e, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
            self.assertTrue(any(l.startswith(debut) for l in r.stdout.splitlines()), (r.stdout, r.stderr))
        self.assertEqual(r.stdout.splitlines()[0], 'Reading the game data pack (once only, a few seconds)...')

    def test_annuler_le_chargement(self):
        for code, a1, a2 in (('fr', 'Aucun chargement à annuler', 'Chargement annulé'), ('en', 'No load to undo', 'Load undone')):
            with en(code):
                j = self.faux(); j.etat_annul = None; INS.InstantanesMixin.annuler_chargement(j)
                j.etat_annul = {'a': 1}; j._etat_complet = lambda: {'b': 2}; j._appliquer_etat = lambda d: None; INS.InstantanesMixin.annuler_chargement(j)
            self.assertEqual(j.msgs, [a1, a2])

    def test_taille_de_fenetre_trop_grande(self):
        with mock.patch.object(AI, 'zone_utile', lambda: (1904, 1040)):
            for code, modele in (('fr', "Fenêtre 3840 x 2160 trop grande pour l'écran : %d x %d"), ('en', 'Window 3840 x 2160 too large for the screen: %d x %d')):
                with en(code): (nw, nh), texte = sortie(AI.ajuster_taille, 3840, 2160)
                self.assertEqual(texte.strip(), modele % (nw, nh))

    # ---- bascule plein ecran <-> fenetre (fausse fenetre de test_mode_fenetre)
    def fen(self, **k):
        f = TM.FausseFenetre(FE, **k); f._journal_fenetre = types.MethodType(FE.Jeu._journal_fenetre, f); f.get_framebuffer_size = lambda: (f.width, f.height); return f

    def test_echec_de_la_bascule(self):
        with mock.patch.object(FE, 'zone_utile', lambda: (1904, 1040)):
            for code, ligne, entete, lignes in (
                    ('fr', "Plein écran impossible (RuntimeError('echec de set_fullscreen(True)')) : fenêtre conservé", 'passage en plein écran impossible ---',
                     ['fenêtre : plein écran = False, 1280 x 720, ', 'écran de la fenêtre pour pyglet : 1920 x 1080 en (0, 0)', 'moniteurs : 1920 x 1080 en (0, 0) (principal)']),
                    ('en', "Fullscreen failed (RuntimeError('echec de set_fullscreen(True)')): windowed mode kept", 'switch to fullscreen failed ---',
                     ['window: fullscreen = False, 1280 x 720, ', 'window screen according to pyglet: 1920 x 1080 at (0, 0)', 'monitors: 1920 x 1080 at (0, 0) (primary)'])):
                if os.path.exists(self.log): os.remove(self.log)
                f = self.fen(echec='set_fullscreen(True)')
                with en(code): rendu, texte = sortie(f.regler_plein_ecran, True)
                self.assertFalse(rendu)
                self.assertIn(ligne, texte.splitlines())
                for att in [entete] + lignes: self.assertIn(att, texte); self.assertIn(att, self.journal())
                if code == 'en': self.assertFalse(francais(sans_chemins(re.sub(r'Traceback.*?\n(?=\w)', '', texte, flags=re.S))), texte)

    def test_echec_du_retour_en_fenetre(self):
        with mock.patch.object(FE, 'zone_utile', lambda: (1904, 1040)):
            for code, ligne in (('fr', "Fenêtre impossible (RuntimeError('echec de set_fullscreen(False,1280x720)')) : plein écran conservé"),
                                ('en', "Windowed mode failed (RuntimeError('echec de set_fullscreen(False,1280x720)')): fullscreen kept")):
                f = self.fen(plein=True, echec='set_fullscreen(False,1280x720)')
                with en(code): rendu, texte = sortie(f.regler_plein_ecran, False)
                self.assertTrue(rendu); self.assertIn(ligne, texte.splitlines())

    def test_ligne_de_journal_de_la_fenetre(self):
        for code, att in (('fr', 'Fenêtre (création) : fenêtre, 1280 x 720, zone de dessin 1280 x 720, écran 1920 x 1080 (écran 1)'),
                          ('en', 'Window (creation): window, 1280 x 720, drawing area 1280 x 720, screen 1920 x 1080 (screen 1)')):
            f = self.fen()
            with en(code): _, texte = sortie(f._journal_fenetre, 'création')
            self.assertEqual(texte.strip(), att)
        for code, att in (('fr', 'Fenêtre (plein écran) : PLEIN ÉCRAN [INCOHÉRENT : fullscreen=False], '), ('en', 'Window (fullscreen): FULLSCREEN [INCONSISTENT: fullscreen=False], ')):
            f = self.fen(plein=True); f.fullscreen = False; f.mode_fen = 1
            with en(code): _, texte = sortie(f._journal_fenetre, 'plein écran')
            self.assertTrue(texte.startswith(att), texte)
        for code, att in (('fr', 'Fenêtre (1re image du jeu) : état illisible ('), ('en', 'Window (1st game frame): state unreadable (')):
            f = self.fen(); f.screen_ = None; del_f = types.SimpleNamespace()
            with en(code): _, texte = sortie(FE.Jeu._journal_fenetre, del_f, '1re image du jeu')
            self.assertTrue(texte.startswith(att), texte)

    def test_moniteurs_illisibles(self):
        for code, att in (('fr', "Moniteurs illisibles (OSError('plus de moniteurs'))"), ('en', "Monitors unreadable (OSError('plus de moniteurs'))")):
            f = self.fen(); f.display = types.SimpleNamespace(get_screens=lambda: (_ for _ in ()).throw(OSError('plus de moniteurs')))
            with en(code): _, texte = sortie(f._lire_ecrans, True)
            self.assertEqual(texte.strip(), att)

    def test_titre_de_la_fenetre(self):
        self.assertEqual(FE.Jeu.TITRE_FENETRE, 'Dragon Quest IV - portage PC (essai)')           # (constante de module marquee N_ : traduite a la creation de la fenetre)
        with en('en'): self.assertEqual(LG.tr(FE.Jeu.TITRE_FENETRE), 'Dragon Quest IV - PC port (trial)')

    def test_texte_des_slots_en_ligne_de_commande(self):
        """`--slot N` : l'etat du chargement direct, dans les deux langues (les deux phrases entieres du catalogue)."""
        for code, a, b in (('fr', 'sauvegarde 2 chargee : oui', 'sauvegarde 2 chargee : NON (fichier data2.dat introuvable ou invalide dans x)'),
                           ('en', 'save 2 loaded: yes', 'save 2 loaded: NO (file data2.dat not found or invalid in x)')):
            with en(code):
                self.assertEqual(LG.tr('sauvegarde %d chargee : oui') % 2, a); self.assertEqual(LG.tr('sauvegarde %d chargee : NON (fichier data%d.dat introuvable ou invalide dans %s)') % (2, 2, 'x'), b)


# ======================================================================================================================================================
@unittest.skipIf(FE is None, 'moteur non importable ici')
class Moteur(unittest.TestCase):
    """Alertes de version du moteur (Moteur._manque) : un autre APK que celui etudie."""
    def setUp(self):
        import test_crochets_manques as TC
        self.TC = TC; self.addCleanup(LG.regler, 'fr')

    def test_fenetre_des_lieux_et_bouton_parametres(self):
        autre = (self.TC.ORIGINE[0], self.TC.ORIGINE[1], 0x11000120 | (0x555 << 10))
        for code, lieux, bouton in (('fr', "fenetre des lieux non elargie : FieldData::drawSymbol inattendu, les lieux de la carte du monde n'apparaissent que dans la fenetre d'origine",
                                     "bouton Paramètres : comparaison du menu Divers inattendue, le bouton ouvre les reglages d'origine du jeu et non le menu Pause"),
                                    ('en', "places window not widened: unexpected FieldData::drawSymbol, world map places only appear in the original window",
                                     "Settings button: unexpected comparison in the Misc menu, the button opens the game's original settings instead of the Pause menu")):
            with en(code):
                m = self.TC.faux_moteur(autre); _, texte = sortie(m._elargir_symboles); self.assertEqual((texte.strip(), m.crochets_manques), (lieux, [lieux]))
                m = self.TC.faux_moteur(cmp_param=0xd503201f); _, texte = sortie(m.patcher_parametres); self.assertEqual((texte.strip(), m.crochets_manques), (bouton, [bouton]))

    def test_tous_les_installateurs_parlent_la_langue_de_l_outil(self):
        """Un moteur dont les fonctions sont introuvables : chaque installateur le dit, en francais comme avant (`KeyError`) et en anglais sans un mot de francais."""
        def introuvable(n): raise KeyError(n)
        noms = ('_crochets_texte', '_crochets_fondu', '_crochets_niveau', '_crochets_rencontres', '_crochets_horloge_jour', '_crochets_temps_de_jeu', '_crochets_magie', '_detourner_parametres', '_elargir_symboles')
        resultats = {}
        for code in ('fr', 'en'):
            with en(code):
                resultats[code] = []
                for nom in noms:
                    m = self.TC.faux_moteur(); m.core.export = introuvable; sortie(getattr(m, nom)); resultats[code] += m.crochets_manques
        self.assertEqual(len(resultats['fr']), len(resultats['en'])); self.assertGreaterEqual(len(resultats['fr']), len(noms))
        for fr, ang in zip(resultats['fr'], resultats['en']):
            self.assertNotEqual(fr, ang); self.assertFalse(francais(ang), ang)
        self.assertIn('vitesse du texte non installee : KeyError(\'DevInit\')'.split(':')[0], '\n'.join(resultats['fr']))


# ======================================================================================================================================================
@unittest.skipIf(FE is None, 'son non importable ici')
class Son(unittest.TestCase):
    def nouveau(self):
        from dq4_pc import son as SON
        self.SON = SON; lignes, journal, alertes = [], [], []
        with mock.patch.dict(sys.modules, {'pyglet': None, 'soundfile': None}):                                  # ni pyglet ni soundfile : « indisponible »
            s = SON.Son('inexistant.apk', self.tmp, log=lambda *a: lignes.append(' '.join(str(x) for x in a)), journal=journal.append, alerte=alertes.append)
        return s, lignes, journal, alertes

    def setUp(self): self.tmp = tempfile.mkdtemp(prefix='lang_son_'); self.addCleanup(shutil.rmtree, self.tmp, True); self.addCleanup(LG.regler, 'fr')

    def test_son_indisponible(self):
        with en('fr'): s, lignes, _, _ = self.nouveau()
        self.assertEqual(lignes[0], 'Musiques indisponibles : module "soundfile" absent (pip install soundfile). Les bruitages restent actifs.'); self.assertTrue(lignes[1].startswith('Son indisponible ('))
        with en('en'): s, lignes, _, _ = self.nouveau()
        self.assertEqual(lignes[0], 'Music unavailable: "soundfile" module missing (pip install soundfile). Sound effects stay active.'); self.assertTrue(lignes[1].startswith('Sound unavailable ('))
        self.assertFalse(francais(lignes[0]))

    def test_echecs_coupure_et_retablissement(self):
        attendus = {'fr': ["bruitage 5 impossible (OSError('x')), echec 1", "bruitage 5 impossible (OSError('x')), echec 2", "bruitage 5 impossible (OSError('x')), echec 3", 'son interrompu, nouvel essai dans 2 s',
                           "volume de la musique impossible (OSError('v')), note une seule fois", 'son retabli'],
                    'en': ["sound effect 5 failed (OSError('x')), failure 1", "sound effect 5 failed (OSError('x')), failure 2", "sound effect 5 failed (OSError('x')), failure 3", 'sound interrupted, retrying in 2 s',
                           "music volume failed (OSError('v')), logged only once", 'sound restored']}
        alertes_att = {'fr': ['Son interrompu : nouvel essai automatique', 'Son rétabli'], 'en': ['Sound interrupted: automatic retry', 'Sound restored']}
        for code in ('fr', 'en'):
            with en(code):
                s, lignes, journal, alertes = self.nouveau(); lignes.clear()
                for _ in range(3): s._echec(LG.tr('bruitage %d') % 5, OSError('x'))
                s._une_fois(LG.N_('volume de la musique'), OSError('v')); s._une_fois(LG.N_('volume de la musique'), OSError('v'))       # (une seule fois)
                s._succes()
            self.assertEqual(journal, attendus[code]); self.assertEqual(alertes, alertes_att[code])
            self.assertEqual(lignes, [('Sound: ' if code == 'en' else 'Son : ') + t for t in attendus[code]])
        self.assertEqual(lignes[0], 'Sound: sound effect 5 failed (OSError(\'x\')), failure 1')

    def test_musique_et_reprise(self):
        with en('en'):
            s, lignes, journal, alertes = self.nouveau()
            s._echec(LG.tr('musique %d') % 12, OSError('m')); s._une_fois(LG.N_('volume des bruitages'), OSError('b')); s._une_fois(LG.N_('reprise apres la pause'), OSError('p'))
        self.assertEqual(journal, ["music track 12 failed (OSError('m')), failure 1", "sound effects volume failed (OSError('b')), logged only once", "resume after pause failed (OSError('p')), logged only once"])


if __name__ == '__main__':
    unittest.main(verbosity=1)
