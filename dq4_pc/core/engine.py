"""Le moteur du jeu (libdq4core.so, ARM64) execute dans un emulateur + decodage de ce qu'il demande a Unity."""
import os, re, struct, time, zipfile, unicorn
import numpy as np
from dq4_pc.language import tr
from dq4_pc.core import emu_core as T
from dq4_pc.core import game_priority as PJ
from dq4_pc.core import lying_pose as PC
from dq4_pc.core import encounters as RE
from dq4_pc.core.pktlog import PacketLog
from dq4_pc.core.history import Sensor
from dq4_pc.battle.battle_history import BattleSensor
from dq4_pc.render import capture_effects as EF
from dq4_pc.persistence.write_dir import atomic_write

FIELD_SCALE = (0.25, 4.0)               # bornes de l'echelle de la carte du monde (paquet 30 ; le moteur n'envoie que 1,0 a 1,25 : la borne ne sert qu'a ecarter une valeur aberrante)
CUR_I, CUR_F = 0x258278, 0x258280          # curseurs d'ecriture (entiers / flottants) dans la bibliotheque
PART_INITIAL = 0x3                         # menu de depart (GameStartPart : liste des journaux, creation, suppression, licence)
PART_TOWN = 0xc                         # ville, donjon, tour (decor 3D)
PART_BATTLE = 0xd
PART_FIELD = 0xe                         # FieldPart : carte du monde
PART_CASINO = 0xf                        # Global::startCasino : machine a sous (carte ev05) et poker (carte ev04), fenetres des types 44-48
PART_BESTIARY = 0x10                    # Global::startBook : livre des monstres (fenetre de type 28) ; garde la carte de la ville
TITLE_MAP = 'ev01'                       # carte de l'ecran-titre (ciel, logo, ile, dragon : scene sans heros)
MINIGAME_PARTS = (PART_CASINO, PART_BESTIARY)        # parties « plein ecran » du moteur qui dessinent leurs elements par maillages dynamiques (paquets 21 / 22) avec leur propre camera
MSGDBG = bool(os.environ.get('DQ_MSGDBG'))     # (test) journal des etats du message du moteur
FBXLOG = bool(os.environ.get('DQ_FBXLOG'))     # (test) journal des paquets 32 (dragon du titre : position, rotation, couleur, sequence)
GLOBAL_PTR = 0x23d438                       # singleton Global
RESOURCE_NAME = 0x258290                    # nom de la ressource carte demandee a Unity (ex. m/ma/in/mak1f1)
SCREEN_STATE = 0xd8                           # Global+0xd8 : copie, a chaque GameUpdate, du premier entier du tampon de sortie (mot d'etat partage avec Unity) ; son bit 1 = « effet d'ecran en cours » (Global::IsScreenEffectEnd attend qu'il retombe)
G_IS_AMAZON = 0x24f684                      # octet g_isAmazon du moteur : a 1, la case « Sauv. cloud » du menu de depart n'existe pas
MSG_RETURN_TITLE = 0xcba2f                     # identifiant du message de la boite « Revenir a l'ecran titre » des Parametres d'origine (TownMenu_OPERATION_SETTING::menuUpdate + 0x1c8 : `mov w1, #0xba2f ; movk w1, #0xc, lsl #16` puis TownMenu_MESSAGE::addMessage(int)) : b0834000.mpt, 834095
MESSAGE_RESULT = 0x10                        # TownMenu_MESSAGE + 0x10 : reponse de la boite (1 = Oui, 2 = Non ; remis a 0 a l'ouverture) ; lue par TownMenu_OPERATION_SETTING::menuUpdate (etat 5)
BATTLE_EFFECT = 4                            # paquet 34 (cmd_screen_effect) : valeur & 0xf = 4, Capture.BattleEffect (les morceaux de l'ecran tombent)
BATTLE_EFFECT_FRAMES = 57                    # Capture.BattleEffect : le compteur va de 0 a divY (56) inclus, une image du jeu chacun
BLACK_SCREEN_MAX = 1800                       # images (30 Hz) d'ecran noir apres le depart d'un voyage (Capture.Tabi) avant de renoncer a attendre l'arrivee (garde-fou : le jeu la lance toujours, bien avant)
LOADING_COVERED = 0.9                    # opacite (0 a 1) d'un plan de fondu a partir de laquelle l'ecran est « couvert » : un chargement de carte qui arrive alors n'est montre qu'une fois la scene en place (State.chargement)
LOADING_MIN, LOADING_PLACEMENT, LOADING_MAX = 1, 2, 6      # images du moteur apres le paquet 0 : au moins 1 (le moteur place la camera et les personnages a l'image suivante, sur 529 cartes), 2 au plus pour attendre les positions des personnages visibles, 6 : garde-fou (jamais d'attente plus longue)
LOAD_WAIT_MAX = 240                    # images (30 Hz) d'ecran noir avant de renoncer a attendre le chargement de la scene de combat
BATTLE_ENTRY_WINDOW = 12                  # images apres le chargement de la scene d'un combat (paquet 0, bit 8) pendant lesquelles un fondu lance par le moteur est le fondu d'arrivee du combat (State.battle_transition)
BATTLE_RETURN_WINDOW = 12                  # images apres la sortie de la partie combat pendant lesquelles un fondu lance par le moteur est le fondu de retour a la carte
TRANSITION_GUARD = 8                        # images ou la transition de combat reste « en cours » apres la fin de l'un de ses fondus (le moteur change de scene 1 a 3 images plus tard, puis lance le fondu suivant)
LIB_APK = 'lib/arm64-v8a/libdq4core.so'
EXIT_COUNTDOWN = 0x258254                  # octet de la bibliotheque lu par Global::NativeExec : decompte (en images) du bruitage de sortie ; startTown, startField, ChangeGamePart, startFirstTown et startDebugTown l'arment a 15 quand le jeu quitte une ville ou la carte du monde,
                                            # NativeExec le decremente a chaque image et, a 0, appelle TownSystem::playTownExitSE / FieldSystem::playFieldExitSE (bruitage 305 : seulement si l'ancienne scene vit encore, son octet 0 = 1) ; voir Engine._exit_countdown

# touches (masque envoye a GameUpdate) : haut, bas, gauche, droite verifies ; A/B a confirmer
UP, DOWN, LEFT, RIGHT, A, B = 0x1, 0x2, 0x4, 0x8, 0x10, 0x20
CAM_G, CAM_D = 0x10, 0x20                  # sur le terrain d'une ville, les bits 4 et 5 des touches tenues ne sont pas A / B mais les boutons de camera du jeu (window::NormalControl::checkCamera lit (Global + 0xe0) >> 4 & 3) : 1 tourne a gauche,
                                           # 2 a droite, 3 (les deux) ramene la camera au nord ; le moteur applique lui-meme limites, verrous et scenes (TownPlayerManager::setCameraRot) et tourne les directions de marche et les rangees des sprites
CAM_STEP = 360.0 * 0x200 / 65536.0          # degres d'une rotation de camera du jeu (TownCamera::rotateL / rotateR : 0x200 sur 65536 par tour), une par pas du moteur tant que le bouton est tenu : 84,4 degres par seconde
ROT_CAM_RIGHT, ROT_CAM_LEFT, ROT_CAM_NORD, ROT_CAM_FINISHED = 1, 2, 3, 4      # CAMERA_ROT_TYPE : TownPlayerManager + 0x698 (rotation demandee, en attente du prochain setCameraRot) ; 3 / 4 = retour au nord en cours / fini
OBJ_MESSAGE = 0x252330                     # objet SDrawCTRL (canevas de texte des messages) dans la bibliotheque
CANVAS_L, CANVAS_H = 512, 512            # texture du canevas de message d'Unity (MenuMessage : Texture2D(512, 512)) ; le moteur y ecrit en boucle
SHORTS_STACK = 4096                         # taille reelle allouee pour la file des messages (Unity en annonce 1089)
MSG_ACTIVE, MSG_STATE, MSG_CURRENT, MSG_END, MSG_SPEED = 0x25238e, 0x25238c, 0x2523cc, 0x2523ce, 0x2523b0      # ui_MsgLoop : message ouvert (octet), etat (1 lecture d'un code, 2 ecriture des lettres, 3 / 5 attente d'une touche), indice de la lettre courante et de la fin de ligne, lettres par image / 4 du type de fenetre
UI_MSGLOOP_WRITE = 0x128                # ui_MsgLoop + 0x128 : `sxth w20, w8` apres `lsl w8, w8, #2` (etat 2 : nombre de lettres ecrites a cette image)
SXTH_W20_W8 = 0x13003d14
BATTLE_MANUAL = 4                          # OptionStatus.battleSpeed : 0 a 3 = attente de 12 / 22 / 32 / 42 images entre deux messages de combat (BattleAutoFeed::setMessageSpeed), 4 = pas d'avance automatique
FADE_FLAG, PLAYER_LOCKED_FLAG = 0x1, 0x4        # Global.Flag (mot d'etat partage, Engine.drapeaux) : un fondu est en cours ; le jeu a verrouille le joueur (evenement, scene : Global.PLAYER_LOCK)
HAVESTATUS_LEVELUP_END = 0x3f8             # status::HaveStatus::levelup(bool) + 0x3f8 : `tbz w20, #0, ...` (w20 = l'argument ; vrai : le personnage retrouve tous ses PV et PM, ses PV max/MF max venant d'etre recalcules)
MENU_MANAGER, OPENED_MENUS, MENU_GIFT_EXP, MENU_GIFT_EXP_STATE, MENU_GIFT_EXP_WAIT = 0x252078, 8, 0x24c730, 0x30, 2      # MenuManager : pointeur vers le gestionnaire (a +8, jusqu'a 8 menus ouverts, un pointeur chacun) ; gMaterielMenu_EXTRA_PRESENT_EXP (don d'experience) : etat a +0x30, 2 = derniere attente (voir awaits_touch)
TBZ_W20_0 = 0x36000094
COUNTDOWN_EXEC_WRITE = 0xc               # CountDown::exec + 0xc : `str w8, [x0]` (w9 = compteur de rencontres avant, w8 = compteur apres avoir perdu 2 x [x0 + 0x10])
STR_W8_X0 = 0xb9000008
DOKU_CHANGETIME_B, DOKU_RET, DOKU_CHANGETIME_STUB = 0x38, 0x44, 0x2246b0      # FieldPlayerDoku::checkDokuDamage + 0x38 : `b FieldStage::ChangeTime` (saut terminal, via le stub PLT 0x2246b0 ; w1 = 0, le temps du monde avance de 2), + 0x44 : le `ret` de la fonction
RET_A64 = 0xd65f03c0
PLAYTIME_MOV_W1, PLAYTIME_BL, PLAYTIME_STUB, PLAYTIME_GOT, MOV_W1_2 = 0x14, 0x20, 0x227d90, 0x240968, 0x52800041
PLAYTIME_STUB_WORDS = (0xb00000d0, 0xf944b611, 0x9125a210, 0xd61f0220)      # les 4 instructions du stub PLT 0x227d90
# Global::NativeExec + 0x14 : `mov w1, #2` ; + 0x20 : `bl GameStatus::addPlayTime` (via le stub PLT 0x227d90 : x0 = status::g_Game, w1 = 2, void) : une fois par pas du moteur, +2 unites (1/60 s) du temps de jeu
MAGIC_CHARSELECT_BL, MAGIC_WITHOUT_TARGET_BL, MAGIC_EXECUSE_STUB = 0x428, 0x188, 0x2269c0      # TownMenu_MAGIC_CHARSELECT::menuUpdate + 0x428 et TownMenu_MAGIC_ROOT::useMagicNoTarget + 0x188 : `bl UseAction::execUse` (via le stub PLT 0x2269c0) du menu Magie du terrain
MAGIC_MP, MAGIC_RESULT, MAGIC_ACTION = 0x7e, 0x210, 0x1d8        # PlayerStatus + 0x7e : PM courants ; UseActionParam + 0x210 : liste des messages de resultat (se termine par 0), + 0x1d8 : numero de l'action
MAGIC_HEAL_SOUND, SUB_W8_W8_C4 = 0x100, 0x51031108          # TownMenu_MAGIC_CHARSELECT::menuUpdate + 0x100 : `sub w8, w8, #0xc4` (w8 = numero de l'action ; si le resultat est <= 2, c'est un sort de soin et le moteur joue le bruitage 501, `playSe(0x1f5)`, quel que soit son effet)
MAGIC_TARGET_COUNT, MAGIC_LOOP_END = 0x257f84, 0x2e0       # gTownMenuItemUseManager + 0xaa : nombre de cibles dont le moteur affiche le resultat (et dont il joue le bruitage de soin, une fois chacune) ; useMagicNoTarget + 0x2e0 : sortie de cette boucle
MSG_NOTHING_HAPPENS = 0xc3d6b             # identifiant du message du moteur « Mais rien ne se passe. » (champ d'echec de la table des actions : Resurrection, Antipoison, Sifflet...) ; sert de repere de version du moteur (action 201) : il n'est plus affiche par la regle des sorts sans effet
MSG_NOTHING_OCCURS = 0xc3d6d          # identifiant du message du moteur « Mais il ne se passe rien. » (celui qu'Evac' hors donjon met dans param + MAGIC_RESULT ; mesure : le champ 5 de la table des actions donne 0xaae7e pour l'action 204, mais ce n'est pas le message affiche) : texte officiel affiche par la regle « sort qui coute des PM sans effet » (demande de Sylfried, #48)
ANIM_DURATION = 18                            # images (30 Hz) avant de dire au moteur qu'une animation d'objet (porte...) est finie
ORIGIN_AFTER = 3                            # images apres sa creation au bout desquelles un personnage anime sans position est place a l'origine (voir State.appliquer, paquet 13)


class Silent:
    def __init__(self): self.lines = []
    def __call__(self, *a):
        self.lines.append(' '.join(str(x) for x in a)); del self.lines[:-200]


class GameCore(T.Core):
    """Core + sauvegardes : lecture dans un dossier reel, ecriture persistante (jamais dans les originaux)."""
    read_folder = None
    write_folder = None

    def h_fopen(self, path, mode, *a):
        p = self.read_cstr(path).decode('latin-1'); m = self.read_cstr(mode).decode()
        mm = re.search(r'(data\d+\.dat)$', p)
        if mm and os.environ.get('DQ_SAVEDBG'): print('fopen %s mode %s' % (p, m), flush=True)           # (test) quand le moteur ouvre un fichier de sauvegarde
        if mm:
            name_str = mm.group(1)
            if 'w' in m or 'a' in m:
                r = super().h_fopen(path, mode, *a)
                if r: self.files[r]['persist'] = os.path.join(self.write_folder, name_str)
                return r
            for d in (self.write_folder, self.read_folder):
                if d and os.path.exists(os.path.join(d, name_str)):
                    self.real_files[p] = os.path.join(d, name_str); break
        return super().h_fopen(path, mode, *a)

    write_failures = None                    # fichiers de sauvegarde que le moteur n'a pas pu ecrire (liste de phrases, lue et videe par la fenetre : petit message + journal)

    atomic_write = staticmethod(atomic_write)                  # (persistance/ecriture.py : partagee avec l'import de sauvegardes)

    def h_fclose(self, h, *a):
        f = self.files.get(h)
        if f and f.get('persist'):
            ex = self.atomic_write(f['persist'], bytes(f['d']))
            if ex is not None:                # le moteur continue (il croit avoir ecrit, comme avant) : la fenetre previent le joueur
                if self.write_failures is None: self.write_failures = []
                self.write_failures.append('%s : %r' % (os.path.basename(f['persist']), ex))
        return super().h_fclose(h, *a)


# Etats instantanes enregistres avant le passage du projet a l'anglais (05/11/2026) : leurs objets `State` (ex-`Etat`) et `Interface` gardent les anciens noms d'attributs, en francais, dans leur pickle.
# `__setstate__` les remet sous leur nom actuel a la lecture ; un etat enregistre depuis (noms anglais) passe tel quel.
OLD_ATTRIBUTES = {
    'attente': 'waiting', 'attente_charge': 'load_wait', 'cam_bas': 'cam_down', 'cam_cible': 'cam_target', 'cam_libre': 'cam_free',
    'carte': 'game_map', 'cartes_chargees': 'loaded_maps', 'champ': 'field', 'champ_echelle': 'field_scale', 'chargement': 'loading',
    'degats': 'damage', 'dort_haut': 'sleeping_height', 'ecran_noir': 'black_screen', 'effet': 'effect', 'effet_ecran': 'screen_effect',
    'fen_entree': 'entry_window', 'fen_retour': 'return_window', 'flottants': 'floats', 'fond': 'background', 'fond_bas': 'bottom_background',
    'fond_haut': 'top_background', 'fondu': 'fade', 'fondu_fond': 'background_fade', 'garde_trans': 'transition_guard', 'icones': 'icons',
    'maillages': 'meshes', 'maillages_vus': 'meshes_seen', 'mesh_etat': 'mesh_state', 'modeles': 'models', 'monde': 'world', 'musique': 'music',
    'objets_cmd': 'object_cmds', 'ordre': 'order', 'pad_clignote': 'pad_blink', 'partie': 'part', 'rapport_fondu': 'fade_ratio', 'sons': 'sounds',
    'symboles': 'symbols', 'systeme': 'system', 'teinte': 'tint', 'vitesse_fondu': 'fade_speed',
}


