"""Camera : zoom, distance, rotation, recentrage, camera des villes / du combat / du titre, correction des bords des sprites."""
import math, os, time
import numpy as np
import pyglet
from dq4_pc.fenetre import entrees as EN
from dq4_pc.noyau import moteur as MO
from dq4_pc.noyau import priorite_jeu as PJ
from dq4_pc.persistance import reglages as RG
from dq4_pc.fenetre.constantes import (ASPECT_PORTRAIT, BAS_DEF, CAM_ANGLE_MAX, CAM_ANGLE_MIN, CAM_CENTRE_MAX, CAM_DIST_VIT, CAM_LACET_VIT,
    CAM_MENE_DIST, CAM_RECENTRE_ANGLE, CAM_SCENE_TAU, CAM_RECENTRE_DIST, CAM_RECENTRE_LACET, CAM_SAUT_VILLE, CAM_TANGAGE_VIT, CAM_Y_TAU, CARTE_TITRE, CB_DEC_Z,
    CB_ECHELLE_DECOR, CB_FAR, CB_FOV_NOM, CB_NEAR, CB_YOFFSET, CH_ECHELLE, CH_PX, CH_VUE_HAUT, CORRECTION_BORDS_DEF, DIST_ADJ_VILLE, FOV_VILLE_DEF,
    HEROS_FRAC, MODE_PP, SPRITE_ECHELLE, SPRITE_H, VILLE_FAR, VILLE_NEAR, ZOOM_MAX, ZOOM_MIN)
from dq4_pc.fenetre.aides import camera_libre, hauteur_camera, matrice, rot_unity


