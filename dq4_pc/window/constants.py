"""Constantes de la fenetre : camera, interface, carte du monde, combat, sprites (valeurs lues dans le jeu d'origine ou choisies pour le portage)."""
import math, os
import numpy as np
from dq4_pc.core import engine as ENGINE


BTN_SAVES = 8         # numero de bouton de la case « Sauv. cloud » du menu de depart (type 53) : le portage y met « Sauvegardes »
SFX_BUTTON = 300               # bruitage de l'appui sur un bouton de menu (joue par Unity, MenuPortItem.Update)
SFX_PADS = 0x810         # touches de manette dont le bouton joue SFX_BUTTON a l'appui (MenuPortItem.Update : `m_gamepad & 0x810`) : A (0x10) et action (0x800) ; B (0x20), retour (0x400), fleches (1, 2, 4, 8) et zone 0x80 sont muets
SFX_PREVIEW = 316                # bruitage d'essai des volumes (page Son du menu Echap) : degats du sol (CommonWalkDamage::checkWalk), court et sans rapport avec l'interface
COMMON_SFX = (300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 402, 409, 412)       # decodes des le depart en tache de fond
MODE_PP = 4                   # dernier mode du menu « Shader » (0 originaux, 1 EPX x8, 4 pixel perfect : voir reglages.MODES_SPRITES) : pixel perfect (texels nets sans aucun adoucissement ; carte du monde a une echelle entiere, camera et sprites calees sur les pixels)
# Camera des villes, lue dans SceneCamera.Update / Global.CameraInitParams[0] (voir docs/technical-notes-dq4-port.md) :
ASPECT_PORTRAIT = 0.5625      # SceneCamera.ASPECT_DEF : l'original est concu pour un ecran portrait 450 x 800 ; Unity fixe le champ de vision HORIZONTAL (fov x 4/3) et en deduit la hauteur
RESOLUTIONS = ((1280, 720), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160))
WINDOW_MARGIN = 100           # pixels a 100 % : barre de titre, bordures et barre des taches autour de la zone de dessin
TOWN_FOV_DEFAULT = 9.5           # fov nominal du mode 0 (terrain) tant que le moteur n'en envoie pas (paquet 11)
TOWN_NEAR, TOWN_FAR = 5.0, 100.0
DIST_ADJ_TOWN = 4.0          # SceneCamera.s_distanceAdjust (.cctor) : apres LookAt, la camera avance de 4 unites le long de son axe
LOOK_DOWN_DEFAULT = 0.2                 # SceneCamera.s_lookDownAdjust (.cctor) : la camera releve son tangage de 0,2 degre
EDGE_CORRECTION_DEFAULT = 0.0     # correction des bords des sprites (voir Game._edge_correction) : 0 = panneau d'origine du jeu (defaut depuis #184), 1 = reconstruit a l'ecran (bords verticaux, #134)
SPRITE_L, SPRITE_H, SPRITE_SCALE = 24, 32, 0.045
UI_ZOOM = 1.12            # agrandissement des fenetres du jeu (la colonne portrait d'origine remplit exactement la hauteur de la fenetre) ; reduit a 1 si un groupe de fenetres ne tient plus a l'ecran
CB_MSG_BOTTOM = -338.0         # combat : bord bas du cadre de message = bord bas du cadre principal des menus de commandes (Combattre / Attaquer...)
CB_ZONE_MENUS = (-402.0, -144.0)       # combat : zone prise par les menus de commandes (bouton Fuir / retour compris) ; sert a garder la meme echelle d'interface que les messages
MSG_BOTTOM = -362.0           # fenetre de message du terrain descendue : bord bas du cadre (unites d'interface), comme les messages de combat
YESNO_BOX_SPACING = 1.0        # Oui/Non (type 1) : espace VISIBLE entre le bord bas de la pile Oui / Non et le bord haut de la boite de dialogue (D-231 : la pile est posee sur son coin haut droit ; 1 unite, comme entre Oui et Non ; avant : 4 unites entre les mailles, soit 8,5 visibles)
TITLE_MAP = ENGINE.TITLE_MAP         # carte de l'ecran-titre (ciel, logo, ile, dragon : scene sans heros dont le jeu fixe seul la camera ; voir _town_camera)
EXTENDED_SKIES = {'dpout': ('dpoutenk',), 'ev09': ('e9km1',)}         # cartes dont le plan de ciel (objets dont le nom contient ces mots) est prolonge de part et d'autre par symetrie (MAP-05, choix du joueur : « prolonger le ciel ») : plans concus pour l'ecran portrait, laissaient un grand coin noir a gauche (ev09) ou deux (dpout, sortie de donjon) en 16/9
CENTERED_WINDOWS = (54, 55)      # types de fenetres d'avant-partie (StartMenuSelect : liste des journaux ; StartNameEntry : choix du sexe) que la visionneuse centre a l'ecran
CH_PX, CH_ATLAS = 16.0, 64                                                  # carte du monde : pixels par tuile, tuiles par ligne d'atlas
# animation de l'eau de la carte du monde (Field.UpdatePattern du jeu) : 5 motifs ; la tuile affichee est numero + decalage du motif, qui avance toutes les 17 images
CH_PATTERN_END = np.array([326, 403, 940, 1195, 1260, 1713])                  # fin (exclue) de chaque plage de numeros de tuile (Field.m_patternCheck)
CH_PATTERN_NUM = np.array([0, 1, 2, 0, 3, 4, 0])                              # motif de chaque plage (0 = tuile fixe) ; la derniere valeur sert au-dela de la derniere plage
CH_PATTERN_STEP = (0, 76, 4, 64, 4)                                            # decalage ajoute a chaque pas, par motif (Field.m_patternInfo.acc)
CH_PATTERN_LIMIT = (0, 608, 96, 512, 96)                                        # le decalage retombe a 0 des qu'il atteint cette limite (.limit)
CH_PATTERN_PERIOD = 17
CH_SCALE = 51.84 * 0.48 / 24                                              # Chara.SetFieldMode : echelle 28,8 x 1,8 = 51,84 sur un maillage de 0,48 x 0,64 : le heros fait ~24,9 x 33,2 px (1,04 x la feuille 24 x 32), a plat sur la carte
# ZOOM COMMUN (carte du monde, villes, grottes, tours) : le heros garde partout la meme taille a l'ecran, celle des villes en 16/9 (camera d'origine : distance 39,55 jusqu'a la cible, 4 de moins apres
# SceneCamera.s_distanceAdjust, champ horizontal fov x 4/3 deduit de l'ecran portrait 450 x 800). HERO_FRAC = hauteur du panneau du heros / hauteur de la fenetre.
HERO_FRAC = SPRITE_H * SPRITE_SCALE / (2.0 * (39.55 - DIST_ADJ_TOWN) * math.tan(math.radians(TOWN_FOV_DEFAULT * 4.0 / 3.0) / 2) / ASPECT_PORTRAIT)       # ~ 0,103
CH_VIEW_HEIGHT = 32.0 / CH_PX * CH_SCALE / HERO_FRAC                         # carte du monde : tuiles visibles en hauteur (~ 20) ; en portrait l'original en montre 28,4 en hauteur et 16 en largeur
CH_GUTTER = 2                                                                 # carte du monde : gouttiere (pixels repetes) autour de chaque tuile de 16 px dans l'atlas copie : aucun debordement d'une tuile sur sa voisine au filtrage
CH_CELL = 16 + 2 * CH_GUTTER
CAM_JUMP_TOWN = 1.5                                                         # unites de ville par pas du moteur : au-dela, la cible de la camera a saute (coupure, changement de carte) : pas d'interpolation
CAM_JUMP_ROT = 0.35                                                          # rotation de la camera autour de sa cible (jeu ou joueur) : tant que le deplacement de la camera par rapport a sa cible, d'un pas a l'autre, reste sous cette part de la distance (environ 20 degres), c'est une rotation,
                                                                             # interpolee comme le reste ; au-dela (angle de scene regle d'un coup), c'est une coupure