def _renamed_attributes(state):
    """Dictionnaire d'attributs lu dans un pickle -> le meme avec les noms actuels."""
    return {OLD_ATTRIBUTES.get(k, k): v for k, v in state.items()}


class State:
    """Ce que Unity saurait a l'ecran : decode des paquets du moteur."""
    fade_speed = 1.0                        # les fondus au noir durent 1 / fade_speed de leur duree d'origine : FIXE a 1 (duree du jeu) depuis #101, plus un reglage du joueur (les tests la font varier)
    sepia = False                              # paquet 1 (cmd_map_effect_sepia : FldObject.calculateExecSepia) : le decor des villes passe aux shaders `Custom/fld_*_sepia` (retours en arriere) jusqu'au chargement de carte suivant ; attribut de classe : un etat instantane enregistre avant #254 n'a pas cet attribut
    field_scale = 1.0                        # paquet 30, entier < 0 : Field.SetScale(echelle) : la camera orthographique de la carte du monde voit echelle x plus de terrain (ballon : 1,0 a 1,25, renvoyee a chaque image par FieldData::setOffset) ; attribut de classe : un etat instantane enregistre avant #252 n'a pas cet attribut
    screen_effect = None                         # paquet 34, valeurs 3 (voyage), 5 (lampe), 6 (Riremito) : effet de la classe Capture en cours {'n': images ecoulees, 'duree': images du moteur, 'images': appels de MoveNext d'origine, 'genre', 'inverse', 'matin'} (voir Engine._start_screen_effect) ; attribut de classe : un etat instantane enregistre avant #256 n'a pas cet attribut
    black_screen = None                          # fin du depart d'un voyage (Capture.Tabi : les deux couches passent a l'alpha 0, la camera du jeu reste coupee) : {'n': images ecoulees} tant que l'ecran reste noir, jusqu'a la fin de l'arrivee (voir Engine._screen_effect)
    floats = ()                             # paquet 30, entier >= 0 : Field.SetFloatingObject(emplacement) : le panneau de ce personnage (le ballon : emplacement 12) est agrandi de `field_scale` (Field.FloatingObject.SetScale), il garde donc sa taille a l'ecran quand le terrain est vu de plus loin ; son ombre n'est pas touchee
    def __init__(self):
        self.game_map = None; self.cam_pos = None; self.cam_target = None; self.cam_rot = None
        self.symbols = {}                            # carte du monde : icones (paquet 29) idx -> {genre, x, y (coin haut-gauche en px), alpha, visible}
        self.models = {}; self.meshes = {}       # combat : emplacement -> id de modele (texture m<id>) ; emplacement -> maillage dynamique (paquet 22)
        self.mesh_state = {}                           # combat : emplacement -> {'shader', 'vis', 'col', 'off'} (paquets 21, 23, 24, 25, 26 : MeshChara cote Unity)
        self.cam_near = None; self.cam_far = None; self.cam_yoff = None; self.cam_free = False; self.cam_down = None      # paquet 11 : near, far, yOffset (None = valeurs de Global.CameraInitParams), camera libre (sans cible), lookDownAdjust (None = 0,2 du .cctor de SceneCamera)
        self.cam_fov = None                           # paquet 11 (camera_sub) : champ de vision nominal en degres (Unity le multiplie par 4/3, SceneCamera.Update) ; None = valeur du combat (48)
        self.pad_blink = False                     # paquet 19 avec un emplacement >= 16 (TouchPad.SetPadBlink) : le jeu fait clignoter le rond central de la croix (boule orange et halo) tant qu'une action est possible / attendue ; numero d'icone < 0 = fin (#131)
        self.icons = {}                              # paquets 19/20 (Riseup) : emplacement (0..15) -> {'id' (case 32 x 32 de la feuille MenuTexture), 'pos', 'alpha'} : bulle « ! » au-dessus d'un personnage
        self.sprites = {}; self.loaded_maps = 0; self.object_cmds = []; self.background = (0.0, 0.0, 0.0); self.top_background = None; self.bottom_background = None       # fond : moyenne des deux teintes du paquet 8 ; top_background / bottom_background : teintes du haut et du bas de l'ecran (BackColor, degrade ; None = pas de paquet 8) ; object_cmds : ordres sur les objets de la carte (paquets 2 a 5 et 7), vides par la fenetre : (genre, objet, valeurs...)
        self.part = 0; self.field = None        # partie du jeu (0xc ville, 0xe carte du monde) ; carte du monde : tuiles a afficher
        self.meshes_seen = set()                # combat : emplacements dont le maillage (paquet 22) est arrive a CETTE image : Unity dessine en mode immediat, pas de paquet = rien a l'ecran (clignotement d'un coup recu, monstre vaincu)
        self.fade = self._fade_plane(); self.background_fade = self._fade_plane()      # Fade.FadePlane : opacite courante, opacite visee, pas par image, images restantes, couleur, images passees tout noir. DEUX plans (Fade.l_fade, bit 14 de l'entier du paquet 9 = Fade.l_targetLayer) : 0 = « FadeForMenu » (shader Custom/FrontFade, file Overlay : devant tout, fenetres et messages compris) ; 1 = « FadeForBG » (Custom/BackFade, file Background : devant la scene, derriere les fenetres)
        self.sounds = []; self.music = None       # paquets 35/36/37 : ordres de son en attente (type, valeur), vides par la fenetre a chaque image ; musique demandee en dernier (None = arret)
        self.effect = None                         # effet d'ecran de debut de combat en cours : {'n': images ecoulees} (le moteur attend sa fin, voir Engine._battle_effect)
        self.loading = None                    # chargement de carte (paquet 0) alors que l'ecran est couvert par un fondu : {'n': images du moteur depuis le paquet 0, 'cam': paquet 10 recu depuis} tant que la scene n'est pas en place ; la fenetre ne dessine alors que le fondu (voir update_loading)
        self.fade_ratio = (-99, 1.0)             # dernier fondu au noir lance par le moteur : (image du moteur, duree jouee / duree d'origine) ; 1.0 = duree du jeu (voir Engine._exit_countdown)
        self.entry_window = 0; self.return_window = 0; self.transition_guard = 0      # transition de combat (voir battle_transition) : images restantes de la fenetre « arrivee en combat », de la fenetre « retour a la carte », de la garde entre deux fondus
        self.load_wait = None                # {'base': nombre de chargements de scene deja vus, 'n': images attendues} : ecran noir tant que la scene du combat n'est pas arrivee
        self.world = None                         # carte du monde entiere lue dans le moteur : {'ids': tuiles (H x L) apres animation, 'l', 'h'} ; None hors de la carte du monde
        self.tint = (1.0, 1.0, 1.0)             # paquet 33 (cmd_map_color_rate) : teinte du decor (FldObject.m_color, ou Field.SetColor sur la carte du monde) : multiplie la couleur de chaque materiau du decor (sauf les textures « tz_ » : lampes, bougies, vagues) ; 1, 1, 1 = neutre
        self.sleeping_height = 0.0                          # paquet 17 (Chara.SetSleepNear) : hauteur du corps des personnages couches (composante Y de s_lieOffset, statique de Chara : elle survit aux changements de carte) ; 0 tant que le moteur n'a rien envoye
        self.fbx = {}; self.image = 0             # modeles 3D animes (paquets 31 / 32 : le dragon du titre) : emplacement -> {'id', 'vis', 'pos', 'rot', 'scl', 'col', 'anim': [(image du moteur, numero de sequence, force)]} ; image : numero du pas du moteur en cours (rempli par Engine.step)

    @staticmethod
    def _fade_plane(): return {'a': 0.0, 'fin': 0.0, 'pas': 0.0, 'n': 0, 'col': (0.0, 0.0, 0.0), 'noir': 0, 'combat': False}      # 'combat' : fondu de la transition d'un combat (duree du jeu, voir battle_transition)

    def __setstate__(self, d):                  # etats enregistres avant les deux plans de fondu (et avant le passage a l'anglais : voir OLD_ATTRIBUTES)
        self.__dict__.update(_renamed_attributes(d)); self.__dict__.setdefault('background_fade', self._fade_plane()); self.__dict__.setdefault('fbx', {}); self.__dict__.setdefault('image', 0); self.__dict__.setdefault('tint', (1.0, 1.0, 1.0)); self.__dict__.setdefault('loading', None); self.__dict__.setdefault('sleeping_height', 0.0); self.__dict__.setdefault('top_background', None); self.__dict__.setdefault('bottom_background', None)
        self.__dict__.setdefault('entry_window', 0); self.__dict__.setdefault('return_window', 0); self.__dict__.setdefault('transition_guard', 0); self.__dict__.setdefault('fade_ratio', (-99, 1.0))

    def fade_in_progress(self): return self.fade['n'] >= 1 or self.background_fade['n'] >= 1      # Fade.FadePlane.CheckFade : images restantes > 0 sur l'un des deux plans

    def battle_transition(self):
        """Le jeu est-il dans la transition d'un combat : effet d'ecran de debut (la « cascade »), ecran noir qui attend la scene, fondus d'arrivee et de sortie du combat, fondu de retour a la carte (et les 1 a 3 images
        entre deux de ces fondus) ? Depuis #47 sa duree en images suit « Vitesse de transition » (State._fondu, Engine._start_battle_effect) comme tout fondu ; son horloge reste celle du jeu pour la cascade et, au retour a la
        carte, tant que le joueur est verrouille ou entre deux fondus (Game._speed_factor : des qu'il est libre, la marche acceleree et l'accelerateur agissent, #127), alors que « Vitesse de combat » agit des la fin de la cascade (ecran noir, fondu d'arrivee, messages) jusqu'au fondu de fin compris."""
        return (self.effect is not None or self.load_wait is not None or self.transition_guard > 0
                or (self.fade['n'] >= 1 and bool(self.fade.get('combat'))) or (self.background_fade['n'] >= 1 and bool(self.background_fade.get('combat'))))

    def tick_transition(self):
        """Une image du jeu (apres tick_fade) : les fenetres et la garde de la transition de combat s'ecoulent."""
        if self.entry_window > 0: self.entry_window -= 1
        if self.return_window > 0: self.return_window -= 1
        if self.transition_guard > 0: self.transition_guard -= 1

    def apply(self, packets, read_name):
        self.meshes_seen = set()
        covered = max(self.fade['a'], self.background_fade['a']) >= LOADING_COVERED; do_load = False; cam_view = False      # ecran deja couvert par un fondu au moment du chargement de carte ?
        for t, a, f in packets:
            if t == 0:
                do_load = True; cam_view = False
                if a and a[0] & 0x100: self.entry_window = BATTLE_ENTRY_WINDOW          # scene de combat (cmd_fld_load, bit 8) : le fondu lance dans la foulee est le fondu d'arrivee du combat
                self.game_map = read_name(); self.loaded_maps += 1; self.sprites.clear(); self.background = (0.0, 0.0, 0.0); self.top_background = self.bottom_background = None; self.models.clear(); self.meshes.clear(); self.mesh_state.clear(); self.object_cmds = [('carte',)]; self.cam_rot = None; self.cam_fov = None; self.cam_near = None; self.cam_far = None; self.cam_yoff = None; self.cam_free = False; self.symbols.clear(); self.icons.clear(); self.fbx.clear(); self.tint = (1.0, 1.0, 1.0); self.field_scale = 1.0; self.floats = (); self.sepia = False      # nouvelle carte : FldObject neuf, m_color blanche (FldObject.init_fld) ; le moteur renvoie la teinte de la carte apres le paquet 0
            elif t == 1: self.sepia = True           # cmd_fld_color (D12C98) = cmd_map_effect_sepia : aucun argument ; FldObject.calculateExecSepia (CDD9E0) remplace le shader de chaque materiau du decor par « <nom>_sepia » (pas celui des personnages)
            elif t == 8 and len(f) >= 6:
                self.background = tuple((f[i] + f[i + 3]) / 2 for i in range(3))     # couleur d'effacement : moyenne des deux teintes (repli, rendu hors ecran) ; le fond lui-meme est un degrade vertical (#111)
                self.top_background = tuple(float(f[i]) for i in range(3)); self.bottom_background = tuple(float(f[i + 3]) for i in range(3))      # cmd_back_color (RVA 0xD14F44) : 6 flottants -> BackColor.SetColor(haut, bas, 0) (0xCC43F8) : haut = sommets 0 et 1 du quadrilatere plein ecran, bas = sommets 2 et 3
            elif t == 33 and len(f) >= 3:           # cmd_map_color_rate (D14E44) : r, g, b ; FldObject.m_color = (r, g, b, 1) (decor des villes et des combats : FldObject.update_material_color, a chaque image, Material.color = _OrgColor (1, 1, 1, alpha) x m_color, sauf les materiaux dont la texture a « tz_ » dans son nom) ; sur la carte du monde : Field.SetColor (tuiles et symboles)
                self.tint = (float(f[0]), float(f[1]), float(f[2]))
            elif t == 27:                           # cmd_field_load : Field.Init, materiau neuf (couleur blanche) ; le moteur renvoie la teinte de la carte du monde ensuite
                self.tint = (1.0, 1.0, 1.0); self.field_scale = 1.0; self.floats = ()          # (Field.Init remet la taille de camera d'origine ; le moteur enregistre le ballon (paquet 30, emplacement 12) juste apres, a chaque chargement de la carte du monde)
            elif t == 30 and a:                     # cmd_field_scale (D12794) : entier >= 0 = Field.SetFloatingObject(Chara de cet emplacement) ; entier < 0 = Field.SetScale(flottant)
                if a[0] >= 0:
                    if a[0] not in self.floats: self.floats = self.floats + (a[0],)
                elif f and 0.0 < f[0] < 1e6: self.field_scale = min(max(float(f[0]), FIELD_SCALE[0]), FIELD_SCALE[1])         # (FieldData::setOffset : 1 + decalage / 128, decalage <= 32 : de 1,00 a 1,25)
            elif t == 28 and len(a) >= 4:           # FieldData::drawBlock : fenetre de tuiles 16x16 de la carte du monde (cols x lignes) autour de la camera
                self.field = {'x0': a[0], 'y0': a[1], 'cols': a[2], 'tuiles': a[4:4 + a[3]], 'cam': (f[0], f[1]) if len(f) >= 2 else None}
            elif t == 29 and a:                     # FieldData::draw_symbol : idx | genre << 8 + [x, y, alpha] ; 0x8000 | idx = cacher ; 0xc000 | idx = remontrer
                v = a[0]; i = v & 0xff
                if v & 0xc000 == 0xc000:
                    if i in self.symbols: self.symbols[i]['vis'] = True
                elif v & 0x8000:
                    if i in self.symbols: self.symbols[i]['vis'] = False
                elif len(f) >= 3: self.symbols[i] = {'genre': (v >> 8) & 0x7f, 'x': f[0], 'y': f[1], 'alpha': f[2], 'vis': True}
            elif t == 12 and len(a) >= 2:
                if a[1] >= 0: self.sprites[a[0]] = {'id': a[1], 'pos': None, 'col': (1, 1, 1, 1), 'pose': 0, 'dir': 0, 'vis': True, 'ech': 1.0, 'cree': self.image}
                else: self.sprites.pop(a[0], None)
            elif t == 14 and len(a) >= 2:           # cmd_chara_on_off : Chara.SetVisible(valeur != 0) = Renderer.enabled du personnage (et de son ombre)
                if a[0] in self.sprites: self.sprites[a[0]]['vis'] = a[1] != 0
            elif t == 16 and a:                     # cmd_chara_sleep_pose (D132FC) : personnage = v & 0xff ; bits 8-9 : Chara.SetSleepPose(bit 8) ; bit 10 : Chara.SetSleepDir(v >> 12) (voir lying_pose.py)
                v = a[0]; s = self.sprites.get(v & 0xff)
                if s is not None:
                    if v & 0x300:
                        s['dort'] = bool(v & 0x100)
                        if s['dort']: s['dort_rot'] = (0.0, 0)          # SetSleepPose(vrai) : quadrant 0, rotation identite (la direction suit dans le meme paquet)
                    if v & 0x400: s['dort_rot'] = PC.packet_direction(v)
            elif t == 17 and len(a) >= 2:           # cmd_chara_sleep_near (D133E4) : (defNear, decalage) ; Chara.SetSleepNear : hauteur du corps couche
                self.sleeping_height = PC.packet_height(a[1])
            elif t == 18 and a:                     # cmd_chara_pose (D13474) : v = personnage | numero << 8 : Chara.SetTexture(numero) = le personnage change de feuille de sprites (TownCharacterDraw::changePose)
                s = self.sprites.get(a[0] & 0xff)
                if s is not None and (a[0] >> 8) >= 0: s['id'] = (a[0] >> 8) | (s['id'] & 4096)
            elif t == 15 and a:                     # cmd_chara_shadow (D13150) : personnage = v & 0xff ; bits 8-9 : ombre visible (bit 8) ; bits 10-11 : ombre separee (bit 10) ; bit 12 : position de l'ombre (3 flottants,
                v = a[0]; s = self.sprites.get(v & 0xff)        # SetShadowPosition) ; bit 13 : opacite (SetShadowAlpha) ; bit 14 : position de l'ombre sur la carte du monde (SetFieldShadowPosition)
                if s is not None:
                    fl = list(f)
                    if v & 0x300: s['ombre'] = bool(v & 0x100)
                    if v & 0xc00: s['ombre_sep'] = bool(v & 0x400)
                    if v & 0x1000 and len(fl) >= 3: s['ombre_pos'] = tuple(fl[:3]); fl = fl[3:]
                    if v & 0x2000 and fl: s['ombre_a'] = float(fl[0]); fl = fl[1:]
                    if v & 0x4000 and len(fl) >= 3: s['ombre_champ'] = tuple(fl[:3])          # SetFieldShadowPosition : (x, y, hauteur) en pixels de la carte ; le ballon : 32 pixels (2 tuiles) au sud de ses pieds
            elif t == 19 and len(a) >= 2 and a[0] >= 16:            # cmd_rise_icon_load avec un emplacement >= 16 : pas une bulle, le clignotement de la croix (TouchPad.SetPadBlink) ; numero < 0 = arret
                self.pad_blink = a[1] >= 0
            elif t == 19 and len(a) >= 2 and 0 <= a[0] < 16:        # cmd_rise_icon_load : emplacement, numero d'icone (< 0 = liberation) ; objet Riseup, materiau Custom/Riseup sur la feuille MenuTexture
                if a[1] >= 0: self.icons[a[0]] = {'id': a[1], 'pos': None, 'alpha': 1.0}
                else: self.icons.pop(a[0], None)
            elif t == 20 and a and len(f) >= 4:     # cmd_rise_icon : emplacement ; x, y, z (SetPosition) puis alpha (Material.color = 1, 1, 1, alpha)
                ic = self.icons.get(a[0])
                if ic is not None: ic['pos'] = tuple(f[:3]); ic['alpha'] = f[3]
            elif t == 9 and a:                      # cmd_fade : duree en images = v & 0x7ff ; bit 12 : sortie vers une couleur (sinon entree) ; bit 11 : couleur r, g, b en flottants ; bit 13 : blanc (sinon noir) ; bit 14 : plan de fond « FadeForBG » (derriere les fenetres ; sinon plan « FadeForMenu », devant tout : voir State._fondu)
                self._fade(a[0], f)
            elif t == 5 and a:                      # cmd_fld_common_anim : objet = v & 0xffff, numero d'animation commune = v >> 16 (FldObject.SetCommonAnimation)
                self.object_cmds.append(('anim', a[0] & 0xffff, (a[0] >> 16) & 0xffff))
            elif t == 7 and a:                      # cmd_fld_on_off : objet = v & 0xffff, drapeau = v >> 16 (SetMapObjOnOff : drapeau non nul = objet masque)
                self.object_cmds.append(('onoff', a[0] & 0xffff, (a[0] >> 16) & 0xffff))
            elif t == 2 and a:                      # cmd_fld_alpha : objet = v & 0xffff, niveau (0..31) = v >> 16 & 0xff (SetMapObjAlpha : opacite = niveau / 31)
                self.object_cmds.append(('alpha', a[0] & 0xffff, (a[0] >> 16) & 0xff))
            elif t == 3 and a and len(f) >= 3:      # cmd_fld_pos : objet ; x, y, z
                self.object_cmds.append(('pos', a[0] & 0xffff, tuple(f[:3])))
            elif t == 4 and a and len(f) >= 2:      # cmd_fld_rot : objet ; rotation x, y (z = 0)
                self.object_cmds.append(('rot', a[0] & 0xffff, tuple(f[:2])))
            elif t == 10 and a:
                if do_load: cam_view = True
                elif self.loading is not None: self.loading['cam'] = True
                fl = list(f)
                if a[0] & 1 and len(fl) >= 3: self.cam_pos = tuple(fl[:3]); fl = fl[3:]
                if a[0] & 2 and len(fl) >= 3: self.cam_target = tuple(fl[:3]); fl = fl[3:]
                if a[0] & 4 and len(fl) >= 3: self.cam_rot = tuple(fl[:3])        # combat : rotation (tangage, lacet, roulis) en degres
            elif t == 21 and len(a) >= 2:           # DSSAObject::send_unity_load(emplacement, id de modele) ; id < 0 = liberation
                if a[1] >= 0:
                    self.models[a[0]] = a[1]
                    self.mesh_state[a[0]] = {'shader': 3 if a[1] > 999 else 1, 'vis': True, 'col': (1.0, 1.0, 1.0), 'off': (0.0, 0.0)}      # MeshChara..ctor : shader 1 (DssaMonster0) sauf id > 999 (DssaCharaTransparent) ; couleur blanche
                else: self.models.pop(a[0], None); self.meshes.pop(a[0], None); self.mesh_state.pop(a[0], None)
            elif t == 31 and len(a) >= 2:           # cmd_fbx_load : emplacement, numero de modele (« fbx/c<numero> », FbxObject) ; < 0 = liberation. Le modele est cree cache, sans rotation (le constructeur de FbxObject n'en pose pas ; le moteur envoie la rotation absolue au 1er paquet 32 : FbxObject.SetRotation = Quaternion.Euler puis Transform.set_rotation, 0xCD1748), echelle 1
                if a[1] >= 0: self.fbx[a[0]] = {'id': a[1], 'vis': False, 'pos': (0.0, 0.0, 0.0), 'rot': (0.0, 0.0, 0.0), 'scl': (1.0, 1.0, 1.0), 'col': (1.0, 1.0, 1.0, 1.0), 'anim': []}
                else: self.fbx.pop(a[0], None)
            elif t == 32 and a:                     # cmd_fbx : emplacement = v & 0xff ; bits 8-9 : visibilite (bit 8 = visible) ; 10 : forcer l'animation ; 11 : echelle (3 flottants) ; 12 : couleur (4) ; 13 : position (3) ; 14 : rotation, degres (3) ; 15 : animation (un entier : sequence)
                v = a[0]; m = self.fbx.get(v & 0xff); fl = list(f)
                if FBXLOG: print('FBX image %d paquet 32 : v=%#x ints=%s flottants=%s' % (self.image, v & 0xffff, list(a[1:]), [round(x, 4) for x in fl]), flush=True)         # (test) DQ_FBXLOG=1 : tous les paquets 32 (position, rotation, echelle, couleur, sequence)
                if m is not None:
                    if v & 0x300: m['vis'] = bool(v & 0x100)
                    if v & 0x800 and len(fl) >= 3: m['scl'] = tuple(fl[:3]); fl = fl[3:]
                    if v & 0x1000 and len(fl) >= 4: m['col'] = tuple(fl[:4]); fl = fl[4:]
                    if v & 0x2000 and len(fl) >= 3: m['pos'] = tuple(fl[:3]); fl = fl[3:]
                    if v & 0x4000 and len(fl) >= 3: m['rot'] = tuple(fl[:3]); fl = fl[3:]
                    if v & 0x8000 and len(a) >= 2: m['anim'].append((self.image, int(a[1]), bool(v & 0x400)))
            elif t == 23 and len(a) >= 2:           # cmd_mesh_on_off : emplacement, visible
                if a[0] in self.mesh_state: self.mesh_state[a[0]]['vis'] = bool(a[1])
            elif t == 24 and a:                     # cmd_mesh_shader : emplacement | numero de shader << 8 (0 Chara, 1 DssaMonster0, 2 DssaMonster1, 3 DssaCharaTransparent)
                if (a[0] & 0xff) in self.mesh_state: self.mesh_state[a[0] & 0xff]['shader'] = a[0] >> 8
            elif t == 25 and a and len(f) >= 3:     # cmd_mesh_color : emplacement ; r, g, b (Material.color, alpha 1)
                if a[0] in self.mesh_state: self.mesh_state[a[0]]['col'] = tuple(f[:3])
            elif t == 26 and a and len(f) >= 2:     # cmd_mesh_tex_offset : emplacement ; u, v (Material.SetTextureOffset)
                if a[0] in self.mesh_state: self.mesh_state[a[0]]['off'] = tuple(f[:2])
            elif t == 11 and a:        # cmd_camera_sub : bit 0 near, 1 far, 2 fov, 4 yOffset, 5 lookDownAdjust (un flottant chacun, dans l'ordre des bits), 7 camera libre (s_targetCamera = faux)
                k = 0
                for bit, name_str in ((0, 'cam_near'), (1, 'cam_far'), (2, 'cam_fov'), (4, 'cam_yoff'), (5, 'cam_down')):
                    if a[0] >> bit & 1 and k < len(f):
                        v = f[k]; k += 1
                        setattr(self, name_str, min(max(v, 0.0), 78.0) if name_str == 'cam_fov' else v)       # SceneCamera.SetFOV2 : borne a 78
                if a[0] & 128: self.cam_free = True
            elif t == 22 and len(a) >= 2:           # maillage dynamique : [emplacement, nb sommets, couleurs (1 octet/sommet, 4 par entier), indices...] + flottants [x, y, z, (u, v, x, y, z) * nb sommets]
                nv = a[1]; nc = (nv + 3) // 4; idx = a[2 + nc:]
                if len(f) >= 3 + 5 * nv and idx:
                    v = [f[3 + 5 * i:8 + 5 * i] for i in range(nv)]
                    self.meshes[a[0]] = {'pos': tuple(f[:3]), 'v': v, 'idx': list(idx), 'col': list(a[2:2 + nc])}       # col : un octet par quad (4 sommets), 255 = opaque
                    self.meshes_seen.add(a[0])
            elif t in (35, 36, 37) and a:           # cmd_se_play / cmd_se_stop / cmd_bgm (Sound.PlaySE, StopSE, PlayBGM ; valeur >= 4096 = StopBGM)
                self.sounds.append((t, a[0]))
                if t == 37: self.music = a[0] if 0 <= a[0] < 4096 else None
            elif t == 13 and a:
                fl = list(f); flags = a[0]; s = self.sprites.get(flags & 0x7ff)
                if s is None: continue
                if flags & 0x800 and fl:                # cmd_chara (D12EA8) : bit 11 = Chara.SetScale(echelle) : Transform.localScale = 1,8 x echelle sur le panneau du personnage (pas sur son ombre)
                    if s['pos'] is not None: s['ech'] = float(fl[0])      # (la 1re mise a jour d'un personnage, celle qui le place, porte une valeur de depart sans suite : 0,0253 a 0,08 puis 1,0 en une image ; observee sur 529 cartes, 1062 personnages : ignoree)
                    fl = fl[1:]
                if flags & 0x1000: s['col'] = tuple(fl[:4]); fl = fl[4:]
                if flags & 0x2000 or flags & 0x8000: s['pos'] = tuple(fl[:3]); fl = fl[3:]      # 0x8000 : meme position, version carte du monde (pixels)
                if flags & 0x4000 and len(a) > 1:
                    s['pose'] = a[1] & 0xff; s['dir'] = (a[1] >> 8) & 0xff
                    if s['pos'] is None and self.image - s.get('cree', 0) >= ORIGIN_AFTER: s['pos'] = (0.0, 0.0, 0.0)       # le moteur n'envoie une position que si elle change de celle qu'il croit deja posee (son enregistrement du personnage : (0, 0, 0)) :
                                                                          # un personnage anime qui n'en a pas recu au bout de quelques images est a l'origine (Chara cree a (0, 0, 0) par Unity) ; mqtf3, mom2f1, msm1f1, emplacement 8 : le PNJ
                                                                          # du milieu de la piece n'etait pas dessine. (Les positions des autres arrivent 1 image apres la creation : pas d'apparition d'une image a l'origine.)
        if do_load:         # chargement de carte : dessin retenu (voir update_loading) si l'ecran est couvert, soit par un fondu deja la, soit par le fondu d'entree lance avec ce chargement (il repart de l'opacite 1)
            if covered or any(fd['a'] >= LOADING_COVERED and fd['fin'] == 0.0 and fd['n'] >= 1 for fd in (self.fade, self.background_fade)): self.loading = {'n': -1, 'cam': cam_view}
            else: self.loading = None

    def _fade(self, v, f):
        """Fade.SetFadeIn / SetFadeOutBlack / SetFadeOutWhite / SetFadeOutColor (FadePlane.Command) : sortie = vers l'opacite 1 depuis l'opacite courante ;
        entree = le plan repart de l'opacite 1 vers 0 (Unity part de l'opacite courante du plan : meme chose apres une sortie terminee). Duree <= 1 image : immediat."""
        script = bool(v & PJ.SCRIPT_FADE_MARK)                                          # fondu lance par une commande de script du jeu (marque posee par Engine._fade_hooks) : sa duree est celle du script
        d = v & 0x7ff; fd = self.background_fade if v & 0x4000 else self.fade; fd['noir'] = 0      # bit 14 : Fade.l_targetLayer (NativeManager.cmd_fade D14D10), le plan qui recoit la commande
        fd['combat'] = self.part == PART_BATTLE or self.entry_window > 0 or self.return_window > 0        # fondu d'un combat (arrivee dans la scene, sortie, retour a la carte) : marque pour battle_transition (sa duree suit « Vitesse de transition » comme tout fondu au noir, #47)
        d0 = d
        if not v & (0x800 | 0x2000): d = PJ.fade_duration(d, State.fade_speed, script)       # fondu au noir (changement de carte, arrivee en combat, fin de combat, retour a la carte) plus court : reglage « vitesse des transitions » (pas pour un fondu de script)
        self.fade_ratio = (self.image, (d / d0) if d0 > 1 and v & 0x1000 else 1.0)      # fondu au noir raccourci : le decompte du bruitage de sortie du moteur suit (Engine._exit_countdown)
        if v & 0x1000:
            fd['col'] = tuple(f[:3]) if v & 0x800 and len(f) >= 3 else ((1.0, 1.0, 1.0) if v & 0x2000 else (0.0, 0.0, 0.0))
            fd['fin'] = 1.0
            if d <= 1: fd['a'] = 1.0; fd['n'] = 0; fd['pas'] = 0.0
            else: fd['pas'] = (1.0 - fd['a']) / d; fd['n'] = d
        else:
            fd['fin'] = 0.0
            if d <= 1: fd['a'] = 0.0; fd['n'] = 0; fd['pas'] = 0.0
            else: fd['a'] = 1.0; fd['pas'] = -1.0 / d; fd['n'] = d

    def sharp_black_fade(self):
        """Fade.SetFadeOutBlack(0) sur le plan 0 (devant tout) : opaque, noir, tout de suite (fin des effets lampe et Riremito) ; il reste ainsi jusqu'a un fondu d'entree lance par le moteur."""
        fd = self.fade; fd['noir'] = 0; fd['col'] = (0.0, 0.0, 0.0); fd['fin'] = 1.0; fd['a'] = 1.0; fd['n'] = 0; fd['pas'] = 0.0; fd['combat'] = False

    def current_fade_in(self, frames):
        """Fade.SetFadeIn(images) sur le plan 0 (arrivee d'un voyage, Capture.Tabi) : de l'opacite COURANTE du plan vers 0, en `frames` pas egaux (FadePlane.Command, IN) : sans effet visible si le plan est transparent, et
        le bit « fondu en cours » de Global.Flag reste leve pendant `frames` images (CheckFade), comme dans le jeu."""
        fd = self.fade; fd['noir'] = 0; fd['fin'] = 0.0; fd['pas'] = -fd['a'] / frames; fd['n'] = frames

    def update_loading(self):
        """Fin de la retenue du dessin apres un chargement de carte (une fois par image du moteur, apres `apply`). La visionneuse n'a vu que le paquet 0 (nouveau decor) a l'image du chargement : camera de la scene
        d'avant, personnages sans position, ni teinte ni ordres d'objets ; le moteur envoie la camera (paquet 10) et les positions (paquet 13) a l'image suivante (59 cartes essayees, 529 cartes comptees : toujours le decalage 1).
        Tant que `loading` existe, la fenetre ne dessine que les plans de fondu (noir de l'ecran couvert) et les fondus d'entree sont suspendus (`tick_fade`) : le fondu du jeu garde toute sa duree, il commence juste
        une image plus tard, sur une scene complete. Prete : au moins LOADING_MIN image, camera recue, et personnages visibles tous places (au plus LOADING_PLACEMENT images d'attente) ; garde-fou LOADING_MAX."""
        ch = self.loading
        if ch is None: return
        ch['n'] += 1                                                       # images du moteur depuis le chargement (0 a l'image du chargement : compte propre, pas de difference d'images : un etat charge peut remettre le compteur d'images a zero)
        places = all(sp['pos'] is not None for sp in self.sprites.values() if sp.get('vis', True))
        world = self.part != PART_FIELD or self.field is not None      # carte du monde : attendre aussi ses tuiles (paquet 28)
        if ch['n'] >= LOADING_MAX or (ch['n'] >= LOADING_MIN and world and ch['cam'] and (places or ch['n'] >= LOADING_PLACEMENT)): self.loading = None

    def tick_fade(self):
        """FadePlane.Update : une fois par image du jeu, pour chacun des deux plans. Garde-fou (plan de devant seulement) : un ecran reste tout noir plus de 6 s (fondu d'entree lance par Unity lui-meme, pas par le moteur) est rouvert ;
        le plan de fond n'en a pas : le moteur le tient noir de lui-meme (titre de chapitre, 160 images) et le rouvre par une commande."""
        for fd, guard in ((self.fade, True), (self.background_fade, False)):
            if self.loading is not None and fd['fin'] == 0.0 and fd['n'] >= 1: continue      # retenue du dessin apres un chargement : un fondu d'entree ne commence qu'avec la scene en place
            if fd['n'] >= 1:
                fd['n'] -= 1
                if fd['n'] < 1:
                    fd['a'] = fd['fin']
                    if fd.get('combat') and fd['fin'] >= 1.0: self.transition_guard = TRANSITION_GUARD      # sortie au noir d'un combat finie : le moteur change de scene dans 1 a 3 images, puis lance le fondu d'entree ; l'horloge ne doit pas changer entre les deux
                else: fd['a'] += fd['pas']
            if guard and fd['a'] >= 0.999 and fd['n'] < 1:
                fd['noir'] += 1
                if fd['noir'] > 180: fd['fin'] = 0.0; fd['pas'] = -1.0 / 15; fd['n'] = 15; fd['noir'] = 0
            else: fd['noir'] = 0


