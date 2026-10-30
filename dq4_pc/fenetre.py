"""Fenetre PC 16/9 : fait tourner le moteur du jeu et dessine ce qu'il demande (decor, sprites, camera)."""
import os, sys, math, time, argparse, glob, collections
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pyglet
from pyglet import gl
from pyglet.graphics.shader import Shader, ShaderProgram


import moteur as MO
import donnees as DO
import hd as HD

VERT = '''#version 330 core
in vec3 position; in vec2 tex_coords; in vec4 colors;
uniform mat4 mvp;
out vec2 v_uv; out vec4 v_col;
void main() { gl_Position = mvp * vec4(position, 1.0); v_uv = tex_coords; v_col = colors; }'''
FRAG = '''#version 330 core
in vec2 v_uv; in vec4 v_col; out vec4 fragColor;
uniform sampler2D tex; uniform float cutoff; uniform vec2 tsize; uniform float net; uniform float amul;
void main() {
    vec2 uv = v_uv;
    if (net > 0.5) {   // pixel art : on garde des pixels nets, seule la frontiere entre deux pixels est adoucie
        vec2 p = uv * tsize; vec2 pc = floor(p) + 0.5; vec2 w = max(fwidth(p), vec2(1e-4));
        uv = (pc + clamp((p - pc) / w, -0.5, 0.5)) / tsize;
    }
    vec4 c = texture(tex, uv) * clamp(v_col, 0.0, 1.0); if (c.a < cutoff) discard; c.a *= amul; fragColor = c; }'''

FOV_VERTICAL = 20.0           # champ de vision vertical des villes (camera Unity du jeu)
SPRITE_L, SPRITE_H, SPRITE_ECHELLE = 24, 32, 0.045
HD_GOUTTIERE, HD_NIVEAUX = 4, 2      # sprites HD (agrandissement x8, voir hd.py) : marge de 4 px, 2 niveaux de mipmaps
POLICES = ('Segoe UI', 'Arial', 'DejaVu Sans', 'Liberation Sans')
BTN_PAROLE, BTN_MENU = 0x100, 0x800     # arg2 de GameUpdate : parler / examiner (exactement 0x100), ouvrir le menu de commandes


def matrice(cam, cible, fov, aspect, n=1.0, f=200.0):
    pos = np.array(cam, float); fw = np.array(cible, float) - pos; fw /= np.linalg.norm(fw)
    droite = np.cross([0, 1, 0], fw); droite /= np.linalg.norm(droite); haut = np.cross(fw, droite)
    th = math.tan(math.radians(fov) / 2)
    M = np.zeros((4, 4))
    M[0, :3] = droite / (th * aspect); M[0, 3] = -pos @ droite / (th * aspect)
    M[1, :3] = haut / th; M[1, 3] = -pos @ haut / th
    k = (f + n) / (f - n)
    M[2, :3] = fw * k; M[2, 3] = -pos @ fw * k - 2 * f * n / (f - n)
    M[3, :3] = fw; M[3, 3] = -pos @ fw
    return M, droite


