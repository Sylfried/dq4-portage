"""Dessin des effets d'ecran de la classe `Capture` de la couche Unity (paquet 34 : voyage, lampe, Riremito ; voir rendu/effets_capture.py pour les regles) : capture de l'ecran du jeu, deux textures de flou a
demi-resolution en alternance (la remanence : a chaque pas de l'effet, l'etat de l'image precedente y est redessine), puis dessin du maillage de l'effet a la place de la scene, sur fond noir. L'interface (messages,
fenetres du jeu) et les plans de fondu restent dessines par-dessus, comme le fait la camera de l'interface de Unity (supposé : le contenu exact de cette camera pendant l'effet n'est pas lu)."""
import ctypes
import numpy as np
import pyglet
from pyglet import gl
from dq4_pc.rendu import effets_capture as EF
from dq4_pc.rendu.effet_lampe import EffetLampe
from dq4_pc.rendu.effet_riremito import EffetRiremito
from dq4_pc.rendu.effet_tabi import EffetTabi


def _gen(f):
    n = gl.GLuint(); f(1, ctypes.byref(n)); return n.value


class EffetsCaptureMixin:
    capt_ref = None; capt_prete = False; capt_sim = None; capt_rt = None; capt_fbo = None; capt_vl = None; capt_taille = None      # effet en cours (dict de Etat.effet_ecran), capture prise, simulation, textures et tampons de flou, listes de sommets

    def _capt_etat(self, e):
        """L'effet Capture en cours (dict de Etat.effet_ecran) ou None ; un nouvel effet remet la capture a faire (la premiere image est dessinee normalement puis copiee, voir _capt_capturer)."""
        ef = getattr(e, 'effet_ecran', None)
        if ef is not self.capt_ref: self.capt_ref = ef; self.capt_prete = False; self.capt_sim = None
        return ef

    def _capt_nouvel_effet(self, ef):
        if ef['genre'] == 'tabi': return EffetTabi(ef['inverse'])
        if ef['genre'] == 'lampe': return EffetLampe(ef['matin'])
        return EffetRiremito()

    def _capt_capturer(self, ef):
        """La scene du jeu vient d'etre dessinee (sans interface) : on la copie dans la texture de capture, on cree l'effet et les cibles de flou (noires au depart)."""
        self._copier_ecran(combat=False)
        w, h = self.get_framebuffer_size(); w2, h2 = max(1, w // 2), max(1, h // 2)
        if self.capt_rt is None or self.capt_taille != (w2, h2):
            for t in self.capt_rt or (): t.delete()
            for f in self.capt_fbo or (): gl.glDeleteFramebuffers(1, ctypes.byref(gl.GLuint(f)))
            self.capt_rt = []; self.capt_fbo = []
            for _ in range(2):
                t = pyglet.image.Texture.create(w2, h2, internalformat=gl.GL_RGBA8); gl.glBindTexture(t.target, t.id)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
                fbo = _gen(gl.glGenFramebuffers); gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fbo)
                gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, t.target, t.id, 0)
                self.capt_rt.append(t); self.capt_fbo.append(fbo)
            self.capt_taille = (w2, h2)
        for fbo in self.capt_fbo:                              # textures de flou noires (le jeu ne les efface pas : contenu initial non etabli, noir suppose)
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fbo); gl.glClearColor(0.0, 0.0, 0.0, 1.0); gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0); gl.glViewport(0, 0, w, h)
        self.capt_vl = {}
        self.capt_sim = self._capt_nouvel_effet(ef); self.capt_sim.sur_flou = self._capt_passe_flou
        self.capt_prete = True

    def _capt_avancer(self, ef):
        """Fait avancer l'effet jusqu'a l'appel de MoveNext qui correspond a l'image du moteur (plusieurs pas par image quand « Vitesse de transition » raccourcit l'effet)."""
        sim = self.capt_sim; cible = EF.appels_faits(ef['n'], ef['duree'], ef['images'])
        while sim.images < cible and not sim.fini: sim.etape()
        return sim

    def _capt_tracer(self, sim, flou):
        """Les dessins de l'effet dans la cible courante : le fond lit la texture de flou `flou` (None : noire, rien a dessiner), la capture lit la copie de l'ecran du jeu."""
        prog = self.prog_effet; prog.use(); prog['lum'] = 1.0; prog['flou'] = 0.0
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glActiveTexture(gl.GL_TEXTURE0)
        for k, (nom, pos, uv, rgba) in enumerate(sim.dessins()):
            if nom == 'flou':
                if flou is None: continue
                tex = self.capt_rt[flou]; gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ZERO)               # Custom/CaptureBlur : texture x couleur remplace l'ecran
            else:
                tex = self.effet_tex; gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)    # Custom/Capture
            vl = self.capt_vl.get(k)
            if vl is None: vl = self.capt_vl[k] = prog.vertex_list(len(pos), gl.GL_TRIANGLES, position=('f', pos.ravel().tolist()), tex_coords=('f', uv.ravel().tolist()), colors=('f', rgba.ravel().tolist()))
            else: vl.position[:] = pos.ravel().tolist(); vl.colors[:] = rgba.ravel().tolist()
            gl.glBindTexture(tex.target, tex.id); vl.draw(gl.GL_TRIANGLES)
        prog.stop()

    def _capt_passe_flou(self, sim, i):
        """Capture.Caputer, passe de flou : l'etat de l'image precedente (fond flou + maillage) est redessine dans la texture de demi-resolution `i`."""
        w, h = self.get_framebuffer_size()
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.capt_fbo[i]); gl.glViewport(0, 0, *self.capt_taille)
        gl.glClearColor(0.0, 0.0, 0.0, 1.0); gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        self._capt_tracer(sim, sim.flou_lu)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0); gl.glViewport(0, 0, w, h)

    def _dessiner_effet_capture(self, sim):
        """Image de l'effet : fond noir, fond flou, maillage ; puis les plans de fondu et l'interface par-dessus (messages, fenetres du jeu)."""
        gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear()
        gl.glViewport(0, 0, *self.get_framebuffer_size())
        self._capt_tracer(sim, sim.flou_lu)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        self._dessiner_fondu(True)
        self._maj_message(); self._dessiner_message(); self._dessiner_menus(); self._dessiner_fondu(); self._dessiner_aide()