DBG = bool(os.environ.get('DQ_UIDBG'))


class Interface:
    """Ce que l'interface Unity memorise des messages du moteur : une fenetre par port (liste de textes, curseur, ouverte ou non).
    Messages d'un port (apres le premier octet = nombre d'arguments) : [1,..] ouvre ; [7,0] ferme ; [11,ligne,colonne] annonce
    que le message suivant du port est le texte de cette case ; [4,i] curseur sur la ligne i ; [12,ligne,x] et [10,..] reglages."""
    def __setstate__(self, state): self.__dict__.update(_renamed_attributes(state))

    def __init__(self):
        self.f = {}; self.waiting = {}; self.order = 0
        self.msg = {'type': 0, 'y': 0, 'feed': False, 'shake': 0, 'qui': '', 'qui_att': False}      # fenetre de message (port 1) : type de fenetre, defilement du canevas, curseur de fin de page, nom de l'interlocuteur (« qui ») ; qui_att : le paquet suivant du port porte ce nom
        self.damage = []           # nombres de degats a faire sauter sur les monstres : (monstre, hauteur, degats), vides par la visionneuse
        self.system = []          # messages du port 0 adresses a l'hote : (code, arguments...) ; 999 = quitter (MenuPortSendQuit), 6 = portail, 4 / 5 = volumes, 7 = taille du nom, 8 = manette
        self.obs = None            # observateur facultatif (visionneuse) : ouvrir(port, type), fermer(port), param_int/param_str/code/selection

    def win(self, port):
        if port not in self.f: self.f[port] = {'cases': {}, 'vis': False, 'cur': 0, 'ordre': 0, 'indic': {}, 'type': None, 'act': False, 'req': False, 'draw': False, 'force': False, 'ign': False, 'sv': True}
        return self.f[port]

    def apply(self, entries):
        if DBG:
            for port, a in entries:
                if port in (0, 1) or port >= 12: print('MSG image %s port %d %s' % (getattr(self, 'image', '?'), port, a[:10]), flush=True)
        for port, a in entries:
            if port == 1:                                       # fenetre de message : dessinee d'apres le canevas du moteur ; MenuMessage.NoticeReceive : 0 type, 1 curseur, 2 secousse, 3 defilement, 4 nom de l'interlocuteur
                if self.msg['qui_att']:                         # [4, 1] a annonce un nom : le paquet suivant du port en est le texte (un entier par caractere, comme les textes des cases des menus)
                    self.msg['qui_att'] = False; self.msg['qui'] = ''.join(chr(v & 0xffff) for v in a if v).strip()
                    continue
                if len(a) >= 2:
                    c, v = a[0], a[1]
                    if c == 0: self.msg['type'] = v
                    elif c == 1: self.msg['feed'] = (v & 0xffff) == 1
                    elif c == 3: self.msg['y'] = v
                    elif c == 4:                                # [4, 0] : pas de nom (cadre sans onglet) ; [4, 1] : le nom suit (cadre avec onglet, seulement pour la fenetre du terrain : MenuMessage.NoticeReceive, commande 4)
                        if (v & 0xffff) != 0: self.msg['qui_att'] = True
                        else: self.msg['qui'] = ''
                continue
            if port == 0:
                if len(a) >= 2 and a[0] == 0: self.system.append(tuple(a[1:]))
                if len(a) >= 2 and 2 <= a[0] < 32:
                    if a[1] == 3: self.win(a[0])['sv'] = bool(a[2]) if len(a) > 2 else True       # [fenetre, 3, visible] : MenuPort.SetVisible
                    elif a[1] == 2:                                                                # [fenetre, 2] : fermee
                        f = self.win(a[0]); f['act'] = f['vis'] = False; f['ferme'] = True          # (les messages d'arret du moteur peuvent remettre « act » : « ferme » reste jusqu'a la creation suivante)
                        if self.obs: self.obs.shutdown(a[0])
                    elif a[1] == 1 and len(a) >= 4:                                                # [fenetre, 1, categorie, type] : cree un menu du type donne (MenuPortItemTable.Make_*)
                        f = self.win(a[0]); f['type'] = a[3]; f['cases'] = {}; f['indic'] = {}; f['cur'] = 0; f['ints'] = {}; f['dispo'] = None; f['listes'] = {}; f['suite'] = None
                        f['act'] = f['req'] = f['draw'] = f['force'] = f['ign'] = False; f['sv'] = True; f['vis'] = False; f['att'] = None; f['plaq'] = {}; f['n_codes'] = {}; f['ferme'] = False
                        if self.obs: self.obs.open_menu(a[0], a[3])
                continue
            f = self.win(port)
            if f.get('ferme'):                                  # MenuPortSystem.internalUpdate (D10A54) : [port, 2] detruit l'element (`s_ports[port] = null`), les messages du port recus ensuite (meme image : les ports 12 a 31 sont lus apres le port 0)
                self.waiting.pop(port, None)                    # n'ont plus de destinataire (`if (item != null) item.NoticeReceive`) ; avant, la fin de la liste des journaux (5, 6, 4) rouvrait la fenetre fermee une image : boite « simple » violette
                continue
            if f['type'] == 43:                                 # Make_BattleHoppingNumber : [12, 0, 0] puis [monstre, hauteur, degats] (BattleMenu_setHoppingNumbers)
                if f.get('dgt'):
                    f['dgt'] = False
                    if len(a) >= 3: self.damage.append(tuple(a[:3]))
                    continue
                if len(a) >= 3 and a[0] == 12: f['dgt'] = True; continue
            if port in self.waiting:                            # texte de la case annoncee
                lookup_key = self.waiting.pop(port); txt = ''.join(chr(v & 0xffff) for v in a if v); f['cases'][lookup_key] = txt
                if self.obs: self.obs.param_str(port, lookup_key[0], lookup_key[1], txt)
                continue
            if f.get('suite') is not None:                      # fenetre de carte (type 25) : la liste de nombres qui suit les codes 3 (lieux decouverts) et 5 (voile) du moteur (MenuPort.Receive des fonctions de Make_CityMap), pas une commande
                f.setdefault('listes', {})[f['suite']] = [v & 0xffff for v in a]; f['suite'] = None
                continue
            if f['type'] == 31 and f.get('att'):               # plaque de monstre : messages qui suivent un code > 0 (nom, puis [x, y, ...])
                i, stage = f['att']
                if stage == 'nom': f['plaq'][i]['nom'] = ''.join(chr(v & 0xffff) for v in a if v); f['att'] = (i, 'prm')
                else:
                    f['plaq'][i]['prm'] = list(a); f['att'] = None
                    if self.obs and hasattr(self.obs, 'plate'): self.obs.plate(port, i, f['plaq'][i]['nom'], f['plaq'][i]['prm'], f['plaq'][i]['code'])
                continue
            if not a: continue
            cmd = a[0]
            if cmd != 7 and not f['act']: f['act'] = True; f['force'] = True       # MenuPortItem.NoticeReceive : premiere commande -> parties activees, dessin force
            if cmd == 11 and len(a) >= 3: self.waiting[port] = (a[1], a[2])
            elif cmd == 1:
                if port >= 12: f['cases'] = {}; f['indic'] = {}; f['cur'] = 0; f['ints'] = {}; f['listes'] = {}; f['suite'] = None           # fenetre dynamique : contenu neuf
                self.order += 1; f['ordre'] = self.order
            elif cmd == 2 and len(a) >= 3: f['grille'] = tuple(a[1:4])                 # setItemMenu : colonnes, lignes, nombre de cases du curseur du moteur
            elif cmd == 6: f['inp'] = True                                              # demande de saisie (a chaque image tant que le menu attend une touche)
            elif cmd == 5: f['req'] = True                                             # demande de dessin : le moteur la renvoie a chaque image tant que la fenetre doit etre vue
            elif cmd == 7: f['act'] = False                                            # arret : parties desactivees
            elif cmd == 8 and len(a) >= 2: f['ign'] = (a[1] & 0xffff) != 0            # ignorer les demandes de dessin (toujours visible)
            elif cmd == 4 and len(a) >= 2:
                f['cur'] = a[1]
                if self.obs: self.obs.selection(port, a[1])
            elif cmd == 10 and len(a) >= 5:                    # setItemParamInt [id, no, bas, haut] : valeur 32 bits
                v = (a[3] & 0xffff) | ((a[4] & 0xffff) << 16); v = v - (1 << 32) if v & 0x80000000 else v
                f.setdefault('ints', {})[(a[1], a[2])] = v                                   # gardes pour rejouer la fenetre (etats instantanes)
                if self.obs: self.obs.param_int(port, a[1], a[2], v)
            elif cmd == 12 and len(a) >= 3:
                f['indic'][a[1]] = a[2]; f.setdefault('n_codes', {})[a[1]] = f.get('n_codes', {}).get(a[1], 0) + 1          # nombre de fois que chaque code est arrive (le titre : TapToStart.CountReset = code 0 du port 12)
                if f['type'] == 25 and a[1] in (3, 5): f['suite'] = a[1]               # ICityMap : code 3 = lieux decouverts (x + 256 y, un par nombre), code 5 = voile (16 nombres : un bit par bloc de 10 x 10 pixels non explore)
                if f['type'] == 31 and a[1] < 4 and a[2] >= 1:                                  # MonsterNamePlate.ReceiveParameters(code >= 1)
                    f.setdefault('plaq', {})[a[1]] = {'code': a[2]}; f['att'] = (a[1], 'nom')
                elif f['type'] == 31 and a[1] == 5:                                             # disposition des plaques (nombre de plaques)
                    f['dispo'] = a[2]
                    if self.obs and hasattr(self.obs, 'arrange'): self.obs.arrange(port, a[2])
                elif self.obs: self.obs.code(port, a[1], a[2])

        for f in self.f.values():                              # MenuPortItem.Update : visible tant que le moteur demande le dessin a chaque image
            if not f['ign']:
                if f['force']: f['force'] = False; f['draw'] = f['req']
                elif f['draw'] != f['req']: f['draw'] = f['req']
            f['req'] = False; f['entree'] = f.get('inp', False); f['inp'] = False
            f['vis'] = f['act'] and f['sv'] and (f['draw'] or f['ign'])

    def visible_ones(self):
        return sorted(((p, f) for p, f in self.f.items() if f['vis'] and f['cases']), key=lambda x: x[1]['ordre'])


