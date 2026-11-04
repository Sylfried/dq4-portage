"""Test des entrees souris / clavier : logique pure (entrees.py) et branchement dans la fenetre (fenetre.Jeu), sans ouvrir de fenetre.

    python3 outils/test_entrees.py

1. La souris apres le clavier (« passer du clavier a la souris rend la souris inutilisable pendant 1 s ») : le survol reprend la main au premier vrai mouvement (ecart CUMULE depuis la derniere touche, petite
   tolerance de bruit), un clic agit toujours, aussitot. L'ancien test (ecart d'un evenement au suivant) est rejoue pour montrer qu'une souris qui envoie des mouvements de 1 a 2 pixels ne reprenait jamais la main.
2. Le clic molette : clic = POSITION de la camera remise (rotation et inclinaison), Ctrl + clic = position ET distance remises, glisser = rotation (pas de saut au debut, memes bornes que les fleches), un clic suivi
   d'un deplacement n'est pas un clic ; Ctrl + molette (haut ou bas) = distance par defaut ; sens du glissement inversable par axe (reglages `camera_inverser_gd` / `camera_inverser_hb`), fleches du clavier intactes.
3. Le bloc d'infos de F1 : en haut a droite par defaut.
4. Branchement dans Jeu : le clic molette n'agit que ou les fleches agissent (terrain libre d'une ville), ne fait rien d'autre, et le zoom ne depend pas de la direction.
"""
import math, os, sys, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..'))
import pyglet
pyglet.options['shadow_window'] = False          # pas de fenetre cachee : le test tourne sans serveur d'affichage
from dq4_pc.fenetre import entrees as EN

try:
    from dq4_pc.fenetre import jeu as FE
except Exception as ex:          # fenetre.py a besoin de pyglet, numpy, unicorn... (l'import seul suffit, aucune fenetre n'est creee)
    FE = None; ERREUR_FE = ex


class SourisApresClavier(unittest.TestCase):
    def test_sans_reference_la_souris_a_la_main(self):
        self.assertTrue(EN.souris_active(None, (10, 10)))
        self.assertTrue(EN.souris_active((10, 10), None))

    def test_tolerance(self):
        t = EN.TOLERANCE_SOURIS
        self.assertFalse(EN.souris_active((100, 100), (100, 100)))                         # evenement sans deplacement (envoye par Windows quand le dessin change sous un pointeur au repos)
        self.assertFalse(EN.souris_active((100, 100), (101, 102)))                         # tremblement du capteur
        self.assertTrue(EN.souris_active((100, 100), (100 + t, 100)))                      # vrai mouvement
        self.assertTrue(EN.souris_active((100, 100), (100 - t, 100)))
        self.assertTrue(EN.souris_active((100, 100), (100, 100 + t)))
        self.assertFalse(EN.souris_active((100, 100), (100 + t - 0.5, 100)))

    def test_ecart_cumule_une_souris_lente_reprend_la_main(self):
        """Mouvement lent : 1 pixel par evenement. L'ancien test (ecart d'un evenement au suivant < 3 px) ne la reprenait jamais ; l'ecart cumule la reprend au bout de quelques evenements (sans delai)."""
        def ancien(pos_prec, pos): return not (pos_prec is None or abs(pos[0] - pos_prec[0]) + abs(pos[1] - pos_prec[1]) < 3)
        chemin = [(100 + i, 100) for i in range(1, 60)]                                    # 59 evenements de 1 pixel
        prec = (100, 100); repris = False
        for p in chemin:
            if ancien(prec, p): repris = True
            prec = p
        self.assertFalse(repris)                                                           # (le defaut d'origine : la souris restait inutilisable tant que le geste n'etait pas rapide)
        g = EN.GardeSouris(); g.clavier((100, 100)); n = 0
        for p in chemin:
            n += 1
            if g.bouge(p): break
        self.assertTrue(g.souris)
        self.assertLessEqual(n, math.ceil(EN.TOLERANCE_SOURIS))                            # 4 evenements de 1 pixel : quelques millisecondes, pas une seconde

    def test_tremblement_ne_reprend_pas(self):
        g = EN.GardeSouris(); g.clavier((300, 200))
        for p in [(300, 200), (301, 200), (300, 201), (299, 199), (301, 201), (300, 200)] * 10: self.assertFalse(g.bouge(p))
        self.assertFalse(g.souris)

    def test_le_tremblement_ne_s_additionne_pas(self):
        """L'ecart est mesure depuis le point de la derniere touche, pas somme d'un evenement a l'autre : aller-retour de 2 px mille fois ne fait pas un mouvement."""
        g = EN.GardeSouris(); g.clavier((50, 50))
        for i in range(1000): self.assertFalse(g.bouge((52, 50) if i % 2 == 0 else (50, 50)))

    def test_clic_agit_toujours_et_rend_la_main(self):
        g = EN.GardeSouris(); g.clavier((10, 10)); self.assertFalse(g.souris)
        g.clic(); self.assertTrue(g.souris)
        self.assertTrue(g.bouge((10, 10)))                                                 # la souris a la main : tout evenement compte, meme sans deplacement

    def test_une_fois_reprise_la_souris_garde_la_main(self):
        g = EN.GardeSouris(); g.clavier((0, 0))
        self.assertTrue(g.bouge((40, 0)))
        self.assertTrue(g.bouge((41, 0))); self.assertTrue(g.bouge((41, 0)))               # plus de tolerance : le survol suit chaque evenement
        g.clavier((41, 0)); self.assertFalse(g.bouge((41, 1)))                             # une nouvelle touche : le clavier reprend la main

    def test_position_inconnue(self):
        g = EN.GardeSouris(); g.clavier(None); self.assertTrue(g.souris); self.assertTrue(g.bouge((5, 5)))


