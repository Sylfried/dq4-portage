"""Reglage « Langue » (D-238) : cle `language` de reglages.json (defaut `system`, valeur inconnue remplacee), ligne de la page Affichage au-dessus de « Plein écran » (Système / Anglais / Français,
System / English / French en anglais), effet immediat du choix, et traduction par les pages (`Pause._label`). Faux « jeu » du test des pages du menu Pause.

    python3 tests/test_page_language.py"""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _paths
import test_pause_pages as TP
from dq4_pc import language as LG
from dq4_pc.persistence import settings as RG


class FakeGameDisplay(TP.FakeGame):
    """Le faux jeu des pages, avec ce que la page Affichage lui demande."""
    is_fullscreen = False; mode = 4; current_resolution = (1280, 720)
    def __init__(self):
        super().__init__(); self.post = type('P', (), {'max_msaa': None})()
    def set_full_screen(self, v): self.is_fullscreen = v
    def resolutions(self): return [(1280, 720), (1920, 1080)]
    def set_resolution(self, v): self.current_resolution = v
    def set_mode(self, v): self.mode = v


def menu(screen_page):
    J = FakeGameDisplay(); p = TP.PA.Pause(J); p.opened = True; p.stack = [screen_page]
    return J, p


class Key(unittest.TestCase):
    def test_default_and_validation(self):
        self.assertEqual(RG.DEFAULT['langue'], 'systeme')
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, 'reglages.json')
            self.assertEqual(RG.Settings(p)['langue'], 'systeme')
            for v, att in (('en', 'en'), ('fr', 'fr'), ('systeme', 'systeme'), ('xx', 'systeme'), (7, 'systeme'), (None, 'systeme')):
                with open(p, 'w', encoding='utf-8') as f: json.dump({'langue': v}, f)
                self.assertEqual(RG.Settings(p)['langue'], att, v)

    def test_enregistree(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, 'reglages.json'); r = RG.Settings(p); r['langue'] = 'en'; r.store()
            self.assertEqual(RG.Settings(p)['langue'], 'en')


class Page(unittest.TestCase):
    def setUp(self): LG.select_language('systeme', reader=lambda: 0x040C)
    def tearDown(self): LG.select_language('fr')

    def test_line_above_full_screen(self):
        _, p = menu('affichage'); e = p._entries()
        self.assertEqual([x['l'] for x in e[:2]], ['Langue', 'Plein écran']); self.assertEqual(e[0]['t'], 'choix'); self.assertEqual(e[0]['vals'], ['systeme', 'en', 'fr'])

    def test_names_in_french_and_english(self):
        J, p = menu('affichage'); e = p._entries()[0]
        self.assertEqual([p._value_name('Langue', v) for v in e['vals']], ['Système', 'Anglais', 'Français'])
        LG.select_language('en')
        self.assertEqual([LG.tr(p._value_name('Langue', v)) for v in e['vals']], ['System', 'English', 'French']); self.assertEqual(LG.tr('Langue'), 'Language')

    def test_system_follows_the_computer_language(self):
        J, p = menu('affichage'); self.assertEqual(J.reg['langue'], 'systeme')
        LG.select_language(J.reg['langue'], reader=lambda: 0x0409); self.assertEqual(LG.current_language(), 'en')
        LG.select_language(J.reg['langue'], reader=lambda: 0x080C); self.assertEqual(LG.current_language(), 'fr')

    def test_choice_applies_immediately_and_is_kept(self):
        J, p = menu('affichage'); e = p._entries()[0]
        e['plus'](); self.assertEqual(J.reg['langue'], 'en'); self.assertEqual(LG.current_language(), 'en')           # systeme -> en
        e['plus'](); self.assertEqual(J.reg['langue'], 'fr'); self.assertEqual(LG.current_language(), 'fr')           # en -> fr
        e['moins'](); self.assertEqual(LG.current_language(), 'en')

    def test_default_value_of_the_line(self):
        J, p = menu('affichage'); e = p._entries()[0]; e['plus'](); self.assertFalse(e['est_defaut']()); e['defaut'](); self.assertEqual(J.reg['langue'], 'systeme'); self.assertTrue(e['est_defaut']())

    def test_pages_translate_what_they_draw(self):
        J, p = menu('affichage')
        seen = []
        J._lbl = lambda text, size_value, color=None, fonts=(): seen.append(text) or type('E', (), {'content_width': 10.0})()
        p._label('Langue', 12.0); LG.select_language('en'); p._label('Langue', 12.0); p._label('Texte sans traduction', 12.0)
        self.assertEqual(seen, ['Langue', 'Language', 'Texte sans traduction'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
