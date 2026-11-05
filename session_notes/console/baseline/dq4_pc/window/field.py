"""Terrain : cartes, decors, personnages (sprites), ombres, carte du monde, icones de lieux."""
import math, os, threading, time
import numpy as np
import pyglet
from pyglet import gl
from dq4_pc.language import tr
from dq4_pc.world import scenery_outlines as CD
from dq4_pc.world import flat_sceneries as DP
from dq4_pc.world import data as DO
from dq4_pc.world import fbx as FX
from dq4_pc.world import hd as HD
from dq4_pc.world import map_objects as OC
from dq4_pc.world import map_tint as TC
from dq4_pc.core import engine as ENGINE
from dq4_pc.core import load_tracking as SV
from dq4_pc.render import title_sky as CT
from dq4_pc.render import postfx as PF
from dq4_pc.window.constants import (TITLE_MAP, CH_ATLAS, CH_CELL, EXTENDED_SKIES, CH_GUTTER, CH_ICONS, CH_PATTERN_END, CH_PATTERN_LIMIT, CH_PATTERN_NUM, CH_PATTERN_STEP,
    CH_PATTERN_PERIOD, CH_PX, SCENERY_BIAS, ORIGINAL_GUTTER, HD_GUTTER, HD_LEVELS, MODE_PP, SPRITE_H, SPRITE_L)


