"""Test du choix du moniteur du plein ecran (reglage `ecran_plein`, ligne « Écran du plein écran » de la page Affichage) : sans fenetre reelle, avec de faux moniteurs (`FauxEcran`) et la vraie logique
de ecrans.py et de fenetre.Jeu (liee a une fausse fenetre qui journalise ses appels).

  1. ecrans.py : liste des moniteurs (principal marque), libelles, memorisation, retrouvaille au lancement suivant (moniteurs dans un autre ordre, resolution changee, moniteur absent, noms en double) ;
  2. reglages : defaut = automatique, enregistrement, valeurs absurdes -> automatique ;
  3. plein ecran (F11, Alt + Entree, interrupteur) : le moniteur choisi sert a chaque entree ; automatique = celui de la fenetre ; changement de choix en plein ecran = bascule immediate vers le nouveau moniteur,
     en une seule etape ; echec = moniteur de depart garde ; moniteur absent ou illisible = repli sans plantage ; retour en fenetre ou elle etait (ou centree sur le moniteur du plein ecran) ;
  4. page Affichage : la ligne, ses valeurs, ses libelles, sa note, son bouton rond.

    python3 outils/test_ecrans.py
"""
import json, os, sys, tempfile, types, unittest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, '..', 'dq4_pc')); sys.path.insert(0, ICI)
import pyglet
pyglet.options['shadow_window'] = False          # pas de fenetre cachee : le test tourne sans serveur d'affichage
import ecrans as EK
import reglages as RG

try:
    import fenetre as FE
    from test_mode_fenetre import FausseFenetre, FauxEcran
except Exception as ex:
    FE = None; ERREUR_FE = ex

A = lambda: FauxEcran(0, 0, 1920, 1080, 'Moniteur A', True)
B = lambda: FauxEcran(1920, 0, 2560, 1440, 'Moniteur B')
C = lambda: FauxEcran(-1280, 0, 1280, 1024, '')


