"""Test de la retenue du dessin pendant un changement de carte (micro-images de mise en place du decor) et de l'absorption des blocages de chargement.

Le moteur envoie le decor de la nouvelle carte (paquet 0) une image AVANT sa camera (paquet 10) et les positions de ses personnages (paquet 13) ; le fondu d'entree demarre, lui, a l'image du chargement.
Sans retenue, une image de la scene d'avant (camera) / sans personnages se voyait sous les quelques % d'opacite restants. `Etat.chargement` retient le dessin (noir + fondus seulement) et suspend le fondu d'entree
jusqu'a ce que la scene soit en place, sans changer la duree du fondu.

  1. regles pures (`Etat.appliquer`, `maj_chargement`, `tick_fondu` sur des paquets fabriques) ;
  2. absorption des blocages (`Jeu._absorber_blocage`, faux objet) ;
  3. Windows : transitions du gestionnaire de fenetres (`transitions_dwm`, systeme simule) ;
  4. moteur d'origine (si --apk et --saves sont donnes) : teleportations vers des cartes de villes : la retenue dure au plus CHARGEMENT_MAX images, la 1re image montree est complete (camera envoyee, personnages
     places) et le fondu d'entree garde toute sa duree.

    python3 outils/test_chargement.py [--apk "<dossier des APK patches>" --saves "<dossier des sauvegardes>" [--slot 4]]
Les sauvegardes ne sont ouvertes qu'en lecture : le moteur ecrit dans un dossier temporaire.
"""
import argparse, os, sys, tempfile, time, types, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
from dq4_pc.noyau import moteur as MO
from dq4_pc.fenetre import jeu as F

ARGS = None
SORTIE, ENTREE = 0x1000, 0                       # bit 12 du paquet 9 : fondu vers la couleur (sortie) ; sinon entree


def pas(e, paquets=()):
    """Un pas du moteur vu de l'etat (Moteur.step) : image, paquets, fin de la retenue, fondus."""
    e.image += 1; e.appliquer(list(paquets), lambda: 'carte_b'); e.maj_chargement(); e.tick_fondu()


def charge(duree=10, camera=True):
    """Paquets d'un chargement de carte : decor, fondu d'entree, un personnage cree (sa position arrive a l'image suivante)."""
    p = [(0, [], []), (9, [ENTREE | duree], []), (12, [0, 5], [])]
    if camera: p.append((10, [3], [0.0, 10.0, -20.0, 0.0, 0.0, 0.0]))
    return p


def etat_couvert(duree=10):
    """Etat apres un fondu au noir termine (ecran couvert), sur une carte quelconque."""
    e = MO.Etat(); e.carte = 'carte_a'
    pas(e, [(9, [SORTIE | duree], [])])
    for _ in range(duree + 2): pas(e)
    assert e.fondu['a'] == 1.0 and e.fondu['n'] == 0
    return e


