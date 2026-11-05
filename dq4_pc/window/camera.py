"""Camera : camera des villes (celle du jeu, que le joueur tourne avec les boutons de camera DU JEU), de la carte du monde, du combat et du titre, correction des bords des sprites. Le joueur ne regle que la rotation (fleches gauche / droite, clic molette) :
plus de zoom, d'inclinaison, de centrage ni de lissage de hauteur (retires en #264), plus d'acceleration de la camera (D-233) et plus de rotation faite par la visionneuse a cote du jeu (D-234) : elle est celle du jeu, comme sur mobile."""
import math, os
import numpy as np
import pyglet
from dq4_pc.window import inputs as EN
from dq4_pc.core import engine as ENGINE
from dq4_pc.window.constants import (ASPECT_PORTRAIT, LOOK_DOWN_DEFAULT, CAM_DRAG_MAX, CAM_DRAG_STEP, TITLE_MAP, CB_DEC_Z, CB_SCENERY_SCALE,
    CB_FAR, CB_FOV_NOMINAL, CB_NEAR, CB_YOFFSET, CH_SCALE, CH_PX, CH_VIEW_HEIGHT, EDGE_CORRECTION_DEFAULT, DIST_ADJ_TOWN, TOWN_FOV_DEFAULT, MODE_PP, TOWN_FAR, TOWN_NEAR)
from dq4_pc.window.helpers import camera_free, matrix, rot_unity


