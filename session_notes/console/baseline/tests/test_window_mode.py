"""Test des deux modes de la fenetre (fenetre, plein ecran) : reglage `mode_fenetre` (bornes, migration de l'ancien booleen `full_screen` et de l'ancien plein ecran exclusif, cles abandonnees), raccourcis F11 et Alt + Entree
(vrai code de Game.on_key_press / on_key_release / _fronts sur un faux Jeu), bascule en une seule etape (vrai code de Game.set_full_screen / _set_full_screen sur une fausse fenetre : ordre des appels, retour a l'etat de depart en cas
d'echec), ordre et grisage des lignes de la page Affichage du menu Echap (interrupteur « Plein écran », plus de « Lissage des textures » ni de « Correction des bords des sprites »). Aucune vraie fenetre n'est ouverte.

    python3 tools/test_window_mode.py
"""
import json, os, sys, tempfile, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from dq4_pc import language as _LANGUAGE; _LANGUAGE.select_language('fr')          # (D-238 : ces tests attendent les textes francais, quelle que soit la langue de l'ordinateur)
import _paths          # (aide des tests : retrouver le code source dans les sous-dossiers de dq4_pc)
from dq4_pc.persistence import settings as RG


def load(content):
    f = os.path.join(tempfile.mkdtemp(prefix='rg_test_'), 'settings.json')
    with open(f, 'w', encoding='utf-8') as fh: json.dump(content, fh)
    return RG.Settings(f), f


class WindowModeSetting(unittest.TestCase):
    def test_default(self):
        r = RG.Settings(None)
        self.assertEqual(r['mode_fenetre'], 0)
        for k in RG.OBSOLETE_KEYS: self.assertNotIn(k, r.v, k)

    def test_old_boolean_migration(self):
        r, _ = load({'plein_ecran': True}); self.assertEqual(r['mode_fenetre'], 1)          # l'ancien plein ecran = fenetre sans bordure : le mode 1
        r, _ = load({'plein_ecran': False}); self.assertEqual(r['mode_fenetre'], 0)
        r, _ = load({'son': False}); self.assertEqual(r['mode_fenetre'], 0)                  # ni l'un ni l'autre : fenetre
        r, _ = load({'plein_ecran': 'oui'}); self.assertEqual(r['mode_fenetre'], 0)          # valeur absurde
        r, _ = load({'plein_ecran': True, 'mode_fenetre': 1}); self.assertEqual(r['mode_fenetre'], 1)
        r, _ = load({'plein_ecran': True, 'mode_fenetre': 0}); self.assertEqual(r['mode_fenetre'], 0)      # le nouveau reglage prime

    def test_old_exclusive_fullscreen_becomes_fullscreen(self):
        r, _ = load({'mode_fenetre': 2}); self.assertEqual(r['mode_fenetre'], 1)
        r, _ = load({'mode_fenetre': 2, 'mode_fenetre_retour': 0, 'plein_ecran': False}); self.assertEqual(r['mode_fenetre'], 1)       # (le dernier mode non exclusif de la #42 est abandonne)
        r, _ = load({'mode_fenetre': 2.0}); self.assertEqual(r['mode_fenetre'], 1)

    def test_bounds(self):
        for raw_value, expected in ((0, 0), (1, 1), (2, 1), (3, 0), (-1, 0), (1.5, 0), (2.0, 1), ('x', 0), ('2', 0), (None, 0), ([1], 0), (True, 1), (False, 0), (float('nan'), 0), (float('inf'), 0)):
            r, _ = load({'mode_fenetre': raw_value}); self.assertEqual(r['mode_fenetre'], expected, repr(raw_value))
            self.assertEqual(RG.valid_window_mode(raw_value), expected, repr(raw_value))

    def test_no_more_exclusive_full_screen_symbols(self):
        for name_str in ('MODES_FENETRE', 'NOMS_MODES_FENETRE'): self.assertFalse(hasattr(RG, name_str), name_str)

    def test_abandoned_keys_neither_read_nor_written(self):
        """`mode_fenetre_retour` (#42), `edge_correction` et `smoothing` (options retirees), `full_screen` (booleen d'avant la #42) : un ancien fichier les contient, ils sont ignores puis disparaissent a la sauvegarde ; le reste est garde."""
        r, f = load({'plein_ecran': True, 'mode_fenetre_retour': 1, 'correction_bords': False, 'lissage': False, 'volume_musique': 0.4, 'msaa': 8})
        for k in RG.OBSOLETE_KEYS: self.assertNotIn(k, r.v, k)
        self.assertEqual((r['mode_fenetre'], r['volume_musique'], r['msaa']), (1, 0.4, 8))
        r.store()
        with open(f, encoding='utf-8') as fh: raw_value = json.load(fh)
        for k in RG.OBSOLETE_KEYS: self.assertNotIn(k, raw_value, k)
        r2 = RG.Settings(f); self.assertEqual((r2['mode_fenetre'], r2['volume_musique'], r2['msaa']), (1, 0.4, 8))

    def test_round_trip(self):
        r, f = load({'mode_fenetre': 2, 'volume_musique': 0.4})
        r['mode_fenetre'] = 0; r.store(); self.assertEqual(RG.Settings(f)['mode_fenetre'], 0)
        r['mode_fenetre'] = 1; r.store(); self.assertEqual(RG.Settings(f)['mode_fenetre'], 1)

    def test_f11_removed_from_old_file(self):
        r, _ = load({'touches_v': 4, 'touches': {'infos': ['F11', None], 'carte': ['M', 'F11']}})
        self.assertEqual(r['touches']['infos'], [None, None]); self.assertEqual(r['touches']['carte'], ['M', None])      # (F11 n'est plus une touche d'action)

    def test_f11_not_remappable(self):
        self.assertIn('F11', RG.RESERVED); self.assertIn('ESCAPE', RG.RESERVED)
        self.assertFalse(any('F11' in ts for ts in RG.DEFAULT_KEYS.values()))                    # (F11 n'etait pas une touche du jeu)


