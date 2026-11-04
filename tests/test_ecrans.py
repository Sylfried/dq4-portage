"""Test du moniteur du plein ecran : le plein ecran (F11, Alt + Entree, interrupteur « Plein écran ») se fait toujours sur le moniteur ou se trouve la fenetre. Le choix du moniteur (reglage `ecran_plein`, ligne
« Écran du plein écran ») a ete retire le 03/11/2026 sur demande de Sylfried. Sans fenetre reelle, avec de faux moniteurs (`FauxEcran`) et la vraie logique de ecrans.py et de fenetre.Jeu (liee a une fausse
fenetre qui journalise ses appels).

  1. ecrans.py : liste des moniteurs (principal marque), moniteur de la fenetre (celui de son centre), cible (celui de la fenetre, a defaut le principal) ;
  2. reglages : `ecran_plein` et `sortie_audio` n'existent plus (cles obsoletes, jamais relues) ; les cles de la camera a la souris restent booleennes ;
  3. plein ecran : le moniteur ou se trouve la fenetre sert a chaque entree (meme apres un deplacement), un seul moniteur comme avant ; moniteurs illisibles = repli sans plantage ; echec = fenetre gardee ;
     retour en fenetre ou elle etait (ou centree sur le moniteur du plein ecran) ;
  4. page Affichage : plus de ligne « Écran du plein écran ».

    python3 outils/test_ecrans.py
"""
import json, os, sys, tempfile, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..')); sys.path.insert(0, ICI)
import pyglet
pyglet.options['shadow_window'] = False          # pas de fenetre cachee : le test tourne sans serveur d'affichage
from dq4_pc.fenetre import ecrans as EK
from dq4_pc.persistance import reglages as RG

try:
    from dq4_pc.fenetre import jeu as FE
    from test_mode_fenetre import FausseFenetre, FauxEcran
except Exception as ex:
    FE = None; ERREUR_FE = ex

A = lambda: FauxEcran(0, 0, 1920, 1080, 'Moniteur A', True)
B = lambda: FauxEcran(1920, 0, 2560, 1440, 'Moniteur B')
C = lambda: FauxEcran(-1280, 0, 1280, 1024, '')


class Logique(unittest.TestCase):
    def test_liste_principal_marque(self):
        d = EK.lister([B(), A()])                                                    # (pyglet peut donner le principal en second)
        self.assertEqual([x['principal'] for x in d], [False, True]); self.assertEqual([x['indice'] for x in d], [0, 1])
        self.assertEqual((d[1]['largeur'], d[1]['hauteur'], d[1]['nom']), (1920, 1080, 'Moniteur A')); self.assertEqual(EK.lister([C()])[0]['nom'], '')

    def test_un_seul_principal_meme_si_le_systeme_n_en_annonce_pas(self):
        e1, e2 = FauxEcran(0, 0, 100, 100), FauxEcran(100, 0, 100, 100)
        e1.is_primary = e2.is_primary = False
        d = EK.lister([e2, e1]); self.assertEqual(sum(x['principal'] for x in d), 1); self.assertTrue(d[1]['principal'])          # (a defaut : celui en (0, 0))
        e1.x = 5; self.assertTrue(EK.lister([e2, e1])[0]['principal'])                                           # (a defaut du defaut : le premier)

    def test_ecrans_illisibles(self):
        self.assertEqual(EK.lister(None), []); self.assertEqual(EK.lister([]), [])
        d = EK.lister([object(), A()]); self.assertEqual(len(d), 1); self.assertEqual(d[0]['source'], 1)         # (un ecran illisible est ignore ; `source` retrouve l'objet pyglet)

    def test_cible_est_le_moniteur_de_la_fenetre(self):
        d = EK.lister([A(), B()])
        self.assertEqual(EK.cible(d, 0), 0); self.assertEqual(EK.cible(d, 1), 1)                                   # celui de la fenetre
        self.assertEqual(EK.cible(d, None), 0); self.assertEqual(EK.cible(d, 7), 0); self.assertEqual(EK.cible(d, -1), 0)          # fenetre inconnue : le principal
        self.assertEqual(EK.cible(EK.lister([B(), A()]), None), 1)                                                    # (le principal, meme en second)
        self.assertIsNone(EK.cible([], None)); self.assertIsNone(EK.cible([], 0))

    def test_ecran_de_la_fenetre(self):
        d = EK.lister([A(), B(), C()])
        self.assertEqual(EK.ecran_de((100, 80, 1280, 720), d), 0)
        self.assertEqual(EK.ecran_de((2000, 100, 1280, 720), d), 1)
        self.assertEqual(EK.ecran_de((-1000, 0, 1280, 720), d), 2)
        self.assertEqual(EK.ecran_de((1500, 100, 1280, 720), d), 1)                                              # a cheval : celui du centre (2140, 460)
        self.assertEqual(EK.ecran_de((1500, 100, 600, 300), d), 0)                                               # a cheval, centre (1800, 250) : A
        self.assertEqual(EK.ecran_de((1800, 100, 400, 300), d), 1)                                               # centre (2000, 250) : B
        self.assertIsNone(EK.ecran_de((9000, 9000, 100, 100), d)); self.assertIsNone(EK.ecran_de(None, d)); self.assertIsNone(EK.ecran_de((1, 2), d))

