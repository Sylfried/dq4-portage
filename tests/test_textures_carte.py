"""`Donnees._texture` : un materiau de decor sans aucune texture (21 cartes de lieux, 10 decors de combat : petites surfaces de couleur unie, sol sombre, eau...) donne la texture blanche 4 x 4
(cle `TEX_BLANCHE`, couleur du sommet x _Color du materiau, comme Unity avec sa texture blanche par defaut), pas `None` (le groupe etait ignore au dessin : la surface manquait) ;
un materiau avec texture est inchange ; un materiau illisible garde `None`.

    python3 outils/test_textures_carte.py
"""
import os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.monde import donnees as DO


class _Mat:
    def __init__(self, textures=(), couleurs=(), exc=False):
        self.exc = exc
        self.m_SavedProperties = types.SimpleNamespace(m_Colors=list(couleurs), m_TexEnvs=list(textures))


class _Ref:
    def __init__(self, mat): self.mat = mat
    def deref_parse_as_object(self):
        if self.mat.exc: raise ValueError('illisible')
        return self.mat


class TestMaterielSansTexture(unittest.TestCase):
    def setUp(self):
        self.d = DO.Donnees.__new__(DO.Donnees); self.d.log = lambda *a: None

    def col(self, r, g, b, a): return types.SimpleNamespace(r=r, g=g, b=b, a=a)

    def test_sans_texture(self):
        tex = {}
        cle, sc, off, col, genre = self.d._texture(_Ref(_Mat(couleurs=[('_Color', self.col(0.5, 0.25, 0.125, 1.0))])), tex)
        self.assertEqual(cle, DO.TEX_BLANCHE)
        self.assertEqual(tex[cle].shape, (4, 4, 4)); self.assertTrue((tex[cle] == 255).all())
        self.assertEqual((sc, off, col, genre), ((1.0, 1.0), (0.0, 0.0), (0.5, 0.25, 0.125, 1.0), 'normal'))

    def test_sans_texture_transparent(self):
        tex = {}
        self.assertEqual(self.d._texture(_Ref(_Mat(couleurs=[('_Color', self.col(1, 1, 1, 0.5))])), tex)[4], 'trans')

    def test_sans_aucune_couleur(self):
        cle, sc, off, col, genre = self.d._texture(_Ref(_Mat()), {})
        self.assertEqual((cle, col, genre), (DO.TEX_BLANCHE, (1.0, 1.0, 1.0, 1.0), 'normal'))

    def test_illisible(self):
        self.assertIsNone(self.d._texture(_Ref(_Mat(exc=True)), {})[0])


class TestPurgeAnciens(unittest.TestCase):
    def test_carte9_purgee_carte10_gardee(self):
        import shutil, tempfile
        d = tempfile.mkdtemp(prefix='cache_test_purge_')
        try:
            for f in ('carte8_a.pkl', 'carte9_a.pkl', 'carte10_a.pkl', 'fbx1_c1018.pkl', 'sprite_h0.npy'): open(os.path.join(d, f), 'wb').close()
            o = DO.Donnees.__new__(DO.Donnees); o.cache = d; o.log = lambda *a: None
            o._purger_anciens()
            self.assertEqual(sorted(os.listdir(d)), ['carte10_a.pkl', 'fbx1_c1018.pkl', 'sprite_h0.npy'])
        finally: shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    unittest.main(verbosity=1)
