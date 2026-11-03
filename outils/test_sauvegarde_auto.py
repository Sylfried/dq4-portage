"""Test de la sauvegarde automatique du jeu (issue #128) : le jeu d'origine n'ecrit AUCUNE sauvegarde automatique en se fermant. Elle est ecrite par le moteur lui-meme, a deux endroits seulement
(`TownPart::initialize` et `FieldPart::initialize` de libdq4core, selon les conditions du jeu : arrivee sur la carte du monde, arrivee dans un donjon...). La visionneuse n'ajoute rien : la fermeture de la fenetre
(croix, Alt + F4, menu Quitter...) enregistre les reglages et l'historique, point. (Le code de fermeture de #124, qui forcait `AutoSave(true)` et replacait le joueur « au pixel pres », est retire.)

    python3 outils/test_sauvegarde_auto.py [--apk <dossier des APK patches> --saves <dossier des sauvegardes>]
(ou DQ_APK et DQ_SAVES ; sans eux seules les parties 1 et 2 tournent). La partie 3 charge le vrai moteur (environ 1 minute) : a lancer par `outils/flux_session/moteur_slot.sh`.

Partie 1 (sans moteur) : plus rien dans Moteur ni dans Jeu qui force une sauvegarde automatique, ou qui surveille la console, les signaux, la fin de session.
Partie 2 (fenetre simulee) : Jeu.on_close ne touche pas au moteur ; le menu Quitter passe par on_close.
Partie 3 (vrai moteur) : l'arrivee en ville n'ecrit pas la banque 4 ; l'arrivee sur la carte du monde l'ecrit (le moteur seul) ; fermer la fenetre n'ecrit rien ; « Revenir a l'ecran titre » l'efface et elle ne revient pas.
"""
import argparse, hashlib, inspect, os, sys, tempfile, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False                     # (pas d'affichage necessaire : on ne dessine rien)
import moteur as MO
import fenetre as F

APK = os.environ.get('DQ_APK'); SAVES = os.environ.get('DQ_SAVES'); REST = sys.argv[1:]
if __name__ == '__main__':
    _ap = argparse.ArgumentParser(); _ap.add_argument('--apk'); _ap.add_argument('--saves'); _a, REST = _ap.parse_known_args()
    APK = _a.apk or APK; SAVES = _a.saves or SAVES
PAD_A = 0x10


# ---------------------------------------------------------------------------------------------------------------------------------- 1. le code
class RienNeForceLaSauvegarde(unittest.TestCase):
    def test_le_moteur_n_a_plus_de_sauvegarde_forcee(self):
        for nom in ('sauvegarde_auto', 'sauvegarde_auto_possible', 'retour_titre_fait'):
            self.assertFalse(hasattr(MO.Moteur, nom), nom)
        self.assertNotIn('_Z8AutoSaveb', inspect.getsource(MO))                                    # AutoSave n'est plus appelee par la visionneuse (le moteur l'appelle seul)
        self.assertNotIn('retour_titre_fait', inspect.getsource(MO))

    def test_la_fenetre_n_a_plus_de_fermeture_speciale(self):
        for nom in ('_sauvegarde_fermeture', '_installer_arret_externe', '_arret_console', '_arret_externe_traiter'):
            self.assertFalse(hasattr(F.Jeu, nom), nom)
        src = inspect.getsource(F)
        for motif in ('_event_endsession', 'SetConsoleCtrlHandler', '_arret_externe', '_arret_motif', '_auto_faite', 'DQ_SAUVEGARDE_FERMETURE', 'sauvegarde_auto'):
            self.assertNotIn(motif, src, motif)

    def test_la_boucle_ne_regarde_plus_les_demandes_des_autres_fils(self):
        self.assertNotIn('_arret', inspect.getsource(F.Jeu._boucle))

    def test_on_close_enregistre_les_reglages_l_historique_et_ferme_le_son(self):
        src = inspect.getsource(F.Jeu.on_close)
        self.assertTrue(src.index('self._pret') < src.index('self.reg.enregistrer()') < src.index('self.son.fermer()'))
        self.assertIn('self.historique.enregistrer(True)', src); self.assertNotIn('moteur', src)

    def test_le_menu_quitter_passe_par_on_close(self):
        src = inspect.getsource(F.Jeu.quitter); self.assertIn('self.on_close()', src); self.assertNotIn('self.close()', src)

    def test_revenir_au_titre_efface_toujours_la_banque_4(self):
        src = inspect.getsource(MO.Moteur.retour_titre); self.assertIn('killbank', src); self.assertIn('startTitle', src)


# ---------------------------------------------------------------------------------------------------------------------------------- 2. la fenetre (simulee)
class MoteurIntouchable:
    """Un moteur qui leve une erreur au moindre acces : la fermeture n'a rien a lui demander."""
    def __getattr__(self, nom): raise AssertionError('la fermeture a touche au moteur : %s' % nom)


class FausseFenetre:
    """Ce que la fermeture lit de Jeu ; la vraie methode on_close lui est liee."""
    def __init__(self, pret=True, moteur=None):
        self._pret = pret; self._ferme = False; self.appels = []; self.moteur = moteur if moteur is not None else MoteurIntouchable()
        self.reg = types.SimpleNamespace(enregistrer=lambda: self.appels.append('reglages'))
        self.historique = types.SimpleNamespace(enregistrer=lambda force=False: self.appels.append('historique'))
        self.son = types.SimpleNamespace(fermer=lambda: self.appels.append('son'))
    def on_close(self):
        # (la derniere ligne de Jeu.on_close est super().on_close() : la fenetre de pyglet, absente ici)
        try: F.Jeu.on_close(self)
        except (TypeError, RuntimeError, AttributeError) as ex:
            if 'super' not in str(ex) and 'argument' not in str(ex) and 'Jeu' not in str(ex): raise


