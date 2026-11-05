"""Langue de l'outil (langue.py, D-238), sans fenetre ni moteur : detection de la langue de l'ordinateur (francais quelle que soit la variante, sinon anglais), reglage, `tr` / `N_`,
lecture du reglage dans reglages.json, et regles du catalogue anglais (textes_en\\) : memes trous (%d, %s...), memes espaces aux bords, pas de francais dans l'anglais, pas de doublon,
chaque texte litteral passe a `tr(...)` / `N_(...)` dans le code a sa traduction.

    python3 tests/test_langue.py"""
import ast, json, os, re, sys, tempfile, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.join(ICI, '..')
sys.path.insert(0, RACINE)
from dq4_pc import langue as LG

ACCENTS = re.compile('[àâäçéèêëîïôöùûüÿœÀÂÇÉÈÊËÎÏÔÙÛÜŒ]')
MOTS_FRANCAIS = {'le', 'la', 'les', 'des', 'du', 'une', 'et', 'ou', 'pour', 'dans', 'sur', 'avec', 'sans', 'est', 'pas', 'ces', 'aux', 'vos', 'votre', 'tes', 'tous', 'toutes', 'quand', 'comme', 'mais', 'donc', 'sont', 'chaque', 'sinon', 'aucun', 'aucune'}
TROUS = re.compile(r'%[-+ #0]*\d*(?:\.\d+)?[sdifgxXrc%]|\{[^{}]*\}')


def francais(texte):
    """Le texte contient une lettre accentuee ou un mot-outil francais."""
    if ACCENTS.search(texte): return True
    return any(m in MOTS_FRANCAIS for m in re.findall(r"[a-zA-Z']+", texte.lower().replace("'", ' ')))


def catalogue_par_fichier():
    import importlib
    return {nom: importlib.import_module('dq4_pc.textes_en.' + nom).EN for nom in LG.MODULES_EN}


class Detection(unittest.TestCase):
    def test_windows_toutes_les_variantes_du_francais(self):
        for code in (0x040C, 0x080C, 0x0C0C, 0x100C, 0x140C, 0x180C):                       # France, Belgique, Canada, Suisse, Luxembourg, Monaco
            self.assertEqual(LG.langue_du_systeme(lambda c=code: c), 'fr', hex(code))

    def test_windows_les_autres_langues_donnent_l_anglais(self):
        for code in (0x0409, 0x0809, 0x0407, 0x0411, 0x0C0A, 0x0410, 0x0416, 0x0419, 0x0804):    # anglais US / GB, allemand, japonais, espagnol, italien, portugais, russe, chinois
            self.assertEqual(LG.langue_du_systeme(lambda c=code: c), 'en', hex(code))

    def test_locales_en_texte(self):
        for t in ('fr_FR.UTF-8', 'fr', 'fr_BE', 'fr-CA', 'French_France', 'fr_CH@euro'):
            self.assertEqual(LG.langue_du_systeme(lambda t=t: t), 'fr', t)
        for t in ('en_US.UTF-8', 'C', 'POSIX', '', None, 'de_DE', 'fra', 'frisian', 'fi_FI'):              # (« fra », « frisian » : pas le francais)
            self.assertEqual(LG.langue_du_systeme(lambda t=t: t), 'en', repr(t))

    def test_lecture_impossible_donne_l_anglais(self):
        def panne(): raise OSError('pas de langue')
        self.assertEqual(LG.langue_du_systeme(panne), 'en')


class Reglage(unittest.TestCase):
    def tearDown(self): LG.regler('fr')

    def test_choix(self):
        self.assertEqual(LG.CHOIX, ('systeme', 'en', 'fr'))
        self.assertEqual(LG.regler('fr', lecteur=lambda: 0x0409), 'fr'); self.assertEqual(LG.courante(), 'fr')
        self.assertEqual(LG.regler('en', lecteur=lambda: 0x040C), 'en'); self.assertEqual(LG.demande(), 'en')
        self.assertEqual(LG.regler('systeme', lecteur=lambda: 0x040C), 'fr'); self.assertEqual(LG.regler('systeme', lecteur=lambda: 0x0409), 'en'); self.assertEqual(LG.demande(), 'systeme')

    def test_valeur_inconnue_comme_systeme(self):
        self.assertEqual(LG.regler('klingon', lecteur=lambda: 0x0409), 'en'); self.assertEqual(LG.demande(), 'systeme')
        self.assertEqual(LG.regler(None, lecteur=lambda: 0x040C), 'fr')

    def test_lire_reglage_dans_le_fichier(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, 'reglages.json')
            self.assertEqual(LG.lire_reglage(p), 'systeme')                                                 # absent
            for v, att in (('fr', 'fr'), ('en', 'en'), ('systeme', 'systeme'), ('xx', 'systeme'), (3, 'systeme')):
                with open(p, 'w', encoding='utf-8') as f: json.dump({'langue': v}, f)
                self.assertEqual(LG.lire_reglage(p), att, v)
            with open(p, 'w', encoding='utf-8') as f: json.dump({'son': True}, f)
            self.assertEqual(LG.lire_reglage(p), 'systeme')                                                 # cle absente
            with open(p, 'w', encoding='utf-8') as f: f.write('{pas du json')
            self.assertEqual(LG.lire_reglage(p), 'systeme')                                                 # illisible