class MoletteGeste(unittest.TestCase):
    def test_clic_simple_remet_la_position(self):
        m = EN.GesteMolette(); m.appui(500, 300)
        self.assertEqual(m.relacher(), 'direction')

    def test_ctrl_clic_remet_les_deux(self):
        m = EN.GesteMolette(); m.appui(500, 300, ctrl=True); self.assertEqual(m.relacher(), 'tout')
        m = EN.GesteMolette(); m.appui(500, 300); self.assertEqual(m.relacher(ctrl=True), 'tout')          # Ctrl enfonce entre l'appui et le relachement : compte aussi

    def test_tremblement_reste_un_clic(self):
        m = EN.GesteMolette(); m.appui(500, 300)
        for p in [(502, 301), (499, 302), (501, 299), (503, 300)]: self.assertEqual(m.deplacer(*p), (0.0, 0.0))
        self.assertEqual(m.relacher(), 'direction')

    def test_glisser_pas_de_saut_au_debut_et_ne_remet_rien(self):
        m = EN.GesteMolette(); m.appui(500, 300)
        self.assertEqual(m.deplacer(503, 300), (0.0, 0.0))                                 # sous le seuil
        self.assertEqual(m.deplacer(520, 300), (0.0, 0.0))                                 # seuil franchi : le geste devient un glissement, la camera ne bouge pas encore (pas de saut des 20 premiers pixels)
        self.assertEqual(m.deplacer(530, 310), (10.0, 10.0))                               # ensuite : l'ecart a l'evenement precedent
        self.assertEqual(m.deplacer(530, 310), (0.0, 0.0))
        self.assertIsNone(m.relacher()); self.assertIsNone(m.relacher())                   # apres un glissement le relachement ne remet rien (ni position, ni distance)
        m.appui(1, 1, ctrl=True); m.deplacer(100, 100); self.assertIsNone(m.relacher(ctrl=True))

    def test_retour_au_point_de_depart_reste_un_glissement(self):
        m = EN.GesteMolette(); m.appui(500, 300); m.deplacer(600, 300); m.deplacer(500, 300)
        self.assertIsNone(m.relacher())                                                    # (on a tourne la camera : ce n'est plus un clic)

    def test_sans_appui_rien(self):
        m = EN.GesteMolette(); self.assertEqual(m.deplacer(10, 10), (0.0, 0.0)); self.assertIsNone(m.relacher())
        m.appui(1, 1); m.annuler(); self.assertIsNone(m.relacher()); self.assertEqual(m.deplacer(300, 300), (0.0, 0.0))


