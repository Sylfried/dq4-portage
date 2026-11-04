"""Test du casino et du bestiaire (parties 0xf et 0x10 du moteur), sans fenetre ni moteur (faux objets) :

  1. constantes du moteur : PARTIE_CASINO, PARTIE_BESTIAIRE, PARTIES_MINIJEU ;
  2. camera libre du casino (`camera_libre`) : position + rotation du paquet 10, sans paquet 11 ; pas ailleurs ;
  3. vitesse de marche : jamais acceleree dans le casino et le bestiaire (les fleches tenues y servent aux menus) ;
  4. Echap : bouton retour de la fenetre ouverte (manette 0x20) dans le casino et le bestiaire, sinon menu Echap ;
  5. menus de saisie numerique au clavier (mise de la machine a sous, du poker, jetons, arene) : colonnes, ▲ / ▼, validation, retour ;
  6. code de fenetre a masque de bits (poker : zones tactiles des cartes et « Donner », valeur 63 hors du tableau exporte) ;
  7. combat de l'arene : fenetre « Quitter » sans validation, A tourne la page du message.

    python3 outils/test_casino_bestiaire.py        (Linux sans ecran : pyglet en mode « headless »)
"""
import functools, os, sys, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import moteur as MO
import fenetre as F
import ui_menu as UI


class Constantes(unittest.TestCase):
    def test_parties(self):
        self.assertEqual((MO.PARTIE_CASINO, MO.PARTIE_BESTIAIRE), (0xf, 0x10))
        self.assertEqual(set(MO.PARTIES_MINIJEU), {MO.PARTIE_CASINO, MO.PARTIE_BESTIAIRE})
        self.assertFalse({MO.PARTIE_DEPART, MO.PARTIE_VILLE, MO.PARTIE_COMBAT, MO.PARTIE_CHAMP} & set(MO.PARTIES_MINIJEU))


class CameraLibre(unittest.TestCase):
    def e(self, partie, libre=False, rot=None): return types.SimpleNamespace(partie=partie, cam_libre=libre, cam_rot=rot)

    def test_casino(self):
        self.assertTrue(F.camera_libre(self.e(MO.PARTIE_CASINO, rot=(10.0, 0.0, 0.0))), 'casino : position + rotation, sans paquet 11')
        self.assertFalse(F.camera_libre(self.e(MO.PARTIE_CASINO, rot=None)), 'pas de rotation : camera a cible')

    def test_autres_parties(self):
        self.assertTrue(F.camera_libre(self.e(MO.PARTIE_VILLE, libre=True, rot=(0.0, 0.0, 0.0))), 'scene (paquet 11, bit 7)')
        self.assertFalse(F.camera_libre(self.e(MO.PARTIE_VILLE, rot=(10.0, 0.0, 0.0))), 'ville : la rotation seule ne rend pas la camera libre')
        self.assertFalse(F.camera_libre(self.e(MO.PARTIE_BESTIAIRE, rot=(10.0, 0.0, 0.0))), 'bestiaire : camera de la ville gardee en memoire')

    def test_faux_etat_sans_partie(self):
        """Les tests de camera passent un faux etat sans `partie` : camera de ville, pas d'erreur."""
        self.assertFalse(F.camera_libre(types.SimpleNamespace(cam_libre=False, cam_rot=None)))


def faux_marche(partie, msg=False):
    mo = types.SimpleNamespace(etat=types.SimpleNamespace(partie=partie, effet=None, attente_charge=None, garde_trans=0, transition_combat=lambda: False), msg_visible=msg, menu_actif=lambda: None, drapeaux=lambda: 0x28)
    return types.SimpleNamespace(reg={'vitesse_marche': 2.0, 'vitesse_accel': 1.5}, moteur=mo, pad=lambda: MO.DROITE, _tenue=lambda a: a == 'accel', hud=types.SimpleNamespace(croix_course=lambda: False), _horloge_combat=lambda: False)


class VitesseDeMarche(unittest.TestCase):
    def test_terrain(self):
        self.assertEqual(F.Jeu._facteur_vitesse(faux_marche(MO.PARTIE_VILLE)), 3.0, 'ville : reglage x accelerateur')

    def test_casino_bestiaire(self):
        for partie in MO.PARTIES_MINIJEU: self.assertEqual(F.Jeu._facteur_vitesse(faux_marche(partie)), 1.0, hex(partie))