class Traduction(unittest.TestCase):
    def setUp(self): self.sauve = LG._catalogue; LG._catalogue = {'Bonjour': 'Hello', '%d fichier(s)': '%d file(s)', 'Oui': 'Yes'}
    def tearDown(self): LG._catalogue = self.sauve; LG.regler('fr')

    def test_francais_inchange(self):
        LG.regler('fr')
        for t in ('Bonjour', 'Texte sans traduction', '', '%d fichier(s)'): self.assertEqual(LG.tr(t), t)

    def test_anglais(self):
        LG.regler('en')
        self.assertEqual(LG.tr('Bonjour'), 'Hello'); self.assertEqual(LG.tr('%d fichier(s)') % 3, '3 file(s)')

    def test_sans_traduction_reste_en_francais_sans_erreur(self):
        LG.regler('en'); self.assertEqual(LG.tr('Texte inconnu'), 'Texte inconnu')

    def test_ce_qui_n_est_pas_un_texte_passe_tel_quel(self):
        LG.regler('en')
        for v in (None, 3, 1.5, ('a', 'b'), True): self.assertEqual(LG.tr(v), v)

    def test_N_marque_sans_changer(self):
        LG.regler('en'); self.assertEqual(LG.N_('Bonjour'), 'Bonjour'); self.assertEqual(LG.tr(LG.N_('Bonjour')), 'Hello')

    def test_le_changement_de_langue_est_immediat(self):
        LG.regler('en'); self.assertEqual(LG.tr('Oui'), 'Yes'); LG.regler('fr'); self.assertEqual(LG.tr('Oui'), 'Oui'); LG.regler('en'); self.assertEqual(LG.tr('Oui'), 'Yes')


class Catalogue(unittest.TestCase):
    """Regles du catalogue anglais (tous les fichiers de textes_en\\)."""
    def test_fichiers_et_types(self):
        for nom, c in catalogue_par_fichier().items():
            self.assertIsInstance(c, dict, nom)
            for fr, en in c.items():
                self.assertTrue(isinstance(fr, str) and isinstance(en, str) and fr.strip() and en.strip(), '%s : %r -> %r' % (nom, fr, en))

    def test_pas_de_doublon_entre_fichiers(self):
        vus = {}
        for nom, c in catalogue_par_fichier().items():
            for fr in c:
                self.assertNotIn(fr, vus, '« %s » est dans %s et dans %s' % (fr, vus.get(fr), nom)); vus[fr] = nom

    def test_memes_trous_et_memes_bords(self):
        for nom, c in catalogue_par_fichier().items():
            for fr, en in c.items():
                self.assertEqual(TROUS.findall(fr), TROUS.findall(en), '%s : trous differents : %r -> %r' % (nom, fr, en))
                self.assertEqual((fr[:len(fr) - len(fr.lstrip())], fr[len(fr.rstrip()):]), (en[:len(en) - len(en.lstrip())], en[len(en.rstrip()):]), '%s : espaces aux bords : %r -> %r' % (nom, fr, en))
                self.assertEqual(fr.count('\n'), en.count('\n'), '%s : retours a la ligne : %r' % (nom, fr))

    def test_pas_de_francais_dans_l_anglais(self):
        for nom, c in catalogue_par_fichier().items():
            for fr, en in c.items():
                if en == fr: self.assertFalse(francais(fr), '%s : « %s » est du francais laisse tel quel' % (nom, fr)); continue
                self.assertFalse(francais(en), '%s : de l\'anglais avec du francais : %r -> %r' % (nom, fr, en))

    def test_les_textes_litteraux_de_tr_ont_leur_traduction(self):
        cat = {}
        for c in catalogue_par_fichier().values(): cat.update(c)
        manques = []
        for d, _, fs in os.walk(os.path.join(RACINE, 'dq4_pc')):
            for f in fs:
                if not f.endswith('.py') or f == 'langue.py': continue
                p = os.path.join(d, f)
                with open(p, encoding='utf-8') as fh: arbre = ast.parse(fh.read())
                for n in ast.walk(arbre):
                    if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute)) and (getattr(n.func, 'id', None) or getattr(n.func, 'attr', None)) in ('tr', 'N_') \
                       and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                        t = n.args[0].value
                        if t not in cat and (ACCENTS.search(t) or francais(t)): manques.append('%s:%d %r' % (os.path.relpath(p, RACINE), n.lineno, t))
        self.assertEqual(manques, [], 'textes passes a tr() / N_() sans traduction')


if __name__ == '__main__':
    unittest.main(verbosity=1)