class Rotation(unittest.TestCase):
    A_MIN, A_MAX = -20.0, 40.0

    def piv(self, lacet, angle, dx, dy, h=720.0, limite=None): return EN.pivoter(lacet, angle, dx, dy, h, self.A_MIN, self.A_MAX, limite)

    def test_sens_comme_les_fleches(self):
        lacet, angle = self.piv(0.0, 0.0, 100, 0)
        self.assertGreater(lacet, 0.0); self.assertEqual(angle, 0.0)                       # droite = fleche droite (lacet + )
        lacet, angle = self.piv(0.0, 0.0, 0, 100)
        self.assertEqual(lacet, 0.0); self.assertGreater(angle, 0.0)                       # haut (y vers le haut) = fleche haut (angle + )
        self.assertLess(self.piv(0.0, 0.0, -100, 0)[0], 0.0); self.assertEqual(self.piv(0.0, 10.0, 0, -50)[1], 10.0 - 50 / 720.0 * EN.CAM_SOURIS_ANGLE)

    def test_sensibilite_independante_de_la_resolution(self):
        self.assertAlmostEqual(self.piv(0.0, 0.0, 360, 0, h=720)[0], self.piv(0.0, 0.0, 540, 0, h=1080)[0])        # la moitie de la hauteur = la meme rotation
        self.assertAlmostEqual(self.piv(0.0, 0.0, 360, 0, h=720)[0], EN.CAM_SOURIS_LACET / 2)

    def test_bornes_de_l_angle(self):
        self.assertEqual(self.piv(0.0, 30.0, 0, 5000)[1], self.A_MAX)
        self.assertEqual(self.piv(0.0, -10.0, 0, -5000)[1], self.A_MIN)

    def test_lacet_reste_entre_moins_180_et_180(self):
        l = 170.0
        for _ in range(5): l, _a = self.piv(l, 0.0, 100, 0); self.assertTrue(-180.0 <= l < 180.0)
        l = self.piv(179.0, 0.0, 100, 0)[0]; self.assertLess(l, 0.0)                       # franchit 180 : repart de -180, comme les fleches

    def test_limite_du_lieu(self):
        self.assertEqual(self.piv(100.0, 0.0, 5000, 0, limite=120.0)[0], 120.0)
        self.assertEqual(self.piv(-100.0, 0.0, -5000, 0, limite=120.0)[0], -120.0)

    def test_hauteur_nulle(self):
        self.assertTrue(all(math.isfinite(v) for v in self.piv(0.0, 0.0, 10, 10, h=0)))

    def inv(self, gd, hb, dx, dy, lacet=0.0, angle=10.0, **kw): return EN.pivoter(lacet, angle, dx, dy, 720.0, self.A_MIN, self.A_MAX, kw.get('limite'), gd, hb)

    def test_inversion_gauche_droite_seulement_sur_l_axe_horizontal(self):
        for dx, dy in ((100, 0), (-60, 0), (100, 50), (-30, -80)):
            normal = self.inv(False, False, dx, dy); inv = self.inv(True, False, dx, dy)
            self.assertAlmostEqual(inv[0], -normal[0]); self.assertEqual(inv[1], normal[1])           # le lacet change de sens (de part et d'autre de 0), l'angle ne bouge pas
            self.assertAlmostEqual(inv[0], self.inv(False, False, -dx, dy)[0])                          # = glisser de l'autre cote

    def test_inversion_haut_bas_seulement_sur_l_axe_vertical(self):
        for dx, dy in ((0, 100), (0, -60), (50, 100), (-30, -40)):
            normal = self.inv(False, False, dx, dy); inv = self.inv(False, True, dx, dy)
            self.assertEqual(inv[0], normal[0]); self.assertAlmostEqual(inv[1] - 10.0, -(normal[1] - 10.0))      # l'angle change de sens autour de sa valeur de depart, le lacet ne bouge pas
            self.assertAlmostEqual(inv[1], self.inv(False, False, dx, -dy)[1])

    def test_inversion_des_deux_axes_et_bornes_gardees(self):
        n = self.inv(False, False, 80, 60); i = self.inv(True, True, 80, 60); j = self.inv(False, False, -80, -60)
        self.assertAlmostEqual(i[0], j[0]); self.assertAlmostEqual(i[1], j[1])
        self.assertEqual(self.inv(False, True, 0, -5000, angle=0.0)[1], self.A_MAX)                  # (haut / bas inverse : glisser vers le bas releve la camera, jusqu'a la meme borne)
        self.assertEqual(self.inv(True, False, 5000, 0, lacet=0.0, limite=30.0)[0], -30.0)           # (gauche / droite inverse : la limite du lieu s'applique de l'autre cote)
        self.assertGreater(n[0], 0.0)

    def test_defaut_sans_inversion(self):
        self.assertEqual(EN.pivoter(0.0, 0.0, 100, 50, 720.0, self.A_MIN, self.A_MAX), self.inv(False, False, 100, 50, angle=0.0))          # (les anciens appels sans les deux arguments : comme avant)


