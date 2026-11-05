"""Etiquettes du poker (SVC-03, choix du joueur : police reduite) : « Abandonner » sortait des cinq boutons sous les cartes et se chevauchait (le francais est plus long que l'anglais du bouton).

  `ui_menu.compress_label` : un texte plus large que sa plaque est comprime pour y tenir avec la police de repli, avec la police d'origine seulement si la fenetre pose une limite (fiche d'un sort) ou si c'est la fenetre du
  poker (type 48) ; ailleurs il depasse comme sur le mobile (choix du joueur, audit UI-05 : on ne touche pas a ces debordements).

    python3 tests/test_poker_font.py
"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
try:
    import pyglet
    if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
    from dq4_pc.menus import ui_menu as UM
except Exception as ex:          # ui_menu a besoin de pyglet (absent de la CI) : les tests sont alors ignores
    UM = None


@unittest.skipIf(UM is None, 'ui_menu non importable ici (pyglet absent)')
class Poker(unittest.TestCase):
    def test_poker_compressed_even_with_original_font(self):
        self.assertIn(48, UM.BUTTON_COMPRESSION_TYPES)
        self.assertTrue(UM.compress_label(True, None, 48))

    def test_other_windows_keep_their_overflow(self):
        for typ in (0, 1, 2, 3, 4, 5, 44, 45, 46, 47, 49, 53, 54):
            self.assertFalse(UM.compress_label(True, None, typ), typ)

    def test_behaviors_already_there(self):
        self.assertTrue(UM.compress_label(False, None, 3))             # police de repli : toujours
        self.assertTrue(UM.compress_label(True, 120.0, 3))             # limite posee par la fenetre (cout d'un sort)

    def test_only_poker(self):
        self.assertEqual(tuple(UM.BUTTON_COMPRESSION_TYPES), (48,))        # (casino : machine a sous 44-47 et pari de l'arene : inchanges)


if __name__ == '__main__':
    unittest.main()
