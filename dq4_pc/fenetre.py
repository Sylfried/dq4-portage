"""Fenetre PC 16/9 : fait tourner le moteur du jeu et dessine ce qu'il demande (decor, sprites, camera)."""
import os, sys, math, time, argparse, glob, collections, threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pyglet
from pyglet import gl
from pyglet.graphics.shader import Shader, ShaderProgram


import moteur as MO
import donnees as DO
import objets_carte as OC
import hd as HD
import ui_menu as UI
import son as SON
import effet_combat as EC
import reglages as RG
import pause as PA
import hud_mobile as HM
import etats as ET

VERT = '''#version 330 core
in vec3 position; in vec2 tex_coords; in vec4 colors;
uniform mat4 mvp;
centroid out vec2 v_uv; out vec4 v_col;
void main() { gl_Position = mvp * vec4(position, 1.0); v_uv = tex_coords; v_col = colors; }'''
FRAG = '''#version 330 core
centroid in vec2 v_uv; in vec4 v_col; out vec4 fragColor;
uniform sampler2D tex; uniform float cutoff; uniform vec2 tsize; uniform float net; uniform float amul;
void main() {
    vec2 uv = v_uv; float lod = 0.0;
    if (net > 0.5) { vec2 p0 = uv * tsize; vec2 dx = dFdx(p0), dy = dFdy(p0); lod = max(0.0, 0.5 * log2(max(max(dot(dx, dx), dot(dy, dy)), 1e-8))); }      // mipmaps choisies sur l'uv d'origine (l'uv decalee saute d'un texel a l'autre)
    if (net > 1.5) { uv = (floor(uv * tsize) + 0.5) / tsize; }      // pixel perfect : plus proche voisin strict, aucun adoucissement
    else if (net > 0.5) {   // pixel art : on garde des pixels nets, seule la frontiere entre deux pixels est adoucie
        vec2 p = uv * tsize; vec2 b = floor(p + 0.5); vec2 w = max(fwidth(p), vec2(1e-4));       // b = frontiere de texel la plus proche : le centre du texel reste pur, seule une bande d'un pixel d'ecran autour de la frontiere est melangee
        uv = (b + clamp((p - b) / w, -0.5, 0.5)) / tsize;
    }
    vec4 c = (net > 0.5 ? textureLod(tex, uv, lod) : texture(tex, uv)) * clamp(v_col, 0.0, 1.0); if (c.a < cutoff) discard; c.a *= amul; fragColor = c; }'''

VERT_EFFET = '''#version 330 core
in vec2 position; in vec2 tex_coords; in vec4 colors;
out vec2 v_uv; out vec4 v_col;
void main() { gl_Position = vec4(position, 0.0, 1.0); v_uv = tex_coords; v_col = colors; }'''
FRAG_EFFET = '''#version 330 core
in vec2 v_uv; in vec4 v_col; out vec4 fragColor;
uniform sampler2D tex; uniform float lum; uniform float flou;
void main() { vec3 c = texture(tex, v_uv, flou).rgb; fragColor = vec4(c * v_col.rgb * lum, v_col.a * lum); }'''
EFFET_FLOU = 1.0              # Capture.SetBlur(vrai) pendant l'effet : la capture est adoucie (biais de mipmap)

SE_BOUTON = 300               # bruitage de l'appui sur un bouton de menu (joue par Unity, MenuPortItem.Update)
SE_COURANTS = (300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 402, 409, 412)       # decodes des le depart en tache de fond
MODE_PP = len(HD.MODES)       # dernier mode de F2 : pixel perfect (texels nets sans aucun adoucissement ; carte du monde a une echelle entiere, camera et sprites calees sur les pixels)
# Camera des villes, lue dans SceneCamera.Update / Global.CameraInitParams[0] (voir docs/notes-technique-portage-dq4.md) :
ASPECT_PORTRAIT = 0.5625      # SceneCamera.ASPECT_DEF : l'original est concu pour un ecran portrait 450 x 800 ; Unity fixe le champ de vision HORIZONTAL (fov x 4/3) et en deduit la hauteur
RESOLUTIONS = ((1280, 720), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160))
FOV_VILLE_DEF = 9.5           # fov nominal du mode 0 (terrain) tant que le moteur n'en envoie pas (paquet 11)
VILLE_NEAR, VILLE_FAR = 5.0, 100.0
DIST_ADJ_VILLE = 4.0          # SceneCamera.s_distanceAdjust (.cctor) : apres LookAt, la camera avance de 4 unites le long de son axe
BAS_DEF = 0.2                 # SceneCamera.s_lookDownAdjust (.cctor) : la camera releve son tangage de 0,2 degre
SPRITE_L, SPRITE_H, SPRITE_ECHELLE = 24, 32, 0.045
UI_ZOOM = 1.12            # agrandissement des fenetres du jeu (la colonne portrait d'origine remplit exactement la hauteur de la fenetre) ; reduit a 1 si un groupe de fenetres ne tient plus a l'ecran
CB_MSG_BAS = -338.0         # combat : bord bas du cadre de message = bord bas du cadre principal des menus de commandes (Combattre / Attaquer...)
CB_ZONE_MENUS = (-402.0, -144.0)       # combat : zone prise par les menus de commandes (bouton Fuir / retour compris) ; sert a garder la meme echelle d'interface que les messages
MSG_BAS = -362.0           # fenetre de message du terrain descendue : bord bas du cadre (unites d'interface), comme les messages de combat
CH_PX, CH_ATLAS = 16.0, 64                                                  # carte du monde : pixels par tuile, tuiles par ligne d'atlas
# animation de l'eau de la carte du monde (Field.UpdatePattern du jeu) : 5 motifs ; la tuile affichee est numero + decalage du motif, qui avance toutes les 17 images
CH_MOTIF_FIN = np.array([326, 403, 940, 1195, 1260, 1713])                  # fin (exclue) de chaque plage de numeros de tuile (Field.m_patternCheck)
CH_MOTIF_NUM = np.array([0, 1, 2, 0, 3, 4, 0])                              # motif de chaque plage (0 = tuile fixe) ; la derniere valeur sert au-dela de la derniere plage
CH_MOTIF_PAS = (0, 76, 4, 64, 4)                                            # decalage ajoute a chaque pas, par motif (Field.m_patternInfo.acc)
CH_MOTIF_LIM = (0, 608, 96, 512, 96)                                        # le decalage retombe a 0 des qu'il atteint cette limite (.limit)
CH_MOTIF_PERIODE = 17
CH_ECHELLE = 51.84 * 0.48 / 24                                              # Chara.SetFieldMode : echelle 28,8 x 1,8 = 51,84 sur un maillage de 0,48 x 0,64 : le heros fait ~24,9 x 33,2 px (1,04 x la feuille 24 x 32), a plat sur la carte
# ZOOM COMMUN (carte du monde, villes, grottes, tours) : le heros garde partout la meme taille a l'ecran, celle des villes en 16/9 (camera d'origine : distance 39,55 jusqu'a la cible, 4 de moins apres
# SceneCamera.s_distanceAdjust, champ horizontal fov x 4/3 deduit de l'ecran portrait 450 x 800). HEROS_FRAC = hauteur du panneau du heros / hauteur de la fenetre.
HEROS_FRAC = SPRITE_H * SPRITE_ECHELLE / (2.0 * (39.55 - DIST_ADJ_VILLE) * math.tan(math.radians(FOV_VILLE_DEF * 4.0 / 3.0) / 2) / ASPECT_PORTRAIT)       # ~ 0,103
CH_VUE_HAUT = 32.0 / CH_PX * CH_ECHELLE / HEROS_FRAC                         # carte du monde : tuiles visibles en hauteur (~ 20) ; en portrait l'original en montre 28,4 en hauteur et 16 en largeur
CH_GOUT = 2                                                                 # carte du monde : gouttiere (pixels repetes) autour de chaque tuile de 16 px dans l'atlas copie : aucun debordement d'une tuile sur sa voisine au filtrage
CH_CASE = 16 + 2 * CH_GOUT
PP_ECHELLES = (1, 2, 4, 8)                                                  # pixel perfect : pixels d'ecran par pixel de la carte
PAS_MOTEUR = 1.0 / 30.0                                                     # le moteur d'origine avance a 30 Hz (Time.fixedDeltaTime de Boot)

CB_FOV_NOM, CB_NEAR, CB_FAR, CB_YOFFSET, CB_ECHELLE_DECOR = 48.0, 0.25, 500.0, 0.04, 6.0      # combat : Global.CameraInitParams[1] du Unity d'origine (champ de vision nominal ; Unity le multiplie par 4/3 et l'applique a l'horizontale d'une vue 4/3)
_cb = [float(x) for x in os.environ.get('DQ_CB', '0,0').split(',')]
CB_MIROIR_X, CB_DEC_Z = int(_cb[0]), _cb[1]      # (essais) miroir gauche/droite ; decalage du decor sur z
CB_CAP = 1536       # sommets reserves par monstre (listes de taille fixe)
CH_ICONES = {0: (0, 512, 48, 32), 1: (96, 512, 48, 32), 2: (192, 512, 48, 48), 3: (288, 512, 41, 32), 4: (384, 512, 41, 32), 5: (480, 512, 25, 31),
             6: (544, 512, 25, 31), 7: (608, 512, 40, 32), 8: (704, 512, 24, 24), 9: (768, 512, 32, 32), 10: (832, 512, 40, 32), 11: (928, 512, 24, 40),
             12: (0, 448, 32, 46), 13: (64, 448, 26, 28), 14: (128, 448, 41, 39), 15: (224, 448, 27, 42), 16: (288, 448, 48, 48), 17: (384, 448, 40, 32),
             19: (544, 448, 64, 58), 20: (640, 448, 41, 39)}   # icones de lieux de la carte du monde (FieldSymbol.s_symbols : 21 rectangles ; le 18 est vide dans l'atlas)
GOUT_ORIG = 2                 # feuilles d'origine : gouttiere de 2 px (bords repetes) autour de chaque case, comme les feuilles HD : le filtrage n'attrape plus un bout de la case voisine
HD_GOUTTIERE, HD_NIVEAUX = 4, 2      # sprites HD (agrandissement x8, voir hd.py) : marge de 4 px, 2 niveaux de mipmaps
POLICES = ('Segoe UI', 'Arial', 'DejaVu Sans', 'Liberation Sans')
ACT_FRONTS = ('menu', 'discussion', 'carte', 'L', 'R')       # actions dont on detecte l'appui (front montant)
BTN_PAROLE, BTN_MENU, BTN_DISCUSSION, BTN_CARTE = 0x100, 0x800, 0x400, 0x1000     # arg2 de GameUpdate : parler / examiner (exactement 0x100), menu de commandes, discussion de groupe, carte


def rot_unity(ex, ey, ez):
    """Matrice 3x3 d'une rotation Unity (angles d'Euler en degres, ordre z puis x puis y, espace gauche) : colonne = axe local dans le monde."""
    cx, sx, cy, sy, cz, sz = (math.cos(math.radians(ex)), math.sin(math.radians(ex)), math.cos(math.radians(ey)), math.sin(math.radians(ey)), math.cos(math.radians(ez)), math.sin(math.radians(ez)))
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]); Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]); Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def matrice(cam, cible, fov, aspect, n=1.0, f=200.0, haut=(0, 1, 0)):
    pos = np.array(cam, float); fw = np.array(cible, float) - pos; fw /= np.linalg.norm(fw)
    droite = np.cross(haut, fw); droite /= np.linalg.norm(droite); haut = np.cross(fw, droite)
    th = math.tan(math.radians(fov) / 2)
    M = np.zeros((4, 4))
    M[0, :3] = droite / (th * aspect); M[0, 3] = -pos @ droite / (th * aspect)
    M[1, :3] = haut / th; M[1, 3] = -pos @ haut / th
    k = (f + n) / (f - n)
    M[2, :3] = fw * k; M[2, 3] = -pos @ fw * k - 2 * f * n / (f - n)
    M[3, :3] = fw; M[3, 3] = -pos @ fw
    return M, droite


