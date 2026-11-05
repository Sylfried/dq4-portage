"""Reglages du joueur (menu Echap) : affichage, son, touches. Enregistres dans reglages.json (a cote de window.py, ignore par git)."""
import json, os
import pyglet
from dq4_pc import language as LG
from dq4_pc.language import N_, tr

# Touches par defaut : action -> [touche principale, touche secondaire] (noms pyglet.window.key)
DEFAULT_KEYS = {
    'gauche': ['Q', None], 'droite': ['D', None], 'haut': ['Z', None], 'bas': ['S', None],
    'cam_gauche': ['LEFT', None], 'cam_droite': ['RIGHT', None], 'cam_haut': ['UP', None], 'cam_bas': ['DOWN', None],      # les fleches : sur le terrain gauche / droite tournent la camera des villes (D-233 ; les deux ensemble la recentrent), partout ailleurs (menus, messages, combats) les quatre sont des directions ; haut / bas ne servent que dans les menus (l'inclinaison a ete retiree en #264)
    'menu': ['RETURN', 'TAB'], 'discussion': ['LALT', 'RALT'], 'carte': ['M', None], 'historique': ['H', None],
    'A': ['SPACE', None], 'B': ['BACKSPACE', None], 'accel': ['LSHIFT', 'RSHIFT'],
    'L': ['A', None], 'R': ['R', None], 'infos': ['F1', None], 'modif': ['LCTRL', 'RCTRL'],
    'vit_combat': ['V', None],        # fait defiler la vitesse de combat (Manuel, Normal, Rapide, Tres rapide) : en combat comme ailleurs ; V = « vitesse » (libre : ni ZQSD, ni fleches, ni F1, ni les chiffres des etats)
}
OLD_MENU = ['RETURN', None]         # defaut de l'action « Menu » avant la v5 (touches_v) : Entree seule ; un fichier qui le contient encore recoit Tab en plus (voir Settings.__init__)
# libelles des actions (menu Commandes : la page range les lignes par sections, voir pause.py ; L / R : pages des menus du jeu, touches fixes absentes du menu)
ACTIONS = [('haut', N_('Haut')), ('bas', N_('Bas')), ('gauche', N_('Gauche')), ('droite', N_('Droite')),
           ('cam_haut', N_('Flèche haut (menus)')), ('cam_bas', N_('Flèche bas (menus)')), ('cam_gauche', N_('Caméra (Gauche)')), ('cam_droite', N_('Caméra (Droite)')),
           ('accel', N_("Touche d'accélérateur")), ('vit_combat', N_('Changer la vitesse en combat')), ('modif', N_('Touche spéciale')),
           ('A', N_('Action')), ('menu', N_('Menu')), ('B', N_('Annuler/Retour')), ('carte', N_('Carte')), ('discussion', N_('Discussion de groupe')), ('historique', N_('Historique')),
           ('infos', N_('Infos à l\'écran')), ('L', N_('Page précédente')), ('R', N_('Page suivante'))]          # (D-238 : libellés en français, traduits à l'affichage par le menu Pause : `tr(label_text)`)
RESERVED = ('ESCAPE', 'F11')          # Echap ouvre le menu, F11 bascule fenetre / plein ecran (comme Alt + Entree) : non reattribuables
NAMES = {'LEFT': '←', 'RIGHT': '→', 'UP': '↑', 'DOWN': '↓', 'LSHIFT': N_('Maj gauche'), 'RSHIFT': N_('Maj droite'), 'LCTRL': N_('Ctrl gauche'), 'RCTRL': N_('Ctrl droite'),
        'LALT': N_('Alt gauche'), 'RALT': N_('Alt droite'), 'SPACE': N_('Espace'), 'RETURN': N_('Entrée'), 'ENTER': N_('Entrée pavé'), 'BACKSPACE': N_('Retour arrière'), 'TAB': 'Tab',
        'DELETE': N_('Suppr'), 'INSERT': N_('Inser'), 'HOME': N_('Début'), 'END': N_('Fin'), 'PAGEUP': N_('Page haut'), 'PAGEDOWN': N_('Page bas'), 'CAPSLOCK': N_('Verr Maj'),
        'NUM_ADD': N_('Pavé +'), 'NUM_SUBTRACT': N_('Pavé -'), 'COMMA': ',', 'PERIOD': '.', 'SEMICOLON': ';', 'COLON': ':', 'EXCLAMATION': '!', 'MINUS': '-', 'PLUS': '+', 'EQUAL': '=', 'SLASH': '/', 'BACKSLASH': '\\'}
# (D-238 : `key_name` rend toujours le nom FRANCAIS (une donnee, comme les libelles des actions) ; le menu le traduit en le dessinant, `tr(key_name(...))`, y compris « Pavé 0 » a « Pavé 9 » des autres touches du pave numerique)

