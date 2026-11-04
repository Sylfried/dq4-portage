"""Camera : camera des villes (celle du jeu + la rotation gauche / droite du joueur), de la carte du monde, du combat et du titre, correction des bords des sprites. Le joueur ne regle que la rotation (fleches gauche / droite, clic molette) :
plus de zoom, d'inclinaison, de centrage ni de lissage de hauteur (retires en #264), et plus d'acceleration de la camera (D-233)."""
import math, os, time
import numpy as np
import pyglet
from dq4_pc.fenetre import entrees as EN
from dq4_pc.noyau import moteur as MO
from dq4_pc.fenetre.constantes import (ASPECT_PORTRAIT, BAS_DEF, CAM_LACET_VIT, CAM_MENE_DIST, CAM_RECENTRE_LACET, CAM_SAUT_VILLE, CAM_SCENE_TAU, CARTE_TITRE, CB_DEC_Z, CB_ECHELLE_DECOR,
    CB_FAR, CB_FOV_NOM, CB_NEAR, CB_YOFFSET, CH_ECHELLE, CH_PX, CH_VUE_HAUT, CORRECTION_BORDS_DEF, DIST_ADJ_VILLE, FOV_VILLE_DEF, MODE_PP, VILLE_FAR, VILLE_NEAR)
from dq4_pc.fenetre.aides import camera_libre, matrice, rot_unity