class Shortcuts(unittest.TestCase):
    """F11 et Alt + Entree (vrai code de Game.on_key_press / on_key_release / _fronts sur un faux Jeu, sans fenetre) : bascule, Entree avalee, discussion de groupe (Alt) au relachement d'Alt seul."""
    @classmethod
    def setUpClass(cls):
        try: from dq4_pc.window import game as window; import pyglet; cls.WND = window; cls.K = pyglet.window.key; cls.pyglet = pyglet
        except Exception as ex: raise unittest.SkipTest('window.py non importable ici (%r)' % (ex,))

    def fake_game(self):
        WND = self.WND
        j = types.SimpleNamespace(swallowed=set(), alt_cand=False, alt_tap=False, reg=RG.Settings(None), key_list=self.K.KeyStateHandler(), prev_action={}, n=0, _ready=True, combo=[False, False], _logo_touched=False, appuis_pause=0, appuis_nom=0,
                                  pause=None, _toggling=False, post=object(), saves_screen=None, license_panel=None, last_device='', bascules=0, annulations=0, is_fullscreen=False,
                                  mouse=(0, 0), mouse_guard=__import__('dq4_pc.window.inputs', fromlist=['MouseGuard']).MouseGuard())          # (souris / mouse_guard : Game.on_key_press memorise la position du pointeur a chaque touche)
        j.pause = types.SimpleNamespace(opened=False, capture=None, key_press=lambda sym, mods: setattr(j, 'appuis_pause', j.appuis_pause + 1))
        j.name_entry = types.SimpleNamespace(key_press=lambda sym, mods: setattr(j, 'appuis_nom', j.appuis_nom + 1))
        j.toggle_full_screen = lambda: setattr(j, 'bascules', j.bascules + 1)
        j._held = lambda a: WND.Game._held(j, a); j._name_entry_in_progress = lambda: False; j._state_number = WND.Game._state_number; j._window_shortcut = lambda sym, mods: WND.Game._window_shortcut(j, sym, mods)
        j.cancel_loading = lambda: setattr(j, 'annulations', j.annulations + 1)
        return j

    def press_state(self, j, sym):
        mods = self.K.MOD_ALT if j.key_list[self.K.LALT] or j.key_list[self.K.RALT] else 0
        j.key_list.on_key_press(sym, mods); return self.WND.Game.on_key_press(j, sym, mods)

    def release(self, j, sym):
        j.key_list.on_key_release(sym, 0); self.WND.Game.on_key_release(j, sym, 0)

    def tick(self, j): return self.WND.Game._edges(j)

    def test_f11_toggles_and_is_not_an_action(self):
        K = self.K; j = self.fake_game(); self.press_state(j, K.F11)
        self.assertEqual(j.bascules, 1); self.assertIn(K.F11, j.swallowed)
        j.reg['touches']['infos'][0] = 'F11'; j.reg.codes_cache = {}                       # (un ancien fichier qui lie F11 a une action : elle ne part pas)
        self.assertFalse(j._held('infos'))
        self.release(j, K.F11); self.assertNotIn(K.F11, j.swallowed)

    def test_alt_enter_toggles_without_validating_or_chat(self):
        K = self.K; j = self.fake_game()
        self.press_state(j, K.LALT); self.assertTrue(j.alt_cand)
        self.assertFalse(self.tick(j)['discussion'])                                       # Alt tenue : rien tant qu'il n'est pas relache
        self.press_state(j, K.RETURN)
        self.assertEqual(j.bascules, 1); self.assertFalse(j.alt_cand)
        fr = self.tick(j); self.assertFalse(fr['menu']); self.assertFalse(j._held('menu'))      # Entree avalee : ni validation, ni menu
        self.release(j, K.RETURN); self.release(j, K.LALT)
        self.assertFalse(self.tick(j)['discussion']); self.assertFalse(j.alt_tap)          # Alt relache apres Alt + Entree : pas de discussion de groupe
        self.press_state(j, K.RETURN); self.assertTrue(self.tick(j)['menu'])                     # (Entree seule fonctionne de nouveau)
        self.assertEqual(j.bascules, 1)

    def test_numpad_enter_and_alt_gr(self):
        K = self.K; j = self.fake_game(); self.press_state(j, K.RALT); self.press_state(j, K.ENTER)
        self.assertEqual(j.bascules, 1); self.release(j, K.ENTER); self.release(j, K.RALT); self.assertFalse(self.tick(j)['discussion'])

    def test_alt_enter_without_system_flag(self):
        """Le drapeau MOD_ALT de l'evenement peut manquer (Alt deja enfoncee avant le focus, clavier particulier) : l'etat des touches Alt suffit."""
        K = self.K; j = self.fake_game(); j.key_list.on_key_press(K.LALT, 0)
        self.WND.Game.on_key_press(j, K.RETURN, 0); self.assertEqual(j.bascules, 1)

    def test_enter_alone_does_not_toggle(self):
        K = self.K; j = self.fake_game(); self.press_state(j, K.RETURN); self.assertEqual(j.bascules, 0); self.assertTrue(self.tick(j)['menu'])
        self.press_state(j, K.LALT); self.assertEqual(j.bascules, 0)                             # (Alt seule non plus)

    def test_in_all_contexts(self):
        """Menu Echap ouvert, saisie du nom, logos d'entree : F11 et Alt + Entree basculent et ne sont transmis ni au menu, ni a la saisie, ni aux logos (qui s'ignorent d'un appui)."""
        K = self.K
        j = self.fake_game(); j.pause.opened = True; self.press_state(j, K.F11); self.press_state(j, K.LALT); self.assertEqual((j.bascules, j.appuis_pause), (1, 1))      # (Alt seule arrive au menu)
        self.press_state(j, K.RETURN); self.assertEqual((j.bascules, j.appuis_pause), (2, 1))                    # Alt + Entree : bascule, pas de touche Entree pour le menu
        self.release(j, K.RETURN); self.release(j, K.LALT); self.press_state(j, K.RETURN); self.assertEqual((j.bascules, j.appuis_pause), (2, 2))      # Entree seule y arrive
        j = self.fake_game(); j._name_entry_in_progress = lambda: True; self.press_state(j, K.F11); self.assertEqual((j.bascules, j.appuis_nom), (1, 0))
        j = self.fake_game(); j._ready = False; self.press_state(j, K.F11); self.assertEqual((j.bascules, j._logo_touched), (1, False))      # (un appui sur une autre touche saute les logos, pas F11)
        self.press_state(j, K.SPACE); self.assertTrue(j._logo_touched)

    def test_alt_alone_triggers_chat_on_release(self):
        K = self.K; j = self.fake_game()
        self.press_state(j, K.LALT); self.assertFalse(self.tick(j)['discussion'])
        self.release(j, K.LALT); self.assertTrue(self.tick(j)['discussion'])               # une seule fois
        self.assertFalse(self.tick(j)['discussion'])
        self.press_state(j, K.RALT); self.release(j, K.RALT); self.assertTrue(self.tick(j)['discussion'])      # Alt Gr aussi

    def test_alt_tab_does_not_start_chat(self):
        K = self.K; j = self.fake_game(); self.press_state(j, K.LALT)
        j.key_list.on_deactivate()                                                          # la fenetre perd le focus : le relachement n'arrive jamais
        self.assertFalse(self.tick(j)['discussion']); self.assertFalse(j.alt_cand)

    def test_pause_menu_opened_or_key_other_than_alt(self):
        K = self.K; j = self.fake_game(); j.pause.opened = True; self.press_state(j, K.LALT); self.release(j, K.LALT)
        self.assertFalse(self.tick(j)['discussion'])                                       # (le menu Echap n'envoie rien au jeu)
        j = self.fake_game(); j.reg.bind('discussion', 0, K.G); j.reg.unbind('discussion', 1)      # discussion = G seule : au moment de l'appui, comme avant
        self.press_state(j, K.G); self.assertTrue(self.tick(j)['discussion']); self.release(j, K.G)
        self.press_state(j, K.LALT); self.release(j, K.LALT); self.assertFalse(self.tick(j)['discussion'])        # Alt ne sert plus a rien

    def test_key_capture_in_progress(self):
        K = self.K; j = self.fake_game(); j.pause.capture = ('A', 0)
        self.assertFalse(j._window_shortcut(K.F11, 0))                                   # la page Commandes attend une touche : F11 lui revient (elle repond « reservee »)
        self.assertEqual(j.bascules, 0)

    def test_no_toggle_during_toggle(self):
        K = self.K; j = self.fake_game(); j._toggling = True; self.press_state(j, K.F11)
        self.assertEqual(j.bascules, 0); self.assertIn(K.F11, j.swallowed)                   # (avalee quand meme : pas de validation)