CAM_DRAG_STEP = 6                                                           # glissement du clic molette : au plus ce nombre de rotations du jeu (ENGINE.CAM_STEP chacune) par pas du moteur, pour que la camera suive le pointeur (506 degres par seconde)
CAM_DRAG_MAX = 180.0                                                       # rotation demandee a la souris et pas encore faite : plafond en degres (un grand glissement ne fait pas tourner la camera longtemps apres le relachement)
ENGINE_STEP = 1.0 / 30.0                                                     # le moteur d'origine avance a 30 Hz (Time.fixedDeltaTime de Boot)
FAST_STEP_BUDGET = float(os.environ.get('DQ_BUDGET_PAS', '0.030'))                                                   # duree maximale (s) des pas du moteur dans une meme image affichee quand la marche est acceleree (vitesse de marche x2 a x4, accelerateur) : au-dela, le jeu prend du retard au lieu de figer l'image
CB_FOV_NOMINAL, CB_NEAR, CB_FAR, CB_YOFFSET, CB_SCENERY_SCALE = 48.0, 0.25, 500.0, 0.04, 6.0      # combat : Global.CameraInitParams[1] du Unity d'origine (champ de vision nominal ; Unity le multiplie par 4/3 et l'applique a l'horizontale d'une vue 4/3)
_cb = [float(x) for x in os.environ.get('DQ_CB', '0,0').split(',')]
CB_MIRROR_X, CB_DEC_Z = int(_cb[0]), _cb[1]      # (essais) miroir gauche/droite ; decalage du decor sur z
CB_CAP = 1536       # sommets reserves par monstre (listes de taille fixe)
CH_ICONS = {0: (0, 512, 48, 32), 1: (96, 512, 48, 32), 2: (192, 512, 48, 48), 3: (288, 512, 41, 32), 4: (384, 512, 41, 32), 5: (480, 512, 25, 31),
             6: (544, 512, 25, 31), 7: (608, 512, 40, 32), 8: (704, 512, 24, 24), 9: (768, 512, 32, 32), 10: (832, 512, 40, 32), 11: (928, 512, 24, 40),
             12: (0, 448, 32, 46), 13: (64, 448, 26, 28), 14: (128, 448, 41, 39), 15: (224, 448, 27, 42), 16: (288, 448, 48, 48), 17: (384, 448, 40, 32),
             19: (544, 448, 64, 58), 20: (640, 448, 41, 39)}   # icones de lieux de la carte du monde (FieldSymbol.s_symbols : 21 rectangles ; le 18 est vide dans l'atlas)