class Jeu(pyglet.window.Window):
    def __init__(self, args, reg=None):
        self._pret = False                      # les evenements (souris...) recus pendant la creation de la fenetre sont ignores
        self.reg = reg or RG.Reglages(None)
        self.pause = PA.Pause(self)
        self.msaa = 0
        for ms in ((args.msaa, 0) if args.msaa else (0,)):       # anticrenelage materiel si la carte le permet
            try:
                cfg = gl.Config(depth_size=24, double_buffer=True, major_version=3, minor_version=3, sample_buffers=1 if ms else 0, samples=ms)
                super().__init__(args.largeur, args.hauteur, caption='Dragon Quest IV - portage PC (essai)', resizable=True, config=cfg, vsync=True)
                self.msaa = ms; break
            except pyglet.window.NoSuchConfigException:
                print('MSAA x%d indisponible' % ms, flush=True)
        print('MSAA : %s' % ('x%d' % self.msaa if self.msaa else 'non'), flush=True)
        self.args = args
        self._attente('Chargement du moteur...')
        self.mode = max(0, min(int(args.hd), MODE_PP)); self.lissage = bool(self.reg['lissage']); self.aniso = self._anisotropie(); self.est_plein = False; self.taille_fenetre = (args.largeur, args.hauteur)
        self.pool = ThreadPoolExecutor(max_workers=1); self.hd_jobs = {}; self.decor_hd = {}; self.decor_arr = {}; self.carte_src = None; self.sprite_vl = {}; self.icone_vl = {}; self.icone_tex = {}; self._menu_tex = None; self._dom_lie = None; self.plans = {}
        self.champ_cle = None; self.champ_tex = None; self.champ_tex_ico = None; self.champ_nearest = None; self.champ_vl = None; self.champ_base = None; self.champ_ico = None
        self.motif_n = 0; self.motif_acc = np.zeros(5, np.int64); self.champ_g = None; self.champ_pat = None; self.champ_acc_vu = None       # eau animee de la carte du monde
        self.champ_zoom = float(args.carte_zoom); self.pp_auto = not self.reg['echelle_pp']; self.pp_k = self._k_auto() if self.pp_auto else int(self.reg['echelle_pp']); self._vue_champ = None       # carte du monde : zoom (molette de la souris) et zone visible (cx, cz, demi-largeur, demi-hauteur en tuiles)
        self.n_combat = 0; self.cb_tex = {}; self.cb_vl = {}
        self.ui_tf = {}; self.ui_k = 1.0; self.cur_local = {}; self.appui = None; self.survol = None; self.clic_a = self.clic_b = False; self.ui_dz = 0.0; self.ui_suit = set()       # souris : bouton appuye (port, numero, manette), clics en attente
        self.cb_mx = CB_MIROIR_X; self.cb_ordre = int(os.environ.get('DQ_ORDRE', '0'))                 # combat : textures de monstres (m<id>) et maillages
        self.angle_cam = float(self.reg['angle_camera']); self.etat_annul = None; self.toasts = []; self.sauve_rapide = None; self.combo = [False, False]
        self.aide = bool(self.reg['infos']); self.cadre_aide = pyglet.shapes.Rectangle(0, 0, 1, 1, color=(0, 0, 0, 150))      # F1 : lignes d'information en haut a gauche + cadre noir translucide
        self.t_demarrage = time.time(); self.etiq_conseil = pyglet.text.Label('Échap : menu    F1 : infos', font_name=POLICES, font_size=11, color=(255, 255, 255, 200), x=10, y=8, anchor_x='left', anchor_y='bottom')
        self.stats = True; self.ecarts = collections.deque(maxlen=120); self.t_prec = None; self.dt_dessin = 0.0
        self.prog = ShaderProgram(Shader(VERT, 'vertex'), Shader(FRAG, 'fragment'))
        self.prog_effet = ShaderProgram(Shader(VERT_EFFET, 'vertex'), Shader(FRAG_EFFET, 'fragment'))
        self.effet_tex = None; self.effet_sim = None; self.effet_vl = None; self.effet_ref = None; self.effet_tex_prete = False      # effet de debut de combat : capture de l'ecran, simulation, sommets
        self.donnees = DO.Donnees(None, args.cache, log=lambda *a: print(*a, flush=True))
        self.moteur = MO.Moteur(args.apk, args.saves_lecture, args.saves_ecriture); self.moteur.duree_anim = self._duree_anim
        self._attente('Chargement de la sauvegarde...')
        self.donnees.apk = self.moteur.apk_donnees
        self.prepa_arret = threading.Event(); self.prepa_proc = None
        self.hud = HM.Boutons(self); self.hud_decl = 0; self.carte_vue = 1; self.carte_ouverte = False; self.nb_degats = []; self._nb_tex = None
        if not args.sans_preparation:           # extrait en arriere-plan cartes, sprites et monstres pas encore en cache : plus de lecture du gros paquet de donnees en pleine partie
            self._lancer_preparation(args.cache)
        self.son = SON.Son(self.moteur.apk_donnees, args.cache, log=lambda *a: print(*a, flush=True), volume_musique=args.volume_musique, volume_bruitages=args.volume_bruitages, actif=bool(self.reg['son']) and not args.sans_son)
        self.son.precharger(SE_COURANTS)
        self.touches = pyglet.window.key.KeyStateHandler(); self.push_handlers(self.touches)
        self.carte_nom = None; self.fond_decor = None; self.carte_vl = []; self.tex_gl = {}; self.sprite_tex = {}; self.palettes = None; self.pam_gl = {}
        self.carte_pos = {}; self.plages = {}; self.noms = {}; self.objets = None; self.bornes_x = None
        self.etiquette = pyglet.text.Label('', x=10, y=self.height - 10, anchor_y='top', font_size=11, color=(255, 255, 255, 255), multiline=True, width=600)
        self.etiq_stats = pyglet.text.Label('', x=10, y=self.height - 50, anchor_y='top', font_size=10, color=(255, 230, 150, 255), multiline=True, width=600)
        self.etiq_hd = pyglet.text.Label('', x=10, y=self.height - 30, anchor_y='top', font_size=10, color=(200, 220, 255, 255), multiline=True, width=600)
        if args.slot:
            ok = self.moteur.charger_sauvegarde(args.slot)
            print('sauvegarde %d chargee : %s' % (args.slot, 'oui' if ok else 'NON (fichier data%d.dat introuvable ou invalide dans %s)' % (args.slot, args.saves_lecture)), flush=True)
            if ok:      # on laisse le moteur lancer la carte sauvegardee avant le premier affichage
                for _ in range(6): self.moteur.step(0, 0)
                self._attente('Chargement de la carte...')
                e = self.moteur.etat
                if e.carte: self._charger_carte(e.carte)      # les chargements lourds se font ici, pas pendant le jeu
                for sp in list(e.sprites.values()): self._feuille(sp['id'], self.mode)
                e.sons = [x for x in e.sons if x[0] == 37][-1:]      # les bruitages du chargement sont perdus, la musique de la carte reste
        self.n = 0; self.dt_moteur = 0.0; self.pad_prec = 0; self.rep = {}; self.act_prec = {}
        self.msg_cle = None; self.msg_img = None; self.msg_spr = None; self.msg_h = 0
        self.etiq_menu = {}; self.focus_vu = None; self.menu_relacher = None
        self.ui_rendu = None; self.ui_g = None; self.ui_msg = None; self.canevas_cle = None
        if not args.ui_simple: self._init_ui()
        # boucle a pas fixe : le moteur avance exactement a 30 Hz (comme FixedUpdate de l'original) quelle que soit la cadence d'affichage, et l'image affichee est calculee entre deux pas
        self.acc = 0.0; self.t_boucle = None; self.alpha = 1.0; self.prec = None; self.pas_t = collections.deque(maxlen=60)
        self.n_boucle = 0; self.base_c = {}
        if self.reg['plein_ecran'] and not args.shot: pyglet.clock.schedule_once(lambda dt: (self.regler_plein_ecran(True)), 0.5)       # plein ecran memorise
        self.fixe_test = bool(args.shot) and not os.environ.get('DQ_TEMPS_REEL')         # (test) un pas par image affichee, sans horloge ni interpolation ; DQ_TEMPS_REEL=1 : horloge reelle (vitesse, course)
        pyglet.clock.schedule(self._boucle)      # execute avant le dessin des fenetres (pyglet.app.run(interval=0))
        self._pret = True

    def _init_ui(self):
        """Fenetres de menu d'origine (mise en page lue dans le code Unity du jeu) ; sans le fichier cache/ui_layout.json on garde les menus simples."""
        a = self.args; lay = os.path.join(a.cache, 'ui_layout.json')
        if not os.path.exists(lay):
            print('Menus : mise en page d\'origine absente (%s) -> menus simples. Lancez outils\\generer_ui.bat pour la creer.' % lay, flush=True); return
        if not UI.preparer_ressources(a.apk, a.cache, log=lambda *x: print(*x, flush=True)): return
        try:
            from PIL import Image
            ml = UI.MiseEnPage(lay, os.path.join(a.cache, 'ui_frameData.bin'))
            feuilles = {0: np.array(Image.open(os.path.join(a.cache, 'ui_MenuTexture.png')).convert('RGBA')), 1: np.array(Image.open(os.path.join(a.cache, 'ui_Button.png')).convert('RGBA'))}
            self.ui_rendu = UI.Rendu(ml, feuilles, os.path.join(a.cache, 'ui_font.otf')); self.ui_g = UI.Gestionnaire(ml); self.moteur.ui.obs = self.ui_g; self.ui_g.proj = self._ui_x_monstres; self.ui_g.rejouer(self.moteur.ui)
            if ml.message: self.ui_msg = UI.FenetreMessage(ml)
            print('Menus : mise en page d\'origine chargee (%d types%s).' % (len(ml.types), ', fenetre de message' if self.ui_msg else ''), flush=True)
        except Exception as e:
            print('Menus : mise en page d\'origine inutilisable (%r) -> menus simples.' % (e,), flush=True); self.ui_rendu = None; self.ui_g = None

    def _attente(self, texte):
        """Ecran noir avec un message : la fenetre reste vivante pendant les chargements."""
        try:
            self.switch_to(); gl.glClearColor(0, 0, 0, 1); self.clear()
            pyglet.text.Label(texte, x=self.width // 2, y=self.height // 2, anchor_x='center', anchor_y='center', font_size=16, color=(255, 255, 255, 255)).draw()
            self.flip(); self.dispatch_events()
        except Exception: pass

    # ---- textures
    def _anisotropie(self):
        """Niveau d'anisotropie maximal utilisable (1.0 si l'extension manque), plafonne a 8."""
        try:
            v = (gl.GLfloat * 1)(); gl.glGetFloatv(0x84FF, v); return max(1.0, min(8.0, float(v[0])))
        except Exception:
            return 1.0

    def _tex(self, arr, repeat, mip=0):
        """Texture RGBA ; mip > 0 : mipmaps (limites a `mip` niveaux, 99 = tous) + filtrage anisotrope."""
        h, w = arr.shape[:2]
        img = pyglet.image.ImageData(w, h, 'RGBA', np.ascontiguousarray(arr[::-1]).tobytes(), pitch=w * 4)
        t = img.get_texture()
        gl.glBindTexture(t.target, t.id)
        m = gl.GL_REPEAT if repeat else gl.GL_CLAMP_TO_EDGE
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, m); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, m)
        if mip:
            gl.glGenerateMipmap(t.target)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAX_LEVEL, min(mip, 20))
            self._filtrer(t, True)
        return t

    def _filtrer(self, t, lisse):
        """Filtrage d'une texture de decor mipmappee (F3) : de loin, toujours mipmaps trilineaires + anisotrope (stable) ; de pres, lisse = bilineaire, sinon plus proche voisin (texels nets)."""
        gl.glBindTexture(t.target, t.id)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR if lisse else gl.GL_NEAREST)
        if self.aniso > 1.0: gl.glTexParameterf(t.target, 0x84FE, self.aniso)

    def _feuille_orig(self, ident):
        """Feuille `h<ident>` d'origine (pixels nets) ; False si absente."""
        cle = (ident, 0)
        if cle in self.sprite_tex: return self.sprite_tex[cle]
        arr = self.donnees.feuille(ident); r = False
        if arr is not None:
            nl = 8 if arr[4 * SPRITE_H:5 * SPRITE_H, :72, 3].any() else 4
            atlas, _, _ = HD.agrandir_feuille(arr, SPRITE_L, SPRITE_H, 3, nl, lambda c: HD._dilater(c, 2), GOUT_ORIG, 1)         # pixels transparents = couleur du bord voisin : plus de liseré sombre au filtrage
            r = dict(t=self._tex(atlas, False), tw=atlas.shape[1], th=atlas.shape[0], nl=nl, hd=False, cl=SPRITE_L, ch=SPRITE_H, g=GOUT_ORIG, arr=arr)
        self.sprite_tex[cle] = r
        return r

    def _calcul_hd(self, arr, nl, ident, cid, algo):
        """(tache de fond) atlas HD d'une feuille, lu dans le cache disque s'il existe."""
        f = os.path.join(self.args.cache, 'hd_%s_v%d_h%d.npy' % (cid, HD.VERSION, ident))
        try:
            if os.path.exists(f): return np.load(f), SPRITE_L * HD.FACTEUR, SPRITE_H * HD.FACTEUR
        except Exception: pass
        atlas, cl, ch = HD.agrandir_feuille(arr, SPRITE_L, SPRITE_H, 3, nl, algo, HD_GOUTTIERE)
        try: np.save(f, atlas)
        except Exception: pass
        return atlas, cl, ch

    def _feuille(self, ident, mode):
        """Feuille de sprites pour le mode choisi. Les versions HD sont calculees en tache de fond : en attendant, l'original sert."""
        orig = self._feuille_orig(ident)
        if not orig or mode in (0, MODE_PP): return orig
        cle = (ident, mode)
        if cle in self.sprite_tex: return self.sprite_tex[cle]
        fut = self.hd_jobs.get(cle)
        if fut is None:
            _nom, cid, algo = HD.MODES[mode]
            self.hd_jobs[cle] = self.pool.submit(self._calcul_hd, orig['arr'], orig['nl'], ident, cid, algo)
            return orig
        if not fut.done(): return orig
        del self.hd_jobs[cle]
        try: atlas, cl, ch = fut.result()
        except Exception as ex:
            print('lissage HD impossible (%s, h%d) : %s' % (HD.MODES[mode][0], ident, ex), flush=True); self.sprite_tex[cle] = orig; return orig
        r = self.sprite_tex[cle] = dict(t=self._tex(atlas, False, HD_NIVEAUX), tw=atlas.shape[1], th=atlas.shape[0], nl=orig['nl'], cl=cl, ch=ch, g=HD_GOUTTIERE, hd=True)
        return r

    def _camera_champ(self, e, aspect):
        """Carte du monde, comme Field.Init / Field.SetPosition du jeu : camera orthographique vue de dessus (Rotate(90, 0, 0)), centree sur le point donne par le moteur
        (en pixels de 16 par tuile). Le haut de l'ecran est le nord (-Z), l'est est a droite. Hauteur visible = CH_VUE_HAUT tuiles (le heros a la meme taille que dans les villes) / zoom."""
        cx, cz = (e.champ['cam'] if e.champ and e.champ['cam'] else (0.0, 0.0))
        if self.mode == MODE_PP:       # pixel perfect : k pixels d'ecran par pixel de la carte (entier), camera sur un pixel de la carte, heros a sa taille exacte (24 x 32)
            k = self._k_pp(); cx, cz = round(cx) / CH_PX, round(cz) / CH_PX
            dh = self.height / (2.0 * k * CH_PX); dl = self.width / (2.0 * k * CH_PX); ech = 1.0
        else:
            cx, cz = cx / CH_PX, cz / CH_PX; dh = CH_VUE_HAUT / 2 / self.champ_zoom; dl = dh * aspect; ech = CH_ECHELLE
        self._vue_champ = (cx, cz, dl, dh)
        M = np.zeros((4, 4)); M[0, 0] = 1 / dl; M[0, 3] = -cx / dl; M[1, 2] = -1 / dh; M[1, 3] = cz / dh; M[2, 1] = -1 / 100.0; M[3, 3] = 1.0
        return M, np.array([1.0, 0.0, 0.0]), 24 / CH_PX * ech, 32 / CH_PX * ech

    def _k_auto(self):
        """Echelle pixel perfect de depart : x1, x2, x4 ou x8, la plus proche (a l'echelle logarithmique) de la hauteur voulue (CH_VUE_HAUT tuiles x zoom)."""
        ideal = max(1e-3, self.height / (CH_VUE_HAUT * CH_PX) * self.champ_zoom)
        return min(PP_ECHELLES, key=lambda k: abs(math.log(k / ideal)))

    def _k_pp(self):
        """Pixel perfect : pixels d'ecran par pixel de la carte (x1, x2, x4 ou x8 ; menu Echap ou molette) ; automatique : suit la taille de la fenetre."""
        return self._k_auto() if self.pp_auto else self.pp_k

    def _maj_champ(self, e):
        """(Re)construit la grille de tuiles quand le moteur en envoie une autre ; l'atlas est la texture Unity `field`."""
        ch = e.champ; mo = e.monde
        if mo is not None and self._vue_champ is not None:      # carte entiere lue dans le moteur : on dessine toute la zone visible (le moteur n'en envoie que 25 colonnes)
            cx, cz, dl, dh = self._vue_champ
            x0 = 4 * int(math.floor((cx - dl - 1) / 4)); x1 = x0 + 4 * int(math.ceil((2 * dl + 7) / 4))                  # bornes sur des multiples de 4 et largeur constante : le maillage garde la meme taille
            y0 = 4 * int(math.floor((cz - dh - 1) / 4)); y1 = y0 + 4 * int(math.ceil((2 * dh + 7) / 4))                  # a la marche et ses sommets sont remplaces sur place (pas de reallocation : pas d'a-coup)
            x0, x1 = max(x0, int(cx) - 120), min(x1, int(cx) + 120); y0, y1 = max(y0, int(cz) - 80), min(y1, int(cz) + 80)
            cols = x1 - x0
            t = mo['ids'][(np.arange(y0, y1) % mo['h'])[:, None], (np.arange(x0, x1) % mo['l'])[None, :]].astype(np.int32).ravel()
            ch = {'x0': x0, 'y0': y0, 'cols': cols}
        else:
            t = np.array(ch['tuiles'], np.int32)
        cle = (ch['x0'], ch['y0'], ch['cols'], hash(t.tobytes()), self.mode == MODE_PP)
        if cle == self.champ_cle: self._rafraichir_motifs(); return
        self.champ_cle = cle
        if self.champ_tex is None:
            arr = self.donnees.texture('field')
            if arr is None: return
            t4 = arr[:CH_ATLAS * 16, :CH_ATLAS * 16].reshape(CH_ATLAS, 16, CH_ATLAS, 16, 4).transpose(0, 2, 1, 3, 4)       # (ligne, colonne, y, x, canal) : une tuile de 16 x 16 par case
            t4 = np.pad(t4, ((0, 0), (0, 0), (CH_GOUT, CH_GOUT), (CH_GOUT, CH_GOUT), (0, 0)), mode='edge')
            self.champ_tex = self._tex(np.ascontiguousarray(t4.transpose(0, 2, 1, 3, 4).reshape(CH_ATLAS * CH_CASE, CH_ATLAS * CH_CASE, 4)), False)      # atlas des tuiles, avec gouttieres
            self.champ_tex_ico = self._tex(arr, False)                                                  # atlas d'origine : les icones de lieux y sont des rectangles quelconques
            self.champ_nearest = None
        cols = ch['cols']; lignes = len(t) // cols
        g = t[:lignes * cols].reshape(lignes, cols)
        self.champ_g = g; self.champ_pat = CH_MOTIF_NUM[np.searchsorted(CH_MOTIF_FIN, g, side='right')]; self.champ_acc_vu = tuple(self.motif_acc)
        if self.champ_base is None or self.champ_base[0] != (cols, lignes):        # sommets de la grille a l'origine (NO, NE, SE, SO, deux triangles par tuile), decales ensuite de (x0, y0)
            X, Z = np.meshgrid(np.arange(cols), np.arange(lignes)); O = np.zeros_like(X)
            P = np.stack([np.stack([X, O, Z], -1), np.stack([X + 1, O, Z], -1), np.stack([X + 1, O, Z + 1], -1), np.stack([X, O, Z + 1], -1)], 2).astype(np.float32)   # (l, c, 4, 3)
            self.champ_base = ((cols, lignes), P[:, :, [0, 1, 2, 0, 2, 3], :].reshape(-1, 3))
        pos = (self.champ_base[1] + np.array([ch['x0'], 0, ch['y0']], np.float32)).ravel(); uv = self._uv_tuiles(g + self.motif_acc[self.champ_pat])
        n = len(pos) // 3
        if self.champ_vl is not None and self.champ_vl.count == n:                  # meme taille : remplacement sur place
            self.champ_vl.position[:] = pos; self.champ_vl.tex_coords[:] = uv
        else:
            if self.champ_vl is not None: self.champ_vl.delete()
            self.champ_vl = self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', pos), tex_coords=('f', uv.ravel()), colors=('f', np.ones(n * 4, np.float32)))

    def _uv_tuiles(self, g):
        """Coordonnees de texture (6 sommets par tuile, a plat) de la grille de numeros de tuile `g` ; les tuiles sont stockees tete en bas dans l'atlas."""
        aw = float(CH_ATLAS * CH_CASE)                                                  # atlas copie avec une gouttiere de CH_GOUT pixels autour de chaque tuile
        u0 = ((g % CH_ATLAS) * CH_CASE + CH_GOUT) / aw; v0 = ((g // CH_ATLAS) * CH_CASE + CH_GOUT) / aw; d = 16.0 / aw
        U = np.stack([np.stack([u0, v0], -1), np.stack([u0 + d, v0], -1), np.stack([u0 + d, v0 + d], -1), np.stack([u0, v0 + d], -1)], 2).astype(np.float32)      # (l, c, 4, 2)
        return U[:, :, [0, 1, 2, 0, 2, 3], :].reshape(-1, 2).ravel()

    def _avancer_motifs(self):
        """Une image du jeu sur la carte du monde (NativeManager.Update -> Field.UpdatePattern) : toutes les 17 images, le decalage de chaque motif avance d'un pas, puis retombe a 0 a sa limite."""
        self.motif_n += 1
        if self.motif_n < CH_MOTIF_PERIODE: return
        self.motif_n = 0
        for i in range(1, len(CH_MOTIF_PAS)):
            v = int(self.motif_acc[i]) + CH_MOTIF_PAS[i]
            self.motif_acc[i] = v if v < CH_MOTIF_LIM[i] else 0

    def _rafraichir_motifs(self):
        """Met a jour sur place les coordonnees de texture des tuiles animees quand un motif a change de pas."""
        acc = tuple(self.motif_acc)
        if acc == self.champ_acc_vu or self.champ_vl is None or self.champ_pat is None: return
        self.champ_acc_vu = acc
        if self.champ_pat.any(): self.champ_vl.tex_coords[:] = self._uv_tuiles(self.champ_g + self.motif_acc[self.champ_pat])

    def _tracer_champ(self, e):
        if self.champ_vl is None or self.champ_tex is None: return
        nearest = self.mode == MODE_PP or not self.lissage          # pixel perfect (echelle entiere) ou lissage coupe (F3) : plus proche voisin ; sinon pixels nets aux frontieres adoucies (comme les sprites d'origine)
        if self.champ_nearest != nearest:
            self.champ_nearest = nearest
            for t in (self.champ_tex, self.champ_tex_ico):
                gl.glBindTexture(t.target, t.id)
                gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST if nearest else gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST if nearest else gl.GL_LINEAR)
        net = 0.0 if nearest else 1.0
        self.prog['cutoff'] = 0.05; self.prog['net'] = net; self.prog['tsize'] = (float(CH_ATLAS * CH_CASE),) * 2
        self._tracer(self.champ_tex, self.champ_vl)
        self.prog['tsize'] = (1024.0, 1024.0)
        q, uv, col = [], [], []
        for s in e.symboles.values():                     # icones de lieux : posees a plat (le heros se tient au milieu du bord bas)
            r = CH_ICONES.get(s['genre'])
            if r is None or not s['vis']: continue
            ox, bas, w, h = r
            x0, z0 = (round(s['x']) if self.mode == MODE_PP else s['x']) / CH_PX, (round(s['y']) if self.mode == MODE_PP else s['y']) / CH_PX; x1, z1 = x0 + w / CH_PX, z0 + h / CH_PX       # a plat sur la carte, comme les tuiles (dessin vu de dessus)
            q += [(x0, 0.02, z0), (x1, 0.02, z0), (x1, 0.02, z1), (x0, 0.02, z0), (x1, 0.02, z1), (x0, 0.02, z1)]
            u0, u1, v1, v0 = ox / 1024.0, (ox + w) / 1024.0, 1 - (bas - h) / 1024.0, 1 - bas / 1024.0
            uv += [(u0, v0), (u1, v0), (u1, v1), (u0, v0), (u1, v1), (u0, v1)]       # tete en bas dans l'atlas, comme les tuiles : le haut de la carte = le bas de l'image
            col += [(1.0, 1.0, 1.0, float(s['alpha']))] * 6
        if q:
            n = len(q); pos = np.array(q, np.float32).ravel(); tc = np.array(uv, np.float32).ravel(); cc = np.array(col, np.float32).ravel()
            if self.champ_ico is None or self.champ_ico[0] != n:
                if self.champ_ico is not None: self.champ_ico[1].delete()
                self.champ_ico = (n, self.prog.vertex_list(n, gl.GL_TRIANGLES, position=('f', pos), tex_coords=('f', tc), colors=('f', cc)))
            else:
                v = self.champ_ico[1]; v.position[:] = pos; v.tex_coords[:] = tc; v.colors[:] = cc
            self._tracer(self.champ_tex_ico, self.champ_ico[1])
        self.prog['net'] = 0.0

    def _tracer(self, tex, vl):
        """Trace une vertex_list en ne liant le VAO et les tampons qu'une fois par image (beaucoup plus rapide que vl.draw)."""
        gl.glBindTexture(tex.target, tex.id)
        try:
            dom = vl.domain
            if dom is not self._dom_lie:
                dom.vao.bind()
                for buf, _ in dom.buffer_attributes: buf.commit()
                self._dom_lie = dom
            gl.glDrawArrays(gl.GL_TRIANGLES, vl.start, vl.count)
        except AttributeError:
            vl.draw(gl.GL_TRIANGLES)

    def on_mouse_scroll(self, x, y, sx, sy):
        """Carte du monde : molette = zoom (x1,1 par cran, de 0,4 a 4)."""
        if not self._pret: return
        if self.pause.ouvert: self.pause.molette(sy); return
        if self.moteur.etat.partie == MO.PARTIE_CHAMP and sy:
            if self.mode == MODE_PP:     # un cran = l'echelle suivante (x1, x2, x4, x8)
                k0 = self._k_pp(); self.pp_auto = False
                self.pp_k = PP_ECHELLES[min(len(PP_ECHELLES) - 1, max(0, PP_ECHELLES.index(k0) + (1 if sy > 0 else -1)))]; self.reg['echelle_pp'] = self.pp_k
            else: self.champ_zoom = min(4.0, max(0.4, self.champ_zoom * (1.1 ** sy))); self.reg['zoom_carte'] = round(self.champ_zoom, 2)

    def on_mouse_drag(self, x, y, dx, dy, boutons, modifiers):
        """Menu Echap : un curseur maintenu suit la souris."""
        if self._pret and self.pause.ouvert: self.pause.glisser(x, y)

    def on_text(self, texte):
        """Menu Echap : saisie d'une valeur au clavier."""
        if self._pret and self.pause.ouvert and self.pause.saisie is not None: self.pause.texte(texte)
        return pyglet.event.EVENT_HANDLED

    def _lancer_preparation(self, cache):
        """Preparation du cache dans un processus a part, a priorite basse (donnees.py en ligne de commande) : dans un thread, ses extractions ralentissaient le jeu. Repli : thread."""
        import subprocess
        try:
            kw = {'creationflags': 0x00004000} if os.name == 'nt' else {'preexec_fn': lambda: os.nice(10)}              # BELOW_NORMAL_PRIORITY_CLASS / nice
            self.prepa_proc = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'donnees.py'), self.moteur.apk_donnees, cache], stdin=subprocess.PIPE, **kw)
        except Exception as ex:
            print('Preparation du cache : processus a part impossible (%r), dans le jeu.' % (ex,), flush=True)
            threading.Thread(target=self.donnees.preparer, args=(self.prepa_arret,), daemon=True, name='preparation-cache').start()

    def on_close(self):
        self.reg.enregistrer(); self.son.fermer()
        p = getattr(self, 'prepa_proc', None)
        if p is not None:
            try: p.stdin.close()
            except Exception: pass
        super().on_close()

    def on_key_press(self, symbol, modifiers):
        """Seules touches fixes : Echap (menu) et F1 (infos). Les touches de jeu sont celles du menu Touches (pad) ; le menu ouvert recupere toutes les touches."""
        K = pyglet.window.key
        if not self._pret: return pyglet.event.EVENT_HANDLED
        if self.pause.ouvert: self.pause.touche(symbol, modifiers); return pyglet.event.EVENT_HANDLED
        if symbol == K.ESCAPE: self.pause.ouvrir(); return pyglet.event.EVENT_HANDLED
        if symbol == K.F1: self.aide = not self.aide; self.reg['infos'] = self.aide; return pyglet.event.EVENT_HANDLED
        n = self._num_etat(symbol)
        if n is not None:                                                  # raccourcis des etats : chiffre = enregistrer, Ctrl + chiffre = charger
            if modifiers & K.MOD_CTRL or self.touches[K.LCTRL] or self.touches[K.RCTRL]:
                self.combo[1] = True
                if self.infos_etat(n):
                    try: self.charger_etat(n); self.toast('État %d chargé' % n)
                    except Exception as ex: self.toast('Chargement impossible : %r' % (ex,))
                else: self.toast('État %d vide' % n)
            else: self.sauve_rapide = n
            return pyglet.event.EVENT_HANDLED
        if symbol in (K.LCTRL, K.RCTRL, K.LSHIFT, K.RSHIFT):               # Maj + Ctrl (sans chiffre) : annule le dernier chargement, au relachement
            ctrl = symbol in (K.LCTRL, K.RCTRL) or self.touches[K.LCTRL] or self.touches[K.RCTRL]; maj = symbol in (K.LSHIFT, K.RSHIFT) or self.touches[K.LSHIFT] or self.touches[K.RSHIFT]
            if ctrl and maj: self.combo = [True, False]
        return pyglet.event.EVENT_HANDLED

    def on_key_release(self, symbol, modifiers):
        K = pyglet.window.key
        if symbol in (K.LCTRL, K.RCTRL, K.LSHIFT, K.RSHIFT) and self.combo[0]:
            declenche = not self.combo[1]; self.combo = [False, False]
            if declenche and self._pret and not self.pause.ouvert: self.annuler_chargement()

    @staticmethod
    def _num_etat(symbol):
        K = pyglet.window.key
        chiffres = {K._1: 1, K._2: 2, K._3: 3, K._4: 4, K._5: 5, K._6: 6, K._7: 7, K._8: 8, K._9: 9, K._0: 10,
                    K.NUM_1: 1, K.NUM_2: 2, K.NUM_3: 3, K.NUM_4: 4, K.NUM_5: 5, K.NUM_6: 6, K.NUM_7: 7, K.NUM_8: 8, K.NUM_9: 9, K.NUM_0: 10}
        return chiffres.get(symbol)

    # ---- reglages appliques depuis le menu Echap
    def regler_mode(self, m): self.mode = int(m)

    def regler_echelle_pp(self, k):
        self.pp_auto = not k
        if k: self.pp_k = int(k)

    def regler_lissage(self, oui):
        self.lissage = bool(oui)
        for t in self.tex_gl.values(): self._filtrer(t, self.lissage)
        for r in self.decor_hd.values():
            for t in r.values(): self._filtrer(t, self.lissage)

    def regler_zoom(self, z):
        self.champ_zoom = float(z); self.pp_auto = True; self.reg['echelle_pp'] = 0         # le curseur reprend la main sur l'echelle pixel perfect (sinon il ne changeait plus rien apres un coup de molette)

    def regler_angle(self, a): self.angle_cam = float(a)

    def resolutions(self):
        """Tailles proposees (16/9, 720p a 4K) ; la taille actuelle s'y ajoute si elle est libre ; triees par largeur puis hauteur."""
        liste = list(RESOLUTIONS); cur = self.resolution_courante()
        if cur not in liste: liste.append(cur)
        return sorted(liste)                # par largeur, puis par hauteur

    def resolution_courante(self): return (int(self.width), int(self.height))

    def regler_resolution(self, v):
        """Fenetre : change la taille ; plein ecran : choisit le mode d'affichage correspondant s'il existe."""
        w, h = int(v[0]), int(v[1])
        if self.est_plein:
            try:
                modes = [m for m in self.screen.get_modes() if (m.width, m.height) == (w, h)]
                if modes: self.set_fullscreen(True, screen=self.screen, mode=max(modes, key=lambda m: m.rate))
            except Exception as ex: print('resolution plein ecran impossible :', ex, flush=True)
        else:
            self.taille_fenetre = (w, h); self.set_size(w, h)
    def regler_infos(self, oui): self.aide = bool(oui)

    def regler_plein_ecran(self, oui):
        oui = bool(oui)
        if oui == self.est_plein: return
        if oui: self.taille_fenetre = (self.width, self.height); self.set_fullscreen(True)
        else: self.set_fullscreen(False, width=self.taille_fenetre[0], height=self.taille_fenetre[1])
        self.est_plein = oui

    def regler_son(self, oui):
        if bool(oui) != self.son.actif:
            self.son.basculer()
            if self.son.actif and self.moteur.etat.musique is not None: self.son.jouer_bgm(self.moteur.etat.musique)

    def regler_vol_musique(self, v): self.son.regler_volumes(v, None)
    def regler_vol_bruitages(self, v): self.son.regler_volumes(None, v)

    def pause_jeu(self, oui):
        """Menu Echap ouvert (oui) ou ferme : le moteur et le son s'arretent ; a la reprise, les touches deja tenues ne comptent pas comme un nouvel appui."""
        self.son.mettre_en_pause(oui)
        self.acc = 0.0; self.t_boucle = None
        if not oui:
            self.pad_prec = self.pad(); self.act_prec = {a: self._tenue(a) for a in ACT_FRONTS}; self.rep = {}; self.survol = None; self.appui = None

    def quitter(self):
        self.close(); pyglet.app.exit()

    # ---- etats instantanes (savestates)
    def chemin_etat(self, n): return os.path.join(self.args.saves_ecriture, 'etats', 'etat_%02d.dqs' % n)

    def infos_etat(self, n):
        """(infos, miniature PNG) de l'etat n, ou None."""
        return ET.infos(self.chemin_etat(n))

    def _lieu(self):
        e = self.moteur.etat
        return 'Carte du monde' if e.partie == MO.PARTIE_CHAMP else ('Combat' if e.partie == MO.PARTIE_COMBAT else (e.carte or '?'))

    def _etat_complet(self):
        """Etat instantane du moteur + de la visionneuse (objets animes de la carte compris)."""
        viewer = {'objets_etat': self.objets.etat if self.objets is not None else None, 'objets_auto': self.objets.auto if self.objets is not None else None,
                  'palettes': self.palettes.etat() if self.palettes is not None else None, 'carte_nom': self.carte_nom, 'motif_n': self.motif_n, 'motif_acc': self.motif_acc.copy(), 'musique': self.son.etat_bgm()}
        return ET.instantane(self.moteur, viewer)

    def sauver_etat(self, n, miniature_png=b''):
        """Enregistre l'etat du jeu dans l'emplacement n."""
        d = self._etat_complet()
        ET.ecrire(self.chemin_etat(n), d, {'lieu': self._lieu(), 'carte': self.moteur.etat.carte, 'partie': self.moteur.etat.partie, 'images': self.moteur.images}, miniature_png)

    def charger_etat(self, n):
        """Recharge l'emplacement n ; l'etat d'avant le chargement est gardé en memoire (annuler_chargement)."""
        d = ET.lire(self.chemin_etat(n))
        try: self.etat_annul = self._etat_complet()
        except Exception as ex: self.etat_annul = None; print('etat avant chargement non garde :', ex, flush=True)
        self._appliquer_etat(d)

    def annuler_chargement(self):
        """Revient a l'etat juste avant le dernier chargement (un deuxieme appel refait le chargement)."""
        if self.etat_annul is None: self.toast('Aucun chargement à annuler'); return False
        actuel = self._etat_complet(); d, self.etat_annul = self.etat_annul, actuel
        self._appliquer_etat(d); self.toast('Chargement annulé')
        return True

    def _appliquer_etat(self, d):
        """Remet le moteur dans l'etat `d`, puis tout ce que la fenetre en a deduit (fenetres de menu, carte, objets animes, musique)."""
        mo = self.moteur
        viewer = ET.appliquer(mo, d)
        self.ui_g_reset()
        self.carte_nom = None; self.champ_cle = None; self.prec = None; self.canevas_cle = None; self.msg_cle = None
        self.pad_prec = 0; self.rep = {}; self.menu_relacher = None; self.survol = None; self.appui = None; self.cur_local = {}; self.effet_ref = None; self.effet_tex_prete = False
        self.acc = 0.0; self.t_boucle = None
        self.n_combat = 0 if mo.etat.partie != MO.PARTIE_COMBAT else self.n_combat
        e = mo.etat
        if e.carte and e.partie != MO.PARTIE_CHAMP and not e.carte.startswith('btl_'):
            self._charger_carte(e.carte)
        elif e.carte and e.partie == MO.PARTIE_COMBAT: self._charger_carte(e.carte)
        if viewer and 'motif_acc' in viewer: self.motif_n = viewer['motif_n']; self.motif_acc[:] = viewer['motif_acc']; self.champ_acc_vu = None          # eau animee de la carte du monde
        if viewer and viewer.get('objets_etat') and self.objets is not None:
            self.objets.reinit(); self.objets.restaurer(viewer['objets_etat'], viewer.get('objets_auto'))
            for tex, vl, key in self.carte_vl:
                vl.position[:] = self.objets.cur[key].ravel(); vl.tex_coords[:] = self.objets.uv(key).ravel(); vl.colors[:] = self.objets.col(key).ravel()
            self.objets.sale = set(); self.objets.sale_uv = set(); self.objets.sale_col = set()
        if viewer and viewer.get('palettes') and self.palettes is not None: self.palettes.regler(viewer['palettes'])
        for sp in list(e.sprites.values()): self._feuille(sp['id'] - 4096 if (e.partie == MO.PARTIE_CHAMP and sp['id'] >= 4096) else sp['id'], self.mode)
        self.son.restaurer_bgm(viewer.get('musique') if viewer else None, e.musique)         # la musique repart du moment enregistre
        e.sons = []

    def toast(self, texte, duree=1.8):
        """Petit message en haut de l'ecran (sauvegardes rapides...)."""
        self.toasts = [(texte, time.time() + duree)]

    def ui_g_reset(self):
        """Refait les fenetres de menu d'origine d'apres la memoire de l'interface (apres le chargement d'un etat)."""
        if self.ui_g is None: return
        self.ui_g.f.clear(); self.moteur.ui.obs = self.ui_g; self.ui_g.rejouer(self.moteur.ui)

    def _copier_miniature(self):
        """Copie l'image du jeu (sans le menu) dans une texture, sur la carte graphique seulement : le menu s'ouvre sans attendre une relecture ; le PNG n'est fait qu'a l'enregistrement d'un etat."""
        try:
            w, h = self.get_framebuffer_size()
            t = pyglet.image.Texture.create(w, h, internalformat=gl.GL_RGBA8)
            gl.glBindTexture(t.target, t.id); gl.glCopyTexSubImage2D(t.target, 0, 0, 0, 0, 0, w, h)
            return t
        except Exception as ex:
            print('miniature impossible :', ex, flush=True); return None

    def _png_miniature(self, t):
        """Texture de _copier_miniature -> PNG reduit (miniature des etats)."""
        if t is None: return b''
        try:
            import io
            from PIL import Image
            img = t.get_image_data()
            a = np.frombuffer(img.get_data('RGB', img.width * 3), np.uint8).reshape(img.height, img.width, 3)[::-1]
            im = Image.fromarray(np.ascontiguousarray(a)); im.thumbnail((320, 180)); b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()
        except Exception as ex:
            print('miniature impossible :', ex, flush=True); return b''

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
        fov_h = math.radians((e.cam_fov if e.cam_fov is not None else FOV_VILLE_DEF) * 4.0 / 3.0)
        th_v = math.tan(fov_h / 2) / ASPECT_PORTRAIT                      # tangente du demi-champ vertical de l'original
        if not e.cam_libre:       # zoom commun : le heros (le point vise) prend HEROS_FRAC de la hauteur de la fenetre, quelle que soit la distance ou le fov de la camera de la ville, de la grotte ou de la tour
            prof = float(np.linalg.norm(cib - pos)) - DIST_ADJ_VILLE
            if prof > 1.0: th_v = SPRITE_H * SPRITE_ECHELLE / HEROS_FRAC / (2.0 * prof)
        if self.bornes_x is not None:
            # cadrage 16/9 : le moteur centre la camera pour un ecran portrait ; en large on garde le bord de la carte hors champ
            fv = cib - pos; fv[1] = 0; fv /= np.linalg.norm(fv) or 1
            if abs(fv[2]) > 0.95:
                W = np.linalg.norm(cib - pos) * th_v * aspect * 0.85
                lo, hi = self.bornes_x[0] + W, self.bornes_x[1] - W
                cx = (self.bornes_x[0] + self.bornes_x[1]) / 2 if lo >= hi else min(max(cib[0], lo), hi)
                d = cx - cib[0]; pos[0] += d; cib[0] += d
        if self.angle_cam and not (e.cam_libre and e.cam_rot is not None):       # option : la camera tourne autour de la cible, en hauteur (0 = comme le jeu)
            dist = float(np.linalg.norm(cib - pos)); f0 = (cib - pos) / (dist or 1.0)
            la = math.atan2(f0[0], f0[2]); tg = min(math.radians(85.0), max(math.radians(5.0), math.asin(-f0[1]) + math.radians(self.angle_cam)))
            pos = cib - np.array([math.sin(la) * math.cos(tg), -math.sin(tg), math.cos(la) * math.cos(tg)]) * dist
        if e.cam_libre and e.cam_rot is not None:                         # camera libre (paquet 11, bit 7) : position + angles, comme en combat
            R = self._rot_camera(e); fw = R @ np.array([0.0, 0.0, 1.0]); haut = R @ np.array([0.0, 1.0, 0.0])
        else:
            fw = cib - pos; fw /= np.linalg.norm(fw)
            lacet = math.atan2(fw[0], fw[2]); tang = math.asin(-fw[1]) - math.radians(e.cam_bas if e.cam_bas is not None else BAS_DEF)
            fw = np.array([math.sin(lacet) * math.cos(tang), -math.sin(tang), math.cos(lacet) * math.cos(tang)]); haut = np.array([0.0, 1.0, 0.0])
            pos = pos + fw * DIST_ADJ_VILLE
        M, droite = matrice(pos, pos + fw * 10, math.degrees(2 * math.atan(th_v)), aspect, n=e.cam_near or VILLE_NEAR, f=e.cam_far or VILLE_FAR, haut=haut)
        if e.cam_yoff:
            Ty = np.eye(4); Ty[1, 3] = e.cam_yoff; M = Ty @ M              # SceneCamera.s_yOffset
        return M, (droite, np.cross(fw, droite), fw)

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

    def _calcul_hd_monstre(self, arr, mid, cid, algo):
        """(tache de fond) texture HD d'un monstre, lue dans le cache disque s'il existe. Plafonnee a 4096 px de cote (moins de passes si besoin)."""
        f = os.path.join(self.args.cache, 'hd_%s_v%d_m%d.npy' % (cid, HD.VERSION, mid))
        try:
            if os.path.exists(f): return np.load(f)
        except Exception: pass
        h, w = arr.shape[:2]; passes = 3
        while passes > 0 and max(h, w) * 2 ** passes > 4096: passes -= 1
        if passes == 0: return arr
        a = algo(arr) if passes == 3 else HD.agrandir_epx(arr, passes)
        try: np.save(f, a)
        except Exception: pass
        return a

    def _texture_monstre(self, mid):
        """Texture d'un monstre pour le mode de sprites choisi (F2) : celle d'origine (pixels nets) ou agrandie par l'algorithme HD (calcul en tache de fond, l'original sert en attendant)."""
        orig = self.cb_tex.get((mid, 0))
        if orig is None:
            try: arr = self.donnees.texture('m%03d' % mid)
            except Exception as ex:
                print('texture de monstre introuvable :', mid, ex, flush=True); arr = np.zeros((16, 16, 4), np.uint8)
            t = self._tex(arr, False, 0)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            orig = self.cb_tex[(mid, 0)] = dict(t=t, tw=arr.shape[1], th=arr.shape[0], hd=False, arr=arr)
        if self.mode in (0, MODE_PP): return orig
        cle = (mid, self.mode); jc = ('m',) + cle
        if cle in self.cb_tex: return self.cb_tex[cle]
        fut = self.hd_jobs.get(jc)
        if fut is None:
            _nom, cid, algo = HD.MODES[self.mode]
            self.hd_jobs[jc] = self.pool.submit(self._calcul_hd_monstre, orig['arr'], mid, cid, algo)
            return orig
        if not fut.done(): return orig
        del self.hd_jobs[jc]
        try: a = fut.result()
        except Exception as ex:
            print('lissage HD impossible (monstre %d) : %s' % (mid, ex), flush=True); self.cb_tex[cle] = orig; return orig
        self.cb_tex[cle] = dict(t=self._tex(a, False, HD_NIVEAUX), tw=a.shape[1], th=a.shape[0], hd=a is not orig['arr'])
        return self.cb_tex[cle]

    def _maillages_combat(self, e):
        """Liste (texture, vertex_list, ...) des maillages de monstres de l'image courante, dans l'ordre de dessin d'Unity :
        shaders DssaMonster* = fusion alpha, pas d'ecriture de profondeur, pas de masquage des faces -> parties dessinees dans l'ordre des paquets ;
        entre monstres : file de rendu du shader (Transparent+150, +200...) puis du plus loin au plus proche."""
        out = []
        R = self._rot_camera(e); Rb = R @ rot_unity(0.0, 180.0, 0.0)            # MeshChara.SetBillboard : rotation de la camera x SceneCamera.s_yReverse (Euler(0, 180, 0))
        cam = np.array(e.cam_pos, float); fw = R @ np.array([0.0, 0.0, 1.0])
        for slot, mm in sorted(e.maillages.items()):
            if slot not in e.maillages_vus: continue                # mode immediat : pas de paquet cette image = pas dessine
            mid = e.modeles.get(slot)
            if mid is None: continue
            st = e.mesh_etat.get(slot) or {'shader': 1, 'vis': True, 'col': (1.0, 1.0, 1.0), 'off': (0.0, 0.0)}
            if not st['vis']: continue
            ft = self._texture_monstre(mid); t, tw, th = ft['t'], ft['tw'], ft['th']
            V = np.array(mm['v'], np.float32); ix = np.array(mm['idx'], np.int64)
            if self.cb_ordre and len(ix) % 6 == 0: ix = ix.reshape(-1, 6)[::-1].ravel()          # (essai) quadrilateres en ordre inverse
            P = V[ix]
            xyz = (P[:, 2:5] @ Rb.T.astype(np.float32)) * np.array([-1 if self.cb_mx else 1, 1, 1], np.float32) + np.array(mm['pos'], np.float32)
            uv = np.c_[P[:, 0] + st['off'][0], 1.0 + P[:, 1] + st['off'][1]].astype(np.float32)
            cq = np.array(mm.get('col') or [255], np.float32) / 255.0   # un octet par quad = opacite de la partie (ombres, apparitions en fondu, clignotements)
            alpha = cq[np.minimum(ix // 4, len(cq) - 1)]
            coul = np.c_[np.ones((len(ix), 3), np.float32) * np.array(st['col'], np.float32), alpha].astype(np.float32)           # Material.color (paquet 25) x couleur de sommet
            n = len(xyz)
            vl = self.cb_vl.get(slot)
            if vl is None or vl[0] < n:                                  # capacite FIXE : recreer une liste quand le nombre de sommets change corrompt les autres monstres (glitchs/clignotements)
                if vl is not None: vl[1].delete()
                cap = max(CB_CAP, n)
                vl = self.cb_vl[slot] = (cap, self.prog.vertex_list(cap, gl.GL_TRIANGLES, position=('f', np.zeros(cap * 3, np.float32)), tex_coords=('f', np.zeros(cap * 2, np.float32)), colors=('f', np.zeros(cap * 4, np.float32))))
            cap = vl[0]
            pp = np.zeros((cap, 3), np.float32); pp[:n] = xyz                  # sommets inutilises : triangles degeneres (au point 0), jamais dessines
            pu = np.zeros((cap, 2), np.float32); pu[:n] = uv
            pc = np.zeros((cap, 4), np.float32); pc[:n] = coul
            vl[1].position[:] = pp.ravel(); vl[1].tex_coords[:] = pu.ravel(); vl[1].colors[:] = pc.ravel()
            queue = {0: 2100, 1: 2150, 2: 2200, 3: 3850}.get(st['shader'], 2150)       # file de rendu des shaders Custom/DssaChara, DssaMonster0, DssaMonster1, DssaCharaTransparent
            centre = (xyz.min(0) + xyz.max(0)) / 2
            out.append(((queue, -float((centre - cam) @ fw)), t, tw, th, vl[1], st['shader'], ft['hd']))
        out.sort(key=lambda o: o[0])
        return [o[1:] for o in out]

    def _charger_carte(self, nom):
        for vl in self.carte_vl: vl[1].delete()
        self.carte_vl = []; self.carte_pos = {}; self.plages = {}; self.noms = {}; self.objets = None; self.palettes = None; self.pam_gl = {}
        src = (os.environ.get('DQ_DECOR') or nom) if nom.startswith('btl_') else nom       # DQ_DECOR : (test) force un autre decor de combat
        try:
            c = self.donnees.carte(src)
        except Exception as ex:
            print('carte non chargee :', ex, flush=True); self.carte_nom = nom; return
        self.carte_src = src; self.decor_arr = {k: v for k, v in c['textures'].items() if k in c['groupes']}       # textures du decor (agrandies selon le mode de F2, voir _decor_tex)
        self.objets = OC.ObjetsCarte(c)                                   # portes, jarres, tonneaux... : positions affichees (variantes cachees au depart) ; eau, lampes... animees en continu
        self.palettes = OC.PalettesCarte(c)                               # surfaces dont la texture change d'image en image (eau qui scintille, marais...)
        for key, (pos, uv, col) in c['groupes'].items():
            if key not in c['textures']: continue
            if (src, key) not in self.tex_gl:
                self.tex_gl[(src, key)] = t = self._tex(c['textures'][key], True, 99); self._filtrer(t, self.lissage)
            vl = self.prog.vertex_list(len(pos), gl.GL_TRIANGLES, position=('f', self.objets.cur[key].ravel()), tex_coords=('f', self.objets.uv(key).ravel()), colors=('f', self.objets.col(key).ravel()))
            self.carte_vl.append((self.tex_gl[(src, key)], vl, key)); self.carte_pos[key] = pos.copy()
        for key, dd in self.palettes.defs.items():                         # images de chaque animation de palette
            if key not in c['groupes']: continue
            self.pam_gl[key] = []
            for k, a in enumerate(dd['images']):
                if (src, key, k) not in self.tex_gl:
                    self.tex_gl[(src, key, k)] = t = self._tex(a, True, 99); self._filtrer(t, self.lissage)
                self.pam_gl[key].append(self.tex_gl[(src, key, k)])
        self.objets.sale = set(); self.objets.sale_uv = set(); self.objets.sale_col = set()
        self.plages = c.get('plages', {}); self.noms = c.get('noms', {})
        allp = np.concatenate([g[0] for g in c['groupes'].values()]) if c['groupes'] else np.zeros((1, 3), np.float32)
        self.bornes_x = (float(np.percentile(allp[:, 0], 0.5)), float(np.percentile(allp[:, 0], 99.5)))
        self.carte_nom = nom
        self.fond_decor = self._fond_combat(c) if nom.startswith('btl_') else None
        print('carte %s : %d groupes' % (nom, len(self.carte_vl)), flush=True)

    def _calcul_hd_decor(self, arrs, algo):
        """(tache de fond) textures de decor agrandies par l'algorithme HD du mode de F2 (x8, plafonne a 4096 px de cote). Le bord est repete en boucle avant l'agrandissement : les textures se raccordent."""
        out = {}
        for key, arr in arrs.items():
            h, w = arr.shape[:2]; passes = 3
            while passes > 0 and max(h, w) * 2 ** passes > 4096: passes -= 1
            if passes == 0: out[key] = arr; continue
            a = np.pad(arr, ((2, 2), (2, 2), (0, 0)), mode='wrap')
            r = algo(a) if passes == 3 else HD.agrandir_epx(a, passes)
            f = r.shape[0] // a.shape[0]
            out[key] = np.ascontiguousarray(r[2 * f:r.shape[0] - 2 * f, 2 * f:r.shape[1] - 2 * f])
        return out

    def _decor_hd(self):
        """Textures GL agrandies du decor courant pour le mode de F2 ; None tant que le calcul en tache de fond n'est pas fini (le decor d'origine sert en attendant)."""
        cle = (self.carte_src, self.mode); r = self.decor_hd.get(cle)
        if r is not None: return r
        jc = ('d',) + cle; fut = self.hd_jobs.get(jc)
        if fut is None:
            self.hd_jobs[jc] = self.pool.submit(self._calcul_hd_decor, dict(self.decor_arr), HD.MODES[self.mode][2]); return None
        if not fut.done(): return None
        del self.hd_jobs[jc]
        try: arrs = fut.result()
        except Exception as ex:
            print('lissage HD du decor impossible (%s) : %s' % (self.carte_src, ex), flush=True); arrs = {}
        r = self.decor_hd[cle] = {}
        for k, a in arrs.items():
            r[k] = t = self._tex(a, True, 99); self._filtrer(t, self.lissage)
        while len(self.decor_hd) > 8:                                  # on ne garde que les derniers decors agrandis (memoire de la carte graphique)
            for t in self.decor_hd.pop(next(iter(self.decor_hd))).values(): t.delete()
        return r

    def _tracer_decor(self, net=False):
        """Decor de la ville ou du combat. Les textures du decor sont des peintures de 8 a 256 px etirees en 3D : en « Originaux » et en pixel perfect (reglages pour les SPRITES) il garde le rendu d'origine,
        lisse (mipmaps + anisotrope, F3 = agrandissement lineaire ou plus proche voisin) ; les modes agrandis (EPX, regions lissees, bicubique) lui appliquent l'algorithme HD choisi."""
        r = self._decor_hd() if self.mode not in (0, MODE_PP) else None
        net_o = 1.0 if (net and r is None and self.lissage and not os.environ.get('DQ_DECOR_FLOU')) else 0.0           # villes et donjons en « Originaux » / pixel perfect : texels nets, seule la frontiere entre deux texels est adoucie (comme les sprites) ; en combat, peintures etirees : lissage normal
        est_tr = lambda k: isinstance(k, tuple) and k[0] == 'tr'
        opaques = [x for x in self.carte_vl if not est_tr(x[2])]
        transp = sorted((x for x in self.carte_vl if est_tr(x[2])), key=lambda x: x[2][1])         # file de rendu 3000 + priorite (FldObject.set_priority)
        cutoff0 = self.prog['cutoff']
        for pas, liste in ((0, opaques), (1, transp)):
            if pas == 1 and liste:
                gl.glDepthMask(gl.GL_FALSE); gl.glDepthFunc(gl.GL_LEQUAL); self.prog['cutoff'] = 0.0      # Custom/fld_trans : Blend SrcAlpha OneMinusSrcAlpha, ZWrite Off, ZTest LEqual, pas de rejet
            for tex, vl, key in liste:
                pg = self.pam_gl.get(key)
                t = pg[self.palettes.image(key)] if pg else (r.get(key, tex) if r else tex)          # palette animee : image courante (sans agrandissement HD)
                self.prog['net'] = net_o if (r is None or key not in r) else 0.0
                self.prog['tsize'] = (float(t.width), float(t.height))
                self._tracer(t, vl)
            if pas == 1 and liste: gl.glDepthMask(gl.GL_TRUE); gl.glDepthFunc(gl.GL_LESS); self.prog['cutoff'] = cutoff0
        self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0)

    def _fond_combat(self, c):
        """Le moteur n'envoie pas de couleur de fond en combat, et le decor laisse un vide entre le bord du sol et le ciel :
        on prend la couleur moyenne (texture x couleur de sommet) du sol a la peripherie de l'arene, ciel exclu."""
        try:
            pts = []
            for iobj, nm in c.get('noms', {}).items():
                if 'sora' in nm.lower(): continue
                for key, deb, n in c['plages'].get(iobj, []):
                    pos, uv, col = c['groupes'][key]; tex = c['textures'].get(key)
                    if tex is None: continue
                    p, u, k = pos[deb:deb + n], uv[deb:deb + n], col[deb:deb + n]
                    h, w = tex.shape[:2]
                    px = tex[np.clip(((1 - u[:, 1]) * (h - 1)).astype(int) % h, 0, h - 1), np.clip((u[:, 0] * (w - 1)).astype(int) % w, 0, w - 1)]
                    rgb = px[:, :3] / 255.0 * k[:, :3]
                    ok = px[:, 3] > 128
                    pts.append(np.c_[np.hypot(p[:, 0], p[:, 2] - 3.0), p[:, 1], rgb][ok])
            a = np.concatenate(pts)
            sol = a[(a[:, 1] < 2.0) & (a[:, 0] >= np.percentile(a[:, 0], 60))]        # sol de la peripherie de l'arene
            if len(sol) < 20: sol = a[a[:, 0] >= np.percentile(a[:, 0], 85)]
            return tuple(float(x) for x in sol[:, 2:].mean(0))
        except Exception as ex:
            print('fond de combat non calcule :', ex, flush=True); return None

    def _ui_x_monstres(self, masque):
        """Abscisses (unites d'interface, colonne portrait 450 x 800) des monstres d'un masque : emplacement i = bit i (MeshChara) projete par la camera de combat."""
        M = getattr(self, '_M_combat', None); e = self.moteur.etat
        if M is None: return None
        ech = self.height / 800.0 * self.ui_k; cx = {'centre': self.width / 2, 'droite': self.width - 225 * ech, 'gauche': 225 * ech}.get(self.args.ui_pos, self.width / 2)
        xs = []
        for i in range(32):
            if not (masque >> i) & 1: continue
            mm = e.maillages.get(i)
            if not mm: continue
            P = np.array(list(mm['pos']) + [1.0]); c = M @ P
            if c[3] <= 0: continue
            xs.append((((c[0] / c[3]) * 0.5 + 0.5) * self.width - cx) / ech)
        return (min(xs), max(xs)) if xs else None

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
                        print('CANEVAS image %s lignes %s msg %s' % (self.moteur.images, g, self.moteur.ui.msg), flush=True)
            m = self.moteur.ui.msg; typ = m['type']
            if typ == 1 and a is not None and a[(np.arange(102, 164) + (int(m['y']) & 0x1ff)) % 512].max() > 40: typ = 4       # message de combat de 4 lignes (4 groupes de monstres) : cadre d'origine
            self.ui_msg.regler(typ, m['y'], m['feed'])
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

    def _copier_ecran(self):
        """Copie l'image qui vient d'etre dessinee dans une texture (la capture que l'effet de debut de combat brise en morceaux)."""
        w, h = self.get_framebuffer_size()
        if self.effet_tex is not None: self.effet_tex.delete()
        t = pyglet.image.Texture.create(w, h, internalformat=gl.GL_RGBA8)
        gl.glBindTexture(t.target, t.id)
        gl.glCopyTexSubImage2D(t.target, 0, 0, 0, 0, 0, w, h)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glGenerateMipmap(t.target)
        gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        self.effet_tex = t
        self.effet_sim = EC.EffetTuiles(self.width / max(1, self.height))
        n = self.effet_sim.rows * EC.COLS * 6
        if self.effet_vl is not None: self.effet_vl.delete()
        self.effet_vl = self.prog_effet.vertex_list(n, gl.GL_TRIANGLES, position=('f', self.effet_sim.positions().ravel().tolist()), tex_coords=('f', self.effet_sim.UV.ravel().tolist()), colors=('f', self.effet_sim.couleurs().ravel().tolist()))

    def _dessiner_effet(self, ef):
        """Effet de debut de combat : fond noir, morceaux de la capture qui tombent (voir effet_combat.py)."""
        sim = self.effet_sim
        while sim.images < ef['n'] and not sim.fini: sim.etape()
        gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear()
        gl.glViewport(0, 0, *self.get_framebuffer_size())
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        vl = self.effet_vl; vl.position[:] = sim.positions().ravel().tolist(); vl.colors[:] = sim.couleurs().ravel().tolist()
        self.prog_effet.use(); self.prog_effet['lum'] = float(sim.lum); self.prog_effet['flou'] = EFFET_FLOU
        gl.glActiveTexture(gl.GL_TEXTURE0); gl.glBindTexture(self.effet_tex.target, self.effet_tex.id)
        vl.draw(gl.GL_TRIANGLES)
        self.prog_effet.stop()

    def _dessiner_fondu(self):
        """Plan de fondu d'ecran (Fade.FadePlane) : derriere l'interface (messages, menus), devant la scene."""
        fd = self.moteur.etat.fondu
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

    def _saisie_menu(self, port, decl):
        """Touches -> menu actif, comme MenuPort.Send d'Unity : [1, numero de bouton, manette] (manette du jeu : bas 1, haut 2, droite 4, gauche 8, A 16, B 32).
        Menu a curseur du moteur (message 2 : colonnes x lignes, ex. Oui / Non) : les touches lui sont transmises, il deplace son curseur (messages 4) et valide ;
        gauche/droite sur une seule colonne = precedent/suivant. Menu tactile (boutons sans curseur du moteur) : curseur local deplace d'apres la position des boutons, A = toucher."""
        mo = self.moteur; f = mo.ui.f[port]
        dirs = ((MO.HAUT, 2), (MO.BAS, 1), (MO.GAUCHE, 8), (MO.DROITE, 4))
        fe = self.ui_g.f.get(port) if self.ui_g else None
        z = {b: ((x0 + x1) / 2, (z0 + z1) / 2) for b, pad, x0, z0, x1, z1, _ in (fe.boutons() if fe else []) if b >= 0 and pad & 0x10}
        if f.get('grille') or len(z) < 1:
            for bit, pad in dirs:
                if decl & bit:
                    if bit in (MO.GAUCHE, MO.DROITE) and (f.get('grille') or (1, 1, 1))[0] < 2: pad = 2 if bit == MO.GAUCHE else 1
                    mo.envoyer_menu(port, 1, -1, pad); self.menu_relacher = port; return
            if decl & MO.A: mo.envoyer_menu(port, 1, -1, 0x10); self.menu_relacher = port; self.son.jouer_se(SE_BOUTON)
            elif decl & MO.B: mo.envoyer_menu(port, 1, -1, 0x20); self.menu_relacher = port; self.son.jouer_se(SE_BOUTON)
            return
        cle = (port, f['ordre']); cur = self.cur_local.get(cle)
        if cur not in z:
            cur = self.cur_local[cle] = f['cur'] if f['cur'] in z else min(z, key=lambda b: (-round(z[b][1]), z[b][0]))       # depart : le bouton en haut a gauche
        for bit, _ in dirs:
            if decl & bit: cur = self.cur_local[cle] = self._voisin(z, cur, bit)
        if decl & MO.A: mo.envoyer_menu(port, 1, cur, 0x10); self.menu_relacher = port; self.son.jouer_se(SE_BOUTON)
        elif decl & MO.B: mo.envoyer_menu(port, 1, -1, 0x20); self.menu_relacher = port; self.son.jouer_se(SE_BOUTON)

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

    def _etiq(self, texte, taille, couleur=(255, 255, 255, 255)):
        k = (texte, round(taille, 1), couleur)
        l = self.etiq_menu.get(k)
        if l is None:
            if len(self.etiq_menu) > 400: self.etiq_menu.clear()
            l = self.etiq_menu[k] = pyglet.text.Label(texte, font_name=POLICES, font_size=taille, color=couleur, anchor_x='left', anchor_y='baseline')
        return l

    def _marge_aide(self):
        """Largeur disponible pour les lignes d'aide : la marge a gauche de la colonne d'interface (portrait 450 x 800 centre), pour ne pas cacher les fenetres du jeu."""
        if self.ui_rendu and self.args.ui_pos == 'centre':
            return int(max(260, (self.width - 450 * self.height / 800.0 * UI_ZOOM) / 2 - 16))
        if self.ui_rendu and self.args.ui_pos == 'droite':
            return int(max(260, self.width - 450 * self.height / 800.0 * UI_ZOOM - 16))
        return int(max(260, self.width - 20))

    def _curseur(self, port):
        """Bouton en surbrillance du menu actif : curseur du moteur (messages 4) ou, sans curseur du moteur, curseur local des fleches."""
        f = self.moteur.ui.f[port]
        if f.get('grille'): return f['cur']
        return self.cur_local.get((port, f['ordre']), f['cur'])

    def _ui_repere(self):
        """Colonne d'interface du jeu (portrait 450 x 800 centre, hauteur de la fenetre) : (x du centre, y du centre, pixels par unite)."""
        ech = self.height / 800.0 * self.ui_k
        return {'centre': self.width / 2, 'droite': self.width - 225 * ech, 'gauche': 225 * ech}.get(self.args.ui_pos, self.width / 2), self.height / 2.0, ech

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
        """Zones tactiles de la fenetre d'un port : [(numero, manette, x0, y0, x1, y1)] en pixels."""
        fe = self.ui_g.f.get(port) if self.ui_g else None
        if not fe: return []
        cx, cy, ech = self.ui_tf.get(port) or self._ui_repere(); dz = getattr(self, 'ui_dz', 0.0) if port in getattr(self, 'ui_suit', ()) else 0.0
        return [(b, pad, cx + x0 * ech, cy + (z0 + dz) * ech, cx + x1 * ech, cy + (z1 + dz) * ech, pr) for b, pad, x0, z0, x1, z1, pr in fe.boutons()]

    def _tex_icone(self, ident):
        """Texture de l'icone `ident` (case 32 x 32 de la feuille MenuTexture, numerotee de gauche a droite et de haut en bas ; Riseup.SetTexture -> UV 1/32) ; None si la feuille est absente."""
        if ident in self.icone_tex: return self.icone_tex[ident]
        if self._menu_tex is None:
            try:
                from PIL import Image
                self._menu_tex = np.array(Image.open(os.path.join(self.args.cache, 'ui_MenuTexture.png')).convert('RGBA'))
            except Exception: self._menu_tex = False
        t = None
        if self._menu_tex is not False:
            r, c = divmod(ident, 32); h = self._menu_tex.shape[0]
            if (r + 1) * 32 <= h: t = self._tex(self._menu_tex[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32], False)
        self.icone_tex[ident] = t
        return t

    def _icones(self, e, champ, bataille, dh, cam3d=None):
        """Bulles d'icone au-dessus des personnages (paquets 19/20, Riseup : carre de 0,96 face a la camera, avance de 0,48 vers elle) : [(texture, vertex_list)]."""
        if champ or bataille or not e.icones or e.cam_pos is None or e.cam_cible is None: return []
        fwd = np.array(e.cam_cible, float) - np.array(e.cam_pos, float); fwd /= np.linalg.norm(fwd) or 1
        out = []
        for slot, ic in sorted(e.icones.items()):
            if ic['pos'] is None or ic['alpha'] < 0.02: continue
            tex = self._tex_icone(ic['id'])
            if not tex: continue
            p = np.array(ic['pos'], float) - fwd * 0.48
            if cam3d is not None: a, b, up = p - cam3d[0] * 0.48, p + cam3d[0] * 0.48, cam3d[1] * 0.96       # de face a l'ecran, comme les personnages (rotation de la camera)
            else: a, b, up = p - dh * 0.48, p + dh * 0.48, np.array([0.0, 0.96, 0.0])
            q = np.array([a, b, b + up, a, b + up, a + up], np.float32).ravel().tolist()
            uv = [0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1]; cl = [1.0, 1.0, 1.0, float(min(max(ic['alpha'], 0.0), 1.0))] * 6
            vl = self.icone_vl.get(slot)
            if vl is None: vl = self.icone_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            out.append((tex, vl))
        return out

    def _carte_ports(self):
        """Fenetres de la carte ouverte (FieldImageMap) : {25: plan fixe, 26: grande carte qui se complete, 22: bouton retour} -> port ; vide si aucune carte n'est ouverte."""
        r = {}
        for p, f in self.moteur.ui.f.items():
            if p >= 12 and f.get('act') and f.get('type') in (22, 23, 25, 26): r[22 if f['type'] == 23 else f['type']] = p
        return r

    def _bouton_sous(self, port, x, y):
        """Bouton de la fenetre `port` sous le pointeur (le plus en avant d'abord) : (numero, manette, profondeur) ou None."""
        h = [(pr, b, pad) for b, pad, x0, y0, x1, y1, pr in self._zones(port) if x0 <= x <= x1 and y0 <= y <= y1]
        if not h: return None
        pr, b, pad = max(h, key=lambda t: t[0])
        return b, pad, pr

    def on_mouse_press(self, x, y, bouton, modifiers):
        """Souris = tactile du mobile : appui sur un bouton du menu actif (MenuPortItem.Update, PUSH_STATE_BEGIN) ; clic droit = Annuler."""
        M = pyglet.window.mouse; mo = self.moteur
        if not self._pret: return
        if self.pause.ouvert: self.pause.clic(x, y, bouton); return
        if bouton == M.RIGHT: self.clic_b = True; return
        if bouton == M.LEFT:
            vis = self.hud.visibles()
            if vis and self.hud.appuyer(x, y, vis): self.son.jouer_se(SE_BOUTON); return                  # boutons a l'ecran (Carte, Commandes, Discussion)
        if bouton != M.LEFT or not self.ui_rendu: return
        cp = self._carte_ports()
        if 22 in cp:                                                               # bouton retour de la carte (touche de manette 0x400, sans numero) : ferme la carte au relachement
            h = self._bouton_sous(cp[22], x, y)
            if h and h[0] == -1 and h[1] == 0x400: self.appui = (cp[22], h[0], h[1]); self.son.jouer_se(SE_BOUTON); return
        touches = [(h[2], -i, port, h) for i, port in enumerate(mo.menus_saisie()) for h in [self._bouton_sous(port, x, y)] if h]      # tous les menus qui attendent la saisie : bouton le plus en avant, puis fenetre la plus recente
        if touches:
            _, _, port, h = max(touches, key=lambda t: t[:2]); self.appui = (port, h[0], h[1]); self.son.jouer_se(SE_BOUTON); return
        if mo.msg_visible: self.clic_a = True                                      # toucher le message = page suivante

    def on_mouse_motion(self, x, y, dx, dy):
        """Survol de la souris : le bouton sous le pointeur est selectionne comme avec les fleches. Menu tactile (curseur local) : immediat ; menu a curseur du moteur :
        le curseur est amene sur le bouton par des appuis de direction, une image sur trois (voir _survol_pas)."""
        if not self._pret: return
        if self.pause.ouvert: self.pause.survol(x, y); return
        if not self.ui_rendu or self.appui: return
        mo = self.moteur
        touches = [(h[2], -i, port, h) for i, port in enumerate(mo.menus_saisie()) for h in [self._bouton_sous(port, x, y)] if h and h[0] >= 0]
        if not touches: self.survol = None; return
        _, _, port, h = max(touches, key=lambda t: t[:2]); f = mo.ui.f[port]
        if f.get('grille'): self.survol = [port, h[0], 0] if f['cur'] != h[0] else None
        elif self.cur_local.get((port, f['ordre'])) != h[0]: self.cur_local[(port, f['ordre'])] = h[0]; self.survol = None

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
        if self.pause.ouvert: self.pause.relache(x, y, bouton); return
        if bouton == pyglet.window.mouse.LEFT and self.hud.appui:
            n = self.hud.relacher(x, y, self.hud.visibles())
            if n: self.hud_decl = HM.DECL[n]
            return
        if bouton != pyglet.window.mouse.LEFT or not self.appui: return
        port, b, pad = self.appui; self.appui = None
        h = self._bouton_sous(port, x, y)
        if b == -1 and pad == 0x400:                       # bouton retour : MenuPortItem.Update ajoute 0x400 aux touches du jeu (le moteur ferme la carte) au lieu d'envoyer un message au port
            if h and h[0] == b: self.hud_decl = BTN_DISCUSSION
            return
        if h and h[0] == b and port in self.moteur.menus_saisie():
            self.moteur.envoyer_menu(port, 1, b, pad); self.menu_relacher = port
            f = self.moteur.ui.f.get(port)
            if f: f['cur'] = b

    # saut des chiffres des degats : decalage vers le haut (unites d'interface) a chaque tick de 2 / 30 s (HoppingNumber.Update)
    SAUT_DEGATS = (0, 0, 4, 4, 6, 6, 6, 6, 4, 4, 2, 2, 0, 0, 2, 2) + (0,) * 22

    def _chiffres_tex(self):
        """Chiffres 0 a 9 (blancs a ombre, 16 x 16 px) de la feuille de menu : textures separees."""
        if self._nb_tex is None:
            self._nb_tex = []
            try:
                from PIL import Image
                im = Image.open(os.path.join(self.args.cache, 'ui_MenuTexture.png')).convert('RGBA')
                for d in range(10):
                    a = np.array(im.crop((576 + 16 * d, 288, 592 + 16 * d, 304)))
                    t = pyglet.image.ImageData(16, 16, 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=64).get_texture(); gl.glBindTexture(t.target, t.id)
                    gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
                    self._nb_tex.append(pyglet.sprite.Sprite(t))
            except Exception as ex: print('Chiffres des degats indisponibles : %r' % (ex,), flush=True)
        return self._nb_tex

    def _dessiner_degats(self, e):
        """Nombres de degats qui sautent au-dessus du monstre touche (BattleMenu_setHoppingNumbers -> HoppingNumber.Create) : quatre chiffres au plus, un tick (2 / 30 s) de decalage entre
        deux chiffres, chaque chiffre visible pendant 19 ticks. Position : pied du monstre projete par la camera du combat, plus min(hauteur x 1,85 ; 160) unites d'interface."""
        if not self.nb_degats: return
        if e.partie != MO.PARTIE_COMBAT or getattr(self, '_M_combat', None) is None: self.nb_degats = []; return
        sp = self._chiffres_tex()
        if not sp: self.nb_degats = []; return
        img = self.moteur.images + self.alpha                          # image du moteur, fraction comprise
        ech = self.height / 800.0 * self.ui_k; vivants = []
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        for n in self.nb_degats:
            mm = e.maillages.get(n['ch'])
            chiffres = [int(c) for c in str(max(0, min(9999, n['dm'] & 0xffff)))]
            t = img - n['t0']                                           # ticks ecoules depuis la creation (1 tick = 1 image du moteur)
            if t > 21 + 2 * len(chiffres): continue                     # termine (dernier chiffre : wait >= 38)
            vivants.append(n)
            if not mm: continue
            P = np.array(list(mm['pos']) + [1.0]); c = self._M_combat @ P
            if c[3] <= 0: continue
            px = ((c[0] / c[3]) * 0.5 + 0.5) * self.width; py = ((c[1] / c[3]) * 0.5 + 0.5) * self.height + min(n['h'] * 1.85, 160.0) * ech
            kd = float(self.reg['taille_degats']); taille = 25.6 * ech * kd; pas = 21.0 * ech * kd; larg = len(chiffres) * pas              # chiffre de 16 px agrandi x 2 (AddIcon size 2,0) x 0,8 (echelle locale)
            for k, d in enumerate(chiffres):
                wait = -(1 + 4 * k) + 2 * t                                  # compteur du chiffre : 2 ticks de decalage entre chiffres, 2 par tick
                if not 0 <= wait < 38: continue
                saut = self.SAUT_DEGATS[int(wait)] * 0.8 * ech
                s = sp[d]; s.update(x=px - larg / 2 + k * pas, y=py + saut, scale=taille / 16.0); s.draw()
        self.nb_degats = vivants

    def _plan_fenetre(self, fe, f):
        """Fenetre de carte du moteur (type 25) : texture du plan nommee par le moteur et marqueur de position (coordonnees en pixels de la texture de 256 x 192)."""
        nom = f['cases'].get((0, 0))
        if nom and fe.nom_carte != nom:
            fe.nom_carte = nom
        if fe.nom_carte and (fe.carte is None or getattr(fe, '_nom_tex', None) != fe.nom_carte):
            t = self.plans.get(fe.nom_carte)
            if t is None:
                try: a = self.donnees.texture(fe.nom_carte)
                except Exception as ex: a = None; print('Plan %s illisible : %r' % (fe.nom_carte, ex), flush=True)
                if a is not None:
                    t = pyglet.image.ImageData(a.shape[1], a.shape[0], 'RGBA', np.ascontiguousarray(a[::-1]).tobytes(), pitch=a.shape[1] * 4).get_texture()
                    gl.glBindTexture(t.target, t.id)
                    gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                    gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
                self.plans[fe.nom_carte] = t
            fe.carte = t; fe._nom_tex = fe.nom_carte
        nd = fe.N.get(1527)                                        # marqueur « vous etes ici » : icone de 24 x 24 centree sur le point (x, y) du plan
        mx, my = f['indic'].get(1), f['indic'].get(2)
        if nd is not None and mx is not None and my is not None:
            nd['pos'][0] = -225.0 + mx * 450.0 / 256.0 - 12.0; nd['pos'][2] = 400.0 - my * 337.5 / 192.0 - 12.0; nd['act'] = True

    def _plan_monde_fenetre(self, fe, f):
        """Grande carte du monde (type 26, Make_WorldLargeMap) : le moteur envoie le drapeau des pieces du plan (indicateur 0), puis la position du joueur x, y (indicateurs 1 et 2) en pixels d'un plan de
        1024 x 1024. Le jeu compose le plan (LoadLargeWorldMap : fond + pieces dont le bit est leve dans le drapeau) et n'en montre qu'une fenetre de 256 x 192 pixels centree sur le joueur
        (decalage de texture x / 1024 - 0,125 ; le marqueur reste au centre de la fenetre)."""
        flag = f['indic'].get(0, 0) & 0xffff; x, y = f['indic'].get(1), f['indic'].get(2)
        if getattr(fe, '_flag_plan', None) != flag or fe.carte is None:
            try: pl = self.donnees.plan_monde()
            except Exception as ex: pl = None; print('Plan du monde illisible : %r' % (ex,), flush=True)
            if pl is None: return
            im = pl['base'].copy()
            for bit, px, py, a in pl['pieces']:
                if flag >> bit & 1: im[py:py + a.shape[0], px:px + a.shape[1]] = a
            rgba = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
            if fe.carte is not None: fe.carte.delete()
            t = pyglet.image.ImageData(1024, 1024, 'RGBA', np.ascontiguousarray(rgba[::-1]).tobytes(), pitch=4096).get_texture()
            gl.glBindTexture(t.target, t.id)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT); gl.glTexParameteri(t.target, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
            fe.carte = t; fe._flag_plan = flag
        if x is not None and y is not None:
            fe.carte_uv = ((x - 128) / 1024.0, 1.0 - (y + 96) / 1024.0, (x + 128) / 1024.0, 1.0 - (y - 96) / 1024.0)

    def _dessiner_menus(self):
        mo = self.moteur
        actif = mo.menu_actif()
        if os.environ.get('DQ_UIDBG'):                      # (test) etat des fenetres a chaque changement : port, type, visible, fenetre d'origine ou menu simple
            etat = tuple(sorted((p, f['type'], f['vis'], p in (self.ui_g.f if self.ui_g else ()), len(f['cases'])) for p, f in mo.ui.f.items() if f['vis'] or f['type'] is not None))
            if etat != getattr(self, '_ui_etat', None):
                self._ui_etat = etat; print('UI image %d actif=%s : %s' % (self.n, actif, ' '.join('%d:t%s%s%s c%d' % (p, t, '' if v else '(cache)', '[O]' if o else '[simple]', c) for p, t, v, o, c in etat)), flush=True)
        if self.ui_rendu:
            liste = sorted((f['ordre'], p) for p, f in mo.ui.f.items() if f['vis'] and p in self.ui_g.f)
            msg = bool(self.ui_msg and mo.msg_visible and 'msg' in self.ui_rendu.tex)
            dz = self._dz_message([p for _, p in liste]) if msg else 0.0
            self.ui_dz = dz; self.ui_suit = {p for _, p in liste if self.ui_g.f[p].typ == 1} if dz else set()      # le Oui/Non (type 1) suit la fenetre de message
            ivs = {}
            for _, p in liste:
                e = self.ui_g.f[p].etendue()
                if e: ivs[p] = (e[0] + (dz if p in self.ui_suit else 0.0), e[1] + (dz if p in self.ui_suit else 0.0))
            if msg:
                e = self.ui_msg.etendue()
                if e: ivs['msg'] = (e[0] + dz, e[1] + dz)
            k, gr, modes = self._ui_echelle(list(ivs.values()) + ([CB_ZONE_MENUS] if self.moteur.etat.partie == MO.PARTIE_COMBAT else [])); self.ui_k = k       # combat : echelle constante (la zone des menus de commandes compte toujours), sinon les fenetres changent de taille a chaque message
            H = float(self.height); s = H / 800.0 * k; cx = self._ui_repere()[0]
            def repere(cle):                                  # (cy, echelle) du groupe de fenetres qui contient cette fenetre
                if cle not in ivs: return 400.0 * s, s
                lo, hi = ivs[cle]; i = next((j for j, g in enumerate(gr) if g[0] - 1e-6 <= lo and hi <= g[1] + 1e-6), 0); m = modes[i] if modes else 'bas'
                return (400.0 * s if m == 'bas' else H - 400.0 * s if m == 'haut' else H / 2), s
            self.ui_tf = {p: (cx,) + repere(p) for _, p in liste}
            for _, p in liste:
                if self.ui_g.f[p].typ == 25: self._plan_fenetre(self.ui_g.f[p], mo.ui.f[p])
                elif self.ui_g.f[p].typ == 26: self._plan_monde_fenetre(self.ui_g.f[p], mo.ui.f[p])
            haut, bas = ([self.ui_msg] if msg else []), {}
            for _, p in liste:
                fe = self.ui_g.f[p]
                fe.selection(self.appui[1] if self.appui and self.appui[0] == p else (self._curseur(p) if p == actif else None))
                if p in self.ui_suit: haut.append(fe)
                else: bas.setdefault(self.ui_tf[p][1], []).append(fe)
            if haut: self.ui_rendu.dessiner(haut, cx, repere('msg')[0] + dz * s, s, (self.width, self.height))
            for cy, fens_g in bas.items(): self.ui_rendu.dessiner(fens_g, cx, cy, s, (self.width, self.height))
        fens = [(p, f) for p, f in mo.ui.visibles() if not (self.ui_g and p in self.ui_g.f)]
        if not fens: return
        ech = self.height / 720.0; W, H = self.width, self.height
        taille = 17 * ech; rh = 36 * ech; pad = 16 * ech; gap = 18 * ech
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        x_main = 40 * ech
        for port, f in fens:
            lignes = self._lignes_menu(f)
            if not lignes: continue
            sel = [l[0] for l in lignes if not l[4]]
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

    def _objets_carte(self):
        """Ordres du moteur sur les objets de la carte (portes, jarres...), puis une image d'animation ; les sommets modifies sont renvoyes a la carte graphique."""
        e = self.moteur.etat; cmds, e.objets_cmd = e.objets_cmd, []
        for c in cmds:
            if c[0] == 'carte':
                if self.objets is not None and self.carte_nom == e.carte: self.objets.reinit()
                continue
            if self.objets is None: continue
            if self.carte_nom != e.carte and e.partie != MO.PARTIE_CHAMP and e.carte: self._charger_carte(e.carte)       # la carte est chargee avant ses ordres
            if c[0] == 'anim': self.objets.anim_commune(c[1], c[2])
            elif c[0] == 'onoff': self.objets.on_off(c[1], c[2])
            elif c[0] == 'alpha': self.objets.alpha(c[1], c[2])
            elif c[0] == 'pos': self.objets.position(c[1], c[2])
            elif c[0] == 'rot': self.objets.rotation(c[1], c[2])
        if self.objets is None: return
        if os.environ.get('DQ_ANIM_TEST') and self.carte_nom == os.environ.get('DQ_CARTE_TEST', ';').split(';')[0]:   # (test) DQ_ANIM_TEST="objet:numero:image" : lance une animation commune a cette image de boucle
            o_t, no_t, n_t = (int(v) for v in os.environ['DQ_ANIM_TEST'].split(':'))
            if self.n == n_t: self.objets.anim_commune(o_t, no_t)
        sales = self.objets.tick()
        if self.palettes is not None: self.palettes.tick()
        sales_uv, sales_col = self.objets.sale_uv, self.objets.sale_col; self.objets.sale_uv = set(); self.objets.sale_col = set()
        for tex, vl, key in self.carte_vl:
            if key in sales: vl.position[:] = self.objets.cur[key].ravel()
            if key in sales_uv: vl.tex_coords[:] = self.objets.uv(key).ravel()
            if key in sales_col: vl.colors[:] = self.objets.col(key).ravel()

    def _duree_anim(self, idx, no):
        return self.objets.duree(idx, no) if self.objets is not None else None

    # ---- boucle
    def _tenue(self, action):
        """Une des touches de l'action (menu Touches) est-elle enfoncee ?"""
        k = self.touches
        return any(k[c] for c in self.reg.codes(action))

    def pad(self):
        """Manette du jeu d'apres les touches reglees : directions, A (valider), B (annuler)."""
        p = 0
        if self._tenue('haut'): p |= MO.HAUT
        if self._tenue('bas'): p |= MO.BAS
        if self._tenue('gauche'): p |= MO.GAUCHE
        if self._tenue('droite'): p |= MO.DROITE
        if self._tenue('A'): p |= MO.A
        if self._tenue('B'): p |= MO.B
        return p

    def _fronts(self):
        """Appuis (front montant) de X, Start, L et R depuis la derniere image du moteur."""
        r = {}
        for a in ACT_FRONTS:
            v = self._tenue(a); r[a] = v and not self.act_prec.get(a, False); self.act_prec[a] = v
        return r

    def _boucle(self, dt):
        """Avance le moteur par pas de 1/30 s (horloge reelle, au plus 3 pas de rattrapage par image affichee ; un blocage plus long est oublie) puis fixe alpha, la fraction du pas en cours."""
        self.n_boucle += 1
        if self.args.touches_test or self.args.shots_boucle: self._touches_test()
        if self.pause.ouvert: self.pause.maj(); self.acc = 0.0; self.t_boucle = None; self.alpha = 1.0; return        # menu Echap : le moteur est arrete
        t = time.perf_counter()
        dt = 0.0 if self.t_boucle is None else t - self.t_boucle
        self.t_boucle = t
        if self.fixe_test:
            self._pas(); self.alpha = 1.0; return
        f = self._facteur_vitesse()
        self.acc += min(dt * f, 3 * PAS_MOTEUR * max(1.0, f))
        n = 0; nmax = 3 * max(1, math.ceil(f))
        while self.acc >= PAS_MOTEUR * 0.85 and n < nmax:      # tolerance de 15 % : sur un ecran de 60 Hz, un pas tous les 2 images exactement (sans elle, la gigue de l'horloge alterne 2 et 3 images)
            self._pas(); self.acc -= PAS_MOTEUR; n += 1
        if n == nmax: self.acc = 0.0
        self.alpha = max(0.0, min(1.0, self.acc / PAS_MOTEUR))

    def _facteur_vitesse(self):
        """Vitesse du jeu quand le heros marche (reglages Jeu : vitesse de deplacement, course tant que la touche est tenue). Seulement sur le terrain (ville, donjon, carte du monde),
        direction tenue, sans message ni menu ni combat ni effet d'ecran : tout le terrain va plus vite, l'animation de marche comprise."""
        R = self.reg; mo = self.moteur; e = mo.etat
        if R['vitesse_marche'] == 1.0 and not (R['course'] and R['vitesse_course'] != 1.0): return 1.0
        if e.partie == MO.PARTIE_COMBAT or mo.msg_visible or mo.menu_actif() is not None or e.effet is not None or e.attente_charge is not None: return 1.0
        if not (self.pad() & (MO.HAUT | MO.BAS | MO.GAUCHE | MO.DROITE)): return 1.0
        f = float(R['vitesse_marche'])
        if R['course'] and self._tenue('courir'): f *= float(R['vitesse_course'])
        return max(0.25, min(8.0, f))

    def _touches_test(self):
        """(test) touches pressees a une image de boucle n, ou "cN+k" = k images de boucle apres que le combat a atteint N images : 'n:NOM' (NOM = nom de touche pyglet ;
        +NOM / -NOM = maintenue / relachee ; @x@y = clic de souris) ; captures '<shot>_<n>.png' ; la derniere capture quitte."""
        a = self.args
        def instant(n):                                         # numero d'image de boucle ou l'evenement n a lieu (None si pas encore connu)
            if isinstance(n, int): return n
            if n[0] not in self.base_c and self.n_combat == n[0] and self.n_combat > 0: self.base_c[n[0]] = self.n_boucle
            return self.base_c[n[0]] + n[1] if n[0] in self.base_c else None
        for ev in list(a.touches_test):
            n, nom = ev
            if instant(n) != self.n_boucle: continue
            a.touches_test.remove(ev); n = self.n_boucle
            if nom[0] == '@':                                  # @x@y : clic gauche en (x, y) pixels depuis le haut a gauche ; @x@y@1 : clic droit ; @x@y@2 : survol seul
                v = [int(t) for t in nom[1:].split('@')] + [0]; x, y = v[0], self.height - v[1]
                self.on_mouse_motion(x, y, 0, 0)
                if v[2] != 2: self.on_mouse_press(x, y, pyglet.window.mouse.RIGHT if v[2] else pyglet.window.mouse.LEFT, 0); a.touches_test.append((n + 3, '~@%d@%d' % (v[0], v[1])))
            elif nom[0] == '~': x, y = [int(t) for t in nom[2:].split('@')]; self.on_mouse_release(x, self.height - y, pyglet.window.mouse.LEFT, 0)
            elif nom[0] == '^': x, y = [int(t) for t in nom[1:].split('^')]; self.on_mouse_drag(x, self.height - y, 0, 0, pyglet.window.mouse.LEFT, 0)      # ^x^y : souris deplacee bouton enfonce
            elif nom[0] == '$': self.dispatch_event('on_text', nom[1:])                                                                                   # $texte : caracteres tapes
            elif nom[0] in '+-': self.dispatch_event('on_key_press' if nom[0] == '+' else 'on_key_release', getattr(pyglet.window.key, nom[1:]), 0)
            else: self.dispatch_event('on_key_press', getattr(pyglet.window.key, nom), 0); a.touches_test.append((n + 3, '-' + nom))       # appui court : relache 3 images plus tard
        for n in list(a.shots_boucle):
            if instant(n) == self.n_boucle:
                a.shots_boucle.remove(n); self.dispatch_event('on_draw'); self.flip()
                nom_n = ('b%d' % n) if isinstance(n, int) else ('c%d+%d' % n)
                pyglet.image.get_buffer_manager().get_color_buffer().save(a.shot.replace('.png', '_%s.png' % nom_n))
                if os.environ.get('DQ_TEMPS_REEL'): print('PAS moteur=%d images boucle=%d t=%.1f' % (self.n, self.n_boucle, time.time() - self.t_demarrage), flush=True)
                if not a.shots_boucle: self.on_close(); pyglet.app.exit()

    def _pas(self):
        self.prec = self._instantane()
        self.pas_t.append(time.perf_counter())
        self.tick(PAS_MOTEUR)

    def _instantane(self):
        """Etat du pas qui vient de finir : positions des personnages et de la camera, pour l'interpolation."""
        e = self.moteur.etat
        tup = lambda v: None if v is None else tuple(float(x) for x in v)
        return dict(cle=(e.partie, e.carte), sp={k: tup(s['pos']) for k, s in e.sprites.items() if s['pos'] is not None},
                    cam_pos=tup(e.cam_pos), cam_cible=tup(e.cam_cible), champ=tup(e.champ['cam']) if e.champ and e.champ['cam'] else None)

    def _interpoler(self):
        """Remplace, le temps d'un dessin, les positions des personnages et de la camera (carte du monde, villes) par celles de l'instant entre le pas precedent et le pas actuel ;
        un saut (changement de carte, deplacement force) n'est pas interpole. Renvoie de quoi tout remettre en place."""
        pr, a, e = self.prec, self.alpha, self.moteur.etat
        sauve = []
        if pr is None or a >= 1.0 or e.partie == MO.PARTIE_COMBAT or pr['cle'] != (e.partie, e.carte): return sauve
        seuil = 24.0 if e.partie == MO.PARTIE_CHAMP else 1.5       # pixels de la carte / unites de la ville par pas ; au-dela, c'est un saut
        def entre(q, c):
            if q is None or c is None or len(q) != len(c): return None
            d = max(abs(x - y) for x, y in zip(q, c))
            return None if d == 0 or d > seuil else tuple(x + (y - x) * a for x, y in zip(q, c))
        for k, sp in e.sprites.items():
            v = entre(pr['sp'].get(k), sp['pos'])
            if v is not None: sauve.append((sp, 'pos', sp['pos'], False)); sp['pos'] = v
        for nom in ('cam_pos', 'cam_cible'):
            v = entre(pr[nom], getattr(e, nom))
            if v is not None: sauve.append((e, nom, getattr(e, nom), True)); setattr(e, nom, v)
        if e.champ and e.champ['cam']:
            v = entre(pr['champ'], e.champ['cam'])
            if v is not None: sauve.append((e.champ, 'cam', e.champ['cam'], False)); e.champ['cam'] = v
        return sauve

    def on_draw(self):
        sauve = self._interpoler()
        try: self._dessiner()
        finally:
            for obj, nom, ancien, attr in sauve:
                if attr: setattr(obj, nom, ancien)
                else: obj[nom] = ancien

    def tick(self, dt):
        p = self.args.script.get(self.n, self.pad()) if self.args.script is not None else self.pad()
        if self.args.slot and self.args.auto_message and self.n < 112:
            # (test) ferme le message d'accueil automatiquement
            p = MO.A if (70 <= self.n <= 72 or 88 <= self.n <= 90) else 0
        if self.args.script_combat is not None and self.n_combat > 0: p = self.args.script_combat.get(self.n_combat, 0)
        if self.args.force_champ and self.n == self.args.force_champ: self.moteur.demarrer_champ()
        if os.environ.get('DQ_SPR') and self.n == 100: print('SPRITES', {k: (sp['id'], tuple(round(float(x), 2) for x in sp['pos']) if sp['pos'] is not None else None, sp.get('pose'), sp.get('dir'), sp.get('vis', True)) for k, sp in self.moteur.etat.sprites.items()}, 'icones', self.moteur.etat.icones, flush=True)
        if os.environ.get('DQ_VILLE') and self.n == 30: self.moteur.demarrer_ville(os.environ['DQ_VILLE'])        # (test) charge cette ville ou ce donjon
        if self.args.clics:                                                # (test) clics simules : image:x:y[:d] (d = clic droit), x et y en pixels depuis le haut a gauche ; appui a l'image, relachement 3 images plus tard
            for c in self.args.clics:
                if c[3] == 2:                                              # d = 2 : survol sans clic
                    if self.n == c[0]: self.on_mouse_motion(c[1], self.height - c[2], 0, 0)
                    continue
                if self.n == c[0]: (self.on_mouse_press(c[1], self.height - c[2], pyglet.window.mouse.RIGHT if c[3] else pyglet.window.mouse.LEFT, 0))
                if self.n == c[0] + 3: self.on_mouse_release(c[1], self.height - c[2], pyglet.window.mouse.LEFT, 0)
        if self.clic_a: p |= MO.A; self.clic_a = False                  # clics de souris : page suivante / annuler
        if self.clic_b: p |= MO.B; self.clic_b = False
        decl = p & ~self.pad_prec                      # boutons qui viennent d'etre presses
        fr = self._fronts()
        if self.moteur.msg_visible and (fr['menu'] or fr['discussion']): p |= MO.A; decl |= MO.A        # Entree et Espace tournent aussi les pages des messages
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
        if carte:
            # Touche Carte : 1re fois la premiere version, 2e fois l'autre version (haut de la manette sur la fenetre du plan : FieldImageMap::execute), 3e fois ferme (bouton retour : 0x400, comme MenuPortItem.Update d'Unity) ;
            # Annuler ou le bouton retour ferment aussi. Le curseur et les fleches ne servent pas ici.
            if fr['carte'] and 25 in carte and 26 in carte and self.carte_vue == 1:
                mo.envoyer_menu(carte[25], 1, -1, 2); self.menu_relacher = carte[25]; self.carte_vue = 2; fr['carte'] = False; self.son.jouer_se(SE_BOUTON)
            elif fr['carte'] or (decl & MO.B): self.hud_decl = BTN_DISCUSSION; self.son.jouer_se(SE_BOUTON)
        port = None if carte else mo.menu_actif()
        if port is not None and mo.msg_visible and not mo.ui.f[port].get('entree'): port = None      # critere memoire seul : le message d'abord
        if port is not None and self.menu_relacher is None: self._survol_pas()
        if port is not None:                               # un menu attend les touches : elles lui sont envoyees, pas au terrain
            f_port = mo.ui.f.get(port)
            self._saisie_menu(port, decl | (MO.A if fr['menu'] or fr['discussion'] else 0) | (MO.B if fr['carte'] and f_port and f_port.get('type') == 25 else 0) | (MO.GAUCHE if fr['L'] else 0) | (MO.DROITE if fr['R'] else 0))        # L / R = gauche / droite (page precedente / suivante des menus a une colonne)
            p = decl = 0
        elif not mo.msg_visible:
            # sur le terrain : A = parler / examiner, Annuler, X ou Start = ouvrir le menu (le moteur veut ces boutons seuls)
            hd, self.hud_decl = self.hud_decl, 0                # (le moteur veut ces boutons seuls) A, puis boutons a l'ecran, puis touches Commandes / Discussion / Carte
            if decl & MO.A: decl = BTN_PAROLE
            elif hd: decl = hd
            elif fr['menu']: decl = BTN_MENU
            elif fr['discussion']: decl = BTN_DISCUSSION
            elif fr['carte']: decl = BTN_CARTE
            p &= ~(MO.A | MO.B)
        if os.environ.get('DQ_DEBUG') and (p or decl): print('n=%d p=%#x decl=%#x msg=%s actif=%s' % (self.n, p, decl, mo.msg_visible, mo.menu_actif()), flush=True)
        t0 = time.time(); mo.step(p, decl); self.dt_moteur = time.time() - t0
        if mo.ui.degats:                                   # nombres de degats sur les monstres (HoppingNumber) : un par coup
            for ch, h, dm in mo.ui.degats: self.nb_degats.append(dict(ch=ch, h=h, dm=dm, t0=mo.images))
            mo.ui.degats = []
        if os.environ.get('DQ_FLAG') and self.n % 20 == 0: print('FLAG n=%d %#x partie=%s msg=%s menu=%s' % (self.n, mo.drapeaux(), mo.etat.partie, mo.msg_visible, mo.menu_actif()), flush=True)
        if mo.etat.partie == MO.PARTIE_CHAMP and mo.etat.champ is not None: self._avancer_motifs()
        self.son.image = self.n
        if mo.etat.sons: self.son.evenements(mo.etat.sons); mo.etat.sons = []
        self.son.tick()
        if os.environ.get('DQ_ETAT') and self.n % 25 == 0: print('ETAT n=%d partie=%#x carte=%s champ=%s p=%#x' % (self.n, mo.etat.partie, mo.etat.carte, None if mo.etat.champ is None else mo.etat.champ['cam'], p), flush=True)
        e = self.moteur.etat
        self._objets_carte()
        self.n += 1
        self.n_combat = self.n_combat + 1 if self.moteur.etat.partie == MO.PARTIE_COMBAT else 0
        if self.args.shots_effet and e.effet is not None and e.effet['n'] in self.args.shots_effet and self.args.shot:       # (test) captures pendant l'effet de debut de combat
            self.dispatch_event('on_draw'); self.flip()
            pyglet.image.get_buffer_manager().get_color_buffer().save(self.args.shot.replace('.png', '_e%d.png' % e.effet['n']))
        if self.args.shots_combat and self.n_combat in self.args.shots_combat and self.args.shot:       # (test) captures intermediaires pendant un combat
            self.dispatch_event('on_draw'); self.flip()
            pyglet.image.get_buffer_manager().get_color_buffer().save(self.args.shot.replace('.png', '_%d.png' % self.n_combat))
            print('combat', self.n_combat, 'engine image', self.moteur.images, [(k, len(m['v']), m['pos']) for k, m in sorted(self.moteur.etat.maillages.items())], flush=True)
        if self.args.shot and (self.n >= self.args.images or (self.args.images_combat and self.n_combat >= self.args.images_combat)):
            self.dispatch_event('on_draw'); self.flip()
            pyglet.image.get_buffer_manager().get_color_buffer().save(self.args.shot)
            print('capture :', self.args.shot, [(q, 'cur', f['cur'], list(f['cases'].items())[:3]) for q, f in self.moteur.ui.visibles()], self.moteur.menu_actif(), self.moteur.msg_visible, flush=True); pyglet.app.exit()

    def _dessiner(self):
        self._dessiner_scene()
        if self.sauve_rapide is not None and not self.pause.ouvert:       # raccourci chiffre : l'etat et la miniature sont pris sur l'image qui vient d'etre dessinee
            n, self.sauve_rapide = self.sauve_rapide, None
            try:
                t = self._copier_miniature(); png = self._png_miniature(t); t.delete(); self.sauver_etat(n, png); self.toast('État %d enregistré' % n)
            except Exception as ex: self.toast('Enregistrement impossible : %r' % (ex,))
        if not self.pause.ouvert: self.hud.dessiner(self.hud.visibles())
        if self.pause.ouvert:
            if self.pause.veut_miniature: self.pause.mini_tex = self._copier_miniature(); self.pause.veut_miniature = False       # le jeu sans le menu, pour la miniature des etats (copie sur la carte graphique : pas de relecture qui bloque)
            self.pause.dessiner()
        elif time.time() - self.t_demarrage < 8.0 and not self.aide and not self.args.shot:
            gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA); self.etiq_conseil.draw()
        if self.toasts and time.time() < self.toasts[0][1]:                # message bref en haut de l'ecran
            k = max(0.75, self.height / 900.0); gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            et = self._etiq(self.toasts[0][0], 16 * k, (255, 255, 255, 255)); w = et.content_width + 28 * k; h = 36 * k
            r = pyglet.shapes.Rectangle((self.width - w) / 2, self.height - 24 * k - h, w, h, color=(0, 0, 0)); r.opacity = 170; r.draw()
            et.x = (self.width - et.content_width) / 2; et.y = self.height - 24 * k - h + 11 * k; et.draw()

    def _dessiner_scene(self):
        t_debut = time.perf_counter()
        if self.t_prec is not None: self.ecarts.append(t_debut - self.t_prec)
        self.t_prec = t_debut
        e = self.moteur.etat
        if os.environ.get('DQ_CARTE_TEST'):                                  # (test) DQ_CARTE_TEST="nom;x,y,z;cx,cy,cz" : montre une carte de ville/grotte avec une camera fixe (animations de decor)
            nom_t, pc, cc = os.environ['DQ_CARTE_TEST'].split(';')
            e.partie = 0; e.carte = nom_t; e.champ = None; e.fond = (0.0, 0.0, 0.0); e.cam_libre = False
            e.cam_pos = tuple(float(v) for v in pc.split(',')); e.cam_cible = tuple(float(v) for v in cc.split(','))
        if e.effet is not None and self.effet_ref is not e.effet: self.effet_ref = e.effet; self.effet_tex_prete = False      # nouvel effet de debut de combat : la premiere image est dessinee normalement puis copiee
        if e.effet is not None and self.effet_tex_prete: self._dessiner_effet(e.effet); self._dessiner_aide(); return
        if e.effet is None and e.attente_charge is not None:                # fin de l'effet, scene du combat pas encore arrivee : noir (sinon on verrait la scene d'avant)
            gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear(); self._dessiner_aide(); return
        champ = e.partie == MO.PARTIE_CHAMP and e.champ is not None        # carte du monde (tuiles) ou ville (decor 3D)
        cam3d = None                                                        # ville : (droite, haut, avant) de la camera, pour les panneaux des personnages
        if not champ and e.carte and e.carte != self.carte_nom: self._charger_carte(e.carte)
        fond = e.fond
        if e.partie == MO.PARTIE_COMBAT and self.fond_decor and not any(fond): fond = self.fond_decor
        gl.glClearColor(fond[0], fond[1], fond[2], 1.0)
        self.clear()
        bataille = e.partie == MO.PARTIE_COMBAT and e.cam_pos is not None and e.cam_rot is not None
        if (e.partie == MO.PARTIE_CHAMP and e.champ is None) or (not champ and not bataille and e.partie != MO.PARTIE_COMBAT and (e.carte or '').startswith('btl_')):
            # carte du monde pas encore envoyee, ou combat fini et scene suivante pas encore arrivee : on ne montre pas la scene d'avant avec la camera d'une autre (image de decor de combat au retour d'une fuite)
            gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear()
            gl.glViewport(0, 0, *self.get_framebuffer_size()); self._dessiner_fondu(); self._maj_message(); self._dessiner_message(); self._dessiner_menus(); self._dessiner_aide(); return
        if not champ and not bataille and (e.cam_pos is None or e.cam_cible is None): self._dessiner_aide(); return
        gl.glEnable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glViewport(0, 0, *self.get_framebuffer_size())
        aspect = self.width / max(1, self.height)
        if champ: M, dh, w, h = self._camera_champ(e, aspect); self._maj_champ(e)
        elif bataille:
            M, M_decor = self._camera_combat(e, aspect); self._M_combat = M; dh = np.array([1.0, 0, 0]); w, h = SPRITE_L * SPRITE_ECHELLE, SPRITE_H * SPRITE_ECHELLE
        else:
            M, cam3d = self._camera_ville(e, aspect)
            # sprites : panneaux verticaux tournes vers la camera (listes de sommets persistantes, une par emplacement)
            fh = np.array([e.cam_cible[0] - e.cam_pos[0], 0, e.cam_cible[2] - e.cam_pos[2]]); fh /= np.linalg.norm(fh) or 1
            dh = np.cross([0, 1, 0], fh); dh /= np.linalg.norm(dh) or 1
            w, h = SPRITE_L * SPRITE_ECHELLE, SPRITE_H * SPRITE_ECHELLE
        up = np.array([0, 0, -h]) if champ else np.array([0, h, 0])       # carte du monde : le haut du sprite est le nord (-Z)
        a_dessiner = []; ombres = []; pp = self.mode == MODE_PP
        rang = {}
        if champ:       # carte du monde : sprites a plat, tous a la meme hauteur ; le jeu les superpose par la hauteur z que le moteur envoie (3e valeur de la position), puis le plus au sud passe devant (un equipier au sud du heros est devant lui), puis l'emplacement le plus recent
            vus = [(float(s['pos'][2]) if len(s['pos']) > 2 else 0.0, float(s['pos'][1]), sl) for sl, s in e.sprites.items() if s['pos'] is not None]
            rang = {sl: i for i, (_, _, sl) in enumerate(sorted(vus))}
        for slot, s in sorted(e.sprites.items()):
            if s['pos'] is None or s['col'][3] < 0.02 or not s.get('vis', True): continue      # paquet 14 : Chara.SetVisible
            f = self._feuille(s['id'] - 4096 if (champ and s['id'] >= 4096) else s['id'], self.mode)
            if not f: continue
            tw, th, nl = f['tw'], f['th'], f['nl']
            col, row = s['pose'] % 3, s['dir'] % nl
            pl, ph, g = f['cl'] + 2 * f['g'], f['ch'] + 2 * f['g'], f['g']          # case (col, row) de l'atlas (origine ou HD), gouttieres exclues
            u0, u1 = (col * pl + g) / tw, (col * pl + g + f['cl']) / tw
            v1, v0 = 1 - (row * ph + g) / th, 1 - (row * ph + g + f['ch']) / th
            p = np.array([(round(s['pos'][0]) if pp else s['pos'][0]) / CH_PX, 0.04 + rang.get(slot, 0) * 0.0005, (round(s['pos'][1]) if pp else s['pos'][1]) / CH_PX]) if champ else np.array(s['pos'], float)       # carte du monde : sprite a plat (vue de dessus), le heros (emplacement 0) au-dessus des autres
            if cam3d is not None:
                # Chara.normalBillboard : le panneau (0,48 x 0,64) prend la rotation de la camera, donc il est de face a l'ecran (pas ecrase par l'inclinaison) ; ses sommets
                # sont decales en profondeur (bas 0,185, haut 0,65 vers la camera, Chara.SystemInit) : une fois a l'ecran il se comporte comme un personnage debout pour le z-buffer
                r_, u_, f_ = cam3d; zb, zh = 0.185 / 0.48 * w, (0.65 - 0.185) / 0.48 * w       # decalages de profondeur a l'echelle du panneau (le haut penche de 36 degres vers la camera : le panneau est presque vertical dans le monde)
                a, b = p - r_ * w / 2 - f_ * zb, p + r_ * w / 2 - f_ * zb
                c, d = b + u_ * h - f_ * zh, a + u_ * h - f_ * zh
                q = np.array([a, b, c, a, c, d], np.float32).ravel().tolist()
            else:
                a, b = p - dh * w / 2, p + dh * w / 2
                q = np.array([a, b, b + up, a, b + up, a + up], np.float32).ravel().tolist()
            uv = [u0, v0, u1, v0, u1, v1, u0, v0, u1, v1, u0, v1]
            cl = list(map(float, s['col'])) * 6
            vl = self.sprite_vl.get(slot)
            if vl is None: vl = self.sprite_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            a_dessiner.append((slot, f, vl))
            if s.get('ombre', True):                                                 # paquet 15 : le moteur peut masquer l'ombre d'un personnage (bateaux de la carte du monde...)
                al = float(s['col'][3]) * float(s.get('ombre_a', 1.0))
                if cam3d is not None: ombres.append((slot, np.array(s['ombre_pos'], float) if s.get('ombre_sep') and s.get('ombre_pos') else p, al))
                elif champ: ombres.append((slot, p, al))
        icones = self._icones(e, champ, bataille, dh, cam3d)
        self._dom_lie = None
        self.prog.use()
        self.prog['mvp'] = tuple(float(x) for x in M.T.ravel()); self.prog['cutoff'] = 0.5; self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0); self.prog['amul'] = 1.0
        gl.glActiveTexture(gl.GL_TEXTURE0)
        if champ: self._tracer_champ(e)
        elif bataille:
            self.prog['mvp'] = tuple(float(x) for x in M_decor.T.ravel())
            self._tracer_decor()
            self.prog['mvp'] = tuple(float(x) for x in M.T.ravel()); self.prog['cutoff'] = 0.05; self.prog['net'] = 1.0
            gl.glDisable(gl.GL_CULL_FACE); gl.glDepthMask(gl.GL_FALSE)         # shaders DssaMonster* : ZWrite Off, Cull Off, ZTest LEqual
            mons = self._maillages_combat(e)             # reecrit les sommets des monstres/effets (tampons « sales » : pas encore envoyes au GPU)
            self._dom_lie = None                         # force le rebind + commit() au 1er trace : sinon les monstres sortent avec les donnees de l'image precedente
            for tex, tw, th, vl, shader, hd in mons:
                self.prog['net'] = 0.0 if hd else (2.0 if pp else 1.0)           # texture agrandie : filtrage doux des mipmaps ; originale : pixels nets
                if shader == 3: gl.glDisable(gl.GL_DEPTH_TEST)                 # DssaCharaTransparent : ZTest Always
                self.prog['tsize'] = (float(tw), float(th)); self._tracer(tex, vl)
                if shader == 3: gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glDepthMask(gl.GL_TRUE)
            self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0)
        else:
            self._tracer_decor(True)
        self.prog['cutoff'] = 0.05
        if ombres and not os.environ.get('DQ_SANS_OMBRE'):
            if cam3d is not None: self._dessiner_ombres_chara(ombres, cam3d)
            elif champ: self._dessiner_ombres_champ(ombres, w * CH_PX / 24.0)
        for slot, f, vl in a_dessiner:
            self.prog['net'] = 0.0 if f['hd'] else (2.0 if pp else 1.0); self.prog['tsize'] = (float(f['tw']), float(f['th']))
            self._tracer(f['t'], vl)       # comme Unity (shader Chara, ZTest normal) : un personnage cache par un decor n'est pas visible du tout
        self.prog['net'] = 2.0 if pp else 1.0; self.prog['tsize'] = (32.0, 32.0)
        for tex, vl in icones: self._tracer(tex, vl)                          # bulles d'icone (Riseup), devant les personnages
        self.prog.stop()
        gl.glDisable(gl.GL_DEPTH_TEST)
        self._dessiner_fondu(); self._dessiner_degats(e)
        self._maj_message(); self._dessiner_message(); self._dessiner_menus()
        self.dt_dessin += (time.perf_counter() - t_debut - self.dt_dessin) * 0.1
        if e.effet is not None and not self.effet_tex_prete: self._copier_ecran(); self.effet_tex_prete = True       # capture de l'ecran du jeu, sans les lignes d'aide
        self._dessiner_aide()


    # ombre des personnages : Chara.s_shadowMesh (carre +-1 en XZ, Y = 0,00625), echelle s_shadowDefScale (0,347 ; 10 ; 0,206), texture CharaTex/common (32 x 32 : ellipse noire d'alpha 96 / 255, filtre point),
    # shader Custom/CharaShadow (SrcAlpha / OneMinusSrcAlpha, ZWrite Off, ZTest LEqual, file 2999 = avant les personnages), position Chara.SetShadowPosition = pos + rotation du panneau x (0 ; 0 ; 0,25)
    # (donc decalee de 0,25 le long du rayon de la camera : meme point a l'ecran, mais devant le sol), orientation Euler(0, lacet de la camera, 0) = a plat.
    OMBRE_DEMI = (0.347, 0.206); OMBRE_HAUT = 0.0625; OMBRE_DEC = 0.25

    def _dessiner_ombres_chara(self, ombres, cam3d):
        if getattr(self, '_ombre_tex', None) is None: self._ombre_tex_creer()
        if not self._ombre_tex: return
        r_, u_, f_ = cam3d
        rh = np.array([r_[0], 0.0, r_[2]]); rh /= np.linalg.norm(rh) or 1                 # lacet seul de la camera
        fh = np.array([f_[0], 0.0, f_[2]]); fh /= np.linalg.norm(fh) or 1
        ex, ez = self.OMBRE_DEMI
        gl.glDepthMask(gl.GL_FALSE); gl.glDepthFunc(gl.GL_LEQUAL)
        self.prog['cutoff'] = 0.0; self.prog['net'] = 0.0; self.prog['tsize'] = (64.0, 64.0)
        for slot, p, alpha in ombres:
            c = p - f_ * self.OMBRE_DEC + np.array([0.0, self.OMBRE_HAUT, 0.0])
            P = [c - rh * ex - fh * ez, c + rh * ex - fh * ez, c + rh * ex + fh * ez, c - rh * ex + fh * ez]
            q = np.array([P[0], P[1], P[2], P[0], P[2], P[3]], np.float32).ravel().tolist()
            uv = [0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1]; cl = [1.0, 1.0, 1.0, min(1.0, alpha)] * 6          # _Color.a = SetShadowAlpha (1 par defaut), x alpha du personnage (SetColorWithShadow)
            vl = self._ombre_vl.get(slot)
            if vl is None: vl = self._ombre_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            self._tracer(self._ombre_tex, vl)
        gl.glDepthMask(gl.GL_TRUE); gl.glDepthFunc(gl.GL_LESS); self.prog['cutoff'] = 0.05        # (les personnages qui suivent rejettent les pixels transparents : sinon leur panneau entier ecrit la profondeur et masque le compagnon derriere)

    # ombre des personnages sur la carte du monde : Chara.SetFieldMode redimensionne le maillage d'ombre a s_shadowDefScale x 28,8 (ellipse de demi-axes 10 x 5,9 pixels de la carte) et l'incline de 36 degres comme le personnage
    # (projetee : 5,9 x cos 36 = 4,8) ; Chara.SetFieldPosition la pose au meme point que le personnage (ses pieds). Le moteur masque celle des bateaux (paquet 15).
    OMBRE_CH = (9.99, 5.93 * math.cos(math.radians(36.0)))

    def _dessiner_ombres_champ(self, ombres, ech):
        if getattr(self, '_ombre_tex', None) is None: self._ombre_tex_creer()
        gl.glDepthMask(gl.GL_FALSE); gl.glDepthFunc(gl.GL_LEQUAL)
        self.prog['cutoff'] = 0.0; self.prog['net'] = 0.0; self.prog['tsize'] = (64.0, 64.0)
        rx, rz = self.OMBRE_CH[0] * ech / CH_PX, self.OMBRE_CH[1] * ech / CH_PX
        for slot, p, alpha in ombres:
            x, y, z = float(p[0]), 0.03, float(p[2])
            q = [x - rx, y, z - rz, x + rx, y, z - rz, x + rx, y, z + rz, x - rx, y, z - rz, x + rx, y, z + rz, x - rx, y, z + rz]
            uv = [0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1]; cl = [1.0, 1.0, 1.0, min(1.0, alpha)] * 6
            vl = self._ombre_vl.get(slot)
            if vl is None: vl = self._ombre_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            self._tracer(self._ombre_tex, vl)
        gl.glDepthMask(gl.GL_TRUE); gl.glDepthFunc(gl.GL_LESS); self.prog['cutoff'] = 0.05

    def _ombre_tex_creer(self):
        # texture CharaTex/common : ellipse d'alpha 96 / 255 aux bords nets (filtre point) ; ici le meme maximum et la meme taille, mais le bord est adouci (ombres « trop brutes »)
        n = 64; yy, xx = np.mgrid[0:n, 0:n]; r = np.hypot((xx + 0.5 - n / 2) / (n / 2), (yy + 0.5 - n / 2) / (n / 2)); k = np.clip((r - 0.45) / 0.55, 0.0, 1.0)
        a = np.zeros((n, n, 4), np.uint8); a[..., 3] = np.round(96 * (1.0 - k * k * (3 - 2 * k))).astype(np.uint8)
        t = self._tex(a, False)
        gl.glBindTexture(t.target, t.id); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR); gl.glTexParameteri(t.target, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        self._ombre_tex = t; self._ombre_vl = {}

    def _infos(self):
        """Lignes d'information (F1) : lieu et fenetre, reglages d'affichage, son, performances. Rien n'est modifiable ici : les reglages sont dans le menu Echap."""
        e = self.moteur.etat; champ = e.partie == MO.PARTIE_CHAMP and e.champ is not None; bataille = e.partie == MO.PARTIE_COMBAT
        lieu = 'Carte du monde' if champ else ('Combat %s' % e.carte if bataille else 'Carte %s' % (e.carte or '?'))
        nom_mode = HD.MODES[self.mode][0] if self.mode < MODE_PP else 'Pixel perfect' + (' x%d%s' % (self._k_pp(), ' (auto)' if self.pp_auto else '') if champ else '')
        decor = 'rendu d\'origine lissé' if self.mode in (0, MODE_PP) else nom_mode
        self.etiquette.text = '%s | fenêtre %d x %d%s | moteur : image %d, partie %#x' % (lieu, self.width, self.height, ' (plein écran)' if self.est_plein else '', self.moteur.images, e.partie)
        self.etiq_hd.text = 'Sprites : %s  |  Décor : %s\nLissage des textures : %s  |  Anticrénelage : %s  |  Zoom de la carte : %d %%\nSon : %s (musique %d %%, bruitages %d %%)' % (
            nom_mode, decor, 'oui' if self.lissage else 'non', 'x%d' % self.msaa if self.msaa else 'non', round(self.champ_zoom * 100),
            ('oui' if self.son.actif else 'non') if self.son.ok else 'indisponible', round(self.son.vol_m * 100), round(self.son.vol_b * 100))

    def _dessiner_aide(self):
        """Lignes d'information en haut a gauche (F1). Dessinees aussi pendant les ecrans noirs et l'effet de debut de combat : sans cela elles clignotent a chaque changement de scene."""
        if not self.aide: return
        self._infos()
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        stats = self.stats and bool(self.ecarts)
        if stats:
            if self.n % 10 == 0 or not self.etiq_stats.text: self.etiq_stats.text = '%.0f images/s | moteur %.1f pas/s (%.1f ms) | pire image %.0f ms | dessin Python %.1f ms' % (len(self.ecarts) / max(1e-6, sum(self.ecarts)), (len(self.pas_t) - 1) / max(1e-6, self.pas_t[-1] - self.pas_t[0]) if len(self.pas_t) > 2 else 0.0, self.dt_moteur * 1000, max(self.ecarts) * 1000, self.dt_dessin * 1000)
        lignes = [self.etiquette, self.etiq_hd] + ([self.etiq_stats] if stats else [])
        marge = self._marge_aide()
        y = self.height - 10
        for l in lignes:                                 # lignes d'information empilees, a la ligne dans la marge laissee libre par la colonne d'interface
            if l.width != marge: l.width = marge
            l.y = y; y -= l.content_height + 3
        bas = y - 3                                       # cadre noir translucide derriere le texte (lisible sur le decor)
        self.cadre_aide.x, self.cadre_aide.y = 4, bas
        self.cadre_aide.width, self.cadre_aide.height = max(l.content_width for l in lignes) + 16, self.height - 4 - bas
        self.cadre_aide.draw()
        for l in lignes: l.draw()


def trouver_defauts():
    """-> (dossier de ce fichier, dossier `jeux/DQ4` des APK francais et des sauvegardes).
    Le projet est autonome : il lit `jeux\\DQ4` dans ce depot (dq4-portage\\jeux\\DQ4), ou le dossier donne par la variable d'environnement DQ4_JEUX.
    Il ne va jamais chercher dans les dossiers des autres projets (patch francais, essai Unity)."""
    ici = os.path.dirname(os.path.abspath(__file__))
    if os.environ.get('DQ4_JEUX'): return ici, os.path.normpath(os.environ['DQ4_JEUX'])
    return ici, os.path.normpath(os.path.join(ici, '..', 'jeux', 'DQ4'))


def main():
    ici, jeux = trouver_defauts()
    ap = argparse.ArgumentParser()
    ap.add_argument('--apk', default=os.path.join(jeux, 'patched_apks'), help='dossier des 3 APK (version francaise)')
    ap.add_argument('--saves-lecture', default=None, help='dossier contenant data1.dat... (par defaut : la plus recente sauvegarde de jeux/DQ4/saves)')
    ap.add_argument('--saves-ecriture', default=os.path.join(ici, 'sauvegardes'))
    ap.add_argument('--cache', default=os.path.join(ici, 'cache'))
    ap.add_argument('--slot', type=int, default=1, help='numero de sauvegarde a charger (1-5), 0 = aucune')
    ap.add_argument('--largeur', type=int, default=None, help='largeur de la fenetre (par defaut : celle du menu Echap, sinon 1280)'); ap.add_argument('--hauteur', type=int, default=None)
    ap.add_argument('--auto-message', type=int, default=0, help='ferme automatiquement le message affiche apres le chargement')
    ap.add_argument('--ui-simple', action='store_true', help='menus simples (zones de texte) au lieu des fenetres d\'origine')
    ap.add_argument('--carte-zoom', type=float, default=None, help='carte du monde : zoom (1 = le heros a la meme taille que dans les villes, ~ 20 tuiles de haut) ; par defaut celui du menu Echap')
    ap.add_argument('--clics', default=None, help='(test) clics de souris simules : "image:x:y,image:x:y:d,..." (d = 1 clic droit, 2 survol sans clic)')
    ap.add_argument('--msg-origine', action='store_true', help='garde la fenetre de message du terrain a sa place d\'origine (portrait) au lieu de la descendre en bas de l\'ecran')
    ap.add_argument('--ui-pos', default='centre', choices=['centre', 'droite', 'gauche'], help='position de la colonne d\'interface d\'origine (portrait 450 x 800) dans la fenetre 16/9')
    ap.add_argument('--sans-preparation', action='store_true', help='(test) ne prepare pas le cache des cartes, sprites et monstres en arriere-plan')
    ap.add_argument('--hd', type=int, default=None, help='sprites : 0 originaux (pixels nets), 1 EPX, 2 regions lissees, 3 bicubique, 4 pixel perfect ; par defaut celui du menu Echap')
    ap.add_argument('--sans-son', action='store_true', help='coupe le son pour cette session (le menu Echap permet de le remettre)')
    ap.add_argument('--volume-musique', type=float, default=None, help='volume des musiques (0 a 1) ; par defaut celui du menu Echap')
    ap.add_argument('--volume-bruitages', type=float, default=None, help='volume des bruitages (0 a 1) ; par defaut celui du menu Echap')
    ap.add_argument('--msaa', type=int, default=None, help='anticrenelage materiel (0 = aucun, 4 = x4) ; par defaut celui du menu Echap')
    ap.add_argument('--reglages', default=os.path.join(ici, 'reglages.json'), help='fichier des reglages du joueur (menu Echap : affichage, son, touches)')
    ap.add_argument('--script-combat', default=None, help='(test) touches pendant un combat : "n:masque,..." (n = images depuis le debut du combat)')
    ap.add_argument('--shots-effet', default=None, help='(test) captures a ces images de l\'effet de debut de combat : "1,10,30,..."')
    ap.add_argument('--shots-combat', default=None, help='(test) captures intermediaires a ces images de combat : "30,60,..."')
    ap.add_argument('--images-combat', type=int, default=0, help='(test) prend la capture N images apres le debut d\'un combat')
    ap.add_argument('--force-champ', type=int, default=0, help='(test) force le passage a la carte du monde a cette image')
    ap.add_argument('--touches-test', default=None, help='(test) touches pressees : "image_de_boucle:NOM,..." (noms pyglet : ESCAPE, DOWN, RETURN...)')
    ap.add_argument('--shots-boucle', default=None, help='(test) captures <shot>_b<n>.png a ces images de boucle (menu Echap compris) ; la derniere quitte')
    ap.add_argument('--shot', default=None, help='(test) enregistre une capture puis quitte')
    ap.add_argument('--images', type=int, default=60)
    ap.add_argument('--script', default=None, help='(test) ex. "20:2,30:0" : image:masque de touches')
    a = ap.parse_args()
    reg = RG.Reglages(a.reglages)
    if a.hd is None: a.hd = reg['mode_sprites']
    else: reg['mode_sprites'] = a.hd
    if a.carte_zoom is None: a.carte_zoom = reg['zoom_carte']
    else: reg['zoom_carte'] = a.carte_zoom
    if a.msaa is None: a.msaa = reg['msaa']
    rs = reg['resolution'] if isinstance(reg['resolution'], (list, tuple)) and len(reg['resolution']) == 2 else (1280, 720)
    if a.largeur is None: a.largeur = int(rs[0]) if a.hauteur is None else int(round(a.hauteur * 16 / 9))
    if a.hauteur is None: a.hauteur = int(rs[1]) if a.largeur == int(rs[0]) else int(round(a.largeur * 9 / 16))
    if a.volume_musique is None: a.volume_musique = reg['volume_musique']
    if a.volume_bruitages is None: a.volume_bruitages = reg['volume_bruitages']
    print('Jeu : APK dans %s' % a.apk, flush=True)
    if not os.path.isfile(os.path.join(a.apk, 'base.apk')):
        print('\nLes APK francais sont introuvables.\nMets base.apk, split_config.arm64_v8a.apk et split_UnityDataAssetPack.apk dans :\n   %s\n(et ta sauvegarde dans %s\\saves\\<date>\\data1.dat). Autre dossier : set DQ4_JEUX=chemin\\vers\\jeux\\DQ4' % (os.path.normpath(a.apk), jeux), flush=True)
        sys.exit(1)
    sys.setswitchinterval(0.001)      # le calcul HD en tache de fond ne doit pas retarder le dessin
    if a.saves_lecture is None:
        dossiers = sorted(glob.glob(os.path.join(jeux, 'saves', '*')))
        a.saves_lecture = dossiers[-1] if dossiers else a.saves_ecriture
    if a.script is not None:
        sc = {}; cur = 0; pts = sorted((int(x.split(':')[0]), int(x.split(':')[1], 0)) for x in a.script.split(','))
        a.script = {}
        for n in range(0, 100000):
            if n > a.images + 5: break
            for (i, m) in pts:
                if n >= i: cur = m
            a.script[n] = cur
    cle = lambda t: (int(t[1:].split('+')[0]), int((t[1:].split('+') + ['0'])[1])) if t[:1] == 'c' else int(t)
    a.touches_test = [(cle(x.split(':')[0]), x.split(':')[1]) for x in a.touches_test.split(',')] if a.touches_test else []
    a.shots_boucle = set(cle(x) for x in a.shots_boucle.split(',')) if a.shots_boucle else set()
    if a.shots_combat: a.shots_combat = set(int(x) for x in a.shots_combat.split(','))
    if a.shots_effet: a.shots_effet = set(int(x) for x in a.shots_effet.split(','))
    if a.clics: a.clics = [tuple(int(v) for v in c.split(':')) + (0,) * (4 - len(c.split(':'))) for c in a.clics.split(',')]
    if a.script_combat is not None:
        pts = sorted((int(x.split(':')[0]), int(x.split(':')[1], 0)) for x in a.script_combat.split(','))
        sc = {}; cur = 0
        for n in range(0, 20000):
            for (i, m) in pts:
                if n >= i: cur = m
            sc[n] = cur
        a.script_combat = sc
    Jeu(a, reg)
    pyglet.app.run(interval=0)       # la boucle fixe (Jeu._boucle) tourne avant chaque dessin ; le dessin suit la synchronisation verticale


if __name__ == '__main__':
    main()
