"""Plein ecran, fenetre, resolution et moniteurs."""
import os, sys, time
import pyglet
from pyglet import gl
from dq4_pc import chemins as CH
from dq4_pc.fenetre import ecrans as EK
from dq4_pc.noyau import suivi_charge as SV
from dq4_pc.persistance import reglages as RG
from dq4_pc.fenetre.constantes import RESOLUTIONS
from dq4_pc.fenetre.aides import ajuster_taille, transitions_dwm, zone_utile


class PleinEcranMixin:
    """Plein ecran, fenetre, resolution et moniteurs."""

    def _creer_fenetre(self, args, cfg, demande):
        """Cree la fenetre directement dans le mode memorise (0 fenetre, 1 plein ecran), avec repli a toute erreur, dit dans la console : plein ecran -> fenetre.
        Elle reste cachee jusqu'a une premiere image noire (pas d'eclair blanc). -> mode obtenu."""
        try:
            ecran = pyglet.display.get_display().get_default_screen(); self.bureau = (int(ecran.width), int(ecran.height))      # (la taille du bureau)
        except Exception as ex: print('Écran principal illisible (%r)' % (ex,), flush=True)
        for mode in range(demande, -1, -1):
            try:
                self._echec_simule(mode)
                if mode == 1: self._creer_plein_ecran(cfg)
                else: super().__init__(args.largeur, args.hauteur, caption=self.TITRE_FENETRE, resizable=True, config=cfg, vsync=True, visible=False)
            except Exception as ex:
                if mode == 0: raise
                print('Plein écran impossible au lancement (%r) : fenêtre' % (ex,), flush=True)
                continue
            self.mode_fen = mode
            SV.noter('fenetre creee (cachee)', mode=mode, taille='%dx%d' % (self.width, self.height))
            if SV.ACTIF:
                for ev in ('on_resize', 'on_show', 'on_hide', 'on_expose', 'on_move', 'on_activate', 'on_deactivate'):
                    self.push_handlers(**{ev: (lambda *a, _e=ev: SV.noter('evenement ' + _e, args=a))})
            try: self.switch_to(); gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear(); self.flip()
            except Exception: pass
            SV.noter('image noire presentee (fenetre cachee)')
            self.dwm_coupe = transitions_dwm(self, False)    # Windows : pas d'animation d'ouverture du gestionnaire de fenetres (remise par on_draw, 2 s apres la 1re image du jeu)
            self.set_visible(True); self.activate()          # (ce que Window.__init__ fait pour une fenetre visible : ici apres l'image noire)
            try: self.switch_to(); gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear(); self.flip()      # Windows : l'image noire presentee fenetre cachee n'est pas forcement affichee ; une 2e, fenetre montree, evite le fond de classe (blanc) le temps du chargement
            except Exception: pass
            SV.noter('fenetre montree', taille='%dx%d' % (self.width, self.height), dwm_coupe=self.dwm_coupe)
            return mode

    def _creer_plein_ecran(self, cfg):
        """Fenetre creee en plein ecran, sur l'ecran principal : elle n'existe pas encore, il n'y a donc pas d'ecran ou elle se trouve a detecter (par la suite, F11 ou l'interrupteur la mettent en plein ecran sur l'ecran ou elle est)."""
        super().__init__(caption=self.TITRE_FENETRE, resizable=True, config=cfg, vsync=True, fullscreen=True, visible=False); self._noter_zone_plein()

    # ---- reglages appliques depuis le menu Echap
    def regler_mode(self, m): self.mode = RG.mode_sprites_valide(m)

    @property
    def est_plein(self):
        """Plein ecran (fenetre sans bordure a la resolution du bureau) ?"""
        return self.mode_fen == 1

    def resolutions(self):
        """Tailles proposees (16/9, 720p a 4K), triees par largeur puis hauteur : fenetre = celles qui tiennent sur l'ecran avec ses bordures ; plein ecran = celles du bureau (la ligne est grisee : la fenetre prend toujours
        la resolution du bureau, le choix sert au prochain retour en fenetre). La taille actuelle s'y ajoute si elle est libre."""
        liste = list(RESOLUTIONS); cur = self.resolution_courante()
        lim = self.bureau if self.est_plein else zone_utile()
        if lim: liste = [r for r in liste if r[0] <= lim[0] and r[1] <= lim[1]]
        if cur not in liste: liste.append(cur)
        return sorted(liste)                # par largeur, puis par hauteur

    def resolution_courante(self): return (int(self.width), int(self.height))

    def regler_resolution(self, v):
        """Fenetre : change la taille (ramenee a l'ecran si elle est trop grande). Plein ecran : sans effet, la fenetre garde la resolution du bureau ; le choix sert au prochain retour en fenetre."""
        w, h = int(v[0]), int(v[1])
        if self.est_plein: self.taille_fenetre = ajuster_taille(w, h)
        else:
            w, h = ajuster_taille(w, h)
            self.taille_fenetre = (w, h); self.set_size(w, h); self._verifier_taille_reelle()

    def _verifier_taille_reelle(self):
        """Windows : compare la zone de dessin donnee par le systeme a celle que pyglet croit avoir et la lui redonne si elles different (fenetre reduite par Windows : sinon le dessin est trop grand et la scene semble zoomee jusqu'au premier redimensionnement)."""
        if sys.platform != 'win32' or self.est_plein: return
        try:
            import ctypes
            from ctypes import wintypes
            r = wintypes.RECT()
            if not ctypes.windll.user32.GetClientRect(self._hwnd, ctypes.byref(r)): return
            w, h = r.right - r.left, r.bottom - r.top
            if w <= 0 or h <= 0 or (w, h) == (self._width, self._height): return
            print('Fenêtre : zone de dessin %d x %d corrigée (le système donne %d x %d)' % (self._width, self._height, w, h), flush=True)
            self._width, self._height = w, h
            self._update_view_location(w, h)
            self.dispatch_event('_on_internal_resize', w, h)
        except Exception as ex: print('vérification de la taille impossible :', ex, flush=True)

    def regler_infos(self, oui): self.aide = bool(oui)

    def regler_plein_ecran(self, oui):
        """Interrupteur « Plein écran » du menu Echap, F11 et Alt + Entree : passe de la fenetre au plein ecran (fenetre sans bordure a la resolution du moniteur, l'affichage du moniteur ne change pas) et inversement, en une seule
        bascule (voir _poser_plein_ecran). Le moniteur du plein ecran est celui ou se trouve la fenetre (voir _ecran_pour_plein).
        Le mode obtenu est memorise dans les reglages (`mode_fenetre`). A toute erreur : etat de depart conserve, dit dans la console et par un message a l'ecran. -> vrai si la fenetre est en plein ecran."""
        cible = 1 if oui else 0; R = self.reg
        if cible == self.mode_fen: R['mode_fenetre'] = cible; return self.est_plein
        if self._en_bascule: return self.est_plein
        self._en_bascule = True
        try:
            erreur = None
            try:
                ecran = None
                if cible == 1:
                    ecran = self._ecran_pour_plein()[0]
                    if ecran is not None and not self.fullscreen and self._deja_sur(ecran): ecran = None          # (c'est deja le moniteur de pyglet : set_fullscreen(True) comme avant)
                self._poser_plein_ecran(cible == 1, ecran)
            except Exception as ex: erreur = ex
            self.mode_fen = 1 if self.fullscreen else 0           # (l'etat reel de la fenetre)
            R['mode_fenetre'] = self.mode_fen
            self._journal_fenetre('plein écran' if self.mode_fen else 'fenêtre')
            if erreur is not None:
                print('%s impossible (%r) : %s conservé' % ('Plein écran' if cible else 'Fenêtre', erreur, 'plein écran' if self.mode_fen else 'fenêtre'), flush=True)
                self._noter_echec_bascule(cible, erreur)
                if self._pret: self.toast('%s impossible' % ('Plein écran' if cible else 'Fenêtre'), 3.0)
        finally: self._en_bascule = False
        return self.est_plein

    def _noter_echec_bascule(self, cible, erreur):
        """Echec d'un passage plein ecran <-> fenetre : l'erreur COMPLETE (la pile d'appels, pas seulement son texte) avec l'etat de la fenetre et des moniteurs, dans la console et dans `erreurs_fenetre.log` (a cote des reglages ;
        ignore par git ; `DQ_JOURNAL_FENETRE` : un autre fichier). La ligne « Fenêtre impossible (...) » ne dit pas ou ca a echoue. Ne leve jamais d'erreur."""
        try:
            import traceback
            etat = []
            try: etat.append('fenêtre : plein écran = %s, %d x %d, taille mémorisée %s, place d\'avant %s, bureau %s' % (self.fullscreen, self.width, self.height, getattr(self, 'taille_fenetre', None), getattr(self, '_windowed_location', None), getattr(self, 'bureau', None)))
            except Exception as ex: etat.append('fenêtre illisible (%r)' % (ex,))
            try: ec = self.screen; etat.append('écran de la fenêtre pour pyglet : %d x %d en (%d, %d)' % (ec.width, ec.height, ec.x, ec.y))
            except Exception as ex: etat.append('écran de la fenêtre illisible (%r)' % (ex,))
            try: etat.append('moniteurs : ' + ' ; '.join('%d x %d en (%d, %d)%s' % (d['largeur'], d['hauteur'], d['x'], d['y'], ' (principal)' if d['principal'] else '') for d in self._lire_ecrans(True)[1]))
            except Exception as ex: etat.append('moniteurs illisibles (%r)' % (ex,))
            etat.append('pyglet %s, Python %s, %s' % (pyglet.version, sys.version.split()[0], sys.platform))
            texte = '--- %s : passage en %s impossible ---\n%s%s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), 'plein écran' if cible else 'fenêtre', ''.join(traceback.format_exception(erreur)), '\n'.join(etat))
            print(texte, flush=True)
            chemin = CH.DOSSIERS.journal_erreurs(); os.makedirs(os.path.dirname(os.path.abspath(chemin)), exist_ok=True)
            with open(chemin, 'a', encoding='utf-8') as f: f.write(texte + '\n')
        except Exception as ex: print('Erreur de la bascule non notée (%r)' % (ex,), flush=True)

    def basculer_plein_ecran(self):
        """F11 / Alt + Entree : fenetre <-> plein ecran."""
        return self.regler_plein_ecran(not self.est_plein)

    def _poser_plein_ecran(self, plein, ecran=None):
        """La bascule, en une seule etape (pyglet : un set_fullscreen, qui sur Windows cache la fenetre, change son style et sa taille, puis la remontre et la replace) :
        - la taille de la fenetre est memorisee avant de la quitter (`taille_fenetre`, la position l'est par pyglet) et rendue d'un coup en y revenant, jamais par un etat intermediaire (plus de set_fullscreen(False) suivi de set_fullscreen(True)) ;
        - la fenetre est cachee AVANT, donc remontree une seule fois, a sa taille et a sa place definitives, et non pas montree au mauvais endroit puis deplacee ;
        - une image du jeu est dessinee a la taille definitive pendant qu'elle est cachee (les tampons du rendu hors ecran, postfx.py, ne sont refaits que si la taille a change, une seule fois, ici : plus de reconstruction forcee a chaque
          bascule), puis affichee, puis la fenetre est montree et la meme image redessinee aussitot (au cas ou le systeme n'aurait pas gardé celle de la fenetre cachee) : aucune trame de taille instable ni de tampon vide.
        `ecran` : objet Screen de pyglet du plein ecran (None : celui que pyglet a deja). Deja en plein ecran, un autre `ecran` deplace la fenetre sur ce moniteur (meme etape : cachee, un set_fullscreen, une image, montree) ;
        le moniteur de depart est retabli si le deplacement echoue.
        Leve une erreur si le mode n'a pas pu etre pris (l'etat de depart est alors retabli). DQ_BASCULE_SIMPLE=1 : (debogage) un set_fullscreen sans rien d'autre, comme avant."""
        avant = bool(self.fullscreen)
        if avant == plein and not (plein and ecran is not None and not self._deja_sur(ecran)): return
        self._rafraichir_ecran()          # (AVANT tout : le moniteur que pyglet garde peut ne plus etre valable, voir _rafraichir_ecran)
        if not avant: self.taille_fenetre = (int(self.width), int(self.height))          # (la taille de la fenetre, a retrouver au retour)
        ecran_avant = getattr(self, 'screen', None) if avant else None              # (le moniteur a retrouver si le deplacement echoue)
        taille = ajuster_taille(*self.taille_fenetre)              # (une taille memorisee plus grande que la zone utile de l'ecran est ramenee a l'ecran)
        if os.environ.get('DQ_BASCULE_SIMPLE'): self._mettre_plein(plein, taille, ecran); self._echec_simule(1 if plein else 0); return
        cachee = False; erreur = None
        try:
            if getattr(self, '_visible', True): cachee = True; self.set_visible(False)          # (cachee avant l'appel : un masquage a moitie reussi est quand meme suivi d'un set_visible(True))
            self._mettre_plein(plein, taille, ecran)
            self._echec_simule(1 if plein else 0)          # (test : l'echec arrive apres le changement, pour essayer le retour a l'etat de depart)
        except Exception as ex:
            erreur = ex
            try: self._mettre_plein(avant, taille, ecran_avant)          # (retour a l'etat de depart, fenetre toujours cachee, sur le moniteur de depart)
            except Exception as ex2:
                print("Retour à l'état de départ impossible (%r)" % (ex2,), flush=True)
                try: erreur.add_note("Retour à l'état de départ impossible aussi : %r" % (ex2,))
                except Exception: pass
        self._image_de_bascule()
        if cachee:
            try: self.set_visible(True)
            except Exception as ex: print('Fenêtre non remontrée (%r)' % (ex,), flush=True)
            else: self._image_de_bascule()          # (supposé : le systeme peut ne pas garder ce qui est affiche pendant que la fenetre est cachee ; la meme image est redessinee des qu'elle est visible, sans attendre la boucle)
        if erreur is not None: raise erreur

    def _mettre_plein(self, plein, taille, ecran=None):
        """Le set_fullscreen de la bascule (un seul appel), sur le moniteur `ecran` (objet Screen de pyglet ; None : celui que la fenetre a). En revenant en fenetre elle retrouve sa taille (`taille`) et sa place d'avant
        (position memorisee par pyglet, sur son moniteur d'origine, quel que soit celui du plein ecran) ; sans position memorisee (lancee en plein ecran) ou si son moniteur n'est plus la, elle est centree sur le moniteur
        du plein ecran."""
        if plein:
            if ecran is not None: self.set_fullscreen(True, screen=ecran)
            else: self.set_fullscreen(True)
            self._noter_zone_plein()
        else:
            self.set_fullscreen(False, width=int(taille[0]), height=int(taille[1]))          # (la signature de pyglet : set_fullscreen(plein, screen, mode, width, height))
            loc = getattr(self, '_windowed_location', None); zone = getattr(self, 'zone_plein', None) or ((0, 0) + tuple(self.bureau) if self.bureau else None)
            vus = self._lire_ecrans(True)[1]
            if loc and zone and vus and EK.ecran_de((loc[0], loc[1], self.width, self.height), vus) is None: loc = None          # (son moniteur a ete debranche : elle serait hors de tous les ecrans)
            if not loc and zone:
                try: self.set_location(int(zone[0] + max(0, (zone[2] - self.width) // 2)), int(zone[1] + max(32, (zone[3] - self.height) // 2)))
                except Exception as ex: print('Fenêtre non centrée (%r)' % (ex,), flush=True)
        if sys.platform == 'win32' and not plein: self._verifier_taille_reelle()          # (Windows peut reduire la fenetre sans prevenir)

    def _image_de_bascule(self):
        """Fenetre cachee, a sa taille definitive : une image du jeu y est dessinee et affichee (pendant les logos et les chargements : du noir), pour que la premiere chose vue soit une image complete."""
        try:
            self.switch_to()
            if self._pret: self.on_draw()
            else: gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear()
            self.flip()
        except Exception as ex:
            print("Image de la bascule impossible (%r) : noir" % (ex,), flush=True)
            try: gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear(); self.flip()
            except Exception: pass

    # ---- moniteur du plein ecran : celui de la fenetre (aucun reglage ; logique pure dans ecrans.py)
    def _lire_ecrans(self, frais=False):
        """-> (objets Screen de pyglet, descriptions de ecrans.lister) des moniteurs detectes (`display.get_screens()`). La liste est gardee 1,5 s (la page Affichage la lit a chaque image et, sous Windows, l'enumeration interroge le
        systeme) ; `frais` la relit (bascule, changement de choix). Illisible -> ([], [])."""
        t = time.perf_counter(); c = getattr(self, '_ecrans_cache', None)
        if c is not None and not frais and t - c[0] < 1.5: return c[1], c[2]
        try:
            ecrans = list((getattr(self, 'display', None) or pyglet.display.get_display()).get_screens())
            res = (t, ecrans, EK.lister(ecrans))
        except Exception as ex:
            print('Moniteurs illisibles (%r)' % (ex,), flush=True); res = (t, [], [])
        self._ecrans_cache = res
        return res[1], res[2]

    def _rafraichir_ecran(self):
        """Remet a jour le moniteur que pyglet garde pour la fenetre (`_screen`) avant une bascule (#126). Sous Windows, ce Screen garde la poignee (HMONITOR) du moniteur telle qu'elle etait a la creation de la fenetre ;
        quand on branche (ou debranche) un ecran, Windows peut en attribuer d'autres et la poignee gardee n'est plus valable : `set_fullscreen` recree alors la fenetre (`Win32Window._create`), qui lit la densite du moniteur
        (`Screen.get_dpi` -> GetDpiForMonitor) et echoue avec « Descripteur non valide » (le journal de Sylfried du 03/11/2026 : plein ecran, puis un ecran externe branche, puis plus de retour en fenetre).
        Le moniteur est cherche dans une enumeration neuve : celui qui a les memes position et dimensions que l'ancien, sinon celui ou se trouve la fenetre, sinon le principal. Ne leve jamais d'erreur.
        -> vrai si un moniteur valable a ete mis en place."""
        try:
            actuel = getattr(self, '_screen', None); ecrans, desc = self._lire_ecrans(True)
            if actuel is None or not ecrans or not desc: return False
            ancien = (int(actuel.x), int(actuel.y), int(actuel.width), int(actuel.height))
            i = next((k for k, d in enumerate(desc) if (d['x'], d['y'], d['largeur'], d['hauteur']) == ancien), None)
            if i is None: i = EK.cible(desc, self._indice_ecran_fenetre(desc))
            if i is None: return False
            neuf = ecrans[desc[i]['source']]
            if (int(neuf.x), int(neuf.y), int(neuf.width), int(neuf.height)) != ancien:
                print('Moniteur de la fenêtre remis à jour : %d x %d en (%d, %d) (avant : %d x %d en (%d, %d))' % (neuf.width, neuf.height, neuf.x, neuf.y, ancien[2], ancien[3], ancien[0], ancien[1]), flush=True)
            self._screen = neuf; return True
        except Exception as ex:
            print('Moniteur de la fenêtre non remis à jour (%r)' % (ex,), flush=True); return False

    def _indice_ecran_fenetre(self, desc):
        """Indice (dans `desc`) du moniteur ou se trouve la fenetre (celui de son centre) ; None si elle n'existe pas encore ou si sa place est illisible."""
        try:
            x, y = self.get_location(); return EK.ecran_de((x, y, self.width, self.height), desc)
        except Exception: return None

    def _ecran_pour_plein(self, frais=True):
        """-> (objet Screen de pyglet, description) du moniteur du plein ecran : celui ou se trouve la fenetre (celui de son centre), a defaut le principal. (None, None) si les moniteurs sont illisibles : pyglet garde alors le sien.
        Aucun choix du joueur (retire le 03/11/2026 sur sa demande : le plein ecran se fait toujours sur l'ecran de la fenetre). Ne leve jamais d'erreur."""
        ecrans, desc = self._lire_ecrans(frais)
        try:
            i = EK.cible(desc, self._indice_ecran_fenetre(desc))
            if i is None: return None, None
            return ecrans[desc[i]['source']], desc[i]
        except Exception as ex:
            print('Moniteur du plein écran illisible (%r)' % (ex,), flush=True); return None, None

    def _deja_sur(self, ecran):
        """La fenetre (en plein ecran) est-elle deja sur ce moniteur ? (meme position et memes dimensions que le moniteur de pyglet.)"""
        try:
            ec = self.screen; return (ec.x, ec.y, ec.width, ec.height) == (ecran.x, ecran.y, ecran.width, ecran.height)
        except Exception: return False

    def _noter_zone_plein(self):
        """Memorise le rectangle du moniteur du plein ecran (centrage au retour en fenetre quand la fenetre n'a pas de place d'avant : lancee en plein ecran)."""
        try: ec = self.screen; self.zone_plein = (int(ec.x), int(ec.y), int(ec.width), int(ec.height))
        except Exception: pass

    def _raccourci_fenetre(self, symbol, modifiers):
        """F11 ou Alt + Entree, de n'importe ou (logos, titre, jeu, menu Echap, saisie du nom, combat) : bascule fenetre <-> plein ecran. La touche est avalee (ni validation, ni action du jeu) et, avec Alt, Alt ne vaut plus
        « discussion de groupe » (voir _fronts). -> True si consommee."""
        K = pyglet.window.key
        t = getattr(self, 'touches', None)
        alt = bool(modifiers & K.MOD_ALT) or (t is not None and bool(t[K.LALT] or t[K.RALT]))          # (le drapeau du systeme, ou l'etat des touches Alt : l'un des deux suffit)
        if not (symbol == K.F11 or (alt and symbol in (K.RETURN, K.ENTER))): return False
        if getattr(self.pause, 'capture', None) is not None: return False                    # menu Commandes en attente d'une touche : F11 y est « réservée » (reglages.RESERVEES)
        self.avalees.add(symbol)
        if alt: self.alt_cand = False
        if self._en_bascule or not hasattr(self, 'post'): return True
        try: self.basculer_plein_ecran()
        except Exception as ex: print('Bascule du plein écran impossible : %r' % (ex,), flush=True)
        return True

    def _journal_fenetre(self, quand):
        """Une ligne de journal : etat et taille de la fenetre (plein ecran ou non), zone de dessin et ecran ; ecrite a la creation, a la 1re image dessinee et a chaque bascule."""
        try:
            ec = self.screen; fb = self.get_framebuffer_size()
            nom = ('fenêtre', 'PLEIN ÉCRAN')[self.mode_fen] + ('' if bool(self.fullscreen) == (self.mode_fen > 0) else ' [INCOHÉRENT : fullscreen=%s]' % self.fullscreen)
            n = EK.ecran_de((ec.x, ec.y, ec.width, ec.height), self._lire_ecrans()[1]); n = '' if n is None else ' (écran %d)' % (n + 1)
            print('Fenêtre (%s) : %s, %d x %d, zone de dessin %d x %d, écran %d x %d%s' % (quand, nom, self.width, self.height, fb[0], fb[1], ec.width, ec.height, n), flush=True)
        except Exception as ex: print('Fenêtre (%s) : état illisible (%r)' % (quand, ex), flush=True)