class FausseFenetre:
    """Fenetre de menu du jeu (ui_menu.Fenetre) reduite a ce que lisent les fonctions testees : typ, boutons() = (numero, manette, x0, z0, x1, z1, profondeur)."""
    def __init__(self, typ, boutons): self.typ = typ; self._b = boutons
    def boutons(self): return list(self._b)


def b(num, pad, x, z=0.0): return (num, pad, x - 10.0, z - 10.0, x + 10.0, z + 10.0, 0)


def faux_jeu_menu(boutons, typ=47, partie=MO.PARTIE_CASINO, port=12):
    envois = []
    fe = FausseFenetre(typ, boutons)
    mo = types.SimpleNamespace(etat=types.SimpleNamespace(partie=partie), msg_visible=False, menu_actif=lambda: port, envoyer_menu=lambda *a: envois.append(a), ui=types.SimpleNamespace(f={port: {'ordre': 1, 'grille': None, 'vis': True}}))
    j = types.SimpleNamespace(moteur=mo, ui_g=types.SimpleNamespace(f={port: fe}), cur_pas={}, survol_nd=1, menu_relacher=None, son=types.SimpleNamespace(jouer_se=lambda *a: None), envois=envois,
                              saisie_nom=types.SimpleNamespace(actif=False), licence=None)
    for nom in ('_pas_colonnes', '_pas_actif', '_saisie_pas', '_retour_possible', '_echap_retour'): setattr(j, nom, functools.partial(getattr(F.Jeu, nom), j))
    j._port_pour_manette = lambda p, pad: p
    return j, fe


# machine a sous (type 47) : une colonne ▲ (manette 0x2) / ▼ (0x1) de numero 1, « Lancer » (0x10) de numero 0 ; retour 0x20 de numero -1
SLOT = [b(1, 0x2, 100, -50), b(1, 0x1, 100, 50), b(0, 0x10, 0, 100), b(-1, 0x20, 200, 150)]
# jetons (type 44) : cinq colonnes (1, 10, 100, 1000, 10000) de gauche a droite : 10000, 1000, 100, 10, 1 (positions croissantes), validation numero 0, retour -1
JETONS = [b(n, 0x2, x, -50) for n, x in ((10000, -200), (1000, -100), (100, 0), (10, 100), (1, 200))] + [b(n, 0x1, x, 50) for n, x in ((10000, -200), (1000, -100), (100, 0), (10, 100), (1, 200))] + [b(0, 0x10, 0, 150), b(-1, 0x20, 250, 200)]