# Fenetres de commandes du combat (le cadre du bas : Combattre / Fuir, Attaquer / Magie / Objets / Defense, cibles, objets et sorts, infos) : cadre de 459 unites d'interface, alors que les messages d'action du combat
# (types 2 et 3 de la fenetre de message) en font 510. Par defaut ces fenetres sont agrandies a la largeur des boites de dialogue (510 / 459) : le bouton de vitesse, colle au coin bas gauche de la boite du bas, ne se
# decale plus quand un message d'action remplace le menu au debut d'un tour (#47). Meme mecanique que toute fenetre reglee dans l'editeur : [taille relative, decalage x, decalage y].
BATTLE_COMMAND_WINDOWS = ('BattleRoot', 'BattleAction', 'BattleTarget', 'BattleGo', 'BattleIM', 'BattleInfo', 'BattleChangeInfo')
COMMANDS_WIDTH = round(510.0 / 459.0, 4)

DEFAULT = {
    'langue': 'systeme',            # langue de l'outil (D-238) : 'systeme' (francais si Windows est en francais, sinon anglais), 'en' ou 'fr' ; les textes du jeu ne changent pas
    'mode_sprites': 4,            # « Shader » : 0 originaux, 1 EPX x8, 4 pixel perfect (voir hd.py) ; 2 (regions lissees) et 3 (bicubique), retires car ils ne faisaient que flouter, valent 1 a la lecture
    'mode_fenetre': 0,            # fenetre : 0 fenetre, 1 plein ecran (fenetre sans bordure a la resolution du bureau, l'affichage du moniteur ne change pas) ; F11 / Alt + Entree passent de l'un a l'autre (ex-booleen « full_screen » ; l'ancien plein ecran exclusif, mode 2, est devenu 1)
    'msaa': 4,                    # anticrenelage MSAA (0, 2, 4, 8) : la scene est dessinee hors ecran (postfx.py), le changement est immediat ; limite par la carte graphique
    'echelle_rendu': 1.0,         # suréchantillonnage : la scene est dessinee a cette echelle (1 a 2) puis reduite (1 = normal ; 2 = 4 fois plus de pixels calcules, scintillement et bords en escalier tres reduits)
    'nettete': 0.0,               # 0 a 1 : accentuation adaptative des contours de la scene (0 = aucune)
    'luminosite': 1.0,            # 0,5 a 1,5 : courbe de gamma de la scene (1 = comme le jeu ; plus haut = plus clair)
    'infos': False,               # F1 : lignes d'information
    'son': True, 'volume_musique': 1.0, 'volume_bruitages': 1.0,
    'volume_general': 1.0, 'volume_jingles': 1.0, 'volume_interface': 1.0,      # son : volume general, des jingles et fanfares, des sons de l'interface (categories : voir sound.py ; « bruitages » = les effets sonores du jeu)
    'musique_active': True, 'jingles_actifs': True, 'bruitages_actifs': True, 'interface_active': True,       # interrupteurs par categorie
    'vitesse_texte': 4.0,         # dialogues : lettres affichees par image du moteur (30 par seconde) ; 4 = comme le jeu (voir TEXT_SPEEDS)
    'resolution': [1920, 1080],   # fenetre : taille de la fenetre [largeur, hauteur] (ramenee a l'ecran si elle est trop grande) ; plein ecran : sans effet (la fenetre prend la resolution du bureau)
    'camera_inverser_gd': False,  # camera tournee a la souris (clic molette maintenu + deplacement) : inverse le sens gauche / droite (non = comme les fleches : glisser vers la droite = fleche droite) ; ne change pas les fleches du clavier
    'vignette': 0.3,              # assombrissement des bords de l'image de jeu (0 = aucun, 1 = coins noirs) : donne du volume aux decors et sprites 2D, cache le fond uni hors de la carte
    'vitesse_marche': 1.0,        # facteur de vitesse du jeu quand le heros marche : x1, x2, x3 ou x4 (SPEEDS_X)
    'vitesse_camera': 1.0,        # vitesse de rotation de la camera aux fleches et du recentrage : x1 a x4 (la touche d'accelerateur ne l'accelere pas)
    'vitesse_accel': 1.5,         # « Multiplicateur de l'accélérateur » (1 a 2) : multiplicateur de la marche (on court) tant que la « Touche d'accélérateur » est tenue (ex-« vitesse_course ») ; ne s'applique JAMAIS aux combats (voir battle_speed)
    'vitesse_combat': 1.0,        # « Vitesse de combat » : 0 Manuel (vitesse normale, on passe chaque message a la main), 1 Normal, 2 Rapide, 3 Tres rapide (BATTLE_SPEEDS) : le moteur fait 1, 2 ou 3 fois plus de pas par seconde pendant un combat (animations des monstres et des coups, deplacements, delais, defilement des messages, fondus) ; la musique et les bruitages gardent leur vitesse (voir battle_speed.py)
    'historique_favoris_seuls': False,   # fenetre « Historique » : case « Favoris seulement » cochee ? (etat enregistre a chaque changement, retrouve d'une session a l'autre ; pas de ligne dans le menu Echap : on le change dans la fenetre elle-meme, voir ui_history.py)
    'soin_niveau': False,         # « PV et PM restaurés au niveau supérieur » : quand un personnage gagne un niveau, il retrouve tous ses PV et tous ses PM (le jeu d'origine ne le fait pas) ; desactive = comme le jeu
    'taille_degats': 1.6,         # taille des nombres de degats sur les monstres (1 = taille de la mise en page d'origine, tres petite sur un grand ecran)
    'grille_edition': True,       # editeur d'interface : grille de placement affichee (32 x 18 cases)
    'boutons': True,              # boutons tactiles de la version mobile (Carte, Commandes, Discussion) affiches a l'ecran, hors combat
    'croix': True, 'croix_taille': 1.0,      # croix (manette tactile) a l'ecran, utilisable a la souris : affichee ou non ; taille relative (en plus de l'option « Taille de la croix » du jeu)
    'boutons_taille': 1.0, 'boutons_aimant': True,       # taille relative ; positions posees sur une grille (aimantation)
    'interface_fenetres': {n: [COMMANDS_WIDTH, 0.0, 0.0] for n in BATTLE_COMMAND_WINDOWS},     # fenetres du jeu : nom (Make_* de MenuPortItemTable, ou 'msg' pour les dialogues) -> [taille relative, decalage x, decalage y en fraction de l'ecran] ; absent : comme le jeu (voir pause.py, editeur d'interface)
    'boutons_pos': {},            # bouton ou 'croix' -> [colonne, ligne] de son coin superieur gauche sur la grille de l'ecran (vide : positions d'origine, voir hud_mobile.py) ; le bouton de vitesse de combat a la sienne (bouton_vitesse_pos)
    'bouton_vitesse': True, 'bouton_vitesse_taille': 1.0, 'bouton_vitesse_pos': [],      # interface « Combat : bouton de vitesse » (sortie de « Boutons et croix de l'ecran ») : affiche en combat ou non ; taille relative ; [colonne, ligne] de son coin superieur gauche (vide : colle sous la boite du bas, voir hud_mobile.Buttons.ancre)
    'interface_v': 2,             # version des tailles par defaut des fenetres du jeu (interface_fenetres) : un fichier enregistre avant (sans cette cle) recoit une seule fois les nouvelles tailles par defaut, sauf pour une fenetre que le joueur a reglee ; v2 : fenetres de commandes du combat a la largeur des dialogues
    'interface_masquees': [],     # editeur d'interface, « Afficher cette interface a l'ecran » = Non : noms des fenetres du jeu (Make_*, ou 'msg' pour les dialogues) qui ne sont pas dessinees ; pour les boutons et la croix de l'ecran, c'est le reglage 'boutons'
    'touches_v': 5,               # version des reglages : une liste de touches plus ancienne que la v3 est abandonnee (v3 : ZQSD pour marcher, fleches = camera, Espace = action) ; v3 -> v4 : Discussion de groupe = Alt / Alt Gr (si ces touches sont libres), accelerateur x1,5 (si la course etait au x2 d'origine) ; v4 -> v5 : « Menu » = Entree et Tab (si « Menu » avait encore l'ancien defaut, Entree seule, et que Tab est libre) ; une action ajoutee depuis prend sa touche par defaut
    'touches': {k: list(v) for k, v in DEFAULT_KEYS.items()},
}


