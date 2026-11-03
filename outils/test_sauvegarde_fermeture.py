"""Test de la sauvegarde automatique a la fermeture de l'application (issue #122) : en fermant le jeu (croix, Alt + F4, menu Quitter, fin de tache, fermeture de la console, Ctrl + C, fin de session Windows) le moteur
ecrit SA sauvegarde automatique (« Sauvegarde automatique » du menu de depart : banque 4, data5.dat), pas un systeme a part ; « Revenir à l'écran titre » l'efface (killbank) et elle ne doit pas revenir.

    python3 outils/test_sauvegarde_fermeture.py [--apk <dossier des APK patches> --saves <dossier des sauvegardes>]
(ou DQ_APK et DQ_SAVES ; sans eux seules les parties 1 et 2 tournent). La partie 3 charge le vrai moteur (environ 1 minute) : a lancer par `outils/flux_session/moteur_slot.sh`.

Partie 1 (sans moteur) : Moteur.sauvegarde_auto_possible (quand ca a un sens) et Moteur.sauvegarde_auto (AutoSave(true) du moteur, 0x164aa8).
Partie 2 (fenetre simulee) : Jeu._sauvegarde_fermeture (une seule fois, dite dans la console, jamais d'erreur, rien pour les captures), l'ordre de on_close, le menu Quitter, la fermeture demandee par un autre fil
(console de Windows, signaux) et le message WM_ENDSESSION.
Partie 3 (vrai moteur) : AutoSave(true) ecrit data5.dat dans le dossier d'ecriture ; le moteur la relit (loadbank(4)) et retrouve la partie ; « Revenir à l'écran titre » : plus de sauvegarde pendant le fondu ni au titre.
"""
import argparse, hashlib, inspect, io, os, signal, struct, sys, tempfile, threading, time, types, unittest
from contextlib import redirect_stdout

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False                     # (pas d'affichage necessaire : on ne dessine rien)
import moteur as MO

APK = os.environ.get('DQ_APK'); SAVES = os.environ.get('DQ_SAVES'); REST = sys.argv[1:]
if __name__ == '__main__':
    _ap = argparse.ArgumentParser(); _ap.add_argument('--apk'); _ap.add_argument('--saves'); _a, REST = _ap.parse_known_args()
    APK = _a.apk or APK; SAVES = _a.saves or SAVES
PAD_BAS = 1; PAD_A = 0x10


def faux_moteur(partie=MO.PARTIE_VILLE, carte='mak1f1', titre_fait=False, titre_etat=None):
    """Ce que sauvegarde_auto_possible lit du moteur (la vraie methode, liee a un faux objet)."""
    m = types.SimpleNamespace(etat=types.SimpleNamespace(partie=partie, carte=carte), retour_titre_fait=titre_fait, retour_titre_etat=titre_etat)
    m.sauvegarde_auto_possible = lambda: MO.Moteur.sauvegarde_auto_possible(m)
    return m


class FauxCoeur:
    def __init__(self, retour=1): self.appels = []; self.retour = retour
    def call(self, adr, *args, label=''): self.appels.append((label, adr) + args); return self.retour
    def export(self, nom): return 0x1000


