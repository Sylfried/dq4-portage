"""Test du retour a l'ecran-titre (issue #109) : menu Pause > « Revenir à l'écran titre » = la boite d'origine du jeu (son texte, Oui / Non), puis le fondu au noir du jeu, puis le titre.

    python3 outils/test_retour_titre.py [--apk <dossier des APK patches> --saves <dossier des sauvegardes>]
(ou DQ_APK et DQ_SAVES ; sans eux seules les parties 1 et 2 tournent). La partie 3 charge le vrai moteur (environ 1 minute) : a lancer par `outils/flux_session/moteur_slot.sh`.

Partie 1 (sans moteur) : la ligne du menu Pause. Elle ferme le menu et demande le retour au titre au jeu (plus de page de confirmation du menu Pause : la question est celle du jeu) ; elle est grisee
quand le jeu n'est pas en ville ni sur la carte du monde.
Partie 2 (moteur simule) : `Moteur.demander_retour_titre` et les deux moments joues autour de GameUpdate (`_retour_titre_avant` / `_retour_titre_apres`) : les appels du moteur dans l'ordre du menu des
Parametres d'origine (TownMenu_OPERATION_SETTING::menuUpdate, etat 5), « Non » ne change rien, « Oui » efface la banque 4 puis lance Global::startTitle ; une boite fermee sans reponse libere le joueur.
Partie 3 (vrai moteur, en ville) : la boite s'ouvre et reste ouverte ; « Non » (flèche vers Non puis A) la ferme sans lancer le titre ; « Oui » (A, curseur d'origine sur Oui) lance killbank puis startTitle dans le
pas meme de GameUpdate et le fondu au noir est progressif (30 images, jamais un saut), puis la carte du titre se charge.
"""
import argparse, inspect, os, struct, sys, tempfile, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False                     # (pas d'affichage necessaire : on ne dessine rien)
import reglages as RG
import pause as PA
import moteur as MO

K = pyglet.window.key
APK = os.environ.get('DQ_APK'); SAVES = os.environ.get('DQ_SAVES'); REST = sys.argv[1:]
if __name__ == '__main__':
    _ap = argparse.ArgumentParser(); _ap.add_argument('--apk'); _ap.add_argument('--saves'); _a, REST = _ap.parse_known_args()
    APK = _a.apk or APK; SAVES = _a.saves or SAVES
LIBELLE = "Revenir à l'écran titre"
PAD_BAS = 1; PAD_A = 0x10                                    # manette du jeu envoyee aux menus : bas 1, haut 2, droite 4, gauche 8, A 16, B 32 (Jeu._saisie_menu) ; le moteur range Oui / Non en une colonne (grille 1 x 2) : « droite » de la visionneuse part en « bas »


class FauxSon:
    actif = True; ecoute = False


class FauxJeu:
    """Ce que le menu Pause demande a la fenetre."""
    def __init__(self, possible=True):
        self.reg = RG.Reglages(os.path.join(tempfile.mkdtemp(prefix='retour_titre_'), 'reglages.json'))
        self.son = FauxSon(); self.args = types.SimpleNamespace(cache='/inexistant'); self.width, self.height = 1280, 720; self.souris = None
        self.appels = []; self.possible = possible
    def noms_fenetres(self): return {}
    def pause_jeu(self, oui): self.appels.append(('pause_jeu', oui))
    def retour_titre(self): self.appels.append('titre')
    def retour_titre_possible(self): return self.possible


def menu(possible=True):
    J = FauxJeu(possible); p = PA.Pause(J); p.ouvert = True; p.pile = ['racine']
    return J, p


def ligne(p): return next(e for e in p._entrees() if e.get('l') == LIBELLE)


def choisir(p):
    """Place le curseur de la racine sur la ligne du retour au titre."""
    p.sel['racine'] = [e.get('l') for e in p._entrees()].index(LIBELLE)


