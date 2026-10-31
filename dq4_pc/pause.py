"""Menu Echap : reprendre, etats instantanes (savestates), affichage, son, commandes (vitesses, touches, interface), quitter.

Pendant que le menu est ouvert le moteur est arrete (la scene reste affichee, assombrie). Navigation : fleches ou touches haut / bas / gauche / droite / A / B reglees,
Entree / Espace = valider, Echap / Retour arriere = retour, souris (survol, clic, clic droit = retour, molette). Les reglages sont enregistres dans reglages.json."""
import math, os, time
import pyglet
from pyglet import gl
import reglages as RG
import hd as HD
import hud_mobile as HM

NB_ETATS = 9                 # emplacements d'etats instantanes (touches 1 a 9)
DELAI_REPETITION, PAS_REPETITION = 0.40, 0.07
# Palette de texte du jeu (MenuPortItemTable : blanc, jaune, rouge, gris) ; fenetres et boutons dans le style du menu des commandes du jeu mobile (voir hud_mobile.cadre et hud_mobile.plaque)
OR = (255, 235, 4, 255); BLANC = (255, 255, 255, 255); GRIS = (128, 128, 128, 255); AIDE = (170, 170, 170, 255); ROUGE = (255, 80, 80, 255)
JAUNE = OR[:3]
LARG_SW, HAUT_SW = 46.0, 24.0                    # interrupteur Oui / Non : taille a 900 px de haut (multipliee par k)
TAILLE_JEU = 1.0                                  # echelle des textes en police du jeu (par rapport aux polices du systeme)
MSAA_CHOIX = (0, 2, 4, 8)


