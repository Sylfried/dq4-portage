"""launch_dq4.bat : la console se ferme avec la fenetre du jeu (D-236) ; messages en francais ou en anglais selon la langue de Windows (D-238). Le fichier est lu comme du texte (sans Windows) : apres la ligne qui lance le jeu, `pause` n'est permis
que dans le bloc « si le code de sortie n'est pas 0 » (le jeu s'est arrete sur une erreur : on laisse le message lisible), et le lanceur rend le code de sortie du jeu. Fins de ligne CRLF conservees. Les messages sont des etiquettes
(`:m_xxx_fr` / `:m_xxx_en`) en bas du fichier, appelees par `call :m_xxx_%DQLANG%` : chaque appel doit avoir ses deux versions, l'anglaise sans mot francais, et le fichier rester en ASCII.

    python3 tests/test_launcher.py"""
import os, re, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BAT = os.path.join(HERE, '..', 'launch_dq4.bat')


def lines():
    with open(BAT, 'rb') as f: raw_value = f.read()
    return raw_value, raw_value.decode('latin-1').split('\r\n')


def body():
    """Les lignes du lanceur proprement dit : jusqu'a « exit /b %CODE% » (apres, ce ne sont que les etiquettes des messages)."""
    _, l = lines()
    return l[:l.index('exit /b %CODE%') + 1]


def messages():
    """{nom d'etiquette : lignes} pour les etiquettes `:m_...`."""
    _, l = lines(); res = {}; lookup_key = None
    for x in l[l.index('exit /b %CODE%') + 1:]:
        if x.startswith(':m_'): lookup_key = x[1:].strip(); res[lookup_key] = []
        elif lookup_key is not None and x.strip() and not x.lower().startswith('rem'): res[lookup_key].append(x)
    return res


class Launcher(unittest.TestCase):
    def test_windows_line_endings(self):
        raw_value, _ = lines()
        self.assertNotIn(b'\n', raw_value.replace(b'\r\n', b''), 'un saut de ligne seul (LF) casse les etiquettes et les blocs de cmd.exe')

    def test_console_closes_with_game(self):
        l = body()
        i = max(k for k, x in enumerate(l) if '-m dq4_pc' in x and 'import' not in x and '.chemins' not in x)                    # la ligne qui lance le jeu
        after = l[i + 1:]
        self.assertTrue(any(x.strip().startswith('set "CODE=%errorlevel%"') for x in after[:2]), 'le code de sortie du jeu doit etre lu tout de suite')
        level = 0; in_error = False
        for x in after:
            t = x.strip()
            if t.startswith('if not "%CODE%"=="0" ('): in_error = True; level = 1; continue
            if in_error:
                level += t.count('(') - t.count(')') if not t.startswith('echo') else 0
                if t == ')': in_error = False
                continue
            self.assertNotEqual(t.lower(), 'pause', 'une pause hors du bloc d\'erreur garderait la console ouverte apres la fermeture du jeu')
        self.assertTrue(any(x.strip() == 'pause' for x in after), 'sur une erreur, la console doit rester pour qu\'on lise le message')
        self.assertEqual(after[-1].strip(), 'exit /b %CODE%')

    def test_pauses_before_launch_are_preparation_errors(self):
        l = body()
        i = max(k for k, x in enumerate(l) if '-m dq4_pc' in x and 'import' not in x and '.chemins' not in x)
        for k, x in enumerate(l[:i]):
            if x.strip().lower() == 'pause':                                                              # chaque pause d'avant suit un message d'echec (Python introuvable, installation...) ou un « exit /b 1 »
                context_text = ' '.join(l[max(0, k - 6):k + 2]).lower()
                self.assertTrue('exit /b 1' in context_text or 'call :m_' in context_text, 'pause sans message : ligne %d' % (k + 1))

    def test_each_message_is_called_and_returns(self):
        calls = set(re.findall(r'call :(m_\w+)', ' '.join(x for x in body() if not x.lower().startswith('rem'))))
        m = messages()
        self.assertGreaterEqual(len(calls), 10)
        for a in calls: self.assertIn(a, m, 'message sans etiquette : ' + a)
        for lookup_key in m:
            self.assertIn(lookup_key, calls, 'etiquette jamais appelee : ' + lookup_key)
            self.assertEqual(m[lookup_key][-1].strip(), 'exit /b', 'l\'etiquette %s doit rendre la main (exit /b)' % lookup_key)

    def test_no_language_detection(self):
        l = ' '.join(x for x in lines()[1] if not x.lower().startswith('rem'))
        for word in ('PreferredUILanguages', 'LocaleName', 'DQLANG', '_fr', '_en'): self.assertNotIn(word, l, 'les messages du lanceur sont en anglais seulement : ' + word)

    def test_messages_are_in_english(self):
        french = re.compile(r"\b(le|la|les|une?|des|du|est|sont|vient|refait|erreur|jeu|dossier|ici|relance|installe|echec|echoue|seule|fois|lit|tes|ton|menus simples|pour|depuis|puis|cette|coche|supprime|lance|lecture|creation|reprise|environnement|fenetres|dans|avec|sans|sur|ou)\b|'", re.I)
        for lookup_key, lg in messages().items():
            for x in lg:
                if x.strip().lower().startswith('title'): x = x[5:]
                remainder = re.sub(r'"[^"]*"|\^\(|\^\)|\b[\w\\.]+\.(bat|log|py)\b|data\\\S*|donnees\\\S*|dq4_pc\\\S*|DQ4_DATA|tools\\\S*', '', x)             # chemins et noms propres exclus
                self.assertIsNone(french.search(remainder), 'mot francais dans %s : %s' % (lookup_key, x.strip()))

    def test_ascii_only(self):
        raw_value, _ = lines()
        raw_value.decode('ascii')                                                                                # la console Windows n'affiche pas les accents sans reglage : pas d'octet hors ASCII


if __name__ == '__main__':
    unittest.main(verbosity=1)