class FakeScreen:
    """Un moniteur de pyglet (x, y, width, height, name, is_primary)."""
    def __init__(self, x, y, w, h, name_str='', main=False, stale=False): self.x, self.y, self.width, self.height, self.name, self.is_primary, self.stale = x, y, w, h, name_str, main, stale          # perime : sa poignee Windows n'est plus valable (apres un branchement d'ecran)
    def get_monitor_name(self): return self.name


class FakeWindow:
    """Les appels que la bascule fait a la fenetre pyglet, dans l'ordre (`logfile`), avec l'etat qu'ils changent. `failure` : nom de l'appel qui leve une erreur (une fois). `screens` : les moniteurs (FakeScreen ; defaut : un seul,
    le bureau) ; `screen_page` : celui de la fenetre pour pyglet (`screen`, defaut le premier)."""
    def __init__(self, WND, full=False, size_value=(1280, 720), desktop=(1920, 1080), failure=None, screens=None, screen_page=0):
        self.logfile = []; self.fullscreen = full; self._visible = True
        self._screens = screens or [FakeScreen(0, 0, desktop[0], desktop[1], main=True)]; self._screen = self._screens[screen_page]
        self.display = types.SimpleNamespace(get_screens=lambda: list(self._screens)); self.width, self.height = ((self.screen.width, self.screen.height) if full else size_value)
        self.desktop = desktop; self.failure = failure; self._windowed_location = None if full else (100, 80); self._windowed_size = size_value
        self.window_size = size_value; self.win_mode = 1 if full else 0; self._ready = True; self._toggling = False; self.reg = RG.Settings(None)
        self.post = types.SimpleNamespace(lookup_key=('cle', 1))
        for name_str in ('set_full_screen', '_set_full_screen', '_apply_full_screen', 'toggle_full_screen', '_toggle_frame', '_read_screens', '_window_screen_index', '_screen_for_fullscreen', '_already_on', '_note_full_zone', '_note_toggle_failure', '_refresh_screen'): setattr(self, name_str, types.MethodType(getattr(WND.Game, name_str), self))
        self._simulated_failure = WND.Game._simulated_failure; self.desktop_ = desktop
        self._check_real_size = lambda: self.logfile.append('verifier')
        self._log_window = lambda q: self.logfile.append('journal(%s)' % q)

    @property
    def is_fullscreen(self): return self.win_mode == 1

    @property
    def screen(self): return self._screen          # (pyglet : BaseWindow.screen renvoie _screen)

    def _trap(self, name_str):
        self.logfile.append(name_str)
        if self.failure == name_str: self.failure = None; raise RuntimeError('echec de %s' % name_str)

    def set_visible(self, v=True): self._trap('visible(%s)' % bool(v)); self._visible = bool(v)

    def get_location(self): return (self.screen.x, self.screen.y) if self.fullscreen else (self._windowed_location or (0, 0))

    def set_fullscreen(self, fullscreen=True, screen=None, mode=None, width=None, height=None):
        """La signature de pyglet 2.1 : (fullscreen, screen, mode, width, height)."""
        size_value = (width, height) if width is not None else ()
        self._trap('set_fullscreen(%s%s%s)' % (bool(fullscreen), ',%dx%d' % size_value if size_value else '', ',écran %d' % (self._screens.index(screen) + 1) if screen is not None else ''))
        if not self.fullscreen: self._windowed_size = (self.width, self.height); self._windowed_location = self._windowed_location or (100, 80)
        self.fullscreen = bool(fullscreen)
        if fullscreen:
            if screen is not None: self._screen = screen
            self.width, self.height = self.screen.width, self.screen.height
        else: self.width, self.height = (size_value if size_value else self._windowed_size); self._windowed_location = self._windowed_location or None
        if self._screen.stale: raise OSError(9, 'Descripteur non valide', None, -2147024890)          # (Win32Window._create : Screen.get_dpi -> GetDpiForMonitor sur une poignee qui n'est plus valable ; l'etat a deja change, comme dans pyglet)

    def set_location(self, x, y): self._trap('set_location(%d,%d)' % (x, y)); self._windowed_location = (x, y)

    def switch_to(self): self.logfile.append('switch_to')

    def on_draw(self): self.logfile.append('on_draw(%dx%d)' % (self.width, self.height))

    def flip(self): self.logfile.append('flip')

    def clear(self): self.logfile.append('clear')


