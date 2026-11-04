"""Clavier, souris et manette : evenements de la fenetre et lecture des touches."""
import os
import pyglet
from dq4_pc.fenetre import entrees as EN
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.noyau import moteur as MO
from dq4_pc.fenetre.constantes import ACT_FRONTS, BTN_CARTE, BTN_DISCUSSION, BTN_MENU, BTN_PAROLE, BTN_SAUVEGARDES, SE_BOUTON, bruit_bouton


class ClavierSourisMixin:
    """Clavier, souris et manette : evenements de la fenetre et lecture des touches."""

    def on_text(self, texte):
        """Menu Echap : saisie d'une valeur au clavier."""
        if self._pret and self.pause.ouvert and self.pause.saisie is not None: self.pause.texte(texte)
        elif self._pret and self._saisie_nom_en_cours(): self.saisie_nom.texte_saisi(texte)
        return pyglet.event.EVENT_HANDLED

    def on_key_press(self, symbol, modifiers):
        """Seule touche fixe : Echap (menu). Les autres sont celles du menu Commandes (pad, infos a l'ecran) ; le menu ouvert recupere toutes les touches."""
        K = pyglet.window.key
        if self._raccourci_fenetre(symbol, modifiers): return pyglet.event.EVENT_HANDLED          # F11 / Alt + Entree : de n'importe ou (logos, titre, jeu, menu Echap)
        if symbol in (K.LALT, K.RALT): self.alt_cand = True                # Alt seul = discussion de groupe, au relachement (voir on_key_release et _fronts)
        if not self._pret: self._logo_touche = True; return pyglet.event.EVENT_HANDLED
        self.garde_souris.clavier(self.souris)                             # le clavier a la main : le survol ne reprend qu'au premier vrai mouvement du pointeur (un clic reprend la main aussitot)
        if self.pause.ouvert: self.pause.touche(symbol, modifiers); return pyglet.event.EVENT_HANDLED
        self.dernier_peripherique = 'clavier'
        if self._saisie_nom_en_cours(): self.saisie_nom.touche(symbol, modifiers); return pyglet.event.EVENT_HANDLED          # saisie du nom : le clavier lui appartient
        if self.sauv is not None: self.sauv.touche(symbol, modifiers); return pyglet.event.EVENT_HANDLED                       # ecran Sauvegardes (export / import)
        if self.licence is not None:                                       # ecran Licence : defilement et retour
            pas = {K.UP: -30.0, K.DOWN: 30.0, K.PAGEUP: -360.0, K.PAGEDOWN: 360.0, K.HOME: -1e9, K.END: 1e9}.get(symbol)
            if pas is not None: self.licence.defiler(pas)
            elif symbol in (K.ESCAPE, K.BACKSPACE) or self.reg.action_de(symbol) == 'B': self._licence_retour()
            return pyglet.event.EVENT_HANDLED
        if symbol == K.ESCAPE:                                             # Echap : retour dans les menus du jeu et la carte (comme la touche Annuler), sinon le menu Echap
            if self._echap_retour(): self.clic_b = True
            else: self.pause.ouvrir()
            return pyglet.event.EVENT_HANDLED
        if self.reg.action_de(symbol) == 'infos': self.aide = not self.aide; self.reg['infos'] = self.aide; return pyglet.event.EVENT_HANDLED
        if self.reg.action_de(symbol) == 'vit_combat': self.changer_vitesse_combat(); return pyglet.event.EVENT_HANDLED          # Manuel -> Normal -> Rapide -> Très rapide (en combat comme ailleurs)
        if self.reg.action_de(symbol) == 'historique' and self.titre is None and self.moteur.etat.partie in (MO.PARTIE_VILLE, MO.PARTIE_COMBAT, MO.PARTIE_CHAMP): self._touche_historique(); return pyglet.event.EVENT_HANDLED          # touche de l'historique des messages (#187 : seulement quand le joueur a la main sur son personnage)
        n = self._num_etat(symbol)
        if n is not None:                                                  # raccourcis des etats : chiffre = enregistrer, Ctrl + chiffre = charger
            if self._tenue('modif'):
                self.combo[1] = True
                if self.infos_etat(n):
                    try: self.charger_etat(n); self.toast('État %d chargé' % n)
                    except Exception as ex: self.toast('Chargement impossible : %r' % (ex,))
                else: self.toast('État %d vide' % n)
            else: self.sauve_rapide = n
            return pyglet.event.EVENT_HANDLED
        if symbol in (K.LSHIFT, K.RSHIFT) or symbol in self.reg.codes('modif'):      # Maj + touche modificatrice (sans chiffre) : annule le dernier chargement, au relachement
            ctrl = symbol in self.reg.codes('modif') or self._tenue('modif'); maj = symbol in (K.LSHIFT, K.RSHIFT) or self.touches[K.LSHIFT] or self.touches[K.RSHIFT]
            if ctrl and maj: self.combo = [True, False]
        return pyglet.event.EVENT_HANDLED

    def on_key_release(self, symbol, modifiers):
        K = pyglet.window.key
        self.avalees.discard(symbol)
        if symbol in (K.LALT, K.RALT):         # Alt relache : si rien d'autre n'a ete fait pendant (pas Alt + Entree), c'est l'appui de la touche de discussion de groupe
            cand, self.alt_cand = self.alt_cand, False
            if cand and self._pret and not self.pause.ouvert and symbol in self.reg.codes('discussion') and not (self.touches[K.LALT] or self.touches[K.RALT]): self.alt_tap = True
        if (symbol in (K.LSHIFT, K.RSHIFT) or symbol in self.reg.codes('modif')) and self.combo[0]:
            declenche = not self.combo[1]; self.combo = [False, False]
            if declenche and self._pret and not self.pause.ouvert: self.annuler_chargement()

    def _echap_retour(self):
        """Echap sert de touche Annuler quand une fenetre du jeu (menu, carte) est ouverte sur le terrain : sinon il ouvre le menu Echap (combat, messages et terrain libre compris)."""
        mo = self.moteur
        if mo.etat.partie == MO.PARTIE_DEPART: return self.saisie_nom.actif or self.licence is not None or (not mo.msg_visible and mo.menu_actif() is not None)           # menu de depart : Echap = Annuler (le retour de la racine = quitter)
        if mo.etat.partie in MO.PARTIES_MINIJEU:          # casino, bestiaire : Echap = bouton retour de la fenetre ouverte (manette 0x20) ; rouleaux en marche, message, cartes en cours de distribution : pas de retour, le menu Echap s'ouvre
            p = mo.menu_actif()
            return p is not None and not mo.msg_visible and self._retour_possible(p)
        if mo.etat.partie not in (MO.PARTIE_VILLE, MO.PARTIE_CHAMP) or mo.etat.effet is not None or getattr(mo.etat, 'effet_ecran', None) is not None: return False
        return bool(self.carte_ouverte) or (not mo.msg_visible and mo.menu_actif() is not None)

    def _retour_possible(self, port):
        """Une fenetre visible du jeu a-t-elle un bouton Annuler / Retour (touche de manette 0x20) en ce moment ? (casino, bestiaire : Echap le presse ; sinon il ouvre le menu Echap)"""
        if not self.ui_g: return False
        for q in [port] + [q for q, fq in self.moteur.ui.f.items() if q > 1 and fq['vis']]:
            fe = self.ui_g.f.get(q)
            if fe and any(b[1] & 0x20 for b in fe.boutons()): return True
        return False

    def _bouton_sous(self, port, x, y):
        """Bouton de la fenetre `port` sous le pointeur (le plus en avant d'abord) : (numero, manette, profondeur, identifiant de l'element) ou None."""
        h = [(pr, b, pad, nid) for b, pad, x0, y0, x1, y1, pr, nid in self._zones(port) if x0 <= x <= x1 and y0 <= y <= y1]
        if not h: return None
        pr, b, pad, nid = max(h, key=lambda t: t[0])
        return b, pad, pr, nid

    def on_mouse_press(self, x, y, bouton, modifiers):
        """Souris = tactile du mobile : appui sur un bouton du menu actif (MenuPortItem.Update, PUSH_STATE_BEGIN) ; clic droit = Annuler."""
        M = pyglet.window.mouse; mo = self.moteur
        if not self._pret: self._logo_touche = True; return
        self.dernier_peripherique = 'souris'; self.garde_souris.clic(); self.souris = (x, y)             # un clic agit toujours, aussitot : la souris a la main
        if bouton == M.MIDDLE: return                                # bouton du milieu : sans effet (il ne servait qu'a la camera, retiree en #264 ; jamais un clic de menu, de message ou de bouton)
        if self.pause.ouvert: self.pause.clic(x, y, bouton); return
        if self._saisie_nom_en_cours(): self.saisie_nom.clic(x, y, bouton); return
        if self.sauv is not None: self.sauv.clic(x, y, bouton); return
        if self.licence is not None: self._licence_clic(x, y, bouton); return
        if self.titre is not None and bouton == M.LEFT: self.clic_a = True; return                 # titre : un toucher n'importe ou valide (la manette recoit A)
        if bouton == M.RIGHT: self.clic_b = True; return
        if bouton == M.LEFT:
            vis = self.hud.visibles()
            if vis:
                n = self.hud.appuyer(x, y, vis)                                                            # boutons a l'ecran (Carte, Commandes, Discussion) et croix
                if n: n != HM.CROIX and self.son.jouer_se(SE_BOUTON); return
        if bouton == M.LEFT and self._terrain_libre(): self.clic_a = True; return                                    # terrain libre : un clic gauche n'importe ou = touche d'action, comme l'espace (#131 ; plus de clic sur la bulle seule)
        if bouton != M.LEFT or not self.ui_rendu: return
        cp = self._carte_ports()
        if 22 in cp:                                                               # boutons de la fenetre de la carte (sans numero) : retour (touche de manette 0x400, ferme la carte) et mode (haut de la manette, change de vue), actifs au relachement
            h = self._bouton_sous(cp[22], x, y)
            if h and h[0] == -1 and h[1] in (0x400, 2): self.appui = (cp[22], h[0], h[1]); return                      # (retour et mode : manette 0x400 et 2, muets comme dans MenuPortItem.Update)
        touches = [(h[2], -i, port, h) for i, port in enumerate(mo.menus_saisie()) for h in [self._bouton_sous(port, x, y)] if h]      # tous les menus qui attendent la saisie : bouton le plus en avant, puis fenetre la plus recente
        if touches:
            _, _, port, h = max(touches, key=lambda t: t[:2]); self.appui = (port, h[0], h[1]); self.appui_nd = h[3]; bruit_bouton(h[1]) and self.son.jouer_se(SE_BOUTON); return
        if mo.msg_visible: self.clic_a = True                                      # toucher le message = page suivante

    def on_mouse_motion(self, x, y, dx, dy):
        """Survol de la souris : le bouton sous le pointeur est selectionne comme avec les fleches. Menu tactile (curseur local) : immediat ; menu a curseur du moteur :
        le curseur est amene sur le bouton par des appuis de direction, une image sur trois (voir _survol_pas)."""
        if not self._pret: return
        self.souris = (x, y)
        if not self.garde_souris.bouge((x, y)): return                # simple tremblement apres l'usage du clavier : ni le mode, ni la selection ne changent (ecart cumule depuis la derniere touche, voir entrees.GardeSouris)
        self.dernier_peripherique = 'souris'
        if self.pause.ouvert: self.pause.survol(x, y); return
        if self._saisie_nom_en_cours(): self.saisie_nom.survol(x, y); return
        if self.sauv is not None: self.sauv.hover(x, y); return
        if self.licence is not None: self.licence.survol = self.licence.zone(x, y); return
        if not self.ui_rendu or self.appui: return
        mo = self.moteur
        touches = [(h[2], -i, port, h) for i, port in enumerate(mo.menus_saisie()) for h in [self._bouton_sous(port, x, y)] if h and (h[0] >= 0 or self._est_bouton(port, h[3]))]
        if not touches: self.survol = None; return                  # hors d'un bouton : l'element survole en dernier reste seul en surbrillance (le curseur du moteur y est aussi) ; effacé par on_mouse_leave ou une touche
        _, _, port, h = max(touches, key=lambda t: t[:2]); f = mo.ui.f[port]; self.survol_nd = (port, h[3])
        if h[0] < 0: self.survol = None                              # bouton sans numero (retour, fleches de page) : seul l'element est allume, le curseur du menu ne bouge pas
        elif f.get('grille'): self.survol = [port, h[0], 0] if f['cur'] != h[0] else None
        elif self.cur_local.get((port, f['ordre'])) != h[0]: self.cur_local[(port, f['ordre'])] = h[0]; self.survol = None

    def _est_bouton(self, port, nid):
        """Vrai si l'element a un dessin de bouton (plaque, partie 7) ou de fleche (partie 10) : le cadre de fenetre qui couvre l'ecran (manette 128) n'en est pas un."""
        nd = self.ui_g.f[port].N.get(nid) if self.ui_g and port in self.ui_g.f else None
        return bool(nd) and any(m.get('part') in (7, 10) for m in nd['mats'])

    def on_mouse_leave(self, x, y):
        self.survol_nd = None
        if self.pause.ouvert: self.pause.sortie()                       # menu Echap : le pointeur a quitte la fenetre, plus rien n'est survole (les plaques se rallument)

    def _survol_pas(self):
        """Un appui de direction vers le bouton survole (menus dont le curseur est dans le moteur), tant que le curseur n'y est pas (au plus 24 appuis)."""
        sv = self.survol; mo = self.moteur
        if not sv: return
        port, b, n = sv; f = mo.ui.f.get(port)
        if f is None or not f.get('grille') or port != mo.menu_actif() or f['cur'] == b or n >= 24: self.survol = None; return
        if self.n % 3: return
        cols = max(1, f['grille'][0]); cc, cr = f['cur'] % cols, f['cur'] // cols; tc, tr = b % cols, b // cols
        pad = (1 if tr > cr else 2) if tr != cr else (4 if tc > cc else 8)       # manette du jeu : bas 1, haut 2, droite 4, gauche 8
        mo.envoyer_menu(port, 1, -1, pad); self.menu_relacher = port; sv[2] += 1

    def on_mouse_release(self, x, y, bouton, modifiers):
        """Relachement sur le meme bouton (PUSH_STATE_FINISH) : MenuPort.Send([1, numero du bouton, touche de manette du bouton])."""
        if not self._pret: return
        if bouton == pyglet.window.mouse.MIDDLE: return
        if self.pause.ouvert: self.pause.relache(x, y, bouton); return
        if self.licence is not None: self.licence.glisse = None; return
        if bouton == pyglet.window.mouse.LEFT and self.hud.croix_on:
            if self.hud.croix_relacher() and self._terrain_libre(): self.clic_a = True              # toucher du rond central de la croix (sans glisser) = touche d'action, comme sur mobile (#131)
            return
        if bouton == pyglet.window.mouse.LEFT and self.hud.appui:
            n = self.hud.relacher(x, y, self.hud.visibles())
            if n == HM.COMBAT: self.changer_vitesse_combat('bouton')                      # bouton de vitesse de l'ecran de combat : ne passe rien au moteur
            elif n: self.hud_decl = HM.DECL[n]
            return
        if bouton != pyglet.window.mouse.LEFT or not self.appui: return
        port, b, pad = self.appui; self.appui = None
        h = self._bouton_sous(port, x, y)
        if b == -1 and pad == 0x400:                       # bouton retour : MenuPortItem.Update ajoute 0x400 aux touches du jeu (le moteur ferme la carte) au lieu d'envoyer un message au port
            if h and h[0] == b: self.hud_decl = BTN_DISCUSSION
            return
        if b == -1 and pad == 2:                           # bouton « mode de la carte » de la fenetre (type 22, icone 19 / 20 / 2 envoyee par le moteur) : haut de la manette = change de vue (traite avec la touche Carte)
            if h and h[0] == b and h[1] == pad: self.carte_bascule = True
            return
        if h and h[0] == b and b == BTN_SAUVEGARDES and self._port_depart(port): self._sauv_ouvrir(); return                # bouton « Sauvegardes » du menu de depart (a la place de « Sauv. cloud ») : propre au portage
        if h and h[0] == b and port in self.moteur.menus_saisie():
            self.moteur.envoyer_menu(port, 1, b, pad); self.menu_relacher = port
            f = self.moteur.ui.f.get(port)
            if f: f['cur'] = b

    def pad(self):
        """Manette du jeu d'apres les touches reglees : directions, A (action / valider), B (annuler). Sur le terrain, seules les touches de deplacement (et la croix a l'ecran) marchent ;
        dans un menu, un message ou un combat, les fleches deviennent des directions."""
        p = 0; libre = self._terrain_libre()
        for act, bit in (('haut', MO.HAUT), ('bas', MO.BAS), ('gauche', MO.GAUCHE), ('droite', MO.DROITE)):
            if self._tenue(act): p |= bit
        if not libre:
            for act, bit in (('cam_haut', MO.HAUT), ('cam_bas', MO.BAS), ('cam_gauche', MO.GAUCHE), ('cam_droite', MO.DROITE)):
                if self._tenue(act): p |= bit
        else:
            p |= self.hud.croix_bits()                                                                        # croix a l'ecran tenue a la souris : une direction de plus (relative a l'ecran, comme les touches)
        if self._tenue('A'): p |= MO.A
        if self._tenue('B'): p |= MO.B
        return p

    def _bruit_hud(self, nom):
        """Touche Commandes / Discussion / Carte sur le terrain : le bruitage 300 du bouton a l'ecran, dans les memes situations qu'au doigt (#60, D-156 ; le bouton est-il permis par le moteur, qu'il soit affiche ou non)."""
        if self.hud.permis(nom): self.son.jouer_se(SE_BOUTON)

    def _fronts(self):
        """Appuis (front montant) de X, Start, L et R depuis la derniere image du moteur."""
        r = {}; K = pyglet.window.key; k = self.touches
        for a in ACT_FRONTS:
            if a == 'discussion': v = any(k[c] and c not in self.avalees for c in self.reg.codes(a) if c not in (K.LALT, K.RALT))        # (Alt : au relachement, voir alt_tap : Alt + Entree ne doit pas lancer la discussion de groupe)
            else: v = self._tenue(a)
            r[a] = v and not self.act_prec.get(a, False); self.act_prec[a] = v
        if self.alt_tap: r['discussion'] = True; self.alt_tap = False
        if r['discussion'] and os.environ.get('DQ_DEBUG'): print('FRONT discussion n=%d' % self.n, flush=True)
        if self.avalees: self.avalees = {c for c in self.avalees if k[c]}          # (une touche avalee relachee hors de la fenetre : la liste se vide)
        if self.alt_cand and not (k[K.LALT] or k[K.RALT]): self.alt_cand = False
        return r

    def _entrees(self, p):
        """Touches et clics de ce pas du moteur -> (p, decl) : boutons tenus et boutons qui viennent d'etre presses, tels que le moteur les veut (menu qui a la saisie : tout passe par `_saisie_menu`, p = decl = 0).
        Seulement dans les pas « reels » : un pas supplementaire d'un combat accelere (`tick(muet=True)`) n'en lit aucune, pour que la cadence des touches (repetition des fleches, premier appui) ne change pas."""
        mo = self.moteur
        if self.clic_a: p |= MO.A; self.clic_a = False                  # clics de souris : page suivante / annuler
        if self.clic_b: p |= MO.B; self.clic_b = False
        decl = p & ~self.pad_prec                      # boutons qui viennent d'etre presses
        fr = self._fronts()
        if self.moteur.msg_visible and fr['menu']: p |= MO.A; decl |= MO.A        # Entree et Espace tournent aussi les pages des messages
        for bit in (MO.HAUT, MO.BAS, MO.GAUCHE, MO.DROITE):      # repetition des directions maintenues (curseurs de menu)
            if p & bit:
                self.rep[bit] = self.rep.get(bit, 0) + 1
                if self.rep[bit] > 12 and (self.rep[bit] - 12) % 4 == 0: decl |= bit
            else: self.rep[bit] = 0
        self.pad_prec = p
        mo = self.moteur
        if self.menu_relacher is not None:                 # fin de l'appui OK / Annuler envoye au menu
            mo.envoyer_menu(self.menu_relacher, 1, -1, 0); self.menu_relacher = None
        carte = self._carte_ports() if not mo.msg_visible else {}
        if bool(carte) != self.carte_ouverte: self.carte_ouverte = bool(carte); self.carte_vue = 1           # carte ouverte : premiere version
        liste = bool(carte) and 24 in carte and 25 in carte and mo.ui.f.get(carte[24], {}).get('cases') and mo.boutiques()[1] > 0          # ville avec des boutiques : la carte a une 2e vue, la liste des boutiques (type 24)
        self.carte_deux_vues = (25 in carte and 26 in carte) or bool(liste)
        if carte:
            # Touche Carte : 1re fois la premiere version (en ville : le plan), 2e fois l'autre version (en ville : la liste des boutiques ; haut de la manette sur la fenetre du plan : FieldImageMap::execute), 3e fois ferme (bouton retour : 0x400, comme MenuPortItem.Update d'Unity) ;
            # Annuler ou le bouton retour ferment aussi. Le curseur et les fleches ne servent pas ici (sauf les fleches de la liste des boutiques : boutique precedente / suivante).
            bascule, self.carte_bascule = self.carte_bascule, False
            if liste:                                              # ville : M = plan, puis liste des boutiques, puis ferme ; le bouton « mode de la carte » alterne plan / liste
                en_liste = bool(mo.ui.f.get(carte[24], {}).get('vis'))
                if bascule: mo.envoyer_menu(carte[25], 1, -1, 2); self.menu_relacher = carte[25]
                elif fr['carte'] and not en_liste: mo.envoyer_menu(carte[25], 1, -1, 2); self.menu_relacher = carte[25]
                elif fr['carte'] or (decl & MO.B): self.hud_decl = BTN_DISCUSSION
                elif en_liste and decl & (MO.GAUCHE | MO.DROITE): mo.envoyer_menu(carte[24], 1, -1, 4 if decl & MO.DROITE else 8); self.menu_relacher = carte[24]         # fleches de la liste : boutique suivante / precedente
            elif (fr['carte'] and self.carte_vue == 1 or bascule) and self.carte_deux_vues:           # (le bouton de l'ecran « mode de la carte » change de vue dans les deux sens)
                mo.envoyer_menu(carte[25], 1, -1, 2); self.menu_relacher = carte[25]; self.carte_vue = 3 - self.carte_vue; fr['carte'] = False
            elif fr['carte'] or (decl & MO.B): self.hud_decl = BTN_DISCUSSION
        port = None if carte or self.sauv is not None else mo.menu_actif()
        if port is not None and mo.msg_visible and not mo.ui.f[port].get('entree'): port = None
        if port is not None and mo.msg_visible and decl & MO.A and self._quitter_seul(port): port = None          # arene (combat) : la seule fenetre ouverte est « Quitter » (manette 0x400) et A doit tourner la page du message (touche du terrain pour le moteur)
        if port is not None: port = self._port_clavier(port)      # critere memoire seul : le message d'abord
        if port is not None and self.menu_relacher is None: self._survol_pas()
        if port is not None:                               # un menu attend les touches : elles lui sont envoyees, pas au terrain
            f_port = mo.ui.f.get(port)
            self._saisie_menu(port, decl | (MO.A if fr['menu'] else 0) | (MO.B if fr['carte'] and f_port and f_port.get('type') == 25 else 0) | (MO.GAUCHE if fr['L'] else 0) | (MO.DROITE if fr['R'] else 0), (1 if fr['L'] else 0) | (2 if fr['R'] else 0))        # L / R = gauche / droite (page precedente / suivante des menus a une colonne)
            p = decl = 0
        elif self.titre is not None:                       # ecran-titre : seul A valide (Espace, Entree ou toucher) ; ni marche, ni camera
            p = decl = MO.A if (decl & MO.A or fr['menu']) else 0
        elif (self.saisie_nom.actif and not mo.msg_visible) or self.licence is not None or self.sauv is not None: p = decl = 0           # saisie du nom, ecran Licence : tout passe par le clavier du portage
        elif not mo.msg_visible:
            # sur le terrain : A = parler / examiner, Annuler, X ou Start = ouvrir le menu (le moteur veut ces boutons seuls)
            hd, self.hud_decl = self.hud_decl, 0                # (le moteur veut ces boutons seuls) A, puis boutons a l'ecran, puis touches Commandes / Discussion / Carte
            if decl & MO.A:
                decl = BTN_PAROLE
            elif hd: decl = hd
            elif fr['menu']: decl = BTN_MENU; self._bruit_hud('menu')
            elif fr['discussion']: decl = BTN_DISCUSSION; self._bruit_hud('discussion')
            elif fr['carte']: decl = BTN_CARTE; self._bruit_hud('carte')
            p &= ~(MO.A | MO.B)
        elif decl & MO.A: p, decl = EN.toucher_pour_le_moteur(p, decl, MO.A, MO.B, BTN_PAROLE, mo.attend_toucher())          # message ouvert : A tourne la page (0x10) ; le menu du don d'experience, a son dernier etat, attend le toucher d'ecran (0x100 seul)
        return p, decl