class Reglage(unittest.TestCase):
    def charger(self, contenu):
        f = os.path.join(tempfile.mkdtemp(prefix='rg_ecran_'), 'reglages.json')
        with open(f, 'w', encoding='utf-8') as fh: json.dump(contenu, fh)
        return RG.Reglages(f), f

    def test_choix_du_moniteur_et_de_la_sortie_audio_retires(self):
        for k in ('ecran_plein', 'sortie_audio'):
            self.assertNotIn(k, RG.DEFAUT); self.assertIn(k, RG.CLES_OBSOLETES); self.assertNotIn(k, RG.Reglages(None).v)
        r, f = self.charger({'son': False, 'ecran_plein': {'indice': 1, 'x': 1920, 'y': 0, 'largeur': 2560, 'hauteur': 1440, 'nom': 'B'}, 'sortie_audio': {'id': 'a', 'nom': 'Casque'}})
        for k in ('ecran_plein', 'sortie_audio'): self.assertNotIn(k, r.v, k)          # un ancien fichier de reglages : les deux cles ne sont pas relues
        self.assertFalse(r['son']); r.enregistrer()
        with open(f, encoding='utf-8') as fh: brut = json.load(fh)
        for k in ('ecran_plein', 'sortie_audio'): self.assertNotIn(k, brut, k)          # ... et disparaissent du fichier a la prochaine sauvegarde



