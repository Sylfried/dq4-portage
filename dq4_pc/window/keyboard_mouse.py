"""Clavier, souris et manette : evenements de la fenetre et lecture des touches."""
import os
import pyglet
from dq4_pc.language import tr
from dq4_pc.window import inputs as EN
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.core import engine as ENGINE
from dq4_pc.window.constants import EDGE_ACTIONS, BTN_MAP, BTN_CHAT, BTN_MENU, BTN_TALK, BTN_SAVES, SFX_BUTTON, button_sfx


class KeyboardMouseMixin:
    """Clavier, souris et manette : evenements de la fenetre et lecture des touches."""

    def on_text(self, text):
        """Menu Echap : saisie d'une valeur au clavier."""
        if self._ready and self.pause.opened and self.pause.entry is not None: self.pause.text(text)
        elif self._ready and self._name_entry_in_progress(): self.name_entry.text_entered(text)
        return pyglet.event.EVENT_HANDLED

    def on_key_press(self, symbol, modifiers):
        """Seule touche fixe : Echap (menu). Les autres sont celles du menu Commandes (pad, infos a l'ecran) ; le menu ouvert recupere toutes les touches."""
        K = pyglet.window.key
        if self._window_shortcut(symbol, modifiers): return pyglet.event.EVENT_HANDLED          # F11 / Alt + Entree : de n'importe ou (logos, titre, jeu, menu Echap)
        if symbol in (K.LALT, K.RALT): self.alt_cand = True                # Alt seul = discussion de groupe, au relachement (voir on_key_release et _fronts)
        if not self._ready: self._logo_touched = True; return pyglet.event.EVENT_HANDLED
        self.mouse_guard.keyboard(self.mouse)                             # le clavier a la main : le survol ne reprend qu'au premier vrai mouvement du pointeur (un clic reprend la main aussitot)
        if self.pause.opened: self.pause.key_press(symbol, modifiers); return pyglet.event.EVENT_HANDLED
        self.last_device = 'clavier'
        if self._name_entry_in_progress(): self.name_entry.key_press(symbol, modifiers); return pyglet.event.EVENT_HANDLED          # saisie du nom : le clavier lui appartient
        if self.saves_screen is not None: self.saves_screen.key_press(symbol, modifiers); return pyglet.event.EVENT_HANDLED                       # ecran Sauvegardes (export / import)
        if self.license_panel is not None:                                       # ecran Licence : defilement et retour
            step = {K.UP: -30.0, K.DOWN: 30.0, K.PAGEUP: -360.0, K.PAGEDOWN: 360.0, K.HOME: -1e9, K.END: 1e9}.get(symbol)
            if step is not None: self.license_panel.scroll_by(step)
            elif symbol in (K.ESCAPE, K.BACKSPACE) or self.reg.action_of(symbol) == 'B': self._license_back()
            return pyglet.event.EVENT_HANDLED
        if symbol == K.ESCAPE:                                             # Echap : retour dans les menus du jeu et la carte (comme la touche Annuler), sinon le menu Echap
            if self._esc_back(): self.click_b = True
            else: self.pause.open_menu()
            return pyglet.event.EVENT_HANDLED
        if self.reg.action_of(symbol) == 'infos': self.helptext = not self.helptext; self.reg['infos'] = self.helptext; return pyglet.event.EVENT_HANDLED
        if self.reg.action_of(symbol) == 'vit_combat': self.change_battle_speed(); return pyglet.event.EVENT_HANDLED          # Manuel -> Normal -> Rapide -> Très rapide (en combat comme ailleurs)
        if self.reg.action_of(symbol) == 'historique' and self.title_screen is None and self.engine.state.part in (ENGINE.PART_TOWN, ENGINE.PART_BATTLE, ENGINE.PART_FIELD): self._history_key(); return pyglet.event.EVENT_HANDLED          # touche de l'historique des messages (#187 : seulement quand le joueur a la main sur son personnage)
        n = self._state_number(symbol)
        if n is not None:                                                  # raccourcis des etats : chiffre = enregistrer, Ctrl + chiffre = charger
            if self._held('modif'):
                self.combo[1] = True
                if self.state_info(n):
                    try: self.load_state(n); self.toast(tr('État %d chargé') % n)
                    except Exception as ex: self._note_state_failure(tr('Chargement de l\'état %d') % n, ex)
                else: self.toast(tr('État %d vide') % n)
            else: self.quick_save = n
            return pyglet.event.EVENT_HANDLED
        if symbol in (K.LSHIFT, K.RSHIFT) or symbol in self.reg.codes('modif'):      # Maj + touche modificatrice (sans chiffre) : annule le dernier chargement, au relachement
            ctrl = symbol in self.reg.codes('modif') or self._held('modif'); do_update = symbol in (K.LSHIFT, K.RSHIFT) or self.key_list[K.LSHIFT] or self.key_list[K.RSHIFT]
            if ctrl and do_update: self.combo = [True, False]
        return pyglet.event.EVENT_HANDLED

    def on_key_release(self, symbol, modifiers):
        K = pyglet.window.key
        self.swallowed.discard(symbol)
        if symbol in (K.LALT, K.RALT):         # Alt relache : si rien d'autre n'a ete fait pendant (pas Alt + Entree), c'est l'appui de la touche de discussion de groupe
            cand, self.alt_cand = self.alt_cand, False
            if cand and self._ready and not self.pause.opened and symbol in self.reg.codes('discussion') and not (self.key_list[K.LALT] or self.key_list[K.RALT]): self.alt_tap = True
        if (symbol in (K.LSHIFT, K.RSHIFT) or symbol in self.reg.codes('modif')) and self.combo[0]:
            triggered = not self.combo[1]; self.combo = [False, False]
            if triggered and self._ready and not self.pause.opened: self.cancel_loading()

    def _esc_back(self):
        """Echap sert de touche Annuler quand une fenetre du jeu (menu, carte) est ouverte sur le terrain : sinon il ouvre le menu Echap (combat, messages et terrain libre compris)."""
        eng = self.engine
        if eng.state.part == ENGINE.PART_INITIAL: return self.name_entry.active or self.license_panel is not None or (not eng.msg_visible and eng.active_menu() is not None)           # menu de depart : Echap = Annuler (le retour de la racine = quitter)
        if eng.state.part in ENGINE.MINIGAME_PARTS:          # casino, bestiaire : Echap = bouton retour de la fenetre ouverte (manette 0x20) ; rouleaux en marche, message, cartes en cours de distribution : pas de retour, le menu Echap s'ouvre
            p = eng.active_menu()
            return p is not None and not eng.msg_visible and self._can_go_back(p)
        if eng.state.part not in (ENGINE.PART_TOWN, ENGINE.PART_FIELD) or eng.state.effect is not None or getattr(eng.state, 'screen_effect', None) is not None: return False
        return bool(self.map_open) or (not eng.msg_visible and eng.active_menu() is not None)

    def _can_go_back(self, port):
        """Une fenetre visible du jeu a-t-elle un bouton Annuler / Retour (touche de manette 0x20) en ce moment ? (casino, bestiaire : Echap le presse ; sinon il ouvre le menu Echap)"""
        if not self.ui_g: return False
        for q in [port] + [q for q, fq in self.engine.ui.f.items() if q > 1 and fq['vis']]:
            wnd = self.ui_g.f.get(q)
            if wnd and any(b[1] & 0x20 for b in wnd.buttons()): return True
        return False

    def _button_under(self, port, x, y):
        """Bouton de la fenetre `port` sous le pointeur (le plus en avant d'abord) : (numero, manette, profondeur, identifiant de l'element) ou None."""
        h = [(pr, b, pad, nid) for b, pad, x0, y0, x1, y1, pr, nid in self._zones(port) if x0 <= x <= x1 and y0 <= y <= y1]
        if not h: return None
        pr, b, pad, nid = max(h, key=lambda t: t[0])
        return b, pad, pr, nid

    def on_mouse_press(self, x, y, button, modifiers):
        """Souris = tactile du mobile : appui sur un bouton du menu actif (MenuPortItem.Update, PUSH_STATE_BEGIN) ; clic droit = Annuler."""
        M = pyglet.window.mouse; eng = self.engine
        if not self._ready: self._logo_touched = True; return
        self.last_device = 'souris'; self.mouse_guard.click(); self.mouse = (x, y)             # un clic agit toujours, aussitot : la souris a la main
        if button == M.MIDDLE: self._wheel_press(x, y); return                                           # bouton du milieu : la camera seulement (jamais un clic de menu, de message ou de bouton)
        if self.pause.opened: self.pause.click(x, y, button); return
        if self._name_entry_in_progress(): self.name_entry.click(x, y, button); return
        if self.saves_screen is not None: self.saves_screen.click(x, y, button); return
        if self.license_panel is not None: self._license_click(x, y, button); return
        if self.title_screen is not None and button == M.LEFT: self.click_a = True; return                 # titre : un toucher n'importe ou valide (la manette recoit A)
        if button == M.RIGHT: self.click_b = True; return
        if button == M.LEFT:
            vis = self.hud.visible_ones()
            if vis:
                n = self.hud.press(x, y, vis)                                                            # boutons a l'ecran (Carte, Commandes, Discussion) et croix
                if n: n != HM.DPAD and self.sound.play_sfx(SFX_BUTTON); return
        if button == M.LEFT and self._terrain_free(): self.click_a = True; return                                    # terrain libre : un clic gauche n'importe ou = touche d'action, comme l'espace (#131 ; plus de clic sur la bulle seule)
        if button != M.LEFT or not self.ui_render: return
        cp = self._map_ports()
        if 22 in cp:                                                               # boutons de la fenetre de la carte (sans numero) : retour (touche de manette 0x400, ferme la carte) et mode (haut de la manette, change de vue), actifs au relachement
            h = self._button_under(cp[22], x, y)
            if h and h[0] == -1 and h[1] in (0x400, 2): self.press_state = (cp[22], h[0], h[1]); return                      # (retour et mode : manette 0x400 et 2, muets comme dans MenuPortItem.Update)
        key_list = [(h[2], -i, port, h) for i, port in enumerate(eng.input_menus()) for h in [self._button_under(port, x, y)] if h]      # tous les menus qui attendent la saisie : bouton le plus en avant, puis fenetre la plus recente
        if key_list:
            _, _, port, h = max(key_list, key=lambda t: t[:2]); self.press_state = (port, h[0], h[1]); self.press_node = h[3]; button_sfx(h[1]) and self.sound.play_sfx(SFX_BUTTON); return
        if eng.msg_visible: self.click_a = True                                      # toucher le message = page suivante

    def on_mouse_motion(self, x, y, dx, dy):
        """Survol de la souris : le bouton sous le pointeur est selectionne comme avec les fleches. Menu tactile (curseur local) : immediat ; menu a curseur du moteur :
        le curseur est amene sur le bouton par des appuis de direction, une image sur trois (voir _step_toward_hover)."""
        if not self._ready: return
        self.mouse = (x, y)
        if self.wheel.in_progress: self.wheel.cancel()                  # (un mouvement sans bouton enfonce : le relachement du bouton du milieu est passe inapercu, hors de la fenetre ou pendant une perte de focus ; le geste est abandonne)
        if not self.mouse_guard.has_moved((x, y)): return                # simple tremblement apres l'usage du clavier : ni le mode, ni la selection ne changent (ecart cumule depuis la derniere touche, voir entrees.MouseGuard)
        self.last_device = 'souris'
        if self.pause.opened: self.pause.hovered(x, y); return
        if self._name_entry_in_progress(): self.name_entry.hovered(x, y); return
        if self.saves_screen is not None: self.saves_screen.hover(x, y); return
        if self.license_panel is not None: self.license_panel.hovered = self.license_panel.zone(x, y); return
        if not self.ui_render or self.press_state: return
        eng = self.engine
        key_list = [(h[2], -i, port, h) for i, port in enumerate(eng.input_menus()) for h in [self._button_under(port, x, y)] if h and (h[0] >= 0 or self._is_button(port, h[3]))]
        if not key_list: self.hovered = None; return                  # hors d'un bouton : l'element survole en dernier reste seul en surbrillance (le curseur du moteur y est aussi) ; effacé par on_mouse_leave ou une touche
        _, _, port, h = max(key_list, key=lambda t: t[:2]); f = eng.ui.f[port]; self.hover_node = (port, h[3])
        if h[0] < 0: self.hovered = None                              # bouton sans numero (retour, fleches de page) : seul l'element est allume, le curseur du menu ne bouge pas
        elif f.get('grille'): self.hovered = [port, h[0], 0] if f['cur'] != h[0] else None
        elif self.cur_local.get((port, f['ordre'])) != h[0]: self.cur_local[(port, f['ordre'])] = h[0]; self.hovered = None

    def _is_button(self, port, nid):
        """Vrai si l'element a un dessin de bouton (plaque, partie 7) ou de fleche (partie 10) : le cadre de fenetre qui couvre l'ecran (manette 128) n'en est pas un."""
        node = self.ui_g.f[port].N.get(nid) if self.ui_g and port in self.ui_g.f else None
        return bool(node) and any(m.get('part') in (7, 10) for m in node['mats'])

    def on_mouse_leave(self, x, y):
        self.hover_node = None
        if self.pause.opened: self.pause.output()                       # menu Echap : le pointeur a quitte la fenetre, plus rien n'est survole (les plaques se rallument)

    def _step_toward_hover(self):
        """Un appui de direction vers le bouton survole (menus dont le curseur est dans le moteur), tant que le curseur n'y est pas (au plus 24 appuis)."""
        sv = self.hovered; eng = self.engine
        if not sv: return
        port, b, n = sv; f = eng.ui.f.get(port)
        if f is None or not f.get('grille') or port != eng.active_menu() or f['cur'] == b or n >= 24: self.hovered = None; return
        if self.n % 3: return
        cols = max(1, f['grille'][0]); cc, cr = f['cur'] % cols, f['cur'] // cols; tc, tr = b % cols, b // cols
        pad = (1 if tr > cr else 2) if tr != cr else (4 if tc > cc else 8)       # manette du jeu : bas 1, haut 2, droite 4, gauche 8
        eng.send_menu(port, 1, -1, pad); self.menu_to_release = port; sv[2] += 1

    def on_mouse_release(self, x, y, button, modifiers):
        """Relachement sur le meme bouton (PUSH_STATE_FINISH) : MenuPort.Send([1, numero du bouton, touche de manette du bouton])."""
        if not self._ready: return
        if button == pyglet.window.mouse.MIDDLE: self._wheel_release(); return
        if self.pause.opened: self.pause.release(x, y, button); return
        if self.license_panel is not None: self.license_panel.dragging = None; return
        if button == pyglet.window.mouse.LEFT and self.hud.dpad_on:
            if self.hud.dpad_release() and self._terrain_free(): self.click_a = True              # toucher du rond central de la croix (sans glisser) = touche d'action, comme sur mobile (#131)
            return
        if button == pyglet.window.mouse.LEFT and self.hud.press_state:
            n = self.hud.let_go(x, y, self.hud.visible_ones())
            if n == HM.BATTLE: self.change_battle_speed('bouton')                      # bouton de vitesse de l'ecran de combat : ne passe rien au moteur
            elif n: self.hud_decl = HM.DECL[n]
            return
        if button != pyglet.window.mouse.LEFT or not self.press_state: return
        port, b, pad = self.press_state; self.press_state = None
        h = self._button_under(port, x, y)
        if b == -1 and pad == 0x400:                       # bouton retour : MenuPortItem.Update ajoute 0x400 aux touches du jeu (le moteur ferme la carte) au lieu d'envoyer un message au port
            if h and h[0] == b: self.hud_decl = BTN_CHAT
            return
        if b == -1 and pad == 2:                           # bouton « mode de la carte » de la fenetre (type 22, icone 19 / 20 / 2 envoyee par le moteur) : haut de la manette = change de vue (traite avec la touche Carte)
            if h and h[0] == b and h[1] == pad: self.map_toggle = True
            return
        if h and h[0] == b and b == BTN_SAVES and self._is_start_menu(port): self._open_saves(); return                # bouton « Sauvegardes » du menu de depart (a la place de « Sauv. cloud ») : propre au portage
        if h and h[0] == b and port in self.engine.input_menus():
            self.engine.send_menu(port, 1, b, pad); self.menu_to_release = port
            f = self.engine.ui.f.get(port)
            if f: f['cur'] = b

    def pad(self):
        """Manette du jeu d'apres les touches reglees : directions, A (action / valider), B (annuler). Sur le terrain, les fleches gauche / droite sont celles de la camera (boutons de camera du jeu, voir _bits_camera) et les directions
        sont celles de l'ecran : c'est le jeu qui les tourne selon sa camera, comme sur mobile ; dans un menu, un message ou un combat, les fleches deviennent des directions."""
        p = 0; free = self._terrain_free()
        for action, bit in (('haut', ENGINE.UP), ('bas', ENGINE.DOWN), ('gauche', ENGINE.LEFT), ('droite', ENGINE.RIGHT)):
            if self._held(action): p |= bit
        if not free:
            for action, bit in (('cam_haut', ENGINE.UP), ('cam_bas', ENGINE.DOWN), ('cam_gauche', ENGINE.LEFT), ('cam_droite', ENGINE.RIGHT)):
                if self._held(action): p |= bit
        else:
            p |= self.hud.dpad_bits()                                                                        # croix a l'ecran tenue a la souris : une direction de plus (relative a l'ecran, comme les touches)
        if self._held('A'): p |= ENGINE.A
        if self._held('B'): p |= ENGINE.B
        return p

    def _hud_sfx(self, name_str):
        """Touche Commandes / Discussion / Carte sur le terrain : le bruitage 300 du bouton a l'ecran, dans les memes situations qu'au doigt (#60, D-156 ; le bouton est-il permis par le moteur, qu'il soit affiche ou non)."""
        if self.hud.allowed(name_str): self.sound.play_sfx(SFX_BUTTON)

    def _edges(self):
        """Appuis (front montant) de X, Start, L et R depuis la derniere image du moteur."""
        r = {}; K = pyglet.window.key; k = self.key_list
        for a in EDGE_ACTIONS:
            if a == 'discussion': v = any(k[c] and c not in self.swallowed for c in self.reg.codes(a) if c not in (K.LALT, K.RALT))        # (Alt : au relachement, voir alt_tap : Alt + Entree ne doit pas lancer la discussion de groupe)
            else: v = self._held(a)
            r[a] = v and not self.prev_action.get(a, False); self.prev_action[a] = v
        if self.alt_tap: r['discussion'] = True; self.alt_tap = False
        if r['discussion'] and os.environ.get('DQ_DEBUG'): print('FRONT discussion n=%d' % self.n, flush=True)
        if self.swallowed: self.swallowed = {c for c in self.swallowed if k[c]}          # (une touche avalee relachee hors de la fenetre : la liste se vide)
        if self.alt_cand and not (k[K.LALT] or k[K.RALT]): self.alt_cand = False
        return r

    def _entries(self, p):
        """Touches et clics de ce pas du moteur -> (p, decl) : boutons tenus et boutons qui viennent d'etre presses, tels que le moteur les veut (menu qui a la saisie : tout passe par `_menu_input`, p = decl = 0).
        Seulement dans les pas « reels » : un pas supplementaire d'un combat accelere (`tick(mute=True)`) n'en lit aucune, pour que la cadence des touches (repetition des fleches, premier appui) ne change pas."""
        eng = self.engine; terrain = False
        if self.click_a: p |= ENGINE.A; self.click_a = False                  # clics de souris : page suivante / annuler
        if self.click_b: p |= ENGINE.B; self.click_b = False
        decl = p & ~self.pad_prev                      # boutons qui viennent d'etre presses
        fr = self._edges()
        if self.engine.msg_visible and fr['menu']: p |= ENGINE.A; decl |= ENGINE.A        # Entree et Espace tournent aussi les pages des messages
        for bit in (ENGINE.UP, ENGINE.DOWN, ENGINE.LEFT, ENGINE.RIGHT):      # repetition des directions maintenues (curseurs de menu)
            if p & bit:
                self.rep[bit] = self.rep.get(bit, 0) + 1
                if self.rep[bit] > 12 and (self.rep[bit] - 12) % 4 == 0: decl |= bit
            else: self.rep[bit] = 0
        self.pad_prev = p
        eng = self.engine
        if self.menu_to_release is not None:                 # fin de l'appui OK / Annuler envoye au menu
            eng.send_menu(self.menu_to_release, 1, -1, 0); self.menu_to_release = None
        game_map = self._map_ports() if not eng.msg_visible else {}
        if bool(game_map) != self.map_open: self.map_open = bool(game_map); self.map_view = 1           # carte ouverte : premiere version
        entries = bool(game_map) and 24 in game_map and 25 in game_map and eng.ui.f.get(game_map[24], {}).get('cases') and eng.shops()[1] > 0          # ville avec des boutiques : la carte a une 2e vue, la liste des boutiques (type 24)
        self.map_two_views = (25 in game_map and 26 in game_map) or bool(entries)
        if game_map:
            # Touche Carte : 1re fois la premiere version (en ville : le plan), 2e fois l'autre version (en ville : la liste des boutiques ; haut de la manette sur la fenetre du plan : FieldImageMap::execute), 3e fois ferme (bouton retour : 0x400, comme MenuPortItem.Update d'Unity) ;
            # Annuler ou le bouton retour ferment aussi. Le curseur et les fleches ne servent pas ici (sauf les fleches de la liste des boutiques : boutique precedente / suivante).
            do_toggle, self.map_toggle = self.map_toggle, False
            if entries:                                              # ville : M = plan, puis liste des boutiques, puis ferme ; le bouton « mode de la carte » alterne plan / liste
                in_entries = bool(eng.ui.f.get(game_map[24], {}).get('vis'))
                if do_toggle: eng.send_menu(game_map[25], 1, -1, 2); self.menu_to_release = game_map[25]
                elif fr['carte'] and not in_entries: eng.send_menu(game_map[25], 1, -1, 2); self.menu_to_release = game_map[25]
                elif fr['carte'] or (decl & ENGINE.B): self.hud_decl = BTN_CHAT
                elif in_entries and decl & (ENGINE.LEFT | ENGINE.RIGHT): eng.send_menu(game_map[24], 1, -1, 4 if decl & ENGINE.RIGHT else 8); self.menu_to_release = game_map[24]         # fleches de la liste : boutique suivante / precedente
            elif (fr['carte'] and self.map_view == 1 or do_toggle) and self.map_two_views:           # (le bouton de l'ecran « mode de la carte » change de vue dans les deux sens)
                eng.send_menu(game_map[25], 1, -1, 2); self.menu_to_release = game_map[25]; self.map_view = 3 - self.map_view; fr['carte'] = False
            elif fr['carte'] or (decl & ENGINE.B): self.hud_decl = BTN_CHAT
        port = None if game_map or self.saves_screen is not None else eng.active_menu()
        if port is not None and eng.msg_visible and not eng.ui.f[port].get('entree'): port = None
        if port is not None and eng.msg_visible and decl & ENGINE.A and self._quit_only(port): port = None          # arene (combat) : la seule fenetre ouverte est « Quitter » (manette 0x400) et A doit tourner la page du message (touche du terrain pour le moteur)
        if port is not None: port = self._keyboard_port(port)      # critere memoire seul : le message d'abord
        if port is not None and self.menu_to_release is None: self._step_toward_hover()
        if port is not None:                               # un menu attend les touches : elles lui sont envoyees, pas au terrain
            f_port = eng.ui.f.get(port)
            self._menu_input(port, decl | (ENGINE.A if fr['menu'] else 0) | (ENGINE.B if fr['carte'] and f_port and f_port.get('type') == 25 else 0) | (ENGINE.LEFT if fr['L'] else 0) | (ENGINE.RIGHT if fr['R'] else 0), (1 if fr['L'] else 0) | (2 if fr['R'] else 0))        # L / R = gauche / droite (page precedente / suivante des menus a une colonne)
            p = decl = 0
        elif self.title_screen is not None:                       # ecran-titre : seul A valide (Espace, Entree ou toucher) ; ni marche, ni camera
            p = decl = ENGINE.A if (decl & ENGINE.A or fr['menu']) else 0
        elif (self.name_entry.active and not eng.msg_visible) or self.license_panel is not None or self.saves_screen is not None: p = decl = 0           # saisie du nom, ecran Licence : tout passe par le clavier du portage
        elif not eng.msg_visible:
            # sur le terrain : A = parler / examiner, Annuler, X ou Start = ouvrir le menu (le moteur veut ces boutons seuls)
            hd, self.hud_decl = self.hud_decl, 0                # (le moteur veut ces boutons seuls) A, puis boutons a l'ecran, puis touches Commandes / Discussion / Carte
            if decl & ENGINE.A:
                decl = BTN_TALK
            elif hd: decl = hd
            elif fr['menu']: decl = BTN_MENU; self._hud_sfx('menu')
            elif fr['discussion']: decl = BTN_CHAT; self._hud_sfx('discussion')
            elif fr['carte']: decl = BTN_MAP; self._hud_sfx('carte')
            p &= ~(ENGINE.A | ENGINE.B)
            terrain = True; p |= self._bits_camera()                          # (sur le terrain, les bits 4 et 5 des touches tenues sont les boutons de camera du jeu : gauche, droite, les deux = retour au nord)
        elif decl & ENGINE.A: p, decl = EN.touch_for_engine(p, decl, ENGINE.A, ENGINE.B, BTN_TALK, eng.awaits_touch())          # message ouvert : A tourne la page (0x10) ; le menu du don d'experience, a son dernier etat, attend le toucher d'ecran (0x100 seul)
        if not terrain: self._camera_oublier()          # (ni menu, ni message, ni titre : une rotation demandee a la souris ou un retour au nord en attente ne partent pas apres coup)
        return p, decl
