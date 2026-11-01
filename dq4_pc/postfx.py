"""Rendu de la scene hors ecran puis passe finale : anticrenelage MSAA reglable a chaud, suréchantillonnage, nettete, luminosite.

La scene (decor, personnages, vignette, fondus de fond) est dessinee dans un tampon hors ecran (renderbuffers multi-echantillons) puis recopiee dans la fenetre ;
l'interface (messages, menus, boutons, menu Echap) est dessinee ensuite directement dans la fenetre : elle n'est ni lissee ni retouchee.
Aucun reglage actif (MSAA 0, echelle 1, nettete 0, luminosite normale) = pas de tampon hors ecran : le dessin direct d'avant.
Tout echec de creation (pilote sans multi-echantillonnage...) retombe sur le dessin direct et le dit dans le journal.
"""
import ctypes, os
import numpy as np
from pyglet import gl
from pyglet.graphics.shader import Shader, ShaderProgram

VERT = '''#version 330 core
in vec2 position; in vec2 tex_coords;
out vec2 v_uv;
void main() { gl_Position = vec4(position, 0.0, 1.0); v_uv = tex_coords; }'''
# Passe finale : lecture bilineaire de la scene (une reduction exacte x2 donne la moyenne de 4 pixels), nettete adaptative (CAS d'AMD FidelityFX, licence MIT : le gain est limite la ou le
# contraste local est deja fort, donc pas de halo), luminosite = courbe de gamma (noir et blanc inchanges).
FRAG = '''#version 330 core
in vec2 v_uv; out vec4 fragColor;
uniform sampler2D tex; uniform vec2 pas; uniform float nettete; uniform float gamma;
vec3 S(vec2 d) { return texture(tex, v_uv + d * pas).rgb; }
void main() {
    vec3 c = S(vec2(0.0));
    if (nettete > 0.001) {
        vec3 n = S(vec2(0.0, 1.0)), s = S(vec2(0.0, -1.0)), e = S(vec2(1.0, 0.0)), o = S(vec2(-1.0, 0.0));
        vec3 mn = min(c, min(min(n, s), min(e, o))), mx = max(c, max(max(n, s), max(e, o)));
        vec3 amp = sqrt(clamp(min(mn, 1.0 - mx) / max(mx, vec3(1e-4)), 0.0, 1.0));
        vec3 w = amp * (-1.0 / mix(8.0, 5.0, nettete));
        c = clamp((c + (n + s + e + o) * w) / (1.0 + 4.0 * w), 0.0, 1.0);
    }
    if (abs(gamma - 1.0) > 0.001) c = pow(c, vec3(1.0 / gamma));
    fragColor = vec4(c, 1.0);
}'''

SAMPLE_ALPHA_TO_COVERAGE = 0x809E
MAX_SAMPLES = 0x8D57


def _gen(fonction):
    i = gl.GLuint(0); fonction(1, ctypes.byref(i)); return i.value


