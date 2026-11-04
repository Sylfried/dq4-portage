"""Fenetre PC 16/9 : fait tourner le moteur du jeu et dessine ce qu'il demande (decor, sprites, camera).
La classe `Jeu` est le coeur (demarrage, boucle, dessin de la scene) ; le reste est range par theme dans les modules voisins (voir docs/plan_du_code.md)."""


import collections, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait as attendre_futures
import numpy as np
import pyglet
from pyglet import gl
from pyglet.graphics.shader import Shader
from pyglet.graphics.shader import ShaderProgram
from dq4_pc import chemins as CH
from dq4_pc import son as SON
from dq4_pc.combat import vitesse_combat as VC
from dq4_pc.fenetre import entrees as EN
from dq4_pc.menus import avant_partie as AP
from dq4_pc.menus import hud_mobile as HM
from dq4_pc.menus import pause as PA
from dq4_pc.menus import saisie_nom as SN
from dq4_pc.menus import ui_menu as UI
from dq4_pc.monde import donnees as DO
from dq4_pc.monde import hd as HD
from dq4_pc.monde import teinte_carte as TC
from dq4_pc.noyau import historique as HI
from dq4_pc.noyau import moteur as MO
from dq4_pc.noyau import pose_couchee as PC
from dq4_pc.noyau import suivi_charge as SV
from dq4_pc.persistance import reglages as RG
from dq4_pc.rendu import postfx as PF
from dq4_pc.fenetre.constantes import (ACT_FRONTS, BUDGET_PAS_RAPIDES, CAM_SAUT_VILLE, CARTE_TITRE, CB_MIROIR_X, CH_PX, MODE_PP, PAS_MOTEUR,
    SE_COURANTS, SPRITE_ECHELLE, SPRITE_H, SPRITE_L)
from dq4_pc.fenetre.shaders import FRAG, FRAG_EFFET, VERT, VERT_EFFET
from dq4_pc.fenetre.aides import ajuster_taille, camera_libre, degrade_fond, rang_profondeur_champ, transitions_dwm
from dq4_pc.fenetre.affichage_menus import MenusMixin
from dq4_pc.fenetre.camera import CameraMixin
from dq4_pc.fenetre.champ import ChampMixin
from dq4_pc.fenetre.clavier_souris import ClavierSourisMixin
from dq4_pc.fenetre.effets_capture import EffetsCaptureMixin
from dq4_pc.fenetre.instantanes import InstantanesMixin
from dq4_pc.fenetre.options import OptionsMixin
from dq4_pc.fenetre.plein_ecran import PleinEcranMixin
from dq4_pc.fenetre.scene_combat import CombatMixin
from dq4_pc.fenetre.titre import TitreMixin
from dq4_pc.fenetre.constantes import *      # noqa : ces noms restent lisibles par `jeu.NOM` (tests, outils)
from dq4_pc.fenetre.shaders import *       # noqa
from dq4_pc.fenetre.aides import *         # noqa


def noter_erreur(texte):
    """Ajoute `texte` (lignes finies par un retour a la ligne) au journal des erreurs de la fenetre (erreurs_fenetre.log, dossier des journaux) ; ne leve jamais : -> True si ecrit."""
    try:
        chemin = CH.DOSSIERS.journal_erreurs(); os.makedirs(os.path.dirname(os.path.abspath(chemin)), exist_ok=True)
        with open(chemin, 'a', encoding='utf-8') as f: f.write(texte)
        return True
    except Exception as ex:
        print('Erreur non notee dans le journal (%r) : %s' % (ex, texte.strip()), flush=True); return False