class FermetureSimulee(unittest.TestCase):
    def test_la_fermeture_ne_touche_pas_au_moteur(self):
        J = FausseFenetre(); J.on_close()
        self.assertEqual(J.appels, ['reglages', 'historique', 'son'])                                # tout ce que fait la fermeture ; aucune sauvegarde du jeu

    def test_pendant_les_logos_la_fenetre_se_ferme_sans_rien_ecrire(self):
        J = FausseFenetre(pret=False); J.on_close(); self.assertTrue(J._ferme); self.assertEqual(J.appels, [])


# ---------------------------------------------------------------------------------------------------------------------------------- 3. le vrai moteur
def md5(chemin):
    with open(chemin, 'rb') as f: return hashlib.md5(f.read()).hexdigest()


@unittest.skipUnless(APK and SAVES, 'moteur reel : --apk et --saves (ou DQ_APK et DQ_SAVES)')
class MoteurReel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ecr = tempfile.mkdtemp(prefix='sv_auto_'); cls.mo = MO.Moteur(APK, SAVES, cls.ecr); cls.c = cls.mo.core
        cls.f5 = os.path.join(cls.ecr, 'data5.dat')

    def pas(self, n=1, p=0, d=0):
        for _ in range(n): self.mo.step(p, d); self.mo.ui.degats = []; p = d = 0

    def touche(self, pad):
        port = self.mo.menu_actif(); self.assertIsNotNone(port, 'aucun menu du moteur n\'attend de touche')
        self.mo.envoyer_menu(port, 1, -1, pad); self.pas(1); self.mo.envoyer_menu(port, 1, -1, 0); self.pas(1); self.pas(8)

    def statut(self):
        """Masque des banques valides (getCatalogStatus : bit 0 a 2 les journaux, 3 la suspension, 4 la sauvegarde automatique), apres relecture des fichiers (getCatalogView)."""
        self.c.call(self.c.export('_ZN7profile8SaveLoad14getCatalogViewEv')); return self.c.call(self.c.export('_ZN7profile8SaveLoad16getCatalogStatusEv')) & 0xffffffff

    def charger(self, numero, partie_attendue):
        self.assertTrue(self.mo.charger_sauvegarde(numero)); self.pas(200)
        if self.mo.etat.partie != partie_attendue: self.skipTest('la sauvegarde %d de cet echantillon n\'est pas en partie %d (%d)' % (numero, partie_attendue, self.mo.etat.partie))

    def test_1_arrivee_en_ville_le_moteur_n_ecrit_pas_la_sauvegarde_automatique(self):
        self.assertFalse(os.path.exists(self.f5))
        self.charger(1, MO.PARTIE_VILLE)
        self.assertFalse(os.path.exists(self.f5), 'le moteur ne sauvegarde pas a l\'arrivee dans une ville (TownPart::initialize : AutoSave(false) refuse)')

    def test_2_arrivee_sur_la_carte_du_monde_le_moteur_l_ecrit_seul(self):
        self.charger(4, MO.PARTIE_CHAMP)
        self.assertTrue(os.path.isfile(self.f5), 'FieldPart::initialize appelle AutoSave(false) : la banque 4 est ecrite sans aucun appel de la visionneuse')
        self.assertEqual(os.path.getsize(self.f5), 0x3c00); self.assertTrue(self.statut() & 0x10)         # la cellule « Sauvegarde automatique » du menu de depart existe

    def test_3_fermer_la_fenetre_n_ecrit_rien(self):
        self.charger(4, MO.PARTIE_CHAMP)
        avant = {f: md5(os.path.join(self.ecr, f)) for f in sorted(os.listdir(self.ecr))}
        J = FausseFenetre(moteur=self.mo); J.on_close()
        self.assertEqual(J.appels, ['reglages', 'historique', 'son'])
        apres = {f: md5(os.path.join(self.ecr, f)) for f in sorted(os.listdir(self.ecr))}
        self.assertEqual(avant, apres, 'fermer la fenetre ne doit modifier aucun fichier de sauvegarde')

    def test_4_retour_au_titre_efface_et_rien_ne_la_remet(self):
        self.charger(4, MO.PARTIE_CHAMP); self.mo.retour_titre_etat = None
        self.assertTrue(self.statut() & 0x10)
        self.assertTrue(self.mo.demander_retour_titre()); self.pas(150)                                      # la boite Oui / Non du jeu
        self.assertEqual(self.mo.retour_titre_etat, 'dialogue')
        self.touche(PAD_A)                                                                                   # « Oui » : killbank(4) puis le fondu
        self.assertFalse(self.statut() & 0x10)                                                               # la banque 4 est effacee
        for n in range(1, 140):
            self.pas(1)
            if n % 10 == 0 or self.mo.etat.carte == MO.CARTE_TITRE: self.assertFalse(self.statut() & 0x10, 'image %d (carte %s)' % (n, self.mo.etat.carte))      # fondu puis titre : rien n'est ecrit
            if self.mo.etat.carte == MO.CARTE_TITRE: break
        self.assertEqual(self.mo.etat.carte, MO.CARTE_TITRE); self.assertFalse(self.statut() & 0x10)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + REST)
