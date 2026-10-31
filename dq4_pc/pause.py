"""Menu Echap : reprendre, etats instantanes (savestates), affichage, son, touches, quitter.

Pendant que le menu est ouvert le moteur est arrete (la scene reste affichee, assombrie). Navigation : fleches ou touches haut / bas / gauche / droite / A / B reglees,
Entree / Espace = valider, Echap / Retour arriere = retour, souris (survol, clic, clic droit = retour, molette). Les reglages sont enregistres dans reglages.json."""
import os, time
import pyglet
from pyglet import gl
import reglages as RG
import hd as HD
import hud_mobile as HM

NB_ETATS = 10
DELAI_REPETITION, PAS_REPETITION = 0.40, 0.07
OR = (255, 235, 130, 255); BLANC = (255, 255, 255, 255); GRIS = (150, 160, 160, 255); ROUGE = (255, 150, 140, 255)
ECHELLES_PP = (0, 1, 2, 4, 8)
MSAA_CHOIX = (0, 2, 4, 8)


class Pause:
    def __init__(self, jeu):
        self.J = jeu; self.ouvert = False; self.pile = []; self.sel = {}; self.capture = None; self.message = None
        self.zones = []; self.barres = {}; self.zones_val = {}; self.zones_col = 0.0; self.minis = {}; self.rep = None; self.veut_miniature = False; self.mini_tex = None; self.confirme = None
        self.placement = False                            # placement des boutons a l'ecran (grille) a la place du menu
        self.glisse = None; self.saisie = None            # curseur maintenu par la souris (numero de ligne) ; valeur en cours de saisie [ligne, texte]

    # ---- ouverture / fermeture
    def ouvrir(self):
        if self.ouvert: return
        self.ouvert = True; self.pile = ['racine']; self.sel = {}; self.capture = None; self.message = None; self.confirme = None
        self.veut_miniature = True; self.minis = {}; self.rep = None; self.glisse = None; self.saisie = None; self.placement = False
        self.J.pause_jeu(True)

    def fermer(self):
        if not self.ouvert: return
        self.ouvert = False; self.capture = None; self.glisse = None; self.saisie = None; self.placement = False; self.J.reg.enregistrer(); self.J.pause_jeu(False)
        if self.mini_tex is not None:
            try: self.mini_tex.delete()
            except Exception: pass
            self.mini_tex = None

    @property
    def ecran(self): return self.pile[-1]

    def retour(self):
        if len(self.pile) > 1: self.pile.pop()
        else: self.fermer()

    # ---- entrees des ecrans : liste de dicts {'t': 'act'|'choix'|'curs'|'touche'|'sep', 'l': libelle, 'v': valeur affichee, 'ok', 'moins', 'plus', 'off'}
    def _entrees(self):
        return getattr(self, '_e_' + self.ecran)()

    def _aller(self, nom):
        return lambda: self.pile.append(nom)

    def _e_racine(self):
        return [dict(t='act', l='Reprendre', ok=self.fermer),
                dict(t='act', l='Sauvegarder un état', ok=self._aller('sauver')),
                dict(t='act', l='Charger un état', ok=self._aller('charger')),
                dict(t='act', l='Affichage', ok=self._aller('affichage')),
                dict(t='act', l='Jeu', ok=self._aller('jeu')),
                dict(t='act', l='Boutons à l\'écran', ok=self._aller('boutons')),
                dict(t='act', l='Son', ok=self._aller('son')),
                dict(t='act', l='Touches', ok=self._aller('touches')),
                dict(t='act', l='Quitter le jeu', ok=self._aller('quitter'))]

    def _choix(self, label, valeurs, get, set_, off=False):
        """Entree a valeurs en liste : gauche / droite (ou valider) passent a la precedente / suivante."""
        def pas(d):
            i = (valeurs.index(get()) + d) % len(valeurs) if get() in valeurs else 0
            set_(valeurs[i])
        return dict(t='choix', l=label, vals=valeurs, v=lambda: self._nom_valeur(label, get()), moins=lambda: pas(-1), plus=lambda: pas(1), ok=lambda: pas(1), off=off)

    def _valeurs(self, en): return en['vals']

    def _nom_valeur(self, label, v):
        n = self.noms.get(label, {}).get(v)
        if n is not None: return n
        if isinstance(v, bool): return 'Oui' if v else 'Non'
        return '%d x %d' % v if isinstance(v, tuple) else str(v)

    def _curs(self, label, get, appliquer, mini, maxi, pas, pas_f, fmt, mult=1.0):
        """Curseur numerique de `mini` a `maxi` (valeurs arrondies a `pas`, fleches : `pas_f`). Cliquer sur la valeur ou valider permet de la saisir au clavier : `mult` = facteur entre la valeur
        interne et celle qui est affichee et saisie (100 pour des pourcentages)."""
        def pose(v): appliquer(min(maxi, max(mini, round(round(v / pas) * pas, 4))))
        return dict(t='curs', l=label, v=lambda: fmt(get()), frac=lambda: (get() - mini) / (maxi - mini), moins=lambda: pose(get() - pas_f), plus=lambda: pose(get() + pas_f),
                    fixe=lambda f: pose(mini + f * (maxi - mini)), saisie=lambda x: pose(x / mult), brut=lambda: ('%g' % round(get() * mult, 2)))

    noms = {
        'Sprites': {0: 'Originaux (pixels nets)', 1: 'EPX x8', 2: 'Régions lissées', 3: 'Bicubique', 4: 'Pixel perfect'},
        'Échelle pixel perfect (carte)': {0: 'Automatique', 1: 'x1', 2: 'x2', 4: 'x4', 8: 'x8'},
        'Lissage des textures': {True: 'Oui', False: 'Non'}, 'Plein écran': {True: 'Oui', False: 'Non'},
        'Anticrénelage (au prochain lancement)': {0: 'Aucun', 2: 'x2', 4: 'x4', 8: 'x8'},
        'Infos à l\'écran (F1)': {True: 'Oui', False: 'Non'}, 'Son': {True: 'Oui', False: 'Non'},
    }

    def _e_affichage(self):
        J, R = self.J, self.J.reg
        def set_(k, f=None):
            def s(v):
                R[k] = v
                if f: f(v)                 # (les reglages sont enregistres a la fermeture du menu)
            return s
        e = [self._choix('Sprites', list(range(len(HD.MODES) + 1)), lambda: J.mode, set_('mode_sprites', J.regler_mode)),
             self._choix('Échelle pixel perfect (carte)', list(ECHELLES_PP), lambda: R['echelle_pp'], set_('echelle_pp', J.regler_echelle_pp)),
             self._choix('Lissage des textures', [True, False], lambda: J.lissage, set_('lissage', J.regler_lissage)),
             self._curs('Zoom de la carte du monde', lambda: J.champ_zoom, lambda v: (set_('zoom_carte', J.regler_zoom)(v)), 0.4, 4.0, 0.01, 0.1, lambda v: '%d %%' % round(v * 100), 100.0),
             self._choix('Résolution', J.resolutions(), J.resolution_courante, lambda v: (J.regler_resolution(v), R.__setitem__('resolution', list(v)))),
             self._curs('Angle de la caméra des villes', lambda: R['angle_camera'], lambda v: (R.__setitem__('angle_camera', v), J.regler_angle(v)), -20.0, 40.0, 1.0, 1.0, lambda v: '%+d °' % round(v) if round(v) else '0 °', 1.0),
             self._choix('Plein écran', [False, True], lambda: J.est_plein, set_('plein_ecran', J.regler_plein_ecran)),
             self._choix('Anticrénelage (au prochain lancement)', list(MSAA_CHOIX), lambda: R['msaa'], set_('msaa')),
             self._choix('Infos à l\'écran (F1)', [False, True], lambda: J.aide, set_('infos', J.regler_infos)),
             dict(t='act', l='Retour', ok=self.retour)]
        return e

    def _e_jeu(self):
        R = self.J.reg
        return [self._curs('Vitesse de déplacement', lambda: R['vitesse_marche'], lambda v: R.__setitem__('vitesse_marche', v), 0.5, 3.0, 0.05, 0.1, lambda v: 'x%.2f' % v, 1.0),
                self._choix('Course (maintenir la touche)', [True, False], lambda: R['course'], lambda v: R.__setitem__('course', v)),
                self._curs('Vitesse de la course', lambda: R['vitesse_course'], lambda v: R.__setitem__('vitesse_course', v), 1.2, 4.0, 0.05, 0.1, lambda v: 'x%.2f' % v, 1.0),
                self._curs('Taille des nombres de dégâts', lambda: R['taille_degats'], lambda v: R.__setitem__('taille_degats', v), 0.5, 3.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0),
                self._choix('Molette des menus : sens inversé', [True, False], lambda: R['molette_inversee'], lambda v: R.__setitem__('molette_inversee', v)),
                dict(t='act', l='Retour', ok=self.retour)]

    def _e_boutons(self):
        R = self.J.reg; H = self.J.hud
        return [self._choix('Boutons à l\'écran (Carte, Commandes, Discussion)', [True, False], lambda: R['boutons'], lambda v: R.__setitem__('boutons', v)),
                self._curs('Taille des boutons', lambda: R['boutons_taille'], lambda v: R.__setitem__('boutons_taille', v), 0.5, 2.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0),
                self._choix('Aimantation à la grille', [True, False], lambda: R['boutons_aimant'], lambda v: R.__setitem__('boutons_aimant', v)),
                dict(t='act', l='Placer les boutons sur la grille…', ok=lambda: setattr(self, 'placement', True)),
                dict(t='act', l='Rétablir les positions d\'origine', ok=H.remettre),
                dict(t='act', l='Retour', ok=self.retour)]

    def _e_son(self):
        J, R = self.J, self.J.reg
        return [self._choix('Son', [True, False], lambda: J.son.actif, lambda v: (J.regler_son(v), R.__setitem__('son', v))),
                self._curs('Volume de la musique', lambda: R['volume_musique'], lambda v: (R.__setitem__('volume_musique', v), J.regler_vol_musique(v)), 0.0, 1.0, 0.01, 0.05, lambda v: '%d %%' % round(v * 100), 100.0),
                self._curs('Volume des bruitages', lambda: R['volume_bruitages'], lambda v: (R.__setitem__('volume_bruitages', v), J.regler_vol_bruitages(v)), 0.0, 1.0, 0.01, 0.05, lambda v: '%d %%' % round(v * 100), 100.0),
                dict(t='act', l='Retour', ok=self.retour)]

    def _e_touches(self):
        R = self.J.reg; e = []
        for act, lib in RG.ACTIONS:
            e.append(dict(t='touche', l=lib, act=act, v=[RG.nom_touche(n) for n in R['touches'][act]]))
        e.append(dict(t='act', l='Rétablir les touches par défaut', ok=lambda: (R.touches_par_defaut(), R.enregistrer())))
        e.append(dict(t='act', l='Retour', ok=self.retour))
        return e

    def _chemin_etat(self, n): return self.J.chemin_etat(n)

    def _e_etats(self, ecriture):
        e = []
        for n in range(1, NB_ETATS + 1):
            inf = self.J.infos_etat(n)
            if inf: lib = inf[0].get('lieu', '?'); val = inf[0].get('date', '')[5:16].replace('-', '/', 1) if inf[0].get('date') else ''
            else: lib = '— vide —'; val = ''
            if ecriture: e.append(dict(t='slot', l=lib, v=val, n=n, off=False, ok=(lambda n=n: self._sauver(n))))
            else: e.append(dict(t='slot', l=lib, v=val, n=n, off=inf is None, ok=(lambda n=n: self._charger(n))))
        e.append(dict(t='act', l='Retour', ok=self.retour))
        return e

    def _e_sauver(self): return self._e_etats(True)
    def _e_charger(self): return self._e_etats(False)

    def _e_quitter(self):
        return [dict(t='sep', l='Quitter le jeu ?'), dict(t='act', l='Non, revenir', ok=self.retour), dict(t='act', l='Oui, quitter', ok=self.J.quitter)]

    # ---- actions
    def _info(self, texte, erreur=False): self.message = (texte, time.time(), erreur)

    def _sauver(self, n):
        try:
            self.J.sauver_etat(n, self.J._png_miniature(self.mini_tex))
            self.minis.pop(n, None); self._info('État enregistré dans l\'emplacement %d.' % n)
        except Exception as ex:
            self._info('Impossible d\'enregistrer l\'état : %r' % (ex,), True)

    def _charger(self, n):
        try:
            self.J.charger_etat(n); self.fermer()
        except Exception as ex:
            self._info('Impossible de charger l\'état : %r' % (ex,), True)

    # ---- touches clavier
    def touche(self, symbol, modifiers=0):
        """True si la touche est consommee (le menu est ouvert)."""
        K = pyglet.window.key; R = self.J.reg
        if self.capture is not None: self._capturer(symbol); return True
        if self.saisie is not None: self._touche_saisie(symbol); return True
        if self.placement:
            if symbol in (K.ESCAPE, K.RETURN, K.ENTER, K.SPACE, K.BACKSPACE): self.placement = False; R.enregistrer()
            return True
        act = R.action_de(symbol)
        if symbol in (K.ESCAPE, K.BACKSPACE) or act == 'B': self.retour(); return True
        if symbol == K.F1: self.J.regler_infos(not self.J.aide); R['infos'] = self.J.aide; return True
        if symbol in (K.UP,) or act == 'haut': self._bouger(-1); self.rep = (symbol, time.time(), time.time(), 'v', -1)
        elif symbol in (K.DOWN,) or act == 'bas': self._bouger(1); self.rep = (symbol, time.time(), time.time(), 'v', 1)
        elif symbol in (K.LEFT,) or act == 'gauche': self._regler(-1); self.rep = (symbol, time.time(), time.time(), 'h', -1)
        elif symbol in (K.RIGHT,) or act == 'droite': self._regler(1); self.rep = (symbol, time.time(), time.time(), 'h', 1)
        elif symbol in (K.RETURN, K.ENTER, K.SPACE) or act == 'A': self._valider()
        return True

    def maj(self):
        """Repetition des directions maintenues (appelee a chaque image)."""
        if not self.rep: return
        sym, t0, tl, sens, d = self.rep; t = time.time()
        if not self.J.touches[sym]: self.rep = None; return
        if t - t0 > DELAI_REPETITION and t - tl > PAS_REPETITION:
            self.rep = (sym, t0, t, sens, d)
            if sens == 'v': self._bouger(d)
            else: self._regler(d)

    def _bouger(self, d):
        e = self._entrees(); n = len(e)
        if not n: return
        i = self.sel.get(self.ecran, 0)
        for _ in range(n):
            i = (i + d) % n
            if e[i]['t'] != 'sep': break
        self.sel[self.ecran] = i

    def _courante(self):
        e = self._entrees(); i = min(self.sel.get(self.ecran, 0), len(e) - 1)
        if e and e[i]['t'] == 'sep':
            self._bouger(1); i = self.sel.get(self.ecran, 0)
        return e[i] if e else None

    def _regler(self, d):
        en = self._courante()
        if not en: return
        if en['t'] in ('choix', 'curs'): (en['moins'] if d < 0 else en['plus'])()
        elif en['t'] == 'touche':
            c = self.sel.get('col', 0); self.sel['col'] = min(1, max(0, c + d))

    def _valider(self):
        en = self._courante()
        if not en or en.get('off'): return
        if en['t'] == 'touche': self.capture = (en['act'], self.sel.get('col', 0)); return
        if en['t'] == 'curs': self.saisie = [self.sel.get(self.ecran, 0), '']
        elif 'ok' in en: en['ok']()

    def _capturer(self, symbol):
        K = pyglet.window.key; R = self.J.reg; act, col = self.capture
        if symbol == K.ESCAPE: self.capture = None; return
        if symbol in (K.DELETE, K.BACKSPACE): R.delier(act, col); self.capture = None; R.enregistrer(); return
        if RG.nom_de(symbol) in RG.RESERVEES: self._info('Cette touche est réservée (%s).' % RG.nom_touche(RG.nom_de(symbol)), True); return
        avait = R.lier(act, col, symbol); self.capture = None; R.enregistrer()
        if avait and avait != act: self._info('%s retirée de « %s ».' % (RG.nom_touche(RG.nom_de(symbol)), dict(RG.ACTIONS)[avait].split(' :')[0]))

    # ---- souris
    def _zone(self, x, y):
        for (x0, y0, x1, y1, i) in self.zones:
            if x0 <= x <= x1 and y0 <= y <= y1: return i, (x - x0) / max(1.0, x1 - x0)
        return None, 0.0

    def survol(self, x, y):
        if self.capture is not None or self.placement: return
        i, _ = self._zone(x, y)
        if i is not None: self.sel[self.ecran] = i

    def clic(self, x, y, bouton):
        M = pyglet.window.mouse
        if self.placement:
            if bouton == M.RIGHT: self.placement = False; self.J.reg.enregistrer()
            else: self.J.hud.prendre(x, y)
            return
        if self.capture is not None: self.capture = None; return
        if bouton == M.RIGHT:
            if self.saisie is not None: self.saisie = None
            else: self.retour()
            return
        i, f = self._zone(x, y)
        if self.saisie is not None:                                   # un clic ailleurs que sur la valeur en cours de saisie la valide
            ligne = self.saisie[0]; zv = self.zones_val.get(ligne)
            if i == ligne and zv and zv[0] <= x <= zv[1]: return
            self._fin_saisie(True)
        if i is None: return
        self.sel[self.ecran] = i; en = self._entrees()[i]
        bar = self.barres.get(i)
        zv = self.zones_val.get(i)
        if en['t'] == 'curs' and bar and bar[0] - 6 <= x <= bar[1] + 6:       # curseur : le clic maintenu le fait glisser (glisser)
            self.glisse = i; en['fixe'](min(1.0, max(0.0, (x - bar[0]) / (bar[1] - bar[0]))))
        elif en['t'] == 'curs' and zv and zv[0] - 8 <= x <= zv[1] + 8: self.saisie = [i, '']     # clic sur la valeur : saisie au clavier
        elif en['t'] == 'touche':
            col = 1 if x > self.zones_col else 0; self.sel['col'] = col; self._valider()
        else: self._valider()

    def relache(self, x, y, bouton):
        self.glisse = None
        if self.placement: self.J.hud.poser(); self.J.reg.enregistrer()

    def glisser(self, x, y):
        """Souris deplacee bouton enfonce : le curseur maintenu suit."""
        if self.placement: self.J.hud.deplacer(x, y); return
        if self.glisse is None: return
        bar = self.barres.get(self.glisse); e = self._entrees()
        if bar is None or self.glisse >= len(e) or e[self.glisse]['t'] != 'curs': self.glisse = None; return
        e[self.glisse]['fixe'](min(1.0, max(0.0, (x - bar[0]) / (bar[1] - bar[0]))))

    def texte(self, t):
        """Caracteres tapes pendant la saisie d'une valeur."""
        if self.saisie is None: return
        for c in t.replace(',', '.'):
            if (c.isdigit() or (c in '.-' and c not in self.saisie[1])) and len(self.saisie[1]) < 7: self.saisie[1] += c

    def _touche_saisie(self, symbol):
        K = pyglet.window.key
        if symbol in (K.RETURN, K.ENTER): self._fin_saisie(True)
        elif symbol == K.ESCAPE: self._fin_saisie(False)
        elif symbol == K.BACKSPACE:
            if self.saisie[1]: self.saisie[1] = self.saisie[1][:-1]
            else: self._fin_saisie(False)

    def _fin_saisie(self, valide):
        ligne, txt = self.saisie; self.saisie = None
        if not valide or txt in ('', '-', '.'): return
        e = self._entrees()
        if ligne < len(e) and e[ligne]['t'] == 'curs' and 'saisie' in e[ligne]:
            try: e[ligne]['saisie'](float(txt))
            except ValueError: pass

    def molette(self, sy):
        if self.placement: return
        d = -1 if sy > 0 else 1
        if self.J.reg['molette_inversee']: d = -d
        self._bouger(d)

    # ---- dessin
    def _miniature(self, n):
        """Texture de la miniature d'un etat (None s'il n'y en a pas)."""
        if n in self.minis: return self.minis[n]
        t = None; inf = self.J.infos_etat(n)
        if inf and inf[1]:
            try:
                import io
                from PIL import Image
                import numpy as np
                im = Image.open(io.BytesIO(inf[1])).convert('RGBA'); a = np.asarray(im)
                t = pyglet.image.ImageData(im.width, im.height, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=im.width * 4).get_texture()
            except Exception: t = None
        self.minis[n] = t
        return t

    def dessiner(self):
        J = self.J; W, H = J.width, J.height; k = max(0.75, H / 900.0)
        if self.placement:
            J.hud.dessiner(HM.NOMS, True)
            gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            et = J._etiq('Glisse les boutons pour les placer    Échap, Entrée ou clic droit : terminer', 16 * k, (255, 255, 255, 255)); w = et.content_width + 28 * k; h = 36 * k
            r = pyglet.shapes.Rectangle((W - w) / 2, H - 24 * k - h, w, h, color=(0, 0, 0)); r.opacity = 190; r.draw(); et.x = (W - et.content_width) / 2; et.y = H - 24 * k - h + 11 * k; et.draw()
            return
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        voile = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); voile.opacity = 150; voile.draw()
        ecr = self.ecran; e = self._entrees(); n = len(e); i_sel = min(self.sel.get(ecr, 0), max(0, n - 1))
        fs, fst, fsp = 18 * k, 24 * k, 13 * k; pad = 30 * k
        titres = {'racine': 'Pause', 'affichage': 'Affichage', 'jeu': 'Jeu', 'son': 'Son', 'boutons': 'Boutons à l\'écran', 'touches': 'Touches', 'sauver': 'Sauvegarder un état', 'charger': 'Charger un état', 'quitter': 'Quitter'}
        avec_mini = ecr in ('sauver', 'charger')
        aide = {'touches': 'Entrée : changer la touche    ←/→ : colonne    Suppr : effacer', 'sauver': 'Entrée : enregistrer ici (écrase l\'état)', 'charger': 'Entrée : charger cet état',
                'affichage': 'Curseurs : glisser, ←/→, ou cliquer sur la valeur pour la taper (Entrée valide)', 'son': 'Curseurs : glisser, ←/→, ou cliquer sur la valeur pour la taper (Entrée valide)',
                'jeu': 'Curseurs : glisser, ←/→, ou cliquer sur la valeur pour la taper (Entrée valide)', 'boutons': 'Les boutons n\'apparaissent que hors combat, quand le jeu les autorise (comme sur le téléphone)'}.get(ecr, '')
        if self.saisie is not None: aide = 'Tape la valeur (Entrée : valider, Échap : annuler)'
        if self.capture is not None:
            act = dict(RG.ACTIONS)[self.capture[0]]; aide = 'Appuie sur la touche pour « %s »    (Échap : annuler, Suppr : effacer)' % act
        msg = self.message[0] if self.message and time.time() - self.message[1] < 4.0 else ''
        # largeur : le plus long libelle + la place des valeurs / curseurs / colonnes de touches
        lw = max([J._etiq(x['l'], fs).content_width for x in e] + [0.0]); vw = 0.0
        for x in e:
            if x['t'] == 'choix': vw = max(vw, max(J._etiq('‹  ' + self._nom_valeur(x['l'], v) + '  ›', fs).content_width for v in self._valeurs(x)))
        pw = max(540 * k, 52 * k + lw + 40 * k + vw + 30 * k)
        if ecr in ('affichage', 'son', 'jeu', 'boutons'): pw = max(pw, 52 * k + lw + 40 * k + 200 * k + 20 * k + 90 * k + 30 * k)
        if ecr == 'touches': pw = max(pw, 52 * k + lw + 40 * k + 2 * 190 * k + 30 * k)
        if ecr in ('sauver', 'charger'): pw = max(pw, 52 * k + lw + 30 * k + 150 * k)
        pied = 36 * k if aide else 0.0                     # (le message d'information est dessine sous le cadre : il ne decale rien)
        hmax = H - 2 * 36 * k; h_titre = 78 * k + (22 * k if ecr == 'touches' else 0.0)
        rh = max(34 * k, min(52 * k, (hmax - h_titre - pad / 2 - pied) / max(1, n))); h = min(hmax, h_titre + n * rh + pad / 2 + pied)
        wmini = 360 * k if avec_mini else 0.0; gap = 24 * k if avec_mini else 0.0
        x0 = (W - pw - wmini - gap) / 2; y1 = (H + h) / 2; y0 = y1 - h
        cadre = pyglet.shapes.BorderedRectangle(x0, y0, pw, h, border=max(2, int(3 * k)), color=(6, 22, 24), border_color=(240, 240, 240)); cadre.opacity = 238; cadre.draw()
        e_t = J._etiq(titres.get(ecr, ''), fst, OR); e_t.x = x0 + (pw - e_t.content_width) / 2; e_t.y = y1 - 52 * k; e_t.draw()
        visibles = max(1, int((h - h_titre - pad / 2 - pied) / rh + 0.02)); debut = 0               # defilement : les lignes qui ne tiennent pas sont decalees pour garder la selection visible
        if n > visibles: debut = min(max(0, i_sel - visibles // 2), n - visibles)
        self.zones = []; self.barres = {}; self.zones_val = {}; c1x = x0 + pw - 30 * k - 2 * 190 * k; self.zones_col = c1x + 190 * k - 8 * k
        if ecr == 'touches':
            for c in range(2):
                eh = J._etiq('Touche %d' % (c + 1), fsp, GRIS); eh.x = c1x + c * 190 * k; eh.y = y1 - h_titre + 6 * k; eh.draw()
        y = y1 - h_titre
        for idx in range(debut, min(n, debut + visibles)):
            en = e[idx]; ytop = y; ybas = y - rh; sel = idx == i_sel and en['t'] != 'sep'
            if sel:
                bar = pyglet.shapes.Rectangle(x0 + 12 * k, ybas + 3 * k, pw - 24 * k, rh - 6 * k, color=(255, 255, 255)); bar.opacity = 46; bar.draw()
                tri = pyglet.shapes.Triangle(x0 + 22 * k, ybas + rh / 2 + 9 * k, x0 + 22 * k, ybas + rh / 2 - 9 * k, x0 + 22 * k + 15 * k, ybas + rh / 2, color=(255, 235, 130)); tri.draw()
            coul = GRIS if en.get('off') else (OR if sel else BLANC)
            base = ybas + (rh - fs * 1.33) / 2 + 5 * k
            if en['t'] == 'sep': coul = OR
            lx = x0 + 52 * k
            if en['t'] == 'slot':
                nu = J._etiq('%d' % en['n'], fs, coul); nu.x = lx; nu.y = base; nu.draw(); lx += 44 * k
            lab = J._etiq(en['l'], fs, coul); lab.x = lx; lab.y = base; lab.draw()
            if en['t'] == 'choix':
                txt = en['v'](); vl = J._etiq('‹  ' + txt + '  ›' if sel else txt, fs, coul); vl.x = x0 + pw - 30 * k - vl.content_width; vl.y = base; vl.draw()
            elif en['t'] == 'curs':
                if self.saisie is not None and self.saisie[0] == idx: txt = (self.saisie[1] + ('_' if int(time.time() * 2) % 2 == 0 else ' ')).rjust(3)
                else: txt = en['v']()
                vl = J._etiq(txt, fs, OR if self.saisie is not None and self.saisie[0] == idx else coul); vl.x = x0 + pw - 30 * k - vl.content_width; vl.y = base; vl.draw()
                self.zones_val[idx] = (vl.x - 10 * k, x0 + pw - 30 * k + 10 * k)
                bw = 200 * k; bx1 = x0 + pw - 30 * k - 90 * k - 20 * k; bx0 = bx1 - bw; by = ybas + rh / 2 - 5 * k; self.barres[idx] = (bx0, bx1)
                fond = pyglet.shapes.Rectangle(bx0, by, bw, 10 * k, color=(70, 82, 82)); fond.draw()
                rem = pyglet.shapes.Rectangle(bx0, by, bw * max(0.0, min(1.0, en['frac']())), 10 * k, color=(255, 235, 130)); rem.draw()
                cur = pyglet.shapes.Rectangle(bx0 + bw * max(0.0, min(1.0, en['frac']())) - 3 * k, by - 4 * k, 6 * k, 18 * k, color=(255, 255, 255)); cur.draw()
            elif en['t'] == 'slot':
                if en['v']: vl = J._etiq(en['v'], fsp * 1.2, GRIS); vl.x = x0 + pw - 24 * k - vl.content_width; vl.y = base; vl.draw()
            elif en['t'] == 'touche':
                for c in range(2):
                    txt = en['v'][c]; actif = sel and self.sel.get('col', 0) == c
                    if self.capture is not None and self.capture == (en['act'], c): txt = '…'
                    cx = c1x + c * 190 * k
                    if actif:
                        r = pyglet.shapes.BorderedRectangle(cx - 8 * k, ybas + 6 * k, 180 * k, rh - 12 * k, border=max(1, int(2 * k)), color=(255, 255, 255), border_color=(255, 235, 130)); r.opacity = 60; r.draw()
                    vl = J._etiq(txt, fs * 0.92, OR if actif else (BLANC if en['v'][c] != RG.nom_touche(None) else GRIS)); vl.x = cx; vl.y = base; vl.draw()
            self.zones.append((x0 + 12 * k, ybas + 3 * k, x0 + pw - 12 * k, ytop - 3 * k, idx))
            y -= rh
        # pied du cadre : message d'information puis aide
        yp = y0 + 12 * k
        if aide:
            ea = J._etiq(aide, fsp, GRIS); ea.x = x0 + (pw - ea.content_width) / 2; ea.y = yp; ea.draw(); yp += 36 * k
        if msg:
            em = J._etiq(msg, fsp * 1.1, ROUGE if self.message[2] else OR); em.x = x0 + (pw - em.content_width) / 2; em.y = max(8 * k, y0 - 34 * k); em.draw()
        # miniature de l'etat survole
        if avec_mini:
            mx = x0 + pw + gap; mh = min(h, 270 * k)
            c2 = pyglet.shapes.BorderedRectangle(mx, y1 - h, wmini, h, border=max(2, int(3 * k)), color=(6, 22, 24), border_color=(240, 240, 240)); c2.opacity = 238; c2.draw()
            if e and e[i_sel]['t'] == 'slot':
                n_e = e[i_sel]['n']; t = self._miniature(n_e); inf = J.infos_etat(n_e)
                if t is not None:
                    w_i = wmini - 40 * k; h_i = w_i * t.height / t.width
                    spr = pyglet.sprite.Sprite(t, x=mx + 20 * k, y=y1 - 40 * k - h_i); spr.scale_x = w_i / t.width; spr.scale_y = h_i / t.height; spr.draw()
                    liste = []
                    if inf:
                        liste = [inf[0].get('lieu', ''), inf[0].get('date', ''), 'Image du moteur %s' % inf[0].get('images', '')]
                    for j, ligne in enumerate(liste):
                        el = J._etiq(ligne, fsp * 1.1, BLANC if j == 0 else GRIS); el.x = mx + 20 * k; el.y = y1 - 40 * k - h_i - 34 * k - j * 30 * k; el.draw()
                else:
                    el = J._etiq('Emplacement vide' if not inf else 'Pas de miniature', fs, GRIS); el.x = mx + (wmini - el.content_width) / 2; el.y = y1 - h / 2; el.draw()
