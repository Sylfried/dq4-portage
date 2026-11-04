"""Faces cachees du decor (#182 : « en interieur les murs doivent devenir transparents ... les faces externes n'ont pas de textures, si on tourne la camera on doit pouvoir voir a travers les murs ») :

Les shaders du decor de carte du jeu (Custom/fld_normal, fld_atest, fld_trans, fld_transz et leurs variantes sepia) sont en « Cull Back » (ShaderLab culling = 2, lu dans le paquet de donnees) ; seule la carte du monde (Custom/Field)
est sans culling. `Jeu._culling_decor` allume donc le culling des faces arriere (face avant = sens horaire a l'ecran, Unity etant en main gauche) pour chaque groupe du decor, sauf le ciel du titre (ses propres sommets) ;
sans fenetre ni GL : les appels GL sont enregistres.

    python3 outils/test_decor_culling.py

  1. mode par defaut : culling des faces arriere, face avant = sens horaire (GL_CW) ; DQ_DECOR_CULL = 0 : rien (l'ancien rendu) ; 2 : sens inverse (essai) ; actif = False : toujours coupe et sens remis ;
  2. `_tracer_decor` : le culling est regle groupe par groupe (jamais pour le ciel du titre) et coupe apres les groupes (ombres, sprites, effets, modeles 3D gardent leur propre reglage) ;
  3. les reglages GL des modeles 3D (Custom/ImdChara), des ombres et des effets sont inchanges.
"""
import inspect, os, sys, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False
import fenetre as F


class FauxGL:
    GL_CULL_FACE, GL_BACK, GL_CW, GL_CCW = 'CULL', 'BACK', 'CW', 'CCW'
    def __init__(self): self.appels = []
    def glEnable(self, x): self.appels.append(('enable', x))
    def glDisable(self, x): self.appels.append(('disable', x))
    def glCullFace(self, x): self.appels.append(('cullface', x))
    def glFrontFace(self, x): self.appels.append(('frontface', x))


class TestCulling(unittest.TestCase):
    def setUp(self):
        self.gl0 = F.gl; self.f = F.gl = FauxGL(); self.env0 = os.environ.pop('DQ_DECOR_CULL', None)
    def tearDown(self):
        F.gl = self.gl0
        os.environ.pop('DQ_DECOR_CULL', None)
        if self.env0 is not None: os.environ['DQ_DECOR_CULL'] = self.env0

    def test_defaut_faces_arriere_cachees_sens_horaire(self):
        F.Jeu._culling_decor(True)
        self.assertEqual(self.f.appels, [('enable', 'CULL'), ('cullface', 'BACK'), ('frontface', 'CW')])

    def test_coupe(self):
        F.Jeu._culling_decor(False); self.assertEqual(self.f.appels, [('disable', 'CULL'), ('frontface', 'CCW')])         # coupe et sens par defaut d'OpenGL remis

    def test_variable_d_essai(self):
        os.environ['DQ_DECOR_CULL'] = '0'; F.Jeu._culling_decor(True); self.assertEqual(self.f.appels, [('disable', 'CULL'), ('frontface', 'CCW')])         # l'ancien rendu
        self.f.appels.clear(); os.environ['DQ_DECOR_CULL'] = '2'; F.Jeu._culling_decor(True); self.assertEqual(self.f.appels, [('enable', 'CULL'), ('cullface', 'BACK'), ('frontface', 'CCW')])
        self.f.appels.clear(); os.environ['DQ_DECOR_CULL'] = 'x'; F.Jeu._culling_decor(True); self.assertEqual(self.f.appels[-1], ('frontface', 'CW'))        # illisible : comme le defaut


class TestUsage(unittest.TestCase):
    def test_groupe_par_groupe_sauf_le_ciel_du_titre(self):
        src = inspect.getsource(F.Jeu._tracer_decor)
        self.assertIn('self._culling_decor(key != cle_ciel)', src)                                                    # chaque groupe du decor ; le ciel du titre jamais
        self.assertIn("cle_ciel = self.ciel_plat['key'] if self.ciel_plat is not None else (self.ciel_zoom['key'] if self.ciel_zoom is not None else None)", src)
        i, j = src.index('self._culling_decor(key != cle_ciel)'), src.index('self._culling_decor(False)')
        self.assertLess(i, j)                                                                                         # coupe apres les groupes : les bandes / copies du ciel et la suite gardent leur reglage
        self.assertLess(j, src.index('for tex, vl, key, deb, n, dx in self.carte_ext'))

    def test_les_autres_reglages_gl_sont_inchanges(self):
        src = inspect.getsource(F.Jeu)
        self.assertIn("cull = os.environ.get('DQ_FBX_CULL', '1')", src)                                               # modeles 3D : Custom/ImdChara, Cull Back, leur propre variable
        self.assertEqual(src.count('gl.glEnable(gl.GL_CULL_FACE)'), 2)                                                # modeles 3D + _culling_decor : rien d'autre ne l'allume


if __name__ == '__main__':
    unittest.main(verbosity=1)
