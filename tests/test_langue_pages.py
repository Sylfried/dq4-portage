"""Reglage « Langue » (D-238) : cle `langue` de reglages.json (defaut `systeme`, valeur inconnue remplacee), ligne de la page Affichage au-dessus de « Plein écran » (Système / Anglais / Français,
System / English / French en anglais), effet immediat du choix, et traduction par les pages (`Pause._et`). Faux « jeu » du test des pages du menu Pause.

    python3 tests/test_langue_pages.py"""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _chemins
import test_pause_pages as TP
from dq4_pc import langue as LG
from dq4_pc.persistance import reglages as RG


class FauxJeuAffichage(TP.FauxJeu):
    """Le faux jeu des pages, avec ce que la page Affichage lui demande."""
    est_plein = False; mode = 4; resolution_courante = (1280, 720)
    def __init__(self):
        super().__init__(); self.post = type('P', (), {'max_msaa': None})()
    def regler_plein_ecran(self, v): self.est_plein = v
    def resolutions(self): return [(1280, 720), (1920, 1080)]
    def regler_resolution(self, v): self.resolution_courante = v
    def regler_mode(self, v): self.mode = v


def menu(ecran):
    J = FauxJeuAffichage(); p = TP.PA.Pause(J); p.ouvert = True; p.pile = [ecran]
    return J, p


class Cle(unittest.TestCase):
    def test_defaut_et_validation(self):
        self.assertEqual(RG.DEFAUT['langue'], 'systeme')
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, 'reglages.json')
            self.assertEqual(RG.Reglages(p)['langue'], 'systeme')
            for v, att in (('en', 'en'), ('fr', 'fr'), ('systeme', 'systeme'), ('xx', 'systeme'), (7, 'systeme'), (None, 'systeme')):
                with open(p, 'w', encoding='utf-8') as f: json.dump({'langue': v}, f)
                self.assertEqual(RG.Reglages(p)['langue'], att, v)

    def test_enregistree(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, 'reglages.json'); r = RG.Reglages(p); r['langue'] = 'en'; r.enregistrer()
            self.assertEqual(RG.Reglages(p)['langue'], 'en')


class Page(unittest.TestCase):
    def setUp(self): LG.regler('systeme', lecteur=lambda: 0x040C)
    def tearDown(self): LG.regler('fr')

    def test_ligne_au_dessus_de_plein_ecran(self):
        _, p = menu('affichage'); e = p._entrees()
        self.assertEqual([x['l'] for x in e[:2]], ['Langue', 'Plein écran']); self.assertEqual(e[0]['t'], 'choix'); self.assertEqual(e[0]['vals'], ['systeme', 'en', 'fr'])

    def test_noms_en_francais_et_en_anglais(self):
        J, p = menu('affichage'); e = p._entrees()[0]
        self.assertEqual([p._nom_valeur('Langue', v) for v in e['vals']], ['Système', 'Anglais', 'Français'])
        LG.regler('en')
        self.assertEqual([LG.tr(p._nom_valeur('Langue', v)) for v in e['vals']], ['System', 'English', 'French']); self.assertEqual(LG.tr('Langue'), 'Language')

    def test_systeme_suit_la_langue_de_l_ordinateur(self):
        J, p = menu('affichage'); self.assertEqual(J.reg['langue'], 'systeme')
        LG.regler(J.reg['langue'], lecteur=lambda: 0x0409); self.assertEqual(LG.courante(), 'en')
        LG.regler(J.reg['langue'], lecteur=lambda: 0x080C); self.assertEqual(LG.courante(), 'fr')

    def test_le_choix_s_applique_tout_de_suite_et_se_garde(self):
        J, p = menu('affichage'); e = p._entrees()[0]
        e['plus'](); self.assertEqual(J.reg['langue'], 'en'); self.assertEqual(LG.courante(), 'en')           # systeme -> en
        e['plus'](); self.assertEqual(J.reg['langue'], 'fr'); self.assertEqual(LG.courante(), 'fr')           # en -> fr
        e['moins'](); self.assertEqual(LG.courante(), 'en')

    def test_valeur_par_defaut_de_la_ligne(self):
        J, p = menu('affichage'); e = p._entrees()[0]; e['plus'](); self.assertFalse(e['est_defaut']()); e['defaut'](); self.assertEqual(J.reg['langue'], 'systeme'); self.assertTrue(e['est_defaut']())

    def test_les_pages_traduisent_ce_qu_elles_dessinent(self):
        J, p = menu('affichage')
        vus = []
        J._etiq = lambda texte, taille, couleur=None, polices=(): vus.append(texte) or type('E', (), {'content_width': 10.0})()
        p._et('Langue', 12.0); LG.regler('en'); p._et('Langue', 12.0); p._et('Texte sans traduction', 12.0)
        self.assertEqual(vus, ['Langue', 'Language', 'Texte sans traduction'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
