"""lancer_dq4.bat : la console se ferme avec la fenetre du jeu (D-236) ; messages en francais ou en anglais selon la langue de Windows (D-238). Le fichier est lu comme du texte (sans Windows) : apres la ligne qui lance le jeu, `pause` n'est permis
que dans le bloc « si le code de sortie n'est pas 0 » (le jeu s'est arrete sur une erreur : on laisse le message lisible), et le lanceur rend le code de sortie du jeu. Fins de ligne CRLF conservees. Les messages sont des etiquettes
(`:m_xxx_fr` / `:m_xxx_en`) en bas du fichier, appelees par `call :m_xxx_%DQLANG%` : chaque appel doit avoir ses deux versions, l'anglaise sans mot francais, et le fichier rester en ASCII.

    python3 tests/test_lanceur.py"""
import os, re, sys, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
BAT = os.path.join(ICI, '..', 'lancer_dq4.bat')


def lignes():
    with open(BAT, 'rb') as f: brut = f.read()
    return brut, brut.decode('latin-1').split('\r\n')


def corps():
    """Les lignes du lanceur proprement dit : jusqu'a « exit /b %CODE% » (apres, ce ne sont que les etiquettes des messages)."""
    _, l = lignes()
    return l[:l.index('exit /b %CODE%') + 1]


def messages():
    """{nom d'etiquette : lignes} pour les etiquettes `:m_...`."""
    _, l = lignes(); res = {}; cle = None
    for x in l[l.index('exit /b %CODE%') + 1:]:
        if x.startswith(':m_'): cle = x[1:].strip(); res[cle] = []
        elif cle is not None and x.strip() and not x.lower().startswith('rem'): res[cle].append(x)
    return res


class Lanceur(unittest.TestCase):
    def test_fins_de_ligne_windows(self):
        brut, _ = lignes()
        self.assertNotIn(b'\n', brut.replace(b'\r\n', b''), 'un saut de ligne seul (LF) casse les etiquettes et les blocs de cmd.exe')

    def test_la_console_se_ferme_avec_le_jeu(self):
        l = corps()
        i = max(k for k, x in enumerate(l) if '-m dq4_pc' in x and 'import' not in x and '.chemins' not in x)                    # la ligne qui lance le jeu
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
        self.assertEqual(apres[-1].strip(), 'exit /b %CODE%')

    def test_les_pauses_d_avant_le_lancement_sont_des_erreurs_de_preparation(self):
        l = corps()
        i = max(k for k, x in enumerate(l) if '-m dq4_pc' in x and 'import' not in x and '.chemins' not in x)
        for k, x in enumerate(l[:i]):
            if x.strip().lower() == 'pause':                                                              # chaque pause d'avant suit un message d'echec (Python introuvable, installation...) ou un « exit /b 1 »
                contexte = ' '.join(l[max(0, k - 6):k + 2]).lower()
                self.assertTrue('exit /b 1' in contexte or 'call :m_' in contexte, 'pause sans message : ligne %d' % (k + 1))

    def test_chaque_message_a_ses_deux_langues(self):
        appels = set(re.findall(r'call :(m_\w+?)_%DQLANG%', ' '.join(x for x in corps() if not x.lower().startswith('rem'))))
        m = messages()
        self.assertGreaterEqual(len(appels), 10)
        for a in appels:
            self.assertIn(a + '_fr', m, 'message sans version francaise : ' + a); self.assertIn(a + '_en', m, 'message sans version anglaise : ' + a)
        for cle in m:
            self.assertIn(re.sub(r'_(fr|en)$', '', cle), appels, 'etiquette jamais appelee : ' + cle)
            self.assertEqual(m[cle][-1].strip(), 'exit /b', 'l\'etiquette %s doit rendre la main (exit /b)' % cle)
        for a in appels:
            fr, en = m[a + '_fr'], m[a + '_en']
            self.assertEqual(len(fr), len(en), 'meme nombre de lignes dans les deux langues : ' + a)
            self.assertEqual([x.strip().split(' ')[0] for x in fr], [x.strip().split(' ')[0] for x in en], 'meme commande a chaque ligne : ' + a)
            self.assertEqual(sorted(re.findall(r'%\d|\^\(code', ' '.join(fr))), sorted(re.findall(r'%\d|\^\(code', ' '.join(en))), 'memes arguments : ' + a)

    def test_la_langue_vient_de_windows(self):
        l = corps()
        self.assertTrue(any('PreferredUILanguages' in x for x in l) and any('LocaleName' in x for x in l), 'langue d\'affichage de Windows, puis format regional en secours')
        self.assertTrue(any(x.strip() == 'set "DQLANG=en"' for x in l), 'anglais par defaut')
        self.assertTrue(any('"fr"' in x and 'DQLANG=fr' in x for x in l), 'francais si Windows est en francais')

    def test_les_messages_anglais_sont_en_anglais(self):
        francais = re.compile(r"\b(le|la|les|une?|des|du|est|sont|vient|refait|erreur|jeu|dossier|ici|relance|installe|echec|echoue|seule|fois|lit|tes|ton|menus simples|pour|depuis|puis|cette|coche|supprime|lance|lecture|creation|reprise|environnement|fenetres|dans|avec|sans|sur|ou)\b|'", re.I)
        for cle, lg in messages().items():
            if not cle.endswith('_en'): continue
            for x in lg:
                if x.strip().lower().startswith('title'): x = x[5:]
                reste = re.sub(r'"[^"]*"|\^\(|\^\)|\b[\w\\.]+\.(bat|log|py)\b|donnees\\\S*|dq4_pc\\\S*|DQ4_DONNEES|outils\\\S*', '', x)             # chemins et noms propres exclus
                self.assertIsNone(francais.search(reste), 'mot francais dans %s : %s' % (cle, x.strip()))

    def test_ascii_seulement(self):
        brut, _ = lignes()
        brut.decode('ascii')                                                                                # la console Windows n'affiche pas les accents sans reglage : pas d'octet hors ASCII


if __name__ == '__main__':
    unittest.main(verbosity=1)
