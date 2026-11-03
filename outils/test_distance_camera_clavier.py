"""Test des touches « Caméra (Rapprocher) » et « Caméra (Éloigner) » (#146) : la distance de la camera se regle aussi au clavier, comme avec le curseur « Distance camera » du menu et la molette.

    python3 outils/test_distance_camera_clavier.py

1. Reglages : deux actions reattribuables (cam_pres, cam_loin), touches par defaut libres (pave numerique + / -, E / W), un ancien fichier les recoit sans rien changer d'autre.
2. Menu Commandes : deux lignes dans la section « Camera au clavier », a la suite des quatre fleches.
3. Logique de la fenetre (vraies methodes de fenetre.Jeu sur un faux jeu) : un pas de 5 % a l'appui, repetition apres 0,4 s, bornes 50 - 200 %, arrondi au pas de 5 %, rien dans un menu, un message ou un combat,
   les deux touches ensemble ne font rien.
"""
import json, os, sys, tempfile, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc'))
import pyglet
pyglet.options['shadow_window'] = False
import reglages as RG
import pause as PA

try:
    import fenetre as FE
except Exception as ex:          # fenetre.py a besoin de pyglet, numpy, unicorn... (l'import seul suffit, aucune fenetre n'est creee)
    FE = None; ERREUR_FE = ex

NOUVELLES = ('cam_pres', 'cam_loin')


def charger(contenu):
    f = os.path.join(tempfile.mkdtemp(prefix='rg_dist_'), 'reglages.json')
    with open(f, 'w', encoding='utf-8') as fh: json.dump(contenu, fh)
    return RG.Reglages(f)


class Reglages(unittest.TestCase):
    def test_actions_et_libelles(self):
        libs = dict(RG.ACTIONS)
        self.assertEqual(libs['cam_pres'], 'Caméra (Rapprocher)'); self.assertEqual(libs['cam_loin'], 'Caméra (Éloigner)')
        self.assertEqual(set(libs), set(RG.TOUCHES_DEF))                                                 # (chaque action a un libelle et inversement)
        ls = [a for a, _ in RG.ACTIONS]; self.assertEqual(ls[ls.index('cam_droite') + 1:ls.index('cam_droite') + 3], list(NOUVELLES))

    def test_touches_par_defaut_libres(self):
        self.assertEqual(RG.TOUCHES_DEF['cam_pres'], ['NUM_ADD', 'E']); self.assertEqual(RG.TOUCHES_DEF['cam_loin'], ['NUM_SUBTRACT', 'W'])
        for a, ts in RG.TOUCHES_DEF.items():
            if a in NOUVELLES: continue
            for n in ('NUM_ADD', 'NUM_SUBTRACT', 'E', 'W'): self.assertNotIn(n, ts, (a, n))               # aucun conflit avec les touches existantes
        for n in ('NUM_ADD', 'NUM_SUBTRACT', 'E', 'W'):
            self.assertNotIn(n, RG.RESERVEES); self.assertIsNotNone(RG.symbole(n), n)                    # (des touches que pyglet connait)
        r = RG.Reglages(None)
        for a in NOUVELLES:
            for n in r['touches'][a]: self.assertEqual(r.action_de(RG.symbole(n)), a)
        self.assertEqual((RG.nom_touche('NUM_ADD'), RG.nom_touche('NUM_SUBTRACT'), RG.nom_touche('NUM_1')), ('Pavé +', 'Pavé -', 'Pavé 1'))     # (noms lisibles pour le menu)

    def test_ancien_fichier_prend_les_touches_par_defaut(self):
        r = charger({'touches_v': RG.DEFAUT['touches_v'], 'touches': {'carte': ['M', None]}})
        self.assertEqual(r['touches']['cam_pres'], ['NUM_ADD', 'E']); self.assertEqual(r['touches']['cam_loin'], ['NUM_SUBTRACT', 'W']); self.assertEqual(r['touches']['carte'], ['M', None])

    def test_touche_deja_prise_par_le_joueur_est_gardee(self):
        r = charger({'touches_v': RG.DEFAUT['touches_v'], 'touches': {'carte': ['E', None], 'historique': ['NUM_SUBTRACT', 'W']}})
        self.assertEqual(r['touches']['cam_pres'], ['NUM_ADD', None]); self.assertEqual(r['touches']['cam_loin'], [None, None])      # la nouvelle action perd la touche prise, pas l'autre
        self.assertEqual(r['touches']['carte'], ['E', None]); self.assertEqual(r['touches']['historique'], ['NUM_SUBTRACT', 'W'])

    def test_reattribution(self):
        r = RG.Reglages(None); avait = r.lier('cam_pres', 0, RG.symbole('P')); self.assertIsNone(avait); self.assertEqual(r['touches']['cam_pres'], ['P', 'E'])
        avait = r.lier('cam_pres', 1, RG.symbole('NUM_SUBTRACT')); self.assertEqual(avait, 'cam_loin'); self.assertEqual(r['touches']['cam_loin'], [None, 'W'])        # (une touche ne sert qu'a une action)


