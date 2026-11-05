"""Messages, fenetres de menu du jeu et editeur d'interface ; fondus, vignette et petits messages des sauvegardes (toasts)."""
import os, random, time
import numpy as np
import pyglet
from pyglet import gl
from pyglet.graphics.shader import Shader
from pyglet.graphics.shader import ShaderProgram
from dq4_pc.battle import battle_effect as EC
from dq4_pc.language import tr, N_
from dq4_pc.window import inputs as EN
from dq4_pc.menus import ui_menu as UI
from dq4_pc.core import engine as ENGINE
from dq4_pc.persistence import settings as RG
from dq4_pc.window.constants import (BTN_SAVES, CB_MSG_BOTTOM, CB_ZONE_MENUS, CENTERED_WINDOWS, MSG_BOTTOM, YESNO_BOX_SPACING, FONTS, SFX_BUTTON,
    UI_ZOOM)
from dq4_pc.window.shaders import FRAG_GRADIENT, VERTEX_GRADIENT
from dq4_pc.window.helpers import without_validation


class MenusMixin:
    """Messages, fenetres de menu du jeu et editeur d'interface ; fondus, vignette et petits messages des sauvegardes (toasts)."""

    def toast(self, text, duration=1.8):
        """Petit message en haut de l'ecran, SEULEMENT pour les sauvegardes (etats instantanes, sauvegarde du jeu impossible, import) : depuis #267 les autres notifications (vitesse de combat, plein ecran, memoire du moteur, reglages, son...) n'existent plus (D-228) ;
        les sauvegardes les ont retrouvees le 04/11/2026 (D-230). tests/test_save_notifications.py garde la liste des appels permis."""
        self.toasts = [(tr(text), time.time() + duration)]            # (D-238 : le texte est traduit ici ; un texte a trous doit l'etre avant d'etre formate : toast(tr('Etat %d') % n))

    def ui_g_reset(self):
        """Refait les fenetres de menu d'origine d'apres la memoire de l'interface (apres le chargement d'un etat)."""
        if self.ui_g is None: return
        self.ui_g.f.clear(); self.engine.ui.obs = self.ui_g; self.ui_g.replay(self.engine.ui)

    SAMPLE_HEIGHT = 87                                                  # hauteur (pixels du canevas) d'un echantillon de message : 3 lignes de 28 pixels + 3 de marge (voir ui_menu.limit_lines)

    SAMPLE_TEXTS = ((N_("Aperçu d'un message."),),                                                      # textes d'essai de l'editeur d'interface (1 a 3 lignes, comme une boite de dialogue) : un au hasard a chaque choix de « Dialogues » ; chaque ligne est traduite au dessin
              (N_("Ceci est un texte de test."), N_("Il sert à régler la taille et"), N_("la position des dialogues.")),
              (N_("Aperçu d'un message"), N_("sur deux lignes.")),
              (N_("Voici un exemple de dialogue."), N_("Déplace et redimensionne cette"), N_("fenêtre comme tu le souhaites.")),
              (N_("Texte d'essai : les messages du jeu"), N_("s'afficheront ici, à cette taille.")))

    def new_sample(self):
        """L'editeur choisit le texte d'essai montre dans la fenetre de dialogue : au hasard parmi SAMPLE_TEXTS (autre que le precedent)."""
        n = len(self.SAMPLE_TEXTS); p = getattr(self, '_trial', None)
        self._trial = random.choice([k for k in range(n) if k != p]); self._sample_seen = None

    def _preview_canvas(self):
        """Canevas 512 x 512 de l'apercu des dialogues : le texte d'essai choisi, en police du jeu, range des la 1re rangee."""
        if getattr(self, '_trial', None) is None: self.new_sample()
        cv = np.zeros((512, 512), np.uint8)
        from PIL import Image, ImageDraw, ImageFont
        im = Image.new('L', (512, self.SAMPLE_HEIGHT), 0); dr = ImageDraw.Draw(im)
        try: f = ImageFont.truetype(os.path.join(self.args.cache, 'ui_font.otf'), 22)
        except Exception: f = ImageFont.load_default()
        for j, t in enumerate(self.SAMPLE_TEXTS[self._trial % len(self.SAMPLE_TEXTS)]): dr.text((4, 7 + 28 * j + 20), tr(t), font=f, fill=255, anchor='ls')
        cv[:self.SAMPLE_HEIGHT] = np.asarray(im)
        return cv

    def _update_message(self):
        """Texte visible du message (canevas du moteur) -> image RGBA blanche dont l'opacite est celle du texte."""
        if self.ui_msg:                                          # fenetre d'origine : tout le canevas (512 x 512, en boucle) + defilement par decalage d'UV
            a = self.engine.read_canvas()
            if a is not None:
                lookup_key = hash(a.tobytes())
                if lookup_key != self.canvas_key:
                    self.canvas_key = lookup_key; self.ui_render.update_canvas(a)
                    if os.environ.get('DQ_UIDBG'):                                  # (test) lignes de texte du canevas : (premiere rangee, derniere rangee)
                        r = np.where(a.max(1) > 40)[0]; g = []
                        if len(r):
                            s0 = p0 = r[0]
                            for q in r[1:]:
                                if q > p0 + 3: g.append((int(s0), int(p0))); s0 = q
                                p0 = q
                            g.append((int(s0), int(p0)))
                        print('CANEVAS image %s lignes %s msg %s moteur (lignes, hauteur, defil) %s' % (self.engine.frames, g, self.engine.ui.msg, self.engine.params_message()), flush=True)
            m = self.engine.ui.msg; typ = m['type']
            if typ == 1 and a is not None and a[(np.arange(102, 164) + (int(m['y']) & 0x1ff)) % 512].max() > 40: typ = 4       # message de combat de 4 lignes (4 groupes de monstres) : cadre d'origine
            self.ui_msg.select_language(typ, m['y'], m['feed'], m.get('qui', ''))
            return
        a = self.engine.read_message()
        if a is None: self.msg_img = None; return
        h = a.shape[0]
        lookup_key = hash(a.tobytes())
        if lookup_key == self.msg_key: return
        self.msg_key = lookup_key; self.msg_h = h
        rgba = np.empty((h, a.shape[1], 4), np.uint8); rgba[..., :3] = 255; rgba[..., 3] = a
        self.msg_img = pyglet.image.ImageData(a.shape[1], h, 'RGBA', np.ascontiguousarray(rgba[::-1]).tobytes(), pitch=a.shape[1] * 4)
        t = self.msg_img.get_texture()
        gl.glBindTexture(t.target, t.id)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)

    def _clone_screen(self, battle=True):
        """Copie l'image qui vient d'etre dessinee dans une texture (la capture que l'effet de debut de combat brise en morceaux, ou que les effets voyage, lampe et Riremito deforment : `battle` faux, voir capture_effects.py)."""
        w, h = self.get_framebuffer_size()
        if self.effect_tex is not None: self.effect_tex.delete()
        t = pyglet.image.Texture.create(w, h, internalformat=gl.GL_RGBA8)
        gl.glBindTexture(t.target, t.id)
        gl.glCopyTexSubImage2D(t.target, 0, 0, 0, 0, 0, w, h)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glGenerateMipmap(t.target)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        self.effect_tex = t
        if not battle: return
        self.sim_effect = EC.TilesEffect(self.width / max(1, self.height))
        n = self.sim_effect.rows * EC.COLS * 6
        if self.effect_vl is not None: self.effect_vl.delete()
        self.effect_vl = self.program_effect.vertex_list(n, gl.GL_TRIANGLES, position=('f', self.sim_effect.positions().ravel().tolist()), tex_coords=('f', self.sim_effect.UV.ravel().tolist()), colors=('f', self.sim_effect.colors().ravel().tolist()))

    def _paint_background_gradient(self, topmost, bottom):
        """Fond des villes (#111) : degrade vertical de la couleur `topmost` (haut de l'image) a la couleur `bottom`, tel que le dessine le `BackColor` du jeu (voir VERTEX_GRADIENT), par-dessus l'effacement (la moyenne des deux) et
        avant la scene ; la profondeur n'est ni lue ni ecrite. Rien a faire si les deux couleurs sont egales (l'effacement est deja cette couleur)."""
        if self.program_gradient is None:
            self.program_gradient = ShaderProgram(Shader(VERTEX_GRADIENT, 'vertex'), Shader(FRAG_GRADIENT, 'fragment'))
            self.gradient_vl = self.program_gradient.vertex_list(6, gl.GL_TRIANGLES, position=('f', [1.0, 1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0, -1.0, 1.0, -1.0]))
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glDisable(gl.GL_BLEND)
        self.program_gradient.use(); self.program_gradient['haut'] = tuple(float(c) for c in topmost); self.program_gradient['bas'] = tuple(float(c) for c in bottom)
        self.gradient_vl.draw(gl.GL_TRIANGLES)
        self.program_gradient.stop()
        gl.glEnable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    def _draw_vignette(self):
        """Assombrit les bords de l'image de jeu (reglage Vignettage), sous le fondu et l'interface : degrade radial elliptique (centre intact jusqu'a 45 % du rayon, bords en noir
        d'opacite = reglage). Texture 512 x 288 etiree sur la fenetre (filtre lineaire), creee une fois."""
        v = float(self.reg['vignette'])
        if v <= 0.005: return
        t = getattr(self, '_vignette_tex', None)
        if t is None:
            n, m = 512, 288; yy, xx = np.mgrid[0:m, 0:n]; r = np.hypot((xx + 0.5) / n * 2 - 1, (yy + 0.5) / m * 2 - 1)
            k = np.clip((r - 0.45) / (1.3 - 0.45), 0.0, 1.0); k = k * k * (3 - 2 * k)
            a = np.zeros((m, n, 4), np.uint8); a[..., 3] = np.round(255 * k).astype(np.uint8)
            t = self._vignette_tex = self._tex(a, False)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        sp = pyglet.sprite.Sprite(t, x=0, y=0); sp.scale_x = self.width / t.width; sp.scale_y = self.height / t.height; sp.opacity = int(round(255 * min(1.0, v))); sp.draw()

    def _draw_fade(self, background=False):
        """Plans de fondu d'ecran (Fade.FadePlane, bit 14 du paquet 9 = Fade.l_targetLayer) : `background` = plan « FadeForBG » (Custom/BackFade, file Background : devant la scene, derriere les fenetres et les messages) ;
        sinon plan « FadeForMenu » (Custom/FrontFade, file Overlay : devant tout, fenetres et messages compris)."""
        e = self.engine.state; fd = e.background_fade if background else e.fade
        if fd['a'] <= 0.004: return
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        r = pyglet.shapes.Rectangle(0, 0, self.width, self.height, color=tuple(int(round(255 * min(max(c, 0.0), 1.0))) for c in fd['col']))
        r.opacity = int(round(255 * min(fd['a'], 1.0)))
        r.draw()

    def _draw_message(self):
        if self.ui_msg: return                                   # dessinee avec les fenetres d'origine (_draw_menus)
        if self.msg_img is None or not self.engine.msg_visible: return
        ui_scale = self.height / 720.0 * 1.3                       # taille du texte : 1 pixel du canevas = 1,3 pixel a 720p
        tl, tn = ENGINE.CANVAS_L * ui_scale * 0.78, self.msg_h * ui_scale
        margin = 18 * ui_scale
        bw, bh = tl + 2 * margin, tn + 2 * margin
        bx, by = (self.width - bw) / 2, 22 * ui_scale
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        border = pyglet.shapes.BorderedRectangle(bx, by, bw, bh, border=max(2, int(3 * ui_scale)), color=(8, 12, 70), border_color=(245, 245, 245))
        border.opacity = 235
        border.draw()
        spr = pyglet.sprite.Sprite(self.msg_img, x=bx + margin, y=by + bh - margin - self.msg_h * ui_scale)
        spr.scale = ui_scale
        spr.draw()

    # ---- menus
    def _menu_lines(self, f):
        """Cases d'une fenetre -> lignes (numero de ligne du moteur, texte, etiquette, valeur, est_un_titre)."""
        rows = {}
        for (r, c), t in f['cases'].items(): rows.setdefault(r, {})[c] = t
        out = []
        for r in sorted(rows):
            cols = rows[r]
            pre, lab, val = cols.get(5, ''), cols.get(2, ''), cols.get(3, '')
            main_part = ' '.join(' '.join(t.split('\n')) for c, t in sorted(cols.items()) if c not in (2, 3, 5) and t)     # retours a la ligne -> espaces (resume d'action : « Attaquer ▼ cible »)
            if not (main_part or val or lab): continue
            out.append((r, (pre + ' ' + main_part).strip(), lab, val, main_part.rstrip().endswith('?')))
        return [l for l in out if l[4]] + [l for l in out if not l[4]]

    def _keyboard_port(self, port):
        """Port qui recoit le clavier : celui du menu actif du moteur, sauf si c'est une fenetre a un seul bouton (menu Divers : la saisie va a « Sauvegarde rapide », ouverte en dernier) alors qu'une fenetre
        visible plus fournie existe (la liste de la page) : c'est elle qu'on parcourt (le toucher agit sur toutes les fenetres)."""
        if port is None or not self.ui_g: return port
        eng = self.engine
        def n(q):
            wnd = self.ui_g.f.get(q); return sum(1 for b in wnd.buttons() if b[1] & 0x10) if wnd else 0
        if n(port) > 1: return port
        cand = [q for q, f in eng.ui.f.items() if q > 1 and f['vis'] and f['cases'] and q in self.ui_g.f and n(q) > 1]
        return max(cand, key=lambda q: eng.ui.f[q]['ordre']) if cand else port

    def _quit_only(self, port):
        """Fenetre « Quitter » de l'arene des monstres (type 71) : en combat, sans bouton de validation ni curseur du moteur."""
        return self.engine.state.part == ENGINE.PART_BATTLE and without_validation(self.engine, self.ui_g, port)

    def _port_for_gamepad(self, port, pad):
        """Port qui recoit la touche de manette `pad` (haut 2, bas 1, droite 4, gauche 8, A 16, B 32) : celui du menu actif s'il a un bouton pour elle, sinon la fenetre visible la plus recente qui en a un.
        Menu Divers : le moteur donne la saisie a la fenetre « Sauvegarde rapide », mais le bouton retour est dans la liste et les fleches de page dans une troisieme fenetre."""
        eng = self.engine
        def a(q):
            wnd = self.ui_g.f.get(q) if self.ui_g else None
            return bool(wnd) and any(b[1] & pad for b in wnd.buttons())
        if a(port): return port
        for q in sorted((q for q, f in eng.ui.f.items() if q > 1 and f['vis'] and q in self.ui_g.f), key=lambda q: -eng.ui.f[q]['ordre']):
            if a(q): return q
        return port

    def _menu_input(self, port, decl, pages=0):
        """Touches -> menu actif, comme MenuPort.Send d'Unity : [1, numero de bouton, manette] (manette du jeu : bas 1, haut 2, droite 4, gauche 8, A 16, B 32).
        Menu a curseur du moteur (message 2 : colonnes x lignes, ex. Oui / Non) : les touches lui sont transmises, il deplace son curseur (messages 4) et valide ;
        gauche/droite sur une seule colonne = precedent/suivant. Menu tactile (boutons sans curseur du moteur) : curseur local deplace d'apres la position des boutons, A = toucher."""
        eng = self.engine; f = eng.ui.f[port]
        if decl: self.hover_node = None                                # une touche : le curseur reprend la main (rangee entiere en surbrillance)
        dirs = ((ENGINE.UP, 2), (ENGINE.DOWN, 1), (ENGINE.LEFT, 8), (ENGINE.RIGHT, 4))
        wnd = self.ui_g.f.get(port) if self.ui_g else None
        z = {b: ((x0 + x1) / 2, (z0 + z1) / 2) for b, pad, x0, z0, x1, z1, _ in (wnd.buttons() if wnd else []) if b >= 0 and pad & 0x10}
        if not f.get('grille') and len(z) <= 1 and self._step_entry(port, f, wnd, z, decl): return          # menu de saisie numerique (mise, jetons, montant) : fleches = colonnes et ▲ / ▼
        if pages and not f.get('grille') and len({round(c[0] / 20.0) for c in z.values()}) >= 2:          # L / R (page precedente / suivante) dans une liste a plusieurs colonnes (bestiaire) : gauche / droite y changent de colonne, ce sont donc les fleches ◀ ▶ de page de la fenetre qui sont pressees
            fl = self._page_arrow(port, 8 if pages & 1 else 4)
            if fl: eng.send_menu(fl[0], 1, fl[1], 8 if pages & 1 else 4); self.menu_to_release = fl[0]; return
        if not f.get('grille') and len(z) < 1 and decl & (ENGINE.LEFT | ENGINE.RIGHT):           # fenetre sans curseur du moteur ni bouton A (pages du Statut, types 13-17) : gauche / droite (Q, D, L, R) tournent les pages avec les fleches d'une autre fenetre (type 6), comme un toucher
            pad = 4 if decl & ENGINE.RIGHT else 8; q = self._port_for_gamepad(port, pad)
            if q != port: eng.send_menu(q, 1, -1, pad); self.menu_to_release = q; return
        if f.get('grille') or len(z) < 1:
            for bit, pad in dirs:
                if decl & bit:
                    if bit in (ENGINE.LEFT, ENGINE.RIGHT) and not f.get('grille') and self._page_arrow(port, pad):         # fenetre sans bouton de validation mais avec ses fleches de page (fiche du bestiaire) : gauche / droite les pressent
                        fl = self._page_arrow(port, pad); eng.send_menu(fl[0], 1, fl[1], pad); self.menu_to_release = fl[0]; return
                    if bit in (ENGINE.LEFT, ENGINE.RIGHT) and (f.get('grille') or (1, 1, 1))[0] < 2: pad = 2 if bit == ENGINE.LEFT else 1
                    eng.send_menu(port, 1, -1, pad); self.menu_to_release = port; return
            if decl & ENGINE.A:
                action = next((b for b, pd, *_ in (wnd.buttons() if wnd else []) if pd & 0x800), None)          # « Action » de la fiche du bestiaire (manette 0x800) : la seule fenetre qui en a un
                if action is not None and not f.get('grille'): eng.send_menu(port, 1, action, 0x800); self.menu_to_release = port; self.sound.play_sfx(SFX_BUTTON)
                else: eng.send_menu(port, 1, -1, 0x10); self.menu_to_release = port; self.sound.play_sfx(SFX_BUTTON)
            elif decl & ENGINE.B: q = self._port_for_gamepad(port, 0x20); eng.send_menu(q, 1, -1, 0x20); self.menu_to_release = q
            return
        lookup_key = (port, f['ordre']); cur = self.cur_local.get(lookup_key)
        if cur not in z:
            cur = self.cur_local[lookup_key] = f['cur'] if f['cur'] in z else min(z, key=lambda b: (-round(z[b][1]), z[b][0]))       # depart : le bouton en haut a gauche
        if decl & (ENGINE.LEFT | ENGINE.RIGHT) and wnd and wnd.typ in (58, 59, 63):                       # quantite (types 58 / 59 : liste « Acheter », 63 : quantite a vendre) : la rangee du curseur porte ses propres fleches (boutons de meme numero, manette gauche 8 / droite 4 : liste « Acheter » d'une boutique, quantite a vendre) -> gauche / droite changent la quantite de la rangee choisie (comme le toucher d'une fleche) ; le curseur garde la rangee entiere
            pad = 4 if decl & ENGINE.RIGHT else 8
            if any(b == cur and pd & pad for b, pd, *_ in wnd.buttons()): eng.send_menu(port, 1, cur, pad); self.menu_to_release = port; return
        if len({round((x0 + x1) / 20.0) for b, pad, x0, z0, x1, z1, _ in (wnd.buttons() if wnd else []) if b >= 0 and pad & 0x10}) <= 1 and decl & (ENGINE.LEFT | ENGINE.RIGHT):       # une seule colonne : gauche / droite tournent les pages si une autre fenetre porte les fleches
            pad = 4 if decl & ENGINE.RIGHT else 8; q = self._port_for_gamepad(port, pad)
            if q != port: eng.send_menu(q, 1, -1, pad); self.menu_to_release = q; return
        for bit, _ in dirs:
            if decl & bit: cur = self.cur_local[lookup_key] = self._neighbor(z, cur, bit)
        if decl and os.environ.get('DQ_MENUDBG'): print('MENU curseur local image %d port %d decl %d -> %s ; boutons %s' % (self.n, port, decl, cur, {b: (round(c[0]), round(c[1])) for b, c in z.items()}), flush=True)
        if decl & ENGINE.A and cur == BTN_SAVES and self._is_start_menu(port): self.sound.play_sfx(SFX_BUTTON); self._open_saves()
        elif decl & ENGINE.A: eng.send_menu(port, 1, cur, 0x10); self.menu_to_release = port; self.sound.play_sfx(SFX_BUTTON)
        elif decl & ENGINE.B: q = self._port_for_gamepad(port, 0x20); eng.send_menu(q, 1, -1, 0x20); self.menu_to_release = q

    def _page_arrow(self, port, pad):
        """Fleche de page ◀ (manette 8) ou ▶ (manette 4) de la fenetre `port` : (port, numero de bouton), ou None. Les fleches de quantite des boutiques (types 58, 59, 63 : une par rangee) n'en sont pas."""
        wnd = self.ui_g.f.get(port) if self.ui_g else None
        if wnd is None or wnd.typ in (58, 59, 63): return None
        for b, pd, *_ in wnd.buttons():
            if pd & pad: return (port, b)
        return None

    def _step_columns(self, wnd):
        """Colonnes ▲ / ▼ d'un menu de saisie numerique (mise de la machine a sous et du poker, jetons, montant de la banque, pari de l'arene : Make_Casino_*, Make_Bank*) : numeros de bouton >= 0 qui ont
        a la fois un element de manette 0x2 (▲, valeur + 1 rang) et un de manette 0x1 (▼), de gauche a droite. Vide pour les autres fenetres (les ▲ / ▼ de numero -1 sont des fleches de page)."""
        if wnd is None: return []
        bs = wnd.buttons(); topmost = {b for b, pad, *_ in bs if b >= 0 and pad & 0x2}; bottom = {b for b, pad, *_ in bs if b >= 0 and pad & 0x1}
        cx = {b: (x0 + x1) / 2 for b, pad, x0, z0, x1, z1, _ in bs if b in topmost & bottom and pad & 0x3}
        return sorted(cx, key=lambda b: cx[b])

    def _active_step(self, port):
        """Colonne ▲ / ▼ choisie au clavier dans un menu de saisie numerique (la plus a droite au depart : les unites), ou None si la fenetre n'en a pas (ou si elle a plusieurs boutons de validation : curseur ordinaire)."""
        wnd = self.ui_g.f.get(port) if self.ui_g else None; f = self.engine.ui.f.get(port)
        if wnd is None or f is None or f.get('grille'): return None
        cols = self._step_columns(wnd)
        if not cols or sum(1 for b in wnd.buttons() if b[0] >= 0 and b[1] & 0x10) > 1: return None
        c = self.cursor_step.get((port, f['ordre'])); return c if c in cols else cols[-1]

    def _step_entry(self, port, f, wnd, z, decl):
        """Menu de saisie numerique au clavier (les boutons ▲ / ▼ sont des touches de manette 0x2 / 0x1, hors du curseur local) : gauche / droite choisissent la colonne (dizaines, unites...), haut / bas = ▲ / ▼ de la colonne
        (envoyes au moteur comme le toucher du bouton), A = le bouton de validation (Lancer, Donner, Valider), B = retour. Faux si la fenetre n'est pas de ce genre ou si aucune touche utile n'est pressee."""
        if not decl & (ENGINE.UP | ENGINE.DOWN | ENGINE.LEFT | ENGINE.RIGHT | ENGINE.A | ENGINE.B): return False
        cols = self._step_columns(wnd)
        if not cols: return False
        eng = self.engine; lookup_key = (port, f['ordre']); action = self._active_step(port)
        if action is None: return False
        self.hover_node = None                                                       # une touche : le curseur reprend la main
        if decl & (ENGINE.LEFT | ENGINE.RIGHT):
            i = cols.index(action) + (1 if decl & ENGINE.RIGHT else -1); self.cursor_step[lookup_key] = cols[min(max(i, 0), len(cols) - 1)]
        elif decl & (ENGINE.UP | ENGINE.DOWN): eng.send_menu(port, 1, action, 2 if decl & ENGINE.UP else 1); self.menu_to_release = port
        elif decl & ENGINE.A: eng.send_menu(port, 1, next(iter(z), -1), 0x10); self.menu_to_release = port; self.sound.play_sfx(SFX_BUTTON)
        else: q = self._port_for_gamepad(port, 0x20); eng.send_menu(q, 1, -1, 0x20); self.menu_to_release = q
        return True

    @staticmethod
    def _neighbor(z, cur, bit):
        """Bouton voisin dans la direction pressee (z : numero -> centre en unites d'interface, Z vers le haut) ; au bord on boucle vers l'autre extremite de la rangee/colonne."""
        x, y = z[cur]
        if bit in (ENGINE.LEFT, ENGINE.RIGHT):
            direction = 1.0 if bit == ENGINE.RIGHT else -1.0
            before = [(b, (c[0] - x) * direction + 3.0 * abs(c[1] - y)) for b, c in z.items() if (c[0] - x) * direction > 4.0]
            if before: return min(before, key=lambda t: t[1])[0]
            candidates = [(b, abs(c[1] - y) * 100.0 - (c[0] - x) * direction) for b, c in z.items() if b != cur and abs(c[1] - y) < 12.0]
        else:
            direction = 1.0 if bit == ENGINE.UP else -1.0
            before = [(b, (c[1] - y) * direction + 3.0 * abs(c[0] - x)) for b, c in z.items() if (c[1] - y) * direction > 4.0]
            if before: return min(before, key=lambda t: t[1])[0]
            candidates = [(b, abs(c[0] - x) * 100.0 - (c[1] - y) * direction) for b, c in z.items() if b != cur and abs(c[0] - x) < 12.0]
        return min(candidates, key=lambda t: t[1])[0] if candidates else cur

    def _lbl(self, text, size_value, color=(255, 255, 255, 255), fonts=()):
        """Etiquette de texte (mise en cache) ; `fonts` : familles essayees avant les polices du systeme (police du jeu pour le menu Echap)."""
        k = (text, round(size_value, 1), color, fonts)
        l = self.lbl_menu.get(k)
        if l is None:
            if len(self.lbl_menu) > 400: self.lbl_menu.clear()
            l = self.lbl_menu[k] = pyglet.text.Label(text, font_name=tuple(fonts) + FONTS, font_size=size_value, color=color, anchor_x='left', anchor_y='baseline')
        return l

    def _helptext_margin(self):
        """(cote, largeur) du bloc d'infos de F1 : en haut a DROITE de l'ecran par defaut ; largeur = la marge libre a cote de la colonne d'interface (portrait 450 x 800 centre), pour ne pas cacher les fenetres du jeu (voir entrees.info_zone)."""
        return EN.info_zone(self.width, self.height, bool(self.ui_render), UI_ZOOM, self.args.ui_pos)

    def _cursor(self, port):
        """Bouton en surbrillance du menu actif : curseur du moteur (messages 4) ou, sans curseur du moteur, curseur local des fleches."""
        f = self.engine.ui.f[port]
        if f.get('grille'): return f['cur']
        step = self._active_step(port)
        if step is not None: return step                                  # menu de saisie numerique : la colonne ▲ / ▼ choisie
        return self.cur_local.get((port, f['ordre']), f['cur'])

    def _ui_reference(self):
        """Colonne d'interface du jeu (portrait 450 x 800 centre, hauteur de la fenetre) : (x du centre, y du centre, pixels par unite)."""
        ui_scale = self.height / 800.0 * self.ui_k
        return {'centre': self.width / 2, 'droite': self.width - 225 * ui_scale, 'gauche': 225 * ui_scale}.get(self.args.ui_pos, self.width / 2), self.height / 2.0, ui_scale

    def window_names(self):
        """Noms (Make_* de MenuPortItemTable, sans le prefixe) des fenetres du jeu qui ont une mise en page : {nom: [numeros de type]} (editeur d'interface)."""
        if getattr(self, '_make_names', None) is None:
            self._make_names = {}
            if self.ui_g is not None:
                for num, t in self.ui_g.ml.types.items():
                    if t.get('err') not in (None, 'None') or not t.get('nodes'): continue
                    self._make_names.setdefault(t.get('name', '').replace('Make_', '').replace('()', '') or 'type%s' % num, []).append(int(num))
        return self._make_names

    def _type_name(self, typ):
        m = getattr(self, '_type_names', None)
        if m is None: m = self._type_names = {n: name_str for name_str, nums in self.window_names().items() for n in nums}          # numero de type -> nom Make_* (une fois par partie : appele pour chaque fenetre a chaque image)
        return m.get(typ)

    def _hidden(self, typ):
        """Fenetre du jeu masquee par le joueur (editeur d'interface : « Afficher cette interface a l'ecran » = Non) ?"""
        ms = self.reg['interface_masquees']
        return bool(ms) and self._type_name(typ) in ms

    def _yesno_on_message(self, msg, wnd):
        """Pile Oui / Non (D-231) posee sur le coin haut droit de la boite de dialogue : -> (decalage vertical en unites qui pose le bord bas VISIBLE de la pile YESNO_BOX_SPACING au-dessus du bord haut visible de la boite,
        (bord droit visible de la boite, bord droit visible de la pile)). Les cadres ont des marges transparentes differentes (6 unites a droite pour la boite) : on aligne ce qu'on voit, pas les mailles. None si une mesure manque."""
        mv = msg.visible_extent() if msg is not None else None; ev = wnd.visible_extent()
        if not mv or not ev: return None
        return float(mv[3] + YESNO_BOX_SPACING - ev[2]), (float(mv[1]), float(ev[1]))

    def _ui_yesno(self, base, D, e0, v, edges=None):
        """Oui / Non (type 1) regle par le joueur : il suit la fenetre de message comme d'habitude (base = (cx, cy, s) de celle-ci, D = decalage vertical d'unites qui l'y colle, e0 = son bord bas en unites),
        puis sa taille v[0] se change autour de son bord bas et de son bord droit, et il se decale de v[1], v[2] (fractions de l'ecran).
        bords = (bord droit de la fenetre de message, bord droit du Oui / Non) en unites : la pile de Oui / Non a son bord droit sur celui de la boite de dialogue (D-231). -> (cx, cy, s) de dessin."""
        bx, by, bs = base; s2 = bs * float(v[0]); y_bottom = by + (D + e0) * bs + float(v[2]) * self.height
        x = bx + float(v[1]) * self.width + ((edges[0] * bs - edges[1] * s2) if edges else 0.0)
        return x, y_bottom - e0 * s2, s2

    def _ui_custom(self, mode, s, v):
        """Repere (cx, cy, s) d'une fenetre modifiee par le joueur (editeur d'interface) : taille v[0] autour du bord de son groupe (bas, haut ou milieu de l'ecran), puis decalage v[1], v[2] en fraction de l'ecran."""
        s2 = s * float(v[0]); H = float(self.height)
        cy = 400.0 * s2 if mode == 'bas' else (H - 400.0 * s2 if mode == 'haut' else H / 2.0)
        return self._ui_reference()[0] + float(v[1]) * self.width, cy + float(v[2]) * H, s2

    def _update_preview_canvas(self, wnd):
        if getattr(self, '_trial', None) is None: self.new_sample()
        if getattr(self, '_sample_seen', None) != self._trial:
            self._sample_seen = self._trial; self.ui_render.update_canvas(self._preview_canvas(), 'msg_apercu')
            wnd.select_language(0, 0, False)

    def _preview_window(self, lookup_key):
        """Fenetre d'apercu de l'editeur d'interface (gardee) : 'msg' = dialogues (texte d'essai), sinon le nom Make_* ; None si elle n'a pas de mise en page."""
        if not hasattr(self, '_previews'): self._previews = {}
        wnd = self._previews.get(lookup_key)
        if wnd is None:
            if lookup_key == 'msg':
                wnd = UI.MessageWindow(self.ui_g.ml); wnd.select_language(0, 0, False); wnd.N['canevas']['mats'][0]['sheet'] = 'msg_apercu'          # (texte d'essai : canevas a part, pas celui du moteur)
            else:
                nums = self.window_names().get(lookup_key)
                if not nums: return None
                wnd = UI.Window(self.ui_g.ml, nums[0])
                if wnd.extent() is None:                                                    # parties cachees tant que le moteur ne les demande pas (bandeau de l'equipe en combat, jetons du stade...) : l'apercu les montre toutes
                    for node in wnd.N.values(): node['act'] = True
            self._previews[lookup_key] = wnd
        return wnd

    def preview_interface(self, lookup_key):
        """Editeur d'interface : apercu de la fenetre `lookup_key` ('msg' = dialogues, sinon nom Make_*) a sa taille et sa place (mise en page d'origine, sans etat de jeu) -> (x0, y0, x1, y1) en pixels, ou None."""
        if self.ui_render is None or self.ui_g is None: return None
        wnd = self._preview_window(lookup_key)
        if wnd is None: return None
        if lookup_key == 'msg': self._update_preview_canvas(wnd)
        e = wnd.extent()
        if not e: return None
        if lookup_key == 'YesNo': return self._yesno_preview(wnd, e)
        dz = (MSG_BOTTOM - wnd.bottom()) if lookup_key == 'msg' else 0.0
        k, gr, modes = self._ui_scale([(e[0] + dz, e[1] + dz)]); s = self.height / 800.0 * k
        mode = modes[0] if modes else 'bas'
        v = self.reg['interface_fenetres'].get(lookup_key) or RG.default_window(lookup_key)
        cx, cy, s2 = self._ui_custom(mode, s, v)
        wnd.selected = None; wnd.selected_node = None; wnd.press_node = None
        self.ui_render.draw_all([wnd], cx, cy + dz * s2, s2, (self.width, self.height))
        x0, x1 = cx - 225 * s2, cx + 225 * s2; y0, y1 = cy + (e[0] + dz) * s2, cy + (e[1] + dz) * s2          # cadre jaune : emprise de la fenetre
        pyglet.shapes.Box(x0, y0, x1 - x0, y1 - y0, thickness=2, color=(255, 235, 130)).draw()
        return x0, y0, x1, y1

    def _yesno_preview(self, wnd, e):
        """Apercu de Oui / Non : comme dans le jeu, la pile (Oui au-dessus de Non) est posee sur le coin haut droit de la fenetre de message (montree a sa place, avec ses reglages), bords droits alignes ; son cadre jaune est celui de l'element regle."""
        fm = self._preview_window('msg'); self._update_preview_canvas(fm); em = fm.extent()
        if not em: return None
        pose = self._yesno_on_message(fm, wnd); dzm = MSG_BOTTOM - fm.bottom(); D = dzm + (pose[0] if pose else em[1] + YESNO_BOX_SPACING - e[0])
        k, gr, modes = self._ui_scale([(em[0] + dzm, em[1] + dzm), (e[0] + D, e[1] + D)]); s = self.height / 800.0 * k
        mode = modes[0] if modes else 'bas'; ov = self.reg['interface_fenetres']
        cxm, cym, sm = self._ui_custom(mode, s, ov.get('msg') or RG.DEFAULT_WINDOW)
        fm.selected = None; fm.selected_node = None; wnd.selected = None; wnd.selected_node = None
        self.ui_render.draw_all([fm], cxm, cym + dzm * sm, sm, (self.width, self.height))
        cx, cy, s2 = self._ui_yesno((cxm, cym, sm), D, e[0], ov.get('YesNo') or RG.DEFAULT_WINDOW, pose[1] if pose else None)
        self.ui_render.draw_all([wnd], cx, cy, s2, (self.width, self.height))
        ex = wnd.extent_x(); x0, x1 = (cx + ex[0] * s2, cx + ex[1] * s2) if ex else (cx - 225 * s2, cx + 225 * s2); y0, y1 = cy + e[0] * s2, cy + e[1] * s2          # (cadre jaune : la pile Oui / Non)
        pyglet.shapes.Box(x0, y0, x1 - x0, y1 - y0, thickness=2, color=(255, 235, 130)).draw()
        return x0, y0, x1, y1

    def _ui_scale(self, intervals):
        """Agrandissement des fenetres : intervalles [(bas, haut)] en unites d'interface -> (k, mode de chaque groupe).
        Les fenetres proches (moins de 60 unites) forment un groupe ; un groupe du bas (resp. du haut, resp. du milieu) est agrandi autour du bord bas
        (haut, centre) de l'ecran, pour rester colle a ce bord. k = UI_ZOOM, reduit (jusqu'a 1) tant qu'un groupe sort de l'ecran ou en recouvre un autre."""
        H = float(self.height); ui_scale = H / 800.0
        gr = []
        for lo, hi in sorted(intervals):
            if gr and lo - gr[-1][1] < 60.0: gr[-1][1] = max(gr[-1][1], hi)
            else: gr.append([lo, hi])
        modes = ['bas' if (lo + hi) / 2 < -100 else 'haut' if (lo + hi) / 2 > 100 else 'centre' for lo, hi in gr]
        def y(z, mode, s): return (z + 400.0) * s if mode == 'bas' else H - (400.0 - z) * s if mode == 'haut' else H / 2 + z * s
        kmax = min(UI_ZOOM, self.width / (450.0 * ui_scale))
        k = kmax
        while k > 1.0:
            s = ui_scale * k; iv = [(y(lo, m, s), y(hi, m, s)) for (lo, hi), m in zip(gr, modes)]
            if all(a >= -0.5 and b <= H + 0.5 for a, b in iv) and all(iv[i + 1][0] - iv[i][1] >= 8.0 for i in range(len(iv) - 1) if iv[i + 1][0] >= iv[i][0]): break
            k -= 0.01
        return max(k, 1.0), gr, modes

    def _dz_message(self, ports):
        """Fenetre de message du terrain : l'original la pose au-dessus de la zone des menus du bas (portrait) ; en 16/9 on la descend en bas de l'ecran,
        sauf si une autre fenetre occupe le bas (elle resterait dessous)."""
        m = self.ui_msg
        battle = self.engine.state.part == ENGINE.PART_BATTLE          # combat : le message se pose au meme endroit que le menu de commandes (meme bord bas, meme echelle)
        if self.args.msg_origine or not m or (m.type != 0 and not battle): return 0.0
        b = m.bottom()
        if any(self.ui_g.f[p].typ != 1 and self.ui_g.f[p].bottom() < b - 2 for p in ports): return 0.0
        return (CB_MSG_BOTTOM if battle else MSG_BOTTOM) - b

    def _zones(self, port):
        """Zones tactiles de la fenetre d'un port : [(numero, manette, x0, y0, x1, y1, profondeur, identifiant de l'element)] en pixels."""
        wnd = self.ui_g.f.get(port) if self.ui_g else None
        if not wnd or self._hidden(wnd.typ): return []
        cx, cy, ui_scale = self.ui_tf.get(port) or self._ui_reference(); dz = getattr(self, 'ui_dzp', {}).get(port, 0.0)
        return [(b, pad, cx + x0 * ui_scale, cy + (z0 + dz) * ui_scale, cx + x1 * ui_scale, cy + (z1 + dz) * ui_scale, pr, nid) for b, pad, x0, z0, x1, z1, pr, nid in wnd.buttons(True)]

    def _draw_menus(self):
        if self.pause.opened and self.pause.screen_page == 'interface': return       # editeur d'interface : seul l'element choisi est montre (par le menu Echap), pas les fenetres du jeu
        eng = self.engine
        active = self._keyboard_port(eng.active_menu())
        if os.environ.get('DQ_UIDBG'):                      # (test) etat des fenetres a chaque changement : port, type, visible, fenetre d'origine ou menu simple
            state = tuple(sorted((p, f['type'], f['vis'], p in (self.ui_g.f if self.ui_g else ()), len(f['cases'])) for p, f in eng.ui.f.items() if f['vis'] or f['type'] is not None))
            if state != getattr(self, '_ui_state', None):
                self._ui_state = state; print('UI image %d actif=%s : %s' % (self.n, active, ' '.join('%d:t%s%s%s c%d' % (p, t, '' if v else '(cache)', '[O]' if o else '[simple]', c) for p, t, v, o, c in state)), flush=True)
        if self.ui_render:
            entries = sorted((f['ordre'], p) for p, f in eng.ui.f.items() if f['vis'] and p in self.ui_g.f)
            if eng.state.part == ENGINE.PART_BATTLE and max(float(eng.state.fade['a']), float(eng.state.background_fade['a'])) >= 0.6: entries = []       # fin de combat : le jeu ferme le fondu au noir alors que la fenetre de statut est encore « visible » (le message, lui, reste : « Ragnar meurt ! » se lit sur le noir) : sinon l'ecran noir montre une boite seule en haut a gauche
            if self.saves_screen is not None: entries = []                                 # ecran Sauvegardes ouvert : le menu de depart est cache (sinon il se devine a travers le cadre translucide)
            wins_v = [self.ui_g.f[p] for _, p in entries]; self.ui_render.neighbors = wins_v
            for wnd in wins_v:
                if wnd.typ == 53: wnd.center_menu(); wnd.auto_plate()          # menu de depart : groupe centre en hauteur, dans un cadre noir (dessine plus bas) ; plaque « Sauvegarde automatique » toujours visible, grisee et inactive sans data5.dat lisible
            should_hide = self._battle_end_box()
            msg = bool(self.ui_msg and eng.msg_visible and 'msg' in self.ui_render.tex and not should_hide)
            dz = self._dz_message([p for _, p in entries]) if msg else 0.0
            self.ui_dz = dz; self.ui_followers = {p for _, p in entries if self.ui_g.f[p].typ == 1} if msg else set()      # le Oui/Non (type 1) suit la fenetre de message (D-231 : toujours, a sa place d'origine ou descendue)
            self.ui_dzp = {}; ui_edges = {}                   # decalage vertical de chaque fenetre qui suit le message : le meme que lui, plus de quoi poser la pile Oui/Non sur le bord haut du message ; bords droits a aligner (D-231)
            for p in self.ui_followers:
                pose = self._yesno_on_message(self.ui_msg, self.ui_g.f[p]) if msg else None
                self.ui_dzp[p] = dz + (pose[0] if pose else 0.0); ui_edges[p] = pose[1] if pose else None
            ivs = {}
            for _, p in entries:
                e = self.ui_g.f[p].extent()
                if e: ivs[p] = (e[0] + self.ui_dzp.get(p, 0.0), e[1] + self.ui_dzp.get(p, 0.0))
            if msg:
                e = self.ui_msg.extent()
                if e: ivs['msg'] = (e[0] + dz, e[1] + dz)
            k, gr, modes = self._ui_scale(list(ivs.values()) + ([CB_ZONE_MENUS] if self.engine.state.part == ENGINE.PART_BATTLE else [])); self.ui_k = k       # combat : echelle constante (la zone des menus de commandes compte toujours), sinon les fenetres changent de taille a chaque message
            H = float(self.height); s = H / 800.0 * k; cx = self._ui_reference()[0]
            def mode_of(lookup_key):                                 # 'bas', 'haut' ou 'centre' : bord de l'ecran auquel est collee la fenetre
                if lookup_key not in ivs: return 'bas'
                lo, hi = ivs[lookup_key]; i = next((j for j, g in enumerate(gr) if g[0] - 1e-6 <= lo and hi <= g[1] + 1e-6), 0); return modes[i] if modes else 'bas'
            def ref_frame(lookup_key):                                  # (cy, echelle) du groupe de fenetres qui contient cette fenetre
                m = mode_of(lookup_key)
                return (400.0 * s if m == 'bas' else H - 400.0 * s if m == 'haut' else H / 2), s
            self.ui_tf = {p: (cx,) + ref_frame(p) for _, p in entries}
            ov = self.reg['interface_fenetres']; tf_msg = None; custom = {}; yes_no = {}           # fenetres modifiees par le joueur (taille, position) : dessinees a part, avec leur propre repere (les zones tactiles le suivent)
            mask = set(self.reg['interface_masquees'])                                  # interfaces masquees (« Afficher cette interface a l'ecran » = Non) : calculees comme les autres (la mise en page ne bouge pas), seul leur dessin est omis
            if ov and msg and ov.get('msg'): tf_msg = self._ui_custom(mode_of('msg'), s, ov['msg'])
            for _, p in entries:
                fe1 = self.ui_g.f[p]
                if fe1.typ != 1: continue
                name_str = self._type_name(1) or ''; v = ov.get(name_str) if (ov and name_str not in RG.REMOVED_WINDOWS) else None
                e1 = fe1.extent()
                if not e1: continue
                if p in self.ui_followers:                                                        # Oui / Non : pose sur le coin haut droit de la boite de dialogue (reglages du joueur relatifs a celle-ci)
                    D = self.ui_dzp.get(p, 0.0); base = tf_msg or (cx, ref_frame('msg')[0], s)
                    t2 = self._ui_yesno(base, D, e1[0], v or RG.DEFAULT_WINDOW, ui_edges.get(p))
                    self.ui_tf[p] = (t2[0], t2[1] - D * t2[2], t2[2]); yes_no[p] = t2
                elif v:                                                                      # sans boite de dialogue : a sa place, avec les reglages du joueur
                    t2 = self._ui_yesno((cx,) + ref_frame(p), 0.0, e1[0], v); self.ui_tf[p] = (t2[0], t2[1], t2[2]); custom[p] = t2
            if ov:
                for _, p in entries:
                    if self.ui_g.f[p].typ == 1 or p in self.ui_followers: continue
                    name_str = self._type_name(self.ui_g.f[p].typ) or ''; v = ov.get(name_str) if name_str not in RG.REMOVED_WINDOWS else None
                    if v: custom[p] = self.ui_tf[p] = self._ui_custom(mode_of(p), s, v)
            for _, p in entries:
                if self.ui_g.f[p].typ in CENTERED_WINDOWS and p not in custom:         # liste des journaux, choix du sexe : centrees a l'ecran dans un cadre noir (les boites de dialogue, elles, restent a leur place)
                    c = self.ui_g.f[p].center_visible()
                    if c: custom[p] = self.ui_tf[p] = (cx - c[0] * s, H / 2 - c[1] * s, s)
            for _, p in entries:
                if self.ui_g.f[p].typ == 25: self._plan_window(self.ui_g.f[p], eng.ui.f[p])
                elif self.ui_g.f[p].typ == 26: self._world_plan_window(self.ui_g.f[p], eng.ui.f[p])
            topmost, bottom = ([self.ui_msg] if msg else []), {}
            for _, p in entries:
                wnd = self.ui_g.f[p]
                wnd.selection(self.press_state[1] if self.press_state and self.press_state[0] == p else (self._cursor(p) if p == active else None))
                if self.press_state and self.press_state[0] == p:           # appui en cours : l'element est sombre tant que le pointeur est dessus ; s'il en sort, plus rien (MenuPortItem.Update, etat 2 : SetPush(touche)), s'il revient, il se rassombrit
                    h = self._button_under(p, *self.mouse); over = bool(h) and h[3] == self.press_node
                    wnd.selected_node = self.press_node if over else -1; wnd.press_node = self.press_node if over else None
                else:
                    wnd.press_node = None
                    wnd.selected_node = self.hover_node[1] if self.hover_node and self.hover_node[0] == p else (-1 if self.hover_node else None)       # souris : l'element pointe seul (-1 : fenetre non survolee, rien n'est allume par numero)
                if p in self.ui_followers: topmost.append(wnd)
                elif p not in custom: bottom.setdefault(self.ui_tf[p][1], []).append(wnd)
            for wnd in topmost:                                   # le message d'abord, puis chaque fenetre qui le suit (Oui/Non) a son propre decalage
                pf = next((p for _, p in entries if self.ui_g.f[p] is wnd), None); dzf = self.ui_dzp.get(pf, dz)
                if ('msg' in mask) if pf is None else self._hidden(self.ui_g.f[pf].typ): continue
                if pf in yes_no: self.ui_render.draw_all([wnd], yes_no[pf][0], yes_no[pf][1], yes_no[pf][2], (self.width, self.height))
                elif tf_msg: self.ui_render.draw_all([wnd], tf_msg[0], tf_msg[1] + dzf * tf_msg[2], tf_msg[2], (self.width, self.height))
                else: self.ui_render.draw_all([wnd], cx, ref_frame('msg')[0] + dzf * s, s, (self.width, self.height))
            for cy, wins_g in bottom.items():
                for wnd in wins_g:
                    if wnd.typ == 53: self._initial_border(wnd, cx, cy, s)
                self.ui_render.draw_all([wnd for wnd in wins_g if not self._hidden(wnd.typ)], cx, cy, s, (self.width, self.height))
            for p, tf in custom.items():
                if self._hidden(self.ui_g.f[p].typ): continue
                if self.ui_g.f[p].typ in CENTERED_WINDOWS: self._initial_border(self.ui_g.f[p], tf[0], tf[1], tf[2], True)
                self.ui_render.draw_all([self.ui_g.f[p]], tf[0], tf[1], tf[2], (self.width, self.height))
            self._anchor_battle_speed(entries, msg, dz, s, cx, ref_frame, tf_msg)
        wins = [(p, f) for p, f in eng.ui.visible_ones() if not (self.ui_g and p in self.ui_g.f)]
        if not wins: return
        ui_scale = self.height / 720.0; W, H = self.width, self.height
        size_value = 17 * ui_scale; rh = 36 * ui_scale; pad = 16 * ui_scale; gap = 18 * ui_scale
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        x_main = 40 * ui_scale
        for port, f in wins:
            lines = self._menu_lines(f)
            if not lines: continue
            # largeur : texte le plus large + zone etiquette/valeur
            left_width = max(self._lbl(l[1], size_value).content_width for l in lines)
            def stack(l): return bool((l[2] and '\n' in l[2]) or (l[3] and '\n' in l[3]))        # etiquettes/valeurs sur plusieurs lignes (PV / PM / Nv.)
            def block_width(l):
                if stack(l):
                    wl = max([self._lbl(t, size_value * 0.8).content_width for t in (l[2] or '').split('\n')] + [0]); wv = max([self._lbl(t, size_value).content_width for t in (l[3] or '').split('\n')] + [0])
                    return wl + 10 * ui_scale + wv
                return max(self._lbl(l[2], size_value * 0.8).content_width if l[2] else 0, self._lbl(l[3], size_value).content_width if l[3] else 0)
            right_width = max([block_width(l) for l in lines] + [0])
            tops = [rh * (0.3 + 0.62 * max(len((l[2] or '').split('\n')), len((l[3] or '').split('\n'))) if stack(l) else (1.5 if (l[2] and l[3]) else 1)) for l in lines]
            w = pad * 2 + 26 * ui_scale + left_width + (right_width + 24 * ui_scale if right_width else 0); h = pad * 2 + sum(tops)
            if port == 3: x, ytop = W - w - 24 * ui_scale, H - 24 * ui_scale
            elif port == 2: x, ytop = W - w - 40 * ui_scale, H * 0.62
            else: x, ytop = x_main, H - 24 * ui_scale; x_main += w + gap
            y = ytop - h
            background = pyglet.shapes.BorderedRectangle(x, y, w, h, border=max(2, int(3 * ui_scale)), color=(8, 12, 70), border_color=(255, 255, 255) if port == active else (150, 150, 170))
            background.opacity = 235; background.draw()
            cy = ytop - pad
            for (idx, left, lab, val, title_screen), hl in zip(lines, tops):
                base = cy - rh * 0.72
                if stack((idx, left, lab, val, title_screen)):
                    labs, vals = (lab or '').split('\n'), (val or '').split('\n')
                    wv = max([self._lbl(t, size_value).content_width for t in vals] + [0]); wl = max([self._lbl(t, size_value * 0.8).content_width for t in labs] + [0])
                    for i in range(max(len(labs), len(vals))):
                        yy = cy - rh * 0.62 * (i + 1) - rh * 0.05
                        if i < len(vals): e = self._lbl(vals[i], size_value); e.x = x + w - pad - e.content_width; e.y = yy; e.draw()
                        if i < len(labs): e = self._lbl(labs[i], size_value * 0.8); e.x = x + w - pad - wv - 10 * ui_scale - wl; e.y = yy; e.draw()
                    gy = cy - rh * 0.62 - rh * 0.05
                elif lab and val:
                    base = cy - rh * 0.72
                    e = self._lbl(lab, size_value * 0.8); e.x = x + w - pad - e.content_width; e.y = base; e.draw()
                    e = self._lbl(val, size_value); e.x = x + w - pad - e.content_width; e.y = base - rh * 0.5; e.draw()
                    gy = cy - rh * 0.95
                elif val:
                    e = self._lbl(val, size_value); e.x = x + w - pad - e.content_width; e.y = base; e.draw(); gy = base
                else: gy = base
                e = self._lbl(left, size_value, (255, 235, 130, 255) if title_screen else (255, 255, 255, 255)); e.x = x + pad + (0 if title_screen else 26 * ui_scale); e.y = gy if not (lab and val) or stack((idx, left, lab, val, title_screen)) else cy - rh * 0.72 - rh * 0.25; e.draw()
                if not title_screen and port == active and idx == f['cur']:
                    ty = (cy - hl / 2) if not (lab and val) else cy - rh * 0.6
                    pyglet.shapes.Triangle(x + pad, ty + 9 * ui_scale, x + pad, ty - 9 * ui_scale, x + pad + 15 * ui_scale, ty, color=(255, 235, 130)).draw()
                cy -= hl

    def _draw_helptext(self):
        """Lignes d'information (F1), en haut a droite par defaut. Dessinees aussi pendant les ecrans noirs et l'effet de debut de combat : sans cela elles clignotent a chaque changement de scene."""
        if not self.helptext: self.helptext_width = 0.0; return
        self._info()
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        stats = self.stats and bool(self.spacings)
        if stats:
            if self.n % 10 == 0 or not self.lbl_stats.text: self.lbl_stats.text = tr('%.0f images/s | moteur %.1f pas/s (%.1f ms) | pire image %.0f ms | dessin Python %.1f ms') % (len(self.spacings) / max(1e-6, sum(self.spacings)), (len(self.step_times) - 1) / max(1e-6, self.step_times[-1] - self.step_times[0]) if len(self.step_times) > 2 else 0.0, self.dt_engine * 1000, max(self.spacings) * 1000, self.dt_drawing * 1000)
        lines = [self.tag_label, self.lbl_hd] + ([self.lbl_stats] if stats else [])
        side, margin = self._helptext_margin()
        if (side, margin) != self.helptext_key: self.helptext_key = (side, margin); self.helptext_width = 0.0          # (fenetre redimensionnee, plein ecran, autre disposition : la largeur est recalculee)
        y = self.height - 10
        for l in lines:                                 # lignes d'information empilees, a la ligne dans la marge laissee libre par la colonne d'interface
            if l.width != margin: l.width = margin
            l.y = y; y -= l.content_height + 3
        bottom = y - 3                                       # cadre noir translucide derriere le texte (lisible sur le decor)
        self.helptext_width = max(self.helptext_width, max(l.content_width for l in lines) + 16)       # (la largeur ne fait que croitre tant que F1 reste affiche : le bord gauche du bloc, colle a droite, et le texte ne bougent pas quand un chiffre change)
        x0 = self.width - 4 - self.helptext_width if side == 'droite' else 4
        self.helptext_border.x, self.helptext_border.y = x0, bottom
        self.helptext_border.width, self.helptext_border.height = self.helptext_width, self.height - 4 - bottom
        self.helptext_border.draw()
        for l in lines: l.x = x0 + 6; l.draw()