class CameraMixin:
    """Camera : zoom, distance, rotation, recentrage, camera des villes / du combat / du titre, correction des bords des sprites."""

    def _camera_champ(self, e, aspect):
        """Carte du monde, comme Field.Init / Field.SetPosition du jeu : camera orthographique vue de dessus (Rotate(90, 0, 0)), centree sur le point donne par le moteur
        (en pixels de 16 par tuile). Le haut de l'ecran est le nord (-Z), l'est est a droite. Hauteur visible = CH_VUE_HAUT tuiles (le heros a la meme taille que dans les villes) x distance d'affichage / zoom.
        L'angle et la rotation de la camera (fleches) ne s'appliquent pas ici."""
        cx, cz = (e.champ['cam'] if e.champ and e.champ['cam'] else (0.0, 0.0))
        dh = CH_VUE_HAUT / 2 / self.zoom; dl = dh * aspect                      # meme champ pour tous les shaders : le zoom ne depend pas du style de rendu
        if self.mode == MODE_PP: cx, cz = round(cx) / CH_PX, round(cz) / CH_PX; ech = 1.0       # pixel perfect : camera sur un pixel de la carte, heros a sa taille exacte (24 x 32 pixels de la carte)
        else: cx, cz = cx / CH_PX, cz / CH_PX; ech = CH_ECHELLE
        self._vue_champ = (cx, cz, dl, dh)                                      # (la camera de la carte du monde ne se regle pas : ni angle ni rotation)
        M = np.zeros((4, 4)); M[0, 0] = 1 / dl; M[0, 3] = -cx / dl
        M[1, 2] = -1 / dh; M[1, 3] = cz / dh                                            # ecran y = -(z - cz) / dh
        M[2, 1] = -1 / 100.0; M[3, 3] = 1.0                                             # profondeur : la hauteur (vue de dessus)
        return M, np.array([1.0, 0.0, 0.0]), 24 / CH_PX * ech, 32 / CH_PX * ech

    def _zoom_possible(self):
        """Le zoom (molette, Ctrl + clic molette) agit sur le terrain : ville, donjon, tour ou carte du monde ; ni message, ni menu du jeu, ni carte ouverte, ni menu Echap, licence, sauvegardes, saisie du nom ou ecran-titre (ni sa scene, avant « Touchez l'ecran » : le cadrage du titre est celui du jeu), ni scene ou le jeu tient la camera (UNI-08)."""
        mo = self.moteur
        return (not self.pause.ouvert and self.licence is None and self.sauv is None and self.titre is None and getattr(self, 'carte_nom', None) != CARTE_TITRE and not self._saisie_nom_en_cours() and mo.etat.partie in (MO.PARTIE_CHAMP, MO.PARTIE_VILLE) and not mo.msg_visible and mo.menu_actif() is None and not self.carte_ouverte
                and not getattr(self, 'cam_jeu', False))                      # (UNI-08 : pendant une scene ou le jeu tient la camera, le jeu l'emporte : le joueur ne regle pas le zoom)

    def _camera_pilotable(self):
        """La camera se tourne a la main (fleches, glisser du clic molette) : terrain libre d'une ville, d'un donjon ou d'une tour (pas la carte du monde), sauf lieu ou le jeu interdit de la tourner (cam_bloquee). Memes conditions que _maj_camera."""
        return self._terrain_libre() and self.moteur.etat.partie == MO.PARTIE_VILLE and not self.cam_bloquee and self.licence is None and self.sauv is None and not self._saisie_nom_en_cours()

    def recentrer_camera(self):
        """Remet la direction de la camera (rotation et inclinaison) par defaut, par l'animation de recentrage : touche speciale + touche de camera, ou clic molette."""
        for ax in self.cam_axe.values(): ax[0] = True; ax[1] = True

    def _ctrl_actif(self, modifiers):
        """Ctrl tenu : le modificateur de la souris ou la « Touche speciale » des reglages."""
        return bool(modifiers & pyglet.window.key.MOD_CTRL) or self._tenue('modif')

    def distance_par_defaut(self):
        """Ramene la distance de la camera a sa valeur par defaut (reglages.DEFAUT['distance_camera'], 100 %) PAR UNE ANIMATION (#167, comme le recentrage de la rotation) : Ctrl + molette, Ctrl + clic molette, les deux touches de distance ensemble.
        Le mouvement est fait par _maj_distance_clavier (a chaque image) ; une molette ou une touche de distance seule l'interrompt."""
        self.dist_retour = True

    def _transition_scene_possible(self):
        """Le retour de debut de scene (UNI-08) peut-il se poursuivre ? Sur le terrain d'une ville ou de la carte du monde, meme sous un message ou un menu du jeu (la scene en affiche), mais pas sous le menu Echap, la licence, les sauvegardes
        ou l'ecran-titre (le joueur y regle sa distance lui-meme) ni hors terrain (combat...)."""
        return (not self.pause.ouvert and self.licence is None and self.sauv is None and self.titre is None and self.moteur.etat.partie in (MO.PARTIE_CHAMP, MO.PARTIE_VILLE))

    def _scene_en_cours(self, e):
        """Le jeu tient-il la camera dans une scene ? TownCamera verrouillee et menee ailleurs que sur le joueur (cam_jeu : travelling, plan fixe, cible = un personnage) ou camera libre d'une scene (paquet 11, bit 7), dans une ville, un donjon
        ou une tour ; jamais l'ecran-titre (le jeu y fixe seul la camera, sans scene)."""
        return bool(e.partie == MO.PARTIE_VILLE and getattr(self, 'carte_nom', None) != CARTE_TITRE and (self.cam_jeu or e.cam_libre))

    def _suivre_scene(self, e):
        """A chaque pas du moteur : repere le DEBUT d'une scene (le jeu prend la camera) et ramene alors le zoom du joueur a 100 % par l'animation de la remise a zero (UNI-08, choix du joueur : « le jeu l'emporte dans ses scenes, avec une
        transition en debut de scene qui remet le zoom par defaut »). Le zoom reste a 100 % ensuite, comme apres la remise a zero au clavier ou a la souris."""
        s = self._scene_en_cours(e)
        if s and not self.scene_prec and abs(self.zoom - 1.0) > 1e-6: self.dist_retour = True; self.dist_scene = True
        self.scene_prec = s

    def reinitialiser_camera(self):
        """Remet TOUS les etats de la camera a leur valeur d'origine (#168) : la position (rotation et inclinaison, par l'animation de recentrage) ET la distance (retour anime a 100 %). Touche speciale (Ctrl) + une touche de camera :
        les quatre fleches, Page haut, Page bas. Chaque etat ne se remet que la ou il se regle : la position sur le terrain libre d'une ville, d'un donjon ou d'une tour (pas la carte du monde, ni un lieu qui interdit de tourner la camera),
        la distance partout ou le zoom agit (_zoom_possible, verifie a chaque image par _maj_distance_clavier)."""
        if self._camera_pilotable(): self.recentrer_camera()
        self.distance_par_defaut()

    def on_mouse_scroll(self, x, y, sx, sy):
        """Hors menu et hors combat : molette = zoom (x1,1 par cran, distance de 200 a 50 %), la meme que celle du menu Echap ; Ctrl + molette (vers le haut OU vers le bas) = retour anime a la distance par defaut (100 %).
        pyglet ne donne pas les modificateurs de la molette : Ctrl = la « Touche speciale » des reglages (Ctrl par defaut, voir _ctrl_actif)."""
        if not self._pret: return
        if self.pause.ouvert: self.pause.molette(sy); return
        if self.licence is not None: self.licence.defiler(-sy * 60.0); return
        if not (sy and self._zoom_possible()): return
        if self._ctrl_actif(0): self.distance_par_defaut()
        else: self.dist_retour = False; self.dist_scene = False; self.regler_zoom(self.zoom * 1.1 ** sy)                      # (un cran de molette interrompt le retour anime a 100 %)

    def _molette_appui(self, x, y, modifiers):
        """Bouton du milieu enfonce : un clic (remise de la position de la camera ; avec Ctrl, de la position et de la distance) ou le debut d'un glissement (rotation de la camera). Hors du terrain (menus, messages, combat, titre...) il ne fait rien."""
        if self.hud.croix_on or self.appui or not (self._camera_pilotable() or self._zoom_possible()): self.molette.annuler(); return
        self.molette.appui(x, y, self._ctrl_actif(modifiers))

    def _molette_glisse(self, x, y):
        """Bouton du milieu maintenu et pointeur deplace : la camera tourne (horizontal : autour du heros ; vertical : inclinaison), memes sens par defaut, bornes et reglage enregistre que les fleches (entrees.pivoter) ;
        les reglages « Inverser gauche / droite » et « Inverser haut / bas » inversent le sens du glissement sur leur axe (jamais celui des fleches du clavier)."""
        dx, dy = self.molette.deplacer(x, y)
        if not (dx or dy) or not self._camera_pilotable(): return
        for ax in self.cam_axe.values(): ax[0] = False                       # un glissement annule le recentrage anime en cours
        self.lacet, a = EN.pivoter(self.lacet, self.angle_cam, dx, dy, self.height, CAM_ANGLE_MIN, CAM_ANGLE_MAX, self.cam_limite, bool(self.reg['camera_inverser_gd']), bool(self.reg['camera_inverser_hb']))
        if a != self.angle_cam: self.angle_cam = a; self.reg['angle_camera'] = round(a, 2)

    def _molette_relache(self, modifiers):
        """Bouton du milieu relache sans avoir glisse : clic = position de la camera (rotation et inclinaison) remise par defaut, par l'animation de recentrage ; Ctrl + clic = la position ET la distance remises par defaut.
        Chacune ne se remet que la ou elle se regle (position : terrain libre d'une ville ; distance : terrain, carte du monde comprise)."""
        agir = self.molette.relacher(self._ctrl_actif(modifiers))
        if agir in ('direction', 'tout') and self._camera_pilotable(): self.recentrer_camera()
        if agir == 'tout' and self._zoom_possible(): self.distance_par_defaut()

    def on_mouse_drag(self, x, y, dx, dy, boutons, modifiers):
        """Menu Echap : un curseur maintenu suit la souris ; sur le terrain, la croix a l'ecran tenue par la souris ; bouton du milieu : rotation de la camera."""
        if not self._pret: return
        self.souris = (x, y)                                          # (pendant un appui, pyglet n'envoie plus on_mouse_motion : la position sert a savoir si le doigt est toujours sur le bouton)
        M = pyglet.window.mouse
        if boutons & M.MIDDLE and not boutons & M.LEFT: self._molette_glisse(x, y); return
        if self.pause.ouvert: self.pause.glisser(x, y)
        elif self.licence is not None: self.licence.glisse and self.licence.glisser(y)
        elif self.hud.croix_on: self.hud.croix_glisser(x, y)

    @staticmethod
    def _zoom_valide(z):
        """Zoom (1 = vue habituelle ; distance de la camera = 100 / zoom) ramene entre 0,5 et 2."""
        try: z = float(z)
        except (TypeError, ValueError): return 1.0
        return min(ZOOM_MAX, max(ZOOM_MIN, z))

    def regler_zoom(self, z):
        """Molette ou --carte-zoom : zoom des villes, donjons, tours et de la carte du monde (enregistre comme distance de la camera, en pourcentage)."""
        self.zoom = self._zoom_valide(z); self.reg['distance_camera'] = round(100.0 / self.zoom)

    def regler_distance(self, pourcent):
        """Menu Echap : distance de la camera en pourcentage (50 = deux fois plus pres, 200 = deux fois plus loin)."""
        self.regler_zoom(100.0 / max(1.0, float(pourcent)))

    _t_dist = None

    dist_retour = False                                           # retour anime de la distance a 100 % en cours (#167)

    dist_scene = False                                            # le retour anime a 100 % en cours est celui d'un debut de scene (UNI-08) : il va a son terme meme pendant un message ou une scene, et les touches de distance n'y changent rien

    scene_prec = False                                            # le jeu tenait la camera (scene) au dernier pas : sert a reperer le DEBUT d'une scene

    cam_scene_w = 0.0                                             # 0 = cadrage commun de la visionneuse (heros a taille fixe), 1 = champ du jeu tel quel (scene), progressif entre les deux

    dist_bloque = False                                           # les deux touches de distance ont ete enfoncees ensemble et il en reste une enfoncee : rien ne se passe (le relachement n'est jamais exactement simultane)

    def _maj_distance_clavier(self):
        """Touches « Caméra (Rapprocher) » / « Caméra (Éloigner) » (a chaque image affichee) : tant qu'une touche est tenue, la distance de la camera diminue / augmente EN CONTINU (sans a-coup, selon le temps ecoule), a la
        vitesse de rotation de la camera (CAM_DIST_VIT x reglage « Vitesse de caméra » x accelerateur tenu), entre 50 et 200 %. Memes conditions que la molette (_zoom_possible : terrain, jamais un menu, un message ou un
        combat). Les DEUX touches ensemble (#167), ou Ctrl + l'une d'elles (#168 : la position revient aussi, voir reinitialiser_camera), ramenent la distance a 100 % par une animation (comme les deux fleches opposees pour la rotation) : vitesse minimale CAM_RECENTRE_DIST, 5 x l'ecart par seconde, fois le
        reglage « Vitesse de caméra » ; tant qu'il en reste une enfoncee apres cette pression double, rien ne se passe ; une nouvelle pression seule, ou un cran de molette, interrompt l'animation (distance_par_defaut la lance aussi : Ctrl + molette,
        Ctrl + clic molette). Meme valeur que la molette (regler_distance)."""
        t = time.perf_counter(); dt = 1.0 / 60.0 if self.fixe_test else (0.0 if self._t_dist is None else min(0.1, t - self._t_dist)); self._t_dist = t
        pres, loin = self._tenue('cam_pres'), self._tenue('cam_loin')
        if not (pres or loin): self.dist_bloque = False
        if getattr(self, 'dist_scene', False) and self.dist_retour and self._transition_scene_possible(): pres = loin = False                      # retour de debut de scene (UNI-08) : il va a son terme, meme sous un message ; les touches n'y changent rien (le jeu l'emporte)
        elif not self._zoom_possible(): self.dist_retour = False; self.dist_scene = False; return
        if (pres or loin) and self._tenue('modif'): self.reinitialiser_camera(); self.dist_bloque = True; sens = 0                          # Ctrl + l'une des deux touches (#168) : TOUS les etats de la camera reviennent a l'origine
        elif pres and loin: self.distance_par_defaut(); self.dist_bloque = True; sens = 0                                                    # les deux touches ensemble (#167) : la distance seule
        elif self.dist_bloque: sens = 0
        else:
            sens = (1 if loin else 0) - (1 if pres else 0)
            if sens: self.dist_retour = False; self.dist_scene = False
        vit_cam = float(self.reg['vitesse_camera']); lo, hi = RG.BORNES['distance_camera']; actuelle = 100.0 / self.zoom
        if sens:
            vit = vit_cam * (float(self.reg['vitesse_accel']) if self._tenue('accel') else 1.0)
            nouvelle = min(hi, max(lo, actuelle + sens * CAM_DIST_VIT * vit * dt))
            if nouvelle != actuelle: self.regler_distance(nouvelle)
        elif self.dist_retour:
            cible = float(RG.DEFAUT['distance_camera']); err = cible - actuelle; pas = max(CAM_RECENTRE_DIST, abs(err) * 5.0) * vit_cam * dt
            if abs(err) <= pas: self.regler_distance(cible); self.dist_retour = False; self.dist_scene = False
            else: self.regler_distance(actuelle + math.copysign(pas, err))

    # ---- combat : decor + monstres (maillages dynamiques du moteur)
    def _rot_camera(self, e):
        """Rotation Unity de la camera de combat (NativeManager.cmd_camera + SceneCamera.Update, mode sans cible) : euler (-x, -(y + 180), z)."""
        ax, ay, az = e.cam_rot
        return rot_unity(-ax, -(ay + 180.0), az)

    def _camera_ville(self, e, aspect):
        """Camera d'une ville comme Unity (SceneCamera.Update, mode avec cible) : LookAt(position, cible), tangage - lookDownAdjust, puis avance de distanceAdjust le long de l'axe.
        Projection : champ HORIZONTAL fov x 4/3 fixe, hauteur deduite de l'ecran portrait d'origine (0,5625). En 16/9 on garde la meme hauteur de champ que sur mobile
        et on montre plus de decor sur les cotes : la bande centrale de la fenetre est exactement l'image du telephone."""
        pos, cib = np.array(e.cam_pos, float), np.array(e.cam_cible, float)
        libre = camera_libre(e); mini = getattr(e, 'partie', None) in MO.PARTIES_MINIJEU       # mini = casino / bestiaire : le cadrage est celui du jeu (ni zoom, ni centrage, ni bornes 16/9, ni rotation du joueur)
        titre = self.carte_nom == CARTE_TITRE          # ecran-titre : le jeu fixe seul la camera (x = 0, cible a l'origine) et aucun heros ne marche ; ni centrage sur un heros, ni bornes 16/9 de la carte : sinon, avec « Centrer la camera » = Non, la camera glissait de +4,5 u vers le milieu des bornes (le logo et le decor partaient a gauche, de 15 % de la largeur a 16/9)
        fov_h = math.radians((e.cam_fov if e.cam_fov is not None else FOV_VILLE_DEF) * 4.0 / 3.0)
        th_v = math.tan(fov_h / 2) / ASPECT_PORTRAIT                      # tangente du demi-champ vertical de l'original
        t = time.perf_counter(); dt = 1.0 / 60.0 if self.fixe_test else (0.0 if self.t_centre is None else min(0.1, t - self.t_centre)); self.t_centre = t
        # Scene ou le jeu tient la camera (cam_jeu, UNI-08, choix du joueur : « le jeu l'emporte dans ses scenes ») : le champ du jeu s'applique tel quel (un travelling avant, un gros plan par la distance ou le fov changent la taille du heros
        # a l'ecran, comme dans l'original) au lieu du cadrage commun ci-dessous ; le passage de l'un a l'autre est progressif (CAM_SCENE_TAU), sans a-coup, et immediat apres une coupure.
        w_jeu = 1.0 if self.cam_jeu else 0.0; w = w_jeu if self.cam_saut else getattr(self, 'cam_scene_w', 0.0) + (w_jeu - getattr(self, 'cam_scene_w', 0.0)) * (1.0 - math.exp(-CAM_SCENE_TAU * dt)); self.cam_scene_w = w
        if not libre:       # zoom commun : le heros (le point vise) prend HEROS_FRAC de la hauteur de la fenetre, quelle que soit la distance ou le fov de la camera de la ville, de la grotte ou de la tour
            prof = float(np.linalg.norm(cib - pos)) - DIST_ADJ_VILLE
            if prof > 1.0 and 0 in e.sprites and self.carte_nom != 'ev01': th_v = (SPRITE_H * SPRITE_ECHELLE / HEROS_FRAC / (2.0 * prof)) ** (1.0 - w) * th_v ** w       # (titre : aucun heros (le sprite 0 est charge mais cache), champ horizontal fixe de l'original : sans cette exception la formule du heros agrandissait toute la scene de 1,185 : logo plus large que l'ecran portrait)
        th_v /= PJ.facteur_effectif(self.zoom, libre or mini or titre)               # zoom (40 a 400 %) : le champ vertical est divise par le zoom (villes, grottes, tours...) ; camera libre d'une scene (position, angles et champ fixes par le script) : le cadrage est celui du jeu, sans zoom
        # La camera est TOUJOURS centree sur le heros (plus d'option : c'est aussi le fonctionnement du jeu, TownCamera::execute fait setTarget(joueur) a chaque pas tant que son verrou est a 0), sauf quand le jeu la prend :
        # TownCamera verrouillee et menee ailleurs (scene, evenement, chute, sort de retour ; cam_jeu), camera libre d'une scene (paquet 11, bit 7) ou mini-jeu. La camera du jeu s'applique alors telle quelle (aucune borne).
        centre = not libre and not mini and not self.cam_jeu and not titre               # centrage actif (jamais sur l'ecran-titre : le jeu y fixe seul la camera)
        dec = (0.0, 0.0)
        if centre:                                                        # camera toujours centree sur le heros (sprite 0) : le jeu borne sa cible aux bords de la carte ; on corrige l'ecart (garde-fou : position du heros perimee)
            sp = e.sprites.get(0); hp = sp.get('pos') if sp else None
            if hp is not None and math.hypot(hp[0] - cib[0], hp[2] - cib[2]) <= CAM_CENTRE_MAX: dec = (hp[0] - cib[0], hp[2] - cib[2])
        # Correction du centrage = cible (heros - cible du jeu, suivie A L'IMAGE PRES : la camera est rigide sur le heros, meme quand le jeu borne la sienne aux bords de la carte et que le heros court)
        # + reste qui se resorbe en douceur. Le reste ne naît que d'un changement de regime (scene <-> main du joueur) ou d'une coupure : avant, TOUT l'ecart etait lisse (exp(-14 t)), donc la camera trainait derriere
        # un heros en course (v / 14 : ~0,6 u a x1,5, plus aux vitesses x2 a x4) et « continuait son chemin » apres l'arret (declenchement d'un evenement) avant de se recentrer
        saut = self.cam_saut
        if saut: self.cam_res = [0.0, 0.0]; self.cam_saut = False             # coupure du jeu (changement de carte, plan de scene) : la correction suit aussitot, sans glissement apres la coupure
        elif centre != self.cam_centre: self.cam_res = [c - d for c, d in zip(self.cam_dec, dec)]                    # changement de regime : on part de l'ecart actuel (aucun saut a l'image), il s'estompe
        self.cam_centre = centre
        k = math.exp(-14.0 * dt)                                          # (temps reel : independant du nombre de pas du moteur par image affichee)
        self.cam_res = [r * k for r in self.cam_res]
        self.cam_dec = [d + r for d, r in zip(dec, self.cam_res)]
        if titre: self.cam_res = [0.0, 0.0]; self.cam_dec = [0.0, 0.0]          # ecran-titre : aucun reste de centrage d'une partie precedente (retour au titre) ne glisse la camera
        # Hauteur (#47, escaliers) : tant que le joueur a la camera, sa hauteur ne suit plus le heros a chaque pas (le jeu la recalcule sur le heros : TownCamera::execute, setTarget(joueur), aucun lissage en Y ; la montee
        # ressentie venait de la). Hauteur de reference = celle de la cible du jeu, rejointe lentement (CAM_Y_TAU), a 3 unites pres au plus (CAM_Y_MAX) ; coupure du jeu (changement de carte, plan, teleportation) ou
        # camera prise par le jeu : la reference est celle du jeu aussitot (aucun glissement). Au repos (etage plat) l'ecart est nul : le heros est au centre, comme avant.
        # #110 : bande morte (CAM_Y_RELIEF) : un petit relief (butte, rampe douce, bosse) est suivi exactement comme le mobile (le sol defile quand le heros monte, le heros reste au centre ; avant, la camera « restait sur le
        # meme plan » et le heros montait a l'ecran) ; seul ce qui depasse (escaliers, etages) est lisse. Voir `hauteur_camera`.
        dy = 0.0
        if centre and CAM_Y_TAU > 0:
            if saut: self.cam_zone_y = self.cam_ref_y = None
            self.cam_zone_y, self.cam_ref_y, dy = hauteur_camera(getattr(self, 'cam_zone_y', None), self.cam_ref_y, float(cib[1]), dt)
        else: self.cam_ref_y = self.cam_zone_y = None
        if abs(dy) > 1e-6: pos[1] += dy; cib[1] += dy
        # Aucune borne de la visionneuse (cadrage 16/9 retire avec l'option) : Unity ne borne rien (SceneCamera.Update : ni Clamp ni Min / Max ; TownCamera::execute non plus), la camera va jusqu'au bord de la carte et le cadre
        # du telephone suit l'evenement ou le PNJ jusqu'au bout, la visionneuse aussi.
        if abs(self.cam_dec[0]) > 1e-4 or abs(self.cam_dec[1]) > 1e-4:
            pos[0] += self.cam_dec[0]; cib[0] += self.cam_dec[0]; pos[2] += self.cam_dec[1]; cib[2] += self.cam_dec[1]
        lacet_a, angle_a = (0.0, 0.0) if self.cam_bloquee or mini or titre else (self.lacet, self.angle_cam)             # lieu ou le jeu interdit de tourner la camera : vue d'origine
        if lacet_a and not (libre and e.cam_rot is not None):           # fleches gauche / droite : la camera tourne autour de la cible (le cap avance vers +X quand le lacet est positif)
            c_, s_ = math.cos(math.radians(lacet_a)), math.sin(math.radians(lacet_a)); d_ = pos - cib
            pos = cib + np.array([d_[0] * c_ + d_[2] * s_, d_[1], -d_[0] * s_ + d_[2] * c_])
        pos_lacet = np.array(pos, float)                                 # camera apres la rotation (lacet) mais avant l'inclinaison de la visionneuse : sert au repere des sprites (voir _cadre_sprites)
        if angle_a and not (libre and e.cam_rot is not None):       # fleches haut / bas : la camera tourne autour de la cible, en hauteur (0 = comme le jeu)
            dist = float(np.linalg.norm(cib - pos)); f0 = (cib - pos) / (dist or 1.0)
            la = math.atan2(f0[0], f0[2]); tg = min(math.radians(85.0), max(math.radians(5.0), math.asin(-f0[1]) + math.radians(angle_a)))
            pos = cib - np.array([math.sin(la) * math.cos(tg), -math.sin(tg), math.cos(la) * math.cos(tg)]) * dist
        if libre and e.cam_rot is not None:                         # camera libre (paquet 11, bit 7) : position + angles, comme en combat
            R = self._rot_camera(e); fw = R @ np.array([0.0, 0.0, 1.0]); haut = R @ np.array([0.0, 1.0, 0.0])
        else:
            fw = cib - pos; fw /= np.linalg.norm(fw)
            lacet = math.atan2(fw[0], fw[2]); tang = math.asin(-fw[1]) - math.radians(e.cam_bas if e.cam_bas is not None else BAS_DEF)
            fw = np.array([math.sin(lacet) * math.cos(tang), -math.sin(tang), math.cos(lacet) * math.cos(tang)]); haut = np.array([0.0, 1.0, 0.0])
            pos = pos + fw * DIST_ADJ_VILLE
        M, droite = matrice(pos, pos + fw * 10, math.degrees(2 * math.atan(th_v)), aspect, n=e.cam_near or VILLE_NEAR, f=(e.cam_far or VILLE_FAR) + (0.05 * self.n_boucle if os.environ.get('DQ_ZDEBUG') else 0.0), haut=haut)      # (test) DQ_ZDEBUG : le plan lointain change a chaque image : seules les surfaces en z-fighting changent d'une image a l'autre
        yoff = e.cam_yoff or 0.0
        if yoff:
            Ty = np.eye(4); Ty[1, 3] = yoff; M = Ty @ M              # SceneCamera.s_yOffset
        self._cadre_vue = (np.array(pos, float), droite, np.cross(fw, droite), fw)
        # Repere des sprites (#184) : le panneau d'un personnage prend la rotation de la camera DU JEU (Chara.normalBillboard), donc son inclinaison est celle du jeu (la visionneuse ne la change pas : un personnage reste debout
        # dans le monde quand on monte ou descend la camera avec Haut / Bas, il ne « s'aligne » pas sur la nouvelle vue) ; la rotation autour du heros (lacet) est suivie (le panneau reste de face, comme dans le jeu a cette orientation)
        self._cadre_sprites = (droite, np.cross(fw, droite), fw)
        if angle_a and not (libre and e.cam_rot is not None):
            fj = cib - pos_lacet; fj /= np.linalg.norm(fj)
            lj = math.atan2(fj[0], fj[2]); tj = math.asin(-fj[1]) - math.radians(e.cam_bas if e.cam_bas is not None else BAS_DEF)
            fj = np.array([math.sin(lj) * math.cos(tj), -math.sin(tj), math.cos(lj) * math.cos(tj)]); dj = np.cross([0.0, 1.0, 0.0], fj); dj /= np.linalg.norm(dj)
            self._cadre_sprites = (dj, np.cross(fj, dj), fj)
        return M, (droite, np.cross(fw, droite), fw)

    def _cadre_jeu(self, e):
        """(position, droite, haut, avant) de la camera de la ville telle que le jeu d'origine la place (meme calcul que _camera_ville, SANS le zoom, le centrage, la rotation et l'inclinaison de la visionneuse)."""
        pos, cib = np.array(e.cam_pos, float), np.array(e.cam_cible, float)
        if camera_libre(e) and e.cam_rot is not None:
            R = self._rot_camera(e); fw = R @ np.array([0.0, 0.0, 1.0]); haut = R @ np.array([0.0, 1.0, 0.0])
        else:
            fw = cib - pos; fw /= np.linalg.norm(fw)
            lacet = math.atan2(fw[0], fw[2]); tang = math.asin(-fw[1]) - math.radians(e.cam_bas if e.cam_bas is not None else BAS_DEF)
            fw = np.array([math.sin(lacet) * math.cos(tang), -math.sin(tang), math.cos(lacet) * math.cos(tang)]); haut = np.array([0.0, 1.0, 0.0])
            pos = pos + fw * DIST_ADJ_VILLE
        droite = np.cross(haut, fw); droite /= np.linalg.norm(droite)
        return pos, droite, np.cross(fw, droite), fw

    def _camera_combat(self, e, aspect):
        R = self._rot_camera(e)
        cam = np.array(e.cam_pos, float); fw = R @ np.array([0.0, 0.0, 1.0]); haut = R @ np.array([0.0, 1.0, 0.0])
        fov_h = math.radians((e.cam_fov if e.cam_fov is not None else CB_FOV_NOM) * 4.0 / 3.0)         # SceneCamera.Update : fov x 4/3, applique a l'horizontale (matrice de projection transposee)
        fov_v = math.degrees(2 * math.atan(math.tan(fov_h / 2) / (4.0 / 3.0)))                         # vue d'origine 4/3 ; en 16/9 on garde la meme hauteur de champ et on montre plus de decor sur les cotes
        M, _ = matrice(cam, cam + fw * 10, fov_v, aspect, n=CB_NEAR, f=CB_FAR, haut=haut)
        Ty = np.eye(4); Ty[1, 3] = CB_YOFFSET; M = Ty @ M                                              # SceneCamera.s_yOffset : decalage vertical de l'image
        if self.cb_mx: M = M @ np.diag([-1.0, 1.0, 1.0, 1.0])
        T = np.diag([CB_ECHELLE_DECOR] * 3 + [1.0]); T[2, 3] = CB_DEC_Z                              # NativeManager.cmd_fld_load en mode combat : FldObject.SetDispScale(6, 6, 6), applique a la racine du decor (FldObject.Update)
        return M, M @ T

    def _maj_camera(self):
        """Fleches sur le terrain (a chaque image affichee) : gauche / droite tournent la camera autour du heros (villes, donjons, tours seulement), haut / bas relevent ou abaissent son angle ;
        deux fleches opposees ensemble la remettent par defaut par une animation ; Ctrl + une fleche remet aussi la distance (reinitialiser_camera), par le chemin le plus court (le lacet est gardé entre -180 et 180 degres : 359 degres revient par +1). Vitesse : reglages « Vitesse de caméra » et « Multiplicateur de l'accélérateur » (touche tenue)."""
        t = time.perf_counter(); dt = 1.0 / 60.0 if self.fixe_test else (0.0 if self.t_cam is None else min(0.1, t - self.t_cam)); self.t_cam = t
        if not self._terrain_libre(): return
        g, d, h, b = (self._tenue(a) for a in ('cam_gauche', 'cam_droite', 'cam_haut', 'cam_bas'))
        vit = float(self.reg['vitesse_camera']); ville = self.moteur.etat.partie == MO.PARTIE_VILLE
        if not ville or self.cam_bloquee:                                                                          # carte du monde, ou lieu ou le jeu interdit de tourner la camera : les touches de la camera ne tournent rien
            if self._tenue('modif') and (g or d or h or b): self.reinitialiser_camera()                              # (Ctrl + fleche : la distance revient quand meme, comme avec la molette ; la position, non : _camera_pilotable est faux)
            for ax in self.cam_axe.values(): ax[0] = False; ax[1] = bool(g or d or h or b)
            return
        acc = self._tenue('accel')                                                                                # camera acceleree : touche d'accelerateur tenue (comme la course)
        if self._tenue('modif') and (g or d or h or b):                                                            # touche modificatrice + fleche : TOUS les etats de la camera (rotation, inclinaison ET distance) reviennent a l'origine par une animation (#168 ; les touches tenues ensuite ne font plus rien)
            self.reinitialiser_camera(); sl = sa = 0
        else: sl = self._etat_axe('lacet', g, d); sa = self._etat_axe('angle', b, h)
        vit_m = vit * (float(self.reg['vitesse_accel']) if acc else 1.0)                                            # acceleration : rotation et inclinaison a la main plus rapides (le recentrage garde sa vitesse)
        if sl:
            self.lacet = (self.lacet + sl * CAM_LACET_VIT * vit_m * dt + 180.0) % 360.0 - 180.0
            if self.cam_limite is not None: self.lacet = max(-self.cam_limite, min(self.cam_limite, self.lacet))
        elif self.cam_axe['lacet'][0]:
            err = -self.lacet; pas = max(CAM_RECENTRE_LACET, abs(err) * 5.0) * vit * dt
            if abs(err) <= pas: self.lacet = 0.0; self.cam_axe['lacet'][0] = False
            else: self.lacet += math.copysign(pas, err)
        a = self.angle_cam
        if sa: a = min(CAM_ANGLE_MAX, max(CAM_ANGLE_MIN, a + sa * CAM_TANGAGE_VIT * vit_m * dt))
        elif self.cam_axe['angle'][0]:
            pas = max(CAM_RECENTRE_ANGLE, abs(a) * 5.0) * vit * dt
            if abs(a) <= pas: a = 0.0; self.cam_axe['angle'][0] = False
            else: a -= math.copysign(pas, a)
        if a != self.angle_cam: self.angle_cam = a; self.reg['angle_camera'] = round(a, 2)

    def _camera_menee(self, mo):
        """La TownCamera verrouillee va-t-elle AILLEURS que sur le joueur ? Mode de cible 1 a 4 (deplacements : travelling, retour) ou 5 (un personnage : la grenouille du prologue...), deplacement en cours, ou cible du jeu a plus de CAM_MENE_DIST du heros
        (plan fixe, heros hors champ). Mode 6 (le joueur) et verrou sans cible a cote du heros : le jeu tient le joueur comme hors scene : AUCUN changement de regime (centrage, bornes), donc pas de glissement au declenchement."""
        try: _, mode, _, deplace = mo.camera_jeu()
        except Exception: return True
        if 1 <= mode <= 5 or deplace: return True
        e = mo.etat; sp = e.sprites.get(0); hp = sp.get('pos') if sp else None
        if mode == 6: return False
        if hp is None or e.cam_cible is None: return True
        return math.hypot(hp[0] - e.cam_cible[0], hp[2] - e.cam_cible[2]) > CAM_MENE_DIST

    def _dbg_proj(self, M, e, cam3d, a_dessiner, icones):
        """(debogage, DQ_PROJ=n) pixels (x, y depuis le haut) des pieds / haut des panneaux des sprites et des bulles, toutes les n images."""
        def px(P):
            v = M @ np.array([P[0], P[1], P[2], 1.0]); return None if v[3] <= 1e-6 else (round(float((v[0] / v[3] * 0.5 + 0.5) * self.width), 1), round(float((1 - (v[1] / v[3] * 0.5 + 0.5)) * self.height), 1))
        out = {}
        for slot, f, vl in a_dessiner:
            q = np.array(vl.position[:], float).reshape(-1, 3); out['s%d' % slot] = (px(q[0]), px(q[1]), px(q[2]), px(q[5]))       # coins : bas-gauche, bas-droit, haut-droit, haut-gauche
        for slot, ic in sorted(e.icones.items()):
            if ic['pos'] is not None: out['i%d' % slot] = (px(ic['pos']),)
        for tex, vl in icones:
            q = np.array(vl.position[:], float).reshape(-1, 3); out['bulle'] = (px(q[0]), px(q[1]), px(q[2]), px(q[5]))
        print('PROJ n=%d' % self.n_boucle, out, flush=True)

    def _correction_bords(self):
        """Intensite (0 a 1) de la correction des bords des sprites (villes, donjons, tours ; voir _panneau_ville) : 0 par defaut depuis #184 (« reviens a la position brute des PNJ, exactement comme dans le jeu » : panneau
        d'origine, sans reconstruction a l'ecran) ; l'ancienne correction complete (bords verticaux, proportion constante, #134) s'obtient avec l'option --correction-bords ou la variable d'environnement DQ_CORRECTION_BORDS,
        de 0 (aucune, defaut) a 100 (complete). Ce n'est pas un reglage du joueur (l'ancienne option « Correction des bords des sprites » est retiree)."""
        v = getattr(self.args, 'correction_bords', None)
        if v is None and os.environ.get('DQ_CORRECTION_BORDS'):
            try: v = float(os.environ['DQ_CORRECTION_BORDS'])
            except ValueError: v = None
        return CORRECTION_BORDS_DEF if v is None else min(1.0, max(0.0, float(v) / 100.0))

    def _repere_sprites(self, cam3d, corr):
        """(droite, haut, avant) qui oriente le panneau d'un personnage de ville. Panneau d'origine (correction des bords nulle, defaut depuis #184) : le repere de la camera DU JEU (Chara.normalBillboard prend la rotation de la camera
        du jeu) : meme inclinaison que sur le mobile, rotation autour du heros (lacet) suivie ; l'inclinaison que la visionneuse ajoute avec Haut / Bas ne change plus le panneau : un personnage ne « s'aligne » pas sur la vue quand on monte
        ou descend la camera. Correction des bords active (essai #134) : le repere de la vue, dont elle a besoin (reconstruction a l'ecran). DQ_SPRITES_SUR_VUE : l'ancien alignement du panneau d'origine sur la vue."""
        if cam3d is None or corr > 0.0 or os.environ.get('DQ_SPRITES_SUR_VUE'): return cam3d
        return getattr(self, '_cadre_sprites', None) or cam3d

    INCLINAISON_SPRITES_DEF = 0.0                                       # part de l'inclinaison des verticales du monde que prend le sprite : 0 = bords exactement verticaux (defaut depuis #180 : l'essai #134 a 0,5 deformait les sprites pres des bords), 1 = parallele aux murs

    def _inclinaison_sprites(self):
        """(Essai #134, RETIRE par defaut en #180 : « remets l'affichage des PNJ comme sur la version mobile, ... ils s'etirent quand ils s'approchent du bord ») Part (0 a 1) de l'inclinaison des VERTICALES DU MONDE (aretes de murs, portes...) que prend le panneau d'un personnage a l'ecran, 0 par defaut (essai : 0,5). Depuis la correction des bords (_panneau_ville) le sprite est
        exactement vertical a l'ecran partout, mais les murs voisins penchent (11 a 19 degres a 9 unites du centre en 16/9, camera a 47 degres, contre 4 a 6,5 sur le portrait du mobile) et cet angle change quand le heros monte ou
        descend : le sprite semble alors se pencher par rapport au decor (illusion d'optique signalee dans #134). Le pencher a moitie vers la verticale du monde reduit cet ecart de moitie sans revenir au panneau d'origine
        (qui s'ecartait du centre de l'image par son seul haut et se deformait). Comparaison avec l'essai : variable d'environnement DQ_SPRITE_INCLINAISON, de 0 (bords verticaux, defaut) a 100 (parallele au decor)."""
        v = os.environ.get('DQ_SPRITE_INCLINAISON')
        if v is None or not v.strip(): return self.INCLINAISON_SPRITES_DEF
        try: return min(1.0, max(0.0, float(v) / 100.0))
        except ValueError: return self.INCLINAISON_SPRITES_DEF

    @staticmethod
    def _decaler_profondeur(X, F, delta, t, C):
        """Point X (d'un panneau parallele a l'ecran) rapproche de la camera de `delta` unites de profondeur. t = 0 : le long de l'axe de la camera (F), comme les sommets du panneau de la bulle Riseup dans Unity (Riseup.s_vtxDepth) ;
        t = 1 : le long du rayon de vue (camera -> X) : meme point a l'ecran, meme profondeur (sinon le bord decale s'ecarte du centre de l'image de delta x ecart / profondeur : la bulle glisse de cote quand la camera est tournee). Entre les deux : melange lineaire."""
        if t <= 0.0 or C is None: return X - F * delta
        d = X - C; z = float(d @ F)
        if z <= delta * 1.5: return X - F * delta                          # (tout contre la camera : pas de division par une profondeur nulle)
        return X - ((1.0 - t) * delta) * F - (t * delta / z) * d

    def _panneau_ville(self, p, r_, u_, f_, w, h, zb, zt, t, C, inc=0.0):
        """Les 4 sommets (bas gauche, bas droit, haut droit, haut gauche) du panneau d'un personnage de ville dont les pieds sont en p : un rectangle w x h parallele a l'ecran, dont le bas est recule de `zb` et le haut de `zt`
        vers la camera (profondeur du panneau d'origine, qui penche de 36 degres). t = 0 : le panneau d'origine (decalages le long de l'axe de la camera). Defaut de l'original, rendu visible par le champ horizontal du 16/9
        (le portrait du mobile en voyait bien moins) : le haut, plus proche, s'ecarte du centre de l'image (de zt x ecart / profondeur) et le sprite « se penche » vers l'exterieur pres des bords gauche / droit (jusqu'a 15 a
        20 degres) ; de plus la hauteur a l'ecran se comprime vers le bas de l'image, d'ou un sprite trop large (jusqu'a 0,9 au lieu de 0,75). t = 1 : le panneau est reconstruit A L'ECRAN : meme position, meme hauteur
        et memes profondeurs qu'avant (taille, recouvrements et z-buffer inchanges), mais bords verticaux et largeur = 0,72 x la hauteur a l'ecran (la proportion du panneau au centre de l'image : la largeur y est la
        moyenne de celles du bas et du haut), donc le sprite garde ses proportions partout. Au centre de l'image, rien ne change. Entre les deux : melange lineaire des sommets. Camera inconnue ou panneau contre la camera : l'original.
        `inc` (0 a 1, essai #134, voir _inclinaison_sprites) : le panneau reconstruit est ensuite CISAILLE vers la verticale du monde, les pieds fixes : le haut glisse de inc x (inclinaison a l'ecran d'une verticale du monde au pied du
        personnage) x hauteur, a la meme profondeur. Taille, profondeur et bas inchanges ; 0 : bords verticaux ; 1 : bords paralleles aux murs. Au centre de l'image la verticale du monde est droite : rien ne change."""
        a, b = p - r_ * (w / 2), p + r_ * (w / 2)
        orig = (a - f_ * zb, b - f_ * zb, b + u_ * h - f_ * zt, a + u_ * h - f_ * zt)
        if t <= 0.0 or C is None: return orig
        d = p - C; z = float(d @ f_)
        if z <= zt * 1.5: return orig
        xs, yb, yt = float(d @ r_) / (z - zb), float(d @ u_) / (z - zb), (float(d @ u_) + h) / (z - zt)      # a l'ecran (focale 1) : abscisse du centre du bas, ordonnees du bas et du haut du panneau d'origine
        hw = 0.5 * (w / h) * (z - zt) / (z - 0.5 * (zb + zt)) * (yt - yb)                                    # demi-largeur a l'ecran : proportion (largeur moyenne / hauteur) du panneau d'origine au centre de l'image
        gl_ = 0.0                                                                                                   # glissement du haut (unites de l'ecran, focale 1) : inc x tan(inclinaison d'une verticale du monde au pied) x hauteur a l'ecran
        if inc > 0.0:
            Y = np.array([0.0, 1.0, 0.0]); db = d - f_ * zb; zz = z - zb                                             # pied du panneau : sa direction a l'ecran (une droite du monde reste une droite) = derivee de la projection quand on monte de dy
            vx = float(Y @ r_) / zz - float(db @ r_) * float(Y @ f_) / zz ** 2; vy = float(Y @ u_) / zz - float(db @ u_) * float(Y @ f_) / zz ** 2
            if abs(vy) > 1e-3: gl_ = min(1.0, max(-1.0, vx / vy)) * min(1.0, max(0.0, inc)) * (yt - yb)
        new = [C + r_ * ((xs + sx * hw + gh) * (z - dz)) + u_ * (ys * (z - dz)) + f_ * (z - dz) for sx, ys, dz, gh in ((-1, yb, zb, 0.0), (1, yb, zb, 0.0), (1, yt, zt, gl_), (-1, yt, zt, gl_))]
        return tuple(o + t * (n - o) for o, n in zip(orig, new))

    def _coupure_camera(self, e):
        """Pendant ce pas du moteur, la cible de la camera du jeu a-t-elle saute (coupure de scene, changement de carte) ? self.prec = etat du pas precedent."""
        pr = self.prec
        if pr is None or pr['cle'] != (e.partie, e.carte): return True
        a, b = pr['cam_cible'], e.cam_cible
        if a is None or b is None or len(a) != len(b): return True
        return max(abs(x - y) for x, y in zip(a, b)) > CAM_SAUT_VILLE

    def _camv(self, mo):
        """(debogage, DQ_CAMV=n) etat de la camera du jeu toutes les n images."""
        e = mo.etat; sp = e.sprites.get(0); hp = sp.get('pos') if sp else None
        r = lambda v: None if v is None else tuple(round(float(x), 1) for x in v)
        print('CAMV n=%d carte=%s partie=%#x cam=%s jeu=%s flag=%#x msg=%d hero=%s cib=%s pos=%s libre=%s dec=%s' % (self.n, e.carte, e.partie, mo.camera_ville(), mo.camera_jeu(), mo.drapeaux(), mo.msg_visible, r(hp), r(e.cam_cible), r(e.cam_pos), e.cam_libre, r(self.cam_dec)), flush=True)
        if os.environ.get('DQ_CAMV_SPR'):                                  # (debogage) + tous les sprites et les bulles d'icone
            print('   sprites', {k: (r(s_.get('pos')), s_.get('id'), s_.get('vis', True)) for k, s_ in e.sprites.items()}, 'icones', {k: (i['id'], r(i['pos']), round(i['alpha'], 2)) for k, i in e.icones.items()}, flush=True)