class SaisieNumerique(unittest.TestCase):
    def test_colonnes(self):
        j, fe = faux_jeu_menu(SLOT); self.assertEqual(j._pas_colonnes(fe), [1])
        j, fe = faux_jeu_menu(JETONS, 44); self.assertEqual(j._pas_colonnes(fe), [10000, 1000, 100, 10, 1], 'de gauche a droite')

    def test_fenetre_ordinaire(self):
        """Une liste (cadeaux, bestiaire) n'a pas de colonne ▲ / ▼ : curseur ordinaire. Les fleches de page (numero -1) ne comptent pas."""
        j, fe = faux_jeu_menu([b(0, 0x10, 0, 0), b(1, 0x10, 0, 50), b(-1, 0x2, 50, 0), b(-1, 0x1, 50, 100)], 45)
        self.assertEqual(j._pas_colonnes(fe), [])
        self.assertFalse(j._saisie_pas(12, j.moteur.ui.f[12], fe, {0: 1}, MO.HAUT))
        self.assertEqual(j.envois, [])

    def test_haut_bas(self):
        j, fe = faux_jeu_menu(SLOT); f = j.moteur.ui.f[12]
        self.assertTrue(j._saisie_pas(12, f, fe, {0: 1}, MO.HAUT)); self.assertEqual(j.envois[-1], (12, 1, 1, 0x2), '▲ de la colonne 1 (manette 0x2)')
        self.assertEqual(j.menu_relacher, 12, 'le relachement suit a l\'image suivante')
        self.assertTrue(j._saisie_pas(12, f, fe, {0: 1}, MO.BAS)); self.assertEqual(j.envois[-1], (12, 1, 1, 0x1), '▼ (manette 0x1)')
        self.assertIsNone(j.survol_nd, 'une touche : le curseur reprend la main')

    def test_colonnes_gauche_droite(self):
        j, fe = faux_jeu_menu(JETONS, 44); f = j.moteur.ui.f[12]; z = {0: 1}
        self.assertEqual(j._pas_actif(12), 1, 'au depart : les unites (colonne de droite)')
        j._saisie_pas(12, f, fe, z, MO.GAUCHE); self.assertEqual(j._pas_actif(12), 10)
        j._saisie_pas(12, f, fe, z, MO.GAUCHE); j._saisie_pas(12, f, fe, z, MO.GAUCHE); j._saisie_pas(12, f, fe, z, MO.GAUCHE); j._saisie_pas(12, f, fe, z, MO.GAUCHE); j._saisie_pas(12, f, fe, z, MO.GAUCHE)
        self.assertEqual(j._pas_actif(12), 10000, 'bornee a gauche')
        j._saisie_pas(12, f, fe, z, MO.HAUT); self.assertEqual(j.envois[-1], (12, 1, 10000, 0x2))
        for _ in range(8): j._saisie_pas(12, f, fe, z, MO.DROITE)
        self.assertEqual(j._pas_actif(12), 1, 'bornee a droite')
        self.assertEqual(j.envois, [(12, 1, 10000, 0x2)], 'gauche / droite ne transmettent rien au moteur')

    def test_valider_et_retour(self):
        j, fe = faux_jeu_menu(SLOT); f = j.moteur.ui.f[12]
        self.assertTrue(j._saisie_pas(12, f, fe, {0: 1}, MO.A)); self.assertEqual(j.envois[-1], (12, 1, 0, 0x10), 'A = bouton de validation (Lancer)')
        self.assertTrue(j._saisie_pas(12, f, fe, {0: 1}, MO.B)); self.assertEqual(j.envois[-1], (12, 1, -1, 0x20), 'B = retour (manette 0x20)')

    def test_aucune_touche_utile(self):
        j, fe = faux_jeu_menu(SLOT); self.assertFalse(j._saisie_pas(12, j.moteur.ui.f[12], fe, {0: 1}, 0)); self.assertEqual(j.envois, [])

    def test_plusieurs_validations_curseur_ordinaire(self):
        """Une fenetre qui a plusieurs boutons de validation (choix a faire) garde le curseur ordinaire."""
        j, fe = faux_jeu_menu(SLOT + [b(2, 0x10, 0, 200)]); self.assertIsNone(j._pas_actif(12))


class EchapRetour(unittest.TestCase):
    def test_casino_avec_bouton_retour(self):
        j, fe = faux_jeu_menu(SLOT); self.assertTrue(j._echap_retour(), 'machine a sous : Echap = retour')

    def test_bestiaire_avec_bouton_retour(self):
        j, fe = faux_jeu_menu([b(0, 0x10, 0, 0), b(-1, 0x20, 200, 0)], 28, MO.PARTIE_BESTIAIRE); self.assertTrue(j._echap_retour())

    def test_sans_bouton_retour_le_menu_echap_s_ouvre(self):
        """Rouleaux en marche, cartes en cours de distribution : la fenetre n'a plus de bouton retour actif."""
        j, fe = faux_jeu_menu([b(0, 0x10, 0, 0)]); self.assertFalse(j._echap_retour())

    def test_message_visible(self):
        j, fe = faux_jeu_menu(SLOT); j.moteur.msg_visible = True; self.assertFalse(j._echap_retour(), 'un message : le menu Echap')

    def test_aucun_menu(self):
        j, fe = faux_jeu_menu(SLOT); j.moteur.menu_actif = lambda: None; self.assertFalse(j._echap_retour())


