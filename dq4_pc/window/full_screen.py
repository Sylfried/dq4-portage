"""Plein ecran, fenetre, resolution et moniteurs."""
import os, sys, time
import pyglet
from pyglet import gl
from dq4_pc import paths as CH
from dq4_pc.language import N_, tr
from dq4_pc.window import screens as EK
from dq4_pc.core import load_tracking as SV
from dq4_pc.persistence import settings as RG
from dq4_pc.window.constants import RESOLUTIONS
from dq4_pc.window.helpers import adjust_size, transitions_dwm, useful_zone


# le message quand un passage fenetre <-> plein ecran echoue : (mode demande est le plein ecran, mode garde est le plein ecran) -> phrase entiere (l'anglais n'a pas le meme ordre des mots)
TOGGLE_FAILURE_MESSAGES = {(True, True): 'Full screen failed (%r): full screen kept', (True, False): 'Full screen failed (%r): windowed mode kept',
                         (False, True): 'Windowed mode failed (%r): full screen kept', (False, False): 'Windowed mode failed (%r): windowed mode kept'}


class FullScreenMixin:
    """Plein ecran, fenetre, resolution et moniteurs."""

    def _create_window(self, args, cfg, requested):
        """Cree la fenetre directement dans le mode memorise (0 fenetre, 1 plein ecran), avec repli a toute erreur, dit dans la console : plein ecran -> fenetre.
        Elle reste cachee jusqu'a une premiere image noire (pas d'eclair blanc). -> mode obtenu."""
        try:
            screen_page = pyglet.display.get_display().get_default_screen(); self.desktop = (int(screen_page.width), int(screen_page.height))      # (la taille du bureau)
        except Exception as ex: print('Main screen unreadable (%r)' % (ex,), flush=True)
        for mode in range(requested, -1, -1):
            try:
                self._simulated_failure(mode)
                if mode == 1: self._create_fullscreen(cfg)
                else: super().__init__(args.width_px, args.height_px, caption=tr(self.WINDOW_TITLE), resizable=True, config=cfg, vsync=True, visible=False)
            except Exception as ex:
                if mode == 0: raise
                print('Full screen failed at launch (%r): windowed mode' % (ex,), flush=True)
                continue
            self.win_mode = mode
            SV.note('window created (hidden)', mode=mode, size_value='%dx%d' % (self.width, self.height))
            if SV.ACTIVE:
                for ev in ('on_resize', 'on_show', 'on_hide', 'on_expose', 'on_move', 'on_activate', 'on_deactivate'):
                    self.push_handlers(**{ev: (lambda *a, _e=ev: SV.note('event ' + _e, args=a))})
            try: self.switch_to(); gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear(); self.flip()
            except Exception: pass
            SV.note('black frame presented (window hidden)')
            self.dwm_cut = transitions_dwm(self, False)    # Windows : pas d'animation d'ouverture du gestionnaire de fenetres (remise par on_draw, 2 s apres la 1re image du jeu)
            self.set_visible(True); self.activate()          # (ce que Window.__init__ fait pour une fenetre visible : ici apres l'image noire)
            try: self.switch_to(); gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear(); self.flip()      # Windows : l'image noire presentee fenetre cachee n'est pas forcement affichee ; une 2e, fenetre montree, evite le fond de classe (blanc) le temps du chargement
            except Exception: pass
            SV.note('window shown', size_value='%dx%d' % (self.width, self.height), dwm_cut=self.dwm_cut)
            return mode

    def _create_fullscreen(self, cfg):
        """Fenetre creee en plein ecran, sur l'ecran principal : elle n'existe pas encore, il n'y a donc pas d'ecran ou elle se trouve a detecter (par la suite, F11 ou l'interrupteur la mettent en plein ecran sur l'ecran ou elle est)."""
        super().__init__(caption=tr(self.WINDOW_TITLE), resizable=True, config=cfg, vsync=True, fullscreen=True, visible=False); self._note_full_zone()

    # ---- reglages appliques depuis le menu Echap
    def set_mode(self, m): self.mode = RG.valid_sprites_mode(m)

    @property
    def is_fullscreen(self):
        """Plein ecran (fenetre sans bordure a la resolution du bureau) ?"""
        return self.win_mode == 1

    def resolutions(self):
        """Tailles proposees (16/9, 720p a 4K), triees par largeur puis hauteur : fenetre = celles qui tiennent sur l'ecran avec ses bordures ; plein ecran = celles du bureau (la ligne est grisee : la fenetre prend toujours
        la resolution du bureau, le choix sert au prochain retour en fenetre). La taille actuelle s'y ajoute si elle est libre."""
        entries = list(RESOLUTIONS); cur = self.current_resolution()
        lim = self.desktop if self.is_fullscreen else useful_zone()
        if lim: entries = [r for r in entries if r[0] <= lim[0] and r[1] <= lim[1]]
        if cur not in entries: entries.append(cur)
        return sorted(entries)                # par largeur, puis par hauteur

    def current_resolution(self): return (int(self.width), int(self.height))

    def set_resolution(self, v):
        """Fenetre : change la taille (ramenee a l'ecran si elle est trop grande). Plein ecran : sans effet, la fenetre garde la resolution du bureau ; le choix sert au prochain retour en fenetre."""
        w, h = int(v[0]), int(v[1])
        if self.is_fullscreen: self.window_size = adjust_size(w, h)
        else:
            w, h = adjust_size(w, h)
            self.window_size = (w, h); self.set_size(w, h); self._check_real_size()

    def _check_real_size(self):
        """Windows : compare la zone de dessin donnee par le systeme a celle que pyglet croit avoir et la lui redonne si elles different (fenetre reduite par Windows : sinon le dessin est trop grand et la scene semble zoomee jusqu'au premier redimensionnement)."""
        if sys.platform != 'win32' or self.is_fullscreen: return
        try:
            import ctypes
            from ctypes import wintypes
            r = wintypes.RECT()
            if not ctypes.windll.user32.GetClientRect(self._hwnd, ctypes.byref(r)): return
            w, h = r.right - r.left, r.bottom - r.top
            if w <= 0 or h <= 0 or (w, h) == (self._width, self._height): return
            print('Window: drawing area %d x %d corrected (the system reports %d x %d)' % (self._width, self._height, w, h), flush=True)
            self._width, self._height = w, h
            self._update_view_location(w, h)
            self.dispatch_event('_on_internal_resize', w, h)
        except Exception as ex: print('size check failed:', ex, flush=True)

    def set_info(self, yes): self.helptext = bool(yes)

    def set_full_screen(self, yes):
        """Interrupteur « Plein écran » du menu Echap, F11 et Alt + Entree : passe de la fenetre au plein ecran (fenetre sans bordure a la resolution du moniteur, l'affichage du moniteur ne change pas) et inversement, en une seule
        bascule (voir _set_full_screen). Le moniteur du plein ecran est celui ou se trouve la fenetre (voir _screen_for_fullscreen).
        Le mode obtenu est memorise dans les reglages (`mode_fenetre`). A toute erreur : etat de depart conserve, dit dans la console et par un message a l'ecran. -> vrai si la fenetre est en plein ecran."""
        target = 1 if yes else 0; R = self.reg
        if target == self.win_mode: R['mode_fenetre'] = target; return self.is_fullscreen
        if self._toggling: return self.is_fullscreen
        self._toggling = True
        try:
            error = None
            try:
                screen_page = None
                if target == 1:
                    screen_page = self._screen_for_fullscreen()[0]
                    if screen_page is not None and not self.fullscreen and self._already_on(screen_page): screen_page = None          # (c'est deja le moniteur de pyglet : set_fullscreen(True) comme avant)
                self._set_full_screen(target == 1, screen_page)
            except Exception as ex: error = ex
            self.win_mode = 1 if self.fullscreen else 0           # (l'etat reel de la fenetre)
            R['mode_fenetre'] = self.win_mode
            self._log_window('full screen' if self.win_mode else 'window')
            if error is not None:
                print(TOGGLE_FAILURE_MESSAGES[(bool(target), bool(self.win_mode))] % (error,), flush=True)
                self._note_toggle_failure(target, error)
        finally: self._toggling = False
        return self.is_fullscreen

    def _note_toggle_failure(self, target, error):
        """Echec d'un passage plein ecran <-> fenetre : l'erreur COMPLETE (la pile d'appels, pas seulement son texte) avec l'etat de la fenetre et des moniteurs, dans la console et dans `erreurs_fenetre.log` (a cote des reglages ;
        ignore par git ; `DQ_JOURNAL_FENETRE` : un autre fichier). La ligne « Fenêtre impossible (...) » ne dit pas ou ca a echoue. Ne leve jamais d'erreur."""
        try:
            import traceback
            state = []
            try: state.append('window: full screen = %s, %d x %d, remembered size %s, previous position %s, desktop %s' % (self.fullscreen, self.width, self.height, getattr(self, 'window_size', None), getattr(self, '_windowed_location', None), getattr(self, 'desktop', None)))
            except Exception as ex: state.append('window unreadable (%r)' % (ex,))
            try: ec = self.screen; state.append('window screen according to pyglet: %d x %d at (%d, %d)' % (ec.width, ec.height, ec.x, ec.y))
            except Exception as ex: state.append('window screen unreadable (%r)' % (ex,))
            try: state.append('monitors: %s' % ' ; '.join(('%d x %d at (%d, %d) (primary)' if d['principal'] else '%d x %d at (%d, %d)') % (d['largeur'], d['hauteur'], d['x'], d['y']) for d in self._read_screens(True)[1]))
            except Exception as ex: state.append('monitors unreadable (%r)' % (ex,))
            state.append('pyglet %s, Python %s, %s' % (pyglet.version, sys.version.split()[0], sys.platform))
            text = ('--- %s: switch to full screen failed ---\n%s%s\n' if target else '--- %s: switch to windowed mode failed ---\n%s%s\n') % (time.strftime('%Y-%m-%d %H:%M:%S'), ''.join(traceback.format_exception(error)), '\n'.join(state))
            print(text, flush=True)
            path = CH.FOLDERS.errors_logfile(); os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, 'a', encoding='utf-8') as f: f.write(text + '\n')
        except Exception as ex: print('Switch error not logged (%r)' % (ex,), flush=True)

    def toggle_full_screen(self):
        """F11 / Alt + Entree : fenetre <-> plein ecran."""
        return self.set_full_screen(not self.is_fullscreen)

    def _set_full_screen(self, full, screen_page=None):
        """La bascule, en une seule etape (pyglet : un set_fullscreen, qui sur Windows cache la fenetre, change son style et sa taille, puis la remontre et la replace) :
        - la taille de la fenetre est memorisee avant de la quitter (`window_size`, la position l'est par pyglet) et rendue d'un coup en y revenant, jamais par un etat intermediaire (plus de set_fullscreen(False) suivi de set_fullscreen(True)) ;
        - la fenetre est cachee AVANT, donc remontree une seule fois, a sa taille et a sa place definitives, et non pas montree au mauvais endroit puis deplacee ;
        - une image du jeu est dessinee a la taille definitive pendant qu'elle est cachee (les tampons du rendu hors ecran, postfx.py, ne sont refaits que si la taille a change, une seule fois, ici : plus de reconstruction forcee a chaque
          bascule), puis affichee, puis la fenetre est montree et la meme image redessinee aussitot (au cas ou le systeme n'aurait pas gardé celle de la fenetre cachee) : aucune trame de taille instable ni de tampon vide.
        `screen_page` : objet Screen de pyglet du plein ecran (None : celui que pyglet a deja). Deja en plein ecran, un autre `screen_page` deplace la fenetre sur ce moniteur (meme etape : cachee, un set_fullscreen, une image, montree) ;
        le moniteur de depart est retabli si le deplacement echoue.
        Leve une erreur si le mode n'a pas pu etre pris (l'etat de depart est alors retabli). DQ_BASCULE_SIMPLE=1 : (debogage) un set_fullscreen sans rien d'autre, comme avant."""
        before = bool(self.fullscreen)
        if before == full and not (full and screen_page is not None and not self._already_on(screen_page)): return
        self._refresh_screen()          # (AVANT tout : le moniteur que pyglet garde peut ne plus etre valable, voir _refresh_screen)
        if not before: self.window_size = (int(self.width), int(self.height))          # (la taille de la fenetre, a retrouver au retour)
        screen_before = getattr(self, 'screen', None) if before else None              # (le moniteur a retrouver si le deplacement echoue)
        size_value = adjust_size(*self.window_size)              # (une taille memorisee plus grande que la zone utile de l'ecran est ramenee a l'ecran)
        if os.environ.get('DQ_BASCULE_SIMPLE'): self._apply_full_screen(full, size_value, screen_page); self._simulated_failure(1 if full else 0); return
        is_hidden = False; error = None
        try:
            if getattr(self, '_visible', True): is_hidden = True; self.set_visible(False)          # (cachee avant l'appel : un masquage a moitie reussi est quand meme suivi d'un set_visible(True))
            self._apply_full_screen(full, size_value, screen_page)
            self._simulated_failure(1 if full else 0)          # (test : l'echec arrive apres le changement, pour essayer le retour a l'etat de depart)
        except Exception as ex:
            error = ex
            try: self._apply_full_screen(before, size_value, screen_before)          # (retour a l'etat de depart, fenetre toujours cachee, sur le moniteur de depart)
            except Exception as ex2:
                print("Return to the starting state failed (%r)" % (ex2,), flush=True)
                try: error.add_note("Return to the starting state failed too: %r" % (ex2,))
                except Exception: pass
        self._toggle_frame()
        if is_hidden:
            try: self.set_visible(True)
            except Exception as ex: print('Window not shown again (%r)' % (ex,), flush=True)
            else: self._toggle_frame()          # (supposé : le systeme peut ne pas garder ce qui est affiche pendant que la fenetre est cachee ; la meme image est redessinee des qu'elle est visible, sans attendre la boucle)
        if error is not None: raise error

    def _apply_full_screen(self, full, size_value, screen_page=None):
        """Le set_fullscreen de la bascule (un seul appel), sur le moniteur `screen_page` (objet Screen de pyglet ; None : celui que la fenetre a). En revenant en fenetre elle retrouve sa taille (`size_value`) et sa place d'avant
        (position memorisee par pyglet, sur son moniteur d'origine, quel que soit celui du plein ecran) ; sans position memorisee (lancee en plein ecran) ou si son moniteur n'est plus la, elle est centree sur le moniteur
        du plein ecran."""
        if full:
            if screen_page is not None: self.set_fullscreen(True, screen=screen_page)
            else: self.set_fullscreen(True)
            self._note_full_zone()
        else:
            self.set_fullscreen(False, width=int(size_value[0]), height=int(size_value[1]))          # (la signature de pyglet : set_fullscreen(plein, screen, mode, width, height))
            loc = getattr(self, '_windowed_location', None); zone = getattr(self, 'full_zone', None) or ((0, 0) + tuple(self.desktop) if self.desktop else None)
            seen = self._read_screens(True)[1]
            if loc and zone and seen and EK.screen_of((loc[0], loc[1], self.width, self.height), seen) is None: loc = None          # (son moniteur a ete debranche : elle serait hors de tous les ecrans)
            if not loc and zone:
                try: self.set_location(int(zone[0] + max(0, (zone[2] - self.width) // 2)), int(zone[1] + max(32, (zone[3] - self.height) // 2)))
                except Exception as ex: print('Window not centered (%r)' % (ex,), flush=True)
        if sys.platform == 'win32' and not full: self._check_real_size()          # (Windows peut reduire la fenetre sans prevenir)

    def _toggle_frame(self):
        """Fenetre cachee, a sa taille definitive : une image du jeu y est dessinee et affichee (pendant les logos et les chargements : du noir), pour que la premiere chose vue soit une image complete."""
        try:
            self.switch_to()
            if self._ready: self.on_draw()
            else: gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear()
            self.flip()
        except Exception as ex:
            print('Switch frame failed (%r): black' % (ex,), flush=True)
            try: gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear(); self.flip()
            except Exception: pass

    # ---- moniteur du plein ecran : celui de la fenetre (aucun reglage ; logique pure dans screens.py)
    def _read_screens(self, fresh=False):
        """-> (objets Screen de pyglet, descriptions de ecrans.lister) des moniteurs detectes (`display.get_screens()`). La liste est gardee 1,5 s (la page Affichage la lit a chaque image et, sous Windows, l'enumeration interroge le
        systeme) ; `fresh` la relit (bascule, changement de choix). Illisible -> ([], [])."""
        t = time.perf_counter(); c = getattr(self, '_screen_cache', None)
        if c is not None and not fresh and t - c[0] < 1.5: return c[1], c[2]
        try:
            screens = list((getattr(self, 'display', None) or pyglet.display.get_display()).get_screens())
            res = (t, screens, EK.listing(screens))
        except Exception as ex:
            print('Monitors unreadable (%r)' % (ex,), flush=True); res = (t, [], [])
        self._screen_cache = res
        return res[1], res[2]

    def _refresh_screen(self):
        """Remet a jour le moniteur que pyglet garde pour la fenetre (`_screen`) avant une bascule (#126). Sous Windows, ce Screen garde la poignee (HMONITOR) du moniteur telle qu'elle etait a la creation de la fenetre ;
        quand on branche (ou debranche) un ecran, Windows peut en attribuer d'autres et la poignee gardee n'est plus valable : `set_fullscreen` recree alors la fenetre (`Win32Window._create`), qui lit la densite du moniteur
        (`Screen.get_dpi` -> GetDpiForMonitor) et echoue avec « Descripteur non valide » (le journal de Sylfried du 03/11/2026 : plein ecran, puis un ecran externe branche, puis plus de retour en fenetre).
        Le moniteur est cherche dans une enumeration neuve : celui qui a les memes position et dimensions que l'ancien, sinon celui ou se trouve la fenetre, sinon le principal. Ne leve jamais d'erreur.
        -> vrai si un moniteur valable a ete mis en place."""
        try:
            current = getattr(self, '_screen', None); screens, desc = self._read_screens(True)
            if current is None or not screens or not desc: return False
            old = (int(current.x), int(current.y), int(current.width), int(current.height))
            i = next((k for k, d in enumerate(desc) if (d['x'], d['y'], d['largeur'], d['hauteur']) == old), None)
            if i is None: i = EK.target(desc, self._window_screen_index(desc))
            if i is None: return False
            fresh = screens[desc[i]['source']]
            if (int(fresh.x), int(fresh.y), int(fresh.width), int(fresh.height)) != old:
                print('Window monitor refreshed: %d x %d at (%d, %d) (before: %d x %d at (%d, %d))' % (fresh.width, fresh.height, fresh.x, fresh.y, old[2], old[3], old[0], old[1]), flush=True)
            self._screen = fresh; return True
        except Exception as ex:
            print('Window monitor not refreshed (%r)' % (ex,), flush=True); return False

    def _window_screen_index(self, desc):
        """Indice (dans `desc`) du moniteur ou se trouve la fenetre (celui de son centre) ; None si elle n'existe pas encore ou si sa place est illisible."""
        try:
            x, y = self.get_location(); return EK.screen_of((x, y, self.width, self.height), desc)
        except Exception: return None

    def _screen_for_fullscreen(self, fresh=True):
        """-> (objet Screen de pyglet, description) du moniteur du plein ecran : celui ou se trouve la fenetre (celui de son centre), a defaut le principal. (None, None) si les moniteurs sont illisibles : pyglet garde alors le sien.
        Aucun choix du joueur (retire le 03/11/2026 sur sa demande : le plein ecran se fait toujours sur l'ecran de la fenetre). Ne leve jamais d'erreur."""
        screens, desc = self._read_screens(fresh)
        try:
            i = EK.target(desc, self._window_screen_index(desc))
            if i is None: return None, None
            return screens[desc[i]['source']], desc[i]
        except Exception as ex:
            print('Full screen monitor unreadable (%r)' % (ex,), flush=True); return None, None

    def _already_on(self, screen_page):
        """La fenetre (en plein ecran) est-elle deja sur ce moniteur ? (meme position et memes dimensions que le moniteur de pyglet.)"""
        try:
            ec = self.screen; return (ec.x, ec.y, ec.width, ec.height) == (screen_page.x, screen_page.y, screen_page.width, screen_page.height)
        except Exception: return False

    def _note_full_zone(self):
        """Memorise le rectangle du moniteur du plein ecran (centrage au retour en fenetre quand la fenetre n'a pas de place d'avant : lancee en plein ecran)."""
        try: ec = self.screen; self.full_zone = (int(ec.x), int(ec.y), int(ec.width), int(ec.height))
        except Exception: pass

    def _window_shortcut(self, symbol, modifiers):
        """F11 ou Alt + Entree, de n'importe ou (logos, titre, jeu, menu Echap, saisie du nom, combat) : bascule fenetre <-> plein ecran. La touche est avalee (ni validation, ni action du jeu) et, avec Alt, Alt ne vaut plus
        « discussion de groupe » (voir _fronts). -> True si consommee."""
        K = pyglet.window.key
        t = getattr(self, 'key_list', None)
        alt = bool(modifiers & K.MOD_ALT) or (t is not None and bool(t[K.LALT] or t[K.RALT]))          # (le drapeau du systeme, ou l'etat des touches Alt : l'un des deux suffit)
        if not (symbol == K.F11 or (alt and symbol in (K.RETURN, K.ENTER))): return False
        if getattr(self.pause, 'capture', None) is not None: return False                    # menu Commandes en attente d'une touche : F11 y est « réservée » (reglages.RESERVED)
        self.swallowed.add(symbol)
        if alt: self.alt_cand = False
        if self._toggling or not hasattr(self, 'post'): return True
        try: self.toggle_full_screen()
        except Exception as ex: print('Full screen switch failed: %r' % (ex,), flush=True)
        return True

    def _log_window(self, when):
        """Une ligne de journal : etat et taille de la fenetre (plein ecran ou non), zone de dessin et ecran ; ecrite a la creation, a la 1re image dessinee et a chaque bascule."""
        try:
            ec = self.screen; fb = self.get_framebuffer_size()
            name_str = ('window', 'FULL SCREEN')[self.win_mode] + ('' if bool(self.fullscreen) == (self.win_mode > 0) else ' [INCONSISTENT: fullscreen=%s]' % self.fullscreen)
            n = EK.screen_of((ec.x, ec.y, ec.width, ec.height), self._read_screens()[1]); n = '' if n is None else ' (screen %d)' % (n + 1)
            print('Window (%s): %s, %d x %d, drawing area %d x %d, screen %d x %d%s' % (when, name_str, self.width, self.height, fb[0], fb[1], ec.width, ec.height, n), flush=True)
        except Exception as ex: print('Window (%s): state unreadable (%r)' % (when, ex), flush=True)
