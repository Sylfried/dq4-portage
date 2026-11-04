"""Etiquettes du poker (SVC-03, choix du joueur : police reduite) : « Abandonner » sortait des cinq boutons sous les cartes et se chevauchait (le francais est plus long que l'anglais du bouton).

  `ui_menu.comprimer_etiquette` : un texte plus large que sa plaque est comprime pour y tenir avec la police de repli, avec la police d'origine seulement si la fenetre pose une limite (fiche d'un sort) ou si c'est la fenetre du
  poker (type 48) ; ailleurs il depasse comme sur le mobile (choix du joueur, audit UI-05 : on ne touche pas a ces debordements).

    python3 tests/test_poker_police.py
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
    def test_poker_comprime_meme_avec_la_police_d_origine(self):
        self.assertIn(48, UM.TYPES_COMPRESSION_BOUTONS)
        self.assertTrue(UM.comprimer_etiquette(True, None, 48))

    def test_les_autres_fenetres_gardent_leur_debordement(self):
        for typ in (0, 1, 2, 3, 4, 5, 44, 45, 46, 47, 49, 53, 54):
            self.assertFalse(UM.comprimer_etiquette(True, None, typ), typ)

    def test_comportements_deja_la(self):
        self.assertTrue(UM.comprimer_etiquette(False, None, 3))             # police de repli : toujours
        self.assertTrue(UM.comprimer_etiquette(True, 120.0, 3))             # limite posee par la fenetre (cout d'un sort)

    def test_seul_le_poker(self):
        self.assertEqual(tuple(UM.TYPES_COMPRESSION_BOUTONS), (48,))        # (casino : machine a sous 44-47 et pari de l'arene : inchanges)


if __name__ == '__main__':
    unittest.main()