class Logique(unittest.TestCase):
    def test_liste_principal_marque_et_libelles(self):
        d = EK.lister([B(), A()])                                                    # (pyglet peut donner le principal en second)
        self.assertEqual([x['principal'] for x in d], [False, True]); self.assertEqual([x['indice'] for x in d], [0, 1])
        self.assertEqual(EK.libelle(d[1]), 'Écran 2 (1920x1080), principal, Moniteur A')
        self.assertEqual(EK.libelle(EK.lister([C()])[0]), 'Écran 1 (1280x1024), principal')                       # sans nom : pas de virgule en trop
        self.assertEqual(EK.libelle(EK.lister([A(), B()])[1]), 'Écran 2 (2560x1440), Moniteur B')

    def test_un_seul_principal_meme_si_le_systeme_n_en_annonce_pas(self):
        e1, e2 = FauxEcran(0, 0, 100, 100), FauxEcran(100, 0, 100, 100)
        e1.is_primary = e2.is_primary = False
        d = EK.lister([e2, e1]); self.assertEqual(sum(x['principal'] for x in d), 1); self.assertTrue(d[1]['principal'])          # (a defaut : celui en (0, 0))
        e1.x = 5; self.assertTrue(EK.lister([e2, e1])[0]['principal'])                                           # (a defaut du defaut : le premier)

    def test_ecrans_illisibles(self):
        self.assertEqual(EK.lister(None), []); self.assertEqual(EK.lister([]), [])
        d = EK.lister([object(), A()]); self.assertEqual(len(d), 1); self.assertEqual(d[0]['source'], 1)         # (un ecran illisible est ignore ; `source` retrouve l'objet pyglet)

    def test_memoriser_puis_retrouver_dans_un_autre_ordre(self):
        d = EK.lister([A(), B()]); choix = EK.memoriser(d[1])
        self.assertEqual(EK.retrouver(choix, EK.lister([B(), A()])), 0)                                          # moniteurs permutes : retrouve par le nom
        self.assertEqual(EK.retrouver(choix, EK.lister([A(), B()])), 1)

    def test_resolution_changee_avec_nom(self):
        choix = EK.memoriser(EK.lister([A(), B()])[1])
        b2 = FauxEcran(1920, 0, 1920, 1080, 'Moniteur B')                                                        # le moniteur B tourne maintenant en 1920x1080
        self.assertEqual(EK.retrouver(choix, EK.lister([A(), b2])), 1)

    def test_sans_nom_indice_et_dimensions(self):
        d = EK.lister([A(), C()]); choix = EK.memoriser(d[1])                                                    # C n'a pas de nom
        a_sans = FauxEcran(0, 0, 1920, 1080, '', True)
        self.assertEqual(EK.retrouver(choix, EK.lister([a_sans, C()])), 1)
        self.assertEqual(EK.retrouver(choix, EK.lister([C(), a_sans])), 0)                                       # (permutes : memes dimensions, unique)
        autre = FauxEcran(-1280, 0, 1600, 900, '')
        self.assertIsNone(EK.retrouver(choix, EK.lister([a_sans, autre])))                                       # resolution changee et pas de nom : plus retrouve (repli)

    def test_ecran_absent(self):
        choix = EK.memoriser(EK.lister([A(), B()])[1])
        self.assertIsNone(EK.retrouver(choix, EK.lister([A()])))                                                 # le moniteur B n'est plus branche
        self.assertIsNone(EK.retrouver(choix, [])); self.assertIsNone(EK.retrouver(None, EK.lister([A()])))

    def test_noms_en_double(self):
        x1, x2 = FauxEcran(0, 0, 1920, 1080, 'Generic PnP', True), FauxEcran(1920, 0, 1920, 1080, 'Generic PnP')
        choix = EK.memoriser(EK.lister([x1, x2])[1])
        self.assertEqual(EK.retrouver(choix, EK.lister([x1, x2])), 1)                                           # meme nom, memes dimensions : le meme indice
        self.assertEqual(EK.retrouver(choix, EK.lister([x2, x1])), 0)                                           # permutes : la position (1920, 0) le retrouve

    def test_valide_ecarte_les_valeurs_absurdes(self):
        bon = dict(indice=1, x=1920, y=0, largeur=2560, hauteur=1440, nom='B')
        self.assertEqual(EK.valide(bon), bon)
        for v in (None, 'x', 3, [], {}, dict(bon, largeur=0), dict(bon, hauteur=-5), dict(bon, indice=-1), dict(bon, indice=999), dict(bon, indice='a'), dict(bon, largeur='abc'), True):
            self.assertIsNone(EK.valide(v), repr(v))
        self.assertEqual(EK.valide(dict(bon, nom=None))['nom'], '')                                              # (nom absent : vide)

    def test_cible_et_etats(self):
        d = EK.lister([A(), B()]); choix = EK.memoriser(d[1])
        self.assertEqual(EK.cible(None, d, 0), (0, 'auto')); self.assertEqual(EK.cible(None, d, 1), (1, 'auto'))                          # automatique : celui de la fenetre
        self.assertEqual(EK.cible(None, d, None), (0, 'auto'))                                                    # fenetre inconnue : le principal
        self.assertEqual(EK.cible(choix, d, 0), (1, 'choisi'))
        self.assertEqual(EK.cible(choix, EK.lister([A()]), 0), (0, 'absent'))                                    # choisi mais absent : celui de la fenetre
        self.assertEqual(EK.cible(choix, [], None), (None, 'absent')); self.assertEqual(EK.cible(None, [], None), (None, 'auto'))
        self.assertEqual(EK.cible(choix, d, 7), (1, 'choisi'))

    def test_ecran_de_la_fenetre(self):
        d = EK.lister([A(), B(), C()])
        self.assertEqual(EK.ecran_de((100, 80, 1280, 720), d), 0)
        self.assertEqual(EK.ecran_de((2000, 100, 1280, 720), d), 1)
        self.assertEqual(EK.ecran_de((-1000, 0, 1280, 720), d), 2)
        self.assertEqual(EK.ecran_de((1500, 100, 1280, 720), d), 1)                                              # a cheval : celui du centre (2140, 460)
        self.assertEqual(EK.ecran_de((1500, 100, 600, 300), d), 0)                                               # a cheval, centre (1800, 250) : A
        self.assertEqual(EK.ecran_de((1800, 100, 400, 300), d), 1)                                               # centre (2000, 250) : B
        self.assertIsNone(EK.ecran_de((9000, 9000, 100, 100), d)); self.assertIsNone(EK.ecran_de(None, d)); self.assertIsNone(EK.ecran_de((1, 2), d))

    def test_valeurs_et_libelles_de_la_liste(self):
        d = EK.lister([A(), B()]); choix = EK.memoriser(d[1])
        self.assertEqual(EK.valeurs_liste(None, d), ['auto', 0, 1]); self.assertEqual(EK.valeurs_liste(choix, d), ['auto', 0, 1])
        self.assertEqual(EK.valeurs_liste(choix, d[:1]), ['auto', 0, 'absent'])                                  # l'ecran enregistre n'est plus la : sa ligne reste, « absent »
        self.assertEqual((EK.valeur_choisie(None, d), EK.valeur_choisie(choix, d), EK.valeur_choisie(choix, d[:1])), ('auto', 1, 'absent'))
        self.assertEqual(EK.nom_valeur('auto', None, d), 'Automatique (écran de la fenêtre)')
        self.assertEqual(EK.nom_valeur(1, choix, d), 'Écran 2 (2560x1440), Moniteur B'); self.assertEqual(EK.nom_valeur('absent', choix, d[:1]), 'Écran 2 (absent)')


