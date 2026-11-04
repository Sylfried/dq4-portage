"""Test de l'issue #129 : le petit rappel « Échap : menu    F1 : infos » en bas à gauche, affiché 8 secondes au démarrage, est retiré (demande de Sylfried, 03/11/2026, 23 h 08).

    python3 outils/test_sans_rappel_demarrage.py
"""
import inspect, os, sys, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..'))
import _chemins          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.fenetre import jeu as F


class SansRappel(unittest.TestCase):
    def test_plus_de_texte_de_rappel(self):
        self.assertFalse(hasattr(F.Jeu, '_texte_conseil'))
        src = _chemins.source('fenetre.py')
        for motif in ('etiq_conseil', '_texte_conseil', "'Échap : menu'"): self.assertNotIn(motif, src, motif)

    def test_le_dessin_n_attend_plus_le_demarrage(self):
        self.assertNotIn('t_demarrage < 8.0', _chemins.source('fenetre.py'))                        # (t_demarrage reste : il sert aux mesures de temps reel)


if __name__ == '__main__':
    unittest.main()