# ---------------------------------------------------------------------------------------------------------------------------------- 1. le moteur
class QuandSauvegarder(unittest.TestCase):
    def test_en_ville_au_donjon_et_sur_la_carte_du_monde(self):
        self.assertTrue(faux_moteur(MO.PARTIE_VILLE, 'mak1f1').sauvegarde_auto_possible())
        self.assertTrue(faux_moteur(MO.PARTIE_CHAMP, 'field').sauvegarde_auto_possible())

    def test_pas_en_dehors_d_une_partie(self):
        for partie in (MO.PARTIE_DEPART, MO.PARTIE_COMBAT, MO.PARTIE_CASINO, MO.PARTIE_BESTIAIRE, 0, 1):
            self.assertFalse(faux_moteur(partie, 'mak1f1').sauvegarde_auto_possible(), partie)

    def test_pas_a_l_ecran_titre(self):
        self.assertFalse(faux_moteur(MO.PARTIE_VILLE, MO.CARTE_TITRE).sauvegarde_auto_possible())            # (le titre est une scene de ville : ev01)
        self.assertFalse(faux_moteur(MO.PARTIE_VILLE, None).sauvegarde_auto_possible())                      # (aucune carte chargee : logos, chargement)

    def test_pas_pendant_un_retour_au_titre(self):
        self.assertFalse(faux_moteur(titre_fait=True).sauvegarde_auto_possible())                            # killbank fait, le fondu court : la banque 4 doit rester effacee
        self.assertFalse(faux_moteur(titre_etat='dialogue').sauvegarde_auto_possible())                      # la boite Oui / Non attend : une demande en cours

    def test_sauvegarde_auto_appelle_autosave_force(self):
        m = faux_moteur(); m.core = FauxCoeur(1); m.E = lambda nom: ('adr', nom)
        self.assertEqual(MO.Moteur.sauvegarde_auto(m), 1)
        self.assertEqual(m.core.appels, [('AutoSave', ('adr', '_Z8AutoSaveb'), 1)])                         # AutoSave(true) : sans les conditions de AutoSave(false), qui refuse villes et donjons

    def test_refus_du_moteur(self):
        m = faux_moteur(); m.core = FauxCoeur(0xffffffff); m.E = lambda nom: 0x10                           # AutoSave renvoie -1 en cas d'echec de savebank
        self.assertEqual(MO.Moteur.sauvegarde_auto(m), -1)
        m.core = FauxCoeur(None); self.assertEqual(MO.Moteur.sauvegarde_auto(m), -1)

    def test_rien_n_est_appele_hors_partie(self):
        m = faux_moteur(MO.PARTIE_DEPART); m.core = FauxCoeur(1); m.E = lambda nom: 0x10
        self.assertEqual(MO.Moteur.sauvegarde_auto(m), 0); self.assertEqual(m.core.appels, [])

    def test_le_drapeau_du_retour_au_titre(self):
        src = inspect.getsource(MO.Moteur.retour_titre); self.assertIn('self.retour_titre_fait = True', src); self.assertLess(src.index('retour_titre_fait = True'), src.index("label='killbank'"))
        stp = inspect.getsource(MO.Moteur.step); self.assertIn('self.retour_titre_fait = False', stp); self.assertIn('CARTE_TITRE', stp.split('self.retour_titre_fait = False')[0].splitlines()[-1])
        self.assertIn('retour_titre_fait = False', inspect.getsource(MO.Moteur.reappliquer_correctifs))     # un etat charge : la partie repart


# ---------------------------------------------------------------------------------------------------------------------------------- 2. la fenetre (simulee)
import fenetre as F


class FausseFenetre:
    """Ce que la fermeture lit de Jeu ; les vraies methodes de Jeu lui sont liees."""
    def __init__(self, resultat=1, shot=None, pret=True):
        self.args = types.SimpleNamespace(shot=shot); self.resultat = resultat; self.appels = []; self._pret = pret
        self._auto_faite = False; self._arret_externe = threading.Event(); self._arret_fini = threading.Event(); self._arret_motif = None; self.fermee = 0
        self.moteur = types.SimpleNamespace(sauvegarde_auto=self._sauvegarde)
    def _sauvegarde(self):
        self.appels.append('sauvegarde')
        if isinstance(self.resultat, Exception): raise self.resultat
        return self.resultat
    def on_close(self): self.fermee += 1; self._sauvegarde_fermeture(self._arret_motif or 'fermeture de la fenêtre')
    def __getattr__(self, nom):
        f = getattr(F.Jeu, nom, None)
        if callable(f) and nom.startswith('_') and not nom.startswith('__'): return types.MethodType(f, self)
        raise AttributeError(nom)