class Reglage(unittest.TestCase):
    def charger(self, contenu):
        f = os.path.join(tempfile.mkdtemp(prefix='rg_ecran_'), 'reglages.json')
        with open(f, 'w', encoding='utf-8') as fh: json.dump(contenu, fh)
        return RG.Reglages(f), f

    def test_defaut_automatique(self):
        self.assertIsNone(RG.DEFAUT['ecran_plein']); self.assertIsNone(RG.Reglages(None)['ecran_plein'])
        r, _ = self.charger({'son': False}); self.assertIsNone(r['ecran_plein'])                                  # un ancien fichier : automatique
        self.assertIsNone(RG.Reglages.defaut('ecran_plein'))

    def test_enregistrement_et_relecture(self):
        r, f = self.charger({}); d = EK.lister([A(), B()])[1]; r['ecran_plein'] = EK.memoriser(d); r.enregistrer()
        with open(f, encoding='utf-8') as fh: brut = json.load(fh)
        self.assertEqual(brut['ecran_plein'], dict(indice=1, x=1920, y=0, largeur=2560, hauteur=1440, nom='Moniteur B'))
        self.assertEqual(RG.Reglages(f)['ecran_plein'], brut['ecran_plein'])
        r['ecran_plein'] = None; r.enregistrer(); self.assertIsNone(RG.Reglages(f)['ecran_plein'])

    def test_valeurs_absurdes_donnent_automatique(self):
        for brut in ('B', 2, [1, 2], {'indice': 'x'}, {'indice': 1, 'largeur': 0, 'hauteur': 5}, {}, True, {'indice': 1, 'x': 'a', 'y': None, 'largeur': 1920, 'hauteur': 1080}):
            r, _ = self.charger({'ecran_plein': brut})
            self.assertTrue(r['ecran_plein'] is None or isinstance(r['ecran_plein'], dict), repr(brut))
            if isinstance(r['ecran_plein'], dict): self.assertEqual(r['ecran_plein']['largeur'], 1920)             # (un champ de position illisible vaut 0, le reste est garde)
            else: self.assertIsNone(r['ecran_plein'])

    def test_cles_camera_booleennes(self):
        r = RG.Reglages(None); self.assertEqual((r['camera_inverser_gd'], r['camera_inverser_hb']), (False, False))          # defaut = comportement actuel
        r, _ = self.charger({'camera_inverser_gd': True, 'camera_inverser_hb': 'oui'}); self.assertEqual((r['camera_inverser_gd'], r['camera_inverser_hb']), (True, False))      # (valeur absurde : defaut)
        r, f = self.charger({}); r['camera_inverser_hb'] = True; r.enregistrer(); self.assertEqual((RG.Reglages(f)['camera_inverser_gd'], RG.Reglages(f)['camera_inverser_hb']), (False, True))


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

    def test_automatique_fenetre_sur_le_moniteur_de_pyglet_comme_avant(self):
        f = self.deux(); f.regler_plein_ecran(True)
        self.assertEqual(self.sets(f), ['set_fullscreen(True)']); self.assertEqual((f.width, f.height), (1920, 1080))          # aucun moniteur impose : rien ne change pour qui n'a qu'un ecran
        f = fen(); f.regler_plein_ecran(True); self.assertEqual(self.sets(f), ['set_fullscreen(True)'])             # un seul moniteur

    def test_automatique_suit_la_fenetre_deplacee_sur_un_autre_moniteur(self):
        f = self.deux(); f._windowed_location = (2000, 100)                                                       # (pyglet croit toujours la fenetre sur A, elle est sur B)
        f.regler_plein_ecran(True); self.assertEqual(self.sets(f), ['set_fullscreen(True,écran 2)']); self.assertEqual((f.width, f.height), (2560, 1440))

    def test_le_moniteur_choisi_sert_a_chaque_entree(self):
        f = self.deux(); f.regler_ecran_plein(1)
        self.assertEqual(f.reg['ecran_plein']['indice'], 1); self.assertEqual((f.reg['ecran_plein']['largeur'], f.reg['ecran_plein']['hauteur']), (2560, 1440)); self.assertEqual(self.sets(f), [])      # fenetre : rien ne bouge encore
        for fois in range(3):                                                                                       # (interrupteur, F11 et Alt + Entree appellent le meme code)
            f.journal.clear(); f.basculer_plein_ecran(); self.assertTrue(f.fullscreen); self.assertEqual(self.sets(f), ['set_fullscreen(True,écran 2)'], fois); self.assertEqual((f.width, f.height), (2560, 1440))
            f.basculer_plein_ecran(); self.assertFalse(f.fullscreen)
            self.assertEqual(f.get_location(), (100, 80))                                                          # (revenue la ou elle etait, sur le moniteur A)

    def test_changer_de_choix_en_plein_ecran_deplace_aussitot_en_une_etape(self):
        f = self.deux(); f.regler_plein_ecran(True); f.journal.clear()
        f.regler_ecran_plein(1)
        self.assertEqual(f.journal, ['visible(False)', 'set_fullscreen(True,écran 2)', 'switch_to', 'on_draw(2560x1440)', 'flip', 'visible(True)', 'switch_to', 'on_draw(2560x1440)', 'flip', 'journal(plein écran)'])
        self.assertEqual((f.mode_fen, f.reg['mode_fenetre'], f.width, f.height), (1, 1, 2560, 1440)); self.assertEqual(f.zone_plein, (1920, 0, 2560, 1440))
        f.journal.clear(); f.regler_ecran_plein(0)                                                                # et retour sur le moniteur A
        self.assertEqual(self.sets(f), ['set_fullscreen(True,écran 1)']); self.assertEqual((f.width, f.height), (1920, 1080))
        f.journal.clear(); f.regler_ecran_plein(0); self.assertEqual(f.journal, [])                               # (deja la : rien)
        f.basculer_plein_ecran(); self.assertEqual(f.get_location(), (100, 80)); self.assertEqual((f.width, f.height), (1280, 720))        # retour en fenetre : taille et place d'avant

    def test_retour_automatique_en_plein_ecran_ne_deplace_pas(self):
        f = self.deux(); f.regler_ecran_plein(1); f.regler_plein_ecran(True); f.journal.clear()
        f.regler_ecran_plein('auto'); self.assertIsNone(f.reg['ecran_plein']); self.assertEqual(f.journal, [])    # automatique = l'ecran de la fenetre : c'est celui ou elle est deja (pas de saut)

    def test_choix_en_fenetre_pas_de_bascule(self):
        f = self.deux(); f.regler_ecran_plein(1); f.regler_ecran_plein('auto'); f.regler_ecran_plein(0); self.assertEqual(f.journal, []); self.assertFalse(f.fullscreen)

    def test_choix_invalides_ignores(self):
        f = self.deux(); f.regler_ecran_plein(1); avant = dict(f.reg['ecran_plein'])
        for v in (5, -1, 'absent', None, True, 'x', 1.5): f.regler_ecran_plein(v)
        self.assertEqual(f.reg['ecran_plein'], avant); self.assertEqual(f.journal, [])                            # (une valeur qui n'est pas un moniteur ne change rien ; « absent » non plus)

    def test_ecran_choisi_absent_repli_sur_la_fenetre_sans_plantage(self):
        f = self.deux(); f.regler_ecran_plein(1); f2 = fen([A()])                                                 # au lancement suivant, B n'est plus branche
        f2.reg['ecran_plein'] = dict(f.reg['ecran_plein'])
        self.assertEqual(f2.valeur_ecran(), 'absent'); self.assertEqual(f2.valeurs_ecran(), ['auto', 0, 'absent']); self.assertIn('absent', f2.nom_ecran('absent')); self.assertIn('Écran absent', f2.note_ecran())
        f2.regler_plein_ecran(True); self.assertTrue(f2.fullscreen); self.assertEqual((f2.width, f2.height), (1920, 1080))
        self.assertEqual(f2.reg['ecran_plein']['indice'], 1)                                                      # (le choix reste enregistre : il resservira si B revient)
        f2.regler_ecran_plein('absent'); self.assertEqual(f2.reg['ecran_plein']['indice'], 1)
        f2.regler_ecran_plein('auto'); self.assertIsNone(f2.reg['ecran_plein'])

    def test_moniteurs_illisibles_pas_de_plantage(self):
        f = self.deux()
        def casse(): raise OSError('plus de moniteurs')
        f.display = types.SimpleNamespace(get_screens=casse)
        self.assertEqual(f._lire_ecrans(True), ([], [])); self.assertEqual(f.valeurs_ecran(), ['auto']); self.assertEqual(f._ecran_pour_plein()[0], None)
        f.regler_plein_ecran(True); self.assertTrue(f.fullscreen); self.assertEqual(self.sets(f), ['set_fullscreen(True)'])                  # pyglet garde son moniteur
        f.regler_ecran_plein(0); self.assertTrue(f.fullscreen)                                                    # (aucun moniteur connu : le choix est ignore)

    def test_echec_du_deplacement_garde_le_moniteur_de_depart(self):
        f = self.deux(); f.regler_plein_ecran(True); f.journal.clear(); os.environ['DQ_SIM_ECHEC'] = '1'
        f.regler_ecran_plein(1)
        self.assertTrue(f.fullscreen); self.assertTrue(f._visible); self.assertEqual((f.mode_fen, f.width, f.height), (1, 1920, 1080)); self.assertEqual(f.screen, f._ecrans[0])      # retour sur A
        self.assertEqual(f.toasts, ['Plein écran impossible']); self.assertEqual(self.sets(f), ['set_fullscreen(True,écran 2)', 'set_fullscreen(True,écran 1)'])

    def test_echec_de_l_entree_sur_le_moniteur_choisi_reste_en_fenetre(self):
        f = self.deux(); f.regler_ecran_plein(1); os.environ['DQ_SIM_ECHEC'] = '1'; f.regler_plein_ecran(True)
        self.assertFalse(f.fullscreen); self.assertTrue(f._visible); self.assertEqual((f.mode_fen, f.reg['mode_fenetre']), (0, 0)); self.assertEqual(f.reg['ecran_plein']['indice'], 1)

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
        import pause; cls.PA = pause

    def page(self, ecrans=None, plein=False):
        f = fen(ecrans or [A(), B()], plein=plein)
        f.mode = 4; f.zoom = 1.0; f.post = types.SimpleNamespace(max_msaa=None); f.resolutions = lambda: [(1280, 720), (1920, 1080)]; f.resolution_courante = lambda: (1280, 720)
        f.regler_resolution = lambda v: None; f.regler_mode = lambda v: None; f.regler_distance = lambda v: None
        P = self.PA.Pause(f); return f, P, {x['l']: x for x in P._e_affichage()}

    def test_ligne_placee_pres_de_plein_ecran(self):
        f, P, e = self.page(); ordre = [x['l'] for x in P._e_affichage()]
        self.assertEqual(ordre[:3], ['Plein écran', 'Écran du plein écran', 'Résolution'])

    def test_valeurs_libelles_et_aide(self):
        f, P, e = self.page(); l = e['Écran du plein écran']
        self.assertEqual(l['vals'], ['auto', 0, 1]); self.assertTrue(l['liste']); self.assertFalse(l['sw']); self.assertTrue(l['aide'])
        self.assertEqual([P._nom_valeur('Écran du plein écran', v) for v in l['vals']], ['Automatique (écran de la fenêtre)', 'Écran 1 (1920x1080), principal, Moniteur A', 'Écran 2 (2560x1440), Moniteur B'])
        self.assertEqual(l['v'](), 'Automatique (écran de la fenêtre)'); self.assertEqual(l['note'](), '')

    def test_choisir_applique_et_le_bouton_rond_remet_automatique(self):
        f, P, e = self.page(); l = e['Écran du plein écran']
        l['set'](1); self.assertEqual(f.reg['ecran_plein']['indice'], 1)
        _, _, e = self.page(); l = e['Écran du plein écran']                                                         # (relu de l'etat des reglages)
        f.reg['ecran_plein'] = dict(indice=1, x=1920, y=0, largeur=2560, hauteur=1440, nom='Moniteur B'); l = {x['l']: x for x in P._e_affichage()}['Écran du plein écran']
        self.assertEqual(l['get'](), 1); self.assertFalse(l['est_defaut']())
        l['defaut'](); self.assertIsNone(f.reg['ecran_plein']); self.assertTrue({x['l']: x for x in P._e_affichage()}['Écran du plein écran']['est_defaut']())
        l['moins'](); l['plus']()                                                                                   # (gauche / droite parcourent la liste)

    def test_un_seul_moniteur_note(self):
        f, P, e = self.page([A()]); l = e['Écran du plein écran']; self.assertEqual(l['vals'], ['auto', 0]); self.assertEqual(l['note'](), 'Un seul écran détecté')

    def test_choisi_en_plein_ecran_est_immediat(self):
        f, P, e = self.page(plein=True); l = e['Écran du plein écran']; f.journal.clear(); l['set'](1)
        self.assertEqual([x for x in f.journal if x.startswith('set_fullscreen')], ['set_fullscreen(True,écran 2)'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