# Fenetres du jeu absentes de l'editeur d'interface (pause.py) : lancement du jeu (menu de depart, nom, titre, licence, reseau : gerees a part), sans maillage (rien a regler), sans objet sur PC
# ou qui suivent les monstres a l'ecran. Leurs reglages enregistres par une ancienne version sont abandonnes au chargement (ils decalaient un texte seul ou une fenetre du lancement).
REMOVED_WINDOWS = ('StartMenuFirst', 'StartMenuSecond', 'StartMenuSelect', 'StartNameEntry', 'SaveOverwrite', 'TitleTouch', 'PortalButton', 'NetworkRoot', 'NetworkPLST', 'NetworkCODE', 'NetworkITEM',
                     'ViewVolumeDecision', 'License', 'MagicInfo', 'Config', 'NENE_ItemView', 'MonsterName', 'BattleHoppingNumber')

# Editeur d'interface (pause.py : Affichage > Interface) : classement des reglages et remises a zero. Toute cle de DEFAULT qui touche l'interface doit figurer dans l'un de ces trois groupes
# (tools/test_interface_settings.py le verifie : une cle ajoutee sans classement fait echouer le test).
SCREEN_TARGET = 'boutons'                                    # « Boutons et croix de l'ecran » : l'une des interfaces de l'editeur (les autres : 'msg' et les fenetres du jeu, par leur nom Make_*)
SCREEN_KEYS = ('boutons', 'croix', 'croix_taille', 'boutons_taille', 'boutons_pos')      # reglages de SCREEN_TARGET : affichage des boutons et de la croix, tailles, positions
SPEED_TARGET = 'bouton_vitesse'                           # « Combat : bouton de vitesse » : sa propre interface de l'editeur (groupe « Combat »), separee de SCREEN_TARGET
SPEED_KEYS = ('bouton_vitesse', 'bouton_vitesse_taille', 'bouton_vitesse_pos')      # reglages de SPEED_TARGET : affichage, taille, position
WINDOW_KEYS = ('interface_fenetres', 'interface_masquees')                       # reglages par fenetre du jeu (ou 'msg') : taille et position, affichage
EDITOR_KEYS = ('grille_edition', 'boutons_aimant')                                # options de l'editeur lui-meme, communes a toutes les interfaces : grille affichee, aimantation
INTERFACE_KEYS = SCREEN_KEYS + SPEED_KEYS + WINDOW_KEYS + EDITOR_KEYS
DEFAULT_WINDOW = (1.0, 0.0, 0.0)                           # fenetre du jeu sans reglage enregistre : taille relative, decalage x, decalage y (fractions de l'ecran)


