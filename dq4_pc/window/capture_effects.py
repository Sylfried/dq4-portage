"""Dessin des effets d'ecran de la classe `Capture` de la couche Unity (paquet 34 : voyage, lampe, Riremito ; voir rendu/capture_effects.py pour les regles) : capture de l'ecran du jeu, deux textures de flou a
demi-resolution en alternance (la remanence : a chaque pas de l'effet, l'etat de l'image precedente y est redessine), puis dessin du maillage de l'effet a la place de la scene, sur fond noir. L'interface (messages,
fenetres du jeu) et les plans de fondu restent dessines par-dessus, comme le fait la camera de l'interface de Unity (supposé : le contenu exact de cette camera pendant l'effet n'est pas lu)."""
import ctypes
import numpy as np
import pyglet
from pyglet import gl
from dq4_pc.render import capture_effects as EF
from dq4_pc.render.lamp_effect import LampEffect
from dq4_pc.render.riremito_effect import RiremitoEffect
from dq4_pc.render.tabi_effect import TabiEffect


def _gen(f):
    n = gl.GLuint(); f(1, ctypes.byref(n)); return n.value


class CaptureEffectsMixin:
    capture_ref = None; capture_ready = False; capture_sim = None; capture_rt = None; capture_fbo = None; capture_vl = None; capture_size = None      # effet en cours (dict de State.screen_effect), capture prise, simulation, textures et tampons de flou, listes de sommets

    def _capture_state(self, e):
        """L'effet Capture en cours (dict de State.screen_effect) ou None ; un nouvel effet remet la capture a faire (la premiere image est dessinee normalement puis copiee, voir _capture_grab)."""
        ef = getattr(e, 'screen_effect', None)
        if ef is not self.capture_ref: self.capture_ref = ef; self.capture_ready = False; self.capture_sim = None
        return ef

    def _capture_new_effect(self, ef):
        if ef['genre'] == 'tabi': return TabiEffect(ef['inverse'])
        if ef['genre'] == 'lampe': return LampEffect(ef['matin'])
        return RiremitoEffect()

    def _capture_grab(self, ef):
        """La scene du jeu vient d'etre dessinee (sans interface) : on la copie dans la texture de capture, on cree l'effet et les cibles de flou (noires au depart)."""
        self._clone_screen(battle=False)
        w, h = self.get_framebuffer_size(); w2, h2 = max(1, w // 2), max(1, h // 2)
        if self.capture_rt is None or self.capture_size != (w2, h2):
            for t in self.capture_rt or (): t.delete()
            for f in self.capture_fbo or (): gl.glDeleteFramebuffers(1, ctypes.byref(gl.GLuint(f)))
            self.capture_rt = []; self.capture_fbo = []
            for _ in range(2):
                t = pyglet.image.Texture.create(w2, h2, internalformat=gl.GL_RGBA8); gl.glBindTexture(t.target, t.id)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
                fbo = _gen(gl.glGenFramebuffers); gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fbo)
                gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, t.target, t.id, 0)
                self.capture_rt.append(t); self.capture_fbo.append(fbo)
            self.capture_size = (w2, h2)
        for fbo in self.capture_fbo:                              # textures de flou noires (le jeu ne les efface pas : contenu initial non etabli, noir suppose)
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fbo); gl.glClearColor(0.0, 0.0, 0.0, 1.0); gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0); gl.glViewport(0, 0, w, h)
        self.capture_vl = {}
        self.capture_sim = self._capture_new_effect(ef); self.capture_sim.on_blur = self._capture_blur_pass
        self.capture_ready = True

    def _capture_advance(self, ef):
        """Fait avancer l'effet jusqu'a l'appel de MoveNext qui correspond a l'image du moteur (plusieurs pas par image quand « Vitesse de transition » raccourcit l'effet)."""
        sim = self.capture_sim; target = EF.calls_made(ef['n'], ef['duree'], ef['images'])
        while sim.frames < target and not sim.finished: sim.stage()
        return sim

    def _capture_paint(self, sim, blur):
        """Les dessins de l'effet dans la cible courante : le fond lit la texture de flou `blur` (None : noire, rien a dessiner), la capture lit la copie de l'ecran du jeu."""
        prog = self.program_effect; prog.use(); prog['lum'] = 1.0; prog['flou'] = 0.0
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glActiveTexture(gl.GL_TEXTURE0)
        for k, (name_str, pos, uv, rgba) in enumerate(sim.drawings()):
            if name_str == 'flou':
                if blur is None: continue
                tex = self.capture_rt[blur]; gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ZERO)               # Custom/CaptureBlur : texture x couleur remplace l'ecran
            else:
                tex = self.effect_tex; gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)    # Custom/Capture
            vl = self.capture_vl.get(k)
            if vl is None: vl = self.capture_vl[k] = prog.vertex_list(len(pos), gl.GL_TRIANGLES, position=('f', pos.ravel().tolist()), tex_coords=('f', uv.ravel().tolist()), colors=('f', rgba.ravel().tolist()))
            else: vl.position[:] = pos.ravel().tolist(); vl.colors[:] = rgba.ravel().tolist()
            gl.glBindTexture(tex.target, tex.id); vl.draw(gl.GL_TRIANGLES)
        prog.stop()

    def _capture_blur_pass(self, sim, i):
        """Capture.Caputer, passe de flou : l'etat de l'image precedente (fond flou + maillage) est redessine dans la texture de demi-resolution `i`."""
        w, h = self.get_framebuffer_size()
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.capture_fbo[i]); gl.glViewport(0, 0, *self.capture_size)
        gl.glClearColor(0.0, 0.0, 0.0, 1.0); gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        self._capture_paint(sim, sim.blur_read)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0); gl.glViewport(0, 0, w, h)

    def _draw_capture_effect(self, sim):
        """Image de l'effet : fond noir, fond flou, maillage ; puis les plans de fondu et l'interface par-dessus (messages, fenetres du jeu)."""
        gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear()
        gl.glViewport(0, 0, *self.get_framebuffer_size())
        self._capture_paint(sim, sim.blur_read)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        self._draw_fade(True)
        self._update_message(); self._draw_message(); self._draw_menus(); self._draw_fade(); self._draw_helptext()
