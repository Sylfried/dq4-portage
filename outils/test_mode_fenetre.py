"""Test des trois modes de la fenetre (fenetre, plein ecran, plein ecran exclusif) : reglage `mode_fenetre` (bornes, migration de l'ancien booleen `plein_ecran`, sauvegarde),
choix du mode d'affichage du moniteur (`fenetre.choisir_mode_ecran`), ordre et grisage des lignes de la page Affichage du menu Echap. Aucune fenetre n'est ouverte.

    python3 outils/test_mode_fenetre.py
"""
import json, os, sys, tempfile, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
import reglages as RG


def charger(contenu):
    f = os.path.join(tempfile.mkdtemp(prefix='rg_test_'), 'reglages.json')
    with open(f, 'w', encoding='utf-8') as fh: json.dump(contenu, fh)
    return RG.Reglages(f), f


class ReglageModeFenetre(unittest.TestCase):
    def test_defaut(self):
        r = RG.Reglages(None)
        self.assertEqual((r['mode_fenetre'], r['mode_fenetre_retour']), (0, 0))
        self.assertNotIn('plein_ecran', r.v)

    def test_migration_de_l_ancien_booleen(self):
        r, _ = charger({'plein_ecran': True}); self.assertEqual(r['mode_fenetre'], 1)          # l'ancien plein ecran = fenetre sans bordure : le mode 1
        r, _ = charger({'plein_ecran': False}); self.assertEqual(r['mode_fenetre'], 0)
        r, _ = charger({'son': False}); self.assertEqual(r['mode_fenetre'], 0)                  # ni l'un ni l'autre : fenetre
        r, _ = charger({'plein_ecran': 'oui'}); self.assertEqual(r['mode_fenetre'], 0)          # valeur absurde
        r, _ = charger({'plein_ecran': True, 'mode_fenetre': 2}); self.assertEqual(r['mode_fenetre'], 2)      # le nouveau reglage prime
        r, _ = charger({'plein_ecran': True, 'mode_fenetre': 0}); self.assertEqual(r['mode_fenetre'], 0)

    def test_bornes(self):
        for brut, attendu in ((0, 0), (1, 1), (2, 2), (3, 0), (-1, 0), (1.5, 0), (2.0, 2), ('x', 0), ('2', 0), (None, 0), ([1], 0), (True, 1), (False, 0), (float('nan'), 0), (float('inf'), 0)):
            r, _ = charger({'mode_fenetre': brut}); self.assertEqual(r['mode_fenetre'], attendu, repr(brut))
            self.assertEqual(RG.mode_fenetre_valide(brut), attendu, repr(brut))

    def test_retour_jamais_exclusif(self):
        for brut, attendu in ((0, 0), (1, 1), (2, 0), (True, 1), ('x', 0), (None, 0)):
            r, _ = charger({'mode_fenetre': 2, 'mode_fenetre_retour': brut}); self.assertEqual(r['mode_fenetre_retour'], attendu, repr(brut))

    def test_aller_retour_et_ancien_booleen_abandonne(self):
        r, f = charger({'plein_ecran': True, 'volume_musique': 0.4})
        r['mode_fenetre'] = 2; r['mode_fenetre_retour'] = 1; r.enregistrer()
        with open(f, encoding='utf-8') as fh: brut = json.load(fh)
        self.assertNotIn('plein_ecran', brut)                                                   # l'ancien booleen n'est plus ecrit
        r2 = RG.Reglages(f)
        self.assertEqual((r2['mode_fenetre'], r2['mode_fenetre_retour'], r2['volume_musique']), (2, 1, 0.4))

    def test_f11_retiree_d_un_ancien_fichier(self):
        r, _ = charger({'touches_v': 4, 'touches': {'infos': ['F11', None], 'carte': ['M', 'F11']}})
        self.assertEqual(r['touches']['infos'], [None, None]); self.assertEqual(r['touches']['carte'], ['M', None])      # (F11 n'est plus une touche d'action)

    def test_f11_non_reattribuable(self):
        self.assertIn('F11', RG.RESERVEES); self.assertIn('ESCAPE', RG.RESERVEES)
        self.assertFalse(any('F11' in ts for ts in RG.TOUCHES_DEF.values()))                    # (F11 n'etait pas une touche du jeu)


class Mode:
    def __init__(self, w, h, depth=32, rate=60, scaling=0): self.width, self.height, self.depth, self.rate, self.scaling = w, h, depth, rate, scaling
    def __repr__(self): return 'Mode(%d x %d, %d bits, %g Hz, scaling %s)' % (self.width, self.height, self.depth, self.rate, self.scaling)


