"""Etats instantanes (sauvegarde / chargement a n'importe quel moment)."""
import os
import numpy as np
import pyglet
from pyglet import gl
from dq4_pc import paths as CH
from dq4_pc.language import tr, N_
from dq4_pc.core import engine as ENGINE
from dq4_pc.persistence import savestates as SS


class SnapshotsMixin:
    """Etats instantanes (sauvegarde / chargement a n'importe quel moment)."""

    @staticmethod
    def _state_number(symbol):
        K = pyglet.window.key
        digits = {K._1: 1, K._2: 2, K._3: 3, K._4: 4, K._5: 5, K._6: 6, K._7: 7, K._8: 8, K._9: 9,
                    K.NUM_1: 1, K.NUM_2: 2, K.NUM_3: 3, K.NUM_4: 4, K.NUM_5: 5, K.NUM_6: 6, K.NUM_7: 7, K.NUM_8: 8, K.NUM_9: 9}
        return digits.get(symbol)

    # ---- etats instantanes (savestates)
    def state_path(self, n): return os.path.join(CH.FOLDERS.savestates_folder(self.args.saves_write), 'state_%02d.dqs' % n)

    def state_info(self, n):
        """(infos, miniature PNG) de l'etat n, ou None."""
        return SS.info(self.state_path(n))

    def _location(self):
        """Lieu note dans le fichier de l'etat : un texte FRANCAIS stable (marque N_), jamais traduit ici ; la page des etats du menu Pause le traduit en l'affichant (Pause._et)."""
        e = self.engine.state
        if e.part == ENGINE.PART_CASINO: return N_('Casino : poker') if e.game_map == 'ev04' else (N_('Casino : machine à sous') if e.game_map == 'ev05' else N_('Casino'))          # (cartes ev04 / ev05 : voir Global::setMinigame)
        if e.part == ENGINE.PART_BESTIARY: return N_('Bestiaire')
        return N_('Carte du monde') if e.part == ENGINE.PART_FIELD else (N_('Combat') if e.part == ENGINE.PART_BATTLE else (e.game_map or '?'))

    def _complete_savestate(self):
        """Etat instantane du moteur + de la visionneuse (objets animes de la carte compris)."""
        viewer = {'objets_etat': self.objects.state if self.objects is not None else None, 'objets_auto': self.objects.auto if self.objects is not None else None,
                  'palettes': self.palettes.state() if self.palettes is not None else None, 'carte_nom': self.map_name, 'motif_n': self.pattern_n, 'motif_acc': self.acc_pattern.copy(), 'musique': self.sound.bgm_state()}
        return SS.snapshot(self.engine, viewer)

    def save_state(self, n, thumbnail_png=b''):
        """Enregistre l'etat du jeu dans l'emplacement n."""
        d = self._complete_savestate()
        SS.write(self.state_path(n), d, {'lieu': self._location(), 'carte': self.engine.state.game_map, 'partie': self.engine.state.part, 'images': self.engine.frames}, thumbnail_png)

    def load_state(self, n):
        """Recharge l'emplacement n ; l'etat d'avant le chargement est gardé en memoire (cancel_loading)."""
        d = SS.read(self.state_path(n))
        try: self.undo_state = self._complete_savestate()
        except Exception as ex: self.undo_state = None; print('state before loading not kept:', ex, flush=True)
        self._apply_savestate(d)

    def cancel_loading(self):
        """Revient a l'etat juste avant le dernier chargement (un deuxieme appel refait le chargement)."""
        if self.undo_state is None: self.toast(N_('Aucun chargement à annuler')); return False
        current = self._complete_savestate(); d, self.undo_state = self.undo_state, current
        self._apply_savestate(d); self.toast(N_('Chargement annulé'))
        return True

    def _apply_savestate(self, d):
        """Remet le moteur dans l'etat `d`, puis tout ce que la fenetre en a deduit (fenetres de menu, carte, objets animes, musique)."""
        eng = self.engine
        viewer = SS.apply(eng, d)
        self.ui_g_reset()
        self.map_name = None; self.field_key = None; self.prev = None; self.canvas_key = None; self.msg_key = None
        self.pad_prev = 0; self.rep = {}; self.menu_to_release = None; self.hovered = None; self.press_state = None; self.hover_node = None; self.cur_local = {}; self.cursor_step = {}; self.ref_effect = None; self.effect_tex_ready = False
        self.acc = 0.0; self.t_loop = None; self.anchor_effect = {}
        self.n_battle = 0 if eng.state.part != ENGINE.PART_BATTLE else self.n_battle
        e = eng.state
        if e.game_map and e.part != ENGINE.PART_FIELD and not e.game_map.startswith('btl_'):
            self._load_map(e.game_map)
        elif e.game_map and e.part == ENGINE.PART_BATTLE: self._load_map(e.game_map)
        if viewer and 'motif_acc' in viewer: self.pattern_n = viewer['motif_n']; self.acc_pattern[:] = viewer['motif_acc']; self.field_acc_seen = None          # eau animee de la carte du monde
        if viewer and viewer.get('objets_etat') and self.objects is not None:
            self.objects.reinit(); self.objects.restore(viewer['objets_etat'], viewer.get('objets_auto'))
            for tex, vl, key in self.map_vl:
                vl.position[:] = self.objects.cur[key].ravel(); vl.tex_coords[:] = self.objects.uv(key).ravel(); vl.colors[:] = self.objects.col(key).ravel()
            self.objects.dirty = set(); self.objects.dirty_uv = set(); self.objects.dirty_col = set()
        if viewer and viewer.get('palettes') and self.palettes is not None: self.palettes.select_language(viewer['palettes'])
        for sp in list(e.sprites.values()): self._sheet(sp['id'] - 4096 if (e.part == ENGINE.PART_FIELD and sp['id'] >= 4096) else sp['id'], self.mode)
        self.sound.restore_bgm(viewer.get('musique') if viewer else None, e.music)         # la musique repart du moment enregistre
        e.sounds = []

    def _clone_thumbnail(self):
        """Copie l'image du jeu (sans le menu) dans une texture, sur la carte graphique seulement : le menu s'ouvre sans attendre une relecture ; le PNG n'est fait qu'a l'enregistrement d'un etat."""
        try:
            w, h = self.get_framebuffer_size()
            t = pyglet.image.Texture.create(w, h, internalformat=gl.GL_RGBA8)
            gl.glBindTexture(t.target, t.id); gl.glCopyTexSubImage2D(t.target, 0, 0, 0, 0, 0, w, h)
            return t
        except Exception as ex:
            print('thumbnail failed:', ex, flush=True); return None

    def _png_thumbnail(self, t):
        """Texture de _clone_thumbnail -> PNG reduit (miniature des etats)."""
        if t is None: return b''
        try:
            import io
            from PIL import Image
            img = t.get_image_data()
            a = np.frombuffer(img.get_data('RGB', img.width * 3), np.uint8).reshape(img.height, img.width, 3)[::-1]
            im = Image.fromarray(np.ascontiguousarray(a)); im.thumbnail((320, 180)); b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()
        except Exception as ex:
            print('thumbnail failed:', ex, flush=True); return b''