def default_window(name_str):
    """Taille relative, decalage x, decalage y d'une fenetre du jeu sans reglage du joueur : celle de DEFAULT (fenetres de commandes du combat) ou, sinon, DEFAULT_WINDOW (comme le jeu)."""
    return tuple(DEFAULT['interface_fenetres'].get(name_str, DEFAULT_WINDOW))


# TzKeys d'anciens fichiers de reglages qui n'existent plus : jamais lues (le chargeur ne prend que les cles de DEFAULT), donc absentes du fichier a la prochaine sauvegarde. 'full_screen' (booleen d'avant la #42) est converti en 'mode_fenetre' ;
# 'mode_fenetre_retour' (dernier mode non exclusif, #42), 'edge_correction' (option retiree : la correction des bords des sprites est toujours appliquee) et 'lissage' (option retiree : le lissage des textures est toujours applique) sont abandonnees ; 'camera_centree' et 'suivi_camera_v' aussi (#47 : la camera est toujours centree sur le heros, sauf quand le jeu la prend). 'ecran_plein' (choix du moniteur du plein ecran, #52) et 'sortie_audio' (choix du peripherique audio, #112) sont retires le 03/11/2026 a la demande de Sylfried : le plein ecran se fait sur l'ecran de la fenetre, le son reste sur la sortie par defaut de Windows.
OBSOLETE_KEYS = ('plein_ecran', 'mode_fenetre_retour', 'correction_bords', 'lissage', 'defilement_force', 'defilement_combat', 'camera_centree', 'suivi_camera_v', 'ecran_plein', 'sortie_audio', 'distance_camera', 'angle_camera', 'camera_inverser_hb', 'zoom')
MODES_SPRITES = (0, 1, 4)      # valeurs possibles de 'mode_sprites' (le 4 garde son numero : les anciens fichiers de reglages et les options --hd restent valables)
MSAA_VALUES = (0, 2, 4, 8)


def valid_sprites_mode(v):
    """Valeur lue (ancien fichier de reglages, option --hd) -> mode existant : 2 (regions lissees) et 3 (bicubique) sont devenus 1 (EPX x8, le plus proche : meme agrandissement x8 des contours, sans le flou) ; tout le reste -> pixel perfect."""
    try: v = int(v)
    except (TypeError, ValueError): return DEFAULT['mode_sprites']
    if v in (2, 3): return 1
    return v if v in MODES_SPRITES else DEFAULT['mode_sprites']


def valid_window_mode(v):
    """Valeur lue (reglages.json, option --plein-ecran) -> 0 (fenetre) ou 1 (plein ecran). Un booleen est l'ancien reglage « full_screen » (vrai = 1) ; 2, l'ancien plein ecran exclusif (#42), devient 1 : le plein ecran qui reste ;
    tout ce qui est invalide -> fenetre."""
    if isinstance(v, bool): return 1 if v else 0
    try: n = int(v)
    except (TypeError, ValueError, OverflowError): return DEFAULT['mode_fenetre']
    if n != v: return DEFAULT['mode_fenetre']
    return {0: 0, 1: 1, 2: 1}.get(n, DEFAULT['mode_fenetre'])