class CameraMixin:
    """Camera : camera des villes (celle du jeu : le joueur la tourne par les boutons de camera du jeu), de la carte du monde, du combat et du titre, correction des bords des sprites."""

    def _field_camera(self, e, aspect):
        """Carte du monde, comme Field.Init / Field.SetPosition du jeu : camera orthographique vue de dessus (Rotate(90, 0, 0)), centree sur le point donne par le moteur
        (en pixels de 16 par tuile). Le haut de l'ecran est le nord (-Z), l'est est a droite. Hauteur visible = CH_VIEW_HEIGHT tuiles (le heros a la meme taille que dans les villes) x echelle du jeu (ballon, paquet 30).
        La camera est celle du jeu : aucun reglage du joueur."""
        cx, cz = (e.field['cam'] if e.field and e.field['cam'] else (0.0, 0.0))
        dh = CH_VIEW_HEIGHT / 2 * float(getattr(e, 'field_scale', 1.0)); dl = dh * aspect          # meme champ pour tous les shaders ; echelle du jeu (ballon : jusqu'a 1,25, Field.SetScale : orthographicSize x echelle, MAP-02)
        if self.mode == MODE_PP: cx, cz = round(cx) / CH_PX, round(cz) / CH_PX; ui_scale = 1.0       # pixel perfect : camera sur un pixel de la carte, heros a sa taille exacte (24 x 32 pixels de la carte)
        else: cx, cz = cx / CH_PX, cz / CH_PX; ui_scale = CH_SCALE
        self._field_view = (cx, cz, dl, dh)                                      # (la camera de la carte du monde ne se regle pas : ni angle ni rotation)
        M = np.zeros((4, 4)); M[0, 0] = 1 / dl; M[0, 3] = -cx / dl
        M[1, 2] = -1 / dh; M[1, 3] = cz / dh                                            # ecran y = -(z - cz) / dh
        M[2, 1] = -1 / 100.0; M[3, 3] = 1.0                                             # profondeur : la hauteur (vue de dessus)
        return M, np.array([1.0, 0.0, 0.0]), 24 / CH_PX * ui_scale, 32 / CH_PX * ui_scale

    def _drivable_camera(self):
        """Les boutons de camera du jeu (fleches gauche / droite, clic molette) sont-ils envoyes au moteur ? Terrain libre d'une ville, d'un donjon ou d'une tour : ni la carte du monde, ni l'ecran-titre, ni un message, un menu, une carte ou un effet.
        Le reste (joueur verrouille par un evenement, camera tenue par une scene, lieu qui interdit de la tourner, limites de rotation) est decide par le jeu lui-meme, comme sur mobile : il refuse alors le bouton (Engine.camera_wait)."""
        e = self.engine.state
        return (self._terrain_free() and e.part == ENGINE.PART_TOWN and getattr(self, 'map_name', None) != TITLE_MAP and self.license_panel is None and self.saves_screen is None and not self._name_entry_in_progress())

    def recenter_camera(self):
        """Clic molette, ou les deux fleches ensemble : les deux boutons de camera du jeu ensemble au prochain pas = le jeu ramene la camera au nord (TownPlayerManager::setCameraRotToNorth : il anime le retour et tient le joueur pendant ce temps)."""
        self.cam_recenter = True

    def _axis_state(self, minus, plus):
        """Les deux fleches de la camera : -1 (gauche) / 0 / +1 (droite) = sens demande a la main. Les deux ensemble demandent le retour au nord, une seule fois ; tant qu'il en reste une enfoncee apres cette pression double, rien ne se passe
        (le relachement n'est jamais exactement simultane)."""
        if minus and plus:
            if not self.cam_two: self.cam_recenter = True
            self.cam_two = True; return 0
        if not (minus or plus): self.cam_two = False; return 0
        if self.cam_two: return 0
        return 1 if plus else -1

    def _bits_camera(self):
        """Boutons de camera du jeu a envoyer a ce pas du moteur (ENGINE.CAM_G / ENGINE.CAM_D ; les deux ensemble : retour au nord), d'apres les fleches, le clic molette et le glissement du clic molette (rotation encore a faire : `cam_request`).
        Hors du terrain libre rien n'est envoye et les demandes en attente sont oubliees. Le sens envoye est garde pour Game._camera_after_step."""
        self.cam_direction = (0, False)
        g, d = self._held('cam_gauche'), self._held('cam_droite')
        if not self._drivable_camera(): self._camera_oublier(); return 0
        direction = self._axis_state(g, d); dragging = False
        if self.cam_recenter: self.cam_recenter = False; self.cam_request = 0.0; return ENGINE.CAM_G | ENGINE.CAM_D
        if not direction and not (g or d) and abs(self.cam_request) >= ENGINE.CAM_STEP / 2: direction = 1 if self.cam_request > 0 else -1; dragging = True
        if not direction: return 0
        self.cam_direction = (direction, dragging)
        return ENGINE.CAM_D if direction > 0 else ENGINE.CAM_G

    def _camera_oublier(self):
        """Rien n'est envoye a la camera du jeu a ce pas (menu, message, titre, carte du monde...) : les demandes en attente (retour au nord, rotation de la souris) sont oubliees, et deux fleches deja tenues ne comptent pas comme une pression double
        au retour sur le terrain."""
        self.cam_recenter = False; self.cam_request = 0.0; self.cam_direction = (0, False); self.cam_two = bool(self._held('cam_gauche') and self._held('cam_droite'))

    def _camera_after_step(self, eng):
        """Apres un pas du moteur envoye avec un bouton de camera : le jeu l'a-t-il pris (Engine.camera_wait) ? Il tourne alors d'un cran (ENGINE.CAM_STEP degres) au pas suivant ; au-dela d'un cran par pas, on lui en fait faire les autres tout de suite
        (Engine.camera_turn) : reglage « Vitesse de camera » aux fleches (x2 = deux crans par pas ; la vitesse non entiere se repartit d'un pas a l'autre), jusqu'a CAM_DRAG_STEP crans pour que le glissement du clic molette suive le pointeur.
        S'il refuse (verrou du joueur, scene, lieu qui interdit de la tourner, limite atteinte), la rotation demandee a la souris est abandonnee : la camera reste ou le jeu la met."""
        (direction, dragging), self.cam_direction = self.cam_direction, (0, False)
        if not direction: return
        kind = ENGINE.ROT_CAM_RIGHT if direction > 0 else ENGINE.ROT_CAM_LEFT
        if eng.camera_wait() != kind:
            if dragging: self.cam_request = 0.0
            return
        if dragging:
            n = max(1, min(CAM_DRAG_STEP, int(round(abs(self.cam_request) / ENGINE.CAM_STEP))))
            self.cam_request -= direction * n * ENGINE.CAM_STEP
        else:
            self.cam_acc += float(self.reg['vitesse_camera']); n = max(1, int(self.cam_acc)); self.cam_acc = max(0.0, self.cam_acc - n)
        if n > 1: eng.camera_turn(kind, n)

    def _engine_yaw(self):
        """Cap de la camera du jeu en degres (0 = le cap d'origine des villes, vers +Z ; positif vers +X, comme la fleche droite), pour l'affichage de F1."""
        e = self.engine.state
        if e.cam_pos is None or e.cam_target is None: return 0.0
        return math.degrees(math.atan2(e.cam_target[0] - e.cam_pos[0], e.cam_target[2] - e.cam_pos[2]))

    def on_mouse_scroll(self, x, y, sx, sy):
        """Molette : fait defiler le menu Echap ou la licence ; sur le terrain elle ne fait plus rien (plus de zoom, #264)."""
        if not self._ready: return
        if self.pause.opened: self.pause.wheel(sy); return
        if self.license_panel is not None: self.license_panel.scroll_by(-sy * 60.0)

    def _wheel_press(self, x, y):
        """Bouton du milieu enfonce : un clic (la camera revient au nord) ou le debut d'un glissement (rotation de la camera). Hors du terrain (menus, messages, combat, titre...) il ne fait rien."""
        if self.hud.dpad_on or self.press_state or not self._drivable_camera(): self.wheel.cancel(); return
        self.wheel.press_state(x, y)

    def _wheel_drag(self, x, y):
        """Bouton du milieu maintenu et pointeur deplace : la camera tourne (a gauche / a droite seulement ; le deplacement vertical ne fait rien), memes sens par defaut que les fleches (entrees.pivoter) ;
        le reglage « Inverser gauche / droite » inverse le sens du glissement (jamais celui des fleches du clavier). Le jeu tourne par crans (voir _camera_after_step)."""
        dx = self.wheel.move_to(x, y)
        if not dx or not self._drivable_camera(): return
        self.cam_recenter = False                                             # un glissement annule le retour au nord demande et pas encore envoye
        self.cam_request = EN.rotate(self.cam_request, dx, self.height, bool(self.reg['camera_inverser_gd']), CAM_DRAG_MAX)

    def _wheel_release(self):
        """Bouton du milieu relache sans avoir glisse : clic = la camera revient au nord (sur le terrain libre d'une ville seulement)."""
        if self.wheel.let_go() and self._drivable_camera(): self.recenter_camera()

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        """Menu Echap : un curseur maintenu suit la souris ; sur le terrain, la croix a l'ecran tenue a la souris ; bouton du milieu : rotation de la camera."""
        if not self._ready: return
        self.mouse = (x, y)                                          # (pendant un appui, pyglet n'envoie plus on_mouse_motion : la position sert a savoir si le doigt est toujours sur le bouton)
        M = pyglet.window.mouse
        if buttons & M.MIDDLE and not buttons & M.LEFT: self._wheel_drag(x, y); return
        if self.pause.opened: self.pause.drag_to(x, y)
        elif self.license_panel is not None: self.license_panel.dragging and self.license_panel.drag_to(y)
        elif self.hud.dpad_on: self.hud.dpad_drag(x, y)


    # ---- combat : decor + monstres (maillages dynamiques du moteur)
    def _rot_camera(self, e):
        """Rotation Unity de la camera de combat (NativeManager.cmd_camera + SceneCamera.Update, mode sans cible) : euler (-x, -(y + 180), z)."""
        ax, ay, az = e.cam_rot
        return rot_unity(-ax, -(ay + 180.0), az)

    def _town_camera(self, e, aspect):
        """Camera d'une ville comme Unity (SceneCamera.Update, mode avec cible) : LookAt(position, cible), tangage - lookDownAdjust, puis avance de distanceAdjust le long de l'axe. Celle du jeu (#264) : position, cible,
        champ, decalage vertical et rotation envoyes par le moteur, sans zoom, inclinaison, centrage sur le heros ni lissage de hauteur de la visionneuse (TownCamera::execute suit le joueur et borne sa cible aux bords de la carte).
        La rotation que le joueur lui donne est celle du jeu aussi (boutons de camera envoyes au moteur, D-234) : position et cible l'ont deja, rien n'y est ajoute ici, et le jeu la reprend dans ses scenes comme sur mobile.
        Projection : champ HORIZONTAL fov x 4/3 fixe, hauteur deduite de l'ecran portrait d'origine (0,5625). En 16/9 on garde la meme hauteur de champ que sur mobile et on montre plus de decor sur les cotes : la bande
        centrale de la fenetre est exactement l'image du telephone."""
        pos, target_pos = np.array(e.cam_pos, float), np.array(e.cam_target, float)
        free = camera_free(e)
        fov_h = math.radians((e.cam_fov if e.cam_fov is not None else TOWN_FOV_DEFAULT) * 4.0 / 3.0)
        th_v = math.tan(fov_h / 2) / ASPECT_PORTRAIT                      # tangente du demi-champ vertical de l'original
        if free and e.cam_rot is not None:                         # camera libre (paquet 11, bit 7) : position + angles, comme en combat
            R = self._rot_camera(e); fw = R @ np.array([0.0, 0.0, 1.0]); topmost = R @ np.array([0.0, 1.0, 0.0])
        else:
            fw = target_pos - pos; fw /= np.linalg.norm(fw)
            yaw = math.atan2(fw[0], fw[2]); tang = math.asin(-fw[1]) - math.radians(e.cam_down if e.cam_down is not None else LOOK_DOWN_DEFAULT)
            fw = np.array([math.sin(yaw) * math.cos(tang), -math.sin(tang), math.cos(yaw) * math.cos(tang)]); topmost = np.array([0.0, 1.0, 0.0])
            pos = pos + fw * DIST_ADJ_TOWN
        M, right = matrix(pos, pos + fw * 10, math.degrees(2 * math.atan(th_v)), aspect, n=e.cam_near or TOWN_NEAR, f=(e.cam_far or TOWN_FAR) + (0.05 * self.n_loop if os.environ.get('DQ_ZDEBUG') else 0.0), topmost=topmost)      # (test) DQ_ZDEBUG : le plan lointain change a chaque image : seules les surfaces en z-fighting changent d'une image a l'autre
        yoff = e.cam_yoff or 0.0
        if yoff:
            Ty = np.eye(4); Ty[1, 3] = yoff; M = Ty @ M              # SceneCamera.s_yOffset
        self._view_border = (np.array(pos, float), right, np.cross(fw, right), fw)
        # Repere des sprites (#184) : le panneau d'un personnage prend la rotation de la camera DU JEU (Chara.normalBillboard) : celle de la vue
        return M, (right, np.cross(fw, right), fw)


    def _game_border(self, e):
        """(position, droite, haut, avant) de la camera de la ville telle que le jeu d'origine la place (meme calcul que _town_camera, NO_DEFAULT la rotation du joueur)."""
        pos, target_pos = np.array(e.cam_pos, float), np.array(e.cam_target, float)
        if camera_free(e) and e.cam_rot is not None:
            R = self._rot_camera(e); fw = R @ np.array([0.0, 0.0, 1.0]); topmost = R @ np.array([0.0, 1.0, 0.0])
        else:
            fw = target_pos - pos; fw /= np.linalg.norm(fw)
            yaw = math.atan2(fw[0], fw[2]); tang = math.asin(-fw[1]) - math.radians(e.cam_down if e.cam_down is not None else LOOK_DOWN_DEFAULT)
            fw = np.array([math.sin(yaw) * math.cos(tang), -math.sin(tang), math.cos(yaw) * math.cos(tang)]); topmost = np.array([0.0, 1.0, 0.0])
            pos = pos + fw * DIST_ADJ_TOWN
        right = np.cross(topmost, fw); right /= np.linalg.norm(right)
        return pos, right, np.cross(fw, right), fw

    def _battle_camera(self, e, aspect):
        R = self._rot_camera(e)
        cam = np.array(e.cam_pos, float); fw = R @ np.array([0.0, 0.0, 1.0]); topmost = R @ np.array([0.0, 1.0, 0.0])
        fov_h = math.radians((e.cam_fov if e.cam_fov is not None else CB_FOV_NOMINAL) * 4.0 / 3.0)         # SceneCamera.Update : fov x 4/3, applique a l'horizontale (matrice de projection transposee)
        fov_v = math.degrees(2 * math.atan(math.tan(fov_h / 2) / (4.0 / 3.0)))                         # vue d'origine 4/3 ; en 16/9 on garde la meme hauteur de champ et on montre plus de decor sur les cotes
        M, _ = matrix(cam, cam + fw * 10, fov_v, aspect, n=CB_NEAR, f=CB_FAR, topmost=topmost)
        Ty = np.eye(4); Ty[1, 3] = CB_YOFFSET; M = Ty @ M                                              # SceneCamera.s_yOffset : decalage vertical de l'image
        if self.cb_mx: M = M @ np.diag([-1.0, 1.0, 1.0, 1.0])
        T = np.diag([CB_SCENERY_SCALE] * 3 + [1.0]); T[2, 3] = CB_DEC_Z                              # NativeManager.cmd_fld_load en mode combat : FldObject.SetDispScale(6, 6, 6), applique a la racine du decor (FldObject.Update)
        return M, M @ T

    def _dbg_proj(self, M, e, cam3d, to_draw, icons):
        """(debogage, DQ_PROJ=n) pixels (x, y depuis le haut) des pieds / haut des panneaux des sprites et des bulles, toutes les n images."""
        def px(P):
            v = M @ np.array([P[0], P[1], P[2], 1.0]); return None if v[3] <= 1e-6 else (round(float((v[0] / v[3] * 0.5 + 0.5) * self.width), 1), round(float((1 - (v[1] / v[3] * 0.5 + 0.5)) * self.height), 1))
        out = {}
        for slot, f, vl in to_draw:
            q = np.array(vl.position[:], float).reshape(-1, 3); out['s%d' % slot] = (px(q[0]), px(q[1]), px(q[2]), px(q[5]))       # coins : bas-gauche, bas-droit, haut-droit, haut-gauche
        for slot, ic in sorted(e.icons.items()):
            if ic['pos'] is not None: out['i%d' % slot] = (px(ic['pos']),)
        for tex, vl in icons:
            q = np.array(vl.position[:], float).reshape(-1, 3); out['bulle'] = (px(q[0]), px(q[1]), px(q[2]), px(q[5]))
        print('PROJ n=%d' % self.n_loop, out, flush=True)

    def _edge_correction(self):
        """Intensite (0 a 1) de la correction des bords des sprites (villes, donjons, tours ; voir _town_panel) : 0 par defaut depuis #184 (« reviens a la position brute des PNJ, exactement comme dans le jeu » : panneau
        d'origine, sans reconstruction a l'ecran) ; l'ancienne correction complete (bords verticaux, proportion constante, #134) s'obtient avec l'option --correction-bords ou la variable d'environnement DQ_CORRECTION_BORDS,
        de 0 (aucune, defaut) a 100 (complete). Ce n'est pas un reglage du joueur (l'ancienne option « Correction des bords des sprites » est retiree)."""
        v = getattr(self.args, 'edge_correction', None)
        if v is None and os.environ.get('DQ_CORRECTION_BORDS'):
            try: v = float(os.environ['DQ_CORRECTION_BORDS'])
            except ValueError: v = None
        return EDGE_CORRECTION_DEFAULT if v is None else min(1.0, max(0.0, float(v) / 100.0))

    def _sprite_reference(self, cam3d, corr):
        """(droite, haut, avant) qui oriente le panneau d'un personnage de ville : le repere de la camera DU JEU (Chara.normalBillboard prend la rotation de la camera du jeu, celle que le joueur lui donne comprise : meme inclinaison que sur le mobile,
        et un personnage ne « s'aligne » pas sur la vue quand on monte ou descend la camera), qui est celui de la vue depuis que la visionneuse ne tourne plus la camera a cote du jeu (D-234). `corr` : intensite de la correction des bords (voir _edge_correction)."""
        return cam3d

    SPRITE_TILT_DEFAULT = 0.0                                       # part de l'inclinaison des verticales du monde que prend le sprite : 0 = bords exactement verticaux (defaut depuis #180 : l'essai #134 a 0,5 deformait les sprites pres des bords), 1 = parallele aux murs

    def _sprite_tilt(self):
        """(Essai #134, RETIRE par defaut en #180 : « remets l'affichage des PNJ comme sur la version mobile, ... ils s'etirent quand ils s'approchent du bord ») Part (0 a 1) de l'inclinaison des VERTICALES DU MONDE (aretes de murs, portes...) que prend le panneau d'un personnage a l'ecran, 0 par defaut (essai : 0,5). Depuis la correction des bords (_town_panel) le sprite est
        exactement vertical a l'ecran partout, mais les murs voisins penchent (11 a 19 degres a 9 unites du centre en 16/9, camera a 47 degres, contre 4 a 6,5 sur le portrait du mobile) et cet angle change quand le heros monte ou
        descend : le sprite semble alors se pencher par rapport au decor (illusion d'optique signalee dans #134). Le pencher a moitie vers la verticale du monde reduit cet ecart de moitie sans revenir au panneau d'origine
        (qui s'ecartait du centre de l'image par son seul haut et se deformait). Comparaison avec l'essai : variable d'environnement DQ_SPRITE_INCLINAISON, de 0 (bords verticaux, defaut) a 100 (parallele au decor)."""
        v = os.environ.get('DQ_SPRITE_INCLINAISON')
        if v is None or not v.strip(): return self.SPRITE_TILT_DEFAULT
        try: return min(1.0, max(0.0, float(v) / 100.0))
        except ValueError: return self.SPRITE_TILT_DEFAULT

    @staticmethod
    def _shift_depth(X, F, delta, t, C):
        """Point X (d'un panneau parallele a l'ecran) rapproche de la camera de `delta` unites de profondeur. t = 0 : le long de l'axe de la camera (F), comme les sommets du panneau de la bulle Riseup dans Unity (Riseup.s_vtxDepth) ;
        t = 1 : le long du rayon de vue (camera -> X) : meme point a l'ecran, meme profondeur (sinon le bord decale s'ecarte du centre de l'image de delta x ecart / profondeur : la bulle glisse de cote quand la camera est tournee). Entre les deux : melange lineaire."""
        if t <= 0.0 or C is None: return X - F * delta
        d = X - C; z = float(d @ F)
        if z <= delta * 1.5: return X - F * delta                          # (tout contre la camera : pas de division par une profondeur nulle)
        return X - ((1.0 - t) * delta) * F - (t * delta / z) * d

    def _town_panel(self, p, r_, u_, f_, w, h, zb, zt, t, C, inc=0.0):
        """Les 4 sommets (bas gauche, bas droit, haut droit, haut gauche) du panneau d'un personnage de ville dont les pieds sont en p : un rectangle w x h parallele a l'ecran, dont le bas est recule de `zb` et le haut de `zt`
        vers la camera (profondeur du panneau d'origine, qui penche de 36 degres). t = 0 : le panneau d'origine (decalages le long de l'axe de la camera). Defaut de l'original, rendu visible par le champ horizontal du 16/9
        (le portrait du mobile en voyait bien moins) : le haut, plus proche, s'ecarte du centre de l'image (de zt x ecart / profondeur) et le sprite « se penche » vers l'exterieur pres des bords gauche / droit (jusqu'a 15 a
        20 degres) ; de plus la hauteur a l'ecran se comprime vers le bas de l'image, d'ou un sprite trop large (jusqu'a 0,9 au lieu de 0,75). t = 1 : le panneau est reconstruit A L'ECRAN : meme position, meme hauteur
        et memes profondeurs qu'avant (taille, recouvrements et z-buffer inchanges), mais bords verticaux et largeur = 0,72 x la hauteur a l'ecran (la proportion du panneau au centre de l'image : la largeur y est la
        moyenne de celles du bas et du haut), donc le sprite garde ses proportions partout. Au centre de l'image, rien ne change. Entre les deux : melange lineaire des sommets. Camera inconnue ou panneau contre la camera : l'original.
        `inc` (0 a 1, essai #134, voir _sprite_tilt) : le panneau reconstruit est ensuite CISAILLE vers la verticale du monde, les pieds fixes : le haut glisse de inc x (inclinaison a l'ecran d'une verticale du monde au pied du
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

    def _camv(self, eng):
        """(debogage, DQ_CAMV=n) etat de la camera du jeu toutes les n images."""
        e = eng.state; sp = e.sprites.get(0); hp = sp.get('pos') if sp else None
        r = lambda v: None if v is None else tuple(round(float(x), 1) for x in v)
        print('CAMV n=%d carte=%s partie=%#x cam=%s jeu=%s flag=%#x msg=%d hero=%s cib=%s pos=%s libre=%s' % (self.n, e.game_map, e.part, eng.camera_town(), eng.camera_game(), eng.flags(), eng.msg_visible, r(hp), r(e.cam_target), r(e.cam_pos), e.cam_free), flush=True)
        if os.environ.get('DQ_CAMV_SPR'):                                  # (debogage) + tous les sprites et les bulles d'icone

            print('   sprites', {k: (r(s_.get('pos')), s_.get('id'), s_.get('vis', True)) for k, s_ in e.sprites.items()}, 'icones', {k: (i['id'], r(i['pos']), round(i['alpha'], 2)) for k, i in e.icons.items()}, flush=True)
