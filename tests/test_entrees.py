"""Test des entrees souris / clavier : logique pure (entrees.py) et branchement dans la fenetre (fenetre.Jeu), sans ouvrir de fenetre.

    python3 tests/test_entrees.py

1. La souris apres le clavier (« passer du clavier a la souris rend la souris inutilisable pendant 1 s ») : le survol reprend la main au premier vrai mouvement (ecart CUMULE depuis la derniere touche, petite
   tolerance de bruit), un clic agit toujours, aussitot. L'ancien test (ecart d'un evenement au suivant) est rejoue pour montrer qu'une souris qui envoie des mouvements de 1 a 2 pixels ne reprenait jamais la main.
2. Le clic molette (D-233) : clic = camera recentree, glisser a gauche / a droite = rotation (pas de saut au debut, memes bornes que les fleches, le deplacement vertical ne tourne rien), un clic suivi d'un deplacement
   n'est pas un clic ; sens du glissement inversable (reglage `camera_inverser_gd`), fleches du clavier non. Le zoom, l'inclinaison et leurs gestes (molette, Ctrl) ont ete retires en #264 et ne reviennent pas.
3. Le bloc d'infos de F1 : en haut a droite par defaut.
4. Branchement dans Jeu : fleches gauche / droite = rotation de la camera (vitesse de camera, l'accelerateur n'y change rien), les deux ensemble = recentrage, deplacement du heros qui suit la camera ; le clic molette
   n'agit que ou les fleches agissent (terrain libre d'une ville, hors scene du jeu), ne fait rien d'autre, et la molette ne fait plus rien sur le terrain.
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
    def test_clic_simple_recentre(self):
        m = EN.GesteMolette(); m.appui(500, 300)
        self.assertTrue(m.relacher())

    def test_tremblement_reste_un_clic(self):
        m = EN.GesteMolette(); m.appui(500, 300)
        for p in [(502, 301), (499, 302), (501, 299), (503, 300)]: self.assertEqual(m.deplacer(*p), 0.0)
        self.assertTrue(m.relacher())

    def test_glisser_pas_de_saut_au_debut_et_ne_recentre_rien(self):
        m = EN.GesteMolette(); m.appui(500, 300)
        self.assertEqual(m.deplacer(503, 300), 0.0)                                        # sous le seuil
        self.assertEqual(m.deplacer(520, 300), 0.0)                                        # seuil franchi : le geste devient un glissement, la camera ne bouge pas encore (pas de saut des 20 premiers pixels)
        self.assertEqual(m.deplacer(530, 310), 10.0)                                       # ensuite : l'ecart horizontal a l'evenement precedent (le vertical ne compte pas)
        self.assertEqual(m.deplacer(530, 310), 0.0)
        self.assertFalse(m.relacher()); self.assertFalse(m.relacher())                     # apres un glissement le relachement ne recentre rien

    def test_glisser_vertical_ne_tourne_pas_mais_n_est_plus_un_clic(self):
        m = EN.GesteMolette(); m.appui(500, 300)
        for y in (330, 380, 450): self.assertEqual(m.deplacer(500, y), 0.0)
        self.assertFalse(m.relacher())

    def test_retour_au_point_de_depart_reste_un_glissement(self):
        m = EN.GesteMolette(); m.appui(500, 300); m.deplacer(600, 300); m.deplacer(500, 300)
        self.assertFalse(m.relacher())                                                     # (on a tourne la camera : ce n'est plus un clic)

    def test_sans_appui_rien(self):
        m = EN.GesteMolette(); self.assertEqual(m.deplacer(10, 10), 0.0); self.assertFalse(m.relacher())
        m.appui(1, 1); m.annuler(); self.assertFalse(m.relacher()); self.assertEqual(m.deplacer(300, 300), 0.0)


class Rotation(unittest.TestCase):
    def piv(self, lacet, dx, h=720.0, limite=None, inv=False): return EN.pivoter(lacet, dx, h, limite, inv)

    def test_sens_comme_les_fleches(self):
        self.assertGreater(self.piv(0.0, 100), 0.0)                                        # droite = fleche droite (lacet + )
        self.assertLess(self.piv(0.0, -100), 0.0)

    def test_sensibilite_independante_de_la_resolution(self):
        self.assertAlmostEqual(self.piv(0.0, 360, h=720), self.piv(0.0, 540, h=1080))      # la moitie de la hauteur = la meme rotation
        self.assertAlmostEqual(self.piv(0.0, 360, h=720), EN.CAM_SOURIS_LACET / 2)

    def test_lacet_reste_entre_moins_180_et_180(self):
        l = 170.0
        for _ in range(5): l = self.piv(l, 100); self.assertTrue(-180.0 <= l < 180.0)
        self.assertLess(self.piv(179.0, 100), 0.0)                                         # franchit 180 : repart de -180, comme les fleches

    def test_limite_du_lieu(self):
        self.assertEqual(self.piv(100.0, 5000, limite=120.0), 120.0)
        self.assertEqual(self.piv(-100.0, -5000, limite=120.0), -120.0)

    def test_hauteur_nulle(self):
        self.assertTrue(math.isfinite(self.piv(0.0, 10, h=0)))

    def test_inversion_gauche_droite(self):
        for dx in (100, -60, 5):
            normal = self.piv(0.0, dx); inv = self.piv(0.0, dx, inv=True)
            self.assertAlmostEqual(inv, -normal); self.assertAlmostEqual(inv, self.piv(0.0, -dx))      # = glisser de l'autre cote
        self.assertEqual(self.piv(0.0, 5000, limite=30.0, inv=True), -30.0)                              # (la limite du lieu s'applique de l'autre cote)

    def test_defaut_sans_inversion(self):
        self.assertEqual(EN.pivoter(0.0, 100, 720.0), self.piv(0.0, 100))


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
        self.moteur = types.SimpleNamespace(etat=types.SimpleNamespace(partie=MO.PARTIE_VILLE if partie is None else partie, effet=None, cam_libre=False, cam_rot=None), msg_visible=False, menu_actif=lambda: None)
        self.pause = types.SimpleNamespace(ouvert=False); self.licence = None; self.sauv = None; self.titre = None; self._saisie_nom_en_cours = lambda: False; self.carte_ouverte = False; self.carte_nom = None
        self.cam_bloquee = False; self.cam_jeu = False; self.cam_limite = None; self.cam_w = 0.0
        self.hud = types.SimpleNamespace(croix_on=False, croix_bits=lambda: 0); self.appui = None; self.molette = EN.GesteMolette(); self.lacet = 0.0; self.height = 720
        self.cam_axe = {'lacet': [False, False]}; self.touches = {}; self.reg = {'camera_inverser_gd': False, 'vitesse_camera': 1.0, 'vitesse_accel': 1.5}
        self._pret = True; self.fixe_test = True; self.t_cam = None
        for k, v in kw.items(): setattr(self, k, v)
        for nom in ('_terrain_libre', '_camera_pilotable', 'recentrer_camera', '_molette_appui', '_molette_glisse', '_molette_relache', '_etat_axe', '_maj_camera', '_lacet_eff', '_tourner_dir', 'pad', 'on_mouse_scroll'):
            setattr(self, nom, types.MethodType(getattr(FE.Jeu, nom), self))
        self._tenue = lambda a: False

    def tenir(self, *actions): self._tenue = lambda a: a in actions

    def images(self, n):
        for _ in range(n): self._maj_camera()

    def clic(self, x=500, y=300):
        self._molette_appui(x, y); self._molette_relache()


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class MoletteDansLeJeu(unittest.TestCase):
    def recentre(self, j): return j.cam_axe['lacet'][0]

    def test_clic_en_ville_recentre(self):
        j = Faux(); j.lacet = 50.0; j.clic()
        self.assertTrue(self.recentre(j)); self.assertEqual(j.lacet, 50.0)                 # animation de recentrage lancee (comme les deux fleches ensemble), la rotation ne saute pas

    def glisse(self, gd, ndy=-40):
        j = Faux(); j.reg['camera_inverser_gd'] = gd
        j._molette_appui(500, 300); j._molette_glisse(520, 300); j._molette_glisse(620, 300 + ndy)          # 100 px vers la droite, ndy vers le haut (y pyglet vers le haut)
        return j

    def test_inversion_du_glissement_dans_le_jeu(self):
        self.assertGreater(self.glisse(False).lacet, 0.0)                                  # sans inversion : droite = lacet +
        for dy in (-40, 0, 40):
            self.assertAlmostEqual(self.glisse(True, dy).lacet, -self.glisse(False, dy).lacet)
        self.assertAlmostEqual(self.glisse(False, 40).lacet, self.glisse(False, -40).lacet)      # le deplacement vertical ne change rien

    def test_inversion_ne_touche_pas_les_fleches_du_clavier(self):
        """Fleches gauche / droite tenues 30 images (vraie `Jeu._maj_camera`) : meme lacet quel que soit le reglage d'inversion."""
        for tenue in ('cam_droite', 'cam_gauche'):
            res = []
            for gd in (False, True):
                j = Faux(); j.reg['camera_inverser_gd'] = gd; j.tenir(tenue); j.images(30); res.append(round(j.lacet, 6))
            self.assertEqual(len(set(res)), 1, (tenue, res)); self.assertNotEqual(res[0], 0.0, tenue)
        j = Faux(); j.tenir('cam_droite'); j.images(30); self.assertGreater(j.lacet, 0.0)      # (la fleche droite tourne vers + : le sens d'origine du glissement vers la droite)

    def test_inversion_sans_effet_sur_le_recentrage(self):
        for gd in (False, True):
            j = Faux(); j.reg['camera_inverser_gd'] = gd; j.clic(); self.assertTrue(self.recentre(j))

    def test_clic_suivi_d_un_deplacement_n_est_pas_un_clic(self):
        j = Faux(); j.lacet = 50.0; j._molette_appui(500, 300); j._molette_glisse(530, 300); j._molette_glisse(500, 300); j._molette_relache()      # revenu au point de depart : toujours un glissement
        self.assertFalse(self.recentre(j))
        j = Faux(); j._molette_appui(500, 300); j._molette_glisse(502, 301); j._molette_relache()                                                 # un simple tremblement reste un clic
        self.assertTrue(self.recentre(j))

    def test_glisser_tourne_comme_les_fleches(self):
        j = Faux(); j._molette_appui(500, 300); j._molette_glisse(520, 300); j._molette_glisse(620, 360)
        self.assertGreater(j.lacet, 0.0)
        j._molette_relache(); self.assertFalse(self.recentre(j))                           # le relachement d'un glissement ne recentre rien
        j = Faux(); j._molette_appui(500, 300); j._molette_glisse(500, 340); j._molette_glisse(500, 480); self.assertEqual(j.lacet, 0.0)      # purement vertical : rien ne tourne (plus d'inclinaison)

    def test_glisser_annule_un_recentrage_en_cours(self):
        j = Faux(); j.recentrer_camera(); j._molette_appui(500, 300); j._molette_glisse(520, 300); j._molette_glisse(560, 300)
        self.assertFalse(self.recentre(j))

    def test_lieu_qui_interdit_la_camera(self):
        j = Faux(cam_bloquee=True); j.clic(); self.assertFalse(self.recentre(j))
        j = Faux(cam_bloquee=True); j._molette_appui(1, 1); j._molette_glisse(50, 50); j._molette_glisse(90, 90); self.assertEqual(j.lacet, 0.0)

    def test_scene_du_jeu(self):
        """Le jeu l'emporte dans ses scenes (travelling, plan fixe, cible = un personnage : cam_jeu ; camera libre) : ni glisser, ni clic, ni fleches."""
        for nom in ('cam_jeu', 'libre'):
            j = Faux()
            if nom == 'cam_jeu': j.cam_jeu = True
            else: j.moteur.etat.cam_libre = True; j.moteur.etat.cam_rot = (30.0, 0.0, 0.0)
            j.clic(); self.assertFalse(self.recentre(j), nom)
            j._molette_appui(1, 1); j._molette_glisse(50, 50); j._molette_glisse(90, 50); self.assertEqual(j.lacet, 0.0, nom)
            j.tenir('cam_droite'); j.images(30); self.assertEqual(j.lacet, 0.0, nom)

    def test_le_terrain_change_entre_l_appui_et_le_relachement(self):
        """Un message qui s'ouvre, une scene du jeu ou un lieu verrouille la camera pendant que le bouton du milieu est enfonce : le relachement ne recentre rien, et le glissement ne tourne rien."""
        for nom in ('message', 'cam_jeu', 'cam_bloquee'):
            j = Faux(); j.lacet = 40.0; j._molette_appui(500, 300)
            if nom == 'message': j.moteur.msg_visible = True
            else: setattr(j, nom, True)
            j._molette_glisse(520, 300); j._molette_glisse(560, 300); self.assertEqual(j.lacet, 40.0, nom)
            j._molette_relache(); self.assertFalse(self.recentre(j), nom)
            j = Faux(); j.lacet = 40.0; j._molette_appui(500, 300)
            if nom == 'message': j.moteur.msg_visible = True
            else: setattr(j, nom, True)
            j._molette_relache(); self.assertFalse(self.recentre(j), nom)                                          # un clic simple, mais le terrain n'est plus libre

    def test_limite_de_rotation_du_lieu(self):
        j = Faux(cam_limite=30.0); j._molette_appui(0, 0); j._molette_glisse(10, 0); j._molette_glisse(5000, 0); self.assertEqual(j.lacet, 30.0)
        j = Faux(cam_limite=30.0); j.tenir('cam_gauche'); j.images(120); self.assertEqual(j.lacet, -30.0)

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
            elif nom == 'ecran-titre': j.carte_nom = FE.CARTE_TITRE
            return j
        for nom in ('pause', 'message', 'menu', 'combat', 'titre', 'licence', 'sauvegardes', 'nom', 'carte', 'effet', 'croix', 'bouton', 'ecran-titre'):
            j = faux(nom); j.lacet = 10.0; j.clic(); j._molette_appui(0, 0); j._molette_glisse(50, 50); j._molette_glisse(120, 90); j._molette_relache()
            self.assertEqual(j.lacet, 10.0, nom); self.assertFalse(self.recentre(j), nom)
            if nom in ('croix', 'bouton'): continue                                                           # (la croix et les boutons de l'ecran sont tenus a la souris : ils ne bloquent que le clic molette, pas les fleches du clavier)
            j = faux(nom); j.lacet = 10.0; j.tenir('cam_droite', 'cam_gauche'); j.images(30); self.assertEqual(j.lacet, 10.0, nom); self.assertFalse(self.recentre(j), nom)

    def test_carte_du_monde_pas_de_rotation(self):
        j = Faux(partie=FE.MO.PARTIE_CHAMP); j.clic(); self.assertFalse(self.recentre(j))          # pas de rotation sur la carte du monde (comme les fleches)
        j.tenir('cam_droite'); j.images(30); self.assertEqual(j.lacet, 0.0)

    def test_la_molette_ne_fait_plus_rien_sur_le_terrain(self):
        for partie in (None, FE.MO.PARTIE_CHAMP):
            j = Faux(partie=partie); j.lacet = 20.0; j.tenir('modif'); j.on_mouse_scroll(0, 0, 0, 1); j.on_mouse_scroll(0, 0, 0, -3)
            self.assertEqual(j.lacet, 20.0); self.assertFalse(self.recentre(j))
            self.assertFalse(hasattr(j, 'zoom'))


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class FlechesDansLeJeu(unittest.TestCase):
    def test_fleches_tournent_la_camera(self):
        j = Faux(); j.tenir('cam_droite'); j.images(30); self.assertAlmostEqual(j.lacet, 30 * FE.CAM_LACET_VIT / 60.0)          # 30 images a 60 Hz de test : 50 degres
        j = Faux(); j.tenir('cam_gauche'); j.images(30); self.assertAlmostEqual(j.lacet, -30 * FE.CAM_LACET_VIT / 60.0)

    def test_vitesse_de_camera(self):
        for v in (1.0, 2.0, 4.0):
            j = Faux(); j.reg['vitesse_camera'] = v; j.tenir('cam_droite'); j.images(10); self.assertAlmostEqual(j.lacet, 10 * FE.CAM_LACET_VIT * v / 60.0)

    def test_l_accelerateur_n_accelere_pas_la_camera(self):
        j = Faux(); j.tenir('cam_droite'); j.images(30); ref = j.lacet
        j = Faux(); j.tenir('cam_droite', 'accel'); j.images(30); self.assertEqual(j.lacet, ref)
        j = Faux(); j.reg['vitesse_accel'] = 2.0; j.tenir('cam_gauche', 'accel'); j.images(30); self.assertAlmostEqual(j.lacet, -ref)

    def test_haut_bas_ne_font_rien_sur_le_terrain(self):
        j = Faux(); j.tenir('cam_haut', 'cam_bas'); j.images(30); self.assertEqual(j.lacet, 0.0); self.assertEqual(j.pad(), 0)          # (ils ne servent que dans les menus : plus d'inclinaison)

    def test_lacet_boucle_entre_moins_180_et_180(self):
        j = Faux(); j.lacet = 175.0; j.tenir('cam_droite'); j.images(5); self.assertTrue(-180.0 <= j.lacet < 0.0, j.lacet)

    def test_les_deux_fleches_recentrent_par_une_animation(self):
        for depart in (80.0, -80.0, 170.0, -3.0):
            j = Faux(); j.lacet = depart; j.tenir('cam_gauche', 'cam_droite'); j.images(1)
            self.assertTrue(j.cam_axe['lacet'][0] or j.lacet == 0.0); self.assertLess(abs(j.lacet), abs(depart) + 1e-9); self.assertLessEqual(abs(depart) - abs(j.lacet), max(FE.CAM_RECENTRE_LACET, abs(depart) * 5.0) / 60.0 + 1e-9)      # lancee dans la meme image, d'un pas seulement : rien ne saute
            j.tenir(); suite = [j.lacet]
            for _ in range(240):
                if j.lacet == 0.0: break
                j.images(1); suite.append(j.lacet)
            self.assertEqual(j.lacet, 0.0, depart); self.assertFalse(j.cam_axe['lacet'][0])
            self.assertTrue(all(abs(b) < abs(a) for a, b in zip(suite, suite[1:])), 'le recentrage se rapproche de 0 a chaque image (%s)' % depart)      # (le plus court chemin, sans a-coup)
            if abs(depart) > 10.0: self.assertGreater(len(suite), 3, 'une animation, pas un saut')

    def test_une_fleche_restee_enfoncee_apres_la_pression_double_ne_fait_rien(self):
        j = Faux(); j.lacet = 60.0; j.tenir('cam_gauche', 'cam_droite'); j.images(1); j.tenir('cam_droite'); j.images(10)
        self.assertTrue(j.cam_axe['lacet'][0]); self.assertLess(j.lacet, 60.0)                              # le recentrage continue, la fleche restante (relachement jamais simultane) ne tourne pas
        j.tenir(); j.images(1); j.tenir('cam_droite'); l = j.lacet; j.images(5)                              # nouvelle pression seule : le recentrage est annule et la camera tourne a nouveau
        self.assertFalse(j.cam_axe['lacet'][0]); self.assertGreater(j.lacet, l)

    def test_deplacement_du_heros_suit_la_camera(self):
        MO = FE.MO
        for lacet, voulu in ((0.0, MO.HAUT), (45.0, MO.HAUT | MO.DROITE), (90.0, MO.DROITE), (180.0, MO.BAS), (-90.0, MO.GAUCHE), (-180.0, MO.BAS), (20.0, MO.HAUT), (30.0, MO.HAUT | MO.DROITE)):
            j = Faux(); j.lacet = lacet; j.tenir('haut'); self.assertEqual(j.pad(), voulu, lacet)
        j = Faux(); j.lacet = 90.0; j.tenir('haut', 'droite'); self.assertEqual(j.pad(), MO.DROITE | MO.BAS)         # une diagonale tourne aussi
        j = Faux(); j.lacet = 90.0; j.tenir('A'); self.assertEqual(j.pad(), MO.A)                                      # les boutons ne tournent pas

    def test_deplacement_sans_rotation_la_ou_la_camera_ne_tourne_pas(self):
        MO = FE.MO
        for nom in ('champ', 'scene', 'verrou', 'titre'):
            j = Faux(partie=MO.PARTIE_CHAMP if nom == 'champ' else None); j.lacet = 90.0
            if nom == 'scene': j.cam_w = 1.0                                                                       # le jeu tient la camera (poids 1) : la rotation du joueur est effacee
            if nom == 'verrou': j.cam_w = 1.0; j.cam_bloquee = True
            if nom == 'titre': j.carte_nom = FE.CARTE_TITRE
            j.tenir('haut'); self.assertEqual(j.pad(), MO.HAUT, nom); self.assertEqual(j._lacet_eff(), 0.0, nom)

    def test_rotation_effacee_en_douceur_pendant_une_scene(self):
        j = Faux(); j.lacet = 100.0
        for w, voulu in ((0.0, 100.0), (0.25, 75.0), (1.0, 0.0)):
            j.cam_w = w; self.assertAlmostEqual(j._lacet_eff(), voulu)

    def test_dans_les_menus_les_fleches_sont_des_directions(self):
        MO = FE.MO
        j = Faux(); j.moteur.msg_visible = True; j.lacet = 90.0
        for act, bit in (('cam_haut', MO.HAUT), ('cam_bas', MO.BAS), ('cam_gauche', MO.GAUCHE), ('cam_droite', MO.DROITE)):
            j.tenir(act); self.assertEqual(j.pad(), bit, act)


if __name__ == '__main__':
    unittest.main(verbosity=1)
