"""Test de « Ctrl + touche de camera = TOUS les etats de la camera reviennent a l'origine » (#168) :

    python3 outils/test_camera_ctrl_tout.py

Les vraies methodes de fenetre.Jeu (_maj_camera, _maj_distance_clavier, reinitialiser_camera...) sur un faux jeu.
1. Ctrl (la « Touche speciale ») + une fleche, Page haut ou Page bas : la rotation, l'inclinaison ET la distance reviennent ensemble a leur valeur d'origine, par les animations (jamais d'a-coup), et y restent tant que les
   touches sont tenues.
2. Sans Ctrl : rien de change (les fleches tournent, Page haut / Page bas zooment, les deux touches de distance ne remettent que la distance).
3. Chaque etat ne se remet que la ou il se regle : carte du monde et lieu qui interdit de tourner la camera = la distance seule ; ni menu, ni message, ni combat : rien.
"""
import os, sys, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False
import reglages as RG

try:
    import fenetre as FE
except Exception as ex:          # fenetre.py a besoin de pyglet, numpy, unicorn... (l'import seul suffit, aucune fenetre n'est creee)
    FE = None; ERREUR_FE = ex

METHODES = ('_terrain_libre', '_camera_pilotable', '_zoom_possible', 'recentrer_camera', 'distance_par_defaut', 'reinitialiser_camera', 'regler_zoom', 'regler_distance', '_maj_distance_clavier', '_etat_axe', '_maj_camera')


class Faux:
    """Un `Jeu` minimal : terrain libre d'une ville, camera tournee de 70 degres, inclinee de 20 degres, distance 170 %."""
    def __init__(self, partie=None, distance=170, lacet=70.0, angle=20.0, **kw):
        MO = FE.MO
        self.moteur = types.SimpleNamespace(etat=types.SimpleNamespace(partie=MO.PARTIE_VILLE if partie is None else partie, effet=None), msg_visible=False, menu_actif=lambda: None)
        self.pause = types.SimpleNamespace(ouvert=False); self.licence = None; self.sauv = None; self.titre = None; self._saisie_nom_en_cours = lambda: False; self.carte_ouverte = False; self.cam_bloquee = False; self.cam_limite = None
        self.reg = RG.Reglages(None); self.reg['distance_camera'] = distance; self.zoom = 100.0 / distance; self.reg['angle_camera'] = angle
        self.lacet = lacet; self.angle_cam = angle; self.cam_axe = {'lacet': [False, False], 'angle': [False, False]}; self.fixe_test = True; self.t_cam = None; self._t_dist = None; self.dist_retour = False; self.dist_bloque = False
        self.tenues = set(); self._tenue = lambda a: a in self.tenues; self._zoom_valide = FE.Jeu._zoom_valide
        for k, v in kw.items(): setattr(self, k, v)
        for nom in METHODES: setattr(self, nom, types.MethodType(getattr(FE.Jeu, nom), self))

    @property
    def distance(self): return 100.0 / self.zoom

    def images(self, n, *touches):
        """n images affichees avec ces actions tenues (comme Jeu.on_draw : _maj_camera puis _maj_distance_clavier) -> [(lacet, angle, distance)]."""
        self.tenues = set(touches); out = []
        for _ in range(n): self._maj_camera(); self._maj_distance_clavier(); out.append((self.lacet, self.angle_cam, self.distance))
        return out


