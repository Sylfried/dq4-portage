"""Constantes de la fenetre : camera, interface, carte du monde, combat, sprites (valeurs lues dans le jeu d'origine ou choisies pour le portage)."""
import math, os
import numpy as np
from dq4_pc.noyau import moteur as MO


BTN_SAUVEGARDES = 8         # numero de bouton de la case « Sauv. cloud » du menu de depart (type 53) : le portage y met « Sauvegardes »
SE_BOUTON = 300               # bruitage de l'appui sur un bouton de menu (joue par Unity, MenuPortItem.Update)
SE_APERCU = 316                # bruitage d'essai des volumes (page Son du menu Echap) : degats du sol (CommonWalkDamage::checkWalk), court et sans rapport avec l'interface
SE_COURANTS = (300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 402, 409, 412)       # decodes des le depart en tache de fond
MODE_PP = 4                   # dernier mode du menu « Shader » (0 originaux, 1 EPX x8, 4 pixel perfect : voir reglages.MODES_SPRITES) : pixel perfect (texels nets sans aucun adoucissement ; carte du monde a une echelle entiere, camera et sprites calees sur les pixels)
# Camera des villes, lue dans SceneCamera.Update / Global.CameraInitParams[0] (voir docs/notes-technique-portage-dq4.md) :
ASPECT_PORTRAIT = 0.5625      # SceneCamera.ASPECT_DEF : l'original est concu pour un ecran portrait 450 x 800 ; Unity fixe le champ de vision HORIZONTAL (fov x 4/3) et en deduit la hauteur
RESOLUTIONS = ((1280, 720), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160))
MARGE_FENETRE = 100           # pixels a 100 % : barre de titre, bordures et barre des taches autour de la zone de dessin
FOV_VILLE_DEF = 9.5           # fov nominal du mode 0 (terrain) tant que le moteur n'en envoie pas (paquet 11)
VILLE_NEAR, VILLE_FAR = 5.0, 100.0
DIST_ADJ_VILLE = 4.0          # SceneCamera.s_distanceAdjust (.cctor) : apres LookAt, la camera avance de 4 unites le long de son axe
BAS_DEF = 0.2                 # SceneCamera.s_lookDownAdjust (.cctor) : la camera releve son tangage de 0,2 degre
CORRECTION_BORDS_DEF = 0.0     # correction des bords des sprites (voir Jeu._correction_bords) : 0 = panneau d'origine du jeu (defaut depuis #184), 1 = reconstruit a l'ecran (bords verticaux, #134)
SPRITE_L, SPRITE_H, SPRITE_ECHELLE = 24, 32, 0.045
UI_ZOOM = 1.12            # agrandissement des fenetres du jeu (la colonne portrait d'origine remplit exactement la hauteur de la fenetre) ; reduit a 1 si un groupe de fenetres ne tient plus a l'ecran
CB_MSG_BAS = -338.0         # combat : bord bas du cadre de message = bord bas du cadre principal des menus de commandes (Combattre / Attaquer...)
CB_ZONE_MENUS = (-402.0, -144.0)       # combat : zone prise par les menus de commandes (bouton Fuir / retour compris) ; sert a garder la meme echelle d'interface que les messages
MSG_BAS = -362.0           # fenetre de message du terrain descendue : bord bas du cadre (unites d'interface), comme les messages de combat
OUINON_ECART = 4.0        # Oui/Non (type 1) : espace entre son bord bas et le bord haut de la fenetre de message (l'original les separe de 78 unites : ici ils sont colles l'un a l'autre)
CARTE_TITRE = MO.CARTE_TITRE         # carte de l'ecran-titre (ciel, logo, ile, dragon : scene sans heros dont le jeu fixe seul la camera ; voir _camera_ville)
FENETRES_CENTREES = (54, 55)      # types de fenetres d'avant-partie (StartMenuSelect : liste des journaux ; StartNameEntry : choix du sexe) que la visionneuse centre a l'ecran
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
ZOOM_MIN, ZOOM_MAX = 0.5, 2.0                                               # zoom interne (1 = vue habituelle) ; reglage « Distance camera » du menu Echap et molette : 200 % (loin) a 50 % (pres)
CAM_LACET_VIT, CAM_TANGAGE_VIT = 100.0, 45.0                                # fleches : tourner la camera (degres / s), relever ou abaisser son angle (degres / s)
CAM_DIST_VIT = CAM_LACET_VIT                                                # touches « Caméra (Rapprocher) » / « Caméra (Éloigner) » (#146) : la distance change en continu, de autant de pourcents par seconde que la camera tourne de degres par seconde (100 : de 100 % a 50 % en 0,5 s), avec les memes reglages de vitesse (vitesse de camera, accelerateur)
CAM_ANGLE_MIN, CAM_ANGLE_MAX = -20.0, 40.0                                  # angle de camera (0 = comme le jeu)
CAM_CENTRE_MAX = 60.0                                                        # camera centree sur le heros : garde-fou, ecart maximal (unites) entre la cible du jeu et le heros pour corriger (position du heros perimee) ; le vrai critere est le verrou TownCamera (cam_jeu)
CAM_SAUT_VILLE = 1.5                                                         # unites de ville par pas du moteur : au-dela, la cible de la camera a saute (coupure, changement de carte) : pas d'interpolation, et la correction du centrage suit aussitot
CAM_MENE_DIST = 1.0                                                      # camera verrouillee sans cible (mode 0) : le jeu la mene ailleurs que sur le joueur quand sa cible est a plus de 1 unite du heros
CAM_Y_TAU = 1.0                                                             # escaliers, rampes, ponts (#47) : la camera ne suit plus la hauteur du heros a chaque pas ; sa hauteur de reference rejoint celle de la cible du jeu en exp(-t / CAM_Y_TAU) (secondes reelles ; 0 = comme le jeu)
CAM_Y_MAX = 3.0                                                             # ... sans jamais s'ecarter de plus de 3 unites de la hauteur du jeu (etages hauts, tours : le heros reste a moins de ~15 % de la hauteur de l'ecran du centre)
CAM_Y_RELIEF = 0.6                                                         # (#110, butte du village du prologue : +0,5 u en 8 pas) bande morte du lissage : tant que la hauteur du jeu reste a moins de 0,6 unite de la hauteur de repos de la camera, elle suit le jeu EXACTEMENT, comme le mobile (buttes, rampes, bosses du terrain) ; le lissage ci-dessus ne porte que sur ce qui depasse (escaliers, etages) ; voir `hauteur_camera`
CAM_RECENTRE_LACET, CAM_RECENTRE_ANGLE = 240.0, 90.0                         # recentrage anime (deux fleches opposees) : vitesse minimale en degres / s (plus vite quand l'ecart est grand : 5 x l'ecart par seconde)
CAM_RECENTRE_DIST = CAM_RECENTRE_LACET                                       # retour anime de la distance a 100 % (#167) : MEME vitesse que le recentrage de la rotation (#173, 04/11 11 h 30) : un ecart de X % se resorbe comme un ecart de X degres (au moins 240 par seconde, plus vite quand l'ecart est grand : 5 x l'ecart par seconde), pour que rotation, inclinaison et distance arrivent ensemble a l'origine
DIR_BITS = (MO.HAUT, MO.HAUT | MO.DROITE, MO.DROITE, MO.BAS | MO.DROITE, MO.BAS, MO.BAS | MO.GAUCHE, MO.GAUCHE, MO.HAUT | MO.GAUCHE)     # les 8 directions du moteur (0 = haut, dans le sens des aiguilles d'une montre)
PAS_MOTEUR = 1.0 / 30.0                                                     # le moteur d'origine avance a 30 Hz (Time.fixedDeltaTime de Boot)
BUDGET_PAS_RAPIDES = float(os.environ.get('DQ_BUDGET_PAS', '0.030'))                                                   # duree maximale (s) des pas du moteur dans une meme image affichee quand la marche est acceleree (vitesse de marche x2 a x4, accelerateur) : au-dela, le jeu prend du retard au lieu de figer l'image
CB_FOV_NOM, CB_NEAR, CB_FAR, CB_YOFFSET, CB_ECHELLE_DECOR = 48.0, 0.25, 500.0, 0.04, 6.0      # combat : Global.CameraInitParams[1] du Unity d'origine (champ de vision nominal ; Unity le multiplie par 4/3 et l'applique a l'horizontale d'une vue 4/3)
_cb = [float(x) for x in os.environ.get('DQ_CB', '0,0').split(',')]
CB_MIROIR_X, CB_DEC_Z = int(_cb[0]), _cb[1]      # (essais) miroir gauche/droite ; decalage du decor sur z
CB_CAP = 1536       # sommets reserves par monstre (listes de taille fixe)
CH_ICONES = {0: (0, 512, 48, 32), 1: (96, 512, 48, 32), 2: (192, 512, 48, 48), 3: (288, 512, 41, 32), 4: (384, 512, 41, 32), 5: (480, 512, 25, 31),
             6: (544, 512, 25, 31), 7: (608, 512, 40, 32), 8: (704, 512, 24, 24), 9: (768, 512, 32, 32), 10: (832, 512, 40, 32), 11: (928, 512, 24, 40),
             12: (0, 448, 32, 46), 13: (64, 448, 26, 28), 14: (128, 448, 41, 39), 15: (224, 448, 27, 42), 16: (288, 448, 48, 48), 17: (384, 448, 40, 32),
             19: (544, 448, 64, 58), 20: (640, 448, 41, 39)}   # icones de lieux de la carte du monde (FieldSymbol.s_symbols : 21 rectangles ; le 18 est vide dans l'atlas)
