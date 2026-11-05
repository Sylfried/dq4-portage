"""Echelle de la carte du monde en ballon (paquet 30, `cmd_field_scale` ; audit MAP-02 / UNI-05 / SPR-06) :

  1. `State` : un entier negatif suivi d'un flottant fixe l'echelle du terrain (Field.SetScale : 1,0 a 1,25 en ballon) ; un entier >= 0 enregistre le personnage de cet emplacement comme « objet flottant »
     (Field.SetFloatingObject : le ballon, emplacement 12) ; sans doublon ; valeurs aberrantes (0, negatives, NaN, infini, absente) ignorees, valeurs extremes bornees ;
  2. rechargement : le chargement de carte (paquet 0) remet l'echelle a 1 et vide les objets flottants ; le chargement de la carte du monde (paquet 27) aussi (le moteur reenregistre le ballon juste apres) ;
  3. un etat enregistre avant ce correctif (sans ces attributs) se comporte comme neuf : echelle 1, aucun objet flottant ;
  4. camera de la carte du monde : la hauteur visible est multipliee par l'echelle du jeu (plus de zoom du joueur depuis #264 ; ignore sans pyglet).

    python3 tests/test_balloon_scale.py
"""
import math, os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.core import engine as ENGINE

try:
    import pyglet
    pyglet.options['shadow_window'] = False
    from dq4_pc.window import camera as CAM
    from dq4_pc.window.constants import CH_VIEW_HEIGHT
except Exception as ex:          # fenetre/camera.py a besoin de pyglet (l'import seul suffit)
    CAM = None


def send(e, *packets):
    e.apply(list(packets), lambda: 'ev01')


class Packet30(unittest.TestCase):
    def test_default_values(self):
        e = ENGINE.State(); self.assertEqual(e.field_scale, 1.0); self.assertEqual(e.floats, ())

    def test_scale(self):
        e = ENGINE.State()
        send(e, (30, [-1], [1.25])); self.assertAlmostEqual(e.field_scale, 1.25)
        send(e, (30, [-1], [1.1015625])); self.assertAlmostEqual(e.field_scale, 1.1015625)          # 1 + 13 / 128
        send(e, (30, [-1], [1.0])); self.assertEqual(e.field_scale, 1.0)                           # atterrissage : le ballon redescend a l'echelle 1

    def test_floating_item(self):
        e = ENGINE.State()
        send(e, (30, [12], [])); self.assertEqual(e.floats, (12,))
        send(e, (30, [12], [])); self.assertEqual(e.floats, (12,))          # pas de doublon
        send(e, (30, [3], [])); self.assertEqual(e.floats, (12, 3))
        self.assertEqual(e.field_scale, 1.0)                                    # enregistrer un objet ne touche pas l'echelle

    def test_outlier_values(self):
        e = ENGINE.State(); send(e, (30, [-1], [1.25]))
        for f in ([], [0.0], [-2.0], [math.nan], [math.inf]):
            send(e, (30, [-1], f)); self.assertEqual(e.field_scale, 1.25, f)
        send(e, (30, [-1], [1000.0])); self.assertEqual(e.field_scale, ENGINE.FIELD_SCALE[1])
        send(e, (30, [-1], [1e-6])); self.assertEqual(e.field_scale, ENGINE.FIELD_SCALE[0])
        send(e, (30, [], [1.25]))                                              # paquet vide : ignore sans erreur

    def test_map_loading(self):
        e = ENGINE.State(); send(e, (30, [12], []), (30, [-1], [1.25]))
        send(e, (0, [], [])); self.assertEqual(e.field_scale, 1.0); self.assertEqual(e.floats, ())

    def test_world_map_loading(self):
        e = ENGINE.State(); send(e, (30, [12], []), (30, [-1], [1.25]))
        send(e, (27, [1], []), (30, [12], []))          # ce que le vrai moteur envoie a l'entree sur la carte du monde (verifie sur la sauvegarde 4 : image 31)
        self.assertEqual(e.field_scale, 1.0); self.assertEqual(e.floats, (12,))

    def test_old_state(self):
        e = ENGINE.State.__new__(ENGINE.State)           # un etat enregistre sans ces attributs (ni __init__, ni __dict__ rempli)
        self.assertEqual(e.field_scale, 1.0); self.assertEqual(e.floats, ())


@unittest.skipIf(CAM is None, 'pas de pyglet')
class WorldCamera(unittest.TestCase):
    def make_view(self, scale_factor):
        fake = types.SimpleNamespace(mode=0)
        e = ENGINE.State(); e.field_scale = scale_factor; e.field = {'x0': 0, 'y0': 0, 'cols': 25, 'tuiles': [], 'cam': (160.0, 320.0)}
        CAM.CameraMixin._field_camera(fake, e, 16 / 9)
        return fake._field_view

    def test_visible_height(self):
        cx, cz, dl, dh = self.make_view(1.0)
        self.assertAlmostEqual(dh, CH_VIEW_HEIGHT / 2); self.assertAlmostEqual(dl, dh * 16 / 9)
        self.assertAlmostEqual(self.make_view(1.25)[3], dh * 1.25)             # 25 % de terrain en plus

    def test_center_unchanged(self):
        cx, cz, dl, dh = self.make_view(1.25); self.assertAlmostEqual(cx, 10.0); self.assertAlmostEqual(cz, 20.0)

    def test_state_without_scale(self):
        fake = types.SimpleNamespace(mode=0); e = types.SimpleNamespace(field=None)        # objet sans l'attribut (autre type d'etat) : echelle 1
        CAM.CameraMixin._field_camera(fake, e, 16 / 9); self.assertAlmostEqual(fake._field_view[3], CH_VIEW_HEIGHT / 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