def etats(j): return (j.lacet, j.angle_cam, j.distance)


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class CtrlPlusToucheDeCamera(unittest.TestCase):
    TOUCHES = ('cam_gauche', 'cam_droite', 'cam_haut', 'cam_bas', 'cam_pres', 'cam_loin')

    def test_les_trois_etats_reviennent_a_l_origine(self):
        for t in self.TOUCHES:
            j = Faux(); j.images(180, 'modif', t)
            self.assertEqual(etats(j), (0.0, 0.0, 100.0), t); self.assertEqual(j.reg['distance_camera'], 100); self.assertEqual(j.reg['angle_camera'], 0.0)

    def test_depuis_les_deux_cotes_de_la_distance_et_de_la_rotation(self):
        for dist, lacet, angle in ((200, -120.0, -30.0), (50, 179.0, 45.0), (100, 10.0, 0.0), (130, -3.0, 60.0)):
            for t in ('cam_gauche', 'cam_pres'):
                j = Faux(distance=dist, lacet=lacet, angle=angle); j.images(240, 'modif', t); self.assertEqual(etats(j), (0.0, 0.0, 100.0), (dist, lacet, angle, t))

    def test_par_animation_pas_d_a_coup(self):
        for t in ('cam_droite', 'cam_loin'):
            j = Faux(); out = j.images(120, 'modif', t); prev = (70.0, 20.0, 170.0)
            premier = out[0]; self.assertNotEqual(premier, (0.0, 0.0, 100.0))                                      # (pas d'arrivee immediate)
            for e in out:
                self.assertLessEqual(abs(e[0]), abs(prev[0]) + 1e-9); self.assertLessEqual(abs(e[1]), abs(prev[1]) + 1e-9); self.assertLessEqual(e[2], prev[2] + 1e-9); self.assertGreaterEqual(e[2], 100.0)      # monotone, sans depassement
                self.assertLess(abs(e[0] - prev[0]), 10.0); self.assertLess(abs(e[1] - prev[1]), 10.0); self.assertLess(abs(e[2] - prev[2]), 10.0)               # (au plus quelques degres / pourcents par image)
                prev = e
            n = next(i for i, e in enumerate(out) if e == (0.0, 0.0, 100.0)); self.assertTrue(10 < n < 100, (t, n))                  # ni un saut, ni une longue attente

    def test_la_distance_va_a_la_meme_vitesse_que_la_rotation(self):
        """#173 : un ecart de X % se resorbe comme un ecart de X degres : rotation et distance arrivent a l'origine a la meme image (a une image pres)."""
        for dist, lacet in ((200, 100.0), (170, 70.0), (150, 50.0), (130, -30.0), (60, 40.0), (50, -50.0), (200, -100.0)):
            j = Faux(distance=dist, lacet=lacet, angle=0.0); out = j.images(240, 'modif', 'cam_gauche')
            n_lacet = next(i for i, e in enumerate(out) if e[0] == 0.0); n_dist = next(i for i, e in enumerate(out) if e[2] == 100.0)
            self.assertLessEqual(abs(n_lacet - n_dist), 1, (dist, lacet, n_lacet, n_dist))
            for i in range(0, min(n_lacet, n_dist) - 1, 3):                                                         # (et pendant le mouvement : la meme part de l'ecart restant, a quelques points pres)
                self.assertLess(abs(abs(out[i][0]) / abs(lacet) - abs(out[i][2] - 100.0) / abs(dist - 100.0)) if lacet else 0.0, 0.2, (dist, lacet, i))

    def test_les_touches_tenues_gardent_l_origine(self):
        j = Faux(); j.images(180, 'modif', 'cam_gauche'); a = etats(j); j.images(60, 'modif', 'cam_gauche'); self.assertEqual(etats(j), a)           # la fleche ne tourne plus la camera tant que Ctrl est tenue
        j.images(60, 'modif', 'cam_pres'); self.assertEqual(etats(j), (0.0, 0.0, 100.0))

    def test_ctrl_relache_la_touche_restee_enfoncee_ne_fait_rien(self):
        for t, avant in (('cam_gauche', (0.0, 0.0, 100.0)), ('cam_pres', (0.0, 0.0, 100.0))):
            j = Faux(); j.images(5, 'modif', t); j.images(240, t); self.assertEqual(etats(j), avant, t)                                           # (Ctrl lache en premier : la touche seule n'agit pas tant qu'elle n'est pas relachee)
            j.images(2); j.images(10, t)
            self.assertNotEqual(etats(j), avant, t)                                                                                              # relachee puis pressee de nouveau : elle agit

    def test_ctrl_seule_ne_fait_rien(self):
        j = Faux(); j.images(60, 'modif'); self.assertEqual(etats(j), (70.0, 20.0, 170.0))

    def test_la_touche_speciale_reattribuee_est_celle_de_reglages(self):
        j = Faux(); j.images(5, 'cam_gauche'); self.assertNotEqual(j.lacet, 70.0)                                                                  # (sans la touche speciale : la camera tourne)
        j = Faux(); j.images(120, 'modif', 'cam_gauche'); self.assertEqual(j.lacet, 0.0)


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class SansCtrlRienNeChange(unittest.TestCase):
    def test_les_fleches_tournent_sans_toucher_la_distance(self):
        j = Faux(); j.images(30, 'cam_droite'); self.assertNotEqual(j.lacet, 70.0); self.assertEqual(j.distance, 170.0)
        j = Faux(); j.images(30, 'cam_haut'); self.assertNotEqual(j.angle_cam, 20.0); self.assertEqual(j.distance, 170.0); self.assertEqual(j.lacet, 70.0)

    def test_page_haut_et_page_bas_zooment_sans_toucher_la_position(self):
        j = Faux(); j.images(30, 'cam_loin'); self.assertGreater(j.distance, 170.0); self.assertEqual((j.lacet, j.angle_cam), (70.0, 20.0))
        j = Faux(); j.images(30, 'cam_pres'); self.assertLess(j.distance, 170.0); self.assertEqual((j.lacet, j.angle_cam), (70.0, 20.0))

    def test_les_deux_touches_de_distance_remettent_la_distance_seule(self):
        j = Faux(); j.images(180, 'cam_pres', 'cam_loin'); self.assertEqual(etats(j), (70.0, 20.0, 100.0))                                          # (#167 : la rotation et l'inclinaison ne bougent pas)
        self.assertFalse(any(a[0] for a in j.cam_axe.values()))

    def test_les_deux_fleches_opposees_remettent_la_position_seule(self):
        j = Faux(); j.images(180, 'cam_gauche', 'cam_droite'); self.assertEqual((j.lacet, j.distance), (0.0, 170.0))                                 # (comportement existant : la distance n'y est pour rien)


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class OuCelaSeRegle(unittest.TestCase):
    def test_carte_du_monde_la_distance_seule(self):
        for t in ('cam_gauche', 'cam_haut', 'cam_pres', 'cam_loin'):
            j = Faux(partie=FE.MO.PARTIE_CHAMP); j.images(180, 'modif', t)
            self.assertEqual(etats(j), (70.0, 20.0, 100.0), t); self.assertFalse(any(a[0] for a in j.cam_axe.values()), t)                          # pas de rotation sur la carte du monde (comme les fleches)

    def test_lieu_qui_interdit_la_camera_la_distance_seule(self):
        for t in ('cam_droite', 'cam_pres'):
            j = Faux(cam_bloquee=True); j.images(180, 'modif', t); self.assertEqual(etats(j), (70.0, 20.0, 100.0), t); self.assertFalse(any(a[0] for a in j.cam_axe.values()), t)

    def test_rien_hors_du_terrain_libre(self):
        MO = FE.MO
        def faux(nom):
            j = Faux()
            if nom == 'pause': j.pause.ouvert = True
            elif nom == 'message': j.moteur.msg_visible = True
            elif nom == 'menu': j.moteur.menu_actif = lambda: 12
            elif nom == 'combat': j.moteur.etat.partie = MO.PARTIE_COMBAT
            elif nom == 'titre': j.titre = object()
            elif nom == 'licence': j.licence = object()
            elif nom == 'sauvegardes': j.sauv = object()
            elif nom == 'nom': j._saisie_nom_en_cours = lambda: True
            elif nom == 'carte': j.carte_ouverte = True
            elif nom == 'effet': j.moteur.etat.effet = object()
            return j
        for nom in ('pause', 'message', 'menu', 'combat', 'titre', 'licence', 'sauvegardes', 'nom', 'carte', 'effet'):
            for t in (('cam_gauche',) if nom == 'effet' else ('cam_gauche', 'cam_pres')):
                j = faux(nom); j.images(60, 'modif', t); self.assertEqual(etats(j), (70.0, 20.0, 170.0), (nom, t)); self.assertFalse(any(a[0] for a in j.cam_axe.values()), (nom, t)); self.assertFalse(j.dist_retour, (nom, t))

    def test_pendant_un_effet_d_ecran_comme_la_molette(self):
        j = Faux(); j.moteur.etat.effet = object(); j.images(180, 'modif', 'cam_pres')
        self.assertEqual(etats(j), (70.0, 20.0, 100.0))                                                            # (la molette zoome encore pendant un effet d'ecran : la distance revient ; la position, non, comme les fleches)
        self.assertFalse(any(a[0] for a in j.cam_axe.values()))


if __name__ == '__main__':
    unittest.main(verbosity=1)