class Regles(unittest.TestCase):
    def setUp(self):
        self.vitesse = MO.Etat.vitesse_fondu; MO.Etat.vitesse_fondu = 1.0

    def tearDown(self): MO.Etat.vitesse_fondu = self.vitesse

    def test_retenue_jusqu_a_la_scene_complete(self):
        e = etat_couvert(); d = 10
        pas(e, charge(d, camera=False))
        self.assertIsNotNone(e.chargement, 'ecran couvert + chargement : dessin retenu')
        self.assertEqual((e.fondu['a'], e.fondu['n']), (1.0, d), 'le fondu d\'entree attend (il n\'a pas bouge)')
        pas(e, [(10, [3], [0.0, 10.0, -20.0, 0.0, 0.0, 0.0])])
        self.assertIsNotNone(e.chargement, 'la camera est la, mais le personnage cree n\'est pas place')
        pas(e, [(13, [0x2000], [1.0, 0.0, 2.0])])
        self.assertIsNone(e.chargement, 'camera recue, personnage place : scene en place')
        self.assertAlmostEqual(e.fondu['a'], 1.0 - 1.0 / d, 6, 'le fondu d\'entree demarre a cette image')

    def test_la_duree_du_fondu_ne_change_pas(self):
        d = 12; e = etat_couvert(d)
        pas(e, charge(d)); attente = 0
        while e.chargement is not None: attente += 1; pas(e, [(13, [0x2000], [1.0, 0.0, 2.0])] if attente == 1 else [])
        n = 1                                                          # (l'image qui leve la retenue fait deja le 1er pas du fondu)
        while e.fondu['n'] >= 1: pas(e); n += 1
        self.assertEqual(n, d, 'le fondu d\'entree du jeu garde ses %d images apres la retenue' % d)
        self.assertEqual(e.fondu['a'], 0.0)

    def test_camera_et_personnages_dans_les_memes_paquets(self):
        e = etat_couvert()
        pas(e, charge() + [(13, [0x2000], [1.0, 0.0, 2.0])])
        self.assertIsNotNone(e.chargement, 'au moins une image de retenue (CHARGEMENT_MIN)')
        pas(e)
        self.assertIsNone(e.chargement)

    def test_garde_fou(self):
        e = etat_couvert(); pas(e, charge(camera=False)); n = 0
        while e.chargement is not None and n < 50: pas(e); n += 1
        self.assertIsNone(e.chargement, 'la retenue ne bloque jamais')
        self.assertLessEqual(n, MO.CHARGEMENT_MAX, 'images retenues (celle du chargement comprise) au plus CHARGEMENT_MAX')

    def test_personnage_jamais_place(self):
        e = etat_couvert(); pas(e, charge()); n = 0
        while e.chargement is not None and n < 50: pas(e); n += 1
        self.assertLessEqual(n, MO.CHARGEMENT_PLACEMENT, 'attente des positions bornee a %d images' % MO.CHARGEMENT_PLACEMENT)

    def test_personnage_cache_pas_attendu(self):
        e = etat_couvert(); pas(e, charge() + [(14, [0, 0], [])]); pas(e)
        self.assertIsNone(e.chargement, 'un personnage cache n\'a pas besoin de position')

    def test_ecran_pas_couvert(self):
        e = MO.Etat(); e.carte = 'carte_a'
        pas(e, [(0, [], [])])
        self.assertIsNone(e.chargement, 'sans fondu, comportement d\'origine')
        e = MO.Etat(); pas(e, [(9, [SORTIE | 10], [])]); pas(e); pas(e)
        self.assertLess(e.fondu['a'], 0.9)
        pas(e, [(0, [], [])])
        self.assertIsNone(e.chargement, 'fondu au noir en cours mais pas encore couvrant')

    def test_fondu_d_entree_immediat_sans_fondu_avant(self):
        e = MO.Etat(); pas(e, [(0, [], []), (9, [ENTREE | 1], [])])
        self.assertIsNone(e.chargement, 'fondu d\'une image : rien a retenir (l\'ecran n\'est pas couvert)')

    def test_fondu_d_entree_avec_le_chargement(self):
        e = MO.Etat(); pas(e, [(0, [], []), (9, [ENTREE | 10], [])])
        self.assertIsNotNone(e.chargement, 'le fondu d\'entree repart de l\'opacite 1 : l\'ecran est couvert')

    def test_carte_du_monde_attend_ses_tuiles(self):
        e = etat_couvert(); e.partie = MO.PARTIE_CHAMP; e.champ = None
        pas(e, charge()); pas(e, [(13, [0x2000], [1.0, 0.0, 2.0])])
        self.assertIsNotNone(e.chargement, 'carte du monde : on attend les tuiles (paquet 28)')
        e.champ = {'x0': 0, 'y0': 0, 'cols': 1, 'tuiles': [0], 'cam': None}; pas(e)
        self.assertIsNone(e.chargement)

    def test_deux_chargements_de_suite(self):
        e = etat_couvert(); pas(e, charge()); pas(e, [(0, [], []), (9, [ENTREE | 10], [])])
        self.assertIsNotNone(e.chargement, 'mort puis eglise : la retenue repart avec le nouveau chargement')
        self.assertEqual(e.chargement['n'], 0)
        for _ in range(MO.CHARGEMENT_MAX + 1): pas(e)
        self.assertIsNone(e.chargement)

    def test_etat_charge_d_une_ancienne_sauvegarde(self):
        e = MO.Etat(); d = dict(e.__dict__); d.pop('chargement')
        e2 = MO.Etat.__new__(MO.Etat); e2.__setstate__(d)
        self.assertIsNone(e2.chargement)


