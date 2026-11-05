"""Le don d'experience du roi (chapitre 1) fige le jeu au dernier message de niveau (#261).

Le menu `MaterielMenu_EXTRA_PRESENT_EXP` (ajout du mobile) attend, une fois les niveaux montres, un declenchement du pad du jeu (`dss::g_Pad + 2`, rempli par `Global::NativeExec` d'apres le 2e argument de `GameUpdate`) :
le toucher d'ecran exactement 0x100, ou les boutons 0x400 a 0x2000. La touche A d'un message (0x10) ne le leve jamais.

  1. `Engine.awaits_touch` (sans moteur : la memoire est simulee) : vrai seulement si le menu est dans le tableau du gestionnaire de menus ET a son dernier etat ;
  2. `inputs.touch_for_engine` : A envoie 0x100 seul quand le menu attend, rien ne change sinon ;
  3. un modele de `Global::NativeExec + 0x74` (code machine relu) montre pourquoi 0x10 et 0x110 ne suffisent pas et 0x100 ou 0x400 oui ;
  4. branchement : `Game._entries` appelle bien la conversion quand un message est ouvert (le test lit le code, sans pyglet).

    python3 tests/test_exp_gift_touch.py
"""
import os, sys, types, unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
from dq4_pc.window import inputs as EN
from dq4_pc.core import engine as ENGINE

A, B, TALK = 0x10, 0x20, 0x100          # (touches du portage ; toucher d'ecran, voir fenetre/constantes.BTN_TALK)
L = 0x10000000


def game_pad(decl):
    """g_Pad + 2 d'apres le 2e argument de GameUpdate (Global::NativeExec + 0x38 a + 0x74) : les bits 10 a 13 de `decl` (decalages -5, -5, -5, -3, masques 0x20, 0x40, 0x80, 0x400), plus 0x10 quand
    `decl & 0x7fff` vaut exactement 0x100 (le toucher)."""
    v = ((decl >> 5) & 0x20) | ((decl >> 5) & 0x40) | ((decl >> 5) & 0x80) | ((decl >> 3) & 0x400)
    return v | (0x10 if (decl & 0x7fff) == 0x100 else 0)


def mock_engine(opened=True, state=2, place=0, manager=True, crash=False):
    """Un moteur dont seule `mem` existe : gestionnaire de menus a GES, tableau de 8 pointeurs a GES + 8, menu du don d'experience a L + 0x24c730 (etat a + 0x30)."""
    GES = L + 0x300000; menu = L + ENGINE.MENU_GIFT_EXP
    m = {}
    m[(L + ENGINE.MENU_MANAGER, 8)] = (GES if manager else 0).to_bytes(8, 'little')
    for i in range(8): m[(GES + 8 + 8 * i, 8)] = (menu if (opened and i == place) else L + 0x2000 + i).to_bytes(8, 'little')      # (les autres cases : d'autres menus)
    m[(menu + ENGINE.MENU_GIFT_EXP_STATE, 1)] = bytes([state])
    def mem(ad, n):
        if crash: raise RuntimeError('memoire illisible')
        return m[(ad, n)]
    return types.SimpleNamespace(core=types.SimpleNamespace(mem=mem), L=L)


def is_waiting(eng): return ENGINE.Engine.awaits_touch(eng)


