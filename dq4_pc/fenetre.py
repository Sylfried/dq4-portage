"""Fenetre PC 16/9 : fait tourner le moteur du jeu et dessine ce qu'il demande (decor, sprites, camera)."""
import os, sys, math, time, argparse, glob
import numpy as np
import pyglet
from pyglet import gl
from pyglet.graphics.shader import Shader, ShaderProgram


import moteur as MO
import donnees as DO

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
        cfg = gl.Config(depth_size=24, double_buffer=True, major_version=3, minor_version=3)
        super().__init__(args.largeur, args.hauteur, caption='Dragon Quest IV - portage PC (essai)', resizable=True, config=cfg, vsync=True)
        self.args = args
        self.prog = ShaderProgram(Shader(VERT, 'vertex'), Shader(FRAG, 'fragment'))
        self.donnees = DO.Donnees(None, args.cache, log=lambda *a: print(*a, flush=True))
        self.moteur = MO.Moteur(args.apk, args.saves_lecture, args.saves_ecriture)
        self.donnees.apk = self.moteur.apk_donnees
        self.touches = pyglet.window.key.KeyStateHandler(); self.push_handlers(self.touches)
        self.carte_nom = None; self.carte_vl = []; self.tex_gl = {}; self.sprite_tex = {}
        self.carte_pos = {}; self.carte_cur = {}; self.plages = {}; self.noms = {}; self.portes = {}; self.bornes_x = None
        self.etiquette = pyglet.text.Label('', x=10, y=self.height - 10, anchor_y='top', font_size=11, color=(255, 255, 255, 255))
        if args.slot:
            ok = self.moteur.charger_sauvegarde(args.slot)
            print('sauvegarde %d chargee : %s' % (args.slot, 'oui' if ok else 'NON (fichier data%d.dat introuvable ou invalide dans %s)' % (args.slot, args.saves_lecture)), flush=True)
            if ok:      # on laisse le moteur lancer la carte sauvegardee avant le premier affichage
                for _ in range(6): self.moteur.step(0, 0)
        self.n = 0; self.dt_moteur = 0.0; self.pad_prec = 0; self.rep = {}
        self.msg_cle = None; self.msg_img = None; self.msg_spr = None; self.msg_h = 0
        self.etiq_menu = {}; self.focus_vu = None; self.menu_relacher = None
        pyglet.clock.schedule_interval(self.tick, 1 / 30.0)

    # ---- textures
    def _tex(self, arr, repeat):
        h, w = arr.shape[:2]
        img = pyglet.image.ImageData(w, h, 'RGBA', np.ascontiguousarray(arr[::-1]).tobytes(), pitch=w * 4)
        t = img.get_texture()
        gl.glBindTexture(t.target, t.id)
        m = gl.GL_REPEAT if repeat else gl.GL_CLAMP_TO_EDGE
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, m); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, m)
        return t

    def _charger_carte(self, nom):
        for vl in self.carte_vl: vl[1].delete()
        self.carte_vl = []; self.carte_pos = {}; self.carte_cur = {}; self.plages = {}; self.noms = {}; self.portes = {}
        try:
            c = self.donnees.carte(nom)
        except Exception as ex:
            print('carte non chargee :', ex, flush=True); self.carte_nom = nom; return
        for key, (pos, uv, col) in c['groupes'].items():
            if key not in c['textures']: continue
            if (nom, key) not in self.tex_gl: self.tex_gl[(nom, key)] = self._tex(c['textures'][key], True)
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
        self.prog.use()
        self.prog['mvp'] = tuple(float(x) for x in M.T.ravel()); self.prog['cutoff'] = 0.5; self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0); self.prog['amul'] = 1.0
        gl.glActiveTexture(gl.GL_TEXTURE0)
        for tex, vl, _cle in self.carte_vl:
            gl.glBindTexture(tex.target, tex.id); vl.draw(gl.GL_TRIANGLES)
        # sprites : panneaux verticaux tournes vers la camera
        fh = np.array([e.cam_cible[0] - e.cam_pos[0], 0, e.cam_cible[2] - e.cam_pos[2]]); fh /= np.linalg.norm(fh) or 1
        dh = np.cross([0, 1, 0], fh); dh /= np.linalg.norm(dh) or 1
        self.prog['cutoff'] = 0.05; self.prog['net'] = 1.0
        for slot, s in sorted(e.sprites.items()):
            if s['pos'] is None or s['col'][3] < 0.02: continue
            tex = self.sprite_tex.get(s['id'])
            if tex is None:
                arr = self.donnees.feuille(s['id'])
                tex = self.sprite_tex[s['id']] = (self._tex(arr, False), arr.shape[1], arr.shape[0], 8 if arr[4 * SPRITE_H:5 * SPRITE_H, :72, 3].any() else 4) if arr is not None else False
            if not tex: continue
            t, tw, th, nl = tex
            self.prog['tsize'] = (float(tw), float(th))
            col, row = s['pose'] % 3, s['dir'] % nl
            u0, u1 = col * SPRITE_L / tw, (col + 1) * SPRITE_L / tw; v1, v0 = 1 - row * SPRITE_H / th, 1 - (row + 1) * SPRITE_H / th
            p = np.array(s['pos'], float); w, h = SPRITE_L * SPRITE_ECHELLE, SPRITE_H * SPRITE_ECHELLE
            a, b = p - dh * w / 2, p + dh * w / 2; up = np.array([0, h, 0])
            q = np.array([a, b, b + up, a, b + up, a + up], np.float32)
            uv = np.array([[u0, v0], [u1, v0], [u1, v1], [u0, v0], [u1, v1], [u0, v1]], np.float32)
            cl = np.tile(np.array(s['col'], np.float32), (6, 1))
            vl = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q.ravel()), tex_coords=('f', uv.ravel()), colors=('f', cl.ravel()))
            gl.glBindTexture(t.target, t.id); vl.draw(gl.GL_TRIANGLES)
            if slot < 8:       # equipe : silhouette translucide quand un decor la cache
                gl.glDepthFunc(gl.GL_GREATER); gl.glDepthMask(gl.GL_FALSE); self.prog['amul'] = 0.4
                vl.draw(gl.GL_TRIANGLES)
                gl.glDepthFunc(gl.GL_LESS); gl.glDepthMask(gl.GL_TRUE); self.prog['amul'] = 1.0
            vl.delete()
        self.prog.stop()
        gl.glDisable(gl.GL_DEPTH_TEST)
        self.etiquette.text = 'Carte %s | %.0f ms moteur | fleches/ZQSD : marcher | Entree : valider/parler | Retour arriere ou X : menu/annuler | Echap : quitter' % (e.carte, self.dt_moteur * 1000)
        self.etiquette.y = self.height - 10
        self._maj_message(); self._dessiner_message(); self._dessiner_menus()
        self.etiquette.draw()


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
    ap.add_argument('--shot', default=None, help='(test) enregistre une capture puis quitte')
    ap.add_argument('--images', type=int, default=60)
    ap.add_argument('--script', default=None, help='(test) ex. "20:2,30:0" : image:masque de touches')
    a = ap.parse_args()
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
