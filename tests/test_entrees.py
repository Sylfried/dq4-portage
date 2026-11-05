"""Test des entrees souris / clavier : logique pure (entrees.py) et branchement dans la fenetre (fenetre.Jeu), sans ouvrir de fenetre.

    python3 tests/test_entrees.py

1. La souris apres le clavier (« passer du clavier a la souris rend la souris inutilisable pendant 1 s ») : le survol reprend la main au premier vrai mouvement (ecart CUMULE depuis la derniere touche, petite
   tolerance de bruit), un clic agit toujours, aussitot. L'ancien test (ecart d'un evenement au suivant) est rejoue pour montrer qu'une souris qui envoie des mouvements de 1 a 2 pixels ne reprenait jamais la main.
2. Le clic molette (D-233, D-234) : clic = la camera revient au nord (par le jeu), glisser a gauche / a droite = rotation demandee (pas de saut au debut, le deplacement vertical ne tourne rien), un clic suivi d'un deplacement
   n'est pas un clic ; sens du glissement inversable (reglage `camera_inverser_gd`), fleches du clavier non. Le zoom, l'inclinaison et leurs gestes (molette, Ctrl) ont ete retires en #264 et ne reviennent pas.
3. Le bloc d'infos de F1 : en haut a droite par defaut.
4. Branchement dans Jeu (D-234) : la camera est celle du JEU. Fleches gauche / droite = boutons de camera du jeu (bits 4 et 5 des touches tenues), les deux ensemble = retour au nord (une seule fois), vitesse de camera = crans de plus
   par pas, l'accelerateur n'y change rien ; la visionneuse ne tourne NI la camera NI les directions du heros a cote du jeu (le jeu s'en charge, comme sur mobile, y compris dans ses scenes) ; le clic molette n'agit que sur le terrain
   libre d'une ville, ne fait rien d'autre, et la molette ne fait plus rien sur le terrain. Le test avec le vrai moteur (rotation, marche relative a la camera, retour au nord) est tests/test_camera_moteur.py.
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
    def piv(self, demande, dx, h=720.0, inv=False, maxi=180.0): return EN.pivoter(demande, dx, h, inv, maxi)

    def test_sens_comme_les_fleches(self):
        self.assertGreater(self.piv(0.0, 100), 0.0)                                        # droite = fleche droite
        self.assertLess(self.piv(0.0, -100), 0.0)

    def test_sensibilite_independante_de_la_resolution(self):
        self.assertAlmostEqual(self.piv(0.0, 360, h=720), self.piv(0.0, 540, h=1080))      # la moitie de la hauteur = la meme rotation
        self.assertAlmostEqual(self.piv(0.0, 360, h=720), EN.CAM_SOURIS_LACET / 2)

    def test_ce_qui_reste_a_tourner_s_ajoute(self):
        self.assertAlmostEqual(self.piv(10.0, 100), 10.0 + self.piv(0.0, 100))
        self.assertAlmostEqual(self.piv(10.0, -100), 10.0 + self.piv(0.0, -100))

    def test_plafond(self):
        """Un grand glissement ne fait pas tourner la camera longtemps apres le relachement : la rotation demandee est plafonnee (et ne boucle pas : le jeu tourne par crans, il n'y a plus de cap a ramener entre -180 et 180)."""
        self.assertEqual(self.piv(100.0, 5000), 180.0); self.assertEqual(self.piv(-100.0, -5000), -180.0)
        self.assertEqual(self.piv(0.0, 5000, maxi=45.0), 45.0)

    def test_hauteur_nulle(self):
        self.assertTrue(math.isfinite(self.piv(0.0, 10, h=0)))

    def test_inversion_gauche_droite(self):
        for dx in (100, -60, 5):
            normal = self.piv(0.0, dx); inv = self.piv(0.0, dx, inv=True)
            self.assertAlmostEqual(inv, -normal); self.assertAlmostEqual(inv, self.piv(0.0, -dx))      # = glisser de l'autre cote

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


class MoteurFactice:
    """Le jeu vu par la visionneuse : accepte (ou refuse) le bouton de camera de ce pas, le garde en attente (TownPlayerManager + 0x698) et tourne d'UN cran au pas suivant, sauf si `camera_tourner` en a fait n tout de suite."""
    def __init__(self):
        MO = FE.MO
        self.etat = types.SimpleNamespace(partie=MO.PARTIE_VILLE, effet=None, cam_libre=False, cam_rot=None, cam_pos=None, cam_cible=None)
        self.msg_visible = False; self.menu_actif = lambda: None
        self.accepte = True; self.attente = 0; self.crans = 0; self.appels = []; self.bits = []

    def camera_attente(self): return self.attente

    def camera_tourner(self, sens, fois): self.appels.append((sens, fois)); self.crans += fois * (1 if sens == FE.MO.ROT_CAM_DROITE else -1); self.attente = 0

    def pas(self, bits):
        """Un pas du moteur avec ces boutons de camera."""
        MO = FE.MO; self.bits.append(bits)
        if self.attente:                                                            # rotation en attente depuis le pas d'avant (non consommee par camera_tourner) : le jeu tourne d'un cran
            self.crans += 1 if self.attente == MO.ROT_CAM_DROITE else -1; self.attente = 0
        if self.accepte and bits in (MO.CAM_D, MO.CAM_G): self.attente = MO.ROT_CAM_DROITE if bits == MO.CAM_D else MO.ROT_CAM_GAUCHE


class Faux:
    """Un `Jeu` minimal : les vraies methodes de fenetre.Jeu (liees a cet objet) travaillent sur un moteur factice qui accepte ou refuse les boutons de camera."""
    def __init__(self, partie=None, **kw):
        MO = FE.MO
        self.moteur = MoteurFactice()
        if partie is not None: self.moteur.etat.partie = partie
        self.pause = types.SimpleNamespace(ouvert=False); self.licence = None; self.sauv = None; self.titre = None; self._saisie_nom_en_cours = lambda: False; self.carte_ouverte = False; self.carte_nom = None
        self.hud = types.SimpleNamespace(croix_on=False, croix_bits=lambda: 0); self.appui = None; self.molette = EN.GesteMolette(); self.height = 720
        self.cam_sens = (0, False); self.cam_recentre = False; self.cam_deux = False; self.cam_demande = 0.0; self.cam_acc = 0.0
        self.touches = {}; self.reg = {'camera_inverser_gd': False, 'vitesse_camera': 1.0, 'vitesse_accel': 1.5}
        self._pret = True; self.fixe_test = True
        for k, v in kw.items(): setattr(self, k, v)
        for nom in ('_terrain_libre', '_camera_pilotable', 'recentrer_camera', '_molette_appui', '_molette_glisse', '_molette_relache', '_etat_axe', '_bits_camera', '_camera_apres_pas', '_camera_oublier', 'pad', 'on_mouse_scroll'):
            setattr(self, nom, types.MethodType(getattr(FE.Jeu, nom), self))
        self._tenue = lambda a: False

    def tenir(self, *actions): self._tenue = lambda a: a in actions

    def images(self, n):
        """n pas du moteur : les boutons de camera que la visionneuse envoie (`Jeu._entrees`, terrain), puis le suivi du pas (`Jeu.tick`)."""
        for _ in range(n):
            bits = self._bits_camera(); self.moteur.pas(bits); self._camera_apres_pas(self.moteur)
        return self.moteur.bits[-n:]

    def clic(self, x=500, y=300):
        self._molette_appui(x, y); self._molette_relache()


BOTH = lambda: FE.MO.CAM_G | FE.MO.CAM_D


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class MoletteDansLeJeu(unittest.TestCase):
    def recentre(self, j): return j.cam_recentre

    def test_clic_en_ville_demande_le_retour_au_nord(self):
        j = Faux(); j.clic()
        self.assertTrue(self.recentre(j)); self.assertEqual(j.images(3), [BOTH(), 0, 0])        # les deux boutons de camera ensemble, une seule fois : le jeu anime le retour au nord (et tient le joueur)

    def glisse(self, gd, ndy=-40):
        j = Faux(); j.reg['camera_inverser_gd'] = gd
        j._molette_appui(500, 300); j._molette_glisse(520, 300); j._molette_glisse(620, 300 + ndy)          # 100 px vers la droite, ndy vers le haut (y pyglet vers le haut)
        return j

    def test_inversion_du_glissement_dans_le_jeu(self):
        self.assertGreater(self.glisse(False).cam_demande, 0.0)                            # sans inversion : droite = a droite, comme la fleche droite
        for dy in (-40, 0, 40):
            self.assertAlmostEqual(self.glisse(True, dy).cam_demande, -self.glisse(False, dy).cam_demande)
        self.assertAlmostEqual(self.glisse(False, 40).cam_demande, self.glisse(False, -40).cam_demande)      # le deplacement vertical ne change rien

    def test_inversion_ne_touche_pas_les_fleches_du_clavier(self):
        """Fleches gauche / droite tenues 30 pas : memes boutons de camera et meme nombre de crans quel que soit le reglage d'inversion."""
        MO = FE.MO
        for tenue, bit, signe in (('cam_droite', MO.CAM_D, 1), ('cam_gauche', MO.CAM_G, -1)):
            res = []
            for gd in (False, True):
                j = Faux(); j.reg['camera_inverser_gd'] = gd; j.tenir(tenue); b = j.images(30); res.append((set(b), j.moteur.crans))
            self.assertEqual(res[0], res[1], tenue); self.assertEqual(res[0][0], {bit}); self.assertEqual(res[0][1], 29 * signe)      # (le dernier cran est consomme au pas d'apres)

    def test_inversion_sans_effet_sur_le_retour_au_nord(self):
        for gd in (False, True):
            j = Faux(); j.reg['camera_inverser_gd'] = gd; j.clic(); self.assertEqual(j.images(1), [BOTH()])

    def test_clic_suivi_d_un_deplacement_n_est_pas_un_clic(self):
        j = Faux(); j._molette_appui(500, 300); j._molette_glisse(530, 300); j._molette_glisse(500, 300); j._molette_relache()      # revenu au point de depart : toujours un glissement
        self.assertFalse(self.recentre(j))
        j = Faux(); j._molette_appui(500, 300); j._molette_glisse(502, 301); j._molette_relache()                                    # un simple tremblement reste un clic
        self.assertTrue(self.recentre(j))

    def test_glisser_demande_une_rotation_comme_les_fleches(self):
        MO = FE.MO
        j = Faux(); j._molette_appui(500, 300); j._molette_glisse(520, 300); j._molette_glisse(620, 360)
        self.assertGreater(j.cam_demande, 0.0); demande = j.cam_demande
        j._molette_relache(); self.assertFalse(self.recentre(j))                           # le relachement d'un glissement ne demande aucun retour au nord
        b = j.images(1); self.assertEqual(b, [MO.CAM_D])                                   # la camera tourne a droite, par le bouton de camera du jeu
        j = Faux(); j._molette_appui(500, 300); j._molette_glisse(500, 340); j._molette_glisse(500, 480); self.assertEqual(j.cam_demande, 0.0); self.assertEqual(j.images(3), [0, 0, 0])      # purement vertical : rien ne tourne
        j = Faux(); j.reg['camera_inverser_gd'] = True; j._molette_appui(500, 300); j._molette_glisse(520, 300); j._molette_glisse(620, 300); self.assertEqual(j.images(1), [MO.CAM_G])

    def test_le_glissement_suit_le_pointeur_par_crans(self):
        """La rotation demandee est faite par des crans du jeu (MO.CAM_PAS chacun, au plus CAM_GLISSE_PAS par pas), puis s'arrete : le reste de moins d'un demi-cran n'est pas tourne, il s'ajoute au glissement suivant."""
        MO = FE.MO
        j = Faux(); j.cam_demande = 40.0; j.images(60)
        self.assertAlmostEqual(j.moteur.crans * MO.CAM_PAS, 40.0, delta=MO.CAM_PAS / 2 + 1e-9); self.assertLess(abs(j.cam_demande), MO.CAM_PAS / 2 + 1e-9)
        self.assertLessEqual(max(f for _, f in j.moteur.appels), FE.CAM_GLISSE_PAS)
        j = Faux(); j.cam_demande = 40.0; j.images(1); self.assertEqual(j.moteur.appels, [(MO.ROT_CAM_DROITE, FE.CAM_GLISSE_PAS)])         # un grand glissement : plusieurs crans dans le meme pas
        j = Faux(); j.cam_demande = -1.0; self.assertEqual(j.images(3), [0, 0, 0])                                                   # moins d'un demi-cran : rien
        j = Faux(); j.cam_demande = -MO.CAM_PAS; j.images(3); self.assertEqual(j.moteur.crans, -1)

    def test_les_fleches_l_emportent_sur_le_glissement(self):
        j = Faux(); j.cam_demande = -40.0; j.tenir('cam_droite'); self.assertEqual(j.images(2), [FE.MO.CAM_D] * 2)

    def test_le_jeu_refuse_la_rotation(self):
        """Verrou du joueur, scene, lieu qui interdit de tourner, limite atteinte : le jeu ne prend pas le bouton (rien en attente). La visionneuse n'ajoute aucun verrou a elle (elle envoie le bouton, le jeu decide) mais abandonne la rotation demandee a la souris."""
        j = Faux(); j.moteur.accepte = False; j.cam_demande = 40.0; j.images(3)
        self.assertEqual(j.cam_demande, 0.0); self.assertEqual(j.moteur.crans, 0); self.assertEqual(j.moteur.appels, [])
        j = Faux(); j.moteur.accepte = False; j.tenir('cam_droite'); self.assertEqual(j.images(3), [FE.MO.CAM_D] * 3); self.assertEqual(j.moteur.crans, 0)          # (les fleches ne sont pas abandonnees : le jeu peut la reprendre la fin de la scene)
        j = Faux(); j.moteur.accepte = False; j.clic(); self.assertEqual(j.images(2), [BOTH(), 0])

    def test_le_terrain_change_entre_l_appui_et_le_relachement(self):
        """Un message qui s'ouvre pendant que le bouton du milieu est enfonce : le relachement ne demande rien, et le glissement ne tourne rien."""
        j = Faux(); j._molette_appui(500, 300); j.moteur.msg_visible = True
        j._molette_glisse(520, 300); j._molette_glisse(560, 300); self.assertEqual(j.cam_demande, 0.0)
        j._molette_relache(); self.assertFalse(self.recentre(j))
        j = Faux(); j._molette_appui(500, 300); j.moteur.msg_visible = True; j._molette_relache(); self.assertFalse(self.recentre(j))                  # un clic simple, mais le terrain n'est plus libre

    def test_une_demande_en_attente_ne_part_pas_apres_un_menu(self):
        """Rotation demandee ou retour au nord demande, puis un message s'ouvre avant le pas : ils sont oublies (`Jeu._entrees` : hors terrain), ils ne partent pas a la fermeture du message."""
        j = Faux(); j.cam_demande = 40.0; j.recentrer_camera(); j.moteur.msg_visible = True; j._camera_oublier(); j.moteur.msg_visible = False
        self.assertEqual(j.images(3), [0, 0, 0])

    def test_le_retour_au_nord_efface_la_rotation_demandee_a_la_souris(self):
        """Clic molette (retour au nord) alors qu'une rotation de la souris restait a faire : le jeu ramene la camera au nord, la rotation restante n'est pas faite apres coup."""
        j = Faux(); j.cam_demande = 40.0; j.recentrer_camera()
        self.assertEqual(j.images(4), [BOTH(), 0, 0, 0]); self.assertEqual(j.cam_demande, 0.0); self.assertEqual(j.moteur.appels, [])

    def test_un_glissement_annule_le_retour_au_nord_pas_encore_envoye(self):
        j = Faux(); j.recentrer_camera(); j._molette_appui(500, 300); j._molette_glisse(520, 300); j._molette_glisse(620, 300)
        self.assertFalse(self.recentre(j)); self.assertEqual(j.images(1), [FE.MO.CAM_D])

    def test_appui_en_menu_puis_terrain_libre_au_relachement(self):
        """Le bouton du milieu enfonce pendant un message, le message se ferme, puis il est relache : ce n'est pas un clic sur le terrain (le geste n'a jamais commence)."""
        j = Faux(); j.moteur.msg_visible = True; j._molette_appui(500, 300); j.moteur.msg_visible = False
        j._molette_relache(); self.assertFalse(self.recentre(j))
        j._molette_glisse(560, 300); self.assertEqual(j.cam_demande, 0.0)

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
            j = faux(nom); j.clic(); j._molette_appui(0, 0); j._molette_glisse(50, 50); j._molette_glisse(120, 90); j._molette_relache()
            self.assertEqual(j.cam_demande, 0.0, nom); self.assertFalse(self.recentre(j), nom)
            if nom in ('croix', 'bouton'): continue                                                           # (la croix et les boutons de l'ecran sont tenus a la souris : ils ne bloquent que le clic molette, pas les fleches du clavier)
            j = faux(nom); j.tenir('cam_droite', 'cam_gauche'); self.assertEqual(j.images(30), [0] * 30, nom); self.assertFalse(self.recentre(j), nom)
            j = faux(nom); j.tenir('cam_droite'); self.assertEqual(j.images(5), [0] * 5, nom)

    def test_carte_du_monde_pas_de_rotation(self):
        j = Faux(partie=FE.MO.PARTIE_CHAMP); j.clic(); self.assertFalse(self.recentre(j))          # pas de rotation sur la carte du monde (comme les fleches)
        j.tenir('cam_droite'); self.assertEqual(j.images(30), [0] * 30)

    def test_la_molette_ne_fait_plus_rien_sur_le_terrain(self):
        for partie in (None, FE.MO.PARTIE_CHAMP):
            j = Faux(partie=partie); j.tenir('modif'); j.on_mouse_scroll(0, 0, 0, 1); j.on_mouse_scroll(0, 0, 0, -3)
            self.assertEqual(j.cam_demande, 0.0); self.assertFalse(self.recentre(j)); self.assertEqual(j.images(2), [0, 0])
            self.assertFalse(hasattr(j, 'zoom'))


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class FlechesDansLeJeu(unittest.TestCase):
    def test_fleches_tournent_la_camera_du_jeu(self):
        MO = FE.MO
        j = Faux(); j.tenir('cam_droite'); self.assertEqual(j.images(30), [MO.CAM_D] * 30); self.assertEqual(j.moteur.crans, 29); self.assertEqual(j.moteur.appels, [])          # un cran par pas, par le jeu : 84,4 degres par seconde
        j = Faux(); j.tenir('cam_gauche'); self.assertEqual(j.images(30), [MO.CAM_G] * 30); self.assertEqual(j.moteur.crans, -29)

    def test_les_boutons_de_camera_sont_les_bits_4_et_5_des_touches_tenues(self):
        """Sur le terrain d'une ville, (Global + 0xe0) >> 4 & 3 : 1 = gauche, 2 = droite, 3 = retour au nord (NormalControl::checkCamera). Ce sont les valeurs de A et B des menus : la visionneuse retire A et B du terrain (le moteur y veut BTN_PAROLE)."""
        MO = FE.MO
        self.assertEqual((MO.CAM_G, MO.CAM_D), (0x10, 0x20)); self.assertEqual((MO.CAM_G, MO.CAM_D), (MO.A, MO.B))
        self.assertAlmostEqual(MO.CAM_PAS, 2.8125)

    def test_vitesse_de_camera(self):
        """x2 = deux crans par pas, x4 = quatre ; le premier cran est celui du bouton (pas d'appel), les autres sont ajoutes tout de suite."""
        MO = FE.MO
        for v in (1.0, 2.0, 3.0, 4.0):
            j = Faux(); j.reg['vitesse_camera'] = v; j.tenir('cam_droite'); j.images(10); self.assertEqual(j.moteur.crans, 10 * int(v) if v > 1 else 9, v)
            if v > 1: self.assertEqual(set(j.moteur.appels), {(MO.ROT_CAM_DROITE, int(v))})
            else: self.assertEqual(j.moteur.appels, [])

    def test_vitesse_de_camera_a_gauche(self):
        MO = FE.MO
        j = Faux(); j.reg['vitesse_camera'] = 3.0; j.tenir('cam_gauche'); j.images(10)
        self.assertEqual(j.moteur.crans, -30); self.assertEqual(set(j.moteur.appels), {(MO.ROT_CAM_GAUCHE, 3)})

    def test_aucun_cran_de_plus_pendant_le_retour_au_nord(self):
        """Le jeu tient la camera (retour au nord en cours : le type en attente est celui du nord, pas celui du bouton envoye) : la visionneuse n'y ajoute aucun cran, ni pour les fleches ni pour le glissement."""
        MO = FE.MO
        j = Faux(); j.reg['vitesse_camera'] = 4.0; j.cam_sens = (-1, False); j.moteur.attente = MO.ROT_CAM_NORD
        j._camera_apres_pas(j.moteur); self.assertEqual(j.moteur.appels, [])
        j.cam_demande = -40.0; j.cam_sens = (-1, True); j._camera_apres_pas(j.moteur); self.assertEqual(j.moteur.appels, []); self.assertEqual(j.cam_demande, 0.0)

    def test_pas_de_glissement_tant_qu_une_fleche_est_tenue(self):
        j = Faux(); j.tenir('cam_gauche', 'cam_droite'); self.assertEqual(j.images(1), [BOTH()])
        j.cam_demande = 40.0; self.assertEqual(j.images(3), [0, 0, 0])
        j.tenir('cam_droite'); self.assertEqual(j.images(2), [0, 0])                  # (la fleche restante apres la pression double)
        j.tenir(); self.assertEqual(j.images(1), [FE.MO.CAM_D])                       # tout relache : la rotation demandee a la souris repart

    def test_vitesse_non_entiere_repartie_d_un_pas_a_l_autre(self):
        j = Faux(); j.reg['vitesse_camera'] = 1.5; j.tenir('cam_droite'); j.images(40); self.assertAlmostEqual(j.moteur.crans, 60, delta=2)

    def test_l_accelerateur_n_accelere_pas_la_camera(self):
        j = Faux(); j.tenir('cam_droite'); j.images(30); ref = j.moteur.crans
        j = Faux(); j.tenir('cam_droite', 'accel'); j.images(30); self.assertEqual(j.moteur.crans, ref)
        j = Faux(); j.reg['vitesse_accel'] = 2.0; j.tenir('cam_gauche', 'accel'); j.images(30); self.assertEqual(j.moteur.crans, -ref)

    def test_haut_bas_ne_font_rien_sur_le_terrain(self):
        j = Faux(); j.tenir('cam_haut', 'cam_bas'); self.assertEqual(j.images(30), [0] * 30); self.assertEqual(j.pad(), 0)          # (ils ne servent que dans les menus : plus d'inclinaison)

    def test_les_deux_fleches_ramenent_la_camera_au_nord_une_fois(self):
        MO = FE.MO
        j = Faux(); j.tenir('cam_gauche', 'cam_droite'); self.assertEqual(j.images(10), [BOTH()] + [0] * 9)          # les deux boutons de camera du jeu au premier pas seulement : le jeu fait le reste (animation, joueur tenu)
        self.assertEqual(j.moteur.crans, 0)

    def test_une_fleche_restee_enfoncee_apres_la_pression_double_ne_fait_rien(self):
        MO = FE.MO
        j = Faux(); j.tenir('cam_gauche', 'cam_droite'); j.images(1); j.tenir('cam_droite'); self.assertEqual(j.images(10), [0] * 10)        # la fleche restante (relachement jamais simultane) ne tourne pas
        j.tenir('cam_gauche', 'cam_droite'); self.assertEqual(j.images(2), [0, 0])                                                         # (l'autre re-enfoncee alors que la premiere est restee tenue : pas de nouveau retour au nord)
        j.tenir(); j.images(1); j.tenir('cam_droite'); self.assertEqual(j.images(3), [MO.CAM_D] * 3)                                      # tout relache, puis une fleche seule : la camera tourne a nouveau
        j.tenir('cam_gauche', 'cam_droite'); self.assertEqual(j.images(2), [BOTH(), 0])                                                    # une fleche tenue, l'autre s'y ajoute : pression double, retour au nord

    def test_deux_fleches_deja_tenues_en_revenant_sur_le_terrain(self):
        """Les deux fleches tenues pendant un message, puis le message se ferme : pas de retour au nord (ce n'est pas une pression double sur le terrain)."""
        j = Faux(); j.moteur.msg_visible = True; j.tenir('cam_gauche', 'cam_droite'); j._camera_oublier(); j.moteur.msg_visible = False
        self.assertEqual(j.images(5), [0] * 5)

    def test_la_visionneuse_ne_tourne_plus_la_marche(self):
        """Les directions de marche sont celles de l'ecran, tournees par le jeu selon sa camera (comme sur mobile) : plus de rotation faite par la visionneuse."""
        MO = FE.MO
        for tenue, voulu in ((('haut',), MO.HAUT), (('bas',), MO.BAS), (('gauche',), MO.GAUCHE), (('droite',), MO.DROITE), (('haut', 'droite'), MO.HAUT | MO.DROITE)):
            j = Faux(); j.tenir(*tenue); self.assertEqual(j.pad(), voulu, tenue)
        j = Faux(); j.tenir('A'); self.assertEqual(j.pad(), MO.A)
        for nom in ('_lacet_eff', '_tourner_dir', '_maj_camera', '_camera_menee', '_coupure_camera'): self.assertFalse(hasattr(FE.Jeu, nom), nom)
        for nom in ('lacet', 'cam_w', 'cam_jeu', 'cam_bloquee', 'cam_limite', 'cam_saut', 'cam_axe'): self.assertFalse(hasattr(Faux(), nom), nom)

    def test_dans_les_menus_les_fleches_sont_des_directions(self):
        MO = FE.MO
        j = Faux(); j.moteur.msg_visible = True
        for act, bit in (('cam_haut', MO.HAUT), ('cam_bas', MO.BAS), ('cam_gauche', MO.GAUCHE), ('cam_droite', MO.DROITE)):
            j.tenir(act); self.assertEqual(j.pad(), bit, act)

    def test_entrees_envoie_les_boutons_de_camera_sur_le_terrain_seulement(self):
        """Branchement (le code est relu, la fenetre n'est pas ouverte) : `_entrees` ajoute les boutons de camera apres avoir retire A et B, dans la branche du terrain ; ailleurs elle oublie les demandes ; `tick` suit le pas avec _camera_apres_pas."""
        import inspect
        src = inspect.getsource(FE.Jeu._entrees)
        self.assertIn('p &= ~(MO.A | MO.B)\n            terrain = True; p |= self._bits_camera()', src)
        self.assertIn('if not terrain: self._camera_oublier()', src)
        tick = inspect.getsource(FE.Jeu.tick)
        self.assertLess(tick.index('mo.step(p, decl)'), tick.index('self._camera_apres_pas(mo)'))


if __name__ == '__main__':
    unittest.main(verbosity=1)