class MenuDetection(unittest.TestCase):
    def test_opened_at_last_state(self): self.assertTrue(is_waiting(mock_engine()))

    def test_all_cells_of_the_array(self):
        for i in range(8): self.assertTrue(is_waiting(mock_engine(place=i)), i)

    def test_other_menu_states(self):
        for state in (0, 1, 3): self.assertFalse(is_waiting(mock_engine(state=state)), state)          # comptage de l'experience, niveaux, ... : A tourne les pages du message comme d'habitude

    def test_menu_closed_even_if_state_remained_at_2(self):
        self.assertFalse(is_waiting(mock_engine(opened=False)))                                    # l'etat reste a 2 apres la fermeture : sans le tableau, chaque message suivant du jeu recevrait le toucher au lieu de A

    def test_without_manager(self): self.assertFalse(is_waiting(mock_engine(manager=False)))

    def test_unreadable_memory(self): self.assertFalse(is_waiting(mock_engine(crash=True)))      # jamais d'exception dans la boucle des touches

    def test_game_addresses(self):
        self.assertEqual((ENGINE.MENU_MANAGER, ENGINE.MENU_GIFT_EXP, ENGINE.MENU_GIFT_EXP_STATE, ENGINE.MENU_GIFT_EXP_WAIT, ENGINE.OPENED_MENUS), (0x252078, 0x24c730, 0x30, 2, 8))      # MenuManager::execute et gMaterielMenu_EXTRA_PRESENT_EXP (relus dans la bibliotheque)


class KeyConversion(unittest.TestCase):
    def test_a_becomes_touch_only(self):
        p, decl = EN.touch_for_engine(A | 0x1, A, A, B, TALK, True)
        self.assertEqual(decl, TALK); self.assertEqual(p, 0x1)                               # A et B retires des touches tenues, la direction reste
        p, decl = EN.touch_for_engine(A | B, A | B, A, B, TALK, True)
        self.assertEqual((p, decl), (0, TALK))                                               # exactement 0x100 : 0x110 ne passerait pas

    def test_without_wait_nothing_changes(self):
        for p, decl in ((A, A), (0, 0), (B, B), (A | 0x4, A | 0x4)): self.assertEqual(EN.touch_for_engine(p, decl, A, B, TALK, False), (p, decl))

    def test_another_key_does_not_trigger(self):
        self.assertEqual(EN.touch_for_engine(0x4, 0x4, A, B, TALK, True), (0x4, 0x4))        # une direction, B seul : seul A (ou clic, Entree, Espace qui deviennent A) vaut un toucher
        self.assertEqual(EN.touch_for_engine(B, B, A, B, TALK, True), (B, B))


class GamePad(unittest.TestCase):
    def test_why_a_was_not_enough(self):
        self.assertEqual(game_pad(A), 0)                    # touche A : g_Pad + 2 reste nul, le menu attend sans fin (le blocage)
        self.assertEqual(game_pad(A | TALK), 0)           # 0x110 non plus : le toucher doit etre seul
        self.assertEqual(game_pad(0), 0)
        self.assertEqual(game_pad(TALK), 0x10)            # le toucher de l'ecran : il passe
        self.assertEqual(game_pad(0x400), 0x20); self.assertEqual(game_pad(0x800), 0x40); self.assertEqual(game_pad(0x1000), 0x80); self.assertEqual(game_pad(0x2000), 0x400)

    def test_conversion_lifts_the_wait(self):
        p, decl = EN.touch_for_engine(A, A, A, B, TALK, True)
        self.assertNotEqual(game_pad(decl), 0)


class Wiring(unittest.TestCase):
    def test_inputs_calls_the_conversion(self):
        """Game._entrees (fenetre/keyboard_mouse.py, a besoin de pyglet : lu comme du texte) envoie A au moteur apres la conversion, seulement quand un message est ouvert (sur le terrain, A = parler, deja 0x100)."""
        with open(os.path.join(ROOT, 'dq4_pc', 'window', 'keyboard_mouse.py'), encoding='utf-8') as f: src = f.read()
        self.assertIn('from dq4_pc.window import inputs as EN', src)
        line = [l for l in src.split('\n') if 'EN.touch_for_engine(' in l]
        self.assertEqual(len(line), 1)
        self.assertIn('elif decl & ENGINE.A:', line[0]); self.assertIn('eng.awaits_touch()', line[0]); self.assertIn('BTN_TALK', line[0])
        i = src.index('elif not eng.msg_visible:'); j = src.index('EN.touch_for_engine(')
        self.assertLess(i, j)                                  # apres la branche du terrain (sans message) : elle garde la priorite


if __name__ == '__main__':
    unittest.main(verbosity=1)