class PostFX:
    def __init__(self, fen, log=print):
        self.f = fen; self.log = log
        self.ok = True                 # False apres un echec : dessin direct pour le reste de la session
        self.msaa = 0                  # anticrenelage reel (limite par la carte graphique)
        self.max_msaa = None
        self.fb = None                 # (largeur, hauteur) des tampons crees
        self.cle = None                # (taille, echantillons) pour lesquels ils ont ete crees
        self.fbo = self.fbo_res = self.rb_col = self.rb_prof = self.tex = 0
        self.prog = None; self.vl = None
        self.actif_cadre = False       # le cadre en cours est dessine hors ecran
        self.a2c = False               # alpha-to-coverage utilisable (tampon multi-echantillons)

    # ---- reglages (lus a chaque image : un changement du menu Echap s'applique tout de suite)
    def reglages(self):
        r = self.f.reg
        return int(r['msaa']), float(r['echelle_rendu']), float(r['nettete']), float(r['luminosite'])

    def demande(self):
        """(echantillons demandes, echelle, nettete, gamma) ; l'echelle n'est utile qu'en dessous de 1 pixel d'ecran par pixel de scene."""
        ms, ech, net, lum = self.reglages()
        return ms, max(1.0, min(2.0, ech)), max(0.0, min(1.0, net)), max(0.5, min(1.5, lum))

    def limite(self):
        if self.max_msaa is None:
            v = (gl.GLint * 1)(); gl.glGetIntegerv(MAX_SAMPLES, v); self.max_msaa = int(v[0])
        return self.max_msaa

    # ---- creation des tampons
    def _liberer(self):
        for nom, f in (('fbo', gl.glDeleteFramebuffers), ('fbo_res', gl.glDeleteFramebuffers), ('rb_col', gl.glDeleteRenderbuffers), ('rb_prof', gl.glDeleteRenderbuffers)):
            v = getattr(self, nom)
            if v: f(1, ctypes.byref(gl.GLuint(v))); setattr(self, nom, 0)
        if self.tex: gl.glDeleteTextures(1, ctypes.byref(gl.GLuint(self.tex))); self.tex = 0
        self.cle = None

    def _creer(self, w, h, ms):
        self._liberer()
        self.fbo = _gen(gl.glGenFramebuffers); self.rb_prof = _gen(gl.glGenRenderbuffers)
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self.rb_prof)
        if ms: gl.glRenderbufferStorageMultisample(gl.GL_RENDERBUFFER, ms, gl.GL_DEPTH_COMPONENT24, w, h)
        else: gl.glRenderbufferStorage(gl.GL_RENDERBUFFER, gl.GL_DEPTH_COMPONENT24, w, h)
        tex = gl.GLuint(0); gl.glGenTextures(1, ctypes.byref(tex)); self.tex = tex.value
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.tex)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8, w, h, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, None)
        for p, v in ((gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR), (gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR), (gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE), (gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)):
            gl.glTexParameteri(gl.GL_TEXTURE_2D, p, v)
        if ms:      # scene multi-echantillons, puis recopie (resolution) dans la texture
            self.rb_col = _gen(gl.glGenRenderbuffers)
            gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self.rb_col)
            gl.glRenderbufferStorageMultisample(gl.GL_RENDERBUFFER, ms, gl.GL_RGBA8, w, h)
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)
            gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_RENDERBUFFER, self.rb_col)
            gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, gl.GL_DEPTH_ATTACHMENT, gl.GL_RENDERBUFFER, self.rb_prof)
            etat = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
            self.fbo_res = _gen(gl.glGenFramebuffers)
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo_res)
            gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, self.tex, 0)
            etat2 = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
            if etat != gl.GL_FRAMEBUFFER_COMPLETE or etat2 != gl.GL_FRAMEBUFFER_COMPLETE: raise RuntimeError('tampon incomplet (%#x, %#x)' % (etat, etat2))
        else:       # sans multi-echantillonnage : dessin directement dans la texture
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)
            gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, self.tex, 0)
            gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, gl.GL_DEPTH_ATTACHMENT, gl.GL_RENDERBUFFER, self.rb_prof)
            etat = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
            if etat != gl.GL_FRAMEBUFFER_COMPLETE: raise RuntimeError('tampon incomplet (%#x)' % etat)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        self.fb = (w, h); self.cle = (w, h, ms)

    def _passe(self):
        if self.prog is None:
            self.prog = ShaderProgram(Shader(VERT, 'vertex'), Shader(FRAG, 'fragment'))
            q = np.array([-1, -1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1], np.float32); uv = np.array([0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1], np.float32)
            self.vl = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv))

    # ---- cadre
    def debut(self, fond):
        """Commence le dessin de la scene ; retourne (largeur, hauteur) de la zone de dessin a utiliser pour glViewport. Efface avec la couleur de fond."""
        W, H = self.f.get_framebuffer_size(); self.actif_cadre = False; self.a2c = False
        if not self.ok: return W, H
        ms, ech, net, lum = self.demande()
        if ms == 0 and ech <= 1.0 and net <= 0.001 and abs(lum - 1.0) <= 0.001: return W, H       # rien a faire : dessin direct
        try:
            reel = min(ms, self.limite()) if ms else 0
            if reel == 1: reel = 0
            w, h = int(round(W * ech)), int(round(H * ech))
            if self.cle != (w, h, reel):
                self._creer(w, h, reel); self.msaa = reel
                self.log('Rendu hors écran : %d x %d (x%.2g), anticrénelage %s%s' % (w, h, ech, 'x%d' % reel if reel else 'non', ' (demandé x%d)' % ms if reel != ms else ''))
            self._passe()
        except Exception as ex:
            self.ok = False; self.msaa = 0; gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
            self.log('Rendu hors écran impossible (%r) : dessin direct, sans anticrénelage' % (ex,)); return W, H
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)
        gl.glViewport(0, 0, *self.fb)
        gl.glClearColor(float(fond[0]), float(fond[1]), float(fond[2]), 1.0); gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        self.actif_cadre = True; self.a2c = self.msaa > 0 and not os.environ.get('DQ_SANS_A2C')       # (test) DQ_SANS_A2C=1 : decoupes en alpha-test dur, comme avant
        return self.fb

    def fin(self):
        """Termine la scene : recopie dans la fenetre (avec la passe finale si un effet est reglé). Remet l'etat attendu par le dessin de l'interface."""
        if not self.actif_cadre: return
        self.actif_cadre = False; self.a2c = False
        W, H = self.f.get_framebuffer_size(); ms, ech, net, lum = self.demande(); w, h = self.fb
        gl.glDisable(SAMPLE_ALPHA_TO_COVERAGE); gl.glDisable(gl.GL_DEPTH_TEST)
        direct = abs(ech - 1.0) < 1e-3 and net <= 0.001 and abs(lum - 1.0) <= 0.001            # pas de passe finale : simple recopie (resolution du multi-echantillonnage comprise)
        if direct:
            gl.glBindFramebuffer(gl.GL_READ_FRAMEBUFFER, self.fbo); gl.glBindFramebuffer(gl.GL_DRAW_FRAMEBUFFER, 0)
            gl.glBlitFramebuffer(0, 0, w, h, 0, 0, W, H, gl.GL_COLOR_BUFFER_BIT, gl.GL_NEAREST)
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        else:
            if self.msaa:
                gl.glBindFramebuffer(gl.GL_READ_FRAMEBUFFER, self.fbo); gl.glBindFramebuffer(gl.GL_DRAW_FRAMEBUFFER, self.fbo_res)
                gl.glBlitFramebuffer(0, 0, w, h, 0, 0, w, h, gl.GL_COLOR_BUFFER_BIT, gl.GL_NEAREST)
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
            gl.glViewport(0, 0, W, H); gl.glDisable(gl.GL_BLEND)
            self.prog.use(); self.prog['pas'] = (1.0 / W, 1.0 / H); self.prog['nettete'] = net; self.prog['gamma'] = lum
            gl.glActiveTexture(gl.GL_TEXTURE0); gl.glBindTexture(gl.GL_TEXTURE_2D, self.tex)
            self.vl.draw(gl.GL_TRIANGLES)
            self.prog.stop()
        gl.glViewport(0, 0, W, H); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