class Engine:
    def __init__(self, apk_folder, read_folder, write_folder, language=1):
        self.log = Silent()
        self.missing_hooks = []               # reglages / crochets que le moteur de CET apk n'a pas laisse installer (voir _manque) ; la fenetre les annonce une fois (Game._report_missing_hooks)
        lib = zipfile.ZipFile(os.path.join(apk_folder, 'split_config.arm64_v8a.apk')).read(LIB_APK)
        pack = os.path.join(apk_folder, 'split_UnityDataAssetPack.apk')
        self.apk_data = pack
        GameCore.read_folder, GameCore.write_folder = read_folder, write_folder
        c = self.core = GameCore(lib, T.ApkFs([pack]), self.log, real_files={'/dq/assets.apk': pack})
        self.E = c.export; self.L = c.LIB_BASE
        self._widen_symbols()
        if not c.run_init(): raise RuntimeError('constructeurs C++ en echec')
        c.call(self.E('DevInit'), c.cstr('/dq/assets.apk'), c.cstr('/dq/'), language)
        self.buf1, self.buf2 = c.malloc(0x2000), c.malloc(0x2000)          # files de messages interface <-> moteur (allouees par l'appelant)
        c.call(self.E('MenuPortInit'), 32, self.buf1, 129, self.buf2, 1089)
        BUFFER_SIZE = 0x40000
        c.inp, c.outp, c.outf, c.strb = c.malloc(BUFFER_SIZE), c.malloc(BUFFER_SIZE), c.malloc(BUFFER_SIZE), c.malloc(0x10000)
        c.call(self.E('GameInit'), c.inp, c.outp, c.outf, c.strb)
        c.mem_w(self.L + G_IS_AMAZON, b'\x01')              # menu de depart : pas de « Sauv. cloud » (Google Play Games / serveur Square Enix absents sur PC) ; l'original retire la meme case pour la version Amazon
        self.pk = PacketLog(c)
        self.state = State()
        self.msgs_ui = []                        # messages moteur -> interface (menus), derniere image
        self.ui = Interface()                    # fenetres de menu memorisees
        self.frames = 0; self._countdown = 0; self._countdown_armed = -99; self._countdown_done = True      # decompte du bruitage de sortie (voir _exit_countdown)
        # animations d'objets de la carte (portes...) : le moteur attend qu'Unity les termine (bit0 de l'octet +0x14 de l'entree)
        self.anims = []                          # [(image d'echeance, index d'objet)]
        self.anim_duration = None                   # (objet, numero) -> images avant la fin de l'animation commune (donnee par la fenetre, d'apres les donnees de la carte) ; None = ANIM_DURATION
        self.fldobj = 0
        self.msg_visible = False                 # fenetre de message affichee ? (MenuPort::SetVisible sur le port du message)
        def _sv(uc, a, sz, u):
            port = uc.reg_read(c.XREG[0]) & 0xffffffffffff
            if port and port == struct.unpack('<Q', c.mem(self.L + OBJ_MESSAGE + 0x30, 8))[0]:
                self.msg_visible = bool(uc.reg_read(c.XREG[1]) & 0xff)
                if not self.msg_visible: self._text_accumulator = 0.0; self.ui.msg['qui'] = ''; self.ui.msg['qui_att'] = False        # MenuMessage.SetVisible(false) efface le texte du nom (m_who)
        hv = c.export('_ZN8MenuPort10SetVisibleEb')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, _sv, None, hv, hv)
        self.fielddata = 0; self._grid = None; self._grid_frame = -999
        self.back_to_title_state = None            # retour au titre : None, 'ouvrir' (a lancer au prochain pas) ou 'dialogue' (la boite Oui / Non du jeu attend la reponse) ; voir request_return_to_title
        self.request_pause = False               # le joueur a choisi « Paramètres » dans le menu Divers : la visionneuse ouvre son menu Pause (voir _divert_params)
        self._divert_params()
        def _fd(uc, a, sz, u): self.fielddata = uc.reg_read(c.XREG[0]) & 0xffffffffffff          # FieldData::drawBlock(this) : l'objet qui porte la carte du monde
        hfd = c.export('_ZN9FieldData9drawBlockEv')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, _fd, None, hfd, hfd)
        def _sca(uc, a, sz, u): self.fldobj = uc.reg_read(c.XREG[0])
        uc_hook = c.export('_ZN9FLDObject18SetCommonAnimationEii')
        c.uc.hook_add(unicorn.UC_HOOK_CODE, _sca, None, uc_hook, uc_hook)
        self._text_hooks()
        self._fade_hooks()
        self._level_hooks()
        self._encounter_hooks()
        self._day_clock_hooks()
        self._game_time_hooks()
        self._magic_hooks()
        self.sensor = Sensor(self)             # historique des dialogues : crochet sur TextBuffer::cat (installe avant la premiere image : Unicorn garde les blocs deja traduits)
        self.battle_sensor = BattleSensor.for_(self)       # historique des combats : crochets en lecture seule (ennemis vaincus, or, experience ; voir battle_history.py)
        if not self.sensor.active: self._record_missing(tr("historique des dialogues : crochet non installe, l'historique restera vide"))
        if not self.battle_sensor.active: self._record_missing(tr("historique des combats : crochets non installes, l'historique des combats restera vide"))
        for _ in range(3): self.step(0, 0)       # le titre tourne quelques images (curseurs initialises)
        self._create_canvas()

    def _record_missing(self, text):
        """Un reglage ou un crochet n'a pas pu etre installe (instruction du moteur differente : autre version de l'apk). Le jeu continue avec le comportement d'origine ; la ligne va dans la console et dans `missing_hooks`
        (sans doublon : reapply_fixes repasse ici apres le chargement d'un etat), d'ou la fenetre la note dans erreurs_fenetre.log et prévient le joueur par un message a l'ecran."""
        print(text, flush=True)
        if text not in self.missing_hooks: self.missing_hooks.append(text)

    def _text_hooks(self):
        """Vitesse du texte des dialogues et defilement des combats (reglages du joueur, menu Echap).
        - Texte : ui_MsgLoop ecrit, a chaque image du moteur (30 Hz), `speed x 4` lettres (vitesse = mot a MSG_SPEED, copie du tableau du type de fenetre : 1 pour les dialogues, 100 pour les fenetres de combat qui
          affichent leur ligne d'un coup). Un crochet sur `sxth w20, w8` remplace ce nombre par celui du reglage (`text_speed`, lettres par image, fractions cumulees ; 4 = comme le jeu : le crochet ne fait rien).
        - Combats : BattleAutoFeed lit OptionStatus.battleSpeed (g_Option + 5, option « Vitesse des messages » du jeu, enregistree dans la sauvegarde) a chaque message : `scroll_mode` (None = on ne touche a rien)
          est ecrit a cette adresse avant chaque image ; un changement fait par le joueur dans la fenetre Parametres du jeu (setBattleSpeed appele depuis TownMenu_OPERATION_SETTING::menuUpdate) est
          signale a `scroll_callback(value)` (le chargement d'une sauvegarde, lui, passe par Profile::deliverDATA_PARTY et ne declenche rien)."""
        c = self.core
        self.text_speed = 4.0; self._text_accumulator = 0.0
        self.scroll_mode = None; self.scroll_callback = None; self._scroll_origin = None
        try:
            a = c.export('_Z10ui_MsgLoopv')
            if a and struct.unpack('<I', c.mem(a + UI_MSGLOOP_WRITE, 4))[0] == SXTH_W20_W8:        # autre version du moteur : on ne touche a rien
                def _vt(uc, ad, sz, u):
                    game = uc.reg_read(c.XREG[8]) & 0xffff                                  # lettres que le moteur s'apprete a ecrire (mot de vitesse de la fenetre x 4)
                    v = PJ.letters_per_frame(self.text_speed, game)                      # reglage du joueur seulement tant que le jeu est a sa vitesse standard (4) ; une autre valeur (100 des fenetres de combat, vitesse fixee par le jeu) est la sienne
                    if v == game: return                                                    # vitesse du jeu : inchange (aussi quand le reglage est « comme le jeu », 4)
                    self._text_accumulator += v; n = int(self._text_accumulator); self._text_accumulator -= n
                    uc.reg_write(c.XREG[8], min(n, 4000))
                c.uc.hook_add(unicorn.UC_HOOK_CODE, _vt, None, a + UI_MSGLOOP_WRITE, a + UI_MSGLOOP_WRITE)
            else: self._record_missing(tr('vitesse du texte : ui_MsgLoop inattendu, reglage sans effet'))
        except Exception as ex: self._record_missing(tr('vitesse du texte non installee : %s') % (ex,))
        try:
            sb = c.export('_ZN6status12OptionStatus14setBattleSpeedEc'); mu = c.export('_ZN26TownMenu_OPERATION_SETTING10menuUpdateEv')
            if sb and mu:
                def _sb(uc, ad, sz, u):
                    if self.scroll_mode is not None and self.scroll_callback is not None and mu <= uc.reg_read(c.XREG[30]) < mu + 0x400: self.scroll_callback(uc.reg_read(c.XREG[1]) & 0xff)
                c.uc.hook_add(unicorn.UC_HOOK_CODE, _sb, None, sb, sb)
        except Exception as ex: self._record_missing(tr('defilement des combats : crochet non installe : %s') % (ex,))

    def _level_hooks(self):
        """Option « PV et PM restaures au niveau superieur » (`level_heal`, faux = comme le jeu). Toute montee de niveau passe par `HaveStatus::levelup(bool)` : elle recalcule les caracteristiques, puis, si l'argument est vrai
        (c'est le cas de `debugLevelup`), remet PV et PM a leur maximum (`tbz w20, #0` a +0x3f8 : PV <- PV max, PM <- PM max). Un crochet sur cette instruction force le bit quand l'option est active ; le reste du calcul est celui du jeu."""
        c = self.core; self.level_heal = False
        try:
            a = c.export('_ZN6status10HaveStatus7levelupEb')
            if not a or struct.unpack('<I', c.mem(a + HAVESTATUS_LEVELUP_END, 4))[0] != TBZ_W20_0:
                self._record_missing(tr('PV/PM au niveau superieur : HaveStatus::levelup inattendu, option sans effet')); return
            def _heal(uc, ad, sz, u):
                if self.level_heal: uc.reg_write(c.XREG[20], uc.reg_read(c.XREG[20]) | 1)
            c.uc.hook_add(unicorn.UC_HOOK_CODE, _heal, None, a + HAVESTATUS_LEVELUP_END, a + HAVESTATUS_LEVELUP_END)
            try: c.uc.ctl_flush_tb()
            except Exception: pass
        except Exception as ex: self._record_missing(tr('PV/PM au niveau superieur : crochet non installe : %s') % (ex,))

    def _encounter_hooks(self):
        """Rencontres aleatoires et marche acceleree (voir encounters.py). `walking_speed` (ecrit par la visionneuse avant chaque pas : facteur d'acceleration de la marche, 1 = normale ; toujours 1 en combat)
        > 1 : le crochet sur `str w8, [x0]` de `CountDown::exec` (w9 = compteur avant, w8 = apres) remplace la perte du compteur par (1 + a) / (2 a) fois celle du jeu, de sorte que les rencontres par seconde
        reelle soient (1 + a) / 2 fois celles de x1 et non a fois. A 1 (ou moins) : le crochet ne fait rien (le jeu d'origine, a l'identique)."""
        c = self.core; self.walking_speed = 1.0; self.encounters = RE.Reducer()
        try:
            a = c.export('_ZN9CountDown4execEv')
            if not a or struct.unpack('<I', c.mem(a + COUNTDOWN_EXEC_WRITE, 4))[0] != STR_W8_X0:
                self._record_missing(tr('rencontres : CountDown::exec inattendu, vitesse de marche sans effet sur la frequence des rencontres')); return
            def _cd(uc, ad, sz, u):
                v = self.walking_speed
                if v <= 1.0: return                                                          # x1 : le jeu tel quel
                r = self.encounters; r.factor = RE.factor_per_step(v)
                before = uc.reg_read(c.XREG[9]) & 0xffffffff; after = uc.reg_read(c.XREG[8]) & 0xffffffff
                before -= (before & 0x80000000) << 1; after -= (after & 0x80000000) << 1      # entiers signes de 32 bits (le compteur devient negatif au declenchement)
                uc.reg_write(c.XREG[8], (before - r.retain(before - after)) & 0xffffffff)
            c.uc.hook_add(unicorn.UC_HOOK_CODE, _cd, None, a + COUNTDOWN_EXEC_WRITE, a + COUNTDOWN_EXEC_WRITE)
            try: c.uc.ctl_flush_tb()
            except Exception: pass
        except Exception as ex: self._record_missing(tr('rencontres : crochet non installe : %s') % (ex,))

    def _day_clock_hooks(self):
        """Arrivee de la nuit et marche acceleree (voir encounters.py, #163). Le temps du monde n'avance que par le saut terminal `FieldStage::ChangeTime(0)` de `FieldPlayerDoku::checkDokuDamage` (+ 0x38, carte du monde,
        a chaque image du moteur ou le heros a avance). `walking_speed` > 1 : ce saut n'a lieu que pour la fraction (1 + a) / (2 a) des appels (`Passer`) ; pour les autres, le crochet va directement au `ret` de la
        fonction (la pile est deja depilee a cet endroit), de sorte que la nuit arrive (1 + a) / 2 fois plus vite par seconde reelle et non a fois. A 1 (ou moins) : le jeu d'origine, a l'identique."""
        c = self.core; self.day_clock = RE.Passer()
        try:
            f = c.export('_ZN15FieldPlayerDoku15checkDokuDamageERN3dss12Fix32Vector3ES2_')
            u32 = lambda a: struct.unpack('<I', c.mem(a, 4))[0]
            w = u32(f + DOKU_CHANGETIME_B) if f else 0
            if not f or w & 0xfc000000 != 0x14000000 or f + DOKU_CHANGETIME_B + ((((w & 0x3ffffff) ^ 0x2000000) - 0x2000000) << 2) != c.LIB_BASE + DOKU_CHANGETIME_STUB or u32(f + DOKU_RET) != RET_A64:
                self._record_missing(tr("horloge jour / nuit : checkDokuDamage inattendu, la vitesse de marche change la vitesse d'arrivee de la nuit")); return
            def _hj(uc, ad, sz, u):
                v = self.walking_speed
                if v <= 1.0: return                                                          # x1 : le jeu tel quel
                p = self.day_clock; p.factor = RE.factor_per_step(v)
                if not p.allows(): uc.reg_write(unicorn.arm64_const.UC_ARM64_REG_PC, f + DOKU_RET)        # appel saute : retour direct (la pile est deja rendue, x30 = adresse de retour de l'appelant)
            c.uc.hook_add(unicorn.UC_HOOK_CODE, _hj, None, f + DOKU_CHANGETIME_B, f + DOKU_CHANGETIME_B)
            try: c.uc.ctl_flush_tb()
            except Exception: pass
        except Exception as ex: self._record_missing(tr('horloge jour / nuit : crochet non installe : %s') % (ex,))

    def _game_time_hooks(self):
        """Temps de jeu de la sauvegarde sur l'heure reelle (#239, audit ENG-04, sondage du 04/11/2026). Le moteur ajoute 2 unites (1/60 s) par pas (`GameStatus::addPlayTime(2)` dans `Global::NativeExec`) : a x1
        (30 pas par seconde) c'est l'heure reelle, mais la marche acceleree et le combat rapide font `a` fois plus de pas par seconde et le temps de jeu (et l'horodatage de l'historique, qui le lit) court `a` fois trop vite.
        `clock_speed` (ecrit par la visionneuse avant chaque pas : facteur d'acceleration de l'horloge du jeu, marche ET combat ; 1 = normale) > 1 : le crochet saute l'appel (retour directement a l'instruction suivante, rien
        d'autre n'est touche : x0 et w1 ne servent plus) pour la fraction 1 - 1 / a des pas (`Passer`), regulierement. A 1 (ou moins, ralenti) : le jeu d'origine, a l'identique."""
        c = self.core; self.clock_speed = 1.0; self.game_time = RE.Passer()
        try:
            f = c.export('_ZN6Global10NativeExecEv'); ad = c.export('_ZN6status10GameStatus11addPlayTimeEj')
            u32 = lambda a: struct.unpack('<I', c.mem(a, 4))[0]; u64 = lambda a: struct.unpack('<Q', c.mem(a, 8))[0]
            w = u32(f + PLAYTIME_BL) if f else 0
            stub = struct.unpack('<4I', c.mem(c.LIB_BASE + PLAYTIME_STUB, 16))                                  # (le stub PLT : adrp x16 ; ldr x17, [x16, #0x968] ; add x16, x16, #0x968 ; br x17 : sa case de la table des adresses, 0x240968, contient addPlayTime)
            if not f or not ad or u32(f + PLAYTIME_MOV_W1) != MOV_W1_2 or w & 0xfc000000 != 0x94000000 or f + PLAYTIME_BL + ((((w & 0x3ffffff) ^ 0x2000000) - 0x2000000) << 2) != c.LIB_BASE + PLAYTIME_STUB \
                    or stub != PLAYTIME_STUB_WORDS or u64(c.LIB_BASE + PLAYTIME_GOT) != ad:
                self._record_missing(tr('temps de jeu : NativeExec inattendu, la vitesse du jeu change la vitesse du temps de jeu')); return
            def _tj(uc, a, sz, u):
                v = self.clock_speed
                if v <= 1.0: return                                                          # x1 : le jeu tel quel
                p = self.game_time; p.factor = 1.0 / v
                if not p.allows(): uc.reg_write(unicorn.arm64_const.UC_ARM64_REG_PC, a + 4)       # appel saute
            c.uc.hook_add(unicorn.UC_HOOK_CODE, _tj, None, f + PLAYTIME_BL, f + PLAYTIME_BL)
            try: c.uc.ctl_flush_tb()
            except Exception: pass
        except Exception as ex: self._record_missing(tr('temps de jeu : crochet non installe : %s') % (ex,))

    def _magic_hooks(self):
        """Sorts du menu Magie (hors combat) qui coutent des PM mais n'en depensent aucun : le moteur ne depense les PM que si le sort a eu un effet (`BaseAction::useMp`), mais pour les soins il annonce quand meme le message
        de succes (la table des actions donne le meme texte au succes et a l'echec : « Les blessures de X guerissent ! » a PV pleins). Le menu Magie lance le sort par `UseAction::execUse` a deux endroits (choix d'une
        cible : `TownMenu_MAGIC_CHARSELECT::menuUpdate` ; sort de groupe ou sans cible : `TownMenu_MAGIC_ROOT::useMagicNoTarget`) puis affiche `param + 0x1f8` (« X lance le sort Y ! ») et la liste `param + 0x210`.
        Un crochet avant l'appel note les PM du lanceur, un crochet apres compare : si le sort coute des PM (table `excelParam`), que les PM n'ont pas baisse et que le jeu annonce son message de succes (champs 1 / 3 de la
        table des messages) ou aucun, la liste devient le message du jeu « Mais il ne se passe rien. » (`MSG_NOTHING_OCCURS`, une seule fois, meme pour un groupe). Les messages d'echec propres au jeu (Rappel, Antipoison, Evac'...) et le combat ne changent pas.
        Bruitages (mesures au moteur reel) : le lancement joue le bruitage 306 (le meme pour tous les sorts : il reste toujours) ; le message de resultat joue ensuite le bruitage de soin 501 (`menuUpdate` + 0x110, pour les actions 196 a 198 : Premiers secours, Soins
        partiels, Soins complets, NO_DEFAULT regarder si le soin a servi) : quand le sort n'a eu aucun effet, ce deuxieme bruitage est coupe (un seul `sub` modifie avant l'instruction : la sortie de comparaison passe a 3, au-dessus de 2). Un sort de groupe sans effet ne le joue deja plus (boucle des cibles vide)."""
        c = self.core; self._magic = None; self._magic_mute = False; self._magic_without_effect = False
        try:
            cs, nt = c.export('_ZN25TownMenu_MAGIC_CHARSELECT10menuUpdateEv'), c.export('_ZN19TownMenu_MAGIC_ROOT16useMagicNoTargetEv')
            msg, exc = c.export('_ZN6status17BaseActionMessage12actionParam_E'), c.export('_ZN6status10excelParamE')
            u32 = lambda a: struct.unpack('<I', c.mem(a, 4))[0]; u64 = lambda a: struct.unpack('<Q', c.mem(a, 8))[0]
            def is_exec_use(a):                                                            # `bl` vers le stub de UseAction::execUse ?
                w = u32(a); return w & 0xfc000000 == 0x94000000 and a + ((((w & 0x3ffffff) ^ 0x2000000) - 0x2000000) << 2) == c.LIB_BASE + MAGIC_EXECUSE_STUB
            sites = [(cs + MAGIC_CHARSELECT_BL, False), (nt + MAGIC_WITHOUT_TARGET_BL, True)] if cs and nt and msg and exc else []
            if not sites or not all(is_exec_use(a) for a, _ in sites) or u32(u64(msg) + 0x48 * 201 + 0x14) != MSG_NOTHING_HAPPENS:
                self._record_missing(tr('sorts sans effet : menu Magie inattendu, le message de succes est garde')); return
            def _before(uc, ad, sz, u):
                p = uc.reg_read(c.XREG[0]) & 0xffffffffffff; caster = u64(p); action = u32(p + MAGIC_ACTION)
                cost = c.mem(u64(exc + 0x70) + 0x48 * action + 0x3a, 1)[0]                  # UseAction::getUseMp
                self._magic = (p, caster, struct.unpack('<H', c.mem(caster + MAGIC_MP, 2))[0], cost, action) if caster and cost else None; self._magic_without_effect = False
            def place(group):
                def _after(uc, ad, sz, u):
                    m, self._magic = self._magic, None
                    if not m: return
                    p, caster, mp, cost, action = m
                    if struct.unpack('<H', c.mem(caster + MAGIC_MP, 2))[0] < mp: return        # PM depenses : le sort a eu un effet
                    e = u64(msg) + 0x48 * action; r = u32(p + MAGIC_RESULT)
                    if r and r not in (u32(e + 4), u32(e + 0xc)): return                    # le jeu a deja son message d'echec
                    c.mem_w(p + MAGIC_RESULT, struct.pack('<II', MSG_NOTHING_OCCURS, 0))
                    if not group: self._magic_without_effect = True                              # le bruitage de soin de l'etape suivante est coupe (voir _son)
                    if group: c.mem_w(self.L + MAGIC_TARGET_COUNT, b'\x01'); self._magic_mute = True      # un seul exemplaire du message (le moteur l'affiche une fois par cible vivante)
                return _after
            for (a, group) in sites:
                c.uc.hook_add(unicorn.UC_HOOK_CODE, _before, None, a, a); c.uc.hook_add(unicorn.UC_HOOK_CODE, place(group), None, a + 4, a + 4)
            def _end(uc, ad, sz, u):                                                       # sortie de la boucle des cibles : plus de bruitage de soin en attente (menuUpdate en joue un par cible restante) si rien ne s'est passe
                if self._magic_mute: self._magic_mute = False; c.mem_w(self.L + MAGIC_TARGET_COUNT, b'\x00')
            c.uc.hook_add(unicorn.UC_HOOK_CODE, _end, None, nt + MAGIC_LOOP_END, nt + MAGIC_LOOP_END)
            if u32(cs + MAGIC_HEAL_SOUND) == SUB_W8_W8_C4:
                def _sound(uc, ad, sz, u):                                                   # avant `sub w8, w8, #0xc4` : le sort n'a eu aucun effet -> w8 = 0xc7 (resultat 3 > 2) : pas de bruitage de soin
                    if self._magic_without_effect: self._magic_without_effect = False; uc.reg_write(c.XREG[8], 0xc7)
                c.uc.hook_add(unicorn.UC_HOOK_CODE, _sound, None, cs + MAGIC_HEAL_SOUND, cs + MAGIC_HEAL_SOUND)
            else: self._record_missing(tr('sorts sans effet : bruitage de soin inattendu, il est garde'))
            try: c.uc.ctl_flush_tb()
            except Exception: pass
        except Exception as ex: self._record_missing(tr('sorts sans effet : crochet non installe : %s') % (ex,))

    def _fade_hooks(self):
        """Fondus lances par une commande de SCRIPT du jeu (fade_in / fade_out : `__cmd_fade_in::initialize`, `__cmd_fade_out::initialize`, qui appellent Global::fadeIn / fadeOutBlack... puis UnitySetFade avec la duree
        du script, et attendent eux-memes ce nombre d'images : `isEnd` compte les images) : le paquet 9 recoit la marque PJ.SCRIPT_FADE_MARK, et State._fondu ne raccourcit pas ce fondu (reglage « vitesse des
        transitions » : il vaut pour les fondus du moteur, changements de carte..., pas pour ceux qu'un script a fixes). Sans la marque, le fondu raccourci laisserait l'ecran noir jusqu'a la fin de l'attente du script."""
        c = self.core; self._script_fade = False
        try:
            ini = [c.export('_ZN13__cmd_fade_in10initializeEPc'), c.export('_ZN14__cmd_fade_out10initializeEPc')]; usf = c.export('_Z12UnitySetFadei')
            if not all(ini) or not usf: self._record_missing(tr('fondus de script : fonctions du moteur introuvables, reglage applique a tous les fondus')); return
            def end_of(a):                                                       # adresse apres le `ret` de la fonction
                for k in range(80):
                    if struct.unpack('<I', c.mem(a + 4 * k, 4))[0] == 0xd65f03c0: return a + 4 * (k + 1)
                return None
            ends = [end_of(a) for a in ini]
            if None in ends or struct.unpack('<I', c.mem(usf + 8, 4))[0] != 0x5280012a:        # UnitySetFade : `mov w10, #9` (type du paquet) a +8 ; autre version du moteur : on ne touche a rien
                self._record_missing(tr('fondus de script : UnitySetFade inattendu, reglage applique a tous les fondus')); return
            def _entry(uc, ad, sz, u): self._script_fade = True
            def _exit(uc, ad, sz, u): self._script_fade = False
            def _packet(uc, ad, sz, u):
                if self._script_fade:
                    self._script_fade = False
                    uc.reg_write(c.XREG[0], (uc.reg_read(c.XREG[0]) & 0xffffffff) | PJ.SCRIPT_FADE_MARK)
            for a, f in zip(ini, ends):
                c.uc.hook_add(unicorn.UC_HOOK_CODE, _entry, None, a, a); c.uc.hook_add(unicorn.UC_HOOK_CODE, _exit, None, f - 4, f - 4)
            c.uc.hook_add(unicorn.UC_HOOK_CODE, _packet, None, usf, usf)
            try: c.uc.ctl_flush_tb()                                             # (blocs deja traduits avant les crochets)
            except Exception: pass
        except Exception as ex: self._record_missing(tr('fondus de script : crochet non installe : %s') % (ex,))

    def _option(self, offset):
        """Adresse d'un octet de status::g_Option (OptionStatus : +1 volume de la musique, +2 volume des bruitages (0 a 4), +5 vitesse des messages de combat)."""
        ad = self.core.export('_ZN6status8g_OptionE')
        return (ad if ad else self.L + 0x25b564) + offset

    def game_options(self):
        """(volume musique, volume bruitages, vitesse des messages de combat) des options du jeu (fenetre Parametres, enregistrees dans la sauvegarde)."""
        c = self.core
        return c.mem(self._option(1), 1)[0], c.mem(self._option(2), 1)[0], c.mem(self._option(5), 1)[0]

    def impose_scroll_mode(self, code):
        """Defilement des messages de combat impose a chaque image (code 0 a 3 : attente de 12 / 22 / 32 / 42 images, 4 : a la main) ; None : on rend la valeur du jeu (celle de la sauvegarde, ou choisie dans ses Parametres)."""
        if code is None:
            if self.scroll_mode is not None and self._scroll_origin is not None: self.core.mem_w(self._option(5), bytes([self._scroll_origin]))
            self.scroll_mode = None; self._scroll_origin = None
        else:
            if self.scroll_mode is None: self._scroll_origin = self.game_options()[2]
            self.scroll_mode = int(code) & 0xff; self.core.mem_w(self._option(5), bytes([self.scroll_mode]))

    def write_scroll_mode(self):
        """Avant chaque image du moteur : la valeur imposee est ecrite ; si le jeu en avait mis une autre (chargement d'une sauvegarde ou d'un etat, fenetre Parametres), c'est elle qu'on rendra."""
        if self.scroll_mode is None: return
        ad = self._option(5); cur = self.core.mem(ad, 1)[0]
        if cur != self.scroll_mode: self._scroll_origin = cur
        self.core.mem_w(ad, bytes([self.scroll_mode]))

    def message_state(self):
        """(test) (message ouvert, etat de ui_MsgLoop, lettre courante, fin de ligne, vitesse du type de fenetre)."""
        c = self.core; g = lambda off: struct.unpack('<H', c.mem(self.L + off, 2))[0]
        return c.mem(self.L + MSG_ACTIVE, 1)[0], g(MSG_STATE), g(MSG_CURRENT), g(MSG_END), g(MSG_SPEED)

    def reapply_fixes(self):
        """Remet les correctifs que la visionneuse pose dans la memoire du moteur (fenetre des lieux elargie, pas de « Sauv. cloud », bouton « Paramètres », vitesses de marche d'origine). Appelee apres le chargement d'un etat
        (etats.appliquer) : l'image d'origine de la bibliotheque est rechargee d'abord, et un etat enregistre par une version qui n'avait pas encore un correctif ne le contient pas. Chacun est idempotent."""
        self._widen_symbols()
        self.core.mem_w(self.L + G_IS_AMAZON, b'\x01')
        self.reset_speeds()
        self.patch_params()
        self.back_to_title_state = None            # un etat charge pendant la boite du retour au titre : la boite n'existe plus (memoire du moteur remplacee)

    def _widen_symbols(self):
        """FieldData::drawSymbol ne montre les lieux de la carte du monde (villes, grottes...) que dans la fenetre de l'ecran portrait d'origine autour du heros
        (x de -192 a +448, y de -192 a +788 pixels, plus une marge) : en 16/9 les lieux des cotes n'apparaissaient qu'une fois tout pres. Les trois constantes de
        la fonction (add w22/w23/w24, w9, #imm) sont portees a 1600 pixels : la fenetre couvre tout ce que la visionneuse peut montrer, meme dezoomee."""
        c = self.core
        try:
            a = c.export('_ZN9FieldData10drawSymbolEv')
            words = [struct.unpack('<I', c.mem(a + dec, 4))[0] for dec in (0x44, 0x48, 0x4c)]
            if all(w & 0xffc003e0 == 0x11000120 and (w >> 10) & 0xfff == 1600 for w in words): return        # deja elargie (reapply_fixes)
            for w, imm in zip(words, (0xc0, 0x1c0, 0x314)):
                if w & 0xffc003e0 != 0x11000120 or (w >> 10) & 0xfff != imm:
                    self._record_missing(tr('fenetre des lieux non elargie : FieldData::drawSymbol inattendu, les lieux de la carte du monde n\'apparaissent que dans la fenetre d\'origine')); return        # autre version du moteur : on ne touche a rien
            for dec in (0x44, 0x48, 0x4c):
                w = struct.unpack('<I', c.mem(a + dec, 4))[0]
                c.mem_w(a + dec, struct.pack('<I', (w & ~(0xfff << 10)) | (1600 << 10)))
        except Exception as ex:
            self._record_missing(tr('fenetre des lieux non elargie : %s') % (ex,))

    # TownMenu_OPERATION_ROOT::menuUpdate (liste du menu Divers) : « cmp w8, #7 » (0x16ef28) suivi de « b.ne » vers la sortie « bouton inconnu » ; le bouton 7 (« Paramètres ») ferme le menu et ouvre TownMenu_OPERATION_SETTING
    CMP_PARAMS = 0x16ef28

    def patch_params(self):
        """Le bouton « Paramètres » du menu Divers ouvre le menu Pause de la visionneuse, pas les reglages d'origine du jeu (volumes, vitesse, taille de la croix, retour au titre) : la comparaison du numero du bouton choisi a 7
        est portee a 4095 (jamais egale : le moteur traite l'appui comme celui d'un bouton inconnu, ne ferme pas le menu Divers et n'entre pas dans l'etat « Parametres »). Sans effet si c'est deja fait ou si le moteur est une autre
        version. Rappelee apres le chargement d'un etat (etats.appliquer remet l'image d'origine de la bibliotheque)."""
        c = self.core; ad = c.LIB_BASE + self.CMP_PARAMS; w = struct.unpack('<I', c.mem(ad, 4))[0]
        if w == 0x71001d1f: c.mem_w(ad, struct.pack('<I', (w & ~(0xfff << 10)) | (0xfff << 10)))       # « cmp w8, #7 » -> « cmp w8, #4095 »
        elif w != 0x713ffd1f: self._record_missing(tr("bouton Paramètres : comparaison du menu Divers inattendue, le bouton ouvre les reglages d'origine du jeu et non le menu Pause"))        # (0x713ffd1f = deja patche)

    def _divert_params(self):
        """Patch du bouton « Paramètres » (patch_params) et crochet sur la comparaison : il leve `request_pause` quand le bouton choisi est le 7 ; la visionneuse n'a plus qu'a ouvrir son menu Pause (Game.tick)."""
        c = self.core
        try:
            self.patch_params(); ad = c.LIB_BASE + self.CMP_PARAMS
            def _p(uc, a, sz, u):
                if uc.reg_read(c.XREG[8]) & 0xffffffff == 7: self.request_pause = True
            c.uc.hook_add(unicorn.UC_HOOK_CODE, _p, None, ad, ad)
        except Exception as ex:
            self._record_missing(tr('bouton Paramètres non detourne : %s') % (ex,))

    def _create_canvas(self):
        c = self.core
        # canevas de texte des messages : Unity le cree par un message de port (largeur, hauteur) ; on appelle directement le gestionnaire
        self.obj_msg = self.L + OBJ_MESSAGE
        shorts = [0]
        for v in (1, 0, CANVAS_L, CANVAS_H, 0): shorts += [v & 0xffff, (v >> 16) & 0xffff]
        mp = c.malloc(64); c.mem_w(mp, struct.pack('<%dH' % len(shorts), *shorts))
        c.call(self.E('_ZN9SDrawCTRL11CanvasSetupEPvPKs'), self.obj_msg, mp, label='CanvasSetup')

    def _global(self):
        return struct.unpack('<Q', self.core.mem(self.L + GLOBAL_PTR, 8))[0]

    def start_field(self):
        """(essai) force le passage a la carte du monde : Global::startField()."""
        self.core.call(self.E('_ZN6Global10startFieldEv'), self._global(), label='startField')

    def back_to_title(self):
        """Retour a l'ecran-titre : la fin du bouton « Revenir à l'écran titre » des Parametres d'origine du jeu quand on repond « Oui » (TownMenu_OPERATION_SETTING::menuUpdate, etat 5) : efface la banque 4
        (sauvegarde automatique, killbank), ferme la boite, verrouille le joueur, puis Global::startTitle() (fondu au noir de 30 images lance par UnitySetFade(0x101e), chapitre 0, la partie suivante est le titre). A
        appeler PENDANT un pas (voir _return_to_title_after) : le paquet du fondu doit etre lu avec ceux du pas, sinon le fondu est perdu (le tampon est remis a zero au pas suivant) et l'ecran passe au noir d'un coup."""
        c = self.core
        c.call(self.E('_ZN7profile8SaveLoad8killbankEib'), 4, 0, label='killbank')
        self._close_title_box()
        c.call(self.E('_ZN3cmn11GameManager12getSingletonEv'), label='getSingleton')
        c.call(self.E('_ZN3cmn13PlayerManager7setLockEb'), 1, label='setLock')
        c.call(self.E('_ZN6Global10startTitleEv'), self._global(), label='startTitle')

    def request_return_to_title(self):
        """Menu Pause > « Revenir à l'écran titre » : ouvre la boite du jeu (son texte, Oui / Non) au prochain pas, comme le bouton des Parametres d'origine. -> faux si une demande est deja en cours.
        « Non » ferme la boite et rend la main au joueur ; « Oui » lance back_to_title, avec le fondu du jeu. Les deux suites sont jouees par `_return_to_title_after`, apres chaque GameUpdate.
        Seulement en ville et sur la carte du monde, les deux parties ou le menu des Parametres d'origine existe et ou la boite repond (essai : en combat, la boite s'ouvre mais ne recoit ni les touches ni
        les clics, le menu de commandes du combat garde la main ; non verifie dans les boutiques et les jeux du casino)."""
        if self.back_to_title_state is not None or self.state.part not in (PART_TOWN, PART_FIELD): return False
        self.back_to_title_state = 'ouvrir'; return True

    def _title_box(self): return self.core.export('gTownMenu_MESSAGE')

    def _close_title_box(self):
        c = self.core; m = self._title_box()
        if m and c.call(self.E('_ZN8MenuBase6isOpenEv'), m, label='isOpen') & 1: c.call(self.E('_ZN8MenuBase5closeEv'), m, label='close')

    def _return_to_title_before(self):
        """Avant GameUpdate : ouvre la boite. Meme suite d'appels que l'etat 5 du menu des Parametres d'origine (menuUpdate + 0x1ac) : openMessageForMENU, addMessage(0xCBA2F), setYesNo() (curseur sur « Oui »),
        setYesNoSuperCancel(false) ; le joueur est verrouille comme dans le menu du jeu (PlayerManager::setLock(true), rendu par « Non »)."""
        if self.back_to_title_state != 'ouvrir': return
        c = self.core; m = self._title_box(); self.back_to_title_state = 'dialogue'
        c.call(self.E('_ZN3cmn11GameManager12getSingletonEv'), label='getSingleton')
        c.call(self.E('_ZN3cmn13PlayerManager7setLockEb'), 1, label='setLock')
        c.call(self.E('_ZN16TownMenu_MESSAGE18openMessageForMENUEv'), m, label='openMessageForMENU')
        c.call(self.E('_ZN16TownMenu_MESSAGE10addMessageEi'), m, MSG_RETURN_TITLE, label='addMessage')
        c.call(self.E('_ZN16TownMenu_MESSAGE8setYesNoEv'), m, label='setYesNo')
        c.call(self.E('_ZN16TownMenu_MESSAGE19setYesNoSuperCancelEb'), m, 0, label='setYesNoSuperCancel')
        c.mem_w(m + MESSAGE_RESULT, bytes(4))                # la reponse d'une boite precedente ne compte pas (MenuBase::menuBaseSetup la remet a 0 quand le menu est ajoute ; ici il peut deja l'etre : message d'un PNJ en cours)

    def _return_to_title_after(self):
        """Apres GameUpdate, avant la lecture des paquets : la reponse de la boite (TownMenu_MESSAGE + 0x10, comme le fait menuUpdate du menu des Parametres d'origine). 2 = Non : on ferme la boite et on
        rend la main (setLock(false), l'inverse de l'ouverture). 1 = Oui : back_to_title, dans ce pas, donc avec son fondu."""
        if self.back_to_title_state != 'dialogue': return
        c = self.core; r = struct.unpack('<I', c.mem(self._title_box() + MESSAGE_RESULT, 4))[0]
        if r == 2:
            self.back_to_title_state = None; self._close_title_box()
            c.call(self.E('_ZN3cmn11GameManager12getSingletonEv'), label='getSingleton')
            c.call(self.E('_ZN3cmn13PlayerManager7setLockEb'), 0, label='setLock')
        elif r == 1:
            self.back_to_title_state = None; self.back_to_title()
        elif not c.call(self.E('_ZN8MenuBase6isOpenEv'), self._title_box(), label='isOpen') & 1:          # fermee sans reponse (la scene du moteur a repris la boite : un message de plus d'un script, par exemple) : la demande tombe, le joueur est libere
            self.back_to_title_state = None
            c.call(self.E('_ZN3cmn11GameManager12getSingletonEv'), label='getSingleton')
            c.call(self.E('_ZN3cmn13PlayerManager7setLockEb'), 0, label='setLock')

    def start_town(self, name_str):
        """(essai) charge une ville ou un donjon : Global::startTown(nom). Refuse un nom sans fichier de carte (`assets/map/<name_str>.stg`) : le moteur d'origine ne le teste pas et plante (pointeur nul dans FldStage::getCameraLimitL),
        par exemple `za3f3`, carte orpheline (`.map` et `.fld` dans le paquet graphique, aucun `.stg`) (#76)."""
        if self.core.fs is not None and self.core.fs.open('map/%s.stg' % name_str) is None: raise ValueError("carte inconnue : pas de fichier assets/map/%s.stg dans les donnees du jeu" % name_str)
        self.core.call(self.E('_ZN6Global9startTownEPKc'), self._global(), self.core.cstr(name_str.encode()), label='startTown')

    # vitesse de marche du heros (Fix32 par pas du moteur, valeurs d'origine de libdq4core) : villes (deux variables), carte du monde (Speed, plus les deux constantes locales 0x27520c et 0x275210 que
    # FieldPlayer::move lit en diagonale). La course accelere l'horloge du moteur (viewer, _boucle), pas ces valeurs ; on ne les remet a l'origine qu'au chargement d'un etat (voir reset_speeds)
    ORIGIN_SPEEDS = (('_ZN16TownPlayerAction9walkSpeedE', 819), ('_ZN16TownPlayerAction10walkSpeed2E', 655), ('_ZN11FieldPlayer5SpeedE', 12288), (0x27520c, 8192), (0x275210, 8192))

    def reset_speeds(self):
        """Remet les vitesses de marche du heros a leurs valeurs d'origine : un etat enregistre par une ancienne version pendant une course les contient majorees (la course n'y touche plus)."""
        c = self.core
        for n, base in self.ORIGIN_SPEEDS:
            ad = c.LIB_BASE + n if isinstance(n, int) else c.export(n)
            if ad: c.mem_w(ad, struct.pack('<i', base))

    def shops(self):
        """(indice courant, nombre) des boutiques de la liste de la carte d'une ville (TownImageMap::execute : deux statiques locales, 0x2750c4 et 0x2750c8 ; la liste est la fenetre de type 24)."""
        c = self.core; b = c.LIB_BASE
        return struct.unpack('<hh', c.mem(b + 0x2750c4, 2) + c.mem(b + 0x2750c8, 2))

    def camera_town(self):
        """Camera des villes du moteur d'origine (TownCamera, objet statique) : (limite gauche, limite droite, verrou) ; limite = 0 : rotation libre, < 0 : rotation interdite, > 0 : angle borne (unites de 1 / 4096 de tour) ; verrou : camera verrouillee par un evenement."""
        c = self.core; ad = c.export('_ZN10TownCamera11m_singletonE')
        if ad is None: return 0, 0, False
        lg, ld = struct.unpack('<ii', c.mem(ad + 0x34, 8)); return lg, ld, bool(c.mem(ad + 0x3e, 1)[0])

    def camera_game(self):
        """Etat de la TownCamera du moteur (objet statique), pour savoir si le jeu pilote la camera : (verrou +0x3e, mode de cible +0x48, verrou de point de vue +0x40, deplacement en cours +0x43)."""
        c = self.core; ad = c.export('_ZN10TownCamera11m_singletonE')
        if ad is None: return 0, 0, 0, 0
        b = c.mem(ad + 0x3e, 6); return b[0], struct.unpack('<i', c.mem(ad + 0x48, 4))[0], b[2], b[5]

    def camera_wait(self):
        """Rotation de camera que le jeu vient d'accepter (TownPlayerManager + 0x698, CAMERA_ROT_TYPE) : ROT_CAM_RIGHT ou ROT_CAM_LEFT tant que le bouton tenu a ce pas n'a pas encore tourne la camera (verrou du joueur, scene, lieu qui interdit
        de la tourner : le jeu n'y touche pas et la valeur reste 0), ROT_CAM_NORD pendant le retour au nord."""
        c = self.core; ad = c.export('_ZN17TownPlayerManager11m_singletonE')
        return 0 if ad is None else struct.unpack('<i', c.mem(ad + 0x698, 4))[0]

    def camera_turn(self, direction, times):
        """`times` rotations de plus de la camera du jeu (sens : ROT_CAM_RIGHT ou ROT_CAM_LEFT), chacune exactement celle d'un pas du moteur (setCameraRotType puis TownPlayerManager::setCameraRot : TownCamera::rotateL / rotateR, qui borne selon les limites
        du lieu, et rotation de la direction du groupe pour que le heros garde son cap a l'ecran). Sert au reglage « Vitesse de camera » (le jeu ne tourne que d'un cran par pas) et au glissement du clic molette. Appelee apres un pas qui a pris le bouton (camera_wait)
        : les rotations de ce pas SONT ces `times` appels (le premier consomme celle que le bouton a mise en attente)."""
        c = self.core; ad = c.export('_ZN17TownPlayerManager11m_singletonE')
        if ad is None: return
        a, b = self.E('_ZN17TownPlayerManager16setCameraRotTypeE15CAMERA_ROT_TYPE'), self.E('_ZN17TownPlayerManager12setCameraRotEv')
        for _ in range(times): c.call(a, ad, direction, label='camera'); c.call(b, ad, label='camera')

    def dpad_size(self):
        """Option « Taille de la croix » du jeu (g_pad_size) : 0 Grande, 1 Moyenne (par defaut), 2 Petite."""
        v = self.core.mem(self.core.LIB_BASE + 0x24a779, 1)[0]
        return v if v in (0, 1, 2) else 1

    def awaits_touch(self):
        """Vrai quand le menu du don d'experience (`MaterielMenu_EXTRA_PRESENT_EXP`, ajout du mobile : le roi de Burland au chapitre 1) est ouvert et a son dernier etat : une fois les niveaux montres, `menuUpdate` (etat +0x30 = 2)
        attend un declenchement du pad du jeu (`dss::g_Pad + 2`, rempli par `Global::NativeExec` d'apres le 2e argument de `GameUpdate` : le toucher d'ecran, exactement 0x100, ou les boutons 0x400 a 0x2000), avant de fermer le menu et de
        rendre la main au scenario. La touche A d'un message (0x10) ne le leve jamais : la fenetre envoie alors le toucher (voir Game._entrees). « Ouvert » : le menu est dans le tableau du gestionnaire `MenuManager` (son etat reste a 2 apres
        la fermeture jusqu'a la creation suivante)."""
        try:
            c = self.core; L = self.L
            ges = int.from_bytes(c.mem(L + MENU_MANAGER, 8), 'little')
            if not ges: return False
            menu = L + MENU_GIFT_EXP
            if not any(int.from_bytes(c.mem(ges + 8 + 8 * i, 8), 'little') == menu for i in range(OPENED_MENUS)): return False
            return c.mem(menu + MENU_GIFT_EXP_STATE, 1)[0] == MENU_GIFT_EXP_WAIT
        except Exception: return False

    def flags(self):
        """Global.Flag : premier mot de la sortie du moteur (bit 3 : manette tactile presente ; 4 verrou du joueur, 0x20 carte autorisee, 0x40 interface verrouillee...)."""
        return struct.unpack('<I', self.core.mem(self.core.outp, 4))[0]

    def _effect_flag(self, active):
        """Bit 1 de Global+0xd8 : Unity (Capture.ScreenEffect) le leve au debut d'un effet d'ecran et l'abaisse a la fin ; le moteur attend qu'il retombe."""
        ad = self.core.outp; v = struct.unpack('<I', self.core.mem(ad, 4))[0]
        self.core.mem_w(ad, struct.pack('<I', (v | 2) if active else (v & ~2)))

    def _start_battle_effect(self, before):
        """Paquet 34 (valeur 4) : l'ecran se brise en morceaux (BATTLE_EFFECT_FRAMES images) pendant que le moteur attend ; ensuite l'ecran reste noir jusqu'au chargement de la scene du combat."""
        if self.state.effect is not None: return
        self.state.effect = {'n': 0, 'duree': PJ.fade_duration(BATTLE_EFFECT_FRAMES, State.fade_speed)}; self._effect_flag(True)      # la cascade suit « Vitesse de transition » comme les fondus : 57 images a x1, 57 / facteur ensuite (la simulation avance de 57 images au total, voir Game._draw_effect)
        if self.state.load_wait is None: self.state.load_wait = {'base': before, 'n': 0}

    def _battle_effect(self):
        """Une image du jeu : avance l'effet de debut de combat, abaisse le drapeau a la fin (le moteur reprend a l'image suivante) ; compte l'attente du chargement."""
        ef = self.state.effect
        if ef is not None:
            ef['n'] += 1
            if ef['n'] >= ef.get('duree', BATTLE_EFFECT_FRAMES): self._effect_flag(False); self.state.effect = None
        ac = self.state.load_wait
        if ac is not None:
            ac['n'] += 1
            if ac['n'] > LOAD_WAIT_MAX + BATTLE_EFFECT_FRAMES: self.state.load_wait = None

    def _start_screen_effect(self, value):
        """Paquet 34, valeurs 3 (voyage : ailes de Chimere), 5 (lampe : Ranaruta) et 6 (Riremito) : Capture.ScreenEffect leve le bit 1 de Global.Flag, que le moteur attend, et lance une coroutine qui dure
        EF.FRAMES[...] images (63 a 64 au depart, 45 a l'arrivee d'un voyage) ; la fenetre dessine l'effet (fenetre/capture_effects.py), voir _screen_effect. Bit 7 de la valeur : bReverse (voyage : arrivee) ou bMorning
        (lampe : teinte du matin). Comme la cascade du combat, l'effet suit « Vitesse de transition » (moins d'images du moteur)."""
        kind = EF.KINDS.get(value & 0xf)
        if kind is None or self.state.screen_effect is not None: return
        bit7 = bool(value & 0x80); inverse = kind == 'tabi' and bit7; frames = EF.frames_of(kind, inverse)
        self.state.screen_effect = {'n': 0, 'duree': PJ.fade_duration(frames, State.fade_speed), 'images': frames, 'genre': kind, 'inverse': inverse, 'matin': kind == 'lampe' and bit7}
        self._effect_flag(True)

    def _screen_effect(self):
        """Une image du jeu : avance l'effet Capture en cours. Le noir immediat (lampe, Riremito : Fade.SetFadeOutBlack(0)) et le fondu d'entree de l'arrivee d'un voyage (Fade.SetFadeIn(30)) sont lances a leur appel de
        MoveNext ; a la fin, le drapeau retombe (le moteur reprend a l'image suivante). Fin du depart d'un voyage : l'ecran reste noir (State.black_screen) jusqu'a la fin de l'arrivee. L'ecran noir est abandonne s'il
        dure trop (garde-fou) ou si le jeu revient au titre."""
        e = self.state
        if e.black_screen is not None:
            e.black_screen['n'] += 1
            if e.black_screen['n'] > BLACK_SCREEN_MAX or e.part == PART_INITIAL or e.game_map == TITLE_MAP: e.black_screen = None
        ef = e.screen_effect
        if ef is None: return
        ef['n'] += 1; kind = ef['genre']; calls = EF.calls_made(ef['n'], ef['duree'], ef['images'])
        if kind in EF.BLACK_CALL and calls >= EF.BLACK_CALL[kind] and not ef.get('noir'): ef['noir'] = True; e.sharp_black_fade()
        if ef['inverse'] and calls >= EF.FADE_IN_CALL and not ef.get('fondu'): ef['fondu'] = True; e.current_fade_in(EF.FADE_IN)
        if ef['inverse'] and calls >= ef['images']: e.black_screen = None            # dernier appel de l'arrivee (etat 4) : la camera du jeu est rendue au jeu, la scene reparait
        if ef['n'] >= ef['duree']:
            self._effect_flag(False); e.screen_effect = None
            if kind == 'tabi' and not ef['inverse']: e.black_screen = {'n': 0}

    def _map_name(self):
        s = self.core.read_cstr(self.L + RESOURCE_NAME).decode('latin-1')
        return s.split('/')[-1]

    def step(self, held=0, decl=None):
        """Une image du jeu. tenu = touches maintenues (marche) ; decl = touches qui viennent d'etre pressees (boutons, menus).
        Les fondus d ecran sont rejoues dans Etat (tick_fade). -> liste de paquets"""
        if decl is None: decl = held
        c = self.core
        w = struct.unpack('<I', c.mem(c.outp, 4))[0]            # bit 0 : « un fondu est en cours » (Fade.FadePlane.CheckFade : images restantes > 0). Le moteur le leve lui-meme en lancant un fondu (UnitySetFade) puis attend qu'il retombe
        w2 = (w | 1) if self.state.fade_in_progress() else (w & ~1)      # (Global::IsFadeEnd : auberge, titres de chapitre, ecran de chargement, ouverture des menus, sifflet...)
        if w2 != w: c.mem_w(c.outp, struct.pack('<I', w2))
        self._finish_anims()
        self._battle_effect(); self._screen_effect()
        if os.environ.get('DQ_CALLHOP'):                                       # (test) "image:monstre:hauteur:degats,..." : appelle BattleMenu_setHoppingNumbers comme le moteur apres un coup
            for spec in os.environ['DQ_CALLHOP'].split(','):
                im, ch, hh, nn = [int(x) for x in spec.split(':')]
                if self.frames == im: self.ui.image = self.frames; c.call(self.E('_Z27BattleMenu_setHoppingNumbersss'), ch, hh, nn, label='hop')
        self.pk.begin()
        if self.scroll_mode is not None: self.write_scroll_mode()
        self._return_to_title_before()
        r = c.call(self.E('GameUpdate'), held, decl, label='GameUpdate')
        self._return_to_title_after()
        if MSGDBG: self._log_message()
        if r is None: raise RuntimeError('le moteur s est arrete :\n' + '\n'.join(self.log.lines[-12:]))
        pkt = self.pk.packets()
        if os.environ.get('DQ_PKT') and self.state.part == PART_BATTLE:       # (test) journal des paquets de combat : image, [(type, ints...)]
            with open(os.environ['DQ_PKT'], 'a') as fj:
                fj.write('%d %s\n' % (self.frames, [(t, a[:2]) if t != 22 else (22, a[0], a[1], [round(x, 2) for x in f[:3]], [round(min(f[3 + 5 * i + 2] for i in range(a[1])), 2), round(max(f[3 + 5 * i + 2] for i in range(a[1])), 2), round(min(f[3 + 5 * i + 3] for i in range(a[1])), 2), round(max(f[3 + 5 * i + 3] for i in range(a[1])), 2)]) for t, a, f in pkt if t not in (12, 13, 14)]))
        if os.environ.get('DQ_PKTALL'):       # (test temporaire) tous les paquets sauf 22/28/29
            with open(os.environ['DQ_PKTALL'], 'a') as fj:
                for t, a, f in pkt:
                    if t not in (22, 28, 29): fj.write('%d p=%#x %d %s %s\n' % (self.frames, self.state.part, t, a[:6], [round(x, 3) for x in f[:6]]))
        self.ui.image = self.frames
        self._consume_messages()
        for p in pkt:
            if p[0] == 5 and p[1]:
                d = self.anim_duration(p[1][0] & 0xffff, (p[1][0] >> 16) & 0xffff) if self.anim_duration else None
                self.anims.append((self.frames + (d or ANIM_DURATION), p[1][0] & 0xffff))
        before = self.state.loaded_maps
        self.state.image = self.frames
        self.state.apply(pkt, self._map_name)
        self._exit_countdown()
        for t, a, f in pkt:
            if t == 34 and a and (a[0] & 0xf) == BATTLE_EFFECT: self._start_battle_effect(before)
            elif t == 34 and a: self._start_screen_effect(a[0])
        ac = self.state.load_wait
        if ac is not None and self.state.effect is None and self.state.loaded_maps > ac['base']: self.state.load_wait = None      # la scene du combat est arrivee
        self.state.update_loading()
        self.state.tick_fade(); self.state.tick_transition()
        prev = self.state.part
        self.state.part = struct.unpack('<H', c.mem(self._global() + 0xee, 2))[0]
        if prev == PART_BATTLE and self.state.part != PART_BATTLE: self.state.return_window = BATTLE_RETURN_WINDOW      # fin du combat : le fondu d'entree qui suit sur la carte est celui du retour (duree du jeu)
        if self.state.part == PART_BATTLE and prev != PART_BATTLE and self.state.load_wait is None and self.state.loaded_maps <= before:
            self.state.load_wait = {'base': before, 'n': 0}      # combat sans effet d'ecran (scenario...) : la scene d'avant ne doit pas apparaitre avant le chargement de celle du combat
        if self.state.part != PART_FIELD: self.state.field = None; self.state.world = None
        else: self._read_world()
        self.frames += 1
        return pkt

    def _exit_countdown(self):
        """Bruitage de transition de carte (porte, sortie, entree de village, escalier, carte du monde <-> ville) : cause de sa perte avec les fondus raccourcis (« Vitesse de transition » x3 et plus, marginal a x2).
        Quand le jeu quitte une ville ou la carte du monde, il lance un fondu au noir de 30 images ET arme un decompte de 15 images (EXIT_COUNTDOWN) ; a 0, NativeExec appelle playTownExitSE / playFieldExitSE, qui ne jouent le
        bruitage 305 que si l'ancienne scene vit encore. Dans le jeu d'origine, le chargement de la carte suivante n'arrive qu'a la fin du fondu (30 images) : le bruitage est demande a mi-fondu. Le fondu raccourci de la
        visionneuse (State._fondu) amene le chargement avant les 15 images : l'ancienne scene est detruite, le moteur ne demande plus rien (aucun paquet 35). On remet donc le decompte a la meme proportion que le fondu
        (duree jouee / duree d'origine) : le bruitage reste demande a mi-fondu, la duree du fondu et celle du bruitage ne changent pas. Sans fondu raccourci (rapport 1), rien n'est touche."""
        c = self.core; b = c.mem(self.L + EXIT_COUNTDOWN, 1)[0]
        if b > self._countdown: self._countdown_armed = self.frames; self._countdown_done = False       # armé pendant ce pas (le moteur l'a deja decremente une fois)
        self._countdown = b
        if self._countdown_done or b == 0 or b > 15: return
        im, r = self.state.fade_ratio
        if self.frames - self._countdown_armed > 2: self._countdown_done = True; return
        if im < self._countdown_armed - 2 or im > self.frames: return           # le fondu de cette sortie n'est pas (encore) arrive
        self._countdown_done = True
        if r < 1.0:
            num = max(1, int(round(b * r))); c.mem_w(self.L + EXIT_COUNTDOWN, bytes([num])); self._countdown = num

    def _log_message(self):
        """(test, DQ_MSGDBG=1) une ligne a chaque changement d'etat du message : image du moteur, etat, lettres ecrites / lettres de la ligne, vitesse du type de fenetre."""
        o = self.game_options()
        if o != getattr(self, '_opt_vu', None): self._opt_vu = o; print('MSGDBG image %d options du jeu : volume musique %d, volume bruitages %d, vitesse des messages de combat %d (impose : %s)' % ((self.frames,) + o + (self.scroll_mode,)), flush=True)
        e = self.message_state()
        if (e[0], e[1], e[4]) != getattr(self, '_msg_vu', None) or (e[1] == 2 and e[2] == e[3]):
            self._msg_vu = (e[0], e[1], e[4]); print('MSGDBG image %d actif %d etat %d lettres %d/%d vitesse %d combat=%d' % ((self.frames,) + e + (self.state.part == PART_BATTLE,)), flush=True)

    def _read_world(self):
        """Carte du monde entiere (FieldData : grille CWorldMap +0x188 de 256 x 256 numeros de bloc, table des blocs +0x180 de 6 octets,
        decalages d'animation de l'eau aux adresses 0x275830/34/38). Meme regle que FieldData::drawBlock (verifiee : 1300 tuiles sur 1300).
        Le moteur n'envoie que 25 colonnes autour du heros ; ici on peut dessiner autour de lui autant qu'on veut."""
        c, fd = self.core, self.fielddata
        if not fd: return
        try:
            if self._grid is None or self.frames - self._grid_frame >= 30:
                gp, = struct.unpack('<Q', c.mem(fd + 0x188, 8)); l, h = struct.unpack('<ii', c.mem(fd + 0x198, 8))
                if not gp or not (0 < l <= 1024 and 0 < h <= 1024): return
                self._grid = np.frombuffer(c.mem(gp, l * h * 2), '<u2').reshape(h, l).astype(np.int32); self._grid_frame = self.frames
            tbl, = struct.unpack('<Q', c.mem(fd + 0x180, 8))
            ch = np.frombuffer(c.mem(tbl, 1024 * 6), np.uint8).reshape(1024, 6)
            b0, b1, b2 = (struct.unpack('<h', c.mem(self.L + a, 2))[0] for a in (0x275830, 0x275834, 0x275838))
            t = ch[:, 1]; s2 = np.ascontiguousarray(ch[:, 2:4]).view('<i2').ravel().astype(np.int32); s4 = np.ascontiguousarray(ch[:, 4:6]).view('<i2').ravel().astype(np.int32)
            tile = np.where(t == 0, s4 + b0, np.where(t == 0x18, s2 + b2, np.where(t == 8, s2 + b1, s2)))
            h, l = self._grid.shape
            self.state.world = {'ids': tile[(self._grid - 1) & 0x3ff], 'l': l, 'h': h}
        except Exception:
            self.state.world = None

    def read_canvas(self):
        """Bitmap du texte du message (hauteur x largeur, 0-255 = opacite), ou None si le canevas n'existe pas encore."""
        c = self.core
        buf = struct.unpack('<Q', c.mem(self.obj_msg + 0x10, 8))[0]
        if not buf: return None
        import numpy as np
        return np.frombuffer(c.mem(buf, CANVAS_L * CANVAS_H), np.uint8).reshape(CANVAS_H, CANVAS_L)

    def _consume_messages(self):
        """Fait ce que ferait l'interface Unity : lit les messages que le moteur a poses pour chaque port (menus, fenetres...)
        puis vide la file. Sans cela la file grossit sans fin et finit par ecraser la memoire voisine."""
        c = self.core
        b2 = self.buf2
        a = struct.unpack('<%dh' % SHORTS_STACK, c.mem(b2, 2 * SHORTS_STACK))
        out = []
        for port in range(32):
            idx = a[port] & 0xffff; guard = 0
            while 0 < idx < SHORTS_STACK - 2 and guard < 600:
                n = a[idx]
                if n < 0 or idx + n + 1 >= SHORTS_STACK: break
                out.append((port, a[idx + 1: idx + 1 + n]))
                idx = a[idx + 1 + n] & 0xffff; guard += 1
        self.msgs_ui = out
        self.ui.apply(out)
        c.mem_w(b2, b'\0' * 128 + struct.pack('<h', 65))              # tetes/queues a 0, pointeur libre = 65

    def active_menu(self):
        """Port de la fenetre de menu qui attend les touches (active et acceptant la saisie), ou None."""
        c = self.core; L = self.L
        u = lambda a, n, sg=False: int.from_bytes(c.mem(a, n), 'little', signed=sg)
        base = u(L + 0x252098, 8); cnt = u(L + 0x252094, 2, True)
        if not base: return None
        cand = []
        for i in range(1, cnt):
            e = base + 0x20 * i
            port = u(e + 0x28, 2, True); this = u(e + 0x30, 8)
            if this and u(e + 0x38, 8) and port > 1 and u(this + 8, 1) == 1 and u(this + 0x50, 2):
                f = self.ui.f.get(port)
                if f and f['vis'] and f['cases']: cand.append((f['ordre'], port))
        if not cand:                                 # sinon : menu dont le moteur demande la saisie (commande 6 a chaque image), meme sous un message : Oui / Non d'une question
            cand = [(self.ui.f[p]['ordre'], p) for p in self.input_menus()]
        return max(cand)[1] if cand else None

    def input_menus(self):
        """Tous les ports de menu dont le moteur demande la saisie (le toucher agit sur chacun d'eux) : le plus recent d'abord."""
        return sorted((p for p, f in self.ui.f.items() if p > 1 and f.get('entree') and f['vis'] and f['cases']), key=lambda p: -self.ui.f[p]['ordre'])

    def send_menu(self, port, *args):
        """Ce que fait Unity : depose un message [n, args...] dans la file moteur<-interface du port (touches/pointeur des menus)."""
        if os.environ.get('DQ_MENUDBG'): print('ENVOI image %d port %d %s' % (self.frames, port, list(args)), flush=True)         # (test) messages interface -> moteur
        c = self.core
        a = list(struct.unpack('<%dh' % SHORTS_STACK, c.mem(self.buf1, 2 * SHORTS_STACK)))
        n = len(args); idx = a[64] or 65
        a[idx] = n
        for i, v in enumerate(args): a[idx + 1 + i] = v
        a[idx + n + 1] = 0
        if a[port]: a[a[32 + port]] = idx
        else: a[port] = idx
        a[32 + port] = idx + n + 1
        a[64] = idx + n + 2
        c.mem_w(self.buf1, struct.pack('<%dh' % SHORTS_STACK, *a))

    def params_message(self):
        """(nombre de lignes visibles - 1, hauteur d'une ligne, defilement) du canevas de message, tels que le moteur les tient."""
        c = self.core; i16 = lambda ad: struct.unpack('<h', c.mem(ad, 2))[0]
        return i16(self.L + 0x2523a0), i16(self.obj_msg + 0x42), i16(self.obj_msg + 0x4a)

    def read_message(self):
        """Partie du canevas actuellement visible dans la fenetre de message : n lignes a partir du defilement courant.
        -> tableau (hauteur x largeur) de 0-255, ou None."""
        a = self.read_canvas()
        if a is None: return None
        c = self.core
        i16 = lambda ad: struct.unpack('<h', c.mem(ad, 2))[0]
        lines = i16(self.L + 0x2523a0) + 1            # nombre de lignes visibles de la fenetre (reglage du moteur)
        lh = i16(self.obj_msg + 0x42)                  # hauteur d'une ligne (pixels du canevas)
        scroll = i16(self.obj_msg + 0x4a)               # defilement courant (le moteur l'anime de 8 pixels par image)
        if not (1 <= lines <= 8 and 8 <= lh <= 64): lines, lh, scroll = 4, 28, -3
        import numpy as np
        h = lines * lh; top = max(0, scroll + 3)
        return a[(top + np.arange(h)) % a.shape[0]]                   # le canevas est circulaire (512 lignes, REPEAT) et le defilement du moteur croit sans borne : comme `ui_menu.select_language` (y & 0x1ff)

    def _finish_anims(self):
        c = self.core
        due = [a for a in self.anims if a[0] <= self.frames]
        if not due: return
        self.anims = [a for a in self.anims if a[0] > self.frames]
        table = struct.unpack('<Q', c.mem(self.fldobj + 8, 8))[0]
        for _, idx in due:
            ad = table + idx * 32 + 0x14
            c.mem_w(ad, bytes([c.mem(ad, 1)[0] & ~1]))

    def catalog_status(self):
        """Masque de `getCatalogStatus` : bits 0-4 = banque valide, 5-9 = illisible, 10-14 = corrompue, 15 = un fichier manque."""
        return int(self.core.call(self.E('_ZN7profile8SaveLoad16getCatalogStatusEv'), label='getCatalogStatus')) & 0xffff

    def reread_savefiles(self):
        """Apres un import de sauvegardes : le moteur ne releve les fichiers data1..5 / data9 qu'a la creation du menu de depart ; on lui refait relever le catalogue (noms, chapitres, durees des listes). -> nouveau masque de statut."""
        for name_str in ('getCatalogView', 'getCatalogRecent'):
            self.core.call(self.E('_ZN7profile8SaveLoad%d%sEv' % (len(name_str), name_str)), label=name_str)
        return self.catalog_status()

    @staticmethod
    def initial_buttons_state(status):
        """Ce que le moteur fixe a la creation du menu de depart (`updateActiveDiary`) : (une banque 0-2 contient des donnees, la banque 3 est valide, la banque 4 est valide) -> boutons grises ou absents."""
        return (bool(status & 0x0007 or status & 0x00e0 or status & 0x1c00), bool(status & 0x0008), bool(status & 0x0010))

    def load_save(self, number):
        """numero 1..5 -> lit data<numero>.dat ; le moteur relance la ville sauvegardee"""
        r = self.core.call(self.E('_ZN7profile8SaveLoad8loadbankEi'), number - 1, label='loadbank')
        return bool(r)