class ArenePageMessage(unittest.TestCase):
    """Combat de l'arene : la seule fenetre ouverte est « Quitter » (type 71, un bouton de manette 0x400). A tourne la page du message (la fenetre n'a pas de bouton de validation) et
    la fenetre n'est pas une attente du joueur (la vitesse des combats s'applique au combat de l'arene)."""
    def jeu(self, boutons, grille=None, partie=MO.PARTIE_COMBAT):
        j, fe = faux_jeu_menu(boutons, 71, partie); j.moteur.ui.f[12]['grille'] = grille
        j._quitter_seul = functools.partial(F.Jeu._quitter_seul, j); j._attend_joueur = functools.partial(F.Jeu._attend_joueur, j); j.moteur.ui.msg = {}
        return j

    def test_quitter_seul(self):
        j = self.jeu([b(0, 0x400, 0, 62)]); self.assertTrue(F.sans_validation(j.moteur, j.ui_g, 12)); self.assertTrue(j._quitter_seul(12))

    def test_fenetre_a_validation(self):
        j = self.jeu([b(0, 0x10, 0, 0), b(-1, 0x20, 200, 0)]); self.assertFalse(j._quitter_seul(12), 'un bouton A : la touche lui appartient')

    def test_oui_non_du_moteur(self):
        self.assertFalse(self.jeu([], grille=(1, 2, 2))._quitter_seul(12), 'curseur du moteur (Oui / Non) : A est la sienne')

    def test_hors_combat(self):
        self.assertFalse(self.jeu([b(0, 0x400, 0, 62)], partie=MO.PARTIE_CASINO)._quitter_seul(12), 'la regle ne vaut qu\'en combat')

    def test_sans_fenetre_de_menu(self):
        j = self.jeu([b(0, 0x400, 0, 62)]); j.ui_g = None; self.assertFalse(j._quitter_seul(12))
        j = self.jeu([b(0, 0x400, 0, 62)]); self.assertFalse(j._quitter_seul(99))

    def test_attente_du_joueur(self):
        self.assertFalse(self.jeu([b(0, 0x400, 0, 62)])._attend_joueur(), 'arene : « Quitter » seul ouvert : le combat n\'attend personne')
        self.assertTrue(self.jeu([b(0, 0x10, 0, 0)])._attend_joueur(), 'menu a boutons de validation (commandes, cibles...) : attente du joueur')
        self.assertTrue(self.jeu([], grille=(1, 2, 2))._attend_joueur(), 'Oui / Non du moteur : attente du joueur')
        j = self.jeu([b(0, 0x400, 0, 62)]); j.moteur.menu_actif = lambda: None; self.assertFalse(j._attend_joueur())
        j.moteur.msg_visible = True; j.moteur.ui.msg = {'feed': True}; self.assertTrue(j._attend_joueur(), 'message avec son curseur : attente du joueur')


class CodeMasque(unittest.TestCase):
    """Poker (type 48) : le code 2 de la fenetre recoit un MASQUE (63 = tout actif) ; le tableau `fx` exporte ne connait que 0 a 5."""
    def fenetre(self, fx):
        e = {'kind': 'func', 'fx': fx}
        f = types.SimpleNamespace(N={10: {'buttonId': 0, 'act': False}, 11: {'buttonId': 1, 'act': False}, 12: {'buttonId': 5, 'act': False}, 13: {'buttonId': None, 'act': True}}, codes={2: [e]}, vals_code={}, eglise=False, statut=False, noms=False, debut=False)
        f.code = functools.partial(UI.Fenetre.code, f); f._code_masque = functools.partial(UI.Fenetre._code_masque, f)
        return f, e

    FX_REGULIER = {'0': {'d': {'10': {'act': False}, '11': {'act': False}, '12': {'act': False}}}, '1': {'d': {'11': {'act': False}, '12': {'act': False}}}, '2': {'d': {'10': {'act': False}, '12': {'act': False}}},
                   '3': {'d': {'12': {'act': False}}}}

    def test_masque_hors_tableau(self):
        f, e = self.fenetre(self.FX_REGULIER)
        f.code(2, 63); self.assertEqual([f.N[n]['act'] for n in (10, 11, 12)], [True, True, True], '63 : toutes les zones tactiles (cartes 0, 1 et « Donner »)')
        f.code(2, 33); self.assertEqual([f.N[n]['act'] for n in (10, 11, 12)], [True, False, True], 'bits 0 et 5')
        self.assertTrue(f.N[13]['act'], 'un element hors du masque n\'est pas touche')

    def test_valeur_du_tableau_inchangee(self):
        f, e = self.fenetre(self.FX_REGULIER)
        f.code(2, 1); self.assertEqual([f.N[n]['act'] for n in (10, 11, 12)], [True, False, False], 'valeur 1 du tableau : comme avant')

    def test_tableau_irregulier_rien(self):
        """Un tableau qui n'a pas la forme « bit n = bouton n » : on n'invente rien (comportement d'origine)."""
        fx = {'0': {'d': {'10': {'act': False}, '11': {'act': False}}}, '1': {'d': {'10': {'act': False}, '11': {'act': False}}}}
        f, e = self.fenetre(fx); f.code(2, 63); self.assertEqual([f.N[n]['act'] for n in (10, 11)], [False, False])

    def test_valeur_negative_ou_non_entiere(self):
        f, e = self.fenetre(self.FX_REGULIER)
        f.code(2, -1); f.code(2, 'x'); self.assertEqual([f.N[n]['act'] for n in (10, 11, 12)], [False, False, False])


if __name__ == '__main__':
    unittest.main(verbosity=1)
