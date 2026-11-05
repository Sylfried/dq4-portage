"""Combat : monstres, fond, effets, degats, vitesse et pas du moteur pendant un combat."""
import math, os, time
import numpy as np
import pyglet
from pyglet import gl
from dq4_pc.language import tr
from dq4_pc.battle import full_screen_effects as EPE
from dq4_pc.battle import battle_speed as VC
from dq4_pc.menus import pre_game as AP
from dq4_pc.world import hd as HD
from dq4_pc.core import engine as ENGINE
from dq4_pc.persistence import settings as RG
from dq4_pc.window.constants import TITLE_MAP, CB_CAP, CB_MSG_BOTTOM, HD_LEVELS, MODE_PP, ENGINE_STEP
from dq4_pc.window.shaders import BLUR_EFFECT
from dq4_pc.window.helpers import rot_unity, without_validation


class BattleMixin:
    """Combat : monstres, fond, effets, degats, vitesse et pas du moteur pendant un combat."""

    def set_battle_speed(self, v):
        """Page Texte du menu Echap : nouvelle « Vitesse de combat » (prise en compte tout de suite, aussi en plein combat)."""
        self.reg['vitesse_combat'] = RG.battle_notch(v); self.apply_scroll()

    battle_anchor = None                                                # rattachement du bouton de vitesse de combat (voir _anchor_battle_speed et hud_mobile.Buttons.ancre)

    def _anchor_battle_speed(self, entries, msg, dz, s, cx, ref_frame, tf_msg):
        """Bouton de vitesse de combat : il se rattache au coin inferieur GAUCHE de la boite du bas (commandes, ou message), comme « Fuir » l'est au coin inferieur droit des commandes. Seules comptent la fenetre de message
        et les fenetres de commandes (RG.BATTLE_COMMAND_WINDOWS) : parmi elles, celle dont le cadre descend le plus bas ; les autres (bandeau de l'equipe en haut, noms des monstres au milieu) n'ont rien a voir avec le bas de
        l'ecran (#47 : le bouton sautait sous elles pendant une image entre deux boites). La plaque a la taille de la plaque « Fuir » (le rectangle accroche sous le cadre, a son bord droit) quand on la trouve, sinon la derniere connue.
        Aucune boite visible (entre deux boites) : l'ancre reste ou elle etait ; toute premiere image du combat (aucune ancre encore) : la boite des messages a sa place d'avance (le bouton n'apparait jamais a la position
        par defaut de la grille, a gauche de l'ecran). -> self.battle_anchor = dict(x, y, w, h) en pixels (x : bord gauche du cadre, y : bord bas du cadre)."""
        if self.engine.state.part != ENGINE.PART_BATTLE: self.battle_anchor = None; return
        cands = []
        def message_box(dzm, tf):
            c = self.ui_msg.N.get('cadre')
            if c and c['vtx']: cands.append((tf[1] + (min(c['pos'][2] + v[1] for v in c['vtx']) + dzm) * tf[2], tf[0] + min(c['pos'][0] + v[0] for v in c['vtx']) * tf[2], None))      # (tf : repere sans le decalage dzm du message)
        if msg and self.ui_msg is not None: message_box(dz, tf_msg or (cx, ref_frame('msg')[0], s))
        for _, p in entries:
            wnd = self.ui_g.f[p]
            if p in self.ui_followers or self._hidden(wnd.typ) or self._type_name(wnd.typ) not in RG.BATTLE_COMMAND_WINDOWS: continue
            rs = wnd.rects(); tf = self.ui_tf.get(p)
            if not rs or tf is None: continue
            border_part = max(rs, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))                          # le cadre de la fenetre : le plus grand rectangle
            flee = [r for r in rs if r is not border_part and r[3] <= border_part[1] + 2.0 and r[2] >= border_part[2] - 12.0]          # plaque accrochee sous le cadre, a son bord droit
            d = (min((r[2] - r[0]) * tf[2] for r in flee), min((r[3] - r[1]) * tf[2] for r in flee)) if flee else None
            cands.append((tf[1] + border_part[1] * tf[2], tf[0] + border_part[0] * tf[2], d))
        if not cands and self.battle_anchor is None and self.ui_msg is not None:
            ov = self.reg['interface_fenetres'].get('msg'); message_box(CB_MSG_BOTTOM - self.ui_msg.bottom(), self._ui_custom('bas', s, ov) if ov else (cx, ref_frame('msg')[0], s))
        if not cands: return
        bottom, left, d = min(cands, key=lambda c: c[0])
        d = d or (self.battle_anchor and self.battle_anchor.get('w') and (self.battle_anchor['w'], self.battle_anchor['h'])) or None
        self.battle_anchor = dict(x=left, y=bottom, w=d[0] if d else None, h=d[1] if d else None)

    def _anchor_effects(self, e):
        """Effets-maillages de la ville (paquets 21 / 22) : le moteur pose l'effet sur le rayon de SA camera, entre elle et le personnage (sort Morph, eclaboussure de la grenouille : a mi-chemin exactement,
        mesure sur le paquet 22). Il n'a pas de personnage dans le paquet : on le retrouve, c'est celui qui est sur ce rayon. Pour chaque effet on garde de quoi le replacer sur le meme personnage vu par la camera
        de la visionneuse (zoom, centrage, rotation, inclinaison) : rapport des profondeurs et ecart angulaire (en tangentes) vu de la camera du jeu. Sans personnage sur le rayon : position telle quelle."""
        anc = {}
        if e.part == ENGINE.PART_TOWN and e.meshes_seen and e.cam_pos is not None and e.cam_target is not None and e.sprites:
            C = np.array(e.cam_pos, float); Co, Dr, H, F = self._game_border(e)
            for slot in e.meshes_seen:
                mm = e.meshes.get(slot)
                if mm is None: continue
                P = np.array(mm['pos'], float); d = P - C; best = None
                for k, sp in e.sprites.items():
                    if sp.get('pos') is None or len(sp['pos']) < 3: continue
                    S = np.array(sp['pos'], float); v = S - C; n2 = float(v @ v)
                    if n2 < 1e-6: continue
                    t = float(d @ v) / n2
                    if not 0.05 < t < 1.5: continue
                    spacing = float(np.linalg.norm(d - t * v))
                    if spacing < 0.05 and (best is None or spacing < best[0]): best = (spacing, k, S)
                if best is None: continue
                _, k, S = best
                vs, vp = S - Co, P - Co; zs, zp = float(vs @ F), float(vp @ F)
                if zs < 1.0 or zp < 0.5: continue
                anc[slot] = (k, zp / zs, float(vp @ Dr) / zp - float(vs @ Dr) / zs, float(vp @ H) / zp - float(vs @ H) / zs)
        self.anchor_effect = anc

    def _effect_pos(self, e, slot, pos):
        """Position d'un effet-maillage de la ville vue par la camera de la visionneuse : sur le meme personnage, au meme rapport de profondeur et au meme ecart angulaire que pour la camera du jeu
        (identique a `pos` quand les deux cameras sont les memes)."""
        a = self.anchor_effect.get(slot); sp = e.sprites.get(a[0]) if a else None
        if a is None or sp is None or sp.get('pos') is None or self._view_border is None: return pos
        C, Dr, H, F = self._view_border
        v = np.array(sp['pos'], float) - C; zs = float(v @ F)
        if zs < 1.0: return pos
        zp = zs * a[1]
        return tuple(C + Dr * ((float(v @ Dr) / zs + a[2]) * zp) + H * ((float(v @ H) / zs + a[3]) * zp) + F * zp)

    def _calc_hd_monster(self, arr, mid, cid, algo):
        """(tache de fond) texture HD d'un monstre, lue dans le cache disque s'il existe. Plafonnee a 4096 px de cote (moins de passes si besoin)."""
        f = os.path.join(self.args.cache, 'hd_%s_v%d_m%d.npy' % (cid, HD.VERSION, mid))
        try:
            if os.path.exists(f): return np.load(f)
        except Exception: pass
        h, w = arr.shape[:2]; passes = 3
        while passes > 0 and max(h, w) * 2 ** passes > 4096: passes -= 1
        if passes == 0: return arr
        a = algo(arr) if passes == 3 else HD.upscale_epx(arr, passes)
        try: np.save(f, a)
        except Exception: pass
        return a

    def _monster_texture(self, mid):
        """Texture d'un monstre pour le mode de sprites choisi (F2) : celle d'origine (pixels nets) ou agrandie par l'algorithme HD (calcul en tache de fond, l'original sert en attendant)."""
        orig = self.cb_tex.get((mid, 0))
        if orig is None:
            try: arr = self.data.texture('m%03d' % mid)
            except Exception as ex:
                print(tr('texture de monstre introuvable :'), mid, ex, flush=True); arr = None
            else:
                if arr is None: print(tr('texture de monstre absente des donnees :'), mid, flush=True)          # 25 numeros n'ont pas de texture m<id> (#225, audit CMB-03)
            if arr is None: arr = np.zeros((16, 16, 4), np.uint8)               # monstre non dessine (texture transparente) plutot qu'un arret du jeu
            t = self._tex(arr, False, 0)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            orig = self.cb_tex[(mid, 0)] = dict(t=t, tw=arr.shape[1], th=arr.shape[0], hd=False, arr=arr)
        if self.mode in (0, MODE_PP): return orig
        lookup_key = (mid, self.mode); jc = ('m',) + lookup_key
        if lookup_key in self.cb_tex: return self.cb_tex[lookup_key]
        fut = self.hd_jobs.get(jc)
        if fut is None:
            _name, cid, algo = HD.MODES[self.mode]
            self.hd_jobs[jc] = self.pool.submit(self._calc_hd_monster, orig['arr'], mid, cid, algo)
            return orig
        if not fut.done(): return orig
        del self.hd_jobs[jc]
        try: a = fut.result()
        except Exception as ex:
            print(tr('lissage HD impossible (monstre %d) : %s') % (mid, ex), flush=True); self.cb_tex[lookup_key] = orig; return orig
        self.cb_tex[lookup_key] = dict(t=self._tex(a, False, HD_LEVELS), tw=a.shape[1], th=a.shape[0], hd=a is not orig['arr'])
        if not self.smoothing: self._filter_texture(self.cb_tex[lookup_key]['t'], False)
        return self.cb_tex[lookup_key]

    def _battle_meshes(self, e, R=None, town=False):
        """Liste (texture, vertex_list, ...) des maillages de monstres de l'image courante, dans l'ordre de dessin d'Unity :
        shaders DssaMonster* = fusion alpha, pas d'ecriture de profondeur, pas de masquage des faces -> parties dessinees dans l'ordre des paquets ;
        entre monstres : file de rendu du shader (Transparent+150, +200...) puis du plus loin au plus proche."""
        out = []
        if R is None: R = self._rot_camera(e)
        Rb = R @ rot_unity(0.0, 180.0, 0.0)            # MeshChara.SetBillboard : rotation de la camera x SceneCamera.s_yReverse (Euler(0, 180, 0))
        cam = np.array(e.cam_pos, float); fw = R @ np.array([0.0, 0.0, 1.0])
        for slot, mm in sorted(e.meshes.items()):
            if slot not in e.meshes_seen: continue                # mode immediat : pas de paquet cette image = pas dessine
            mid = e.models.get(slot)
            if mid is None: continue
            credits = town and mid == 8905 and self.map_name == 'ev01'          # ecran-titre : les textes des credits (Yuji Horii...), avant le logo ; poses par le moteur, sans correction (1 pour 1 avec le mobile)
            if credits and os.environ.get('DQ_SANS_CREDITS'): continue            # (test) sans les credits : la difference avec la capture normale donne leur position exacte
            st = e.mesh_state.get(slot) or {'shader': 1, 'vis': True, 'col': (1.0, 1.0, 1.0), 'off': (0.0, 0.0)}
            if not st['vis']: continue
            ft = self._monster_texture(mid); t, tw, th = ft['t'], ft['tw'], ft['th']
            V = np.array(mm['v'], np.float32); ix = np.array(mm['idx'], np.int64)
            if self.cb_order and len(ix) % 6 == 0: ix = ix.reshape(-1, 6)[::-1].ravel()          # (essai) quadrilateres en ordre inverse
            P = V[ix]
            loc = P[:, 2:5]
            if not town: loc = EPE.widen(loc, mid, self.width / max(1, self.height))          # effet a quad plein ecran (35) : etire a la largeur de l'ecran 16/9 (CMB-02)
            if town and mid in AP.LOGO_MODELS and self.map_name == TITLE_MAP: loc = self._upscale_title_logo(loc, mm['pos'], Rb)          # ecran-titre : logo et sous-titre deux fois plus grands (ecart voulu, issue #108)
            xyz = (loc @ Rb.T.astype(np.float32)) * np.array([-1 if self.cb_mx else 1, 1, 1], np.float32) + np.array(self._effect_pos(e, slot, mm['pos']) if town else mm['pos'], np.float32)
            uv = np.c_[P[:, 0] + st['off'][0], 1.0 + P[:, 1] + st['off'][1]].astype(np.float32)
            cq = np.array(mm.get('col') or [255], np.float32) / 255.0   # un octet par quad = opacite de la partie (ombres, apparitions en fondu, clignotements)
            alpha = cq[np.minimum(ix // 4, len(cq) - 1)]
            clr = np.c_[np.ones((len(ix), 3), np.float32) * np.array(st['col'], np.float32), alpha].astype(np.float32)           # Material.color (paquet 25) x couleur de sommet
            n = len(xyz)
            vl = self.cb_vl.get(slot)
            if vl is None or vl[0] < n:                                  # capacite FIXE : recreer une liste quand le nombre de sommets change corrompt les autres monstres (glitchs/clignotements)
                if vl is not None: vl[1].delete()
                cap = max(CB_CAP, n)
                vl = self.cb_vl[slot] = (cap, self.prog.vertex_list(cap, gl.GL_TRIANGLES, position=('f', np.zeros(cap * 3, np.float32)), tex_coords=('f', np.zeros(cap * 2, np.float32)), colors=('f', np.zeros(cap * 4, np.float32))))
            cap = vl[0]
            pp = np.zeros((cap, 3), np.float32); pp[:n] = xyz                  # sommets inutilises : triangles degeneres (au point 0), jamais dessines
            pu = np.zeros((cap, 2), np.float32); pu[:n] = uv
            pc = np.zeros((cap, 4), np.float32); pc[:n] = clr
            vl[1].position[:] = pp.ravel(); vl[1].tex_coords[:] = pu.ravel(); vl[1].colors[:] = pc.ravel()
            queue = {0: 2100, 1: 2150, 2: 2200, 3: 3850}.get(st['shader'], 2150)       # file de rendu des shaders Custom/DssaChara, DssaMonster0, DssaMonster1, DssaCharaTransparent
            center_pos = (xyz.min(0) + xyz.max(0)) / 2
            out.append(((queue, -float((center_pos - cam) @ fw)), t, tw, th, vl[1], st['shader'], ft['hd']))
        out.sort(key=lambda o: o[0])
        return [o[1:] for o in out]

    def _battle_background(self, c):
        """Le moteur n'envoie pas de couleur de fond en combat, et le decor laisse un vide entre le bord du sol et le ciel :
        on prend la couleur moyenne (texture x couleur de sommet) du sol a la peripherie de l'arene, ciel exclu."""
        try:
            pts = []
            for iobj, nm in c.get('noms', {}).items():
                if 'sora' in nm.lower(): continue
                for key, start_idx, n in c['plages'].get(iobj, []):
                    pos, uv, col = c['groupes'][key]; tex = c['textures'].get(key)
                    if tex is None: continue
                    p, u, k = pos[start_idx:start_idx + n], uv[start_idx:start_idx + n], col[start_idx:start_idx + n]
                    h, w = tex.shape[:2]
                    px = tex[np.clip(((1 - u[:, 1]) * (h - 1)).astype(int) % h, 0, h - 1), np.clip((u[:, 0] * (w - 1)).astype(int) % w, 0, w - 1)]
                    rgb = px[:, :3] / 255.0 * k[:, :3]
                    ok = px[:, 3] > 128
                    pts.append(np.c_[np.hypot(p[:, 0], p[:, 2] - 3.0), p[:, 1], rgb][ok])
            a = np.concatenate(pts)
            ground = a[(a[:, 1] < 2.0) & (a[:, 0] >= np.percentile(a[:, 0], 60))]        # sol de la peripherie de l'arene
            if len(ground) < 20: ground = a[a[:, 0] >= np.percentile(a[:, 0], 85)]
            return tuple(float(x) for x in ground[:, 2:].mean(0))
        except Exception as ex:
            print(tr('fond de combat non calcule :'), ex, flush=True); return None

    def _ui_monster_x(self, mask, entries=False):
        """Abscisses (unites d'interface, colonne portrait 450 x 800) des monstres d'un masque : emplacement i = bit i (MeshChara) projete par la camera de combat. -> (min, max), ou la liste des abscisses (une par monstre) si `entries`."""
        M = getattr(self, '_M_battle', None); e = self.engine.state
        if M is None: return None
        ui_scale = self.height / 800.0 * self.ui_k; cx = {'centre': self.width / 2, 'droite': self.width - 225 * ui_scale, 'gauche': 225 * ui_scale}.get(self.args.ui_pos, self.width / 2)
        xs = []
        for i in range(32):
            if not (mask >> i) & 1: continue
            mm = e.meshes.get(i)
            if not mm: continue
            P = np.array(list(mm['pos']) + [1.0]); c = M @ P
            if c[3] <= 0: continue
            xs.append((((c[0] / c[3]) * 0.5 + 0.5) * self.width - cx) / ui_scale)
        if entries: return xs
        return (min(xs), max(xs)) if xs else None

    def _draw_effect(self, ef):
        """Effet de debut de combat : fond noir, morceaux de la capture qui tombent (voir battle_effect.py)."""
        sim = self.sim_effect
        target = math.ceil(ef['n'] * ENGINE.BATTLE_EFFECT_FRAMES / ef.get('duree', ENGINE.BATTLE_EFFECT_FRAMES))          # cascade raccourcie par « Vitesse de transition » : la simulation avance de plusieurs images du jeu par image du moteur
        while sim.frames < target and not sim.finished: sim.stage()
        gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear()
        gl.glViewport(0, 0, *self.get_framebuffer_size())
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        vl = self.effect_vl; vl.position[:] = sim.positions().ravel().tolist(); vl.colors[:] = sim.colors().ravel().tolist()
        self.program_effect.use(); self.program_effect['lum'] = float(sim.lum); self.program_effect['flou'] = BLUR_EFFECT
        gl.glActiveTexture(gl.GL_TEXTURE0); gl.glBindTexture(self.effect_tex.target, self.effect_tex.id)
        vl.draw(gl.GL_TRIANGLES)
        self.program_effect.stop()

    # saut des chiffres des degats : decalage vers le haut (unites d'interface) a chaque tick de 2 / 30 s (HoppingNumber.Update)
    DAMAGE_JUMP = (0, 0, 4, 4, 6, 6, 6, 6, 4, 4, 2, 2, 0, 0, 2, 2) + (0,) * 22

    def _digits_tex(self):
        """Chiffres 0 a 9 (blancs a ombre, 16 x 16 px) de la feuille de menu : textures separees."""
        if self._tex_count is None:
            self._tex_count = []
            try:
                from PIL import Image
                im = Image.open(os.path.join(self.args.cache, 'ui_MenuTexture.png')).convert('RGBA')
                for d in range(10):
                    a = np.array(im.crop((576 + 16 * d, 288, 592 + 16 * d, 304)))
                    t = pyglet.image.ImageData(16, 16, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=64).get_texture(); gl.glBindTexture(t.target, t.id)
                    gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
                    self._tex_count.append(pyglet.sprite.Sprite(t))
            except Exception as ex: print(tr('Chiffres des degats indisponibles : %r') % (ex,), flush=True)
        return self._tex_count

    def _draw_damage(self, e):
        """Nombres de degats qui sautent au-dessus du monstre touche (BattleMenu_setHoppingNumbers -> HoppingNumber.Create) : quatre chiffres au plus, un tick (2 / 30 s) de decalage entre
        deux chiffres, chaque chiffre visible pendant 19 ticks. Position : pied du monstre projete par la camera du combat, plus min(hauteur x 1,85 ; 160) unites d'interface."""
        if not self.damage_count: return
        if e.part != ENGINE.PART_BATTLE or getattr(self, '_M_battle', None) is None: self.damage_count = []; return
        sp = self._digits_tex()
        if not sp: self.damage_count = []; return
        img = self.engine.frames + self.alpha                          # image du moteur, fraction comprise
        ui_scale = self.height / 800.0 * self.ui_k; living = []
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        for n in self.damage_count:
            mm = e.meshes.get(n['ch'])
            digits = [int(c) for c in str(max(0, min(9999, n['dm'] & 0xffff)))]
            t = img - n['t0']                                           # ticks ecoules depuis la creation (1 tick = 1 image du moteur)
            if t > 21 + 2 * len(digits): continue                     # termine (dernier chiffre : wait >= 38)
            living.append(n)
            if not mm: continue
            P = np.array(list(mm['pos']) + [1.0]); c = self._M_battle @ P
            if c[3] <= 0: continue
            px = ((c[0] / c[3]) * 0.5 + 0.5) * self.width; py = ((c[1] / c[3]) * 0.5 + 0.5) * self.height + min(n['h'] * 1.85, 160.0) * ui_scale
            kd = float(self.reg['taille_degats']); size_value = 25.6 * ui_scale * kd; step = 12.8 * ui_scale * kd; wid = (len(digits) - 1) * step + size_value              # HoppingNumber.Setup : chiffre de 16 px agrandi x 2 (AddIcon size 2,0) soit 32, avance de 16 (PartsInfo[11].m_dps) par chiffre, le tout x 0,8 (echelle locale) : les cases se chevauchent de moitie, les chiffres (7 px sur 16) restent serres
            for k, d in enumerate(digits):
                wait = -(1 + 4 * k) + 2 * t                                  # compteur du chiffre : 2 ticks de decalage entre chiffres, 2 par tick
                if not 0 <= wait < 38: continue
                jump = self.DAMAGE_JUMP[int(wait)] * 0.8 * ui_scale
                s = sp[d]; s.update(x=px - wid / 2 + k * step, y=py + jump, scale=size_value / 16.0); s.draw()
        self.damage_count = living

    def _battle_end_box(self):
        """Vrai quand la boite de dialogue d'un combat doit disparaitre : un fondu au noir commence et la boite n'attend pas de touche (pas de curseur de fin de page : derniere page validee, ou message qui se ferme seul comme « Ragnar meurt ! »).
        Le moteur ne ferme la boite qu'apres le fondu : elle restait affichee sur l'ecran qui noircit. Une boite qui attend encore une touche reste affichee. Elle revient si un nouveau fondu (d'ouverture) commence."""
        eng = self.engine; e = eng.state; fd = e.fade; feed = bool(eng.ui.msg.get('feed'))
        fade_rising = e.part == ENGINE.PART_BATTLE and fd['pas'] > 0 and (fd['n'] >= 1 or fd['a'] >= 0.999)         # fondu au noir en cours (ou noir maintenu)
        if not fade_rising: self._box_hidden = False
        elif not getattr(self, '_prev_fading', False): self._box_hidden = not feed
        self._prev_fading = fade_rising
        if feed: self._box_hidden = False                                  # une page qui attend une touche doit se voir
        return getattr(self, '_box_hidden', False)

    def _battle_clock(self):
        """Le jeu est-il dans un combat, au sens de l'horloge du moteur ? Partie « combat » du moteur (0xd), mais aussi l'effet d'ecran qui le lance et l'ecran noir qui attend le chargement de sa scene (State.effet,
        State.load_wait : seul un combat les leve). Hors de cela la vitesse de combat n'a aucun effet (la marche garde ses reglages) ; en combat, au contraire, la marche et l'accelerateur n'en ont plus."""
        e = self.engine.state
        return e.part == ENGINE.PART_BATTLE or e.effect is not None or e.load_wait is not None

    def _wait_for_player(self):
        """Le moteur attend-il le joueur en combat ? Menu qui a la saisie (commandes, cible, sorts, objets, Oui / Non) ou message qui montre son curseur ▼ (Manuel : une touche est attendue). Les touches ne sont alors lues qu'au rythme
        normal (pas « muets » entre deux lectures, voir _do_battle_step) : curseur et repetition des touches inchanges, alors que les monstres suivent la vitesse de combat. (Le dernier message d'un combat attend aussi une touche
        sans montrer le curseur : non detectable, ses pas supplementaires sont donc lus comme des pas ordinaires.)"""
        eng = self.engine; p = eng.active_menu()
        if p is not None and not (eng.state.part == ENGINE.PART_BATTLE and without_validation(eng, getattr(self, 'ui_g', None), p)): return True          # (arene des monstres : la fenetre « Quitter » reste ouverte pendant tout le combat, ce n'est pas une attente du joueur)
        return bool(eng.msg_visible and eng.ui.msg.get('feed'))

    _t_real_step = 0.0                                                  # heure du dernier pas qui a lu les touches (combat accelere : voir _do_battle_step)

    def _do_battle_step(self):
        """Un pas du moteur pendant un combat accelere. Quand le moteur attend le joueur, seul un pas sur (f) lit les touches et les clics, a cadence normale (un par 1 / 30 s reelles) ; les autres sont muets : le moteur avance
        (animation de repos des monstres, fenetres) a la vitesse choisie, sans qu'un curseur ni une repetition de touche aille plus vite. Toujours True : on continue jusqu'au bout du rattrapage."""
        t = time.perf_counter()
        mute = self._wait_for_player() and t - self._t_real_step < ENGINE_STEP * VC.TOLERANCE
        if not mute: self._t_real_step = t
        e = self.engine.state; before = e.effect is not None
        self._step(mute)
        return before or e.effect is None          # la cascade d'entree commence pendant ce pas : on s'arrete la, la suite de l'image reprend a l'horloge du jeu (voir _speed_factor)

    def change_battle_speed(self, source='touche'):
        """Touche « Changer la vitesse en combat » ou bouton de l'ecran de combat : Manuel -> Normal -> Rapide -> Très rapide -> Manuel. Le reglage change tout de suite (la section Défilement du texte de Commandes le relit), est enregistre et gouverne aussi le
        defilement des messages (Manuel : a la main). Aucun message a l'ecran (retire depuis #267) : le bouton de l'ecran de combat montre la vitesse, la section Defilement du texte de Commandes aussi."""
        v = RG.next_battle_speed(self.reg['vitesse_combat']); self.reg['vitesse_combat'] = v; self.apply_scroll(); self.reg.store()
        return v