class Jeu(PleinEcranMixin, CameraMixin, ChampMixin, CombatMixin, TitreMixin, MenusMixin, ClavierSourisMixin, InstantanesMixin, OptionsMixin, EffetsCaptureMixin, pyglet.window.Window):
    def __init__(self, args, reg=None):
        SV.noter('demarrage', largeur=args.largeur, hauteur=args.hauteur, plein_ecran=getattr(args, 'plein_ecran', 0), shot=bool(args.shot))
        self._journal_logo = False
        self.avalees = set(); self.alt_cand = False; self.alt_tap = False; self.bureau = None; self._en_bascule = False       # F11 / Alt + Entree : touches avalees (ni action ni validation), Alt peut-il encore valoir « discussion de groupe » (appui seul), relachement d'Alt seul a traiter ; taille du bureau ; bascule fenetre / plein ecran en cours
        self._pret = False                      # les evenements (souris...) recus pendant la creation de la fenetre sont ignores
        self._logo_touche = False; self._ferme = False      # logos d'entree : un appui les saute ; fermeture de la fenetre pendant leur affichage
        self.carte_ext = []; self.ciel_ext = None; self._M_ville = None; self._aspect_ville = 16 / 9; self.saisie_nom = SN.SaisieNom(self); self.port_saisie = 15; self.licence = None; self.sauv = None; self.statut_depart = None; self.dernier_peripherique = 'clavier'; self.titre = None; self.titre_n = 0; self.ap_fich = {}      # ecran-titre : etat de « Touchez l'ecran » (TapToStart) tant que le port 12 porte la fenetre de type 73
        self.reg = reg or RG.Reglages(None)
        self.pause = PA.Pause(self); self.historique = HI.Historique(getattr(args, 'historique', None))          # historique : dialogues et combats de la session, favoris dans un fichier a cote de la visionneuse (voir historique.py)
        if not args.shot: args.largeur, args.hauteur = ajuster_taille(args.largeur, args.hauteur)       # (les captures de test gardent la taille demandee)
        cfg = gl.Config(depth_size=24, double_buffer=True, major_version=3, minor_version=3)       # (l'anticrenelage MSAA n'est plus demande a la fenetre : la scene est dessinee hors ecran, voir postfx.py ; reglable a chaud)
        self.mode_fen = self._creer_fenetre(args, cfg, RG.mode_fenetre_valide(getattr(args, 'plein_ecran', 0)))        # mode memorise : la fenetre est creee directement dans ce mode, logos compris : ni fenetre qui apparait puis grandit, ni bascule plus tard
        self.taille_fenetre = (args.largeur, args.hauteur)         # taille de la fenetre a retrouver en quittant un plein ecran
        self.post = PF.PostFX(self, log=lambda *a: print(*a, flush=True))
        self.args = args
        self._journal_fenetre('création')
        self._attente('Chargement du moteur...')
        self.mode = RG.mode_sprites_valide(args.hd); self.lissage = not os.environ.get('DQ_SANS_LISSAGE'); self.aniso = self._anisotropie()          # lissage des textures : toujours actif (ex-reglage « Lissage des textures », retire) ; DQ_SANS_LISSAGE=1 : (debogage) plus proche voisin
        self.pool = ThreadPoolExecutor(max_workers=1); self.hd_jobs = {}; self.decor_hd = {}; self.decor_arr = {}; self.carte_src = None; self.sprite_vl = {}; self.icone_vl = {}; self.icone_tex = {}; self._menu_tex = None; self._dom_lie = None; self.plans = {}
        self.champ_cle = None; self.champ_tex = None; self.champ_tex_ico = None; self.champ_nearest = None; self.champ_vl = None; self.champ_base = None; self.champ_ico = None
        self.motif_n = 0; self.motif_acc = np.zeros(5, np.int64); self.champ_g = None; self.champ_pat = None; self.champ_acc_vu = None       # eau animee de la carte du monde
        self._vue_champ = None       # carte du monde : zone visible (cx, cz, demi-largeur, demi-hauteur en tuiles)
        self.souris = (0, 0); self.souris_gel = None; self.objets_orient = None       # action sans effet -> discussion ; orientation des panneaux de decor
        self.garde_souris = EN.GardeSouris()          # entrees : qui a la main (clavier ou souris, voir entrees.py ; remplace souris_gel)
        self.effet_ancre = {}; self._cadre_vue = None; self._cadre_sprites = None          # effets-maillages de la ville : emplacement -> (personnage, rapport de profondeur, ecart angulaire) ; (position, droite, haut, avant) de la camera de la visionneuse
        self.n_combat = 0; self.cb_tex = {}; self.cb_vl = {}
        self.ui_tf = {}; self.ui_k = 1.0; self.cur_local = {}; self.cur_pas = {}; self.appui = None; self.appui_nd = None; self.survol = None; self.survol_nd = None; self.clic_a = self.clic_b = False; self.ui_dz = 0.0; self.ui_dzp = {}; self.ui_suit = set()       # souris : bouton appuye (port, numero, manette), clics en attente
        self.cb_mx = CB_MIROIR_X; self.cb_ordre = int(os.environ.get('DQ_ORDRE', '0'))                 # combat : textures de monstres (m<id>) et maillages
        self.etat_annul = None; self.sauve_rapide = None; self.combo = [False, False]
        self.aide = bool(self.reg['infos']); self.aide_larg = 0.0; self.aide_cle = None; self.cadre_aide = pyglet.shapes.Rectangle(0, 0, 1, 1, color=(0, 0, 0, 150))      # F1 : lignes d'information en haut a droite + cadre noir translucide
        self.t_demarrage = time.time()
        self.stats = True; self.ecarts = collections.deque(maxlen=120); self.t_prec = None; self.dt_dessin = 0.0
        self.prog = ShaderProgram(Shader(VERT, 'vertex'), Shader(FRAG, 'fragment'))
        self.prog_effet = ShaderProgram(Shader(VERT_EFFET, 'vertex'), Shader(FRAG_EFFET, 'fragment'))
        self.prog_degrade = None; self.degrade_vl = None       # fond en degrade des villes (#111) : programme et quadrilatere plein ecran, crees au premier besoin
        self.effet_tex = None; self.effet_sim = None; self.effet_vl = None; self.effet_ref = None; self.effet_tex_prete = False      # effet de debut de combat : capture de l'ecran, simulation, sommets
        self.donnees = DO.Donnees(None, args.cache, log=lambda *a: print(*a, flush=True))
        self.fonds = TC.Fonds(self.donnees, log=lambda *a: print(*a, flush=True)); self.tz = TC.Cles(self.donnees, log=lambda *a: print(*a, flush=True)); self._teinte_gl = None        # teinte du decor (paquet 33) : textures « tz_ » exclues ; derniere valeur du uniforme `teinte`
        self._demarrer_moteur(args)
        self._attente('Chargement de la sauvegarde...')
        self.donnees.apk = self.moteur.apk_donnees
        self.prepa_arret = threading.Event(); self.prepa_proc = None
        self.hud = HM.Boutons(self); self.hud_decl = 0; self.carte_vue = 1; self.carte_ouverte = False; self.carte_deux_vues = False; self.carte_bascule = False; self.nb_degats = []; self._nb_tex = None
        if not args.sans_preparation:           # extrait en arriere-plan cartes, sprites et monstres pas encore en cache : plus de lecture du gros paquet de donnees en pleine partie
            self._lancer_preparation(args.cache)
        self.son = SON.Son(self.moteur.apk_donnees, args.cache, log=lambda *a: print(*a, flush=True), volume_musique=args.volume_musique, volume_bruitages=args.volume_bruitages, actif=bool(self.reg['son']) and not args.sans_son,
                           journal=lambda t: noter_erreur('--- %s : son : %s ---\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), t)))
        self.son.precharger(SE_COURANTS); self.son.precharger_musiques()
        self._opt_son = None; self._t_apercu = 0.0; self.appliquer_mixage(depart=True); self.appliquer_texte(); self.appliquer_jeu(); self.moteur.rappel_defilement = self._adopter_defilement; self.appliquer_defilement()
        self.touches = pyglet.window.key.KeyStateHandler(); self.push_handlers(self.touches)
        self.carte_nom = None; self.fond_decor = None; self.carte_vl = []; self.tex_gl = {}; self._tex_contours = []; self.sprite_tex = {}; self.palettes = None; self.pam_gl = {}
        self.carte_pos = {}; self.plages = {}; self.noms = {}; self.objets = None; self.bornes_x = None
        self.fbx_cache = {}; self.fbx_lect = {}           # modeles 3D animes (fbx.py : le dragon du titre) : numero -> {'etat', 'm', ...} ; emplacement -> lecteur d'animation
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
        self.n = 0; self._crochets_signales = 0; self._tas_niveau = 0; self.dt_moteur = 0.0; self.pad_prec = 0; self.rep = {}; self.act_prec = {}
        self.msg_cle = None; self.msg_img = None; self.msg_spr = None; self.msg_h = 0
        self.etiq_menu = {}; self.focus_vu = None; self.menu_relacher = None
        self.ui_rendu = None; self.ui_g = None; self.ui_msg = None; self.canevas_cle = None
        if not args.ui_simple: self._init_ui()
        # boucle a pas fixe : le moteur avance exactement a 30 Hz (comme FixedUpdate de l'original) quelle que soit la cadence d'affichage, et l'image affichee est calculee entre deux pas
        self.acc = 0.0; self.t_boucle = None; self.alpha = 1.0; self.prec = None; self.pas_t = collections.deque(maxlen=60)
        self.n_boucle = 0; self.base_c = {}
        self.fixe_test = bool(args.shot) and not os.environ.get('DQ_TEMPS_REEL')         # (test) un pas par image affichee, sans horloge ni interpolation ; DQ_TEMPS_REEL=1 : horloge reelle (vitesse, course)
        pyglet.clock.schedule(self._boucle)      # execute avant le dessin des fenetres (pyglet.app.run(interval=0))
        self._pret = True
        SV.noter('constructeur termine')

    # ---- mode de la fenetre : 0 fenetre, 1 plein ecran (sans bordure, a la resolution du bureau : l'affichage du moniteur ne change jamais)
    TITRE_FENETRE = 'Dragon Quest IV - portage PC (essai)'

    @staticmethod
    def _echec_simule(mode):
        """(test) DQ_SIM_ECHEC=1 (ou 0, ou 1,0) : la creation / la bascule vers ce mode (1 plein ecran, 0 fenetre) echoue, pour essayer les replis."""
        if str(mode) in os.environ.get('DQ_SIM_ECHEC', '').split(','): raise RuntimeError('échec simulé (DQ_SIM_ECHEC)')

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
            if 'hyodai1' in self.ap_fich: feuilles['hyodai1'] = np.array(Image.open(self.ap_fich['hyodai1']).convert('RGBA'))      # bandeau des titres de chapitre (type 12)
            self.ui_rendu = UI.Rendu(ml, feuilles, os.path.join(a.cache, 'ui_font.otf')); self.ui_g = UI.Gestionnaire(ml); self.moteur.ui.obs = self.ui_g; self.ui_g.proj = self._ui_x_monstres; self.ui_g.rejouer(self.moteur.ui)
            if ml.message: self.ui_msg = UI.FenetreMessage(ml)
            print('Menus : mise en page d\'origine chargee (%d types%s).' % (len(ml.types), ', fenetre de message' if self.ui_msg else ''), flush=True)
        except Exception as e:
            print('Menus : mise en page d\'origine inutilisable (%r) -> menus simples.' % (e,), flush=True); self.ui_rendu = None; self.ui_g = None

    def _demarrer_moteur(self, args):
        """Le moteur se charge dans un fil pendant que les logos d'entree (Boot.Logo : SQUARE ENIX, ArtePiazza) passent, comme sur le mobile ou ils couvrent le chargement ; un appui saute le logo courant.
        Pas de logos pour un lancement direct sur une sauvegarde (--slot N), les captures de test (sauf --logos) ni avec --sans-logos."""
        res = {}
        def charger():
            try: res['m'] = MO.Moteur(args.apk, args.saves_lecture, args.saves_ecriture)
            except BaseException as ex: res['e'] = ex
        fil = threading.Thread(target=charger, daemon=True, name='moteur'); fil.start()
        self.ap_fich = AP.chemins(args.cache)
        if len(self.ap_fich) < len(AP.RESSOURCES) and not args.sans_preparation: AP.preparer(args.apk, args.cache, log=lambda *a: print(*a, flush=True)); self.ap_fich = AP.chemins(args.cache)      # premiere fois : les images du titre sont extraites avant les logos (le moteur se charge pendant ce temps)
        logos = AP.Logos(self.ap_fich) if self.ap_fich and not args.sans_logos and (args.logos or (not args.shot and not args.slot)) else None
        if logos is not None and not logos.ok: logos = None
        t0 = time.perf_counter(); nb_logo = 0; pire_logo = 0.0
        SV.noter('boucle des logos', logos=logos is not None)
        while (logos is not None and not logos.fini) or fil.is_alive():
            if self._ferme: sys.exit(0)
            self.switch_to(); self.dispatch_events()
            t = time.perf_counter(); pire_logo = max(pire_logo, t - t0); dt = min(t - t0, 0.1); t0 = t; nb_logo += 1
            gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear(); gl.glViewport(0, 0, *self.get_framebuffer_size())
            if logos is not None and not logos.fini:
                if self._logo_touche: logos.toucher()
                logos.maj(dt); logos.dessiner(self.width, self.height)
            else: time.sleep(0.02)           # (le moteur se charge encore : ecran noir, sans texte)
            self._logo_touche = False
            self.flip()
            if not self._journal_logo: self._journal_logo = True; self._journal_fenetre('1re image affichée (logos)')
        fil.join()
        SV.noter('logos et moteur termines', images=nb_logo, pire_ecart_ms=round(1000 * pire_logo))
        if 'e' in res: raise res['e']
        self.moteur = res['m']; self.moteur.duree_anim = self._duree_anim

    def _attente(self, texte):
        """Ecran noir, sans aucun texte (le texte, lui, va dans la console) : la fenetre reste vivante pendant les chargements du demarrage."""
        print(texte, flush=True)
        try:
            self.switch_to(); gl.glClearColor(0, 0, 0, 1); self.clear()
            self.flip(); self.dispatch_events()
        except Exception: pass
        SV.noter('attente (image noire)', texte=texte)

    def _lancer_preparation(self, cache):
        """Preparation du cache dans un processus a part, a priorite basse (donnees.py en ligne de commande) : dans un thread, ses extractions ralentissaient le jeu. Repli : thread."""
        import subprocess
        try:
            kw = {'creationflags': 0x00004000} if os.name == 'nt' else {'preexec_fn': lambda: os.nice(10)}              # BELOW_NORMAL_PRIORITY_CLASS / nice
            self.prepa_proc = subprocess.Popen([sys.executable, '-m', 'dq4_pc.monde.donnees', self.moteur.apk_donnees, cache], stdin=subprocess.PIPE, cwd=CH.RACINE, **kw)
        except Exception as ex:
            print('Preparation du cache : processus a part impossible (%r), dans le jeu.' % (ex,), flush=True)
            threading.Thread(target=self.donnees.preparer, args=(self.prepa_arret,), daemon=True, name='preparation-cache').start()

    def on_close(self):
        if not self._pret: self._ferme = True; return           # fermeture pendant les logos : le constructeur s'arrete
        self.reg.enregistrer(); self.historique.enregistrer(True); self.son.fermer()
        p = getattr(self, 'prepa_proc', None)
        if p is not None:
            try: p.stdin.close()
            except Exception: pass
        super().on_close()

    if sys.platform == 'win32':
        try:
            @pyglet.window._PlatformEventHandler(0x0106)          # WM_SYSCHAR : le caractere de Alt + Entree. Sans ce gestionnaire, Windows (DefWindowProc) fait entendre sa « tonalite d'erreur » a chaque Alt + Entree. Les autres Alt + touche restent a Windows.
            def _event_syschar(self, msg, wParam, lParam): return 0 if wParam == 13 else None
        except Exception: pass

    def pause_jeu(self, oui):
        """Menu « Paramètres » (Echap) ouvert (oui) ou ferme. Le jeu continue de tourner derriere lui, sans aucune entree (voir `tick`), sur toutes les pages (#178) ; une page de Pause.PAGES_FIGEES (vide) l'arreterait (moteur et son : `_synchroniser_gel`, a chaque image).
        A la fermeture, les touches deja tenues ne comptent pas comme un nouvel appui."""
        self.acc = 0.0; self.t_boucle = None
        if not oui:
            if self._jeu_fige: self._jeu_fige = False; self.son.mettre_en_pause(False)
            self.pad_prec = self.pad(); self.act_prec = {a: self._tenue(a) for a in ACT_FRONTS}; self.rep = {}; self.survol = None; self.appui = None; self.survol_nd = None
            self.garde_souris.clavier(self.souris)             # le pointeur ne choisit rien dans les menus du jeu tant qu'il ne s'est pas ecarte de sa position d'avant (la selection au clavier ne doit pas sauter ; voir entrees.GardeSouris)

    _focus_perdu = False                                               # la fenetre n'a plus le focus : le jeu et le son sont geles (#235, sondage du 04/11/2026 : « pause a chaque perte de focus ») ; voir on_deactivate / on_activate et _boucle

    def on_deactivate(self):
        """La fenetre perd le focus (Alt + Tab, clic sur une autre fenetre ou un autre ecran, minimisation) : le jeu s'arrete (`_boucle`), la musique et les bruitages se mettent en pause (Son.perdre_focus, comme Sound.SystemPause de l'original) et les boutons de la souris tenus sont relaches (le relachement hors de la fenetre n'arrive jamais : camera a la molette, croix a l'ecran, bouton appuye)."""
        self._focus_perdu = True
        if not self._pret: return                # (pendant la creation de la fenetre, rien n'existe encore : `_boucle` gele le jeu et met le son en pause des qu'elle tourne)
        try: self.son.perdre_focus(True)
        except Exception as ex: print('Son : pause a la perte du focus impossible (%r)' % (ex,), flush=True)
        self.appui = None; self.survol = None; self.hud.croix_lacher(); self.hud.appui = None

    def on_activate(self):
        """La fenetre reprend le focus : le son repart la ou il s'etait arrete, le jeu reprend sans rattraper le temps passe (horloge remise a zero, comme a la fermeture du menu) et les touches deja tenues ne comptent pas comme un nouvel appui."""
        self._focus_perdu = False
        if not self._pret: return
        try: self.son.perdre_focus(False)
        except Exception as ex: print('Son : reprise au retour du focus impossible (%r)' % (ex,), flush=True)
        self.acc = 0.0; self.t_boucle = None
        if self._pret:
            self.pad_prec = self.pad(); self.act_prec = {a: self._tenue(a) for a in ACT_FRONTS}; self.rep = {}
            self.garde_souris.clavier(self.souris)

    def quitter(self):
        """Menu Echap > Quitter > Oui (et « Quitter » du menu de depart) : la meme fermeture que la croix de la fenetre (reglages, historique, son ; aucune sauvegarde de partie : comme le jeu d'origine, l'automatique n'est ecrite qu'a l'arrivee sur une carte, voir docs/notes-technique-portage-dq4.md)."""
        self.on_close(); pyglet.app.exit()

    def retour_titre_possible(self):
        """La ligne « Revenir à l'écran titre » du menu Pause n'est active qu'en ville et sur la carte du monde (hors ecran-titre) : la, la boite d'origine (Moteur.demander_retour_titre) recoit les touches et les clics."""
        return self.moteur.etat.partie in (MO.PARTIE_VILLE, MO.PARTIE_CHAMP) and getattr(self, 'carte_nom', None) != CARTE_TITRE and self.moteur.retour_titre_etat is None

    def retour_titre(self):
        """Menu Pause > « Revenir à l'écran titre » : le menu Pause est deja ferme ; le moteur ouvre la boite d'origine du jeu (son texte, Oui / Non) ; « Oui » lance son retour au titre, avec son fondu
        (Moteur.demander_retour_titre). Seul chemin de retour au titre du jeu."""
        self.moteur.demander_retour_titre()

    _se_images = None                                                  # bruitages deja lances pendant l'image affichee en cours quand le combat est accelere (None : pas de filtre ; voir _boucle et vitesse_combat.sons_a_jouer)

    _jeu_fige = False                                                  # le moteur et le son sont-ils arretes derriere le menu ? (voir _synchroniser_gel)

    def _synchroniser_gel(self):
        """Arret du son et de l'horloge du moteur quand le menu passe sur une page qui arrete le jeu (Pause.PAGES_FIGEES), reprise quand il la quitte ; au retour, pas de rattrapage du temps passe."""
        arret = self.pause.fige_le_jeu()
        if arret != self._jeu_fige:
            self._jeu_fige = arret; self.son.mettre_en_pause(arret); self.acc = 0.0; self.t_boucle = None

    def _boucle(self, dt):
        """Avance le moteur par pas de 1/30 s (horloge reelle, au plus 3 pas de rattrapage par image affichee ; un blocage plus long est oublie) puis fixe alpha, la fraction du pas en cours."""
        self.n_boucle += 1
        if self.args.touches_test or self.args.shots_boucle: self._touches_test()
        if self.args.options_test: self._options_test()
        if self._focus_perdu:
            if not self.son.hors_focus: self.son.perdre_focus(True)
            self.acc = 0.0; self.t_boucle = None; self.alpha = 1.0; return          # fenetre sans focus : le moteur est arrete (le son : Son.perdre_focus), l'image reste celle du dernier pas ; au retour, pas de rattrapage (on_activate)
        if os.environ.get('DQ_ATTENDRE_HD') and self.hd_jobs: attendre_futures(list(self.hd_jobs.values()))      # (test) captures reproductibles : attend la fin des calculs HD en tache de fond
        if self.pause.ouvert:
            self.pause.maj(); self._synchroniser_gel()
            if self.pause.fige_le_jeu(): self.acc = 0.0; self.t_boucle = None; self.alpha = 1.0; return        # page de PAGES_FIGEES (aucune depuis #178) : le moteur est arrete ; sinon il tourne sans entree (tick)
        t = time.perf_counter()
        dt = 0.0 if self.t_boucle is None else t - self.t_boucle
        self.t_boucle = t
        if self.fixe_test:
            self._pas(); self.alpha = 1.0; return
        f = self._facteur_vitesse(); en_combat = self._horloge_combat() and f > 1.0
        self.moteur.vitesse_horloge = f          # temps de jeu de la sauvegarde sur l'heure reelle, marche et combat (#239 : le moteur n'en compte qu'une part des pas quand f > 1, voir Moteur._crochets_temps_de_jeu)
        self.moteur.vitesse_marche = 1.0 if self._horloge_combat() else f          # marche acceleree : les rencontres aleatoires par seconde suivent (1 + a) / 2 et non a (crochet du compteur du moteur, voir rencontres.py) ; en combat, rien
        self._se_images = set() if en_combat else None            # combat accelere : un meme bruitage n'est lance qu'une fois par image affichee (voir VC.sons_a_jouer) ; sa vitesse de lecture ne change pas
        self.acc, n, coupe = VC.avancer(self.acc, dt, f, self._faire_pas_combat if en_combat else self._pas_terrain, time.perf_counter, PAS_MOTEUR, BUDGET_PAS_RAPIDES)      # (tolerance de 15 %, rattrapage et budget de calcul : voir vitesse_combat.avancer)
        self.alpha = max(0.0, min(1.0, self.acc / PAS_MOTEUR))

    def _facteur_vitesse(self):
        """Facteur de vitesse de l'horloge du jeu quand le heros marche (reglages : vitesse de marche, accelerateur tant que sa touche est tenue). Seulement sur le terrain (ville, donjon, carte du monde),
        direction tenue, sans message ni menu ni combat ni effet d'ecran, ni evenement du jeu (verrou du joueur, Global.Flag 4) : quand le jeu a la main, son rythme prime sur le reglage. Un fondu seul (flag 1, joueur libre) n'empeche plus l'acceleration (#107) : le fondu d'arrivee d'une carte dure 30 images alors que le heros marche deja
        depuis la 12e (mesure sur le vrai moteur) ; avant, l'accelerateur ne marchait pas pendant cette seconde. Meme chose au retour d'un combat (#127) : le fondu de retour dure 30 images, le joueur est verrouille jusqu'a l'image 11 puis libre
        (le heros marche des l'image 13, mesure sur le vrai moteur) ; avant, `Etat.transition_combat` coupait l'acceleration pendant les 30 images, soit 0,6 s de marche normale malgre la touche de course tenue. Pendant le fondu de sortie, le joueur est verrouille (flag 4) : rien n'y change. Le moteur fait alors plus de pas par seconde (voir _boucle) : le heros, les PNJ et les animations vont plus vite ensemble,
        les compagnons gardent leur distance (l'historique des positions avance au meme rythme) et le taux de rencontre suit la distance parcourue (il compte les pas)."""
        R = self.reg; mo = self.moteur; e = mo.etat
        if e.effet is not None or getattr(e, 'effet_ecran', None) is not None: return 1.0          # effet d'ecran de la classe Capture (voyage, lampe, Riremito : le moteur attend sa fin) ; cascade d'entree en combat : horloge du jeu (sa duree suit « Vitesse de transition », en images du moteur : Moteur._debut_effet_combat) ; ni vitesse de combat, ni de marche, ni accelerateur
        if self._horloge_combat(): return VC.facteur(R['vitesse_combat'], True)          # combat, des la fin de la cascade (ecran noir, fondu d'arrivee, message « X apparait ») jusqu'au fondu de fin compris : « Vitesse de combat » seule (Manuel et Normal : 1, Rapide : 2, Très rapide : 3) ; ni la vitesse de marche ni le multiplicateur de l'accélérateur ne s'y appliquent
        if self.pause.ouvert: return 1.0          # menu « Paramètres » : pas de marche acceleree (aucune direction n'est envoyee au jeu)
        if e.garde_trans > 0: return 1.0          # entre deux fondus d'un combat (le moteur change de scene 1 a 3 images plus tard) : horloge du jeu. Le fondu de RETOUR a la carte, lui, n'est plus coupe d'office (#127) : seul le verrou du joueur (plus bas) compte, comme pour le fondu d'arrivee sur une carte (#107)
        if R['vitesse_marche'] == 1.0 and R['vitesse_accel'] == 1.0: return 1.0
        if e.partie == MO.PARTIE_COMBAT or e.partie in MO.PARTIES_MINIJEU or mo.msg_visible or mo.menu_actif() is not None or e.effet is not None or getattr(e, 'effet_ecran', None) is not None or e.attente_charge is not None: return 1.0          # casino, bestiaire : jamais de marche acceleree (les fleches tenues y servent aux menus)
        if not (self.pad() & (MO.HAUT | MO.BAS | MO.GAUCHE | MO.DROITE)): return 1.0
        if mo.drapeaux() & MO.DRAPEAU_JOUEUR_VERROUILLE: return 1.0       # le jeu a la main (scene, evenement sans message, fondu de sortie) : son rythme est le sien, la direction tenue n'y change rien ; un fondu seul (arrivee sur une carte, joueur libre) n'y compte plus (#107)
        f = float(R['vitesse_marche'])
        if self._tenue('accel') or self.hud.croix_course(): f *= float(R['vitesse_accel'])          # course : touche d'accelerateur tenue, ou croix a l'ecran tenue au bord de son anneau (hud_mobile.COURSE_SEUIL)
        return max(0.25, min(8.0, f))

    def controle_joueur(self):
        """Le joueur a-t-il la main sur son personnage ? Oui seulement sur le terrain (ville, donjon, tour, carte du monde), quand le jeu n'a verrouille ni le joueur (evenement, scene, discussion avec un PNJ, fondu de sortie :
        Global.Flag 4, la meme condition que la marche acceleree, voir _facteur_vitesse), sans message, sans menu du jeu (commandes, boutique, Divers...), sans effet d'ecran ni chargement, et hors combat (partie
        « combat », cascade d'entree, ecran noir qui attend la scene du combat, entre deux fondus d'un combat). Un fondu seul (arrivee sur une carte, retour de combat, joueur libre) n'y compte pas (#107, #127)."""
        mo = self.moteur; e = mo.etat
        if e.partie not in (MO.PARTIE_VILLE, MO.PARTIE_CHAMP) or self._horloge_combat() or e.garde_trans > 0: return False
        if mo.msg_visible or mo.menu_actif() is not None: return False
        return not (mo.drapeaux() & MO.DRAPEAU_JOUEUR_VERROUILLE)

    def historique_possible(self):
        """L'historique (touche H, ligne « Historique » du menu Paramètres) n'est accessible que quand le joueur a la main sur son personnage (#187) : ni pendant un combat, ni quand le jeu prend la main (dialogue, scene, evenement,
        fondu de sortie, menu du jeu), ni a l'ecran titre."""
        return self.titre is None and self.controle_joueur()

    def _touche_historique(self):
        """Touche de l'historique : ouvre la page si le joueur a la main, sinon rien (aucun message : le joueur n'a pas a en etre informe, #194 ; la touche est toujours acquittee, elle ne sert qu'a cela)."""
        if self.historique_possible(): self.pause.ouvrir('historique')

    def _pas_terrain(self):
        """Un pas du moteur hors combat accelere (marche, accelerateur). Renvoie False quand la transition d'un combat vient de commencer pendant ce pas (effet d'ecran de debut rendu par une rencontre) : VC.avancer s'arrete la
        et le reste de l'image reprend a l'horloge du jeu ; sans cela, les pas restants du rattrapage d'une marche acceleree raccourciraient le debut de la cascade."""
        e = self.moteur.etat; avant = e.effet is not None
        self._pas()
        return avant or e.effet is None

    def _touches_test(self):
        """(test) touches pressees a une image de boucle n, ou "cN+k" = k images de boucle apres que le combat a atteint N images : 'n:NOM' (NOM = nom de touche pyglet ;
        +NOM / -NOM = maintenue / relachee ; @x@y = clic de souris (@x@y@2 : survol seul) ; %x%y &x&y *x*y = appui / glisser / relachement du bouton du milieu) ; captures '<shot>_<n>.png' ; la derniere capture quitte."""
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
            elif nom[0] == '!': x, y = [int(t) for t in nom[1:].split('!')]; self.on_mouse_motion(x, self.height - y, 0, 0); self.on_mouse_press(x, self.height - y, pyglet.window.mouse.LEFT, 0)      # !x!y : appui sans relachement automatique (relachement : ~@x@y)
            elif nom[0] == '~': x, y = [int(t) for t in nom[2:].split('@')]; self.on_mouse_release(x, self.height - y, pyglet.window.mouse.LEFT, 0)
            elif nom[0] == '^': x, y = [int(t) for t in nom[1:].split('^')]; self.on_mouse_drag(x, self.height - y, 0, 0, pyglet.window.mouse.LEFT, 0)      # ^x^y : souris deplacee bouton enfonce
            elif nom[0] == '%': x, y = [int(t) for t in nom[1:].split('%')]; self.on_mouse_motion(x, self.height - y, 0, 0); self.on_mouse_press(x, self.height - y, pyglet.window.mouse.MIDDLE, 0)      # %x%y : appui du bouton du milieu (la molette) ; &x&y : pointeur deplace bouton du milieu enfonce ; *x*y : relachement
            elif nom[0] == '&': x, y = [int(t) for t in nom[1:].split('&')]; self.on_mouse_drag(x, self.height - y, 0, 0, pyglet.window.mouse.MIDDLE, 0)
            elif nom[0] == '*': x, y = [int(t) for t in nom[1:].split('*')]; self.on_mouse_release(x, self.height - y, pyglet.window.mouse.MIDDLE, 0)
            elif nom[0] == '$': self.dispatch_event('on_text', nom[1:])                                                                                   # $texte : caracteres tapes
            elif nom[0] in '+-': self.dispatch_event('on_key_press' if nom[0] == '+' else 'on_key_release', getattr(pyglet.window.key, nom[1:]), self._mod_alt_test())
            else: self.dispatch_event('on_key_press', getattr(pyglet.window.key, nom), self._mod_alt_test()); a.touches_test.append((n + 3, '-' + nom))       # appui court : relache 3 images plus tard
        for n in list(a.shots_boucle):
            if instant(n) == self.n_boucle:
                a.shots_boucle.remove(n); self.dispatch_event('on_draw'); self.flip()
                nom_n = ('b%d' % n) if isinstance(n, int) else ('c%d+%d' % n)
                pyglet.image.get_buffer_manager().get_color_buffer().save(a.shot.replace('.png', '_%s.png' % nom_n))
                if os.environ.get('DQ_TEMPS_REEL'): print('PAS moteur=%d images boucle=%d t=%.1f' % (self.n, self.n_boucle, time.time() - self.t_demarrage), flush=True)
                if not a.shots_boucle: self.on_close(); pyglet.app.exit()

    def _mod_alt_test(self):
        """(test) modificateur Alt d'un evenement de touche simule : le vrai clavier le donne (Alt tenue : MOD_ALT) ; +LALT puis RETURN = Alt + Entree."""
        K = pyglet.window.key
        return K.MOD_ALT if self.touches[K.LALT] or self.touches[K.RALT] else 0

    def _options_test(self):
        """(test) --options-test "image:Libelle=valeur;image:Libelle=valeur" : applique des options de la page Affichage a l'image de boucle donnee, par les memes fonctions que le menu Echap (valeur lue comme du JSON : 3, true, 0.5, [1280, 720])."""
        import json
        for ev in list(self.args.options_test):
            n, lib, val = ev
            if n != self.n_boucle: continue
            self.args.options_test.remove(ev)
            for en in self.pause._e_affichage():
                if en.get('l') != lib: continue
                v = json.loads(val)
                if isinstance(v, list): v = tuple(v)
                (en['set'](v) if en['t'] == 'choix' else en['saisie'](float(v))); print('OPTION %s = %s (image %d)' % (lib, val, n), flush=True)

    def _pas(self, muet=False):
        self.prec = self._instantane()
        self.pas_t.append(time.perf_counter())
        t0 = time.perf_counter()
        self.tick(PAS_MOTEUR, muet)
        self._ancrer_effets(self.moteur.etat)
        self._mesure('pas', t0)

    def _mesure(self, genre, t0):
        """(test) DQ_TEMPS_IMAGES=<fichier> : journal « genre image-de-boucle image-du-moteur duree-en-ms » de chaque pas du moteur et de chaque dessin (repere les blocages d'un premier affichage :
        texture ou modele charge a la volee)."""
        f = os.environ.get('DQ_TEMPS_IMAGES')
        if f:
            with open(f, 'a') as fh: fh.write('%s %d %d %.1f\n' % (genre, self.n_boucle, self.moteur.images, 1000.0 * (time.perf_counter() - t0)))

    def _instantane(self):
        """Etat du pas qui vient de finir : positions des personnages et de la camera, pour l'interpolation."""
        e = self.moteur.etat
        tup = lambda v: None if v is None else tuple(float(x) for x in v)
        return dict(cle=(e.partie, e.carte), ret=getattr(e, 'chargement', None) is not None, sp={k: tup(s['pos']) for k, s in e.sprites.items() if s['pos'] is not None},
                    cam_pos=tup(e.cam_pos), cam_cible=tup(e.cam_cible), champ=tup(e.champ['cam']) if e.champ and e.champ['cam'] else None)

    def _interpoler(self):
        """Remplace, le temps d'un dessin, les positions des personnages et de la camera (carte du monde, villes) par celles de l'instant entre le pas precedent et le pas actuel ;
        un saut (changement de carte, deplacement force) n'est pas interpole. Renvoie de quoi tout remettre en place."""
        pr, a, e = self.prec, self.alpha, self.moteur.etat
        sauve = []
        if pr is None or a >= 1.0 or e.partie == MO.PARTIE_COMBAT or pr['cle'] != (e.partie, e.carte) or pr.get('ret', False) != (getattr(e, 'chargement', None) is not None): return sauve      # (l'image qui leve la retenue d'un chargement n'est pas interpolee depuis la camera de la retenue)
        seuil = 24.0 if e.partie == MO.PARTIE_CHAMP else CAM_SAUT_VILLE       # pixels de la carte / unites de la ville par pas ; au-dela, c'est un saut
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
        self._nb_dessins = getattr(self, '_nb_dessins', 0) + 1
        if self._nb_dessins == 1:
            self._journal_fenetre('1re image du jeu')
            if getattr(self, 'dwm_coupe', False): pyglet.clock.schedule_once(lambda dt: transitions_dwm(self, True), 2.0)
        if self._nb_dessins <= 90 or self._nb_dessins % 120 == 0: self._verifier_taille_reelle()
        sauve = self._interpoler(); t0 = time.perf_counter(); self._dessin_genre = '?'
        try: self._dessiner()
        finally:
            for obj, nom, ancien, attr in sauve:
                if attr: setattr(obj, nom, ancien)
                else: obj[nom] = ancien
            self._mesure('dessin', t0)
            self._absorber_blocage(t0)
            if SV.ACTIF: self._suivre_dessin(t0)

    def _absorber_blocage(self, t0):
        """Une image tres longue (plus de 4 pas du moteur : 133 ms) parmi les 3 qui suivent un chargement de carte (textures du decor et des personnages, shaders, rendu hors ecran : premiere image d'une scene) ne doit pas
        etre rattrapee : sans cela le moteur refait d'un coup 3 pas (VC.avancer) et le fondu d'entree saute d'autant (a l'ecran : l'image apparait deja a moitie fondue). L'horloge du moteur repart de zero ; le temps
        du blocage est perdu (ecran de chargement). Limites : une machine lente (images de 100 ms et plus) ne fige pas le jeu, seul un vrai blocage est absorbe, au plus 3 fois par chargement."""
        e = self.moteur.etat; cle = e.cartes_chargees
        if cle != getattr(self, '_absorb_cle', None): self._absorb_cle = cle; self._absorb_n = 0
        self._absorb_n += 1
        if self._absorb_n <= 3 and time.perf_counter() - t0 > 4 * PAS_MOTEUR: self.t_boucle = None

    def _suivre_dessin(self, t0):
        """(diagnostic, DQ_SUIVI) une ligne par image dessinee pendant les 12 premieres images et pendant les 16 images qui suivent un chargement de carte ou un changement de partie : ce qui a ete dessine (`_dessin_genre` :
        scene, noir de chargement...), l'etat de la scene (camera, personnages places), l'opacite des deux plans de fondu, la retenue du dessin (`Etat.chargement`)."""
        e = self.moteur.etat; cle = (e.cartes_chargees, e.partie)
        if cle != getattr(self, '_suivi_cle', None): self._suivi_cle = cle; self._suivi_n = 0
        n = getattr(self, '_suivi_n', 99)
        if self._nb_dessins <= 12 or n < 16:
            places = sum(1 for sp in e.sprites.values() if sp['pos'] is not None)
            SV.noter('dessin', n=self._nb_dessins, img=self.moteur.images, genre=self._dessin_genre, partie=hex(e.partie), carte=e.carte, chargee=self.carte_nom, camera=SV.arrondi(e.cam_pos, 1), personnages='%d/%d' % (places, len(e.sprites)),
                     fondu='%.2f/%d' % (e.fondu['a'], e.fondu['n']), fond='%.2f/%d' % (e.fondu_fond['a'], e.fondu_fond['n']), retenu=getattr(e, 'chargement', None) is not None, ms=round(1000 * (time.perf_counter() - t0), 1))
        self._suivi_n = n + 1

    def _noter_echec_etat(self, quoi, ex):
        """Un etat instantane (raccourci chiffre, Ctrl + chiffre) n'a pas pu etre enregistre ou charge : une ligne dans la console et dans le journal des erreurs (le petit message a l'ecran est retire depuis #267)."""
        texte = '--- %s : %s impossible : %r ---\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), quoi, ex)
        print(texte, end='', flush=True); noter_erreur(texte)

    def _signaler_echecs_ecriture(self, core):
        """Sauvegarde que le moteur n'a pas pu ecrire (CoreJeu.h_fclose, apres deux essais, #198) : l'ancien fichier est intact et le jeu continue ; une ligne dans la console et dans le journal des erreurs (aucun message a l'ecran depuis #267)."""
        lignes, core.echecs_ecriture = core.echecs_ecriture, None
        texte = ''.join('--- %s : sauvegarde impossible : %s ---\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), l) for l in lignes)
        print(texte, end='', flush=True); noter_erreur(texte)

    def _surveiller_tas(self, core):
        """Tas du moteur (ENG-01, audit du 04/11/2026 : « Core.malloc » avance toujours, « h_free » ne libere rien, 256 Mo en tout ; environ 480 combats ou 7 000 chargements de carte, soit des heures de jeu) : le moteur s'arreterait d'un coup
        a 256 Mo. Une ligne du journal des erreurs le note a 200 Mo (78 %), puis a 240 Mo (94 %) (aucun message a l'ecran depuis #267), une fois par palier (de nouveau si le tas redescend, par exemple apres le chargement
        d'un etat). Fermer puis relancer le jeu remet la memoire a zero ; le jeu ecrit sa sauvegarde automatique (data5) a chaque arrivee sur une carte, rien n'est ecrit ici : un etat instantane garderait le tas plein."""
        u = core.tas_utilise(); niveau = 2 if u >= core.TAS_CRITIQUE else (1 if u >= core.TAS_ALERTE else 0)
        if niveau > self._tas_niveau:
            pc = round(100.0 * u / core.HEAP_SIZE)
            noter_erreur('--- %s : memoire du moteur a %d %% (%d Mo sur %d Mo) ---\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), pc, u >> 20, core.HEAP_SIZE >> 20))
        self._tas_niveau = niveau

    def _signaler_crochets_manques(self, mo):
        """Reglages du moteur que l'apk utilise n'a pas laisses s'installer (Moteur._manque : autre version du moteur que celle etudiee) : le jeu tourne avec le comportement d'origine pour ces points. Une ligne par point dans le journal
        des erreurs (aucun message a l'ecran depuis #267), une seule fois (les points trouves plus tard, apres le chargement d'un etat, sont annonces a leur tour)."""
        nouveaux = mo.crochets_manques[self._crochets_signales:]; self._crochets_signales = len(mo.crochets_manques)
        texte = ''.join('--- %s : reglage du moteur non applique : %s ---\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), l) for l in nouveaux)
        noter_erreur(texte)

    def tick(self, dt, muet=False):
        """Un pas du moteur (30 par seconde d'horloge de jeu). `muet` : pas supplementaire d'un combat accelere pendant que le moteur attend le joueur (menu, message qui attend une touche) : le moteur avance (animations des monstres,
        fenetres, minuteries) sans aucune touche ni clic, ceux-ci restant lus au rythme normal (voir _faire_pas_combat)."""
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
        p, decl = (0, 0) if (muet or self.pause.ouvert) else self._entrees(p)          # menu « Paramètres » ouvert : le jeu tourne mais ne recoit ni touche ni clic (les touches du menu ne font pas marcher le heros)
        mo = self.moteur
        if os.environ.get('DQ_CAMV') and self.n % int(os.environ['DQ_CAMV']) == 0: self._camv(mo)
        if os.environ.get('DQ_DEBUG') and (p or decl): print('n=%d p=%#x decl=%#x msg=%s actif=%s' % (self.n, p, decl, mo.msg_visible, mo.menu_actif()), flush=True)
        t0 = time.time(); mo.step(p, decl); self.dt_moteur = time.time() - t0
        if len(mo.crochets_manques) > self._crochets_signales: self._signaler_crochets_manques(mo)
        self._surveiller_tas(mo.core)          # tas du moteur presque plein (ENG-01)
        if mo.core.echecs_ecriture: self._signaler_echecs_ecriture(mo.core)          # une sauvegarde n'a pas pu etre ecrite (#198) : le jeu continue, le joueur est prevenu
        self.historique.maj(mo)          # dialogues et combats de ce pas -> historique (voir historique.py)
        if mo.demande_pause: mo.demande_pause = False; self.pause.ouvrir()          # bouton « Paramètres » du menu Divers : le menu Pause s'ouvre a la place des reglages d'origine du jeu (Moteur._detourner_parametres)
        self._maj_titre()
        for code, *_ in mo.ui.systeme:
            if code == 999: self.pause.ouvrir('quitter')            # MenuPortSendQuit : retour sur le menu de depart = quitter l'application (ApplicationQuit : question Oui / Non)
        mo.ui.systeme = []
        if self.ui_g: self.ui_g.tick()                     # animations des fenetres d'origine, une fois par image du jeu
        if mo.ui.degats:                                   # nombres de degats sur les monstres (HoppingNumber) : un par coup
            for ch, h, dm in mo.ui.degats: self.nb_degats.append(dict(ch=ch, h=h, dm=dm, t0=mo.images))
            mo.ui.degats = []
        if os.environ.get('DQ_FLAG') and self.n % int(os.environ['DQ_FLAG']) == 0: print('FLAG n=%d %#x partie=%s msg=%s menu=%s cam=%s>%s' % (self.n, mo.drapeaux(), mo.etat.partie, mo.msg_visible, mo.menu_actif(), None if mo.etat.cam_pos is None else tuple(round(float(x), 2) for x in mo.etat.cam_pos), None if mo.etat.cam_cible is None else tuple(round(float(x), 2) for x in mo.etat.cam_cible)), flush=True)
        if mo.etat.partie == MO.PARTIE_CHAMP and mo.etat.champ is not None: self._avancer_motifs()
        self.son.image = self.n
        if mo.etat.sons: self.son.evenements(VC.sons_a_jouer(mo.etat.sons, self._se_images), image_moteur=mo.images); mo.etat.sons = []
        self.son.tick()
        jeu = mo.options_jeu()[:2]
        if jeu != self._opt_son: self._opt_son = jeu; self.son.regler_mixage(jeu={'musique': SON.volume_option_jeu(jeu[0]), 'effets': SON.volume_option_jeu(jeu[1])})        # options « volume » de la fenetre Parametres du jeu
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
            print('combat', self.n_combat, 'engine image', self.moteur.images, 'type msg', getattr(self.ui_msg, 'type', None), [(k, len(m['v']), m['pos']) for k, m in sorted(self.moteur.etat.maillages.items())], flush=True)
        if self.args.shot and (self.n >= self.args.images or (self.args.images_combat and self.n_combat >= self.args.images_combat)):
            self.dispatch_event('on_draw'); self.flip()
            pyglet.image.get_buffer_manager().get_color_buffer().save(self.args.shot)
            print('capture :', self.args.shot, [(q, 'cur', f['cur'], list(f['cases'].items())[:3]) for q, f in self.moteur.ui.visibles()], self.moteur.menu_actif(), self.moteur.msg_visible, flush=True); pyglet.app.exit()

    def _dessiner(self):
        self._dessiner_scene()
        if self.sauve_rapide is not None and not self.pause.ouvert:       # raccourci chiffre : l'etat et la miniature sont pris sur l'image qui vient d'etre dessinee
            n, self.sauve_rapide = self.sauve_rapide, None
            try:
                t = self._copier_miniature(); png = self._png_miniature(t); t.delete(); self.sauver_etat(n, png)
            except Exception as ex: self._noter_echec_etat('Enregistrement de l\'état %d' % n, ex)
        if not self.pause.ouvert: self.hud.dessiner(self.hud.visibles())
        if self.pause.ouvert:
            if self.pause.veut_miniature: self.pause.mini_tex = self._copier_miniature(); self.pause.veut_miniature = False       # le jeu sans le menu, pour la miniature des etats (copie sur la carte graphique : pas de relecture qui bloque)
            self.pause.dessiner()

    def _dessiner_scene(self):
        t_debut = time.perf_counter()
        if self.t_prec is not None: self.ecarts.append(t_debut - self.t_prec)
        self.t_prec = t_debut
        e = self.moteur.etat
        if os.environ.get('DQ_CARTE_TEST'):                                  # (test) DQ_CARTE_TEST="nom;x,y,z;cx,cy,cz" : montre une carte de ville/grotte avec une camera fixe (animations de decor)
            nom_t, pc, cc = os.environ['DQ_CARTE_TEST'].split(';')
            e.partie = 0; e.carte = nom_t; e.champ = None; e.fond = (0.0, 0.0, 0.0); e.fond_haut = e.fond_bas = None; e.cam_libre = False
            if os.environ.get('DQ_CARTE_SANS_SPR'): e.sprites.clear()                          # (test) sans les personnages du moteur (le heros se superposerait aux objets etudies)
            e.cam_pos = tuple(float(v) for v in pc.split(',')); e.cam_cible = tuple(float(v) for v in cc.split(','))
            if os.environ.get('DQ_CARTE_DEPL'):                              # (test) DQ_CARTE_DEPL="dx,dy,dz" : la camera se deplace de ce vecteur a chaque image affichee (scintillement en mouvement)
                dv = [float(v) * self.n_boucle for v in os.environ['DQ_CARTE_DEPL'].split(',')]
                e.cam_pos = tuple(a + b for a, b in zip(e.cam_pos, dv)); e.cam_cible = tuple(a + b for a, b in zip(e.cam_cible, dv))
        if e.effet is not None and self.effet_ref is not e.effet: self.effet_ref = e.effet; self.effet_tex_prete = False      # nouvel effet de debut de combat : la premiere image est dessinee normalement puis copiee
        if e.effet is not None and self.effet_tex_prete: self._dessin_genre = 'effet'; self._dessiner_effet(e.effet); self._dessiner_aide(); return
        ef_c = self._capt_etat(e)                                            # effet d'ecran de la classe Capture (voyage, lampe, Riremito) : meme principe, mais l'interface reste dessinee par-dessus (effets_capture.py)
        if ef_c is not None and self.capt_prete:
            sim = self._capt_avancer(ef_c)
            if sim.rendu_actif or e.ecran_noir is not None: self._dessin_genre = 'effet d\'ecran'; self._dessiner_effet_capture(sim); return          # (les deux premieres images, le jeu est encore affiche normalement ; a l'arrivee d'un voyage c'est le noir du depart)
        if e.effet is None and e.attente_charge is not None:                # fin de l'effet, scene du combat pas encore arrivee : noir (sinon on verrait la scene d'avant)
            self._dessin_genre = 'noir (attente du combat)'; gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear(); self._dessiner_aide(); return
        champ = e.partie == MO.PARTIE_CHAMP and e.champ is not None        # carte du monde (tuiles) ou ville (decor 3D)
        cam3d = None                                                        # ville : (droite, haut, avant) de la camera, pour les panneaux des personnages
        retenu = getattr(e, 'chargement', None) is not None                 # chargement de carte sous un ecran couvert, scene pas encore en place : on ne dessine que le noir et les fondus (Etat.maj_chargement)
        if not champ and e.carte and e.carte != self.carte_nom:
            self._charger_carte(e.carte); self.t_boucle = None              # chargement synchrone (plusieurs dixiemes de seconde) : le temps passe n'est pas rattrape par le moteur (le fondu d'entree garde sa duree, au lieu de sauter 3 pas en une image)
        fond = e.fond
        if e.partie == MO.PARTIE_COMBAT and not any(fond) and not os.environ.get('DQ_FOND_ESTIME'): fond = self.fonds.couleur(self.carte_src) or self.fond_decor      # fond du combat = bg_color du decor charge (FETC, BackColor.SetColor de cmd_fld_load) ; estimation en attendant la liste / DQ_FOND_ESTIME=1 : (test) l'ancienne estimation
        elif e.partie == MO.PARTIE_COMBAT and self.fond_decor and not any(fond): fond = self.fond_decor
        gl.glClearColor(fond[0], fond[1], fond[2], 1.0)
        self.clear()
        bataille = e.partie == MO.PARTIE_COMBAT and e.cam_pos is not None and e.cam_rot is not None
        if retenu or (e.ecran_noir is not None and ef_c is None) or (e.partie == MO.PARTIE_CHAMP and e.champ is None) or (not champ and not bataille and e.partie != MO.PARTIE_COMBAT and (e.carte or '').startswith('btl_')):
            # carte du monde pas encore envoyee, ou combat fini et scene suivante pas encore arrivee : on ne montre pas la scene d'avant avec la camera d'une autre (image de decor de combat au retour d'une fuite) ;
            # ou chargement de carte pas encore complet (retenu) : le moteur n'a envoye que le decor, la camera et les personnages arrivent a l'image suivante
            self._dessin_genre = 'noir (retenue du chargement)' if retenu else 'noir (scene pas arrivee)'; gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear()
            if retenu: self.post.debut((0.0, 0.0, 0.0)); self.post.fin()                   # (prepare le rendu hors ecran sous le noir : sa creation ne retarde pas la 1re image visible)
            gl.glViewport(0, 0, *self.get_framebuffer_size()); self._dessiner_fondu(True)
            if not (e.carte or '').startswith('btl_'):               # (fin de combat : les fenetres du combat, comme le statut du groupe en haut a gauche, restent « visibles » dans le moteur un instant : sur l'ecran noir on ne voyait que cette boite)
                self._maj_message(); self._dessiner_message(); self._dessiner_menus()
            self._dessiner_fondu(); self._dessiner_aide(); return
        if not champ and not bataille and (e.cam_pos is None or (e.cam_cible is None and not camera_libre(e))): self._dessin_genre = 'rien (pas de camera)'; self._dessiner_aide(); return
        self._dessin_genre = 'scene'
        gl.glEnable(gl.GL_DEPTH_TEST); gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glViewport(0, 0, *self.post.debut(fond))          # scene dessinee hors ecran si un reglage d'affichage le demande (anticrenelage MSAA, nettete, luminosite : postfx.py) ; sinon directement dans la fenetre
        if not champ and not bataille and degrade_fond(e.fond_haut, e.fond_bas): self._tracer_degrade_fond(e.fond_haut, e.fond_bas)       # ville : fond de BackColor en degrade (#111)
        aspect = self.width / max(1, self.height)
        if champ: M, dh, w, h = self._camera_champ(e, aspect); self._maj_champ(e)
        elif bataille:
            M, M_decor = self._camera_combat(e, aspect); self._M_combat = M; dh = np.array([1.0, 0, 0]); w, h = SPRITE_L * SPRITE_ECHELLE, SPRITE_H * SPRITE_ECHELLE
        else:
            M, cam3d = self._camera_ville(e, aspect)
            if self.objets is not None and self.carte_nom == e.carte: self._orienter_decor(cam3d)         # arbres, bougies... : de face a la camera, quelle que soit sa rotation
            # sprites : panneaux verticaux tournes vers la camera (listes de sommets persistantes, une par emplacement)
            fh = np.array([e.cam_cible[0] - e.cam_pos[0], 0, e.cam_cible[2] - e.cam_pos[2]]); fh /= np.linalg.norm(fh) or 1
            dh = np.cross([0, 1, 0], fh); dh /= np.linalg.norm(dh) or 1
            w, h = SPRITE_L * SPRITE_ECHELLE, SPRITE_H * SPRITE_ECHELLE
        up = np.array([0, 0, -h]) if champ else np.array([0, h, 0])       # carte du monde : le haut du sprite est le nord (-Z)
        a_dessiner = []; ombres = []; pp = self.mode == MODE_PP
        phi = 0.0                                                          # (plus de rotation de la camera par le joueur : #264)
        corr = self._correction_bords(); C_vue = self._cadre_vue[0] if self._cadre_vue is not None else None          # correction des bords : intensite (0 a 1) et position de la camera de la visionneuse
        incl = self._inclinaison_sprites()                                         # essai #134 : part de l'inclinaison des verticales du monde prise par les sprites
        rang = {}
        if champ: rang = rang_profondeur_champ(e.sprites)      # carte du monde : sprites a plat, tous a la meme hauteur, superposes selon rang_profondeur_champ
        for slot, s in sorted(e.sprites.items()):
            if s['pos'] is None or s['col'][3] < 0.02 or not s.get('vis', True): continue      # paquet 14 : Chara.SetVisible
            f = self._feuille(s['id'] - 4096 if (champ and s['id'] >= 4096) else s['id'], self.mode)
            if not f: continue
            nl = f['nl']
            col, row = s['pose'] % f.get('cols', 3), s['dir'] % nl          # (bateau : 12 colonnes de 40 x 40, voir hd.FEUILLES_SPECIALES)
            pw, ph = f.get('pw', 1.0), f.get('ph', 1.0)                       # panneau du bateau : 0,8 x 0,8 contre 0,48 x 0,64 pour un personnage
            dort = bool(s.get('dort')) and not champ and not bataille and cam3d is not None          # personnage couche (paquet 16) : dessine a plat par pose_couchee, voir plus bas
            if phi and not dort:                                                     # camera tournee : la rangee montre le personnage tel qu'on le voit (cap du personnage - rotation de la camera, au plus proche) ; un personnage couche garde la rangee du moteur (c'est son corps entier qui tourne a l'ecran avec la camera)
                pas_d = 360.0 / nl; row = int(round((row * pas_d - phi) / pas_d)) % nl
            u0, u1, v0, v1 = HD.uv_case(f, col, row)                                 # case (col, row) de l'atlas (origine ou HD), gouttieres exclues
            p = np.array([(round(s['pos'][0]) if pp else s['pos'][0]) / CH_PX, 0.04 + rang.get(slot, 0) * 0.0005, (round(s['pos'][1]) if pp else s['pos'][1]) / CH_PX]) if champ else np.array(s['pos'], float)       # carte du monde : sprite a plat (vue de dessus), le heros (emplacement 0) au-dessus des autres
            if cam3d is not None:
                # Chara.normalBillboard : le panneau (0,48 x 0,64) prend la rotation de la camera, donc il est de face a l'ecran (pas ecrase par l'inclinaison) ; ses sommets
                # sont decales en profondeur (bas 0,185, haut 0,65 vers la camera, Chara.SystemInit) : une fois a l'ecran il se comporte comme un personnage debout pour le z-buffer
                k = 1.0 if os.environ.get('DQ_SANS_ECHELLE') else min(max(float(s.get('ech', 1.0)), 0.0), 8.0)          # paquet 13, bit 11 : Chara.SetScale (Transform.localScale du panneau, pieds fixes) ; 1,0 presque partout, 0,738 pour le heros et son equipier dans mlb1a, 0,952 dans ev07 (le reste : valeurs de depart d'une image)
                wk, hk = w * k * pw, h * k * ph
                r_, u_, f_ = self._repere_sprites(cam3d, corr); zb, zh = 0.185 / 0.48 * wk, (0.65 - 0.185) / 0.48 * wk       # decalages de profondeur a l'echelle du panneau (le haut penche de 36 degres vers la camera : le panneau est presque vertical dans le monde)
                # Panneau d'origine par defaut depuis #184 (« exactement comme dans le jeu » : voir _correction_bords, _repere_sprites et _panneau_ville) : le haut du panneau, plus proche, s'ecarte du centre de l'image et le sprite
                # « se penche » vers l'exterieur pres des bords gauche / droit (jusqu'a 15 a 20 degres en 16/9), comme sur le mobile mais plus visible avec le champ du 16/9 ; la correction des bords (bords verticaux, proportions
                # constantes, taille et profondeur inchangees, #134) reste disponible (DQ_CORRECTION_BORDS=100), de meme que le cisaillement (DQ_SPRITE_INCLINAISON, voir _inclinaison_sprites)
                if dort and C_vue is not None:
                    # Pose couchee (paquets 16 / 17, Chara.SetSleepPose, shader Custom/CharaSleep ; voir pose_couchee.py) : le panneau n'est PAS debout, la correction des bords (qui redresse un panneau debout) ne lui
                    # est jamais appliquee ; vu de dessus, a pleine taille, tourne selon la direction du sommeil, avec la profondeur du corps a plat (z-buffer, recouvrements par un lit, un mur...)
                    ang, qd = s.get('dort_rot', (0.0, 0))
                    qv = PC.sommets(p, ang, qd, float(getattr(e, 'dort_haut', 0.0)), wk / 0.48, cam3d, C_vue)
                    if qv is None: continue
                    a, b, c, d = qv
                else:
                    a, b, c, d = self._panneau_ville(p, r_, u_, f_, wk, hk, zb, zb + zh, corr, C_vue, incl)
                q = np.array([a, b, c, a, c, d], np.float32).ravel().tolist()
            else:
                kf = float(getattr(e, 'champ_echelle', 1.0)) if champ and slot in getattr(e, 'flottants', ()) else 1.0          # paquet 30 : le panneau du ballon (Field.SetFloatingObject) suit l'echelle du terrain, pieds fixes : il garde sa taille a l'ecran (MAP-02)
                a, b = p - dh * w * kf * pw / 2, p + dh * w * kf * pw / 2; upk = up * ph * kf
                q = np.array([a, b, b + upk, a, b + upk, a + upk], np.float32).ravel().tolist()
            uv = [u0, v0, u1, v0, u1, v1, u0, v0, u1, v1, u0, v1]
            cl = list(map(float, s['col'])) * 6
            vl = self.sprite_vl.get(slot)
            if vl is None: vl = self.sprite_vl[slot] = self.prog.vertex_list(6, gl.GL_TRIANGLES, position=('f', q), tex_coords=('f', uv), colors=('f', cl))
            else: vl.position[:] = q; vl.tex_coords[:] = uv; vl.colors[:] = cl
            a_dessiner.append((slot, f, vl))
            if s.get('ombre', True) and not (dort and not s.get('ombre_sep')):       # paquet 15 : le moteur peut masquer l'ombre d'un personnage (bateaux de la carte du monde...) ; couche, l'ombre part 64 sous le sol (Chara.lieBillboard) sauf si elle est separee
                al = float(s['col'][3]) * float(s.get('ombre_a', 1.0))
                if cam3d is not None: ombres.append((slot, np.array(s['ombre_pos'], float) if s.get('ombre_sep') and s.get('ombre_pos') else p, al))
                elif champ:
                    oc = s.get('ombre_champ')                      # paquet 15, bit 14 : le moteur donne la position de l'ombre sur la carte du monde (le ballon : plus au sud que ses pieds) ; sinon l'ombre est sous les pieds
                    po = np.array([(round(oc[0]) if pp else oc[0]) / CH_PX, p[1], (round(oc[1]) if pp else oc[1]) / CH_PX]) if oc is not None and len(oc) >= 2 else p
                    ombres.append((slot, po, al))
        icones = self._icones(e, champ, bataille, dh, cam3d)
        if os.environ.get('DQ_PROJ') and self.n_boucle % int(os.environ['DQ_PROJ']) == 0: self._dbg_proj(M, e, cam3d, a_dessiner, icones)
        self._dom_lie = None
        self.prog.use()
        self.prog['mvp'] = tuple(float(x) for x in M.T.ravel()); self.prog['cutoff'] = 0.5; self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0); self.prog['amul'] = 1.0
        self._teinte_gl = None; self._regler_teinte((1.0, 1.0, 1.0))        # (le uniforme vaut 0 tant qu'on ne l'a pas ecrit : tout noir)
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
                self.prog['net'] = 0.0 if hd else (2.0 if (pp or not self.lissage) else 1.0)           # texture agrandie : filtrage doux des mipmaps ; originale : pixels nets (plus proche voisin si le lissage est coupe)
                if shader == 3: gl.glDisable(gl.GL_DEPTH_TEST)                 # DssaCharaTransparent : ZTest Always
                self.prog['tsize'] = (float(tw), float(th)); self._tracer(tex, vl)
                if shader == 3: gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glDepthMask(gl.GL_TRUE)
            self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0)
        else:
            self._M_ville = M; self._aspect_ville = aspect
            if e.partie != MO.PARTIE_BESTIAIRE: self._tracer_decor(True)          # bestiaire : la carte de la ville reste chargee (aucun paquet 0) mais la camera du livre, a 83 unites, n'en voit qu'une tranche (l'eglise, au bord du plan lointain) derriere la liste et la fiche : le livre ne montre que le monstre (paquets 21 / 22)
            if e.fbx: self._tracer_fbx(e)               # modeles 3D animes (le dragon du titre) : meme file que le decor opaque
        self.prog['cutoff'] = 0.05
        if ombres and not os.environ.get('DQ_SANS_OMBRE'):
            if cam3d is not None: self._dessiner_ombres_chara(ombres, cam3d)
            elif champ: self._dessiner_ombres_champ(ombres, w * CH_PX / 24.0)
        for slot, f, vl in a_dessiner:
            self.prog['net'] = 0.0 if f['hd'] else (2.0 if (pp or not self.lissage) else 1.0); self.prog['tsize'] = (float(f['tw']), float(f['th']))
            self._tracer(f['t'], vl)       # comme Unity (shader Chara, ZTest normal) : un personnage cache par un decor n'est pas visible du tout
        self.prog['net'] = 2.0 if (pp or not self.lissage) else 1.0; self.prog['tsize'] = (32.0, 32.0)
        for tex, vl in icones: self._tracer(tex, vl)                          # bulles d'icone (Riseup), devant les personnages
        if not champ and not bataille and e.maillages and e.partie in (MO.PARTIE_VILLE,) + MO.PARTIES_MINIJEU and cam3d is not None:
            # effets-maillages de la ville (paquets 21, 22 : sort Morph, eclaboussures, coups d'epee du prologue, credits et logo du titre), tournes vers la camera. Ils passent APRES les personnages (Custom/Chara : file Transparent,
            # 3000) : DssaChara Transparent+100, DssaMonster0 +150, DssaMonster1 +200, DssaCharaTransparent Overlay-150 (3850, ZTest Always : devant tout, comme les bulles Riseup, de la meme file). Avant, ils etaient dessines
            # avant les personnages : un personnage cache a l'effet qui le recouvre (le nuage du sort Morph passait « derriere » Elisa).
            self.prog['cutoff'] = 0.05; self.prog['net'] = 1.0; self.prog['tsize'] = (1.0, 1.0)
            gl.glDisable(gl.GL_CULL_FACE); gl.glDepthMask(gl.GL_FALSE)
            self._dom_lie = None
            for tex, tw, th, vl, shader, hd in self._maillages_combat(e, np.column_stack(cam3d), True):
                self.prog['net'] = 0.0 if hd else (1.0 if self.lissage else 2.0)
                if shader == 3: gl.glDisable(gl.GL_DEPTH_TEST)
                self.prog['tsize'] = (float(tw), float(th)); self._tracer(tex, vl)
                if shader == 3: gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glDepthMask(gl.GL_TRUE); self.prog['net'] = 0.0; self.prog['tsize'] = (1.0, 1.0)
        self.prog.stop()
        gl.glDisable(gl.GL_DEPTH_TEST)
        if e.partie != MO.PARTIE_COMBAT and not champ: self._dessiner_vignette()          # (pas sur la carte du monde, entierement en 2D)
        self._dessiner_fondu(True); self.post.fin()
        if ef_c is not None and not self.capt_prete:                         # effet Capture qui demarre : la scene (sans interface) est copiee, puis les images normales continuent (le noir d'un voyage en cours couvre tout)
            self._capt_capturer(ef_c)
            if e.ecran_noir is not None: gl.glClearColor(0.0, 0.0, 0.0, 1.0); self.clear()
        self._dessiner_degats(e)
        self._maj_message(); self._dessiner_saisie_nom(); self._dessiner_message(); self._dessiner_menus(); self._dessiner_fondu(); self._dessiner_titre(); self._dessiner_licence(); self._dessiner_sauvegardes()
        self.dt_dessin += (time.perf_counter() - t_debut - self.dt_dessin) * 0.1
        if e.effet is not None and not self.effet_tex_prete: self._copier_ecran(); self.effet_tex_prete = True       # capture de l'ecran du jeu, sans les lignes d'aide
        self._dessiner_aide()

    def _infos(self):
        """Lignes d'information (F1) : lieu et fenetre, reglages d'affichage, son, performances. Rien n'est modifiable ici : les reglages sont dans le menu Echap."""
        e = self.moteur.etat; champ = e.partie == MO.PARTIE_CHAMP and e.champ is not None; bataille = e.partie == MO.PARTIE_COMBAT
        lieu = 'Carte du monde' if champ else ('Combat %s' % e.carte if bataille else 'Carte %s' % (e.carte or '?'))
        nom_mode = HD.MODES[self.mode][0] if self.mode < MODE_PP else 'Pixel perfect'
        decor = 'rendu d\'origine lissé' if self.mode in (0, MODE_PP) else nom_mode
        self.etiquette.text = '%s | fenêtre %d x %d%s | moteur : image %d, partie %#x' % (lieu, self.width, self.height, ' (plein écran)' if self.est_plein else '', self.moteur.images, e.partie)
        self.etiq_hd.text = 'Sprites : %s  |  Décor : %s\nLissage des textures : %s  |  Antialiasing : %s\nSon : %s (musique %d %%, bruitages %d %%)' % (
            nom_mode, decor, 'oui' if self.lissage else 'non', 'x%d' % self.post.msaa if self.post.msaa else 'non',
            ('oui' if self.son.actif else 'non') if self.son.ok else 'indisponible', round(self.son.vol_m * 100), round(self.son.vol_b * 100))
