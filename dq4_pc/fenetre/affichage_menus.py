"""Messages, fenetres de menu du jeu et editeur d'interface ; fondus, vignette et petits messages des sauvegardes (toasts)."""
import os, random, time
import numpy as np
import pyglet
from pyglet import gl
from pyglet.graphics.shader import Shader
from pyglet.graphics.shader import ShaderProgram
from dq4_pc.combat import effet_combat as EC
from dq4_pc.langue import tr, N_
from dq4_pc.fenetre import entrees as EN
from dq4_pc.menus import ui_menu as UI
from dq4_pc.noyau import moteur as MO
from dq4_pc.persistance import reglages as RG
from dq4_pc.fenetre.constantes import (BTN_SAUVEGARDES, CB_MSG_BAS, CB_ZONE_MENUS, FENETRES_CENTREES, MSG_BAS, OUINON_ECART, POLICES, SE_BOUTON,
    UI_ZOOM)
from dq4_pc.fenetre.shaders import FRAG_DEGRADE, VERT_DEGRADE
from dq4_pc.fenetre.aides import sans_validation


class MenusMixin:
    """Messages, fenetres de menu du jeu et editeur d'interface ; fondus, vignette et petits messages des sauvegardes (toasts)."""

    def toast(self, texte, duree=1.8):
        """Petit message en haut de l'ecran, SEULEMENT pour les sauvegardes (etats instantanes, sauvegarde du jeu impossible, import) : depuis #267 les autres notifications (vitesse de combat, plein ecran, memoire du moteur, reglages, son...) n'existent plus (D-228) ;
        les sauvegardes les ont retrouvees le 04/11/2026 (D-230). tests/test_notifications_sauvegardes.py garde la liste des appels permis."""
        self.toasts = [(tr(texte), time.time() + duree)]            # (D-238 : le texte est traduit ici ; un texte a trous doit l'etre avant d'etre formate : toast(tr('Etat %d') % n))

    def ui_g_reset(self):
        """Refait les fenetres de menu d'origine d'apres la memoire de l'interface (apres le chargement d'un etat)."""
        if self.ui_g is None: return
        self.ui_g.f.clear(); self.moteur.ui.obs = self.ui_g; self.ui_g.rejouer(self.moteur.ui)

    H_ECH = 87                                                  # hauteur (pixels du canevas) d'un echantillon de message : 3 lignes de 28 pixels + 3 de marge (voir ui_menu.limiter_lignes)

    ESSAIS = ((N_("Aperçu d'un message."),),                                                      # textes d'essai de l'editeur d'interface (1 a 3 lignes, comme une boite de dialogue) : un au hasard a chaque choix de « Dialogues » ; chaque ligne est traduite au dessin
              (N_("Ceci est un texte de test."), N_("Il sert à régler la taille et"), N_("la position des dialogues.")),
              (N_("Aperçu d'un message"), N_("sur deux lignes.")),
              (N_("Voici un exemple de dialogue."), N_("Déplace et redimensionne cette"), N_("fenêtre comme tu le souhaites.")),
              (N_("Texte d'essai : les messages du jeu"), N_("s'afficheront ici, à cette taille.")))

    def nouvel_echantillon(self):
        """L'editeur choisit le texte d'essai montre dans la fenetre de dialogue : au hasard parmi ESSAIS (autre que le precedent)."""
        n = len(self.ESSAIS); p = getattr(self, '_essai', None)
        self._essai = random.choice([k for k in range(n) if k != p]); self._ech_vu = None

    def _canevas_apercu(self):
        """Canevas 512 x 512 de l'apercu des dialogues : le texte d'essai choisi, en police du jeu, range des la 1re rangee."""
        if getattr(self, '_essai', None) is None: self.nouvel_echantillon()
        cv = np.zeros((512, 512), np.uint8)
        from PIL import Image, ImageDraw, ImageFont
        im = Image.new('L', (512, self.H_ECH), 0); dr = ImageDraw.Draw(im)
        try: f = ImageFont.truetype(os.path.join(self.args.cache, 'ui_font.otf'), 22)
        except Exception: f = ImageFont.load_default()
        for j, t in enumerate(self.ESSAIS[self._essai % len(self.ESSAIS)]): dr.text((4, 7 + 28 * j + 20), tr(t), font=f, fill=255, anchor='ls')
        cv[:self.H_ECH] = np.asarray(im)
        return cv

    def _maj_message(self):
        """Texte visible du message (canevas du moteur) -> image RGBA blanche dont l'opacite est celle du texte."""
        if self.ui_msg:                                          # fenetre d'origine : tout le canevas (512 x 512, en boucle) + defilement par decalage d'UV
            a = self.moteur.lire_canevas()
            if a is not None:
                cle = hash(a.tobytes())
                if cle != self.canevas_cle:
                    self.canevas_cle = cle; self.ui_rendu.maj_canevas(a)
                    if os.environ.get('DQ_UIDBG'):                                  # (test) lignes de texte du canevas : (premiere rangee, derniere rangee)
                        r = np.where(a.max(1) > 40)[0]; g = []
                        if len(r):
                            s0 = p0 = r[0]
                            for q in r[1:]:
                                if q > p0 + 3: g.append((int(s0), int(p0))); s0 = q
                                p0 = q
                            g.append((int(s0), int(p0)))
                        print('CANEVAS image %s lignes %s msg %s moteur (lignes, hauteur, defil) %s' % (self.moteur.images, g, self.moteur.ui.msg, self.moteur.params_message()), flush=True)
            m = self.moteur.ui.msg; typ = m['type']
            if typ == 1 and a is not None and a[(np.arange(102, 164) + (int(m['y']) & 0x1ff)) % 512].max() > 40: typ = 4       # message de combat de 4 lignes (4 groupes de monstres) : cadre d'origine
            self.ui_msg.regler(typ, m['y'], m['feed'], m.get('qui', ''))
            return
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

    def _copier_ecran(self, combat=True):
        """Copie l'image qui vient d'etre dessinee dans une texture (la capture que l'effet de debut de combat brise en morceaux, ou que les effets voyage, lampe et Riremito deforment : `combat` faux, voir effets_capture.py)."""
        w, h = self.get_framebuffer_size()
        if self.effet_tex is not None: self.effet_tex.delete()
        t = pyglet.image.Texture.create(w, h, internalformat=gl.GL_RGBA8)
        gl.glBindTexture(t.target, t.id)
        gl.glCopyTexSubImage2D(t.target, 0, 0, 0, 0, 0, w, h)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glGenerateMipmap(t.target)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        self.effet_tex = t
        if not combat: return
        self.effet_sim = EC.EffetTuiles(self.width / max(1, self.height))
        n = self.effet_sim.rows * EC.COLS * 6
        if self.effet_vl is not None: self.effet_vl.delete()
        self.effet_vl = self.prog_effet.vertex_list(n, gl.GL_TRIANGLES, position=('f', self.effet_sim.positions().ravel().tolist()), tex_coords=('f', self.effet_sim.UV.ravel().tolist()), colors=('f', self.effet_sim.couleurs().ravel().tolist()))

    def _tracer_degrade_fond(self, haut, bas):
        """Fond des villes (#111) : degrade vertical de la couleur `haut` (haut de l'image) a la couleur `bas`, tel que le dessine le `BackColor` du jeu (voir VERT_DEGRADE), par-dessus l'effacement (la moyenne des deux) et
        avant la scene ; la profondeur n'est ni lue ni ecrite. Rien a faire si les deux couleurs sont egales (l'effacement est deja cette couleur)."""
        if self.prog_degrade is None:
            self.prog_degrade = ShaderProgram(Shader(VERT_DEGRADE, 'vertex'), Shader(FRAG_DEGRADE, 'fragment'))
            self.degrade_vl = self.prog_degrade.vertex_list(6, gl.GL_TRIANGLES, position=('f', [1.0, 1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0, -1.0, 1.0, -1.0]))
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glDisable(gl.GL_BLEND)
        self.prog_degrade.use(); self.prog_degrade['haut'] = tuple(float(c) for c in haut); self.prog_degrade['bas'] = tuple(float(c) for c in bas)
        self.degrade_vl.draw(gl.GL_TRIANGLES)
        self.prog_degrade.stop()
        gl.glEnable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    def _dessiner_vignette(self):
        """Assombrit les bords de l'image de jeu (reglage Vignettage), sous le fondu et l'interface : degrade radial elliptique (centre intact jusqu'a 45 % du rayon, bords en noir
        d'opacite = reglage). Texture 512 x 288 etiree sur la fenetre (filtre lineaire), creee une fois."""
        v = float(self.reg['vignette'])
        if v <= 0.005: return
        t = getattr(self, '_vign_tex', None)
        if t is None:
            n, m = 512, 288; yy, xx = np.mgrid[0:m, 0:n]; r = np.hypot((xx + 0.5) / n * 2 - 1, (yy + 0.5) / m * 2 - 1)
            k = np.clip((r - 0.45) / (1.3 - 0.45), 0.0, 1.0); k = k * k * (3 - 2 * k)
            a = np.zeros((m, n, 4), np.uint8); a[..., 3] = np.round(255 * k).astype(np.uint8)
            t = self._vign_tex = self._tex(a, False)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        sp = pyglet.sprite.Sprite(t, x=0, y=0); sp.scale_x = self.width / t.width; sp.scale_y = self.height / t.height; sp.opacity = int(round(255 * min(1.0, v))); sp.draw()

    def _dessiner_fondu(self, fond=False):
        """Plans de fondu d'ecran (Fade.FadePlane, bit 14 du paquet 9 = Fade.l_targetLayer) : `fond` = plan « FadeForBG » (Custom/BackFade, file Background : devant la scene, derriere les fenetres et les messages) ;
        sinon plan « FadeForMenu » (Custom/FrontFade, file Overlay : devant tout, fenetres et messages compris)."""
        e = self.moteur.etat; fd = e.fondu_fond if fond else e.fondu
        if fd['a'] <= 0.004: return
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        r = pyglet.shapes.Rectangle(0, 0, self.width, self.height, color=tuple(int(round(255 * min(max(c, 0.0), 1.0))) for c in fd['col']))
        r.opacity = int(round(255 * min(fd['a'], 1.0)))
        r.draw()

    def _dessiner_message(self):
        if self.ui_msg: return                                   # dessinee avec les fenetres d'origine (_dessiner_menus)
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
            princ = ' '.join(' '.join(t.split('\n')) for c, t in sorted(cols.items()) if c not in (2, 3, 5) and t)     # retours a la ligne -> espaces (resume d'action : « Attaquer ▼ cible »)
            if not (princ or val or lab): continue
            out.append((r, (pre + ' ' + princ).strip(), lab, val, princ.rstrip().endswith('?')))
        return [l for l in out if l[4]] + [l for l in out if not l[4]]

    def _port_clavier(self, port):
        """Port qui recoit le clavier : celui du menu actif du moteur, sauf si c'est une fenetre a un seul bouton (menu Divers : la saisie va a « Sauvegarde rapide », ouverte en dernier) alors qu'une fenetre
        visible plus fournie existe (la liste de la page) : c'est elle qu'on parcourt (le toucher agit sur toutes les fenetres)."""
        if port is None or not self.ui_g: return port
        mo = self.moteur
        def n(q):
            fe = self.ui_g.f.get(q); return sum(1 for b in fe.boutons() if b[1] & 0x10) if fe else 0
        if n(port) > 1: return port
        cand = [q for q, f in mo.ui.f.items() if q > 1 and f['vis'] and f['cases'] and q in self.ui_g.f and n(q) > 1]
        return max(cand, key=lambda q: mo.ui.f[q]['ordre']) if cand else port

    def _quitter_seul(self, port):
        """Fenetre « Quitter » de l'arene des monstres (type 71) : en combat, sans bouton de validation ni curseur du moteur."""
        return self.moteur.etat.partie == MO.PARTIE_COMBAT and sans_validation(self.moteur, self.ui_g, port)

    def _port_pour_manette(self, port, pad):
        """Port qui recoit la touche de manette `pad` (haut 2, bas 1, droite 4, gauche 8, A 16, B 32) : celui du menu actif s'il a un bouton pour elle, sinon la fenetre visible la plus recente qui en a un.
        Menu Divers : le moteur donne la saisie a la fenetre « Sauvegarde rapide », mais le bouton retour est dans la liste et les fleches de page dans une troisieme fenetre."""
        mo = self.moteur
        def a(q):
            fe = self.ui_g.f.get(q) if self.ui_g else None
            return bool(fe) and any(b[1] & pad for b in fe.boutons())
        if a(port): return port
        for q in sorted((q for q, f in mo.ui.f.items() if q > 1 and f['vis'] and q in self.ui_g.f), key=lambda q: -mo.ui.f[q]['ordre']):
            if a(q): return q
        return port

    def _saisie_menu(self, port, decl, pages=0):
        """Touches -> menu actif, comme MenuPort.Send d'Unity : [1, numero de bouton, manette] (manette du jeu : bas 1, haut 2, droite 4, gauche 8, A 16, B 32).
        Menu a curseur du moteur (message 2 : colonnes x lignes, ex. Oui / Non) : les touches lui sont transmises, il deplace son curseur (messages 4) et valide ;
        gauche/droite sur une seule colonne = precedent/suivant. Menu tactile (boutons sans curseur du moteur) : curseur local deplace d'apres la position des boutons, A = toucher."""
        mo = self.moteur; f = mo.ui.f[port]
        if decl: self.survol_nd = None                                # une touche : le curseur reprend la main (rangee entiere en surbrillance)
        dirs = ((MO.HAUT, 2), (MO.BAS, 1), (MO.GAUCHE, 8), (MO.DROITE, 4))
        fe = self.ui_g.f.get(port) if self.ui_g else None
        z = {b: ((x0 + x1) / 2, (z0 + z1) / 2) for b, pad, x0, z0, x1, z1, _ in (fe.boutons() if fe else []) if b >= 0 and pad & 0x10}
        if not f.get('grille') and len(z) <= 1 and self._saisie_pas(port, f, fe, z, decl): return          # menu de saisie numerique (mise, jetons, montant) : fleches = colonnes et ▲ / ▼
        if pages and not f.get('grille') and len({round(c[0] / 20.0) for c in z.values()}) >= 2:          # L / R (page precedente / suivante) dans une liste a plusieurs colonnes (bestiaire) : gauche / droite y changent de colonne, ce sont donc les fleches ◀ ▶ de page de la fenetre qui sont pressees
            fl = self._fleche_page(port, 8 if pages & 1 else 4)
            if fl: mo.envoyer_menu(fl[0], 1, fl[1], 8 if pages & 1 else 4); self.menu_relacher = fl[0]; return
        if not f.get('grille') and len(z) < 1 and decl & (MO.GAUCHE | MO.DROITE):           # fenetre sans curseur du moteur ni bouton A (pages du Statut, types 13-17) : gauche / droite (Q, D, L, R) tournent les pages avec les fleches d'une autre fenetre (type 6), comme un toucher
            pad = 4 if decl & MO.DROITE else 8; q = self._port_pour_manette(port, pad)
            if q != port: mo.envoyer_menu(q, 1, -1, pad); self.menu_relacher = q; return
        if f.get('grille') or len(z) < 1:
            for bit, pad in dirs:
                if decl & bit:
                    if bit in (MO.GAUCHE, MO.DROITE) and not f.get('grille') and self._fleche_page(port, pad):         # fenetre sans bouton de validation mais avec ses fleches de page (fiche du bestiaire) : gauche / droite les pressent
                        fl = self._fleche_page(port, pad); mo.envoyer_menu(fl[0], 1, fl[1], pad); self.menu_relacher = fl[0]; return
                    if bit in (MO.GAUCHE, MO.DROITE) and (f.get('grille') or (1, 1, 1))[0] < 2: pad = 2 if bit == MO.GAUCHE else 1
                    mo.envoyer_menu(port, 1, -1, pad); self.menu_relacher = port; return
            if decl & MO.A:
                act = next((b for b, pd, *_ in (fe.boutons() if fe else []) if pd & 0x800), None)          # « Action » de la fiche du bestiaire (manette 0x800) : la seule fenetre qui en a un
                if act is not None and not f.get('grille'): mo.envoyer_menu(port, 1, act, 0x800); self.menu_relacher = port; self.son.jouer_se(SE_BOUTON)
                else: mo.envoyer_menu(port, 1, -1, 0x10); self.menu_relacher = port; self.son.jouer_se(SE_BOUTON)
            elif decl & MO.B: q = self._port_pour_manette(port, 0x20); mo.envoyer_menu(q, 1, -1, 0x20); self.menu_relacher = q
            return
        cle = (port, f['ordre']); cur = self.cur_local.get(cle)
        if cur not in z:
            cur = self.cur_local[cle] = f['cur'] if f['cur'] in z else min(z, key=lambda b: (-round(z[b][1]), z[b][0]))       # depart : le bouton en haut a gauche
        if decl & (MO.GAUCHE | MO.DROITE) and fe and fe.typ in (58, 59, 63):                       # quantite (types 58 / 59 : liste « Acheter », 63 : quantite a vendre) : la rangee du curseur porte ses propres fleches (boutons de meme numero, manette gauche 8 / droite 4 : liste « Acheter » d'une boutique, quantite a vendre) -> gauche / droite changent la quantite de la rangee choisie (comme le toucher d'une fleche) ; le curseur garde la rangee entiere
            pad = 4 if decl & MO.DROITE else 8
            if any(b == cur and pd & pad for b, pd, *_ in fe.boutons()): mo.envoyer_menu(port, 1, cur, pad); self.menu_relacher = port; return
        if len({round((x0 + x1) / 20.0) for b, pad, x0, z0, x1, z1, _ in (fe.boutons() if fe else []) if b >= 0 and pad & 0x10}) <= 1 and decl & (MO.GAUCHE | MO.DROITE):       # une seule colonne : gauche / droite tournent les pages si une autre fenetre porte les fleches
            pad = 4 if decl & MO.DROITE else 8; q = self._port_pour_manette(port, pad)
            if q != port: mo.envoyer_menu(q, 1, -1, pad); self.menu_relacher = q; return
        for bit, _ in dirs:
            if decl & bit: cur = self.cur_local[cle] = self._voisin(z, cur, bit)
        if decl and os.environ.get('DQ_MENUDBG'): print('MENU curseur local image %d port %d decl %d -> %s ; boutons %s' % (self.n, port, decl, cur, {b: (round(c[0]), round(c[1])) for b, c in z.items()}), flush=True)
        if decl & MO.A and cur == BTN_SAUVEGARDES and self._port_depart(port): self.son.jouer_se(SE_BOUTON); self._sauv_ouvrir()
        elif decl & MO.A: mo.envoyer_menu(port, 1, cur, 0x10); self.menu_relacher = port; self.son.jouer_se(SE_BOUTON)
        elif decl & MO.B: q = self._port_pour_manette(port, 0x20); mo.envoyer_menu(q, 1, -1, 0x20); self.menu_relacher = q

    def _fleche_page(self, port, pad):
        """Fleche de page ◀ (manette 8) ou ▶ (manette 4) de la fenetre `port` : (port, numero de bouton), ou None. Les fleches de quantite des boutiques (types 58, 59, 63 : une par rangee) n'en sont pas."""
        fe = self.ui_g.f.get(port) if self.ui_g else None
        if fe is None or fe.typ in (58, 59, 63): return None
        for b, pd, *_ in fe.boutons():
            if pd & pad: return (port, b)
        return None

    def _pas_colonnes(self, fe):
        """Colonnes ▲ / ▼ d'un menu de saisie numerique (mise de la machine a sous et du poker, jetons, montant de la banque, pari de l'arene : Make_Casino_*, Make_Bank*) : numeros de bouton >= 0 qui ont
        a la fois un element de manette 0x2 (▲, valeur + 1 rang) et un de manette 0x1 (▼), de gauche a droite. Vide pour les autres fenetres (les ▲ / ▼ de numero -1 sont des fleches de page)."""
        if fe is None: return []
        bs = fe.boutons(); haut = {b for b, pad, *_ in bs if b >= 0 and pad & 0x2}; bas = {b for b, pad, *_ in bs if b >= 0 and pad & 0x1}
        cx = {b: (x0 + x1) / 2 for b, pad, x0, z0, x1, z1, _ in bs if b in haut & bas and pad & 0x3}
        return sorted(cx, key=lambda b: cx[b])

    def _pas_actif(self, port):
        """Colonne ▲ / ▼ choisie au clavier dans un menu de saisie numerique (la plus a droite au depart : les unites), ou None si la fenetre n'en a pas (ou si elle a plusieurs boutons de validation : curseur ordinaire)."""
        fe = self.ui_g.f.get(port) if self.ui_g else None; f = self.moteur.ui.f.get(port)
        if fe is None or f is None or f.get('grille'): return None
        cols = self._pas_colonnes(fe)
        if not cols or sum(1 for b in fe.boutons() if b[0] >= 0 and b[1] & 0x10) > 1: return None
        c = self.cur_pas.get((port, f['ordre'])); return c if c in cols else cols[-1]

    def _saisie_pas(self, port, f, fe, z, decl):
        """Menu de saisie numerique au clavier (les boutons ▲ / ▼ sont des touches de manette 0x2 / 0x1, hors du curseur local) : gauche / droite choisissent la colonne (dizaines, unites...), haut / bas = ▲ / ▼ de la colonne
        (envoyes au moteur comme le toucher du bouton), A = le bouton de validation (Lancer, Donner, Valider), B = retour. Faux si la fenetre n'est pas de ce genre ou si aucune touche utile n'est pressee."""
        if not decl & (MO.HAUT | MO.BAS | MO.GAUCHE | MO.DROITE | MO.A | MO.B): return False
        cols = self._pas_colonnes(fe)
        if not cols: return False
        mo = self.moteur; cle = (port, f['ordre']); act = self._pas_actif(port)
        if act is None: return False
        self.survol_nd = None                                                       # une touche : le curseur reprend la main
        if decl & (MO.GAUCHE | MO.DROITE):
            i = cols.index(act) + (1 if decl & MO.DROITE else -1); self.cur_pas[cle] = cols[min(max(i, 0), len(cols) - 1)]
        elif decl & (MO.HAUT | MO.BAS): mo.envoyer_menu(port, 1, act, 2 if decl & MO.HAUT else 1); self.menu_relacher = port
        elif decl & MO.A: mo.envoyer_menu(port, 1, next(iter(z), -1), 0x10); self.menu_relacher = port; self.son.jouer_se(SE_BOUTON)
        else: q = self._port_pour_manette(port, 0x20); mo.envoyer_menu(q, 1, -1, 0x20); self.menu_relacher = q
        return True

    @staticmethod
    def _voisin(z, cur, bit):
        """Bouton voisin dans la direction pressee (z : numero -> centre en unites d'interface, Z vers le haut) ; au bord on boucle vers l'autre extremite de la rangee/colonne."""
        x, y = z[cur]
        if bit in (MO.GAUCHE, MO.DROITE):
            sens = 1.0 if bit == MO.DROITE else -1.0
            avant = [(b, (c[0] - x) * sens + 3.0 * abs(c[1] - y)) for b, c in z.items() if (c[0] - x) * sens > 4.0]
            if avant: return min(avant, key=lambda t: t[1])[0]
            tour = [(b, abs(c[1] - y) * 100.0 - (c[0] - x) * sens) for b, c in z.items() if b != cur and abs(c[1] - y) < 12.0]
        else:
            sens = 1.0 if bit == MO.HAUT else -1.0
            avant = [(b, (c[1] - y) * sens + 3.0 * abs(c[0] - x)) for b, c in z.items() if (c[1] - y) * sens > 4.0]
            if avant: return min(avant, key=lambda t: t[1])[0]
            tour = [(b, abs(c[0] - x) * 100.0 - (c[1] - y) * sens) for b, c in z.items() if b != cur and abs(c[0] - x) < 12.0]
        return min(tour, key=lambda t: t[1])[0] if tour else cur

    def _etiq(self, texte, taille, couleur=(255, 255, 255, 255), polices=()):
        """Etiquette de texte (mise en cache) ; `polices` : familles essayees avant les polices du systeme (police du jeu pour le menu Echap)."""
        k = (texte, round(taille, 1), couleur, polices)
        l = self.etiq_menu.get(k)
        if l is None:
            if len(self.etiq_menu) > 400: self.etiq_menu.clear()
            l = self.etiq_menu[k] = pyglet.text.Label(texte, font_name=tuple(polices) + POLICES, font_size=taille, color=couleur, anchor_x='left', anchor_y='baseline')
        return l

    def _marge_aide(self):
        """(cote, largeur) du bloc d'infos de F1 : en haut a DROITE de l'ecran par defaut ; largeur = la marge libre a cote de la colonne d'interface (portrait 450 x 800 centre), pour ne pas cacher les fenetres du jeu (voir entrees.zone_infos)."""
        return EN.zone_infos(self.width, self.height, bool(self.ui_rendu), UI_ZOOM, self.args.ui_pos)

    def _curseur(self, port):
        """Bouton en surbrillance du menu actif : curseur du moteur (messages 4) ou, sans curseur du moteur, curseur local des fleches."""
        f = self.moteur.ui.f[port]
        if f.get('grille'): return f['cur']
        pas = self._pas_actif(port)
        if pas is not None: return pas                                  # menu de saisie numerique : la colonne ▲ / ▼ choisie
        return self.cur_local.get((port, f['ordre']), f['cur'])

    def _ui_repere(self):
        """Colonne d'interface du jeu (portrait 450 x 800 centre, hauteur de la fenetre) : (x du centre, y du centre, pixels par unite)."""
        ech = self.height / 800.0 * self.ui_k
        return {'centre': self.width / 2, 'droite': self.width - 225 * ech, 'gauche': 225 * ech}.get(self.args.ui_pos, self.width / 2), self.height / 2.0, ech

    def noms_fenetres(self):
        """Noms (Make_* de MenuPortItemTable, sans le prefixe) des fenetres du jeu qui ont une mise en page : {nom: [numeros de type]} (editeur d'interface)."""
        if getattr(self, '_noms_make', None) is None:
            self._noms_make = {}
            if self.ui_g is not None:
                for num, t in self.ui_g.ml.types.items():
                    if t.get('err') not in (None, 'None') or not t.get('nodes'): continue
                    self._noms_make.setdefault(t.get('name', '').replace('Make_', '').replace('()', '') or 'type%s' % num, []).append(int(num))
        return self._noms_make

    def _nom_de_type(self, typ):
        m = getattr(self, '_types_noms', None)
        if m is None: m = self._types_noms = {n: nom for nom, nums in self.noms_fenetres().items() for n in nums}          # numero de type -> nom Make_* (une fois par partie : appele pour chaque fenetre a chaque image)
        return m.get(typ)

    def _cachee(self, typ):
        """Fenetre du jeu masquee par le joueur (editeur d'interface : « Afficher cette interface a l'ecran » = Non) ?"""
        ms = self.reg['interface_masquees']
        return bool(ms) and self._nom_de_type(typ) in ms

    def _ouinon_sur_message(self, msg, fe):
        """Pile Oui / Non (D-231) posee sur le coin haut droit de la boite de dialogue : -> (decalage vertical en unites qui pose le bord bas VISIBLE de la pile OUINON_ECART au-dessus du bord haut visible de la boite,
        (bord droit visible de la boite, bord droit visible de la pile)). Les cadres ont des marges transparentes differentes (6 unites a droite pour la boite) : on aligne ce qu'on voit, pas les mailles. None si une mesure manque."""
        mv = msg.etendue_visible() if msg is not None else None; ev = fe.etendue_visible()
        if not mv or not ev: return None
        return float(mv[3] + OUINON_ECART - ev[2]), (float(mv[1]), float(ev[1]))

    def _ui_ouinon(self, base, D, e0, v, bords=None):
        """Oui / Non (type 1) regle par le joueur : il suit la fenetre de message comme d'habitude (base = (cx, cy, s) de celle-ci, D = decalage vertical d'unites qui l'y colle, e0 = son bord bas en unites),
        puis sa taille v[0] se change autour de son bord bas et de son bord droit, et il se decale de v[1], v[2] (fractions de l'ecran).
        bords = (bord droit de la fenetre de message, bord droit du Oui / Non) en unites : la pile de Oui / Non a son bord droit sur celui de la boite de dialogue (D-231). -> (cx, cy, s) de dessin."""
        bx, by, bs = base; s2 = bs * float(v[0]); y_bas = by + (D + e0) * bs + float(v[2]) * self.height
        x = bx + float(v[1]) * self.width + ((bords[0] * bs - bords[1] * s2) if bords else 0.0)
        return x, y_bas - e0 * s2, s2

    def _ui_perso(self, mode, s, v):
        """Repere (cx, cy, s) d'une fenetre modifiee par le joueur (editeur d'interface) : taille v[0] autour du bord de son groupe (bas, haut ou milieu de l'ecran), puis decalage v[1], v[2] en fraction de l'ecran."""
        s2 = s * float(v[0]); H = float(self.height)
        cy = 400.0 * s2 if mode == 'bas' else (H - 400.0 * s2 if mode == 'haut' else H / 2.0)
        return self._ui_repere()[0] + float(v[1]) * self.width, cy + float(v[2]) * H, s2

    def _canevas_apercu_maj(self, fe):
        if getattr(self, '_essai', None) is None: self.nouvel_echantillon()
        if getattr(self, '_ech_vu', None) != self._essai:
            self._ech_vu = self._essai; self.ui_rendu.maj_canevas(self._canevas_apercu(), 'msg_apercu')
            fe.regler(0, 0, False)

    def _fenetre_apercu(self, cle):
        """Fenetre d'apercu de l'editeur d'interface (gardee) : 'msg' = dialogues (texte d'essai), sinon le nom Make_* ; None si elle n'a pas de mise en page."""
        if not hasattr(self, '_apercus'): self._apercus = {}
        fe = self._apercus.get(cle)
        if fe is None:
            if cle == 'msg':
                fe = UI.FenetreMessage(self.ui_g.ml); fe.regler(0, 0, False); fe.N['canevas']['mats'][0]['sheet'] = 'msg_apercu'          # (texte d'essai : canevas a part, pas celui du moteur)
            else:
                nums = self.noms_fenetres().get(cle)
                if not nums: return None
                fe = UI.Fenetre(self.ui_g.ml, nums[0])
                if fe.etendue() is None:                                                    # parties cachees tant que le moteur ne les demande pas (bandeau de l'equipe en combat, jetons du stade...) : l'apercu les montre toutes
                    for nd in fe.N.values(): nd['act'] = True
            self._apercus[cle] = fe
        return fe

    def apercu_interface(self, cle):
        """Editeur d'interface : apercu de la fenetre `cle` ('msg' = dialogues, sinon nom Make_*) a sa taille et sa place (mise en page d'origine, sans etat de jeu) -> (x0, y0, x1, y1) en pixels, ou None."""
        if self.ui_rendu is None or self.ui_g is None: return None
        fe = self._fenetre_apercu(cle)
        if fe is None: return None
        if cle == 'msg': self._canevas_apercu_maj(fe)
        e = fe.etendue()
        if not e: return None
        if cle == 'YesNo': return self._apercu_ouinon(fe, e)
        dz = (MSG_BAS - fe.bas()) if cle == 'msg' else 0.0
        k, gr, modes = self._ui_echelle([(e[0] + dz, e[1] + dz)]); s = self.height / 800.0 * k
        mode = modes[0] if modes else 'bas'
        v = self.reg['interface_fenetres'].get(cle) or RG.fenetre_defaut(cle)
        cx, cy, s2 = self._ui_perso(mode, s, v)
        fe.sel = None; fe.sel_nd = None; fe.appui_nd = None
        self.ui_rendu.dessiner([fe], cx, cy + dz * s2, s2, (self.width, self.height))
        x0, x1 = cx - 225 * s2, cx + 225 * s2; y0, y1 = cy + (e[0] + dz) * s2, cy + (e[1] + dz) * s2          # cadre jaune : emprise de la fenetre
        pyglet.shapes.Box(x0, y0, x1 - x0, y1 - y0, thickness=2, color=(255, 235, 130)).draw()
        return x0, y0, x1, y1

    def _apercu_ouinon(self, fe, e):
        """Apercu de Oui / Non : comme dans le jeu, la pile (Oui au-dessus de Non) est posee sur le coin haut droit de la fenetre de message (montree a sa place, avec ses reglages), bords droits alignes ; son cadre jaune est celui de l'element regle."""
        fm = self._fenetre_apercu('msg'); self._canevas_apercu_maj(fm); em = fm.etendue()
        if not em: return None
        pose = self._ouinon_sur_message(fm, fe); dzm = MSG_BAS - fm.bas(); D = dzm + (pose[0] if pose else em[1] + OUINON_ECART - e[0])
        k, gr, modes = self._ui_echelle([(em[0] + dzm, em[1] + dzm), (e[0] + D, e[1] + D)]); s = self.height / 800.0 * k
        mode = modes[0] if modes else 'bas'; ov = self.reg['interface_fenetres']
        cxm, cym, sm = self._ui_perso(mode, s, ov.get('msg') or RG.FENETRE_DEFAUT)
        fm.sel = None; fm.sel_nd = None; fe.sel = None; fe.sel_nd = None
        self.ui_rendu.dessiner([fm], cxm, cym + dzm * sm, sm, (self.width, self.height))
        cx, cy, s2 = self._ui_ouinon((cxm, cym, sm), D, e[0], ov.get('YesNo') or RG.FENETRE_DEFAUT, pose[1] if pose else None)
        self.ui_rendu.dessiner([fe], cx, cy, s2, (self.width, self.height))
        ex = fe.etendue_x(); x0, x1 = (cx + ex[0] * s2, cx + ex[1] * s2) if ex else (cx - 225 * s2, cx + 225 * s2); y0, y1 = cy + e[0] * s2, cy + e[1] * s2          # (cadre jaune : la pile Oui / Non)
        pyglet.shapes.Box(x0, y0, x1 - x0, y1 - y0, thickness=2, color=(255, 235, 130)).draw()
        return x0, y0, x1, y1

    def _ui_echelle(self, intervalles):
        """Agrandissement des fenetres : intervalles [(bas, haut)] en unites d'interface -> (k, mode de chaque groupe).
        Les fenetres proches (moins de 60 unites) forment un groupe ; un groupe du bas (resp. du haut, resp. du milieu) est agrandi autour du bord bas
        (haut, centre) de l'ecran, pour rester colle a ce bord. k = UI_ZOOM, reduit (jusqu'a 1) tant qu'un groupe sort de l'ecran ou en recouvre un autre."""
        H = float(self.height); ech = H / 800.0
        gr = []
        for lo, hi in sorted(intervalles):
            if gr and lo - gr[-1][1] < 60.0: gr[-1][1] = max(gr[-1][1], hi)
            else: gr.append([lo, hi])
        modes = ['bas' if (lo + hi) / 2 < -100 else 'haut' if (lo + hi) / 2 > 100 else 'centre' for lo, hi in gr]
        def y(z, mode, s): return (z + 400.0) * s if mode == 'bas' else H - (400.0 - z) * s if mode == 'haut' else H / 2 + z * s
        kmax = min(UI_ZOOM, self.width / (450.0 * ech))
        k = kmax
        while k > 1.0:
            s = ech * k; iv = [(y(lo, m, s), y(hi, m, s)) for (lo, hi), m in zip(gr, modes)]
            if all(a >= -0.5 and b <= H + 0.5 for a, b in iv) and all(iv[i + 1][0] - iv[i][1] >= 8.0 for i in range(len(iv) - 1) if iv[i + 1][0] >= iv[i][0]): break
            k -= 0.01
        return max(k, 1.0), gr, modes

    def _dz_message(self, ports):
        """Fenetre de message du terrain : l'original la pose au-dessus de la zone des menus du bas (portrait) ; en 16/9 on la descend en bas de l'ecran,
        sauf si une autre fenetre occupe le bas (elle resterait dessous)."""
        m = self.ui_msg
        combat = self.moteur.etat.partie == MO.PARTIE_COMBAT          # combat : le message se pose au meme endroit que le menu de commandes (meme bord bas, meme echelle)
        if self.args.msg_origine or not m or (m.type != 0 and not combat): return 0.0
        b = m.bas()
        if any(self.ui_g.f[p].typ != 1 and self.ui_g.f[p].bas() < b - 2 for p in ports): return 0.0
        return (CB_MSG_BAS if combat else MSG_BAS) - b

    def _zones(self, port):
        """Zones tactiles de la fenetre d'un port : [(numero, manette, x0, y0, x1, y1, profondeur, identifiant de l'element)] en pixels."""
        fe = self.ui_g.f.get(port) if self.ui_g else None
        if not fe or self._cachee(fe.typ): return []
        cx, cy, ech = self.ui_tf.get(port) or self._ui_repere(); dz = getattr(self, 'ui_dzp', {}).get(port, 0.0)
        return [(b, pad, cx + x0 * ech, cy + (z0 + dz) * ech, cx + x1 * ech, cy + (z1 + dz) * ech, pr, nid) for b, pad, x0, z0, x1, z1, pr, nid in fe.boutons(True)]

    def _dessiner_menus(self):
        if self.pause.ouvert and self.pause.ecran == 'interface': return       # editeur d'interface : seul l'element choisi est montre (par le menu Echap), pas les fenetres du jeu
        mo = self.moteur
        actif = self._port_clavier(mo.menu_actif())
        if os.environ.get('DQ_UIDBG'):                      # (test) etat des fenetres a chaque changement : port, type, visible, fenetre d'origine ou menu simple
            etat = tuple(sorted((p, f['type'], f['vis'], p in (self.ui_g.f if self.ui_g else ()), len(f['cases'])) for p, f in mo.ui.f.items() if f['vis'] or f['type'] is not None))
            if etat != getattr(self, '_ui_etat', None):
                self._ui_etat = etat; print('UI image %d actif=%s : %s' % (self.n, actif, ' '.join('%d:t%s%s%s c%d' % (p, t, '' if v else '(cache)', '[O]' if o else '[simple]', c) for p, t, v, o, c in etat)), flush=True)
        if self.ui_rendu:
            liste = sorted((f['ordre'], p) for p, f in mo.ui.f.items() if f['vis'] and p in self.ui_g.f)
            if mo.etat.partie == MO.PARTIE_COMBAT and max(float(mo.etat.fondu['a']), float(mo.etat.fondu_fond['a'])) >= 0.6: liste = []       # fin de combat : le jeu ferme le fondu au noir alors que la fenetre de statut est encore « visible » (le message, lui, reste : « Ragnar meurt ! » se lit sur le noir) : sinon l'ecran noir montre une boite seule en haut a gauche
            if self.sauv is not None: liste = []                                 # ecran Sauvegardes ouvert : le menu de depart est cache (sinon il se devine a travers le cadre translucide)
            fens_v = [self.ui_g.f[p] for _, p in liste]; self.ui_rendu.voisins = fens_v
            for fe in fens_v:
                if fe.typ == 53: fe.centrer_menu(); fe.plaque_auto()          # menu de depart : groupe centre en hauteur, dans un cadre noir (dessine plus bas) ; plaque « Sauvegarde automatique » toujours visible, grisee et inactive sans data5.dat lisible
            cacher = self._boite_fin_combat()
            msg = bool(self.ui_msg and mo.msg_visible and 'msg' in self.ui_rendu.tex and not cacher)
            dz = self._dz_message([p for _, p in liste]) if msg else 0.0
            self.ui_dz = dz; self.ui_suit = {p for _, p in liste if self.ui_g.f[p].typ == 1} if msg else set()      # le Oui/Non (type 1) suit la fenetre de message (D-231 : toujours, a sa place d'origine ou descendue)
            self.ui_dzp = {}; ui_bords = {}                   # decalage vertical de chaque fenetre qui suit le message : le meme que lui, plus de quoi poser la pile Oui/Non sur le bord haut du message ; bords droits a aligner (D-231)
            for p in self.ui_suit:
                pose = self._ouinon_sur_message(self.ui_msg, self.ui_g.f[p]) if msg else None
                self.ui_dzp[p] = dz + (pose[0] if pose else 0.0); ui_bords[p] = pose[1] if pose else None
            ivs = {}
            for _, p in liste:
                e = self.ui_g.f[p].etendue()
                if e: ivs[p] = (e[0] + self.ui_dzp.get(p, 0.0), e[1] + self.ui_dzp.get(p, 0.0))
            if msg:
                e = self.ui_msg.etendue()
                if e: ivs['msg'] = (e[0] + dz, e[1] + dz)
            k, gr, modes = self._ui_echelle(list(ivs.values()) + ([CB_ZONE_MENUS] if self.moteur.etat.partie == MO.PARTIE_COMBAT else [])); self.ui_k = k       # combat : echelle constante (la zone des menus de commandes compte toujours), sinon les fenetres changent de taille a chaque message
            H = float(self.height); s = H / 800.0 * k; cx = self._ui_repere()[0]
            def mode_de(cle):                                 # 'bas', 'haut' ou 'centre' : bord de l'ecran auquel est collee la fenetre
                if cle not in ivs: return 'bas'
                lo, hi = ivs[cle]; i = next((j for j, g in enumerate(gr) if g[0] - 1e-6 <= lo and hi <= g[1] + 1e-6), 0); return modes[i] if modes else 'bas'
            def repere(cle):                                  # (cy, echelle) du groupe de fenetres qui contient cette fenetre
                m = mode_de(cle)
                return (400.0 * s if m == 'bas' else H - 400.0 * s if m == 'haut' else H / 2), s
            self.ui_tf = {p: (cx,) + repere(p) for _, p in liste}
            ov = self.reg['interface_fenetres']; tf_msg = None; perso = {}; ouinon = {}           # fenetres modifiees par le joueur (taille, position) : dessinees a part, avec leur propre repere (les zones tactiles le suivent)
            masque = set(self.reg['interface_masquees'])                                  # interfaces masquees (« Afficher cette interface a l'ecran » = Non) : calculees comme les autres (la mise en page ne bouge pas), seul leur dessin est omis
            if ov and msg and ov.get('msg'): tf_msg = self._ui_perso(mode_de('msg'), s, ov['msg'])
            for _, p in liste:
                fe1 = self.ui_g.f[p]
                if fe1.typ != 1: continue
                nom = self._nom_de_type(1) or ''; v = ov.get(nom) if (ov and nom not in RG.FENETRES_RETIREES) else None
                e1 = fe1.etendue()
                if not e1: continue
                if p in self.ui_suit:                                                        # Oui / Non : pose sur le coin haut droit de la boite de dialogue (reglages du joueur relatifs a celle-ci)
                    D = self.ui_dzp.get(p, 0.0); base = tf_msg or (cx, repere('msg')[0], s)
                    t2 = self._ui_ouinon(base, D, e1[0], v or RG.FENETRE_DEFAUT, ui_bords.get(p))
                    self.ui_tf[p] = (t2[0], t2[1] - D * t2[2], t2[2]); ouinon[p] = t2
                elif v:                                                                      # sans boite de dialogue : a sa place, avec les reglages du joueur
                    t2 = self._ui_ouinon((cx,) + repere(p), 0.0, e1[0], v); self.ui_tf[p] = (t2[0], t2[1], t2[2]); perso[p] = t2
            if ov:
                for _, p in liste:
                    if self.ui_g.f[p].typ == 1 or p in self.ui_suit: continue
                    nom = self._nom_de_type(self.ui_g.f[p].typ) or ''; v = ov.get(nom) if nom not in RG.FENETRES_RETIREES else None
                    if v: perso[p] = self.ui_tf[p] = self._ui_perso(mode_de(p), s, v)
            for _, p in liste:
                if self.ui_g.f[p].typ in FENETRES_CENTREES and p not in perso:         # liste des journaux, choix du sexe : centrees a l'ecran dans un cadre noir (les boites de dialogue, elles, restent a leur place)
                    c = self.ui_g.f[p].centre_visible()
                    if c: perso[p] = self.ui_tf[p] = (cx - c[0] * s, H / 2 - c[1] * s, s)
            for _, p in liste:
                if self.ui_g.f[p].typ == 25: self._plan_fenetre(self.ui_g.f[p], mo.ui.f[p])
                elif self.ui_g.f[p].typ == 26: self._plan_monde_fenetre(self.ui_g.f[p], mo.ui.f[p])
            haut, bas = ([self.ui_msg] if msg else []), {}
            for _, p in liste:
                fe = self.ui_g.f[p]
                fe.selection(self.appui[1] if self.appui and self.appui[0] == p else (self._curseur(p) if p == actif else None))
                if self.appui and self.appui[0] == p:           # appui en cours : l'element est sombre tant que le pointeur est dessus ; s'il en sort, plus rien (MenuPortItem.Update, etat 2 : SetPush(touche)), s'il revient, il se rassombrit
                    h = self._bouton_sous(p, *self.souris); sur = bool(h) and h[3] == self.appui_nd
                    fe.sel_nd = self.appui_nd if sur else -1; fe.appui_nd = self.appui_nd if sur else None
                else:
                    fe.appui_nd = None
                    fe.sel_nd = self.survol_nd[1] if self.survol_nd and self.survol_nd[0] == p else (-1 if self.survol_nd else None)       # souris : l'element pointe seul (-1 : fenetre non survolee, rien n'est allume par numero)
                if p in self.ui_suit: haut.append(fe)
                elif p not in perso: bas.setdefault(self.ui_tf[p][1], []).append(fe)
            for fe in haut:                                   # le message d'abord, puis chaque fenetre qui le suit (Oui/Non) a son propre decalage
                pf = next((p for _, p in liste if self.ui_g.f[p] is fe), None); dzf = self.ui_dzp.get(pf, dz)
                if ('msg' in masque) if pf is None else self._cachee(self.ui_g.f[pf].typ): continue
                if pf in ouinon: self.ui_rendu.dessiner([fe], ouinon[pf][0], ouinon[pf][1], ouinon[pf][2], (self.width, self.height))
                elif tf_msg: self.ui_rendu.dessiner([fe], tf_msg[0], tf_msg[1] + dzf * tf_msg[2], tf_msg[2], (self.width, self.height))
                else: self.ui_rendu.dessiner([fe], cx, repere('msg')[0] + dzf * s, s, (self.width, self.height))
            for cy, fens_g in bas.items():
                for fe in fens_g:
                    if fe.typ == 53: self._cadre_depart(fe, cx, cy, s)
                self.ui_rendu.dessiner([fe for fe in fens_g if not self._cachee(fe.typ)], cx, cy, s, (self.width, self.height))
            for p, tf in perso.items():
                if self._cachee(self.ui_g.f[p].typ): continue
                if self.ui_g.f[p].typ in FENETRES_CENTREES: self._cadre_depart(self.ui_g.f[p], tf[0], tf[1], tf[2], True)
                self.ui_rendu.dessiner([self.ui_g.f[p]], tf[0], tf[1], tf[2], (self.width, self.height))
            self._ancrer_vitesse_combat(liste, msg, dz, s, cx, repere, tf_msg)
        fens = [(p, f) for p, f in mo.ui.visibles() if not (self.ui_g and p in self.ui_g.f)]
        if not fens: return
        ech = self.height / 720.0; W, H = self.width, self.height
        taille = 17 * ech; rh = 36 * ech; pad = 16 * ech; gap = 18 * ech
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        x_main = 40 * ech
        for port, f in fens:
            lignes = self._lignes_menu(f)
            if not lignes: continue
            # largeur : texte le plus large + zone etiquette/valeur
            largeur_g = max(self._etiq(l[1], taille).content_width for l in lignes)
            def pile(l): return bool((l[2] and '\n' in l[2]) or (l[3] and '\n' in l[3]))        # etiquettes/valeurs sur plusieurs lignes (PV / PM / Nv.)
            def larg_bloc(l):
                if pile(l):
                    wl = max([self._etiq(t, taille * 0.8).content_width for t in (l[2] or '').split('\n')] + [0]); wv = max([self._etiq(t, taille).content_width for t in (l[3] or '').split('\n')] + [0])
                    return wl + 10 * ech + wv
                return max(self._etiq(l[2], taille * 0.8).content_width if l[2] else 0, self._etiq(l[3], taille).content_width if l[3] else 0)
            largeur_d = max([larg_bloc(l) for l in lignes] + [0])
            hauts = [rh * (0.3 + 0.62 * max(len((l[2] or '').split('\n')), len((l[3] or '').split('\n'))) if pile(l) else (1.5 if (l[2] and l[3]) else 1)) for l in lignes]
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
                if pile((idx, gauche, lab, val, titre)):
                    labs, vals = (lab or '').split('\n'), (val or '').split('\n')
                    wv = max([self._etiq(t, taille).content_width for t in vals] + [0]); wl = max([self._etiq(t, taille * 0.8).content_width for t in labs] + [0])
                    for i in range(max(len(labs), len(vals))):
                        yy = cy - rh * 0.62 * (i + 1) - rh * 0.05
                        if i < len(vals): e = self._etiq(vals[i], taille); e.x = x + w - pad - e.content_width; e.y = yy; e.draw()
                        if i < len(labs): e = self._etiq(labs[i], taille * 0.8); e.x = x + w - pad - wv - 10 * ech - wl; e.y = yy; e.draw()
                    gy = cy - rh * 0.62 - rh * 0.05
                elif lab and val:
                    base = cy - rh * 0.72
                    e = self._etiq(lab, taille * 0.8); e.x = x + w - pad - e.content_width; e.y = base; e.draw()
                    e = self._etiq(val, taille); e.x = x + w - pad - e.content_width; e.y = base - rh * 0.5; e.draw()
                    gy = cy - rh * 0.95
                elif val:
                    e = self._etiq(val, taille); e.x = x + w - pad - e.content_width; e.y = base; e.draw(); gy = base
                else: gy = base
                e = self._etiq(gauche, taille, (255, 235, 130, 255) if titre else (255, 255, 255, 255)); e.x = x + pad + (0 if titre else 26 * ech); e.y = gy if not (lab and val) or pile((idx, gauche, lab, val, titre)) else cy - rh * 0.72 - rh * 0.25; e.draw()
                if not titre and port == actif and idx == f['cur']:
                    ty = (cy - hl / 2) if not (lab and val) else cy - rh * 0.6
                    pyglet.shapes.Triangle(x + pad, ty + 9 * ech, x + pad, ty - 9 * ech, x + pad + 15 * ech, ty, color=(255, 235, 130)).draw()
                cy -= hl

    def _dessiner_aide(self):
        """Lignes d'information (F1), en haut a droite par defaut. Dessinees aussi pendant les ecrans noirs et l'effet de debut de combat : sans cela elles clignotent a chaque changement de scene."""
        if not self.aide: self.aide_larg = 0.0; return
        self._infos()
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        stats = self.stats and bool(self.ecarts)
        if stats:
            if self.n % 10 == 0 or not self.etiq_stats.text: self.etiq_stats.text = tr('%.0f images/s | moteur %.1f pas/s (%.1f ms) | pire image %.0f ms | dessin Python %.1f ms') % (len(self.ecarts) / max(1e-6, sum(self.ecarts)), (len(self.pas_t) - 1) / max(1e-6, self.pas_t[-1] - self.pas_t[0]) if len(self.pas_t) > 2 else 0.0, self.dt_moteur * 1000, max(self.ecarts) * 1000, self.dt_dessin * 1000)
        lignes = [self.etiquette, self.etiq_hd] + ([self.etiq_stats] if stats else [])
        cote, marge = self._marge_aide()
        if (cote, marge) != self.aide_cle: self.aide_cle = (cote, marge); self.aide_larg = 0.0          # (fenetre redimensionnee, plein ecran, autre disposition : la largeur est recalculee)
        y = self.height - 10
        for l in lignes:                                 # lignes d'information empilees, a la ligne dans la marge laissee libre par la colonne d'interface
            if l.width != marge: l.width = marge
            l.y = y; y -= l.content_height + 3
        bas = y - 3                                       # cadre noir translucide derriere le texte (lisible sur le decor)
        self.aide_larg = max(self.aide_larg, max(l.content_width for l in lignes) + 16)       # (la largeur ne fait que croitre tant que F1 reste affiche : le bord gauche du bloc, colle a droite, et le texte ne bougent pas quand un chiffre change)
        x0 = self.width - 4 - self.aide_larg if cote == 'droite' else 4
        self.cadre_aide.x, self.cadre_aide.y = x0, bas
        self.cadre_aide.width, self.cadre_aide.height = self.aide_larg, self.height - 4 - bas
        self.cadre_aide.draw()
        for l in lignes: l.x = x0 + 6; l.draw()