class Jeu(pyglet.window.Window):
    def __init__(self, args):
        self.msaa = 0
        for ms in ((args.msaa, 0) if args.msaa else (0,)):       # anticrenelage materiel si la carte le permet
            try:
                cfg = gl.Config(depth_size=24, double_buffer=True, major_version=3, minor_version=3, sample_buffers=1 if ms else 0, samples=ms)
                super().__init__(args.largeur, args.hauteur, caption='Dragon Quest IV - portage PC (essai)', resizable=True, config=cfg, vsync=True)
                self.msaa = ms; break
            except pyglet.window.NoSuchConfigException:
                print('MSAA x%d indisponible' % ms, flush=True)
        print('MSAA : %s' % ('x%d' % self.msaa if self.msaa else 'non'), flush=True)
        self.args = args
        self._attente('Chargement du moteur...')
        self.mode = max(0, min(int(args.hd), len(HD.MODES) - 1)); self.lissage = True; self.aniso = self._anisotropie()
        self.pool = ThreadPoolExecutor(max_workers=1); self.hd_jobs = {}; self.sprite_vl = {}; self._dom_lie = None
        self.stats = True; self.ecarts = collections.deque(maxlen=120); self.t_prec = None; self.dt_dessin = 0.0
        self.prog = ShaderProgram(Shader(VERT, 'vertex'), Shader(FRAG, 'fragment'))
        self.donnees = DO.Donnees(None, args.cache, log=lambda *a: print(*a, flush=True))
        self.moteur = MO.Moteur(args.apk, args.saves_lecture, args.saves_ecriture)
        self._attente('Chargement de la sauvegarde...')
        self.donnees.apk = self.moteur.apk_donnees
        self.touches = pyglet.window.key.KeyStateHandler(); self.push_handlers(self.touches)
        self.carte_nom = None; self.carte_vl = []; self.tex_gl = {}; self.sprite_tex = {}
        self.carte_pos = {}; self.carte_cur = {}; self.plages = {}; self.noms = {}; self.portes = {}; self.bornes_x = None
        self.etiquette = pyglet.text.Label('', x=10, y=self.height - 10, anchor_y='top', font_size=11, color=(255, 255, 255, 255))
        self.etiq_stats = pyglet.text.Label('', x=10, y=self.height - 50, anchor_y='top', font_size=10, color=(255, 230, 150, 255))
        self.etiq_hd = pyglet.text.Label('', x=10, y=self.height - 30, anchor_y='top', font_size=10, color=(200, 220, 255, 255))
        if args.slot:
            ok = self.moteur.charger_sauvegarde(args.slot)
            print('sauvegarde %d chargee : %s' % (args.slot, 'oui' if ok else 'NON (fichier data%d.dat introuvable ou invalide dans %s)' % (args.slot, args.saves_lecture)), flush=True)
            if ok:      # on laisse le moteur lancer la carte sauvegardee avant le premier affichage
                for _ in range(6): self.moteur.step(0, 0)
                self._attente('Chargement de la carte...')
                e = self.moteur.etat
                if e.carte: self._charger_carte(e.carte)      # les chargements lourds se font ici, pas pendant le jeu
                for sp in list(e.sprites.values()): self._feuille(sp['id'], self.mode)
        self.n = 0; self.dt_moteur = 0.0; self.pad_prec = 0; self.rep = {}
        self.msg_cle = None; self.msg_img = None; self.msg_spr = None; self.msg_h = 0
        self.etiq_menu = {}; self.focus_vu = None; self.menu_relacher = None
        pyglet.clock.schedule_interval(self.tick, 1 / 30.0)

    def _attente(self, texte):
        """Ecran noir avec un message : la fenetre reste vivante pendant les chargements."""
        try:
            self.switch_to(); gl.glClearColor(0, 0, 0, 1); self.clear()
            pyglet.text.Label(texte, x=self.width // 2, y=self.height // 2, anchor_x='center', anchor_y='center', font_size=16, color=(255, 255, 255, 255)).draw()
            self.flip(); self.dispatch_events()
        except Exception: pass

    # ---- textures
    def _anisotropie(self):
        """Niveau d'anisotropie maximal utilisable (1.0 si l'extension manque), plafonne a 8."""
        try:
            v = (gl.GLfloat * 1)(); gl.glGetFloatv(0x84FF, v); return max(1.0, min(8.0, float(v[0])))
        except Exception:
            return 1.0

    def _tex(self, arr, repeat, mip=0):
        """Texture RGBA ; mip > 0 : mipmaps (limites a `mip` niveaux, 99 = tous) + filtrage anisotrope."""
        h, w = arr.shape[:2]
        img = pyglet.image.ImageData(w, h, 'RGBA', np.ascontiguousarray(arr[::-1]).tobytes(), pitch=w * 4)
        t = img.get_texture()
        gl.glBindTexture(t.target, t.id)
        m = gl.GL_REPEAT if repeat else gl.GL_CLAMP_TO_EDGE
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, m); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, m)
        if mip:
            gl.glGenerateMipmap(t.target)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAX_LEVEL, min(mip, 20))
            self._filtrer(t, True)
        return t

    def _filtrer(self, t, lisse):
        """Filtrage d'une texture mipmappee : lisse = mipmaps trilineaires + anisotrope, sinon bilineaire simple."""
        gl.glBindTexture(t.target, t.id)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR if lisse else gl.GL_LINEAR)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        if self.aniso > 1.0: gl.glTexParameterf(t.target, 0x84FE, self.aniso if lisse else 1.0)

    def _feuille_orig(self, ident):
        """Feuille `h<ident>` d'origine (pixels nets) ; False si absente."""
        cle = (ident, 0)
        if cle in self.sprite_tex: return self.sprite_tex[cle]
        arr = self.donnees.feuille(ident); r = False
        if arr is not None:
            nl = 8 if arr[4 * SPRITE_H:5 * SPRITE_H, :72, 3].any() else 4
            r = dict(t=self._tex(arr, False), tw=arr.shape[1], th=arr.shape[0], nl=nl, hd=False, arr=arr)
        self.sprite_tex[cle] = r
        return r

    def _calcul_hd(self, arr, nl, ident, cid, algo):
        """(tache de fond) atlas HD d'une feuille, lu dans le cache disque s'il existe."""
        f = os.path.join(self.args.cache, 'hd_%s_v%d_h%d.npy' % (cid, HD.VERSION, ident))
        try:
            if os.path.exists(f): return np.load(f), SPRITE_L * HD.FACTEUR, SPRITE_H * HD.FACTEUR
        except Exception: pass
        atlas, cl, ch = HD.agrandir_feuille(arr, SPRITE_L, SPRITE_H, 3, nl, algo, HD_GOUTTIERE)
        try: np.save(f, atlas)
        except Exception: pass
        return atlas, cl, ch

    def _feuille(self, ident, mode):
        """Feuille de sprites pour le mode choisi. Les versions HD sont calculees en tache de fond : en attendant, l'original sert."""
        orig = self._feuille_orig(ident)
        if not orig or mode == 0: return orig
        cle = (ident, mode)
        if cle in self.sprite_tex: return self.sprite_tex[cle]
        fut = self.hd_jobs.get(cle)
        if fut is None:
            _nom, cid, algo = HD.MODES[mode]
            self.hd_jobs[cle] = self.pool.submit(self._calcul_hd, orig['arr'], orig['nl'], ident, cid, algo)
            return orig
        if not fut.done(): return orig
        del self.hd_jobs[cle]
        try: atlas, cl, ch = fut.result()
        except Exception as ex:
            print('lissage HD impossible (%s, h%d) : %s' % (HD.MODES[mode][0], ident, ex), flush=True); self.sprite_tex[cle] = orig; return orig
        r = self.sprite_tex[cle] = dict(t=self._tex(atlas, False, HD_NIVEAUX), tw=atlas.shape[1], th=atlas.shape[0], nl=orig['nl'], cl=cl, ch=ch, hd=True)
        return r

    def _tracer(self, tex, vl):
        """Trace une vertex_list en ne liant le VAO et les tampons qu'une fois par image (beaucoup plus rapide que vl.draw)."""
        gl.glBindTexture(tex.target, tex.id)
        try:
            dom = vl.domain
            if dom is not self._dom_lie:
                dom.vao.bind()
                for buf, _ in dom.buffer_attributes: buf.commit()
                self._dom_lie = dom
            gl.glDrawArrays(gl.GL_TRIANGLES, vl.start, vl.count)
        except AttributeError:
            vl.draw(gl.GL_TRIANGLES)

    def on_key_press(self, symbol, modifiers):
        K = pyglet.window.key
        if symbol == K.F2: self.mode = (self.mode + 1) % len(HD.MODES)
        elif symbol == K.F4: self.stats = not self.stats
        elif symbol == K.F3:
            self.lissage = not self.lissage
            for t in self.tex_gl.values(): self._filtrer(t, self.lissage)
        else: return super().on_key_press(symbol, modifiers)

    def _charger_carte(self, nom):
        for vl in self.carte_vl: vl[1].delete()
        self.carte_vl = []; self.carte_pos = {}; self.carte_cur = {}; self.plages = {}; self.noms = {}; self.portes = {}
        try:
            c = self.donnees.carte(nom)
        except Exception as ex:
            print('carte non chargee :', ex, flush=True); self.carte_nom = nom; return
        for key, (pos, uv, col) in c['groupes'].items():
            if key not in c['textures']: continue
            if (nom, key) not in self.tex_gl:
                self.tex_gl[(nom, key)] = t = self._tex(c['textures'][key], True, 99); self._filtrer(t, self.lissage)
            vl = self.prog.vertex_list(len(pos), gl.GL_TRIANGLES, position=('f', pos.ravel()), tex_coords=('f', uv.ravel()), colors=('f', col.ravel()))
            self.carte_vl.append((self.tex_gl[(nom, key)], vl, key)); self.carte_pos[key] = pos.copy()
        self.plages = c.get('plages', {}); self.noms = c.get('noms', {})
        allp = np.concatenate([g[0] for g in c['groupes'].values()]) if c['groupes'] else np.zeros((1, 3), np.float32)
        self.bornes_x = (float(np.percentile(allp[:, 0], 0.5)), float(np.percentile(allp[:, 0], 99.5)))
        self.carte_nom = nom
        print('carte %s : %d groupes' % (nom, len(self.carte_vl)), flush=True)

    def _maj_message(self):
        """Texte visible du message (canevas du moteur) -> image RGBA blanche dont l'opacite est celle du texte."""
        a = self.moteur.lire_message()
        if a is None: self.msg_img = None; return
        h = a.shape[0]
        cle = hash(a.tobytes())
        if cle == self.msg_cle: return
        self.msg_cle = cle; self.msg_h = h
        rgba = np.empty((h, a.shape[1], 4), np.uint8); rgba[..., :3] = 255; rgba[..., 3] = a
        self.msg_img = pyglet.image.ImageData(a.shape[1], h, 'RGBA', np.ascontiguousarray(rgba[::-1]).tobytes(), pitch=a.shape[1] * 4)
        t = self.msg_img.get_texture()
        gl.glBindTexture(t.target, t.id)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)

    def _dessiner_message(self):
        if self.msg_img is None or not self.moteur.msg_visible: return
        ech = self.height / 720.0 * 1.3                       # taille du texte : 1 pixel du canevas = 1,3 pixel a 720p
        tl, tn = MO.CANEVAS_L * ech * 0.78, self.msg_h * ech
        marge = 18 * ech
        bw, bh = tl + 2 * marge, tn + 2 * marge
        bx, by = (self.width - bw) / 2, 22 * ech
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        cadre = pyglet.shapes.BorderedRectangle(bx, by, bw, bh, border=max(2, int(3 * ech)), color=(8, 12, 70), border_color=(245, 245, 245))
        cadre.opacity = 235
        cadre.draw()
        spr = pyglet.sprite.Sprite(self.msg_img, x=bx + marge, y=by + bh - marge - self.msg_h * ech)
        spr.scale = ech
        spr.draw()

    # ---- menus
    def _lignes_menu(self, f):
        """Cases d'une fenetre -> lignes (numero de ligne du moteur, texte, etiquette, valeur, est_un_titre)."""
        rows = {}
        for (r, c), t in f['cases'].items(): rows.setdefault(r, {})[c] = t
        out = []
        for r in sorted(rows):
            cols = rows[r]
            pre, lab, val = cols.get(5, ''), cols.get(2, ''), cols.get(3, '')
            princ = ' '.join(t for c, t in sorted(cols.items()) if c not in (2, 3, 5) and t)
            if not (princ or val or lab): continue
            out.append((r, (pre + ' ' + princ).strip(), lab, val, princ.rstrip().endswith('?')))
        return [l for l in out if l[4]] + [l for l in out if not l[4]]

    def _saisie_menu(self, port, decl):
        mo = self.moteur; f = mo.ui.f[port]
        sel = [l[0] for l in self._lignes_menu(f) if not l[4]]
        cle = (port, f['ordre'])
        if sel and (cle != self.focus_vu or f['cur'] not in sel):
            self.focus_vu = cle
            if f['cur'] not in sel: f['cur'] = sel[0]; mo.envoyer_menu(port, 1, sel[0], 0)
        if sel and (decl & (MO.HAUT | MO.BAS)):
            i = sel.index(f['cur']) if f['cur'] in sel else 0
            i = (i + (1 if decl & MO.BAS else -1)) % len(sel)
            f['cur'] = sel[i]; mo.envoyer_menu(port, 1, sel[i], 0)
        elif decl & MO.A:
            mo.envoyer_menu(port, 1, -1, 0x10); self.menu_relacher = port
        elif decl & MO.B:
            mo.envoyer_menu(port, 1, -1, 0x20); self.menu_relacher = port

    def _etiq(self, texte, taille, couleur=(255, 255, 255, 255)):
        k = (texte, round(taille, 1), couleur)
        l = self.etiq_menu.get(k)
        if l is None:
            if len(self.etiq_menu) > 400: self.etiq_menu.clear()
            l = self.etiq_menu[k] = pyglet.text.Label(texte, font_name=POLICES, font_size=taille, color=couleur, anchor_x='left', anchor_y='baseline')
        return l

    def _dessiner_menus(self):
        mo = self.moteur
        fens = mo.ui.visibles()
        if not fens: return
        ech = self.height / 720.0; W, H = self.width, self.height
        taille = 17 * ech; rh = 36 * ech; pad = 16 * ech; gap = 18 * ech
        actif = mo.menu_actif()
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        x_main = 40 * ech
        for port, f in fens:
            lignes = self._lignes_menu(f)
            if not lignes: continue
            sel = [l[0] for l in lignes if not l[4]]
            # largeur : texte le plus large + zone etiquette/valeur
            largeur_g = max(self._etiq(l[1], taille).content_width for l in lignes)
            largeur_d = max([max(self._etiq(l[2], taille * 0.8).content_width if l[2] else 0, self._etiq(l[3], taille).content_width if l[3] else 0) for l in lignes] + [0])
            deux = [l for l in lignes if l[2] and l[3]]
            hauts = [rh * (1.5 if (l[2] and l[3]) else 1) for l in lignes]
            w = pad * 2 + 26 * ech + largeur_g + (largeur_d + 24 * ech if largeur_d else 0); h = pad * 2 + sum(hauts)
            if port == 3: x, ytop = W - w - 24 * ech, H - 24 * ech
            elif port == 2: x, ytop = W - w - 40 * ech, H * 0.62
            else: x, ytop = x_main, H - 24 * ech; x_main += w + gap
            y = ytop - h
            fond = pyglet.shapes.BorderedRectangle(x, y, w, h, border=max(2, int(3 * ech)), color=(8, 12, 70), border_color=(255, 255, 255) if port == actif else (150, 150, 170))
            fond.opacity = 235; fond.draw()
            cy = ytop - pad
            for (idx, gauche, lab, val, titre), hl in zip(lignes, hauts):
                base = cy - rh * 0.72
                if lab and val:
                    base = cy - rh * 0.72
                    e = self._etiq(lab, taille * 0.8); e.x = x + w - pad - e.content_width; e.y = base; e.draw()
                    e = self._etiq(val, taille); e.x = x + w - pad - e.content_width; e.y = base - rh * 0.5; e.draw()
                    gy = cy - rh * 0.95
                elif val:
                    e = self._etiq(val, taille); e.x = x + w - pad - e.content_width; e.y = base; e.draw(); gy = base
                else: gy = base
                e = self._etiq(gauche, taille, (255, 235, 130, 255) if titre else (255, 255, 255, 255)); e.x = x + pad + (0 if titre else 26 * ech); e.y = gy if not (lab and val) else cy - rh * 0.72 - rh * 0.25; e.draw()
                if not titre and port == actif and idx == f['cur']:
                    ty = (cy - hl / 2) if not (lab and val) else cy - rh * 0.6
                    pyglet.shapes.Triangle(x + pad, ty + 9 * ech, x + pad, ty - 9 * ech, x + pad + 15 * ech, ty, color=(255, 235, 130)).draw()
                cy -= hl

    def _animer_portes(self):
        """Les battants de porte pivotent de 90 degres vers l'exterieur (-z) autour de leur charniere (bord le plus eloigne du centre)."""
        if not self.portes: return
        touches = set()
        for idx, debut in self.portes.items():
            t = min(1.0, (self.n - debut + 1) / float(MO.DUREE_ANIM)); t = t * t * (3 - 2 * t)
            for key, start, cnt in self.plages.get(idx, []):
                orig = self.carte_pos.get(key)
                if orig is None: continue
                seg = orig[start:start + cnt]
                cx = float((seg[:, 0].min() + seg[:, 0].max()) / 2)
                hx = float(seg[:, 0].max() if cx > 0 else seg[:, 0].min()); hz = float(seg[:, 2].mean())
                phi = math.radians(90.0 * t) * (-1.0 if cx > 0 else 1.0)
                c, sn = math.cos(phi), math.sin(phi)
                dx, dz = seg[:, 0] - hx, seg[:, 2] - hz
                nv = seg.copy(); nv[:, 0] = hx + dx * c + dz * sn; nv[:, 2] = hz - dx * sn + dz * c
                self.carte_cur.setdefault(key, orig.copy())[start:start + cnt] = nv
                touches.add(key)
        for tex, vl, key in self.carte_vl:
            if key in touches: vl.position[:] = self.carte_cur[key].ravel()

    # ---- boucle
    def pad(self):
        k, K = self.touches, pyglet.window.key
        p = 0
        if k[K.UP] or k[K.Z] or k[K.W]: p |= MO.HAUT
        if k[K.DOWN] or k[K.S]: p |= MO.BAS
        if k[K.LEFT] or k[K.Q] or k[K.A]: p |= MO.GAUCHE
        if k[K.RIGHT] or k[K.D]: p |= MO.DROITE
        if k[K.ENTER] or k[K.SPACE] or k[K.E]: p |= MO.A
        if k[K.BACKSPACE] or k[K.X]: p |= MO.B
        return p

    def tick(self, dt):
        p = self.args.script.get(self.n, self.pad()) if self.args.script is not None else self.pad()
        if self.args.slot and self.args.auto_message and self.n < 112:
            # (test) ferme le message d'accueil automatiquement
            p = MO.A if (70 <= self.n <= 72 or 88 <= self.n <= 90) else 0
        decl = p & ~self.pad_prec                      # boutons qui viennent d'etre presses
        for bit in (MO.HAUT, MO.BAS, MO.GAUCHE, MO.DROITE):      # repetition des directions maintenues (curseurs de menu)
            if p & bit:
                self.rep[bit] = self.rep.get(bit, 0) + 1
                if self.rep[bit] > 12 and (self.rep[bit] - 12) % 4 == 0: decl |= bit
            else: self.rep[bit] = 0
        self.pad_prec = p
        mo = self.moteur
        if self.menu_relacher is not None:                 # fin de l'appui OK / Annuler envoye au menu
            mo.envoyer_menu(self.menu_relacher, 1, -1, 0); self.menu_relacher = None
        port = mo.menu_actif() if not mo.msg_visible else None
        if port is not None:                               # un menu attend les touches : elles lui sont envoyees, pas au terrain
            self._saisie_menu(port, decl)
            p = decl = 0
        elif not mo.msg_visible:
            # sur le terrain : A = parler / examiner, Annuler = ouvrir le menu (le moteur veut ces boutons seuls)
            if decl & MO.A: decl = BTN_PAROLE
            elif decl & MO.B: decl = BTN_MENU
            p &= ~(MO.A | MO.B)
        if os.environ.get('DQ_DEBUG') and (p or decl): print('n=%d p=%#x decl=%#x msg=%s' % (self.n, p, decl, mo.msg_visible), flush=True)
        t0 = time.time(); mo.step(p, decl); self.dt_moteur = time.time() - t0
        e = self.moteur.etat
        for idx, anim in e.evt_anim:
            if 'door' in self.noms.get(idx, '').lower() and idx not in self.portes: self.portes[idx] = self.n
        e.evt_anim.clear()
        self._animer_portes()
        self.n += 1
        if self.args.shot and self.n >= self.args.images:
            self.dispatch_event('on_draw'); self.flip()
            pyglet.image.get_buffer_manager().get_color_buffer().save(self.args.shot)
            print('capture :', self.args.shot, [(q, list(f['cases'].items())[:3]) for q, f in self.moteur.ui.visibles()], self.moteur.menu_actif(), self.moteur.msg_visible, flush=True); pyglet.app.exit()

    def on_draw(self):
        t_debut = time.perf_counter()
        if self.t_prec is not None: self.ecarts.append(t_debut - self.t_prec)
        self.t_prec = t_debut
        e = self.moteur.etat
        gl.glClearColor(e.fond[0], e.fond[1], e.fond[2], 1.0)
        self.clear()
        if e.carte and e.carte != self.carte_nom: self._charger_carte(e.carte)
        if e.cam_pos is None or e.cam_cible is None: return
        gl.glEnable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glViewport(0, 0, *self.get_framebuffer_size())
        aspect = self.width / max(1, self.height)
        cam, cib = np.array(e.cam_pos, float), np.array(e.cam_cible, float)
        if self.bornes_x is not None:
            # cadrage 16/9 : le moteur centre la camera pour un ecran portrait ; en large on garde le bord de la carte hors champ
            fv = cib - cam; fv[1] = 0; fv /= np.linalg.norm(fv) or 1
            if abs(fv[2]) > 0.95:
                W = np.linalg.norm(cib - cam) * math.tan(math.radians(FOV_VERTICAL / 2)) * aspect * 0.85
                lo, hi = self.bornes_x[0] + W, self.bornes_x[1] - W
                cx = (self.bornes_x[0] + self.bornes_x[1]) / 2 if lo >= hi else min(max(cib[0], lo), hi)
                d = cx - cib[0]; cam[0] += d; cib[0] += d
        M, droite = matrice(cam, cib, FOV_VERTICAL, aspect)
        # sprites : panneaux verticaux tournes vers la camera (listes de sommets persistantes, une par emplacement)
        fh = np.array([e.cam_cible[0] - e.cam_pos[0], 0, e.cam_cible[2] - e.cam_pos[2]]); fh /= np.linalg.norm(fh) or 1
        dh = np.cross([0, 1, 0], fh); dh /= np.linalg.norm(dh) or 1
        w, h = SPRITE_L * SPRITE_ECHELLE, SPRITE_H * SPRITE_ECHELLE; up = np.array([0, h, 0])
        a_dessiner = []
        for slot, s in sorted(e.sprites.items()):
            if s['pos'] is None or s['col'][3] < 0.02: continue
            f = self._feuille(s['id'], self.mode)
            if not f: continue
            tw, th, nl = f['tw'], f['th'], f['nl']
            col, row = s['pose'] % 3, s['dir'] % nl
            if f['hd']:     # case (col, row) de l'atlas HD, marges exclues
                pl, ph, g = f['cl'] + 2 * HD_GOUTTIERE, f['ch'] + 2 * HD_GOUTTIERE, HD_GOUTTIERE
                u0, u1 = (col * pl + g) / tw, (col * pl + g + f['cl']) / tw
                v1, v0 = 1 - (row * ph + g) / th, 1 - (row * ph + g + f['ch']) / th
            else:
                u0, u1 = col * SPRITE_L / tw, (col + 1) * SPRITE_L / tw; v1, v0 = 1 - row * SPRITE_H / th, 1 - (row + 1) * SPRITE_H / th
            p = np.array(s['pos'], float)
            a, b = p - dh * w / 2, p + dh * w / 2
            q = np.array([a, b, b + up, a, b + up, a + up], np.float32).ravel().tolist()
            uv = [u0, v0, u1, v0, u1, v1, u0, v0, u1, v1, u0, v1]
            cl = list(map(float, s['col'])) * 6
            vl = self.sprite_vl.get(slot)
            if vl is None: vl = self.sprite_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            a_dessiner.append((slot, f, vl))
        self._dom_lie = None
        self.prog.use()
        self.prog['mvp'] = tuple(float(x) for x in M.T.ravel()); self.prog['cutoff'] = 0.5; self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0); self.prog['amul'] = 1.0
        gl.glActiveTexture(gl.GL_TEXTURE0)
        for tex, vl, _cle in self.carte_vl: self._tracer(tex, vl)
        self.prog['cutoff'] = 0.05
        for slot, f, vl in a_dessiner:
            self.prog['net'] = 0.0 if f['hd'] else 1.0; self.prog['tsize'] = (float(f['tw']), float(f['th']))
            self._tracer(f['t'], vl)
            if slot < 8:       # equipe : silhouette translucide quand un decor la cache
                gl.glDepthFunc(gl.GL_GREATER); gl.glDepthMask(gl.GL_FALSE); self.prog['amul'] = 0.4
                self._tracer(f['t'], vl)
                gl.glDepthFunc(gl.GL_LESS); gl.glDepthMask(gl.GL_TRUE); self.prog['amul'] = 1.0
        self.prog.stop()
        gl.glDisable(gl.GL_DEPTH_TEST)
        self.etiquette.text = 'Carte %s | fleches/ZQSD : marcher | Entree : valider/parler | Retour arriere ou X : menu/annuler | Echap : quitter' % e.carte
        self.etiquette.y = self.height - 10
        self.etiq_hd.text = 'F2 : sprites = %s | F3 : lissage du decor %s | anticrenelage %s | F4 : stats' % (HD.MODES[self.mode][0], 'oui' if self.lissage else 'non', 'x%d' % self.msaa if self.msaa else 'non')
        self.etiq_hd.y = self.height - 30
        self._maj_message(); self._dessiner_message(); self._dessiner_menus()
        self.etiquette.draw(); self.etiq_hd.draw()
        self.dt_dessin += (time.perf_counter() - t_debut - self.dt_dessin) * 0.1
        if self.stats and self.ecarts:
            if self.n % 10 == 0: self.etiq_stats.text = '%.0f images/s | pire image %.0f ms | moteur %.1f ms | dessin Python %.1f ms' % (len(self.ecarts) / max(1e-6, sum(self.ecarts)), max(self.ecarts) * 1000, self.dt_moteur * 1000, self.dt_dessin * 1000)
            self.etiq_stats.y = self.height - 50; self.etiq_stats.draw()


