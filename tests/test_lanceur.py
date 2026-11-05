"""lancer_dq4.bat : la console se ferme avec la fenetre du jeu (D-236). Le fichier est lu comme du texte (sans Windows) : apres la ligne qui lance le jeu, `pause` n'est permis que dans le bloc
« si le code de sortie n'est pas 0 » (le jeu s'est arrete sur une erreur : on laisse le message lisible), et le lanceur rend le code de sortie du jeu. Fins de ligne CRLF conservees.

    python3 tests/test_lanceur.py"""
import os, sys, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
BAT = os.path.join(ICI, '..', 'lancer_dq4.bat')


def lignes():
    with open(BAT, 'rb') as f: brut = f.read()
    return brut, brut.decode('latin-1').split('\r\n')


class Lanceur(unittest.TestCase):
    def test_fins_de_ligne_windows(self):
        brut, _ = lignes()
        self.assertNotIn(b'\n', brut.replace(b'\r\n', b''), 'un saut de ligne seul (LF) casse les etiquettes et les blocs de cmd.exe')

    def test_la_console_se_ferme_avec_le_jeu(self):
        _, l = lignes()
        i = max(k for k, x in enumerate(l) if '-m dq4_pc' in x)                                          # la ligne qui lance le jeu
        apres = l[i + 1:]
        self.assertTrue(any(x.strip().startswith('set "CODE=%errorlevel%"') for x in apres[:2]), 'le code de sortie du jeu doit etre lu tout de suite')
        niveau = 0; dans_erreur = False
        for x in apres:
            t = x.strip()
            if t.startswith('if not "%CODE%"=="0" ('): dans_erreur = True; niveau = 1; continue
            if dans_erreur:
                niveau += t.count('(') - t.count(')') if not t.startswith('echo') else 0
                if t == ')': dans_erreur = False
                continue
            self.assertNotEqual(t.lower(), 'pause', 'une pause hors du bloc d\'erreur garderait la console ouverte apres la fermeture du jeu')
        self.assertTrue(any(x.strip() == 'pause' for x in apres), 'sur une erreur, la console doit rester pour qu\'on lise le message')
        self.assertEqual(apres[-2].strip() if apres[-1] == '' else apres[-1].strip(), 'exit /b %CODE%')

    def test_les_pauses_d_avant_le_lancement_sont_des_erreurs_de_preparation(self):
        _, l = lignes()
        i = max(k for k, x in enumerate(l) if '-m dq4_pc' in x)
        for k, x in enumerate(l[:i]):
            if x.strip().lower() == 'pause':                                                              # chaque pause d'avant suit un message d'echec (Python introuvable, installation...) ou un « exit /b 1 »
                contexte = ' '.join(l[max(0, k - 6):k + 2]).lower()
                self.assertTrue('exit /b 1' in contexte or 'echo' in contexte, 'pause sans message : ligne %d' % (k + 1))


if __name__ == '__main__':
    unittest.main(verbosity=1)