BOUNDS = {'vitesse_marche': (1.0, 4.0), 'vitesse_camera': (1.0, 4.0), 'vitesse_accel': (1.0, 2.0), 'vignette': (0.0, 1.0), 'croix_taille': (0.5, 2.0)}      # bornes des curseurs du menu Echap
BOUNDS.update({'echelle_rendu': (1.0, 2.0), 'nettete': (0.0, 1.0), 'luminosite': (0.5, 1.5)})
BOUNDS.update({'volume_musique': (0.0, 1.0), 'volume_bruitages': (0.0, 1.0), 'volume_general': (0.0, 1.0), 'volume_jingles': (0.0, 1.0), 'volume_interface': (0.0, 1.0), 'vitesse_texte': (0.25, 4000.0)})
SOUND_TEXT_BOOLEANS = ('musique_active', 'jingles_actifs', 'bruitages_actifs', 'interface_active', 'soin_niveau', 'camera_inverser_gd', 'historique_favoris_seuls')      # (reglages Oui / Non : toute valeur qui n'est pas un booleen revient au defaut)
TEXT_SPEEDS = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 4000.0)     # crans de la vitesse du texte (lettres par image) ; 4 = le jeu, 4000 = tout d'un coup
SPEEDS_X = (1.0, 2.0, 3.0, 4.0)                            # crans de la vitesse de marche, de la camera et des transitions (x1 = comme le jeu)
SPEEDS_X_KEYS = ('vitesse_marche', 'vitesse_camera')
BATTLE_SPEEDS = (0.0, 1.0, 2.0, 3.0)                       # crans de « Vitesse de combat » : Manuel (vitesse normale + messages passes a la main), Normal (= le jeu), Rapide, Tres rapide
BATTLE_SPEED_NAMES = {0.0: N_('Manuel'), 1.0: N_('Normal'), 2.0: N_('Rapide'), 3.0: N_('Très rapide')}      # libelles montres au joueur (page Texte, bouton de l'ecran de combat, message de la touche) : jamais « x1 », « x2 », « x3 »
# Defilement des messages de combat : OptionStatus.battleSpeed (g_Option + 5, valeur d'origine 2 : OptionStatus::initialize) ; BattleAutoFeed::setMessageSpeed : 0 / 1 / 2 / 3 = attente de 12 / 22 / 32 / 42 images (0,4 / 0,73 / 1,07 / 1,4 s) avant le message
# suivant, 4 = pas d'avance automatique (touche). « Vitesse de combat » impose 4 en Manuel et 0 (la plus courte, 12 images) sinon (#45 : avec 2, la valeur d'origine, 32 images, le nombre de degats n'apparaissait que 0,77 s apres le debut de l'animation du coup
# et un tour d'attaque durait 5,7 s ; avec 0 : 0,43 s et 3,0 s ; l'animation du coup garde sa duree) : les vitesses Rapide et Tres rapide accelerent l'horloge du moteur, donc cette attente aussi.
BATTLE_MANUAL = 0.0
CODE_SCROLL_MANUAL, CODE_SCROLL_AUTO = 4, 0


def scroll_code(speed):
    """Valeur de OptionStatus.battleSpeed a imposer au moteur pour ce cran de « Vitesse de combat » : 4 (a la main) en Manuel, 0 (attente de 12 images entre deux messages : les animations s'enchainent sans temps mort) sinon."""
    return CODE_SCROLL_MANUAL if battle_notch(speed) == BATTLE_MANUAL else CODE_SCROLL_AUTO


def speed_after_game_code(code, speed):
    """Le jeu change lui-meme battleSpeed (chargement d'une sauvegarde, fenetre Parametres d'origine) : 4 -> Manuel ; toute autre valeur -> sortie du Manuel (Normal), les autres crans sont gardes."""
    v = battle_notch(speed)
    try: code = int(code)
    except (TypeError, ValueError): return v
    if code == CODE_SCROLL_MANUAL: return BATTLE_MANUAL
    return DEFAULT['vitesse_combat'] if v == BATTLE_MANUAL else v


def notch_x(v, default=1.0):
    """Vitesse lue (ancien curseur de 0,5 a 2 ou valeur absurde) -> le cran x1 a x4 le plus proche (a egalite le plus rapide), jamais moins que x1."""
    if isinstance(v, bool) or not isinstance(v, (int, float)): return default
    return float(min(SPEEDS_X[-1], max(SPEEDS_X[0], int(v + 0.5))))


def battle_notch(v, default=1.0):
    """Valeur lue (reglages.json, saisie) -> le cran de BATTLE_SPEEDS le plus proche (a egalite le plus rapide) ; tout ce qui n'est pas un nombre (texte, booleen, None, nan) -> `default`."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v: return default
    v = min(BATTLE_SPEEDS[-1], max(BATTLE_SPEEDS[0], v))                                  # (bornes : jamais plus lent que Manuel, ni plus rapide que Très rapide)
    return min(BATTLE_SPEEDS, key=lambda c: (abs(c - v), -c))


def next_battle_speed(v):
    """Touche « Changer la vitesse en combat » : Manuel -> Normal -> Rapide -> Très rapide -> Manuel (une valeur invalide est lue comme Normal, une valeur hors bornes comme le cran le plus proche)."""
    v = battle_notch(v)
    return BATTLE_SPEEDS[(BATTLE_SPEEDS.index(v) + 1) % len(BATTLE_SPEEDS)]


def key_name(name_str):
    """Nom lisible d'une touche (nom pyglet) pour le menu."""
    if not name_str: return '—'
    return NAMES.get(name_str, name_str.replace('NUM_', 'Pavé ') if name_str.startswith('NUM_') else (name_str[1:] if name_str.startswith('_') and name_str[1:].isdigit() else name_str))


