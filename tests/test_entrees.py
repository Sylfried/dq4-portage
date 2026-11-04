"""Test des entrees souris / clavier : logique pure (entrees.py) et branchement dans la fenetre (fenetre.Jeu), sans ouvrir de fenetre.

    python3 tests/test_entrees.py

1. La souris apres le clavier (« passer du clavier a la souris rend la souris inutilisable pendant 1 s ») : le survol reprend la main au premier vrai mouvement (ecart CUMULE depuis la derniere touche, petite
   tolerance de bruit), un clic agit toujours, aussitot. L'ancien test (ecart d'un evenement au suivant) est rejoue pour montrer qu'une souris qui envoie des mouvements de 1 a 2 pixels ne reprenait jamais la main.
2. Le bloc d'infos de F1 : en haut a droite par defaut.
Les gestes du clic molette (rotation de la camera, zoom a la molette, remises a zero) et leurs reglages ont ete retires en #264 : le bouton du milieu et la molette sur le terrain ne font plus rien.
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


if __name__ == '__main__':
    unittest.main(verbosity=1)
