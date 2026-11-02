"""Test des deux modes de la fenetre (fenetre, plein ecran) : reglage `mode_fenetre` (bornes, migration de l'ancien booleen `plein_ecran` et de l'ancien plein ecran exclusif, cles abandonnees), raccourcis F11 et Alt + Entree
(vrai code de Jeu.on_key_press / on_key_release / _fronts sur un faux Jeu), bascule en une seule etape (vrai code de Jeu.regler_plein_ecran / _poser_plein_ecran sur une fausse fenetre : ordre des appels, retour a l'etat de depart en cas
d'echec), ordre et grisage des lignes de la page Affichage du menu Echap (interrupteur « Plein écran », plus de « Lissage des textures » ni de « Correction des bords des sprites »). Aucune vraie fenetre n'est ouverte.

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
        self.assertEqual(r['mode_fenetre'], 0)
        for k in RG.CLES_OBSOLETES: self.assertNotIn(k, r.v, k)

    def test_migration_de_l_ancien_booleen(self):
        r, _ = charger({'plein_ecran': True}); self.assertEqual(r['mode_fenetre'], 1)          # l'ancien plein ecran = fenetre sans bordure : le mode 1
        r, _ = charger({'plein_ecran': False}); self.assertEqual(r['mode_fenetre'], 0)
        r, _ = charger({'son': False}); self.assertEqual(r['mode_fenetre'], 0)                  # ni l'un ni l'autre : fenetre
        r, _ = charger({'plein_ecran': 'oui'}); self.assertEqual(r['mode_fenetre'], 0)          # valeur absurde
        r, _ = charger({'plein_ecran': True, 'mode_fenetre': 1}); self.assertEqual(r['mode_fenetre'], 1)
        r, _ = charger({'plein_ecran': True, 'mode_fenetre': 0}); self.assertEqual(r['mode_fenetre'], 0)      # le nouveau reglage prime

    def test_ancien_plein_ecran_exclusif_devient_plein_ecran(self):
        r, _ = charger({'mode_fenetre': 2}); self.assertEqual(r['mode_fenetre'], 1)
        r, _ = charger({'mode_fenetre': 2, 'mode_fenetre_retour': 0, 'plein_ecran': False}); self.assertEqual(r['mode_fenetre'], 1)       # (le dernier mode non exclusif de la #42 est abandonne)
        r, _ = charger({'mode_fenetre': 2.0}); self.assertEqual(r['mode_fenetre'], 1)

    def test_bornes(self):
        for brut, attendu in ((0, 0), (1, 1), (2, 1), (3, 0), (-1, 0), (1.5, 0), (2.0, 1), ('x', 0), ('2', 0), (None, 0), ([1], 0), (True, 1), (False, 0), (float('nan'), 0), (float('inf'), 0)):
            r, _ = charger({'mode_fenetre': brut}); self.assertEqual(r['mode_fenetre'], attendu, repr(brut))
            self.assertEqual(RG.mode_fenetre_valide(brut), attendu, repr(brut))

    def test_plus_de_symboles_du_plein_ecran_exclusif(self):
        for nom in ('MODES_FENETRE', 'NOMS_MODES_FENETRE'): self.assertFalse(hasattr(RG, nom), nom)

    def test_cles_abandonnees_ni_lues_ni_ecrites(self):
        """`mode_fenetre_retour` (#42), `correction_bords` et `lissage` (options retirees), `plein_ecran` (booleen d'avant la #42) : un ancien fichier les contient, ils sont ignores puis disparaissent a la sauvegarde ; le reste est garde."""
        r, f = charger({'plein_ecran': True, 'mode_fenetre_retour': 1, 'correction_bords': False, 'lissage': False, 'volume_musique': 0.4, 'msaa': 8})
        for k in RG.CLES_OBSOLETES: self.assertNotIn(k, r.v, k)
        self.assertEqual((r['mode_fenetre'], r['volume_musique'], r['msaa']), (1, 0.4, 8))
        r.enregistrer()
        with open(f, encoding='utf-8') as fh: brut = json.load(fh)
        for k in RG.CLES_OBSOLETES: self.assertNotIn(k, brut, k)
        r2 = RG.Reglages(f); self.assertEqual((r2['mode_fenetre'], r2['volume_musique'], r2['msaa']), (1, 0.4, 8))

    def test_aller_retour(self):
        r, f = charger({'mode_fenetre': 2, 'volume_musique': 0.4})
        r['mode_fenetre'] = 0; r.enregistrer(); self.assertEqual(RG.Reglages(f)['mode_fenetre'], 0)
        r['mode_fenetre'] = 1; r.enregistrer(); self.assertEqual(RG.Reglages(f)['mode_fenetre'], 1)

    def test_f11_retiree_d_un_ancien_fichier(self):
        r, _ = charger({'touches_v': 4, 'touches': {'infos': ['F11', None], 'carte': ['M', 'F11']}})
        self.assertEqual(r['touches']['infos'], [None, None]); self.assertEqual(r['touches']['carte'], ['M', None])      # (F11 n'est plus une touche d'action)

    def test_f11_non_reattribuable(self):
        self.assertIn('F11', RG.RESERVEES); self.assertIn('ESCAPE', RG.RESERVEES)
        self.assertFalse(any('F11' in ts for ts in RG.TOUCHES_DEF.values()))                    # (F11 n'etait pas une touche du jeu)


class Raccourcis(unittest.TestCase):
    """F11 et Alt + Entree (vrai code de Jeu.on_key_press / on_key_release / _fronts sur un faux Jeu, sans fenetre) : bascule, Entree avalee, discussion de groupe (Alt) au relachement d'Alt seul."""
    @classmethod
    def setUpClass(cls):
        try: import fenetre, pyglet; cls.FE = fenetre; cls.K = pyglet.window.key; cls.pyglet = pyglet
        except Exception as ex: raise unittest.SkipTest('fenetre.py non importable ici (%r)' % (ex,))

    def faux_jeu(self):
        FE = self.FE
        j = types.SimpleNamespace(avalees=set(), alt_cand=False, alt_tap=False, reg=RG.Reglages(None), touches=self.K.KeyStateHandler(), act_prec={}, n=0, _pret=True, combo=[False, False], _logo_touche=False, appuis_pause=0, appuis_nom=0,
                                  pause=None, _en_bascule=False, post=object(), sauv=None, licence=None, dernier_peripherique='', bascules=0, annulations=0, est_plein=False)
        j.pause = types.SimpleNamespace(ouvert=False, capture=None, touche=lambda sym, mods: setattr(j, 'appuis_pause', j.appuis_pause + 1))
        j.saisie_nom = types.SimpleNamespace(touche=lambda sym, mods: setattr(j, 'appuis_nom', j.appuis_nom + 1))
        j.basculer_plein_ecran = lambda: setattr(j, 'bascules', j.bascules + 1)
        j._tenue = lambda a: FE.Jeu._tenue(j, a); j._saisie_nom_en_cours = lambda: False; j._num_etat = FE.Jeu._num_etat; j._raccourci_fenetre = lambda sym, mods: FE.Jeu._raccourci_fenetre(j, sym, mods)
        j.annuler_chargement = lambda: setattr(j, 'annulations', j.annulations + 1)
        return j

    def appui(self, j, sym):
        mods = self.K.MOD_ALT if j.touches[self.K.LALT] or j.touches[self.K.RALT] else 0
        j.touches.on_key_press(sym, mods); return self.FE.Jeu.on_key_press(j, sym, mods)

    def relache(self, j, sym):
        j.touches.on_key_release(sym, 0); self.FE.Jeu.on_key_release(j, sym, 0)

    def tick(self, j): return self.FE.Jeu._fronts(j)

    def test_f11_bascule_et_n_est_pas_une_action(self):
        K = self.K; j = self.faux_jeu(); self.appui(j, K.F11)
        self.assertEqual(j.bascules, 1); self.assertIn(K.F11, j.avalees)
        j.reg['touches']['infos'][0] = 'F11'; j.reg.codes_cache = {}                       # (un ancien fichier qui lie F11 a une action : elle ne part pas)
        self.assertFalse(j._tenue('infos'))
        self.relache(j, K.F11); self.assertNotIn(K.F11, j.avalees)

    def test_alt_entree_bascule_sans_valider_ni_discussion(self):
        K = self.K; j = self.faux_jeu()
        self.appui(j, K.LALT); self.assertTrue(j.alt_cand)
        self.assertFalse(self.tick(j)['discussion'])                                       # Alt tenue : rien tant qu'il n'est pas relache
        self.appui(j, K.RETURN)
        self.assertEqual(j.bascules, 1); self.assertFalse(j.alt_cand)
        fr = self.tick(j); self.assertFalse(fr['menu']); self.assertFalse(j._tenue('menu'))      # Entree avalee : ni validation, ni menu
        self.relache(j, K.RETURN); self.relache(j, K.LALT)
        self.assertFalse(self.tick(j)['discussion']); self.assertFalse(j.alt_tap)          # Alt relache apres Alt + Entree : pas de discussion de groupe
        self.appui(j, K.RETURN); self.assertTrue(self.tick(j)['menu'])                     # (Entree seule fonctionne de nouveau)
        self.assertEqual(j.bascules, 1)

    def test_entree_pave_et_alt_gr(self):
        K = self.K; j = self.faux_jeu(); self.appui(j, K.RALT); self.appui(j, K.ENTER)
        self.assertEqual(j.bascules, 1); self.relache(j, K.ENTER); self.relache(j, K.RALT); self.assertFalse(self.tick(j)['discussion'])

    def test_alt_entree_sans_drapeau_du_systeme(self):
        """Le drapeau MOD_ALT de l'evenement peut manquer (Alt deja enfoncee avant le focus, clavier particulier) : l'etat des touches Alt suffit."""
        K = self.K; j = self.faux_jeu(); j.touches.on_key_press(K.LALT, 0)
        self.FE.Jeu.on_key_press(j, K.RETURN, 0); self.assertEqual(j.bascules, 1)

    def test_entree_seule_ne_bascule_pas(self):
        K = self.K; j = self.faux_jeu(); self.appui(j, K.RETURN); self.assertEqual(j.bascules, 0); self.assertTrue(self.tick(j)['menu'])
        self.appui(j, K.LALT); self.assertEqual(j.bascules, 0)                             # (Alt seule non plus)

    def test_dans_tous_les_contextes(self):
        """Menu Echap ouvert, saisie du nom, logos d'entree : F11 et Alt + Entree basculent et ne sont transmis ni au menu, ni a la saisie, ni aux logos (qui s'ignorent d'un appui)."""
        K = self.K
        j = self.faux_jeu(); j.pause.ouvert = True; self.appui(j, K.F11); self.appui(j, K.LALT); self.assertEqual((j.bascules, j.appuis_pause), (1, 1))      # (Alt seule arrive au menu)
        self.appui(j, K.RETURN); self.assertEqual((j.bascules, j.appuis_pause), (2, 1))                    # Alt + Entree : bascule, pas de touche Entree pour le menu
        self.relache(j, K.RETURN); self.relache(j, K.LALT); self.appui(j, K.RETURN); self.assertEqual((j.bascules, j.appuis_pause), (2, 2))      # Entree seule y arrive
        j = self.faux_jeu(); j._saisie_nom_en_cours = lambda: True; self.appui(j, K.F11); self.assertEqual((j.bascules, j.appuis_nom), (1, 0))
        j = self.faux_jeu(); j._pret = False; self.appui(j, K.F11); self.assertEqual((j.bascules, j._logo_touche), (1, False))      # (un appui sur une autre touche saute les logos, pas F11)
        self.appui(j, K.SPACE); self.assertTrue(j._logo_touche)

    def test_alt_seul_declenche_la_discussion_au_relachement(self):
        K = self.K; j = self.faux_jeu()
        self.appui(j, K.LALT); self.assertFalse(self.tick(j)['discussion'])
        self.relache(j, K.LALT); self.assertTrue(self.tick(j)['discussion'])               # une seule fois
        self.assertFalse(self.tick(j)['discussion'])
        self.appui(j, K.RALT); self.relache(j, K.RALT); self.assertTrue(self.tick(j)['discussion'])      # Alt Gr aussi

    def test_alt_tab_ne_lance_pas_la_discussion(self):
        K = self.K; j = self.faux_jeu(); self.appui(j, K.LALT)
        j.touches.on_deactivate()                                                          # la fenetre perd le focus : le relachement n'arrive jamais
        self.assertFalse(self.tick(j)['discussion']); self.assertFalse(j.alt_cand)

    def test_menu_pause_ouvert_ou_touche_autre_que_alt(self):
        K = self.K; j = self.faux_jeu(); j.pause.ouvert = True; self.appui(j, K.LALT); self.relache(j, K.LALT)
        self.assertFalse(self.tick(j)['discussion'])                                       # (le menu Echap n'envoie rien au jeu)
        j = self.faux_jeu(); j.reg.lier('discussion', 0, K.G); j.reg.delier('discussion', 1)      # discussion = G seule : au moment de l'appui, comme avant
        self.appui(j, K.G); self.assertTrue(self.tick(j)['discussion']); self.relache(j, K.G)
        self.appui(j, K.LALT); self.relache(j, K.LALT); self.assertFalse(self.tick(j)['discussion'])        # Alt ne sert plus a rien

    def test_capture_de_touche_en_cours(self):
        K = self.K; j = self.faux_jeu(); j.pause.capture = ('A', 0)
        self.assertFalse(j._raccourci_fenetre(K.F11, 0))                                   # la page Commandes attend une touche : F11 lui revient (elle repond « reservee »)
        self.assertEqual(j.bascules, 0)

    def test_pas_de_bascule_pendant_une_bascule(self):
        K = self.K; j = self.faux_jeu(); j._en_bascule = True; self.appui(j, K.F11)
        self.assertEqual(j.bascules, 0); self.assertIn(K.F11, j.avalees)                   # (avalee quand meme : pas de validation)


class FausseFenetre:
    """Les appels que la bascule fait a la fenetre pyglet, dans l'ordre (`journal`), avec l'etat qu'ils changent. `echec` : nom de l'appel qui leve une erreur (une fois)."""
    def __init__(self, FE, plein=False, taille=(1280, 720), bureau=(1920, 1080), echec=None):
        self.journal = []; self.fullscreen = plein; self._visible = True; self.width, self.height = (bureau if plein else taille)
        self.bureau = bureau; self.echec = echec; self._windowed_location = None if plein else (100, 80); self._windowed_size = taille
        self.taille_fenetre = taille; self.mode_fen = 1 if plein else 0; self._pret = True; self._en_bascule = False; self.reg = RG.Reglages(None)
        self.toasts = []; self.post = types.SimpleNamespace(cle=('cle', 1))
        for nom in ('regler_plein_ecran', '_poser_plein_ecran', '_mettre_plein', 'basculer_plein_ecran', '_image_de_bascule'): setattr(self, nom, types.MethodType(getattr(FE.Jeu, nom), self))
        self._echec_simule = FE.Jeu._echec_simule; self.bureau_ = bureau
        self._verifier_taille_reelle = lambda: self.journal.append('verifier')
        self.toast = lambda t, d=3.0: self.toasts.append(t)
        self._journal_fenetre = lambda q: self.journal.append('journal(%s)' % q)

    @property
    def est_plein(self): return self.mode_fen == 1

    def _piege(self, nom):
        self.journal.append(nom)
        if self.echec == nom: self.echec = None; raise RuntimeError('echec de %s' % nom)

    def set_visible(self, v=True): self._piege('visible(%s)' % bool(v)); self._visible = bool(v)

    def set_fullscreen(self, plein=True, *taille):
        self._piege('set_fullscreen(%s%s)' % (bool(plein), ',%dx%d' % taille if taille else ''))
        if not self.fullscreen: self._windowed_size = (self.width, self.height); self._windowed_location = (100, 80)
        self.fullscreen = bool(plein)
        if plein: self.width, self.height = self.bureau
        else: self.width, self.height = (taille if taille else self._windowed_size); self._windowed_location = self._windowed_location or None

    def set_location(self, x, y): self._piege('set_location(%d,%d)' % (x, y)); self._windowed_location = (x, y)

    def switch_to(self): self.journal.append('switch_to')

    def on_draw(self): self.journal.append('on_draw(%dx%d)' % (self.width, self.height))

    def flip(self): self.journal.append('flip')

    def clear(self): self.journal.append('clear')


class Bascule(unittest.TestCase):
    """Vrai code de Jeu.regler_plein_ecran / _poser_plein_ecran sur une fausse fenetre : une seule etape (cachee, un set_fullscreen, une image a la taille definitive, montree), taille memorisee, repli en cas d'echec."""
    @classmethod
    def setUpClass(cls):
        try:
            import fenetre; cls.FE = fenetre
        except Exception as ex: raise unittest.SkipTest('fenetre.py non importable ici (%r)' % (ex,))

    def setUp(self):
        os.environ.pop('DQ_SIM_ECHEC', None); os.environ.pop('DQ_BASCULE_SIMPLE', None)
        self.zone = self.FE.zone_utile; self.FE.zone_utile = lambda: (1904, 1040)          # (un bureau 1920 x 1080 : la taille de l'ecran de test ne compte pas)

    def tearDown(self):
        self.FE.zone_utile = self.zone; os.environ.pop('DQ_SIM_ECHEC', None); os.environ.pop('DQ_BASCULE_SIMPLE', None)

    def fen(self, **k): return FausseFenetre(self.FE, **k)

    def test_vers_le_plein_ecran_en_une_etape(self):
        f = self.fen(); self.assertTrue(f.regler_plein_ecran(True))
        self.assertEqual(f.journal, ['visible(False)', 'set_fullscreen(True)', 'switch_to', 'on_draw(1920x1080)', 'flip', 'visible(True)', 'journal(plein écran)'])
        self.assertEqual((f.mode_fen, f.reg['mode_fenetre'], f.taille_fenetre), (1, 1, (1280, 720)))         # (la taille de la fenetre est gardee pour le retour)
        self.assertEqual(f.post.cle, ('cle', 1))                                                              # (les tampons du rendu hors ecran ne sont pas invalides de force : refaits seulement si la taille change)

    def test_retour_en_fenetre_en_une_etape_a_la_taille_memorisee(self):
        f = self.fen(); f.regler_plein_ecran(True); f.journal.clear(); self.assertFalse(f.regler_plein_ecran(False))
        self.assertEqual(f.journal, ['visible(False)', 'set_fullscreen(False,1280x720)', 'switch_to', 'on_draw(1280x720)', 'flip', 'visible(True)', 'journal(fenêtre)'])
        self.assertEqual((f.mode_fen, f.reg['mode_fenetre'], f.width, f.height), (0, 0, 1280, 720))

    def test_aucun_set_fullscreen_double(self):
        f = self.fen()
        for i in range(6): f.basculer_plein_ecran()
        self.assertEqual(sum(1 for e in f.journal if e.startswith('set_fullscreen')), 6)                      # un seul par bascule, jamais « fenetre puis plein ecran »
        self.assertEqual(sum(1 for e in f.journal if e == 'visible(False)'), sum(1 for e in f.journal if e == 'visible(True)'))      # fenetre toujours remontree

    def test_deja_dans_le_mode_demande(self):
        f = self.fen(); f.regler_plein_ecran(False); self.assertEqual(f.journal, []); self.assertEqual(f.reg['mode_fenetre'], 0)

    def test_taille_trop_grande_ramenee_a_l_ecran(self):
        f = self.fen(plein=True, taille=(1280, 720)); f.taille_fenetre = (7680, 4320); f.regler_plein_ecran(False)
        w, h = self.FE.ajuster_taille(7680, 4320)
        self.assertIn('set_fullscreen(False,%dx%d)' % (w, h), f.journal)

    def test_lancee_en_plein_ecran_la_fenetre_est_centree_au_retour(self):
        f = self.fen(plein=True); f.regler_plein_ecran(False)
        self.assertIn('set_location(320,180)', f.journal)                                                     # 1920 x 1080 : fenetre 1280 x 720 au centre du bureau
        f = self.fen(); f.regler_plein_ecran(True); f.journal.clear(); f.regler_plein_ecran(False)
        self.assertFalse([e for e in f.journal if e.startswith('set_location') and e != 'set_location(100,80)'])      # position memorisee par la fenetre : gardee (pas de recentrage)

    def test_echec_du_plein_ecran_etat_de_depart_garde(self):
        os.environ['DQ_SIM_ECHEC'] = '1'
        f = self.fen(); self.assertFalse(f.regler_plein_ecran(True))
        self.assertFalse(f.fullscreen); self.assertTrue(f._visible); self.assertEqual((f.mode_fen, f.reg['mode_fenetre']), (0, 0))
        self.assertEqual(f.toasts, ['Plein écran impossible'])
        self.assertEqual([e for e in f.journal if e.startswith('set_fullscreen')], ['set_fullscreen(True)', 'set_fullscreen(False,1280x720)'])      # (changement puis retour a l'etat de depart)
        self.assertEqual(f.journal[-3:], ['flip', 'visible(True)', 'journal(fenêtre)'])                       # (une image complete est montree)

    def test_echec_du_retour_en_fenetre_reste_en_plein_ecran(self):
        f = self.fen(); f.regler_plein_ecran(True); os.environ['DQ_SIM_ECHEC'] = '0'
        self.assertTrue(f.regler_plein_ecran(False)); self.assertTrue(f.fullscreen); self.assertTrue(f._visible); self.assertEqual((f.mode_fen, f.reg['mode_fenetre']), (1, 1))
        self.assertEqual(f.toasts, ['Fenêtre impossible'])

    def test_erreur_de_la_fenetre_pyglet(self):
        for appel in ('set_fullscreen(True)', 'visible(False)'):
            f = self.fen(echec=appel); f.regler_plein_ecran(True)
            self.assertFalse(f.fullscreen, appel); self.assertTrue(f._visible, appel); self.assertEqual((f.mode_fen, f.reg['mode_fenetre']), (0, 0), appel)
            self.assertEqual(len(f.toasts), 1, appel)
            f.regler_plein_ecran(True); self.assertTrue(f.fullscreen, appel)                                 # (l'essai suivant fonctionne)

    def test_pas_de_bascule_pendant_une_bascule(self):
        f = self.fen(); f._en_bascule = True; self.assertFalse(f.regler_plein_ecran(True)); self.assertEqual(f.journal, [])

    def test_bascule_simple_de_debogage(self):
        os.environ['DQ_BASCULE_SIMPLE'] = '1'
        f = self.fen(); f.regler_plein_ecran(True); self.assertEqual(f.journal, ['set_fullscreen(True)', 'journal(plein écran)'])


class PageAffichage(unittest.TestCase):
    """Page Affichage du menu Echap : ordre voulu, ligne « Plein écran » = simple interrupteur Oui / Non, « Résolution » grisee en plein ecran, plus de « Lissage des textures » ni de « Correction des bords des sprites »."""
    ORDRE = ['Plein écran', 'Résolution', 'Netteté', 'Shader', 'Effet de vignetage', 'Anticrénelage', 'Suréchantillonnage', 'Luminosité', 'Distance caméra', 'Centrer la caméra sur le joueur', 'Interface']

    @classmethod
    def setUpClass(cls):
        try: import pause
        except Exception as ex: raise unittest.SkipTest('pause.py non importable ici (%r)' % (ex,))
        cls.PA = pause

    def page(self, plein, reg=None):
        reg = reg or RG.Reglages(None); reg['mode_fenetre'] = int(plein); appels = []
        J = types.SimpleNamespace(reg=reg, mode_fen=int(plein), mode=4, zoom=1.0, post=types.SimpleNamespace(max_msaa=None), est_plein=plein,
                                  resolutions=lambda: [(1280, 720), (1920, 1080)], resolution_courante=lambda: (1920, 1080),
                                  regler_resolution=lambda v: appels.append(('res', v)), regler_plein_ecran=lambda v: appels.append(('plein', v)),
                                  regler_mode=lambda v: None, regler_distance=lambda v: None)
        return self.PA.Pause(J)._e_affichage(), appels

    def test_ordre(self):
        for plein in (False, True):
            e, _ = self.page(plein); self.assertEqual([x['l'] for x in e], self.ORDRE, 'plein %s' % plein)

    def test_ligne_plein_ecran_est_un_interrupteur(self):
        for plein in (False, True):
            e, appels = self.page(plein); f = e[0]
            self.assertEqual((f['t'], f['vals'], f['sw'], f['v']()), ('choix', [False, True], True, 'Oui' if plein else 'Non'))      # interrupteur Oui / Non, pas une liste deroulante
            self.assertTrue(f['aide'])
            f['ok'](); self.assertEqual(appels[-1], ('plein', not plein))                        # Entree / clic bascule (Jeu.regler_plein_ecran)
            n = len(appels); (f['moins'] if plein else f['plus'])(); self.assertEqual(appels[n:], [('plein', not plein)])      # gauche = Non, droite = Oui
            n = len(appels); (f['plus'] if plein else f['moins'])(); self.assertEqual(len(appels), n)                        # (deja dans cet etat : rien)

    def test_resolution_grisee_en_plein_ecran(self):
        for plein in (False, True):
            e, appels = self.page(plein); r = e[1]
            self.assertEqual(bool(r['off']), plein, 'plein %s' % plein)
            self.assertEqual(bool(r['note']()), plein)                                         # (la note rouge explique pourquoi)
            r['plus'](); self.assertEqual(len(appels), 0 if plein else 1)                      # grisee : les fleches ne changent rien

    def test_plus_d_options_lissage_ni_correction_des_bords(self):
        e, _ = self.page(False)
        for x in e: self.assertNotIn(x['l'], ('Lissage des textures', 'Correction des bords des sprites', 'Fenêtre'))

    def test_plein_ecran_et_interface_aux_extremites(self):
        e, _ = self.page(False); self.assertEqual((e[0]['l'], e[-1]['l']), ('Plein écran', 'Interface'))


class CodeRetire(unittest.TestCase):
    """Le plein ecran exclusif, l'option « Correction des bords des sprites » et l'option « Lissage des textures » ne sont plus nulle part dans le code (il reste leurs interrupteurs de debogage : variables d'environnement)."""
    @classmethod
    def setUpClass(cls):
        try: import fenetre; cls.FE = fenetre
        except Exception as ex: raise unittest.SkipTest('fenetre.py non importable ici (%r)' % (ex,))

    def test_fenetre(self):
        FE = self.FE
        for nom in ('choisir_mode_ecran',): self.assertFalse(hasattr(FE, nom), nom)
        for nom in ('regler_mode_fenetre', '_poser_mode', 'basculer_exclusif', 'modes_ecran', '_mode_applique', '_restaurer_affichage', '_restaurer_a_la_sortie', 'regler_lissage'): self.assertFalse(hasattr(FE.Jeu, nom), nom)
        for nom in ('regler_plein_ecran', 'basculer_plein_ecran', '_poser_plein_ecran', '_raccourci_fenetre'): self.assertTrue(hasattr(FE.Jeu, nom), nom)

    def test_lecture_des_reglages_retires(self):
        """Aucune lecture de `reg['lissage']` / `reg['correction_bords']` / `reg['mode_fenetre_retour']` dans le code."""
        import re
        for fich in ('fenetre.py', 'pause.py', 'postfx.py', 'decors_plats.py', 'reglages.py'):
            with open(os.path.join(ICI, '..', 'dq4_pc', fich), encoding='utf-8') as fh: src = fh.read()
            self.assertIsNone(re.search(r"\[\s*'(lissage|correction_bords|mode_fenetre_retour)'\s*\]", src), fich)
            self.assertNotIn("'lissage':", src, fich); self.assertNotIn("'correction_bords':", src, fich)

    def test_lissage_et_correction_toujours_actifs(self):
        FE = self.FE; j = types.SimpleNamespace(args=types.SimpleNamespace(), reg=RG.Reglages(None))
        os.environ.pop('DQ_CORRECTION_BORDS', None)
        self.assertEqual(FE.Jeu._correction_bords(j), 1.0)                                                    # complete, sans reglage
        j.reg.v['correction_bords'] = False; self.assertEqual(FE.Jeu._correction_bords(j), 1.0)                # (un ancien reglage n'y change rien)
        os.environ['DQ_CORRECTION_BORDS'] = '0'
        try: self.assertEqual(FE.Jeu._correction_bords(j), 0.0)                                              # interrupteur de debogage
        finally: os.environ.pop('DQ_CORRECTION_BORDS', None)
        j.args.correction_bords = 40; self.assertAlmostEqual(FE.Jeu._correction_bords(j), 0.4)


if __name__ == '__main__':
    unittest.main(verbosity=2)