DECOR_BIAIS = 4.0            # decor : decalage de profondeur (en plus petites unites de profondeur) entre deux groupes dessines l'un apres l'autre ; 24 bits : 4 unites = 2e-7 de la plage de profondeur, invisible pour un relief reel
GOUT_ORIG = 2                 # feuilles d'origine : gouttiere de 2 px (bords repetes) autour de chaque case, comme les feuilles HD : le filtrage n'attrape plus un bout de la case voisine
HD_GOUTTIERE, HD_NIVEAUX = 4, 2      # sprites HD (agrandissement x8, voir hd.py) : marge de 4 px, 2 niveaux de mipmaps
POLICES = ('Segoe UI', 'Arial', 'DejaVu Sans', 'Liberation Sans')
ACT_FRONTS = ('menu', 'discussion', 'carte', 'L', 'R')       # actions dont on detecte l'appui (front montant)
BTN_PAROLE, BTN_MENU, BTN_DISCUSSION, BTN_CARTE = 0x100, 0x800, 0x400, 0x1000     # arg2 de GameUpdate : parler / examiner (exactement 0x100), menu de commandes, discussion de groupe, carte
EMPLACEMENTS_GROUPE = 10      # carte du monde : emplacements 0 a 9 = membres du groupe (heros en 0) ; 10 a 12 = vehicules (bateau, ballon...)