SCENERY_BIAS = 4.0            # decor : decalage de profondeur (en plus petites unites de profondeur) entre deux groupes dessines l'un apres l'autre ; 24 bits : 4 unites = 2e-7 de la plage de profondeur, invisible pour un relief reel
ORIGINAL_GUTTER = 2                 # feuilles d'origine : gouttiere de 2 px (bords repetes) autour de chaque case, comme les feuilles HD : le filtrage n'attrape plus un bout de la case voisine
HD_GUTTER, HD_LEVELS = 4, 2      # sprites HD (agrandissement x8, voir hd.py) : marge de 4 px, 2 niveaux de mipmaps
FONTS = ('Segoe UI', 'Arial', 'DejaVu Sans', 'Liberation Sans')
EDGE_ACTIONS = ('menu', 'discussion', 'carte', 'L', 'R')       # actions dont on detecte l'appui (front montant)
BTN_TALK, BTN_MENU, BTN_CHAT, BTN_MAP = 0x100, 0x800, 0x400, 0x1000     # arg2 de GameUpdate : parler / examiner (exactement 0x100), menu de commandes, discussion de groupe, carte
GROUP_SLOTS = 10      # carte du monde : emplacements 0 a 9 = membres du groupe (heros en 0) ; 10 a 12 = vehicules (bateau, ballon...)

def button_sfx(pad):
    """Vrai si l'appui d'un bouton de menu de touche de manette `pad` joue SFX_BUTTON dans le jeu d'origine (A et action seulement). Le clavier suit la meme regle que le doigt (D-156, #60)."""
    return bool(pad & SFX_PADS)
