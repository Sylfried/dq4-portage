"""Ecrans d'avant-partie : titre (ciel, logo), licence, saisie du nom, sauvegardes."""
import os
import numpy as np
import pyglet
from pyglet import gl
from dq4_pc.language import tr, N_
from dq4_pc.menus import pre_game as AP
from dq4_pc.menus import saves_screen as ES
from dq4_pc.render import title_sky as CT
from dq4_pc.window.constants import EXTENDED_SKIES, SCENERY_BIAS, SFX_BUTTON


class TitleMixin:
    """Ecrans d'avant-partie : titre (ciel, logo), licence, saisie du nom, sauvegardes."""

    def _upscale_title_logo(self, loc, pos, Rb):
        """Ecran-titre : logo (modele 8901 : « DRAGON QUEST », « IV », sous-titre) et eclat anime (8900) agrandis de AP.LOGO_SCALE autour d'un meme point (pre_game.upscale_logo), sans decalage de profondeur.
        ECART VOULU avec l'APK (Sylfried, 03/11/2026, #108). Le facteur est reduit si le logo agrandi depasserait la largeur de la fenetre (fenetre tres etroite) ; DQ_LOGO_ECHELLE=1 : le logo d'origine."""
        try: wanted = float(os.environ.get('DQ_LOGO_ECHELLE', AP.LOGO_SCALE))
        except ValueError: wanted = AP.LOGO_SCALE
        if wanted == 1.0: return loc
        wid = 0.0; M = self._M_town
        if M is not None:
            try:
                xs = []
                for sx in (-1.0, 1.0):
                    q = np.array(pos, float) + Rb @ np.array([sx * AP.LOGO_HALF_WIDTH, 0.0, 0.0]); c = M @ np.append(q, 1.0); xs.append(c[0] / c[3])
                wid = abs(xs[1] - xs[0]) / 2.0                              # largeur du logo de l'APK, en fraction de la largeur de la fenetre (NDC : -1 a 1)
            except Exception: wid = 0.0
        try: y0 = float(os.environ.get('DQ_LOGO_Y', AP.LOGO_Y_FIXED))
        except ValueError: y0 = AP.LOGO_Y_FIXED
        return AP.upscale_logo(loc, AP.logo_factor(wid, wanted), y0)

    def _title_sky(self, c, src):
        """Ecran-titre : le ciel (carreaux de nuages identiques qui glissent) est concu pour l'ecran portrait ; en 16/9 ses bords entreraient dans le champ et le meme carreau se repeterait 3 a 6 fois.
        Solution : la zone portrait garde le ciel d'origine ; de chaque cote, des bandes de meme geometrie dont la texture est etiree de facon variable (title_sky.py : raccord continu au bord de la zone, defilement suivi).
        Secours (structure inattendue, ou DQ_CIEL_COPIES : ancien comportement, pour comparer) : deux copies du ciel decalees de sa largeur, qui prolongent le motif tel quel."""
        for iobj, nm in self.names.items():
            if 'kumo' not in nm.lower(): continue
            for key, start_idx, n in self.spans.get(iobj, []):
                if key not in c['textures']: continue
                if not os.environ.get('DQ_CIEL_COPIES'):
                    try:
                        cl = CT.WideSky(self.map_pos[key][start_idx:start_idx + n], self.objects.uv(key)[start_idx:start_idx + n], self.objects.col(key)[start_idx:start_idx + n])
                        only = start_idx == 0 and n == len(self.map_pos[key])                                                 # (le ciel est seul dans son groupe de texture)
                        if not os.environ.get('DQ_CIEL_BANDES') and only:
                            if os.environ.get('DQ_CIEL_AGRANDI'): self.zoom_sky = {'key': key}                          # essai #130 : ciel agrandi autour du centre de l'ecran, sans bandes
                            else: self.flat_sky = {'key': key, 'ciel': cl, 'vl': None, 'nv': 0, 'degrade': None, 'cle': None}      # #174 (par defaut) : ciel a plat, hauteur de la texture = hauteur de la fenetre, repetition sur la largeur, effet de vague
                            continue
                        self.ext_sky = {'ciel': cl, 'tex': self.tex_gl[(src, key)], 'key': key, 'deb': start_idx, 'vl': None, 'nv': 0}
                        continue
                    except Exception as ex: print(tr('Ciel du titre : %s (copies decalees a la place)') % ex, flush=True)
                cur = self.objects.cur[key][start_idx:start_idx + n]; wid = float(cur[:, 0].max() - cur[:, 0].min())
                for dx in (-wid, wid):
                    vl = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', CT.cloned_positions(cur, dx).ravel()), tex_coords=('f', self.objects.uv(key)[start_idx:start_idx + n].ravel()), colors=('f', self.objects.col(key)[start_idx:start_idx + n].ravel()))
                    self.ext_map.append((self.tex_gl[(src, key)], vl, key, start_idx, n, dx))

    def _extended_sky(self, c, src, name_str):
        """Plan de ciel des cartes de EXTENDED_SKIES (dpout, ev09 ; MAP-05) : concu pour l'ecran portrait, il s'arrete avant les bords de la fenetre en 16/9 (coins noirs). De part et d'autre, une copie SYMETRIQUE du plan (bord gauche et bord droit
        servent de miroir, memes coordonnees de texture : l'image se prolonge sans couture, a la maniere des copies du ciel du titre) ; la zone portrait centrale garde exactement le ciel d'origine. Ajoutee a `ext_map` (dessinee et mise a jour comme les copies du titre)."""
        words = EXTENDED_SKIES.get(name_str, ())
        for iobj, nm in self.names.items():
            if not any(m in nm.lower() for m in words): continue
            for key, start_idx, n in self.spans.get(iobj, []):
                if key not in c['textures'] or (src, key) not in self.tex_gl: continue
                cur = self.objects.cur[key][start_idx:start_idx + n]
                if not len(cur): continue
                for xe in (float(cur[:, 0].min()), float(cur[:, 0].max())):
                    dx = ('miroir', xe)
                    vl = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', CT.cloned_positions(cur, dx).ravel()), tex_coords=('f', self.objects.uv(key)[start_idx:start_idx + n].ravel()), colors=('f', self.objects.col(key)[start_idx:start_idx + n].ravel()))
                    self.ext_map.append((self.tex_gl[(src, key)], vl, key, start_idx, n, dx))

    def _paint_flat_sky(self, t):
        """Ciel de l'ecran-titre a plat (#174), a la place du groupe du ciel d'origine : la texture a la hauteur de la fenetre et se repete sur la largeur, avec l'effet de vague (title_sky.screen_sky ; defilement de l'objet suivi,
        degrade de teinte des rangees d'origine). -> True s'il a ete dessine ; toute erreur : False (le ciel d'origine est dessine par l'appelant) et le rendu a plat est coupe."""
        c = self.flat_sky
        if c is None or self._M_town is None: return False
        try:
            key = c['key']; cl = c['ciel']; phi = float(self.objects.cur[key][0, 0] - self.map_pos[key][0, 0])
            lookup_key = (np.asarray(self._M_town, float).tobytes(), float(self._town_aspect))
            if c['cle'] != lookup_key: c['degrade'] = CT.screen_gradient(self._M_town, cl.rows, cl.x_mil); c['cle'] = lookup_key
            P, U, C = CT.screen_sky(self._town_aspect, phi / cl.period, c['degrade']); n = len(P)
            if c['vl'] is None or c['nv'] != n:
                if c['vl'] is not None: c['vl'].delete()
                c['vl'] = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', P.ravel()), tex_coords=('f', U.ravel()), colors=('f', C.ravel())); c['nv'] = n
            else: c['vl'].position[:] = P.ravel(); c['vl'].tex_coords[:] = U.ravel(); c['vl'].colors[:] = C.ravel()
            self._linked_domain = None                          # sommets reecrits APRES le 1er trace de l'image : sans rebind + commit() ils ne partent pas (voir _paint_sky)
            gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
            self.prog['mvp'] = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)          # coordonnees d'ecran normalisees : pas de projection
            self._paint(t, c['vl'])
            self.prog['mvp'] = tuple(float(x) for x in self._M_town.T.ravel())
            gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
            return True
        except Exception as ex:
            self.flat_sky = None; self.prog['mvp'] = tuple(float(x) for x in self._M_town.T.ravel()); gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
            print(tr('Ciel du titre (a plat) desactive : %s') % ex, flush=True)
            return False

    def _paint_sky(self, r, sharp_o):
        """Bandes de ciel de l'ecran-titre (apres le decor opaque, meme plan que le ciel d'origine : decalage de profondeur pour passer devant sa partie hors de la zone portrait). Toute erreur : on garde le ciel d'origine seul."""
        c = self.ext_sky
        if c is None or self._M_town is None: return
        try:
            key = c['key']; phi = float(self.objects.cur[key][c['deb'], 0] - self.map_pos[key][c['deb'], 0])
            b = c['ciel'].bands(self._M_town, self._town_aspect, phi)
            if b is None: return
            P, U, C = b; n = len(P)
            if c['vl'] is None or c['nv'] != n:
                if c['vl'] is not None: c['vl'].delete()
                c['vl'] = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', P.ravel()), tex_coords=('f', U.ravel()), colors=('f', C.ravel())); c['nv'] = n
            else: c['vl'].position[:] = P.ravel(); c['vl'].tex_coords[:] = U.ravel(); c['vl'].colors[:] = C.ravel()
            t = r.get(key, c['tex']) if r else c['tex']
            self._linked_domain = None                          # sommets crees ou reecrits APRES le 1er trace de l'image (le decor opaque vient d'etre trace) : sans rebind + commit() ils ne partent pas : a la 1re image du titre les bandes manquaient (cotes noirs), puis elles etaient en retard d'une image
            gl.glEnable(gl.GL_POLYGON_OFFSET_FILL); gl.glPolygonOffset(0.0, -SCENERY_BIAS * (len(self.map_vl) + 2))
            self.prog['net'] = sharp_o if (r is None or key not in r) else 0.0; self.prog['tsize'] = (float(t.width), float(t.height)); self._paint(t, c['vl'])
            gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
        except Exception as ex:
            gl.glDisable(gl.GL_POLYGON_OFFSET_FILL); self.ext_sky = None
            print(tr('Ciel du titre (bandes) desactive : %s') % ex, flush=True)

    def _is_start_menu(self, port):
        """Vrai si ce port est le menu de depart (type 53, Make_StartMenuSecond)."""
        wnd = self.ui_g.f.get(port) if self.ui_g else None
        return bool(wnd and wnd.typ == 53)

    def _open_saves(self):
        if self.initial_status is None: self.initial_status = self.engine.catalog_status()          # etat des journaux quand le moteur a construit le menu de depart (ses boutons grises / absents en dependent)
        self.saves_screen = ES.SavesScreen(self); self.press_state = None; self.hover_node = None

    def _close_saves(self):
        s, self.saves_screen = self.saves_screen, None
        if s is not None and s.needs_reload: self._after_import()

    def _after_import(self):
        """Des journaux viennent d'etre importes (le catalogue du moteur a deja ete relu par l'ecran Sauvegardes)."""
        self.toast(N_('Sauvegardes importées'))                      # (N_ : marque le texte, que toast() traduit)

    def _initial_border(self, wnd, cx, cy, s, visible_ones=False):
        """Cadre noir (comme les autres menus du portage) derriere tout le menu de depart (ou de la fenetre d'avant-partie centree)."""
        r = wnd.menu_border(22.0, visible_ones)
        if r is None: return
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        self.pause._border(cx + r[0] * s, cy + r[1] * s, (r[2] - r[0]) * s, (r[3] - r[1]) * s, s * 800.0 / 900.0)
        self.pause._restore_blend()

    flat_sky = None                                                   # #174 (par defaut) : {'key': groupe du ciel du titre, 'ciel': WideSky, 'vl', 'nv', 'degrade', 'cle'} quand le ciel est dessine a plat a l'echelle de l'ecran (title_sky.screen_sky)

    zoom_sky = None                                                   # essai #130 (DQ_CIEL_AGRANDI=1) : {'key': groupe du ciel du titre} quand le ciel est agrandi (title_sky.screen_zoom) au lieu d'etre prolonge par des bandes

    def _update_title(self):
        """Port 12 = fenetre de type 73 (Make_TitleTouch) : le moteur ne lui donne aucune case, « Touchez l'ecran » et le copyright sont dessines par Unity (TapToStart) ; le code 0 est CountReset."""
        eng = self.engine; f = eng.ui.f.get(12)
        if bool(f and f.get('type') == 73 and f.get('act')):
            if self.title_screen is None: self.title_screen = AP.TitleTouch(eng.frames, self.pre_game_files); self.title_n = f.get('n_codes', {}).get(0, 0)
            n = f.get('n_codes', {}).get(0, 0)
            if n > self.title_n: self.title_screen.reset()
            self.title_n = n
            self.title_screen.do_update(eng.frames)
        else: self.title_screen = None
        self._update_name_entry(); self._update_license()
        if self.saves_screen is not None: self.saves_screen.do_update()

    def _update_license(self):
        """Fenetre de type 80 (Make_License) sur le port 15 : le texte des licences est dessine par Unity (LicenseNobu)."""
        eng = self.engine; port = next((q for q, f in eng.ui.f.items() if f.get('type') == 80 and not f.get('ferme')), None)
        if port is None: self.license_panel = None; return
        if self.license_panel is None: self.entry_port = port; self.license_panel = AP.License(self.pre_game_files.get('licence'))
        eng.state.fade['noir'] = 0                                         # (l'ecran reste noir tant que la fenetre est ouverte : pas de reouverture automatique apres 6 s)

    def _license_back(self):
        self.engine.send_menu(self.entry_port, 1, -1, 0x20); self.menu_to_release = self.entry_port                  # (retour : manette 0x20, muet comme dans MenuPortItem.Update)

    def _license_click(self, x, y, button):
        lic = self.license_panel; name_str = lic.zone(x, y)
        if button == pyglet.window.mouse.RIGHT: self._license_back(); return
        if lic.on_bar(x, y): lic.dragging = True; lic.drag_to(y); return                 # barre de defilement : le curseur se glisse avec le pointeur
        if name_str == 'retour': self._license_back()
        elif name_str == 'politique':
            self.sound.play_sfx(SFX_BUTTON)
            try: import webbrowser; webbrowser.open(AP.PRIVACY_URL)
            except Exception as ex: print(tr('Ouverture de la page de la politique de confidentialite impossible : %r') % (ex,), flush=True)

    def _draw_saves(self):
        if self.saves_screen is None: return
        cx, cy, ui_scale = self._ui_reference(); self.saves_screen.draw_all(self, cx, cy, ui_scale)

    def _draw_license(self):
        if self.license_panel is None: return
        cx, cy, ui_scale = self._ui_reference(); self.license_panel.draw_all(self, cx, cy, ui_scale)

    def _update_name_entry(self):
        """Fenetre de type 55 (StartNameEntry) : le clavier de saisie du nom est tenu par Unity ; il est visible tant que le moteur a envoye [12, 1, 1] (le message [12, 0, 8] donne le nombre de caracteres)."""
        eng = self.engine; port = next((q for q, f in eng.ui.f.items() if f.get('type') == 55 and not f.get('ferme')), None)
        f = eng.ui.f.get(port) if port is not None else None
        keyboard_on = bool(f and f['indic'].get(1) == 1)
        if keyboard_on and not self.name_entry.active: self.entry_port = port; self.name_entry.open_menu((f['indic'].get(0, 8) & 0xff) or 8)
        elif not keyboard_on and self.name_entry.active: self.name_entry.shutdown()

    def _name_entry_in_progress(self):
        return self.name_entry.active and not self.engine.msg_visible and not self.pause.opened

    def _name_entry_ok(self, name_str):
        """OK : [2, nombre d'octets] puis les octets UTF-8 du nom (deux par nombre, petit-boutiste), tous deux avant la prochaine image du moteur."""
        import struct
        b = name_str.encode('utf-8'); n = len(b); b += b'\0' * (n % 2)
        self.engine.send_menu(self.entry_port, 2, n); self.engine.send_menu(self.entry_port, *struct.unpack('<%dh' % (len(b) // 2), b))

    def _name_entry_back(self):
        """Retour : comme la touche B sur la fenetre 55, [1, -1, 32] (le moteur revient a la liste des journaux)."""
        self.engine.send_menu(self.entry_port, 1, -1, 0x20); self.menu_to_release = self.entry_port

    def _draw_name_entry(self):
        if not self.name_entry.active: return
        cx, cy, ui_scale = self._ui_reference(); self.name_entry.draw_all(cx, cy, ui_scale)

    def _draw_title(self):
        if self.title_screen is None: return
        cx, cy, ui_scale = self._ui_reference(); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        self.title_screen.draw_all(cx, cy, ui_scale, self.height)
