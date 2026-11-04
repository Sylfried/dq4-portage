"""#208 (audit UI-03) : `TextMesh.tabSize` : une tabulation `\\t` d'un texte de menu vaut `tabSize` espaces, dans TOUTES les cellules qui en portent un (avant : liste des magies seulement).
Cas reels : « Nv. » de l'ordre de marche (type 20, tabSize 8), « x N » des plaques de groupe en combat (type 31, tabSize 25). Sans moteur ni fenetre ; avec la police du jeu (DQ_UI_CACHE : dossier de ui_garrir.json / .png), « x2 » a « x9 » tiennent dans la plaque.
    python3 tests/test_tabulation_menu.py"""
import os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.menus import ui_menu as UM
CACHE_POLICE = os.environ.get('DQ_UI_CACHE', '/tmp/audit_final/interface/uicache')


def type_tab(tab_size, nom='Make_Test()'):
    """Une plaque et son texte (cellule (0, 0), tabSize donne) ; code 0 (« plaque de monstre ») : -1 montre la plaque, 1 le texte."""
    carre = {'vtx': [[-71.0, 18.0], [71.0, 18.0], [71.0, -18.0], [-71.0, -18.0]], 'uv': [[0, 0], [1, 0], [1, 1], [0, 1]], 'sub': {'0': [0, 1, 2, 0, 2, 3]}}
    return {'name': nom, 'err': None,
            'nodes': [{'id': 1, 'par': None, 'pos': [0.0, 0.0, 0.0], 'act': True, 'mats': []},
                      {'id': 10, 'par': 1, 'pos': [0.0, 4.0, 0.0], 'act': True, 'mats': [], 'mesh': carre},
                      {'id': 11, 'par': 10, 'pos': [-60.0, 8.0, 8.0], 'act': True, 'text': {'font': 'font', 'characterSize': 10.0, 'text': None, 'tabSize': tab_size}, 'mats': []}],
            'parts': [{'node': 11, 'ib': [{'k': 'text', 'go': 11, 'variant': 0}]}],
            'params': [{'id': 0, 'no': 0, 'parts': 0, 'base': 0}],
            'codes': [{'id': 0, 'kind': 'func', 'fx': {'-1': {'d': {'10': {'act': False}}}, '1': {'d': {'11': {'act': True}}}}}], 'builds': []}


def fenetre(tab_size, nom='Make_Test()'):
    ml = types.SimpleNamespace(types={'99': type_tab(tab_size, nom)}, infos=[], cadres=[], hdr={'lang': {'hiro': 1.0}}, pousse=(0.0, 0.0))
    return UM.Fenetre(ml, 99)


class Tabuler(unittest.TestCase):
    def test_remplacement(self):
        self.assertEqual(UM.tabuler('a\tb', 8), 'a' + ' ' * 8 + 'b'); self.assertEqual(UM.tabuler('\t×2', 25), ' ' * 25 + '×2')
        self.assertEqual(UM.tabuler('a\t\tb', 2), 'a    b'); self.assertEqual(UM.tabuler('a\tb', 7.6), 'a' + ' ' * 8 + 'b')

    def test_sans_tabsize_ou_sans_tabulation_inchange(self):
        for ts in (None, 0, 0.0): self.assertEqual(UM.tabuler('a\tb', ts), 'a\tb')
        self.assertEqual(UM.tabuler('abc', 8), 'abc'); self.assertEqual(UM.tabuler('', 8), ''); self.assertIsNone(UM.tabuler(None, 8))


class CellulesDeMenu(unittest.TestCase):
    def test_param_str_hors_liste_des_magies(self):                       # type 20 « Ordre de marche » : avant, seule la liste des magies (Make_NameButton) etait traitee
        fe = fenetre(8); self.assertFalse(fe.noms_liste)
        fe.param_str(0, 0, '\tNv.: 5'); self.assertEqual(fe.N[11]['text']['text'], ' ' * 8 + 'Nv.: 5')

    def test_param_str_liste_des_magies_inchangee(self):
        fe = fenetre(8, 'Make_NameButton(test)'); self.assertTrue(fe.noms_liste)
        fe.param_str(0, 0, 'Coût en PM:\t  2'); self.assertEqual(fe.N[11]['text']['text'], 'Coût en PM:' + ' ' * 8 + '  2')

    def test_cellule_sans_tabsize_garde_la_tabulation(self):
        fe = fenetre(None); fe.param_str(0, 0, 'a\tb'); self.assertEqual(fe.N[11]['text']['text'], 'a\tb')

    def test_plaque_de_groupe(self):                                       # type 31 : « nom \n \t×N », tabSize 25
        fe = fenetre(25); fe.plaque(0, 'Gluant\n\t×2', [0, 0, 0, 0, 0], 1)
        self.assertEqual(fe.N[11]['text']['text'], 'Gluant\n' + ' ' * 25 + '×2')
        fe.plaque(0, 'Gluant', [0, 0, 0, 0, 0], 1); self.assertEqual(fe.N[11]['text']['text'], 'Gluant')          # un seul monstre : pas de tabulation, rien ne change


@unittest.skipUnless(os.path.exists(os.path.join(CACHE_POLICE, 'ui_garrir.json')), 'police du jeu absente (ui_garrir.json)')
class AvecLaPolice(unittest.TestCase):
    def test_fois_n_tient_dans_la_plaque_jusqu_a_neuf(self):
        pol = UM.PoliceBitmap(os.path.join(CACHE_POLICE, 'ui_garrir.json'), os.path.join(CACHE_POLICE, 'ui_garrir.png'))
        px = 9.3925 * 0.1                                                  # Make_MonsterName : caractere de taille 9,3925 (1 px de police = cs * 0,1 unite), texte ancre a gauche en x = -74, plaque de -71 a +71
        for n in ('\u00d72', '\u00d75', '\u00d79'):                    # (\u00d710 et plus : fin vers x = 79, 8 unites au-dela du bord, comme avec les memes constantes dans Unity : suppose, voir #208)
            fin = -74.0 + pol.largeur(UM.tabuler('\t' + n, 25)) * px
            self.assertLess(fin, 71.0, (n, fin))                           # « x N » finit dans la plaque (a gauche : tabulation ignoree, ca finissait vers -63)


if __name__ == '__main__': unittest.main(verbosity=1)