class FieldMixin:
    """Terrain : cartes, decors, personnages (sprites), ombres, carte du monde, icones de lieux."""

    # ---- textures
    def _anisotropy(self):
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
            self._filter_texture(t, True)
        return t

    def _filter_texture(self, t, smooth):
        """Filtrage d'une texture de decor mipmappee (F3) : de loin, toujours mipmaps trilineaires + anisotrope (stable) ; de pres, lisse = bilineaire, sinon plus proche voisin (texels nets)."""
        gl.glBindTexture(t.target, t.id)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR if smooth else gl.GL_NEAREST)
        if self.aniso > 1.0: gl.glTexParameterf(t.target, 0x84FE, self.aniso)

    def _original_sheet(self, ident):
        """Feuille `h<ident>` d'origine (pixels nets) ; False si absente. 194 = alias de 193 (Chara.SetTexture)."""
        ident = HD.SHEET_ALIASES.get(ident, ident)
        lookup_key = (ident, 0)
        if lookup_key in self.sprite_tex: return self.sprite_tex[lookup_key]
        arr = self.data.sheet(ident); r = False
        if arr is not None:
            arr = HD.clean_sheet(arr)[0]                      # heros : plus de halo violet semi-transparent
            geo = HD.sheet_geometry(ident, arr)                  # personnage : cases 24 x 32 sur 3 colonnes ; bateau (193) : cases 40 x 40 sur 12 colonnes et panneau plus grand (voir hd.SPECIAL_SHEETS)
            atlas, _, _ = HD.upscale_sheet(arr, geo['larg'], geo['haut'], geo['cols'], geo['nl'], lambda c: HD._dilate(c, 2), ORIGINAL_GUTTER, 1)         # pixels transparents = couleur du bord voisin : plus de liseré sombre au filtrage
            r = dict(t=self._tex(atlas, False), tw=atlas.shape[1], th=atlas.shape[0], nl=geo['nl'], cols=geo['cols'], pw=geo['pw'], ph=geo['ph'], hd=False, cl=geo['larg'], ch=geo['haut'], g=ORIGINAL_GUTTER, arr=arr, geo=geo)
        self.sprite_tex[lookup_key] = r
        return r

    def _calc_hd(self, arr, geo, ident, cid, algo):
        """(tache de fond) atlas HD d'une feuille, lu dans le cache disque s'il existe (une feuille au decoupage special a un fichier a part : le bateau n'a rien de commun avec l'ancien decoupage 24 x 32)."""
        suffix = '' if geo['standard'] else '_g%dx%dx%dx%d' % (geo['larg'], geo['haut'], geo['cols'], geo['nl'])
        f = os.path.join(self.args.cache, 'hd_%s_v%d_h%d%s.npy' % (cid, HD.VERSION, ident, suffix))
        try:
            if os.path.exists(f): return np.load(f), geo['larg'] * HD.FACTOR, geo['haut'] * HD.FACTOR
        except Exception: pass
        atlas, cl, ch = HD.upscale_sheet(arr, geo['larg'], geo['haut'], geo['cols'], geo['nl'], algo, HD_GUTTER)
        try: np.save(f, atlas)
        except Exception: pass
        return atlas, cl, ch

    def _sheet(self, ident, mode):
        """Feuille de sprites pour le mode choisi. Les versions HD sont calculees en tache de fond : en attendant, l'original sert."""
        ident = HD.SHEET_ALIASES.get(ident, ident)
        orig = self._original_sheet(ident)
        if not orig or mode in (0, MODE_PP): return orig
        lookup_key = (ident, mode)
        if lookup_key in self.sprite_tex: return self.sprite_tex[lookup_key]
        fut = self.hd_jobs.get(lookup_key)
        if fut is None:
            _name, cid, algo = HD.MODES[mode]
            self.hd_jobs[lookup_key] = self.pool.submit(self._calc_hd, orig['arr'], orig['geo'], ident, cid, algo)
            return orig
        if not fut.done(): return orig
        del self.hd_jobs[lookup_key]
        try: atlas, cl, ch = fut.result()
        except Exception as ex:
            print(tr('lissage HD impossible (%s, h%d) : %s') % (HD.MODES[mode][0], ident, ex), flush=True); self.sprite_tex[lookup_key] = orig; return orig
        r = self.sprite_tex[lookup_key] = dict(t=self._tex(atlas, False, HD_LEVELS), tw=atlas.shape[1], th=atlas.shape[0], nl=orig['nl'], cols=orig['cols'], pw=orig['pw'], ph=orig['ph'], cl=cl, ch=ch, g=HD_GUTTER, hd=True)
        if not self.smoothing: self._filter_texture(r['t'], False)
        return r

    def _update_field(self, e):
        """(Re)construit la grille de tuiles quand le moteur en envoie une autre ; l'atlas est la texture Unity `field`."""
        ch = e.field; eng = e.world
        if eng is not None and self._field_view is not None:      # carte entiere lue dans le moteur : on dessine toute la zone visible (le moteur n'en envoie que 25 colonnes)
            cx, cz, dl, dh = self._field_view
            x0 = 4 * int(math.floor((cx - dl - 1) / 4)); x1 = x0 + 4 * int(math.ceil((2 * dl + 7) / 4))                  # bornes sur des multiples de 4 et largeur constante : le maillage garde la meme taille
            y0 = 4 * int(math.floor((cz - dh - 1) / 4)); y1 = y0 + 4 * int(math.ceil((2 * dh + 7) / 4))                  # a la marche et ses sommets sont remplaces sur place (pas de reallocation : pas d'a-coup)
            x0, x1 = max(x0, int(cx) - 120), min(x1, int(cx) + 120); y0, y1 = max(y0, int(cz) - 80), min(y1, int(cz) + 80)
            cols = x1 - x0
            t = eng['ids'][(np.arange(y0, y1) % eng['h'])[:, None], (np.arange(x0, x1) % eng['l'])[None, :]].astype(np.int32).ravel()
            ch = {'x0': x0, 'y0': y0, 'cols': cols}
        else:
            t = np.array(ch['tuiles'], np.int32)
        lookup_key = (ch['x0'], ch['y0'], ch['cols'], hash(t.tobytes()), self.mode == MODE_PP)
        if lookup_key == self.field_key: self._refresh_patterns(); return
        self.field_key = lookup_key
        if self.field_tex is None:
            arr = self.data.texture('field')
            if arr is None: return
            t4 = arr[:CH_ATLAS * 16, :CH_ATLAS * 16].reshape(CH_ATLAS, 16, CH_ATLAS, 16, 4).transpose(0, 2, 1, 3, 4)       # (ligne, colonne, y, x, canal) : une tuile de 16 x 16 par case
            t4 = np.pad(t4, ((0, 0), (0, 0), (CH_GUTTER, CH_GUTTER), (CH_GUTTER, CH_GUTTER), (0, 0)), mode='edge')
            self.field_tex = self._tex(np.ascontiguousarray(t4.transpose(0, 2, 1, 3, 4).reshape(CH_ATLAS * CH_CELL, CH_ATLAS * CH_CELL, 4)), False)      # atlas des tuiles, avec gouttieres
            self.field_tex_icon = self._tex(arr, False)                                                  # atlas d'origine : les icones de lieux y sont des rectangles quelconques
            self.field_nearest = None
        cols = ch['cols']; lines = len(t) // cols
        g = t[:lines * cols].reshape(lines, cols)
        self.field_g = g; self.field_pattern = CH_PATTERN_NUM[np.searchsorted(CH_PATTERN_END, g, side='right')]; self.field_acc_seen = tuple(self.acc_pattern)
        if self.field_base is None or self.field_base[0] != (cols, lines):        # sommets de la grille a l'origine (NO, NE, SE, SO, deux triangles par tuile), decales ensuite de (x0, y0)
            X, Z = np.meshgrid(np.arange(cols), np.arange(lines)); O = np.zeros_like(X)
            P = np.stack([np.stack([X, O, Z], -1), np.stack([X + 1, O, Z], -1), np.stack([X + 1, O, Z + 1], -1), np.stack([X, O, Z + 1], -1)], 2).astype(np.float32)   # (l, c, 4, 3)
            self.field_base = ((cols, lines), P[:, :, [0, 1, 2, 0, 2, 3], :].reshape(-1, 3))
        pos = (self.field_base[1] + np.array([ch['x0'], 0, ch['y0']], np.float32)).ravel(); uv = self._tile_uv(g + self.acc_pattern[self.field_pattern])
        n = len(pos) // 3
        if self.field_vl is not None and self.field_vl.count == n:                  # meme taille : remplacement sur place
            self.field_vl.position[:] = pos; self.field_vl.tex_coords[:] = uv
        else:
            if self.field_vl is not None: self.field_vl.delete()
            self.field_vl = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', pos), tex_coords=('f', uv.ravel()), colors=('f', np.ones(n * 4, np.float32)))

    def _tile_uv(self, g):
        """Coordonnees de texture (6 sommets par tuile, a plat) de la grille de numeros de tuile `g` ; les tuiles sont stockees tete en bas dans l'atlas."""
        aw = float(CH_ATLAS * CH_CELL)                                                  # atlas copie avec une gouttiere de CH_GUTTER pixels autour de chaque tuile
        u0 = ((g % CH_ATLAS) * CH_CELL + CH_GUTTER) / aw; v0 = ((g // CH_ATLAS) * CH_CELL + CH_GUTTER) / aw; d = 16.0 / aw
        U = np.stack([np.stack([u0, v0], -1), np.stack([u0 + d, v0], -1), np.stack([u0 + d, v0 + d], -1), np.stack([u0, v0 + d], -1)], 2).astype(np.float32)      # (l, c, 4, 2)
        return U[:, :, [0, 1, 2, 0, 2, 3], :].reshape(-1, 2).ravel()

    def _advance_patterns(self):
        """Une image du jeu sur la carte du monde (NativeManager.Update -> Field.UpdatePattern) : toutes les 17 images, le decalage de chaque motif avance d'un pas, puis retombe a 0 a sa limite."""
        self.pattern_n += 1
        if self.pattern_n < CH_PATTERN_PERIOD: return
        self.pattern_n = 0
        for i in range(1, len(CH_PATTERN_STEP)):
            v = int(self.acc_pattern[i]) + CH_PATTERN_STEP[i]
            self.acc_pattern[i] = v if v < CH_PATTERN_LIMIT[i] else 0

    def _refresh_patterns(self):
        """Met a jour sur place les coordonnees de texture des tuiles animees quand un motif a change de pas."""
        acc = tuple(self.acc_pattern)
        if acc == self.field_acc_seen or self.field_vl is None or self.field_pattern is None: return
        self.field_acc_seen = acc
        if self.field_pattern.any(): self.field_vl.tex_coords[:] = self._tile_uv(self.field_g + self.acc_pattern[self.field_pattern])

    def _paint_field(self, e):
        if self.field_vl is None or self.field_tex is None: return
        nearest = self.mode == MODE_PP or not self.smoothing          # pixel perfect (echelle entiere) ou lissage coupe (F3) : plus proche voisin ; sinon pixels nets aux frontieres adoucies (comme les sprites d'origine)
        if self.field_nearest != nearest:
            self.field_nearest = nearest
            for t in (self.field_tex, self.field_tex_icon):
                gl.glBindTexture(t.target, t.id)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST if nearest else gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST if nearest else gl.GL_LINEAR)
        sharp = 0.0 if nearest else 1.0
        tint = self._scenery_tint()                       # paquet 33 sur la carte du monde : Field.SetColor = couleur du materiau des tuiles (Custom/Field : texture x _Color) et de chaque symbole (alpha propre conserve)
        if tint is not None: self._set_tint(tint)
        self.prog['cutoff'] = 0.05; self.prog['net'] = sharp; self.prog['tsize'] = (float(CH_ATLAS * CH_CELL),) * 2
        self._paint(self.field_tex, self.field_vl)
        self.prog['tsize'] = (1024.0, 1024.0)
        q, uv, col = [], [], []
        for s in e.symbols.values():                     # icones de lieux : posees a plat (le heros se tient au milieu du bord bas)
            r = CH_ICONS.get(s['genre'])
            if r is None or not s['vis']: continue
            ox, bottom, w, h = r
            x0, z0 = (round(s['x']) if self.mode == MODE_PP else s['x']) / CH_PX, (round(s['y']) if self.mode == MODE_PP else s['y']) / CH_PX; x1, z1 = x0 + w / CH_PX, z0 + h / CH_PX       # a plat sur la carte, comme les tuiles (dessin vu de dessus)
            q += [(x0, 0.02, z0), (x1, 0.02, z0), (x1, 0.02, z1), (x0, 0.02, z0), (x1, 0.02, z1), (x0, 0.02, z1)]
            u0, u1, v1, v0 = ox / 1024.0, (ox + w) / 1024.0, 1 - (bottom - h) / 1024.0, 1 - bottom / 1024.0
            uv += [(u0, v0), (u1, v0), (u1, v1), (u0, v0), (u1, v1), (u0, v1)]       # tete en bas dans l'atlas, comme les tuiles : le haut de la carte = le bas de l'image
            col += [(1.0, 1.0, 1.0, float(s['alpha']))] * 6
        if q:
            n = len(q); pos = np.array(q, np.float32).ravel(); tc = np.array(uv, np.float32).ravel(); cc = np.array(col, np.float32).ravel()
            if self.field_icon is None or self.field_icon[0] != n:
                if self.field_icon is not None: self.field_icon[1].delete()
                self.field_icon = (n, self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', pos), tex_coords=('f', tc), colors=('f', cc)))
            else:
                v = self.field_icon[1]; v.position[:] = pos; v.tex_coords[:] = tc; v.colors[:] = cc
            self._linked_domain = None                                  # sommets ecrits apres le 1er trace de l'image : sans rebind + commit() ils partent avec l'image precedente (icones en retard d'une image, absentes une image quand leur nombre change)
            self._paint(self.field_tex_icon, self.field_icon[1])
        if tint is not None: self._set_tint((1.0, 1.0, 1.0))
        self.prog['net'] = 0.0

    def _paint(self, tex, vl):
        """Trace une vertex_list en ne liant le VAO et les tampons qu'une fois par image (beaucoup plus rapide que vl.draw)."""
        gl.glBindTexture(tex.target, tex.id)
        try:
            dom = vl.domain
            if dom is not self._linked_domain:
                dom.vao.bind()
                for buf, _ in dom.buffer_attributes: buf.commit()
                self._linked_domain = dom
            gl.glDrawArrays(gl.GL_TRIANGLES, vl.start, vl.count)
        except AttributeError:
            vl.draw(gl.GL_TRIANGLES)

    def _purge_outlines(self, src, guard=CD.KEPT_TEXTURES):
        """Les textures de decor de combat agrandies x4 (scenery_outlines.py, 5,6 Mo avec leurs mipmaps) ne sont gardees que pour les derniers decors vus : les plus anciennes rendent leur place sur la carte graphique."""
        while len(self._tex_outlines) > guard:
            for i, lookup_key in enumerate(self._tex_outlines):
                if lookup_key[0] != src: break
            else: return
            lookup_key = self._tex_outlines.pop(i); t = self.tex_gl.pop(lookup_key, None)
            if t is not None: t.delete()

    def _load_map(self, name_str):
        t_load = time.perf_counter()
        for vl in self.map_vl: vl[1].delete()
        for x in self.ext_map: x[1].delete()
        if self.ext_sky and self.ext_sky['vl'] is not None: self.ext_sky['vl'].delete()
        if self.flat_sky and self.flat_sky.get('vl') is not None: self.flat_sky['vl'].delete()
        self.ext_sky = None; self.zoom_sky = None; self.flat_sky = None; self.ext_map = []; self.map_vl = []; self.map_pos = {}; self.spans = {}; self.names = {}; self.objects = None; self.palettes = None; self.pam_gl = {}
        src = (os.environ.get('DQ_DECOR') or name_str) if name_str.startswith('btl_') else name_str       # DQ_DECOR : (test) force un autre decor de combat
        c = error = None
        for cand in [src] + (DO.fallback_sceneries(src) if name_str.startswith('btl') else []):         # decor de combat sans la variante demandee (heure) : la plus proche, plutot qu'un decor vide
            try: c = self.data.game_map(cand)
            except KeyError as ex: error = ex; continue
            except Exception as ex: error = ex
            if c is not None and cand != src: print(tr('decor %s absent des donnees : %s a la place') % (src, cand), flush=True); src = cand
            break
        if c is None:
            print(tr('carte non chargee :'), error, flush=True); self.map_name = name_str; return
        if not os.environ.get('DQ_SANS_DECALAGE'):
            try: DP.shift(c)                                               # massifs de fleurs & co : triangles plats superposes releves de 3 mm (plus de z-fighting, voir flat_sceneries.py)
            except Exception as ex: print('decors_plats :', ex, flush=True)
        self.map_src = src; self.scenery_arr = {k: v for k, v in c['textures'].items() if k in c['groupes']}       # textures du decor (agrandies selon le mode de F2, voir _decor_tex)
        self.objects = OC.MapObjects(c)                                   # portes, jarres, tonneaux... : positions affichees (variantes cachees au depart) ; eau, lampes... animees en continu
        self.palettes = OC.MapPalettes(c)                               # surfaces dont la texture change d'image en image (eau qui scintille, marais...)
        outlines = name_str.startswith('btl') and not os.environ.get('DQ_SANS_CONTOURS')        # decors de combat : silhouettes des arbres et montagnes adoucies (scenery_outlines.py) ; DQ_SANS_CONTOURS=1 : (test) texture d'origine
        for key, (pos, uv, col) in c['groupes'].items():
            if key not in c['textures']: continue
            if (src, key) not in self.tex_gl:
                arr = CD.for_scenery(c['textures'][key], key) if outlines else c['textures'][key]
                self.tex_gl[(src, key)] = t = self._tex(arr, True, 99); self._filter_texture(t, self.smoothing)
                if arr is not c['textures'][key]: self._tex_outlines.append((src, key)); self._purge_outlines(src)
            vl = self.prog.vertex_list(len(pos), gl.GL_TRIANGLES, position=('f', self.objects.cur[key].ravel()), tex_coords=('f', self.objects.uv(key).ravel()), colors=('f', self.objects.col(key).ravel()))
            self.map_vl.append((self.tex_gl[(src, key)], vl, key)); self.map_pos[key] = pos.copy()
        for key, dd in self.palettes.defs.items():                         # images de chaque animation de palette
            if key not in c['groupes']: continue
            self.pam_gl[key] = []
            for k, a in enumerate(dd['images']):
                if (src, key, k) not in self.tex_gl:
                    self.tex_gl[(src, key, k)] = t = self._tex(a, True, 99); self._filter_texture(t, self.smoothing)
                self.pam_gl[key].append(self.tex_gl[(src, key, k)])
        self.objects.dirty = set(); self.objects.dirty_uv = set(); self.objects.dirty_col = set()
        self.spans = c.get('plages', {}); self.names = c.get('noms', {})
        if name_str == 'ev01': self._title_sky(c, src)         # ecran-titre : ciel prolonge de part et d'autre de la zone portrait
        elif name_str in EXTENDED_SKIES: self._extended_sky(c, src, name_str)         # dpout, ev09 : plan de ciel prolonge par symetrie (MAP-05)
        allp = np.concatenate([g[0] for g in c['groupes'].values()]) if c['groupes'] else np.zeros((1, 3), np.float32)
        self.bounds_x = (float(np.percentile(allp[:, 0], 0.5)), float(np.percentile(allp[:, 0], 99.5)))
        self.map_name = name_str
        self.scenery_background = self._battle_background(c) if name_str.startswith('btl_') else None
        print(tr('carte %s : %d groupes') % (name_str, len(self.map_vl)), flush=True)
        SV.note('carte chargee', name_str=name_str, groups=len(self.map_vl), ms=round(1000 * (time.perf_counter() - t_load)))

    def _calc_hd_scenery(self, arrs, algo):
        """(tache de fond) textures de decor agrandies par l'algorithme HD du mode de F2 (x8, plafonne a 4096 px de cote). Le bord est repete en boucle avant l'agrandissement : les textures se raccordent."""
        out = {}
        for key, arr in arrs.items():
            h, w = arr.shape[:2]; passes = 3
            while passes > 0 and max(h, w) * 2 ** passes > 4096: passes -= 1
            if passes == 0: out[key] = arr; continue
            a = np.pad(arr, ((2, 2), (2, 2), (0, 0)), mode='wrap')
            r = algo(a) if passes == 3 else HD.upscale_epx(a, passes)
            f = r.shape[0] // a.shape[0]
            out[key] = np.ascontiguousarray(r[2 * f:r.shape[0] - 2 * f, 2 * f:r.shape[1] - 2 * f])
        return out

    def _hd_scenery(self):
        """Textures GL agrandies du decor courant pour le mode de F2 ; None tant que le calcul en tache de fond n'est pas fini (le decor d'origine sert en attendant)."""
        lookup_key = (self.map_src, self.mode); r = self.scenery_hd.get(lookup_key)
        if r is not None: return r
        jc = ('d',) + lookup_key; fut = self.hd_jobs.get(jc)
        if fut is None:
            self.hd_jobs[jc] = self.pool.submit(self._calc_hd_scenery, dict(self.scenery_arr), HD.MODES[self.mode][2]); return None
        if not fut.done(): return None
        del self.hd_jobs[jc]
        try: arrs = fut.result()
        except Exception as ex:
            print(tr('lissage HD du decor impossible (%s) : %s') % (self.map_src, ex), flush=True); arrs = {}
        r = self.scenery_hd[lookup_key] = {}
        for k, a in arrs.items():
            r[k] = t = self._tex(a, True, 99); self._filter_texture(t, self.smoothing)
        while len(self.scenery_hd) > 8:                                  # on ne garde que les derniers decors agrandis (memoire de la carte graphique)
            for t in self.scenery_hd.pop(next(iter(self.scenery_hd))).values(): t.delete()
        return r

    def _scenery_tint(self):
        """Teinte du paquet 33 a appliquer au decor (r, g, b), ou None si elle est neutre (rien ne change : le dessin reste identique). DQ_SANS_TEINTE=1 : (debogage) jamais de teinte, pour comparer."""
        if os.environ.get('DQ_SANS_TEINTE'): return None
        t = self.engine.state.tint
        return None if TC.neutral_tint(t) else t

    def _set_tint(self, t):
        """Ecrit le uniforme `tint` s'il a change (le programme est en cours d'utilisation)."""
        t = (float(t[0]), float(t[1]), float(t[2]))
        if t != self._gl_tint: self._gl_tint = t; self.prog['teinte'] = t

    @staticmethod
    def _scenery_culling(active):
        """Faces cachees du decor (#182) : les shaders du decor de carte du jeu (Custom/fld_normal, fld_atest, fld_trans, fld_transz et leurs variantes sepia) sont en « Cull Back » (lu dans le paquet de donnees :
        ShaderLab culling = 2) : un mur, un toit, un plafond n'a de texture que sur sa face avant ; vu de derriere (camera tournee, de l'exterieur d'une piece) il est invisible, d'ou la vue a travers les murs d'un interieur.
        Unity : face avant = triangle dans le sens horaire a l'ecran (main gauche), comme les modeles 3D (DQ_FBX_CULL) ; DQ_DECOR_CULL : 0 = sans culling (l'ancien rendu), 1 = defaut, 2 = sens inverse (essai)."""
        mode = os.environ.get('DQ_DECOR_CULL', '1')
        if active and mode != '0':
            gl.glEnable(gl.GL_CULL_FACE); gl.glCullFace(gl.GL_BACK); gl.glFrontFace(gl.GL_CCW if mode == '2' else gl.GL_CW)
        else: gl.glDisable(gl.GL_CULL_FACE); gl.glFrontFace(gl.GL_CCW)

    def _paint_scenery(self, sharp=False):
        """Decor de la ville ou du combat. Les textures du decor sont des peintures de 8 a 256 px etirees en 3D : en « Originaux » et en pixel perfect (reglages pour les SPRITES) il garde le rendu d'origine,
        lisse (mipmaps + anisotrope, F3 = agrandissement lineaire ou plus proche voisin) ; le mode agrandi (EPX) lui applique l'algorithme HD choisi."""
        r = self._hd_scenery() if self.mode not in (0, MODE_PP) else None
        sharp_o = 1.0 if (sharp and r is None and self.smoothing and not os.environ.get('DQ_DECOR_FLOU')) else 0.0           # villes et donjons en « Originaux » / pixel perfect : texels nets, seule la frontiere entre deux texels est adoucie (comme les sprites) ; en combat, peintures etirees : lissage normal
        is_tr = lambda k: isinstance(k, tuple) and k[0] == 'tr'
        opaque_ones = [x for x in self.map_vl if not is_tr(x[2])]
        transp = sorted((x for x in self.map_vl if is_tr(x[2])), key=lambda x: x[2][1])         # file de rendu 3000 + priorite (FldObject.set_priority)
        cutoff0 = self.prog['cutoff']; a2c = self.post.a2c
        sepia = bool(getattr(self.engine.state, 'sepia', False)) and not os.environ.get('DQ_SANS_SEPIA')          # paquet 1 : retour en arriere, decor en sepia (les personnages, bulles et menus gardent leurs couleurs)
        if sepia: self.prog['sepia'] = 1.0
        tint = self._scenery_tint(); ids_tz = self.tz.ids() if tint is not None else None; neutral = (1.0, 1.0, 1.0)      # paquet 33 : teinte de tout le decor, sauf les groupes dont la texture a « tz_ » dans son nom (lampes, bougies, vagues)
        if a2c: self.prog['a2c'] = 1.0; gl.glEnable(PF.SAMPLE_ALPHA_TO_COVERAGE); gl.glDisable(gl.GL_BLEND)      # decor opaque decoupe : alpha -> couverture MSAA, sans melange (le melange doublerait l'alpha)
        for step, entries in ((0, opaque_ones), (1, transp)):
            if step == 1 and entries:
                if a2c: self.prog['a2c'] = 0.0; gl.glDisable(PF.SAMPLE_ALPHA_TO_COVERAGE); gl.glEnable(gl.GL_BLEND)
                gl.glDepthMask(gl.GL_FALSE); gl.glDepthFunc(gl.GL_LEQUAL); self.prog['cutoff'] = 0.0      # Custom/fld_trans : Blend SrcAlpha OneMinusSrcAlpha, ZWrite Off, ZTest LEqual, pas de rejet
            gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
            sky_key = self.flat_sky['key'] if self.flat_sky is not None else (self.zoom_sky['key'] if self.zoom_sky is not None else None)          # (le ciel du titre a ses propres sommets : jamais de culling)
            for i, (tex, vl, key) in enumerate(entries):
                self._scenery_culling(key != sky_key)
                gl.glPolygonOffset(0.0, -SCENERY_BIAS * (i + (len(opaque_ones) if step else 0)))         # decors a plat superposes a la meme hauteur (deux massifs de fleurs, chemin et pelouse...) : sans cela leur profondeur est egale a l'arrondi pres et l'un ou l'autre gagne pixel par pixel, ce qui change a chaque mouvement de la camera (scintillement) ; le groupe dessine en dernier l'emporte, toujours
                pg = self.pam_gl.get(key)
                t = pg[self.palettes.image(key)] if pg else (r.get(key, tex) if r else tex)          # palette animee : image courante (sans agrandissement HD)
                self.prog['net'] = sharp_o if (r is None or key not in r) else 0.0
                self.prog['tsize'] = (float(t.width), float(t.height))
                if tint is not None: self._set_tint(neutral if TC.group_tz(key, ids_tz) else tint)
                zoom = CT.screen_zoom(self._town_aspect) if (self.zoom_sky is not None and key == self.zoom_sky['key'] and self._M_town is not None) else 1.0
                if zoom > 1.0 + 1e-6: self.prog['mvp'] = tuple(float(x) for x in CT.zoom_matrix(self._M_town, zoom).T.ravel())          # ciel du titre agrandi autour du centre de l'ecran (#130)
                if not (self.flat_sky is not None and key == self.flat_sky['key'] and self._paint_flat_sky(t)): self._paint(t, vl)
                if zoom > 1.0 + 1e-6: self.prog['mvp'] = tuple(float(x) for x in self._M_town.T.ravel())
            if step == 1 and entries: gl.glDepthMask(gl.GL_TRUE); gl.glDepthFunc(gl.GL_LESS); self.prog['cutoff'] = cutoff0
            gl.glDisable(gl.GL_POLYGON_OFFSET_FILL); self._scenery_culling(False)
            if step == 0:
                if tint is not None: self._set_tint(tint)
                for tex, vl, key, start_idx, n, dx in self.ext_map:
                    self.prog['net'] = sharp_o; self.prog['tsize'] = (float(tex.width), float(tex.height)); self._paint(tex, vl)
                if self.ext_sky is not None: self._paint_sky(r, sharp_o)
        if a2c: self.prog['a2c'] = 0.0; gl.glDisable(PF.SAMPLE_ALPHA_TO_COVERAGE); gl.glEnable(gl.GL_BLEND)
        if tint is not None: self._set_tint(neutral)
        if sepia: self.prog['sepia'] = 0.0
        self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0)

    def _fbx_ready(self, no):
        """Modele 3D numero `no` pret a etre dessine ({'m': fbx.FbxModel, 'vl', 'tex'...}), None tant qu'il se lit (tache de fond : le cache disque, ou le paquet de donnees la premiere fois) ou s'il n'est pas gere."""
        r = self.fbx_cache.get(no)
        if r is None:
            r = self.fbx_cache[no] = {'etat': 'lecture', 'm': None}
            def task():
                try: r['m'] = FX.FbxModel(self.data.fbx_model(no)); r['etat'] = 'lu'
                except Exception as ex: r['etat'] = 'erreur'; print(tr('Modele 3D %d non affiche : %s') % (no, ex), flush=True)
            threading.Thread(target=task, daemon=True).start()
        if r['etat'] == 'lu':                                       # objets OpenGL : dans le fil du dessin
            try:
                m = r['m']; nt = len(m.tri_indices)
                self.tex_gl[('fbx', no)] = r['tex'] = t = self._tex(m.tex, True, 99); self._filter_texture(t, self.smoothing)
                r['uv'] = m.uv[m.tri_indices.ravel()].ravel().astype(np.float32); r['n'] = nt * 3
                r['vl'] = self.prog.vertex_list(r['n'], gl.GL_TRIANGLES, position=('f', np.zeros(r['n'] * 3, np.float32)), tex_coords=('f', r['uv']), colors=('f', np.ones(r['n'] * 4, np.float32)))
                r['etat'] = 'pret'
            except Exception as ex: r['etat'] = 'erreur'; print(tr('Modele 3D %d non affiche : %s') % (no, ex), flush=True)
        return r if r['etat'] == 'pret' else None

    def _paint_fbx(self, e):
        """Modeles 3D de la scene (e.fbx) : pose = position / rotation / echelle du moteur (paquet 32), animation jouee depuis son lancement (images du moteur : 30 Hz, fraction de pas comprise), couleur = Material.color.
        Shader Custom/ImdChara : couleur du sommet x _Color x texture, fusion alpha, ZWrite, ZTest LEqual, Cull Back, file Geometry (avec le decor opaque, avant les personnages et les effets-maillages)."""
        tf = max(0.0, self.engine.frames - 2.0 + self.alpha)           # image du moteur affichee : celle du pas precedent + alpha (voir _interpoler)
        for k in [k for k in self.fbx_player if k not in e.fbx]: del self.fbx_player[k]
        for slot, mod in sorted(e.fbx.items()):
            if not mod['vis']: continue
            r = self._fbx_ready(mod['id'])
            if r is None: continue
            m = r['m']; lc = self.fbx_player.get(slot)
            if lc is None or lc['id'] != mod['id'] or lc['n'] > len(mod['anim']):
                lc = self.fbx_player[slot] = {'id': mod['id'], 'n': 0, 'a': FX.AnimPlayer({k: {'dur': c['dur'], 'wrap': c['wrap']} for k, c in m.clips.items()})}
            for img, seq, force in mod['anim'][lc['n']:]: lc['a'].play(seq, force, img)
            lc['n'] = len(mod['anim'])
            ui_scale = 0.4 if mod['id'] == 10 else 1.0                      # FbxObject.m_defScale (.ctor : 0,4 pour le modele 10, 1 sinon)
            sc = tuple(float(x) * ui_scale for x in mod['scl'])
            V = m.vertices(FX.object_matrix(mod['pos'], mod['rot'], sc), lc['a'].poses(tf))
            vl = r['vl']; vl.position[:] = V[m.tri_indices.ravel()].ravel(); vl.colors[:] = np.tile(np.array(mod['col'], np.float32), r['n'])
            self.prog['cutoff'] = 0.0; self.prog['net'] = 1.0 if self.smoothing else 0.0; self.prog['tsize'] = (float(m.tex.shape[1]), float(m.tex.shape[0]))
            self._linked_domain = None
            cull = os.environ.get('DQ_FBX_CULL', '1')                   # Custom/ImdChara : Cull Back (lu dans le shader) ; DQ_FBX_CULL=0 : sans culling, 2 : sens inverse (l'ancien, faux : on voyait l'interieur du dragon) pour comparer
            if cull != '0':
                gl.glEnable(gl.GL_CULL_FACE); gl.glCullFace(gl.GL_BACK)
                gl.glFrontFace(gl.GL_CCW if cull == '2' else gl.GL_CW)         # Unity : face avant = triangle dans le sens horaire a l'ecran (main gauche), l'inverse du defaut d'OpenGL ; sans cela on ne dessinait que les faces arrieres (l'interieur du dragon : visage vu de l'interieur, corps vu de dos)
            self._paint(r['tex'], vl)
            gl.glDisable(gl.GL_CULL_FACE); gl.glFrontFace(gl.GL_CCW)
        self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0); self.prog['cutoff'] = 0.05

    def _icon_tex(self, ident):
        """Texture de l'icone `ident` (case 32 x 32 de la feuille MenuTexture, numerotee de gauche a droite et de haut en bas ; Riseup.SetTexture -> UV 1/32) ; None si la feuille est absente."""
        if ident in self.icon_tex: return self.icon_tex[ident]
        if self._menu_tex is None:
            try:
                from PIL import Image
                self._menu_tex = np.array(Image.open(os.path.join(self.args.cache, 'ui_MenuTexture.png')).convert('RGBA'))
            except Exception: self._menu_tex = False
        t = None
        if self._menu_tex is not False:
            r, c = divmod(ident, 32); h = self._menu_tex.shape[0]
            if (r + 1) * 32 <= h: t = self._tex(HD._dilate(self._menu_tex[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32], 3), False)          # (couleur du bord sous les pixels transparents : pas de liseré clair au filtrage)
        self.icon_tex[ident] = t
        return t

    def _icons(self, e, field, is_battle, dh, cam3d=None):
        """Bulles d'icone au-dessus des personnages (paquets 19/20, Riseup : carre de 0,96 face a la camera, avance de 0,48 vers elle) : [(texture, vertex_list)]."""
        if field or is_battle or not e.icons or e.cam_pos is None or e.cam_target is None: return []
        fwd = np.array(e.cam_target, float) - np.array(e.cam_pos, float); fwd /= np.linalg.norm(fwd) or 1
        out = []; corr = self._edge_correction(); C_view = self._view_border[0] if self._view_border is not None else None
        for slot, ic in sorted(e.icons.items()):
            if ic['pos'] is None or ic['alpha'] < 0.02: continue
            tex = self._icon_tex(ic['id'])
            if not tex: continue
            if cam3d is not None:
                # de face a l'ecran, comme les personnages (rotation de la camera). Avance de 0,48 vers la camera de la VISIONNEUSE (et non de celle du jeu : tournee ou inclinee par le joueur, elle decalait la bulle a l'ecran),
                # le long du rayon de vue (voir _shift_depth) ; la bulle reste collee au personnage qui la porte, quelle que soit l'inclinaison de la camera (voir _anchor_icon)
                P = self._anchor_icon(e, np.array(ic['pos'], float), cam3d); r_, u_, f_ = cam3d; D = self._shift_depth
                A0, B0 = P - r_ * 0.48, P + r_ * 0.48
                a, b, c, d = D(A0, f_, 0.48, corr, C_view), D(B0, f_, 0.48, corr, C_view), D(B0 + u_ * 0.96, f_, 0.48, corr, C_view), D(A0 + u_ * 0.96, f_, 0.48, corr, C_view)
                q = np.array([a, b, c, a, c, d], np.float32).ravel().tolist()
            else:
                p = np.array(ic['pos'], float) - fwd * 0.48
                a, b, up = p - dh * 0.48, p + dh * 0.48, np.array([0.0, 0.96, 0.0])
                q = np.array([a, b, b + up, a, b + up, a + up], np.float32).ravel().tolist()
            uv = [0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1]; cl = [1.0, 1.0, 1.0, float(min(max(ic['alpha'], 0.0), 1.0))] * 6
            vl = self.icon_vl.get(slot)
            if vl is None: vl = self.icon_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            out.append((tex, vl))
        return out

    def _anchor_icon(self, e, P, cam3d):
        """Position d'une bulle d'icone (paquet 20) pour la camera de la visionneuse. Le moteur la pose au-dessus de la cible (1,294 au-dessus de ses pieds, mesure sur trois villageois) en coordonnees du MONDE, alors que
        les personnages sont des panneaux de face a la camera : si la camera du joueur est inclinee ou tournee, la hauteur de la bulle par rapport a la tete change (1,294 x cos de l'inclinaison a l'ecran, contre une hauteur
        de panneau fixe) et elle semble trop haute ou trop basse. Quand un personnage est sous la bulle (meme x, z), on garde donc l'ecart tel que la camera DU JEU le voit (composantes droite / haut / avant) et on le
        rapporte au repere de la camera de la visionneuse : la bulle reste a la meme place par rapport a la tete (identique a P quand les deux cameras sont les memes). Sans personnage dessous (tonneau, jarre...) : P, ancre dans le monde."""
        S = None; best = 0.35
        for sp in e.sprites.values():
            pos = sp.get('pos')
            if pos is None or len(pos) < 3 or not sp.get('vis', True): continue
            dx, dz, dy = P[0] - pos[0], P[2] - pos[2], P[1] - pos[1]
            if 0.3 < dy < 3.0 and math.hypot(dx, dz) < best: best = math.hypot(dx, dz); S = np.array(pos, float)
        if S is None: return P
        try: _, Dr, H, F = self._game_border(e)
        except Exception: return P
        d = P - S
        return S + cam3d[0] * float(d @ Dr) + cam3d[1] * float(d @ H) + cam3d[2] * float(d @ F)

    def _map_ports(self):
        """Fenetres de la carte ouverte (FieldImageMap) : {25: plan fixe, 26: grande carte qui se complete, 24: liste des boutiques de la ville, 22: bouton retour} -> port ; vide si aucune carte n'est ouverte."""
        r = {}; hidden_windows = {}
        for p, f in self.engine.ui.f.items():
            if p >= 12 and f.get('type') in (22, 23, 24, 25, 26):
                t = 22 if f['type'] == 23 else f['type']
                if f.get('vis'): r[t] = p
                elif f.get('act'): hidden_windows[t] = p                       # fenetre creee mais pas montree (la 2e vue de la carte, avant qu'on y passe)
        if r:
            for t, p in hidden_windows.items(): r.setdefault(t, p)
        return r                                                      # (des fenetres de carte restees creees apres la fermeture ne comptent pas : sans fenetre visible, la carte est fermee)

    def _plan_window(self, wnd, f):
        """Fenetre de carte du moteur (type 25) : texture du plan nommee par le moteur et marqueur de position (coordonnees en pixels de la texture de 256 x 192)."""
        name_str = f['cases'].get((0, 0))
        if name_str and wnd.map_name != name_str:
            wnd.map_name = name_str
        lic = f.get('listes') or {}                                 # lieux decouverts (code 3 : x + 256 y, un par nombre) et voile des blocs non explores (code 5) envoyes par le moteur
        wnd.symbols = [(v & 0xff, v >> 8 & 0xff) for v in lic.get(3, ())]
        if wnd.symbols and getattr(wnd, 't_blink', None) is None: wnd.t_blink = time.monotonic()
        v4 = f['indic'].get(4); wnd.special = None if v4 is None else (v4 & 0xff, v4 >> 8 & 0xff)        # code 4 : lieu special (croix rouge), meme codage que les lieux : x + 256 y
        lookup_key = tuple(lic[5][:16]) if lic.get(5) else None
        if wnd.map_name and (wnd.game_map is None or getattr(wnd, '_key_tex', None) != (wnd.map_name, lookup_key)):
            wnd._key_tex = (wnd.map_name, lookup_key)
            hd_a = self.plans.get(wnd.map_name)                    # plan agrandi (1024 x 768) : Lanczos, avec arrondi des contours (EPX) pour le plan du monde dont les terres sont en pixel art
            if hd_a is None:
                try:
                    a = self.data.texture(wnd.map_name)
                    if a is not None: hd_a = self.plans[wnd.map_name] = HD.upscale_plan(a, epx=wnd.map_name.startswith('dsdq4w'))
                except Exception as ex: print(tr('Plan %s illisible : %r') % (wnd.map_name, ex), flush=True)
            if hd_a is not None:
                if lookup_key:                                            # carte du monde : voile (silhouette grisee) sur les blocs de 10 x 10 pixels non explores (16 x 16 blocs a partir de x = 48, y = 16 du plan de 256 x 192)
                    src = self.data.world_veil()
                    if src is not None: hd_a = HD.veil_plan(hd_a, src, lookup_key)
                t = pyglet.image.ImageData(hd_a.shape[1], hd_a.shape[0], 'RGBA', np.ascontiguousarray(hd_a[::-1]).tobytes(), pitch=hd_a.shape[1] * 4).get_texture()
                gl.glBindTexture(t.target, t.id)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
                if wnd.game_map is not None: wnd.game_map.delete()
                wnd.game_map = t; wnd.map_mode = 0
        node = next((o for o in wnd.N.values() if o['mats'] and o['mats'][0].get('part') == 3), None)      # marqueur « vous etes ici » (icone de 24 x 24, partie 3 ; son numero change d'une generation de la mise en page a l'autre) centre sur le point (x, y) du plan
        mx, my = f['indic'].get(1), f['indic'].get(2)
        if node is not None and mx is not None and my is not None:
            node['pos'][0] = -223.0 + mx * 1.740234; node['pos'][2] = 398.0 - my * 1.740234; node['act'] = True        # AddIcon(Vector3.zero, 31, bInBounds) : le coin bas gauche de l'icone (la pointe de la plume) est sur la position, dans le plan de 450 x 337,5 pose en (2, -2) a l'echelle 0,99 (0,99 x 450 / 256)

    def _world_plan_window(self, wnd, f):
        """Grande carte du monde (type 26, Make_WorldLargeMap) : le moteur envoie le drapeau des pieces du plan (indicateur 0), puis la position du joueur x, y (indicateurs 1 et 2) en pixels d'un plan de
        1024 x 1024. Le jeu compose le plan (LoadLargeWorldMap : fond + pieces dont le bit est leve dans le drapeau) et n'en montre qu'une fenetre de 256 x 192 pixels centree sur le joueur
        (decalage de texture x / 1024 - 0,125 ; le marqueur reste au centre de la fenetre)."""
        flag = f['indic'].get(0, 0) & 0xffff; x, y = f['indic'].get(1), f['indic'].get(2)
        if getattr(wnd, '_plane_flag', None) != flag or wnd.game_map is None:
            try: pl = self.data.world_plan()
            except Exception as ex: pl = None; print(tr('Plan du monde illisible : %r') % (ex,), flush=True)
            if pl is None: return
            im = pl['base'].copy()
            for bit, px, py, a in pl['pieces']:
                if flag >> bit & 1: im[py:py + a.shape[0], px:px + a.shape[1]] = a
            rgba = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
            if wnd.game_map is not None: wnd.game_map.delete()
            t = pyglet.image.ImageData(1024, 1024, 'RGBA', np.ascontiguousarray(rgba[::-1]).tobytes(), pitch=4096).get_texture()
            gl.glBindTexture(t.target, t.id)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
            wnd.game_map = t; wnd._plane_flag = flag; wnd.map_mode = 3
        if x is not None and y is not None:
            wnd.map_uv = ((x - 128) / 1024.0, 1.0 - (y + 96) / 1024.0, (x + 128) / 1024.0, 1.0 - (y - 96) / 1024.0)

    def _map_objects(self):
        """Ordres du moteur sur les objets de la carte (portes, jarres...), puis une image d'animation ; les sommets modifies sont renvoyes a la carte graphique."""
        e = self.engine.state; cmds, e.object_cmds = e.object_cmds, []
        for c in cmds:
            if c[0] == 'carte':
                if self.objects is not None and self.map_name == e.game_map: self.objects.reinit()
                continue
            if self.objects is None: continue
            if self.map_name != e.game_map and e.part != ENGINE.PART_FIELD and e.game_map: self._load_map(e.game_map)       # la carte est chargee avant ses ordres
            if c[0] == 'anim': self.objects.common_anim(c[1], c[2])
            elif c[0] == 'onoff': self.objects.on_off(c[1], c[2])
            elif c[0] == 'alpha': self.objects.alpha(c[1], c[2])
            elif c[0] == 'pos': self.objects.position(c[1], c[2])
            elif c[0] == 'rot': self.objects.rotation(c[1], c[2])
        if self.objects is None: return
        if os.environ.get('DQ_ANIM_TEST') and self.map_name == os.environ.get('DQ_CARTE_TEST', ';').split(';')[0]:   # (test) DQ_ANIM_TEST="objet:numero:image" : lance une animation commune a cette image de boucle
            o_t, no_t, n_t = (int(v) for v in os.environ['DQ_ANIM_TEST'].split(':'))
            if self.n == n_t: self.objects.common_anim(o_t, no_t)
        dirty_keys = self.objects.tick()
        if self.palettes is not None: self.palettes.tick()
        dirty_uv_keys, dirty_col_keys = self.objects.dirty_uv, self.objects.dirty_col; self.objects.dirty_uv = set(); self.objects.dirty_col = set()
        for tex, vl, key, start_idx, n, dx in self.ext_map:
            if key in dirty_keys: vl.position[:] = CT.cloned_positions(self.objects.cur[key][start_idx:start_idx + n], dx).ravel()
        for tex, vl, key in self.map_vl:
            if key in dirty_keys: vl.position[:] = self.objects.cur[key].ravel()
            if key in dirty_uv_keys: vl.tex_coords[:] = self.objects.uv(key).ravel()
            if key in dirty_col_keys: vl.colors[:] = self.objects.col(key).ravel()

    def _orient_scenery(self, cam3d):
        """Panneaux de decor tournes vers la camera ; les sommets modifies sont renvoyes a la carte graphique seulement si l'orientation a change."""
        fw = cam3d[2]
        if not self.objects.orient(math.atan2(fw[0], fw[2]), cam3d, 0.0): return
        dirty_keys, self.objects.dirty = self.objects.dirty, set()
        for tex, vl, key in self.map_vl:
            if key in dirty_keys: vl.position[:] = self.objects.cur[key].ravel()

    def _anim_duration(self, idx, no):
        return self.objects.duration(idx, no) if self.objects is not None else None

    # ---- boucle
    def _held(self, action):
        """Une des touches de l'action (menu Touches) est-elle enfoncee ? (Une touche avalee par un raccourci, Entree de Alt + Entree, ne compte pas jusqu'a son relachement.)"""
        k = self.key_list; av = self.swallowed
        return any(k[c] and c not in av for c in self.reg.codes(action))

    def _terrain_free(self):
        """Terrain sans fenetre : ni menu d'Echap, ni message, ni menu ou carte du jeu, ni combat, ni effet d'ecran. Les fleches gauche / droite tournent alors la camera du jeu (D-233, D-234) ; haut / bas ne font rien ; sinon elles naviguent dans les fenetres."""
        eng = self.engine; e = eng.state
        return (not self.pause.opened and self.title_screen is None and e.part in (ENGINE.PART_TOWN, ENGINE.PART_FIELD) and not eng.msg_visible and eng.active_menu() is None and not self.map_open and e.effect is None and getattr(e, 'screen_effect', None) is None)

    # ombre des personnages : Chara.s_shadowMesh (carre +-1 en XZ, Y = 0,00625), echelle s_shadowDefScale (0,347 ; 10 ; 0,206), texture CharaTex/common (32 x 32 : ellipse noire d'alpha 96 / 255, filtre point),
    # shader Custom/CharaShadow (SrcAlpha / OneMinusSrcAlpha, ZWrite Off, ZTest LEqual, file 2999 = avant les personnages), position Chara.SetShadowPosition = pos + rotation du panneau x (0 ; 0 ; 0,25)
    # (donc decalee de 0,25 le long du rayon de la camera : meme point a l'ecran, mais devant le sol), orientation Euler(0, lacet de la camera, 0) = a plat.
    SHADOW_HALF_SIZE = (0.347, 0.206); SHADOW_HEIGHT = 0.0625; SHADOW_OFFSET = 0.25

    def _draw_character_shadows(self, shadows, cam3d):
        if getattr(self, '_shadow_tex', None) is None: self._create_shadow_tex()
        if not self._shadow_tex: return
        r_, u_, f_ = cam3d
        rh = np.array([r_[0], 0.0, r_[2]]); rh /= np.linalg.norm(rh) or 1                 # lacet seul de la camera
        fh = np.array([f_[0], 0.0, f_[2]]); fh /= np.linalg.norm(fh) or 1
        ex, ez = self.SHADOW_HALF_SIZE
        gl.glDepthMask(gl.GL_FALSE); gl.glDepthFunc(gl.GL_LEQUAL)
        self.prog['cutoff'] = 0.0; self.prog['net'] = 0.0; self.prog['tsize'] = (64.0, 64.0)
        for slot, p, alpha in shadows:
            c = p - f_ * self.SHADOW_OFFSET + np.array([0.0, self.SHADOW_HEIGHT, 0.0])
            P = [c - rh * ex - fh * ez, c + rh * ex - fh * ez, c + rh * ex + fh * ez, c - rh * ex + fh * ez]
            q = np.array([P[0], P[1], P[2], P[0], P[2], P[3]], np.float32).ravel().tolist()
            uv = [0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1]; cl = [1.0, 1.0, 1.0, min(1.0, alpha)] * 6          # _Color.a = SetShadowAlpha (1 par defaut), x alpha du personnage (SetColorWithShadow)
            vl = self._shadow_vl.get(slot)
            if vl is None: vl = self._shadow_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            self._paint(self._shadow_tex, vl)
        gl.glDepthMask(gl.GL_TRUE); gl.glDepthFunc(gl.GL_LESS); self.prog['cutoff'] = 0.05        # (les personnages qui suivent rejettent les pixels transparents : sinon leur panneau entier ecrit la profondeur et masque le compagnon derriere)

    # ombre des personnages sur la carte du monde : Chara.SetFieldMode redimensionne le maillage d'ombre a s_shadowDefScale x 28,8 (ellipse de demi-axes 10 x 5,9 pixels de la carte) et l'incline de 36 degres comme le personnage
    # (projetee : 5,9 x cos 36 = 4,8) ; Chara.SetFieldPosition la pose au meme point que le personnage (ses pieds). Le moteur masque celle des bateaux (paquet 15).
    SHADOW_FIELD = (9.99, 5.93 * math.cos(math.radians(36.0)))

    def _draw_field_shadows(self, shadows, ui_scale):
        if getattr(self, '_shadow_tex', None) is None: self._create_shadow_tex()
        gl.glDepthMask(gl.GL_FALSE); gl.glDepthFunc(gl.GL_LEQUAL)
        self.prog['cutoff'] = 0.0; self.prog['net'] = 0.0; self.prog['tsize'] = (64.0, 64.0)
        rx, rz = self.SHADOW_FIELD[0] * ui_scale / CH_PX, self.SHADOW_FIELD[1] * ui_scale / CH_PX
        for slot, p, alpha in shadows:
            x, y, z = float(p[0]), 0.03, float(p[2])
            q = [x - rx, y, z - rz, x + rx, y, z - rz, x + rx, y, z + rz, x - rx, y, z - rz, x + rx, y, z + rz, x - rx, y, z + rz]
            uv = [0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1]; cl = [1.0, 1.0, 1.0, min(1.0, alpha)] * 6
            vl = self._shadow_vl.get(slot)
            if vl is None: vl = self._shadow_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            self._paint(self._shadow_tex, vl)
        gl.glDepthMask(gl.GL_TRUE); gl.glDepthFunc(gl.GL_LESS); self.prog['cutoff'] = 0.05

    def _create_shadow_tex(self):
        # texture CharaTex/common : ellipse d'alpha 96 / 255 aux bords nets (filtre point) ; ici le meme maximum et la meme taille, mais le bord est adouci (ombres « trop brutes »)
        n = 64; yy, xx = np.mgrid[0:n, 0:n]; r = np.hypot((xx + 0.5 - n / 2) / (n / 2), (yy + 0.5 - n / 2) / (n / 2)); k = np.clip((r - 0.45) / 0.55, 0.0, 1.0)
        a = np.zeros((n, n, 4), np.uint8); a[..., 3] = np.round(96 * (1.0 - k * k * (3 - 2 * k))).astype(np.uint8)
        t = self._tex(a, False)
        gl.glBindTexture(t.target, t.id); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        self._shadow_tex = t; self._shadow_vl = {}