def trouver_defauts():
    ici = os.path.dirname(os.path.abspath(__file__))
    jeux = os.path.normpath(os.path.join(ici, '..', '..', 'jeux', 'DQ4'))
    return ici, jeux


def main():
    ici, jeux = trouver_defauts()
    ap = argparse.ArgumentParser()
    ap.add_argument('--apk', default=os.path.join(jeux, 'patched_apks'), help='dossier des 3 APK (version francaise)')
    ap.add_argument('--saves-lecture', default=None, help='dossier contenant data1.dat... (par defaut : la plus recente sauvegarde de jeux/DQ4/saves)')
    ap.add_argument('--saves-ecriture', default=os.path.join(ici, 'sauvegardes'))
    ap.add_argument('--cache', default=os.path.join(ici, 'cache'))
    ap.add_argument('--slot', type=int, default=1, help='numero de sauvegarde a charger (1-5), 0 = aucune')
    ap.add_argument('--largeur', type=int, default=1280); ap.add_argument('--hauteur', type=int, default=720)
    ap.add_argument('--auto-message', type=int, default=0, help='ferme automatiquement le message affiche apres le chargement')
    ap.add_argument('--hd', type=int, default=1, help='lissage des sprites : 0 originaux, 1 EPX, 2 regions lissees, 3 bicubique ; touche F2 pour changer en jeu')
    ap.add_argument('--msaa', type=int, default=4, help='anticrenelage materiel (0 = aucun, 4 = x4)')
    ap.add_argument('--shot', default=None, help='(test) enregistre une capture puis quitte')
    ap.add_argument('--images', type=int, default=60)
    ap.add_argument('--script', default=None, help='(test) ex. "20:2,30:0" : image:masque de touches')
    a = ap.parse_args()
    sys.setswitchinterval(0.001)      # le calcul HD en tache de fond ne doit pas retarder le dessin
    if a.saves_lecture is None:
        dossiers = sorted(glob.glob(os.path.join(jeux, 'saves', '*')))
        a.saves_lecture = dossiers[-1] if dossiers else a.saves_ecriture
    if a.script is not None:
        sc = {}; cur = 0; pts = sorted((int(x.split(':')[0]), int(x.split(':')[1], 0)) for x in a.script.split(','))
        a.script = {}
        for n in range(0, 100000):
            if n > a.images + 5: break
            for (i, m) in pts:
                if n >= i: cur = m
            a.script[n] = cur
    Jeu(a)
    pyglet.app.run()


if __name__ == '__main__':
    main()
