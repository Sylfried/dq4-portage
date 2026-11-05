"""#225 (audit CMB-03) : `BattleMixin._monster_texture` : une texture de monstre absente des donnees (`data.texture` renvoie None : 25 numeros de monstre) ou illisible (exception) est remplacee par une petite texture
transparente au lieu d'arreter le jeu. Sans moteur ni fenetre : les appels OpenGL sont remplaces.
    PYGLET_HEADLESS=1 python3 tests/test_missing_monster_texture.py"""
import os, sys, types, unittest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
try:
    from dq4_pc.window import battle_scene as SC
except Exception as ex: SC = None; REASON = repr(ex)


class Data:
    def __init__(self, rep): self.rep = rep
    def texture(self, name_str):
        if isinstance(self.rep, Exception): raise self.rep
        return self.rep


@unittest.skipIf(SC is None, 'fenetre non importable ici (pyglet)')
class AbsentTexture(unittest.TestCase):
    def setUp(self):
        self.gl_before = SC.gl; SC.gl = types.SimpleNamespace(glTexParameteri=lambda *a: None, GL_TEXTURE_MIN_FILTER=1, GL_TEXTURE_MAG_FILTER=2, GL_LINEAR=3)
        self.addCleanup(setattr, SC, 'gl', self.gl_before)

    def game(self, rep):
        received = []
        j = types.SimpleNamespace(cb_tex={}, mode=0, data=Data(rep), _tex=lambda arr, *a: received.append(arr) or types.SimpleNamespace(target=0))
        return j, received

    def test_present_texture_unchanged(self):
        arr = np.full((8, 4, 4), 7, np.uint8); j, received = self.game(arr)
        r = SC.BattleMixin._monster_texture(j, 5)
        self.assertIs(received[0], arr); self.assertEqual((r['tw'], r['th']), (4, 8))

    def test_missing_texture_replaced(self):
        j, received = self.game(None)
        r = SC.BattleMixin._monster_texture(j, 199)                                    # (le monstre 199 plantait le processus)
        self.assertEqual(received[0].shape, (16, 16, 4)); self.assertFalse(received[0].any())  # transparente
        self.assertEqual((r['tw'], r['th']), (16, 16)); self.assertIs(SC.BattleMixin._monster_texture(j, 199), r)       # gardee en memoire : une seule ligne de console

    def test_unreadable_texture_replaced(self):
        j, received = self.game(OSError('fichier abime'))
        r = SC.BattleMixin._monster_texture(j, 3)
        self.assertEqual((r['tw'], r['th']), (16, 16))


if __name__ == '__main__': unittest.main(verbosity=1)
