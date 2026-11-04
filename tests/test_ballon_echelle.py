"""Echelle de la carte du monde en ballon (paquet 30, `cmd_field_scale` ; audit MAP-02 / UNI-05 / SPR-06) :

  1. `Etat` : un entier negatif suivi d'un flottant fixe l'echelle du terrain (Field.SetScale : 1,0 a 1,25 en ballon) ; un entier >= 0 enregistre le personnage de cet emplacement comme « objet flottant »
     (Field.SetFloatingObject : le ballon, emplacement 12) ; sans doublon ; valeurs aberrantes (0, negatives, NaN, infini, absente) ignorees, valeurs extremes bornees ;
  2. rechargement : le chargement de carte (paquet 0) remet l'echelle a 1 et vide les objets flottants ; le chargement de la carte du monde (paquet 27) aussi (le moteur reenregistre le ballon juste apres) ;
  3. un etat enregistre avant ce correctif (sans ces attributs) se comporte comme neuf : echelle 1, aucun objet flottant ;
  4. camera de la carte du monde : la hauteur visible est multipliee par l'echelle du jeu, par-dessus le zoom du joueur (ignore sans pyglet).

    python3 tests/test_ballon_echelle.py
"""
import math, os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dq4_pc.noyau import moteur as MO

try:
    import pyglet
    pyglet.options['shadow_window'] = False
    from dq4_pc.fenetre import camera as CAM
    from dq4_pc.fenetre.constantes import CH_VUE_HAUT
except Exception as ex:          # fenetre/camera.py a besoin de pyglet (l'import seul suffit)
    CAM = None


def envoyer(e, *paquets):
    e.appliquer(list(paquets), lambda: 'ev01')


class Paquet30(unittest.TestCase):
    def test_valeurs_par_defaut(self):
        e = MO.Etat(); self.assertEqual(e.champ_echelle, 1.0); self.assertEqual(e.flottants, ())

    def test_echelle(self):
        e = MO.Etat()
        envoyer(e, (30, [-1], [1.25])); self.assertAlmostEqual(e.champ_echelle, 1.25)
        envoyer(e, (30, [-1], [1.1015625])); self.assertAlmostEqual(e.champ_echelle, 1.1015625)          # 1 + 13 / 128
        envoyer(e, (30, [-1], [1.0])); self.assertEqual(e.champ_echelle, 1.0)                           # atterrissage : le ballon redescend a l'echelle 1

    def test_objet_flottant(self):
        e = MO.Etat()
        envoyer(e, (30, [12], [])); self.assertEqual(e.flottants, (12,))
        envoyer(e, (30, [12], [])); self.assertEqual(e.flottants, (12,))          # pas de doublon
        envoyer(e, (30, [3], [])); self.assertEqual(e.flottants, (12, 3))
        self.assertEqual(e.champ_echelle, 1.0)                                    # enregistrer un objet ne touche pas l'echelle

    def test_valeurs_aberrantes(self):
        e = MO.Etat(); envoyer(e, (30, [-1], [1.25]))
        for f in ([], [0.0], [-2.0], [math.nan], [math.inf]):
            envoyer(e, (30, [-1], f)); self.assertEqual(e.champ_echelle, 1.25, f)
        envoyer(e, (30, [-1], [1000.0])); self.assertEqual(e.champ_echelle, MO.ECHELLE_CHAMP[1])
        envoyer(e, (30, [-1], [1e-6])); self.assertEqual(e.champ_echelle, MO.ECHELLE_CHAMP[0])
        envoyer(e, (30, [], [1.25]))                                              # paquet vide : ignore sans erreur

    def test_chargement_de_carte(self):
        e = MO.Etat(); envoyer(e, (30, [12], []), (30, [-1], [1.25]))
        envoyer(e, (0, [], [])); self.assertEqual(e.champ_echelle, 1.0); self.assertEqual(e.flottants, ())

    def test_chargement_de_la_carte_du_monde(self):
        e = MO.Etat(); envoyer(e, (30, [12], []), (30, [-1], [1.25]))
        envoyer(e, (27, [1], []), (30, [12], []))          # ce que le vrai moteur envoie a l'entree sur la carte du monde (verifie sur la sauvegarde 4 : image 31)
        self.assertEqual(e.champ_echelle, 1.0); self.assertEqual(e.flottants, (12,))

    def test_ancien_etat(self):
        e = MO.Etat.__new__(MO.Etat)           # un etat enregistre sans ces attributs (ni __init__, ni __dict__ rempli)
        self.assertEqual(e.champ_echelle, 1.0); self.assertEqual(e.flottants, ())


@unittest.skipIf(CAM is None, 'pas de pyglet')
class CameraMonde(unittest.TestCase):
    def vue(self, zoom, echelle):
        faux = types.SimpleNamespace(zoom=zoom, mode=0)
        e = MO.Etat(); e.champ_echelle = echelle; e.champ = {'x0': 0, 'y0': 0, 'cols': 25, 'tuiles': [], 'cam': (160.0, 320.0)}
        CAM.CameraMixin._camera_champ(faux, e, 16 / 9)
        return faux._vue_champ

    def test_hauteur_visible(self):
        cx, cz, dl, dh = self.vue(1.0, 1.0)
        self.assertAlmostEqual(dh, CH_VUE_HAUT / 2); self.assertAlmostEqual(dl, dh * 16 / 9)
        self.assertAlmostEqual(self.vue(1.0, 1.25)[3], dh * 1.25)             # 25 % de terrain en plus
        self.assertAlmostEqual(self.vue(2.0, 1.0)[3], dh / 2)                 # zoom du joueur seul
        self.assertAlmostEqual(self.vue(2.0, 1.25)[3], dh / 2 * 1.25)         # les deux se multiplient : le jeu l'emporte sans effacer le zoom du joueur

    def test_centre_inchange(self):
        cx, cz, dl, dh = self.vue(1.0, 1.25); self.assertAlmostEqual(cx, 10.0); self.assertAlmostEqual(cz, 20.0)

    def test_etat_sans_echelle(self):
        faux = types.SimpleNamespace(zoom=1.0, mode=0); e = types.SimpleNamespace(champ=None)        # objet sans l'attribut (autre type d'etat) : echelle 1
        CAM.CameraMixin._camera_champ(faux, e, 16 / 9); self.assertAlmostEqual(faux._vue_champ[3], CH_VUE_HAUT / 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
