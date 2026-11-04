"""#225 (audit CMB-03) : `CombatMixin._texture_monstre` : une texture de monstre absente des donnees (`donnees.texture` renvoie None : 25 numeros de monstre) ou illisible (exception) est remplacee par une petite texture
transparente au lieu d'arreter le jeu. Sans moteur ni fenetre : les appels OpenGL sont remplaces.
    PYGLET_HEADLESS=1 python3 tests/test_texture_monstre_absente.py"""
import os, sys, types, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
try:
    from dq4_pc.fenetre import scene_combat as SC
except Exception as ex: SC = None; RAISON = repr(ex)


class Donnees:
    def __init__(self, rep): self.rep = rep
    def texture(self, nom):
        if isinstance(self.rep, Exception): raise self.rep
        return self.rep


@unittest.skipIf(SC is None, 'fenetre non importable ici (pyglet)')
class TextureAbsente(unittest.TestCase):
    def setUp(self):
        self.gl_avant = SC.gl; SC.gl = types.SimpleNamespace(glTexParameteri=lambda *a: None, GL_TEXTURE_MIN_FILTER=1, GL_TEXTURE_MAG_FILTER=2, GL_LINEAR=3)
        self.addCleanup(setattr, SC, 'gl', self.gl_avant)

    def jeu(self, rep):
        recu = []
        j = types.SimpleNamespace(cb_tex={}, mode=0, donnees=Donnees(rep), _tex=lambda arr, *a: recu.append(arr) or types.SimpleNamespace(target=0))
        return j, recu

    def test_texture_presente_inchangee(self):
        arr = np.full((8, 4, 4), 7, np.uint8); j, recu = self.jeu(arr)
        r = SC.CombatMixin._texture_monstre(j, 5)
        self.assertIs(recu[0], arr); self.assertEqual((r['tw'], r['th']), (4, 8))

    def test_texture_absente_remplacee(self):
        j, recu = self.jeu(None)
        r = SC.CombatMixin._texture_monstre(j, 199)                                    # (le monstre 199 plantait le processus)
        self.assertEqual(recu[0].shape, (16, 16, 4)); self.assertFalse(recu[0].any())  # transparente
        self.assertEqual((r['tw'], r['th']), (16, 16)); self.assertIs(SC.CombatMixin._texture_monstre(j, 199), r)       # gardee en memoire : une seule ligne de console

    def test_texture_illisible_remplacee(self):
        j, recu = self.jeu(OSError('fichier abime'))
        r = SC.CombatMixin._texture_monstre(j, 3)
        self.assertEqual((r['tw'], r['th']), (16, 16))


if __name__ == '__main__': unittest.main(verbosity=1)