def key_symbol(name_str):
    """Nom pyglet -> code de touche (None si inconnu)."""
    return getattr(pyglet.window.key, name_str, None) if name_str else None


def name_of(symbol):
    """Code de touche -> nom pyglet."""
    return pyglet.window.key.symbol_string(symbol)


class Settings:
    def __init__(self, path=None):
        self.path = path; self.v = json.loads(json.dumps(DEFAULT))
        if path and os.path.exists(path):
            try:
                with open(path, encoding='utf-8') as f: d = json.load(f)
                if 'mode_fenetre' not in d and 'plein_ecran' in d: d['mode_fenetre'] = d['plein_ecran']      # ancien reglage « Plein écran » (booleen) -> 1 (plein ecran sans bordure, comme avant) ou 0 ; le booleen n'est plus enregistre (voir OBSOLETE_KEYS)
                if 'vitesse_accel' not in d and isinstance(d.get('vitesse_course'), (int, float)) and not isinstance(d.get('vitesse_course'), bool): d['vitesse_accel'] = d['vitesse_course']      # ancien « Multiplicateur de la course » -> vitesse de l'accelerateur (l'ancien multiplicateur de la camera, accel_camera, est abandonne : un seul facteur pour les deux)
                if isinstance(d.get('touches'), dict) and 'accel' not in d['touches']:       # anciennes touches de course et d'acceleration de la camera -> une seule « Touche d'accélérateur » : « Courir (maintenir) », a defaut les trois autres (« appuyer » n'existe plus)
                    for old in ('courir', 'courir_bascule', 'cam_accel', 'cam_accel_bascule'):
                        l = d['touches'].get(old)
                        if isinstance(l, list) and any(l): d['touches']['accel'] = l; break
                    else:
                        if isinstance(d['touches'].get('courir'), list): d['touches']['accel'] = [None, None]        # le joueur avait vide ces touches : l'accelerateur n'a pas de touche
                if 'bouton_vitesse' not in d and 'bouton_vitesse_taille' not in d and 'bouton_vitesse_pos' not in d: self.migrate_speed_button(d)      # (une seule fois : ensuite les trois cles sont enregistrees)
                old = d.get('defilement_combat'); old = 4 if old is None and d.get('defilement_auto') is False else old                # (tout ancien « Defilement automatique : non » = messages a la main)
                if d.get('defilement_force') is True and old == 4: d['vitesse_combat'] = BATTLE_MANUAL      # ancien « Messages en combat : Manuel » impose -> « Vitesse de combat : Manuel » (les autres crans n'ont plus d'equivalent : l'attente suit la vitesse de combat ; rien d'impose : la vitesse enregistree reste)
                saved_v = d.get('touches_v')
                for k, x in d.items():
                    if k == 'touches' and saved_v not in (3, 4, DEFAULT['touches_v']): continue
                    if k == 'touches' and isinstance(x, dict):
                        for a, ts in x.items():
                            if a in DEFAULT_KEYS and isinstance(ts, list): self.v['touches'][a] = (list(ts) + [None, None])[:2]
                    elif k in DEFAULT and k != 'touches' and k != 'taille_degats': self.v[k] = x          # (la taille des nombres de degats n'est plus un reglage : valeur fixe)
                if d.get('interface_v') != DEFAULT['interface_v'] and isinstance(self.v['interface_fenetres'], dict):      # anciennes tailles par defaut des fenetres -> nouvelles, une seule fois (ensuite la cle est enregistree et le choix du joueur fait foi) : fenetre sans reglage ou a l'ancienne taille par defaut (1, 0, 0)
                    fw = dict(self.v['interface_fenetres'])
                    for n, nv in DEFAULT['interface_fenetres'].items():
                        if n not in fw or fw[n] == list(DEFAULT_WINDOW): fw[n] = list(nv)
                    self.v['interface_fenetres'] = fw
                if saved_v == 3:                                      # v3 -> v4 : nouvelles valeurs par defaut, sans toucher a ce que le joueur a regle lui-meme
                    ts = self.v['touches']
                    if ts['discussion'] == [None, None] and not any(n in (a for l in ts.values() for a in l) for n in ('LALT', 'RALT')): ts['discussion'] = list(DEFAULT_KEYS['discussion'])
                    for a in ('modif',):
                        for i, n in enumerate(ts[a]):
                            if n and any(n in l for b, l in ts.items() if b != a): ts[a][i] = None        # une touche deja prise par une autre action lui reste
                    if self.v['vitesse_accel'] == 2.0: self.v['vitesse_accel'] = DEFAULT['vitesse_accel']
                if saved_v in (3, 4):                                 # v4 -> v5 : nouveau defaut de « Menu » (Entree et Tab). Seul l'ancien defaut exact (Entree seule) change : un choix du joueur est garde, et Tab reste a l'action qui l'a prise
                    ts = self.v['touches']
                    if ts['menu'] == OLD_MENU and not any('TAB' in l for a, l in ts.items() if a != 'menu'): ts['menu'] = list(DEFAULT_KEYS['menu'])
                saved = d.get('touches') if isinstance(d.get('touches'), dict) else {}
                for a in DEFAULT_KEYS:                                  # action ajoutee depuis : sa touche d'origine est abandonnee si une autre action l'a prise 
                    if a in saved: continue
                    ts = self.v['touches']
                    for i, n in enumerate(ts[a]):
                        if n and any(n in l for b, l in ts.items() if b != a): ts[a][i] = None
                self.v['touches_v'] = DEFAULT['touches_v']
                self.v['interface_v'] = DEFAULT['interface_v']
                for ts in self.v['touches'].values():                   # une touche reservee (F11 : bascule fenetre / plein ecran) ne peut plus etre une touche d'action : retiree d'un ancien fichier
                    for i in range(2):
                        if ts[i] in RESERVED: ts[i] = None
                for k, (mi, ma) in BOUNDS.items(): self.v[k] = min(ma, max(mi, self.v[k])) if isinstance(self.v[k], (int, float)) and not isinstance(self.v[k], bool) else DEFAULT[k]       # valeurs d'anciennes versions ramenees aux curseurs
                for k in SOUND_TEXT_BOOLEANS:
                    if not isinstance(self.v[k], bool): self.v[k] = DEFAULT[k]
                for k in SPEEDS_X_KEYS: self.v[k] = notch_x(self.v[k], DEFAULT[k])                       # ancien curseur (0,5 a 2) -> x1 a x4
                self.v['vitesse_combat'] = battle_notch(self.v['vitesse_combat'], DEFAULT['vitesse_combat'])
                self.v['vitesse_texte'] = min(TEXT_SPEEDS, key=lambda x: max(x, self.v['vitesse_texte']) / min(x, self.v['vitesse_texte']))        # un des crans du menu
                fw = self.v['interface_fenetres']; self.v['interface_fenetres'] = {n: x for n, x in fw.items() if n not in REMOVED_WINDOWS and isinstance(x, list) and len(x) == 3} if isinstance(fw, dict) else {}      # editeur d'interface : fenetres retirees de l'editeur
                ms = self.v['interface_masquees']; self.v['interface_masquees'] = [n for n in ms if isinstance(n, str) and n not in REMOVED_WINDOWS] if isinstance(ms, list) else []
                bs = self.v['bouton_vitesse_taille']; self.v['bouton_vitesse_taille'] = min(2.0, max(0.5, float(bs))) if isinstance(bs, (int, float)) and not isinstance(bs, bool) and bs == bs else DEFAULT['bouton_vitesse_taille']
                if not isinstance(self.v['bouton_vitesse'], bool): self.v['bouton_vitesse'] = DEFAULT['bouton_vitesse']
                bp = self.v['bouton_vitesse_pos']; self.v['bouton_vitesse_pos'] = [float(x) for x in bp] if isinstance(bp, list) and len(bp) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in bp) else []
                if isinstance(self.v['boutons_pos'], dict): self.v['boutons_pos'] = {n: x for n, x in self.v['boutons_pos'].items() if n != 'combat'}      # (la position du bouton de vitesse n'est plus ici)
                self.v['mode_sprites'] = valid_sprites_mode(self.v['mode_sprites'])
                self.v['mode_fenetre'] = valid_window_mode(self.v['mode_fenetre'])          # (2 = ancien plein ecran exclusif -> 1)
                if self.v['langue'] not in LG.CHOICES: self.v['langue'] = DEFAULT['langue']
                if self.v['msaa'] not in MSAA_VALUES: self.v['msaa'] = DEFAULT['msaa']
            except Exception as ex:
                print('Unreadable settings (%s): default values (%r)' % (path, ex), flush=True)
        self.codes_cache = {}

    @staticmethod
    def migrate_speed_button(d):
        """Ancien fichier : le bouton de vitesse de combat faisait partie de « Boutons et croix de l'ecran » (affichage = 'boutons', taille = 'boutons_taille', position = boutons_pos['combat']) ; il a maintenant ses propres reglages,
        repris tels qu'ils agissaient : affiche si les boutons l'etaient ; sa position gardee si le joueur l'avait placee (sinon elle reste collee a la boite du bas) et alors la taille des boutons (sans position, la plaque
        suivait celle de « Fuir » et ignorait la taille). `boutons_pos` perd la cle 'combat'. Modifie `d` sur place."""
        bp = d.get('boutons_pos'); pos = bp.pop('combat', None) if isinstance(bp, dict) else None
        if isinstance(d.get('boutons'), bool): d['bouton_vitesse'] = d['boutons']
        if isinstance(pos, list) and len(pos) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in pos):
            d['bouton_vitesse_pos'] = [pos[0], pos[1]]
            t = d.get('boutons_taille')
            if isinstance(t, (int, float)) and not isinstance(t, bool): d['bouton_vitesse_taille'] = t

    def __getitem__(self, k): return self.v[k]

    def __setitem__(self, k, x):
        self.v[k] = x; self.codes_cache = {}

    # ---- editeur d'interface : remises a zero (toujours a partir de DEFAULT, jamais de valeurs recopiees)
    @staticmethod
    def default(lookup_key):
        """Copie (modifiable) de la valeur par defaut d'un reglage."""
        return json.loads(json.dumps(DEFAULT[lookup_key]))

    def reset_interface(self, target):
        """« Retablir cette interface » : l'interface `target` de l'editeur (SCREEN_TARGET, 'msg' ou nom Make_* d'une fenetre du jeu) revient entierement a son etat d'origine, et elle seule :
        position, taille, affichage (« Afficher cette interface a l'ecran ») et ses autres options. Boutons et croix de l'ecran : tout SCREEN_KEYS (affichage, taille de la croix et des boutons, positions) ; bouton de vitesse de combat : tout SPEED_KEYS.
        Fenetre du jeu : son entree de WINDOW_KEYS (absente de DEFAULT = taille, position et affichage du jeu). Les options de l'editeur (EDITOR_KEYS) ne bougent pas."""
        if target == SCREEN_TARGET:
            for k in SCREEN_KEYS: self[k] = self.default(k)
            return
        if target == SPEED_TARGET:                                    # bouton de vitesse de combat : affichage, taille et position (retour sous la boite du bas)
            for k in SPEED_KEYS: self[k] = self.default(k)
            return
        win = dict(self['interface_fenetres']); win.pop(target, None)
        if target in DEFAULT['interface_fenetres']: win[target] = self.default('interface_fenetres')[target]
        self['interface_fenetres'] = win
        masked = [n for n in self['interface_masquees'] if n != target]
        if target in DEFAULT['interface_masquees']: masked.append(target)
        self['interface_masquees'] = masked

    def reset_interfaces(self):
        """« Retablir toutes les interfaces » : toutes les interfaces (SCREEN_KEYS et WINDOW_KEYS) et les options de l'editeur (EDITOR_KEYS : grille, aimantation) reviennent a DEFAULT."""
        for k in INTERFACE_KEYS: self[k] = self.default(k)

    def store(self):
        if not self.path: return
        try:
            tmp = self.path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f: json.dump(self.v, f, indent=1, ensure_ascii=False)
            os.replace(tmp, self.path)
        except Exception as ex:
            print('Settings not saved:', ex, flush=True)

    # ---- touches
    def codes(self, action):
        """Codes pyglet des touches d'une action."""
        c = self.codes_cache.get(action)
        if c is None:
            c = self.codes_cache[action] = tuple(s for s in (key_symbol(n) for n in self.v['touches'][action]) if s is not None)
        return c

    def action_of(self, symbol):
        """Action liee a une touche (ou None) : une touche ne sert qu'a une action."""
        name_str = name_of(symbol)
        for a, ts in self.v['touches'].items():
            if name_str in ts: return a
        return None

    def bind(self, action, column, symbol):
        """Lie une touche a (action, colonne 0/1) ; la touche est retiree de toute autre action. -> nom de l'action qui l'avait, ou None."""
        name_str = name_of(symbol); previous = None
        for a, ts in self.v['touches'].items():
            for i in range(2):
                if ts[i] == name_str and (a, i) != (action, column): ts[i] = None; previous = a
        self.v['touches'][action][column] = name_str; self.codes_cache = {}
        return previous

    def unbind(self, action, column):
        self.v['touches'][action][column] = None; self.codes_cache = {}

    def reset_to_default(self, action):
        """Remet les touches d'une action a leurs valeurs d'origine (une touche d'origine prise depuis par une autre action lui est retiree). -> noms des actions qui l'ont perdue."""
        lost = []; ts = self.v['touches']; ts[action] = [None, None]
        for col, name_str in enumerate(DEFAULT_KEYS[action]):
            if not name_str: continue
            for a, others in ts.items():
                for i in range(2):
                    if others[i] == name_str and (a, i) != (action, col): others[i] = None; lost.append(a)
            ts[action][col] = name_str
        self.codes_cache = {}
        return lost

    def is_default_binding(self, action):
        return list(self.v['touches'][action]) == list(DEFAULT_KEYS[action])

    def default_keys(self):
        self.v['touches'] = {k: list(x) for k, x in DEFAULT_KEYS.items()}; self.codes_cache = {}