class Toggle(unittest.TestCase):
    """Vrai code de Game.set_full_screen / _set_full_screen sur une fausse fenetre : une seule etape (cachee, un set_fullscreen, une image a la taille definitive, montree), taille memorisee, repli en cas d'echec."""
    @classmethod
    def setUpClass(cls):
        try:
            from dq4_pc.window import game as window; cls.WND = window
        except Exception as ex: raise unittest.SkipTest('window.py non importable ici (%r)' % (ex,))

    def failures(self):
        """Nombre d'echecs de bascule notes dans le journal des erreurs (depuis #267 la fenetre n'affiche plus de message : console et journal seulement)."""
        try:
            with open(self.errors_logfile, encoding='utf-8') as fh: return fh.read().count('impossible ---')
        except OSError: return 0

    def setUp(self):
        os.environ.pop('DQ_SIM_ECHEC', None); os.environ.pop('DQ_BASCULE_SIMPLE', None)
        self.errors_logfile = os.path.join(tempfile.mkdtemp(prefix='journal_fenetre_'), 'window_errors.log'); os.environ['DQ_JOURNAL_FENETRE'] = self.errors_logfile          # (les echecs simules ne s'ecrivent pas dans le depot)
        self.zone = self.WND.useful_zone; self.WND.useful_zone = lambda: (1904, 1040)          # (un bureau 1920 x 1080 : la taille de l'ecran de test ne compte pas)

    def tearDown(self):
        self.WND.useful_zone = self.zone; os.environ.pop('DQ_SIM_ECHEC', None); os.environ.pop('DQ_BASCULE_SIMPLE', None); os.environ.pop('DQ_JOURNAL_FENETRE', None)

    def win(self, **k): return FakeWindow(self.WND, **k)

    def test_to_full_screen_in_one_step(self):
        f = self.win(); self.assertTrue(f.set_full_screen(True))
        self.assertEqual(f.logfile, ['visible(False)', 'set_fullscreen(True)', 'switch_to', 'on_draw(1920x1080)', 'flip', 'visible(True)', 'switch_to', 'on_draw(1920x1080)', 'flip', 'journal(plein écran)'])
        self.assertEqual((f.win_mode, f.reg['mode_fenetre'], f.window_size), (1, 1, (1280, 720)))         # (la taille de la fenetre est gardee pour le retour)
        self.assertEqual(f.post.lookup_key, ('cle', 1))                                                              # (les tampons du rendu hors ecran ne sont pas invalides de force : refaits seulement si la taille change)

    def test_return_to_window_in_one_step_at_remembered_size(self):
        f = self.win(); f.set_full_screen(True); f.logfile.clear(); self.assertFalse(f.set_full_screen(False))
        self.assertEqual(f.logfile, ['visible(False)', 'set_fullscreen(False,1280x720)', 'switch_to', 'on_draw(1280x720)', 'flip', 'visible(True)', 'switch_to', 'on_draw(1280x720)', 'flip', 'journal(fenêtre)'])
        self.assertEqual((f.win_mode, f.reg['mode_fenetre'], f.width, f.height), (0, 0, 1280, 720))

    def test_no_double_set_fullscreen(self):
        f = self.win()
        for i in range(6): f.toggle_full_screen()
        self.assertEqual(sum(1 for e in f.logfile if e.startswith('set_fullscreen')), 6)                      # un seul par bascule, jamais « fenetre puis plein ecran »
        self.assertEqual(sum(1 for e in f.logfile if e == 'visible(False)'), sum(1 for e in f.logfile if e == 'visible(True)'))      # fenetre toujours remontree

    def test_already_in_requested_mode(self):
        f = self.win(); f.set_full_screen(False); self.assertEqual(f.logfile, []); self.assertEqual(f.reg['mode_fenetre'], 0)

    def test_too_large_size_clamped_to_the_screen(self):
        f = self.win(full=True, size_value=(1280, 720)); f.window_size = (7680, 4320); f.set_full_screen(False)
        w, h = self.WND.adjust_size(7680, 4320)
        self.assertIn('set_fullscreen(False,%dx%d)' % (w, h), f.logfile)

    def test_launched_full_screen_window_is_centered_on_return(self):
        f = self.win(full=True); f.set_full_screen(False)
        self.assertIn('set_location(320,180)', f.logfile)                                                     # 1920 x 1080 : fenetre 1280 x 720 au centre du bureau
        f = self.win(); f.set_full_screen(True); f.logfile.clear(); f.set_full_screen(False)
        self.assertFalse([e for e in f.logfile if e.startswith('set_location') and e != 'set_location(100,80)'])      # position memorisee par la fenetre : gardee (pas de recentrage)

    def test_full_screen_failure_keeps_initial_state(self):
        os.environ['DQ_SIM_ECHEC'] = '1'
        f = self.win(); self.assertFalse(f.set_full_screen(True))
        self.assertFalse(f.fullscreen); self.assertTrue(f._visible); self.assertEqual((f.win_mode, f.reg['mode_fenetre']), (0, 0))
        self.assertEqual(self.failures(), 1)
        self.assertEqual([e for e in f.logfile if e.startswith('set_fullscreen')], ['set_fullscreen(True)', 'set_fullscreen(False,1280x720)'])      # (changement puis retour a l'etat de depart)
        self.assertEqual(f.logfile[-6:], ['flip', 'visible(True)', 'switch_to', 'on_draw(1280x720)', 'flip', 'journal(fenêtre)'])                       # (une image complete est dessinee avant et apres l'affichage de la fenetre)

    def test_return_to_window_failure_stays_full_screen(self):
        f = self.win(); f.set_full_screen(True); os.environ['DQ_SIM_ECHEC'] = '0'
        self.assertTrue(f.set_full_screen(False)); self.assertTrue(f.fullscreen); self.assertTrue(f._visible); self.assertEqual((f.win_mode, f.reg['mode_fenetre']), (1, 1))
        self.assertEqual(self.failures(), 1)

    def test_full_error_is_noted_in_the_log(self):
        """Issue #123 : la ligne « Fenêtre impossible (...) » ne dit pas ou ca a echoue : la pile d'appels complete, l'etat de la fenetre et des moniteurs vont dans window_errors.log (et la console)."""
        f = self.win(full=True, failure='set_fullscreen(False,1280x720)'); self.assertTrue(f.set_full_screen(False))      # (l'echec est unique : le retour a l'etat de depart reussit)
        self.assertEqual(self.failures(), 1)
        txt = open(self.errors_logfile, encoding='utf-8').read()
        self.assertIn('passage en fenêtre impossible', txt); self.assertIn('Traceback', txt); self.assertIn('RuntimeError', txt); self.assertIn('echec de set_fullscreen(False,1280x720)', txt)
        self.assertIn('_apply_full_screen', txt)                                                                          # la pile : ou ca a echoue
        self.assertIn('fenêtre : plein écran = ', txt); self.assertIn('moniteurs : 1920 x 1080 en (0, 0) (principal)', txt); self.assertIn('pyglet ', txt)
        f2 = self.win(full=True, failure='visible(False)'); f2.set_full_screen(False)
        self.assertEqual(open(self.errors_logfile, encoding='utf-8').read().count('impossible ---'), 2)             # (une entree de plus, a la suite : le journal n'est jamais ecrase)

    def test_a_log_error_does_not_hinder_the_toggle(self):
        os.environ['DQ_JOURNAL_FENETRE'] = os.path.join(self.errors_logfile, 'dossier', 'inexistant', 'x.log')       # (inecrivable)
        f = self.win(full=True, failure='set_fullscreen(False,1280x720)'); self.assertTrue(f.set_full_screen(False))
        self.assertTrue(f.fullscreen)

    def test_no_entry_without_failure(self):
        f = self.win(); f.set_full_screen(True); f.set_full_screen(False); self.assertFalse(os.path.exists(self.errors_logfile))

    def test_pyglet_window_error(self):
        for k, call in enumerate(('set_fullscreen(True)', 'visible(False)'), 1):
            f = self.win(failure=call); f.set_full_screen(True)
            self.assertFalse(f.fullscreen, call); self.assertTrue(f._visible, call); self.assertEqual((f.win_mode, f.reg['mode_fenetre']), (0, 0), call)
            self.assertEqual(self.failures(), k, call)                                                          # (un echec de plus a chaque essai)
            f.set_full_screen(True); self.assertTrue(f.fullscreen, call)                                 # (l'essai suivant fonctionne)

    # ---- #126 : un ecran branche pendant que la fenetre existe rend la poignee du moniteur de pyglet invalide
    def stale_win(self, full=True, **k):
        """Une fenetre dont le moniteur gardé par pyglet (`_screen`) est perime (meme position et memes dimensions que le moniteur 1 de la liste neuve) : un second ecran vient d'etre branche."""
        main = FakeScreen(0, 0, 1920, 1200, main=True); external = FakeScreen(-331, -1440, 2560, 1440)
        f = self.win(full=full, screens=[main, external], **k); f._screen = FakeScreen(0, 0, 1920, 1200, main=True, stale=True)
        return f, main, external

    def test_stale_fake_monitor_reproduces_windows_error(self):
        f, _, _ = self.stale_win()
        with self.assertRaises(OSError) as c: f.set_fullscreen(False, width=1280, height=720)
        self.assertEqual(c.exception.errno, 9)

    def test_full_screen_then_external_screen_plugged_in_back_to_window(self):
        """Le cas de Sylfried (03/11/2026, 23 h 08) : plein ecran, ecran externe branche, passage en fenetre : marche."""
        f, main, _ = self.stale_win()
        self.assertFalse(f.set_full_screen(False))
        self.assertFalse(f.fullscreen); self.assertTrue(f._visible); self.assertEqual((f.win_mode, f.reg['mode_fenetre']), (0, 0))
        self.assertIs(f._screen, main)                                                                  # le moniteur gardé est celui de la liste neuve
        self.assertFalse(os.path.exists(self.errors_logfile))                                               # aucune erreur notee
        self.assertEqual([e for e in f.logfile if e.startswith('set_fullscreen')], ['set_fullscreen(False,1280x720)'])

    def test_window_then_external_screen_plugged_in_full_screen(self):
        """Meme defaut dans l'autre sens : fenetre, ecran branche, plein ecran sur le moniteur de pyglet (set_fullscreen(True) sans moniteur, comme avant)."""
        f, main, _ = self.stale_win(full=False)
        self.assertTrue(f.set_full_screen(True)); self.assertTrue(f.fullscreen); self.assertIs(f._screen, main)
        self.assertFalse(os.path.exists(self.errors_logfile))

    def test_return_to_initial_state_also_uses_new_monitor(self):
        """Si le passage en fenetre echoue pour une autre raison, le retour au plein ecran ne reutilise pas la poignee perimee."""
        f, main, _ = self.stale_win(failure='set_fullscreen(False,1280x720)')
        self.assertTrue(f.set_full_screen(False)); self.assertTrue(f.fullscreen); self.assertEqual(self.failures(), 1)
        self.assertIs(f._screen, main)
        self.assertNotIn('Retour à l\'état de départ impossible', open(self.errors_logfile, encoding='utf-8').read())

    def test_unplugged_monitor_window_takes_current_or_main(self):
        """L'ancien moniteur n'existe plus (aucun de meme position) : le moniteur gardé devient celui ou se trouve la fenetre, a defaut le principal."""
        main = FakeScreen(0, 0, 1920, 1080, main=True)
        f = self.win(full=True, screens=[main]); f._screen = FakeScreen(-1920, 0, 1920, 1080, stale=True)
        self.assertFalse(f.set_full_screen(False)); self.assertIs(f._screen, main)

    def test_refresh_never_raises_an_error(self):
        f = self.win(full=True); old = f._screen
        f.display = types.SimpleNamespace(get_screens=lambda: (_ for _ in ()).throw(RuntimeError('moniteurs illisibles')))
        self.assertFalse(f._refresh_screen()); self.assertIs(f._screen, old)
        f.display = types.SimpleNamespace(get_screens=lambda: []); self.assertFalse(f._refresh_screen()); self.assertIs(f._screen, old)
        f._screen = None; self.assertFalse(f._refresh_screen())

    def test_no_toggle_during_toggle(self):
        f = self.win(); f._toggling = True; self.assertFalse(f.set_full_screen(True)); self.assertEqual(f.logfile, [])

    def test_simple_debug_toggle(self):
        os.environ['DQ_BASCULE_SIMPLE'] = '1'
        f = self.win(); f.set_full_screen(True); self.assertEqual(f.logfile, ['set_fullscreen(True)', 'journal(plein écran)'])