class InfosF1(unittest.TestCase):
    def test_en_haut_a_droite_par_defaut(self):
        for l, h in ((1280, 720), (1920, 1080), (2560, 1080), (960, 720)):
            cote, larg = EN.zone_infos(l, h, True, 1.12, 'centre')
            self.assertEqual(cote, 'droite', (l, h)); self.assertGreaterEqual(larg, 260)
            self.assertEqual(EN.zone_infos(l, h, False, 1.12, 'centre')[0], 'droite')      # sans fenetres du jeu : tout l'ecran, toujours a droite

    def test_largeur_laisse_la_colonne_d_interface(self):
        l, h = 1920, 1080; col = 450 * h / 800.0 * 1.12
        cote, larg = EN.zone_infos(l, h, True, 1.12, 'centre')
        self.assertLessEqual(larg, (l - col) / 2)                                          # ne recouvre pas la colonne centree
        self.assertEqual(EN.zone_infos(l, h, False, 1.12, 'centre')[1], l - 20)

    def test_colonne_a_droite_le_bloc_passe_a_gauche(self):
        self.assertEqual(EN.zone_infos(1920, 1080, True, 1.12, 'droite')[0], 'gauche')
        self.assertEqual(EN.zone_infos(1920, 1080, True, 1.12, 'gauche')[0], 'droite')


try:
    from dq4_pc.persistance import reglages as RG
    from dq4_pc.menus import pause as PA
except Exception as ex:          # pause.py a besoin de pyglet (sans affichage : l'import seul suffit)
    PA = None


