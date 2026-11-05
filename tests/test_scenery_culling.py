"""Faces cachees du decor (#182 : « en interieur les murs doivent devenir transparents ... les faces externes n'ont pas de textures, si on tourne la camera on doit pouvoir voir a travers les murs ») :

Les shaders du decor de carte du jeu (Custom/fld_normal, fld_atest, fld_trans, fld_transz et leurs variantes sepia) sont en « Cull Back » (ShaderLab culling = 2, lu dans le paquet de donnees) ; seule la carte du monde (Custom/Field)
est sans culling. `Game._scenery_culling` allume donc le culling des faces arriere (face avant = sens horaire a l'ecran, Unity etant en main gauche) pour chaque groupe du decor, sauf le ciel du titre (ses propres sommets) ;
sans fenetre ni GL : les appels GL sont enregistres.

    python3 tools/test_scenery_culling.py

  1. mode par defaut : culling des faces arriere, face avant = sens horaire (GL_CW) ; DQ_DECOR_CULL = 0 : rien (l'ancien rendu) ; 2 : sens inverse (essai) ; actif = False : toujours coupe et sens remis ;
  2. `_paint_scenery` : le culling est regle groupe par groupe (jamais pour le ciel du titre) et coupe apres les groupes (ombres, sprites, effets, modeles 3D gardent leur propre reglage) ;
  3. les reglages GL des modeles 3D (Custom/ImdChara), des ombres et des effets sont inchanges.
"""
import inspect, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.window import game as F


class FakeGL:
    GL_CULL_FACE, GL_BACK, GL_CW, GL_CCW = 'CULL', 'BACK', 'CW', 'CCW'
    def __init__(self): self.calls = []
    def glEnable(self, x): self.calls.append(('enable', x))
    def glDisable(self, x): self.calls.append(('disable', x))
    def glCullFace(self, x): self.calls.append(('cullface', x))
    def glFrontFace(self, x): self.calls.append(('frontface', x))


class TestCulling(unittest.TestCase):
    def setUp(self):
        self.f = FakeGL(); self.restore_gl = _paths.set_global('gl', self.f); self.env0 = os.environ.pop('DQ_DECOR_CULL', None)
    def tearDown(self):
        self.restore_gl()
        os.environ.pop('DQ_DECOR_CULL', None)
        if self.env0 is not None: os.environ['DQ_DECOR_CULL'] = self.env0

    def test_default_back_faces_hidden_clockwise(self):
        F.Game._scenery_culling(True)
        self.assertEqual(self.f.calls, [('enable', 'CULL'), ('cullface', 'BACK'), ('frontface', 'CW')])

    def test_culling_off(self):
        F.Game._scenery_culling(False); self.assertEqual(self.f.calls, [('disable', 'CULL'), ('frontface', 'CCW')])         # coupe et sens par defaut d'OpenGL remis

    def test_trial_variable(self):
        os.environ['DQ_DECOR_CULL'] = '0'; F.Game._scenery_culling(True); self.assertEqual(self.f.calls, [('disable', 'CULL'), ('frontface', 'CCW')])         # l'ancien rendu
        self.f.calls.clear(); os.environ['DQ_DECOR_CULL'] = '2'; F.Game._scenery_culling(True); self.assertEqual(self.f.calls, [('enable', 'CULL'), ('cullface', 'BACK'), ('frontface', 'CCW')])
        self.f.calls.clear(); os.environ['DQ_DECOR_CULL'] = 'x'; F.Game._scenery_culling(True); self.assertEqual(self.f.calls[-1], ('frontface', 'CW'))        # illisible : comme le defaut


class TestUsage(unittest.TestCase):
    def test_group_by_group_except_title_sky(self):
        src = inspect.getsource(F.Game._paint_scenery)
        self.assertIn('self._scenery_culling(key != sky_key)', src)                                                    # chaque groupe du decor ; le ciel du titre jamais
        self.assertIn("sky_key = self.flat_sky['key'] if self.flat_sky is not None else (self.zoom_sky['key'] if self.zoom_sky is not None else None)", src)
        i, j = src.index('self._scenery_culling(key != sky_key)'), src.index('self._scenery_culling(False)')
        self.assertLess(i, j)                                                                                         # coupe apres les groupes : les bandes / copies du ciel et la suite gardent leur reglage
        self.assertLess(j, src.index('for tex, vl, key, start_idx, n, dx in self.ext_map'))

    def test_other_gl_settings_unchanged(self):
        src = _paths.source('window.py')
        self.assertIn("cull = os.environ.get('DQ_FBX_CULL', '1')", src)                                               # modeles 3D : Custom/ImdChara, Cull Back, leur propre variable
        self.assertEqual(src.count('gl.glEnable(gl.GL_CULL_FACE)'), 2)                                                # modeles 3D + _scenery_culling : rien d'autre ne l'allume


if __name__ == '__main__':
    unittest.main(verbosity=1)