class DisplayPage(unittest.TestCase):
    """Page Affichage du menu Echap : ordre voulu, ligne « Plein écran » = simple interrupteur Oui / Non, « Résolution » grisee en plein ecran, plus de « Lissage des textures » ni de « Correction des bords des sprites »."""
    ORDER = ['Langue', 'Plein écran', 'Résolution', 'Netteté', 'Shader', 'Effet de vignetage', 'Antialiasing', 'Suréchantillonnage', 'Luminosité', 'Interface']

    @classmethod
    def setUpClass(cls):
        try: from dq4_pc.menus import pause
        except Exception as ex: raise unittest.SkipTest('pause.py non importable ici (%r)' % (ex,))
        cls.PA = pause

    def page(self, full, reg=None):
        reg = reg or RG.Settings(None); reg['mode_fenetre'] = int(full); calls = []
        J = self.J = types.SimpleNamespace(reg=reg, win_mode=int(full), mode=4, zoom=1.0, post=types.SimpleNamespace(max_msaa=None), is_fullscreen=full,
                                  resolutions=lambda: [(1280, 720), (1920, 1080)], current_resolution=lambda: (1920, 1080),
                                  set_resolution=lambda v: calls.append(('res', v)), set_full_screen=lambda v: calls.append(('plein', v)),
                                  set_mode=lambda v: None, set_distance=lambda v: None)
        self.P = self.PA.Pause(J); return self.P._entries_display(), calls

    def test_order(self):
        for full in (False, True):
            e, _ = self.page(full); self.assertEqual([x['l'] for x in e], self.ORDER, 'plein %s' % full)

    def test_full_screen_line_is_a_switch(self):
        for full in (False, True):
            e, calls = self.page(full); f = e[1]                                                  # (e[0] : « Langue », D-238)
            self.assertEqual((f['t'], f['vals'], f['sw'], f['v']()), ('choix', [False, True], True, 'Oui' if full else 'Non'))      # interrupteur Oui / Non, pas une liste deroulante
            self.assertTrue(f['aide'])
            f['ok'](); self.assertEqual(calls[-1], ('plein', not full))                        # Entree / clic bascule (Game.set_full_screen)
            n = len(calls); (f['moins'] if full else f['plus'])(); self.assertEqual(calls[n:], [('plein', not full)])      # gauche = Non, droite = Oui
            n = len(calls); (f['plus'] if full else f['moins'])(); self.assertEqual(len(calls), n)                        # (deja dans cet etat : rien)

    def test_resolution_grayed_in_full_screen(self):
        for full in (False, True):
            e, calls = self.page(full); r = e[2]
            self.assertEqual(bool(r['off']), full, 'plein %s' % full)
            self.assertNotIn('note', r)                                                        # (plus de texte rouge « Sans effet en plein écran » : la ligne est seulement grisee)
            self.P.stack = ['affichage']; self.P.selected['affichage'] = 2; self.P.key_press(self.PA.pyglet.window.key.RIGHT)          # (au clavier, par le menu : une ligne grisee ne change rien)
            self.assertEqual(len(calls), 0 if full else 1)

    def test_no_more_smoothing_or_edge_correction_options(self):
        e, _ = self.page(False)
        for x in e: self.assertNotIn(x['l'], ('Lissage des textures', 'Correction des bords des sprites', 'Fenêtre'))

    def test_full_screen_and_interface_at_ends(self):
        e, _ = self.page(False); self.assertEqual((e[0]['l'], e[1]['l'], e[-1]['l']), ('Langue', 'Plein écran', 'Interface'))               # (« Langue » en tete, D-238)