@unittest.skipIf(PA is None, 'pause.py non importable ici')
class PauseSourisApresClavier(unittest.TestCase):
    """Menu Echap : une touche remet la selection au clavier ; la souris reprend la main au premier vrai mouvement (pas apres un tremblement), un clic aussitot."""
    LIGNES = [(500.0, 400.0 - 40 * i, 780.0, 436.0 - 40 * i, i) for i in range(6)]          # six lignes de 36 px, la premiere en haut

    def pause(self, pos=(640.0, 300.0)):
        garde = EN.GardeSouris()
        jeu = types.SimpleNamespace(reg=RG.Reglages(None), hud=types.SimpleNamespace(pris=None, poser=lambda: None), width=1280, height=720, souris=pos, garde_souris=garde,
                                    son=types.SimpleNamespace(ecoute=False, ecouter=lambda b: None, tick=lambda: None), touches={}, pause_jeu=lambda oui: None)
        P = PA.Pause(jeu); P.ouvert = True; P.pile = ['racine']; P.zones = list(self.LIGNES); P.pos_souris = pos; P.sel['racine'] = 0; P.mode_souris = False
        return P

    def test_lent_un_pixel_par_evenement(self):
        P = self.pause(); P.touche(pyglet.window.key.F5); self.assertFalse(P.mode_souris)             # une touche (sans effet) : retour au clavier
        for i in range(1, 12):                                                                        # le pointeur descend d'un pixel par evenement, de y = 300 (ligne 2, entre 276 et 320 : la ligne 3 est entre 236 et 276)
            P.survol(640.0, 300.0 - i)
            if P.mode_souris: break
        self.assertTrue(P.mode_souris); self.assertLessEqual(i, 5)                                    # au 4e pixel : aucune attente
        P.survol(640.0, 250.0)
        self.assertEqual(P._zone(640.0, 250.0)[0], P.sel['racine'])                                   # la selection suit le pointeur

    def test_tremblement_ne_change_rien(self):
        P = self.pause(); P.touche(pyglet.window.key.F5); avant = P.sel['racine']
        for p in [(641, 300), (640, 301), (639, 299), (640, 300)] * 20: P.survol(*p)
        self.assertFalse(P.mode_souris); self.assertEqual(P.sel['racine'], avant)

    def test_clic_agit_tout_de_suite(self):
        P = self.pause(); P.touche(pyglet.window.key.F5)
        P.clic(640.0, 250.0, 1)                                                                       # clic gauche juste apres la touche
        self.assertTrue(P.mode_souris); self.assertEqual(P.sel['racine'], P._zone(640.0, 250.0)[0])

    def test_pointeur_hors_fenetre_le_premier_mouvement_compte(self):
        P = self.pause(); P.sortie(); P.touche(pyglet.window.key.F5); P.survol(641.0, 250.0)
        self.assertTrue(P.mode_souris)

    def test_ouverture_au_clavier_la_souris_au_repos_ne_prend_rien(self):
        P = self.pause(); P.ouvert = False; P.ouvrir()
        P.survol(640.0, 300.0); P.survol(641.0, 300.0)
        self.assertFalse(P.mode_souris)
        P.survol(660.0, 300.0); self.assertTrue(P.mode_souris)


