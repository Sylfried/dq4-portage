"""Test des touches « Caméra (Rapprocher) » et « Caméra (Éloigner) » (#146) : la distance de la camera se regle au clavier, en continu, comme la molette de la souris (le curseur « Distance camera » du menu Affichage est retire).

    python3 outils/test_distance_camera_clavier.py

1. Reglages : deux actions reattribuables (cam_pres, cam_loin), par defaut Page haut / Page bas ; un fichier de l'avance #153 qui a encore les anciens defauts (pave + / -, E / W) les remplace ; un choix du joueur est garde.
2. Menu : deux lignes dans la section « Camera au clavier », a la suite des quatre fleches (la page Affichage n'a plus de ligne « Distance camera » : voir `test_mode_fenetre.py`).
3. Logique de la fenetre (vraies methodes de fenetre.Jeu sur un faux jeu) : tant que la touche est tenue la distance change EN CONTINU (meme variation a chaque image, aucun a-coup), a la vitesse de rotation de la camera
   (100 % par seconde a vitesse x1) avec les memes reglages (vitesse de camera, accelerateur), bornes 50 - 200 %, rien dans un menu, un message ou un combat.
4. Retour anime a 100 % (#167) : les deux touches ensemble, Ctrl + molette et Ctrl + clic molette (distance_par_defaut) ramenent la distance a 100 % PROGRESSIVEMENT (jamais d'a-coup), a la vitesse de la remise de la
   rotation (5 x l'ecart par seconde, au moins CAM_RECENTRE_DIST, fois la « Vitesse de camera ») ; une touche de distance seule ou la molette l'interrompt ; tant qu'il en reste une enfoncee apres la pression double, rien ne se passe.
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
ANCIENS = {'cam_pres': ['NUM_ADD', 'E'], 'cam_loin': ['NUM_SUBTRACT', 'W']}                    # defauts de l'avance #153


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

    def test_touches_par_defaut_page_haut_et_page_bas(self):
        self.assertEqual(RG.TOUCHES_DEF['cam_pres'], ['PAGEUP', None]); self.assertEqual(RG.TOUCHES_DEF['cam_loin'], ['PAGEDOWN', None])
        for n in ('PAGEUP', 'PAGEDOWN'): self.assertNotIn(n, RG.RESERVEES); self.assertIsNotNone(RG.symbole(n), n)
        self.assertEqual((RG.nom_touche('PAGEUP'), RG.nom_touche('PAGEDOWN')), ('Page haut', 'Page bas'))
        r = RG.Reglages(None); self.assertEqual(r['touches']['cam_pres'], ['PAGEUP', None]); self.assertEqual(r['touches']['cam_loin'], ['PAGEDOWN', None])
        self.assertEqual(r['touches']['L'], ['A', None]); self.assertEqual(r['touches']['R'], ['R', None])                           # (L / R, pages des menus du jeu, perdent Page haut / Page bas : une touche ne sert qu'a une action)
        tous = [n for ts in RG.TOUCHES_DEF.values() for n in ts if n]; self.assertEqual(len(tous), len(set(tous)))

    def test_ancien_fichier_sans_ces_actions(self):
        r = charger({'touches_v': RG.DEFAUT['touches_v'], 'touches': {'carte': ['M', None]}})
        self.assertEqual(r['touches']['cam_pres'], ['PAGEUP', None]); self.assertEqual(r['touches']['cam_loin'], ['PAGEDOWN', None]); self.assertEqual(r['touches']['carte'], ['M', None])
        self.assertEqual(r['touches']['L'], ['A', None]); self.assertEqual(r['touches']['R'], ['R', None])                          # (L / R de l'ancien fichier avaient Page haut / Page bas : retirees)

    def test_fichier_de_l_avance_153_prend_les_nouveaux_defauts(self):
        r = charger({'touches_v': RG.DEFAUT['touches_v'], 'touches': dict(ANCIENS, L=['A', 'PAGEUP'], R=['R', 'PAGEDOWN'])})
        self.assertEqual(r['touches']['cam_pres'], ['PAGEUP', None]); self.assertEqual(r['touches']['cam_loin'], ['PAGEDOWN', None])
        self.assertEqual(r['touches']['L'], ['A', None]); self.assertEqual(r['touches']['R'], ['R', None])
        tous = [n for ts in r['touches'].values() for n in ts if n]; self.assertEqual(len(tous), len(set(tous)), 'une touche ne sert qu\'a une action')

    def test_page_haut_deja_prise_par_le_joueur(self):
        r = charger({'touches_v': RG.DEFAUT['touches_v'], 'touches': {'historique': ['PAGEUP', None], 'L': ['A', None]}})
        self.assertEqual(r['touches']['historique'], ['PAGEUP', None]); self.assertEqual(r['touches']['cam_pres'], [None, None]); self.assertEqual(r['touches']['cam_loin'], ['PAGEDOWN', None])      # (le choix du joueur est garde, la camera n'a pas la touche)

    def test_choix_du_joueur_garde(self):
        r = charger({'touches_v': RG.DEFAUT['touches_v'], 'touches': {'cam_pres': ['P', None], 'cam_loin': ['NUM_SUBTRACT', None]}})
        self.assertEqual(r['touches']['cam_pres'], ['P', None]); self.assertEqual(r['touches']['cam_loin'], ['NUM_SUBTRACT', None])                    # (un seul des deux anciens defauts ne compte pas comme « les anciens defauts »)
        r = charger({'touches_v': RG.DEFAUT['touches_v'], 'touches': {'cam_pres': ['NUM_ADD', None], 'cam_loin': ['W', 'NUM_SUBTRACT']}})
        self.assertEqual(r['touches']['cam_pres'], ['NUM_ADD', None]); self.assertEqual(r['touches']['cam_loin'], ['W', 'NUM_SUBTRACT'])

    def test_reattribution(self):
        r = RG.Reglages(None); avait = r.lier('cam_pres', 1, RG.symbole('P')); self.assertIsNone(avait); self.assertEqual(r['touches']['cam_pres'], ['PAGEUP', 'P'])


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
        for lib, act, v in (('Caméra (Rapprocher)', 'cam_pres', ['Page haut', '—']), ('Caméra (Éloigner)', 'cam_loin', ['Page bas', '—'])):
            x = next(t for t in e if t['l'] == lib); self.assertEqual((x['t'], x['act'], x['v']), ('touche', act, v))
            self.assertIn('en continu', x['aide']); self.assertIn('50 à 200 %', x['aide'])


class Faux:
    """Un `Jeu` minimal : les vraies methodes de fenetre.Jeu liees a cet objet, sur un etat factice (terrain libre d'une ville, camera a 100 %)."""
    def __init__(self, partie=None, distance=100):
        MO = FE.MO
        self.moteur = types.SimpleNamespace(etat=types.SimpleNamespace(partie=MO.PARTIE_VILLE if partie is None else partie, effet=None), msg_visible=False, menu_actif=lambda: None)
        self.pause = types.SimpleNamespace(ouvert=False); self.licence = None; self.sauv = None; self.titre = None; self._saisie_nom_en_cours = lambda: False; self.carte_ouverte = False
        self.reg = RG.Reglages(None); self.reg['distance_camera'] = distance; self.zoom = 100.0 / distance; self.fixe_test = True; self._pret = True; self.tenues = set(); self._t_dist = None; self.dist_retour = False; self.dist_bloque = False
        for nom in ('_zoom_possible', 'regler_zoom', 'regler_distance', '_maj_distance_clavier', 'distance_par_defaut'):
            setattr(self, nom, types.MethodType(getattr(FE.Jeu, nom), self))
        self._zoom_valide = FE.Jeu._zoom_valide; self._tenue = lambda a: a in self.tenues

    @property
    def distance(self): return 100.0 / self.zoom                                  # (exacte, non arrondie : c'est elle qui rend le mouvement fluide)

    def images(self, n, *touches):
        self.tenues = set(touches); out = []
        for _ in range(n): self._maj_distance_clavier(); out.append(self.distance)
        return out


@unittest.skipIf(FE is None, 'fenetre.py non importable ici')
class DansLeJeu(unittest.TestCase):
    def test_vitesse_de_rotation(self):
        self.assertEqual(FE.CAM_DIST_VIT, FE.CAM_LACET_VIT)                                                                           # meme vitesse que la rotation (100 par seconde)
        j = Faux(); j.images(30, 'cam_loin'); self.assertAlmostEqual(j.distance, 150.0, 6)                                         # 0,5 s : 100 -> 150 %
        j = Faux(); j.images(30, 'cam_pres'); self.assertAlmostEqual(j.distance, 50.0, 6)                                          # 0,5 s : 100 -> 50 %

    def test_mouvement_fluide_sans_a_coup(self):
        d = Faux().images(40, 'cam_loin'); pas = [b - a for a, b in zip([100.0] + d, d)]
        self.assertGreater(min(pas), 0.0); self.assertLess(max(pas) - min(pas), 1e-9)                                              # meme variation a chaque image : pas de palier, pas de delai, pas de saccade
        self.assertLess(max(pas), 2.0)                                                                                             # (moins de 2 % par image : continu a l'oeil)
        d = Faux().images(20, 'cam_pres'); pas = [b - a for a, b in zip([100.0] + d, d)]; self.assertLess(max(pas) - min(pas), 1e-9); self.assertLess(max(pas), 0.0)

    def test_agit_des_la_premiere_image_sans_delai(self):
        j = Faux(); j.images(1, 'cam_loin'); self.assertGreater(j.distance, 100.0)

    def test_valeur_enregistree_arrondie_au_pourcent(self):
        j = Faux(); j.images(7, 'cam_loin'); self.assertEqual(j.reg['distance_camera'], round(j.distance)); self.assertIsInstance(j.reg['distance_camera'], int)
        self.assertAlmostEqual(j.zoom, 100.0 / j.distance)                                                                          # (le zoom garde la valeur exacte)

    def test_la_touche_relachee_arrete_aussitot(self):
        j = Faux(); j.images(10, 'cam_loin'); d = j.distance; j.images(5); self.assertEqual(j.distance, d)

    def test_bornes_50_et_200(self):
        j = Faux(); j.images(1000, 'cam_loin'); self.assertEqual(j.distance, 200.0); self.assertEqual(j.reg['distance_camera'], 200)
        j = Faux(); j.images(1000, 'cam_pres'); self.assertEqual(j.distance, 50.0); self.assertEqual(j.reg['distance_camera'], 50)
        j = Faux(distance=200); j.images(5, 'cam_loin'); self.assertEqual(j.distance, 200.0)
        j = Faux(distance=50); j.images(5, 'cam_pres'); self.assertEqual(j.distance, 50.0)

    def test_reglages_de_vitesse_de_la_camera(self):
        j = Faux(); j.reg['vitesse_camera'] = 2.0; j.images(15, 'cam_loin'); self.assertAlmostEqual(j.distance, 150.0, 6)                # x2 : deux fois plus vite
        j = Faux(); j.images(15, 'cam_loin', 'accel'); self.assertAlmostEqual(j.distance, 100.0 + 25.0 * float(j.reg['vitesse_accel']), 6)      # accelerateur tenu : comme la rotation

    def test_les_deux_touches_ensemble_ramenent_a_100_progressivement(self):
        for depart in (200, 150, 70, 50):
            j = Faux(distance=depart); d = j.images(120, 'cam_loin', 'cam_pres'); self.assertEqual(j.distance, 100.0, depart); self.assertEqual(j.reg['distance_camera'], 100)
            sens = 1 if depart > 100 else -1
            pas = [abs(b - a) for a, b in zip([float(depart)] + d, d)]
            self.assertTrue(all((b - a) * sens <= 1e-9 for a, b in zip([float(depart)] + d, d)), depart)        # monotone : jamais de depassement ni de retour en arriere
            self.assertGreater(sum(1 for x in d if x != 100.0), 4, depart)                               # plusieurs images (pas un saut)
            self.assertLessEqual(max(pas), max(FE.CAM_RECENTRE_DIST, 5.0 * abs(depart - 100.0)) / 60.0 + 1e-9, depart)          # (l'ecart maximal d'une image : 5 x l'ecart / 60, plus de 8 % de la course a la fois, jamais plus)
            self.assertFalse(j.dist_retour)                                                                      # l'animation se termine d'elle-meme

    def test_duree_du_retour(self):
        j = Faux(distance=200); d = j.images(120, 'cam_loin', 'cam_pres'); n = next(i for i, x in enumerate(d) if x == 100.0) + 1
        self.assertTrue(10 <= n <= 40, n)                                                                       # de 200 % a 100 % : un tiers de seconde environ, comme 100 degres de rotation (ni un saut, ni une longue attente)
        j = Faux(distance=50); d = j.images(120, 'cam_loin', 'cam_pres'); n = next(i for i, x in enumerate(d) if x == 100.0) + 1; self.assertTrue(8 <= n <= 40, n)

    def test_meme_vitesse_que_le_recentrage_de_la_rotation(self):
        self.assertEqual(FE.CAM_RECENTRE_DIST, FE.CAM_RECENTRE_LACET)                                          # #173 : memes nombres (240 par seconde au minimum, 5 x l'ecart), memes unites de vitesse

    def test_deja_a_100_rien_ne_bouge(self):
        j = Faux(); d = j.images(30, 'cam_loin', 'cam_pres'); self.assertEqual(set(d), {100.0}); self.assertFalse(j.dist_retour)

    def test_vitesse_de_camera_et_accelerateur(self):
        def n_images(vit=1.0, *autres):
            j = Faux(distance=200); j.reg['vitesse_camera'] = vit; d = j.images(240, 'cam_loin', 'cam_pres', *autres); return next(i for i, x in enumerate(d) if x == 100.0) + 1
        base = n_images(); self.assertLess(n_images(2.0), base); self.assertGreater(n_images(0.5), base)        # « Vitesse de camera » : retour plus rapide / plus lent
        self.assertEqual(n_images(1.0, 'accel'), base)                                                          # l'accelerateur n'y change rien (comme la remise de la rotation)

    def test_le_retour_se_poursuit_apres_le_relachement(self):
        j = Faux(distance=200); j.images(3, 'cam_loin', 'cam_pres'); d = j.distance; self.assertTrue(j.dist_retour); self.assertLess(d, 200.0)
        j.images(120); self.assertEqual(j.distance, 100.0)                                                       # (touches relachees : l'animation va a son terme)

    def test_une_touche_restee_enfoncee_apres_la_pression_double_ne_fait_rien(self):
        j = Faux(distance=200); j.images(3, 'cam_loin', 'cam_pres'); j.images(5, 'cam_loin'); self.assertTrue(j.dist_retour)           # le retour continue, la touche restante n'agit pas
        j.images(120, 'cam_loin'); self.assertEqual(j.distance, 100.0)                                                                  # arrive a 100 %, la touche tenue ne les ecarte pas
        j.images(2); j.images(5, 'cam_loin'); self.assertGreater(j.distance, 100.0)                                                    # relachee puis pressee de nouveau : elle agit

    def test_une_touche_seule_interrompt_le_retour(self):
        j = Faux(distance=200); j.images(3, 'cam_loin', 'cam_pres'); j.images(1); j.images(2, 'cam_pres'); self.assertFalse(j.dist_retour)
        d = j.distance; j.images(10); self.assertEqual(j.distance, d)                                          # plus d'animation
        j = Faux(distance=200); j.images(3, 'cam_loin', 'cam_pres'); j.images(1); d = j.distance; j.images(5, 'cam_loin'); self.assertFalse(j.dist_retour); self.assertGreater(j.distance, d)       # (« Eloigner » seule reprend la main : la distance remonte)

    def test_ctrl_molette_et_ctrl_clic_molette_lancent_le_meme_retour(self):
        j = Faux(distance=60); self.assertFalse(j.dist_retour); j.distance_par_defaut(); self.assertTrue(j.dist_retour); self.assertEqual(j.distance, 60.0)       # (rien n'est immediat)
        d = j.images(120); self.assertEqual(j.distance, 100.0); self.assertEqual(j.reg['distance_camera'], 100); self.assertGreater(sum(1 for x in d if x not in (60.0, 100.0)), 5)

    def test_le_retour_s_arrete_hors_du_terrain(self):
        j = Faux(distance=200); j.distance_par_defaut(); j.images(2); d = j.distance; j.pause.ouvert = True; j.images(30); self.assertEqual(j.distance, d); self.assertFalse(j.dist_retour)      # menu Echap
        j.pause.ouvert = False; j.images(30); self.assertEqual(j.distance, d)                                                                                                       # (annule : ne reprend pas tout seul)
        j = Faux(distance=200); j.distance_par_defaut(); j.moteur.msg_visible = True; j.images(30); self.assertEqual(j.distance, 200.0)

    def test_changer_de_sens_est_immediat(self):
        j = Faux(); j.images(10, 'cam_loin'); d = j.distance; j.images(10, 'cam_pres'); self.assertAlmostEqual(j.distance, 100.0, 6); self.assertGreater(d, 100.0)

    def test_rien_hors_du_terrain(self):
        MO = FE.MO
        j = Faux(); j.pause.ouvert = True; j.images(5, 'cam_loin'); self.assertEqual(j.distance, 100.0)                             # menu Echap
        j = Faux(); j.moteur.msg_visible = True; j.images(5, 'cam_loin'); self.assertEqual(j.distance, 100.0)                       # message
        j = Faux(); j.moteur.menu_actif = lambda: object(); j.images(5, 'cam_loin'); self.assertEqual(j.distance, 100.0)            # menu du jeu
        j = Faux(); j.carte_ouverte = True; j.images(5, 'cam_loin'); self.assertEqual(j.distance, 100.0)                            # carte ouverte
        j = Faux(partie=MO.PARTIE_COMBAT); j.images(5, 'cam_loin'); self.assertEqual(j.distance, 100.0)                             # combat
        j = Faux(); j.images(5, 'cam_loin'); self.assertGreater(j.distance, 100.0)                                                  # (le terrain libre, lui, agit)

    def test_la_carte_du_monde_aussi(self):
        j = Faux(partie=FE.MO.PARTIE_CHAMP); j.images(5, 'cam_loin'); self.assertGreater(j.distance, 100.0)                         # comme la molette : villes, donjons, tours et carte du monde


if __name__ == '__main__':
    unittest.main(verbosity=1)