class Absorption(unittest.TestCase):
    def faux(self, cartes=1):
        return types.SimpleNamespace(moteur=types.SimpleNamespace(etat=types.SimpleNamespace(cartes_chargees=cartes)), t_boucle=5.0)

    def test_image_longue_apres_un_chargement(self):
        j = self.faux()
        F.Jeu._absorber_blocage(j, time.perf_counter() - 0.3)
        self.assertIsNone(j.t_boucle, 'un blocage de 300 ms n\'est pas rattrape par le moteur')

    def test_image_normale(self):
        j = self.faux()
        for _ in range(5): F.Jeu._absorber_blocage(j, time.perf_counter() - 0.004)
        self.assertEqual(j.t_boucle, 5.0)

    def test_machine_lente(self):
        j = self.faux()
        for _ in range(3): F.Jeu._absorber_blocage(j, time.perf_counter() - 0.10)
        self.assertEqual(j.t_boucle, 5.0, 'des images de 100 ms (machine lente) ne sont pas des blocages : le jeu ne se fige pas')

    def test_seulement_les_premieres_images_d_une_carte(self):
        j = self.faux()
        for _ in range(3): F.Jeu._absorber_blocage(j, time.perf_counter())
        F.Jeu._absorber_blocage(j, time.perf_counter() - 0.3)
        self.assertEqual(j.t_boucle, 5.0, 'plus de 3 images apres le chargement : un ralentissement ordinaire reste soumis au rattrapage normal')
        j.moteur.etat.cartes_chargees = 2
        F.Jeu._absorber_blocage(j, time.perf_counter() - 0.3)
        self.assertIsNone(j.t_boucle, 'nouvelle carte : le compte repart')


class Interpolation(unittest.TestCase):
    """L'image qui leve la retenue d'un chargement n'est pas interpolee depuis l'etat de la retenue (camera d'avant) : Jeu._interpoler sur un faux objet."""
    def faux(self, retenu_avant, retenu_apres):
        e = types.SimpleNamespace(partie=0xc, carte='x', chargement={'n': 1} if retenu_apres else None, sprites={}, cam_pos=(0.0, 10.0, -20.0), cam_cible=(0.0, 0.0, 0.0), champ=None)
        pr = dict(cle=(0xc, 'x'), ret=retenu_avant, sp={}, cam_pos=(0.5, 10.0, -20.0), cam_cible=(0.0, 0.0, 0.0), champ=None)
        j = types.SimpleNamespace(prec=pr, alpha=0.5, moteur=types.SimpleNamespace(etat=e)); j._interpoler_camera = types.MethodType(F.Jeu._interpoler_camera, j); return j

    def test_pas_d_interpolation_a_la_levee(self):
        j = self.faux(True, False)
        self.assertEqual(F.Jeu._interpoler(j), [])
        self.assertEqual(j.moteur.etat.cam_pos, (0.0, 10.0, -20.0))

    def test_interpolation_ordinaire(self):
        j = self.faux(False, False)
        sauve = F.Jeu._interpoler(j)
        self.assertTrue(sauve); self.assertAlmostEqual(j.moteur.etat.cam_pos[0], 0.25, places=3, msg='camera a mi-chemin entre les deux pas')