class Pause:
    def __init__(self, jeu):
        self.J = jeu; self.ouvert = False; self.pile = []; self.sel = {}; self.capture = None; self.message = None
        self.zones = []; self.barres = {}; self.zones_val = {}; self.zones_col = 0.0; self.minis = {}; self.rep = None; self.veut_miniature = False; self.mini_tex = None; self.confirme = None
        self.cadre_panneau = None                          # (x0, y0, x1, y1) du cadre dessine a la derniere image (placement des boutons : un clic hors du cadre saisit un bouton)
        self.zones_def = {}                                # ligne -> (x0, y0, x1, y1) du bouton « valeur par defaut » des curseurs
        self.glisse = None; self.saisie = None            # curseur maintenu par la souris (numero de ligne) ; valeur en cours de saisie [ligne, texte]
        self.deroule = None; self.zones_pop = []          # liste deroulante ouverte [ligne, valeur survolee] ; zones de ses valeurs (x0, y0, x1, y1, numero)
        self.pos_sw = {}; self.t_sw = time.time(); self.dt_sw = 0.0         # interrupteurs : position du bouton (0 = Non, 1 = Oui) par libelle, pour l'animation
        self._pol = None                                  # familles de la police du jeu (None : pas encore cherchee)
        self.rep_pos = None                               # (ecran, ligne) sur lesquels la repetition d'une touche maintenue a commence

    def _et(self, texte, taille, couleur=BLANC):
        """Etiquette en police du jeu (GMaruGoPro-M, cache/ui_font.otf, enregistree au premier appel) ; a defaut, les polices du systeme."""
        if self._pol is None:
            self._pol = ()
            f = os.path.join(self.J.args.cache, 'ui_font.otf')
            if os.path.exists(f):
                try: pyglet.font.add_file(f); self._pol = ('FOT-GMaruGo Pro', 'FOT-GMaruGo Pro M', 'GMaruGoPro-M')
                except Exception as ex: print('police du jeu non chargee :', ex, flush=True)
        return self.J._etiq(texte, taille * (1.0 if not self._pol else TAILLE_JEU), couleur, self._pol)

    # ---- ouverture / fermeture
    def ouvrir(self):
        if self.ouvert: return
        self.ouvert = True; self.pile = ['racine']; self.sel = {}; self.capture = None; self.message = None; self.confirme = None
        self.veut_miniature = True; self.minis = {}; self.rep = None; self.glisse = None; self.saisie = None; self.deroule = None
        self.J.pause_jeu(True)

    def fermer(self):
        if not self.ouvert: return
        self.ouvert = False; self.capture = None; self.glisse = None; self.saisie = None; self.deroule = None; self.J.reg.enregistrer(); self.J.pause_jeu(False)
        if self.mini_tex is not None:
            try: self.mini_tex.delete()
            except Exception: pass
            self.mini_tex = None

    @property
    def ecran(self): return self.pile[-1]

    def retour(self):
        if self.ecran == 'placement': self.J.reg.enregistrer()                # fin du placement des boutons
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
                dict(t='act', l='Son', ok=self._aller('son')),
                dict(t='act', l='Commandes', ok=self._aller('commandes')),
                dict(t='act', l='Quitter le jeu', ok=self._aller('quitter'))]

    def _choix(self, label, valeurs, get, set_, off=False, note=None):
        """Entree a valeurs : Oui / Non = interrupteur (valider ou cliquer le bascule ; gauche = Non, droite = Oui) ; tout autre choix, meme a deux valeurs = liste deroulante
        (valider ou cliquer l'ouvre ; gauche / droite passent a la valeur precedente / suivante). `note` : fonction donnant un texte rouge affiche sous la valeur (ou '')."""
        sw = len(valeurs) == 2 and all(isinstance(v, bool) for v in valeurs)
        def pas(d):
            i = (valeurs.index(get()) + d) % len(valeurs) if get() in valeurs else 0
            set_(valeurs[i])
        def fixer(x):
            if get() != x: set_(x)
        if sw: moins, plus, ok = (lambda: fixer(False)), (lambda: fixer(True)), (lambda: set_(not get()))
        else: moins, plus, ok = (lambda: pas(-1)), (lambda: pas(1)), (lambda: pas(1))
        return dict(t='choix', l=label, vals=valeurs, v=lambda: self._nom_valeur(label, get()), moins=moins, plus=plus, ok=ok, off=off, get=get, set=set_, sw=sw, liste=not sw, note=note)

    def _valeurs(self, en): return en['vals']

    def _nom_valeur(self, label, v):
        n = self.noms.get(label, {}).get(v)
        if n is not None: return n
        if isinstance(v, bool): return 'Oui' if v else 'Non'
        return '%d x %d' % v if isinstance(v, tuple) else str(v)

    def _curs(self, label, get, appliquer, mini, maxi, pas, pas_f, fmt, mult=1.0, defaut=None):
        """Curseur numerique de `mini` a `maxi` (valeurs arrondies a `pas`, fleches : `pas_f`). Cliquer sur la valeur ou valider permet de la saisir au clavier : `mult` = facteur entre la valeur
        interne et celle qui est affichee et saisie (100 pour des pourcentages). `defaut` : valeur d'origine du reglage (bouton « valeur par defaut » a gauche du curseur, touche Suppr)."""
        def pose(v): appliquer(min(maxi, max(mini, round(round(v / pas) * pas, 4))))
        d = dict(t='curs', l=label, v=lambda: fmt(get()), frac=lambda: (get() - mini) / (maxi - mini), moins=lambda: pose(get() - pas_f), plus=lambda: pose(get() + pas_f),
                 fixe=lambda f: pose(mini + f * (maxi - mini)), saisie=lambda x: pose(x / mult), brut=lambda: ('%g' % round(get() * mult, 2)))
        if defaut is not None: d['defaut'] = lambda: pose(defaut); d['est_defaut'] = lambda: abs(get() - defaut) < pas / 2
        return d

    noms = {
        'Shader': {0: 'Originaux (pixels nets)', 1: 'EPX x8', 2: 'Régions lissées', 3: 'Bicubique', 4: 'Pixel perfect'},
        'Anticrénelage': {0: 'Aucun', 2: 'x2', 4: 'x4', 8: 'x8'},
    }

    def _e_affichage(self):
        J, R = self.J, self.J.reg
        def set_(k, f=None):
            def s(v):
                R[k] = v
                if f: f(v)                 # (les reglages sont enregistres a la fermeture du menu)
            return s
        return [self._choix('Plein écran', [False, True], lambda: J.est_plein, set_('plein_ecran', J.regler_plein_ecran)),
                self._choix('Résolution', J.resolutions(), J.resolution_courante, lambda v: (J.regler_resolution(v), R.__setitem__('resolution', list(v)))),
                self._choix('Shader', list(range(len(HD.MODES) + 1)), lambda: J.mode, set_('mode_sprites', J.regler_mode)),
                self._choix('Lissage des textures', [True, False], lambda: J.lissage, set_('lissage', J.regler_lissage)),
                self._curs('Zoom', lambda: round(J.zoom * 100), lambda v: J.regler_zoom(v / 100.0), 40.0, 400.0, 5.0, 10.0, lambda v: '%d %%' % round(v), 1.0, defaut=float(RG.DEFAUT['zoom'])),
                self._curs('Vignettage (bords assombris)', lambda: R['vignette'], lambda v: R.__setitem__('vignette', v), 0.0, 1.0, 0.01, 0.05, lambda v: '%d %%' % round(v * 100), 100.0, defaut=RG.DEFAUT['vignette']),
                self._curs('Taille des nombres de dégâts', lambda: R['taille_degats'], lambda v: R.__setitem__('taille_degats', v), 0.5, 3.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, defaut=RG.DEFAUT['taille_degats']),
                self._choix('Anticrénelage', list(MSAA_CHOIX), lambda: R['msaa'], set_('msaa'), note=lambda: 'Sera appliqué au prochain lancement du jeu' if R['msaa'] != J.args.msaa else ''),
                dict(t='act', l='Retour', ok=self.retour)]

    def _e_interface(self):
        R = self.J.reg
        return [self._choix("Afficher les boutons à l'écran", [True, False], lambda: R['boutons'], lambda v: R.__setitem__('boutons', v)),
                dict(t='act', l="Changer le dispositionnement de l'interface", ok=self._aller('placement')),
                dict(t='act', l='Retour', ok=self.retour)]

    def _e_placement(self):
        """Panneau en bas de l'ecran pendant le placement des boutons (les boutons sont glisses a la souris, sur la grille)."""
        R = self.J.reg; H = self.J.hud
        return [self._curs('Taille des boutons', lambda: R['boutons_taille'], lambda v: R.__setitem__('boutons_taille', v), 0.5, 2.0, 0.05, 0.1, lambda v: '%d %%' % round(v * 100), 100.0, defaut=RG.DEFAUT['boutons_taille']),
                self._choix('Aimantation à la grille', [True, False], lambda: R['boutons_aimant'], lambda v: R.__setitem__('boutons_aimant', v)),
                dict(t='act', l="Rétablir les positions d'origine", ok=H.remettre),
                dict(t='act', l='Terminer', ok=self.retour)]

    def _e_son(self):
        J, R = self.J, self.J.reg
        return [self._choix('Son', [True, False], lambda: J.son.actif, lambda v: (J.regler_son(v), R.__setitem__('son', v))),
                self._curs('Volume de la musique', lambda: R['volume_musique'], lambda v: (R.__setitem__('volume_musique', v), J.regler_vol_musique(v)), 0.0, 1.0, 0.01, 0.05, lambda v: '%d %%' % round(v * 100), 100.0, defaut=RG.DEFAUT['volume_musique']),
                self._curs('Volume des bruitages', lambda: R['volume_bruitages'], lambda v: (R.__setitem__('volume_bruitages', v), J.regler_vol_bruitages(v)), 0.0, 1.0, 0.01, 0.05, lambda v: '%d %%' % round(v * 100), 100.0, defaut=RG.DEFAUT['volume_bruitages']),
                dict(t='act', l='Retour', ok=self.retour)]

    def _e_commandes(self):
        R = self.J.reg
        e = [self._curs('Vitesse de déplacement', lambda: R['vitesse_marche'], lambda v: R.__setitem__('vitesse_marche', v), 0.5, 3.0, 0.05, 0.1, lambda v: 'x%.2f' % v, 1.0, defaut=RG.DEFAUT['vitesse_marche']),
             self._choix('Course (maintenir la touche)', [True, False], lambda: R['course'], lambda v: R.__setitem__('course', v)),
             self._curs('Vitesse de la course', lambda: R['vitesse_course'], lambda v: R.__setitem__('vitesse_course', v), 1.2, 4.0, 0.05, 0.1, lambda v: 'x%.2f' % v, 1.0, defaut=RG.DEFAUT['vitesse_course']),
             self._curs('Vitesse des transitions entre cartes', lambda: R['vitesse_fondu'], lambda v: (R.__setitem__('vitesse_fondu', v), self.J.regler_fondu(v)), 1.0, 4.0, 0.05, 0.25, lambda v: 'x%.2f' % v, 1.0, defaut=RG.DEFAUT['vitesse_fondu']),
             dict(t='act', l='Interface', ok=self._aller('interface'))]
        for act, lib in RG.ACTIONS:
            e.append(dict(t='touche', l=lib, act=act, v=[RG.nom_touche(n) for n in R['touches'][act]]))
        e.append(dict(t='act', l='Rétablir les touches par défaut', ok=lambda: (R.touches_par_defaut(), R.enregistrer())))
        e.append(dict(t='act', l='Retour', ok=self.retour))
        return e

    def _chemin_etat(self, n): return self.J.chemin_etat(n)

    @staticmethod
    def _date_fr(date):
        """'2026-10-31 19:21:05' -> '31/10/2026  19:21:05' (nom d'un etat : sa date et son heure d'enregistrement)."""
        try: return time.strftime('%d/%m/%Y  %H:%M:%S', time.strptime(date, '%Y-%m-%d %H:%M:%S'))
        except Exception: return ''

    @staticmethod
    def _lieu_lisible(inf):
        """Lieu de l'etat seulement s'il parle a un joueur (le nom technique d'une carte, comme « mak1f1 », n'est pas montre)."""
        return inf.get('lieu', '') if inf.get('lieu') in ('Carte du monde', 'Combat') else ''

    def _e_etats(self, ecriture):
        e = []
        for n in range(1, NB_ETATS + 1):
            inf = self.J.infos_etat(n)
            if inf: lib = self._date_fr(inf[0].get('date')) or 'Sans date'; val = self._lieu_lisible(inf[0])
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
        act = R.action_de(symbol)
        if self.deroule is not None: self._touche_liste(symbol, act); return True
        if symbol in (K.ESCAPE, K.BACKSPACE) or act == 'B': self.retour(); return True
        if act == 'infos': self.J.regler_infos(not self.J.aide); R['infos'] = self.J.aide; return True          # (la touche des infos a l'ecran se regle dans Commandes)
        if symbol == K.DELETE: self._defaut(); return True
        if symbol in (K.UP,) or act == 'haut': self._bouger(-1); self._repeter(symbol, 'v', -1)
        elif symbol in (K.DOWN,) or act == 'bas': self._bouger(1); self._repeter(symbol, 'v', 1)
        elif symbol in (K.LEFT,) or act == 'gauche': self._regler(-1); self._repeter(symbol, 'h', -1)
        elif symbol in (K.RIGHT,) or act == 'droite': self._regler(1); self._repeter(symbol, 'h', 1)
        elif symbol in (K.RETURN, K.ENTER, K.SPACE) or act == 'A': self._valider()
        return True

    def _repeter(self, symbol, sens, d):
        """Une direction est enfoncee : elle se repetera (maj) tant qu'elle est maintenue, sur la ligne et l'ecran ou elle a commence."""
        t = time.time(); self.rep = (symbol, t, t, sens, d); self.rep_pos = (self.ecran, self.sel.get(self.ecran, 0))

    def maj(self):
        """Repetition des directions maintenues (appelee a chaque image)."""
        if not self.rep: return
        sym, t0, tl, sens, d = self.rep; t = time.time()
        if not self.J.touches[sym]: self.rep = None; return
        if sens == 'h' and self.rep_pos != (self.ecran, self.sel.get(self.ecran, 0)): self.rep = None; return       # la selection a change (souris, autre ecran) : la repetition s'arrete, elle ne doit jamais toucher un autre reglage
        if t - t0 > DELAI_REPETITION and t - tl > PAS_REPETITION:
            self.rep = (sym, t0, t, sens, d)
            if sens == 'v': self._bouger(d)
            else: self._regler(d)

    # ---- liste deroulante
    def _ouvrir_liste(self):
        i = self.sel.get(self.ecran, 0); en = self._entrees()[i]; cur = en['get']()
        self.deroule = [i, en['vals'].index(cur) if cur in en['vals'] else 0]

    def _fin_liste(self, valide):
        d, self.deroule = self.deroule, None
        if not valide or d is None: return
        e = self._entrees()
        if d[0] < len(e) and e[d[0]]['t'] == 'choix': e[d[0]]['set'](e[d[0]]['vals'][d[1]])

    def _bouger_liste(self, d):
        e = self._entrees()
        if self.deroule[0] >= len(e) or e[self.deroule[0]]['t'] != 'choix': self.deroule = None; return
        n = len(e[self.deroule[0]]['vals']); self.deroule[1] = (self.deroule[1] + d) % n

    def _touche_liste(self, symbol, act):
        K = pyglet.window.key
        if symbol in (K.ESCAPE, K.BACKSPACE) or act == 'B': self._fin_liste(False)
        elif symbol == K.UP or act == 'haut': self._bouger_liste(-1); self._repeter(symbol, 'v', -1)
        elif symbol == K.DOWN or act == 'bas': self._bouger_liste(1); self._repeter(symbol, 'v', 1)
        elif symbol in (K.RETURN, K.ENTER, K.SPACE) or act == 'A': self._fin_liste(True)

    def _zone_liste(self, x, y):
        for (x0, y0, x1, y1, j) in self.zones_pop:
            if x0 <= x <= x1 and y0 <= y <= y1: return j
        return None

    def _bouger(self, d):
        if self.deroule is not None: self._bouger_liste(d); return
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
        if self.deroule is not None: return
        en = self._courante()
        if not en: return
        if en['t'] in ('choix', 'curs'): (en['moins'] if d < 0 else en['plus'])()
        elif en['t'] == 'touche':
            c = self.sel.get('col', 0); self.sel['col'] = min(1, max(0, c + d))

    def _defaut(self):
        """Remet le curseur selectionne a sa valeur d'origine."""
        en = self._courante()
        if en and en['t'] == 'curs' and 'defaut' in en: en['defaut']()

    def _valider(self):
        en = self._courante()
        if not en or en.get('off'): return
        if en['t'] == 'touche': self.capture = (en['act'], self.sel.get('col', 0)); return
        if en['t'] == 'curs': self.saisie = [self.sel.get(self.ecran, 0), '']
        elif en['t'] == 'choix' and en.get('liste'): self._ouvrir_liste()
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
        if self.capture is not None: return
        if self.deroule is not None:
            j = self._zone_liste(x, y)
            if j is not None: self.deroule[1] = j
            return
        i, _ = self._zone(x, y)
        if i is not None: self.sel[self.ecran] = i

    def clic(self, x, y, bouton):
        M = pyglet.window.mouse
        if self.capture is not None: self.capture = None; return
        if self.deroule is not None:                                  # liste deroulante ouverte : un clic sur une valeur la choisit, ailleurs (ou clic droit) la ferme
            j = self._zone_liste(x, y) if bouton != M.RIGHT else None
            if j is not None: self.deroule[1] = j; self._fin_liste(True)
            else: self.deroule = None
            return
        if bouton == M.RIGHT:
            if self.saisie is not None: self.saisie = None
            else: self.retour()
            return
        i, f = self._zone(x, y)
        if self.ecran == 'placement' and i is None and self.saisie is None:       # placement : hors du panneau, un clic saisit un bouton de l'ecran
            c = self.cadre_panneau
            if not (c and c[0] <= x <= c[2] and c[1] <= y <= c[3]): self.J.hud.prendre(x, y)
            return
        if self.saisie is not None:                                   # un clic ailleurs que sur la valeur en cours de saisie la valide
            ligne = self.saisie[0]; zv = self.zones_val.get(ligne)
            if i == ligne and zv and zv[0] <= x <= zv[1]: return
            self._fin_saisie(True)
        if i is None: return
        self.sel[self.ecran] = i; en = self._entrees()[i]
        bar = self.barres.get(i)
        zv = self.zones_val.get(i); zd = self.zones_def.get(i)
        if en['t'] == 'curs' and zd and zd[0] <= x <= zd[2] and zd[1] <= y <= zd[3]:       # bouton « valeur par defaut »
            if 'defaut' in en: en['defaut']()
        elif en['t'] == 'curs' and bar and bar[0] - 6 <= x <= bar[1] + 6:       # curseur : le clic maintenu le fait glisser (glisser)
            self.glisse = i; en['fixe'](min(1.0, max(0.0, (x - bar[0]) / (bar[1] - bar[0]))))
        elif en['t'] == 'curs' and zv and zv[0] - 8 <= x <= zv[1] + 8: self.saisie = [i, '']     # clic sur la valeur : saisie au clavier
        elif en['t'] == 'touche':
            col = 1 if x > self.zones_col else 0; self.sel['col'] = col; self._valider()
        else: self._valider()

    def relache(self, x, y, bouton):
        self.glisse = None
        if self.ecran == 'placement' and self.J.hud.pris is not None: self.J.hud.poser(); self.J.reg.enregistrer()

    def glisser(self, x, y):
        """Souris deplacee bouton enfonce : le curseur maintenu suit."""
        if self.glisse is None:
            if self.ecran == 'placement': self.J.hud.deplacer(x, y)
            return
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
        self._bouger(1 if sy > 0 else -1)                                    # (sens inverse : molette vers le haut = ligne suivante)

    # ---- dessin
    @staticmethod
    def _cadre(x, y, w, h, k):
        """Fenetre a la maniere des menus du jeu mobile : fond bleu nuit translucide, cadre en cinq traits, coins arrondis (hud_mobile.cadre)."""
        HM.cadre(x, y, w, h, k)

    def _bouton_defaut(self, idx, x, y, c, est_defaut, sel, k):
        """Bouton carre « valeur par defaut » (fleche en cercle) : clair quand la valeur differe de celle d'origine, terne sinon."""
        self.zones_def[idx] = (x - 3 * k, y - 3 * k, x + c + 3 * k, y + c + 3 * k)
        coul = (90, 90, 90) if est_defaut else JAUNE
        r = pyglet.shapes.BorderedRectangle(x, y, c, c, border=max(1, int(2 * k)), color=(255, 255, 255), border_color=coul[:3]); r.opacity = 30 if est_defaut else 70; r.draw()
        cx, cy, ra = x + c / 2, y + c / 2, c * 0.28; t0, t1 = math.radians(55), math.radians(55 + 270)
        pts = [(cx + ra * math.cos(t0 + (t1 - t0) * i / 14), cy + ra * math.sin(t0 + (t1 - t0) * i / 14)) for i in range(15)]
        for a, b in zip(pts, pts[1:]): pyglet.shapes.Line(a[0], a[1], b[0], b[1], thickness=max(1.5, 2 * k), color=coul[:3]).draw()
        ex, ey = pts[0]; tg = t0 - math.pi / 2                                       # pointe de fleche au debut de l'arc
        h = c * 0.2
        pyglet.shapes.Triangle(ex + h * math.cos(tg), ey + h * math.sin(tg), ex + h * math.cos(tg + 2.4), ey + h * math.sin(tg + 2.4), ex + h * math.cos(tg - 2.4), ey + h * math.sin(tg - 2.4), color=coul[:3]).draw()

    @staticmethod
    def _pilule(x, yc, w, h, couleur):
        """Rectangle a bouts ronds, centre verticalement en yc."""
        r = h / 2
        for sh in (pyglet.shapes.Rectangle(x + r, yc - r, w - 2 * r, h, color=couleur), pyglet.shapes.Circle(x + r, yc, r, segments=24, color=couleur), pyglet.shapes.Circle(x + w - r, yc, r, segments=24, color=couleur)): sh.draw()

    def _interrupteur(self, cle, x, yc, actif, sel, grise, k):
        """Interrupteur coulissant (piste arrondie, bouton rond) : or quand c'est active, gris sinon ; le bouton glisse d'une position a l'autre (animation courte) ; contour or s'il est selectionne."""
        cible = 1.0 if actif else 0.0; p = self.pos_sw.get(cle, cible)                   # premiere apparition : pas d'animation
        p = cible if abs(cible - p) < 0.02 else p + (cible - p) * min(1.0, self.dt_sw * 16.0); self.pos_sw[cle] = p
        w, h = LARG_SW * k, HAUT_SW * k; r = h / 2
        piste = (30, 32, 36) if grise else tuple(int(a + (b - a) * p) for a, b in zip((20, 22, 26), (225, 207, 3)))
        if sel and not grise: e = max(1.5, 2 * k); self._pilule(x - e, yc, w + 2 * e, h + 2 * e, JAUNE)
        self._pilule(x, yc, w, h, piste)
        pyglet.shapes.Circle(x + r + (w - 2 * r) * p, yc, r - 3 * k, segments=24, color=(128, 128, 128) if grise else (255, 255, 255)).draw()

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
        placement = self.ecran == 'placement'
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        if placement: J.hud.dessiner(HM.NOMS, True)                          # placement : les boutons de l'ecran, bien visibles (ni voile ni cadre central), et le panneau en bas
        else:
            voile = pyglet.shapes.Rectangle(0, 0, W, H, color=(0, 0, 0)); voile.opacity = 150; voile.draw()
        t = time.time(); self.dt_sw = min(0.1, t - self.t_sw); self.t_sw = t               # (animation des interrupteurs)
        ecr = self.ecran; e = self._entrees(); n = len(e); i_sel = min(self.sel.get(ecr, 0), max(0, n - 1))
        fs, fst, fsp = 18 * k, 24 * k, 13 * k; pad = 30 * k
        titres = {'racine': 'Pause', 'affichage': 'Affichage', 'son': 'Son', 'commandes': 'Commandes', 'interface': 'Interface', 'placement': "Disposition de l'interface", 'sauver': 'Sauvegarder un état', 'charger': 'Charger un état', 'quitter': 'Quitter'}
        avec_mini = ecr in ('sauver', 'charger')
        curs_aide = 'Curseurs : glisser, ←/→ ou cliquer sur la valeur pour la taper ; Suppr ou bouton rond : valeur par défaut'
        aide = {'sauver': 'Entrée : enregistrer ici (écrase l\'état)', 'charger': 'Entrée : charger cet état', 'affichage': curs_aide, 'son': curs_aide, 'commandes': curs_aide,
                'interface': 'Les boutons n\'apparaissent que hors combat, quand le jeu les autorise (comme sur le téléphone)',
                'placement': 'Glisse les boutons pour les placer    Échap ou clic droit : terminer'}.get(ecr, '')
        en_sel = e[i_sel] if e else None
        if en_sel and en_sel['t'] == 'touche': aide = 'Entrée : changer la touche    ←/→ : colonne    Suppr : effacer'
        elif en_sel and en_sel['t'] == 'choix' and not placement:
            aide = 'Entrée ou clic : activer / désactiver    ←  : Non    →  : Oui' if en_sel.get('sw') else 'Entrée ou clic : ouvrir la liste    ←/→ : valeur précédente / suivante'
        if self.deroule is not None: aide = '↑/↓ : choisir    Entrée ou clic : valider    Échap ou clic droit : fermer'
        if self.saisie is not None: aide = 'Tape la valeur (Entrée : valider, Échap : annuler)'
        if self.capture is not None:
            act = dict(RG.ACTIONS)[self.capture[0]]; aide = 'Appuie sur la touche pour « %s »    (Échap : annuler, Suppr : effacer)' % act
        msg = self.message[0] if self.message and time.time() - self.message[1] < 4.0 else ''
        # largeur : le plus long libelle + la place des valeurs / curseurs / colonnes de touches
        lw = max([self._et(x['l'], fs).content_width for x in e] + [0.0]); vw = 0.0
        for x in e:
            if x['t'] == 'choix':
                tw = max(self._et(self._nom_valeur(x['l'], v), fs).content_width for v in self._valeurs(x))
                vw = max(vw, tw + 24 * k if x.get('liste') else tw + 14 * k + LARG_SW * k)               # liste : valeur + fleche ; interrupteur : Oui / Non puis l'interrupteur
        pw = max(540 * k, 52 * k + lw + 40 * k + vw + 30 * k)
        if ecr in ('affichage', 'son', 'commandes', 'placement'): pw = max(pw, 52 * k + lw + 40 * k + 44 * k + 200 * k + 20 * k + 90 * k + 30 * k)
        if ecr == 'commandes': pw = max(pw, 52 * k + lw + 40 * k + 2 * 190 * k + 30 * k)
        if ecr in ('sauver', 'charger'): pw = max(pw, 52 * k + lw + 30 * k + 150 * k)
        pied = 36 * k if aide else 0.0                     # (le message d'information est dessine sous le cadre : il ne decale rien)
        hmax = H - 2 * 36 * k; h_titre = 78 * k + (22 * k if ecr == 'commandes' else 0.0)
        if placement: h_titre = 64 * k
        rh = max(34 * k, min(52 * k, (hmax - h_titre - pad / 2 - pied) / max(1, n)))
        if placement: rh = 38 * k                                                  # panneau compact
        h = min(hmax, h_titre + n * rh + pad / 2 + pied)
        wmini = 360 * k if avec_mini else 0.0; gap = 24 * k if avec_mini else 0.0
        x0 = (W - pw - wmini - gap) / 2; y1 = (H + h) / 2; y0 = y1 - h
        if placement: y0 = 22 * k; y1 = y0 + h                                      # panneau colle en bas de l'ecran
        self.cadre_panneau = (x0, y0, x0 + pw, y1) if placement else None
        self._cadre(x0, y0, pw, h, k)
        e_t = self._et(titres.get(ecr, ''), fst, BLANC); e_t.x = x0 + (pw - e_t.content_width) / 2; e_t.y = y1 - (44 if placement else 52) * k; e_t.draw()
        visibles = max(1, int((h - h_titre - pad / 2 - pied) / rh + 0.02)); debut = 0               # defilement : les lignes qui ne tiennent pas sont decalees pour garder la selection visible
        if n > visibles: debut = min(max(0, i_sel - visibles // 2), n - visibles)
        self.zones = []; self.barres = {}; self.zones_val = {}; self.zones_def = {}; self.zones_pop = []; lignes = {}; c1x = x0 + pw - 30 * k - 2 * 190 * k; self.zones_col = c1x + 190 * k - 8 * k
        if ecr == 'commandes':
            for c in range(2):
                eh = self._et('Touche %d' % (c + 1), fsp, GRIS); eh.x = c1x + c * 190 * k; eh.y = y1 - h_titre + 6 * k; eh.draw()
        y = y1 - h_titre
        for idx in range(debut, min(n, debut + visibles)):
            en = e[idx]; ytop = y; ybas = y - rh; sel = idx == i_sel and en['t'] != 'sep'; lignes[idx] = (ybas, ytop)
            note = en['note']() if en.get('note') else ''
            dec = max(0.0, min(8 * k, (rh - 36 * k) * 0.6)) if note else 0.0                  # note rouge sous la valeur : la ligne monte un peu pour lui laisser la place
            if en['t'] != 'sep': HM.plaque(x0 + 42 * k, ybas + 3 * k, pw - 58 * k, rh - 6 * k, k, sel)       # fond du bouton, comme ceux du menu des commandes du jeu mobile
            if sel:
                cy = ybas + rh / 2 + dec
                tri = pyglet.shapes.Triangle(x0 + 22 * k, cy + 9 * k, x0 + 22 * k, cy - 9 * k, x0 + 22 * k + 15 * k, cy, color=JAUNE); tri.draw()
            coul = GRIS if en.get('off') else BLANC
            base = ybas + (rh - fs * 1.33) / 2 + 5 * k
            if en['t'] == 'sep': coul = OR
            lx = x0 + 52 * k
            if en['t'] == 'slot':
                nu = self._et('%d' % en['n'], fs, coul); nu.x = lx; nu.y = base; nu.draw(); lx += 44 * k
            base += dec
            lab = self._et(en['l'], fs, coul); lab.x = lx; lab.y = base; lab.draw()
            if note:
                en_ = self._et(note, fsp * 0.95, ROUGE); en_.x = x0 + pw - 30 * k - en_.content_width; en_.y = ybas + 6 * k; en_.draw()
            if en['t'] == 'choix' and en.get('liste'):                                        # liste deroulante : valeur courante et petite fleche vers le bas
                vl = self._et(en['v'](), fs, coul); vl.x = x0 + pw - 30 * k - 24 * k - vl.content_width; vl.y = base; vl.draw()
                fx, fy = x0 + pw - 30 * k - 8 * k, ybas + rh / 2 + dec
                pyglet.shapes.Triangle(fx - 7 * k, fy + 4 * k, fx + 7 * k, fy + 4 * k, fx, fy - 5 * k, color=OR[:3] if sel else coul[:3]).draw()
                self.zones_val[idx] = (vl.x - 10 * k, x0 + pw - 30 * k + 10 * k)
            elif en['t'] == 'choix':                                                          # interrupteur Oui / Non : le texte de la valeur, puis l'interrupteur
                sw_x = x0 + pw - 30 * k - LARG_SW * k; actif = bool(en['get']())
                vl = self._et(en['v'](), fs, coul if not actif or en.get('off') else OR); vl.x = sw_x - 14 * k - vl.content_width; vl.y = base; vl.draw()
                self._interrupteur(en['l'], sw_x, ybas + rh / 2, actif, sel, en.get('off'), k)
                self.zones_val[idx] = (vl.x - 10 * k, sw_x + LARG_SW * k + 10 * k)
            elif en['t'] == 'curs':
                if self.saisie is not None and self.saisie[0] == idx: txt = (self.saisie[1] + ('_' if int(time.time() * 2) % 2 == 0 else ' ')).rjust(3)
                else: txt = en['v']()
                dr = x0 + pw - 30 * k - 40 * k                                                # bord droit de la valeur : le bouton « valeur par defaut » est a sa droite
                vl = self._et(txt, fs, OR if self.saisie is not None and self.saisie[0] == idx else coul); vl.x = dr - vl.content_width; vl.y = base; vl.draw()
                self.zones_val[idx] = (vl.x - 10 * k, dr + 10 * k)
                bw = 200 * k; bx1 = dr - 90 * k - 20 * k; bx0 = bx1 - bw; by = ybas + rh / 2 - 5 * k; self.barres[idx] = (bx0, bx1)
                fond = pyglet.shapes.Rectangle(bx0, by, bw, 10 * k, color=(16, 18, 22)); fond.draw()
                rem = pyglet.shapes.Rectangle(bx0, by, bw * max(0.0, min(1.0, en['frac']())), 10 * k, color=JAUNE); rem.draw()
                cur = pyglet.shapes.Rectangle(bx0 + bw * max(0.0, min(1.0, en['frac']())) - 3 * k, by - 4 * k, 6 * k, 18 * k, color=(255, 255, 255)); cur.draw()
                if 'defaut' in en: self._bouton_defaut(idx, x0 + pw - 30 * k - 26 * k, ybas + rh / 2 - 13 * k, 26 * k, en['est_defaut'](), sel, k)
            elif en['t'] == 'slot':
                if en['v']: vl = self._et(en['v'], fsp * 1.2, GRIS); vl.x = x0 + pw - 24 * k - vl.content_width; vl.y = base; vl.draw()
            elif en['t'] == 'touche':
                for c in range(2):
                    txt = en['v'][c]; actif = sel and self.sel.get('col', 0) == c
                    if self.capture is not None and self.capture == (en['act'], c): txt = '…'
                    cx = c1x + c * 190 * k
                    if actif:
                        r = pyglet.shapes.BorderedRectangle(cx - 8 * k, ybas + 6 * k, 180 * k, rh - 12 * k, border=max(1, int(2 * k)), color=(255, 255, 255), border_color=JAUNE); r.opacity = 60; r.draw()
                    vl = self._et(txt, fs * 0.92, OR if actif else (BLANC if en['v'][c] != RG.nom_touche(None) else GRIS)); vl.x = cx; vl.y = base; vl.draw()
            self.zones.append((x0 + 12 * k, ybas + 3 * k, x0 + pw - 12 * k, ytop - 3 * k, idx))
            y -= rh
        # pied du cadre : message d'information puis aide
        yp = y0 + 12 * k
        if aide:
            ea = self._et(aide, fsp, AIDE); ea.x = x0 + (pw - ea.content_width) / 2; ea.y = yp; ea.draw(); yp += 36 * k
        if msg:
            em = self._et(msg, fsp * 1.1, ROUGE if self.message[2] else OR); em.x = x0 + (pw - em.content_width) / 2; em.y = max(8 * k, y0 - 34 * k); em.draw()
        # miniature de l'etat survole
        if avec_mini:
            mx = x0 + pw + gap; mh = min(h, 270 * k)
            self._cadre(mx, y1 - h, wmini, h, k)
            if e and e[i_sel]['t'] == 'slot':
                n_e = e[i_sel]['n']; t = self._miniature(n_e); inf = J.infos_etat(n_e)
                if t is not None:
                    w_i = wmini - 40 * k; h_i = w_i * t.height / t.width
                    spr = pyglet.sprite.Sprite(t, x=mx + 20 * k, y=y1 - 40 * k - h_i); spr.scale_x = w_i / t.width; spr.scale_y = h_i / t.height; spr.draw()
                    liste = []
                    if inf:
                        liste = [self._date_fr(inf[0].get('date')) or 'Sans date', self._lieu_lisible(inf[0]), 'Image du moteur %s' % inf[0].get('images', '')]
                    for j, ligne in enumerate(liste):
                        el = self._et(ligne, fsp * 1.1, BLANC if j == 0 else GRIS); el.x = mx + 20 * k; el.y = y1 - 40 * k - h_i - 34 * k - j * 30 * k; el.draw()
                else:
                    el = self._et('Emplacement vide' if not inf else 'Pas de miniature', fs, GRIS); el.x = mx + (wmini - el.content_width) / 2; el.y = y1 - h / 2; el.draw()
        if self.deroule is not None and self.deroule[0] in lignes and self.deroule[0] < n and e[self.deroule[0]]['t'] == 'choix':
            self._dessiner_liste(e[self.deroule[0]], lignes[self.deroule[0]], x0 + pw - 24 * k, k, fs)

    def _dessiner_liste(self, en, ligne, xd, k, fs):
        """Liste deroulante d'un choix : sous la ligne (au-dessus s'il n'y a pas la place), valeur courante en or, curseur en triangle comme dans les menus du jeu."""
        J = self.J; vals = en['vals']; noms = [self._nom_valeur(en['l'], v) for v in vals]; cur = self.deroule[1]; H = J.height
        ih = 36 * k; nvis = max(1, min(len(vals), 8, int((H - 40 * k) // ih)))
        w = max(max(self._et(t, fs).content_width for t in noms) + 90 * k, 240 * k); h = nvis * ih + 20 * k
        ybas, ytop = ligne; y1 = ybas - 4 * k; y0 = y1 - h
        if y0 < 8 * k: y1 = ytop + 4 * k; y0 = y1 - h
        if y0 < 8 * k: y0 = 8 * k; y1 = y0 + h
        x1 = xd; x0 = x1 - w
        self._cadre(x0, y0, w, h, k)
        top = max(0, min(cur - nvis // 2, len(vals) - nvis))
        self.zones_pop = []; y = y1 - 10 * k
        for j in range(top, top + nvis):
            yb = y - ih; courant = vals[j] == en['get']()
            if j == cur:
                pyglet.shapes.Triangle(x0 + 16 * k, yb + ih / 2 + 8 * k, x0 + 16 * k, yb + ih / 2 - 8 * k, x0 + 16 * k + 13 * k, yb + ih / 2, color=OR[:3]).draw()
            et = self._et(noms[j], fs, OR if courant else BLANC); et.x = x0 + 44 * k; et.y = yb + (ih - fs * 1.33) / 2 + 5 * k; et.draw()
            self.zones_pop.append((x0 + 6 * k, yb, x1 - 6 * k, y, j)); y -= ih
        if top > 0: pyglet.shapes.Triangle(x1 - 22 * k, y1 - 8 * k, x1 - 10 * k, y1 - 8 * k, x1 - 16 * k, y1 - 1 * k, color=GRIS[:3]).draw()
        if top + nvis < len(vals): pyglet.shapes.Triangle(x1 - 22 * k, y0 + 8 * k, x1 - 10 * k, y0 + 8 * k, x1 - 16 * k, y0 + 1 * k, color=GRIS[:3]).draw()