class FauxJeu:
    def noms_fenetres(self): return {}
    def __init__(self):
        self.reg = RG.Reglages(os.path.join(tempfile.mkdtemp(prefix='pause_dist_'), 'reglages.json'))
        self.son = types.SimpleNamespace(actif=True, ecoute=False); self.args = types.SimpleNamespace(cache='/inexistant'); self.width, self.height = 1280, 720; self.souris = None
    def regler_son(self, oui): pass
    def appliquer_mixage(self): pass
    def apercu_son(self, cat): pass
    def regler_fondu(self, v): pass
    def appliquer_texte(self): pass
    def appliquer_jeu(self): pass
    def regler_vitesse_combat(self, v): pass
    def pause_jeu(self, oui): pass


class MenuCommandes(unittest.TestCase):
    def test_deux_lignes_dans_camera_au_clavier(self):
        p = PA.Pause(FauxJeu()); p.ouvert = True; p.pile = ['commandes']; e = p._entrees(); ls = [x['l'] for x in e]
        i = ls.index('Caméra au clavier'); self.assertEqual(e[i]['t'], 'sep')
        self.assertEqual(ls[i + 1:i + 7], ['Caméra (Haut)', 'Caméra (Bas)', 'Caméra (Gauche)', 'Caméra (Droite)', 'Caméra (Rapprocher)', 'Caméra (Éloigner)'])
        self.assertEqual(ls[i + 7], 'Caméra à la souris')                                                   # (la section suivante)
        for lib, act, v in (('Caméra (Rapprocher)', 'cam_pres', ['Pavé +', 'E']), ('Caméra (Éloigner)', 'cam_loin', ['Pavé -', 'W'])):
            x = next(t for t in e if t['l'] == lib); self.assertEqual((x['t'], x['act'], x['v']), ('touche', act, v))
            self.assertIn('Distance caméra', x['aide']); self.assertIn('50 à 200 %', x['aide'])

    def test_vitesse_de_transition_inchangee_ici(self):
        p = PA.Pause(FauxJeu()); p.ouvert = True; p.pile = ['commandes']; self.assertIn('Vitesse de transition', [x['l'] for x in p._entrees()])         # (son retrait est #101, a part)


