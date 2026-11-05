"""Langue de l'outil (language.py, D-238), sans fenetre ni moteur : detection de la langue de l'ordinateur (francais quelle que soit la variante, sinon anglais), reglage, `tr` / `N_`,
lecture du reglage dans reglages.json, et regles du catalogue anglais (texts_en\\) : memes trous (%d, %s...), memes espaces aux bords, pas de francais dans l'anglais, pas de doublon,
chaque texte litteral passe a `tr(...)` / `N_(...)` dans le code a sa traduction.

    python3 tests/test_language.py"""
import ast, json, os, re, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, ROOT)
from dq4_pc import language as LG

ACCENTS = re.compile('[àâäçéèêëîïôöùûüÿœÀÂÇÉÈÊËÎÏÔÙÛÜŒ]')
FRENCH_WORDS = {'le', 'la', 'les', 'des', 'du', 'une', 'et', 'ou', 'pour', 'dans', 'sur', 'avec', 'sans', 'est', 'pas', 'ces', 'aux', 'vos', 'votre', 'tes', 'tous', 'toutes', 'quand', 'comme', 'mais', 'donc', 'sont', 'chaque', 'sinon', 'aucun', 'aucune'}
TROUS = re.compile(r'%[-+ #0]*\d*(?:\.\d+)?[sdifgxXrc%]|\{[^{}]*\}')


def french(text):
    """Le texte contient une lettre accentuee ou un mot-outil francais."""
    if ACCENTS.search(text): return True
    return any(m in FRENCH_WORDS for m in re.findall(r"[a-zA-Z']+", text.lower().replace("'", ' ')))


def catalog_by_file():
    import importlib
    return {name_str: importlib.import_module('dq4_pc.texts_en.' + name_str).EN for name_str in LG.MODULES_EN}


class Detection(unittest.TestCase):
    def test_windows_all_french_variants(self):
        for code in (0x040C, 0x080C, 0x0C0C, 0x100C, 0x140C, 0x180C):                       # France, Belgique, Canada, Suisse, Luxembourg, Monaco
            self.assertEqual(LG.system_language(lambda c=code: c), 'fr', hex(code))

    def test_windows_other_languages_give_english(self):
        for code in (0x0409, 0x0809, 0x0407, 0x0411, 0x0C0A, 0x0410, 0x0416, 0x0419, 0x0804):    # anglais US / GB, allemand, japonais, espagnol, italien, portugais, russe, chinois
            self.assertEqual(LG.system_language(lambda c=code: c), 'en', hex(code))

    def test_locales_as_text(self):
        for t in ('fr_FR.UTF-8', 'fr', 'fr_BE', 'fr-CA', 'French_France', 'fr_CH@euro'):
            self.assertEqual(LG.system_language(lambda t=t: t), 'fr', t)
        for t in ('en_US.UTF-8', 'C', 'POSIX', '', None, 'de_DE', 'fra', 'frisian', 'fi_FI'):              # (« fra », « frisian » : pas le francais)
            self.assertEqual(LG.system_language(lambda t=t: t), 'en', repr(t))

    def test_read_failure_gives_english(self):
        def outage(): raise OSError('pas de langue')
        self.assertEqual(LG.system_language(outage), 'en')


class Setting(unittest.TestCase):
    def tearDown(self): LG.select_language('fr')

    def test_choice(self):
        self.assertEqual(LG.CHOICES, ('systeme', 'en', 'fr'))
        self.assertEqual(LG.select_language('fr', reader=lambda: 0x0409), 'fr'); self.assertEqual(LG.current_language(), 'fr')
        self.assertEqual(LG.select_language('en', reader=lambda: 0x040C), 'en'); self.assertEqual(LG.requested(), 'en')
        self.assertEqual(LG.select_language('systeme', reader=lambda: 0x040C), 'fr'); self.assertEqual(LG.select_language('systeme', reader=lambda: 0x0409), 'en'); self.assertEqual(LG.requested(), 'systeme')

    def test_unknown_value_treated_as_system(self):
        self.assertEqual(LG.select_language('klingon', reader=lambda: 0x0409), 'en'); self.assertEqual(LG.requested(), 'systeme')
        self.assertEqual(LG.select_language(None, reader=lambda: 0x040C), 'fr')

    def test_read_setting_from_file(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, 'settings.json')
            self.assertEqual(LG.read_setting(p), 'systeme')                                                 # absent
            for v, att in (('fr', 'fr'), ('en', 'en'), ('systeme', 'systeme'), ('xx', 'systeme'), (3, 'systeme')):
                with open(p, 'w', encoding='utf-8') as f: json.dump({'langue': v}, f)
                self.assertEqual(LG.read_setting(p), att, v)
            with open(p, 'w', encoding='utf-8') as f: json.dump({'son': True}, f)
            self.assertEqual(LG.read_setting(p), 'systeme')                                                 # cle absente
            with open(p, 'w', encoding='utf-8') as f: f.write('{pas du json')
            self.assertEqual(LG.read_setting(p), 'systeme')                                                 # illisible


