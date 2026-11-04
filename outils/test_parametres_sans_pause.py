"""Test (sans moteur ni affichage) de l'ecran « Paramètres » (#136) : l'ecran qui s'appelait « Pause » (menu Echap) s'appelle « Paramètres » et ne met plus le jeu en pause : le jeu tourne derriere lui
(sans touche ni clic : les touches du menu ne font pas marcher le heros), seules les pages « Historique » et « Quitter » l'arretent.

    python3 outils/test_parametres_sans_pause.py

  1. le titre de la racine est « Paramètres » (plus « Pause ») ;
  2. Pause.fige_le_jeu : faux menu ferme, faux sur la racine et les pages de reglages, vrai sur l'historique et la question de sortie ;
  3. Jeu._synchroniser_gel : le son et l'horloge ne s'arretent qu'en entrant sur une page figee, et repartent en la quittant (sans rattrapage du temps passe) ; Jeu.pause_jeu : ouvrir ne coupe rien, fermer rend le son s'il etait arrete ;
  4. Jeu.tick : aucune entree n'est envoyee au moteur menu ouvert ; Jeu._facteur_vitesse : pas de marche acceleree menu ouvert (aucune direction n'est envoyee au jeu) ;
  5. Jeu._boucle : le moteur tourne menu ouvert (sauf page figee).
"""
import inspect, os, sys, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False
import fenetre as F
import pause as PA
import moteur as MO


def menu(ecran, ouvert=True):
    p = PA.Pause.__new__(PA.Pause); p.ouvert = ouvert; p.pile = ['racine'] + ([ecran] if ecran != 'racine' else []); return p


class TestTitre(unittest.TestCase):
    def test_racine_s_appelle_parametres(self):
        src = inspect.getsource(PA.Pause.dessiner)
        self.assertIn("'racine': 'Paramètres'", src); self.assertNotIn("'racine': 'Pause'", src)


class TestPagesFigees(unittest.TestCase):
    def test_pages_de_reglages_laissent_tourner_le_jeu(self):
        for page in ('racine', 'affichage', 'son', 'commandes', 'interface', 'etats', 'modifications'):
            self.assertFalse(menu(page).fige_le_jeu(), page)

    def test_historique_et_quitter_arretent_le_jeu(self):
        for page in ('historique', 'quitter'): self.assertTrue(menu(page).fige_le_jeu(), page)

    def test_menu_ferme(self):
        self.assertFalse(menu('historique', ouvert=False).fige_le_jeu())

    def test_le_retour_de_l_historique_relance_le_jeu(self):
        p = menu('historique'); self.assertTrue(p.fige_le_jeu()); p.pile.pop(); self.assertFalse(p.fige_le_jeu())


class Faux:
    """Ce que la boucle de la fenetre demande au menu, au son et au reste (champs de Jeu utilises par les methodes essayees)."""
    def __init__(self, ecran='racine'):
        self.pile_p = menu(ecran); self.pause = self.pile_p; self.appels = []; self._jeu_fige = False; self.acc = 5.0; self.t_boucle = 1.0
        self.son = types.SimpleNamespace(mettre_en_pause=lambda oui: self.appels.append(('son', oui)))
        self.pad_prec = None; self.act_prec = None; self.rep = {}; self.survol = self.appui = self.survol_nd = None
        self.pad = lambda: 0; self._tenue = lambda a: False; self.garde_souris = types.SimpleNamespace(clavier=lambda s: None); self.souris = None


class TestArret(unittest.TestCase):
    def test_entrer_sur_une_page_figee_coupe_le_son_et_l_horloge(self):
        J = Faux('racine'); F.Jeu._synchroniser_gel(J); self.assertEqual(J.appels, []); self.assertFalse(J._jeu_fige)       # racine : rien ne s'arrete
        J.pause.pile.append('historique'); J.acc = 7.0; F.Jeu._synchroniser_gel(J)
        self.assertEqual(J.appels, [('son', True)]); self.assertTrue(J._jeu_fige); self.assertEqual((J.acc, J.t_boucle), (0.0, None))
        F.Jeu._synchroniser_gel(J); self.assertEqual(J.appels, [('son', True)], 'pas de repetition')

    def test_quitter_la_page_figee_relance(self):
        J = Faux('historique'); F.Jeu._synchroniser_gel(J); J.pause.pile.pop(); J.acc = 3.0; J.t_boucle = 2.0
        F.Jeu._synchroniser_gel(J)
        self.assertEqual(J.appels, [('son', True), ('son', False)]); self.assertFalse(J._jeu_fige); self.assertEqual((J.acc, J.t_boucle), (0.0, None), 'pas de rattrapage du temps passe')

    def test_ouvrir_la_racine_ne_coupe_rien(self):
        J = Faux('racine'); F.Jeu.pause_jeu(J, True); self.assertEqual(J.appels, []); self.assertFalse(J._jeu_fige)

    def test_fermer_depuis_une_page_figee_rend_le_son(self):
        J = Faux('historique'); F.Jeu._synchroniser_gel(J); J.pause.ouvert = False; F.Jeu.pause_jeu(J, False)
        self.assertEqual(J.appels, [('son', True), ('son', False)]); self.assertFalse(J._jeu_fige)

    def test_fermer_la_racine_ne_touche_pas_au_son(self):
        J = Faux('racine'); F.Jeu.pause_jeu(J, True); J.pause.ouvert = False; F.Jeu.pause_jeu(J, False); self.assertEqual(J.appels, [])


class TestEntrees(unittest.TestCase):
    def test_tick_n_envoie_aucune_entree_menu_ouvert(self):
        src = inspect.getsource(F.Jeu.tick)
        self.assertIn('(muet or self.pause.ouvert)', src)                                               # (0, 0) : ni touche ni clic ni direction pour le jeu

    def faux_facteur(self, ouvert, dirs):
        mo = types.SimpleNamespace(etat=types.SimpleNamespace(effet=None, garde_trans=0, partie=MO.PARTIE_CHAMP, attente_charge=None), msg_visible=False, menu_actif=lambda: None, drapeaux=lambda: 0)
        J = types.SimpleNamespace(reg={'vitesse_marche': 3.0, 'vitesse_accel': 2.0, 'vitesse_combat': 0}, moteur=mo, pause=types.SimpleNamespace(ouvert=ouvert),
                                  pad=lambda: dirs, _tenue=lambda a: False, hud=types.SimpleNamespace(croix_course=lambda: False))
        J._horloge_combat = lambda: F.Jeu._horloge_combat(J)
        return F.Jeu._facteur_vitesse(J)

    def test_pas_de_marche_acceleree_menu_ouvert(self):
        self.assertEqual(self.faux_facteur(False, MO.GAUCHE), 3.0, 'terrain : la marche acceleree s\'applique')
        self.assertEqual(self.faux_facteur(True, MO.GAUCHE), 1.0, 'menu ouvert : une direction du menu ne fait pas courir le jeu')


class TestBoucle(unittest.TestCase):
    def test_le_moteur_tourne_menu_ouvert_sauf_page_figee(self):
        src = inspect.getsource(F.Jeu._boucle)
        self.assertIn('if self.pause.fige_le_jeu():', src)                                           # seul le retour anticipe d'une page figee arrete le moteur
        self.assertNotIn('if self.pause.ouvert: self.pause.maj(); self.acc = 0.0', src)                 # l'ancien arret general a disparu
        self.assertIn('self._synchroniser_gel()', src)


if __name__ == '__main__':
    unittest.main(verbosity=1)