class CameraMixin:
    """Camera : camera des villes (celle du jeu, tournee autour de sa cible par le joueur), de la carte du monde, du combat et du titre, correction des bords des sprites."""

    def _camera_champ(self, e, aspect):
        """Carte du monde, comme Field.Init / Field.SetPosition du jeu : camera orthographique vue de dessus (Rotate(90, 0, 0)), centree sur le point donne par le moteur
        (en pixels de 16 par tuile). Le haut de l'ecran est le nord (-Z), l'est est a droite. Hauteur visible = CH_VUE_HAUT tuiles (le heros a la meme taille que dans les villes) x echelle du jeu (ballon, paquet 30).
        La camera est celle du jeu : aucun reglage du joueur."""
        cx, cz = (e.champ['cam'] if e.champ and e.champ['cam'] else (0.0, 0.0))
        dh = CH_VUE_HAUT / 2 * float(getattr(e, 'champ_echelle', 1.0)); dl = dh * aspect          # meme champ pour tous les shaders ; echelle du jeu (ballon : jusqu'a 1,25, Field.SetScale : orthographicSize x echelle, MAP-02)
        if self.mode == MODE_PP: cx, cz = round(cx) / CH_PX, round(cz) / CH_PX; ech = 1.0       # pixel perfect : camera sur un pixel de la carte, heros a sa taille exacte (24 x 32 pixels de la carte)
        else: cx, cz = cx / CH_PX, cz / CH_PX; ech = CH_ECHELLE
        self._vue_champ = (cx, cz, dl, dh)                                      # (la camera de la carte du monde ne se regle pas : ni angle ni rotation)
        M = np.zeros((4, 4)); M[0, 0] = 1 / dl; M[0, 3] = -cx / dl
        M[1, 2] = -1 / dh; M[1, 3] = cz / dh                                            # ecran y = -(z - cz) / dh
        M[2, 1] = -1 / 100.0; M[3, 3] = 1.0                                             # profondeur : la hauteur (vue de dessus)
        return M, np.array([1.0, 0.0, 0.0]), 24 / CH_PX * ech, 32 / CH_PX * ech

    def _camera_pilotable(self):
        """La camera se tourne a la main (fleches gauche / droite, glisser du clic molette) : terrain libre d'une ville, d'un donjon ou d'une tour (pas la carte du monde, pas l'ecran-titre), sauf lieu ou le jeu interdit de la tourner (cam_bloquee)
        et scene ou le jeu tient la camera (cam_jeu, camera libre : le jeu l'emporte). Memes conditions que _maj_camera."""
        e = self.moteur.etat
        return (self._terrain_libre() and e.partie == MO.PARTIE_VILLE and getattr(self, 'carte_nom', None) != CARTE_TITRE and not self.cam_bloquee and not self.cam_jeu and not (e.cam_libre and e.cam_rot is not None)
                and self.licence is None and self.sauv is None and not self._saisie_nom_en_cours())

    def recentrer_camera(self):
        """Remet la rotation de la camera par defaut (celle du jeu) par l'animation de recentrage : les deux fleches ensemble, ou clic molette."""
        self.cam_axe['lacet'][0] = True; self.cam_axe['lacet'][1] = True

    def on_mouse_scroll(self, x, y, sx, sy):
        """Molette : fait defiler le menu Echap ou la licence ; sur le terrain elle ne fait plus rien (plus de zoom, #264)."""
        if not self._pret: return
        if self.pause.ouvert: self.pause.molette(sy); return
        if self.licence is not None: self.licence.defiler(-sy * 60.0)

    def _molette_appui(self, x, y):
        """Bouton du milieu enfonce : un clic (la camera se recentre) ou le debut d'un glissement (rotation de la camera). Hors du terrain (menus, messages, combat, titre...) il ne fait rien."""
        if self.hud.croix_on or self.appui or not self._camera_pilotable(): self.molette.annuler(); return
        self.molette.appui(x, y)

    def _molette_glisse(self, x, y):
        """Bouton du milieu maintenu et pointeur deplace : la camera tourne (a gauche / a droite seulement ; le deplacement vertical ne fait rien), memes sens par defaut, bornes que les fleches (entrees.pivoter) ;
        le reglage « Inverser gauche / droite » inverse le sens du glissement (jamais celui des fleches du clavier). Le lacet n'est pas enregistre."""
        dx = self.molette.deplacer(x, y)
        if not dx or not self._camera_pilotable(): return
        self.cam_axe['lacet'][0] = False                                      # un glissement annule le recentrage anime en cours
        self.lacet = EN.pivoter(self.lacet, dx, self.height, self.cam_limite, bool(self.reg['camera_inverser_gd']))

    def _molette_relache(self):
        """Bouton du milieu relache sans avoir glisse : clic = camera recentree, par l'animation de recentrage (sur le terrain libre d'une ville seulement)."""
        if self.molette.relacher() and self._camera_pilotable(): self.recentrer_camera()

    def on_mouse_drag(self, x, y, dx, dy, boutons, modifiers):
        """Menu Echap : un curseur maintenu suit la souris ; sur le terrain, la croix a l'ecran tenue a la souris ; bouton du milieu : rotation de la camera."""
        if not self._pret: return
        self.souris = (x, y)                                          # (pendant un appui, pyglet n'envoie plus on_mouse_motion : la position sert a savoir si le doigt est toujours sur le bouton)
        M = pyglet.window.mouse
        if boutons & M.MIDDLE and not boutons & M.LEFT: self._molette_glisse(x, y); return
        if self.pause.ouvert: self.pause.glisser(x, y)
        elif self.licence is not None: self.licence.glisse and self.licence.glisser(y)
        elif self.hud.croix_on: self.hud.croix_glisser(x, y)


    # ---- combat : decor + monstres (maillages dynamiques du moteur)
    def _rot_camera(self, e):
        """Rotation Unity de la camera de combat (NativeManager.cmd_camera + SceneCamera.Update, mode sans cible) : euler (-x, -(y + 180), z)."""
        ax, ay, az = e.cam_rot
        return rot_unity(-ax, -(ay + 180.0), az)

    def _camera_ville(self, e, aspect):
        """Camera d'une ville comme Unity (SceneCamera.Update, mode avec cible) : LookAt(position, cible), tangage - lookDownAdjust, puis avance de distanceAdjust le long de l'axe. Celle du jeu (#264) : position, cible,
        champ, decalage vertical et rotation envoyes par le moteur, sans zoom, inclinaison, centrage sur le heros ni lissage de hauteur de la visionneuse (TownCamera::execute suit le joueur et borne sa cible aux bords de la carte) ;
        la SEULE chose que le joueur y change est la rotation autour de la cible (fleches gauche / droite, clic molette : `_lacet_eff`, D-233), qui s'efface en douceur quand le jeu tient la camera (scene, lieu qui interdit de la tourner).
        Projection : champ HORIZONTAL fov x 4/3 fixe, hauteur deduite de l'ecran portrait d'origine (0,5625). En 16/9 on garde la meme hauteur de champ que sur mobile et on montre plus de decor sur les cotes : la bande
        centrale de la fenetre est exactement l'image du telephone."""
        pos, cib = np.array(e.cam_pos, float), np.array(e.cam_cible, float)
        libre = camera_libre(e)
        fov_h = math.radians((e.cam_fov if e.cam_fov is not None else FOV_VILLE_DEF) * 4.0 / 3.0)
        th_v = math.tan(fov_h / 2) / ASPECT_PORTRAIT                      # tangente du demi-champ vertical de l'original
        t = time.perf_counter(); dt = 1.0 / 60.0 if self.fixe_test else (0.0 if self.t_centre is None else min(0.1, t - self.t_centre)); self.t_centre = t
        # Scene ou le jeu tient la camera (cam_jeu : travelling, plan fixe, cible = un personnage ; verrou de la TownCamera ; lieu qui interdit de la tourner ; camera libre d'une scene) : la rotation du joueur s'efface en douceur
        # (CAM_SCENE_TAU) et revient de meme a la fin, sans a-coup ; immediatement apres une coupure (changement de carte, plan de scene : cam_saut).
        w_jeu = 1.0 if (self.cam_jeu or self.cam_bloquee or (libre and e.cam_rot is not None)) else 0.0
        self.cam_w = w_jeu if self.cam_saut else self.cam_w + (w_jeu - self.cam_w) * (1.0 - math.exp(-CAM_SCENE_TAU * dt)); self.cam_saut = False
        lacet_a = self._lacet_eff()
        if lacet_a and not (libre and e.cam_rot is not None):           # fleches gauche / droite : la camera tourne autour de la cible du jeu (le cap avance vers +X quand le lacet est positif)
            c_, s_ = math.cos(math.radians(lacet_a)), math.sin(math.radians(lacet_a)); d_ = pos - cib
            pos = cib + np.array([d_[0] * c_ + d_[2] * s_, d_[1], -d_[0] * s_ + d_[2] * c_])
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
        # Repere des sprites (#184) : le panneau d'un personnage prend la rotation de la camera DU JEU (Chara.normalBillboard) ; la rotation autour de la cible (lacet) est suivie (le panneau reste de face, comme dans le jeu a cette orientation)
        self._cadre_sprites = (droite, np.cross(fw, droite), fw)
        return M, (droite, np.cross(fw, droite), fw)


    def _cadre_jeu(self, e):
        """(position, droite, haut, avant) de la camera de la ville telle que le jeu d'origine la place (meme calcul que _camera_ville, SANS la rotation du joueur)."""
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

    def _maj_camera(self):
        """Fleches gauche / droite sur le terrain (a chaque image affichee) : elles tournent la camera autour de sa cible (villes, donjons, tours seulement, pas la carte du monde) ; les deux ensemble la remettent par defaut par une animation,
        par le chemin le plus court (le lacet est gardé entre -180 et 180 degres : 359 degres revient par +1). Vitesse : reglage « Vitesse de caméra » (x1 par defaut) ; la touche d'accelerateur n'y change rien (D-233). Haut / bas ne font rien sur le terrain."""
        t = time.perf_counter(); dt = 1.0 / 60.0 if self.fixe_test else (0.0 if self.t_cam is None else min(0.1, t - self.t_cam)); self.t_cam = t
        if not self._terrain_libre(): return
        g, d = self._tenue('cam_gauche'), self._tenue('cam_droite')
        if not self._camera_pilotable():                                                                           # carte du monde, lieu qui interdit de tourner la camera, scene du jeu : les fleches ne tournent rien
            self.cam_axe['lacet'][0] = False; self.cam_axe['lacet'][1] = bool(g or d)
            return
        vit = float(self.reg['vitesse_camera']); sl = self._etat_axe('lacet', g, d)
        if sl:
            self.lacet = (self.lacet + sl * CAM_LACET_VIT * vit * dt + 180.0) % 360.0 - 180.0
            if self.cam_limite is not None: self.lacet = max(-self.cam_limite, min(self.cam_limite, self.lacet))
        elif self.cam_axe['lacet'][0]:
            err = -self.lacet; pas = max(CAM_RECENTRE_LACET, abs(err) * 5.0) * vit * dt
            if abs(err) <= pas: self.lacet = 0.0; self.cam_axe['lacet'][0] = False
            else: self.lacet += math.copysign(pas, err)

    def _camera_menee(self, mo):
        """La TownCamera verrouillee va-t-elle AILLEURS que sur le joueur ? Mode de cible 1 a 4 (deplacements : travelling, retour) ou 5 (un personnage : la grenouille du prologue...), deplacement en cours, ou cible du jeu a plus de CAM_MENE_DIST du heros
        (plan fixe, heros hors champ). Mode 6 (le joueur) et verrou sans cible a cote du heros : le jeu tient le joueur comme hors scene : AUCUN changement de regime, donc pas de glissement au declenchement."""
        try: _, mode, _, deplace = mo.camera_jeu()
        except Exception: return True
        if 1 <= mode <= 5 or deplace: return True
        e = mo.etat; sp = e.sprites.get(0); hp = sp.get('pos') if sp else None
        if mode == 6: return False
        if hp is None or e.cam_cible is None: return True
        return math.hypot(hp[0] - e.cam_cible[0], hp[2] - e.cam_cible[2]) > CAM_MENE_DIST

    def _coupure_camera(self, e):
        """Pendant ce pas du moteur, la cible de la camera du jeu a-t-elle saute (coupure de scene, changement de carte) ? self.prec = etat du pas precedent."""
        pr = self.prec
        if pr is None or pr['cle'] != (e.partie, e.carte): return True
        a, b = pr['cam_cible'], e.cam_cible
        if a is None or b is None or len(a) != len(b): return True
        return max(abs(x - y) for x, y in zip(a, b)) > CAM_SAUT_VILLE

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

    def _camv(self, mo):
        """(debogage, DQ_CAMV=n) etat de la camera du jeu toutes les n images."""
        e = mo.etat; sp = e.sprites.get(0); hp = sp.get('pos') if sp else None
        r = lambda v: None if v is None else tuple(round(float(x), 1) for x in v)
        print('CAMV n=%d carte=%s partie=%#x cam=%s jeu=%s flag=%#x msg=%d hero=%s cib=%s pos=%s libre=%s' % (self.n, e.carte, e.partie, mo.camera_ville(), mo.camera_jeu(), mo.drapeaux(), mo.msg_visible, r(hp), r(e.cam_cible), r(e.cam_pos), e.cam_libre), flush=True)
        if os.environ.get('DQ_CAMV_SPR'):                                  # (debogage) + tous les sprites et les bulles d'icone

            print('   sprites', {k: (r(s_.get('pos')), s_.get('id'), s_.get('vis', True)) for k, s_ in e.sprites.items()}, 'icones', {k: (i['id'], r(i['pos']), round(i['alpha'], 2)) for k, i in e.icones.items()}, flush=True)
