"""Terrain : cartes, decors, personnages (sprites), ombres, carte du monde, icones de lieux."""
import math, os, threading, time
import numpy as np
import pyglet
from pyglet import gl
from dq4_pc.monde import contours_decor as CD
from dq4_pc.monde import decors_plats as DP
from dq4_pc.monde import donnees as DO
from dq4_pc.monde import fbx as FX
from dq4_pc.monde import hd as HD
from dq4_pc.monde import objets_carte as OC
from dq4_pc.monde import teinte_carte as TC
from dq4_pc.noyau import moteur as MO
from dq4_pc.noyau import suivi_charge as SV
from dq4_pc.rendu import ciel_titre as CT
from dq4_pc.rendu import postfx as PF
from dq4_pc.fenetre.constantes import (CH_ATLAS, CH_CASE, CIELS_ETENDUS, CH_GOUT, CH_ICONES, CH_MOTIF_FIN, CH_MOTIF_LIM, CH_MOTIF_NUM, CH_MOTIF_PAS,
    CH_MOTIF_PERIODE, CH_PX, DECOR_BIAIS, GOUT_ORIG, HD_GOUTTIERE, HD_NIVEAUX, MODE_PP, SPRITE_H, SPRITE_L)


class ChampMixin:
    """Terrain : cartes, decors, personnages (sprites), ombres, carte du monde, icones de lieux."""

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
        """Filtrage d'une texture de decor mipmappee (F3) : de loin, toujours mipmaps trilineaires + anisotrope (stable) ; de pres, lisse = bilineaire, sinon plus proche voisin (texels nets)."""
        gl.glBindTexture(t.target, t.id)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR if lisse else gl.GL_NEAREST)
        if self.aniso > 1.0: gl.glTexParameterf(t.target, 0x84FE, self.aniso)

    def _feuille_orig(self, ident):
        """Feuille `h<ident>` d'origine (pixels nets) ; False si absente. 194 = alias de 193 (Chara.SetTexture)."""
        ident = HD.ALIAS_FEUILLES.get(ident, ident)
        cle = (ident, 0)
        if cle in self.sprite_tex: return self.sprite_tex[cle]
        arr = self.donnees.feuille(ident); r = False
        if arr is not None:
            arr = HD.nettoyer_feuille(arr)[0]                      # heros : plus de halo violet semi-transparent
            geo = HD.geometrie_feuille(ident, arr)                  # personnage : cases 24 x 32 sur 3 colonnes ; bateau (193) : cases 40 x 40 sur 12 colonnes et panneau plus grand (voir hd.FEUILLES_SPECIALES)
            atlas, _, _ = HD.agrandir_feuille(arr, geo['larg'], geo['haut'], geo['cols'], geo['nl'], lambda c: HD._dilater(c, 2), GOUT_ORIG, 1)         # pixels transparents = couleur du bord voisin : plus de liseré sombre au filtrage
            r = dict(t=self._tex(atlas, False), tw=atlas.shape[1], th=atlas.shape[0], nl=geo['nl'], cols=geo['cols'], pw=geo['pw'], ph=geo['ph'], hd=False, cl=geo['larg'], ch=geo['haut'], g=GOUT_ORIG, arr=arr, geo=geo)
        self.sprite_tex[cle] = r
        return r

    def _calcul_hd(self, arr, geo, ident, cid, algo):
        """(tache de fond) atlas HD d'une feuille, lu dans le cache disque s'il existe (une feuille au decoupage special a un fichier a part : le bateau n'a rien de commun avec l'ancien decoupage 24 x 32)."""
        suffixe = '' if geo['standard'] else '_g%dx%dx%dx%d' % (geo['larg'], geo['haut'], geo['cols'], geo['nl'])
        f = os.path.join(self.args.cache, 'hd_%s_v%d_h%d%s.npy' % (cid, HD.VERSION, ident, suffixe))
        try:
            if os.path.exists(f): return np.load(f), geo['larg'] * HD.FACTEUR, geo['haut'] * HD.FACTEUR
        except Exception: pass
        atlas, cl, ch = HD.agrandir_feuille(arr, geo['larg'], geo['haut'], geo['cols'], geo['nl'], algo, HD_GOUTTIERE)
        try: np.save(f, atlas)
        except Exception: pass
        return atlas, cl, ch

    def _feuille(self, ident, mode):
        """Feuille de sprites pour le mode choisi. Les versions HD sont calculees en tache de fond : en attendant, l'original sert."""
        ident = HD.ALIAS_FEUILLES.get(ident, ident)
        orig = self._feuille_orig(ident)
        if not orig or mode in (0, MODE_PP): return orig
        cle = (ident, mode)
        if cle in self.sprite_tex: return self.sprite_tex[cle]
        fut = self.hd_jobs.get(cle)
        if fut is None:
            _nom, cid, algo = HD.MODES[mode]
            self.hd_jobs[cle] = self.pool.submit(self._calcul_hd, orig['arr'], orig['geo'], ident, cid, algo)
            return orig
        if not fut.done(): return orig
        del self.hd_jobs[cle]
        try: atlas, cl, ch = fut.result()
        except Exception as ex:
            print('lissage HD impossible (%s, h%d) : %s' % (HD.MODES[mode][0], ident, ex), flush=True); self.sprite_tex[cle] = orig; return orig
        r = self.sprite_tex[cle] = dict(t=self._tex(atlas, False, HD_NIVEAUX), tw=atlas.shape[1], th=atlas.shape[0], nl=orig['nl'], cols=orig['cols'], pw=orig['pw'], ph=orig['ph'], cl=cl, ch=ch, g=HD_GOUTTIERE, hd=True)
        if not self.lissage: self._filtrer(r['t'], False)
        return r

    def _maj_champ(self, e):
        """(Re)construit la grille de tuiles quand le moteur en envoie une autre ; l'atlas est la texture Unity `field`."""
        ch = e.champ; mo = e.monde
        if mo is not None and self._vue_champ is not None:      # carte entiere lue dans le moteur : on dessine toute la zone visible (le moteur n'en envoie que 25 colonnes)
            cx, cz, dl, dh = self._vue_champ
            x0 = 4 * int(math.floor((cx - dl - 1) / 4)); x1 = x0 + 4 * int(math.ceil((2 * dl + 7) / 4))                  # bornes sur des multiples de 4 et largeur constante : le maillage garde la meme taille
            y0 = 4 * int(math.floor((cz - dh - 1) / 4)); y1 = y0 + 4 * int(math.ceil((2 * dh + 7) / 4))                  # a la marche et ses sommets sont remplaces sur place (pas de reallocation : pas d'a-coup)
            x0, x1 = max(x0, int(cx) - 120), min(x1, int(cx) + 120); y0, y1 = max(y0, int(cz) - 80), min(y1, int(cz) + 80)
            cols = x1 - x0
            t = mo['ids'][(np.arange(y0, y1) % mo['h'])[:, None], (np.arange(x0, x1) % mo['l'])[None, :]].astype(np.int32).ravel()
            ch = {'x0': x0, 'y0': y0, 'cols': cols}
        else:
            t = np.array(ch['tuiles'], np.int32)
        cle = (ch['x0'], ch['y0'], ch['cols'], hash(t.tobytes()), self.mode == MODE_PP)
        if cle == self.champ_cle: self._rafraichir_motifs(); return
        self.champ_cle = cle
        if self.champ_tex is None:
            arr = self.donnees.texture('field')
            if arr is None: return
            t4 = arr[:CH_ATLAS * 16, :CH_ATLAS * 16].reshape(CH_ATLAS, 16, CH_ATLAS, 16, 4).transpose(0, 2, 1, 3, 4)       # (ligne, colonne, y, x, canal) : une tuile de 16 x 16 par case
            t4 = np.pad(t4, ((0, 0), (0, 0), (CH_GOUT, CH_GOUT), (CH_GOUT, CH_GOUT), (0, 0)), mode='edge')
            self.champ_tex = self._tex(np.ascontiguousarray(t4.transpose(0, 2, 1, 3, 4).reshape(CH_ATLAS * CH_CASE, CH_ATLAS * CH_CASE, 4)), False)      # atlas des tuiles, avec gouttieres
            self.champ_tex_ico = self._tex(arr, False)                                                  # atlas d'origine : les icones de lieux y sont des rectangles quelconques
            self.champ_nearest = None
        cols = ch['cols']; lignes = len(t) // cols
        g = t[:lignes * cols].reshape(lignes, cols)
        self.champ_g = g; self.champ_pat = CH_MOTIF_NUM[np.searchsorted(CH_MOTIF_FIN, g, side='right')]; self.champ_acc_vu = tuple(self.motif_acc)
        if self.champ_base is None or self.champ_base[0] != (cols, lignes):        # sommets de la grille a l'origine (NO, NE, SE, SO, deux triangles par tuile), decales ensuite de (x0, y0)
            X, Z = np.meshgrid(np.arange(cols), np.arange(lignes)); O = np.zeros_like(X)
            P = np.stack([np.stack([X, O, Z], -1), np.stack([X + 1, O, Z], -1), np.stack([X + 1, O, Z + 1], -1), np.stack([X, O, Z + 1], -1)], 2).astype(np.float32)   # (l, c, 4, 3)
            self.champ_base = ((cols, lignes), P[:, :, [0, 1, 2, 0, 2, 3], :].reshape(-1, 3))
        pos = (self.champ_base[1] + np.array([ch['x0'], 0, ch['y0']], np.float32)).ravel(); uv = self._uv_tuiles(g + self.motif_acc[self.champ_pat])
        n = len(pos) // 3
        if self.champ_vl is not None and self.champ_vl.count == n:                  # meme taille : remplacement sur place
            self.champ_vl.position[:] = pos; self.champ_vl.tex_coords[:] = uv
        else:
            if self.champ_vl is not None: self.champ_vl.delete()
            self.champ_vl = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', pos), tex_coords=('f', uv.ravel()), colors=('f', np.ones(n * 4, np.float32)))

    def _uv_tuiles(self, g):
        """Coordonnees de texture (6 sommets par tuile, a plat) de la grille de numeros de tuile `g` ; les tuiles sont stockees tete en bas dans l'atlas."""
        aw = float(CH_ATLAS * CH_CASE)                                                  # atlas copie avec une gouttiere de CH_GOUT pixels autour de chaque tuile
        u0 = ((g % CH_ATLAS) * CH_CASE + CH_GOUT) / aw; v0 = ((g // CH_ATLAS) * CH_CASE + CH_GOUT) / aw; d = 16.0 / aw
        U = np.stack([np.stack([u0, v0], -1), np.stack([u0 + d, v0], -1), np.stack([u0 + d, v0 + d], -1), np.stack([u0, v0 + d], -1)], 2).astype(np.float32)      # (l, c, 4, 2)
        return U[:, :, [0, 1, 2, 0, 2, 3], :].reshape(-1, 2).ravel()

    def _avancer_motifs(self):
        """Une image du jeu sur la carte du monde (NativeManager.Update -> Field.UpdatePattern) : toutes les 17 images, le decalage de chaque motif avance d'un pas, puis retombe a 0 a sa limite."""
        self.motif_n += 1
        if self.motif_n < CH_MOTIF_PERIODE: return
        self.motif_n = 0
        for i in range(1, len(CH_MOTIF_PAS)):
            v = int(self.motif_acc[i]) + CH_MOTIF_PAS[i]
            self.motif_acc[i] = v if v < CH_MOTIF_LIM[i] else 0

    def _rafraichir_motifs(self):
        """Met a jour sur place les coordonnees de texture des tuiles animees quand un motif a change de pas."""
        acc = tuple(self.motif_acc)
        if acc == self.champ_acc_vu or self.champ_vl is None or self.champ_pat is None: return
        self.champ_acc_vu = acc
        if self.champ_pat.any(): self.champ_vl.tex_coords[:] = self._uv_tuiles(self.champ_g + self.motif_acc[self.champ_pat])

    def _tracer_champ(self, e):
        if self.champ_vl is None or self.champ_tex is None: return
        nearest = self.mode == MODE_PP or not self.lissage          # pixel perfect (echelle entiere) ou lissage coupe (F3) : plus proche voisin ; sinon pixels nets aux frontieres adoucies (comme les sprites d'origine)
        if self.champ_nearest != nearest:
            self.champ_nearest = nearest
            for t in (self.champ_tex, self.champ_tex_ico):
                gl.glBindTexture(t.target, t.id)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST if nearest else gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST if nearest else gl.GL_LINEAR)
        net = 0.0 if nearest else 1.0
        tint = self._teinte_decor()                       # paquet 33 sur la carte du monde : Field.SetColor = couleur du materiau des tuiles (Custom/Field : texture x _Color) et de chaque symbole (alpha propre conserve)
        if tint is not None: self._regler_teinte(tint)
        self.prog['cutoff'] = 0.05; self.prog['net'] = net; self.prog['tsize'] = (float(CH_ATLAS * CH_CASE),) * 2
        self._tracer(self.champ_tex, self.champ_vl)
        self.prog['tsize'] = (1024.0, 1024.0)
        q, uv, col = [], [], []
        for s in e.symboles.values():                     # icones de lieux : posees a plat (le heros se tient au milieu du bord bas)
            r = CH_ICONES.get(s['genre'])
            if r is None or not s['vis']: continue
            ox, bas, w, h = r
            x0, z0 = (round(s['x']) if self.mode == MODE_PP else s['x']) / CH_PX, (round(s['y']) if self.mode == MODE_PP else s['y']) / CH_PX; x1, z1 = x0 + w / CH_PX, z0 + h / CH_PX       # a plat sur la carte, comme les tuiles (dessin vu de dessus)
            q += [(x0, 0.02, z0), (x1, 0.02, z0), (x1, 0.02, z1), (x0, 0.02, z0), (x1, 0.02, z1), (x0, 0.02, z1)]
            u0, u1, v1, v0 = ox / 1024.0, (ox + w) / 1024.0, 1 - (bas - h) / 1024.0, 1 - bas / 1024.0
            uv += [(u0, v0), (u1, v0), (u1, v1), (u0, v0), (u1, v1), (u0, v1)]       # tete en bas dans l'atlas, comme les tuiles : le haut de la carte = le bas de l'image
            col += [(1.0, 1.0, 1.0, float(s['alpha']))] * 6
        if q:
            n = len(q); pos = np.array(q, np.float32).ravel(); tc = np.array(uv, np.float32).ravel(); cc = np.array(col, np.float32).ravel()
            if self.champ_ico is None or self.champ_ico[0] != n:
                if self.champ_ico is not None: self.champ_ico[1].delete()
                self.champ_ico = (n, self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', pos), tex_coords=('f', tc), colors=('f', cc)))
            else:
                v = self.champ_ico[1]; v.position[:] = pos; v.tex_coords[:] = tc; v.colors[:] = cc
            self._dom_lie = None                                  # sommets ecrits apres le 1er trace de l'image : sans rebind + commit() ils partent avec l'image precedente (icones en retard d'une image, absentes une image quand leur nombre change)
            self._tracer(self.champ_tex_ico, self.champ_ico[1])
        if tint is not None: self._regler_teinte((1.0, 1.0, 1.0))
        self.prog['net'] = 0.0

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

    def _purger_contours(self, src, garde=CD.TEXTURES_GARDEES):
        """Les textures de decor de combat agrandies x4 (contours_decor.py, 5,6 Mo avec leurs mipmaps) ne sont gardees que pour les derniers decors vus : les plus anciennes rendent leur place sur la carte graphique."""
        while len(self._tex_contours) > garde:
            for i, cle in enumerate(self._tex_contours):
                if cle[0] != src: break
            else: return
            cle = self._tex_contours.pop(i); t = self.tex_gl.pop(cle, None)
            if t is not None: t.delete()

    def _charger_carte(self, nom):
        t_charge = time.perf_counter()
        for vl in self.carte_vl: vl[1].delete()
        for x in self.carte_ext: x[1].delete()
        if self.ciel_ext and self.ciel_ext['vl'] is not None: self.ciel_ext['vl'].delete()
        if self.ciel_plat and self.ciel_plat.get('vl') is not None: self.ciel_plat['vl'].delete()
        self.ciel_ext = None; self.ciel_zoom = None; self.ciel_plat = None; self.carte_ext = []; self.carte_vl = []; self.carte_pos = {}; self.plages = {}; self.noms = {}; self.objets = None; self.palettes = None; self.pam_gl = {}
        src = (os.environ.get('DQ_DECOR') or nom) if nom.startswith('btl_') else nom       # DQ_DECOR : (test) force un autre decor de combat
        c = erreur = None
        for cand in [src] + (DO.decors_de_secours(src) if nom.startswith('btl') else []):         # decor de combat sans la variante demandee (heure) : la plus proche, plutot qu'un decor vide
            try: c = self.donnees.carte(cand)
            except KeyError as ex: erreur = ex; continue
            except Exception as ex: erreur = ex
            if c is not None and cand != src: print('decor %s absent des donnees : %s a la place' % (src, cand), flush=True); src = cand
            break
        if c is None:
            print('carte non chargee :', erreur, flush=True); self.carte_nom = nom; return
        if not os.environ.get('DQ_SANS_DECALAGE'):
            try: DP.decaler(c)                                               # massifs de fleurs & co : triangles plats superposes releves de 3 mm (plus de z-fighting, voir decors_plats.py)
            except Exception as ex: print('decors_plats :', ex, flush=True)
        self.carte_src = src; self.decor_arr = {k: v for k, v in c['textures'].items() if k in c['groupes']}       # textures du decor (agrandies selon le mode de F2, voir _decor_tex)
        self.objets = OC.ObjetsCarte(c)                                   # portes, jarres, tonneaux... : positions affichees (variantes cachees au depart) ; eau, lampes... animees en continu
        self.palettes = OC.PalettesCarte(c)                               # surfaces dont la texture change d'image en image (eau qui scintille, marais...)
        contours = nom.startswith('btl') and not os.environ.get('DQ_SANS_CONTOURS')        # decors de combat : silhouettes des arbres et montagnes adoucies (contours_decor.py) ; DQ_SANS_CONTOURS=1 : (test) texture d'origine
        for key, (pos, uv, col) in c['groupes'].items():
            if key not in c['textures']: continue
            if (src, key) not in self.tex_gl:
                arr = CD.pour_decor(c['textures'][key], key) if contours else c['textures'][key]
                self.tex_gl[(src, key)] = t = self._tex(arr, True, 99); self._filtrer(t, self.lissage)
                if arr is not c['textures'][key]: self._tex_contours.append((src, key)); self._purger_contours(src)
            vl = self.prog.vertex_list(len(pos), gl.GL_TRIANGLES, position=('f', self.objets.cur[key].ravel()), tex_coords=('f', self.objets.uv(key).ravel()), colors=('f', self.objets.col(key).ravel()))
            self.carte_vl.append((self.tex_gl[(src, key)], vl, key)); self.carte_pos[key] = pos.copy()
        for key, dd in self.palettes.defs.items():                         # images de chaque animation de palette
            if key not in c['groupes']: continue
            self.pam_gl[key] = []
            for k, a in enumerate(dd['images']):
                if (src, key, k) not in self.tex_gl:
                    self.tex_gl[(src, key, k)] = t = self._tex(a, True, 99); self._filtrer(t, self.lissage)
                self.pam_gl[key].append(self.tex_gl[(src, key, k)])
        self.objets.sale = set(); self.objets.sale_uv = set(); self.objets.sale_col = set()
        self.plages = c.get('plages', {}); self.noms = c.get('noms', {})
        if nom == 'ev01': self._ciel_titre(c, src)         # ecran-titre : ciel prolonge de part et d'autre de la zone portrait
        elif nom in CIELS_ETENDUS: self._ciel_etendu(c, src, nom)         # dpout, ev09 : plan de ciel prolonge par symetrie (MAP-05)
        allp = np.concatenate([g[0] for g in c['groupes'].values()]) if c['groupes'] else np.zeros((1, 3), np.float32)
        self.bornes_x = (float(np.percentile(allp[:, 0], 0.5)), float(np.percentile(allp[:, 0], 99.5)))
        self.carte_nom = nom
        self.fond_decor = self._fond_combat(c) if nom.startswith('btl_') else None
        print('carte %s : %d groupes' % (nom, len(self.carte_vl)), flush=True)
        SV.noter('carte chargee', nom=nom, groupes=len(self.carte_vl), ms=round(1000 * (time.perf_counter() - t_charge)))

    def _calcul_hd_decor(self, arrs, algo):
        """(tache de fond) textures de decor agrandies par l'algorithme HD du mode de F2 (x8, plafonne a 4096 px de cote). Le bord est repete en boucle avant l'agrandissement : les textures se raccordent."""
        out = {}
        for key, arr in arrs.items():
            h, w = arr.shape[:2]; passes = 3
            while passes > 0 and max(h, w) * 2 ** passes > 4096: passes -= 1
            if passes == 0: out[key] = arr; continue
            a = np.pad(arr, ((2, 2), (2, 2), (0, 0)), mode='wrap')
            r = algo(a) if passes == 3 else HD.agrandir_epx(a, passes)
            f = r.shape[0] // a.shape[0]
            out[key] = np.ascontiguousarray(r[2 * f:r.shape[0] - 2 * f, 2 * f:r.shape[1] - 2 * f])
        return out

    def _decor_hd(self):
        """Textures GL agrandies du decor courant pour le mode de F2 ; None tant que le calcul en tache de fond n'est pas fini (le decor d'origine sert en attendant)."""
        cle = (self.carte_src, self.mode); r = self.decor_hd.get(cle)
        if r is not None: return r
        jc = ('d',) + cle; fut = self.hd_jobs.get(jc)
        if fut is None:
            self.hd_jobs[jc] = self.pool.submit(self._calcul_hd_decor, dict(self.decor_arr), HD.MODES[self.mode][2]); return None
        if not fut.done(): return None
        del self.hd_jobs[jc]
        try: arrs = fut.result()
        except Exception as ex:
            print('lissage HD du decor impossible (%s) : %s' % (self.carte_src, ex), flush=True); arrs = {}
        r = self.decor_hd[cle] = {}
        for k, a in arrs.items():
            r[k] = t = self._tex(a, True, 99); self._filtrer(t, self.lissage)
        while len(self.decor_hd) > 8:                                  # on ne garde que les derniers decors agrandis (memoire de la carte graphique)
            for t in self.decor_hd.pop(next(iter(self.decor_hd))).values(): t.delete()
        return r

    def _teinte_decor(self):
        """Teinte du paquet 33 a appliquer au decor (r, g, b), ou None si elle est neutre (rien ne change : le dessin reste identique). DQ_SANS_TEINTE=1 : (debogage) jamais de teinte, pour comparer."""
        if os.environ.get('DQ_SANS_TEINTE'): return None
        t = self.moteur.etat.teinte
        return None if TC.teinte_neutre(t) else t

    def _regler_teinte(self, t):
        """Ecrit le uniforme `teinte` s'il a change (le programme est en cours d'utilisation)."""
        t = (float(t[0]), float(t[1]), float(t[2]))
        if t != self._teinte_gl: self._teinte_gl = t; self.prog['teinte'] = t

    @staticmethod
    def _culling_decor(actif):
        """Faces cachees du decor (#182) : les shaders du decor de carte du jeu (Custom/fld_normal, fld_atest, fld_trans, fld_transz et leurs variantes sepia) sont en « Cull Back » (lu dans le paquet de donnees :
        ShaderLab culling = 2) : un mur, un toit, un plafond n'a de texture que sur sa face avant ; vu de derriere (camera tournee, de l'exterieur d'une piece) il est invisible, d'ou la vue a travers les murs d'un interieur.
        Unity : face avant = triangle dans le sens horaire a l'ecran (main gauche), comme les modeles 3D (DQ_FBX_CULL) ; DQ_DECOR_CULL : 0 = sans culling (l'ancien rendu), 1 = defaut, 2 = sens inverse (essai)."""
        mode = os.environ.get('DQ_DECOR_CULL', '1')
        if actif and mode != '0':
            gl.glEnable(gl.GL_CULL_FACE); gl.glCullFace(gl.GL_BACK); gl.glFrontFace(gl.GL_CCW if mode == '2' else gl.GL_CW)
        else: gl.glDisable(gl.GL_CULL_FACE); gl.glFrontFace(gl.GL_CCW)

    def _tracer_decor(self, net=False):
        """Decor de la ville ou du combat. Les textures du decor sont des peintures de 8 a 256 px etirees en 3D : en « Originaux » et en pixel perfect (reglages pour les SPRITES) il garde le rendu d'origine,
        lisse (mipmaps + anisotrope, F3 = agrandissement lineaire ou plus proche voisin) ; le mode agrandi (EPX) lui applique l'algorithme HD choisi."""
        r = self._decor_hd() if self.mode not in (0, MODE_PP) else None
        net_o = 1.0 if (net and r is None and self.lissage and not os.environ.get('DQ_DECOR_FLOU')) else 0.0           # villes et donjons en « Originaux » / pixel perfect : texels nets, seule la frontiere entre deux texels est adoucie (comme les sprites) ; en combat, peintures etirees : lissage normal
        est_tr = lambda k: isinstance(k, tuple) and k[0] == 'tr'
        opaques = [x for x in self.carte_vl if not est_tr(x[2])]
        transp = sorted((x for x in self.carte_vl if est_tr(x[2])), key=lambda x: x[2][1])         # file de rendu 3000 + priorite (FldObject.set_priority)
        cutoff0 = self.prog['cutoff']; a2c = self.post.a2c
        sepia = bool(getattr(self.moteur.etat, 'sepia', False)) and not os.environ.get('DQ_SANS_SEPIA')          # paquet 1 : retour en arriere, decor en sepia (les personnages, bulles et menus gardent leurs couleurs)
        if sepia: self.prog['sepia'] = 1.0
        tint = self._teinte_decor(); ids_tz = self.tz.ids() if tint is not None else None; neutre = (1.0, 1.0, 1.0)      # paquet 33 : teinte de tout le decor, sauf les groupes dont la texture a « tz_ » dans son nom (lampes, bougies, vagues)
        if a2c: self.prog['a2c'] = 1.0; gl.glEnable(PF.SAMPLE_ALPHA_TO_COVERAGE); gl.glDisable(gl.GL_BLEND)      # decor opaque decoupe : alpha -> couverture MSAA, sans melange (le melange doublerait l'alpha)
        for pas, liste in ((0, opaques), (1, transp)):
            if pas == 1 and liste:
                if a2c: self.prog['a2c'] = 0.0; gl.glDisable(PF.SAMPLE_ALPHA_TO_COVERAGE); gl.glEnable(gl.GL_BLEND)
                gl.glDepthMask(gl.GL_FALSE); gl.glDepthFunc(gl.GL_LEQUAL); self.prog['cutoff'] = 0.0      # Custom/fld_trans : Blend SrcAlpha OneMinusSrcAlpha, ZWrite Off, ZTest LEqual, pas de rejet
            gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
            cle_ciel = self.ciel_plat['key'] if self.ciel_plat is not None else (self.ciel_zoom['key'] if self.ciel_zoom is not None else None)          # (le ciel du titre a ses propres sommets : jamais de culling)
            for i, (tex, vl, key) in enumerate(liste):
                self._culling_decor(key != cle_ciel)
                gl.glPolygonOffset(0.0, -DECOR_BIAIS * (i + (len(opaques) if pas else 0)))         # decors a plat superposes a la meme hauteur (deux massifs de fleurs, chemin et pelouse...) : sans cela leur profondeur est egale a l'arrondi pres et l'un ou l'autre gagne pixel par pixel, ce qui change a chaque mouvement de la camera (scintillement) ; le groupe dessine en dernier l'emporte, toujours
                pg = self.pam_gl.get(key)
                t = pg[self.palettes.image(key)] if pg else (r.get(key, tex) if r else tex)          # palette animee : image courante (sans agrandissement HD)
                self.prog['net'] = net_o if (r is None or key not in r) else 0.0
                self.prog['tsize'] = (float(t.width), float(t.height))
                if tint is not None: self._regler_teinte(neutre if TC.groupe_tz(key, ids_tz) else tint)
                zoom = CT.zoom_ecran(self._aspect_ville) if (self.ciel_zoom is not None and key == self.ciel_zoom['key'] and self._M_ville is not None) else 1.0
                if zoom > 1.0 + 1e-6: self.prog['mvp'] = tuple(float(x) for x in CT.matrice_zoom(self._M_ville, zoom).T.ravel())          # ciel du titre agrandi autour du centre de l'ecran (#130)
                if not (self.ciel_plat is not None and key == self.ciel_plat['key'] and self._tracer_ciel_plat(t)): self._tracer(t, vl)
                if zoom > 1.0 + 1e-6: self.prog['mvp'] = tuple(float(x) for x in self._M_ville.T.ravel())
            if pas == 1 and liste: gl.glDepthMask(gl.GL_TRUE); gl.glDepthFunc(gl.GL_LESS); self.prog['cutoff'] = cutoff0
            gl.glDisable(gl.GL_POLYGON_OFFSET_FILL); self._culling_decor(False)
            if pas == 0:
                if tint is not None: self._regler_teinte(tint)
                for tex, vl, key, deb, n, dx in self.carte_ext:
                    self.prog['net'] = net_o; self.prog['tsize'] = (float(tex.width), float(tex.height)); self._tracer(tex, vl)
                if self.ciel_ext is not None: self._tracer_ciel(r, net_o)
        if a2c: self.prog['a2c'] = 0.0; gl.glDisable(PF.SAMPLE_ALPHA_TO_COVERAGE); gl.glEnable(gl.GL_BLEND)
        if tint is not None: self._regler_teinte(neutre)
        if sepia: self.prog['sepia'] = 0.0
        self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0)

    def _fbx_pret(self, no):
        """Modele 3D numero `no` pret a etre dessine ({'m': fbx.ModeleFbx, 'vl', 'tex'...}), None tant qu'il se lit (tache de fond : le cache disque, ou le paquet de donnees la premiere fois) ou s'il n'est pas gere."""
        r = self.fbx_cache.get(no)
        if r is None:
            r = self.fbx_cache[no] = {'etat': 'lecture', 'm': None}
            def tache():
                try: r['m'] = FX.ModeleFbx(self.donnees.modele_fbx(no)); r['etat'] = 'lu'
                except Exception as ex: r['etat'] = 'erreur'; print('Modele 3D %d non affiche : %s' % (no, ex), flush=True)
            threading.Thread(target=tache, daemon=True).start()
        if r['etat'] == 'lu':                                       # objets OpenGL : dans le fil du dessin
            try:
                m = r['m']; nt = len(m.tri)
                self.tex_gl[('fbx', no)] = r['tex'] = t = self._tex(m.tex, True, 99); self._filtrer(t, self.lissage)
                r['uv'] = m.uv[m.tri.ravel()].ravel().astype(np.float32); r['n'] = nt * 3
                r['vl'] = self.prog.vertex_list(r['n'], gl.GL_TRIANGLES, position=('f', np.zeros(r['n'] * 3, np.float32)), tex_coords=('f', r['uv']), colors=('f', np.ones(r['n'] * 4, np.float32)))
                r['etat'] = 'pret'
            except Exception as ex: r['etat'] = 'erreur'; print('Modele 3D %d non affiche : %s' % (no, ex), flush=True)
        return r if r['etat'] == 'pret' else None

    def _tracer_fbx(self, e):
        """Modeles 3D de la scene (e.fbx) : pose = position / rotation / echelle du moteur (paquet 32), animation jouee depuis son lancement (images du moteur : 30 Hz, fraction de pas comprise), couleur = Material.color.
        Shader Custom/ImdChara : couleur du sommet x _Color x texture, fusion alpha, ZWrite, ZTest LEqual, Cull Back, file Geometry (avec le decor opaque, avant les personnages et les effets-maillages)."""
        tf = max(0.0, self.moteur.images - 2.0 + self.alpha)           # image du moteur affichee : celle du pas precedent + alpha (voir _interpoler)
        for k in [k for k in self.fbx_lect if k not in e.fbx]: del self.fbx_lect[k]
        for slot, mod in sorted(e.fbx.items()):
            if not mod['vis']: continue
            r = self._fbx_pret(mod['id'])
            if r is None: continue
            m = r['m']; lc = self.fbx_lect.get(slot)
            if lc is None or lc['id'] != mod['id'] or lc['n'] > len(mod['anim']):
                lc = self.fbx_lect[slot] = {'id': mod['id'], 'n': 0, 'a': FX.LecteurAnim({k: {'dur': c['dur'], 'wrap': c['wrap']} for k, c in m.clips.items()})}
            for img, seq, force in mod['anim'][lc['n']:]: lc['a'].jouer(seq, force, img)
            lc['n'] = len(mod['anim'])
            ech = 0.4 if mod['id'] == 10 else 1.0                      # FbxObject.m_defScale (.ctor : 0,4 pour le modele 10, 1 sinon)
            sc = tuple(float(x) * ech for x in mod['scl'])
            V = m.sommets(FX.matrice_objet(mod['pos'], mod['rot'], sc), lc['a'].poses(tf))
            vl = r['vl']; vl.position[:] = V[m.tri.ravel()].ravel(); vl.colors[:] = np.tile(np.array(mod['col'], np.float32), r['n'])
            self.prog['cutoff'] = 0.0; self.prog['net'] = 1.0 if self.lissage else 0.0; self.prog['tsize'] = (float(m.tex.shape[1]), float(m.tex.shape[0]))
            self._dom_lie = None
            cull = os.environ.get('DQ_FBX_CULL', '1')                   # Custom/ImdChara : Cull Back (lu dans le shader) ; DQ_FBX_CULL=0 : sans culling, 2 : sens inverse (l'ancien, faux : on voyait l'interieur du dragon) pour comparer
            if cull != '0':
                gl.glEnable(gl.GL_CULL_FACE); gl.glCullFace(gl.GL_BACK)
                gl.glFrontFace(gl.GL_CCW if cull == '2' else gl.GL_CW)         # Unity : face avant = triangle dans le sens horaire a l'ecran (main gauche), l'inverse du defaut d'OpenGL ; sans cela on ne dessinait que les faces arrieres (l'interieur du dragon : visage vu de l'interieur, corps vu de dos)
            self._tracer(r['tex'], vl)
            gl.glDisable(gl.GL_CULL_FACE); gl.glFrontFace(gl.GL_CCW)
        self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0); self.prog['cutoff'] = 0.05

    def _tex_icone(self, ident):
        """Texture de l'icone `ident` (case 32 x 32 de la feuille MenuTexture, numerotee de gauche a droite et de haut en bas ; Riseup.SetTexture -> UV 1/32) ; None si la feuille est absente."""
        if ident in self.icone_tex: return self.icone_tex[ident]
        if self._menu_tex is None:
            try:
                from PIL import Image
                self._menu_tex = np.array(Image.open(os.path.join(self.args.cache, 'ui_MenuTexture.png')).convert('RGBA'))
            except Exception: self._menu_tex = False
        t = None
        if self._menu_tex is not False:
            r, c = divmod(ident, 32); h = self._menu_tex.shape[0]
            if (r + 1) * 32 <= h: t = self._tex(HD._dilater(self._menu_tex[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32], 3), False)          # (couleur du bord sous les pixels transparents : pas de liseré clair au filtrage)
        self.icone_tex[ident] = t
        return t

    def _icones(self, e, champ, bataille, dh, cam3d=None):
        """Bulles d'icone au-dessus des personnages (paquets 19/20, Riseup : carre de 0,96 face a la camera, avance de 0,48 vers elle) : [(texture, vertex_list)]."""
        if champ or bataille or not e.icones or e.cam_pos is None or e.cam_cible is None: return []
        fwd = np.array(e.cam_cible, float) - np.array(e.cam_pos, float); fwd /= np.linalg.norm(fwd) or 1
        out = []; corr = self._correction_bords(); C_vue = self._cadre_vue[0] if self._cadre_vue is not None else None
        for slot, ic in sorted(e.icones.items()):
            if ic['pos'] is None or ic['alpha'] < 0.02: continue
            tex = self._tex_icone(ic['id'])
            if not tex: continue
            if cam3d is not None:
                # de face a l'ecran, comme les personnages (rotation de la camera). Avance de 0,48 vers la camera de la VISIONNEUSE (et non de celle du jeu : tournee ou inclinee par le joueur, elle decalait la bulle a l'ecran),
                # le long du rayon de vue (voir _decaler_profondeur) ; la bulle reste collee au personnage qui la porte, quelle que soit l'inclinaison de la camera (voir _ancrer_icone)
                P = self._ancrer_icone(e, np.array(ic['pos'], float), cam3d); r_, u_, f_ = cam3d; D = self._decaler_profondeur
                A0, B0 = P - r_ * 0.48, P + r_ * 0.48
                a, b, c, d = D(A0, f_, 0.48, corr, C_vue), D(B0, f_, 0.48, corr, C_vue), D(B0 + u_ * 0.96, f_, 0.48, corr, C_vue), D(A0 + u_ * 0.96, f_, 0.48, corr, C_vue)
                q = np.array([a, b, c, a, c, d], np.float32).ravel().tolist()
            else:
                p = np.array(ic['pos'], float) - fwd * 0.48
                a, b, up = p - dh * 0.48, p + dh * 0.48, np.array([0.0, 0.96, 0.0])
                q = np.array([a, b, b + up, a, b + up, a + up], np.float32).ravel().tolist()
            uv = [0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1]; cl = [1.0, 1.0, 1.0, float(min(max(ic['alpha'], 0.0), 1.0))] * 6
            vl = self.icone_vl.get(slot)
            if vl is None: vl = self.icone_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            out.append((tex, vl))
        return out

    def _ancrer_icone(self, e, P, cam3d):
        """Position d'une bulle d'icone (paquet 20) pour la camera de la visionneuse. Le moteur la pose au-dessus de la cible (1,294 au-dessus de ses pieds, mesure sur trois villageois) en coordonnees du MONDE, alors que
        les personnages sont des panneaux de face a la camera : si la camera du joueur est inclinee ou tournee, la hauteur de la bulle par rapport a la tete change (1,294 x cos de l'inclinaison a l'ecran, contre une hauteur
        de panneau fixe) et elle semble trop haute ou trop basse. Quand un personnage est sous la bulle (meme x, z), on garde donc l'ecart tel que la camera DU JEU le voit (composantes droite / haut / avant) et on le
        rapporte au repere de la camera de la visionneuse : la bulle reste a la meme place par rapport a la tete (identique a P quand les deux cameras sont les memes). Sans personnage dessous (tonneau, jarre...) : P, ancre dans le monde."""
        S = None; meilleur = 0.35
        for sp in e.sprites.values():
            pos = sp.get('pos')
            if pos is None or len(pos) < 3 or not sp.get('vis', True): continue
            dx, dz, dy = P[0] - pos[0], P[2] - pos[2], P[1] - pos[1]
            if 0.3 < dy < 3.0 and math.hypot(dx, dz) < meilleur: meilleur = math.hypot(dx, dz); S = np.array(pos, float)
        if S is None: return P
        try: _, Dr, H, F = self._cadre_jeu(e)
        except Exception: return P
        d = P - S
        return S + cam3d[0] * float(d @ Dr) + cam3d[1] * float(d @ H) + cam3d[2] * float(d @ F)

    def _carte_ports(self):
        """Fenetres de la carte ouverte (FieldImageMap) : {25: plan fixe, 26: grande carte qui se complete, 24: liste des boutiques de la ville, 22: bouton retour} -> port ; vide si aucune carte n'est ouverte."""
        r = {}; cachees = {}
        for p, f in self.moteur.ui.f.items():
            if p >= 12 and f.get('type') in (22, 23, 24, 25, 26):
                t = 22 if f['type'] == 23 else f['type']
                if f.get('vis'): r[t] = p
                elif f.get('act'): cachees[t] = p                       # fenetre creee mais pas montree (la 2e vue de la carte, avant qu'on y passe)
        if r:
            for t, p in cachees.items(): r.setdefault(t, p)
        return r                                                      # (des fenetres de carte restees creees apres la fermeture ne comptent pas : sans fenetre visible, la carte est fermee)

    def _plan_fenetre(self, fe, f):
        """Fenetre de carte du moteur (type 25) : texture du plan nommee par le moteur et marqueur de position (coordonnees en pixels de la texture de 256 x 192)."""
        nom = f['cases'].get((0, 0))
        if nom and fe.nom_carte != nom:
            fe.nom_carte = nom
        li = f.get('listes') or {}                                 # lieux decouverts (code 3 : x + 256 y, un par nombre) et voile des blocs non explores (code 5) envoyes par le moteur
        fe.symboles = [(v & 0xff, v >> 8 & 0xff) for v in li.get(3, ())]
        if fe.symboles and getattr(fe, 't_blink', None) is None: fe.t_blink = time.monotonic()
        v4 = f['indic'].get(4); fe.special = None if v4 is None else (v4 & 0xff, v4 >> 8 & 0xff)        # code 4 : lieu special (croix rouge), meme codage que les lieux : x + 256 y
        cle = tuple(li[5][:16]) if li.get(5) else None
        if fe.nom_carte and (fe.carte is None or getattr(fe, '_cle_tex', None) != (fe.nom_carte, cle)):
            fe._cle_tex = (fe.nom_carte, cle)
            hd_a = self.plans.get(fe.nom_carte)                    # plan agrandi (1024 x 768) : Lanczos, avec arrondi des contours (EPX) pour le plan du monde dont les terres sont en pixel art
            if hd_a is None:
                try:
                    a = self.donnees.texture(fe.nom_carte)
                    if a is not None: hd_a = self.plans[fe.nom_carte] = HD.agrandir_plan(a, epx=fe.nom_carte.startswith('dsdq4w'))
                except Exception as ex: print('Plan %s illisible : %r' % (fe.nom_carte, ex), flush=True)
            if hd_a is not None:
                if cle:                                            # carte du monde : voile (silhouette grisee) sur les blocs de 10 x 10 pixels non explores (16 x 16 blocs a partir de x = 48, y = 16 du plan de 256 x 192)
                    src = self.donnees.voile_monde()
                    if src is not None: hd_a = HD.voiler_plan(hd_a, src, cle)
                t = pyglet.image.ImageData(hd_a.shape[1], hd_a.shape[0], 'RGBA', np.ascontiguousarray(hd_a[::-1]).tobytes(), pitch=hd_a.shape[1] * 4).get_texture()
                gl.glBindTexture(t.target, t.id)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
                if fe.carte is not None: fe.carte.delete()
                fe.carte = t; fe.carte_mode = 0
        nd = next((o for o in fe.N.values() if o['mats'] and o['mats'][0].get('part') == 3), None)      # marqueur « vous etes ici » (icone de 24 x 24, partie 3 ; son numero change d'une generation de la mise en page a l'autre) centre sur le point (x, y) du plan
        mx, my = f['indic'].get(1), f['indic'].get(2)
        if nd is not None and mx is not None and my is not None:
            nd['pos'][0] = -223.0 + mx * 1.740234; nd['pos'][2] = 398.0 - my * 1.740234; nd['act'] = True        # AddIcon(Vector3.zero, 31, bInBounds) : le coin bas gauche de l'icone (la pointe de la plume) est sur la position, dans le plan de 450 x 337,5 pose en (2, -2) a l'echelle 0,99 (0,99 x 450 / 256)

    def _plan_monde_fenetre(self, fe, f):
        """Grande carte du monde (type 26, Make_WorldLargeMap) : le moteur envoie le drapeau des pieces du plan (indicateur 0), puis la position du joueur x, y (indicateurs 1 et 2) en pixels d'un plan de
        1024 x 1024. Le jeu compose le plan (LoadLargeWorldMap : fond + pieces dont le bit est leve dans le drapeau) et n'en montre qu'une fenetre de 256 x 192 pixels centree sur le joueur
        (decalage de texture x / 1024 - 0,125 ; le marqueur reste au centre de la fenetre)."""
        flag = f['indic'].get(0, 0) & 0xffff; x, y = f['indic'].get(1), f['indic'].get(2)
        if getattr(fe, '_flag_plan', None) != flag or fe.carte is None:
            try: pl = self.donnees.plan_monde()
            except Exception as ex: pl = None; print('Plan du monde illisible : %r' % (ex,), flush=True)
            if pl is None: return
            im = pl['base'].copy()
            for bit, px, py, a in pl['pieces']:
                if flag >> bit & 1: im[py:py + a.shape[0], px:px + a.shape[1]] = a
            rgba = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
            if fe.carte is not None: fe.carte.delete()
            t = pyglet.image.ImageData(1024, 1024, 'RGBA', np.ascontiguousarray(rgba[::-1]).tobytes(), pitch=4096).get_texture()
            gl.glBindTexture(t.target, t.id)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
            fe.carte = t; fe._flag_plan = flag; fe.carte_mode = 3
        if x is not None and y is not None:
            fe.carte_uv = ((x - 128) / 1024.0, 1.0 - (y + 96) / 1024.0, (x + 128) / 1024.0, 1.0 - (y - 96) / 1024.0)

    def _objets_carte(self):
        """Ordres du moteur sur les objets de la carte (portes, jarres...), puis une image d'animation ; les sommets modifies sont renvoyes a la carte graphique."""
        e = self.moteur.etat; cmds, e.objets_cmd = e.objets_cmd, []
        for c in cmds:
            if c[0] == 'carte':
                if self.objets is not None and self.carte_nom == e.carte: self.objets.reinit()
                continue
            if self.objets is None: continue
            if self.carte_nom != e.carte and e.partie != MO.PARTIE_CHAMP and e.carte: self._charger_carte(e.carte)       # la carte est chargee avant ses ordres
            if c[0] == 'anim': self.objets.anim_commune(c[1], c[2])
            elif c[0] == 'onoff': self.objets.on_off(c[1], c[2])
            elif c[0] == 'alpha': self.objets.alpha(c[1], c[2])
            elif c[0] == 'pos': self.objets.position(c[1], c[2])
            elif c[0] == 'rot': self.objets.rotation(c[1], c[2])
        if self.objets is None: return
        if os.environ.get('DQ_ANIM_TEST') and self.carte_nom == os.environ.get('DQ_CARTE_TEST', ';').split(';')[0]:   # (test) DQ_ANIM_TEST="objet:numero:image" : lance une animation commune a cette image de boucle
            o_t, no_t, n_t = (int(v) for v in os.environ['DQ_ANIM_TEST'].split(':'))
            if self.n == n_t: self.objets.anim_commune(o_t, no_t)
        sales = self.objets.tick()
        if self.palettes is not None: self.palettes.tick()
        sales_uv, sales_col = self.objets.sale_uv, self.objets.sale_col; self.objets.sale_uv = set(); self.objets.sale_col = set()
        for tex, vl, key, deb, n, dx in self.carte_ext:
            if key in sales: vl.position[:] = CT.positions_copie(self.objets.cur[key][deb:deb + n], dx).ravel()
        for tex, vl, key in self.carte_vl:
            if key in sales: vl.position[:] = self.objets.cur[key].ravel()
            if key in sales_uv: vl.tex_coords[:] = self.objets.uv(key).ravel()
            if key in sales_col: vl.colors[:] = self.objets.col(key).ravel()

    def _orienter_decor(self, cam3d):
        """Panneaux de decor tournes vers la camera ; les sommets modifies sont renvoyes a la carte graphique seulement si l'orientation a change."""
        fw = cam3d[2]
        if not self.objets.orienter(math.atan2(fw[0], fw[2]), cam3d, 0.0): return
        sales, self.objets.sale = self.objets.sale, set()
        for tex, vl, key in self.carte_vl:
            if key in sales: vl.position[:] = self.objets.cur[key].ravel()

    def _duree_anim(self, idx, no):
        return self.objets.duree(idx, no) if self.objets is not None else None

    # ---- boucle
    def _tenue(self, action):
        """Une des touches de l'action (menu Touches) est-elle enfoncee ? (Une touche avalee par un raccourci, Entree de Alt + Entree, ne compte pas jusqu'a son relachement.)"""
        k = self.touches; av = self.avalees
        return any(k[c] and c not in av for c in self.reg.codes(action))

    def _terrain_libre(self):
        """Terrain sans fenetre : ni menu d'Echap, ni message, ni menu ou carte du jeu, ni combat, ni effet d'ecran. Sinon les fleches naviguent dans les fenetres (elles ne font rien sur le terrain : plus de camera a la main, #264)."""
        mo = self.moteur; e = mo.etat
        return (not self.pause.ouvert and self.titre is None and e.partie in (MO.PARTIE_VILLE, MO.PARTIE_CHAMP) and not mo.msg_visible and mo.menu_actif() is None and not self.carte_ouverte and e.effet is None and getattr(e, 'effet_ecran', None) is None)

    # ombre des personnages : Chara.s_shadowMesh (carre +-1 en XZ, Y = 0,00625), echelle s_shadowDefScale (0,347 ; 10 ; 0,206), texture CharaTex/common (32 x 32 : ellipse noire d'alpha 96 / 255, filtre point),
    # shader Custom/CharaShadow (SrcAlpha / OneMinusSrcAlpha, ZWrite Off, ZTest LEqual, file 2999 = avant les personnages), position Chara.SetShadowPosition = pos + rotation du panneau x (0 ; 0 ; 0,25)
    # (donc decalee de 0,25 le long du rayon de la camera : meme point a l'ecran, mais devant le sol), orientation Euler(0, lacet de la camera, 0) = a plat.
    OMBRE_DEMI = (0.347, 0.206); OMBRE_HAUT = 0.0625; OMBRE_DEC = 0.25

    def _dessiner_ombres_chara(self, ombres, cam3d):
        if getattr(self, '_ombre_tex', None) is None: self._ombre_tex_creer()
        if not self._ombre_tex: return
        r_, u_, f_ = cam3d
        rh = np.array([r_[0], 0.0, r_[2]]); rh /= np.linalg.norm(rh) or 1                 # lacet seul de la camera
        fh = np.array([f_[0], 0.0, f_[2]]); fh /= np.linalg.norm(fh) or 1
        ex, ez = self.OMBRE_DEMI
        gl.glDepthMask(gl.GL_FALSE); gl.glDepthFunc(gl.GL_LEQUAL)
        self.prog['cutoff'] = 0.0; self.prog['net'] = 0.0; self.prog['tsize'] = (64.0, 64.0)
        for slot, p, alpha in ombres:
            c = p - f_ * self.OMBRE_DEC + np.array([0.0, self.OMBRE_HAUT, 0.0])
            P = [c - rh * ex - fh * ez, c + rh * ex - fh * ez, c + rh * ex + fh * ez, c - rh * ex + fh * ez]
            q = np.array([P[0], P[1], P[2], P[0], P[2], P[3]], np.float32).ravel().tolist()
            uv = [0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1]; cl = [1.0, 1.0, 1.0, min(1.0, alpha)] * 6          # _Color.a = SetShadowAlpha (1 par defaut), x alpha du personnage (SetColorWithShadow)
            vl = self._ombre_vl.get(slot)
            if vl is None: vl = self._ombre_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            self._tracer(self._ombre_tex, vl)
        gl.glDepthMask(gl.GL_TRUE); gl.glDepthFunc(gl.GL_LESS); self.prog['cutoff'] = 0.05        # (les personnages qui suivent rejettent les pixels transparents : sinon leur panneau entier ecrit la profondeur et masque le compagnon derriere)

    # ombre des personnages sur la carte du monde : Chara.SetFieldMode redimensionne le maillage d'ombre a s_shadowDefScale x 28,8 (ellipse de demi-axes 10 x 5,9 pixels de la carte) et l'incline de 36 degres comme le personnage
    # (projetee : 5,9 x cos 36 = 4,8) ; Chara.SetFieldPosition la pose au meme point que le personnage (ses pieds). Le moteur masque celle des bateaux (paquet 15).
    OMBRE_CH = (9.99, 5.93 * math.cos(math.radians(36.0)))

    def _dessiner_ombres_champ(self, ombres, ech):
        if getattr(self, '_ombre_tex', None) is None: self._ombre_tex_creer()
        gl.glDepthMask(gl.GL_FALSE); gl.glDepthFunc(gl.GL_LEQUAL)
        self.prog['cutoff'] = 0.0; self.prog['net'] = 0.0; self.prog['tsize'] = (64.0, 64.0)
        rx, rz = self.OMBRE_CH[0] * ech / CH_PX, self.OMBRE_CH[1] * ech / CH_PX
        for slot, p, alpha in ombres:
            x, y, z = float(p[0]), 0.03, float(p[2])
            q = [x - rx, y, z - rz, x + rx, y, z - rz, x + rx, y, z + rz, x - rx, y, z - rz, x + rx, y, z + rz, x - rx, y, z + rz]
            uv = [0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1]; cl = [1.0, 1.0, 1.0, min(1.0, alpha)] * 6
            vl = self._ombre_vl.get(slot)
            if vl is None: vl = self._ombre_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            self._tracer(self._ombre_tex, vl)
        gl.glDepthMask(gl.GL_TRUE); gl.glDepthFunc(gl.GL_LESS); self.prog['cutoff'] = 0.05

    def _ombre_tex_creer(self):
        # texture CharaTex/common : ellipse d'alpha 96 / 255 aux bords nets (filtre point) ; ici le meme maximum et la meme taille, mais le bord est adouci (ombres « trop brutes »)
        n = 64; yy, xx = np.mgrid[0:n, 0:n]; r = np.hypot((xx + 0.5 - n / 2) / (n / 2), (yy + 0.5 - n / 2) / (n / 2)); k = np.clip((r - 0.45) / 0.55, 0.0, 1.0)
        a = np.zeros((n, n, 4), np.uint8); a[..., 3] = np.round(96 * (1.0 - k * k * (3 - 2 * k))).astype(np.uint8)
        t = self._tex(a, False)
        gl.glBindTexture(t.target, t.id); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        self._ombre_tex = t; self._ombre_vl = {}
