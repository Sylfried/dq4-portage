"""Test de la logique pure de la plaque « Sauvegarde automatique » du menu de depart (type 53), sans fenetre ni moteur :

  1. etats d'un bouton (MenuParts.BUTTON_STATE_*) : normal et enfonce reagissent, invisible / grise / inverse ne reagissent pas (IButton : le test de contact est coupe) ;
  2. disponibilite de la sauvegarde auto : le code 0 du moteur (1 = data5.dat valide, 0 = absent) l'emporte ; sans code, l'etiquette envoyee par le moteur tranche ;
  3. `Window.auto_plate` : plaque TOUJOURS visible avec son etiquette ; sans sauvegarde auto elle est grisee (etat 3) et sort des zones tactiles (`buttons` : ni clic, ni survol, ni validation au clavier) ;
     des que la sauvegarde auto existe : etat normal, etiquette du moteur, zone tactile ; les autres plaques (Continuer...) ne sont pas touchees ; l'ancien comportement (plaque cachee) reste disponible (DQ_AUTO_CACHEE).

    python3 tools/test_start_menu_plate.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.menus import ui_menu as UM


def initial_type():
    """Mise en page minimale du menu de depart : deux plaques (Continuer = bouton 0, Sauvegarde automatique = bouton 4), chacune avec son etiquette."""
    square = {'vtx': [[-100.0, 10.0], [100.0, 10.0], [100.0, -10.0], [-100.0, -10.0]], 'uv': [[0, 0], [1, 0], [1, 1], [0, 1]], 'sub': {'0': [0, 1, 2, 0, 2, 3]}}
    def plate(nid, button, z): return {'id': nid, 'par': 1, 'pos': [0.0, 4.0, z], 'act': True, 'mats': [{'sheet': 1, 'part': 7, 'color': [1, 1, 1, 1], 'shader': 'parts', 'offset': None}], 'mesh': square, 'parts': {'buttonId': button, 'gamepad': 16}}
    def text(nid, parent_idx): return {'id': nid, 'par': parent_idx, 'pos': [0.0, 8.0, -8.0], 'act': True, 'text': {'font': 'font', 'characterSize': 10.0, 'text': None}, 'mats': []}
    return {'name': 'Make_StartMenuSecond()', 'err': None,
            'nodes': [{'id': 1, 'par': None, 'pos': [0.0, 0.0, 0.0], 'act': True, 'mats': []}, plate(10, 4, 60.0), text(11, 10), plate(20, 0, 0.0), text(21, 20)],
            'parts': [{'node': 10, 'ib': [{'k': 'button'}, {'k': 'text', 'go': 11, 'variant': 0}]}, {'node': 20, 'ib': [{'k': 'button'}, {'k': 'text', 'go': 21, 'variant': 0}]}],
            'params': [{'id': 4, 'no': 0, 'parts': 0, 'base': 0}, {'id': 4, 'no': 1, 'parts': 0, 'base': 1}, {'id': 0, 'no': 0, 'parts': 1, 'base': 0}, {'id': 0, 'no': 1, 'parts': 1, 'base': 1}],
            'codes': [], 'builds': []}


def window():
    ml = types.SimpleNamespace(types={'53': initial_type()}, info=[], borders=[], hdr={'lang': {'hiro': 1.0}}, pushed=(0.0, 0.0))
    return UM.Window(ml, 53)


def text(wnd, nid): return wnd.N[nid]['text']['text']
def zones(wnd): return sorted(b[0] for b in wnd.buttons())


class TestStates(unittest.TestCase):
    def test_active_state(self):
        self.assertTrue(UM.is_state_active(UM.STATE_NORMAL)); self.assertTrue(UM.is_state_active(UM.STATE_PRESSED))
        for e in (UM.STATE_INVISIBLE, UM.STATE_GRAYED, UM.STATE_INVERTED): self.assertFalse(UM.is_state_active(e), e)
        self.assertEqual((UM.STATE_NORMAL, UM.STATE_PRESSED, UM.STATE_INVISIBLE, UM.STATE_GRAYED, UM.STATE_INVERTED), (0, 1, 2, 3, 4))      # MenuParts.BUTTON_STATE_*

    def test_availability(self):
        self.assertTrue(UM.auto_plate_available(1, '')); self.assertFalse(UM.auto_plate_available(0, 'Sauvegarde automatique'))      # le code 0 l'emporte
        self.assertTrue(UM.auto_plate_available(None, 'Sauvegarde automatique')); self.assertFalse(UM.auto_plate_available(None, '')); self.assertFalse(UM.auto_plate_available(None, '  ')); self.assertFalse(UM.auto_plate_available(None, None))


class TestAutoPlate(unittest.TestCase):
    def setUp(self): os.environ.pop('DQ_AUTO_CACHEE', None)

    def test_without_autosave_grayed_and_inactive(self):
        wnd = window(); wnd.code(0, 0)                                                                   # le moteur : pas de data5.dat, pas d'etiquette (4, 1)
        for _ in range(3): wnd.auto_plate()                                                              # idempotent : appelee a chaque image
        pl = wnd.N[10]
        self.assertTrue(pl['act']); self.assertEqual(text(wnd, 11), UM.AUTO_CAPTION)                      # visible, avec son etiquette
        self.assertEqual(pl['etat'], UM.STATE_GRAYED)                                                      # grisee
        self.assertNotIn(4, zones(wnd)); self.assertIn(0, zones(wnd))                                       # inactive : plus de zone tactile ; Continuer, lui, reste actif

    def test_with_normal_autosave(self):
        wnd = window(); wnd.param_str(4, 1, 'Sauvegarde automatique'); wnd.code(0, 1); wnd.auto_plate()
        self.assertEqual(wnd.N[10]['etat'], UM.STATE_NORMAL); self.assertTrue(wnd.N[10]['act']); self.assertIn(4, zones(wnd))

    def test_engine_label_kept(self):
        wnd = window(); wnd.param_str(4, 1, 'Reprendre le dernier point'); wnd.code(0, 1); wnd.auto_plate()
        self.assertEqual(text(wnd, 11), 'Reprendre le dernier point')                                  # on ne remplace jamais l'etiquette envoyee par le moteur

    def test_save_appears_afterwards(self):
        wnd = window(); wnd.code(0, 0); wnd.auto_plate(); self.assertEqual(wnd.N[10]['etat'], UM.STATE_GRAYED)
        wnd.param_str(4, 1, 'Sauvegarde automatique (nouvelle)'); wnd.code(0, 1); wnd.auto_plate()           # data5.dat apparait : le moteur renvoie code et etiquette
        self.assertEqual(wnd.N[10]['etat'], UM.STATE_NORMAL); self.assertIn(4, zones(wnd)); self.assertEqual(text(wnd, 11), 'Sauvegarde automatique (nouvelle)'); self.assertFalse(wnd.auto_grayed)

    def test_then_vanishes(self):
        wnd = window(); wnd.param_str(4, 1, 'Sauvegarde automatique'); wnd.code(0, 1); wnd.auto_plate(); wnd.code(0, 0); wnd.auto_plate()
        self.assertEqual(wnd.N[10]['etat'], UM.STATE_GRAYED); self.assertNotIn(4, zones(wnd)); self.assertTrue(text(wnd, 11))

    def test_without_code_the_label_decides(self):
        wnd = window(); wnd.auto_plate(); wnd.auto_plate()                                                # ni code ni etiquette : grisee (et notre etiquette de remplacement ne la « valide » pas a l'image suivante)
        self.assertEqual(wnd.N[10]['etat'], UM.STATE_GRAYED); self.assertNotIn(4, zones(wnd))
        wnd.param_str(4, 1, 'Reprise automatique'); wnd.auto_plate()                                       # etiquette du moteur (differente de la notre) sans code : disponible
        self.assertEqual(wnd.N[10]['etat'], UM.STATE_NORMAL); self.assertIn(4, zones(wnd))

    def test_other_plates_intact(self):
        wnd = window(); wnd.param_str(0, 1, 'Continuer votre aventure'); wnd.param_int(0, 0, UM.STATE_GRAYED); wnd.code(0, 0); wnd.auto_plate()
        self.assertEqual(wnd.N[20]['etat'], UM.STATE_GRAYED); self.assertEqual(text(wnd, 21), 'Continuer votre aventure'); self.assertNotIn(0, zones(wnd))      # une plaque grisee par le moteur (aucune banque) : meme regle

    def test_gray_text_of_grayed_plates(self):
        wnd = window(); wnd.param_str(0, 1, 'Continuer'); wnd.param_int(0, 0, UM.STATE_GRAYED); wnd.code(0, 0); wnd.auto_plate()
        self.assertEqual(wnd.N[21]['tcol'], UM.TEXT_GRAY); self.assertEqual(wnd.N[11]['tcol'], UM.TEXT_GRAY)                # Continuer (grise par le moteur) et Sauvegarde automatique (grisee par la visionneuse)
        wnd.param_int(0, 0, UM.STATE_NORMAL); wnd.auto_plate(); self.assertEqual(wnd.N[21]['tcol'], 0); self.assertEqual(wnd.N[11]['tcol'], UM.TEXT_GRAY)
        wnd.param_str(4, 1, 'Sauvegarde automatique'); wnd.code(0, 1); wnd.auto_plate(); self.assertEqual(wnd.N[11]['tcol'], 0)    # la sauvegarde auto existe : texte normal

    def test_state_sent_by_engine(self):
        wnd = window(); wnd.param_int(0, 0, UM.STATE_NORMAL); self.assertIn(0, zones(wnd))
        for state, expected in ((UM.STATE_PRESSED, True), (UM.STATE_INVISIBLE, False), (UM.STATE_GRAYED, False), (UM.STATE_INVERTED, False), (UM.STATE_NORMAL, True)):
            wnd.param_int(0, 0, state); self.assertEqual(0 in zones(wnd), expected, state)

    def test_original_behavior_on_request(self):
        os.environ['DQ_AUTO_CACHEE'] = '1'
        try:
            wnd = window(); wnd.code(0, 0); wnd.auto_plate()
            self.assertFalse(wnd.N[10]['act']); self.assertNotIn(4, zones(wnd))                              # le jeu d'origine cache la plaque
        finally: os.environ.pop('DQ_AUTO_CACHEE', None)


if __name__ == '__main__':
    unittest.main()
