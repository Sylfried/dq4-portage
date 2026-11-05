"""Fenetre PC 16/9 : fait tourner le moteur du jeu et dessine ce qu'il demande (decor, sprites, camera).
La classe `Game` est le coeur (demarrage, boucle, dessin de la scene) ; le reste est range par theme dans les modules voisins (voir docs/code_plan.md)."""


import collections, math, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait as wait_futures
import numpy as np
import pyglet
from pyglet import gl
from pyglet.graphics.shader import Shader
from pyglet.graphics.shader import ShaderProgram
from dq4_pc import paths as CH
from dq4_pc import language as LG
from dq4_pc import sound as SOUND
from dq4_pc.language import N_, tr
from dq4_pc.battle import battle_speed as VC
from dq4_pc.window import inputs as EN
from dq4_pc.menus import pre_game as AP
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.menus import pause as PA
from dq4_pc.menus import name_entry as SN
from dq4_pc.menus import ui_menu as UI
from dq4_pc.world import data as DO
from dq4_pc.world import hd as HD
from dq4_pc.world import map_tint as TC
from dq4_pc.core import history as HI
from dq4_pc.core import engine as ENGINE
from dq4_pc.core import lying_pose as PC
from dq4_pc.core import load_tracking as SV
from dq4_pc.persistence import settings as RG
from dq4_pc.render import postfx as PF
from dq4_pc.window.constants import (EDGE_ACTIONS, FAST_STEP_BUDGET, CAM_JUMP_ROT, CAM_JUMP_TOWN, TITLE_MAP, CB_MIRROR_X, CH_PX, MODE_PP, ENGINE_STEP,
    COMMON_SFX, SPRITE_SCALE, SPRITE_H, SPRITE_L)
from dq4_pc.window.shaders import FRAG, FRAG_EFFECT, VERTEX, VERTEX_EFFECT
from dq4_pc.window.helpers import adjust_size, camera_free, background_gradient, field_depth_rank, transitions_dwm
from dq4_pc.window.menu_display import MenusMixin
from dq4_pc.window.camera import CameraMixin
from dq4_pc.window.field import FieldMixin
from dq4_pc.window.keyboard_mouse import KeyboardMouseMixin
from dq4_pc.window.capture_effects import CaptureEffectsMixin
from dq4_pc.window.snapshots import SnapshotsMixin
from dq4_pc.window.options import OptionsMixin
from dq4_pc.window.full_screen import FullScreenMixin
from dq4_pc.window.battle_scene import BattleMixin
from dq4_pc.window.title_screen import TitleMixin
from dq4_pc.window.constants import *      # noqa : ces noms restent lisibles par `game.NOM` (tests, outils)
from dq4_pc.window.shaders import *       # noqa
from dq4_pc.window.helpers import *         # noqa


def note_error(text):
    """Ajoute `text` (lignes finies par un retour a la ligne) au journal des erreurs de la fenetre (window_errors.log, dossier des journaux) ; ne leve jamais : -> True si ecrit."""
    try:
        path = CH.FOLDERS.errors_logfile(); os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f: f.write(text)
        return True
    except Exception as ex:
        print('Error not written to the log (%r): %s' % (ex, text.strip()), flush=True); return False