class Faux:
    """Un `Jeu` minimal : les vraies methodes de fenetre.Jeu liees a cet objet, sur un etat factice (terrain libre d'une ville, camera a 100 %)."""
    def __init__(self, partie=None, distance=100):
        MO = FE.MO
        self.moteur = types.SimpleNamespace(etat=types.SimpleNamespace(partie=MO.PARTIE_VILLE if partie is None else partie, effet=None), msg_visible=False, menu_actif=lambda: None)
        self.pause = types.SimpleNamespace(ouvert=False); self.licence = None; self.sauv = None; self.titre = None; self._saisie_nom_en_cours = lambda: False; self.carte_ouverte = False
        self.reg = RG.Reglages(None); self.reg['distance_camera'] = distance; self.zoom = 100.0 / distance; self.fixe_test = True; self._pret = True; self.tenues = set()
        self._dist_sens = 0; self._dist_tenue = 0.0; self._dist_rep = 0.0; self._t_dist = None
        for nom in ('_zoom_possible', 'regler_zoom', 'regler_distance', 'distance_au_pas', '_maj_distance_clavier'):
            setattr(self, nom, types.MethodType(getattr(FE.Jeu, nom), self))
        self._zoom_valide = FE.Jeu._zoom_valide; self._tenue = lambda a: a in self.tenues

    @property
    def distance(self): return round(100.0 / self.zoom)

    def images(self, n, *touches):
        self.tenues = set(touches)
        for _ in range(n): self._maj_distance_clavier()


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class DansLeJeu(unittest.TestCase):
    def test_un_pas_a_l_appui(self):
        j = Faux(); j.images(1, 'cam_loin'); self.assertEqual((j.distance, j.reg['distance_camera']), (105, 105))                  # éloigner : 100 -> 105 %
        j = Faux(); j.images(1, 'cam_pres'); self.assertEqual((j.distance, j.reg['distance_camera']), (95, 95))                    # rapprocher : 100 -> 95 %
        j = Faux(); j.images(1, 'cam_pres'); self.assertAlmostEqual(j.zoom, 100.0 / 95)                                           # (meme valeur que le curseur : regler_distance)

    def test_un_appui_court_ne_fait_qu_un_pas(self):
        j = Faux(); j.images(1, 'cam_loin'); j.images(1); j.images(1, 'cam_loin'); j.images(1); self.assertEqual(j.distance, 110)       # deux appuis courts = deux pas
        j = Faux(); j.images(20, 'cam_loin'); self.assertEqual(j.distance, 105)                                                   # 20 images (0,33 s) maintenues : toujours un seul pas (avant le delai de 0,4 s)

    def test_maintenue_repete_apres_le_delai(self):
        j = Faux(); j.images(24, 'cam_loin'); self.assertEqual(j.distance, 105)                                                   # 0,4 s : delai atteint a l'image 25
        j.images(1, 'cam_loin'); self.assertEqual(j.distance, 105)
        j = Faux(); j.images(60, 'cam_loin'); self.assertGreater(j.distance, 110)                                                 # 1 s maintenue : la repetition a commence

    def test_cadence_de_la_repetition(self):
        j = Faux(); j.images(1, 'cam_loin'); d0 = j.distance; j.images(60, 'cam_loin')                                            # 1 s de plus
        pas = (j.distance - d0) // 5; self.assertGreaterEqual(pas, 6); self.assertLessEqual(pas, 8)                              # ~ (1 - 0,4) / 0,08 = 7,5 pas
        self.assertEqual((j.distance - d0) % 5, 0)

    def test_bornes_50_et_200(self):
        j = Faux(); j.images(1000, 'cam_loin'); self.assertEqual(j.distance, 200); self.assertEqual(j.reg['distance_camera'], 200)
        j = Faux(); j.images(1000, 'cam_pres'); self.assertEqual(j.distance, 50); self.assertEqual(j.reg['distance_camera'], 50)
        j = Faux(distance=200); j.images(1, 'cam_loin'); self.assertEqual(j.distance, 200)
        j = Faux(distance=50); j.images(1, 'cam_pres'); self.assertEqual(j.distance, 50)

    def test_arrondi_au_pas_de_5(self):
        for dist, loin, pres in ((91, 95, 90), (96, 100, 95), (100, 105, 95), (53, 55, 50), (199, 200, 195), (51, 55, 50), (50, 55, 50), (200, 200, 195)):
            j = Faux(distance=dist); self.assertEqual(j.distance_au_pas(1), loin, (dist, 'loin')); self.assertEqual(j.distance_au_pas(-1), pres, (dist, 'pres'))

    def test_les_deux_touches_ensemble_ne_font_rien(self):
        j = Faux(); j.images(60, 'cam_loin', 'cam_pres'); self.assertEqual(j.distance, 100)
        j = Faux(); j.images(1, 'cam_loin'); j.images(30, 'cam_loin', 'cam_pres'); self.assertEqual(j.distance, 105)               # (ni pas, ni repetition tant que les deux sont tenues)

    def test_changer_de_sens_donne_un_pas_aussitot(self):
        j = Faux(); j.images(1, 'cam_loin'); j.images(1, 'cam_pres'); self.assertEqual(j.distance, 100)
        j.images(1); j.images(1, 'cam_pres'); self.assertEqual(j.distance, 95)

    def test_rien_hors_du_terrain(self):
        MO = FE.MO
        j = Faux(); j.pause.ouvert = True; j.images(5, 'cam_loin'); self.assertEqual(j.distance, 100)                               # menu Echap
        j = Faux(); j.moteur.msg_visible = True; j.images(5, 'cam_loin'); self.assertEqual(j.distance, 100)                         # message
        j = Faux(); j.moteur.menu_actif = lambda: object(); j.images(5, 'cam_loin'); self.assertEqual(j.distance, 100)              # menu du jeu
        j = Faux(); j.carte_ouverte = True; j.images(5, 'cam_loin'); self.assertEqual(j.distance, 100)                              # carte ouverte
        j = Faux(partie=MO.PARTIE_COMBAT); j.images(5, 'cam_loin'); self.assertEqual(j.distance, 100)                               # combat
        j = Faux(); j.images(5, 'cam_loin'); self.assertEqual(j.distance, 105)                                                      # (le terrain libre, lui, agit)

    def test_la_carte_du_monde_aussi(self):
        j = Faux(partie=FE.MO.PARTIE_CHAMP); j.images(1, 'cam_loin'); self.assertEqual(j.distance, 105)                             # comme la molette : villes, donjons, tours et carte du monde

    def test_la_touche_relachee_remet_le_delai_a_zero(self):
        j = Faux(); j.images(40, 'cam_loin'); d = j.distance; j.images(3); j.images(1, 'cam_loin'); self.assertEqual(j.distance, d + 5)         # nouvel appui = un pas, sans repetition immediate
        self.assertEqual((j._dist_sens, j._dist_tenue), (1, 0.0))


if __name__ == '__main__':
    unittest.main(verbosity=1)