def fen(ecrans=None, ecran=0, **kw):
    return FausseFenetre(FE, ecrans=ecrans, ecran=ecran, **kw)


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class PleinEcran(unittest.TestCase):
    def setUp(self):
        os.environ.pop('DQ_SIM_ECHEC', None); os.environ.pop('DQ_BASCULE_SIMPLE', None)
        self.zone = FE.zone_utile; FE.zone_utile = lambda: (1904, 1040)

    def tearDown(self):
        FE.zone_utile = self.zone; os.environ.pop('DQ_SIM_ECHEC', None); os.environ.pop('DQ_BASCULE_SIMPLE', None)

    def deux(self, **kw): return fen([A(), B()], **kw)

    def sets(self, f): return [e for e in f.journal if e.startswith('set_fullscreen')]

    def test_fenetre_sur_le_moniteur_de_pyglet_comme_avant(self):
        f = self.deux(); f.regler_plein_ecran(True)
        self.assertEqual(self.sets(f), ['set_fullscreen(True)']); self.assertEqual((f.width, f.height), (1920, 1080))          # c'est deja le moniteur de pyglet : rien d'impose
        f = fen(); f.regler_plein_ecran(True); self.assertEqual(self.sets(f), ['set_fullscreen(True)'])             # un seul moniteur

    def test_suit_la_fenetre_deplacee_sur_un_autre_moniteur(self):
        f = self.deux(); f._windowed_location = (2000, 100)                                                       # (pyglet croit toujours la fenetre sur A, elle est sur B)
        f.regler_plein_ecran(True); self.assertEqual(self.sets(f), ['set_fullscreen(True,écran 2)']); self.assertEqual((f.width, f.height), (2560, 1440))

    def test_a_chaque_entree_le_moniteur_ou_se_trouve_la_fenetre(self):
        """Fenetre deplacee d'un moniteur a l'autre entre deux passages : chaque entree en plein ecran se fait sur le moniteur ou elle est."""
        f = self.deux()
        for emplacement, attendu in (((2000, 100), 'set_fullscreen(True,écran 2)'), ((100, 80), 'set_fullscreen(True,écran 1)'), ((2300, 200), 'set_fullscreen(True,écran 2)')):
            f.journal.clear(); f._windowed_location = emplacement; f.basculer_plein_ecran()
            self.assertTrue(f.fullscreen); self.assertEqual(self.sets(f), [attendu], emplacement)
            f.basculer_plein_ecran(); self.assertFalse(f.fullscreen)

    def test_fenetre_a_cheval_le_moniteur_du_centre(self):
        f = self.deux(); f._windowed_location = (1500, 100)                                                       # fenetre 1280 x 720 : centre en x = 2140 -> moniteur B
        f.regler_plein_ecran(True); self.assertEqual(self.sets(f), ['set_fullscreen(True,écran 2)'])

    def test_plein_ecran_deja_pris_ne_redemande_rien(self):
        f = self.deux(); f.regler_plein_ecran(True); f.journal.clear(); f.regler_plein_ecran(True); self.assertEqual(f.journal, [])          # (deja en plein ecran : rien ne bouge)

    def test_moniteurs_illisibles_pas_de_plantage(self):
        f = self.deux()
        def casse(): raise OSError('plus de moniteurs')
        f.display = types.SimpleNamespace(get_screens=casse)
        self.assertEqual(f._lire_ecrans(True), ([], [])); self.assertEqual(f._ecran_pour_plein(), (None, None))
        f.regler_plein_ecran(True); self.assertTrue(f.fullscreen); self.assertEqual(self.sets(f), ['set_fullscreen(True)'])                  # pyglet garde son moniteur

    def test_echec_de_l_entree_reste_en_fenetre(self):
        f = self.deux(); f._windowed_location = (2000, 100); os.environ['DQ_SIM_ECHEC'] = '1'; f.regler_plein_ecran(True)
        self.assertFalse(f.fullscreen); self.assertTrue(f._visible); self.assertEqual((f.mode_fen, f.reg['mode_fenetre']), (0, 0))

    def test_retour_en_fenetre_sans_place_memorisee_centre_sur_le_moniteur_du_plein_ecran(self):
        f = self.deux(plein=True, ecran=1); f._noter_zone_plein(); f.regler_plein_ecran(False)                     # (lancee en plein ecran sur B)
        self.assertIn('set_location(%d,%d)' % (1920 + (2560 - 1280) // 2, (1440 - 720) // 2), f.journal)
        f = self.deux(plein=True, ecran=0); f._noter_zone_plein(); f.regler_plein_ecran(False); self.assertIn('set_location(320,180)', f.journal)

    def test_retour_en_fenetre_si_son_moniteur_a_disparu(self):
        f = self.deux(); f.regler_plein_ecran(True)
        f.display = types.SimpleNamespace(get_screens=lambda: [f._ecrans[1]])                                       # (A debranche pendant le plein ecran) : seul B reste
        f._windowed_location = (100, 80)
        f.journal.clear(); f.regler_plein_ecran(False)
        self.assertTrue([e for e in f.journal if e.startswith('set_location')], f.journal)                         # la fenetre serait hors de tous les moniteurs : elle est recentree

    def test_alt_entree_et_f11_passent_par_le_meme_code(self):
        self.assertIs(FE.Jeu.basculer_plein_ecran.__code__.co_names.count('regler_plein_ecran') >= 1, True)
        import inspect; src = inspect.getsource(FE.Jeu._raccourci_fenetre); self.assertIn('basculer_plein_ecran', src)

    def test_signature_set_fullscreen_de_pyglet(self):
        """Le retour en fenetre passe la taille par `width` / `height` : le 2e et le 3e argument positionnels de pyglet sont le moniteur et le mode (l'ancien appel `set_fullscreen(False, largeur, hauteur)` les confondait)."""
        import inspect
        p = list(inspect.signature(pyglet.window.BaseWindow.set_fullscreen).parameters)
        self.assertEqual(p[:6], ['self', 'fullscreen', 'screen', 'mode', 'width', 'height'])
        self.assertNotIn('set_fullscreen(False, *taille)', inspect.getsource(FE.Jeu._mettre_plein))




@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class PageAffichage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dq4_pc.menus import pause; cls.PA = pause

    def test_plus_de_ligne_pour_choisir_le_moniteur(self):
        f = fen([A(), B()]); f.mode = 4; f.zoom = 1.0; f.post = types.SimpleNamespace(max_msaa=None); f.resolutions = lambda: [(1280, 720), (1920, 1080)]; f.resolution_courante = lambda: (1280, 720)
        f.regler_resolution = lambda v: None; f.regler_mode = lambda v: None; f.regler_distance = lambda v: None
        ordre = [x['l'] for x in self.PA.Pause(f)._e_affichage()]
        self.assertEqual(ordre[:2], ['Plein écran', 'Résolution']); self.assertFalse([l for l in ordre if 'cran du plein' in l or 'moniteur' in l.lower()], ordre)
        for nom in ('valeurs_ecran', 'valeur_ecran', 'nom_ecran', 'ecran_modifiable', 'regler_ecran_plein'): self.assertFalse(hasattr(FE.Jeu, nom), nom)          # (et plus rien dans la fenetre pour le choisir)


if __name__ == '__main__':
    unittest.main(verbosity=1)