class Game(FullScreenMixin, CameraMixin, FieldMixin, BattleMixin, TitleMixin, MenusMixin, KeyboardMouseMixin, SnapshotsMixin, OptionsMixin, CaptureEffectsMixin, pyglet.window.Window):
    def __init__(self, args, reg=None):
        SV.note('startup', width_px=args.width_px, height_px=args.height_px, full_screen=getattr(args, 'full_screen', 0), shot=bool(args.shot))
        self._logo_logged = False
        self.swallowed = set(); self.alt_cand = False; self.alt_tap = False; self.desktop = None; self._toggling = False       # F11 / Alt + Entree : touches avalees (ni action ni validation), Alt peut-il encore valoir « discussion de groupe » (appui seul), relachement d'Alt seul a traiter ; taille du bureau ; bascule fenetre / plein ecran en cours
        self._ready = False                      # les evenements (souris...) recus pendant la creation de la fenetre sont ignores
        self._logo_touched = False; self._closed = False      # logos d'entree : un appui les saute ; fermeture de la fenetre pendant leur affichage
        self.ext_map = []; self.ext_sky = None; self._M_town = None; self._town_aspect = 16 / 9; self.name_entry = SN.NameEntry(self); self.entry_port = 15; self.license_panel = None; self.saves_screen = None; self.initial_status = None; self.last_device = 'clavier'; self.title_screen = None; self.title_n = 0; self.pre_game_files = {}      # ecran-titre : etat de « Touchez l'ecran » (TapToStart) tant que le port 12 porte la fenetre de type 73
        self.reg = reg or RG.Settings(None)
        self.pause = PA.Pause(self); self.history = HI.History(getattr(args, 'history', None))          # historique : dialogues et combats de la session, favoris dans un fichier a cote de la visionneuse (voir history.py)
        if not args.shot: args.width_px, args.height_px = adjust_size(args.width_px, args.height_px)       # (les captures de test gardent la taille demandee)
        cfg = gl.Config(depth_size=24, double_buffer=True, major_version=3, minor_version=3)       # (l'anticrenelage MSAA n'est plus demande a la fenetre : la scene est dessinee hors ecran, voir postfx.py ; reglable a chaud)
        self.win_mode = self._create_window(args, cfg, RG.valid_window_mode(getattr(args, 'full_screen', 0)))        # mode memorise : la fenetre est creee directement dans ce mode, logos compris : ni fenetre qui apparait puis grandit, ni bascule plus tard
        self.window_size = (args.width_px, args.height_px)         # taille de la fenetre a retrouver en quittant un plein ecran
        self.post = PF.PostFX(self, log=lambda *a: print(*a, flush=True))
        self.args = args
        self._log_window('creation')
        self._wait('Loading the engine...')
        self.mode = RG.valid_sprites_mode(args.hd); self.smoothing = not os.environ.get('DQ_SANS_LISSAGE'); self.aniso = self._anisotropy()          # lissage des textures : toujours actif (ex-reglage « Lissage des textures », retire) ; DQ_SANS_LISSAGE=1 : (debogage) plus proche voisin
        self.pool = ThreadPoolExecutor(max_workers=1); self.hd_jobs = {}; self.scenery_hd = {}; self.scenery_arr = {}; self.map_src = None; self.sprite_vl = {}; self.icon_vl = {}; self.icon_tex = {}; self._menu_tex = None; self._linked_domain = None; self.plans = {}
        self.field_key = None; self.field_tex = None; self.field_tex_icon = None; self.field_nearest = None; self.field_vl = None; self.field_base = None; self.field_icon = None
        self.pattern_n = 0; self.acc_pattern = np.zeros(5, np.int64); self.field_g = None; self.field_pattern = None; self.field_acc_seen = None       # eau animee de la carte du monde
        self._field_view = None       # carte du monde : zone visible (cx, cz, demi-largeur, demi-hauteur en tuiles)
        self.cam_direction = (0, False); self.cam_recenter = False; self.cam_two = False; self.cam_request = 0.0; self.cam_acc = 0.0      # camera : boutons de camera du jeu envoyes au dernier pas (sens, a la souris ?), retour au nord demande, les deux fleches tenues, rotation demandee a la souris pas encore faite (degres), reste de la vitesse (voir camera.py)
        self.mouse = (0, 0); self.mouse_freeze = None; self.objects_orient = None       # action sans effet -> discussion ; orientation des panneaux de decor
        self.mouse_guard = EN.MouseGuard(); self.wheel = EN.WheelGesture()          # entrees : qui a la main (clavier ou souris, voir inputs.py ; remplace mouse_freeze) ; geste du bouton du milieu (clic = recentrer, glisser = tourner la camera)
        self.anchor_effect = {}; self._view_border = None; self._sprites_border = None          # effets-maillages de la ville : emplacement -> (personnage, rapport de profondeur, ecart angulaire) ; (position, droite, haut, avant) de la camera de la visionneuse
        self.n_battle = 0; self.cb_tex = {}; self.cb_vl = {}
        self.ui_tf = {}; self.ui_k = 1.0; self.cur_local = {}; self.cursor_step = {}; self.press_state = None; self.press_node = None; self.hovered = None; self.hover_node = None; self.click_a = self.click_b = False; self.ui_dz = 0.0; self.ui_dzp = {}; self.ui_followers = set()       # souris : bouton appuye (port, numero, manette), clics en attente
        self.cb_mx = CB_MIRROR_X; self.cb_order = int(os.environ.get('DQ_ORDRE', '0'))                 # combat : textures de monstres (m<id>) et maillages
        self.undo_state = None; self.toasts = []; self.quick_save = None; self.combo = [False, False]
        self.helptext = bool(self.reg['infos']); self.helptext_width = 0.0; self.helptext_key = None; self.helptext_border = pyglet.shapes.Rectangle(0, 0, 1, 1, color=(0, 0, 0, 150))      # F1 : lignes d'information en haut a droite + cadre noir translucide
        self.t_startup = time.time()
        self.stats = True; self.spacings = collections.deque(maxlen=120); self.t_prev = None; self.dt_drawing = 0.0
        self.prog = ShaderProgram(Shader(VERTEX, 'vertex'), Shader(FRAG, 'fragment'))
        self.program_effect = ShaderProgram(Shader(VERTEX_EFFECT, 'vertex'), Shader(FRAG_EFFECT, 'fragment'))
        self.program_gradient = None; self.gradient_vl = None       # fond en degrade des villes (#111) : programme et quadrilatere plein ecran, crees au premier besoin
        self.effect_tex = None; self.sim_effect = None; self.effect_vl = None; self.ref_effect = None; self.effect_tex_ready = False      # effet de debut de combat : capture de l'ecran, simulation, sommets
        self.data = DO.Data(None, args.cache, log=lambda *a: print(*a, flush=True))
        self.backgrounds = TC.Backgrounds(self.data, log=lambda *a: print(*a, flush=True)); self.tz = TC.TzKeys(self.data, log=lambda *a: print(*a, flush=True)); self._gl_tint = None        # teinte du decor (paquet 33) : textures « tz_ » exclues ; derniere valeur du uniforme `tint`
        self._start_engine(args)
        self._wait('Loading the save...')
        self.data.apk = self.engine.apk_data
        self.prep_stop = threading.Event(); self.prep_proc = None
        self.hud = HM.Buttons(self); self.hud_decl = 0; self.map_view = 1; self.map_open = False; self.map_two_views = False; self.map_toggle = False; self.damage_count = []; self._tex_count = None
        if not args.sans_preparation:           # extrait en arriere-plan cartes, sprites et monstres pas encore en cache : plus de lecture du gros paquet de donnees en pleine partie
            self._launch_preparation(args.cache)
        self.sound = SOUND.Sound(self.engine.apk_data, args.cache, log=lambda *a: print(*a, flush=True), music_volume=args.music_volume, sfx_volume=args.sfx_volume, active=bool(self.reg['son']) and not args.sans_son,
                           logfile=lambda t: note_error('--- %s: sound: %s ---\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), t)))
        self.sound.preload(COMMON_SFX); self.sound.preload_music()
        self._sound_opt = None; self._t_preview = 0.0; self.apply_mix(initial=True); self.apply_text(); self.apply_game(); self.engine.scroll_callback = self._adopt_scroll; self.apply_scroll()
        self.key_list = pyglet.window.key.KeyStateHandler(); self.push_handlers(self.key_list)
        self.map_name = None; self.scenery_background = None; self.map_vl = []; self.tex_gl = {}; self._tex_outlines = []; self.sprite_tex = {}; self.palettes = None; self.pam_gl = {}
        self.map_pos = {}; self.spans = {}; self.names = {}; self.objects = None; self.bounds_x = None
        self.fbx_cache = {}; self.fbx_player = {}           # modeles 3D animes (fbx.py : le dragon du titre) : numero -> {'etat', 'm', ...} ; emplacement -> lecteur d'animation
        self.tag_label = pyglet.text.Label('', x=10, y=self.height - 10, anchor_y='top', font_size=11, color=(255, 255, 255, 255), multiline=True, width=600)
        self.lbl_stats = pyglet.text.Label('', x=10, y=self.height - 50, anchor_y='top', font_size=10, color=(255, 230, 150, 255), multiline=True, width=600)
        self.lbl_hd = pyglet.text.Label('', x=10, y=self.height - 30, anchor_y='top', font_size=10, color=(200, 220, 255, 255), multiline=True, width=600)
        if args.slot:
            ok = self.engine.load_save(args.slot)
            print('save %d loaded: yes' % args.slot if ok else 'save %d loaded: NO (file data%d.dat not found or invalid in %s)' % (args.slot, args.slot, args.saves_read), flush=True)
            if ok:      # on laisse le moteur lancer la carte sauvegardee avant le premier affichage
                for _ in range(6): self.engine.step(0, 0)
                self._wait('Loading the map...')
                e = self.engine.state
                if e.game_map: self._load_map(e.game_map)      # les chargements lourds se font ici, pas pendant le jeu
                for sp in list(e.sprites.values()): self._sheet(sp['id'], self.mode)
                e.sounds = [x for x in e.sounds if x[0] == 37][-1:]      # les bruitages du chargement sont perdus, la musique de la carte reste
        self.n = 0; self._reported_hooks = 0; self._heap_level = 0; self.dt_engine = 0.0; self.pad_prev = 0; self.rep = {}; self.prev_action = {}
        self.msg_key = None; self.msg_img = None; self.msg_spr = None; self.msg_h = 0
        self.lbl_menu = {}; self.focus_vu = None; self.menu_to_release = None
        self.ui_render = None; self.ui_g = None; self.ui_msg = None; self.canvas_key = None
        if not args.ui_simple: self._init_ui()
        # boucle a pas fixe : le moteur avance exactement a 30 Hz (comme FixedUpdate de l'original) quelle que soit la cadence d'affichage, et l'image affichee est calculee entre deux pas
        self.acc = 0.0; self.t_loop = None; self.alpha = 1.0; self.prev = None; self.step_times = collections.deque(maxlen=60)
        self.n_loop = 0; self.base_c = {}
        self.fixed_test = bool(args.shot) and not os.environ.get('DQ_TEMPS_REEL')         # (test) un pas par image affichee, sans horloge ni interpolation ; DQ_TEMPS_REEL=1 : horloge reelle (vitesse, course)
        pyglet.clock.schedule(self._loop)      # execute avant le dessin des fenetres (pyglet.app.run(interval=0))
        self._ready = True
        SV.note('constructor finished')

    # ---- mode de la fenetre : 0 fenetre, 1 plein ecran (sans bordure, a la resolution du bureau : l'affichage du moniteur ne change jamais)
    WINDOW_TITLE = N_('Dragon Quest IV - portage PC (essai)')          # (affiche par full_screen.py avec tr)

    @staticmethod
    def _simulated_failure(mode):
        """(test) DQ_SIM_ECHEC=1 (ou 0, ou 1,0) : la creation / la bascule vers ce mode (1 plein ecran, 0 fenetre) echoue, pour essayer les replis."""
        if str(mode) in os.environ.get('DQ_SIM_ECHEC', '').split(','): raise RuntimeError('simulated failure (DQ_SIM_ECHEC)')

    def _init_ui(self):
        """Fenetres de menu d'origine (mise en page lue dans le code Unity du jeu) ; sans le fichier cache/ui_layout.json on garde les menus simples."""
        a = self.args; lay = os.path.join(a.cache, 'ui_layout.json')
        if not os.path.exists(lay):
            print('Menus: original layout missing (%s) -> simple menus. Run tools\\generate_ui.bat to create it.' % lay, flush=True); return
        if not UI.prepare_resources(a.apk, a.cache, log=lambda *x: print(*x, flush=True)): return
        try:
            from PIL import Image
            ml = UI.PageLayout(lay, os.path.join(a.cache, 'ui_frameData.bin'))
            sheets = {0: np.array(Image.open(os.path.join(a.cache, 'ui_MenuTexture.png')).convert('RGBA')), 1: np.array(Image.open(os.path.join(a.cache, 'ui_Button.png')).convert('RGBA'))}
            if 'hyodai1' in self.pre_game_files: sheets['hyodai1'] = np.array(Image.open(self.pre_game_files['hyodai1']).convert('RGBA'))      # bandeau des titres de chapitre (type 12)
            self.ui_render = UI.Render(ml, sheets, os.path.join(a.cache, 'ui_font.otf')); self.ui_g = UI.Manager(ml); self.engine.ui.obs = self.ui_g; self.ui_g.proj = self._ui_monster_x; self.ui_g.replay(self.engine.ui)
            if ml.message: self.ui_msg = UI.MessageWindow(ml)
            print(('Menus: original layout loaded (%d types, message window).' if self.ui_msg else 'Menus: original layout loaded (%d types).') % len(ml.types), flush=True)
        except Exception as e:
            print('Menus: original layout unusable (%r) -> simple menus.' % (e,), flush=True); self.ui_render = None; self.ui_g = None

    def _start_engine(self, args):
        """Le moteur se charge dans un fil pendant que les logos d'entree (Boot.Logo : SQUARE ENIX, ArtePiazza) passent, comme sur le mobile ou ils couvrent le chargement ; un appui saute le logo courant.
        Pas de logos pour un lancement direct sur une sauvegarde (--slot N), les captures de test (sauf --logos) ni avec --sans-logos."""
        res = {}
        def load():
            try: res['m'] = ENGINE.Engine(args.apk, args.saves_read, args.saves_write)
            except BaseException as ex: res['e'] = ex
        fil = threading.Thread(target=load, daemon=True, name='moteur'); fil.start()
        self.pre_game_files = AP.paths(args.cache)
        if len(self.pre_game_files) < len(AP.RESOURCES) and not args.sans_preparation: AP.prepare(args.apk, args.cache, log=lambda *a: print(*a, flush=True)); self.pre_game_files = AP.paths(args.cache)      # premiere fois : les images du titre sont extraites avant les logos (le moteur se charge pendant ce temps)
        logos = AP.Logos(self.pre_game_files) if self.pre_game_files and not args.sans_logos and (args.logos or (not args.shot and not args.slot)) else None
        if logos is not None and not logos.ok: logos = None
        t0 = time.perf_counter(); logo_count = 0; worst_logo = 0.0
        SV.note('logo loop', logos=logos is not None)
        while (logos is not None and not logos.finished) or fil.is_alive():
            if self._closed: sys.exit(0)
            self.switch_to(); self.dispatch_events()
            t = time.perf_counter(); worst_logo = max(worst_logo, t - t0); dt = min(t - t0, 0.1); t0 = t; logo_count += 1
            gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear(); gl.glViewport(0, 0, *self.get_framebuffer_size())
            if logos is not None and not logos.finished:
                if self._logo_touched: logos.touch()
                logos.do_update(dt); logos.draw_all(self.width, self.height)
            else: time.sleep(0.02)           # (le moteur se charge encore : ecran noir, sans texte)
            self._logo_touched = False
            self.flip()
            if not self._logo_logged: self._logo_logged = True; self._log_window('1st frame shown (logos)')
        fil.join()
        SV.note('logos and engine finished', frames=logo_count, worst_gap_ms=round(1000 * worst_logo))
        if 'e' in res: raise res['e']
        self.engine = res['m']; self.engine.anim_duration = self._anim_duration

    def _wait(self, text):
        """Ecran noir, sans aucun texte (le texte, lui, va dans la console) : la fenetre reste vivante pendant les chargements du demarrage."""
        print(text, flush=True)
        try:
            self.switch_to(); gl.glClearColor(0, 0, 0, 1); self.clear()
            self.flip(); self.dispatch_events()
        except Exception: pass
        SV.note('wait (black frame)', text=text)

    def _launch_preparation(self, cache):
        """Preparation du cache dans un processus a part, a priorite basse (data.py en ligne de commande) : dans un thread, ses extractions ralentissaient le jeu. Repli : thread."""
        import subprocess
        try:
            kw = {'creationflags': 0x00004000} if os.name == 'nt' else {'preexec_fn': lambda: os.nice(10)}              # BELOW_NORMAL_PRIORITY_CLASS / nice
            kw['env'] = dict(os.environ, DQ4_LANGUE=LG.current_language())              # (D-238 : le processus de preparation parle la langue de l'outil, pas celle de l'ordinateur)
            self.prep_proc = subprocess.Popen([sys.executable, '-m', 'dq4_pc.world.data', self.engine.apk_data, cache], stdin=subprocess.PIPE, cwd=CH.ROOT, **kw)
        except Exception as ex:
            print('Cache preparation: separate process failed (%r), running inside the game.' % (ex,), flush=True)
            threading.Thread(target=self.data.prepare, args=(self.prep_stop,), daemon=True, name='preparation-cache').start()

    def on_close(self):
        if not self._ready: self._closed = True; return           # fermeture pendant les logos : le constructeur s'arrete
        self.reg.store(); self.history.store(True); self.sound.shutdown()
        p = getattr(self, 'prep_proc', None)
        if p is not None:
            try: p.stdin.close()
            except Exception: pass
        super().on_close()

    if sys.platform == 'win32':
        try:
            @pyglet.window._PlatformEventHandler(0x0106)          # WM_SYSCHAR : le caractere de Alt + Entree. Sans ce gestionnaire, Windows (DefWindowProc) fait entendre sa « tonalite d'erreur » a chaque Alt + Entree. Les autres Alt + touche restent a Windows.
            def _event_syschar(self, msg, wParam, lParam): return 0 if wParam == 13 else None
        except Exception: pass

    def pause_game(self, yes):
        """Menu « Paramètres » (Echap) ouvert (oui) ou ferme. Le jeu continue de tourner derriere lui, sans aucune entree (voir `tick`), sur toutes les pages (#178) ; une page de Pause.FROZEN_PAGES (vide) l'arreterait (moteur et son : `_sync_freeze`, a chaque image).
        A la fermeture, les touches deja tenues ne comptent pas comme un nouvel appui."""
        self.acc = 0.0; self.t_loop = None
        if not yes:
            if self._game_frozen: self._game_frozen = False; self.sound.set_paused(False)
            self.pad_prev = self.pad(); self.prev_action = {a: self._held(a) for a in EDGE_ACTIONS}; self.rep = {}; self.hovered = None; self.press_state = None; self.hover_node = None
            self.mouse_guard.keyboard(self.mouse)             # le pointeur ne choisit rien dans les menus du jeu tant qu'il ne s'est pas ecarte de sa position d'avant (la selection au clavier ne doit pas sauter ; voir entrees.MouseGuard)

    _focus_lost = False                                               # la fenetre n'a plus le focus : le jeu et le son sont geles (#235, sondage du 04/11/2026 : « pause a chaque perte de focus ») ; voir on_deactivate / on_activate et _boucle

    def on_deactivate(self):
        """La fenetre perd le focus (Alt + Tab, clic sur une autre fenetre ou un autre ecran, minimisation) : le jeu s'arrete (`_loop`), la musique et les bruitages se mettent en pause (Sound.lose_focus, comme Sound.SystemPause de l'original) et les boutons de la souris tenus sont relaches (le relachement hors de la fenetre n'arrive jamais : camera a la molette, croix a l'ecran, bouton appuye)."""
        self._focus_lost = True
        if not self._ready: return                # (pendant la creation de la fenetre, rien n'existe encore : `_loop` gele le jeu et met le son en pause des qu'elle tourne)
        try: self.sound.lose_focus(True)
        except Exception as ex: print('Sound: pausing on focus loss failed (%r)' % (ex,), flush=True)
        self.wheel.cancel(); self.press_state = None; self.hovered = None; self.hud.dpad_drop(); self.hud.press_state = None; self._camera_oublier()          # (rotation demandee a la souris, retour au nord en attente : pas apres coup)

    def on_activate(self):
        """La fenetre reprend le focus : le son repart la ou il s'etait arrete, le jeu reprend sans rattraper le temps passe (horloge remise a zero, comme a la fermeture du menu) et les touches deja tenues ne comptent pas comme un nouvel appui."""
        self._focus_lost = False
        if not self._ready: return
        try: self.sound.lose_focus(False)
        except Exception as ex: print('Sound: resuming on focus return failed (%r)' % (ex,), flush=True)
        self.acc = 0.0; self.t_loop = None
        if self._ready:
            self.pad_prev = self.pad(); self.prev_action = {a: self._held(a) for a in EDGE_ACTIONS}; self.rep = {}
            self.mouse_guard.keyboard(self.mouse)

    def quit_game(self):
        """Menu Echap > Quitter > Oui (et « Quitter » du menu de depart) : la meme fermeture que la croix de la fenetre (reglages, historique, son ; aucune sauvegarde de partie : comme le jeu d'origine, l'automatique n'est ecrite qu'a l'arrivee sur une carte, voir docs/technical-notes-dq4-port.md)."""
        self.on_close(); pyglet.app.exit()

    def back_to_title_possible(self):
        """La ligne « Revenir à l'écran titre » du menu Pause n'est active qu'en ville et sur la carte du monde (hors ecran-titre) : la, la boite d'origine (Engine.request_return_to_title) recoit les touches et les clics."""
        return self.engine.state.part in (ENGINE.PART_TOWN, ENGINE.PART_FIELD) and getattr(self, 'map_name', None) != TITLE_MAP and self.engine.back_to_title_state is None

    def back_to_title(self):
        """Menu Pause > « Revenir à l'écran titre » : le menu Pause est deja ferme ; le moteur ouvre la boite d'origine du jeu (son texte, Oui / Non) ; « Oui » lance son retour au titre, avec son fondu
        (Engine.request_return_to_title). Seul chemin de retour au titre du jeu."""
        self.engine.request_return_to_title()

    _sfx_this_frame = None                                                  # bruitages deja lances pendant l'image affichee en cours quand le combat est accelere (None : pas de filtre ; voir _boucle et battle_speed.sounds_to_play)

    _game_frozen = False                                                  # le moteur et le son sont-ils arretes derriere le menu ? (voir _sync_freeze)

    def _sync_freeze(self):
        """Arret du son et de l'horloge du moteur quand le menu passe sur une page qui arrete le jeu (Pause.FROZEN_PAGES), reprise quand il la quitte ; au retour, pas de rattrapage du temps passe."""
        stop = self.pause.freezes_game()
        if stop != self._game_frozen:
            self._game_frozen = stop; self.sound.set_paused(stop); self.acc = 0.0; self.t_loop = None

    def _loop(self, dt):
        """Avance le moteur par pas de 1/30 s (horloge reelle, au plus 3 pas de rattrapage par image affichee ; un blocage plus long est oublie) puis fixe alpha, la fraction du pas en cours."""
        self.n_loop += 1
        if self.args.keys_test or self.args.shots_loop: self._test_keys()
        if self.args.options_test: self._options_test()
        if self._focus_lost:
            if not self.sound.out_of_focus: self.sound.lose_focus(True)
            self.acc = 0.0; self.t_loop = None; self.alpha = 1.0; return          # fenetre sans focus : le moteur est arrete (le son : Sound.lose_focus), l'image reste celle du dernier pas ; au retour, pas de rattrapage (on_activate)
        if os.environ.get('DQ_ATTENDRE_HD') and self.hd_jobs: wait_futures(list(self.hd_jobs.values()))      # (test) captures reproductibles : attend la fin des calculs HD en tache de fond
        if self.pause.opened:
            self.pause.do_update(); self._sync_freeze()
            if self.pause.freezes_game(): self.acc = 0.0; self.t_loop = None; self.alpha = 1.0; return        # page de FROZEN_PAGES (aucune depuis #178) : le moteur est arrete ; sinon il tourne sans entree (tick)
        t = time.perf_counter()
        dt = 0.0 if self.t_loop is None else t - self.t_loop
        self.t_loop = t
        if self.fixed_test:
            self._step(); self.alpha = 1.0; return
        f = self._speed_factor(); in_battle = self._battle_clock() and f > 1.0
        self.engine.clock_speed = f          # temps de jeu de la sauvegarde sur l'heure reelle, marche et combat (#239 : le moteur n'en compte qu'une part des pas quand f > 1, voir Engine._game_time_hooks)
        self.engine.walking_speed = 1.0 if self._battle_clock() else f          # marche acceleree : les rencontres aleatoires par seconde suivent (1 + a) / 2 et non a (crochet du compteur du moteur, voir encounters.py) ; en combat, rien
        self._sfx_this_frame = set() if in_battle else None            # combat accelere : un meme bruitage n'est lance qu'une fois par image affichee (voir VC.sounds_to_play) ; sa vitesse de lecture ne change pas
        self.acc, n, cut = VC.advance_time(self.acc, dt, f, self._do_battle_step if in_battle else self._terrain_step, time.perf_counter, ENGINE_STEP, FAST_STEP_BUDGET)      # (tolerance de 15 %, rattrapage et budget de calcul : voir battle_speed.avancer)
        self.alpha = max(0.0, min(1.0, self.acc / ENGINE_STEP))

    def _speed_factor(self):
        """Facteur de vitesse de l'horloge du jeu quand le heros marche (reglages : vitesse de marche, accelerateur tant que sa touche est tenue). Seulement sur le terrain (ville, donjon, carte du monde),
        direction tenue, sans message ni menu ni combat ni effet d'ecran, ni evenement du jeu (verrou du joueur, Global.Flag 4) : quand le jeu a la main, son rythme prime sur le reglage. Un fondu seul (flag 1, joueur libre) n'empeche plus l'acceleration (#107) : le fondu d'arrivee d'une carte dure 30 images alors que le heros marche deja
        depuis la 12e (mesure sur le vrai moteur) ; avant, l'accelerateur ne marchait pas pendant cette seconde. Meme chose au retour d'un combat (#127) : le fondu de retour dure 30 images, le joueur est verrouille jusqu'a l'image 11 puis libre
        (le heros marche des l'image 13, mesure sur le vrai moteur) ; avant, `State.battle_transition` coupait l'acceleration pendant les 30 images, soit 0,6 s de marche normale malgre la touche de course tenue. Pendant le fondu de sortie, le joueur est verrouille (flag 4) : rien n'y change. Le moteur fait alors plus de pas par seconde (voir _boucle) : le heros, les PNJ et les animations vont plus vite ensemble,
        les compagnons gardent leur distance (l'historique des positions avance au meme rythme) et le taux de rencontre suit la distance parcourue (il compte les pas)."""
        R = self.reg; eng = self.engine; e = eng.state
        if e.effect is not None or getattr(e, 'screen_effect', None) is not None: return 1.0          # effet d'ecran de la classe Capture (voyage, lampe, Riremito : le moteur attend sa fin) ; cascade d'entree en combat : horloge du jeu (sa duree suit « Vitesse de transition », en images du moteur : Engine._start_battle_effect) ; ni vitesse de combat, ni de marche, ni accelerateur
        if self._battle_clock(): return VC.factor(R['vitesse_combat'], True)          # combat, des la fin de la cascade (ecran noir, fondu d'arrivee, message « X apparait ») jusqu'au fondu de fin compris : « Vitesse de combat » seule (Manuel et Normal : 1, Rapide : 2, Très rapide : 3) ; ni la vitesse de marche ni le multiplicateur de l'accélérateur ne s'y appliquent
        if self.pause.opened: return 1.0          # menu « Paramètres » : pas de marche acceleree (aucune direction n'est envoyee au jeu)
        if e.transition_guard > 0: return 1.0          # entre deux fondus d'un combat (le moteur change de scene 1 a 3 images plus tard) : horloge du jeu. Le fondu de RETOUR a la carte, lui, n'est plus coupe d'office (#127) : seul le verrou du joueur (plus bas) compte, comme pour le fondu d'arrivee sur une carte (#107)
        if R['vitesse_marche'] == 1.0 and R['vitesse_accel'] == 1.0: return 1.0
        if e.part == ENGINE.PART_BATTLE or e.part in ENGINE.MINIGAME_PARTS or eng.msg_visible or eng.active_menu() is not None or e.effect is not None or getattr(e, 'screen_effect', None) is not None or e.load_wait is not None: return 1.0          # casino, bestiaire : jamais de marche acceleree (les fleches tenues y servent aux menus)
        if not (self.pad() & (ENGINE.UP | ENGINE.DOWN | ENGINE.LEFT | ENGINE.RIGHT)): return 1.0
        if eng.flags() & ENGINE.PLAYER_LOCKED_FLAG: return 1.0       # le jeu a la main (scene, evenement sans message, fondu de sortie) : son rythme est le sien, la direction tenue n'y change rien ; un fondu seul (arrivee sur une carte, joueur libre) n'y compte plus (#107)
        f = float(R['vitesse_marche'])
        if self._held('accel') or self.hud.dpad_run(): f *= float(R['vitesse_accel'])          # course : touche d'accelerateur tenue, ou croix a l'ecran tenue au bord de son anneau (hud_mobile.TRAVEL_THRESHOLD)
        return max(0.25, min(8.0, f))

    def player_control(self):
        """Le joueur a-t-il la main sur son personnage ? Oui seulement sur le terrain (ville, donjon, tour, carte du monde), quand le jeu n'a verrouille ni le joueur (evenement, scene, discussion avec un PNJ, fondu de sortie :
        Global.Flag 4, la meme condition que la marche acceleree, voir _speed_factor), sans message, sans menu du jeu (commandes, boutique, Divers...), sans effet d'ecran ni chargement, et hors combat (partie
        « combat », cascade d'entree, ecran noir qui attend la scene du combat, entre deux fondus d'un combat). Un fondu seul (arrivee sur une carte, retour de combat, joueur libre) n'y compte pas (#107, #127)."""
        eng = self.engine; e = eng.state
        if e.part not in (ENGINE.PART_TOWN, ENGINE.PART_FIELD) or self._battle_clock() or e.transition_guard > 0: return False
        if eng.msg_visible or eng.active_menu() is not None: return False
        return not (eng.flags() & ENGINE.PLAYER_LOCKED_FLAG)

    def history_possible(self):
        """L'historique (touche H, ligne « Historique » du menu Paramètres) n'est accessible que quand le joueur a la main sur son personnage (#187) : ni pendant un combat, ni quand le jeu prend la main (dialogue, scene, evenement,
        fondu de sortie, menu du jeu), ni a l'ecran titre."""
        return self.title_screen is None and self.player_control()

    def _history_key(self):
        """Touche de l'historique : ouvre la page si le joueur a la main, sinon rien (aucun message : le joueur n'a pas a en etre informe, #194 ; la touche est toujours acquittee, elle ne sert qu'a cela)."""
        if self.history_possible(): self.pause.open_menu('historique')

    def _terrain_step(self):
        """Un pas du moteur hors combat accelere (marche, accelerateur). Renvoie False quand la transition d'un combat vient de commencer pendant ce pas (effet d'ecran de debut rendu par une rencontre) : VC.avancer s'arrete la
        et le reste de l'image reprend a l'horloge du jeu ; sans cela, les pas restants du rattrapage d'une marche acceleree raccourciraient le debut de la cascade."""
        e = self.engine.state; before = e.effect is not None
        self._step()
        return before or e.effect is None

    def _test_keys(self):
        """(test) touches pressees a une image de boucle n, ou "cN+k" = k images de boucle apres que le combat a atteint N images : 'n:NOM' (NOM = nom de touche pyglet ;
        +NOM / -NOM = maintenue / relachee ; @x@y = clic de souris (@x@y@2 : survol seul) ; %x%y &x&y *x*y = appui / glisser / relachement du bouton du milieu) ; captures '<shot>_<n>.png' ; la derniere capture quitte."""
        a = self.args
        def instant(n):                                         # numero d'image de boucle ou l'evenement n a lieu (None si pas encore connu)
            if isinstance(n, int): return n
            if n[0] not in self.base_c and self.n_battle == n[0] and self.n_battle > 0: self.base_c[n[0]] = self.n_loop
            return self.base_c[n[0]] + n[1] if n[0] in self.base_c else None
        for ev in list(a.keys_test):
            n, name_str = ev
            if instant(n) != self.n_loop: continue
            a.keys_test.remove(ev); n = self.n_loop
            if name_str[0] == '@':                                  # @x@y : clic gauche en (x, y) pixels depuis le haut a gauche ; @x@y@1 : clic droit ; @x@y@2 : survol seul
                v = [int(t) for t in name_str[1:].split('@')] + [0]; x, y = v[0], self.height - v[1]
                self.on_mouse_motion(x, y, 0, 0)
                if v[2] != 2: self.on_mouse_press(x, y, pyglet.window.mouse.RIGHT if v[2] else pyglet.window.mouse.LEFT, 0); a.keys_test.append((n + 3, '~@%d@%d' % (v[0], v[1])))
            elif name_str[0] == '!': x, y = [int(t) for t in name_str[1:].split('!')]; self.on_mouse_motion(x, self.height - y, 0, 0); self.on_mouse_press(x, self.height - y, pyglet.window.mouse.LEFT, 0)      # !x!y : appui sans relachement automatique (relachement : ~@x@y)
            elif name_str[0] == '~': x, y = [int(t) for t in name_str[2:].split('@')]; self.on_mouse_release(x, self.height - y, pyglet.window.mouse.LEFT, 0)
            elif name_str[0] == '^': x, y = [int(t) for t in name_str[1:].split('^')]; self.on_mouse_drag(x, self.height - y, 0, 0, pyglet.window.mouse.LEFT, 0)      # ^x^y : souris deplacee bouton enfonce
            elif name_str[0] == '%': x, y = [int(t) for t in name_str[1:].split('%')]; self.on_mouse_motion(x, self.height - y, 0, 0); self.on_mouse_press(x, self.height - y, pyglet.window.mouse.MIDDLE, 0)      # %x%y : appui du bouton du milieu (la molette) ; &x&y : pointeur deplace bouton du milieu enfonce ; *x*y : relachement
            elif name_str[0] == '&': x, y = [int(t) for t in name_str[1:].split('&')]; self.on_mouse_drag(x, self.height - y, 0, 0, pyglet.window.mouse.MIDDLE, 0)
            elif name_str[0] == '*': x, y = [int(t) for t in name_str[1:].split('*')]; self.on_mouse_release(x, self.height - y, pyglet.window.mouse.MIDDLE, 0)
            elif name_str[0] == '$': self.dispatch_event('on_text', name_str[1:])                                                                                   # $texte : caracteres tapes
            elif name_str[0] in '+-': self.dispatch_event('on_key_press' if name_str[0] == '+' else 'on_key_release', getattr(pyglet.window.key, name_str[1:]), self._mod_alt_test())
            else: self.dispatch_event('on_key_press', getattr(pyglet.window.key, name_str), self._mod_alt_test()); a.keys_test.append((n + 3, '-' + name_str))       # appui court : relache 3 images plus tard
        for n in list(a.shots_loop):
            if instant(n) == self.n_loop:
                a.shots_loop.remove(n); self.dispatch_event('on_draw'); self.flip()
                name_n = ('b%d' % n) if isinstance(n, int) else ('c%d+%d' % n)
                pyglet.image.get_buffer_manager().get_color_buffer().save(a.shot.replace('.png', '_%s.png' % name_n))
                if os.environ.get('DQ_TEMPS_REEL'): print('STEP engine=%d loop frames=%d t=%.1f' % (self.n, self.n_loop, time.time() - self.t_startup), flush=True)
                if not a.shots_loop: self.on_close(); pyglet.app.exit()

    def _mod_alt_test(self):
        """(test) modificateur Alt d'un evenement de touche simule : le vrai clavier le donne (Alt tenue : MOD_ALT) ; +LALT puis RETURN = Alt + Entree."""
        K = pyglet.window.key
        return K.MOD_ALT if self.key_list[K.LALT] or self.key_list[K.RALT] else 0

    def _options_test(self):
        """(test) --options-test "image:Libelle=valeur;image:Libelle=valeur" : applique des options de la page Affichage a l'image de boucle donnee, par les memes fonctions que le menu Echap (valeur lue comme du JSON : 3, true, 0.5, [1280, 720])."""
        import json
        for ev in list(self.args.options_test):
            n, lib, val = ev
            if n != self.n_loop: continue
            self.args.options_test.remove(ev)
            for entry in self.pause._entries_display():
                if entry.get('l') != lib: continue
                v = json.loads(val)
                if isinstance(v, list): v = tuple(v)
                (entry['set'](v) if entry['t'] == 'choix' else entry['saisie'](float(v))); print('OPTION %s = %s (frame %d)' % (lib, val, n), flush=True)

    def _step(self, mute=False):
        self.prev = self._snapshot()
        self.step_times.append(time.perf_counter())
        t0 = time.perf_counter()
        self.tick(ENGINE_STEP, mute)
        self._anchor_effects(self.engine.state)
        self._log_timing('pas', t0)

    def _log_timing(self, kind, t0):
        """(test) DQ_TEMPS_IMAGES=<fichier> : journal « genre image-de-boucle image-du-moteur duree-en-ms » de chaque pas du moteur et de chaque dessin (repere les blocages d'un premier affichage :
        texture ou modele charge a la volee)."""
        f = os.environ.get('DQ_TEMPS_IMAGES')
        if f:
            with open(f, 'a') as fh: fh.write('%s %d %d %.1f\n' % (kind, self.n_loop, self.engine.frames, 1000.0 * (time.perf_counter() - t0)))

    def _snapshot(self):
        """Etat du pas qui vient de finir : positions des personnages et de la camera, pour l'interpolation."""
        e = self.engine.state
        tup = lambda v: None if v is None else tuple(float(x) for x in v)
        return dict(cle=(e.part, e.game_map), ret=getattr(e, 'loading', None) is not None, sp={k: tup(s['pos']) for k, s in e.sprites.items() if s['pos'] is not None},
                    cam_pos=tup(e.cam_pos), cam_cible=tup(e.cam_target), champ=tup(e.field['cam']) if e.field and e.field['cam'] else None)

    def _interpolate(self):
        """Remplace, le temps d'un dessin, les positions des personnages et de la camera (carte du monde, villes) par celles de l'instant entre le pas precedent et le pas actuel ;
        un saut (changement de carte, deplacement force) n'est pas interpole. Renvoie de quoi tout remettre en place."""
        pr, a, e = self.prev, self.alpha, self.engine.state
        saved = []
        if pr is None or a >= 1.0 or e.part == ENGINE.PART_BATTLE or pr['cle'] != (e.part, e.game_map) or pr.get('ret', False) != (getattr(e, 'loading', None) is not None): return saved      # (l'image qui leve la retenue d'un chargement n'est pas interpolee depuis la camera de la retenue)
        threshold = 24.0 if e.part == ENGINE.PART_FIELD else CAM_JUMP_TOWN       # pixels de la carte / unites de la ville par pas ; au-dela, c'est un saut
        def between(q, c):
            if q is None or c is None or len(q) != len(c): return None
            d = max(abs(x - y) for x, y in zip(q, c))
            return None if d == 0 or d > threshold else tuple(x + (y - x) * a for x, y in zip(q, c))
        for k, sp in e.sprites.items():
            v = between(pr['sp'].get(k), sp['pos'])
            if v is not None: saved.append((sp, 'pos', sp['pos'], False)); sp['pos'] = v
        cam = self._interpolate_camera(pr, a) if e.part != ENGINE.PART_FIELD else None          # (ville : la cible, et la camera autour d'elle quand elle tourne ; carte du monde : camera de la carte, plus bas)
        if cam is not None:
            for name_str, v in zip(('cam_pos', 'cam_target'), cam): saved.append((e, name_str, getattr(e, name_str), True)); setattr(e, name_str, v)
        if e.field and e.field['cam']:
            v = between(pr['champ'], e.field['cam'])
            if v is not None: saved.append((e.field, 'cam', e.field['cam'], False)); e.field['cam'] = v
        return saved

    def _interpolate_camera(self, pr, a):
        """(position, cible) de la camera de la ville entre le pas precedent `pr` et le pas actuel, a la fraction `a`, ou None (rien n'a bouge, ou coupure : changement de carte, plan de scene, angle regle d'un coup). La cible suit le deplacement ; la camera tourne
        autour d'elle (boutons de camera du jeu, scenes) : on interpole sa position RELATIVE a la cible, en cap (par le plus court chemin) et en rayon, pour que la rotation reste lisse entre deux pas du moteur (a 30 Hz, un cran de rotation deplace la camera de
        1,7 unite : plus que le seuil d'un saut sur une seule coordonnee) ; un deplacement relatif de plus de CAM_JUMP_ROT fois la distance en un pas est une coupure."""
        e = self.engine.state
        p0, c0, p1, c1 = pr['cam_pos'], pr['cam_cible'], e.cam_pos, e.cam_target
        if any(v is None for v in (p0, c0, p1, c1)) or not (len(p0) == len(c0) == len(p1) == len(c1) == 3): return None
        p0, c0, p1, c1 = (np.array(v, float) for v in (p0, c0, p1, c1))
        if not ((p1 != p0).any() or (c1 != c0).any()): return None
        if np.abs(c1 - c0).max() > CAM_JUMP_TOWN: return None
        r0, r1 = p0 - c0, p1 - c1
        h0, h1 = math.hypot(r0[0], r0[2]), math.hypot(r1[0], r1[2])
        if np.abs(r1 - r0).max() > max(CAM_JUMP_TOWN, CAM_JUMP_ROT * max(h0, h1)): return None
        c = c0 + (c1 - c0) * a
        if min(h0, h1) < 1e-6: r = r0 + (r1 - r0) * a
        else:
            a0, a1 = math.atan2(r0[0], r0[2]), math.atan2(r1[0], r1[2]); da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            h = h0 + (h1 - h0) * a; ang = a0 + da * a
            r = np.array([h * math.sin(ang), r0[1] + (r1[1] - r0[1]) * a, h * math.cos(ang)])
        return tuple(float(x) for x in c + r), tuple(float(x) for x in c)

    def on_draw(self):
        self._drawing_count = getattr(self, '_drawing_count', 0) + 1
        if self._drawing_count == 1:
            self._log_window('1st game frame')
            if getattr(self, 'dwm_cut', False): pyglet.clock.schedule_once(lambda dt: transitions_dwm(self, True), 2.0)
        if self._drawing_count <= 90 or self._drawing_count % 120 == 0: self._check_real_size()
        saved = self._interpolate(); t0 = time.perf_counter(); self._drawing_kind = '?'
        try: self._draw()
        finally:
            for obj, name_str, old, attr in saved:
                if attr: setattr(obj, name_str, old)
                else: obj[name_str] = old
            self._log_timing('dessin', t0)
            self._absorb_blocking(t0)
            if SV.ACTIVE: self._track_drawing(t0)

    def _absorb_blocking(self, t0):
        """Une image tres longue (plus de 4 pas du moteur : 133 ms) parmi les 3 qui suivent un chargement de carte (textures du decor et des personnages, shaders, rendu hors ecran : premiere image d'une scene) ne doit pas
        etre rattrapee : sans cela le moteur refait d'un coup 3 pas (VC.avancer) et le fondu d'entree saute d'autant (a l'ecran : l'image apparait deja a moitie fondue). L'horloge du moteur repart de zero ; le temps
        du blocage est perdu (ecran de chargement). Limites : une machine lente (images de 100 ms et plus) ne fige pas le jeu, seul un vrai blocage est absorbe, au plus 3 fois par chargement."""
        e = self.engine.state; lookup_key = e.loaded_maps
        if lookup_key != getattr(self, '_absorb_key', None): self._absorb_key = lookup_key; self._absorb_n = 0
        self._absorb_n += 1
        if self._absorb_n <= 3 and time.perf_counter() - t0 > 4 * ENGINE_STEP: self.t_loop = None

    def _track_drawing(self, t0):
        """(diagnostic, DQ_SUIVI) une ligne par image dessinee pendant les 12 premieres images et pendant les 16 images qui suivent un chargement de carte ou un changement de partie : ce qui a ete dessine (`_drawing_kind` :
        scene, noir de chargement...), l'etat de la scene (camera, personnages places), l'opacite des deux plans de fondu, la retenue du dessin (`State.loading`)."""
        e = self.engine.state; lookup_key = (e.loaded_maps, e.part)
        if lookup_key != getattr(self, '_tracking_key', None): self._tracking_key = lookup_key; self._tracking_n = 0
        n = getattr(self, '_tracking_n', 99)
        if self._drawing_count <= 12 or n < 16:
            places = sum(1 for sp in e.sprites.values() if sp['pos'] is not None)
            SV.note('draw', n=self._drawing_count, img=self.engine.frames, kind=self._drawing_kind, part=hex(e.part), game_map=e.game_map, loaded=self.map_name, camera=SV.rounded(e.cam_pos, 1), characters='%d/%d' % (places, len(e.sprites)),
                     fade='%.2f/%d' % (e.fade['a'], e.fade['n']), background='%.2f/%d' % (e.background_fade['a'], e.background_fade['n']), retained=getattr(e, 'loading', None) is not None, ms=round(1000 * (time.perf_counter() - t0), 1))
        self._tracking_n = n + 1

    def _note_state_failure(self, what, console_what, ex):
        """Un etat instantane (raccourci chiffre, Ctrl + chiffre) n'a pas pu etre enregistre ou charge : une ligne dans la console et dans le journal des erreurs, et le petit message a l'ecran (D-230)."""
        text = '--- %s: %s failed: %r ---\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), console_what, ex)
        print(text, end='', flush=True); note_error(text)
        self.toast(tr('%s impossible : %r') % (what, ex))

    def _report_write_failures(self, core):
        """Sauvegarde que le moteur n'a pas pu ecrire (GameCore.h_fclose, apres deux essais, #198) : l'ancien fichier est intact et le jeu continue ; petit message a l'ecran (D-230) et ligne dans le journal des erreurs."""
        lines, core.write_failures = core.write_failures, None
        text = ''.join('--- %s: save failed: %s ---\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), l) for l in lines)
        print(text, end='', flush=True); note_error(text)
        self.toast(tr('Sauvegarde impossible : le jeu continue (détails dans window_errors.log)'), duration=6.0)

    def _watch_heap(self, core):
        """Tas du moteur (ENG-01, audit du 04/11/2026 : « Core.malloc » avance toujours, « h_free » ne libere rien, 256 Mo en tout ; environ 480 combats ou 7 000 chargements de carte, soit des heures de jeu) : le moteur s'arreterait d'un coup
        a 256 Mo. Une ligne du journal des erreurs le note a 200 Mo (78 %), puis a 240 Mo (94 %) (aucun message a l'ecran depuis #267), une fois par palier (de nouveau si le tas redescend, par exemple apres le chargement
        d'un etat). Fermer puis relancer le jeu remet la memoire a zero ; le jeu ecrit sa sauvegarde automatique (data5) a chaque arrivee sur une carte, rien n'est ecrit ici : un etat instantane garderait le tas plein."""
        u = core.heap_used(); level = 2 if u >= core.HEAP_CRITICAL else (1 if u >= core.HEAP_ALERT else 0)
        if level > self._heap_level:
            pc = round(100.0 * u / core.HEAP_SIZE)
            note_error('--- %s: engine memory at %d %% (%d MB of %d MB) ---\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), pc, u >> 20, core.HEAP_SIZE >> 20))
        self._heap_level = level

    def _report_missing_hooks(self, eng):
        """Reglages du moteur que l'apk utilise n'a pas laisses s'installer (Engine._manque : autre version du moteur que celle etudiee) : le jeu tourne avec le comportement d'origine pour ces points. Une ligne par point dans le journal
        des erreurs (aucun message a l'ecran depuis #267), une seule fois (les points trouves plus tard, apres le chargement d'un etat, sont annonces a leur tour)."""
        new_ones = eng.missing_hooks[self._reported_hooks:]; self._reported_hooks = len(eng.missing_hooks)
        text = ''.join('--- %s: engine setting not applied: %s ---\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), l) for l in new_ones)
        note_error(text)

    def tick(self, dt, mute=False):
        """Un pas du moteur (30 par seconde d'horloge de jeu). `mute` : pas supplementaire d'un combat accelere pendant que le moteur attend le joueur (menu, message qui attend une touche) : le moteur avance (animations des monstres,
        fenetres, minuteries) sans aucune touche ni clic, ceux-ci restant lus au rythme normal (voir _do_battle_step)."""
        p = self.args.script.get(self.n, self.pad()) if self.args.script is not None else self.pad()
        if self.args.slot and self.args.auto_message and self.n < 112:
            # (test) ferme le message d'accueil automatiquement
            p = ENGINE.A if (70 <= self.n <= 72 or 88 <= self.n <= 90) else 0
        if self.args.battle_script is not None and self.n_battle > 0: p = self.args.battle_script.get(self.n_battle, 0)
        if self.args.force_champ and self.n == self.args.force_champ: self.engine.start_field()
        if os.environ.get('DQ_SPR') and self.n == 100: print('SPRITES', {k: (sp['id'], tuple(round(float(x), 2) for x in sp['pos']) if sp['pos'] is not None else None, sp.get('pose'), sp.get('dir'), sp.get('vis', True)) for k, sp in self.engine.state.sprites.items()}, 'icons', self.engine.state.icons, flush=True)
        if os.environ.get('DQ_VILLE') and self.n == 30: self.engine.start_town(os.environ['DQ_VILLE'])        # (test) charge cette ville ou ce donjon
        if self.args.clicks:                                                # (test) clics simules : image:x:y[:d] (d = clic droit), x et y en pixels depuis le haut a gauche ; appui a l'image, relachement 3 images plus tard
            for c in self.args.clicks:
                if c[3] == 2:                                              # d = 2 : survol sans clic
                    if self.n == c[0]: self.on_mouse_motion(c[1], self.height - c[2], 0, 0)
                    continue
                if self.n == c[0]: (self.on_mouse_press(c[1], self.height - c[2], pyglet.window.mouse.RIGHT if c[3] else pyglet.window.mouse.LEFT, 0))
                if self.n == c[0] + 3: self.on_mouse_release(c[1], self.height - c[2], pyglet.window.mouse.LEFT, 0)
        p, decl = (0, 0) if (mute or self.pause.opened) else self._entries(p)          # menu « Paramètres » ouvert : le jeu tourne mais ne recoit ni touche ni clic (les touches du menu ne font pas marcher le heros)
        eng = self.engine
        if os.environ.get('DQ_CAMV') and self.n % int(os.environ['DQ_CAMV']) == 0: self._camv(eng)
        if os.environ.get('DQ_DEBUG') and (p or decl): print('n=%d p=%#x decl=%#x msg=%s active=%s' % (self.n, p, decl, eng.msg_visible, eng.active_menu()), flush=True)
        t0 = time.time(); eng.step(p, decl); self.dt_engine = time.time() - t0
        self._camera_after_step(eng)          # rotation de camera demandee a ce pas : crans de plus selon la vitesse reglee ou le glissement (camera.py)
        if len(eng.missing_hooks) > self._reported_hooks: self._report_missing_hooks(eng)
        self._watch_heap(eng.core)          # tas du moteur presque plein (ENG-01)
        if eng.core.write_failures: self._report_write_failures(eng.core)          # une sauvegarde n'a pas pu etre ecrite (#198) : le jeu continue, le joueur est prevenu
        self.history.do_update(eng)          # dialogues et combats de ce pas -> historique (voir history.py)
        if eng.request_pause: eng.request_pause = False; self.pause.open_menu()          # bouton « Paramètres » du menu Divers : le menu Pause s'ouvre a la place des reglages d'origine du jeu (Engine._divert_params)
        self._update_title()
        for code, *_ in eng.ui.system:
            if code == 999: self.pause.open_menu('quitter')            # MenuPortSendQuit : retour sur le menu de depart = quitter l'application (ApplicationQuit : question Oui / Non)
        eng.ui.system = []
        if self.ui_g: self.ui_g.tick()                     # animations des fenetres d'origine, une fois par image du jeu
        if eng.ui.damage:                                   # nombres de degats sur les monstres (HoppingNumber) : un par coup
            for ch, h, dm in eng.ui.damage: self.damage_count.append(dict(ch=ch, h=h, dm=dm, t0=eng.frames))
            eng.ui.damage = []
        if os.environ.get('DQ_FLAG') and self.n % int(os.environ['DQ_FLAG']) == 0: print('FLAG n=%d %#x part=%s msg=%s menu=%s cam=%s>%s' % (self.n, eng.flags(), eng.state.part, eng.msg_visible, eng.active_menu(), None if eng.state.cam_pos is None else tuple(round(float(x), 2) for x in eng.state.cam_pos), None if eng.state.cam_target is None else tuple(round(float(x), 2) for x in eng.state.cam_target)), flush=True)
        if eng.state.part == ENGINE.PART_FIELD and eng.state.field is not None: self._advance_patterns()
        self.sound.image = self.n
        if eng.state.sounds: self.sound.events(VC.sounds_to_play(eng.state.sounds, self._sfx_this_frame), engine_frame=eng.frames); eng.state.sounds = []
        self.sound.tick()
        game = eng.game_options()[:2]
        if game != self._sound_opt: self._sound_opt = game; self.sound.set_mix(game={'musique': SOUND.game_option_volume(game[0]), 'effets': SOUND.game_option_volume(game[1])})        # options « volume » de la fenetre Parametres du jeu
        if os.environ.get('DQ_ETAT') and self.n % 25 == 0: print('STATE n=%d part=%#x map=%s field=%s p=%#x' % (self.n, eng.state.part, eng.state.game_map, None if eng.state.field is None else eng.state.field['cam'], p), flush=True)
        e = self.engine.state
        self._map_objects()
        self.n += 1
        self.n_battle = self.n_battle + 1 if self.engine.state.part == ENGINE.PART_BATTLE else 0
        if self.args.shots_effect and e.effect is not None and e.effect['n'] in self.args.shots_effect and self.args.shot:       # (test) captures pendant l'effet de debut de combat
            self.dispatch_event('on_draw'); self.flip()
            pyglet.image.get_buffer_manager().get_color_buffer().save(self.args.shot.replace('.png', '_e%d.png' % e.effect['n']))
        if self.args.shots_battle and self.n_battle in self.args.shots_battle and self.args.shot:       # (test) captures intermediaires pendant un combat
            self.dispatch_event('on_draw'); self.flip()
            pyglet.image.get_buffer_manager().get_color_buffer().save(self.args.shot.replace('.png', '_%d.png' % self.n_battle))
            print('battle', self.n_battle, 'engine frame', self.engine.frames, 'msg type', getattr(self.ui_msg, 'type', None), [(k, len(m['v']), m['pos']) for k, m in sorted(self.engine.state.meshes.items())], flush=True)
        if self.args.shot and (self.n >= self.args.frames or (self.args.images_combat and self.n_battle >= self.args.images_combat)):
            self.dispatch_event('on_draw'); self.flip()
            pyglet.image.get_buffer_manager().get_color_buffer().save(self.args.shot)
            print('screenshot:', self.args.shot, [(q, 'cur', f['cur'], list(f['cases'].items())[:3]) for q, f in self.engine.ui.visible_ones()], self.engine.active_menu(), self.engine.msg_visible, flush=True); pyglet.app.exit()

    def _draw(self):
        self._draw_scene()
        if self.quick_save is not None and not self.pause.opened:       # raccourci chiffre : l'etat et la miniature sont pris sur l'image qui vient d'etre dessinee
            n, self.quick_save = self.quick_save, None
            try:
                t = self._clone_thumbnail(); png = self._png_thumbnail(t); t.delete(); self.save_state(n, png); self.toast(tr('État %d enregistré') % n)
            except Exception as ex: self._note_state_failure(tr('Enregistrement de l\'état %d') % n, 'Saving savestate %d' % n, ex)
        if not self.pause.opened: self.hud.draw_all(self.hud.visible_ones())
        if self.pause.opened:
            if self.pause.wants_thumbnail: self.pause.mini_tex = self._clone_thumbnail(); self.pause.wants_thumbnail = False       # le jeu sans le menu, pour la miniature des etats (copie sur la carte graphique : pas de relecture qui bloque)
            self.pause.draw_all()
        if self.toasts and time.time() < self.toasts[0][1]:                # message bref en haut de l'ecran (sauvegardes seulement, D-230)
            k = max(0.75, self.height / 900.0); gl.glDisable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            label = self._lbl(self.toasts[0][0], 16 * k, (255, 255, 255, 255)); w = label.content_width + 28 * k; h = 36 * k
            r = pyglet.shapes.Rectangle((self.width - w) / 2, self.height - 24 * k - h, w, h, color=(0, 0, 0)); r.opacity = 170; r.draw()
            label.x = (self.width - label.content_width) / 2; label.y = self.height - 24 * k - h + 11 * k; label.draw()

    def _draw_scene(self):
        t_start = time.perf_counter()
        if self.t_prev is not None: self.spacings.append(t_start - self.t_prev)
        self.t_prev = t_start
        e = self.engine.state
        if os.environ.get('DQ_CARTE_TEST'):                                  # (test) DQ_CARTE_TEST="nom;x,y,z;cx,cy,cz" : montre une carte de ville/grotte avec une camera fixe (animations de decor)
            trial_name, pc, cc = os.environ['DQ_CARTE_TEST'].split(';')
            e.part = 0; e.game_map = trial_name; e.field = None; e.background = (0.0, 0.0, 0.0); e.top_background = e.bottom_background = None; e.cam_free = False
            if os.environ.get('DQ_CARTE_SANS_SPR'): e.sprites.clear()                          # (test) sans les personnages du moteur (le heros se superposerait aux objets etudies)
            e.cam_pos = tuple(float(v) for v in pc.split(',')); e.cam_target = tuple(float(v) for v in cc.split(','))
            if os.environ.get('DQ_CARTE_DEPL'):                              # (test) DQ_CARTE_DEPL="dx,dy,dz" : la camera se deplace de ce vecteur a chaque image affichee (scintillement en mouvement)
                dv = [float(v) * self.n_loop for v in os.environ['DQ_CARTE_DEPL'].split(',')]
                e.cam_pos = tuple(a + b for a, b in zip(e.cam_pos, dv)); e.cam_target = tuple(a + b for a, b in zip(e.cam_target, dv))
        if e.effect is not None and self.ref_effect is not e.effect: self.ref_effect = e.effect; self.effect_tex_ready = False      # nouvel effet de debut de combat : la premiere image est dessinee normalement puis copiee
        if e.effect is not None and self.effect_tex_ready: self._drawing_kind = 'effet'; self._draw_effect(e.effect); self._draw_helptext(); return
        ef_c = self._capture_state(e)                                            # effet d'ecran de la classe Capture (voyage, lampe, Riremito) : meme principe, mais l'interface reste dessinee par-dessus (capture_effects.py)
        if ef_c is not None and self.capture_ready:
            sim = self._capture_advance(ef_c)
            if sim.render_active or e.black_screen is not None: self._drawing_kind = 'effet d\'ecran'; self._draw_capture_effect(sim); return          # (les deux premieres images, le jeu est encore affiche normalement ; a l'arrivee d'un voyage c'est le noir du depart)
        if e.effect is None and e.load_wait is not None:                # fin de l'effet, scene du combat pas encore arrivee : noir (sinon on verrait la scene d'avant)
            self._drawing_kind = 'noir (attente du combat)'; gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear(); self._draw_helptext(); return
        field = e.part == ENGINE.PART_FIELD and e.field is not None        # carte du monde (tuiles) ou ville (decor 3D)
        cam3d = None                                                        # ville : (droite, haut, avant) de la camera, pour les panneaux des personnages
        retained = getattr(e, 'loading', None) is not None                 # chargement de carte sous un ecran couvert, scene pas encore en place : on ne dessine que le noir et les fondus (State.update_loading)
        if not field and e.game_map and e.game_map != self.map_name:
            self._load_map(e.game_map); self.t_loop = None              # chargement synchrone (plusieurs dixiemes de seconde) : le temps passe n'est pas rattrape par le moteur (le fondu d'entree garde sa duree, au lieu de sauter 3 pas en une image)
        background = e.background
        if e.part == ENGINE.PART_BATTLE and not any(background) and not os.environ.get('DQ_FOND_ESTIME'): background = self.backgrounds.color(self.map_src) or self.scenery_background      # fond du combat = bg_color du decor charge (FETC, BackColor.SetColor de cmd_fld_load) ; estimation en attendant la liste / DQ_FOND_ESTIME=1 : (test) l'ancienne estimation
        elif e.part == ENGINE.PART_BATTLE and self.scenery_background and not any(background): background = self.scenery_background
        gl.glClearColor(background[0], background[1], background[2], 1.0)
        self.clear()
        is_battle = e.part == ENGINE.PART_BATTLE and e.cam_pos is not None and e.cam_rot is not None
        if retained or (e.black_screen is not None and ef_c is None) or (e.part == ENGINE.PART_FIELD and e.field is None) or (not field and not is_battle and e.part != ENGINE.PART_BATTLE and (e.game_map or '').startswith('btl_')):
            # carte du monde pas encore envoyee, ou combat fini et scene suivante pas encore arrivee : on ne montre pas la scene d'avant avec la camera d'une autre (image de decor de combat au retour d'une fuite) ;
            # ou chargement de carte pas encore complet (retenu) : le moteur n'a envoye que le decor, la camera et les personnages arrivent a l'image suivante
            self._drawing_kind = 'noir (retenue du chargement)' if retained else 'noir (scene pas arrivee)'; gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear()
            if retained: self.post.begin((0.0, 0.0, 0.0)); self.post.end()                   # (prepare le rendu hors ecran sous le noir : sa creation ne retarde pas la 1re image visible)
            gl.glViewport(0, 0, *self.get_framebuffer_size()); self._draw_fade(True)
            if not (e.game_map or '').startswith('btl_'):               # (fin de combat : les fenetres du combat, comme le statut du groupe en haut a gauche, restent « visibles » dans le moteur un instant : sur l'ecran noir on ne voyait que cette boite)
                self._update_message(); self._draw_message(); self._draw_menus()
            self._draw_fade(); self._draw_helptext(); return
        if not field and not is_battle and (e.cam_pos is None or (e.cam_target is None and not camera_free(e))): self._drawing_kind = 'rien (pas de camera)'; self._draw_helptext(); return
        self._drawing_kind = 'scene'
        gl.glEnable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glViewport(0, 0, *self.post.begin(background))          # scene dessinee hors ecran si un reglage d'affichage le demande (anticrenelage MSAA, nettete, luminosite : postfx.py) ; sinon directement dans la fenetre
        if not field and not is_battle and background_gradient(e.top_background, e.bottom_background): self._paint_background_gradient(e.top_background, e.bottom_background)       # ville : fond de BackColor en degrade (#111)
        aspect = self.width / max(1, self.height)
        if field: M, dh, w, h = self._field_camera(e, aspect); self._update_field(e)
        elif is_battle:
            M, M_scenery = self._battle_camera(e, aspect); self._M_battle = M; dh = np.array([1.0, 0, 0]); w, h = SPRITE_L * SPRITE_SCALE, SPRITE_H * SPRITE_SCALE
        else:
            M, cam3d = self._town_camera(e, aspect)
            if self.objects is not None and self.map_name == e.game_map: self._orient_scenery(cam3d)         # arbres, bougies... : de face a la camera, quelle que soit sa rotation
            # sprites : panneaux verticaux tournes vers la camera (listes de sommets persistantes, une par emplacement)
            fh = np.array([e.cam_target[0] - e.cam_pos[0], 0, e.cam_target[2] - e.cam_pos[2]]); fh /= np.linalg.norm(fh) or 1
            dh = np.cross([0, 1, 0], fh); dh /= np.linalg.norm(dh) or 1
            w, h = SPRITE_L * SPRITE_SCALE, SPRITE_H * SPRITE_SCALE
        up = np.array([0, 0, -h]) if field else np.array([0, h, 0])       # carte du monde : le haut du sprite est le nord (-Z)
        to_draw = []; shadows = []; pp = self.mode == MODE_PP
        corr = self._edge_correction(); C_view = self._view_border[0] if self._view_border is not None else None          # correction des bords : intensite (0 a 1) et position de la camera de la visionneuse
        tilt = self._sprite_tilt()                                         # essai #134 : part de l'inclinaison des verticales du monde prise par les sprites
        rank = {}
        if field: rank = field_depth_rank(e.sprites)      # carte du monde : sprites a plat, tous a la meme hauteur, superposes selon field_depth_rank
        for slot, s in sorted(e.sprites.items()):
            if s['pos'] is None or s['col'][3] < 0.02 or not s.get('vis', True): continue      # paquet 14 : Chara.SetVisible
            f = self._sheet(s['id'] - 4096 if (field and s['id'] >= 4096) else s['id'], self.mode)
            if not f: continue
            nl = f['nl']
            col, row = s['pose'] % f.get('cols', 3), s['dir'] % nl          # (bateau : 12 colonnes de 40 x 40, voir hd.SPECIAL_SHEETS)
            pw, ph = f.get('pw', 1.0), f.get('ph', 1.0)                       # panneau du bateau : 0,8 x 0,8 contre 0,48 x 0,64 pour un personnage
            sleeping = bool(s.get('dort')) and not field and not is_battle and cam3d is not None          # personnage couche (paquet 16) : dessine a plat par lying_pose, voir plus bas
            u0, u1, v0, v1 = HD.uv_cell(f, col, row)                                 # case (col, row) de l'atlas (origine ou HD), gouttieres exclues
            p = np.array([(round(s['pos'][0]) if pp else s['pos'][0]) / CH_PX, 0.04 + rank.get(slot, 0) * 0.0005, (round(s['pos'][1]) if pp else s['pos'][1]) / CH_PX]) if field else np.array(s['pos'], float)       # carte du monde : sprite a plat (vue de dessus), le heros (emplacement 0) au-dessus des autres
            if cam3d is not None:
                # Chara.normalBillboard : le panneau (0,48 x 0,64) prend la rotation de la camera, donc il est de face a l'ecran (pas ecrase par l'inclinaison) ; ses sommets
                # sont decales en profondeur (bas 0,185, haut 0,65 vers la camera, Chara.SystemInit) : une fois a l'ecran il se comporte comme un personnage debout pour le z-buffer
                k = 1.0 if os.environ.get('DQ_SANS_ECHELLE') else min(max(float(s.get('ech', 1.0)), 0.0), 8.0)          # paquet 13, bit 11 : Chara.SetScale (Transform.localScale du panneau, pieds fixes) ; 1,0 presque partout, 0,738 pour le heros et son equipier dans mlb1a, 0,952 dans ev07 (le reste : valeurs de depart d'une image)
                wk, hk = w * k * pw, h * k * ph
                r_, u_, f_ = self._sprite_reference(cam3d, corr); zb, zh = 0.185 / 0.48 * wk, (0.65 - 0.185) / 0.48 * wk       # decalages de profondeur a l'echelle du panneau (le haut penche de 36 degres vers la camera : le panneau est presque vertical dans le monde)
                # Panneau d'origine par defaut depuis #184 (« exactement comme dans le jeu » : voir _edge_correction, _sprite_reference et _town_panel) : le haut du panneau, plus proche, s'ecarte du centre de l'image et le sprite
                # « se penche » vers l'exterieur pres des bords gauche / droit (jusqu'a 15 a 20 degres en 16/9), comme sur le mobile mais plus visible avec le champ du 16/9 ; la correction des bords (bords verticaux, proportions
                # constantes, taille et profondeur inchangees, #134) reste disponible (DQ_CORRECTION_BORDS=100), de meme que le cisaillement (DQ_SPRITE_INCLINAISON, voir _sprite_tilt)
                if sleeping and C_view is not None:
                    # Pose couchee (paquets 16 / 17, Chara.SetSleepPose, shader Custom/CharaSleep ; voir lying_pose.py) : le panneau n'est PAS debout, la correction des bords (qui redresse un panneau debout) ne lui
                    # est jamais appliquee ; vu de dessus, a pleine taille, tourne selon la direction du sommeil, avec la profondeur du corps a plat (z-buffer, recouvrements par un lit, un mur...)
                    ang, qd = s.get('dort_rot', (0.0, 0))
                    qv = PC.vertices(p, ang, qd, float(getattr(e, 'sleeping_height', 0.0)), wk / 0.48, cam3d, C_view)
                    if qv is None: continue
                    a, b, c, d = qv
                else:
                    a, b, c, d = self._town_panel(p, r_, u_, f_, wk, hk, zb, zb + zh, corr, C_view, tilt)
                q = np.array([a, b, c, a, c, d], np.float32).ravel().tolist()
            else:
                kf = float(getattr(e, 'field_scale', 1.0)) if field and slot in getattr(e, 'floats', ()) else 1.0          # paquet 30 : le panneau du ballon (Field.SetFloatingObject) suit l'echelle du terrain, pieds fixes : il garde sa taille a l'ecran (MAP-02)
                a, b = p - dh * w * kf * pw / 2, p + dh * w * kf * pw / 2; upk = up * ph * kf
                q = np.array([a, b, b + upk, a, b + upk, a + upk], np.float32).ravel().tolist()
            uv = [u0, v0, u1, v0, u1, v1, u0, v0, u1, v1, u0, v1]
            cl = list(map(float, s['col'])) * 6
            vl = self.sprite_vl.get(slot)
            if vl is None: vl = self.sprite_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            to_draw.append((slot, f, vl))
            if s.get('ombre', True) and not (sleeping and not s.get('ombre_sep')):       # paquet 15 : le moteur peut masquer l'ombre d'un personnage (bateaux de la carte du monde...) ; couche, l'ombre part 64 sous le sol (Chara.lieBillboard) sauf si elle est separee
                al = float(s['col'][3]) * float(s.get('ombre_a', 1.0))
                if cam3d is not None: shadows.append((slot, np.array(s['ombre_pos'], float) if s.get('ombre_sep') and s.get('ombre_pos') else p, al))
                elif field:
                    oc = s.get('ombre_champ')                      # paquet 15, bit 14 : le moteur donne la position de l'ombre sur la carte du monde (le ballon : plus au sud que ses pieds) ; sinon l'ombre est sous les pieds
                    po = np.array([(round(oc[0]) if pp else oc[0]) / CH_PX, p[1], (round(oc[1]) if pp else oc[1]) / CH_PX]) if oc is not None and len(oc) >= 2 else p
                    shadows.append((slot, po, al))
        icons = self._icons(e, field, is_battle, dh, cam3d)
        if os.environ.get('DQ_PROJ') and self.n_loop % int(os.environ['DQ_PROJ']) == 0: self._dbg_proj(M, e, cam3d, to_draw, icons)
        self._linked_domain = None
        self.prog.use()
        self.prog['mvp'] = tuple(float(x) for x in M.T.ravel()); self.prog['cutoff'] = 0.5; self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0); self.prog['amul'] = 1.0
        self._gl_tint = None; self._set_tint((1.0, 1.0, 1.0))        # (le uniforme vaut 0 tant qu'on ne l'a pas ecrit : tout noir)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        if field: self._paint_field(e)
        elif is_battle:
            self.prog['mvp'] = tuple(float(x) for x in M_scenery.T.ravel())
            self._paint_scenery()
            self.prog['mvp'] = tuple(float(x) for x in M.T.ravel()); self.prog['cutoff'] = 0.05; self.prog['net'] = 1.0
            gl.glDisable(gl.GL_CULL_FACE); gl.glDepthMask(gl.GL_FALSE)         # shaders DssaMonster* : ZWrite Off, Cull Off, ZTest LEqual
            monster_meshes = self._battle_meshes(e)             # reecrit les sommets des monstres/effets (tampons « sales » : pas encore envoyes au GPU)
            self._linked_domain = None                         # force le rebind + commit() au 1er trace : sinon les monstres sortent avec les donnees de l'image precedente
            for tex, tw, th, vl, shader, hd in monster_meshes:
                self.prog['net'] = 0.0 if hd else (2.0 if (pp or not self.smoothing) else 1.0)           # texture agrandie : filtrage doux des mipmaps ; originale : pixels nets (plus proche voisin si le lissage est coupe)
                if shader == 3: gl.glDisable(gl.GL_DEPTH_TEST)                 # DssaCharaTransparent : ZTest Always
                self.prog['tsize'] = (float(tw), float(th)); self._paint(tex, vl)
                if shader == 3: gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glDepthMask(gl.GL_TRUE)
            self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0)
        else:
            self._M_town = M; self._town_aspect = aspect
            if e.part != ENGINE.PART_BESTIARY: self._paint_scenery(True)          # bestiaire : la carte de la ville reste chargee (aucun paquet 0) mais la camera du livre, a 83 unites, n'en voit qu'une tranche (l'eglise, au bord du plan lointain) derriere la liste et la fiche : le livre ne montre que le monstre (paquets 21 / 22)
            if e.fbx: self._paint_fbx(e)               # modeles 3D animes (le dragon du titre) : meme file que le decor opaque
        self.prog['cutoff'] = 0.05
        if shadows and not os.environ.get('DQ_SANS_OMBRE'):
            if cam3d is not None: self._draw_character_shadows(shadows, cam3d)
            elif field: self._draw_field_shadows(shadows, w * CH_PX / 24.0)
        for slot, f, vl in to_draw:
            self.prog['net'] = 0.0 if f['hd'] else (2.0 if (pp or not self.smoothing) else 1.0); self.prog['tsize'] = (float(f['tw']), float(f['th']))
            self._paint(f['t'], vl)       # comme Unity (shader Chara, ZTest normal) : un personnage cache par un decor n'est pas visible du tout
        self.prog['net'] = 2.0 if (pp or not self.smoothing) else 1.0; self.prog['tsize'] = (32.0, 32.0)
        for tex, vl in icons: self._paint(tex, vl)                          # bulles d'icone (Riseup), devant les personnages
        if not field and not is_battle and e.meshes and e.part in (ENGINE.PART_TOWN,) + ENGINE.MINIGAME_PARTS and cam3d is not None:
            # effets-maillages de la ville (paquets 21, 22 : sort Morph, eclaboussures, coups d'epee du prologue, credits et logo du titre), tournes vers la camera. Ils passent APRES les personnages (Custom/Chara : file Transparent,
            # 3000) : DssaChara Transparent+100, DssaMonster0 +150, DssaMonster1 +200, DssaCharaTransparent Overlay-150 (3850, ZTest Always : devant tout, comme les bulles Riseup, de la meme file). Avant, ils etaient dessines
            # avant les personnages : un personnage cache a l'effet qui le recouvre (le nuage du sort Morph passait « derriere » Elisa).
            self.prog['cutoff'] = 0.05; self.prog['net'] = 1.0; self.prog['tsize'] = (1.0, 1.0)
            gl.glDisable(gl.GL_CULL_FACE); gl.glDepthMask(gl.GL_FALSE)
            self._linked_domain = None
            for tex, tw, th, vl, shader, hd in self._battle_meshes(e, np.column_stack(cam3d), True):
                self.prog['net'] = 0.0 if hd else (1.0 if self.smoothing else 2.0)
                if shader == 3: gl.glDisable(gl.GL_DEPTH_TEST)
                self.prog['tsize'] = (float(tw), float(th)); self._paint(tex, vl)
                if shader == 3: gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glDepthMask(gl.GL_TRUE); self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0)
        self.prog.stop()
        gl.glDisable(gl.GL_DEPTH_TEST)
        if e.part != ENGINE.PART_BATTLE and not field: self._draw_vignette()          # (pas sur la carte du monde, entierement en 2D)
        self._draw_fade(True); self.post.end()
        if ef_c is not None and not self.capture_ready:                         # effet Capture qui demarre : la scene (sans interface) est copiee, puis les images normales continuent (le noir d'un voyage en cours couvre tout)
            self._capture_grab(ef_c)
            if e.black_screen is not None: gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear()
        self._draw_damage(e)
        self._update_message(); self._draw_name_entry(); self._draw_message(); self._draw_menus(); self._draw_fade(); self._draw_title(); self._draw_license(); self._draw_saves()
        self.dt_drawing += (time.perf_counter() - t_start - self.dt_drawing) * 0.1
        if e.effect is not None and not self.effect_tex_ready: self._clone_screen(); self.effect_tex_ready = True       # capture de l'ecran du jeu, sans les lignes d'aide
        self._draw_helptext()

    def _info(self):
        """Lignes d'information (F1) : lieu et fenetre, reglages d'affichage, son, performances. Rien n'est modifiable ici : les reglages sont dans le menu Echap."""
        e = self.engine.state; field = e.part == ENGINE.PART_FIELD and e.field is not None; is_battle = e.part == ENGINE.PART_BATTLE
        location = 'Carte du monde' if field else ('Combat %s' % e.game_map if is_battle else 'Carte %s' % (e.game_map or '?'))
        mode_name = HD.MODES[self.mode][0] if self.mode < MODE_PP else 'Pixel perfect'
        scenery = 'rendu d\'origine lissé' if self.mode in (0, MODE_PP) else mode_name
        self.tag_label.text = '%s | fenêtre %d x %d%s | moteur : image %d, partie %#x' % (location, self.width, self.height, ' (plein écran)' if self.is_fullscreen else '', self.engine.frames, e.part)
        self.lbl_hd.text = 'Sprites : %s  |  Décor : %s\nLissage des textures : %s  |  Antialiasing : %s  |  Caméra : rotation %d °\nSon : %s (musique %d %%, bruitages %d %%)' % (
            mode_name, scenery, 'oui' if self.smoothing else 'non', 'x%d' % self.post.msaa if self.post.msaa else 'non', round(self._engine_yaw()),
            ('oui' if self.sound.active else 'non') if self.sound.ok else 'indisponible', round(self.sound.vol_m * 100), round(self.sound.vol_b * 100))
