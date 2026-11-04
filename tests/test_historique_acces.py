"""Test (sans moteur ni affichage) de l'acces a l'historique (#187 : « l'historique doit pouvoir etre accessible uniquement quand j'ai le controle de mon perso, donc pas pendant un combat ni pendant un moment ou le jeu
prend le controle ») : `Jeu.controle_joueur`, `Jeu.historique_possible`, `Jeu._touche_historique`, la ligne « Historique » du menu Paramètres et la fermeture de la page quand le jeu reprend la main.

    python3 outils/test_historique_acces.py

  1. controle_joueur : vrai seulement sur le terrain (ville, carte du monde) sans verrou du joueur (Global.Flag 4), message, menu du jeu, effet d'ecran, chargement ni combat ; un fondu seul (flag 1) n'y change rien ;
  2. historique_possible : en plus, jamais a l'ecran titre ;
  3. touche H : ouvre la page quand c'est possible, sinon un message bref et aucune page ; la touche est branchee sur `_touche_historique` dans on_key_press (et plus sur l'ouverture directe) ;
  4. menu Paramètres : la ligne « Historique » est active / inactive (grisee, infobulle) selon `historique_possible` ; sans cette methode (faux jeu minimal) elle reste active ;
  5. Pause.maj : page historique ouverte puis le jeu reprend la main (combat, dialogue, scene) : la page se ferme (retour a la racine, ou menu ferme si elle avait ete ouverte par la touche) avec un message ; tant que le joueur a la main, la liste suit le jeu (#178).
"""
import inspect, os, sys, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..'))
import pyglet
pyglet.options['shadow_window'] = False
from dq4_pc.fenetre import jeu as F
from dq4_pc.menus import pause as PA
from dq4_pc.noyau import moteur as MO


def faux_jeu(partie=MO.PARTIE_VILLE, flag=0, msg=False, menu=None, effet=None, attente=None, garde=0, titre=None):
    """Ce que `controle_joueur` lit du moteur et de la fenetre."""
    e = types.SimpleNamespace(partie=partie, effet=effet, attente_charge=attente, garde_trans=garde)
    mo = types.SimpleNamespace(etat=e, msg_visible=msg, menu_actif=lambda: menu, drapeaux=lambda: flag)
    j = types.SimpleNamespace(moteur=mo, titre=titre, toasts=[], appels=[])
    j._horloge_combat = lambda: F.Jeu._horloge_combat(j)
    j.controle_joueur = lambda: F.Jeu.controle_joueur(j)
    j.historique_possible = lambda: F.Jeu.historique_possible(j)
    j.toast = lambda t, duree=1.8: j.toasts.append(t)
    j.pause = types.SimpleNamespace(ouvrir=lambda page=None: j.appels.append(page))
    return j


class TestControleJoueur(unittest.TestCase):
    def test_joueur_libre_sur_le_terrain(self):
        for partie in (MO.PARTIE_VILLE, MO.PARTIE_CHAMP): self.assertTrue(F.Jeu.controle_joueur(faux_jeu(partie=partie)), partie)

    def test_pas_en_combat(self):
        self.assertFalse(F.Jeu.controle_joueur(faux_jeu(partie=MO.PARTIE_COMBAT)))
        self.assertFalse(F.Jeu.controle_joueur(faux_jeu(effet={'n': 3, 'duree': 57})), 'cascade d\'entree en combat')
        self.assertFalse(F.Jeu.controle_joueur(faux_jeu(attente=object())), 'ecran noir qui attend la scene du combat')
        self.assertFalse(F.Jeu.controle_joueur(faux_jeu(garde=2)), 'entre deux fondus d\'un combat')

    def test_pas_quand_le_jeu_prend_la_main(self):
        self.assertFalse(F.Jeu.controle_joueur(faux_jeu(flag=MO.DRAPEAU_JOUEUR_VERROUILLE)), 'evenement, scene, dialogue, fondu de sortie : joueur verrouille')
        self.assertFalse(F.Jeu.controle_joueur(faux_jeu(flag=MO.DRAPEAU_JOUEUR_VERROUILLE | MO.DRAPEAU_FONDU)))
        self.assertFalse(F.Jeu.controle_joueur(faux_jeu(msg=True)), 'message visible')
        self.assertFalse(F.Jeu.controle_joueur(faux_jeu(menu=3)), 'menu du jeu (commandes, boutique, Divers...)')

    def test_un_fondu_seul_ne_compte_pas(self):
        self.assertTrue(F.Jeu.controle_joueur(faux_jeu(flag=MO.DRAPEAU_FONDU)), 'fondu d\'arrivee ou de retour de combat, joueur libre (#107, #127)')
        self.assertTrue(F.Jeu.controle_joueur(faux_jeu(flag=0x8 | 0x20)), 'autres bits de Global.Flag (manette, carte autorisee)')

    def test_autres_parties(self):
        autres = [p for p in (getattr(MO, n) for n in dir(MO) if n.startswith('PARTIE_')) if p not in (MO.PARTIE_VILLE, MO.PARTIE_CHAMP)]
        self.assertTrue(autres)
        for p in autres: self.assertFalse(F.Jeu.controle_joueur(faux_jeu(partie=p)), 'partie %r : ni ville ni carte du monde' % (p,))


class TestHistoriquePossible(unittest.TestCase):
    def test_possible_quand_libre(self): self.assertTrue(F.Jeu.historique_possible(faux_jeu()))
    def test_pas_a_l_ecran_titre(self): self.assertFalse(F.Jeu.historique_possible(faux_jeu(titre=object())))
    def test_pas_en_combat_ni_en_dialogue(self):
        for kw in (dict(partie=MO.PARTIE_COMBAT), dict(msg=True), dict(flag=MO.DRAPEAU_JOUEUR_VERROUILLE), dict(menu=1)): self.assertFalse(F.Jeu.historique_possible(faux_jeu(**kw)), kw)


