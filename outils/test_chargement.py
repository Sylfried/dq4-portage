"""Test de la retenue du dessin pendant un changement de carte (micro-images de mise en place du decor).

Le moteur envoie le decor de la nouvelle carte (paquet 0) une image AVANT sa camera (paquet 10) et les positions de ses personnages (paquet 13) ; le fondu d'entree demarre, lui, a l'image du chargement.
Sans retenue, une image de la scene d'avant (camera) / sans personnages se voyait sous les quelques % d'opacite restants. `Etat.chargement` retient le dessin (noir + fondus seulement) et suspend le fondu d'entree
jusqu'a ce que la scene soit en place, sans changer la duree du fondu.

  1. regles pures (`Etat.appliquer`, `maj_chargement`, `tick_fondu` sur des paquets fabriques) ;
  2. moteur d'origine (si --apk et --saves sont donnes) : teleportations vers des cartes de villes : la retenue dure au plus CHARGEMENT_MAX images, la 1re image montree est complete (camera envoyee, personnages
     places) et le fondu d'entree garde toute sa duree.

    python3 outils/test_chargement.py [--apk "<dossier des APK patches>" --saves "<dossier des sauvegardes>" [--slot 4]]
Les sauvegardes ne sont ouvertes qu'en lecture : le moteur ecrit dans un dossier temporaire.
"""
import argparse, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dq4_pc'))
import pyglet
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'): pyglet.options['headless'] = True; pyglet.options['shadow_window'] = False
import moteur as MO

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