def sortie(f, *a, **k):
    tampon = io.StringIO()
    with redirect_stdout(tampon): r = f(*a, **k)
    return r, tampon.getvalue()


class FermetureSimulee(unittest.TestCase):
    def test_ecrite_une_seule_fois(self):
        J = FausseFenetre(1); _, out = sortie(J._sauvegarde_fermeture); sortie(J._sauvegarde_fermeture); sortie(J._sauvegarde_fermeture, 'autre')
        self.assertEqual(J.appels, ['sauvegarde']); self.assertIn('Sauvegarde automatique écrite', out)                  # la croix puis Alt + F4 le meme instant : une seule ecriture

    def test_dite_dans_la_console(self):
        self.assertIn('aucune partie en cours', sortie(FausseFenetre(0)._sauvegarde_fermeture)[1])
        self.assertIn('refusée par le moteur', sortie(FausseFenetre(-1)._sauvegarde_fermeture)[1])
        self.assertIn('(Ctrl + C)', sortie(FausseFenetre(1)._sauvegarde_fermeture, 'Ctrl + C')[1])

    def test_une_erreur_n_arrete_pas_la_fermeture(self):
        J = FausseFenetre(RuntimeError('boum')); r, out = sortie(J._sauvegarde_fermeture)
        self.assertIn('impossible', out); self.assertIn('boum', out)

    def test_captures_de_test_sans_ecriture(self):
        J = FausseFenetre(1, shot='capture.png'); sortie(J._sauvegarde_fermeture); self.assertEqual(J.appels, [])      # --shot : rien n'est ecrit dans les dossiers de sauvegarde
        os.environ['DQ_SAUVEGARDE_FERMETURE'] = '1'
        try: J = FausseFenetre(1, shot='capture.png'); sortie(J._sauvegarde_fermeture); self.assertEqual(J.appels, ['sauvegarde'])
        finally: del os.environ['DQ_SAUVEGARDE_FERMETURE']

    def test_ordre_de_on_close(self):
        src = inspect.getsource(F.Jeu.on_close)
        i_pret = src.index('self._pret'); i_auto = src.index('_sauvegarde_fermeture'); i_reg = src.index('self.reg.enregistrer()'); i_son = src.index('self.son.fermer()')
        self.assertTrue(i_pret < i_auto < i_reg < i_son)                      # fenetre prete (pas pendant les logos), puis la sauvegarde (le moteur, le son se ferment apres)

    def test_le_menu_quitter_passe_par_on_close(self):
        src = inspect.getsource(F.Jeu.quitter); self.assertIn('self.on_close()', src); self.assertNotIn('self.close()', src)         # (il fermait la fenetre sans passer par on_close : ni sauvegarde ni reglages)

    def test_la_boucle_regarde_les_demandes_des_autres_fils(self):
        src = inspect.getsource(F.Jeu._boucle); self.assertIn('_arret_externe', src); self.assertLess(src.index('_arret_externe'), src.index('self.pause.ouvert'))

    def test_console_de_windows_la_fermeture_attend_la_sauvegarde(self):
        J = FausseFenetre(1); res = []
        fil = threading.Thread(target=lambda: res.append(J._arret_console('fermeture de la console', 3.0))); fil.start()
        self.assertTrue(J._arret_externe.wait(2.0))                                                        # le fil de la console demande la fermeture...
        self.assertTrue(fil.is_alive())                                                                    # ...et attend
        J.__getattr__('_arret_externe_traiter')()                                                          # la boucle principale la fait (on_close puis liberation)
        fil.join(2.0); self.assertEqual(res, [True]); self.assertEqual(J.fermee, 1); self.assertEqual(J.appels, ['sauvegarde']); self.assertEqual(J._arret_motif, 'fermeture de la console')
        self.assertTrue(J._arret_fini.is_set())

    def test_console_de_windows_delai_borne(self):
        J = FausseFenetre(1); t = time.time(); self.assertTrue(J._arret_console('Ctrl + C', 0.2)); self.assertLess(time.time() - t, 1.5)        # boucle bloquee : le gestionnaire rend la main

    def test_console_de_windows_cas_ignores(self):
        self.assertFalse(FausseFenetre(1)._arret_console(None))                                            # evenement inconnu : Windows fait ce qu'il fait d'habitude
        self.assertFalse(FausseFenetre(1, pret=False)._arret_console('Ctrl + C'))                          # logos, chargement : rien a sauvegarder
        J = FausseFenetre(1); J._auto_faite = True; self.assertFalse(J._arret_console('Ctrl + C'))         # deja fait

    def test_evenements_de_la_console_surveilles(self):
        src = inspect.getsource(F.Jeu._installer_arret_externe)
        self.assertIn('SetConsoleCtrlHandler', src)
        for motif in ('Ctrl + C', 'fermeture de la console', 'fermeture de session', 'arrêt de Windows'): self.assertIn(motif, src)

    @unittest.skipIf(sys.platform == 'win32', 'signaux POSIX')
    def test_signal_sigterm(self):
        J = FausseFenetre(1); ancien = signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGHUP)
        try:
            J._installer_arret_externe(); os.kill(os.getpid(), signal.SIGTERM); time.sleep(0.05)
            self.assertTrue(J._arret_externe.is_set()); self.assertEqual(J._arret_motif, 'SIGTERM')
        finally: signal.signal(signal.SIGTERM, ancien[0]); signal.signal(signal.SIGHUP, ancien[1])

    def test_fin_de_session_windows(self):
        src = inspect.getsource(F)
        self.assertIn('0x0016', src); self.assertIn('def _event_endsession', src)                         # WM_ENDSESSION : le processus est arrete juste apres, on ecrit tout de suite
        i = src.index('def _event_endsession'); self.assertIn('self.on_close()', src[i:i + 400])

    def test_les_champs_existent_a_la_creation(self):
        src = inspect.getsource(F.Jeu.__init__)
        for nom in ('_auto_faite', '_arret_externe', '_arret_fini', '_arret_motif'): self.assertIn(nom, src)
        self.assertLess(src.index('self._auto_faite'), src.index('self._pret = True'))                       # avant que la fermeture soit possible
        self.assertLess(src.index('self._pret = True'), src.index('self._installer_arret_externe()'))