class RemovedCode(unittest.TestCase):
    """Le plein ecran exclusif, l'option « Correction des bords des sprites » et l'option « Lissage des textures » ne sont plus nulle part dans le code (il reste leurs interrupteurs de debogage : variables d'environnement)."""
    @classmethod
    def setUpClass(cls):
        try: from dq4_pc.window import game as window; cls.WND = window
        except Exception as ex: raise unittest.SkipTest('window.py non importable ici (%r)' % (ex,))

    def test_window(self):
        WND = self.WND
        for name_str in ('choisir_mode_ecran',): self.assertFalse(hasattr(WND, name_str), name_str)
        for name_str in ('regler_mode_fenetre', '_poser_mode', 'basculer_exclusif', 'modes_ecran', '_mode_applique', '_restaurer_affichage', '_restaurer_a_la_sortie', 'regler_lissage'): self.assertFalse(hasattr(WND.Game, name_str), name_str)
        for name_str in ('set_full_screen', 'toggle_full_screen', '_set_full_screen', '_window_shortcut'): self.assertTrue(hasattr(WND.Game, name_str), name_str)

    def test_read_removed_settings(self):
        """Aucune lecture de `reg['lissage']` / `reg['edge_correction']` / `reg['mode_fenetre_retour']` dans le code."""
        import re
        for file_name in ('window.py', 'pause.py', 'postfx.py', 'flat_sceneries.py', 'settings.py'):
            src = _paths.source(file_name)
            self.assertIsNone(re.search(r"\[\s*'(lissage|correction_bords|mode_fenetre_retour)'\s*\]", src), file_name)
            self.assertNotIn("'lissage':", src, file_name); self.assertNotIn("'correction_bords':", src, file_name)

    def test_smoothing_and_correction_always_active(self):
        """Depuis #184 la correction des bords est a 0 par defaut (position brute des PNJ, comme dans le jeu) ; l'ancienne correction complete se demande par --correction-bords ou DQ_CORRECTION_BORDS ; un ancien reglage n'y change rien."""
        WND = self.WND; j = types.SimpleNamespace(args=types.SimpleNamespace(), reg=RG.Settings(None))
        os.environ.pop('DQ_CORRECTION_BORDS', None)
        self.assertEqual(WND.Game._edge_correction(j), 0.0)                                                    # position brute, sans reglage
        j.reg.v['correction_bords'] = True; self.assertEqual(WND.Game._edge_correction(j), 0.0)                # (un ancien reglage n'y change rien)
        os.environ['DQ_CORRECTION_BORDS'] = '100'
        try: self.assertEqual(WND.Game._edge_correction(j), 1.0)                                              # ancienne correction complete (debogage)
        finally: os.environ.pop('DQ_CORRECTION_BORDS', None)
        j.args.edge_correction = 40; self.assertAlmostEqual(WND.Game._edge_correction(j), 0.4)


if __name__ == '__main__':
    unittest.main(verbosity=2)