# ---------------------------------------------------------------------------------------------------------------------------------- 1. le menu Pause
class LigneDuMenu(unittest.TestCase):
    def test_la_ligne_est_la_derniere_de_la_racine(self):
        J, p = menu(); libs = [e['l'] for e in p._entrees() if e['t'] != 'sep']
        self.assertEqual(libs[-1], LIBELLE)

    def test_plus_de_page_de_confirmation_du_menu_pause(self):
        self.assertFalse(hasattr(PA.Pause, '_e_titre'))                                                  # la question est celle du jeu (boite d'origine), pas une page du menu
        src = inspect.getsource(PA.Pause); self.assertNotIn("_aller('titre')", src); self.assertNotIn("titres['titre']", src)

    def test_valider_ferme_le_menu_et_demande_le_retour_au_jeu(self):
        J, p = menu(); choisir(p); p.touche(K.RETURN)
        self.assertFalse(p.ouvert); self.assertEqual([a for a in J.appels if a == 'titre'], ['titre'])
        self.assertIn(('pause_jeu', False), J.appels)                                                    # le jeu reprend : c'est lui qui pose la question

    def test_l_action_de_la_ligne_est_celle_du_clic(self):
        J, p = menu(); ligne(p)['ok'](); self.assertFalse(p.ouvert); self.assertEqual(J.appels.count('titre'), 1)

    def test_grisee_hors_ville_et_carte_du_monde(self):
        J, p = menu(possible=False); e = ligne(p)
        self.assertTrue(p._inactif(e)); self.assertFalse(p._actif(e)); self.assertTrue(e.get('aide'))   # grisee, avec son explication
        choisir(p); p.touche(K.RETURN)
        self.assertTrue(p.ouvert); self.assertNotIn('titre', J.appels)                                  # rien ne part

    def test_active_quand_possible(self):
        J, p = menu(possible=True); self.assertFalse(p._inactif(ligne(p)))

    def test_le_jeu_sait_quand_c_est_possible(self):
        import fenetre as F
        src = inspect.getsource(F.Jeu.retour_titre_possible)
        self.assertIn('PARTIE_VILLE', src); self.assertIn('PARTIE_CHAMP', src); self.assertIn('CARTE_TITRE', src); self.assertNotIn('PARTIE_COMBAT', src)
        self.assertIn('demander_retour_titre', inspect.getsource(F.Jeu.retour_titre))


# ---------------------------------------------------------------------------------------------------------------------------------- 2. le moteur (simule)
class FauxCoeur:
    """Remplace emu_core : enregistre les appels du moteur (noms de symboles), garde une memoire a mots."""
    def __init__(self): self.appels = []; self.memoire = {}; self.ouverte = True
    def export(self, nom): return 0x5000 if nom == 'gTownMenu_MESSAGE' else 0x9000
    def call(self, adresse, *args, label=None):
        self.appels.append((adresse, args))
        return (1 if self.ouverte else 0) if adresse == '_ZN8MenuBase6isOpenEv' else 0
    def mem(self, adr, n): return self.memoire.get(adr, bytes(n))
    def mem_w(self, adr, octets): self.memoire[adr] = bytes(octets); self.appels.append(('mem_w', (adr, bytes(octets))))
    def noms(self): return [a[0] for a in self.appels if isinstance(a[0], str) and a[0] != 'mem_w']


def moteur_simule(partie=MO.PARTIE_VILLE):
    m = MO.Moteur.__new__(MO.Moteur); m.core = FauxCoeur(); m.E = lambda s: s; m._global = lambda: 0x7000
    m.etat = types.SimpleNamespace(partie=partie); m.retour_titre_etat = None
    return m


def reponse(m, v): m.core.memoire[0x5000 + MO.MESSAGE_RESULTAT] = struct.pack('<I', v)