class ChoixModeEcran(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: import fenetre; cls.choisir = staticmethod(fenetre.choisir_mode_ecran)
        except Exception as ex: raise unittest.SkipTest('fenetre.py non importable ici (%r)' % (ex,))

    def test_taille_exacte_meilleure_frequence(self):
        modes = [Mode(1280, 720, rate=60), Mode(1920, 1080, rate=60), Mode(1920, 1080, rate=144), Mode(1920, 1080, rate=120), Mode(2560, 1440, rate=60)]
        m = self.choisir(modes, 1920, 1080); self.assertEqual((m.width, m.height, m.rate), (1920, 1080, 144))
        m = self.choisir(modes, 1280, 720); self.assertEqual((m.width, m.height), (1280, 720))

    def test_profondeur_et_mise_a_l_echelle(self):
        modes = [Mode(1920, 1080, depth=16, rate=240), Mode(1920, 1080, depth=32, rate=60), Mode(1920, 1080, depth=32, rate=144, scaling=2), Mode(1920, 1080, depth=24, rate=75)]
        m = self.choisir(modes, 1920, 1080); self.assertEqual((m.depth, m.rate, m.scaling), (24, 75, 0))      # ni 16 bits, ni mode mis a l'echelle par le pilote : le meilleur des restants
        m = self.choisir([Mode(1920, 1080, depth=32, rate=60), Mode(1920, 1080, depth=24, rate=60)], 1920, 1080); self.assertEqual(m.depth, 32)      # a frequence egale : plus de couleurs

    def test_taille_absente_la_plus_proche_en_16_9(self):
        modes = [Mode(1024, 768), Mode(1280, 720), Mode(1600, 1200), Mode(1920, 1080), Mode(3840, 2160)]
        m = self.choisir(modes, 1600, 900); self.assertEqual((m.width, m.height), (1280, 720))        # 16/9 : 1280 x 720 (ecart 0,52 M pixels) plus pres que 1920 x 1080 (0,63 M) ; pas le 1600 x 1200 (4/3)
        m = self.choisir(modes + [Mode(1366, 768)], 1600, 900); self.assertEqual((m.width, m.height), (1366, 768))      # 1366 x 768 est un 16/9 (a 0,1 % pres) : le plus proche
        m = self.choisir(modes, 2560, 1440); self.assertEqual((m.width, m.height), (1920, 1080))      # 1920 x 1080 (1,4 M) plus pres que 3840 x 2160 (4,6 M)
        m = self.choisir([Mode(800, 600), Mode(1024, 768)], 1920, 1080); self.assertEqual((m.width, m.height), (1024, 768))      # aucun 16/9 : le plus proche tout court

    def test_aucun_mode(self):
        self.assertIsNone(self.choisir([], 1920, 1080)); self.assertIsNone(self.choisir([Mode(0, 0)], 1920, 1080))

    def test_modes_sans_champs_facultatifs(self):
        m = self.choisir([types.SimpleNamespace(width=1280, height=720), types.SimpleNamespace(width=1920, height=1080)], 1920, 1080); self.assertEqual((m.width, m.height), (1920, 1080))


class PageAffichage(unittest.TestCase):
    """Page Affichage du menu Echap : ordre voulu, ligne « Fenêtre » a trois valeurs, « Résolution » grisee en plein ecran sans bordure."""
    ORDRE = ['Fenêtre', 'Résolution', 'Netteté', 'Shader', 'Lissage des textures', 'Effet de vignetage', 'Anticrénelage', 'Suréchantillonnage', 'Luminosité', 'Distance caméra', 'Centrer la caméra sur le joueur', 'Interface']

    @classmethod
    def setUpClass(cls):
        try: import pause
        except Exception as ex: raise unittest.SkipTest('pause.py non importable ici (%r)' % (ex,))
        cls.PA = pause

    def page(self, mode, reg=None):
        reg = reg or RG.Reglages(None); reg['mode_fenetre'] = mode; appels = []
        J = types.SimpleNamespace(reg=reg, mode_fen=mode, mode=4, lissage=True, zoom=1.0, post=types.SimpleNamespace(max_msaa=None), est_plein=mode > 0,
                                  resolutions=lambda: [(1280, 720), (1920, 1080)], resolution_courante=lambda: (1920, 1080),
                                  regler_resolution=lambda v: appels.append(('res', v)), regler_mode_fenetre=lambda v: appels.append(('mode', v)),
                                  regler_mode=lambda v: None, regler_lissage=lambda v: None, regler_distance=lambda v: None)
        return self.PA.Pause(J)._e_affichage(), appels

    def test_ordre(self):
        for mode in (0, 1, 2):
            e, _ = self.page(mode); self.assertEqual([x['l'] for x in e], self.ORDRE, 'mode %d' % mode)

    def test_ligne_fenetre(self):
        for mode, nom in ((0, 'Fenêtré'), (1, 'Plein écran'), (2, 'Plein écran exclusif')):
            e, appels = self.page(mode); f = e[0]
            self.assertEqual((f['t'], f['vals'], f['v']()), ('choix', [0, 1, 2], nom))
            self.assertTrue(f['aide'])
            f['set'](2 - mode); self.assertEqual(appels[-1], ('mode', 2 - mode))             # le choix appelle Jeu.regler_mode_fenetre

    def test_resolution_grisee_en_plein_ecran(self):
        for mode, grisee in ((0, False), (1, True), (2, False)):
            e, appels = self.page(mode); r = e[1]
            self.assertEqual(bool(r['off']), grisee, 'mode %d' % mode)
            self.assertEqual(bool(r['note']()), grisee)                                        # (la note rouge explique pourquoi)
            r['plus'](); self.assertEqual(len(appels), 0 if grisee else 1)                     # grisee : les fleches ne changent rien

    def test_fenetre_et_interface_aux_extremites(self):
        e, _ = self.page(0); self.assertEqual((e[0]['l'], e[-1]['l']), ('Fenêtre', 'Interface'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
