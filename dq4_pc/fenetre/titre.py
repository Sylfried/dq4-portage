"""Ecrans d'avant-partie : titre (ciel, logo), licence, saisie du nom, sauvegardes."""
import os
import numpy as np
import pyglet
from pyglet import gl
from dq4_pc.menus import avant_partie as AP
from dq4_pc.menus import ecran_sauvegardes as ES
from dq4_pc.rendu import ciel_titre as CT
from dq4_pc.fenetre.constantes import CIELS_ETENDUS, DECOR_BIAIS, SE_BOUTON


class TitreMixin:
    """Ecrans d'avant-partie : titre (ciel, logo), licence, saisie du nom, sauvegardes."""

    def _agrandir_logo_titre(self, loc, pos, Rb):
        """Ecran-titre : logo (modele 8901 : « DRAGON QUEST », « IV », sous-titre) et eclat anime (8900) agrandis de AP.LOGO_ECHELLE autour d'un meme point (avant_partie.agrandir_logo), sans decalage de profondeur.
        ECART VOULU avec l'APK (Sylfried, 03/11/2026, #108). Le facteur est reduit si le logo agrandi depasserait la largeur de la fenetre (fenetre tres etroite) ; DQ_LOGO_ECHELLE=1 : le logo d'origine."""
        try: voulu = float(os.environ.get('DQ_LOGO_ECHELLE', AP.LOGO_ECHELLE))
        except ValueError: voulu = AP.LOGO_ECHELLE
        if voulu == 1.0: return loc
        larg = 0.0; M = self._M_ville
        if M is not None:
            try:
                xs = []
                for sx in (-1.0, 1.0):
                    q = np.array(pos, float) + Rb @ np.array([sx * AP.LOGO_DEMI_LARGEUR, 0.0, 0.0]); c = M @ np.append(q, 1.0); xs.append(c[0] / c[3])
                larg = abs(xs[1] - xs[0]) / 2.0                              # largeur du logo de l'APK, en fraction de la largeur de la fenetre (NDC : -1 a 1)
            except Exception: larg = 0.0
        try: y0 = float(os.environ.get('DQ_LOGO_Y', AP.LOGO_Y_FIXE))
        except ValueError: y0 = AP.LOGO_Y_FIXE
        return AP.agrandir_logo(loc, AP.facteur_logo(larg, voulu), y0)

    def _ciel_titre(self, c, src):
        """Ecran-titre : le ciel (carreaux de nuages identiques qui glissent) est concu pour l'ecran portrait ; en 16/9 ses bords entreraient dans le champ et le meme carreau se repeterait 3 a 6 fois.
        Solution : la zone portrait garde le ciel d'origine ; de chaque cote, des bandes de meme geometrie dont la texture est etiree de facon variable (ciel_titre.py : raccord continu au bord de la zone, defilement suivi).
        Secours (structure inattendue, ou DQ_CIEL_COPIES : ancien comportement, pour comparer) : deux copies du ciel decalees de sa largeur, qui prolongent le motif tel quel."""
        for iobj, nm in self.noms.items():
            if 'kumo' not in nm.lower(): continue
            for key, deb, n in self.plages.get(iobj, []):
                if key not in c['textures']: continue
                if not os.environ.get('DQ_CIEL_COPIES'):
                    try:
                        cl = CT.CielLarge(self.carte_pos[key][deb:deb + n], self.objets.uv(key)[deb:deb + n], self.objets.col(key)[deb:deb + n])
                        seul = deb == 0 and n == len(self.carte_pos[key])                                                 # (le ciel est seul dans son groupe de texture)
                        if not os.environ.get('DQ_CIEL_BANDES') and seul:
                            if os.environ.get('DQ_CIEL_AGRANDI'): self.ciel_zoom = {'key': key}                          # essai #130 : ciel agrandi autour du centre de l'ecran, sans bandes
                            else: self.ciel_plat = {'key': key, 'ciel': cl, 'vl': None, 'nv': 0, 'degrade': None, 'cle': None}      # #174 (par defaut) : ciel a plat, hauteur de la texture = hauteur de la fenetre, repetition sur la largeur, effet de vague
                            continue
                        self.ciel_ext = {'ciel': cl, 'tex': self.tex_gl[(src, key)], 'key': key, 'deb': deb, 'vl': None, 'nv': 0}
                        continue
                    except Exception as ex: print('Ciel du titre : %s (copies decalees a la place)' % ex, flush=True)
                cur = self.objets.cur[key][deb:deb + n]; larg = float(cur[:, 0].max() - cur[:, 0].min())
                for dx in (-larg, larg):
                    vl = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', CT.positions_copie(cur, dx).ravel()), tex_coords=('f', self.objets.uv(key)[deb:deb + n].ravel()), colors=('f', self.objets.col(key)[deb:deb + n].ravel()))
                    self.carte_ext.append((self.tex_gl[(src, key)], vl, key, deb, n, dx))

    def _ciel_etendu(self, c, src, nom):
        """Plan de ciel des cartes de CIELS_ETENDUS (dpout, ev09 ; MAP-05) : concu pour l'ecran portrait, il s'arrete avant les bords de la fenetre en 16/9 (coins noirs). De part et d'autre, une copie SYMETRIQUE du plan (bord gauche et bord droit
        servent de miroir, memes coordonnees de texture : l'image se prolonge sans couture, a la maniere des copies du ciel du titre) ; la zone portrait centrale garde exactement le ciel d'origine. Ajoutee a `carte_ext` (dessinee et mise a jour comme les copies du titre)."""
        mots = CIELS_ETENDUS.get(nom, ())
        for iobj, nm in self.noms.items():
            if not any(m in nm.lower() for m in mots): continue
            for key, deb, n in self.plages.get(iobj, []):
                if key not in c['textures'] or (src, key) not in self.tex_gl: continue
                cur = self.objets.cur[key][deb:deb + n]
                if not len(cur): continue
                for xe in (float(cur[:, 0].min()), float(cur[:, 0].max())):
                    dx = ('miroir', xe)
                    vl = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', CT.positions_copie(cur, dx).ravel()), tex_coords=('f', self.objets.uv(key)[deb:deb + n].ravel()), colors=('f', self.objets.col(key)[deb:deb + n].ravel()))
                    self.carte_ext.append((self.tex_gl[(src, key)], vl, key, deb, n, dx))

    def _tracer_ciel_plat(self, t):
        """Ciel de l'ecran-titre a plat (#174), a la place du groupe du ciel d'origine : la texture a la hauteur de la fenetre et se repete sur la largeur, avec l'effet de vague (ciel_titre.ciel_ecran ; defilement de l'objet suivi,
        degrade de teinte des rangees d'origine). -> True s'il a ete dessine ; toute erreur : False (le ciel d'origine est dessine par l'appelant) et le rendu a plat est coupe."""
        c = self.ciel_plat
        if c is None or self._M_ville is None: return False
        try:
            key = c['key']; cl = c['ciel']; phi = float(self.objets.cur[key][0, 0] - self.carte_pos[key][0, 0])
            cle = (np.asarray(self._M_ville, float).tobytes(), float(self._aspect_ville))
            if c['cle'] != cle: c['degrade'] = CT.degrade_ecran(self._M_ville, cl.rangees, cl.x_mil); c['cle'] = cle
            P, U, C = CT.ciel_ecran(self._aspect_ville, phi / cl.periode, c['degrade']); n = len(P)
            if c['vl'] is None or c['nv'] != n:
                if c['vl'] is not None: c['vl'].delete()
                c['vl'] = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', P.ravel()), tex_coords=('f', U.ravel()), colors=('f', C.ravel())); c['nv'] = n
            else: c['vl'].position[:] = P.ravel(); c['vl'].tex_coords[:] = U.ravel(); c['vl'].colors[:] = C.ravel()
            self._dom_lie = None                          # sommets reecrits APRES le 1er trace de l'image : sans rebind + commit() ils ne partent pas (voir _tracer_ciel)
            gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
            self.prog['mvp'] = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)          # coordonnees d'ecran normalisees : pas de projection
            self._tracer(t, c['vl'])
            self.prog['mvp'] = tuple(float(x) for x in self._M_ville.T.ravel())
            gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
            return True
        except Exception as ex:
            self.ciel_plat = None; self.prog['mvp'] = tuple(float(x) for x in self._M_ville.T.ravel()); gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
            print('Ciel du titre (a plat) desactive : %s' % ex, flush=True)
            return False

    def _tracer_ciel(self, r, net_o):
        """Bandes de ciel de l'ecran-titre (apres le decor opaque, meme plan que le ciel d'origine : decalage de profondeur pour passer devant sa partie hors de la zone portrait). Toute erreur : on garde le ciel d'origine seul."""
        c = self.ciel_ext
        if c is None or self._M_ville is None: return
        try:
            key = c['key']; phi = float(self.objets.cur[key][c['deb'], 0] - self.carte_pos[key][c['deb'], 0])
            b = c['ciel'].bandes(self._M_ville, self._aspect_ville, phi)
            if b is None: return
            P, U, C = b; n = len(P)
            if c['vl'] is None or c['nv'] != n:
                if c['vl'] is not None: c['vl'].delete()
                c['vl'] = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', P.ravel()), tex_coords=('f', U.ravel()), colors=('f', C.ravel())); c['nv'] = n
            else: c['vl'].position[:] = P.ravel(); c['vl'].tex_coords[:] = U.ravel(); c['vl'].colors[:] = C.ravel()
            t = r.get(key, c['tex']) if r else c['tex']
            self._dom_lie = None                          # sommets crees ou reecrits APRES le 1er trace de l'image (le decor opaque vient d'etre trace) : sans rebind + commit() ils ne partent pas : a la 1re image du titre les bandes manquaient (cotes noirs), puis elles etaient en retard d'une image
            gl.glEnable(gl.GL_POLYGON_OFFSET_FILL); gl.glPolygonOffset(0.0, -DECOR_BIAIS * (len(self.carte_vl) + 2))
            self.prog['net'] = net_o if (r is None or key not in r) else 0.0; self.prog['tsize'] = (float(t.width), float(t.height)); self._tracer(t, c['vl'])
            gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
        except Exception as ex:
            gl.glDisable(gl.GL_POLYGON_OFFSET_FILL); self.ciel_ext = None
            print('Ciel du titre (bandes) desactive : %s' % ex, flush=True)

    def _port_depart(self, port):
        """Vrai si ce port est le menu de depart (type 53, Make_StartMenuSecond)."""
        fe = self.ui_g.f.get(port) if self.ui_g else None
        return bool(fe and fe.typ == 53)

    def _sauv_ouvrir(self):
        if self.statut_depart is None: self.statut_depart = self.moteur.statut_catalogue()          # etat des journaux quand le moteur a construit le menu de depart (ses boutons grises / absents en dependent)
        self.sauv = ES.EcranSauvegardes(self); self.appui = None; self.survol_nd = None

    def _sauv_fermer(self):
        s, self.sauv = self.sauv, None
        if s is not None and s.a_recharger: self._apres_import()

    def _apres_import(self):
        """Des journaux viennent d'etre importes (le catalogue du moteur a deja ete relu par l'ecran Sauvegardes)."""
        self.toast('Sauvegardes importées')

    def _cadre_depart(self, fe, cx, cy, s, visibles=False):
        """Cadre noir (comme les autres menus du portage) derriere tout le menu de depart (ou de la fenetre d'avant-partie centree)."""
        r = fe.cadre_menu(22.0, visibles)
        if r is None: return
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        self.pause._cadre(cx + r[0] * s, cy + r[1] * s, (r[2] - r[0]) * s, (r[3] - r[1]) * s, s * 800.0 / 900.0)
        self.pause._melange()

    ciel_plat = None                                                   # #174 (par defaut) : {'key': groupe du ciel du titre, 'ciel': CielLarge, 'vl', 'nv', 'degrade', 'cle'} quand le ciel est dessine a plat a l'echelle de l'ecran (ciel_titre.ciel_ecran)

    ciel_zoom = None                                                   # essai #130 (DQ_CIEL_AGRANDI=1) : {'key': groupe du ciel du titre} quand le ciel est agrandi (ciel_titre.zoom_ecran) au lieu d'etre prolonge par des bandes

    def _maj_titre(self):
        """Port 12 = fenetre de type 73 (Make_TitleTouch) : le moteur ne lui donne aucune case, « Touchez l'ecran » et le copyright sont dessines par Unity (TapToStart) ; le code 0 est CountReset."""
        mo = self.moteur; f = mo.ui.f.get(12)
        if bool(f and f.get('type') == 73 and f.get('act')):
            if self.titre is None: self.titre = AP.TitreTouch(mo.images, self.ap_fich); self.titre_n = f.get('n_codes', {}).get(0, 0)
            n = f.get('n_codes', {}).get(0, 0)
            if n > self.titre_n: self.titre.reset()
            self.titre_n = n
            self.titre.maj(mo.images)
        else: self.titre = None
        self._maj_saisie_nom(); self._maj_licence()
        if self.sauv is not None: self.sauv.maj()

    def _maj_licence(self):
        """Fenetre de type 80 (Make_License) sur le port 15 : le texte des licences est dessine par Unity (LicenseNobu)."""
        mo = self.moteur; port = next((q for q, f in mo.ui.f.items() if f.get('type') == 80 and not f.get('ferme')), None)
        if port is None: self.licence = None; return
        if self.licence is None: self.port_saisie = port; self.licence = AP.Licence(self.ap_fich.get('licence'))
        mo.etat.fondu['noir'] = 0                                         # (l'ecran reste noir tant que la fenetre est ouverte : pas de reouverture automatique apres 6 s)

    def _licence_retour(self):
        self.moteur.envoyer_menu(self.port_saisie, 1, -1, 0x20); self.menu_relacher = self.port_saisie                  # (retour : manette 0x20, muet comme dans MenuPortItem.Update)

    def _licence_clic(self, x, y, bouton):
        li = self.licence; nom = li.zone(x, y)
        if bouton == pyglet.window.mouse.RIGHT: self._licence_retour(); return
        if li.sur_barre(x, y): li.glisse = True; li.glisser(y); return                 # barre de defilement : le curseur se glisse avec le pointeur
        if nom == 'retour': self._licence_retour()
        elif nom == 'politique':
            self.son.jouer_se(SE_BOUTON)
            try: import webbrowser; webbrowser.open(AP.URL_CONFIDENTIALITE)
            except Exception as ex: self.toast('Ouverture impossible : %r' % (ex,))

    def _dessiner_sauvegardes(self):
        if self.sauv is None: return
        cx, cy, ech = self._ui_repere(); self.sauv.dessiner(self, cx, cy, ech)

    def _dessiner_licence(self):
        if self.licence is None: return
        cx, cy, ech = self._ui_repere(); self.licence.dessiner(self, cx, cy, ech)

    def _maj_saisie_nom(self):
        """Fenetre de type 55 (StartNameEntry) : le clavier de saisie du nom est tenu par Unity ; il est visible tant que le moteur a envoye [12, 1, 1] (le message [12, 0, 8] donne le nombre de caracteres)."""
        mo = self.moteur; port = next((q for q, f in mo.ui.f.items() if f.get('type') == 55 and not f.get('ferme')), None)
        f = mo.ui.f.get(port) if port is not None else None
        clav = bool(f and f['indic'].get(1) == 1)
        if clav and not self.saisie_nom.actif: self.port_saisie = port; self.saisie_nom.ouvrir((f['indic'].get(0, 8) & 0xff) or 8)
        elif not clav and self.saisie_nom.actif: self.saisie_nom.fermer()

    def _saisie_nom_en_cours(self):
        return self.saisie_nom.actif and not self.moteur.msg_visible and not self.pause.ouvert

    def _saisie_nom_ok(self, nom):
        """OK : [2, nombre d'octets] puis les octets UTF-8 du nom (deux par nombre, petit-boutiste), tous deux avant la prochaine image du moteur."""
        import struct
        b = nom.encode('utf-8'); n = len(b); b += b'\0' * (n % 2)
        self.moteur.envoyer_menu(self.port_saisie, 2, n); self.moteur.envoyer_menu(self.port_saisie, *struct.unpack('<%dh' % (len(b) // 2), b))

    def _saisie_nom_retour(self):
        """Retour : comme la touche B sur la fenetre 55, [1, -1, 32] (le moteur revient a la liste des journaux)."""
        self.moteur.envoyer_menu(self.port_saisie, 1, -1, 0x20); self.menu_relacher = self.port_saisie

    def _dessiner_saisie_nom(self):
        if not self.saisie_nom.actif: return
        cx, cy, ech = self._ui_repere(); self.saisie_nom.dessiner(cx, cy, ech)

    def _dessiner_titre(self):
        if self.titre is None: return
        cx, cy, ech = self._ui_repere(); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        self.titre.dessiner(cx, cy, ech, self.height)