# ---------------------------------------------------------------------------------------------------------------------------------- 3. le vrai moteur
def md5(chemin):
    with open(chemin, 'rb') as f: return hashlib.md5(f.read()).hexdigest()


@unittest.skipUnless(APK and SAVES, 'moteur reel : --apk et --saves (ou DQ_APK et DQ_SAVES)')
class MoteurReel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import etats as ET
        cls.ET = ET; cls.ecr = tempfile.mkdtemp(prefix='sv_fermeture_'); mo = cls.mo = MO.Moteur(APK, SAVES, cls.ecr); cls.c = mo.core
        mo.charger_sauvegarde(1)
        for _ in range(200): mo.step(0, 0)
        cls.partie0 = mo.etat.partie; cls.carte0 = mo.etat.carte

    def pas(self, n=1, p=0, d=0):
        for _ in range(n): self.mo.step(p, d); self.mo.ui.degats = []; p = d = 0

    def touche(self, pad):
        port = self.mo.menu_actif(); self.assertIsNotNone(port, 'aucun menu du moteur n\'attend de touche')
        self.mo.envoyer_menu(port, 1, -1, pad); self.pas(1); self.mo.envoyer_menu(port, 1, -1, 0); self.pas(1); self.pas(8)

    def statut(self):
        """Masque des banques valides (getCatalogStatus : bit 0 a 2 les journaux, 3 la suspension, 4 la sauvegarde automatique), apres relecture des fichiers (getCatalogView)."""
        self.c.call(self.c.export('_ZN7profile8SaveLoad14getCatalogViewEv')); return self.c.call(self.c.export('_ZN7profile8SaveLoad16getCatalogStatusEv')) & 0xffffffff

    def test_1_la_partie_est_en_cours(self):
        self.assertIn(self.partie0, (MO.PARTIE_VILLE, MO.PARTIE_CHAMP)); self.assertTrue(self.mo.sauvegarde_auto_possible())

    def test_2_autosave_ecrit_data5_et_le_moteur_la_relit(self):
        f5 = os.path.join(self.ecr, 'data5.dat'); self.assertFalse(os.path.exists(f5))
        self.assertEqual(self.mo.sauvegarde_auto(), 1)
        self.assertTrue(os.path.isfile(f5)); self.assertEqual(os.path.getsize(f5), 0x3c00)                  # la banque 4, dans le dossier d'ecriture (jamais dans les originaux)
        self.assertTrue(os.path.isfile(os.path.join(self.ecr, 'data9.dat')))
        self.assertTrue(self.statut() & 0x10)                                                              # la cellule « Sauvegarde automatique » du menu de depart existe
        origine = os.path.join(SAVES, 'data5.dat')
        if os.path.isfile(origine): self.assertNotEqual(md5(f5), md5(origine))                              # (ce n'est pas la sauvegarde automatique de l'echantillon : c'est la partie en cours)
        # une autre partie en cours (journal 2 : une autre carte), puis la sauvegarde automatique relue : on retrouve la partie fermee
        self.mo.charger_sauvegarde(2); self.pas(200); autre = self.mo.etat.carte
        self.assertNotEqual(autre, self.carte0, 'le journal 2 devrait etre ailleurs que le journal 1')
        self.assertTrue(self.mo.charger_sauvegarde(5)); self.pas(200)
        self.assertEqual(self.mo.etat.carte, self.carte0); self.assertEqual(self.mo.etat.partie, self.partie0)

    def test_3_deux_fermetures_donnent_le_meme_fichier(self):
        self.mo.charger_sauvegarde(1); self.pas(200)
        self.assertEqual(self.mo.sauvegarde_auto(), 1); a = md5(os.path.join(self.ecr, 'data5.dat'))
        self.assertEqual(self.mo.sauvegarde_auto(), 1); self.assertEqual(md5(os.path.join(self.ecr, 'data5.dat')), a)          # (l'image ne change pas sans que la partie bouge : rien d'aleatoire)

    def test_4_retour_au_titre_efface_et_rien_ne_la_remet(self):
        self.mo.charger_sauvegarde(1); self.pas(200); self.mo.retour_titre_etat = None
        self.assertEqual(self.mo.sauvegarde_auto(), 1); f5 = os.path.join(self.ecr, 'data5.dat'); self.assertTrue(self.statut() & 0x10)
        self.assertTrue(self.mo.demander_retour_titre()); self.pas(150)                                      # la boite Oui / Non du jeu
        self.assertEqual(self.mo.retour_titre_etat, 'dialogue')
        self.assertEqual(self.mo.sauvegarde_auto(), 0)                                                       # une question en cours : pas de sauvegarde
        self.touche(PAD_A)                                                                                   # « Oui » : killbank(4) puis le fondu
        self.assertTrue(self.mo.retour_titre_fait)
        apres = md5(f5); self.assertFalse(self.statut() & 0x10)                                              # la banque 4 est effacee
        for n in range(1, 140):
            self.pas(1)
            if n % 10 == 0 or self.mo.etat.carte == MO.CARTE_TITRE: self.assertEqual(self.mo.sauvegarde_auto(), 0, 'image %d (carte %s)' % (n, self.mo.etat.carte))      # fondu puis titre : rien n'est ecrit
            if self.mo.etat.carte == MO.CARTE_TITRE: break
        self.assertEqual(self.mo.etat.carte, MO.CARTE_TITRE); self.assertFalse(self.mo.retour_titre_fait)
        self.assertEqual(self.mo.sauvegarde_auto(), 0); self.assertEqual(md5(f5), apres); self.assertFalse(self.statut() & 0x10)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + REST)