class TestTouche(unittest.TestCase):
    def test_ouvre_quand_le_joueur_a_la_main(self):
        j = faux_jeu(); F.Jeu._touche_historique(j); self.assertEqual(j.appels, ['historique']); self.assertEqual(j.toasts, [])

    def test_ne_fait_rien_sans_message_sinon(self):          # #194 : le joueur n'a pas a etre informe
        for kw in (dict(partie=MO.PARTIE_COMBAT), dict(msg=True), dict(flag=MO.DRAPEAU_JOUEUR_VERROUILLE)):
            j = faux_jeu(**kw); F.Jeu._touche_historique(j); self.assertEqual(j.appels, [], kw); self.assertEqual(j.toasts, [], kw)

    def test_on_key_press_passe_par_la_regle(self):
        src = inspect.getsource(F.Jeu.on_key_press)
        i = src.index("action_de(symbol) == 'historique'"); ligne = src[i:src.index('\n', i)]
        self.assertIn('self._touche_historique()', ligne); self.assertNotIn("self.pause.ouvrir('historique')", ligne)


def menu(j, pile=None):
    p = PA.Pause.__new__(PA.Pause); p.J = j; p.ouvert = True; p.pile = pile or ['racine']; p.sel = {}; return p


def ligne_historique(p):
    return next(en for en in p._e_racine() if en.get('l') == 'Historique')


class TestMenu(unittest.TestCase):
    def test_ligne_active_quand_le_joueur_a_la_main(self):
        p = menu(faux_jeu()); en = ligne_historique(p); self.assertFalse(PA.Pause._inactif(en)); self.assertTrue(p._actif(en))

    def test_ligne_grisee_sinon_avec_infobulle(self):
        for kw in (dict(partie=MO.PARTIE_COMBAT), dict(msg=True), dict(flag=MO.DRAPEAU_JOUEUR_VERROUILLE), dict(menu=2)):
            p = menu(faux_jeu(**kw)); en = ligne_historique(p); self.assertTrue(PA.Pause._inactif(en), kw); self.assertFalse(p._actif(en), kw)
            self.assertIn('main sur votre personnage', en.get('aide', ''))

    def test_la_ligne_suit_l_etat_du_jeu_a_chaque_image(self):
        j = faux_jeu(); p = menu(j); self.assertFalse(PA.Pause._inactif(ligne_historique(p)))
        j.moteur.msg_visible = True; self.assertTrue(PA.Pause._inactif(ligne_historique(p)))
        j.moteur.msg_visible = False; self.assertFalse(PA.Pause._inactif(ligne_historique(p)))

    def test_faux_jeu_minimal_garde_la_ligne_active(self):
        p = menu(types.SimpleNamespace()); self.assertFalse(PA.Pause._inactif(ligne_historique(p)))


class TestFermeture(unittest.TestCase):
    """Pause.maj sur la page « historique » (les autres pages et `fermer` sont remplaces par des espions)."""
    def pause(self, j, pile):
        p = menu(j, pile); p.appels = []; p.hist = types.SimpleNamespace(suivre_le_jeu=lambda: p.appels.append('suit'))
        p.J.son = types.SimpleNamespace(ecoute=False, ecouter=lambda e: None, tick=lambda: None)
        p.pan_plier_a = None; p.pan_appui = None; p.rep = None
        p.fermer = lambda: p.appels.append('ferme'); return p

    def test_suit_le_jeu_tant_que_le_joueur_a_la_main(self):
        j = faux_jeu(); p = self.pause(j, ['racine', 'historique']); p.maj(); self.assertEqual(p.appels, ['suit']); self.assertEqual(p.pile, ['racine', 'historique']); self.assertEqual(j.toasts, [])

    def test_le_jeu_reprend_la_main_retour_a_la_racine(self):          # sans message (#194)
        for kw in (dict(partie=MO.PARTIE_COMBAT), dict(msg=True), dict(flag=MO.DRAPEAU_JOUEUR_VERROUILLE)):
            j = faux_jeu(); p = self.pause(j, ['racine', 'historique']); p.maj(); self.assertEqual(p.pile, ['racine', 'historique'])
            for k, v in kw.items():
                if k == 'partie': j.moteur.etat.partie = v
                elif k == 'msg': j.moteur.msg_visible = v
                elif k == 'flag': j.moteur.drapeaux = lambda v=v: v
            p.maj(); self.assertEqual(p.pile, ['racine'], kw); self.assertNotIn('ferme', p.appels); self.assertEqual(j.toasts, [], kw)

    def test_ouverte_par_la_touche_le_menu_se_ferme(self):
        j = faux_jeu(msg=True); p = self.pause(j, ['historique']); p.maj(); self.assertEqual(p.appels, ['ferme']); self.assertEqual(j.toasts, [])

    def test_les_autres_pages_ne_sont_pas_touchees(self):
        for page in ('racine', 'affichage', 'son', 'commandes'):
            j = faux_jeu(partie=MO.PARTIE_COMBAT, msg=True); p = self.pause(j, ['racine'] + ([page] if page != 'racine' else [])); pile = list(p.pile); p.maj()
            self.assertEqual(p.pile, pile, page); self.assertEqual(j.toasts, [], page)


if __name__ == '__main__':
    unittest.main(verbosity=2)