class Faux:
    """Un `Jeu` minimal : les vraies methodes de fenetre.Jeu (liees a cet objet) travaillent sur un etat factice."""
    def __init__(self, partie=None, **kw):
        MO = FE.MO
        self.moteur = types.SimpleNamespace(etat=types.SimpleNamespace(partie=MO.PARTIE_VILLE if partie is None else partie, effet=None), msg_visible=False, menu_actif=lambda: None)
        self.pause = types.SimpleNamespace(ouvert=False); self.licence = None; self.sauv = None; self.titre = None; self._saisie_nom_en_cours = lambda: False; self.carte_ouverte = False; self.cam_bloquee = False; self.cam_limite = None
        self.hud = types.SimpleNamespace(croix_on=False); self.appui = None; self.molette = EN.GesteMolette(); self.lacet = 0.0; self.angle_cam = 0.0; self.height = 720
        self.cam_axe = {'lacet': [False, False], 'angle': [False, False]}; self.touches = {}; self.reg = {'angle_camera': 0.0, 'distance_camera': 60, 'camera_inverser_gd': False, 'camera_inverser_hb': False,
                                                                                                         'vitesse_camera': 1.0, 'vitesse_accel': 1.5}
        self.zoom = 100.0 / 60; self.zooms = []; self.dist_retour = False; self._pret = True; self.fixe_test = True; self.t_cam = None
        for k, v in kw.items(): setattr(self, k, v)
        for nom in ('_terrain_libre', '_camera_pilotable', '_zoom_possible', 'recentrer_camera', '_ctrl_actif', '_molette_appui', '_molette_glisse', '_molette_relache', 'distance_par_defaut', 'on_mouse_scroll', '_etat_axe', '_maj_camera'):
            setattr(self, nom, types.MethodType(getattr(FE.Jeu, nom), self))
        self._tenue = lambda a: False
        self.regler_zoom = lambda z: self.zooms.append(round(100.0 / z))

    def molette_tournee(self, sy, ctrl=False):
        """Un cran de molette (sy > 0 : vers le haut) ; ctrl : la « Touche speciale » des reglages est tenue."""
        self._tenue = lambda a: ctrl and a == 'modif'; self.on_mouse_scroll(0, 0, 0, sy)

    def clic(self, ctrl=0, x=500, y=300):
        self._molette_appui(x, y, ctrl); self._molette_relache(ctrl)


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class MoletteDansLeJeu(unittest.TestCase):
    def test_clic_en_ville_remet_la_position_seulement(self):
        j = Faux(); j.lacet = 50.0; j.angle_cam = 20.0; j.clic()
        self.assertTrue(all(a[0] for a in j.cam_axe.values())); self.assertEqual(j.zooms, [])           # animation de recentrage lancee (comme « Ctrl + touche camera »), distance intacte

    def test_ctrl_clic_remet_la_position_et_la_distance(self):
        j = Faux(); j.lacet = 50.0; j.clic(ctrl=FE.pyglet.window.key.MOD_CTRL)
        self.assertEqual(j.zooms, []); self.assertTrue(j.dist_retour); self.assertTrue(all(a[0] for a in j.cam_axe.values()))        # les deux : retour anime de la distance (#167, plus de saut immediat) + animation de remise de la position
        j = Faux(); j._tenue = lambda a: a == 'modif'; j.clic()                                         # « Touche speciale » des reglages (Ctrl par defaut) enfoncee
        self.assertEqual(j.zooms, []); self.assertTrue(j.dist_retour); self.assertTrue(all(a[0] for a in j.cam_axe.values()))

    def test_ctrl_molette_haut_ou_bas_remet_la_distance_seulement(self):
        for sy in (1, -1, 2.5, -0.2):
            j = Faux(); j.lacet = 50.0; j.angle_cam = 20.0; j.molette_tournee(sy, ctrl=True)
            self.assertEqual(j.zooms, [], sy); self.assertTrue(j.dist_retour, sy); self.assertEqual((j.lacet, j.angle_cam), (50.0, 20.0)); self.assertFalse(any(a[0] for a in j.cam_axe.values()))          # la position n'y est pour rien
        j = Faux(); j.molette_tournee(0, ctrl=True); self.assertEqual(j.zooms, []); self.assertFalse(j.dist_retour)                      # (un cran nul ne fait rien)

    def test_molette_seule_zoome_toujours(self):
        j = Faux(); j.molette_tournee(1); j.molette_tournee(-1)
        self.assertEqual(j.zooms, [round(100.0 / (j.zoom * 1.1)), round(100.0 / (j.zoom / 1.1))]); self.assertEqual(len(j.zooms), 2); self.assertFalse(j.dist_retour)       # un cran = x1,1 (avant : pas de remise a 100)

    def test_un_cran_de_molette_interrompt_le_retour_anime(self):
        j = Faux(); j.dist_retour = True; j.molette_tournee(1); self.assertFalse(j.dist_retour); self.assertEqual(len(j.zooms), 1)
        j = Faux(); j.dist_retour = True; j.molette_tournee(1, ctrl=True); self.assertTrue(j.dist_retour); self.assertEqual(j.zooms, [])     # (Ctrl + molette le relance)

    def test_ctrl_molette_hors_terrain_ou_dans_un_menu_ne_remet_rien(self):
        j = Faux(); j.pause.ouvert = True; j.pause.molette = lambda sy: None; j.molette_tournee(1, ctrl=True); self.assertEqual(j.zooms, [])
        j = Faux(); j.moteur.msg_visible = True; j.molette_tournee(1, ctrl=True); self.assertEqual(j.zooms, [])
        j = Faux(); j.moteur.etat.partie = FE.MO.PARTIE_COMBAT; j.molette_tournee(-1, ctrl=True); self.assertEqual(j.zooms, [])
        j = Faux(); j._pret = False; j.molette_tournee(1, ctrl=True); self.assertEqual(j.zooms, [])

    def test_ctrl_molette_sur_la_carte_du_monde_remet_la_distance(self):
        j = Faux(partie=FE.MO.PARTIE_CHAMP); j.molette_tournee(1, ctrl=True); self.assertTrue(j.dist_retour); self.assertEqual(j.zooms, [])

    COMBOS = ((False, False), (True, False), (False, True), (True, True))

    def glisse(self, gd, hb, ndy=-40):
        j = Faux(); j.reg['camera_inverser_gd'] = gd; j.reg['camera_inverser_hb'] = hb
        j._molette_appui(500, 300, 0); j._molette_glisse(520, 300); j._molette_glisse(620, 300 + ndy)          # 100 px vers la droite, ndy vers le haut (y pyglet vers le haut)
        return j

    def test_inversion_du_glissement_dans_le_jeu_axe_par_axe(self):
        base = self.glisse(False, False); self.assertGreater(base.lacet, 0.0); self.assertGreater(self.glisse(False, False, 40).angle_cam, 0.0)         # sans inversion : droite = lacet +, haut = angle +
        for gd, hb in self.COMBOS:
            j = self.glisse(gd, hb, 40); ref = self.glisse(False, False, 40)
            self.assertAlmostEqual(j.lacet, -ref.lacet if gd else ref.lacet)                          # gauche / droite : le lacet change de sens exactement quand « Inverser gauche / droite » est a Oui
            self.assertAlmostEqual(j.angle_cam, -ref.angle_cam if hb else ref.angle_cam)              # haut / bas : l'angle change de sens exactement quand « Inverser haut / bas » est a Oui
            self.assertEqual(j.reg['angle_camera'], round(j.angle_cam, 2))                             # (l'angle est enregistre comme avant)

    def test_inversion_ne_touche_pas_les_fleches_du_clavier(self):
        """Fleches gauche / droite / haut / bas tenues 30 images (vraie `Jeu._maj_camera`) : meme lacet et meme angle quels que soient les deux reglages d'inversion."""
        for tenue in ('cam_droite', 'cam_gauche', 'cam_haut', 'cam_bas'):
            res = []
            for gd, hb in self.COMBOS:
                j = Faux(); j.reg['camera_inverser_gd'] = gd; j.reg['camera_inverser_hb'] = hb; j._tenue = lambda a, t=tenue: a == t
                for _ in range(30): j._maj_camera()
                res.append((round(j.lacet, 6), round(j.angle_cam, 6)))
            self.assertEqual(len(set(res)), 1, (tenue, res)); self.assertNotEqual(res[0], (0.0, 0.0), tenue)             # (la camera a bien bouge, et pareil dans les 4 cas)
        j = Faux(); j._tenue = lambda a: a == 'cam_droite'; [j._maj_camera() for _ in range(30)]; self.assertGreater(j.lacet, 0.0)      # (la fleche droite tourne vers + : le sens d'origine du glissement vers la droite)

    def test_inversion_sans_effet_sur_les_remises_a_zero(self):
        for gd, hb in self.COMBOS:
            j = Faux(); j.reg['camera_inverser_gd'] = gd; j.reg['camera_inverser_hb'] = hb; j.clic(); self.assertTrue(all(a[0] for a in j.cam_axe.values()))
            j = Faux(); j.reg['camera_inverser_gd'] = gd; j.reg['camera_inverser_hb'] = hb; j.molette_tournee(1, ctrl=True); self.assertTrue(j.dist_retour); self.assertEqual(j.zooms, [])

    def test_clic_suivi_d_un_deplacement_n_est_pas_un_clic(self):
        K = FE.pyglet.window.key
        for ctrl in (0, K.MOD_CTRL):
            j = Faux(); j.lacet = 50.0; j._molette_appui(500, 300, ctrl); j._molette_glisse(530, 300); j._molette_glisse(500, 300); j._molette_relache(ctrl)      # revenu au point de depart : toujours un glissement
            self.assertFalse(any(a[0] for a in j.cam_axe.values())); self.assertEqual(j.zooms, [])
            j = Faux(); j._molette_appui(500, 300, ctrl); j._molette_glisse(502, 301); j._molette_relache(ctrl)                                                 # un simple tremblement reste un clic
            self.assertTrue(all(a[0] for a in j.cam_axe.values())); self.assertEqual((j.zooms, j.dist_retour), ([], bool(ctrl)))

    def test_glisser_tourne_comme_les_fleches(self):
        j = Faux(); j._molette_appui(500, 300, 0); j._molette_glisse(520, 300); j._molette_glisse(620, 360)
        self.assertGreater(j.lacet, 0.0); self.assertGreater(j.angle_cam, 0.0); self.assertEqual(j.reg['angle_camera'], round(j.angle_cam, 2))
        j._molette_relache(0)
        self.assertFalse(any(a[0] for a in j.cam_axe.values())); self.assertEqual(j.zooms, [])         # le relachement d'un glissement ne remet rien

    def test_glisser_annule_un_recentrage_en_cours(self):
        j = Faux(); j.recentrer_camera(); j._molette_appui(500, 300, 0); j._molette_glisse(520, 300); j._molette_glisse(560, 300)
        self.assertFalse(any(a[0] for a in j.cam_axe.values()))

    def test_lieu_qui_interdit_la_camera(self):
        j = Faux(cam_bloquee=True); j.clic(); self.assertFalse(any(a[0] for a in j.cam_axe.values()))
        j = Faux(cam_bloquee=True); j._molette_appui(1, 1, 0); j._molette_glisse(50, 50); j._molette_glisse(90, 90); self.assertEqual((j.lacet, j.angle_cam), (0.0, 0.0))
        j = Faux(cam_bloquee=True); j.clic(ctrl=FE.pyglet.window.key.MOD_CTRL); self.assertTrue(j.dist_retour); self.assertFalse(any(a[0] for a in j.cam_axe.values()))       # (la distance reste reglable : comme la molette ; la position, non)
        j = Faux(cam_bloquee=True); j.molette_tournee(1, ctrl=True); self.assertTrue(j.dist_retour)

    def test_limite_de_rotation_du_lieu(self):
        j = Faux(cam_limite=30.0); j._molette_appui(0, 0, 0); j._molette_glisse(10, 0); j._molette_glisse(5000, 0); self.assertEqual(j.lacet, 30.0)

    def test_hors_terrain_rien_ne_se_passe(self):
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
            elif nom == 'croix': j.hud.croix_on = True
            elif nom == 'bouton': j.appui = (12, 0, 16)
            return j
        for nom in ('pause', 'message', 'menu', 'combat', 'titre', 'licence', 'sauvegardes', 'nom', 'carte', 'effet', 'croix', 'bouton'):
            for ctrl in (0, FE.pyglet.window.key.MOD_CTRL):
                j = faux(nom); j.lacet = 10.0; j.clic(ctrl=ctrl); j._molette_appui(0, 0, ctrl); j._molette_glisse(50, 50); j._molette_glisse(120, 90); j._molette_relache(ctrl)
                retour = bool(nom == 'effet' and ctrl)                                                           # (pendant un effet d'ecran la molette zoome encore, comme avant ; les fleches ne tournent pas)
                self.assertEqual((j.lacet, j.angle_cam, j.zooms, j.dist_retour), (10.0, 0.0, [], retour), '%s ctrl=%s' % (nom, ctrl))
                self.assertFalse(any(a[0] for a in j.cam_axe.values()), nom)

    def test_carte_du_monde_zoom_oui_direction_non(self):
        j = Faux(partie=FE.MO.PARTIE_CHAMP); j.clic(); self.assertFalse(any(a[0] for a in j.cam_axe.values()))          # pas de rotation sur la carte du monde (comme les fleches)
        j.clic(ctrl=FE.pyglet.window.key.MOD_CTRL); self.assertTrue(j.dist_retour)                                    # mais la distance, oui (comme la molette)

    def test_defaut_du_zoom_est_celui_des_reglages(self):
        self.assertEqual(float(FE.RG.DEFAUT['distance_camera']), 100.0)


if __name__ == '__main__':
    unittest.main(verbosity=1)