class Traduction(unittest.TestCase):
    def setUp(self): self.saved = LG._catalog; LG._catalog = {'Bonjour': 'Hello', '%d fichier(s)': '%d file(s)', 'Oui': 'Yes'}
    def tearDown(self): LG._catalog = self.saved; LG.select_language('fr')

    def test_french_unchanged(self):
        LG.select_language('fr')
        for t in ('Bonjour', 'Texte sans traduction', '', '%d fichier(s)'): self.assertEqual(LG.tr(t), t)

    def test_anglais(self):
        LG.select_language('en')
        self.assertEqual(LG.tr('Bonjour'), 'Hello'); self.assertEqual(LG.tr('%d fichier(s)') % 3, '3 file(s)')

    def test_without_translation_stays_french_without_error(self):
        LG.select_language('en'); self.assertEqual(LG.tr('Texte inconnu'), 'Texte inconnu')

    def test_non_text_passes_through_unchanged(self):
        LG.select_language('en')
        for v in (None, 3, 1.5, ('a', 'b'), True): self.assertEqual(LG.tr(v), v)

    def test_N_marks_without_changing(self):
        LG.select_language('en'); self.assertEqual(LG.N_('Bonjour'), 'Bonjour'); self.assertEqual(LG.tr(LG.N_('Bonjour')), 'Hello')

    def test_language_change_is_immediate(self):
        LG.select_language('en'); self.assertEqual(LG.tr('Oui'), 'Yes'); LG.select_language('fr'); self.assertEqual(LG.tr('Oui'), 'Oui'); LG.select_language('en'); self.assertEqual(LG.tr('Oui'), 'Yes')


class Catalog(unittest.TestCase):
    """Regles du catalogue anglais (tous les fichiers de texts_en\\)."""
    def test_files_and_types(self):
        for name_str, c in catalog_by_file().items():
            self.assertIsInstance(c, dict, name_str)
            for fr, entry in c.items():
                self.assertTrue(isinstance(fr, str) and isinstance(entry, str) and fr.strip() and entry.strip(), '%s : %r -> %r' % (name_str, fr, entry))

    def test_no_duplicate_between_files(self):
        seen = {}
        for name_str, c in catalog_by_file().items():
            for fr in c:
                self.assertNotIn(fr, seen, '« %s » est dans %s et dans %s' % (fr, seen.get(fr), name_str)); seen[fr] = name_str

    def test_same_placeholders_and_same_edges(self):
        for name_str, c in catalog_by_file().items():
            for fr, entry in c.items():
                self.assertEqual(TROUS.findall(fr), TROUS.findall(entry), '%s : trous differents : %r -> %r' % (name_str, fr, entry))
                self.assertEqual((fr[:len(fr) - len(fr.lstrip())], fr[len(fr.rstrip()):]), (entry[:len(entry) - len(entry.lstrip())], entry[len(entry.rstrip()):]), '%s : espaces aux bords : %r -> %r' % (name_str, fr, entry))
                self.assertEqual(fr.count('\n'), entry.count('\n'), '%s : retours a la ligne : %r' % (name_str, fr))

    def test_no_french_in_english(self):
        for name_str, c in catalog_by_file().items():
            for fr, entry in c.items():
                if entry == fr: self.assertFalse(french(fr), '%s : « %s » est du francais laisse tel quel' % (name_str, fr)); continue
                self.assertFalse(french(entry), '%s : de l\'anglais avec du francais : %r -> %r' % (name_str, fr, entry))

    def test_tr_literal_texts_have_translation(self):
        category = {}
        for c in catalog_by_file().values(): category.update(c)
        missing_items = []
        for d, _, fs in os.walk(os.path.join(ROOT, 'dq4_pc')):
            for f in fs:
                if not f.endswith('.py') or f == 'language.py': continue
                p = os.path.join(d, f)
                with open(p, encoding='utf-8') as fh: tree = ast.parse(fh.read())
                for n in ast.walk(tree):
                    if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute)) and (getattr(n.func, 'id', None) or getattr(n.func, 'attr', None)) in ('tr', 'N_') \
                       and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                        t = n.args[0].value
                        if t not in category and (ACCENTS.search(t) or french(t)): missing_items.append('%s:%d %r' % (os.path.relpath(p, ROOT), n.lineno, t))
        self.assertEqual(missing_items, [], 'textes passes a tr() / N_() sans traduction')


if __name__ == '__main__':
    unittest.main(verbosity=1)
