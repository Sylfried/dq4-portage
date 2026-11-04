"""#198 (audit ENG-02) : ecriture des sauvegardes du moteur : atomique, et une erreur d'E/S ne plante plus le jeu.
Lancer depuis la racine : PYGLET_HEADLESS=1 python3 tests/test_ecriture_sauvegarde.py"""
import os, sys, tempfile, types, unittest, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dq4_pc.noyau import moteur as MO


def faux_coeur(chemin, donnees=b'abc'):
    c = object.__new__(MO.CoreJeu)                                   # sans __init__ : pas de bibliotheque ni d'emulateur pour tester l'ecriture
    c.files = {0x100: {'d': bytearray(donnees), 'persist': chemin, 'pos': 0, 'w': True, 'name': 'x'}}
    return c


class Ecriture(unittest.TestCase):
    def setUp(self): self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d, True)

    def test_ecriture_normale_sans_fichier_temporaire(self):
        ch = os.path.join(self.d, 'sous', 'data1.dat'); c = faux_coeur(ch, b'0123456789')
        c.h_fclose(0x100)
        self.assertEqual(open(ch, 'rb').read(), b'0123456789')
        self.assertEqual(os.listdir(os.path.dirname(ch)), ['data1.dat'])          # le .tmp a disparu
        self.assertFalse(c.echecs_ecriture)

    def test_remplace_l_ancien_fichier(self):
        ch = os.path.join(self.d, 'data1.dat'); open(ch, 'wb').write(b'ancien')
        faux_coeur(ch, b'nouveau').h_fclose(0x100)
        self.assertEqual(open(ch, 'rb').read(), b'nouveau')

    def test_erreur_d_ecriture_garde_l_ancien_fichier_et_ne_plante_pas(self):
        ch = os.path.join(self.d, 'data1.dat'); open(ch, 'wb').write(b'ancien')
        c = faux_coeur(ch, b'nouveau')
        vrai = os.replace
        def refuse(a, b): raise PermissionError('verrouille par un antivirus')
        os.replace = refuse
        try: c.h_fclose(0x100)                                                       # aucune exception
        finally: os.replace = vrai
        self.assertEqual(open(ch, 'rb').read(), b'ancien')                           # intact
        self.assertEqual(os.listdir(self.d), ['data1.dat'])                           # pas de .tmp qui traine
        self.assertEqual(len(c.echecs_ecriture), 1); self.assertIn('data1.dat', c.echecs_ecriture[0]); self.assertIn('antivirus', c.echecs_ecriture[0])
        self.assertNotIn(0x100, c.files)                                              # le fichier est ferme quand meme (comme avant)

    def test_deuxieme_essai_reussit(self):
        ch = os.path.join(self.d, 'data1.dat'); vrai = os.replace; n = []
        def une_fois(a, b):
            n.append(1)
            if len(n) == 1: raise PermissionError('verrou passager')
            return vrai(a, b)
        os.replace = une_fois
        try: err = MO.CoreJeu.ecrire_atomique(ch, b'ok', essais=2, pause=0.0)
        finally: os.replace = vrai
        self.assertIsNone(err); self.assertEqual(open(ch, 'rb').read(), b'ok'); self.assertEqual(len(n), 2)

    def test_dossier_impossible_a_creer(self):
        fichier = os.path.join(self.d, 'fichier'); open(fichier, 'wb').close()
        err = MO.CoreJeu.ecrire_atomique(os.path.join(fichier, 'data1.dat'), b'x', essais=1)       # « fichier » n'est pas un dossier
        self.assertIsInstance(err, OSError)


class Fenetre(unittest.TestCase):
    def test_signalement_dans_le_journal_et_message(self):
        try: from dq4_pc.fenetre import jeu as F
        except Exception as ex: raise unittest.SkipTest('fenetre non importable ici (%r)' % (ex,))
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        os.environ['DQ_JOURNAL_FENETRE'] = os.path.join(d, 'journaux', 'erreurs_fenetre.log')
        self.addCleanup(os.environ.pop, 'DQ_JOURNAL_FENETRE', None)
        j = types.SimpleNamespace()                                                   # (sans `toast` : depuis #267 aucun message a l'ecran, seulement la console et le journal)
        core = types.SimpleNamespace(echecs_ecriture=["data1.dat : PermissionError('x')"])
        F.Jeu._signaler_echecs_ecriture(j, core)
        self.assertIsNone(core.echecs_ecriture)                                       # vide : un seul message par echec
        with open(os.environ['DQ_JOURNAL_FENETRE'], encoding='utf-8') as f: txt = f.read()
        self.assertIn('data1.dat', txt); self.assertIn('sauvegarde impossible', txt)


if __name__ == '__main__': unittest.main(verbosity=1)
