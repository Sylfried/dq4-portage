"""Plus de petit message en haut de l'ecran (#267, demande de Sylfried du 04/11/2026, 22 h 14 : « Enleve le message de notification en haut de l'ecran pour le changement de vitesse [...] toutes les notifications tout
court finalement, celles qui apparaissent en haut de l'ecran »).

  1. le code ne contient plus aucune notification (`toast`, `toasts`) : ni la methode, ni l'etat, ni le dessin, ni un appel ;
  2. les echecs qu'elles annoncaient (etat instantane non enregistre ou non charge) restent dans la console et dans le journal des erreurs (`Jeu._noter_echec_etat`) ;
  3. changer la vitesse de combat ne montre rien (et rend la nouvelle vitesse).

    python3 tests/test_sans_notifications.py
"""
import os, re, shutil, sys, tempfile, types, unittest

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, RACINE)


class Code(unittest.TestCase):
    def test_aucune_notification_dans_le_code(self):
        trouves = []
        for dossier, _d, fichiers in os.walk(os.path.join(RACINE, 'dq4_pc')):
            for nom in fichiers:
                if not nom.endswith('.py'): continue
                with open(os.path.join(dossier, nom), encoding='utf-8') as f:
                    for i, l in enumerate(f, 1):
                        if re.search(r'\btoasts?\b', l): trouves.append('%s:%d' % (nom, i))
        self.assertEqual(trouves, [])


class Comportement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: from dq4_pc.fenetre import jeu as F
        except Exception as ex: raise unittest.SkipTest('fenetre non importable ici (%r)' % (ex,))
        cls.F = F

    def test_jeu_n_a_plus_de_notification(self):
        self.assertFalse(hasattr(self.F.Jeu, 'toast')); self.assertFalse(hasattr(self.F.Jeu, 'toasts'))

    def test_echec_d_etat_dans_la_console_et_le_journal(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        os.environ['DQ_JOURNAL_FENETRE'] = os.path.join(d, 'journaux', 'erreurs_fenetre.log'); self.addCleanup(os.environ.pop, 'DQ_JOURNAL_FENETRE', None)
        self.F.Jeu._noter_echec_etat(types.SimpleNamespace(), "Chargement de l'état 3", OSError('disque'))
        with open(os.environ['DQ_JOURNAL_FENETRE'], encoding='utf-8') as f: txt = f.read()
        self.assertIn("Chargement de l'état 3 impossible", txt); self.assertIn('disque', txt)


if __name__ == '__main__':
    unittest.main()
