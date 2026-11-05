"""Petites fonctions de la fenetre (sans etat) : zone utile de l'ecran, rang de profondeur, camera libre, hauteur de camera, matrice de projection..."""
import math, sys
import numpy as np
import pyglet
from dq4_pc.langue import tr
from dq4_pc.noyau import moteur as MO
from dq4_pc.fenetre.constantes import EMPLACEMENTS_GROUPE, MARGE_FENETRE


def zone_utile():
    """(largeur, hauteur) maximales d'une zone de dessin qui tient sur l'ecran principal avec sa barre de titre et la barre des taches ; None si l'ecran est inconnu."""
    try:
        ec = pyglet.display.get_display().get_default_screen()
        try: k = max(1.0, float(ec.get_dpi()) / 96.0)
        except Exception: k = 1.0
        return int(ec.width - 16 * k), int(ec.height - MARGE_FENETRE * k)
    except Exception: return None


def ajuster_taille(w, h):
    """Ramene une taille de fenetre trop grande pour l'ecran a la plus grande taille de meme forme qui tient : Windows reduit alors la fenetre sans prevenir et le dessin gardait la taille demandee (scene zoomee, en partie hors de la fenetre)."""
    zu = zone_utile()
    if zu is None or (w <= zu[0] and h <= zu[1]): return int(w), int(h)
    k = min(zu[0] / float(w), zu[1] / float(h)); nw, nh = max(320, int(w * k)), max(180, int(h * k))
    print(tr('Fenêtre %d x %d trop grande pour l\'écran : %d x %d') % (w, h, nw, nh), flush=True)
    return nw, nh


def rang_profondeur_champ(sprites):
    """Carte du monde : rang de superposition de chaque sprite place (le plus grand rang est devant ; il pose la hauteur 0,04 + rang x 0,0005 du sprite a plat).
    Le jeu (FieldPartyDraw::draw, libdq4core 0x1ec5a8) trie les membres du groupe par profondeur decroissante (tri par selection ; a profondeur egale, l'emplacement le plus bas garde la tete) puis leur donne
    SpriteCharacter::setDepth 10, 9, 8... dans cet ordre : a profondeur egale, le heros (emplacement 0) est devant son equipier. Ordre ici : hauteur z du moteur (3e valeur de la position), puis le plus au sud
    (un equipier au sud du heros est devant lui), puis, a position egale (atterrissage d'une aile de chimere ou de Zoom : le groupe est empile sur un seul point, issue #135), l'emplacement le plus BAS devant
    pour le groupe ; les vehicules (emplacements >= 10) gardent le plus recent devant."""
    vus = [(float(s['pos'][2]) if len(s['pos']) > 2 else 0.0, float(s['pos'][1]), -sl if sl < EMPLACEMENTS_GROUPE else sl, sl) for sl, s in sprites.items() if s['pos'] is not None]
    return {sl: i for i, (_, _, _, sl) in enumerate(sorted(vus))}


def rot_unity(ex, ey, ez):
    """Matrice 3x3 d'une rotation Unity (angles d'Euler en degres, ordre z puis x puis y, espace gauche) : colonne = axe local dans le monde."""
    cx, sx, cy, sy, cz, sz = (math.cos(math.radians(ex)), math.sin(math.radians(ex)), math.cos(math.radians(ey)), math.sin(math.radians(ey)), math.cos(math.radians(ez)), math.sin(math.radians(ez)))
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]); Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]); Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def camera_libre(e):
    """Camera libre : position + rotation (comme en combat), pas de cible. Paquet 11 bit 7 (scenes, titre) ; casino : le moteur envoie la position et la rotation (paquet 10, masque 5) sans paquet 11."""
    return bool(e.cam_libre or (getattr(e, 'partie', None) == MO.PARTIE_CASINO and e.cam_rot is not None))


def degrade_fond(haut, bas):
    """Le fond de la ville est-il un vrai degrade (paquet 8 : couleurs du haut et du bas de l'image, `Etat.fond_haut` / `fond_bas`) ? Faux sans paquet 8 (None) ou si les deux couleurs sont egales : l'effacement
    de l'image, de cette couleur, suffit (aucune difference avec avant #111)."""
    return haut is not None and bas is not None and max(abs(float(a) - float(b)) for a, b in zip(haut, bas)) > 1e-6


def sans_validation(mo, ui_g, port):
    """Fenetre ouverte sans bouton de validation (manette 0x10) ni curseur du moteur (Oui / Non) : elle n'a rien a faire de la touche A (ex. « Quitter » de l'arene des monstres, un seul bouton de retour 0x400)."""
    if ui_g is None: return False
    f = mo.ui.f.get(port); fe = ui_g.f.get(port)
    return bool(f and fe and not f.get('grille') and not any(b[1] & 0x10 for b in fe.boutons()))


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


def transitions_dwm(fenetre, actif):
    """Windows seulement : active ou coupe les animations de la fenetre faites par le gestionnaire de fenetres (DWM : ouverture en fondu / zoom, reduction, restauration ; DWMWA_TRANSITIONS_FORCEDISABLED).
    Coupees pendant l'ouverture de la fenetre du jeu, elles ne s'ajoutent pas (un fondu de la fenetre elle-meme, par-dessus le noir puis les logos, ressemble a un rideau) ; remises ensuite (voir on_draw).
    Aucune erreur ne remonte (systeme sans DWM, poignee absente : rien ne change). -> True si le systeme a accepte."""
    if not sys.platform.startswith('win'): return False
    try:
        import ctypes
        hwnd = getattr(fenetre, '_hwnd', None)
        if not hwnd: return False
        v = ctypes.c_int(0 if actif else 1)
        return ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 3, ctypes.byref(v), ctypes.sizeof(v)) == 0
    except Exception as ex:
        print(tr('Transitions de fenêtre (DWM) inchangées : %r') % (ex,), flush=True); return False