class MachineRetour(unittest.TestCase):
    def test_constantes_du_menu_d_origine(self):
        self.assertEqual(MO.MSG_RETOUR_TITRE, 0xcba2f); self.assertEqual(MO.MESSAGE_RESULTAT, 0x10)

    def test_seulement_en_ville_et_sur_la_carte(self):
        for partie, attendu in ((MO.PARTIE_VILLE, True), (MO.PARTIE_CHAMP, True), (MO.PARTIE_COMBAT, False), (MO.PARTIE_CASINO, False), (MO.PARTIE_BESTIAIRE, False), (MO.PARTIE_DEPART, False)):
            m = moteur_simule(partie); self.assertEqual(m.demander_retour_titre(), attendu, partie); self.assertEqual(m.retour_titre_etat, 'ouvrir' if attendu else None)

    def test_une_seule_demande_a_la_fois(self):
        m = moteur_simule(); self.assertTrue(m.demander_retour_titre()); self.assertFalse(m.demander_retour_titre())

    def test_ouverture_comme_le_menu_d_origine(self):
        m = moteur_simule(); m.demander_retour_titre(); reponse(m, 2); m._retour_titre_avant()               # (une ancienne reponse ne compte pas : remise a 0)
        self.assertEqual(m.retour_titre_etat, 'dialogue')
        self.assertEqual(m.core.noms(), ['_ZN3cmn11GameManager12getSingletonEv', '_ZN3cmn13PlayerManager7setLockEb', '_ZN16TownMenu_MESSAGE18openMessageForMENUEv', '_ZN16TownMenu_MESSAGE10addMessageEi',
                                         '_ZN16TownMenu_MESSAGE8setYesNoEv', '_ZN16TownMenu_MESSAGE19setYesNoSuperCancelEb'])
        a = {x[0]: x[1] for x in m.core.appels if isinstance(x[0], str)}
        self.assertEqual(a['_ZN3cmn13PlayerManager7setLockEb'], (1,)); self.assertEqual(a['_ZN16TownMenu_MESSAGE10addMessageEi'], (0x5000, 0xcba2f)); self.assertEqual(a['_ZN16TownMenu_MESSAGE19setYesNoSuperCancelEb'], (0x5000, 0))
        self.assertEqual(m.core.memoire[0x5000 + MO.MESSAGE_RESULTAT], bytes(4))

    def test_rien_avant_la_demande(self):
        m = moteur_simule(); m._retour_titre_avant(); m._retour_titre_apres(); self.assertEqual(m.core.appels, []); self.assertIsNone(m.retour_titre_etat)

    def test_attente_de_la_reponse(self):
        m = moteur_simule(); m.demander_retour_titre(); m._retour_titre_avant(); m.core.appels.clear(); reponse(m, 0); m._retour_titre_apres()
        self.assertEqual(m.retour_titre_etat, 'dialogue'); self.assertEqual(m.core.noms(), ['_ZN8MenuBase6isOpenEv'])                                # seulement la lecture de l'etat de la boite

    def test_non_ne_change_rien(self):
        m = moteur_simule(); m.demander_retour_titre(); m._retour_titre_avant(); m.core.appels.clear(); reponse(m, 2); m._retour_titre_apres()
        self.assertIsNone(m.retour_titre_etat); n = m.core.noms()
        self.assertIn('_ZN8MenuBase5closeEv', n); self.assertNotIn('_ZN6Global10startTitleEv', n); self.assertNotIn('_ZN7profile8SaveLoad8killbankEib', n)
        self.assertEqual([x[1] for x in m.core.appels if x[0] == '_ZN3cmn13PlayerManager7setLockEb'], [(0,)])               # le joueur est libere

    def test_oui_efface_la_banque_4_puis_lance_le_titre(self):
        m = moteur_simule(); m.demander_retour_titre(); m._retour_titre_avant(); m.core.appels.clear(); reponse(m, 1); m._retour_titre_apres()
        self.assertIsNone(m.retour_titre_etat); n = m.core.noms()
        self.assertLess(n.index('_ZN7profile8SaveLoad8killbankEib'), n.index('_ZN6Global10startTitleEv')); self.assertEqual(n[-1], '_ZN6Global10startTitleEv')
        self.assertEqual([x[1] for x in m.core.appels if x[0] == '_ZN7profile8SaveLoad8killbankEib'], [(4, 0)])
        self.assertEqual([x[1] for x in m.core.appels if x[0] == '_ZN3cmn13PlayerManager7setLockEb'], [(1,)])

    def test_boite_fermee_sans_reponse_libere_le_joueur(self):
        m = moteur_simule(); m.demander_retour_titre(); m._retour_titre_avant(); m.core.appels.clear(); m.core.ouverte = False; reponse(m, 0); m._retour_titre_apres()
        self.assertIsNone(m.retour_titre_etat); self.assertEqual([x[1] for x in m.core.appels if x[0] == '_ZN3cmn13PlayerManager7setLockEb'], [(0,)]); self.assertNotIn('_ZN6Global10startTitleEv', m.core.noms())
        self.assertTrue(m.demander_retour_titre())                                                                        # et on peut redemander

    def test_les_deux_moments_sont_dans_le_pas_du_moteur(self):
        """Le fondu du titre est un paquet lu avec ceux du pas : startTitle doit etre lance entre `pk.begin()` et `pk.packets()`, autour de GameUpdate (sinon le fondu est perdu et l'ecran saute au noir)."""
        src = inspect.getsource(MO.Moteur.step)
        i0 = src.index('self.pk.begin()'); i1 = src.index('_retour_titre_avant()'); i2 = src.index("'GameUpdate'"); i3 = src.index('_retour_titre_apres()'); i4 = src.index('self.pk.packets()')
        self.assertTrue(i0 < i1 < i2 < i3 < i4)