class DWM(unittest.TestCase):
    """Windows : animation d'ouverture de la fenetre coupee pendant le lancement (fenetre.transitions_dwm). Ici sans Windows : le systeme est simule."""
    def avec_dwm(self, dwm, fenetre):
        import ctypes
        ancien = sys.platform; sys.platform = 'win32'; ctypes.windll = types.SimpleNamespace(dwmapi=dwm)
        try: return F.transitions_dwm(fenetre, False), F.transitions_dwm(fenetre, True)
        finally: sys.platform = ancien; del ctypes.windll

    def test_hors_windows_rien_ne_change(self):
        self.assertFalse(F.transitions_dwm(types.SimpleNamespace(_hwnd=123), False))

    def test_appel_windows(self):
        appels = []
        class Dwm:
            def DwmSetWindowAttribute(self, h, attr, ref, taille): appels.append((h.value, attr, ref._obj.value, taille)); return 0
        self.assertEqual(self.avec_dwm(Dwm(), types.SimpleNamespace(_hwnd=0x1234)), (True, True))
        self.assertEqual(appels, [(0x1234, 3, 1, 4), (0x1234, 3, 0, 4)], 'DWMWA_TRANSITIONS_FORCEDISABLED : 1 pour couper, 0 pour remettre')

    def test_erreurs_sans_suite(self):
        class Casse:
            def DwmSetWindowAttribute(self, *a): raise OSError('dwmapi absent')
        class Refuse:
            def DwmSetWindowAttribute(self, *a): return 0x80070057
        self.assertEqual(self.avec_dwm(Casse(), types.SimpleNamespace(_hwnd=1)), (False, False))
        self.assertEqual(self.avec_dwm(Refuse(), types.SimpleNamespace(_hwnd=1)), (False, False))
        self.assertEqual(self.avec_dwm(Refuse(), types.SimpleNamespace()), (False, False), 'pas de poignee de fenetre')


@unittest.skipIf(ARGS is None and '--apk' not in sys.argv, 'moteur d\'origine : --apk et --saves requis')
class Moteur(unittest.TestCase):
    def test_teleportations(self):
        mo = MO.Moteur(ARGS.apk, ARGS.saves, tempfile.mkdtemp(prefix='sv_test_chg_'))
        mo.charger_sauvegarde(ARGS.slot)
        for _ in range(100): mo.step(0, 0)
        MO.Etat.vitesse_fondu = 1.0; vus = 0
        for nom in ('caf1', 'cbf1', 'cdf1', 'mak1f1', 'maout'):
            avant = mo.etat.cartes_chargees; cam0 = mo.etat.cam_pos
            mo.demarrer_ville(nom); k = None; trace = []
            for i in range(40):
                mo.step(0, 0); e = mo.etat
                if k is None and e.cartes_chargees > avant: k = i
                if k is not None: trace.append((i - k, e.chargement is not None, e.cam_pos, [s['pos'] for s in e.sprites.values() if s.get('vis', True)], e.fondu['a'], e.fondu['n']))
            self.assertIsNotNone(k, nom + ' : carte chargee')
            vus += 1
            retenues = [t for t in trace if t[1]]
            self.assertTrue(retenues, nom + ' : le chargement a ete retenu')
            self.assertLessEqual(len(retenues), MO.CHARGEMENT_MAX, nom)
            premiere = next(t for t in trace if not t[1])
            self.assertIsNotNone(premiere[2], nom + ' : camera envoyee a la 1re image montree')
            if vus == 1: self.assertNotEqual(premiere[2], cam0, nom + ' : ce n\'est plus la camera de la carte d\'avant (carte du monde ; deux villes peuvent avoir la meme camera de depart)')
            self.assertTrue(all(p is not None for p in premiere[3]), nom + ' : personnages places a la 1re image montree')
            for t in retenues: self.assertEqual(t[4], 1.0, nom + ' : ecran couvert pendant la retenue')
        self.assertEqual(vus, 5)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apk'); ap.add_argument('--saves'); ap.add_argument('--slot', type=int, default=4)
    ARGS, reste = ap.parse_known_args()
    if not (ARGS.apk and ARGS.saves): ARGS = None
    unittest.main(argv=[sys.argv[0]] + reste, verbosity=2)
