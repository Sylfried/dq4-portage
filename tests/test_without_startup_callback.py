"""Test de l'issue #129 : le petit rappel « Échap : menu    F1 : infos » en bas à gauche, affiché 8 secondes au démarrage, est retiré (demande de Sylfried, 03/11/2026, 23 h 08).

    python3 tools/test_without_startup_callback.py
"""
import inspect, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.window import game as F


class WithoutReminder(unittest.TestCase):
    def test_no_more_reminder_text(self):
        self.assertFalse(hasattr(F.Game, '_texte_conseil'))
        src = _paths.source('window.py')
        for pattern in ('etiq_conseil', '_texte_conseil', "'Échap : menu'"): self.assertNotIn(pattern, src, pattern)

    def test_drawing_no_longer_waits_for_startup(self):
        self.assertNotIn('t_startup < 8.0', _paths.source('window.py'))                        # (t_startup reste : il sert aux mesures de temps reel)


if __name__ == '__main__':
    unittest.main()