# ---------------------------------------------------------------------------------------------------------------------------------- 3. le vrai moteur
@unittest.skipUnless(APK and SAVES, 'moteur reel : --apk et --saves (ou DQ_APK et DQ_SAVES)')
class MoteurReel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import unicorn, etats as ET
        cls.ET = ET; mo = cls.mo = MO.Moteur(APK, SAVES, tempfile.mkdtemp(prefix='sv_retour_titre_')); c = cls.c = mo.core
        mo.charger_sauvegarde(1)
        for _ in range(200): mo.step(0, 0)
        cls.partie0 = mo.etat.partie; cls.carte0 = mo.etat.carte
        def compteur(nom):
            adr = c.export(nom); n = []; c.uc.hook_add(unicorn.UC_HOOK_CODE, lambda u, a, sz, ud: n.append(mo.images), None, adr, adr); return n
        cls.titre = compteur('_ZN6Global10startTitleEv'); cls.kill = compteur('_ZN7profile8SaveLoad8killbankEib'); c.uc.ctl_flush_tb()
        cls.depart = ET.instantane(mo)

    def setUp(self):
        self.ET.appliquer(self.mo, self.depart); self.mo.retour_titre_etat = None; self.titre.clear(); self.kill.clear()

    def boite(self): return self.c.export('gTownMenu_MESSAGE')
    def ouverte(self): return bool(self.c.call(self.c.export('_ZN8MenuBase6isOpenEv'), self.boite()) & 1)
    def reponse(self): return struct.unpack('<I', self.c.mem(self.boite() + MO.MESSAGE_RESULTAT, 4))[0]

    def pas(self, n=1, p=0, d=0):
        for _ in range(n): self.mo.step(p, d); self.mo.ui.degats = []; p = d = 0

    def touche(self, pad):
        """Une touche de la manette envoyee au menu du moteur qui a la saisie (comme Jeu._saisie_menu : [1, -1, manette]), relachee a l'image suivante, puis 8 images de repos."""
        port = self.mo.menu_actif(); self.assertIsNotNone(port, 'aucun menu du moteur n\'attend de touche')
        self.mo.envoyer_menu(port, 1, -1, pad); self.pas(1); self.mo.envoyer_menu(port, 1, -1, 0); self.pas(1); self.pas(8)

    def ouvrir_boite(self):
        self.assertTrue(self.mo.demander_retour_titre()); self.pas(150)                                    # le texte s'ecrit, puis Oui / Non
        self.assertEqual(self.mo.retour_titre_etat, 'dialogue'); self.assertTrue(self.ouverte()); self.assertEqual(self.reponse(), 0); self.assertIsNotNone(self.mo.menu_actif())           # Oui / Non attend

    def test_1_la_boite_s_ouvre_et_attend(self):
        self.ouvrir_boite(); self.pas(120)
        self.assertEqual(self.mo.retour_titre_etat, 'dialogue'); self.assertTrue(self.ouverte()); self.assertEqual(self.titre, [])          # elle attend : rien ne se passe sans reponse

    def test_2_non_ne_change_rien(self):
        self.ouvrir_boite(); self.touche(PAD_BAS); self.touche(PAD_A); self.pas(30)
        self.assertIsNone(self.mo.retour_titre_etat); self.assertFalse(self.ouverte())
        self.assertEqual(self.titre, []); self.assertEqual(self.kill, [])                                      # ni banque effacee, ni titre
        self.assertEqual(self.mo.etat.partie, self.partie0); self.assertEqual(self.mo.etat.carte, self.carte0)
        self.assertLess(self.mo.etat.fondu['a'], 0.01)                                                        # aucun fondu

    def test_3_oui_lance_le_fondu_puis_le_titre(self):
        self.ouvrir_boite(); self.touche(PAD_A)                                                          # le curseur d'origine est sur « Oui »
        alphas = []
        for _ in range(140): self.pas(1); alphas.append(self.mo.etat.fondu['a'])
        self.assertEqual(len(self.titre), 1); self.assertEqual(len(self.kill), 1); self.assertLessEqual(self.kill[0], self.titre[0])        # banque 4 effacee puis titre, une fois chacun
        sauts = [b - a for a, b in zip(alphas, alphas[1:])]
        self.assertLess(max(sauts), 0.1, 'le fondu saute au noir : %.3f' % max(sauts))                      # progressif (un trente-troisieme par image), jamais d'un coup
        self.assertGreaterEqual(sum(1 for a in alphas if 0.05 < a < 0.95), 20)                               # une trentaine d'images de fondu
        self.assertGreater(max(alphas), 0.99)
        self.assertFalse(self.ouverte())

    def test_4_une_demande_apres_non_est_possible(self):
        self.ouvrir_boite(); self.touche(PAD_BAS); self.touche(PAD_A); self.pas(30)
        self.ouvrir_boite()                                                                                   # et la meme question se pose de nouveau


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + REST)
